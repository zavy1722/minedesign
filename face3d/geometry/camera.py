"""Full-perspective pinhole camera model.

Conventions (OpenCV style, used everywhere inside the engine):
  * camera frame: +x right, +y down, +z forward (into the scene)
  * image frame: pixels, origin at the top-left corner of the top-left pixel
  * world -> camera: X_c = R @ X_w + t
Model units are millimetres unless a caller says otherwise.

Conversion to Blender's camera convention (+y up, looking down -z) lives in
:func:`to_blender_camera`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .rotations import rodrigues, rotation_to_rvec

FULL_FRAME_DIAGONAL_MM = float(np.hypot(36.0, 24.0))  # 43.2666 mm


def focal_px_from_35mm(f35_mm: float, width_px: int, height_px: int) -> float:
    """Pixel focal length from a 35 mm-equivalent focal length (EXIF FocalLengthIn35mmFilm).

    The 35 mm equivalence (crop factor) is defined on the image diagonal, so this
    also stays correct for non-3:2 aspect ratios such as 4:3 phone images.
    """
    diag_px = float(np.hypot(width_px, height_px))
    return f35_mm * diag_px / FULL_FRAME_DIAGONAL_MM


def focal_px_from_sensor(f_mm: float, sensor_width_mm: float, width_px: int) -> float:
    """Pixel focal length from the real focal length and the sensor width."""
    return f_mm * width_px / sensor_width_mm


def focal_35mm_from_px(f_px: float, width_px: int, height_px: int) -> float:
    return f_px * FULL_FRAME_DIAGONAL_MM / float(np.hypot(width_px, height_px))


def fov_deg(f_px: float, size_px: float) -> float:
    """Full field of view (degrees) across `size_px` pixels."""
    return float(np.degrees(2.0 * np.arctan(size_px / (2.0 * f_px))))


@dataclass
class Camera:
    """Pinhole camera with square pixels and no skew (adequate for photo matching)."""

    f: float  # focal length in pixels
    cx: float
    cy: float
    width: int
    height: int
    R: np.ndarray = field(default_factory=lambda: np.eye(3))
    t: np.ndarray = field(default_factory=lambda: np.zeros(3))
    # Optional radial distortion (k1, k2) on normalised coordinates.
    k: np.ndarray = field(default_factory=lambda: np.zeros(2))

    @classmethod
    def centered(cls, f: float, width: int, height: int, **kw) -> "Camera":
        return cls(f=f, cx=width / 2.0, cy=height / 2.0, width=width, height=height, **kw)

    # ------------------------------------------------------------------ basics
    @property
    def K(self) -> np.ndarray:
        return np.array([[self.f, 0.0, self.cx], [0.0, self.f, self.cy], [0.0, 0.0, 1.0]])

    @property
    def rvec(self) -> np.ndarray:
        return rotation_to_rvec(self.R)

    @property
    def center(self) -> np.ndarray:
        """Camera centre in world coordinates."""
        return -self.R.T @ self.t

    def copy(self) -> "Camera":
        return Camera(self.f, self.cx, self.cy, self.width, self.height,
                      self.R.copy(), self.t.copy(), self.k.copy())

    def to_camera(self, X: np.ndarray) -> np.ndarray:
        return np.asarray(X, float) @ self.R.T + self.t

    def project(self, X: np.ndarray) -> np.ndarray:
        """World points (N,3) -> pixel coordinates (N,2)."""
        Xc = self.to_camera(X)
        z = Xc[:, 2:3]
        xn = Xc[:, :2] / z
        if np.any(self.k):
            r2 = np.sum(xn * xn, axis=1, keepdims=True)
            xn = xn * (1.0 + self.k[0] * r2 + self.k[1] * r2 * r2)
        return xn * self.f + np.array([self.cx, self.cy])

    def depth(self, X: np.ndarray) -> np.ndarray:
        return self.to_camera(X)[:, 2]

    def ray(self, uv: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Pixel(s) -> (origin, unit direction) in world space (ignores distortion)."""
        uv = np.atleast_2d(uv).astype(float)
        d_c = np.column_stack([(uv[:, 0] - self.cx) / self.f, (uv[:, 1] - self.cy) / self.f, np.ones(len(uv))])
        d_w = d_c @ self.R  # R^T d for each row
        d_w /= np.linalg.norm(d_w, axis=1, keepdims=True)
        return self.center, d_w

    # ---------------------------------------------------------- param vectors
    def pose_params(self) -> np.ndarray:
        return np.concatenate([self.rvec, self.t])

    def set_pose_params(self, p: np.ndarray) -> None:
        self.R = rodrigues(p[:3])
        self.t = np.asarray(p[3:6], float).copy()

    @property
    def fov_x_deg(self) -> float:
        return fov_deg(self.f, self.width)

    @property
    def focal_35mm(self) -> float:
        return focal_35mm_from_px(self.f, self.width, self.height)


def look_at(eye: np.ndarray, target: np.ndarray, up: np.ndarray = np.array([0.0, 1.0, 0.0])) -> tuple[np.ndarray, np.ndarray]:
    """(R, t) for a camera at `eye` looking at `target`.

    `up` is the world up direction (world is y-up, matching the head model frame);
    image y points down, so camera +y is aligned with world -up.
    """
    eye = np.asarray(eye, float)
    z = np.asarray(target, float) - eye
    z /= np.linalg.norm(z)
    # Right-handed camera frame: x = y × z with y ≈ -up (image y points down).
    x = np.cross(-np.asarray(up, float), z)
    if np.linalg.norm(x) < 1e-9:
        x = np.cross(np.array([0.0, 0.0, -1.0]), z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    R = np.vstack([x, y, z])
    return R, -R @ eye


# Blender camera space: +x right, +y up, looking along -z.  OpenCV -> Blender flips y and z.
_CV_TO_BLENDER = np.diag([1.0, -1.0, -1.0])


def to_blender_camera(cam: Camera, sensor_width_mm: float = 36.0) -> dict:
    """Blender camera settings reproducing `cam` (world frame unchanged).

    Returns a dict with `matrix_world` (4x4, camera->world in Blender's camera
    convention), `lens` (mm) for the given sensor width with sensor_fit
    HORIZONTAL, `shift_x` / `shift_y` for an off-centre principal point, and the
    render resolution.
    """
    R_bl = _CV_TO_BLENDER @ cam.R  # world -> blender-camera rotation
    M = np.eye(4)
    M[:3, :3] = R_bl.T
    M[:3, 3] = cam.center
    lens = cam.f * sensor_width_mm / cam.width
    # Blender shift is in units of the larger image dimension; a positive shift
    # moves the frame right/up, so the optical axis lands left of/below centre.
    larger = float(max(cam.width, cam.height))
    shift_x = (cam.width / 2.0 - cam.cx) / larger
    shift_y = (cam.cy - cam.height / 2.0) / larger
    return {
        "matrix_world": M,
        "lens": lens,
        "sensor_width": sensor_width_mm,
        "sensor_fit": "HORIZONTAL",
        "shift_x": shift_x,
        "shift_y": shift_y,
        "resolution": (cam.width, cam.height),
    }
