"""Similarity alignment (Umeyama 1991), numpy only."""
from __future__ import annotations

import numpy as np


def umeyama(src: np.ndarray, dst: np.ndarray, with_scale: bool = True,
            weights: np.ndarray | None = None) -> tuple[float, np.ndarray, np.ndarray]:
    """Least-squares similarity transform with dst ≈ s * R @ src + t.

    Works in any dimension (N, d). Optional per-point weights.
    Returns (s, R, t).
    """
    src = np.asarray(src, float)
    dst = np.asarray(dst, float)
    n, d = src.shape
    w = np.ones(n) if weights is None else np.asarray(weights, float)
    w = w / w.sum()
    mu_s = w @ src
    mu_d = w @ dst
    xs = src - mu_s
    xd = dst - mu_d
    cov = (xd * w[:, None]).T @ xs
    U, S, Vt = np.linalg.svd(cov)
    D = np.eye(d)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        D[-1, -1] = -1.0
    R = U @ D @ Vt
    if with_scale:
        var_s = float(w @ np.sum(xs * xs, axis=1))
        s = float(np.trace(np.diag(S) @ D) / var_s) if var_s > 0 else 1.0
    else:
        s = 1.0
    t = mu_d - s * R @ mu_s
    return s, R, t


def apply_similarity(X: np.ndarray, s: float, R: np.ndarray, t: np.ndarray) -> np.ndarray:
    return s * np.asarray(X, float) @ R.T + t


def procrustes_rmse(src: np.ndarray, dst: np.ndarray, with_scale: bool = True) -> float:
    """RMS distance after optimal similarity alignment of src onto dst."""
    s, R, t = umeyama(src, dst, with_scale)
    d = apply_similarity(src, s, R, t) - dst
    return float(np.sqrt(np.mean(np.sum(d * d, axis=1))))
