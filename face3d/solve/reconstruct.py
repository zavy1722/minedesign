"""High-level landmark reconstruction: photos' 2D landmarks -> cameras + 3D landmarks.

WP-07 changes (DESIGN 4.4, D-03, D-05, D-06):

* ``PhotoLandmarks.kinds`` (one kind per landmark, :data:`face3d.solve.noise.KINDS`) and
  ``PhotoLandmarks.focal_prior`` (a duck-typed object with ``f_px`` and ``log_sigma``,
  e.g. from the focal ladder of WP-06; it overrides ``f_prior_px`` /
  ``f_prior_log_sigma``).
* When ``PhotoLandmarks.sigma_px`` is None the bundle uses the noise model of the
  photo's ``kinds`` (or 'generic') in mm at each landmark's depth, instead of the
  legacy 0.006 x diagonal heuristic.  :meth:`PhotoLandmarks.resolved_sigma_px` is kept
  (legacy; it still sets the PnP initialisation's Huber threshold).
* ``reconstruct_landmarks`` passes ``prior``, ``scale``, ``gauge_anchor_idx`` and
  ``sigma_def_mm`` through to :func:`face3d.solve.bundle.bundle_adjust`.

Known limitation (follow-up, not WP-07 scope): ``PhotoLandmarks`` carries no image
tangents and nothing here derives t-hat from neighbouring curve points (DESIGN 4.4), so
every contour / brow / curve landmark enters with the unknown-tangent isotropic sigma
sqrt((sigma_n^2 + sigma_t^2) / 2): about 707 mm for contour and 28 mm for brow (in
effect discarded) and 5.4 mm instead of 1.5 mm normal precision for curve points.  A
``tangents`` field or scheme-curve-neighbour tangents (WP-11 contours / scheme work)
will let them enter with their normal-only sigma.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from .bundle import BundleResult, Priors, ScaleConfig, ViewObs, bundle_adjust
from .pnp import solve_pnp

# Landmark noise as a fraction of the visible-landmark bounding-box diagonal. Modern
# 68-point detectors reach ~3 % inter-ocular NME on 300-W (research/reconstruction/
# camera-pose-solving.md); inter-ocular distance is ~0.2 of the face-box diagonal,
# so 2.5 % IOD ~= 0.006 x diagonal.  Legacy: since WP-07 it only sets the PnP
# initialisation's robust threshold; the bundle uses the mm noise model (DESIGN 4.4).
AUTO_SIGMA_FRACTION_OF_DIAG = 0.006


@dataclass
class PhotoLandmarks:
    uv: np.ndarray                    # (N,2) pixels, NaN where not visible/unknown
    width: int
    height: int
    f_prior_px: float | None = None   # e.g. from EXIF 35 mm-equivalent focal
    f_prior_log_sigma: float = 0.35   # ~0.05 for trustworthy EXIF, 0.25-0.6 when guessed
    focal_group: str | int | None = None  # photos from the same camera+zoom share a focal
    weights: np.ndarray | None = None
    sigma_px: float | None = None     # None -> noise model of `kinds` in mm at depth (DESIGN 4.4)
    kinds: list[str] | None = None    # (N,) landmark kinds; None -> 'generic'
    focal_prior: Any = None           # object with f_px, log_sigma; overrides f_prior_px / f_prior_log_sigma

    def resolved_sigma_px(self) -> float:
        """Legacy isotropic sigma (px): ``sigma_px`` or 0.006 x the visible-landmark bbox diagonal (>= 0.5)."""
        if self.sigma_px is not None:
            return float(self.sigma_px)
        vis = ~np.isnan(self.uv[:, 0])
        pts = self.uv[vis]
        diag = float(np.linalg.norm(pts.max(0) - pts.min(0))) if len(pts) >= 2 else 0.0
        return max(AUTO_SIGMA_FRACTION_OF_DIAG * diag, 0.5)

    def resolved_focal_prior(self) -> tuple[float | None, float]:
        """(f_prior_px, f_prior_log_sigma), with ``focal_prior`` taking precedence."""
        fp = self.focal_prior
        if fp is not None:
            f = getattr(fp, "f_px", None)
            return (None if f is None else float(f)), float(getattr(fp, "log_sigma"))
        return self.f_prior_px, self.f_prior_log_sigma


def reconstruct_landmarks(photos: list[PhotoLandmarks], priors: Priors | None, *,
                          huber_sigmas: float | None = 3.0, max_iter: int = 100,
                          prior: Any = None, scale: ScaleConfig | str | None = "auto",
                          gauge_anchor_idx: Sequence[int] | None = None,
                          sigma_def_mm: np.ndarray | None = None) -> BundleResult:
    """Initialise each camera by PnP against the prior mean shape, then bundle-adjust
    all cameras, focal lengths, (optionally) the log-scale and 3D landmarks jointly.

    huber_sigmas: robust threshold in units of each observation's sigma, so it
    scales with how large the face is in the image.  ``prior``, ``scale``,
    ``gauge_anchor_idx`` and ``sigma_def_mm`` are passed to :func:`bundle_adjust`.
    The initial shape is ``priors.mean``, or ``prior.mean()`` when that covers all
    landmarks and ``priors`` has no mean.
    """
    N = len(photos[0].uv) if photos else 0
    if priors is not None and priors.mean is not None:
        X_init = np.asarray(priors.mean, float)
    elif prior is not None and hasattr(prior, "mean") and np.shape(prior.mean()) == (N, 3):
        X_init = np.asarray(prior.mean(), float)
    else:
        raise ValueError("priors.mean (template landmark positions) is required for initialisation")
    views = []
    for ph in photos:
        vis = ~np.isnan(ph.uv[:, 0])
        if vis.sum() < 6:
            raise ValueError("each photo needs at least 6 visible landmarks")
        s_px = ph.resolved_sigma_px()
        f_px, f_ls = ph.resolved_focal_prior()
        pnp = solve_pnp(X_init[vis], ph.uv[vis], ph.width, ph.height,
                        f_prior_px=f_px, f_prior_log_sigma=f_ls,
                        estimate_focal=True,
                        weights=None if ph.weights is None else ph.weights[vis],
                        huber_px=None if huber_sigmas is None else huber_sigmas * s_px)
        views.append(ViewObs(uv=ph.uv, camera=pnp.camera, estimate_focal=True, f_prior=f_px,
                             f_prior_log_sigma=f_ls, weights=ph.weights,
                             sigma_px=ph.sigma_px, focal_group=ph.focal_group, kinds=ph.kinds))
    return bundle_adjust(views, X_init.copy(), priors, huber_px=huber_sigmas, max_iter=max_iter,
                         prior=prior, scale=scale, gauge_anchor_idx=gauge_anchor_idx,
                         sigma_def_mm=sigma_def_mm)
