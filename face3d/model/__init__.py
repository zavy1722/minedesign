"""face3d.model: landmark registry, landmark priors, procedural head and template kits (DESIGN 2.2 L2).

Public re-exports of the modules listed in DESIGN 2.3 (finalised by WP-23).  Every name is importable
from its module path as before; a name that exists in two modules is exported once.
Submodules stay importable as attributes (``from face3d.model import conditional_prior``).
"""
from .conditional_prior import (ConditionalTemplatePrior, rbf_transfer_matrix, DEFAULT_REGION_SIGMA_MM,
    DEFAULT_KAPPA, ANATOMICAL_SCHEME)
from .landmark_prior import (LandmarkPrior, GeneralisedPrior, FactorPrior, DiagonalPrior, CompositePrior,
    PACKAGE_PRIOR_PATH, load_prior_package, prior_mean, rigid_tangent_basis)
from .procedural_head import (build_procedural_head, cube_sphere, ProceduralHeadError, geometric_regions,
    jaw_weights_rule, stiffness_rule, region_weights_default, spherical_uv, signed_volume, fold_check,
    legacy_synthetic_embeddings, REGION_ORDER, REGION_RULES_MM, BUMPS, HEAD_RADII_MM, HEAD_CENTRE_MM,
    GENERATOR_VERSION, REGION_LANDMARKS)
from .registry import (MIDLINE_BASES, BILATERAL_BASES, ANATOMICAL_IDS, BASE_NAMES, KIND_SIGMA_MM,
    SCHEME_KINDS, SIDES, Landmark, ANATOMICAL, landmark_base, anchor_ids, SchemePoint, Scheme, load_scheme,
    resolve_lr, SCHEME_DIR)
from .template_kit import (TemplateKit, TopologyMismatch, KIT_FORMAT, KIT_VERSION, MIRROR_TOL_MM,
    fan_triangles, topology_sha256, vertex_embedding, vertex_embeddings, area_weighted_normals, midline_ring,
    npz_path_for)

__all__ = [
    'ANATOMICAL', 'ANATOMICAL_IDS', 'ANATOMICAL_SCHEME', 'BASE_NAMES', 'BILATERAL_BASES', 'BUMPS',
    'CompositePrior', 'ConditionalTemplatePrior', 'DEFAULT_KAPPA', 'DEFAULT_REGION_SIGMA_MM',
    'DiagonalPrior', 'FactorPrior', 'GENERATOR_VERSION', 'GeneralisedPrior', 'HEAD_CENTRE_MM',
    'HEAD_RADII_MM', 'KIND_SIGMA_MM', 'KIT_FORMAT', 'KIT_VERSION', 'Landmark', 'LandmarkPrior',
    'MIDLINE_BASES', 'MIRROR_TOL_MM', 'PACKAGE_PRIOR_PATH', 'ProceduralHeadError', 'REGION_LANDMARKS',
    'REGION_ORDER', 'REGION_RULES_MM', 'SCHEME_DIR', 'SCHEME_KINDS', 'SIDES', 'Scheme', 'SchemePoint',
    'TemplateKit', 'TopologyMismatch', 'anchor_ids', 'area_weighted_normals', 'build_procedural_head',
    'cube_sphere', 'fan_triangles', 'fold_check', 'geometric_regions', 'jaw_weights_rule', 'landmark_base',
    'legacy_synthetic_embeddings', 'load_prior_package', 'load_scheme', 'midline_ring', 'npz_path_for',
    'prior_mean', 'rbf_transfer_matrix', 'region_weights_default', 'resolve_lr', 'rigid_tangent_basis',
    'signed_volume', 'spherical_uv', 'stiffness_rule', 'topology_sha256', 'vertex_embedding',
    'vertex_embeddings',
]
