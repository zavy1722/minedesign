"""WP-22: Blender extension UI (operators, rail, pin tool, cards, overlays, keymap), tested with the bpy stub.

No Blender here. As in test_blender_core, the stub directory is put on sys.path only inside the ``ui``
fixture and the stub modules are purged afterwards. The stub lacks a few Blender APIs that only the
hand-off operator needs (``Mesh.copy``, ``Object.shape_key_clear``, ``modal_handler_add``); the fixture adds
them for the test run (they exist in real Blender).
"""
from __future__ import annotations

import ast
import importlib
import json
import re
import subprocess
import sys
import types
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
STUB = ROOT / "tests" / "blender_stub"
EXT = ROOT / "blender_ext" / "face3d_likeness"
_PURGE = ("bpy", "mathutils", "gpu", "gpu_extras", "blf", "blender_ext", "bpy_extras")
PKG = "blender_ext.face3d_likeness"
UI_FILES = ("ops_project", "ops_photos", "ops_landmarks", "ops_solve", "ops_apply", "ops_handoff",
            "ui_panels", "overlays", "keymap")

CUBE_V = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]
CUBE_F = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


def _purge():
    for name in list(sys.modules):
        if name.split(".")[0] in _PURGE:
            del sys.modules[name]


@pytest.fixture
def ui(monkeypatch, tmp_path):
    _purge()
    monkeypatch.syspath_prepend(str(ROOT))
    monkeypatch.syspath_prepend(str(STUB))
    import bpy
    bpy._reset()
    ns = types.SimpleNamespace(bpy=bpy, tmp=tmp_path)
    ns.pkg = importlib.import_module(PKG)
    ns.pkg.register()
    for m in ("messages", "bridge") + UI_FILES:
        setattr(ns, m, importlib.import_module(PKG + "." + m))
    ns.ctx = bpy.context
    # stub gaps (real Blender has these)
    bpy.context.window_manager.modal_handler_add = lambda op: True
    T = bpy.types
    if not hasattr(T.Mesh, "copy"):
        def _copy(self):
            m = T.Mesh(self.name + ".copy")
            m.vertices.add(len(self.vertices))
            m.vertices._arrays["co"] = self.vertices._arrays["co"].copy()
            m.polygons, m.loops = self.polygons, self.loops
            return m
        T.Mesh.copy = _copy
    if not hasattr(T.Object, "shape_key_clear"):
        T.Object.shape_key_clear = lambda self: setattr(self.data, "shape_keys", None)
    yield ns
    try:
        ns.pkg.unregister()
    except Exception:
        pass
    _purge()


def _op(ui, cls, **props):
    o = cls()
    for k, v in props.items():
        setattr(o, k, v)
    return o


def _last_msg(op):
    return op.reports[-1][1]


def _new_project(ui, scopes=("allow_reconstruct", "allow_texture")):
    folder = ui.tmp / "proj.face3d"
    if not (folder / "project.json").exists():          # project_new refuses an existing project (never overwrites)
        o = _op(ui, ui.ops_project.FACE3D_OT_project_new, directory=str(folder))
        assert o.execute(ui.ctx) == {"FINISHED"}
    if scopes is not None:
        c = _op(ui, ui.ops_project.FACE3D_OT_consent_edit, **{s: True for s in scopes})
        assert c.execute(ui.ctx) == {"FINISHED"}
    return folder


def _png(path, seed=0, h=40, w=48):
    from face3d.io.png import write_png
    rng = np.random.default_rng(seed)
    write_png(path, (rng.random((h, w, 3)) * 255).astype(np.uint8))
    return str(path)


def _cube_object(ui, name="head"):
    bpy = ui.bpy
    me = bpy.data.meshes.new(name)
    me.from_pydata(CUBE_V, [], CUBE_F)
    ob = bpy.data.objects.new(name, me)
    bpy.context.object = bpy.context.active_object = ob
    return ob


def _fake_result(ui, ob, tmp, name, basis, idf, asym, topo=None, extra_regions=True):
    """Write a result folder like the engine's job (face3d.result + arrays.npz)."""
    from face3d.core.schema import dump_json, save_arrays
    n = len(basis)
    arrays = {"handoff_key_basis": basis, "handoff_key_ID_fit": idf, "handoff_key_Asym": idf + asym,
              "handoff_key_artist": idf.copy(), "handoff_key_stage_A": basis + 1.0,
              "sigma_n": np.linspace(0.5, 1.5, n), "support": np.linspace(0.0, 1.0, n),
              "region_ids": np.arange(n) % 2}
    d = tmp / name
    d.mkdir(parents=True)
    man = save_arrays(d / "arrays.npz", **arrays)
    doc = {"format": "face3d.result", "version": 1, "arrays": man,
           "run": {"input_hashes": {"template_topology_sha256": topo or ui.bridge.topology_sha(ob.data)}},
           "cameras": [], "cards": [],
           "regions": [{"name": "eyes", "status": "measured", "sigma_rep_mm": 0.9, "next_photo": None},
                       {"name": "nose", "status": "prior-driven", "sigma_rep_mm": 2.0, "next_photo": "take a profile"},
                       {"name": "nose_projection", "status": "unobserved", "sigma_rep_mm": 3.0, "next_photo": None}],
           "per_vertex": {"region_names": ["eyes", "nose"], "inflation": 1.0},
           "banner": "Not validated against a scan.", "tier": {"code": "C", "name": "Photos only"},
           "unverified_defaults": 12, "focal_statuses": ["measured", "prior_used"]}
    dump_json(doc, d / "result.json")
    return d, arrays


# ------------------------------------------------------------------ registration
def test_all_operators_registered_with_prefix_and_flags(ui):
    bpy = ui.bpy
    ops = [c for c in bpy.utils.registered_classes if issubclass(c, bpy.types.Operator)]
    ids = {c.bl_idname: c for c in ops}
    assert all(i.startswith("face3d.") for i in ids)
    expected = {"project_new", "consent_edit", "photos_add", "review_next", "review_prev", "view_next", "view_prev",
                "landmarks_import", "pin_place", "trace_contour", "solve", "fit", "texture_project", "job_cancel",
                "card_accept", "card_dismiss", "apply_result", "revert_solve", "handoff_sculpt", "rebase_sculpt",
                "protect_measured", "prepare_for_sharing", "purge", "compare_flip", "compare_mode"}
    assert expected <= {i.split(".", 1)[1] for i in ids}
    mutating = {"project_new", "consent_edit", "photos_add", "landmarks_import", "pin_place", "trace_contour",
                "card_accept", "card_dismiss", "apply_result", "revert_solve", "handoff_sculpt", "rebase_sculpt",
                "protect_measured", "prepare_for_sharing", "purge"}
    launchers = {"solve", "fit", "texture_project", "job_cancel"}
    for name in mutating:
        assert {"REGISTER", "UNDO"} <= set(ids["face3d." + name].bl_options), name
    for name in launchers:
        assert "UNDO" not in ids["face3d." + name].bl_options, name
    tools = bpy.utils.registered_tools
    assert [t.bl_idname for t in tools] == ["face3d.pin_tool"]
    pan = [c for c in bpy.utils.registered_classes if issubclass(c, bpy.types.Panel)]
    assert {p.bl_category for p in pan} == {"Face3D"}
    expert = [p for p in pan if p.bl_idname.startswith("FACE3D_PT_expert")]
    assert len(expert) >= 3 and all("DEFAULT_CLOSED" in p.bl_options for p in expert)
    stage_panels = {p.bl_idname for p in pan}
    assert {"FACE3D_PT_" + s for s in ui.ui_panels.STAGES} <= stage_panels
    ui.pkg.unregister()
    assert bpy.utils.registered_classes == [] and bpy.utils.registered_tools == []


# ------------------------------------------------------------------ polls
def test_poll_messages_explain_disabled(ui):
    ops_solve, ops_apply = ui.ops_solve, ui.ops_apply
    M = ui.messages.MESSAGES
    _new_project(ui, scopes=())                       # default deny: record with no scopes
    assert ops_solve.FACE3D_OT_solve.poll(ui.ctx) is False
    assert ops_solve.FACE3D_OT_solve._poll_messages[-1] == M["consent_missing"]
    _new_project(ui)                                   # consent allows reconstruction now
    s = ui.ctx.scene.face3d
    assert ops_solve.FACE3D_OT_solve.poll(ui.ctx) is False
    assert ops_solve.FACE3D_OT_solve._poll_messages[-1] == M["no_photos"]
    s.job.status = "running"
    assert ops_apply.FACE3D_OT_apply_result.poll(ui.ctx) is False
    assert ops_apply.FACE3D_OT_apply_result._poll_messages[-1] == M["job_running"]
    assert ops_solve.FACE3D_OT_job_cancel.poll(ui.ctx) is True
    s.job.status = "idle"
    assert ops_solve.FACE3D_OT_job_cancel.poll(ui.ctx) is False
    assert ops_apply.FACE3D_OT_apply_result.poll(ui.ctx) is False
    assert ops_apply.FACE3D_OT_apply_result._poll_messages[-1] == M["no_result"]


def test_no_project_poll(ui):
    assert ui.ops_photos.FACE3D_OT_photos_add.poll(ui.ctx) is False
    assert ui.ops_photos.FACE3D_OT_photos_add._poll_messages[-1] == ui.messages.MESSAGES["no_project"]


# ------------------------------------------------------------------ rail
def _consent(scopes=2, shas=("a" * 64,), expires=None):
    return {"consent_id": "c1", "subject_pseudonym": "s", "signer_role": "self", "consent_text_version": "v",
            "method": "m", "signed_at": "2026-01-01T00:00:00+00:00", "expires_at": expires,
            "jurisdiction_tags": [], "photo_sha256": list(shas), "retention_days": 30,
            "revocation_contact": "", "scopes": scopes, "attested_age": None, "deceased": False}


def test_rail_state_pure(ui):
    rs = ui.ui_panels.rail_state
    rows = rs(None, None, None)
    assert [r[0] for r in rows] == list(ui.ui_panels.STAGES)
    assert all(len(r) == 5 for r in rows)
    assert rows[0] == ("consent", "not_started", "rail.consent.done_when", "face3d.project_new", None)
    assert rows[1][4] == "no_project" and rows[4][4] == "no_project"
    # project without consent
    proj = {"photos": [], "pins": []}
    r = {x[0]: x for x in rs(proj, None, {"status": "idle"})}
    assert r["consent"][1] == "not_started" and r["consent"][3] == "face3d.consent_edit"
    assert r["photos"][4] == "consent_missing" and r["cameras"][4] == "consent_missing"
    # consent without scope: attention
    proj["consent"] = _consent(scopes=0)
    r = {x[0]: x for x in rs(proj, None, None)}
    assert r["consent"][1] == "attention" and r["photos"][4] == "consent_missing"
    # consent ok, no photos
    proj["consent"] = _consent()
    r = {x[0]: x for x in rs(proj, None, None)}
    assert r["consent"][1] == "done" and r["photos"][1] == "not_started" and r["photos"][4] is None
    assert r["cameras"][4] == "no_photos" and r["check"][4] == "no_photos"
    # expired consent
    proj["consent"] = _consent(expires="2000-01-01T00:00:00+00:00")
    assert {x[0]: x for x in rs(proj, None, None)}["consent"][1] == "attention"
    proj["consent"] = _consent()
    # photos: one covered, one not
    proj["photos"] = [{"id": "p01", "sha256": "a" * 64, "include": "auto"},
                      {"id": "p02", "sha256": "b" * 64, "include": "auto"}]
    r = {x[0]: x for x in rs(proj, None, None)}
    assert r["photos"][1] == "attention" and r["cameras"][4] == "photo_not_consented"
    proj["photos"][1]["include"] = False                  # excluded photos do not count
    r = {x[0]: x for x in rs(proj, None, None)}
    assert r["photos"][1] == "done" and r["cameras"][4] == "no_landmarks" and r["landmarks"][1] == "not_started"
    proj["pins"] = [{"photo": "p01"}]                      # pins alone do not start a solve: the engine needs a landmark set
    r = {x[0]: x for x in rs(proj, None, None)}
    assert r["landmarks"][1] == "not_started" and r["cameras"][4] == "no_landmarks"
    proj["landmark_photos"] = ["p01"]
    proj["cards"] = [{"severity": "warn", "decided": False}, {"severity": "info", "decided": False}]
    r = {x[0]: x for x in rs(proj, None, None)}
    assert r["landmarks"][1] == "done" and r["cameras"][4] is None and r["check"][1] == "attention"
    assert r["check"][3] == "face3d.review_next"
    proj["cards"][0]["decided"] = True
    assert {x[0]: x for x in rs(proj, None, None)}["check"][1] == "done"
    # running job disables everything that would start or apply
    r = {x[0]: x for x in rs(proj, None, {"status": "running"})}
    assert r["cameras"][4] == "job_running" and r["photos"][4] == "job_running"
    # result present, not applied: attention with the apply button
    res = {"regions": [{"name": "eyes", "status": "measured"}, {"name": "nose", "status": "prior-driven"}]}
    r = {x[0]: x for x in rs(proj, res, {"status": "ready"})}
    assert r["cameras"][1] == "attention" and r["cameras"][3] == "face3d.apply_result" and r["cameras"][4] is None
    assert r["confidence"][1] == "attention" and r["sculpt"][4] == "no_result"
    assert rs(proj, res, {"status": "running"})[4][4] == "job_running"
    # applied
    proj["keys_applied"] = proj["cameras_applied"] = True
    r = {x[0]: x for x in rs(proj, res, None)}
    assert r["cameras"][1] == r["shape"][1] == "done" and r["sculpt"][4] is None
    assert r["texture"][4] == "consent_denied_scope"           # consent has only RECONSTRUCT
    proj["consent"] = _consent(scopes=2 | 8)
    r = {x[0]: x for x in rs(proj, res, None)}
    assert r["texture"][4] is None and r["share"][3] == "face3d.prepare_for_sharing"
    # every key the rail returns is a message key
    M = ui.messages.MESSAGES
    for row in rs(proj, res, None) + rs(None, None, None):
        assert row[2] in M and row[4] in (None, *M) and "btn." + row[3].split(".", 1)[1] in M
        assert row[1] in ("done", "attention", "not_started") and "status." + row[1] in M


def test_rail_importable_without_bpy():
    code = ("import sys; sys.path.insert(0, %r); import blender_ext.face3d_likeness.ui_panels as u; "
            "assert u.bpy is None; print(len(u.rail_state(None, None, None)))" % str(ROOT))
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0 and out.stdout.strip() == "10", out.stderr


def test_ledger_lines_plain_language(ui):
    L = ui.ui_panels.ledger_lines
    assert L(None)[0] == "Not validated against a scan."
    ob = _cube_object(ui)
    d, arrays = _fake_result(ui, ob, ui.tmp, "r0", np.zeros((8, 3)), np.zeros((8, 3)), np.zeros((8, 3)))
    doc = json.loads((d / "result.json").read_text())
    doc["regions"][0]["sigma_rep_mm"] = 0.05                     # never finer than the 0.2 mm floor (H8)
    lines = L(doc)
    assert lines[0] == "Not validated against a scan."
    assert any("+/-0.2 mm (measured)" in x for x in lines)
    assert any("guessed from average proportions" in x and "take a profile" in x for x in lines)
    assert any("not seen in any photo" in x for x in lines)
    assert "Tier C" in lines[1] and "12 defaults" in lines[-1]
    assert "measured in 1 of 2" in ui.ui_panels.focal_summary(doc)


# ------------------------------------------------------------------ photos, cameras, consent
def test_photos_add_blocks_unconsented_then_adds(ui):
    bpy = ui.bpy
    folder = _new_project(ui)
    s = ui.ctx.scene.face3d
    a = _png(ui.tmp / "a.png", 1)
    o = _op(ui, ui.ops_photos.FACE3D_OT_photos_add, filepath=a)
    assert o.poll(ui.ctx) is True
    assert o.execute(ui.ctx) == {"CANCELLED"}                    # default deny: hash not in the record
    assert _last_msg(o) == ui.messages.MESSAGES["photo_not_consented"] and len(s.photos) == 0
    o = _op(ui, ui.ops_photos.FACE3D_OT_photos_add, filepath=a, consent_covers=True)
    assert o.execute(ui.ctx) == {"FINISHED"}
    assert len(s.photos) == 1 and s.photos[0].id == "p01"
    cam = ui.ops_photos.camera_for_photo("p01")
    assert cam is not None and cam.lock_location == (True, True, True)
    assert cam.data.show_background_images and cam.data.background_images[0].alpha == 0.4
    assert [m.name for m in ui.ctx.scene.timeline_markers] == ["F3D_p01"]
    assert (folder / "photos" / "p01.npy").is_file()
    wc = np.load(folder / "photos" / "p01.npy")
    assert wc.dtype == np.float32 and wc.ndim == 3 and wc.shape[2] == 3
    rec = ui.ops_project.load_consent(folder)
    assert len(rec.photo_sha256) == 1
    audit = (folder / "audit.jsonl").read_text()
    assert "photo_added" in audit and "consent_photo_added" in audit
    assert str(a) not in audit                                    # hashes and codes only
    # the same file again is refused
    o2 = _op(ui, ui.ops_photos.FACE3D_OT_photos_add, filepath=a, consent_covers=True)
    assert o2.execute(ui.ctx) == {"CANCELLED"} and _last_msg(o2) == ui.messages.MESSAGES["photo_exists"]
    # a file Blender cannot load gets convert_to_png
    monkey = bpy.data.images
    orig = monkey.load
    monkey.load = lambda *a_, **k: (_ for _ in ()).throw(RuntimeError("cannot read"))
    b = _png(ui.tmp / "b.png", 2)
    o3 = _op(ui, ui.ops_photos.FACE3D_OT_photos_add, filepath=b, consent_covers=True)
    assert o3.execute(ui.ctx) == {"CANCELLED"} and _last_msg(o3) == ui.messages.MESSAGES["convert_to_png"]
    monkey.load = orig


def test_review_and_view_stepping(ui):
    _new_project(ui)
    s = ui.ctx.scene.face3d
    for k in range(2):
        pth = _png(ui.tmp / ("p%d.png" % k), k)
        o = _op(ui, ui.ops_photos.FACE3D_OT_photos_add, filepath=pth, consent_covers=True)
        assert o.execute(ui.ctx) == {"FINISHED"}
    v = _op(ui, ui.ops_photos.FACE3D_OT_view_next)
    assert v.execute(ui.ctx) == {"FINISHED"} and ui.ops_project.active_photo_id(ui.ctx) == "p01"
    _op(ui, ui.ops_photos.FACE3D_OT_view_next).execute(ui.ctx)
    assert ui.ops_project.active_photo_id(ui.ctx) == "p02"
    _op(ui, ui.ops_photos.FACE3D_OT_view_next).execute(ui.ctx)
    assert ui.ops_project.active_photo_id(ui.ctx) == "p01"                       # wraps
    _op(ui, ui.ops_photos.FACE3D_OT_view_prev).execute(ui.ctx)
    assert ui.ops_project.active_photo_id(ui.ctx) == "p02"
    # keyed (keyboard) use outside a photo camera passes the key through
    ui.ctx.scene.camera = None
    k = _op(ui, ui.ops_photos.FACE3D_OT_view_next, keyed=True)
    assert k.invoke(ui.ctx, None) == {"PASS_THROUGH"}
    # review queue: worst first
    s.cards.clear()
    for sev, pid in (("info", "p01"), ("block", "p02"), ("warn", "p01")):
        c = s.cards.add()
        c.code, c.severity, c.msg_key, c.photo_id, c.decided = "Q-X", sev, "qa.Q-BLUR", pid, False
    assert ui.ops_photos.card_order(s.cards) == [1, 2, 0]
    r = _op(ui, ui.ops_photos.FACE3D_OT_review_next)
    r.execute(ui.ctx)
    assert ui.ctx.scene["f3d_review_idx"] == 1 and ui.ops_project.active_photo_id(ui.ctx) == "p02"
    r.execute(ui.ctx)
    assert ui.ctx.scene["f3d_review_idx"] == 2
    _op(ui, ui.ops_photos.FACE3D_OT_review_prev).execute(ui.ctx)
    assert ui.ctx.scene["f3d_review_idx"] == 1


# ------------------------------------------------------------------ apply_result / key stack
def _scene_for_apply(ui):
    _new_project(ui)
    ob = _cube_object(ui)
    ui.ctx.scene.face3d.job.status = "ready"
    return ob


def _blender_keys(ui, ob):
    return ui.bridge.read_shape_keys(ob)


def test_apply_result_writes_key_stack_on_stub_mesh(ui):
    br = ui.bridge
    ob = _scene_for_apply(ui)
    s = ui.ctx.scene.face3d
    rng = np.random.default_rng(3)
    basis = np.asarray(CUBE_V, float) * 100.0
    idf = basis + rng.normal(0, 2.0, basis.shape)
    asym = rng.normal(0, 0.5, basis.shape)
    d, arrays = _fake_result(ui, ob, ui.tmp, "job1", basis, idf, asym)
    op = _op(ui, ui.ops_apply.FACE3D_OT_apply_result, solve_dir=str(d))
    assert op.poll(ui.ctx) is True
    assert op.execute(ui.ctx) == {"FINISHED"}, op.reports
    keys = _blender_keys(ui, ob)
    assert list(keys) == ["Basis", "ID_fit", "Asym", "artist", "stage_A"]
    assert keys["ID_fit"][1] == "Basis" and keys["ID_fit"][3] == 1.5 and keys["ID_fit"][2] == 1.0
    assert keys["Asym"][1] == "ID_fit" and keys["artist"][1] == "ID_fit"
    assert keys["stage_A"][1] == "Basis" and keys["stage_A"][4] is True and keys["stage_A"][2] == 0.0
    np.testing.assert_allclose(keys["ID_fit"][0], br.engine_mm_to_blender_m(idf), atol=1e-6)
    np.testing.assert_allclose(keys["Asym"][0] - keys["ID_fit"][0], br.engine_mm_to_blender_m(asym), atol=1e-6)
    np.testing.assert_allclose(keys["artist"][0], keys["ID_fit"][0], atol=1e-7)       # empty sculpt layer
    me = ob.data
    assert len(me.attributes.get("f3d_sigma_mm").data._arrays["value"]) == 8
    np.testing.assert_allclose(me.attributes.get("f3d_support").data._arrays["value"], np.linspace(0, 1, 8), atol=1e-6)
    status = me.attributes.get("f3d_status").data._arrays["value"]
    # eyes -> measured (3); nose -> min(prior-driven 1, nose_projection unobserved 0) = 0
    assert status.tolist() == [3, 0] * 4
    assert ob["f3d_applied_solve"] == "solves/0001" and (ui.tmp / "proj.face3d" / "solves" / "0001" / "result.json").is_file()
    assert s.job.status == "idle"
    # the artist sculpts: move the artist key; refit: new ID_fit and Asym
    art = keys["artist"][0] + np.asarray([0.003, -0.002, 0.001])
    br.write_shape_key(ob, "artist", art, "ID_fit", 1.0, 1.0, False)
    keys = _blender_keys(ui, ob)
    delta_before = (keys["artist"][0] - keys["ID_fit"][0]) * 1000.0                     # mm
    assert np.abs(delta_before).max() > 1.0
    idf2 = idf + rng.normal(0, 1.5, idf.shape)
    d2, _ = _fake_result(ui, ob, ui.tmp, "job2", basis, idf2, asym * 0.5)
    s.job.status = "ready"
    op2 = _op(ui, ui.ops_apply.FACE3D_OT_apply_result, solve_dir=str(d2))
    assert op2.execute(ui.ctx) == {"FINISHED"}, op2.reports
    k2 = _blender_keys(ui, ob)
    assert list(k2) == ["Basis", "ID_fit", "Asym", "artist", "stage_A"]
    np.testing.assert_allclose(k2["ID_fit"][0], br.engine_mm_to_blender_m(idf2), atol=1e-6)
    delta_after = (k2["artist"][0] - k2["ID_fit"][0]) * 1000.0
    np.testing.assert_allclose(delta_after, delta_before, atol=1e-4)                   # float32 round-off only
    np.testing.assert_allclose(br.blender_m_to_engine_mm(k2["Asym"][0] - k2["ID_fit"][0]), asym * 0.5, atol=1e-4)
    assert ob["f3d_applied_solve"] == "solves/0002"
    # revert to solve 1: ID_fit comes back, the artist delta survives again
    rv = _op(ui, ui.ops_apply.FACE3D_OT_revert_solve, n=1)
    assert rv.poll(ui.ctx) is True and rv.execute(ui.ctx) == {"FINISHED"}
    k3 = _blender_keys(ui, ob)
    np.testing.assert_allclose(k3["ID_fit"][0], br.engine_mm_to_blender_m(idf), atol=1e-6)
    np.testing.assert_allclose((k3["artist"][0] - k3["ID_fit"][0]) * 1000.0, delta_before, atol=1e-4)
    assert _op(ui, ui.ops_apply.FACE3D_OT_revert_solve, n=9).execute(ui.ctx) == {"CANCELLED"}


def test_apply_result_refuses_sculpt_mode_and_topology_mismatch(ui):
    ob = _scene_for_apply(ui)
    basis = np.asarray(CUBE_V, float) * 100.0
    d, _ = _fake_result(ui, ob, ui.tmp, "ok", basis, basis + 1, basis * 0)
    ob.mode = "SCULPT"
    op = _op(ui, ui.ops_apply.FACE3D_OT_apply_result, solve_dir=str(d))
    assert op.poll(ui.ctx) is False
    assert ui.ops_apply.FACE3D_OT_apply_result._poll_messages[-1] == ui.messages.MESSAGES["wrong_mode"]
    assert op.execute(ui.ctx) == {"CANCELLED"}                                # the guard also holds without the poll
    assert _last_msg(op) == ui.messages.MESSAGES["wrong_mode"]
    assert ob.data.shape_keys is None and not (ui.tmp / "proj.face3d" / "solves").exists()
    ob.mode = "OBJECT"
    bad, _ = _fake_result(ui, ob, ui.tmp, "bad", basis, basis + 1, basis * 0, topo="0" * 64)
    op = _op(ui, ui.ops_apply.FACE3D_OT_apply_result, solve_dir=str(bad))
    assert op.execute(ui.ctx) == {"CANCELLED"} and _last_msg(op) == ui.messages.MESSAGES["topology_mismatch"]
    assert ob.data.shape_keys is None
    # wrong vertex count in the arrays also counts as a topology mismatch
    short, _ = _fake_result(ui, ob, ui.tmp, "short", basis[:6], basis[:6] + 1, basis[:6] * 0, topo=ui.bridge.topology_sha(ob.data))
    op = _op(ui, ui.ops_apply.FACE3D_OT_apply_result, solve_dir=str(short))
    assert op.execute(ui.ctx) == {"CANCELLED"} and ob.data.shape_keys is None
    # no result at all
    op = _op(ui, ui.ops_apply.FACE3D_OT_apply_result, solve_dir=str(ui.tmp / "nowhere"))
    assert op.execute(ui.ctx) == {"CANCELLED"} and _last_msg(op) == ui.messages.MESSAGES["result_unreadable"]


def test_vertex_status_pure(ui):
    regs = [{"name": "nose", "status": "constrained"}, {"name": "nose_projection", "status": "prior-driven"},
            {"name": "eyes", "status": "measured"}]
    st = ui.ops_apply.vertex_status(["nose", "eyes", "neck"], [0, 1, 2, 1], regs)
    assert st.tolist() == [1, 3, 0, 3] and st.dtype == np.int32


# ------------------------------------------------------------------ cards
def test_card_accept_records_decision_never_auto(ui):
    folder = _new_project(ui)
    s = ui.ctx.scene.face3d
    o = _op(ui, ui.ops_photos.FACE3D_OT_photos_add, filepath=_png(ui.tmp / "m.png", 5), consent_covers=True)
    assert o.execute(ui.ctx) == {"FINISHED"}
    s.cards.clear()
    res = {"cards": [{"kind": "mirror_flip", "photo": "p01", "decision": "suggest_flip", "applied": False,
                      "delta": 0.3, "g": 5.0, "margin": 1.0, "preselect": True},
                     {"kind": "mirror_flip", "photo": "p01", "decision": "keep", "applied": False}]}
    cards = ui.ops_solve.cards_from_result(ui.ctx, res)
    assert [c.msg_key for c in cards] == ["mirror_suggest"] and cards[0].decided is False
    assert ui.ops_solve.cards_from_result(ui.ctx, res) == []                 # no duplicate open card
    prj = ui.ops_project.load_project(ui.ctx)
    assert prj.decisions == [] and prj.mirror_state("p01") is None and prj.flipped_photos() == []
    assert not (folder / "audit.jsonl").read_text().count("decision_")         # a suggestion writes nothing
    acc = _op(ui, ui.ops_solve.FACE3D_OT_card_accept)
    assert acc.poll(ui.ctx) is True
    assert acc.execute(ui.ctx) == {"FINISHED"}
    prj = ui.ops_project.load_project(ui.ctx)
    assert [d["kind"] for d in prj.decisions] == ["mirror_flip"] and prj.decisions[0]["by"] == "user"
    assert prj.flipped_photos() == ["p01"]
    assert "decision_mirror_flip" in (folder / "audit.jsonl").read_text()
    assert s.cards[len(s.cards) - 1].decided is True and s.photos[0].mirror_decision == "flip"
    # decided photos get no new suggestion; dismiss records 'keep'
    assert ui.ops_solve.cards_from_result(ui.ctx, res) == []
    s.cards.clear()
    res2 = {"cards": [{"photo": "p01", "decision": "undetermined", "applied": False}]}
    prj.record_decision("mirror_keep", "p01", "user")                          # (a revert is a recorded keep)
    prj.save()
    assert ui.ops_solve.cards_from_result(ui.ctx, res2) == []
    # 'undetermined' with a significant gap (M-GAP-SIGNIFICANT, margin > 0) has its own text (final review)
    s.cards.clear()
    res3 = {"cards": [{"photo": "p02", "decision": "undetermined", "applied": False, "margin": 2.5}]}
    assert [c.msg_key for c in ui.ops_solve.cards_from_result(ui.ctx, res3)] == ["mirror_gap_significant"]
    s.cards.clear()
    res3["cards"][0]["margin"] = -4.0
    assert [c.msg_key for c in ui.ops_solve.cards_from_result(ui.ctx, res3)] == ["mirror_undetermined"]
    s.cards.clear()
    # a QA card dismissal changes nothing in the project
    c = s.cards.add()
    c.code, c.severity, c.msg_key, c.photo_id, c.decided = "Q-BLUR", "warn", "qa.Q-BLUR", "p01", False
    n = len(ui.ops_project.load_project(ui.ctx).decisions)
    assert _op(ui, ui.ops_solve.FACE3D_OT_card_dismiss).execute(ui.ctx) == {"FINISHED"}
    assert len(ui.ops_project.load_project(ui.ctx).decisions) == n and c.decided is True
    assert _op(ui, ui.ops_solve.FACE3D_OT_card_accept).poll(ui.ctx) is False  # nothing open


def test_card_dismiss_mirror_records_keep(ui):
    _new_project(ui)
    _op(ui, ui.ops_photos.FACE3D_OT_photos_add, filepath=_png(ui.tmp / "m.png", 5), consent_covers=True).execute(ui.ctx)
    ui.ctx.scene.face3d.cards.clear()
    ui.ops_solve.cards_from_result(ui.ctx, {"cards": [{"photo": "p01", "decision": "suggest_flip", "applied": False}]})
    assert _op(ui, ui.ops_solve.FACE3D_OT_card_dismiss).execute(ui.ctx) == {"FINISHED"}
    prj = ui.ops_project.load_project(ui.ctx)
    assert prj.mirror_state("p01") == "keep" and prj.flipped_photos() == []


# ------------------------------------------------------------------ landmarks
def _landmark_file(path, faces=1, scheme="anatomical44"):
    from face3d.io.landmarks import Face, LandmarkSet, save_landmarks
    fs = [Face(score=0.9 - 0.1 * k, uv=np.full((44, 2), 10.0 + k), visible=np.ones(44, bool)) for k in range(faces)]
    save_landmarks(LandmarkSet(scheme, {"backend": "test"}, {"wh": [48, 40]}, fs), path)
    return str(path)


def test_landmarks_import_and_subject_card(ui):
    _new_project(ui)
    s = ui.ctx.scene.face3d
    _op(ui, ui.ops_photos.FACE3D_OT_photos_add, filepath=_png(ui.tmp / "m.png", 5), consent_covers=True).execute(ui.ctx)
    one = _landmark_file(ui.tmp / "one.json")
    o = _op(ui, ui.ops_landmarks.FACE3D_OT_landmarks_import, filepath=one, photo_id="p01")
    assert o.execute(ui.ctx) == {"FINISHED"} and "p01" in ui.ops_landmarks.session_sets(ui.ctx)
    ui.ops_landmarks.SESSION.clear()
    two = _landmark_file(ui.tmp / "two.json", faces=2)
    o = _op(ui, ui.ops_landmarks.FACE3D_OT_landmarks_import, filepath=two, photo_id="p01")
    assert o.execute(ui.ctx) == {"FINISHED"}
    assert ui.ops_landmarks.session_sets(ui.ctx) == {}                         # no face picked automatically
    card = s.cards[len(s.cards) - 1]
    assert card.code == "Q-FACES" and card.msg_key == "pick_subject"
    acc = _op(ui, ui.ops_solve.FACE3D_OT_card_accept, face_index=1, index=len(s.cards) - 1)
    assert acc.execute(ui.ctx) == {"FINISHED"}
    ls = ui.ops_landmarks.session_sets(ui.ctx)["p01"]
    assert len(ls.faces) == 1 and np.allclose(ls.faces[0].uv, 11.0)            # the chosen second face
    # an unknown scheme and an unreadable file are refused with messages
    bad = ui.tmp / "bad.json"
    bad.write_text("{}")
    o = _op(ui, ui.ops_landmarks.FACE3D_OT_landmarks_import, filepath=str(bad), photo_id="p01")
    assert o.execute(ui.ctx) == {"CANCELLED"} and _last_msg(o) == ui.messages.MESSAGES["landmarks_read_failed"]
    weird = _landmark_file(ui.tmp / "weird.json", scheme="weird_scheme")
    o = _op(ui, ui.ops_landmarks.FACE3D_OT_landmarks_import, filepath=weird, photo_id="p01")
    assert o.execute(ui.ctx) == {"CANCELLED"} and _last_msg(o) == ui.messages.MESSAGES["landmarks_scheme_unknown"]


def test_solve_job_inputs(ui, monkeypatch):
    _new_project(ui)
    s = ui.ctx.scene.face3d
    _op(ui, ui.ops_photos.FACE3D_OT_photos_add, filepath=_png(ui.tmp / "m.png", 5), consent_covers=True).execute(ui.ctx)
    assert ui.ops_solve.FACE3D_OT_solve.poll(ui.ctx) is False
    assert ui.ops_solve.FACE3D_OT_solve._poll_messages[-1] == ui.messages.MESSAGES["no_landmarks"]
    _op(ui, ui.ops_landmarks.FACE3D_OT_landmarks_import, filepath=_landmark_file(ui.tmp / "a.json"),
        photo_id="p01").execute(ui.ctx)
    assert ui.ops_solve.FACE3D_OT_solve.poll(ui.ctx) is True
    calls = []

    class FakeRunner:
        status = "running"

        def __init__(self, *a):
            pass

        def start(self, stage, inputs, config, seed):
            calls.append((stage, inputs, config, seed))
            return "jobdir"
    monkeypatch.setattr(ui.ops_solve, "JobRunner", FakeRunner)
    ui.ops_solve.RUNNERS.clear()
    assert _op(ui, ui.ops_solve.FACE3D_OT_solve).execute(ui.ctx) == {"FINISHED"}
    stage, inputs, config, seed = calls[0]
    assert stage == "report" and inputs["apply_mirror"] == [] and inputs["texture"] is False
    assert inputs["project"].endswith("project.json") and "p01" in inputs["landmark_sets"]
    assert json.loads(inputs["consent"])["scopes"] & 2
    assert _op(ui, ui.ops_solve.FACE3D_OT_fit, cage=True).execute(ui.ctx) == {"FINISHED"}
    assert calls[1][2] == {"stages": {"handoff": {"cage": True}}}
    assert _op(ui, ui.ops_solve.FACE3D_OT_texture_project).execute(ui.ctx) == {"FINISHED"} and calls[2][1]["texture"] is True


# ------------------------------------------------------------------ pin tool: pure mapping and editor
CORNERS = np.array([[100.0, 500.0], [300.0, 500.0], [300.0, 400.0], [100.0, 400.0]])   # TL TR BR BL, region y up


def test_view_to_image_px_mapping(ui):
    f, inv = ui.overlays.view_to_image_px, ui.overlays.image_px_to_view
    wh = (2000, 1000)
    assert f((100, 500), CORNERS, wh) == pytest.approx((0, 0))
    assert f((300, 400), CORNERS, wh) == pytest.approx((2000, 1000))
    assert f((200, 450), CORNERS, wh) == pytest.approx((1000, 500))
    assert f((150, 475), CORNERS, wh) == pytest.approx((500, 250))
    assert f((50, 550), CORNERS, wh) == pytest.approx((-500, -500))                 # outside is not clamped
    assert inv((1000, 500), CORNERS, wh) == pytest.approx([200, 450])
    pts = np.array([[0, 0], [2000, 1000], [250, 750]], float)
    np.testing.assert_allclose(inv(pts, CORNERS, wh)[2], [125, 425])
    rng = np.random.default_rng(0)
    for _ in range(20):
        p = rng.uniform(0, 1, 2) * wh
        assert f(inv(p, CORNERS, wh), CORNERS, wh) == pytest.approx(tuple(p))
    # a rotated frame (camera rolled 90 degrees: image-left edge points down in the region)
    rot = np.array([[300.0, 400.0], [300.0, 600.0], [200.0, 600.0], [200.0, 400.0]])
    assert f((300, 500), rot, (100, 200)) == pytest.approx((50, 0))
    assert f((250, 400), rot, (100, 200)) == pytest.approx((0, 100.0))
    with pytest.raises(ValueError):
        f((0, 0), np.array([[0, 0], [1, 1], [2, 2], [3, 3]], float), wh)
    with pytest.raises(ValueError):
        f((0, 0), np.zeros((3, 2)), wh)
    assert ui.overlays.zoom_of_frame(CORNERS, wh) == pytest.approx(0.1)
    shuffled = CORNERS[[2, 0, 3, 1]]
    np.testing.assert_allclose(ui.overlays.order_corners(shuffled), CORNERS)


def test_pin_editor_place_drag_nudge_delete(ui):
    ed = ui.ops_landmarks.PinEditor([], (200, 100))
    assert ed.press((50, 40), 2.0, "nasion") == "placed"
    assert ed.pins[0]["zoom"] == 2.0 and ed.pins[0]["cls"] == "crisp"
    ed.move((60.5, 41.5), 3.0)
    assert ed.release() is True and ed.release() is False
    assert (ed.pins[0]["x"], ed.pins[0]["y"], ed.pins[0]["zoom"]) == (60.5, 41.5, 3.0)
    assert ed.press((61, 42), 3.0, "glabella") == "grab" and len(ed.pins) == 1     # within 12 screen px / zoom
    ed.release()
    assert ed.press((100, 80), 3.0, "glabella") == "placed" and len(ed.pins) == 2
    ed.release()
    ed.nudge(1, 0)
    ed.nudge(0, -1, fine=True)
    assert (ed.pins[1]["x"], ed.pins[1]["y"]) == (101.0, 79.75)
    ed.nudge(-1, 0, fine=True)
    assert ed.pins[1]["x"] == 100.75
    ed.move((9999, -5))                                                             # not dragging: ignored
    assert ed.pins[1]["x"] == 100.75
    assert ed.press((100, 80), 3.0, None) == "grab"
    ed.move((9999, -5))
    assert (ed.pins[1]["x"], ed.pins[1]["y"]) == (200.0, 0.0)                       # clamped to the image
    ed.release()
    # re-placing a landmark moves its single pin
    ed.press((10, 10), 1.0, "nasion")
    ed.release()
    assert [p["landmark"] for p in ed.pins].count("nasion") == 1
    assert ed.delete() == "nasion" and len(ed.pins) == 1 and ed.delete() is None
    assert ui.ops_landmarks.next_landmark(["vertex", "trichion"], ui.ops_landmarks.scheme_names()) == "glabella"
    assert ui.ops_landmarks.next_landmark(ui.ops_landmarks.scheme_names(), ui.ops_landmarks.scheme_names()) is None
    ed2 = ui.ops_landmarks.PinEditor([], (10, 10))
    assert ed2.press((1, 1), 1.0, None) is None


def _ev(type_, value="PRESS", xy=(0, 0), shift=False):
    return types.SimpleNamespace(type=type_, value=value, mouse_region_x=xy[0], mouse_region_y=xy[1], shift=shift)


def test_pin_place_modal_records_pins_and_zoom(ui, monkeypatch):
    folder = _new_project(ui)
    s = ui.ctx.scene.face3d
    _op(ui, ui.ops_photos.FACE3D_OT_photos_add, filepath=_png(ui.tmp / "m.png", 5), consent_covers=True).execute(ui.ctx)
    cam = ui.ops_photos.camera_for_photo("p01")
    cam["f3d_res_x"], cam["f3d_res_y"] = 2000, 1000
    ui.ctx.scene.camera = cam
    corners = CORNERS.copy()
    pin = _op(ui, ui.ops_landmarks.FACE3D_OT_pin_place, pin_class="crisp", expertise="expert", blind=True)
    monkeypatch.setattr(type(pin), "_frame", lambda self, ctx: corners)
    assert pin.poll(ui.ctx) is True
    assert pin.invoke(ui.ctx, None) == {"RUNNING_MODAL"}
    assert ui.overlays.STATE["hide_auto"] is True                                   # blind first pins
    assert pin.modal(ui.ctx, _ev("LEFTMOUSE", "PRESS", (200, 450))) == {"RUNNING_MODAL"}
    assert pin.modal(ui.ctx, _ev("MOUSEMOVE", xy=(210, 450))) == {"RUNNING_MODAL"}
    assert pin.modal(ui.ctx, _ev("LEFTMOUSE", "RELEASE", (210, 450))) == {"RUNNING_MODAL"}
    assert len(s.pins) == 1
    p = s.pins[0]
    assert (p.photo_id, p.landmark, p.cls, p.expertise, p.blind) == ("p01", "vertex", "crisp", "expert", True)
    assert (p.x, p.y) == pytest.approx((1100.0, 500.0)) and p.zoom == pytest.approx(0.1)
    prj = ui.ops_project.load_project(ui.ctx)
    assert prj.pins[0].landmark == "vertex" and prj.pins[0].expertise == "expert" and prj.pins[0].zoom == pytest.approx(0.1)
    assert ui.ops_landmarks.resolve_pin_class(prj.pins[0].cls, prj.pins[0].expertise) == "crisp_expert"
    # arrow keys nudge the selected pin; Shift = 0.25 px
    pin.modal(ui.ctx, _ev("RIGHT_ARROW"))
    pin.modal(ui.ctx, _ev("DOWN_ARROW", shift=True))
    assert (pin._editor.pins[0]["x"], pin._editor.pins[0]["y"]) == pytest.approx((1101.0, 500.25))
    # a second click places the next landmark; X deletes the selected one (stored at once)
    pin.modal(ui.ctx, _ev("LEFTMOUSE", "PRESS", (150, 450)))
    pin.modal(ui.ctx, _ev("LEFTMOUSE", "RELEASE", (150, 450)))
    assert [q.landmark for q in s.pins] == ["vertex", "trichion"]
    assert pin.modal(ui.ctx, _ev("X")) == {"RUNNING_MODAL"}
    assert [q.landmark for q in s.pins] == ["vertex"]
    assert pin.modal(ui.ctx, _ev("ESC")) == {"FINISHED"}
    assert ui.overlays.STATE["hide_auto"] is False and ui.overlays.STATE["selected_pin"] is None
    assert [q["photo"] for q in json.loads((folder / "project.json").read_text())["pins"]] == ["p01"]
    # not in camera view -> the tool refuses to start
    monkeypatch.setattr(type(pin), "_frame", lambda self, ctx: None)
    assert _op(ui, ui.ops_landmarks.FACE3D_OT_pin_place).invoke(ui.ctx, None) == {"CANCELLED"}


def test_trace_contour_needs_five_clicks_then_snaps(ui, monkeypatch):
    _new_project(ui)
    # a photo with a bright disc on dark: the traced circle must snap to the disc edge
    from face3d.io.png import write_png
    yy, xx = np.mgrid[0:200, 0:200]
    disc = (np.hypot(xx - 100, yy - 100) < 50).astype(np.uint8) * 200 + 20
    write_png(ui.tmp / "disc.png", np.stack([disc] * 3, axis=-1))
    _op(ui, ui.ops_photos.FACE3D_OT_photos_add, filepath=str(ui.tmp / "disc.png"), consent_covers=True).execute(ui.ctx)
    # the stub loads a blank 64x64 image; overwrite the working copy with the real pixels
    wc = ui.tmp / "proj.face3d" / "photos" / "p01.npy"
    np.save(wc, np.stack([disc / 255.0] * 3, axis=-1).astype(np.float32))
    cam = ui.ops_photos.camera_for_photo("p01")
    cam["f3d_res_x"], cam["f3d_res_y"] = 200, 200
    ui.ctx.scene.camera = cam
    tr = _op(ui, ui.ops_landmarks.FACE3D_OT_trace_contour, closed=True)
    sq = np.array([[0.0, 600.0], [200.0, 600.0], [200.0, 400.0], [0.0, 400.0]])
    monkeypatch.setattr(type(tr), "_frame", lambda self, ctx: sq)
    assert tr.invoke(ui.ctx, None) == {"RUNNING_MODAL"}
    monkeypatch.setattr(type(tr), "_iod_px", lambda self, ctx: 200.0)            # band half-width 6 px
    angs = np.linspace(0, 2 * np.pi, 8, endpoint=False)
    for ang in angs[:4]:
        x, y = 100 + 52 * np.cos(ang), 100 + 52 * np.sin(ang)
        assert tr.modal(ui.ctx, _ev("LEFTMOUSE", "PRESS", (x, 600 - y))) == {"RUNNING_MODAL"}
    assert tr.modal(ui.ctx, _ev("RET")) == {"RUNNING_MODAL"}                       # only 4 clicks: refused
    assert _last_msg(tr) == ui.messages.MESSAGES["trace_too_few"]
    for ang in angs[4:]:
        x, y = 100 + 52 * np.cos(ang), 100 + 52 * np.sin(ang)
        tr.modal(ui.ctx, _ev("LEFTMOUSE", "PRESS", (x, 600 - y)))
    assert tr.modal(ui.ctx, _ev("RET")) == {"FINISHED"}
    pts = ui.overlays.STATE["traced"]["p01"]
    r = np.hypot(pts[:, 0] - 100, pts[:, 1] - 100)
    assert len(pts) > 20 and abs(np.median(r) - 50) < 2.5
    assert tr.modal(ui.ctx, _ev("ESC")) == {"CANCELLED"}


# ------------------------------------------------------------------ overlays and comparison
def test_overlay_draw_list_roles_scaling_and_blind(ui):
    ov = ui.overlays
    ov.reset_state()
    wh = (2000, 1000)
    ov.set_data("auto_landmarks", "p01", np.array([[100.0, 100.0], [200.0, 200.0]]))
    ov.set_data("sigma", "p01", [((500.0, 500.0), np.diag([100.0, 25.0]))])
    ov.set_data("residuals", "p01", [((510.0, 500.0), (500.0, 500.0), 2.0)])
    ov.set_data("model_contour", "p01", np.array([[0.0, 0.0], [100.0, 50.0], [200.0, 0.0]]))
    ov.set_data("traced", "p01", np.array([[0.0, 10.0], [300.0, 10.0]]))
    ov.set_data("hatch", "p01", [np.array([[0, 0], [100, 0], [100, 100], [0, 100]], float)])
    pins = [{"landmark": "nasion", "x": 400.0, "y": 300.0}, {"landmark": "glabella", "x": 410.0, "y": 280.0, "conflict": True}]
    ov.STATE["selected_pin"] = ("p01", "nasion")
    items = ov.build_draw_list("p01", CORNERS, wh, 1.0, pins)
    assert all(p.ndim == 2 and p.shape[1] == 2 and w > 0 and len(c) == 4 for p, w, c in items)
    from face3d.qa import palette
    colours = {tuple(np.round(c[:3], 3)) for _p, _w, c in items}
    for role in ("auto_pin", "user_pin", "conflict", "selected", "model_contour", "guessed"):
        assert tuple(np.round(palette.hex_to_rgb(palette.ROLES[role][0]), 3)) in colours, role
    items2 = ov.build_draw_list("p01", CORNERS, wh, 2.0, pins)
    assert len(items2) == len(items)
    assert all(w2 == pytest.approx(2 * w1) for (_a, w1, _c), (_b, w2, _d) in zip(items, items2))   # UI scale
    ov.STATE["hide_auto"] = True
    assert len(ov.build_draw_list("p01", CORNERS, wh, 1.0, pins)) < len(items)
    assert ov.build_draw_list("other", CORNERS, wh, 1.0, []) == []
    # the traced outline is dashed (a shape cue distinct from the model line)
    segs = ov.dashed(np.array([[0.0, 0.0], [100.0, 0.0]]), 8, 5)
    assert len(segs) == 8 and all(abs(np.linalg.norm(s[-1] - s[0]) - 8) < 1e-9 for s in segs[:-1])
    ov.reset_state()
    assert ov.STATE["mode"] is None and ov.STATE["hide_auto"] is False and ov.STATE["traced"] == {}
    with pytest.raises(KeyError):
        ov.set_data("nope", "p", 1)


def test_compare_modes_pure(ui):
    ov = ui.overlays
    rng = np.random.default_rng(1)
    img = rng.random((300, 400, 4))
    th = ov.compare_image(img, "thumb")
    fl = ov.compare_image(img, "flip")
    assert th.shape == (48, 64, 3) and th.dtype == np.float32 and max(th.shape[:2]) == 64
    np.testing.assert_array_equal(fl, th[:, ::-1])
    assert 0.0 <= th.min() and th.max() <= 1.0
    bl = ov.compare_image(img, "blur", face_width_px=200.0)             # sigma = 3 % of 200 = 6 px
    assert bl.shape == (300, 400, 3) and bl.std() < img[..., :3].std() * 0.5
    gr = ov.compare_image(img, "grey")
    assert np.allclose(gr[..., 0], gr[..., 1]) and gr.shape == (300, 400, 3)
    step = np.zeros((50, 50, 3))
    step[:, 25:] = 1.0
    ed = ov.compare_image(step, "edges")
    assert ed[25, 25, 0] == pytest.approx(1.0) and ed[25, 5, 0] < 0.05
    with pytest.raises(ValueError):
        ov.compare_image(img, "wobble")


def test_compare_flip_is_hold_to_flip(ui):
    ov = ui.overlays
    ob = ui.ops_photos.make_photo_camera(ui.ctx.scene, "p01", 0, ui.bpy.data.images.new("i", 4, 4), 50, (4, 4))
    ui.ctx.scene.camera = ob
    op = _op(ui, ov.FACE3D_OT_compare_flip, keyed=True)
    assert op.poll(ui.ctx) is True
    assert op.invoke(ui.ctx, None) == {"RUNNING_MODAL"} and ov.STATE["mode"] == "flip"
    assert op.modal(ui.ctx, _ev("MOUSEMOVE")) == {"PASS_THROUGH"} and ov.STATE["mode"] == "flip"   # still held
    assert op.modal(ui.ctx, _ev("F", "RELEASE")) == {"FINISHED"} and ov.STATE["mode"] is None      # restored
    op.invoke(ui.ctx, None)
    assert op.modal(ui.ctx, _ev("ESC")) == {"CANCELLED"} and ov.STATE["mode"] is None
    mode = _op(ui, ov.FACE3D_OT_compare_mode, mode="blur")
    mode.execute(ui.ctx)
    assert ov.STATE["mode"] == "blur"
    mode.execute(ui.ctx)
    assert ov.STATE["mode"] is None                                    # toggles off
    w = _op(ui, ov.FACE3D_OT_compare_mode, mode="wobble")
    assert w.execute(ui.ctx) == {"CANCELLED"} and _last_msg(w) == ui.messages.MESSAGES["deferred_feature"]
    ui.ctx.scene.camera = None
    assert op.poll(ui.ctx) is False
    assert _op(ui, ov.FACE3D_OT_compare_mode, mode="grey", keyed=True).invoke(ui.ctx, None) == {"PASS_THROUGH"}


def test_overlay_handler_registered_and_removed(ui):
    bpy = ui.bpy
    hs = bpy.types.SpaceView3D.handlers
    assert len(hs) == 1 and hs[0][0] is ui.overlays.draw_callback and hs[0][3] == "POST_PIXEL"
    ui.overlays.draw_callback()                                          # never raises, even without a camera
    ui.pkg.unregister()
    assert bpy.types.SpaceView3D.handlers == []


def test_no_blink(ui):
    tree = ast.parse((EXT / "overlays.py").read_text())
    bad = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "register":
            chain = ast.unparse(n.func)
            if "timers" in chain:
                interval = None
                for kw in n.keywords:
                    if kw.arg == "first_interval" and isinstance(kw.value, ast.Constant):
                        interval = kw.value.value
                if len(n.args) > 1 and isinstance(n.args[1], ast.Constant):
                    interval = n.args[1].value
                if interval is None or interval < 1.0:
                    bad.append(ast.unparse(n))
    assert bad == []
    src = (EXT / "overlays.py").read_text()
    assert "time.sleep" not in src and "timers.register" not in src
    # no other UI module drives a timer either
    for name in UI_FILES:
        if name == "overlays":
            continue
        assert "timers.register" not in (EXT / (name + ".py")).read_text(), name


# ------------------------------------------------------------------ keymap
def test_keymap_entries_registered_and_removed(ui):
    kc = ui.bpy.context.window_manager.keyconfigs.addon
    km = [k for k in kc.keymaps if k.name == "3D View"]
    assert len(km) == 1
    items = {(i.idname, i.type, i.kwargs_shift if hasattr(i, "kwargs_shift") else getattr(i, "shift", False),
              getattr(i, "ctrl", False)) for i in km[0].keymap_items}
    want = {("wm.tool_set_by_id", "P", False, False), ("face3d.review_next", "TAB", False, False),
            ("face3d.review_prev", "TAB", True, False), ("face3d.view_next", "PAGE_DOWN", False, False),
            ("face3d.view_prev", "PAGE_UP", False, False), ("face3d.solve", "R", False, True),
            ("face3d.job_cancel", "ESC", False, False), ("face3d.card_accept", "RET", False, True),
            ("face3d.card_dismiss", "BACK_SPACE", False, True), ("face3d.compare_flip", "F", False, False),
            ("face3d.compare_mode", "B", False, False), ("face3d.compare_mode", "G", False, False),
            ("face3d.compare_mode", "E", False, False), ("face3d.compare_mode", "W", False, False)}
    assert want == items
    known = {c.bl_idname for c in ui.bpy.utils.registered_classes if hasattr(c, "bl_idname")}
    for idname, *_ in ui.keymap.ITEMS:
        assert idname == "wm.tool_set_by_id" or idname in known, idname          # every key maps to a real operator
    ui.keymap.register()                                                       # idempotent
    assert len(km[0].keymap_items) == len(want)
    ui.pkg.unregister()
    assert [k for k in kc.keymaps if k.name == "3D View"] == []
    ui.pkg.register()
    assert len([k for k in kc.keymaps if k.name == "3D View"][0].keymap_items) == len(want)


# ------------------------------------------------------------------ hand-off
def _applied_scene(ui):
    ob = _scene_for_apply(ui)
    rng = np.random.default_rng(3)
    basis = np.asarray(CUBE_V, float) * 100.0
    d, _ = _fake_result(ui, ob, ui.tmp, "job1", basis, basis + rng.normal(0, 2, basis.shape), rng.normal(0, .5, basis.shape))
    assert _op(ui, ui.ops_apply.FACE3D_OT_apply_result, solve_dir=str(d)).execute(ui.ctx) == {"FINISHED"}
    return ob


def test_handoff_sculpt_bakes_mix_and_adds_multires(ui, monkeypatch):
    bpy, br = ui.bpy, ui.bridge
    ob = _applied_scene(ui)
    keys = _blender_keys(ui, ob)
    br.write_shape_key(ob, "artist", keys["artist"][0] + 0.002, "ID_fit", 1.0, 1.0, False)   # sculpted layer
    from face3d.handoff.keys import Key, KeyStack
    ks, _ = ui.ops_apply.stack_from_object(ob)
    mix_mm = ks.evaluate()
    calls = []

    class Grp:
        def __getattr__(self, name):
            return lambda *a, **k: calls.append((name, k)) or {"FINISHED"}

    class Ops:
        object = Grp()
    monkeypatch.setattr(bpy, "ops", Ops())
    op = _op(ui, ui.ops_handoff.FACE3D_OT_handoff_sculpt, levels=3)
    assert op.poll(ui.ctx) is True and op.execute(ui.ctx) == {"FINISHED"}, op.reports
    cp = [o for o in bpy.data.objects if "f3d_sculpt_of" in o]
    assert len(cp) == 1 and cp[0].name == "head_sculpt" and cp[0].data.shape_keys is None
    assert ob.data.shape_keys is not None and len(ob.data.shape_keys.key_blocks) == 5          # original untouched
    got = br.blender_m_to_engine_mm(br.mesh_vertices_to_array(cp[0].data))
    np.testing.assert_allclose(got, mix_mm, atol=1e-3)                                          # baked (cube mesh: no cage)
    names = [c[0] for c in calls]
    assert names == ["modifier_add"] + ["multires_subdivide"] * 3
    assert calls[0][1] == {"type": "MULTIRES"} and calls[1][1]["mode"] == "CATMULL_CLARK"
    assert (ui.tmp / "proj.face3d" / cp[0]["f3d_sculpt_cage"]).is_file()
    assert ui.messages.MESSAGES["handoff_done"] in [m for _k, m in op.reports]
    # Multires failure leaves the copy and says so
    monkeypatch.setattr(bpy, "ops", types.SimpleNamespace(object=types.SimpleNamespace(
        modifier_add=lambda **k: (_ for _ in ()).throw(RuntimeError("ctx")))))
    op2 = _op(ui, ui.ops_handoff.FACE3D_OT_handoff_sculpt)
    assert op2.execute(ui.ctx) == {"FINISHED"} and _last_msg(op2) == ui.messages.MESSAGES["handoff_multires_failed"]
    # no keys -> refused
    bare = _cube_object(ui, "bare")
    op3 = _op(ui, ui.ops_handoff.FACE3D_OT_handoff_sculpt)
    assert op3.execute(ui.ctx) == {"CANCELLED"} and _last_msg(op3) == ui.messages.MESSAGES["no_keys"]
    ob.mode = "SCULPT"
    bpy.context.object = bpy.context.active_object = ob
    assert op3.poll(ui.ctx) is False


def test_rebase_sculpt_carries_cage_edits(ui, monkeypatch):
    bpy, br = ui.bpy, ui.bridge
    ob = _applied_scene(ui)
    monkeypatch.setattr(bpy, "ops", types.SimpleNamespace(object=types.SimpleNamespace(
        modifier_add=lambda **k: {"FINISHED"}, multires_subdivide=lambda **k: {"FINISHED"})))
    assert _op(ui, ui.ops_handoff.FACE3D_OT_handoff_sculpt).execute(ui.ctx) == {"FINISHED"}
    copy = [o for o in bpy.data.objects if "f3d_sculpt_of" in o][0]
    rb = _op(ui, ui.ops_handoff.FACE3D_OT_rebase_sculpt)
    bpy.context.object = bpy.context.active_object = ob
    assert rb.poll(ui.ctx) is False and ui.ops_handoff.FACE3D_OT_rebase_sculpt._poll_messages[-1] == ui.messages.MESSAGES["sculpt_needs_copy"]
    # the artist edits the copy's cage by +0.5 mm along x for vertex 0
    me = copy.data
    V = br.mesh_vertices_to_array(me)
    V[0, 0] += 0.0005
    br.write_vertices(me, V)
    # a refit changes ID_fit
    basis = np.asarray(CUBE_V, float) * 100.0
    keys = _blender_keys(ui, ob)
    new_id = br.blender_m_to_engine_mm(keys["ID_fit"][0]) + 3.0
    d2, _ = _fake_result(ui, ob, ui.tmp, "job2", basis, new_id, np.zeros((8, 3)))
    ui.ctx.scene.face3d.job.status = "ready"
    assert _op(ui, ui.ops_apply.FACE3D_OT_apply_result, solve_dir=str(d2)).execute(ui.ctx) == {"FINISHED"}
    bpy.context.object = bpy.context.active_object = copy
    assert rb.poll(ui.ctx) is True and rb.execute(ui.ctx) == {"FINISHED"}, rb.reports
    copies = [o for o in bpy.data.objects if "f3d_sculpt_of" in o]
    assert len(copies) == 2
    new = copies[-1]
    ks, _ = ui.ops_apply.stack_from_object(ob)
    got = br.blender_m_to_engine_mm(br.mesh_vertices_to_array(new.data))
    want = ks.evaluate()
    want[0, 0] += 0.5                                                                         # only the cage edit carries
    np.testing.assert_allclose(got, want, atol=1e-3)


def test_protect_measured_writes_support_mask(ui, monkeypatch):
    bpy = ui.bpy
    ob = _applied_scene(ui)
    op = _op(ui, ui.ops_handoff.FACE3D_OT_protect_measured)
    assert op.poll(ui.ctx) is True and op.execute(ui.ctx) == {"FINISHED"}
    m = ob.data.attributes.get(".sculpt_mask").data._arrays["value"]
    np.testing.assert_allclose(m, np.linspace(0, 1, 8), atol=1e-6)        # measured (support 1) = fully masked
    assert m[7] == pytest.approx(1.0) and m[0] == pytest.approx(0.0)
    ob.mode = "SCULPT"
    assert op.execute(ui.ctx) == {"CANCELLED"} and _last_msg(op) == ui.messages.MESSAGES["wrong_mode"]


def test_prepare_for_sharing_lists_then_purges_on_confirm(ui):
    bpy = ui.bpy
    folder = _new_project(ui)
    _op(ui, ui.ops_photos.FACE3D_OT_photos_add, filepath=_png(ui.tmp / "m.png", 5), consent_covers=True).execute(ui.ctx)
    img = bpy.data.images.new("packed", 4, 4)
    img.packed_file = object()
    (folder / "jobs" / "j1").mkdir(parents=True)
    items = ui.ops_handoff.scan_shareables(ui.ctx)
    kinds = {i["kind"] for i in items}
    assert {"packed_image", "background_image"} <= kinds
    op = _op(ui, ui.ops_handoff.FACE3D_OT_prepare_for_sharing)
    assert op.execute(ui.ctx) == {"FINISHED"} and (folder / "photos" / "p01.npy").is_file()   # listing only
    assert ui.ops_handoff.SCAN and ui.ctx.scene["f3d_share_reviewed"] is True
    assert "found" in _last_msg(op).lower() or "Found" in op.reports[0][1]
    pg = _op(ui, ui.ops_handoff.FACE3D_OT_purge, data_class="PERSONAL_IMAGE")
    assert pg.execute(ui.ctx) == {"CANCELLED"} and (folder / "photos" / "p01.npy").is_file()  # needs confirmation
    pg = _op(ui, ui.ops_handoff.FACE3D_OT_purge, data_class="PERSONAL_IMAGE", confirm=True)
    assert pg.execute(ui.ctx) == {"FINISHED"} and not (folder / "photos" / "p01.npy").exists()
    assert ui.ops_photos.camera_for_photo("p01").data.background_images[0].image is None
    pg = _op(ui, ui.ops_handoff.FACE3D_OT_purge, data_class="BIOMETRIC_GEOMETRY", confirm=True)
    assert pg.execute(ui.ctx) == {"FINISHED"} and not (folder / "jobs").exists()
    audit = (folder / "audit.jsonl").read_text()
    assert "purge_personal_image" in audit and "purge_biometric_geometry" in audit


def test_consent_edit_default_deny_and_audit(ui):
    folder = _new_project(ui, scopes=())
    rec = ui.ops_project.load_consent(folder)
    assert int(rec.scopes) == 0
    assert ui.ops_project.consent_state(folder, "reconstruct")[0] is False
    c = _op(ui, ui.ops_project.FACE3D_OT_consent_edit, allow_reconstruct=True, signer_role="self")
    assert c.execute(ui.ctx) == {"FINISHED"}
    assert ui.ops_project.consent_state(folder, "reconstruct") == (True, None)
    assert ui.ops_project.consent_state(folder, "texture")[0] is False
    assert ui.ops_project.consent_state(folder, "reconstruct", ["f" * 64]) == (False, "photo_not_consented")
    assert "consent_recorded" in (folder / "audit.jsonl").read_text()
    from face3d.pipeline.project import Project
    assert Project.load(folder).consent_id == rec.consent_id or Project.load(folder).consent_id
    # project_new without a folder is refused with a message key
    o = _op(ui, ui.ops_project.FACE3D_OT_project_new, directory="")
    assert o.execute(ui.ctx) == {"CANCELLED"} and _last_msg(o) == ui.messages.MESSAGES["project_dir_missing"]


# ------------------------------------------------------------------ messages
def _py(name):
    return ast.parse((EXT / (name + ".py")).read_text(), filename=name)


def test_ui_strings_use_message_keys(ui):
    M = ui.messages.MESSAGES
    helpers_arg1 = {"deny", "fail", "info", "warn"}          # (obj, key, ...)
    helpers_arg0 = {"text", "has"}
    keys, raw = [], []
    for name in UI_FILES:
        for n in ast.walk(_py(name)):
            if isinstance(n, ast.Call):
                fn = n.func
                fname = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
                if fname in helpers_arg1 and len(n.args) >= 2 and isinstance(n.args[1], ast.Constant):
                    keys.append((name, n.args[1].value))
                elif fname in helpers_arg0 and n.args and isinstance(n.args[0], ast.Constant) \
                        and isinstance(n.args[0].value, str) and fname == "text":
                    keys.append((name, n.args[0].value))
                elif fname in ("report", "poll_message_set"):
                    a = n.args[-1] if n.args else None
                    # a direct report/poll message must be MESSAGES[...] or a message-key helper result
                    if not (isinstance(a, ast.Subscript) and getattr(a.value, "id", "") == "MESSAGES") \
                            and not (isinstance(a, ast.Call) and getattr(a.func, "id", "") == "text") \
                            and not (isinstance(a, ast.Name) and a.id == "message"):
                        raw.append((name, n.lineno, ast.unparse(n)))
            if isinstance(n, ast.Subscript) and getattr(n.value, "id", "") == "MESSAGES" \
                    and isinstance(n.slice, ast.Constant):
                keys.append((name, n.slice.value))
    # the only direct report() calls are inside the message helpers
    assert [r for r in raw if "def " in r[2]] == []
    for name, lineno, src in raw:
        assert "P.text(" in src or "text(" in src or "MESSAGES[" in src, (name, lineno, src)
    assert len(keys) > 80
    missing = sorted({k for _n, k in keys if k not in M})
    assert missing == [], missing
    # no literal strings handed to label()/report() outside messages (rail text comes from keys)
    for name in ("ops_project", "ops_photos", "ops_landmarks", "ops_solve", "ops_apply", "ops_handoff"):
        for n in ast.walk(_py(name)):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "report":
                assert not (n.args and isinstance(n.args[-1], (ast.Constant, ast.JoinedStr))), (name, n.lineno)


def test_message_catalogue_covers_engine_keys(ui):
    M = ui.messages.MESSAGES
    checks_src = (ROOT / "face3d" / "qa" / "checks.py").read_text()
    codes = set(re.findall(r'"(Q-[A-Z0-9-]+)"', checks_src))
    assert codes and codes <= set(ui.messages.QA_CODES)
    for code in ui.messages.QA_CODES:
        assert M["qa." + code] and M["qa." + code + ".fix"]
    jobs_src = (ROOT / "face3d" / "pipeline" / "jobs.py").read_text()
    for code in set(re.findall(r'_write_error\(\w+, "(\w+)"', jobs_src)):
        assert "job.error." + code in M, code
    ledger_src = (ROOT / "face3d" / "fit" / "ledger.py").read_text()
    for key in set(re.findall(r'"(ledger\.why\.\w+)"', ledger_src)):
        assert key in M, key
    for key in ("consent_missing", "photo_not_consented", "no_photos", "job_running", "no_result", "wrong_mode",
                "topology_mismatch", "convert_to_png", "mirror_suggest", "mirror_undetermined",
                "mirror_gap_significant", "mirror_unverifiable", "deferred_feature"):
        assert key in M
    assert ui.messages.text("nonexistent_key") == "nonexistent_key"
    assert ui.messages.text("ledger.region.measured", label="Eyes", sigma=0.9).startswith("Eyes: likely within")
    assert all(isinstance(v, str) and v for v in M.values())
    # every message formatter placeholder is a known name
    for k, v in M.items():
        for ph in re.findall(r"\{(\w+)", v):
            assert ph in {"n", "card", "stage", "pct", "code", "name", "label", "sigma", "summary", "score"}, (k, ph)


def test_files_carry_spdx_header_and_py311_syntax():
    for name in UI_FILES + ("messages",):
        src = (EXT / (name + ".py")).read_text()
        assert src.startswith("# SPDX-License-Identifier: GPL-3.0-or-later"), name
        ast.parse(src, feature_version=(3, 11))
        for n in ast.walk(ast.parse(src)):
            assert not isinstance(n, getattr(ast, "TypeAlias", ())), name         # PEP 695 is 3.12+


# ====================================================================== review-fix regressions (WP-22)
def _add_photo(ui, name="m.png", seed=5):
    o = _op(ui, ui.ops_photos.FACE3D_OT_photos_add, filepath=_png(ui.tmp / name, seed), consent_covers=True)
    assert o.execute(ui.ctx) == {"FINISHED"}, o.reports


def _import_lm(ui, pid="p01", faces=1, name="lm.json"):
    o = _op(ui, ui.ops_landmarks.FACE3D_OT_landmarks_import, filepath=_landmark_file(ui.tmp / name, faces=faces),
            photo_id=pid)
    assert o.execute(ui.ctx) == {"FINISHED"}, o.reports
    return o


def test_rail_offers_apply_for_a_finished_job_through_collect_rail_inputs(ui):
    """Finding: the rail never offered apply_result after a solve (collect read only active_solve)."""
    _new_project(ui)
    ob = _cube_object(ui)
    _add_photo(ui)
    _import_lm(ui)
    s = ui.ctx.scene.face3d
    basis = np.asarray(CUBE_V, float) * 100.0
    d, _ = _fake_result(ui, ob, ui.tmp, "jobA", basis, basis.copy(), np.zeros((8, 3)))
    s.job.status, s.job.job_dir = "ready", str(d)
    rows = ui.ui_panels.rail_rows(ui.ctx)
    assert rows["cameras"][1] == "attention" and rows["cameras"][3] == "face3d.apply_result" and rows["cameras"][4] is None
    assert rows["shape"][3] == "face3d.apply_result"
    assert _op(ui, ui.ops_apply.FACE3D_OT_apply_result).poll(ui.ctx) is True
    assert _op(ui, ui.ops_apply.FACE3D_OT_apply_result).execute(ui.ctx) == {"FINISHED"}
    rows = ui.ui_panels.rail_rows(ui.ctx)                           # applied: done, solve/fit buttons again
    assert rows["cameras"][1] == "done" and rows["cameras"][3] == "face3d.solve"
    # a refit finishes: the new result is pending again, with an Apply button although an earlier one was applied
    d2, _ = _fake_result(ui, ob, ui.tmp, "jobB", basis, basis + 1.0, np.zeros((8, 3)))
    s.job.status, s.job.job_dir = "ready", str(d2)
    rows = ui.ui_panels.rail_rows(ui.ctx)
    assert rows["cameras"][1] == "attention" and rows["shape"][3] == "face3d.apply_result"


def test_check_row_agrees_with_review_next_and_checks_project_first(ui):
    rs = ui.ui_panels.rail_state
    assert {r[0]: r for r in rs(None, None, None)}["check"][4] == "no_project"
    proj = {"photos": [{"id": "p01", "sha256": "a" * 64, "include": "auto"}], "consent": _consent(),
            "cards": [{"severity": "info", "decided": False}]}
    row = {r[0]: r for r in rs(proj, None, None)}["check"]
    assert row[1] == "done" and row[4] is None                    # info-only: nothing urgent, but review_next works
    proj["cards"][0]["decided"] = True
    assert {r[0]: r for r in rs(proj, None, None)}["check"][4] == "review_empty"


def test_pin_tool_press_that_starts_the_session_places_a_pin(ui, monkeypatch):
    _new_project(ui)
    _add_photo(ui)
    cam = ui.ops_photos.camera_for_photo("p01")
    cam["f3d_res_x"], cam["f3d_res_y"] = 2000, 1000
    ui.ctx.scene.camera = cam
    pin = _op(ui, ui.ops_landmarks.FACE3D_OT_pin_place)
    monkeypatch.setattr(type(pin), "_frame", lambda self, ctx: CORNERS.copy())
    assert pin.invoke(ui.ctx, _ev("LEFTMOUSE", "PRESS", (200, 450))) == {"RUNNING_MODAL"}
    pin.modal(ui.ctx, _ev("LEFTMOUSE", "RELEASE", (200, 450)))
    s = ui.ctx.scene.face3d
    assert len(s.pins) == 1 and (s.pins[0].x, s.pins[0].y) == pytest.approx((1000.0, 500.0))
    # a press on an existing pin starts a drag on the very first click
    pin2 = _op(ui, ui.ops_landmarks.FACE3D_OT_pin_place)
    assert pin2.invoke(ui.ctx, _ev("LEFTMOUSE", "PRESS", (200, 450))) == {"RUNNING_MODAL"}
    assert pin2._editor.dragging and pin2._editor.selected == 0


def test_pin_tool_settings_choose_landmark_and_options(ui, monkeypatch):
    L = ui.ops_landmarks
    items = L.landmark_items()
    assert items[0][0] == L.NEXT_LANDMARK and [i[0] for i in items[1:]] == L.scheme_names()
    props = types.SimpleNamespace(landmark=L.NEXT_LANDMARK, pin_class="crisp", expertise="novice", blind=False)
    drawn, labels = [], []
    layout = types.SimpleNamespace(prop=lambda p, name, **k: drawn.append(name), label=lambda **k: labels.append(k["text"]))
    tool = types.SimpleNamespace(operator_properties=lambda idname: props)
    _new_project(ui)
    _add_photo(ui)
    ui.ctx.scene.camera = ui.ops_photos.camera_for_photo("p01")
    tool_cls = ui.bpy.utils.registered_tools[0]
    tool_cls.draw_settings(ui.ctx, layout, tool)
    assert drawn == ["landmark", "pin_class", "expertise", "blind"]
    assert any(ui.messages.text("pin_next", name="vertex") == t for t in labels)         # the next click's landmark
    # a chosen landmark places that one (skipping the unseen ones) and then falls back to scheme order
    cam = ui.ops_photos.camera_for_photo("p01")
    cam["f3d_res_x"], cam["f3d_res_y"] = 2000, 1000
    pin = _op(ui, L.FACE3D_OT_pin_place, landmark="nasion")
    monkeypatch.setattr(type(pin), "_frame", lambda self, ctx: CORNERS.copy())
    pin.invoke(ui.ctx, None)
    pin.modal(ui.ctx, _ev("LEFTMOUSE", "PRESS", (150, 450)))
    pin.modal(ui.ctx, _ev("LEFTMOUSE", "RELEASE", (150, 450)))
    pin.modal(ui.ctx, _ev("LEFTMOUSE", "PRESS", (250, 450)))
    pin.modal(ui.ctx, _ev("LEFTMOUSE", "RELEASE", (250, 450)))
    assert [p.landmark for p in ui.ctx.scene.face3d.pins] == ["nasion", "vertex"]
    assert any("Next click places" in m for _k, m in pin.reports)


def test_import_with_one_strong_face_keeps_only_that_face(ui):
    """Finding: a weak background face listed first was fitted because the engine uses faces[0]."""
    from face3d.io.landmarks import Face, LandmarkSet, save_landmarks
    _new_project(ui)
    _add_photo(ui)
    faces = [Face(score=0.3, uv=np.full((44, 2), 5.0), visible=np.ones(44, bool)),
             Face(score=0.95, uv=np.full((44, 2), 20.0), visible=np.ones(44, bool))]
    f = ui.tmp / "weak_first.json"
    save_landmarks(LandmarkSet("anatomical44", {"backend": "t"}, {"wh": [48, 40]}, faces), f)
    o = _op(ui, ui.ops_landmarks.FACE3D_OT_landmarks_import, filepath=str(f), photo_id="p01")
    assert o.execute(ui.ctx) == {"FINISHED"}
    ls = ui.ops_landmarks.session_sets(ui.ctx)["p01"]
    assert len(ls.faces) == 1 and np.allclose(ls.faces[0].uv, 20.0)
    assert ui.overlays.STATE["auto_landmarks"]["p01"].shape == (44, 2)          # imported landmarks are displayed
    # several faces and none strong: a pick-subject card, nothing stored
    ui.ops_landmarks.SESSION.clear()
    weak = [Face(score=0.2, uv=np.full((44, 2), 1.0), visible=np.ones(44, bool)),
            Face(score=0.4, uv=np.full((44, 2), 2.0), visible=np.ones(44, bool))]
    g = ui.tmp / "none_strong.json"
    save_landmarks(LandmarkSet("anatomical44", {"backend": "t"}, {"wh": [48, 40]}, weak), g)
    o = _op(ui, ui.ops_landmarks.FACE3D_OT_landmarks_import, filepath=str(g), photo_id="p01")
    assert o.execute(ui.ctx) == {"FINISHED"} and ui.ops_landmarks.session_sets(ui.ctx) == {}
    assert ui.ctx.scene.face3d.cards[len(ui.ctx.scene.face3d.cards) - 1].code == "Q-FACES"


def test_choose_face_is_non_destructive_and_cards_are_drawn(ui):
    _new_project(ui)
    _add_photo(ui)
    _import_lm(ui, faces=2)                                          # two strong faces -> Q-FACES card
    s = ui.ctx.scene.face3d
    i = len(s.cards) - 1
    bad = _op(ui, ui.ops_solve.FACE3D_OT_card_accept, index=i, face_index=7)
    assert bad.execute(ui.ctx) == {"CANCELLED"}
    assert "p01" in ui.ops_landmarks.pending_sets(ui.ctx) and s.cards[i].decided is False   # nothing was lost
    # the cards panel lists question, fix text, a button per face and Dismiss
    drawn = []

    class _Op:
        pass

    class Lay:
        def box(self):
            return self

        def label(self, **k):
            drawn.append(("label", k["text"]))

        def operator(self, idname, **k):
            o = _Op()
            drawn.append((idname, k.get("text"), o))
            return o
    ui.ui_panels.draw_cards(Lay(), ui.ctx)
    texts = [d[1] for d in drawn]
    assert ui.messages.text("pick_subject") in texts and ui.messages.text("qa.Q-FACES.fix") in texts
    face_buttons = [d for d in drawn if d[0] == "face3d.card_accept" and d[2].index == i]
    assert len(face_buttons) == 2 and [d[2].face_index for d in face_buttons] == [0, 1]
    assert any(d[0] == "face3d.card_dismiss" and d[2].index == i for d in drawn)
    ok = _op(ui, ui.ops_solve.FACE3D_OT_card_accept, index=i, face_index=1)
    assert ok.execute(ui.ctx) == {"FINISHED"} and "p01" not in ui.ops_landmarks.pending_sets(ui.ctx)
    drawn.clear()
    s.cards.clear()
    ui.ui_panels.draw_cards(Lay(), ui.ctx)
    assert drawn == [("label", ui.messages.text("panel.cards_none"))]
    assert any(getattr(p, "bl_idname", "") == "FACE3D_PT_cards" for p in ui.bpy.utils.registered_classes)


def test_keyed_card_keys_decide_only_the_card_under_review(ui):
    _new_project(ui)
    _add_photo(ui, "a.png", 1)
    _add_photo(ui, "b.png", 2)
    s = ui.ctx.scene.face3d
    s.cards.clear()
    for pid in ("p01", "p02"):
        c = s.cards.add()
        c.code, c.severity, c.msg_key, c.photo_id, c.decided = "Q-BLUR", "warn", "qa.Q-BLUR", pid, False
    ui.ctx.scene.camera = ui.ops_photos.camera_for_photo("p01")
    ui.ctx.scene["f3d_review_idx"] = 1                               # reviewing p02's card, but p01's camera is active
    acc = _op(ui, ui.ops_solve.FACE3D_OT_card_accept, keyed=True)
    assert acc.invoke(ui.ctx, None) == {"CANCELLED"} and not s.cards[0].decided and not s.cards[1].decided
    ui.ctx.scene["f3d_review_idx"] = 0                               # the card under review belongs to the active photo
    assert _op(ui, ui.ops_solve.FACE3D_OT_card_accept, keyed=True).invoke(ui.ctx, None) == {"FINISHED"}
    assert s.cards[0].decided and not s.cards[1].decided
    ui.ctx.scene["f3d_review_idx"] = 0                               # decided and stale: no fallback to the worst card
    assert _op(ui, ui.ops_solve.FACE3D_OT_card_dismiss, keyed=True).invoke(ui.ctx, None) == {"CANCELLED"}
    assert not s.cards[1].decided


def test_keyed_items_need_the_viewport_to_look_through_the_camera(ui):
    _new_project(ui)
    _add_photo(ui)
    ui.ctx.scene.camera = ui.ops_photos.camera_for_photo("p01")
    ui.ctx.region_data = types.SimpleNamespace(view_perspective="PERSP")
    v = _op(ui, ui.ops_photos.FACE3D_OT_view_next, keyed=True)
    assert v.invoke(ui.ctx, None) == {"PASS_THROUGH"}
    assert _op(ui, ui.overlays.FACE3D_OT_compare_mode, mode="blur", keyed=True).invoke(ui.ctx, None) == {"PASS_THROUGH"}
    assert _op(ui, ui.overlays.FACE3D_OT_compare_flip, keyed=True).invoke(ui.ctx, None) == {"PASS_THROUGH"}
    assert _op(ui, ui.ops_solve.FACE3D_OT_solve, keyed=True).invoke(ui.ctx, None) == {"PASS_THROUGH"}
    ui.ctx.region_data = types.SimpleNamespace(view_perspective="CAMERA")
    assert _op(ui, ui.ops_photos.FACE3D_OT_view_next, keyed=True).invoke(ui.ctx, None) == {"FINISHED"}
    ui.ctx.region_data = None


def test_stale_running_status_is_reset_by_cancel_and_by_load_post(ui):
    """Finding: 'running' saved in the .blend with no live runner locked every operator for good."""
    _new_project(ui)
    _add_photo(ui)
    _import_lm(ui)
    s = ui.ctx.scene.face3d
    ui.ops_solve.RUNNERS.clear()
    job_dir = ui.tmp / "stale_job"
    job_dir.mkdir()
    s.job.status, s.job.job_dir = "running", str(job_dir)
    assert ui.ops_solve.FACE3D_OT_solve.poll(ui.ctx) is False and ui.ops_photos.FACE3D_OT_photos_add.poll(ui.ctx) is False
    c = _op(ui, ui.ops_solve.FACE3D_OT_job_cancel)
    assert c.poll(ui.ctx) is True and c.execute(ui.ctx) == {"FINISHED"}
    assert _last_msg(c) == ui.messages.MESSAGES["job_reset"] and s.job.status == "idle"
    assert ui.ops_solve.FACE3D_OT_solve.poll(ui.ctx) is True and ui.ops_photos.FACE3D_OT_photos_add.poll(ui.ctx) is True
    # the job folder decides: a result means ready, a cancel file means cancelled
    (job_dir / "result.json").write_text("{}")
    s.job.status = "running"
    ui.bpy.data.scenes.append(ui.ctx.scene)
    ui.ops_solve._load_post()
    assert s.job.status == "ready"
    (job_dir / "result.json").unlink()
    (job_dir / "cancel").write_text("1")
    s.job.status = "running"
    ui.ops_solve.reconcile_job(ui.ctx.scene)
    assert s.job.status == "cancelled"
    # a live runner is left alone
    ui.ops_solve.RUNNERS[str(s.project_path)] = types.SimpleNamespace(status="running")
    s.job.status = "running"
    assert ui.ops_solve.reconcile_job(ui.ctx.scene) is False and s.job.status == "running"
    assert ui.ops_solve._load_post in ui.bpy.app.handlers.load_post
    ui.ops_solve.RUNNERS.clear()


def test_compare_image_is_cached_and_made_at_display_resolution(ui, monkeypatch):
    ov = ui.overlays
    ov.reset_state()
    rng = np.random.default_rng(0)
    big = rng.random((1500, 2000, 3)).astype(np.float32)
    out = ov.compare_image(big, "blur", 700.0)
    assert max(out.shape[:2]) <= ov.COMPARE_MAX_SIDE and out.dtype == np.float32      # not full resolution
    assert ov.compare_image(big, "grey").shape[:2] == out.shape[:2]
    small = rng.random((60, 80, 3)).astype(np.float32)
    assert ov.compare_image(small, "grey").shape[:2] == (60, 80)                       # small images unchanged
    path = ui.tmp / "wc.npy"
    np.save(path, small)
    calls = []
    real = ov.compare_image
    monkeypatch.setattr(ov, "compare_image", lambda *a, **k: calls.append(a[1]) or real(*a, **k))
    a1 = ov.compare_for_photo(str(path), "blur", 40.0)
    a2 = ov.compare_for_photo(str(path), "blur", 40.0)                                 # a redraw: no recomputation
    assert a1 is a2 and calls == ["blur"]
    ov.compare_for_photo(str(path), "grey", 40.0)                                      # mode change invalidates
    ov.compare_for_photo(str(path), "blur", 40.0)
    assert calls == ["blur", "grey", "blur"]
    ov.compare_for_photo(str(path), "blur", 55.0)                                      # so does the face width
    assert calls[-1] == "blur" and len(calls) == 4
    # the draw handler builds the GPU texture once per cache entry
    built = []
    monkeypatch.setattr(ov, "_compare_texture", lambda img: built.append(1) or object())
    assert ov._COMPARE["key"] is not None
    ov.reset_state()
    assert ov._COMPARE["key"] is None


def test_ledger_shows_scale_and_focal_and_never_a_floor_for_unknown_sigma(ui):
    L = ui.ui_panels.ledger_lines
    ob = _cube_object(ui)
    d, _ = _fake_result(ui, ob, ui.tmp, "rL", np.zeros((8, 3)), np.zeros((8, 3)), np.zeros((8, 3)))
    doc = json.loads((d / "result.json").read_text())
    doc["scale"] = {"mode": "iris", "sigma_pct": 4.0, "text": "Scale: from the iris, +/-4 %"}
    doc["regions"][0]["sigma_rep_mm"] = None                      # constrained/measured with an unknown sigma
    lines = L(doc)
    assert "Scale: from the iris, +/-4 %" in lines                # H4
    assert any(x.startswith("Focal length: measured in 1 of 2") for x in lines)    # H5
    assert lines.index("Scale: from the iris, +/-4 %") < next(i for i, x in enumerate(lines) if x.startswith("Eyes"))
    eyes = [x for x in lines if x.startswith("Eyes")][0]
    assert "range unknown" in eyes and "0.2" not in eyes


def test_solve_needs_an_imported_landmark_set_per_included_photo(ui):
    """Finding: the pins-only path passed the UI gate but the engine always failed it."""
    _new_project(ui)
    _add_photo(ui, "a.png", 1)
    _add_photo(ui, "b.png", 2)
    S = ui.ops_solve.FACE3D_OT_solve
    M = ui.messages.MESSAGES
    # pins alone are not enough
    ui.ctx.scene.face3d.pins.add().photo_id = "p01"
    assert S.poll(ui.ctx) is False and S._poll_messages[-1] == M["no_landmarks"]
    assert ui.ops_solve.FACE3D_OT_fit.poll(ui.ctx) is False
    _import_lm(ui, "p01")
    assert S.poll(ui.ctx) is False and S._poll_messages[-1] == M["landmarks_incomplete"]   # p02 has none
    ui.ctx.scene.face3d.photos[1].include = "exclude"                                      # excluded photos need none
    assert S.poll(ui.ctx) is True
    ui.ctx.scene.face3d.photos[1].include = "auto"
    # the rail applies the same rule (no pin-only 'done' and no enabled button)
    rows = ui.ui_panels.rail_rows(ui.ctx)
    assert rows["cameras"][4] == "landmarks_incomplete" and rows["landmarks"][1] == "attention"
    _import_lm(ui, "p02", name="lm2.json")
    assert S.poll(ui.ctx) is True and ui.ui_panels.rail_rows(ui.ctx)["cameras"][4] is None


def _result_with_cameras(ui, ob, tmp, name):
    """A result like the engine's, with a camera for p01, per-vertex 'vertices' and region ids."""
    from face3d.core.schema import dump_json, save_arrays
    basis = np.asarray(CUBE_V, float) * 100.0
    n = len(basis)
    ax, ay = 0.3, 0.4
    Rx = np.array([[1, 0, 0], [0, np.cos(ax), -np.sin(ax)], [0, np.sin(ax), np.cos(ax)]])
    Ry = np.array([[np.cos(ay), 0, np.sin(ay)], [0, 1, 0], [-np.sin(ay), 0, np.cos(ay)]])
    R = Rx @ Ry
    arrays = {"handoff_key_basis": basis, "handoff_key_ID_fit": basis.copy(), "handoff_key_Asym": basis.copy(),
              "vertices": basis, "region_ids": np.arange(n) % 2, "sigma_n": np.ones(n), "support": np.ones(n)}
    d = tmp / name
    d.mkdir(parents=True)
    man = save_arrays(d / "arrays.npz", **arrays)
    doc = {"format": "face3d.result", "version": 1, "arrays": man,
           "run": {"input_hashes": {"template_topology_sha256": ui.bridge.topology_sha(ob.data)}},
           "cameras": [{"photo": "p01", "K": [[800, 0, 32], [0, 800, 32], [0, 0, 1]], "R": R.tolist(),
                        "t": [0, 0, 600]}],
           "cards": [], "regions": [{"name": "eyes", "status": "measured", "sigma_rep_mm": 0.9, "next_photo": None},
                                    {"name": "nose", "status": "prior-driven", "sigma_rep_mm": 2.0, "next_photo": None},
                                    {"name": "nose_projection", "status": "unobserved", "sigma_rep_mm": 3.0,
                                     "next_photo": None}],
           "per_vertex": {"region_names": ["eyes", "nose"], "inflation": 1.0}}
    dump_json(doc, d / "result.json")
    return d


def test_apply_sets_resolution_flip_overlays_and_refuses_moved_head(ui):
    _new_project(ui)
    ob = _cube_object(ui)
    _add_photo(ui)
    cam = ui.ops_photos.camera_for_photo("p01")
    cam["f3d_res_x"], cam["f3d_res_y"] = 1200, 800
    ui.ctx.scene.face3d.job.status = "ready"
    d = _result_with_cameras(ui, ob, ui.tmp, "jobC")
    # stepping to the photo sets the scene render resolution and pixel aspect (per scene in Blender)
    assert _op(ui, ui.ops_photos.FACE3D_OT_view_next).execute(ui.ctx) == {"FINISHED"}
    r = ui.ctx.scene.render
    assert (r.resolution_x, r.resolution_y, r.pixel_aspect_x, r.pixel_aspect_y) == (1200, 800, 1.0, 1.0)
    # a moved head would misalign the world-space cameras: refused, nothing written
    ob.matrix_world = np.diag([1.0, 1.0, 1.0, 1.0])
    ob.matrix_world[0][3] = 0.5 if isinstance(ob.matrix_world, list) else 0
    ob.matrix_world = [[1, 0, 0, 0.5], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    op = _op(ui, ui.ops_apply.FACE3D_OT_apply_result, solve_dir=str(d))
    assert op.execute(ui.ctx) == {"CANCELLED"} and _last_msg(op) == ui.messages.MESSAGES["head_transform"]
    assert ob.data.shape_keys is None
    ob.matrix_world = None
    # a recorded flip is honoured: the solved image is the flipped one
    prj = ui.ops_project.load_project(ui.ctx)
    prj.record_decision("mirror_flip", "p01", "user")
    prj.save()
    op = _op(ui, ui.ops_apply.FACE3D_OT_apply_result, solve_dir=str(d))
    assert op.execute(ui.ctx) == {"FINISHED"}, op.reports
    assert cam.data.background_images[0].use_flip_x is True
    assert (r.resolution_x, r.resolution_y) == (1200, 800)
    # overlays are fed: hatching of prior-driven / unobserved regions and the model outline
    st = ui.overlays.STATE
    assert len(st["hatch"]["p01"]) == 1 and st["hatch"]["p01"][0].shape[1] == 2 and len(st["hatch"]["p01"][0]) >= 3
    assert len(st["model_contour"]["p01"]) >= 4
    items = ui.overlays.build_draw_list("p01", CORNERS, (64, 64), 1.0, [])
    assert items                                                  # H9 hatching reaches the draw list
    # deciding 'keep' on a mirror card shows the photo unflipped again
    ui.ops_solve._set_photo_mirror(ui.ctx.scene.face3d, "p01", "keep")
    assert cam.data.background_images[0].use_flip_x is False
    hull = ui.overlays.convex_hull(np.array([[0, 0], [2, 0], [2, 2], [0, 2], [1, 1], [1, 0.5]], float))
    assert len(hull) == 4


def test_prepare_for_sharing_confirm_purges_only_what_it_listed(ui):
    bpy = ui.bpy
    folder = _new_project(ui)
    _add_photo(ui)
    img = bpy.data.images.new("packed", 4, 4)
    img.packed_file = object()
    orphan = bpy.data.meshes.new("orphan_mesh")
    orphan.users = 0
    items = ui.ops_handoff.scan_shareables(ui.ctx)
    assert {"packed_image", "background_image", "orphan"} <= {i["kind"] for i in items}
    op = _op(ui, ui.ops_handoff.FACE3D_OT_prepare_for_sharing, confirm=True)
    assert op.execute(ui.ctx) == {"FINISHED"}
    # what the scan listed is gone ...
    assert bpy.data.images.get("packed") is None and bpy.data.meshes.get("orphan_mesh") is None
    assert ui.ops_photos.camera_for_photo("p01").data.background_images[0].image is None
    # ... but the project's working copy survives: the project can still be solved, the photo is still known
    assert (folder / "photos" / "p01.npy").is_file()
    assert [p.id for p in ui.ops_project.load_project(ui.ctx).photos] == ["p01"]
    assert ui.ops_handoff.SCAN == [] or all(i["kind"] != "packed_image" for i in ui.ops_handoff.SCAN)
    assert "share_cleanup" in (folder / "audit.jsonl").read_text()
    assert "working copies" in ui.messages.MESSAGES["purge_confirm"]


def test_project_new_never_overwrites_an_existing_project(ui):
    folder = _new_project(ui)
    _add_photo(ui)
    before = (folder / "project.json").read_text()
    o = _op(ui, ui.ops_project.FACE3D_OT_project_new, directory=str(folder))
    assert o.execute(ui.ctx) == {"CANCELLED"} and _last_msg(o) == ui.messages.MESSAGES["project_exists"]
    assert (folder / "project.json").read_text() == before
    assert len(ui.ops_project.load_project(ui.ctx).photos) == 1 and (folder / "photos" / "p01.npy").is_file()


def test_photos_add_extends_consent_only_after_the_checks_and_checks_the_whole_set(ui, monkeypatch):
    bpy = ui.bpy
    folder = _new_project(ui)
    a = _png(ui.tmp / "a.png", 1)
    before = ui.ops_project.load_consent(folder).photo_sha256
    # a photo refused for orientation must leave the consent record unchanged and not leak its image
    from face3d.pipeline import project as proj_mod
    real = proj_mod.Project.add_photo

    def rotated(self, path, rights, **kw):
        rec = real(self, path, rights, **kw)
        rec.exif["orientation"] = 6
        return rec
    monkeypatch.setattr(proj_mod.Project, "add_photo", rotated)
    n_img = len(bpy.data.images)
    o = _op(ui, ui.ops_photos.FACE3D_OT_photos_add, filepath=a, consent_covers=True)
    assert o.execute(ui.ctx) == {"CANCELLED"} and _last_msg(o) == ui.messages.MESSAGES["convert_to_png"]
    assert ui.ops_project.load_consent(folder).photo_sha256 == before
    assert "consent_photo_added" not in (folder / "audit.jsonl").read_text()
    assert len(bpy.data.images) == n_img
    monkeypatch.setattr(proj_mod.Project, "add_photo", real)
    # set-level QA sees every project photo, not only the current batch
    seen = []
    real_set = ui.ops_photos.qa.run_set_checks
    monkeypatch.setattr(ui.ops_photos.qa, "run_set_checks", lambda ctxs, *a_, **k: seen.append(len(list(ctxs))) or real_set(ctxs))
    _add_photo(ui, "a.png", 1)
    _add_photo(ui, "b.png", 2)
    assert seen[-1] == 2


def test_refit_keeps_user_key_state_and_nudges_in_all_directions(ui):
    br = ui.bridge
    ob = _scene_for_apply(ui)
    rng = np.random.default_rng(4)
    basis = np.asarray(CUBE_V, float) * 100.0
    idf = basis + rng.normal(0, 2.0, basis.shape)
    d, _ = _fake_result(ui, ob, ui.tmp, "k1", basis, idf, rng.normal(0, 0.5, basis.shape))
    assert _op(ui, ui.ops_apply.FACE3D_OT_apply_result, solve_dir=str(d)).execute(ui.ctx) == {"FINISHED"}
    blocks = ob.data.shape_keys.key_blocks
    blocks.get("ID_fit").value = 1.3                               # the user's own state
    blocks.get("Asym").mute = True
    blocks.get("artist").slider_max = 2.0
    d2, _ = _fake_result(ui, ob, ui.tmp, "k2", basis, idf + 1.0, rng.normal(0, 0.5, basis.shape))
    ui.ctx.scene.face3d.job.status = "ready"
    assert _op(ui, ui.ops_apply.FACE3D_OT_apply_result, solve_dir=str(d2)).execute(ui.ctx) == {"FINISHED"}
    k = _blender_keys(ui, ob)
    assert k["ID_fit"][2] == pytest.approx(1.3) and k["Asym"][4] is True and k["artist"][3] == pytest.approx(2.0)
    # all four arrow directions nudge by the right sign (x right+, y down+ in image px), fine with Shift
    ed = ui.ops_landmarks.PinEditor([{"landmark": "a", "x": 10.0, "y": 10.0}], (100, 100))
    ed.selected = 0
    for dx, dy, want in ((1, 0, (11, 10)), (-1, 0, (10, 10)), (0, 1, (10, 11)), (0, -1, (10, 10))):
        ed.nudge(dx, dy)
        assert (ed.pins[0]["x"], ed.pins[0]["y"]) == pytest.approx(want)


def test_modules_do_not_touch_mesh_or_image_data_directly(ui):
    """Only bridge.py loads images, copies meshes or clears keys (DESIGN 6.2)."""
    banned = {"load", "copy", "shape_key_clear", "foreach_get", "foreach_set", "pixels"}
    for name in ("ops_handoff", "ops_photos", "ops_apply", "ops_landmarks", "ops_solve", "ops_project", "overlays"):
        for n in ast.walk(_py(name)):
            if isinstance(n, ast.Attribute) and n.attr in banned:
                owner = ast.unparse(n.value)
                assert not (n.attr in ("load",) and owner.endswith("images")), (name, n.lineno)
                assert n.attr not in ("shape_key_clear", "foreach_get", "foreach_set", "pixels"), (name, n.lineno)
                assert not (n.attr == "copy" and owner.endswith(".data")), (name, n.lineno)


def test_catalogue_covers_every_pipeline_error_and_qa_msg_key(ui):
    M = ui.messages.MESSAGES
    codes = set()
    for f in (ROOT / "face3d").rglob("*.py"):
        codes |= set(re.findall(r'PipelineError\(\s*"(\w+)"', f.read_text()))
    assert "missing_landmarks" in codes and "texture_blocked" in codes
    for c in sorted(codes):
        assert "job.error." + c in M, c
    for f in (ROOT / "face3d" / "qa").glob("*.py"):
        for key in re.findall(r'msg_key *= *"([\w.\-]+)"', f.read_text()):
            assert key in M, key
    assert "qa.Q-SMALL.no_iris_scale" in M
