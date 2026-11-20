import numpy as np

from face3d.fit import ContourView, Template, fit_silhouettes, fit_template_to_landmarks, silhouette_vertices
from face3d.geometry import Camera, look_at
from face3d.mesh import Mesh, uv_sphere

rng = np.random.default_rng(3)


def _bumped(V, center, amp, width):
    d = np.linalg.norm(V - center, axis=1)
    n = V / np.linalg.norm(V, axis=1, keepdims=True)
    return V + n * (amp * np.exp(-(d / width) ** 2))[:, None]


def _profile_cam(dist=700.0, f=4000.0):
    R, t = look_at(np.array([dist, 0, 0.0]), np.zeros(3))
    return Camera.centered(f, 3000, 3000, R=R, t=t)


def test_silhouette_of_sphere_is_its_rim():
    m = uv_sphere(80.0, 32, 64)
    cam = _profile_cam()
    sil = silhouette_vertices(m.vertices, m.triangles(), cam)
    # Rim of a sphere seen from +x (far away) lies near the x=0 great circle.
    assert len(sil) > 20
    assert np.abs(m.vertices[sil, 0]).max() < 15.0


def test_template_fit_hits_landmarks():
    m = uv_sphere(80.0, 24, 48)
    idx = rng.choice(m.n_vertices, 12, replace=False)
    tpl = Template(m, [f"l{i}" for i in range(12)], idx)
    X = m.vertices[idx] * 1.1 + rng.normal(scale=3.0, size=(12, 3)) + np.array([5, -3, 2.0])
    fit = fit_template_to_landmarks(tpl, X)
    assert fit.landmark_rmse_mm < 0.5


def test_profile_contour_recovers_nose_bump():
    base = uv_sphere(80.0, 40, 80)
    front = np.array([0, 0, 80.0])
    target_V = _bumped(base.vertices, front, 25.0, 18.0)   # a "nose" the template lacks
    cam = _profile_cam()
    target = Mesh(target_V, base.faces)
    sil_t = silhouette_vertices(target.vertices, target.triangles(), cam)
    outline = cam.project(target.vertices[sil_t])
    tip = int(np.argmax(base.vertices[:, 2]))
    before = np.linalg.norm(base.vertices[tip] - target_V[tip])
    V, hist = fit_silhouettes(base, [ContourView(cam, outline)], iterations=12)
    after = np.linalg.norm(V[tip] - target_V[tip])
    assert before > 20
    assert after < 0.25 * before, (before, after)
    assert hist[-1] < 0.3 * hist[0]
