"""face3d.testbed: synthetic subjects, rigs, detector simulator, faults, renders, scenarios, scorecard (DESIGN 7.2).

Public re-exports of the modules listed in DESIGN 2.3 (finalised by WP-23).  Every name is importable
from its module path as before; a name that exists in two modules is exported once.
Submodules stay importable as attributes (``from face3d.testbed import detector_sim``).
"""
from .detector_sim import (KIND_SIGMA_MM, KIND_SIGMA_DEF_MM, LEGACY_KIND, OUTLIER_SIGMA_RANGE, Observation,
    legacy_kind, legacy_kinds, simulate)
from .faults import (mirror_view, unbaked_orientation, exif_crop, exif_missing, selfie_rig, expression_fault,
    beauty_warp, beauty_index_map, off_axis_wide, OffAxisView, occluder_fault, small_face, face_width_px,
    gross_outliers, definition_bias, FAULT_MATRIX, ALARM_BUDGET, FAULT_DEFAULTS, design_fault_rows)
from .render import (RenderedView, render_view, project_landmarks, render_masks, scale_camera,
    procedural_albedo, surface_points, vertex_normals, face_centre, gaussian_blur, RENDER_DEFAULTS, SKIN_RGB,
    LIPS_RGB, BROW_RGB, FACE_CENTRE_IDS)
from .rigs import (Rig, visible_mask, facing_mask, in_image_mask, studio_ring, rear_phone, selfie,
    camera_roll, PROTOCOLS, IMAGE_W, IMAGE_H, DEFAULT_TARGET, MIN_VISIBLE, MAX_VIEW_ATTEMPTS,
    VISIBILITY_COS_MIN)
from .scenarios import (Scenario, METRIC_KEYS, SCENARIOS, FAST_SCENARIOS, LEGACY_PRIOR, default_engine,
    run_seed, run_scenario)
from .scorecard import (SEED0, FAST_SEEDS, SCORECARD_FORMAT, HIGHER_IS_WORSE, BASELINE_LABEL,
    BLAS_THREAD_VARS, N_OK_FRACTION_DROP, PAIRED_MAX_SEED_SHIFT, seeds_for, aggregate, build_scorecard,
    per_seed_columns, paired_medians, compare, is_paired, blas_thread_env, blas_single_threaded, dumps,
    write_scorecard, load_scorecard, main)
from .subjects import (LOG_SCALE_SD, legacy_subject, smooth_field_subject, log_scale_of)
from .surface_subjects import (SurfaceSubject, out_of_prior_subject, expression_field, expression_meta,
    EXPRESSION_KINDS, area_ratios, face_hemisphere, symmetric_part, antisymmetric_part, asymmetry_rms,
    region_weight, SURFACE_DEFAULTS, FACE_MIN_Z_MM, SubjectGenerationError, feature_displacements,
    jaw_open_weights, HINGE_LANDMARK_WEIGHTS, HINGE_SCHEME, RIGID_BASES, FEATURE_KEYS)

__all__ = [
    'ALARM_BUDGET', 'BASELINE_LABEL', 'BLAS_THREAD_VARS', 'BROW_RGB', 'DEFAULT_TARGET', 'EXPRESSION_KINDS',
    'FACE_CENTRE_IDS', 'FACE_MIN_Z_MM', 'FAST_SCENARIOS', 'FAST_SEEDS', 'FAULT_DEFAULTS', 'FAULT_MATRIX',
    'FEATURE_KEYS', 'HIGHER_IS_WORSE', 'HINGE_LANDMARK_WEIGHTS', 'HINGE_SCHEME', 'IMAGE_H', 'IMAGE_W',
    'KIND_SIGMA_DEF_MM', 'KIND_SIGMA_MM', 'LEGACY_KIND', 'LEGACY_PRIOR', 'LIPS_RGB', 'LOG_SCALE_SD',
    'MAX_VIEW_ATTEMPTS', 'METRIC_KEYS', 'MIN_VISIBLE', 'N_OK_FRACTION_DROP', 'OUTLIER_SIGMA_RANGE',
    'Observation', 'OffAxisView', 'PAIRED_MAX_SEED_SHIFT', 'PROTOCOLS', 'RENDER_DEFAULTS', 'RIGID_BASES',
    'RenderedView', 'Rig', 'SCENARIOS', 'SCORECARD_FORMAT', 'SEED0', 'SKIN_RGB', 'SURFACE_DEFAULTS',
    'Scenario', 'SubjectGenerationError', 'SurfaceSubject', 'VISIBILITY_COS_MIN', 'aggregate',
    'antisymmetric_part', 'area_ratios', 'asymmetry_rms', 'beauty_index_map', 'beauty_warp',
    'blas_single_threaded', 'blas_thread_env', 'build_scorecard', 'camera_roll', 'compare',
    'default_engine', 'definition_bias', 'design_fault_rows', 'dumps', 'exif_crop', 'exif_missing',
    'expression_fault', 'expression_field', 'expression_meta', 'face_centre', 'face_hemisphere',
    'face_width_px', 'facing_mask', 'feature_displacements', 'gaussian_blur', 'gross_outliers',
    'in_image_mask', 'is_paired', 'jaw_open_weights', 'legacy_kind', 'legacy_kinds', 'legacy_subject',
    'load_scorecard', 'log_scale_of', 'main', 'mirror_view', 'occluder_fault', 'off_axis_wide',
    'out_of_prior_subject', 'paired_medians', 'per_seed_columns', 'procedural_albedo', 'project_landmarks',
    'rear_phone', 'region_weight', 'render_masks', 'render_view', 'run_scenario', 'run_seed',
    'scale_camera', 'seeds_for', 'selfie', 'selfie_rig', 'simulate', 'small_face', 'smooth_field_subject',
    'studio_ring', 'surface_points', 'symmetric_part', 'unbaked_orientation', 'vertex_normals',
    'visible_mask', 'write_scorecard',
]
