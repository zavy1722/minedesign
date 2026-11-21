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
* re-tag after a solve, at most 3 rounds (the caller's loop).  :func:`retag_from_residuals`
  keeps the DESIGN 4.9 rule (mobile-class reduced chi^2 > 4 -> at least mild, > 9 ->
  expressive, 🆕).  Since WBS FU-04 the pipeline uses :func:`retag_from_evidence`, whose
  thresholds are quantiles of the engine's own null distributions at stated false-alarm rates
  (see 'Re-tag statistics' below).

Re-tag statistics (WBS FU-04 task 3)
------------------------------------
Measured on the WP-23 fault matrix (30 seeds, docs/RESULTS.md 3.1): the DESIGN thresholds 4
and 9 on a 12-dof reduced chi^2 are the 3e-6 and 1e-17 quantiles of its null, and a jaw
opening never reaches the mobile class at all, because the per-view jaw hinge absorbs it (a
5-15 deg opening is fitted as 3-6 deg against the neutral prior N(1.5 deg, 1 deg^2), the rest
goes into the view's pose and the consensus).  Two statistics, both against the *neutral*
declared noise of the view (never the already inflated one, or a 'mild' view could not
escalate):

* **mobile-class chi^2** (:func:`mobile_chi2_capped`): T = sum_i min(e_i^2, c^2) over the
  view's visible expression-affected landmarks (the pipeline passes the mobile class and the
  jaw-dependent class: the chin points the robust schedule rejects when it does not follow the
  jaw), e_i^2 = r_i^T Sigma_i^-1 r_i the squared Mahalanobis
  residual (full 2x2 covariance: anisotropic since FU-04) and c = 3.035 sigma, the DESIGN D-08
  rejection threshold: a landmark the robust schedule rejected still counts, but no more than
  a rejected one, so a single gross detector outlier cannot tag a view.  Null: T <= chi^2 with
  2 n dof (the cap and the fit only lower it).  Tag 'mild' at T > chi2_(2n)(1 - alpha_mild),
  'expressive' at T > chi2_(2n)(1 - alpha_expressive) (Wilson-Hilferty quantiles,
  :func:`face3d.solve.robust.chi2_quantile_wh`).
* **jaw angle** (:func:`jaw_angle_z`): z = (theta_v - mu) / SD_0, with theta_v the view's
  fitted hinge angle, N(mu, sigma_neutral^2) = N(1.5 deg, 1 deg^2) the DESIGN 4.9 neutral jaw
  population and SD_0 the standard deviation the fitted angle has under 'this view is neutral'
  given the jaw prior it was solved with and its posterior SD (a posterior mean is shrunk:
  SD_0^2 = sigma_neutral^2 - sigma_post^2 on a neutral-tagged view).  One-sided: 'mild' at
  z > z_(1 - alpha_mild_jaw), 'expressive' at z > z_(1 - alpha_expressive_jaw).  A 'mild' tag
  widens the view's jaw prior to 3 deg (:func:`jaw_config_for_tag`), so the next round fits
  the opening itself and the second threshold decides.

Stated false-alarm rates per neutral view (registered defaults, 🆕 provisional):
``retag_mild_alpha`` 0.01 and ``retag_expressive_alpha`` 0.001 for the mobile chi^2,
``retag_mild_jaw_alpha`` 0.05 and ``retag_expressive_jaw_alpha`` 0.005 for the jaw angle (a
5 deg opening is 3.5 sigma of the neutral population, so the DESIGN 7.4 row 'jaw 5-15 deg ->
expressive' cannot be met at a smaller rate).  A false 'mild' costs a x3 mobile-class sigma
on that view; a false 'expressive' drops its mobile points.

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
from .robust import chi2_quantile_wh, norm_ppf

__all__ = [
    "EXPRESSION", "TAGS", "CLASS_MULT", "EXPR_CLASSES", "tag_from_blendshapes", "mouth_width", "tag_fallback",
    "retag_from_residuals", "mobile_chi2_red", "MAX_RETAG_ROUNDS", "expression_sigma_mm", "inflate_view_cov",
    "apply_expression", "projection_jacobians", "lid_drop", "no_neutral_view", "jaw_config_for_tag",
    "FLAG_NO_NEUTRAL", "expression_classes",
]
# WBS FU-04 additions (public, import from this module: mahalanobis_e2, mobile_chi2_capped, jaw_angle_z,
# retag_thresholds, retag_from_evidence, soft_mobile_multiplier) are not in __all__: the face3d.solve
# export list is owned by WP-23.

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
    "retag_mild_alpha": Default(0.01, _NEW, "WBS FU-04 task 3: false-alarm rate per neutral view of the 'mild' "
                                "re-tag from the capped mobile-class chi^2 (null chi^2 with 2 n dof; replaces "
                                "the fixed reduced chi^2 > 4 in the pipeline). Provisional", "", (1e-9, 0.5)),
    "retag_expressive_alpha": Default(0.001, _NEW, "WBS FU-04 task 3: false-alarm rate per neutral view of the "
                                      "'expressive' re-tag from the capped mobile-class chi^2 (replaces the fixed "
                                      "reduced chi^2 > 9 in the pipeline). Provisional", "", (1e-9, 0.5)),
    "retag_mild_jaw_alpha": Default(0.05, _NEW, "WBS FU-04 task 3: false-alarm rate per neutral view of the 'mild' "
                                    "re-tag from the fitted jaw angle against the DESIGN 4.9 neutral population "
                                    "N(1.5 deg, 1 deg^2) (one-sided z > 1.645). Provisional", "", (1e-9, 0.5)),
    "retag_expressive_jaw_alpha": Default(0.005, _NEW, "WBS FU-04 task 3: false-alarm rate per neutral view of the "
                                          "'expressive' re-tag from the fitted jaw angle (one-sided z > 2.576; a "
                                          "5 deg opening, the lower end of the DESIGN 7.4 row, is 3.5 sigma of the "
                                          "neutral population). Provisional", "", (1e-9, 0.5)),
    "retag_cap_sigmas": Default(3.035, "\U0001F522", "DESIGN D-08 / 4.5 rejection threshold (1 % false alarm in 2D): "
                                "cap of one landmark's whitened residual in the mobile-class chi^2 "
                                "(WBS FU-04: a rejected landmark counts, but only as a rejected one)", "sigma",
                                (1e-6, None)),
    "retag_jaw_min_sd_deg": Default(0.5, _NEW, "WBS FU-04 task 3: floor of the null SD of the fitted jaw angle in "
                                    "jaw_angle_z (half the neutral population SD; guards a nearly uninformative "
                                    "view). Provisional", "deg", (1e-6, None)),
    "soft_mobile_alpha": Default(0.20, _NEW, "WBS FU-04 task 4: a view whose capped mobile-class chi^2 exceeds its "
                                 "1 - alpha null quantile without reaching a tag threshold gets its mobile class "
                                 "down-weighted (soft_mobile_multiplier). Provisional", "", (1e-9, 0.9)),
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


# =========================================================================== re-tag statistics (WBS FU-04)
def mahalanobis_e2(residual_px: Any, cov_px: Any) -> np.ndarray:
    """(N,) squared Mahalanobis residuals r_i^T Sigma_i^-1 r_i (chi^2 with 2 dof under the declared
    noise).  ``residual_px`` (N, 2) px, ``cov_px`` (N, 2, 2) px^2; NaN where either is not finite or
    the covariance is not positive definite."""
    r = np.asarray(residual_px, float)
    C = np.asarray(cov_px, float)
    if r.ndim != 2 or r.shape[1] != 2 or C.shape != (len(r), 2, 2):
        raise ValueError("residual_px must be (N, 2) and cov_px (N, 2, 2)")
    out = np.full(len(r), np.nan)
    a, b, d = C[:, 0, 0], 0.5 * (C[:, 0, 1] + C[:, 1, 0]), C[:, 1, 1]
    det = a * d - b * b
    with np.errstate(invalid="ignore"):
        ok = np.isfinite(r).all(axis=1) & np.isfinite(det) & (det > 0) & (a > 0)
    x, y = r[ok, 0], r[ok, 1]
    out[ok] = (d[ok] * x * x - 2.0 * b[ok] * x * y + a[ok] * y * y) / det[ok]
    return out


def mobile_chi2_capped(e2: Any, cap_sigmas: float | None = None) -> tuple[float, int]:
    """(T, dof) of a view's mobile-class landmarks: T = sum_i min(e_i^2, c^2) over the finite
    entries of ``e2`` (squared Mahalanobis residuals, :func:`mahalanobis_e2`), dof = 2 n.

    ``cap_sigmas`` c (default ``expression.retag_cap_sigmas`` = 3.035, DESIGN D-08): a landmark
    beyond the robust rejection threshold counts as a rejected one and no more, so one gross
    outlier cannot tag a view (with n = 1 the cap is below every threshold).  Under the declared
    noise T is stochastically below chi^2 with ``dof`` degrees of freedom.  (0.0, 0) without points."""
    e = np.asarray(e2, float).reshape(-1)
    e = e[np.isfinite(e)]
    c = float(_E["retag_cap_sigmas"]) if cap_sigmas is None else float(cap_sigmas)
    return float(np.sum(np.minimum(e, c * c))), int(2 * len(e))


def jaw_angle_z(theta_deg: float | None, sigma_post_deg: float | None,
                prior_sigma_deg: float | None = None) -> float:
    """z of a view's fitted jaw angle under 'this view is neutral' (WBS FU-04 task 3).

    The DESIGN 4.9 neutral population is theta ~ N(mu, sigma_n^2) (``bundle.jaw_prior_mean_deg``
    1.5, ``bundle.jaw_prior_sigma_deg`` 1).  The view was solved with the jaw prior
    N(mu, s_p^2) (``prior_sigma_deg``; default sigma_n, the neutral tag's prior; 3 deg on a
    'mild' / 'expressive' view) and its fitted angle has the posterior SD s_post
    (``sigma_post_deg``).  In the linear-Gaussian model the fitted angle is
    theta_hat = mu + w (theta_data - mu) with w = 1 - r, r = s_post^2 / s_p^2, and the data-only
    estimate has variance s_d^2 = s_post^2 / (1 - r), so for a neutral view

        Var(theta_hat - mu) = w^2 (sigma_n^2 + s_d^2) = (1 - r)^2 sigma_n^2 + (1 - r) s_post^2

    (= sigma_n^2 - s_post^2 when s_p = sigma_n: a posterior mean is shrunk).  z = (theta_hat - mu)
    over the square root of that variance, with the SD floored at ``expression.retag_jaw_min_sd_deg``
    (0.5 deg: the bundle's s_post is a linearised value and the hinge is bounded and robustly
    weighted, so a nearly uninformative view must not produce a large z from a tiny variance).
    NaN when an input is missing (jaw not fitted, frozen view) or the data carry no information
    on the angle (s_post >= s_p)."""
    if theta_deg is None or sigma_post_deg is None:
        return float("nan")
    th, sp = float(theta_deg), float(sigma_post_deg)
    if not (math.isfinite(th) and math.isfinite(sp)) or sp < 0:
        return float("nan")
    mu, sn = float(BUNDLE["jaw_prior_mean_deg"].value), float(BUNDLE["jaw_prior_sigma_deg"].value)
    s_p = sn if prior_sigma_deg is None else float(prior_sigma_deg)
    if not s_p > 0:
        return float("nan")
    r = (sp / s_p) ** 2
    if r >= 0.98:
        return float("nan")
    var = (1.0 - r) ** 2 * sn * sn + (1.0 - r) * sp * sp
    sd = max(math.sqrt(var), float(_E["retag_jaw_min_sd_deg"]))
    return (th - mu) / sd


def retag_thresholds(dof: int) -> dict:
    """The re-tag thresholds at the registered false-alarm rates (module docstring):
    ``{'chi2_mild', 'chi2_expressive'}`` for a mobile-class chi^2 with ``dof`` degrees of freedom
    (inf when dof <= 0) and ``{'jaw_z_mild', 'jaw_z_expressive'}``."""
    out = {"jaw_z_mild": float(norm_ppf(1.0 - float(_E["retag_mild_jaw_alpha"]))),
           "jaw_z_expressive": float(norm_ppf(1.0 - float(_E["retag_expressive_jaw_alpha"])))}
    if dof > 0:
        out["chi2_mild"] = float(chi2_quantile_wh(float(dof), 1.0 - float(_E["retag_mild_alpha"])))
        out["chi2_expressive"] = float(chi2_quantile_wh(float(dof), 1.0 - float(_E["retag_expressive_alpha"])))
    else:
        out["chi2_mild"] = out["chi2_expressive"] = math.inf
    return out


def retag_from_evidence(mobile_T: float, mobile_dof: int, jaw_z: float = float("nan"),
                        current: str | None = None) -> tuple[str, dict]:
    """Re-tag a view after a solve from its two statistics (WBS FU-04 task 3; module docstring).

    ``mobile_T``, ``mobile_dof`` from :func:`mobile_chi2_capped` on residuals whitened by the
    view's *neutral* declared noise; ``jaw_z`` from :func:`jaw_angle_z` (NaN: not available).
    Returns ``(tag, detail)``: the tag is never below ``current`` (tags only escalate; the caller
    re-solves and repeats at most :data:`MAX_RETAG_ROUNDS` rounds) and ``detail`` holds the
    statistics, the thresholds (:func:`retag_thresholds`) and ``'by'``, the statistics that
    crossed a threshold ('mobile_chi2', 'jaw_angle')."""
    thr = retag_thresholds(int(mobile_dof))
    T, z = float(mobile_T), float(jaw_z)
    implied, by = "neutral", []
    if math.isfinite(T) and mobile_dof > 0:
        if T > thr["chi2_expressive"]:
            implied, by = "expressive", ["mobile_chi2"]
        elif T > thr["chi2_mild"]:
            implied, by = "mild", ["mobile_chi2"]
    if math.isfinite(z):
        if z > thr["jaw_z_expressive"]:
            by = (by if implied == "expressive" else []) + ["jaw_angle"]
            implied = "expressive"
        elif z > thr["jaw_z_mild"]:
            if implied == "neutral":
                implied, by = "mild", ["jaw_angle"]
            elif implied == "mild":
                by = by + ["jaw_angle"]
    tag = _max_tag(current, implied) or implied
    return tag, {"mobile_chi2": T, "mobile_dof": int(mobile_dof), "jaw_z": z, "implied": implied, "by": by, **thr}


def soft_mobile_multiplier(mobile_T: float, mobile_dof: int) -> float:
    """Sigma multiplier (>= 1) of the mobile class of a view whose mobile chi^2 is elevated but
    below the tag thresholds (WBS FU-04 task 4, robust down-weighting).

    1 while T <= q = chi2_dof(1 - ``expression.soft_mobile_alpha``); above it sqrt(T / dof),
    the factor that brings the class's reduced chi^2 back to 1 (never below 1, never above the
    'mild' class multiplier 3, which a tagged view gets anyway)."""
    T = float(mobile_T)
    if not math.isfinite(T) or mobile_dof <= 0:
        return 1.0
    q = float(chi2_quantile_wh(float(mobile_dof), 1.0 - float(_E["soft_mobile_alpha"])))
    if T <= q:
        return 1.0
    return float(min(max(math.sqrt(T / float(mobile_dof)), 1.0), CLASS_MULT["mobile"][1]))


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
