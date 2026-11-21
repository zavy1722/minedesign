"""WP-02: exact point-to-triangle distance, grid broad phase, z-buffer rasteriser, surface metrics."""
import time

import numpy as np
import pytest

from face3d.eval.metrics import (LIKENESS_WEIGHTS, chamfer, likeness_weighted_error, sample_surface,
                                 surface_error)
from face3d.fit.silhouette import silhouette_vertices
from face3d.geometry.camera import Camera, look_at
from face3d.mesh.core import uv_sphere
from face3d.mesh.distance import (TriangleGrid, brute_force_point_to_mesh, closest_point_on_triangle,
                                  mesh_orientation_volume, point_to_mesh)
from face3d.mesh.raster import boundary_pixels, rasterize, render_lambert, render_normals


def _deformed_sphere(n_lat=24, n_lon=48, r=80.0):
    m = uv_sphere(r, n_lat, n_lon)
    V = m.vertices.copy()
    n = V / np.linalg.norm(V, axis=1, keepdims=True)
    V = V * (1.0 + 0.15 * np.sin(3 * n[:, 0]) * np.cos(2 * n[:, 1]) + 0.05 * n[:, 2] ** 3)[:, None]
    return V + np.array([3.0, -7.0, 11.0]), m.triangles()


def _reference_cpt(P, A, B, C):
    """Independent closest point: in-plane projection if inside, else best of the 3 edges."""
    out = np.zeros(len(P))
    for i in range(len(P)):
        p, a, b, c = P[i], A[i], B[i], C[i]
        n = np.cross(b - a, c - a)
        nn = n @ n
        cands = []
        if nn > 0:
            q = p - ((p - a) @ n) / nn * n
            # barycentrics of q by area ratios
            u = np.cross(b - q, c - q) @ n / nn
            v = np.cross(c - q, a - q) @ n / nn
            w = 1 - u - v
            if min(u, v, w) >= 0:
                cands.append(np.sum((p - q) ** 2))
        for s, e in ((a, b), (b, c), (c, a)):
            d = e - s
            t = 0.0 if d @ d == 0 else np.clip((p - s) @ d / (d @ d), 0, 1)
            cands.append(np.sum((p - s - t * d) ** 2))
        out[i] = min(cands)
    return out


# --------------------------------------------------------------------------- distance
def test_point_triangle_matches_brute_force():
    rng = np.random.default_rng(11)
    # single-triangle kernel against an independent construction
    P, A, B, C = (rng.normal(scale=10.0, size=(400, 3)) for _ in range(4))
    Q, d2, bary = closest_point_on_triangle(P, A, B, C)
    assert np.allclose(d2, _reference_cpt(P, A, B, C), rtol=1e-9, atol=1e-9)
    assert np.allclose(Q, bary[:, :1] * A + bary[:, 1:2] * B + bary[:, 2:] * C, atol=1e-9)
    assert np.allclose(bary.sum(1), 1.0, atol=1e-12) and bary.min() >= -1e-12

    V, T = _deformed_sphere()
    lo, hi = V.min(0), V.max(0)
    c = 0.5 * (lo + hi)
    P = np.vstack([c + (rng.uniform(lo, hi, (1000, 3)) - c) * 1.3,                 # in the box, both sides
                   V[rng.integers(0, len(V), 1000)] + rng.normal(scale=4.0, size=(1000, 3))])  # near surface
    assert len(P) == 2000
    d_bf, Q_bf, t_bf, b_bf = brute_force_point_to_mesh(P, V, T)
    d, Q, t, b = point_to_mesh(P, V, T)
    assert np.abs(d - d_bf).max() < 1e-9
    assert np.abs(Q - Q_bf).max() < 1e-9
    g = TriangleGrid(V, T)
    d2_, Q2, t2, b2 = g.query(P)
    assert np.array_equal(d2_, d_bf) and np.array_equal(Q2, Q_bf) and np.array_equal(t2, t_bf)
    # closest points lie on the reported triangle
    tri = V[T[t]]
    assert np.allclose(Q, np.einsum("ij,ijk->ik", b, tri), atol=1e-9)
    # exactness does not depend on the cell size, also for points far outside the grid
    far = rng.uniform(-1500, 1500, (60, 3))
    d_far, Q_far, _, _ = brute_force_point_to_mesh(far, V, T)
    for cell in (2.0, 40.0, 500.0):
        dg, Qg, _, _ = TriangleGrid(V, T, cell=cell).query(np.vstack([far, P[:200]]))
        assert np.abs(dg[:60] - d_far).max() < 1e-9 and np.abs(Qg[:60] - Q_far).max() < 1e-9
        assert np.abs(dg[60:] - d_bf[:200]).max() < 1e-9


def test_degenerate_triangles_handled():
    rng = np.random.default_rng(2)
    P = rng.normal(scale=5.0, size=(500, 3))

    def seg_d2(P, s, e):
        d = e - s
        t = np.clip((P - s) @ d / max(d @ d, 1e-300), 0, 1) if d @ d > 0 else np.zeros(len(P))
        return np.sum((P - s - t[:, None] * d) ** 2, axis=1)

    a, b = np.array([1.0, 2.0, -1.0]), np.array([4.0, -2.0, 3.0])
    cases = {
        "collinear": (a, b, a + 0.37 * (b - a)),
        "collinear_outside": (a, b, a + 1.8 * (b - a)),
        "two_coincident": (a, a.copy(), b),
        "all_coincident": (a, a.copy(), a.copy()),
        "near_zero_area": (a, b, a + 0.5 * (b - a) + np.array([0.0, 0.0, 1e-9])),
    }
    for name, (A, B, C) in cases.items():
        Q, d2, bary = closest_point_on_triangle(P, np.tile(A, (len(P), 1)), np.tile(B, (len(P), 1)),
                                                np.tile(C, (len(P), 1)))
        assert np.all(np.isfinite(Q)) and np.all(np.isfinite(d2)) and np.all(np.isfinite(bary)), name
        ref = np.minimum(np.minimum(seg_d2(P, A, B), seg_d2(P, B, C)), seg_d2(P, C, A))
        assert np.allclose(d2, ref, rtol=1e-9, atol=1e-12), name
        assert np.allclose(bary.sum(1), 1.0) and np.allclose(Q, bary[:, :1] * A + bary[:, 1:2] * B + bary[:, 2:] * C)
    # degenerate faces inside a mesh: grid, brute force and signing stay finite
    V = np.array([[0, 0, 0], [10, 0, 0], [0, 10, 0], [5, 0, 0], [5, 0, 0.0]])
    T = np.array([[0, 1, 2], [0, 3, 1], [3, 4, 1]])
    d, Q, t, _ = point_to_mesh(P, V, T, signed=True)
    d_bf, _, _, _ = brute_force_point_to_mesh(P, V, T)
    assert np.all(np.isfinite(d)) and np.allclose(np.abs(d), d_bf, atol=1e-12)


def test_signed_distance_sign_on_sphere():
    rng = np.random.default_rng(4)
    # convex polyhedron: exact inside/outside labels from the face half-spaces
    m = uv_sphere(80.0, 16, 32)
    V, T = m.vertices, m.triangles()
    assert mesh_orientation_volume(V, T) > 0
    A, B, C = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    n = np.cross(B - A, C - A)
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    # points near vertices, edge midpoints and faces, both sides
    E = 0.5 * (A + B)
    base = np.vstack([V, E, (A + B + C) / 3.0])
    dirs = base / np.linalg.norm(base, axis=1, keepdims=True)
    P = np.vstack([base + dirs * rng.uniform(0.05, 6.0, (len(base), 1)),
                   base - dirs * rng.uniform(0.05, 6.0, (len(base), 1)),
                   rng.uniform(-100, 100, (2000, 3))])
    plane = P @ n.T - np.einsum("fk,fk->f", n, A)[None, :]     # signed plane offsets (M,F)
    inside = plane.max(axis=1) < -1e-9
    outside = plane.max(axis=1) > 1e-9
    d, _, _, _ = point_to_mesh(P, V, T, signed=True)
    assert np.all(d[inside] < 0) and np.all(d[outside] > 0)
    assert inside.sum() > 1000 and outside.sum() > 1000
    Tf = T[:, [0, 2, 1]]
    assert mesh_orientation_volume(V, Tf) < 0
    df, _, _, _ = point_to_mesh(P, V, Tf, signed=True)
    assert np.all(df[inside] > 0) and np.all(df[outside] < 0)
    assert np.allclose(np.abs(df), np.abs(d))

    # non-convex (deformed) sphere: points well inside / outside along radial rays
    Vd, Td = _deformed_sphere(20, 40)
    centre = np.array([3.0, -7.0, 11.0])
    k = rng.integers(0, len(Vd), 800)
    radial = Vd[k] - centre
    Pin = centre + radial * rng.uniform(0.1, 0.85, (800, 1))
    Pout = centre + radial * rng.uniform(1.15, 2.0, (800, 1))
    assert mesh_orientation_volume(Vd, Td) > 0
    din, _, _, _ = point_to_mesh(Pin, Vd, Td, signed=True)
    dout, _, _, _ = point_to_mesh(Pout, Vd, Td, signed=True)
    assert np.all(din < 0) and np.all(dout > 0)
    din_f, _, _, _ = point_to_mesh(Pin, Vd, Td[:, [0, 2, 1]], signed=True)
    assert np.all(din_f > 0)


# --------------------------------------------------------------------------- raster
def _sphere_cam(f=800.0, W=512, H=512, eye=(60.0, 40.0, 400.0)):
    R, t = look_at(np.array(eye), np.zeros(3))
    return Camera.centered(f, W, H, R=R, t=t)


def test_raster_silhouette_matches_silhouette_vertices():
    m = uv_sphere(80.0, 40, 80)
    V, T = m.vertices, m.triangles()
    cam = _sphere_cam()
    res = rasterize(V, T, cam)
    sil = silhouette_vertices(V, T, cam)
    uv = cam.project(V[sil])
    bp = boundary_pixels(res.mask)
    assert len(sil) > 50 and len(bp) > 100
    d = np.sqrt(((uv[:, None, :] - bp[None]) ** 2).sum(-1)).min(1)
    assert d.max() < 1.5
    # back-face culling does not change a closed convex mesh's visible surface
    res_c = rasterize(V, T, cam, cull_backfaces=True)
    assert np.array_equal(res_c.tri_id, res.tri_id) and np.array_equal(res_c.depth, res.depth)
    # depth agrees with the camera depth of the surface point given by tri_id + bary
    rows, cols = np.nonzero(res.mask)
    X = np.einsum("ij,ijk->ik", res.bary[rows, cols], V[T[res.tri_id[rows, cols]]])
    assert np.abs(cam.depth(X) - res.depth[rows, cols]).max() < 1e-9
    # and the surface point projects onto the pixel centre
    assert np.abs(cam.project(X) - np.column_stack([cols + 0.5, rows + 0.5])).max() < 1e-6


def test_raster_depth_exact_on_plane():
    Vq = np.array([[-50.0, -40, 0], [60, -40, 0], [60, 45, 0], [-50, 45, 0]])
    Tq = np.array([[0, 1, 2], [0, 2, 3]])
    cam = Camera.centered(500.0, 64, 48, R=np.eye(3), t=np.array([3.0, -2.0, 300.0]))
    res = rasterize(Vq, Tq, cam)
    assert res.mask.all()                                  # the quad covers the whole image
    assert np.abs(res.depth[res.mask] - 300.0).max() < 1e-9
    assert np.abs(res.bary[res.mask].sum(-1) - 1.0).max() < 1e-9
    assert np.all(res.depth[~res.mask] == np.inf) and np.all(res.tri_id[~res.mask] == -1)
    # a smaller quad: coverage exactly the pixel centres inside its projection
    Vs = np.array([[-10.0, -10, 0], [10, -10, 0], [10, 10, 0], [-10, 10, 0]])
    res = rasterize(Vs, Tq, cam)
    uv = cam.project(Vs)
    jj, ii = np.mgrid[0:48, 0:64]
    expect = ((ii + 0.5 >= uv[:, 0].min()) & (ii + 0.5 <= uv[:, 0].max())
              & (jj + 0.5 >= uv[:, 1].min()) & (jj + 0.5 <= uv[:, 1].max()))
    assert np.array_equal(res.mask, expect)
    # tilted plane: perspective-correct depth equals the ray-plane intersection
    R, t = look_at(np.array([120.0, -60.0, 350.0]), np.array([5.0, 3.0, 0.0]))
    cam2 = Camera.centered(700.0, 160, 120, R=R, t=t)
    res = rasterize(Vq, Tq, cam2)
    rows, cols = np.nonzero(res.mask)
    o, d = cam2.ray(np.column_stack([cols + 0.5, rows + 0.5]))
    s = -o[2] / d[:, 2]
    X = o + s[:, None] * d
    assert res.mask.sum() > 1000
    assert np.abs(cam2.depth(X) - res.depth[rows, cols]).max() < 1e-9
    assert np.abs(res.bary[rows, cols].sum(-1) - 1.0).max() < 1e-9


def test_raster_occlusion():
    cam = Camera.centered(400.0, 120, 100, R=np.eye(3), t=np.zeros(3))
    # tri 0 is far (z=500), tri 1 is near (z=300) and drawn later: depth decides, not order
    V = np.array([[-80.0, -60, 500], [80, -60, 500], [0, 80, 500],
                  [-40.0, -50, 300], [60, -30, 300], [-10, 50, 300]])
    T = np.array([[0, 1, 2], [3, 5, 4]])
    for order in (T, T[::-1]):
        res = rasterize(V, order, cam)
        far_only = rasterize(V, order[order[:, 0] == 0], cam).mask
        near_only = rasterize(V, order[order[:, 0] == 3], cam).mask
        overlap = far_only & near_only
        assert overlap.sum() > 200
        near_id = int(np.flatnonzero(order[:, 0] == 3)[0])
        assert np.all(res.tri_id[overlap] == near_id)
        assert np.allclose(res.depth[overlap], 300.0, atol=1e-9)
        assert np.all(res.depth[far_only & ~near_only] > 499.999)
    # triangles behind the near plane are skipped
    res = rasterize(V, T, cam, near=400.0)
    assert np.all(res.tri_id[res.mask] == 0)
    # equal depth: the lower triangle id wins
    Vt = np.array([[-80.0, -60, 500], [80, -60, 500], [0, 80, 500]])
    res = rasterize(np.vstack([Vt, Vt]), np.array([[3, 4, 5], [0, 1, 2]]), cam)
    assert res.mask.any() and np.all(res.tri_id[res.mask] == 0)


def test_render_normals_lambert_and_boundary():
    m = uv_sphere(80.0, 40, 80)
    V, T = m.vertices, m.triangles()
    cam = _sphere_cam(W=200, H=160, f=320.0)
    res = rasterize(V, T, cam)
    N = render_normals(res, V, T)
    rows, cols = np.nonzero(res.mask)
    X = np.einsum("ij,ijk->ik", res.bary[rows, cols], V[T[res.tri_id[rows, cols]]])
    cosang = np.einsum("ij,ij->i", N[rows, cols], X / np.linalg.norm(X, axis=1, keepdims=True))
    assert cosang.min() > np.cos(np.radians(2.0))
    assert np.all(N[~res.mask] == 0)
    img = render_lambert(res, V, T, cam)
    assert img.dtype == np.float32 and img.shape == (160, 200, 3)
    assert img.min() >= 0 and img.max() <= 1 and np.all(img[~res.mask] == 0)
    assert img[res.mask].min() >= 0.25 - 1e-6           # ambient floor with white albedo
    # brightest where the normal faces the light
    L = -np.array([0.3, -0.5, -0.8]) / np.linalg.norm([0.3, -0.5, -0.8])
    lam = np.clip(N[rows, cols] @ L, 0, None)
    assert np.allclose(img[rows, cols, 0], 0.25 + 0.75 * lam, atol=1e-5)
    alb = np.tile([0.8, 0.5, 0.4], (len(V), 1))
    img2 = render_lambert(res, V, T, cam, albedo=alb)
    assert np.allclose(img2[rows, cols], img[rows, cols] * np.array([0.8, 0.5, 0.4]), atol=1e-5)
    # boundary pixels of a rectangle are its outline
    mask = np.zeros((10, 12), bool)
    mask[2:7, 3:9] = True
    bp = boundary_pixels(mask)
    assert len(bp) == 2 * 6 + 2 * 3
    assert np.all((bp[:, 0] == 3.5) | (bp[:, 0] == 8.5) | (bp[:, 1] == 2.5) | (bp[:, 1] == 6.5))
    full = np.ones((3, 4), bool)
    assert len(boundary_pixels(full)) == 3 * 4 - 2     # image border counts as outside


# --------------------------------------------------------------------------- metrics
def test_surface_error_known_offset():
    a = uv_sphere(80.0, 30, 60)
    b = uv_sphere(81.0, 30, 60)
    Va, T = a.vertices, a.triangles()
    Vb = b.vertices
    for sample in ("vertices", "area"):
        same = surface_error(Va, T, Va, T, sample=sample, n_samples=3000, signed=True)
        assert same["median"] < 1e-9 and same["rms"] < 1e-9 and same["f_at"][0.5] == 1.0
        for direction in ("ref_to_est", "est_to_ref", "symmetric"):
            # estimate r=80 inside reference r=81: bias negative (estimate too small)
            r = surface_error(Va, T, Vb, T, direction=direction, sample=sample, n_samples=4000,
                              rng=np.random.default_rng(1), signed=True)
            assert abs(r["median"] - 1.0) < 0.02, (sample, direction, r["median"])
            assert r["signed_bias"] < -0.95
            assert r["f_at"][0.5] == 0.0 and r["f_at"][2.0] == 1.0
            r2 = surface_error(Vb, T, Va, T, direction=direction, sample=sample, n_samples=4000, signed=True)
            assert abs(r2["median"] - 1.0) < 0.02 and r2["signed_bias"] > 0.95
    # unsigned call reports NaN bias; regions on the sampled (reference) mesh
    upper = np.flatnonzero(Vb[:, 1] > 0)
    r = surface_error(Va, T, Vb, T, regions={"upper": upper, "empty": []})
    assert np.isnan(r["signed_bias"])
    assert r["per_region"]["upper"]["n"] == len(upper)
    assert abs(r["per_region"]["upper"]["median"] - 1.0) < 0.02
    assert r["per_region"]["empty"]["n"] == 0 and np.isnan(r["per_region"]["empty"]["rms"])
    # area sampling is deterministic for a given seed
    r1 = surface_error(Va, T, Vb, T, sample="area", n_samples=2000, rng=7)
    r2 = surface_error(Va, T, Vb, T, sample="area", n_samples=2000, rng=7)
    assert r1["mean"] == r2["mean"]


def test_chamfer_sampling_and_likeness():
    a = uv_sphere(80.0, 30, 60)
    b = uv_sphere(81.0, 30, 60)
    cd = chamfer(a.vertices, a.triangles(), b.vertices, b.triangles(), n_samples=3000)
    assert abs(cd - 1.0) < 0.02
    assert chamfer(a.vertices, a.triangles(), a.vertices, a.triangles(), n_samples=500) < 1e-9
    # area-uniform sampling: about half of the samples on the upper hemisphere
    pts, t, bary = sample_surface(a.vertices, a.triangles(), 20000, rng=3)
    assert abs(np.mean(pts[:, 1] > 0) - 0.5) < 0.02
    assert np.all(np.linalg.norm(pts, axis=1) <= 80.0 + 1e-9)      # on the inscribed polyhedron
    assert np.all(np.linalg.norm(pts, axis=1) > 79.5)
    assert bary.min() >= 0 and np.allclose(bary.sum(1), 1.0)
    # likeness-weighted error
    e = likeness_weighted_error({"eyes": 1.0, "jaw": 2.0, "unknown": 50.0, "ears": float("nan")})
    assert np.isclose(e, (1.0 * 1.0 + 0.5 * 2.0) / 1.5)
    assert np.isclose(likeness_weighted_error({"a": 1.0, "b": 3.0}, {"a": 1.0, "b": 1.0}), 2.0)
    assert np.isclose(likeness_weighted_error({"eyes": {"rms": 2.0, "n": 5}}), 2.0)
    assert np.isnan(likeness_weighted_error({}))
    assert LIKENESS_WEIGHTS["eyes"] == 1.0 and LIKENESS_WEIGHTS["neck"] == 0.05


def test_raster_speed():
    m = uv_sphere(80.0, 100, 101)
    V, T = m.vertices, m.triangles()
    assert len(T) >= 19998
    cam = _sphere_cam()
    t0 = time.perf_counter()
    res = rasterize(V, T, cam)
    assert time.perf_counter() - t0 < 10.0
    assert res.mask.sum() > 50000
    rng = np.random.default_rng(0)
    P = V[rng.integers(0, len(V), 10000)] + rng.normal(scale=3.0, size=(10000, 3))
    t0 = time.perf_counter()
    d, _, _, _ = point_to_mesh(P, V, T)
    assert time.perf_counter() - t0 < 5.0
    assert np.all(np.isfinite(d))
