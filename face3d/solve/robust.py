"""Robust schedule for the landmark bundle: IRLS weights, per-view noise scale and chi^2 bounds.

DESIGN D-07, D-08 and 4.5 (WBS WP-10).  With e_i = ||Sigma_iv^-1/2 r_iv|| the whitened
*radial* residual of landmark i in view v (a 2-vector, so e_i^2 ~ chi^2 with 2 dof under
the noise model), :func:`face3d.solve.bundle.bundle_adjust` with
``robust=RobustSchedule()`` runs, re-freezing the noise before every round:

1. ``huber_rounds`` (2) IRLS rounds with Huber weights w = min(1, delta / e), delta = 2;
2. ``tukey_rounds`` (1) round with Tukey's biweight w = (1 - (e / c)^2)^2 for e < c,
   else 0, c = 4.685;
3. rejection of every observation with e > ``reject_k`` = 3.035 and a final plain
   least-squares solve on the inliers;
4. before each round the per-view robust noise scale
   nu_v^2 = clip(median_i e_i^2 / 1.386, 1, 9) multiplies the view's noise covariance
   (e_i over the detector part of the noise; 1.386 = 2 ln 2, the median of chi^2_2);
5. view test: chi^2_v = sum of e_i^2 over the view's inliers with dof_v = 2 n_v - 7; the
   view is rejected (finding ``F-VIEW-REJECT``) when chi^2_v exceeds the
   ``view_chi2_q`` = 0.99 Wilson-Hilferty quantile; a view is flagged ``F-VIEW-NOISY``
   when nu_v > 2 and ``F-VIEW-OUTLIERS`` when more than 15 % of its points are rejected.

Numeric defaults (registered under the ``robust`` namespace of
:mod:`face3d.core.config`, all PROVISIONAL until the fault-matrix tuning of DESIGN 7.4):

* Huber delta 2 sigma: DESIGN D-08 / 4.5, research/reconstruction/README.md row C6
  ("Default delta = 2 sigma") 🧠.
* Tukey c = 4.685 sigma: 95 % Gaussian efficiency, research note deformation-fitting-math
  [27] (robustbase psi-function vignette) 📄.
* Rejection at 3.035 sigma = sqrt(-2 ln 0.01), the 1 % point of the radial residual of a
  2D standard normal (P(e > k) = exp(-k^2 / 2)); DESIGN D-08 "1 % false alarm in 2D" 🔢,
  validation-test-bed "Gates from quantiles" (3.03 sigma).
* View chi^2 quantile 0.99 and the 15 % outlier flag: DESIGN D-08 / 4.5,
  research/reconstruction/README.md "Engine robust defaults" 🧠.
* nu clip [1, 9] on nu^2 and the flag nu > 2: DESIGN D-07 ([Rob 3.2]) 🆕.

Statistics helpers: :func:`norm_ppf` (Acklam's rational approximation refined by one
Halley step on ``math.erfc``; |error| < 1e-9), :func:`chi2_quantile_wh` (Wilson-Hilferty,
DESIGN 4.5: q(z) = h (1 - 2/(9h) + z sqrt(2/(9h)))^3) and :func:`view_chi2_test`.
numpy + stdlib only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..core.config import Default, register_defaults

__all__ = ["ROBUST", "CHI2_2_MEDIAN", "RobustSchedule", "huber_weights", "tukey_weights", "nu2_view",
           "norm_ppf", "chi2_quantile_wh", "view_chi2_test"]

_BRAIN = "\U0001F9E0"   # expert knowledge, provisional
_PAGE = "\U0001F4C4"    # single cited source
_NEW = "\U0001F195"     # introduced by this design, uncalibrated
_NUM = "\U0001F522"     # checked numerically

#: Median of the chi-square distribution with 2 degrees of freedom: 2 ln 2 = 1.3863 (DESIGN D-07 🔢).
CHI2_2_MEDIAN = 2.0 * math.log(2.0)

ROBUST = register_defaults("robust", {
    "huber_delta": Default(2.0, _BRAIN, "DESIGN D-08 / 4.5: Huber delta = 2 sigma (research/reconstruction "
                           "README C6)", "sigma", (1e-6, None)),
    "huber_rounds": Default(2, _BRAIN, "DESIGN 4.5 step 1: two Huber IRLS rounds", "rounds", (0, 100)),
    "tukey_c": Default(4.685, _PAGE, "DESIGN D-08 / 4.5: Tukey c 4.685 (95 % efficiency; deformation-fitting-math "
                       "[27] robustbase vignette)", "sigma", (1e-6, None)),
    "tukey_rounds": Default(1, _BRAIN, "DESIGN 4.5 step 2: one Tukey round", "rounds", (0, 100)),
    "reject_k": Default(3.035, _NUM, "DESIGN D-08 / 4.5: reject e > 3.035 = sqrt(-2 ln 0.01), 1 % false alarm "
                        "in 2D (validation-test-bed 'Gates from quantiles')", "sigma", (1e-6, None)),
    "view_chi2_q": Default(0.99, _BRAIN, "DESIGN D-08 / 4.5 step 5: reject a view above its 99 % chi^2 bound",
                           "", (0.5, 1.0 - 1e-12)),
    "view_reject_frac_flag": Default(0.15, _BRAIN, "DESIGN D-08 / 4.5: flag a view with > 15 % of its points "
                                     "rejected (research/reconstruction README 'Engine robust defaults')",
                                     "", (0.0, 1.0)),
    "nu2_min": Default(1.0, _NEW, "DESIGN D-07 / 4.5 step 4: nu_v^2 = clip(median e^2 / 1.386, 1, 9) "
                       "([Rob 3.2])", "", (1e-6, None)),
    "nu2_max": Default(9.0, _NEW, "DESIGN D-07 / 4.5 step 4: nu_v^2 clipped at 9 ([Rob 3.2])", "", (1e-6, None)),
    "nu_flag": Default(2.0, _NEW, "DESIGN D-07: flag nu_v > 2 (F-VIEW-NOISY)", "", (0.0, None)),
})


@dataclass
class RobustSchedule:
    """Settings of the robust schedule of DESIGN 4.5 (see the module docstring).

    ``huber_delta``, ``tukey_c`` and ``reject_k`` are in units of the whitened radial
    residual e (sigma units); ``nu_clip`` bounds nu_v^2 (not nu_v); ``nu_flag`` bounds
    nu_v; ``view_reject_frac_flag`` is a fraction of the view's considered points.
    """

    huber_delta: float = float(ROBUST["huber_delta"].value)
    huber_rounds: int = int(ROBUST["huber_rounds"].value)
    tukey_c: float = float(ROBUST["tukey_c"].value)
    tukey_rounds: int = int(ROBUST["tukey_rounds"].value)
    reject_k: float = float(ROBUST["reject_k"].value)
    view_chi2_q: float = float(ROBUST["view_chi2_q"].value)
    view_reject_frac_flag: float = float(ROBUST["view_reject_frac_flag"].value)
    nu_clip: tuple[float, float] = (float(ROBUST["nu2_min"].value), float(ROBUST["nu2_max"].value))
    nu_flag: float = float(ROBUST["nu_flag"].value)

    def validate(self) -> "RobustSchedule":
        """Raise ``ValueError`` on an unusable setting; returns self."""
        if not (self.huber_delta > 0 and self.tukey_c > 0 and self.reject_k > 0):
            raise ValueError("RobustSchedule: huber_delta, tukey_c and reject_k must be > 0")
        if int(self.huber_rounds) < 0 or int(self.tukey_rounds) < 0:
            raise ValueError("RobustSchedule: round counts must be >= 0")
        if not 0.5 <= self.view_chi2_q < 1.0:
            raise ValueError("RobustSchedule: view_chi2_q must lie in [0.5, 1)")
        lo, hi = (float(v) for v in self.nu_clip)
        if not (0 < lo <= hi):
            raise ValueError("RobustSchedule: nu_clip must satisfy 0 < lo <= hi")
        return self


def huber_weights(e: Any, delta: float) -> np.ndarray:
    """Huber IRLS weights min(1, delta / e) for whitened residual norms e >= 0 (DESIGN 4.5 step 1)."""
    e = np.abs(np.asarray(e, float))
    return np.where(e <= delta, 1.0, delta / np.maximum(e, 1e-300))


def tukey_weights(e: Any, c: float) -> np.ndarray:
    """Tukey biweight IRLS weights (1 - (e/c)^2)^2 for e < c, else 0 (DESIGN 4.5 step 2)."""
    e = np.abs(np.asarray(e, float))
    u = e / float(c)
    return np.where(u < 1.0, (1.0 - u * u) ** 2, 0.0)


def nu2_view(e2: Any, clip: tuple[float, float] = (1.0, 9.0)) -> float:
    """Robust per-view noise scale nu_v^2 = clip(median(e2) / 1.386, lo, hi) (DESIGN D-07, 4.5 step 4).

    ``e2`` are squared whitened radial residuals; 1.386 = 2 ln 2 is the median of chi^2_2,
    so nu^2 = 1 when the noise model is right.  Returns ``clip[0]`` for an empty input.
    """
    a = np.asarray(e2, float).reshape(-1)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return float(clip[0])
    return float(np.clip(np.median(a) / CHI2_2_MEDIAN, clip[0], clip[1]))


# Acklam's rational approximation of the standard normal quantile (relative error < 1.15e-9
# before refinement); coefficients from P. J. Acklam, "An algorithm for computing the inverse
# normal cumulative distribution function" (2003).
_A = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
      1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
_B = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
      6.680131188771972e+01, -1.328068155288572e+01)
_C = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
      -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
_D = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00)
_P_LOW = 0.02425


def _acklam(p: float) -> float:
    if p < _P_LOW:
        q = math.sqrt(-2.0 * math.log(p))
        return ((((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5])
                / ((((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0))
    if p > 1.0 - _P_LOW:
        q = math.sqrt(-2.0 * math.log1p(-p))
        return -((((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5])
                 / ((((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0))
    q = p - 0.5
    r = q * q
    return ((((((_A[0] * r + _A[1]) * r + _A[2]) * r + _A[3]) * r + _A[4]) * r + _A[5]) * q
            / (((((_B[0] * r + _B[1]) * r + _B[2]) * r + _B[3]) * r + _B[4]) * r + 1.0))


def norm_ppf(p: float) -> float:
    """Standard normal quantile Phi^-1(p) for 0 < p < 1 (|error| < 1e-9).

    Acklam's rational approximation followed by one Halley step on
    Phi(x) = erfc(-x / sqrt 2) / 2 (stdlib ``math.erfc``).  ``ValueError`` outside (0, 1).
    """
    p = float(p)
    if not 0.0 < p < 1.0:
        raise ValueError(f"norm_ppf needs 0 < p < 1, got {p!r}")
    x = _acklam(p)
    e = 0.5 * math.erfc(-x / math.sqrt(2.0)) - p
    u = e * math.sqrt(2.0 * math.pi) * math.exp(0.5 * x * x)
    return x - u / (1.0 + 0.5 * x * u)


def chi2_quantile_wh(dof: float, q: float) -> float:
    """Wilson-Hilferty approximation of the q-quantile of chi^2 with ``dof`` degrees of freedom.

    q(z) = h (1 - 2/(9h) + z sqrt(2/(9h)))^3 with h = dof and z = Phi^-1(q) (DESIGN 4.5).
    ``ValueError`` for dof <= 0.
    """
    h = float(dof)
    if not h > 0:
        raise ValueError(f"chi2_quantile_wh needs dof > 0, got {dof!r}")
    z = norm_ppf(q)
    a = 2.0 / (9.0 * h)
    return h * max(1.0 - a + z * math.sqrt(a), 0.0) ** 3


def view_chi2_test(e2_inliers: Any, dof: float, q: float = 0.99) -> tuple[float, float, bool]:
    """View test of DESIGN 4.5 step 5: ``(chi2, threshold, reject)``.

    chi2 = sum of the squared whitened residuals ``e2_inliers`` over the view's inliers,
    threshold = :func:`chi2_quantile_wh` (dof, q), reject = chi2 > threshold.  With
    dof <= 0 the view cannot be tested: ``(chi2, inf, False)``.
    """
    chi2 = float(np.sum(np.asarray(e2_inliers, float)))
    if not dof > 0:
        return chi2, float("inf"), False
    thr = chi2_quantile_wh(dof, q)
    return chi2, thr, bool(chi2 > thr)
