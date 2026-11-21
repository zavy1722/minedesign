"""WP-10: bundle v2 (DESIGN D-01, D-02, D-07, D-08, 4.3, 4.5, 4.8, 4.9).

Inverse-depth camera blocks (FREE / HARD / FIXED_F) with soft focal ties, distance and
pose-tag priors, visibility weights, view weights with the 40 % cap, the jaw hinge, the
robust schedule (robust.py), the Term / ShapeModel protocols (terms.py), the Schur step
and the reconstruct_landmarks extensions.
"""
import math
import time

import numpy as np
import pytest

import face3d.solve.bundle as B
import face3d.solve.reconstruct as Rc
from face3d.geometry.camera import Camera
from face3d.geometry.procrustes import procrustes_rmse, umeyama
from face3d.model.landmark_prior import FactorPrior
from face3d.model.registry import ANATOMICAL
from face3d.solve import robust as R
from face3d.solve.bundle import (ENGINE_VERSION, JawConfig, Priors, ScaleConfig, ViewObs, bundle_adjust,
                                 dense_step, jaw_hinge, schur_step)
from face3d.solve.noise import NoiseModel
from face3d.solve.reconstruct import PhotoLandmarks, reconstruct_landmarks
from face3d.solve.robust import RobustSchedule
from face3d.solve.terms import FreePoints, ShapeModel, SolverState, Term
from face3d.synthetic import midline_indices, mirror_pairs, orbit_camera, random_subject, synthetic_landmarks
from face3d.testbed import detector_sim, rigs, subjects
from face3d.testbed.scenarios import LEGACY_PRIOR, _seed_streams

NAMES, TEMPLATE = synthetic_landmarks()
N = len(TEMPLATE)
IDX = {n: i for i, n in enumerate(NAMES)}
# DESIGN 4.9 hinge weights on the legacy names (me, pg, li 1.0; sto 0.5; ch 0.4; go 1.0)
JAW_W = np.zeros(N)
for _n, _w in (("menton", 1.0), ("pogonion", 1.0), ("labrale_inferius", 1.0), ("stomion", 0.5),
               ("cheilion_L", 0.4), ("cheilion_R", 0.4), ("gonion_L", 1.0), ("gonion_R", 1.0)):
    JAW_W[IDX[_n]] = _w
# legacy template origin is the head centre; mid-tragion is (0, 15, -5) mm: c = mid-tragion + (0, -5, 11.5)
JAW_C = np.array([0.0, 10.0, 6.5])


def _priors(template=TEMPLATE, names=NAMES, sigma=8.0, sigma_sym=3.0, sigma_mid=2.0):
    return Priors(mean=template, sigma=sigma, pairs=mirror_pairs(list(names)), sigma_sym=sigma_sym,
                  midline=midline_indices(list(names)), sigma_mid=sigma_mid)


def _normals(X):
    """Outward unit normals of the legacy head proxy (radial from the head centre)."""
    return X / np.linalg.norm(X, axis=1, keepdims=True)


def _capture(monkeypatch, *args, **kwargs):
    """Run bundle_adjust with a zero-iteration LM shim; return the closures of the last LM call."""
    cap = {}
    orig = B.levenberg_marquardt

    def shim(fun, x0, jac=None, retract=None, **kw):
        cap.update(fun=fun, jac=jac, retract=retract, x0=x0, kw=kw)
        return orig(fun, x0, jac=jac, retract=retract, max_iter=0)
    monkeypatch.setattr(B, "levenberg_marquardt", shim)
    res = B.bundle_adjust(*args, **kwargs)
    return cap, res


def _numeric_jacobian(fun, retract, x0, h=1e-3):
    """Central differences through ``retract`` with one Richardson step (O(h^4))."""
    def central(hh):
        r0 = fun(x0)
        Jn = np.zeros((len(r0), len(x0)))
        for j in range(len(x0)):
            e = np.zeros(len(x0))
            e[j] = hh
            Jn[:, j] = (fun(retract(x0, e)) - fun(retract(x0, -e))) / (2 * hh)
        return Jn
    return (4.0 * central(h / 2) - central(h)) / 3.0


_FINE = ("omega_", "tau_", "rho_", "a_", "phi_", "jaw_", "zeta", "points", "term:")


def _close(Ja, Jn, param_index, rtol=1e-4, atol_rel=1e-6, floor_rel=1e-9):
    """|Ja - Jn| <= rtol |Jn| + atol_rel * max|Jn| over (row, finest parameter block)
    + floor_rel * max|Jn| over the row (finite-difference round-off on analytically ~0 entries)."""
    A = np.abs(Jn)
    scale = np.zeros_like(A)
    for name, sl in param_index.items():
        if name.startswith(_FINE) and sl.stop > sl.start:
            scale[:, sl] = A[:, sl].max(axis=1, keepdims=True)
    return np.abs(Ja - Jn) <= rtol * A + atol_rel * scale + floor_rel * A.max(axis=1, keepdims=True)


def _assert_close(Ja, Jn, idx):
    ok = _close(Ja, Jn, idx)
    if not ok.all():
        i, j = np.unravel_index(np.argmin(ok), ok.shape)
        raise AssertionError(f"{int((~ok).sum())} entries differ, e.g. [{i}, {j}]: {Ja[i, j]!r} vs {Jn[i, j]!r}")


def _detected(Ja, Jn, idx, cols, factor=1.001):
    Jm = Ja.copy()
    Jm[:, cols] *= factor
    return not _close(Jm, Jn, idx).all()


def _rich_scene(rng, X_true, dist=520.0):
    """Six views covering every camera block kind, noise path and camera prior."""
    yaws = (-50, -20, 0, 15, 35, 60)
    cams = [orbit_camera(dist + 40 * k, y, rng.uniform(-8, 8), 26.0) for k, y in enumerate(yaws)]
    kinds = list(rng.choice(["sharp_junction", "extremal", "curve", "generic", "contour"], size=N))
    views = []
    for k, c in enumerate(cams):
        uv = c.project(X_true) + rng.normal(scale=1.5, size=(N, 2))
        uv[~rigs.visible_mask(c, X_true)] = np.nan
        c0 = c.copy()
        c0.t = c0.t + rng.normal(scale=2.0, size=3)
        c0.R = c0.R @ B.rodrigues(rng.normal(scale=0.01, size=3))
        kw = dict(kinds=kinds)
        if k == 0:     # FREE ungrouped: focal prior on a - ln rho, distance prior, pose tag, jaw
            C = c.center
            kw.update(f_prior=c.f * 1.05, sigma_px=1.5, distance_prior=(float(np.linalg.norm(C)) * 1.1, 0.3),
                      pose_tag=(math.degrees(math.atan2(C[0], C[2])) + 3.0, 2.0, 10.0, 5.0),
                      jaw=JawConfig(enabled=True))
        elif k == 1:   # FIXED_F, noise model, jaw
            kw.update(estimate_focal=False, jaw=JawConfig(enabled=True, prior_sigma_deg=3.0))
        elif k in (2, 3):   # soft-tied focal group: FREE blocks + phi
            kw.update(focal_group="soft", focal_tie_sigma=0.02, f_prior=c.f * 0.97, f_prior_log_sigma=0.1)
            if k == 3:
                kw.update(jaw=JawConfig(enabled=True), distance_prior=(700.0, 0.4))
        else:          # hard group: HARD blocks + phi; one view with an explicit covariance
            kw.update(focal_group="hard", f_prior=c.f * 1.02, f_prior_log_sigma=0.2)
            if k == 5:
                A = rng.normal(size=(N, 2, 2))
                kw.update(cov_px=np.einsum("nij,nkj->nik", A, A) + np.eye(2), pose_tag=(55.0, -3.0, 5.0, 5.0))
        views.append(ViewObs(uv, c0, **kw))
    return views, cams


# ------------------------------------------------------------------ robust.py
def test_robust_helpers():
    for p, x in ((0.975, 1.959963984540054), (0.99, 2.3263478740408408), (0.5, 0.0), (1e-6, -4.753424308822899),
                 (0.02, -2.053748910631823), (0.999, 3.090232306167813)):
        assert abs(R.norm_ppf(p) - x) < 1e-9
    for p in np.linspace(1e-9, 1 - 1e-9, 101):
        x = R.norm_ppf(p)
        assert abs(0.5 * math.erfc(-x / math.sqrt(2)) - p) <= 1e-12 * max(1.0, 1 / min(p, 1 - p)) * min(p, 1 - p) + 1e-15
    with pytest.raises(ValueError):
        R.norm_ppf(1.0)
    # Wilson-Hilferty vs tabulated chi^2 quantiles (0.99: dof 7 -> 18.475, 30 -> 50.892, 100 -> 135.807)
    for dof, q in ((7, 18.475), (30, 50.892), (100, 135.807)):
        assert abs(R.chi2_quantile_wh(dof, 0.99) / q - 1) < 0.005
    assert abs(R.CHI2_2_MEDIAN - 1.386294) < 1e-6
    # 3.035 is the 1 % point of the 2D radial residual: P(e > k) = exp(-k^2 / 2)
    assert abs(math.exp(-RobustSchedule().reject_k ** 2 / 2) - 0.01) < 1e-4
    e = np.array([0.0, 1.0, 2.0, 4.0, 10.0])
    assert np.allclose(R.huber_weights(e, 2.0), [1, 1, 1, 0.5, 0.2])
    assert np.allclose(R.tukey_weights(e, 4.685), [1, (1 - (1 / 4.685) ** 2) ** 2, (1 - (2 / 4.685) ** 2) ** 2,
                                                   (1 - (4 / 4.685) ** 2) ** 2, 0])
    assert R.nu2_view([1.386294] * 7) == pytest.approx(1.0)
    assert R.nu2_view(np.full(9, 100.0)) == 9.0 and R.nu2_view([0.01]) == 1.0 and R.nu2_view([]) == 1.0
    chi2, thr, rej = R.view_chi2_test(np.full(20, 2.0), 33, 0.99)
    assert chi2 == 40.0 and not rej and thr == pytest.approx(R.chi2_quantile_wh(33, 0.99))
    assert R.view_chi2_test([50.0], 1, 0.99)[2]
    assert R.view_chi2_test([50.0], 0, 0.99) == (50.0, float("inf"), False)
    s = RobustSchedule()
    assert (s.huber_delta, s.huber_rounds, s.tukey_c, s.tukey_rounds, s.reject_k, s.view_chi2_q,
            s.view_reject_frac_flag, s.nu_clip, s.nu_flag) == (2.0, 2, 4.685, 1, 3.035, 0.99, 0.15, (1.0, 9.0), 2.0)
    with pytest.raises(ValueError):
        RobustSchedule(nu_clip=(2.0, 1.0)).validate()
    assert ENGINE_VERSION == "v2"


# ------------------------------------------------------------------ Jacobians
def test_invdepth_bundle_jacobian_numeric(monkeypatch):
    rng = np.random.default_rng(31)
    X_true = random_subject(TEMPLATE, NAMES, rng)
    views, cams = _rich_scene(rng, X_true)
    cap, res = _capture(monkeypatch, views, TEMPLATE + rng.normal(scale=2.0, size=TEMPLATE.shape), _priors(),
                        scale=ScaleConfig(init=0.15), robust=RobustSchedule(), view_weighting=True,
                        landmark_normals=_normals(TEMPLATE), jaw_weights=JAW_W, jaw_center_mm=JAW_C)
    idx = res.param_index
    kinds = [st["kind"] for st in res.view_stats]
    assert kinds == ["free", "fixed_f", "free", "free", "hard", "hard"]
    assert {"a_0", "a_2", "a_3", "phi_0", "phi_1", "jaw_0", "jaw_1", "jaw_3", "zeta"} <= set(idx)
    assert "a_1" not in idx and "a_4" not in idx
    # the project hook enforces the boxes; retract stays smooth
    assert cap["kw"]["project"] is not None and cap["kw"]["step_solver"] is not None
    fun, jac, retract, x0 = cap["fun"], cap["jac"], cap["retract"], cap["x0"]
    Ja = jac(x0)
    Jn = _numeric_jacobian(fun, retract, x0)
    assert Ja.shape == Jn.shape
    _assert_close(Ja, Jn, idx)
    # every special column is exercised and a 0.1 % error in it is detected
    for key in ("rho_0", "rho_1", "rho_4", "a_0", "a_2", "phi_0", "phi_1", "jaw_0", "jaw_1", "jaw_3", "zeta",
                "omega_1", "tau_5"):
        sl = idx[key]
        assert np.abs(Ja[:, sl]).max() > 0, key
        assert _detected(Ja, Jn, idx, np.arange(sl.start, sl.stop)), key
    pts = idx["points"]
    assert _detected(Ja, Jn, idx, np.arange(pts.start, pts.stop))
    # robust schedule state reached the closures: weights below one somewhere
    assert any(st["view_weight"] < 1.0 for st in res.view_stats) or any(st["nu"] > 1 for st in res.view_stats)


class _LinearShape:
    """Non-identity ShapeModel: X = mean + reshape(B q)."""

    def __init__(self, mean, Bm):
        self.mean = np.asarray(mean, float)
        self.B = np.asarray(Bm, float)
        self.n_params = self.B.shape[1]

    def init(self, X0):
        return np.linalg.lstsq(self.B, (np.asarray(X0, float) - self.mean).ravel(), rcond=None)[0]

    def points(self, q):
        return self.mean + (self.B @ q).reshape(-1, 3)

    def jacobian(self, q):
        return self.B


def test_shape_model_chain_rule(monkeypatch):
    rng = np.random.default_rng(5)
    X_true = random_subject(TEMPLATE, NAMES, rng)
    views = []
    for yaw in (-40, 0, 40):
        c = orbit_camera(500.0, yaw, 3.0, 26.0)
        uv = c.project(X_true) + rng.normal(scale=1.0, size=(N, 2))
        uv[~rigs.visible_mask(c, X_true)] = np.nan
        views.append(ViewObs(uv, c.copy(), f_prior=c.f, f_prior_log_sigma=0.05, focal_group="g", sigma_px=1.0))
    Bm = np.eye(3 * N) + 0.05 * rng.normal(size=(3 * N, 3 * N))
    shape = _LinearShape(TEMPLATE, Bm)
    assert isinstance(shape, ShapeModel) and isinstance(FreePoints(N), ShapeModel)
    cap, res = _capture(monkeypatch, views, TEMPLATE.copy(), _priors(), scale=ScaleConfig(init=0.1), shape_model=shape)
    Ja = cap["jac"](cap["x0"])
    Jn = _numeric_jacobian(cap["fun"], cap["retract"], cap["x0"])
    _assert_close(Ja, Jn, res.param_index)
    monkeypatch.undo()
    # a full-rank linear reparameterisation gives the FreePoints solution and covariance
    a = bundle_adjust(views, TEMPLATE.copy(), _priors(), shape_model=shape)
    b = bundle_adjust(views, TEMPLATE.copy(), _priors())
    assert np.abs(a.X - b.X).max() < 1e-4                                # LM tolerance
    assert np.linalg.norm(a.cov_shape - b.cov_shape) / np.linalg.norm(b.cov_shape) < 1e-4
    # a reduced basis: points stay in the affine span
    lo = _LinearShape(TEMPLATE, np.linalg.qr(rng.normal(size=(3 * N, 12)))[0])
    c = bundle_adjust(views, TEMPLATE.copy(), _priors(), shape_model=lo)
    d = (c.X - TEMPLATE).ravel()
    assert np.allclose(lo.B @ (lo.B.T @ d), d, atol=1e-8)
    assert c.cov.shape == (3 * N, 3 * N) and np.linalg.matrix_rank(c.cov, tol=1e-9 * np.abs(c.cov).max()) <= 12


# ------------------------------------------------------------------ cameras
def test_invdepth_results_match_pinhole():
    rng = np.random.default_rng(2)
    X_true = random_subject(TEMPLATE, NAMES, rng)
    cams = [orbit_camera(450.0 + 30 * k, y, rng.uniform(-6, 6), 26.0) for k, y in enumerate((-60, -30, 0, 30, 60))]
    views = []
    for k, c in enumerate(cams):
        uv = c.project(X_true)
        uv[~rigs.visible_mask(c, X_true)] = np.nan
        c0 = c.copy()
        c0.t = c0.t + rng.normal(scale=3.0, size=3)
        c0.f *= 1.03
        kw = dict(sigma_px=1.0)
        if k == 0:
            kw.update(estimate_focal=False)
            c0.f = c.f
        elif k in (1, 2):
            kw.update(focal_group="hard")
        elif k == 3:
            kw.update(focal_group="soft", focal_tie_sigma=0.02)
        views.append(ViewObs(uv, c0, **kw))
    # prior centred on the truth without symmetry / midline terms: the truth is the exact optimum
    res = bundle_adjust(views, TEMPLATE.copy(), Priors(mean=X_true, sigma=8.0), huber_px=None)
    assert [st["kind"] for st in res.view_stats] == ["fixed_f", "hard", "hard", "free", "free"]
    for c_est, c_true, v in zip(res.cameras, cams, views):
        assert isinstance(c_est, Camera)
        m = ~np.isnan(v.uv[:, 0])
        rms = float(np.sqrt(np.mean(np.sum((c_est.project(res.X[m]) - v.uv[m]) ** 2, axis=1))))
        assert rms < 1e-6, rms
        assert abs(c_est.f / c_true.f - 1) < 1e-8
        assert np.allclose(c_est.R, c_true.R, atol=1e-9) and np.allclose(c_est.t, c_true.t, atol=1e-6)
    assert max(res.rmse_px) < 1e-6
    assert np.abs(res.X - X_true).max() < 1e-6
    assert np.ptp([res.cameras[1].f, res.cameras[2].f]) < 1e-9          # hard sharing is exact


def test_rho_bounds_weak_perspective():
    rng = np.random.default_rng(9)
    X_true = random_subject(TEMPLATE, NAMES, rng)
    views, cams = [], []
    for k, yaw in enumerate((-60, -30, 0, 30, 60)):
        c = orbit_camera(8000.0, yaw, rng.uniform(-5, 5), 200.0)
        uv = c.project(X_true) + rng.normal(scale=1.0, size=(N, 2))
        uv[~rigs.visible_mask(c, X_true)] = np.nan
        c0 = c.copy()
        c0.t = c0.t * (1.3 if k % 2 else 0.9)      # 10.4 m starts are clipped to the 10 m bound
        c0.f = c.f * 1.1
        views.append(ViewObs(uv, c0, f_prior=c.f * 1.1, f_prior_log_sigma=0.1, kinds=["generic"] * N))
        cams.append(c)
    res = bundle_adjust(views, TEMPLATE.copy(), _priors())
    assert np.isfinite(res.X).all() and np.isfinite(res.cost) and not res.flags
    lo, hi = B.BUNDLE["rho_min_per_mm"].value, B.BUNDLE["rho_max_per_mm"].value
    for c, st in zip(res.cameras, res.view_stats):
        rho = 1.0 / c.t[2]
        assert lo - 1e-15 <= rho <= hi + 1e-15 and np.isfinite(c.f)
        assert st["kind"] == "free"
        assert abs(st["sigma_logf"] / 0.1 - 1.0) < 0.2, st["sigma_logf"]   # the data hardly see f
        assert st["sigma_logz"] > 0.05
    assert max(res.rmse_px) < 10.0


def _focal_scene(rng, yaws, dist, f_scale, log_sigma, tie, group="phone", noise=1.0):
    X_true = random_subject(TEMPLATE, NAMES, rng)
    views, cams = [], []
    for yaw in yaws:
        c = orbit_camera(dist * rng.uniform(0.95, 1.05), yaw, rng.uniform(-5, 5), 26.0)
        uv = c.project(X_true) + rng.normal(scale=noise, size=(N, 2))
        uv[~rigs.visible_mask(c, X_true)] = np.nan
        c0 = c.copy()
        c0.f = c.f * f_scale
        c0.t = c0.t * f_scale
        views.append(ViewObs(uv, c0, f_prior=c.f * f_scale, f_prior_log_sigma=log_sigma, focal_group=group,
                             focal_tie_sigma=tie, sigma_px=noise))
        cams.append(c)
    return X_true, views, cams


def test_soft_focal_tie():
    # (a) two views of one group, tie 0.02: their focals stay within a few tie sigmas
    rng = np.random.default_rng(4)
    X_true, views, cams = _focal_scene(rng, (-25, 25), 600.0, 1.0, 0.6, 0.02)
    views[1].camera.f *= 1.15                         # start the second view 15 % off
    res = bundle_adjust(views, TEMPLATE.copy(), _priors())
    f1, f2 = (c.f for c in res.cameras)
    assert abs(f1 / f2 - 1) < 0.05 and f1 != f2       # tied softly, not shared exactly
    assert "phi_0" in res.param_index and "a_0" in res.param_index and "a_1" in res.param_index
    # (b) a 10 %-off EXIF prior (sigma 0.6) still lets views spanning >= 60 deg at 0.5 m recover f within 3 %
    errs = []
    for seed in range(3):
        rng = np.random.default_rng(40 + seed)
        X_true, views, cams = _focal_scene(rng, (-35, -10, 10, 35), 500.0, 1.10, 0.6, 0.02)
        res = bundle_adjust(views, TEMPLATE.copy(), _priors())
        errs += [abs(c.f / t.f - 1) for c, t in zip(res.cameras, cams)]
        assert all(st["sigma_logf"] < 0.1 for st in res.view_stats)   # measured, not prior-driven
    assert max(errs) < 0.03, errs


def test_distance_and_pose_priors():
    rng = np.random.default_rng(12)
    X_true = random_subject(TEMPLATE, NAMES, rng)
    c = orbit_camera(900.0, 20.0, 0.0, 85.0)
    uv = c.project(X_true) + rng.normal(scale=1.0, size=(N, 2))
    uv[~rigs.visible_mask(c, X_true)] = np.nan
    d_true = float(np.linalg.norm(c.t))
    # a weak-perspective single view: f and z are a ridge; a tight distance prior picks the point on it
    for target in (0.8, 1.25):
        v = ViewObs(uv, c.copy(), f_prior=c.f, f_prior_log_sigma=0.5, sigma_px=1.0,
                    distance_prior=(c.t[2] * target, 0.01))
        res = bundle_adjust([v], TEMPLATE.copy(), _priors())
        assert abs(res.cameras[0].t[2] / (c.t[2] * target) - 1) < 0.03
        assert res.view_stats[0]["sigma_logz"] < 0.012
    # pose tags: yaw/pitch of the camera centre in the head frame; a consistent tag costs nothing
    yaw, pitch = B.camera_angles_deg(c)
    assert abs(yaw - 20.0) < 3.0 and abs(pitch) < 3.0
    v = ViewObs(uv, c.copy(), f_prior=c.f, f_prior_log_sigma=0.05, sigma_px=1.0, pose_tag=(yaw, pitch, 10.0, 5.0))
    res = bundle_adjust([v], TEMPLATE.copy(), _priors())
    assert abs(res.view_stats[0]["yaw_deg"] - yaw) < 1.0
    with pytest.raises(ValueError):
        bundle_adjust([ViewObs(uv, c.copy(), pose_tag=(0.0, 0.0, 0.0, 5.0))], TEMPLATE.copy(), _priors())
    with pytest.raises(ValueError):
        bundle_adjust([ViewObs(uv, c.copy(), distance_prior=(-1.0, 0.3))], TEMPLATE.copy(), _priors())


# ------------------------------------------------------------------ robust schedule
def _rear_phone_views(seed, outlier_frac, noise_mult=None):
    """rear_phone scenario (legacy subject, definition bias on) with the simulator's true per-observation
    covariance as cov_px, so '5-20 sigma' outliers are 5-20 sigma for the bundle too.

    (With the WP-07 kind model and no image tangents, brow points enter with a 28 mm isotropic sigma:
    a 5-20 x 6.3 mm brow outlier is then within ~1 sigma and no residual test can see it.  That is the
    noise model's limitation, so this test feeds the true noise.)
    """
    r_subj, r_rig, r_det = _seed_streams(seed)
    names, X, meta = subjects.legacy_subject(r_subj)
    rig = rigs.rear_phone(r_rig, X=X)
    kinds = detector_sim.legacy_kinds(names)
    obs = detector_sim.simulate(X, kinds, rig, r_det, outlier_frac=outlier_frac)
    t = obs.tangent_dirs
    n = np.column_stack([-t[:, 1], t[:, 0]])
    views = []
    for k, (uv, cam) in enumerate(zip(obs.uv, rig.cameras)):
        s = obs.sigma_px_true[k]
        C = (s[:, 1] ** 2)[:, None, None] * np.einsum("ni,nj->nij", t, t) \
            + (s[:, 0] ** 2)[:, None, None] * np.einsum("ni,nj->nij", n, n)
        C[np.isnan(s[:, 0])] = np.eye(2)
        c0 = cam.copy()
        c0.f = rig.f_prior_px[k]
        views.append(ViewObs(uv, c0, f_prior=rig.f_prior_px[k], f_prior_log_sigma=rig.f_prior_log_sigma[k],
                             focal_group=rig.focal_group[k], kinds=kinds, cov_px=C))
    pri = _priors(meta["template"], names, LEGACY_PRIOR["sigma"], LEGACY_PRIOR["sigma_sym"], LEGACY_PRIOR["sigma_mid"])
    return views, pri, obs, X, meta


def test_robust_rejection_rates():
    rej_out = n_out = rej_in = n_in = 0
    rms, rms0 = [], []
    for seed in range(1000, 1020):
        views, pri, obs, X, meta = _rear_phone_views(seed, 0.05)
        res = bundle_adjust(views, meta["template"].copy(), pri, robust=RobustSchedule())
        views0, pri0, obs0, _, _ = _rear_phone_views(seed, 0.0)
        res0 = bundle_adjust(views0, meta["template"].copy(), pri0, robust=RobustSchedule())
        for k in range(len(views)):
            out = obs.outlier_mask[k]
            inl = obs.visible[k] & ~out
            rej_out += int((out & ~res.inlier_mask[k]).sum())
            n_out += int(out.sum())
            rej_in += int((inl & ~res.inlier_mask[k]).sum())
            n_in += int(inl.sum())
        rms.append(procrustes_rmse(res.X, X))
        rms0.append(procrustes_rmse(res0.X, X))
        assert np.isfinite(res.chi2_red) and res.view_stats[0]["dof"] > 0
    assert n_out > 50
    assert rej_out / n_out >= 0.95, (rej_out, n_out)
    assert rej_in / n_in <= 0.02, (rej_in, n_in)
    assert np.median(rms) <= 1.1 * np.median(rms0), (np.median(rms), np.median(rms0))


def test_noisy_view_flagged():
    rng = np.random.default_rng(17)
    X_true = random_subject(TEMPLATE, NAMES, rng)
    views = []
    for k, yaw in enumerate((-50, -25, 0, 25, 50)):
        c = orbit_camera(600.0, yaw, rng.uniform(-5, 5), 26.0)
        s = 3.0 if k == 2 else 1.0
        uv = c.project(X_true) + rng.normal(scale=1.5 * s, size=(N, 2))
        uv[~rigs.visible_mask(c, X_true)] = np.nan
        views.append(ViewObs(uv, c.copy(), f_prior=c.f, f_prior_log_sigma=0.05, focal_group="g", sigma_px=1.5))
    res = bundle_adjust(views, TEMPLATE.copy(), _priors(), robust=RobustSchedule())
    nu2 = [st["nu"] ** 2 for st in res.view_stats]
    assert nu2[2] > 4.0 and "F-VIEW-NOISY" in res.view_stats[2]["flags"], nu2
    assert all(nu2[k] <= 2.0 for k in (0, 1, 3, 4)), nu2
    assert all("F-VIEW-NOISY" not in res.view_stats[k]["flags"] for k in (0, 1, 3, 4))
    assert "F-VIEW-NOISY" in res.flags
    # the scale is folded into the reported noise of the final round
    m = res.inlier_mask[2]
    assert np.allclose(res.obs_cov_px[2][m, 0, 0], 1.5 ** 2 * nu2[2])


def test_view_rejected_and_outlier_flag():
    rng = np.random.default_rng(23)
    X_true = random_subject(TEMPLATE, NAMES, rng)
    views = []
    for k, yaw in enumerate((-50, -25, 0, 25, 50)):
        c = orbit_camera(600.0, yaw, rng.uniform(-5, 5), 26.0)
        uv = c.project(X_true) + rng.normal(scale=1.5, size=(N, 2))
        vis = rigs.visible_mask(c, X_true)
        if k == 1:    # wrong correspondences: a shuffled view (nu clipped at 3, chi^2 test fails)
            perm = rng.permutation(np.flatnonzero(vis))
            uv[np.flatnonzero(vis)] = uv[perm] + rng.normal(scale=40.0, size=(len(perm), 2))
        if k == 3:    # 25 % gross outliers
            bad = rng.choice(np.flatnonzero(vis), size=int(0.25 * vis.sum()), replace=False)
            uv[bad] += rng.normal(scale=60.0, size=(len(bad), 2))
        uv[~vis] = np.nan
        views.append(ViewObs(uv, c.copy(), f_prior=c.f, f_prior_log_sigma=0.05, focal_group="g", sigma_px=1.5))
    res = bundle_adjust(views, TEMPLATE.copy(), _priors(), robust=RobustSchedule())
    st = res.view_stats
    assert "F-VIEW-REJECT" in st[1]["flags"] and not res.inlier_mask[1].any()
    assert "F-VIEW-OUTLIERS" in st[3]["flags"] and st[3]["rejected_frac"] > 0.15
    assert all("F-VIEW-REJECT" not in st[k]["flags"] for k in (0, 2, 3, 4))
    assert {"F-VIEW-REJECT", "F-VIEW-OUTLIERS"} <= set(res.flags)
    assert procrustes_rmse(res.X, X_true) < 0.5 * procrustes_rmse(TEMPLATE, X_true)
    assert np.isfinite(res.cov).all() and "COV-SINGULAR" not in res.flags


# ------------------------------------------------------------------ visibility and view weights
def test_visibility_weights_and_contour_rule():
    rng = np.random.default_rng(8)
    X_true = random_subject(TEMPLATE, NAMES, rng)
    kinds = ["contour" if n.startswith(("zygion", "gonion", "tragion")) else "generic" for n in NAMES]
    views = []
    for yaw in (-60, 0, 60):
        c = orbit_camera(600.0, yaw, 0.0, 26.0)
        uv = c.project(X_true) + rng.normal(scale=1.0, size=(N, 2))
        views.append(ViewObs(uv, c.copy(), f_prior=c.f, f_prior_log_sigma=0.05, focal_group="g", sigma_px=1.0,
                             kinds=kinds))          # every point 'visible' to the detector
    res = bundle_adjust(views, TEMPLATE.copy(), _priors(), landmark_normals=_normals(TEMPLATE))
    plain = bundle_adjust(views, TEMPLATE.copy(), _priors())
    assert all(m.all() for m in plain.inlier_mask)
    for k, yaw in enumerate((-60, 0, 60)):
        C = res.cameras[k].center
        d = C - res.X
        cos = np.einsum("ij,ij->i", _normals(TEMPLATE), d) / np.linalg.norm(d, axis=1)
        back = cos < np.cos(np.radians(80))
        assert back.any() and not res.inlier_mask[k][back].any()
        if yaw:
            far = np.array([kd == "contour" for kd in kinds]) & (res.X[:, 0] * yaw < 0)
            assert far.any() and not res.inlier_mask[k][far].any()
    assert res.m_data < plain.m_data


def test_view_weight_cap():
    rng = np.random.default_rng(3)
    X_true = random_subject(TEMPLATE, NAMES, rng)
    views = []
    for k in range(7):
        yaw, pitch = (rng.uniform(-3, 3), rng.uniform(-3, 3)) if k < 6 else (85.0, 0.0)
        c = orbit_camera(600.0, yaw, pitch, 26.0)
        uv = c.project(X_true) + rng.normal(scale=1.0, size=(N, 2))
        uv[~rigs.visible_mask(c, X_true)] = np.nan
        views.append(ViewObs(uv, c.copy(), f_prior=c.f, f_prior_log_sigma=0.05, focal_group="g", sigma_px=1.0))
    res = bundle_adjust(views, TEMPLATE.copy(), _priors(), view_weighting=True)
    share = np.array([st["weight_share"] for st in res.view_stats])
    w = np.array([st["view_weight"] for st in res.view_stats])
    # the cap acts on the frozen weights before each LM run; the shares re-evaluated at the
    # final solution may drift by O(1e-5)
    assert share.max() <= 0.40 + 1e-4, share
    assert abs(share.sum() - 1.0) < 1e-9
    assert np.allclose(w[:6], w[0]) and w[0] <= 1.0 / 6.0 + 1e-12      # one yaw/pitch bin
    assert w[6] < 1.0 and share[6] > 0.39                                # the profile was capped, not dropped
    assert share[6] > share[0]                                           # and still counts most
    off = bundle_adjust(views, TEMPLATE.copy(), _priors())
    assert np.allclose([st["view_weight"] for st in off.view_stats], 1.0)


# ------------------------------------------------------------------ jaw hinge
def _jaw_views(X_true, theta_deg, rng_seed, jaw_on=True, neutral_deg=1.5):
    """Five views; view 3 has the hinge at ``theta_deg``, the others at ``neutral_deg`` (the DESIGN 4.9
    neutral prior mean: only differences between views are observable, the common mode is the prior's)."""
    rng = np.random.default_rng(rng_seed)
    views = []
    for k, yaw in enumerate((-60, -30, 0, 30, 60)):
        c = orbit_camera(600.0, yaw, rng.uniform(-4, 4), 26.0)
        Xk = jaw_hinge(X_true, JAW_W, math.radians(theta_deg if k == 3 else neutral_deg), JAW_C)
        uv = c.project(Xk) + rng.normal(scale=1.0, size=(N, 2))
        uv[~rigs.visible_mask(c, X_true)] = np.nan
        jc = JawConfig(enabled=jaw_on, prior_sigma_deg=3.0 if k == 3 else 1.0)
        views.append(ViewObs(uv, c.copy(), f_prior=c.f, f_prior_log_sigma=0.05, focal_group="g", sigma_px=1.0,
                             jaw=jc))
    return views


def test_jaw_hinge_recovers_opening():
    rng = np.random.default_rng(6)
    X_true = random_subject(TEMPLATE, NAMES, rng)
    kw = dict(jaw_weights=JAW_W, jaw_center_mm=JAW_C)
    opened = bundle_adjust(_jaw_views(X_true, 8.0, 1), TEMPLATE.copy(), _priors(), **kw)
    closed = bundle_adjust(_jaw_views(X_true, 1.5, 1), TEMPLATE.copy(), _priors(), **kw)   # no opening
    rigid_fit = bundle_adjust(_jaw_views(X_true, 8.0, 1, jaw_on=False), TEMPLATE.copy(), _priors(), **kw)
    st = opened.view_stats
    assert abs(st[3]["jaw_deg"] - 8.0) < 1.5, st[3]["jaw_deg"]
    assert st[3]["jaw_sigma_deg"] is not None and 0 < st[3]["jaw_sigma_deg"] < 1.5
    assert all(abs(st[k]["jaw_deg"] - 1.5) < 1.0 for k in (0, 1, 2, 4))
    assert rigid_fit.view_stats[3]["jaw_deg"] is None and "jaw_3" not in rigid_fit.param_index
    rigid = JAW_W == 0

    def moved(res):
        """Rigid-landmark displacement vs the no-opening solve after similarity alignment on them
        (gauge-projected, DESIGN 7.3: the legacy prior fixes pose and size only loosely)."""
        s, Rm, t = umeyama(res.X[rigid], closed.X[rigid], with_scale=True)
        return np.linalg.norm(s * res.X[rigid] @ Rm.T + t - closed.X[rigid], axis=1)
    assert moved(opened).max() < 0.3, moved(opened).max()
    assert moved(rigid_fit).max() > 3 * moved(opened).max()
    assert procrustes_rmse(rigid_fit.X, X_true) > procrustes_rmse(opened.X, X_true)
    assert max(opened.rmse_px) < 4.0 and rigid_fit.rmse_px[3] > opened.rmse_px[3]
    with pytest.raises(ValueError, match="jaw_weights"):
        bundle_adjust(_jaw_views(X_true, 8.0, 1), TEMPLATE.copy(), _priors())


# ------------------------------------------------------------------ terms
class ChordTerm:
    """Toy caliper chord (DESIGN 4.7): (|X_a - X_b| - L) / sigma_L, no own parameters."""

    is_prior = False

    def __init__(self, a, b, L, sigma=0.5, name="chord"):
        self.a, self.b, self.L, self.sigma, self.name = int(a), int(b), float(L), float(sigma), name

    def n_params(self):
        return 0

    def init_params(self, state):
        return np.zeros(0)

    def residuals(self, state, p):
        return np.array([(np.linalg.norm(state.X[self.a] - state.X[self.b]) - self.L) / self.sigma])

    def jacobian(self, state, p):
        d = state.X[self.a] - state.X[self.b]
        u = d / np.linalg.norm(d) / self.sigma
        J = np.zeros((1, 3 * len(state.X)))
        J[0, 3 * self.a:3 * self.a + 3] = u
        J[0, 3 * self.b:3 * self.b + 3] = -u
        return {"X": J}


class DistanceTerm:
    """Toy prior term with its own parameter d (mm) and a camera block: (1/rho_v - d)/s, (d - d0)/s0."""

    is_prior = True

    def __init__(self, view, d0, s=5.0, s0=50.0, name="dist"):
        self.v, self.d0, self.s, self.s0, self.name = view, float(d0), float(s), float(s0), name

    def n_params(self):
        return 1

    def init_params(self, state):
        return np.array([1.0 / state.invdepth[self.v]["rho"]])

    def residuals(self, state, p):
        rho = state.invdepth[self.v]["rho"]
        return np.array([(1.0 / rho - p[0]) / self.s, (p[0] - self.d0) / self.s0])

    def jacobian(self, state, p):
        inv = state.invdepth[self.v]
        rho = inv["rho"]
        Jc = np.zeros((2, len(inv["block"])))
        Jc[0, inv["block"].index("rho_per_m")] = -1e-3 / rho ** 2 / self.s
        return {f"cam:{self.v}": Jc, "self": np.array([[-1.0 / self.s], [1.0 / self.s0]])}


def test_term_protocol_toy_chord(monkeypatch):
    # (1) protocol integration on the anatomical factor-prior scene: X block, cam:<v> block,
    #     self block, data vs prior routing; analytic Jacobian vs numeric.
    prior = FactorPrior.from_package()
    mu = prior.mean()
    ids = list(prior.ids)
    kinds = [ANATOMICAL[i].kind for i in ids]
    rng = np.random.default_rng(11)
    X = mu * np.exp(0.02)
    nm = NoiseModel(kinds)
    views = []
    for yaw in (-60, -30, 0, 30, 60):
        c = orbit_camera(600.0, yaw, rng.uniform(-5, 5), 26.0)
        m = rigs.visible_mask(c, X)
        Cv = nm.view_cov(np.where(m, c.f / c.depth(X), np.nan), float(np.ptp(c.project(X)[m, 0])))
        L = np.linalg.cholesky(np.where(m[:, None, None], Cv, np.eye(2)))
        uv = c.project(X) + np.einsum("nij,nj->ni", L, rng.normal(size=(len(X), 2)))
        uv[~m] = np.nan
        c0 = c.copy()
        c0.t = c0.t + rng.normal(scale=2.0, size=3)
        views.append(ViewObs(uv, c0, f_prior=c.f, f_prior_log_sigma=0.05, focal_group="g", kinds=kinds))
    a, b = ids.index("zy_L"), ids.index("zy_R")
    chord = ChordTerm(a, b, float(np.linalg.norm(X[a] - X[b])))
    dist = DistanceTerm(2, 650.0)
    assert isinstance(chord, Term) and isinstance(dist, Term)
    cap, res = _capture(monkeypatch, views, mu.copy(), None, prior=prior, terms=[chord, dist])
    Ja = cap["jac"](cap["x0"])
    Jn = _numeric_jacobian(cap["fun"], cap["retract"], cap["x0"])
    _assert_close(Ja, Jn, res.param_index)
    sl = res.param_index["term:dist"]
    assert sl.stop - sl.start == 1 and sl.start >= res.param_index["points"].stop
    assert "term:chord" in res.param_index
    monkeypatch.undo()
    base = bundle_adjust(views, mu.copy(), None, prior=prior)
    withc = bundle_adjust(views, mu.copy(), None, prior=prior, terms=[chord, dist])
    # data term rows count in m_data; the prior term goes to H_prior only
    assert withc.m_data == base.m_data + 1
    j = res.param_index["term:dist"].start
    assert withc.H_data[j, j] == 0 and withc.H_prior[j, j] > 0
    assert set(withc.term_params) == {"chord", "dist"} and withc.term_params["dist"].shape == (1,)
    # the chord fixes its own metric length to sigma_L ...
    g = np.zeros(3 * len(X))
    u = withc.X[a] - withc.X[b]
    u /= np.linalg.norm(u)
    g[3 * a:3 * a + 3], g[3 * b:3 * b + 3] = u, -u
    assert np.sqrt(g @ withc.cov @ g) < 0.55 < np.sqrt(g @ base.cov @ g)
    # ... but under the anatomical factor prior zy-zy varies relative to overall size (kappa 1.5),
    # so one chord leaves the global log-scale at ~2 % (measured ~0.022 even with 0.1 px data)
    assert 0.01 < withc.zeta_sigma < 0.7 * base.zeta_sigma
    # (2) the toy chord with a template-centred prior (the chord's relative length is pinned):
    #     the term drives zeta_sigma below 0.01 and recovers the 2 % scale
    rng = np.random.default_rng(12)
    Xs = TEMPLATE * np.exp(0.02)
    tv = []
    for yaw in (-60, -30, 0, 30, 60):
        c = orbit_camera(600.0, yaw, rng.uniform(-5, 5), 26.0)
        uv = c.project(Xs) + rng.normal(scale=1.0, size=(N, 2))
        uv[~rigs.visible_mask(c, Xs)] = np.nan
        tv.append(ViewObs(uv, c.copy(), f_prior=c.f, f_prior_log_sigma=0.05, focal_group="g", sigma_px=1.0))
    za, zb = IDX["zygion_L"], IDX["zygion_R"]
    toy = ChordTerm(za, zb, float(np.linalg.norm(Xs[za] - Xs[zb])))
    pri = Priors(mean=TEMPLATE, sigma=3.0)
    t0 = bundle_adjust(tv, TEMPLATE.copy(), pri, scale=ScaleConfig())
    t1 = bundle_adjust(tv, TEMPLATE.copy(), pri, scale=ScaleConfig(), terms=[toy])
    assert t0.zeta_sigma > 0.04
    assert t1.zeta_sigma < 0.01, t1.zeta_sigma
    assert abs(t1.zeta - 0.02) < 0.01
    assert abs(np.linalg.norm(t1.X[za] - t1.X[zb]) - toy.L) < 1.0
    # SolverState is a read-only view
    st = SolverState(mu, 0.0, [], [], {})
    with pytest.raises(ValueError):
        st.X[0, 0] = 1.0
    with pytest.raises(ValueError, match="unique"):
        bundle_adjust(views, mu.copy(), None, prior=prior, terms=[chord, ChordTerm(a, b, 1.0)])


# ------------------------------------------------------------------ linear step
def test_schur_step_equals_dense(monkeypatch):
    rng = np.random.default_rng(13)
    X_true = random_subject(TEMPLATE, NAMES, rng)
    views = []
    for yaw in (-45, 0, 45):
        c = orbit_camera(550.0, yaw, 2.0, 26.0)
        uv = c.project(X_true) + rng.normal(scale=1.0, size=(N, 2))
        uv[~rigs.visible_mask(c, X_true)] = np.nan
        views.append(ViewObs(uv, c.copy(), f_prior=c.f, f_prior_log_sigma=0.05, focal_group="g", sigma_px=1.0))
    pri = _priors()
    paired = np.zeros(N, bool)
    paired[np.asarray(pri.pairs).ravel()] = True
    free = ~paired                                   # midline points: 3x3 block-diagonal (legacy iid prior)
    cap, res = _capture(monkeypatch, views, TEMPLATE.copy(), pri)
    J = cap["jac"](cap["x0"])
    r = cap["fun"](cap["x0"])
    H, g = J.T @ J, J.T @ r
    lam = 1e-3 * np.diag(H)
    cols = res.param_index["points"].start + B._coord_cols(np.flatnonzero(free))
    d0 = dense_step(H, lam, g)
    d1 = schur_step(H, lam, g, cols)
    assert np.linalg.norm(d1 - d0) / np.linalg.norm(d0) < 1e-8
    assert np.allclose(-np.linalg.solve(H + np.diag(lam), g), d0, rtol=1e-8, atol=1e-12 * np.abs(d0).max())
    # coupled points (a symmetric pair) are not block-diagonal: falls back to the dense step
    cpl = res.param_index["points"].start + B._coord_cols(np.asarray(pri.pairs[0]))
    assert np.linalg.norm(schur_step(H, lam, g, cpl) - d0) / np.linalg.norm(d0) < 1e-8
    monkeypatch.undo()
    # the whole solve with the Schur step (threshold lowered) equals the dense solve
    dense = bundle_adjust(views, TEMPLATE.copy(), pri)
    calls = []
    orig = B.schur_step

    def spy(*a, **k):
        calls.append(1)
        return orig(*a, **k)
    monkeypatch.setattr(B, "schur_step", spy)
    schur = bundle_adjust(views, TEMPLATE.copy(), pri, schur_point_idx=free, dense_max_params=0)
    assert calls
    assert np.abs(schur.X - dense.X).max() < 1e-7
    assert abs(schur.cameras[0].f / dense.cameras[0].f - 1) < 1e-9
    with pytest.raises(ValueError):
        bundle_adjust(views, TEMPLATE.copy(), pri, schur_point_idx=free[:-1], dense_max_params=0)


# ------------------------------------------------------------------ reconstruct
def test_reconstruct_v2_kwargs_and_reinit(monkeypatch):
    rng = np.random.default_rng(21)
    X = random_subject(TEMPLATE, NAMES, rng)
    kinds = detector_sim.legacy_kinds(NAMES)
    photos, cams = [], []
    for yaw in (-40, -15, 15, 40):
        c = orbit_camera(500.0, yaw, 2.0, 26.0)
        uv = c.project(X) + rng.normal(scale=2.0, size=(N, 2))
        uv[~rigs.visible_mask(c, X)] = np.nan
        photos.append(PhotoLandmarks(uv, c.width, c.height, f_prior_px=c.f * 1.05, f_prior_log_sigma=0.3,
                                     kinds=kinds, focal_group="phone"))
        cams.append(c)
    calls = []
    orig = B.bundle_adjust

    def spy(views, X0, priors=None, **kw):
        calls.append((len(views), kw))
        return orig(views, X0, priors, **kw)
    monkeypatch.setattr(Rc, "bundle_adjust", spy)
    # PnP sigma from the noise model: kinds at one common px_per_mm, finite and positive
    sig = Rc.pnp_sigma_px(photos[0], TEMPLATE, ~np.isnan(photos[0].uv[:, 0]), None, None)
    assert np.all(np.isfinite(sig)) and np.all(sig > 0)
    dps = [(600.0, 0.4)] * 4
    res = reconstruct_landmarks(photos, _priors(), robust=RobustSchedule(), view_weighting=True,
                                distance_priors=dps, focal_tie_sigma=0.02, jaw=JawConfig(enabled=True),
                                jaw_weights=JAW_W, jaw_center_mm=JAW_C, landmark_normals=_normals(TEMPLATE))
    assert len(calls) == 1
    n, kw = calls[0]
    assert isinstance(kw["robust"], RobustSchedule) and kw["view_weighting"] and kw["jaw_weights"] is JAW_W
    assert all(st["kind"] == "free" for st in res.view_stats) and "phi_0" in res.param_index
    assert all(st["jaw_deg"] is not None for st in res.view_stats)
    for c_est, c, st in zip(res.cameras, cams, res.view_stats):     # 4 views, 7-12 px noise: f is
        assert abs(np.log(c_est.f / c.f)) < 2.5 * st["sigma_logf"]     # only measured to ~14 %
    assert procrustes_rmse(res.X, X) < 2.0
    # a view whose PnP fit is poor is re-initialised against the consensus of the others
    calls.clear()
    real = Rc._robust_rms_sigmas
    count = {"n": 0}

    def fake(res_px, sigma):
        count["n"] += 1
        return 10.0 if count["n"] == 2 else real(res_px, sigma)
    monkeypatch.setattr(Rc, "_robust_rms_sigmas", fake)
    res2 = reconstruct_landmarks(photos, _priors())
    assert [c[0] for c in calls] == [3, 4]
    assert procrustes_rmse(res2.X, X) < 2.0
    with pytest.raises(ValueError, match="distance_priors"):
        reconstruct_landmarks(photos, _priors(), distance_priors=[(600.0, 0.4)])


# ------------------------------------------------------------------ runtime
def test_runtime_budget():
    rng = np.random.default_rng(99)
    extra = rng.normal(size=(100 - N, 3))
    extra /= np.linalg.norm(extra, axis=1, keepdims=True)
    extra[:, 2] = np.abs(extra[:, 2])                         # front half of the head
    T100 = np.vstack([TEMPLATE, extra * np.array([75.0, 95.0, 100.0])])
    X_true = T100 + rng.normal(scale=3.0, size=T100.shape)
    pri = Priors(mean=T100, sigma=8.0)
    views = []
    for k, yaw in enumerate(np.linspace(-60, 60, 7)):
        c = orbit_camera(600.0, yaw, rng.uniform(-5, 5), 26.0)
        uv = c.project(X_true) + rng.normal(scale=1.5, size=(100, 2))
        vis = rigs.visible_mask(c, X_true)
        bad = rng.random(100) < 0.05
        uv[bad & vis] += rng.normal(scale=40.0, size=(int((bad & vis).sum()), 2))
        uv[~vis] = np.nan
        c0 = c.copy()
        c0.t = c0.t + rng.normal(scale=3.0, size=3)
        views.append(ViewObs(uv, c0, f_prior=c.f * 1.03, f_prior_log_sigma=0.1, focal_group="g",
                             focal_tie_sigma=0.02, kinds=["generic"] * 100))
    t0 = time.perf_counter()
    res = bundle_adjust(views, T100.copy(), pri, robust=RobustSchedule(), view_weighting=True,
                        landmark_normals=_normals(T100))
    dt = time.perf_counter() - t0
    assert dt < 10.0, dt
    assert np.isfinite(res.X).all() and len(res.view_stats) == 7
