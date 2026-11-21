"""Template head fitting: similarity-align, RBF-warp to landmarks, Laplacian refine.

Two entry points:

* :func:`fit_template_to_landmarks` - the legacy one-shot fit of a :class:`Template`
  (Umeyama, exact RBF, hard Laplacian refine); unchanged.
* The staged warp of DESIGN 4.15 on a :class:`~face3d.model.template_kit.TemplateKit`
  (WBS WP-19): :func:`stage_a` (similarity + source checks), :func:`stage_b` (RBF with
  per-landmark smoothing; linear in the targets), :func:`stage_c` (bilaplacian with the
  kit's per-vertex stiffness and the offset cap), :func:`stage_d` (contours, delegated to
  :func:`face3d.fit.contour.contour_stage`), the gate :func:`fold_gate`, and the driver
  :func:`staged_warp` that runs A-C with the advance rules and roll-backs.

Conventions
-----------
* Units: millimetres in the head frame (DESIGN 3.1); ``V`` arrays are ``(V, 3)`` in kit
  vertex order; landmark targets ``X`` are ``(N, 3)`` with rows named by ``ids`` (the
  kit's ``scheme`` names, default ``'anatomical44'``).  A NaN row of ``X`` is a missing
  target and is ignored by every stage.
* ``sigma_X_mm`` ``(N,)`` is the 1-sigma position uncertainty of each target as a 3-D
  length, ``sqrt(trace Cov_i)`` of its posterior block
  (:func:`face3d.fit.uncertainty.landmark_sigma_mm`); ``warp.alpha`` is calibrated for
  this convention.
* ``views_agree`` ``(N,)`` int is the number of views whose observation of landmark i is
  an inlier of the bundle (DESIGN 4.15 C / MM-10: offsets above the cap need >= 2 views).
* Flags are strings: ``W-MIRRORED-SOURCE``, ``W-WRONG-AXES`` (stage A),
  ``W-FOLD`` (a stage was rolled back by :func:`fold_gate`), ``W-B-RMS`` (stage B did not
  reach the advance threshold, stage C not run), ``W-LANDMARK-FREEZE`` (stage D rejected),
  ``W-CONTOUR-HALF-WEIGHT`` (stage D accepted only at half the contour weight).
* Targets are never symmetrised, and a mirrored source is never flipped (DESIGN 4.15).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

import numpy as np

from ..core.config import Default, register_defaults
from ..geometry.procrustes import apply_similarity, umeyama, umeyama_proper_and_reflected
from ..geometry.rbf import WARP, RBFWarp, per_landmark_lambda, rms_radius
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


# =========================================================================== staged warp (WP-19)
_BRAIN = "\U0001F9E0"   # expert knowledge, provisional
_NEW = "\U0001F195"     # introduced by this design / WP spec, uncalibrated

FLAG_MIRRORED = "W-MIRRORED-SOURCE"
FLAG_WRONG_AXES = "W-WRONG-AXES"
FLAG_FOLD = "W-FOLD"
FLAG_B_RMS = "W-B-RMS"
FLAG_LANDMARK_FREEZE = "W-LANDMARK-FREEZE"
FLAG_CONTOUR_HALF = "W-CONTOUR-HALF-WEIGHT"

#: The 7 NoW-style landmarks of the stage-A rigid check (rec EV-1; same set as
#: ``face3d.eval.align.NOW7_NAMES``, repeated here because fit/ (L4) must not import eval/).
NOW7_IDS: tuple[str, ...] = ("ex_L", "en_L", "en_R", "ex_R", "prn", "ch_L", "ch_R")

_WARP_STAGES = register_defaults("warp", {
    "offset_cap_mm": Default(4.0, _BRAIN, "DESIGN 4.15 stage C: offsets capped at 4 mm unless >= 2 views agree "
                             "(MM-10: 3-5 mm)", "mm", (0.0, None)),
    "agree_views": Default(2, _BRAIN, "DESIGN 4.15 stage C / MM-10: >= 2 views must agree to lift the offset cap",
                           "views", (1, None)),
    "fold_det_min": Default(0.2, _BRAIN, "DESIGN 4.15 gates / MM-11: det J_warp > 0.2", "", (0.0, 1.0)),
    "landmark_freeze_mm": Default(0.5, _BRAIN, "DESIGN 4.15 stage D: no landmark moves > 0.5 mm (com R5.2)", "mm",
                                  (0.0, None)),
    "advance_rms_mm": Default(2.2, _BRAIN, "DESIGN 4.15 stage B advance: landmark RMS < 2.2 mm "
                              "(2.5 % of 88 mm)", "mm", (0.0, None)),
    "min_gain": Default(0.01, _BRAIN, "DESIGN 4.15 stage C: iterate while the RMS gain is >= 1 % per iteration",
                        "", (0.0, 1.0)),
    "max_c_iters": Default(5, _NEW, "WBS WP-19 spec: at most 5 stage-C iterations", "", (1, None)),
    "mirrored_ratio": Default(0.5, _BRAIN, "DESIGN 4.15 stage A / bl W2: reflected RMS < 0.5 x proper -> "
                              "mirrored source", "", (0.0, 1.0)),
    "wrong_axes_rms_mm": Default(10.0, _BRAIN, "DESIGN 4.15 stage A / bl W2: rigid 7-landmark RMS > 10 mm -> "
                                 "wrong landmarks or axes (2-5 mm is normal)", "mm", (0.0, None)),
    "c_weight": Default(1e3, _NEW, "WP-19 implementation choice: stage-C landmark weight relative to the "
                        "normalised bilaplacian energy (the legacy refine_weight of fit_template_to_landmarks)",
                        "", (0.0, None)),
    "c_sigma_ref_mm": Default(3.0, _NEW, "WP-19 implementation choice: sigma at which a stage-C landmark weight "
                              "is 1 in normalised bilaplacian units, w_i = (sigma_ref / sigma_i)^2 for uncertain "
                              "targets. Test bed (kit n=16, 6+6 subjects, alpha 30): stage-C face RMS out-of-prior / "
                              "in-space 2.46 / 1.67 mm (1 mm), 2.37 / 1.70 (3 mm), 2.34 / 1.98 (hard targets); "
                              "3 mm has the lowest pooled error", "mm", (1e-9, None)),
})


def _d(key: str) -> Any:
    return (WARP[key] if key == "alpha" else _WARP_STAGES[key]).value


@dataclass
class StagedWarpConfig:
    """Parameters of the staged warp (defaults: the ``warp`` namespace of the registry).

    alpha : stage-B gain of ``lambda_i = alpha (sigma_i / R_bar)^2`` (dimensionless).
    offset_cap_mm : stage-C cap on ``|V_C - V_B|`` for vertices whose nearest landmark
        has ``views_agree < agree_views``.
    fold_det_min : :func:`fold_gate` threshold on the signed area ratio.
    landmark_freeze_mm : largest landmark move stage D may make.
    advance_rms_mm : stage B must bring the landmark RMS below this for stage C to run.
    min_gain : stage C iterates while the relative landmark-RMS gain is at least this;
        max_c_iters bounds the iterations.
    """

    alpha: float = field(default_factory=lambda: float(_d("alpha")))
    offset_cap_mm: float = field(default_factory=lambda: float(_d("offset_cap_mm")))
    agree_views: int = field(default_factory=lambda: int(_d("agree_views")))
    fold_det_min: float = field(default_factory=lambda: float(_d("fold_det_min")))
    landmark_freeze_mm: float = field(default_factory=lambda: float(_d("landmark_freeze_mm")))
    advance_rms_mm: float = field(default_factory=lambda: float(_d("advance_rms_mm")))
    min_gain: float = field(default_factory=lambda: float(_d("min_gain")))
    max_c_iters: int = field(default_factory=lambda: int(_d("max_c_iters")))


def _targets(kit: Any, X: np.ndarray, ids: Sequence[str] | None, scheme: str) -> tuple[list[str], np.ndarray, np.ndarray]:
    """(ids, X (N, 3), ok (N,) bool: finite target rows)."""
    X = np.asarray(X, float)
    names = kit.landmark_names(scheme) if ids is None else [str(i) for i in ids]
    if X.ndim != 2 or X.shape != (len(names), 3):
        raise ValueError(f"X must be ({len(names)}, 3) for the given ids, got {X.shape}")
    return names, X, np.all(np.isfinite(X), axis=1)


def _rms(d: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.sum(d * d, axis=1)))) if len(d) else 0.0


def landmark_rms(kit: Any, V: np.ndarray, X: np.ndarray, ids: Sequence[str] | None = None, *,
                 scheme: str = "anatomical44", mask: np.ndarray | None = None) -> float:
    """RMS distance (mm) of the kit's landmarks on ``V`` to the targets ``X`` (finite rows, and ``mask``)."""
    names, X, ok = _targets(kit, X, ids, scheme)
    if mask is not None:
        ok = ok & np.asarray(mask, bool)
    return _rms(kit.landmark_positions(scheme, V, names)[ok] - X[ok])


# --------------------------------------------------------------------------- stage A
def stage_a(kit: Any, X_targets: np.ndarray, ids: Sequence[str] | None = None, *,
            scheme: str = "anatomical44") -> tuple[np.ndarray, tuple[float, np.ndarray, np.ndarray], list[str]]:
    """Stage A (DESIGN 4.15): proper similarity of the kit onto the landmark targets.

    Returns ``(V_A, (s, R, t), flags)`` with ``V_A = s V R^T + t`` and ``det R = +1``
    always.  Flags:

    * ``W-MIRRORED-SOURCE`` when the best reflected similarity has an RMSE below 0.5 x the
      proper one (bl W2).  The source is never flipped: the caller must fix its input.
    * ``W-WRONG-AXES`` when the *rigid* (no scale) RMS over the 7 landmarks
      :data:`NOW7_IDS` present in ``ids`` exceeds 10 mm (bl W2: 2-5 mm is normal; above
      10 mm the landmarks, axes or units are wrong).  Skipped with fewer than 4 of them.
    """
    names, X, ok = _targets(kit, X_targets, ids, scheme)
    if ok.sum() < 4:
        raise ValueError("stage A needs at least 4 finite landmark targets")
    src = kit.landmark_positions(scheme, names=names)
    both = umeyama_proper_and_reflected(src[ok], X[ok])
    s, R, t, rm_p = both["proper"]
    flags: list[str] = []
    if both["reflected"][3] < float(_d("mirrored_ratio")) * rm_p:
        flags.append(FLAG_MIRRORED)
    i7 = np.array([names.index(n) for n in NOW7_IDS if n in names and ok[names.index(n)]], np.int64)
    if len(i7) >= 4:
        s7, R7, t7 = umeyama(src[i7], X[i7], with_scale=False)
        if _rms(apply_similarity(src[i7], s7, R7, t7) - X[i7]) > float(_d("wrong_axes_rms_mm")):
            flags.append(FLAG_WRONG_AXES)
    return apply_similarity(np.asarray(kit.vertices, float), s, R, t), (float(s), R, t), flags


# --------------------------------------------------------------------------- stage B
def stage_b(V_A: np.ndarray, kit: Any, X: np.ndarray, sigma_X_mm: np.ndarray | float | None = None,
            ids: Sequence[str] | None = None, *, alpha: float | None = None,
            scheme: str = "anatomical44") -> tuple[np.ndarray, np.ndarray]:
    """Stage B (DESIGN 4.15, MM-8): biharmonic RBF warp with per-landmark smoothing.

    Solves ``(K - Lambda) w + P a = X - X_A`` in normalised coordinates
    (``RBFWarp(normalise=True)``), ``Lambda = diag(alpha (sigma_i / R_bar)^2)`` with
    ``R_bar`` the RMS radius of the template landmarks ``X_A`` on ``V_A``
    (:func:`face3d.geometry.rbf.per_landmark_lambda`; ``alpha`` defaults to ``warp.alpha``).
    ``sigma_X_mm`` None or 0 gives exact interpolation.

    Returns ``(V_B, A_rows)`` with ``A_rows`` ``(V, N)`` the explicit linear map
    ``V_B = V_A + A_rows @ (X - X_A)`` (the same row acts on x, y and z; columns of
    missing targets are zero), used by :mod:`face3d.fit.uncertainty`.
    """
    names, X, ok = _targets(kit, X, ids, scheme)
    V_A = np.asarray(V_A, float)
    if ok.sum() < 4:
        raise ValueError("stage B needs at least 4 finite landmark targets")
    src = kit.landmark_positions(scheme, V_A, names)
    sig = np.zeros(len(names)) if sigma_X_mm is None else np.broadcast_to(
        np.asarray(sigma_X_mm, float), (len(names),)).copy()
    lam = per_landmark_lambda(sig[ok], rms_radius(src[ok]), alpha)
    warp = RBFWarp(src[ok], X[ok], smoothing=lam, normalise=True)
    A = np.zeros((len(V_A), len(names)))
    A[:, ok] = warp.linear_map(V_A)
    return V_A + A[:, ok] @ (X[ok] - src[ok]), A


# --------------------------------------------------------------------------- stage C
def _nearest_landmark(V: np.ndarray, P: np.ndarray, chunk: int = 4096) -> np.ndarray:
    out = np.empty(len(V), np.int64)
    for i in range(0, len(V), chunk):
        v = V[i:i + chunk]
        d2 = np.sum(v * v, 1)[:, None] + np.sum(P * P, 1)[None, :] - 2.0 * v @ P.T
        out[i:i + chunk] = np.argmin(d2, axis=1)
    return out


def stage_c(V_B: np.ndarray, kit: Any, X: np.ndarray, views_agree: np.ndarray | None = None, *,
            ids: Sequence[str] | None = None, sigma_X_mm: np.ndarray | float | None = None,
            config: StagedWarpConfig | None = None, weight: float | None = None,
            scheme: str = "anatomical44", info: dict | None = None) -> np.ndarray:
    """Stage C (DESIGN 4.15, MM-10): bilaplacian offsets with per-vertex stiffness.

    Finds the displacement ``d = V_C - V_B`` minimising the stiffness-weighted bilaplacian
    energy of ``d`` (``laplacian_deform(..., stiffness=kit.stiffness)`` on the ``V_B``
    mesh) plus soft landmark terms ``w_i |x_i(V_B + d) - X_i|^2``.  Each landmark is
    carried by its vertex of largest barycentric weight ``v_i`` with the vertex target
    ``V[v_i] + (X_i - x_i(V))``, re-linearised each iteration; the loop continues while
    the relative gain of the landmark RMS is at least ``config.min_gain`` (at most
    ``config.max_c_iters`` solves; one solve is exact for one-hot embeddings).

    ``w_i = weight / (1 + weight (sigma_i / sigma_ref)^2)`` with ``weight`` (default
    ``warp.c_weight`` = 1e3) the weight of an exact target and ``sigma_ref`` =
    ``warp.c_sigma_ref_mm``: an exact target (``sigma_X_mm`` None or 0) is met to
    ~1e-3 of its residual, an uncertain one is pulled only as far as its sigma warrants,
    so stage C does not re-inject the noise that stage B smoothed away.

    Offset cap: with ``views_agree`` given, the vertices whose nearest landmark (on
    ``V_B``) has ``views_agree < config.agree_views`` keep ``|V_C - V_B| <=
    config.offset_cap_mm``.  When a first solution exceeds the cap there, the excess is
    scaled back, the system is re-solved once with soft targets at the capped positions
    (and the capped landmark targets), and any remaining excess is clamped, so the bound
    holds exactly.  ``views_agree`` None means every landmark is agreed (no cap).

    ``info`` (optional dict) receives ``rms_history`` (landmark RMS before and after each
    solve, over all finite targets), ``n_capped`` and ``iterations``.  Returns ``V_C``.
    """
    cfg = config or StagedWarpConfig()
    names, X, ok = _targets(kit, X, ids, scheme)
    V_B = np.asarray(V_B, float)
    N = len(names)
    w0 = float(_d("c_weight") if weight is None else weight)
    sig = np.zeros(N) if sigma_X_mm is None else np.broadcast_to(np.asarray(sigma_X_mm, float), (N,))
    w_lm = w0 / (1.0 + w0 * (sig / float(_d("c_sigma_ref_mm"))) ** 2)
    lv = np.asarray(kit.landmark_vertices(scheme, names), np.int64)
    mesh = kit.mesh(V_B)
    stiff = None if kit.stiffness is None else np.asarray(kit.stiffness, float)
    use = np.flatnonzero(ok)

    def lm(V: np.ndarray) -> np.ndarray:
        return kit.landmark_positions(scheme, V, names)

    def solve(V_cur: np.ndarray, tg: np.ndarray, extra_idx=None, extra_tg=None, extra_w=None) -> np.ndarray:
        idx, w = lv[use], w_lm[use]
        if extra_idx is not None and len(extra_idx):
            idx = np.concatenate([idx, extra_idx])
            tg = np.vstack([tg, extra_tg])
            w = np.concatenate([w, extra_w])
        return laplacian_deform(mesh, idx, tg, weight=w, x_init=V_cur, stiffness=stiff, solver="auto")[0]

    def iterate(V0: np.ndarray, X_t: np.ndarray, hist: list, **extra) -> tuple[np.ndarray, int]:
        V_cur, r_prev, n_it, tg_prev = V0, _rms((lm(V0) - X_t)[use]), 0, None
        for _ in range(int(cfg.max_c_iters)):
            tg = V_cur[lv[use]] + (X_t[use] - lm(V_cur)[use])   # carrier-vertex targets, re-linearised
            if tg_prev is not None and np.allclose(tg, tg_prev, rtol=0.0, atol=1e-9):
                break                                    # same linear problem (one-hot embeddings): converged
            tg_prev = tg
            V_new = solve(V_cur, tg, **extra)
            r_new = _rms((lm(V_new) - X_t)[use])
            n_it += 1
            if not r_new < r_prev:                       # no gain: keep the previous iterate
                break
            gain = (r_prev - r_new) / r_prev
            V_cur, r_prev = V_new, r_new
            hist.append(r_new)
            if gain < cfg.min_gain:
                break
        return V_cur, n_it

    hist = [_rms((lm(V_B) - X)[use])]
    if hist[0] <= 1e-9:                                  # stage B already interpolates the targets
        if info is not None:
            info.update(rms_history=hist, n_capped=0, iterations=0)
        return V_B.copy()
    V_C, n_it = iterate(V_B, X, hist)
    n_capped = 0
    if views_agree is not None:
        va = np.asarray(views_agree).reshape(-1)
        if va.shape != (N,):
            raise ValueError(f"views_agree must have shape ({N},)")
        near = use[_nearest_landmark(V_B, lm(V_B)[use])]
        capped = va[near] < int(cfg.agree_views)                      # (V,) bool
        cap = float(cfg.offset_cap_mm)

        def excess(V: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
            off = V - V_B
            n = np.linalg.norm(off, axis=1)
            over = capped & (n > cap)
            Vc = V.copy()
            Vc[over] = V_B[over] + off[over] * (cap / n[over])[:, None]
            return over, Vc

        over, V_cap = excess(V_C)
        n_capped = int(over.sum())
        if n_capped:
            # capped landmark targets: a landmark carried by a capped vertex may move at most cap
            X_c = X.copy()
            dl = X - lm(V_B)
            nl = np.linalg.norm(np.where(ok[:, None], dl, 0.0), axis=1)
            lim = ok & capped[lv] & (nl > cap)
            X_c[lim] = lm(V_B)[lim] + dl[lim] * (cap / nl[lim])[:, None]
            e_idx = np.flatnonzero(over)
            hist2: list = []
            V_C, n2 = iterate(V_B, X_c, hist2, extra_idx=e_idx, extra_tg=V_cap[e_idx],
                              extra_w=np.full(len(e_idx), w0))
            n_it += n2
            _, V_C = excess(V_C)                                       # exact bound
            hist.append(_rms((lm(V_C) - X)[use]))
    if info is not None:
        info.update(rms_history=hist, n_capped=n_capped, iterations=n_it)
    return V_C


# --------------------------------------------------------------------------- stage D
def stage_d(basis: Any, views: Sequence[Any], obs: Sequence[Any] | None, iod_px: Any = None, *,
            config: StagedWarpConfig | None = None, contour_weight: float = 1.0,
            stage_fn: Callable[..., Any] | None = None, **kwargs: Any) -> tuple[np.ndarray, Any, list[str]]:
    """Stage D (DESIGN 4.15 D, 4.16): contours with free cameras, delegated to WP-17.

    basis, views, obs, iod_px and ``kwargs`` are those of
    :func:`face3d.fit.contour.contour_stage` (``basis`` is a
    :class:`~face3d.solve.shape_models.LinearBasis` on the stage-C surface).  With no
    ``ContourObs`` the stage is skipped and ``(basis.V_bar, None, [])`` is returned.

    Landmark freeze (com R5.2): a result whose largest landmark move
    (``result.landmark_shift_mm``) exceeds ``config.landmark_freeze_mm`` (0.5 mm) is
    rejected and the stage is retried once with half the contour weight (the forward kind
    weights and the backward weight of the :class:`~face3d.fit.contour.ContourTerm`); if
    the retry passes it is returned with ``W-CONTOUR-HALF-WEIGHT``, otherwise the stage is
    rolled back to ``basis.V_bar`` with ``W-LANDMARK-FREEZE``.

    Returns ``(V_D, result, flags)``; ``result`` is the accepted
    :class:`~face3d.fit.contour.ContourStageResult`, or the last rejected one on roll-back.
    ``stage_fn`` replaces ``contour_stage`` (tests).  The fold gate is applied by the
    caller (:func:`fold_gate` on ``basis.V_bar`` -> ``V_D``).
    """
    cfg = config or StagedWarpConfig()
    V0 = np.asarray(basis.V_bar, float)
    if obs is None or len(obs) == 0:
        return V0.copy(), None, []
    from .contour import CONTOUR, contour_stage                 # lazy: pulls in the L3 solver
    fn = contour_stage if stage_fn is None else stage_fn
    tk0 = dict(kwargs.pop("term_kwargs", None) or {})
    kind0 = {"hard": 1.0, "outer_bound": float(CONTOUR["outer_bound_weight"].value), "inner_bound": 1.0}
    kind0.update({str(k): float(v) for k, v in (tk0.get("kind_weights") or {}).items()})
    back0 = float(CONTOUR["backward_weight"].value if tk0.get("backward_weight") is None
                  else tk0["backward_weight"])
    res = None
    for attempt, w in enumerate((float(contour_weight), 0.5 * float(contour_weight))):
        tk = dict(tk0)
        tk["kind_weights"] = {k: w * v for k, v in kind0.items()}
        tk["backward_weight"] = w * back0
        res = fn(basis, views, obs, iod_px, term_kwargs=tk, **kwargs)
        shift = np.asarray(res.landmark_shift_mm, float)
        if float(shift.max(initial=0.0)) <= float(cfg.landmark_freeze_mm):
            return np.asarray(res.V, float), res, ([FLAG_CONTOUR_HALF] if attempt else [])
    return V0.copy(), res, [FLAG_LANDMARK_FREEZE]


# --------------------------------------------------------------------------- gates
def fold_gate(V_before: np.ndarray, V_after: np.ndarray, tris: np.ndarray,
              fold_det_min: float | None = None) -> tuple[bool, float]:
    """Fold gate (DESIGN 4.15 gates, MM-11): ``(ok, min_det)``.

    Per triangle, the determinant of the deformation gradient restricted to the triangle
    plane is the signed area ratio ``det = sign(n_after . n_before) |n_after| / |n_before|``
    (``n`` the area vectors), where the after-mesh is first rotated back by the best rigid
    rotation between the two vertex sets so that a global rotation does not read as a
    flip.  ``ok`` iff every triangle has ``det > fold_det_min`` (default 0.2); a flipped
    normal has ``det < 0`` and fails.  Triangles degenerate in ``V_before`` are ignored.
    """
    thr = float(_d("fold_det_min") if fold_det_min is None else fold_det_min)
    Vb = np.asarray(V_before, float)
    Va = np.asarray(V_after, float)
    T = np.asarray(tris, np.int64)
    if not np.all(np.isfinite(Va)):
        return False, float("-inf")
    _, R, _ = umeyama(Vb, Va, with_scale=False)                 # Va ~ R Vb + t
    nb = np.cross(Vb[T[:, 1]] - Vb[T[:, 0]], Vb[T[:, 2]] - Vb[T[:, 0]])
    na = np.cross(Va[T[:, 1]] - Va[T[:, 0]], Va[T[:, 2]] - Va[T[:, 0]]) @ R   # rows R^T n
    ab = np.linalg.norm(nb, axis=1)
    good = ab > 1e-12 * max(float(ab.max(initial=0.0)), 1e-300)
    if not good.any():
        return True, float("inf")
    det = np.sign(np.einsum("ij,ij->i", na[good], nb[good])) * np.linalg.norm(na[good], axis=1) / ab[good]
    m = float(det.min())
    return bool(m > thr), m


# --------------------------------------------------------------------------- driver
@dataclass
class StagedWarpResult:
    """Output of :func:`staged_warp`.

    vertices : (V, 3) the accepted surface (of ``stage``).  stage : last accepted stage
    ('A', 'B' or 'C').  V_A, V_B, V_C : stage surfaces (None when not run; a rolled-back
    stage keeps its rejected surface out: the attribute is None).  similarity : stage-A
    ``(s, R, t)``.  A_rows : (V, N) stage-B linear map (None when B was rolled back).
    flags : list of flag strings.  landmark_rms_mm : {'A', 'B', 'C': RMS over the finite
    targets}.  min_det : {'B', 'C': fold-gate minimum}.  info : stage-C diagnostics.
    """

    vertices: np.ndarray
    stage: str
    similarity: tuple[float, np.ndarray, np.ndarray]
    V_A: np.ndarray
    V_B: np.ndarray | None = None
    V_C: np.ndarray | None = None
    A_rows: np.ndarray | None = None
    flags: list = field(default_factory=list)
    landmark_rms_mm: dict = field(default_factory=dict)
    min_det: dict = field(default_factory=dict)
    info: dict = field(default_factory=dict)


def staged_warp(kit: Any, X: np.ndarray, ids: Sequence[str] | None = None, *,
                sigma_X_mm: np.ndarray | float | None = None, views_agree: np.ndarray | None = None,
                config: StagedWarpConfig | None = None, scheme: str = "anatomical44") -> StagedWarpResult:
    """Run stages A-C of DESIGN 4.15 with their gates (stage D needs views: :func:`stage_d`).

    A always runs.  B is rolled back to ``V_A`` with ``W-FOLD`` when :func:`fold_gate`
    fails.  C runs when the stage-B landmark RMS is below ``config.advance_rms_mm``
    (measured over the landmarks with ``views_agree >= config.agree_views`` when
    ``views_agree`` is given - an unobserved landmark's target is the prior, which stage B
    deliberately does not interpolate - else over all finite targets); otherwise the
    result stays at B with ``W-B-RMS``.  C is rolled back to ``V_B`` with ``W-FOLD`` when
    the gate fails.  Targets are never symmetrised.
    """
    cfg = config or StagedWarpConfig()
    names, X, ok = _targets(kit, X, ids, scheme)
    tris = np.asarray(kit.triangles(), np.int64)
    V_A, sim, flags = stage_a(kit, X, names, scheme=scheme)
    out = StagedWarpResult(vertices=V_A, stage="A", similarity=sim, V_A=V_A, flags=list(flags))
    out.landmark_rms_mm["A"] = landmark_rms(kit, V_A, X, names, scheme=scheme)
    V_B, A_rows = stage_b(V_A, kit, X, sigma_X_mm, names, alpha=cfg.alpha, scheme=scheme)
    good, out.min_det["B"] = fold_gate(V_A, V_B, tris, cfg.fold_det_min)
    if not good:
        out.flags.append(FLAG_FOLD)
        return out
    out.vertices, out.stage, out.V_B, out.A_rows = V_B, "B", V_B, A_rows
    out.landmark_rms_mm["B"] = landmark_rms(kit, V_B, X, names, scheme=scheme)
    seen = None if views_agree is None else np.asarray(views_agree).reshape(-1) >= int(cfg.agree_views)
    gate_rms = out.landmark_rms_mm["B"] if seen is None or not (seen & ok).any() else \
        landmark_rms(kit, V_B, X, names, scheme=scheme, mask=seen)
    out.info["advance_rms_mm"] = gate_rms
    if not gate_rms < cfg.advance_rms_mm:
        out.flags.append(FLAG_B_RMS)
        return out
    V_C = stage_c(V_B, kit, X, views_agree, ids=names, sigma_X_mm=sigma_X_mm, config=cfg, scheme=scheme,
                  info=out.info)
    good, out.min_det["C"] = fold_gate(V_B, V_C, tris, cfg.fold_det_min)
    if not good:
        out.flags.append(FLAG_FOLD)
        return out
    out.vertices, out.stage, out.V_C = V_C, "C", V_C
    out.landmark_rms_mm["C"] = landmark_rms(kit, V_C, X, names, scheme=scheme)
    return out
