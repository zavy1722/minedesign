"""WP-12: reflection Procrustes, symmetry-plane fit, evidence-gated sigmas, S/Asym split, checks.

DESIGN D-15, 4.11 and 4.15 stage A.  Fixtures are synthetic: the packaged
expert-prior landmark mean (CC0, exactly mirror-symmetric) and the procedural
CC0 head (WP-08); no third-party geometry (DESIGN D-26).
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from face3d.core import config
from face3d.fit.symmetry import (FACE_REGIONS, SYM, SymmetryTerm, check_mirror_map, detect_mirrored_source,
                                 face_vertex_mask, gate_symmetry_sigmas, midline_sigmas, mirror_rmsd,
                                 pair_sigmas, plane_group, plane_weights, split_symmetric, symmetry_checks)
from face3d.geometry.procrustes import (apply_similarity, fit_symmetry_plane, permute_pairs, reflect,
                                        reflection_matrix, umeyama, umeyama_proper_and_reflected)
from face3d.geometry.rotations import rodrigues
from face3d.model.landmark_prior import prior_mean
from face3d.model.registry import ANATOMICAL


# ----------------------------------------------------------------------------- fixtures
def _legacy_umeyama(src, dst, with_scale=True, weights=None):
    """Verbatim copy of the pre-WP-12 implementation (reference for 'unchanged by default')."""
    src = np.asarray(src, float)
    dst = np.asarray(dst, float)
    n, d = src.shape
    w = np.ones(n) if weights is None else np.asarray(weights, float)
    w = w / w.sum()
    mu_s = w @ src
    mu_d = w @ dst
    xs = src - mu_s
    xd = dst - mu_d
    cov = (xd * w[:, None]).T @ xs
    U, S, Vt = np.linalg.svd(cov)
    D = np.eye(d)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        D[-1, -1] = -1.0
    R = U @ D @ Vt
    if with_scale:
        var_s = float(w @ np.sum(xs * xs, axis=1))
        s = float(np.trace(np.diag(S) @ D) / var_s) if var_s > 0 else 1.0
    else:
        s = 1.0
    t = mu_d - s * R @ mu_s
    return s, R, t


def _random_rotation(rng):
    q = rng.normal(size=4)
    q /= np.linalg.norm(q)
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


@pytest.fixture(scope="module")
def landmarks():
    ids, X = prior_mean()
    return list(ids), np.asarray(X, float)


@pytest.fixture(scope="module")
def term_parts(landmarks):
    ids, X = landmarks
    t = SymmetryTerm.from_ids(ids)
    return ids, X, t


@pytest.fixture(scope="module")
def head():
    from face3d.model.procedural_head import build_procedural_head
    return build_procedural_head()


MX = np.array([-1.0, 1.0, 1.0])


# ----------------------------------------------------------------------------- procrustes
def test_umeyama_default_unchanged_bitwise():
    rng = np.random.default_rng(1)
    for k in range(6):
        X = rng.normal(scale=40.0, size=(30, 3))
        R = _random_rotation(rng)
        Y = apply_similarity(X, 1.3, R, rng.normal(size=3)) + rng.normal(scale=0.5, size=X.shape)
        if k % 2:
            Y = Y * MX                      # forces the det correction branch
        w = None if k < 3 else rng.uniform(0.1, 2.0, size=30)
        for ws in (True, False):
            a = umeyama(X, Y, ws, w)
            b = _legacy_umeyama(X, Y, ws, w)
            assert a[0] == b[0] and np.array_equal(a[1], b[1]) and np.array_equal(a[2], b[2])
            assert np.linalg.det(a[1]) > 0


def test_umeyama_allow_reflection_recovers_exact_reflected_similarity(landmarks):
    _, X = landmarks
    rng = np.random.default_rng(2)
    R0 = _random_rotation(rng) @ np.diag(MX)        # improper
    s0, t0 = 0.87, np.array([12.0, -4.0, 30.0])
    Y = apply_similarity(X, s0, R0, t0)
    s, R, t = umeyama(X, Y, allow_reflection=True)
    assert np.isclose(np.linalg.det(R), -1.0)
    assert np.isclose(s, s0, rtol=1e-12) and np.allclose(R, R0, atol=1e-12) and np.allclose(t, t0, atol=1e-9)
    assert np.allclose(apply_similarity(X, s, R, t), Y, atol=1e-9)
    # The default (proper) cannot reproduce it.
    sp, Rp, tp = umeyama(X, Y)
    assert np.linalg.det(Rp) > 0 and np.abs(apply_similarity(X, sp, Rp, tp) - Y).max() > 1.0
    # On proper data the unconstrained optimum is the proper rotation.
    Yp = apply_similarity(X, s0, R0 @ np.diag(MX), t0)
    s2, R2, t2 = umeyama(X, Yp, allow_reflection=True)
    assert np.isclose(np.linalg.det(R2), 1.0) and np.allclose(apply_similarity(X, s2, R2, t2), Yp, atol=1e-9)
    # Weighted, rigid, in 2-D as well.
    P2 = rng.normal(size=(12, 2))
    Q2 = P2 @ np.array([[0.0, 1.0], [1.0, 0.0]]).T + np.array([3.0, 1.0])
    s3, R3, t3 = umeyama(P2, Q2, with_scale=False, weights=rng.uniform(0.5, 1.5, 12), allow_reflection=True)
    assert np.isclose(np.linalg.det(R3), -1.0) and np.allclose(P2 @ R3.T + t3, Q2, atol=1e-12)


def test_proper_vs_reflected_detects_mirrored_source(landmarks):
    ids, X = landmarks
    rng = np.random.default_rng(3)
    # A realistic subject: the symmetric mean plus 1 mm asymmetric noise.
    subj = X + rng.normal(scale=1.0, size=X.shape)
    R, s, t = _random_rotation(rng), 1.05, np.array([5.0, 2.0, -7.0])
    mirrored = apply_similarity(subj * MX, s, R, t) + rng.normal(scale=0.5, size=X.shape)   # labels unchanged
    fits = umeyama_proper_and_reflected(X, mirrored)
    assert set(fits) == {"proper", "reflected"}
    sp, Rp, tp, rp = fits["proper"]
    sr, Rr, tr, rr = fits["reflected"]
    assert np.isclose(np.linalg.det(Rp), 1.0) and np.isclose(np.linalg.det(Rr), -1.0)
    assert rr < 0.5 * rp
    assert np.isclose(rp, math.sqrt(np.mean(np.sum((apply_similarity(X, sp, Rp, tp) - mirrored) ** 2, 1))))
    det = detect_mirrored_source(X, mirrored)
    assert det["mirrored"] and det["threshold"] == 0.5 and det["ratio"] < 0.5
    # Control: the same subject, not mirrored -> proper wins, nothing flagged.
    clean = apply_similarity(subj, s, R, t) + rng.normal(scale=0.5, size=X.shape)
    fits_c = umeyama_proper_and_reflected(X, clean)
    assert fits_c["proper"][3] < fits_c["reflected"][3]
    assert not detect_mirrored_source(X, clean)["mirrored"]
    # Weighted RMSE definition.
    w = rng.uniform(0.2, 1.0, len(X))
    s_, R_, t_, r_ = umeyama_proper_and_reflected(X, clean, weights=w)["proper"]
    res2 = np.sum((apply_similarity(X, s_, R_, t_) - clean) ** 2, 1)
    assert np.isclose(r_, math.sqrt(w @ res2 / w.sum()))


def test_reflect_basics():
    rng = np.random.default_rng(4)
    P = rng.normal(scale=50.0, size=(20, 3))
    assert np.array_equal(reflect(P), P * MX)                       # exact for the sagittal plane
    n = np.array([0.9, 0.3, -0.2])
    n_u = n / np.linalg.norm(n)
    Q = reflect(P, n, 7.0)
    assert np.allclose(reflect(Q, n, 7.0), P, atol=1e-12)            # involution
    assert np.allclose(Q - P, np.outer(P @ n_u - 7.0 / np.linalg.norm(n), -2 * n_u), atol=1e-12)
    on_plane = P - np.outer(P @ n_u - 2.0, n_u)
    assert np.allclose(reflect(on_plane, n_u, 2.0), on_plane, atol=1e-12)
    H = reflection_matrix(n)
    assert np.allclose(H @ H, np.eye(3)) and np.isclose(np.linalg.det(H), -1.0)
    assert reflect(np.array([1.0, 2.0, 3.0])).shape == (3,)
    with pytest.raises(ValueError):
        reflect(P, (0.0, 0.0, 0.0), 0.0)


def test_permute_pairs_validation():
    assert permute_pairs(5, [[0, 3]]).tolist() == [3, 1, 2, 0, 4]
    for bad in ([[0, 0]], [[0, 5]], [[0, 1], [1, 2]]):
        with pytest.raises(ValueError):
            permute_pairs(5, bad)


def _tilted_configuration(X, rng, tilt_deg=3.0, offset_mm=4.0, noise_mm=0.1):
    axis = np.array([0.0, 0.6, 0.8])                                 # perpendicular to +x
    R = rodrigues(axis * math.radians(tilt_deg)) @ rodrigues(np.array([math.radians(10.0), 0.0, 0.0]))
    n_true = R @ np.array([1.0, 0.0, 0.0])
    u = rng.normal(scale=5.0, size=3)
    u -= (u @ n_true) * n_true                                        # in-plane shift
    t = offset_mm * n_true + u
    Y = X @ R.T + t + rng.normal(scale=noise_mm, size=X.shape)
    return Y, n_true, float(n_true @ t)


def test_symmetry_plane_recovers_tilted_plane(term_parts):
    ids, X, term = term_parts
    for seed in range(5):
        rng = np.random.default_rng(100 + seed)
        Y, n_true, d_true = _tilted_configuration(X, rng)
        assert math.isclose(math.degrees(math.acos(n_true[0])), 3.0, rel_tol=1e-9) and math.isclose(d_true, 4.0)
        n, d, rmse = fit_symmetry_plane(Y, term.pairs, term.midline, term.plane_weights)
        assert np.isclose(np.linalg.norm(n), 1.0) and n[0] > 0
        ang = math.degrees(math.acos(min(1.0, float(n @ n_true))))
        assert ang < 0.3, ang
        assert abs(d - d_true) < 0.2, (d, d_true)
        assert rmse < 0.5                                             # ~ sqrt(2*3)*0.1 mm of noise
        # Unweighted and robust variants also recover it.
        n2, d2, _ = fit_symmetry_plane(Y, term.pairs, term.midline)
        assert math.degrees(math.acos(min(1.0, float(n2 @ n_true)))) < 0.3 and abs(d2 - d_true) < 0.2
        n3, d3, _ = fit_symmetry_plane(Y, term.pairs, term.midline, term.plane_weights, huber_mm=1.0)
        assert math.degrees(math.acos(min(1.0, float(n3 @ n_true)))) < 0.3 and abs(d3 - d_true) < 0.2


def test_symmetry_plane_exact_and_fallback(term_parts):
    ids, X, term = term_parts
    n, d, rmse = fit_symmetry_plane(X, term.pairs, term.midline, term.plane_weights)
    assert np.allclose(n, [1.0, 0.0, 0.0], atol=1e-12) and abs(d) < 1e-9 and rmse < 1e-9
    # Fewer than 3 pairs -> head-frame plane.
    Y = X + np.array([10.0, 0.0, 0.0])
    n2, d2, rmse2 = fit_symmetry_plane(Y, term.pairs[:2], term.midline, term.plane_weights)
    assert np.array_equal(n2, [1.0, 0.0, 0.0]) and d2 == 0.0 and rmse2 > 1.0
    # A sign-flipped input normal convention: n_x > 0 always.
    n3, d3, _ = fit_symmetry_plane(-X, term.pairs, term.midline)
    assert n3[0] > 0 and abs(d3) < 1e-9
    with pytest.raises(ValueError):
        fit_symmetry_plane(X, term.pairs, np.r_[term.midline, term.pairs[0, 0]])


# ----------------------------------------------------------------------------- sigmas and weights
def test_pair_and_midline_sigmas():
    s = pair_sigmas([("en_L", "en_R"), ("go_L", "go_R"), ("brow_inner_L", "brow_inner_R"),
                     ("endocanthion_L", "endocanthion_R"), ("t_L", "t_R")])
    assert s.shape == (5, 3)
    assert np.allclose(s[0], 0.85) and np.allclose(s[1], 2.75) and np.allclose(s[2], [1.5, 2.0, 1.5])
    assert np.allclose(s[3], 0.85) and np.allclose(s[4], 3.5)
    assert np.allclose(pair_sigmas([("forehead_side_L", "forehead_side_R")], fallback_mm=2.0), 2.0)
    with pytest.raises(KeyError):
        pair_sigmas([("forehead_side_L", "forehead_side_R")])
    with pytest.raises(ValueError):
        pair_sigmas([("en_L", "ex_R")])
    m = midline_sigmas(["n", "g", "prn", "sn", "pg", "me", "sto"])
    assert np.allclose(m, [0.9, 0.9, 1.75, 1.75, 2.5, 2.5, 2.0])
    with pytest.raises(ValueError):
        midline_sigmas(["en_L"])
    assert np.allclose(midline_sigmas(["vertex_front"], fallback_mm=1.5), 1.5)


def test_gate_symmetry_sigmas():
    base = pair_sigmas([("en_L", "en_R"), ("ch_L", "ch_R"), ("al_L", "al_R"), ("go_L", "go_R")])
    g = gate_symmetry_sigmas(base, ["measured", "prior-driven", "constrained", "unobserved"])
    assert np.allclose(g[0], 2 * base[0]) and np.allclose(g[2], 2 * base[2])        # measured -> 2x sigma
    assert np.array_equal(g[1], base[1]) and np.array_equal(g[3], base[3])          # prior-driven -> 1x
    assert np.allclose(gate_symmetry_sigmas(base, ["measured"] * 4, assist_factor=1.0), base)
    assert np.allclose(gate_symmetry_sigmas(np.array([0.9, 2.5]), ["constrained", "prior_driven"]), [1.8, 2.5])
    with pytest.raises(ValueError):
        gate_symmetry_sigmas(base, ["measured"] * 3)
    with pytest.raises(ValueError):
        gate_symmetry_sigmas(base, ["measured", "bogus", "measured", "measured"])
    with pytest.raises(ValueError):
        gate_symmetry_sigmas(base, ["measured"] * 4, assist_factor=0.0)
    # Weight x assist_factor == information x 0.25 at the default.
    assert SYM.assist_factor.value == 0.25
    assert np.allclose((base[0] / g[0]) ** 2, 0.25)


def test_plane_weights():
    w = plane_weights(["en_L", "n", "g", "ps_R", "tr", "prn", "sn", "al_L", "ac_R", "or_L", "zy_R",
                       "ls", "ch_L", "pg", "me", "go_R", "t_L", "sa_R", "sba_L", "brow_outer_L"])
    assert np.allclose(w, [1.0, 1.0, 1.0, 1.0, 1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5,
                           0.25, 0.25, 0.25, 0.25, 0.25, 0.1, 0.1, 0.1, 1.0])
    assert plane_group("n") == "upper" and plane_group("or_L") == "midface" and plane_group("v") == "cranium"
    with pytest.raises(KeyError):
        plane_weights(["vertex_front"])
    assert np.allclose(plane_weights(["vertex_front"], default=0.0), 0.0)
    # Overrides through a resolved config.
    cfg = config.resolve({"symmetry": {"plane_weight_ears": 0.0}})
    assert plane_weights(["t_L"], cfg=cfg)[0] == 0.0


def test_symmetry_defaults_registered_with_badges():
    for key in ("assist_factor", "plane_weight_upper", "plane_weight_midface", "plane_weight_lower",
                "plane_weight_ears", "too_symmetric_rmsd_mm", "too_asymmetric_rmsd_mm",
                "single_view_asym_multiplier", "min_views_30deg", "mirrored_source_ratio"):
        d = config.get("symmetry." + key)
        assert d.badge in config.BADGES and d.source
    assert config.get("symmetry.too_symmetric_rmsd_mm").value == 0.3
    assert config.get("symmetry.too_asymmetric_rmsd_mm").value == 1.5


# ----------------------------------------------------------------------------- the term
def test_symmetry_term_from_ids_structure(term_parts):
    ids, X, term = term_parts
    assert term.n_params() == 0 and term.is_prior is True and term.name == "symmetry"
    assert term.init_params(None).shape == (0,)
    assert len(term.pairs) == 15 and len(term.midline) == 14
    for (l, r), (a, b) in zip(term.pairs, term.pair_ids):
        assert ids[l] == a and ids[r] == b and ANATOMICAL[a].mirror_id == b and a.endswith("_L")
    # The symmetric mean has zero residual on the head-frame plane.
    r = term.residuals(X)
    assert r.shape == (term.n_residuals(),) == (3 * 15 + 14,) and np.abs(r).max() < 1e-12
    # Evidence gating through region states.
    gated = SymmetryTerm.from_ids(ids, region_status={"eyes": "measured", "ears": "unobserved"})
    k_en = [k for k, (a, _) in enumerate(gated.pair_ids) if a == "en_L"][0]
    k_t = [k for k, (a, _) in enumerate(gated.pair_ids) if a == "t_L"][0]
    assert np.allclose(gated.pair_sigma[k_en], 2 * 0.85) and np.allclose(gated.pair_sigma[k_t], 3.5)
    # A subset of ids (missing mirrors are simply not paired).
    sub = SymmetryTerm.from_ids(["en_L", "en_R", "ex_L", "n", "brow_inner_L", "brow_inner_R"])
    assert sub.pairs.tolist() == [[0, 1], [4, 5]] and sub.midline.tolist() == [3]
    assert np.allclose(sub.pair_sigma[1], [1.5, 2.0, 1.5]) and sub.plane_weights[2] == 0.0


def test_symmetry_term_jacobian_numeric(term_parts):
    ids, X, _ = term_parts
    rng = np.random.default_rng(7)
    status = [("measured", "constrained", "prior-driven", "unobserved")[k % 4] for k in range(15)]
    term = SymmetryTerm.from_ids(ids, pair_status=status, n=(0.98, 0.15, -0.1), d=2.5)
    Xp = X + rng.normal(scale=2.0, size=X.shape)

    class State:                                   # solver-state duck type
        def __init__(self, X):
            self.X = X

    J = term.jacobian(State(Xp), np.zeros(0))
    assert set(J) == {"X"} and J["X"].shape == (term.n_residuals(), 3 * len(X))
    Jn = np.zeros_like(J["X"])
    h = 1e-6
    x0 = Xp.ravel()
    for j in range(len(x0)):
        xp, xm = x0.copy(), x0.copy()
        xp[j] += h
        xm[j] -= h
        Jn[:, j] = (term.residuals(State(xp.reshape(-1, 3))) - term.residuals(State(xm.reshape(-1, 3)))) / (2 * h)
    assert np.allclose(J["X"], Jn, atol=1e-7, rtol=1e-6)
    # Residuals are linear in X for a fixed plane: r(X) = J vec(X) + r(0).
    r0 = term.residuals(np.zeros_like(Xp))
    assert np.allclose(term.residuals(Xp), J["X"] @ x0 + r0, atol=1e-9)
    assert np.isclose(term.cost(Xp), 0.5 * float(term.residuals(Xp) @ term.residuals(Xp)))


def test_symmetry_term_update_plane(term_parts):
    ids, X, _ = term_parts
    term = SymmetryTerm.from_ids(ids)
    rng = np.random.default_rng(11)
    Y, n_true, d_true = _tilted_configuration(X, rng, noise_mm=0.0)
    before = term.cost(Y)
    n, d, rmse = term.update_plane(Y)
    assert np.allclose(n, n_true, atol=1e-9) and abs(d - d_true) < 1e-8 and rmse < 1e-8
    assert np.allclose(term.n, n_true, atol=1e-9) and term.plane_rmse_mm == rmse
    assert term.cost(Y) < 1e-12 < before
    # The plane is fixed between updates: the Jacobian does not depend on X.
    assert np.array_equal(term.jacobian(Y)["X"], term.jacobian(Y + 1.0)["X"])
    # pair_differences is 2x the asymmetric part.
    A = np.zeros_like(Y)
    A[term.pairs[:, 0]] = [0.4, 0.0, 0.0]
    Z = Y + A
    assert np.allclose(term.pair_differences(Z), A[term.pairs[:, 0]], atol=1e-9)


# ----------------------------------------------------------------------------- zeta (WBS FU-02)
class _ZState:
    """Solver-state duck type with the bundle's global log-scale (None = disabled)."""

    def __init__(self, X, zeta=None):
        self.X = X
        self.zeta = zeta


def _fd(f, x0, h):
    """Central differences with one Richardson step (O(h^4)); exact for the linear X block."""
    def central(hh):
        cols = []
        for j in range(len(x0)):
            e = np.zeros(len(x0))
            e[j] = hh
            cols.append((f(x0 + e) - f(x0 - e)) / (2 * hh))
        return np.stack(cols, axis=1)
    return (4.0 * central(h / 2) - central(h)) / 3.0


def _strict_close(Ja, Jn, rtol=1e-8):
    """Per-block strict comparison: |Ja - Jn| <= rtol (|Jn| + max |Jn| over the row's block)."""
    Ja, Jn = np.atleast_2d(Ja.T).T, np.atleast_2d(Jn.T).T
    return bool(np.all(np.abs(Ja - Jn) <= rtol * (np.abs(Jn) + np.abs(Jn).max(axis=1, keepdims=True)) + 1e-12))


def test_symmetry_term_zeta_blocks_strict_fd(term_parts):
    """zeta enabled: rows and plane offset act on X~ = exp(-zeta) X; exact 'X' and 'zeta' blocks.

    zeta = 0.2 (a missing e^-zeta factor is an 18 % error) and a tilted plane with d = 2.5,
    so that d r / d zeta = -(r - r(0)) differs from -r."""
    ids, X, _ = term_parts
    rng = np.random.default_rng(21)
    status = [("measured", "constrained", "prior-driven", "unobserved")[k % 4] for k in range(15)]
    term = SymmetryTerm.from_ids(ids, pair_status=status, n=(0.98, 0.15, -0.1), d=2.5)
    zeta = 0.2
    s = math.exp(-zeta)
    Xp = X + rng.normal(scale=2.0, size=X.shape)
    st = _ZState(Xp, zeta)
    r = term.residuals(st)
    J = term.jacobian(st, np.zeros(0))
    m, N = term.n_residuals(), len(X)
    assert set(J) == {"X", "zeta"} and J["X"].shape == (m, 3 * N) and J["zeta"].shape == (m,)
    # values: the legacy rows evaluated on the scale-free points (plane offset in that frame)
    assert np.allclose(r, term.residuals(s * Xp), rtol=1e-14, atol=1e-14)
    assert np.allclose(term.pair_differences(st), term.pair_differences(s * Xp), rtol=1e-14, atol=1e-14)
    assert np.isclose(term.cost(st), 0.5 * float(r @ r), rtol=1e-14)
    # closed forms: d/dX = e^-zeta J0, d/dzeta = -J0 vec(X~) = -(r - r(0))
    J0 = term.jacobian(Xp)["X"]
    r0 = term.residuals(np.zeros_like(Xp))
    assert np.allclose(J["X"], s * J0, rtol=1e-14, atol=0.0)
    assert np.allclose(J["zeta"], -(r - r0), rtol=1e-12, atol=1e-12)
    assert np.abs(J["zeta"] + r).max() > 0.1                      # not -r: the offset d does not scale
    # strict per-block finite differences
    Jx_n = _fd(lambda x: term.residuals(_ZState(x.reshape(-1, 3), zeta)), Xp.ravel(), 1e-2)
    Jz_n = _fd(lambda z: term.residuals(_ZState(Xp, float(z[0]))), np.array([zeta]), 1e-2)[:, 0]
    assert _strict_close(J["X"], Jx_n)
    assert _strict_close(J["zeta"], Jz_n)
    # the comparison is sharp: a dropped e^-zeta, a flipped sign or -r instead of -(r - r(0)) fails
    assert not _strict_close(J0, Jx_n)
    assert not _strict_close(J["X"] * (1.0 + 1e-5), Jx_n)
    assert not _strict_close(-J["zeta"], Jz_n)
    assert not _strict_close(J["zeta"] / s, Jz_n)
    assert not _strict_close(-r, Jz_n)
    # shape, not size: scaling the head and moving zeta with it leaves the rows unchanged
    for dz in (-0.3, 0.1, 0.5):
        assert np.allclose(term.residuals(_ZState(math.exp(dz) * Xp, zeta + dz)), r, rtol=1e-12, atol=1e-12)
    assert not np.allclose(term.residuals(math.exp(0.1) * Xp), term.residuals(Xp), atol=1e-3)   # mm rows do change
    with pytest.raises(ValueError):
        term.residuals(_ZState(Xp, float("nan")))


def test_symmetry_term_without_zeta_is_legacy_bitwise(term_parts):
    """zeta disabled (None, absent, or a bare array): the WP-12 rows on X in mm, bit for bit."""
    ids, X, _ = term_parts
    rng = np.random.default_rng(22)
    term = SymmetryTerm.from_ids(ids, n=(0.98, 0.15, -0.1), d=2.5)
    Xp = X + rng.normal(scale=2.0, size=X.shape)

    class Bare:
        def __init__(self, X):
            self.X = X

    # the WP-12 expressions verbatim
    r_pair = ((Xp[term.pairs[:, 0]] - reflect(Xp[term.pairs[:, 1]], term.n, term.d)) / term.pair_sigma).ravel()
    r_mid = (Xp[term.midline] @ term.n - term.d) / term.midline_sigma
    legacy = np.concatenate([r_pair, r_mid])
    J_ref = term.jacobian(Xp)["X"]
    for st in (Xp, Bare(Xp), _ZState(Xp, None)):
        assert np.array_equal(term.residuals(st), legacy)
        J = term.jacobian(st)
        assert set(J) == {"X"} and np.array_equal(J["X"], J_ref)
    # zeta = 0.0 is "enabled": same numbers, plus the zeta block
    J = term.jacobian(_ZState(Xp, 0.0))
    assert set(J) == {"X", "zeta"} and np.allclose(J["X"], J_ref, rtol=1e-15, atol=0.0)
    assert np.allclose(term.residuals(_ZState(Xp, 0.0)), legacy, rtol=1e-15, atol=1e-15)


def test_symmetry_term_update_plane_follows_zeta(term_parts):
    """update_plane on a state with zeta fits the plane of exp(-zeta) X, the points the rows use."""
    ids, X, _ = term_parts
    rng = np.random.default_rng(23)
    Y, n_true, d_true = _tilted_configuration(X, rng, noise_mm=0.0)
    zeta = 0.15
    big = math.exp(zeta) * Y                                     # the same shape, 16 % larger, in mm
    term = SymmetryTerm.from_ids(ids)
    n, d, rmse = term.update_plane(_ZState(big, zeta))
    assert np.allclose(n, n_true, atol=1e-9) and abs(d - d_true) < 1e-8 and rmse < 1e-8
    assert term.cost(_ZState(big, zeta)) < 1e-12
    assert term.cost(big) > 1e-3                                 # on mm the offset no longer matches
    n2, d2, _ = SymmetryTerm.from_ids(ids).update_plane(big)     # arrays: mm, as before
    assert np.allclose(n2, n_true, atol=1e-9) and abs(d2 - math.exp(zeta) * d_true) < 1e-7


def _bundle_scene(seed):
    from face3d.model.landmark_prior import FactorPrior
    from face3d.solve.bundle import ViewObs
    from face3d.synthetic import orbit_camera
    from face3d.testbed import rigs, subjects
    prior = FactorPrior.from_package()
    mu, ids = prior.mean(), list(prior.ids)
    rng = np.random.default_rng(seed)
    _, X, _ = subjects.smooth_field_subject(rng, names=ids, template=mu)
    views = []
    for yaw in (-40.0, 0.0, 40.0):
        cam = orbit_camera(700.0 * rng.uniform(0.95, 1.05), yaw, rng.uniform(-5.0, 5.0), 26.0, target=(0.0, 0.0, 60.0))
        uv = cam.project(X) + rng.normal(scale=1.0, size=(len(ids), 2))
        uv[~rigs.visible_mask(cam, X)] = np.nan
        # no metric cue: unknown focal (sigma 0.6, DESIGN 4.2 'Nothing' row), no scale reference
        views.append(ViewObs(uv, cam.copy(), f_prior=cam.f, f_prior_log_sigma=0.6, focal_group="g",
                             kinds=["generic"] * len(ids)))
    return prior, mu, ids, views


def test_symmetry_term_in_bundle_with_zeta(monkeypatch):
    """In bundle_adjust with zeta enabled: the term's rows reach the zeta column exactly (strict
    FD through the solver's closures) and do not pull the global scale.

    Measured (seeds 0-3, no metric cue, zeta prior N(0, 0.045^2)): zeta_hat = 0.0000 without
    the term and with it; the pre-FU-02 rows on X in mm give -0.0019 .. -0.0025 (heads 0.2 %
    small; the pull grows as the shape prior weakens, ~8 % in WP-15's iris-only scene with
    the bundle's own rows, WBS FU-01)."""
    import face3d.solve.bundle as B
    from face3d.solve.bundle import ScaleConfig, bundle_adjust

    class OnMm(SymmetryTerm):                                    # the defect: rows on state.X in mm
        def residuals(self, state, p=None):
            return super().residuals(np.asarray(state.X), p)

        def jacobian(self, state, p=None):
            return super().jacobian(np.asarray(state.X), p)

    for seed in range(2):
        prior, mu, ids, views = _bundle_scene(seed)
        base = bundle_adjust(views, mu.copy(), None, prior=prior)
        fixed = bundle_adjust(views, mu.copy(), None, prior=prior, terms=[SymmetryTerm.from_ids(ids)])
        on_mm = bundle_adjust(views, mu.copy(), None, prior=prior, terms=[OnMm.from_ids(ids)])
        assert fixed.zeta is not None and "term:symmetry" in fixed.param_index
        assert abs(fixed.zeta - base.zeta) < 2e-4, (fixed.zeta, base.zeta)
        assert on_mm.zeta - base.zeta < -1e-3, (on_mm.zeta, base.zeta)

    # strict per-block FD of the term rows through the solver's residual / jacobian / retract
    prior, mu, ids, views = _bundle_scene(5)
    term = SymmetryTerm.from_ids(ids, n=(0.98, 0.15, -0.1), d=2.5)
    captured = {}
    orig = B.levenberg_marquardt

    def shim(fun, x0, jac=None, retract=None, **kw):
        captured.setdefault("c", (fun, jac, retract, np.array(x0, float)))
        return orig(fun, x0, jac=jac, retract=retract, max_iter=0)
    monkeypatch.setattr(B, "levenberg_marquardt", shim)
    rng = np.random.default_rng(5)
    X0 = mu + rng.normal(scale=2.0, size=mu.shape)
    res = bundle_adjust(views, X0, None, prior=prior, terms=[term], scale=ScaleConfig(init=0.2))
    fun, jac, retract, x0 = captured["c"]
    idx = res.param_index
    z, pts = idx["zeta"].start, idx["points"]
    assert np.isclose(x0[z], 0.2)
    Xs = math.exp(-0.2) * x0[pts].reshape(-1, 3)
    expect = term.residuals(Xs)
    r = fun(x0)
    m = term.n_residuals()
    hits = [o for o in range(len(r) - m + 1) if np.allclose(r[o:o + m], expect, rtol=1e-12, atol=1e-12)]
    assert len(hits) == 1, hits
    rows = np.arange(hits[0], hits[0] + m)
    Ja = jac(x0)[rows]

    def central(hh):
        Jn = np.zeros((m, len(x0)))
        for j in range(len(x0)):
            e = np.zeros(len(x0))
            e[j] = hh
            Jn[:, j] = (fun(retract(x0, e))[rows] - fun(retract(x0, -e))[rows]) / (2 * hh)
        return Jn
    Jn = (4.0 * central(5e-4) - central(1e-3)) / 3.0
    blocks = {k: sl for k, sl in idx.items() if k != "cameras" and sl.stop > sl.start}   # term has 0 own params
    assert {"zeta", "points"} <= set(blocks)
    for name, sl in blocks.items():
        assert _strict_close(Ja[:, sl], Jn[:, sl], rtol=1e-7), name
    other = np.ones(len(x0), bool)
    other[pts] = False
    other[z] = False
    assert not np.any(Ja[:, other]) and np.abs(Ja[:, z]).max() > 0.1
    # legacy path: zeta disabled -> no 'zeta' block is returned (the bundle would reject one)
    from face3d.solve.bundle import Priors
    leg = bundle_adjust(views, mu.copy(), Priors(mean=mu, sigma=8.0), terms=[SymmetryTerm.from_ids(ids)])
    assert leg.zeta is None and np.all(np.isfinite(leg.X))


# ----------------------------------------------------------------------------- S / Asym
def test_split_symmetric_exact(head):
    V0, m = head.vertices, head.mirror_map
    rng = np.random.default_rng(5)
    V = V0 + rng.normal(scale=1.5, size=V0.shape)                    # random asymmetric field
    S, A = split_symmetric(V, m)
    assert np.abs(S[m] * MX - S).max() < 1e-9                        # S symmetric (bit-exact here)
    assert np.array_equal(S[m] * MX, S)
    assert np.allclose(S + A, V, rtol=0.0, atol=1e-12)
    assert np.abs(A[m] * MX + A).max() < 1e-9                        # Asym antisymmetric
    assert np.allclose(S[head.midline, 0], 0.0, atol=1e-12)
    # Inputs untouched; symmetric input -> zero Asym.
    S0, A0 = split_symmetric(V0, m)
    assert np.array_equal(S0, V0) and not A0.any()
    # Tilted plane.
    n, d = np.array([0.99, 0.1, -0.05]), 3.0
    S2, A2 = split_symmetric(V, m, n, d)
    assert np.abs(reflect(S2[m], n, d) - S2).max() < 1e-9
    assert np.allclose(S2 + A2, V, rtol=0.0, atol=1e-12)
    with pytest.raises(ValueError):
        split_symmetric(V, np.roll(m, 1))
    with pytest.raises(ValueError):
        check_mirror_map(m[:-1], len(V))


def _antisymmetric_field(head, rng, rms_mm):
    """Smooth field A with A = -M A[m] (pure asymmetry), scaled to a given mirror RMSD on the face."""
    V0, m = head.vertices, head.mirror_map
    c = rng.normal(scale=40.0, size=(6, 3)) + np.array([0.0, 0.0, 60.0])
    a = rng.normal(size=(6, 3))
    F = sum(a[k] * np.exp(-np.sum((V0 - c[k]) ** 2, 1) / (2 * 30.0 ** 2))[:, None] for k in range(6))
    A = 0.5 * (F - F[m] * MX)
    mask = face_vertex_mask(head.regions, len(V0))
    cur = math.sqrt(np.mean(np.sum((2 * A[mask]) ** 2, 1)))           # mirror RMSD of V0 + A
    return A * (rms_mm / cur)


def test_mirror_rmsd(head):
    V0, m = head.vertices, head.mirror_map
    assert mirror_rmsd(V0, m, face_vertex_mask(head.regions, len(V0))) == 0.0
    rng = np.random.default_rng(6)
    A = _antisymmetric_field(head, rng, 0.8)
    mask = face_vertex_mask(head.regions, len(V0))
    assert np.isclose(mirror_rmsd(V0 + A, m, mask), 0.8)
    assert np.isclose(mirror_rmsd(V0 + A, m, np.flatnonzero(mask)), 0.8)
    _, Asym = split_symmetric(V0 + A, m)
    assert np.isclose(mirror_rmsd(V0 + A, m, mask), 2 * math.sqrt(np.mean(np.sum(Asym[mask] ** 2, 1))))
    assert set(FACE_REGIONS) <= set(head.regions)
    with pytest.raises(ValueError):
        mirror_rmsd(V0, m, np.zeros(len(V0), bool))


def test_symmetry_checks_thresholds(head):
    V0, m, regions = head.vertices, head.mirror_map, head.regions
    # Exactly symmetric head: flagged too symmetric only when the photos show asymmetry.
    f, mult = symmetry_checks(V0, m, regions, True, 2)
    assert [x["code"] for x in f] == ["S-TOO-SYMMETRIC"] and mult == 1.0
    assert abs(f[0]["value"]) < 1e-9 and f[0]["threshold"] == 0.3  # plane now registered: rounding-level RMSD and f[0]["msg_key"] == "symmetry.S-TOO-SYMMETRIC"
    assert f[0]["action"] == "ask"
    f, _ = symmetry_checks(V0, m, regions, False, 2)
    assert f == []
    rng = np.random.default_rng(8)
    # 2 mm antisymmetric field -> too asymmetric.
    A2 = _antisymmetric_field(head, rng, 2.0)
    f, _ = symmetry_checks(V0 + A2, m, regions, True, 3)
    assert [x["code"] for x in f] == ["S-TOO-ASYMMETRIC"]
    # Registration removes the part of the random field that is a rigid tilt, so <= 2.0.
    assert 1.5 < f[0]["value"] <= 2.0 + 1e-9 and f[0]["threshold"] == 1.5
    # A typical adult value (~0.8 mm, facial-asymmetry) raises nothing.
    A08 = _antisymmetric_field(head, rng, 0.8)
    assert symmetry_checks(V0 + A08, m, regions, True, 2)[0] == []
    # Fewer than 2 view pairs >= 30 deg apart: reported asymmetry sigma x4.
    assert symmetry_checks(V0 + A08, m, regions, True, 1)[1] == 4.0
    assert symmetry_checks(V0 + A08, m, regions, True, 0)[1] == 4.0
    assert symmetry_checks(V0 + A08, m, regions, True, 2)[1] == 1.0
    # Thresholds come from the badged defaults and honour overrides.
    cfg = config.resolve({"symmetry": {"too_asymmetric_rmsd_mm": 0.5}})
    assert [x["code"] for x in symmetry_checks(V0 + A08, m, regions, True, 2, cfg=cfg)[0]] == ["S-TOO-ASYMMETRIC"]
    # All vertices when no regions are given.
    assert symmetry_checks(V0, m, None, True, 2)[0][0]["code"] == "S-TOO-SYMMETRIC"
    with pytest.raises(ValueError):
        symmetry_checks(V0, m, {"scalp": head.regions["scalp"]}, True, 2)


def test_symmetry_checks_register_plane_so_pose_offset_is_not_asymmetry(head):
    """A perfectly symmetric head 1 deg off the head frame must not be flagged (WP-12 review)."""
    from face3d.geometry.rotations import rotation_from_euler_deg
    V0, mirror = head.vertices, head.mirror_map
    for R in (rotation_from_euler_deg(0, 1, 0), rotation_from_euler_deg(0, 0, 1)):
        V = V0 @ R.T + np.array([0.8, 0.0, 0.0])
        findings, _ = symmetry_checks(V, mirror, None, photos_show_asymmetry=False, n_view_pairs_30deg=2)
        assert not any(f["code"] == "S-TOO-ASYMMETRIC" for f in findings)
        # The fixed head-frame plane would have flagged it.
        f_fixed, _ = symmetry_checks(V, mirror, None, photos_show_asymmetry=False, n_view_pairs_30deg=2,
                                     n_plane=(1.0, 0.0, 0.0), d=0.0)
        assert any(f["code"] == "S-TOO-ASYMMETRIC" for f in f_fixed)
