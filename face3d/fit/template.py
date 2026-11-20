"""Template head fitting: similarity-align, RBF-warp to landmarks, Laplacian refine."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..geometry.procrustes import apply_similarity, umeyama
from ..geometry.rbf import RBFWarp
from ..mesh.core import Mesh
from ..mesh.laplacian import laplacian_deform


@dataclass
class Template:
    """A base head mesh plus which vertex carries each landmark.

    landmark_vertices[i] = vertex index of landmark i (or -1 when the landmark
    is not represented on this mesh, e.g. an iris centre on a mesh without eyes).
    """
    mesh: Mesh
    names: list[str]
    landmark_vertices: np.ndarray
    meta: dict = field(default_factory=dict)

    @property
    def landmark_positions(self) -> np.ndarray:
        idx = self.landmark_vertices
        out = np.full((len(idx), 3), np.nan)
        ok = idx >= 0
        out[ok] = self.mesh.vertices[idx[ok]]
        return out


@dataclass
class TemplateFit:
    vertices: np.ndarray
    similarity: tuple[float, np.ndarray, np.ndarray]
    landmark_rmse_mm: float


def fit_template_to_landmarks(tpl: Template, X: np.ndarray, *, rbf_smoothing: float = 0.0,
                              refine: bool = True, refine_weight: float = 1e3,
                              landmark_mask: np.ndarray | None = None) -> TemplateFit:
    """Deform the template so its landmark vertices land on target 3D landmarks X (N,3)."""
    X = np.asarray(X, float)
    idx = tpl.landmark_vertices
    ok = (idx >= 0) & ~np.isnan(X[:, 0])
    if landmark_mask is not None:
        ok &= np.asarray(landmark_mask, bool)
    if ok.sum() < 4:
        raise ValueError("need at least 4 usable landmarks")
    src = tpl.mesh.vertices[idx[ok]]
    s, R, t = umeyama(src, X[ok])
    V = apply_similarity(tpl.mesh.vertices, s, R, t)
    warp = RBFWarp(V[idx[ok]], X[ok], smoothing=rbf_smoothing)
    V = warp(V)
    if refine:
        m = Mesh(V, tpl.mesh.faces)
        V, _ = laplacian_deform(m, idx[ok], X[ok], weight=refine_weight, x_init=V)
    rmse = float(np.sqrt(np.mean(np.sum((V[idx[ok]] - X[ok]) ** 2, axis=1))))
    return TemplateFit(V, (s, R, t), rmse)
