"""High-level landmark reconstruction: photos' 2D landmarks -> cameras + 3D landmarks.

WP-07 changes (DESIGN 4.4, D-03, D-05, D-06):

* ``PhotoLandmarks.kinds`` (one kind per landmark, :data:`face3d.solve.noise.KINDS`) and
  ``PhotoLandmarks.focal_prior`` (a duck-typed object with ``f_px`` and ``log_sigma``,
  e.g. from the focal ladder of WP-06; it overrides ``f_prior_px`` /
  ``f_prior_log_sigma``).
* When ``PhotoLandmarks.sigma_px`` is None the bundle uses the noise model of the
  photo's ``kinds`` (or 'generic') in mm at each landmark's depth, instead of the
  legacy 0.006 x diagonal heuristic.  :meth:`PhotoLandmarks.resolved_sigma_px` is kept
  (legacy).
* ``reconstruct_landmarks`` passes ``prior``, ``scale``, ``gauge_anchor_idx`` and
  ``sigma_def_mm`` through to :func:`face3d.solve.bundle.bundle_adjust`.

WP-10 changes (DESIGN 4.2, 4.3, 4.5, 4.8, 4.9):

* New keyword arguments passed to the bundle: ``robust``, ``view_weighting``,
  ``distance_priors`` (one ``(median_mm, sigma_log)`` or None per photo, e.g.
  :func:`face3d.solve.focal.distance_prior_head_origin`), ``jaw`` (a
  :class:`~face3d.solve.bundle.JawConfig` for every photo, or one per photo) with
  ``jaw_weights`` / ``jaw_center_mm``, ``terms``, ``landmark_normals`` and
  ``focal_tie_sigma`` (None: views of a focal group share one focal exactly, the legacy
  behaviour; the pipeline passes 0.02, rec CAM-5).
* PnP initialisation uses WP-06's multi-start :func:`~face3d.solve.pnp.solve_pnp` with
  per-landmark sigma_px from the noise model (``sigma_px`` when given, else the
  photo's ``kinds``) evaluated at one common depth: px_per_mm = f_prior / median
  distance when the photo has both a focal and a distance prior, else the ratio of the
  visible landmarks' image spread to the prior-mean shape's spread (an initialisation
  only, DESIGN 4.2: "IOD-based distance is used only to initialise"), and Huber delta = 2
  in sigma units (DESIGN 4.3).
* Views whose initial robust RMS (sqrt(median e^2 / 1.386) of the PnP fit, sigma units)
  exceeds 3 are re-initialised by PnP against the consensus after a first bundle pass
  over the other views (DESIGN 4.3 "later views are initialised against the BA consensus").
* Defaults stay legacy-compatible (exact focal sharing in a group, Huber IRLS, no
  distance priors).  On the WP-01 test bed (30 seeds) the soft tie can only lose: the
  simulator gives every view of a group the same focal, so exact sharing is the true model
  there; the tie is for real groups (crops, stabilisation; DESIGN 4.2).

FU-04 changes (DESIGN 4.4 "t-hat the image tangent from neighbouring curve points"):

* ``PhotoLandmarks.tangents`` ((N, 2) exact image tangents of any length, or (N, 3)
  (t_x, t_y, rho) with the direction confidence of a detection-derived tangent,
  :mod:`face3d.solve.noise`; NaN / zero rows unknown) is passed
  to ``ViewObs.tangents``, so that curve / contour / extremal landmarks enter with sigma_n across
  and sigma_t along their curve instead of the unknown-tangent isotropic sigma (curve points:
  1.5 mm normal precision instead of 5.4 mm isotropic; extremal: 2.0 / 3.0 instead of 3.0).
* :func:`photo_tangents` derives them from the photo's *own detections* and a scheme's
  neighbour metadata (:func:`face3d.solve.noise.scheme_tangent_pairs` /
  :func:`~face3d.solve.noise.image_tangents`); nothing here ever reads a simulator's ground
  truth.  ``tangents=None`` (the default) keeps the pre-FU-04 behaviour exactly.
* Points without a usable tangent keep the FU-01 rule (isotropic at max(sigma_n, sigma_t), or
  the orientation average for the free-tangent kinds).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Sequence

import numpy as np

from ..core.config import Default, register_defaults
from .bundle import BundleResult, JawConfig, Priors, ScaleConfig, ViewObs, bundle_adjust
from .noise import NoiseModel
from .pnp import PNP_DEFAULTS, solve_pnp
from .robust import CHI2_2_MEDIAN, RobustSchedule

# Landmark noise as a fraction of the visible-landmark bounding-box diagonal. Modern
# 68-point detectors reach ~3 % inter-ocular NME on 300-W (research/reconstruction/
# camera-pose-solving.md); inter-ocular distance is ~0.2 of the face-box diagonal,
# so 2.5 % IOD ~= 0.006 x diagonal.  Legacy: kept for resolved_sigma_px(); since WP-10
# neither the PnP initialisation nor the bundle uses it (DESIGN 4.4).
AUTO_SIGMA_FRACTION_OF_DIAG = 0.006

RECONSTRUCT = register_defaults("reconstruct", {
    "reinit_rms_sigmas": Default(3.0, "\U0001F195", "WBS WP-10: re-initialise a view by PnP against the "
                                 "consensus when its initial robust RMS exceeds 3 sigma (DESIGN 4.3)", "sigma",
                                 (0.0, None)),
})
#: Re-initialise a view by PnP against the consensus when its initial robust RMS exceeds
#: this many sigma (WBS WP-10, 🆕 provisional; registered default ``reconstruct.reinit_rms_sigmas``).
REINIT_RMS_SIGMAS = float(RECONSTRUCT["reinit_rms_sigmas"].value)


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
    # (N,3) image tangents (t_x, t_y, rho) from the photo's own detections, or (N,2) exact directions (photo_tangents / noise.image_tangents);
    # None -> every tangent unknown (isotropic fallback, WBS FU-01).  Ignored with an explicit sigma_px.
    tangents: np.ndarray | None = None

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


def _per_photo(value: Any, n: int, name: str, kind: type | tuple = ()) -> list:
    """Broadcast a per-photo option: None -> [None]*n, a single instance -> [value]*n, a list -> checked."""
    if value is None:
        return [None] * n
    if kind and isinstance(value, kind):
        return [value] * n
    vals = list(value)
    if len(vals) != n:
        raise ValueError(f"{name} must have one entry per photo ({n}), got {len(vals)}")
    return vals


def pnp_sigma_px(ph: PhotoLandmarks, X_ref: np.ndarray, vis: np.ndarray, f_px: float | None,
                 distance_prior: tuple[float, float] | None) -> np.ndarray | float:
    """Per-landmark PnP sigma (px) of the visible landmarks of ``ph`` (WBS WP-10).

    ``ph.sigma_px`` when given (legacy float); otherwise the noise model of ``ph.kinds``
    (DESIGN 4.4) at one common px_per_mm: f_px / median distance with a focal and a
    distance prior, else rms-spread(image) / (sqrt(2/3) rms-spread(X_ref)) of the visible
    landmarks (an orthographic size ratio; initialisation only).  Returns the isotropic
    equivalent sqrt(trace(Sigma) / 2) per visible landmark.
    """
    if ph.sigma_px is not None:
        return float(ph.sigma_px)
    uv = np.asarray(ph.uv, float)[vis]
    Xv = np.asarray(X_ref, float)[vis]
    if f_px is not None and distance_prior is not None:
        ppm = float(f_px) / float(distance_prior[0])
    else:
        s_img = float(np.sqrt(np.mean(np.sum((uv - uv.mean(0)) ** 2, axis=1))))
        s_mm = float(np.sqrt(np.mean(np.sum((Xv - Xv.mean(0)) ** 2, axis=1)))) * np.sqrt(2.0 / 3.0)
        ppm = s_img / max(s_mm, 1e-9)
    N = len(ph.uv)
    kinds = ph.kinds if ph.kinds is not None else ["generic"] * N
    face = float(np.ptp(uv[:, 0])) if len(uv) >= 2 else None
    C = NoiseModel(kinds).view_cov(np.full(N, ppm), face, tangents=ph.tangents)[vis]
    return np.sqrt(0.5 * (C[:, 0, 0] + C[:, 1, 1]))


def photo_tangents(uv: Any, kinds: Sequence[str | None] | None, pairs: Any, X_ref: np.ndarray | None = None,
                   px_per_mm: float | None = None, weights: Any = None) -> np.ndarray:
    """(N, 3) image tangents (t_x, t_y, rho) of one photo from its own detections (WBS FU-04 task 1).

    ``uv`` (N, 2) px (NaN rows hidden); ``kinds`` (N,) landmark kinds (None: 'generic');
    ``pairs`` (N, 2) neighbour indices from the scheme (:func:`face3d.solve.noise.scheme_tangent_pairs`).
    The direction confidence of each chord uses the neighbours' declared isotropic-equivalent
    noise in px at ``px_per_mm`` (px per mm; None: the orthographic size ratio of the visible
    landmarks to ``X_ref`` (N, 3) mm, as in :func:`pnp_sigma_px`; with neither, the directions
    are taken as exact), divided by sqrt(``weights``) where information weights are given (a
    down-weighted neighbour gives a less certain direction).  Returns
    :func:`face3d.solve.noise.image_tangents`: NaN rows where no usable tangent exists.
    """
    from .noise import image_tangents
    U = np.asarray(uv, float)
    N = len(U)
    vis = np.isfinite(U).all(axis=1)
    ppm = px_per_mm
    if ppm is None and X_ref is not None and vis.sum() >= 2:
        Xv = np.asarray(X_ref, float)[vis]
        s_img = float(np.sqrt(np.mean(np.sum((U[vis] - U[vis].mean(0)) ** 2, axis=1))))
        s_mm = float(np.sqrt(np.mean(np.sum((Xv - Xv.mean(0)) ** 2, axis=1)))) * np.sqrt(2.0 / 3.0)
        ppm = s_img / max(s_mm, 1e-9)
    sig = None
    if ppm is not None and np.isfinite(ppm) and ppm > 0:
        kk = list(kinds) if kinds is not None else ["generic"] * N
        face = float(np.ptp(U[vis, 0])) if vis.sum() >= 2 else None
        C = NoiseModel(kk).view_cov(np.full(N, float(ppm)), face)
        sig = np.sqrt(0.5 * (C[:, 0, 0] + C[:, 1, 1]))
        if weights is not None:
            w = np.asarray(weights, float).reshape(-1)
            ok = np.isfinite(w) & (w > 0)
            sig = np.where(ok, sig / np.sqrt(np.where(ok, w, 1.0)), np.inf)
    return image_tangents(U, pairs, sig)


def _robust_rms_sigmas(res_px: np.ndarray, sigma: np.ndarray | float) -> float:
    """sqrt(median(e^2) / 1.386) of the PnP residuals in sigma units (1 for a correct noise model)."""
    e = np.asarray(res_px, float) / np.asarray(sigma, float)
    return float(np.sqrt(np.median(e * e) / CHI2_2_MEDIAN)) if e.size else float("nan")


def reconstruct_landmarks(photos: list[PhotoLandmarks], priors: Priors | None, *,
                          huber_sigmas: float | None = 3.0, max_iter: int = 100,
                          prior: Any = None, scale: ScaleConfig | str | None = "auto",
                          gauge_anchor_idx: Sequence[int] | None = None,
                          sigma_def_mm: np.ndarray | None = None,
                          robust: RobustSchedule | None = None, view_weighting: bool = False,
                          distance_priors: Sequence[tuple[float, float] | None] | None = None,
                          jaw: JawConfig | Sequence[JawConfig | None] | None = None,
                          jaw_weights: np.ndarray | None = None, jaw_center_mm: Sequence[float] | None = None,
                          terms: Sequence[Any] | None = None, landmark_normals: np.ndarray | None = None,
                          focal_tie_sigma: float | None = None,
                          reinit_rms_sigmas: float | None = REINIT_RMS_SIGMAS) -> BundleResult:
    """Initialise each camera by PnP against the prior mean shape, then bundle-adjust
    all cameras, focal lengths, (optionally) the log-scale and 3D landmarks jointly.

    huber_sigmas: robust threshold of the legacy bundle IRLS in units of each
    observation's sigma (``None``: plain least squares, also in PnP).  ``prior``,
    ``scale``, ``gauge_anchor_idx``, ``sigma_def_mm``, ``robust``, ``view_weighting``,
    ``landmark_normals``, ``jaw_weights``, ``jaw_center_mm`` and ``terms`` are passed to
    :func:`bundle_adjust`; ``distance_priors``, ``jaw`` and ``focal_tie_sigma`` fill the
    per-photo :class:`ViewObs` fields.  ``reinit_rms_sigmas=None`` disables the PnP
    re-initialisation against the consensus.  The initial shape is ``priors.mean``, or
    ``prior.mean()`` when that covers all landmarks and ``priors`` has no mean.
    """
    N = len(photos[0].uv) if photos else 0
    if priors is not None and priors.mean is not None:
        X_init = np.asarray(priors.mean, float)
    elif prior is not None and hasattr(prior, "mean") and np.shape(prior.mean()) == (N, 3):
        X_init = np.asarray(prior.mean(), float)
    else:
        raise ValueError("priors.mean (template landmark positions) is required for initialisation")
    n = len(photos)
    dps = _per_photo(distance_priors, n, "distance_priors")
    jaws = _per_photo(jaw, n, "jaw", JawConfig)
    pnp_huber = None if huber_sigmas is None else float(PNP_DEFAULTS.huber_sigmas.value)

    def pnp(ph: PhotoLandmarks, X_ref: np.ndarray, dp):
        vis = ~np.isnan(ph.uv[:, 0])
        f_px, f_ls = ph.resolved_focal_prior()
        sig = pnp_sigma_px(ph, X_ref, vis, f_px, dp)
        r = solve_pnp(X_ref[vis], ph.uv[vis], ph.width, ph.height, f_prior_px=f_px, f_prior_log_sigma=f_ls,
                      estimate_focal=True, weights=None if ph.weights is None else ph.weights[vis],
                      sigma_px=sig, huber_sigmas=pnp_huber)
        return r, _robust_rms_sigmas(r.residuals_px, sig)

    views, bad = [], []
    for k, ph in enumerate(photos):
        vis = ~np.isnan(ph.uv[:, 0])
        if vis.sum() < 6:
            raise ValueError("each photo needs at least 6 visible landmarks")
        f_px, f_ls = ph.resolved_focal_prior()
        r, rms = pnp(ph, X_init, dps[k])
        if reinit_rms_sigmas is not None and np.isfinite(rms) and rms > reinit_rms_sigmas:
            bad.append(k)
        views.append(ViewObs(uv=ph.uv, camera=r.camera, estimate_focal=True, f_prior=f_px,
                             f_prior_log_sigma=f_ls, weights=ph.weights,
                             sigma_px=ph.sigma_px, focal_group=ph.focal_group, kinds=ph.kinds,
                             tangents=ph.tangents,
                             focal_tie_sigma=focal_tie_sigma, distance_prior=dps[k],
                             jaw=jaws[k] if jaws[k] is not None else JawConfig()))
    kw = dict(huber_px=huber_sigmas, max_iter=max_iter, prior=prior, scale=scale,
              gauge_anchor_idx=gauge_anchor_idx, sigma_def_mm=sigma_def_mm, robust=robust,
              view_weighting=view_weighting, landmark_normals=landmark_normals, jaw_weights=jaw_weights,
              jaw_center_mm=jaw_center_mm, terms=terms)
    good = [k for k in range(n) if k not in bad]
    if bad and good:
        # consensus from the well-initialised views (terms may index views: left out here)
        first = bundle_adjust([views[k] for k in good], X_init.copy(), priors, **{**kw, "terms": None})
        for k in bad:
            r, _ = pnp(photos[k], first.X, dps[k])
            views[k] = replace(views[k], camera=r.camera)
    return bundle_adjust(views, X_init.copy(), priors, **kw)


# photo_tangents (WBS FU-04) is public but not in __all__: the face3d.solve export list is owned by WP-23.
__all__ = ["PhotoLandmarks", "reconstruct_landmarks", "pnp_sigma_px", "AUTO_SIGMA_FRACTION_OF_DIAG",
           "REINIT_RMS_SIGMAS", "RECONSTRUCT"]
