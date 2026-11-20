"""Reduced-space smooth deformation (fast on 50k-vertex heads, numpy only).

The displacement field is a sum of Gaussian RBFs centred on k vertices chosen by
farthest-point sampling:  d(x) = sum_j w_j * exp(-|x - c_j|^2 / (2 s^2)).
Fitting solves the k x k system
    (Phi_m^T W Phi_m + lam * Phi_cc) w = Phi_m^T W d_m
i.e. weighted least squares on the constraints plus the RKHS-norm smoothness
penalty. Unlike the global biharmonic warp, Gaussian fields decay away from
the constraints, so regions without evidence stay where they were.
"""
from __future__ import annotations

import numpy as np


def farthest_point_sample(V: np.ndarray, k: int, start: int = 0) -> np.ndarray:
    V = np.asarray(V, float)
    k = min(k, len(V))
    idx = np.empty(k, np.int64)
    idx[0] = start
    d = np.sum((V - V[start]) ** 2, axis=1)
    for i in range(1, k):
        idx[i] = int(np.argmax(d))
        d = np.minimum(d, np.sum((V - V[idx[i]]) ** 2, axis=1))
    return idx


def _gauss(A: np.ndarray, C: np.ndarray, s: float) -> np.ndarray:
    d2 = np.sum(A * A, 1)[:, None] + np.sum(C * C, 1)[None, :] - 2.0 * A @ C.T
    return np.exp(-np.maximum(d2, 0.0) / (2.0 * s * s))


class ReducedDeformer:
    def __init__(self, V: np.ndarray, n_centers: int = 600, width_factor: float = 1.6):
        self.V = np.asarray(V, float)
        self.centers_idx = farthest_point_sample(self.V, n_centers)
        self.C = self.V[self.centers_idx]
        # Mean nearest-centre spacing sets the kernel width.
        D = np.sqrt(np.maximum(np.sum(self.C ** 2, 1)[:, None] + np.sum(self.C ** 2, 1)[None] - 2 * self.C @ self.C.T, 0))
        np.fill_diagonal(D, np.inf)
        self.spacing = float(np.median(D.min(1)))
        self.s = width_factor * self.spacing
        self.Kcc = _gauss(self.C, self.C, self.s)

    def solve(self, idx: np.ndarray, disp: np.ndarray, weights: np.ndarray | float = 1.0,
              smoothness: float = 1e-2) -> np.ndarray:
        """Displacement for every vertex given target displacements at vertices `idx`."""
        idx = np.asarray(idx, np.int64)
        w = np.broadcast_to(np.asarray(weights, float), idx.shape)
        Phi = _gauss(self.V[idx], self.C, self.s)
        A = Phi.T @ (Phi * w[:, None]) + smoothness * float(w.mean()) * self.Kcc
        A[np.diag_indices_from(A)] += 1e-9 * np.trace(A) / len(A)
        coef = np.linalg.solve(A, Phi.T @ (np.asarray(disp, float) * w[:, None]))
        return self.apply(coef)

    def apply(self, coef: np.ndarray, chunk: int = 8000) -> np.ndarray:
        out = np.empty((len(self.V), coef.shape[1]))
        for i in range(0, len(self.V), chunk):
            out[i:i + chunk] = _gauss(self.V[i:i + chunk], self.C, self.s) @ coef
        return out
