"""face3d.mesh: mesh container, sparse algebra, Laplacians, reduced deformer, distance, rasteriser, subdivision.

Public re-exports of the modules listed in DESIGN 2.3 (finalised by WP-23).  Every name is importable
from its module path as before; a name that exists in two modules is exported once.
Submodules stay importable as attributes (``from face3d.mesh import core``).
"""
from .core import (Mesh, read_obj, write_obj, uv_sphere)
from .sparse import (Sparse, cg)
from .laplacian import (cotan_laplacian, uniform_laplacian, DENSE_MAX_VERTS, laplacian_deform, smooth)
from .reduced import (farthest_point_sample, coef_matrix, coef_vector, similarity_tangent_cm,
    similarity_projector_from, ReducedDeformer)
from .distance import (closest_point_on_triangle, TriangleGrid, point_to_mesh, brute_force_point_to_mesh,
    mesh_orientation_volume, angle_weighted_pseudonormals)
from .raster import (RasterResult, rasterize, render_normals, render_lambert, boundary_pixels, INSIDE_EPS,
    DEFAULT_LIGHT_DIR_WORLD, DEFAULT_AMBIENT)
from .subdiv import (quad_one_rings, is_closed, catmull_clark, limit_stencil_matrix, limit_positions,
    fit_cage_to_limit, subdivide_levels, quad_edges, SUBDIV_DEFAULTS)

__all__ = [
    'DEFAULT_AMBIENT', 'DEFAULT_LIGHT_DIR_WORLD', 'DENSE_MAX_VERTS', 'INSIDE_EPS', 'Mesh', 'RasterResult',
    'ReducedDeformer', 'SUBDIV_DEFAULTS', 'Sparse', 'TriangleGrid', 'angle_weighted_pseudonormals',
    'boundary_pixels', 'brute_force_point_to_mesh', 'catmull_clark', 'cg', 'closest_point_on_triangle',
    'coef_matrix', 'coef_vector', 'cotan_laplacian', 'farthest_point_sample', 'fit_cage_to_limit',
    'is_closed', 'laplacian_deform', 'limit_positions', 'limit_stencil_matrix', 'mesh_orientation_volume',
    'point_to_mesh', 'quad_edges', 'quad_one_rings', 'rasterize', 'read_obj', 'render_lambert',
    'render_normals', 'similarity_projector_from', 'similarity_tangent_cm', 'smooth', 'subdivide_levels',
    'uniform_laplacian', 'uv_sphere', 'write_obj',
]
