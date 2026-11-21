"""WP-17: contours v2 (DESIGN D-13, 4.15 stage D, 4.16, SIL-3).

ContourObs and residual kinds, the sub-vertex rim, the exact Felzenszwalb-Huttenlocher
distance transform, grid matching with the normal gate, Viterbi edge snap, the
LinearBasis shape model with the similarity projector, the contour Term inside the
bundle (free cameras), the focal/distance diagnosis and the legacy ``use_subvertex``
path of ``fit_silhouettes``.
"""
import dataclasses
import math
import time

import numpy as np
import pytest

import face3d.solve.bundle as B
from face3d.fit import ContourView, fit_silhouettes, silhouette_vertices
from face3d.fit.contour import (FINDING_FOCAL_DIST, ContourDistance, ContourObs, ContourTerm,
                                _pad_view, backward_residuals, contour_stage, densify_rim, diagnose_focal_distance,
                                effective_sample_weights, forward_residuals, grid_nearest, match, rim_points,
                                scale_camera, sigma_n_model, vertex_normals)
from face3d.fit.distance_transform import edt_squared, edt_with_nearest, gradient, sample_bilinear
from face3d.fit.edge_snap import edge_snap
from face3d.geometry.camera import Camera, look_at
from face3d.geometry.procrustes import apply_similarity, umeyama
from face3d.geometry.rbf import RBFWarp
from face3d.mesh import Mesh, uv_sphere
from face3d.mesh.distance import point_to_mesh
from face3d.mesh.raster import rasterize
from face3d.mesh.reduced import ReducedDeformer, coef_matrix, similarity_tangent_cm
from face3d.model.landmark_prior import FactorPrior
from face3d.model.procedural_head import build_procedural_head
from face3d.solve.bundle import ViewObs, bundle_adjust
from face3d.solve.shape_models import BasisPrior, LinearBasis, extremal_landmark
from face3d.solve.terms import ShapeModel, Term
from face3d.testbed.render import landmark_visibility
from face3d.testbed.surface_subjects import out_of_prior_subject


# =========================================================================== fixtures
@pytest.fixture(scope="module")
def kit():
    return build_procedural_head()


def _look(C, target=(0.0, 0.0, 0.0), f=2000.0, W=1000, H=1000):
    R, t = look_at(np.asarray(C, float), np.asarray(target, float))
    return Camera.centered(f, W, H, R=R, t=t)


# =========================================================================== distance transform
def _brute_d2(mask):
    H, W = mask.shape
    r, c = np.nonzero(mask)
    if len(r) == 0:
        return np.full((H, W), np.inf)
    rr, cc = np.mgrid[0:H, 0:W]
    d2 = (rr[..., None] - r) ** 2 + (cc[..., None] - c) ** 2
    return d2.min(axis=-1).astype(float)


def test_edt_matches_brute_force():
    rng = np.random.default_rng(0)
    masks = [rng.random((64, 80)) < p for p in (0.002, 0.01, 0.05, 0.3, 0.9)]
    one = np.zeros((64, 80), bool)
    one[17, 63] = True
    masks += [one, np.zeros((64, 80), bool), np.ones((64, 80), bool)]
    edge = np.zeros((64, 80), bool)
    edge[:, 0] = True
    masks.append(edge)
    for m in masks:
        ref = _brute_d2(m)
        d2 = edt_squared(m)
        assert np.array_equal(d2, ref)                        # exactly equal (integers in float64)
        d2n, near = edt_with_nearest(m)
        assert np.array_equal(d2n, ref)
        if m.any():
            rr, cc = np.mgrid[0:64, 0:80]
            assert m[near[..., 0], near[..., 1]].all()
            dd = (rr - near[..., 0]) ** 2 + (cc - near[..., 1]) ** 2
            assert np.array_equal(dd.astype(float), ref)
        else:
            assert np.isinf(d2).all() and (near == -1).all()


def test_sample_bilinear_pixel_centres_and_gradient():
    img = np.arange(12, dtype=float).reshape(3, 4) ** 1.5
    # pixel [r, c] at (c + 0.5, r + 0.5)
    uv = np.array([[c + 0.5, r + 0.5] for r in range(3) for c in range(4)])
    assert np.allclose(sample_bilinear(img, uv), img.ravel())
    # exact derivative of the interpolant (inside a cell, away from the centres)
    p = np.array([[1.3, 1.7]])
    v, g = sample_bilinear(img, p, return_grad=True)
    h = 1e-6
    gu = (sample_bilinear(img, p + [h, 0]) - sample_bilinear(img, p - [h, 0])) / (2 * h)
    gv = (sample_bilinear(img, p + [0, h]) - sample_bilinear(img, p - [0, h])) / (2 * h)
    assert np.allclose(g[0], [gu[0], gv[0]], rtol=1e-6)
    assert np.isnan(sample_bilinear(img, np.array([[np.nan, 1.0]]))[0])
    assert sample_bilinear(img, np.array([[-3.0, 1.0]]), fill=7.0)[0] == 7.0
    gu2, gv2 = gradient(img)
    assert np.allclose(gu2, np.gradient(img, axis=1)) and np.allclose(gv2, np.gradient(img, axis=0))


# =========================================================================== sub-vertex rim
def test_subvertex_rim_on_sphere():
    """uv_sphere(80, 24, 48) seen from (700, 100, 50): with the surface's own (radial) normals the
    sub-vertex rim lies within 0.05 mm (geodesic) of the true rim; silhouette vertices >= 1 mm off."""
    r = 80.0
    m = uv_sphere(r, 24, 48)
    V, T = m.vertices, m.triangles()
    C = np.array([700.0, 100.0, 50.0])
    cam = _look(C)
    d = np.linalg.norm(C)
    rim_ang = math.acos(r / d)

    def geodesic(P):
        ang = np.arccos(np.clip(P @ C / (np.linalg.norm(P, axis=1) * d), -1.0, 1.0))
        return r * np.abs(ang - rim_ang)

    normals = V / np.linalg.norm(V, axis=1, keepdims=True)
    ras = rasterize(V, T, cam, cull_backfaces=True)
    rim = rim_points(V, T, normals, cam, ras)
    assert len(rim) > 40 and rim.visible.all()
    assert geodesic(rim.p).max() < 0.05
    # t in [0, 1], p on the edge, normal2d unit and pointing away from the sphere's image centre
    assert np.all((rim.t >= 0) & (rim.t <= 1))
    e = rim.edge
    assert np.allclose(rim.p, V[e[:, 0]] + rim.t[:, None] * (V[e[:, 1]] - V[e[:, 0]]))
    assert np.allclose(np.linalg.norm(rim.normal2d, axis=1), 1.0)
    c_img = cam.project(np.zeros((1, 3)))[0]
    assert np.all(np.sum(rim.normal2d * (rim.uv - c_img), axis=1) > 0)
    # the rim polyline is one closed loop (every point has two segment neighbours)
    assert np.all(np.bincount(rim.segments.ravel(), minlength=len(rim)) == 2)
    smp = densify_rim(rim, cam, 2.0, ras)
    assert len(smp) > len(rim) and geodesic(smp.p).max() < 0.05
    assert np.allclose(smp.w.sum(axis=1), 1.0)
    assert np.allclose(np.einsum("nk,nkd->nd", smp.w, V[smp.vid]), smp.p)
    # vertex-level silhouette: half-edge bias
    sil = silhouette_vertices(V, T, cam)
    assert geodesic(V[sil]).max() >= 1.0


def test_rim_visibility_occluded_by_raster():
    """A small sphere hidden behind a big one: its rim is invisible in the raster test."""
    big = uv_sphere(80.0, 24, 48)
    small = uv_sphere(20.0, 12, 24)
    Vs = small.vertices + np.array([0.0, 0.0, -150.0])
    V = np.vstack([big.vertices, Vs])
    T = np.vstack([big.triangles(), small.triangles() + len(big.vertices)])
    cam = _look((0.0, 0.0, 800.0))
    ras = rasterize(V, T, cam, cull_backfaces=True)
    rim = rim_points(V, T, vertex_normals(V, T), cam, ras)
    on_small = rim.edge[:, 0] >= len(big.vertices)
    assert on_small.any() and not rim.visible[on_small].any()
    assert rim.visible[~on_small].mean() > 0.95


# =========================================================================== residual kinds, matching
def _line_obs(kind, margin=0.0, n=(0.0, -1.0)):
    xs = np.linspace(100, 200, 11)
    xy = np.column_stack([xs, np.full_like(xs, 300.0)])
    return ContourObs(0, xy, np.tile(n, (len(xs), 1)), 0.5, kind, margin_px=margin)


def test_outer_bound_one_sided():
    obs = _line_obs("outer_bound", margin=1.0)      # outward normal = -v (up in the image)
    pairs = np.column_stack([np.arange(11), np.arange(11)])
    inside = obs.xy + [0.0, 2.0]                     # below the line: inside the bound
    assert np.all(forward_residuals(obs, pairs, inside) == 0.0)
    within_margin = obs.xy + [0.0, -0.4]             # outside by 0.4 px < margin 1 px
    assert np.all(forward_residuals(obs, pairs, within_margin) == 0.0)
    outside = obs.xy + [0.0, -3.0]
    r = forward_residuals(obs, pairs, outside)
    assert np.allclose(r, (3.0 - 1.0) / 0.5)
    hard = dataclasses.replace(obs, kind="hard")
    assert np.allclose(forward_residuals(hard, pairs, inside), -4.0)
    inner = dataclasses.replace(obs, kind="inner_bound", margin_px=0.0)
    assert np.allclose(forward_residuals(inner, pairs, inside), 4.0)
    assert np.all(forward_residuals(inner, pairs, outside) == 0.0)
    # never pulls inward: the cost gradient w.r.t. the rim position vanishes inside the bound
    # and, outside, points outward (so a descent step moves the rim inward, back under the bound)
    for pos, zero in ((inside, True), (outside, False)):
        h = 1e-6
        c0 = 0.5 * np.sum(forward_residuals(obs, pairs, pos) ** 2)
        dv = (0.5 * np.sum(forward_residuals(obs, pairs, pos + [0, h]) ** 2) - c0) / h
        if zero:
            assert dv == 0.0
        else:
            assert dv < 0.0          # cost decreases when moving +v, i.e. inward (the outward normal is -v)


def test_normal_gate_rejects_mismatch():
    obs = ContourObs(0, [[50.0, 50.0]], [[1.0, 0.0]], 1.0)
    for deg, expect in ((60.0, 0), (30.0, 1)):
        a = math.radians(deg)
        rim_uv = np.array([[51.0, 50.5]])
        rim_n = np.array([[math.cos(a), math.sin(a)]])
        pairs = match(obs, rim_uv, rim_n, gate_px=5.0)
        assert len(pairs) == expect, (deg, pairs)
    # the nearest compatible candidate wins over a nearer mismatched one
    rim_uv = np.array([[50.5, 50.0], [52.0, 50.0]])
    rim_n = np.array([[0.0, 1.0], [1.0, 0.0]])
    assert match(obs, rim_uv, rim_n, 5.0).tolist() == [[0, 1]]
    # beyond the gate: no pair
    assert len(match(obs, np.array([[60.0, 50.0]]), np.array([[1.0, 0.0]]), 5.0)) == 0


def test_grid_nearest_equals_brute_force():
    rng = np.random.default_rng(3)
    Q = rng.uniform(0, 300, size=(400, 2))
    R = rng.uniform(0, 300, size=(250, 2))
    for gate in (3.0, 11.0, 40.0):
        pairs = grid_nearest(Q, R, gate)
        d = np.linalg.norm(Q[:, None] - R[None], axis=2)
        best = np.argmin(d, axis=1)
        ok = d[np.arange(len(Q)), best] <= gate
        assert pairs[:, 0].tolist() == np.flatnonzero(ok).tolist()
        assert np.array_equal(pairs[:, 1], best[ok])


def test_backward_residuals_and_noise_helpers():
    xs = np.arange(20.0, 80.0, 1.0)
    xy = np.column_stack([xs, np.full_like(xs, 40.5)])
    nrm = np.tile([0.0, -1.0], (len(xs), 1))
    dist = ContourDistance(xy, nrm, pad=20)
    uv = np.array([[50.2, 41.5], [50.2, 39.0], [50.2, 30.0]])
    r = backward_residuals(dist, uv, sigma_px=1.0, trunc=3.0, weight=0.5)
    assert np.allclose(r, math.sqrt(0.5) * np.array([1.0, 1.5, 3.0]))
    # the raw EDT field of a full image (bilinear sqrt-EDT)
    mask = np.zeros((80, 100), bool)
    mask[40, 20:80] = True
    field = np.sqrt(edt_squared(mask))
    r2 = backward_residuals(field, np.array([[50.5, 43.5]]), sigma_px=1.0, trunc=3.0, weight=1.0)
    assert np.isclose(r2[0], 3.0)
    assert sigma_n_model(0.5, 0.0, 0.0, 10.0) == 0.5
    assert sigma_n_model(0.0, 0.0, 0.0, 400.0) == pytest.approx(2.0)          # 0.005 IOD floor
    assert sigma_n_model(0.3, 2.0, 0.4, 0.0) == pytest.approx(math.sqrt(0.09 + 1.0 + 0.16))
    assert effective_sample_weights(10) == 1.0 and effective_sample_weights(400) == pytest.approx(0.1)


def test_contour_obs_from_polyline_and_mask():
    th = np.linspace(0, 2 * np.pi, 60, endpoint=False)
    circ = np.column_stack([100 + 30 * np.cos(th), 80 + 30 * np.sin(th)])
    ob = ContourObs.from_polyline(circ, True, (100.0, 80.0), 0.7, view=2)
    radial = (circ - [100.0, 80.0]) / 30.0
    assert ob.view == 2 and np.all(np.sum(ob.normal_out * radial, axis=1) > 0.99)
    with pytest.raises(ValueError):
        ContourObs(0, circ, np.zeros_like(circ), 1.0)
    with pytest.raises(ValueError):
        ContourObs(0, circ, radial, 1.0, kind="soft")
    # a rasterised disc: sub-pixel samples on the circle, normals radial
    H, W = 120, 160
    rr, cc = np.mgrid[0:H, 0:W]
    mask = (cc + 0.5 - 70.3) ** 2 + (rr + 0.5 - 60.8) ** 2 <= 35.0 ** 2
    mo = ContourObs.from_mask(mask, view=1)
    rad = np.linalg.norm(mo.xy - [70.3, 60.8], axis=1)
    assert np.abs(rad - 35.0).max() < 0.75 and abs(np.mean(rad) - 35.0) < 0.2
    u = (mo.xy - [70.3, 60.8]) / rad[:, None]
    assert np.degrees(np.arccos(np.clip(np.sum(u * mo.normal_out, axis=1), -1, 1))).max() < 15.0
    assert np.allclose(mo.sigma_n_px, math.sqrt(1.0 / 12.0 + 0.25))
    # ordered: consecutive samples are neighbours
    steps = np.linalg.norm(np.diff(mo.xy, axis=0), axis=1)
    assert np.median(steps) < 1.6


# =========================================================================== edge snap
def test_edge_snap_recovers_edge():
    H, W = 200, 400
    iod = 120.0                                        # px: L = ceil(0.03 * 120) = 4
    rr, cc = np.mgrid[0:H, 0:W]

    def y_edge(u):
        return 100.0 + 12.0 * np.sin(2 * np.pi * u / 160.0)

    yy = rr + 0.5
    uu = cc + 0.5
    img = np.where(yy > y_edge(uu), 0.8, 0.2)
    # Gaussian blur (sigma 1.5 px) of the step, analytically along v: 0.2 + 0.6 Phi((v - y) / s)
    s = 1.5
    img = 0.2 + 0.6 * 0.5 * (1.0 + np.vectorize(math.erf)((yy - y_edge(uu)) / (s * math.sqrt(2.0))))
    img = img + np.random.default_rng(4).normal(scale=0.01, size=img.shape)
    xs = np.linspace(30.0, 370.0, 9)
    offs = np.array([3.0, -2.0, 1.0, -3.0, 2.5, -1.5, 3.0, -2.5, 0.5])   # up to 3 px = 2.5 % IOD
    coarse = np.column_stack([xs, y_edge(xs) + offs])
    res = edge_snap(img, coarse, iod)
    dv = res.points[:, 1] - y_edge(res.points[:, 0])
    assert np.sqrt(np.mean(dv ** 2)) < 1.0, np.sqrt(np.mean(dv ** 2))
    assert np.all(res.sigma_n_px >= 1.0)
    assert res.points.shape == res.normals.shape and len(res.offsets) == len(res.points)
    res2 = edge_snap(img.copy(), coarse.copy(), iod)
    assert np.array_equal(res.points, res2.points) and res.cost == res2.cost       # deterministic
    # the snapped curve is much closer to the edge than the coarse polyline was
    assert np.sqrt(np.mean(dv ** 2)) < 0.5 * np.sqrt(np.mean(offs ** 2))
    # closed curve: a blurred disc
    disc = np.where((uu - 200) ** 2 + (yy - 100) ** 2 <= 60.0 ** 2, 0.9, 0.1)
    th = np.linspace(0, 2 * np.pi, 12, endpoint=False)
    coarse_c = np.column_stack([200 + 62.5 * np.cos(th), 100 + 62.5 * np.sin(th)])
    rc = edge_snap(disc, coarse_c, iod, closed=True)
    rad = np.linalg.norm(rc.points - [200.0, 100.0], axis=1)
    assert np.sqrt(np.mean((rad - 60.0) ** 2)) < 1.0


# =========================================================================== projector, basis
def test_projector_removes_similarity(kit):
    D = ReducedDeformer(kit.vertices, n_centers=120)
    lb = LinearBasis(kit, D)
    rng = np.random.default_rng(5)
    Pa = D.V[lb.anchor_rows]
    G = similarity_tangent_cm(Pa)
    Phi = D.basis_rows(lb.anchor_rows)
    for _ in range(5):
        c = lb.Pi @ rng.normal(size=lb.n_params)
        da = (Phi @ coef_matrix(c, lb.K)).T.reshape(-1)          # coordinate-major anchor displacement
        assert np.linalg.norm(G.T @ da) < 1e-9 * np.linalg.norm(da)
    assert np.allclose(lb.Pi, lb.Pi.T) and np.allclose(lb.Pi @ lb.Pi, lb.Pi, atol=1e-10)
    assert np.linalg.matrix_rank(lb.Pi, tol=1e-8) == lb.n_params - 7
    # without the projector the coefficients can express a similarity of the anchors
    raw = LinearBasis(kit, D, projector=False)
    c = rng.normal(size=raw.n_params)
    da = (Phi @ coef_matrix(c, raw.K)).T.reshape(-1)
    assert np.linalg.norm(G.T @ da) > 1e-2 * np.linalg.norm(da)


def test_linear_basis_shape_model(kit):
    D = ReducedDeformer(kit.vertices, n_centers=60)
    lb = LinearBasis(kit, D)
    assert isinstance(lb, ShapeModel) and lb.n_params == 180 and lb.N == 44
    rng = np.random.default_rng(6)
    q = rng.normal(size=lb.n_params)
    X = lb.points(q)
    V = lb.vertices_q(q)
    assert np.allclose(X, kit.landmark_positions("anatomical44", V))
    J = lb.jacobian(q)
    h = 1e-6
    for j in rng.choice(lb.n_params, 8, replace=False):
        e = np.zeros(lb.n_params)
        e[j] = h
        assert np.allclose((lb.points(q + e) - lb.points(q - e)).ravel() / (2 * h), J[:, j], atol=1e-8)
    assert np.allclose(lb.points(lb.init(X)), X, atol=1e-4)            # ridge least squares
    assert np.allclose(lb.init(lb.X_bar), 0.0)
    ex = lb.with_coefficient_rows()
    Xe = ex.points(q)
    assert Xe.shape == (44 + 60, 3) and np.allclose(ex.init(Xe), q)
    assert ex.jacobian(q).shape == (3 * 104, 180) and np.allclose(ex.jacobian(q)[:132], J)
    rows = np.arange(0, kit.n_verts, 7)
    assert np.allclose(lb.vertices(lb.coefficients(q), rows), V[rows])
    pr = BasisPrior(ex)
    assert isinstance(pr, Term) and pr.is_prior


def test_extremal_softmax_jacobian_numeric(kit):
    rng = np.random.default_rng(7)
    P = rng.normal(scale=5.0, size=(25, 3)) + [0.0, -60.0, 90.0]
    d = np.array([0.1, -0.4, 1.0])
    X, w, J = extremal_landmark(P, d, T=1.5)
    assert np.isclose(w.sum(), 1.0) and np.allclose(X, w @ P)
    h = 1e-6
    for k in (0, 3, int(np.argmax(w))):
        for a in range(3):
            Pp, Pm = P.copy(), P.copy()
            Pp[k, a] += h
            Pm[k, a] -= h
            num = (extremal_landmark(Pp, d, 1.5)[0] - extremal_landmark(Pm, d, 1.5)[0]) / (2 * h)
            assert np.allclose(J[k][:, a], num, atol=1e-7)
    # low temperature -> argmax; and the Jacobian with respect to the basis parameters
    Xc, _, _ = extremal_landmark(P, d, T=1e-3)
    assert np.allclose(Xc, P[np.argmax(P @ (d / np.linalg.norm(d)))])
    lb = LinearBasis(kit, ReducedDeformer(kit.vertices, n_centers=40))
    rows = np.flatnonzero(kit.vertices[:, 1] < -60)
    q = rng.normal(scale=0.5, size=lb.n_params)
    Xq, dX = lb.extremal_point(q, rows, (0.0, -1.0, 0.3))
    for j in rng.choice(lb.n_params, 6, replace=False):
        e = np.zeros(lb.n_params)
        e[j] = h
        num = (lb.extremal_point(q + e, rows, (0.0, -1.0, 0.3))[0]
               - lb.extremal_point(q - e, rows, (0.0, -1.0, 0.3))[0]) / (2 * h)
        assert np.allclose(dX[:, j], num, atol=1e-7)


# =========================================================================== legacy silhouette path
def _bumped(V, center, amp, width):
    d = np.linalg.norm(V - center, axis=1)
    n = V / np.linalg.norm(V, axis=1, keepdims=True)
    return V + n * (amp * np.exp(-(d / width) ** 2))[:, None]


def test_profile_contour_recovers_nose_bump_subvertex():
    """tests/test_fit.py::test_profile_contour_recovers_nose_bump with use_subvertex=True."""
    base = uv_sphere(80.0, 40, 80)
    target_V = _bumped(base.vertices, np.array([0, 0, 80.0]), 25.0, 18.0)
    R, t = look_at(np.array([700.0, 0, 0.0]), np.zeros(3))
    cam = Camera.centered(4000.0, 3000, 3000, R=R, t=t)
    target = Mesh(target_V, base.faces)
    sil_t = silhouette_vertices(target.vertices, target.triangles(), cam)
    outline = cam.project(target.vertices[sil_t])
    tip = int(np.argmax(base.vertices[:, 2]))
    before = np.linalg.norm(base.vertices[tip] - target_V[tip])
    V, hist = fit_silhouettes(base, [ContourView(cam, outline)], iterations=12, use_subvertex=True)
    after = np.linalg.norm(V[tip] - target_V[tip])
    assert before > 20
    assert after < 0.25 * before, (before, after)
    assert hist[-1] < 0.3 * hist[0]


def _rim_loop(rim):
    """Rim point indices in order around the (single, closed) rim loop."""
    nb = {i: [] for i in range(len(rim))}
    for a, b in rim.segments:
        nb[int(a)].append(int(b))
        nb[int(b)].append(int(a))
    order, prev = [0], -1
    while True:
        nxt = [x for x in nb[order[-1]] if x != prev]
        if not nxt or nxt[0] == order[0]:
            return np.array(order)
        prev = order[-1]
        order.append(nxt[0])


def test_no_tangential_drift_subvertex():
    """tests/test_m1_fixes.py::test_no_tangential_drift with use_subvertex=True. The outline is the
    mesh's own sub-vertex rim polyline (upper half), sampled in one-sided clusters 1-4 px after
    anchors every 20 px of arc length: normal-only sub-vertex targets leave the mesh in place, the
    full correction drags rim vertices along the contour."""
    m = uv_sphere(80, 40, 80)
    dist = 20000.0
    R, t = look_at(np.array([dist, 0, 0.0]), np.zeros(3))
    cam = Camera.centered(4000.0 * dist / 700.0, 3000, 3000, R=R, t=t)
    V = m.vertices
    rim = rim_points(V, m.triangles(), m.vertex_normals(), cam)
    order = _rim_loop(rim)
    assert len(order) == len(rim)
    P = np.vstack([rim.uv[order], rim.uv[order[:1]]])
    Y = np.r_[rim.p[order, 1], rim.p[order[0], 1]]
    arc = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    pts = []
    for a in np.arange(0.0, arc[-1], 20.0):
        for d in (1.0, 2.0, 3.0, 4.0):
            if np.interp(a + d, arc, Y) > 0:
                pts.append((np.interp(a + d, arc, P[:, 0]), np.interp(a + d, arc, P[:, 1])))
    outline = np.array(pts)
    assert len(outline) > 100
    Vn, hist_n = fit_silhouettes(m, [ContourView(cam, outline)], iterations=8, normal_only=True,
                                 use_subvertex=True)
    move_n = np.linalg.norm(Vn - V, axis=1).max()
    assert move_n <= 0.05, move_n
    assert max(hist_n) < 0.05
    Vl, _ = fit_silhouettes(m, [ContourView(cam, outline)], iterations=8, normal_only=False, use_subvertex=True)
    move_l = np.linalg.norm(Vl - V, axis=1).max()
    assert move_l > 0.2 and move_l > 10 * move_n, (move_l, move_n)


def test_fit_silhouettes_defaults_unchanged():
    import inspect
    sig = inspect.signature(fit_silhouettes)
    assert sig.parameters["use_subvertex"].default is False
    assert sig.parameters["normal_only"].default is True


# =========================================================================== the Term in the bundle
def _capture(monkeypatch, *args, **kwargs):
    """bundle_adjust with a zero-iteration LM shim; returns the closures of the last LM call."""
    cap = {}
    orig = B.levenberg_marquardt

    def shim(fun, x0, jac=None, retract=None, **kw):
        cap.update(fun=fun, jac=jac, retract=retract, x0=x0)
        return orig(fun, x0, jac=jac, retract=retract, max_iter=0)
    monkeypatch.setattr(B, "levenberg_marquardt", shim)
    res = B.bundle_adjust(*args, **kwargs)
    monkeypatch.undo()
    return cap, res


def test_contour_term_jacobian_numeric(kit, monkeypatch):
    """Analytic Jacobian of the contour, basis-prior and hold terms through the bundle's chain rule
    (coefficient rows x Pi) and the inverse-depth camera blocks (FREE, FIXED_F and HARD + phi)."""
    rng = np.random.default_rng(8)
    subj = out_of_prior_subject(kit, rng)
    T = kit.triangles()
    lb = LinearBasis(kit, ReducedDeformer(kit.vertices, n_centers=30)).with_coefficient_rows()
    Xt = subj.landmarks()
    views, obs = [], []
    kinds = ("hard", "hard", "outer_bound", "inner_bound")
    for k, yaw in enumerate((0.0, 90.0, -45.0, 30.0)):
        # pitched 8 deg: a level camera's rotation is exactly pi, where the bundle's rotation-vector
        # retraction (rotation_to_rvec) is ill-conditioned for finite differences
        c = _cam(yaw, 1000.0, 85.0, 300, 400, pitch_deg=8.0)
        uv = c.project(Xt) + rng.normal(scale=1.0, size=(len(Xt), 2))
        c0 = c.copy()
        c0.t = c0.t + rng.normal(scale=1.0, size=3)
        kw = [dict(), dict(estimate_focal=False), dict(focal_group="g"), dict(focal_group="g")][k]
        views.append(ViewObs(uv, c0, f_prior=c.f, f_prior_log_sigma=0.05, sigma_px=1.5, **kw))
        o = ContourObs.from_mask(rasterize(subj.V_true, T, c, cull_backfaces=True).mask, view=k)
        obs.append(dataclasses.replace(o, kind=kinds[k], margin_px=0.5 if k == 2 else 0.0))
    iod = {k: 40.0 for k in range(4)}
    term = ContourTerm(obs, lb, iod, n_outer=3, max_rows_per_view=25, phi_keys={2: "phi_0", 3: "phi_0"})
    assert isinstance(term, Term)
    q = rng.normal(scale=0.5, size=lb.n_params)
    V = lb.vertices_q(q)
    term.update(V, [v.camera for v in views], 0,
                {k: rasterize(V, T, scale_camera(views[k].camera, 0.5), cull_backfaces=True) for k in range(4)})
    assert {b.kind for b in term._blocks} >= {"hard", "backward", "outer_bound", "inner_bound"}
    from face3d.fit.contour import _LandmarkHold
    hold = _LandmarkHold(lb.points(q)[:lb.N] + 0.1, 0.25, lb.n_points)
    pv = [_pad_view(v, lb.K) for v in views]
    cap, res = _capture(monkeypatch, pv, lb.points(q), None, scale=None, shape_model=lb,
                        terms=[term, BasisPrior(lb), hold], huber_px=None)
    x0 = cap["x0"]
    Ja = cap["jac"](x0)
    r0 = cap["fun"](x0)

    def central(h):
        Jn = np.zeros((len(r0), len(x0)))
        for j in range(len(x0)):
            e = np.zeros(len(x0))
            e[j] = h
            Jn[:, j] = (cap["fun"](cap["retract"](x0, e)) - cap["fun"](cap["retract"](x0, -e))) / (2 * h)
        return Jn
    Jn = (4.0 * central(5e-4) - central(1e-3)) / 3.0
    # rows on a kink are one-sided there: the backward truncation (|r| = 3 sqrt(w)) and the hinge of
    # the bound kinds (an active bound residual within the finite-difference reach of zero)
    kink = np.zeros(len(r0), bool)
    row = sum(int(np.isfinite(v.uv[:, 0]).sum()) * 2 for v in views)
    for b in term._blocks:
        n = len(b.sw)
        rr = r0[row:row + n]
        if b.kind == "backward":
            kink[row:row + n] = np.isclose(np.abs(rr), term.trunc * b.sw)
        elif b.kind in ("outer_bound", "inner_bound"):
            kink[row:row + n] = (rr > 0) & (rr < 0.05)
        row += n
    ok = ~kink
    err = np.abs(Ja - Jn)[ok]
    scale = np.abs(Jn[ok]).max(axis=1, keepdims=True)
    assert np.all(err <= 1e-4 * np.abs(Jn[ok]) + 1e-6 * scale + 1e-9), float((err / (scale + 1e-12)).max())
    for name in ("cam_0", "cam_1", "cam_2", "cam_3", "phi_0", "points"):
        assert np.abs(Jn[ok][:, res.param_index[name]]).max() > 0, name


# =========================================================================== the contour stage
FACE_IDS = ("g", "n", "prn", "sn", "ls", "sto", "li", "sl", "pg", "gn", "me", "or_L", "or_R", "en_L", "en_R",
            "ex_L", "ex_R", "ps_L", "ps_R", "pi_L", "pi_R", "al_L", "al_R", "ac_L", "ac_R", "ch_L", "ch_R",
            "zy_L", "zy_R")
STAGE_SEEDS = (0, 1, 2, 3, 4)


def _cam(yaw_deg, dist, f35, W, H, target=(0.0, 5.0, 40.0), pitch_deg=0.0):
    """Camera on an orbit around ``target`` (head frame mm), f from the 35 mm-equivalent."""
    y, p = math.radians(yaw_deg), math.radians(pitch_deg)
    tgt = np.asarray(target, float)
    C = tgt + dist * np.array([math.sin(y) * math.cos(p), math.sin(p), math.cos(y) * math.cos(p)])
    R, t = look_at(C, tgt)
    return Camera.centered(f35 / 36.0 * W, W, H, R=R, t=t)


def _scene(kit, seed, yaws, dist, f35, W, H, noise_px=1.0):
    """Out-of-prior WP-11 subject, landmark observations (geometric visibility, N(0, noise^2) px) and
    full-resolution mask contours per view; IOD_px = f IOD_mm / depth of the eye centre."""
    rng = np.random.default_rng(seed)
    subj = out_of_prior_subject(kit, rng)
    T = kit.triangles()
    ids = kit.landmark_names("anatomical44")
    Xt = subj.landmarks()
    E = Xt[[ids.index(n) for n in ("en_L", "en_R", "ex_L", "ex_R")]]
    iod_mm = float(np.linalg.norm(0.5 * (E[0] + E[2]) - 0.5 * (E[1] + E[3])))
    cams, uvs, obs, iod = [], [], [], []
    for k, yaw in enumerate(yaws):
        c = _cam(yaw, dist, f35, W, H)
        vis = landmark_visibility(kit, subj.V_true, "anatomical44", c)
        uv = c.project(Xt) + rng.normal(scale=noise_px, size=(len(Xt), 2))
        uv[~vis] = np.nan
        cams.append(c)
        uvs.append(uv)
        obs.append(ContourObs.from_mask(rasterize(subj.V_true, T, c, cull_backfaces=True).mask, view=k,
                                        source="test_mask"))
        iod.append(c.f * iod_mm / float(c.depth(E.mean(axis=0, keepdims=True))[0]))
    return subj, cams, uvs, obs, iod


def _profile_error(kit, V, X, subj):
    """RMS distance (mm) of the fitted midline vertices near the nose tip (12 mm of prn) and the chin
    (15 mm of pg) to the true surface, after similarity alignment of the fitted face landmarks
    (DESIGN 7.3 'landmark similarity alignment'; the ear and cranial landmarks are left out)."""
    ids = kit.landmark_names("anatomical44")
    fi = [ids.index(n) for n in FACE_IDS]
    s, R, t = umeyama(X[fi], subj.landmarks()[fi])
    Va = apply_similarity(V, s, R, t)
    out = []
    for nm, rad in (("prn", 12.0), ("pg", 15.0)):
        c0 = kit.vertices[kit.landmark_vertices("anatomical44", [nm])[0]]
        sel = kit.midline[np.linalg.norm(kit.vertices[kit.midline] - c0, axis=1) < rad]
        d = point_to_mesh(Va[sel], subj.V_true, kit.triangles())[0]
        out.append(float(np.sqrt(np.mean(d ** 2))))
    return out


@pytest.fixture(scope="module")
def stage_runs(kit):
    """Landmark bundle (factor prior, free focal with a 5 % EXIF prior) then the contour stage with
    free cameras (LinearBasis K = 150, 5 outer iterations) on front + left profile + three-quarter
    views of 5 out-of-prior subjects (85 mm-eq at 1 m, 600 x 800 px, 1 px landmark noise)."""
    prior = FactorPrior.from_package()
    lv = kit.landmark_vertices("anatomical44")
    out = []
    for seed in STAGE_SEEDS:
        subj, cams, uvs, obs, iod = _scene(kit, seed, (0.0, 90.0, -45.0), 1000.0, 85.0, 600, 800)
        views = []
        for c, uv in zip(cams, uvs):
            c0 = c.copy()
            c0.t = c0.t + np.array([3.0, -3.0, 20.0])
            views.append(ViewObs(uv, c0, f_prior=c.f, f_prior_log_sigma=0.05, sigma_px=1.0))
        lm = bundle_adjust(views, prior.mean(), None, prior=prior)
        s, R, t = umeyama(kit.vertices[lv], lm.X)
        V0 = apply_similarity(kit.vertices, s, R, t)
        V0 = RBFWarp(V0[lv], lm.X)(V0)                       # template through the landmark solution
        basis = LinearBasis(kit, ReducedDeformer(V0, n_centers=150))
        sviews = [dataclasses.replace(v, camera=c) for v, c in zip(views, lm.cameras)]
        t0 = time.perf_counter()
        res = contour_stage(basis, sviews, obs, iod, n_outer=5)
        dt = time.perf_counter() - t0
        out.append(dict(seed=seed, res=res, time=dt, before=_profile_error(kit, V0, lm.X, subj),
                        after=_profile_error(kit, res.V, res.X, subj)))
    return out


def test_contour_stage_recovers_profile(stage_runs):
    after = np.array([r["after"] for r in stage_runs])            # (seeds, [nose tip, chin]) mm
    before = np.array([r["before"] for r in stage_runs])
    assert np.median(after.max(axis=1)) <= 1.5, after
    assert np.median(after, axis=0).max() <= 1.5
    assert np.median(after.max(axis=1)) <= np.median(before.max(axis=1)) + 0.1   # the stage does not degrade it
    for r in stage_runs:
        res = r["res"]
        assert res.landmark_shift_mm.max() <= 0.5, (r["seed"], res.landmark_shift_mm.max())
        assert len(res.history) == 5 and res.findings == [] and res.flags == []
        # the silhouettes are fitted: every view ends below 1 sigma_n (median |r|) and the mean
        # wide-gate residual drops by at least half
        fin = [st["wide_median_abs_sigma"] for st in res.view_stats.values()]
        ini = [st["wide_median_abs_sigma"] for st in res.initial_stats.values()]
        assert max(fin) < 1.0, (r["seed"], fin)
        assert np.mean(fin) < 0.5 * np.mean(ini), (r["seed"], ini, fin)
        assert res.landmark_rms_pct_iod < 3.0


def test_contour_stage_runtime(stage_runs):
    """5 outer iterations on the 3.5k-vertex procedural head (3458 vertices) < 30 s."""
    r = stage_runs[0]
    assert r["res"].V.shape == (3458, 3)
    assert r["time"] < 30.0, r["time"]


def test_focal_distance_diagnosis(kit):
    """SIL-3: selfie-like set (26 mm-eq at 0.35 m, yaw 0 / +-25 deg). The focal is frozen in the
    cameras (FIXED_F), which are fitted to the interior landmarks with the shape held; the contours
    are pure witnesses. A +25 % mis-set focal leaves the interior fitting (< 3 % IOD) but the
    outline off by > 3 sigma_n on >= 2 views -> 'C-FOCAL-DIST'; the correct focal does not."""
    from face3d.fit.contour import focal_distance_check
    for seed in (0, 1):
        subj, cams, uvs, obs, iod = _scene(kit, seed, (0.0, 25.0, -25.0), 350.0, 26.0, 600, 800)
        Xt = subj.landmarks()
        found = {}
        for fac in (1.0, 1.25):
            views = []
            for c, uv in zip(cams, uvs):
                c0 = c.copy()
                c0.f = c.f * fac
                c0.t = c.t + np.array([0.0, 0.0, (fac - 1.0) * c.t[2]])     # same image scale at the origin
                views.append(ViewObs(uv, c0, estimate_focal=False, sigma_px=1.0))
            f, info = focal_distance_check(subj.V_true, kit.triangles(), Xt, views, obs, iod)
            found[fac] = (f, info)
        f_bad, info_bad = found[1.25]
        assert f_bad is not None and f_bad.code == FINDING_FOCAL_DIST, info_bad["contour_median_sigma"]
        assert info_bad["landmark_rms_pct_iod"] < 3.0
        assert sum(m > 3.0 for m in info_bad["contour_median_sigma"].values()) >= 2
        assert found[1.0][0] is None, found[1.0][1]["contour_median_sigma"]
    # the rule itself (DESIGN 4.16 SIL-3)
    assert diagnose_focal_distance(2.0, [3.5, 4.0, 1.0]).code == FINDING_FOCAL_DIST
    assert diagnose_focal_distance(2.0, [3.5, 1.0, 1.0]) is None
    assert diagnose_focal_distance(4.0, [5.0, 5.0, 5.0]) is None                  # the interior does not fit
    assert diagnose_focal_distance(2.0, {0: 0.5, 1: 0.7}, ears_fail=True).code == FINDING_FOCAL_DIST
    fnd = diagnose_focal_distance(2.0, [3.5, 4.0])
    assert fnd.action == "ask" and fnd.severity == "warn" and fnd.detail["views_failing"] == [0, 1]
