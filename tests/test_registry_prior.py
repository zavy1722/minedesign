"""WP-03: landmark registry, scheme files and the metric 18-factor landmark prior.

Acceptance tests from docs/wbs.json (WP-03) plus a few supporting checks.  The
research JSON (research/data/metric-3d-landmark-reference.json) is optional:
tests that compare against it skip when it is absent.
"""
from __future__ import annotations

import inspect
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from face3d.geometry.camera import Camera, look_at
from face3d.geometry.rotations import rodrigues
from face3d.model.landmark_prior import (
    PACKAGE_PRIOR_PATH,
    CompositePrior,
    DiagonalPrior,
    FactorPrior,
    GeneralisedPrior,
    LandmarkPrior,
    load_prior_package,
    prior_mean,
)
from face3d.model.registry import (
    ANATOMICAL,
    ANATOMICAL_IDS,
    Scheme,
    anchor_ids,
    load_scheme,
    resolve_lr,
)
from face3d.synthetic import synthetic_landmarks

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "data" / "metric-3d-landmark-reference.json"
TOOL = REPO / "tools" / "build_prior_tables.py"
needs_research = pytest.mark.skipif(not RESEARCH.is_file(), reason="research JSON absent")


def _tables() -> dict:
    d = json.loads(RESEARCH.read_text(encoding="utf-8"))
    return {t["name"]: t for t in d["tables"]}


def _rel(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b) / np.linalg.norm(b))


# --------------------------------------------------------------------------- build tool
@needs_research
def test_build_tool_reproduces_packaged_json(tmp_path):
    out = tmp_path / "landmark_prior_v1.json"
    proc = subprocess.run([sys.executable, str(TOOL), "--out", str(out)], cwd=str(REPO),
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    assert out.read_bytes() == PACKAGE_PRIOR_PATH.read_bytes()


@needs_research
def test_male_loadings_match_research_table():
    T = _tables()
    pkg = load_prior_package()
    ids, fnames = pkg["ids"], pkg["factor_names"]
    Lo = pkg["sexes"]["M"]["loadings"]
    assert Lo.shape == (132, 18) and len(fnames) == 18
    listed = set()
    for row in T["factor_loadings"]["rows"]:
        fac, lid = row[0], row[1]
        k = fnames.index(fac)
        if lid == "*":  # size: loading = mean coordinate (isometric scaling about mid-tragion)
            assert fac == "size"
            np.testing.assert_allclose(Lo[:, k], pkg["sexes"]["M"]["mean"].reshape(-1), atol=1e-12)
            continue
        i = ids.index(lid)
        np.testing.assert_allclose(Lo[3 * i:3 * i + 3, k], np.array(row[2:5], float), atol=0.006,
                                   err_msg=f"{fac} {lid}")
        listed.add((fac, lid))
    # every loading the research table does not list is zero
    for k, fac in enumerate(fnames):
        if fac == "size":
            continue
        for i, lid in enumerate(ids):
            if (fac, lid) not in listed:
                assert np.all(np.abs(Lo[3 * i:3 * i + 3, k]) <= 0.006), (fac, lid)


@needs_research
def test_packaged_means_and_sigmas_match_research_tables():
    T = _tables()
    pkg = load_prior_package()
    for code, sex in (("M", "male"), ("F", "female")):
        rows = T[f"mean_landmarks_{sex}_european_young_adult"]["rows"]
        assert pkg["ids"] == [r[0] for r in rows]
        np.testing.assert_allclose(pkg["sexes"][code]["mean"], np.array([r[2:5] for r in rows], float), atol=1e-9)
        sig = T[f"factor_sigmas_{sex}"]["rows"]
        assert pkg["factor_names"] == [r[0] for r in sig]
        np.testing.assert_allclose(pkg["sexes"][code]["factor_sigma"], [r[1] for r in sig], atol=1e-9)


# --------------------------------------------------------------------------- chord SDs
@needs_research
@pytest.mark.parametrize("sex,col", [("male", "model_sd_M"), ("female", "model_sd_F")])
def test_chord_sds_match_model_column(sex, col):
    T = _tables()
    table = T["model_vs_norm_chords"]
    j = table["columns"].index(col)
    prior = FactorPrior.from_package(sex=sex, population="matched", include_size=True, extra_depth_sigma_mm=0,
                                     rigid_invariance=False, tragion_floor=False)
    assert len(table["rows"]) >= 20
    for row in table["rows"]:
        a, b = row[0].split("-")
        assert abs(prior.chord_sd(a, b) - row[j]) < 0.06, (row[0], prior.chord_sd(a, b), row[j])


@needs_research
@pytest.mark.parametrize("sex", ["male", "female"])
def test_marginal_sds_match_research_mean_tables(sex):
    """The mean tables' sd_x/y/z columns are sqrt(diag) of the factor covariance (rounded to 0.1)."""
    rows = _tables()[f"mean_landmarks_{sex}_european_young_adult"]["rows"]
    prior = FactorPrior.from_package(sex=sex, population="matched", include_size=True, extra_depth_sigma_mm=0,
                                     rigid_invariance=False, tragion_floor=False)
    np.testing.assert_allclose(prior.marginal_sd(), np.array([r[5:8] for r in rows], float), atol=0.06)


# --------------------------------------------------------------------------- algebra
def _random_factor_prior(seed: int = 3, n: int = 9, K: int = 5) -> FactorPrior:
    rng = np.random.default_rng(seed)
    L = rng.normal(scale=3.0, size=(3 * n, K))
    A = rng.normal(size=(3 * n, 3 * n))
    R = A @ A.T / (3 * n) + 0.5 * np.eye(3 * n)
    return FactorPrior(rng.normal(scale=40.0, size=(n, 3)), L, R)


@pytest.mark.parametrize("which", ["default", "random"])
def test_woodbury_equals_dense(which):
    prior = FactorPrior.from_package() if which == "default" else _random_factor_prior()
    S = prior.cov()
    rng = np.random.default_rng(11)
    r = rng.normal(scale=5.0, size=S.shape[0])
    assert _rel(prior.solve(r), np.linalg.solve(S, r)) < 1e-9
    Rm = rng.normal(size=(S.shape[0], 4))
    assert _rel(prior.solve(Rm), np.linalg.solve(S, Rm)) < 1e-9
    W = prior.whiten_matrix()
    assert np.allclose(W, np.tril(W))  # inverse of a lower Cholesky factor
    Sinv = np.linalg.inv(S)
    assert _rel(W.T @ W, Sinv) < 1e-8
    np.testing.assert_allclose(prior.whiten(r), W @ r)
    X = prior.mean() + rng.normal(scale=2.0, size=prior.mean().shape)
    d = (X - prior.mean()).reshape(-1)
    assert prior.neg_log_density(X) == pytest.approx(0.5 * d @ Sinv @ d, rel=1e-8)
    assert prior.neg_log_density(X) == pytest.approx(0.5 * np.sum((W @ d) ** 2), rel=1e-8)


def test_default_prior_spd_mixture_kappa_depth():
    prior = FactorPrior.from_package()
    assert prior.ids == list(ANATOMICAL_IDS)
    prior.check_spd()
    np.linalg.cholesky(prior.cov())
    assert prior.meta["rigid_invariant"] is True
    assert prior.meta["sex"] == "unspecified" and prior.meta["population"] == "unknown"
    assert "size" not in " ".join(prior.meta["columns"])  # D-03: zeta carries size
    pkg = load_prior_package()
    np.testing.assert_allclose(prior.mean(), 0.5 * (pkg["sexes"]["M"]["mean"] + pkg["sexes"]["F"]["mean"]),
                               atol=1e-12)
    # extra face-depth factor: +6^2 mm^2 on prn z, nothing on the excluded tragion
    no_depth = FactorPrior.from_package(extra_depth_sigma_mm=0)
    k_prn = 3 * prior.ids.index("prn") + 2
    k_t = 3 * prior.ids.index("t_L") + 2
    assert prior.cov()[k_prn, k_prn] - no_depth.cov()[k_prn, k_prn] >= 36.0 - 1e-9
    assert prior.cov()[k_t, k_t] == pytest.approx(no_depth.cov()[k_t, k_t])
    # kappa: unknown population inflates en_L x by 2.5^2 (anat R4.4), other coords by 1.5^2
    kw = dict(extra_depth_sigma_mm=0, rigid_invariance=False)
    unknown = FactorPrior.from_package(population="unknown", **kw)
    matched = FactorPrior.from_package(population="matched", **kw)
    k = 3 * unknown.ids.index("en_L")
    assert unknown.cov()[k, k] / matched.cov()[k, k] == pytest.approx(2.5 ** 2, rel=0.01)
    k = 3 * unknown.ids.index("ex_L") + 1
    assert unknown.cov()[k, k] / matched.cov()[k, k] == pytest.approx(1.5 ** 2, rel=0.01)
    # balanced mixture covariance S = (S_M + S_F)/2 + delta delta^T / 4 (anat R5.5)
    kw = dict(population="matched", extra_depth_sigma_mm=0, rigid_invariance=False, include_size=True)
    mix = FactorPrior.from_package(**kw)
    SM = FactorPrior.from_package(sex="male", **kw).cov()
    SF = FactorPrior.from_package(sex="female", **kw).cov()
    delta = (pkg["sexes"]["M"]["mean"] - pkg["sexes"]["F"]["mean"]).reshape(-1)
    np.testing.assert_allclose(mix.cov(), 0.5 * (SM + SF) + 0.25 * np.outer(delta, delta), atol=1e-9)
    # tragion floor makes R positive definite; without it the inverse is refused, naming the ids
    bare = FactorPrior.from_package(tragion_floor=False)
    with pytest.raises(ValueError, match="t_L"):
        bare.solve(np.ones(132))


def test_rigid_invariance():
    """Rigid motions are almost free, a local shape change is not (DESIGN 4.6 G Lambda_g G^T).

    Expected rigid cost: 0.5 (10/100)^2 + 0.5 (0.0349/0.5)^2 ~ 0.0074 plus the
    second-order (non-tangent) part of the rotation.  The > 10 bound on prn z uses
    the matched-population prior: with the default kappa 1.5 the conditional prn-z
    SD is ~2.4 mm and the same change costs ~8.4 (still > 500x a rigid motion).
    """
    theta = np.radians(2.0)
    shift = np.array([6.0, -8.0, 0.0])  # 10 mm
    for population, bound in (("matched", 10.0), ("unknown", 5.0)):
        prior = FactorPrior.from_package(population=population)
        mu = prior.mean()
        c = mu.mean(axis=0)
        e0 = prior.neg_log_density(mu)
        assert e0 == pytest.approx(0.0, abs=1e-12)
        worst = 0.0
        for axis in np.eye(3):
            X = (mu - c) @ rodrigues(axis * theta).T + c + shift
            worst = max(worst, prior.neg_log_density(X) - e0)
        assert worst < 1e-2
        X = mu.copy()
        X[prior.ids.index("prn"), 2] += 10.0
        local = prior.neg_log_density(X) - e0
        assert local > bound
        assert local > 500 * worst
    # without the rigid columns the same rigid motion is expensive
    stiff = FactorPrior.from_package(rigid_invariance=False)
    mu = stiff.mean()
    assert stiff.meta["rigid_invariant"] is False
    assert stiff.neg_log_density(mu + shift) > 1.0


def test_no_ancestry_parameter():
    params = inspect.signature(FactorPrior.from_package).parameters
    pat = re.compile(r"ancestr|ethnic|(^|_)race($|_)", re.IGNORECASE)
    assert not [p for p in params if pat.search(p)]
    doc = json.loads(PACKAGE_PRIOR_PATH.read_text(encoding="utf-8"))

    def keys(o):
        if isinstance(o, dict):
            for k, v in o.items():
                yield k
                yield from keys(v)
        elif isinstance(o, list):
            for v in o:
                yield from keys(v)

    assert not [k for k in keys(doc) if pat.search(k)]
    assert doc["licence"] == "CC0-1.0" and doc["format"] == "face3d.landmark_prior" and doc["version"] == 1
    assert set(doc["sexes"]) == {"M", "F"}


# --------------------------------------------------------------------------- registry & schemes
def test_registry_and_scheme_mirror_involution():
    assert len(ANATOMICAL) == 44 and list(ANATOMICAL) == list(ANATOMICAL_IDS)
    assert list(ANATOMICAL_IDS) == load_prior_package()["ids"]
    en = ANATOMICAL["en_L"]
    assert (en.kind, en.region, en.expr_class, en.side, en.mirror_id) == ("sharp_junction", "eyes", "rigid", "L", "en_R")
    assert (en.sigma_n_mm, en.sigma_t_mm, en.sigma_def_mm, en.sym_sigma_mm) == (1.25, 1.25, 0.5, (0.85, 0.85, 0.85))
    assert ANATOMICAL["or_R"].sigma_def_mm == 2.0 and ANATOMICAL["prn"].sigma_def_mm == 1.5
    assert ANATOMICAL["tr"].kind == "hair" and ANATOMICAL["p_L"].kind == "iris" and ANATOMICAL["ls"].kind == "curve"
    assert ANATOMICAL["prn"].midline_sigma_mm == 1.75 and ANATOMICAL["n"].midline_sigma_mm == 0.9
    assert ANATOMICAL["v"].midline_sigma_mm == 2.0 and ANATOMICAL["prn"].sym_sigma_mm is None
    assert ANATOMICAL["go_L"].sym_sigma_mm == (2.75,) * 3 and ANATOMICAL["eu_R"].sym_sigma_mm == (3.5,) * 3
    assert [ANATOMICAL[i].jaw_weight for i in ("me", "sto", "ch_L", "go_R", "n")] == [1.0, 0.5, 0.4, 1.0, 0.0]
    assert {ANATOMICAL[i].base for i in anchor_ids()} == {"en", "ex", "p", "n", "prn", "sn", "ch", "ls", "li", "sto"}
    assert all(ANATOMICAL[ANATOMICAL[i].mirror_id].mirror_id == i for i in ANATOMICAL)

    for name in ("anatomical44", "legacy_synthetic"):
        sch = load_scheme(name)
        pi = sch.mirror_permutation()
        assert pi.dtype.kind == "i" and pi.shape == (sch.n,)
        np.testing.assert_array_equal(pi[pi], np.arange(sch.n))
        mid = [p.index for p in sch.points if p.side == "mid"]
        np.testing.assert_array_equal(pi[mid], mid)
        for p in sch.points:
            if p.side in ("L", "R"):
                q = sch.points[pi[p.index]]
                assert {p.side, q.side} == {"L", "R"} and q.name[:-2] == p.name[:-2]

    a44 = load_scheme("anatomical44")
    assert a44.n == 44 and all(p.verified for p in a44.points)
    assert a44.anatomical_index() == {lid: i for i, lid in enumerate(ANATOMICAL_IDS)}
    assert a44.kinds() == [ANATOMICAL[i].kind for i in ANATOMICAL_IDS]

    legacy = load_scheme("legacy_synthetic")
    names, _ = synthetic_landmarks()
    assert legacy.names() == names
    alias = {"pronasale": "prn", "subnasale": "sn", "labrale_superius": "ls", "stomion": "sto",
             "labrale_inferius": "li", "pogonion": "pg", "menton": "me", "glabella": "g", "nasion": "n",
             "endocanthion": "en", "exocanthion": "ex", "pupil": "p", "alare": "al", "cheilion": "ch",
             "zygion": "zy", "gonion": "go", "tragion": "t"}
    null_kind = {"vertex_front": "extremal", "brow_inner": "brow", "brow_outer": "brow", "forehead_side": "extremal"}
    for p in legacy.points:
        side = p.name[-2:] if p.name.endswith(("_L", "_R")) else ""
        base = p.name[:-2] if side else p.name
        if base in alias:
            assert p.anatomical_id == alias[base] + side, p.name
            assert p.kind == ANATOMICAL[p.anatomical_id].kind
        else:
            assert p.anatomical_id is None and p.kind == null_kind[base], p.name
    assert "not in the fh prior frame" in legacy.notes.lower()


def _scheme_doc(**over):
    doc = {"format": "face3d.scheme", "version": 1, "scheme": "tiny", "n": 3,
           "points": [{"index": 0, "name": "a_L", "anatomical_id": None, "kind": "generic", "side": "L",
                       "verified": False, "badge": "🆕"},
                      {"index": 1, "name": "a_R", "anatomical_id": None, "kind": "generic", "side": "R",
                       "verified": False, "badge": "🆕"},
                      {"index": 2, "name": "m", "anatomical_id": "prn", "kind": "extremal", "side": "mid",
                       "verified": False, "badge": "🆕"}],
           "polylines": {}, "mirror_pairs": [[1, 0]], "lr_groups": [], "z_policy": "ignore"}
    doc.update(over)
    return doc


def test_scheme_validation_rejects_bad_pairs(tmp_path):
    sch = Scheme(_scheme_doc())
    np.testing.assert_array_equal(sch.mirror_permutation(), [1, 0, 2])
    with pytest.raises(ValueError, match="midline"):
        Scheme(_scheme_doc(mirror_pairs=[[2, 0]])).mirror_permutation()
    with pytest.raises(ValueError, match="more than one"):
        Scheme(_scheme_doc(mirror_pairs=[[1, 0], [0, 1]])).mirror_permutation()
    with pytest.raises(ValueError):
        Scheme(_scheme_doc(points=_scheme_doc()["points"][:2]))  # n mismatch
    bad = _scheme_doc()
    bad["points"][2]["anatomical_id"] = "en_L"  # side disagrees with the registry
    with pytest.raises(ValueError, match="side"):
        Scheme(bad)
    path = tmp_path / "tiny.json"
    path.write_text(json.dumps(_scheme_doc()), encoding="utf-8")
    assert load_scheme("tiny", path=tmp_path).names() == ["a_L", "a_R", "m"]
    with pytest.raises(ValueError):
        load_scheme("other", path=path)


# --------------------------------------------------------------------------- L/R resolution
def _eye_rings(cam: Camera, centres: dict) -> dict:
    ang = np.linspace(0.0, 2 * np.pi, 5, endpoint=False)
    out = {}
    for side, c in centres.items():
        ring = c + 5.9 * np.column_stack([np.cos(ang), np.sin(ang), np.zeros_like(ang)])
        out[side] = cam.project(np.vstack([c, ring]))
    return out


def test_resolve_lr():
    ids, mu = prior_mean()
    centres = {"L": mu[ids.index("p_L")], "R": mu[ids.index("p_R")]}
    for yaw in (-30.0, 0.0, 35.0):
        a = np.radians(yaw)
        eye = np.array([0.0, 10.0, 80.0]) + 450.0 * np.array([np.sin(a), 0.0, np.cos(a)])
        R, t = look_at(eye, np.array([0.0, 10.0, 80.0]))
        cam = Camera.centered(3000.0, 3000, 4000, R=R, t=t)
        rings = _eye_rings(cam, centres)
        groups = {"g468": rings["L"], "g473": rings["R"]}
        assign, amb = resolve_lr(groups, camera=cam, eye_centres_world=centres)
        assert assign == {"g468": "L", "g473": "R"} and not amb
        assign, amb = resolve_lr({"x": rings["R"], "y": rings["L"]}, camera=cam, eye_centres_world=centres)
        assert assign == {"x": "R", "y": "L"} and not amb
        # mirrored image: uv reflected u' = W - u; the flag restores the true sides
        mirrored = {k: np.column_stack([cam.width - v[:, 0], v[:, 1]]) for k, v in groups.items()}
        assign, amb = resolve_lr(mirrored, camera=cam, eye_centres_world=centres, image_mirrored=True)
        assert assign == {"g468": "L", "g473": "R"} and not amb
        assign, _ = resolve_lr(mirrored, camera=cam, eye_centres_world=centres)
        assert assign == {"g468": "R", "g473": "L"}
        # a group midway between the projected eyes is ambiguous
        P = cam.project(np.array([centres["L"], centres["R"]]))
        mid = 0.5 * (P[0] + P[1]) + np.array([3.0, 0.0])
        _, amb = resolve_lr({"a": mid[None, :], "b": rings["R"]}, camera=cam, eye_centres_world=centres)
        assert amb
        # both groups nearest the same eye -> ambiguous, best joint assignment kept
        assign, amb = resolve_lr({"a": rings["L"], "b": rings["L"] + 1.0}, camera=cam, eye_centres_world=centres)
        assert amb and sorted(assign.values()) == ["L", "R"]

    # camera-free rule: subject-left = larger u in a non-mirrored image; mirrored swaps
    g = {"a": np.array([[1610.0, 900.0], [1590.0, 905.0]]), "b": np.array([[1400.0, 900.0], [np.nan, np.nan]])}
    assert resolve_lr(g, face_midline_u=1500.0) == ({"a": "L", "b": "R"}, False)
    assert resolve_lr(g, face_midline_u=1500.0, image_mirrored=True) == ({"a": "R", "b": "L"}, False)
    assert resolve_lr(g) == ({"a": "L", "b": "R"}, False)
    _, amb = resolve_lr({"a": np.array([[1500.5, 900.0]]), "b": np.array([[1499.5, 900.0]])})
    assert amb
    _, amb = resolve_lr(g, face_midline_u=1300.0)  # both groups on one side of the midline
    assert amb
    assert resolve_lr({"a": g["a"]}, face_midline_u=1500.0) == ({"a": "L"}, False)


# --------------------------------------------------------------------------- subset / composite
def test_subset_marginal_and_composite():
    prior = FactorPrior.from_package()
    sub_ids = ["prn", "en_R", "n", "ch_L", "t_L"]
    sub = prior.subset(sub_ids)
    rows = np.concatenate([np.arange(3) + 3 * prior.ids.index(i) for i in sub_ids])
    np.testing.assert_allclose(sub.cov(), prior.cov()[np.ix_(rows, rows)], atol=1e-10)
    np.testing.assert_allclose(sub.mean(), prior.mean()[[prior.ids.index(i) for i in sub_ids]])
    assert sub.ids == sub_ids and sub.meta["rigid_invariant"] is True
    assert isinstance(sub, LandmarkPrior) and isinstance(sub, GeneralisedPrior)

    # two parts on a global array of N points (FactorPrior subset + DiagonalPrior)
    rng = np.random.default_rng(5)
    a_ids = ["en_L", "en_R", "ex_L", "ex_R", "prn", "sn", "ch_L", "ch_R"]
    part_a = prior.subset(a_ids)
    part_b = DiagonalPrior(rng.normal(scale=30.0, size=(4, 3)), rng.uniform(1.0, 3.0, size=(4, 3)))
    N = 15
    idx_a = np.array([0, 2, 4, 6, 8, 10, 12, 14])
    idx_b = np.array([1, 3, 5, 7])
    comp = CompositePrior([(part_a, idx_a), (part_b, idx_b)], n_total=N)
    X = rng.normal(scale=50.0, size=(N, 3))
    r = comp.residual(X)
    ra = part_a.whiten((X[idx_a] - part_a.mean()).reshape(-1))
    rb = part_b.whiten((X[idx_b] - part_b.mean()).reshape(-1))
    assert r.shape == (24 + 12,)
    assert float(r @ r) == pytest.approx(float(ra @ ra + rb @ rb), rel=1e-12)
    expected = part_a.neg_log_density(X[idx_a]) + part_b.neg_log_density(X[idx_b])
    assert comp.neg_log_density(X) == pytest.approx(expected, rel=1e-9)
    # block-structured whitening in the global order; residual is affine with that Jacobian
    Wg = comp.whiten_matrix()
    assert Wg.shape == (36, 3 * N)
    cols_b = (3 * idx_b[:, None] + np.arange(3)).reshape(-1)
    assert np.all(Wg[:24, cols_b] == 0.0)
    dX = rng.normal(size=(N, 3))
    np.testing.assert_allclose(comp.residual(X + dX) - comp.residual(X), Wg @ dX.reshape(-1), atol=1e-9)
    np.testing.assert_allclose(comp.jacobian(X), Wg)
    assert comp.meta["rigid_invariant"] is False  # the diagonal part is not
    # points 9, 11, 13 are unconstrained: the product has no proper mean
    with pytest.raises(ValueError):
        comp.mean()
    # a covering composite reproduces the parts' means and block covariances
    idx_b2 = np.array([1, 3, 5, 7])
    part_c = DiagonalPrior(np.zeros((3, 3)), 2.0)
    full = CompositePrior([(part_a, idx_a), (part_b, idx_b2), (part_c, np.array([9, 11, 13]))], n_total=N)
    np.testing.assert_allclose(full.mean()[idx_a], part_a.mean(), atol=1e-8)
    cols_a = (3 * idx_a[:, None] + np.arange(3)).reshape(-1)
    np.testing.assert_allclose(full.cov()[np.ix_(cols_a, cols_a)], part_a.cov(), rtol=1e-7, atol=1e-6)
    # overlapping parts add their energies
    over = CompositePrior([(part_a, idx_a), (part_a, idx_a)], n_total=N)
    assert over.neg_log_density(X) == pytest.approx(2 * part_a.neg_log_density(X[idx_a]), rel=1e-9)
    # a bound prior is accepted as-is (generalised interface)
    bound = part_a.with_index(idx_a)
    np.testing.assert_allclose(CompositePrior([bound], n_total=N).residual(X), ra)
    np.testing.assert_allclose(bound.jacobian(X), Wg[:24])


def test_rigid_gauge_rows_and_diagonal_prior():
    prior = FactorPrior.from_package()
    G = prior.rigid_gauge_rows()
    assert G.shape == (6, 132)
    np.testing.assert_allclose(np.linalg.norm(G, axis=1), 1.0)
    assert np.linalg.matrix_rank(G) == 6
    anchors = {prior.ids.index(i) for i in anchor_ids()}
    off = [k for k in range(132) if k // 3 not in anchors]
    assert np.all(G[:, off] == 0.0)
    # bases expand to both sides; ints are local indices
    np.testing.assert_allclose(prior.rigid_gauge_rows(["en", "n", "prn"]),
                               prior.rigid_gauge_rows(["en_L", "en_R", 3, 4]))
    # translation rows read translations only; rotations about the anchor centroid leave them at 0
    mu = prior.mean().reshape(-1)
    t = np.tile([1.0, 0.0, 0.0], 44)
    g = G @ t
    assert abs(g[0]) > 0.1 and np.all(np.abs(g[1:]) < 1e-12)
    A = sorted(anchors)
    c = prior.mean()[A].mean(axis=0)
    rot = (np.cross([0.0, 1.0, 0.0], prior.mean() - c)).reshape(-1)
    g = G @ rot
    assert abs(g[4]) > 0.1 and np.all(np.abs(g[:3]) < 1e-9)
    assert mu.shape == (132,)

    dp = DiagonalPrior(np.zeros((2, 3)), [[1.0, 2.0, 4.0], [1.0, 1.0, 1.0]], ids=["a", "b"])
    assert isinstance(dp, LandmarkPrior)
    r = np.array([1.0, 2.0, 4.0, 0.0, 0.0, 3.0])
    np.testing.assert_allclose(dp.solve(r), [1.0, 0.5, 0.25, 0.0, 0.0, 3.0])
    assert dp.neg_log_density(r) == pytest.approx(0.5 * (1 + 1 + 1 + 9))
    np.testing.assert_allclose(dp.whiten_matrix().T @ dp.whiten_matrix(), np.linalg.inv(dp.cov()))
    np.testing.assert_allclose(dp.subset(["b"]).cov(), np.eye(3))
    assert dp.meta["rigid_invariant"] is False
    with pytest.raises(ValueError, match="b.y"):
        DiagonalPrior(np.zeros((2, 3)), [[1.0, 1.0, 1.0], [1.0, 0.0, 1.0]], ids=["a", "b"])
