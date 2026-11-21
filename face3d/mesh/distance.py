"""Exact point-to-triangle-mesh distance with a uniform-grid broad phase.

This is the distance used by the evaluation metrics (DESIGN §7.3, research
``reconstruction/benchmarks-metrics.md`` "Algorithmic implications"; rec EV-1):
exact closest points on the triangle surface (not nearest vertices, whose bias
is ≈0.35 × edge length, benchmarks-metrics Table 5), optionally signed with
angle-weighted pseudonormals.

Conventions
-----------
* Units are whatever the caller's vertices use (the engine uses millimetres,
  DESIGN §2.1 invariant 2). Distances are Euclidean in those units.
* ``tris`` is an (F,3) integer array of 0-based vertex indices.
* **Orientation**: triangles are assumed to be wound counter-clockwise when
  seen from *outside* the surface, i.e. the face normal (B−A)×(C−A) points
  outward. With that orientation :func:`mesh_orientation_volume` is positive
  for a closed mesh and :func:`point_to_mesh` with ``signed=True`` returns
  positive distances outside and negative distances inside. A mesh with the
  opposite winding gives the opposite signs.
* Barycentric coordinates ``bary`` = (u, v, w) satisfy Q = u·A + v·B + w·C and
  u + v + w = 1. When the closest point lies on a vertex or an edge the
  coordinates that are zero are *exactly* zero; the sign computation relies on
  this to choose the vertex, edge or face pseudonormal.
* Ties between triangles at exactly equal distance resolve to the lowest
  triangle id, in both the grid query and the brute-force reference.

Algorithms
----------
* Closest point on a triangle: vectorised Voronoi-region classification of
  Ericson, *Real-Time Collision Detection* (2005) §5.1.5 (vertex, edge and face
  regions). The face-region barycentrics use Ericson's signed sub-areas written
  with cross products, va = n·((B−P)×(C−P)) etc., which are equal (Lagrange
  identity) to his dot-product form d3·d6 − d5·d4 but keep their relative
  accuracy on thin triangles (error ∝ ε/ρ instead of ε/ρ², ρ = 2·area/L²).
* Degenerate triangles: when the Gram determinant |AB×AC|² that the face
  formula divides by is ≤ 1e-14·L⁴ (L = longest edge; i.e. 2·area/L² ≤ 1e-7,
  the "area < 1e-14 relative" rule of the WP-02 spec applied to that squared
  area measure) the triangle is treated as the closest of its three segments.
  The resulting distance error is at most the sliver height ≤ 1e-7·L. Zero
  area, collinear and coincident-vertex triangles never produce NaN.
* Broad phase: :class:`TriangleGrid`, a uniform grid whose cells store every
  triangle whose axis-aligned bounding box overlaps the cell. Queries search
  Chebyshev rings of cells outward and stop once a lower bound on the distance
  to anything in the unvisited rings exceeds the best distance found, so the
  result is exact (identical to the brute-force reference). Points farther
  outside the mesh bounding box than half its diagonal skip the rings and are
  screened against all triangles (same kernel, same result, less work).
* Sign: Bærentzen & Aanæs (2005), "Signed distance computation using the angle
  weighted pseudonormal", IEEE TVCG 11(3): sign of (P − Q)·n where n is the face
  normal for an interior closest point, the sum of the two adjacent unit face
  normals on an edge (the single face normal on a boundary edge) and the
  angle-weighted vertex normal on a vertex. The sign is exact for closed,
  consistently oriented, manifold meshes; on open meshes it is "above/below"
  the surface near it.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "closest_point_on_triangle",
    "TriangleGrid",
    "point_to_mesh",
    "brute_force_point_to_mesh",
    "mesh_orientation_volume",
    "angle_weighted_pseudonormals",
]

# Degeneracy threshold on |AB×AC|² / L⁴ (see module docstring; WP-02 spec).
DEGENERATE_REL = 1e-14
# Working-set bounds for vectorised evaluation (memory only; results unaffected).
_PAIR_BATCH = 1 << 18          # point-triangle pairs evaluated per numpy batch
_CELL_BATCH = 1 << 20          # (point, ring cell) candidates per batch
_MAX_CELLS = 1 << 21           # grid cells; the cell size grows to respect it
_DT_MAX_ITERS = 64             # chessboard distance transform iterations (a lower bound beyond)


# --------------------------------------------------------------------------- kernel
def _cpt_kernel(px, py, pz, ax, ay, az, bx, by, bz, cx, cy, cz):
    """Component-wise Ericson closest point. All inputs are (N,) float arrays.

    Returns (qx, qy, qz, d2, u, v, w).
    """
    abx, aby, abz = bx - ax, by - ay, bz - az
    acx, acy, acz = cx - ax, cy - ay, cz - az
    apx, apy, apz = px - ax, py - ay, pz - az
    bpx, bpy, bpz = px - bx, py - by, pz - bz
    cpx, cpy, cpz = px - cx, py - cy, pz - cz

    d1 = abx * apx + aby * apy + abz * apz
    d2 = acx * apx + acy * apy + acz * apz
    d3 = abx * bpx + aby * bpy + abz * bpz
    d4 = acx * bpx + acy * bpy + acz * bpz
    d5 = abx * cpx + aby * cpy + abz * cpz
    d6 = acx * cpx + acy * cpy + acz * cpz

    nx = aby * acz - abz * acy
    ny = abz * acx - abx * acz
    nz = abx * acy - aby * acx
    # Signed sub-areas (Ericson §5.1.5): vc = n·(AP×BP), vb = n·(CP×AP), va = n·(BP×CP).
    vc = (nx * (apy * bpz - apz * bpy) + ny * (apz * bpx - apx * bpz) + nz * (apx * bpy - apy * bpx))
    vb = (nx * (cpy * apz - cpz * apy) + ny * (cpz * apx - cpx * apz) + nz * (cpx * apy - cpy * apx))
    va = (nx * (bpy * cpz - bpz * cpy) + ny * (bpz * cpx - bpx * cpz) + nz * (bpx * cpy - bpy * cpx))

    m_a = (d1 <= 0) & (d2 <= 0)
    m_b = (d3 >= 0) & (d4 <= d3)
    m_ab = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
    m_c = (d6 >= 0) & (d5 <= d6)
    m_ac = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
    d43 = d4 - d3
    d56 = d5 - d6
    m_bc = (va <= 0) & (d43 >= 0) & (d56 >= 0)
    # np.select takes the first true condition: Ericson's sequential tests.
    conds = [m_a, m_b, m_ab, m_c, m_ac, m_bc]

    den = d1 - d3
    t_ab = d1 / np.where(den > 0, den, 1.0)
    den = d2 - d6
    t_ac = d2 / np.where(den > 0, den, 1.0)
    den = d43 + d56
    t_bc = d43 / np.where(den > 0, den, 1.0)
    den = va + vb + vc
    den = np.where(den > 0, den, 1.0)
    fu, fv, fw = va / den, vb / den, vc / den

    zero = np.zeros_like(d1)
    one = np.ones_like(d1)
    u = np.select(conds, [one, zero, 1.0 - t_ab, zero, 1.0 - t_ac, zero], fu)
    v = np.select(conds, [zero, one, t_ab, zero, zero, 1.0 - t_bc], fv)
    w = np.select(conds, [zero, zero, zero, one, t_ac, t_bc], fw)
    qx = np.select(conds, [ax, bx, ax + t_ab * abx, cx, ax + t_ac * acx, bx + t_bc * (cx - bx)],
                   ax + fv * abx + fw * acx)
    qy = np.select(conds, [ay, by, ay + t_ab * aby, cy, ay + t_ac * acy, by + t_bc * (cy - by)],
                   ay + fv * aby + fw * acy)
    qz = np.select(conds, [az, bz, az + t_ab * abz, cz, az + t_ac * acz, bz + t_bc * (cz - bz)],
                   az + fv * abz + fw * acz)

    # Degenerate triangles: closest of the three segments.
    ab2 = abx * abx + aby * aby + abz * abz
    ac2 = acx * acx + acy * acy + acz * acz
    bcx, bcy, bcz = cx - bx, cy - by, cz - bz
    bc2 = bcx * bcx + bcy * bcy + bcz * bcz
    lmax = np.maximum(np.maximum(ab2, ac2), bc2)
    n2 = nx * nx + ny * ny + nz * nz
    deg = n2 <= DEGENERATE_REL * lmax * lmax
    if np.any(deg):
        i = np.flatnonzero(deg)
        P = (px[i], py[i], pz[i])
        A = (ax[i], ay[i], az[i])
        B = (bx[i], by[i], bz[i])
        C = (cx[i], cy[i], cz[i])
        best = None
        for k, (S, E) in enumerate(((A, B), (B, C), (C, A))):
            sq, t, sd2 = _segment_kernel(P, S, E)
            if best is None:
                best = [sq, t, sd2, np.zeros(len(i), np.int64)]
                continue
            better = sd2 < best[2]
            for j in range(3):
                best[0][j][better] = sq[j][better]
            best[1][better] = t[better]
            best[2][better] = sd2[better]
            best[3][better] = k
        sq, t, _, which = best
        qx[i], qy[i], qz[i] = sq
        uu = np.where(which == 0, 1.0 - t, np.where(which == 1, 0.0, t))
        vv = np.where(which == 0, t, np.where(which == 1, 1.0 - t, 0.0))
        ww = np.where(which == 0, 0.0, np.where(which == 1, t, 1.0 - t))
        u[i], v[i], w[i] = uu, vv, ww

    ex, ey, ez = px - qx, py - qy, pz - qz
    dd = ex * ex + ey * ey + ez * ez
    return qx, qy, qz, dd, u, v, w


def _segment_kernel(P, S, E):
    """Closest point on segment S→E. Tuples of component arrays in, (Q, t, d2) out."""
    dx, dy, dz = E[0] - S[0], E[1] - S[1], E[2] - S[2]
    l2 = dx * dx + dy * dy + dz * dz
    num = (P[0] - S[0]) * dx + (P[1] - S[1]) * dy + (P[2] - S[2]) * dz
    t = np.clip(num / np.where(l2 > 0, l2, 1.0), 0.0, 1.0)
    t = np.where(l2 > 0, t, 0.0)
    q = [S[0] + t * dx, S[1] + t * dy, S[2] + t * dz]
    # Exact endpoints so that zero barycentrics stay exact.
    for j in range(3):
        q[j] = np.where(t == 1.0, E[j], np.where(t == 0.0, S[j], q[j]))
    ex, ey, ez = P[0] - q[0], P[1] - q[1], P[2] - q[2]
    return q, t, ex * ex + ey * ey + ez * ez


def closest_point_on_triangle(P: np.ndarray, A: np.ndarray, B: np.ndarray,
                              C: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Closest points Q on triangles (A, B, C) to points P, row by row.

    Parameters
    ----------
    P, A, B, C : (M,3) arrays (broadcastable to a common (M,3) shape).

    Returns
    -------
    Q : (M,3) closest points on the (closed) triangles.
    d2 : (M,) squared distances |P − Q|².
    bary : (M,3) barycentric coordinates (u, v, w) of Q; zeros are exact on
        vertex and edge regions.

    Ericson §5.1.5 region classification; degenerate triangles (Gram
    determinant ≤ 1e-14·L⁴) are handled as the closest of their segments.
    """
    P, A, B, C = np.broadcast_arrays(*(np.asarray(x, np.float64) for x in (P, A, B, C)))
    if P.ndim == 1:
        P, A, B, C = (x[None, :] for x in (P, A, B, C))
    P, A, B, C = (np.ascontiguousarray(x.reshape(-1, 3)) for x in (P, A, B, C))
    qx, qy, qz, d2, u, v, w = _cpt_kernel(P[:, 0], P[:, 1], P[:, 2], A[:, 0], A[:, 1], A[:, 2],
                                          B[:, 0], B[:, 1], B[:, 2], C[:, 0], C[:, 1], C[:, 2])
    return np.column_stack([qx, qy, qz]), d2, np.column_stack([u, v, w])


# --------------------------------------------------------------------------- helpers
def _check_mesh(V: np.ndarray, tris: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    V = np.ascontiguousarray(np.asarray(V, np.float64).reshape(-1, 3))
    tris = np.ascontiguousarray(np.asarray(tris, np.int64).reshape(-1, 3))
    if len(tris) == 0:
        raise ValueError("mesh has no triangles")
    if tris.min() < 0 or tris.max() >= len(V):
        raise ValueError("triangle index out of range")
    return V, tris


def _as_points(P: np.ndarray) -> np.ndarray:
    P = np.asarray(P, np.float64)
    return np.ascontiguousarray(P.reshape(-1, 3))


def mesh_orientation_volume(V: np.ndarray, tris: np.ndarray) -> float:
    """Signed volume enclosed by a triangle mesh (units³; positive = outward winding).

    Σ A·(B×C)/6 over triangles, with coordinates taken relative to the mean of
    the referenced vertices for numerical stability. For a closed mesh this is
    the enclosed volume, positive iff the triangles are wound counter-clockwise
    seen from outside (normals point outward). For an open mesh it is the volume
    of the cone from that centroid and only indicates the dominant orientation.
    """
    V, tris = _check_mesh(V, tris)
    c = V[np.unique(tris)].mean(axis=0)
    a, b, cc = V[tris[:, 0]] - c, V[tris[:, 1]] - c, V[tris[:, 2]] - c
    return float(np.sum(a * np.cross(b, cc)) / 6.0)


def angle_weighted_pseudonormals(V: np.ndarray, tris: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pseudonormals of Bærentzen & Aanæs (2005).

    Returns
    -------
    face_n : (F,3) unit face normals (zero for degenerate faces).
    edge_n : (F,3,3) edge pseudonormal per triangle and local edge k, where
        local edge k is the edge *opposite* local vertex k: the sum of the unit
        normals of all faces sharing that edge (two on a manifold edge; one on a
        boundary edge).
    vert_n : (V,3) angle-weighted vertex pseudonormals Σ αᵢ nᵢ (not normalised;
        only the direction matters for signs).
    """
    V, tris = _check_mesh(V, tris)
    A, B, C = V[tris[:, 0]], V[tris[:, 1]], V[tris[:, 2]]
    n = np.cross(B - A, C - A)
    ln = np.linalg.norm(n, axis=1)
    face_n = n / np.where(ln > 0, ln, 1.0)[:, None]
    face_n[ln <= 0] = 0.0

    def _angle(x, y):
        return np.arctan2(np.linalg.norm(np.cross(x, y), axis=1), np.einsum("ij,ij->i", x, y))

    ang = np.column_stack([_angle(B - A, C - A), _angle(C - B, A - B), _angle(A - C, B - C)])
    vert_n = np.zeros((len(V), 3))
    for k in range(3):
        for j in range(3):
            vert_n[:, j] += np.bincount(tris[:, k], weights=ang[:, k] * face_n[:, j], minlength=len(V))

    u = tris[:, [1, 2, 0]].ravel()
    w = tris[:, [2, 0, 1]].ravel()
    key = np.minimum(u, w) * len(V) + np.maximum(u, w)
    uniq, inv = np.unique(key, return_inverse=True)
    inv = inv.ravel()
    fn_he = np.repeat(face_n, 3, axis=0)
    esum = np.zeros((len(uniq), 3))
    for j in range(3):
        esum[:, j] = np.bincount(inv, weights=fn_he[:, j], minlength=len(uniq))
    edge_n = esum[inv].reshape(len(tris), 3, 3)
    return face_n, edge_n, vert_n


def _pseudonormal_at(tris: np.ndarray, tri_id: np.ndarray, bary: np.ndarray,
                     pn: tuple[np.ndarray, np.ndarray, np.ndarray]) -> np.ndarray:
    """Select face / edge / vertex pseudonormal from exact-zero barycentrics."""
    face_n, edge_n, vert_n = pn
    nzero = bary != 0.0
    cnt = nzero.sum(axis=1)
    out = face_n[tri_id].copy()
    e = cnt == 2
    if np.any(e):
        k = np.argmin(nzero[e], axis=1)           # index of the zero coordinate = opposite vertex
        out[e] = edge_n[tri_id[e], k]
    vtx = cnt <= 1
    if np.any(vtx):
        k = np.argmax(nzero[vtx], axis=1)          # the single non-zero coordinate
        out[vtx] = vert_n[tris[tri_id[vtx], k]]
    return out


def _sign_distances(P, Q, tris, tri_id, bary, dist, pn):
    n = _pseudonormal_at(tris, tri_id, bary, pn)
    s = np.einsum("ij,ij->i", P - Q, n)
    return np.where(s < 0, -dist, dist)


# --------------------------------------------------------------------------- grid
def _ring_offsets(r: int) -> np.ndarray:
    """Integer offsets o with max|o| == r (the Chebyshev shell of radius r), (24r²+2, 3)."""
    if r == 0:
        return np.zeros((1, 3), np.int64)
    full = np.arange(-r, r + 1)
    inner = np.arange(-r + 1, r)
    parts = []
    for s in (-r, r):   # x = ±r faces, all y, z
        yy, zz = np.meshgrid(full, full, indexing="ij")
        parts.append(np.column_stack([np.full(yy.size, s), yy.ravel(), zz.ravel()]))
    for s in (-r, r):   # y = ±r faces, inner x, all z
        xx, zz = np.meshgrid(inner, full, indexing="ij")
        parts.append(np.column_stack([xx.ravel(), np.full(xx.size, s), zz.ravel()]))
    for s in (-r, r):   # z = ±r faces, inner x, inner y
        xx, yy = np.meshgrid(inner, inner, indexing="ij")
        parts.append(np.column_stack([xx.ravel(), yy.ravel(), np.full(xx.size, s)]))
    return np.concatenate(parts).astype(np.int64)


class TriangleGrid:
    """Uniform-grid broad phase for exact closest-point queries on a triangle mesh.

    Parameters
    ----------
    V : (n,3) vertices; tris : (F,3) triangle indices.
    cell : cell edge length in the vertices' units. Default: 2 × the mean
        triangle edge length (WP-02 spec), so a typical triangle overlaps 1–8
        cells. If the grid would exceed 2**21 cells the cell is enlarged
        (memory bound only; exactness is unaffected).

    Every triangle is registered in all cells overlapped by its axis-aligned
    bounding box. :meth:`query` searches Chebyshev rings of cells around each
    point and stops when the lower bound on the distance to anything not yet
    visited exceeds the best distance found, so results are exact.

    The lower bound after ring r is the distance from P to the union of the six
    axis-aligned slabs of cells outside the visited (2r+1)³ block (clipped to the
    mesh bounding box), which also covers points outside the grid: their rings
    are centred on the cell of P clamped into the grid. Rings that cannot
    contain a triangle are skipped with a chessboard distance transform of cell
    occupancy, and candidate pairs are screened with triangle bounding boxes
    before the exact test (both are pure accelerations).
    """

    def __init__(self, V: np.ndarray, tris: np.ndarray, cell: float | None = None):
        V, tris = _check_mesh(V, tris)
        self.V = V
        self.tris = tris
        self.A = np.ascontiguousarray(V[tris[:, 0]])
        self.B = np.ascontiguousarray(V[tris[:, 1]])
        self.C = np.ascontiguousarray(V[tris[:, 2]])
        tmin = np.minimum(np.minimum(self.A, self.B), self.C)
        tmax = np.maximum(np.maximum(self.A, self.B), self.C)
        self.tmin, self.tmax = tmin, tmax
        self.centroid = (self.A + self.B + self.C) / 3.0
        lo = tmin.min(axis=0)
        hi = tmax.max(axis=0)
        self.mesh_lo, self.mesh_hi = lo, hi
        extent = hi - lo
        if cell is None:
            e = np.concatenate([np.linalg.norm(self.B - self.A, axis=1),
                                np.linalg.norm(self.C - self.B, axis=1),
                                np.linalg.norm(self.A - self.C, axis=1)])
            cell = 2.0 * float(e.mean())
        cell = float(cell)
        if not np.isfinite(cell) or cell <= 0:
            cell = float(extent.max()) / 16.0 if extent.max() > 0 else 1.0
        dims = np.floor(extent / cell).astype(np.int64) + 1
        while int(np.prod(dims)) > _MAX_CELLS:
            cell *= (np.prod(dims) / _MAX_CELLS) ** (1.0 / 3.0) * 1.01
            dims = np.floor(extent / cell).astype(np.int64) + 1
        self.cell = cell
        self.origin = lo
        self.dims = dims
        self.box_hi = lo + dims * cell
        n_cells = int(np.prod(dims))

        ilo = np.clip(np.floor((tmin - lo) / cell).astype(np.int64), 0, dims - 1)
        ihi = np.clip(np.floor((tmax - lo) / cell).astype(np.int64), 0, dims - 1)
        ext = ihi - ilo + 1
        counts = np.prod(ext, axis=1)
        F = len(tris)
        tri_rep = np.repeat(np.arange(F, dtype=np.int64), counts)
        local = np.arange(int(counts.sum()), dtype=np.int64) - np.repeat(np.cumsum(counts) - counts, counts)
        ex, ey = ext[tri_rep, 0], ext[tri_rep, 1]
        cx = ilo[tri_rep, 0] + local % ex
        cy = ilo[tri_rep, 1] + (local // ex) % ey
        cz = ilo[tri_rep, 2] + local // (ex * ey)
        key = cx + dims[0] * (cy + dims[1] * cz)
        order = np.argsort(key, kind="stable")      # triangle ids ascend within a cell
        self.cell_tris = tri_rep[order]
        self.cell_start = np.searchsorted(key[order], np.arange(n_cells + 1, dtype=np.int64))
        self._empty_rings = self._chessboard_dt(np.diff(self.cell_start) > 0)
        self._pn = None

    # .................................................................. internals
    def _chessboard_dt(self, occupied_flat: np.ndarray) -> np.ndarray:
        """Per cell, a lower bound on the Chebyshev distance (in cells) to an occupied cell."""
        nx, ny, nz = (int(d) for d in self.dims)
        occ = occupied_flat.reshape(nz, ny, nx)          # key = x + nx*(y + ny*z)
        D = np.where(occ, 0, -1).astype(np.int64)
        cur = occ.copy()
        it = 0
        while (D < 0).any() and it < _DT_MAX_ITERS:
            it += 1
            dil = cur
            for ax in range(3):
                t = dil.copy()
                sl_a = [slice(None)] * 3
                sl_b = [slice(None)] * 3
                sl_a[ax], sl_b[ax] = slice(1, None), slice(None, -1)
                t[tuple(sl_a)] |= dil[tuple(sl_b)]
                t[tuple(sl_b)] |= dil[tuple(sl_a)]
                dil = t
            D[dil & (D < 0)] = it
            cur = dil
        D[D < 0] = it          # unreached after `it` dilations: true distance > it
        return D.ravel()

    def _unvisited_lb2(self, P: np.ndarray, q: np.ndarray, r: np.ndarray) -> np.ndarray:
        """Squared lower bound on the distance from P to any triangle not registered
        in the cells of Chebyshev rings 0..r around cell q.

        Such a triangle lies entirely in cells with c_a < q_a − r or c_a > q_a + r
        for some axis a, i.e. in the union of six axis-aligned slabs (clipped to
        the mesh bounding box); the bound is the distance to the nearest slab.
        """
        lo, hi, org, cell, dims = self.mesh_lo, self.mesh_hi, self.origin, self.cell, self.dims
        gap = np.maximum(lo - P, 0.0) + np.maximum(P - hi, 0.0)
        g2 = gap * gap
        lb2 = np.full(len(P), np.inf)
        for a in range(3):
            b, c = (a + 1) % 3, (a + 2) % 3
            rest = g2[:, b] + g2[:, c]
            x = P[:, a]
            top = np.minimum(hi[a], org[a] + (q[:, a] - r) * cell)          # lower slab [lo, top]
            ga = np.maximum(lo[a] - x, 0.0) + np.maximum(x - top, 0.0)
            lb2 = np.where(q[:, a] - r >= 1, np.minimum(lb2, rest + ga * ga), lb2)
            bot = np.maximum(lo[a], org[a] + (q[:, a] + r + 1) * cell)      # upper slab [bot, hi]
            ga = np.maximum(bot - x, 0.0) + np.maximum(x - hi[a], 0.0)
            lb2 = np.where(q[:, a] + r + 1 <= dims[a] - 1, np.minimum(lb2, rest + ga * ga), lb2)
        return lb2

    def pseudonormals(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Cached :func:`angle_weighted_pseudonormals` of the grid's mesh."""
        if self._pn is None:
            self._pn = angle_weighted_pseudonormals(self.V, self.tris)
        return self._pn

    def _evaluate(self, P, pt, tri, best):
        """Evaluate point-triangle pairs and fold them into `best` (in place).

        Pairs are first screened: a pair is dropped when the squared distance
        from the point to the triangle's AABB (a lower bound) exceeds an upper
        bound on the point's best distance (its best so far, or the distance to
        the nearest candidate centroid). Exact ties survive the screen, so the
        selected triangle is the same as with no screening.
        """
        bd2, btri, bq, bbary = best
        if pt.size > 1 and np.any(pt[1:] < pt[:-1]):
            o = np.argsort(pt, kind="stable")
            pt, tri = pt[o], tri[o]
        Pp = P[pt]
        g = Pp - self.centroid[tri]
        ub = g[:, 0] * g[:, 0] + g[:, 1] * g[:, 1] + g[:, 2] * g[:, 2]
        g = np.maximum(self.tmin[tri] - Pp, 0.0) + np.maximum(Pp - self.tmax[tri], 0.0)
        lb = g[:, 0] * g[:, 0] + g[:, 1] * g[:, 1] + g[:, 2] * g[:, 2]
        starts = np.flatnonzero(np.r_[True, pt[1:] != pt[:-1]])
        ubmin = np.minimum(np.minimum.reduceat(ub, starts), bd2[pt[starts]])
        ubp = np.repeat(ubmin, np.diff(np.r_[starts, len(pt)]))
        # 1e-9 relative slack absorbs rounding in lb/ub (both exact to ~1e-15);
        # it can only keep extra pairs, never drop the winner.
        keep = lb <= ubp * (1.0 + 1e-9)
        pt, tri, Pp = pt[keep], tri[keep], Pp[keep]
        if pt.size == 0:
            return
        A, B, C = self.A[tri], self.B[tri], self.C[tri]
        qx, qy, qz, d2, u, v, w = _cpt_kernel(Pp[:, 0], Pp[:, 1], Pp[:, 2], A[:, 0], A[:, 1], A[:, 2],
                                              B[:, 0], B[:, 1], B[:, 2], C[:, 0], C[:, 1], C[:, 2])
        order = np.lexsort((tri, d2, pt))
        pts = pt[order]
        first = np.r_[True, pts[1:] != pts[:-1]]
        sel = order[first]
        gp = pt[sel]
        cd2, ctri = d2[sel], tri[sel]
        better = (cd2 < bd2[gp]) | ((cd2 == bd2[gp]) & (ctri < btri[gp]))
        if not np.any(better):
            return
        gp, sel = gp[better], sel[better]
        bd2[gp] = d2[sel]
        btri[gp] = tri[sel]
        bq[gp] = np.column_stack([qx[sel], qy[sel], qz[sel]])
        bbary[gp] = np.column_stack([u[sel], v[sel], w[sel]])

    def _process_ring(self, P, q, idx, r, best):
        offs = _ring_offsets(r)
        K = len(offs)
        dims = self.dims
        F = len(self.tris)
        step = max(1, _CELL_BATCH // K)
        for c0 in range(0, len(idx), step):
            pidx = idx[c0:c0 + step]
            qq = q[pidx]
            X = qq[:, 0:1] + offs[None, :, 0]
            Y = qq[:, 1:2] + offs[None, :, 1]
            Z = qq[:, 2:3] + offs[None, :, 2]
            ok = (X >= 0) & (X < dims[0]) & (Y >= 0) & (Y < dims[1]) & (Z >= 0) & (Z < dims[2])
            pi, ki = np.nonzero(ok)
            if pi.size == 0:
                continue
            key = X[pi, ki] + dims[0] * (Y[pi, ki] + dims[1] * Z[pi, ki])
            s = self.cell_start[key]
            cnt = self.cell_start[key + 1] - s
            nzm = cnt > 0
            pi, s, cnt = pi[nzm], s[nzm], cnt[nzm]
            if pi.size == 0:
                continue
            # split into sub-batches of whole points with bounded pair counts
            ppc = np.bincount(pi, weights=cnt, minlength=len(pidx)).astype(np.int64)
            cum = np.cumsum(ppc)
            b0 = 0
            while b0 < len(pidx):
                base = cum[b0 - 1] if b0 > 0 else 0
                b1 = int(np.searchsorted(cum, base + _PAIR_BATCH, side="right"))
                b1 = max(b1, b0 + 1)
                lo_e, hi_e = np.searchsorted(pi, [b0, b1])
                if hi_e > lo_e:
                    spi, ss, sc = pi[lo_e:hi_e], s[lo_e:hi_e], cnt[lo_e:hi_e]
                    tot = int(sc.sum())
                    rep = np.repeat(np.arange(len(sc)), sc)
                    pos = np.repeat(ss, sc) + np.arange(tot) - np.repeat(np.cumsum(sc) - sc, sc)
                    tri = self.cell_tris[pos]
                    pt = pidx[spi[rep]]
                    if r > 0:      # a triangle can sit in several cells of one ring
                        u = np.sort(pt * F + tri)
                        u = u[np.r_[True, u[1:] != u[:-1]]]
                        pt, tri = u // F, u % F
                    self._evaluate(P, pt, tri, best)
                b0 = b1

    def _query_all(self, P, idx, best):
        """Screened evaluation of points `idx` against every triangle (far points)."""
        F = len(self.tris)
        tb = min(F, _PAIR_BATCH)
        m = max(1, _PAIR_BATCH // F)
        for c0 in range(0, len(idx), m):
            pidx = idx[c0:c0 + m]
            for t0 in range(0, F, tb):      # triangle blocks; later blocks prune against the running best
                tr = np.arange(t0, min(F, t0 + tb), dtype=np.int64)
                self._evaluate(P, np.repeat(pidx, len(tr)), np.tile(tr, len(pidx)), best)

    # .................................................................. public
    def query(self, P: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Exact closest points on the mesh.

        Parameters
        ----------
        P : (M,3) query points.

        Returns
        -------
        dist : (M,) unsigned distances.
        Q : (M,3) closest points.
        tri_id : (M,) int64 index of the triangle containing Q (lowest id on ties).
        bary : (M,3) barycentrics of Q in that triangle.
        """
        P = _as_points(P)
        M = len(P)
        best = (np.full(M, np.inf), np.full(M, -1, np.int64), np.zeros((M, 3)), np.zeros((M, 3)))
        if M == 0:
            return np.zeros(0), best[2], best[1], best[3]
        cell, dims = self.cell, self.dims
        # Points far outside the mesh box (more than half its diagonal) would
        # sweep most of the grid ring by ring; they are cheaper to screen against
        # all triangles directly (same exact kernel and tie rule).
        gap = P - np.clip(P, self.mesh_lo, self.mesh_hi)
        far = np.einsum("ij,ij->i", gap, gap) > 0.25 * float(np.sum((self.mesh_hi - self.mesh_lo) ** 2))
        if np.any(far):
            self._query_all(P, np.flatnonzero(far), best)
        Pc = np.clip(P, self.origin, self.box_hi)
        q = np.clip(np.floor((Pc - self.origin) / cell).astype(np.int64), 0, dims - 1)
        max_ring = np.maximum(q, dims - 1 - q).max(axis=1)
        keys = q[:, 0] + dims[0] * (q[:, 1] + dims[1] * q[:, 2])
        ring = np.minimum(self._empty_rings[keys], max_ring)
        active = np.flatnonzero(~far)
        while active.size:
            ra = ring[active]
            for r in np.unique(ra):
                self._process_ring(P, q, active[ra == r], int(r), best)
            # Lower bound on the distance to anything in rings >= r+1; continue
            # while it does not exceed the best (1e-9 relative rounding slack:
            # costs at most one extra ring, never exactness).
            lb2 = self._unvisited_lb2(P[active], q[active], ra)
            keep = (lb2 <= best[0][active] * (1.0 + 1e-9)) & (ra < max_ring[active])
            ring[active] += 1
            active = active[keep]
        return np.sqrt(best[0]), best[2], best[1], best[3]


# --------------------------------------------------------------------------- API
def brute_force_point_to_mesh(P: np.ndarray, V: np.ndarray,
                              tris: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Reference closest points: every point against every triangle.

    Vectorised over (point chunk × all triangles); O(M·F). Same return values and
    tie rule (lowest triangle id) as :meth:`TriangleGrid.query`.
    """
    V, tris = _check_mesh(V, tris)
    P = _as_points(P)
    M, F = len(P), len(tris)
    A, B, C = V[tris[:, 0]], V[tris[:, 1]], V[tris[:, 2]]
    d2best = np.full(M, np.inf)
    Q = np.zeros((M, 3))
    tri_id = np.full(M, -1, np.int64)
    bary = np.zeros((M, 3))
    tb = min(F, _PAIR_BATCH)                 # triangle block
    m = max(1, _PAIR_BATCH // tb)            # point chunk
    for c0 in range(0, M, m):
        Pc = P[c0:c0 + m]
        k = len(Pc)
        rows = np.arange(c0, c0 + k)
        for t0 in range(0, F, tb):
            nt = min(tb, F - t0)
            pt = np.repeat(np.arange(k), nt)
            tr = np.tile(np.arange(t0, t0 + nt), k)
            Pp, Ap, Bp, Cp = Pc[pt], A[tr], B[tr], C[tr]
            qx, qy, qz, d2, u, v, w = _cpt_kernel(Pp[:, 0], Pp[:, 1], Pp[:, 2], Ap[:, 0], Ap[:, 1], Ap[:, 2],
                                                  Bp[:, 0], Bp[:, 1], Bp[:, 2], Cp[:, 0], Cp[:, 1], Cp[:, 2])
            j = np.argmin(d2.reshape(k, nt), axis=1)       # first minimum = lowest triangle id
            flat = np.arange(k) * nt + j
            better = d2[flat] < d2best[rows]                # strict: earlier blocks hold lower ids
            r, f = rows[better], flat[better]
            d2best[r] = d2[f]
            Q[r] = np.column_stack([qx[f], qy[f], qz[f]])
            tri_id[r] = t0 + j[better]
            bary[r] = np.column_stack([u[f], v[f], w[f]])
    return np.sqrt(d2best), Q, tri_id, bary


def point_to_mesh(P: np.ndarray, V: np.ndarray, tris: np.ndarray, signed: bool = False,
                  grid: TriangleGrid | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Exact distance from points to a triangle mesh surface.

    Parameters
    ----------
    P : (M,3) points; V : (n,3) vertices; tris : (F,3) triangles.
    signed : if True, distances carry the sign of (P − Q)·n with the angle-
        weighted pseudonormal n (Bærentzen & Aanæs 2005): positive outside,
        negative inside for an outward (counter-clockwise from outside) wound
        closed mesh — see the module docstring.
    grid : optional prebuilt :class:`TriangleGrid` of the *same* (V, tris), to
        amortise the broad-phase build over several calls.

    Returns
    -------
    dist : (M,) (signed) distances; Q : (M,3) closest points; tri_id : (M,)
    int64; bary : (M,3) barycentrics of Q in ``tri_id``.
    """
    if grid is None:
        grid = TriangleGrid(V, tris)
    elif tris is not None and np.asarray(tris).reshape(-1, 3).shape != grid.tris.shape:
        raise ValueError("grid was built for a different mesh")
    P = _as_points(P)
    dist, Q, tri_id, bary = grid.query(P)
    if signed and len(P):
        dist = _sign_distances(P, Q, grid.tris, tri_id, bary, dist, grid.pseudonormals())
    return dist, Q, tri_id, bary
