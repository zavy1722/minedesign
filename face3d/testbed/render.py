"""Numpy renders of test-bed subjects: shaded sRGB images, depth, masks and landmark projections (WP-11).

Implements DESIGN 7.2 "Images" ("a numpy rasteriser draws depth, masks,
Lambert-shaded textured images and blurred edges for the pixel steps") and
source 3 of DESIGN 2.5 (tests use synthetic arrays from ``testbed.render``).
The rasterisation itself is :func:`face3d.mesh.raster.rasterize` (WP-02).

Conventions
-----------
* World: float64 mm in the kit's head frame (DESIGN 3.1).  Cameras are
  :class:`face3d.geometry.camera.Camera` (OpenCV: X_c = R X + t, +y down,
  +z forward); radial distortion ``k`` is ignored by the rasteriser.
* Image coordinates are continuous with the origin at the top-left *corner*;
  pixel ``[j, i]`` (row j, column i) has its centre at ``(i + 0.5, j + 0.5)``
  (DESIGN 3.1, same as :mod:`face3d.mesh.raster`).
* ``scale_resolution = s`` renders a ``W' x H'`` image with ``W' = round(W s)``,
  ``H' = round(H s)`` and intrinsics scaled by the corner convention
  (``f' = f W'/W``, ``c_x' = c_x W'/W``, ``c_y' = c_y H'/H``), so that
  ``u' = u W'/W`` and ``v' = v H'/H`` exactly whenever ``W'/W = H'/H``
  (always true when ``W s`` and ``H s`` are integers); :func:`scale_camera`.
* Colour: albedos are given as sRGB-encoded values in [0, 1]; shading
  (Lambert, :func:`face3d.mesh.raster.render_lambert`), background and blur are
  computed in linear light (IEC 61966-2-1, :mod:`face3d.io.image_ops`), and the
  returned image is sRGB-encoded float32 in [0, 1].  Sensor noise
  (``noise_sd``) is added to the encoded values, then clipped.
* ``depth`` is camera-frame z in mm (``inf`` on background), ``tri_id`` the
  index into ``kit.triangles()`` (-1 on background), ``bary`` the
  perspective-correct barycentrics; they are never blurred.

Procedural albedo (WP-11 spec; colours 🆕, a rendering convention, not measured
skin data): base skin sRGB (0.78, 0.60, 0.52), lips (0.65, 0.35, 0.35) inside
the vermilion ellipse spanned by ch_L, ch_R, ls, li around sto, a brow band
(0.35, 0.25, 0.20) within 3-5 mm of the brow_inner-brow_outer segments of the
kit's ``legacy_synthetic`` embeddings, and a slight (<= 5 %) deterministic
low-frequency multiplicative variation.  Everything is evaluated per pixel at
the rendered surface point of the deformed mesh, so features follow the
subject.  Missing landmarks simply drop the corresponding feature.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from ..core.config import Default, register_defaults
from ..geometry.camera import Camera
from ..io.image_ops import linear_to_srgb, srgb_to_linear
from ..mesh.raster import RasterResult, rasterize, render_lambert

__all__ = [
    "RenderedView", "render_view", "project_landmarks", "render_masks", "scale_camera",
    "procedural_albedo", "surface_points", "vertex_normals", "face_centre", "gaussian_blur",
    "RENDER_DEFAULTS", "SKIN_RGB", "LIPS_RGB", "BROW_RGB", "FACE_CENTRE_IDS",
]

_NEW = "\U0001F195"
_WP = "WBS WP-11 spec (test-bed rendering convention)"
_THIS = "WP-11 implementation choice (test-bed rendering; not in the spec)"

RENDER_DEFAULTS = register_defaults("testbed.render", {
    "ambient": Default(0.25, _NEW, _WP + "; same as face3d.mesh.raster.DEFAULT_AMBIENT (WP-02)", "",
                       (0.0, 1.0)),
    "lip_edge_lo": Default(0.85, _NEW, _THIS + ": lip ellipse soft edge, start (normalised radius^2)", "",
                           (0.0, 2.0)),
    "lip_edge_hi": Default(1.15, _NEW, _THIS + ": lip ellipse soft edge, end", "", (0.0, 4.0)),
    "lip_front_margin_mm": Default(12.0, _NEW, _THIS + ": lips only within this depth behind the corners", "mm",
                                   (0.0, 100.0)),
    "brow_core_mm": Default(3.0, _NEW, _THIS + ": brow band full colour within this distance of the segment",
                            "mm", (0.0, 50.0)),
    "brow_edge_mm": Default(5.0, _NEW, _THIS + ": brow band fades out at this distance", "mm", (0.0, 50.0)),
    "albedo_variation": Default(0.03, _NEW, _WP + " ('slight low-frequency variation'); amplitude", "",
                                (0.0, 0.5)),
    "label_threshold": Default(0.5, _NEW, _THIS + ": per-pixel lips/brow weight above which a pixel is "
                               "labelled lips/brow", "", (0.0, 1.0)),
})
_R = {k: RENDER_DEFAULTS[k].value for k in RENDER_DEFAULTS}

#: Procedural albedo colours, sRGB-encoded (WP-11 spec; 🆕 rendering convention).
SKIN_RGB = (0.78, 0.60, 0.52)
LIPS_RGB = (0.65, 0.35, 0.35)
BROW_RGB = (0.35, 0.25, 0.20)

#: Key light direction (travel direction, world frame) shared with WP-02's shader.
DEFAULT_LIGHT_DIR = (0.3, -0.5, -0.8)

#: Anatomical ids whose centroid is the face centre used to aim cameras (eyes, nose, mouth).
FACE_CENTRE_IDS: tuple[str, ...] = ("en_L", "en_R", "ex_L", "ex_R", "n", "prn", "sn", "sto", "ch_L", "ch_R")

#: Regions never counted as skin in :func:`render_masks` (hair-bearing or out of the face
#: in a real photo; test-bed convention 🆕).
SKIN_EXCLUDED_REGIONS: tuple[str, ...] = ("scalp", "neck")


# =========================================================================== data class
@dataclass
class RenderedView:
    """One rendered view (WP-11).

    image : (H, W, 3) float32 sRGB-encoded in [0, 1].
    depth : (H, W) float64 camera z, mm (inf on background).
    mask : (H, W) bool, surface pixels.
    tri_id : (H, W) int64 index into ``kit.triangles()`` (-1 on background).
    bary : (H, W, 3) perspective-correct barycentrics of the visible point.
    camera : the camera of *this* image (scaled intrinsics when rendered with
        ``scale_resolution != 1``); use it with :func:`project_landmarks`.
    meta : render settings (light, ambient, blur, noise, scale, albedo mode).
    """

    image: np.ndarray
    depth: np.ndarray
    mask: np.ndarray
    tri_id: np.ndarray
    bary: np.ndarray
    camera: Camera
    meta: dict = field(default_factory=dict)

    @property
    def height(self) -> int:
        return int(self.mask.shape[0])

    @property
    def width(self) -> int:
        return int(self.mask.shape[1])

    def raster(self) -> RasterResult:
        """The raster buffers as a :class:`face3d.mesh.raster.RasterResult`."""
        return RasterResult(depth=self.depth, tri_id=self.tri_id, bary=self.bary, mask=self.mask)

    def depth_at(self, uv: np.ndarray) -> np.ndarray:
        """Raster depth at the pixels containing ``uv`` (N, 2) (inf outside the image / on background)."""
        uv = np.asarray(uv, float).reshape(-1, 2)
        out = np.full(len(uv), np.inf)
        with np.errstate(invalid="ignore"):
            i = np.floor(uv[:, 0])
            j = np.floor(uv[:, 1])
            ok = np.isfinite(i) & np.isfinite(j) & (i >= 0) & (j >= 0) & (i < self.width) & (j < self.height)
        out[ok] = self.depth[j[ok].astype(np.int64), i[ok].astype(np.int64)]
        return out


# =========================================================================== helpers
def scale_camera(camera: Camera, scale: float) -> Camera:
    """Camera of a ``round(W s) x round(H s)`` image with corner-convention intrinsics.

    ``f' = f W'/W``, ``c_x' = c_x W'/W``, ``c_y' = c_y H'/H`` (DESIGN 3.1 resize map
    ``u' = u W'/W``).  Extrinsics and ``k`` are copied.  ``scale = 1`` returns a copy.
    """
    s = float(scale)
    if not (s > 0.0 and math.isfinite(s)):
        raise ValueError(f"scale_resolution must be a positive finite number, got {scale!r}")
    cam = camera.copy()
    if s == 1.0:
        return cam
    W2 = max(1, int(round(camera.width * s)))
    H2 = max(1, int(round(camera.height * s)))
    sx = W2 / float(camera.width)
    sy = H2 / float(camera.height)
    return Camera(f=camera.f * sx, cx=camera.cx * sx, cy=camera.cy * sy, width=W2, height=H2,
                  R=camera.R.copy(), t=camera.t.copy(), k=camera.k.copy())


def vertex_normals(V: np.ndarray, tris: np.ndarray) -> np.ndarray:
    """Unit area-weighted vertex normals of the triangle mesh (V, tris)."""
    V = np.asarray(V, float)
    t = np.asarray(tris, np.int64)
    fn = np.cross(V[t[:, 1]] - V[t[:, 0]], V[t[:, 2]] - V[t[:, 0]])
    n = np.zeros_like(V)
    for k in range(3):
        for a in range(3):
            n[:, a] += np.bincount(t[:, k], weights=fn[:, a], minlength=len(V))
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    return n / np.where(ln > 0, ln, 1.0)


def surface_points(res: RasterResult | RenderedView, V: np.ndarray, tris: np.ndarray) -> np.ndarray:
    """(H, W, 3) world point of every rendered pixel (NaN on background)."""
    V = np.asarray(V, float)
    out = np.full(res.bary.shape, np.nan)
    m = res.mask
    if m.any():
        tv = np.asarray(tris, np.int64)[res.tri_id[m]]
        b = res.bary[m]
        out[m] = b[:, 0:1] * V[tv[:, 0]] + b[:, 1:2] * V[tv[:, 1]] + b[:, 2:3] * V[tv[:, 2]]
    return out


def face_centre(kit, V: np.ndarray | None = None, scheme: str = "anatomical44") -> np.ndarray:
    """Centroid (3,) of the eye, nose and mouth landmarks (:data:`FACE_CENTRE_IDS`) on ``V``.

    Used to aim test-bed cameras; falls back to the centroid of the face-hemisphere
    vertices (rest z > 0) when the kit has no ``anatomical44`` embedding.
    """
    Vx = kit.vertices if V is None else np.asarray(V, float)
    pts = kit.landmarks.get(scheme)
    if pts is not None and all(n in pts for n in FACE_CENTRE_IDS):
        return kit.landmark_positions(scheme, Vx, list(FACE_CENTRE_IDS)).mean(axis=0)
    sel = kit.vertices[:, 2] > 0.0
    return Vx[sel].mean(axis=0) if sel.any() else Vx.mean(axis=0)


def _smoothstep(e0: float, e1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _lm(kit, V, names, scheme):
    pts = kit.landmarks.get(scheme)
    if pts is None or any(n not in pts for n in names):
        return None
    return kit.landmark_positions(scheme, V, list(names))


def _seg_dist(P: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    ab = b - a
    L2 = float(ab @ ab)
    t = np.zeros(len(P)) if L2 <= 0 else np.clip((P - a) @ ab / L2, 0.0, 1.0)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)


def feature_weights(kit, V: np.ndarray, X: np.ndarray) -> dict[str, np.ndarray]:
    """Per-point lips and brow weights in [0, 1] for world points ``X`` (M, 3) on the mesh ``V``.

    lips: normalised vermilion ellipse ``e = (dx/a)^2 + (dy/h)^2`` centred at sto, with
    ``a`` half the ch_L-ch_R distance, ``h = ls.y - sto.y`` above and ``sto.y - li.y``
    below the stomion; weight ``1 - smoothstep(0.85, 1.15, e)``, only within 12 mm
    behind the mouth corners (front of the face).  brows: ``1 - smoothstep(3, 5, d)``
    with ``d`` the distance to the brow_inner-brow_outer segment of each side.
    """
    X = np.asarray(X, float).reshape(-1, 3)
    out = {"lips": np.zeros(len(X)), "brows": np.zeros(len(X))}
    P = _lm(kit, V, ["ch_L", "ch_R", "ls", "sto", "li"], "anatomical44")
    if P is not None:
        chL, chR, ls, sto, li = P
        a = 0.5 * float(np.linalg.norm(chL - chR))
        h_up = max(float(ls[1] - sto[1]), 1e-3)
        h_lo = max(float(sto[1] - li[1]), 1e-3)
        cx = 0.5 * float(chL[0] + chR[0])
        dy = X[:, 1] - sto[1]
        h = np.where(dy >= 0, h_up, h_lo)
        e = ((X[:, 0] - cx) / max(a, 1e-3)) ** 2 + (dy / h) ** 2
        front = X[:, 2] > min(chL[2], chR[2]) - _R["lip_front_margin_mm"]
        out["lips"] = (1.0 - _smoothstep(_R["lip_edge_lo"], _R["lip_edge_hi"], e)) * front
    B = _lm(kit, V, ["brow_inner_L", "brow_outer_L", "brow_inner_R", "brow_outer_R"], "legacy_synthetic")
    if B is not None:
        d = np.minimum(_seg_dist(X, B[0], B[1]), _seg_dist(X, B[2], B[3]))
        out["brows"] = 1.0 - _smoothstep(_R["brow_core_mm"], _R["brow_edge_mm"], d)
    return out


def procedural_albedo(kit, V: np.ndarray, X: np.ndarray) -> np.ndarray:
    """sRGB-encoded procedural albedo (M, 3) at world points ``X`` on the mesh ``V`` (see module doc).

    The low-frequency variation is ``1 + A (sin(2 pi x/70 + 0.3) cos(2 pi y/90 + 1.1)
    + 0.6 sin(2 pi z/110 + 2.0))`` with ``A = 0.03`` (deterministic, no RNG; 🆕).
    """
    X = np.asarray(X, float).reshape(-1, 3)
    w = feature_weights(kit, V, X)
    col = np.broadcast_to(np.asarray(SKIN_RGB, float), (len(X), 3)).copy()
    col += w["lips"][:, None] * (np.asarray(LIPS_RGB) - col)
    col += w["brows"][:, None] * (np.asarray(BROW_RGB) - col)
    A = _R["albedo_variation"]
    var = 1.0 + A * (np.sin(2 * np.pi * X[:, 0] / 70.0 + 0.3) * np.cos(2 * np.pi * X[:, 1] / 90.0 + 1.1)
                     + 0.6 * np.sin(2 * np.pi * X[:, 2] / 110.0 + 2.0))
    return np.clip(col * var[:, None], 0.0, 1.0)


def gaussian_blur(img: np.ndarray, sigma_px: float) -> np.ndarray:
    """Separable Gaussian blur (radius ceil(3 sigma), edge-replicated borders) of an (H, W[, C]) image."""
    s = float(sigma_px)
    a = np.asarray(img, np.float64)
    if s <= 0.0:
        return a.copy()
    r = max(1, int(math.ceil(3.0 * s)))
    x = np.arange(-r, r + 1, dtype=np.float64)
    k = np.exp(-0.5 * (x / s) ** 2)
    k /= k.sum()
    pad = [(r, r), (0, 0)] + [(0, 0)] * (a.ndim - 2)
    p = np.pad(a, pad, mode="edge")
    out = sum(k[i] * p[i:i + a.shape[0]] for i in range(2 * r + 1))
    pad = [(0, 0), (r, r)] + [(0, 0)] * (a.ndim - 2)
    p = np.pad(out, pad, mode="edge")
    return sum(k[i] * p[:, i:i + a.shape[1]] for i in range(2 * r + 1))


def _albedo_linear(albedo: Any, kit, V: np.ndarray, tris: np.ndarray, res: RasterResult) -> np.ndarray:
    """Per-pixel *linear* albedo (n_mask, 3) for the mask pixels of ``res``."""
    m = res.mask
    n = int(m.sum())
    if isinstance(albedo, str):
        if albedo != "procedural":
            raise ValueError(f"albedo must be 'procedural', None, (3,) or (n_vertices, 3); got {albedo!r}")
        X = surface_points(res, V, tris)[m]
        return srgb_to_linear(procedural_albedo(kit, V, X))
    if albedo is None:
        return np.ones((n, 3))
    a = np.asarray(albedo, float)
    if a.shape == (3,):
        return np.broadcast_to(srgb_to_linear(a), (n, 3)).copy()
    if a.shape == (len(V), 3):
        lin = srgb_to_linear(a)
        tv = tris[res.tri_id[m]]
        b = res.bary[m]
        return b[:, 0:1] * lin[tv[:, 0]] + b[:, 1:2] * lin[tv[:, 1]] + b[:, 2:3] * lin[tv[:, 2]]
    raise ValueError("albedo must be 'procedural', None, (3,) or (n_vertices, 3)")


# =========================================================================== render
def render_view(V: np.ndarray, kit, camera: Camera, *, albedo: Any = "procedural",
                light_dir: Sequence[float] = DEFAULT_LIGHT_DIR, ambient: float = _R["ambient"],
                blur_px: float = 0.0, noise_sd: float = 0.0, rng: np.random.Generator | None = None,
                scale_resolution: float = 1.0, background: Sequence[float] = (0.0, 0.0, 0.0),
                cull_backfaces: bool = True) -> RenderedView:
    """Render the mesh ``(V, kit.triangles())`` seen by ``camera`` (DESIGN 7.2 "Images"; WP-11).

    V : (n, 3) vertex positions in the kit's topology (mm, head frame).
    camera : full-resolution camera; with ``scale_resolution = s`` the image is
        ``round(W s) x round(H s)`` and ``RenderedView.camera`` is the scaled camera
        (:func:`scale_camera`).
    albedo : ``'procedural'`` (default, see module docstring), None (white), an sRGB
        (3,) colour or (n, 3) per-vertex sRGB colours.
    light_dir : direction in which the key light travels, world frame (default
        (0.3, -0.5, -0.8): from the front, above and the subject's right; WP-02).
    ambient : ambient fraction of the Lambert term (0.25).
    blur_px : Gaussian blur sigma in pixels of the *output* image (linear light;
        depth, mask, tri_id and bary are not blurred).
    noise_sd : SD of additive Gaussian noise on the sRGB-encoded values; needs ``rng``.
    background : sRGB background colour.
    cull_backfaces : draw only front-facing triangles (exact for the closed,
        outward-oriented template; faster).

    Shading: ``linear = albedo_lin * (ambient + (1 - ambient) max(0, n . l))`` via
    :func:`face3d.mesh.raster.render_lambert` (two-sided normals), then blur, sRGB
    encoding, noise and clipping to [0, 1].
    """
    if noise_sd < 0 or blur_px < 0:
        raise ValueError("noise_sd and blur_px must be >= 0")
    if noise_sd > 0 and rng is None:
        raise ValueError("noise_sd > 0 needs a seeded rng (determinism)")
    V = np.asarray(V, float)
    if V.shape != kit.vertices.shape:
        raise ValueError(f"V must have the kit's shape {kit.vertices.shape}, got {V.shape}")
    cam = scale_camera(camera, scale_resolution)
    tris = kit.triangles()
    res = rasterize(V, tris, cam, cull_backfaces=cull_backfaces)
    H, W = res.mask.shape
    bg = srgb_to_linear(np.asarray(background, float).reshape(3))
    lin = np.empty((H, W, 3))
    lin[...] = bg
    m = res.mask
    if m.any():
        shade = render_lambert(res, V, tris, cam, albedo=None, light_dir_world=tuple(light_dir),
                               ambient=float(ambient))[..., 0].astype(np.float64)
        lin[m] = _albedo_linear(albedo, kit, V, tris, res) * shade[m][:, None]
    if blur_px > 0:
        lin = gaussian_blur(lin, blur_px)
    img = linear_to_srgb(np.clip(lin, 0.0, 1.0))
    if noise_sd > 0:
        img = img + rng.normal(scale=float(noise_sd), size=img.shape)
    img = np.clip(img, 0.0, 1.0).astype(np.float32)
    meta = {"albedo": albedo if isinstance(albedo, str) or albedo is None else "array",
            "light_dir": [float(x) for x in light_dir], "ambient": float(ambient), "blur_px": float(blur_px),
            "noise_sd": float(noise_sd), "scale_resolution": float(scale_resolution),
            "full_resolution_wh": [int(camera.width), int(camera.height)], "colour": "sRGB",
            "kit_id": getattr(kit, "id", None)}
    return RenderedView(image=img, depth=res.depth, mask=res.mask, tri_id=res.tri_id, bary=res.bary,
                        camera=cam, meta=meta)


def segment_hits(V: np.ndarray, tris: np.ndarray, origin: np.ndarray, X: np.ndarray,
                 end_tol_mm: float | np.ndarray = 0.0) -> np.ndarray:
    """True for each point of ``X`` (N, 3) whose segment from ``origin`` is blocked by a triangle.

    Moller-Trumbore ray/triangle test on closed triangles (edges count).  A hit
    counts when it lies strictly between the origin and the point and more than
    ``end_tol_mm`` (scalar or per point; plus a relative 1e-9) before the point, so the
    triangles through the point itself never block it.  Independent of the
    rasteriser: an exact geometric occlusion oracle for tests and labels.
    """
    V = np.asarray(V, float)
    t = np.asarray(tris, np.int64)
    o = np.asarray(origin, float).reshape(3)
    X = np.asarray(X, float).reshape(-1, 3)
    tol = np.broadcast_to(np.asarray(end_tol_mm, float), (len(X),))
    A = V[t[:, 0]]
    e1 = V[t[:, 1]] - A
    e2 = V[t[:, 2]] - A
    s = o - A
    q = np.cross(s, e1)                     # independent of the ray direction
    tq = np.einsum("ij,ij->i", e2, q)
    out = np.zeros(len(X), bool)
    for i, x in enumerate(X):
        d = x - o
        L = float(np.linalg.norm(d))
        if L <= 0.0:
            continue
        p = np.cross(d, e2)
        det = np.einsum("ij,ij->i", e1, p)
        ok = np.abs(det) > 1e-300
        inv = np.zeros_like(det)
        inv[ok] = 1.0 / det[ok]
        u = np.einsum("ij,ij->i", s, p) * inv
        v = (q @ d) * inv
        tt = tq * inv
        t_max = 1.0 - 1e-9 - float(tol[i]) / L
        hit = ok & (u >= -1e-12) & (v >= -1e-12) & (u + v <= 1.0 + 1e-12) & (tt > 1e-9) & (tt < t_max)
        out[i] = bool(hit.any())
    return out


def landmark_visibility(kit, V: np.ndarray, scheme: str, camera: Camera, *,
                        names: Sequence[str] | None = None, cos_min: float = 0.0,
                        margin_px: float = 0.0) -> np.ndarray:
    """Exact geometric visibility (N,) bool of the ``scheme`` landmarks on ``V`` (raster-independent).

    A landmark is visible when

    1. it is in front of the camera and projects inside ``[0, W] x [0, H]``;
    2. every triangle incident to a vertex carrying barycentric weight faces the
       camera with ``cos(n_t, C - X_t) > cos_min``, and so does the interpolated
       vertex normal (``cos_min = 0``: front-facing, so no occluding contour of its
       own surface passes through the point; larger values also exclude grazing points);
    3. the segment from the camera centre to the point crosses no triangle
       (:func:`segment_hits`);
    4. with ``margin_px > 0``: the segments to 8 points at ``r = margin_px * z / f`` mm
       around it in its tangent plane are also unblocked (ignoring hits within
       ``max(0.5, 2 r)`` mm of their ends), so no other surface's contour passes within
       about ``margin_px`` pixels.
    """
    V = np.asarray(V, float)
    tris = kit.triangles()
    pts = kit.landmarks[scheme]
    nm = kit.landmark_names(scheme) if names is None else list(names)
    tri = np.asarray([pts[k]["tri"] for k in nm], np.int64)
    bary = np.asarray([pts[k]["bary"] for k in nm], float).reshape(-1, 3)
    X = kit.landmark_positions(scheme, V, nm)
    uv = camera.project(X)
    z = camera.depth(X)
    with np.errstate(invalid="ignore"):
        vis = ((z > 0) & np.isfinite(uv).all(axis=1) & (uv[:, 0] >= 0) & (uv[:, 0] <= camera.width)
               & (uv[:, 1] >= 0) & (uv[:, 1] <= camera.height))
    C = camera.center
    A = V[tris[:, 0]]
    fn = np.cross(V[tris[:, 1]] - A, V[tris[:, 2]] - A)
    to_c = C - (A + V[tris[:, 1]] + V[tris[:, 2]]) / 3.0
    tri_cos = np.einsum("ij,ij->i", fn, to_c) / np.maximum(
        np.linalg.norm(fn, axis=1) * np.linalg.norm(to_c, axis=1), 1e-300)
    vn = vertex_normals(V, tris)
    normals = np.zeros_like(X)
    for i in np.flatnonzero(vis):
        verts = tris[tri[i]][bary[i] > 1e-12]
        star = np.flatnonzero(np.isin(tris, verts).any(axis=1))
        n = bary[i] @ vn[tris[tri[i]]]
        n = n / max(float(np.linalg.norm(n)), 1e-300)
        normals[i] = n
        to_cam = C - X[i]
        cosv = float(n @ to_cam) / max(float(np.linalg.norm(to_cam)), 1e-300)
        vis[i] = bool(np.all(tri_cos[star] > cos_min) and tri_cos[tri[i]] > cos_min and cosv > float(cos_min))
    idx = np.flatnonzero(vis)
    if idx.size:
        vis[idx] = ~segment_hits(V, tris, C, X[idx])
    if margin_px > 0:
        ang = np.arange(8) * (np.pi / 4.0)
        for i in np.flatnonzero(vis):
            n = normals[i]
            a = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
            t1 = np.cross(n, a)
            t1 /= np.linalg.norm(t1)
            t2 = np.cross(n, t1)
            r = float(margin_px) * float(z[i]) / float(camera.f)
            P = X[i] + r * (np.cos(ang)[:, None] * t1 + np.sin(ang)[:, None] * t2)
            vis[i] = not segment_hits(V, tris, C, P, end_tol_mm=max(0.5, 2.0 * r)).any()
    return vis


def project_landmarks(kit, V: np.ndarray, scheme: str, camera: Camera, *, names: Sequence[str] | None = None,
                      return_visible: bool = False, cos_min: float = 0.0, margin_px: float = 0.0):
    """Project the kit's ``scheme`` landmarks evaluated on ``V`` with ``camera`` -> uv (N, 2) px.

    ``camera.project`` is used (it applies ``camera.k``; test-bed cameras have k = 0,
    matching the rasteriser).  For a view rendered at reduced resolution pass
    ``view.camera``.  With ``return_visible=True`` returns ``(uv, visible)`` with the
    exact geometric visibility of :func:`landmark_visibility`.
    """
    X = kit.landmark_positions(scheme, V, names)
    uv = camera.project(X)
    if not return_visible:
        return uv
    return uv, landmark_visibility(kit, V, scheme, camera, names=names, cos_min=cos_min, margin_px=margin_px)


def render_masks(view: RenderedView, kit, V: np.ndarray, *,
                 exclude_regions: Sequence[str] = SKIN_EXCLUDED_REGIONS) -> dict[str, np.ndarray]:
    """Skin and background masks of a rendered view (plus the lips / brows labels).

    Returns ``{'skin', 'background', 'lips', 'brows', 'face'}`` (H, W) bool:
    ``background = ~mask``; ``face`` = rendered pixels whose triangle's dominant vertex
    is not in ``exclude_regions`` (scalp, neck: hair-bearing or off-face in a real
    photo); ``lips`` / ``brows`` = rendered pixels whose procedural feature weight
    (:func:`feature_weights`) exceeds 0.5; ``skin = face & ~lips & ~brows``.
    ``V`` must be the vertices the view was rendered from.
    """
    H, W = view.mask.shape
    m = view.mask
    out = {k: np.zeros((H, W), bool) for k in ("skin", "lips", "brows", "face")}
    out["background"] = ~m
    if not m.any():
        return out
    tris = kit.triangles()
    X = surface_points(view, V, tris)[m]
    w = feature_weights(kit, V, X)
    thr = _R["label_threshold"]
    tv = tris[view.tri_id[m]]
    dom = tv[np.arange(len(tv)), np.argmax(view.bary[m], axis=1)]
    reg = kit.vertex_regions()[dom]
    face = ~np.isin(reg, list(exclude_regions))
    lips = w["lips"] > thr
    brows = w["brows"] > thr
    for key, val in (("face", face), ("lips", lips), ("brows", brows), ("skin", face & ~lips & ~brows)):
        out[key][m] = val
    return out
