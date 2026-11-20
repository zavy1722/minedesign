import numpy as np
import pytest

from face3d.geometry import (Camera, RBFWarp, apply_similarity, focal_px_from_35mm, look_at,
                             nearest_rotation, rodrigues, rotation_from_euler_deg, rotation_to_rvec,
                             to_blender_camera, umeyama, euler_xyz_deg)
from face3d.synthetic import orbit_camera, synthetic_landmarks

rng = np.random.default_rng(0)


def random_rotation():
    return nearest_rotation(rng.normal(size=(3, 3)))


@pytest.mark.parametrize("theta", [0.0, 1e-7, 0.3, 1.5, 3.0, np.pi - 1e-7])
def test_rodrigues_roundtrip(theta):
    axis = rng.normal(size=3)
    axis /= np.linalg.norm(axis)
    r = axis * theta
    R = rodrigues(r)
    assert np.allclose(R @ R.T, np.eye(3), atol=1e-9)
    assert np.isclose(np.linalg.det(R), 1.0)
    assert np.allclose(rodrigues(rotation_to_rvec(R)), R, atol=1e-6)


def test_euler_roundtrip():
    R = rotation_from_euler_deg(10, -25, 5)
    assert np.allclose(euler_xyz_deg(R), [10, -25, 5], atol=1e-9)


def test_focal_35mm_equivalence():
    # A 3:2 full-frame-shaped image: 35 mm-equivalent 36 mm lens -> f_px == width.
    assert np.isclose(focal_px_from_35mm(36.0, 6000, 4000), 6000.0)


def test_look_at_frontal_camera_orientation():
    # Camera in front of the face (+z), looking at origin: subject's left (+x) must be
    # image right, head top (+y) must be image up (smaller v).
    R, t = look_at(np.array([0, 0, 500.0]), np.zeros(3))
    cam = Camera.centered(1000.0, 1000, 1000, R=R, t=t)
    left, top = cam.project(np.array([[50.0, 0, 0], [0, 50.0, 0]]))
    assert left[0] > 500 and np.isclose(left[1], 500)
    assert top[1] < 500 and np.isclose(top[0], 500)
    assert np.isclose(np.linalg.det(R), 1.0)


def test_to_blender_camera_conventions():
    cam = orbit_camera(600, 30, 10, 50)
    bl = to_blender_camera(cam)
    M = bl["matrix_world"]
    assert np.allclose(M[:3, 3], cam.center)
    # Blender camera looks along its local -z: world direction to the target must match.
    view_dir_world = -M[:3, 2]
    target_dir = np.array([0, 0, 60.0]) - cam.center
    target_dir /= np.linalg.norm(target_dir)
    assert np.allclose(view_dir_world, target_dir, atol=1e-9)
    assert np.isclose(np.linalg.det(M[:3, :3]), 1.0)
    # Lens for a 36 mm sensor reproduces the horizontal FOV.
    assert np.isclose(bl["lens"], cam.f * 36.0 / cam.width)
    # Centred principal point -> no shift; off-centre point -> sign convention.
    assert bl["shift_x"] == 0 and bl["shift_y"] == 0
    cam2 = cam.copy(); cam2.cx -= 100
    assert to_blender_camera(cam2)["shift_x"] > 0


def test_umeyama_recovers_similarity():
    _, X = synthetic_landmarks()
    R = random_rotation(); s = 1.7; t = np.array([10.0, -5.0, 3.0])
    Y = apply_similarity(X, s, R, t)
    s2, R2, t2 = umeyama(X, Y)
    assert np.isclose(s2, s) and np.allclose(R2, R, atol=1e-9) and np.allclose(t2, t, atol=1e-7)


def test_rbf_interpolates_and_preserves_affine():
    _, X = synthetic_landmarks()
    Y = X + rng.normal(scale=3.0, size=X.shape)
    warp = RBFWarp(X, Y)
    assert np.allclose(warp(X), Y, atol=1e-6)
    # Pure affine target: warp must reproduce the affine map everywhere.
    A = np.array([[1.1, 0.1, 0], [0, 0.9, 0.05], [0.02, 0, 1.05]]); b = np.array([1.0, 2.0, 3.0])
    warp_aff = RBFWarp(X, X @ A.T + b)
    P = rng.uniform(-100, 100, size=(200, 3))
    assert np.allclose(warp_aff(P), P @ A.T + b, atol=1e-6)


def test_rbf_smoothing_trades_fit_for_smoothness():
    _, X = synthetic_landmarks()
    Y = X + rng.normal(scale=3.0, size=X.shape)
    exact = RBFWarp(X, Y)
    smooth = RBFWarp(X, Y, smoothing=50.0)
    err_exact = np.abs(exact(X) - Y).max()
    err_smooth = np.abs(smooth(X) - Y).max()
    assert err_smooth > err_exact
