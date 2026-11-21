"""WP-06 M1 cheap fixes: silhouette normal-only correction, multi-start PnP with the
C-TWIN flag, focal/distance ladders, inverse-depth and virtual-camera helpers.

DESIGN D-02, D-11, D-12, D-13, 4.2, 4.3; acceptance tests of WP-06 in docs/wbs.json.
"""
import numpy as np
import pytest

from face3d.core import config
from face3d.fit import ContourView, fit_silhouettes, silhouette_vertices
from face3d.geometry import Camera, look_at
from face3d.geometry.camera import (apply_homography, camera_to_invdepth, face_ray_angle, focal_px_from_35mm,
                                    invdepth_to_camera, project_invdepth, rectilinear_virtual_camera,
                                    rectilinear_virtual_homography, stereographic_project, stereographic_unproject,
                                    stereographic_virtual_camera, virtual_rotation)
from face3d.geometry.rotations import euler_xyz_deg, rodrigues, rotation_from_euler_deg
from face3d.io.exif import ExifInfo
from face3d.mesh import uv_sphere
from face3d.solve.focal import (HEAD_ORIGIN_OFFSET_MM, FocalPrior, aspect_is_native, distance_prior,
                                distance_prior_head_origin, focal_group_key, focal_prior_from_evidence,
                                is_phone_make)
from face3d.solve.lm import numeric_jacobian
from face3d.solve.pnp import (DEFAULT_F35_HYPOTHESES, PnPResult, _project, _project_jacobian, rotation_angle_deg,
                              solve_pnp, start_poses)
from face3d.synthetic import orbit_camera, synthetic_landmarks


def _rot_err_deg(Ra, Rb):
    return rotation_angle_deg(Ra, Rb)


def _random_rotation(rng):
    return rodrigues(rng.normal(size=3) * rng.uniform(0.1, 2.5) / 1.7)


# --------------------------------------------------------------------- (a) silhouette

def _far_profile_cam(dist=20000.0):
    """Near-orthographic profile camera (+x side) framing the 80 mm sphere like _profile_cam in test_fit."""
    R, t = look_at(np.array([dist, 0, 0.0]), np.zeros(3))
    return Camera.centered(4000.0 * dist / 700.0, 3000, 3000, R=R, t=t)


def test_no_tangential_drift():
    """Outline = the mesh's own projected silhouette (upper half), sampled in one-sided clusters along
    the contour. Normal-only correction must leave the mesh in place; the legacy full correction drags
    rim vertices along the contour (DESIGN D-13 defect 1). The near-orthographic camera keeps the rim
    on one meridian, so the test isolates tangential drift from the vertex-staircase (half-edge) bias
    that the sub-vertex rim of WP-17 addresses."""
    m = uv_sphere(80, 40, 80)
    cam = _far_profile_cam()
    V = m.vertices
    sil = silhouette_vertices(V, m.triangles(), cam)
    up = sil[V[sil, 1] > 0]                       # upper half of the outline only
    P = cam.project(V[up])
    n3 = m.vertex_normals()[up]
    ray = V[up] - cam.center
    t3 = np.cross(n3, ray / np.linalg.norm(ray, axis=1, keepdims=True))   # 3D rim tangent
    t3 /= np.linalg.norm(t3, axis=1, keepdims=True)
    t2 = cam.project(V[up] + t3) - P                                        # its image direction
    t2 /= np.linalg.norm(t2, axis=1, keepdims=True)
    outline = np.concatenate([P + s * t2 for s in (1.0, 2.0, 3.0, 4.0)])   # clustered, one-sided
    assert len(up) > 30

    Vn, hist_n = fit_silhouettes(m, [ContourView(cam, outline)], iterations=8, normal_only=True)
    move_n = np.linalg.norm(Vn - V, axis=1).max()
    assert move_n <= 0.05, move_n
    assert max(hist_n) < 0.05  # across-contour error stays ~0 px

    Vl, _ = fit_silhouettes(m, [ContourView(cam, outline)], iterations=8, normal_only=False)
    move_l = np.linalg.norm(Vl - V, axis=1).max()
    assert move_l > 0.5, move_l


def test_normal_only_is_default_and_legacy_flag_kept():
    import inspect
    sig = inspect.signature(fit_silhouettes)
    assert sig.parameters["normal_only"].default is True


# --------------------------------------------------------------------- (b) PnP

def test_pnp_ten_hypotheses():
    assert DEFAULT_F35_HYPOTHESES == (13, 24, 26, 35, 50, 77, 85, 120, 135, 200)
    assert all(isinstance(v, float) for v in DEFAULT_F35_HYPOTHESES)


def test_pnp_result_positional_api_unchanged():
    cam = Camera.centered(1000.0, 100, 100)
    r = PnPResult(cam, 0.5, np.zeros(4), True)
    assert r.twin is None and r.flags == [] and r.candidates_tried == 0
    r2 = PnPResult(cam, 0.5, np.zeros(4), True)
    r.flags.append("X")
    assert r2.flags == []  # default_factory, not a shared list


def test_pnp_recovers_77mm_unknown_focal():
    _, X = synthetic_landmarks()
    cam = orbit_camera(1000, 20, 0, 77)
    res = solve_pnp(X, cam.project(X), cam.width, cam.height)
    assert res.focal_estimated
    assert abs(res.camera.f / cam.f - 1) < 0.01
    assert res.rmse_px < 1e-3
    assert res.candidates_tried == 3 * len(DEFAULT_F35_HYPOTHESES)
    assert "C-TWIN" not in res.flags and res.twin is None


def test_pnp_start_poses_flip_and_keep_centroid():
    _, X = synthetic_landmarks()
    cam = orbit_camera(900, 25, 12, 50)
    starts = start_poses(cam.R, cam.t, X)
    assert [k for k, _, _ in starts] == ["affine", "pitch_flip", "yaw_mirror"]
    p, y, r = euler_xyz_deg(cam.R)
    mu = X.mean(0)
    c0 = cam.R @ mu + cam.t
    _, Rp, tp = starts[1]
    _, Ry, ty = starts[2]
    assert np.allclose(Rp, rotation_from_euler_deg(-p, y, r), atol=1e-12)
    assert np.allclose(Ry, rotation_from_euler_deg(p, -y, r), atol=1e-12)
    assert np.allclose(Rp @ mu + tp, c0, atol=1e-9)
    assert np.allclose(Ry @ mu + ty, c0, atol=1e-9)
    assert _rot_err_deg(Ry, cam.R) > 40  # a genuinely different start


def _near_planar_patch(relief_mm=0.5):
    """7 x 7 landmark patch, +-40 mm, with a shallow dome of `relief_mm` (a near-planar target)."""
    g = np.linspace(-40.0, 40.0, 7)
    gx, gy = np.meshgrid(g, g)
    gx, gy = gx.ravel(), gy.ravel()
    return np.column_stack([gx, gy, 60.0 + relief_mm * (1.0 - (gx ** 2 + gy ** 2) / 3200.0)])


def test_pnp_twin_flag():
    """Near-weak-perspective frontal view (200 mm-eq at 3 m, pitch 10 deg, 2 px noise) of a near-planar
    landmark set: the pitch-reversed pose fits almost as well -> C-TWIN with a twin camera. The same
    patch at 26 mm-eq / 0.4 m (strong perspective) has no twin. Focal comes from the EXIF rung of the
    ladder (sigma 0.04): with focal free the focal/depth ambiguity lets the twin slide back."""
    Xp = _near_planar_patch()
    rng = np.random.default_rng(0)

    cam = orbit_camera(3000, 0, 10, 200)
    uv = cam.project(Xp) + rng.normal(scale=2.0, size=(len(Xp), 2))
    fp = focal_prior_from_evidence(ExifInfo(focal_35mm=200.0, make="Canon"), cam.width, cam.height)
    assert fp.source_code == "exif_f35" and fp.log_sigma == 0.04
    res = solve_pnp(Xp, uv, cam.width, cam.height, f_prior_px=fp.f_px, f_prior_log_sigma=fp.log_sigma)
    assert "C-TWIN" in res.flags
    assert isinstance(res.twin, Camera)
    sep = _rot_err_deg(res.twin.R, res.camera.R)
    assert 10.0 < sep < 30.0, sep                       # about twice the 10 deg pitch
    truth = min(_rot_err_deg(res.camera.R, cam.R), _rot_err_deg(res.twin.R, cam.R))
    assert truth < 3.0                                  # one of the two is the true pose
    e_twin = np.linalg.norm(res.twin.project(Xp) - uv, axis=1)
    assert np.sqrt(np.mean(e_twin ** 2)) < 1.2 * res.rmse_px  # the twin explains the image almost as well
    assert res.candidates_tried == 3                    # one (prior) focal x three starts

    cam2 = orbit_camera(400, 0, 10, 26)
    uv2 = cam2.project(Xp) + rng.normal(scale=2.0, size=(len(Xp), 2))
    fp2 = focal_prior_from_evidence(ExifInfo(focal_35mm=26.0, make="Apple"), cam2.width, cam2.height)
    res2 = solve_pnp(Xp, uv2, cam2.width, cam2.height, f_prior_px=fp2.f_px, f_prior_log_sigma=fp2.log_sigma)
    assert "C-TWIN" not in res2.flags and res2.twin is None
    assert _rot_err_deg(res2.camera.R, cam2.R) < 2.0

    # A face's depth relief disambiguates the same far view: no twin.
    _, X = synthetic_landmarks()
    uv3 = cam.project(X) + rng.normal(scale=2.0, size=(len(X), 2))
    res3 = solve_pnp(X, uv3, cam.width, cam.height, f_prior_px=fp.f_px, f_prior_log_sigma=fp.log_sigma)
    assert "C-TWIN" not in res3.flags and _rot_err_deg(res3.camera.R, cam.R) < 1.0


def test_pnp_huber_in_sigma_units():
    _, X = synthetic_landmarks()
    rng = np.random.default_rng(1)
    cam = orbit_camera(600, -25, 0, 35)
    uv = cam.project(X) + rng.normal(scale=0.5, size=(len(X), 2))
    uv[[3, 10, 20]] += np.array([[80, -40], [-60, 90], [120, 30]])  # bad detections (test_solvers scene)
    res = solve_pnp(X, uv, cam.width, cam.height, f_px=cam.f, sigma_px=0.5, huber_sigmas=2)
    assert _rot_err_deg(res.camera.R, cam.R) < 1.0
    assert np.median(res.residuals_px) < 2.0
    # Per-point sigma arrays are accepted; a huge sigma on the outliers has the same effect.
    s = np.full(len(X), 0.5)
    s[[3, 10, 20]] = 1e3
    res_l2 = solve_pnp(X, uv, cam.width, cam.height, f_px=cam.f, sigma_px=s, huber_sigmas=None)
    assert _rot_err_deg(res_l2.camera.R, cam.R) < 1.0
    with pytest.raises(ValueError):
        solve_pnp(X, uv, cam.width, cam.height, f_px=cam.f, sigma_px=np.ones(3))
    with pytest.raises(ValueError):
        solve_pnp(X, uv, cam.width, cam.height, f_px=cam.f, sigma_px=0.0)


def test_pnp_analytic_jacobian_matches_numeric():
    rng = np.random.default_rng(5)
    X = rng.normal(scale=50.0, size=(15, 3))
    for v in (rng.normal(size=3), np.array([1e-10, 0.0, 0.0]), np.array([np.pi - 1e-3, 0.02, 0.0])):
        q = np.concatenate([v, [5.0, -3.0, 800.0], [np.log(3000.0)]])
        for f_fixed in (None, 2500.0):
            qq = q if f_fixed is None else q[:6]
            Jn = numeric_jacobian(lambda p: _project(p, X, 10.0, 20.0, f_fixed).ravel(), qq)
            Ja = _project_jacobian(qq, X, f_fixed).reshape(2 * len(X), -1)
            assert np.abs(Jn - Ja).max() <= 1e-7 * np.abs(Jn).max()


# --------------------------------------------------------------------- (c) focal and distance ladders

def test_focal_ladder_precedence():
    W, H = 4000, 2000  # 2:1, not a native aspect
    exif = ExifInfo(focal_35mm=52.0, focal_length_mm=6.0, digital_zoom_ratio=2.0, make="Apple",
                    focal_plane_x_res=250.0, focal_plane_res_unit=4, width=4000)
    f52 = focal_px_from_35mm(52.0, W, H)

    def fp(e, w=W, h=H, **kw):
        return focal_prior_from_evidence(e, w, h, **kw)

    r = fp(exif, sfm_f_px=3100.0, calibrated_f_px=3200.0)
    assert (r.f_px, r.log_sigma, r.source_code) == (3100.0, 0.01, "sfm")
    r = fp(exif, calibrated_f_px=3200.0)
    assert (r.f_px, r.log_sigma, r.source_code) == (3200.0, 0.01, "calibrated")
    r = fp(exif)
    assert (r.log_sigma, r.source_code) == (0.06, "zoom") and r.f_px == pytest.approx(f52, rel=1e-12)
    # zoom by the focal-group ratio test (f35/FocalLength = 8.67 > 1.02 x 8.0)
    exif.digital_zoom_ratio = 1.0
    r = fp(exif, group_crop_ratio_mode=8.0)
    assert (r.log_sigma, r.source_code) == (0.06, "zoom")
    r = fp(exif, group_crop_ratio_mode=52.0 / 6.0)  # ratio equals the group mode: no zoom
    assert (r.log_sigma, r.source_code) == (0.09, "aspect")
    r = fp(exif)  # no group information, DigitalZoomRatio 1: aspect rule
    assert (r.log_sigma, r.source_code) == (0.09, "aspect")
    r = fp(exif, 4032, 3024)
    assert (r.log_sigma, r.source_code) == (0.04, "exif_f35")
    assert r.f_px == pytest.approx(52.0 * np.hypot(4032, 3024) / 43.2666, rel=1e-5)
    exif.focal_35mm = None
    r = fp(exif, 4000, 3000)
    assert (r.log_sigma, r.source_code) == (0.10, "focal_plane") and r.f_px == pytest.approx(6.0 * 250.0)
    exif.focal_plane_x_res = None
    r = fp(exif, 4000, 3000)
    assert (r.log_sigma, r.source_code) == (0.25, "phone")
    assert r.f_px == pytest.approx(focal_px_from_35mm(26.0, 4000, 3000))
    r = fp(exif, 4000, 3000, is_phone=False)
    assert (r.log_sigma, r.source_code) == (0.6, "nothing")
    r = fp(None, 4000, 3000, is_phone=True)
    assert (r.log_sigma, r.source_code) == (0.25, "phone")
    r = fp(None, 4000, 3000)
    assert (r.log_sigma, r.source_code) == (0.6, "nothing")
    assert r.f_px == pytest.approx(50.0 * np.hypot(4000, 3000) / 43.2666, rel=1e-5)
    assert isinstance(r, FocalPrior)


def test_focal_ladder_aspects_phones_and_overrides():
    assert aspect_is_native(4032, 3024) and aspect_is_native(3024, 4032) and aspect_is_native(1920, 1080)
    assert aspect_is_native(6000, 4000) and aspect_is_native(4030, 3000)      # within 1 %
    assert not aspect_is_native(3000, 3000) and not aspect_is_native(4000, 2000)
    assert not aspect_is_native(4000, 3000, native_aspects=((3, 2),))
    for make in ("Apple", "samsung", "Google", "Xiaomi", "OnePlus", "HUAWEI", "OPPO", "vivo",
                 "Sony Mobile Communications"):
        assert is_phone_make(make), make
    for make in ("SONY", "Canon", "NIKON CORPORATION", None, ""):
        assert not is_phone_make(make), make
    cfg = config.resolve({"focal": {"sigma_log_exif": 0.05}})
    r = focal_prior_from_evidence(ExifInfo(focal_35mm=26.0), 4032, 3024, cfg=cfg)
    assert (r.log_sigma, r.source_code) == (0.05, "exif_f35")
    d = config.get("focal.sigma_log_exif")
    assert d.value == 0.04 and d.badge in config.BADGES and d.source


def test_distance_ladder_precedence():
    front = ExifInfo(make="Apple", focal_35mm=85.0, lens_model="iPhone 15 Pro front camera 2.69mm f/1.9")
    assert distance_prior(front, taped_mm=600.0) == (600.0, pytest.approx(50.0 / 600.0))
    assert distance_prior(front) == (350.0, 0.3)
    assert distance_prior(None, is_front_camera=True) == (350.0, 0.3)
    tele = ExifInfo(make="Apple", focal_35mm=85.0, lens_model="iPhone 15 Pro back triple camera")
    assert distance_prior(tele) == (2000.0, 0.4)
    assert distance_prior(front, is_front_camera=False) == (2000.0, 0.4)
    assert distance_prior(ExifInfo(focal_35mm=70.0)) == (2000.0, 0.4)
    assert distance_prior(ExifInfo(make="Apple", focal_35mm=26.0)) == (800.0, 0.4)
    assert distance_prior(ExifInfo(make="Canon")) == (800.0, 0.4)
    assert distance_prior(ExifInfo()) == (1000.0, 0.7)
    assert distance_prior(None) == (1000.0, 0.7)
    med, sig = distance_prior(None)
    assert (med, sig) == (1000.0, 0.7)
    with pytest.raises(ValueError):
        distance_prior(None, taped_mm=0.0)
    assert HEAD_ORIGIN_OFFSET_MM == 100.0
    assert distance_prior_head_origin(None) == (1100.0, 0.7)
    assert distance_prior_head_origin(front) == (450.0, 0.3)
    m, s = distance_prior_head_origin(None, taped_mm=400.0)
    assert m == 500.0 and s == pytest.approx(50.0 / 500.0)


def test_focal_group_key():
    ex = ExifInfo(make="Apple", model="iPhone 15", lens_model="back camera", focal_35mm=26.0)
    k = focal_group_key(ex, 4032, 3024)
    assert k == ex.focal_group_key(4032, 3024) == "Apple|iPhone 15|back camera|26|4032|3024|still"
    kv = focal_group_key(ex, 4032, 3024, still=False)
    assert kv.endswith("|video") and kv != k
    assert focal_group_key(None, 4032, 3024) is None
    assert focal_group_key(ExifInfo(), 4032, 3024) is None


# --------------------------------------------------------------------- (d) camera helpers

def _random_camera(rng):
    W, H = int(rng.integers(800, 6000)), int(rng.integers(800, 6000))
    return Camera(f=float(rng.uniform(400, 25000)), cx=W / 2 + rng.uniform(-50, 50), cy=H / 2 + rng.uniform(-50, 50),
                  width=W, height=H, R=_random_rotation(rng),
                  t=np.array([rng.uniform(-80, 80), rng.uniform(-80, 80), rng.uniform(200, 5000)]))


def test_invdepth_roundtrip_exact():
    rng = np.random.default_rng(11)
    for _ in range(50):
        c = _random_camera(rng)
        p = camera_to_invdepth(c)
        assert set(p) == {"R", "tau", "s", "rho"} and p["tau"].shape == (2,)
        assert p["rho"] == pytest.approx(1.0 / c.t[2], rel=1e-15) and p["s"] == pytest.approx(c.f / c.t[2])
        c2 = invdepth_to_camera(p["R"], p["tau"], p["s"], p["rho"], like=c)
        assert np.array_equal(c2.R, c.R)
        assert np.all(np.abs(c2.t - c.t) <= 1e-12 * np.abs(c.t[2]))
        assert abs(c2.f / c.f - 1.0) <= 1e-12
        assert (c2.cx, c2.cy, c2.width, c2.height) == (c.cx, c.cy, c.width, c.height)
        X = rng.uniform(-100, 100, size=(40, 3))
        X = X[(X @ c.R.T + c.t)[:, 2] > 50]
        uv = project_invdepth(X, p["R"], p["tau"], p["s"], p["rho"], c.cx, c.cy)
        assert np.abs(uv - c.project(X)).max() < 5e-9
    bad = Camera.centered(1000.0, 100, 100, t=np.array([0.0, 0.0, -5.0]))
    with pytest.raises(ValueError):
        camera_to_invdepth(bad)
    with pytest.raises(ValueError):
        invdepth_to_camera(np.eye(3), np.zeros(2), 1.0, 0.0, like=bad)


def test_stereographic_local_magnification():
    f, theta, psi, h = 1000.0, np.radians(35.0), np.radians(30.0), 1e-6

    def ray(phi, az):
        return np.array([[np.sin(phi) * np.cos(az), np.sin(phi) * np.sin(az), np.cos(phi)]])

    def mags(proj):
        rad = np.linalg.norm(proj(ray(theta + h, psi)) - proj(ray(theta - h, psi))) / (2 * h)
        tan = np.linalg.norm(proj(ray(theta, psi + h)) - proj(ray(theta, psi - h))) / (2 * h * np.sin(theta))
        return rad / f, tan / f

    rad_s, tan_s = mags(lambda d: stereographic_project(d, f, 0.0, 0.0))
    expected = 1.0 / np.cos(theta / 2) ** 2
    assert expected == pytest.approx(1.0994, abs=1e-4)
    assert abs(rad_s - expected) < 1e-4 and abs(tan_s - expected) < 1e-4
    pin = Camera(f, 0.0, 0.0, 100, 100)  # R = I, t = 0: rectilinear
    rad_r, tan_r = mags(pin.project)
    assert abs(rad_r - 1.0 / np.cos(theta) ** 2) < 1e-4 and abs(rad_r - 1.4903) < 1e-4
    assert abs(tan_r - 1.0 / np.cos(theta)) < 1e-4 and abs(tan_r - 1.2208) < 1e-4
    # radius law r = 2 f tan(phi/2) and exact inverse
    uv = stereographic_project(ray(theta, psi) * 7.0, f, 10.0, 20.0)
    assert np.hypot(uv[0, 0] - 10.0, uv[0, 1] - 20.0) == pytest.approx(2 * f * np.tan(theta / 2), rel=1e-12)
    assert np.allclose(stereographic_unproject(uv, f, 10.0, 20.0), ray(theta, psi), atol=1e-12)


def test_virtual_rectilinear_homography_exact():
    rng = np.random.default_rng(4)
    for _ in range(10):
        c = _random_camera(rng)
        # a face centre ~20-40 deg off-axis at the camera's distance
        az, th = rng.uniform(0, 2 * np.pi), np.radians(rng.uniform(20, 40))
        d = np.array([np.sin(th) * np.cos(az), np.sin(th) * np.sin(az), np.cos(th)])
        Xc_centre = d * c.t[2]
        X_centre = c.R.T @ (Xc_centre - c.t)
        assert face_ray_angle(c, X_centre) == pytest.approx(th, abs=1e-12)
        Rv = virtual_rotation(c, X_centre)
        assert np.allclose(Rv @ d, [0, 0, 1], atol=1e-12) and np.allclose(Rv @ Rv.T, np.eye(3), atol=1e-12)
        virt, H = rectilinear_virtual_camera(c, X_centre)
        assert np.allclose(H, rectilinear_virtual_homography(c, Rv))
        assert virt.f == c.f and np.allclose(virt.center, c.center, atol=1e-9)
        X = X_centre + rng.uniform(-90, 90, size=(30, 3))
        assert np.abs(apply_homography(H, c.project(X)) - virt.project(X)).max() < 1e-9
        assert np.allclose(virt.project(X_centre[None]), [[virt.cx, virt.cy]], atol=1e-9)
    assert np.allclose(virtual_rotation(Camera.centered(100.0, 10, 10, t=np.array([0, 0, 5.0])), np.zeros(3)),
                       np.eye(3))


def test_stereographic_virtual_camera_exact_and_locally_identity():
    rng = np.random.default_rng(9)
    c = _random_camera(rng)
    th = np.radians(35.0)
    d = np.array([np.sin(th), 0.0, np.cos(th)])
    X_centre = c.R.T @ (d * 600.0 - c.t)
    virt, to_virtual = stereographic_virtual_camera(c, X_centre)
    assert virt.f == pytest.approx(c.f / np.cos(th / 2) ** 2, rel=1e-12)
    assert np.allclose(virt.R, virtual_rotation(c, X_centre) @ c.R, atol=1e-12)
    X = X_centre + rng.uniform(-90, 90, size=(30, 3))
    uv_st = stereographic_project(c.to_camera(X), c.f, c.cx, c.cy)
    assert np.abs(to_virtual(uv_st) - virt.project(X)).max() < 1e-8
    # equal local magnification: the map is the identity to first order at the face centre
    u0 = stereographic_project(c.to_camera(X_centre[None]), c.f, c.cx, c.cy)[0]
    assert np.allclose(to_virtual(u0[None])[0], u0, atol=1e-8)
    J = numeric_jacobian(lambda u: to_virtual(u[None])[0], u0, step=1e-4)
    assert np.allclose(J, np.eye(2), atol=1e-6)
