"""Landmark-driven smooth deformation with radial basis functions.

The default kernel phi(r) = r is the biharmonic (thin-plate) spline in 3D: it
minimises bending energy, which is the standard choice for warping a template
head so that its landmarks land on target positions while the surface between
landmarks deforms smoothly (as in Wrap-style template fitting).

Conventions (WP-19; DESIGN 4.15 stage B, research MM-8)
-------------------------------------------------------
* Points are rows, ``(N, d)``; in the engine they are millimetres in the head frame.
* The fitted quantity is the displacement field: ``u(x) = Phi(x, src) w + [1, x] a`` with
  ``u(src_i) ~= dst_i - src_i``; ``warp(x) = x + u(x)``.
* ``smoothing`` is a scalar ``lambda`` or one ``lambda_i >= 0`` per landmark
  (``Lambda = diag(lambda_i)``).  The system is ``(Phi + sign Lambda) w + P a = y``,
  ``P^T w = 0`` with ``sign = -1`` for the biharmonic and multiquadric kernels (they are
  conditionally positive definite only as ``-phi``) and ``+1`` otherwise, so a larger
  ``lambda_i`` always means "trust landmark i less".
* ``normalise=False`` (legacy): ``lambda`` carries the units of the kernel (mm for
  ``phi = r``).  ``normalise=True``: coordinates are centred on the source centroid and
  divided by ``R_bar``, the RMS distance of ``src`` from its centroid, before solving, and
  the displacement is scaled back, so ``lambda`` is dimensionless (and ``eps`` of the
  Gaussian / multiquadric kernels is then in units of ``R_bar``).  For ``phi = r`` a
  dimensionless ``lambda`` equals a legacy ``lambda * R_bar`` in mm.
* The warp is linear in the targets: ``u(X_eval) = A (dst - src)`` with
  ``A = [Phi(X_eval, src), P_eval] inv(A_sys)[:, :N]`` (:meth:`RBFWarp.linear_map`), which
  is what the per-vertex uncertainty propagation uses (DESIGN 4.15 "Uncertainty").
"""
from __future__ import annotations

import numpy as np

from ..core.config import Default, register_defaults

_NEW = "\U0001F195"     # introduced by this design / WP spec

#: Candidate grid of the WP-19 alpha calibration (WBS WP-19 spec).
ALPHA_GRID: tuple[float, ...] = (0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0)

WARP = register_defaults("warp", {
    "alpha": Default(
        30.0, _NEW,
        "WP-19 calibration on the test bed (procedural kit n=24, 7-view studio ring, detector-sim defaults, bundle "
        "with the factor prior; 10 out-of-prior + 10 smooth in-space subjects; sigma_i = sqrt(tr Cov_i) of the "
        "posterior). Median landmark residual RMS / sigma per grid value 0.1..100: 0.001, 0.004, 0.011, 0.03, "
        "0.08, 0.15, 0.26 - the WP-19 target band [0.5, 1.0] is NOT reached on the grid (the posteriors are "
        "already prior-smoothed). Chosen by the remaining evidence: worst stage-B fold-gate min det -0.18 "
        "(alpha <= 1; folds at the chin), 0.15 (3), 0.37 (10), 0.65 (30), 0.85 (100); stage-B face RMS "
        "out-of-prior 2.19 / 2.23 / 2.26 / 2.38 mm and in-space 1.83 / 1.77 / 1.69 / 1.62 mm at alpha -> 0 / "
        "10 / 30 / 100. alpha = 30 is the largest value that costs < 5 % out-of-prior accuracy and clears the "
        "0.2 fold gate with margin. DESIGN 4.15 B (MM-8) quoted 1e-2 in mm^2 units, uncalibrated.",
        "", (0.0, None)),
})


def _kernel(r: np.ndarray, kind: str, eps: float) -> np.ndarray:
    if kind == "biharmonic":
        return r
    if kind == "triharmonic":
        return r ** 3
    if kind == "gaussian":
        return np.exp(-(r / eps) ** 2)
    if kind == "multiquadric":
        return np.sqrt(r * r + eps * eps)
    raise ValueError(f"unknown kernel {kind!r}")


def _pairwise(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    d2 = np.sum(a * a, 1)[:, None] + np.sum(b * b, 1)[None, :] - 2.0 * a @ b.T
    return np.sqrt(np.maximum(d2, 0.0))


class RBFWarp:
    """Fit once on (source landmarks -> target landmarks), then apply to any points.

    `smoothing` > 0 turns exact interpolation into regularised approximation, which
    is what you want with noisy landmarks (e.g. from a detector).  It is a scalar or a
    per-landmark array ``(N,)`` (``Lambda = diag(lambda_i)``; see the module docstring
    for the sign rule and for ``normalise``).
    """

    def __init__(self, src: np.ndarray, dst: np.ndarray, kind: str = "biharmonic",
                 smoothing: float | np.ndarray = 0.0, eps: float = 1.0, normalise: bool = False):
        src = np.asarray(src, float)
        dst = np.asarray(dst, float)
        if src.shape != dst.shape:
            raise ValueError("src and dst must have the same shape")
        n, d = src.shape
        lam = np.asarray(smoothing, float)
        if lam.ndim == 0:
            lam = np.full(n, float(lam))
        elif lam.shape != (n,):
            raise ValueError(f"smoothing must be a scalar or have shape ({n},), got {lam.shape}")
        if not np.all(np.isfinite(lam)) or np.any(lam < 0):
            raise ValueError("smoothing must be finite and >= 0")
        self.kind, self.eps = kind, eps
        self.normalise = bool(normalise)
        self.smoothing = lam
        self.src_mm = src
        if self.normalise:
            self.centre = src.mean(axis=0)
            self.R_bar = rms_radius(src)
            if not self.R_bar > 0:
                raise ValueError("normalise=True needs source points that are not all coincident")
        else:
            self.centre = np.zeros(d)
            self.R_bar = 1.0
        # ``src`` is the centre set in solver coordinates (== the input when not normalised).
        self.src = src if not self.normalise else (src - self.centre) / self.R_bar
        Phi = _kernel(_pairwise(self.src, self.src), kind, eps)
        P = np.hstack([np.ones((n, 1)), self.src])
        A = np.zeros((n + d + 1, n + d + 1))
        # Smoothing splines solve (K_cpd + lam I) w + P a = y with K_cpd the
        # conditionally POSITIVE definite form of the kernel. In 3D, r and the
        # multiquadric are CPD only with a minus sign (-r, -sqrt(r^2+c^2)), so for
        # them the system written with phi itself is (Phi - lam I). r^3 (CPD order 2)
        # and the Gaussian (PD) keep +lam. Using +lam with phi = r makes the system
        # indefinite and can blow landmark errors up to hundreds of mm.
        self.sign = -1.0 if kind in ("biharmonic", "multiquadric") else 1.0
        A[:n, :n] = Phi + self.sign * np.diag(lam)
        A[:n, n:] = P
        A[n:, :n] = P.T
        b = np.zeros((n + d + 1, d))
        b[:n] = (dst - src) / self.R_bar  # fit the displacement field
        self._A_sys = A
        self._Phi = Phi
        self._inv_cols: np.ndarray | None = None
        sol = np.linalg.lstsq(A, b, rcond=None)[0]
        self.w = sol[:n]
        self.a = sol[n:]

    # ------------------------------------------------------------------ evaluation
    def _coords(self, X: np.ndarray) -> np.ndarray:
        return X if not self.normalise else (X - self.centre) / self.R_bar

    def _eval_rows(self, x: np.ndarray) -> np.ndarray:
        """[Phi(x, src), 1, x] in solver coordinates, (m, N + d + 1)."""
        xs = self._coords(x)
        return np.hstack([_kernel(_pairwise(xs, self.src), self.kind, self.eps), np.ones((len(xs), 1)), xs])

    def displacement(self, X: np.ndarray, chunk: int = 20000) -> np.ndarray:
        """Displacement ``u(X)`` (same units as the inputs) at points ``X`` (m, d)."""
        X = np.asarray(X, float)
        out = np.empty_like(X)
        sol = np.vstack([self.w, self.a])
        for i in range(0, len(X), chunk):
            out[i:i + chunk] = self.R_bar * (self._eval_rows(X[i:i + chunk]) @ sol)
        return out

    def __call__(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, float)
        return X + self.displacement(X)

    # ------------------------------------------------------------------ linear map
    def linear_map(self, X_eval: np.ndarray, chunk: int = 20000) -> np.ndarray:
        """Rows ``A`` (n_eval, N) with ``displacement(X_eval) == A @ (dst - src)``.

        ``A = [Phi(X_eval, src), P_eval] @ inv(A_sys)[:, :N]`` (affine part included);
        the same ``A`` acts on each coordinate, and it does not depend on ``dst``
        (DESIGN 4.15 "Uncertainty").  The normalisation cancels: the right-hand side is
        divided by ``R_bar`` and the displacement multiplied by it.  ``inv(A_sys)[:, :N]``
        is the minimum-norm least-squares solution, exactly as in the fit.
        """
        if self._inv_cols is None:
            n = len(self.src)
            E = np.zeros((self._A_sys.shape[0], n))
            E[:n] = np.eye(n)
            self._inv_cols = np.linalg.lstsq(self._A_sys, E, rcond=None)[0]
        X_eval = np.asarray(X_eval, float)
        out = np.empty((len(X_eval), len(self.src)))
        for i in range(0, len(X_eval), chunk):
            out[i:i + chunk] = self._eval_rows(X_eval[i:i + chunk]) @ self._inv_cols
        return out

    # ------------------------------------------------------------------ diagnostics
    def bending_energy(self) -> float:
        """Spline (semi-norm) energy ``sign * sum_d w_d^T Phi w_d`` in solver coordinates.

        Non-negative for the conditionally positive definite kernels because
        ``P^T w = 0``; it falls monotonically as the smoothing rises (MM-8).
        """
        return float(self.sign * np.einsum("id,ij,jd->", self.w, self._Phi, self.w))

    def residual(self, dst: np.ndarray) -> np.ndarray:
        """Per-landmark misfit norm ``|warp(src_i) - dst_i|`` (N,), input units."""
        return np.linalg.norm(self(self.src_mm) - np.asarray(dst, float), axis=1)


def rms_radius(src: np.ndarray) -> float:
    """``R_bar``: RMS distance of the points (N, d) from their centroid (input units)."""
    src = np.asarray(src, float)
    return float(np.sqrt(np.mean(np.sum((src - src.mean(axis=0)) ** 2, axis=1))))


def per_landmark_lambda(sigma_mm: np.ndarray, R_bar: float, alpha: float | None = None) -> np.ndarray:
    """Dimensionless per-landmark smoothing ``lambda_i = alpha * (sigma_i / R_bar)^2``.

    sigma_mm : (N,) 1-sigma position uncertainty of each target landmark, mm.
    R_bar : RMS radius of the source landmarks, mm (:func:`rms_radius`).
    alpha : gain; default the registered ``warp.alpha`` (calibrated in WP-19, see its
        source string).  Use with ``RBFWarp(..., normalise=True)`` (DESIGN 4.15 stage B,
        MM-8: ``Lambda = diag(alpha sigma_i^2)`` in normalised units).
    """
    a = float(WARP["alpha"].value if alpha is None else alpha)
    if a < 0 or not R_bar > 0:
        raise ValueError("alpha must be >= 0 and R_bar > 0")
    s = np.asarray(sigma_mm, float)
    if np.any(~np.isfinite(s)) or np.any(s < 0):
        raise ValueError("sigma_mm must be finite and >= 0")
    return a * (s / float(R_bar)) ** 2
