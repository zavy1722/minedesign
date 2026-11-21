# SPDX-License-Identifier: GPL-3.0-or-later
"""Face3D Likeness: Blender extension entry point (DESIGN 6.2).

`register()` runs the compat probe, registers the PropertyGroups, then every
module of `_MODULES` that exists (modules are added by later work packages).
`unregister()` reverses that. Both are idempotent.
"""
import importlib
import importlib.util
import os
import sys

_MODULES = ("ops_project", "ops_photos", "ops_landmarks", "ops_solve", "ops_apply",
            "ops_handoff", "ui_panels", "overlays", "keymap")

COMPAT = {}          # result of compat.probe(), set by register()
_registered = []     # modules whose register() ran, in order
_props_registered = False


def engine_root():
    """Directory to put on sys.path to import `face3d`.

    The vendored `engine/` next to this file if present (installed extension),
    else the repository root (development layout: parents of blender_ext).
    """
    here = os.path.dirname(os.path.abspath(__file__))
    vendored = os.path.join(here, "engine")
    if os.path.isdir(vendored):
        return vendored
    return os.path.dirname(os.path.dirname(here))


def ensure_engine_on_path():
    """Insert engine_root() into sys.path once (only needed for in-process background jobs)."""
    root = engine_root()
    if root not in sys.path:
        sys.path.insert(0, root)
    return root


def register():
    global _props_registered
    from . import compat, props
    COMPAT.clear()
    COMPAT.update(compat.probe())
    if not _props_registered:
        props.register()
        _props_registered = True
    for name in _MODULES:
        full = __name__ + "." + name
        if full in _registered:
            continue
        if importlib.util.find_spec(full) is None:
            continue
        mod = importlib.import_module(full)
        mod.register()
        _registered.append(full)


def unregister():
    global _props_registered
    for full in reversed(list(_registered)):
        mod = sys.modules.get(full) or importlib.import_module(full)
        mod.unregister()
        _registered.remove(full)
    if _props_registered:
        from . import props
        props.unregister()
        _props_registered = False
