import numpy as np
import pytest

from face3d.geometry import focal_px_from_35mm
from face3d.solve import levenberg_marquardt, solve_pnp, triangulate_points
from face3d.synthetic import orbit_camera, synthetic_landmarks

rng = np.random.default_rng(1)


def test_lm_rosenbrock():
    def r(x):
        return np.array([10 * (x[1] - x[0] ** 2), 1 - x[0]])
    res = levenberg_marquardt(r, np.array([-1.2, 1.0]), max_iter=500)
    assert np.allclose(res.x, [1, 1], atol=1e-6)


@pytest.mark.parametrize("f35,dist,yaw,pitch", [
    (26, 350, 0, 0),      # phone selfie distance: strong perspective
    (26, 450, 35, 5),     # three-quarter selfie
    (50, 900, -60, -5),   # normal lens, near profile
    (85, 1400, 15, 10),   # portrait lens
])
def test_pnp_known_focal_exact(f35, dist, yaw, pitch):
    _, X = synthetic_landmarks()
    cam = orbit_camera(dist, yaw, pitch, f35)
    uv = cam.project(X)
    res = solve_pnp(X, uv, cam.width, cam.height, f_px=cam.f)
    assert res.rmse_px < 1e-4
    assert np.allclose(res.camera.R, cam.R, atol=1e-6)
    assert np.allclose(res.camera.center, cam.center, atol=1e-3)


@pytest.mark.parametrize("f35,dist,yaw", [(26, 350, 0), (26, 400, 30), (35, 500, -20)])
def test_pnp_unknown_focal_close_range(f35, dist, yaw):
    # At selfie distances the depth relief of the face makes focal length observable.
    _, X = synthetic_landmarks()
    cam = orbit_camera(dist, yaw, 3, f35)
    uv = cam.project(X)
    res = solve_pnp(X, uv, cam.width, cam.height)
    assert res.rmse_px < 1e-3
    assert abs(res.camera.f / cam.f - 1) < 1e-3
    assert np.linalg.norm(res.camera.center - cam.center) < 1.0


def test_pnp_unknown_focal_with_noise_uses_prior():
    _, X = synthetic_landmarks()
    cam = orbit_camera(1500, 20, 0, 85)
    uv = cam.project(X) + rng.normal(scale=1.0, size=(len(X), 2))
    # EXIF says ~85 mm equivalent; the prior keeps the ill-posed focal in check.
    prior = focal_px_from_35mm(85, cam.width, cam.height) * 1.1
    res = solve_pnp(X, uv, cam.width, cam.height, f_prior_px=prior, estimate_focal=True)
    assert res.rmse_px < 2.0
    assert abs(res.camera.f / cam.f - 1) < 0.15
    ang = np.degrees(np.arccos(np.clip((np.trace(res.camera.R.T @ cam.R) - 1) / 2, -1, 1)))
    assert ang < 2.0


def test_pnp_robust_to_outliers():
    _, X = synthetic_landmarks()
    cam = orbit_camera(600, -25, 0, 35)
    uv = cam.project(X) + rng.normal(scale=0.5, size=(len(X), 2))
    uv[[3, 10, 20]] += np.array([[80, -40], [-60, 90], [120, 30]])  # bad detections
    res = solve_pnp(X, uv, cam.width, cam.height, f_px=cam.f, huber_px=3.0)
    ang = np.degrees(np.arccos(np.clip((np.trace(res.camera.R.T @ cam.R) - 1) / 2, -1, 1)))
    assert ang < 1.0
    assert np.median(res.residuals_px) < 2.0


def test_triangulation_multiview():
    _, X = synthetic_landmarks()
    cams = [orbit_camera(700, yaw, 0, 50) for yaw in (-45, 0, 45)]
    obs = np.stack([c.project(X) for c in cams]) + rng.normal(scale=0.3, size=(3, len(X), 2))
    vis = np.ones((3, len(X)), bool)
    vis[0, 5] = vis[1, 5] = False  # only one view -> NaN
    Xt, err = triangulate_points(cams, obs, vis)
    assert np.isnan(Xt[5]).all()
    ok = ~np.isnan(Xt[:, 0])
    assert np.sqrt(np.mean(np.sum((Xt[ok] - X[ok]) ** 2, 1))) < 1.0
    assert np.nanmax(err) < 1.5
