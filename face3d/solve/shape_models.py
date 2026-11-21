"""Low-dimensional shape models for the bundle: ``LinearBasis`` and extremal soft-argmax landmarks
(DESIGN 4.8 "ShapeModel", 4.15 stage D, 4.16; WBS WP-17).

``LinearBasis`` parameterises a whole template mesh by the Gaussian-RBF coefficients of a
:class:`~face3d.mesh.reduced.ReducedDeformer` and exposes the scheme landmarks to the
bundle through the :class:`~face3d.solve.terms.ShapeModel` protocol (WP-10), so the
contour stage (DESIGN 4.15 D, 4.16) runs inside the one landmark solver (DESIGN D-01).

Conventions
-----------
* Units: mm in the template's head frame (DESIGN 3.1).  Kernel values are dimensionless,
  so coefficients are displacements in mm.
* Coefficient vectors are **coordinate-major**: c = (W[:, 0]; W[:, 1]; W[:, 2]) for the
  coefficient matrix W (K, 3) of the K centres (:func:`face3d.mesh.reduced.coef_matrix`).
  The parameters are c~ (3K,) and the coefficients c = Pi c~, Pi the similarity
  projector of :meth:`face3d.mesh.reduced.ReducedDeformer.similarity_projector` over the
  anchor vertex rows (DESIGN 4.16 "Gauge projector"; identity with ``projector=False``),
  so the coefficients cannot express a similarity at the anchors and cannot trade with
  free cameras or the global log-scale.
* Vertices: V(c) = V_bar + Phi W (V_bar = ``deformer.V``, Phi = ``deformer.basis_rows``).
  Landmarks: X_n = sum_k bary_nk V[tris[tri_n, k]] (the kit embeddings; DESIGN 3.2), so
  X = X_bar + A W with A = B Phi_rows evaluated only on the needed vertex rows.
* ``jacobian(q)`` is dX/dc~ with point-major rows (bundle convention, ``terms.py``):
  row 3n + d, column d' K + j equals A[n, j] [d == d'], times Pi.  The model is linear,
  so the Jacobian is computed once and cached.
* **Coefficient rows** (``expose_coefficients=True``, :meth:`LinearBasis.with_coefficient_rows`):
  ``points(q)`` appends K rows holding the *parameters* c~ reshaped to (K, 3)
  (row j = (c~[j], c~[K + j], c~[2K + j])), with identity Jacobian rows.  The WP-10 Term
  protocol gives a term derivatives only through the 'X' block (vec of the points), so
  this is how :class:`~face3d.fit.contour.ContourTerm` and :class:`BasisPrior` read c~
  and return dr/dc~ exactly through the bundle's chain rule without any change to the
  bundle; their rows are never observed (NaN in every view) and carry no data.

Extremal landmarks (DESIGN 4.16 "Extremal landmarks", anat R3.2): an extremal point
(g', zy', go', pg') is the soft-argmax of the candidate vertices along a direction d,
X = sum_j w_j V_j with w = softmax(<V_j, d> / T), temperature T = 1.5 mm; its Jacobian is
dX/dV_k = w_k (I + (V_k - X) d^T / T) (:func:`extremal_landmark`).

numpy + stdlib only.
"""
from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from ..core.config import Default, register_defaults
from ..mesh.reduced import ReducedDeformer, coef_matrix, coef_vector

__all__ = ["LinearBasis", "BasisPrior", "extremal_landmark", "DEFAULT_ANCHOR_IDS", "SHAPE_MODELS"]

_BRAIN = "\U0001F9E0"   # expert knowledge, provisional
_NEW = "\U0001F195"     # introduced by this design, uncalibrated

SHAPE_MODELS = register_defaults("shape_models", {
    "extremal_temperature_mm": Default(1.5, _BRAIN, "DESIGN 4.16 'Extremal landmarks': soft-argmax temperature "
                                       "1.5 mm (anat R3.2; proposal-accuracy 1-2 mm)", "mm", (1e-6, 100.0)),
    "coef_prior_sigma_mm": Default(3.0, _BRAIN, "DESIGN 4.15 'Uncertainty': residual surface sigma after stage C "
                                   "(nose 2-3, cheeks 2.5-4 mm); prior SD of the stage-D displacement field",
                                   "mm", (1e-6, 1000.0)),
    "coef_prior_jitter": Default(1e-2, _NEW, "WBS WP-17 implementation: ridge added to the unit-diagonal kernel "
                                 "matrix K_cc of the coefficient prior (numerical conditioning)", "", (0.0, 1.0)),
})

#: Gauge anchors of the similarity projector (WBS WP-17; DESIGN 4.6 gauge anchors).
DEFAULT_ANCHOR_IDS: tuple[str, ...] = ("en_L", "en_R", "ex_L", "ex_R", "p_L", "p_R", "n", "prn", "sn",
                                       "ch_L", "ch_R", "ls", "li", "sto")


def extremal_landmark(V_rows: np.ndarray, direction: np.ndarray, T: float | None = None
                      ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Soft-argmax extremal point of candidate vertices along ``direction`` (DESIGN 4.16).

    X = sum_j w_j V_j with w = softmax(<V_j, d> / T) (d normalised; T in mm, default
    1.5 mm).  Returns ``(X (3,), w (n,), J (n, 3, 3))`` with J_k = dX/dV_k =
    w_k (I + (V_k - X) d^T / T), the exact Jacobian weights.
    """
    P = np.asarray(V_rows, float).reshape(-1, 3)
    if len(P) == 0:
        raise ValueError("extremal_landmark needs at least one candidate vertex")
    d = np.asarray(direction, float).reshape(3)
    nd = float(np.linalg.norm(d))
    if not nd > 0:
        raise ValueError("direction must be non-zero")
    d = d / nd
    Tm = float(SHAPE_MODELS["extremal_temperature_mm"].value if T is None else T)
    if not Tm > 0:
        raise ValueError("temperature must be > 0")
    s = P @ d / Tm
    s = s - s.max()
    w = np.exp(s)
    w /= w.sum()
    X = w @ P
    J = w[:, None, None] * (np.eye(3)[None] + np.einsum("ni,j->nij", P - X, d) / Tm)
    return X, w, J


def _kit_rows(kit: Any, scheme: str, names: Sequence[str] | None) -> tuple[list[str], np.ndarray, np.ndarray]:
    pts = kit.landmarks[scheme]
    nm = list(pts) if names is None else [str(x) for x in names]
    missing = [x for x in nm if x not in pts]
    if missing:
        raise KeyError(f"scheme {scheme!r} has no landmarks {missing}")
    tri = np.asarray([pts[x]["tri"] for x in nm], np.int64)
    bary = np.asarray([pts[x]["bary"] for x in nm], float).reshape(-1, 3)
    return nm, tri, bary


class LinearBasis:
    """Template mesh parameterised by similarity-projected RBF coefficients (WBS WP-17).

    Parameters
    ----------
    kit : :class:`~face3d.model.template_kit.TemplateKit` (topology and landmark embeddings).
    deformer : :class:`~face3d.mesh.reduced.ReducedDeformer` built on the rest vertices
        V_bar of this stage (``deformer.V``, kit topology), e.g. the template warped to the
        landmark-stage solution.
    scheme : landmark scheme whose points the bundle sees (``points``).
    anchor_ids : anatomical ids of the projector anchors (the vertex of largest
        barycentric weight of each; looked up in ``'anatomical44'`` when the kit has it,
        else in ``scheme``); ids the kit lacks are skipped.
    projector : apply Pi (True) or use c = c~ (False).
    names : optional subset / order of the scheme's points (default: stored order).
    expose_coefficients : append the K coefficient rows to ``points`` (module docstring).

    Attributes: ``K`` (centres), ``N`` (landmarks), ``n_points`` (N or N + K),
    ``n_params`` (3K), ``Pi`` (3K, 3K), ``A`` (N, K), ``X_bar`` (N, 3), ``V_bar``,
    ``anchor_rows``, ``names``, ``coef_offset`` (= N, first coefficient row).
    """

    def __init__(self, kit: Any, deformer: ReducedDeformer, scheme: str = "anatomical44",
                 anchor_ids: Sequence[str] = DEFAULT_ANCHOR_IDS, projector: bool = True, *,
                 names: Sequence[str] | None = None, expose_coefficients: bool = False):
        self.kit = kit
        self.deformer = deformer
        self.V_bar = np.asarray(deformer.V, float)
        if self.V_bar.shape != (kit.n_verts, 3):
            raise ValueError(f"deformer.V has shape {self.V_bar.shape}; the kit has {kit.n_verts} vertices")
        self.scheme = scheme
        self.tris = np.asarray(kit.triangles(), np.int64)
        self.names, tri, bary = _kit_rows(kit, scheme, names)
        T = self.tris[tri]                                       # (N, 3) vertex ids
        self.rows, inv = np.unique(T.ravel(), return_inverse=True)
        inv = inv.reshape(T.shape)
        N = len(self.names)
        B = np.zeros((N, len(self.rows)))
        for k in range(3):
            np.add.at(B, (np.arange(N), inv[:, k]), bary[:, k])
        self.B = B
        self.K = int(deformer.n_centers)
        self.N = N
        self.A = B @ deformer.basis_rows(self.rows)              # (N, K)
        self.X_bar = B @ self.V_bar[self.rows]                    # (N, 3)
        a_scheme = "anatomical44" if "anatomical44" in kit.landmarks else scheme
        ids = [a for a in anchor_ids if a in kit.landmarks[a_scheme]]
        self.anchor_ids = tuple(ids)
        self.anchor_rows = (np.asarray(kit.landmark_vertices(a_scheme, ids), np.int64) if ids
                            else np.zeros(0, np.int64))
        self.projector = bool(projector)
        if self.projector:
            if len(np.unique(self.anchor_rows)) < 3:
                raise ValueError("the similarity projector needs at least 3 distinct anchor vertices")
            self.Pi = deformer.similarity_projector(self.anchor_rows)
        else:
            self.Pi = np.eye(3 * self.K)
        self.expose_coefficients = bool(expose_coefficients)
        self.coef_offset = N
        J0 = np.zeros((3 * N, 3 * self.K))
        for d in range(3):
            J0[d::3, d * self.K:(d + 1) * self.K] = self.A
        self._J_lm = J0 @ self.Pi
        self._J_cache: np.ndarray | None = None

    # ------------------------------------------------------------------ protocol
    @property
    def n_params(self) -> int:
        return 3 * self.K

    @property
    def n_points(self) -> int:
        return self.N + (self.K if self.expose_coefficients else 0)

    def with_coefficient_rows(self) -> "LinearBasis":
        """A shallow copy with ``expose_coefficients=True`` (shares every array)."""
        out = object.__new__(LinearBasis)
        out.__dict__.update(self.__dict__)
        out.expose_coefficients = True
        out._J_cache = None
        return out

    def coefficients(self, q: np.ndarray) -> np.ndarray:
        """c = Pi c~ (3K,)."""
        return self.Pi @ np.asarray(q, float).reshape(-1)

    def coef_from_points(self, X: np.ndarray) -> np.ndarray:
        """The parameters c~ stored in the coefficient rows of ``X`` (needs exposed rows)."""
        X = np.asarray(X, float)
        if not self.expose_coefficients or len(X) != self.n_points:
            raise ValueError("coefficient rows are not exposed in X")
        return coef_vector(X[self.N:self.N + self.K])

    def init(self, X0: np.ndarray) -> np.ndarray:
        """Initial c~ from points X0 (N or N + K rows).

        With exposed coefficient rows the parameters are read from them (exact round
        trip of ``points``); otherwise the ridge least-squares fit of
        A Pi c~ = X0 - X_bar (ridge 1e-9 x mean diag of J^T J), which is 0 for X0 = X_bar.
        """
        X0 = np.asarray(X0, float)
        if self.expose_coefficients:
            if X0.shape != (self.n_points, 3):
                raise ValueError(f"LinearBasis.init needs X0 of shape ({self.n_points}, 3), got {X0.shape}")
            return self.coef_from_points(X0)
        if X0.shape != (self.N, 3):
            raise ValueError(f"LinearBasis.init needs X0 of shape ({self.N}, 3), got {X0.shape}")
        J = self._J_lm
        H = J.T @ J
        lam = 1e-9 * max(float(np.trace(H)) / max(len(H), 1), 1e-300)
        return np.linalg.solve(H + lam * np.eye(len(H)), J.T @ (X0 - self.X_bar).ravel())

    def points(self, q: np.ndarray) -> np.ndarray:
        q = np.asarray(q, float).reshape(-1)
        W = coef_matrix(self.Pi @ q, self.K)
        X = self.X_bar + self.A @ W
        if self.expose_coefficients:
            X = np.vstack([X, coef_matrix(q, self.K)])
        return X

    def jacobian(self, q: np.ndarray) -> np.ndarray:
        if self._J_cache is None:
            if self.expose_coefficients:
                Jc = np.zeros((3 * self.K, 3 * self.K))
                j = np.arange(self.K)
                for d in range(3):
                    Jc[3 * j + d, d * self.K + j] = 1.0
                self._J_cache = np.vstack([self._J_lm, Jc])
            else:
                self._J_cache = self._J_lm.copy()
            self._J_cache.setflags(write=False)
        return self._J_cache

    # ------------------------------------------------------------------ mesh
    def vertices(self, c: np.ndarray, rows: np.ndarray | None = None) -> np.ndarray:
        """V_bar[rows] + Phi_rows W for *projected* coefficients c (3K,) (all rows when None)."""
        W = coef_matrix(c, self.K)
        if rows is None:
            return self.V_bar + self.deformer.apply(W)
        r = np.asarray(rows, np.int64).reshape(-1)
        return self.V_bar[r] + self.deformer.basis_rows(r) @ W

    def vertices_q(self, q: np.ndarray, rows: np.ndarray | None = None) -> np.ndarray:
        """Vertices for parameters c~ (applies Pi)."""
        return self.vertices(self.coefficients(q), rows)

    # ------------------------------------------------------------------ extremal points
    extremal_landmark = staticmethod(extremal_landmark)

    def extremal_point(self, q: np.ndarray, rows: np.ndarray, direction: np.ndarray,
                       T: float | None = None) -> tuple[np.ndarray, np.ndarray]:
        """Soft-argmax extremal point over candidate vertex ``rows`` and its Jacobian (3, 3K)
        with respect to c~ (DESIGN 4.16; recompute after each pose update)."""
        r = np.asarray(rows, np.int64).reshape(-1)
        Phi = self.deformer.basis_rows(r)                         # (n, K)
        Vr = self.V_bar[r] + Phi @ coef_matrix(self.coefficients(q), self.K)
        X, _, J = extremal_landmark(Vr, direction, T)
        dX = np.zeros((3, 3 * self.K))
        for d in range(3):
            dX[:, d * self.K:(d + 1) * self.K] = np.einsum("na,nk->ak", J[:, :, d], Phi)
        return X, dX @ self.Pi

    def __repr__(self) -> str:
        return (f"LinearBasis(K={self.K}, N={self.N}, scheme={self.scheme!r}, projector={self.projector}, "
                f"expose_coefficients={self.expose_coefficients})")


class BasisPrior:
    """Prior term on the stage-D displacement field of a :class:`LinearBasis` (WBS WP-17).

    E = 1/2 sum_d c~_d^T (K_cc + jitter I) c~_d / sigma^2 for each coordinate d, the
    RKHS norm of the Gaussian displacement field d(x) = sum_j phi_j(x) W_j: with this
    Gaussian-process reading the prior SD of each displacement coordinate at a centre is
    sigma (default 3 mm, DESIGN 4.15 residual surface sigma, 🧠).  The prior acts on the
    parameters c~ (the 7 similarity directions removed by Pi are held at zero by it, so
    the Hessian stays non-singular).  Residuals r = (I3 kron L^T) c~ / sigma, K_cc + jitter
    I = L L^T.  Needs the basis' coefficient rows (``with_coefficient_rows``); the term
    reads c~ from them and returns its Jacobian in the 'X' block on those rows only.
    ``is_prior = True`` (rows go to H_prior).
    """

    is_prior = True

    def __init__(self, basis: LinearBasis, sigma_mm: float | None = None, jitter: float | None = None,
                 name: str = "basis_prior"):
        if not basis.expose_coefficients:
            raise ValueError("BasisPrior needs a LinearBasis with coefficient rows (with_coefficient_rows())")
        self.basis = basis
        self.name = str(name)
        self.sigma = float(SHAPE_MODELS["coef_prior_sigma_mm"].value if sigma_mm is None else sigma_mm)
        if not self.sigma > 0:
            raise ValueError("sigma_mm must be > 0")
        jit = float(SHAPE_MODELS["coef_prior_jitter"].value if jitter is None else jitter)
        Kcc = np.asarray(basis.deformer.Kcc, float)
        self.L = np.linalg.cholesky(0.5 * (Kcc + Kcc.T) + jit * np.eye(len(Kcc)))
        K = basis.K
        M = np.zeros((3 * K, 3 * K))
        for d in range(3):
            M[d * K:(d + 1) * K, d * K:(d + 1) * K] = self.L.T / self.sigma
        self._M = M                                     # r = M c~
        n_pts = basis.n_points
        JX = np.zeros((3 * K, 3 * n_pts))
        j = np.arange(K)
        off = basis.coef_offset
        for d in range(3):
            JX[:, 3 * (off + j) + d] = M[:, d * K + j]
        self._JX = JX

    def n_params(self) -> int:
        return 0

    def init_params(self, state: Any) -> np.ndarray:
        return np.zeros(0)

    def residuals(self, state: Any, p: np.ndarray) -> np.ndarray:
        return self._M @ self.basis.coef_from_points(state.X)

    def jacobian(self, state: Any, p: np.ndarray) -> dict:
        return {"X": self._JX}
