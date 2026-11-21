"""FU-01: follow-up fixes found during WP-15 (WBS FU-01).

1. ``face3d/solve/bundle.py``: with the explicit log-scale zeta enabled, the legacy symmetry
   and midline rows (``Priors.pairs`` / ``Priors.midline``, DESIGN 4.11) act on the scale-free
   X~ = e^-zeta X, like the shape prior (DESIGN D-03, 4.6); with zeta disabled they are the
   WP-07 rows on X in mm, bit for bit.  On X in mm they pulled a weakly measured global scale
   toward small heads (~8 % in WP-15's iris-only scene).
2. ``face3d/solve/noise.py``: a landmark whose image tangent is unknown gets an isotropic
   covariance with variance max(sigma_n^2, sigma_t^2) when its kind's tangent SD is finite
   (extremal: 3.0 mm, DESIGN 4.4), instead of sigma_n^2; the curve-sample kinds whose tangent
   is 'free' (curve, contour, brow) keep the WP-07 orientation average.

Test-bed conventions: the WP-01 legacy 32-point subjects on the ``rear_phone`` rig with the
detector simulator (legacy kinds), started from the rig's poses with the EXIF focal, as in
tests/test_bundle_fixes.py (WP-07).  Head size is the Umeyama log-size relative to the
template (:func:`face3d.solve.scale.log_size`, the test bed's ``log_scale_true`` definition);
its bias is log_size(X_hat) - log_scale_true.
"""
from __future__ import annotations

import numpy as np
import pytest

import face3d.solve.bundle as B
from face3d.solve import noise
from face3d.solve import scale as S
from face3d.solve.bundle import MIRROR, Priors, ScaleConfig, ViewObs, bundle_adjust, view_noise_cov
from face3d.solve.noise import FREE_TANGENT_KINDS, KIND_SIGMA_MM, KINDS, NoiseModel
from face3d.solve.robust import RobustSchedule
from face3d.synthetic import midline_indices, mirror_pairs, orbit_camera, random_subject, synthetic_landmarks
from face3d.testbed import detector_sim, rigs, subjects
from face3d.testbed.scenarios import LEGACY_PRIOR, _seed_streams

NAMES, TEMPLATE = synthetic_landmarks()
N = len(TEMPLATE)
PAIRS = np.asarray(mirror_pairs(NAMES), np.int64).reshape(-1, 2)
MID = np.asarray(midline_indices(NAMES), np.int64)


# =========================================================================== helpers
def _capture_closures(monkeypatch, *args, **kwargs):
    """Run bundle_adjust with a zero-iteration LM shim; return its closures and the result."""
    captured = {}
    orig = B.levenberg_marquardt

    def shim(fun, x0, jac=None, retract=None, **kw):
        captured.update(fun=fun, jac=jac, retract=retract, x0=np.array(x0, float))
        return orig(fun, x0, jac=jac, retract=retract, max_iter=0)
    monkeypatch.setattr(B, "levenberg_marquardt", shim)
    res = bundle_adjust(*args, **kwargs)
    return captured, res


def _numeric_rows(fun, retract, x0, rows, h=1e-3):
    """Central differences through ``retract`` with one Richardson step (O(h^4)), rows only."""
    def central(hh):
        Jn = np.zeros((len(rows), len(x0)))
        for j in range(len(x0)):
            e = np.zeros(len(x0))
            e[j] = hh
            Jn[:, j] = (fun(retract(x0, e))[rows] - fun(retract(x0, -e))[rows]) / (2 * hh)
        return Jn
    return (4.0 * central(h / 2) - central(h)) / 3.0


def _blocks(param_index):
    return {k: sl for k, sl in param_index.items() if k != "cameras"}


def _block_close(Ja, Jn, param_index, rtol=1e-7):
    """Strict per-block comparison: |Ja - Jn| <= rtol (|Jn| + max |Jn| over the row's block),
    and both exactly zero wherever the numeric block of a row is (to 1e-12 absolute)."""
    ok = np.ones(Ja.shape, bool)
    for sl in _blocks(param_index).values():
        a, n = Ja[:, sl], Jn[:, sl]
        scale = np.abs(n).max(axis=1, keepdims=True)
        ok[:, sl] = np.abs(a - n) <= rtol * (np.abs(n) + scale) + 1e-12
    return ok


def _scene(rng, yaws=(-35.0, 0.0, 40.0)):
    X_true = random_subject(TEMPLATE, NAMES, rng)
    views = []
    for k, yaw in enumerate(yaws):
        c = orbit_camera(500.0, yaw, rng.uniform(-8, 8), 26.0)
        uv = c.project(X_true) + rng.normal(scale=2.0, size=(N, 2))
        uv[~rigs.visible_mask(c, X_true)] = np.nan
        c0 = c.copy()
        c0.t = c0.t + rng.normal(scale=2.0, size=3)
        views.append(ViewObs(uv, c0, f_prior=c.f * 1.05, kinds=["generic"] * N,
                             focal_group="phone" if k < 2 else None))
    return views


def _sym_priors(rng, per_axis=True):
    ss = rng.uniform(1.0, 3.0, (len(PAIRS), 3)) if per_axis else 2.0
    sm = rng.uniform(1.0, 3.0, len(MID)) if per_axis else 1.5
    return Priors(mean=TEMPLATE, sigma=8.0, pairs=[tuple(p) for p in PAIRS], sigma_sym=ss, midline=list(MID),
                  sigma_mid=sm)


def _expected_rows(X, zeta, pri):
    """(sym rows (3P,), mid rows (M,)) of DESIGN 4.11 on X~ = e^-zeta X (zeta None: on X)."""
    Xt = X if zeta is None else np.exp(-zeta) * X
    S_sym = np.broadcast_to(np.asarray(pri.sigma_sym, float), (len(PAIRS), 3))
    S_mid = np.broadcast_to(np.asarray(pri.sigma_mid, float), (len(MID),))
    return ((Xt[PAIRS[:, 0]] - Xt[PAIRS[:, 1]] * MIRROR) / S_sym).ravel(), Xt[MID, 0] / S_mid


# =========================================================================== 1. symmetry / midline rows
@pytest.mark.parametrize("with_factor_prior", [False, True])
def test_symmetry_midline_rows_on_scale_free_points_jacobian(monkeypatch, with_factor_prior):
    """Strict per-block analytic vs numeric Jacobian of the symmetry and midline rows with zeta on.

    Rows [data | focal priors | zeta prior | shape | symmetry (3P) | midline (M) | gauge (6)?].
    The values are (X~_l - M X~_r) / sigma_sym and X~_mid,x / sigma_mid with X~ = e^-zeta X
    (zeta = 0.2, so a missing e^-zeta factor is an 18 % error); d/dX = e^-zeta x the legacy
    row, d/dzeta = -(the residual), zero on every camera / focal block."""
    rng = np.random.default_rng(11 + with_factor_prior)
    views = _scene(rng)
    pri = _sym_priors(rng)
    kw = {}
    n_gauge = 0
    if with_factor_prior:
        from face3d.model.landmark_prior import FactorPrior
        m = 3 * N
        L = rng.normal(scale=2.0, size=(m, 3))
        A = rng.normal(size=(m, m))
        R = A @ A.T / m + np.diag(rng.uniform(1.0, 4.0, m))
        kw["prior"] = FactorPrior(TEMPLATE, L, R, meta={"rigid_invariant": True, "source": "test", "badge": "🆕"})
        pri = Priors(pairs=pri.pairs, sigma_sym=pri.sigma_sym, midline=pri.midline, sigma_mid=pri.sigma_mid)
        n_gauge = 6
    zeta0 = 0.2
    X0 = TEMPLATE + rng.normal(scale=2.0, size=TEMPLATE.shape)
    cap, res = _capture_closures(monkeypatch, views, X0, pri, scale=ScaleConfig(init=zeta0), **kw)
    fun, jac, retract, x0 = cap["fun"], cap["jac"], cap["retract"], cap["x0"]
    idx = res.param_index
    z = idx["zeta"].start
    pts = idx["points"]
    assert np.isclose(x0[z], zeta0)
    X = x0[pts].reshape(N, 3)
    r = fun(x0)
    P, M = len(PAIRS), len(MID)
    off = len(r) - n_gauge - 3 * P - M
    sym_rows = np.arange(off, off + 3 * P)
    mid_rows = np.arange(off + 3 * P, off + 3 * P + M)
    e_sym, e_mid = _expected_rows(X, zeta0, pri)
    assert np.allclose(r[sym_rows], e_sym, rtol=1e-13, atol=1e-13)
    assert np.allclose(r[mid_rows], e_mid, rtol=1e-13, atol=1e-13)
    # analytic closed forms
    Ja = jac(x0)
    s = np.exp(-zeta0)
    Jx = np.zeros((3 * P + M, 3 * N))
    S_sym = np.asarray(pri.sigma_sym, float)
    for a, (l, rr) in enumerate(PAIRS):
        for c in range(3):
            Jx[3 * a + c, 3 * l + c] += s / S_sym[a, c]
            Jx[3 * a + c, 3 * rr + c] -= MIRROR[c] * s / S_sym[a, c]
    Jx[3 * P + np.arange(M), 3 * MID] = s / np.asarray(pri.sigma_mid, float)
    rows = np.concatenate([sym_rows, mid_rows])
    assert np.allclose(Ja[np.ix_(rows, np.arange(pts.start, pts.stop))], Jx, rtol=1e-13, atol=1e-15)
    assert np.allclose(Ja[rows, z], -np.concatenate([e_sym, e_mid]), rtol=1e-13, atol=1e-15)
    other = np.ones(Ja.shape[1], bool)
    other[pts] = False
    other[z] = False
    assert not np.any(Ja[np.ix_(rows, np.flatnonzero(other))])
    # strict per-block comparison against central differences through the closures
    Jn = _numeric_rows(fun, retract, x0, rows)
    ok = _block_close(Ja[rows], Jn, idx)
    assert ok.all(), (int((~ok).sum()), np.argwhere(~ok)[:3].tolist())
    # the comparison is sharp: dropping e^-zeta on either block, or flipping the zeta column, fails
    pc = np.arange(pts.start, pts.stop)
    for cols, factor in ((pc, 1.0 / s), ([z], 1.0 / s), ([z], -1.0), (pc, 1.0 + 1e-5)):
        Jm = Ja[rows].copy()
        Jm[:, cols] *= factor
        assert not _block_close(Jm, Jn, idx).all()


def test_symmetry_midline_rows_bit_identical_without_zeta(monkeypatch):
    """zeta disabled (legacy Priors, scale 'auto' or None): the rows are the WP-07 rows on X in
    mm, bit for bit (residuals and Jacobian compared with np.array_equal)."""
    rng = np.random.default_rng(5)
    views = _scene(rng)
    for per_axis in (False, True):
        pri = _sym_priors(rng, per_axis)
        for scale in ("auto", None):
            X0 = TEMPLATE + rng.normal(scale=2.0, size=TEMPLATE.shape)
            cap, res = _capture_closures(monkeypatch, views, X0, pri, scale=scale)
            assert res.zeta is None and "zeta" not in res.param_index
            fun, jac, x0 = cap["fun"], cap["jac"], cap["x0"]
            pts = res.param_index["points"]
            X = x0[pts].reshape(N, 3)
            P, M = len(PAIRS), len(MID)
            r = fun(x0)
            Ja = jac(x0)
            rows = np.arange(len(r) - 3 * P - M, len(r))
            S_sym = np.broadcast_to(np.asarray(pri.sigma_sym, float).reshape(-1, 1) if np.ndim(pri.sigma_sym) == 1
                                    else np.asarray(pri.sigma_sym, float), (P, 3)).copy()
            S_mid = np.broadcast_to(np.asarray(pri.sigma_mid, float), (M,)).copy()
            # the WP-07 expressions verbatim
            ref_r = np.concatenate([((X[PAIRS[:, 0]] - X[PAIRS[:, 1]] * MIRROR) / S_sym).ravel(), X[MID, 0] / S_mid])
            ref_J = np.zeros((3 * P + M, len(x0)))
            a = np.arange(P)
            po = pts.start
            for c in range(3):
                ref_J[3 * a + c, po + 3 * PAIRS[:, 0] + c] += 1.0 / S_sym[:, c]
                ref_J[3 * a + c, po + 3 * PAIRS[:, 1] + c] -= MIRROR[c] / S_sym[:, c]
            ref_J[3 * P + np.arange(M), po + 3 * MID] = 1.0 / S_mid
            assert np.array_equal(r[rows], ref_r)
            assert np.array_equal(Ja[rows], ref_J)


class _MmSymmetry:
    """The pre-FU-01 rows: symmetry and midline on X in mm, as a prior Term (test emulation of
    the defect, to show the regression scene detects it)."""

    is_prior = True
    name = "mm_symmetry"

    def __init__(self, sigma_sym, sigma_mid):
        self.ss, self.sm = float(sigma_sym), float(sigma_mid)

    def n_params(self):
        return 0

    def init_params(self, state):
        return np.zeros(0)

    def residuals(self, state, p):
        X = state.X
        return np.concatenate([((X[PAIRS[:, 0]] - X[PAIRS[:, 1]] * MIRROR) / self.ss).ravel(), X[MID, 0] / self.sm])

    def jacobian(self, state, p):
        P, M = len(PAIRS), len(MID)
        J = np.zeros((3 * P + M, 3 * len(state.X)))
        a = np.arange(P)
        for c in range(3):
            J[3 * a + c, 3 * PAIRS[:, 0] + c] += 1.0 / self.ss
            J[3 * a + c, 3 * PAIRS[:, 1] + c] -= MIRROR[c] / self.ss
        J[3 * P + np.arange(M), 3 * MID] = 1.0 / self.sm
        return {"X": J}


def _iris_scene(seed):
    """Legacy subject on the rear_phone rig (detector_sim, legacy kinds, outlier-free) with
    iris-diameter observations (D ~ N(11.8, 0.6^2) mm, 1 px noise; DESIGN 4.7)."""
    r_subj, r_rig, r_det = _seed_streams(seed)
    names, X_true, meta = subjects.legacy_subject(r_subj)
    assert list(names) == list(NAMES)
    rig = rigs.rear_phone(r_rig, X=X_true)
    kinds = detector_sim.legacy_kinds(names)
    obs = detector_sim.simulate(X_true, kinds, rig, r_det, outlier_frac=0.0)
    eye = {"L": names.index("pupil_L"), "R": names.index("pupil_R")}
    rng = np.random.default_rng(seed + 7)
    D = 11.8 + rng.normal(scale=0.6)
    iobs = [(k, e, cam.f * D / cam.depth(X_true[i][None])[0] + rng.normal(scale=1.0), 1.0)
            for k, cam in enumerate(rig.cameras) for e, i in eye.items() if np.isfinite(obs.uv[k][i, 0])]
    assert all(S.iris_usable(o[2], True, False) for o in iobs)

    def views():
        vs = [ViewObs(uv, cam.copy(), f_prior=rig.f_prior_px[k], f_prior_log_sigma=rig.f_prior_log_sigma[k],
                      focal_group=rig.focal_group[k], kinds=kinds) for k, (uv, cam) in enumerate(zip(obs.uv, rig.cameras))]
        for v, f in zip(vs, rig.f_prior_px):
            v.camera.f = f                                  # start from the EXIF focal, not the truth
        return vs
    return views, iobs, eye, meta


@pytest.mark.parametrize("cue", ["iris_free_zeta", "population_only"])
def test_symmetry_rows_do_not_bias_head_size(cue):
    """Head-size bias with the symmetry / midline rows on stays within the no-symmetry-rows bias
    +- 1 % (log units), per seed.

    * ``iris_free_zeta``: the only metric cue is the iris (IrisTerm, flat zeta prior; the WP-15
      iris-only scene).  Before FU-01 the mm-space rows pulled the head 2.7-4.3 % smaller here
      (8 % in WP-15's reconstruct_landmarks run); emulated below by the same rows as a Term on
      X in mm, which this scene must flag (< -2 % each seed).
    * ``population_only``: no metric cue, zeta ~ N(0, 0.045^2) (DESIGN D-03).  The rows still
      regularise the shape X~ (~ -0.5 % here), no longer the scale (mm rows: ~ -2.8 %).
    """
    for seed in (3000, 3001, 3002):
        views, iobs, eye, meta = _iris_scene(seed)
        T = meta["template"]
        src = None if cue == "iris_free_zeta" else "global_size"
        bias = {}
        for mode in ("none", "rows", "mm_rows"):
            sc, extra = S.population_scale_setup(src)
            vs = views()
            terms = list(extra)
            if cue == "iris_free_zeta":
                terms.append(S.IrisTerm(iobs, eye, phi_keys=S.focal_phi_keys(vs)))
            if mode == "rows":
                pri = Priors(mean=T, sigma=LEGACY_PRIOR["sigma"], pairs=[tuple(p) for p in PAIRS],
                             sigma_sym=LEGACY_PRIOR["sigma_sym"], midline=list(MID), sigma_mid=LEGACY_PRIOR["sigma_mid"])
            else:
                pri = Priors(mean=T, sigma=LEGACY_PRIOR["sigma"])
            if mode == "mm_rows":
                terms.append(_MmSymmetry(LEGACY_PRIOR["sigma_sym"], LEGACY_PRIOR["sigma_mid"]))
            res = bundle_adjust(vs, T.copy(), pri, scale=sc, terms=terms)
            assert res.zeta is not None and np.all(np.isfinite(res.X))
            bias[mode] = S.log_size(res.X, T) - float(meta["log_scale_true"])
        assert abs(bias["rows"] - bias["none"]) < 0.01, (seed, bias)
        assert bias["mm_rows"] - bias["none"] < -0.02, (seed, bias)


# =========================================================================== 2. unknown-tangent noise
def test_extremal_without_tangent_covers_sigma_t():
    """Unknown tangent (None, NaN or zero): an extremal point's covariance is isotropic with both
    eigenvalues >= (p sigma_t)^2 (DESIGN 4.4 extremal 2.0 / 3.0 mm), also through the bundle's
    per-observation noise resolution; with a known tangent it is unchanged (normal 2.0, tangent 3.0)."""
    sn, st = KIND_SIGMA_MM["extremal"]
    assert (sn, st) == (2.0, 3.0)
    m = NoiseModel(["extremal"] * 4)
    p = np.array([4.0, 6.0, 9.0, 2.5])                              # px per mm
    for tangents in (None, np.full((4, 2), np.nan), np.zeros((4, 2)), np.array([[np.nan, 1.0]] * 4)):
        C = m.view_cov(p, 400.0, tangents=tangents)
        w = np.linalg.eigvalsh(C)
        assert np.all(w >= (p * st)[:, None] ** 2 * (1 - 1e-12)), w
        floor2 = m.floor_px(400.0) ** 2
        assert np.allclose(C, np.eye(2) * ((p * st) ** 2 + floor2)[:, None, None])
    # known tangent: anisotropic, WP-07 behaviour unchanged
    t = np.array([[1.0, 0.0], [0.0, 2.0], [3.0, 4.0], [-1.0, 1.0]])
    C = m.view_cov(p, None, tangents=t)
    tu = t / np.linalg.norm(t, axis=1, keepdims=True)
    nu = np.column_stack([-tu[:, 1], tu[:, 0]])
    f2 = noise.FLOOR_MIN_PX ** 2
    assert np.allclose(np.einsum("ni,nij,nj->n", tu, C, tu), (p * st) ** 2 + f2)
    assert np.allclose(np.einsum("ni,nij,nj->n", nu, C, nu), (p * sn) ** 2 + f2)
    # multipliers and dense inflation scale the fallback like the anisotropic covariance
    md = NoiseModel(["extremal"] * 4, dense_mask=[True, False, False, False], n_total=160)
    C2 = md.view_cov(p, None, multipliers=np.full(4, 1.5))
    eta = np.array([2.0, 1.0, 1.0, 1.0])
    assert np.allclose(C2[:, 0, 0], (p * st * 1.5) ** 2 * eta + f2)
    # the bundle's per-observation covariance (noise model at each point's depth, no tangents)
    cam = orbit_camera(500.0, 10.0, 0.0, 26.0)
    uv = cam.project(TEMPLATE)
    view = ViewObs(uv, cam, kinds=["extremal"] * N)
    Cv = view_noise_cov(view, TEMPLATE, cam.R, cam.t, cam.f)
    ppm = cam.f / cam.depth(TEMPLATE)
    w = np.linalg.eigvalsh(Cv)
    assert np.all(w >= (ppm * st)[:, None] ** 2), (w.min(axis=1) / (ppm * st) ** 2).min()


def test_unknown_tangent_rule_by_kind():
    """max(sigma_n^2, sigma_t^2) for kinds with a finite tangent SD; the WP-07 orientation
    average for the 'free'-tangent curve-sample kinds (curve, contour, brow), config overrides
    honoured."""
    assert FREE_TANGENT_KINDS == frozenset({"curve", "contour", "brow"})
    m = NoiseModel(list(KINDS))
    for k, s_iso in zip(KINDS, m.sigma_iso_mm):
        sn, st = KIND_SIGMA_MM[k]
        want = np.sqrt(0.5 * (sn ** 2 + st ** 2)) if k in FREE_TANGENT_KINDS else max(sn, st)
        assert np.isclose(s_iso, want), (k, s_iso, want)
    # values: unchanged where sigma_n = sigma_t; extremal 2.0 -> 3.0 mm; hair 6.32 -> 8.0 mm
    got = dict(zip(KINDS, m.sigma_iso_mm))
    assert np.isclose(got["sharp_junction"], 1.25) and np.isclose(got["iris"], 0.6) and np.isclose(got["generic"], 2.0)
    assert np.isclose(got["extremal"], 3.0) and np.isclose(got["hair"], 8.0)
    assert np.isclose(got["curve"], np.sqrt((1.5 ** 2 + 7.5 ** 2) / 2))
    C = m.view_cov(np.ones(len(KINDS)), None)
    assert np.allclose(C[:, 0, 0], m.sigma_iso_mm ** 2 + noise.FLOOR_MIN_PX ** 2)
    assert np.allclose(C[:, 0, 1], 0.0)
    # config overrides: a tangent SD below the normal SD falls back to sigma_n
    from face3d.core import config
    cfg = config.resolve({"noise": {"extremal_sigma_n_mm": 2.5, "extremal_sigma_t_mm": 1.0}})
    assert np.isclose(NoiseModel(["extremal"], cfg=cfg).sigma_iso_mm[0], 2.5)
    with pytest.raises(ValueError):
        noise.unknown_tangent_var_mm2(["extremal"], np.ones((2, 2)))


def _chi2_red(seed, tangents, robust=None, outlier_frac=0.0):
    """The WP-07 chi^2 scene (tests/test_bundle_fixes._chi2_seed) with or without the simulator's
    tangents: legacy kinds, rear_phone rig, definition bias off."""
    r_subj, r_rig, r_det = _seed_streams(seed)
    names, X, meta = subjects.legacy_subject(r_subj)
    rig = rigs.rear_phone(r_rig, X=X)
    kinds = detector_sim.legacy_kinds(names)
    obs = detector_sim.simulate(X, kinds, rig, r_det, outlier_frac=outlier_frac, definition_bias=False)
    views = [ViewObs(uv, cam.copy(), f_prior=rig.f_prior_px[k], f_prior_log_sigma=rig.f_prior_log_sigma[k],
                     focal_group=rig.focal_group[k], kinds=kinds, tangents=obs.tangent_dirs if tangents else None)
             for k, (uv, cam) in enumerate(zip(obs.uv, rig.cameras))]
    for v, f in zip(views, rig.f_prior_px):
        v.camera.f = f
    T = meta["template"]
    pri = Priors(mean=T, sigma=LEGACY_PRIOR["sigma"], pairs=mirror_pairs(names), sigma_sym=LEGACY_PRIOR["sigma_sym"],
                 midline=midline_indices(names), sigma_mid=LEGACY_PRIOR["sigma_mid"])
    return bundle_adjust(views, T.copy(), pri, robust=robust).chi2_red


def test_unknown_tangent_fallback_is_conservative():
    """On the WP-07 chi^2 scene the tangent-free noise is an upper bound: per seed chi2_red
    without tangents <= chi2_red with the simulator's tangents, median in [0.5, 1.0] (the extremal
    points, a third of the legacy set, are now over- rather than under-covered); with tangents the
    WP-07 band [0.7, 1.4] holds (tests/test_bundle_fixes.py)."""
    seeds = range(1000, 1010)
    with_t = np.array([_chi2_red(s, True) for s in seeds])
    without = np.array([_chi2_red(s, False) for s in seeds])
    assert np.all(without <= with_t * 1.02), np.c_[without, with_t]
    assert 0.5 <= np.median(without) <= 1.0, without
    assert 0.7 <= np.median(with_t) <= 1.4, with_t
    rob = [_chi2_red(s, False, RobustSchedule(), 0.05) for s in list(seeds)[:5]]
    assert 0.45 <= np.median(rob) <= 1.0, rob
