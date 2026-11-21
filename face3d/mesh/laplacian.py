"""Cotangent Laplacian and Laplacian-coordinates surface deformation.

`laplacian_deform` solves
    min_x  || L (x - x0) ||_M^2  +  sum_c w_c || x_c - p_c ||^2
i.e. it finds the smoothest (bilaplacian-energy) displacement field that moves
constraint vertices to their targets. Starting from an RBF warp, it pulls the
surface onto local constraints without disturbing the rest of the shape.

With a per-vertex ``stiffness`` w_s (DESIGN 4.15 stage C; anat R5.9: lid margins 3.0,
lips 0.3, forehead 0.5) the smoothness energy becomes
    sum_v w_s[v] (L d)_v^2 / m_v ,
so displacing a stiff region costs more bending energy and it moves less under the
same pull.  Units: positions in mm; weights are relative to the bilaplacian energy
normalised by the median vertex area.
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


#: Largest mesh (vertices) that ``solver='auto'`` solves directly: the dense system needs
#: 8 V^2 bytes (288 MB at 6000) and O(V^3) time (WP-19 implementation choice).
DENSE_MAX_VERTS = 6000


def _dense_weighted_gram(L: Sparse, w: np.ndarray) -> np.ndarray:
    """Dense ``L^T diag(w) L`` (n, n) from the sparse rows of ``L`` (no dense product)."""
    n_r, n_c = L.shape
    order = np.argsort(L.rows, kind="stable")
    r, c, v = L.rows[order], L.cols[order], L.vals[order]
    counts = np.bincount(r, minlength=n_r)
    k = int(counts.max(initial=0))
    out = np.zeros((n_c, n_c))
    if k == 0:
        return out
    slot = np.arange(len(r)) - np.repeat(np.cumsum(counts) - counts, counts)
    C = np.zeros((n_r, k), np.int64)
    Vp = np.zeros((n_r, k))
    C[r, slot] = c
    Vp[r, slot] = v                                  # padded slots keep value 0
    W = (Vp * np.asarray(w, float)[:, None])[:, :, None] * Vp[:, None, :]
    np.add.at(out, (np.broadcast_to(C[:, :, None], W.shape).ravel(),
                    np.broadcast_to(C[:, None, :], W.shape).ravel()), W.ravel())
    return out


def laplacian_deform(mesh: Mesh, idx: np.ndarray, targets: np.ndarray, weight: float | np.ndarray = 1e3,
                     x_init: np.ndarray | None = None, tol: float = 1e-7, max_iter: int = 3000,
                     cotan: bool = True, stiffness: np.ndarray | None = None,
                     solver: str = "cg") -> tuple[np.ndarray, int]:
    """Bilaplacian-smooth displacement moving vertices `idx` to `targets`.

    `weight` is a scalar or one weight per constraint (soft constraints).
    `stiffness` (V,) > 0 multiplies the bilaplacian energy per vertex: the operator is
    ``d -> scale * L^T (w_s * Minv * (L d)) + w_c d`` (``None`` = 1 everywhere, the legacy
    behaviour).  ``solver``: ``'cg'`` (legacy default: Jacobi-preconditioned CG, any size),
    ``'dense'`` (assemble the (V, V) system and solve it directly; O(V^2) memory) or
    ``'auto'`` (dense up to :data:`DENSE_MAX_VERTS` vertices, else CG).  The bilaplacian is
    badly conditioned for CG (thousands of iterations on a few thousand vertices), so the
    direct solve is ~10x faster on template-sized meshes; a singular dense system falls
    back to CG.  Returns (new vertices (V, 3), CG iterations of the slowest coordinate;
    0 for a direct solve).
    """
    if solver not in ("cg", "dense", "auto"):
        raise ValueError(f"unknown solver {solver!r}")
    V0 = mesh.vertices
    n = len(V0)
    tris = mesh.triangles()
    if cotan:
        L, mass = cotan_laplacian(V0, tris)
    else:
        L, mass = uniform_laplacian(n, mesh.edges()), np.ones(n)
    Minv = 1.0 / mass
    if stiffness is not None:
        w_s = np.asarray(stiffness, float).reshape(-1)
        if w_s.shape != (n,) or not np.all(np.isfinite(w_s)) or np.any(w_s <= 0):
            raise ValueError(f"stiffness must be ({n},) finite and > 0")
        Minv = w_s * Minv          # w_s * M^-1: per-vertex weighted bilaplacian energy
    # Normalise so the constraint weight is scale-independent.
    scale = float(np.median(mass))
    idx = np.asarray(idx, np.int64)
    wv = np.broadcast_to(np.asarray(weight, float), idx.shape)
    w_c = np.zeros(n)
    np.add.at(w_c, idx, wv)
    rhs = np.zeros((n, 3))
    np.add.at(rhs, idx, wv[:, None] * (np.asarray(targets, float) - V0[idx]))

    if solver == "dense" or (solver == "auto" and n <= DENSE_MAX_VERTS):
        A = _dense_weighted_gram(L, scale * Minv)
        A[np.arange(n), np.arange(n)] += w_c
        try:
            d = np.linalg.solve(A, rhs)
            if np.all(np.isfinite(d)):
                return V0 + d, 0
        except np.linalg.LinAlgError:
            pass                                   # e.g. no constraint in a component: use CG

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
