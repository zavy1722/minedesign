"""face3d.geometry: rotations, cameras, Procrustes and RBF warps (DESIGN 2.2; mm, OpenCV cameras).

Public re-exports of the modules listed in DESIGN 2.3 (finalised by WP-23).  Every name is importable
from its module path as before; a name that exists in two modules is exported once.
Submodules stay importable as attributes (``from face3d.geometry import camera``).
"""
from .camera import (FULL_FRAME_DIAGONAL_MM, focal_px_from_35mm, focal_px_from_sensor, focal_35mm_from_px,
    fov_deg, Camera, look_at, to_blender_camera, camera_to_invdepth, invdepth_to_camera, project_invdepth,
    face_ray_angle, virtual_rotation, rectilinear_virtual_homography, apply_homography,
    rectilinear_virtual_camera, stereographic_project, stereographic_unproject, stereographic_virtual_camera)
from .procrustes import (umeyama, umeyama_proper_and_reflected, apply_similarity, procrustes_rmse,
    fit_symmetry_plane, reflect, reflection_matrix, permute_pairs)
from .rbf import (ALPHA_GRID, WARP, RBFWarp, rms_radius, per_landmark_lambda)
from .rotations import (skew, rodrigues, rotation_to_rvec, nearest_rotation, euler_xyz_deg,
    rotation_from_euler_deg)

__all__ = [
    'ALPHA_GRID', 'Camera', 'FULL_FRAME_DIAGONAL_MM', 'RBFWarp', 'WARP', 'apply_homography',
    'apply_similarity', 'camera_to_invdepth', 'euler_xyz_deg', 'face_ray_angle', 'fit_symmetry_plane',
    'focal_35mm_from_px', 'focal_px_from_35mm', 'focal_px_from_sensor', 'fov_deg', 'invdepth_to_camera',
    'look_at', 'nearest_rotation', 'per_landmark_lambda', 'permute_pairs', 'procrustes_rmse',
    'project_invdepth', 'rectilinear_virtual_camera', 'rectilinear_virtual_homography', 'reflect',
    'reflection_matrix', 'rms_radius', 'rodrigues', 'rotation_from_euler_deg', 'rotation_to_rvec', 'skew',
    'stereographic_project', 'stereographic_unproject', 'stereographic_virtual_camera', 'to_blender_camera',
    'umeyama', 'umeyama_proper_and_reflected', 'virtual_rotation',
]
