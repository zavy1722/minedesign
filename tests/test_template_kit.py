"""WP-08: procedural CC0 template head, template kit format and tool, conditional template prior.

Acceptance tests from docs/wbs.json (WP-08) plus supporting checks.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from face3d.core.schema import FormatError
from face3d.geometry.rbf import RBFWarp
from face3d.mesh.core import write_obj
from face3d.model.conditional_prior import (DEFAULT_REGION_SIGMA_MM, ConditionalTemplatePrior,
                                            rbf_transfer_matrix)
from face3d.model.landmark_prior import CompositePrior, FactorPrior, GeneralisedPrior, prior_mean
from face3d.model.procedural_head import (REGION_ORDER, ProceduralHeadError, build_procedural_head,
                                          cube_sphere, signed_volume)
from face3d.model.registry import load_scheme
from face3d.model.template_kit import TemplateKit, TopologyMismatch, fan_triangles, topology_sha256

REPO = Path(__file__).resolve().parents[1]
FLIP = np.array([-1.0, 1.0, 1.0])


@pytest.fixture(scope="module")
def kit() -> TemplateKit:
    return build_procedural_head()


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("build_template_kit", REPO / "tools" / "build_template_kit.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _legacy_other_names() -> list[str]:
    return [p.name for p in load_scheme("legacy_synthetic").points if p.anatomical_id is None]


# =========================================================================== procedural head
def test_procedural_head_deterministic_quads_closed(kit):
    again = build_procedural_head()
    assert again.topology_sha256 == kit.topology_sha256
    assert again.vertices.tobytes() == kit.vertices.tobytes()
    assert again == kit
    assert kit.generated is True and kit.licence == "CC0-1.0" and kit.bundle_ok and kit.units == "mm"
    assert kit.id == "procedural-head-v1"
    n = 24
    assert kit.faces.shape == (6 * n * n, 4) and kit.is_quad
    assert kit.n_verts == 6 * n * n + 2
    # closed and consistently oriented: every directed edge once, its reverse once
    f = kit.faces
    directed = np.concatenate([np.stack([f[:, i], f[:, (i + 1) % 4]], 1) for i in range(4)])
    assert len(np.unique(directed, axis=0)) == len(directed)
    und, counts = np.unique(np.sort(directed, axis=1), axis=0, return_counts=True)
    assert np.all(counts == 2), "boundary or non-manifold edges"
    assert len(kit.mesh().boundary_vertices()) == 0
    euler = kit.n_verts - len(und) + kit.n_faces
    assert euler == 2
    assert signed_volume(kit.vertices, kit.triangles()) > 0
    # topology hash definition: int64 n_verts + int32 faces
    import hashlib
    h = hashlib.sha256(np.int64(kit.n_verts).astype("<i8").tobytes() + f.astype("<i4").tobytes()).hexdigest()
    assert kit.topology_sha256 == h
    assert topology_sha256(kit.n_verts, f.tolist()) == h


def test_mirror_map_exact(kit):
    m = kit.mirror_map
    assert np.array_equal(m[m], np.arange(kit.n_verts))
    assert np.abs(kit.vertices[m] * FLIP - kit.vertices).max() < 1e-9
    assert kit.midline.size > 0
    assert np.all(kit.vertices[kit.midline, 0] == 0.0)
    assert np.array_equal(np.sort(kit.midline), np.flatnonzero(m == np.arange(kit.n_verts)))
    # the fan split is mirror-symmetric too: every triangle's mirror is a triangle
    tris = kit.triangles()
    as_sets = {tuple(sorted(t)) for t in tris.tolist()}
    assert all(tuple(sorted(m[t].tolist())) in as_sets for t in tris)


def test_landmarks_hit_prior_mean(kit):
    ids, mu = prior_mean("unspecified")
    P = kit.landmark_positions("anatomical44", names=ids)
    assert np.abs(P - mu).max() < 1e-6
    assert kit.landmark_names("anatomical44") == list(ids)
    assert kit.meta["landmark_mode"] == "vertex" and kit.meta["landmarks_exact"]
    # one-hot embeddings on distinct, mirror-consistent vertices
    lv = kit.landmark_vertices("anatomical44", ids)
    assert len(set(lv.tolist())) == 44
    idx = {k: i for i, k in enumerate(ids)}
    for k in ids:
        if k.endswith("_L"):
            assert kit.mirror_map[lv[idx[k]]] == lv[idx[k[:-2] + "_R"]]
        elif not k.endswith("_R"):
            assert lv[idx[k]] in set(kit.midline.tolist())
    for e in kit.landmarks["anatomical44"].values():
        assert sorted(e["bary"].tolist()) == [0.0, 0.0, 1.0]
        assert e["sigma_annot_mm"] == 0.0
    # sex-specific builds hit their own means
    for sex in ("male", "female"):
        k2 = build_procedural_head(sex=sex)
        ids2, mu2 = prior_mean(sex)
        assert np.abs(k2.landmark_positions("anatomical44", names=ids2) - mu2).max() < 1e-6


def test_no_folded_faces(kit):
    S = cube_sphere(24)["sphere"]
    V = kit.vertices
    for tri in (kit.triangles(), None):
        if tri is None:  # quad normals from the diagonals
            f = kit.faces
            fn = np.cross(V[f[:, 2]] - V[f[:, 0]], V[f[:, 3]] - V[f[:, 1]])
            ns = S[f].sum(axis=1)
        else:
            fn = np.cross(V[tri[:, 1]] - V[tri[:, 0]], V[tri[:, 2]] - V[tri[:, 0]])
            ns = S[tri].sum(axis=1)
        assert np.all(np.einsum("ij,ij->i", fn, ns) > 0)
    assert kit.meta["fold_min_cos"] > 0
    # vertex normals point outward, roughly along the sphere normal
    assert np.all(np.einsum("ij,ij->i", kit.normals, S) > 0)
    assert np.allclose(np.linalg.norm(kit.normals, axis=1), 1.0)


def test_coarse_head_builds_without_folds():
    """n = 16 (used by WP-13) needs the documented surface fallback; it must be fold-free."""
    k = build_procedural_head(n=16)
    S = cube_sphere(16)["sphere"]
    tri = k.triangles()
    fn = np.cross(k.vertices[tri[:, 1]] - k.vertices[tri[:, 0]], k.vertices[tri[:, 2]] - k.vertices[tri[:, 0]])
    assert np.all(np.einsum("ij,ij->i", fn, S[tri].sum(axis=1)) > 0)
    assert k.meta["landmark_mode"] in ("vertex", "surface")
    ids, mu = prior_mean("unspecified")
    err = np.linalg.norm(k.landmark_positions("anatomical44", names=ids) - mu, axis=1)
    sig = np.array([k.landmarks["anatomical44"][i]["sigma_annot_mm"] for i in ids])
    assert np.allclose(err, sig, atol=1e-6) or k.meta["landmarks_exact"]
    assert np.abs(k.vertices[k.mirror_map] * FLIP - k.vertices).max() < 1e-9
    with pytest.raises(ValueError):
        build_procedural_head(n=15)
    with pytest.raises(ValueError):
        build_procedural_head(sex="other")
    assert issubclass(ProceduralHeadError, RuntimeError)


def test_regions_cover_disjoint_nonempty(kit):
    assert list(kit.regions) == list(REGION_ORDER)
    count = np.zeros(kit.n_verts, int)
    for idx in kit.regions.values():
        np.add.at(count, idx, 1)
    assert np.all(count == 1)
    for r in ("eyes", "nose", "lips", "chin", "ears"):
        assert kit.regions[r].size > 0, r
    # regions are mirror-symmetric sets
    for r, idx in kit.regions.items():
        assert set(kit.mirror_map[idx].tolist()) == set(idx.tolist()), r
    vr = kit.vertex_regions()
    assert vr[kit.landmark_vertices("anatomical44", ["prn"])[0]] == "nose"
    assert vr[kit.landmark_vertices("anatomical44", ["p_L"])[0]] == "eyes"
    # per-vertex attributes
    assert np.all((kit.jaw_weights >= 0) & (kit.jaw_weights <= 1))
    me = kit.landmark_vertices("anatomical44", ["me"])[0]
    v_top = kit.landmark_vertices("anatomical44", ["v"])[0]
    assert kit.jaw_weights[me] == 1.0 and kit.jaw_weights[v_top] == 0.0
    assert set(np.unique(kit.stiffness).tolist()) <= {0.3, 0.5, 1.0, 3.0}
    assert np.all(kit.stiffness[kit.regions["lips"]] == 0.3)
    assert np.any(kit.stiffness[kit.regions["eyes"]] == 3.0)
    assert kit.uv.min() >= 0.0 and kit.uv.max() <= 1.0
    ring = kit.contour_rings["midline_profile"]
    assert sorted(ring.tolist()) == sorted(kit.midline.tolist())
    assert set(kit.region_weights) == set(REGION_ORDER)


def test_kit_save_load_topology_refusal(kit, tmp_path):
    path = tmp_path / "procedural-head-v1.kit.json"
    npz = kit.save(path)
    assert npz.name == "procedural-head-v1.npz" and npz.exists()
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["format"] == "face3d.template_kit" and doc["version"] == 1
    assert doc["topology_sha256"] == kit.topology_sha256 and doc["generated"] is True
    back = TemplateKit.load(path, expect_topology_sha256=kit.topology_sha256)
    assert back == kit
    assert back.landmark_names("legacy_synthetic") == kit.landmark_names("legacy_synthetic")
    assert np.array_equal(back.landmark_positions("anatomical44"), kit.landmark_positions("anatomical44"))
    with pytest.raises(TopologyMismatch):
        TemplateKit.load(path, expect_topology_sha256="0" * 64)
    assert issubclass(TopologyMismatch, ValueError)
    # a JSON whose recorded topology differs from the arrays is refused too
    bad = dict(doc)
    bad["topology_sha256"] = "f" * 64
    (tmp_path / "bad.json").write_text(json.dumps(bad), encoding="utf-8")
    import shutil
    shutil.copy(npz, tmp_path / "bad.npz")
    bad["arrays"] = {k: dict(v, file="bad.npz") for k, v in doc["arrays"].items()}
    (tmp_path / "bad.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(TopologyMismatch):
        TemplateKit.load(tmp_path / "bad.json")
    # corrupted arrays are refused by their sha256
    arr = dict(np.load(npz))
    arr["vertices"] = arr["vertices"] + 1.0
    np.savez(npz, **arr)
    with pytest.raises(FormatError):
        TemplateKit.load(path)
    # licence: non-CC0 kits never bundle, and the flag survives a roundtrip
    nc = kit.replace(licence="CC-BY-4.0")
    assert nc.bundle_ok is False and kit.bundle_ok is True
    nc.save(tmp_path / "nc.kit.json")
    assert TemplateKit.load(tmp_path / "nc.kit.json").bundle_ok is False


def test_kit_validation_and_legacy_template(kit):
    V = kit.vertices.copy()
    V[0, 0] += 1e-3
    with pytest.raises(ValueError, match="reflection"):
        kit.replace(vertices=V)
    m = kit.mirror_map.copy()
    m[[0, 1]] = m[[1, 0]]
    with pytest.raises(ValueError):
        kit.replace(mirror_map=m)
    tpl = kit.to_template("legacy_synthetic")
    from face3d.synthetic import synthetic_landmarks
    names, _ = synthetic_landmarks()
    assert tpl.names == names
    assert np.all(tpl.landmark_vertices >= 0)
    assert np.allclose(tpl.landmark_positions, kit.landmark_positions("legacy_synthetic"))
    lg = kit.landmarks["legacy_synthetic"]
    assert lg["pronasale"]["tri"] == kit.landmarks["anatomical44"]["prn"]["tri"]
    assert lg["brow_inner_L"]["provenance"] == "legacy_similarity_transfer"
    lv = dict(zip(names, tpl.landmark_vertices.tolist()))
    for nm in names:
        if nm.endswith("_L"):
            assert kit.mirror_map[lv[nm]] == lv[nm[:-2] + "_R"]
    assert lv["vertex_front"] in set(kit.midline.tolist())


# =========================================================================== conditional prior
def test_conditional_prior_affine_invariant_and_jacobian(kit):
    ids, _ = prior_mean()
    other = _legacy_other_names()
    pr = ConditionalTemplatePrior(kit, "legacy_synthetic", other, ids)
    assert isinstance(pr, GeneralisedPrior)
    assert pr.B.shape == (len(other), 44)
    TA, TC = pr.T_A, pr.T_C
    X0 = np.vstack([TA, TC])
    assert np.abs(pr.residual(X0)).max() < 1e-9
    rng = np.random.default_rng(8)
    for _ in range(3):
        G = np.eye(3) + 0.3 * rng.normal(size=(3, 3))
        g = rng.normal(scale=40.0, size=3)
        X = np.vstack([TA @ G.T + g, TC @ G.T + g])
        assert np.abs(pr.residual(X)).max() < 1e-8
    # B reproduces affine fields row by row and equals the RBFWarp transfer
    assert np.allclose(pr.B.sum(axis=1), 1.0, atol=1e-10)
    d_A = rng.normal(scale=3.0, size=TA.shape)
    warp = RBFWarp(TA, TA + d_A, smoothing=0.0)
    assert np.allclose(pr.B @ d_A, warp.displacement(TC), atol=1e-8)
    # residual units: a 1 mm shift of one C point = 1/(kappa*sigma) whitened
    X = X0.copy()
    X[44, 1] += 1.0
    r = pr.residual(X)
    assert r[1] == pytest.approx(1.0 / pr.sigma_mm[0], rel=1e-9)
    assert pr.sigma_mm[0] == pytest.approx(1.5 * DEFAULT_REGION_SIGMA_MM[pr.regions[0]])
    # analytic Jacobian vs central differences, at a random state with permuted global rows
    N = 44 + len(other) + 3
    perm = rng.permutation(N)
    iA, iC = perm[:44], perm[44:44 + len(other)]
    pb = pr.with_index(iA, iC, n_total=N)
    Xall = rng.normal(scale=50.0, size=(N, 3))
    J = pb.jacobian(Xall)
    assert J.shape == (3 * len(other), 3 * N)
    h = 1e-3
    Jn = np.zeros_like(J)
    flat = Xall.reshape(-1)
    for c in range(3 * N):
        e = np.zeros_like(flat)
        e[c] = h
        Jn[:, c] = (pb.residual((flat + e).reshape(N, 3)) - pb.residual((flat - e).reshape(N, 3))) / (2 * h)
    assert np.allclose(J, Jn, rtol=1e-6, atol=1e-9)
    assert pb.neg_log_density(Xall) == pytest.approx(0.5 * float(pb.residual(Xall) @ pb.residual(Xall)))
    # stacks with the factor prior in CompositePrior
    fp = FactorPrior.from_package()
    comp = CompositePrior([(fp, iA), pb], n_total=N)
    assert comp.jacobian(Xall).shape == (3 * 44 + 3 * len(other), 3 * N)
    r_fp, r_c = fp.with_index(iA).residual(Xall), pb.residual(Xall)
    assert comp.neg_log_density(Xall) == pytest.approx(0.5 * float(r_fp @ r_fp + r_c @ r_c))


def test_conditional_prior_options_and_errors(kit):
    ids, _ = prior_mean()
    other = _legacy_other_names()
    pr = ConditionalTemplatePrior(kit, "legacy_synthetic", other, ids, kappa=1.0,
                                  region_sigma_mm={"forehead": 5.0})
    for nm, reg, s in zip(other, pr.regions, pr.sigma_mm):
        expect = 5.0 if reg == "forehead" else DEFAULT_REGION_SIGMA_MM[reg]
        assert s == pytest.approx(expect), nm
    # anatomical points can play C too (conditioning on a subset of the backbone)
    sub = ["en_L", "en_R", "prn", "sto", "t_L", "t_R", "g", "me"]
    rest = [i for i in ids if i not in sub]
    pc = ConditionalTemplatePrior(kit, "anatomical44", rest, sub)
    assert np.abs(pc.residual(np.vstack([pc.T_A, pc.T_C]))).max() < 1e-9
    with pytest.raises(ValueError):
        ConditionalTemplatePrior(kit, "legacy_synthetic", other, ids, kappa=0.0)
    with pytest.raises(KeyError):
        ConditionalTemplatePrior(kit, "legacy_synthetic", ["nope"], ids)
    with pytest.raises(ValueError):
        pr.with_index(np.arange(44), np.arange(len(other)))
    with pytest.raises(ValueError):
        rbf_transfer_matrix(pr.T_A[:3], pr.T_C)


# =========================================================================== build tool
def _export(kit: TemplateKit, d: Path) -> tuple[Path, Path]:
    obj = d / "head.obj"
    write_obj(kit.mesh(), obj)
    ann = d / "annotations.json"
    ann.write_text(json.dumps(kit.annotations()), encoding="utf-8")
    return obj, ann


def test_build_template_kit_from_obj(kit, tool, tmp_path, capsys):
    obj, ann = _export(kit, tmp_path)
    out = tmp_path / "rebuilt.kit.json"
    rc = tool.main(["--obj", str(obj), "--annotations", str(ann), "--licence", "CC0-1.0",
                    "--source-sha256", kit.source_sha256, "--out", str(out), "--generated"])
    assert rc == 0, capsys.readouterr().err
    summary = json.loads(capsys.readouterr().out)
    assert summary["topology_sha256"] == kit.topology_sha256 and summary["bundle_ok"] is True
    rebuilt = TemplateKit.load(out, expect_topology_sha256=kit.topology_sha256)
    assert rebuilt.topology_sha256 == kit.topology_sha256
    assert np.array_equal(rebuilt.mirror_map, kit.mirror_map)
    assert np.array_equal(rebuilt.midline, kit.midline)
    assert np.abs(rebuilt.vertices - kit.vertices).max() < 1e-6
    for s in kit.schemes:
        assert rebuilt.landmark_names(s) == kit.landmark_names(s)
        for name, e in kit.landmarks[s].items():
            f = rebuilt.landmarks[s][name]
            assert f["tri"] == e["tri"] and np.array_equal(f["bary"], e["bary"]), (s, name)
    assert np.abs(rebuilt.landmark_positions("anatomical44") - kit.landmark_positions("anatomical44")).max() < 1e-6
    assert rebuilt.meta["uv_source"] == "obj" and np.abs(rebuilt.uv - kit.uv).max() < 1e-6
    # vertex-form annotations give the same one-hot embeddings
    vert_ann = {"anatomical44": {k: {"vertex": int(v), "sigma_annot_mm": 0.5, "annotator_spread_mm": 0.4}
                                 for k, v in zip(kit.landmark_names("anatomical44"),
                                                 kit.landmark_vertices("anatomical44"))}}
    k2 = tool.build_kit(obj, vert_ann, "CC0-1.0", kit.source_sha256)
    for name, e in kit.landmarks["anatomical44"].items():
        assert k2.landmarks["anatomical44"][name]["tri"] == e["tri"]
        assert np.array_equal(k2.landmarks["anatomical44"][name]["bary"], e["bary"])

    # one asymmetric vertex is refused (no mirror partner within tolerance) ...
    lines = obj.read_text(encoding="utf-8").splitlines()
    vi = next(i for i, ln in enumerate(lines) if ln.startswith("v "))
    j = vi + int(kit.regions["cheeks"][0])
    x, y, z = (float(t) for t in lines[j].split()[1:4])
    asym = list(lines)
    asym[j] = f"v {x + 0.5:.6f} {y:.6f} {z:.6f}"
    bad_obj = tmp_path / "asym.obj"
    bad_obj.write_text("\n".join(asym) + "\n", encoding="utf-8")
    rc = tool.main(["--obj", str(bad_obj), "--annotations", str(ann), "--licence", "CC0-1.0",
                    "--source-sha256", kit.source_sha256, "--out", str(tmp_path / "x.kit.json")])
    assert rc == 2 and "mirror" in capsys.readouterr().err
    assert not (tmp_path / "x.kit.json").exists()
    # ... and so is a sub-tolerance asymmetry, unless explicitly symmetrised
    asym[j] = f"v {x + 0.001:.6f} {y:.6f} {z:.6f}"
    bad_obj.write_text("\n".join(asym) + "\n", encoding="utf-8")
    with pytest.raises(tool.BuildRefused, match="exactly mirror-symmetric"):
        tool.build_kit(bad_obj, kit.annotations(), "CC0-1.0", kit.source_sha256)
    ks = tool.build_kit(bad_obj, kit.annotations(), "CC0-1.0", kit.source_sha256, symmetrize=True)
    assert ks.topology_sha256 == kit.topology_sha256 and ks.meta["symmetrized"]


def test_build_tool_refusals(kit, tool, tmp_path):
    obj, ann = _export(kit, tmp_path)
    annotations = kit.annotations()
    with pytest.raises(tool.BuildRefused, match="licence"):
        tool.build_kit(obj, annotations, "CC-BY-4.0", kit.source_sha256)
    nc = tool.build_kit(obj, annotations, "CC-BY-4.0", kit.source_sha256, allow_noncc0=True)
    assert nc.bundle_ok is False
    with pytest.raises(tool.BuildRefused):
        tool.build_kit(obj, annotations, "CC0-1.0", "not-a-hash")
    # two-annotator acceptance: 1.0 mm for sharp_junction/curve, 2.5 mm otherwise
    bad = json.loads(json.dumps(annotations))
    bad["anatomical44"]["en_L"]["annotator_spread_mm"] = 1.2      # sharp_junction -> rejected
    bad["anatomical44"]["prn"]["annotator_spread_mm"] = 2.0       # extremal -> accepted
    bad["anatomical44"]["ls"]["annotator_spread_mm"] = 1.5        # curve -> rejected
    del bad["legacy_synthetic"]["brow_inner_L"]["annotator_spread_mm"]
    with pytest.raises(tool.BuildRefused) as ei:
        tool.build_kit(obj, bad, "CC0-1.0", kit.source_sha256)
    rep = "\n".join(ei.value.report)
    assert "en_L" in rep and "ls" in rep and "brow_inner_L" in rep and "prn" not in rep
    assert len(ei.value.report) == 3
    # regions from JSON
    k3 = tool.build_kit(obj, annotations, "CC0-1.0", kit.source_sha256,
                        regions={"eyes": kit.regions["eyes"].tolist(), "nose": kit.regions["nose"].tolist()})
    assert list(k3.regions) == ["eyes", "nose"] and k3.meta["region_source"] == "json"
    # non-quad meshes are refused in this version
    tri_obj = tmp_path / "tri.obj"
    lines = obj.read_text(encoding="utf-8").splitlines()
    fi = next(i for i, ln in enumerate(lines) if ln.startswith("f "))
    toks = lines[fi].split()
    lines[fi] = " ".join(toks[:4])
    tri_obj.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(tool.BuildRefused, match="quads"):
        tool.build_kit(tri_obj, annotations, "CC0-1.0", kit.source_sha256)


def test_fan_triangles_consistent_with_mesh(kit):
    assert np.array_equal(fan_triangles(kit.faces), kit.mesh().triangles())
    assert np.array_equal(kit.triangles()[0], kit.faces[0, [0, 1, 2]])
    assert np.array_equal(kit.triangles()[1], kit.faces[0, [0, 2, 3]])
