"""High-level landmark reconstruction: photos' 2D landmarks -> cameras + 3D landmarks."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .bundle import BundleResult, Priors, ViewObs, bundle_adjust
from .pnp import solve_pnp

# Landmark noise as a fraction of the visible-landmark bounding-box diagonal. Modern
# 68-point detectors reach ~3 % inter-ocular NME on 300-W (research/reconstruction/
# camera-pose-solving.md); inter-ocular distance is ~0.2 of the face-box diagonal,
# so 2.5 % IOD ~= 0.006 x diagonal.
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
    sigma_px: float | None = None     # None -> scaled from face size in the image

    def resolved_sigma_px(self) -> float:
        if self.sigma_px is not None:
            return float(self.sigma_px)
        vis = ~np.isnan(self.uv[:, 0])
        pts = self.uv[vis]
        diag = float(np.linalg.norm(pts.max(0) - pts.min(0))) if len(pts) >= 2 else 0.0
        return max(AUTO_SIGMA_FRACTION_OF_DIAG * diag, 0.5)


def reconstruct_landmarks(photos: list[PhotoLandmarks], priors: Priors, *,
                          huber_sigmas: float | None = 3.0, max_iter: int = 100) -> BundleResult:
    """Initialise each camera by PnP against the prior mean shape, then bundle-adjust
    all cameras, focal lengths and 3D landmarks jointly.

    huber_sigmas: robust threshold in units of each photo's landmark sigma, so it
    scales with how large the face is in the image.
    """
    if priors.mean is None:
        raise ValueError("priors.mean (template landmark positions) is required for initialisation")
    views = []
    for ph in photos:
        vis = ~np.isnan(ph.uv[:, 0])
        if vis.sum() < 6:
            raise ValueError("each photo needs at least 6 visible landmarks")
        s_px = ph.resolved_sigma_px()
        pnp = solve_pnp(priors.mean[vis], ph.uv[vis], ph.width, ph.height,
                        f_prior_px=ph.f_prior_px, f_prior_log_sigma=ph.f_prior_log_sigma,
                        estimate_focal=True,
                        weights=None if ph.weights is None else ph.weights[vis],
                        huber_px=None if huber_sigmas is None else huber_sigmas * s_px)
        views.append(ViewObs(uv=ph.uv, camera=pnp.camera, estimate_focal=True, f_prior=ph.f_prior_px,
                             f_prior_log_sigma=ph.f_prior_log_sigma, weights=ph.weights,
                             sigma_px=s_px, focal_group=ph.focal_group))
    return bundle_adjust(views, priors.mean.copy(), priors, huber_px=huber_sigmas, max_iter=max_iter)
