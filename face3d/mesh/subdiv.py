"""Catmull-Clark subdivision, limit stencils and limit-surface cage fitting (DESIGN D-21, 4.17; bl W4).

When the delivery mesh is a Multires (Catmull-Clark) cage, the surface the
artist sees is the *limit* surface, which shrinks convex features by about
``e^2/(6R)`` (0.1-0.4 mm on lips, nose tip and chin; research/blender/
face-retopology.md "Fit the limit surface", README table).  D-21 therefore fits
the cage ``C`` so that its limit positions ``S C`` interpolate the target.

Conventions
-----------
* Quad meshes only: ``faces`` is an ``(F, 4)`` int array of vertex indices,
  0-based, consistently oriented (CCW seen from outside for a closed mesh).
* Positions are float64 (any unit; the engine uses mm).
* An edge is *boundary* when exactly one face uses it, *interior* when two do;
  more than two raises ``ValueError`` (non-manifold).  A vertex is boundary
  when it lies on a boundary edge; vertices used by no face are *isolated*
  and are left where they are (identity rows).

Rules (Catmull & Clark 1978; limit stencils as in Halstead, Kass & DeRose 1993,
cited in face-retopology.md "Sources"; DESIGN 4.17):

* face point: mean of the face's 4 corners;
* edge point: ``(v0 + v1 + fp0 + fp1) / 4`` (interior), midpoint (boundary);
* vertex point, interior of valence ``n``: ``(F + 2R + (n - 3) P) / n`` with ``F``
  the mean of adjacent face points and ``R`` the mean of incident edge midpoints;
  boundary: cubic B-spline rule ``(1/8, 6/8, 1/8)`` of (prev, self, next) along
  the boundary;
* limit position, interior: ``v_inf = (n^2 v + 4 sum e_j + sum f_j) / (n (n + 5))``
  with ``e_j`` the edge neighbours and ``f_j`` the face-diagonal neighbours
  (regular ``n = 4``: 16/36, 4/36, 1/36); boundary: ``(1/6, 4/6, 1/6)`` of the
  boundary neighbours (uniform cubic B-spline limit).

Subdivided vertex order is ``[vertex points (V), edge points (E), face points
(F)]``, so an original vertex keeps its index at every level; edges are the
sorted unique ``(lo, hi)`` pairs; child quads are emitted face-major,
corner-minor as ``(v, e_next, f, e_prev)``, which keeps the parent orientation.

Cage fit (DESIGN 4.17): ``C = argmin ||S C - T||^2 + mu ||L (C - T)||^2`` with
``L`` the unit-weight graph Laplacian (degree minus adjacency over mesh edges)
and ``mu = 1e-5`` (``subdiv.cage_fit_mu``), solved per coordinate by
Jacobi-preconditioned CG on the normal equations ``(S^T S + mu L^T L) C =
S^T T + mu L^T L T``.  Design verification on the 1,538-vertex cube-sphere head
(mean edge ~8.7 mm): cond(S) ~ 9, naive-cage shrink RMS 0.38 mm (max 0.93),
fitted RMS 0.0002 mm (max 0.0012).  Measured by WP-13 on the current WP-08
``build_procedural_head(n=16)`` (1,538 vertices, mean edge 8.9 mm, surface-mode
landmarks): cond(S) = 9.14; naive RMS 0.52 mm (max 7.6 mm at a sharp nose-tip
vertex); fitted RMS 0.0009 mm (max 0.0085 mm).  The fitted residual is entirely
the ``mu`` bias (``mu = 0`` interpolates to ~1e-9 mm), so it grows where the
cage must move far from the target (sharp features, open corners).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..core.config import Default, register_defaults
from .laplacian import uniform_laplacian
from .sparse import Sparse, cg

__all__ = [
    "quad_one_rings", "is_closed", "catmull_clark", "limit_stencil_matrix", "limit_positions",
    "fit_cage_to_limit", "subdivide_levels", "quad_edges", "SUBDIV_DEFAULTS",
]

_NEW = "\U0001F195"      # introduced by this design, uncalibrated
_DERIVED = "\U0001F522"  # derived / numerically verified

SUBDIV_DEFAULTS = register_defaults("subdiv", {
    # DESIGN 4.17 "Limit stencils": mu = 1e-5; verified on the 1,538-vertex cube-sphere head
    # (fitted RMS 0.0002 mm, max 0.0012 mm).
    "cage_fit_mu": Default(1e-5, _DERIVED, "DESIGN 4.17 limit stencils (mu = 1e-5, verified on the "
                           "1,538-vertex cube-sphere head; bl W4)", "", (0.0, None)),
    # WP-13 spec: CG stopping tolerance (relative residual of the normal equations).
    "cage_fit_tol": Default(1e-10, _NEW, "WP-13 spec (relative CG residual of the cage-fit normal "
                            "equations)", "", (0.0, 1e-3)),
    # WP-13 implementation cap on CG iterations (cond(S^T S) ~ 81 needs ~100).
    "cage_fit_max_iter": Default(2000, _NEW, "WP-13 implementation (CG iteration cap; cond(S^T S) ~ 81 "
                                 "per DESIGN 4.17)", "", (1, None)),
})


# ============================================================================ topology
def _quads(faces, n_verts: int | None = None) -> np.ndarray:
    F = np.asarray(faces)
    if F.size == 0:
        return np.zeros((0, 4), np.int64)
    if F.ndim != 2 or F.shape[1] != 4:
        raise ValueError(f"faces must be an (F, 4) quad array, got shape {F.shape}")
    if F.dtype.kind not in "iu":
        raise ValueError("faces must hold integer vertex indices")
    F = np.ascontiguousarray(F, dtype=np.int64)
    if F.min() < 0 or (n_verts is not None and F.max() >= n_verts):
        raise ValueError("face index out of range")
    s = np.sort(F, axis=1)
    if np.any(s[:, 1:] == s[:, :-1]):
        raise ValueError("degenerate quad (repeated vertex)")
    return F


@dataclass(frozen=True)
class _Topology:
    faces: np.ndarray           # (F, 4)
    edges: np.ndarray           # (E, 2) sorted unique (lo, hi)
    he_edge: np.ndarray         # (F, 4) edge id of the half-edge (F[f, i], F[f, i+1])
    edge_nfaces: np.ndarray     # (E,) 1 = boundary, 2 = interior
    valence: np.ndarray         # (V,) incident edges
    vert_nfaces: np.ndarray     # (V,) incident faces
    boundary_vertex: np.ndarray  # (V,) bool
    interior_vertex: np.ndarray  # (V,) bool (has faces, not on the boundary)


def _topology(n_verts: int, faces) -> _Topology:
    F = _quads(faces, n_verts)
    n = int(n_verts)
    a = F.reshape(-1)
    b = F[:, [1, 2, 3, 0]].reshape(-1)
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    key = lo * max(n, 1) + hi
    uniq, inv = np.unique(key, return_inverse=True)
    inv = inv.reshape(-1)
    edges = np.stack([uniq // max(n, 1), uniq % max(n, 1)], axis=1).astype(np.int64)
    edge_nfaces = np.bincount(inv, minlength=len(uniq))
    if np.any(edge_nfaces > 2):
        e = edges[np.flatnonzero(edge_nfaces > 2)[0]]
        raise ValueError(f"non-manifold edge {tuple(int(x) for x in e)} shared by more than two faces")
    valence = np.bincount(edges.reshape(-1), minlength=n)
    vert_nfaces = np.bincount(a, minlength=n)
    bnd_edges = edges[edge_nfaces == 1]
    boundary_vertex = np.zeros(n, bool)
    boundary_vertex[bnd_edges.reshape(-1)] = True
    interior_vertex = (vert_nfaces > 0) & ~boundary_vertex
    if np.any(valence[interior_vertex] != vert_nfaces[interior_vertex]):
        v = int(np.flatnonzero(interior_vertex & (valence != vert_nfaces))[0])
        raise ValueError(f"non-manifold interior vertex {v}")
    bcount = np.bincount(bnd_edges.reshape(-1), minlength=n)
    if np.any(bcount[boundary_vertex] != 2):
        v = int(np.flatnonzero(boundary_vertex & (bcount != 2))[0])
        raise ValueError(f"non-manifold boundary vertex {v} ({int(bcount[v])} boundary edges)")
    return _Topology(F, edges, inv.reshape(-1, 4), edge_nfaces, valence, vert_nfaces,
                     boundary_vertex, interior_vertex)


def quad_edges(faces) -> np.ndarray:
    """Sorted unique undirected edges ``(E, 2)`` of a quad mesh."""
    F = _quads(faces)
    if len(F) == 0:
        return np.zeros((0, 2), np.int64)
    return _topology(int(F.max()) + 1, F).edges


def quad_one_rings(n_verts: int, faces) -> list[tuple[list[int], list[int]]]:
    """Per vertex ``(edge_neighbours, diagonal_neighbours)`` of a quad mesh.

    ``edge_neighbours`` are the distinct vertices sharing an edge with the vertex;
    ``diagonal_neighbours`` holds, for every incident quad, the corner opposite the
    vertex (one entry per incident face, so a repeat is kept).  Both lists are in
    order of first appearance in ``faces`` (deterministic).  For an interior
    vertex of valence ``n`` both lists have length ``n``.
    """
    F = _quads(faces, n_verts)
    edge_nb: list[list[int]] = [[] for _ in range(int(n_verts))]
    seen: list[set[int]] = [set() for _ in range(int(n_verts))]
    diag_nb: list[list[int]] = [[] for _ in range(int(n_verts))]
    for f in F.tolist():
        for i in range(4):
            v = f[i]
            for u in (f[(i + 1) % 4], f[(i + 3) % 4]):
                if u not in seen[v]:
                    seen[v].add(u)
                    edge_nb[v].append(u)
            diag_nb[v].append(f[(i + 2) % 4])
    return [(edge_nb[v], diag_nb[v]) for v in range(int(n_verts))]


def is_closed(faces) -> bool:
    """True when every edge of the quad mesh is shared by exactly two faces."""
    F = _quads(faces)
    if len(F) == 0:
        return False
    a = F.reshape(-1)
    b = F[:, [1, 2, 3, 0]].reshape(-1)
    e = np.sort(np.stack([a, b], axis=1), axis=1)
    _, counts = np.unique(e, axis=0, return_counts=True)
    return bool(np.all(counts == 2))


# ============================================================================ subdivision
def catmull_clark(V, faces) -> tuple[np.ndarray, np.ndarray]:
    """One Catmull-Clark step of a quad mesh: ``(V1, faces1)``.

    ``V1`` is ``(V + E + F, 3)`` ordered ``[vertex points, edge points, face points]``;
    ``faces1`` is ``(4F, 4)`` with child ``(v, e_next, f, e_prev)`` per parent corner
    (same orientation as the parent).  Rules in the module docstring.
    """
    P = np.asarray(V, dtype=np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError(f"V must be (n, 3), got {P.shape}")
    n = len(P)
    T = _topology(n, faces)
    F, E = T.faces, T.edges
    nF, nE = len(F), len(E)
    FP = P[F].mean(axis=1)
    he_face = np.repeat(np.arange(nF), 4)
    he_edge = T.he_edge.reshape(-1)
    # Edge points.
    efp = np.zeros((nE, 3))
    np.add.at(efp, he_edge, FP[he_face])
    mid = 0.5 * (P[E[:, 0]] + P[E[:, 1]])
    EP = mid.copy()
    inner = T.edge_nfaces == 2
    EP[inner] = 0.25 * (P[E[inner, 0]] + P[E[inner, 1]] + efp[inner])
    # Vertex points.
    VP = P.copy()
    iv = T.interior_vertex
    if np.any(iv):
        fsum = np.zeros((n, 3))
        np.add.at(fsum, F.reshape(-1), FP[he_face])
        rsum = np.zeros((n, 3))
        np.add.at(rsum, E[:, 0], mid)
        np.add.at(rsum, E[:, 1], mid)
        k = T.valence[iv].astype(np.float64)[:, None]
        Fm = fsum[iv] / T.vert_nfaces[iv][:, None]
        Rm = rsum[iv] / k
        VP[iv] = (Fm + 2.0 * Rm + (k - 3.0) * P[iv]) / k
    bv = T.boundary_vertex
    if np.any(bv):
        be = E[~inner]
        bsum = np.zeros((n, 3))
        np.add.at(bsum, be[:, 0], P[be[:, 1]])
        np.add.at(bsum, be[:, 1], P[be[:, 0]])
        VP[bv] = 0.75 * P[bv] + 0.125 * bsum[bv]
    V1 = np.concatenate([VP, EP, FP], axis=0)
    e_next = T.he_edge
    e_prev = np.roll(T.he_edge, 1, axis=1)
    fidx = np.broadcast_to((n + nE + np.arange(nF))[:, None], (nF, 4))
    faces1 = np.stack([F, n + e_next, fidx, n + e_prev], axis=2).reshape(-1, 4).astype(np.int64)
    return V1, faces1


def subdivide_levels(C, faces, levels: int) -> tuple[np.ndarray, np.ndarray]:
    """``levels`` Catmull-Clark steps (Multires L``levels``); level 0 returns copies."""
    levels = int(levels)
    if levels < 0:
        raise ValueError("levels must be >= 0")
    V = np.array(C, dtype=np.float64, copy=True)
    F = _quads(faces, len(V)).copy()
    for _ in range(levels):
        V, F = catmull_clark(V, F)
    return V, F


# ============================================================================ limit stencils
def limit_stencil_matrix(n_verts: int, faces) -> Sparse:
    """Sparse ``(n, n)`` Catmull-Clark limit-position operator ``S`` (rows sum to 1).

    Interior vertex of valence ``n``: ``n/(n+5)`` on itself (= n^2/(n(n+5))),
    ``4/(n(n+5))`` per edge neighbour, ``1/(n(n+5))`` per face-diagonal neighbour.
    Boundary vertex: ``4/6`` on itself, ``1/6`` per boundary neighbour.  Isolated
    vertex: identity row.
    """
    n = int(n_verts)
    T = _topology(n, faces)
    F, E = T.faces, T.edges
    iv, bv = T.interior_vertex, T.boundary_vertex
    val = T.valence.astype(np.float64)
    denom = np.where(iv, val * (val + 5.0), 1.0)
    rows: list[np.ndarray] = []
    cols: list[np.ndarray] = []
    vals: list[np.ndarray] = []

    def add(r: np.ndarray, c: np.ndarray, w: np.ndarray) -> None:
        rows.append(r)
        cols.append(c)
        vals.append(np.broadcast_to(np.asarray(w, np.float64), r.shape))

    # Centre weights.
    idx = np.arange(n)
    add(idx, idx, np.where(iv, val * val / denom, np.where(bv, 4.0 / 6.0, 1.0)))
    # Edge neighbours of interior vertices.
    for s, t in ((0, 1), (1, 0)):
        m = iv[E[:, s]]
        add(E[m, s], E[m, t], 4.0 / denom[E[m, s]])
    # Face diagonals of interior vertices (one entry per incident face).
    v = F.reshape(-1)
    d = F[:, [2, 3, 0, 1]].reshape(-1)
    m = iv[v]
    add(v[m], d[m], 1.0 / denom[v[m]])
    # Boundary neighbours of boundary vertices.
    be = E[T.edge_nfaces == 1]
    for s, t in ((0, 1), (1, 0)):
        add(be[:, s], be[:, t], 1.0 / 6.0)
    return Sparse(np.concatenate(rows), np.concatenate(cols), np.concatenate(vals), (n, n))


def limit_positions(V, faces) -> np.ndarray:
    """Catmull-Clark limit positions of the cage vertices, ``S V`` (same units as ``V``)."""
    P = np.asarray(V, dtype=np.float64)
    return limit_stencil_matrix(len(P), faces) @ P


def fit_cage_to_limit(targets, faces, mu: float | None = None, x0=None, tol: float | None = None,
                      max_iter: int | None = None) -> np.ndarray:
    """Cage ``C`` whose Catmull-Clark limit interpolates ``targets`` (DESIGN 4.17, D-21; bl W4).

    Minimises ``||S C - T||^2 + mu ||L (C - T)||^2`` (``S`` limit stencils, ``L``
    unit-weight graph Laplacian over the mesh edges) per coordinate with
    Jacobi-preconditioned :func:`face3d.mesh.sparse.cg` on the normal equations.

    ``targets`` (n, 3), any unit (mm in the engine); ``mu`` defaults to 1e-5
    (``subdiv.cage_fit_mu``), ``tol`` to 1e-10 (``subdiv.cage_fit_tol``, relative
    residual), ``max_iter`` to 2000; ``x0`` (n, 3) is the CG start (default: the
    naive cage ``targets``).  Raises ``RuntimeError`` if CG does not converge.
    """
    Tg = np.asarray(targets, dtype=np.float64)
    if Tg.ndim != 2 or Tg.shape[1] != 3:
        raise ValueError(f"targets must be (n, 3), got {Tg.shape}")
    mu = SUBDIV_DEFAULTS.cage_fit_mu.value if mu is None else float(mu)
    tol = SUBDIV_DEFAULTS.cage_fit_tol.value if tol is None else float(tol)
    max_iter = SUBDIV_DEFAULTS.cage_fit_max_iter.value if max_iter is None else int(max_iter)
    if not (np.isfinite(mu) and mu >= 0.0):
        raise ValueError(f"mu must be finite and >= 0, got {mu}")
    n = len(Tg)
    T = _topology(n, faces)
    S = limit_stencil_matrix(n, T.faces)
    St = S.T
    L = uniform_laplacian(n, T.edges)  # symmetric: L^T = L

    def matvec(x: np.ndarray) -> np.ndarray:
        return St @ (S @ x) + mu * (L @ (L @ x))

    b = St @ Tg + mu * (L @ (L @ Tg))
    # Jacobi preconditioner: diag(S^T S) = column sums of S^2; diag(L^T L) = deg^2 + deg.
    diag = np.bincount(S.cols, weights=S.vals ** 2, minlength=n)
    deg = T.valence.astype(np.float64)
    diag = diag + mu * (deg * deg + deg)
    start = Tg.copy() if x0 is None else np.asarray(x0, dtype=np.float64)
    if start.shape != Tg.shape:
        raise ValueError(f"x0 must have shape {Tg.shape}, got {start.shape}")
    C, it = cg(matvec, b, x0=start, precond=diag, tol=tol, max_iter=max_iter)
    if it >= max_iter:
        raise RuntimeError(f"cage fit CG did not converge in {max_iter} iterations (tol {tol:g})")
    return C
