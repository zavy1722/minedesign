"""Mirror test: was this photo horizontally flipped (selfie mirror, editor flip)?

DESIGN D-10, 4.10, H6, H7 (WBS WP-15).  A mirrored photo's landmarks satisfy
obs[pi(i)] = (W - u_i, v_i) (DESIGN 3.1, :func:`face3d.io.image_ops.flip_uv`): the face seen
is the mirror image of the subject with left/right labels swapped.  For an exactly symmetric
face that is indistinguishable from the real photo, so the test compares the two hypotheses
on the consensus shape and predicts how detectable a flip *could* be from the consensus's own
asymmetry:

* C0, C1: robust costs sum_i min(e_i^2, 3.035^2) (e_i = ||Sigma_i^-1/2 r_i|| the whitened
  radial residual; a point beyond the DESIGN D-08 rejection threshold 3.035 sigma counts as an
  outlier with a constant cost, so C ~ chi^2 with 2 n_v - 6 dof for inliers) after a WP-06 PnP
  (:func:`face3d.solve.pnp.solve_pnp`, multi-start, whitened by per-axis sigma_px from
  ``noise_cov``, focal fixed at ``camera_init.f``) refined by Huber IRLS (delta 2 sigma, D-08)
  with the full 2x2 covariances, for the landmarks as given (C0) and flipped (C1; uv' = W - u,
  labels permuted by pi, covariances reflected and permuted, principal point W - c_x);
* delta = (C0 - C1) / C0 (relative gain of the flip) and gap = C0 - C1;
* A = (X - reflect(X_pi)) / 2: the asymmetric part of the consensus about ``plane`` (n, d)
  (default the head frame's sagittal plane x = 0), with X_pi the label-permuted consensus;
* g = || (I - P) w ||^2 with w the stacked Sigma_i^-1/2 J_i A_i (J_i = d u / d X_i at the
  as-given solved pose) and P the projector onto the whitened pose Jacobian (rotation and
  translation): the whitened image size of the asymmetry that a pose refit cannot absorb, i.e.
  the predicted detectability of a flip.  P carries the Huber weights the robust fit gives the
  shifted landmarks (:func:`_robust_perp`, final FU-04 review): for an asymmetry spread evenly
  at the scales near g_min it is the least-squares projector, and an asymmetry carried by one or
  two landmarks stays on them instead of being spread over the rest (where the least-squares
  projection made it uncapped and promised a power near 1 that the capped rule did not have:
  'keep' on ~30 % of mirrored views).  ``g_raw`` = ||w||^2 is the WBS formula without the
  projection; it over-predicts the observed gap by up to ~25x when the asymmetry is largely a
  rigid motion (a mid-sagittal plane slightly off the reference plane), on the WP-11 surface
  subjects its correlation with the gap is ~0.3-0.5 against ~0.8-0.9 after projection, so a
  'keep' could be reported for a flip the test could not have seen (H7 prefers 'undetermined');
* decision (recalibrated by WBS FU-04 task 3 against the test's own null distribution, below):
  ``'unverifiable'`` when every view of the set is a front-camera selfie (nothing to compare
  against; H7); ``'suggest_flip'`` when delta > rel (0.10 front camera, 0.20 other; DESIGN
  D-10) **and** gap > tau; ``'undetermined'`` (flag ``M-GAP-SIGNIFICANT``) when gap > tau but
  delta <= rel: the evidence favours the flip at the alpha level although the relative rule
  does not confirm it, so the view is never called 'keep'; otherwise ``'keep'`` when
  g >= g_min (the *complete* rule had the power to suggest a flip, see below, and the gap is
  not significant) and ``'undetermined'`` when g < g_min (the face is too symmetric at this
  noise level for a non-detection to mean anything; H7);
* ``preselect_flip`` (UI pre-selects [Flip]) only for ``'suggest_flip'`` with delta > 0.2 and
  front-camera EXIF or agreement of other views.

Null distribution and thresholds (WBS FU-04 task 3; WP-15 note 'g ~12 is needed for 95 %
detection' with the old absolute threshold 2 sqrt(2 n_v))
---------------------------------------------------------
The flipped hypothesis explains the view with the mirror image of the consensus, X - 2 A, so
its whitened prediction differs from the as-given one by 2 w_perp with ||w_perp||^2 = g.
With whitened noise eps ~ N(0, I) and a correct as-given labelling,
C1 - C0 = ||eps + 2 w_perp||^2 - ||eps||^2, i.e. to first order

    gap = C0 - C1 ~ N(-4 g, 16 g)   (not mirrored),      gap ~ N(+4 g, 16 g)   (mirrored).

* False flips: P(gap > tau | not mirrored) = Phi(-(tau + 4 g) / (4 sqrt(g))) is largest at
  g = tau / 4, where it equals Phi(-sqrt(tau)).  So tau = z_(1 - alpha)^2 bounds the false-flip
  rate of a view by alpha *whatever the asymmetry*: ``mirror.flip_alpha`` = 1e-4 gives
  tau = 13.83 (:func:`gap_threshold`).  This replaces 2 sqrt(2 n_v) (15.5 at n_v = 30), which
  grows with the number of landmarks although the gap's null distribution does not.
* Power of the gap condition alone: P(gap > tau | mirrored) = Phi((4 g - tau) / (4 sqrt(g))) >= p
  <=> sqrt(g) >= (z_p + sqrt(z_p^2 + tau)) / 2: g = 8.16 for alpha = 1e-4, p = 0.95
  (:func:`derived_g_min` without ``n_v``; :data:`G_MIN`).  This is only a *lower bound* of the
  g a 'keep' needs, because a flip is suggested by the complete rule
  (gap > tau **and** gap > rel / (1 - rel) * C1) on costs capped at 3.035 sigma (FU-04 review:
  at g = 8.3, 44 landmarks, rel 0.20 the engine suggested the flip for 77 % of mirrored views,
  not 95 %).
* g_min from the complete rule (:func:`rule_power`, :func:`derived_g_min` with ``n_v``): per
  landmark the as-given residual of a mirrored view is eps_i + d_i, d_i = 2 w_perp,i, so its
  contribution to the gap is x_i = min(|eps_i + d_i|^2, c^2) - min(|eps_i|^2, c^2) and to C1 it
  is y_i = min(|eps_i|^2, c^2) (c = 3.035, eps_i ~ N(0, I_2)).  Mean, variance and covariance
  of (x_i, y_i) depend on |d_i| only (tabulated once by quadrature, :func:`_cap_moments`;
  without the cap E x = |d|^2, Var x = 4 |d|^2, i.e. the 4 g / 16 g above).  Summed over the
  view's landmarks (C1 scaled to its 2 n_v - 6 dof), (gap, C1) is treated as bivariate normal
  and power = P(gap > tau, gap > rel / (1 - rel) C1).  g_min of a view is the g at which that
  power reaches ``mirror.keep_power`` = 0.95 *for the view's own distribution of the asymmetry
  over its landmarks* (the pattern d_i scaled by a common factor): an asymmetry concentrated in
  a few landmarks is capped and needs a larger g than one spread evenly.  For 44 landmarks and
  rel 0.20: 11.6 spread evenly (WP-15 note 'g ~12'), about 13 for a random pattern; it grows
  with n_v (C1 grows, the relative rule gets harder).  The cap can only lower the false-flip
  rate bound above (Var x <= 4 E x for every |d|, asserted in the tests).
  Below g_min a non-detection is 'undetermined', never 'keep'; and a significant gap is never
  'keep' whatever g.  (DESIGN 4.10's g_min = 4 with the old threshold answered 'keep' /
  'undetermined' at a detectability where the test found 44 % of the flips.)
* The noise must be the noise the view is *declared* with and should include the consensus
  uncertainty: pass ``noise_cov`` = declared covariance + J Sigma_consensus J^T (the predictive
  covariance of the held-out view, pooled over the other views:
  :func:`face3d.solve.observability.heldout_prediction`), as the pipeline does.  A conservative
  (too wide) noise model only lowers the false-flip rate.
* :func:`project_mirror_status` pools the per-view detectabilities (``g_pooled`` = sum of g):
  a set none of whose views could be tested is 'undetermined' as a whole.

Explicit ``g_min`` / ``gap_threshold`` arguments override the derived values (an explicit
``g_min`` replaces the per-view value of the complete rule); the derived values are what
:func:`mirror_test` uses by default.  The DESIGN defaults ``mirror.g_min`` (4) and
``mirror.gap_k`` (2) stay registered for the record only: no code reads them since FU-04 (the
gap threshold is tau from ``mirror.flip_alpha`` or the explicit ``gap_threshold`` argument, and
g_min is derived per view unless a caller passes its own value).

The engine never flips anything: it never mutates its inputs and applying a flip is a
recorded user (or explicit CLI flag) decision in the project (DESIGN D-10; WP-20).

``margin`` = gap - tau (cost units; > 0 means the absolute gap is significant).
Defaults are registered under ``mirror`` in :mod:`face3d.core.config` (🆕 / 🧠).
numpy + stdlib only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from ..core.config import Default, register_defaults
from ..geometry.camera import Camera
from ..geometry.procrustes import reflect
from ..io.image_ops import flip_uv
from .camera_model import _cov_sigma_px, _pinhole_jac, _pinhole_proj, projection_jacobians, refine_pose
from .noise import whitening
from .pnp import solve_pnp
from .robust import norm_ppf

# gap_threshold, derived_g_min, rule_power, G_MIN and GAP_THRESHOLD (WBS FU-04) are public but not in __all__: the
# face3d.solve export list is owned by WP-23 (import them from this module).
__all__ = ["MIRROR", "MirrorDecision", "mirror_test", "flip_cov", "DECISIONS", "project_mirror_status"]

_BRAIN = "\U0001F9E0"
_NEW = "\U0001F195"

MIRROR = register_defaults("mirror", {
    "g_min": Default(4.0, _NEW, "DESIGN D-10 / 4.10: 'undetermined' when the predicted gap g < 4 (the DESIGN "
                     "value; since WBS FU-04 mirror_test derives g_min per view from flip_alpha and keep_power "
                     "unless a caller passes its own g_min; not read by any code, kept for the record)", "",
                     (0.0, None)),
    "flip_alpha": Default(1e-4, _NEW, "WBS FU-04 task 3: stated false-flip rate per view of the mirror test. "
                          "Null gap ~ N(-4 g, 16 g); sup over g of P(gap > tau) = Phi(-sqrt(tau)), so "
                          "tau = z_(1-alpha)^2 = 13.83 (DESIGN 7.4 asks FPR <= 0.02; the honesty gate 'no flip "
                          "suggested on an unmirrored view' over several hundred views per release run "
                          "needs a rate well below 1e-3). Derived, test-bed checked, provisional", "",
                          (1e-9, 0.5)),
    "keep_power": Default(0.95, _NEW, "WBS FU-04 task 3 / DESIGN 7.4 'TPR >= 0.95': g_min is the detectability at "
                          "which a mirrored view is flagged with this probability by the complete rule (gap > tau "
                          "and delta > rel on costs capped at reject_k; rule_power / derived_g_min(n_v, rel)): 11.6 "
                          "at 44 evenly loaded landmarks and rel 0.20 (WP-15 note: g ~12), per view from its own "
                          "asymmetry pattern; the gap condition alone gives the lower bound 8.16. Below it a "
                          "non-detection is 'undetermined', not 'keep'", "", (0.5, 1.0)),
    "rel_front": Default(0.10, _BRAIN, "DESIGN D-10 / 4.10: suggest a flip at delta > 10 % on a front camera "
                         "([Art 3.6])", "", (0.0, 1.0)),
    "rel_other": Default(0.20, _BRAIN, "DESIGN D-10 / 4.10: suggest a flip at delta > 20 % on other cameras "
                         "([Art 3.6])", "", (0.0, 1.0)),
    "gap_k": Default(2.0, _BRAIN, "DESIGN D-10 / 4.10: absolute gap C0 - C1 > 2 sqrt(2 n_v) ([Art 3.6], derived). "
                     "Superseded since WBS FU-04 by flip_alpha / the gap_threshold argument (tau = 13.83); not "
                     "read by mirror_test, kept for the record", "", (0.0, None)),
    "preselect_delta": Default(0.20, _NEW, "DESIGN 4.10: UI pre-selects [Flip] only when delta > 0.2 and front "
                               "camera or other views agree", "", (0.0, 1.0)),
    "huber_delta": Default(2.0, _BRAIN, "DESIGN D-08: Huber delta 2 sigma in the robust pose refinement of "
                           "C0 / C1", "sigma", (1e-6, None)),
    "reject_k": Default(3.035, "\U0001F522", "DESIGN D-08 / 4.5: residuals beyond 3.035 sigma (1 % false alarm in "
                        "2D) count as rejected outliers: C = sum_i min(e_i^2, 3.035^2)", "sigma", (1e-6, None)),
})
_M = {k: MIRROR[k].value for k in MIRROR}


def gap_threshold(alpha: float | None = None) -> float:
    """tau = z_(1 - alpha)^2: the gap C0 - C1 above which a flip is suggested, with the false-flip
    rate of a view bounded by ``alpha`` (default ``mirror.flip_alpha``) for every asymmetry
    (module docstring: sup_g Phi(-(tau + 4 g) / (4 sqrt(g))) = Phi(-sqrt(tau)))."""
    a = float(_M["flip_alpha"]) if alpha is None else float(alpha)
    if not 0.0 < a < 0.5:
        raise ValueError(f"alpha must be in (0, 0.5), got {a!r}")
    return float(norm_ppf(1.0 - a) ** 2)


_CAP_TABLE: dict = {}


def _cap_moments(d: Any, c: float | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    """Per-landmark moments of the capped costs of a mirrored view (module docstring).

    For eps ~ N(0, I_2) and a whitened shift of length ``d`` (array), with
    x = min(|eps + d|^2, c^2) - min(|eps|^2, c^2) and y = min(|eps|^2, c^2): returns
    (E x, Var x, Cov(x, y)) at ``d`` and the scalars (E y, Var y).  Deterministic quadrature on a
    fixed grid, tabulated once per cap ``c`` (default ``mirror.reject_k``) and interpolated; d
    beyond the table (12) is clamped (the moments are constant there: the point is capped)."""
    cc = float(_M["reject_k"]) if c is None else float(c)
    key = round(cc, 9)
    if key not in _CAP_TABLE:
        h = 0.05
        ax = np.arange(-7.0, 7.0 + 0.5 * h, h)
        gx, gy = np.meshgrid(ax, ax, indexing="ij")
        wgt = np.exp(-0.5 * (gx * gx + gy * gy))
        wgt /= wgt.sum()
        c2 = cc * cc
        y = np.minimum(gx * gx + gy * gy, c2)
        ey = float(np.sum(wgt * y))
        vy = float(np.sum(wgt * y * y) - ey * ey)
        dd = np.concatenate([np.arange(0.0, 6.0, 0.1), np.arange(6.0, 12.01, 0.5)])
        ex, vx, cxy = np.empty(len(dd)), np.empty(len(dd)), np.empty(len(dd))
        for k, dk in enumerate(dd):
            x = np.minimum((gx + dk) ** 2 + gy * gy, c2) - y
            ex[k] = np.sum(wgt * x)
            vx[k] = np.sum(wgt * x * x) - ex[k] ** 2
            cxy[k] = np.sum(wgt * x * y) - ex[k] * ey
        _CAP_TABLE[key] = (dd, ex, vx, cxy, ey, vy)
    dd, ex, vx, cxy, ey, vy = _CAP_TABLE[key]
    a = np.abs(np.asarray(d, dtype=float))
    return np.interp(a, dd, ex), np.interp(a, dd, vx), np.interp(a, dd, cxy), ey, vy


def _norm_cdf(x: Any) -> np.ndarray:
    return 0.5 * (1.0 + np.vectorize(math.erf)(np.asarray(x, dtype=float) / math.sqrt(2.0)))


def rule_power(d: Any, rel: float, tau: float | None = None, n_v: int | None = None) -> float:
    """Probability that the complete rule (gap > tau and delta > rel, capped costs) suggests a flip
    for a mirrored view whose landmarks carry the whitened shifts of length ``d`` ((n,);
    d_i = 2 |w_perp,i|, so sum d_i^2 = 4 g).  ``n_v``: visible landmarks (default ``len(d)``; C1 has
    2 n_v - 6 dof).  Bivariate-normal approximation of (gap, C1); see the module docstring."""
    dn = np.abs(np.asarray(d, dtype=float).reshape(-1))
    n = len(dn) if n_v is None else int(n_v)
    t = gap_threshold() if tau is None else float(tau)
    r = float(rel)
    if not 0.0 <= r < 1.0:
        raise ValueError(f"rel must be in [0, 1), got {rel!r}")
    ex, vx, cxy, ey, vy = _cap_moments(dn)
    mg, vg = float(ex.sum()), float(vx.sum())
    if vg <= 0.0:
        return 0.0
    dof = max(2.0 * n - 6.0, 1.0) / (2.0 * max(n, 1))
    m1, v1, cov = n * ey * dof, n * vy * dof, float(cxy.sum()) * dof
    k = r / (1.0 - r)
    # integrate over C1 (normal, 61-point grid over +-5 sd): gap | C1 is normal
    z = np.linspace(-5.0, 5.0, 61)
    pz = np.exp(-0.5 * z * z)
    pz /= pz.sum()
    c1 = m1 + math.sqrt(v1) * z
    rho = cov / math.sqrt(vg * v1)
    rho = min(max(rho, -0.99), 0.99)
    mu_c = mg + rho * math.sqrt(vg) * z
    sd_c = math.sqrt(vg * (1.0 - rho * rho))
    need = np.maximum(t, k * c1)
    return float(np.sum(pz * _norm_cdf((mu_c - need) / sd_c)))


def _g_min_for_pattern(d: np.ndarray, rel: float, tau: float, power: float, n_v: int | None = None) -> float:
    """g at which the complete rule reaches ``power`` when the pattern ``d`` is scaled by a common
    factor (inf when no scale up to 100 x reaches it, or the pattern is zero)."""
    dn = np.abs(np.asarray(d, dtype=float).reshape(-1))
    g0 = float(np.sum(dn * dn)) / 4.0
    if not g0 > 0.0:
        return float("inf")
    lo, hi = 0.0, 1.0
    while rule_power(hi * dn, rel, tau, n_v) < power:
        lo, hi = hi, hi * 2.0
        if hi > 100.0 or float(np.max(hi * dn)) > 1e3:
            return float("inf")
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if rule_power(mid * dn, rel, tau, n_v) < power:
            lo = mid
        else:
            hi = mid
    return float(hi * hi * g0)


def derived_g_min(tau: float | None = None, power: float | None = None, n_v: int | None = None,
                  rel: float | None = None) -> float:
    """Smallest detectability g at which a mirrored view is flagged with probability ``power``
    (default ``mirror.keep_power``) at the gap threshold ``tau`` (default :func:`gap_threshold`).

    ``n_v`` None: the gap condition alone, ((z_p + sqrt(z_p^2 + tau)) / 2)^2 from
    gap ~ N(4 g, 16 g): a lower bound (8.16 at the defaults).  ``n_v`` given: the complete rule
    (gap > tau and delta > ``rel``, default ``mirror.rel_other``; costs capped at
    ``mirror.reject_k``) for an asymmetry spread evenly over ``n_v`` landmarks
    (:func:`rule_power`); :func:`mirror_test` uses the view's own pattern instead of the even one."""
    t = gap_threshold() if tau is None else float(tau)
    p = float(_M["keep_power"]) if power is None else float(power)
    if not 0.5 <= p < 1.0 or t < 0:
        raise ValueError("power must be in [0.5, 1) and tau >= 0")
    if n_v is None:
        z = float(norm_ppf(p)) if p > 0.5 else 0.0
        return float(((z + math.sqrt(z * z + t)) / 2.0) ** 2)
    if int(n_v) < 4:
        raise ValueError("n_v must be >= 4")
    r = float(_M["rel_other"]) if rel is None else float(rel)
    return _g_min_for_pattern(np.ones(int(n_v)), r, t, p, int(n_v))


#: Gap threshold tau (13.83) and the gap-only lower bound of g_min (8.16) at the registered defaults
#: (WBS FU-04).  The g_min a decision used is per view (complete rule): ``MirrorDecision.g_min``.
GAP_THRESHOLD: float = gap_threshold()
G_MIN: float = derived_g_min()

#: The four answers of the mirror test (DESIGN 4.10; H7: undetermined / unverifiable are first class).
DECISIONS: tuple[str, ...] = ("keep", "suggest_flip", "undetermined", "unverifiable")


@dataclass
class MirrorDecision:
    """Result of :func:`mirror_test` for one view (DESIGN D-10, 4.10).

    delta : (C0 - C1) / C0, relative cost reduction of the flipped hypothesis.
    g : predicted detectability ||(I - P) Sigma^-1/2 J A||^2 of the consensus asymmetry
        (pose-absorbable part removed, P weighted like the robust fit: :func:`_robust_perp`;
        ``g_raw`` without the projection).
    gap : C0 - C1 (cost units, ~chi^2).
    margin : gap - ``gap_threshold`` (> 0: the absolute gap is significant).
    g_min, gap_threshold : the thresholds this decision used (derived from ``mirror.flip_alpha``
        and ``mirror.keep_power`` unless given explicitly; g_min is per view: the complete rule
        on the view's own asymmetry pattern, n_v and camera class, never below :data:`G_MIN`).
    power : predicted probability that the complete rule suggests a flip if this view is mirrored.
    decision : 'keep' | 'suggest_flip' | 'undetermined' | 'unverifiable'.
    preselect_flip : the UI may pre-select [Flip] (never applied automatically).
    """

    delta: float
    g: float
    gap: float
    margin: float
    decision: str
    preselect_flip: bool
    C0: float = float("nan")
    C1: float = float("nan")
    g_raw: float = float("nan")
    n_v: int = 0
    rel_threshold: float = float("nan")
    g_min: float = float("nan")
    gap_threshold: float = float("nan")
    power: float = float("nan")
    camera: Camera | None = None           # as-given solved pose (focal fixed)
    camera_flipped: Camera | None = None   # pose of the flipped hypothesis (in the flipped image)
    flags: list[str] = field(default_factory=list)


def flip_cov(cov: Any, perm: Sequence[int]) -> np.ndarray:
    """Covariances of horizontally flipped landmarks: out[pi[i]] = F cov[i] F, F = diag(-1, 1)."""
    C = np.asarray(cov, float)
    p = np.asarray(perm, np.int64)
    F = np.array([1.0, -1.0, -1.0, 1.0]).reshape(2, 2)        # sign pattern of F C F
    out = np.empty_like(C)
    out[p] = C * F
    return out


def _fit(X: np.ndarray, uv: np.ndarray, cov: np.ndarray, like: Camera, cx: float, delta: float
         ) -> tuple[float, Camera, np.ndarray]:
    """Robust whitened pinhole fit (focal fixed): (cost C, camera, whitened residuals)."""
    W = whitening(cov)
    r = solve_pnp(X, uv, like.width, like.height, f_px=like.f, estimate_focal=False, cx=cx, cy=like.cy,
                  sigma_px=_cov_sigma_px(cov), huber_sigmas=None)
    cam = Camera(like.f, cx, like.cy, like.width, like.height)
    ph = _pinhole_proj(cam)
    R, t, _, e = refine_pose(lambda R_, t_, x_: ph(R_, t_, x_, X), r.camera.R, r.camera.t, uv, W, delta=delta,
                              jac=_pinhole_jac(cam, X))
    cam.R, cam.t = R, t
    c = float(_M["reject_k"])
    return float(np.sum(np.minimum(e * e, c * c))), cam, e


def _robust_perp(w: np.ndarray, Jp: np.ndarray, delta: float, rounds: int = 10) -> np.ndarray:
    """(I - P_h) w: the whitened asymmetry ``w`` (2n,) minus the part the *robust* pose fit absorbs
    (final FU-04 review).  P_h projects onto the whitened pose Jacobian ``Jp`` (2n, 6) weighted
    with the Huber IRLS weights :func:`refine_pose` gives the as-given residuals of a mirrored
    view: h_i = min(1, delta / e_i), e_i = sqrt(d_i^2 + 2) the expected radial residual
    (d_i = 2 |w_perp,i| the shift, E |eps_i|^2 = 2 the noise), iterated to a fixed point from the
    least-squares projection.  An asymmetry carried by one or two landmarks is treated as outliers
    by the robust fit, which does not move the pose: the shift stays on those landmarks, where the
    cost cap bounds the gap.  The least-squares projection spread it over the other landmarks,
    where it is not capped and grows with scale, and predicted a power near 1 for a rule that
    found 69 % of the flips on a front camera (10 % on a rear one) and answered 'keep' on about
    30 % of the mirrored views.  When every e_i <= delta (an
    evenly spread asymmetry at the scales near g_min) all weights are 1 and this is the
    least-squares projection."""
    h = np.ones(len(w) // 2)
    wp = w
    for _ in range(int(rounds)):
        sh = np.repeat(np.sqrt(h), 2)
        wp = w - Jp @ np.linalg.lstsq(Jp * sh[:, None], w * sh, rcond=None)[0]
        d = 2.0 * np.linalg.norm(wp.reshape(-1, 2), axis=1)
        e = np.sqrt(d * d + 2.0)
        h_new = np.where(e <= delta, 1.0, delta / e)
        if np.allclose(h_new, h, rtol=1e-6, atol=1e-9):
            break
        h = h_new
    return wp


def _pose_jacobian(cam: Camera, X: np.ndarray) -> np.ndarray:
    """d u / d (omega, t) (n, 2, 6) of a pinhole camera; omega is the left rotation increment."""
    Xc = cam.to_camera(X)
    z = Xc[:, 2]
    A = np.zeros((len(Xc), 2, 3))
    A[:, 0, 0] = cam.f / z
    A[:, 1, 1] = cam.f / z
    A[:, 0, 2] = -cam.f * Xc[:, 0] / z ** 2
    A[:, 1, 2] = -cam.f * Xc[:, 1] / z ** 2
    S = np.zeros((len(Xc), 3, 3))
    S[:, 0, 1], S[:, 0, 2] = -Xc[:, 2], Xc[:, 1]
    S[:, 1, 0], S[:, 1, 2] = Xc[:, 2], -Xc[:, 0]
    S[:, 2, 0], S[:, 2, 1] = -Xc[:, 1], Xc[:, 0]
    return np.concatenate([-np.einsum("nij,njk->nik", A, S), A], axis=2)


def mirror_test(uv: Any, W: float, perm: Sequence[int], consensus_X: Any, noise_cov: Any, camera_init: Camera, *,
                is_front_camera: bool, all_views_front: bool, other_views_agree: bool,
                plane: tuple = (np.array([1.0, 0.0, 0.0]), 0.0), g_min: float | None = None,
                rel_front: float = _M["rel_front"], rel_other: float = _M["rel_other"],
                gap_threshold: float | None = None) -> MirrorDecision:
    """Mirror test of one view against the consensus shape (DESIGN D-10, 4.10).

    ``uv`` (N, 2) px as detected (NaN rows hidden); ``W`` image width px; ``perm`` the
    scheme's L/R label permutation; ``consensus_X`` (N, 3) mm, ideally the BA consensus
    *without* this view (DESIGN 4.10); ``noise_cov`` (N, 2, 2) px^2 of the view: the noise it is
    declared with, ideally plus the projected consensus covariance (module docstring);
    ``g_min`` / ``gap_threshold``: None (default) = derived from ``mirror.flip_alpha`` and
    ``mirror.keep_power`` (:func:`derived_g_min`, :func:`gap_threshold`; an explicit
    ``gap_threshold`` with ``g_min`` None derives g_min from it);
    ``camera_init`` gives focal, principal point and image size (its pose is not used);
    ``is_front_camera`` / ``all_views_front`` from EXIF (Q-FRONTCAM); ``other_views_agree``:
    at least two other views independently support the flip (UI pre-selection only).
    See the module docstring for the statistics and the decision rule.  Inputs are never
    modified.
    """
    uv = np.array(uv, dtype=float, copy=True)
    X = np.array(consensus_X, dtype=float, copy=True)
    cov = np.array(noise_cov, dtype=float, copy=True)
    perm = np.array(perm, dtype=np.int64, copy=True)
    N = len(uv)
    if X.shape != (N, 3) or cov.shape != (N, 2, 2) or perm.shape != (N,):
        raise ValueError("uv (N,2), consensus_X (N,3), noise_cov (N,2,2) and perm (N,) must agree")
    delta_h = float(_M["huber_delta"])
    rel = float(rel_front) if is_front_camera else float(rel_other)
    # as given
    vis0 = np.isfinite(uv).all(axis=1) & np.isfinite(X).all(axis=1) & np.isfinite(cov).all(axis=(1, 2))
    # flipped (labels permuted, u -> W - u, covariances reflected)
    uv1 = flip_uv(uv, float(W), perm)
    cov1 = flip_cov(cov, perm)
    vis1 = np.isfinite(uv1).all(axis=1) & np.isfinite(X).all(axis=1) & np.isfinite(cov1).all(axis=(1, 2))
    n_v = int(vis0.sum())
    if n_v < 6 or int(vis1.sum()) < 6:
        raise ValueError("mirror_test needs at least 6 visible landmarks")
    C0, cam0, _ = _fit(X[vis0], uv[vis0], cov[vis0], camera_init, float(camera_init.cx), delta_h)
    C1, cam1, _ = _fit(X[vis1], uv1[vis1], cov1[vis1], camera_init, float(W) - float(camera_init.cx), delta_h)
    gap = C0 - C1
    dlt = gap / C0 if C0 > 0 else 0.0
    # predicted detectability of a flip from the consensus asymmetry about the plane
    n_vec, d_off = np.asarray(plane[0], float), float(plane[1])
    A = 0.5 * (X - reflect(X[perm], n_vec, d_off))
    Wh = whitening(cov[vis0])
    w = np.einsum("nij,njk,nk->ni", Wh, projection_jacobians(cam0, X[vis0]), A[vis0]).reshape(-1)
    g_raw = float(w @ w)
    Jp = np.einsum("nij,njk->nik", Wh, _pose_jacobian(cam0, X[vis0])).reshape(-1, 6)
    w_perp = _robust_perp(w, Jp, delta_h)
    g = float(w_perp @ w_perp)
    thr_gap = GAP_THRESHOLD if gap_threshold is None else float(gap_threshold)
    # per-landmark whitened shift of the flipped prediction, d_i = 2 |w_perp,i| (sum d_i^2 = 4 g)
    d_pts = 2.0 * np.linalg.norm(w_perp.reshape(-1, 2), axis=1)
    power = rule_power(d_pts, rel, thr_gap, n_v)
    if g_min is None:
        # complete rule on this view's pattern; never below the gap-only bound
        gmin = max(_g_min_for_pattern(d_pts, rel, thr_gap, float(_M["keep_power"]), n_v), derived_g_min(thr_gap))
    else:
        gmin = float(g_min)
    margin = gap - thr_gap
    flags: list[str] = []
    if all_views_front:
        decision = "unverifiable"
    elif dlt > rel and gap > thr_gap:
        # significant evidence for the flip: its false-alarm rate is bounded by flip_alpha for every g
        decision = "suggest_flip"
    elif gap > thr_gap:
        # significant gap that the relative rule does not confirm: never 'keep' (FU-04 review)
        decision = "undetermined"
        flags.append("M-GAP-SIGNIFICANT")
    elif g < gmin:
        decision = "undetermined"
    else:
        decision = "keep"
    if decision == "suggest_flip":
        flags.append("M-SUGGEST-FLIP")
    elif decision in ("undetermined", "unverifiable"):
        flags.append("M-" + decision.upper())
    pre = bool(decision == "suggest_flip" and dlt > float(_M["preselect_delta"])
               and (bool(is_front_camera) or bool(other_views_agree)))
    return MirrorDecision(delta=float(dlt), g=g, gap=float(gap), margin=float(margin), decision=decision,
                          preselect_flip=pre, C0=float(C0), C1=float(C1), g_raw=g_raw, n_v=n_v,
                          rel_threshold=rel, g_min=float(gmin), gap_threshold=float(thr_gap), power=float(power),
                          camera=cam0, camera_flipped=cam1, flags=flags)


def project_mirror_status(decisions: Sequence[MirrorDecision], all_views_front: bool) -> dict:
    """Project-level mirror summary (DESIGN 4.10): ``{'status', 'suggested', 'undetermined',
    'g_pooled'}``; ``g_pooled`` = sum of the views' detectabilities g (WBS FU-04: the pooled
    evidence the set holds about left / right; reported, not a decision threshold).

    status is 'unverifiable' for an all-selfie set (asymmetry claims must be flagged, H7),
    'suggest_flip' when any view suggests a flip, 'undetermined' when no view could be
    tested (every view undetermined), else 'keep'.
    """
    sug = [k for k, d in enumerate(decisions) if d.decision == "suggest_flip"]
    und = [k for k, d in enumerate(decisions) if d.decision == "undetermined"]
    if all_views_front:
        status = "unverifiable"
    elif sug:
        status = "suggest_flip"
    elif decisions and len(und) == len(decisions):
        status = "undetermined"
    else:
        status = "keep"
    gs = [float(d.g) for d in decisions if np.isfinite(d.g)]
    return {"status": status, "suggested": sug, "undetermined": und, "g_pooled": float(sum(gs))}
