"""Silhouette / profile-contour fitting.

Landmark detectors are weak exactly where likeness lives in side views: the
profile line of forehead, nose, lips and chin, and the jaw/cheek outline. This
module pulls the mesh's occluding contour (silhouette) onto 2D outlines traced
in the photos (manually, or from a segmentation mask), using an ICP-style loop:

  repeat:
    1. find silhouette vertices of the current mesh in each view
       (vertices on edges shared by a front-facing and a back-facing triangle)
    2. match every outline sample to the nearest projected silhouette vertex
    3. turn each 2D correction into a 3D target at the vertex's current depth
    4. solve a bilaplacian-smooth deformation honouring these targets plus any
       fixed constraints (e.g. reconstructed landmarks), take a damped step.
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


def fit_silhouettes(mesh: Mesh, views: list[ContourView], *, fixed_idx: np.ndarray | None = None,
                    fixed_pos: np.ndarray | None = None, iterations: int = 10, max_dist_px: float = 60.0,
                    step: float = 0.7, weight: float = 200.0, fixed_weight: float = 1e3,
                    vertex_mask: np.ndarray | None = None, method: str = "reduced",
                    n_centers: int = 600, smoothness: float = 1e-2) -> tuple[np.ndarray, list[float]]:
    """Deform `mesh` so its silhouettes match the outlines. Returns (vertices, mean px error per iteration).

    vertex_mask: optional bool (V,) restricting which vertices may be matched
    (e.g. exclude hair/ears/neck regions that the outline does not describe).
    method: "reduced" (Gaussian-RBF subspace, fast on large meshes) or
    "laplacian" (full bilaplacian solve, exact but slow beyond a few thousand vertices).
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
        for view in views:
            cam = view.camera
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
            errs.append(float(dist[keep].mean()) if keep.any() else max_dist_px)
            vi = sil[nn[keep]]
            depth = cam.depth(V[vi])
            target = _backproject_at_depth(cam, O[keep], depth)
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
