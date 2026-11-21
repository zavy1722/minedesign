"""WP-20: pipeline (project file, cached pure stages, CLI, job-folder protocol, isolated launcher).

Scenes are synthetic (provenance 'synthetic'): a surface subject of the procedural head
(WP-11 ``out_of_prior_subject``), a 5-view rear-phone rig at 600 x 800 px, detections from the test-bed
detector simulator, and shaded renders as ``.npy`` working copies generated at test time from seeds
(nothing but ``project.json`` and ``expected_result.json`` is committed).  LandmarkSets are written as
JSON outside the project folder (session data, TTL 0).
"""
import json
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pytest

from face3d.core import policy
from face3d.core.cache import StageCache
from face3d.core.policy import ConsentRecord, Scope
from face3d.core.schema import sha256_file
from face3d.io import image_ops
from face3d.io.landmarks import Face, LandmarkSet, load_landmarks, save_landmarks
from face3d.model.procedural_head import build_procedural_head
from face3d.model.registry import ANATOMICAL, load_scheme
from face3d.pipeline import cli, jobs, stages as S
from face3d.pipeline.project import Pin, PhotoRecord, Project, ProjectError
from face3d.testbed import detector_sim, rigs
from face3d.testbed.render import face_centre, render_view
from face3d.testbed.surface_subjects import out_of_prior_subject

#: the synthetic scene's inlier landmark reprojection exceeds the bl T2 gate (max 3 px; out-of-prior subject,
#: 5 % outliers): texture tests that are not about the gate relax it explicitly (recorded in the config)
NO_DOWNWEIGHT = {"downweight_sigma_mult": 1.0}       # the small synthetic faces carry Q-SMALL (warn) down-weights
RELAX = {"reproj_median_max_px": 99.0, "reproj_max_max_px": 999.0}
GOLDEN = Path(__file__).parent / "golden" / "pipeline_small"
W, H = 600, 800
REPO = Path(__file__).resolve().parents[1]


# ============================================================================ fixtures
def _scene(seed, n_views=5, asym_mm=None, detector=None):
    kit = build_procedural_head()
    ids = kit.landmark_names("anatomical44")
    kinds = [ANATOMICAL[i].kind for i in ids]
    r_subj, r_rig, r_det = (np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(3))
    kw = {} if asym_mm is None else {"asym_mm": asym_mm}
    sub = out_of_prior_subject(kit, r_subj, **kw)
    X = sub.landmarks("anatomical44")
    rig = rigs.rear_phone(r_rig, n_views, X=X, target=face_centre(kit), width=W, height=H)
    obs = detector_sim.simulate(X, kinds, rig, r_det, **(detector or {}))
    return kit, sub, rig, obs


def materialise(tmp: Path, seed=None, asym_mm=None, detector=None, template=None, n_views=5):
    """Project folder from the golden template (or a given one): working copies, sha256, consent,
    LandmarkSets (returned, and saved under ``tmp/_lm`` OUTSIDE the project)."""
    doc = json.loads((template or GOLDEN / "project.json").read_text())
    seed = doc["seed"] if seed is None else seed
    kit, sub, rig, obs = _scene(seed, n_views, asym_mm, detector)
    root = tmp / "proj"
    (root / "photos").mkdir(parents=True)
    doc["photos"] = doc["photos"][:n_views]
    sets = {}
    for k, (rec, cam) in enumerate(zip(doc["photos"], rig.cameras)):
        view = render_view(sub.V_true, kit, cam)
        np.save(root / rec["path"], (np.clip(view.image, 0, 1) * 255).astype(np.uint8))
        rec["sha256"] = sha256_file(root / rec["path"])
        uv = obs.uv[k]
        sets[rec["id"]] = LandmarkSet(
            "anatomical44", {"backend": "synthetic", "version": "1", "licence": "CC0-1.0",
                             "commercial_ok": True, "is_ml": False},
            {"sha256": rec["sha256"], "wh": [W, H], "orientation_applied": True, "input_flipped": False,
             "coords": "px_corner"}, [Face(1.0, uv, np.isfinite(uv[:, 0]))])
    (root / "project.json").write_text(json.dumps(doc))
    prj = Project.load(root / "project.json")
    consent = ConsentRecord(doc["consent_id"], "subject-001", "self", "v1", "test", "2026-01-01T00:00:00+00:00",
                            None, [], [p.sha256 for p in prj.photos], 30, "owner",
                            Scope.RECONSTRUCT | Scope.TEXTURE, attested_age=30)
    (root / "consent").mkdir()
    (root / "consent" / f"{doc['consent_id']}.json").write_text(consent.to_json())
    lm = tmp / "_lm"
    lm.mkdir()
    for pid, ls in sets.items():
        save_landmarks(ls, lm / f"{pid}.json")
    return prj, sets, consent, lm, (kit, sub, rig, obs)


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    """The golden scene materialised once, with one shared cache: tests copy the project folder and
    pass ``base['cache']``, so a stage whose inputs did not change is not recomputed (the cache is
    content-keyed, so sharing it between tests cannot leak state)."""
    tmp = tmp_path_factory.mktemp("golden")
    prj, sets, consent, lm, scene = materialise(tmp)
    # disk root outside the project: only LIKENESS_ASSET entries may reach it; the default LRU (64) would
    # evict the golden entries
    cache = StageCache(root=tmp / "stage_cache", max_items=1000)
    with policy.network_guard():                        # the whole golden run completes without network
        run = S.run_pipeline(prj, "report", cache=cache, landmark_sets=sets, consent=consent)
    return {"tmp": tmp, "prj": prj, "sets": sets, "consent": consent, "lm": lm, "run": run, "scene": scene,
            "cache": cache}


@pytest.fixture(scope="module")
def golden(base):
    return base


@pytest.fixture(scope="module")
def cli_run(base, tmp_path_factory):
    """``python -m face3d report`` on a copy of the golden project (fresh process-level cache): the
    stdout, the project folder and the solve folder it wrote."""
    import contextlib
    import io
    root = tmp_path_factory.mktemp("cli") / "proj"
    shutil.copytree(base["prj"].root, root, ignore=shutil.ignore_patterns("solves", "jobs", "audit.jsonl"))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cli.main(["report", "--project", str(root / "project.json"), "--landmarks", str(base["lm"])])
    return {"rc": rc, "out": buf.getvalue(), "root": root, "sol": root / "solves" / "0001"}


@pytest.fixture()
def proj(base, tmp_path):
    """A private copy of the golden project folder (+ its LandmarkSets, consent and the shared cache)."""
    root = tmp_path / "proj"
    shutil.copytree(base["prj"].root, root, ignore=shutil.ignore_patterns("solves", "jobs", "audit.jsonl"))
    prj = Project.load(root / "project.json")
    return {"prj": prj, "sets": base["sets"], "consent": base["consent"], "lm": base["lm"], "cache": base["cache"],
            "scene": base["scene"], "tmp": tmp_path}


def _landmark_files(root: Path):
    hits = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if "landmark" in p.name.lower():
            hits.append(p)
        elif p.suffix == ".json":
            try:
                if json.loads(p.read_text()).get("format") == "face3d.landmarks":
                    hits.append(p)
            except ValueError:
                pass
    return hits


def _files_under(root: Path):
    return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())


# ============================================================================ project file
def test_project_roundtrip_and_validation(proj):
    prj, tmp_path = proj["prj"], proj["tmp"]
    assert prj.provenance == "synthetic" and len(prj.photos) == 5
    prj.pins.append(Pin("p01", "prn", (310.5, 420.25), cls="novice", zoom=2.0))
    p = prj.save(tmp_path / "proj" / "copy.json")
    again = Project.load(p)
    assert again.to_json() == prj.to_json()
    assert json.loads(p.read_text())["format"] == "face3d.project"
    # closed enums fail closed
    bad = Project.load(tmp_path / "proj" / "project.json")
    bad.photos[0].rights_basis = "found_online"
    with pytest.raises(ProjectError):
        bad.validate()
    bad = Project.load(tmp_path / "proj" / "project.json")
    bad.settings["sex_prior"] = "inferred"
    with pytest.raises(ProjectError):
        bad.validate()
    bad.settings["sex_prior"] = "unspecified"
    bad.settings["population"] = "european"                     # never stored as ancestry
    with pytest.raises(ProjectError):
        bad.validate()
    bad.settings["population"] = "matched"
    bad.validate()
    bad.landmark_cache = {"keep": "yes"}
    with pytest.raises(ProjectError):
        bad.validate()


def test_add_photo_and_record_decision(tmp_path):
    prj = Project(consent_id="c1")
    prj.path = tmp_path / "p" / "project.json"
    (tmp_path / "p").mkdir()
    img = tmp_path / "p" / "a.npy"
    np.save(img, np.zeros((40, 30), np.uint8))
    rec = prj.add_photo(img, "self_shot", working_copy="a.npy")
    assert rec.id == "p01" and rec.sha256 == sha256_file(img) and rec.exif["wh"] == [30, 40]
    with pytest.raises(ProjectError):
        prj.add_photo(img, "self_shot")                         # duplicate
    other = tmp_path / "p" / "b.npy"
    np.save(other, np.ones((40, 30), np.uint8))
    with pytest.raises(ProjectError):
        prj.add_photo(other, "unknown")                         # rights basis fails closed
    d = prj.record_decision("mirror_flip", "p01", "cli")
    assert d["by"] == "cli" and prj.decision_for("mirror_flip", "p01") is d
    line = json.loads((tmp_path / "p" / "audit.jsonl").read_text().splitlines()[0])
    assert line["event"] == "decision_mirror_flip" and line["sha256"] == rec.sha256
    assert set(line) == {"event", "time", "data_class", "sha256", "scope", "detail_code"}
    with pytest.raises(ProjectError):
        prj.record_decision("mirror_flip", "p01", "robot")


# ============================================================================ CLI end to end
def test_cli_end_to_end_synthetic_project(cli_run):
    root, sol, out = cli_run["root"], cli_run["sol"], cli_run["out"]
    assert cli_run["rc"] == 0
    res = json.loads((sol / "result.json").read_text())
    assert res["format"] == "face3d.result" and res["tier"]["code"] in "ABCD"
    assert res["scale"]["mode"] in ("prior", "iris", "measured") and res["scale"]["sigma_pct"] > 0
    assert {r["name"] for r in res["regions"]} >= {"eyes", "nose", "lips", "chin", "ears"}
    assert all(r["status"] in ("measured", "constrained", "prior-driven", "unobserved") for r in res["regions"])
    assert isinstance(res["flags"], list) and res["banner"] == "Not validated against a scan."
    assert len(res["cameras"]) == 5 and all(c["focal_status"] for c in res["cameras"])
    assert "licence" in res["run"] and res["run"]["licence"]["commercial_ok"] is True
    z = np.load(sol / "arrays.npz")
    assert z["X"].shape == (44, 3) and z["vertices"].shape[1] == 3 and z["sigma_n"].shape == (z["vertices"].shape[0],)
    for name, m in res["arrays"].items():
        assert m["sha256"] and m["file"] == "arrays.npz"
    text = (sol / "report.txt").read_text()
    assert text.startswith("Not validated against a scan.\n")
    assert f"Tier {res['tier']['code']}" in text and "Scale mode:" in text and "Focal length:" in text
    assert "Active unverified defaults:" in text and "Flags:" in text and "Region claims (worst first):" in text
    # worst first: the first claim line has the lowest status rank
    first = text.split("Region claims (worst first):\n")[1].splitlines()[0]
    assert first.strip().lower().startswith(("ears", "cranium"))
    assert "Not validated against a scan." in out and "result:" in out
    assert json.loads((root / "project.json").read_text())["active_solve"] == "solves/0001"
    # landmark caches are BIOMETRIC_GEOMETRY with TTL 0: nothing landmark-like was written under the project,
    # and nothing biometric reached the on-disk stage cache
    assert _landmark_files(root) == [] and not (root / "landmarks").exists()
    cache_dir = root / "cache"
    assert not cache_dir.exists() or [p for p in cache_dir.glob("*.json")] == []
    # triage-only commands write no solve folder; the solve folder is immutable (a new run gets 0002)
    assert cli.main(["triage", "--project", str(root / "project.json"), "--quiet"]) == 0
    assert sorted(p.name for p in (root / "solves").iterdir()) == ["0001"]


def test_cli_usage_and_testbed_delegation(monkeypatch, proj, capsys):
    assert cli.main(["solve"]) == 2                              # --project is required
    assert cli.main(["nonsense"]) == 2
    seen = {}
    from face3d.testbed import scorecard
    monkeypatch.setattr(scorecard, "main", lambda argv: seen.setdefault("argv", list(argv)) and 0)
    assert cli.main(["testbed", "scorecard", "--fast", "--out", "x.json"]) == 0
    assert seen["argv"] == ["--fast", "--out", "x.json"]
    # triage runs without landmarks and without a consent record
    prj = proj["prj"]
    (prj.root / "consent" / f"{prj.consent_id}.json").unlink()
    assert cli.main(["triage", "--project", str(prj.path)]) == 0
    assert "stages run: ingest, triage" in capsys.readouterr().out


# ============================================================================ cache
def test_stage_cache_hits_and_downstream_invalidation(proj):
    prj, sets, consent = proj["prj"], proj["sets"], proj["consent"]
    own = StageCache()
    kw = dict(landmark_sets=sets, consent=consent)
    r1 = S.run_pipeline(prj, "landmarks", cache=own, **kw)
    assert r1.executed == ["ingest", "triage", "landmarks"] and r1.cache_hits == []
    r2 = S.run_pipeline(prj, "landmarks", cache=own, **kw)
    assert r2.executed == [] and r2.cache_hits == r1.executed
    prj.pins.append(Pin("p01", "prn", tuple(sets["p01"].faces[0].uv[list(ANATOMICAL).index("prn")] + 4.0),
                        cls="novice", zoom=2.0))
    r3 = S.run_pipeline(prj, "landmarks", cache=own, **kw)
    assert r3.cache_hits == ["ingest", "triage"] and r3.executed == ["landmarks"]
    # the pin moved the nose tip observation and carries its own sigma
    lm = r3.outputs["landmarks"]
    j = list(ANATOMICAL).index("prn")
    assert lm["pin_mask"][0, j] and not lm["pin_mask"][1, j] and lm["weights"][0, j] != 1.0
    # full pipeline: a rerun of the golden inputs executes nothing; the pinned project re-runs landmarks
    # and everything downstream, and only those stages
    cache = proj["cache"]
    prj.pins.clear()
    r4 = S.run_pipeline(prj, "report", cache=cache, **kw)
    assert r4.executed == [] and r4.cache_hits == [s for s in S.ORDER if s != "texture"]
    prj.pins.append(Pin("p01", "prn", (310.0, 420.0), cls="novice", zoom=2.0))
    r5 = S.run_pipeline(prj, "report", cache=cache, **kw)
    assert r5.cache_hits == ["ingest", "triage"]
    assert r5.executed == ["landmarks", "solve", "observe", "fit", "uncertainty", "handoff", "report"]
    # a different seed changes every key
    prj.seed = 12
    r6 = S.run_pipeline(prj, "triage", cache=cache, **kw)
    assert r6.executed == ["ingest", "triage"]


def test_stage_registry_declares_inputs_outputs_and_data_classes():
    assert tuple(S.STAGES) == S.ORDER
    assert S.STAGES["landmarks"].data_class is policy.DataClass.BIOMETRIC_GEOMETRY
    assert S.STAGES["texture"].data_class is policy.DataClass.LIKENESS_ASSET
    assert S.STAGES["ingest"].data_class is policy.DataClass.PERSONAL_IMAGE
    for st in S.STAGES.values():
        assert callable(st.fn) and st.outputs
        assert all(u in S.ORDER and S.ORDER.index(u) < S.ORDER.index(st.name) for u in st.inputs)
    with pytest.raises(S.PipelineError):
        S.run_pipeline(Project(), "nonsense")


# ============================================================================ consent
def test_consent_gates(proj, capsys):
    prj, sets, consent, lm, tmp_path = proj["prj"], proj["sets"], proj["consent"], proj["lm"], proj["tmp"]
    kw = dict(landmark_sets=sets)
    with pytest.raises(S.ConsentError) as e:                    # no record at all
        S.run_pipeline(prj, "solve", consent=None, **kw)
    assert e.value.operation == "reconstruct" and "consent_record" in e.value.result.missing
    no_scope = ConsentRecord(**{**consent.__dict__, "scopes": Scope.CAPTURE})
    with pytest.raises(S.ConsentError) as e:
        S.run_pipeline(prj, "solve", consent=no_scope, **kw)
    assert "RECONSTRUCT" in e.value.result.missing
    missing_photo = ConsentRecord(**{**consent.__dict__, "photo_sha256": consent.photo_sha256[:-1]})
    with pytest.raises(S.ConsentError) as e:
        S.run_pipeline(prj, "solve", consent=missing_photo, **kw)
    assert any("F2" in r for r in e.value.result.reasons)
    # triage needs no consent; solve does (CLI exit code 3, code only on stderr)
    assert S.run_pipeline(prj, "triage", consent=None, **kw).outputs["triage"]["photos"][0]["usable"]
    (prj.root / "consent" / f"{prj.consent_id}.json").write_text(missing_photo.to_json())
    assert cli.main(["solve", "--project", str(prj.path), "--landmarks", str(lm)]) == 3
    err = capsys.readouterr().err
    assert "consent_refused" in err and str(tmp_path) not in err
    # texture is a separate gate
    no_tex = ConsentRecord(**{**consent.__dict__, "scopes": Scope.RECONSTRUCT})
    with pytest.raises(S.ConsentError) as e:
        S.run_pipeline(prj, "report", cache=proj["cache"], consent=no_tex, texture=True, **kw)
    assert e.value.operation == "texture" and "TEXTURE" in e.value.result.missing
    # a photo the user excluded is not part of the reconstruct check
    prj.photos[4].include = False
    short = ConsentRecord(**{**consent.__dict__, "photo_sha256": consent.photo_sha256[:4]})
    assert S.run_pipeline(prj, "landmarks", consent=short, **kw).outputs["landmarks"]["photo_ids"] == \
        ["p01", "p02", "p03", "p04"]


# ============================================================================ mirror (D-10)
def test_mirror_never_applied_without_decision(tmp_path):
    det = {"noise_scale": 0.3, "outlier_frac": 0.0, "definition_bias": False}
    prj, sets, consent, _, scene = materialise(tmp_path, seed=6, asym_mm=3.0, detector=det)
    perm = load_scheme("anatomical44").mirror_permutation()
    f = sets["p03"].faces[0]
    f.uv = image_ops.flip_uv(f.uv, W, perm)                      # photo p03 arrives mirrored
    f.visible = np.isfinite(f.uv[:, 0])
    # the synthetic faces are small (100-165 px): without the QA down-weight the mirror evidence is decisive
    kw = dict(landmark_sets=sets, consent=consent,
              config={"landmarks": {"downweight_sigma_mult": 1.0}, "solve": {"downweight_sigma_mult": 1.0}})
    run = S.run_pipeline(prj, "solve", **kw)
    assert prj.decisions == [] and run.outputs["landmarks"]["flips_applied"] == []
    cards = run.outputs["solve"]["mirror_cards"]
    assert cards[0]["kind"] == "mirror_flip" and cards[0]["photo"] == "p03"
    assert cards[0]["decision"] == "suggest_flip" and cards[0]["applied"] is False
    # the observations are exactly the detections: nothing was flipped
    j = list(ANATOMICAL).index("ch_L")
    assert np.allclose(run.outputs["landmarks"]["uv"][2, j], sets["p03"].faces[0].uv[j])
    # explicit --apply-mirror: decision (by cli) + audit entry, then the flip is applied
    run2 = S.run_pipeline(prj, "solve", apply_mirror=["p03"], **kw)
    assert run2.flips_recorded == ["p03"]
    assert [(d["kind"], d["photo"], d["by"]) for d in prj.decisions] == [("mirror_flip", "p03", "cli")]
    audit = [json.loads(x) for x in (prj.root / "audit.jsonl").read_text().splitlines()]
    assert [a["event"] for a in audit] == ["decision_mirror_flip"] and audit[0]["sha256"] == prj.photo("p03").sha256
    assert run2.outputs["landmarks"]["flips_applied"] == ["p03"]
    assert np.allclose(run2.outputs["landmarks"]["uv"][2, list(ANATOMICAL).index("ch_R")],
                       image_ops.flip_uv(f.uv, W, perm)[list(ANATOMICAL).index("ch_R")])
    assert not any(c["decision"] == "suggest_flip" and not c["applied"] for c in run2.outputs["solve"]["mirror_cards"])
    # a second apply does not duplicate the decision
    S.run_pipeline(prj, "landmarks", apply_mirror=["p03"], **kw)
    assert len(prj.decisions) == 1
    assert json.loads(prj.path.read_text())["decisions"][0]["photo"] == "p03"


# ============================================================================ network, determinism, golden
def test_network_guard_full_pipeline(base):
    """The golden run (module fixture ``base``) ran every stage under ``policy.network_guard()``; the
    texture stage and the report run under it as well."""
    assert base["run"].executed == [s for s in S.ORDER if s != "texture"] and base["run"].result["tier"]["code"]
    with policy.network_guard():
        with pytest.raises(PermissionError):
            socket.create_connection(("127.0.0.1", 9), timeout=0.1)
        run = S.run_pipeline(base["prj"], "report", cache=base["cache"], landmark_sets=base["sets"],
                             consent=base["consent"], texture=True, config={"texture": {"size": 64, **RELAX}})
    assert run.executed == ["texture", "report"] and run.outputs["texture"]["albedo_linear"].shape == (64, 64, 3)
    assert run.result["texture"]["mirror_fill"] is False and run.arrays["texture_albedo_linear"].shape == (64, 64, 3)


def _assert_close(a, b, path=""):
    if isinstance(b, dict):
        assert set(a) == set(b), path
        for k in b:
            _assert_close(a[k], b[k], f"{path}/{k}")
    elif isinstance(b, list):
        assert len(a) == len(b), path
        for i, (x, y) in enumerate(zip(a, b)):
            _assert_close(x, y, f"{path}[{i}]")
    elif isinstance(b, float):
        assert a == pytest.approx(b, rel=1e-5, abs=1e-9), path
    else:
        assert a == b, path


def test_golden_pipeline_small(golden, cli_run, tmp_path):
    run = golden["run"]
    summary = S.result_summary(run.result)
    path = GOLDEN / "expected_result.json"
    if not path.exists():                                        # first generation only (reviewed + committed)
        path.write_text(json.dumps({"provenance": "synthetic", "summary": summary}, indent=1, sort_keys=True) + "\n")
    expected = json.loads(path.read_text())
    assert expected["provenance"] == "synthetic" and json.loads((GOLDEN / "project.json").read_text())[
        "provenance"] == "synthetic"
    _assert_close(summary, expected["summary"])
    assert summary["tier"] in "ABCD" and summary["scale_mode"] == "prior"
    # identical rerun from scratch (the CLI run on a copy: fresh cache): bit-identical result.json, report
    # and arrays; timestamps live only in decisions and audit lines, never in the result files
    sol = cli_run["sol"]
    a = tmp_path / "a"
    a.mkdir()
    S.write_result_files(a, run.outputs["report"])
    assert (a / "result.json").read_bytes() == (sol / "result.json").read_bytes()
    assert (a / "report.txt").read_bytes() == (sol / "report.txt").read_bytes()
    za, zb = np.load(a / "arrays.npz"), np.load(sol / "arrays.npz")
    assert za.files == zb.files and all(np.array_equal(za[k], zb[k], equal_nan=za[k].dtype.kind == "f")
                                        for k in za.files)


def test_result_quality_on_synthetic_subject(golden):
    """The solve recovers the subject's landmarks (sanity, not a calibration test)."""
    from face3d.geometry.procrustes import procrustes_rmse
    kit, sub, rig, obs = golden["scene"]
    X = golden["run"].outputs["solve"]["X"]
    assert procrustes_rmse(X, sub.landmarks("anatomical44"), with_scale=True) < 4.0
    res = golden["run"].result
    assert res["scale"]["mode"] == "prior" and "population" in res["scale"]["label"]
    assert res["unverified_defaults"] > 0 and res["stage"] in ("A", "B", "C", "D")
    arrays = golden["run"].arrays
    assert np.isfinite(arrays["sigma_n"]).all() and ((arrays["support"] >= 0) & (arrays["support"] <= 1)).all()
    assert arrays["handoff_key_ID_fit"].shape == arrays["vertices"].shape
    # the asymmetry is exported as its own key, never removed (D-15): the Asym key is the fitted shape
    assert np.allclose(arrays["handoff_key_Asym"], arrays["vertices"])


def test_settings_and_scale_refs_are_solve_inputs(proj):
    prj, sets, consent, cache, scene = proj["prj"], proj["sets"], proj["consent"], proj["cache"], proj["scene"]
    kw = dict(cache=cache, landmark_sets=sets, consent=consent)
    X = scene[1].landmarks("anatomical44")
    ids = list(ANATOMICAL)
    a, b = ids.index("zy_L"), ids.index("zy_R")
    prj.scale_refs.append({"kind": "caliper", "a": "zy_L", "b": "zy_R",
                           "mm": float(np.linalg.norm(X[a] - X[b])), "sigma_mm": 0.5})
    run = S.run_pipeline(prj, "observe", **kw)
    assert run.executed == ["solve", "observe"] and run.outputs["solve"]["scale_mode"] == "measured"
    assert run.outputs["observe"]["scale"]["mode"] == "measured" and run.outputs["observe"]["scale"]["sigma_pct"] < 5.0
    # the sex prior is a consented input (never inferred): it is part of the solve key and changes the prior
    prj.scale_refs.clear()
    prj.settings["sex_prior"] = "female"
    r1 = S.run_pipeline(prj, "solve", **kw)
    assert r1.executed == ["solve"]
    assert not np.allclose(r1.outputs["solve"]["X"], golden_X(proj))


def golden_X(proj):
    return S.run_pipeline(proj["prj"].__class__.load(proj["prj"].path), "solve", cache=proj["cache"],
                          landmark_sets=proj["sets"], consent=proj["consent"]).outputs["solve"]["X"]


# ============================================================================ landmark TTL 0
def test_landmark_cache_ttl_zero(proj, base):
    prj, sets, consent = proj["prj"], proj["sets"], proj["consent"]
    # the golden run used a disk-backed cache: nothing but the (TTL 30 days) texture may be on disk
    root = base["tmp"] / "stage_cache"
    S.run_pipeline(base["prj"], "report", cache=base["cache"], landmark_sets=base["sets"], consent=base["consent"],
                   texture=True, config={"texture": {"size": 32, **RELAX}})
    kinds = [json.loads(p.read_text())["data_class"] for p in root.glob("*.json")]
    assert kinds and set(kinds) == {"LIKENESS_ASSET"} and _landmark_files(base["prj"].root) == []
    # TTL-0 classes in a fresh disk cache write nothing; close() purges leftovers
    own = StageCache(root=prj.root / "cache2")
    S.run_pipeline(prj, "landmarks", cache=own, landmark_sets=sets, consent=consent)
    assert not (prj.root / "cache2").exists() or list((prj.root / "cache2").glob("*")) == []
    own.close()
    assert _landmark_files(prj.root) == []
    # opt-in keep: copies under the project, logged
    prj.landmark_cache = {"keep": True}
    prj.save()
    S.run_pipeline(prj, "landmarks", landmark_sets=sets, consent=consent)
    kept = sorted(p.name for p in (prj.root / "landmarks").glob("*.json"))
    assert kept == [f"p0{i}.json" for i in range(1, 6)]
    assert load_landmarks(prj.root / "landmarks" / "p01.json").scheme == "anatomical44"
    events = [json.loads(x)["event"] for x in (prj.root / "audit.jsonl").read_text().splitlines()]
    assert events == ["landmarks_kept"] * 5
    # and a later run finds them without being handed any
    run = S.run_pipeline(Project.load(prj.path), "landmarks", consent=consent)
    assert run.outputs["landmarks"]["photo_ids"] == ["p01", "p02", "p03", "p04", "p05"]


# ============================================================================ jobs
def _job_for(prj, sets, consent, stage="report", **extra):
    jd = jobs.new_job_dir(prj.root)
    inputs = {"project": str(prj.path), "landmark_sets": {k: S.landmark_set_to_plain(v) for k, v in sets.items()},
              "consent": consent.to_json() if consent else None, "apply_mirror": [], "texture": False, **extra}
    jobs.write_job(jd, stage, inputs, {}, prj.seed)
    return jd


def test_job_roundtrip_and_progress_reader(proj):
    prj, sets, consent = proj["prj"], proj["sets"], proj["consent"]
    jd = _job_for(prj, sets, consent, "landmarks")
    doc = jobs.read_job(jd)
    assert doc["stage"] == "landmarks" and doc["seed"] == prj.seed and doc["format"] == "face3d.job"
    assert np.array_equal(doc["inputs"]["landmark_sets"]["p01"]["faces"][0]["uv"], sets["p01"].faces[0].uv,
                          equal_nan=True)
    assert jobs.run_job(jd) == 0 and not (jd / "inputs.npz").exists()       # TTL 0: input arrays deleted
    lines, off = jobs.read_progress(jd)
    assert lines and all(set(x) == {"t", "stage", "frac", "msg_key"} for x in lines)
    assert lines[0]["msg_key"] == "job.start" and lines[-1]["msg_key"] == "job.done" and lines[-1]["frac"] == 1.0
    assert [x["frac"] for x in lines] == sorted(x["frac"] for x in lines)
    assert {x["stage"] for x in lines} >= {"ingest", "triage", "landmarks"}
    assert jobs.read_progress(jd, off) == ([], off)
    res = json.loads((jd / "result.json").read_text())
    assert res["format"] == "face3d.job_result" and res["stage"] == "landmarks"
    assert np.load(jd / "arrays.npz")["uv"].shape == (5, 44, 2) and not list(jd.glob("*.tmp"))
    # a partial last line is left for the next read
    with open(jd / "progress.jsonl", "ab") as f:
        f.write(b'{"t": 1, "stage": "x"')
    assert jobs.read_progress(jd, off) == ([], off)
    with open(jd / "progress.jsonl", "ab") as f:
        f.write(b', "frac": 0.5, "msg_key": "k"}\n')
    more, off2 = jobs.read_progress(jd, off)
    assert more == [{"t": 1, "stage": "x", "frac": 0.5, "msg_key": "k"}] and off2 > off


def test_lm_cancel_hook_stops_the_solver_between_iterations(proj):
    prj, sets, consent = proj["prj"], proj["sets"], proj["consent"]
    calls = {"stage": 0, "lm": 0, "armed": False}

    def cancel():
        if calls["armed"]:
            calls["lm"] += 1
            return calls["lm"] > 3
        calls["stage"] += 1
        return False

    orig = S.STAGES["solve"]

    def arm(inputs, config, seed):
        calls["armed"] = True
        return orig.fn(inputs, config, seed)

    S.STAGES["solve"] = S.Stage(**{**orig.__dict__, "fn": arm})
    try:
        with pytest.raises(S.Cancelled):
            S.run_pipeline(prj, "solve", cache=StageCache(), landmark_sets=sets, consent=consent, cancel=cancel)
    finally:
        S.STAGES["solve"] = orig
    assert calls["lm"] == 4 and calls["stage"] >= 3
    import face3d.solve.bundle as bundle
    assert bundle.levenberg_marquardt.__module__ == "face3d.solve.lm"      # hook removed again


def _isolated_layout(tmp: Path) -> Path:
    """tmp/engine/face3d (copied package) + tmp/launcher.py inserting tmp/engine into sys.path."""
    eng = tmp / "engine"
    eng.mkdir()
    shutil.copytree(REPO / "face3d", eng / "face3d", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    launcher = tmp / "launcher.py"
    launcher.write_text(
        "import os, sys\n"
        "sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'engine'))\n"
        "from face3d.pipeline.jobs import run_job\n"
        "import face3d\n"
        "assert os.path.dirname(os.path.dirname(face3d.__file__)).endswith('engine')\n"
        "sys.exit(run_job(sys.argv[1]))\n")
    return launcher


def test_job_protocol_with_isolated_launcher(proj):
    prj, sets, consent, tmp_path = proj["prj"], proj["sets"], proj["consent"], proj["tmp"]
    (tmp_path / "iso").mkdir()
    launcher = _isolated_layout(tmp_path / "iso")
    jd = _job_for(prj, sets, consent, "report")
    r = subprocess.run([sys.executable, "-I", str(launcher), str(jd)], capture_output=True, timeout=120)
    assert r.returncode == 0, r.stderr.decode()[-2000:]
    lines, _ = jobs.read_progress(jd)
    assert lines[-1]["msg_key"] == "job.done" and any(x["stage"] == "solve" for x in lines)
    res = json.loads((jd / "result.json").read_text())
    assert res["format"] == "face3d.result" and res["tier"]["code"] in "ABCD"
    ref = S.run_pipeline(prj, "report", cache=proj["cache"], landmark_sets=sets, consent=consent)
    assert ref.executed == []                                    # the in-process reference comes from the cache
    assert res["tier"] == ref.result["tier"] and res["scale"]["mode"] == ref.result["scale"]["mode"]
    assert res["cameras"][0]["f_px"] == pytest.approx(ref.result["cameras"][0]["f_px"], rel=1e-6)
    assert (jd / "arrays.npz").is_file() and not list(jd.glob("*.tmp"))
    assert not (jd / "error.json").exists() and not (jd / "inputs.npz").exists()

    # cancel: a long job stops within 2 s of the sentinel file
    jd2 = jobs.new_job_dir(prj.root)
    jobs.write_job(jd2, "selftest", {}, {"seconds": 60.0, "tick": 0.05}, 1)
    p = subprocess.Popen([sys.executable, "-I", str(launcher), str(jd2)])
    try:
        t0 = time.time()
        while time.time() - t0 < 60:
            lines, _ = jobs.read_progress(jd2)
            if any(x["stage"] == "selftest" for x in lines):
                break
            time.sleep(0.05)
        else:
            pytest.fail("no progress line")
        (jd2 / "cancel").write_text("")
        t1 = time.time()
        rc = p.wait(timeout=10)
        assert time.time() - t1 < 2.0
    finally:
        if p.poll() is None:
            p.kill()
    assert rc == jobs.EXIT_CANCELLED
    err = json.loads((jd2 / "error.json").read_text())
    assert err == {"code": "cancelled", "msg_key": "job.error.cancelled", "stage": "selftest"}
    assert not (jd2 / "result.json").exists()
    assert jobs.read_progress(jd2)[0][-1]["msg_key"] == "job.cancelled"

    # a failing job: error.json carries a code only (no paths, arrays or coordinates)
    jd3 = jobs.new_job_dir(prj.root)
    jobs.write_job(jd3, "solve", {"project": str(tmp_path / "nowhere" / "project.json"),
                                  "landmark_sets": {"p01": S.landmark_set_to_plain(sets["p01"])}}, {}, 1)
    rc = subprocess.run([sys.executable, "-I", str(launcher), str(jd3)], capture_output=True, timeout=60).returncode
    assert rc == jobs.EXIT_INVALID
    text = (jd3 / "error.json").read_text()
    err = json.loads(text)
    assert set(err) == {"code", "msg_key", "stage"} and err["stage"] == "solve"
    assert "/" not in text and "\\" not in text and str(tmp_path) not in text
    assert not any(ch.isdigit() for ch in text)                  # no coordinates or arrays
    assert not (jd3 / "result.json").exists()


def test_job_consent_failure_exit_code_and_error_json(proj):
    prj, sets = proj["prj"], proj["sets"]
    jd = _job_for(prj, sets, None, "solve")                       # no consent record
    assert jobs.run_job(jd) == jobs.EXIT_CONSENT
    err = json.loads((jd / "error.json").read_text())
    assert err["code"] == "consent_refused" and err["stage"] == "landmarks"      # the stage that was refused
    jd = jobs.new_job_dir(prj.root)
    (jd / "job.json").write_text("{not json")
    assert jobs.run_job(jd) == jobs.EXIT_INVALID
    assert json.loads((jd / "error.json").read_text())["code"] == "invalid_input"


# ============================================================================ stage details
def test_triage_findings_focal_ladder_and_occluders(proj):
    prj, sets, consent = proj["prj"], proj["sets"], proj["consent"]
    prj.photos[0].tags["occluders"] = ["beard", "glasses"]
    prj.photos[1].include = False
    run = S.run_pipeline(prj, "observe", cache=proj["cache"], landmark_sets=sets, consent=consent,
                         config={"landmarks": NO_DOWNWEIGHT, "solve": NO_DOWNWEIGHT})
    tri = {r["id"]: r for r in run.outputs["triage"]["photos"]}
    assert tri["p01"]["f_source"] == "exif_f35" and tri["p01"]["f_log_sigma"] == pytest.approx(0.04)
    assert tri["p01"]["f_px"] == pytest.approx(27.2 * np.hypot(W, H) / np.hypot(36, 24), rel=1e-3)
    assert tri["p01"]["distance_mm"] > 600.0 and not tri["p02"]["usable"]
    assert run.outputs["landmarks"]["photo_ids"] == ["p01", "p03", "p04", "p05"]
    # beard: the jaw claim is capped at prior-driven (DESIGN 4.1, status cap)
    st = {r["name"]: r["status"] for r in run.outputs["observe"]["regions"]}
    assert st["jaw"] == "prior-driven" and run.outputs["observe"]["status_caps"]["jaw"] == "prior-driven"
    # glasses: eye sigma x2 (information weight 1/4) on the eye landmarks of that photo only
    w = run.outputs["landmarks"]["weights"]
    eyes = [k for k, i in enumerate(ANATOMICAL) if ANATOMICAL[i].region == "eyes"]
    assert np.allclose(w[0, eyes], 0.25) and np.allclose(w[1, eyes], 1.0)


def test_landmarks_stage_scheme_permutation_and_geometric_lr(proj):
    """A MediaPipe-scheme set: anatomical correspondences are mapped by the scheme (unverified points
    inflated), and the two iris rings are assigned to sides from geometry, never from their indices."""
    prj, sets, consent, scene = proj["prj"], proj["sets"], proj["consent"], proj["scene"]
    sc = load_scheme("mediapipe_478")
    ids = list(ANATOMICAL)
    ls_new = {}
    for k, (pid, ls) in enumerate(sets.items()):
        uv44 = ls.faces[0].uv
        uv = np.full((478, 2), np.nan)
        for lid, si in sc.anatomical_index().items():
            uv[si] = uv44[ids.index(lid)]
        # iris rings: ring a sits on the pupil of the subject's LEFT eye (the opposite of the provisional side)
        for gname, eye in (("iris_a", "p_L"), ("iris_b", "p_R")):
            g = next(g for g in sc.lr_groups if g["name"] == gname)
            c = uv44[ids.index(eye)]
            uv[g["centre_index"]] = c
            for j, i in enumerate([i for i in g["indices"] if i != g["centre_index"]]):
                uv[i] = c + 6.0 * np.array([np.cos(j * np.pi / 2), np.sin(j * np.pi / 2)])
        ls_new[pid] = LandmarkSet("mediapipe_478", ls.detector, {**ls.image}, [Face(1.0, uv, np.isfinite(uv[:, 0]))])
    run = S.run_pipeline(prj, "landmarks", landmark_sets=ls_new, consent=consent,
                         config={"landmarks": NO_DOWNWEIGHT})
    lm = run.outputs["landmarks"]
    checked = 0
    for v in range(5):
        for eye in ("p_L", "p_R"):
            j = ids.index(eye)
            if np.isfinite(sets[f"p0{v+1}"].faces[0].uv[j, 0]):
                assert np.allclose(lm["uv"][v, j], sets[f"p0{v+1}"].faces[0].uv[j]), (v, eye)
                checked += 1
    assert checked >= 6
    # every mapped scheme point is unverified (mediapipe_478): the *definition* sigma (sigma_def) is
    # inflated x3 (DESIGN 3.2, D-06), the per-observation sigma is not (so the bias does not average down)
    j = ids.index("prn")
    assert lm["sigma_def_mult"][j] == pytest.approx(3.0)
    assert np.allclose(lm["weights"][:, j][np.isfinite(lm["uv"][:, j, 0])], 1.0)
    got = S.run_pipeline(prj, "solve", landmark_sets=ls_new, consent=consent,
                         config={"landmarks": NO_DOWNWEIGHT, "solve": NO_DOWNWEIGHT}).outputs["solve"]["sigma_def_mm"]
    assert got[j] == pytest.approx(3.0 * ANATOMICAL["prn"].sigma_def_mm)
    # anatomical ids the scheme does not list stay unobserved
    assert np.isnan(lm["uv"][:, ids.index("sba_L"), 0]).all()
    assert np.isfinite(lm["iris_px"]).sum() >= 6 and np.nanmax(np.abs(lm["iris_px"] - 6.0)) < 1e-9


def test_solve_with_non_anatomical_scheme_points(proj):
    """A scheme with points that have no anatomical id (legacy_synthetic: vertex_front, brows, temples)
    enters through the conditional template prior; the solve runs on 44 + 7 points."""
    prj, consent = proj["prj"], proj["consent"]
    kit, sub, rig, _ = proj["scene"]
    sc = load_scheme("legacy_synthetic")
    X32 = sub.landmarks("legacy_synthetic")
    obs = detector_sim.simulate(X32, sc.kinds(), rig, np.random.default_rng(5))
    sets = {f"p0{k + 1}": LandmarkSet("legacy_synthetic", {"backend": "synthetic", "licence": "CC0-1.0",
                                                           "commercial_ok": True},
                                      {"wh": [W, H]}, [Face(1.0, obs.uv[k], np.isfinite(obs.uv[k][:, 0]))])
            for k in range(5)}
    for ph in prj.photos[3:]:
        ph.include = False
    run = S.run_pipeline(prj, "solve", landmark_sets=sets, consent=consent)
    lm = run.outputs["landmarks"]
    n_other = sum(1 for p in sc.points if p.anatomical_id is None)
    assert lm["c_scheme"] == "legacy_synthetic" and len(lm["ids"]) == 44 + n_other and n_other == 7
    assert lm["ids"][44].startswith("legacy_synthetic:") and lm["uv"].shape == (3, 44 + n_other, 2)
    assert np.isfinite(lm["uv"][:, 44:, 0]).any()
    X = run.outputs["solve"]["X"]
    assert X.shape == (44 + n_other, 3) and np.isfinite(X).all()
    assert run.outputs["solve"]["cov"].shape == (3 * (44 + n_other),) * 2
    # the permutation maps the scheme's mirrored pairs (brow_L <-> brow_R) onto engine points
    perm = lm["perm"]
    assert np.array_equal(perm[perm], np.arange(len(perm)))
    assert (perm[44:] != np.arange(44, 44 + n_other)).sum() >= 2


def test_stage_d_runs_only_with_contour_observations(proj):
    from face3d.fit.contour import ContourObs
    from face3d.mesh.raster import rasterize
    prj, sets, consent, cache = proj["prj"], proj["sets"], proj["consent"], proj["cache"]
    kit, sub, rig, _ = proj["scene"]
    r0 = S.run_pipeline(prj, "fit", cache=cache, landmark_sets=sets, consent=consent)
    assert r0.outputs["fit"]["contours"] == "none" and r0.outputs["fit"]["stage"] in ("B", "C")
    cobs = [ContourObs.from_mask(rasterize(sub.V_true, kit.triangles(), cam, cull_backfaces=True).mask, view=k,
                                 source="test_mask") for k, cam in enumerate(rig.cameras)]
    r1 = S.run_pipeline(prj, "fit", cache=cache, landmark_sets=sets, consent=consent, extra_inputs={"contour_obs": cobs})
    assert r1.executed == ["fit"]                              # only the fit stage re-ran: contours are its input
    fit = r1.outputs["fit"]
    assert fit["contours"] in ("applied", "rolled_back") and fit["vertices"].shape == r0.outputs["fit"]["vertices"].shape
    if fit["contours"] == "applied":
        assert fit["stage"] == "D" and "V_D" in fit
    else:
        assert np.array_equal(fit["vertices"], r0.outputs["fit"]["vertices"])


def test_texture_stage_is_gated_and_mirror_fill_is_off(proj):
    prj, sets, consent = proj["prj"], proj["sets"], proj["consent"]
    run = S.run_pipeline(prj, "report", cache=proj["cache"], landmark_sets=sets, consent=consent)
    assert "texture" not in run.executed and run.outputs["texture"] is None and run.result["texture"] is None
    run = S.run_pipeline(prj, "report", cache=proj["cache"], landmark_sets=sets, consent=consent, texture=True,
                         config={"texture": {"size": 64, **RELAX}})
    t = run.outputs["texture"]
    assert t["size"] == 64 and np.isfinite(t["albedo_linear"]).all() and t["photo_ids"][0] == "p01"
    assert run.result["texture"]["size"] == 64 and run.arrays["texture_albedo_linear"].shape == (64, 64, 3)
    assert not list(prj.root.rglob("*.png"))               # working copies are never re-written


def test_handoff_cage_is_optional(proj):
    prj, sets, consent, cache = proj["prj"], proj["sets"], proj["consent"], proj["cache"]
    run = S.run_pipeline(prj, "handoff", cache=cache, landmark_sets=sets, consent=consent)
    assert "cage" not in run.outputs["handoff"] and run.executed == []
    run = S.run_pipeline(prj, "handoff", cache=cache, landmark_sets=sets, consent=consent,
                         config={"handoff": {"cage": True}})
    cage = run.outputs["handoff"]["cage"]
    assert cage.shape == run.outputs["fit"]["vertices"].shape and np.isfinite(cage).all()
    assert run.executed == ["handoff"]


def test_engine_files_stay_numpy_only():
    import ast
    allowed = {"numpy", "face3d"}
    stdlib = set(sys.stdlib_module_names)
    for f in ("project.py", "stages.py", "jobs.py", "cli.py"):
        tree = ast.parse((REPO / "face3d" / "pipeline" / f).read_text())
        mods = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                mods |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
                mods.add(n.module.split(".")[0])
        assert mods <= allowed | stdlib, (f, mods - allowed - stdlib)


# ============================================================================ review fixes (WP-20 findings)
CLEAN_DET = {"noise_scale": 0.3, "outlier_frac": 0.0, "definition_bias": False}


def _iris(views, radius=15.0, sharp=True, eye="L"):
    return [(v, eye, radius, 0.4, sharp) for v in views]


def test_iris_observations_are_gated_and_survive_lovo(proj):
    """Iris rows are filtered with ``iris_usable`` (d >= 20 px, sharp flag, no glasses) and stay on their
    camera in every leave-one-view-out re-solve (the unfixed code raised 'view 4 out of range')."""
    prj, sets, consent = proj["prj"], proj["sets"], proj["consent"]
    kw = dict(landmark_sets=sets, consent=consent, config={"landmarks": NO_DOWNWEIGHT, "solve": NO_DOWNWEIGHT})
    run = S.run_pipeline(prj, "observe", extra_inputs={"iris_obs": [o for v in range(5) for o in
                                                                    _iris([v], 15.0 + v, eye="L")]}, **kw)
    s = run.outputs["solve"]
    assert s["scale_mode"] == "iris" and "S-IRIS-UNUSABLE" not in s["flags"]
    assert run.outputs["observe"]["scale"]["mode"] == "iris" and np.isfinite(run.outputs["observe"]["gamma"])
    # unusable observations are dropped and flagged: 4 px radius (d = 8 < 20), no sharp flag, glasses
    prj.photos[3].tags["occluders"] = ["glasses"]
    obs = _iris([0], 4.0) + [(1, "L", 15.0, 0.4)] + _iris([3]) + _iris([9]) + [(2, "X", 15.0, 0.4, True)]
    run = S.run_pipeline(prj, "solve", extra_inputs={"iris_obs": obs}, **kw)
    s = run.outputs["solve"]
    assert s["scale_mode"] == "prior" and "S-IRIS-UNUSABLE" in s["flags"]
    assert not any(isinstance(t, S._scale.IrisTerm) for t in s["_terms"])
    # photo ids name views too
    run = S.run_pipeline(prj, "solve", extra_inputs={"iris_obs": _iris(["p02", "p05"])}, **kw)
    assert run.outputs["solve"]["scale_mode"] == "iris"


def test_terms_without_reindexes_per_view_terms():
    t = S._scale.IrisTerm([(0, "L", 20.0, 0.5), (2, "R", 21.0, 0.5), (4, "L", 22.0, 0.5)], {"L": 1, "R": 2})
    out = S._terms_without([t], 2)
    assert [(o[0], o[2]) for o in out[0].obs] == [(0, 20.0), (3, 22.0)]
    assert S._terms_without([t], 0)[0].obs[0][:2] == (1, "R")
    one = S._scale.IrisTerm([(1, "L", 20.0, 0.5)], {"L": 1, "R": 2})
    assert S._terms_without([one], 1) == []                       # its only observation is left out


def test_expression_retag_ignores_rejected_outliers(proj):
    """A gross detector outlier on a lip point must not re-tag a neutral view as expressive (DESIGN 4.9).
    In the golden scene the detector simulator puts an outlier on 'ls' in view p04 (the unfixed code
    re-tagged that view 'expressive', chi2_red 11.9 over a rejected observation)."""
    run = S.run_pipeline(proj["prj"], "solve", cache=proj["cache"], landmark_sets=proj["sets"],
                         consent=proj["consent"], config={"landmarks": NO_DOWNWEIGHT, "solve": NO_DOWNWEIGHT})
    s = run.outputs["solve"]
    j = list(ANATOMICAL).index("ls")
    assert not s["inlier_mask"][3][j]                                # the robust schedule rejected it
    assert s["tags"] == ["neutral"] * 5 and "E-NO-NEUTRAL" not in s["flags"]
    assert run.outputs["landmarks"]["expression_tags"] == ["neutral"] * 5


def test_texture_gates_reprojection_blocks_and_excluded_view_never_feeds_albedo(proj):
    prj, sets, consent = proj["prj"], proj["sets"], proj["consent"]
    kw = dict(cache=proj["cache"], landmark_sets=sets, consent=consent, texture=True)
    base_run = S.run_pipeline(prj, "report", cache=proj["cache"], landmark_sets=sets, consent=consent)
    s = base_run.outputs["solve"]
    assert s["reproj_max_px"] > 3.0                                  # the golden scene fails bl T2 (max 3 px)
    with pytest.raises(S.PipelineError) as e:                        # the default limits block the stage
        S.run_pipeline(prj, "report", config={"texture": {"size": 32}}, **kw)
    assert e.value.code == "texture_blocked" and "T-REPROJ-MAX" in str(e.value)
    # relaxed limits (recorded in the config): a Q-PROCESS (editor) photo is excluded from the albedo
    prj.photos[1].exif = {**prj.photos[1].exif, "software": "Adobe Photoshop 25.0"}
    run = S.run_pipeline(prj, "report", config={"texture": {"size": 32, **RELAX}}, **kw)
    t = run.outputs["texture"]
    assert run.outputs["triage"]["photos"][1]["findings"][0]["code"] == "Q-PROCESS"
    assert t["excluded"] == ["p02"] and t["photo_ids"] == ["p01", "p03", "p04", "p05"]
    assert run.result["texture"]["excluded_views"] == ["p02"] and run.result["texture"]["gate_limits"] == RELAX
    assert t["provenance"]["excluded_views"] == [1]
    assert [g["code"] for g in t["gate"]] == ["T-VIEW-EXCLUDED"]


def test_cancel_is_polled_inside_the_texture_stage(proj, monkeypatch):
    """A cancel raised while the texture stage is running stops it after the current view, not after the stage."""
    prj, sets, consent = proj["prj"], proj["sets"], proj["consent"]
    calls = []
    orig = S._tp.view_weights

    def spy(*a, **k):
        calls.append(1)
        return orig(*a, **k)
    monkeypatch.setattr(S._tp, "view_weights", spy)

    def cancel():
        return len(calls) >= 1
    with pytest.raises(S.Cancelled):
        S.run_pipeline(prj, "report", cache=proj["cache"], landmark_sets=sets, consent=consent, texture=True,
                       config={"texture": {"size": 24, **RELAX}}, cancel=cancel)     # a size no other test used
    assert len(calls) == 1                                           # 5 views: the stage did not run to the end


def test_job_cancel_reaches_a_real_pipeline_stage(proj, monkeypatch):
    """run_job wires cancellation into the pipeline: a cancel file created while the texture stage runs ends
    the job with exit 4 and error.json names the texture stage (not the requested 'report')."""
    prj, sets, consent = proj["prj"], proj["sets"], proj["consent"]
    jd = jobs.new_job_dir(prj.root)
    jobs.write_job(jd, "report", {"project": str(prj.path), "landmark_sets": {
        k: S.landmark_set_to_plain(v) for k, v in sets.items()}, "consent": consent.to_json(), "apply_mirror": [],
        "texture": True}, {"stages": {"texture": {"size": 32, **RELAX}}}, prj.seed)
    calls = []
    orig = S._tp.view_weights

    def spy(*a, **k):
        calls.append(1)
        (jd / "cancel").write_text("")                              # the user cancels during the first view
        return orig(*a, **k)
    monkeypatch.setattr(S._tp, "view_weights", spy)
    assert jobs.run_job(jd) == jobs.EXIT_CANCELLED
    err = json.loads((jd / "error.json").read_text())
    assert err == {"code": "cancelled", "msg_key": "job.error.cancelled", "stage": "texture"}
    assert len(calls) == 1 and not (jd / "result.json").exists()


def test_landmark_stage_qa_small_face_and_near_findings(proj):
    """Q-SMALL (face < 120 px) excludes the view unless the user forced it; findings reach result.json."""
    prj, sets, consent = proj["prj"], proj["sets"], proj["consent"]
    prj.photos[2].include = "auto"                                   # p03 is 74 px: Q-SMALL block
    run = S.run_pipeline(prj, "report", landmark_sets=sets, consent=consent)
    lm, res = run.outputs["landmarks"], run.result
    assert lm["photo_ids"] == ["p01", "p02", "p04", "p05"]
    assert lm["excluded"] == [{"photo": "p03", "codes": ["Q-SMALL"]}]
    assert res["excluded_views"] == [{"photo": "p03", "stage": "landmarks", "codes": ["Q-SMALL"]}]
    assert [v["photo"] for v in res["views"]] == ["p01", "p02", "p04", "p05"] and len(res["cameras"]) == 4
    assert "Q-SMALL" in res["flags"] and "Q-SMALL" in res["views"][0]["findings"]
    assert {"code": "Q-SMALL", "severity": "block", "action": "exclude_geometry"} in res["findings"]["p03"]
    assert any(x["action"] == "down_weight" for x in res["findings"]["p02"] if x["code"] == "Q-SMALL")
    # the post-solve distance gate ran (the golden rig shoots p02 and p05 from < 1 m) and is carried too
    assert any(x["code"] == "Q-NEAR" for x in res["findings"]["p02"] + res["findings"]["p05"])
    assert "Flags: " in run.report_text and "Q-SMALL" in run.report_text
    # forced include keeps the view (the golden project forces all five)
    prj.photos[2].include = True
    assert S.run_pipeline(prj, "landmarks", landmark_sets=sets, consent=consent).outputs["landmarks"][
        "photo_ids"][2] == "p03"


def test_mirror_latest_decision_wins_and_cli_reverts(proj, capsys):
    prj, sets, consent, lm = proj["prj"], proj["sets"], proj["consent"], proj["lm"]
    kw = dict(landmark_sets=sets, consent=consent)
    S.run_pipeline(prj, "landmarks", apply_mirror=["p03"], **kw)
    assert prj.flipped_photos() == ["p03"]
    prj.record_decision("mirror_keep", "p03", "user")                 # the user reverts the flip
    assert prj.flipped_photos() == [] and prj.mirror_state("p03") == "keep"
    assert S.run_pipeline(prj, "landmarks", **kw).outputs["landmarks"]["flips_applied"] == []
    run = S.run_pipeline(prj, "landmarks", apply_mirror=["p03"], **kw)   # --apply-mirror after a revert flips again
    assert run.flips_recorded == ["p03"] and run.outputs["landmarks"]["flips_applied"] == ["p03"]
    assert [d["kind"] for d in prj.decisions] == ["mirror_flip", "mirror_keep", "mirror_flip"]
    # CLI: --revert-mirror records a mirror_keep decision
    prj.save()
    rc = cli.main(["triage", "--project", str(prj.path), "--revert-mirror", "p03", "--quiet"])
    assert rc == 0 and Project.load(prj.path).mirror_state("p03") == "keep"


def test_landmark_keep_opt_out_purges_and_is_not_used(proj):
    prj, sets, consent = proj["prj"], proj["sets"], proj["consent"]
    prj.set_landmark_keep(True)
    prj.save()
    S.run_pipeline(prj, "landmarks", landmark_sets=sets, consent=consent)
    assert len(list((prj.root / "landmarks").glob("*.json"))) == 5
    # opting out purges the kept sets (logged); a later run is not handed them
    prj.set_landmark_keep(False)
    prj.save()
    assert not (prj.root / "landmarks").exists()
    events = [json.loads(x)["event"] for x in (prj.root / "audit.jsonl").read_text().splitlines()]
    assert events.count("landmarks_purged") == 5
    with pytest.raises(S.PipelineError) as e:
        S.run_pipeline(Project.load(prj.path), "landmarks", consent=consent)
    assert e.value.code == "missing_landmarks"
    # files that sit under a project with keep=false (copied folder, edited flag) are purged, never read
    prj.set_landmark_keep(True)
    S.run_pipeline(prj, "landmarks", landmark_sets=sets, consent=consent)
    prj.landmark_cache = {"keep": False}                              # edited by hand: no purge call
    assert len(list((prj.root / "landmarks").glob("*.json"))) == 5
    with pytest.raises(S.PipelineError):
        S.run_pipeline(prj, "landmarks", consent=consent)
    assert not (prj.root / "landmarks").exists()


def test_pin_class_and_expertise(proj):
    from face3d.pipeline.project import resolve_pin_class
    prj, sets, consent = proj["prj"], proj["sets"], proj["consent"]
    assert resolve_pin_class("crisp", "novice") == "crisp_novice" and resolve_pin_class("crisp", "expert") == "crisp_expert"
    assert resolve_pin_class("nose_tip", "expert") == "nose_tip" and resolve_pin_class("expert") == "crisp_expert"
    with pytest.raises(ProjectError):
        resolve_pin_class("bogus")
    j = list(ANATOMICAL).index("prn")
    w = {}
    for ex in ("novice", "expert"):
        prj.pins[:] = [Pin("p01", "prn", (310.0, 420.0), cls="crisp", expertise=ex, zoom=1.0)]
        w[ex] = S.run_pipeline(prj, "landmarks", landmark_sets=sets, consent=consent).outputs["landmarks"]["weights"][0, j]
    assert w["expert"] > w["novice"]                                 # sigma 0.8 vs 1.2 mm: expertise is honoured
    prj.pins[:] = [Pin("p01", "prn", (310.0, 420.0), cls="nonsense")]
    with pytest.raises(ProjectError):
        prj.validate()


def test_job_applies_job_seed_and_error_names_failing_stage(proj):
    prj, sets, consent = proj["prj"], proj["sets"], proj["consent"]
    jd = jobs.new_job_dir(prj.root)
    jobs.write_job(jd, "report", {"project": str(prj.path), "landmark_sets": {
        k: S.landmark_set_to_plain(v) for k, v in sets.items()}, "consent": consent.to_json(), "apply_mirror": [],
        "texture": False}, {}, 999)
    assert jobs.run_job(jd) == 0
    assert json.loads((jd / "result.json").read_text())["run"]["seed"] == 999
    assert Project.load(prj.path).seed == prj.seed                    # never written back to the project
    # a failure in the landmarks stage (no landmark set) is named by that stage, not the requested one
    jd = jobs.new_job_dir(prj.root)
    jobs.write_job(jd, "report", {"project": str(prj.path), "landmark_sets": {}, "consent": consent.to_json()}, {}, 1)
    assert jobs.run_job(jd) == jobs.EXIT_INVALID
    assert json.loads((jd / "error.json").read_text())["stage"] == "landmarks"


def test_cli_error_codes_and_seed_override_is_not_persisted(proj, capsys):
    prj, lm = proj["prj"], proj["lm"]
    root = prj.root
    (root / "consent" / f"{prj.consent_id}.json").write_text("{not json")
    assert cli.main(["solve", "--project", str(prj.path), "--landmarks", str(lm)]) == cli.EXIT_INVALID
    err = capsys.readouterr().err
    assert "invalid_input" in err and str(root) not in err and "Traceback" not in err
    (root / "consent" / f"{prj.consent_id}.json").write_text(proj["consent"].to_json())
    out = root / "mysolve"
    out.mkdir()
    assert cli.main(["report", "--project", str(prj.path), "--landmarks", str(lm), "--out", str(out),
                     "--quiet"]) == cli.EXIT_INVALID                  # --out exists: a code, not a traceback
    assert str(root) not in capsys.readouterr().err
    assert cli.main(["report", "--project", str(prj.path), "--landmarks", str(lm), "--seed", "77",
                     "--quiet"]) == 0
    assert Project.load(prj.path).seed == prj.seed                    # the override lives in result.run.seed only
    assert json.loads((root / "solves" / "0001" / "result.json").read_text())["run"]["seed"] == 77


def test_engine_defaults_snapshot_is_process_independent():
    code = ("import sys\n"
            "if sys.argv[1] == 'all':\n"
            "    import importlib, pkgutil, face3d\n"
            "    for m in pkgutil.walk_packages(face3d.__path__, 'face3d.'):\n"
            "        if 'testbed' in m.name or 'blender' in m.name: continue\n"
            "        importlib.import_module(m.name)\n"
            "from face3d.pipeline import stages as S\n"
            "from face3d.core.schema import canonical_json, sha256_bytes\n"
            "print(sha256_bytes(canonical_json(S.engine_defaults_snapshot())), S.engine_unverified_count())\n")
    outs = [subprocess.run([sys.executable, "-c", code, mode], capture_output=True, text=True, timeout=120,
                           cwd=str(REPO)).stdout.strip() for mode in ("min", "all")]
    assert outs[0] and outs[0] == outs[1]          # importing every engine module changes nothing


def test_ingest_key_tracks_file_contents_and_landmark_sets_are_checked(proj):
    prj, sets, consent = proj["prj"], proj["sets"], proj["consent"]
    own = StageCache()
    kw = dict(landmark_sets=sets, consent=consent, cache=own)
    r1 = S.run_pipeline(prj, "ingest", **kw)
    assert S.run_pipeline(prj, "ingest", **kw).executed == []
    wc = prj.root / prj.photos[0].working_copy
    np.save(wc, np.load(wc) // 2)                                    # same path, different pixels
    with pytest.raises(S.PipelineError) as e:                        # a miss: the stage re-ran and caught it
        S.run_pipeline(prj, "ingest", **kw)
    assert e.value.code == "photo_sha_mismatch"


def test_landmark_set_of_another_image_is_refused(proj):
    import copy
    prj, consent = proj["prj"], proj["consent"]
    bad = copy.deepcopy(proj["sets"])
    bad["p02"].image["sha256"] = "0" * 64
    with pytest.raises(S.PipelineError) as e:
        S.run_pipeline(prj, "landmarks", landmark_sets=bad, consent=consent)
    assert e.value.code == "landmarks_image_mismatch"


def test_landmark_set_input_flipped_is_unflipped(proj):
    import copy
    prj, sets, consent = proj["prj"], copy.deepcopy(proj["sets"]), proj["consent"]
    perm = load_scheme("anatomical44").mirror_permutation()
    ref = S.run_pipeline(prj, "landmarks", landmark_sets=sets, consent=consent).outputs["landmarks"]["uv"]
    f = sets["p02"].faces[0]
    f.uv = image_ops.flip_uv(f.uv, W, perm)
    f.visible = np.isfinite(f.uv[:, 0])
    sets["p02"].image["input_flipped"] = True                        # the detector saw a mirrored copy
    got = S.run_pipeline(prj, "landmarks", landmark_sets=sets, consent=consent).outputs["landmarks"]
    assert np.allclose(got["uv"][1], ref[1], equal_nan=True)
    assert {"code": "L-INPUT-UNFLIPPED", "photo": "p02", "action": "none"} in got["findings"]
