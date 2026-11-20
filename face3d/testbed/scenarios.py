"""Landmark-level test-bed scenarios and the per-seed scenario runner (DESIGN 7.2-7.3).

A :class:`Scenario` couples a subject generator, a rig protocol and detector-simulator
settings. :func:`run_scenario` draws, for each seed, a subject, a rig and detections
from three independent streams spawned from ``numpy.random.SeedSequence(seed)``
(subject, rig, detector), so scenarios that share a generator see the same subject and
rig for the same seed (common random numbers; validation-test-bed.md "compare settings
with common random numbers and paired tests").

Engine protocol
---------------
``engine_fn(obs, rig, names, template) -> result`` where ``result`` has ``X`` (N, 3 mm,
head frame), ``cameras`` (one :class:`~face3d.geometry.camera.Camera` per used view),
``rmse_px`` (per used view) and optionally ``view_index`` (rig view index of each used
view; default ``range(len(cameras))``), ``cov`` (3N, 3N mm^2, point-major) and/or
``point_sigma_mm`` (N, 3).

Metrics per seed (all floats; NaN when failed or unavailable)
------------------------------------------------------------
* ``config_rms_mm``   - RMS point distance after similarity alignment to the truth
  (configuration RMS; :func:`face3d.geometry.procrustes.procrustes_rmse`; rec EV-2).
* ``now7_rms_mm``     - RMS over all points after NoW-style rigid alignment on 7 landmarks
  (:func:`face3d.eval.align.align` mode ``'now7'``; rec EV-1).
* ``nees_per_dof``, ``coverage_1s``, ``coverage_2s`` - gauge-projected NEES/dof and per-axis
  1/2-sigma coverage (DESIGN 7.3): the estimate is similarity-aligned to the truth, its
  covariance (``result.cov`` if present, else diag(point_sigma_mm^2)) rotated and scaled
  with it, then both are projected off the similarity tangent at the truth.
* ``focal_rel_err``   - median over used views of |f_est / f_true - 1|.
* ``distance_rel_err`` - median over used views of |d_est / d_true - 1| with d the camera
  centre's distance to the head-frame origin, each in its own frame (the engine's template
  gauge vs the truth frame; both put the origin at the head centre).
* ``log_scale_err``   - log s(template -> estimate) - log s(template -> truth), with s the
  Umeyama similarity scale (signed; the truth's value is ``meta['log_scale_true']``).
* ``rmse_px``         - median over used views of the engine's reprojection RMSE.
* ``runtime_s``       - wall-clock seconds spent in ``engine_fn``.

Bookkeeping keys: ``seed`` (int), ``failed`` (bool), ``error`` (str, '' when ok).
:func:`run_scenario` never raises for a seed: any exception (PnP failure, singular
system, ...) gives ``failed=True`` with NaN metrics.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Sequence

import numpy as np

from ..eval.align import align
from ..eval.coverage import axis_coverage, nees
from ..geometry.procrustes import procrustes_rmse, umeyama
from ..solve.bundle import Priors
from ..solve.reconstruct import PhotoLandmarks, reconstruct_landmarks
from ..synthetic import midline_indices, mirror_pairs
from .detector_sim import Observation, legacy_kinds, simulate
from .rigs import MIN_VISIBLE, Rig, camera_roll, rear_phone, selfie, studio_ring
from .subjects import legacy_subject, log_scale_of, smooth_field_subject

__all__ = ["Scenario", "METRIC_KEYS", "SCENARIOS", "FAST_SCENARIOS", "LEGACY_PRIOR",
           "default_engine", "run_seed", "run_scenario"]

METRIC_KEYS: tuple[str, ...] = (
    "config_rms_mm", "now7_rms_mm", "nees_per_dof", "coverage_1s", "coverage_2s",
    "focal_rel_err", "distance_rel_err", "log_scale_err", "rmse_px", "runtime_s",
)

# Legacy prior settings of the committed baseline engine (git 41179a3; WBS WP-01):
# iid 8 mm landmark prior around the template, symmetry 2 mm, midline 1.5 mm
# (face3d.solve.bundle.Priors defaults).
LEGACY_PRIOR = {"sigma": 8.0, "sigma_sym": 2.0, "sigma_mid": 1.5}


@dataclass
class Scenario:
    """subject_fn(rng) -> (names, X_true, meta); rig_fn(rng, X=X_true) -> Rig;
    detector_kwargs are passed to :func:`face3d.testbed.detector_sim.simulate`."""

    name: str
    subject_fn: Callable[[np.random.Generator], tuple]
    rig_fn: Callable[..., Rig]
    detector_kwargs: dict = field(default_factory=dict)
    n_seeds: int = 30


def default_engine(obs: Observation, rig: Rig, names: Sequence[str], template: np.ndarray):
    """The legacy engine: :func:`face3d.solve.reconstruct_landmarks` with legacy ``Priors``.

    One :class:`PhotoLandmarks` per view with the rig's focal prior and focal group and
    ``sigma_px=None`` (the legacy auto sigma); views with fewer than 6 visible landmarks
    are dropped. The returned ``BundleResult`` gets a ``view_index`` attribute listing
    the rig views used.
    """
    names = list(names)
    photos, used = [], []
    for k, (uv, cam) in enumerate(zip(obs.uv, rig.cameras)):
        if int(np.sum(~np.isnan(uv[:, 0]))) < MIN_VISIBLE:
            continue
        photos.append(PhotoLandmarks(uv, cam.width, cam.height, f_prior_px=rig.f_prior_px[k],
                                     f_prior_log_sigma=rig.f_prior_log_sigma[k],
                                     focal_group=rig.focal_group[k], sigma_px=None))
        used.append(k)
    if not photos:
        raise ValueError("no view has >= %d visible landmarks" % MIN_VISIBLE)
    pri = Priors(mean=np.asarray(template, float), sigma=LEGACY_PRIOR["sigma"],
                 pairs=mirror_pairs(names), sigma_sym=LEGACY_PRIOR["sigma_sym"],
                 midline=midline_indices(names), sigma_mid=LEGACY_PRIOR["sigma_mid"])
    res = reconstruct_landmarks(photos, pri)
    res.view_index = used
    return res


def _nan_metrics() -> dict:
    return {k: float("nan") for k in METRIC_KEYS}


def _seed_streams(seed: int) -> tuple[np.random.Generator, np.random.Generator, np.random.Generator]:
    ss = np.random.SeedSequence(int(seed))
    a, b, c = ss.spawn(3)
    return np.random.default_rng(a), np.random.default_rng(b), np.random.default_rng(c)


def _result_cov(res, n: int) -> np.ndarray | None:
    cov = getattr(res, "cov", None)
    if cov is not None:
        cov = np.asarray(cov, float)
        if cov.shape == (3 * n, 3 * n):
            return cov
    ps = getattr(res, "point_sigma_mm", None)
    if ps is None:
        return None
    ps = np.asarray(ps, float)
    if ps.shape != (n, 3):
        return None
    return np.diag(ps.ravel() ** 2)


def _metrics(res, rig: Rig, names: list[str], X_true: np.ndarray, meta: dict) -> dict:
    m = _nan_metrics()
    X = np.asarray(res.X, float)
    n = len(X_true)
    if X.shape != X_true.shape or not np.isfinite(X).all():
        raise ValueError("engine returned a non-finite or mis-shaped landmark set")
    m["config_rms_mm"] = procrustes_rmse(X, X_true, with_scale=True)
    _, _, _, al7 = align(X, X_true, "now7", names=names)
    m["now7_rms_mm"] = float(np.sqrt(np.mean(np.sum((al7 - X_true) ** 2, axis=1))))

    cov = _result_cov(res, n)
    if cov is not None and np.isfinite(cov).all():
        s, R, t = umeyama(X, X_true, with_scale=True)
        err = s * X @ R.T + t - X_true
        B = np.kron(np.eye(n), R)
        cov_al = (s * s) * (B @ cov @ B.T)
        m["nees_per_dof"] = nees(err, cov_al, X_true, project=True)[0]
        cvg = axis_coverage(err, cov_al, X_true, ks=(1, 2), project=True)
        m["coverage_1s"], m["coverage_2s"] = cvg[1], cvg[2]

    used = list(getattr(res, "view_index", range(len(res.cameras))))
    fe, de = [], []
    for cam_est, k in zip(res.cameras, used):
        cam_true = rig.cameras[k]
        fe.append(abs(cam_est.f / cam_true.f - 1.0))
        de.append(abs(np.linalg.norm(cam_est.center) / np.linalg.norm(cam_true.center) - 1.0))
    if fe:
        m["focal_rel_err"] = float(np.median(fe))
        m["distance_rel_err"] = float(np.median(de))
    m["log_scale_err"] = log_scale_of(X, meta["template"]) - float(meta["log_scale_true"])
    rm = np.asarray(getattr(res, "rmse_px", []), float)
    if rm.size and np.isfinite(rm).any():
        m["rmse_px"] = float(np.nanmedian(rm))
    return m


def run_seed(scn: Scenario, seed: int, engine_fn=default_engine) -> dict:
    """One seed of a scenario; never raises (see module docstring)."""
    rec = {"seed": int(seed), "failed": False, "error": ""}
    rec.update(_nan_metrics())
    try:
        with np.errstate(all="ignore"):
            r_subj, r_rig, r_det = _seed_streams(seed)
            names, X_true, meta = scn.subject_fn(r_subj)
            names = list(names)
            rig = scn.rig_fn(r_rig, X=X_true)
            obs = simulate(X_true, legacy_kinds(names), rig, r_det, **scn.detector_kwargs)
            t0 = time.perf_counter()
            res = engine_fn(obs, rig, names, meta["template"])
            runtime = time.perf_counter() - t0
            rec.update(_metrics(res, rig, names, X_true, meta))
            rec["runtime_s"] = float(runtime)
    except Exception as exc:  # noqa: BLE001 - the runner must never raise (WBS WP-01)
        rec.update(_nan_metrics())
        rec["failed"] = True
        rec["error"] = "%s: %s" % (type(exc).__name__, exc)
    return rec


def run_scenario(scn: Scenario, seeds: Sequence[int], engine_fn=default_engine) -> list[dict]:
    """Run ``scn`` for every seed; one metrics dict per seed (see module docstring)."""
    return [run_seed(scn, s, engine_fn) for s in seeds]


# DESIGN 7.2 rigs x subjects x detector faults (WBS WP-01). Detector defaults: 5 %
# outliers, definition bias on, nominal noise (DESIGN 7.2).
SCENARIOS: dict[str, Scenario] = {s.name: s for s in [
    Scenario("studio_ring_legacy", legacy_subject, studio_ring, {}),
    Scenario("rear_phone_legacy", legacy_subject, rear_phone, {}),
    Scenario("selfie_legacy", legacy_subject, selfie, {}),
    Scenario("camera_roll_legacy", legacy_subject, camera_roll, {}),
    Scenario("rear_phone_smooth", smooth_field_subject, rear_phone, {}),
    Scenario("rear_phone_nobias", legacy_subject, rear_phone, {"definition_bias": False}),
    Scenario("rear_phone_outliers", legacy_subject, rear_phone, {"outlier_frac": 0.10}),
]}

# Fast mode (scorecard --fast): three legacy-subject scenarios spanning the rig range.
FAST_SCENARIOS: tuple[str, ...] = ("rear_phone_legacy", "studio_ring_legacy", "selfie_legacy")
