"""Camera pose + focal length from 2D-3D correspondences (perspective-n-point).

Faces are shallow compared with typical camera distances, so focal length and
distance are strongly coupled (the classic "focal/depth ambiguity"). The solver
therefore:
  1. initialises pose from a scaled-orthographic (affine) fit,
  2. refines (rotation, translation, log focal) with Levenberg-Marquardt,
  3. tries several focal hypotheses when focal length is unknown, and
  4. accepts an optional log-normal prior on focal length (e.g. from EXIF).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..geometry.camera import Camera, focal_px_from_35mm
from ..geometry.rotations import nearest_rotation, rodrigues, rotation_to_rvec
from .lm import levenberg_marquardt

# 35 mm-equivalent focal lengths tried when focal length is unknown: phone ultrawide, phone wide,
# phone tele, normal, portrait and long portrait lenses.
DEFAULT_F35_HYPOTHESES = (13.0, 24.0, 35.0, 50.0, 85.0, 135.0, 200.0)


@dataclass
class PnPResult:
    camera: Camera
    rmse_px: float
    residuals_px: np.ndarray  # (N,) per-point reprojection error
    focal_estimated: bool


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


def _project(params: np.ndarray, X: np.ndarray, cx: float, cy: float, f_fixed: float | None) -> np.ndarray:
    R = rodrigues(params[:3])
    t = params[3:6]
    f = f_fixed if f_fixed is not None else float(np.exp(params[6]))
    Xc = X @ R.T + t
    z = Xc[:, 2:3]
    z = np.where(np.abs(z) < 1e-9, 1e-9, z)
    return Xc[:, :2] / z * f + np.array([cx, cy])


def solve_pnp(X: np.ndarray, uv: np.ndarray, width: int, height: int, *,
              f_px: float | None = None, estimate_focal: bool | None = None,
              f_prior_px: float | None = None, f_prior_log_sigma: float = 0.35,
              f35_hypotheses: tuple[float, ...] = DEFAULT_F35_HYPOTHESES,
              weights: np.ndarray | None = None, huber_px: float | None = 3.0,
              cx: float | None = None, cy: float | None = None) -> PnPResult:
    """Solve camera pose (and optionally focal length) from N 3D-2D matches.

    Parameters
    ----------
    X, uv : (N,3) model points and (N,2) observed pixels.
    f_px : known focal length in pixels (fixes focal unless estimate_focal=True).
    f_prior_px : soft prior on focal length (e.g. from EXIF); log-normal with
        `f_prior_log_sigma` (0.35 ≈ ±40 %).
    weights : per-landmark confidence weights.
    huber_px : Huber threshold in pixels for robustness to bad landmarks (None = L2).
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

    if f_px is not None:
        f_inits = [f_px]
    elif f_prior_px is not None:
        f_inits = [f_prior_px]
    else:
        f_inits = [focal_px_from_35mm(f35, width, height) for f35 in f35_hypotheses]

    best: tuple[float, np.ndarray] | None = None
    for f0 in f_inits:
        R0, t0 = affine_pose_init(X, uv, f0, cx, cy)
        if t0 @ t0 <= 0 or (X @ R0.T + t0)[:, 2].min() <= 0:
            continue
        p0 = np.concatenate([rotation_to_rvec(R0), t0] + ([[np.log(f0)]] if estimate_focal else []))
        f_fixed = None if estimate_focal else f0
        irls_w = np.ones(n)
        p = p0
        for _ in range(4 if huber_px else 1):
            sw = np.sqrt(w * irls_w)

            def resid(q: np.ndarray, sw=sw) -> np.ndarray:
                r = ((_project(q, X, cx, cy, f_fixed) - uv) * sw[:, None]).ravel()
                if estimate_focal and f_prior_px is not None:
                    r = np.append(r, (q[6] - np.log(f_prior_px)) / f_prior_log_sigma)
                return r

            p = levenberg_marquardt(resid, p, max_iter=200).x
            if huber_px:
                e = np.linalg.norm(_project(p, X, cx, cy, f_fixed) - uv, axis=1)
                irls_w = np.where(e <= huber_px, 1.0, huber_px / np.maximum(e, 1e-12))
        e = np.linalg.norm(_project(p, X, cx, cy, f_fixed) - uv, axis=1)
        # Robust score used to compare hypotheses.
        score = float(np.sum(w * (np.minimum(e, huber_px) ** 2 if huber_px else e ** 2)))
        if estimate_focal and f_prior_px is not None:
            score += float(((p[6] - np.log(f_prior_px)) / f_prior_log_sigma) ** 2)
        Xc_ok = (X @ rodrigues(p[:3]).T + p[3:6])[:, 2].min() > 0
        if Xc_ok and (best is None or score < best[0] - 1e-9):
            best = (score, p)

    if best is None:
        raise RuntimeError("PnP failed: no hypothesis put the points in front of the camera")
    p = best[1]
    f = float(np.exp(p[6])) if estimate_focal else f_inits[0]
    cam = Camera(f=f, cx=cx, cy=cy, width=width, height=height, R=rodrigues(p[:3]), t=p[3:6].copy())
    e = np.linalg.norm(cam.project(X) - uv, axis=1)
    return PnPResult(cam, float(np.sqrt(np.mean(e ** 2))), e, estimate_focal)
