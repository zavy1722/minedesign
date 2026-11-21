"""WP-21: Blender extension core, tested with the bpy stub (DESIGN 6.8).

No Blender here. The stub directory is put on sys.path only inside the
``bx`` fixture and the stub modules are purged afterwards.
"""
from __future__ import annotations

import ast
import importlib
import importlib.machinery
import json
import subprocess
import sys
import time
import tomllib
import types
import zipfile
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
STUB = ROOT / "tests" / "blender_stub"
EXT = ROOT / "blender_ext" / "face3d_likeness"
_PURGE = ("bpy", "mathutils", "gpu", "gpu_extras", "blf", "blender_ext")


def _purge():
    for name in list(sys.modules):
        if name.split(".")[0] in _PURGE:
            del sys.modules[name]


@pytest.fixture
def bx(monkeypatch):
    _purge()
    monkeypatch.syspath_prepend(str(ROOT))
    monkeypatch.syspath_prepend(str(STUB))
    import bpy
    bpy._reset()
    ns = types.SimpleNamespace(bpy=bpy)
    pkg = "blender_ext.face3d_likeness"
    ns.pkg = importlib.import_module(pkg)
    for m in ("bridge", "jobs", "props", "compat"):
        setattr(ns, m, importlib.import_module(pkg + "." + m))
    yield ns
    _purge()


def _cube_obj(bpy, n_extra=0):
    me = bpy.data.meshes.new("m")
    V = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]
    F = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me.from_pydata(V, [], F)
    ob = bpy.data.objects.new("o", me)
    return ob, np.array(V, float), np.array(F)


# ------------------------------------------------------------------ manifest
def test_manifest_lint():
    with open(EXT / "blender_manifest.toml", "rb") as fh:
        m = tomllib.load(fh)
    assert m["schema_version"] == "1.0.0"
    assert m["id"] == "face3d_likeness"
    assert m["name"] == "Face3D Likeness"
    assert len(m["tagline"]) <= 64
    assert m["license"] == ["SPDX:GPL-3.0-or-later"]
    assert "network" not in m["permissions"] and "files" in m["permissions"]
    assert m["blender_version_min"] == "4.5.0"
    assert m["type"] == "add-on"
    assert "paths_exclude_pattern" in m["build"]
    for p in EXT.glob("*.py"):
        assert p.read_text().splitlines()[0] == "# SPDX-License-Identifier: GPL-3.0-or-later", p
    assert (EXT / "NOTICE").read_text().lower().count("wheels") >= 1


# ------------------------------------------------------------------ register
def test_register_unregister_with_stub(bx, monkeypatch):
    bpy, pkg = bx.bpy, bx.pkg
    monkeypatch.setattr(pkg, "_MODULES", ("ops_project",))   # WP-22 modules now exist: test only the fake one
    calls = []
    name = pkg.__name__ + ".ops_project"
    fake = types.ModuleType(name)
    fake.__spec__ = importlib.machinery.ModuleSpec(name, None)
    fake.register = lambda: calls.append("r")
    fake.unregister = lambda: calls.append("u")
    monkeypatch.setitem(sys.modules, name, fake)

    pkg.register()
    pkg.register()                       # idempotent
    assert calls == ["r"]
    assert pkg.COMPAT["blender"] == (4, 5, 0)
    assert len(bpy.utils.registered_classes) == len(bx.props.CLASSES)
    s = bpy.context.scene.face3d
    assert s.job.status == "idle" and s.rail_stage == "consent"
    pin = s.pins.add()
    pin.photo_id = "p1"
    assert len(s.pins) == 1 and s.photos is not None
    ph = s.photos.add()
    assert ph.include == "auto" and ph.mirror_decision == "none"

    pkg.unregister()
    pkg.unregister()                     # idempotent
    assert calls == ["r", "u"]
    assert bpy.utils.registered_classes == []
    assert not hasattr(bpy.types.Scene, "face3d")
    pkg.register()                       # can come back
    assert len(bpy.utils.registered_classes) == len(bx.props.CLASSES)
    pkg.unregister()


def test_compat_probe_fast_and_keys(bx):
    t0 = time.perf_counter()
    d = bx.compat.probe()
    assert time.perf_counter() - t0 < 0.1
    assert set(d) == {"blender", "python_tag", "numpy", "online_access", "platform", "background"}
    assert d["python_tag"].startswith("cp3") and d["online_access"] is False
    for opt in ("mediapipe", "torch", "onnxruntime"):
        assert opt not in sys.modules


def test_engine_root(bx):
    root = Path(bx.pkg.engine_root())
    assert (root / "face3d").is_dir()
    before = list(sys.path)
    bx.pkg.ensure_engine_on_path()
    bx.pkg.ensure_engine_on_path()
    assert str(root) in sys.path
    assert sys.path.count(str(root)) == max(1, before.count(str(root)))


# ------------------------------------------------------------------ bridge
def test_bridge_dtype_and_frame(bx):
    bpy, br = bx.bpy, bx.bridge
    ob, V, F = _cube_obj(bpy)
    me = ob.data
    out = br.mesh_vertices_to_array(me)
    assert out.dtype == np.float64 and out.shape == (8, 3) and np.array_equal(out, V)
    W = np.random.default_rng(0).normal(size=(8, 3))
    br.write_vertices(me, W)
    assert me.update_count >= 1
    back = br.mesh_vertices_to_array(me)
    assert np.array_equal(back, W.astype(np.float32).astype(np.float64))
    # stub refuses non-contiguous / wrong dtype buffers, so the bridge must comply
    P = np.random.default_rng(1).normal(size=(5, 3)) * 100.0
    B = br.engine_mm_to_blender_m(P)
    assert np.allclose(B, 0.001 * np.stack([P[:, 0], -P[:, 2], P[:, 1]], 1), rtol=0, atol=1e-15)
    assert np.allclose(br.blender_m_to_engine_mm(B), P, rtol=1e-12, atol=1e-12)
    H = np.c_[P, np.ones(5)]
    assert np.allclose((br.ENGINE_TO_BLENDER @ H.T).T[:, :3], B)
    # image rows flipped (Blender bottom-up -> engine top-down)
    img = bpy.data.images.new("i", 3, 2)
    px = np.arange(2 * 3 * 4, dtype=np.float32)
    img.pixels.foreach_set(px)
    arr = br.image_to_array(img)
    assert arr.shape == (2, 3, 4) and arr.dtype == np.float32
    assert np.array_equal(arr[0], px.reshape(2, 3, 4)[1])
    assert np.array_equal(arr[1], px.reshape(2, 3, 4)[0])


def test_topology_sha_matches_engine_and_attributes(bx):
    from face3d.model.template_kit import topology_sha256
    bpy, br = bx.bpy, bx.bridge
    ob, V, F = _cube_obj(bpy)
    assert br.topology_sha(ob.data) == topology_sha256(8, F)
    me2 = bpy.data.meshes.new("mix")
    me2.from_pydata(V, [], [(0, 1, 2), (0, 2, 3, 4)])
    assert br.topology_sha(me2) == topology_sha256(8, [(0, 1, 2), (0, 2, 3, 4)])
    br.set_attribute(ob.data, "f3d_sigma_mm", np.arange(8.0))
    a = ob.data.attributes.get("f3d_sigma_mm")
    buf = np.empty(8, np.float32)
    a.data.foreach_get("value", buf)
    assert np.array_equal(buf, np.arange(8, dtype=np.float32))


def test_shape_key_write_semantics(bx):
    bpy, br = bx.bpy, bx.bridge
    ob, V, F = _cube_obj(bpy)
    kb = br.write_shape_key(ob, "f3d_a", V + 1.0, slider_max=2.5, value=2.0, mute=True)
    blocks = ob.data.shape_keys.key_blocks
    assert [k.name for k in blocks] == ["Basis", "f3d_a"]
    assert kb.relative_key is blocks["Basis"]
    assert kb.slider_max == 2.5 and kb.value == 2.0 and kb.mute is True
    br.write_shape_key(ob, "f3d_b", V - 1.0, relative_to="f3d_a")
    keys = br.read_shape_keys(ob)
    assert keys["f3d_b"][1] == "f3d_a" and keys["f3d_a"][3] == 2.5
    assert np.array_equal(keys["f3d_a"][0], V + 1.0)
    assert np.array_equal(keys["Basis"][0], V)   # from_mix=False: Basis not polluted
    with pytest.raises(KeyError):
        br.write_shape_key(ob, "x", V, relative_to="nope")


def test_mode_guard_refuses_edit_and_sculpt(bx):
    bpy, br = bx.bpy, bx.bridge
    ob, _, _ = _cube_obj(bpy)
    bpy.context.object = ob
    for mode in ("EDIT", "SCULPT"):
        ob.mode = mode
        with pytest.raises(br.BridgeRefusal):
            with br.mode_guard(ob):
                pytest.fail("body must not run")
        assert ob.mode == mode
    ob.mode = "OBJECT"
    with br.mode_guard(ob):
        pass
    ob.mode = "POSE"
    with br.mode_guard(ob):
        assert ob.mode == "OBJECT"
    assert ob.mode == "POSE"


def test_apply_camera_uses_to_blender_camera(bx):
    from face3d.geometry.camera import Camera, to_blender_camera
    bpy, br = bx.bpy, bx.bridge
    cam = Camera(f=3200.0, cx=1500.0 + 37.0, cy=2000.0 - 52.0, width=3000, height=4000,
                 t=np.array([0.0, 0.0, 600.0]))
    d = to_blender_camera(cam)
    obj = bpy.data.objects.new("cam", bpy.data.cameras.new("c"))
    br.apply_camera(obj, d)
    c = obj.data
    assert c.shift_x == d["shift_x"] and c.shift_y == d["shift_y"]
    assert abs(c.shift_x) > 0 and abs(c.shift_y) > 0
    assert c.sensor_fit == "HORIZONTAL" and c.lens == d["lens"] and c.sensor_width == 36.0
    assert obj["f3d_res_x"] == 3000 and obj["f3d_res_y"] == 4000
    M = np.asarray(obj.matrix_world)
    assert np.allclose(M[:3, 3], br.engine_mm_to_blender_m(d["matrix_world"][:3, 3]))
    assert np.allclose(M[:3, :3] @ M[:3, :3].T, np.eye(3))   # unit scale
    # full orientation: R_x(90) @ R_engine, translation 0.001 * R_x(90) @ t
    Rx = np.array([[1.0, 0, 0], [0, 0, -1.0], [0, 1.0, 0]])
    Me = np.asarray(d["matrix_world"], float)
    assert np.allclose(M[:3, :3], Rx @ Me[:3, :3])
    assert np.allclose(M[:3, 3], 0.001 * Rx @ Me[:3, 3])
    # reprojection through lens/shift/matrix_world matches the engine pinhole
    P = np.array([12.0, -30.0, 5.0])
    Pw = br.engine_mm_to_blender_m(P)
    pc = M[:3, :3].T @ (Pw - M[:3, 3])          # Blender camera frame: looks down -z, +y up
    fpx = d["lens"] / d["sensor_width"] * 3000
    u = 3000 / 2 - c.shift_x * 3000 + fpx * pc[0] / -pc[2]
    v = 4000 / 2 + c.shift_y * 3000 - fpx * pc[1] / -pc[2]
    assert np.allclose([u, v], cam.project(P[None])[0], atol=1e-6)


# ------------------------------------------------------------------ jobs
class FakeProc:
    def __init__(self, polls_until_done=2, code=0):
        self.n, self.code, self.killed = polls_until_done, code, False

    def poll(self):
        if self.killed:
            return -9
        if self.n <= 0:
            return self.code
        self.n -= 1
        return None

    def kill(self):
        self.killed = True


def _fake_engine(monkeypatch, bx, run_log):
    def write_job(job_dir, stage, inputs, config, seed):
        Path(job_dir, "job.json").write_text(json.dumps(
            {"stage": stage, "config": config, "seed": seed, "inputs": sorted(inputs)}))

    def run_job(job_dir):
        run_log.append(job_dir)
        with open(Path(job_dir, "progress.jsonl"), "w") as fh:
            fh.write(json.dumps({"t": 0, "stage": "solve", "frac": 1.0, "msg_key": "done"}) + "\n")
        Path(job_dir, "result.json").write_text("{}")
        return 0

    eng = types.SimpleNamespace(write_job=write_job, run_job=run_job)
    monkeypatch.setattr(bx.jobs, "_engine_jobs", lambda: eng)


def test_jobs_timer_budget(bx, monkeypatch, tmp_path):
    bpy, jobs = bx.bpy, bx.jobs
    _fake_engine(monkeypatch, bx, [])
    popen_args = []

    def fake_popen(args):
        popen_args.append(args)
        return FakeProc(polls_until_done=3)

    monkeypatch.setattr(jobs.subprocess, "Popen", fake_popen)
    bx.pkg.register()
    r = jobs.JobRunner(tmp_path)
    jd = r.start("solve", {"a": 1}, {}, 7)
    assert popen_args[0][:3] == [sys.executable, "-I", jobs.launcher_path()] and popen_args[0][3] == jd
    assert json.loads(Path(jd, "job.json").read_text())["seed"] == 7
    assert bpy.app.timers.is_registered(r.poll)
    assert bpy.app.timers.registered[0][1] == 0.1
    assert bpy.context.scene.face3d.job.status == "running"
    # big progress file: 200k lines
    line = json.dumps({"t": 1.0, "stage": "solve", "frac": 0.5, "msg_key": "k"}) + "\n"
    Path(jd, "progress.jsonl").write_text(line * 200_000)
    t0 = time.perf_counter()
    assert r.poll() == 0.1
    assert time.perf_counter() - t0 <= 0.025
    assert 0.0 < r._offset < 200_000 * len(line) and r.progress == 0.5
    # finish: result present, process done, progress drained over several ticks
    Path(jd, "progress.jsonl").write_text(line * 10)
    r._offset = 0
    Path(jd, "result.json").write_text("{}")
    results = [r.poll() for _ in range(10)]
    assert results[-1] is None and r.status == "ready"
    assert bpy.context.scene.face3d.job.status == "ready"
    assert bpy.context.scene.face3d.job.progress == 1.0


def test_jobs_cancel_kills_and_failure(bx, monkeypatch, tmp_path):
    jobs = bx.jobs
    _fake_engine(monkeypatch, bx, [])
    proc = FakeProc(polls_until_done=10 ** 6)
    monkeypatch.setattr(jobs.subprocess, "Popen", lambda a: proc)
    r = jobs.JobRunner(tmp_path)
    jd = r.start("fit", {}, {}, 1)
    r.cancel()
    assert Path(jd, "cancel").exists()
    assert r.poll() == 0.1 and not proc.killed
    r._cancel_at -= 2.0
    assert r.poll() is None and proc.killed and r.status == "cancelled"
    # failure path reads error.json (no paths/coordinates kept)
    r2 = jobs.JobRunner(tmp_path)
    jd2 = r2.start("fit", {}, {}, 1)
    Path(jd2, "error.json").write_text(json.dumps({"code": "E", "msg_key": "bad", "stage": "fit"}))
    r2.proc = FakeProc(0, code=1)
    assert r2.poll() is None and r2.status == "failed" and r2.error["msg_key"] == "bad"


def test_jobs_background_runs_synchronously(bx, monkeypatch, tmp_path):
    bpy, jobs = bx.bpy, bx.jobs
    log = []
    _fake_engine(monkeypatch, bx, log)
    monkeypatch.setattr(jobs.subprocess, "Popen",
                        lambda a: pytest.fail("no subprocess in background mode"))
    bpy.app.background = True
    r = jobs.JobRunner(tmp_path)
    jd = r.start("solve", {}, {}, 3)
    assert log == [jd] and r.status == "ready" and r.progress == 1.0
    assert r.msg_key == "done" and bpy.app.timers.registered == []


def test_launcher_isolated_mode(tmp_path):
    ext = tmp_path / "ext"
    pk = ext / "engine" / "face3d" / "pipeline"
    pk.mkdir(parents=True)
    (ext / "engine" / "face3d" / "__init__.py").write_text("")
    (pk / "__init__.py").write_text("")
    (pk / "jobs.py").write_text(
        "import json, os\n"
        "def run_job(job_dir):\n"
        "    spec = json.load(open(os.path.join(job_dir, 'job.json')))\n"
        "    open(os.path.join(job_dir, 'result.json'), 'w').write(json.dumps({'stage': spec['stage']}))\n"
        "    return 0\n")
    (ext / "launcher.py").write_text((EXT / "launcher.py").read_text())
    job = tmp_path / "job"
    job.mkdir()
    (job / "job.json").write_text(json.dumps({"stage": "tiny", "config": {}, "seed": 1, "inputs": {}}))
    cp = subprocess.run([sys.executable, "-I", str(ext / "launcher.py"), str(job)],
                        capture_output=True, text=True, cwd=str(tmp_path), timeout=60)
    assert cp.returncode == 0, cp.stderr
    assert json.loads((job / "result.json").read_text()) == {"stage": "tiny"}


def test_launcher_dev_layout_resolves_repo_root():
    src = (EXT / "launcher.py").read_text()
    ns = {"__file__": str(EXT / "launcher.py"), "__name__": "launcher_probe"}
    saved = list(sys.path)
    try:
        exec(compile(src, str(EXT / "launcher.py"), "exec"), ns)
        assert sys.path[0] == str(ROOT)
    finally:
        sys.path[:] = saved


# ------------------------------------------------------------------ build
def _load_build():
    spec = importlib.util.spec_from_file_location("build_extension_wp21", ROOT / "tools" / "build_extension.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _mini_tree(tmp_path):
    eng = tmp_path / "face3d"
    (eng / "tests").mkdir(parents=True)
    (eng / "__pycache__").mkdir()
    (eng / "__init__.py").write_text('"""x"""\nimport numpy\nimport json\n')
    (eng / "mod.py").write_text("# SPDX-License-Identifier: MIT\nX = 1\n")
    (eng / "tests" / "test_x.py").write_text("")
    (eng / "__pycache__" / "a.pyc").write_bytes(b"0")
    ext = tmp_path / "ext"
    ext.mkdir()
    for f in ("blender_manifest.toml", "NOTICE", "__init__.py"):
        (ext / f).write_bytes((EXT / f).read_bytes())
    (ext / "__pycache__").mkdir()
    (ext / "__pycache__" / "x.pyc").write_bytes(b"0")
    gpl = tmp_path / "COPYING"
    gpl.write_text("GNU GENERAL PUBLIC LICENSE\nVersion 3, 29 June 2007\n")
    return eng, ext, gpl


def test_build_extension_zip(tmp_path):
    be = _load_build()
    eng, ext, gpl = _mini_tree(tmp_path)
    out = tmp_path / "o" / "x.zip"
    rep = be.build(out, engine_src=eng, ext_src=ext, gpl_text=gpl)
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        assert "blender_manifest.toml" in names and "engine/face3d/__init__.py" in names
        assert not any("__pycache__" in n or "/tests/" in n or n.endswith((".whl", ".pyc")) for n in names)
        assert zf.read("engine/face3d/__init__.py").decode().startswith("# SPDX-License-Identifier: MIT")
        assert zf.read("engine/face3d/mod.py").decode().count("SPDX") == 1
        assert "LICENSE" in names
    assert rep["spdx_added"] == ["engine/face3d/__init__.py"]
    # missing gpl text for store build
    with pytest.raises(be.BuildError):
        be.build(tmp_path / "n.zip", engine_src=eng, ext_src=ext, gpl_text=None)
    # no-SPDX refusal
    with pytest.raises(be.BuildError):
        be.build(tmp_path / "n.zip", engine_src=eng, ext_src=ext, gpl_text=gpl, add_spdx=False)
    # network permission
    man = (ext / "blender_manifest.toml").read_text()
    (ext / "blender_manifest.toml").write_text(man.replace("[permissions]", '[permissions]\nnetwork = "x"'))
    with pytest.raises(be.BuildError, match="network"):
        be.build(tmp_path / "n.zip", engine_src=eng, ext_src=ext, gpl_text=gpl)
    be.build(tmp_path / "off.zip", engine_src=eng, ext_src=ext, store=False)   # off-store ok
    (ext / "blender_manifest.toml").write_text(man)
    # long tagline
    (ext / "blender_manifest.toml").write_text(man.replace("Fit a sculpt-ready head to consented photos", "x" * 65))
    with pytest.raises(be.BuildError, match="tagline"):
        be.build(tmp_path / "n.zip", engine_src=eng, ext_src=ext, gpl_text=gpl)
    (ext / "blender_manifest.toml").write_text(man)
    # assets: non-CC0 refused, CC0 accepted
    (ext / "assets").mkdir()
    (ext / "assets" / "head.obj").write_text("v 0 0 0\n")
    with pytest.raises(be.BuildError, match="not listed"):
        be.build(tmp_path / "n.zip", engine_src=eng, ext_src=ext, gpl_text=gpl)
    (ext / "assets" / "assets.toml").write_text('[[asset]]\npath = "assets/head.obj"\nlicense = "CC-BY-4.0"\n')
    with pytest.raises(be.BuildError, match="CC0"):
        be.build(tmp_path / "n.zip", engine_src=eng, ext_src=ext, gpl_text=gpl)
    (ext / "assets" / "assets.toml").write_text('[[asset]]\npath = "assets/head.obj"\nlicense = "CC0-1.0"\n')
    be.build(tmp_path / "ok.zip", engine_src=eng, ext_src=ext, gpl_text=gpl)
    # wheels and non-numpy imports
    (ext / "w.whl").write_bytes(b"x")
    with pytest.raises(be.BuildError, match="wheel"):
        be.build(tmp_path / "n.zip", engine_src=eng, ext_src=ext, gpl_text=gpl)
    (ext / "w.whl").unlink()
    (eng / "bad.py").write_text("# SPDX-License-Identifier: MIT\nimport scipy\n")
    with pytest.raises(be.BuildError, match="scipy"):
        be.build(tmp_path / "n.zip", engine_src=eng, ext_src=ext, gpl_text=gpl)


def test_build_real_tree_is_clean(tmp_path):
    be = _load_build()
    gpl = tmp_path / "COPYING"
    gpl.write_text("GNU GENERAL PUBLIC LICENSE Version 3")
    rep = be.build(tmp_path / "real.zip", gpl_text=gpl)
    assert "blender_manifest.toml" in rep["files"]
    assert any(n.startswith("engine/face3d/") for n in rep["files"])


# ------------------------------------------------------------------ AST rules
_BANNED_ATTRS = {"foreach_get", "foreach_set", "pixels"}


def test_only_bridge_touches_mesh_data():
    seen_bridge = False
    for p in sorted((ROOT / "blender_ext").rglob("*.py")):
        tree = ast.parse(p.read_text(), filename=str(p))
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        if p.name == "bridge.py":
            seen_bridge = True
            assert {"foreach_get", "foreach_set"} <= attrs
            continue
        assert not (attrs & _BANNED_ATTRS), "%s touches mesh/image data" % p
    assert seen_bridge


def test_engine_has_no_bpy_import():
    bad = {"bpy", "mathutils", "gpu", "gpu_extras", "blf", "bmesh"}
    for p in sorted((ROOT / "face3d").rglob("*.py")):
        tree = ast.parse(p.read_text(), filename=str(p))
        for n in ast.walk(tree):
            mods = []
            if isinstance(n, ast.Import):
                mods = [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
                mods = [n.module]
            assert not {m.split(".")[0] for m in mods} & bad, p


# ------------------------------------------------------------------ review fixes
def test_shape_key_rewrite_updates_in_place(bx):
    bpy, br = bx.bpy, bx.bridge
    ob, V, _ = _cube_obj(bpy)
    br.write_shape_key(ob, "ID_fit", V + 1.0)
    br.write_shape_key(ob, "artist", V + 3.0, relative_to="ID_fit")
    kb = br.write_shape_key(ob, "ID_fit", V + 2.0, slider_max=1.5)
    blocks = ob.data.shape_keys.key_blocks
    assert [k.name for k in blocks] == ["Basis", "ID_fit", "artist"]
    assert blocks["artist"].relative_key is blocks["ID_fit"] is kb
    keys = br.read_shape_keys(ob)
    assert np.array_equal(keys["ID_fit"][0], V + 2.0) and keys["ID_fit"][3] == 1.5
    assert np.array_equal(keys["artist"][0], V + 3.0) and keys["artist"][1] == "ID_fit"
    with pytest.raises(ValueError):
        br.write_shape_key(ob, "ID_fit", V[:3])
    # the stub now mimics Blender's unique key-block names
    assert ob.shape_key_add(name="artist", from_mix=False).name == "artist.001"


def test_bridge_refuses_non_finite(bx):
    bpy, br = bx.bpy, bx.bridge
    ob, V, _ = _cube_obj(bpy)
    bad = V.copy()
    bad[2, 1] = np.nan
    with pytest.raises(br.BridgeRefusal):
        br.write_vertices(ob.data, bad)
    with pytest.raises(br.BridgeRefusal):
        br.write_shape_key(ob, "k", np.where(V > 0, np.inf, V))
    assert np.array_equal(br.mesh_vertices_to_array(ob.data), V)
    assert ob.data.shape_keys is None or ob.data.shape_keys.key_blocks.get("k") is None


def test_mode_guard_refuses_non_active_object(bx):
    bpy, br = bx.bpy, bx.bridge
    ob, _, _ = _cube_obj(bpy)
    other = bpy.data.objects.new("other", None)
    bpy.context.object = other
    ob.mode = "WEIGHT_PAINT"
    with pytest.raises(br.BridgeRefusal):
        with br.mode_guard(ob):
            pytest.fail("body must not run")
    assert ob.mode == "WEIGHT_PAINT" and other.mode == "OBJECT"


def test_probe_platform_avoids_platform_uname(bx, monkeypatch):
    import platform
    monkeypatch.setattr(platform, "uname", lambda: pytest.fail("platform.uname called"))
    info = bx.compat.probe()
    assert info["platform"].startswith(sys.platform.lower() + "-")


def test_jobs_spawn_failure_and_double_start(bx, monkeypatch, tmp_path):
    bpy, jobs = bx.bpy, bx.jobs
    _fake_engine(monkeypatch, bx, [])

    def boom(args):
        raise OSError("cannot spawn")

    monkeypatch.setattr(jobs.subprocess, "Popen", boom)
    bx.pkg.register()
    r = jobs.JobRunner(tmp_path)
    assert r.start("solve", {}, {}, 1) is None
    assert r.status == "failed" and r.error["code"] == "spawn_failed"
    assert bpy.context.scene.face3d.job.status == "failed"
    assert bpy.app.timers.registered == []
    # a second start while running is refused: no orphan process, one timer
    monkeypatch.setattr(jobs.subprocess, "Popen", lambda a: FakeProc(10 ** 6))
    jd = r.start("solve", {}, {}, 1)
    assert jd and r.status == "running"
    assert r.start("solve", {}, {}, 2) is None and r.job_dir == jd
    assert sum(1 for fn, _a, _b in bpy.app.timers.registered if fn == r.poll) == 1


def _fake_clock(monkeypatch, jobs, step):
    t = [0.0]

    def pc():
        t[0] += step
        return t[0]

    monkeypatch.setattr(jobs, "time", types.SimpleNamespace(perf_counter=pc))


def test_jobs_budget_limits_parsing_and_drain_continues(bx, monkeypatch, tmp_path):
    jobs = bx.jobs
    _fake_engine(monkeypatch, bx, [])
    proc = FakeProc(polls_until_done=10 ** 6)
    monkeypatch.setattr(jobs.subprocess, "Popen", lambda a: proc)
    r = jobs.JobRunner(tmp_path)
    jd = r.start("solve", {}, {}, 1)
    line = json.dumps({"t": 1.0, "stage": "solve", "frac": 0.5, "msg_key": "k"}) + "\n"
    Path(jd, "progress.jsonl").write_text(line * 50)
    _fake_clock(monkeypatch, jobs, 0.015)     # each clock read costs 15 ms
    recs, off = jobs.read_progress_budgeted(jd, 0, budget_s=0.020)
    assert 1 <= len(recs) <= 3 and off == len(recs) * len(line)
    # process finished with unread progress: poll keeps ticking (0.1) before returning None
    proc.n, proc.code = 0, 0
    Path(jd, "result.json").write_text("{}")
    out = []
    for _ in range(100):
        v = r.poll()
        out.append(v)
        if v is None:
            break
    assert out[0] == 0.1 and out[-1] is None and len(out) > 2 and r.status == "ready"
    assert r._offset == 50 * len(line)


def test_jobs_result_after_cancel_wins_only_on_clean_exit(bx, monkeypatch, tmp_path):
    jobs = bx.jobs
    _fake_engine(monkeypatch, bx, [])
    proc = FakeProc(polls_until_done=1, code=0)
    monkeypatch.setattr(jobs.subprocess, "Popen", lambda a: proc)
    r = jobs.JobRunner(tmp_path)
    jd = r.start("solve", {}, {}, 1)
    r.cancel()
    Path(jd, "result.json").write_text("{}")
    while r.poll() is not None:
        pass
    assert r.status == "ready"          # finished cleanly before the kill: result stands
    proc2 = FakeProc(polls_until_done=10 ** 6)
    monkeypatch.setattr(jobs.subprocess, "Popen", lambda a: proc2)
    r2 = jobs.JobRunner(tmp_path)
    jd2 = r2.start("solve", {}, {}, 1)
    r2.cancel()
    Path(jd2, "result.json").write_text("{}")
    r2._cancel_at -= 2.0
    while r2.poll() is not None:
        pass
    assert proc2.killed and r2.status == "cancelled"


def test_build_rejects_unlicensed_engine_data_and_wheels(tmp_path):
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        import build_extension as be
    finally:
        sys.path.pop(0)
    be._check_engine_data("data/x.json", b'{"licence": "CC0-1.0"}')
    be._check_engine_data("core/defaults.toml", b"a = 1\n")
    for sub, raw in (("data/x.json", b'{"licence": "CC-BY-4.0"}'), ("data/y.json", b"{}"),
                     ("data/z.toml", b"a = 1\n")):
        with pytest.raises(be.BuildError):
            be._check_engine_data(sub, raw)
    m = tmp_path / "m.toml"
    src = (EXT / "blender_manifest.toml").read_text()
    m.write_text("wheels = [\"./wheels/x.whl\"]\n" + src)
    with pytest.raises(be.BuildError):
        be.validate_manifest(m, store=True)


def test_stub_has_wp22_apis(bx):
    bpy = bx.bpy
    app = bpy.app
    app.translations.register("m", {"en": {}})
    assert app.translations.pgettext("x") == "x"
    app.translations.unregister("m")
    km = bpy.context.window_manager.keyconfigs.addon.keymaps.new("Window")
    it = km.keymap_items.new("f3d.op", "F", "PRESS")
    km.keymap_items.remove(it)
    assert bpy.data.images.load("/x/y.jpg").size == (64, 64)
    bpy.context.scene.timeline_markers.new("m", frame=1)
    bpy.data.cameras.new("c").background_images.new()
    assert bpy.context.scene.render.resolution_x > 0
    from gpu_extras.batch import batch_for_shader
    assert batch_for_shader(None, "LINES", {}) is not None
