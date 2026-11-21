"""Mirror test: was this photo horizontally flipped (selfie mirror, editor flip)?

DESIGN D-10, 4.10, H6, H7 (WBS WP-15).  A mirrored photo's landmarks satisfy
obs[pi(i)] = (W - u_i, v_i) (DESIGN 3.1, :func:`face3d.io.image_ops.flip_uv`): the face seen
is the mirror image of the subject with left/right labels swapped.  For an exactly symmetric
face that is indistinguishable from the real photo, so the test compares the two hypotheses
on the consensus shape and predicts how detectable a flip *could* be from the consensus's own
asymmetry:

* C0, C1: robust costs sum_i min(e_i^2, 3.035^2) (e_i = ||Sigma_i^-1/2 r_i|| the whitened
  radial residual; a point beyond the DESIGN D-08 rejection threshold 3.035 sigma counts as an
  outlier with a constant cost, so C ~ chi^2 with 2 n_v - 6 dof for inliers) after a WP-06 PnP
  (:func:`face3d.solve.pnp.solve_pnp`, multi-start, whitened by per-axis sigma_px from
  ``noise_cov``, focal fixed at ``camera_init.f``) refined by Huber IRLS (delta 2 sigma, D-08)
  with the full 2x2 covariances, for the landmarks as given (C0) and flipped (C1; uv' = W - u,
  labels permuted by pi, covariances reflected and permuted, principal point W - c_x);
* delta = (C0 - C1) / C0 (relative gain of the flip) and gap = C0 - C1;
* A = (X - reflect(X_pi)) / 2: the asymmetric part of the consensus about ``plane`` (n, d)
  (default the head frame's sagittal plane x = 0), with X_pi the label-permuted consensus;
* g = || (I - P) w ||^2 with w the stacked Sigma_i^-1/2 J_i A_i (J_i = d u / d X_i at the
  as-given solved pose) and P the projector onto the whitened pose Jacobian (rotation and
  translation): the whitened image size of the asymmetry that a pose refit cannot absorb, i.e.
  the predicted detectability of a flip.  ``g_raw`` = ||w||^2 is the WBS formula without the
  projection; it over-predicts the observed gap by up to ~25x when the asymmetry is largely a
  rigid motion (a mid-sagittal plane slightly off the reference plane), on the WP-11 surface
  subjects its correlation with the gap is ~0.3-0.5 against ~0.8-0.9 after projection, so a
  'keep' could be reported for a flip the test could not have seen (H7 prefers 'undetermined');
* decision: ``'unverifiable'`` when every view of the set is a front-camera selfie (nothing
  to compare against; H7), ``'undetermined'`` when g < g_min (4) (the face is too symmetric
  at this noise level), ``'suggest_flip'`` when delta > rel (0.10 front camera, 0.20 other)
  **and** gap > 2 sqrt(2 n_v) ([Art 3.6] derived), else ``'keep'``;
* ``preselect_flip`` (UI pre-selects [Flip]) only for ``'suggest_flip'`` with delta > 0.2 and
  front-camera EXIF or agreement of other views.

The engine never flips anything: it never mutates its inputs and applying a flip is a
recorded user (or explicit CLI flag) decision in the project (DESIGN D-10; WP-20).

``margin`` = gap - 2 sqrt(2 n_v) (cost units; > 0 means the absolute gap is significant).
Defaults are registered under ``mirror`` in :mod:`face3d.core.config` (🆕 / 🧠).
numpy + stdlib only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from ..core.config import Default, register_defaults
from ..geometry.camera import Camera
from ..geometry.procrustes import reflect
from ..io.image_ops import flip_uv
from .camera_model import _cov_sigma_px, _pinhole_jac, _pinhole_proj, projection_jacobians, refine_pose
from .noise import whitening
from .pnp import solve_pnp

__all__ = ["MIRROR", "MirrorDecision", "mirror_test", "flip_cov", "DECISIONS", "project_mirror_status"]

_BRAIN = "\U0001F9E0"
_NEW = "\U0001F195"

MIRROR = register_defaults("mirror", {
    "g_min": Default(4.0, _NEW, "DESIGN D-10 / 4.10: 'undetermined' when the predicted gap g < 4", "", (0.0, None)),
    "rel_front": Default(0.10, _BRAIN, "DESIGN D-10 / 4.10: suggest a flip at delta > 10 % on a front camera "
                         "([Art 3.6])", "", (0.0, 1.0)),
    "rel_other": Default(0.20, _BRAIN, "DESIGN D-10 / 4.10: suggest a flip at delta > 20 % on other cameras "
                         "([Art 3.6])", "", (0.0, 1.0)),
    "gap_k": Default(2.0, _BRAIN, "DESIGN D-10 / 4.10: absolute gap C0 - C1 > 2 sqrt(2 n_v) ([Art 3.6], derived)",
                     "", (0.0, None)),
    "preselect_delta": Default(0.20, _NEW, "DESIGN 4.10: UI pre-selects [Flip] only when delta > 0.2 and front "
                               "camera or other views agree", "", (0.0, 1.0)),
    "huber_delta": Default(2.0, _BRAIN, "DESIGN D-08: Huber delta 2 sigma in the robust pose refinement of "
                           "C0 / C1", "sigma", (1e-6, None)),
    "reject_k": Default(3.035, "\U0001F522", "DESIGN D-08 / 4.5: residuals beyond 3.035 sigma (1 % false alarm in "
                        "2D) count as rejected outliers: C = sum_i min(e_i^2, 3.035^2)", "sigma", (1e-6, None)),
})
_M = {k: MIRROR[k].value for k in MIRROR}

#: The four answers of the mirror test (DESIGN 4.10; H7: undetermined / unverifiable are first class).
DECISIONS: tuple[str, ...] = ("keep", "suggest_flip", "undetermined", "unverifiable")


@dataclass
class MirrorDecision:
    """Result of :func:`mirror_test` for one view (DESIGN D-10, 4.10).

    delta : (C0 - C1) / C0, relative cost reduction of the flipped hypothesis.
    g : predicted detectability ||(I - P) Sigma^-1/2 J A||^2 of the consensus asymmetry
        (pose-absorbable part removed; ``g_raw`` without the projection).
    gap : C0 - C1 (cost units, ~chi^2).
    margin : gap - 2 sqrt(2 n_v) (> 0: the absolute gap is significant).
    decision : 'keep' | 'suggest_flip' | 'undetermined' | 'unverifiable'.
    preselect_flip : the UI may pre-select [Flip] (never applied automatically).
    """

    delta: float
    g: float
    gap: float
    margin: float
    decision: str
    preselect_flip: bool
    C0: float = float("nan")
    C1: float = float("nan")
    g_raw: float = float("nan")
    n_v: int = 0
    rel_threshold: float = float("nan")
    camera: Camera | None = None           # as-given solved pose (focal fixed)
    camera_flipped: Camera | None = None   # pose of the flipped hypothesis (in the flipped image)
    flags: list[str] = field(default_factory=list)


def flip_cov(cov: Any, perm: Sequence[int]) -> np.ndarray:
    """Covariances of horizontally flipped landmarks: out[pi[i]] = F cov[i] F, F = diag(-1, 1)."""
    C = np.asarray(cov, float)
    p = np.asarray(perm, np.int64)
    F = np.array([1.0, -1.0, -1.0, 1.0]).reshape(2, 2)        # sign pattern of F C F
    out = np.empty_like(C)
    out[p] = C * F
    return out


def _fit(X: np.ndarray, uv: np.ndarray, cov: np.ndarray, like: Camera, cx: float, delta: float
         ) -> tuple[float, Camera, np.ndarray]:
    """Robust whitened pinhole fit (focal fixed): (cost C, camera, whitened residuals)."""
    W = whitening(cov)
    r = solve_pnp(X, uv, like.width, like.height, f_px=like.f, estimate_focal=False, cx=cx, cy=like.cy,
                  sigma_px=_cov_sigma_px(cov), huber_sigmas=None)
    cam = Camera(like.f, cx, like.cy, like.width, like.height)
    ph = _pinhole_proj(cam)
    R, t, _, e = refine_pose(lambda R_, t_, x_: ph(R_, t_, x_, X), r.camera.R, r.camera.t, uv, W, delta=delta,
                              jac=_pinhole_jac(cam, X))
    cam.R, cam.t = R, t
    c = float(_M["reject_k"])
    return float(np.sum(np.minimum(e * e, c * c))), cam, e


def _pose_jacobian(cam: Camera, X: np.ndarray) -> np.ndarray:
    """d u / d (omega, t) (n, 2, 6) of a pinhole camera; omega is the left rotation increment."""
    Xc = cam.to_camera(X)
    z = Xc[:, 2]
    A = np.zeros((len(Xc), 2, 3))
    A[:, 0, 0] = cam.f / z
    A[:, 1, 1] = cam.f / z
    A[:, 0, 2] = -cam.f * Xc[:, 0] / z ** 2
    A[:, 1, 2] = -cam.f * Xc[:, 1] / z ** 2
    S = np.zeros((len(Xc), 3, 3))
    S[:, 0, 1], S[:, 0, 2] = -Xc[:, 2], Xc[:, 1]
    S[:, 1, 0], S[:, 1, 2] = Xc[:, 2], -Xc[:, 0]
    S[:, 2, 0], S[:, 2, 1] = -Xc[:, 1], Xc[:, 0]
    return np.concatenate([-np.einsum("nij,njk->nik", A, S), A], axis=2)


def mirror_test(uv: Any, W: float, perm: Sequence[int], consensus_X: Any, noise_cov: Any, camera_init: Camera, *,
                is_front_camera: bool, all_views_front: bool, other_views_agree: bool,
                plane: tuple = (np.array([1.0, 0.0, 0.0]), 0.0), g_min: float = _M["g_min"],
                rel_front: float = _M["rel_front"], rel_other: float = _M["rel_other"]) -> MirrorDecision:
    """Mirror test of one view against the consensus shape (DESIGN D-10, 4.10).

    ``uv`` (N, 2) px as detected (NaN rows hidden); ``W`` image width px; ``perm`` the
    scheme's L/R label permutation; ``consensus_X`` (N, 3) mm, ideally the BA consensus
    *without* this view (DESIGN 4.10); ``noise_cov`` (N, 2, 2) px^2 of the view;
    ``camera_init`` gives focal, principal point and image size (its pose is not used);
    ``is_front_camera`` / ``all_views_front`` from EXIF (Q-FRONTCAM); ``other_views_agree``:
    at least two other views independently support the flip (UI pre-selection only).
    See the module docstring for the statistics and the decision rule.  Inputs are never
    modified.
    """
    uv = np.array(uv, dtype=float, copy=True)
    X = np.array(consensus_X, dtype=float, copy=True)
    cov = np.array(noise_cov, dtype=float, copy=True)
    perm = np.array(perm, dtype=np.int64, copy=True)
    N = len(uv)
    if X.shape != (N, 3) or cov.shape != (N, 2, 2) or perm.shape != (N,):
        raise ValueError("uv (N,2), consensus_X (N,3), noise_cov (N,2,2) and perm (N,) must agree")
    delta_h = float(_M["huber_delta"])
    rel = float(rel_front) if is_front_camera else float(rel_other)
    # as given
    vis0 = np.isfinite(uv).all(axis=1) & np.isfinite(X).all(axis=1) & np.isfinite(cov).all(axis=(1, 2))
    # flipped (labels permuted, u -> W - u, covariances reflected)
    uv1 = flip_uv(uv, float(W), perm)
    cov1 = flip_cov(cov, perm)
    vis1 = np.isfinite(uv1).all(axis=1) & np.isfinite(X).all(axis=1) & np.isfinite(cov1).all(axis=(1, 2))
    n_v = int(vis0.sum())
    if n_v < 6 or int(vis1.sum()) < 6:
        raise ValueError("mirror_test needs at least 6 visible landmarks")
    C0, cam0, _ = _fit(X[vis0], uv[vis0], cov[vis0], camera_init, float(camera_init.cx), delta_h)
    C1, cam1, _ = _fit(X[vis1], uv1[vis1], cov1[vis1], camera_init, float(W) - float(camera_init.cx), delta_h)
    gap = C0 - C1
    dlt = gap / C0 if C0 > 0 else 0.0
    # predicted detectability of a flip from the consensus asymmetry about the plane
    n_vec, d_off = np.asarray(plane[0], float), float(plane[1])
    A = 0.5 * (X - reflect(X[perm], n_vec, d_off))
    Wh = whitening(cov[vis0])
    w = np.einsum("nij,njk,nk->ni", Wh, projection_jacobians(cam0, X[vis0]), A[vis0]).reshape(-1)
    g_raw = float(w @ w)
    Jp = np.einsum("nij,njk->nik", Wh, _pose_jacobian(cam0, X[vis0])).reshape(-1, 6)
    w_perp = w - Jp @ np.linalg.lstsq(Jp, w, rcond=None)[0]
    g = float(w_perp @ w_perp)
    thr_gap = float(_M["gap_k"]) * math.sqrt(2.0 * n_v)
    margin = gap - thr_gap
    flags: list[str] = []
    if all_views_front:
        decision = "unverifiable"
    elif g < float(g_min):
        decision = "undetermined"
    elif dlt > rel and gap > thr_gap:
        decision = "suggest_flip"
    else:
        decision = "keep"
    if decision == "suggest_flip":
        flags.append("M-SUGGEST-FLIP")
    elif decision in ("undetermined", "unverifiable"):
        flags.append("M-" + decision.upper())
    pre = bool(decision == "suggest_flip" and dlt > float(_M["preselect_delta"])
               and (bool(is_front_camera) or bool(other_views_agree)))
    return MirrorDecision(delta=float(dlt), g=g, gap=float(gap), margin=float(margin), decision=decision,
                          preselect_flip=pre, C0=float(C0), C1=float(C1), g_raw=g_raw, n_v=n_v,
                          rel_threshold=rel,
                          camera=cam0, camera_flipped=cam1, flags=flags)


def project_mirror_status(decisions: Sequence[MirrorDecision], all_views_front: bool) -> dict:
    """Project-level mirror summary (DESIGN 4.10): ``{'status', 'suggested', 'undetermined'}``.

    status is 'unverifiable' for an all-selfie set (asymmetry claims must be flagged, H7),
    'suggest_flip' when any view suggests a flip, 'undetermined' when no view could be
    tested (every view undetermined), else 'keep'.
    """
    sug = [k for k, d in enumerate(decisions) if d.decision == "suggest_flip"]
    und = [k for k, d in enumerate(decisions) if d.decision == "undetermined"]
    if all_views_front:
        status = "unverifiable"
    elif sug:
        status = "suggest_flip"
    elif decisions and len(und) == len(decisions):
        status = "undetermined"
    else:
        status = "keep"
    return {"status": status, "suggested": sug, "undetermined": und}
