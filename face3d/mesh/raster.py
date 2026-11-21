"""Numpy z-buffer rasteriser: depth, triangle id, barycentrics, normals, Lambert shading.

Used by the test bed for depth maps, masks and shaded images (DESIGN §7.2
"Images"), by contour visibility checks (DESIGN §4.16 "the rasterised depth
confirms visibility") and by texture projection (DESIGN §4.18 z-buffer
visibility).

Conventions (DESIGN §3.1, identical to :mod:`face3d.geometry.camera`)
---------------------------------------------------------------------
* World units are millimetres; ``V`` is (n,3) in the world frame and is mapped
  to the camera frame with ``cam.to_camera`` (X_c = R·X_w + t; +x right, +y down,
  +z forward).
* Projection is the pinhole u = f·x/z + c_x, v = f·y/z + c_y. Radial distortion
  ``cam.k`` is ignored (WP-02 spec).
* Image coordinates are continuous with the origin at the top-left *corner* of
  the top-left pixel; the pixel in row ``j`` and column ``i`` (array element
  ``[j, i]``) has its centre at (u, v) = (i + 0.5, j + 0.5). All coverage tests
  are made at pixel centres.
* ``depth`` is the camera-frame z (mm, along the optical axis, not the ray
  length), ``inf`` on background. ``tri_id`` is the triangle index (−1 on
  background). ``bary`` holds perspective-correct barycentrics (u, v, w) of the
  visible surface point with respect to the triangle's vertices (A, B, C) =
  ``V[tris[tri_id]]``, so X_world = u·A + v·B + w·C; zeros on background.
* Coverage: a pixel centre is inside a triangle when all three screen-space
  barycentrics are ≥ −1e-9 (inclusive test, so shared edges are covered by both
  neighbours and the depth test decides).
* Visibility: the smallest depth wins; exact depth ties go to the lower triangle
  id. The result is therefore independent of processing order (small triangles
  are processed in vectorised batches, large ones in a Python loop).
* Front-facing triangles (outward normal towards the camera, for meshes wound
  counter-clockwise seen from outside, see :mod:`face3d.mesh.distance`) have a
  negative signed area in (u, v) pixel coordinates; with ``cull_backfaces`` only
  those are drawn. This matches ``face3d.fit.silhouette.silhouette_vertices``.
* Triangles with any vertex at camera z ≤ ``near`` are skipped (no clipping).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..geometry.camera import Camera

__all__ = ["RasterResult", "rasterize", "render_normals", "render_lambert", "boundary_pixels",
           "INSIDE_EPS", "DEFAULT_LIGHT_DIR_WORLD", "DEFAULT_AMBIENT"]

# Inclusive coverage tolerance on normalised screen barycentrics (WP-02 spec).
INSIDE_EPS = 1e-9
# Shading defaults shared with the test-bed renderer (WP-02/WP-11 specs; a
# rendering convention for synthetic images, not a measured quantity): light
# travelling down, into the face (−z) and towards +x, i.e. a key light from the
# front, above and the subject's right; 25 % ambient.
DEFAULT_LIGHT_DIR_WORLD = (0.3, -0.5, -0.8)
DEFAULT_AMBIENT = 0.25

_WINDOW_CLASSES = (1, 2, 4, 8, 16)      # bbox side classes rasterised in vectorised batches
_FRAG_BATCH = 1 << 20                    # candidate pixel centres per vectorised batch


@dataclass
class RasterResult:
    """Per-pixel rasterisation buffers; see the module docstring for conventions."""

    depth: np.ndarray      # (H,W) float64 camera z in mm, inf on background
    tri_id: np.ndarray     # (H,W) int64, -1 on background
    bary: np.ndarray       # (H,W,3) float64 perspective-correct barycentrics, 0 on background
    mask: np.ndarray       # (H,W) bool, tri_id >= 0

    @property
    def shape(self) -> tuple[int, int]:
        return self.depth.shape  # type: ignore[return-value]


def _project(V: np.ndarray, cam: Camera) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    Xc = cam.to_camera(np.asarray(V, np.float64).reshape(-1, 3))
    z = Xc[:, 2]
    with np.errstate(divide="ignore", invalid="ignore"):
        u = cam.f * Xc[:, 0] / z + cam.cx
        v = cam.f * Xc[:, 1] / z + cam.cy
    return u, v, z


class _Buffers:
    def __init__(self, H: int, W: int):
        self.H, self.W = H, W
        self.depth = np.full(H * W, np.inf)
        self.tri = np.full(H * W, -1, np.int64)
        self.bary = np.zeros((H * W, 3))

    def merge(self, pix, dep, tri, b):
        """Fold fragments in: per pixel the lexicographic minimum of (depth, tri id) wins."""
        if pix.size == 0:
            return
        order = np.lexsort((tri, dep, pix))
        ps = pix[order]
        sel = order[np.r_[True, ps[1:] != ps[:-1]]]
        p, d, t = pix[sel], dep[sel], tri[sel]
        cd, ct = self.depth[p], self.tri[p]
        win = (d < cd) | ((d == cd) & (t < ct))
        p, sel = p[win], sel[win]
        self.depth[p] = dep[sel]
        self.tri[p] = tri[sel]
        self.bary[p] = b[sel]


def _window_fragments(ids, sh, sw, r0, r1, c0, c1, ut, vt, zt, inv_area, W):
    """Fragments of triangles `ids` evaluated on (sh × sw) pixel windows at their bbox corner."""
    rows = r0[ids][:, None] + np.arange(sh)            # (n,sh)
    cols = c0[ids][:, None] + np.arange(sw)            # (n,sw)
    pv = rows + 0.5
    pu = cols + 0.5
    au, bu, cu = ut[ids, 0], ut[ids, 1], ut[ids, 2]
    av, bv, cv = vt[ids, 0], vt[ids, 1], vt[ids, 2]
    ia = inv_area[ids][:, None, None]

    def edge(xu, xv, yu, yv):
        # signed doubled area of (x, y, p) for every pixel centre p of the window
        return ((yu - xu)[:, None, None] * (pv - xv[:, None])[:, :, None]
                - (yv - xv)[:, None, None] * (pu - xu[:, None])[:, None, :]) * ia

    l0 = edge(bu, bv, cu, cv)       # weight of A
    l1 = edge(cu, cv, au, av)       # weight of B
    l2 = edge(au, av, bu, bv)       # weight of C
    inside = ((l0 >= -INSIDE_EPS) & (l1 >= -INSIDE_EPS) & (l2 >= -INSIDE_EPS)
              & (rows <= r1[ids][:, None])[:, :, None] & (cols <= c1[ids][:, None])[:, None, :])
    k, i, j = np.nonzero(inside)
    if k.size == 0:
        return None
    l0, l1, l2 = l0[k, i, j], l1[k, i, j], l2[k, i, j]
    tri = ids[k]
    w0, w1, w2 = l0 / zt[tri, 0], l1 / zt[tri, 1], l2 / zt[tri, 2]
    dep = 1.0 / (w0 + w1 + w2)
    b = np.column_stack([w0 * dep, w1 * dep, w2 * dep])
    pix = rows[k, i] * W + cols[k, j]
    return pix, dep, tri, b


def rasterize(V: np.ndarray, tris: np.ndarray, cam: Camera, width: int | None = None,
              height: int | None = None, cull_backfaces: bool = False, near: float = 1.0) -> RasterResult:
    """Z-buffer rasterisation of a triangle mesh seen by a pinhole camera.

    Parameters
    ----------
    V : (n,3) world vertices (mm). tris : (F,3) vertex indices.
    cam : :class:`~face3d.geometry.camera.Camera`; its intrinsics are used as
        given (``k`` ignored).
    width, height : image size in pixels; default ``cam.width`` / ``cam.height``.
        Overriding them changes the canvas only, not the intrinsics.
    cull_backfaces : draw only front-facing triangles (see module docstring).
    near : triangles with any vertex at camera z ≤ ``near`` (mm) are skipped
        (no clipping); a ``near`` ≤ 0 still skips vertices at z ≤ 0.

    Returns
    -------
    :class:`RasterResult` with depth, tri_id, bary and mask buffers.

    Each triangle is evaluated on the pixel centres of its clipped bounding box
    with edge functions; small triangles (bbox sides ≤ 16 px) are batched,
    larger ones are looped over. Depth uses perspective-correct interpolation
    of 1/z, so planar surfaces get exact depths.
    """
    W = int(cam.width if width is None else width)
    H = int(cam.height if height is None else height)
    tris = np.asarray(tris, np.int64).reshape(-1, 3)
    buf = _Buffers(H, W)
    if len(tris) and W > 0 and H > 0:
        _rasterize_into(buf, V, tris, cam, cull_backfaces, near)
    depth = buf.depth.reshape(H, W)
    tri_id = buf.tri.reshape(H, W)
    return RasterResult(depth=depth, tri_id=tri_id, bary=buf.bary.reshape(H, W, 3), mask=tri_id >= 0)


def _rasterize_into(buf: _Buffers, V, tris, cam, cull_backfaces, near):
    H, W = buf.H, buf.W
    u, v, z = _project(V, cam)
    ut, vt, zt = u[tris], v[tris], z[tris]
    # Vertices at or behind the camera centre are never drawn, whatever `near` is.
    okz = np.all(zt > max(float(near), 0.0), axis=1)
    ut = np.where(okz[:, None], ut, 0.0)
    vt = np.where(okz[:, None], vt, 0.0)
    zt = np.where(okz[:, None], zt, 1.0)
    with np.errstate(over="ignore", invalid="ignore"):
        area2 = (ut[:, 1] - ut[:, 0]) * (vt[:, 2] - vt[:, 0]) - (vt[:, 1] - vt[:, 0]) * (ut[:, 2] - ut[:, 0])
        ok = okz & np.isfinite(area2) & (area2 != 0)
        if cull_backfaces:
            ok &= area2 < 0
        c0 = np.clip(np.ceil(ut.min(axis=1) - 0.5), 0, W)
        c1 = np.clip(np.floor(ut.max(axis=1) - 0.5), -1, W - 1)
        r0 = np.clip(np.ceil(vt.min(axis=1) - 0.5), 0, H)
        r1 = np.clip(np.floor(vt.max(axis=1) - 0.5), -1, H - 1)
    ok &= np.isfinite(c0) & np.isfinite(c1) & np.isfinite(r0) & np.isfinite(r1)
    c0 = np.where(ok, c0, 0).astype(np.int64)
    c1 = np.where(ok, c1, -1).astype(np.int64)
    r0 = np.where(ok, r0, 0).astype(np.int64)
    r1 = np.where(ok, r1, -1).astype(np.int64)
    ok &= (c0 <= c1) & (r0 <= r1)
    idx = np.flatnonzero(ok)
    if idx.size == 0:
        return
    inv_area = np.zeros(len(tris))
    inv_area[idx] = 1.0 / area2[idx]
    bw = c1 - c0 + 1
    bh = r1 - r0 + 1
    big = idx[np.maximum(bw[idx], bh[idx]) > _WINDOW_CLASSES[-1]]
    small = idx[np.maximum(bw[idx], bh[idx]) <= _WINDOW_CLASSES[-1]]

    # Vectorised batches of small triangles, grouped by (height, width) window class.
    if small.size:
        cls = np.asarray(_WINDOW_CLASSES)
        ch = cls[np.searchsorted(cls, bh[small])]
        cw = cls[np.searchsorted(cls, bw[small])]
        for sh in _WINDOW_CLASSES:
            for sw in _WINDOW_CLASSES:
                grp = small[(ch == sh) & (cw == sw)]
                step = max(1, _FRAG_BATCH // (sh * sw))
                for s0 in range(0, grp.size, step):
                    fr = _window_fragments(grp[s0:s0 + step], sh, sw, r0, r1, c0, c1, ut, vt, zt, inv_area, W)
                    if fr is not None:
                        buf.merge(*fr)

    # Large triangles: one bounding box at a time, z-test in place.
    depth = buf.depth.reshape(H, W)
    tri_buf = buf.tri.reshape(H, W)
    bary = buf.bary.reshape(H, W, 3)
    for t in big:
        rr = np.arange(r0[t], r1[t] + 1) + 0.5
        cc = np.arange(c0[t], c1[t] + 1) + 0.5
        au, bu, cu = ut[t]
        av, bv, cv = vt[t]
        ia = inv_area[t]
        l0 = ((cu - bu) * (rr - bv)[:, None] - (cv - bv) * (cc - bu)[None, :]) * ia
        l1 = ((au - cu) * (rr - cv)[:, None] - (av - cv) * (cc - cu)[None, :]) * ia
        l2 = ((bu - au) * (rr - av)[:, None] - (bv - av) * (cc - au)[None, :]) * ia
        inside = (l0 >= -INSIDE_EPS) & (l1 >= -INSIDE_EPS) & (l2 >= -INSIDE_EPS)
        if not inside.any():
            continue
        w0, w1, w2 = l0 / zt[t, 0], l1 / zt[t, 1], l2 / zt[t, 2]
        with np.errstate(divide="ignore", invalid="ignore"):
            dep = 1.0 / (w0 + w1 + w2)
        sd = depth[r0[t]:r1[t] + 1, c0[t]:c1[t] + 1]
        st = tri_buf[r0[t]:r1[t] + 1, c0[t]:c1[t] + 1]
        win = inside & ((dep < sd) | ((dep == sd) & (t < st)))
        if not win.any():
            continue
        sd[win] = dep[win]
        st[win] = t
        sb = bary[r0[t]:r1[t] + 1, c0[t]:c1[t] + 1]
        sb[win] = np.column_stack([w0[win] * dep[win], w1[win] * dep[win], w2[win] * dep[win]])


# --------------------------------------------------------------------------- shading
def _unit_vertex_normals(V: np.ndarray, tris: np.ndarray) -> np.ndarray:
    """Area-weighted unit vertex normals (as ``face3d.mesh.core.Mesh.vertex_normals``)."""
    a, b, c = V[tris[:, 0]], V[tris[:, 1]], V[tris[:, 2]]
    fn = np.cross(b - a, c - a)
    n = np.zeros_like(V)
    for k in range(3):
        for j in range(3):
            n[:, j] += np.bincount(tris[:, k], weights=fn[:, j], minlength=len(V))
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    return n / np.where(ln > 0, ln, 1.0)


def render_normals(res: RasterResult, V: np.ndarray, tris: np.ndarray) -> np.ndarray:
    """(H,W,3) world-frame unit normals interpolated from area-weighted vertex normals.

    Interpolation uses the perspective-correct barycentrics of ``res`` and the
    result is renormalised; background pixels are 0. ``V``/``tris`` must be the
    mesh that produced ``res``.
    """
    V = np.asarray(V, np.float64).reshape(-1, 3)
    tris = np.asarray(tris, np.int64).reshape(-1, 3)
    out = np.zeros(res.bary.shape)
    m = res.mask
    if not m.any():
        return out
    vn = _unit_vertex_normals(V, tris)
    t = res.tri_id[m]
    b = res.bary[m]
    tv = tris[t]
    n = b[:, 0:1] * vn[tv[:, 0]] + b[:, 1:2] * vn[tv[:, 1]] + b[:, 2:3] * vn[tv[:, 2]]
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    out[m] = n / np.where(ln > 0, ln, 1.0)
    return out


def render_lambert(res: RasterResult, V: np.ndarray, tris: np.ndarray, cam: Camera,
                   albedo: np.ndarray | None = None,
                   light_dir_world: tuple[float, float, float] | np.ndarray = DEFAULT_LIGHT_DIR_WORLD,
                   ambient: float = DEFAULT_AMBIENT) -> np.ndarray:
    """Lambert-shaded image, (H,W,3) float32 in [0, 1], background 0.

    colour = albedo · (ambient + (1 − ambient)·max(0, n·ℓ)), with n the
    interpolated unit normal (:func:`render_normals`) and ℓ = −light_dir_world
    normalised: ``light_dir_world`` is the direction in which the light
    *travels* (world frame). Lighting is two-sided: on a back-facing triangle
    (geometric normal pointing away from ``cam``, e.g. the inside of an open mesh
    seen through an opening) the interpolated normal is flipped towards the
    camera; ``cam`` must be the camera that produced ``res``.

    albedo : None (white, so the image equals the shading term), a (3,) RGB
        colour, or (n,3) per-vertex colours interpolated with the barycentrics.
        Values are linear and the result is clipped to [0, 1].
    """
    V = np.asarray(V, np.float64).reshape(-1, 3)
    tris = np.asarray(tris, np.int64).reshape(-1, 3)
    H, W = res.mask.shape
    img = np.zeros((H, W, 3), np.float32)
    m = res.mask
    if not m.any():
        return img
    n = render_normals(res, V, tris)[m]
    t = res.tri_id[m]
    b = res.bary[m]
    tv = tris[t]
    # Two-sided lighting decided per triangle from its geometric normal, so smooth
    # normals that graze away from the camera near a silhouette are left alone.
    A = V[tv[:, 0]]
    fn = np.cross(V[tv[:, 1]] - A, V[tv[:, 2]] - A)
    away = np.einsum("ij,ij->i", fn, A - cam.center) > 0
    n[away] = -n[away]
    ell = -np.asarray(light_dir_world, np.float64)
    ell = ell / np.linalg.norm(ell)
    shade = ambient + (1.0 - ambient) * np.clip(n @ ell, 0.0, None)
    if albedo is None:
        alb = np.ones((len(t), 3))
    else:
        albedo = np.asarray(albedo, np.float64)
        if albedo.shape == (3,):
            alb = np.broadcast_to(albedo, (len(t), 3))
        elif albedo.ndim == 2 and albedo.shape == (len(V), 3):
            alb = b[:, 0:1] * albedo[tv[:, 0]] + b[:, 1:2] * albedo[tv[:, 1]] + b[:, 2:3] * albedo[tv[:, 2]]
        else:
            raise ValueError("albedo must be None, (3,) or (n_vertices, 3)")
    img[m] = np.clip(alb * shade[:, None], 0.0, 1.0).astype(np.float32)
    return img


def boundary_pixels(mask: np.ndarray) -> np.ndarray:
    """(K,2) pixel centres (u, v) = (col + 0.5, row + 0.5) of mask pixels that have
    a 4-neighbour outside the mask (pixels beyond the image border count as
    outside). Row-major order."""
    m = np.asarray(mask, bool)
    p = np.pad(m, 1, constant_values=False)
    interior = p[1:-1, 1:-1] & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    rows, cols = np.nonzero(m & ~interior)
    return np.column_stack([cols + 0.5, rows + 0.5]).astype(np.float64)
