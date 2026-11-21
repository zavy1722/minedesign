import ast
import itertools
import pathlib
from dataclasses import fields, replace

import numpy as np

from face3d.core import config
from face3d.io.exif import ExifInfo
from face3d.qa import image_stats as ims
from face3d.qa import overlay_geom as og
from face3d.qa import palette as pal
from face3d.qa.checks import (Finding, PhotoContext, occluder_actions, retouch_findings,
                              run_photo_checks, run_set_checks)
from face3d.io.heif import HeifInfo

W, H = 4000, 3000


def clean(pid="a", **kw):
    ex = ExifInfo(make="Acme", model="X1", focal_35mm=26.0, width=W, height=H,
                  datetime_original="2024:05:01 10:00:00", software="Camera 1.0",
                  digital_zoom_ratio=1.0, custom_rendered=0)
    rng = np.random.default_rng(1)
    rgb = rng.uniform(0.2, 0.7, (40, 40, 3))
    base = dict(photo_id=pid, exif=ex, width=W, height=H, face_px=800.0,
                face_centre_px=np.array([2000.0, 1500.0]), iris_px=40.0,
                solved_distance_mm=1500.0, f_px=3000.0, image_rgb=rgb,
                skin_mask=np.ones((40, 40), bool), face_scores=[0.99], view_rms_sigma=1.0,
                roll_deg=0.0)
    base.update(kw)
    return PhotoContext(**base)


def codes(ctx):
    return {f.code for f in run_photo_checks(ctx)}


def _ex(**kw):
    return replace(clean().exif, **kw)


def test_each_gate_fires_on_fixture_and_silent_on_clean():
    c = clean()
    assert [f for f in run_photo_checks(c) if f.severity != "info"] == []
    sat = np.ones((40, 40, 3)) * 0.5
    sat[:10] = 1.0
    eye_open = np.array([[0, 0], [1, 1], [2, 1], [3, 0], [2, -1], [1, -1]], float)
    eye_shut = eye_open * np.array([1, 0.1])
    cases = {
        "Q-ORIENT": clean(orientation_applied=False),
        "Q-EXIF-NONE": clean(exif=None),
        "Q-CROP": clean(exif=_ex(digital_zoom_ratio=2.0)),
        "Q-FRONTCAM": clean(exif=_ex(lens_model="front camera 2.2mm")),
        "Q-NEAR": clean(solved_distance_mm=700.0),
        "Q-WIDE": clean(exif=_ex(focal_35mm=14.0)),
        "Q-PROCESS": clean(exif=_ex(software="Adobe PHOTOSHOP 25")),
        "Q-SMALL": clean(face_px=100.0),
        "Q-BLINK": clean(eye_pts6={"L": eye_shut, "R": eye_open}),
        "Q-CLIP": clean(image_rgb=sat),
        "Q-FACES": clean(n_faces=2, face_scores=[0.9, 0.7]),
        "Q-CONSENT": clean(consent_ok=False),
    }
    for code, ctx in cases.items():
        assert codes(ctx) == {code}, (code, codes(ctx))
    assert codes(clean(view_rms_sigma=5.0, roll_deg=88.0)) == {"Q-ORIENT"}
    assert codes(clean(view_rms_sigma=5.0, roll_deg=30.0)) == set()
    assert codes(clean(exif=_ex(custom_rendered=1))) == {"Q-PROCESS"}
    assert codes(clean(exif=_ex(width=4000, height=2250))) == {"Q-CROP"}
    assert codes(clean(face_centre_px=np.array([3900.0, 2900.0]))) == {"Q-WIDE"}
    assert codes(clean(face_centre_px=np.array([3000.0, 1500.0]), f_px=1500.0)) == {"Q-WIDE"}
    assert codes(clean(iris_px=10.0)) == {"Q-SMALL"}
    assert codes(clean(n_faces=2, face_scores=[0.9, 0.3])) == set()
    sev = {f.severity for f in run_photo_checks(clean(face_px=100.0))}
    assert sev == {"block"}
    near = {d: run_photo_checks(clean(solved_distance_mm=d))[0] for d in (900.0, 700.0, 500.0)}
    assert [near[d].action for d in (900.0, 700.0, 500.0)] == ["down_weight", "down_weight",
                                                               "exclude_geometry"]
    assert near[700.0].threshold == 800.0


def test_alarm_budget_clean_set():
    rng = np.random.default_rng(7)
    total = 0
    for i in range(20):
        ctx = clean(f"p{i}", face_px=float(rng.uniform(300, 1500)),
                    solved_distance_mm=float(rng.uniform(1000, 3000)),
                    face_centre_px=np.array([rng.uniform(1500, 2500), rng.uniform(1100, 1900)]),
                    exif=_ex(focal_35mm=float(rng.choice([24, 26, 50, 85]))))
        total += sum(f.severity != "info" for f in run_photo_checks(ctx))
    assert total <= 2


def test_set_checks_blur_dates_group_spread():
    rng = np.random.default_rng(0)
    sharp = rng.uniform(0, 1, (64, 64))
    blurred = ims.gaussian_blur(sharp, 2.0)
    ctxs = [clean("s1", image_gray=sharp, skin_mask=None), clean("s2", image_gray=sharp.copy(), skin_mask=None),
            clean("b", image_gray=blurred, skin_mask=None)]
    fs = run_set_checks(ctxs)
    assert [(f.code, f.photo_id) for f in fs] == [("Q-BLUR", "b")]
    old = clean("o", exif=_ex(datetime_original="2020:01:01 00:00:00"))
    fs = run_set_checks([clean("n1"), clean("n2"), old])
    d = [f for f in fs if f.code == "Q-DATES"]
    assert len(d) == 1 and d[0].value == 2
    assert d[0].detail["clusters"]["o"] != d[0].detail["clusters"]["n1"]
    assert d[0].detail["clusters"]["n1"] == d[0].detail["clusters"]["n2"]
    assert not [f for f in run_set_checks([clean("n1"), clean("n2")])]
    g = run_set_checks([clean("a"), clean("b", exif=_ex(focal_35mm=28.0))])
    assert [f.code for f in g] == ["Q-GROUP-SPREAD"]
    g = run_set_checks([clean("a"), clean("b", exif=_ex(focal_35mm=26.5))])
    assert g == []


def test_findings_complete_and_registered():
    ctx = clean(orientation_applied=False, exif=_ex(digital_zoom_ratio=2.0, software="gimp",
                                                    lens_model="front"),
                solved_distance_mm=500.0, face_px=100.0, iris_px=5.0, consent_ok=False,
                n_faces=2, face_scores=[1.0, 0.8])
    fs = run_photo_checks(ctx)
    assert {f.code for f in fs} >= {"Q-ORIENT", "Q-CROP", "Q-PROCESS", "Q-NEAR", "Q-SMALL",
                                    "Q-FACES", "Q-CONSENT", "Q-FRONTCAM"}
    names = {f.name for f in fields(Finding)}
    assert names >= {"code", "severity", "value", "threshold", "action", "msg_key", "fix_key",
                     "source", "badge", "photo_id"}
    for f in fs:
        assert f.severity in ("info", "warn", "block")
        assert f.action in ("down_weight", "drop_class", "exclude_geometry", "exclude_texture",
                            "ask", "none")
        assert f.msg_key and f.fix_key and f.source and f.badge in config.BADGES
        assert f.photo_id == "a"
    qa = [k for k in config._REGISTRY if k.startswith("qa.")]
    assert len(qa) >= 20
    for k in qa:
        d = config.get(k)
        assert d.badge in config.BADGES and d.source
    for f in fs:
        if isinstance(f.threshold, float):
            assert f.threshold in {config.get(k).value for k in qa}


def test_image_stats_known_values():
    p = np.array([[0, 0], [1, 2], [3, 2], [4, 0], [3, -2], [1, -2]], float)
    assert abs(ims.eye_aspect_ratio(p) - (4 + 4) / (2 * 4)) < 1e-12
    p2 = np.array([[0, 0], [1, 1], [2, 1], [4, 0], [2, -1], [1, -1]], float)
    assert abs(ims.eye_aspect_ratio(p2) - 4 / 8) < 1e-12
    yy, xx = np.mgrid[0:32, 0:32]
    cb = ((yy + xx) % 2).astype(float)
    assert ims.laplacian_variance(cb) > ims.laplacian_variance(ims.gaussian_blur(cb, 1.0)) > 0
    assert ims.laplacian_variance(np.ones((8, 8))) == 0.0
    m = np.zeros((32, 32), bool)
    m[:, :16] = True
    assert ims.laplacian_variance(cb, m) > 0
    assert np.allclose(ims.gaussian_blur(np.full((9, 9), 3.0), 2.0), 3.0)
    assert np.allclose(ims.box_blur(np.full((9, 9), 3.0), 2), 3.0)
    img = np.full((4, 4, 3), 0.5)
    img[0, 0, 1] = 1.0
    assert ims.clipped_fraction(img, np.ones((4, 4), bool)) == 1 / 16
    rng = np.random.default_rng(0)
    tex = rng.uniform(0, 1, (64, 64))
    smooth = tex.copy()
    cheek = np.zeros((64, 64), bool)
    cheek[:, :32] = True
    smooth[:, :32] = ims.gaussian_blur(tex, 3.0)[:, :32]
    assert ims.skin_smoothness_index(smooth, cheek, ~cheek) < 0.5
    assert abs(ims.skin_smoothness_index(tex, cheek, cheek) - 1.0) < 1e-12


def test_sigma_ellipse_axes():
    e = og.sigma_ellipse((10.0, 20.0), np.diag([4.0, 1.0]), k=1.0)
    assert abs((e[:, 0].max() - e[:, 0].min()) / 2 - 2.0) < 1e-9
    assert abs((e[:, 1].max() - e[:, 1].min()) / 2 - 1.0) < 1e-9
    assert e.shape == (32, 2)
    assert abs(e[:, 0].mean() - 10.0) < 0.1


def test_overlay_misc():
    a = og.residual_arrow((11, 10), (10, 10), scale=5.0)
    assert np.allclose(a[0], [[10, 10], [15, 10]]) and len(a) == 2
    assert len(og.residual_arrow((1, 1), (1, 1))) == 1
    for k in ("circle", "square", "cross", "ring", "line", "hatch"):
        assert og.glyph(k, (0, 0), ui_scale=2.0)
    sq = np.array([[0, 0], [20, 0], [20, 20], [0, 20.0]])
    segs = og.hatch_polygon(sq, spacing_px=6, angle_deg=0.0)
    assert all(abs(s[0][1] - s[1][1]) < 1e-9 and abs(abs(s[1][0] - s[0][0]) - 20) < 1e-9
               for s in segs) and len(segs) == 4
    # concave U shape: hatch line through the notch yields two segments
    u = np.array([[0, 0], [30, 0], [30, 30], [20, 30], [20, 10], [10, 10], [10, 30], [0, 30.0]])
    row = [s for s in og.hatch_polygon(u, spacing_px=6, angle_deg=0.0) if abs(s[0][1] - 18) < 1e-9]
    assert len(row) == 2
    st = og.styled([np.array([[0, 0], [1, 1.0]])], "user_pin")
    assert [(w, c) for _, w, c in st] == [(6.0, "#FFFFFF"), (4.0, "#000000"), (2.0, "#E69F00")]
    assert og.blur_sigma_px(200) == 6.0
    assert og.thumbnail_shape(300, 600) == (32, 64)
    assert (og.HIT_RADIUS_PX, og.MIN_TARGET_PX) == (12, 24)


def test_palette_cvd_separation():
    cols = {r: pal.hex_to_rgb(c) for r, (c, _) in pal.ROLES.items()}
    shapes = {r: s for r, (_, s) in pal.ROLES.items()}
    expected_min = {None: 33.0, "protan": 20.6, "deutan": 17.0, "tritan": 16.0}
    for kind in (None, "protan", "deutan", "tritan"):
        sim = {r: c if kind is None else pal.simulate_cvd(c, kind) for r, c in cols.items()}
        des = [(a, b, pal.delta_e76(sim[a], sim[b])) for a, b in itertools.combinations(sim, 2)]
        assert min(d for *_, d in des) >= max(15.0, expected_min[kind] - 0.5)
        for a, b, d in des:
            if shapes[a] == shapes[b]:
                assert d >= 20.0
    for r, (c, _) in pal.ROLES.items():
        assert max(pal.contrast_ratio(c, pal.OUTLINE), pal.contrast_ratio(c, pal.HALO)) >= 3.0
    assert abs(pal.contrast_ratio("#000000", "#FFFFFF") - 21.0) < 1e-9
    assert abs(pal.delta_e76("#000000", "#FFFFFF") - 100.0) < 1e-3
    assert len(pal.RESIDUAL_BINS) == 4


def test_occluder_actions():
    a = occluder_actions({"glasses", "beard", "hair", "makeup"})
    assert a["sigma_mult"]["eye"] == 2.0 and a["sigma_mult"]["lip_border"] == 2.0
    assert {"pg", "gn", "me", "ear", "temple"} <= set(a["drop_classes"])
    assert a["flags"]["contour_kind"] == "outer_bound"
    assert occluder_actions(set()) == {"sigma_mult": {}, "drop_classes": [], "flags": {}}


def test_overlay_geom_no_bpy_import():
    root = pathlib.Path(__file__).resolve().parents[1] / "face3d" / "qa"
    for f in root.glob("*.py"):
        for node in ast.walk(ast.parse(f.read_text())):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                mods = [node.module or ""]
            for m in mods:
                assert m.split(".")[0] not in ("bpy", "mathutils", "gpu", "gpu_extras", "blf"), (f, m)


def _ph(w, h, **kw):
    ex = ExifInfo(make="Apple", model="iPhone 15", focal_35mm=26.0, width=w, height=h,
                  datetime_original="2024:05:01 10:00:00", software="Camera 1.0",
                  digital_zoom_ratio=1.0, custom_rendered=0)
    return clean(exif=replace(ex, **kw.pop("exif_kw", {})), width=w, height=h,
                 face_centre_px=np.array([w / 2.0, h / 2.0]), **kw)


def test_crop_non_native_aspect_and_heif_clap():
    assert codes(_ph(4032, 3024)) == set()
    assert codes(_ph(4032, 2268)) == {"Q-CROP"}          # 16:9 with matching EXIF dims
    assert codes(_ph(3024, 3024)) == {"Q-CROP"}          # 1:1
    assert codes(_ph(4500, 3000)) == {"Q-CROP"}          # 3:2 is non-native on a phone
    assert codes(_ph(3000, 1000, exif_kw={"width": None, "height": None})) == {"Q-CROP"}
    ctx = _ph(4032, 3024)
    ctx.heif = HeifInfo(clap={"width_n": 3000, "width_d": 1})
    f = [x for x in run_photo_checks(ctx) if x.code == "Q-CROP"]
    assert len(f) == 1 and "heif_clap" in f[0].detail["reasons"]
    dslr = clean(width=6000, height=4000, exif=_ex(make="Canon", width=6000, height=4000))
    assert "Q-CROP" not in codes(dslr)
    f = [x for x in run_photo_checks(_ph(3024, 3024)) if x.code == "Q-CROP"][0]
    assert f.threshold == 0.02 and f.detail["sigma_logf"] == 0.09
    z = [x for x in run_photo_checks(clean(exif=_ex(digital_zoom_ratio=2.0)))][0]
    assert z.threshold == 1.0 and z.detail["sigma_logf"] == 0.06


def test_group_mode_zoom_detector():
    def c(pid, f35, fl):
        return clean(pid, exif=_ex(focal_35mm=f35, focal_length_mm=fl))
    fs = run_set_checks([c("a", 26.0, 6.0), c("b", 26.0, 6.0), c("z", 31.2, 6.0)])
    z = [f for f in fs if f.code == "Q-CROP"]
    assert [f.photo_id for f in z] == ["z"] and z[0].value > 1.02
    assert not [f for f in run_set_checks([c("a", 26.0, 6.0), c("b", 26.2, 6.0)]) if f.code == "Q-CROP"]


def test_clip_dtypes_and_alpha():
    m = np.ones((10, 10), bool)
    assert "Q-CLIP" not in codes(clean(image_rgb=np.full((10, 10, 3), 30000, np.uint16), skin_mask=m))
    assert "Q-CLIP" not in codes(clean(image_rgb=np.full((10, 10, 3), 200, np.int64), skin_mask=m))
    rgba = np.full((10, 10, 4), 100, np.uint8)
    rgba[..., 3] = 255
    assert "Q-CLIP" not in codes(clean(image_rgb=rgba, skin_mask=m))
    assert "Q-CLIP" in codes(clean(image_rgb=np.full((10, 10, 3), 65535, np.uint16), skin_mask=m))
    try:
        run_photo_checks(clean(image_rgb=np.zeros((10, 10)), skin_mask=m))
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_degenerate_eye_points_not_blink():
    z = {"L": np.zeros((6, 2)), "R": np.zeros((6, 2))}
    assert np.isnan(ims.eye_aspect_ratio(np.zeros((6, 2))))
    assert "Q-BLINK" not in codes(clean(eye_pts6=z))


def test_wide_off_axis_uses_exif_focal():
    ex = _ex(focal_35mm=20.0)
    ctx = clean(exif=ex, f_px=None, face_centre_px=np.array([2000.0 + 1200.0, 1500.0]))
    f = [x for x in run_photo_checks(ctx) if x.code == "Q-WIDE"]
    assert len(f) == 1 and abs(f[0].value - 27.4) < 0.5


def test_findings_threshold_and_levels():
    n = {d: run_photo_checks(clean(solved_distance_mm=d))[0] for d in (900.0, 700.0)}
    assert n[900.0].detail["level"] == "warn" and n[700.0].detail["level"] == "strong"
    o = run_photo_checks(clean(orientation_applied=False))[0]
    assert o.threshold is None


def test_cfg_overrides_reach_checks():
    ctx = clean(solved_distance_mm=1200.0)
    assert codes(ctx) == set()
    assert {f.code for f in run_photo_checks(ctx, cfg={"qa.near_warn_mm": 1500.0})} == {"Q-NEAR"}
    assert run_set_checks([clean("a"), clean("b", exif=_ex(focal_35mm=26.5))],
                          cfg={"qa.group_f35_spread": 0.01})


def test_retouch_findings():
    fs = retouch_findings({"a": 1.0, "b": 1.1, "c": 0.1})
    assert [f.photo_id for f in fs] == ["c"] and fs[0].action == "exclude_texture"
    assert retouch_findings({"a": 1.0}) == []
    assert retouch_findings({"a": 1.0, "b": 1.0}) == []


def test_ellipse_rotated_mahalanobis_and_arrow_head_blur_orient_makeup():
    th = 0.6
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    C = R @ np.diag([9.0, 1.0]) @ R.T
    e = og.sigma_ellipse((5.0, -3.0), C, k=2.0, n=64) - np.array([5.0, -3.0])
    m = np.einsum("ni,ij,nj->n", e, np.linalg.inv(C), e)
    assert np.allclose(m, 4.0)
    a = og.residual_arrow((10, 0), (0, 0), scale=1.0, head_px=6.0)
    head = a[1]
    assert np.allclose(head[1], [10, 0])
    for b in (head[0], head[2]):
        v = b - head[1]
        assert abs(np.linalg.norm(v) - 6.0) < 1e-9
        assert abs(np.degrees(np.arccos(-v[0] / np.linalg.norm(v))) - 25.0) < 1e-6
    assert head[0][1] * head[2][1] < 0
    d = np.zeros((41, 41))
    d[20, 20] = 1.0
    b = ims.gaussian_blur(d, 2.0)
    yy, xx = np.mgrid[0:41, 0:41]
    var = (b * (xx - 20) ** 2).sum()
    assert abs(var - 4.0) < 0.05
    assert "Q-ORIENT" in codes(clean(view_rms_sigma=5.0, roll_deg=-90.0))
    assert "Q-ORIENT" in codes(clean(view_rms_sigma=5.0, roll_deg=270.0))
    a = occluder_actions({"makeup"})
    assert a["sigma_mult"] == {"lip_border": 2.0, "brow_border": 2.0}
    g = occluder_actions({"glasses"})
    assert g["flags"]["no_iris_scale"] and "lid_points_under_frame" in g["drop_classes"]
