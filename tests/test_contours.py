"""WP-17: contours v2 (DESIGN D-13, 4.15 stage D, 4.16, SIL-3).

ContourObs and residual kinds, the sub-vertex rim, the exact Felzenszwalb-Huttenlocher
distance transform, grid matching with the normal gate, Viterbi edge snap, the
LinearBasis shape model with the similarity projector, the contour Term inside the
bundle (free cameras), the focal/distance diagnosis and the legacy ``use_subvertex``
path of ``fit_silhouettes``.

WP-17 review regressions: the backward term past the open end of a partial outline,
the Term's normal gate and frozen Huber weights, one 40-sample budget per view, image
border truncation of mask contours, SIL-3 on estimated shapes (witness views, interior
landmarks, camera-uncertainty inflation) and a profile scene the landmark stage misses.
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
from face3d.mesh.reduced import ReducedDeformer, coef_matrix, farthest_point_sample, similarity_tangent_cm
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
    # past the open end of the segment (x in [20, 79]) the distance is Euclidean, not the normal offset
    # to the tangent-line extension: 31 px away -> truncated, zero gradient (WP-17 review)
    for mode in ("normal", "edt"):
        rr, gg = backward_residuals(ContourDistance(xy, nrm, pad=40, mode=mode), np.array([[110.0, 42.0]]),
                                    sigma_px=1.0, return_grad=True)
        assert rr[0] == pytest.approx(math.sqrt(0.5) * 3.0) and np.all(gg == 0.0), (mode, rr, gg)
    # just past the end: sqrt(s^2 + e^2), e the excess beyond the last sample (x = 79; nothing beyond it)
    d_end, g_end, _ = dist.sample(np.array([[81.0, 41.5]]))
    assert d_end[0] == pytest.approx(math.hypot(1.0, 2.0))
    assert g_end[0, 0] > 0 and g_end[0, 1] > 0
    j, s_off, e, sg = dist.project(np.array([[50.2, 41.5], [81.0, 41.5], [10.0, 40.0]]))
    assert np.allclose(s_off, [-1.0, -1.0, 0.5]) and np.allclose(e, [0.0, 2.0, 10.0]) and list(sg) == [0, 1, -1]
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


def test_tangent_extents_open_closed_and_chains():
    from face3d.fit.contour import tangent_extents
    xs = np.arange(0.0, 10.0)
    xy = np.column_stack([xs, np.zeros_like(xs)])
    n = np.tile([0.0, -1.0], (10, 1))                 # tangent t = (-n_y, n_x) = (1, 0)
    lo, hi = tangent_extents(xy, n)
    assert lo[0] == 0.0 and hi[-1] == 0.0               # open ends: nothing beyond the end samples
    assert np.allclose(hi[:-1], 1.0) and np.allclose(lo[1:], -1.0)       # half-way (0.5) + 0.5 px tolerance
    # a closed circle: every sample has both neighbours
    th = np.linspace(0, 2 * np.pi, 40, endpoint=False)
    c = np.column_stack([np.cos(th), np.sin(th)]) * 20.0
    lo, hi = tangent_extents(c, c / 20.0)
    assert np.all(lo < 0) and np.all(hi > 0)
    # two chains (two outlines in one view) are never linked, even when adjacent in the array
    xy2 = np.vstack([xy, xy + [10.5, 0.0]])
    lo, hi = tangent_extents(xy2, np.vstack([n, n]), chain=np.r_[np.zeros(10), np.ones(10)])
    assert hi[9] == 0.0 and lo[10] == 0.0
    lo, hi = tangent_extents(xy2, np.vstack([n, n]))
    assert hi[9] > 0.0                                  # one chain: 9 and 10 are neighbours


def test_from_mask_drops_image_border_truncation():
    """A mask cut off by the image edge (head and shoulders) is a truncation, not a silhouette: no
    samples along the border and true (sideways) normals where the outline runs into the edge."""
    H, W = 100, 120
    m = np.zeros((H, W), bool)
    m[30:, 40:80] = True                              # object cut off by the bottom image edge
    o = ContourObs.from_mask(m)
    assert not np.any(o.xy[:, 1] > H - 0.25), o.xy[o.xy[:, 1] > H - 0.25]     # nothing on the border line
    low = o.xy[:, 1] > H - 6.0                        # the two sides near the bottom edge
    assert low.sum() >= 8 and np.all(np.abs(o.normal_out[low, 0]) > 0.95), o.normal_out[low]
    assert np.allclose(np.abs(o.xy[low, 0] - 60.0), 20.0, atol=0.6)
    old = ContourObs.from_mask(m, image_border="keep")   # the border as background (previous behaviour)
    on_border = old.xy[:, 1] >= H - 0.01
    assert on_border.sum() > 30 and np.all(old.normal_out[on_border, 1] > 0.9)
    assert o.M < old.M - 30
    # a mask filling a whole image side keeps its inner outline only
    m2 = np.zeros((50, 60), bool)
    m2[:, :25] = True
    o2 = ContourObs.from_mask(m2)
    assert np.allclose(o2.xy[:, 0], 25.0, atol=0.6) and np.all(o2.normal_out[:, 0] > 0.95)
    with pytest.raises(ValueError):
        ContourObs.from_mask(np.ones((10, 10), bool))


def _toy_term(kit, obs, rim_uv, rim_n, **kw):
    """ContourTerm on the procedural head whose rim samples are replaced by ``rim_uv`` / ``rim_n`` (rim
    sample k sits on vertex k, so the frozen rows reveal which rim sample a pair took)."""
    from face3d.fit.contour import RimSamples
    lb = LinearBasis(kit, ReducedDeformer(kit.vertices, n_centers=20)).with_coefficient_rows()
    term = ContourTerm(obs, lb, {0: 100.0}, n_outer=3, **kw)
    P = len(rim_uv)
    vid = np.zeros((P, 4), np.int64)
    vid[:, 0] = np.arange(P)
    w = np.zeros((P, 4))
    w[:, 0] = 1.0
    smp = RimSamples(vid=vid, w=w, p=kit.vertices[:P].copy(), uv=np.asarray(rim_uv, float),
                     depth=np.full(P, 500.0), normal2d=np.asarray(rim_n, float), normal3d=np.zeros((P, 3)),
                     visible=np.ones(P, bool))
    term.rim_samples = lambda V, cam, raster=None, normals=None: smp
    term.update(lb.V_bar, [_look((0.0, 0.0, 800.0))], 0)
    return term, lb


def test_contour_term_update_normal_gate_and_huber(kit):
    """ContourTerm.update: the 40 deg normal gate picks a compatible rim sample over a nearer mismatched
    one, and the frozen IRLS weights of 'hard' rows are w_s min(1, delta / |r|) (delta = 2)."""
    a60 = math.radians(60.0)
    obs = [ContourObs(0, [[100.0, 100.0], [100.0, 200.0], [100.0, 300.0]], [[1.0, 0.0]] * 3, 0.5)]
    rim_uv = [[100.5, 100.0], [102.0, 100.0], [103.0, 200.0], [100.4, 300.0]]
    rim_n = [[math.cos(a60), math.sin(a60)], [1.0, 0.0], [1.0, 0.0], [1.0, 0.0]]
    term, lb = _toy_term(kit, obs, rim_uv, rim_n, backward=False)
    assert [b.kind for b in term._blocks] == ["hard"]
    blk = term._blocks[0]
    assert blk.obs_idx.tolist() == [0, 1, 2]
    rim_of = [int(np.argmin(np.linalg.norm(kit.vertices[:4] - p, axis=1))) for p in blk.pbar]
    assert rim_of == [1, 2, 3]                       # sample 0 took rim 1 (0 deg), not rim 0 (60 deg, nearer)
    r = np.array([2.0 / 0.5, 3.0 / 0.5, 0.4 / 0.5])
    assert np.allclose(blk.sw ** 2, np.minimum(1.0, 2.0 / np.abs(r)))     # w_s = 1 (3 samples < cap)
    # with the gate test off (180 deg) the nearer mismatched rim sample wins
    term2, _ = _toy_term(kit, obs, rim_uv, rim_n, backward=False, max_normal_deg=180.0)
    rim_of2 = [int(np.argmin(np.linalg.norm(kit.vertices[:4] - p, axis=1))) for p in term2._blocks[0].pbar]
    assert rim_of2[0] == 0


def test_contour_term_shared_sample_budget_and_open_end(kit):
    """One budget of 40 effective samples per view, shared by the forward kinds and the backward rows
    (DESIGN 4.16 'Noise'); backward rows only for rim samples on the observed span of an open outline."""
    ys = np.arange(100.0, 220.0, 1.0)                # 120 observed samples on x = 100, v in [100, 219]
    obs = [ContourObs(0, np.column_stack([np.full_like(ys, 100.0), ys]), np.tile([1.0, 0.0], (len(ys), 1)),
                      0.5),
           ContourObs(0, [[300.0, 150.0], [300.0, 151.0]], [[1.0, 0.0]] * 2, 0.5, kind="outer_bound")]
    yr = np.arange(80.0, 240.0, 1.0)                 # the rim runs 20 px past both ends of the outline
    rim_uv = np.vstack([np.column_stack([np.full_like(yr, 100.2), yr]), [[300.5, 150.0], [300.5, 151.0]]])
    rim_n = np.tile([1.0, 0.0], (len(rim_uv), 1))
    term, lb = _toy_term(kit, obs, rim_uv, rim_n)
    eff = {}
    for b in term._blocks:
        kw = {"hard": 1.0, "outer_bound": 10.0, "backward": 0.5}[b.kind]
        eff[b.kind] = float(np.sum(b.sw ** 2) / kw)
    assert set(eff) == {"hard", "outer_bound", "backward"}
    assert sum(eff.values()) == pytest.approx(40.0)  # not 40 per kind plus 20 backward
    bw = [b for b in term._blocks if b.kind == "backward"][0]
    n_b = len(bw.sw)
    assert 120 <= n_b <= 122                         # the 40 rim samples past the ends carry no row
    assert eff["hard"] == pytest.approx(40.0 * 120 / (122 + n_b))          # shared in proportion to counts
    assert eff["outer_bound"] == pytest.approx(40.0 * 2 / (122 + n_b))
    v_rows = lb.V_bar[:len(rim_uv)]
    rim_rows = [int(np.argmin(np.linalg.norm(v_rows - p, axis=1))) for p in bw.pbar]
    v_of = rim_uv[rim_rows, 1]
    assert v_of.min() >= 100.0 - 1.0 and v_of.max() <= 219.0 + 1.0, (v_of.min(), v_of.max())


def test_backward_rows_partial_profile_outline(kit):
    """Partial outline (the face side of a profile silhouette, as from pins, a lasso or a snapped jaw):
    with the model rim exactly on the true rim, every backward row is a rim sample on the observed span,
    and its row is the normal offset to it (WP-17 review: 17 of 70 rows were rim samples up to 21 px past
    the outline's ends, pulled toward the tangent-line extension of its last samples)."""
    subj = out_of_prior_subject(kit, np.random.default_rng(0))
    T = kit.triangles()
    cam = _cam(90.0, 1000.0, 85.0, 600, 800)
    full = ContourObs.from_mask(rasterize(subj.V_true, T, cam, cull_backfaces=True).mask, view=0)
    c = full.xy.mean(axis=0)
    sel = (full.xy[:, 1] > c[1] - 60) & (full.xy[:, 1] < c[1] + 20) & (full.normal_out[:, 0] < -0.3)
    part = ContourObs(0, full.xy[sel], full.normal_out[sel], full.sigma_n_px[sel])
    lb = LinearBasis(kit, ReducedDeformer(subj.V_true, n_centers=60)).with_coefficient_rows()
    term = ContourTerm([part], lb, {0: 89.0}, n_outer=5)
    V = lb.vertices_q(np.zeros(lb.n_params))
    ras = {0: rasterize(V, T, scale_camera(cam, 0.5), cull_backfaces=True)}
    for it in (0, 4):
        term.update(V, [cam], it, ras)
        bw = [b for b in term._blocks if b.kind == "backward"]
        assert len(bw) == 1 and len(bw[0].sw) > 20
        uv = cam.project(bw[0].pbar)                  # q = 0: the rim sample positions
        d_e = np.min(np.linalg.norm(uv[:, None] - part.xy[None], axis=2), axis=1)
        d_n = np.abs(np.sum(bw[0].n * (uv - bw[0].x), axis=1))
        assert d_e.max() <= term.gates[0] + 1.5, (it, d_e.max(), term.gates[0])
        assert np.all(d_e <= d_n + 1.5), (it, np.max(d_e - d_n))
        r = term.residuals(_State(lb, V, cam), None)
        assert np.all(np.isfinite(r))


class _State:
    """Minimal bundle state for ContourTerm.residuals: X with the basis' coefficient rows and one
    inverse-depth camera block."""

    def __init__(self, lb, V, cam):
        from face3d.geometry.camera import camera_to_invdepth
        self.X = lb.points(np.zeros(lb.n_params))
        d = camera_to_invdepth(cam)
        self.invdepth = [dict(R=d["R"], tau=d["tau"], rho=d["rho"], s=d["s"], block=np.zeros(7), kind="free")]


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


def test_no_tangential_drift_subvertex_offset_outline():
    """Clustered one-sided samples that are *not* on the rim (offset +-0.5 px along the outward normal of
    the sub-vertex rim): normal-only sub-vertex targets move the rim by exactly the normal offset and
    leave it in place along the contour; the legacy full correction drags it tangentially.  (The WP-06
    construction of test_m1_fixes - samples on the tangent lines at the silhouette *vertices* - is off the
    sub-vertex rim polyline by the chord sagitta, so normal-only fitting rightly moves the mesh by
    ~0.09 mm there; this test covers the off-rim case with a known answer instead.)"""
    m = uv_sphere(80, 40, 80)
    dist = 20000.0
    R, t = look_at(np.array([dist, 0, 0.0]), np.zeros(3))
    cam = Camera.centered(4000.0 * dist / 700.0, 3000, 3000, R=R, t=t)
    V = m.vertices
    rim = rim_points(V, m.triangles(), m.vertex_normals(), cam)
    order = _rim_loop(rim)
    P = np.vstack([rim.uv[order], rim.uv[order[:1]]])
    N2 = np.vstack([rim.normal2d[order], rim.normal2d[order[:1]]])
    Y = np.r_[rim.p[order, 1], rim.p[order[0], 1]]
    arc = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    scale = cam.f / dist                                  # px per mm at the sphere
    radial = V / np.linalg.norm(V, axis=1, keepdims=True)
    on_rim = (np.abs(V[:, 0]) < 3.0) & (V[:, 1] > 10.0)
    for delta in (0.5, -0.5):
        pts = []
        for a in np.arange(0.0, arc[-1], 20.0):
            for d in (1.0, 2.0, 3.0, 4.0):
                if np.interp(a + d, arc, Y) > 0:
                    p = np.array([np.interp(a + d, arc, P[:, 0]), np.interp(a + d, arc, P[:, 1])])
                    n = np.array([np.interp(a + d, arc, N2[:, 0]), np.interp(a + d, arc, N2[:, 1])])
                    pts.append(p + delta * n / np.linalg.norm(n))
        outline = np.array(pts)
        moves = {}
        for no in ((True, False) if delta > 0 else (True,)):
            Vn, _ = fit_silhouettes(m, [ContourView(cam, outline)], iterations=8, normal_only=no, use_subvertex=True)
            D = Vn - V
            rad = np.sum(D * radial, axis=1)
            moves[no] = (float(np.median(rad[on_rim])), float(np.linalg.norm(D - rad[:, None] * radial, axis=1).max()))
        assert moves[True][0] == pytest.approx(delta / scale, abs=0.01), moves
        assert moves[True][1] <= 0.03, moves                       # no tangential drift
        if delta > 0:
            assert moves[False][1] > 5.0 * moves[True][1] and moves[False][1] > 0.15, moves


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
#: Witness selfies of the SIL-3 test: (yaw deg, distance mm, 35 mm-eq focal, W, H).  A front camera
#: at 0.30 m (camera-perspective-distortion: selfies 0.25-0.4 m), the image at 1200 x 1600 px.
SELFIES = ((20.0, 300.0, 26.0, 1200, 1600), (-20.0, 300.0, 26.0, 1200, 1600))
FOCAL_ERR = 1.25                     # the mis-set (frozen) focal of the SIL-3 test


def _cam(yaw_deg, dist, f35, W, H, target=(0.0, 5.0, 40.0), pitch_deg=0.0):
    """Camera on an orbit around ``target`` (head frame mm), f from the 35 mm-equivalent."""
    y, p = math.radians(yaw_deg), math.radians(pitch_deg)
    tgt = np.asarray(target, float)
    C = tgt + dist * np.array([math.sin(y) * math.cos(p), math.sin(p), math.cos(y) * math.cos(p)])
    R, t = look_at(C, tgt)
    return Camera.centered(f35 / 36.0 * W, W, H, R=R, t=t)


def _dorsal_hump(kit, V, amp=3.0, sigma=10.0):
    """V with a Gaussian hump (``amp`` mm along the normals, ``sigma`` mm) at the n-prn chord midpoint:
    a nasal-dorsum feature between landmarks, which the landmark stage cannot see."""
    L = kit.landmark_positions("anatomical44", V, ["n", "prn"])
    d = np.linalg.norm(V - 0.5 * (L[0] + L[1]), axis=1)
    return V + vertex_normals(V, kit.triangles()) * (amp * np.exp(-0.5 * (d / sigma) ** 2))[:, None]


def _scene(kit, seed, specs, noise_px=1.0, hump=False):
    """Out-of-prior WP-11 subject (optionally with a dorsal hump), landmark observations (geometric
    visibility, N(0, noise^2) px) and full-resolution mask contours per view; IOD_px = f IOD_mm / depth of
    the eye centre.  ``specs``: (yaw, distance mm, 35 mm-eq focal, W, H) per view.  Returns (subject,
    true surface, true landmarks, cameras, uvs, obs, iod)."""
    rng = np.random.default_rng(seed)
    subj = out_of_prior_subject(kit, rng)
    T = kit.triangles()
    ids = kit.landmark_names("anatomical44")
    Vt = _dorsal_hump(kit, subj.V_true) if hump else subj.V_true
    Xt = kit.landmark_positions("anatomical44", Vt)
    E = Xt[[ids.index(n) for n in ("en_L", "en_R", "ex_L", "ex_R")]]
    iod_mm = float(np.linalg.norm(0.5 * (E[0] + E[2]) - 0.5 * (E[1] + E[3])))
    cams, uvs, obs, iod = [], [], [], []
    for k, (yaw, dist, f35, W, H) in enumerate(specs):
        c = _cam(yaw, dist, f35, W, H)
        vis = landmark_visibility(kit, Vt, "anatomical44", c)
        uv = c.project(Xt) + rng.normal(scale=noise_px, size=(len(Xt), 2))
        uv[~vis] = np.nan
        cams.append(c)
        uvs.append(uv)
        obs.append(ContourObs.from_mask(rasterize(Vt, T, c, cull_backfaces=True).mask, view=k, source="test_mask"))
        iod.append(c.f * iod_mm / float(c.depth(E.mean(axis=0, keepdims=True))[0]))
    return subj, Vt, Xt, cams, uvs, obs, iod


def _profile_windows(kit):
    """Midline vertex windows of the profile error: 'nose' = within 12 mm of prn plus the dorsum between
    n and prn (where the hump sits), 'chin' = within 15 mm of pg."""
    V = kit.vertices
    ml = kit.midline
    n0, p0, g0 = (V[kit.landmark_vertices("anatomical44", [nm])[0]] for nm in ("n", "prn", "pg"))
    tip = ml[np.linalg.norm(V[ml] - p0, axis=1) < 12.0]
    dorsum = ml[(V[ml, 1] <= n0[1]) & (V[ml, 1] >= p0[1]) & (V[ml, 2] > 85.0)]
    return {"nose": np.union1d(tip, dorsum), "chin": ml[np.linalg.norm(V[ml] - g0, axis=1) < 15.0]}


def _profile_error(kit, V, X, Vt, Xt):
    """RMS distance (mm) of the fitted midline vertices of the nose and chin windows to the true surface,
    after similarity alignment of the fitted face landmarks (DESIGN 7.3 'landmark similarity alignment';
    the ear and cranial landmarks are left out)."""
    ids = kit.landmark_names("anatomical44")
    fi = [ids.index(n) for n in FACE_IDS]
    s, R, t = umeyama(X[fi], Xt[fi])
    Va = apply_similarity(V, s, R, t)
    return [float(np.sqrt(np.mean(point_to_mesh(Va[w], Vt, kit.triangles())[0] ** 2)))
            for w in _profile_windows(kit).values()]


def _selfie_views(cams, uvs, fac):
    """FIXED_F views of the witness selfies with the focal set to ``fac`` x the true one; the distance is
    scaled by the same factor (dolly zoom: same image scale at the target)."""
    out = []
    for c, uv in zip(cams, uvs):
        c0 = c.copy()
        c0.f = c.f * fac
        c0.t = c.t + np.array([0.0, 0.0, (fac - 1.0) * c.t[2]])
        out.append(ViewObs(uv, c0, estimate_focal=False, sigma_px=1.0))
    return out


@pytest.fixture(scope="module")
def stage_runs(kit):
    """Landmark bundle (factor prior, free focal with a 5 % EXIF prior) on front + left profile +
    three-quarter views (85 mm-eq at 1 m, 600 x 800 px, 1 px landmark noise) of 5 out-of-prior subjects
    with a 3 mm dorsal hump between n and prn; then the contour stage with free cameras: LinearBasis
    K = 150 with its centres spread over the face hemisphere (rest z > 0: kernel ~28 mm, fine enough
    to bend the dorsum between the held landmarks), contours restricted to the same region, 5 outer
    iterations.  Two selfies (SELFIES) whose focal is frozen at +25 % are SIL-3 witness views."""
    prior = FactorPrior.from_package()
    lv = kit.landmark_vertices("anatomical44")
    face = kit.vertices[:, 2] > 0.0
    front = np.flatnonzero(face)
    centers = front[farthest_point_sample(kit.vertices[front], 150)]
    portraits = ((0.0, 1000.0, 85.0, 600, 800), (90.0, 1000.0, 85.0, 600, 800), (-45.0, 1000.0, 85.0, 600, 800))
    out = []
    for seed in STAGE_SEEDS:
        subj, Vt, Xt, cams, uvs, obs, iod = _scene(kit, seed, portraits + SELFIES, hump=True)
        views = []
        for c, uv in zip(cams[:3], uvs[:3]):
            c0 = c.copy()
            c0.t = c0.t + np.array([3.0, -3.0, 20.0])
            views.append(ViewObs(uv, c0, f_prior=c.f, f_prior_log_sigma=0.05, sigma_px=1.0))
        lm = bundle_adjust(views, prior.mean(), None, prior=prior)
        s, R, t = umeyama(kit.vertices[lv], lm.X)
        V0 = apply_similarity(kit.vertices, s, R, t)
        V0 = RBFWarp(V0[lv], lm.X)(V0)                       # template through the landmark solution
        basis = LinearBasis(kit, ReducedDeformer(V0, centers_idx=centers))
        sviews = [dataclasses.replace(v, camera=c) for v, c in zip(views, lm.cameras)]
        sviews += _selfie_views(cams[3:], uvs[3:], FOCAL_ERR)
        t0 = time.perf_counter()
        res = contour_stage(basis, sviews, obs, iod, n_outer=5, witness_views=(3, 4),
                            term_kwargs={"vertex_mask": face})
        dt = time.perf_counter() - t0
        out.append(dict(seed=seed, res=res, time=dt, before=_profile_error(kit, V0, lm.X, Vt, Xt),
                        after=_profile_error(kit, res.V, res.X, Vt, Xt), cams=cams, uvs=uvs, obs=obs, iod=iod,
                        face=face))
    return out


def test_contour_stage_recovers_profile(stage_runs):
    after = np.array([r["after"] for r in stage_runs])            # (seeds, [nose, chin]) mm
    before = np.array([r["before"] for r in stage_runs])
    assert np.median(after.max(axis=1)) <= 1.5, after
    assert np.median(after, axis=0).max() <= 1.5
    # the landmark stage misses the dorsal hump between n and prn; the contour stage recovers it
    assert np.median(before[:, 0]) > 1.4, before
    assert np.median(after[:, 0]) <= 0.7 * np.median(before[:, 0]), (before[:, 0], after[:, 0])
    assert np.all(after[:, 0] < before[:, 0] - 0.05), (before[:, 0], after[:, 0])
    assert np.median(after[:, 1]) <= np.median(before[:, 1]) + 0.1            # the chin is not degraded
    for r in stage_runs:
        res = r["res"]
        assert res.landmark_shift_mm.max() <= 0.5, (r["seed"], res.landmark_shift_mm.max())
        assert len(res.history) == 5 and res.flags == []
        # the SIL-3 rule on the fitted views' final state does not fire (only the witnesses may)
        assert all(set(f.detail["views_failing"]) <= {3, 4} for f in res.findings), res.findings
        assert res.V_start is not None and len(res.cameras) == 5
        # the silhouettes are fitted: every view ends below 1 sigma_n (median |r|) and the mean
        # wide-gate residual drops by at least half
        assert sorted(res.view_stats) == [0, 1, 2]
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


def test_focal_distance_diagnosis(kit, stage_runs):
    """SIL-3 on estimated shapes (no ground truth enters the check).  The contour stage fits the shape to
    the portrait views; two selfies at 0.30 m whose FIXED_F focal is frozen at +25 % are witness views:
    their cameras come from their interior landmarks with the fitted shape held and their contours are
    compared with sigma_n inflated by the cameras' own uncertainty.  The stage reports 'C-FOCAL-DIST' on
    every seed of the sweep (no false negative); the same check with the correct focal reports nothing
    (no false positive).  (WP-17 review sweep, seeds 0-9: 10/10 detected, 0/10 false; with the selfies at
    600 x 800 px, 0.35 m the camera uncertainty is ~1 px at the outline and only about half the cases
    are detected; with the landmark-stage surface instead of the fitted one about a third misclassify.)"""
    from face3d.fit.contour import focal_distance_check
    ids = kit.landmark_names("anatomical44")
    hits, false = 0, 0
    for r in stage_runs:
        res = r["res"]
        f_w = [f for f in res.findings if f.code == FINDING_FOCAL_DIST]
        hit = len(f_w) == 1 and sorted(f_w[0].detail["views_failing"]) == [3, 4]
        hits += hit
        assert res.witness is not None and sorted(res.witness["contour_median_sigma"]) == [3, 4]
        assert res.witness["landmark_rms_pct_iod"] < 3.0                  # the interior fits
        if hit:
            assert sum(m > 3.0 for m in res.witness["contour_median_sigma"].values()) >= 2
        # the correct focal, same estimated shape and witnesses: no finding
        sobs = [dataclasses.replace(o, view=o.view - 3) for o in r["obs"][3:]]
        good = _selfie_views(r["cams"][3:], r["uvs"][3:], 1.0)
        f_ok, info = focal_distance_check(res.V, kit.triangles(), res.X, good, sobs, r["iod"][3:],
                                          landmark_names=ids, vertex_mask=r["face"])
        false += f_ok is not None
        assert info["landmark_rms_pct_iod"] < 3.0
        assert all(st["wide_pose_sigma_px"] > 0 for st in info["view_stats"].values())
    assert hits == len(stage_runs) and false == 0, (hits, false)
    # the rule itself (DESIGN 4.16 SIL-3)
    assert diagnose_focal_distance(2.0, [3.5, 4.0, 1.0]).code == FINDING_FOCAL_DIST
    assert diagnose_focal_distance(2.0, [3.5, 1.0, 1.0]) is None
    assert diagnose_focal_distance(4.0, [5.0, 5.0, 5.0]) is None                  # the interior does not fit
    assert diagnose_focal_distance(2.0, {0: 0.5, 1: 0.7}, ears_fail=True).code == FINDING_FOCAL_DIST
    fnd = diagnose_focal_distance(2.0, [3.5, 4.0])
    assert fnd.action == "ask" and fnd.severity == "warn" and fnd.detail["views_failing"] == [0, 1]
    assert diagnose_focal_distance(2.0, {3: 3.5, 7: 4.0}).detail["views_failing"] == [3, 7]


def test_focal_distance_check_uses_interior_landmarks(kit, stage_runs):
    """SIL-3 'interior landmark RMS' (DESIGN 4.16): the witness cameras are refit from the interior
    landmarks only, so a wild ear or cranial point changes neither the cameras nor the RMS."""
    from face3d.fit.contour import SIL3_NON_INTERIOR_BASES, focal_distance_check, interior_landmark_mask
    ids = kit.landmark_names("anatomical44")
    m = interior_landmark_mask(ids)
    assert not m[[ids.index(n) for n in ("t_L", "sa_R", "sba_L", "eu_R", "v", "op", "tr", "zy_L", "go_R")]].any()
    assert m[[ids.index(n) for n in ("en_L", "prn", "ch_R", "pg", "p_L")]].all()
    assert {n.split("_")[0] for n in np.asarray(ids)[~m]} == set(SIL3_NON_INTERIOR_BASES)
    r = stage_runs[0]
    res = r["res"]
    assert np.array_equal(res.interior, m)
    sobs = [dataclasses.replace(o, view=o.view - 3) for o in r["obs"][3:]]
    good = _selfie_views(r["cams"][3:], r["uvs"][3:], 1.0)
    bad = []
    for v in good:
        uv = np.asarray(v.uv, float).copy()
        for nm in ("t_L", "t_R", "sa_L", "sa_R", "v"):
            if np.isfinite(uv[ids.index(nm)]).all():
                uv[ids.index(nm)] += 60.0
        bad.append(dataclasses.replace(v, uv=uv))
    _, i0 = focal_distance_check(res.V, kit.triangles(), res.X, good, sobs, r["iod"][3:], landmark_names=ids)
    _, i1 = focal_distance_check(res.V, kit.triangles(), res.X, bad, sobs, r["iod"][3:], landmark_names=ids)
    for c0, c1 in zip(i0["cameras"], i1["cameras"]):
        assert np.allclose(c0.R, c1.R) and np.allclose(c0.t, c1.t)
    assert i0["landmark_rms_pct_iod"] == pytest.approx(i1["landmark_rms_pct_iod"])
    # with every landmark the corrupted ears would pull the RMS up
    _, i2 = focal_distance_check(res.V, kit.triangles(), res.X, bad, sobs, r["iod"][3:],
                                 interior=np.ones(len(ids), bool))
    assert i2["landmark_rms_pct_iod"] > 2.0 * i1["landmark_rms_pct_iod"]


def test_pose_uv_jacobian_numeric():
    """d uv / d camera block in the bundle's parameterisation (left rotation increment, tau mm, rho in
    1/m, a = ln s or phi = ln f): the Jacobian behind the SIL-3 pose-uncertainty inflation."""
    from face3d.fit.contour import pose_uv_jacobian
    from face3d.geometry.camera import camera_to_invdepth, invdepth_to_camera
    from face3d.solve.bundle import rodrigues
    cam = _cam(20.0, 350.0, 26.0, 600, 800, pitch_deg=5.0)
    P = np.random.default_rng(11).normal(scale=40.0, size=(6, 3)) + [0.0, 0.0, 40.0]

    def uv_of(th, kind):
        d = camera_to_invdepth(cam)
        rho = d["rho"] + 1e-3 * th[5]
        if kind == "free":
            s = d["s"] * math.exp(th[6])
        elif kind == "hard":
            s = cam.f * math.exp(th[6]) * rho
        else:
            s = cam.f * rho
        c = invdepth_to_camera(rodrigues(th[:3]) @ d["R"], d["tau"] + th[3:5], s, rho, like=cam)
        return c.project(P)
    for kind, k in (("free", 7), ("hard", 7), ("fixed_f", 6)):
        J = pose_uv_jacobian(cam, P, kind)
        assert J.shape == (6, 2, k)
        for j in range(k):
            e = np.zeros(k)
            e[j] = 1e-6
            num = (uv_of(e, kind) - uv_of(-e, kind)) / 2e-6
            assert np.allclose(J[:, :, j], num, atol=1e-5 * max(1.0, np.abs(num).max())), (kind, j)
