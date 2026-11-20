"""Alignment and gauge projection for evaluating landmark estimates.

Conventions
-----------
* Points are (N, 3) arrays in millimetres in the head frame (+x subject's left,
  +y up, +z out of the face; DESIGN 3.1).
* Flattened vectors and 3N x 3N matrices use **point-major** order: row/column
  ``3*i + a`` is point ``i``, axis ``a`` (a = 0, 1, 2 for x, y, z). This is the
  order of ``X.ravel()`` and of ``BundleResult.X.ravel()``.

Gauge
-----
Photos fix a head only up to a 7-DoF similarity (translation, rotation, scale);
the prior picks one representative. Errors and covariances are therefore
compared on the complement of the similarity tangent at the reference shape
(DESIGN 7.3 "gauge-projected"; research/reconstruction/validation-test-bed.md,
"Test sigma in a gauge-free frame": P = I - G (G^T G)^-1 G^T with G the 3N x 7
similarity tangent).

Alignment modes (DESIGN 7.3, rec EV-1 / research/reconstruction/benchmarks-metrics.md
"NoW protocol"):
* ``'rigid'``      - Umeyama without scale on all (or ``idx``) points;
* ``'similarity'`` - Umeyama with scale on all (or ``idx``) points;
* ``'now7'``       - NoW-style: rigid (no scale) on the 7 NoW landmarks (four eye
  corners, nose tip, two mouth corners), applied to every point.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np

from ..geometry.procrustes import apply_similarity, umeyama

__all__ = [
    "NOW7_NAMES", "NOW7_LEGACY_NAMES", "similarity_tangent_basis", "gauge_projector",
    "now7_indices", "align",
]

# NoW 7-landmark alignment set (rec EV-1; benchmarks-metrics.md: "4 eye corners, a nose
# point, 2 mouth corners"), in the scheme-registry short names and in the legacy
# face3d.synthetic names. Order: ex_L, en_L, en_R, ex_R, prn, ch_L, ch_R (WBS WP-01).
NOW7_NAMES: tuple[str, ...] = ("ex_L", "en_L", "en_R", "ex_R", "prn", "ch_L", "ch_R")
NOW7_LEGACY_NAMES: tuple[str, ...] = (
    "exocanthion_L", "endocanthion_L", "endocanthion_R", "exocanthion_R",
    "pronasale", "cheilion_L", "cheilion_R",
)

_MODES = ("rigid", "similarity", "now7")


def similarity_tangent_basis(X: np.ndarray, rigid_only: bool = False) -> np.ndarray:
    """Tangent of the similarity orbit of the point set ``X`` (N, 3).

    Returns G with shape (3N, 7), or (3N, 6) when ``rigid_only``. Row ``3i + a`` is
    point ``i``, axis ``a``. Columns:

    * 0-2: translations along x, y, z (G[3i + a, a] = 1);
    * 3-5: infinitesimal rotations about the x, y, z axes through the centroid
      X̄: column k is ``flatten(e_k x (X_i - X̄))``;
    * 6 (similarity only): isotropic scale about the centroid, ``flatten(X_i - X̄)``.

    Units: translation columns are dimensionless (mm per mm), rotation columns are
    mm per radian, the scale column is mm per unit log-scale. Projectors built from
    G are independent of these column scalings.
    """
    X = np.asarray(X, float)
    if X.ndim != 2 or X.shape[1] != 3:
        raise ValueError("X must have shape (N, 3)")
    n = len(X)
    Xc = X - X.mean(0)
    ncol = 6 if rigid_only else 7
    G = np.zeros((3 * n, ncol))
    for a in range(3):
        G[a::3, a] = 1.0
    for k in range(3):
        e = np.zeros(3)
        e[k] = 1.0
        G[:, 3 + k] = np.cross(e, Xc).ravel()
    if not rigid_only:
        G[:, 6] = Xc.ravel()
    return G


def gauge_projector(X: np.ndarray, rigid_only: bool = False) -> np.ndarray:
    """Orthogonal projector onto the complement of the similarity tangent at ``X``.

    P = I - G (G^T G)^-1 G^T with G = :func:`similarity_tangent_basis` (DESIGN 7.3).
    It is computed as I - U U^T from an orthonormal basis U of range(G) (thin SVD,
    singular values below 1e-12 x the largest dropped), which equals the formula
    above when G has full column rank and stays exactly symmetric and idempotent to
    rounding error when it does not (e.g. collinear points, where one rotation
    column vanishes). Shape (3N, 3N), dimensionless.
    """
    G = similarity_tangent_basis(X, rigid_only)
    U, s, _ = np.linalg.svd(G, full_matrices=False)
    keep = s > 1e-12 * (s[0] if len(s) and s[0] > 0 else 1.0)
    U = U[:, keep]
    P = np.eye(G.shape[0]) - U @ U.T
    return 0.5 * (P + P.T)


def now7_indices(names: Sequence[str]) -> np.ndarray:
    """Indices of the 7 NoW alignment landmarks in ``names``.

    Accepts the registry short names (:data:`NOW7_NAMES`) or the legacy synthetic
    names (:data:`NOW7_LEGACY_NAMES`); raises ``ValueError`` if neither set is
    complete.
    """
    lookup = {n: i for i, n in enumerate(names)}
    for cand in (NOW7_NAMES, NOW7_LEGACY_NAMES):
        if all(c in lookup for c in cand):
            return np.array([lookup[c] for c in cand], dtype=np.int64)
    raise ValueError("names contain neither the NoW-7 short names %s nor the legacy names %s"
                     % (NOW7_NAMES, NOW7_LEGACY_NAMES))


def align(est: np.ndarray, ref: np.ndarray, mode: str = "similarity",
          idx: Sequence[int] | np.ndarray | None = None,
          weights: np.ndarray | None = None,
          names: Sequence[str] | None = None) -> tuple[float, np.ndarray, np.ndarray, np.ndarray]:
    """Align ``est`` (N, 3) onto ``ref`` (N, 3) with :func:`face3d.geometry.procrustes.umeyama`.

    Parameters
    ----------
    mode : ``'rigid'`` (no scale), ``'similarity'`` (with scale) or ``'now7'`` (rigid on
        the 7 NoW landmarks, looked up in ``names``; rec EV-1).
    idx : optional subset of point indices used for the fit (all points by default;
        for ``'now7'`` it overrides the name lookup).
    weights : optional per-point weights (length N), restricted to the fit subset.
    names : landmark names, required for ``'now7'`` unless ``idx`` is given.

    Rows with NaN in ``est`` or ``ref`` are excluded from the fit (but are still
    transformed). Returns ``(s, R, t, aligned_est)`` with ``ref ≈ s R est + t`` and
    ``aligned_est = s * est @ R.T + t`` for every point; ``s`` is 1 for rigid modes.
    """
    if mode not in _MODES:
        raise ValueError("mode must be one of %s, got %r" % (_MODES, mode))
    est = np.asarray(est, float)
    ref = np.asarray(ref, float)
    if est.shape != ref.shape or est.ndim != 2 or est.shape[1] != 3:
        raise ValueError("est and ref must both have shape (N, 3)")
    n = len(est)
    if mode == "now7" and idx is None:
        if names is None:
            raise ValueError("mode 'now7' needs `names` (or an explicit `idx`)")
        idx = now7_indices(names)
    sel = np.arange(n) if idx is None else np.asarray(idx, dtype=np.int64)
    w = None if weights is None else np.asarray(weights, float).reshape(-1)
    if w is not None and len(w) != n:
        raise ValueError("weights must have length N")
    ok = np.isfinite(est[sel]).all(1) & np.isfinite(ref[sel]).all(1)
    sel = sel[ok]
    if len(sel) < 3:
        raise ValueError("alignment needs at least 3 finite corresponding points")
    with_scale = mode == "similarity"
    s, R, t = umeyama(est[sel], ref[sel], with_scale=with_scale,
                      weights=None if w is None else w[sel])
    return s, R, t, apply_similarity(est, s, R, t)
