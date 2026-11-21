"""face3d.eval: alignment, gauge-projected coverage / NEES and surface error metrics (DESIGN 7.3).

Public re-exports of the modules listed in DESIGN 2.3 (finalised by WP-23).  Every name is importable
from its module path as before; a name that exists in two modules is exported once (not re-exported here:
align.align (submodule name)).
Submodules stay importable as attributes (``from face3d.eval import align``).
"""
from .align import (NOW7_NAMES, NOW7_LEGACY_NAMES, similarity_tangent_basis, gauge_projector, now7_indices)
from .coverage import (PINV_RCOND, COV_DIAG_MIN, projected_error_and_cov, projected_z, nees, axis_coverage,
    scale_z)
from .metrics import (surface_error, chamfer, likeness_weighted_error, sample_surface, LIKENESS_WEIGHTS,
    F_THRESHOLDS_MM)

__all__ = [
    'COV_DIAG_MIN', 'F_THRESHOLDS_MM', 'LIKENESS_WEIGHTS', 'NOW7_LEGACY_NAMES', 'NOW7_NAMES', 'PINV_RCOND',
    'axis_coverage', 'chamfer', 'gauge_projector', 'likeness_weighted_error', 'nees', 'now7_indices',
    'projected_error_and_cov', 'projected_z', 'sample_surface', 'scale_z', 'similarity_tangent_basis',
    'surface_error',
]
