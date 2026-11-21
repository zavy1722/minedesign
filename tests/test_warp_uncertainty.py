"""WP-19: template warp v2 (stages A-D with gates) and per-vertex uncertainty (DESIGN 4.15).

Test-bed conventions used here
------------------------------
* Kit: the procedural CC0 head (n = 24, 3458 vertices), scheme ``anatomical44``.
* "Face RMS": RMS point-to-surface distance (mm) of the fitted face-hemisphere vertices
  (``face_hemisphere``: rest z > 0) to the true surface after similarity alignment of the
  fitted face landmarks to the true ones (DESIGN 7.3 "landmark similarity alignment").
* "BA targets": ``reconstruct_landmarks`` with the packaged factor prior on a 7-view studio
  ring (``testbed.rigs.studio_ring``) observed by ``testbed.detector_sim.simulate``.
* sigma_X = sqrt(trace Cov_i) of the bundle posterior (``landmark_sigma_mm``).
"""
import numpy as np
import pytest

from face3d.fit import template as T
from face3d.fit import uncertainty as U
from face3d.geometry.procrustes import apply_similarity, umeyama
from face3d.geometry.rbf import ALPHA_GRID, WARP, RBFWarp, per_landmark_lambda, rms_radius
from face3d.geometry.rotations import rodrigues
from face3d.mesh import uv_sphere
from face3d.mesh.distance import point_to_mesh
from face3d.mesh.laplacian import _dense_weighted_gram, cotan_laplacian, laplacian_deform
from face3d.model.landmark_prior import FactorPrior
from face3d.model.procedural_head import build_procedural_head
from face3d.model.registry import ANATOMICAL
from face3d.model.template_kit import area_weighted_normals
from face3d.solve.reconstruct import PhotoLandmarks, reconstruct_landmarks
from face3d.solve.robust import RobustSchedule
from face3d.synthetic import synthetic_landmarks
from face3d.testbed import detector_sim, rigs
from face3d.testbed.surface_subjects import face_hemisphere, out_of_prior_subject

SCHEME = "anatomical44"
FACE_REGIONS = ("eyes", "nose", "lips", "chin", "cheeks", "forehead")
MEASURED_REGIONS = ("eyes", "nose", "lips", "chin", "cheeks")     # regions carrying >= 4 landmarks


# =========================================================================== fixtures / helpers
@pytest.fixture(scope="module")
def kit():
    return build_procedural_head()


@pytest.fixture(scope="module")
def bed(kit):
    ids = kit.landmark_names(SCHEME)
    prior = FactorPrior.from_package()
    assert list(prior.ids) == ids
    face = np.zeros(kit.n_verts, bool)
    face[face_hemisphere(kit)] = True
    regions = kit.vertex_regions()
    return dict(
        ids=ids, prior=prior, face=face, regions=regions, tris=kit.triangles(),
        kinds=[ANATOMICAL[i].kind for i in ids],
        sdef=np.array([ANATOMICAL[i].sigma_def_mm for i in ids]),
        face_lm=[k for k, i in enumerate(ids) if ANATOMICAL[i].region in FACE_REGIONS],
        measured=face & np.isin(regions, MEASURED_REGIONS),
    )


def _rms(d):
    return float(np.sqrt(np.mean(np.square(d))))


def _signed_distance(kit, bed, V_fit, V_true, mask):
    """Signed point-to-surface distance (mm) of V_fit[mask] to the true mesh after the landmark
    similarity alignment (module docstring)."""
    Xf = kit.landmark_positions(SCHEME, V_fit)[bed["face_lm"]]
    Xt = kit.landmark_positions(SCHEME, V_true)[bed["face_lm"]]
    s, R, t = umeyama(Xf, Xt)
    return point_to_mesh(apply_similarity(V_fit, s, R, t)[mask], V_true, bed["tris"], signed=True)[0]


def _face_rms(kit, bed, V_fit, V_true):
    return _rms(_signed_distance(kit, bed, V_fit, V_true, bed["face"]))


def _bundle(kit, bed, V_true, seed, robust=False, **detector):
    """BA targets from a 7-view studio ring: (BundleResult, views_agree (N,))."""
    r_rig, r_det = (np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(2))
    Xt = kit.landmark_positions(SCHEME, V_true)
    rig = rigs.studio_ring(r_rig, 7, X=Xt)
    obs = detector_sim.simulate(Xt, bed["kinds"], rig, r_det, **detector)
    photos = [PhotoLandmarks(uv, c.width, c.height, f_prior_px=rig.f_prior_px[k],
                             f_prior_log_sigma=rig.f_prior_log_sigma[k], focal_group=rig.focal_group[k],
                             kinds=bed["kinds"])
              for k, (uv, c) in enumerate(zip(obs.uv, rig.cameras))]
    res = reconstruct_landmarks(photos, None, prior=bed["prior"], sigma_def_mm=bed["sdef"],
                                robust=RobustSchedule() if robust else None)
    return res, np.sum(res.inlier_mask, axis=0)


def _smooth_in_space_subject(kit, seed, amp_mm=3.0, n_bumps=6):
    """Template warped by a smooth field inside the warp space: a sum of ``n_bumps`` Gaussian bumps
    (width 40-80 mm, vector amplitude N(0, amp^2) mm) sampled at the landmarks and extended to the
    surface by the exact biharmonic RBF (so noise-free landmark targets determine it exactly)."""
    rng = np.random.default_rng(seed)
    X0 = kit.landmark_positions(SCHEME)
    c = X0[rng.integers(0, len(X0), n_bumps)] + rng.normal(scale=10.0, size=(n_bumps, 3))
    w = rng.uniform(40.0, 80.0, n_bumps)
    a = rng.normal(scale=amp_mm, size=(n_bumps, 3))
    d = sum(np.exp(-np.sum((X0 - c[k]) ** 2, axis=1) / (2.0 * w[k] ** 2))[:, None] * a[k] for k in range(n_bumps))
    return RBFWarp(X0, X0 + d)(kit.vertices)


# =========================================================================== rbf.py
def test_rbf_legacy_and_normalise_equivalence():
    rng = np.random.default_rng(0)
    _, X = synthetic_landmarks()
    Y = X + rng.normal(scale=3.0, size=X.shape)
    P = rng.uniform(-80, 80, size=(50, 3))
    # scalar smoothing == constant per-landmark array (legacy path unchanged)
    a = RBFWarp(X, Y, smoothing=2.0)
    b = RBFWarp(X, Y, smoothing=np.full(len(X), 2.0))
    assert np.array_equal(a(P), b(P))
    # normalise: a dimensionless lambda equals a legacy lambda * R_bar (phi = r), so smoothing is unit-free
    R = rms_radius(X)
    lam = rng.uniform(0.0, 0.05, len(X))
    n1 = RBFWarp(X, Y, smoothing=lam, normalise=True)
    l1 = RBFWarp(X, Y, smoothing=lam * R)
    assert n1.R_bar == pytest.approx(R)
    assert np.allclose(n1(P), l1(P), atol=1e-8)
    # the same landmarks in metres give the same warp (scaled) under normalise=True
    n2 = RBFWarp(X * 1e-3, Y * 1e-3, smoothing=lam, normalise=True)
    assert np.allclose(n2(P * 1e-3) * 1e3, n1(P), atol=1e-8)
    with pytest.raises(ValueError):
        RBFWarp(X, Y, smoothing=np.ones(3))
    with pytest.raises(ValueError):
        RBFWarp(X, Y, smoothing=-1.0)
    assert np.allclose(per_landmark_lambda(np.array([1.0, 2.0]), 50.0, 10.0), 10.0 * np.array([1.0, 4.0]) / 2500.0)
    assert np.allclose(per_landmark_lambda(np.array([2.0]), 50.0), WARP["alpha"].value * 4.0 / 2500.0)
    assert WARP["alpha"].value in ALPHA_GRID


def test_per_landmark_smoothing_monotone():
    """Increasing alpha lowers the bending energy and raises the residual with per-landmark arrays."""
    rng = np.random.default_rng(1)
    _, X = synthetic_landmarks()
    Y = X + rng.normal(scale=3.0, size=X.shape)
    sigma = rng.uniform(0.5, 4.0, len(X))                 # mm, one per landmark
    R = rms_radius(X)
    energies, residuals = [], []
    for alpha in (0.0,) + ALPHA_GRID + (1e3, 1e4):
        w = RBFWarp(X, Y, smoothing=per_landmark_lambda(sigma, R, alpha), normalise=True)
        energies.append(w.bending_energy())
        residuals.append(_rms(w.residual(Y)))
    assert all(e >= -1e-9 for e in energies)
    assert residuals[0] < 1e-8
    assert all(e1 < e0 for e0, e1 in zip(energies, energies[1:]))
    assert all(r1 > r0 for r0, r1 in zip(residuals, residuals[1:]))
    # a landmark with a larger sigma is trusted less: its own residual grows when only its sigma grows
    lam = per_landmark_lambda(sigma, R, 10.0)
    lam2 = lam.copy()
    lam2[5] *= 50.0
    r1 = RBFWarp(X, Y, smoothing=lam, normalise=True).residual(Y)
    r2 = RBFWarp(X, Y, smoothing=lam2, normalise=True).residual(Y)
    assert r2[5] > r1[5]


@pytest.mark.parametrize("kind,normalise", [("biharmonic", False), ("biharmonic", True), ("triharmonic", True)])
def test_rbf_linear_map_exact(normalise, kind):
    """warp(X + delta) - warp(X) == A delta within 1e-9 (affine part included).  (r^3 in raw mm has
    kernel values ~1e6 and loses ~2 more digits to conditioning, so it is checked normalised.)"""
    rng = np.random.default_rng(2)
    _, X = synthetic_landmarks()
    Y = X + rng.normal(scale=3.0, size=X.shape)
    lam = rng.uniform(0.0, 0.02, len(X))
    P = rng.uniform(-90, 90, size=(300, 3))
    w = RBFWarp(X, Y, kind=kind, smoothing=lam, normalise=normalise)
    A = w.linear_map(P)
    assert A.shape == (len(P), len(X))
    assert np.abs(w.displacement(P) - A @ (Y - X)).max() < 1e-9
    delta = rng.normal(scale=2.0, size=X.shape)
    w2 = RBFWarp(X, Y + delta, kind=kind, smoothing=lam, normalise=normalise)
    assert np.abs((w2(P) - w(P)) - A @ delta).max() < 1e-9
    # affine reproduction: rows sum to 1 for a pure translation of the targets
    assert np.abs(A.sum(axis=1) - 1.0).max() < 1e-9


# =========================================================================== laplacian.py
def test_stiffness_reduces_motion():
    """A stiffness-3.0 region moves less than a 0.3 region under equal pull."""
    m = uv_sphere(50.0, n_lat=16, n_lon=24)
    V = m.vertices
    n = len(V)
    a, b = int(np.argmax(V[:, 0])), int(np.argmin(V[:, 0]))          # antipodal equator vertices
    stiff = np.ones(n)
    stiff[np.linalg.norm(V - V[a], axis=1) < 30.0] = 3.0
    stiff[np.linalg.norm(V - V[b], axis=1) < 30.0] = 0.3
    anchors = np.flatnonzero(np.abs(V[:, 0]) < 1.0)                   # the x = 0 great circle stays put
    pull = np.array([[8.0, 0.0, 0.0], [-8.0, 0.0, 0.0]])              # equal outward pulls
    idx = np.r_[anchors, a, b]
    tg = np.vstack([V[anchors], V[[a, b]] + pull])
    wts = np.r_[np.full(len(anchors), 1e3), 0.02, 0.02]               # soft, equal pulls
    Vs, it = laplacian_deform(m, idx, tg, weight=wts, stiffness=stiff, solver="dense")
    move_stiff, move_soft = np.linalg.norm(Vs[a] - V[a]), np.linalg.norm(Vs[b] - V[b])
    assert it == 0
    assert 0.0 < move_stiff < 0.6 * move_soft
    # without stiffness the two sides move equally (the mesh and the pulls are mirror images)
    V1, _ = laplacian_deform(m, idx, tg, weight=wts, solver="dense")
    assert np.linalg.norm(V1[a] - V[a]) == pytest.approx(np.linalg.norm(V1[b] - V[b]), rel=1e-6)
    assert move_stiff < np.linalg.norm(V1[a] - V[a]) < move_soft
    # stiffness = ones is the legacy operator; the dense and CG solvers agree
    V2, _ = laplacian_deform(m, idx, tg, weight=wts, stiffness=np.ones(n), solver="dense")
    assert np.allclose(V1, V2, atol=1e-10)
    Vc, itc = laplacian_deform(m, idx, tg, weight=wts, stiffness=stiff, tol=1e-12, max_iter=20000)
    assert itc > 0 and np.abs(Vc - Vs).max() < 1e-5
    Va, _ = laplacian_deform(m, idx, tg, weight=wts, stiffness=stiff, solver="auto")
    assert np.array_equal(Va, Vs)
    with pytest.raises(ValueError):
        laplacian_deform(m, idx, tg, weight=wts, stiffness=np.zeros(n))
    with pytest.raises(ValueError):
        laplacian_deform(m, idx, tg, weight=wts, solver="nope")
    L, mass = cotan_laplacian(V, m.triangles())
    Ld = L.toarray()
    wv = np.random.default_rng(0).uniform(0.5, 2.0, n)
    assert np.allclose(_dense_weighted_gram(L, wv), Ld.T @ (wv[:, None] * Ld), atol=1e-9)


# =========================================================================== template.py stages
def test_stage_a_flags_mirrored_and_wrong_axes(kit, bed):
    ids = bed["ids"]
    X0 = kit.landmark_positions(SCHEME)
    Rm = rodrigues(np.array([0.1, -0.4, 0.2]))
    X = 1.05 * X0 @ Rm.T + np.array([10.0, -20.0, 300.0])
    V_A, (s, R, t), flags = T.stage_a(kit, X, ids)
    assert flags == []
    assert s == pytest.approx(1.05) and np.allclose(R, Rm, atol=1e-9)
    assert np.allclose(V_A, 1.05 * kit.vertices @ Rm.T + t, atol=1e-8)
    # mirrored source (x -> -x with the labels kept): flagged, never flipped
    Xm = X0 * np.array([-1.0, 1.0, 1.0])
    V_m, (sm, Rmm, tm), flags_m = T.stage_a(kit, Xm, ids)
    assert T.FLAG_MIRRORED in flags_m
    assert np.linalg.det(Rmm) == pytest.approx(1.0)
    # wrong axes / units: targets in centimetres, and targets with y and z scaled apart
    assert T.FLAG_WRONG_AXES in T.stage_a(kit, X0 * 0.1, ids)[2]
    assert T.FLAG_WRONG_AXES in T.stage_a(kit, X0 * np.array([1.0, 2.0, 0.5]), ids)[2]
    assert T.FLAG_MIRRORED not in T.stage_a(kit, X0 * 0.1, ids)[2]
    # a normal subject raises neither flag; NaN targets are ignored
    Vt = out_of_prior_subject(kit, np.random.default_rng(3)).V_true
    Xs = kit.landmark_positions(SCHEME, Vt)
    Xs[ids.index("op")] = np.nan
    assert T.stage_a(kit, Xs, ids)[2] == []
    with pytest.raises(ValueError):
        T.stage_a(kit, X[:5], ids)


def test_stage_b_linear_map_and_missing_targets(kit, bed):
    ids = bed["ids"]
    rng = np.random.default_rng(4)
    X = kit.landmark_positions(SCHEME) + rng.normal(scale=1.5, size=(len(ids), 3))
    X[ids.index("v")] = np.nan
    sig = rng.uniform(0.5, 3.0, len(ids))
    V_A, _, _ = T.stage_a(kit, X, ids)
    V_B, A = T.stage_b(V_A, kit, X, sig, ids)
    assert A.shape == (kit.n_verts, len(ids)) and np.all(A[:, ids.index("v")] == 0.0)
    ok = np.isfinite(X[:, 0])
    X_A = kit.landmark_positions(SCHEME, V_A)
    assert np.abs(V_B - (V_A + A[:, ok] @ (X[ok] - X_A[ok]))).max() < 1e-9
    # exact interpolation without sigma; smoothing leaves a residual
    V_e, _ = T.stage_b(V_A, kit, X, None, ids)
    assert T.landmark_rms(kit, V_e, X, ids) < 1e-8
    assert T.landmark_rms(kit, V_B, X, ids) > 1e-3


def test_offset_cap_unless_views_agree(kit, bed):
    ids = bed["ids"]
    N = len(ids)
    V_B = kit.vertices
    i = ids.index("prn")
    X = kit.landmark_positions(SCHEME)
    X[i] += np.array([0.0, 0.0, 10.0])                    # a 10 mm stage-C offset at the nose tip
    cfg = T.StagedWarpConfig()
    assert cfg.offset_cap_mm == 4.0 and cfg.agree_views == 2

    def run(views_agree):
        info = {}
        V = T.stage_c(V_B, kit, X, views_agree, ids=ids, info=info)
        off = np.linalg.norm(V - V_B, axis=1)
        return V, off, np.linalg.norm(kit.landmark_positions(SCHEME, V)[i] - X[i]), info

    # one view only: every vertex near the single-view landmark stays within 4 mm
    one = np.full(N, 3)
    one[i] = 1
    V1, off1, miss1, info1 = run(one)
    near = np.argmin(np.linalg.norm(V_B[:, None] - kit.landmark_positions(SCHEME)[None], axis=2), axis=1)
    assert info1["n_capped"] > 0
    assert off1[near == i].max() <= 4.0 + 1e-9
    assert off1[near == i].max() > 3.9 and miss1 == pytest.approx(6.0, abs=0.1)
    # two views agree: the full offset is allowed
    V2, off2, miss2, info2 = run(np.full(N, 2))
    assert info2["n_capped"] == 0 and miss2 < 0.05 and off2.max() > 9.9
    # no view information: no cap
    V3, off3, miss3, _ = run(None)
    assert np.array_equal(V3, V2)
    # the other landmarks stay where they are in both cases
    others = np.arange(N) != i
    for V in (V1, V2):
        assert np.linalg.norm(kit.landmark_positions(SCHEME, V)[others] - X[others], axis=1).max() < 0.2


def test_stage_c_soft_targets_follow_sigma(kit, bed):
    ids = bed["ids"]
    i = ids.index("pg")
    X = kit.landmark_positions(SCHEME)
    X[i] += np.array([0.0, 0.0, 3.0])
    moved = []
    for s in (0.0, 1.0, 5.0):
        sig = np.zeros(len(ids))
        sig[i] = s
        V = T.stage_c(kit.vertices, kit, X, None, ids=ids, sigma_X_mm=sig)
        moved.append(float(np.linalg.norm(kit.landmark_positions(SCHEME, V)[i] - kit.landmark_positions(SCHEME)[i])))
    assert moved[0] == pytest.approx(3.0, abs=0.02)
    assert moved[0] > moved[1] > moved[2] > 0.0
    # nothing to do when stage B already interpolates
    info = {}
    V = T.stage_c(kit.vertices, kit, kit.landmark_positions(SCHEME), None, ids=ids, info=info)
    assert np.array_equal(V, kit.vertices) and info["iterations"] == 0


def test_fold_gate_rolls_back(kit, bed):
    ids = bed["ids"]
    tris = bed["tris"]
    V0 = kit.vertices
    ok, det = T.fold_gate(V0, V0, tris)
    assert ok and det == pytest.approx(1.0)
    # a global rotation, translation and mild scale is not a fold
    Rm = rodrigues(np.array([0.3, 2.0, -0.5]))
    ok, det = T.fold_gate(V0, 0.9 * V0 @ Rm.T + 5.0, tris)
    assert ok and det == pytest.approx(0.81, abs=1e-6)
    # a uniform shrink below the threshold fails; one flipped triangle fails with a negative det
    assert not T.fold_gate(V0, 0.4 * V0, tris)[0]
    V1 = V0.copy()
    v = kit.landmark_vertices(SCHEME, ["prn"])[0]
    V1[v] -= 12.0 * kit.normals[v]
    ok, det = T.fold_gate(V0, V1, tris)
    assert not ok and det < 0.0
    # extreme target: the sublabiale target dragged 40 mm down through the chin landmarks
    X = kit.landmark_positions(SCHEME)
    X[ids.index("sl")] += np.array([0.0, -40.0, 0.0])
    res = T.staged_warp(kit, X, ids)
    assert T.FLAG_FOLD in res.flags and T.FLAG_WRONG_AXES not in res.flags
    assert res.stage == "A" and res.V_B is None and res.A_rows is None
    assert np.array_equal(res.vertices, res.V_A)
    assert res.min_det["B"] <= 0.2
    # a moderate target passes all gates and reaches stage C
    X = kit.landmark_positions(SCHEME)
    X[ids.index("prn")] += np.array([0.0, 0.0, 3.0])
    good = T.staged_warp(kit, X, ids)
    assert good.stage == "C" and good.flags == [] and min(good.min_det.values()) > 0.2
    # stage B that misses the advance threshold stays at B
    held = T.staged_warp(kit, X, ids, sigma_X_mm=np.full(len(ids), 1.0),
                         config=T.StagedWarpConfig(alpha=30.0, advance_rms_mm=1e-6))
    assert held.stage == "B" and T.FLAG_B_RMS in held.flags and held.V_C is None


def test_in_space_accuracy(kit, bed):
    """Template warped by a smooth field: noise-free landmark targets give stage C face RMS <= 0.5 mm;
    BA targets from 7 noisy views (detector noise and 5 % outliers; robust bundle) <= 1.5 mm
    (median of 5 seeds), and better than stage A."""
    ids = bed["ids"]
    exact, noisy, stage_a = [], [], []
    for seed in range(5):
        Vt = _smooth_in_space_subject(kit, seed)
        r0 = T.staged_warp(kit, kit.landmark_positions(SCHEME, Vt), ids)
        assert r0.stage == "C" and r0.flags == []
        exact.append(_face_rms(kit, bed, r0.vertices, Vt))
        res, agree = _bundle(kit, bed, Vt, 100 + seed, robust=True, definition_bias=False)
        r = T.staged_warp(kit, res.X, ids, sigma_X_mm=U.landmark_sigma_mm(res.cov), views_agree=agree)
        assert r.stage == "C" and r.flags == []
        noisy.append(_face_rms(kit, bed, r.vertices, Vt))
        stage_a.append(_face_rms(kit, bed, r.V_A, Vt))
    assert max(exact) <= 0.5 and np.median(exact) < 1e-3          # in the warp space: essentially exact
    assert np.median(noisy) <= 1.5
    assert np.median(noisy) < 0.85 * np.median(stage_a)


def test_out_of_space_stage_c_improves(kit, bed):
    """Out-of-prior subjects (WP-11 generator), true landmark targets, 10 seeds: the stage-C face RMS
    is at least 30 % lower than stage A in the median and over the pooled seeds, and lower for every
    subject.  (Per subject the reduction ranges 22-62 %: a subject whose bumps sit on the forehead,
    where only g and tr constrain the surface, gains least.)"""
    ids = bed["ids"]
    a, c = [], []
    for seed in range(10):
        Vt = out_of_prior_subject(kit, np.random.default_rng(seed)).V_true
        r = T.staged_warp(kit, kit.landmark_positions(SCHEME, Vt), ids)
        assert r.stage == "C" and r.flags == []
        assert r.landmark_rms_mm["C"] < 1e-6 < r.landmark_rms_mm["A"]
        a.append(_face_rms(kit, bed, r.V_A, Vt))
        c.append(_face_rms(kit, bed, r.vertices, Vt))
    a, c = np.array(a), np.array(c)
    assert np.median(c / a) <= 0.7
    assert _rms(c) <= 0.7 * _rms(a)
    assert np.all(c < 0.85 * a)


# =========================================================================== stage D
class _FakeResult:
    def __init__(self, V, shift):
        self.V, self.landmark_shift_mm = V, np.asarray(shift, float)


class _FakeBasis:
    def __init__(self, V):
        self.V_bar = V


def test_stage_d_landmark_freeze_and_retry(kit):
    from face3d.fit.contour import CONTOUR
    V0 = kit.vertices
    basis = _FakeBasis(V0)
    calls = []

    def stage(shifts):
        def fn(b, views, obs, iod, term_kwargs=None, **kw):
            calls.append(dict(term_kwargs, **kw))
            return _FakeResult(V0 + float(len(calls)), [0.0, shifts[len(calls) - 1]])
        return fn

    # no contours: skipped
    V, res, flags = T.stage_d(basis, [], [], None, stage_fn=stage([9.0]))
    assert res is None and flags == [] and np.array_equal(V, V0) and not calls
    # accepted at full weight (forward kind weights and the backward weight are passed through)
    V, res, flags = T.stage_d(basis, ["v"], ["o"], [1.0], stage_fn=stage([0.4]), n_outer=2,
                              term_kwargs={"vertex_mask": None})
    assert flags == [] and np.array_equal(V, V0 + 1.0) and len(calls) == 1
    assert calls[0]["n_outer"] == 2 and "vertex_mask" in calls[0]
    assert calls[0]["kind_weights"] == {"hard": 1.0, "outer_bound": CONTOUR["outer_bound_weight"].value,
                                        "inner_bound": 1.0}
    assert calls[0]["backward_weight"] == CONTOUR["backward_weight"].value
    # a landmark moved 0.8 mm: rejected, retried once with half the contour weight, accepted
    calls.clear()
    V, res, flags = T.stage_d(basis, ["v"], ["o"], [1.0], stage_fn=stage([0.8, 0.3]))
    assert flags == [T.FLAG_CONTOUR_HALF] and len(calls) == 2 and np.array_equal(V, V0 + 2.0)
    assert calls[1]["kind_weights"]["hard"] == 0.5 * calls[0]["kind_weights"]["hard"]
    assert calls[1]["kind_weights"]["outer_bound"] == 0.5 * calls[0]["kind_weights"]["outer_bound"]
    assert calls[1]["backward_weight"] == 0.5 * calls[0]["backward_weight"]
    # still moving after the retry: rolled back to the stage-C surface
    calls.clear()
    V, res, flags = T.stage_d(basis, ["v"], ["o"], [1.0], stage_fn=stage([0.8, 0.6]))
    assert flags == [T.FLAG_LANDMARK_FREEZE] and len(calls) == 2 and np.array_equal(V, V0)
    assert res.landmark_shift_mm.max() == pytest.approx(0.6)


def test_stage_d_delegates_to_contour_stage(kit, bed):
    """One real WP-17 contour stage on the stage-C surface (front + profile masks of the true surface)."""
    import dataclasses
    import math

    from face3d.fit.contour import ContourObs
    from face3d.geometry.camera import Camera, look_at
    from face3d.mesh.raster import rasterize
    from face3d.mesh.reduced import ReducedDeformer, farthest_point_sample
    from face3d.solve.bundle import ViewObs, bundle_adjust
    from face3d.solve.shape_models import LinearBasis
    from face3d.testbed.render import landmark_visibility

    ids = bed["ids"]
    rng = np.random.default_rng(7)
    Vt = out_of_prior_subject(kit, rng).V_true
    Xt = kit.landmark_positions(SCHEME, Vt)
    E = Xt[[ids.index(n) for n in ("en_L", "en_R", "ex_L", "ex_R")]]
    iod_mm = float(np.linalg.norm(0.5 * (E[0] + E[2]) - 0.5 * (E[1] + E[3])))
    views, obs, iod = [], [], []
    for k, yaw in enumerate((0.0, 90.0, -45.0)):
        y = math.radians(yaw)
        tgt = np.array([0.0, 5.0, 40.0])
        R, t = look_at(tgt + 1000.0 * np.array([math.sin(y), 0.0, math.cos(y)]), tgt)
        c = Camera.centered(85.0 / 36.0 * 480, 480, 640, R=R, t=t)
        uv = c.project(Xt) + rng.normal(scale=0.5, size=(len(Xt), 2))
        uv[~landmark_visibility(kit, Vt, SCHEME, c)] = np.nan
        views.append(ViewObs(uv, c.copy(), f_prior=c.f, f_prior_log_sigma=0.05, sigma_px=1.0))
        obs.append(ContourObs.from_mask(rasterize(Vt, bed["tris"], c, cull_backfaces=True).mask, view=k,
                                        source="test_mask"))
        iod.append(c.f * iod_mm / float(c.depth(E.mean(axis=0, keepdims=True))[0]))
    lm = bundle_adjust(views, bed["prior"].mean(), None, prior=bed["prior"])
    r = T.staged_warp(kit, lm.X, ids, sigma_X_mm=U.landmark_sigma_mm(lm.cov), views_agree=np.sum(lm.inlier_mask, axis=0))
    assert r.stage == "C"
    front = np.flatnonzero(bed["face"])
    centers = front[farthest_point_sample(kit.vertices[front], 60)]
    basis = LinearBasis(kit, ReducedDeformer(r.vertices, centers_idx=centers))
    sviews = [dataclasses.replace(v, camera=c) for v, c in zip(views, lm.cameras)]
    V_D, res, flags = T.stage_d(basis, sviews, obs, iod, n_outer=2, term_kwargs={"vertex_mask": bed["face"]})
    assert res is not None and V_D.shape == r.vertices.shape
    if T.FLAG_LANDMARK_FREEZE in flags:
        assert np.array_equal(V_D, r.vertices)
    else:
        assert res.landmark_shift_mm.max() <= 0.5 and np.abs(V_D - r.vertices).max() > 1e-3
        assert T.fold_gate(r.vertices, V_D, bed["tris"])[0]
    # an impossible freeze threshold always rolls back
    V_R, _, flags_r = T.stage_d(basis, sviews, obs, iod, n_outer=1, term_kwargs={"vertex_mask": bed["face"]},
                                config=T.StagedWarpConfig(landmark_freeze_mm=1e-9))
    assert flags_r == [T.FLAG_LANDMARK_FREEZE] and np.array_equal(V_R, r.vertices)


# =========================================================================== uncertainty.py
def test_sigma_res_table_and_cov_propagation():
    assert U.SIGMA_RES_MM == {"eyes": 1.25, "nose": 2.5, "lips": 2.0, "cheeks": 3.25, "forehead": 2.5, "chin": 3.0,
                              "jaw": 3.0, "ears": 4.0, "scalp": 4.5, "neck": 7.5, "other": 3.0}
    rng = np.random.default_rng(5)
    Vn, N = 23, 6
    A = rng.normal(size=(Vn, N))
    M = rng.normal(size=(3 * N, 3 * N))
    S = M @ M.T
    cov = U.vertex_cov_stage_b(A, S, chunk=5)
    for j in (0, 7, 22):
        K = np.kron(A[j][None, :], np.eye(3))
        assert np.allclose(cov[j], K @ S @ K.T, rtol=1e-9, atol=1e-9)
    assert np.allclose(U.vertex_cov_stage_b(A, S, chunk=2000), cov)
    # a rank-deficient (PSD) covariance still factors
    S0 = M[:, :4] @ M[:, :4].T
    K = np.kron(A[3][None, :], np.eye(3))
    assert np.allclose(U.vertex_cov_stage_b(A, S0)[3], K @ S0 @ K.T, atol=1e-6)
    assert np.allclose(U.landmark_sigma_mm(S), np.sqrt(np.diag(S).reshape(-1, 3).sum(axis=1)))
    with pytest.raises(ValueError):
        U.vertex_cov_stage_b(A, S[:6, :6])
    # sigma_n: formula, inflation floor at 1, definition sigma, override drops sigma_res
    n = rng.normal(size=(Vn, 3))
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    regions = np.array((["eyes", "nose", "neck", "unknown-region"] * 6)[:Vn])
    res = np.array([{"eyes": 1.25, "nose": 2.5, "neck": 7.5}.get(r, 3.0) for r in regions])
    var = np.einsum("vi,vij,vj->v", n, cov, n)
    assert np.allclose(U.vertex_sigma_n(cov, n, regions), np.sqrt(var + res ** 2))
    assert np.allclose(U.vertex_sigma_n(cov, n, regions, 0.3), np.sqrt(var + res ** 2))
    sdef = {"eyes": 0.5, "other": 1.5}
    sd = np.array([sdef.get(r, 1.5) for r in regions])
    assert np.allclose(U.vertex_sigma_n(cov, n, regions, 2.5, sdef), np.sqrt(2.5 * var + res ** 2 + sd ** 2))
    assert np.allclose(U.vertex_sigma_n(cov, n, regions, 1.0, 0.7), np.sqrt(var + res ** 2 + 0.49))
    mask = np.arange(Vn) % 2 == 0
    co = 0.01 * cov
    out = U.vertex_sigma_n(cov, n, regions, 1.0, None, co, mask)
    assert np.allclose(out[mask], np.sqrt(0.01 * var[mask]))
    assert np.allclose(out[~mask], np.sqrt(var[~mask] + res[~mask] ** 2))
    with pytest.raises(ValueError):
        U.vertex_sigma_n(cov, n, regions, 1.0, None, co, None)
    d = U.landmark_region_sigma_def(["eyes", "eyes", "nose"], [0.5, 1.0, 1.5])
    assert d["eyes"] == pytest.approx(np.sqrt(0.625)) and d["nose"] == 1.5 and d["other"] == pytest.approx(
        np.sqrt((0.25 + 1.0 + 2.25) / 3.0))


def test_uncertainty_fd_check(kit, bed):
    """Relative error < 1e-6 for the stage-B linear map; every vertex sigma_n >= its sigma_res floor."""
    ids = bed["ids"]
    Vt = out_of_prior_subject(kit, np.random.default_rng(11)).V_true
    res, agree = _bundle(kit, bed, Vt, 211)
    sig = U.landmark_sigma_mm(res.cov)
    V_A, _, _ = T.stage_a(kit, res.X, ids)
    V_B, A = T.stage_b(V_A, kit, res.X, sig, ids)
    sub = np.arange(0, kit.n_verts, 7)                                  # every 7th vertex keeps the check fast

    def warp(X):
        return T.stage_b(V_A, kit, X, sig, ids)[0][sub]

    assert U.finite_difference_check(warp, res.X, A[sub]) < 1e-6
    assert U.finite_difference_check(warp, res.X, 1.01 * A[sub]) > 1e-3   # the check has teeth
    cov_v = U.vertex_cov_stage_b(A, res.cov)
    assert cov_v.shape == (kit.n_verts, 3, 3) and np.all(np.linalg.eigvalsh(cov_v)[:, 0] > -1e-9)
    normals = area_weighted_normals(V_B, kit.faces)
    sn = U.vertex_sigma_n(cov_v, normals, bed["regions"], max(1.0, res.chi2_red))
    floor = U.sigma_res_of(bed["regions"])
    assert np.all(sn >= floor) and np.all(np.isfinite(sn))
    # a vertex carrying a landmark has (close to) that landmark's posterior along the normal
    i = ids.index("prn")
    v = kit.landmark_vertices(SCHEME, ["prn"])[0]
    exact_A = T.stage_b(V_A, kit, res.X, None, ids)[1]
    assert np.allclose(U.vertex_cov_stage_b(exact_A[[v]], res.cov)[0], res.cov[3 * i:3 * i + 3, 3 * i:3 * i + 3],
                       atol=1e-6)


def test_coverage_measured_regions_small(kit, bed):
    """10 seeds, out-of-prior subjects, 7-view studio ring (detector-sim defaults: noise, definition
    bias, 5 % outliers): the fraction of measured-region vertices with |normal error| <= 1.96 sigma_n
    is in [0.85, 1.0] (pooled and per seed)."""
    ids = bed["ids"]
    meas = bed["measured"]
    lm_regions = bed["regions"][kit.landmark_vertices(SCHEME)]
    sdef = U.landmark_region_sigma_def(lm_regions, bed["sdef"])
    inside, total, fracs, zs = 0, 0, [], []
    for seed in range(10):
        Vt = out_of_prior_subject(kit, np.random.default_rng(seed)).V_true
        res, agree = _bundle(kit, bed, Vt, 100 + seed)
        r = T.staged_warp(kit, res.X, ids, sigma_X_mm=U.landmark_sigma_mm(res.cov), views_agree=agree)
        assert r.stage == "C" and r.flags == []
        cov_v = U.vertex_cov_stage_b(r.A_rows, res.cov)
        sn = U.vertex_sigma_n(cov_v, area_weighted_normals(r.vertices, kit.faces), bed["regions"],
                              max(1.0, res.chi2_red), sdef)
        err = _signed_distance(kit, bed, r.vertices, Vt, meas)
        hit = np.abs(err) <= 1.96 * sn[meas]
        inside += int(hit.sum())
        total += int(hit.size)
        fracs.append(float(hit.mean()))
        zs.append(_rms(err / sn[meas]))
    assert total == 10 * int(meas.sum()) and meas.sum() > 200
    assert 0.85 <= inside / total <= 1.0
    assert min(fracs) >= 0.85
    # recorded for the WP-19 report: sigma_n is conservative here (z RMS well below 1)
    assert 0.05 < np.median(zs) < 1.0
