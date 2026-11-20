import numpy as np
import pytest

from face3d.geometry import procrustes_rmse, rodrigues, rotation_to_rvec
from face3d.mesh import Mesh, Sparse, cg, cotan_laplacian, laplacian_deform, read_obj, uv_sphere, write_obj
from face3d.solve import PhotoLandmarks, Priors, ViewObs, bundle_adjust, reconstruct_landmarks
from face3d.solve.bundle import _Layout, _pack  # noqa: internal check
from face3d.synthetic import midline_indices, mirror_pairs, orbit_camera, random_subject, synthetic_landmarks

rng = np.random.default_rng(7)


# ------------------------------------------------------------------ sparse / mesh
def test_sparse_matches_dense_and_cg_solves():
    n = 60
    A = rng.normal(size=(n, n)) * (rng.random((n, n)) < 0.1)
    S = A.T @ A + n * np.eye(n)
    r, c = np.nonzero(S)
    sp = Sparse(r, c, S[r, c], (n, n))
    x = rng.normal(size=n)
    assert np.allclose(sp @ x, S @ x)
    assert np.allclose(sp.T.toarray(), S.T)
    b = S @ x
    xs, _ = cg(lambda v: sp @ v, b, precond=sp.diagonal(), tol=1e-12)
    assert np.allclose(xs, x, atol=1e-8)


def test_obj_roundtrip(tmp_path):
    m = uv_sphere(50, 8, 16)
    p = tmp_path / "s.obj"
    write_obj(m, p)
    m2 = read_obj(p)
    assert np.allclose(m.vertices, m2.vertices, atol=1e-5)
    assert m.faces == m2.faces
    assert len(m.boundary_vertices()) == 0  # closed surface


def test_cotan_laplacian_properties():
    m = uv_sphere(1.0, 16, 32)
    L, mass = cotan_laplacian(m.vertices, m.triangles())
    ones = np.ones(m.n_vertices)
    assert np.allclose(L @ ones, 0, atol=1e-9)           # constants in the null space
    assert np.isclose(mass.sum(), 4 * np.pi, rtol=0.02)    # unit sphere area
    x = rng.normal(size=m.n_vertices)
    assert x @ (L @ x) >= -1e-9                            # positive semi-definite


def test_laplacian_deform_hits_constraints_and_stays_smooth():
    m = uv_sphere(100.0, 20, 40)
    tip = int(np.argmax(m.vertices[:, 2]))               # front-most vertex
    back = int(np.argmin(m.vertices[:, 2]))
    target = m.vertices[[tip, back]] + np.array([[0, 0, 20.0], [0, 0, 0]])
    V, _ = laplacian_deform(m, np.array([tip, back]), target, weight=1e4)
    assert np.linalg.norm(V[tip] - target[0]) < 0.5
    assert np.linalg.norm(V[back] - target[1]) < 0.5
    # Displacement decays smoothly away from the pulled vertex.
    d = np.linalg.norm(V - m.vertices, axis=1)
    near = np.linalg.norm(m.vertices - m.vertices[tip], axis=1) < 30
    far = np.linalg.norm(m.vertices - m.vertices[tip], axis=1) > 150
    assert d[near].mean() > d[far].mean() * 3


# ------------------------------------------------------------------ bundle adjustment
def _scene(n_views=5, f35=26.0, dist=420.0, noise=0.8, yaws=(-60, -30, 0, 30, 60)):
    names, T = synthetic_landmarks()
    subj = random_subject(T, names, rng)
    cams = [orbit_camera(dist, y, rng.uniform(-8, 8), f35) for y in yaws[:n_views]]
    photos = []
    for c in cams:
        uv = c.project(subj) + rng.normal(scale=noise, size=(len(subj), 2))
        # Self-occlusion proxy: hide landmarks on the far side of the head.
        n_dir = c.center - subj
        facing = (subj - np.array([0, 0, 0.0]))
        hidden = np.einsum("ij,ij->i", n_dir / np.linalg.norm(n_dir, axis=1, keepdims=True),
                           facing / np.linalg.norm(facing, axis=1, keepdims=True)) < -0.1
        uv[hidden] = np.nan
        photos.append(PhotoLandmarks(uv, c.width, c.height, sigma_px=noise))
    pri = Priors(mean=T, sigma=8.0, pairs=mirror_pairs(names), sigma_sym=3.0,
                 midline=midline_indices(names), sigma_mid=2.0)
    return names, T, subj, cams, photos, pri


def test_bundle_jacobian_matches_numeric():
    names, T, subj, cams, photos, pri = _scene(n_views=3)
    views = [ViewObs(ph.uv, c.copy(), estimate_focal=True, f_prior=c.f * 1.1) for ph, c in zip(photos, cams)]
    # Capture the closures by running a zero-iteration solve through a tiny shim.
    import face3d.solve.bundle as B
    captured = {}
    orig = B.levenberg_marquardt

    def shim(fun, x0, jac=None, retract=None, **kw):
        captured.update(fun=fun, jac=jac, retract=retract, x0=x0)
        return orig(fun, x0, jac=jac, retract=retract, max_iter=0)
    B.levenberg_marquardt = shim
    try:
        bundle_adjust(views, subj + rng.normal(scale=2, size=subj.shape), pri, huber_px=None)
    finally:
        B.levenberg_marquardt = orig
    fun, jac, retract, x0 = captured["fun"], captured["jac"], captured["retract"], captured["x0"]
    Ja = jac(x0)
    h = 1e-6
    Jn = np.zeros_like(Ja)
    for j in range(len(x0)):
        e = np.zeros(len(x0)); e[j] = h
        Jn[:, j] = (fun(retract(x0, e)) - fun(retract(x0, -e))) / (2 * h)
    assert np.allclose(Ja, Jn, rtol=1e-4, atol=1e-4 * np.abs(Jn).max())


def test_reconstruct_recovers_subject_shape_unknown_focal():
    names, T, subj, cams, photos, pri = _scene()
    res = reconstruct_landmarks(photos, pri)
    err_template = procrustes_rmse(T, subj)
    err_recon = procrustes_rmse(res.X, subj)
    assert err_recon < 1.5, err_recon
    assert err_recon < 0.35 * err_template
    for c_est, c_true in zip(res.cameras, cams):
        assert abs(c_est.f / c_true.f - 1) < 0.08
    assert max(res.rmse_px) < 3.0


def test_reconstruct_with_exif_prior_long_lens():
    # 85 mm portrait shots from ~1.4 m: weak perspective, focal needs the EXIF prior.
    names, T, subj, cams, photos, pri = _scene(f35=85.0, dist=1400.0, noise=1.0)
    for ph, c in zip(photos, cams):
        ph.f_prior_px = c.f * rng.uniform(0.95, 1.05)
    res = reconstruct_landmarks(photos, pri)
    assert procrustes_rmse(res.X, subj) < 2.0


def test_point_uncertainty_reflects_coverage():
    names, T, subj, cams, photos, pri = _scene()
    res = reconstruct_landmarks(photos, pri)
    sig = res.point_sigma_mm
    assert sig is not None and sig.shape == subj.shape
    assert np.all(sig < 8.0)                      # never worse than the prior
    seen = np.stack([~np.isnan(ph.uv[:, 0]) for ph in photos]).sum(0)
    many, few = seen >= 4, seen <= 2
    if many.any() and few.any():
        assert np.median(sig[few]) > np.median(sig[many])
    # Single frontal photo: depth (z) is far less certain than x/y.
    _, T, subj, cams, photos, pri = _scene(n_views=1, yaws=(0,))
    res1 = reconstruct_landmarks(photos, pri)
    s1 = res1.point_sigma_mm
    assert np.median(s1[:, 2]) > 2 * np.median(s1[:, 0])


def test_shared_focal_group_and_exif_strength():
    # Same phone, same zoom: one shared focal. A tight EXIF prior that is 3 % off
    # must hold the focal nearer the prior than a loose prior does; with the loose
    # prior the five close views recover the true focal.
    def run(log_sigma):
        global rng
        rng = np.random.default_rng(11)
        names, T, subj, cams, photos, pri = _scene(f35=26.0, dist=450.0)
        for ph in photos:
            ph.focal_group = "phone"
            ph.f_prior_px = cams[0].f * 1.03
            ph.f_prior_log_sigma = log_sigma
        res = reconstruct_landmarks(photos, pri)
        return res, cams[0].f, subj
    tight, true_f, subj = run(0.005)
    mid, _, _ = run(0.05)
    loose, _, _ = run(0.6)
    fs = [c.f for c in tight.cameras]
    assert np.ptp(fs) < 1e-9                                   # one shared value
    r_t, r_m, r_l = (x.cameras[0].f / true_f for x in (tight, mid, loose))
    assert abs(r_l - 1) < 0.01                                 # data decides
    assert r_t > r_m >= r_l - 1e-4                             # monotone pull toward prior
    assert r_t - r_l > 0.008
    assert procrustes_rmse(tight.X, subj) < 1.5


def test_auto_sigma_scales_with_face_size():
    names, T, subj, cams, photos, pri = _scene()
    ph = photos[2]
    auto = PhotoLandmarks(ph.uv, ph.width, ph.height).resolved_sigma_px()
    big = PhotoLandmarks(ph.uv * 2.0, ph.width * 2, ph.height * 2).resolved_sigma_px()
    assert np.isclose(big, 2 * auto)
    assert 1.0 < auto < 50.0
