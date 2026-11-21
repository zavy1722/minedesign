"""WP-18 texture projection: UV G-buffer, weights, gains, gates, two-band blend, fills.

Acceptance tests (WBS WP-18; DESIGN 4.18, rec TEX-8):
* test_gains_recovered
* test_no_leakage_onto_occluded_texels
* test_texture_gates
* test_mirror_fill_off_by_default_and_marked_when_on
* test_two_band_preserves_low_frequency

Renders come from the WP-11 test bed (subjects generated independently of any prior)
through :mod:`face3d.mesh.raster`.  Gains are applied in linear light to the rendered
sRGB images; "+/-1 mm shape noise" is a per-vertex displacement U(-1, 1) mm along the
normal of the geometry the projector is given (the images come from the true shape).
"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pytest

from face3d.core import config
from face3d.core.policy import ConsentRecord, Scope
from face3d.io.image_ops import linear_to_srgb, srgb_to_linear
from face3d.model.procedural_head import build_procedural_head
from face3d.synthetic import orbit_camera
from face3d.testbed import render as RD
from face3d.testbed import surface_subjects as SS
from face3d.texture import blend as B
from face3d.texture import project as P

S = 256
NOW = datetime(2026, 11, 21, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def kit():
    return build_procedural_head()


@pytest.fixture(scope="module")
def subject(kit):
    return SS.out_of_prior_subject(kit, np.random.default_rng(5))


def _noisy(kit, V, rng, amp_mm=1.0):
    """V displaced by U(-amp, amp) mm along the unit vertex normals (+/-1 mm shape noise)."""
    n = RD.vertex_normals(V, kit.triangles())
    return V + rng.uniform(-amp_mm, amp_mm, len(V))[:, None] * n


def _views(kit, V_true, V_geom, yaws, gains, *, albedo="procedural", ambient=0.25, pitch=5.0, size=S):
    """Render views of V_true, apply per-view linear gains, project onto V_geom's G-buffer."""
    target = RD.face_centre(kit, V_true)
    tris = kit.triangles()
    gb = P.uv_gbuffer(kit, size, V=V_geom)
    cams, samples, weights, terms = [], [], [], []
    for k, yaw in enumerate(yaws):
        cam = orbit_camera(600.0, yaw, pitch, 85.0, width=600, height=800, target=target)
        view = RD.render_view(V_true, kit, cam, albedo=albedo, ambient=ambient)
        img = linear_to_srgb(np.clip(srgb_to_linear(view.image) * gains[k], 0.0, 1.0)).astype(np.float32)
        w, uv, tm = P.view_weights(gb, V_geom, tris, cam, img.shape, return_terms=True)
        cams.append(cam)
        samples.append(P.sample_image(img, uv))
        weights.append(w)
        terms.append(tm)
    return gb, cams, np.stack(samples), np.stack(weights), terms


def _relative(g):
    """Gains divided by their per-channel geometric mean (only relative gains are observable)."""
    g = np.asarray(g, float)
    return g / np.exp(np.log(g).mean(axis=0))


# =========================================================================== acceptance
def test_gains_recovered(kit, subject):
    """WP-11 renders with per-view gains 0.7-1.3 and +/-1 mm shape noise: relative gains within 2 %."""
    rng = np.random.default_rng(11)
    yaws = (-40.0, -20.0, 0.0, 20.0, 40.0)
    g_true = rng.uniform(0.7, 1.3, (len(yaws), 3))
    V_est = _noisy(kit, subject.V_true, rng)
    _gb, _c, samples, weights, _t = _views(kit, subject.V_true, V_est, yaws, g_true)
    g, info = P.solve_gains(list(samples), list(weights), return_info=True)
    assert g.shape == (len(yaws), 3)
    assert np.allclose(np.log(g).sum(axis=0), 0.0, atol=1e-9)          # sum log g = 0 per channel
    err = np.abs(_relative(g) / _relative(g_true) - 1.0)
    assert err.max() < 0.02, err
    assert all(n > 1000 for n in info["n_texels"])
    assert all(len(c) == 1 for c in info["components"])                # one connected view graph


def test_no_leakage_onto_occluded_texels(kit, subject):
    """Three-quarter view: cheek texels occluded by the nose get zero weight from it; where another
    view sees them, the blended colour is within 0.05 of the ground truth (TEX-8: no nose colour
    on occluded cheek texels).  The nose is painted green so any leak would be obvious."""
    rng = np.random.default_rng(12)
    V_true = subject.V_true
    tris = kit.triangles()
    lm = dict(zip(kit.landmark_names("anatomical44"), kit.landmark_positions("anatomical44", V_true)))

    def seg_dist(X, a, b):
        ab = b - a
        t = np.clip((X - a) @ ab / (ab @ ab), 0.0, 1.0)
        return np.linalg.norm(X - (a + t[:, None] * ab), axis=1)

    nose = np.minimum(seg_dist(V_true, lm["n"], lm["prn"]), seg_dist(V_true, lm["prn"], lm["sn"])) < 8.0
    assert nose.sum() >= 10
    albedo = np.where(nose[:, None], [0.25, 0.75, 0.30], [0.78, 0.60, 0.52])      # sRGB per vertex
    yaws = (45.0, 0.0, -45.0)                                            # view 0 = three-quarter
    g_true = rng.uniform(0.7, 1.3, (len(yaws), 3))
    V_est = _noisy(kit, V_true, rng)
    gb, cams, samples, weights, terms = _views(kit, V_true, V_est, yaws, g_true, albedo=albedo, ambient=1.0)
    res = B.build_texture(samples, weights, P.texel_size_mm(gb), region=gb.mask)

    # Ground truth: interpolated linear vertex albedo at each texel's surface point, in the
    # gauge of the solved gains (relative to their geometric mean).
    m = gb.mask
    lin_v = srgb_to_linear(albedo)
    truth = np.zeros((S, S, 3))
    truth[m] = np.einsum("nk,nkd->nd", gb.bary[m], lin_v[tris[gb.face_id[m]]])
    truth *= np.exp(np.log(g_true).mean(axis=0))

    # Cheek-side texels (no nose-coloured corner) facing view 0 and lying behind the nose
    # by more than the depth tolerance: exact ray test against the nose triangles.
    cand = m & (terms[0]["cos"] > 0.1) & ~nose[tris[np.maximum(gb.face_id, 0)]].any(axis=-1)
    cand &= np.linalg.norm(gb.pos - lm["prn"], axis=-1) < 45.0
    jj, ii = np.nonzero(cand)
    tri_nose = tris[nose[tris].any(axis=1)]
    occ = RD.segment_hits(V_est, tri_nose, cams[0].center, gb.pos[jj, ii],
                          end_tol_mm=P.visibility_eps_mm(1.0) + 1.0)
    jj, ii = jj[occ], ii[occ]
    assert len(jj) >= 50, len(jj)
    assert np.all(weights[0][jj, ii] == 0.0)
    seen = (weights[1][jj, ii] + weights[2][jj, ii]) > 0
    assert seen.mean() > 0.5
    err = np.abs(res.albedo_linear[jj[seen], ii[seen]] - truth[jj[seen], ii[seen]]).max(axis=-1)
    assert err.max() < 0.05, err.max()
    assert np.all(res.view_index[jj[seen], ii[seen]] != 0)


def test_texture_gates():
    """Unknown rights or missing TEXTURE scope blocked; reprojection median 2 px blocked;
    flagged views excluded without blocking (DESIGN 4.18, bl T2, eth F7)."""
    def record(scopes):
        return ConsentRecord(consent_id="c1", subject_pseudonym="s1", signer_role="self",
                             consent_text_version="v1", method="click", signed_at="2026-01-01T00:00:00Z",
                             expires_at=None, jurisdiction_tags=[], photo_sha256=["a", "b", "c"],
                             retention_days=30, revocation_contact="x", scopes=scopes, attested_age=30)

    ok_rec = record(Scope.RECONSTRUCT | Scope.TEXTURE)
    rights = ["self_shot", "photographer_licence", "subject_selfie"]
    f = P.texture_gates(ok_rec, rights, 0.8, 2.5, [[], [], []], now=NOW)
    assert f == [] and not P.texture_blocked(f)

    # Missing TEXTURE scope -> block (via core.policy.check('texture')).
    f = P.texture_gates(record(Scope.RECONSTRUCT), rights, 0.8, 2.5, now=NOW)
    assert P.texture_blocked(f) and "T-SCOPE" in {x["code"] for x in f}
    scope = next(x for x in f if x["code"] == "T-SCOPE")
    assert scope["value"] == ["TEXTURE"] and scope["severity"] == "block"

    # Unknown rights on one view -> block, naming the view.
    f = P.texture_gates(ok_rec, ["self_shot", "unknown", "self_shot"], 0.8, 2.5, now=NOW)
    rights_f = [x for x in f if x["code"] == "T-RIGHTS"]
    assert P.texture_blocked(f) and len(rights_f) == 1 and rights_f[0]["detail"]["views"] == [1]

    # No consent record at all -> block.
    assert P.texture_blocked(P.texture_gates(None, rights, 0.8, 2.5, now=NOW))

    # Reprojection: median 2 px -> block; max 3.5 px -> block; unknown -> block (fail closed).
    f = P.texture_gates(ok_rec, rights, 2.0, 2.5, now=NOW)
    assert [x["code"] for x in f] == ["T-REPROJ-MEDIAN"] and f[0]["value"] == 2.0 and f[0]["threshold"] == 1.5
    f = P.texture_gates(ok_rec, rights, 1.0, 3.5, now=NOW)
    assert [x["code"] for x in f] == ["T-REPROJ-MAX"] and P.texture_blocked(f)
    assert P.texture_blocked(P.texture_gates(ok_rec, rights, None, 2.0, now=NOW))
    assert not P.texture_blocked(P.texture_gates(ok_rec, rights, 1.5, 3.0, now=NOW))   # bounds inclusive

    # Flagged views and other date clusters are excluded, not blocking.
    f = P.texture_gates(ok_rec, rights, 0.8, 2.5, [["Retouched"], ["portrait"], ["clipped", "warped"]],
                        now=NOW)
    assert not P.texture_blocked(f)
    assert P.excluded_views(f) == [0, 2]
    assert all(x["action"] == "exclude_texture" and x["severity"] == "warn" for x in f)
    f = P.texture_gates(ok_rec, rights, 0.8, 2.5, now=NOW, date_clusters=[0, 1, 0])
    assert P.excluded_views(f) == [1] and f[0]["detail"]["flags"] == ["other_date_cluster"]
    for x in f:   # Finding-compatible dicts
        assert {"code", "severity", "value", "threshold", "action", "msg_key", "fix_key", "source", "badge",
                "photo_id", "detail", "view"} <= set(x)

    # build_texture honours the findings: blocking raises, excluded views get no weight.
    rng = np.random.default_rng(0)
    cols = rng.uniform(0.2, 0.8, (3, 8, 8, 3))
    wts = np.ones((3, 8, 8))
    blocked = P.texture_gates(ok_rec, ["unknown"] * 3, 0.8, 2.5, now=NOW)
    with pytest.raises(B.TextureBlocked):
        B.build_texture(cols, wts, 1.0, findings=blocked)
    excl = P.texture_gates(ok_rec, rights, 0.8, 2.5, [[], ["filtered"], []], now=NOW)
    res = B.build_texture(cols, wts, 1.0, findings=excl)
    assert res.provenance["excluded_views"] == [1] and res.provenance["gated"]
    assert not np.any(res.view_index == 1)


def test_mirror_fill_off_by_default_and_marked_when_on(kit, subject):
    """D-27: no mirroring unless allow_mirror=True; then only the low band, from sources with
    confidence >= 0.3, and every mirrored texel is marked and recorded in the provenance."""
    rng = np.random.default_rng(13)
    yaws = (25.0, 55.0)                                       # subject's left only
    g_true = rng.uniform(0.8, 1.2, (2, 3))
    gb, _c, samples, weights, _t = _views(kit, subject.V_true, subject.V_true, yaws, g_true)
    mmap = P.mirror_texel_map(kit, gb)
    texel = P.texel_size_mm(gb)

    off = B.build_texture(samples, weights, texel, region=gb.mask, mirror_uv_map=mmap)
    assert not off.mirrored_mask.any()
    assert off.provenance["allow_mirror"] is False and off.provenance["mirrored_fraction"] == 0.0
    assert "mirror" not in off.provenance["fill_order"]
    assert off.provenance["absolute_colour"] == "absolute colour unknown without a chart"
    assert off.filled_mask.any() and off.provenance["filled_fraction"] > 0

    on = B.build_texture(samples, weights, texel, region=gb.mask, mirror_uv_map=mmap, allow_mirror=True)
    mir = on.mirrored_mask
    assert mir.sum() > 100
    assert on.provenance["allow_mirror"] is True and on.provenance["mirrored_fraction"] > 0
    assert on.provenance["fill_order"] == ["mirror", "harmonic"]
    assert not np.any(mir & on.filled_mask)
    assert np.all(on.confidence[mir] == 0) and np.all(on.view_index[mir] == -1)
    src = mmap[mir]
    assert np.all(off.confidence[src[:, 0], src[:, 1]] >= 0.3)
    assert np.median(gb.pos[mir][:, 0]) < 0.0                 # mirrored onto the unseen right side
    observed = off.confidence > 0
    assert np.array_equal(on.albedo_linear[observed], off.albedo_linear[observed])

    # Direct calls: a no-op by default; when on, the low band (not the full albedo) is copied.
    S8 = 8
    alb = rng.uniform(0.2, 0.8, (S8, S8, 3))
    low = rng.uniform(0.2, 0.8, (S8, S8, 3))
    valid = np.zeros((S8, S8), bool)
    valid[:, :4] = True
    conf = np.where(valid, 1.0, 0.0)
    conf[0, 3] = 0.2                                          # weak source: not used
    mp = np.full((S8, S8, 2), -1, np.int64)
    jj, ii = np.mgrid[0:S8, 0:S8]
    mp[..., 0], mp[..., 1] = jj, S8 - 1 - ii
    out, marks = B.mirror_fill_low_band(alb, valid, mp, confidence=conf, low_band=low)
    assert np.array_equal(out, alb) and not marks.any()
    out, marks = B.mirror_fill_low_band(alb, valid, mp, True, confidence=conf, low_band=low)
    expect = ~valid
    expect[0, 4] = False
    assert np.array_equal(marks, expect)
    assert np.array_equal(out[marks], low[mp[marks][:, 0], mp[marks][:, 1]])
    assert np.array_equal(out[~marks], alb[~marks])
    with pytest.raises(ValueError):
        B.mirror_fill_low_band(alb, valid, mp, True)


def test_two_band_preserves_low_frequency(kit, subject):
    """Constant albedo, per-view gains removed by solve_gains, +/-1 mm shape noise: the blended
    albedo stays constant within 1 % on every observed texel."""
    rng = np.random.default_rng(14)
    yaws = (-35.0, 0.0, 35.0, 60.0)
    g_true = rng.uniform(0.7, 1.3, (len(yaws), 3))
    V_est = _noisy(kit, subject.V_true, rng)
    gb, _c, samples, weights, _t = _views(kit, subject.V_true, V_est, yaws, g_true,
                                          albedo=(0.70, 0.55, 0.45), ambient=1.0)
    g = P.solve_gains(list(samples), list(weights))
    albedo, conf, best = B.two_band_blend(samples / g[:, None, None, :], weights, P.texel_size_mm(gb))
    obs = conf > 0
    assert obs.sum() > 5000 and set(np.unique(best[obs])) <= set(range(len(yaws)))
    assert np.all(best[~obs] == -1)
    ref = np.median(albedo[obs], axis=0)
    assert np.abs(albedo[obs] / ref - 1.0).max() < 0.01
    expect = srgb_to_linear(np.array([0.70, 0.55, 0.45])) * np.exp(np.log(g_true).mean(axis=0))
    assert np.allclose(ref, expect, rtol=0.01)


# =========================================================================== units
def test_uv_gbuffer_texel_centres_and_seam(kit):
    gb = P.uv_gbuffer(kit, 64)
    pos, normal, mask, face_id = gb                      # unpacks as the spec's 4-tuple
    assert pos.shape == (64, 64, 3) and mask.dtype == bool and face_id.dtype == np.int64
    assert mask.mean() > 0.95                            # spherical layout covers the square
    assert mask[:, 0].mean() > 0.9 and mask[:, -1].mean() > 0.9   # both sides of the u seam
    tris = kit.triangles()
    jj, ii = np.nonzero(mask)
    tuv, _ = P._unwrap_u(kit.uv[tris[face_id[mask]]])
    uv = np.einsum("nk,nkd->nd", gb.bary[mask], tuv)
    uv[:, 0] = np.mod(uv[:, 0], 1.0)
    assert np.abs(uv[:, 0] - (ii + 0.5) / 64).max() < 1e-9   # texel centre ((i+0.5)/S, (j+0.5)/S)
    assert np.abs(uv[:, 1] - (jj + 0.5) / 64).max() < 1e-9
    assert np.all(gb.bary[mask] >= -1e-9)
    X = np.einsum("nk,nkd->nd", gb.bary[mask], kit.vertices[tris[face_id[mask]]])
    assert np.allclose(pos[mask], X)
    assert np.allclose(np.linalg.norm(normal[mask], axis=1), 1.0)
    assert np.all(face_id[~mask] == -1) and np.all(pos[~mask] == 0)
    # No seam smear: every texel position lies on its triangle (checked) and texel
    # neighbours in the same row are close on the surface away from the poles.
    rows = slice(16, 48)
    d = np.linalg.norm(pos[rows, 1:] - pos[rows, :-1], axis=-1)[mask[rows, 1:] & mask[rows, :-1]]
    assert d.max() < 20.0
    with pytest.raises(ValueError):
        P.uv_gbuffer(kit, 16, V=np.zeros((3, 3)))
    assert P.uv_gbuffer(kit, 64).face_id.tolist() == face_id.tolist()        # deterministic


def test_barycentric_fill_matches_brute_force():
    rng = np.random.default_rng(3)
    Tr = rng.uniform(-2.0, 14.0, (6, 3, 2))
    tri, bary = P.barycentric_fill(Tr, 12, 10)
    for j in range(10):
        for i in range(12):
            p = np.array([i + 0.5, j + 0.5])
            inside = []
            for t, (a, b, c) in enumerate(Tr):
                M = np.column_stack([b - a, c - a])
                if abs(np.linalg.det(M)) < 1e-12:
                    continue
                l1, l2 = np.linalg.solve(M, p - a)
                lam = np.array([1 - l1 - l2, l1, l2])
                if np.all(lam >= -1e-9):
                    inside.append((t, lam))
            if not inside:
                assert tri[j, i] == -1
                continue
            t = tri[j, i]
            assert t in [x[0] for x in inside]
            lam = dict(inside)[t]
            assert np.allclose(bary[j, i], lam, atol=1e-9)


def test_bounded_distance_exact():
    rng = np.random.default_rng(4)
    m = rng.uniform(size=(30, 40)) > 0.08
    m[:, :3] = True
    d = P.bounded_distance_to_outside(m, 6)
    bg = np.argwhere(np.pad(~m, 1, constant_values=True)) - 1
    for j, i in np.argwhere(m):
        true = np.sqrt(((bg - [j, i]) ** 2).sum(axis=1)).min()
        assert (abs(d[j, i] - true) < 1e-12) if true <= 6 else d[j, i] == 7.0
    assert np.all(d[~m] == 0)


def test_sample_image_bilinear_corner_convention():
    img = np.zeros((4, 5, 3), np.uint8)
    img[..., 0] = np.arange(20).reshape(4, 5) * 10
    img[..., 1] = 255
    uv = np.array([[2.5, 1.5], [3.0, 1.5], [0.0, 0.0], [5.0, 4.0], [-0.1, 1.0], [np.nan, 1.0]])
    out = P.sample_image(img, uv)
    enc = np.array([70, 75, 0, 190]) / 255.0
    assert np.allclose(out[:4, 0], srgb_to_linear(enc))       # pixel centre exact; midpoint; clamped
    assert np.allclose(out[:4, 1], 1.0)
    assert np.all(np.isnan(out[4:]))
    grey = P.sample_image(np.full((3, 3), 0.5), np.array([[1.5, 1.5]]))
    assert np.allclose(grey, srgb_to_linear(0.5))


def test_solve_gains_exact_components_and_constraint():
    rng = np.random.default_rng(5)
    K = (16, 16)
    a = rng.uniform(0.1, 0.8, K + (3,))
    g_true = rng.uniform(0.6, 1.4, (4, 3))
    w = rng.uniform(0.0, 1.0, (4,) + K) * (rng.uniform(size=(4,) + K) > 0.3)
    samples = [a * g_true[v] for v in range(4)]
    g = P.solve_gains(samples, list(w))
    assert np.allclose(_relative(g), _relative(g_true), rtol=1e-10)
    # Two disconnected pairs + one view with no overlap: gauge fixed per component.
    w2 = np.zeros((5,) + K)
    w2[0, :8] = w2[1, :8] = 1.0
    w2[2, 8:] = w2[3, 8:] = 1.0
    w2[4, :1, :1] = 1.0
    w2[4, 0, 0] = 0.0
    s5 = [a * gt for gt in rng.uniform(0.6, 1.4, (5, 3))]
    g5, info = P.solve_gains(s5, list(w2), return_info=True)
    assert info["components"][0] == [[0, 1], [2, 3], [4]]
    assert np.allclose(np.log(g5[:2]).sum(axis=0), 0) and np.allclose(np.log(g5[2:4]).sum(axis=0), 0)
    assert np.allclose(g5[4], 1.0)
    r01 = (s5[0] / s5[1])[0, 0]
    assert np.allclose(g5[0] / g5[1], r01)
    # Clipped / black samples are ignored.
    bad = [s.copy() for s in samples]
    bad[0][:4] = 0.99
    bad[1][4:8] = 0.0
    assert np.allclose(_relative(P.solve_gains(bad, list(w))), _relative(g_true), rtol=1e-10)


def test_fill_holes_harmonic_and_push_pull():
    jj, ii = np.mgrid[0:32, 0:32].astype(float)
    lin = np.stack([0.01 * ii + 0.2, 0.02 * jj + 0.1, 0.005 * (ii + jj)], axis=-1)
    valid = np.ones((32, 32), bool)
    valid[10:20, 12:22] = False                       # a hole: harmonic fill reproduces linear fields
    filled, fm = B.fill_holes(np.where(valid[..., None], lin, 0.0), valid, 500)
    assert np.array_equal(fm, ~valid)
    assert np.array_equal(filled[valid], lin[valid])
    assert np.abs(filled - lin).max() < 2e-3
    region = np.zeros((32, 32), bool)
    region[10:15] = True
    f2, fm2 = B.fill_holes(np.where(valid[..., None], lin, 0.0), valid, 10, region=region)
    assert np.array_equal(fm2, ~valid & region) and np.all(f2[~valid & ~region] == 0)
    same, none = B.fill_holes(lin, np.zeros((32, 32), bool))
    assert not none.any() and np.array_equal(same, lin)


def test_view_weight_terms(kit, subject):
    """Weights are in [0, 1]; zero beyond 75 deg, on z-buffer-hidden texels, within the eroded
    band of the face-mask boundary and inside the frame margin; frontal back-of-head is zero."""
    V = subject.V_true
    tris = kit.triangles()
    gb = P.uv_gbuffer(kit, 128, V=V)
    cam = orbit_camera(600.0, 30.0, 0.0, 85.0, width=600, height=800, target=RD.face_centre(kit, V))
    w, uv, t = P.view_weights(gb, V, tris, cam, (800, 600), return_terms=True)
    assert w.min() >= 0 and w.max() <= 1.0 and (w > 0).sum() > 1000
    pos = w > 0
    assert np.all(t["vis"][pos] == 1) and np.all(t["edge"][pos] > 0) and np.all(t["frame"][pos] == 1)
    assert np.all(t["cos"][pos] > np.cos(np.radians(75.0)) - 1e-12)
    full = (t["cos"] >= np.cos(np.radians(60.0))) & (t["vis"] == 1) & (t["edge"] == 1) & (t["frame"] == 1)
    assert np.allclose(w[full], t["cos"][full] ** 2)
    assert np.all(w[gb.mask & (gb.pos[..., 2] < -30.0)] == 0)        # back of the head
    assert np.all(np.isnan(uv[~gb.mask]))
    # Texels with positive weight project > 5 px from the raster silhouette.
    from face3d.mesh.raster import rasterize
    r = rasterize(V, tris, cam, cull_backfaces=False)
    d = P.bounded_distance_to_outside(r.mask, 8)
    cols = np.floor(uv[pos][:, 0]).astype(int)
    rows = np.floor(uv[pos][:, 1]).astype(int)
    assert d[rows, cols].min() > 5.0
    # Stricter margins only remove weight; a supplied face mask removes the masked pixels.
    w2, _ = P.view_weights(gb, V, tris, cam, (800, 600), edge_erode_px=8.0, frame_margin=0.3)
    assert np.all(w2 <= w + 1e-15) and (w2 > 0).sum() < (w > 0).sum()
    fm = np.ones((800, 600), bool)
    fm[:400] = False
    w3, uv3 = P.view_weights(gb, V, tris, cam, (800, 600), face_mask=fm, raster=r)
    assert np.all(w3[uv3[..., 1] < 400] == 0) and (w3 > 0).any()


def test_two_band_detail_comes_from_best_view():
    """High band from the max-weight view, low band from all views (rec TEX-4)."""
    rng = np.random.default_rng(6)
    base = np.full((32, 32, 3), 0.5)
    detail = np.zeros((32, 32, 3))
    detail[16, 16] = 0.2                                   # a 'mole' seen sharply by view 0 only
    c0 = base + detail
    c1 = base + 0.02                                       # second view slightly brighter, no detail
    w = np.stack([np.full((32, 32), 0.9), np.full((32, 32), 0.6)])
    alb, conf, best = B.two_band_blend(np.stack([c0, c1]), w, texel_mm=1.0, split_sigma_mm=3.0)
    assert np.all(best == 0) and np.allclose(conf, 1.0)
    # Away from the mole the result is the weighted mean (0.5 + 0.4 * 0.02).
    assert np.allclose(alb[2, 2], 0.508, atol=1e-9)
    assert alb[16, 16, 0] - alb[2, 2, 0] > 0.18             # the detail survives
    w[0, :, 20:] = 0.0                                     # view 0 does not see the right side
    alb2, _, best2 = B.two_band_blend(np.stack([c0, c1 + rng.normal(0, 1e-3, c1.shape)]), w, 1.0)
    assert np.all(best2[:, 20:] == 1) and np.all(best2[:, :20] == 0)
    assert np.isfinite(alb2).all()


def test_defaults_registered_with_badges():
    for full in ("texture.sigma_geom_mm", "texture.fade_start_deg", "texture.fade_end_deg",
                 "texture.cos_power", "texture.edge_erode_px", "texture.edge_ramp_px", "texture.frame_margin",
                 "texture.reproj_median_max_px", "texture.reproj_max_max_px", "texture.blend.split_sigma_mm",
                 "texture.blend.mirror_min_confidence", "texture.blend.fill_iterations"):
        d = config.get(full)
        assert d.badge in config.BADGES and d.source
    assert config.get("texture.reproj_median_max_px").value == 1.5
    assert config.get("texture.reproj_max_max_px").value == 3.0
    assert config.get("texture.blend.split_sigma_mm").value == 3.0
    assert P.visibility_eps_mm(1.0) == 2.0 and P.visibility_eps_mm(0.2) == 1.0


# =========================================================================== review regressions
def _consent(scopes=None):
    return ConsentRecord(consent_id="c1", subject_pseudonym="s1", signer_role="self", consent_text_version="v1",
                         method="click", signed_at="2026-01-01T00:00:00Z", expires_at=None, jurisdiction_tags=[],
                         photo_sha256=["a", "b", "c"], retention_days=30, revocation_contact="x",
                         scopes=Scope.RECONSTRUCT | Scope.TEXTURE if scopes is None else scopes, attested_age=30)


def test_texture_gates_rights_must_cover_every_view():
    """A view with no rights entry is unknown (eth F7, fail closed): a short per-view list
    blocks and names the uncovered views; a list is never broadcast; build_texture refuses
    colours for a different number of views than the gates checked."""
    rec = _consent()
    # One entry for three views (count from photo_ids / view_flags): blocked, views 1 and 2 named.
    f = P.texture_gates(rec, ["self_shot"], 0.8, 2.5, [[], [], []], photo_ids=["a", "b", "c"], now=NOW)
    assert P.texture_blocked(f) and f.n_views == 3
    r = [x for x in f if x["code"] == "T-RIGHTS"]
    assert len(r) == 1 and r[0]["detail"]["uncovered_views"] == [1, 2] and r[0]["detail"]["views"] == [1, 2]
    # Two entries for three views (count from date_clusters): blocked.
    f = P.texture_gates(rec, ["self_shot", "self_shot"], 0.8, 2.5, now=NOW, date_clusters=[0, 0, 0])
    assert P.texture_blocked(f) and [x["detail"]["uncovered_views"] for x in f if x["code"] == "T-RIGHTS"] == [[2]]
    # Explicit n_views; too many entries cannot be aligned either.
    assert P.texture_blocked(P.texture_gates(rec, ["self_shot"] * 2, 0.8, 2.5, n_views=3, now=NOW))
    assert P.texture_blocked(P.texture_gates(rec, ["self_shot"] * 4, 0.8, 2.5, n_views=3, now=NOW))
    # Disagreeing view counts -> T-VIEW-COUNT block.
    f = P.texture_gates(rec, ["self_shot"] * 3, 0.8, 2.5, [[], [], []], photo_ids=["a", "b"], now=NOW)
    assert "T-VIEW-COUNT" in {x["code"] for x in f} and P.texture_blocked(f)
    # A single string stands for every view; a full list passes; GateFindings is a plain list.
    f = P.texture_gates(rec, "self_shot", 0.8, 2.5, n_views=3, now=NOW)
    assert f == [] and isinstance(f, list) and f.n_views == 3
    f = P.texture_gates(rec, ["self_shot"] * 3, 0.8, 2.5, [[], ["filtered"], []], now=NOW)
    assert not P.texture_blocked(f) and f.n_views == 3 and all(x["detail"]["n_views"] == 3 for x in f)
    assert P.texture_blocked(P.texture_gates(rec, "unknown", 0.8, 2.5, n_views=2, now=NOW))
    # Without any view count the rights list defines the views (2 here) ...
    f2 = P.texture_gates(rec, ["self_shot"] * 2, 0.8, 2.5, now=NOW)
    assert f2 == [] and f2.n_views == 2
    cols = np.full((3, 8, 8, 3), 0.5)
    wts = np.ones((3, 8, 8))
    # ... and build_texture refuses three colour views gated as two (attribute or detail).
    with pytest.raises(B.TextureBlocked, match="2 views but 3"):
        B.build_texture(cols, wts, 1.0, findings=f2)
    f2x = P.texture_gates(rec, ["self_shot"] * 2, 0.8, 2.5, [["filtered"], []], now=NOW)
    with pytest.raises(B.TextureBlocked):
        B.build_texture(cols, wts, 1.0, findings=list(f2x))
    res = B.build_texture(cols, wts, 1.0, findings=list(f))      # 3 gated views, plain list
    blocked = P.texture_gates(rec, ["self_shot"], 0.8, 2.5, n_views=3, now=NOW)
    with pytest.raises(B.TextureBlocked):                         # a generator is read once, not lost
        B.build_texture(cols, wts, 1.0, findings=(x for x in blocked))
    assert res.provenance["gated_n_views"] == 3 and res.provenance["excluded_views"] == [1]


def test_view_weights_rejects_gbuffer_not_built_on_V(kit, subject):
    """A rest-shape G-buffer (spec call uv_gbuffer(kit, size)) used with the fitted V would
    sample and z-test at the wrong surface points: view_weights raises instead."""
    V = subject.V_true
    tris = kit.triangles()
    assert np.median(np.linalg.norm(V - kit.vertices, axis=1)) > 1.0
    cam = orbit_camera(600.0, 30.0, 5.0, 85.0, width=150, height=200, target=RD.face_centre(kit, V))
    rest = P.uv_gbuffer(kit, 48)
    with pytest.raises(ValueError, match="uv_gbuffer"):
        P.view_weights(rest, V, tris, cam, (200, 150))
    fit = P.uv_gbuffer(kit, 48, V=V)
    w, _uv = P.view_weights(fit, V, tris, cam, (200, 150))
    assert (w > 0).any()
    P.check_gbuffer_on_mesh(fit, V.astype(np.float32), tris)             # float32 round-off is fine
    extra = np.vstack([V, [[0.0, 0.0, 200.0]] * 3])                       # appended occluder triangle
    P.check_gbuffer_on_mesh(fit, extra, np.vstack([tris, [[len(V), len(V) + 1, len(V) + 2]]]))
    with pytest.raises(ValueError):
        P.check_gbuffer_on_mesh(fit, V, tris[: len(tris) // 2])           # not the G-buffer's triangles
    P.view_weights(tuple(rest), kit.vertices, tris, cam, (200, 150))      # plain tuple: nothing to check


def test_two_band_tiny_best_view_weight_falls_back_to_low_band():
    """The best view's own low-pass may be undefined at a texel it barely sees: the high
    band is then 0 (albedo = low band), never c_best - 0 (twice the colour)."""
    C = np.full((2, 16, 16, 3), 0.5)
    for tiny in (1e-6, 1e-11, 1e-14, 1e-300):
        w = np.zeros((2, 16, 16))
        w[0] = 1.0
        w[0, 8, 8] = 0.0
        w[1, 8, 8] = tiny
        alb, conf, best = B.two_band_blend(C, w, 1.0, 3.0)
        assert best[8, 8] == 1 and conf[8, 8] > 0
        assert np.allclose(alb, 0.5, atol=1e-9), (tiny, alb[8, 8])
    # A lone observed texel with a relatively tiny total weight, far from all others: no band
    # split, it keeps its own colour (not 0).
    w = np.zeros((2, 32, 32))
    w[0, :, :8] = 1.0
    w[1, 30, 30] = 1e-14
    C2 = np.full((2, 32, 32, 3), 0.5)
    C2[1, 30, 30] = (0.2, 0.3, 0.4)
    alb, conf, _ = B.two_band_blend(C2, w, 1.0, 1.0)
    assert np.allclose(alb[30, 30], (0.2, 0.3, 0.4)) and np.allclose(alb[:, :8], 0.5)
    # The normalised blur no longer depends on the scale of the weights.
    rng = np.random.default_rng(8)
    vals = rng.uniform(size=(16, 16, 3))
    ww = rng.uniform(size=(16, 16)) * (rng.uniform(size=(16, 16)) > 0.5)
    a, da = B.normalized_blur(vals, ww, 2.0)
    b, db = B.normalized_blur(vals, ww * 1e-20, 2.0)
    assert np.allclose(a, b, rtol=1e-12, atol=0) and np.allclose(db, da * 1e-20)


def test_depth_edges_opt_in(kit, subject):
    """The occlusion-edge extension of the edge term is off by default (WBS WP-18 spec: the
    face-mask boundary only); enabling it can only remove weight.  Its badge stays 🆕."""
    from face3d.mesh.raster import rasterize
    V = subject.V_true
    tris = kit.triangles()
    gb = P.uv_gbuffer(kit, 96, V=V)
    cam = orbit_camera(600.0, 45.0, 5.0, 85.0, width=300, height=400, target=RD.face_centre(kit, V))
    r = rasterize(V, tris, cam, cull_backfaces=False)
    w_def, _ = P.view_weights(gb, V, tris, cam, (400, 300), raster=r)
    w_off, _ = P.view_weights(gb, V, tris, cam, (400, 300), raster=r, depth_edge_angle_deg=None)
    assert np.array_equal(w_def, w_off)
    d = config.get("texture.depth_edge_angle_deg")
    assert d.badge == "\U0001F195" and d.value == 75.0
    w_on, _ = P.view_weights(gb, V, tris, cam, (400, 300), raster=r, depth_edge_angle_deg=d.value)
    assert np.all(w_on <= w_off) and (w_on > 0).sum() < (w_off > 0).sum()


def test_build_texture_refuses_when_no_view_is_usable():
    """Excluding every view (or a region no view sees) raises instead of returning black."""
    rng = np.random.default_rng(9)
    cols = rng.uniform(0.2, 0.8, (2, 8, 8, 3))
    w = np.ones((2, 8, 8))
    with pytest.raises(ValueError, match="no usable views"):
        B.build_texture(cols, w, 1.0, exclude_views=[0, 1])
    excl = P.texture_gates(_consent(), ["self_shot"] * 2, 0.8, 2.5, [["filtered"], ["retouched"]], now=NOW)
    with pytest.raises(ValueError, match="no usable views"):
        B.build_texture(cols, w, 1.0, findings=excl)
    w2 = w.copy()
    w2[:, :4] = 0.0
    region = np.zeros((8, 8), bool)
    region[:4] = True
    with pytest.raises(ValueError, match="no usable views"):
        B.build_texture(cols, w2, 1.0, region=region)
    res = B.build_texture(cols, w, 1.0, exclude_views=[0])
    assert res.provenance["observed_fraction"] == 1.0 and np.all(res.view_index == 1)
