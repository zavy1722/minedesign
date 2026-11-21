# SPDX-License-Identifier: GPL-3.0-or-later
"""Sculpt hand-off, protection mask, sharing review and purge (DESIGN 4.17, 6.4, 6.6, eth F9).

Conventions
-----------
* `handoff_sculpt` duplicates the fitted object, bakes the evaluated key mix (``Basis + sum value_k
  (data_k - data_of(relative_to_k))``, face3d.handoff.keys.KeyStack.evaluate; includes the artist layer),
  clears the keys of the copy, sets its base mesh to the **limit-fitted cage**
  (face3d.mesh.subdiv.fit_cage_to_limit, mu = 1e-5, DESIGN 4.17) so that Multires levels interpolate the
  fitted surface without shrinking, then adds a Multires modifier and subdivides 2-3 levels through guarded
  `bpy.ops` calls (a failure leaves the copy and reports ``handoff_multires_failed``). A template that is not
  all-quad has no limit stencils: the baked mix is used as the base and Multires subdivides it unfitted.
* The cage at hand-off is stored as ``<project>/sculpt/<id>.npy`` (engine mm) so that `rebase_sculpt` can
  carry the artist's coarse (cage-level) edits to a new fit. Multires displacement detail is NOT transferred:
  writing into a Multires copy only goes through ``multires_reshape`` (DESIGN 6.6, bl K5/Q4 unverified), so
  rebase uses the documented "new copy" fallback and leaves the old copy untouched.
* `protect_measured` writes ``face3d.handoff.keys.protect_mask(support)`` = clip(support, 0, 1) into the
  point attribute ``.sculpt_mask`` (1 = fully masked): measured vertices are locked, guessed ones stay
  sculptable (DESIGN 4.17 as corrected after the WP-13 review; the older "1 - support" in the WBS text
  protects the wrong side). Support comes from the active solve's arrays.
* `prepare_for_sharing` only LISTS what a shared .blend would carry (packed images, camera background
  images, orphan data, file previews, .blend1 backups) unless ``confirm`` is set; `purge` deletes by
  engine data class (face3d.core.policy.DataClass) after confirmation and audits each purge (class + code).
"""
import glob
import os
import shutil

import bpy
import numpy as np
from bpy.props import BoolProperty, EnumProperty, IntProperty

from . import bridge, ensure_engine_on_path
from . import ops_apply, ops_landmarks
from . import ops_project as P

ensure_engine_on_path()

from face3d.core.policy import DataClass  # noqa: E402
from face3d.core.schema import FormatError, load_arrays  # noqa: E402
from face3d.handoff import keys as K  # noqa: E402
from face3d.mesh.subdiv import fit_cage_to_limit  # noqa: E402
from face3d.pipeline.project import ProjectError  # noqa: E402
from face3d.pipeline.stages import load_kit  # noqa: E402

MIN_LEVELS, MAX_LEVELS = 2, 3         # WP-22 spec: Multires 2-3 levels
MASK_ATTR = ".sculpt_mask"
#: DataClass names the purge operator can act on (others hold no user data in the project folder).
PURGE_CLASSES = ("PERSONAL_IMAGE", "BIOMETRIC_GEOMETRY")
#: Last sharing scan (list of dicts), shown by the Share panel.
SCAN = []


# ------------------------------------------------------------------ sculpt copy
def _link(scene, obj):
    coll = getattr(scene, "collection", None)
    if coll is not None:
        coll.objects.link(obj)


def _activate(context, obj):
    vl = getattr(context, "view_layer", None)
    if vl is not None:
        vl.objects.active = obj
    if hasattr(obj, "select_set"):
        obj.select_set(True)


def _fit_object(context, obj):
    """The fitted object behind ``obj``: itself, or the source of a sculpt copy."""
    src = obj.get("f3d_sculpt_of") if "f3d_sculpt_of" in obj else None
    if src:
        return bpy.data.objects.get(src) if hasattr(bpy.data.objects, "get") else None
    return obj


def make_cage(context, V_mix_mm):
    """Limit-fitted cage (mm) of the baked mix, or the mix itself for a non-quad template (see module doc)."""
    prj = P.load_project(context)
    kit = load_kit(prj.template, prj.root)
    if kit.is_quad and len(kit.vertices) == len(V_mix_mm):
        return np.asarray(fit_cage_to_limit(V_mix_mm, np.asarray(kit.faces)), dtype=np.float64), prj
    return np.asarray(V_mix_mm, dtype=np.float64), prj


def new_sculpt_copy(context, src, cage_mm, prj, name):
    """Duplicate ``src`` into a key-free object whose base mesh is ``cage_mm`` (engine mm); returns it."""
    me = src.data.copy()
    me.name = name
    obj = bpy.data.objects.new(name, me)
    _link(context.scene, obj)
    obj.shape_key_clear()
    bridge.write_vertices(me, bridge.engine_mm_to_blender_m(cage_mm))
    sdir = prj.root / "sculpt"
    sdir.mkdir(parents=True, exist_ok=True)
    uid = ops_apply.object_uuid(prj, obj)
    np.save(sdir / (uid + ".npy"), np.asarray(cage_mm, dtype=np.float64), allow_pickle=False)
    obj["f3d_sculpt_of"] = src.name
    obj["f3d_sculpt_cage"] = os.path.join("sculpt", uid + ".npy")
    obj["face3d_uuid"] = uid
    return obj


def add_multires(context, obj, levels):
    """Add Multires and subdivide ``levels`` times through guarded bpy.ops calls; False on failure."""
    try:
        _activate(context, obj)
        bpy.ops.object.modifier_add(type="MULTIRES")
        for _ in range(levels):
            bpy.ops.object.multires_subdivide(modifier="Multires", mode="CATMULL_CLARK")
        return True
    except (RuntimeError, AttributeError, TypeError):
        return False


def _fit_poll(cls, context):
    if P.project_root(context) is None:
        return P.deny(cls, "no_project")
    if P.job_is_running(context):
        return P.deny(cls, "job_running")
    obj = getattr(context, "active_object", None) or getattr(context, "object", None)
    if obj is None or getattr(obj, "type", "") != "MESH":
        return P.deny(cls, "no_mesh_object")
    if getattr(obj, "mode", "OBJECT") in ("EDIT", "SCULPT"):
        return P.deny(cls, "wrong_mode")
    return True


class FACE3D_OT_handoff_sculpt(bpy.types.Operator):
    bl_idname = "face3d.handoff_sculpt"
    bl_label = "Start Sculpting"
    bl_description = "Make a sculpt copy with a Multires modifier; the fitted object keeps its shape keys"
    bl_options = {"REGISTER", "UNDO"}

    levels: IntProperty(name="Multires levels", default=MIN_LEVELS, min=MIN_LEVELS, max=MAX_LEVELS)

    @classmethod
    def poll(cls, context):
        return _fit_poll(cls, context)

    def execute(self, context):
        try:
            src = _fit_object(context, getattr(context, "active_object", None) or context.object)
            if src is None:
                return P.fail(self, "no_mesh_object")
            with bridge.mode_guard(src):
                ks, _ = ops_apply.stack_from_object(src)
                if ks is None:
                    return P.fail(self, "no_keys")
                cage, prj = make_cage(context, ks.evaluate())
                obj = new_sculpt_copy(context, src, cage, prj, src.name + "_sculpt")
            ok = add_multires(context, obj, self.levels)
            P.info(self, "handoff_done" if ok else "handoff_multires_failed")
            return {"FINISHED"}
        except bridge.BridgeRefusal:
            return P.fail(self, "wrong_mode")
        except (ProjectError, OSError, ValueError, KeyError, RuntimeError):
            return P.fail(self, "internal_error")
        except Exception:  # noqa: BLE001
            return P.fail(self, "internal_error")


class FACE3D_OT_rebase_sculpt(bpy.types.Operator):
    bl_idname = "face3d.rebase_sculpt"
    bl_label = "Rebase Sculpt on New Fit"
    bl_description = "Make a new sculpt copy from the refitted shape that carries your coarse edits"
    bl_options = {"REGISTER", "UNDO"}

    levels: IntProperty(name="Multires levels", default=MIN_LEVELS, min=MIN_LEVELS, max=MAX_LEVELS)

    @classmethod
    def poll(cls, context):
        if not _fit_poll(cls, context):
            return False
        obj = getattr(context, "active_object", None) or context.object
        if "f3d_sculpt_of" not in obj:
            return P.deny(cls, "sculpt_needs_copy")
        return True

    def execute(self, context):
        try:
            copy = getattr(context, "active_object", None) or context.object
            src = _fit_object(context, copy)
            if src is None:
                return P.fail(self, "no_mesh_object")
            prj = P.load_project(context)
            then = np.load(str(prj.root / copy["f3d_sculpt_cage"]), allow_pickle=False)
            with bridge.mode_guard(src), bridge.mode_guard(copy):
                ks, _ = ops_apply.stack_from_object(src)
                if ks is None:
                    return P.fail(self, "no_keys")
                now = bridge.blender_m_to_engine_mm(bridge.mesh_vertices_to_array(copy.data))
                edit = now - then                                  # the artist's coarse (cage-level) edits, mm
                cage, prj = make_cage(context, ks.evaluate())
                obj = new_sculpt_copy(context, src, cage + edit, prj, src.name + "_sculpt")
            ok = add_multires(context, obj, self.levels)
            P.info(self, "rebase_done" if ok else "handoff_multires_failed")
            return {"FINISHED"}
        except bridge.BridgeRefusal:
            return P.fail(self, "wrong_mode")
        except (ProjectError, OSError, ValueError, KeyError):
            return P.fail(self, "internal_error")
        except Exception:  # noqa: BLE001
            return P.fail(self, "internal_error")


class FACE3D_OT_protect_measured(bpy.types.Operator):
    bl_idname = "face3d.protect_measured"
    bl_label = "Protect Measured Regions"
    bl_description = "Mask the measured regions so sculpt brushes cannot move them (guessed regions stay free)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if not _fit_poll(cls, context):
            return False
        try:
            if not P.load_project(context).active_solve:
                return P.deny(cls, "no_result")
        except ProjectError:
            return P.deny(cls, "no_project")
        return True

    def execute(self, context):
        try:
            obj = getattr(context, "active_object", None) or context.object
            prj = P.load_project(context)
            arr = load_arrays(prj.root / prj.active_solve / "arrays.npz")
            support = arr.get("support")
            if support is None or len(support) != len(obj.data.vertices):
                return P.fail(self, "topology_mismatch")
            with bridge.mode_guard(obj):
                bridge.set_attribute(obj.data, MASK_ATTR, K.protect_mask(support), "POINT", "FLOAT")
            P.info(self, "protect_done")
            return {"FINISHED"}
        except bridge.BridgeRefusal:
            return P.fail(self, "wrong_mode")
        except (ProjectError, FormatError, OSError, ValueError, KeyError):
            return P.fail(self, "no_result")
        except Exception:  # noqa: BLE001
            return P.fail(self, "internal_error")


# ------------------------------------------------------------------ sharing and purge
def scan_shareables(context):
    """What a shared .blend would carry: a list of {kind, name, data_class} (read-only, no deletion).

    kinds: packed_image, background_image, orphan, file_preview, backup. data_class is the face3d DataClass
    name the item belongs to (images and backups: PERSONAL_IMAGE; orphan meshes: BIOMETRIC_GEOMETRY).
    """
    items = []
    for img in bpy.data.images:
        if getattr(img, "packed_file", None) is not None:
            items.append({"kind": "packed_image", "name": img.name, "data_class": "PERSONAL_IMAGE"})
    for cam in bpy.data.cameras:
        for bg in cam.background_images:
            if getattr(bg, "image", None) is not None:
                items.append({"kind": "background_image", "name": cam.name, "data_class": "PERSONAL_IMAGE"})
    for coll_name, dc in (("meshes", "BIOMETRIC_GEOMETRY"), ("images", "PERSONAL_IMAGE"), ("cameras", "PERSONAL_IMAGE")):
        for it in getattr(bpy.data, coll_name, []):
            if getattr(it, "users", 1) == 0:
                items.append({"kind": "orphan", "name": it.name, "data_class": dc})
    prefs = getattr(context, "preferences", None)
    if prefs is not None and getattr(prefs.filepaths, "file_preview_type", "NONE") != "NONE":
        items.append({"kind": "file_preview", "name": "file_preview_type", "data_class": "PERSONAL_IMAGE"})
    path = getattr(bpy.data, "filepath", "")
    if path:
        for b in sorted(glob.glob(path + "1")):
            items.append({"kind": "backup", "name": os.path.basename(b), "data_class": "PERSONAL_IMAGE"})
    return items


def purge_class(context, data_class):
    """Delete the project's data of ``data_class`` (PERSONAL_IMAGE or BIOMETRIC_GEOMETRY); returns the count."""
    if data_class not in PURGE_CLASSES:
        raise ValueError(data_class)
    prj = P.load_project(context)
    n = 0
    if data_class == "PERSONAL_IMAGE":
        pdir = prj.root / "photos"
        for f in sorted(pdir.glob("*.npy")) if pdir.is_dir() else []:
            f.unlink()
            n += 1
        for cam in bpy.data.cameras:
            for bg in list(cam.background_images):
                if getattr(bg, "image", None) is not None:
                    bg.image = None
                    n += 1
        for img in list(bpy.data.images):
            if getattr(img, "packed_file", None) is not None and hasattr(bpy.data.images, "remove"):
                bpy.data.images.remove(img)
                n += 1
        path = getattr(bpy.data, "filepath", "")
        for b in glob.glob(path + "1") if path else []:
            os.remove(b)
            n += 1
    else:
        n += prj.purge_kept_landmarks()
        jobs = prj.root / "jobs"
        if jobs.is_dir():
            n += sum(1 for _ in jobs.iterdir())
            shutil.rmtree(jobs)
        ops_landmarks.SESSION.pop(str(prj.root), None)
        ops_landmarks.PENDING.pop(str(prj.root), None)
    P.audit(prj, "purge", DataClass[data_class], "", "", "purge_" + data_class.lower())
    return n


class FACE3D_OT_prepare_for_sharing(bpy.types.Operator):
    bl_idname = "face3d.prepare_for_sharing"
    bl_label = "Prepare for Sharing"
    bl_description = "List the photos, previews and leftovers a shared file would contain; delete them only on confirmation"
    bl_options = {"REGISTER", "UNDO"}

    confirm: BoolProperty(name="Delete the listed personal data now", default=False)

    @classmethod
    def poll(cls, context):
        if P.project_root(context) is None:
            return P.deny(cls, "no_project")
        if P.job_is_running(context):
            return P.deny(cls, "job_running")
        return True

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        try:
            SCAN[:] = scan_shareables(context)
            if not SCAN:
                P.info(self, "share_clean")
            else:
                P.info(self, "share_listed", n=len(SCAN))
            if self.confirm and SCAN:
                n = purge_class(context, "PERSONAL_IMAGE")
                P.info(self, "purge_done", n=n)
                SCAN[:] = scan_shareables(context)
            context.scene["f3d_share_reviewed"] = True
            return {"FINISHED"}
        except (ProjectError, OSError, ValueError):
            return P.fail(self, "internal_error")
        except Exception:  # noqa: BLE001
            return P.fail(self, "internal_error")


class FACE3D_OT_purge(bpy.types.Operator):
    bl_idname = "face3d.purge"
    bl_label = "Purge Data"
    bl_description = "Delete the project's data of one class (photos' working copies, or landmarks and job folders)"
    bl_options = {"REGISTER", "UNDO"}

    data_class: EnumProperty(name="Data class", items=[(c, c.replace("_", " ").capitalize(), "") for c in PURGE_CLASSES],
                             default="PERSONAL_IMAGE")
    confirm: BoolProperty(name="Yes, delete", default=False)

    @classmethod
    def poll(cls, context):
        if P.project_root(context) is None:
            return P.deny(cls, "no_project")
        if P.job_is_running(context):
            return P.deny(cls, "job_running")
        return True

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        try:
            if not self.confirm:
                P.info(self, "purge_confirm")
                return {"CANCELLED"}
            n = purge_class(context, self.data_class)
            P.info(self, "purge_done", n=n)
            return {"FINISHED"}
        except (ProjectError, OSError, ValueError):
            return P.fail(self, "internal_error")
        except Exception:  # noqa: BLE001
            return P.fail(self, "internal_error")


CLASSES = (FACE3D_OT_handoff_sculpt, FACE3D_OT_rebase_sculpt, FACE3D_OT_protect_measured,
           FACE3D_OT_prepare_for_sharing, FACE3D_OT_purge)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
