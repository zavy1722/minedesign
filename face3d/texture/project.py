"""Texture projection: UV G-buffer, per-view weights, image sampling, log-domain gains, gates (WP-18).

Implements DESIGN D-27 and section 4.18 (rec TEX-1..TEX-3 and TEX-8, bl T2/T3, eth F7 and
the ethics texture gate).  The research basis is *texture-extraction*
(``research/reconstruction/texture-extraction.md``): every item there is expert
knowledge (🧠) except the cos exponent (↔️), so every number below is PROVISIONAL and is
registered as a badged default in :mod:`face3d.core.config` (namespace ``texture``).
Blending, hole filling and the mirror option live in :mod:`face3d.texture.blend`.

Pipeline (DESIGN 4.18)
----------------------
1. :func:`uv_gbuffer` rasterises the mesh in UV space: per texel the 3D position, the
   smoothed normal, the triangle id and barycentrics (rec TEX-1).
2. :func:`view_weights` projects every texel into one solved camera and scores it
   ``w = vis * cos^2(theta) * fade(60 deg -> 75 deg) * edge * frame`` (rec TEX-2, bl T3).
3. :func:`sample_image` reads the photo at the projected texel (bilinear, then sRGB
   decode to linear light).
4. :func:`solve_gains` levels exposure / white balance across views in log space with
   ``sum_v log g_v = 0`` per channel (rec TEX-3).
5. :func:`texture_gates` decides whether texture may be built at all (TEXTURE scope,
   rights basis, landmark reprojection; DESIGN 4.18, bl T2) and which views never feed
   albedo (filtered, retouched, warped, clipped, other date cluster).

Conventions and units
---------------------
* World: float64 millimetres in the head frame of the mesh ``V`` (DESIGN 2.1 inv. 2).
  Cameras are :class:`face3d.geometry.camera.Camera` (X_c = R X + t, +y down, +z
  forward); image coordinates use the corner convention of :mod:`face3d.mesh.raster`:
  pixel ``[row j, col i]`` has its centre at ``(u, v) = (i + 0.5, j + 0.5)``.
* Texture space: an ``S x S`` map; array element ``[j, i]`` is the texel whose centre is
  ``(u, v) = ((i + 0.5)/S, (j + 0.5)/S)`` (rec TEX-1), i.e. the column follows ``u`` and
  the row follows ``v``.  Row 0 is ``v`` near 0, the *bottom* of the texture in
  Blender's convention (the order of ``bpy`` image pixel buffers); flip the rows
  (``arr[::-1]``) to write a top-down image file.
* Triangles are the fan split of the kit faces (:meth:`TemplateKit.triangles`);
  ``face_id`` indexes that triangle list (for an all-quad kit, the quad is
  ``face_id // 2``).
* UV seams are allowed: charts need not be connected, texels between charts stay
  outside the mask (gutter).  A triangle whose corner ``u`` values span more than half
  the map (:data:`UV_WRAP_SPAN`) is taken to cross the seam of a ``u``-periodic layout
  (such as the procedural head's spherical UVs, ``u = 0.5 + atan2(x, z) / 2 pi``):
  it is unwrapped and rasterised on both sides of the seam.
* Colour: images are sRGB-encoded (uint8, uint16 or float in [0, 1]); everything after
  :func:`sample_image` is linear light (rec TEX-3: "work in linear RGB").
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from ..core import policy
from ..core.config import Default, register_defaults
from ..geometry.camera import Camera
from ..io.image_ops import srgb_to_linear
from ..mesh.raster import RasterResult, rasterize
from ..model.template_kit import area_weighted_normals

__all__ = [
    "TEXTURE_DEFAULTS", "UVGBuffer", "UV_WRAP_SPAN", "EXCLUDE_FLAGS", "GBUFFER_TOL_MM", "GateFindings",
    "barycentric_fill", "uv_gbuffer", "texel_size_mm", "mirror_texel_map",
    "bounded_distance_to_outside", "depth_edges", "visibility_eps_mm", "check_gbuffer_on_mesh",
    "view_weights", "sample_image", "solve_gains",
    "texture_gates", "texture_blocked", "excluded_views",
]

_BRAIN = "\U0001F9E0"
_NEW = "\U0001F195"
_CONTESTED = "↔️"
_TX = "texture-extraction Table 4"

#: Badged defaults of the projection stage (DESIGN 2.1: no hard-coded 🧠/↔️/🆕 numbers).
TEXTURE_DEFAULTS = register_defaults("texture", {
    "sigma_geom_mm": Default(
        1.0, _NEW, "WBS WP-18 spec default (geometry error sigma; rec TEX-8 tests use +/-1 mm shape "
        "noise; texture-extraction: 0.5-1 mm scan, 2-5 mm template-only fit)", "mm", (0.0, 100.0)),
    "eps_floor_mm": Default(
        1.0, _BRAIN, "DESIGN 4.18 / rec TEX-1: eps = max(1 mm, 2 sigma_geom) (" + _TX + ")", "mm",
        (0.0, 100.0)),
    "eps_sigma_factor": Default(
        2.0, _BRAIN, "DESIGN 4.18 / rec TEX-1: eps = max(1 mm, 2 sigma_geom) (" + _TX + ")", "",
        (0.0, 100.0)),
    "fade_start_deg": Default(
        60.0, _BRAIN, "DESIGN 4.18 / rec TEX-2 / bl T3: fade from 60 deg (" + _TX + ")", "deg", (0.0, 90.0)),
    "fade_end_deg": Default(
        75.0, _BRAIN, "DESIGN 4.18 / rec TEX-2 / bl T3: cut at 75 deg (" + _TX + ")", "deg", (0.0, 90.0)),
    "cos_power": Default(
        2.0, _CONTESTED, "DESIGN 4.18 w = vis cos^2: rec TEX-2 p = 2, contested 1-4 (" + _TX + ")", "",
        (0.0, 16.0)),
    "edge_erode_px": Default(
        5.0, _BRAIN, "rec TEX-2 erosion 5 px (" + _TX + ": 3-15 px)", "px", (0.0, 200.0)),
    "edge_ramp_px": Default(
        10.0, _BRAIN, "rec TEX-2 ramp 10 px (" + _TX + ": 3-15 px)", "px", (0.0, 400.0)),
    "frame_margin": Default(
        0.02, _BRAIN, "rec TEX-2 frame margin 2 % of the image width (" + _TX + ": 1-5 %)", "",
        (0.0, 0.5)),
    "depth_edge_angle_deg": Default(
        75.0, _NEW, "WP-18 implementation, OPT-IN (view_weights default None = WBS WP-18 spec edge "
        "term on the face-mask boundary only): when enabled, a depth step between 4-neighbour pixels "
        "steeper than this obliquity marks an occlusion boundary for the edge term (texture-extraction "
        "'Occlusion edges are wrong first': nose side, alar crease, ear, jaw over neck); equal to the "
        "fade cut-off; uncalibrated", "deg", (1.0, 89.9)),
    "min_views": Default(
        2, _NEW, "WBS WP-18 spec: gains use texels seen by >= 2 views (rec TEX-3)", "", (2, 10000)),
    "gain_floor_linear": Default(
        1e-3, _NEW, "WP-18 implementation: linear samples at or below this are left out of the "
        "log-domain gain fit (log of near-black / background)", "", (0.0, 1.0)),
    "gain_ceiling_linear": Default(
        0.955, _BRAIN, "DESIGN 4.1 Q-CLIP clip level 0.98 sRGB-encoded = 0.955 linear: clipped "
        "samples are left out of the gain fit", "", (0.0, 1.0)),
    "reproj_median_max_px": Default(
        1.5, _BRAIN, "DESIGN 4.18 / bl T2: project only if landmark reprojection median <= 1.5 px",
        "px", (0.0, 1000.0)),
    "reproj_max_max_px": Default(
        3.0, _BRAIN, "DESIGN 4.18 / bl T2: project only if landmark reprojection max <= 3 px",
        "px", (0.0, 1000.0)),
})
_D = {k: TEXTURE_DEFAULTS[k].value for k in TEXTURE_DEFAULTS}

#: A triangle whose corner u values span more than this fraction of the map crosses
#: the seam of a u-periodic layout (implementation constant: no valid chart triangle
#: spans half a texture).
UV_WRAP_SPAN = 0.5

#: Near plane (mm) for texel projection, the same as :func:`face3d.mesh.raster.rasterize`.
_NEAR_MM = 1.0

#: Largest |G-buffer position - barycentric position on V| (mm) that :func:`view_weights`
#: accepts (implementation constant: float32 round-off of head coordinates is ~1e-5 mm,
#: a stale rest-shape G-buffer is off by millimetres).
GBUFFER_TOL_MM = 1e-3

#: View flags that keep a view out of the albedo (DESIGN 4.18; DESIGN 4.1 Q-PROCESS,
#: Q-RETOUCH, Q-CLIP, Q-DATES).  Matching is case-insensitive.
EXCLUDE_FLAGS = ("filtered", "retouched", "warped", "clipped", "other_date_cluster")


# =========================================================================== G-buffer
@dataclass(eq=False)
class UVGBuffer:
    """Per-texel surface buffers of an ``S x S`` UV map (rec TEX-1).

    pos : (S, S, 3) float64 world position in mm (0 outside the mask).
    normal : (S, S, 3) float64 unit smoothed normal (area-weighted vertex normals of
        the mesh, interpolated and renormalised; 0 outside the mask).
    mask : (S, S) bool, texel centre inside a UV triangle.
    face_id : (S, S) int64 index into the kit's fan triangles (-1 outside).
    bary : (S, S, 3) float64 affine UV barycentrics of the texel centre in ``face_id``
        (for a seam-crossing triangle, with respect to its unwrapped UVs).
    size : S.

    Unpacks as the 4-tuple ``(pos, normal, mask, face_id)`` of the WP-18 spec.
    """

    pos: np.ndarray
    normal: np.ndarray
    mask: np.ndarray
    face_id: np.ndarray
    bary: np.ndarray
    size: int

    def __iter__(self):
        return iter((self.pos, self.normal, self.mask, self.face_id))

    def __len__(self) -> int:
        return 4

    def __getitem__(self, i):
        return (self.pos, self.normal, self.mask, self.face_id)[i]


def _unpack_gbuffer(gbuffer: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    pos, normal, mask, face_id = tuple(gbuffer)[:4]
    pos = np.asarray(pos, np.float64)
    normal = np.asarray(normal, np.float64)
    mask = np.asarray(mask, bool)
    if pos.shape[:2] != mask.shape or normal.shape[:2] != mask.shape or pos.shape[-1] != 3:
        raise ValueError("gbuffer pos/normal must be (S, S, 3) and mask (S, S)")
    return pos, normal, mask, np.asarray(face_id)


def barycentric_fill(P: np.ndarray, width: int, height: int) -> tuple[np.ndarray, np.ndarray]:
    """2D barycentric fill of triangles ``P`` (T, 3, 2) given in pixel/texel coordinates.

    Returns ``(tri (H, W) int64, bary (H, W, 3) float64)``: for every cell centre
    ``(i + 0.5, j + 0.5)`` covered by a triangle, its index and the affine barycentrics
    of the centre (inclusive coverage test, tolerance
    :data:`face3d.mesh.raster.INSIDE_EPS`); -1 and zeros elsewhere.  Overlaps are
    resolved deterministically (as by the z-buffer on exactly equal depth: whichever
    triangle the rounding of ``1 / sum(barycentrics)`` favours, then the lower index).

    Implementation: the triangles are lifted to the constant depth z = 2 mm and
    rasterised with :func:`face3d.mesh.raster.rasterize` through a camera with f = 2,
    c = 0 and identity pose, so the projection is exactly u = x, v = y and the
    perspective-correct barycentrics equal the affine ones (constant 1/z).
    """
    P = np.asarray(P, np.float64).reshape(-1, 3, 2)
    W, H = int(width), int(height)
    T = len(P)
    if T == 0 or W <= 0 or H <= 0:
        return np.full((max(H, 0), max(W, 0)), -1, np.int64), np.zeros((max(H, 0), max(W, 0), 3))
    V3 = np.empty((3 * T, 3))
    V3[:, :2] = P.reshape(-1, 2)
    V3[:, 2] = 2.0
    tris = np.arange(3 * T, dtype=np.int64).reshape(T, 3)
    cam = Camera(f=2.0, cx=0.0, cy=0.0, width=W, height=H)
    res = rasterize(V3, tris, cam, width=W, height=H, cull_backfaces=False, near=1.0)
    return res.tri_id, res.bary


def _unwrap_u(tri_uv: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Unwrap seam-crossing triangles of a u-periodic layout: (unwrapped (T,3,2), seam (T,) bool)."""
    uv = np.array(tri_uv, np.float64, copy=True)
    span = uv[:, :, 0].max(axis=1) - uv[:, :, 0].min(axis=1)
    seam = span > UV_WRAP_SPAN
    if seam.any():
        us = uv[seam, :, 0]
        uv[seam, :, 0] = np.where(us < 0.5, us + 1.0, us)
    return uv, seam


def uv_gbuffer(kit: Any, size: int, *, V: np.ndarray | None = None, tri_uv: np.ndarray | None = None,
               wrap_u: bool = True) -> UVGBuffer:
    """Rasterise the kit's triangles in UV space into an ``S x S`` G-buffer (rec TEX-1).

    Parameters
    ----------
    kit : :class:`face3d.model.template_kit.TemplateKit` (uses ``triangles()``,
        ``faces``, ``uv`` and ``vertices``).
    size : S, the map resolution in texels (rec TEX-7: 4096 for production, 2048 for
        phone sets; tests use 128-256).
    V : (n, 3) vertex positions in mm with the kit's topology (the *fitted* mesh);
        default the kit's rest vertices.
    tri_uv : optional (T, 3, 2) per-corner UVs (meshes with split UV seams); default
        ``kit.uv[triangles]``.
    wrap_u : unwrap triangles whose u span exceeds :data:`UV_WRAP_SPAN` and rasterise
        them on both sides of the u seam (see module docstring).

    Texel ``[j, i]`` has its centre at ``((i + 0.5)/S, (j + 0.5)/S)``.  Positions are the
    barycentric interpolation of ``V`` and normals of the area-weighted unit vertex
    normals of ``V`` (renormalised).  Memory: three (S, S, 3) float64 arrays
    (~1.2 GB at S = 4096; tile or use S = 2048 on small machines).
    """
    S = int(size)
    if S <= 0:
        raise ValueError("size must be a positive number of texels")
    tris = np.asarray(kit.triangles(), np.int64)
    Vx = np.asarray(kit.vertices if V is None else V, np.float64)
    if Vx.shape != np.asarray(kit.vertices).shape:
        raise ValueError(f"V must have the kit's shape {np.asarray(kit.vertices).shape}, got {Vx.shape}")
    tuv = np.asarray(kit.uv, np.float64)[tris] if tri_uv is None else np.asarray(tri_uv, np.float64)
    if tuv.shape != (len(tris), 3, 2):
        raise ValueError(f"tri_uv must be (T, 3, 2) = {(len(tris), 3, 2)}, got {tuv.shape}")
    if wrap_u:
        tuv, seam = _unwrap_u(tuv)
    else:
        seam = np.zeros(len(tris), bool)
    P = tuv * S
    ids = np.arange(len(tris), dtype=np.int64)
    if seam.any():
        P2 = P[seam].copy()
        P2[:, :, 0] -= S
        P = np.concatenate([P, P2])
        ids = np.concatenate([ids, ids[seam]])
    local, bary = barycentric_fill(P, S, S)
    mask = local >= 0
    face_id = np.where(mask, ids[np.maximum(local, 0)], -1)
    pos = np.zeros((S, S, 3))
    normal = np.zeros((S, S, 3))
    if mask.any():
        vn = area_weighted_normals(Vx, kit.faces)
        tv = tris[face_id[mask]]
        b = bary[mask]
        pos[mask] = np.einsum("nk,nkd->nd", b, Vx[tv])
        n = np.einsum("nk,nkd->nd", b, vn[tv])
        ln = np.linalg.norm(n, axis=1, keepdims=True)
        normal[mask] = n / np.where(ln > 0, ln, 1.0)
    bary = np.where(mask[..., None], bary, 0.0)
    return UVGBuffer(pos=pos, normal=normal, mask=mask, face_id=face_id, bary=bary, size=S)


def texel_size_mm(gbuffer: Any) -> float:
    """Median surface pitch of a texel in mm: ``sqrt(|dp/di x dp/dj|)`` over texels whose
    right and upper neighbours are on the same triangle fan region (finite differences).

    Used as ``texel_mm`` for :func:`face3d.texture.blend.two_band_blend`; UV layouts are
    not isometric, so this is a representative scalar, not a per-texel value.
    """
    pos, _n, mask, face_id = _unpack_gbuffer(gbuffer)
    ok = mask[:-1, :-1] & mask[:-1, 1:] & mask[1:, :-1]
    if not ok.any():
        raise ValueError("gbuffer has no 2x2 neighbourhood of valid texels")
    di = pos[:-1, 1:] - pos[:-1, :-1]
    dj = pos[1:, :-1] - pos[:-1, :-1]
    a = np.linalg.norm(np.cross(di, dj), axis=-1)[ok]
    # Texel pairs straddling a UV seam jump across the surface: drop outliers above
    # 10x the median pitch (a seam jump is many texels long).
    li = np.linalg.norm(di, axis=-1)[ok]
    lj = np.linalg.norm(dj, axis=-1)[ok]
    med = float(np.median(np.sqrt(a)))
    keep = (li < 10.0 * max(med, 1e-12)) & (lj < 10.0 * max(med, 1e-12))
    return float(np.median(np.sqrt(a[keep]))) if keep.any() else med


def mirror_texel_map(kit: Any, gbuffer: UVGBuffer, *, wrap_u: bool = True) -> np.ndarray:
    """(S, S, 2) int64 ``(row, col)`` of each texel's mirror texel, -1 where there is none.

    The mirror point of a texel with triangle ``t`` and barycentrics ``b`` is the point
    with the same barycentrics on the mirrored corners ``kit.mirror_map[tris[t]]``
    (rec TEX-5 / texture-extraction: "a symmetric vertex map becomes the mirror texel
    map"); its UV is ``sum_k b_k uv[mirror(corner_k)]`` (unwrapped across the u seam,
    then taken modulo 1), rounded down to the containing texel.  Texels whose mirror
    lands outside the G-buffer mask map to -1.  Requires the G-buffer's barycentrics,
    i.e. a :class:`UVGBuffer` from :func:`uv_gbuffer` without ``tri_uv``.
    """
    if not isinstance(gbuffer, UVGBuffer):
        raise TypeError("mirror_texel_map needs a UVGBuffer (it uses the barycentrics)")
    S = gbuffer.size
    out = np.full((S, S, 2), -1, np.int64)
    m = gbuffer.mask
    if not m.any():
        return out
    tris = np.asarray(kit.triangles(), np.int64)
    mm = np.asarray(kit.mirror_map, np.int64)
    corners = mm[tris[gbuffer.face_id[m]]]
    tuv = np.asarray(kit.uv, np.float64)[corners]
    if wrap_u:
        tuv, _ = _unwrap_u(tuv)
    uvm = np.einsum("nk,nkd->nd", gbuffer.bary[m], tuv)
    uvm[:, 0] = np.mod(uvm[:, 0], 1.0)
    col = np.clip(np.floor(uvm[:, 0] * S), 0, S - 1).astype(np.int64)
    row = np.clip(np.floor(uvm[:, 1] * S), 0, S - 1).astype(np.int64)
    ok = (uvm[:, 1] >= 0.0) & (uvm[:, 1] <= 1.0) & m[row, col]
    rc = np.where(ok[:, None], np.column_stack([row, col]), -1)
    out[m] = rc
    return out


# =========================================================================== image-space helpers
def bounded_distance_to_outside(mask: np.ndarray, max_px: int) -> np.ndarray:
    """Exact Euclidean distance (px, between pixel centres) from each True pixel to the
    nearest False pixel, capped at ``max_px + 1``; 0 on False pixels.

    Pixels beyond the image border count as False.  Two separable passes restricted to
    offsets ``|d| <= max_px`` (row distance, then ``min_dj dj^2 + g(j + dj)^2``): exact
    whenever the true distance is ``<= max_px`` (the minimiser then lies within the
    window), and ``>= max_px + 1`` otherwise.  Cost O(max_px * H * W).
    """
    m = np.asarray(mask, bool)
    H, W = m.shape
    R = max(0, int(math.ceil(max_px)))
    big = R + 1
    pad = R + 1
    bg = np.pad(~m, pad, constant_values=True)
    g = np.where(bg, 0, big).astype(np.int64)
    for d in range(1, R + 1):
        near = np.zeros_like(bg)
        near[:, d:] |= bg[:, :-d]
        near[:, :-d] |= bg[:, d:]
        g[near & (g > d)] = d
    g2 = (g * g).astype(np.float64)
    best = g2.copy()
    for d in range(1, R + 1):
        dd = float(d * d)
        best[d:] = np.minimum(best[d:], g2[:-d] + dd)
        best[:-d] = np.minimum(best[:-d], g2[d:] + dd)
    dist = np.sqrt(best[pad:pad + H, pad:pad + W])
    dist = np.minimum(dist, float(big))
    dist[~m] = 0.0
    return dist


def depth_edges(depth: np.ndarray, mask: np.ndarray, f_px: float, angle_deg: float,
                floor_mm: float) -> np.ndarray:
    """(H, W) bool: mask pixels next to a depth discontinuity (an occlusion boundary).

    Two 4-neighbour mask pixels are separated by a discontinuity when their camera
    depths differ by more than ``max(floor_mm, (z / f) * tan(angle))``: ``z / f`` is the
    pixel footprint in mm, so the threshold is the step a surface seen at obliquity
    ``angle`` makes across one pixel.  Both pixels are marked.  ``angle`` defaults to the
    fade cut-off (texels steeper than that already get zero weight), so only genuine
    occlusions (nose over cheek, jaw over neck, ear) are marked.
    """
    m = np.asarray(mask, bool)
    z = np.where(m, np.asarray(depth, np.float64), np.nan)
    thr = np.maximum(float(floor_mm), z / float(f_px) * math.tan(math.radians(float(angle_deg))))
    out = np.zeros(m.shape, bool)
    with np.errstate(invalid="ignore"):
        jv = np.abs(z[1:] - z[:-1]) > np.fmax(thr[1:], thr[:-1])
        jh = np.abs(z[:, 1:] - z[:, :-1]) > np.fmax(thr[:, 1:], thr[:, :-1])
    out[1:] |= jv
    out[:-1] |= jv
    out[:, 1:] |= jh
    out[:, :-1] |= jh
    return out & m


def visibility_eps_mm(sigma_geom_mm: float) -> float:
    """Depth-test tolerance eps = max(1 mm, 2 sigma_geom) (DESIGN 4.18, rec TEX-1)."""
    return max(float(_D["eps_floor_mm"]), float(_D["eps_sigma_factor"]) * float(sigma_geom_mm))


def check_gbuffer_on_mesh(gbuffer: Any, V: np.ndarray, tris: np.ndarray, tol_mm: float = GBUFFER_TOL_MM) -> None:
    """Raise ValueError unless a :class:`UVGBuffer` was built on the mesh ``(V, tris)``.

    Every masked texel's stored position must equal ``sum_k bary_k V[tris[face_id, k]]``
    within ``tol_mm``; this catches a G-buffer built on the kit's rest vertices
    (``uv_gbuffer(kit, S)``) being used with the fitted ``V``, and a ``tris`` whose first
    triangles are not the G-buffer's (extra occluder triangles may be appended).  A plain
    ``(pos, normal, mask, face_id)`` tuple carries no barycentrics and is not checked.
    """
    if not isinstance(gbuffer, UVGBuffer):
        return
    m = np.asarray(gbuffer.mask, bool)
    if not m.any():
        return
    V = np.asarray(V, np.float64)
    tris = np.asarray(tris, np.int64).reshape(-1, 3)
    fid = np.asarray(gbuffer.face_id)[m]
    if fid.min() < 0 or fid.max() >= len(tris):
        raise ValueError(f"gbuffer face_id reaches triangle {int(fid.max())} but tris has {len(tris)}: "
                         "the G-buffer was not built on this triangle list")
    tv = tris[fid]
    if tv.min() < 0 or tv.max() >= len(V):
        raise ValueError("tris index vertices outside V")
    b = np.asarray(gbuffer.bary, np.float64)[m]
    X = b[:, 0:1] * V[tv[:, 0]]
    X += b[:, 1:2] * V[tv[:, 1]]
    X += b[:, 2:3] * V[tv[:, 2]]
    err = float(np.max(np.abs(X - np.asarray(gbuffer.pos, np.float64)[m])))
    if not err <= float(tol_mm):
        raise ValueError(f"gbuffer positions differ from the mesh V by up to {err:.4g} mm (tolerance "
                         f"{float(tol_mm):g} mm): build the G-buffer on the mesh used for visibility, "
                         "uv_gbuffer(kit, S, V=V)")


# =========================================================================== weights
def view_weights(gbuffer: Any, V: np.ndarray, tris: np.ndarray, cam: Camera, image_shape: Sequence[int],
                 sigma_geom_mm: float = _D["sigma_geom_mm"],
                 fade: tuple[float, float] = (_D["fade_start_deg"], _D["fade_end_deg"]),
                 edge_erode_px: float = _D["edge_erode_px"], edge_ramp_px: float = _D["edge_ramp_px"],
                 frame_margin: float = _D["frame_margin"], *, cos_power: float = _D["cos_power"],
                 face_mask: np.ndarray | None = None, raster: RasterResult | None = None,
                 depth_edge_angle_deg: float | None = None,
                 return_terms: bool = False):
    """Per-texel weight of one view and the texel's image position (DESIGN 4.18, rec TEX-2, bl T3).

    ``w = vis * cos(theta)^p * fade(theta) * edge * frame`` with

    * **vis** (z-buffer visibility, rec TEX-1): the texel is in front of the camera,
      projects inside the image onto a rendered pixel of the mesh ``(V, tris)``
      (rasterised with :mod:`face3d.mesh.raster`, back faces kept so any surface
      occludes), and its camera depth exceeds the raster depth of that pixel (the
      pixel containing its pinhole projection) by at most
      ``eps = max(1 mm, 2 sigma_geom_mm)``;
    * **cos(theta)** = ``n . (C - p) / |C - p|`` with ``C`` the camera centre, clipped at 0
      and raised to ``p = cos_power`` (2, ↔️);
    * **fade**: 1 up to ``fade[0]`` = 60 deg, linear to 0 at ``fade[1]`` = 75 deg;
    * **edge**: ``clip((d - edge_erode_px) / edge_ramp_px, 0, 1)`` with ``d`` the exact
      Euclidean distance (px) of the texel's pixel to the boundary of the face mask in
      the image.  The face mask is the rendered mesh mask, intersected with
      ``face_mask`` when given (e.g. a skin segmentation that excludes hair or glasses;
      bl T3 occluders).  Pixels outside the image count as outside the mask.  So texels
      within 5 px of the silhouette get no weight and the weight ramps up over the next
      10 px (WBS WP-18 spec);
    * **opt-in occlusion edges** (🆕, off by default): with ``depth_edge_angle_deg`` set
      (the registered value is ``TEXTURE_DEFAULTS['depth_edge_angle_deg'].value`` = 75
      deg), pixels on a depth discontinuity (:func:`depth_edges`) are also removed from
      the face mask, so the same erosion and ramp apply at occlusion boundaries such as
      the nose side or the jaw over the neck (texture-extraction: "Occlusion edges are
      wrong first").  This extends the spec's edge term and is uncalibrated;
    * **frame**: 1 when the projection lies at least ``frame_margin * W`` px inside every
      image border (2 % of the width), else 0.

    Parameters
    ----------
    gbuffer : :class:`UVGBuffer` or ``(pos, normal, mask, face_id)`` built on ``V``
        (``uv_gbuffer(kit, S, V=V)``).  A :class:`UVGBuffer` is checked against
        ``(V, tris)`` with :func:`check_gbuffer_on_mesh` (ValueError when its positions
        are more than :data:`GBUFFER_TOL_MM` off, e.g. a rest-shape G-buffer used with
        the fitted mesh: visibility and sample positions would silently be wrong).
    V, tris : the mesh used for the z-buffer (mm), normally the fitted mesh and
        ``kit.triangles()`` (extra occluder triangles may be appended).
    cam : the solved camera of this photo; ``image_shape`` = (H, W[, C]) of the photo.
    raster : optional precomputed ``rasterize(V, tris, cam, W, H, cull_backfaces=False)``.
    return_terms : also return ``{'vis', 'cos', 'fade', 'edge', 'frame'}`` (S, S) maps.

    Returns
    -------
    ``(w (S, S) float64, uv_img (S, S, 2) float64)``: ``uv_img`` is ``cam.project`` of
    every texel in front of the camera (lens distortion ``cam.k`` applied, corner
    convention; NaN elsewhere), to be passed to :func:`sample_image`.  Visibility, edge
    and depth tests use the distortion-free pinhole projection of the rasteriser.
    """
    pos, normal, gmask, _fid = _unpack_gbuffer(gbuffer)
    H, W = int(image_shape[0]), int(image_shape[1])
    tris = np.asarray(tris, np.int64).reshape(-1, 3)
    V = np.asarray(V, np.float64)
    check_gbuffer_on_mesh(gbuffer, V, tris)
    f0, f1 = float(fade[0]), float(fade[1])
    if not (0.0 <= f0 <= f1 <= 90.0):
        raise ValueError("fade must satisfy 0 <= start <= end <= 90 degrees")
    if raster is None:
        raster = rasterize(V, tris, cam, width=W, height=H, cull_backfaces=False, near=_NEAR_MM)
    elif raster.mask.shape != (H, W):
        raise ValueError(f"raster shape {raster.mask.shape} does not match image_shape {(H, W)}")
    eps = visibility_eps_mm(sigma_geom_mm)
    S = gmask.shape
    w = np.zeros(S)
    uv_img = np.full(S + (2,), np.nan)
    terms = {k: np.zeros(S) for k in ("vis", "cos", "fade", "edge", "frame")}
    idx = np.flatnonzero(gmask)
    if idx.size == 0:
        return (w, uv_img, terms) if return_terms else (w, uv_img)
    X = pos.reshape(-1, 3)[idx]
    N = normal.reshape(-1, 3)[idx]
    Xc = cam.to_camera(X)
    z = Xc[:, 2]
    front = z > _NEAR_MM
    zz = np.where(front, z, 1.0)
    u0 = cam.f * Xc[:, 0] / zz + cam.cx
    v0 = cam.f * Xc[:, 1] / zz + cam.cy
    uvp = np.full((len(idx), 2), np.nan)
    if front.any():
        uvp[front] = cam.project(X[front])
    in_img = front & np.isfinite(u0) & np.isfinite(v0) & (u0 >= 0) & (u0 < W) & (v0 >= 0) & (v0 < H)
    col = np.clip(np.floor(np.where(in_img, u0, 0.0)), 0, W - 1).astype(np.int64)
    row = np.clip(np.floor(np.where(in_img, v0, 0.0)), 0, H - 1).astype(np.int64)
    hit = in_img & raster.mask[row, col]
    with np.errstate(invalid="ignore"):
        vis = hit & ((z - raster.depth[row, col]) <= eps)
    # Angle between the texel normal and the direction to the camera centre.
    to_c = cam.center[None, :] - X
    dist = np.linalg.norm(to_c, axis=1)
    cos = np.einsum("ij,ij->i", N, to_c) / np.maximum(dist, 1e-300)
    theta = np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))
    if f1 > f0:
        fade_w = np.clip((f1 - theta) / (f1 - f0), 0.0, 1.0)
    else:
        fade_w = (theta < f0).astype(np.float64)
    cos_w = np.clip(cos, 0.0, None) ** float(cos_power)
    # Edge term: distance to the face-mask boundary (silhouettes and occlusion boundaries).
    face = raster.mask.copy()
    if depth_edge_angle_deg is not None:
        face &= ~depth_edges(raster.depth, raster.mask, cam.f, depth_edge_angle_deg, eps)
    if face_mask is not None:
        fm = np.asarray(face_mask, bool)
        if fm.shape != (H, W):
            raise ValueError(f"face_mask must be (H, W) = {(H, W)}, got {fm.shape}")
        face &= fm
    erode, ramp = float(edge_erode_px), float(edge_ramp_px)
    dpx = bounded_distance_to_outside(face, int(math.ceil(erode + ramp)) + 1)
    if ramp > 0:
        edge_img = np.clip((dpx - erode) / ramp, 0.0, 1.0)
    else:
        edge_img = (dpx > erode).astype(np.float64)
    edge = np.where(in_img, edge_img[row, col], 0.0)
    mpx = float(frame_margin) * W
    with np.errstate(invalid="ignore"):
        frame = (front & (uvp[:, 0] >= mpx) & (uvp[:, 0] <= W - mpx)
                 & (uvp[:, 1] >= mpx) & (uvp[:, 1] <= H - mpx)).astype(np.float64)
    wk = vis * cos_w * fade_w * edge * frame
    w.reshape(-1)[idx] = wk
    uvf = uv_img.reshape(-1, 2)
    uvf[idx] = uvp
    if return_terms:
        for k, val in (("vis", vis.astype(np.float64)), ("cos", cos), ("fade", fade_w), ("edge", edge),
                       ("frame", frame)):
            terms[k].reshape(-1)[idx] = val
        return w, uv_img, terms
    return w, uv_img


# =========================================================================== sampling
def _unit_rgb(img: Any) -> np.ndarray:
    a = np.asarray(img)
    if a.dtype == np.uint8:
        a = a.astype(np.float64) / 255.0
    elif a.dtype == np.uint16:
        a = a.astype(np.float64) / 65535.0
    else:
        a = a.astype(np.float64)
    if a.ndim == 2:
        a = a[..., None]
    if a.ndim != 3:
        raise ValueError(f"image must be (H, W) or (H, W, C), got {a.shape}")
    c = a.shape[2]
    if c in (1, 2):          # grey or grey + alpha
        a = np.repeat(a[..., :1], 3, axis=2)
    elif c >= 3:             # RGB or RGBA (alpha dropped)
        a = a[..., :3]
    return a


def sample_image(img_srgb: Any, uv: np.ndarray) -> np.ndarray:
    """Bilinear sample of an sRGB-encoded image at ``uv`` (..., 2), decoded to linear light.

    ``img_srgb``: (H, W[, C]) uint8, uint16 or float in [0, 1]; grey is replicated to
    RGB and alpha dropped.  Corner convention: the value at ``(i + 0.5, j + 0.5)`` is
    pixel ``[j, i]`` exactly; positions between the outermost pixel centres and the
    image border are clamped to the edge pixels.  The encoded values are interpolated
    and then decoded with :func:`face3d.io.image_ops.srgb_to_linear` (WP-18 spec order).
    Returns (..., 3) float64; NaN where ``uv`` is not finite or outside ``[0, W] x [0, H]``.
    """
    img = _unit_rgb(img_srgb)
    H, W = img.shape[:2]
    uv = np.asarray(uv, np.float64)
    shp = uv.shape[:-1]
    u = uv[..., 0].reshape(-1)
    v = uv[..., 1].reshape(-1)
    with np.errstate(invalid="ignore"):
        ok = np.isfinite(u) & np.isfinite(v) & (u >= 0) & (u <= W) & (v >= 0) & (v <= H)
    x = np.clip(np.where(ok, u, 0.5) - 0.5, 0.0, W - 1.0)
    y = np.clip(np.where(ok, v, 0.5) - 0.5, 0.0, H - 1.0)
    x0 = np.minimum(np.floor(x).astype(np.int64), max(W - 2, 0))
    y0 = np.minimum(np.floor(y).astype(np.int64), max(H - 2, 0))
    x1 = np.minimum(x0 + 1, W - 1)
    y1 = np.minimum(y0 + 1, H - 1)
    fx = (x - x0)[:, None]
    fy = (y - y0)[:, None]
    top = img[y0, x0] * (1.0 - fx) + img[y0, x1] * fx
    bot = img[y1, x0] * (1.0 - fx) + img[y1, x1] * fx
    out = srgb_to_linear(top * (1.0 - fy) + bot * fy)
    out[~ok] = np.nan
    return out.reshape(shp + (3,))


# =========================================================================== gains
def _components(adj: np.ndarray) -> list[list[int]]:
    """Connected components (sorted lists) of a symmetric boolean adjacency matrix."""
    n = len(adj)
    seen = np.zeros(n, bool)
    comps = []
    for s in range(n):
        if seen[s]:
            continue
        stack, comp = [s], []
        seen[s] = True
        while stack:
            a = stack.pop()
            comp.append(a)
            for b in np.flatnonzero(adj[a] & ~seen):
                seen[b] = True
                stack.append(int(b))
        comps.append(sorted(comp))
    return comps


def solve_gains(samples: Sequence[np.ndarray], weights: Sequence[np.ndarray], *,
                min_views: int = _D["min_views"], floor: float = _D["gain_floor_linear"],
                ceiling: float = _D["gain_ceiling_linear"], return_info: bool = False):
    """Per-view, per-channel colour gains in log space (DESIGN 4.18, rec TEX-3).

    Model: ``log I_v(k) = log g_v + log a_k`` for view v and texel k (linear RGB).  Per
    channel, minimise ``sum_k sum_v w_vk (log I_v(k) - log g_v - log a_k)^2`` over texels
    seen by at least ``min_views`` = 2 views (weighted least squares), subject to
    ``sum_v log g_v = 0``.  The texel albedos are eliminated in closed form, leaving
    the n x n weighted-Laplacian system ``A x = b`` with
    ``A = sum_k (diag(w_k) - w_k w_k^T / W_k)``,
    ``b = sum_k (w_k * y_k - w_k (w_k . y_k) / W_k)``, ``W_k = sum_v w_vk``, which is
    solved with the gauge constraint by a KKT system.  If the view-overlap graph is
    disconnected the gauge is fixed per connected component (``sum log g = 0`` within
    each, hence also overall); a view sharing no texel keeps ``g = 1``.

    samples : n arrays (S, S, 3) of linear colour from :func:`sample_image` (NaN = none).
    weights : n arrays (S, S) from :func:`view_weights` (exclude a view by zeroing it).
    floor, ceiling : samples outside ``(floor, ceiling)`` (near-black, clipped) are not
        used (DESIGN 4.1 Q-CLIP for the ceiling).

    Returns ``g`` (n, 3); with ``return_info`` also ``{'n_texels': [3], 'components':
    [[...] per channel], 'rms_log_residual': [3]}``.  Divide the samples of view v by
    ``g[v]`` to level them.  Only relative gains are observable: absolute colour needs
    a chart (TEX-6).
    """
    Y = np.stack([np.asarray(s, np.float64) for s in samples])
    Wt = np.stack([np.asarray(w, np.float64) for w in weights])
    n = len(Y)
    if Y.ndim != 4 or Y.shape[-1] != 3 or Wt.shape != Y.shape[:-1]:
        raise ValueError("samples must be n x (S, S, 3) and weights n x (S, S)")
    if int(min_views) < 2:
        raise ValueError("min_views must be >= 2 (gains are relative)")
    Y = Y.reshape(n, -1, 3)
    Wt = Wt.reshape(n, -1)
    g = np.ones((n, 3))
    info = {"n_texels": [], "components": [], "rms_log_residual": []}
    for c in range(3):
        I = Y[:, :, c]
        with np.errstate(invalid="ignore"):
            valid = np.isfinite(I) & (I > floor) & (I < ceiling) & np.isfinite(Wt) & (Wt > 0)
        a = np.where(valid, Wt, 0.0)
        use = (a > 0).sum(axis=0) >= int(min_views)
        a = a[:, use]
        y = np.log(np.where(valid[:, use], I[:, use], 1.0))
        Wk = a.sum(axis=0)
        info["n_texels"].append(int(use.sum()))
        if a.shape[1] == 0:
            info["components"].append([[v] for v in range(n)])
            info["rms_log_residual"].append(float("nan"))
            continue
        aw = a / Wk
        A = np.diag(a.sum(axis=1)) - aw @ a.T
        ay = a * y
        b = ay.sum(axis=1) - a @ (ay.sum(axis=0) / Wk)
        comps = _components((a > 0).astype(np.float64) @ (a > 0).T.astype(np.float64) > 0)
        C = np.zeros((len(comps), n))
        for r, comp in enumerate(comps):
            C[r, comp] = 1.0
        K = np.zeros((n + len(comps), n + len(comps)))
        K[:n, :n] = A
        K[:n, n:] = C.T
        K[n:, :n] = C
        rhs = np.concatenate([b, np.zeros(len(comps))])
        try:
            sol = np.linalg.solve(K, rhs)
        except np.linalg.LinAlgError:
            sol = np.linalg.lstsq(K, rhs, rcond=None)[0]
        x = sol[:n]
        g[:, c] = np.exp(x)
        alpha = ((a * (y - x[:, None])).sum(axis=0)) / Wk
        r = y - x[:, None] - alpha[None, :]
        info["components"].append(comps)
        info["rms_log_residual"].append(float(np.sqrt((a * r * r).sum() / max(a.sum(), 1e-300))))
    return (g, info) if return_info else g


# =========================================================================== gates
def _finding(code: str, severity: str, value: Any, threshold: Any, action: str, source: str, badge: str,
             view: int | None = None, photo_id: str | None = None, detail: dict | None = None) -> dict:
    """A finding dict with the fields of :class:`face3d.qa.checks.Finding` plus ``view``."""
    return {"code": code, "severity": severity, "value": value, "threshold": threshold, "action": action,
            "msg_key": f"texture.{code}", "fix_key": f"texture.{code}.fix", "source": source, "badge": badge,
            "photo_id": photo_id, "view": view, "detail": detail or {}}


def _view_flag_sets(view_flags: Any) -> dict[int, set]:
    """``{view: {lower-case flag, ...}}`` from a per-view sequence or a mapping."""
    out: dict[int, set] = {}
    if view_flags is None:
        return out
    items = view_flags.items() if isinstance(view_flags, Mapping) else enumerate(view_flags)
    for v, flags in items:
        if flags is None:
            continue
        if isinstance(flags, str):
            flags = (flags,)
        out[int(v)] = {str(f).strip().lower() for f in flags}
    return out


def _primary_cluster(clusters: Sequence[Any]) -> Any:
    counts: dict = {}
    first: dict = {}
    for i, c in enumerate(clusters):
        if c is None:
            continue
        counts[c] = counts.get(c, 0) + 1
        first.setdefault(c, i)
    if not counts:
        return None
    return max(counts, key=lambda c: (counts[c], -first[c]))


class GateFindings(list):
    """The finding dicts returned by :func:`texture_gates`: a plain ``list`` (compares
    equal to a list of the same dicts) that also carries ``n_views``, the number of
    views whose rights the gates checked (None when no view count was known).
    :func:`face3d.texture.blend.build_texture` refuses colours for a different number of
    views.  Every finding's ``detail`` also holds ``n_views``, so the count survives
    ``list(...)`` or concatenation as long as one finding is present."""

    n_views: int | None = None


def _view_count(n_views: int | None, view_flags: Any, photo_ids: Any,
                date_clusters: Any) -> dict[str, int]:
    """``{source: count}`` of every argument that states the number of views."""
    counts: dict[str, int] = {}
    if n_views is not None:
        counts["n_views"] = int(n_views)
    if view_flags is not None and not isinstance(view_flags, (Mapping, str, bytes)):
        counts["view_flags"] = len(view_flags)
    if photo_ids is not None:
        counts["photo_ids"] = len(photo_ids)
    if date_clusters is not None:
        counts["date_clusters"] = len(date_clusters)
    return counts


def texture_gates(consent_record: policy.ConsentRecord | None, rights_basis: Any,
                  reproj_median_px: float | None, reproj_max_px: float | None,
                  view_flags: Any = None, *, now: datetime | None = None,
                  date_clusters: Sequence[Any] | None = None, primary_cluster: Any = None,
                  photo_ids: Sequence[str] | None = None, n_views: int | None = None,
                  median_max_px: float = _D["reproj_median_max_px"],
                  max_max_px: float = _D["reproj_max_max_px"]) -> GateFindings:
    """Texture gates (DESIGN 4.18, 3.3 data classes, bl T2, eth F7): a list of finding dicts.

    Blocking findings (texture must not be projected, baked, packed or exported):

    * ``T-SCOPE`` / ``T-CONSENT`` / ``T-RIGHTS``: :func:`face3d.core.policy.check`
      ``('texture', ...)`` denies, i.e. no consent record, the TEXTURE scope is missing,
      the record expired, a minor without guardian consent, or a view's
      ``rights_basis`` is ``'unknown'`` / not a recognised basis (F7; fails closed).
      Texture is a LIKENESS_ASSET (eth: "fitting extracts facts; texture copies
      pixels"), so a single unknown-rights photo blocks the stage.  A view with *no*
      rights entry is unknown too: when the number of views is known (``n_views``, or
      the length of a per-view ``view_flags`` sequence, ``photo_ids`` or
      ``date_clusters``) and a per-view ``rights_basis`` list has a different length,
      ``T-RIGHTS`` blocks and names the views it does not cover in
      ``detail['uncovered_views']`` (a list is never broadcast; only a single string
      stands for every view).
    * ``T-VIEW-COUNT``: the arguments that state the number of views disagree (fail
      closed: the per-view lists cannot be aligned).
    * ``T-REPROJ-MEDIAN`` / ``T-REPROJ-MAX``: landmark reprojection median > 1.5 px or
      max > 3 px (bl T2); ``T-REPROJ-UNKNOWN`` when either statistic is missing.

    Non-blocking: ``T-VIEW-EXCLUDED`` (severity ``warn``, action ``exclude_texture``) for
    each view flagged ``filtered``, ``retouched``, ``warped``, ``clipped`` or
    ``other_date_cluster`` in ``view_flags``, or (with ``date_clusters``, one cluster id
    per view, None = unknown) whose date cluster differs from ``primary_cluster``
    (default: the most frequent cluster, ties to the earliest view).  Such views never
    feed albedo (DESIGN 4.18) but do not stop the stage.

    rights_basis : one string per view (or a single string for all views).
    view_flags : sequence (per view) or mapping ``{view: flags}`` of flag strings.
    n_views : the number of views that will feed the texture (optional; see above).
        Without any view count the ``rights_basis`` list defines the views.
    now : evaluation time for consent expiry (default: current UTC time).

    Returns a :class:`GateFindings` list whose ``n_views`` is the number of views the
    rights were checked for (:func:`face3d.texture.blend.build_texture` requires the
    same number of colour views).  Each dict has the :class:`face3d.qa.checks.Finding`
    fields (``code``, ``severity``, ``value``, ``threshold``, ``action``, ``msg_key``,
    ``fix_key``, ``source``, ``badge``, ``photo_id``, ``detail``) plus ``view`` (int or
    None); ``detail['n_views']`` repeats the checked view count.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    if view_flags is not None and not isinstance(view_flags, (Mapping, str, bytes)):
        view_flags = list(view_flags)
    counts = _view_count(n_views, view_flags, photo_ids, date_clusters)
    broadcast = isinstance(rights_basis, (str, bytes))
    given: list = [] if rights_basis is None else ([rights_basis] if broadcast else list(rights_basis))
    if counts:
        n: int | None = max(counts.values())
    elif rights_basis is not None and not broadcast:
        n = len(given)
    else:
        n = None
    # Per-view rights: a single string stands for every view; a list is never broadcast.
    rights = given * (n if n is not None else 1) if broadcast else given
    pid = (lambda v: None if photo_ids is None or v is None or v >= len(photo_ids) else str(photo_ids[v]))
    findings: list[dict] = []
    src = "DESIGN 4.18 / 3.3 (LIKENESS_ASSET needs TEXTURE + rights_basis != unknown); core.policy.check"

    if len(set(counts.values())) > 1:
        findings.append(_finding("T-VIEW-COUNT", "block", dict(counts), "equal", "ask",
                                 src + " (eth F7: per-view rights cannot be aligned, fail closed)", _BRAIN,
                                 detail={"counts": dict(counts)}))

    gate = policy.check("texture", consent_record, rights_basis=tuple(rights), now=now)
    if gate.missing:
        findings.append(_finding("T-SCOPE", "block", list(gate.missing), "TEXTURE", "ask",
                                 src + " (eth F1, scopes)", "\U0001F4C4"))
    for reason in gate.reasons:
        if "(F7)" not in reason:
            findings.append(_finding("T-CONSENT", "block", reason, None, "ask", src, "\U0001F4C4",
                                     detail={"reason": reason}))
    n_cov = len(rights) if n is None else min(len(rights), n)
    invalid = [i for i in range(n_cov) if not (isinstance(rights[i], str) and rights[i] in policy.RIGHTS_BASES)]
    uncovered = list(range(len(rights), n)) if n is not None and len(rights) < n else []
    extra = len(rights) - n if n is not None and len(rights) > n else 0
    f7 = [r for r in gate.reasons if "(F7)" in r]
    if f7 or invalid or uncovered or extra:
        views = sorted(invalid + uncovered)
        reason = f7[0] if f7 else "rights basis unknown or invalid (F7)"
        if uncovered:
            reason += f"; no rights basis for view(s) {uncovered} of {n}"
        if extra:
            reason += f"; {len(rights)} rights entries for {n} views (cannot be aligned)"
        value = [rights[i] if i < len(rights) else "missing" for i in views] or "missing"
        findings.append(_finding("T-RIGHTS", "block", value, sorted(policy.RIGHTS_BASES), "ask",
                                 src + " (eth F7)", _BRAIN,
                                 detail={"views": views, "uncovered_views": uncovered, "n_rights": len(rights),
                                         "reason": reason}))

    src_t2 = "DESIGN 4.18 / bl T2 (texture-extraction)"
    for code, val, thr, key in (("T-REPROJ-MEDIAN", reproj_median_px, median_max_px, "reproj_median_max_px"),
                                ("T-REPROJ-MAX", reproj_max_px, max_max_px, "reproj_max_max_px")):
        if val is None or not np.isfinite(float(val)):
            findings.append(_finding("T-REPROJ-UNKNOWN", "block", None, float(thr), "ask",
                                     src_t2 + ": reprojection unknown, fail closed", _BRAIN,
                                     detail={"statistic": code}))
        elif float(val) > float(thr):
            findings.append(_finding(code, "block", float(val), float(thr), "ask",
                                     src_t2, TEXTURE_DEFAULTS[key].badge))

    flags = _view_flag_sets(view_flags)
    if date_clusters is not None:
        prim = primary_cluster if primary_cluster is not None else _primary_cluster(date_clusters)
        for v, c in enumerate(date_clusters):
            if c is not None and prim is not None and c != prim:
                flags.setdefault(v, set()).add("other_date_cluster")
    for v in sorted(flags):
        hit = sorted(f for f in flags[v] if f in EXCLUDE_FLAGS)
        if hit:
            findings.append(_finding("T-VIEW-EXCLUDED", "warn", hit, list(EXCLUDE_FLAGS), "exclude_texture",
                                     "DESIGN 4.18 (views flagged filtered, retouched, warped or clipped, or "
                                     "from another date cluster, never feed albedo); DESIGN 4.1 Q-PROCESS, "
                                     "Q-RETOUCH, Q-CLIP, Q-DATES", _BRAIN, view=v, photo_id=pid(v),
                                     detail={"flags": hit}))
    out = GateFindings(findings)
    out.n_views = n
    for f in out:
        f["detail"]["n_views"] = n
    return out


def texture_blocked(findings: Iterable[Mapping]) -> bool:
    """True when any finding blocks the texture stage."""
    return any(f.get("severity") == "block" for f in findings)


def excluded_views(findings: Iterable[Mapping]) -> list[int]:
    """Sorted view indices that must not feed albedo (``action == 'exclude_texture'``)."""
    return sorted({int(f["view"]) for f in findings
                   if f.get("action") == "exclude_texture" and f.get("view") is not None})
