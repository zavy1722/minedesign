"""face3d.qa: photo checks, image statistics, overlay geometry and the colour palette (DESIGN 4.1, 6.5).

Public re-exports of the modules listed in DESIGN 2.3 (finalised by WP-23).  Every name is importable
from its module path as before; a name that exists in two modules is exported once.
Submodules stay importable as attributes (``from face3d.qa import checks``).
"""
from .checks import (QA, PHONE_MAKES, NATIVE_ASPECTS_PHONE, NATIVE_ASPECTS_OTHER, EDITOR_NAMES, Finding,
    PhotoContext, run_photo_checks, run_set_checks, retouch_findings, occluder_actions)
from .image_stats import (laplacian_variance, clipped_fraction, eye_aspect_ratio, gaussian_blur, box_blur,
    skin_smoothness_index)
from .overlay_geom import (HIT_RADIUS_PX, MIN_TARGET_PX, sigma_ellipse, residual_arrow, glyph, styled,
    hatch_polygon, blur_sigma_px, thumbnail_shape)
from .palette import (ROLES, OUTLINE, HALO, RESIDUAL_BINS, hex_to_rgb, srgb_to_linear, linear_to_srgb,
    simulate_cvd, srgb_to_lab, delta_e76, relative_luminance, contrast_ratio)

__all__ = [
    'EDITOR_NAMES', 'Finding', 'HALO', 'HIT_RADIUS_PX', 'MIN_TARGET_PX', 'NATIVE_ASPECTS_OTHER',
    'NATIVE_ASPECTS_PHONE', 'OUTLINE', 'PHONE_MAKES', 'PhotoContext', 'QA', 'RESIDUAL_BINS', 'ROLES',
    'blur_sigma_px', 'box_blur', 'clipped_fraction', 'contrast_ratio', 'delta_e76', 'eye_aspect_ratio',
    'gaussian_blur', 'glyph', 'hatch_polygon', 'hex_to_rgb', 'laplacian_variance', 'linear_to_srgb',
    'occluder_actions', 'relative_luminance', 'residual_arrow', 'retouch_findings', 'run_photo_checks',
    'run_set_checks', 'sigma_ellipse', 'simulate_cvd', 'skin_smoothness_index', 'srgb_to_lab',
    'srgb_to_linear', 'styled', 'thumbnail_shape',
]
