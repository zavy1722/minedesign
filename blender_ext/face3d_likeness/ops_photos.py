# SPDX-License-Identifier: GPL-3.0-or-later
"""Photo operators: add (hash, EXIF, working copy, QA cards, camera), review and view stepping (DESIGN 6.4).

Conventions
-----------
* One photo = one project PhotoRecord + one ``.npy`` working copy (``photos/<id>.npy``, float32 RGB,
  rows top-down, values as Blender reports them; EXIF GPS and every other tag are NOT carried into the
  copy, DESIGN D-25 / eth F9) + one locked camera object ``F3D_cam_<id>`` (custom property
  ``f3d_photo_id``) showing the photo as a background image at alpha 0.4 + one timeline marker.
* Blender does not apply EXIF orientation when it loads an image, so a photo whose EXIF orientation is
  not 1 is refused with ``convert_to_png`` (the pins would otherwise be placed in the wrong frame,
  DESIGN Q-ORIENT). HEIF files that Blender cannot load get the same message.
* Only `bridge.image_to_array` / `bridge.save_working_copy` touch pixel data (bridge rule, DESIGN 6.2).
* Consent: a photo whose SHA-256 is not in the consent record is blocked unless the user ticks
  ``consent_covers`` ("these photos are covered"), which adds the hash to the record and audits it.
* The initial camera focal length is the EXIF 35 mm equivalent on a 36 mm sensor when present, else
  50 mm; it is a placeholder until a solve is applied (PROVISIONAL, DESIGN 4.3 owns the real value).
"""
import os
from pathlib import Path

import bpy
import numpy as np
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, StringProperty

from . import bridge, ensure_engine_on_path
from . import ops_project as P

ensure_engine_on_path()

from face3d.core.policy import RIGHTS_BASES, DataClass  # noqa: E402
from face3d.core.schema import sha256_file  # noqa: E402
from face3d.io import image_ops  # noqa: E402
from face3d.pipeline.project import ProjectError, exif_from_summary  # noqa: E402
from face3d.qa import checks as qa  # noqa: E402

BACKGROUND_ALPHA = 0.4          # DESIGN 6.4 / WP-22 spec
SEVERITY_RANK = {"block": 0, "warn": 1, "info": 2}
DEFAULT_LENS_MM = 50.0          # PROVISIONAL placeholder (see module docstring)
SENSOR_WIDTH_MM = 36.0
_FILE_ELEM = getattr(bpy.types, "OperatorFileListElement", bpy.types.PropertyGroup)


# ------------------------------------------------------------------ helpers
def cameras(context=None):
    """Photo camera objects ordered by their ``f3d_index`` custom property."""
    objs = [o for o in bpy.data.objects if getattr(o, "type", "") == "CAMERA" and "f3d_photo_id" in o]
    return sorted(objs, key=lambda o: (o.get("f3d_index", 0), o.name))


def camera_for_photo(photo_id):
    for o in cameras():
        if o["f3d_photo_id"] == photo_id:
            return o
    return None


def _link(scene, obj):
    coll = getattr(scene, "collection", None)
    if coll is not None:
        coll.objects.link(obj)


def make_photo_camera(scene, photo_id, index, image, f35, wh):
    """Create the locked camera of a photo with its background image and timeline marker."""
    lens = float(f35) if f35 else DEFAULT_LENS_MM
    cam = bpy.data.cameras.new("F3D_cam_" + photo_id)
    cam.lens, cam.sensor_width, cam.sensor_fit = lens, SENSOR_WIDTH_MM, "HORIZONTAL"
    cam.show_background_images = True
    bg = cam.background_images.new()
    bg.image = image
    bg.alpha = BACKGROUND_ALPHA
    obj = bpy.data.objects.new("F3D_cam_" + photo_id, cam)
    obj["f3d_photo_id"] = photo_id
    obj["f3d_index"] = int(index)
    obj["f3d_res_x"], obj["f3d_res_y"] = int(wh[0]), int(wh[1])
    obj.lock_location = (True, True, True)
    obj.lock_rotation = (True, True, True)
    obj.lock_scale = (True, True, True)
    _link(scene, obj)
    marker = scene.timeline_markers.new("F3D_" + photo_id, frame=int(index) + 1)
    try:
        marker.camera = obj                     # stepping the timeline switches the scene camera
    except (AttributeError, TypeError):
        pass
    return obj


def sync_render_resolution(scene, cam_obj):
    """Set the scene render resolution to the photo's (stored per camera as f3d_res_x/y), pixel aspect 1.

    Blender keeps resolution per scene, not per camera; without this the camera frame takes the scene's
    aspect and the background photo no longer lines up with the solved camera (DESIGN 6.4, bl C5).
    """
    w, h = int(cam_obj.get("f3d_res_x", 0)), int(cam_obj.get("f3d_res_y", 0))
    if w <= 0 or h <= 0:
        return False
    r = scene.render
    r.resolution_x, r.resolution_y = w, h
    r.pixel_aspect_x = r.pixel_aspect_y = 1.0
    return True


def cards_from_findings(s, findings, dedupe=False):
    """Append one F3DCard per QA Finding (code, severity, msg_key, photo_id); returns the cards.

    ``dedupe`` skips a finding whose (code, photo) already has a card, decided or not (set-level checks are
    re-run over all photos on every add and must not ask the same question twice).
    """
    out = []
    for f in findings:
        if dedupe and any(c.code == f.code and c.photo_id == (f.photo_id or "") for c in s.cards):
            continue
        c = s.cards.add()
        c.code, c.severity, c.msg_key = f.code, f.severity, f.msg_key
        c.photo_id = f.photo_id or ""
        c.decided = False
        out.append(c)
    return out


def card_order(cards):
    """Indices of undecided cards, worst first (block, warn, info), stable by original order."""
    idx = [i for i, c in enumerate(cards) if not c.decided]
    return sorted(idx, key=lambda i: (SEVERITY_RANK.get(cards[i].severity, 3), i))


def _paths(op):
    d = op.directory
    files = [f.name for f in op.files if getattr(f, "name", "")]
    if files:
        return [os.path.join(d, n) for n in files]
    return [op.filepath] if op.filepath else []


# ------------------------------------------------------------------ operators
class FACE3D_OT_photos_add(bpy.types.Operator):
    bl_idname = "face3d.photos_add"
    bl_label = "Add Photos"
    bl_description = "Add photos: hash, read camera info, make a working copy, check quality, create a locked camera"
    bl_options = {"REGISTER", "UNDO"}

    directory: StringProperty(subtype="DIR_PATH")
    filepath: StringProperty(subtype="FILE_PATH")
    files: CollectionProperty(type=_FILE_ELEM, options={"HIDDEN", "SKIP_SAVE"})
    rights_basis: EnumProperty(name="Right to use", items=[(r, r.replace("_", " ").capitalize(), "")
                                                           for r in sorted(RIGHTS_BASES)], default="self_shot")
    consent_covers: BoolProperty(name="These photos are covered by the consent record",
                                 description="Adds the photo hashes to the consent record (audited)",
                                 default=False)

    @classmethod
    def poll(cls, context):
        root = P.project_root(context)
        if root is None:
            return P.deny(cls, "no_project")
        if P.job_is_running(context):
            return P.deny(cls, "job_running")
        ok, key = P.consent_state(root, "reconstruct", None)
        return True if ok else P.deny(cls, key)

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        try:
            return self._run(context)
        except ProjectError:
            return P.fail(self, "project_load_failed")
        except Exception:  # noqa: BLE001 - UI boundary
            return P.fail(self, "internal_error")

    def _run(self, context):
        root = P.project_root(context)
        prj = P.load_project(context)
        rec_consent = P.load_consent(root)
        if rec_consent is None:
            return P.fail(self, "consent_missing")
        paths = _paths(self)
        if not paths:
            return P.fail(self, "no_photos")
        s = P.settings(context)
        ctxs, added = [], 0
        for path in paths:
            res = self._add_one(context, prj, root, rec_consent, Path(path), s)
            if res is not None:
                ctxs.append(res)
                added += 1
        if ctxs:
            cards_from_findings(s, qa.run_set_checks(self._all_contexts(prj, root)), dedupe=True)
            prj.save()
        return {"FINISHED"} if added else {"CANCELLED"}

    @staticmethod
    def _all_contexts(prj, root):
        """PhotoContexts of EVERY project photo (set-level QA must see the whole set, not one add batch)."""
        out = []
        for rec in prj.photos:
            if not rec.working_copy:
                continue
            try:
                arr = np.load(str(root / rec.working_copy), allow_pickle=False)
            except (OSError, ValueError):
                continue
            out.append(qa.PhotoContext(photo_id=rec.id, exif=exif_from_summary(rec.exif),
                                       width=int(arr.shape[1]), height=int(arr.shape[0]),
                                       image_gray=image_ops.to_gray(arr)))
        return out

    def _add_one(self, context, prj, root, consent, src, s):
        """Add one file; returns its PhotoContext, or None when it was skipped (a message was reported)."""
        if not src.is_file():
            P.warn(self, "photo_failed")
            return None
        sha = sha256_file(src)
        if any(p.sha256 == sha for p in prj.photos):
            P.warn(self, "photo_exists")
            return None
        needs_consent = sha not in consent.photo_sha256
        if needs_consent and not self.consent_covers:
            P.warn(self, "photo_not_consented")
            return None
        try:
            img, w, h = bridge.load_image(src)
        except (RuntimeError, OSError):
            P.warn(self, "convert_to_png")
            return None
        if w <= 0 or h <= 0:
            bridge.remove_image(img)
            P.warn(self, "convert_to_png")
            return None
        try:
            rec = prj.add_photo(src, self.rights_basis)
        except Exception:  # noqa: BLE001 - unreadable EXIF/HEIF container, duplicate, bad basis: skip the file
            bridge.remove_image(img)
            P.warn(self, "photo_failed")
            return None
        orientation = int(rec.exif.get("orientation") or 1)
        if orientation != 1:
            prj.photos.remove(rec)
            bridge.remove_image(img)
            P.warn(self, "convert_to_png")
            return None
        if needs_consent:       # the record is extended only now: every check above has passed
            consent.photo_sha256 = sorted(set(consent.photo_sha256) | {sha})
            P.save_consent(root, consent)
            P.audit(prj, "consent_photo_added", DataClass.PERSONAL_IMAGE, sha, "RECONSTRUCT", "user_granted")
            P.info(self, "consent_photo_added")
        arr = bridge.image_to_array(img)[..., :3]
        photos_dir = root / "photos"
        photos_dir.mkdir(parents=True, exist_ok=True)
        saved = bridge.save_working_copy(np.ascontiguousarray(arr, dtype=np.float32), photos_dir / rec.id)
        rec.working_copy = os.path.relpath(saved, root)
        info = exif_from_summary(rec.exif)
        findings = qa.run_photo_checks(qa.PhotoContext(
            photo_id=rec.id, exif=info, width=w, height=h, orientation_applied=True,
            image_gray=image_ops.to_gray(arr), image_rgb=arr, consent_ok=True))
        cards_from_findings(s, findings)
        idx = len(s.photos)
        make_photo_camera(context.scene, rec.id, idx, img, info.focal_35mm, (w, h))
        item = s.photos.add()
        item.id, item.path, item.sha256 = rec.id, str(src), sha
        item.include, item.status = "auto", "added"
        P.audit(prj, "photo_added", DataClass.PERSONAL_IMAGE, sha, "RECONSTRUCT", "added")
        P.info(self, "photo_added")
        return qa.PhotoContext(photo_id=rec.id, exif=info, width=w, height=h,
                               image_gray=image_ops.to_gray(arr), image_rgb=None)


def _goto_photo(context, photo_id):
    cam = camera_for_photo(photo_id)
    if cam is None:
        return False
    context.scene.camera = cam
    sync_render_resolution(context.scene, cam)
    context.scene["f3d_active_photo"] = photo_id
    context.scene.frame_current = int(cam.get("f3d_index", 0)) + 1
    return True


class _StepBase:
    """Shared invoke guard: a key press outside a photo camera passes through to Blender."""

    keyed: BoolProperty(default=False, options={"HIDDEN"})

    def invoke(self, context, event):
        if self.keyed and not P.keyed_active(context):
            return {"PASS_THROUGH"}
        return self.execute(context)


class FACE3D_OT_review_next(_StepBase, bpy.types.Operator):
    bl_idname = "face3d.review_next"
    bl_label = "Review Next Finding"
    bl_description = "Go to the photo of the next open finding, worst first"
    bl_options = {"REGISTER"}
    step: BoolProperty(default=True, options={"HIDDEN"})   # True = forward

    @classmethod
    def poll(cls, context):
        if P.project_root(context) is None:
            return P.deny(cls, "no_project")
        if not card_order(P.settings(context).cards):
            return P.deny(cls, "review_empty")
        return True

    def execute(self, context):
        s = P.settings(context)
        order = card_order(s.cards)
        if not order:
            return P.fail(self, "review_empty")
        cur = int(context.scene.get("f3d_review_idx", -1))
        pos = order.index(cur) if cur in order else (-1 if self.step else 0)
        pick = order[(pos + (1 if self.step else -1)) % len(order)]      # worst-first queue, wraps
        context.scene["f3d_review_idx"] = pick
        card = s.cards[pick]
        _goto_photo(context, card.photo_id)
        s.rail_stage = "check"
        P.info(self, "review_card", card=P.text(card.msg_key))
        return {"FINISHED"}


class FACE3D_OT_review_prev(FACE3D_OT_review_next):
    bl_idname = "face3d.review_prev"
    bl_label = "Review Previous Finding"
    bl_description = "Go to the photo of the previous open finding"
    step: BoolProperty(default=False, options={"HIDDEN"})


class FACE3D_OT_view_next(_StepBase, bpy.types.Operator):
    bl_idname = "face3d.view_next"
    bl_label = "Next Photo Camera"
    bl_description = "Step the scene camera to the next photo"
    bl_options = {"REGISTER"}
    step: BoolProperty(default=True, options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        if not cameras():
            return P.deny(cls, "view_none")
        return True

    def execute(self, context):
        cams = cameras()
        if not cams:
            return P.fail(self, "view_none")
        cur = P.active_photo_id(context)
        ids = [c["f3d_photo_id"] for c in cams]
        i = ids.index(cur) if cur in ids else (-1 if self.step else 0)
        _goto_photo(context, ids[(i + (1 if self.step else -1)) % len(ids)])
        return {"FINISHED"}


class FACE3D_OT_view_prev(FACE3D_OT_view_next):
    bl_idname = "face3d.view_prev"
    bl_label = "Previous Photo Camera"
    bl_description = "Step the scene camera to the previous photo"
    step: BoolProperty(default=False, options={"HIDDEN"})


CLASSES = (FACE3D_OT_photos_add, FACE3D_OT_review_next, FACE3D_OT_review_prev,
           FACE3D_OT_view_next, FACE3D_OT_view_prev)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
