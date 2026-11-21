"""Silhouette / profile-contour fitting.

Landmark detectors are weak exactly where likeness lives in side views: the
profile line of forehead, nose, lips and chin, and the jaw/cheek outline. This
module pulls the mesh's occluding contour (silhouette) onto 2D outlines traced
in the photos (manually, or from a segmentation mask), using an ICP-style loop:

  repeat:
    1. find silhouette vertices of the current mesh in each view
       (vertices on edges shared by a front-facing and a back-facing triangle)
    2. match every outline sample to the nearest projected silhouette vertex
    3. keep only the component of each 2D correction along the vertex's outward
       image normal (``normal_only=True``, the default; see below)
    4. turn each 2D correction into a 3D target at the vertex's current depth
    5. solve a bilaplacian-smooth deformation honouring these targets plus any
       fixed constraints (e.g. reconstructed landmarks), take a damped step.

Normal-only correction (DESIGN D-13 "normal-only residuals", defect 1 "tangential
silhouette drift"; WP-06 (a)). An outline sample only says where the occluding
contour is *across* the curve; its position *along* the curve is arbitrary
(sampling density, clustering, partial outlines). The legacy correction moved the
matched vertex all the way to the sample, so unevenly spaced or one-sided samples
dragged rim vertices tangentially along the contour (vertex contours carry
half-edge bias). With ``normal_only=True`` the sample O_k matched to vertex v
(projection P) is replaced by

    O'_k = P + n2 (n2 . (O_k - P)),
    n2   = normalise(project(V_v + 1.0 mm * n3_v) - project(V_v)),

where n3_v is the area-weighted vertex normal (``Mesh.vertex_normals``), so only
the across-contour component survives; samples whose normal projects to
|.| < 1e-9 px (normal along the viewing ray) are skipped. The full sub-vertex rim,
ContourObs residuals and the contour Term of DESIGN 4.16 live in :mod:`face3d.fit.contour`
(WP-17); ``use_subvertex=True`` brings the sub-vertex rim to this legacy loop.
``normal_only=False`` reproduces the legacy behaviour exactly.

Sub-vertex targets (``use_subvertex=True``, WP-17; DESIGN D-13 "sub-vertex zero
crossing", 4.16 "Model rim"). Instead of silhouette *vertices*, each view's model rim is
the sub-vertex zero crossing of q = n . (x - C) (:func:`face3d.fit.contour.rim_points`),
sampled along its polyline every ``subvertex_spacing_px`` (:func:`face3d.fit.contour.densify_rim`;
every sample is a fixed combination of up to four vertices with weights w). Each
outline sample is matched to the nearest rim sample within ``max_dist_px`` (uniform-grid
search, :func:`face3d.fit.contour.grid_nearest`), the correction keeps only its
component along the rim sample's outward image normal n2 (normal-only, as above; the
full correction when ``normal_only=False``), and the 3D displacement D of the rim sample
(back-projection of the corrected point at the sample's depth, minus the sample) is
shared by its support vertices: vertex v receives the target V_v + D with weight
weight_view * w_v. Defaults are unchanged (``use_subvertex=False``).

Units: vertices and depths in mm (model units), outlines and errors in pixels.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..geometry.camera import Camera
from ..mesh.core import Mesh
from ..mesh.laplacian import laplacian_deform
from ..mesh.reduced import ReducedDeformer


@dataclass
class ContourView:
    camera: Camera
    outline_px: np.ndarray       # (M,2) samples along the traced outline (any order)
    weight: float = 1.0


def edge_faces(tris: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Unique edges (E,2) and the two adjacent triangle ids per edge (E,2; -1 = boundary)."""
    e = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    f = np.tile(np.arange(len(tris)), 3)
    es = np.sort(e, axis=1)
    key = es[:, 0] * (tris.max() + 1) + es[:, 1]
    order = np.argsort(key, kind="stable")
    key, es, f = key[order], es[order], f[order]
    starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    counts = np.diff(np.r_[starts, len(key)])
    edges = es[starts]
    adj = np.full((len(starts), 2), -1, np.int64)
    adj[:, 0] = f[starts]
    two = counts >= 2
    adj[two, 1] = f[starts[two] + 1]
    return edges, adj


def silhouette_vertices(V: np.ndarray, tris: np.ndarray, cam: Camera,
                        topo: tuple[np.ndarray, np.ndarray] | None = None) -> np.ndarray:
    """Indices of vertices lying on occluding-contour edges as seen from `cam`."""
    edges, adj = topo if topo is not None else edge_faces(tris)
    a, b, c = V[tris[:, 0]], V[tris[:, 1]], V[tris[:, 2]]
    n = np.cross(b - a, c - a)
    view = (a + b + c) / 3.0 - cam.center
    front = np.einsum("ij,ij->i", n, view) < 0
    inner = adj[:, 1] >= 0
    sil = inner & (front[adj[:, 0]] != np.where(inner, front[np.maximum(adj[:, 1], 0)], False))
    sil |= ~inner & front[adj[:, 0]]  # open-mesh boundary edges also outline the shape
    return np.unique(edges[sil].ravel())


def _backproject_at_depth(cam: Camera, uv: np.ndarray, depth: np.ndarray) -> np.ndarray:
    xc = np.column_stack([(uv[:, 0] - cam.cx) / cam.f * depth, (uv[:, 1] - cam.cy) / cam.f * depth, depth])
    return (xc - cam.t) @ cam.R  # R^T (xc - t)


def _subvertex_targets(V: np.ndarray, tris: np.ndarray, normals: np.ndarray, cam: Camera, view: ContourView,
                       topo: tuple[np.ndarray, np.ndarray], vertex_mask: np.ndarray | None, max_dist_px: float,
                       normal_only: bool, spacing_px: float, tgt_sum: np.ndarray, tgt_w: np.ndarray) -> float:
    """Accumulate sub-vertex rim targets of one view (module docstring); returns its mean error (px)."""
    from .contour import densify_rim, grid_nearest, rim_points   # contour imports this module

    rim = rim_points(V, tris, normals, cam, topo=topo)
    smp = densify_rim(rim, cam, spacing_px)
    keep = smp.visible.copy()
    if vertex_mask is not None:
        keep &= np.all(np.asarray(vertex_mask, bool)[smp.vid] | (smp.w <= 0), axis=1)
    sel = np.flatnonzero(keep)
    O = np.asarray(view.outline_px, float).reshape(-1, 2)
    if len(sel) == 0 or len(O) == 0:
        return float(max_dist_px)
    pairs = grid_nearest(O, smp.uv[sel], max_dist_px)
    if len(pairs) == 0:
        return float(max_dist_px)
    oi, si = pairs[:, 0], sel[pairs[:, 1]]
    P = smp.uv[si]
    Ok = O[oi]
    if normal_only:
        n2 = smp.normal2d[si]
        d_n = np.sum(n2 * (Ok - P), axis=1)
        Ok = P + n2 * d_n[:, None]
        err = float(np.abs(d_n).mean())
    else:
        err = float(np.linalg.norm(Ok - P, axis=1).mean())
    target = _backproject_at_depth(cam, Ok, smp.depth[si])
    disp = target - smp.p[si]                                  # (n, 3) rim-sample displacement
    vid, w = smp.vid[si], smp.w[si] * float(view.weight)
    for k in range(vid.shape[1]):
        wk = w[:, k]
        m = wk > 0
        np.add.at(tgt_sum, vid[m, k], wk[m, None] * (V[vid[m, k]] + disp[m]))
        np.add.at(tgt_w, vid[m, k], wk[m])
    return err


def fit_silhouettes(mesh: Mesh, views: list[ContourView], *, fixed_idx: np.ndarray | None = None,
                    fixed_pos: np.ndarray | None = None, iterations: int = 10, max_dist_px: float = 60.0,
                    step: float = 0.7, weight: float = 200.0, fixed_weight: float = 1e3,
                    vertex_mask: np.ndarray | None = None, method: str = "reduced",
                    n_centers: int = 600, smoothness: float = 1e-2,
                    normal_only: bool = True, use_subvertex: bool = False,
                    subvertex_spacing_px: float = 2.0) -> tuple[np.ndarray, list[float]]:
    """Deform `mesh` so its silhouettes match the outlines. Returns (vertices, mean px error per iteration).

    vertex_mask: optional bool (V,) restricting which vertices may be matched
    (e.g. exclude hair/ears/neck regions that the outline does not describe).
    method: "reduced" (Gaussian-RBF subspace, fast on large meshes) or
    "laplacian" (full bilaplacian solve, exact but slow beyond a few thousand vertices).
    normal_only: keep only the across-contour (outward image normal) component of
    each outline correction (DESIGN D-13, WP-06 (a); see the module docstring).
    False reproduces the legacy full-correction behaviour exactly.
    use_subvertex: match outline samples to the sub-vertex rim polyline instead of the
    silhouette vertices (WP-17; module docstring); ``subvertex_spacing_px`` is the rim
    sampling step in pixels. ``vertex_mask`` then keeps the rim samples whose support
    vertices are all allowed.

    The returned history is the mean error in pixels per iteration over the
    samples within ``max_dist_px`` of their nearest projected silhouette vertex:
    the across-contour distance |n2 . (O_k - P)| when ``normal_only`` (the
    residual this mode minimises; the along-contour offset is not an error), else
    the legacy Euclidean sample-to-vertex distance.
    """
    V = mesh.vertices.copy()
    tris = mesh.triangles()
    topo = edge_faces(tris)
    reducer = ReducedDeformer(V, n_centers=n_centers) if method == "reduced" else None
    history: list[float] = []
    fixed_idx = np.zeros(0, np.int64) if fixed_idx is None else np.asarray(fixed_idx, np.int64)
    fixed_pos = np.zeros((0, 3)) if fixed_pos is None else np.asarray(fixed_pos, float)
    for _ in range(iterations):
        tgt_sum = np.zeros_like(V)
        tgt_w = np.zeros(len(V))
        errs = []
        normals = None  # vertex normals of the current V, computed lazily (normal_only)
        for view in views:
            cam = view.camera
            if use_subvertex:
                if normals is None:
                    normals = Mesh(V, mesh.faces).vertex_normals()
                errs.append(_subvertex_targets(V, tris, normals, cam, view, topo, vertex_mask, max_dist_px,
                                               normal_only, subvertex_spacing_px, tgt_sum, tgt_w))
                continue
            sil = silhouette_vertices(V, tris, cam, topo)
            if vertex_mask is not None:
                sil = sil[vertex_mask[sil]]
            if len(sil) == 0:
                continue
            P = cam.project(V[sil])
            O = np.asarray(view.outline_px, float)
            d2 = np.sum((O[:, None, :] - P[None, :, :]) ** 2, axis=2)
            nn = np.argmin(d2, axis=1)
            dist = np.sqrt(d2[np.arange(len(O)), nn])
            keep = dist < max_dist_px
            vi = sil[nn[keep]]
            Ok = O[keep]
            if not normal_only:
                errs.append(float(dist[keep].mean()) if keep.any() else max_dist_px)
            else:
                d_n = np.zeros(0)
                if len(vi):
                    if normals is None:
                        normals = Mesh(V, mesh.faces).vertex_normals()
                    Pk = P[nn[keep]]
                    q = cam.project(V[vi] + 1.0 * normals[vi]) - Pk  # image of a 1 mm step along n3
                    qn = np.linalg.norm(q, axis=1)
                    ok = qn >= 1e-9  # skip normals seen end-on
                    n2 = q[ok] / qn[ok, None]
                    vi, Pk, Ok = vi[ok], Pk[ok], Ok[ok]
                    d_n = np.sum(n2 * (Ok - Pk), axis=1)  # signed across-contour offset (px)
                    Ok = Pk + n2 * d_n[:, None]
                errs.append(float(np.abs(d_n).mean()) if len(d_n) else max_dist_px)
            depth = cam.depth(V[vi])
            target = _backproject_at_depth(cam, Ok, depth)
            np.add.at(tgt_sum, vi, view.weight * target)
            np.add.at(tgt_w, vi, view.weight)
        history.append(float(np.mean(errs)) if errs else float("nan"))
        hit = np.flatnonzero(tgt_w > 0)
        if len(hit) == 0:
            break
        targets = tgt_sum[hit] / tgt_w[hit, None]
        targets = V[hit] + step * (targets - V[hit])
        free = np.setdiff1d(hit, fixed_idx)
        sel = np.isin(hit, free)
        idx = np.concatenate([free, fixed_idx])
        tg = np.vstack([targets[sel], fixed_pos])
        # Silhouette targets are softer than fixed (landmark) constraints.
        w = np.r_[np.full(len(free), weight), np.full(len(fixed_idx), fixed_weight)]
        if reducer is not None:
            # The subspace is built on the rest shape; displacements accumulate on it.
            V = V + reducer.solve(idx, tg - V[idx], w, smoothness)
        else:
            V, _ = laplacian_deform(Mesh(V, mesh.faces), idx, tg, weight=w, x_init=V)
    return V, history
