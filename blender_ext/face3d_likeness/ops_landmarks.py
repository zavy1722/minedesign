# SPDX-License-Identifier: GPL-3.0-or-later
"""Landmark import, the pin tool and contour tracing (DESIGN 6.4, 6.7, D-09, D-25).

Conventions
-----------
* Pin coordinates are image pixels, top-left origin, y down (DESIGN 3.1); the viewport maps through the
  camera frame with `overlays.view_to_image_px`. A pin's `zoom` is the screen pixels per image pixel when
  it was placed (overlays.zoom_of_frame); the engine derives the pin sigma from it (DESIGN 4.4, D-09).
* Pin class: ``crisp`` takes its noise class from ``expertise`` (``crisp_novice`` / ``crisp_expert``,
  face3d.pipeline.project.resolve_pin_class); other classes are the engine's PIN_CLASSES names.
* Imported landmark sets are BIOMETRIC_GEOMETRY with TTL 0 (D-25): they are held in this process only
  (`SESSION`), passed to a job through its inputs, and never written to the project unless the user opted
  in to `landmark_cache.keep` (handled by the engine's pipeline).
* More than one detected face (score >= 0.6, the Q-FACES threshold) never picks a subject by itself: the
  set is parked and a Q-FACES card asks the user (card_accept with `face_index`).
* `trace_contour` snaps the clicked outline with face3d.fit.edge_snap synchronously on the working copy
  (a small Viterbi per station; DESIGN 4.16). The job protocol has no edge-snap stage, so this is not a
  background job (see notes of WP-22). Pixels come from the ``.npy`` working copy, not from bpy.
* The pin editor (`PinEditor`) is pure Python; the modal operator only translates events and view maps.
"""
import os

import bpy
import numpy as np
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty

from . import ensure_engine_on_path, overlays
from . import ops_project as P

ensure_engine_on_path()

from face3d.fit import edge_snap as _snap  # noqa: E402
from face3d.io import landmarks as _lm  # noqa: E402
from face3d.model.registry import SCHEME_DIR, load_scheme  # noqa: E402
from face3d.pipeline.project import Pin, ProjectError, resolve_pin_class  # noqa: E402
from face3d.qa import overlay_geom as og  # noqa: E402

DEFAULT_SCHEME = "anatomical44"
NUDGE_PX = 1.0                    # DESIGN 6.4: arrow keys nudge 1 image px
NUDGE_FINE_PX = 0.25              # Shift: 0.25 px
MIN_TRACE_CLICKS = 5              # DESIGN 4.16 "edge snap": >= 5 user clicks
FACE_SCORE_MIN = 0.6              # Q-FACES threshold (qa.faces_score, eth F1)
#: Inter-ocular distance used for the edge-snap band when no eye pins exist: PROVISIONAL, 0.2 of the image
#: width (typical head-and-shoulders framing); the band is only a search width (DESIGN 4.16).
DEFAULT_IOD_FRAC = 0.2
NEXT_LANDMARK = "NEXT"            # enum value of the landmark property: "the next unplaced landmark"
PIN_CLASS_ITEMS = [("crisp", "Crisp point", ""), ("contour", "Contour", ""), ("alar_base", "Alar base", ""),
                   ("nose_tip", "Nose tip", ""), ("ears", "Ear", ""), ("palpation", "Palpated", ""),
                   ("hair_defined", "Hair-defined", "")]

#: {project path string: {photo id: LandmarkSet}} session cache (never persisted, D-25).
SESSION = {}
#: {project path string: {photo id: LandmarkSet with several faces awaiting a choice}}
PENDING = {}


# ------------------------------------------------------------------ pure helpers
def scheme_names(scheme=DEFAULT_SCHEME):
    """Landmark names of a packaged scheme, in index order."""
    return [p.name for p in load_scheme(scheme).points]


def known_schemes():
    return sorted(p.stem for p in SCHEME_DIR.glob("*.json"))


def next_landmark(placed, names):
    """First name of ``names`` not in ``placed`` (else None)."""
    done = set(placed)
    for n in names:
        if n not in done:
            return n
    return None


def landmark_items(scheme=DEFAULT_SCHEME):
    """Enum items of the landmark choice: the automatic 'next unplaced' entry, then every scheme landmark."""
    return [(NEXT_LANDMARK, "Next unplaced", "Place the first landmark of the scheme that has no pin yet")] + \
        [(n, n.replace("_", " ").capitalize(), "") for n in scheme_names(scheme)]


def next_pin_name(context, landmark=NEXT_LANDMARK):
    """Name the next click will place on the active photo (None when every landmark has a pin)."""
    if landmark and landmark != NEXT_LANDMARK:
        return landmark
    pid = P.active_photo_id(context)
    return next_landmark([p["landmark"] for p in pins_of(context, pid)] if pid else [], scheme_names())


def session_sets(context):
    return SESSION.setdefault(str(P.settings(context).project_path), {})


def pending_sets(context):
    return PENDING.setdefault(str(P.settings(context).project_path), {})


class PinEditor:
    """Place, drag, nudge and delete pins of one photo (pure; no bpy).

    ``pins``: list of dicts ``{landmark, x, y, cls, expertise, zoom, blind}`` edited in place.
    ``image_wh``: (W, H) image pixels; positions are clamped to [0, W] x [0, H].
    `hit` picks the nearest pin within HIT_RADIUS_PX *screen* pixels (overlay_geom.HIT_RADIUS_PX), i.e.
    ``HIT_RADIUS_PX / zoom`` image pixels.
    """

    def __init__(self, pins, image_wh):
        self.pins = pins
        self.wh = (float(image_wh[0]), float(image_wh[1]))
        self.selected = None          # index into pins
        self.dragging = False
        self.dirty = False

    def _clamp(self, x, y):
        return (min(max(float(x), 0.0), self.wh[0]), min(max(float(y), 0.0), self.wh[1]))

    def hit(self, xy, zoom=1.0):
        best, bd = None, og.HIT_RADIUS_PX / max(float(zoom), 1e-9)
        for i, p in enumerate(self.pins):
            d = float(np.hypot(p["x"] - xy[0], p["y"] - xy[1]))
            if d <= bd:
                best, bd = i, d
        return best

    def press(self, xy, zoom, landmark=None, cls="crisp", expertise="novice", blind=False):
        """Press at image px ``xy``: grab the pin under the cursor, else place ``landmark`` (None = ignore).
        Returns 'grab', 'placed' or None."""
        i = self.hit(xy, zoom)
        if i is not None:
            self.selected, self.dragging = i, True
            return "grab"
        if landmark is None:
            return None
        x, y = self._clamp(*xy)
        existing = [k for k, p in enumerate(self.pins) if p["landmark"] == landmark]
        pin = {"landmark": landmark, "x": x, "y": y, "cls": cls, "expertise": expertise,
               "zoom": float(zoom), "blind": bool(blind)}
        if existing:                          # one pin per landmark and photo: re-placing moves it
            self.pins[existing[0]] = pin
            self.selected = existing[0]
        else:
            self.pins.append(pin)
            self.selected = len(self.pins) - 1
        self.dragging, self.dirty = True, True
        return "placed"

    def move(self, xy, zoom=None):
        """Drag: move the selected pin to ``xy`` (only while the button is held)."""
        if not self.dragging or self.selected is None:
            return False
        p = self.pins[self.selected]
        p["x"], p["y"] = self._clamp(*xy)
        if zoom is not None:
            p["zoom"] = float(zoom)
        self.dirty = True
        return True

    def release(self):
        """End a drag; True when something changed (the caller pushes ONE undo step)."""
        was = self.dragging and self.dirty
        self.dragging = False
        return was

    def nudge(self, dx, dy, fine=False):
        """Move the selected pin by (dx, dy) steps of 1 image px (0.25 px with ``fine``)."""
        if self.selected is None:
            return False
        step = NUDGE_FINE_PX if fine else NUDGE_PX
        p = self.pins[self.selected]
        p["x"], p["y"] = self._clamp(p["x"] + dx * step, p["y"] + dy * step)
        self.dirty = True
        return True

    def delete(self):
        """Delete the selected pin; returns its landmark name or None."""
        if self.selected is None:
            return None
        name = self.pins.pop(self.selected)["landmark"]
        self.selected, self.dragging, self.dirty = None, False, True
        return name


def pins_of(context, photo_id):
    """The scene pins of a photo as a list of plain dicts (the PinEditor's working list)."""
    return [{"landmark": p.landmark, "x": p.x, "y": p.y, "cls": p.cls, "expertise": p.expertise,
             "zoom": p.zoom, "blind": p.blind}
            for p in P.settings(context).pins if p.photo_id == photo_id]


def store_pins(context, photo_id, pins):
    """Replace the scene pins of ``photo_id`` by ``pins`` and mirror them to project.json."""
    s = P.settings(context)
    keep = [(p.photo_id, p.landmark, p.x, p.y, p.cls, p.expertise, p.zoom, p.blind)
            for p in s.pins if p.photo_id != photo_id]
    s.pins.clear()
    for pid, lm, x, y, cls, ex, z, bl in keep:
        it = s.pins.add()
        it.photo_id, it.landmark, it.x, it.y, it.cls, it.expertise, it.zoom, it.blind = pid, lm, x, y, cls, ex, z, bl
    for p in pins:
        it = s.pins.add()
        it.photo_id, it.landmark, it.x, it.y = photo_id, p["landmark"], p["x"], p["y"]
        it.cls, it.expertise, it.zoom, it.blind = p["cls"], p["expertise"], p["zoom"], p["blind"]
    prj = P.load_project(context)
    prj.pins = [Pin(photo=p.photo_id, landmark=p.landmark, xy_px=(p.x, p.y), cls=p.cls,
                    expertise=p.expertise, zoom=max(p.zoom, 1e-6)) for p in s.pins]
    prj.save()


# ------------------------------------------------------------------ operators
class FACE3D_OT_landmarks_import(bpy.types.Operator):
    bl_idname = "face3d.landmarks_import"
    bl_label = "Import Landmarks"
    bl_description = "Import a LandmarkSet JSON for a photo (the scheme must be named in the file)"
    bl_options = {"REGISTER", "UNDO"}

    filepath: StringProperty(subtype="FILE_PATH")
    photo_id: StringProperty(name="Photo", description="Empty = the active photo camera")

    @classmethod
    def poll(cls, context):
        root = P.project_root(context)
        if root is None:
            return P.deny(cls, "no_project")
        if not P.settings(context).photos:
            return P.deny(cls, "no_photos")
        if P.job_is_running(context):
            return P.deny(cls, "job_running")
        ok, key = P.consent_state(root, "reconstruct", None)
        return True if ok else P.deny(cls, key)

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        try:
            s = P.settings(context)
            pid = self.photo_id or P.active_photo_id(context) or (s.photos[0].id if len(s.photos) else "")
            if pid not in [p.id for p in s.photos]:
                return P.fail(self, "no_active_photo")
            try:
                ls = _lm.load_landmarks(self.filepath)
            except (OSError, ValueError, KeyError, TypeError):
                return P.fail(self, "landmarks_read_failed")
            if not ls.scheme:
                return P.fail(self, "landmarks_scheme_missing")
            if ls.scheme not in known_schemes():
                return P.fail(self, "landmarks_scheme_unknown")
            strong = [i for i, f in enumerate(ls.faces) if f.score >= FACE_SCORE_MIN]
            if len(ls.faces) > 1 and len(strong) == 1:
                # exactly one confident face: keep only it, because the engine always fits faces[0]
                # (a weak background face listed first would otherwise be fitted, with no card)
                ls = _lm.LandmarkSet(ls.scheme, ls.detector, ls.image, [_lm.select_face(ls, strong[0])])
            elif len(ls.faces) > 1:                   # several strong faces, or none: the user picks (D-10)
                pending_sets(context)[pid] = ls
                overlays.set_data("auto_landmarks", pid, np.vstack([np.asarray(f.uv, float) for f in ls.faces]))
                c = s.cards.add()
                c.code, c.severity, c.msg_key, c.photo_id, c.decided = "Q-FACES", "warn", "pick_subject", pid, False
                P.warn(self, "pick_subject")
                return {"FINISHED"}
            session_sets(context)[pid] = ls
            _show_auto_landmarks(pid, ls.faces[0] if ls.faces else None)
            P.info(self, "landmarks_imported")
            return {"FINISHED"}
        except Exception:  # noqa: BLE001
            return P.fail(self, "internal_error")


def _show_auto_landmarks(photo_id, face):
    """Feed the overlay with the imported landmarks of ``face`` (image px) and the face width they span."""
    if face is None:
        return
    uv = np.asarray(face.uv, dtype=np.float64)
    if uv.ndim != 2 or not len(uv):
        return
    overlays.set_data("auto_landmarks", photo_id, uv)
    width = float(np.ptp(uv[:, 0]))
    if width > 0:                       # PROVISIONAL face width for the blur: x-extent of the landmarks
        overlays.STATE["face_width_px"] = width


def choose_face(context, photo_id, face_index):
    """Resolve a parked multi-face set: keep only the chosen face (user decision, never automatic).

    Non-destructive until it succeeds: a bad ``face_index`` leaves the parked set in place, so the redo panel
    or the next click can still choose. Returns False when there is no parked set or the index is not a face.
    """
    ls = pending_sets(context).get(photo_id)
    if ls is None or not 0 <= int(face_index) < len(ls.faces):
        return False
    face = _lm.select_face(ls, int(face_index))
    session_sets(context)[photo_id] = _lm.LandmarkSet(ls.scheme, ls.detector, ls.image, [face])
    pending_sets(context).pop(photo_id, None)
    _show_auto_landmarks(photo_id, face)
    return True


def _region_xy(event):
    return (float(event.mouse_region_x), float(event.mouse_region_y))


class FACE3D_OT_pin_place(bpy.types.Operator):
    bl_idname = "face3d.pin_place"
    bl_label = "Place Pin"
    bl_description = "Click to place a landmark pin, drag to move, arrows nudge, X deletes"
    bl_options = {"REGISTER", "UNDO"}

    landmark: EnumProperty(name="Landmark", description="The landmark the next click places (Next unplaced = "
                           "scheme order; pick another to skip one the photo does not show)",
                           items=landmark_items(), default=NEXT_LANDMARK)
    pin_class: EnumProperty(name="Pin class", items=PIN_CLASS_ITEMS, default="crisp")
    expertise: EnumProperty(name="Expertise", items=[("novice", "Novice", ""), ("expert", "Expert", "")],
                            default="novice")
    blind: BoolProperty(name="Blind first pins", description="Hide the automatic landmarks while placing the "
                        "first pins", default=False)

    _editor = None
    _photo = None
    _wh = (0, 0)

    @classmethod
    def poll(cls, context):
        if P.project_root(context) is None:
            return P.deny(cls, "no_project")
        if P.active_photo_id(context) is None:
            return P.deny(cls, "pin_need_camera")
        return True

    # -- the view mapping is isolated so tests can replace it
    def _frame(self, context):
        return overlays.frame_corners_region(context)

    def invoke(self, context, event):
        corners = self._frame(context)
        if corners is None:
            return P.fail(self, "pin_need_camera")
        cam = context.scene.camera
        self._photo = cam["f3d_photo_id"]
        self._wh = (int(cam.get("f3d_res_x", 0)), int(cam.get("f3d_res_y", 0)))
        try:
            resolve_pin_class(self.pin_class, self.expertise)           # validate the class/expertise pair
        except ProjectError:
            return P.fail(self, "internal_error")
        self._editor = PinEditor(pins_of(context, self._photo), self._wh)
        if self.blind and not self._editor.pins:
            overlays.STATE["hide_auto"] = True
        P.info(self, "pin_help")
        self._announce_next()
        context.window_manager.modal_handler_add(self)
        if event is not None and getattr(event, "type", None) == "LEFTMOUSE" and getattr(event, "value", None) == "PRESS":
            # the tool keymap invokes us ON the press that starts the session: it must place or grab a pin too
            r = self.modal(context, event)
            return {"RUNNING_MODAL"} if "PASS_THROUGH" in r else r
        return {"RUNNING_MODAL"}

    def _announce_next(self):
        name = self._next_name()
        P.info(self, "pin_next" if name else "pin_next_none", name=name or "")

    def _finish(self, context, result):
        overlays.STATE["hide_auto"] = False
        overlays.STATE["selected_pin"] = None
        if self._editor is not None and self._editor.dirty:
            store_pins(context, self._photo, self._editor.pins)
        return result

    def _next_name(self):
        if self.landmark and self.landmark != NEXT_LANDMARK:
            return self.landmark
        return next_landmark([p["landmark"] for p in self._editor.pins], scheme_names())

    def modal(self, context, event):
        ed = self._editor
        if event.type in ("ESC", "RIGHTMOUSE") and event.value == "PRESS":
            return self._finish(context, {"FINISHED"})
        corners = self._frame(context)
        if corners is None:
            return self._finish(context, {"CANCELLED"})
        zoom = overlays.zoom_of_frame(corners, self._wh)
        if event.type == "LEFTMOUSE":
            xy = overlays.view_to_image_px(_region_xy(event), corners, self._wh)
            if event.value == "PRESS":
                act = ed.press(xy, zoom, self._next_name(), self.pin_class, self.expertise,
                               overlays.STATE["hide_auto"])
                if act == "placed":
                    self.landmark = NEXT_LANDMARK        # a chosen landmark applies to one click only
                    self._announce_next()
                self._select(ed)
                return {"RUNNING_MODAL"} if act else {"PASS_THROUGH"}
            if event.value == "RELEASE":
                if ed.release():
                    store_pins(context, self._photo, ed.pins)
                    ed.dirty = False
                    self._undo_push()
                return {"RUNNING_MODAL"}
        if event.type == "MOUSEMOVE" and ed.dragging:
            ed.move(overlays.view_to_image_px(_region_xy(event), corners, self._wh), zoom)
            return {"RUNNING_MODAL"}
        if event.value == "PRESS":
            arrows = {"LEFT_ARROW": (-1, 0), "RIGHT_ARROW": (1, 0), "UP_ARROW": (0, -1), "DOWN_ARROW": (0, 1)}
            if event.type in arrows and ed.nudge(*arrows[event.type], fine=bool(event.shift)):
                return {"RUNNING_MODAL"}
            if event.type == "X" and ed.delete() is not None:
                store_pins(context, self._photo, ed.pins)
                ed.dirty = False
                P.info(self, "pin_deleted")
                self._undo_push()
                self._select(ed)
                return {"RUNNING_MODAL"}
        return {"PASS_THROUGH"}

    def _select(self, ed):
        if ed.selected is not None and ed.selected < len(ed.pins):
            overlays.STATE["selected_pin"] = (self._photo, ed.pins[ed.selected]["landmark"])
        else:
            overlays.STATE["selected_pin"] = None

    def _undo_push(self):
        try:
            bpy.ops.ed.undo_push(message="Face3D pin")      # one undo step per drag or deletion
        except (RuntimeError, AttributeError):
            pass

    def execute(self, context):
        """Placement is interactive only (invoke/modal); a scripted call does nothing."""
        return {"CANCELLED"}

    def cancel(self, context):
        overlays.STATE["hide_auto"] = False


class FACE3D_OT_trace_contour(bpy.types.Operator):
    bl_idname = "face3d.trace_contour"
    bl_label = "Trace Contour"
    bl_description = "Click the face outline (at least 5 points); it snaps to the nearest image edge"
    bl_options = {"REGISTER", "UNDO"}

    closed: BoolProperty(name="Closed outline", default=False)

    _clicks = None
    _photo = None
    _wh = (0, 0)

    @classmethod
    def poll(cls, context):
        if P.project_root(context) is None:
            return P.deny(cls, "no_project")
        if P.active_photo_id(context) is None:
            return P.deny(cls, "pin_need_camera")
        if P.job_is_running(context):
            return P.deny(cls, "job_running")
        return True

    def _frame(self, context):
        return overlays.frame_corners_region(context)

    def invoke(self, context, event):
        if self._frame(context) is None:
            return P.fail(self, "pin_need_camera")
        cam = context.scene.camera
        self._photo = cam["f3d_photo_id"]
        self._wh = (int(cam.get("f3d_res_x", 0)), int(cam.get("f3d_res_y", 0)))
        self._clicks = []
        P.info(self, "trace_help")
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type == "ESC" and event.value == "PRESS":
            return {"CANCELLED"}
        corners = self._frame(context)
        if corners is None:
            return {"CANCELLED"}
        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            self._clicks.append(overlays.view_to_image_px(_region_xy(event), corners, self._wh))
            overlays.set_data("traced", self._photo, np.asarray(self._clicks))
            return {"RUNNING_MODAL"}
        if event.type in ("RET", "NUMPAD_ENTER") and event.value == "PRESS":
            if len(self._clicks) < MIN_TRACE_CLICKS:
                P.warn(self, "trace_too_few")
                return {"RUNNING_MODAL"}
            return self._snap(context)
        return {"PASS_THROUGH"}

    def _iod_px(self, context):
        pins = {p["landmark"]: p for p in pins_of(context, self._photo)}
        a, b = pins.get("pupil_R"), pins.get("pupil_L")      # anatomical44 names
        if a and b:
            return float(np.hypot(a["x"] - b["x"], a["y"] - b["y"]))
        return DEFAULT_IOD_FRAC * float(self._wh[0])

    def _gray(self, context):
        from face3d.io.image_ops import to_gray
        root = P.settings(context).project_path
        arr = np.load(os.path.join(root, "photos", self._photo + ".npy"), allow_pickle=False)
        return to_gray(arr)

    def _snap(self, context):
        try:
            res = _snap.edge_snap(self._gray(context), np.asarray(self._clicks, float),
                                  self._iod_px(context), closed=self.closed)
            overlays.set_data("traced", self._photo, np.asarray(res.points))
            P.info(self, "trace_done")
            return {"FINISHED"}
        except (OSError, ValueError):
            return P.fail(self, "internal_error")

    def execute(self, context):
        return {"CANCELLED"}


def _tool_cls():
    class FACE3D_TOOL_pin(bpy.types.WorkSpaceTool):
        bl_space_type = "VIEW_3D"
        bl_context_mode = "OBJECT"
        bl_idname = "face3d.pin_tool"
        bl_label = "Face3D Pin"
        bl_description = "Place and move landmark pins on the photo (P)"
        bl_icon = "ops.generic.select"
        bl_widget = None
        bl_keymap = (("face3d.pin_place", {"type": "LEFTMOUSE", "value": "PRESS"}, None),)

        def draw_settings(context, layout, tool):
            props = tool.operator_properties("face3d.pin_place")
            name = next_pin_name(context, getattr(props, "landmark", NEXT_LANDMARK))
            layout.label(text=P.text("pin_next" if name else "pin_next_none", name=name or ""))
            for prop in ("landmark", "pin_class", "expertise", "blind"):
                layout.prop(props, prop)
            layout.label(text=P.text("pin_help"))
    return FACE3D_TOOL_pin


CLASSES = (FACE3D_OT_landmarks_import, FACE3D_OT_pin_place, FACE3D_OT_trace_contour)
_tool = None


def register():
    global _tool
    for c in CLASSES:
        bpy.utils.register_class(c)
    if _tool is None:
        _tool = _tool_cls()
        bpy.utils.register_tool(_tool, after={"builtin.cursor"}, separator=True, group=False)


def unregister():
    global _tool
    if _tool is not None:
        bpy.utils.unregister_tool(_tool)
        _tool = None
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
