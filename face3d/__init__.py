"""face3d: photo-to-3D face fitting engine (numpy only, Blender-compatible).

Subpackages (DESIGN 2.2 layers; each re-exports its public API, DESIGN 2.3): ``core``, ``io``,
``geometry``, ``mesh``, ``model``, ``solve``, ``fit``, ``handoff``, ``texture``, ``qa``, ``eval``,
``testbed``, ``pipeline``.  Importing ``face3d`` itself imports none of them (the Blender add-on
probes the engine in < 100 ms); import the subpackage or module you need.  Units: float64 mm,
OpenCV cameras, pixel origin at the top-left corner (DESIGN 3.1).
"""
__version__ = "0.2.0"

#: the subpackages, in layer order (not in ``__all__``: ``from face3d import *`` must neither import them
#: all nor rebind the caller's ``eval`` and ``io``)
SUBPACKAGES = ("core", "io", "geometry", "mesh", "model", "solve", "fit", "handoff", "texture", "qa", "eval",
               "testbed", "pipeline")

__all__ = ["__version__", "SUBPACKAGES"]
