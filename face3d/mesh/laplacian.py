"""Cotangent Laplacian and Laplacian-coordinates surface deformation.

`laplacian_deform` solves
    min_x  || L (x - x0) ||_M^2  +  sum_c w_c || x_c - p_c ||^2
i.e. it finds the smoothest (bilaplacian-energy) displacement field that moves
constraint vertices to their targets. Starting from an RBF warp, it pulls the
surface onto local constraints without disturbing the rest of the shape.
"""
from __future__ import annotations

import numpy as np

from .core import Mesh
from .sparse import Sparse, cg


def cotan_laplacian(V: np.ndarray, tris: np.ndarray, clamp: float = 1e3) -> tuple[Sparse, np.ndarray]:
    """Return (L, mass) with L positive semi-definite (L = D - W) and lumped
    barycentric vertex areas `mass`."""
    V = np.asarray(V, float)
    n = len(V)
    rows, cols, vals = [], [], []
    for k in range(3):
        i, j, o = tris[:, (k + 1) % 3], tris[:, (k + 2) % 3], tris[:, k]
        a = V[i] - V[o]
        b = V[j] - V[o]
        cross = np.linalg.norm(np.cross(a, b), axis=1)
        cot = np.einsum("ij,ij->i", a, b) / np.maximum(cross, 1e-12)
        w = 0.5 * np.clip(cot, -clamp, clamp)
        rows += [i, j, i, j]
        cols += [j, i, i, j]
        vals += [-w, -w, w, w]
    L = Sparse(np.concatenate(rows), np.concatenate(cols), np.concatenate(vals), (n, n))
    area = 0.5 * np.linalg.norm(np.cross(V[tris[:, 1]] - V[tris[:, 0]], V[tris[:, 2]] - V[tris[:, 0]]), axis=1)
    mass = np.zeros(n)
    for k in range(3):
        np.add.at(mass, tris[:, k], area / 3.0)
    return L, np.maximum(mass, 1e-12)


def uniform_laplacian(n: int, edges: np.ndarray) -> Sparse:
    i, j = edges[:, 0], edges[:, 1]
    ones = np.ones(len(edges))
    return Sparse(np.r_[i, j, i, j], np.r_[j, i, i, j], np.r_[-ones, -ones, ones, ones], (n, n))


def laplacian_deform(mesh: Mesh, idx: np.ndarray, targets: np.ndarray, weight: float | np.ndarray = 1e3,
                     x_init: np.ndarray | None = None, tol: float = 1e-7, max_iter: int = 3000,
                     cotan: bool = True) -> tuple[np.ndarray, int]:
    """Bilaplacian-smooth displacement moving vertices `idx` to `targets`.

    `weight` is a scalar or one weight per constraint (soft constraints).
    """
    V0 = mesh.vertices
    n = len(V0)
    tris = mesh.triangles()
    if cotan:
        L, mass = cotan_laplacian(V0, tris)
    else:
        L, mass = uniform_laplacian(n, mesh.edges()), np.ones(n)
    Minv = 1.0 / mass
    # Normalise so the constraint weight is scale-independent.
    scale = float(np.median(mass))
    idx = np.asarray(idx, np.int64)
    wv = np.broadcast_to(np.asarray(weight, float), idx.shape)
    w_c = np.zeros(n)
    np.add.at(w_c, idx, wv)
    rhs = np.zeros((n, 3))
    np.add.at(rhs, idx, wv[:, None] * (np.asarray(targets, float) - V0[idx]))

    def matvec(d: np.ndarray) -> np.ndarray:
        return scale * (L.T @ (Minv * (L @ d))) + w_c * d

    diag_LML = np.zeros(n)
    np.add.at(diag_LML, L.cols, (L.vals ** 2) * Minv[L.rows])
    precond = scale * diag_LML + w_c
    d0 = None if x_init is None else np.asarray(x_init, float) - V0
    d, it = cg(matvec, rhs, d0, precond, tol=tol, max_iter=max_iter)
    return V0 + d, it


def smooth(mesh: Mesh, iterations: int = 5, lam: float = 0.5, mask: np.ndarray | None = None) -> np.ndarray:
    """Uniform Laplacian smoothing (Taubin-free, simple); `mask` limits which vertices move."""
    V = mesh.vertices.copy()
    E = mesh.edges()
    n = len(V)
    deg = np.bincount(E.ravel(), minlength=n).astype(float)
    m = np.ones(n, bool) if mask is None else np.asarray(mask, bool)
    for _ in range(iterations):
        acc = np.zeros_like(V)
        np.add.at(acc, E[:, 0], V[E[:, 1]])
        np.add.at(acc, E[:, 1], V[E[:, 0]])
        avg = acc / np.maximum(deg, 1)[:, None]
        V[m] += lam * (avg[m] - V[m])
    return V
