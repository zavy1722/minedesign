"""WP-11: surface test bed -- out-of-prior procedural subjects, expression fields, renders, faults.

Acceptance tests from docs/wbs.json (WP-11) plus supporting checks.
"""
from __future__ import annotations

import ast
import inspect
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pytest

from face3d.geometry import camera as camera_mod
from face3d.geometry.procrustes import apply_similarity, umeyama
from face3d.io.image_ops import orientation_point_map
from face3d.model.procedural_head import build_procedural_head
from face3d.synthetic import orbit_camera
from face3d.testbed import faults as F
from face3d.testbed import render as RD
from face3d.testbed import surface_subjects as SS

REPO = Path(__file__).resolve().parents[1]
FLIP = np.array([-1.0, 1.0, 1.0])


@pytest.fixture(scope="module")
def kit():
    return build_procedural_head()


@pytest.fixture(scope="module")
def subjects(kit):
    return [SS.out_of_prior_subject(kit, np.random.default_rng(1000 + s)) for s in range(20)]


def _swap_perm(names):
    idx = {n: i for i, n in enumerate(names)}
    out = []
    for n in names:
        if n.endswith("_L"):
            out.append(idx[n[:-2] + "_R"])
        elif n.endswith("_R"):
            out.append(idx[n[:-2] + "_L"])
        else:
            out.append(idx[n])
    return np.asarray(out)


# =========================================================================== subjects
def _resolved_imports(path: Path, package: str):
    """(module, names, in_type_checking) for every import statement of a module file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    tc_nodes = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and "TYPE_CHECKING" in ast.unparse(node.test):
            for sub in ast.walk(node):
                tc_nodes.add(id(sub))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.append((a.name, [], id(node) in tc_nodes))
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parts = package.split(".")
                base = ".".join(parts[: len(parts) - node.level + 1])
                mod = base + ("." + node.module if node.module else "")
            else:
                mod = node.module or ""
            out.append((mod, [a.name for a in node.names], id(node) in tc_nodes))
    return out


def test_surface_generator_independent_of_prior(kit):
    path = REPO / "face3d" / "testbed" / "surface_subjects.py"
    imports = _resolved_imports(path, "face3d.testbed")
    for mod, names, _tc in imports:
        full = [mod] + [f"{mod}.{n}" for n in names]
        assert not any(m.startswith("face3d.model.landmark_prior") for m in full), (mod, names)
    # Nothing from face3d.model at run time (a TemplateKit annotation is typing-only).
    runtime_model = [m for m, _n, tc in imports if m.startswith("face3d.model") and not tc]
    assert runtime_model == []
    # ... and importing the module does not load the prior.
    code = ("import sys, face3d.testbed.surface_subjects; "
            "print(any(m.startswith('face3d.model') for m in sys.modules))")
    res = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True, check=True)
    assert res.stdout.strip() == "False"
    sub = SS.out_of_prior_subject(kit, np.random.default_rng(7))
    assert sub.meta["inverse_crime"] is False
    assert sub.meta["generator"] == "out_of_prior_surface"


def test_out_of_prior_not_in_factor_span(kit, subjects):
    """Diagnostic: the anatomical landmarks leave > 0.5 mm RMS outside span(factors + similarity)."""
    from face3d.eval.align import similarity_tangent_basis
    from face3d.model.landmark_prior import FactorPrior

    names = kit.landmark_names("anatomical44")
    prior = FactorPrior.from_package(include_size=True, rigid_invariance=False, extra_depth_sigma_mm=6.0)
    assert list(prior.ids) == names
    mu = prior.mean()
    B = np.hstack([prior.L, similarity_tangent_basis(mu)])     # both sexes' factors, sex diff, depth, 7-DoF
    Q, _ = np.linalg.qr(B)
    rms = []
    for sub in subjects:
        X = sub.landmarks("anatomical44")
        s, R, t = umeyama(X, mu)
        d = (apply_similarity(X, s, R, t) - mu).reshape(-1)
        r = d - Q @ (Q.T @ d)
        rms.append(float(np.sqrt(np.mean(np.sum(r.reshape(-1, 3) ** 2, axis=1)))))
    assert np.mean(rms) > 0.5, rms


def test_subjects_no_folds_and_landmarks_follow_vertices(kit, subjects):
    tris = kit.triangles()
    for sub in subjects[:10]:
        V = sub.V_true
        assert V.shape == kit.vertices.shape and np.all(np.isfinite(V))
        ratios = SS.area_ratios(kit.vertices, V, tris)
        assert ratios.min() >= 0.2
        assert sub.meta["min_area_ratio"] == pytest.approx(ratios.min())
        vol = float(np.einsum("ij,ij->i", V[tris[:, 0]], np.cross(V[tris[:, 1]], V[tris[:, 2]])).sum() / 6.0)
        assert vol > 0
        # landmarks follow the vertices exactly (one-hot embeddings of the procedural kit)
        X = sub.landmarks("anatomical44")
        assert np.array_equal(X, kit.landmark_positions("anatomical44", V))
        lv = kit.landmark_vertices("anatomical44")
        assert np.array_equal(X, V[lv])
        assert np.array_equal(sub.landmarks("legacy_synthetic"), kit.landmark_positions("legacy_synthetic", V))
        # recorded asymmetry is the antisymmetric part of V_true; mirror RMSD = 2x
        A = SS.antisymmetric_part(V, kit.mirror_map)
        face = SS.face_hemisphere(kit)
        assert sub.asym_rms_mm == pytest.approx(float(np.sqrt(np.mean(np.sum(A[face] ** 2, 1)))))
        assert sub.meta["mirror_rmsd_mm"] == pytest.approx(2.0 * sub.asym_rms_mm)
        assert 0.6 < sub.asym_rms_mm < 1.0            # 0.8 mm target times the global scale
        s, _, _ = umeyama(kit.landmark_positions("anatomical44"), X)
        assert sub.log_scale_true == pytest.approx(math.log(s))
        assert abs(sub.log_scale_true) < 0.25
    # deterministic given the seed
    a = SS.out_of_prior_subject(kit, np.random.default_rng(1000))
    assert np.array_equal(a.V_true, subjects[0].V_true)
    # with asym_mm = 0 the subject is exactly mirror-symmetric
    sym = SS.out_of_prior_subject(kit, np.random.default_rng(5), asym_mm=0.0)
    assert np.abs(sym.V_true[kit.mirror_map] * FLIP - sym.V_true).max() < 1e-9
    assert sym.asym_rms_mm < 1e-9
    # features change the face (out-of-model components present)
    nf = SS.out_of_prior_subject(kit, np.random.default_rng(5), asym_mm=0.0, features=False)
    assert set(sym.meta["features"]) == {"dorsal_hump_mm", "chin_cleft_mm", "lip_curve_mm", "cheek_fullness_mm"}
    assert nf.meta["features"] == {}


def test_area_ratio_detects_folds(kit):
    tris = kit.triangles()
    V = kit.vertices.copy()
    assert np.allclose(SS.area_ratios(kit.vertices, V * 1.1, tris), 1.21)
    t = tris[100]
    V[t[0]] = V[t[1]] + V[t[2]] - V[t[0]]         # reflect one corner across the opposite edge
    assert SS.area_ratios(kit.vertices, V, tris)[100] < 0


def test_expression_fields(kit, subjects):
    sub = subjects[0]
    V = sub.V_true
    names = kit.landmark_names("anatomical44")
    lv = dict(zip(names, kit.landmark_vertices("anatomical44")))
    # zero amount is the identity
    for kind in SS.EXPRESSION_KINDS:
        assert np.array_equal(SS.expression_field(kit, V, kind, 0.0), V)
    # smile: corners up >= 0.6 a and outward; the back of the head does not move
    a = 3.0
    Vs, meta = SS.expression_field(kit, V, "smile", a, return_meta=True)
    assert meta["model_matched"] is False and meta["units"] == "mm"
    dL = Vs[lv["ch_L"]] - V[lv["ch_L"]]
    dR = Vs[lv["ch_R"]] - V[lv["ch_R"]]
    assert dL[1] >= 0.6 * a and dR[1] >= 0.6 * a
    assert dL[0] > 0.3 * a and dR[0] < -0.3 * a
    assert np.abs(Vs[lv["op"]] - V[lv["op"]]).max() < 1e-9
    # jaw_open: exact hinge rotation for weight-1 vertices, fixed for weight-0 ones.  The weights are
    # the jaw_open field (kit jaw weights smoothed and pinned to DESIGN 4.9 at the landmarks; review
    # of WP-11), no longer the raw kit weights.
    deg = 10.0
    Vj, meta = SS.expression_field(kit, V, "jaw_open", deg, return_meta=True)
    assert meta["model_matched"] is True and meta["units"] == "deg"
    T = sub.landmarks("anatomical44", ["t_L", "t_R"])
    c = 0.5 * (T[0] + T[1]) + np.array([0.0, -5.0, 11.5])
    assert np.allclose(meta["hinge_mm"], c)
    w, _info = SS.jaw_open_weights(kit)
    th = math.radians(deg)
    Rx = np.array([[1, 0, 0], [0, math.cos(th), -math.sin(th)], [0, math.sin(th), math.cos(th)]])
    full = np.flatnonzero(w == 1.0)
    assert full.size > 0
    assert np.abs(Vj[full] - ((V[full] - c) @ Rx.T + c)).max() < 1e-9
    zero = np.flatnonzero(w == 0.0)
    assert np.array_equal(Vj[zero], V[zero])
    assert Vj[lv["me"], 1] < V[lv["me"], 1]          # opening moves the chin down
    # on the rest kit the axis passes through (0, -5, 11.5) (mid-tragion is the origin)
    _, m0 = SS.expression_field(kit, kit.vertices, "jaw_open", 5.0, return_meta=True)
    assert np.allclose(m0["hinge_mm"], [0.0, -5.0, 11.5], atol=1e-9)
    # brow raise: the forehead region moves up by the amount
    Vb = SS.expression_field(kit, V, "brow_raise", 2.0)
    fh = kit.regions["forehead"]
    assert np.allclose(Vb[fh, 1] - V[fh, 1], 2.0)
    assert abs(Vb[lv["me"], 1] - V[lv["me"], 1]) < 1e-6
    # blink: the upper lid moves down (the full amount at ps and above it, on the ps column), nothing
    # at or below the pupil moves, and only vertical motion; fold-free at 2 mm
    Vk, km = SS.expression_field(kit, V, "blink", 2.0, return_meta=True)
    eyes = kit.regions["eyes"]
    pL = V[lv["p_L"]]
    psL = V[lv["ps_L"]]
    upper = eyes[(V[eyes, 1] >= psL[1]) & (np.abs(V[eyes, 0] - psL[0]) < 1e-9)]
    lower = eyes[(V[eyes, 1] <= pL[1]) & (V[eyes, 0] > 0)]
    assert upper.size and lower.size
    assert np.allclose(Vk[upper, 1] - V[upper, 1], -2.0)
    assert np.array_equal(Vk[lower], V[lower])
    dk = Vk - V
    assert np.all(dk[:, [0, 2]] == 0.0) and dk[:, 1].min() >= -2.0 - 1e-12 and dk[:, 1].max() <= 0.0
    assert SS.area_ratios(V, Vk, kit.triangles()).min() > 0.2
    assert km["min_area_ratio"] > 0.2 and km["fold_free_max_mm"] > 2.0
    with pytest.raises(ValueError):
        SS.expression_field(kit, V, "wink", 1.0)


def test_jaw_open_matches_design_hinge_at_landmarks(kit, subjects):
    """Regression (review of WP-11): jaw_open is labelled model_matched, so the landmark motion must be
    the DESIGN 4.9 hinge X + w_i (R_x(a)(X - c) - (X - c)) with the registry per-landmark weights, not
    the kit's per-vertex weights (which differ at go, ls, ch, li)."""
    from face3d.model.registry import ANATOMICAL

    names = kit.landmark_names("anatomical44")
    omega = np.array([ANATOMICAL[n].jaw_weight for n in names])
    # the hard-coded tables equal the registry (DESIGN 4.9) and the kit weights really differ there
    assert {b: SS.HINGE_LANDMARK_WEIGHTS.get(b, 0.0) for b in (ANATOMICAL[n].base for n in names)} == {
        ANATOMICAL[n].base: ANATOMICAL[n].jaw_weight for n in names}
    assert set(SS.RIGID_BASES) == {ANATOMICAL[n].base for n in names if ANATOMICAL[n].expr_class == "rigid"}
    lv = kit.landmark_vertices("anatomical44")
    assert np.abs(kit.jaw_weights[lv] - omega).max() > 0.5            # go: 0.365 in the kit vs 1.0
    w, info = SS.jaw_open_weights(kit)
    assert info["model_matched"] and info["conflicts"] == [] and info["pinned_vertices"] == len(names)
    assert np.array_equal(w[lv], omega) and w.min() >= 0.0 and w.max() <= 1.0
    assert np.allclose(w, w[kit.mirror_map], atol=1e-12)
    for sub in subjects[:3]:
        X = sub.landmarks("anatomical44")
        for deg in (5.0, 10.0, 15.0):
            Vj, meta = SS.expression_field(kit, sub.V_true, "jaw_open", deg, return_meta=True)
            assert meta["model_matched"] is True
            c = np.asarray(meta["hinge_mm"])
            th = math.radians(deg)
            Rx = np.array([[1, 0, 0], [0, math.cos(th), -math.sin(th)], [0, math.sin(th), math.cos(th)]])
            pred = X + omega[:, None] * ((X - c) @ Rx.T - (X - c))
            assert np.abs(kit.landmark_positions("anatomical44", Vj) - pred).max() < 1e-9
            d = meta["landmark_displacement_mm"]
            assert all(d[n] == 0.0 for n, o in zip(names, omega) if o == 0.0)
    # a hinge override or a kit without the anatomical scheme cannot claim the model match
    _, m2 = SS.expression_field(kit, subjects[0].V_true, "jaw_open", 10.0, hinge_mm=[0.0, -8.0, 12.0],
                                return_meta=True)
    assert m2["model_matched"] is False
    k2 = kit.replace(landmarks={k: v for k, v in kit.landmarks.items() if k != "anatomical44"})
    _, m3 = SS.expression_field(k2, kit.vertices, "jaw_open", 10.0, scheme="legacy_synthetic", return_meta=True)
    assert m3["model_matched"] is False and m3["jaw_weights"]["pinned_vertices"] == 0
    with pytest.raises(ValueError):
        SS.jaw_open_weights(kit, {"go": 1.5})


def test_jaw_open_fold_free(kit, subjects):
    """Regression (review of WP-11): the raw kit weights step 0 -> 1 across edges at z = -10 mm and fold
    the mesh under the jaw from ~5 deg; the jaw_open field keeps det J > 0.2 over the fault-matrix range."""
    tris = kit.triangles()
    w, _ = SS.jaw_open_weights(kit)
    e = kit.edges()
    jump_kit = np.abs(np.diff(kit.jaw_weights[e], axis=1))[:, 0]
    step = jump_kit > 0.5                                   # the kit's 0 -> 1 step edges at z = -10 mm
    assert step.sum() >= 10 and jump_kit.max() == 1.0
    assert np.abs(np.diff(w[e[step]], axis=1)).max() < 0.25
    for sub in subjects[:10]:
        Vj, meta = SS.expression_field(kit, sub.V_true, "jaw_open", 15.0, return_meta=True)
        r = SS.area_ratios(sub.V_true, Vj, tris)
        assert r.min() > 0.2
        assert meta["min_area_ratio"] == pytest.approx(r.min())


def test_expressions_hold_rigid_landmarks(kit, subjects):
    """Regression (review of WP-11): the smile's cheek lift, the blink ramp and the brow-raise falloff
    moved rigid-class landmarks (p, or, ex, zy, n) by up to 1.4 mm; the DESIGN 4.9 hard gate needs them still."""
    names = kit.landmark_names("anatomical44")
    rigid = [n for n in names if n.rstrip("_LR") in SS.RIGID_BASES or n in SS.RIGID_BASES]
    for sub in subjects[:3]:
        V = sub.V_true
        X = sub.landmarks("anatomical44")
        ix = {n: i for i, n in enumerate(names)}
        # smile: every rigid-class landmark exactly fixed; the corners still move up >= 0.6 a
        Vs, m = SS.expression_field(kit, V, "smile", 3.0, return_meta=True)
        Xs = kit.landmark_positions("anatomical44", Vs)
        assert np.abs(Xs[[ix[n] for n in rigid]] - X[[ix[n] for n in rigid]]).max() == 0.0
        assert m["rigid_landmark_max_mm"] == 0.0 and set(m["guarded_landmarks"]) == set(rigid)
        assert Xs[ix["ch_L"], 1] - X[ix["ch_L"], 1] >= 1.8 and m["min_area_ratio"] > 0.2
        # blink 2 mm: p, pi, en, ex, or fixed; ps down by the full amount
        Vk, m = SS.expression_field(kit, V, "blink", 2.0, return_meta=True)
        Xk = kit.landmark_positions("anatomical44", Vk)
        for b in ("p", "pi", "en", "ex", "or"):
            for side in ("_L", "_R"):
                assert np.array_equal(Xk[ix[b + side]], X[ix[b + side]]), b + side
        for side in ("_L", "_R"):
            assert Xk[ix["ps" + side]] - X[ix["ps" + side]] == pytest.approx([0.0, -2.0, 0.0], abs=1e-12)
        assert m["rigid_landmark_max_mm"] == 0.0
        # blink 10 mm: full amplitude at ps (the spec) even though the lid then folds over the eye
        Vk, m = SS.expression_field(kit, V, "blink", 10.0, return_meta=True)
        assert kit.landmark_positions("anatomical44", Vk)[ix["ps_L"], 1] - X[ix["ps_L"], 1] == pytest.approx(-10.0)
        assert m["fold_free_max_mm"] < 10.0 and m["min_area_ratio"] < 0.2
        # brow raise: n (and the eyes) fixed; g, tr move with the forehead as specified
        Vb, m = SS.expression_field(kit, V, "brow_raise", 2.0, return_meta=True)
        Xb = kit.landmark_positions("anatomical44", Vb)
        for n in ("n", "en_L", "en_R", "ex_L", "ex_R", "p_L", "p_R", "ps_L", "ps_R"):
            assert np.array_equal(Xb[ix[n]], X[ix[n]]), n
        assert Xb[ix["g"], 1] - X[ix["g"], 1] == pytest.approx(2.0)
        assert m["landmark_displacement_mm"]["n"] == 0.0 and m["rigid_landmark_max_mm"] == pytest.approx(2.0)
    for kind in SS.EXPRESSION_KINDS:
        em = SS.expression_meta(kind, 1.0)
        assert em["held_fixed"] and em["residual_rigid_motion"]


def test_out_of_prior_features_displacements(kit):
    """Regression (review of WP-11): the four spec features outside the factor model (dorsal hump, chin
    cleft, lip curvature, cheek fullness) must actually displace the subject by the drawn amounts."""
    V0, N0 = kit.vertices, kit.normals
    lv = dict(zip(kit.landmark_names("anatomical44"), kit.landmark_vertices("anatomical44")))
    checked = 0
    for seed in (1, 2, 3, 6):
        f = SS.out_of_prior_subject(kit, np.random.default_rng(seed), asym_mm=0.0)
        nf = SS.out_of_prior_subject(kit, np.random.default_rng(seed), asym_mm=0.0, features=False)
        if f.meta["attempts"] != 1 or nf.meta["attempts"] != 1:
            continue
        checked += 1
        p = f.meta["features"]
        assert set(p) == set(SS.FEATURE_KEYS) and nf.meta["feature_draws"] == f.meta["feature_draws"] == p
        assert f.meta["aniso_scale"] == nf.meta["aniso_scale"] and f.meta["zeta_drawn"] == nf.meta["zeta_drawn"]
        parts = SS.feature_displacements(kit, p)
        assert list(parts) == list(SS.FEATURE_KEYS)
        # dorsal hump: the midline vertex nearest the n-prn chord midpoint moves h along its normal
        mid = 0.5 * (V0[lv["n"]] + V0[lv["prn"]])
        c = kit.midline[np.argmin(np.linalg.norm(V0[kit.midline] - mid, axis=1))]
        assert np.allclose(parts["dorsal_hump_mm"][c], p["dorsal_hump_mm"] * N0[c], atol=1e-12)
        # chin cleft: pg moves inward by the cleft depth
        assert np.allclose(parts["chin_cleft_mm"][lv["pg"]], -p["chin_cleft_mm"] * N0[lv["pg"]], atol=1e-12)
        # lip curvature: ch moves vertically by u (|x_ch| / 30)^3
        for ch in ("ch_L", "ch_R"):
            v = lv[ch]
            exp_dy = p["lip_curve_mm"] * (abs(V0[v, 0]) / 30.0) ** 3
            assert np.allclose(parts["lip_curve_mm"][v], [0.0, exp_dy, 0.0], atol=1e-12)
        # cheek fullness: the cheeks region moves k along the normals
        ck = kit.regions["cheeks"]
        assert np.allclose(parts["cheek_fullness_mm"][ck], p["cheek_fullness_mm"] * N0[ck], atol=1e-12)
        # the subject differs from its feature-free twin by exactly the (symmetrised, scaled) features
        Df = sum(parts.values())
        S = SS.symmetric_part(Df, kit.mirror_map)
        S[kit.midline, 0] = 0.0
        scale = math.exp(f.meta["zeta_drawn"]) * np.asarray(f.meta["aniso_scale"])
        assert np.abs((f.V_true - nf.V_true) - S * scale).max() < 1e-9
        assert np.abs(f.V_true - nf.V_true).max() > 0.5
    assert checked >= 3


# =========================================================================== render
def test_render_landmarks_consistent(kit, subjects):
    """Visible projected landmarks lie inside the mask; the raster depth at the landmark pixel
    equals the landmark camera depth within 0.5 mm.  Visibility is the raster-independent
    geometric oracle (front-facing non-grazing star, unoccluded rays with a 2 px margin)."""
    n_checked = 0
    for sub in subjects[:3]:
        X = sub.landmarks("anatomical44")
        target = RD.face_centre(kit, sub.V_true)
        for yaw in (0.0, 20.0, -20.0, 45.0, 90.0):
            cam = orbit_camera(600.0, yaw, 5.0, 85.0, width=600, height=800, target=target)
            view = RD.render_view(sub.V_true, kit, cam)
            uv, vis = RD.project_landmarks(kit, sub.V_true, "anatomical44", view.camera, return_visible=True,
                                           cos_min=0.3, margin_px=2.0)
            assert vis.sum() >= 2
            cols = np.floor(uv[vis, 0]).astype(int)
            rows = np.floor(uv[vis, 1]).astype(int)
            assert view.mask[rows, cols].all()
            err = np.abs(view.depth[rows, cols] - cam.depth(X[vis]))
            assert err.max() < 0.5, err
            n_checked += int(vis.sum())
            # the uncorrected projection is the same uv
            assert np.array_equal(RD.project_landmarks(kit, sub.V_true, "anatomical44", cam), uv)
    assert n_checked > 100


def test_render_scale_resolution_corner_convention(kit, subjects):
    sub = subjects[1]
    cam = orbit_camera(700.0, 15.0, 0.0, 85.0, width=600, height=800, target=RD.face_centre(kit, sub.V_true))
    half = RD.render_view(sub.V_true, kit, cam, scale_resolution=0.5)
    assert half.image.shape == (400, 300, 3) and half.camera.width == 300 and half.camera.height == 400
    uv_full = RD.project_landmarks(kit, sub.V_true, "anatomical44", cam)
    uv_half = RD.project_landmarks(kit, sub.V_true, "anatomical44", half.camera)
    assert np.abs(uv_half - uv_full * 0.5).max() < 1e-9          # u' = u W'/W
    full = RD.render_view(sub.V_true, kit, cam)
    assert abs(half.mask.mean() - full.mask.mean()) < 0.01
    with pytest.raises(ValueError):
        RD.scale_camera(cam, 0.0)


def test_render_image_and_masks(kit, subjects):
    sub = subjects[2]
    cam = orbit_camera(700.0, 0.0, 0.0, 85.0, width=300, height=400, target=RD.face_centre(kit, sub.V_true))
    bg = (0.2, 0.3, 0.4)
    v = RD.render_view(sub.V_true, kit, cam, background=bg)
    assert v.image.dtype == np.float32 and v.image.shape == (400, 300, 3)
    assert v.image.min() >= 0.0 and v.image.max() <= 1.0
    assert np.allclose(v.image[~v.mask], np.asarray(bg, np.float32), atol=1e-6)
    assert v.mask.mean() > 0.2 and np.all(np.isinf(v.depth[~v.mask])) and np.all(v.tri_id[~v.mask] == -1)
    assert np.allclose(v.bary[v.mask].sum(axis=1), 1.0)
    m = RD.render_masks(v, kit, sub.V_true)
    assert np.array_equal(m["background"], ~v.mask)
    for k in ("skin", "lips", "brows", "face"):
        assert not np.any(m[k] & ~v.mask)
    assert m["skin"].sum() > 0.5 * v.mask.sum() and m["lips"].sum() > 50 and m["brows"].sum() > 20
    assert not np.any(m["skin"] & (m["lips"] | m["brows"]))
    # lips are redder than skin; brows darker
    img = v.image
    assert img[m["lips"], 0].mean() - img[m["lips"], 1].mean() > img[m["skin"], 0].mean() - img[m["skin"], 1].mean()
    assert img[m["brows"]].mean() < img[m["skin"]].mean()
    # determinism; noise needs an rng; blur keeps the mean
    assert np.array_equal(RD.render_view(sub.V_true, kit, cam, background=bg).image, v.image)
    with pytest.raises(ValueError):
        RD.render_view(sub.V_true, kit, cam, noise_sd=0.01)
    n1 = RD.render_view(sub.V_true, kit, cam, noise_sd=0.02, rng=np.random.default_rng(3))
    n2 = RD.render_view(sub.V_true, kit, cam, noise_sd=0.02, rng=np.random.default_rng(3))
    assert np.array_equal(n1.image, n2.image) and not np.array_equal(n1.image, v.image)
    b = RD.render_view(sub.V_true, kit, cam, blur_px=1.5, background=bg)
    assert np.array_equal(b.mask, v.mask)
    assert abs(float(b.image.mean()) - float(v.image.mean())) < 0.01
    lap = lambda a: np.abs(np.diff(a.astype(float), axis=1)).mean()
    assert lap(b.image) < lap(v.image)
    # constant and per-vertex albedo
    w = RD.render_view(sub.V_true, kit, cam, albedo=None)
    assert w.image[w.mask].max() <= 1.0 and np.allclose(w.image[w.mask, 0], w.image[w.mask, 1])
    pv = RD.render_view(sub.V_true, kit, cam, albedo=np.tile([0.5, 0.5, 0.5], (kit.n_verts, 1)))
    cst = RD.render_view(sub.V_true, kit, cam, albedo=(0.5, 0.5, 0.5))
    assert np.allclose(pv.image, cst.image, atol=1e-6)


def test_render_speed(kit):
    cam = orbit_camera(600.0, 10.0, 5.0, 85.0, width=600, height=800, target=RD.face_centre(kit))
    RD.render_view(kit.vertices, kit, cam)                 # warm-up (imports, caches)
    t0 = time.perf_counter()
    v = RD.render_view(kit.vertices, kit, cam)
    dt = time.perf_counter() - t0
    assert v.image.shape == (800, 600, 3)
    assert dt < 3.0, f"600x800 render took {dt:.2f} s"


# =========================================================================== faults
def test_mirror_fault_involution(kit):
    names = kit.landmark_names("anatomical44")
    perm = _swap_perm(names)
    cam = orbit_camera(800.0, 20.0, 0.0, 26.0, target=RD.face_centre(kit))
    uv = cam.project(kit.landmark_positions("anatomical44"))
    uv[3] = np.nan
    a, truth = F.mirror_view(uv, cam.width, perm)
    assert truth["truth"] == "mirrored" and truth["expect"] == "suggest_flip"
    i = names.index("ex_L")
    j = names.index("ex_R")
    assert a[j, 0] == cam.width - uv[i, 0] and a[j, 1] == uv[i, 1]         # labels swapped
    b, _ = F.mirror_view(a, cam.width, perm)
    assert np.array_equal(np.isnan(b), np.isnan(uv))
    assert np.array_equal(b[~np.isnan(uv)], uv[~np.isnan(uv)])
    assert not np.shares_memory(a, uv)


def test_unbaked_orientation_roundtrip():
    rng = np.random.default_rng(0)
    W, H = 3000, 4000
    uv = rng.uniform([0, 0], [W, H], size=(30, 2))
    for o in range(1, 9):
        s, (Ws, Hs), truth = F.unbaked_orientation(uv, W, H, o)
        assert (Ws, Hs) == ((H, W) if o >= 5 else (W, H))
        assert truth["expect"] == "Q-ORIENT" and truth["orientation_applied"] is False
        assert np.abs(orientation_point_map(o, Ws, Hs)(s) - uv).max() < 1e-9
        assert np.all((s >= 0) & (s <= [Ws, Hs]))
    s6, (Ws6, Hs6), _ = F.unbaked_orientation(uv, W, H)   # default o = 6: stored (u, v) -> (Hs - v, u)
    assert (Ws6, Hs6) == (H, W)
    assert np.allclose(np.column_stack([Hs6 - s6[:, 1], s6[:, 0]]), uv, rtol=0, atol=1e-9)


def test_beauty_warp_magnitudes(kit):
    names = kit.landmark_names("anatomical44")
    cam = orbit_camera(800.0, 5.0, 0.0, 26.0, target=RD.face_centre(kit))
    uv = cam.project(kit.landmark_positions("anatomical44"))
    imap = F.beauty_index_map(names)
    out, truth = F.beauty_warp(uv, imap)
    assert truth["expect"] == "Q-RETOUCH"
    ix = names.index
    for s in ("L", "R"):
        ratio = (np.linalg.norm(out[ix("ex_" + s)] - out[ix("en_" + s)])
                 / np.linalg.norm(uv[ix("ex_" + s)] - uv[ix("en_" + s)]))
        assert abs(ratio - 1.06) < 0.005
    jaw = np.linalg.norm(out[ix("go_L")] - out[ix("go_R")]) / np.linalg.norm(uv[ix("go_L")] - uv[ix("go_R")])
    assert abs(jaw - 0.96) < 0.005
    untouched = ~truth["moved"]
    assert np.array_equal(out[untouched], uv[untouched])
    assert np.array_equal(out[ix("prn")], uv[ix("prn")])
    # legacy long names map to the same roles
    lnames = kit.landmark_names("legacy_synthetic")
    lmap = F.beauty_index_map(lnames)
    assert [lnames[k] for k in lmap["eyes"]["L"]] == ["endocanthion_L", "exocanthion_L"]
    assert lnames[lmap["eye_centres"]["R"]] == "pupil_R"
    assert sorted(lnames[k] for k in lmap["jaw"]) == ["gonion_L", "gonion_R", "menton", "pogonion"]


def test_off_axis_stereographic_uses_model(kit, subjects):
    sub = subjects[0]
    Xc = RD.face_centre(kit, sub.V_true)
    cam = orbit_camera(600.0, 0.0, 0.0, 13.0, target=Xc)
    X = sub.landmarks("anatomical44")
    view, truth = F.off_axis_wide(cam, Xc, 35.0, "stereographic")
    uv = view.project(X)
    ref = camera_mod.stereographic_project(view.camera.to_camera(X), view.camera.f, view.camera.cx, view.camera.cy)
    assert np.abs(uv - ref).max() < 1e-9
    # independent check of the r = 2 f tan(phi/2) model
    Xcam = view.camera.to_camera(X)
    phi = np.arctan2(np.linalg.norm(Xcam[:, :2], axis=1), Xcam[:, 2])
    r = 2.0 * view.camera.f * np.tan(phi / 2.0)
    az = np.arctan2(Xcam[:, 1], Xcam[:, 0])
    ref2 = np.column_stack([view.camera.cx + r * np.cos(az), view.camera.cy + r * np.sin(az)])
    assert np.abs(uv - ref2).max() < 1e-9
    assert truth["expected_model"] == "virtual_stereo" and truth["expect"] == "Q-WIDE"
    assert truth["f_local_px"] == pytest.approx(cam.f / math.cos(math.radians(17.5)) ** 2)
    # the camera was rotated about its centre so the face sits 35 deg off-axis
    assert np.allclose(view.camera.center, cam.center) and view.camera.f == cam.f
    assert math.degrees(camera_mod.face_ray_angle(view.camera, Xc)) == pytest.approx(35.0, abs=1e-9)
    # rectilinear: plain pinhole of the rotated camera
    rv, rt = F.off_axis_wide(cam, Xc, 35.0, "rectilinear")
    assert np.abs(rv.project(X) - rv.camera.project(X)).max() == 0.0
    assert rt["expected_model"] == "pinhole"
    with pytest.raises(ValueError):          # a 85 mm-eq lens cannot hold the face 35 deg off-axis
        F.off_axis_wide(orbit_camera(600.0, 0.0, 0.0, 85.0, target=Xc), Xc, 35.0)
    assert truth["f35_mm"] == pytest.approx(13.0) and truth["q_wide_f35"] is True


def test_off_axis_wide_keeps_whole_face_in_frame(kit, subjects):
    """Regression (review of WP-11): at 26 mm the stereographic face centre landed at v = 3895 of 4000 px
    (most of the face off-image) and was accepted; the off-axis rows did not say which lens to use."""
    sub = subjects[0]
    Xc = RD.face_centre(kit, sub.V_true)
    names = kit.landmark_names("anatomical44")
    face = sub.landmarks("anatomical44", [n for n in names if n.rstrip("_LR") not in ("v", "op", "eu")])
    for model in ("stereographic", "rectilinear"):
        with pytest.raises(ValueError):
            F.off_axis_wide(orbit_camera(600.0, 0.0, 0.0, 26.0, target=Xc), Xc, 35.0, model)
        for f35 in (13.0, 16.0):
            cam = orbit_camera(600.0, 0.0, 0.0, f35, target=Xc)
            view, t = F.off_axis_wide(cam, Xc, 35.0, model, face_points=face)
            uv = view.project(face)
            assert np.all((uv >= 0) & (uv <= [cam.width, cam.height]))
            assert t["q_wide_f35"] is True and t["face_extent"] == "face points"
    # points far outside the field of view are refused even when the centre is in frame
    cam = orbit_camera(600.0, 0.0, 0.0, 16.0, target=Xc)
    with pytest.raises(ValueError):
        F.off_axis_wide(cam, Xc, 35.0, "rectilinear", face_points=np.vstack([face, Xc + [0.0, -400.0, 0.0]]))
    with pytest.raises(ValueError):
        F.off_axis_wide(cam, Xc, 35.0, "rectilinear", face_radius_mm=400.0)
    # the matrix rows say which lens the harness must use (DESIGN 4.1 Q-WIDE: f35 <= 16 mm)
    for e in F.FAULT_MATRIX:
        if e["generator"] is F.off_axis_wide:
            cam_req = e["requires"]["camera"]
            lo, hi = cam_req["f35_mm"]["uniform"]
            assert cam_req["f35_max_mm"] == 16.0 and 0 < lo < hi <= 16.0 and e["requires"]["face_in_frame"]
            for f35 in (lo, hi):
                F.off_axis_wide(orbit_camera(600.0, 0.0, 0.0, f35, target=Xc), Xc, face_points=face,
                                **e["kwargs"])


def test_selfie_small_face_outliers_occluders_bias(kit, subjects):
    rig, truth = F.selfie_rig(np.random.default_rng(4))
    target = np.asarray(rig.target)
    assert np.allclose(target, RD.face_centre(build_procedural_head()))
    assert rig.n_views == 3 and all(rig.is_front_camera) and truth["expect"][0] == "Q-NEAR"
    for c in rig.cameras:
        assert np.linalg.norm(c.center - target) == pytest.approx(350.0)
        assert 22.0 - 1e-6 <= c.focal_35mm <= 30.0 + 1e-6
    # small face: the bizygomatic width becomes 150 px by moving back along the axis
    names = kit.landmark_names("anatomical44")
    X = subjects[0].landmarks("anatomical44")
    cam = orbit_camera(800.0, 10.0, 0.0, 26.0, target=RD.face_centre(kit, subjects[0].V_true))
    pair = (names.index("zy_L"), names.index("zy_R"))
    c2, t = F.small_face(cam, 150.0, X=X, pair=pair)
    assert F.face_width_px(c2, X, pair) == pytest.approx(150.0, rel=1e-6)
    assert np.array_equal(c2.R, cam.R) and c2.f == cam.f and t["moved_back_mm"] > 0
    shift = c2.center - cam.center
    assert np.linalg.norm(np.cross(shift, cam.R[2])) < 1e-6 * np.linalg.norm(shift)
    with pytest.raises(ValueError):
        F.small_face(c2, 300.0, X=X, pair=pair)
    # gross outliers: exact count, magnitudes 5-20 sigma, deterministic, NaN rows untouched
    uv = cam.project(X)
    uv[0] = np.nan
    out, t = F.gross_outliers(uv, 0.1, np.random.default_rng(2), 2.0)
    mask = t["outlier_mask"]
    assert mask.sum() == round(0.1 * 43) and not mask[0]
    d = np.linalg.norm(out - uv, axis=1)
    assert np.all((d[mask] >= 10.0 - 1e-9) & (d[mask] <= 40.0 + 1e-9))
    assert np.array_equal(out[~mask & ~np.isnan(uv[:, 0])], uv[~mask & ~np.isnan(uv[:, 0])])
    out2, _ = F.gross_outliers(uv, 0.1, np.random.default_rng(2), 2.0)
    assert np.array_equal(out, out2, equal_nan=True)
    # occluders
    eff, t = F.occluder_fault(["beard"], names=names, uv=cam.project(X))
    dropped = {names[k] for k in np.flatnonzero(eff["drop"])}
    assert dropped == {"pg", "gn", "me", "go_L", "go_R"}
    assert np.all(np.isnan(eff["uv"][eff["drop"]]))
    assert eff["contour_flags"] == [{"region": "jaw", "kind": "outer_bound"}]
    assert t["expect"]["jaw_status"] == "prior-driven"
    eff, t = F.occluder_fault(["glasses"], names=names)
    assert {names[k] for k in np.flatnonzero(eff["drop"])} == {"p_L", "p_R"}
    assert {names[k] for k in np.flatnonzero(eff["noise_multiplier"] == 2.0)} == {
        b + s for b in ("en", "ex", "ps", "pi") for s in ("_L", "_R")}
    assert t["expect"]["no_iris_scale"] is True
    eff, t = F.occluder_fault(["hair"], names=kit.landmark_names("legacy_synthetic"))
    assert {kit.landmark_names("legacy_synthetic")[k] for k in np.flatnonzero(eff["drop"])} == {
        "tragion_L", "tragion_R", "forehead_side_L", "forehead_side_R"}
    with pytest.raises(ValueError):
        F.occluder_fault(["hat"])
    # definition bias, EXIF
    Xb, t = F.definition_bias(X, np.random.default_rng(0), 1.0)
    assert np.allclose(Xb - X, t["bias_3d"], rtol=0, atol=1e-12) and t["bias_3d"].shape == X.shape
    big = F.definition_bias(np.zeros((4000, 3)), np.random.default_rng(1))[1]["bias_3d"]
    assert abs(big.std() - 1.0) < 0.03
    p, t = F.exif_crop(1000.0, 1.3)
    assert p["f_prior_px"] == pytest.approx(1300.0) and p["f_prior_log_sigma"] == 0.04 and t["f_true_px"] == 1000.0
    p, t = F.exif_missing()
    assert p["f_prior_px"] is None and p["f_prior_log_sigma"] == 0.6
    # expression fault: one expressive view among five
    Vs, t = F.expression_fault(subjects[0], 3, "jaw_open", 10.0)
    assert len(Vs) == 5 and t["model_matched"] is True and t["neutral_views"] == [0, 1, 2, 4]
    assert all(np.array_equal(Vs[k], subjects[0].V_true) for k in (0, 1, 2, 4))
    assert not np.array_equal(Vs[3], subjects[0].V_true)


def test_fault_matrix_rows_complete():
    rows = F.design_fault_rows((REPO / "docs" / "DESIGN.md").read_text(encoding="utf-8"))
    assert len(rows) >= 11
    covered = {e["design_row"] for e in F.FAULT_MATRIX}
    assert set(rows) <= covered, sorted(set(rows) - covered)
    assert covered <= set(rows)
    names = [e["name"] for e in F.FAULT_MATRIX]
    assert len(set(names)) == len(names)
    for e in F.FAULT_MATRIX:
        assert set(e) >= {"name", "generator", "must_raise", "metric", "threshold", "degradation_bound",
                          "requires"}
        assert isinstance(e["requires"], dict)
        assert callable(e["generator"]) and getattr(F, e["generator_name"]) is e["generator"]
        params = inspect.signature(e["generator"]).parameters
        assert set(e["kwargs"]) <= set(params) and set(e["sampling"]) <= set(params), e["name"]
        assert not set(e["kwargs"]) & set(e["sampling"])
        assert e["must_raise"] or e["metric"]
        assert e["threshold"]
    # both off-axis models, all three tags, both expression kinds, crop and missing EXIF are present
    assert {"off_axis_stereographic", "off_axis_rectilinear", "beard", "glasses", "hair", "jaw_open", "smile",
            "exif_crop", "exif_missing"} <= set(names)
    codes = {e["must_raise"] for e in F.FAULT_MATRIX}
    assert {"suggest_flip", "Q-ORIENT", "C-FOCAL-PRIOR", "Q-NEAR", "expressive", "Q-RETOUCH", "Q-WIDE",
            "Q-SMALL"} <= codes


def test_defaults_registered_with_badges():
    from face3d.core import config

    keys = [k for k in config._REGISTRY if k.startswith("testbed.")]
    assert any(k.startswith("testbed.surface.") for k in keys)
    assert any(k.startswith("testbed.render.") for k in keys)
    assert any(k.startswith("testbed.faults.") for k in keys)
    for k in keys:
        d = config.get(k)
        assert d.badge in config.BADGES and d.source
