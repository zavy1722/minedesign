"""Gauge-projected NEES and per-axis coverage of reported landmark uncertainty.

Conventions
-----------
* ``err`` is estimate minus truth, (N, 3) in mm, after any alignment the caller
  chose (the scenario runner similarity-aligns first; research/reconstruction/
  validation-test-bed.md "Similarity-align, then project the covariance").
* ``cov`` is the (3N, 3N) covariance of the flattened points in **point-major**
  order (row ``3i + a`` = point i, axis a), in mm^2; alternatively ``sigma`` (N, 3)
  gives per-axis 1-sigma values (mm) and means ``cov = diag(sigma.ravel()**2)``.
* ``X_ref`` (N, 3) is the shape at which the similarity tangent is evaluated (the
  truth in the test bed).

Definitions (DESIGN 7.3): with P the gauge projector (:func:`face3d.eval.align.gauge_projector`),
e_p = P e and C_p = P C P,

    NEES = e_p^T C_p^+ e_p,     dof = rank(C_p)  (= 3N - 7 for a full-rank C),

reported as NEES/dof (target 0.8-1.25, DESIGN 7.5). A correctly specified Gaussian
error gives NEES ~ chi^2(dof), so NEES/dof has mean 1. Per-axis coverage counts the
fraction of projected coordinates with |e_p,j| / sqrt(C_p,jj) < k (Gaussian
yardsticks 0.683 / 0.954 for k = 1 / 2; validation-test-bed.md Table 4).
Scale is evaluated separately as z = (zeta_hat - zeta) / sigma_zeta (DESIGN 7.3).

Rows with any NaN in ``err``, ``X_ref`` (or ``sigma``) are dropped consistently from
the error, the covariance and the reference shape before projection.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np

from .align import gauge_projector

__all__ = ["PINV_RCOND", "COV_DIAG_MIN", "projected_error_and_cov", "projected_z",
           "nees", "axis_coverage", "scale_z"]

# Relative eigenvalue cut-off for the pseudo-inverse of C_p (WBS WP-01 spec: pinv(rcond=1e-10)).
PINV_RCOND = 1e-10
# Coordinates whose projected variance is below this (mm^2) are excluded from coverage (WBS WP-01).
COV_DIAG_MIN = 1e-12


def _as_cov(err: np.ndarray, cov_or_sigma: np.ndarray | None, sigma: np.ndarray | None
            ) -> tuple[np.ndarray, np.ndarray | None]:
    """Return (cov (3N,3N), sigma-or-None) from either argument form."""
    n = len(err)
    if sigma is not None and cov_or_sigma is not None:
        raise ValueError("give either cov or sigma, not both")
    if sigma is None and cov_or_sigma is not None:
        c = np.asarray(cov_or_sigma, float)
        if c.shape == (n, 3):
            sigma = c
        elif c.shape == (3 * n, 3 * n):
            return c, None
        else:
            raise ValueError("cov must be (3N, 3N) or sigma (N, 3); got %s for N=%d" % (c.shape, n))
    if sigma is None:
        raise ValueError("a covariance (3N, 3N) or per-axis sigma (N, 3) is required")
    s = np.asarray(sigma, float)
    if s.shape != (n, 3):
        raise ValueError("sigma must have shape (N, 3)")
    s2 = np.where(np.isfinite(s), s, 0.0).ravel() ** 2
    return np.diag(s2), s


def projected_error_and_cov(err: np.ndarray, cov: np.ndarray | None = None,
                            X_ref: np.ndarray | None = None, project: bool = True, *,
                            sigma: np.ndarray | None = None
                            ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Drop NaN rows, then gauge-project.

    Returns ``(e_p (3M,), C_p (3M, 3M), keep (N,) bool)`` where M is the number of
    kept points. With ``project=False`` the error and covariance are only
    restricted to the kept rows. ``cov`` may also be an (N, 3) sigma array.
    """
    err = np.asarray(err, float)
    if err.ndim != 2 or err.shape[1] != 3:
        raise ValueError("err must have shape (N, 3)")
    C, sig = _as_cov(err, cov, sigma)
    keep = np.isfinite(err).all(1)
    if X_ref is not None:
        X_ref = np.asarray(X_ref, float)
        if X_ref.shape != err.shape:
            raise ValueError("X_ref must have the same shape as err")
        keep &= np.isfinite(X_ref).all(1)
    if sig is not None:
        keep &= np.isfinite(sig).all(1)
    rows = (3 * np.flatnonzero(keep)[:, None] + np.arange(3)).ravel()
    e = err[keep].ravel()
    C = C[np.ix_(rows, rows)]
    if not np.isfinite(C).all():
        raise ValueError("covariance has non-finite entries on the kept rows")
    if project:
        if X_ref is None:
            raise ValueError("project=True needs X_ref (the shape at which the gauge is evaluated)")
        P = gauge_projector(X_ref[keep])
        e = P @ e
        C = P @ C @ P
        C = 0.5 * (C + C.T)
    return e, C, keep


def projected_z(err: np.ndarray, cov: np.ndarray | None = None, X_ref: np.ndarray | None = None,
                project: bool = True, *, sigma: np.ndarray | None = None) -> np.ndarray:
    """Per-coordinate z-scores e_p,j / sqrt(C_p,jj) of the kept rows, flattened.

    Coordinates with C_p,jj <= :data:`COV_DIAG_MIN` mm^2 are returned as NaN.
    """
    e, C, _ = projected_error_and_cov(err, cov, X_ref, project, sigma=sigma)
    d = np.diag(C)
    z = np.full(len(e), np.nan)
    ok = d > COV_DIAG_MIN
    z[ok] = e[ok] / np.sqrt(d[ok])
    return z


def nees(err: np.ndarray, cov: np.ndarray | None = None, X_ref: np.ndarray | None = None,
         project: bool = True, *, sigma: np.ndarray | None = None,
         rcond: float = PINV_RCOND) -> tuple[float, int]:
    """Normalised estimation error squared per degree of freedom.

    ``cov`` is the (3N, 3N) covariance or an (N, 3) per-axis sigma (also accepted as
    the keyword ``sigma``). With ``project`` (default) the error and covariance are
    projected off the 7-DoF similarity tangent at ``X_ref`` (DESIGN 7.3). The
    pseudo-inverse keeps eigenvalues above ``rcond`` x the largest one; ``dof`` is the
    number kept (3N - 7 for a full-rank covariance after projection).

    Returns ``(nees_per_dof, dof)``; ``(nan, 0)`` when nothing is left.
    """
    e, C, _ = projected_error_and_cov(err, cov, X_ref, project, sigma=sigma)
    if len(e) == 0:
        return float("nan"), 0
    w, V = np.linalg.eigh(C)
    wmax = float(w.max()) if len(w) else 0.0
    if not wmax > 0.0:
        return float("nan"), 0
    pos = w > rcond * wmax
    dof = int(pos.sum())
    q = V[:, pos].T @ e
    val = float(np.sum(q * q / w[pos]))
    return val / dof, dof


def axis_coverage(err: np.ndarray, cov: np.ndarray | None = None, X_ref: np.ndarray | None = None,
                  ks: Sequence[float] = (1, 2), project: bool = True, *,
                  sigma: np.ndarray | None = None) -> dict:
    """Fraction of (projected) coordinates whose |z| is below each k in ``ks``.

    Only coordinates with projected variance > :data:`COV_DIAG_MIN` mm^2 count.
    Returns ``{k: fraction}`` (NaN when no coordinate qualifies).
    """
    z = projected_z(err, cov, X_ref, project, sigma=sigma)
    z = np.abs(z[np.isfinite(z)])
    out = {}
    for k in ks:
        out[k] = float(np.mean(z < k)) if len(z) else float("nan")
    return out


def scale_z(zeta_est: float, zeta_true: float, sigma: float) -> float:
    """Scale z-score (zeta_hat - zeta) / sigma_zeta, with zeta the log-scale (DESIGN 7.3)."""
    sigma = float(sigma)
    if not sigma > 0.0:
        return float("nan")
    return (float(zeta_est) - float(zeta_true)) / sigma
