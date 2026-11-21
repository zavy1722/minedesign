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


# =========================================================================== FU-04: image tangents
# WBS FU-04: tangents derived from the detections (scheme neighbour chords), the direction-confidence
# covariance, and the recalibrated single-view thresholds (mirror gap / g_min, expression re-tag).
def test_fu04_tangent_direction_confidence_covariance():
    """An (N, 3) tangent (t_x, t_y, rho) is a direction known with mean resultant length rho: the covariance
    is the exact second moment E[R(delta) diag(sn^2, st^2) R(delta)^T] with E[cos 2 delta] = rho, checked
    by Monte Carlo; an (N, 2) tangent is exact whatever its length (pre-FU-04 behaviour; review finding: a
    length < 1 used to be read as a confidence); rho -> 0 tends to the orientation average; an unknown
    tangent keeps the FU-01 rule."""
    sn, st = KIND_SIGMA_MM["curve"]
    m = NoiseModel(["curve"])
    f2 = noise.FLOOR_MIN_PX ** 2
    t = np.array([[np.cos(0.3), np.sin(0.3)]])
    C1 = m.view_cov([2.0], None, tangents=t)[0]
    for length in (7.5, 0.3, 1e-6):                                               # (N, 2): exact, any length
        assert np.allclose(m.view_cov([2.0], None, tangents=length * t)[0], C1)
    assert np.allclose(m.view_cov([2.0], None, tangents=np.column_stack([3.0 * t, [1.0]]))[0], C1)
    for sd in (0.1, 0.35, 0.8):
        rho = np.exp(-2.0 * sd ** 2)
        C = m.view_cov([2.0], None, tangents=np.column_stack([t, [rho]]))[0] - f2 * np.eye(2)
        rng = np.random.default_rng(5)
        d = rng.normal(0.0, sd, 200000) + 0.3
        tt = np.column_stack([np.cos(d), np.sin(d)])
        nn = np.column_stack([-tt[:, 1], tt[:, 0]])
        mc = 4.0 * (st ** 2 * np.einsum("ni,nj->ij", tt, tt) + sn ** 2 * np.einsum("ni,nj->ij", nn, nn)) / len(d)
        assert np.allclose(C, mc, rtol=0.02, atol=0.02 * 4.0 * st ** 2), (sd, C, mc)
        # never tighter across the curve than with the exact tangent, same trace
        n0 = np.array([-t[0, 1], t[0, 0]])
        assert n0 @ C @ n0 > n0 @ (C1 - f2 * np.eye(2)) @ n0 and np.isclose(np.trace(C), 4.0 * (sn ** 2 + st ** 2))
    C0 = m.view_cov([2.0], None, tangents=np.column_stack([t, [1e-9]]))[0] - f2 * np.eye(2)
    assert np.allclose(C0, np.eye(2) * 2.0 * (sn ** 2 + st ** 2), rtol=1e-6, atol=1e-5)   # orientation average
    # unknown: zero / non-finite direction, or non-positive / non-finite rho
    iso = m.view_cov([2.0], None)[0]
    for bad in ([[0.0, 0.0, 1.0]], [[np.nan, 1.0, 1.0]], [[1.0, 0.0, 0.0]], [[1.0, 0.0, np.nan]]):
        assert np.allclose(m.view_cov([2.0], None, tangents=np.array(bad))[0], iso)
    assert np.allclose(noise.tangent_rho(np.array([[3.0, 4.0], [0.3, 0.4], [0.0, 0.0], [np.nan, 1.0]])),
                       [1.0, 1.0, np.nan, np.nan], equal_nan=True)
    assert np.allclose(noise.tangent_rho(np.array([[3.0, 4.0, 0.5], [0.3, 0.4, 2.0], [1.0, 0.0, 0.0]])),
                       [0.5, 1.0, np.nan], equal_nan=True)
    with pytest.raises(ValueError):
        m.view_cov([2.0], None, tangents=np.ones((1, 4)))


def test_fu04_review_free_tangent_kinds_do_not_leak_into_the_normal():
    """Review finding (minor): for contour / brow the tangent SD (1000 / 40 mm) encodes 'free'; with a
    direction confidence rho < 1 it leaked into the normal (contour: 158 mm across the curve at
    rho = 0.95), so a detection-derived tangent removed the point's information.  The leakage now uses the
    finite slide spread ``noise.free_tangent_leak_mm``; the tangent itself stays free."""
    from face3d.core import config as cfg
    kinds = ["contour", "brow", "curve"]
    m = NoiseModel(kinds)
    leak = noise.NOISE["free_tangent_leak_mm"].value
    assert leak == 7.5 and "FU-04" in cfg.get("noise.free_tangent_leak_mm").source
    assert noise.FREE_ENCODED_KINDS == {"contour", "brow"}
    f2 = noise.FLOOR_MIN_PX ** 2
    prev = None
    for rho in (1.0, 0.99, 0.95, 0.9, 0.5):
        C = m.view_cov(np.ones(3), None, tangents=np.array([[1.0, 0.0, rho]] * 3)) - f2 * np.eye(2)
        sd_n, sd_t = np.sqrt(C[:, 1, 1]), np.sqrt(C[:, 0, 0])
        for k, kind in enumerate(kinds):
            sn, st = KIND_SIGMA_MM[kind]
            exp_n = np.sqrt(sn ** 2 + 0.5 * (1 - rho) * (min(st, leak) ** 2 - sn ** 2))
            assert np.isclose(sd_n[k], exp_n), (kind, rho, sd_n[k])
            assert sd_n[k] <= leak                              # bounded: never the 'free' encoding
        assert np.isclose(sd_t[0], 1000.0) and np.isclose(sd_t[1], 40.0)            # the tangent stays free
        assert prev is None or np.all(sd_n >= prev - 1e-12)                         # monotone in the uncertainty
        prev = sd_n
    # was 158 / 7.47 mm at rho = 0.95
    C = m.view_cov(np.ones(3), None, tangents=np.array([[1.0, 0.0, 0.95]] * 3)) - f2 * np.eye(2)
    assert np.sqrt(C[0, 1, 1]) < 2.8 and np.sqrt(C[1, 1, 1]) < 4.2


def test_fu04_image_tangents_from_detections():
    """``image_tangents``: rows (t_x, t_y, rho): the unit chord between the detected neighbours and its
    direction confidence rho = exp(-2 (sa^2 + sb^2) / L^2); unknown (NaN) without a pair, with a hidden point
    or neighbour, a zero-length chord or rho below ``noise.tangent_min_rho``."""
    uv = np.array([[0.0, 0.0], [40.0, 30.0], [20.0, 16.0], [5.0, 5.0], [np.nan, np.nan], [6.0, 5.0]])
    pairs = np.array([[-1, -1], [-1, -1], [0, 1], [0, 4], [0, 1], [3, 5]])
    T = noise.image_tangents(uv, pairs, 2.0)
    rho = np.exp(-2.0 * 8.0 / 2500.0)
    assert T.shape == (6, 3)
    assert np.allclose(T[2], [0.8, 0.6, rho]) and np.isnan(T[[0, 1, 3, 4]]).all()
    assert np.isnan(T[5]).all()                                    # 1 px chord against 2 px noise
    assert np.allclose(noise.image_tangents(uv, pairs)[5], [1.0, 0.0, 1.0])          # no noise given: exact
    assert np.allclose(noise.image_tangents(uv, pairs, 2.0, min_rho=0.0)[5], [1.0, 0.0, np.exp(-16.0)])
    assert noise.TANGENT_MIN_RHO == noise.NOISE["tangent_min_rho"].value == 0.5
    with pytest.raises(ValueError):
        noise.image_tangents(uv, pairs[:3])
    with pytest.raises(ValueError):
        noise.image_tangents(uv, np.array([[0, 9]] * 6))
    # the function reads nothing but uv: the same detections give the same tangents
    assert np.array_equal(T, noise.image_tangents(uv.copy(), pairs.copy(), 2.0), equal_nan=True)


def test_fu04_scheme_tangent_metadata():
    """anatomical44 carries the neighbour metadata (key ``tangents``; backwards compatible: the scheme
    still loads, and schemes without the key give no tangents); every listed point is a curve or extremal
    landmark, pairs are mirror-consistent, and the id-mapped form follows the caller's point order."""
    from face3d.model.registry import ANATOMICAL, load_scheme
    sc = load_scheme("anatomical44")
    meta = sc.raw["tangents"]
    assert meta["badge"] == "\U0001F195" and "provisional" in meta["status"]
    P = noise.scheme_tangent_pairs(sc)
    assert P.shape == (44, 2) and (noise.scheme_tangent_pairs(load_scheme("legacy_synthetic")) == -1).all()
    ids = [p.anatomical_id for p in sc.points]
    has = (P >= 0).all(axis=1)
    assert set(np.array(ids)[has]) == set(meta["neighbours"])
    assert {ANATOMICAL[i].kind for i in np.array(ids)[has]} == {"curve", "extremal"}
    assert not any(ANATOMICAL[i].kind in ("sharp_junction", "iris", "hair") for i in np.array(ids)[has])
    pi = sc.mirror_permutation()
    for i in np.flatnonzero(has):                    # the mirrored point uses the mirrored neighbours
        assert has[pi[i]] and set(pi[P[i]]) == set(P[pi[i]])
    assert ids[P[ids.index("ls")][0]] == "ch_R" and ids[P[ids.index("n")][1]] == "prn"
    # caller's order (the pipeline's engine point list); points or neighbours not in the list: none
    sub = ["ch_L", "ls", "ch_R", "n", "g"]
    Q = noise.scheme_tangent_pairs(sc, sub)
    assert Q.tolist() == [[-1, -1], [2, 0], [-1, -1], [-1, -1], [-1, -1]]
    bad = dict(sc.raw)
    bad["tangents"] = {"neighbours": {"ls": ["ch_L", "nope"]}}
    with pytest.raises(ValueError):
        noise.scheme_tangent_pairs(bad)


def test_fu04_reconstruct_passes_detection_tangents():
    """``PhotoLandmarks.tangents`` reaches the bundle: with tangents from ``photo_tangents`` (the photos'
    own detections) the declared covariance of a curve point is sigma_n across / sigma_t along its chord
    (with the direction-confidence term), and without them the pre-FU-04 isotropic fallback; the solve
    runs either way."""
    from face3d.model.landmark_prior import FactorPrior
    from face3d.model.registry import ANATOMICAL, load_scheme
    from face3d.solve.reconstruct import PhotoLandmarks, photo_tangents, reconstruct_landmarks
    sc = load_scheme("anatomical44")
    ids = [p.anatomical_id for p in sc.points]
    kinds = [ANATOMICAL[i].kind for i in ids]
    prior = FactorPrior.from_package()
    X = prior.mean()
    pairs = noise.scheme_tangent_pairs(sc)
    cams = [orbit_camera(700.0, yaw, 5.0, 50.0, target=(0.0, -20.0, 60.0)) for yaw in (-35.0, 0.0, 35.0)]
    rng = np.random.default_rng(3)
    photos, plain = [], []
    for cam in cams:
        uv = cam.project(X) + rng.normal(0.0, 0.3, (len(X), 2))
        tg = photo_tangents(uv, kinds, pairs, X_ref=X)
        photos.append(PhotoLandmarks(uv, cam.width, cam.height, f_prior_px=cam.f, f_prior_log_sigma=0.05,
                                     focal_group="a", kinds=kinds, tangents=tg))
        plain.append(PhotoLandmarks(uv, cam.width, cam.height, f_prior_px=cam.f, f_prior_log_sigma=0.05,
                                    focal_group="a", kinds=kinds))
    tg = photos[1].tangents
    i = ids.index("ls")
    chord = photos[1].uv[ids.index("ch_L")] - photos[1].uv[ids.index("ch_R")]
    rho = tg[i, 2]
    assert tg.shape == (44, 3) and 0.9 < rho < 1.0 and np.isclose(np.linalg.norm(tg[i, :2]), 1.0)
    assert np.isclose(abs(tg[i, :2] @ chord) / np.linalg.norm(chord), 1.0)
    assert np.isnan(tg[ids.index("prn")]).all() and np.isnan(tg[ids.index("en_L")]).all()
    res_t = reconstruct_landmarks(photos, None, prior=prior)
    res_0 = reconstruct_landmarks(plain, None, prior=prior)
    assert np.all(np.isfinite(res_t.X)) and np.all(np.isfinite(res_0.X))
    Ct, C0 = res_t.obs_cov_px[1][i], res_0.obs_cov_px[1][i]
    t = tg[i, :2]
    n = np.array([-t[1], t[0]])
    sn, st = KIND_SIGMA_MM["curve"]
    assert np.isclose(C0[0, 0], C0[1, 1]) and abs(C0[0, 1]) < 1e-9 * C0[0, 0]        # isotropic fallback
    ratio = (n @ Ct @ n) / (t @ Ct @ t)
    assert ratio < 0.2 and (n @ Ct @ n) < 0.2 * C0[0, 0]            # across the lip line: ~1.5 mm, not 5.4 mm
    assert ratio > (sn / st) ** 2                                   # direction uncertainty and floor included
    # a point without a tangent is declared as before: isotropic at max(sigma_n, sigma_t) (FU-01)
    j = ids.index("prn")
    Cj = res_t.obs_cov_px[1][j]
    assert np.isclose(Cj[0, 0], Cj[1, 1]) and abs(Cj[0, 1]) < 1e-9 * Cj[0, 0]
    assert np.allclose(np.diag(Cj), np.diag(res_0.obs_cov_px[1][j]), rtol=0.05)


def test_fu04_mirror_thresholds_from_the_null():
    """gap ~ N(-/+ 4 g, 16 g): tau = z_(1-alpha)^2 bounds the false-flip rate by alpha for every g (checked
    on the formula and by simulation at the worst case g = tau / 4) and ``derived_g_min()`` without n_v is
    the detectability at which the *gap condition alone* has 95 % power (simulated): a lower bound of the
    per-view g_min of the complete rule (next test).  Registered defaults carry badge and source."""
    from face3d.core import config as cfg
    from face3d.solve import mirror as M
    from face3d.solve.robust import norm_ppf
    assert M.GAP_THRESHOLD == pytest.approx(norm_ppf(1.0 - 1e-4) ** 2) == pytest.approx(13.83, abs=0.01)
    assert M.G_MIN == pytest.approx(8.155, abs=0.01) and M.derived_g_min(15.5) == pytest.approx(8.75, abs=0.05)
    for key in ("flip_alpha", "keep_power", "g_min"):
        d = cfg.get("mirror." + key)
        assert d.badge and "FU-04" in d.source
    # the false-flip bound, with a looser alpha so that the simulation resolves it
    alpha = 0.01
    tau = M.gap_threshold(alpha)
    g = np.linspace(0.05, 40.0, 4000)
    from math import erfc, sqrt
    p_false = np.array([0.5 * erfc((tau + 4 * x) / (4 * sqrt(x)) / sqrt(2.0)) for x in g])
    assert p_false.max() <= alpha * (1 + 1e-6) and abs(g[p_false.argmax()] - tau / 4.0) < 0.05
    rng = np.random.default_rng(11)
    n, dim = 200000, 40
    for gg, mirrored in ((tau / 4.0, False), (M.derived_g_min(tau), True)):
        w = np.zeros(dim)
        w[0] = np.sqrt(gg)
        eps = rng.normal(size=(n, dim))
        # as given: residual eps (+ 2 w when the view really is mirrored); flipped hypothesis: the other one
        r0 = eps + (2 * w if mirrored else 0.0)
        r1 = eps + (0.0 if mirrored else 2 * w)
        gap = np.sum(r0 ** 2, axis=1) - np.sum(r1 ** 2, axis=1)
        rate = float(np.mean(gap > tau))
        if mirrored:
            assert abs(rate - 0.95) < 0.01, rate
        else:
            assert rate <= alpha * 1.15, rate
    with pytest.raises(ValueError):
        M.gap_threshold(0.7)


def _mirror_mc_case():
    """44 anatomical landmarks (packaged prior mean, made symmetric) plus an antisymmetric perturbation
    field, a rear camera at 1.5 m and the true isotropic noise: (consensus_of(scale), camera, perm, sigma)."""
    from face3d.geometry.procrustes import reflect
    from face3d.model.landmark_prior import FactorPrior
    from face3d.model.registry import load_scheme
    from face3d.synthetic import orbit_camera
    perm = load_scheme("anatomical44").mirror_permutation()
    X0 = FactorPrior.from_package().mean()
    nx = np.array([1.0, 0.0, 0.0])
    D = np.random.default_rng(1).normal(0.0, 1.0, X0.shape)
    Xs = 0.5 * (X0 + reflect(X0[perm], nx, 0.0))
    A = 0.5 * (D - reflect(D[perm], nx, 0.0))
    cam = orbit_camera(1500.0, 20.0, 5.0, 85.0, target=(0.0, -20.0, 60.0))
    return (lambda k: Xs + k * A), cam, perm, 2.0


def test_fu04_review_mirror_keep_needs_power_of_the_complete_rule():
    """Review finding (major): g_min came from the gap > tau condition alone (8.16), so 'keep' was given
    where the complete rule (gap > tau AND delta > rel, costs capped at 3.035 sigma) found far fewer than
    95 % of the flips (23 % 'keep' on mirrored views at g = 8.3, 44 landmarks, rel 0.20).  Now g_min is
    derived per view from the complete rule, and a significant gap is never 'keep'.  Monte Carlo through
    ``mirror_test`` itself, 44 landmarks, rear camera (rel 0.20), true noise."""
    from face3d.io.image_ops import flip_uv
    from face3d.solve import mirror as M
    make, cam, perm, sig = _mirror_mc_case()
    cov = np.tile(np.eye(2) * sig ** 2, (44, 1, 1))
    kw = dict(is_front_camera=False, all_views_front=False, other_views_agree=False)

    def at(k):
        X = make(k)
        return X, M.mirror_test(cam.project(X), cam.width, perm, X, cov, cam, **kw)

    def scale_for(target_ratio):                       # bisect the asymmetry scale to g / g_min = target
        lo, hi = 0.0, 2.0
        for _ in range(18):
            mid = 0.5 * (lo + hi)
            d = at(mid)[1]
            lo, hi = (mid, hi) if d.g < target_ratio * d.g_min else (lo, mid)
        return hi

    # the complete rule asks for more than the gap-only bound, and more with more landmarks
    assert M.derived_g_min(n_v=44, rel=0.20) == pytest.approx(11.6, abs=0.3)
    assert M.derived_g_min(n_v=80) > M.derived_g_min(n_v=44) > M.derived_g_min(n_v=30) > M.G_MIN
    assert M.derived_g_min(n_v=44, rel=0.10) < M.derived_g_min(n_v=44, rel=0.20)
    # the cap never raises the false-flip bound: Var x <= 4 E x for every shift
    ex, vx, _, _, _ = M._cap_moments(np.linspace(0.05, 12.0, 300))
    assert np.all(vx <= 4.0 * ex * (1 + 1e-9)) and np.all(np.diff(ex) >= -1e-9)

    rng = np.random.default_rng(7)
    n = 150
    # (a) just above g_min: the flip is found at the promised rate and a mirrored view is ~never 'keep'
    X, d0 = at(scale_for(1.03))
    assert d0.decision == "keep" and d0.g >= d0.g_min > 11.0 and d0.power >= 0.95
    uv_m = flip_uv(cam.project(X), float(cam.width), perm)
    cov_m = M.flip_cov(cov, perm)
    dec = [M.mirror_test(uv_m + rng.normal(0, sig, uv_m.shape), cam.width, perm, X, cov_m, cam, **kw) for _ in range(n)]
    n_flip = sum(d.decision == "suggest_flip" for d in dec)
    assert n_flip >= 0.90 * n, n_flip                  # 0.95 promised; 150 trials: 2.8-sigma band below
    assert sum(d.decision == "keep" for d in dec) <= 0.03 * n
    assert not any(d.decision == "keep" and d.gap > d.gap_threshold for d in dec)
    assert all("M-GAP-SIGNIFICANT" in d.flags for d in dec if d.decision == "undetermined" and d.gap > d.gap_threshold)
    clean = [M.mirror_test(cam.project(X) + rng.normal(0, sig, uv_m.shape), cam.width, perm, X, cov, cam, **kw)
             for _ in range(50)]
    assert not any(d.decision == "suggest_flip" for d in clean)
    # (b) at the old g_min (8.3): the test is honest about its power: never 'keep', mirrored or not
    k83 = 0.0
    lo, hi = 0.0, 2.0
    for _ in range(18):
        k83 = 0.5 * (lo + hi)
        lo, hi = (k83, hi) if at(k83)[1].g < 8.3 else (lo, k83)
    X, d1 = at(hi)
    assert d1.g == pytest.approx(8.3, abs=0.1) and d1.decision == "undetermined" and 0.6 < d1.power < 0.9
    uv_m = flip_uv(cam.project(X), float(cam.width), perm)
    dec = [M.mirror_test(uv_m + rng.normal(0, sig, uv_m.shape), cam.width, perm, X, cov_m, cam, **kw) for _ in range(60)]
    assert not any(d.decision == "keep" for d in dec)
    assert abs(np.mean([d.decision == "suggest_flip" for d in dec]) - d1.power) < 0.15   # predicted power is real
    # an explicit g_min still overrides, but a significant gap is not 'keep' even then
    dec = [M.mirror_test(uv_m + rng.normal(0, sig, uv_m.shape), cam.width, perm, X, cov_m, cam, g_min=0.0, **kw)
           for _ in range(30)]
    assert not any(d.decision == "keep" and d.gap > d.gap_threshold for d in dec)


def test_fu04_final_review_mirror_power_follows_the_robust_fit():
    """Final review finding (major): the power model removed the pose by a least-squares projection, which
    spreads an asymmetry carried by one L/R pair over all the other landmarks, where it is not capped and
    grows with scale; the robust fit (Huber IRLS, costs capped at 3.035 sigma) treats the pair as outliers
    and does not move the pose, so the observed gap stops near 15 while the predicted power went to 1.
    Result: 'keep' on ~30 % of mirrored views at g >= g_min.  Now the projection carries the Huber weights
    of the robust fit (``_robust_perp``).  Asymmetry on go_L / go_R only (5.4 mm), front camera, yaw 0,
    true noise; Monte Carlo through ``mirror_test``."""
    from face3d.geometry.procrustes import reflect
    from face3d.io.image_ops import flip_uv
    from face3d.model.landmark_prior import FactorPrior
    from face3d.model.registry import load_scheme
    from face3d.solve import mirror as M
    from face3d.synthetic import orbit_camera
    sch = load_scheme("anatomical44")
    perm = sch.mirror_permutation()
    names = [p.get("anatomical_id") or p.get("name") for p in sch.raw["points"]]
    X0 = FactorPrior.from_package().mean()
    nx = np.array([1.0, 0.0, 0.0])
    Xs = 0.5 * (X0 + reflect(X0[perm], nx, 0.0))
    D = np.zeros_like(Xs)
    D[names.index("go_L")] = [3.0, 4.0, 2.0]
    A = 0.5 * (D - reflect(D[perm], nx, 0.0))
    X = Xs + 2.0 * A
    assert np.linalg.norm(2.0 * A[names.index("go_L")]) == pytest.approx(5.4, abs=0.1)
    cam = orbit_camera(1500.0, 0.0, 5.0, 85.0, target=(0.0, -20.0, 60.0))
    sig = 2.0
    cov = np.tile(np.eye(2) * sig ** 2, (44, 1, 1))
    kw = dict(is_front_camera=True, all_views_front=False, other_views_agree=False)
    d0 = M.mirror_test(cam.project(X), cam.width, perm, X, cov, cam, **kw)
    assert d0.decision == "undetermined" and d0.g < d0.g_min and d0.power < 0.95
    # the least-squares projection (before the fix) promised a flip with power ~1 on the same view
    from face3d.solve.camera_model import projection_jacobians
    Wh = M.whitening(cov)
    w = np.einsum("nij,njk,nk->ni", Wh, projection_jacobians(d0.camera, X), A).reshape(-1)
    Jp = np.einsum("nij,njk->nik", Wh, M._pose_jacobian(d0.camera, X)).reshape(-1, 6)
    w_ls = w - Jp @ np.linalg.lstsq(Jp, w, rcond=None)[0]
    assert M.rule_power(2.0 * np.linalg.norm(w_ls.reshape(-1, 2), axis=1), d0.rel_threshold, d0.gap_threshold,
                        44) > 0.95
    # mirrored views: never 'keep'; the predicted power does not over-promise
    rng = np.random.default_rng(5)
    n = 100
    uv_m = flip_uv(cam.project(X), float(cam.width), perm)
    cov_m = M.flip_cov(cov, perm)
    dec = [M.mirror_test(uv_m + rng.normal(0, sig, uv_m.shape), cam.width, perm, X, cov_m, cam, **kw) for _ in range(n)]
    assert sum(d.decision == "keep" for d in dec) <= 0.05 * n          # was ~0.31 n
    p_mc = np.mean([d.decision == "suggest_flip" for d in dec])       # ~0.71
    assert np.mean([d.power for d in dec]) <= p_mc + 0.05 and abs(np.mean([d.power for d in dec]) - p_mc) < 0.15
    # an evenly spread small asymmetry (every expected residual within the Huber delta): weights 1, the
    # least-squares projection unchanged
    w_s = 0.15 * rng.normal(size=88)
    Jr = rng.normal(size=(88, 6))
    assert np.allclose(M._robust_perp(w_s, Jr, 2.0), w_s - Jr @ np.linalg.lstsq(Jr, w_s, rcond=None)[0])


def test_fu04_expression_retag_statistics():
    """The re-tag statistics and their null thresholds: Mahalanobis residuals with a full covariance, the
    capped mobile chi^2 (one gross outlier cannot tag a view), the jaw-angle z under 'this view is
    neutral' (exact for the linear-Gaussian case, by simulation), the registered false-alarm rates."""
    from face3d.core import config as cfg
    from face3d.solve import expression as E
    from face3d.solve.robust import chi2_quantile_wh
    rng = np.random.default_rng(2)
    C = np.array([[[4.0, 1.5], [1.5, 2.0]]] * 5)
    r = rng.normal(size=(5, 2))
    assert np.allclose(E.mahalanobis_e2(r, C), np.einsum("ni,nij,nj->n", r, np.linalg.inv(C), r))
    bad = C.copy()
    bad[0] = np.nan
    assert np.isnan(E.mahalanobis_e2(r, bad)[0])
    # capped chi^2: a 30 sigma outlier counts as a rejected landmark (3.035^2), never more
    e2 = np.array([1.0, 2.0, 900.0, np.nan, 0.5, 3.0])
    T, dof = E.mobile_chi2_capped(e2)
    assert dof == 10 and T == pytest.approx(6.5 + 3.035 ** 2)
    thr = E.retag_thresholds(12)
    assert thr["chi2_mild"] == pytest.approx(chi2_quantile_wh(12, 0.99)) and thr["chi2_mild"] < thr["chi2_expressive"]
    assert E.retag_from_evidence(T + 5.0, 12)[0] == "neutral"            # one outlier + ordinary residuals
    assert E.retag_from_evidence(thr["chi2_mild"] + 0.1, 12)[0] == "mild"
    tag, det = E.retag_from_evidence(thr["chi2_expressive"] + 0.1, 12)
    assert tag == "expressive" and det["by"] == ["mobile_chi2"]
    assert E.retag_from_evidence(1.0, 12, 2.0)[0] == "mild" and E.retag_from_evidence(1.0, 12, 2.7)[1]["by"] == ["jaw_angle"]
    assert E.retag_from_evidence(1.0, 12, 2.7)[0] == "expressive"
    assert E.retag_from_evidence(1.0, 12, float("nan"), "mild")[0] == "mild"    # tags only escalate
    assert E.retag_from_evidence(1.0, 0, float("nan"))[0] == "neutral"
    # null of the capped chi^2 at the stated rate (the cap only lowers it)
    x = rng.chisquare(2, size=(200000, 6))
    Tn = np.minimum(x, 3.035 ** 2).sum(axis=1)
    assert np.mean(Tn > thr["chi2_mild"]) <= 0.01 and np.mean(Tn > thr["chi2_expressive"]) <= 0.001
    # jaw angle: theta ~ N(1.5, 1), measured with SD s_d, solved with the prior N(1.5, s_p^2)
    for s_p, s_d in ((1.0, 0.8), (3.0, 0.8), (3.0, 1.6)):
        theta = rng.normal(1.5, 1.0, 200000)
        meas = theta + rng.normal(0.0, s_d, theta.size)
        w = (1 / s_d ** 2) / (1 / s_d ** 2 + 1 / s_p ** 2)
        hat = 1.5 + w * (meas - 1.5)
        s_post = np.sqrt(1.0 / (1 / s_d ** 2 + 1 / s_p ** 2))
        z = np.array([E.jaw_angle_z(h, s_post, s_p) for h in hat[:2000]])
        sd0 = (hat[0] - 1.5) / z[0]
        assert np.std(hat - 1.5) == pytest.approx(sd0, rel=0.02), (s_p, s_d)
        assert np.mean((hat - 1.5) / sd0 > thr["jaw_z_expressive"]) == pytest.approx(0.005, abs=0.0015)
    assert np.isnan(E.jaw_angle_z(None, 0.5)) and np.isnan(E.jaw_angle_z(4.0, 1.0, 1.0))   # no information
    assert E.jaw_angle_z(4.0, 0.99, 1.0 / 0.99) > 0 and E.jaw_angle_z(6.5, 0.6, 3.0) > thr["jaw_z_expressive"]
    # the 'uninformative' cut is the registered ratio (final review: it was a bare 0.98 in the code)
    rmax = cfg.get("expression.retag_jaw_max_var_ratio").value
    assert rmax == 0.98 and np.isnan(E.jaw_angle_z(4.0, np.sqrt(rmax) * 1.0001, 1.0))
    assert np.isfinite(E.jaw_angle_z(4.0, np.sqrt(rmax) * 0.9999, 1.0))
    # soft down-weighting (off by default in the pipeline): 1 below the soft quantile, sqrt(T / dof) above
    assert E.soft_mobile_multiplier(10.0, 12) == 1.0 and E.soft_mobile_multiplier(24.0, 12) == pytest.approx(2 ** 0.5)
    assert E.soft_mobile_multiplier(500.0, 12) == 3.0
    for key in ("retag_mild_alpha", "retag_expressive_alpha", "retag_mild_jaw_alpha", "retag_expressive_jaw_alpha",
                "retag_jaw_min_sd_deg", "retag_jaw_max_var_ratio", "soft_mobile_alpha"):
        d = cfg.get("expression." + key)
        assert d.badge and "FU-04" in d.source, key
    import face3d.pipeline.stages  # noqa: F401  (registers the ``pipeline`` defaults)
    for key in ("image_tangents", "soft_mobile_downweight"):
        assert "FU-04" in cfg.get("pipeline." + key).source
    # both opt-in: image_tangents is off by default since the FU-04 review (unmeasured scheme metadata)
    assert cfg.get("pipeline.soft_mobile_downweight").value is False and cfg.get("pipeline.image_tangents").value is False
