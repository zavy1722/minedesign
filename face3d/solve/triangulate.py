"""Multi-view triangulation of landmarks with known cameras."""
from __future__ import annotations

import numpy as np

from ..geometry.camera import Camera
from .lm import levenberg_marquardt


def triangulate_dlt(cams: list[Camera], uvs: list[np.ndarray]) -> np.ndarray:
    """Linear (DLT) triangulation of one point seen in >= 2 views."""
    rows = []
    for cam, uv in zip(cams, uvs):
        P = cam.K @ np.hstack([cam.R, cam.t[:, None]])
        u, v = uv
        rows.append(u * P[2] - P[0])
        rows.append(v * P[2] - P[1])
    A = np.asarray(rows)
    # Normalise rows for conditioning.
    A /= np.linalg.norm(A, axis=1, keepdims=True)
    _, _, Vt = np.linalg.svd(A)
    Xh = Vt[-1]
    return Xh[:3] / Xh[3]


def triangulate_points(cams: list[Camera], obs: np.ndarray, visible: np.ndarray | None = None,
                       refine: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """Triangulate N points from V views.

    obs : (V, N, 2) pixel observations.
    visible : (V, N) bool mask (default: all visible).
    Returns (points (N,3) with NaN where < 2 views, per-point RMS reprojection error).
    """
    obs = np.asarray(obs, float)
    V, N, _ = obs.shape
    vis = np.ones((V, N), bool) if visible is None else np.asarray(visible, bool)
    X = np.full((N, 3), np.nan)
    err = np.full(N, np.nan)
    for i in range(N):
        views = np.flatnonzero(vis[:, i])
        if len(views) < 2:
            continue
        cs = [cams[v] for v in views]
        us = [obs[v, i] for v in views]
        x0 = triangulate_dlt(cs, us)
        if refine:
            def resid(x, cs=cs, us=us):
                return np.concatenate([c.project(x[None])[0] - u for c, u in zip(cs, us)])
            x0 = levenberg_marquardt(resid, x0, max_iter=50).x
        X[i] = x0
        e = np.array([np.linalg.norm(c.project(x0[None])[0] - u) for c, u in zip(cs, us)])
        err[i] = float(np.sqrt(np.mean(e ** 2)))
    return X, err
