"""WP-14: maintainer tools (MediaPipe scheme file, detector helper, scheme calibration, prior recalibration).

Acceptance tests from docs/wbs.json (WP-14) plus supporting checks.  Everything
runs on synthetic inputs and fake modules: no MediaPipe, Blender, network or
real-person data (DESIGN D-26).
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
import types
from pathlib import Path

import numpy as np
import pytest

from face3d.geometry.camera import Camera, look_at
from face3d.io.landmarks import Face, LandmarkSet, load_landmarks, save_landmarks
from face3d.io.png import read_png
from face3d.mesh.distance import point_to_mesh
from face3d.model.landmark_prior import FactorPrior, load_prior_package
from face3d.model.procedural_head import build_procedural_head
from face3d.model.registry import Scheme, load_scheme
from face3d.model.template_kit import TemplateKit, vertex_embedding

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"
RESEARCH_LIC = REPO / "research" / "data" / "landmark-index-correspondence.json"
RESEARCH_METRIC = REPO / "research" / "data" / "metric-3d-landmark-reference.json"
needs_lic = pytest.mark.skipif(not RESEARCH_LIC.is_file(), reason="research JSON absent")
needs_metric = pytest.mark.skipif(not RESEARCH_METRIC.is_file(), reason="research JSON absent")


def _tool(name: str):
    spec = importlib.util.spec_from_file_location(f"wp14_{name}", TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# =========================================================================== 1. scheme file
@needs_lic
def test_mediapipe_scheme_built_from_research(tmp_path):
    out = tmp_path / "mediapipe_478.json"
    proc = subprocess.run([sys.executable, str(TOOLS / "build_scheme_mediapipe.py"), "--out", str(out)],
                          cwd=str(tmp_path), capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    packaged = REPO / "face3d" / "schemes" / "mediapipe_478.json"
    assert out.read_bytes() == packaged.read_bytes()          # rebuilding is byte-identical
    again = tmp_path / "again.json"
    assert _tool("build_scheme_mediapipe").main(["--out", str(again)]) == 0
    assert again.read_bytes() == out.read_bytes()

    sch = load_scheme("mediapipe_478")
    assert sch.n == 478 and len(sch.points) == 478 and [p.index for p in sch.points] == list(range(478))
    assert not any(p.verified for p in sch.points)
    pi = sch.mirror_permutation()
    assert np.array_equal(pi[pi], np.arange(478))
    assert len(sch.mirror_pairs) == 70 and sch.raw["mirror_complete"] is False
    for a, b in sch.mirror_pairs:
        assert pi[a] == b and pi[b] == a
        assert {sch.points[a].side, sch.points[b].side} in ({"L", "R"}, {"geometric"})
    # iris groups: geometric, never side-named, p only through lr_groups
    assert [g["indices"] for g in sch.lr_groups] == [list(range(468, 473)), list(range(473, 478))]
    assert all(g["rule"] == "geometric" and g["anatomical_id"] == "p" for g in sch.lr_groups)
    for i in range(468, 478):
        p = sch.points[i]
        assert p.side == "geometric" and p.anatomical_id is None and p.kind == "iris"
        assert not p.name.endswith(("_L", "_R"))
    # no polyline touching the iris indices carries a side from the index; the research side is provisional only
    iris_polys = {k: v for k, v in sch.polylines.items() if set(v["indices"]) & set(range(468, 478))}
    assert set(iris_polys) == {"iris_a_centre_then_ring", "iris_b_centre_then_ring"}
    for v in sch.polylines.values():
        if set(v["indices"]) & set(range(468, 478)):
            assert v["side"] not in ("L", "R") and v["side"] == "geometric"
            assert v["provisional_side"] in ("L", "R") and "never used" in v["provisional_note"]
    assert iris_polys["iris_a_centre_then_ring"]["indices"] == list(range(468, 473))
    assert (468, 473) in [tuple(p) for p in sch.mirror_pairs] and "[468, 473]" in sch.raw["notes"]
    assert "no side meaning" in sch.raw["notes"]
    aidx = sch.anatomical_index()
    assert not any(k.startswith("p_") for k in aidx)
    for b in ("prn", "sn"):
        assert b in aidx
    for b in ("en", "ex", "ch"):
        assert f"{b}_L" in aidx and f"{b}_R" in aidx
    # spot checks against the research table (subject-relative sides)
    assert aidx["prn"] == 1 and aidx["sn"] == 2 and aidx["ex_R"] == 33 and aidx["ex_L"] == 263
    assert aidx["en_R"] == 133 and aidx["en_L"] == 362 and aidx["ch_R"] == 61 and aidx["ch_L"] == 291
    assert "sto" not in aidx                                  # two indices (13, 14): never one id
    kinds = {p.index: p.kind for p in sch.points}
    assert kinds[1] == "extremal" and kinds[133] == "sharp_junction" and kinds[159] == "curve"
    assert kinds[234] == "contour" and kinds[70] == "brow" and kinds[338] == "contour"
    assert sum(k == "generic" for k in kinds.values()) > 250
    assert sch.points[10].anatomical_id is None                # mesh top is never trichion
    assert sch.z_policy == "ignore" and sch.licence == "CC0-1.0" and "C7" in sch.raw["licence_note"]
    det = sch.raw["detector"]
    assert det["code_licence"] == "Apache-2.0" and det["commercial_ok"] is None
    assert "contested" in det["weights_licence"]


# =========================================================================== 2. detector helper
def _mirror_offsets(seed: int = 5) -> np.ndarray:
    """Landmark offsets (units of the blob radius) consistent with the scheme mirror permutation."""
    sch = load_scheme("mediapipe_478")
    perm = sch.mirror_permutation()
    sides = np.array(sch.sides())
    off = np.random.default_rng(seed).uniform(-1.2, 1.2, (478, 2))
    off[sides == "mid", 0] = 0.0
    for i in range(478):
        if perm[i] > i:
            off[perm[i]] = (-off[i, 0], off[i, 1])
    return off


def _fake_mediapipe(offsets: np.ndarray, n_faces: int = 1):
    """A fake ``mediapipe`` module exposing the Tasks-API surface the helper uses.

    Its detector is equivariant: landmarks = intensity centroid + RMS radius x offsets,
    so similarity jitter and flips of the image move the landmarks like a real face.
    """
    calls: list[dict] = []

    class _Pt:
        def __init__(self, x, y):
            self.x, self.y, self.z = float(x), float(y), 0.0

    class _Cat:
        def __init__(self, name, score):
            self.category_name, self.score = name, score

    class _Image:
        def __init__(self, image_format=None, data=None):
            self.image_format, self.data = image_format, data

    class _Landmarker:
        def detect(self, image):
            a = image.data.astype(float).mean(axis=2)
            H, W = a.shape
            w = a / a.sum()
            ys, xs = np.mgrid[0:H, 0:W] + 0.5
            cx, cy = (w * xs).sum(), (w * ys).sum()
            r = np.sqrt((w * ((xs - cx) ** 2 + (ys - cy) ** 2)).sum())
            faces = []
            for k in range(n_faces):
                pts = np.column_stack([(cx + r * offsets[:, 0]) / W + 0.3 * k, (cy + r * offsets[:, 1]) / H])
                faces.append(pts)
            calls.append({"wh": (W, H), "faces": faces})
            res = types.SimpleNamespace()
            res.face_landmarks = [[_Pt(*p) for p in f] for f in faces]
            res.face_blendshapes = [[_Cat("jawOpen", 0.25), _Cat("eyeBlinkLeft", 0.5)] for _ in faces]
            res.facial_transformation_matrixes = [np.eye(4) for _ in faces]
            return res

        def close(self):
            calls.append({"closed": True})

    class _FaceLandmarker:
        @staticmethod
        def create_from_options(options):
            assert options["running_mode"] == "IMAGE" and options["output_face_blendshapes"] is True
            assert options["output_facial_transformation_matrixes"] is True
            assert options["base_options"]["model_asset_buffer"] == b"fake face landmarker model"
            return _Landmarker()

    vision = types.SimpleNamespace(FaceLandmarker=_FaceLandmarker, FaceLandmarkerOptions=lambda **k: k,
                                   RunningMode=types.SimpleNamespace(IMAGE="IMAGE"))
    mp = types.ModuleType("mediapipe")
    mp.__version__ = "0.10-fake"
    mp.tasks = types.SimpleNamespace(BaseOptions=lambda **k: k, vision=vision)
    mp.Image = _Image
    mp.ImageFormat = types.SimpleNamespace(SRGB="SRGB")
    return mp, calls


def _blob(W: int, H: int, cx: float, cy: float, s: float) -> np.ndarray:
    ys, xs = np.mgrid[0:H, 0:W] + 0.5
    g = 255.0 * np.exp(-((xs - cx) ** 2 + (ys - cy) ** 2) / (2.0 * s * s))
    return np.repeat(np.rint(g)[..., None], 3, axis=2).astype(np.uint8)


def test_detect_helper_with_fake_mediapipe(tmp_path, monkeypatch):
    from PIL import Image

    # importing the helper needs neither mediapipe nor Pillow
    monkeypatch.delitem(sys.modules, "mediapipe", raising=False)
    mod = _tool("detect_mediapipe")
    assert "mediapipe" not in sys.modules
    offsets = _mirror_offsets()
    fake, calls = _fake_mediapipe(offsets)
    monkeypatch.setitem(sys.modules, "mediapipe", fake)

    W, H = 320, 240
    img = _blob(W, H, 150.0, 110.0, 22.0)
    photo = tmp_path / "face.png"
    Image.fromarray(img).save(photo)
    model = tmp_path / "face_landmarker.task"
    model.write_bytes(b"fake face landmarker model")
    sha = hashlib.sha256(model.read_bytes()).hexdigest()
    base = ["--model", str(model), "--model-sha256", sha, "--images", str(photo)]

    # sha mismatch refused before anything runs
    assert mod.main(["--model", str(model), "--model-sha256", "0" * 64, "--images", str(photo),
                     "--out", str(tmp_path / "bad")]) == 2
    assert not (tmp_path / "bad").exists() and not calls

    # no TTA: uv == x * W exactly (corner convention)
    assert mod.main(base + ["--out", str(tmp_path / "o0"), "--tta", "0"]) == 0
    ls = load_landmarks(tmp_path / "o0" / "face.landmarks.json")
    x = calls[0]["faces"][0]
    assert calls[0]["wh"] == (W, H)
    assert np.abs(ls.faces[0].uv - x * np.array([W, H])).max() <= 1e-9
    assert ls.scheme == "mediapipe_478" and len(ls.faces) == 1
    d = ls.detector
    assert d["backend"] == "mediapipe-tasks" and d["version"] == "0.10-fake" and d["model_sha256"] == sha
    assert d["commercial_ok"] is None and d["is_ml"] is True and "Apache-2.0" in d["licence"]
    assert ls.image["orientation_applied"] is True and ls.image["wh"] == [W, H]
    assert ls.image["sha256"] == hashlib.sha256(photo.read_bytes()).hexdigest()
    assert ls.faces[0].score == 1.0 and ls.faces[0].tta_spread_px is None
    assert ls.faces[0].blendshapes == {"jawOpen": 0.25, "eyeBlinkLeft": 0.5}
    extras = json.loads((tmp_path / "o0" / "face.mediapipe_extras.json").read_text())
    assert extras["faces"][0]["facial_transformation_matrix"] == np.eye(4).tolist()

    # TTA: 8 passes, exact inverse maps, median + robust spread
    calls.clear()
    assert mod.main(base + ["--out", str(tmp_path / "o8"), "--tta", "8", "--png-out", "--seed", "3"]) == 0
    det_calls = [c for c in calls if "faces" in c]
    assert len(det_calls) == 8
    ls8 = load_landmarks(tmp_path / "o8" / "face.landmarks.json")
    f8 = ls8.faces[0]
    plain = det_calls[0]["faces"][0] * np.array([W, H])
    assert f8.tta_spread_px is not None and f8.tta_spread_px.shape == (478,)
    assert np.all(np.isfinite(f8.tta_spread_px)) and np.all(f8.tta_spread_px >= 0.0)
    assert 0.0 < np.max(f8.tta_spread_px) < 0.5
    assert np.abs(f8.uv - plain).max() < 0.3
    assert f8.score == 1.0 and ls8.detector["tta"]["passes"] == 8
    plan = mod.tta_plan(8, W, H, np.random.default_rng(3))
    assert [a.kind for a in plan] == ["plain"] + ["jitter"] * 6 + ["flip"]
    sch = load_scheme("mediapipe_478")
    perm = sch.mirror_permutation()
    known = (perm != np.arange(478)) | (np.array(sch.sides()) == "mid")
    for aug, c in zip(plan, det_calls):
        back = mod.map_back(c["faces"][0], aug, W, H, W, H, perm, known)
        if aug.kind == "flip":
            assert np.all(np.isnan(back[~known])) and np.all(np.isfinite(back[known]))
            assert np.abs(back[known] - plain[known]).max() < 0.3
        else:
            assert np.abs(back - plain).max() < 0.3
    assert np.array_equal(read_png(tmp_path / "o8" / "face.png"), img)
    # robust spread definition: 1.4826 x median radial deviation from the median
    stack = np.stack([np.zeros((1, 2)), np.ones((1, 2)), 2 * np.ones((1, 2))])
    med = np.median(stack, axis=0)
    assert mod.robust_spread(stack, med)[0] == pytest.approx(1.4826 * np.sqrt(2.0))

    # large photo: detection at long side 2048, mapping back u = x * W
    calls.clear()
    big = tmp_path / "big.png"
    Image.fromarray(_blob(2600, 1300, 1300.0, 600.0, 150.0)).save(big)
    assert mod.main(["--model", str(model), "--model-sha256", sha, "--images", str(big),
                     "--out", str(tmp_path / "ob"), "--tta", "0"]) == 0
    assert calls[0]["wh"] == (2048, 1024)
    lb = load_landmarks(tmp_path / "ob" / "big.landmarks.json")
    assert lb.image["wh"] == [2600, 1300] and lb.image["detect_wh"] == [2048, 1024]
    assert np.abs(lb.faces[0].uv - calls[0]["faces"][0] * np.array([2600, 1300])).max() <= 1e-9


def test_detect_helper_all_faces_orientation_and_heic(tmp_path, monkeypatch):
    from PIL import Image

    mod = _tool("detect_mediapipe")
    fake, calls = _fake_mediapipe(_mirror_offsets(), n_faces=2)
    monkeypatch.setitem(sys.modules, "mediapipe", fake)
    model = tmp_path / "m.task"
    model.write_bytes(b"fake face landmarker model")
    sha = hashlib.sha256(model.read_bytes()).hexdigest()
    # EXIF orientation 6 is baked: a 40 x 20 stored image becomes 20 x 40
    jpg = tmp_path / "rot.jpg"
    exif = Image.Exif()
    exif[0x0112] = 6
    Image.fromarray(_blob(40, 20, 20.0, 10.0, 5.0)).save(jpg, exif=exif.tobytes())
    heic = tmp_path / "x.heic"
    heic.write_bytes(b"not really a heic file")
    rc = mod.main(["--model", str(model), "--model-sha256", sha, "--images", str(jpg), str(heic),
                   "--out", str(tmp_path / "o"), "--tta", "0", "--num-faces", "2"])
    assert rc == 1                                          # the HEIC was skipped, the JPEG processed
    ls = load_landmarks(tmp_path / "o" / "rot.landmarks.json")
    assert ls.image["wh"] == [20, 40] and ls.image["exif_orientation"] == 6
    assert len(ls.faces) == 2 and all(f.score == 1.0 for f in ls.faces)   # every face kept (eth F1)
    assert not (tmp_path / "o" / "x.landmarks.json").exists()
    with pytest.raises(mod.Refused):
        mod.read_verified_model(model, "zz")


# =========================================================================== 3. scheme calibration
def _calib_scene(kit: TemplateKit):
    """A synthetic calibration scheme on the procedural head: 16 frontal mirror pairs, 4 midline
    points (all embedded) and two iris groups without embeddings."""
    V, Nn, tris = kit.vertices, kit.normals, kit.triangles()
    cand = np.flatnonzero((V[:, 0] > 8.0) & (Nn[:, 2] > 0.85) & (V[:, 2] > 30.0) & (V[:, 1] > -75.0)
                          & (V[:, 1] < 45.0))
    chosen = [int(cand[np.argmax(V[cand, 2])])]
    while len(chosen) < 16:                                  # farthest-point sampling (deterministic)
        d = np.min(np.linalg.norm(V[cand][:, None] - V[chosen][None], axis=2), axis=1)
        chosen.append(int(cand[np.argmax(d)]))
    mid_c = sorted((int(v) for v in kit.midline if Nn[v, 2] > 0.9 and V[v, 2] > 60.0), key=lambda v: V[v, 1])
    mid = [mid_c[i] for i in np.linspace(0, len(mid_c) - 1, 4).astype(int)]
    kinds = ("sharp_junction", "curve", "extremal", "generic")
    pts, emb, verts, pairs = [], {}, {}, []
    for k, v in enumerate(chosen):
        for side, vv in (("R", int(kit.mirror_map[v])), ("L", v)):
            name = f"g{side}{k:02d}"
            pts.append({"index": len(pts), "name": name, "anatomical_id": None, "kind": kinds[k % 4],
                        "side": side, "verified": False, "badge": ""})
            verts[name] = vv
        pairs.append([len(pts) - 2, len(pts) - 1])
    for k, v in enumerate(mid):
        name = f"gM{k}"
        pts.append({"index": len(pts), "name": name, "anatomical_id": None, "kind": "curve", "side": "mid",
                    "verified": False, "badge": ""})
        verts[name] = v
    for nm in ("iris_a_centre", "iris_b_centre"):
        pts.append({"index": len(pts), "name": nm, "anatomical_id": None, "kind": "iris", "side": "geometric",
                    "verified": False, "badge": ""})
    pairs.append([len(pts) - 2, len(pts) - 1])
    for name, v in verts.items():
        tri, bary = vertex_embedding(tris, v)
        emb[name] = {"tri": tri, "bary": bary, "sigma_annot_mm": 0.0, "provenance": "test vertex"}
    doc = {"format": "face3d.scheme", "version": 1, "licence": "CC0-1.0", "scheme": "calib_test", "n": len(pts),
           "points": pts, "polylines": {}, "mirror_pairs": pairs, "z_policy": "ignore",
           "lr_groups": [{"name": "iris_a", "indices": [len(pts) - 2], "rule": "geometric", "provisional_side": "R"},
                         {"name": "iris_b", "indices": [len(pts) - 1], "rule": "geometric", "provisional_side": "L"}]}
    return Scheme(doc), doc, emb


def test_calibrate_scheme_recovers_offsets(tmp_path):
    cs = _tool("calibrate_scheme")
    kit0 = build_procedural_head()
    sch, doc, emb = _calib_scene(kit0)
    kit = kit0.replace(landmarks={**kit0.landmarks, "calib_test": emb})
    surf = cs.Surface(kit)
    rng = np.random.default_rng(14)
    names = sch.names()

    # 30 calibrated renders around the face (yaw +/-20 deg, pitch +/-10 deg)
    target = np.array([0.0, -10.0, 60.0])
    cams = []
    for _ in range(30):
        yaw, pitch = np.radians(rng.uniform(-20, 20)), np.radians(rng.uniform(-10, 10))
        eye = target + 520.0 * np.array([np.sin(yaw) * np.cos(pitch), np.sin(pitch), np.cos(yaw) * np.cos(pitch)])
        R, t = look_at(eye, target)
        cams.append(Camera(f=1100.0, cx=240.0, cy=280.0, width=480, height=560, R=R, t=t))
    probe = [cs.Render(c.K, c.R, c.t, c.width, c.height, np.zeros((len(names), 2))) for c in cams]

    # truth: prior embedding, 2 mm surface offsets on 30 indices (15 pairs); iris groups deliberately swapped
    P0 = {nm: surf.point(e["tri"], e["bary"]) for nm, e in emb.items()}
    truth = {}
    offset_names = [nm for nm in names if nm[:2] in ("gL", "gR") and int(nm[2:]) < 15]
    assert len(offset_names) == 30
    for nm, e in emb.items():
        if nm in offset_names:
            nrm = surf.normal(e["tri"], e["bary"])
            d = rng.normal(size=3)
            if nm in ("gL00", "gR00"):
                d = np.array([1.0, 0.0, 0.0])               # same +x move on both sides: not mirrored
            d -= (d @ nrm) * nrm
            q = P0[nm] + 2.0 * d / np.linalg.norm(d)
            _, _, tri, bary = point_to_mesh(q[None], kit.vertices, kit.triangles(), grid=surf.grid)
            truth[nm] = (int(tri[0]), bary[0])
        else:
            truth[nm] = (e["tri"], e["bary"])
    p_emb = kit.landmarks["anatomical44"]
    truth["iris_a_centre"] = (p_emb["p_L"]["tri"], p_emb["p_L"]["bary"])   # provisional side says R
    truth["iris_b_centre"] = (p_emb["p_R"]["tri"], p_emb["p_R"]["bary"])

    # detections = projections + 0.5 px noise where visible; LandmarkSet files + records
    renders = []
    for k, (c, pr) in enumerate(zip(cams, probe)):
        uv = np.full((len(names), 2), np.nan)
        for i, nm in enumerate(names):
            tri, bary = truth[nm]
            if cs.visible_in(pr, surf, tri, bary):
                uv[i] = c.project(surf.point(tri, bary)[None])[0] + rng.normal(0.0, 0.5, 2)
        ls = LandmarkSet(scheme="calib_test", detector={"backend": "synthetic", "is_ml": False},
                         image={"sha256": "0" * 64, "wh": [c.width, c.height], "orientation_applied": True,
                                "input_flipped": False, "coords": "px_corner"},
                         faces=[Face(score=1.0, uv=uv, visible=np.all(np.isfinite(uv), axis=1))])
        save_landmarks(ls, tmp_path / f"r{k:02d}.landmarks.json")
        renders.append({"K": c.K.tolist(), "R": c.R.tolist(), "t": c.t.tolist(), "W": c.width, "H": c.height,
                        "detections": f"r{k:02d}.landmarks.json"})
    records = tmp_path / "records.json"
    records.write_text(json.dumps({"format": "face3d.render_records", "version": 1, "source": "template_render",
                                   "renders": renders}))
    (tmp_path / "calib_test.json").write_text(json.dumps(doc))
    kit_path = tmp_path / "kit.kit.json"
    kit.save(kit_path)

    rc = cs.main(["--kit", str(kit_path), "--renders", str(records), "--scheme", "calib_test",
                  "--scheme-path", str(tmp_path), "--out-kit", str(tmp_path / "out.kit.json"),
                  "--report", str(tmp_path / "report.json"), "--scheme-out", str(tmp_path / "scheme_out.json")])
    assert rc == 0
    report = json.loads((tmp_path / "report.json").read_text())
    out_kit = TemplateKit.load(tmp_path / "out.kit.json", expect_topology_sha256=kit.topology_sha256)
    by_name = {p["name"]: p for p in report["points"]}
    assert "uv" not in json.dumps(report)                     # aggregates only, never detections

    for nm in offset_names:
        e = by_name[nm]
        n = e["n"]
        assert n >= 20 and e["verified"] is True, (nm, e)
        w = n / (n + 2.0)
        assert e["w"] == pytest.approx(w, abs=1e-6)
        p_true = surf.point(*truth[nm])
        expect = P0[nm] + w * (p_true - P0[nm])
        got = out_kit.landmark_positions("calib_test", names=[nm])[0]
        assert np.linalg.norm(got - expect) < 0.3, (nm, np.linalg.norm(got - expect))
        assert np.linalg.norm(got - P0[nm]) > 0.5 * np.linalg.norm(p_true - P0[nm]) > 0.25   # it moved
        assert e["sigma_cal_mm"] < 1.0 and e["sigma_def_mm"] >= e["sigma_cal_mm"]
    # untouched points stay put
    for nm in ("gL15", "gR15", "gM0"):
        got = out_kit.landmark_positions("calib_test", names=[nm])[0]
        assert np.linalg.norm(got - P0[nm]) < 0.3
    # mirror-pair check: the asymmetric pair is flagged, the untouched pair is not
    assert "pair_mismatch" in by_name["gL00"]["flags"] and "pair_mismatch" in by_name["gR00"]["flags"]
    assert "pair_mismatch" not in by_name["gL15"]["flags"]
    # the deliberately swapped iris groups are resolved geometrically and flagged
    assert report["lr_resolved"] == {"iris_a": "L", "iris_b": "R"}
    flags = {g["name"]: g["flags"] for g in report["lr_groups"]}
    assert "lr_unexpected" in flags["iris_a"] and "lr_unexpected" in flags["iris_b"]
    assert by_name["iris_a_centre"]["init"] == "ray" and "lr_unexpected" in by_name["iris_a_centre"]["flags"]
    assert np.linalg.norm(out_kit.landmark_positions("calib_test", names=["iris_a_centre"])[0]
                          - surf.point(*truth["iris_a_centre"])) < 1.0
    # updated scheme: verified flags from the report, sides still geometric
    sch_out = Scheme(json.loads((tmp_path / "scheme_out.json").read_text()))
    assert sch_out.points[sch_out.index_of("gL01")].verified is True
    assert sch_out.points[sch_out.index_of("iris_a_centre")].side == "geometric"
    assert sch_out.raw["calibration"]["lr_resolved"] == {"iris_a": "L", "iris_b": "R"}


def test_calibrate_scheme_shrink_and_lr_from_detections():
    """Few renders: the w = n/(n+2) shrink is visible beyond the tolerance, and geometric L/R groups are
    resolved from the detections' optimum, not from the shrunk embedding (regression: a re-run with an
    iris embedding on the provisional side and one render kept the prior side without any flag)."""
    cs = _tool("calibrate_scheme")
    kit0 = build_procedural_head()
    sch, _doc, emb = _calib_scene(kit0)
    pe = kit0.landmarks["anatomical44"]
    emb = dict(emb)
    emb["iris_a_centre"] = dict(pe["p_R"])                   # prior embedding at the provisional side ...
    emb["iris_b_centre"] = dict(pe["p_L"])
    kit = kit0.replace(landmarks={**kit0.landmarks, "calib_test": emb})
    surf = cs.Surface(kit)
    rng = np.random.default_rng(3)
    names = sch.names()
    P0 = {nm: surf.point(e["tri"], e["bary"]) for nm, e in emb.items()}
    truth = {}
    for nm, e in emb.items():
        if nm.startswith("iris"):
            continue
        nrm = surf.normal(e["tri"], e["bary"])
        d = rng.normal(size=3)
        d -= (d @ nrm) * nrm
        q = P0[nm] + 3.0 * d / np.linalg.norm(d)               # 3 mm offsets
        _, _, tri, bary = point_to_mesh(q[None], kit.vertices, kit.triangles(), grid=surf.grid)
        truth[nm] = (int(tri[0]), bary[0])
    truth["iris_a_centre"] = (pe["p_L"]["tri"], pe["p_L"]["bary"])   # ... the detections say the other eye
    truth["iris_b_centre"] = (pe["p_R"]["tri"], pe["p_R"]["bary"])
    target = np.array([0.0, -10.0, 60.0])
    renders = []
    for yaw_d in (-5, -15, 5, 15):
        yaw = np.radians(yaw_d)
        R, t = look_at(target + 520.0 * np.array([np.sin(yaw), 0.0, np.cos(yaw)]), target)
        c = Camera(f=1100.0, cx=240.0, cy=280.0, width=480, height=560, R=R, t=t)
        r = cs.Render(c.K, c.R, c.t, c.width, c.height, np.full((len(names), 2), np.nan))
        for i, nm in enumerate(names):
            if cs.visible_in(r, surf, *truth[nm]):
                r.uv[i] = c.project(surf.point(*truth[nm])[None])[0]
        renders.append(r)

    # 4 renders: w = 2/3, so the shrink (about 1 mm) is well above the 0.3 mm tolerance
    new_kit, rep = cs.calibrate(kit, renders, sch)
    checked = 0
    for p in rep["points"]:
        nm = p["name"]
        if nm.startswith("iris") or p["n"] != 4:
            continue
        w = p["w"]
        assert w == pytest.approx(4.0 / 6.0)
        p_true = surf.point(*truth[nm])
        expect = P0[nm] + w * (p_true - P0[nm])
        got = new_kit.landmark_positions("calib_test", names=[nm])[0]
        e_shr, e_raw = np.linalg.norm(got - expect), np.linalg.norm(got - p_true)
        assert e_shr < 0.3 and e_raw > 0.6 and e_shr < e_raw, (nm, e_shr, e_raw)
        assert p["verified"] is False                          # n < 20
        checked += 1
    assert checked >= 20
    assert rep["lr_resolved"] == {"iris_a": "L", "iris_b": "R"}

    # 1 render: w = 1/3 pulls the embedding back toward the provisional side; the side still follows
    # the detections and the result is flagged (unexpected side, too few renders)
    _, rep1 = cs.calibrate(kit, renders[:1], sch)
    assert rep1["lr_resolved"] == {"iris_a": "L", "iris_b": "R"}
    g1 = {g["name"]: g for g in rep1["lr_groups"]}
    for gname in ("iris_a", "iris_b"):
        assert {"lr_unexpected", "lr_low_n"} <= set(g1[gname]["flags"]) and g1[gname]["n_min"] == 1
    by1 = {p["name"]: p for p in rep1["points"]}
    assert by1["iris_a_centre"]["w"] == pytest.approx(1.0 / 3.0) and "lr_low_n" in by1["iris_a_centre"]["flags"]


def test_calibrate_refuses_non_template_records(tmp_path):
    cs = _tool("calibrate_scheme")
    rec = tmp_path / "records.json"
    rec.write_text(json.dumps({"format": "face3d.render_records", "version": 1, "source": "photos", "renders": []}))
    with pytest.raises(cs.CalibrationError, match="template"):
        cs.load_records(rec, load_scheme("anatomical44"))


# =========================================================================== 4. prior recalibration
ANSUR_COLS = ("headcircumference", "headlength", "headbreadth", "bizygomaticbreadth", "mentonsellionlength",
              "interpupillarybreadth", "earlength", "tragiontopofhead")


def _ansur_truth():
    """Known per-sex within-group covariance and three group means (synthetic, not ANSUR data)."""
    mean = {"M": np.array([572.0, 198.0, 154.0, 142.0, 123.0, 64.5, 64.0, 131.0]),
            "F": np.array([551.0, 189.0, 147.0, 133.0, 114.0, 61.5, 59.5, 127.0])}
    sd = {"M": np.array([15.0, 6.6, 5.3, 5.0, 6.8, 3.5, 3.6, 4.5]),
          "F": np.array([14.0, 6.3, 5.0, 4.6, 5.2, 3.3, 3.4, 4.3])}
    p = len(ANSUR_COLS)
    Rm = np.full((p, p), 0.3)
    Rm[np.ix_([1, 2, 3], [1, 2, 3])] = 0.5
    np.fill_diagonal(Rm, 1.0)
    shifts = [np.zeros(p), np.array([0.3, 0.5, 0.5, 0.4, 0.0, 0.2, 0.0, 0.3]),
              np.array([-0.2, 2.5, -0.8, 0.0, 0.6, 0.0, 0.5, -0.4])]
    sizes = (1100, 600, 300)
    out = {}
    for s in ("M", "F"):
        Sw = Rm * np.outer(sd[s], sd[s])
        mus = [mean[s] + sh * sd[s] for sh in shifts]
        mubar = np.mean(mus, axis=0)
        St = Sw + np.mean([np.outer(m - mubar, m - mubar) for m in mus], axis=0)
        out[s] = {"Sw": Sw, "mus": mus, "Sigma": St, "sizes": sizes}
    return out


def _write_ansur_csv(path: Path, truth: dict, seed: int = 7, scale: dict | None = None) -> None:
    rng = np.random.default_rng(seed)
    scale = scale or {}
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subjectid", "Gender", "DODRace"] + list(ANSUR_COLS))
        sid = 0
        for s, label in (("M", "Male"), ("F", "Female")):
            Lc = np.linalg.cholesky(truth[s]["Sw"])
            for g, (mu, n) in enumerate(zip(truth[s]["mus"], truth[s]["sizes"])):
                # exact-moment draws: sample mean mu and sample covariance Sw (ddof=1), so the test
                # checks the tool's pooling arithmetic, not sampling luck
                Z = rng.standard_normal((n, len(ANSUR_COLS)))
                Z -= Z.mean(axis=0)
                Z = Z @ np.linalg.inv(np.linalg.cholesky(np.cov(Z, rowvar=False))).T
                X = mu + Z @ Lc.T
                for row in X:
                    sid += 1
                    vals = [f"{v * scale.get(c, 1.0):.2f}" for c, v in zip(ANSUR_COLS, row)]
                    w.writerow([sid, label, g + 1] + vals)


def _walk_keys(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.append(str(k))
            _walk_keys(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_keys(v, out)
    elif isinstance(obj, str):
        out.append(obj)
    return out


@needs_metric
def test_recalibrate_ansur_synthetic(tmp_path):
    rp = _tool("recalibrate_prior")
    truth = _ansur_truth()
    csv_path = tmp_path / "ansur_synthetic.csv"
    _write_ansur_csv(csv_path, truth)
    out = tmp_path / "prior_v2.json"
    assert rp.main(["--ansur", str(csv_path), "--licence", "CC0-1.0", "--out", str(out), "--date", "2026-11-21"]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    stats = doc["recalibration"]["statistics"]
    for s in ("M", "F"):
        st = stats[s]
        assert st["n"] == 2000 and st["n_groups_pooled"] == 3
        cols = st["columns"]
        order = [cols.index(c) for c in ANSUR_COLS]
        sd = np.array(st["sd_mm"])[order]
        corr = np.array(st["corr"])[np.ix_(order, order)]
        S = truth[s]["Sigma"]
        sd_true = np.sqrt(np.diag(S))
        assert np.all(np.abs(sd / sd_true - 1.0) < 0.05), (s, sd / sd_true)
        assert np.abs(corr - S / np.outer(sd_true, sd_true)).max() < 0.05
        assert np.all(np.abs(sd / sd_true - 1.0) < 2e-3)        # exact up to the CSV's 0.01 mm rounding
        # balanced pooling differs from naive (size-weighted) pooling on headlength by > 5 %
        sizes = np.array(truth[s]["sizes"], float) / sum(truth[s]["sizes"])
        mus = np.array(truth[s]["mus"])
        mbar = sizes @ mus
        naive = truth[s]["Sw"] + sum(wg * np.outer(m - mbar, m - mbar) for wg, m in zip(sizes, mus))
        j = ANSUR_COLS.index("headlength")
        assert abs(np.sqrt(naive[j, j]) / sd_true[j] - 1.0) > 0.05
        assert abs(sd[j] / sd_true[j] - 1.0) < 0.03
    # no race-conditioned output anywhere
    words = " ".join(_walk_keys(doc, [])).lower()
    for bad in ("race", "ancestry", "ethnic"):
        assert bad not in words
    assert set(doc["sexes"]) == {"M", "F"}
    prov = doc["provenance"]
    assert prov["badge"] == "\U0001F4C4" and prov["n"] == {"M": 2000, "F": 2000} and prov["date"] == "2026-11-21"
    assert prov["files"][0]["sha256"] == hashlib.sha256(csv_path.read_bytes()).hexdigest()
    assert doc["version"] == 1 and doc["data_version"] == 2
    # means and loadings kept; sigmas moved toward the new targets; the file loads as a prior
    v1 = load_prior_package()
    pkg = load_prior_package(out)
    for s in ("M", "F"):
        assert np.allclose(pkg["sexes"][s]["mean"], v1["sexes"][s]["mean"], atol=1e-6)
        assert np.allclose(pkg["sexes"][s]["loadings"], v1["sexes"][s]["loadings"], atol=1e-6)
        rows = doc["recalibration"]["targets"][s]
        assert len(rows) == 7
        mis = {v: sum(((r[f"model_sd_{v}_mm"] - r["ansur_sd_mm"]) / r["ansur_sd_mm"]) ** 2 for r in rows)
               for v in ("v1", "v2")}
        assert mis["v2"] < mis["v1"], mis                         # the refit moves toward the new targets
    prior = FactorPrior.from_package(path=out, sex="male", population="matched", include_size=True,
                                     extra_depth_sigma_mm=0.0, rigid_invariance=False, tragion_floor=False)
    hb = next(r for r in doc["recalibration"]["targets"]["M"] if r["csv_column"] == "headbreadth")
    assert prior.chord_sd("eu_L", "eu_R") == pytest.approx(hb["model_sd_v2_mm"], rel=1e-3)
    sc = doc["recalibration"]["scale_sigma_log"]
    assert doc["defaults"]["scale_sigma_log"] == sc["proposed"] and 0.02 < sc["proposed"] < 0.08

    # implausible units refused; 0.1 mm units accepted and rescaled
    bad = tmp_path / "bad.csv"
    _write_ansur_csv(bad, truth, scale={"headlength": 100.0})
    assert rp.main(["--ansur", str(bad), "--licence", "CC0-1.0", "--out", str(tmp_path / "x.json")]) == 2
    assert not (tmp_path / "x.json").exists()
    tenth = tmp_path / "tenth.csv"
    _write_ansur_csv(tenth, truth, scale={"headlength": 10.0})
    doc10 = rp.build_from_ansur([tenth], licence="CC0-1.0", date="2026-11-21")
    assert doc10["provenance"]["unit_scale"]["headlength"] == 0.1
    j = doc10["recalibration"]["statistics"]["M"]["columns"].index("headlength")
    assert doc10["recalibration"]["statistics"]["M"]["sd_mm"][j] == pytest.approx(
        doc["recalibration"]["statistics"]["M"]["sd_mm"][j], rel=0.05)


def test_recalibrate_port_reproduces_packaged_sigmas():
    """The ported build_lm.calibrate with the original targets reproduces the v1 factor sigmas."""
    rp = _tool("recalibrate_prior")
    pkg = load_prior_package()
    for s in ("M", "F"):
        sig = rp.calibrate_sigmas(pkg["sexes"][s]["mean"], pkg["ids"], pkg["sexes"][s]["loadings"],
                                  pkg["factor_names"], pkg["residual_cov"], rp.default_targets(s))
        assert np.abs(sig - pkg["sexes"][s]["factor_sigma"]).max() < 0.006


def test_recalibrate_from_landmark_samples(tmp_path):
    rp = _tool("recalibrate_prior")
    pkg = load_prior_package()
    ids = pkg["ids"]
    mu = pkg["sexes"]["M"]["mean"]
    L_true = pkg["sexes"]["M"]["loadings"] * pkg["sexes"]["M"]["factor_sigma"][None, :]   # a known 18-factor model
    psi_true = np.maximum(pkg["residual_total"].reshape(-1), 0.5) ** 2
    rng = np.random.default_rng(21)
    S = 3000
    Y = mu.reshape(-1) + rng.standard_normal((S, 18)) @ L_true.T + rng.standard_normal((S, 132)) * np.sqrt(psi_true)
    npz = tmp_path / "samples.npz"
    np.savez(npz, samples=Y.reshape(S, 44, 3), ids=np.array(ids))
    out = tmp_path / "prior_samples.json"
    assert rp.main(["--landmark-samples", str(npz), "--licence", "CC-BY-4.0", "--attribution",
                    "Synthetic samples from a known factor model (test)", "--out", str(out),
                    "--date", "2026-11-21"]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["attribution"].startswith("Synthetic") and doc["licence"] == "CC-BY-4.0"
    assert len(doc["factor_names"]) == 18 and doc["provenance"]["n"] == {"M": S, "F": S}
    assert min(doc["residual_total"][i][a] for i in range(44) for a in range(3)) >= 0.3 - 1e-9
    fit = FactorPrior.from_package(path=out, sex="male", population="matched", include_size=True,
                                   extra_depth_sigma_mm=0.0, rigid_invariance=False, tragion_floor=False)
    true = FactorPrior(mu, L_true, np.diag(psi_true), ids=ids)
    T = json.loads(RESEARCH_METRIC.read_text())["tables"] if RESEARCH_METRIC.is_file() else None
    chords = ([r[0].split("-") for r in next(t for t in T if t["name"] == "model_vs_norm_chords")["rows"]]
              if T else [["en_L", "en_R"], ["zy_L", "zy_R"], ["g", "op"], ["n", "me"], ["sa_L", "sba_L"]])
    for a, b in chords:
        assert fit.chord_sd(a, b) == pytest.approx(true.chord_sd(a, b), rel=0.05), (a, b)
    # metres are refused with a hint
    np.savez(tmp_path / "m.npz", samples=Y.reshape(S, 44, 3) / 1000.0)
    with pytest.raises(rp.RecalibrationError, match="metres"):
        rp.build_from_samples(tmp_path / "m.npz", licence="CC-BY-4.0", attribution="x", date="2026-11-21")
    with pytest.raises(rp.RecalibrationError, match="attribution"):
        rp.build_from_samples(npz, licence="CC-BY-4.0", attribution="  ", date="2026-11-21")


def _to_fh_frame(X: np.ndarray, ix: dict) -> np.ndarray:
    """Re-express one sample (44, 3) in its own FH frame (research head_frame_definition, 'renormalise')."""
    tL, tR = X[ix["t_L"]], X[ix["t_R"]]
    o = 0.5 * (tL + tR)
    x = (tL - tR) / np.linalg.norm(tL - tR)
    a = 0.5 * (X[ix["or_L"]] + X[ix["or_R"]]) - o                # FH plane through both tragia and mid-orbitale
    z = a - (a @ x) * x
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    z = np.cross(x, y)
    return (X - o) @ np.stack([x, y, z]).T


def test_recalibrate_samples_in_fh_frame(tmp_path):
    """Regression: samples really in the FH frame have t_L.y/z and t_R.y/z fixed at zero; they are accepted,
    the 0.3 mm residual floor holds on the mm scale and the prior loads without the tragion floor."""
    rp = _tool("recalibrate_prior")
    pkg = load_prior_package()
    ids = pkg["ids"]
    ix = {k: i for i, k in enumerate(ids)}
    mu = pkg["sexes"]["M"]["mean"]
    L_true = pkg["sexes"]["M"]["loadings"] * pkg["sexes"]["M"]["factor_sigma"][None, :]
    psi_true = np.maximum(pkg["residual_total"].reshape(-1), 0.5) ** 2
    rng = np.random.default_rng(21)
    S = 3000
    Y = (mu.reshape(-1) + rng.standard_normal((S, 18)) @ L_true.T
         + rng.standard_normal((S, 132)) * np.sqrt(psi_true)).reshape(S, 44, 3)
    Yfh = np.stack([_to_fh_frame(s, ix) for s in Y])
    tr = [ix["t_L"], ix["t_R"]]
    assert np.abs(Yfh[:, tr, 1:]).max() < 1e-9                  # frame-fixed (floating-point zeros)
    exact = Yfh.copy()
    exact[:, tr, 1:] = 0.0                                       # exactly zero, as a pipeline may write them
    true = FactorPrior(mu, L_true, np.diag(psi_true), ids=ids)
    for label, data in (("float", Yfh), ("exact", exact)):
        npz = tmp_path / f"fh_{label}.npz"
        np.savez(npz, samples=data, ids=np.array(ids))
        doc = rp.build_from_samples(npz, licence="CC-BY-4.0", attribution="synthetic FH-frame samples (test)",
                                    date="2026-11-21")
        rt = np.array(doc["residual_total"])
        assert rt.min() >= 0.3 - 1e-9, (label, rt.min())
        assert doc["recalibration"]["frame_fixed_coordinates"] == ["t_L.y", "t_L.z", "t_R.y", "t_R.z"]
        for s in ("M", "F"):
            load = np.array(doc["sexes"][s]["loadings"]).reshape(44, 3, -1)
            assert np.all(load[tr, 1:] == 0.0)
        out = tmp_path / f"fh_{label}.json"
        rp.write(doc, out)
        fit = FactorPrior.from_package(path=out, sex="male", population="matched", include_size=True,
                                       extra_depth_sigma_mm=0.0, rigid_invariance=False, tragion_floor=False)
        for a, b in (("en_L", "en_R"), ("zy_L", "zy_R"), ("g", "op"), ("n", "me"), ("t_L", "t_R")):
            assert fit.chord_sd(a, b) == pytest.approx(true.chord_sd(a, b), rel=0.05), (label, a, b)


def test_principal_factors_floor_on_mm_scale():
    """A coordinate whose total SD is below the floor still gets the full 0.3 mm residual SD."""
    rp = _tool("recalibrate_prior")
    rng = np.random.default_rng(4)
    p, K = 12, 2
    L = rng.normal(0.0, 2.0, (p, K))
    L[3] *= 0.02                                                 # tiny loadings: total SD about 0.1 mm
    psi = np.full(p, 1.0)
    psi[3] = 0.05 ** 2
    C = L @ L.T + np.diag(psi)
    C[7, :] = C[:, 7] = 0.0                                      # a frame-fixed coordinate
    assert np.sqrt(C[3, 3]) < 0.3
    Lf, psi_f = rp.principal_factors(C, K)
    assert np.all(psi_f >= 0.3 ** 2 - 1e-12)
    assert psi_f[7] == pytest.approx(0.09) and np.all(Lf[7] == 0.0)
    free = np.arange(p) != 3
    free[7] = False
    fit = Lf @ Lf.T + np.diag(psi_f)
    assert np.allclose(fit[np.ix_(free, free)], C[np.ix_(free, free)], rtol=0.05, atol=0.15)
