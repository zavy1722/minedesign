# SPDX-License-Identifier: GPL-3.0-or-later
"""The ONLY module that touches Blender mesh or image data (DESIGN 6.2 bridge rules, bl A3).

Conventions
-----------
* Engine frame: millimetres, +y up, +z toward the viewer (DESIGN 3.1). Blender
  frame: metres, +z up, -y toward the viewer. `ENGINE_TO_BLENDER` = scale
  0.001 times R_x(+90 deg), i.e. (x, y, z)_mm -> 0.001 * (x, -z, y) m.
* Coordinates cross the boundary through contiguous float32 `foreach_get` /
  `foreach_set` buffers; the engine sees float64.
* Image rows: Blender stores bottom-up, the engine top-down; flipped here.
* Camera shift is delegated to `face3d.geometry.camera.to_blender_camera`
  (kept unchanged; shift in units of image width with sensor_fit HORIZONTAL,
  known fact 1). Render resolution is per scene in Blender (bl C5), so it is
  stored as custom properties on the camera object.
"""
import contextlib
import hashlib

import numpy as np

import bpy

_MM_TO_M = 0.001

_RX90 = np.array([[1.0, 0.0, 0.0],
                  [0.0, 0.0, -1.0],
                  [0.0, 1.0, 0.0]])

ENGINE_TO_BLENDER = np.eye(4)
ENGINE_TO_BLENDER[:3, :3] = _MM_TO_M * _RX90


class BridgeRefusal(RuntimeError):
    """Raised when the bridge declines to touch a mesh (Edit/Sculpt mode)."""


# ------------------------------------------------------------------ frames
def engine_mm_to_blender_m(V):
    """(n,3) or (3,) engine mm -> Blender m: 0.001 * (x, -z, y)."""
    V = np.asarray(V, dtype=np.float64)
    out = np.empty_like(V)
    out[..., 0] = V[..., 0]
    out[..., 1] = -V[..., 2]
    out[..., 2] = V[..., 1]
    return out * _MM_TO_M


def blender_m_to_engine_mm(B):
    """Inverse of engine_mm_to_blender_m: (x, y, z) m -> 1000 * (x, z, -y) mm."""
    B = np.asarray(B, dtype=np.float64) / _MM_TO_M
    out = np.empty_like(B)
    out[..., 0] = B[..., 0]
    out[..., 1] = B[..., 2]
    out[..., 2] = -B[..., 1]
    return out


# ------------------------------------------------------------------ meshes
def mesh_vertices_to_array(me):
    """Vertex coordinates of `me` as float64 (n,3) (read via contiguous float32)."""
    n = len(me.vertices)
    buf = np.empty(n * 3, dtype=np.float32)
    me.vertices.foreach_get("co", buf)
    return buf.reshape(n, 3).astype(np.float64)


def _require_finite(V, what):
    if not np.isfinite(np.asarray(V, dtype=np.float64)).all():
        raise BridgeRefusal("non-finite %s coordinates (NaN/inf); refusing to write" % what)


def write_vertices(me, V):
    """Write (n,3) coordinates into `me` (float32 contiguous) and call me.update()."""
    V = np.asarray(V)
    if V.shape != (len(me.vertices), 3):
        raise ValueError("vertex array shape %r != (%d, 3)" % (V.shape, len(me.vertices)))
    _require_finite(V, "vertex")
    flat = np.ascontiguousarray(V.astype(np.float32).reshape(-1))
    assert flat.dtype == np.float32 and flat.flags["C_CONTIGUOUS"]
    me.vertices.foreach_set("co", flat)
    me.update()


def write_shape_key(obj, name, V, relative_to="Basis", slider_max=1.0, value=0.0, mute=False):
    """Create or update shape key `name` holding absolute coordinates `V` (Blender frame, (n,3)).

    A new key uses shape_key_add(from_mix=False) so it is not baked from the
    current mix. A key that already exists is reused in place (Blender makes
    key-block names unique, so adding again would create 'name.001' and leave
    dependent relative keys on the stale block); its relative_key, slider_max,
    value, mute and coordinates are overwritten. A Basis key is created first
    if the object has none. Returns the key block.
    """
    me = obj.data
    if me.shape_keys is None or len(me.shape_keys.key_blocks) == 0:
        obj.shape_key_add(name="Basis", from_mix=False)
    blocks = me.shape_keys.key_blocks
    ref = blocks.get(relative_to)
    if ref is None:
        raise KeyError("relative key %r not found" % relative_to)
    V = np.asarray(V)
    kb = blocks.get(name)
    if kb is not None and kb is ref:
        raise ValueError("shape key %r cannot be relative to itself" % name)
    if kb is not None and V.shape != (len(kb.data), 3):
        raise ValueError("key array shape %r != (%d, 3)" % (V.shape, len(kb.data)))
    _require_finite(V, "shape key")
    if kb is None:
        kb = obj.shape_key_add(name=name, from_mix=False)
    kb.relative_key = ref
    kb.slider_max = float(slider_max)
    kb.value = float(value)
    kb.mute = bool(mute)
    if V.shape != (len(kb.data), 3):
        raise ValueError("key array shape %r != (%d, 3)" % (V.shape, len(kb.data)))
    flat = np.ascontiguousarray(V.astype(np.float32).reshape(-1))
    kb.data.foreach_set("co", flat)
    me.update()
    return kb


def read_shape_keys(obj):
    """{name: (data float64 (n,3), relative_to name, value, slider_max, mute)}."""
    out = {}
    sk = obj.data.shape_keys
    if sk is None:
        return out
    for kb in sk.key_blocks:
        n = len(kb.data)
        buf = np.empty(n * 3, dtype=np.float32)
        kb.data.foreach_get("co", buf)
        rel = kb.relative_key.name if kb.relative_key is not None else None
        out[kb.name] = (buf.reshape(n, 3).astype(np.float64), rel,
                        float(kb.value), float(kb.slider_max), bool(kb.mute))
    return out


def set_attribute(me, name, values, domain="POINT", type="FLOAT"):
    """Create/overwrite a mesh attribute (f3d_sigma_mm etc., DESIGN 6.6)."""
    attr = me.attributes.get(name)
    if attr is None:
        attr = me.attributes.new(name=name, type=type, domain=domain)
    if type == "FLOAT_VECTOR":
        key, dt = "vector", np.float32
    elif type == "INT":
        key, dt = "value", np.int32
    elif type == "BOOLEAN":
        key, dt = "value", np.bool_
    else:
        key, dt = "value", np.float32
    flat = np.ascontiguousarray(np.asarray(values).astype(dt).reshape(-1))
    attr.data.foreach_set(key, flat)
    return attr


def topology_sha(me):
    """SHA-256 of int64(n_verts) + int32 face indices; same definition as
    face3d.model.template_kit.topology_sha256 (mixed meshes add int32 face sizes first)."""
    n_v = len(me.vertices)
    n_f = len(me.polygons)
    sizes = np.empty(n_f, dtype=np.int32)
    starts = np.empty(n_f, dtype=np.int32)
    me.polygons.foreach_get("loop_total", sizes)
    me.polygons.foreach_get("loop_start", starts)
    loops = np.empty(len(me.loops), dtype=np.int32)
    me.loops.foreach_get("vertex_index", loops)
    flat = np.concatenate([loops[s:s + k] for s, k in zip(starts.tolist(), sizes.tolist())]) \
        if n_f else np.zeros(0, np.int32)
    head = np.asarray([n_v], dtype="<i8").tobytes()
    flat = np.ascontiguousarray(flat, dtype="<i4").tobytes()
    if n_f and bool(np.all(sizes == sizes[0])):
        return hashlib.sha256(head + flat).hexdigest()
    return hashlib.sha256(head + sizes.astype("<i4").tobytes() + flat).hexdigest()


@contextlib.contextmanager
def mode_guard(obj):
    """Refuse in EDIT or SCULPT mode; otherwise run in OBJECT mode and restore the prior mode."""
    mode = getattr(obj, "mode", "OBJECT")
    if mode in ("EDIT", "SCULPT"):
        raise BridgeRefusal("object is in %s mode; switch to Object mode first" % mode)
    switched = mode != "OBJECT"
    if switched and getattr(bpy.context, "view_layer", None) is not None:
        active = bpy.context.view_layer.objects.active
    else:
        active = getattr(bpy.context, "object", None)
    if switched and active is not obj:
        # mode_set acts on the active object only; never change another object's mode
        raise BridgeRefusal("object is in %s mode but is not the active object; "
                            "make it active or switch to Object mode first" % mode)
    if switched:
        bpy.ops.object.mode_set(mode="OBJECT")
    try:
        yield obj
    finally:
        if switched:
            bpy.ops.object.mode_set(mode=mode)


# ------------------------------------------------------------------ images
def image_to_array(img):
    """Blender image -> (H, W, 4) float32, top-down rows (Blender stores bottom-up)."""
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    return np.ascontiguousarray(buf.reshape(h, w, 4)[::-1])


def save_working_copy(arr, path):
    """Save a working copy as .npy (numpy.save; no pickles). Returns the path used."""
    path = str(path)
    if not path.endswith(".npy"):
        path += ".npy"
    with open(path, "wb") as fh:
        np.save(fh, np.asarray(arr), allow_pickle=False)
    return path


# ------------------------------------------------------------------ cameras
def apply_camera(cam_obj, cam_dict):
    """Apply a `to_blender_camera` dict to a Blender camera object.

    lens / sensor_width / sensor_fit ('HORIZONTAL') / shift_x / shift_y are
    copied verbatim (known fact 1). `matrix_world` is the engine-frame
    camera-to-world matrix mapped with ENGINE_TO_BLENDER; the 0.001 scale is
    applied to the translation only, so the camera object keeps unit scale.
    Resolution is stored as custom properties f3d_res_x / f3d_res_y.
    """
    import mathutils
    cam = cam_obj.data
    cam.lens = float(cam_dict["lens"])
    cam.sensor_width = float(cam_dict["sensor_width"])
    cam.sensor_fit = cam_dict["sensor_fit"]
    cam.shift_x = float(cam_dict["shift_x"])
    cam.shift_y = float(cam_dict["shift_y"])
    M = np.asarray(cam_dict["matrix_world"], dtype=np.float64)
    full = ENGINE_TO_BLENDER @ M
    out = np.eye(4)
    out[:3, :3] = _RX90 @ M[:3, :3]   # rotation only; ENGINE_TO_BLENDER's scale removed
    out[:3, 3] = full[:3, 3]
    cam_obj.matrix_world = mathutils.Matrix(out.tolist())
    res = cam_dict.get("resolution")
    if res is not None:
        cam_obj["f3d_res_x"] = int(res[0])
        cam_obj["f3d_res_y"] = int(res[1])
    return cam_obj
