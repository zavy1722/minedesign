"""High-level landmark reconstruction: photos' 2D landmarks -> cameras + 3D landmarks."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..geometry.camera import Camera
from .bundle import BundleResult, Priors, ViewObs, bundle_adjust
from .pnp import solve_pnp


@dataclass
class PhotoLandmarks:
    uv: np.ndarray                    # (N,2) pixels, NaN where not visible/unknown
    width: int
    height: int
    f_prior_px: float | None = None   # e.g. from EXIF 35 mm-equivalent focal
    weights: np.ndarray | None = None
    sigma_px: float = 1.0


def reconstruct_landmarks(photos: list[PhotoLandmarks], priors: Priors, *,
                          huber_px: float | None = 3.0, max_iter: int = 100) -> BundleResult:
    """Initialise each camera by PnP against the prior mean shape, then bundle-adjust
    all cameras, focal lengths and 3D landmarks jointly."""
    if priors.mean is None:
        raise ValueError("priors.mean (template landmark positions) is required for initialisation")
    views = []
    for ph in photos:
        vis = ~np.isnan(ph.uv[:, 0])
        if vis.sum() < 6:
            raise ValueError("each photo needs at least 6 visible landmarks")
        pnp = solve_pnp(priors.mean[vis], ph.uv[vis], ph.width, ph.height,
                        f_prior_px=ph.f_prior_px, estimate_focal=True,
                        weights=None if ph.weights is None else ph.weights[vis], huber_px=huber_px)
        views.append(ViewObs(uv=ph.uv, camera=pnp.camera, estimate_focal=True, f_prior=ph.f_prior_px,
                             weights=ph.weights, sigma_px=ph.sigma_px))
    return bundle_adjust(views, priors.mean.copy(), priors, huber_px=huber_px, max_iter=max_iter)
