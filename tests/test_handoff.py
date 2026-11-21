"""WP-13: shape-key stack (exact rebase, Basis propagation, masks) and Catmull-Clark
limit stencils with limit-surface cage fitting (DESIGN D-21, D-22, 4.17).

Acceptance tests from docs/wbs.json (WP-13) plus supporting checks.
"""
from __future__ import annotations

import numpy as np
import pytest

from face3d.core import config
from face3d.handoff.keys import (ARTIST, ASYM, BASIS, ID, STAGE_PREFIX, Key, KeyStack,
                                 TopologyMismatch, mask_to_data_weights, protect_mask,
                                 topology_guard)
from face3d.mesh.subdiv import (catmull_clark, fit_cage_to_limit, is_closed, limit_positions,
                                limit_stencil_matrix, quad_edges, quad_one_rings, subdivide_levels)
from face3d.model import template_kit
from face3d.model.procedural_head import build_procedural_head, cube_sphere, signed_volume
from face3d.model.template_kit import fan_triangles, topology_sha256


# =========================================================================== fixtures
def _cube() -> tuple[np.ndarray, np.ndarray]:
    """Unit cube [-1, 1]^3 with 6 outward-oriented quads."""
    V = np.array([[x, y, z] for x in (-1.0, 1.0) for y in (-1.0, 1.0) for z in (-1.0, 1.0)])

    def i(x, y, z):
        return (x > 0) * 4 + (y > 0) * 2 + (z > 0)

    F = np.array([
        [i(1, -1, -1), i(1, 1, -1), i(1, 1, 1), i(1, -1, 1)],
        [i(-1, -1, -1), i(-1, -1, 1), i(-1, 1, 1), i(-1, 1, -1)],
        [i(-1, 1, -1), i(-1, 1, 1), i(1, 1, 1), i(1, 1, -1)],
        [i(-1, -1, -1), i(1, -1, -1), i(1, -1, 1), i(-1, -1, 1)],
        [i(-1, -1, 1), i(1, -1, 1), i(1, 1, 1), i(-1, 1, 1)],
        [i(-1, -1, -1), i(-1, 1, -1), i(1, 1, -1), i(1, -1, -1)],
    ], dtype=np.int64)
    return V, F


def _grid(nx: int, ny: int) -> tuple[np.ndarray, np.ndarray]:
    """Open planar (nx x ny)-quad grid in z = 0, vertex (i, j) at index j * (nx + 1) + i."""
    xs, ys = np.meshgrid(np.arange(nx + 1, dtype=float), np.arange(ny + 1, dtype=float))
    V = np.stack([xs.ravel(), ys.ravel(), np.zeros(xs.size)], axis=1)
    F = []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            F.append([a, a + 1, a + nx + 2, a + nx + 1])
    return V, np.asarray(F, np.int64)


def _valence5_disk() -> tuple[np.ndarray, np.ndarray]:
    """Open disk: one interior vertex of valence 5 surrounded by 5 quads (non-planar ring)."""
    V = [[0.0, 0.0, 0.3]]
    for k in range(5):
        a = 2 * np.pi * k / 5
        V.append([np.cos(a), np.sin(a), 0.1 * np.cos(2 * a)])            # edge neighbour
        b = 2 * np.pi * (k + 0.5) / 5
        V.append([1.6 * np.cos(b), 1.6 * np.sin(b), -0.2 + 0.05 * k])    # diagonal
    F = []
    for k in range(5):
        e0, d, e1 = 1 + 2 * k, 2 + 2 * k, 1 + 2 * ((k + 1) % 5)
        F.append([0, e0, d, e1])
    return np.asarray(V), np.asarray(F, np.int64)


@pytest.fixture(scope="module")
def head16():
    return build_procedural_head(n=16)


def _rand_stack(rng, n=50):
    basis = rng.normal(0.0, 60.0, (n, 3))
    id_fit = basis + rng.normal(0.0, 4.0, (n, 3))
    asym = rng.normal(0.0, 0.5, (n, 3))
    stages = {"A": basis + rng.normal(0.0, 1.0, (n, 3)), "stage_B": basis + 1.0}
    return basis, id_fit, asym, stages


# =========================================================================== keys
def test_from_fit_layout():
    rng = np.random.default_rng(1)
    basis, id_fit, asym, stages = _rand_stack(rng)
    ks = KeyStack.from_fit(basis, id_fit, asym, stages)
    assert list(ks.keys) == [ID, ASYM, ARTIST, STAGE_PREFIX + "A", "stage_B"]
    k = ks.keys
    assert k[ID].relative_to == BASIS and k[ID].value == 1.0 and k[ID].slider_max == 1.5
    assert k[ASYM].relative_to == ID and k[ASYM].value == 1.0
    assert k[ARTIST].relative_to == ID and k[ARTIST].value == 1.0
    for s in ("stage_A", "stage_B"):
        assert k[s].relative_to == BASIS and k[s].value == 0.0 and k[s].mute
    np.testing.assert_array_equal(k[ID].data, id_fit)
    np.testing.assert_array_equal(k[ARTIST].data, id_fit)
    assert k[ARTIST].data is not k[ID].data            # independent copies
    np.testing.assert_allclose(ks.evaluate(), id_fit + asym, atol=1e-12)
    np.testing.assert_array_equal(ks.artist_delta(), 0.0)
    # asym_delta None -> Asym equals ID_fit.
    ks0 = KeyStack.from_fit(basis, id_fit)
    np.testing.assert_array_equal(ks0.keys[ASYM].data, id_fit)
    assert list(ks0.keys) == [ID, ASYM, ARTIST]


def test_rebase_exact():
    rng = np.random.default_rng(7)
    basis, id_fit, asym, stages = _rand_stack(rng, n=200)
    ks = KeyStack.from_fit(basis, id_fit, asym, stages)
    sculpt = rng.normal(0.0, 2.0, (200, 3))
    ks.keys[ARTIST].data = ks.keys[ARTIST].data + sculpt
    old_artist_delta = ks.artist_delta().copy()
    old_asym_own = ks.delta(ASYM).copy()
    old_stage = ks.keys["stage_A"].data.copy()

    new_id = id_fit + rng.normal(0.0, 3.0, (200, 3))
    ks.rebase(new_id)
    np.testing.assert_array_equal(ks.keys[ID].data, new_id)             # exact float64
    assert np.abs((ks.keys[ARTIST].data - new_id) - old_artist_delta).max() < 1e-9
    assert np.abs(ks.artist_delta() - sculpt).max() < 1e-9
    assert np.abs(ks.delta(ASYM) - old_asym_own).max() < 1e-9          # Asym.data += delta
    np.testing.assert_array_equal(ks.keys["stage_A"].data, old_stage)   # stages untouched
    np.testing.assert_allclose(ks.evaluate(), new_id + asym + sculpt, atol=1e-9)

    # With a new asymmetry the Asym key is replaced: data = new_id + new_asym_delta.
    new_id2 = new_id + rng.normal(0.0, 1.0, (200, 3))
    new_asym = rng.normal(0.0, 0.3, (200, 3))
    ks.rebase(new_id2, new_asym)
    assert np.abs(ks.keys[ASYM].data - (new_id2 + new_asym)).max() < 1e-12
    assert np.abs(ks.artist_delta() - sculpt).max() < 1e-9


def test_rebase_keeps_chained_dependents():
    rng = np.random.default_rng(3)
    basis, id_fit, asym, _ = _rand_stack(rng, n=20)
    ks = KeyStack.from_fit(basis, id_fit, asym)
    extra = rng.normal(0.0, 1.0, (20, 3))
    ks.keys["detail"] = Key(ks.keys[ARTIST].data + extra, ARTIST, value=1.0)
    ks.keys["regional"] = Key(basis + 0.5, BASIS, value=0.3)
    ks.validate()
    reg = ks.keys["regional"].data.copy()
    ks.rebase(id_fit + 5.0)
    assert np.abs(ks.delta("detail") - extra).max() < 1e-9
    np.testing.assert_array_equal(ks.keys["regional"].data, reg)


def test_basis_write_propagates():
    rng = np.random.default_rng(11)
    basis, id_fit, asym, stages = _rand_stack(rng, n=120)
    ks = KeyStack.from_fit(basis, id_fit, asym, stages)
    ks.keys[ARTIST].data = ks.keys[ARTIST].data + rng.normal(0.0, 1.5, (120, 3))
    before = ks.evaluate()
    art = ks.artist_delta().copy()
    deltas = {k: ks.delta(k).copy() for k in ks.keys}
    d = rng.normal(0.0, 2.0, (120, 3))
    ks.write_basis(basis + d)
    np.testing.assert_allclose(ks.evaluate(), before + d, atol=1e-9)
    assert np.abs(ks.artist_delta() - art).max() < 1e-9
    for k, v in deltas.items():
        assert np.abs(ks.delta(k) - v).max() < 1e-9
    # Also with a caricature value and an un-muted stage key.
    ks.keys[ID].value = 1.3
    ks.keys["stage_A"].mute = False
    ks.keys["stage_A"].value = 0.4
    before = ks.evaluate()
    ks.write_basis(ks.basis - d)
    np.testing.assert_allclose(ks.evaluate(), before - d, atol=1e-9)


def test_evaluate_blender_relative_semantics():
    B = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    A = B + np.array([[1.0, 0, 0], [0, 0, 0], [0, 0, 0]])      # own delta (1,0,0) at v0
    C = A + np.array([[0.0, 0, 0], [0, 2, 0], [0, 0, 0]])      # relative to A: (0,2,0) at v1
    D = C + np.array([[0.0, 0, 0], [0, 0, 0], [0, 0, 3]])      # relative to C: (0,0,3) at v2
    ks = KeyStack(B, {
        "A": Key(A, BASIS, value=0.5),
        "C": Key(C, "A", value=1.0),
        "D": Key(D, "C", value=0.25),
        "M": Key(B + 10.0, BASIS, value=1.0, mute=True),
    })
    # Hand-computed: each key adds value * (its data - its reference's STORED data).
    expected = np.array([[0.5, 0.0, 0.0], [1.0, 2.0, 0.0], [0.0, 1.0, 0.75]])
    np.testing.assert_allclose(ks.evaluate(), expected, atol=1e-15)
    # Muting the reference key does not change a dependent's delta (stored data, not mix).
    ks.keys["A"].mute = True
    np.testing.assert_allclose(ks.evaluate(), expected - [[0.5, 0, 0], [0, 0, 0], [0, 0, 0]], atol=1e-15)
    # A key at value 0 contributes nothing.
    ks.keys["C"].value = 0.0
    np.testing.assert_allclose(ks.evaluate(), [[0, 0, 0], [1, 0, 0], [0, 1, 0.75]], atol=1e-15)


def test_keystack_validation():
    B = np.zeros((3, 3))
    with pytest.raises(ValueError):
        KeyStack(B, {"x": Key(np.zeros((3, 3)), "nope")})
    with pytest.raises(ValueError):
        KeyStack(B, {BASIS: Key(np.zeros((3, 3)), BASIS)})
    with pytest.raises(ValueError):
        KeyStack(B, {"x": Key(np.zeros((4, 3)), BASIS)})
    with pytest.raises(ValueError):
        KeyStack(B, {"a": Key(B, "b"), "b": Key(B, "a")})
    with pytest.raises(ValueError):
        KeyStack(B, {"a": Key(B, "a")})
    with pytest.raises(ValueError):
        Key(np.full((3, 3), np.nan), BASIS)
    ks = KeyStack(B, {"a": Key(B, BASIS)})
    assert ks.relative_chain("a") == ["a", BASIS]
    with pytest.raises(KeyError):
        ks.rebase(B)          # no ID_fit key
    # copy() is deep.
    ks2 = KeyStack.from_fit(B, B + 1.0)
    cp = ks2.copy()
    cp.keys[ARTIST].data[0, 0] = 99.0
    assert ks2.keys[ARTIST].data[0, 0] == 1.0


def test_protect_mask_and_weights():
    s = np.array([-0.2, 0.0, 0.3, 1.0, 1.5])
    np.testing.assert_allclose(protect_mask(s), 1.0 - np.array([1.0, 1.0, 0.7, 0.0, 0.0]))  # mask = support (measured -> locked)
    m = np.array([0.0, 0.25, 0.5, 0.51, 1.0, 1.2, -0.1])
    w, sig = mask_to_data_weights(m)
    np.testing.assert_allclose(w, [1.0, 0.75, 0.5, 0.49, 0.0, 0.0, 1.0])
    assert np.all(np.isinf(sig[[0, 1, 2, 6]]))                     # m <= 0.5: no pin
    np.testing.assert_allclose(sig[[3, 4, 5]], 0.2)                   # pin at sigma 0.2 mm
    # Registered, badged defaults (DESIGN 4.17 / bl W5).
    assert config.get("handoff.mask_pin_sigma_mm").value == 0.2
    assert config.get("handoff.mask_pin_threshold").value == 0.5
    assert config.get("handoff.id_fit_slider_max").value == 1.5
    w2, sig2 = mask_to_data_weights(m, pin_sigma_mm=0.1, threshold=0.2)
    np.testing.assert_allclose(sig2[[1, 2, 3, 4, 5]], 0.1)
    assert np.isinf(sig2[0]) and np.isinf(sig2[6])
    np.testing.assert_allclose(w2, w)
    with pytest.raises(ValueError):
        protect_mask(np.array([0.1, np.nan]))
    with pytest.raises(ValueError):
        mask_to_data_weights(np.zeros((3, 2)))


def test_topology_guard_raises():
    V, F = _cube()
    sha = topology_sha256(len(V), F)
    topology_guard(sha, sha)
    topology_guard(sha, sha.upper())
    V1, F1 = catmull_clark(V, F)
    with pytest.raises(TopologyMismatch):
        topology_guard(sha, topology_sha256(len(V1), F1))
    with pytest.raises(ValueError):          # TopologyMismatch is a ValueError
        topology_guard(sha, "0" * 64)
    assert TopologyMismatch is template_kit.TopologyMismatch   # one exception type engine-wide


# =========================================================================== Catmull-Clark
def test_cc_cube_topology_and_convergence():
    V, F = _cube()
    assert is_closed(F)
    V1, F1 = catmull_clark(V, F)
    assert V1.shape == (26, 3) and F1.shape == (24, 4)
    assert is_closed(F1)
    E1 = quad_edges(F1)
    assert len(V1) - len(E1) + len(F1) == 2                           # Euler characteristic
    # Consistent orientation: every directed half-edge appears exactly once; outward volume.
    he = np.stack([F1.ravel(), np.roll(F1, -1, axis=1).ravel()], axis=1)
    assert len(np.unique(he, axis=0)) == len(he)
    assert signed_volume(V1, fan_triangles(F1)) > 0
    # Hand values: corner -> 5/9 (valence 3), edge point (3/4, 3/4, 0), face point (1, 0, 0).
    np.testing.assert_allclose(V1[7], [5 / 9, 5 / 9, 5 / 9], atol=1e-15)
    E = quad_edges(F)
    k = int(np.flatnonzero((E[:, 0] == 6) & (E[:, 1] == 7))[0])     # (1,1,-1)-(1,1,1)
    np.testing.assert_allclose(V1[8 + k], [0.75, 0.75, 0.0], atol=1e-15)
    np.testing.assert_allclose(V1[8 + 12 + 0], [1.0, 0.0, 0.0], atol=1e-15)
    # Limit positions of the original vertices vs 6 subdivision levels (indices are kept).
    lim = limit_positions(V, F)
    np.testing.assert_allclose(lim[7], [0.5, 0.5, 0.5], atol=1e-15)   # (9v + 4Se + Sf)/24
    V6, F6 = subdivide_levels(V, F, 6)
    assert F6.shape == (6 * 4 ** 6, 4)
    diag = np.linalg.norm(V.max(0) - V.min(0))
    assert np.abs(V6[:8] - lim).max() / diag < 1e-3


def test_limit_stencil_regular_weights():
    V, F = _grid(3, 3)                       # vertex 5 = (1, 1) is interior, valence 4
    S = limit_stencil_matrix(len(V), F).toarray()
    edge_nb, diag_nb = quad_one_rings(len(V), F)[5]
    assert sorted(edge_nb) == [1, 4, 6, 9] and sorted(diag_nb) == [0, 2, 8, 10]
    row = S[5]
    assert row[5] == pytest.approx(16 / 36, abs=1e-15)
    for j in edge_nb:
        assert row[j] == pytest.approx(4 / 36, abs=1e-15)
    for j in diag_nb:
        assert row[j] == pytest.approx(1 / 36, abs=1e-15)
    assert np.count_nonzero(row) == 9
    # Boundary vertex 1 (bottom edge): (1/6, 4/6, 1/6) of its boundary neighbours 0 and 2.
    np.testing.assert_allclose(S[1, [0, 1, 2]], [1 / 6, 4 / 6, 1 / 6], atol=1e-15)
    assert np.count_nonzero(S[1]) == 3
    np.testing.assert_allclose(S.sum(axis=1), 1.0, atol=1e-15)
    # Planar input: limit and subdivision stay planar and inside the grid.
    V2, _ = subdivide_levels(V, F, 2)
    assert np.all(V2[:, 2] == 0.0)


def test_limit_stencils_irregular_and_boundary_converge():
    """Valence 3/4/5 and boundary limit stencils agree with deep subdivision."""
    for V, F, levels in (_valence5_disk() + (7,), _grid(3, 2) + (7,)):
        rng = np.random.default_rng(5)
        V = V + rng.normal(0.0, 0.05, V.shape)
        lim = limit_positions(V, F)
        Vk, _ = subdivide_levels(V, F, levels)
        diag = np.linalg.norm(V.max(0) - V.min(0))
        assert np.abs(Vk[:len(V)] - lim).max() / diag < 1e-3
    # Valence-5 row: n^2/(n(n+5)) = 5/10 centre, 4/50 edge, 1/50 diagonal.
    V, F = _valence5_disk()
    S = limit_stencil_matrix(len(V), F).toarray()
    assert S[0, 0] == pytest.approx(0.5) and S[0, 1] == pytest.approx(0.08) and S[0, 2] == pytest.approx(0.02)
    # quad_one_rings agrees with the matrix on the cube-sphere (valence 3 and 4).
    cs = cube_sphere(4)
    Vc, Fc = cs["sphere"], cs["faces"]
    Sc = limit_stencil_matrix(len(Vc), Fc).toarray()
    for v, (enb, dnb) in enumerate(quad_one_rings(len(Vc), Fc)):
        n = len(enb)
        assert len(dnb) == n
        expect = np.zeros(len(Vc))
        expect[v] = n * n
        expect[enb] += 4.0
        np.add.at(expect, dnb, 1.0)
        np.testing.assert_allclose(Sc[v], expect / (n * (n + 5)), atol=1e-15)


def test_cc_input_validation():
    V, F = _cube()
    with pytest.raises(ValueError):
        catmull_clark(V, F[:, :3])                    # not quads
    with pytest.raises(ValueError):
        catmull_clark(V, np.array([[0, 0, 1, 2]]))   # degenerate quad
    bad = np.concatenate([F, F[:1]])                  # duplicated face -> edges shared 3x
    with pytest.raises(ValueError):
        catmull_clark(V, bad)
    assert not is_closed(_grid(2, 2)[1])


# =========================================================================== cage fit
def test_cage_fit_removes_shrink(head16):
    T, F = head16.vertices, np.asarray(head16.faces)
    assert len(T) == 1538
    S = limit_stencil_matrix(len(T), F)

    def rms_max(C):
        e = np.linalg.norm(S @ C - T, axis=1)
        return float(np.sqrt(np.mean(e ** 2))), float(e.max())

    naive_rms, naive_max = rms_max(T)
    assert naive_rms >= 0.1
    C = fit_cage_to_limit(T, F)
    fit_rms, fit_max = rms_max(C)
    assert fit_rms < 0.01 and fit_max < 0.02
    assert fit_rms < naive_rms / 50
    # Same answer through limit_positions; deterministic.
    np.testing.assert_allclose(limit_positions(C, F), S @ C, atol=0)
    np.testing.assert_array_equal(fit_cage_to_limit(T, F), C)
    # mu = 0 interpolates to solver precision (S is square and well conditioned).
    C0 = fit_cage_to_limit(T, F, mu=0.0, tol=1e-12)
    assert rms_max(C0)[1] < 1e-6
    # Multires L3 of the fitted cage sits closer to the targets than the naive cage.
    V3f, _ = subdivide_levels(C, F, 3)
    V3n, _ = subdivide_levels(T, F, 3)
    err_f = np.linalg.norm(V3f[:len(T)] - T, axis=1).max()
    err_n = np.linalg.norm(V3n[:len(T)] - T, axis=1).max()
    assert err_f < err_n


def test_limit_stencil_condition_number(head16):
    """DESIGN 4.17: cond(S_lim) ~ 9 on the 1,538-vertex cube-sphere head."""
    F = np.asarray(head16.faces)
    S = limit_stencil_matrix(len(head16.vertices), F).toarray()
    np.testing.assert_allclose(S.sum(axis=1), 1.0, atol=1e-14)
    assert 7.0 < np.linalg.cond(S) < 11.0
    assert config.get("subdiv.cage_fit_mu").value == 1e-5


def test_cage_fit_open_mesh():
    V, F = _grid(4, 3)
    rng = np.random.default_rng(2)
    T = V + np.c_[np.zeros((len(V), 2)), rng.normal(0.0, 0.3, len(V))]
    naive = np.abs(limit_positions(T, F) - T).max()
    C = fit_cage_to_limit(T, F)
    # mu-bias only (the open corners need cage offsets of ~0.4 units).
    assert np.abs(limit_positions(C, F) - T).max() < 2e-3 < naive / 50
    C0 = fit_cage_to_limit(T, F, mu=0.0, tol=1e-13)
    assert np.abs(limit_positions(C0, F) - T).max() < 1e-9
    with pytest.raises(ValueError):
        fit_cage_to_limit(T, F, mu=-1.0)


def test_topology_guard_rejects_missing_or_malformed_hashes():
    good = "a" * 64
    topology_guard(good, good.upper())
    for bad in [(None, None), (good, None), ("", ""), ("abc", "abc"), (good, "g" * 64)]:
        with pytest.raises(TopologyMismatch):
            topology_guard(*bad)


def test_validate_rejects_non_finite_assigned_data():
    from face3d.handoff.keys import Key, KeyStack
    B = np.zeros((2, 3))
    ks = KeyStack(basis=B, keys={"ID_fit": Key(data=B + 1.0, relative_to="Basis")})
    ks.keys["ID_fit"].data = np.full((2, 3), np.nan)
    with pytest.raises(ValueError):
        ks.validate()
