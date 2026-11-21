"""Per-vertex uncertainty of the staged template warp (DESIGN 4.15 "Uncertainty", H1/H3; WBS WP-19).

Stage B of the warp is linear in the landmark targets,
``V_B = V_A + A (X - X_A)`` with ``A`` ``(V, N)`` the explicit map returned by
:func:`face3d.fit.template.stage_b` (the same row acts on x, y and z).  Hence

    Cov(V_j) = (A_j kron I_3) Sigma_X (A_j kron I_3)^T            (3 x 3)

which is evaluated as ``C_j C_j^T`` with ``C_j = (A_j kron I_3) L_X`` and
``Sigma_X = L_X L_X^T`` - one Cholesky factor and chunked matrix products, no unit
solves (DESIGN 4.15; the J1/J2 flaw of the proposals).

What the landmarks cannot say about the surface between them is the regional residual
``sigma_res`` (:data:`SIGMA_RES_MM`), added in quadrature along the normal until a
stage-D joint posterior covers the vertex.  The reported per-vertex value is

    sigma_n,j = sqrt( n_j^T Cov(V_j) n_j * inflation + sigma_res,r(j)^2 + sigma_def,r(j)^2 )

with ``inflation = max(1, gamma^2, chi2_red)`` of DESIGN 4.13.

Conventions
-----------
* Units: millimetres (covariances mm^2), head frame (DESIGN 3.1).
* ``cov_X`` is ``(3N, 3N)`` point-major (x0, y0, z0, x1, ...), as ``BundleResult.cov``;
  it must be expressed in the frame of the targets that drove stage B.
* ``regions`` is one region name per vertex (``TemplateKit.vertex_regions()``).
* ``normals`` are unit vertex normals of the surface the sigma is reported on.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

import numpy as np

from ..core.config import Default, register_defaults

__all__ = ["SIGMA_RES_MM", "CHOL_JITTER", "landmark_sigma_mm", "vertex_cov_stage_b", "vertex_sigma_n", "sigma_res_of",
           "finite_difference_check", "landmark_region_sigma_def"]

_BRAIN = "\U0001F9E0"   # expert knowledge, provisional
_T4 = "research/blender/open-template-head-kit.md Table 4"

_RES = register_defaults("warp", {
    "sigma_res_eyes_mm": Default(1.25, _BRAIN, f"DESIGN 4.15 lids 1-1.5; {_T4} lids, canthi 1.0-1.5 (WP-19, "
                                 "provisional)", "mm", (0.0, None)),
    "sigma_res_nose_mm": Default(2.5, _BRAIN, f"DESIGN 4.15 nose 2-3; {_T4} (WP-19, provisional)", "mm",
                                 (0.0, None)),
    "sigma_res_lips_mm": Default(2.0, _BRAIN, f"{_T4} lips 1.5-2.5 (WP-19, provisional)", "mm", (0.0, None)),
    "sigma_res_cheeks_mm": Default(3.25, _BRAIN, f"DESIGN 4.15 cheeks 2.5-4; {_T4} (WP-19, provisional)", "mm",
                                   (0.0, None)),
    "sigma_res_forehead_mm": Default(2.5, _BRAIN, f"{_T4} brow, forehead 2-3 (WP-19, provisional)", "mm",
                                     (0.0, None)),
    "sigma_res_chin_mm": Default(3.0, _BRAIN, f"{_T4} jaw, chin 2-4 (WP-19, provisional)", "mm", (0.0, None)),
    "sigma_res_jaw_mm": Default(3.0, _BRAIN, f"{_T4} jaw, chin 2-4 (WP-19, provisional)", "mm", (0.0, None)),
    "sigma_res_ears_mm": Default(4.0, _BRAIN, f"DESIGN 4.15 ears 3-5; {_T4} (WP-19, provisional)", "mm",
                                 (0.0, None)),
    "sigma_res_scalp_mm": Default(4.5, _BRAIN, f"DESIGN 4.15 scalp 3-6; {_T4} (WP-19, provisional)", "mm",
                                  (0.0, None)),
    "sigma_res_neck_mm": Default(7.5, _BRAIN, f"DESIGN 4.15 neck 5-10; {_T4} (WP-19, provisional)", "mm",
                                 (0.0, None)),
    "sigma_res_other_mm": Default(3.0, "\U0001F195", "WBS WP-19 spec (catch-all region; uncalibrated, "
                                  "provisional)", "mm", (0.0, None)),
})

#: Regional residual sigma (mm) of the landmark-driven warp: what remains unknown about
#: the surface between landmarks (DESIGN 4.15; open-template-head-kit Table 4; all
#: PROVISIONAL, badge brain).  Keys are the kit region names; unknown regions use 'other'.
SIGMA_RES_MM: dict[str, float] = {
    r: float(_RES[f"sigma_res_{r}_mm"].value)
    for r in ("eyes", "nose", "lips", "cheeks", "forehead", "chin", "jaw", "ears", "scalp", "neck", "other")
}

#: Diagonal jitter (mm^2) added to cov_X before the Cholesky factorisation (WBS WP-19 spec).
CHOL_JITTER = 1e-12


def _factor(cov_X: np.ndarray) -> np.ndarray:
    """Lower factor L with L L^T = cov_X + jitter I (Cholesky; eigen-factor if not PD)."""
    S = np.asarray(cov_X, float)
    if S.ndim != 2 or S.shape[0] != S.shape[1] or S.shape[0] % 3:
        raise ValueError(f"cov_X must be (3N, 3N), got {S.shape}")
    if not np.all(np.isfinite(S)):
        raise ValueError("cov_X must be finite")
    S = 0.5 * (S + S.T) + CHOL_JITTER * np.eye(len(S))
    try:
        return np.linalg.cholesky(S)
    except np.linalg.LinAlgError:
        # a posterior that is PSD only up to round-off: clip the negative eigenvalues
        w, U = np.linalg.eigh(S)
        return U * np.sqrt(np.clip(w, 0.0, None))


def landmark_sigma_mm(cov_X: np.ndarray) -> np.ndarray:
    """Per-landmark position sigma (N,) mm, ``sqrt(trace Cov_i)`` of the 3 x 3 diagonal blocks.

    This is the ``sigma_X_mm`` convention of :func:`face3d.fit.template.stage_b` under
    which ``warp.alpha`` was calibrated (WP-19).
    """
    d = np.diag(np.asarray(cov_X, float))
    if d.size % 3:
        raise ValueError("cov_X must be (3N, 3N)")
    return np.sqrt(np.clip(d, 0.0, None).reshape(-1, 3).sum(axis=1))


def vertex_cov_stage_b(A_rows: np.ndarray, cov_X: np.ndarray, chunk: int = 2000) -> np.ndarray:
    """Covariance (V, 3, 3) mm^2 of the stage-B vertices under target covariance ``cov_X``.

    A_rows : (V, N) stage-B linear map (:func:`face3d.fit.template.stage_b`).
    cov_X : (3N, 3N) mm^2, point-major.
    With ``L_X = chol(cov_X + 1e-12 I)``: ``C_j = (A_j kron I_3) L_X`` (3, 3N) and
    ``cov_j = C_j C_j^T``, in chunks of ``chunk`` vertices (no unit solves).
    """
    A = np.asarray(A_rows, float)
    if A.ndim != 2:
        raise ValueError("A_rows must be (V, N)")
    V, N = A.shape
    L = _factor(cov_X)
    if L.shape[0] != 3 * N:
        raise ValueError(f"cov_X is {L.shape[0]} x {L.shape[0]}; A_rows has {N} landmarks (need {3 * N})")
    L3 = L.reshape(N, 3, L.shape[1])                       # (N, 3, m): rows of point i
    out = np.empty((V, 3, 3))
    for i in range(0, V, max(1, int(chunk))):
        C = np.einsum("vn,nam->vam", A[i:i + chunk], L3, optimize=True)
        out[i:i + chunk] = np.einsum("vam,vbm->vab", C, C, optimize=True)
    return out


def sigma_res_of(regions: Sequence[str], sigma_res: Mapping[str, float] | None = None) -> np.ndarray:
    """Residual sigma (V,) mm of each vertex from its region name (unknown names -> 'other')."""
    table = SIGMA_RES_MM if sigma_res is None else sigma_res
    other = float(table.get("other", SIGMA_RES_MM["other"]))
    return np.array([float(table.get(str(r), other)) for r in regions], float)


def _per_vertex(value: Any, regions: Sequence[str], n: int, name: str) -> np.ndarray:
    if value is None:
        return np.zeros(n)
    if isinstance(value, Mapping):
        other = float(value.get("other", 0.0))
        return np.array([float(value.get(str(r), other)) for r in regions], float)
    a = np.asarray(value, float)
    if a.ndim == 0:
        return np.full(n, float(a))
    if a.shape != (n,):
        raise ValueError(f"{name} must be a scalar, a region dict or ({n},)")
    return a


def vertex_sigma_n(cov: np.ndarray, normals: np.ndarray, regions: Sequence[str], inflation: float = 1.0,
                   sigma_def_region: Any = None, cov_override: np.ndarray | None = None,
                   override_mask: np.ndarray | None = None, *,
                   sigma_res: Mapping[str, float] | None = None) -> np.ndarray:
    """Reported normal sigma (V,) mm of every vertex (DESIGN 4.15, 4.13).

    ``sigma_n = sqrt(n^T cov n * inflation + sigma_res^2 + sigma_def^2)``.

    cov : (V, 3, 3) mm^2 (:func:`vertex_cov_stage_b`).  normals : (V, 3) unit normals.
    regions : (V,) region names.  inflation : scalar ``max(1, gamma^2, chi2_red)``
    (values below 1 are raised to 1).  sigma_def_region : definition-bias sigma in mm as
    a ``{region: mm}`` dict (missing regions use its 'other', else 0), a scalar, a (V,)
    array, or None (0).  cov_override / override_mask : vertices with
    ``override_mask`` True are covered by a stage-D joint posterior (DESIGN 4.15: k > 0.5):
    their covariance is ``cov_override[j]`` and ``sigma_res`` is dropped for them.
    sigma_res : optional replacement of :data:`SIGMA_RES_MM`.
    """
    cov = np.asarray(cov, float)
    n = np.asarray(normals, float)
    V = len(n)
    if cov.shape != (V, 3, 3) or n.shape != (V, 3) or len(regions) != V:
        raise ValueError("cov must be (V, 3, 3), normals (V, 3) and regions (V,)")
    infl = float(inflation)
    if not np.isfinite(infl):
        raise ValueError("inflation must be finite")
    infl = max(1.0, infl)
    res = sigma_res_of(regions, sigma_res)
    sdef = _per_vertex(sigma_def_region, regions, V, "sigma_def_region")
    if (cov_override is None) != (override_mask is None):
        raise ValueError("cov_override and override_mask must be given together")
    if override_mask is not None:
        m = np.asarray(override_mask, bool).reshape(-1)
        co = np.asarray(cov_override, float)
        if m.shape != (V,) or co.shape != (V, 3, 3):
            raise ValueError("cov_override must be (V, 3, 3) and override_mask (V,)")
        cov = np.where(m[:, None, None], co, cov)
        res = np.where(m, 0.0, res)
    var_n = np.einsum("vi,vij,vj->v", n, cov, n)
    return np.sqrt(np.clip(var_n, 0.0, None) * infl + res ** 2 + sdef ** 2)


def landmark_region_sigma_def(landmark_regions: Sequence[str], sigma_def_mm: Sequence[float]) -> dict[str, float]:
    """``{region: RMS of the landmarks' definition sigma}`` plus ``'other'`` = the overall RMS.

    landmark_regions : region name of each landmark's carrier vertex (kit regions).
    sigma_def_mm : (N,) definition-bias sigma of each landmark (DESIGN D-06;
    ``face3d.model.registry.ANATOMICAL[id].sigma_def_mm``).  A region without landmarks
    falls back to 'other' in :func:`vertex_sigma_n`.
    """
    s = np.asarray(sigma_def_mm, float).reshape(-1)
    if len(landmark_regions) != len(s):
        raise ValueError("one region per landmark is required")
    out: dict[str, float] = {}
    for r in dict.fromkeys(str(x) for x in landmark_regions):
        sel = np.array([str(x) == r for x in landmark_regions])
        out[r] = float(np.sqrt(np.mean(s[sel] ** 2)))
    out["other"] = float(np.sqrt(np.mean(s ** 2))) if len(s) else 0.0
    return out


def finite_difference_check(warp_fn: Callable[[np.ndarray], np.ndarray], X: np.ndarray, A_rows: np.ndarray,
                            eps: float = 1e-3) -> float:
    """Verify the explicit stage-B map by central differences; returns the max relative error.

    warp_fn : ``X (N, 3) -> V (V, 3)`` (e.g. ``lambda X: stage_b(V_A, kit, X, sigma, ids)[0]``).
    A_rows : (V, N) claimed map, ``dV[j, a] / dX[i, b] = A_rows[j, i] delta_ab``.
    eps : step in mm.  The error is ``max |J_fd - J| / max |J|`` over all 3N target
    coordinates (3N pairs of warp evaluations).  Columns of non-finite targets are skipped.
    """
    X = np.asarray(X, float)
    A = np.asarray(A_rows, float)
    N = len(X)
    if A.shape[1] != N:
        raise ValueError("A_rows must have one column per target")
    scale = float(np.abs(A).max()) or 1.0
    worst = 0.0
    for i in range(N):
        if not np.all(np.isfinite(X[i])):
            continue
        for b in range(3):
            Xp, Xm = X.copy(), X.copy()
            Xp[i, b] += eps
            Xm[i, b] -= eps
            J = (np.asarray(warp_fn(Xp), float) - np.asarray(warp_fn(Xm), float)) / (2.0 * eps)   # (V, 3)
            ref = np.zeros_like(J)
            ref[:, b] = A[:, i]
            worst = max(worst, float(np.abs(J - ref).max()))
    return worst / scale
