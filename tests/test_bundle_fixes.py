"""WP-07: bundle defect fixes (DESIGN D-03, D-05, D-06, 4.4, 4.6 gauge, 4.8 covariance).

Covers the mm noise model (sigma_px default None), the explicit log-scale zeta, the
LandmarkPrior protocol with rigid gauge rows, the Schur covariance and the
definition-bias floor, plus the lm.py extensions (step_solver, project, jtj).
"""
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import face3d.solve.bundle as B
from face3d.core import config
from face3d.eval.align import gauge_projector
from face3d.eval.coverage import nees
from face3d.geometry.camera import Camera, look_at
from face3d.geometry.procrustes import umeyama
from face3d.model.landmark_prior import FactorPrior
from face3d.model.registry import ANATOMICAL
from face3d.solve import noise
from face3d.solve.bundle import ENGINE_VERSION, Priors, ScaleConfig, ViewObs, bundle_adjust, view_noise_cov
from face3d.solve.lm import levenberg_marquardt
from face3d.solve.noise import NoiseModel, pin_sigma_px, whitening
from face3d.solve.reconstruct import PhotoLandmarks, reconstruct_landmarks
from face3d.solve.robust import RobustSchedule
from face3d.synthetic import midline_indices, mirror_pairs, orbit_camera, random_subject, synthetic_landmarks
from face3d.testbed import detector_sim, rigs, scorecard, subjects
from face3d.testbed.scenarios import FAST_SCENARIOS, LEGACY_PRIOR, SCENARIOS, _seed_streams

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "tests" / "golden" / "baseline_scorecard_v0.json"
NAMES, TEMPLATE = synthetic_landmarks()
N = len(TEMPLATE)


def _legacy_priors(names=NAMES, template=TEMPLATE, sigma=8.0, sigma_sym=3.0, sigma_mid=2.0):
    return Priors(mean=template, sigma=sigma, pairs=mirror_pairs(list(names)), sigma_sym=sigma_sym,
                  midline=midline_indices(list(names)), sigma_mid=sigma_mid)


def _sample_views(X, kinds, yaws, rng, dist=600.0, f35=26.0, bias=None, init_jitter_mm=2.0, **view_kw):
    """Views of X (+ shared definition bias) with noise drawn from the WP-07 noise model itself."""
    Xo = X if bias is None else X + bias
    nm = NoiseModel(kinds)
    views, vis = [], []
    for yaw in yaws:
        cam = orbit_camera(dist, yaw, rng.uniform(-5.0, 5.0), f35)
        m = rigs.visible_mask(cam, X)
        uv0 = cam.project(Xo)
        C = nm.view_cov(np.where(m, cam.f / cam.depth(Xo), np.nan), float(np.ptp(uv0[m, 0])))
        L = np.linalg.cholesky(np.where(m[:, None, None], C, np.eye(2)))
        uv = uv0 + np.einsum("nij,nj->ni", L, rng.normal(size=(len(X), 2)))
        uv[~m] = np.nan
        c0 = cam.copy()
        c0.t = c0.t + rng.normal(scale=init_jitter_mm, size=3)
        views.append(ViewObs(uv, c0, f_prior=cam.f, f_prior_log_sigma=0.05, focal_group="g", kinds=list(kinds),
                             **view_kw))
        vis.append(m)
    return views, np.array(vis)


def _capture_closures(monkeypatch, *args, **kwargs):
    """Run bundle_adjust with a zero-iteration LM shim and return its closures (legacy shim test)."""
    captured = {}
    orig = B.levenberg_marquardt

    def shim(fun, x0, jac=None, retract=None, **kw):
        captured.update(fun=fun, jac=jac, retract=retract, x0=x0)
        return orig(fun, x0, jac=jac, retract=retract, max_iter=0)
    monkeypatch.setattr(B, "levenberg_marquardt", shim)
    res = B.bundle_adjust(*args, **kwargs)
    return captured, res


def _numeric_jacobian(fun, retract, x0, h=1e-3):
    """Central differences through ``retract`` with one Richardson step (error O(h^4)).

    Plain central differences at h = 1e-6 are round-off limited at ~1e-4 relative on
    the small entries; with Richardson at h = 1e-3 the analytic Jacobian matches to
    ~2e-6 under the block-scaled comparison of :func:`_jacobian_close`.
    """
    def central(hh):
        r0 = fun(x0)
        Jn = np.zeros((len(r0), len(x0)))
        for j in range(len(x0)):
            e = np.zeros(len(x0))
            e[j] = hh
            Jn[:, j] = (fun(retract(x0, e)) - fun(retract(x0, -e))) / (2 * hh)
        return Jn
    return (4.0 * central(h / 2) - central(h)) / 3.0


def _jacobian_close(Ja, Jn, param_index, rtol=1e-4, atol_rel=1e-6):
    """Element-wise |Ja - Jn| <= rtol |Jn| + atol_rel * max|Jn| over (same row, same parameter block).

    Parameter blocks are the entries of ``param_index`` (each pose, each focal, zeta,
    points).  Unlike a single global atol (the gauge rows' zeta column, ~1e4, would
    swamp every other entry), this scale-aware test sees a 1e-4 relative error in any
    block of any row.  Returns the boolean mask of matching entries.
    """
    A = np.abs(Jn)
    scale = np.zeros_like(A)
    for name, sl in param_index.items():
        if name == "cameras":                    # union of the pose / focal blocks
            continue
        scale[:, sl] = A[:, sl].max(axis=1, keepdims=True)
    return np.abs(Ja - Jn) <= rtol * A + atol_rel * scale


def _assert_jacobian_close(Ja, Jn, param_index):
    ok = _jacobian_close(Ja, Jn, param_index)
    if not ok.all():
        i, j = np.unravel_index(np.argmin(ok), ok.shape)
        raise AssertionError(f"{int((~ok).sum())} Jacobian entries differ, e.g. [{i}, {j}]: "
                             f"analytic {Ja[i, j]!r} vs numeric {Jn[i, j]!r}")


def _assert_mutation_detected(Ja, Jn, param_index, rows, cols, factor):
    """The comparison must reject Ja with the block (rows, cols) scaled by ``factor``."""
    Jm = Ja.copy()
    Jm[np.ix_(rows, cols)] *= factor
    assert np.abs(Jm - Ja).max() > 0
    assert not _jacobian_close(Jm, Jn, param_index).all()


def _random_factor_prior(rng, mean, k=4, index=None):
    m = 3 * len(mean)
    L = rng.normal(scale=2.0, size=(m, k))
    A = rng.normal(size=(m, m))
    R = A @ A.T / m + np.diag(rng.uniform(1.0, 4.0, m))
    pr = FactorPrior(mean, L, R, meta={"rigid_invariant": True, "source": "test", "badge": "🆕"})
    return pr if index is None else pr.with_index(index)


def _anatomical_scene(seed, yaws=(-60, -30, 0, 30, 60)):
    prior = FactorPrior.from_package()
    mu = prior.mean()
    kinds = [ANATOMICAL[i].kind for i in prior.ids]
    rng = np.random.default_rng(seed)
    X = mu * np.exp(0.02)
    views, vis = _sample_views(X, kinds, yaws, rng)
    return prior, mu, X, views, vis


# ------------------------------------------------------------------ noise model
def test_noise_tables_registered():
    assert noise.KIND_SIGMA_MM == {
        "sharp_junction": (1.25, 1.25), "extremal": (2.0, 3.0), "curve": (1.5, 7.5), "contour": (2.5, 1000.0),
        "brow": (4.0, 40.0), "iris": (0.6, 0.6), "hair": (4.0, 8.0), "generic": (2.0, 2.0)}
    assert noise.KIND_SIGMA_DEF_MM == {"sharp_junction": 0.5, "extremal": 1.5, "curve": 1.0, "contour": 2.0,
                                       "brow": 2.0, "iris": 0.0, "hair": 3.0, "generic": 1.5}
    assert noise.PIN_CLASS_SIGMA_MM == {"crisp_expert": 0.8, "crisp_novice": 1.2, "contour": 1.0, "alar_base": 1.8,
                                        "nose_tip": 2.0, "ears": 2.5, "palpation": 4.5, "hair_defined": 5.0}
    assert noise.FLOOR_K == {"inner": 0.6, "iris": 0.4, "brow": 1.0, "contour": 1.5}
    assert noise.N_EFF == 80.0
    d = config.get("noise.sharp_junction_sigma_n_mm")
    assert d.value == 1.25 and d.badge in config.BADGES and d.source
    assert config.get("bundle.scale_sigma_log").value == 0.045
    # overrides flow through cfg
    cfg = config.resolve({"noise": {"generic_sigma_n_mm": 3.0, "generic_sigma_t_mm": 3.0}})
    m = NoiseModel(["generic"], cfg=cfg)
    assert np.isclose(m.view_cov([1.0], None)[0, 0, 0], 9.0 + 0.25)
    with pytest.raises(ValueError):
        NoiseModel(["nose"])


def test_noise_model_view_cov_structure():
    kinds = ["curve", "curve", "extremal", "contour", "brow", "iris", "generic"]
    m = NoiseModel(kinds, dense_mask=[False] * 6 + [True], n_total=480)
    p = np.full(7, 4.0)
    t = np.array([[2.0, 0.0], [np.nan, np.nan], [0.0, 0.0], [0.0, 3.0], [np.nan, 1.0], [1.0, 1.0], [1.0, 0.0]])
    C = m.view_cov(p, None, tangents=t)
    f2 = 0.25                                               # floor_min_px^2 (face_px unknown)
    # known tangent along +x: x variance = sigma_t^2, y = sigma_n^2
    assert np.allclose(C[0], np.diag([7.5 ** 2 * 16 + f2, 1.5 ** 2 * 16 + f2]))
    # unknown tangent: curve averages, extremal uses sigma_n
    assert np.allclose(C[1], np.eye(2) * ((1.5 ** 2 + 7.5 ** 2) / 2 * 16 + f2))
    assert np.allclose(C[2], np.eye(2) * (2.0 ** 2 * 16 + f2))
    # contour tangent along +y: normal (x) sigma 2.5 mm
    assert np.isclose(C[3, 0, 0], 2.5 ** 2 * 16 + f2) and C[3, 1, 1] > 1e6
    # brow with a NaN tangent component is unknown -> isotropic average
    assert np.isclose(C[4, 0, 0], (4.0 ** 2 + 40.0 ** 2) / 2 * 16 + f2) and np.isclose(C[4, 0, 1], 0.0)
    # dense point inflated by eta = 480 / 80 = 6
    assert np.isclose(C[6, 0, 0], 2.0 ** 2 * 16 * 6.0 + f2)
    # floor = max(0.5, k * face_px / 256); multipliers and TTA spread
    C2 = m.view_cov(p, 1024.0, tangents=t, multipliers=np.full(7, 2.0), tta_px=np.full(7, 3.0))
    assert np.isclose(C2[2, 0, 0], 2.0 ** 2 * 16 * 4 + 9.0 + (0.6 * 4) ** 2)
    assert np.isclose(C2[5, 0, 0], 0.6 ** 2 * 16 * 4 + 9.0 + (0.4 * 4) ** 2)
    assert np.isclose(C2[3, 0, 0], 2.5 ** 2 * 16 * 4 + 9.0 + (1.5 * 4) ** 2)
    assert np.all(np.isnan(m.view_cov(np.array([np.nan] + [4.0] * 6), 500.0)[0]))
    assert np.allclose(m.sigma_def_mm(), [1.0, 1.0, 1.5, 2.0, 2.0, 0.0, 1.5])


def test_whitening_and_pin_sigma():
    rng = np.random.default_rng(3)
    A = rng.normal(size=(20, 2, 2))
    C = np.einsum("nij,nkj->nik", A, A) + 0.1 * np.eye(2)
    W = whitening(C)
    assert np.allclose(np.triu(W, 1), 0.0)
    assert np.allclose(np.einsum("nji,njk->nik", W, W), np.linalg.inv(C))
    C[3] = np.nan
    assert np.isnan(whitening(C)[3]).all() and np.isfinite(whitening(C)[4]).all()
    with pytest.raises(ValueError):
        whitening(np.array([[[1.0, 2.0], [2.0, 1.0]]]))
    assert np.isclose(pin_sigma_px("crisp_novice", 10.0, 4.0), np.hypot(12.0, 0.25))
    assert np.allclose(pin_sigma_px("palpation", np.array([2.0, 4.0]), 1.0), np.hypot([9.0, 18.0], 1.0))
    with pytest.raises(ValueError):
        pin_sigma_px("crisp_novice", 10.0, 0.0)


# ------------------------------------------------------------------ lm.py
def test_lm_step_solver_project_and_jtj():
    def r(x):
        return np.array([10 * (x[1] - x[0] ** 2), 1 - x[0]])

    def J(x):
        return np.array([[-20 * x[0], 10.0], [-1.0, 0.0]])
    calls = []

    def chol_step(H, lam_diag, g):
        calls.append(1)
        L = np.linalg.cholesky(H + np.diag(lam_diag))
        return -np.linalg.solve(L.T, np.linalg.solve(L, g))
    res = levenberg_marquardt(r, np.array([-1.2, 1.0]), jac=J, max_iter=500, step_solver=chol_step)
    assert calls and np.allclose(res.x, [1, 1], atol=1e-6)
    ref = levenberg_marquardt(r, np.array([-1.2, 1.0]), jac=J, max_iter=500)
    assert np.allclose(res.x, ref.x, atol=1e-9) and res.iterations == ref.iterations
    if res.jtj is not None:
        assert np.allclose(res.jtj, J(res.x).T @ J(res.x))
    # box projection: x0 <= 0.5 is enforced on every trial point
    boxed = levenberg_marquardt(r, np.array([-1.2, 1.0]), jac=J, max_iter=500,
                                project=lambda x: np.array([min(x[0], 0.5), x[1]]))
    assert boxed.x[0] <= 0.5 + 1e-12 and abs(boxed.x[0] - 0.5) < 1e-3
    # convergence by a small gradient at the start: jtj is J^T J at the returned x
    lin = levenberg_marquardt(lambda x: np.array([x[0] - 1.0, 2.0 * x[1]]), np.array([1.0, 0.0]),
                              jac=lambda x: np.array([[1.0, 0.0], [0.0, 2.0]]))
    assert lin.converged and np.allclose(lin.jtj, np.diag([1.0, 4.0]))
    assert levenberg_marquardt(r, np.array([0.0, 0.0]), max_iter=0).jtj is None


# ------------------------------------------------------------------ Jacobians
@pytest.mark.parametrize("indexed", [False, True])
def test_jacobian_with_zeta_factor_prior_and_gauge(monkeypatch, indexed):
    rng = np.random.default_rng(21 + indexed)
    X_true = random_subject(TEMPLATE, NAMES, rng)
    kinds = list(rng.choice(noise.KINDS, size=N))
    cams = [orbit_camera(500.0, yaw, rng.uniform(-8, 8), 26.0) for yaw in (-35, 0, 40)]
    views = []
    for k, c in enumerate(cams):
        uv = c.project(X_true) + rng.normal(scale=2.0, size=(N, 2))
        uv[rigs.visible_mask(c, X_true) == 0] = np.nan
        c0 = c.copy()
        c0.t = c0.t + rng.normal(scale=2.0, size=3)
        kw = dict(f_prior=c.f * 1.05, kinds=kinds, focal_group="phone" if k < 2 else None)
        if k == 0:       # noise model with tangents, multipliers, TTA and dense points
            T = rng.normal(size=(N, 2))
            T[::5] = np.nan
            kw.update(tangents=T, multipliers=rng.uniform(1.0, 2.0, N), tta_px=rng.uniform(0.0, 2.0, N),
                      dense_mask=rng.random(N) < 0.3, weights=rng.uniform(0.5, 1.5, N))
        elif k == 1:     # explicit full covariance
            A = rng.normal(size=(N, 2, 2)) * 3.0
            kw.update(cov_px=np.einsum("nij,nkj->nik", A, A) + np.eye(2))
        else:            # legacy isotropic float
            kw.update(sigma_px=2.5)
        views.append(ViewObs(uv, c0, **kw))
    anchors = [NAMES.index(n) for n in ("endocanthion_L", "endocanthion_R", "exocanthion_L", "exocanthion_R",
                                        "pronasale", "subnasale", "cheilion_L", "cheilion_R")]
    if indexed:
        sub = np.array(sorted(set(anchors) | set(range(0, N, 2))))
        prior = _random_factor_prior(rng, TEMPLATE[sub], index=sub)
    else:
        prior = _random_factor_prior(rng, TEMPLATE)
    pairs = mirror_pairs(NAMES)
    mid = midline_indices(NAMES)
    pri = Priors(pairs=pairs, sigma_sym=rng.uniform(1.0, 3.0, (len(pairs), 3)), midline=mid,
                 sigma_mid=rng.uniform(1.0, 3.0, len(mid)))
    X0 = TEMPLATE + rng.normal(scale=2.0, size=TEMPLATE.shape)
    # zeta = 0.2: a missing e^-zeta factor is an 18 % error, far outside the tolerance.
    zeta0 = 0.2
    cap, res = _capture_closures(monkeypatch, views, X0, pri, prior=prior, scale=ScaleConfig(init=zeta0),
                                 gauge_anchor_idx=anchors)
    fun, jac, retract, x0 = cap["fun"], cap["jac"], cap["retract"], cap["x0"]
    idx = res.param_index
    assert "zeta" in idx and np.isclose(x0[idx["zeta"]][0], zeta0)
    Ja = jac(x0)
    Jn = _numeric_jacobian(fun, retract, x0)
    assert Ja.shape == Jn.shape
    _assert_jacobian_close(Ja, Jn, idx)
    z = idx["zeta"].start
    assert np.abs(Ja[:, z]).max() > 0
    # the six gauge rows exist: rows weighted by 1 / 0.01 mm on the anchor coordinates only
    pts = idx["points"]
    big = np.abs(Ja[:, pts]).max(axis=1) > 1.0 / B.BUNDLE["gauge_sigma_mm"].value * 0.05
    assert big.sum() >= 6
    # Row layout [data | focal priors | zeta prior | shape | symmetry | midline | gauge (6)].
    n_focal = sum(1 for k in idx if k.startswith("focal_"))
    shape0 = res.m_data + n_focal + 1
    n_shape = len(Ja) - shape0 - 3 * len(pairs) - len(mid) - 6
    assert n_shape > 0
    data_rows = np.arange(res.m_data)
    shape_rows = np.arange(shape0, shape0 + n_shape)
    gauge_rows = np.arange(len(Ja) - 6, len(Ja))
    pcols = np.arange(pts.start, pts.stop)
    # The spec-named derivatives are pinned: d/dX = e^-zeta W (shape), e^-zeta G / 0.01 (gauge),
    # d/dzeta = -e^-zeta W X.  The comparison rejects each one with its e^-zeta factor
    # dropped (or with a scaled reprojection block), so a later edit cannot slip through.
    s = np.exp(-zeta0)
    G, _ = B._gauge_rows(prior, N, anchors, X0)
    assert np.allclose(Ja[np.ix_(gauge_rows, pcols)], s * G / B.BUNDLE["gauge_sigma_mm"].value)
    for rows, cols, factor in ((shape_rows, pcols, 1.0 / s), (gauge_rows, pcols, 1.0 / s),
                               (shape_rows, [z], 1.0 / s), (gauge_rows, [z], 1.0 / s),
                               (data_rows, pcols, 1.5), (data_rows, pcols, 1.001)):
        _assert_mutation_detected(Ja, Jn, idx, rows, cols, factor)


def test_jacobian_matches_with_legacy_float_sigma_and_scale(monkeypatch):
    rng = np.random.default_rng(5)
    X_true = random_subject(TEMPLATE, NAMES, rng)
    views = []
    for yaw in (-30, 10, 50):
        c = orbit_camera(450.0, yaw, 3.0, 26.0)
        uv = c.project(X_true) + rng.normal(scale=1.0, size=(N, 2))
        uv[~rigs.visible_mask(c, X_true)] = np.nan
        views.append(ViewObs(uv, c.copy(), f_prior=c.f, sigma_px=1.5))
    zeta0 = -0.2
    cap, res = _capture_closures(monkeypatch, views, TEMPLATE.copy(), _legacy_priors(), huber_px=None,
                                 scale=ScaleConfig(init=zeta0))
    idx = res.param_index
    Ja = cap["jac"](cap["x0"])
    Jn = _numeric_jacobian(cap["fun"], cap["retract"], cap["x0"])
    _assert_jacobian_close(Ja, Jn, idx)
    # Rows [data | 3 focal priors | zeta prior | legacy shape (3N) | symmetry | midline]:
    # the legacy shape term on X~ = e^-zeta X has d/dX = e^-zeta / sigma.
    shape_rows = np.arange(res.m_data + 4, res.m_data + 4 + 3 * N)
    pcols = np.arange(idx["points"].start, idx["points"].stop)
    assert np.allclose(np.diag(Ja[np.ix_(shape_rows, pcols)]), np.exp(-zeta0) / 8.0)
    for rows, cols, factor in ((shape_rows, pcols, np.exp(zeta0)), (shape_rows, [idx["zeta"].start], 1.1),
                               (np.arange(res.m_data), pcols, 1.001)):
        _assert_mutation_detected(Ja, Jn, idx, rows, cols, factor)


# ------------------------------------------------------------------ noise default
def test_default_sigma_from_noise_model():
    assert ViewObs(np.zeros((1, 2)), Camera.centered(1000.0, 10, 10)).sigma_px is None
    R, t = look_at(np.array([0.0, 0.0, 560.0]), np.array([0.0, 0.0, 60.0]))
    cam = Camera.centered(3000.0, 3000, 4000, R=R, t=t)
    m = rigs.visible_mask(cam, TEMPLATE)
    uv = cam.project(TEMPLATE)
    uv[~m] = np.nan
    v = ViewObs(uv, cam.copy())
    z = cam.depth(TEMPLATE)
    assert 440 < np.median(z[m]) < 560
    expected = cam.f / z * 2.0
    C = view_noise_cov(v, TEMPLATE, cam.R, cam.t, cam.f)
    assert np.isnan(C[~m]).all()
    sig = np.sqrt(C[m, 0, 0])
    assert np.allclose(C[m, 0, 0], C[m, 1, 1]) and np.allclose(C[m, 0, 1], 0.0)
    assert np.all(np.abs(sig / expected[m] - 1.0) < 0.10)
    # inside the bundle: the frozen per-view noise of the final round
    rng = np.random.default_rng(0)
    v2 = ViewObs(uv + rng.normal(scale=0.5, size=uv.shape), cam.copy(), estimate_focal=False)
    res = bundle_adjust([v2], TEMPLATE.copy(), _legacy_priors())
    z2 = res.cameras[0].depth(res.X)
    s2 = np.sqrt(res.obs_cov_px[0][m, 0, 0])
    assert np.all(np.abs(s2 / (cam.f / z2[m] * 2.0) - 1.0) < 0.10)


def _chi2_seed(seed, sigma_px=None, outlier_frac=0.0, robust=None):
    """WP-01 detector_sim on the rear_phone rig (legacy kinds, no definition bias) -> (result, obs).

    The bundle starts from the rig's poses with the EXIF focal; its chi2 at convergence
    does not depend on that start (the reconstruct_landmarks PnP start gives the same
    median chi2_red to 3 digits on these seeds).
    """
    r_subj, r_rig, r_det = _seed_streams(seed)
    names, X, meta = subjects.legacy_subject(r_subj)
    rig = rigs.rear_phone(r_rig, X=X)
    kinds = detector_sim.legacy_kinds(names)
    obs = detector_sim.simulate(X, kinds, rig, r_det, outlier_frac=outlier_frac, definition_bias=False)
    views = [ViewObs(uv, cam.copy(), f_prior=rig.f_prior_px[k], f_prior_log_sigma=rig.f_prior_log_sigma[k],
                     focal_group=rig.focal_group[k], kinds=kinds, sigma_px=sigma_px)
             for k, (uv, cam) in enumerate(zip(obs.uv, rig.cameras))]
    for v, f in zip(views, rig.f_prior_px):
        v.camera.f = f                                  # start from the EXIF focal, not the truth
    pri = _legacy_priors(names, meta["template"], LEGACY_PRIOR["sigma"], LEGACY_PRIOR["sigma_sym"],
                         LEGACY_PRIOR["sigma_mid"])
    return bundle_adjust(views, meta["template"].copy(), pri, robust=robust), obs


def _inlier_chi2_red(res, obs):
    """Reduced chi2 over the simulator's inliers only, whitened by the bundle's own final-round
    noise (obs_cov_px): sum r^T C^-1 r / (m_inlier - p_eff).  A test-side stand-in for the
    robust (inlier) chi2 of WP-10."""
    tot, m = 0.0, 0
    for k, cam in enumerate(res.cameras):
        sel = obs.visible[k] & ~obs.outlier_mask[k]
        r = cam.project(res.X[sel]) - obs.uv[k][sel]
        tot += float(np.einsum("ni,nij,nj->", r, np.linalg.inv(res.obs_cov_px[k][sel]), r))
        m += 2 * int(sel.sum())
    return tot / (m - res.p_eff)


def test_reduced_chi2_near_one_with_correct_noise():
    # Outlier-free data: the legacy Huber IRLS chi2_red is near one with the noise model.
    seeds = range(1000, 1010)
    chi = [_chi2_seed(s)[0].chi2_red for s in seeds]
    assert 0.7 <= np.median(chi) <= 1.4, chi
    legacy = [_chi2_seed(s, sigma_px=1.0)[0].chi2_red for s in seeds]
    assert np.median(legacy) > 10.0, legacy
    # The spec's data: detector_sim defaults (5 % outliers at 5-20 sigma), definition bias
    # off.  Updated by WP-10 (integration addendum 2): the robust schedule (DESIGN 4.5)
    # reports chi2_red over the inliers of its final least-squares solve, so it is near one
    # with outliers too.  The test-side inlier chi2 of WP-07 is kept as a cross-check.
    spec = [_chi2_seed(s, outlier_frac=0.05, robust=RobustSchedule()) for s in seeds]
    assert 0.7 <= np.median([r.chi2_red for r, _ in spec]) <= 1.4, [r.chi2_red for r, _ in spec]
    side = [_inlier_chi2_red(*_chi2_seed(s, outlier_frac=0.05)) for s in seeds]
    assert 0.7 <= np.median(side) <= 1.4, side


# ------------------------------------------------------------------ scale and covariance
def test_zeta_prior_limited_without_metric_information():
    prior, mu, X, views, _ = _anatomical_scene(3)
    res = bundle_adjust(views, mu.copy(), None, prior=prior)
    assert res.zeta is not None and abs(res.zeta_sigma / 0.045 - 1.0) < 0.10, res.zeta_sigma
    assert "zeta" in res.param_index and not res.flags
    # unconditional cov carries the scale mode that cov_shape (conditional on zeta) does not
    assert np.trace(res.cov) > np.trace(res.cov_shape)
    # legacy Priors only: zeta stays disabled ('auto'), legacy numerics
    names, T = NAMES, TEMPLATE
    rng = np.random.default_rng(1)
    lv, _ = _sample_views(random_subject(T, names, rng), ["generic"] * N, (-30, 0, 30), rng)
    leg = bundle_adjust(lv, T.copy(), _legacy_priors())
    assert leg.zeta is None and leg.zeta_sigma is None and "zeta" not in leg.param_index
    assert np.array_equal(leg.cov, leg.cov_shape)
    exp = bundle_adjust(lv, T.copy(), _legacy_priors(), scale=ScaleConfig())
    assert exp.zeta is not None and "zeta" in exp.param_index


@pytest.mark.parametrize("path", ["prior", "legacy"])
def test_cov_schur_equals_direct_inverse(path):
    if path == "prior":
        prior, mu, X, views, _ = _anatomical_scene(4)
        res = bundle_adjust(views, mu.copy(), None, prior=prior)
    else:
        rng = np.random.default_rng(4)
        views, _ = _sample_views(random_subject(TEMPLATE, NAMES, rng), ["sharp_junction"] * N, (-40, 0, 40), rng)
        res = bundle_adjust(views, TEMPLATE.copy(), _legacy_priors(), scale=ScaleConfig())
    H = res.H_data + res.H_prior
    H[np.diag_indices_from(H)] += res.cov_ridge
    pts = res.param_index["points"]
    z = res.param_index["zeta"].start
    keep = [i for i in range(len(H)) if i != z]
    direct_shape = np.linalg.inv(H[np.ix_(keep, keep)])[pts.start - 1:, pts.start - 1:]
    direct_cov = np.linalg.inv(H)[pts, pts]
    for got, want in ((res.cov_shape, direct_shape), (res.cov, direct_cov)):
        assert np.linalg.norm(got - want) / np.linalg.norm(want) < 1e-8
        assert np.allclose(got, got.T, rtol=0, atol=1e-12 * np.abs(got).max())
        w = np.linalg.eigvalsh(got)
        assert w.min() > -1e-10 * w.max()
    # camera blocks and zeta come from the same inverse
    Sig = np.linalg.inv(H)
    assert np.isclose(res.zeta_sigma, np.sqrt(Sig[z, z]), rtol=1e-6)
    p0 = res.param_index["pose_0"]
    assert np.allclose(res.camera_cov[0][:6, :6], Sig[p0, p0], rtol=1e-6, atol=1e-12)
    # chi2_red bookkeeping: p_eff = tr(H_data Sigma)
    assert np.isclose(res.p_eff, np.sum(res.H_data * Sig), rtol=1e-6)
    assert 0 < res.p_eff < res.m_data


def test_point_sigma_legacy_semantics():
    rng = np.random.default_rng(8)
    views, _ = _sample_views(random_subject(TEMPLATE, NAMES, rng), ["generic"] * N, (-45, 0, 45), rng)
    for kw in ({}, {"scale": ScaleConfig()}):
        res = bundle_adjust(views, TEMPLATE.copy(), _legacy_priors(), **kw)
        assert res.point_sigma_mm.shape == (N, 3)
        assert np.allclose(res.point_sigma_mm, np.sqrt(np.diag(res.cov_shape)).reshape(N, 3), rtol=1e-12)
    prior, mu, X, pviews, _ = _anatomical_scene(5)
    res = bundle_adjust(pviews, mu.copy(), None, prior=prior)
    assert np.allclose(res.point_sigma_mm, np.sqrt(np.diag(res.cov_shape)).reshape(-1, 3), rtol=1e-12)
    # sigma_rep formula (DESIGN 4.13 without gamma)
    sdef = res.sigma_def_mm
    assert np.allclose(sdef, [noise.KIND_SIGMA_DEF_MM[ANATOMICAL[i].kind] for i in prior.ids])
    infl = max(1.0, res.chi2_red)
    assert np.allclose(res.sigma_rep_mm, np.sqrt(res.point_sigma_mm ** 2 * infl + sdef[:, None] ** 2))


def test_definition_bias_floor_does_not_shrink():
    # Precise observations (explicit 1 px ~ 0.2 mm) of sharp junctions: the posterior
    # shrinks with more views, the reported sigma stays near the 0.5 mm definition floor.
    rng = np.random.default_rng(5)
    X = random_subject(TEMPLATE, NAMES, rng)
    kinds = ["sharp_junction"] * N

    def run(yaws):
        views, vis = [], []
        for yaw in yaws:
            cam = orbit_camera(600.0, yaw, 0.0, 26.0)
            m = rigs.visible_mask(cam, X)
            uv = cam.project(X) + rng.normal(scale=1.0, size=(N, 2))
            uv[~m] = np.nan
            views.append(ViewObs(uv, cam.copy(), f_prior=cam.f, f_prior_log_sigma=0.05, focal_group="g",
                                 kinds=kinds, sigma_px=1.0))
            vis.append(m)
        return bundle_adjust(views, TEMPLATE.copy(), _legacy_priors()), np.array(vis)
    r3, v3 = run((-30, 0, 30))
    r9, v9 = run(tuple(range(-40, 41, 10)))
    for r in (r3, r9):
        assert np.all(r.sigma_def_mm == 0.5)
        assert np.all(r.sigma_rep_mm >= 0.5)
    well = v3.all(0) & v9.all(0)
    assert well.sum() >= 10

    # Gauge-projected (DESIGN 7.3): in the template gauge the marginals of the 8 mm
    # legacy prior are dominated by the prior-fixed similarity, which no view removes.
    def projected(r):
        P = gauge_projector(r.X)
        d = np.maximum(np.diag(P @ r.cov_shape @ P), 0.0).reshape(N, 3)
        post = np.sqrt(np.mean(d, axis=1))
        rep = np.sqrt(np.mean(d * max(1.0, r.chi2_red) + r.sigma_def_mm[:, None] ** 2, axis=1))
        return post, rep
    p3, s3 = projected(r3)
    p9, s9 = projected(r9)
    assert np.median(s9[well] / s3[well]) > 0.8
    assert np.median(p9[well] / p3[well]) < 0.7


def test_nees_with_sigma_def_calibrated():
    yaws = (-60, -40, -20, 0, 20, 40, 60)
    with_def, post_only = [], []
    for seed in range(30):
        rng = np.random.default_rng(100 + seed)
        X = random_subject(TEMPLATE, NAMES, rng)
        bias = rng.normal(scale=1.0, size=X.shape)          # 1 mm, shared by all views (D-06)
        views, vis = _sample_views(X, ["sharp_junction"] * N, yaws, rng, bias=bias)
        res = bundle_adjust(views, TEMPLATE.copy(), _legacy_priors(), sigma_def_mm=np.full(N, 1.0))
        sel = vis.sum(0) >= 3
        s, R, t = umeyama(res.X[sel], X[sel], with_scale=True)
        err = s * res.X[sel] @ R.T + t - X[sel]
        rows = (3 * np.flatnonzero(sel)[:, None] + np.arange(3)).ravel()
        Bk = np.kron(np.eye(int(sel.sum())), R)
        for cov, out in ((res.cov_shape + np.eye(3 * N), with_def), (res.cov_shape, post_only)):
            C = s * s * Bk @ cov[np.ix_(rows, rows)] @ Bk.T
            out.append(nees(err, C, X[sel], project=True)[0])
    assert 0.6 <= np.mean(with_def) <= 1.6, np.mean(with_def)
    assert np.mean(post_only) > 2.0, np.mean(post_only)


def test_cov_singular_falls_back_to_pinv():
    lay = SimpleNamespace(pts_off=2, n=5, zeta_idx=-1)
    H = np.diag([4.0, 1.0, 2.0, -1.0, 3.0])                  # not positive definite
    post = B._posterior(H, lay, 1e-12)
    assert post["flags"] == [B.FLAG_COV_SINGULAR]
    assert np.allclose(post["Sigma"], np.linalg.pinv(H + post["ridge"] * np.eye(5)))
    assert post["cov"].shape == (3, 3)
    ok = B._posterior(np.diag([4.0, 1.0, 2.0, 1.0, 3.0]), lay, 1e-12)
    assert ok["flags"] == [] and np.allclose(np.diag(ok["cov"]), [0.5, 1.0, 1.0 / 3.0])


def _small_scene(seed=2):
    rng = np.random.default_rng(seed)
    views, vis = _sample_views(random_subject(TEMPLATE, NAMES, rng), ["generic"] * N, (-30, 0, 30), rng)
    return views, vis


def test_non_finite_noise_inputs_raise():
    # Regression: a NaN multiplier / TTA spread / weight on a visible landmark used to
    # make every residual NaN, so LM rejected every step and bundle_adjust silently
    # returned X0 with cost NaN and only a COV-SINGULAR flag.
    views, vis = _small_scene()
    i = int(np.flatnonzero(vis[0])[0])
    h = int(np.flatnonzero(~vis[0])[0])
    for field, base in (("multipliers", 1.0), ("tta_px", 0.5), ("weights", 1.0)):
        for bad in (np.nan, np.inf):
            a = np.full(N, base)
            a[i] = bad
            v0 = ViewObs(**{**views[0].__dict__, field: a})
            with pytest.raises(ValueError, match=field):
                bundle_adjust([v0] + views[1:], TEMPLATE.copy(), _legacy_priors())
        # hidden rows may hold anything
        a = np.full(N, base)
        a[h] = np.nan
        v0 = ViewObs(**{**views[0].__dict__, field: a})
        res = bundle_adjust([v0] + views[1:], TEMPLATE.copy(), _legacy_priors())
        assert np.isfinite(res.cost) and not res.flags and np.abs(res.X - TEMPLATE).max() > 0.5
    with pytest.raises(ValueError, match="weights"):
        bundle_adjust([ViewObs(**{**views[0].__dict__, "weights": -np.ones(N)})] + views[1:], TEMPLATE.copy(),
                      _legacy_priors())
    with pytest.raises(ValueError, match="weights"):
        bundle_adjust([ViewObs(**{**views[0].__dict__, "weights": np.ones(N + 1)})] + views[1:], TEMPLATE.copy(),
                      _legacy_priors())
    with pytest.raises(ValueError, match="multipliers"):
        bundle_adjust([ViewObs(**{**views[0].__dict__, "multipliers": np.ones(N - 1)})] + views[1:],
                      TEMPLATE.copy(), _legacy_priors())
    # a non-finite estimate reaching the noise model is reported, not whitened into NaN
    with pytest.raises(ValueError, match="non-finite"):
        view_noise_cov(views[0], np.where(np.arange(N)[:, None] == i, np.nan, TEMPLATE), views[0].camera.R,
                       views[0].camera.t, views[0].camera.f)
    # scalar multipliers / TTA still work
    res = bundle_adjust([ViewObs(**{**views[0].__dict__, "multipliers": 1.5, "tta_px": 0.3})] + views[1:],
                        TEMPLATE.copy(), _legacy_priors())
    assert np.isfinite(res.cost) and not res.flags


def test_sigma_def_validated_and_cov_flag_not_masking_input_errors(monkeypatch):
    # Regression: the covariance block caught every ValueError, so a wrongly shaped
    # sigma_def_mm came back as COV-SINGULAR with no posterior at all, and a negative
    # one was accepted.
    views, _ = _small_scene()
    for bad in (np.ones(N + 1), -np.ones(N), np.full(N, np.nan), np.ones((N, 1)), -1.0, np.inf):
        with pytest.raises(ValueError, match="sigma_def_mm"):
            bundle_adjust(views, TEMPLATE.copy(), _legacy_priors(), sigma_def_mm=bad)
    res = bundle_adjust(views, TEMPLATE.copy(), _legacy_priors(), sigma_def_mm=0.7)
    assert np.all(res.sigma_def_mm == 0.7) and res.sigma_def_mm.shape == (N,) and not res.flags
    assert res.point_sigma_mm is not None and res.cov is not None
    # invalid kinds are an input error too (also with an explicit legacy sigma_px)
    with pytest.raises(ValueError):
        bundle_adjust([ViewObs(**{**views[0].__dict__, "kinds": ["nose"] * N, "sigma_px": 2.0})] + views[1:],
                      TEMPLATE.copy(), _legacy_priors())
    with pytest.raises(ValueError, match="kinds"):
        bundle_adjust([ViewObs(**{**views[0].__dict__, "kinds": ["generic"] * (N - 1), "sigma_px": 2.0})]
                      + views[1:], TEMPLATE.copy(), _legacy_priors())
    # COV-SINGULAR still reports a genuine numerical failure of the covariance
    def failing(H, lay, ridge_rel):
        raise np.linalg.LinAlgError("SVD did not converge")
    monkeypatch.setattr(B, "_posterior", failing)
    res = bundle_adjust(views, TEMPLATE.copy(), _legacy_priors())
    assert res.flags == [B.FLAG_COV_SINGULAR] and res.cov is None

# ------------------------------------------------------------------ reconstruct and baseline
def test_reconstruct_passes_kinds_focal_prior_and_sigma_def(monkeypatch):
    rng = np.random.default_rng(12)
    X = random_subject(TEMPLATE, NAMES, rng)
    kinds = detector_sim.legacy_kinds(NAMES)
    photos, cams = [], []
    for yaw in (-40, 0, 40):
        c = orbit_camera(500.0, yaw, 2.0, 26.0)
        uv = c.project(X) + rng.normal(scale=1.0, size=(N, 2))
        uv[~rigs.visible_mask(c, X)] = np.nan
        photos.append(PhotoLandmarks(uv, c.width, c.height, f_prior_px=c.f * 1.3, kinds=kinds,
                                     focal_group="phone",
                                     focal_prior=SimpleNamespace(f_px=c.f * 1.02, log_sigma=0.002)))
        cams.append(c)
    seen = {}
    orig = B.bundle_adjust

    def spy(views, X0, priors=None, **kw):
        seen.update(views=views, kw=kw)
        return orig(views, X0, priors, **kw)
    import face3d.solve.reconstruct as Rc
    monkeypatch.setattr(Rc, "bundle_adjust", spy)
    res = reconstruct_landmarks(photos, _legacy_priors(), sigma_def_mm=np.full(N, 0.7))
    assert all(v.kinds == kinds and v.sigma_px is None for v in seen["views"])
    assert all(np.isclose(v.f_prior, c.f * 1.02) and v.f_prior_log_sigma == 0.002
               for v, c in zip(seen["views"], cams))
    assert abs(res.cameras[0].f / (cams[0].f * 1.02) - 1) < 0.005
    assert np.all(res.sigma_def_mm == 0.7) and res.zeta is None
    assert seen["kw"]["scale"] == "auto" and seen["kw"]["prior"] is None
    assert photos[0].resolved_sigma_px() > 0.5                       # legacy method kept
    assert res.engine_version == ENGINE_VERSION == "v2"          # WP-10 (spec: ENGINE_VERSION = 'v2')


def test_not_worse_than_baseline():
    base = json.loads(BASELINE.read_text())
    sc = scorecard.build_scorecard([SCENARIOS[n] for n in FAST_SCENARIOS], scorecard.FAST_SEEDS, git_rev="test",
                                   engine_label=ENGINE_VERSION)
    for name in FAST_SCENARIOS:
        pm = scorecard.paired_medians(base, sc, name, "config_rms_mm")
        assert pm is not None and pm["n_ok_new"] >= pm["n_ok_baseline"], (name, pm)
        assert pm["new"] <= 1.1 * pm["baseline"], (name, pm)
