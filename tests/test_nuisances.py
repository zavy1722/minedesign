"""WP-15: nuisances - scale fusion and limbus fit, mirror test, expression tags and inflation,
per-view camera-model selection, retouch residual test (DESIGN D-03, D-10, D-12, D-14, 4.3,
4.7, 4.9, 4.10, 4.1 Q-RETOUCH).

Test-bed conventions used here
------------------------------
* Landmark-level trials use the WP-01 test bed (legacy 32-point subjects, ``rear_phone`` rig,
  detector simulator); surface-level trials use the WP-11 out-of-prior subjects on the
  procedural CC0 kit (``anatomical44`` landmarks).
* Detector covariances passed to the nuisance tests are the simulator's own (normal / tangent
  sigma along its tangent directions), so the statistics are tested against a correct noise
  model.
* The mirror TPR and retouch TPR acceptance rows are run with the detector simulator at 0.2 x
  the DESIGN 4.4 nominal noise (``LOW_NOISE``).  At nominal noise a single view cannot resolve
  ~1 mm of facial asymmetry or a 6 % / 4 % beauty warp (40 seeds: median mirror detectability
  g ~2; retouch TPR 0.25).  WBS FU-04 recalibrated the mirror test against its own null: the
  gap threshold tau = 13.83 bounds the false-flip rate by 1e-4 and g_min (per view, complete rule; >= 8.16) is the
  detectability with 95 % power (``solve.mirror`` 'Null distribution'), so the mirror row is
  tested on the views with g >= g_min (at 0.2 x and at 0.5 x noise; no view reaches g_min at
  nominal noise, where the honesty halves are asserted: no false flip, no false 'keep').  The
  retouch TPR half at nominal noise stays a strict xfail on the spec row.
* Scale is tested on the pair the report prints (``reported_scale``: Umeyama log-size and an SD
  that covers its error) against the test bed's ``log_scale_true``; the scale mode's SD is only
  the metric references' share of it.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from face3d.core import config as cfg
from face3d.geometry.camera import Camera, camera_to_invdepth
from face3d.geometry.procrustes import umeyama
from face3d.geometry.rotations import rodrigues
from face3d.qa.image_stats import gaussian_blur
from face3d.solve import camera_model as CM
from face3d.solve import expression as E
from face3d.solve import mirror as M
from face3d.solve import scale as S
from face3d.solve.bundle import BUNDLE, Priors, ViewObs, bundle_adjust
from face3d.solve.noise import KIND_SIGMA_MM, NoiseModel, whitening
from face3d.solve.pnp import solve_pnp
from face3d.solve.reconstruct import PhotoLandmarks, reconstruct_landmarks
from face3d.solve.robust import norm_ppf
from face3d.solve.terms import SolverState, Term
from face3d.synthetic import orbit_camera
from face3d.testbed import detector_sim, faults, rigs, subjects
from face3d.testbed.scenarios import LEGACY_PRIOR, _seed_streams

LOW_NOISE = 0.2          # detector noise scale for the single-view TPR rows (see module docstring)


# =========================================================================== helpers
def _sim_cov(obs, k):
    """(N, 2, 2) px^2: the simulator's true covariance of view k (NaN where hidden)."""
    sg = obs.sigma_px_true[k]
    t = obs.tangent_dirs
    n = np.column_stack([-t[:, 1], t[:, 0]])
    C = ((sg[:, 1] ** 2)[:, None, None] * np.einsum("ni,nj->nij", t, t)
         + (sg[:, 0] ** 2)[:, None, None] * np.einsum("ni,nj->nij", n, n))
    C[~np.isfinite(obs.uv[k][:, 0])] = np.nan
    return C


def _legacy_prior(T, names, symmetry=True):
    from face3d.synthetic import midline_indices, mirror_pairs
    if not symmetry:
        return Priors(mean=T, sigma=LEGACY_PRIOR["sigma"])
    return Priors(mean=T, sigma=LEGACY_PRIOR["sigma"], pairs=mirror_pairs(names), sigma_sym=LEGACY_PRIOR["sigma_sym"],
                  midline=midline_indices(names), sigma_mid=LEGACY_PRIOR["sigma_mid"])


def _photos(obs, rig, kinds, uvs=None):
    uvs = obs.uv if uvs is None else uvs
    return [PhotoLandmarks(uv, c.width, c.height, f_prior_px=rig.f_prior_px[k],
                           f_prior_log_sigma=rig.f_prior_log_sigma[k], focal_group=rig.focal_group[k], kinds=kinds)
            for k, (uv, c) in enumerate(zip(uvs, rig.cameras))]


def _mode_error(res, mode, X_true):
    """Scale-mode coordinate of the error, l^T vec(X_hat - X_true) with l = C^-1 x / x^T C^-1 x
    (:func:`face3d.solve.scale.scale_mode`); the truth is rigidly aligned to the estimate first
    (the solve's gauge is arbitrary; the scale coordinate is rigid-invariant to first order)."""
    _, R, t = umeyama(X_true, res.X, with_scale=False)
    return float(mode["functional"] @ (res.X - (X_true @ R.T + t)).reshape(-1))


@pytest.fixture(scope="module")
def kit():
    from face3d.model.procedural_head import build_procedural_head
    return build_procedural_head()


@pytest.fixture(scope="module")
def anat(kit):
    from face3d.model.registry import ANATOMICAL, load_scheme
    from face3d.testbed.render import face_centre
    names = kit.landmark_names("anatomical44")
    sch = load_scheme("anatomical44")
    assert [p.anatomical_id for p in sch.points] == names
    return {"names": names, "kinds": [ANATOMICAL[n].kind for n in names], "perm": sch.mirror_permutation(),
            "fc": tuple(float(v) for v in face_centre(kit))}


# =========================================================================== term Jacobians
def _state(X, blocks, zeta=0.0):
    """SolverState from per-view dicts {kind, R, tau, rho (1/mm), a | phi | f, cx, cy}."""
    from face3d.solve.terms import BLOCK_NAMES
    inv, like = [], []
    for b in blocks:
        kind = b["kind"]
        if kind == "free":
            s = math.exp(b["a"])
        elif kind == "hard":
            s = math.exp(b["phi"]) * b["rho"]
        else:
            s = b["f"] * b["rho"]
        inv.append({"R": b["R"], "tau": b["tau"], "rho": b["rho"], "s": s, "a": math.log(s), "f": s / b["rho"],
                    "kind": kind, "block": BLOCK_NAMES[kind]})
        like.append(Camera(s / b["rho"], b["cx"], b["cy"], 3000, 4000))
    return SolverState(X, zeta, inv, like, {})


def _perturb(blocks, v, j, h):
    """Copy of the camera blocks with parameter j of view v moved by h (block order, rho in 1/m)."""
    out = [dict(b) for b in blocks]
    b = out[v]
    if j < 3:
        e = np.zeros(3)
        e[j] = h
        b["R"] = rodrigues(e) @ b["R"]
    elif j < 5:
        b["tau"] = b["tau"].copy()
        b["tau"][j - 3] += h
    elif j == 5:
        b["rho"] = b["rho"] + h * 1e-3
    else:
        b["a"] = b["a"] + h
    return out


def _close_rows(Ja, Jn, what):
    """|Ja - Jn| <= 1e-5 |Jn| + 1e-6 max|row| + 1e-7 (central differences with h = 1e-6 are
    accurate to ~1e-8 here), so a 0.1 % error in any non-negligible entry is caught."""
    rowmax = np.abs(Jn).max(axis=1, keepdims=True)
    bad = np.abs(Ja - Jn) > 1e-5 * np.abs(Jn) + 1e-6 * rowmax + 1e-7
    assert not bad.any(), (what, np.argwhere(bad)[:3].tolist())


def _check_term_jacobian(term, X, blocks, p, phi_key=None, hard_view=None):
    st = _state(X, blocks)
    J = term.jacobian(st, p)
    r0 = term.residuals(st, p)
    h = 1e-6
    # X block
    if "X" in J:
        Jn = np.zeros((len(r0), X.size))
        for c in range(X.size):
            for sgn in (1, -1):
                Xp = X.copy().reshape(-1)
                Xp[c] += sgn * h
                Jn[:, c] += sgn * term.residuals(_state(Xp.reshape(X.shape), blocks), p) / (2 * h)
        _close_rows(J["X"], Jn, "X block")
    # self block
    if p.size:
        Jn = np.zeros((len(r0), p.size))
        for c in range(p.size):
            e = np.zeros(p.size)
            e[c] = h
            Jn[:, c] = (term.residuals(st, p + e) - term.residuals(st, p - e)) / (2 * h)
        _close_rows(J["self"], Jn, "self block")
    # camera blocks
    for v, b in enumerate(blocks):
        key = f"cam:{v}"
        size = 7 if b["kind"] == "free" else 6
        Jn = np.zeros((len(r0), size))
        for j in range(size):
            Jn[:, j] = (term.residuals(_state(X, _perturb(blocks, v, j, h)), p)
                        - term.residuals(_state(X, _perturb(blocks, v, j, -h)), p)) / (2 * h)
        _close_rows(J.get(key, np.zeros_like(Jn)), Jn, key)
    if hard_view is not None:
        b = blocks[hard_view]
        Jn = np.zeros((len(r0), 1))
        for sgn in (1, -1):
            bb = [dict(x) for x in blocks]
            bb[hard_view]["phi"] = b["phi"] + sgn * h
            Jn[:, 0] += sgn * term.residuals(_state(X, bb), p) / (2 * h)
        _close_rows(J[phi_key], Jn, "phi")


def test_term_jacobians_and_protocol():
    rng = np.random.default_rng(1)
    X = rng.normal(scale=40.0, size=(6, 3)) + np.array([0.0, 0.0, 60.0])
    blocks = []
    for kind, yaw in (("free", -20.0), ("hard", 10.0), ("fixed_f", 30.0)):
        cam = orbit_camera(700.0, yaw, 3.0, 26.0)
        d = camera_to_invdepth(cam)
        b = {"kind": kind, "R": d["R"], "tau": d["tau"] + rng.normal(scale=2, size=2), "rho": d["rho"],
             "cx": cam.cx + 3.0, "cy": cam.cy - 2.0}
        b.update({"free": {"a": math.log(d["s"])}, "hard": {"phi": math.log(cam.f)}, "fixed_f": {"f": cam.f}}[kind])
        blocks.append(b)
    phi = {1: "phi_0"}
    chord = S.ChordTerm(0, 1, 50.0)
    ipd = S.IpdTerm(2, 3, z_mm=350.0)
    iris = S.IrisTerm([(0, "L", 35.0, 1.0), (1, "R", 30.0, 1.0), (2, "L", 33.0, 0.7)], {"L": 2, "R": 3},
                      phi_keys=phi)
    card = S.CardTerm(1, [[1400.0, 1900.0], [1650.0, 1910.0]], 4, phi_keys=phi)
    card_spec = S.CardTerm(1, [[1400.0, 1900.0], [1650.0, 1910.0]], 4, phi_keys=phi, tilt_sigma_mm=None)
    for t in (chord, ipd, iris, card):
        assert isinstance(t, Term)
    st = _state(X, blocks)
    _check_term_jacobian(chord, X, blocks, np.zeros(0))
    _check_term_jacobian(ipd, X, blocks, np.zeros(0))
    _check_term_jacobian(iris, X, blocks, np.array([11.5]), phi_key="phi_0", hard_view=1)
    p_card = card.init_params(st) + rng.normal(scale=1.0, size=6)
    _check_term_jacobian(card, X, blocks, p_card, phi_key="phi_0", hard_view=1)
    _check_term_jacobian(card_spec, X, blocks, p_card, phi_key="phi_0", hard_view=1)
    assert len(card.residuals(st, p_card)) == 7 and len(card_spec.residuals(st, p_card)) == 6
    # routing and defaults (DESIGN 4.7)
    assert not chord.is_prior and not iris.is_prior and not card.is_prior and ipd.is_prior
    assert ipd.mean == pytest.approx(63.0 - 2.0)          # vergence 2.0 mm at 0.35 m (bl C3)
    assert S.vergence_correction_mm(280.0) == pytest.approx(2.5) and S.vergence_correction_mm(1500.0) == 0.0
    assert S.vergence_correction_mm(700.0) == pytest.approx(1.0)
    # the init back-projects the card to the touch landmark's depth
    C0 = card.init_params(st).reshape(2, 3)
    cam1 = st.cameras[1]
    assert np.allclose(cam1.depth(C0), cam1.depth(X[4][None])[0])
    # a 'hard' view without its phi key is refused
    with pytest.raises(ValueError, match="phi_keys"):
        S.IrisTerm([(1, "L", 30.0, 1.0)], {"L": 2}).residuals(st, np.array([11.8]))
    # focal_phi_keys mirrors the bundle's parameter layout
    views = [ViewObs(np.zeros((3, 2)), cam1, focal_group="b"), ViewObs(np.zeros((3, 2)), cam1, focal_group="a"),
             ViewObs(np.zeros((3, 2)), cam1, focal_group="b", focal_tie_sigma=0.02),
             ViewObs(np.zeros((3, 2)), cam1, estimate_focal=False, focal_group="a")]
    assert S.focal_phi_keys(views) == {0: "phi_0", 1: "phi_1"}


def test_terms_inside_the_bundle_jacobian(monkeypatch):
    """The scale terms plugged into bundle_adjust: the bundle's analytic Jacobian (term blocks
    'X', 'self', 'cam:<v>' and the focal-group 'phi_<j>' named by focal_phi_keys) equals central
    differences through the bundle's retract, for FREE and HARD camera blocks."""
    import face3d.solve.bundle as B
    from face3d.solve.bundle import ScaleConfig
    from face3d.synthetic import synthetic_landmarks
    names, T = synthetic_landmarks()
    rng = np.random.default_rng(4)
    X = T * 1.03 + rng.normal(scale=1.0, size=T.shape)
    views = []
    for k, yaw in enumerate((-30.0, 0.0, 35.0)):
        c = orbit_camera(650.0, yaw, 4.0, 26.0)
        uv = c.project(X) + rng.normal(scale=1.0, size=(len(X), 2))
        uv[~rigs.visible_mask(c, X)] = np.nan
        c0 = c.copy()
        c0.t = c0.t + rng.normal(scale=2.0, size=3)
        kw = {"f_prior": c.f, "f_prior_log_sigma": 0.05, "sigma_px": 1.5}
        if k > 0:
            kw["focal_group"] = "g"                           # HARD blocks sharing phi_0
        views.append(ViewObs(uv, c0, **kw))
    pk = S.focal_phi_keys(views)
    assert pk == {1: "phi_0", 2: "phi_0"}
    eye = {"L": names.index("pupil_L"), "R": names.index("pupil_R")}
    iris = S.IrisTerm([(0, "L", 40.0, 1.0), (1, "R", 38.0, 1.0), (2, "L", 37.0, 1.0)], eye, phi_keys=pk)
    k = names.index("pogonion")
    card = S.CardTerm(1, views[1].camera.project(X[k] + np.array([[-42.8, 0, 3], [42.8, 0, 3]])), k, phi_keys=pk)
    chord = S.ChordTerm(names.index("zygion_L"), names.index("zygion_R"), 140.0)
    ipd = S.IpdTerm(eye["L"], eye["R"])
    cap = {}
    orig = B.levenberg_marquardt

    def shim(fun, x0, jac=None, retract=None, **kw):
        cap.update(fun=fun, jac=jac, retract=retract, x0=x0)
        return orig(fun, x0, jac=jac, retract=retract, max_iter=0)
    monkeypatch.setattr(B, "levenberg_marquardt", shim)
    res = B.bundle_adjust(views, T.copy(), Priors(mean=T, sigma=8.0), scale=ScaleConfig(),
                          terms=[iris, card, chord, ipd])
    fun, retract, x0 = cap["fun"], cap["retract"], cap["x0"]
    Ja = cap["jac"](x0)
    h = 1e-4
    Jn = np.zeros_like(Ja)
    for j in range(len(x0)):
        e = np.zeros(len(x0))
        e[j] = h
        Jn[:, j] = (fun(retract(x0, e)) - fun(retract(x0, -e))) / (2 * h)
    scale = np.abs(Jn).max(axis=0, keepdims=True) + 1e-12
    assert np.all(np.abs(Ja - Jn) <= 1e-4 * scale + 1e-5 * np.abs(Jn)), float(np.max(np.abs(Ja - Jn) / scale))
    assert {"term:iris", "term:card", "phi_0"} <= set(res.param_index)


# =========================================================================== scale: caliper
def test_caliper_scale_tight():
    """Caliper chord zy-zy (0.5 mm) on 40 landmark-testbed trials (DESIGN 4.7, H4, H12).

    The reported pair (:func:`face3d.solve.scale.reported_scale` -> ``scale_report``) is the
    Umeyama log-size of the reconstruction and an SD meant to cover its error; it is tested
    against the test bed's own truth ``log_scale_true`` (review WP-15: the scale mode's SD
    alone, ~0.4 %, covered only ~1/3 of the trials and is no longer printed).  The chord carries
    the end points' definition bias (zygion: extremal, 1.5 mm each; DESIGN D-06), without which
    the caliper's 0.5 mm overstates what it fixes.  The caliper noise is stratified (the 40
    normal quantiles, randomly permuted over the trials).

    WBS row vs this test (escalated, see the WP-15 notes): an honest log-size SD with a caliper
    is ~2.5 % on this test bed (reference ~1.5 %, shape ~1.4 % before chi^2 inflation), so
    'zeta_sigma <= 0.006' holds only for the caliper's own reference share (checked below, 0.5 mm
    chord without definition bias); the pair is calibrated (RMS z ~1.0) and covers 37 of 40 at
    2 sigma, where '>= 95 % of 40' would fail a perfectly calibrated estimator ~30 % of the time.
    """
    n_trials = 40
    q = np.array([norm_ppf((k + 0.5) / n_trials) for k in range(n_trials)])
    q = q[np.random.default_rng(15).permutation(n_trials)]
    errs, sig, ref_sig, cal_ref, err_with, err_without = [], [], [], [], [], []
    for trial in range(n_trials):
        r_subj, r_rig, r_det = _seed_streams(2000 + trial)
        names, X_true, meta = subjects.legacy_subject(r_subj)
        T = meta["template"]
        rig = rigs.rear_phone(r_rig, X=X_true)
        kinds = detector_sim.legacy_kinds(names)
        obs = detector_sim.simulate(X_true, kinds, rig, r_det)
        a, b = names.index("zygion_L"), names.index("zygion_R")
        L = float(np.linalg.norm(X_true[a] - X_true[b])) + 0.5 * q[trial]
        sdef = NoiseModel(kinds).sigma_def_mm()
        sc, extra = S.population_scale_setup("global_size")
        photos, prior = _photos(obs, rig, kinds), _legacy_prior(T, names)
        chord = S.ChordTerm(a, b, L, definition_sigma_mm=sdef[[a, b]])
        res = reconstruct_landmarks(photos, prior, scale=sc, terms=[chord] + extra)
        rs = S.reported_scale(res, T)
        sig.append(rs["sigma"])
        ref_sig.append(rs["reference_sigma"])
        err = rs["zeta"] - meta["log_scale_true"]
        errs.append(err)
        assert rs["zeta"] == pytest.approx(S.log_size(res.X, T))
        assert rs["sigma"] >= rs["reference_sigma"] > 0 and rs["shape_sigma"] > 0 and rs["definition_sigma"] > 0
        if trial < 10:      # the remedy on the test bed: absolute size with vs without the caliper
            res0 = reconstruct_landmarks(photos, prior, scale=sc)
            err_with.append(err)
            err_without.append(S.log_size(res0.X, T) - meta["log_scale_true"])
        if trial < 5:       # the caliper's own share: the WBS residual (0.5 mm, no definition bias)
            res_cal = reconstruct_landmarks(photos, prior, scale=sc, terms=[S.ChordTerm(a, b, L)] + extra)
            cal_ref.append(S.scale_mode(res_cal)["sigma"])
    sig, ref_sig, errs = np.array(sig), np.array(ref_sig), np.array(errs)
    zs = errs / sig
    # the reported pair against the truth: calibrated, and >= 90 % inside 2 sigma (see docstring)
    assert np.mean(np.abs(zs) < 2.0) >= 0.9, np.sort(np.abs(zs))[-5:]
    assert 0.8 < float(np.sqrt(np.mean(zs ** 2))) < 1.25, float(np.sqrt(np.mean(zs ** 2)))
    # the caliper still pins the scale: the reference share 0.5 / L <= 0.6 % (DESIGN 4.7 '< 1 %')
    assert max(cal_ref) <= 0.006, cal_ref
    # ... and the size a user sees improves over the population prior alone.  Updated by WBS
    # FU-01: the population-only solves no longer carry the mm-space symmetry rows' pull toward
    # small heads (mean error -5.8 % -> -2.5 % on trials 0-9, RMS 0.064 -> 0.038), so the ratio
    # is 0.63 instead of 0.36; 'several-fold' (< 0.5) was measured against that biased baseline.
    assert np.sqrt(np.mean(np.square(err_with))) < 0.75 * np.sqrt(np.mean(np.square(err_without)))
    # regression (review WP-15): the scale mode's SD next to the printed log-size would cover
    # well under half of the trials; the reported SD is several times larger
    assert np.mean(np.abs(errs) < 2.0 * max(cal_ref)) < 0.5
    assert np.all(sig > 3.0 * max(cal_ref)) and np.all(sig > ref_sig)
    # the report: measured mode, the reported pair's +/- %, the reference share echoed
    rep = S.scale_report(rs["zeta"], rs["sigma"], ["caliper", "global_size"], reference_sigma=rs["reference_sigma"])
    assert rep["mode"] == "measured" and rep["label"] == "caliper+population"
    assert rep["sigma_pct"] == pytest.approx(100.0 * rs["sigma"]) and rep["zeta"] == rs["zeta"]
    assert rep["reference_sigma_pct"] == pytest.approx(100.0 * rs["reference_sigma"])
    assert rep["text"] == f"scale: caliper+population ±{100.0 * rs['sigma']:.1f} %"


def test_card_term_recovers_scale():
    """An ID-1 card held against pogonion in the frontal view (DESIGN 4.7): the card's corner
    reprojection, 85.60 mm chord and 10 mm contact-depth prior pin the scale mode to ~1 %."""
    r_subj, r_rig, r_det = _seed_streams(2100)
    names, X_true, meta = subjects.legacy_subject(r_subj)
    T = meta["template"]
    rig = rigs.rear_phone(r_rig, X=X_true)
    kinds = detector_sim.legacy_kinds(names)
    obs = detector_sim.simulate(X_true, kinds, rig, r_det)
    k = names.index("pogonion")
    v = 2                                                         # the yaw-0 view
    C_true = X_true[k] + np.array([[-42.8, -8.0, 4.0], [42.8, -8.0, 4.0]])
    corner_uv = rig.cameras[v].project(C_true) + np.random.default_rng(3).normal(scale=1.0, size=(2, 2))
    photos = _photos(obs, rig, kinds)
    card = S.CardTerm(v, corner_uv, k, phi_keys=S.focal_phi_keys(photos))
    sc, extra = S.population_scale_setup("global_size")
    res = reconstruct_landmarks(photos, _legacy_prior(T, names), scale=sc, terms=[card] + extra)
    res0 = reconstruct_landmarks(photos, _legacy_prior(T, names), scale=sc)
    mode = S.scale_mode(res)
    mode0 = S.scale_mode(res0)
    assert 0.004 < mode["sigma"] < 0.02 and mode0["sigma"] > 0.04, (mode["sigma"], mode0["sigma"])
    corners = res.term_params["card"].reshape(2, 3)
    assert abs(np.linalg.norm(corners[0] - corners[1]) - 85.60) < 1.0
    assert abs(_mode_error(res, mode, X_true)) < 3.0 * mode["sigma"]
    src = S.card_scale_source(res.X, res.cameras[v], corner_uv, k, T)
    assert src["kind"] == "card" and abs(src["zeta"] - S.log_size(res.X, T)) < 3.0 * src["sigma"]
    # the reported pair covers the truth (H4, H12)
    rs = S.reported_scale(res, T)
    assert rs["reference_sigma"] == pytest.approx(mode["sigma"]) and rs["sigma"] > rs["reference_sigma"]
    assert abs(rs["zeta"] - meta["log_scale_true"]) < 3.0 * rs["sigma"]


# =========================================================================== scale: iris
def test_iris_fusion_numbers():
    """Iris alone ~ 0.6 / 11.8 = 5.1 %, fused with the 0.045 population prior ~ 3.4 % (DESIGN 4.7 🔢).

    These are the metric references' share of the size uncertainty (the scale mode's SD,
    :func:`face3d.solve.scale.scale_mode`), which is what the DESIGN numbers derive.  The report
    prints the reported pair (:func:`face3d.solve.scale.reported_scale`), whose SD adds the
    log-size's shape and definition parts (~3.7 % for iris + population here) and covers the
    test bed's truth."""
    assert S.fuse_log_scale([(0.0, 0.6 / 11.8), (0.0, 0.045)])[1] == pytest.approx(0.0337, abs=5e-4)
    for trial in range(3):
        r_subj, r_rig, r_det = _seed_streams(3000 + trial)
        names, X_true, meta = subjects.legacy_subject(r_subj)
        T = meta["template"]
        rig = rigs.rear_phone(r_rig, X=X_true)
        kinds = detector_sim.legacy_kinds(names)
        obs = detector_sim.simulate(X_true, kinds, rig, r_det)
        eye = {"L": names.index("pupil_L"), "R": names.index("pupil_R")}
        rng = np.random.default_rng(30 + trial)
        D_true = 11.8 + rng.normal(scale=0.6)
        iobs = [(k, e, cam.f * D_true / cam.depth(X_true[i][None])[0] + rng.normal(scale=1.0), 1.0)
                for k, cam in enumerate(rig.cameras) for e, i in eye.items() if np.isfinite(obs.uv[k][i, 0])]
        assert all(S.iris_usable(o[2], True, False) for o in iobs)
        photos = _photos(obs, rig, kinds)
        # the legacy iid shape prior without its mm-space symmetry rows (they leak a size cue; see notes)
        pri = _legacy_prior(T, names, symmetry=False)
        sig = {}
        for src in (None, "global_size"):
            sc, extra = S.population_scale_setup(src)
            it = S.IrisTerm(iobs, eye, phi_keys=S.focal_phi_keys(photos))
            res = reconstruct_landmarks(photos, pri, scale=sc, terms=[it] + extra)
            mode = S.scale_mode(res)
            sig[src] = mode["sigma"]
            assert abs(_mode_error(res, mode, X_true)) < 3.0 * mode["sigma"]
            rs = S.reported_scale(res, T)
            assert rs["reference_sigma"] == pytest.approx(mode["sigma"])
            assert mode["sigma"] < rs["sigma"] < 1.25 * mode["sigma"], rs
            assert abs(rs["zeta"] - meta["log_scale_true"]) < 2.5 * rs["sigma"]
            if src == "global_size":
                isrc = S.iris_scale_source(res.X, res.cameras, iobs, eye, T)
                rep = S.scale_report(rs["zeta"], rs["sigma"], [isrc, "global_size"],
                                     reference_sigma=rs["reference_sigma"])
        assert abs(sig[None] / 0.0508 - 1.0) < 0.10, sig
        assert abs(sig["global_size"] / 0.034 - 1.0) < 0.10, sig
        assert rep["label"] == "iris+population" and rep["mode"] == "iris" and not rep["conflict"]
        assert abs(rep["reference_sigma_pct"] / 3.4 - 1.0) < 0.10
        assert rep["text"] == f"scale: iris+population ±{rep['sigma_pct']:.1f} %" and rep["sigma_pct"] > 3.4


def test_iris_gating_and_one_population_source():
    assert not S.iris_usable(15.0, True, False)            # d_px < 20
    assert not S.iris_usable(30.0, True, True)             # glasses
    assert not S.iris_usable(30.0, False, False)           # unsharp limbus
    assert S.iris_usable(20.0, True, False)
    with pytest.raises(ValueError, match="exactly one"):
        S.population_scale_source(["global_size", "ipd"])
    with pytest.raises(ValueError, match="exactly one"):
        S.population_scale_setup(("ipd", "global_size"), pupil_idx=(0, 1))
    with pytest.raises(ValueError):
        S.population_scale_source("caliper")
    assert S.population_scale_source("global_size") == "global_size" and S.population_scale_source(None) is None
    sc, terms = S.population_scale_setup("global_size")
    assert sc.enabled and sc.sigma_log == pytest.approx(0.045) and terms == []
    sc, terms = S.population_scale_setup("ipd", pupil_idx=(3, 4), z_mm=350.0)
    assert sc.sigma_log >= 10.0 and len(terms) == 1 and terms[0].is_prior
    assert terms[0].mean == pytest.approx(63.0 - 2.0)
    with pytest.raises(ValueError):
        S.population_scale_setup("ipd")


# =========================================================================== limbus fit
def _eye_image(rng, R, blur, noise=0.02, iris=0.30, sclera=0.75, lids=False):
    """Synthetic eye: dark iris disc (radius R px, 8x8 supersampled) with a pupil on sclera,
    optional lids covering the top and bottom sectors, Gaussian blur, then pixel noise."""
    size = int(4 * R + 20)
    c = np.array([size / 2 + rng.uniform(-0.5, 0.5), size / 2 + rng.uniform(-0.5, 0.5)])
    off = (np.arange(8) + 0.5) / 8
    jj, ii = np.meshgrid(np.arange(size), np.arange(size))
    acc = np.zeros((size, size))
    accp = np.zeros((size, size))
    for a in off:
        for b in off:
            d = np.hypot(jj + a - c[0], ii + b - c[1])
            acc += d <= R
            accp += d <= 0.4 * R
    img = sclera + (iris - sclera) * acc / 64.0 + (0.08 - iris) * accp / 64.0
    if lids:
        v = ii + 0.5
        img = np.where((v < c[1] - 0.80 * R) | (v > c[1] + 0.85 * R), 0.55, img)
    img = gaussian_blur(img, blur) if blur > 0 else img
    return img + rng.normal(scale=noise, size=img.shape), c


def test_limbus_fit_synthetic():
    """Dark disc radius 12-30 px, blur 0.5-1.5 px, noise SD 0.02: radius error < 0.3 px and the
    limbus is usable; blur 3 px is not usable (DESIGN 4.7 'sharp limbus').

    The gate (review WP-15) is the fitted edge width AND the contrast-to-noise statistic, and is
    checked over pixel noise SD 0.005-0.05 and iris/sclera contrast 0.15-0.60 (lids on part of
    the images): blur >= 3 px is never usable, also at low noise where the contrast-to-noise
    statistic alone passes it (2.4-6 there); a crisp limbus is usable wherever its edge stands
    clear of the noise (also at noise 0.05 with contrast 0.45); a usable limbus has its radius
    within 0.45 px and 2 sigma_r."""
    rng = np.random.default_rng(42)
    for blur in (0.5, 1.0, 1.5, 3.0):
        for k in range(8):
            R = 12.0 + 18.0 * k / 7.0
            img, c = _eye_image(rng, R, blur, lids=(k % 2 == 1))
            guess_c = c + rng.normal(scale=1.0, size=2)
            centre, r, sigma_r, sharp, info = S.fit_limbus(img, guess_c, R * rng.uniform(0.85, 1.15), full_output=True)
            usable = S.limbus_is_sharp(sharp, info["edge_sigma_px"])
            assert usable == info["sharp"]
            if blur <= 1.5:
                assert abs(r - R) < 0.3, (blur, R, r)
                assert np.linalg.norm(centre - c) < 0.3
                assert usable, (blur, R, sharp, info)
                assert 0.5 <= sigma_r < 0.6
                assert abs(info["edge_sigma_px"] - math.hypot(blur, 0.5)) < 0.35, (blur, info)
            else:
                assert not usable, (blur, R, sharp, info)
    # across noise and contrast (the 4-tuple without full_output is unchanged)
    for noise in (0.005, 0.01, 0.02, 0.05):
        for iris, sclera in ((0.30, 0.75), (0.20, 0.80), (0.45, 0.60)):
            con = sclera - iris
            for blur in (0.5, 1.0, 1.5, 3.0, 4.0):
                for k, R in enumerate((12.0, 26.0)):
                    img, c = _eye_image(rng, R, blur, noise=noise, iris=iris, sclera=sclera, lids=(k == 1))
                    args = (img, c + rng.normal(scale=1.0, size=2), R * rng.uniform(0.85, 1.15))
                    centre, r, sigma_r, sharp, info = S.fit_limbus(*args, full_output=True)
                    if noise == 0.005 and blur == 0.5 and k == 0:
                        assert len(S.fit_limbus(*args)) == 4
                    usable = S.limbus_is_sharp(sharp, info["edge_sigma_px"])
                    case = (noise, con, blur, R, round(sharp, 2), info["edge_sigma_px"], r - R)
                    if blur >= 3.0:
                        assert not usable, case
                    elif noise <= 0.01 or (noise <= 0.02 and con >= 0.4) or (blur <= 0.5 and con >= 0.4):
                        assert usable, case
                    if usable:
                        assert abs(r - R) < min(0.45, 2.0 * sigma_r), case
    # an unknown edge width is not usable; an observation for IrisTerm: diameter and its sigma
    assert not S.limbus_is_sharp(5.0, None) and not S.limbus_is_sharp(5.0, float("nan"))
    assert S.limbus_is_sharp(5.0, 1.0) and not S.limbus_is_sharp(0.5, 1.0) and not S.limbus_is_sharp(5.0, 3.0)
    assert S.iris_observation(2, "L", 15.0, 0.5) == (2, "L", 30.0, 1.0)
    with pytest.raises(ValueError):
        S.fit_limbus(np.full((60, 60), 0.5), (30.0, 30.0), 12.0)      # no edge anywhere


# =========================================================================== scale report
def test_scale_conflict_flag():
    cal = S.scale_source("caliper", 0.020, 0.004)
    card = S.scale_source("card", 0.052, 0.010)          # 3.2 % apart, 2.98 combined sigma -> conflict
    iris = S.scale_source("iris", 0.060, 0.051)          # 4 % apart but within 2 sigma -> no conflict
    rep = S.scale_report(0.02, 0.0037, [cal, iris, "global_size"])
    assert not rep["conflict"] and rep["mode"] == "measured" and rep["label"] == "caliper+iris+population"
    rep = S.scale_report(0.02, 0.0037, [cal, card])
    assert rep["conflict"] and rep["findings"][0]["code"] == "S-CONFLICT"
    assert rep["findings"][0]["detail"] == {"a": "caliper", "b": "card"}
    # > 2 sigma but below 1 %: no conflict (both conditions are needed)
    rep = S.scale_report(0.0, 0.001, [S.scale_source("caliper", 0.0, 0.001), S.scale_source("caliper", 0.008, 0.001)])
    assert not rep["conflict"]
    # population sources never conflict with metric ones; prior-only mode and label
    rep = S.scale_report(0.0, 0.045, ["global_size"])
    assert rep["mode"] == "prior" and rep["label"] == "population" and rep["sigma_pct"] == pytest.approx(4.5)
    assert S.scale_report(0.0, 0.05, [])["label"] == "none"
    # implied log-size of a chord
    X = np.array([[0.0, 0.0, 0.0], [100.0, 0.0, 0.0], [0.0, 50.0, 0.0]])
    src = S.chord_scale_source(X, 0, 1, 110.0, X)
    assert src["zeta"] == pytest.approx(math.log(1.1)) and src["sigma"] == pytest.approx(0.5 / 110.0)
    # log-size gradient matches finite differences
    rng = np.random.default_rng(2)
    T = rng.normal(scale=50.0, size=(10, 3))
    Y = 1.05 * T @ rodrigues(np.array([0.1, -0.2, 0.05])).T + rng.normal(scale=2.0, size=(10, 3)) + 5.0
    G = S.log_size_gradient(Y, T)
    h = 1e-5
    for i, j in ((0, 0), (3, 2), (7, 1)):
        Yp, Ym = Y.copy(), Y.copy()
        Yp[i, j] += h
        Ym[i, j] -= h
        assert G[i, j] == pytest.approx((S.log_size(Yp, T) - S.log_size(Ym, T)) / (2 * h), rel=1e-5, abs=1e-10)
    z, s = S.log_size_posterior(Y, np.eye(30) * 4.0, T)
    assert z == pytest.approx(S.log_size(Y, T)) and s == pytest.approx(2.0 * np.linalg.norm(G))


def test_reported_scale_pair():
    """reported_scale (review WP-15): value = Umeyama log-size; SD^2 = reference^2 + max(1, chi2)
    shape^2 + definition^2, with reference = scale-mode SD and shape^2 = g^T C g - reference^2
    (uncorrelated split: g^T x = 1 makes g = l + (g - l) with l^T C (g - l) = 0)."""
    rng = np.random.default_rng(5)
    T = rng.normal(scale=50.0, size=(8, 3))
    X = 1.04 * T @ rodrigues(np.array([0.1, 0.2, -0.1])).T + rng.normal(scale=1.0, size=T.shape)
    A = rng.normal(size=(24, 24))
    C = A @ A.T * 0.05 + np.eye(24) * 0.3
    sdef = np.linspace(0.0, 2.0, 8)

    class R:                                   # a minimal bundle result
        pass
    res = R()
    res.X, res.cov, res.chi2_red, res.sigma_def_mm = X, C, 2.5, sdef
    rs = S.reported_scale(res, T)
    g = S.log_size_gradient(X, T)
    assert float(g.reshape(-1) @ X.reshape(-1)) == pytest.approx(1.0, rel=1e-9)     # Euler: g^T x = 1
    mode = S.scale_mode(res)
    assert rs["zeta"] == pytest.approx(S.log_size(X, T)) and rs["reference_sigma"] == pytest.approx(mode["sigma"])
    post = S.log_size_posterior(X, C, T)[1]
    assert rs["shape_sigma"] == pytest.approx(math.sqrt(post ** 2 - mode["sigma"] ** 2))
    assert rs["definition_sigma"] == pytest.approx(math.sqrt(float(np.sum(sdef[:, None] ** 2 * g ** 2))))
    assert rs["chi2_inflation"] == 2.5
    assert rs["sigma"] == pytest.approx(math.sqrt(mode["sigma"] ** 2 + 2.5 * rs["shape_sigma"] ** 2
                                                  + rs["definition_sigma"] ** 2))
    assert rs["sigma"] > post > mode["sigma"]
    # chi2 < 1 never shrinks it; overrides; no definition floor
    r1 = S.reported_scale(res, T, chi2_red=0.5, sigma_def_mm=0.0)
    assert r1["chi2_inflation"] == 1.0 and r1["sigma"] == pytest.approx(post) and r1["definition_sigma"] == 0.0
    # the chord's definition bias (D-06): sigma = sqrt(0.5^2 + 1.5^2 + 1.5^2)
    ch = S.ChordTerm(0, 1, 140.0, definition_sigma_mm=(1.5, 1.5))
    assert ch.sigma == pytest.approx(math.sqrt(0.25 + 4.5)) and ch.sigma_mm == 0.5
    st = _state(X, [])
    d = float(np.linalg.norm(X[0] - X[1]))
    assert ch.residuals(st, np.zeros(0))[0] == pytest.approx((d - 140.0) / ch.sigma)
    assert S.ChordTerm(0, 1, 140.0).sigma == 0.5
    with pytest.raises(ValueError):
        S.ChordTerm(0, 1, 140.0, definition_sigma_mm=-1.0)
    src = S.chord_scale_source(X, 0, 1, 140.0, T, definition_sigma_mm=1.5)
    assert src["sigma"] == pytest.approx(math.sqrt(0.25 + 4.5) / 140.0)
    rep = S.scale_report(rs["zeta"], rs["sigma"], [src, "global_size"], reference_sigma=rs["reference_sigma"])
    assert rep["sigma_pct"] == pytest.approx(100 * rs["sigma"]) and rep["reference_sigma"] == rs["reference_sigma"]
    assert S.scale_report(0.0, 0.05, ["iris"])["reference_sigma_pct"] is None


# =========================================================================== mirror test
def _mirror_trials(kit, anat, seeds, noise_scale, asym, bias=False):
    from face3d.testbed.surface_subjects import out_of_prior_subject
    perm = anat["perm"]
    out = []
    for seed in seeds:
        rs, rr, rd, rm = [np.random.default_rng(s) for s in np.random.SeedSequence(4000 + seed).spawn(4)]
        a = float(rs.uniform(*asym)) if isinstance(asym, tuple) else float(asym)
        sub = out_of_prior_subject(kit, rs, asym_mm=a)
        X = sub.landmarks("anatomical44")
        rig = rigs.rear_phone(rr, n_views=4, X=X, target=anat["fc"])
        obs = detector_sim.simulate(X, anat["kinds"], rig, rd, definition_bias=bias, noise_scale=noise_scale)
        consensus = X + obs.bias_3d          # the many-view BA consensus shares the definition bias
        mv = int(rm.integers(0, 4))
        for k, cam in enumerate(rig.cameras):
            uv, cov = obs.uv[k], _sim_cov(obs, k)
            if k == mv:
                uv, _ = faults.mirror_view(uv, cam.width, perm)
                cov = M.flip_cov(cov, perm)
            d = M.mirror_test(uv, cam.width, perm, consensus, cov, cam, is_front_camera=False,
                              all_views_front=False, other_views_agree=False)
            out.append({"mirrored": k == mv, "d": d, "asym": sub.asym_rms_mm,
                        "args": (uv, cam.width, perm, consensus, cov, cam)})
    return out


def test_mirror_tpr_fpr(kit, anat):
    """40 seeds of 4-view rear-phone surface subjects (asymmetry >= 0.8 mm RMS) with one mirrored
    view: among cases with g >= g_min suggest_flip TPR >= 0.95; over all clean views FPR <= 0.02.
    FU-04: g_min (per view, from the complete decision rule; >= 8.16) and the gap threshold tau (13.83) are derived from ``mirror.flip_alpha`` /
    ``mirror.keep_power`` (the DESIGN values g_min = 4 and 2 sqrt(2 n_v) before)."""
    rows = _mirror_trials(kit, anat, range(40), LOW_NOISE, (0.85, 1.5))
    assert min(r["asym"] for r in rows) >= 0.8
    mir = [r["d"] for r in rows if r["mirrored"]]
    clean = [r["d"] for r in rows if not r["mirrored"]]
    det = [d for d in mir if d.g >= d.g_min]
    assert len(det) >= 30
    assert np.mean([d.decision == "suggest_flip" for d in det]) >= 0.95
    assert np.mean([d.decision == "suggest_flip" for d in clean]) <= 0.02
    for d in mir + clean:
        assert d.decision in M.DECISIONS and d.g <= d.g_raw + 1e-9
        assert d.margin == pytest.approx(d.gap - M.GAP_THRESHOLD)
        # g_min is per view (complete rule on the view's asymmetry pattern), never below the gap-only bound
        assert d.g_min >= M.G_MIN - 1e-9 and d.gap_threshold == pytest.approx(M.GAP_THRESHOLD)
        assert (d.power >= 0.95 - 1e-6) == (d.g >= d.g_min) or abs(d.g / d.g_min - 1.0) < 1e-3
        # a 'keep' is only given where the complete rule had 95 % power and the gap is not significant
        assert d.decision != "keep" or (d.g >= d.g_min and d.gap <= M.GAP_THRESHOLD)
        assert d.decision != "suggest_flip" or d.gap > M.GAP_THRESHOLD
        assert not d.preselect_flip or d.decision == "suggest_flip"
    # the flip hypothesis wins on mirrored views, loses on clean ones
    assert np.mean([d.delta > 0 for d in mir]) >= 0.95 and np.mean([d.delta < 0 for d in clean]) >= 0.95
    # rear camera, no agreeing views: never pre-selected
    assert not any(d.preselect_flip for d in mir)


@pytest.fixture(scope="module")
def mirror_nominal(kit, anat):
    """The mirror TPR/FPR scenario of the WBS row at the DESIGN 4.4 nominal detector noise."""
    return _mirror_trials(kit, anat, range(40), 1.0, (0.85, 1.5))


def test_mirror_nominal_noise_is_honest(mirror_nominal):
    """At the DESIGN 4.4 nominal detector noise ~1 mm of asymmetry is rarely resolvable from one
    view: the test must then answer 'undetermined' (H7) rather than a falsely reassuring 'keep',
    and never raise a false flip on a clean view (the WBS row's FPR <= 0.02 holds at nominal
    noise, over the same 40 seeds).  (With the WBS formula g_raw, which ignores what the pose
    refit absorbs, most mirrored views would be answered 'keep'.)"""
    mir = [r["d"] for r in mirror_nominal if r["mirrored"]]
    clean = [r["d"] for r in mirror_nominal if not r["mirrored"]]
    assert len(clean) == 120
    assert np.mean([d.decision == "suggest_flip" for d in clean]) <= 0.02
    assert np.mean([d.decision == "keep" for d in mir]) <= 0.3
    assert np.mean([d.g_raw >= 4.0 and d.decision != "suggest_flip" for d in mir]) >= 0.5


def _binom_lo(n: int, p: float) -> int:
    """Smallest k with P(Binomial(n, p) <= k) > 0.025 (exact)."""
    from math import comb
    cdf = 0.0
    for k in range(n + 1):
        cdf += comb(n, k) * p ** k * (1.0 - p) ** (n - k)
        if cdf > 0.025:
            return k
    return n


def test_mirror_tpr_spec_row_nominal_noise(mirror_nominal, kit, anat):
    """The WBS row after the FU-04 recalibration.  (WP-15 kept this as a strict xfail: with g_min = 4 and
    the absolute threshold 2 sqrt(2 n_v), the TPR among g >= 4 at nominal noise was 0.44.)  g_min is now
    the detectability at which the complete rule (gap > tau and delta > rel, capped costs) suggests the flip
    with probability 0.95, for the view's own asymmetry pattern:

    * at nominal noise no mirrored view of these 40 seeds reaches it (g median ~2), so none is answered
      'keep', the flips that are suggested all have a significant gap, and the target of the row is
      *unreachable* at this noise (recorded in docs/RESULTS.md; not asserted as met);
    * at half the nominal noise 12 of the 30 mirrored views reach their g_min, and among those the flip is
      found at the rate g_min promises (binomial 95 % bound of 'TPR >= 0.95')."""
    mir = [r["d"] for r in mirror_nominal if r["mirrored"]]
    assert not any(d.decision == "keep" for d in mir if d.g < d.g_min or d.gap > M.GAP_THRESHOLD)
    assert all(d.gap > M.GAP_THRESHOLD for d in mir if d.decision == "suggest_flip")
    assert sum(d.g >= d.g_min for d in mir) <= 4 and np.median([d.g for d in mir]) < M.G_MIN
    half = _mirror_trials(kit, anat, range(30), 0.5, (0.85, 1.5))
    det = [r["d"] for r in half if r["mirrored"] and r["d"].g >= r["d"].g_min]
    assert len(det) >= 10
    assert sum(d.decision == "suggest_flip" for d in det) >= _binom_lo(len(det), 0.95)
    assert not any(r["d"].decision == "suggest_flip" for r in half if not r["mirrored"])


def test_mirror_undetermined_and_unverifiable(kit, anat):
    rows = _mirror_trials(kit, anat, range(100, 110), LOW_NOISE, 0.0)
    assert np.mean([r["d"].decision == "undetermined" for r in rows]) >= 0.9
    # all-front-camera set -> unverifiable; inputs unchanged
    from face3d.testbed.surface_subjects import out_of_prior_subject
    sub = out_of_prior_subject(kit, np.random.default_rng(7))
    X = sub.landmarks("anatomical44")
    rig, _ = faults.selfie_rig(np.random.default_rng(8), target=anat["fc"])
    obs = detector_sim.simulate(X, anat["kinds"], rig, np.random.default_rng(9))
    uv, cov = obs.uv[0], _sim_cov(obs, 0)
    args = (uv.copy(), cov.copy(), X.copy(), anat["perm"].copy())
    d = M.mirror_test(uv, rig.cameras[0].width, anat["perm"], X, cov, rig.cameras[0], is_front_camera=True,
                      all_views_front=True, other_views_agree=True)
    assert d.decision == "unverifiable" and not d.preselect_flip
    for a, b in zip(args, (uv, cov, X, anat["perm"])):
        assert np.array_equal(a, b, equal_nan=True)
    st = M.project_mirror_status([d], all_views_front=True)
    assert st["status"] == "unverifiable"
    # pre-selection needs delta > 0.2 and the front camera (or agreeing views)
    rows = _mirror_trials(kit, anat, [0], LOW_NOISE, (1.2, 1.5))
    assert M.project_mirror_status([r["d"] for r in rows], False)["status"] == "suggest_flip"
    row = [r for r in rows if r["mirrored"]][0]
    d = row["d"]
    assert d.decision == "suggest_flip" and d.delta > 0.2 and not d.preselect_flip
    assert M.project_mirror_status([r["d"] for r in rows if not r["mirrored"]], False)["status"] == "keep"
    for kw in ({"is_front_camera": True, "other_views_agree": False},
               {"is_front_camera": False, "other_views_agree": True}):
        d2 = M.mirror_test(*row["args"], all_views_front=False, **kw)
        assert d2.decision == "suggest_flip" and d2.preselect_flip
    assert M.mirror_test(*row["args"], is_front_camera=True, all_views_front=False,
                         other_views_agree=False).rel_threshold == pytest.approx(0.10)


# =========================================================================== expression
def test_expression_tags_relative_and_fallbacks():
    neutral = {"jawOpen": 0.10, "mouthSmileLeft": 0.20, "mouthSmileRight": 0.18, "eyeBlinkLeft": 0.25,
               "eyeBlinkRight": 0.20, "browInnerUp": 0.10, "cheekSquintLeft": 0.1, "eyeWideLeft": 0.05}
    mild = dict(neutral, mouthSmileLeft=0.40)                       # Delta smile 0.20 -> mild
    expressive = dict(neutral, mouthSmileRight=0.50)                # Delta smile 0.32 -> expressive
    wide = dict(neutral, eyeWideLeft=0.40)                          # Delta eyeWide 0.35 -> expressive
    blink = dict(neutral, eyeBlinkRight=0.62)                       # Delta blink 0.42 -> expressive
    jaw = dict(neutral, jawOpen=0.20)                               # Delta jawOpen 0.10 -> mild
    tags = E.tag_from_blendshapes([neutral, mild, expressive, None, wide, blink, jaw])
    assert tags == ["neutral", "mild", "expressive", None, "expressive", "expressive", "mild"]
    # relative to the subject's own minimum: a resting smile score of 0.2 is neutral for this face
    assert E.tag_from_blendshapes([neutral, neutral])[0] == "neutral"
    # absolute 0.2 smile would not be neutral; relative to a reference view instead of the minimum
    assert E.tag_from_blendshapes([mild, neutral], neutral_ref=0) == ["neutral", "neutral"]
    assert E.tag_from_blendshapes([None, None]) == [None, None]
    # fallbacks without scores
    idx = {"ch_L": 0, "ch_R": 1, "lip_upper_inner": 2, "lip_lower_inner": 3, "sto": 4, "li": 5, "ex_L": 6, "ex_R": 7}
    uv = np.array([[1250.0, 1500], [1050, 1500], [1150, 1495], [1150, 1499], [1150, 1497], [1150, 1520],
                   [1330, 1300], [970, 1300]])
    w0 = E.mouth_width(uv, idx)
    assert w0 == pytest.approx(200.0 / 360.0)
    assert E.tag_fallback(uv, idx, w0) == ("neutral", [])           # gap 4 / 200 = 0.02
    open_mouth = uv.copy()
    open_mouth[3, 1] = 1510.0                                       # gap 15 / 200 = 0.075 -> drop sto, li
    assert E.tag_fallback(open_mouth, idx, w0) == ("neutral", [4, 5])
    wide_mouth = uv.copy()
    wide_mouth[0, 0], wide_mouth[1, 0] = 1265.0, 1035.0             # 230 / 200 = 1.15 x median -> mild
    assert E.tag_fallback(wide_mouth, idx, w0)[0] == "mild"
    # re-tagging escalates only
    assert E.retag_from_residuals(3.0) == "neutral" and E.retag_from_residuals(5.0) == "mild"
    assert E.retag_from_residuals(10.0) == "expressive" and E.retag_from_residuals(1.0, "mild") == "mild"
    assert E.MAX_RETAG_ROUNDS == 3
    assert E.mobile_chi2_red([2.0, 4.0, 6.0]) == pytest.approx(2.0)
    # lids and the no-neutral finding
    assert E.lid_drop(0.15, 0.0) and E.lid_drop(0.3, -13.0) and not E.lid_drop(0.3, 10.0)
    assert not E.lid_drop(None, None)
    f = E.no_neutral_view(["mild", "expressive", None])
    assert f["code"] == "E-NO-NEUTRAL" and f["detail"]["suppress_below_mm"] == 1.0
    assert E.no_neutral_view(["neutral", "mild"]) is None
    jc = E.jaw_config_for_tag("expressive")
    assert jc.enabled and jc.prior_sigma_deg == 3.0 and jc.bounds_deg == (0.0, 30.0)
    assert E.jaw_config_for_tag("neutral").prior_sigma_deg == 1.0


def test_expression_inflation_math():
    assert E.CLASS_MULT == {"rigid": (1, 1, 1.25), "semi_mobile": (1, 1.75, 2.5), "mobile": (1, 3, math.inf),
                            "jaw": (1, 1, 1)}
    classes = ["rigid", "semi_mobile", "mobile", "jaw"]
    sig, drop = E.expression_sigma_mm(classes, [1.25, 2.0, 1.5, 2.0], "expressive")
    assert np.allclose(sig[[0, 1, 3]], [math.sqrt(1.25 ** 2 - 1) * 1.25, math.sqrt(2.5 ** 2 - 1) * 2.0, 0.0])
    assert drop.tolist() == [False, False, True, False] and np.isinf(sig[2])
    sig, drop = E.expression_sigma_mm(classes, 1.5, "mild")
    assert np.allclose(sig, [0.0, math.sqrt(1.75 ** 2 - 1) * 1.5, math.sqrt(8.0) * 1.5, 0.0]) and not drop.any()
    sig, drop = E.expression_sigma_mm(classes, 1.5, "neutral")
    assert np.all(sig == 0) and not drop.any()
    with pytest.raises(ValueError):
        E.expression_sigma_mm(["unknown"], 1.0, "mild")
    # inflation adds P (s^2 I3) P^T; inputs untouched; dropped rows become NaN
    cam = orbit_camera(600.0, 20.0, 5.0, 26.0)
    X = np.array([[10.0, -30.0, 90.0], [30.0, 20.0, 70.0], [-25.0, -40.0, 85.0]])
    P = E.projection_jacobians(cam, X)
    h = 1e-4
    for i in range(3):
        for j in range(3):
            Xp, Xm = X.copy(), X.copy()
            Xp[i, j] += h
            Xm[i, j] -= h
            assert np.allclose(P[i, :, j], (cam.project(Xp)[i] - cam.project(Xm)[i]) / (2 * h), rtol=1e-6)
    cov = np.stack([np.eye(2) * 4.0] * 3)
    cov0 = cov.copy()
    # non-unit sigmas: adding sigma P P^T instead of sigma^2 P P^T is caught (review WP-15)
    out = E.inflate_view_cov(cov, P, np.array([2.0, 0.5, np.inf]))
    assert np.allclose(out[0], cov[0] + 4.0 * P[0] @ P[0].T) and np.allclose(out[1], cov[1] + 0.25 * P[1] @ P[1].T)
    assert np.isnan(out[2]).all()
    out = E.inflate_view_cov(cov, P, np.array([1.0, 0.0, np.inf]))
    assert np.allclose(out[0], cov[0] + P[0] @ P[0].T) and np.allclose(out[1], cov[1]) and np.isnan(out[2]).all()
    assert np.allclose(E.inflate_view_cov(cov, P, 3.0), cov + 9.0 * np.einsum("nij,nkj->nik", P, P))
    assert np.array_equal(cov, cov0)
    uv = cam.project(X)
    uv2, C2 = E.apply_expression(uv, cov, P, [2.0, 0.5, 1.0], [False, False, True])
    assert np.isnan(uv2[2]).all() and np.isnan(C2[2]).all() and np.isfinite(uv2[:2]).all()
    assert np.allclose(C2[0], cov[0] + 4.0 * P[0] @ P[0].T) and np.allclose(C2[1], cov[1] + 0.25 * P[1] @ P[1].T)
    assert np.array_equal(uv2[:2], uv[:2]) and np.array_equal(cov, cov0)
    assert E.expression_classes(["en_L", "ch_R", "pg", "prn", None]) == ["rigid", "mobile", "jaw", "semi_mobile",
                                                                       "semi_mobile"]


def test_smile_hard_gate(kit, anat):
    """DESIGN 4.9 hard gate: one 3 mm smile among five views, solved with expression inflation,
    moves the rigid-class landmarks < 0.3 mm (max over rigid landmarks, median over 10 seeds).

    Two readings, both checked: (a) noise-free data, the smiling view tagged expressive against
    the all-neutral solve; (b) nominal detector noise with common random numbers and the same tags
    in both solves (the only difference is the smile).  Without inflation the smile moves them
    > 0.3 mm, so the gate is not vacuous."""
    from face3d.model.landmark_prior import FactorPrior
    from face3d.testbed.surface_subjects import expression_field, out_of_prior_subject
    names, kinds = anat["names"], anat["kinds"]
    classes = E.expression_classes(names)
    rigid = np.array([c == "rigid" for c in classes])
    nm = NoiseModel(kinds)
    sig_n = np.array([KIND_SIGMA_MM[k][0] for k in kinds])
    prior = FactorPrior.from_package()
    mu = prior.mean()

    def solve(rig, Xs_by_view, G, inflate_view):
        views = []
        for k, cam in enumerate(rig.cameras):
            Xv = Xs_by_view[k]
            vis = rigs.visible_mask(cam, Xs_by_view[0])
            C = nm.view_cov(cam.f / cam.depth(Xv), float(np.ptp(cam.project(Xv)[vis, 0])))
            uv = cam.project(Xv) + np.einsum("nij,nj->ni", np.linalg.cholesky(C), G[k])
            uv[~vis] = np.nan
            C[~vis] = np.nan
            if k == inflate_view:
                se, drop = E.expression_sigma_mm(classes, sig_n, "expressive")
                uv, C = E.apply_expression(uv, C, E.projection_jacobians(cam, Xv), se, drop)
            views.append(ViewObs(uv, cam.copy(), f_prior=cam.f, f_prior_log_sigma=0.04, focal_group="phone",
                                 kinds=kinds, cov_px=C))
        return bundle_adjust(views, mu.copy(), None, prior=prior).X

    def moved(A, B):
        _, R, t = umeyama(B[rigid], A[rigid], with_scale=False)
        return float(np.linalg.norm((B @ R.T + t)[rigid] - A[rigid], axis=1).max())

    a_noise_free, b_noisy, c_no_inflation = [], [], []
    for seed in range(10):
        rs, rr, rd = [np.random.default_rng(s) for s in np.random.SeedSequence(5000 + seed).spawn(3)]
        sub = out_of_prior_subject(kit, rs)
        X = sub.landmarks("anatomical44")
        Xs = kit.landmark_positions("anatomical44", expression_field(kit, sub.V_true, "smile", 3.0))
        rig = rigs.rear_phone(rr, n_views=5, X=X, target=anat["fc"])
        sv = int(rd.integers(0, 5))
        G = rd.normal(size=(5, len(X), 2))
        neutral = [X] * 5
        smiling = [Xs if k == sv else X for k in range(5)]
        base0 = solve(rig, neutral, 0.0 * G, None)
        a_noise_free.append(moved(base0, solve(rig, smiling, 0.0 * G, sv)))
        b_noisy.append(moved(solve(rig, neutral, G, sv), solve(rig, smiling, G, sv)))
        c_no_inflation.append(moved(base0, solve(rig, smiling, 0.0 * G, None)))
    assert np.median(a_noise_free) < 0.3, a_noise_free
    assert np.median(b_noisy) < 0.3, b_noisy
    # the gate is not vacuous: without inflation the same smile moves the rigid landmarks > 0.3 mm
    assert np.median(c_no_inflation) > 0.3, c_no_inflation


# =========================================================================== camera model
def test_camera_model_selection():
    """Stereographic off-axis fault (35 deg, f35 13-16 mm) picks virtual_stereo in >= 0.8 of 20
    seeds; centred clean views (and rectilinear off-axis views) pick pinhole (DESIGN D-12)."""
    picks = {"stereo": [], "rect": [], "centred": []}
    flags = []
    for seed in range(20):
        rng = np.random.default_rng(700 + seed)
        names, X, _ = subjects.legacy_subject(rng)
        nm = NoiseModel(detector_sim.legacy_kinds(names))
        cam0 = orbit_camera(rng.uniform(500, 700), rng.uniform(-20, 20), rng.uniform(-5, 5), rng.uniform(13, 16))
        fc = X.mean(axis=0)
        for kind in (("stereo", "rect", "centred") if seed < 10 else ("stereo",)):
            if kind == "centred":
                cam, proj = cam0, cam0.project
            else:
                view, _ = faults.off_axis_wide(cam0, fc, 35.0, "stereographic" if kind == "stereo" else "rectilinear",
                                                   face_points=X)
                cam, proj = view.camera, view.project
            uv = proj(X)
            C = nm.view_cov(cam.f / cam.depth(X), float(np.ptp(uv[:, 0])))
            uv = uv + np.einsum("nij,nj->ni", np.linalg.cholesky(C), rng.normal(size=(len(X), 2)))
            init = cam.copy()
            init.R = rodrigues(rng.normal(scale=0.01, size=3)) @ init.R
            init.t = init.t + rng.normal(scale=5.0, size=3)
            out = CM.select_camera_model(uv, X + rng.normal(scale=0.7, size=X.shape), init, C, fc)
            picks[kind].append(out)
            if kind == "stereo":
                flags.append(CM.k1_flag(out["k1"], out["k1_sigma"]))
    assert np.mean([o["model"] == "virtual_stereo" for o in picks["stereo"]]) >= 0.8
    assert all(o["model"] == "pinhole" and not o["ambiguous"] and o["sigma_mult"] == 1.0 for o in picks["centred"])
    assert np.mean([o["model"] in ("pinhole", "virtual_rectilinear") for o in picks["rect"]]) >= 0.8
    o = picks["stereo"][0]
    assert set(o["costs"]) == set(CM.MODELS) and o["costs"]["k1"] >= o["raw_costs"]["k1"]
    assert 34.0 < o["theta_deg"] < 36.0
    # a stereographic face warp looks like a strong k1 to a pinhole fit (DESIGN 4.3 diagnostic)
    assert np.mean(flags) >= 0.8
    assert not any(CM.k1_flag(c["k1"], c["k1_sigma"]) for c in picks["centred"])


def test_lens_flags():
    assert CM.k1_flag(0.07, 0.02) and not CM.k1_flag(0.05, 0.02) and not CM.k1_flag(0.1, 0.0)
    rho = np.linspace(10.0, 300.0, 30)
    assert CM.radial_magnification_error(0.06 * rho + 1.0, rho) == pytest.approx(0.06)
    assert CM.radial_slope_flag(0.06 * rho, rho) and not CM.radial_slope_flag(0.03 * rho, rho)
    assert not CM.radial_slope_flag([1.0, np.nan], [1.0, 2.0])
    assert CM.huber_cost([1.0, 3.0, np.nan], 2.0) == pytest.approx(1.0 + 12.0 - 4.0)
    codes = [f["code"] for f in CM.lens_findings(0.1, 0.02, 0.08, photo_id="p2")]
    assert codes == ["C-K1", "C-RADIAL-SLOPE"] and CM.lens_findings(0.01, 0.02, 0.01) == []


def test_indistinguishable_models_merge():
    """On a very noisy view every hypothesis predicts the same image within the noise: they are
    merged into the simplest model (pinhole), which is then not 'ambiguous' (no sigma x 3)."""
    rng = np.random.default_rng(11)
    names, X, _ = subjects.legacy_subject(rng)
    cam0 = orbit_camera(650.0, 0.0, 0.0, 14.0)
    view, _ = faults.off_axis_wide(cam0, X.mean(axis=0), 20.0, "stereographic", face_points=X)
    uv = view.project(X)
    nm = NoiseModel(detector_sim.legacy_kinds(names))
    C = nm.view_cov(view.camera.f / view.camera.depth(X), float(np.ptp(uv[:, 0]))) * 400.0   # very noisy view
    uv = uv + np.einsum("nij,nj->ni", np.linalg.cholesky(C), rng.normal(size=(len(X), 2)))
    out = CM.select_camera_model(uv, X, view.camera, C, X.mean(axis=0))
    assert out["model"] == "pinhole" and set(out["equivalent_to"]) == {"virtual_rectilinear", "virtual_stereo", "k1"}
    assert not out["ambiguous"] and out["sigma_mult"] == 1.0


# =========================================================================== retouch
def _retouch_ids(names):
    """Retouch-test landmark ids on the legacy synthetic names (en, ex, go, p per side)."""
    return {f"{b}_{side}": names.index(f"{long}_{side}") for b, long in
            (("en", "endocanthion"), ("ex", "exocanthion"), ("go", "gonion"), ("p", "pupil")) for side in "LR"}


def _retouch_trials(noise_scale, n_seeds=40):
    """(tp, fp) flags of the retouch test: beauty warp (eyes +6 %, jaw -4 %) in 1 of 4 views of
    the WP-01 rear-phone rig.  Each view is posed (WP-06 PnP + robust refine) against the
    consensus (truth + the shared definition bias, the many-view BA limit); outliers are
    excluded as the bundle's inlier mask would."""
    tp, fp = [], []
    for seed in range(n_seeds):
        r_subj, r_rig, r_det = _seed_streams(6000 + seed)
        names, X_true, _ = subjects.legacy_subject(r_subj)
        rig = rigs.rear_phone(r_rig, n_views=4, X=X_true)
        kinds = detector_sim.legacy_kinds(names)
        obs = detector_sim.simulate(X_true, kinds, rig, r_det, noise_scale=noise_scale)
        bv = int(r_det.integers(0, 4))
        uvs = [u.copy() for u in obs.uv]
        uvs[bv], _ = faults.beauty_warp(uvs[bv], faults.beauty_index_map(names, kinds))
        ids = _retouch_ids(names)
        consensus = X_true + obs.bias_3d
        for v, c in enumerate(rig.cameras):
            cov = _sim_cov(obs, v)
            inl = np.isfinite(uvs[v][:, 0]) & ~obs.outlier_mask[v]
            Xi = consensus[inl]
            r = solve_pnp(Xi, uvs[v][inl], c.width, c.height, f_px=c.f, estimate_focal=False,
                          sigma_px=CM._cov_sigma_px(cov[inl]))
            cam = Camera(c.f, c.cx, c.cy, c.width, c.height)
            proj = CM._pinhole_proj(cam)
            cam.R, cam.t, _, _ = CM.refine_pose(lambda R_, t_, x_: proj(R_, t_, x_, Xi), r.camera.R, r.camera.t,
                                                uvs[v][inl], whitening(cov[inl]), jac=CM._pinhole_jac(cam, Xi))
            _, _, flagged = CM.retouch_residual_test(uvs[v], cam.project(consensus), ids, cov, inliers=inl)
            (tp if v == bv else fp).append(flagged)
    return tp, fp


@pytest.fixture(scope="module")
def retouch_nominal():
    """The retouch scenario of the WBS row at the DESIGN 4.4 nominal detector noise (20 seeds,
    80 views; the 40-seed run measured TPR 0.25 and FPR 0.0)."""
    return _retouch_trials(1.0, n_seeds=20)


def test_retouch_nominal_noise_no_false_alarms(retouch_nominal):
    """At nominal detector noise the clean-view half of the WBS row holds (FPR <= 0.05)."""
    tp, fp = retouch_nominal
    assert len(fp) == 60 and np.mean(fp) <= 0.05, np.mean(fp)


@pytest.mark.xfail(strict=True, reason="WBS WP-15 retouch row at nominal noise: a single view cannot resolve the "
                   "6 % / 4 % beauty warp at the DESIGN 4.4 nominal detector noise (measured TPR 0.25). Escalated "
                   "for a spec decision (amend the row to the reduced-noise condition or the warp size); strict, so "
                   "a change that fixes it is noticed.")
def test_retouch_tpr_spec_row_nominal_noise(retouch_nominal):
    """The WBS row itself at nominal noise: beauty-warped views flagged >= 0.8."""
    tp, _ = retouch_nominal
    assert np.mean(tp) >= 0.8


def test_retouch_residual_flags_beauty_warp():
    """Beauty warp (eyes +6 %, jaw -4 %) in 1 of 4 views is flagged in >= 0.8 of the trials; clean
    views <= 0.05 (DESIGN 4.1 Q-RETOUCH, 7.4), at 0.2 x the nominal detector noise (LOW_NOISE; see
    the module docstring and the nominal-noise tests above).  Each view is posed (WP-06 PnP +
    robust refine) against the consensus (truth + the shared definition bias, the many-view BA
    limit); outliers are excluded as the bundle's inlier mask would."""
    tp, fp = _retouch_trials(LOW_NOISE)
    assert np.mean(tp) >= 0.8, np.mean(tp)
    assert np.mean(fp) <= 0.05, np.mean(fp)
    # the statistics on an exact, noise-free warp of a frontal view; the Q-RETOUCH finding
    cam = orbit_camera(800.0, 0.0, 0.0, 26.0)
    names, X, _ = subjects.legacy_subject(np.random.default_rng(1))
    uv = cam.project(X)
    warped, _ = faults.beauty_warp(uv, faults.beauty_index_map(names))
    ids = _retouch_ids(names)
    cov = np.stack([np.eye(2)] * len(X))
    z, t_eye, flagged = CM.retouch_residual_test(warped, uv, ids, cov)
    assert flagged and z["eye_width_ratio"] > 3 and z["bigonial_ratio"] < -3 and t_eye > 3
    f = CM.retouch_finding(z, t_eye, flagged, photo_id="p1")
    assert f["code"] == "Q-RETOUCH" and f["action"] == "down_weight" and f["detail"]["exclude_texture"]
    z0, t0, f0 = CM.retouch_residual_test(uv, uv, ids, cov)
    assert not f0 and abs(z0["eye_width_ratio"]) < 1e-9 and abs(t0) < 1e-9
    with pytest.raises(KeyError):
        CM.retouch_residual_test(uv, uv, {"en_L": 0}, cov)


# =========================================================================== defaults
def test_defaults_registered_with_badges():
    for ns in ("scale", "mirror", "expression", "camera_model"):
        keys = [k for k in cfg.snapshot() if k.startswith(ns + ".")]
        assert keys, ns
        for k in keys:
            d = cfg.get(k)
            assert d.badge in cfg.BADGES and d.source
    assert cfg.get("scale.iris_mean_mm").value == 11.8 and cfg.get("scale.iris_mean_mm").badge == "✅"
    assert cfg.get("mirror.g_min").value == 4.0 and cfg.get("camera_model.k1_sigma").value == 0.02
    assert cfg.get("scale.card_length_mm").value == 85.60
    assert BUNDLE["scale_sigma_log"].value == 0.045
