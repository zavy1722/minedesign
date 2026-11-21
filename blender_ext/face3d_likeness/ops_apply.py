# SPDX-License-Identifier: GPL-3.0-or-later
"""Apply a finished solve to the scene: cameras, shape-key stack, per-vertex attributes (DESIGN 6.4, 6.6, D-22).

Conventions
-----------
* Engine arrays are float64 millimetres in the engine frame; `bridge` converts to Blender metres
  (`engine_mm_to_blender_m`) and is the only code that touches mesh data.
* Key stack (DESIGN 4.17, D-22, bl K2): ``Basis`` = template; ``ID_fit`` relative to Basis (slider max 1.5,
  face3d.handoff.keys.HANDOFF_DEFAULTS); ``Asym`` and ``artist`` relative to ``ID_fit``; muted ``stage_*``
  diagnostics relative to Basis. A first apply builds the stack with `KeyStack.from_fit`; a **refit** reads
  the keys from the object, calls `KeyStack.rebase` (the artist delta ``artist - ID_fit`` is preserved
  exactly in float64; Blender stores float32, so the preserved delta is exact to float32 rounding of the
  coordinates, ~1e-5 mm at 100 mm) and writes them back with the user's values, slider ranges and mutes kept.
* Attributes written per vertex (POINT domain): ``f3d_sigma_mm`` (float, 1-sigma along the normal, mm),
  ``f3d_support`` (float in [0, 1], measurement support, DESIGN 4.17), ``f3d_status`` (int: 0 unobserved,
  1 prior-driven, 2 constrained, 3 measured; the lowest status among the ledger regions of the vertex's
  template region, face3d.fit.ledger.KIT_REGION_MAP).
* Refusals (nothing is written): Edit/Sculpt mode (`bridge.mode_guard`), a mesh whose topology hash differs
  from the result's template hash (`keys.topology_guard`), a missing or unreadable result.
* One operator call = one undo step (``UNDO`` flag). Every solve that is applied is adopted as an
  immutable ``solves/NNNN`` folder (result.json, arrays.npz, report.txt) and recorded as
  ``project.active_solve``; `revert_solve` re-applies an earlier one.
"""
import hashlib
import shutil
from pathlib import Path

import bpy
import numpy as np
from bpy.props import IntProperty, StringProperty

from . import bridge, ensure_engine_on_path
from . import ops_photos, ops_solve, overlays
from . import ops_project as P

ensure_engine_on_path()

from face3d.core.schema import FormatError, load_arrays, load_json  # noqa: E402
from face3d.fit.ledger import KIT_REGION_MAP  # noqa: E402
from face3d.geometry.camera import Camera, to_blender_camera  # noqa: E402
from face3d.handoff import keys as K  # noqa: E402
from face3d.pipeline.project import ProjectError  # noqa: E402

RESULT_FORMAT = "face3d.result"
STATUS_RANK = {"unobserved": 0, "prior-driven": 1, "constrained": 2, "measured": 3}
ATTR_SIGMA, ATTR_SUPPORT, ATTR_STATUS = "f3d_sigma_mm", "f3d_support", "f3d_status"


# ------------------------------------------------------------------ pure helpers
def vertex_status(region_names, region_ids, regions):
    """(n,) int32 status per vertex from ledger ``regions`` (result.json list of {name, status}).

    The vertex's template region (``region_names[region_ids[v]]``) maps to ledger regions by
    KIT_REGION_MAP; the vertex takes the LOWEST status among those present (a nose vertex is only as
    supported as the nose projection); a region with no ledger region (neck, other) is 0 (unobserved).
    """
    by = {r["name"]: STATUS_RANK.get(r["status"], 0) for r in regions}
    per_region = []
    for name in region_names:
        targets = [by[r] for r in KIT_REGION_MAP.get(name, (name,)) if r in by]
        per_region.append(min(targets) if targets else 0)
    return np.asarray(per_region, dtype=np.int32)[np.asarray(region_ids, dtype=np.int64)]


def load_result(solve_dir):
    """(result dict, arrays dict) of a ``result.json`` + ``arrays.npz`` folder; FormatError/OSError if bad."""
    d = Path(solve_dir)
    res = load_json(d / "result.json", expect_format=RESULT_FORMAT, max_version=1)
    arrays = load_arrays(d / "arrays.npz", res.get("arrays") or None)
    return res, arrays


def adopt_solve(project, solve_dir):
    """Make ``solve_dir`` the project's active solve; copies a job folder to ``solves/NNNN`` (immutable).

    Returns the project-relative path. Arrays are copied first and ``result.json`` last (its presence
    marks completion, as in face3d.pipeline.stages.write_result_files).
    """
    root, src = project.root, Path(solve_dir)
    if src.parent == root / "solves":
        dst = src
    else:
        base = root / "solves"
        base.mkdir(parents=True, exist_ok=True)
        n = 1 + max([int(p.name) for p in base.iterdir() if p.name.isdigit()] or [0])
        dst = base / ("%04d" % n)
        dst.mkdir()
        for name in ("arrays.npz", "report.txt", "result.json"):
            if (src / name).is_file():
                shutil.copy2(src / name, dst / name)
    project.active_solve = str(dst.relative_to(root))
    project.save()
    return project.active_solve


def stack_from_arrays(arrays):
    """KeyStack of a first apply from the engine's handoff arrays (artist = empty sculpt layer)."""
    basis = arrays["handoff_key_basis"]
    idf = arrays["handoff_key_ID_fit"]
    asym = arrays["handoff_key_Asym"] - idf
    stages = {k[len("handoff_key_"):]: arrays[k] for k in sorted(arrays) if k.startswith("handoff_key_stage_")}
    return K.KeyStack.from_fit(basis, idf, asym, stages)


def stack_from_object(obj):
    """KeyStack read back from an object's shape keys (engine mm), plus {name: (value, slider_max, mute)}.

    Returns (None, {}) when the object has no ID_fit key (no earlier fit to rebase).
    """
    raw = bridge.read_shape_keys(obj)
    if "Basis" not in raw or K.ID not in raw:
        return None, {}
    basis = bridge.blender_m_to_engine_mm(raw["Basis"][0])
    keys, state = {}, {}
    for name, (data, rel, value, smax, mute) in raw.items():
        if name == "Basis":
            continue
        keys[name] = K.Key(bridge.blender_m_to_engine_mm(data), rel or "Basis", value, smax, mute)
        state[name] = (value, smax, mute)
    return K.KeyStack(basis, keys), state


def write_stack(obj, ks, state):
    """Write every key of ``ks`` to ``obj`` in dependency order, keeping user values where known."""
    done, order = set(), []

    def visit(name):
        if name in done or name == "Basis":
            return
        visit(ks.keys[name].relative_to)
        done.add(name)
        order.append(name)

    for n in ks.keys:
        visit(n)
    for name in order:
        key = ks.keys[name]
        value, smax, mute = state.get(name, (key.value, key.slider_max, key.mute))
        bridge.write_shape_key(obj, name, bridge.engine_mm_to_blender_m(key.data), key.relative_to,
                               smax, value, mute)


def object_uuid(project, obj):
    return hashlib.sha256((str(project.root) + "|" + obj.name).encode()).hexdigest()[:16]


def is_identity_transform(obj, tol=1e-6):
    """True when ``obj.matrix_world`` is the identity (or unset): keys are in object space, cameras in world."""
    m = getattr(obj, "matrix_world", None)
    if m is None:
        return True
    try:
        return bool(np.allclose(np.asarray(m, dtype=np.float64).reshape(4, 4), np.eye(4), atol=tol))
    except (TypeError, ValueError):
        return True


def apply_cameras(result, scene=None, flipped=()):
    """Apply result cameras to the photo camera objects; returns the number applied.

    With ``scene`` the render resolution follows the active photo camera (it is per scene in Blender), and
    the background image of every photo in ``flipped`` (a recorded mirror decision) is shown flipped, because
    the engine solved the flipped image.
    """
    n = 0
    for c in result.get("cameras", []):
        obj = ops_photos.camera_for_photo(c["photo"])
        if obj is None:
            continue
        K3 = np.asarray(c["K"], dtype=np.float64)
        w = int(obj.get("f3d_res_x", 0)) or int(round(2 * K3[0, 2]))
        h = int(obj.get("f3d_res_y", 0)) or int(round(2 * K3[1, 2]))
        cam = Camera(f=float(K3[0, 0]), cx=float(K3[0, 2]), cy=float(K3[1, 2]), width=w, height=h,
                     R=np.asarray(c["R"], dtype=np.float64), t=np.asarray(c["t"], dtype=np.float64))
        bridge.apply_camera(obj, to_blender_camera(cam))
        for bg in obj.data.background_images:
            bg.use_flip_x = c["photo"] in flipped
        if scene is not None and getattr(scene, "camera", None) is obj:
            ops_photos.sync_render_resolution(scene, obj)
        n += 1
    return n


def apply_solve(op, context, solve_dir):
    """Apply a solve folder to the active mesh object; returns an operator result set.

    All checks run before the first write. Reports through message keys only.
    """
    obj = context.active_object if getattr(context, "active_object", None) is not None else context.object
    if obj is None or getattr(obj, "type", "") != "MESH":
        return P.fail(op, "no_mesh_object")
    if not is_identity_transform(obj):
        return P.fail(op, "head_transform")
    try:
        res, arrays = load_result(solve_dir)
    except (FormatError, OSError, ValueError, KeyError):
        return P.fail(op, "result_unreadable")
    need = ("handoff_key_basis", "handoff_key_ID_fit", "handoff_key_Asym")
    if any(k not in arrays for k in need):
        return P.fail(op, "no_result")
    try:
        want = res["run"]["input_hashes"]["template_topology_sha256"]
        K.topology_guard(want, bridge.topology_sha(obj.data))
        n = len(obj.data.vertices)
        if arrays["handoff_key_basis"].shape != (n, 3):
            raise K.TopologyMismatch("vertex count differs from the result")
    except K.TopologyMismatch:
        return P.fail(op, "topology_mismatch")
    except KeyError:
        return P.fail(op, "result_unreadable")
    try:
        prj = P.load_project(context)
        with bridge.mode_guard(obj):
            old, state = stack_from_object(obj)
            if old is None:
                ks = stack_from_arrays(arrays)
                if obj.data.shape_keys is None:
                    bridge.write_vertices(obj.data, bridge.engine_mm_to_blender_m(ks.basis))
                state = {}
            else:
                new_id = arrays["handoff_key_ID_fit"]
                old.rebase(new_id, arrays["handoff_key_Asym"] - new_id)
                for k in sorted(arrays):
                    if k.startswith("handoff_key_stage_"):
                        old.keys[k[len("handoff_key_"):]] = K.Key(arrays[k], K.BASIS, 0.0, 1.0, True)
                ks = old
            apply_cameras(res, context.scene, set(prj.flipped_photos()))
            write_stack(obj, ks, state)
            _write_attributes(obj, res, arrays)
            fill_overlays(res, arrays)
        obj["f3d_applied_solve"] = adopt_solve(prj, solve_dir)
        obj["face3d_uuid"] = object_uuid(prj, obj)
        P.settings(context).job.status = "idle"
        ops_solve.cards_from_result(context, res)
        return {"FINISHED"}
    except bridge.BridgeRefusal:
        return P.fail(op, "wrong_mode")
    except (ProjectError, K.TopologyMismatch):
        return P.fail(op, "topology_mismatch")
    except (OSError, ValueError, KeyError, TypeError):
        return P.fail(op, "result_unreadable")


def fill_overlays(res, arrays):
    """Feed the camera-view overlays from a result: hatching of prior-driven/unobserved regions (H9) and the
    model outline, projected through each result camera (image px).

    Hatch = the convex hull of each template region's projected vertices whose status is unobserved or
    prior-driven. The model contour is the convex hull of ALL projected vertices: PROVISIONAL, an outer
    approximation of the silhouette (the engine exports no silhouette polyline). Sigma ellipses and residual
    arrows stay unfilled: result.json carries no per-photo landmark residuals.
    """
    V, ids = arrays.get("vertices"), arrays.get("region_ids")
    names = (res.get("per_vertex") or {}).get("region_names")
    if V is None or ids is None or names is None:
        return 0
    V = np.asarray(V, dtype=np.float64)
    ids = np.asarray(ids, dtype=np.int64)
    status = vertex_status(names, ids, res.get("regions", []))
    n = 0
    for c in res.get("cameras", []):
        K3 = np.asarray(c["K"], dtype=np.float64)
        cam = Camera(f=float(K3[0, 0]), cx=float(K3[0, 2]), cy=float(K3[1, 2]), width=int(round(2 * K3[0, 2])),
                     height=int(round(2 * K3[1, 2])), R=np.asarray(c["R"], dtype=np.float64),
                     t=np.asarray(c["t"], dtype=np.float64))
        front = cam.depth(V) > 1e-6
        uv = np.full((len(V), 2), np.nan)
        uv[front] = cam.project(V[front])
        hulls = []
        for rid in np.unique(ids[status <= 1]):
            pts = uv[(ids == rid) & (status <= 1) & front]
            hull = overlays.convex_hull(pts)
            if len(hull) >= 3:
                hulls.append(hull)
        overlays.set_data("hatch", c["photo"], hulls)
        outline = overlays.convex_hull(uv[front])
        if len(outline) >= 3:
            overlays.set_data("model_contour", c["photo"], np.vstack([outline, outline[:1]]))
        n += 1
    return n


def _write_attributes(obj, res, arrays):
    me = obj.data
    n = len(me.vertices)
    if "sigma_n" in arrays and len(arrays["sigma_n"]) == n:
        bridge.set_attribute(me, ATTR_SIGMA, np.asarray(arrays["sigma_n"], np.float64), "POINT", "FLOAT")
    if "support" in arrays and len(arrays["support"]) == n:
        bridge.set_attribute(me, ATTR_SUPPORT, np.clip(arrays["support"], 0.0, 1.0), "POINT", "FLOAT")
    names = (res.get("per_vertex") or {}).get("region_names")
    if names is not None and "region_ids" in arrays and len(arrays["region_ids"]) == n:
        bridge.set_attribute(me, ATTR_STATUS, vertex_status(names, arrays["region_ids"], res.get("regions", [])),
                             "POINT", "INT")


# ------------------------------------------------------------------ operators
def _mesh_poll(cls, context):
    obj = getattr(context, "active_object", None) or getattr(context, "object", None)
    if obj is None or getattr(obj, "type", "") != "MESH":
        return P.deny(cls, "no_mesh_object")
    if getattr(obj, "mode", "OBJECT") in ("EDIT", "SCULPT"):
        return P.deny(cls, "wrong_mode")
    return True


class FACE3D_OT_apply_result(bpy.types.Operator):
    bl_idname = "face3d.apply_result"
    bl_label = "Apply Result"
    bl_description = "Put the solved cameras and the fitted shape keys on the selected head mesh (one undo step)"
    bl_options = {"REGISTER", "UNDO"}

    solve_dir: StringProperty(name="Solve folder", description="Empty = the finished job", subtype="DIR_PATH")

    @classmethod
    def poll(cls, context):
        if P.project_root(context) is None:
            return P.deny(cls, "no_project")
        if P.job_is_running(context):
            return P.deny(cls, "job_running")
        if P.settings(context).job.status != "ready":
            return P.deny(cls, "no_result")
        return _mesh_poll(cls, context)

    def execute(self, context):
        try:
            d = self.solve_dir or P.settings(context).job.job_dir
            if not d:
                return P.fail(self, "no_result")
            r = apply_solve(self, context, d)
            if "FINISHED" in r:
                P.info(self, "result_applied")
            return r
        except Exception:  # noqa: BLE001 - UI boundary
            return P.fail(self, "internal_error")


class FACE3D_OT_revert_solve(bpy.types.Operator):
    bl_idname = "face3d.revert_solve"
    bl_label = "Revert to Solve"
    bl_description = "Re-apply an earlier solve of this project (the sculpt layer is carried over)"
    bl_options = {"REGISTER", "UNDO"}

    n: IntProperty(name="Solve number", default=1, min=1)

    @classmethod
    def poll(cls, context):
        root = P.project_root(context)
        if root is None:
            return P.deny(cls, "no_project")
        if P.job_is_running(context):
            return P.deny(cls, "job_running")
        if not (root / "solves").is_dir():
            return P.deny(cls, "no_result")
        return _mesh_poll(cls, context)

    def execute(self, context):
        try:
            d = P.project_root(context) / "solves" / ("%04d" % self.n)
            if not (d / "result.json").is_file():
                return P.fail(self, "revert_unknown")
            r = apply_solve(self, context, d)
            if "FINISHED" in r:
                P.info(self, "result_reverted", n=self.n)
            return r
        except Exception:  # noqa: BLE001
            return P.fail(self, "internal_error")


CLASSES = (FACE3D_OT_apply_result, FACE3D_OT_revert_solve)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
