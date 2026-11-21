# SPDX-License-Identifier: GPL-3.0-or-later
"""Add-on keymap (DESIGN 6.4, D-22 key stack). Items live in ``keyconfigs.addon`` so users can remap them.

Key stack (3D View, Object Mode context):

====================  ==================================  =============================================
Key                   Operator                            Notes
====================  ==================================  =============================================
P                     wm.tool_set_by_id face3d.pin_tool   activates the pin tool
Tab / Shift-Tab       face3d.review_next / review_prev    worst-first review queue
PageDown / PageUp     face3d.view_next / view_prev        step the photo cameras
Ctrl-R                face3d.solve                        starts the solve job
Esc                   face3d.job_cancel                   only while a job runs (else the key passes on)
Ctrl-Enter            face3d.card_accept                  accept the finding under review
Ctrl-Backspace        face3d.card_dismiss                 dismiss it
F (hold)              face3d.compare_flip                 shows the flipped thumbnail while held
B / G / E             face3d.compare_mode blur/grey/edges comparison views (toggle)
W                     face3d.compare_mode wobble          reports 'not available yet' (deferred, DESIGN 6.5)
====================  ==================================  =============================================

Several of these keys have Blender defaults (Tab = edit mode, G = grab, E = extrude, B = box select ...).
Every operator therefore passes the key through (``PASS_THROUGH``) unless the scene camera is a Face3D photo
camera AND the viewport looks through it (``keyed`` property set here; `ops_project.keyed_active`), and
Esc/Ctrl-R only act through the operators' own polls. Ctrl-Enter / Ctrl-Backspace decide only the card under
review, and only if it belongs to the active photo.
`unregister` removes exactly the items and keymaps this module created.
"""
import bpy

KEYMAP_NAME = "3D View"
SPACE_TYPE = "VIEW_3D"

#: (operator id, key, value, shift, ctrl, operator properties)
ITEMS = (
    ("wm.tool_set_by_id", "P", "PRESS", False, False, {"name": "face3d.pin_tool"}),
    ("face3d.review_next", "TAB", "PRESS", False, False, {"keyed": True}),
    ("face3d.review_prev", "TAB", "PRESS", True, False, {"keyed": True}),
    ("face3d.view_next", "PAGE_DOWN", "PRESS", False, False, {"keyed": True}),
    ("face3d.view_prev", "PAGE_UP", "PRESS", False, False, {"keyed": True}),
    ("face3d.solve", "R", "PRESS", False, True, {"keyed": True}),
    ("face3d.job_cancel", "ESC", "PRESS", False, False, {}),
    ("face3d.card_accept", "RET", "PRESS", False, True, {"keyed": True}),
    ("face3d.card_dismiss", "BACK_SPACE", "PRESS", False, True, {"keyed": True}),
    ("face3d.compare_flip", "F", "PRESS", False, False, {"keyed": True}),
    ("face3d.compare_mode", "B", "PRESS", False, False, {"mode": "blur", "keyed": True}),
    ("face3d.compare_mode", "G", "PRESS", False, False, {"mode": "grey", "keyed": True}),
    ("face3d.compare_mode", "E", "PRESS", False, False, {"mode": "edges", "keyed": True}),
    ("face3d.compare_mode", "W", "PRESS", False, False, {"mode": "wobble", "keyed": True}),
)

_added = []      # [(keymap, item)]
_keymaps = []    # keymaps this module created


def register():
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc is None or _added:
        return
    km = None
    for existing in kc.keymaps:
        if existing.name == KEYMAP_NAME:
            km = existing
    if km is None:
        km = kc.keymaps.new(name=KEYMAP_NAME, space_type=SPACE_TYPE)
        _keymaps.append(km)
    for idname, key, value, shift, ctrl, props in ITEMS:
        kmi = km.keymap_items.new(idname, key, value, shift=shift, ctrl=ctrl)
        target = getattr(kmi, "properties", None)
        if target is not None:
            for k, v in props.items():
                try:
                    setattr(target, k, v)
                except (AttributeError, TypeError):
                    pass
        _added.append((km, kmi))


def unregister():
    for km, kmi in reversed(_added):
        try:
            km.keymap_items.remove(kmi)
        except (ValueError, RuntimeError):
            pass
    _added.clear()
    kc = bpy.context.window_manager.keyconfigs.addon
    for km in _keymaps:
        try:
            if kc is not None:
                kc.keymaps.remove(km)
        except (ValueError, RuntimeError):
            pass
    _keymaps.clear()
