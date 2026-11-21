"""Expression tags and expression covariance inflation (DESIGN D-14, 4.9; WBS WP-15).

Expression is handled as a nuisance on the *neutral* identity: each view gets a tag
(``neutral`` / ``mild`` / ``expressive``) and every landmark's observation covariance is
inflated by its expression class (DESIGN 4.9, [Rob 3.6] 🧠):

    Sigma_expr,iv = (mu_c(tag)^2 - 1) sigma_kind,i^2 I_3   (3D, mm^2),
    Sigma_iv += P_iv Sigma_expr,iv P_iv^T                  (P_iv = d u / d X_i, px/mm),

with class multipliers mu_c (neutral / mild / expressive): rigid 1 / 1 / 1.25, semi-mobile
1 / 1.75 / 2.5, mobile 1 / 3 / drop, jaw-dependent 1 / 1 / 1 (the jaw hinge angle is fitted
instead; :func:`jaw_config_for_tag`).  The inflation only down-weights (first-order
marginalisation, D-14); the DESIGN hard gate (one smiling view among five moves the
neutral-region identity < 0.3 mm) is tested in ``tests/test_nuisances.py``.

Tags (DESIGN 4.9, thresholds 🧠 from anat section 6):

* from blendshape scores Delta b measured from the subject's own per-key minimum (or the
  view marked neutral): neutral if jawOpen < 0.08, mouthSmile (max L/R) < 0.15, eyeBlink
  (max L/R) < 0.35 and browInnerUp < 0.2; expressive if smile > 0.25, any of cheekSquint /
  eyeWide / browOuterUp / browInnerUp > 0.3, or blink > 0.4; mild otherwise (the
  expressive test is applied first);
* without scores (:func:`tag_fallback`, 🆕): an inner-lip gap / ch-ch > 0.04 drops sto and li;
  a mouth width (ch-ch over the rigid ex-ex width) above 1.08 x the set median marks mild;
* re-tag after a solve (:func:`retag_from_residuals`, 🆕): mobile-class reduced chi^2 > 4 ->
  at least mild, > 9 -> expressive, at most 3 rounds (the caller's loop).

Lids are dropped on a blink (EAR < 0.2) or gaze pitch beyond 12 deg (:func:`lid_drop`);
with no neutral view, lip and lid measurements finer than 1 mm are suppressed
(:func:`no_neutral_view`, finding ``E-NO-NEUTRAL``, rec BA-9).

Units: mm for sigma_kind and Sigma_expr, px^2 for image covariances, px/mm for P.
Thresholds are registered under ``expression`` in :mod:`face3d.core.config`.
numpy + stdlib only.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import numpy as np

from ..core.config import Default, register_defaults
from ..geometry.camera import Camera
from .bundle import BUNDLE, JawConfig
from .camera_model import projection_jacobians as _projection_jacobians

__all__ = [
    "EXPRESSION", "TAGS", "CLASS_MULT", "EXPR_CLASSES", "tag_from_blendshapes", "mouth_width", "tag_fallback",
    "retag_from_residuals", "mobile_chi2_red", "MAX_RETAG_ROUNDS", "expression_sigma_mm", "inflate_view_cov",
    "apply_expression", "projection_jacobians", "lid_drop", "no_neutral_view", "jaw_config_for_tag",
    "FLAG_NO_NEUTRAL", "expression_classes",
]

_BRAIN = "\U0001F9E0"
_NEW = "\U0001F195"
_A6 = "DESIGN 4.9 tags (anat section 6)"

EXPRESSION = register_defaults("expression", {
    "neutral_jaw_open": Default(0.08, _BRAIN, _A6 + ": neutral if jawOpen < 0.08", "", (0.0, 1.0)),
    "neutral_smile": Default(0.15, _BRAIN, _A6 + ": neutral if mouthSmile < 0.15", "", (0.0, 1.0)),
    "neutral_blink": Default(0.35, _BRAIN, _A6 + ": neutral if eyeBlink < 0.35", "", (0.0, 1.0)),
    "neutral_brow_inner": Default(0.2, _BRAIN, _A6 + ": neutral if browInnerUp < 0.2", "", (0.0, 1.0)),
    "expressive_smile": Default(0.25, _BRAIN, _A6 + ": expressive if smile > 0.25", "", (0.0, 1.0)),
    "expressive_other": Default(0.3, _BRAIN, _A6 + ": expressive if squint / eyeWide / brow > 0.3", "", (0.0, 1.0)),
    "expressive_blink": Default(0.4, _BRAIN, _A6 + ": expressive if blink > 0.4", "", (0.0, 1.0)),
    "fallback_lip_gap": Default(0.04, _NEW, "DESIGN 4.9 no-score fallback: inner-lip gap / ch-ch > 0.04 drops "
                                "sto and li", "", (0.0, 1.0)),
    "fallback_mouth_width": Default(1.08, _NEW, "DESIGN 4.9 no-score fallback: mouth width > 1.08 x set median "
                                    "marks mild", "", (1.0, 3.0)),
    "retag_mild_chi2": Default(4.0, _NEW, "DESIGN 4.9 re-tag: mobile-class reduced chi^2 > 4 -> at least mild",
                               "", (0.0, None)),
    "retag_expressive_chi2": Default(9.0, _NEW, "DESIGN 4.9 re-tag: mobile-class reduced chi^2 > 9 -> expressive",
                                     "", (0.0, None)),
    "max_retag_rounds": Default(3, _NEW, "DESIGN 4.9 re-tag at most 3 rounds", "", (0, 100)),
    "lid_ear_min": Default(0.2, _BRAIN, "DESIGN 4.9 / 4.1 Q-BLINK: lids dropped on EAR < 0.2 (bl section 10)",
                           "", (0.0, 1.0)),
    "lid_pitch_max_deg": Default(12.0, _BRAIN, "DESIGN 4.9: lids dropped at gaze pitch > 12 deg", "deg",
                                 (0.0, 90.0)),
    "jaw_expressive_sigma_deg": Default(3.0, _BRAIN, "DESIGN D-14 / 4.9: jaw prior sigma 3 deg on expressive "
                                        "views", "deg", (1e-9, None)),
    "no_neutral_suppress_mm": Default(1.0, _BRAIN, "DESIGN 4.9 / rec BA-9: with no neutral view, lip and lid "
                                      "measurements finer than 1 mm are suppressed", "mm", (0.0, None)),
})
_E = {k: EXPRESSION[k].value for k in EXPRESSION}

#: Expression tags in increasing order of activation (DESIGN 4.9).
TAGS: tuple[str, ...] = ("neutral", "mild", "expressive")
#: Expression classes of the landmark registry (face3d.model.registry Landmark.expr_class).
EXPR_CLASSES: tuple[str, ...] = ("rigid", "semi_mobile", "mobile", "jaw")
#: Class multipliers mu_c for (neutral, mild, expressive) (DESIGN 4.9, [Rob 3.6] 🧠); inf = drop.
CLASS_MULT: dict[str, tuple[float, float, float]] = {
    "rigid": (1.0, 1.0, 1.25),
    "semi_mobile": (1.0, 1.75, 2.5),
    "mobile": (1.0, 3.0, math.inf),
    "jaw": (1.0, 1.0, 1.0),
}
#: Re-tag rounds allowed to the caller (DESIGN 4.9).
MAX_RETAG_ROUNDS: int = int(_E["max_retag_rounds"])
#: Finding code: no view is neutral (DESIGN 4.9, rec BA-9).
FLAG_NO_NEUTRAL = "E-NO-NEUTRAL"

_PAIRS = {"smile": ("mouthSmileLeft", "mouthSmileRight"), "blink": ("eyeBlinkLeft", "eyeBlinkRight"),
          "cheekSquint": ("cheekSquintLeft", "cheekSquintRight"), "eyeWide": ("eyeWideLeft", "eyeWideRight"),
          "browOuterUp": ("browOuterUpLeft", "browOuterUpRight")}
_SINGLE = ("jawOpen", "browInnerUp")


def _tag_index(tag: str) -> int:
    if tag not in TAGS:
        raise ValueError(f"unknown expression tag {tag!r} (expected one of {TAGS})")
    return TAGS.index(tag)


def _max_tag(a: str | None, b: str | None) -> str | None:
    if a is None:
        return b
    if b is None:
        return a
    return TAGS[max(_tag_index(a), _tag_index(b))]


# =========================================================================== tags
def tag_from_blendshapes(scores: Sequence[Mapping[str, float] | None], neutral_ref: int | None = None
                         ) -> list[str | None]:
    """Expression tag per view from blendshape scores (DESIGN 4.9).

    ``scores``: one dict per view (ARKit / MediaPipe names such as ``jawOpen``,
    ``mouthSmileLeft``, ``eyeBlinkRight``, ``browInnerUp``, ``cheekSquintLeft``,
    ``eyeWideRight``, ``browOuterUpLeft``) or None for a view without scores.  Delta b is
    each score minus the subject's per-key minimum over the views that have the key (or minus
    the ``neutral_ref`` view's score when that view has the key); a missing key counts as no
    activation.  L/R keys enter as the max over the two sides.  Returns one of
    ``'neutral'`` / ``'mild'`` / ``'expressive'`` per view, or None for a view without scores
    (use :func:`tag_fallback`).
    """
    views = list(scores)
    keys = set(_SINGLE) | {k for pair in _PAIRS.values() for k in pair}
    base: dict[str, float] = {}
    ref = None
    if neutral_ref is not None:
        if not 0 <= int(neutral_ref) < len(views):
            raise ValueError("neutral_ref out of range")
        ref = views[int(neutral_ref)]
    for k in keys:
        vals = [float(s[k]) for s in views if s is not None and k in s and math.isfinite(float(s[k]))]
        if ref is not None and k in ref and math.isfinite(float(ref[k])):
            base[k] = float(ref[k])
        elif vals:
            base[k] = min(vals)

    def delta(s: Mapping[str, float], k: str) -> float:
        if k not in s or k not in base or not math.isfinite(float(s[k])):
            return 0.0
        return float(s[k]) - base[k]

    out: list[str | None] = []
    for s in views:
        if s is None:
            out.append(None)
            continue
        d = {k: delta(s, k) for k in _SINGLE}
        for name, (l, r) in _PAIRS.items():
            d[name] = max(delta(s, l), delta(s, r))
        expressive = (d["smile"] > _E["expressive_smile"] or d["blink"] > _E["expressive_blink"]
                      or any(d[k] > _E["expressive_other"] for k in ("cheekSquint", "eyeWide", "browOuterUp",
                                                                       "browInnerUp")))
        neutral = (d["jawOpen"] < _E["neutral_jaw_open"] and d["smile"] < _E["neutral_smile"]
                   and d["blink"] < _E["neutral_blink"] and d["browInnerUp"] < _E["neutral_brow_inner"])
        out.append("expressive" if expressive else ("neutral" if neutral else "mild"))
    return out


def _dist(uv: np.ndarray, a: int, b: int) -> float:
    d = uv[int(a)] - uv[int(b)]
    return float(np.hypot(d[0], d[1])) if np.all(np.isfinite(d)) else float("nan")


def mouth_width(uv: Any, scheme_index: Mapping[str, int]) -> float:
    """Mouth width ch_L-ch_R, divided by the rigid outer canthal width ex_L-ex_R when both are
    in ``scheme_index`` (dimensionless, invariant to distance and focal), else in px; NaN when
    the corners are missing."""
    uv = np.asarray(uv, float)
    w = _dist(uv, scheme_index["ch_L"], scheme_index["ch_R"])
    if "ex_L" in scheme_index and "ex_R" in scheme_index:
        ref = _dist(uv, scheme_index["ex_L"], scheme_index["ex_R"])
        return w / ref if ref > 0 else float("nan")
    return w


def tag_fallback(uv: Any, scheme_index: Mapping[str, int], set_mouth_width_median: float | None
                 ) -> tuple[str, list[int]]:
    """Expression tag of a view without blendshape scores (DESIGN 4.9 'No scores', 🆕).

    ``scheme_index`` maps names to point indices: ``ch_L``, ``ch_R`` (required), optional
    ``lip_upper_inner`` / ``lip_lower_inner`` (inner-lip midpoints), ``sto``, ``li`` (points to
    drop) and ``ex_L`` / ``ex_R`` (width reference, :func:`mouth_width`).

    * inner-lip gap / ch-ch > 0.04: the lips are apart, so sto and li are dropped
      (``drop_ids``, the indices of those present in ``scheme_index``);
    * :func:`mouth_width` > 1.08 x ``set_mouth_width_median`` (the median of the same quantity
      over the set): 'mild', else 'neutral'.
    """
    uv = np.asarray(uv, float)
    drop: list[int] = []
    cc = _dist(uv, scheme_index["ch_L"], scheme_index["ch_R"])
    if "lip_upper_inner" in scheme_index and "lip_lower_inner" in scheme_index and cc > 0:
        gap = _dist(uv, scheme_index["lip_upper_inner"], scheme_index["lip_lower_inner"])
        if math.isfinite(gap) and gap / cc > _E["fallback_lip_gap"]:
            drop = [int(scheme_index[k]) for k in ("sto", "li") if k in scheme_index]
    tag = "neutral"
    if set_mouth_width_median is not None and math.isfinite(float(set_mouth_width_median)):
        w = mouth_width(uv, scheme_index)
        if math.isfinite(w) and w > _E["fallback_mouth_width"] * float(set_mouth_width_median):
            tag = "mild"
    return tag, drop


def mobile_chi2_red(e2: Any) -> float:
    """Reduced chi^2 of a view's mobile-class landmarks: sum e_i^2 / (2 n) for whitened radial
    residuals e_i (2 dof each); NaN without points."""
    e2 = np.asarray(e2, float).reshape(-1)
    e2 = e2[np.isfinite(e2)]
    return float(np.sum(e2) / (2.0 * len(e2))) if len(e2) else float("nan")


def retag_from_residuals(mobile_chi2_red: float, current: str | None = None) -> str:
    """Re-tag a view from its mobile-class reduced chi^2 after a solve (DESIGN 4.9, 🆕).

    > 4 -> at least 'mild', > 9 -> 'expressive'; the result is never below ``current``
    (tags only escalate).  The caller re-solves and repeats at most :data:`MAX_RETAG_ROUNDS`
    (3) rounds.
    """
    x = float(mobile_chi2_red)
    implied = "neutral"
    if math.isfinite(x):
        if x > _E["retag_expressive_chi2"]:
            implied = "expressive"
        elif x > _E["retag_mild_chi2"]:
            implied = "mild"
    return _max_tag(current, implied) or implied


# =========================================================================== covariance inflation
def expression_classes(ids: Sequence[str | None]) -> list[str]:
    """Expression class per landmark id from the registry (``face3d.model.registry``);
    unknown / None ids (non-anatomical scheme points) are 'semi_mobile' (🆕 conservative
    default between rigid and mobile)."""
    from ..model.registry import ANATOMICAL
    return [ANATOMICAL[i].expr_class if i is not None and i in ANATOMICAL else "semi_mobile" for i in ids]


def expression_sigma_mm(expr_classes: Sequence[str], kinds_sigma_n_mm: Any, tag: str
                        ) -> tuple[np.ndarray, np.ndarray]:
    """(sigma_expr (N,) mm, drop (N,) bool) for one view's tag (DESIGN 4.9).

    sigma_expr = sqrt(mu^2 - 1) sigma_kind with mu = CLASS_MULT[class][tag] and sigma_kind the
    landmark kind's normal sigma in mm (``kinds_sigma_n_mm``, scalar or (N,), e.g. from
    :data:`face3d.solve.noise.KIND_SIGMA_MM`); drop where mu is infinite (mobile points on an
    expressive view), where sigma_expr is set to inf.
    """
    k = _tag_index(tag)
    cls = list(expr_classes)
    s = np.broadcast_to(np.asarray(kinds_sigma_n_mm, float), (len(cls),)).astype(float)
    mu = np.array([CLASS_MULT[c][k] if c in CLASS_MULT else _unknown_class(c) for c in cls], float)
    drop = ~np.isfinite(mu)
    with np.errstate(invalid="ignore"):
        sig = np.where(drop, np.inf, np.sqrt(np.maximum(mu * mu - 1.0, 0.0)) * s)
    return sig, drop


def _unknown_class(c: str) -> float:
    raise ValueError(f"unknown expression class {c!r} (expected one of {EXPR_CLASSES})")


def projection_jacobians(camera: Camera, X: Any) -> np.ndarray:
    """P_i = d u / d X_i (N, 2, 3) px/mm of a pinhole camera at the points X (head frame, mm)."""
    return _projection_jacobians(camera, X)


def inflate_view_cov(cov: Any, P: Any, sigma_expr: Any) -> np.ndarray:
    """cov + P (sigma_expr^2 I_3) P^T per landmark (px^2); a copy (inputs are not modified).

    ``cov`` (N, 2, 2) px^2, ``P`` (N, 2, 3) px/mm, ``sigma_expr`` (N,) mm (scalar allowed).
    Rows with a non-finite sigma_expr (dropped landmarks) become NaN.
    """
    C = np.array(cov, dtype=float, copy=True)
    P = np.asarray(P, float)
    s = np.broadcast_to(np.asarray(sigma_expr, float), (len(C),))
    if P.shape != (len(C), 2, 3):
        raise ValueError(f"P must have shape ({len(C)}, 2, 3), got {P.shape}")
    fin = np.isfinite(s)
    PPt = np.einsum("nij,nkj->nik", P[fin], P[fin])
    C[fin] = C[fin] + (s[fin] ** 2)[:, None, None] * PPt
    C[~fin] = np.nan
    return C


def apply_expression(uv: Any, cov: Any, P: Any, sigma_expr: Any, drop: Any) -> tuple[np.ndarray, np.ndarray]:
    """(uv', cov') for one view: inflated covariances and dropped landmarks hidden (NaN rows in
    both), ready for :class:`face3d.solve.bundle.ViewObs` (``uv``, ``cov_px``).  Copies."""
    uv2 = np.array(uv, dtype=float, copy=True)
    drop = np.asarray(drop, bool).reshape(-1)
    C = inflate_view_cov(cov, P, np.where(drop, np.inf, np.asarray(sigma_expr, float)))
    uv2[drop] = np.nan
    C[np.isnan(uv2).any(axis=1)] = np.nan
    return uv2, C


def lid_drop(ear: float | None, gaze_pitch_deg: float | None) -> bool:
    """Drop the lid points of a view: blink (EAR < 0.2) or gaze pitch beyond 12 deg (DESIGN 4.9).
    Unknown (None / NaN) inputs do not trigger the drop."""
    e = float("nan") if ear is None else float(ear)
    p = float("nan") if gaze_pitch_deg is None else float(gaze_pitch_deg)
    return bool((math.isfinite(e) and e < _E["lid_ear_min"]) or (math.isfinite(p) and abs(p) > _E["lid_pitch_max_deg"]))


def no_neutral_view(tags: Sequence[str | None]) -> dict | None:
    """Finding ``E-NO-NEUTRAL`` when no view is tagged neutral (DESIGN 4.9, rec BA-9), else None.

    The finding asks the report to suppress lip and lid measurements finer than 1 mm
    (``detail['suppress_regions']``, ``detail['suppress_below_mm']``).  The dict has the
    fields of :class:`face3d.qa.checks.Finding`.
    """
    if any(t == "neutral" for t in tags):
        return None
    d = EXPRESSION["no_neutral_suppress_mm"]
    return {"code": FLAG_NO_NEUTRAL, "severity": "warn", "value": [t for t in tags], "threshold": "neutral",
            "action": "ask", "msg_key": f"solve.{FLAG_NO_NEUTRAL}", "fix_key": f"solve.{FLAG_NO_NEUTRAL}.fix",
            "source": d.source, "badge": d.badge, "photo_id": None,
            "detail": {"suppress_regions": ["lips", "eyes"], "suppress_below_mm": float(d.value)}}


def jaw_config_for_tag(tag: str) -> JawConfig:
    """Jaw hinge settings for a view (DESIGN D-14 / 4.9): theta ~ N(1.5 deg, 1 deg^2) on neutral
    views, sigma 3 deg otherwise, bounded to [0, 30] deg."""
    k = _tag_index(tag)
    sig = float(BUNDLE["jaw_prior_sigma_deg"].value) if k == 0 else float(_E["jaw_expressive_sigma_deg"])
    return JawConfig(enabled=True, prior_mean_deg=float(BUNDLE["jaw_prior_mean_deg"].value), prior_sigma_deg=sig,
                     bounds_deg=(0.0, float(BUNDLE["jaw_bound_max_deg"].value)))
