"""WP-16: observability, evidence at prior weight 1, claims ledger, tiers, LOVO gamma, sigma_rep,
the fixed shrinkage gate and the Schur-marginalised next-best photo (DESIGN D-16..D-19,
4.12-4.14, section 5 H1-H9).

Scenes use the packaged 44-landmark factor prior (DESIGN D-04) and subjects drawn with the
test bed's smooth-field generator on the prior mean (independent of the prior's factors,
D-30), observed through the DESIGN 4.4 noise model of each landmark's kind.
"""
import math
import time

import numpy as np
import pytest

from face3d.core import config
from face3d.eval.coverage import axis_coverage, nees
from face3d.geometry.procrustes import umeyama
from face3d.model.landmark_prior import FactorPrior
from face3d.model.registry import ANATOMICAL
from face3d.solve import nbv
from face3d.solve import observability as ob
from face3d.solve.bundle import Priors, ViewObs, bundle_adjust
from face3d.solve.noise import NoiseModel
from face3d.synthetic import orbit_camera
from face3d.testbed import rigs, subjects
from face3d.fit import ledger as lg

PRIOR = FactorPrior.from_package()
MU = PRIOR.mean()
IDS = list(PRIOR.ids)
N = len(IDS)
KINDS = [ANATOMICAL[i].kind for i in IDS]
NM = NoiseModel(KINDS)
RI = ob.default_region_index(IDS)
F35_NOTHING = 50.0        # DESIGN 4.2 'Nothing' row: 50 mm, sigma 0.6


class Chord:
    """Caliper chord term (DESIGN 4.7): (|X_a - X_b| - L) / sigma, sigma 0.5 mm."""

    is_prior = False

    def __init__(self, a, b, L, sigma=0.5, name="chord"):
        self.a, self.b, self.L, self.sigma, self.name = a, b, L, sigma, name

    def n_params(self):
        return 0

    def init_params(self, state):
        return np.zeros(0)

    def residuals(self, state, p):
        return np.array([(np.linalg.norm(state.X[self.a] - state.X[self.b]) - self.L) / self.sigma])

    def jacobian(self, state, p):
        d = state.X[self.a] - state.X[self.b]
        g = d / np.linalg.norm(d) / self.sigma
        J = np.zeros((1, 3 * len(state.X)))
        J[0, 3 * self.a:3 * self.a + 3] = g
        J[0, 3 * self.b:3 * self.b + 3] = -g
        return {"X": J}


def _scene(seed, yaws, dist, f35=26.0, noise_scale=1.0, declared=1.0, exif=True, pitch=(-5.0, 5.0)):
    """Views of a smooth-field subject; noise drawn from the DESIGN 4.4 model (x noise_scale).

    ``declared`` scales the sigma given to the solver; ``exif=False`` gives the 'Nothing'
    focal prior (50 mm-eq, sigma 0.6) and starts the cameras on it (DESIGN 4.2).
    """
    rng = np.random.default_rng(seed)
    _, X, _ = subjects.smooth_field_subject(rng, names=IDS, template=MU)
    views, cams = [], []
    for y in yaws:
        cam = orbit_camera(dist * rng.uniform(0.95, 1.05), y, rng.uniform(*pitch), f35, target=(0.0, 0.0, 60.0))
        m = rigs.visible_mask(cam, X)
        uv0 = cam.project(X)
        C = NM.view_cov(np.where(m, cam.f / cam.depth(X), np.nan), float(np.ptp(uv0[m, 0]))) * noise_scale ** 2
        L = np.linalg.cholesky(np.where(m[:, None, None], C, np.eye(2)))
        uv = uv0 + np.einsum("nij,nj->ni", L, rng.normal(size=(N, 2)))
        uv[~m] = np.nan
        c0 = cam.copy()
        if exif:
            c0.t = c0.t + rng.normal(scale=3.0, size=3)
            fp, fs = cam.f, 0.04
        else:
            r = F35_NOTHING / f35
            c0.f, c0.t = cam.f * r, cam.t * r
            fp, fs = cam.f * r, 0.6
        views.append(ViewObs(uv, c0, f_prior=fp, f_prior_log_sigma=fs, focal_group="g", kinds=KINDS,
                             cov_px=C * declared ** 2))
        cams.append(cam)
    return X, views, cams


def _solve(views, prior=PRIOR, terms=None, **kw):
    return bundle_adjust(views, MU.copy(), None, prior=prior, terms=terms, **kw)


def _rot_err_deg(Ra, Rb):
    c = (np.trace(Ra @ Rb.T) - 1.0) / 2.0
    return math.degrees(math.acos(min(1.0, max(-1.0, c))))


# ------------------------------------------------------------------ regions and rules
def test_default_region_index_and_registered_defaults():
    assert set(RI) == {"eyes", "lips", "nose", "nose_projection", "cheeks", "forehead", "chin",
                       "chin_projection", "jaw", "ears", "cranium"}            # no brow points in the 44
    zcoord = lambda lid: 3 * IDS.index(lid) + 2
    assert sorted(RI["nose_projection"].tolist()) == sorted(zcoord(x) for x in ("prn", "sn", "ac_L", "ac_R"))
    assert sorted(RI["chin_projection"].tolist()) == sorted(zcoord(x) for x in ("pg", "gn", "sl"))
    assert set(RI["eyes"].tolist()) >= {3 * IDS.index("en_L"), 3 * IDS.index("en_L") + 1}
    legacy = ob.default_region_index(["brow_inner_L", "pronasale", "subnasale", "pogonion", "menton", "foo"])
    assert legacy["brows"].tolist() == [0, 1, 2] and legacy["nose_projection"].tolist() == [5, 8]
    assert ob.REGION_TARGET_MM == {"eyes": 1.0, "lips": 1.0, "brows": 1.2, "nose": 1.2, "nose_projection": 1.5,
                                   "forehead": 1.5, "cheeks": 1.5, "chin": 1.5, "chin_projection": 1.5,
                                   "jaw": 2.0, "ears": 3.0, "cranium": 3.0}
    assert nbv.REGION_WEIGHTS == {"eyes": 1.0, "brows": 0.9, "lips": 0.8, "nose": 0.7, "nose_projection": 0.7,
                                  "jaw": 0.5, "chin": 0.5, "chin_projection": 0.5, "cheeks": 0.4,
                                  "forehead": 0.3, "ears": 0.15, "cranium": 0.1}
    for ns in ("observability", "nbv", "ledger"):
        keys = [k for k in config.snapshot() if k.startswith(ns + ".")]
        assert keys and all(config.get(k).source for k in keys)


def test_coverage_rules_and_region_status():
    pts = {"nose_projection": np.array([0, 1]), "jaw": np.array([2]), "ears": np.array([3]),
           "cheeks": np.array([4])}
    vis = np.ones((4, 5), bool)
    vis[:, 4] = False                                                   # cheeks never seen
    r = ob.coverage_rules([0.0, 10.0, 65.0, 30.0], [0.0, 0.0, -16.0, 6.0], vis, pts)
    assert r["nose_projection"] == {"depth": True, "projection": True, "jaw_underside": True, "ears": True,
                                    "observed": True}
    assert r["cheeks"]["observed"] is False and r["cheeks"]["depth"] is False
    # frontal only: no projection, no depth
    r2 = ob.coverage_rules([-10.0, 0.0, 10.0], [0.0, 0.0, 0.0], np.ones((3, 5), bool), pts)
    assert not r2["nose_projection"]["projection"] and not r2["nose_projection"]["depth"]
    assert not ob.coverage_ok("nose_projection", r2["nose_projection"])
    # half the points must be seen for a view to "see" a region
    v3 = np.zeros((2, 5), bool)
    v3[0, 0] = True
    v3[1, :] = True
    r3 = ob.coverage_rules([0.0, 60.0], [0.0, 0.0], v3, {"np": np.array([0, 1, 2])})
    assert r3["np"]["observed"] and not r3["np"]["projection"]
    assert ob.region_status(0.9, True, 0.8, 1.0, True) == "measured"
    assert ob.region_status(0.9, False, 0.8, 1.0, True) == "constrained"
    assert ob.region_status(0.9, True, 1.2, 1.0, True) == "constrained"
    assert ob.region_status(0.6, True, 0.8, 1.0, True) == "constrained"
    assert ob.region_status(0.4, True, 0.8, 1.0, True) == "prior-driven"
    assert ob.region_status(float("nan"), True, 0.8, 1.0, True) == "prior-driven"
    assert ob.region_status(0.99, True, 0.1, 1.0, False) == "unobserved"
    k = ob.region_evidence(np.diag([1.0, 1.0, 4.0]), np.diag([4.0, 4.0, 4.0]), {"a": [0, 1], "b": [2]})
    assert k == {"a": 0.75, "b": 0.0}


# ------------------------------------------------------------------ focal status
def test_focal_status():
    # (a) frontal-only views at 2 m without EXIF (prior 50 mm-eq, sigma 0.6): the focal is the
    # prior's (median over 10 seeds; never 'measured').  The factor prior knows the depth relief,
    # so perspective still gives a weak cue: sigma_logf 0.34-0.56 here, and about a quarter of
    # such sets read 'partial' (sigma < 0.8 x 0.6) -- never 'measured'.
    sig, n_prior = [], 0
    for seed in range(10):
        _, views, _ = _scene(seed, (-3.0, 0.0, 3.0), 2000.0, exif=False)
        res = _solve(views)
        cs = ob.camera_status(res.view_stats, 0.6, res.cameras)
        assert all(c["focal_status"] != "measured" for c in cs)
        assert all(abs(c["P"] - 100.0 / np.linalg.norm(cam.center)) < 1e-12 for c, cam in zip(cs, res.cameras))
        n_prior += all(c["focal_status"] == "prior_used" for c in cs)
        sig.append(cs[0]["sigma_logf"])
    assert np.median(sig) > 0.8 * 0.6 and n_prior >= 6, (sig, n_prior)
    # (b) views spanning >= 60 deg yaw at 0.5 m (5 views, -60..60) without EXIF: measured, focal
    # error < 5 % and rotation error < 2 deg (median over 10 seeds; com R8.4).  The detector here
    # has half the nominal DESIGN 4.4 sigma (a sharp 12 MP photo); at the nominal sigma the same
    # rig gives sigma_logf ~0.105 ('partial') and a ~7 % median focal error (WP-16 report).
    ferr, rerr = [], []
    for seed in range(10):
        X, views, cams = _scene(100 + seed, (-60.0, -30.0, 0.0, 30.0, 60.0), 500.0, exif=False, noise_scale=0.5)
        res = _solve(views)
        cs = ob.camera_status(res.view_stats, 0.6, res.cameras)
        assert all(c["focal_status"] == "measured" for c in cs), [c["sigma_logf"] for c in cs]
        ferr.append(abs(res.cameras[0].f / cams[0].f - 1.0))
        s, R, t = umeyama(res.X, X, with_scale=True)                    # truth ~ s R est + t
        rerr.append(np.median([_rot_err_deg(c.R @ R.T, ct.R) for c, ct in zip(res.cameras, cams)]))
    assert np.median(ferr) < 0.05, ferr
    assert np.median(rerr) < 2.0, rerr
    # rule order (DESIGN 4.12 / H5): CAM-7 first, then the 0.10 threshold
    st = [{"sigma_logf": 0.035, "sigma_logz": 0.1}, {"sigma_logf": 0.02, "sigma_logz": 0.1},
          {"sigma_logf": 0.2, "sigma_logz": 0.1}, {"sigma_logf": None, "sigma_logz": None},
          {"sigma_logf": 0.0, "sigma_logz": 0.01}]
    out = [c["focal_status"] for c in ob.camera_status(st, [0.04, 0.04, 0.6, 0.6, 0.6])]
    assert out == ["prior_used", "measured", "partial", "prior_used", "measured"]


# ------------------------------------------------------------------ evidence and coverage
def _ring(seed, chord=True):
    yaws = tuple(np.linspace(-90.0, 90.0, 7))
    X, views, cams = _scene(seed, yaws, 2000.0, f35=85.0)
    terms = None
    if chord:
        a, b = IDS.index("t_L"), IDS.index("t_R")
        terms = [Chord(a, b, float(np.linalg.norm(X[a] - X[b])))]
    return X, views, _solve(views, terms=terms)


def test_frontal_only_projection_not_measured():
    for seed in range(4):
        _, views, _ = _scene(10 + seed, (-12.0, 0.0, 12.0), 600.0)
        res = _solve(views)
        A = ob.assess(res, region_index=RI, prior_log_sigma=0.04)
        for r in ("nose_projection", "chin_projection"):
            assert A["region_status"][r] != "measured"
            assert not A["coverage"][r]["projection"]
        assert A["tier"][0] == "C"                                     # all views within |yaw| < 20
        # evidence sits in [0, 1]: the posterior never exceeds the prior (PSD order)
        assert all(-1e-9 <= k <= 1.0 for k in A["region_k"].values())
    # studio ring (7 views over +/-90 deg, 85 mm, 2 m) with a caliper chord: nose projection measured
    for seed in (1, 2):
        _, _, res = _ring(seed)
        A = ob.assess(res, region_index=RI, prior_log_sigma=0.04, scale_mode="measured")
        assert A["coverage"]["nose_projection"]["projection"]
        assert A["region_status"]["nose_projection"] == "measured", (A["region_k"]["nose_projection"],
                                                                     A["region_sigma_rep_mm"]["nose_projection"])
        assert A["region_k"]["nose_projection"] >= 0.8
        assert A["region_sigma_rep_mm"]["nose_projection"] <= 1.5
        assert res.zeta_sigma < 0.6 * 0.045                            # the chord informs the scale


def test_labels_invariant_to_prior_weight():
    # Likeness mode (DESIGN 4.6) widens kappa where >= 2 views see a point; labels and sigma
    # stay at prior weight 1 (H2) through standard_prior_info.  The 1.2 m frontal set is where
    # the widened prior moves the estimate most and where naive labels (read off the widened
    # solve) change, so it shows the guard has teeth.
    for seed, yaws, dist in ((2, (-60.0, -30.0, 0.0, 30.0, 60.0), 900.0), (5, (-12.0, 0.0, 12.0), 1200.0)):
        _, views, _ = _scene(seed, yaws, dist)
        res = _solve(views)
        A = ob.assess(res, region_index=RI, prior_log_sigma=0.04)
        seen = np.array(res.inlier_mask).sum(axis=0)
        wide, res_w = ob.likeness_mode_prior(PRIOR, res, seen, resolve=lambda p: _solve(views, prior=p),
                                             return_result=True)
        assert wide.meta["likeness"]["rounds"] >= 1
        mult = np.asarray(wide.meta["likeness_multiplier"])
        assert mult.max() > 1.0 and mult.min() == 1.0
        H_std = ob.standard_prior_info(res_w, wide, PRIOR)
        Aw = ob.assess(res_w, region_index=RI, prior_log_sigma=0.04, standard_prior_info=H_std)
        assert Aw["region_status"] == A["region_status"]
        assert max(abs(Aw["region_k"][r] - A["region_k"][r]) for r in RI) < 0.06
        if dist > 1000.0:
            naive = ob.assess(res_w, region_index=RI, prior_log_sigma=0.04)
            assert naive["region_status"] != A["region_status"]
            assert naive["region_k"]["nose_projection"] > A["region_k"]["nose_projection"] + 0.2
    _, views, _ = _scene(3, (-30.0, 0.0, 30.0), 700.0)
    res = _solve(views)
    # without a substitute prior, Sigma1 is the bundle's own posterior (Schur over cameras and
    # zeta), also with a frozen (empty) view conditioned on
    assert np.allclose(ob.posterior_at_prior_weight_one(res, project=False), res.cov, rtol=1e-8, atol=1e-10)
    assert np.allclose(ob.posterior_at_prior_weight_one(res, project=False, conditional_on_zeta=True),
                       res.cov_shape, rtol=1e-8, atol=1e-10)
    empty = ViewObs(np.full((N, 2), np.nan), views[0].camera.copy(), f_prior=views[0].f_prior,
                    f_prior_log_sigma=0.04, focal_group="other", kinds=KINDS)
    res_e = _solve(views + [empty])
    assert res_e.view_stats[-1]["frozen"] and ob.frozen_parameters(res_e).size >= 6
    assert np.allclose(ob.posterior_at_prior_weight_one(res_e, project=False), res_e.cov, rtol=1e-8, atol=1e-10)
    # the standard information equals the solve's own H_prior when nothing was widened
    assert np.allclose(ob.standard_prior_info(res, PRIOR, PRIOR), res.H_prior, rtol=1e-9, atol=1e-9)
    H_shape = ob.shape_prior_info(PRIOR, res)
    assert np.all(np.linalg.eigvalsh(res.H_prior - H_shape) > -1e-6 * np.abs(res.H_prior).max())


# ------------------------------------------------------------------ LOVO and sigma_rep
def test_lovo_gamma():
    yaws = (-60.0, -30.0, 0.0, 30.0, 60.0)
    for declared, lo, hi in ((1.0, 0.8, 1.25), (0.5, 1.6, 2.4)):
        for seed in range(4):
            _, views, _ = _scene(seed, yaws, 900.0, declared=declared)
            res = _solve(views)
            solve_without = ob.make_solve_without(views, res, bundle_kwargs={"prior": PRIOR})
            g, ratio, flags = ob.lovo_gamma(solve_without, res, views, [v.cov_px for v in views])
            assert lo <= g <= hi, (declared, seed, g)
            assert ratio.shape == (5,) and np.all(ratio[np.isfinite(ratio)] > 0.5)
            assert ob.FLAG_L_HELDOUT not in flags
    g, ratio, flags = ob.lovo_gamma(lambda v: None, res, views[:2], [v.cov_px for v in views[:2]])
    assert g == 1.0 and flags == [ob.FLAG_L_TOO_FEW_VIEWS] and np.all(np.isnan(ratio))


def test_sigma_rep_formula():
    _, views, _ = _scene(7, (-45.0, 0.0, 45.0), 700.0)
    res = _solve(views)
    d = np.diag(res.cov_shape).reshape(N, 3)
    sdef = res.sigma_def_mm[:, None]
    # gamma 1 reproduces the bundle's own sigma_rep (WP-07: max(1, chi2_red))
    assert np.allclose(ob.sigma_rep(res, 1.0), res.sigma_rep_mm, rtol=1e-12)
    for gamma in (0.5, 1.0, 1.7, 3.0):
        infl = max(1.0, gamma ** 2, res.chi2_red)
        assert np.allclose(ob.sigma_rep(res, gamma), np.sqrt(d * infl + sdef ** 2), rtol=1e-12)
    C = np.eye(3 * N) * 4.0
    assert np.allclose(ob.sigma_rep(res, 2.0, cov=C), np.sqrt(4.0 * max(4.0, res.chi2_red) + sdef ** 2))
    # gain form: B = K D K^T, which is the floor D when the photos determine everything (K = I)
    K = ob.bias_gain(res)
    Dm = np.repeat(res.sigma_def_mm ** 2, 3)
    Cr = ob.reported_covariance(res, 1.3)
    assert np.allclose(Cr, res.cov_shape * max(1.69, res.chi2_red) + (K * Dm) @ K.T)
    assert np.allclose(ob.sigma_rep(res, 1.3, bias="gain"), np.sqrt(np.diag(Cr)).reshape(N, 3))
    ev = np.linalg.eigvals(K)                                    # K = Sigma H_data: eigenvalues in [0, 1]
    assert np.all(ev.real > -1e-6) and np.all(ev.real < 1 + 1e-6) and np.abs(ev.imag).max() < 1e-6
    res.H_prior = np.zeros_like(res.H_prior)                     # no prior: K = I, gain == floor
    assert np.allclose(ob.reported_covariance(res, 1.0, bias="gain"), ob.reported_covariance(res, 1.0, bias="floor"))
    with pytest.raises(ValueError):
        ob.sigma_rep(res, 1.0, bias="nope")


def test_sigma_rep_honesty_on_testbed():
    """Gauge-projected NEES/dof and 1-sigma coverage of the reported covariance (DESIGN 7.5)
    on the WP-01 rear_phone_legacy scenario (legacy prior, robust schedule, the detector's
    shared definition bias): the posterior alone is over-confident, the literal floor form
    under-confident, the gain form inside the gates.  The 30 scorecard seeds of this scenario;
    the WP-16 report gives the numbers for every legacy scenario."""
    from face3d.solve.reconstruct import PhotoLandmarks, reconstruct_landmarks
    from face3d.solve.robust import RobustSchedule
    from face3d.synthetic import midline_indices, mirror_pairs
    from face3d.testbed.detector_sim import legacy_kinds, simulate
    from face3d.testbed.scenarios import LEGACY_PRIOR, SCENARIOS, _seed_streams
    scn = SCENARIOS["rear_phone_legacy"]
    stats = {"post": [], "floor": [], "gain": []}
    for seed in range(1000, 1030):
        r_subj, r_rig, r_det = _seed_streams(seed)
        names, Xt, meta = scn.subject_fn(r_subj)
        rig = scn.rig_fn(r_rig, X=Xt)
        kinds = legacy_kinds(names)
        obs = simulate(Xt, kinds, rig, r_det, **scn.detector_kwargs)
        photos = [PhotoLandmarks(uv, c.width, c.height, f_prior_px=rig.f_prior_px[k],
                                 f_prior_log_sigma=rig.f_prior_log_sigma[k], focal_group=rig.focal_group[k],
                                 kinds=kinds) for k, (uv, c) in enumerate(zip(obs.uv, rig.cameras))]
        pri = Priors(mean=meta["template"], sigma=LEGACY_PRIOR["sigma"], pairs=mirror_pairs(names),
                     sigma_sym=LEGACY_PRIOR["sigma_sym"], midline=midline_indices(names),
                     sigma_mid=LEGACY_PRIOR["sigma_mid"])
        res = reconstruct_landmarks(photos, pri, robust=RobustSchedule())
        s, R, t = umeyama(res.X, Xt, with_scale=True)
        err = s * res.X @ R.T + t - Xt
        Bk = np.kron(np.eye(len(Xt)), R)
        for key, C in (("post", res.cov_shape), ("floor", ob.reported_covariance(res, bias="floor")),
                       ("gain", ob.reported_covariance(res, bias="gain"))):
            Ca = s * s * Bk @ C @ Bk.T
            stats[key].append((nees(err, Ca, Xt)[0], axis_coverage(err, Ca, Xt, ks=(1,))[1]))
    m = {k: np.mean(np.array(v), axis=0) for k, v in stats.items()}
    assert m["post"][0] > 1.25                                   # over-confident without sigma_def
    assert m["floor"][0] < m["gain"][0] < m["post"][0]
    assert 0.8 <= m["gain"][0] <= 1.25, m
    assert 0.60 <= m["gain"][1] <= 0.76, m


# ------------------------------------------------------------------ shrinkage gate
def test_shrinkage_gate_calibration():
    rng = np.random.default_rng(0)
    K = 50
    lam = np.linspace(0.02, 0.94, K)                             # k_eff = sum(lambda) = 24
    n = 1.0 / lam - 1.0                                          # whitened noise variances
    Q, _ = np.linalg.qr(rng.normal(size=(K, K)))
    Sh = Q @ np.diag(rng.uniform(1.0, 5.0, K)) @ Q.T            # S^1/2 (a general SPD prior)
    S = Sh @ Sh
    Ncov = Sh @ np.diag(n) @ Sh
    Si, Ni = np.linalg.inv(S), np.linalg.inv(Ncov)
    Sig = np.linalg.inv(Si + Ni)
    gate = ob.shrinkage_gate(np.zeros(K), S, Sig)
    assert abs(gate["k_eff"] - 24.0) < 1e-6
    M = 20000
    z = rng.normal(size=(M, K))
    y = z @ Sh.T + (rng.normal(size=(M, K)) * np.sqrt(n)) @ Sh.T     # prior-drawn faces + noise
    xh = y @ (Sig @ Ni).T
    T = np.einsum("mi,ij,mj->m", xh, Si, xh)
    assert abs(T.mean() - 24.0) < 0.5                           # predictive mean = k_eff
    assert np.mean(T < gate["q_lo"]) <= 0.02                    # alpha_lo 1 %
    assert np.mean(T > gate["q_hi"]) <= 0.005                   # alpha_hi 0.1 %
    # 10x prior weight (over-shrinkage) is detected
    xh10 = y @ (np.linalg.inv(10.0 * Si + Ni) @ Ni).T
    T10 = np.einsum("mi,ij,mj->m", xh10, Si, xh10)
    assert np.mean(T10 < gate["q_lo"]) >= 0.90
    # per-draw findings agree with the vectorised test
    for i in range(50):
        g = ob.shrinkage_gate(xh10[i], S, Sig)
        assert (g["finding"] == ob.FINDING_PULLED) == bool(T10[i] < gate["q_lo"])
        assert abs(g["T"] - T10[i]) < 1e-6 * T10[i]
    assert ob.shrinkage_gate(3.0 * y[0] @ (Sig @ Ni).T * 4.0, S, Sig)["finding"] == ob.FINDING_IMPLAUSIBLE
    # the legacy chi^2_K gate fires on most faces drawn from the prior itself (D-18: 85 %)
    c = xh[:2000] @ np.linalg.inv(Sh).T
    fired = np.mean([ob.legacy_shrinkage_gate(ci, K) for ci in c])
    assert fired >= 0.5, fired
    # nothing measured: no finding
    assert ob.shrinkage_gate(np.ones(3), np.eye(3), np.eye(3))["finding"] is None


# ------------------------------------------------------------------ tiers
def test_tiers_from_evidence():
    meas = {"nose_projection": "measured", "chin_projection": "measured"}
    yaws7 = [-90, -60, -30, 0, 30, 60, 90]
    assert ob.tier("measured", meas, 7, yaws7, ["measured"] * 7, False) == ("S", "metric")
    # EXIF sigma <= 0.04 confirms the focal for S
    assert ob.tier("measured", meas, 7, yaws7, ["prior_used"] * 7, False, exif_log_sigma=0.04)[0] == "S"
    assert ob.tier("measured", meas, 7, yaws7, ["prior_used"] * 7, False, exif_log_sigma=0.09)[0] == "A"
    assert ob.tier("measured", meas, 4, yaws7[:4], ["measured"] * 4, False)[0] == "A"       # < 5 views
    assert ob.tier("iris", meas, 7, yaws7, ["measured"] * 7, False) == ("A", "iris-scaled")
    part = {"nose_projection": "constrained", "chin_projection": "measured"}
    assert ob.tier("measured", part, 7, yaws7, ["measured"] * 7, False)[0] == "A"
    assert ob.tier("iris", meas, 3, [-30, 0, 30], ["measured"] * 3, False) == ("B", "proportions only")
    assert ob.tier("prior", meas, 7, yaws7, ["measured"] * 7, False)[0] == "B"               # H4
    assert ob.tier("iris", meas, 2, [0, 60], ["measured"] * 2, False)[0] == "B"
    assert ob.tier("measured", meas, 1, [0], ["measured"], False) == ("C", "blockout")
    assert ob.tier("measured", meas, 5, [-15, -5, 0, 5, 19], ["measured"] * 5, False)[0] == "C"
    assert ob.tier("measured", meas, 7, yaws7, ["measured"] * 7, True)[0] == "C"
    # from evidence end to end: a ring with a caliper chord; frontal-only; three-quarter set
    _, _, res = _ring(1)
    A = ob.assess(res, region_index=RI, prior_log_sigma=0.04, exif_log_sigma=0.04, scale_mode="measured")
    assert A["tier"][0] in ("S", "A")
    statuses = dict(A["region_status"], chin_projection="measured", nose_projection="measured")
    assert ob.tier("measured", statuses, 7, A["yaws"], A["focal_statuses"], False, exif_log_sigma=0.04)[0] == "S"
    _, views, _ = _scene(4, (-50.0, 0.0, 50.0), 800.0)
    A3 = ob.assess(_solve(views), region_index=RI, prior_log_sigma=0.04, scale_mode="iris")
    assert A3["tier"] == ("A", "iris-scaled")
    A3p = ob.assess(_solve(views), region_index=RI, prior_log_sigma=0.04, scale_mode="prior")
    assert A3p["tier"] == ("B", "proportions only")


# ------------------------------------------------------------------ next-best photo
def _kit_normals():
    from face3d.model.procedural_head import build_procedural_head
    kit = build_procedural_head()
    return kit, kit.normals[kit.landmark_vertices("anatomical44", IDS)]


def test_nbv_frontal_only_picks_profile():
    kit, normals = _kit_normals()                                # template normals (DESIGN 4.8)
    picks, slow = [], 0.0
    for seed in range(30):
        rng = np.random.default_rng(5000 + seed)
        yaws = tuple(rng.uniform(-15.0, 15.0, size=3))
        dist = float(rng.uniform(800.0, 1500.0))
        _, views, _ = _scene(200 + seed, yaws, dist)
        res = _solve(views)
        t0 = time.perf_counter()
        ranked, sentence, known = nbv.next_best_view(res.cov_shape, res, res.X, noise_model=NM,
                                                     region_index=RI, normals=normals, return_known=True)
        slow = max(slow, time.perf_counter() - t0)
        assert len(ranked) == 39
        assert all(s <= known[(y, p)] * (1 + 1e-9) + 1e-9 for y, p, s in ranked)
        assert all(s >= -1e-9 for _, _, s in ranked)
        assert [s for _, _, s in ranked] == sorted((s for _, _, s in ranked), reverse=True)
        picks.append(ranked[0])
        assert sentence.startswith("Next: ") and sentence.endswith(" m")
    frac = np.mean([abs(y) >= 60.0 for y, _, _ in picks])
    assert frac >= 0.9, picks
    assert slow < 2.0, slow
    # the sentence: subject's left = positive yaw
    assert nbv.describe_view(60.0, 0.0, 1750.0) == "Next: left profile, eye height, 1.5-2 m"
    assert nbv.describe_view(-45.0, -20.0, 1200.0) == "Next: right three-quarter, from below, 1-1.4 m"
    assert nbv.describe_view(0.0, 20.0, 600.0) == "Next: front, from above, 0.5-0.7 m"
    # a candidate is the orbit_camera geometry (focal in px)
    cam = nbv.candidate_camera(30.0, 10.0, 1200.0, 3000.0, (3000, 4000))
    ref = orbit_camera(1200.0, 30.0, 10.0, 26.0, target=(0.0, 0.0, 0.0))
    assert np.allclose(cam.R, ref.R) and np.allclose(cam.t, ref.t) and cam.f == 3000.0


# ------------------------------------------------------------------ ledger
def test_ledger_plain_language_and_banner():
    kit, normals = _kit_normals()
    _, views, _ = _scene(11, (-10.0, 0.0, 10.0), 1000.0)
    res = _solve(views)
    A = ob.assess(res, region_index=RI, prior_log_sigma=0.04)
    _, sentence = nbv.next_best_view(res.cov_shape, res, res.X, noise_model=NM, region_index=RI, normals=normals)
    led = lg.build_ledger(res, PRIOR, ANATOMICAL, A, next_photo=sentence)
    lines = lg.report_lines(led)
    assert lines[0] == "Not validated against a scan." and led.banner == lg.BANNER
    assert lines[1] == "Tier C: blockout"
    assert led.unverified_defaults == config.unverified_count() > 0
    assert any(ln.startswith("Scale: population prior +/-4.") for ln in lines)          # H4
    assert any(ln.startswith("Focal length: ") for ln in lines)
    assert "Nose projection: guessed from average proportions (prior-driven) - take a left or right profile" \
        in lines
    npj = led.region("nose_projection")
    assert npj.status == "prior-driven" and npj.why_key == "ledger.why.prior_no_coverage"
    assert lines[-1] == sentence
    # a region no photo shows is 'unobserved' and says which photo would show it (H9)
    vis = np.array(res.inlier_mask)
    vis[:, [IDS.index(x) for x in ("v", "op", "eu_L", "eu_R")]] = False
    Au = ob.assess(res, region_index=RI, prior_log_sigma=0.04, visibility=vis)
    led_u = lg.build_ledger(res, PRIOR, ANATOMICAL, Au)
    assert led_u.region("cranium").status == "unobserved" and led_u.region("cranium").why_key == "ledger.why.unobserved"
    assert "Cranium: not seen in any photo (unobserved) - take a photo that shows the cranium" in lg.report_lines(led_u)
    # a measured region reads "likely within +/-x mm (measured)"
    _, _, ring = _ring(1)
    Ar = ob.assess(ring, region_index=RI, prior_log_sigma=0.04, scale_mode="measured")
    led_r = lg.build_ledger(ring, PRIOR, IDS, Ar)
    lr = lg.report_lines(led_r)
    sig = led_r.region("nose_projection").sigma_rep_mm
    assert f"Nose projection: likely within +/-{sig:.1f} mm (measured)" in lr
    assert any(ln.startswith("Scale: caliper/card +/-") for ln in lr)
    # occluder tags cap a status (beard -> jaw prior-driven) and say why
    Ab = ob.assess(ring, region_index=RI, prior_log_sigma=0.04, status_caps={"jaw": "prior-driven"})
    led_b = lg.build_ledger(ring, PRIOR, IDS, Ab)
    assert led_b.region("jaw").status == "prior-driven" and led_b.region("jaw").why_key == "ledger.why.tagged"
    # DESIGN D-31: the ear shape is silhouette-only and labelled prior-driven in this version
    ears = led_r.region("ears")
    assert ears.status == "prior-driven" and ears.why_key == "ledger.why.not_modelled" and ears.k > 0.5
    assert "Ears: guessed from average proportions (prior-driven) - shape not fitted in this version; " \
           "sculpt it from a side photo" in lr
    # per-vertex support for the protect mask: k by kit region, nose limited by its projection
    sup = lg.vertex_support(kit, led_r)
    assert sup.shape == (kit.n_verts,) and np.all((sup >= 0) & (sup <= 1))
    vr = kit.vertex_regions()
    kk = {c.name: c.k for c in led_r.regions}
    assert np.allclose(sup[vr == "nose"], min(kk["nose"], kk["nose_projection"]))
    assert np.allclose(sup[vr == "neck"], 0.0) and np.allclose(sup[vr == "ears"], 0.0)
    assert np.allclose(lg.vertex_support(kit, led_b)[vr == "jaw"], 0.0)
    sup_f = lg.vertex_support(kit, led)
    assert np.allclose(sup_f[vr == "scalp"], np.clip(led.region("cranium").k, 0.0, 1.0))
    sup_u = lg.vertex_support(kit, led_u)
    assert np.allclose(sup_u[vr == "scalp"], 0.0)                 # cranium unobserved -> guessed
