"""Reduced-space smooth deformation (fast on 50k-vertex heads, numpy only).

The displacement field is a sum of Gaussian RBFs centred on k vertices chosen by
farthest-point sampling:  d(x) = sum_j w_j * exp(-|x - c_j|^2 / (2 s^2)).
Fitting solves the k x k system
    (Phi_m^T W Phi_m + lam * Phi_cc) w = Phi_m^T W d_m
i.e. weighted least squares on the constraints plus the RKHS-norm smoothness
penalty. Unlike the global biharmonic warp, Gaussian fields decay away from
the constraints, so regions without evidence stay where they were.

Explicit linear map and similarity projector (DESIGN 4.16 "Gauge projector"; WP-17)
------------------------------------------------------------------------------------
For the contour stage the deformation is used as a linear basis: with the coefficient
matrix W (k, 3) the displaced vertices are V = V_rest + Phi W, Phi = :meth:`basis_rows`.
The coefficient *vector* is ordered coordinate-major, c = (W[:, 0]; W[:, 1]; W[:, 2])
(3k,), so the displacement of rows a, ordered the same way, is d_a = (I3 kron Phi_a) c
(:func:`coef_matrix` / :func:`coef_vector` convert).  :meth:`similarity_projector`
returns Pi = I - C^T (C C^T)^-1 C with C = G^T (I3 kron Phi_a), G the 7-column
similarity tangent basis (3 translations, 3 rotations about the anchor centroid,
isotropic scale) at the anchor rest positions, ordered coordinate-major like d_a; any
c = Pi c~ then moves the anchors by a displacement with no similarity component
(G^T d_a = 0), so the coefficients cannot trade with free cameras or the global scale.
Units: coefficients and displacements in mm (the Gaussian kernel is dimensionless).
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


def coef_matrix(c: np.ndarray, k: int) -> np.ndarray:
    """Coordinate-major coefficient vector (3k,) -> matrix W (k, 3) (W[j, d] = c[d k + j])."""
    return np.asarray(c, float).reshape(3, k).T


def coef_vector(W: np.ndarray) -> np.ndarray:
    """Coefficient matrix W (k, 3) -> coordinate-major vector (3k,)."""
    return np.ascontiguousarray(np.asarray(W, float).T).reshape(-1)


def similarity_tangent_cm(P: np.ndarray) -> np.ndarray:
    """Similarity tangent basis G (3n, 7) at points P (n, 3), rows ordered coordinate-major.

    Row ``d n + i`` is point i, axis d.  Columns: translations along x, y, z; infinitesimal
    rotations about x, y, z through the centroid (e_k x (P_i - P_bar)); isotropic scale
    about the centroid (P_i - P_bar).  Columns are normalised to unit length (the
    projectors built from G do not depend on column scaling).
    """
    P = np.asarray(P, float).reshape(-1, 3)
    n = len(P)
    D = P - P.mean(axis=0)
    G = np.zeros((3 * n, 7))
    for d in range(3):
        G[d * n:(d + 1) * n, d] = 1.0
    eye = np.eye(3)
    for k in range(3):
        R = np.cross(eye[k], D)                       # (n, 3)
        G[:, 3 + k] = R.T.reshape(-1)
    G[:, 6] = D.T.reshape(-1)
    nrm = np.linalg.norm(G, axis=0)
    keep = nrm > 1e-12
    G[:, keep] /= nrm[keep]
    return G


def similarity_projector_from(Phi_a: np.ndarray, P_a: np.ndarray, rel_tol: float = 1e-10) -> np.ndarray:
    """Pi = I - C^T (C C^T)^-1 C with C = G^T (I3 kron Phi_a) (see the module docstring).

    ``Phi_a`` (n_a, k) basis rows at the anchors, ``P_a`` (n_a, 3) anchor rest positions.
    Computed as I - U U^T with U an orthonormal basis of range(C^T) (thin SVD; singular
    values below ``rel_tol`` x the largest are dropped), which equals the formula when C
    has full row rank and stays a symmetric idempotent otherwise.
    """
    Phi_a = np.asarray(Phi_a, float)
    n_a, k = Phi_a.shape
    G = similarity_tangent_cm(P_a)                    # (3 n_a, 7)
    C = np.zeros((G.shape[1], 3 * k))
    for d in range(3):
        C[:, d * k:(d + 1) * k] = G[d * n_a:(d + 1) * n_a].T @ Phi_a
    U, sv, _ = np.linalg.svd(C.T, full_matrices=False)
    keep = sv > rel_tol * (sv[0] if len(sv) and sv[0] > 0 else 1.0)
    U = U[:, keep]
    Pi = np.eye(3 * k) - U @ U.T
    return 0.5 * (Pi + Pi.T)


class ReducedDeformer:
    def __init__(self, V: np.ndarray, n_centers: int = 600, width_factor: float = 1.6,
                 centers_idx: np.ndarray | None = None):
        """``centers_idx`` (optional, WP-17): explicit centre vertices instead of the
        farthest-point sample (default behaviour unchanged)."""
        self.V = np.asarray(V, float)
        if centers_idx is None:
            self.centers_idx = farthest_point_sample(self.V, n_centers)
        else:
            self.centers_idx = np.asarray(centers_idx, np.int64).reshape(-1)
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

    # ------------------------------------------------------------------ WP-17
    @property
    def n_centers(self) -> int:
        return len(self.centers_idx)

    def basis_rows(self, rows: np.ndarray | None = None) -> np.ndarray:
        """Phi (r, k): the Gaussian kernel of rest vertices ``rows`` (all when None) at the centres.

        The displacement of those rows for coefficients W (k, 3) is ``Phi @ W`` (mm).
        """
        P = self.V if rows is None else self.V[np.asarray(rows, np.int64).reshape(-1)]
        return _gauss(P, self.C, self.s)

    def similarity_projector(self, anchor_rows: np.ndarray) -> np.ndarray:
        """Pi (3k, 3k) removing the 7-DoF similarity at the anchor rows (module docstring;
        DESIGN 4.16 "Gauge projector")."""
        rows = np.asarray(anchor_rows, np.int64).reshape(-1)
        if len(rows) < 3:
            raise ValueError("the similarity projector needs at least 3 anchor rows")
        return similarity_projector_from(self.basis_rows(rows), self.V[rows])
