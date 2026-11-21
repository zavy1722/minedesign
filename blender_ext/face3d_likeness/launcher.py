# SPDX-License-Identifier: GPL-3.0-or-later
"""Stand-alone job launcher (DESIGN 6.3, D-24).

Run as `[sys.executable, '-I', launcher.py, job_dir]`. Under `-I` neither the
script directory nor the cwd is on sys.path, so this file inserts the engine
root itself: the vendored `engine/` next to this file if present, else the
repository root (development layout: blender_ext/face3d_likeness/launcher.py).
Imports only the standard library before the path is set; no bpy.
"""
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
_vendored = os.path.join(here, "engine")
root = _vendored if os.path.isdir(_vendored) else os.path.dirname(os.path.dirname(here))
sys.path.insert(0, root)

if __name__ == "__main__":
    from face3d.pipeline.jobs import run_job

    sys.exit(run_job(sys.argv[1]))
