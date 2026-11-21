"""WP-01: landmark test bed, gauge-projected coverage and the committed baseline scorecard."""
import ast
import json
import math
import time
from pathlib import Path

import numpy as np
import pytest

import face3d.solve.bundle as bundle_mod
from face3d.eval.align import (NOW7_LEGACY_NAMES, align, gauge_projector, now7_indices,
                               similarity_tangent_basis)
from face3d.eval.coverage import axis_coverage, nees, scale_z
from face3d.geometry.procrustes import procrustes_rmse
from face3d.geometry.rotations import rodrigues
from face3d.synthetic import midline_indices, mirror_pairs, synthetic_landmarks
from face3d.testbed import detector_sim, rigs, scorecard, subjects
from face3d.testbed.detector_sim import KIND_SIGMA_DEF_MM, legacy_kinds, simulate
from face3d.testbed.scenarios import FAST_SCENARIOS, METRIC_KEYS, SCENARIOS, Scenario, run_scenario

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "tests" / "golden" / "baseline_scorecard_v0.json"
FIRST3 = [1000, 1001, 1002]


@pytest.fixture(scope="module")
def rear_phone_first3():
    """rear_phone_legacy on seeds 1000-1002 with the default (legacy) engine; shared by two tests."""
    return run_scenario(SCENARIOS["rear_phone_legacy"], FIRST3)


def _random_spd(rng, n, scale=4.0):
    A = rng.normal(size=(n, n))
    return scale * (A @ A.T / n + 0.2 * np.eye(n))


# ------------------------------------------------------------------ eval.align
def test_gauge_projector_removes_similarity():
    rng = np.random.default_rng(0)
    X = rng.normal(scale=50.0, size=(20, 3))
    G = similarity_tangent_basis(X)
    assert G.shape == (60, 7)
    assert similarity_tangent_basis(X, rigid_only=True).shape == (60, 6)
    P = gauge_projector(X)
    for _ in range(20):
        v = G @ rng.normal(size=7)
        assert np.linalg.norm(P @ v) < 1e-9 * np.linalg.norm(v)
    assert np.abs(P - P.T).max() < 1e-12
    assert np.abs(P @ P - P).max() < 1e-12
    assert np.isclose(np.trace(P), 60 - 7)
    # Column semantics: translation along y, rotation about z, scale about the centroid.
    Xc = X - X.mean(0)
    assert np.allclose(G[1::3, 1], 1.0) and np.allclose(G[0::3, 1], 0.0)
    assert np.allclose(G[:, 5].reshape(-1, 3), np.cross([0.0, 0.0, 1.0], Xc))
    assert np.allclose(G[:, 6].reshape(-1, 3), Xc)
    # A small finite similarity motion is removed to second order.
    R = rodrigues(np.array([0.01, -0.02, 0.015]))
    Y = 1.01 * X @ R.T + np.array([3.0, -2.0, 1.0])
    d = (Y - X).ravel()
    assert np.linalg.norm(P @ d) < 0.03 * np.linalg.norm(d)
    # A genuine shape change survives the projection.
    s = rng.normal(size=60)
    assert np.linalg.norm(P @ s) > 0.8 * np.linalg.norm(s)
    Pr = gauge_projector(X, rigid_only=True)
    assert np.isclose(np.trace(Pr), 60 - 6)


def test_align_modes_recover_known_transforms():
    names, T = synthetic_landmarks()
    rng = np.random.default_rng(1)
    R = rodrigues(np.array([0.1, -0.2, 0.05]))
    t = np.array([5.0, -3.0, 12.0])
    ref = 1.07 * T @ R.T + t
    s, R_e, t_e, al = align(T, ref, "similarity")
    assert np.isclose(s, 1.07) and np.allclose(R_e, R) and np.allclose(al, ref)
    s, R_e, _, al = align(T, T @ R.T + t, "rigid")
    assert s == 1.0 and np.allclose(al, T @ R.T + t)
    # now7: rigid on the seven NoW landmarks only; other points may be anything.
    ref2 = T @ R.T + t
    junk = ref2.copy()
    idx7 = now7_indices(names)
    assert [names[i] for i in idx7] == list(NOW7_LEGACY_NAMES)
    others = np.setdiff1d(np.arange(len(T)), idx7)
    junk[others] += rng.normal(scale=20.0, size=(len(others), 3))
    s, R_e, _, al = align(T, junk, "now7", names=names)
    assert s == 1.0 and np.allclose(R_e, R) and np.allclose(al, ref2)
    with pytest.raises(ValueError):
        align(T, ref, "now7")
    with pytest.raises(ValueError):
        align(T, ref, "affine")
    # NaN rows are ignored by the fit but still transformed.
    bad = ref.copy()
    bad[3] = np.nan
    s, _, _, al = align(T, bad, "similarity")
    assert np.isclose(s, 1.07) and np.allclose(al, ref)


# ------------------------------------------------------------------ eval.coverage
def test_nees_is_one_for_calibrated_gaussian():
    rng = np.random.default_rng(2)
    n = 20
    C = _random_spd(rng, 3 * n)
    L = np.linalg.cholesky(C)
    X_ref = rng.normal(scale=50.0, size=(n, 3))
    vals = []
    for _ in range(2000):
        e = (L @ rng.normal(size=3 * n)).reshape(n, 3)
        v, dof = nees(e, C, X_ref, project=True)
        vals.append(v)
    assert dof == 3 * n - 7
    assert 0.95 <= np.mean(vals) <= 1.05, np.mean(vals)
    # Unprojected: full rank.
    e = (L @ rng.normal(size=3 * n)).reshape(n, 3)
    assert nees(e, C, X_ref, project=False)[1] == 3 * n


def test_axis_coverage_calibrated():
    rng = np.random.default_rng(3)
    n = 20
    C = _random_spd(rng, 3 * n)
    L = np.linalg.cholesky(C)
    X_ref = rng.normal(scale=50.0, size=(n, 3))
    c1, c2 = [], []
    for _ in range(400):
        e = (L @ rng.normal(size=3 * n)).reshape(n, 3)
        cv = axis_coverage(e, C, X_ref, ks=(1, 2))
        c1.append(cv[1]); c2.append(cv[2])
    assert abs(np.mean(c1) - 0.683) < 0.02, np.mean(c1)
    assert abs(np.mean(c2) - 0.954) < 0.02, np.mean(c2)


def test_sigma_form_and_nan_rows():
    rng = np.random.default_rng(4)
    n = 15
    sig = rng.uniform(0.5, 3.0, size=(n, 3))
    X_ref = rng.normal(scale=40.0, size=(n, 3))
    e = rng.normal(size=(n, 3)) * sig
    a = nees(e, sig, X_ref)
    b = nees(e, np.diag(sig.ravel() ** 2), X_ref)
    c = nees(e, sigma=sig, X_ref=X_ref)
    assert np.allclose(a, b) and np.allclose(a, c)
    # A NaN row is dropped consistently from error, covariance and reference.
    e2 = e.copy(); e2[4] = np.nan
    keep = np.arange(n) != 4
    v_nan = nees(e2, sig, X_ref)
    v_sub = nees(e[keep], sig[keep], X_ref[keep])
    assert v_nan[1] == 3 * (n - 1) - 7 and np.isclose(v_nan[0], v_sub[0])
    Xn = X_ref.copy(); Xn[7] = np.nan
    keep7 = np.arange(n) != 7
    assert np.isclose(axis_coverage(e, sig, Xn)[1], axis_coverage(e[keep7], sig[keep7], X_ref[keep7])[1])
    assert scale_z(0.05, 0.02, 0.03) == pytest.approx(1.0)


# ------------------------------------------------------------------ subjects
def test_subjects_independent_of_prior():
    path = ROOT / "face3d" / "testbed" / "subjects.py"
    tree = ast.parse(path.read_text())
    pkg = ["face3d", "testbed"]
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = pkg[:len(pkg) - node.level + 1] if node.level else []
            mod = ".".join(base + ([node.module] if node.module else []))
            imported.append(mod)
            imported += [mod + "." + a.name for a in node.names]
    assert imported, "expected some imports"
    assert not [m for m in imported if m == "face3d.model" or m.startswith("face3d.model.")], imported
    for gen in (subjects.legacy_subject, subjects.smooth_field_subject):
        names, X, meta = gen(np.random.default_rng(5))
        assert meta["inverse_crime"] is False
        assert X.shape == (len(names), 3) and np.isfinite(X).all()
        assert np.isclose(meta["log_scale_true"], subjects.log_scale_of(X, meta["template"]))


def test_smooth_field_subject_properties():
    names, T = synthetic_landmarks()
    a = subjects.smooth_field_subject(np.random.default_rng(6))
    b = subjects.smooth_field_subject(np.random.default_rng(6))
    assert np.array_equal(a[1], b[1])                                  # seeded, deterministic
    _, X, meta = subjects.smooth_field_subject(np.random.default_rng(6), asym_mm=0.0)
    for l, r in mirror_pairs(names):                                     # exactly symmetric
        assert np.allclose(X[l], X[r] * np.array([-1.0, 1.0, 1.0]))
    assert np.allclose(X[midline_indices(names), 0], 0.0)
    assert meta["generator"] == "smooth_field"
    assert abs(meta["log_scale_true"] - meta["zeta_drawn"]) < 0.03
    errs = [procrustes_rmse(T, subjects.smooth_field_subject(np.random.default_rng(s))[1]) for s in range(30)]
    assert 1.0 < np.median(errs) < 6.0                                   # a different face, not a new species
    zs = [subjects.smooth_field_subject(np.random.default_rng(s))[2]["zeta_drawn"] for s in range(300)]
    assert abs(np.std(zs) - subjects.LOG_SCALE_SD) < 0.15 * subjects.LOG_SCALE_SD


# ------------------------------------------------------------------ detector simulator
def test_legacy_kinds_cover_synthetic_names():
    names, _ = synthetic_landmarks()
    kinds = legacy_kinds(names)
    assert "generic" not in kinds
    assert detector_sim.legacy_kind("cheilion_R") == "sharp_junction"
    assert detector_sim.legacy_kind("pupil_L") == "iris"
    assert detector_sim.legacy_kind("unknown_point") == "generic"


def test_detector_sim_bias_shared_across_views():
    names, T = synthetic_landmarks()
    kinds = legacy_kinds(names)
    # Noise and outliers off: every view sees exactly project(X + b) with the same b.
    _, X, _ = subjects.legacy_subject(np.random.default_rng(7))
    rig = rigs.rear_phone(np.random.default_rng(8), X=X)
    obs = simulate(X, kinds, rig, np.random.default_rng(9), outlier_frac=0.0, noise_scale=0.0)
    assert obs.bias_3d.shape == X.shape and np.abs(obs.bias_3d).max() > 0
    for cam, uv, vis in zip(rig.cameras, obs.uv, obs.visible):
        assert vis.sum() >= 6
        assert np.allclose(uv[vis], cam.project(X[vis] + obs.bias_3d[vis]), atol=1e-9)
    off = simulate(X, kinds, rig, np.random.default_rng(9), outlier_frac=0.0, noise_scale=0.0,
                   definition_bias=False)
    assert not np.any(off.bias_3d)
    # Bias SD per kind over 200 subjects matches KIND_SIGMA_DEF_MM within 10 %.
    rig1 = rigs.rear_phone(np.random.default_rng(10), n_views=1)
    rng = np.random.default_rng(11)
    B = np.stack([simulate(T, kinds, rig1, rng).bias_3d for _ in range(200)])   # (200, N, 3)
    kinds_arr = np.array(kinds)
    for kind in set(kinds):
        sel = B[:, kinds_arr == kind, :]
        target = KIND_SIGMA_DEF_MM[kind]
        if target == 0.0:
            assert not np.any(sel)
        else:
            sd = float(np.sqrt(np.mean(sel ** 2)))
            assert abs(sd / target - 1.0) < 0.10, (kind, sd, target)


def test_detector_noise_is_anisotropic_and_calibrated():
    names, T = synthetic_landmarks()
    kinds = legacy_kinds(names)
    rig = rigs.rear_phone(np.random.default_rng(12), X=T)
    zt, zn, n_out, n_vis = [], [], 0, 0
    rng = np.random.default_rng(13)
    for _ in range(40):
        obs = simulate(T, kinds, rig, rng, outlier_frac=0.10, definition_bias=False)
        tdir = obs.tangent_dirs
        ndir = np.column_stack([-tdir[:, 1], tdir[:, 0]])
        for cam, uv, sig, out in zip(rig.cameras, obs.uv, obs.sigma_px_true, obs.outlier_mask):
            vis = ~np.isnan(uv[:, 0])
            clean = vis & ~out
            r = uv[clean] - cam.project(T[clean])
            zt.append(np.einsum("ij,ij->i", r, tdir[clean]) / sig[clean, 1])
            zn.append(np.einsum("ij,ij->i", r, ndir[clean]) / sig[clean, 0])
            n_out += int(out.sum()); n_vis += int(vis.sum())
    zt, zn = np.concatenate(zt), np.concatenate(zn)
    assert abs(np.std(zt) - 1.0) < 0.05 and abs(np.std(zn) - 1.0) < 0.05
    assert abs(n_out / n_vis - 0.10) < 0.02
    # Pixel sigma follows f / z: same landmark, nearer view -> larger sigma.
    obs = simulate(T, kinds, rig, rng)
    sig0 = obs.sigma_px_true[2][:, 0]
    ppm = rig.cameras[2].f / rig.cameras[2].depth(T)
    sn = np.array([detector_sim.KIND_SIGMA_MM[k][0] for k in kinds])
    ok = np.isfinite(sig0)
    assert np.allclose(sig0[ok], (sn * ppm)[ok], rtol=0.02)   # bias shifts depth slightly


# ------------------------------------------------------------------ rigs
def test_rigs_have_enough_visible_landmarks():
    for name, proto in rigs.PROTOCOLS.items():
        for seed in range(20):
            _, X, _ = subjects.legacy_subject(np.random.default_rng(100 + seed))
            for pts in (None, X):
                rig = proto(np.random.default_rng(seed), X=pts)
                P = synthetic_landmarks()[1] if pts is None else pts
                n = rig.n_views
                assert n >= 1 and all(len(v) == n for v in (
                    rig.f_prior_px, rig.f_prior_log_sigma, rig.focal_group, rig.is_front_camera,
                    rig.view_yaw_deg))
                for cam in rig.cameras:
                    assert rigs.visible_mask(cam, P).sum() >= 6, (name, seed)
                    assert (cam.width, cam.height) == (3000, 4000)


def test_rig_protocol_parameters():
    rng = np.random.default_rng(14)
    r = rigs.rear_phone(rng)
    assert r.view_yaw_deg == [-60.0, -30.0, 0.0, 30.0, 60.0]
    assert len({round(c.f, 9) for c in r.cameras}) == 1 and set(r.focal_group) == {"phone"}
    assert all(600 <= d <= 1500 for d in r.distance_mm)
    assert all(abs(np.log(fp / c.f)) < 0.05 for fp, c in zip(r.f_prior_px, r.cameras))
    assert set(r.f_prior_log_sigma) == {0.04}
    s = rigs.studio_ring(rng)
    assert np.allclose(s.view_yaw_deg, np.linspace(-90, 90, 7))
    assert all(1500 <= d <= 3000 for d in s.distance_mm) and np.isclose(s.cameras[0].focal_35mm, 85.0)
    f = rigs.selfie(rng)
    assert all(f.is_front_camera) and all(250 <= d <= 450 for d in f.distance_mm)
    assert all(-30 <= y <= 30 for y in f.view_yaw_deg)
    c = rigs.camera_roll(rng)
    assert sum(p is None for p in c.f_prior_px) == 2
    assert all(sg == 0.6 for p, sg in zip(c.f_prior_px, c.f_prior_log_sigma) if p is None)
    for g, cam in zip(c.focal_group, c.cameras):
        assert g == "roll_f%d" % round(cam.focal_35mm)


# ------------------------------------------------------------------ scenarios
def test_run_scenario_legacy_engine_fast(rear_phone_first3):
    recs = rear_phone_first3
    assert [r["seed"] for r in recs] == FIRST3
    for r in recs:
        assert not r["failed"], r["error"]
        for k in METRIC_KEYS:
            assert np.isfinite(r[k]), (k, r[k])
        assert 0.0 <= r["coverage_1s"] <= r["coverage_2s"] <= 1.0
        assert r["config_rms_mm"] < 8.0           # no catastrophic solve on these seeds
    # Legacy engine under the DESIGN 4.4 mm noise model: ~4 mm configuration RMS.
    assert np.median([r["config_rms_mm"] for r in recs]) < 5.0


def test_run_scenario_never_raises():
    def broken(*_args):
        raise np.linalg.LinAlgError("singular")

    def pnp_fail(*_args):
        raise RuntimeError("PnP failed")

    scn = SCENARIOS["rear_phone_legacy"]
    for eng in (broken, pnp_fail):
        recs = run_scenario(scn, [1000], engine_fn=eng)
        assert recs[0]["failed"] and recs[0]["error"]
        assert all(math.isnan(recs[0][k]) for k in METRIC_KEYS)

    def bad_subject(rng):
        raise ValueError("bad subject")
    recs = run_scenario(Scenario("x", bad_subject, rigs.rear_phone), [1, 2])
    assert all(r["failed"] for r in recs)


def test_scenarios_defined():
    expected = {"studio_ring_legacy", "rear_phone_legacy", "selfie_legacy", "camera_roll_legacy",
                "rear_phone_smooth", "rear_phone_nobias", "rear_phone_outliers"}
    assert set(SCENARIOS) == expected
    assert SCENARIOS["rear_phone_nobias"].detector_kwargs == {"definition_bias": False}
    assert SCENARIOS["rear_phone_outliers"].detector_kwargs == {"outlier_frac": 0.10}
    assert SCENARIOS["rear_phone_smooth"].subject_fn is subjects.smooth_field_subject
    assert len(FAST_SCENARIOS) == 3 and set(FAST_SCENARIOS) <= expected


# ------------------------------------------------------------------ scorecard
def test_baseline_scorecard_committed(rear_phone_first3):
    assert BASELINE.exists()
    sc = json.loads(BASELINE.read_text())
    assert sc["meta"]["engine_label"].startswith("legacy")
    assert sc["meta"]["seeds"] == list(range(1000, 1030))
    for name in SCENARIOS:
        assert name in sc["scenarios"], name
        for metric, agg in sc["scenarios"][name].items():
            assert agg["n_ok"] >= 28, (name, metric, agg)
    # File is in canonical form (sorted keys, 9 significant digits).
    assert scorecard.dumps(sc) == BASELINE.read_text()
    if not hasattr(bundle_mod, "ENGINE_VERSION"):
        stored = sc["per_seed_first3"]["rear_phone_legacy"]
        assert [d["seed"] for d in stored] == FIRST3
        for d, r in zip(stored, rear_phone_first3):
            assert d["failed"] == r["failed"]
            for k in sc["meta"]["metric_keys"]:
                if d[k] is None:
                    assert not np.isfinite(r[k])
                else:
                    assert r[k] == pytest.approx(d[k], rel=1e-5, abs=1e-12), k


def _synthetic_card(medians, mad_frac=0.05, n=30):
    return {
        "meta": {"seeds": list(range(1000, 1000 + n))},
        "scenarios": {name: {m: {"median": v, "mad": mad_frac * v, "n_ok": n} for m, v in ms.items()}
                      for name, ms in medians.items()},
    }


def test_compare_flags_regression():
    base_m = {"a": {"config_rms_mm": 2.0, "focal_rel_err": 0.01, "coverage_1s": 0.68},
              "b": {"config_rms_mm": 3.0, "focal_rel_err": 0.02, "coverage_1s": 0.68}}
    base = _synthetic_card(base_m)
    assert scorecard.compare(base, base) == []
    worse = json.loads(json.dumps(base))
    worse["scenarios"]["a"]["config_rms_mm"]["median"] *= 1.05
    assert scorecard.compare(base, worse) == ["a:config_rms_mm"]
    slightly = json.loads(json.dumps(base))
    slightly["scenarios"]["b"]["config_rms_mm"]["median"] *= 1.01           # within 2 %
    assert scorecard.compare(base, slightly) == []
    better = json.loads(json.dumps(base))
    better["scenarios"]["a"]["config_rms_mm"]["median"] *= 0.8
    better["scenarios"]["a"]["coverage_1s"]["median"] = 0.1                 # not higher-is-worse
    assert scorecard.compare(base, better) == []
    gone = json.loads(json.dumps(base))
    gone["scenarios"]["b"]["config_rms_mm"].update(median=None, n_ok=0)
    assert set(scorecard.compare(base, gone)) == {"b:config_rms_mm", "b:n_ok"}
    # A subset run (fast mode) only compares shared scenarios. +2.5 % is inside the seed-noise
    # tolerance 3 * MAD / sqrt(30) = 2.7 % here; mad_k=0 gives the strict 2 % rule.
    sub = _synthetic_card({"b": {"config_rms_mm": 3.0 * 1.025, "focal_rel_err": 0.02}}, n=5)
    assert scorecard.compare(base, sub) == []
    assert scorecard.compare(base, sub, mad_k=0.0) == ["b:config_rms_mm"]
    # Against the committed baseline: identical -> nothing; 5 % worse on the low-spread
    # studio ring is flagged with the default tolerance.
    real = json.loads(BASELINE.read_text())
    assert scorecard.compare(real, real) == []
    r5 = json.loads(BASELINE.read_text())
    r5["scenarios"]["studio_ring_legacy"]["config_rms_mm"]["median"] *= 1.05
    assert "studio_ring_legacy:config_rms_mm" in scorecard.compare(real, r5)


def test_scorecard_cli_and_determinism(tmp_path):
    out = tmp_path / "sc.json"
    assert scorecard.main(["--scenarios", "rear_phone_legacy", "--seeds", "2", "--out", str(out),
                           "--git-rev", "test-rev"]) == 0
    sc = json.loads(out.read_text())
    assert sc["meta"]["git_rev"] == "test-rev" and sc["meta"]["seeds"] == [1000, 1001]
    assert sc["meta"]["numpy_version"] == np.__version__
    assert set(sc["scenarios"]) == {"rear_phone_legacy"}
    assert len(sc["per_seed_first3"]["rear_phone_legacy"]) == 2
    assert "runtime_s" not in sc["scenarios"]["rear_phone_legacy"]       # machine-dependent
    agg = sc["scenarios"]["rear_phone_legacy"]["config_rms_mm"]
    vals = [d["config_rms_mm"] for d in sc["per_seed_first3"]["rear_phone_legacy"]]
    assert agg["n_ok"] == 2 and np.isclose(agg["median"], np.median(vals))
    assert out.read_text() == scorecard.dumps(sc)                          # canonical, sorted
    again = scorecard.build_scorecard([SCENARIOS["rear_phone_legacy"]], 2, git_rev="test-rev")
    assert scorecard.dumps(again) == out.read_text()                      # deterministic
    assert scorecard.dumps({"x": 1.234567890123}) == '{\n "x": 1.23456789\n}\n'
    assert json.loads(scorecard.dumps({"x": float("nan")})) == {"x": None}


def test_fast_mode_runtime():
    t0 = time.perf_counter()
    sc = scorecard.build_scorecard([SCENARIOS[n] for n in FAST_SCENARIOS], scorecard.FAST_SEEDS,
                                   git_rev="test")
    assert time.perf_counter() - t0 <= 60.0
    assert set(sc["scenarios"]) == set(FAST_SCENARIOS)
