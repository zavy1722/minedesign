"""Landmark-driven smooth deformation with radial basis functions.

The default kernel phi(r) = r is the biharmonic (thin-plate) spline in 3D: it
minimises bending energy, which is the standard choice for warping a template
head so that its landmarks land on target positions while the surface between
landmarks deforms smoothly (as in Wrap-style template fitting).
"""
from __future__ import annotations

import numpy as np


def _kernel(r: np.ndarray, kind: str, eps: float) -> np.ndarray:
    if kind == "biharmonic":
        return r
    if kind == "triharmonic":
        return r ** 3
    if kind == "gaussian":
        return np.exp(-(r / eps) ** 2)
    if kind == "multiquadric":
        return np.sqrt(r * r + eps * eps)
    raise ValueError(f"unknown kernel {kind!r}")


def _pairwise(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    d2 = np.sum(a * a, 1)[:, None] + np.sum(b * b, 1)[None, :] - 2.0 * a @ b.T
    return np.sqrt(np.maximum(d2, 0.0))


class RBFWarp:
    """Fit once on (source landmarks -> target landmarks), then apply to any points.

    `smoothing` > 0 turns exact interpolation into regularised approximation, which
    is what you want with noisy landmarks (e.g. from a detector).
    """

    def __init__(self, src: np.ndarray, dst: np.ndarray, kind: str = "biharmonic",
                 smoothing: float = 0.0, eps: float = 1.0):
        src = np.asarray(src, float)
        dst = np.asarray(dst, float)
        if src.shape != dst.shape:
            raise ValueError("src and dst must have the same shape")
        n, d = src.shape
        self.src, self.kind, self.eps = src, kind, eps
        Phi = _kernel(_pairwise(src, src), kind, eps)
        P = np.hstack([np.ones((n, 1)), src])
        A = np.zeros((n + d + 1, n + d + 1))
        # Smoothing splines solve (K_cpd + lam I) w + P a = y with K_cpd the
        # conditionally POSITIVE definite form of the kernel. In 3D, r and the
        # multiquadric are CPD only with a minus sign (-r, -sqrt(r^2+c^2)), so for
        # them the system written with phi itself is (Phi - lam I). r^3 (CPD order 2)
        # and the Gaussian (PD) keep +lam. Using +lam with phi = r makes the system
        # indefinite and can blow landmark errors up to hundreds of mm.
        sign = -1.0 if kind in ("biharmonic", "multiquadric") else 1.0
        A[:n, :n] = Phi + sign * smoothing * np.eye(n)
        A[:n, n:] = P
        A[n:, :n] = P.T
        b = np.zeros((n + d + 1, d))
        b[:n] = dst - src  # fit the displacement field
        sol = np.linalg.lstsq(A, b, rcond=None)[0]
        self.w = sol[:n]
        self.a = sol[n:]

    def displacement(self, X: np.ndarray, chunk: int = 20000) -> np.ndarray:
        X = np.asarray(X, float)
        out = np.empty_like(X)
        for i in range(0, len(X), chunk):
            x = X[i:i + chunk]
            Phi = _kernel(_pairwise(x, self.src), self.kind, self.eps)
            out[i:i + chunk] = Phi @ self.w + np.hstack([np.ones((len(x), 1)), x]) @ self.a
        return out

    def __call__(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, float)
        return X + self.displacement(X)
