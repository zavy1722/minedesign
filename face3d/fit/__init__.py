"""face3d.fit: symmetry, template warp, contours, edge snap, per-vertex uncertainty, claims ledger (L4).

Public re-exports of the modules listed in DESIGN 2.3 (finalised by WP-23).  Every name is importable
from its module path as before; a name that exists in two modules is exported once (not re-exported here:
edge_snap.edge_snap (submodule name)).
Submodules stay importable as attributes (``from face3d.fit import contour``).
"""
from .template import (Template, TemplateFit, fit_template_to_landmarks, FLAG_MIRRORED, FLAG_WRONG_AXES,
    FLAG_FOLD, FLAG_B_RMS, FLAG_LANDMARK_FREEZE, FLAG_CONTOUR_HALF, NOW7_IDS, StagedWarpConfig, landmark_rms,
    stage_a, stage_b, stage_c, stage_d, fold_gate, StagedWarpResult, staged_warp)
from .silhouette import (ContourView, edge_faces, silhouette_vertices, fit_silhouettes)
from .symmetry import (SYM, EVIDENCE_STATES, GATED_STATES, FULL_SIGMA_STATES, FACE_REGIONS, PLANE_GROUPS,
    pair_sigmas, midline_sigmas, gate_symmetry_sigmas, plane_weights, plane_group, SymmetryTerm,
    split_symmetric, mirror_rmsd, face_vertex_mask, symmetry_checks, detect_mirrored_source, check_mirror_map)
from .contour import (ContourObs, RimPoints, RimSamples, ContourDistance, ContourTerm, ContourStageResult,
    rim_points, densify_rim, match, grid_nearest, forward_residuals, backward_residuals, sigma_n_model,
    effective_sample_weights, diagnose_focal_distance, contour_stage, landmark_rms_pct_iod, vertex_normals,
    scale_camera, KINDS, CONTOUR, FINDING_FOCAL_DIST, contour_view_stats, focal_distance_check,
    FLAG_LANDMARK_SHIFT, tangent_extents, interior_landmark_mask, pose_uv_jacobian, SIL3_NON_INTERIOR_BASES)
from .distance_transform import (edt_squared, edt_with_nearest, edt, sample_bilinear, gradient,
    fh_lower_envelope)
from .edge_snap import (SnapResult, resample_polyline, gaussian_blur, sobel_magnitude, EDGE_SNAP)
from .uncertainty import (SIGMA_RES_MM, CHOL_JITTER, landmark_sigma_mm, vertex_cov_stage_b, vertex_sigma_n,
    sigma_res_of, finite_difference_check, landmark_region_sigma_def)
from .ledger import (LEDGER, BANNER, RegionClaim, ClaimsLedger, build_ledger, vertex_support, report_lines,
    KIT_REGION_MAP, REGION_LABELS)

__all__ = [
    'BANNER', 'CHOL_JITTER', 'CONTOUR', 'ClaimsLedger', 'ContourDistance', 'ContourObs',
    'ContourStageResult', 'ContourTerm', 'ContourView', 'EDGE_SNAP', 'EVIDENCE_STATES', 'FACE_REGIONS',
    'FINDING_FOCAL_DIST', 'FLAG_B_RMS', 'FLAG_CONTOUR_HALF', 'FLAG_FOLD', 'FLAG_LANDMARK_FREEZE',
    'FLAG_LANDMARK_SHIFT', 'FLAG_MIRRORED', 'FLAG_WRONG_AXES', 'FULL_SIGMA_STATES', 'GATED_STATES', 'KINDS',
    'KIT_REGION_MAP', 'LEDGER', 'NOW7_IDS', 'PLANE_GROUPS', 'REGION_LABELS', 'RegionClaim', 'RimPoints',
    'RimSamples', 'SIGMA_RES_MM', 'SIL3_NON_INTERIOR_BASES', 'SYM', 'SnapResult', 'StagedWarpConfig',
    'StagedWarpResult', 'SymmetryTerm', 'Template', 'TemplateFit', 'backward_residuals', 'build_ledger',
    'check_mirror_map', 'contour_stage', 'contour_view_stats', 'densify_rim', 'detect_mirrored_source',
    'diagnose_focal_distance', 'edge_faces', 'edt', 'edt_squared', 'edt_with_nearest',
    'effective_sample_weights', 'face_vertex_mask', 'fh_lower_envelope', 'finite_difference_check',
    'fit_silhouettes', 'fit_template_to_landmarks', 'focal_distance_check', 'fold_gate',
    'forward_residuals', 'gate_symmetry_sigmas', 'gaussian_blur', 'gradient', 'grid_nearest',
    'interior_landmark_mask', 'landmark_region_sigma_def', 'landmark_rms', 'landmark_rms_pct_iod',
    'landmark_sigma_mm', 'match', 'midline_sigmas', 'mirror_rmsd', 'pair_sigmas', 'plane_group',
    'plane_weights', 'pose_uv_jacobian', 'report_lines', 'resample_polyline', 'rim_points',
    'sample_bilinear', 'scale_camera', 'sigma_n_model', 'sigma_res_of', 'silhouette_vertices',
    'sobel_magnitude', 'split_symmetric', 'stage_a', 'stage_b', 'stage_c', 'stage_d', 'staged_warp',
    'symmetry_checks', 'tangent_extents', 'vertex_cov_stage_b', 'vertex_normals', 'vertex_sigma_n',
    'vertex_support',
]
