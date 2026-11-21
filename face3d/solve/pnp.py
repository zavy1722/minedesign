"""Camera pose + focal length from 2D-3D correspondences (perspective-n-point).

Faces are shallow compared with typical camera distances, so focal length and
distance are strongly coupled (the classic "focal/depth ambiguity"), and when the
visible landmarks are nearly coplanar a near-weak-perspective view has a
pitch-reversed (Necker) twin pose that fits almost as well. The solver therefore
(DESIGN D-11, 4.3 "Initialisation"; rec CAM-3; [Rob 3.3]):

  1. tries every 35 mm-equivalent focal hypothesis of ``DEFAULT_F35_HYPOTHESES``
     when focal length is unknown (else the known or prior focal),
  2. runs three starts per focal: the scaled-orthographic (affine) pose, the
     pitch-flipped pose and the yaw-mirrored pose,
  3. refines (rotation, translation, log focal) of each start with
     Levenberg-Marquardt (analytic Jacobian, ``_project_jacobian``) and Huber
     IRLS, optionally with a log-normal focal prior,
  4. keeps converged cheiral solutions (every point in front of the camera),
     returns the best robust score, and
  5. raises ``C-TWIN`` with the twin camera when another such solution whose
     rotation differs by more than 10 degrees scores within 20 % of the best.

Units: model points in mm (any consistent unit works), pixels for image
coordinates, focal lengths in pixels unless named ``f35`` (35 mm-equivalent mm).
Camera convention: OpenCV, X_c = R X + t (see ``geometry/camera.py``).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..core.config import Default, register_defaults
from ..geometry.camera import Camera, focal_px_from_35mm
from ..geometry.rotations import (euler_xyz_deg, nearest_rotation, rodrigues, rotation_from_euler_deg,
                                  rotation_to_rvec, skew)
from .lm import levenberg_marquardt

# 35 mm-equivalent focal lengths tried when focal length is unknown (rec CAM-3; DESIGN D-11, 4.3):
# phone ultrawide 13, phone wide 24/26, 35, normal 50, phone tele 77, portrait 85, 120, long portrait
# 135 and 200 mm. The legacy seven (13, 24, 35, 50, 85, 135, 200) missed the common 26/77/120 mm.
DEFAULT_F35_HYPOTHESES = (13.0, 24.0, 26.0, 35.0, 50.0, 77.0, 85.0, 120.0, 135.0, 200.0)

_NEW = "\U0001F195"    # introduced by this design, uncalibrated
_BRAIN = "\U0001F9E0"  # expert knowledge, provisional

PNP_DEFAULTS = register_defaults("pnp", {
    "twin_min_angle_deg": Default(10.0, _NEW, "DESIGN D-11 / 4.3: C-TWIN when two cheiral poses > 10 deg apart",
                                  "deg", (0.0, 180.0)),
    "twin_score_ratio": Default(1.2, _NEW, "DESIGN D-11 / 4.3: C-TWIN when the twin scores within 20 % of the best",
                                "", (1.0, None)),
    "huber_sigmas": Default(2.0, _BRAIN, "DESIGN D-08 / 4.3 / 4.5: Huber delta = 2 in sigma units (rec BA-5)",
                            "sigma", (0.0, None)),
})
TWIN_MIN_ANGLE_DEG = float(PNP_DEFAULTS.twin_min_angle_deg.value)
TWIN_SCORE_RATIO = float(PNP_DEFAULTS.twin_score_ratio.value)

START_KINDS = ("affine", "pitch_flip", "yaw_mirror")


@dataclass
class PnPResult:
    camera: Camera
    rmse_px: float
    residuals_px: np.ndarray  # (N,) per-point reprojection error
    focal_estimated: bool
    twin: Camera | None = None                        # near-equal-score pose > 10 deg away (C-TWIN)
    flags: list[str] = field(default_factory=list)    # e.g. ['C-TWIN']
    candidates_tried: int = 0                         # (focal, start) pairs refined by LM


def affine_pose_init(X: np.ndarray, uv: np.ndarray, f: float, cx: float, cy: float) -> tuple[np.ndarray, np.ndarray]:
    """Scaled-orthographic initial pose (R, t) for a given focal length."""
    mu_X = X.mean(0)
    mu_uv = uv.mean(0)
    A = X - mu_X
    B = uv - mu_uv
    M = np.linalg.lstsq(A, B, rcond=None)[0].T  # (2,3): B ≈ A @ M.T
    U, S, Vt = np.linalg.svd(M, full_matrices=False)
    top = U @ Vt  # closest 2x3 with orthonormal rows
    s = float(S.mean())
    r3 = np.cross(top[0], top[1])
    R = nearest_rotation(np.vstack([top, r3]))
    z = f / max(s, 1e-12)
    centroid_cam = np.array([(mu_uv[0] - cx) * z / f, (mu_uv[1] - cy) * z / f, z])
    t = centroid_cam - R @ mu_X
    return R, t


def start_poses(R0: np.ndarray, t0: np.ndarray, X: np.ndarray) -> list[tuple[str, np.ndarray, np.ndarray]]:
    """The three PnP starts (kind, R, t) derived from the affine start (R0, t0) (WP-06 (b)).

    * ``affine``: (R0, t0) unchanged.
    * ``pitch_flip``: (pitch, yaw, roll) = ``euler_xyz_deg(R0)`` rebuilt as
      ``rotation_from_euler_deg(-pitch, yaw, roll)``.
    * ``yaw_mirror``: rebuilt as ``rotation_from_euler_deg(pitch, -yaw, roll)``.

    For a camera facing the head, ``euler_xyz_deg`` returns pitch near +-180 deg, so
    negating it reverses the head's pitch relative to the camera (the Necker twin
    of a near-weak-perspective view). DESIGN 4.3 words the flips as R R_x(pi) and a
    reflection about the camera's y-z plane; the WP-06 spec's Euler form is used.
    The flipped starts recompute t so that the model centroid keeps the affine
    start's camera-frame position: t = R0 mu + t0 - R mu.
    """
    mu = np.asarray(X, float).mean(0)
    c = R0 @ mu + t0
    pitch, yaw, roll = (float(a) for a in euler_xyz_deg(R0))
    out = [("affine", R0, t0)]
    for kind, (p, y) in (("pitch_flip", (-pitch, yaw)), ("yaw_mirror", (pitch, -yaw))):
        R = rotation_from_euler_deg(p, y, roll)
        out.append((kind, R, c - R @ mu))
    return out


def rotation_angle_deg(Ra: np.ndarray, Rb: np.ndarray) -> float:
    """Geodesic angle (degrees) between two rotation matrices."""
    c = (np.trace(np.asarray(Ra, float).T @ np.asarray(Rb, float)) - 1.0) / 2.0
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


def _project(params: np.ndarray, X: np.ndarray, cx: float, cy: float, f_fixed: float | None) -> np.ndarray:
    R = rodrigues(params[:3])
    t = params[3:6]
    f = f_fixed if f_fixed is not None else float(np.exp(params[6]))
    Xc = X @ R.T + t
    z = Xc[:, 2:3]
    z = np.where(np.abs(z) < 1e-9, 1e-9, z)
    return Xc[:, :2] / z * f + np.array([cx, cy])


def _drot_dv(v: np.ndarray, X: np.ndarray, R: np.ndarray) -> np.ndarray:
    """d(R(v) X_i)/dv for the Rodrigues vector v: (N,3,3), [i, :, j] = d(R X_i)/dv_j.

    Gallego & Yezzi (2015): d(R X)/dv = -R [X]x (v v^T + (R^T - I)[v]x) / |v|^2,
    and -[X]x (the first-order map used by ``rodrigues``) for |v| < 1e-8.
    """
    th2 = float(v @ v)
    if th2 < 1e-16:
        return -np.einsum("ab,ibc->iac", np.eye(3), _skews(X))
    M = (np.outer(v, v) + (R.T - np.eye(3)) @ skew(v)) / th2
    return -np.einsum("ab,ibc,cd->iad", R, _skews(X), M)


def _skews(X: np.ndarray) -> np.ndarray:
    """Stack of cross-product matrices [X_i]x, (N,3,3)."""
    S = np.zeros((len(X), 3, 3))
    S[:, 0, 1], S[:, 0, 2] = -X[:, 2], X[:, 1]
    S[:, 1, 0], S[:, 1, 2] = X[:, 2], -X[:, 0]
    S[:, 2, 0], S[:, 2, 1] = -X[:, 1], X[:, 0]
    return S


def _project_jacobian(params: np.ndarray, X: np.ndarray, f_fixed: float | None) -> np.ndarray:
    """Analytic d(_project)/d(params): (N, 2, 6 or 7) for (rvec, t[, log f])."""
    v = np.asarray(params[:3], float)
    R = rodrigues(v)
    f = f_fixed if f_fixed is not None else float(np.exp(params[6]))
    Xc = X @ R.T + params[3:6]
    z = Xc[:, 2]
    z = np.where(np.abs(z) < 1e-9, 1e-9, z)
    n = len(X)
    dP = np.zeros((n, 2, 3))  # d(uv)/d(Xc)
    dP[:, 0, 0] = f / z
    dP[:, 1, 1] = f / z
    dP[:, 0, 2] = -f * Xc[:, 0] / z ** 2
    dP[:, 1, 2] = -f * Xc[:, 1] / z ** 2
    J = np.zeros((n, 2, 7 if f_fixed is None else 6))
    J[:, :, :3] = np.einsum("iab,ibc->iac", dP, _drot_dv(v, X, R))
    J[:, :, 3:6] = dP
    if f_fixed is None:
        J[:, :, 6] = Xc[:, :2] / z[:, None] * f  # d(uv)/d(log f) = uv - c
    return J


def _sigma_xy(sigma_px, n: int) -> np.ndarray:
    """sigma_px (scalar, (N,) or (N,2); px) -> positive finite (N,2) array."""
    s = np.asarray(sigma_px, float)
    if s.ndim == 0:
        s = np.full((n, 2), float(s))
    elif s.shape == (n,):
        s = np.repeat(s[:, None], 2, axis=1)
    elif s.shape == (n, 2):
        s = s.copy()
    else:
        raise ValueError(f"sigma_px must be a scalar, (N,) or (N,2); got shape {s.shape} for N={n}")
    if not (np.all(np.isfinite(s)) and np.all(s > 0)):
        raise ValueError("sigma_px must be finite and > 0")
    return s


def solve_pnp(X: np.ndarray, uv: np.ndarray, width: int, height: int, *,
              f_px: float | None = None, estimate_focal: bool | None = None,
              f_prior_px: float | None = None, f_prior_log_sigma: float = 0.35,
              f35_hypotheses: tuple[float, ...] = DEFAULT_F35_HYPOTHESES,
              weights: np.ndarray | None = None, huber_px: float | None = 3.0,
              cx: float | None = None, cy: float | None = None,
              sigma_px: float | np.ndarray | None = None,
              huber_sigmas: float | None = 2.0) -> PnPResult:
    """Solve camera pose (and optionally focal length) from N 3D-2D matches.

    Parameters
    ----------
    X, uv : (N,3) model points and (N,2) observed pixels.
    f_px : known focal length in pixels (fixes focal unless estimate_focal=True).
    f_prior_px : soft prior on focal length (e.g. from EXIF); log-normal with
        `f_prior_log_sigma` (0.35 ≈ ±40 %).
    f35_hypotheses : 35 mm-equivalent focal starts (mm) used when neither
        ``f_px`` nor ``f_prior_px`` is given (DESIGN D-11).
    weights : per-landmark confidence weights.
    huber_px : Huber threshold in pixels for robustness to bad landmarks (None = L2).
        Used only when ``sigma_px`` is None (the legacy path, unchanged).
    sigma_px : per-landmark noise in pixels (scalar, (N,) or (N,2)). When given,
        residuals are whitened by it and Huber is applied at ``huber_sigmas``
        (sigma units; DESIGN 4.3 "Huber delta = 2 in sigma units"); ``huber_px``
        is then ignored. ``huber_sigmas=None`` gives whitened L2.

    Every start (focal hypothesis x {affine, pitch-flip, yaw-mirror}) is refined
    independently; candidates are ranked by the robust score
    sum_i w_i min(e_i, delta)^2 (+ the focal-prior term), with e_i the per-point
    error in px (legacy) or in sigma units, and the best converged cheiral one is
    returned. ``C-TWIN`` is raised (``flags``, ``twin``) when another converged
    cheiral candidate whose rotation differs from the best by more than
    ``TWIN_MIN_ANGLE_DEG`` scores at most ``TWIN_SCORE_RATIO`` x the best score.
    If no candidate reports LM convergence, the best cheiral candidate is
    returned with flag ``C-PNP-UNCONVERGED``.
    """
    X = np.asarray(X, float)
    uv = np.asarray(uv, float)
    n = len(X)
    if n < 4:
        raise ValueError("need at least 4 correspondences")
    cx = width / 2.0 if cx is None else cx
    cy = height / 2.0 if cy is None else cy
    if estimate_focal is None:
        estimate_focal = f_px is None
    w = np.ones(n) if weights is None else np.asarray(weights, float)
    whiten = sigma_px is not None
    if whiten:
        sig = _sigma_xy(sigma_px, n)
        delta = None if huber_sigmas is None else float(huber_sigmas)
    else:
        sig = None
        delta = huber_px

    if f_px is not None:
        f_inits = [f_px]
    elif f_prior_px is not None:
        f_inits = [f_prior_px]
    else:
        f_inits = [focal_px_from_35mm(f35, width, height) for f35 in f35_hypotheses]

    def errors(q: np.ndarray, f_fixed: float | None) -> np.ndarray:
        r = _project(q, X, cx, cy, f_fixed) - uv
        return np.linalg.norm(r / sig if whiten else r, axis=1)

    # candidates: (score, params, R, f, converged, cheiral)
    cands: list[tuple[float, np.ndarray, np.ndarray, float, bool, bool]] = []
    tried = 0
    for f0 in f_inits:
        R0, t0 = affine_pose_init(X, uv, f0, cx, cy)
        f_fixed = None if estimate_focal else f0
        for _kind, Rs, ts in start_poses(R0, t0, X):
            if ts @ ts <= 0 or (X @ Rs.T + ts)[:, 2].min() <= 0:
                continue
            tried += 1
            p0 = np.concatenate([rotation_to_rvec(Rs), ts] + ([[np.log(f0)]] if estimate_focal else []))
            irls_w = np.ones(n)
            p = p0
            converged = False
            for _ in range(4 if delta else 1):
                sw = np.sqrt(w * irls_w)

                def resid(q: np.ndarray, sw=sw) -> np.ndarray:
                    r = _project(q, X, cx, cy, f_fixed) - uv
                    if whiten:
                        r = r / sig
                    r = (r * sw[:, None]).ravel()
                    if estimate_focal and f_prior_px is not None:
                        r = np.append(r, (q[6] - np.log(f_prior_px)) / f_prior_log_sigma)
                    return r

                def jac(q: np.ndarray, sw=sw) -> np.ndarray:
                    J = _project_jacobian(q, X, f_fixed)
                    if whiten:
                        J = J / sig[:, :, None]
                    J = (J * sw[:, None, None]).reshape(2 * n, -1)
                    if estimate_focal and f_prior_px is not None:
                        prior_row = np.zeros((1, J.shape[1]))
                        prior_row[0, 6] = 1.0 / f_prior_log_sigma
                        J = np.vstack([J, prior_row])
                    return J

                lm = levenberg_marquardt(resid, p, jac=jac, max_iter=200)
                p, converged = lm.x, bool(lm.converged)
                if delta:
                    e = errors(p, f_fixed)
                    new_w = np.where(e <= delta, 1.0, delta / np.maximum(e, 1e-12))
                    if np.array_equal(new_w, irls_w):
                        break  # same weights: the next round would re-solve the problem just solved
                    irls_w = new_w
            e = errors(p, f_fixed)
            # Robust score used to compare hypotheses.
            score = float(np.sum(w * (np.minimum(e, delta) ** 2 if delta else e ** 2)))
            if estimate_focal and f_prior_px is not None:
                score += float(((p[6] - np.log(f_prior_px)) / f_prior_log_sigma) ** 2)
            R = rodrigues(p[:3])
            cheiral = bool((X @ R.T + p[3:6])[:, 2].min() > 0)
            f = float(np.exp(p[6])) if estimate_focal else float(f0)
            cands.append((score, p, R, f, converged, cheiral))

    flags: list[str] = []
    pool = [c for c in cands if c[5] and c[4]]
    if not pool:
        pool = [c for c in cands if c[5]]
        if pool:
            flags.append("C-PNP-UNCONVERGED")
    if not pool:
        raise RuntimeError("PnP failed: no hypothesis put the points in front of the camera")
    best = None
    for c in pool:  # first-found wins near-ties (legacy ordering)
        if best is None or c[0] < best[0] - 1e-9:
            best = c

    def make_cam(c) -> Camera:
        return Camera(f=c[3], cx=cx, cy=cy, width=width, height=height, R=c[2].copy(), t=c[1][3:6].copy())

    cam = make_cam(best)
    twin = None
    if "C-PNP-UNCONVERGED" not in flags:
        rivals = [c for c in pool if c is not best and rotation_angle_deg(c[2], best[2]) > TWIN_MIN_ANGLE_DEG
                  and c[0] <= TWIN_SCORE_RATIO * best[0]]
        if rivals:
            twin = make_cam(min(rivals, key=lambda c: c[0]))
            flags.append("C-TWIN")
    e = np.linalg.norm(cam.project(X) - uv, axis=1)
    return PnPResult(cam, float(np.sqrt(np.mean(e ** 2))), e, estimate_focal,
                     twin=twin, flags=flags, candidates_tried=tried)
