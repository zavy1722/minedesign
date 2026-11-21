# SPDX-License-Identifier: GPL-3.0-or-later
"""Feature probe (DESIGN 6.2, bl A9). Runs in well under 100 ms.

Never imports optional ML packages; only bpy, numpy and the standard library.
"""
import platform as _platform
import sys

import bpy


def probe():
    """Return a plain dict describing the host.

    Keys: blender (tuple, bpy.app.version), python_tag (e.g. 'cp311'),
    numpy (version string or None), online_access (bool, Blender's
    'Allow Online Access' preference; False when unknown), platform, background.
    """
    try:
        import numpy
        np_version = numpy.__version__
    except Exception:  # pragma: no cover - numpy ships with Blender
        np_version = None
    app = bpy.app
    return {
        "blender": tuple(app.version),
        "python_tag": "cp%d%d" % (sys.version_info[0], sys.version_info[1]),
        "numpy": np_version,
        "online_access": bool(getattr(app, "online_access", False)),
        "platform": _platform.system().lower() + "-" + _platform.machine().lower(),
        "background": bool(getattr(app, "background", False)),
    }
