"""Per-view camera-model selection, lens diagnostics and the retouch residual test.

DESIGN D-12, 4.3 "Per-view camera model", 4.1 Q-WIDE / Q-RETOUCH (residual part), 3.2
(result ``model`` per camera), H6 (WBS WP-15).

Camera models (one view at a time, fitted against the consensus landmarks X, focal fixed
at the view's current f):

* ``pinhole``: plain pinhole, pose by the WP-06 multi-start PnP
  (:func:`face3d.solve.pnp.solve_pnp`) and a robust whitened refinement;
* ``virtual_rectilinear``: the same pinhole model solved in a virtual camera rotated onto
  the face ray (homography H = K R_virt K^-1, f' = f, :func:`face3d.geometry.camera.
  rectilinear_virtual_homography`) and mapped back: for exact data it *is* the pinhole
  model (a rotation about the centre is an exact homography; DESIGN D-12), so it is
  reported only when it reaches a strictly better fit (a better PnP basin on a strongly
  off-axis view);
* ``virtual_stereo``: the image is a stereographic projection about the principal point
  (phone face-warp correction; DESIGN D-12): pixels are unprojected stereographically,
  rotated by R_virt and seen by a local pinhole camera with f' = f sec^2(theta/2)
  (:func:`face3d.geometry.camera.stereographic_virtual_camera`), and the pose is refined
  with the exact stereographic projection;
* ``k1``: pinhole with one radial coefficient k1 on normalised coordinates and prior
  N(0, 0.02^2) (rec CAM, DESIGN 4.3).

Costs are -log-likelihoods: 0.5 sum_i rho_H(e_i) with e_i = ||Sigma_i^-1/2 r_i|| the whitened
radial residual and rho_H the Huber function (rho = e^2 for e <= delta, 2 delta e - delta^2
beyond, delta = 2; DESIGN D-08), plus 0.5 (k1 / 0.02)^2 for k1.  The penalised cost adds
0.5 x extra_params x ln(2 n) (a BIC penalty; n visible points).  Hypotheses whose fitted
predictions agree within the ambiguity margin (0.5 sum ||Sigma^-1/2 (u_a - u_b)||^2 < 2) are
observationally equivalent on this view and are merged into the simpler model (order:
pinhole, virtual_rectilinear, virtual_stereo, k1); the view is ``ambiguous`` when the best
two non-equivalent hypotheses are within 2.0 (sigma multiplier 3, DESIGN D-12).

Conventions: OpenCV cameras (X_c = R X + t), head frame in mm, pixels with the origin at
the top-left corner (DESIGN 3.1).  Covariances are (N, 2, 2) px^2 with NaN rows for hidden
landmarks.  Every numeric default is registered under ``camera_model`` in
:mod:`face3d.core.config` (badged, provisional).  numpy + stdlib only.
"""
from __future__ import annotations

import math
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from ..core.config import Default, register_defaults
from ..geometry.camera import (Camera, apply_homography, face_ray_angle, rectilinear_virtual_homography,
                               stereographic_project, stereographic_virtual_camera, virtual_rotation)
from ..geometry.rotations import rodrigues
from .lm import levenberg_marquardt
from .noise import whitening
from .pnp import solve_pnp

__all__ = [
    "CAMERA_MODEL", "MODELS", "huber_cost", "whitened_errors", "refine_pose", "projection_jacobians",
    "select_camera_model", "k1_flag", "radial_magnification_error", "radial_slope_flag", "lens_findings",
    "retouch_residual_test", "retouch_finding", "FLAG_K1", "FLAG_RADIAL", "FLAG_RETOUCH",
]

_PAGE = "\U0001F4C4"
_BRAIN = "\U0001F9E0"
_NEW = "\U0001F195"

CAMERA_MODEL = register_defaults("camera_model", {
    "huber_delta": Default(2.0, _BRAIN, "DESIGN D-08 / 4.3: Huber delta = 2 sigma in the robust view costs",
                           "sigma", (1e-6, None)),
    "k1_sigma": Default(0.02, _BRAIN, "DESIGN D-12 / 4.3: k1 ~ N(0, 0.02^2) (rec CAM)", "", (1e-9, None)),
    "bic_weight": Default(0.5, _NEW, "WBS WP-15: penalised cost = robust cost + 0.5 x extra params x ln(2n)",
                          "", (0.0, None)),
    "ambiguity_margin": Default(2.0, _NEW, "DESIGN D-12 / 4.3: ambiguous when the best two are within 2 cost "
                                "units", "", (0.0, None)),
    "ambiguous_sigma_mult": Default(3.0, _NEW, "DESIGN D-12 / 4.3: inflate sigma x3 when the model is ambiguous",
                                    "", (1.0, None)),
    "k1_flag_z": Default(3.0, _BRAIN, "DESIGN 4.3: diagnostic |k1 / sigma| > 3 flags non-pinhole processing "
                         "(com R2.8)", "", (0.0, None)),
    "radial_slope_max": Default(0.05, _BRAIN, "DESIGN 4.3: radial-residual slope implying > 5 % magnification "
                                "error flags 'non-pinhole processing or wrong z/f' (com R2.8)", "", (0.0, None)),
    "retouch_z": Default(3.0, _NEW, "DESIGN 4.1 Q-RETOUCH: eye/jaw residual pattern t > 3 (after BA, 4.9)", "",
                         (0.0, None)),
    "refine_rounds": Default(3, _NEW, "WP-15 implementation choice: Huber IRLS rounds of the per-view pose "
                             "refinement", "", (1, 20)),
})
_C = {k: CAMERA_MODEL[k].value for k in CAMERA_MODEL}

#: Model names in order of preference (simplest first; DESIGN 3.2 camera ``model``).
MODELS: tuple[str, ...] = ("pinhole", "virtual_rectilinear", "virtual_stereo", "k1")
_EXTRA_PARAMS = {"pinhole": 0, "virtual_rectilinear": 0, "virtual_stereo": 0, "k1": 1}
#: Finding codes (DESIGN 4.3 lens diagnostics, 4.1 Q-RETOUCH).
FLAG_K1 = "C-K1"
FLAG_RADIAL = "C-RADIAL-SLOPE"
FLAG_RETOUCH = "Q-RETOUCH"


# =========================================================================== robust costs
def huber_cost(e: Any, delta: float = _C["huber_delta"]) -> float:
    """sum_i rho_H(e_i): e^2 for e <= delta, 2 delta e - delta^2 beyond (non-finite e ignored)."""
    e = np.abs(np.asarray(e, float))
    e = e[np.isfinite(e)]
    d = float(delta)
    return float(np.sum(np.where(e <= d, e * e, 2.0 * d * e - d * d)))


def whitened_errors(uv_pred: np.ndarray, uv_obs: np.ndarray, W: np.ndarray) -> np.ndarray:
    """e_i = ||W_i (uv_pred_i - uv_obs_i)|| with W_i the inverse Cholesky factor of Sigma_i."""
    r = np.asarray(uv_pred, float) - np.asarray(uv_obs, float)
    return np.linalg.norm(np.einsum("nij,nj->ni", W, r), axis=1)


def _cov_sigma_px(cov: np.ndarray) -> np.ndarray:
    """Per-axis sigma (n, 2) for the diagonal-whitened PnP initialisation."""
    return np.sqrt(np.maximum(np.stack([cov[:, 0, 0], cov[:, 1, 1]], axis=1), 1e-12))


def refine_pose(project: Callable[[np.ndarray, np.ndarray, Any], np.ndarray], R0: np.ndarray, t0: np.ndarray,
                uv: np.ndarray, W: np.ndarray, *, extra0: Sequence[float] = (), extra_prior_sigma: Sequence[float] = (),
                delta: float = _C["huber_delta"], rounds: int = int(_C["refine_rounds"]),
                jac: Callable[[np.ndarray, np.ndarray, Any], np.ndarray] | None = None
                ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Robust whitened pose refinement (Huber IRLS rounds of Levenberg-Marquardt).

    ``project(R, t, extra) -> uv (n, 2)``; the rotation is updated multiplicatively,
    R <- exp([omega]_x) R; ``extra`` are additional model parameters (e.g. k1) with zero-mean
    Gaussian priors ``extra_prior_sigma``.  ``jac(R, t, extra) -> (n, 2, 6 + k)`` is the
    analytic d uv / d (omega, t, extra) (omega the left increment); without it the Jacobian is
    taken by central differences.  Returns ``(R, t, extra, e)`` with e the whitened radial
    residuals (all points, final pose).
    """
    from ..geometry.rotations import rotation_to_rvec
    R = np.asarray(R0, float).copy()
    t = np.asarray(t0, float).copy()
    ex = np.asarray(extra0, float).copy()
    ps = np.asarray(extra_prior_sigma, float)
    k = len(ex)
    n = len(uv)
    w = np.ones(n)
    for _ in range(int(rounds)):
        sw = np.sqrt(w)
        if jac is None:
            Rb = R

            def fun(q: np.ndarray, Rb=Rb, sw=sw) -> np.ndarray:
                pred = project(rodrigues(q[:3]) @ Rb, q[3:6], q[6:])
                r = (np.einsum("nij,nj->ni", W, pred - uv) * sw[:, None]).ravel()
                return np.concatenate([r, q[6:] / ps]) if k else r

            lm = levenberg_marquardt(fun, np.concatenate([np.zeros(3), t, ex]), max_iter=100)
            R = rodrigues(lm.x[:3]) @ Rb
        else:
            def fun(q: np.ndarray, sw=sw) -> np.ndarray:
                pred = project(rodrigues(q[:3]), q[3:6], q[6:])
                r = (np.einsum("nij,nj->ni", W, pred - uv) * sw[:, None]).ravel()
                return np.concatenate([r, q[6:] / ps]) if k else r

            def jf(q: np.ndarray, sw=sw) -> np.ndarray:
                Jp = jac(rodrigues(q[:3]), q[3:6], q[6:])
                Jw = (np.einsum("nij,njk->nik", W, Jp) * sw[:, None, None]).reshape(2 * n, -1)
                if k:
                    Jx = np.zeros((k, 6 + k))
                    Jx[:, 6:] = np.diag(1.0 / ps)
                    Jw = np.vstack([Jw, Jx])
                return Jw

            def retract(q: np.ndarray, dq: np.ndarray) -> np.ndarray:
                out = q + dq
                out[:3] = rotation_to_rvec(rodrigues(dq[:3]) @ rodrigues(q[:3]))
                return out

            lm = levenberg_marquardt(fun, np.concatenate([rotation_to_rvec(R), t, ex]), jac=jf, retract=retract,
                                     max_iter=100)
            R = rodrigues(lm.x[:3])
        t = lm.x[3:6].copy()
        ex = lm.x[6:].copy()
        e = whitened_errors(project(R, t, ex), uv, W)
        w = np.where(e <= delta, 1.0, delta / np.maximum(e, 1e-12))
    e = whitened_errors(project(R, t, ex), uv, W)
    return R, t, ex, e


def projection_jacobians(camera: Camera, X: Any) -> np.ndarray:
    """du/dX (N, 2, 3) of a distortion-free pinhole camera at world points X (mm -> px).

    P_i = (f / z_i) [[1, 0, -x_i / z_i], [0, 1, -y_i / z_i]] R with (x, y, z) = R X_i + t.
    """
    Xc = camera.to_camera(np.asarray(X, float))
    z = Xc[:, 2]
    A = np.zeros((len(Xc), 2, 3))
    A[:, 0, 0] = camera.f / z
    A[:, 1, 1] = camera.f / z
    A[:, 0, 2] = -camera.f * Xc[:, 0] / z ** 2
    A[:, 1, 2] = -camera.f * Xc[:, 1] / z ** 2
    return np.einsum("nij,jk->nik", A, camera.R)


def _map_cov(fun: Callable[[np.ndarray], np.ndarray], uv: np.ndarray, cov: np.ndarray, h: float = 0.5) -> np.ndarray:
    """J Sigma J^T for a pixel map ``fun`` (central differences with step h px)."""
    J = np.zeros((len(uv), 2, 2))
    for a in range(2):
        e = np.zeros(2)
        e[a] = h
        J[:, :, a] = (fun(uv + e) - fun(uv - e)) / (2.0 * h)
    return np.einsum("nij,njk,nlk->nil", J, cov, J)


def _pinhole_proj(cam: Camera) -> Callable:
    """project(R, t, extra, X): pinhole with optional k1 = extra[0] on normalised coordinates."""
    f, c = float(cam.f), np.array([cam.cx, cam.cy], float)

    def proj(R: np.ndarray, t: np.ndarray, ex: Any, X: np.ndarray) -> np.ndarray:
        Xc = X @ R.T + t
        xn = Xc[:, :2] / Xc[:, 2:3]
        if len(ex):
            xn = xn * (1.0 + float(ex[0]) * np.sum(xn * xn, axis=1, keepdims=True))
        return f * xn + c
    return proj


def _pinhole_jac(cam: Camera, X: np.ndarray) -> Callable:
    """Analytic d uv / d (omega, t[, k1]) of :func:`_pinhole_proj` (omega: left rotation increment)."""
    f = float(cam.f)

    def jac(R: np.ndarray, t: np.ndarray, ex: Any) -> np.ndarray:
        Y = X @ R.T                                  # R X
        Xc = Y + t
        z = Xc[:, 2]
        xn = Xc[:, :2] / z[:, None]
        n = len(X)
        k1 = float(ex[0]) if len(ex) else 0.0
        r2 = np.sum(xn * xn, axis=1)
        d = 1.0 + k1 * r2
        Du = f * (d[:, None, None] * np.eye(2)[None] + 2.0 * k1 * np.einsum("ni,nj->nij", xn, xn))
        Dn = np.zeros((n, 2, 3))
        Dn[:, 0, 0] = 1.0 / z
        Dn[:, 1, 1] = 1.0 / z
        Dn[:, :, 2] = -xn / z[:, None]
        A = np.einsum("nij,njk->nik", Du, Dn)        # d uv / d X_c
        S = np.zeros((n, 3, 3))
        S[:, 0, 1], S[:, 0, 2] = -Y[:, 2], Y[:, 1]
        S[:, 1, 0], S[:, 1, 2] = Y[:, 2], -Y[:, 0]
        S[:, 2, 0], S[:, 2, 1] = -Y[:, 1], Y[:, 0]
        J = np.zeros((n, 2, 6 + len(ex)))
        J[:, :, 0:3] = -np.einsum("nij,njk->nik", A, S)
        J[:, :, 3:6] = A
        if len(ex):
            J[:, :, 6] = f * r2[:, None] * xn
        return J
    return jac


def _stereo_proj(cam: Camera) -> Callable:
    def proj(R: np.ndarray, t: np.ndarray, ex: Any, X: np.ndarray) -> np.ndarray:
        return stereographic_project(X @ R.T + t, cam.f, cam.cx, cam.cy)
    return proj


# =========================================================================== model selection
def select_camera_model(uv: Any, X_consensus: Any, cam: Camera, noise_cov: Any, face_centre_X: Any) -> dict:
    """Choose the camera model of one view against the consensus shape (DESIGN D-12, 4.3).

    ``uv`` (N, 2) observed px (NaN rows hidden); ``X_consensus`` (N, 3) mm; ``cam`` the view's
    current camera (focal, principal point, image size and a pose near the solution, used for
    the face ray); ``noise_cov`` (N, 2, 2) px^2; ``face_centre_X`` (3,) mm (head frame).

    Returns ``{model, costs, ambiguous, sigma_mult, raw_costs, cameras, k1, k1_sigma,
    theta_deg, n, equivalent_to}``: ``costs`` are the penalised costs per hypothesis,
    ``raw_costs`` the robust costs, ``cameras`` the fitted pinhole poses (for
    ``virtual_stereo`` the pose of the stereographic model; for ``k1`` with ``k`` set),
    ``equivalent_to`` maps a hypothesis merged into a simpler one.  ``sigma_mult`` is 3.0
    when ``ambiguous`` else 1.0.
    """
    uv = np.asarray(uv, float)
    X = np.asarray(X_consensus, float)
    cov = np.asarray(noise_cov, float)
    vis = np.isfinite(uv).all(axis=1) & np.isfinite(X).all(axis=1) & np.isfinite(cov).all(axis=(1, 2))
    n = int(vis.sum())
    if n < 6:
        raise ValueError("select_camera_model needs at least 6 visible landmarks")
    uvv, Xv, Cv = uv[vis], X[vis], cov[vis]
    W = whitening(Cv)
    sig = _cov_sigma_px(Cv)
    W_img, H_img = int(cam.width), int(cam.height)
    delta = float(_C["huber_delta"])
    fc = np.asarray(face_centre_X, float).reshape(3)
    theta = face_ray_angle(cam, fc)
    Rv = virtual_rotation(cam, fc)

    fits: dict[str, dict] = {}

    def pnp(uv_in: np.ndarray, f: float, cx: float, cy: float, s: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        r = solve_pnp(Xv, uv_in, W_img, H_img, f_px=f, estimate_focal=False, cx=cx, cy=cy, sigma_px=s,
                      huber_sigmas=delta)
        return r.camera.R, r.camera.t

    # (a) pinhole
    ph = _pinhole_proj(cam)
    R0, t0 = pnp(uvv, cam.f, cam.cx, cam.cy, sig)
    pj = _pinhole_jac(cam, Xv)
    R, t, ex, e = refine_pose(lambda R_, t_, x_: ph(R_, t_, x_, Xv), R0, t0, uvv, W, delta=delta, jac=pj)
    fits["pinhole"] = {"R": R, "t": t, "ex": ex, "e": e, "pred": ph(R, t, ex, Xv)}
    # (b) virtual rectilinear: PnP in the camera rotated onto the face ray (f' = f), mapped back
    Hh = rectilinear_virtual_homography(cam, Rv)
    uv_r = apply_homography(Hh, uvv)
    cov_r = _map_cov(lambda q: apply_homography(Hh, q), uvv, Cv)
    Rr, tr = pnp(uv_r, cam.f, cam.cx, cam.cy, _cov_sigma_px(cov_r))
    R, t, ex, e = refine_pose(lambda R_, t_, x_: ph(R_, t_, x_, Xv), Rv.T @ Rr, Rv.T @ tr, uvv, W, delta=delta,
                              jac=pj)
    fits["virtual_rectilinear"] = {"R": R, "t": t, "ex": ex, "e": e, "pred": ph(R, t, ex, Xv)}
    # (c) virtual stereographic: unproject stereographically, rotate, pinhole with f' = f sec^2(theta/2)
    st = _stereo_proj(cam)
    try:
        virt, to_virtual = stereographic_virtual_camera(cam, fc)
        uv_s = to_virtual(uvv)
        cov_s = _map_cov(to_virtual, uvv, Cv)
        Rs, ts = pnp(uv_s, virt.f, virt.cx, virt.cy, _cov_sigma_px(cov_s))
        R_init, t_init = Rv.T @ Rs, Rv.T @ ts
    except (ValueError, RuntimeError, np.linalg.LinAlgError):
        R_init, t_init = fits["pinhole"]["R"], fits["pinhole"]["t"]
    R, t, ex, e = refine_pose(lambda R_, t_, x_: st(R_, t_, x_, Xv), R_init, t_init, uvv, W, delta=delta)
    fits["virtual_stereo"] = {"R": R, "t": t, "ex": ex, "e": e, "pred": st(R, t, ex, Xv)}
    # (d) k1 with prior N(0, 0.02^2), from the better pinhole-family pose
    base = min(("pinhole", "virtual_rectilinear"), key=lambda m: huber_cost(fits[m]["e"], delta))
    ks = float(_C["k1_sigma"])
    R, t, ex, e = refine_pose(lambda R_, t_, x_: ph(R_, t_, x_, Xv), fits[base]["R"], fits[base]["t"], uvv, W,
                              extra0=[0.0], extra_prior_sigma=[ks], delta=delta, jac=pj)
    fits["k1"] = {"R": R, "t": t, "ex": ex, "e": e, "pred": ph(R, t, ex, Xv)}

    raw = {m: 0.5 * huber_cost(fits[m]["e"], delta) + (0.5 * float(fits[m]["ex"][0] / ks) ** 2 if m == "k1" else 0.0)
           for m in MODELS}
    pen = {m: raw[m] + float(_C["bic_weight"]) * _EXTRA_PARAMS[m] * math.log(2.0 * n) for m in MODELS}
    margin = float(_C["ambiguity_margin"])

    def sep(a: str, b: str) -> float:
        d = np.einsum("nij,nj->ni", W, fits[a]["pred"] - fits[b]["pred"])
        return 0.5 * float(np.sum(d * d))

    best = min(MODELS, key=lambda m: (pen[m], MODELS.index(m)))
    # merge observationally equivalent hypotheses into the simplest one
    chosen = best
    for m in MODELS:
        if MODELS.index(m) < MODELS.index(chosen) and sep(m, best) < margin and pen[m] - pen[best] < margin:
            chosen = m
            break
    equivalent = {m: chosen for m in MODELS if m != chosen and sep(m, chosen) < margin}
    rivals = [m for m in MODELS if m != chosen and m not in equivalent]
    ambiguous = bool(rivals) and min(pen[m] for m in rivals) - pen[best] < margin
    # k1 uncertainty from the Gauss-Newton Hessian of the k1 fit (numeric Jacobian, final weights)
    k1 = float(fits["k1"]["ex"][0])
    k1_sigma = _k1_sigma(cam, fits["k1"], Xv, W, ks, delta)
    cams = {}
    for m in MODELS:
        c = Camera(cam.f, cam.cx, cam.cy, cam.width, cam.height, fits[m]["R"].copy(), fits[m]["t"].copy())
        if m == "k1":
            c.k = np.array([k1, 0.0])
        cams[m] = c
    return {"model": chosen, "costs": pen, "ambiguous": ambiguous,
            "sigma_mult": float(_C["ambiguous_sigma_mult"]) if ambiguous else 1.0, "raw_costs": raw,
            "cameras": cams, "k1": k1, "k1_sigma": k1_sigma, "theta_deg": math.degrees(theta), "n": n,
            "equivalent_to": equivalent}


def _k1_sigma(cam: Camera, fit: dict, Xv: np.ndarray, W: np.ndarray, ks: float, delta: float) -> float:
    """Posterior SD of k1 from the Gauss-Newton Hessian of the k1 fit (final Huber weights)."""
    e = fit["e"]
    sw = np.sqrt(np.where(e <= delta, 1.0, delta / np.maximum(e, 1e-12)))
    Jp = _pinhole_jac(cam, Xv)(fit["R"], fit["t"], fit["ex"])
    J = (np.einsum("nij,njk->nik", W, Jp) * sw[:, None, None]).reshape(-1, 7)
    H = J.T @ J
    H[6, 6] += 1.0 / ks ** 2
    try:
        C = np.linalg.inv(H)
    except np.linalg.LinAlgError:
        return float("nan")
    return float(math.sqrt(max(C[6, 6], 0.0)))


# =========================================================================== lens diagnostics
def k1_flag(k1: float, sigma: float, *, z: float = _C["k1_flag_z"]) -> bool:
    """Diagnostic k1 significant: |k1 / sigma| > 3 (DESIGN 4.3: 'non-pinhole processing or wrong z/f')."""
    k1, sigma = float(k1), float(sigma)
    if not (sigma > 0 and math.isfinite(sigma) and math.isfinite(k1)):
        return False
    return abs(k1 / sigma) > float(z)


def radial_magnification_error(per_point_residual_radial: Any, rho_delta: Any) -> float:
    """Least-squares slope b of r_i = a + b rho_i (radial residual px against radial distance px).

    A local magnification error m gives radial residuals m rho about the magnification centre,
    so b is the implied relative magnification error (0.05 = 5 %).  Non-finite pairs are ignored;
    NaN when fewer than 3 points or no spread in rho.
    """
    r = np.asarray(per_point_residual_radial, float).reshape(-1)
    rho = np.asarray(rho_delta, float).reshape(-1)
    ok = np.isfinite(r) & np.isfinite(rho)
    r, rho = r[ok], rho[ok]
    if len(r) < 3:
        return float("nan")
    dr = rho - rho.mean()
    den = float(dr @ dr)
    if not den > 0:
        return float("nan")
    return float(dr @ (r - r.mean()) / den)


def radial_slope_flag(per_point_residual_radial: Any, rho_delta: Any, *, max_slope: float = _C["radial_slope_max"]
                      ) -> bool:
    """Radial-residual slope implying a magnification error above 5 % (DESIGN 4.3; com R2.8 🧠)."""
    b = radial_magnification_error(per_point_residual_radial, rho_delta)
    return bool(math.isfinite(b) and abs(b) > float(max_slope))


def _finding(code: str, value: Any, threshold: Any, action: str, key: str, photo_id: str | None,
             detail: dict | None) -> dict:
    """A finding dict with the fields of :class:`face3d.qa.checks.Finding` (solve/ stays below qa/)."""
    d = CAMERA_MODEL[key]
    return {"code": code, "severity": "warn", "value": value, "threshold": threshold, "action": action,
            "msg_key": f"solve.{code}", "fix_key": f"solve.{code}.fix", "source": d.source, "badge": d.badge,
            "photo_id": photo_id, "detail": detail}


def lens_findings(k1: float | None = None, k1_sigma: float | None = None, radial_slope: float | None = None, *,
                  photo_id: str | None = None) -> list[dict]:
    """Lens diagnostics of one view as findings (DESIGN 4.3): ``C-K1`` when :func:`k1_flag`,
    ``C-RADIAL-SLOPE`` when |slope| > 5 % ("non-pinhole processing or wrong z/f"; action ask)."""
    out = []
    if k1 is not None and k1_sigma is not None and k1_flag(k1, k1_sigma):
        out.append(_finding(FLAG_K1, float(k1) / float(k1_sigma), float(_C["k1_flag_z"]), "ask", "k1_flag_z",
                            photo_id, {"k1": float(k1), "k1_sigma": float(k1_sigma)}))
    if radial_slope is not None and math.isfinite(float(radial_slope)) and \
            abs(float(radial_slope)) > float(_C["radial_slope_max"]):
        out.append(_finding(FLAG_RADIAL, float(radial_slope), float(_C["radial_slope_max"]), "ask",
                            "radial_slope_max", photo_id, None))
    return out


# =========================================================================== retouch residual test
def _ratio_and_grad(uv: np.ndarray, num: tuple[tuple[int, int], ...], den: tuple[int, int]
                    ) -> tuple[float, dict[int, np.ndarray]]:
    """ratio = mean_k |uv_a - uv_b| over ``num`` pairs / |uv_c - uv_d| and d ratio / d uv_i."""
    grads: dict[int, np.ndarray] = {}

    def add(i: int, g: np.ndarray) -> None:
        grads[i] = grads.get(i, np.zeros(2)) + g

    nums = []
    for a, b in num:
        d = uv[a] - uv[b]
        nums.append((a, b, d, float(np.linalg.norm(d))))
    N = float(np.mean([x[3] for x in nums]))
    c, dd = den
    dv = uv[c] - uv[dd]
    D = float(np.linalg.norm(dv))
    ratio = N / D
    for a, b, d, L in nums:
        g = d / L / len(nums) / D
        add(a, g)
        add(b, -g)
    g = -ratio * dv / D / D
    add(c, g)
    add(dd, -g)
    return ratio, grads


def retouch_residual_test(view_uv: Any, projected_consensus_uv: Any, ids: Mapping[str, int], noise_cov: Any, *,
                          consensus_cov: Any = None, inliers: Any = None, z_max: float = _C["retouch_z"]
                          ) -> tuple[dict, float, bool]:
    """Post-BA residual pattern of a beauty warp in one view (DESIGN 4.1 Q-RETOUCH, 7.4).

    ``view_uv`` (N, 2) the view's landmarks, ``projected_consensus_uv`` (N, 2) the consensus
    shape projected by the view's solved camera, ``ids`` landmark indices with keys
    ``en_L, ex_L, en_R, ex_R, go_L, go_R`` (and optional ``p_L, p_R`` eye centres),
    ``noise_cov`` (N, 2, 2) px^2 of the view (``consensus_cov``, optional, adds the projected
    consensus covariance); ``inliers`` (N,) bool, optional: only these points are used (pass
    the bundle's ``inlier_mask`` so that gross detector outliers rejected by the robust
    schedule cannot fake a pattern).

    * ``eye_width_ratio`` = mean eye width (en-ex, both eyes) / outer IOD (ex_L-ex_R);
      ``bigonial_ratio`` = |go_L - go_R| / outer IOD; each is computed on the view and on the
      projected consensus and z-scored with the first-order propagated noise
      (z = (ratio_view - ratio_consensus) / sigma).  A missing landmark gives NaN.
    * ``t_eye``: the residuals r_i = view - consensus of the four eye corners projected on the
      outward eye directions d_i (from the eye centre: the pupil when given, else the en-ex
      midpoint) are regressed on the corner distances rho_i to that centre (r_i.d_i = beta
      rho_i, weighted by 1 / d_i^T Sigma_i d_i); t = beta / SE(beta) (eye enlargement > 0).

    Returns ``({'eye_width_ratio': z, 'bigonial_ratio': z}, t_eye, flagged)`` with flagged =
    any |z| > 3 or t_eye > 3 (finding Q-RETOUCH: sigma x2-3, no texture; DESIGN 4.1).
    """
    V = np.array(view_uv, dtype=float, copy=True)
    P = np.asarray(projected_consensus_uv, float)
    if inliers is not None:
        V[~np.asarray(inliers, bool).reshape(-1)] = np.nan
    C = np.asarray(noise_cov, float)
    if consensus_cov is not None:
        C = C + np.asarray(consensus_cov, float)
    req = ("en_L", "ex_L", "en_R", "ex_R")
    for k in req:
        if k not in ids:
            raise KeyError(f"retouch_residual_test needs landmark id {k!r}")
    idx = {k: int(v) for k, v in ids.items() if v is not None}

    def finite(*keys: str) -> bool:
        return all(k in idx and np.isfinite(V[idx[k]]).all() and np.isfinite(P[idx[k]]).all()
                   and np.isfinite(C[idx[k]]).all() for k in keys)

    def zscore(num: tuple, den: tuple, keys: tuple) -> float:
        if not finite(*keys):
            return float("nan")
        rv, gv = _ratio_and_grad(V, num, den)
        rp, _ = _ratio_and_grad(P, num, den)
        var = float(sum(g @ C[i] @ g for i, g in gv.items()))
        return (rv - rp) / math.sqrt(var) if var > 0 else float("nan")

    eL, xL, eR, xR = (idx[k] for k in req)
    z_eye = zscore(((eL, xL), (eR, xR)), (xL, xR), req)
    z_go = (zscore(((idx["go_L"], idx["go_R"]),), (xL, xR), ("go_L", "go_R", "ex_L", "ex_R"))
            if "go_L" in idx and "go_R" in idx else float("nan"))
    # eye-corner pattern
    num, den = 0.0, 0.0
    for side, (en, ex) in (("L", (eL, xL)), ("R", (eR, xR))):
        if not finite(f"en_{side}", f"ex_{side}"):
            continue
        pk = f"p_{side}"
        if pk in idx and np.isfinite(V[idx[pk]]).all():
            ctr = V[idx[pk]]
        else:
            ctr = 0.5 * (V[en] + V[ex])
        for i in (en, ex):
            d = V[i] - ctr
            rho = float(np.linalg.norm(d))
            if not rho > 0:
                continue
            u = d / rho
            y = float((V[i] - P[i]) @ u)
            v = float(u @ C[i] @ u)
            if not v > 0:
                continue
            num += rho * y / v
            den += rho * rho / v
    t_eye = num / math.sqrt(den) if den > 0 else float("nan")
    z = {"eye_width_ratio": float(z_eye), "bigonial_ratio": float(z_go)}
    flagged = any(math.isfinite(v) and abs(v) > float(z_max) for v in z.values()) or \
        (math.isfinite(t_eye) and t_eye > float(z_max))
    return z, float(t_eye), bool(flagged)


def retouch_finding(z_scores: Mapping[str, float], t_eye: float, flagged: bool, *, photo_id: str | None = None
                    ) -> dict | None:
    """The ``Q-RETOUCH`` finding for a flagged view (DESIGN 4.1: sigma x2-3, no texture), else None.

    Action ``down_weight`` (the pipeline inflates the view's sigma and excludes it from texture);
    ``detail`` carries the z-scores and t_eye."""
    if not flagged:
        return None
    return _finding(FLAG_RETOUCH, {"z": dict(z_scores), "t_eye": float(t_eye)}, float(_C["retouch_z"]),
                    "down_weight", "retouch_z", photo_id, {"exclude_texture": True, "sigma_mult": [2.0, 3.0]})

