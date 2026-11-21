# SPDX-License-Identifier: GPL-3.0-or-later
"""Camera-view overlays and comparison modes (DESIGN 6.5, H-accessibility rules).

Conventions
-----------
* Overlay data are kept in **image pixels** (top-left origin, y down; DESIGN 3.1) and mapped to
  region pixels (origin bottom-left of the 3D viewport region, y up) through the camera frame:
  `frame_corners_region` returns the four corners ordered top-left, top-right, bottom-right,
  bottom-left of the displayed photo; `view_to_image_px` / `image_px_to_view` are the exact affine
  maps between the two (pure, tested).
* Geometry comes from face3d.qa.overlay_geom (polylines, glyphs, the halo + outline + colour layer
  order of `styled`) and colours from face3d.qa.palette (Okabe-Ito roles, DESIGN 6.5); every role has a
  distinct glyph shape, so colour is never the only cue. Widths are multiplied by the UI scale.
* Nothing blinks and nothing is timer-driven (WCAG 2.3.1, DESIGN 6.5): comparison is **hold F to flip**
  (the flipped 64 px thumbnail is shown while the key is held, restored on release), plus a blur at
  3 % of the face width and a 64 px thumbnail mode. This module registers no timers.
* `compare_image` is pure numpy; the GPU texture upload in `_draw_compare` is best effort and silent
  when the GPU API is unavailable (stub, background mode).
* Residual arrows are magnified x5 (DESIGN 6.5). The face width used for the blur defaults to
  `DEFAULT_FACE_WIDTH_FRAC` of the shorter image side until the pins give a better value (PROVISIONAL).
"""
import os

import bpy
import numpy as np

from . import ensure_engine_on_path
from .messages import MESSAGES

ensure_engine_on_path()

from face3d.fit.edge_snap import gaussian_blur, sobel_magnitude  # noqa: E402
from face3d.io.image_ops import flip_horizontal, to_gray  # noqa: E402
from face3d.qa import overlay_geom as og  # noqa: E402
from face3d.qa import palette  # noqa: E402

RESIDUAL_SCALE = 5.0                 # DESIGN 6.5 "residual arrows x5"
DEFAULT_FACE_WIDTH_FRAC = 0.5        # PROVISIONAL: face width as a fraction of the shorter image side
DASH_ON_PX, DASH_OFF_PX = 8.0, 5.0   # traced-outline dash pattern (shape cue distinct from the model line)
MODES = ("flip", "blur", "thumb", "grey", "edges")

STATE = {
    "hide_auto": False,          # 'blind first pins': hide auto landmarks while the first pins are placed
    "mode": None,                # None or one of MODES; `flip` only while F is held
    "face_width_px": None,
    "selected_pin": None,        # (photo_id, landmark)
    "auto_landmarks": {},        # photo id -> (n, 2) image px
    "sigma": {},                 # photo id -> [(center (2,), cov2 (2,2))]
    "residuals": {},             # photo id -> [(p_obs, p_model, sigma_px)]
    "model_contour": {},         # photo id -> (m, 2)
    "traced": {},                # photo id -> (m, 2)
    "hatch": {},                 # photo id -> [polygon (k, 2)]
}
_handle = None


def reset_state():
    """Clear all overlay data and modes (new project, tests)."""
    for k, v in list(STATE.items()):
        STATE[k] = {} if isinstance(v, dict) else (False if k == "hide_auto" else None)


def set_data(kind, photo_id, value):
    """Store overlay data of ``kind`` ('auto_landmarks', 'sigma', 'residuals', 'model_contour', 'traced', 'hatch')."""
    if kind not in STATE or not isinstance(STATE[kind], dict):
        raise KeyError(kind)
    STATE[kind][photo_id] = value


# ------------------------------------------------------------------ pure mapping
def _corners(c):
    c = np.asarray(c, dtype=np.float64)
    if c.shape != (4, 2):
        raise ValueError("frame_corners_region must have shape (4, 2)")
    return c


def view_to_image_px(region_xy, frame_corners_region, image_wh):
    """Region pixel -> image pixel (top-left origin, y down), via the camera frame corners.

    ``frame_corners_region`` (4, 2): the displayed photo's corners in region pixels ordered
    top-left, top-right, bottom-right, bottom-left. The frame is a parallelogram
    ``TL + s (TR - TL) + t (BL - TL)``; the result is ``(s W, t H)`` with ``image_wh = (W, H)``.
    Works for any region y direction and for a rotated frame; points outside the frame give s or t
    outside [0, 1] (the caller decides whether to accept them). Raises ValueError for a degenerate frame.
    """
    C = _corners(frame_corners_region)
    tl, tr, bl = C[0], C[1], C[3]
    A = np.stack([tr - tl, bl - tl], axis=1)
    if abs(np.linalg.det(A)) < 1e-12:
        raise ValueError("degenerate camera frame")
    s, t = np.linalg.solve(A, np.asarray(region_xy, dtype=np.float64) - tl)
    return float(s * image_wh[0]), float(t * image_wh[1])


def image_px_to_view(xy, frame_corners_region, image_wh):
    """Inverse of `view_to_image_px`; also accepts an (n, 2) array."""
    C = _corners(frame_corners_region)
    p = np.asarray(xy, dtype=np.float64)
    s, t = p[..., 0] / float(image_wh[0]), p[..., 1] / float(image_wh[1])
    return C[0] + s[..., None] * (C[1] - C[0]) + t[..., None] * (C[3] - C[0])


def order_corners(pts):
    """Order four region points as top-left, top-right, bottom-right, bottom-left (region y up)."""
    p = np.asarray(pts, dtype=np.float64).reshape(4, 2)
    by_y = p[np.argsort(-p[:, 1], kind="stable")]
    top = by_y[:2][np.argsort(by_y[:2, 0])]
    bot = by_y[2:][np.argsort(by_y[2:, 0])]
    return np.array([top[0], top[1], bot[1], bot[0]])


def zoom_of_frame(frame_corners_region, image_wh):
    """Screen pixels per image pixel (the pin zoom of DESIGN 6.4; 1.0 = one photo px per screen px)."""
    C = _corners(frame_corners_region)
    return float(np.linalg.norm(C[1] - C[0]) / float(image_wh[0]))


def frame_corners_region(context):
    """Camera-frame corners in region pixels for the active scene camera, or None (not in camera view).

    Uses the camera's `view_frame`, the object matrix and `view3d_utils.location_3d_to_region_2d`
    (bpy_extras; imported lazily). The corners are ordered by `order_corners`.
    """
    try:
        from bpy_extras import view3d_utils
        scene, region, rv3d = context.scene, context.region, context.region_data
        cam = scene.camera
        if cam is None or rv3d is None or rv3d.view_perspective != "CAMERA":
            return None
        pts = []
        for co in cam.data.view_frame(scene=scene):
            p = view3d_utils.location_3d_to_region_2d(region, rv3d, cam.matrix_world @ co)
            if p is None:
                return None
            pts.append((p[0], p[1]))
        return order_corners(pts)
    except (AttributeError, ImportError, ValueError, TypeError):
        return None


def ui_scale(context):
    try:
        return float(context.preferences.system.ui_scale)
    except AttributeError:
        return 1.0


# ------------------------------------------------------------------ draw list (pure)
def _rgba(hex_colour, a=1.0):
    r, g, b = palette.hex_to_rgb(hex_colour)
    return (float(r), float(g), float(b), float(a))


def dashed(poly, on_px=DASH_ON_PX, off_px=DASH_OFF_PX):
    """Split a polyline into dash segments (a list of (k, 2) arrays) by arc length."""
    P = np.asarray(poly, dtype=np.float64)
    out, pos, on = [], 0.0, True
    cur = [P[0]] if len(P) else []
    for a, b in zip(P[:-1], P[1:]):
        seg = float(np.linalg.norm(b - a))
        if seg <= 0:
            continue
        d = (b - a) / seg
        t = 0.0
        while t < seg:
            lim = (on_px if on else off_px) - pos
            step = min(lim, seg - t)
            if on:
                if not cur:
                    cur = [a + d * t]
                cur.append(a + d * (t + step))
            t += step
            pos += step
            if pos >= (on_px if on else off_px) - 1e-12:
                if on and len(cur) > 1:
                    out.append(np.array(cur))
                cur, pos, on = [], 0.0, not on
    if on and len(cur) > 1:
        out.append(np.array(cur))
    return out


def _role_for_pin(pin):
    return "conflict" if pin.get("conflict") else "user_pin"


def _add_styled(out, polys_img, role, corners, wh, scale, width=None):
    """Map image-px polylines to region px and append the halo/outline/colour layers."""
    mapped = [image_px_to_view(np.asarray(p), corners, wh) for p in polys_img]
    for poly, w, col in og.styled(mapped, role, None if width is None else width):
        out.append((poly, w * scale, _rgba(col)))


def build_draw_list(photo_id, corners, image_wh, scale=1.0, pins=(), state=None):
    """All overlay polylines for one photo as [(region polyline (n,2), width_px, rgba)], back to front.

    ``pins``: dicts with ``landmark``, ``x``, ``y`` (image px) and optional ``conflict``. ``state``
    defaults to the module STATE. Order: hatching, model contour, traced outline, sigma ellipses,
    residual arrows, auto landmarks (unless `hide_auto`), user pins, the selected-pin ring. Widths and
    glyph sizes are multiplied by ``scale`` (the UI scale).
    """
    st = STATE if state is None else state
    out = []
    for poly in st["hatch"].get(photo_id, ()):
        segs = og.hatch_polygon(np.asarray(poly))
        _add_styled(out, segs, "guessed", corners, image_wh, scale, width=1.0)
    if photo_id in st["model_contour"]:
        _add_styled(out, [st["model_contour"][photo_id]], "model_contour", corners, image_wh, scale)
    if photo_id in st["traced"]:
        _add_styled(out, dashed(st["traced"][photo_id]), "user_pin", corners, image_wh, scale, width=2.0)
    for centre, cov2 in st["sigma"].get(photo_id, ()):
        e = og.sigma_ellipse(centre, cov2)
        _add_styled(out, [np.vstack([e, e[:1]])], "auto_pin", corners, image_wh, scale, width=1.5)
    for item in st["residuals"].get(photo_id, ()):
        p_obs, p_model = item[0], item[1]
        sig = float(item[2]) if len(item) > 2 and item[2] else 1.0
        d = np.linalg.norm(np.asarray(p_obs, float) - np.asarray(p_model, float))
        col = palette.RESIDUAL_BINS[int(min(3, d / max(sig, 1e-9)))]
        mapped = [image_px_to_view(a, corners, image_wh) for a in og.residual_arrow(p_obs, p_model, RESIDUAL_SCALE)]
        for poly in mapped:
            out.append((poly, 4.0 * scale, _rgba(palette.HALO)))
            out.append((poly, 2.0 * scale, _rgba(col)))
    if not st["hide_auto"] and photo_id in st["auto_landmarks"]:
        for xy in np.asarray(st["auto_landmarks"][photo_id]):
            _add_styled(out, og.glyph("circle", xy, 7.0, scale), "auto_pin", corners, image_wh, scale, width=1.5)
    sel = st["selected_pin"]
    for pin in pins:
        role = _role_for_pin(pin)
        _add_styled(out, og.glyph("cross" if role == "conflict" else "square", (pin["x"], pin["y"]), 9.0, scale),
                    role, corners, image_wh, scale, width=2.0)
        if sel and sel == (photo_id, pin["landmark"]):
            _add_styled(out, og.glyph("ring", (pin["x"], pin["y"]), 9.0, scale), "selected",
                        corners, image_wh, scale, width=2.0)
    return out


# ------------------------------------------------------------------ comparison images (pure)
def _area_resize(img, h2, w2):
    """Box-average resize of (H, W[, C]) to (h2, w2[, C]) (no interpolation artefacts for a thumbnail)."""
    a = np.asarray(img, dtype=np.float64)
    rows = np.array_split(np.arange(a.shape[0]), h2)
    cols = np.array_split(np.arange(a.shape[1]), w2)
    out = np.empty((h2, w2) + a.shape[2:], dtype=np.float64)
    for i, r in enumerate(rows):
        band = a[r[0]:r[-1] + 1].mean(axis=0)
        for j, c in enumerate(cols):
            out[i, j] = band[c[0]:c[-1] + 1].mean(axis=0)
    return out


def face_width_or_default(img_shape, face_width_px=None):
    if face_width_px:
        return float(face_width_px)
    return DEFAULT_FACE_WIDTH_FRAC * float(min(img_shape[0], img_shape[1]))


def compare_image(rgb, mode, face_width_px=None):
    """Display array (h, w, 3) float32 in [0, 1] for a comparison ``mode`` of a photo (H, W, 3 or 4).

    flip: the 64 px thumbnail mirrored left-right (DESIGN 6.5: shown only while F is held);
    thumb: the 64 px thumbnail (face3d.qa.overlay_geom.thumbnail_shape); blur: Gaussian blur with
    sigma = 3 % of the face width (overlay_geom.blur_sigma_px); grey: Rec.709 luma; edges: Sobel
    magnitude of the 1 px-smoothed luma, scaled to its maximum.
    """
    if mode not in MODES:
        raise ValueError("unknown comparison mode %r" % (mode,))
    a = np.asarray(rgb, dtype=np.float64)[..., :3]
    if mode in ("flip", "thumb"):
        h2, w2 = og.thumbnail_shape(a.shape[0], a.shape[1])
        th = _area_resize(a, h2, w2)
        return np.ascontiguousarray((flip_horizontal(th) if mode == "flip" else th).astype(np.float32))
    if mode == "blur":
        sig = og.blur_sigma_px(face_width_or_default(a.shape, face_width_px))
        out = np.stack([gaussian_blur(a[..., k], sig) for k in range(3)], axis=-1)
        return np.ascontiguousarray(np.clip(out, 0, 1).astype(np.float32))
    g = to_gray(a)
    if mode == "grey":
        return np.ascontiguousarray(np.repeat(g[..., None], 3, axis=-1).astype(np.float32))
    e = sobel_magnitude(gaussian_blur(g, 1.0))
    m = float(e.max())
    e = e / m if m > 0 else e
    return np.ascontiguousarray(np.repeat(e[..., None], 3, axis=-1).astype(np.float32))


# ------------------------------------------------------------------ GPU drawing
def _scene_pins(context, photo_id):
    try:
        return [{"landmark": p.landmark, "x": p.x, "y": p.y} for p in context.scene.face3d.pins
                if p.photo_id == photo_id]
    except AttributeError:
        return []


def _image_wh(cam_obj):
    return int(cam_obj.get("f3d_res_x", 0)), int(cam_obj.get("f3d_res_y", 0))


def _draw_polylines(context, items):
    import gpu
    from gpu_extras.batch import batch_for_shader
    shader = gpu.shader.from_builtin("POLYLINE_UNIFORM_COLOR")
    gpu.state.blend_set("ALPHA")
    region = context.region
    for poly, width, rgba in items:
        batch = batch_for_shader(shader, "LINE_STRIP", {"pos": [tuple(p) for p in np.asarray(poly)]})
        shader.bind()
        shader.uniform_float("viewportSize", (region.width, region.height))
        shader.uniform_float("lineWidth", float(width))
        shader.uniform_float("color", rgba)
        batch.draw(shader)
    gpu.state.blend_set("NONE")


def _draw_compare(context, photo_id, corners, wh):
    """Upload the comparison array as a texture over the camera frame (best effort)."""
    if not STATE["mode"]:
        return
    try:
        import gpu
        from gpu_extras.batch import batch_for_shader
        if not hasattr(gpu, "types"):
            return
        root = context.scene.face3d.project_path
        arr = np.load(os.path.join(root, "photos", photo_id + ".npy"), allow_pickle=False)
        img = compare_image(arr, STATE["mode"], STATE["face_width_px"])
        h, w = img.shape[:2]
        flat = np.concatenate([img, np.ones((h, w, 1), np.float32)], axis=-1)[::-1].reshape(-1)
        buf = gpu.types.Buffer("FLOAT", flat.size, flat)
        tex = gpu.types.GPUTexture((w, h), format="RGBA16F", data=buf)
        shader = gpu.shader.from_builtin("IMAGE")
        quad = [tuple(c) for c in corners[[3, 2, 0, 1]]]            # BL, BR, TL, TR
        batch = batch_for_shader(shader, "TRI_STRIP", {"pos": quad, "texCoord": ((0, 0), (1, 0), (0, 1), (1, 1))})
        shader.bind()
        shader.uniform_sampler("image", tex)
        batch.draw(shader)
    except Exception:  # noqa: BLE001 - a draw handler must never raise
        return


def draw_callback():
    """POST_PIXEL handler: draws the overlays of the active photo camera. Never raises."""
    try:
        context = bpy.context
        cam = context.scene.camera
        if cam is None or "f3d_photo_id" not in cam:
            return
        corners = frame_corners_region(context)
        if corners is None:
            return
        pid, wh = cam["f3d_photo_id"], _image_wh(cam)
        if wh[0] <= 0 or wh[1] <= 0:
            return
        _draw_compare(context, pid, corners, wh)
        _draw_polylines(context, build_draw_list(pid, corners, wh, ui_scale(context),
                                                 _scene_pins(context, pid)))
    except Exception:  # noqa: BLE001
        return


# ------------------------------------------------------------------ operators
def _redraw(context):
    area = getattr(context, "area", None)
    if area is not None:
        area.tag_redraw()


class FACE3D_OT_compare_flip(bpy.types.Operator):
    bl_idname = "face3d.compare_flip"
    bl_label = "Hold to Flip"
    bl_description = "Hold to see the photo flipped left-right; release to restore (no blinking)"
    bl_options = {"REGISTER"}

    keyed: bpy.props.BoolProperty(default=False, options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        cam = getattr(context.scene, "camera", None)
        if cam is None or "f3d_photo_id" not in cam:
            cls.poll_message_set(MESSAGES["no_active_photo"])
            return False
        return True

    def invoke(self, context, event):
        STATE["mode"] = "flip"
        _redraw(context)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type == "F" and event.value == "RELEASE":
            STATE["mode"] = None
            _redraw(context)
            return {"FINISHED"}
        if event.type in ("ESC", "RIGHTMOUSE"):
            STATE["mode"] = None
            _redraw(context)
            return {"CANCELLED"}
        return {"PASS_THROUGH"}

    def execute(self, context):                       # F3 search / scripted use: toggle without a key release
        STATE["mode"] = None if STATE["mode"] == "flip" else "flip"
        _redraw(context)
        return {"FINISHED"}

    def cancel(self, context):
        STATE["mode"] = None


class FACE3D_OT_compare_mode(bpy.types.Operator):
    bl_idname = "face3d.compare_mode"
    bl_label = "Comparison View"
    bl_description = "Toggle the blur (3 % of face width), 64 px thumbnail, grey or edges comparison view"
    bl_options = {"REGISTER"}

    mode: bpy.props.EnumProperty(name="Mode", items=[("blur", "Blur", ""), ("thumb", "Thumbnail", ""),
                                                     ("grey", "Grey", ""), ("edges", "Edges", ""),
                                                     ("wobble", "Wobble", "")], default="blur")
    keyed: bpy.props.BoolProperty(default=False, options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        cam = getattr(context.scene, "camera", None)
        if cam is None or "f3d_photo_id" not in cam:
            cls.poll_message_set(MESSAGES["no_active_photo"])
            return False
        return True

    def invoke(self, context, event):
        if self.keyed and not self.poll(context):
            return {"PASS_THROUGH"}
        return self.execute(context)

    def execute(self, context):
        if self.mode == "wobble":                      # DESIGN 6.5: a wobble would be motion; deferred
            self.report({"INFO"}, MESSAGES["deferred_feature"])
            return {"CANCELLED"}
        STATE["mode"] = None if STATE["mode"] == self.mode else self.mode
        _redraw(context)
        return {"FINISHED"}


CLASSES = (FACE3D_OT_compare_flip, FACE3D_OT_compare_mode)


def register():
    global _handle
    for c in CLASSES:
        bpy.utils.register_class(c)
    if _handle is None:
        _handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback, (), "WINDOW", "POST_PIXEL")


def unregister():
    global _handle
    if _handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_handle, "WINDOW")
        _handle = None
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
    STATE["mode"] = None
