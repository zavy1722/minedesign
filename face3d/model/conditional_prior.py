"""Conditional template prior: non-anatomical points given the anatomical backbone.

DESIGN 4.6, the "C" part of the shape prior::

    E_C = 1/2 || W_C ( X_C - T_C - B (X_A - T_A) ) ||^2

* ``A``: the anatomical backbone (ids of the ``anatomical44`` scheme), ``C``: the
  scheme's other points (e.g. MediaPipe indices without an anatomical id).
* ``T_A``, ``T_C``: their positions on the template kit (barycentric evaluation of
  the kit's embeddings; :meth:`face3d.model.template_kit.TemplateKit.landmark_positions`).
* ``B`` (n_C x n_A): the exact linear transfer of the biharmonic RBF warp of
  :class:`face3d.geometry.rbf.RBFWarp` (kernel ``phi(r) = r``, affine part
  ``[1, x, y, z]``, smoothing 0) from ``T_A`` to ``T_C``: a displacement field
  ``d_A`` of the backbone moves the C points by ``d_C = B d_A`` with::

      B = [Phi(T_C, T_A) | P_C] A_sys^-1[:, :n_A],
      A_sys = [[Phi(T_A, T_A), P_A], [P_A^T, 0]]   ((n_A + 4) square)

  applied to x, y and z separately.  Because the RBF reproduces affine fields,
  ``B`` does too, so the prior is invariant to any common affine map of A and C
  (in particular rigid motion and scale): it constrains shape only.
* ``W_C = diag(1 / (kappa * sigma_region))`` per point and coordinate, with the
  region of the embedding's dominant vertex (largest barycentric weight) and the
  region sigma table :data:`DEFAULT_REGION_SIGMA_MM` (DESIGN 4.6: lids 1.25, lips
  2.0, nose 2.5, brow 2.5, cheek 3.0, jaw 3.0, ears 4.0, scalp 4.5 mm; chin 3.0,
  neck 6.0, other 3.0 mm from WP-08; research basis *open-template-head-kit*
  Table 4 "per-region residual sigma"; all 🧠 provisional).  ``kappa`` defaults to
  1.5, the unknown-population inflation of DESIGN D-04 / 4.6 (anat R4.4).

Interface: WP-03's generalised prior (:class:`face3d.model.landmark_prior.GeneralisedPrior`):
``residual(X_all) -> (3 n_C,)`` whitened residuals (row ``3 i + axis`` for C point
``i``), ``jacobian(X_all) -> (3 n_C, 3 N)`` over a global point array ``X_all (N, 3)``
in mm, with the global rows of A and C given at construction (``index_A``,
``index_C``).  The residual is affine in ``X_all`` so the Jacobian is constant.
It stacks with :class:`face3d.model.landmark_prior.FactorPrior` in
:class:`face3d.model.landmark_prior.CompositePrior`.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping, Sequence

import numpy as np

from ..core.config import Default, register_defaults
from .template_kit import TemplateKit

__all__ = [
    "ConditionalTemplatePrior", "rbf_transfer_matrix", "DEFAULT_REGION_SIGMA_MM", "DEFAULT_KAPPA",
    "ANATOMICAL_SCHEME",
]

_BRAIN = "\U0001F9E0"   # expert knowledge, provisional
_NEW = "\U0001F195"     # introduced by this design, uncalibrated
_T4 = "research/blender/open-template-head-kit.md Table 4"

#: Scheme holding the anatomical backbone embeddings on a kit.
ANATOMICAL_SCHEME = "anatomical44"

_TP = register_defaults("template_prior", {
    "kappa": Default(1.5, _BRAIN, "DESIGN D-04 / 4.6: kappa 1.5 for an unknown population (anat R4.4)",
                     "", (1e-6, None)),
    "sigma_eyes_mm": Default(1.25, _BRAIN, f"DESIGN 4.6 lids 1.25; {_T4} lids, canthi 1.0-1.5", "mm", (1e-6, None)),
    "sigma_lips_mm": Default(2.0, _BRAIN, f"DESIGN 4.6 lips 2.0; {_T4} lips 1.5-2.5", "mm", (1e-6, None)),
    "sigma_nose_mm": Default(2.5, _BRAIN, f"DESIGN 4.6 nose 2.5; {_T4} nose 2-3", "mm", (1e-6, None)),
    "sigma_forehead_mm": Default(2.5, _BRAIN, f"DESIGN 4.6 brow 2.5; {_T4} brow, forehead 2-3", "mm",
                                 (1e-6, None)),
    "sigma_cheeks_mm": Default(3.0, _BRAIN, f"DESIGN 4.6 cheek 3.0; {_T4} cheek, malar 2.5-4", "mm",
                               (1e-6, None)),
    "sigma_jaw_mm": Default(3.0, _BRAIN, f"DESIGN 4.6 jaw 3.0; {_T4} jaw, chin 2-4", "mm", (1e-6, None)),
    "sigma_chin_mm": Default(3.0, _BRAIN, f"WP-08; {_T4} jaw, chin 2-4", "mm", (1e-6, None)),
    "sigma_ears_mm": Default(4.0, _BRAIN, f"DESIGN 4.6 ears 4.0; {_T4} ears 3-5", "mm", (1e-6, None)),
    "sigma_scalp_mm": Default(4.5, _BRAIN, f"DESIGN 4.6 scalp 4.5; {_T4} scalp, back of head 3-6", "mm",
                              (1e-6, None)),
    "sigma_neck_mm": Default(6.0, _BRAIN, f"WP-08; {_T4} neck 5-10", "mm", (1e-6, None)),
    "sigma_other_mm": Default(3.0, _NEW, "WP-08 (catch-all region; uncalibrated)", "mm", (1e-6, None)),
})

#: Default unknown-population inflation (DESIGN D-04, 4.6).
DEFAULT_KAPPA: float = float(_TP.kappa.value)

#: Region residual sigma (mm) of the conditional prior (see module docstring).
DEFAULT_REGION_SIGMA_MM: dict[str, float] = {
    r: float(_TP[f"sigma_{r}_mm"].value)
    for r in ("eyes", "lips", "nose", "forehead", "cheeks", "jaw", "chin", "ears", "scalp", "neck", "other")
}


def _pairwise(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Euclidean distances (same formula as face3d.geometry.rbf)."""
    d2 = np.sum(a * a, 1)[:, None] + np.sum(b * b, 1)[None, :] - 2.0 * a @ b.T
    return np.sqrt(np.maximum(d2, 0.0))


def rbf_transfer_matrix(T_A: np.ndarray, T_C: np.ndarray) -> np.ndarray:
    """Exact linear transfer ``B`` (n_C, n_A) of the biharmonic RBF warp (smoothing 0).

    For any displacement field ``d_A (n_A, 3)`` of the source points ``T_A``,
    ``B @ d_A`` equals ``RBFWarp(T_A, T_A + d_A).displacement(T_C)`` (kernel
    ``phi(r) = r``, affine part ``[1, x, y, z]``; :mod:`face3d.geometry.rbf`).
    Rows of ``B`` sum to one and reproduce affine fields exactly.

    Raises ValueError when the system is singular (fewer than 4 points, or all
    coplanar / coincident).
    """
    T_A = np.asarray(T_A, float).reshape(-1, 3)
    T_C = np.asarray(T_C, float).reshape(-1, 3)
    n = len(T_A)
    if n < 4:
        raise ValueError(f"the RBF transfer needs at least 4 anatomical points, got {n}")
    P_A = np.hstack([np.ones((n, 1)), T_A])
    A = np.zeros((n + 4, n + 4))
    A[:n, :n] = _pairwise(T_A, T_A)
    A[:n, n:] = P_A
    A[n:, :n] = P_A.T
    rhs = np.zeros((n + 4, n))
    rhs[:n] = np.eye(n)
    try:
        M = np.linalg.solve(A, rhs)
    except np.linalg.LinAlgError as e:
        raise ValueError("RBF system is singular (anatomical points coplanar or coincident?)") from e
    E = np.hstack([_pairwise(T_C, T_A), np.ones((len(T_C), 1)), T_C])
    return E @ M


def _index(a: Any, n: int, what: str) -> np.ndarray:
    idx = np.array(a, dtype=np.int64).reshape(-1)
    if idx.shape != (n,):
        raise ValueError(f"{what} must have one global row per point ({n}), got {idx.shape}")
    if np.any(idx < 0):
        raise ValueError(f"{what} must be non-negative")
    if len(np.unique(idx)) != n:
        raise ValueError(f"{what} has duplicate rows")
    idx.setflags(write=False)
    return idx


class ConditionalTemplatePrior:
    """Conditional prior of scheme points C given the anatomical backbone A (DESIGN 4.6; WP-08).

    Parameters
    ----------
    kit : the template kit providing ``T_A`` (scheme ``'anatomical44'``), ``T_C``
        (scheme ``scheme``) and the regions.
    scheme : scheme of the C points on the kit (e.g. ``'legacy_synthetic'``).
    other_names : names of the C points in that scheme (their order = C order).
    anatomical_ids : anatomical ids of the A points (their order = A order).
    kappa : population inflation of the region sigmas (default 1.5, DESIGN D-04).
    region_sigma_mm : overrides merged into :data:`DEFAULT_REGION_SIGMA_MM`.
    index_A, index_C : global rows of A and C in ``X_all`` (default
        ``0..n_A-1`` and ``n_A..n_A+n_C-1``).
    n_total : optional number of global rows (checked against the indices).

    Attributes: ``T_A (n_A, 3)``, ``T_C (n_C, 3)``, ``B (n_C, n_A)``, ``regions``
    (region name per C point), ``sigma_mm (n_C,)`` = kappa * region sigma,
    ``index`` (A rows then C rows), ``meta``.
    """

    def __init__(self, kit: TemplateKit, scheme: str, other_names: Sequence[str], anatomical_ids: Sequence[str],
                 kappa: float = DEFAULT_KAPPA, region_sigma_mm: Mapping[str, float] | None = None, *,
                 index_A: Any = None, index_C: Any = None, n_total: int | None = None):
        if not isinstance(kit, TemplateKit):
            raise TypeError("kit must be a TemplateKit")
        self.kit_id = kit.id
        self.topology_sha256 = kit.topology_sha256
        self.scheme = str(scheme)
        self.other_names = [str(x) for x in other_names]
        self.anatomical_ids = [str(x) for x in anatomical_ids]
        if not self.other_names:
            raise ValueError("other_names is empty")
        if len(set(self.other_names)) != len(self.other_names) \
                or len(set(self.anatomical_ids)) != len(self.anatomical_ids):
            raise ValueError("point names must be unique")
        self.kappa = float(kappa)
        if not self.kappa > 0.0:
            raise ValueError("kappa must be positive")
        table = dict(DEFAULT_REGION_SIGMA_MM)
        if region_sigma_mm:
            table.update({str(k): float(v) for k, v in region_sigma_mm.items()})
        if any(not v > 0.0 for v in table.values()):
            raise ValueError("region sigmas must be positive")
        self.region_sigma_mm = table

        self.T_A = kit.landmark_positions(ANATOMICAL_SCHEME, names=self.anatomical_ids)
        self.T_C = kit.landmark_positions(self.scheme, names=self.other_names)
        self.B = rbf_transfer_matrix(self.T_A, self.T_C)
        vreg = kit.vertex_regions(default="other")
        dom = kit.landmark_vertices(self.scheme, self.other_names)
        self.regions = [str(vreg[v]) for v in dom]
        missing = sorted({r for r in self.regions if r not in table})
        if missing:
            raise KeyError(f"no region sigma for regions {missing}; pass region_sigma_mm")
        self.sigma_mm = self.kappa * np.asarray([table[r] for r in self.regions], float)
        for a in (self.T_A, self.T_C, self.B, self.sigma_mm):
            a.setflags(write=False)

        n_A, n_C = len(self.anatomical_ids), len(self.other_names)
        iA = np.arange(n_A) if index_A is None else index_A
        iC = n_A + np.arange(n_C) if index_C is None else index_C
        self.index_A = _index(iA, n_A, "index_A")
        self.index_C = _index(iC, n_C, "index_C")
        if np.intersect1d(self.index_A, self.index_C).size:
            raise ValueError("index_A and index_C overlap")
        self.index = np.concatenate([self.index_A, self.index_C])
        self.index.setflags(write=False)
        self.n_total = None if n_total is None else int(n_total)
        if self.n_total is not None and self.index.max() >= self.n_total:
            raise ValueError(f"global index exceeds n_total={self.n_total}")
        self.meta: dict[str, Any] = {
            "rigid_invariant": True, "affine_invariant": True,
            "source": f"template kit {kit.id} ({'generated' if kit.generated else 'measured'}); "
                      f"region sigma DESIGN 4.6 / open-template-head-kit Table 4",
            "badge": _BRAIN, "kappa": self.kappa, "scheme": self.scheme,
        }

    # ------------------------------------------------------------------ basics
    @property
    def n_A(self) -> int:
        return len(self.anatomical_ids)

    @property
    def n_C(self) -> int:
        return len(self.other_names)

    def with_index(self, index_A: Any, index_C: Any, n_total: int | None = None) -> "ConditionalTemplatePrior":
        """A copy bound to other global rows (shares B, T and sigmas)."""
        out = copy.copy(self)
        out.meta = dict(self.meta)
        out.index_A = _index(index_A, self.n_A, "index_A")
        out.index_C = _index(index_C, self.n_C, "index_C")
        if np.intersect1d(out.index_A, out.index_C).size:
            raise ValueError("index_A and index_C overlap")
        out.index = np.concatenate([out.index_A, out.index_C])
        out.index.setflags(write=False)
        out.n_total = None if n_total is None else int(n_total)
        if out.n_total is not None and out.index.max() >= out.n_total:
            raise ValueError(f"global index exceeds n_total={out.n_total}")
        return out

    def _points(self, X_all: Any) -> np.ndarray:
        X = np.asarray(X_all, dtype=float)
        if X.ndim == 1 and X.size % 3 == 0:
            X = X.reshape(-1, 3)
        if X.ndim != 2 or X.shape[1] != 3:
            raise ValueError(f"X_all must be (N, 3), got {np.shape(X_all)}")
        if self.index.max() >= len(X):
            raise ValueError(f"X_all has {len(X)} rows; the prior needs row {int(self.index.max())}")
        if self.n_total is not None and len(X) != self.n_total:
            raise ValueError(f"X_all must have n_total={self.n_total} rows, got {len(X)}")
        return X

    # ------------------------------------------------------------------ prior
    def conditional_mean(self, X_A: Any) -> np.ndarray:
        """Mean of C given A: ``T_C + B (X_A - T_A)`` (n_C, 3) mm."""
        XA = np.asarray(X_A, float).reshape(self.n_A, 3)
        return self.T_C + self.B @ (XA - self.T_A)

    def residual(self, X_all: Any) -> np.ndarray:
        """Whitened residual ``(X_C - T_C - B (X_A - T_A)) / sigma``, flattened (3 n_C,)."""
        X = self._points(X_all)
        r = X[self.index_C] - self.conditional_mean(X[self.index_A])
        return (r / self.sigma_mm[:, None]).reshape(-1)

    def jacobian(self, X_all: Any) -> np.ndarray:
        """d residual / d vec(X_all), (3 n_C, 3 N); constant (the residual is affine)."""
        X = self._points(X_all)
        N = len(X)
        J = np.zeros((3 * self.n_C, 3 * N))
        inv = 1.0 / self.sigma_mm
        ax = np.arange(3)
        rows = (3 * np.arange(self.n_C)[:, None] + ax).reshape(-1)
        colsC = (3 * self.index_C[:, None] + ax).reshape(-1)
        J[rows, colsC] = np.repeat(inv, 3)
        colsA = (3 * self.index_A[:, None] + ax).reshape(-1)
        J[:, colsA] = np.kron(-self.B * inv[:, None], np.eye(3))
        return J

    def whiten_matrix(self, X_all: Any = None) -> np.ndarray:
        """The (constant) Jacobian; ``X_all`` only fixes N (default ``max(index) + 1`` or n_total)."""
        if X_all is None:
            N = self.n_total if self.n_total is not None else int(self.index.max()) + 1
            X_all = np.zeros((N, 3))
        return self.jacobian(X_all)

    def neg_log_density(self, X_all: Any) -> float:
        """0.5 ||residual||^2 (the log-determinant constant is dropped)."""
        r = self.residual(X_all)
        return 0.5 * float(r @ r)

    def __repr__(self) -> str:
        return (f"ConditionalTemplatePrior(kit={self.kit_id!r}, scheme={self.scheme!r}, n_A={self.n_A}, "
                f"n_C={self.n_C}, kappa={self.kappa})")
