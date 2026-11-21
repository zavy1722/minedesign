# SPDX-License-Identifier: GPL-3.0-or-later
"""Scene-level PropertyGroups (DESIGN 6.2, 3.2). Attached as `bpy.types.Scene.face3d`.

Conventions: pin coordinates `x`, `y` are image pixels, top-left origin, y down
(the engine's convention, not Blender's bottom-up image rows); `zoom` is the
view magnification when the pin was placed (it sets the pin sigma, DESIGN 6.4);
`blind` marks a first pin placed without the model overlay. `msg_key` fields
are translation keys, never prose. Project data itself lives in sidecar files
(DESIGN 6.6); these groups only mirror what the UI needs.

Annotations are evaluated eagerly (no `from __future__ import annotations`),
as Blender requires.
"""
import bpy
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty, FloatProperty,
                       IntProperty, PointerProperty, StringProperty)

INCLUDE_ITEMS = [
    ("auto", "Auto", "Let the quality checks decide"),
    ("include", "Include", "Always use this photo"),
    ("exclude", "Exclude", "Never use this photo"),
]
MIRROR_ITEMS = [
    ("none", "None", "No mirror decision recorded"),
    ("keep", "Keep", "Keep the photo as it is"),
    ("flip", "Flip", "Flip the photo horizontally (user decision)"),
]
JOB_STATUS_ITEMS = [
    ("idle", "Idle", ""),
    ("running", "Running", ""),
    ("ready", "Ready", "Result waiting to be applied"),
    ("failed", "Failed", ""),
    ("cancelled", "Cancelled", ""),
]
# Guided rail, DESIGN 6.4.
RAIL_STAGES = ("consent", "photos", "check", "landmarks", "cameras", "shape",
               "confidence", "sculpt", "texture", "share")
RAIL_ITEMS = [(s, s.capitalize(), "") for s in RAIL_STAGES]


class F3DPin(bpy.types.PropertyGroup):
    photo_id: StringProperty()
    landmark: StringProperty()
    x: FloatProperty()
    y: FloatProperty()
    cls: StringProperty()
    expertise: StringProperty(default="novice")
    zoom: FloatProperty(default=1.0)
    blind: BoolProperty(default=False)


class F3DPhoto(bpy.types.PropertyGroup):
    id: StringProperty()
    path: StringProperty(subtype="FILE_PATH")
    sha256: StringProperty()
    include: EnumProperty(items=INCLUDE_ITEMS, default="auto")
    mirror_decision: EnumProperty(items=MIRROR_ITEMS, default="none")
    status: StringProperty()


class F3DCard(bpy.types.PropertyGroup):
    code: StringProperty()
    severity: StringProperty(default="info")
    msg_key: StringProperty()
    photo_id: StringProperty()
    decided: BoolProperty(default=False)


class F3DJob(bpy.types.PropertyGroup):
    job_dir: StringProperty(subtype="DIR_PATH")
    stage: StringProperty()
    status: EnumProperty(items=JOB_STATUS_ITEMS, default="idle")
    progress: FloatProperty(min=0.0, max=1.0)
    msg_key: StringProperty()


class F3DSettings(bpy.types.PropertyGroup):
    project_path: StringProperty(subtype="DIR_PATH")
    pins: CollectionProperty(type=F3DPin)
    photos: CollectionProperty(type=F3DPhoto)
    cards: CollectionProperty(type=F3DCard)
    job: PointerProperty(type=F3DJob)
    rail_stage: EnumProperty(items=RAIL_ITEMS, default="consent")


CLASSES = (F3DPin, F3DPhoto, F3DCard, F3DJob, F3DSettings)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.Scene.face3d = PointerProperty(type=F3DSettings)


def unregister():
    if hasattr(bpy.types.Scene, "face3d"):
        del bpy.types.Scene.face3d
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
