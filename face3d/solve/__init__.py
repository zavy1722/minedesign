"""face3d.solve: noise, robust schedule, focal ladders, PnP, bundle, nuisances, observability, next-best view (L3).

Public re-exports of the modules listed in DESIGN 2.3 (finalised by WP-23).  Every name is importable
from its module path as before; a name that exists in two modules is exported once
(``camera_model.projection_jacobians`` is the one from ``.expression``).  ``MIRROR`` is the mirror-test
config namespace of ``.mirror`` (like ``NOISE``, ``ROBUST``, ``SCALE``, ... of their modules); the unrelated
``bundle.MIRROR``, the x-flip vector [-1, 1, 1], is exported as ``MIRROR_FLIP``.
Submodules stay importable as attributes (``from face3d.solve import bundle``).
"""
from .lm import (LMResult, numeric_jacobian, levenberg_marquardt)
from .pnp import (DEFAULT_F35_HYPOTHESES, PNP_DEFAULTS, TWIN_MIN_ANGLE_DEG, TWIN_SCORE_RATIO, START_KINDS,
    PnPResult, affine_pose_init, start_poses, rotation_angle_deg, solve_pnp)
from .triangulate import (triangulate_dlt, triangulate_points)
from .bundle import (ENGINE_VERSION, MIRROR as MIRROR_FLIP, BUNDLE, FLAG_COV_SINGULAR, FLAG_VIEW_REJECT, FLAG_VIEW_NOISY,
    FLAG_VIEW_OUTLIERS, FLAG_VIEW_EMPTY, RHO_MM_PER_PARAM, Priors, ScaleConfig, JawConfig, ViewObs,
    BundleResult, view_noise_cov, dense_step, schur_step, jaw_hinge, camera_angles_deg, bundle_adjust)
from .reconstruct import (PhotoLandmarks, reconstruct_landmarks, pnp_sigma_px, AUTO_SIGMA_FRACTION_OF_DIAG,
    REINIT_RMS_SIGMAS, RECONSTRUCT)
from .noise import (NOISE, KINDS, PIN_CLASSES, FLOOR_CLASSES, FLOOR_CLASS_OF_KIND, POINT_LIKE_KINDS,
    FREE_TANGENT_KINDS, unknown_tangent_var_mm2, KIND_SIGMA_MM, KIND_SIGMA_DEF_MM, PIN_CLASS_SIGMA_MM,
    FLOOR_K, N_EFF, FLOOR_MIN_PX, FLOOR_CROP_PX, NoiseModel, pin_sigma_px, whitening, kind_tables)
from .robust import (ROBUST, CHI2_2_MEDIAN, RobustSchedule, huber_weights, tukey_weights, nu2_view, norm_ppf,
    chi2_quantile_wh, view_chi2_test)
from .terms import (SolverState, Term, ShapeModel, FreePoints, shape_n_params, BLOCK_NAMES)
from .focal import (FOCAL_DEFAULTS, HEAD_ORIGIN_OFFSET_MM, PHONE_MAKERS, DEFAULT_NATIVE_ASPECTS, FocalPrior,
    DistancePrior, is_phone_make, aspect_is_native, focal_prior_from_evidence, distance_prior,
    distance_prior_head_origin, focal_group_key)
from .scale import (SCALE, ChordTerm, CardTerm, IrisTerm, IpdTerm, vergence_correction_mm, iris_usable,
    fit_limbus, limbus_is_sharp, iris_observation, POPULATION_SOURCES, population_scale_source,
    population_scale_setup, focal_phi_keys, scale_mode, reported_scale, log_size, log_size_gradient,
    log_size_posterior, scale_source, chord_scale_source, iris_scale_source, card_scale_source,
    fuse_log_scale, scale_report, FLAG_SCALE_CONFLICT, METRIC_KINDS)
from .mirror import (MIRROR, MirrorDecision, mirror_test, flip_cov, DECISIONS, project_mirror_status)
from .expression import (EXPRESSION, TAGS, CLASS_MULT, EXPR_CLASSES, tag_from_blendshapes, mouth_width,
    tag_fallback, retag_from_residuals, mobile_chi2_red, MAX_RETAG_ROUNDS, expression_sigma_mm,
    inflate_view_cov, apply_expression, projection_jacobians, lid_drop, no_neutral_view, jaw_config_for_tag,
    FLAG_NO_NEUTRAL, expression_classes)
from .camera_model import (CAMERA_MODEL, MODELS, huber_cost, whitened_errors, refine_pose,
    select_camera_model, k1_flag, radial_magnification_error, radial_slope_flag, lens_findings,
    retouch_residual_test, retouch_finding, FLAG_K1, FLAG_RADIAL, FLAG_RETOUCH)
from .observability import (OBS, REGION_TARGET_MM, REGION_ORDER, REGION_COVERAGE_RULES, STATUSES, TIER_NAMES,
    FLAG_L_HELDOUT, FLAG_L_TOO_FEW_VIEWS, FINDING_PULLED, FINDING_IMPLAUSIBLE, FLAG_LIKENESS,
    default_region_index, region_points, camera_status, focal_prior_log_sigmas, frozen_parameters,
    posterior_at_prior_weight_one, prior_covariance, shape_prior_info, standard_prior_info, region_evidence,
    coverage_rules, coverage_ok, region_sigma_rep, region_status, lovo_gamma, make_solve_without,
    trim_consistency, inflation, bias_gain, reported_covariance, sigma_rep, shrinkage_gate,
    legacy_shrinkage_gate, shape_prior_cov, prior_shares, widen_prior, likeness_mode_prior, tier, assess)
from .nbv import (NBV, REGION_WEIGHTS, CANDIDATE_YAWS, CANDIDATE_PITCHES, POSE_PRIOR, ACCEPTANCE_RATES,
    candidate_camera, describe_view, template_normals, pose_jacobians, next_best_view)
from .shape_models import (LinearBasis, BasisPrior, extremal_landmark, DEFAULT_ANCHOR_IDS, SHAPE_MODELS)

__all__ = [
    'ACCEPTANCE_RATES', 'AUTO_SIGMA_FRACTION_OF_DIAG', 'BLOCK_NAMES', 'BUNDLE', 'BasisPrior',
    'BundleResult', 'CAMERA_MODEL', 'CANDIDATE_PITCHES', 'CANDIDATE_YAWS', 'CHI2_2_MEDIAN', 'CLASS_MULT',
    'CardTerm', 'ChordTerm', 'DECISIONS', 'DEFAULT_ANCHOR_IDS', 'DEFAULT_F35_HYPOTHESES',
    'DEFAULT_NATIVE_ASPECTS', 'DistancePrior', 'ENGINE_VERSION', 'EXPRESSION', 'EXPR_CLASSES',
    'FINDING_IMPLAUSIBLE', 'FINDING_PULLED', 'FLAG_COV_SINGULAR', 'FLAG_K1', 'FLAG_LIKENESS',
    'FLAG_L_HELDOUT', 'FLAG_L_TOO_FEW_VIEWS', 'FLAG_NO_NEUTRAL', 'FLAG_RADIAL', 'FLAG_RETOUCH',
    'FLAG_SCALE_CONFLICT', 'FLAG_VIEW_EMPTY', 'FLAG_VIEW_NOISY', 'FLAG_VIEW_OUTLIERS', 'FLAG_VIEW_REJECT',
    'FLOOR_CLASSES', 'FLOOR_CLASS_OF_KIND', 'FLOOR_CROP_PX', 'FLOOR_K', 'FLOOR_MIN_PX', 'FOCAL_DEFAULTS',
    'FREE_TANGENT_KINDS', 'FocalPrior', 'FreePoints', 'HEAD_ORIGIN_OFFSET_MM', 'IpdTerm', 'IrisTerm',
    'JawConfig', 'KINDS', 'KIND_SIGMA_DEF_MM', 'KIND_SIGMA_MM', 'LMResult', 'LinearBasis',
    'MAX_RETAG_ROUNDS', 'METRIC_KINDS', 'MIRROR', 'MIRROR_FLIP', 'MODELS', 'MirrorDecision', 'NBV', 'NOISE', 'N_EFF',
    'NoiseModel', 'OBS', 'PHONE_MAKERS', 'PIN_CLASSES', 'PIN_CLASS_SIGMA_MM', 'PNP_DEFAULTS',
    'POINT_LIKE_KINDS', 'POPULATION_SOURCES', 'POSE_PRIOR', 'PhotoLandmarks', 'PnPResult', 'Priors',
    'RECONSTRUCT', 'REGION_COVERAGE_RULES', 'REGION_ORDER', 'REGION_TARGET_MM', 'REGION_WEIGHTS',
    'REINIT_RMS_SIGMAS', 'RHO_MM_PER_PARAM', 'ROBUST', 'RobustSchedule', 'SCALE', 'SHAPE_MODELS',
    'START_KINDS', 'STATUSES', 'ScaleConfig', 'ShapeModel', 'SolverState', 'TAGS', 'TIER_NAMES',
    'TWIN_MIN_ANGLE_DEG', 'TWIN_SCORE_RATIO', 'Term', 'ViewObs', 'affine_pose_init', 'apply_expression',
    'aspect_is_native', 'assess', 'bias_gain', 'bundle_adjust', 'camera_angles_deg', 'camera_status',
    'candidate_camera', 'card_scale_source', 'chi2_quantile_wh', 'chord_scale_source', 'coverage_ok',
    'coverage_rules', 'default_region_index', 'dense_step', 'describe_view', 'distance_prior',
    'distance_prior_head_origin', 'expression_classes', 'expression_sigma_mm', 'extremal_landmark',
    'fit_limbus', 'flip_cov', 'focal_group_key', 'focal_phi_keys', 'focal_prior_from_evidence',
    'focal_prior_log_sigmas', 'frozen_parameters', 'fuse_log_scale', 'huber_cost', 'huber_weights',
    'inflate_view_cov', 'inflation', 'iris_observation', 'iris_scale_source', 'iris_usable',
    'is_phone_make', 'jaw_config_for_tag', 'jaw_hinge', 'k1_flag', 'kind_tables', 'legacy_shrinkage_gate',
    'lens_findings', 'levenberg_marquardt', 'lid_drop', 'likeness_mode_prior', 'limbus_is_sharp',
    'log_size', 'log_size_gradient', 'log_size_posterior', 'lovo_gamma', 'make_solve_without',
    'mirror_test', 'mobile_chi2_red', 'mouth_width', 'next_best_view', 'no_neutral_view', 'norm_ppf',
    'nu2_view', 'numeric_jacobian', 'pin_sigma_px', 'pnp_sigma_px', 'population_scale_setup',
    'population_scale_source', 'pose_jacobians', 'posterior_at_prior_weight_one', 'prior_covariance',
    'prior_shares', 'project_mirror_status', 'projection_jacobians', 'radial_magnification_error',
    'radial_slope_flag', 'reconstruct_landmarks', 'refine_pose', 'region_evidence', 'region_points',
    'region_sigma_rep', 'region_status', 'reported_covariance', 'reported_scale', 'retag_from_residuals',
    'retouch_finding', 'retouch_residual_test', 'rotation_angle_deg', 'scale_mode', 'scale_report',
    'scale_source', 'schur_step', 'select_camera_model', 'shape_n_params', 'shape_prior_cov',
    'shape_prior_info', 'shrinkage_gate', 'sigma_rep', 'solve_pnp', 'standard_prior_info', 'start_poses',
    'tag_fallback', 'tag_from_blendshapes', 'template_normals', 'tier', 'triangulate_dlt',
    'triangulate_points', 'trim_consistency', 'tukey_weights', 'unknown_tangent_var_mm2',
    'vergence_correction_mm', 'view_chi2_test', 'view_noise_cov', 'whitened_errors', 'whitening',
    'widen_prior',
]
