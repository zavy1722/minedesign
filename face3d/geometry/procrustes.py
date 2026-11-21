"""Similarity alignment (Umeyama 1991), reflection Procrustes and symmetry planes; numpy only.

Implements the geometry half of DESIGN D-15, 4.11 (plane re-fitted by weighted
reflection Procrustes; anat R3.3) and 4.15 stage A (Umeyama, proper *and*
reflected, on the anatomical landmarks).

Conventions
-----------
* Points are rows: ``src`` / ``dst`` are ``(N, d)`` arrays (any dimension ``d``;
  the symmetry-plane functions are 3-D only).  Lengths are whatever the caller
  uses; in the engine they are millimetres in the head frame (DESIGN 3.1:
  +x subject's left, +y up, +z out of the face).
* A similarity is ``dst ≈ s * R @ src + t`` (row form ``s * src @ R.T + t``,
  :func:`apply_similarity`).
* **Plane** ``(n, d)``: the set ``{x : n . x = d}`` with ``n`` a unit normal and
  ``d`` the signed offset (mm) of the plane from the origin along ``n``.  The
  reflection about it is ``x' = (I - 2 n n^T) x + 2 d n`` (:func:`reflect`).
  :func:`fit_symmetry_plane` returns ``n`` with ``n_x > 0`` (the head frame's
  sagittal plane is ``n = (1, 0, 0)``, ``d = 0``).
* Weights are relative (only their ratios matter); they are normalised to sum 1.
  Every RMSE returned here is the weighted RMS of the point residual norms,
  ``sqrt(sum_i w_i |r_i|^2 / sum_i w_i)``, which is the plain RMS when
  ``weights`` is None.

Determinant handling (Umeyama 1991, eq. 39-43): the SVD of the weighted cross
covariance ``U S V^T`` gives ``R = U D V^T``.  ``D = I`` is the unconstrained
orthogonal optimum (``det R`` may be -1); the classical correction
``D[-1, -1] = -1`` when ``det U det V < 0`` forces a proper rotation; the "sign
trick" ``D[-1, -1] = -sign(det U det V)`` forces the best *improper* transform
(``det R = -1``).  :func:`umeyama` keeps its historical behaviour (proper
rotation) unless ``allow_reflection=True``.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "umeyama", "umeyama_proper_and_reflected", "apply_similarity", "procrustes_rmse",
    "fit_symmetry_plane", "reflect", "reflection_matrix", "permute_pairs",
]

#: Default sagittal plane of the head frame (DESIGN 3.1): normal +x, offset 0 mm.
SAGITTAL_NORMAL: tuple[float, float, float] = (1.0, 0.0, 0.0)

#: Minimum number of bilateral pairs for a plane fit; with fewer the head-frame
#: sagittal plane is returned (WP-12 spec; 🆕 uncalibrated -- three pairs plus the
#: midline make the 3x3 cross covariance well conditioned in practice).
MIN_PAIRS_PLANE_FIT: int = 3


def _normalised_weights(n: int, weights: np.ndarray | None) -> np.ndarray:
    w = np.ones(n) if weights is None else np.asarray(weights, float)
    return w / w.sum()


def _align(src: np.ndarray, dst: np.ndarray, with_scale: bool, weights: np.ndarray | None,
           det_mode: str) -> tuple[float, np.ndarray, np.ndarray]:
    """Weighted Umeyama core.  ``det_mode``: 'proper' (det +1), 'free' (D = I) or 'improper' (det -1).

    The 'proper' branch is the exact arithmetic of the historical ``umeyama`` so
    that its default results are bit-for-bit unchanged.
    """
    src = np.asarray(src, float)
    dst = np.asarray(dst, float)
    n, d = src.shape
    w = _normalised_weights(n, weights)
    mu_s = w @ src
    mu_d = w @ dst
    xs = src - mu_s
    xd = dst - mu_d
    cov = (xd * w[:, None]).T @ xs
    U, S, Vt = np.linalg.svd(cov)
    D = np.eye(d)
    if det_mode == "proper":
        if np.linalg.det(U) * np.linalg.det(Vt) < 0:
            D[-1, -1] = -1.0
    elif det_mode == "improper":
        # Sign trick: det(R) = det(U) det(Vt) D[-1,-1] = -1.
        D[-1, -1] = -1.0 if np.linalg.det(U) * np.linalg.det(Vt) > 0 else 1.0
    elif det_mode != "free":
        raise ValueError(f"unknown det_mode {det_mode!r}")
    R = U @ D @ Vt
    if with_scale:
        var_s = float(w @ np.sum(xs * xs, axis=1))
        s = float(np.trace(np.diag(S) @ D) / var_s) if var_s > 0 else 1.0
    else:
        s = 1.0
    t = mu_d - s * R @ mu_s
    return s, R, t


def umeyama(src: np.ndarray, dst: np.ndarray, with_scale: bool = True,
            weights: np.ndarray | None = None,
            allow_reflection: bool = False) -> tuple[float, np.ndarray, np.ndarray]:
    """Least-squares similarity transform with dst ≈ s * R @ src + t.

    Works in any dimension (N, d). Optional per-point weights (relative).
    Returns (s, R, t).

    By default ``R`` is a proper rotation (det +1; Umeyama's determinant
    correction), exactly as before WP-12.  With ``allow_reflection=True`` the
    correction is skipped (``D = I``), so ``R`` is the unconstrained orthogonal
    optimum and may have det -1 (a reflected similarity is then recovered
    exactly).
    """
    return _align(src, dst, with_scale, weights, "free" if allow_reflection else "proper")


def apply_similarity(X: np.ndarray, s: float, R: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Row-form similarity ``s * X @ R.T + t``."""
    return s * np.asarray(X, float) @ R.T + t


def _weighted_rmse(residual: np.ndarray, weights: np.ndarray | None) -> float:
    r2 = np.sum(np.asarray(residual, float) ** 2, axis=1)
    if len(r2) == 0:
        return float("nan")
    w = _normalised_weights(len(r2), weights)
    return float(np.sqrt(max(float(w @ r2), 0.0)))


def procrustes_rmse(src: np.ndarray, dst: np.ndarray, with_scale: bool = True) -> float:
    """RMS distance after optimal similarity alignment of src onto dst."""
    s, R, t = umeyama(src, dst, with_scale)
    d = apply_similarity(src, s, R, t) - dst
    return float(np.sqrt(np.mean(np.sum(d * d, axis=1))))


def umeyama_proper_and_reflected(src: np.ndarray, dst: np.ndarray, weights: np.ndarray | None = None,
                                 with_scale: bool = True) -> dict[str, tuple[float, np.ndarray, np.ndarray, float]]:
    """Best proper and best improper similarity of ``src`` onto ``dst`` (DESIGN 4.15 stage A).

    Returns ``{'proper': (s, R, t, rmse), 'reflected': (s, R, t, rmse)}`` where
    ``'proper'`` has ``det R = +1`` (the default :func:`umeyama`) and
    ``'reflected'`` is the best transform with ``det R = -1`` (forced by the sign
    trick ``D[-1, -1] = -sign(det U det V)``).  ``rmse`` is the (weighted) RMS
    residual of ``apply_similarity(src, s, R, t) - dst`` in the units of ``dst``.

    Stage A reads a reflected RMSE below 0.5x the proper one as a mirrored source
    (DESIGN 4.15; never auto-flipped -- see
    :func:`face3d.fit.symmetry.detect_mirrored_source`).
    """
    src = np.asarray(src, float)
    dst = np.asarray(dst, float)
    if src.shape != dst.shape or src.ndim != 2:
        raise ValueError(f"src and dst must both be (N, d); got {src.shape} and {dst.shape}")
    out: dict[str, tuple[float, np.ndarray, np.ndarray, float]] = {}
    for key, mode in (("proper", "proper"), ("reflected", "improper")):
        s, R, t = _align(src, dst, with_scale, weights, mode)
        out[key] = (s, R, t, _weighted_rmse(apply_similarity(src, s, R, t) - dst, weights))
    return out


# ============================================================================ planes
def _unit_plane(n: np.ndarray | tuple, d: float) -> tuple[np.ndarray, float]:
    n = np.asarray(n, float).reshape(3)
    norm = float(np.linalg.norm(n))
    if not np.isfinite(norm) or norm == 0.0:
        raise ValueError(f"plane normal must be a finite non-zero 3-vector, got {n}")
    if norm == 1.0:
        return n, float(d)
    # The plane {x: n.x = d} is unchanged when n and d are scaled together.
    return n / norm, float(d) / norm


def reflection_matrix(n: np.ndarray | tuple) -> np.ndarray:
    """Householder matrix ``I - 2 n n^T`` for the (normalised) normal ``n``."""
    n, _ = _unit_plane(n, 0.0)
    return np.eye(3) - 2.0 * np.outer(n, n)


def reflect(X: np.ndarray, n: np.ndarray | tuple = SAGITTAL_NORMAL, d: float = 0.0) -> np.ndarray:
    """Reflect points about the plane ``{x : n . x = d}``: ``x' = (I - 2 n n^T) x + 2 d n``.

    ``X`` is ``(3,)`` or ``(..., 3)`` (mm).  ``n`` is normalised (together with
    ``d``) if it is not unit length.  For the default sagittal plane
    (``n = (1, 0, 0)``, ``d = 0``) the result is exactly ``X * (-1, 1, 1)``.
    """
    n, d = _unit_plane(n, d)
    X = np.asarray(X, float)
    h = X @ n - d
    return X - 2.0 * h[..., None] * n


def permute_pairs(n_points: int, pairs: np.ndarray) -> np.ndarray:
    """Index permutation that swaps each bilateral pair ``(l, r)`` and fixes all other points.

    Raises ValueError if an index is out of range, a pair is ``(i, i)`` or an
    index appears in more than one pair.
    """
    pairs = np.asarray(pairs, dtype=np.int64).reshape(-1, 2)
    perm = np.arange(n_points, dtype=np.int64)
    if len(pairs) == 0:
        return perm
    flat = pairs.ravel()
    if flat.min() < 0 or flat.max() >= n_points:
        raise ValueError(f"pair indices must be in [0, {n_points}), got {pairs.tolist()}")
    if np.any(pairs[:, 0] == pairs[:, 1]):
        raise ValueError("a symmetry pair must join two different points")
    if len(np.unique(flat)) != len(flat):
        raise ValueError("each point may belong to at most one symmetry pair")
    perm[pairs[:, 0]] = pairs[:, 1]
    perm[pairs[:, 1]] = pairs[:, 0]
    return perm


def _normal_from_improper(R: np.ndarray) -> np.ndarray:
    """Unit eigenvector of an improper orthogonal ``R`` for eigenvalue -1, sign ``n_x > 0``.

    Uses the symmetric part of ``(I - R)/2``: for a pure reflection it equals
    ``n n^T`` exactly; for a rotoreflection (rotation by theta about ``n`` times
    the reflection) its eigenvalues are ``1`` (eigenvector ``n``) and
    ``(1 - cos theta)/2`` (twice), so the top eigenvector is still ``n``.
    """
    Msym = 0.5 * (np.eye(3) - 0.5 * (R + R.T))
    _, vecs = np.linalg.eigh(Msym)
    n = vecs[:, -1]
    n = n / np.linalg.norm(n)
    nz = np.flatnonzero(np.abs(n) > 1e-15)
    if len(nz) and n[nz[0]] < 0:     # n_x > 0 (or the first non-zero component if n_x == 0)
        n = -n
    return n


def fit_symmetry_plane(X: np.ndarray, pairs: np.ndarray, midline: np.ndarray,
                       weights: np.ndarray | None = None, *,
                       huber_mm: float | None = None,
                       max_iter: int = 10) -> tuple[np.ndarray, float, float]:
    """Plane of best bilateral symmetry by weighted reflection Procrustes (DESIGN 4.11; anat R3.3).

    Parameters
    ----------
    X : (N, 3) points, mm (head frame).
    pairs : (P, 2) indices ``(l, r)`` of bilateral pairs (subject-left first by
        convention; the fit itself does not depend on the order within a pair).
    midline : (M,) indices of midline points (fixed by the label swap).
    weights : (N,) non-negative per-point weights or None (all 1).  DESIGN 4.11 /
        anat R3.3 weights come from :func:`face3d.fit.symmetry.plane_weights`
        (upper face 1.0, midface 0.5, lower 0.25, ears 0.1).
    huber_mm : optional Huber threshold (mm) on the per-point residual norm,
        applied by IRLS (``max_iter`` rounds).  None (default, the WP-12 spec)
        is plain weighted least squares; the research note *facial-asymmetry*
        ("Plane-fit weights ... Use a Huber loss at about 1 mm" 🧠) suggests 1.0.

    Method: build ``X_pi`` by swapping the rows of every pair (midline rows fixed),
    then align ``X_pi`` onto ``X`` with the best weighted rigid *improper*
    transform (``with_scale=False``, ``det R = -1``), using only the pair and
    midline rows.  The normal ``n`` is the eigenvector of ``R`` with eigenvalue
    -1 (from ``(I - R)/2``), sign chosen so that ``n_x > 0``; ``d = (n . t)/2``,
    which is also the least-squares offset for that ``n`` (``n . R y = -n . y``).

    Returns ``(n, d, rmse)``: unit normal (3,), offset (mm) and the weighted RMS
    (mm) of ``X_i - reflect(X_pi_i; n, d)`` over the pair and midline points
    (``nan`` when there are none).  With fewer than :data:`MIN_PAIRS_PLANE_FIT`
    pairs (or zero total weight) the head-frame plane ``n = (1, 0, 0)``,
    ``d = 0`` is returned.
    """
    X = np.asarray(X, float)
    if X.ndim != 2 or X.shape[1] != 3:
        raise ValueError(f"X must be (N, 3), got {X.shape}")
    N = len(X)
    pairs = np.asarray(pairs, dtype=np.int64).reshape(-1, 2)
    midline = np.asarray(midline, dtype=np.int64).reshape(-1)
    perm = permute_pairs(N, pairs)
    if len(midline) and (midline.min() < 0 or midline.max() >= N):
        raise ValueError(f"midline indices must be in [0, {N})")
    if np.intersect1d(midline, pairs.ravel()).size:
        raise ValueError("a point cannot be both a pair member and a midline point")
    used = np.unique(np.concatenate([pairs.ravel(), midline]))
    w_all = np.ones(N) if weights is None else np.asarray(weights, float).reshape(-1)
    if len(w_all) != N:
        raise ValueError(f"weights must have length N={N}, got {len(w_all)}")
    if np.any(~np.isfinite(w_all)) or np.any(w_all < 0):
        raise ValueError("weights must be finite and non-negative")
    w = w_all[used]
    dst = X[used]
    src = X[perm[used]]                       # X_pi restricted to the used rows

    n = np.array(SAGITTAL_NORMAL, float)
    d = 0.0
    if len(pairs) >= MIN_PAIRS_PLANE_FIT and len(used) and w.sum() > 0:
        w_irls = w.copy()
        for _ in range(max(1, int(max_iter)) if huber_mm is not None else 1):
            _, R, t = _align(src, dst, False, w_irls, "improper")
            n = _normal_from_improper(R)
            d = 0.5 * float(n @ t)
            if huber_mm is None:
                break
            r = np.linalg.norm(dst - reflect(src, n, d), axis=1)
            hub = np.where(r <= huber_mm, 1.0, huber_mm / np.maximum(r, 1e-300))
            w_new = w * hub
            if w_new.sum() <= 0 or np.allclose(w_new, w_irls, rtol=1e-10, atol=0.0):
                break
            w_irls = w_new
    if len(used) == 0 or w.sum() <= 0:
        return n, d, float("nan")
    return n, d, _weighted_rmse(dst - reflect(src, n, d), w)
