"""face3d.texture: z-buffer texture projection and blending (DESIGN 4.18).

Public re-exports of the modules listed in DESIGN 2.3 (finalised by WP-23).  Every name is importable
from its module path as before; a name that exists in two modules is exported once.
Submodules stay importable as attributes (``from face3d.texture import blend``).
"""
from .blend import (BLEND_DEFAULTS, TextureResult, TextureBlocked, ABSOLUTE_COLOUR_NOTE, gaussian_blur,
    normalized_blur, two_band_blend, fill_holes, mirror_fill_low_band, build_texture)
from .project import (TEXTURE_DEFAULTS, UVGBuffer, UV_WRAP_SPAN, EXCLUDE_FLAGS, GBUFFER_TOL_MM, GateFindings,
    barycentric_fill, uv_gbuffer, texel_size_mm, mirror_texel_map, bounded_distance_to_outside, depth_edges,
    visibility_eps_mm, check_gbuffer_on_mesh, view_weights, sample_image, solve_gains, texture_gates,
    texture_blocked, excluded_views)

__all__ = [
    'ABSOLUTE_COLOUR_NOTE', 'BLEND_DEFAULTS', 'EXCLUDE_FLAGS', 'GBUFFER_TOL_MM', 'GateFindings',
    'TEXTURE_DEFAULTS', 'TextureBlocked', 'TextureResult', 'UVGBuffer', 'UV_WRAP_SPAN', 'barycentric_fill',
    'bounded_distance_to_outside', 'build_texture', 'check_gbuffer_on_mesh', 'depth_edges',
    'excluded_views', 'fill_holes', 'gaussian_blur', 'mirror_fill_low_band', 'mirror_texel_map',
    'normalized_blur', 'sample_image', 'solve_gains', 'texel_size_mm', 'texture_blocked', 'texture_gates',
    'two_band_blend', 'uv_gbuffer', 'view_weights', 'visibility_eps_mm',
]
