"""Full-perspective pinhole camera model.

Conventions (OpenCV style, used everywhere inside the engine):
  * camera frame: +x right, +y down, +z forward (into the scene)
  * image frame: pixels, origin at the top-left corner of the top-left pixel
  * world -> camera: X_c = R @ X_w + t
Model units are millimetres unless a caller says otherwise.

Conversion to Blender's camera convention (+y up, looking down -z) lives in
:func:`to_blender_camera`.

WP-06 additions (all existing functions unchanged): the exact inverse-depth
reparameterisation used inside the solver (DESIGN D-02; ``camera_to_invdepth``,
``invdepth_to_camera``, ``project_invdepth``) and local virtual cameras for
off-axis faces (DESIGN D-12, 4.3; ``face_ray_angle``, ``virtual_rotation``,
rectilinear homography and stereographic helpers). Angles are radians.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .rotations import rodrigues, rotation_to_rvec, skew

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
    # Blender measures shift in units of the sensor-fit dimension; with
    # sensor_fit = HORIZONTAL that is the image width for BOTH shift_x and
    # shift_y (with AUTO it would be the larger side). A positive shift moves
    # the frame right/up, so the optical axis lands left of/below centre.
    fit = float(cam.width)
    shift_x = (cam.width / 2.0 - cam.cx) / fit
    shift_y = (cam.cy - cam.height / 2.0) / fit
    return {
        "matrix_world": M,
        "lens": lens,
        "sensor_width": sensor_width_mm,
        "sensor_fit": "HORIZONTAL",
        "shift_x": shift_x,
        "shift_y": shift_y,
        "resolution": (cam.width, cam.height),
    }


# ---------------------------------------------------------------------------
# Inverse-depth camera parameters (DESIGN D-02, 3.1 "Camera", 4.3; rec CAM-4;
# research note camera-perspective-distortion). WP-06 (d).
#
# With X_c = R X + t and t = (tau_x, tau_y, t_z), dividing the pinhole model by
# t_z gives the exact reparameterisation
#     u = c + s ((R X)_xy + tau) / (1 + rho (R X)_z),   rho = 1 / t_z,  s = f rho,
# so f = s / rho and t = (tau_x, tau_y, 1 / rho). Units: tau in model units (mm),
# rho in 1/mm, s in px/mm, f in px. rho -> 0 is the regular weak-perspective
# limit (scaled orthography with scale s), which is why the solver uses rho
# itself and not log rho (DESIGN D-02). Radial distortion `k` is not part of the
# inverse-depth block: conversions carry it through unchanged and
# `project_invdepth` is the distortion-free model.
# ---------------------------------------------------------------------------


def camera_to_invdepth(cam: Camera) -> dict:
    """``Camera`` -> inverse-depth parameters ``{'R', 'tau' (2,), 's', 'rho'}``.

    rho = 1/t_z (1/mm), s = f*rho (px/mm), tau = t[:2] (mm), R copied. Requires
    t_z > 0 (the model origin in front of the camera), else ``ValueError``.
    """
    t = np.asarray(cam.t, float)
    tz = float(t[2])
    if not (np.isfinite(tz) and tz > 0.0):
        raise ValueError(f"inverse depth needs t_z > 0 (model origin in front of the camera); got t_z={tz!r}")
    rho = 1.0 / tz
    return {"R": np.asarray(cam.R, float).copy(), "tau": t[:2].copy(), "s": float(cam.f) * rho, "rho": rho}


def invdepth_to_camera(R: np.ndarray, tau: np.ndarray, s: float, rho: float, like: Camera) -> Camera:
    """Inverse-depth parameters -> ``Camera`` (f = s/rho, t = (tau_x, tau_y, 1/rho)).

    Principal point, image size and distortion ``k`` are copied from ``like``.
    rho must be > 0 (a finite camera distance), else ``ValueError``.
    """
    rho = float(rho)
    if not (np.isfinite(rho) and rho > 0.0):
        raise ValueError(f"invdepth_to_camera needs rho > 0; got {rho!r}")
    tau = np.asarray(tau, float).reshape(2)
    return Camera(f=float(s) / rho, cx=like.cx, cy=like.cy, width=like.width, height=like.height,
                  R=np.asarray(R, float).copy(), t=np.array([tau[0], tau[1], 1.0 / rho]),
                  k=np.asarray(like.k, float).copy())


def project_invdepth(X: np.ndarray, R: np.ndarray, tau: np.ndarray, s: float, rho: float,
                     cx: float, cy: float) -> np.ndarray:
    """Project world points (N,3) with inverse-depth parameters (DESIGN D-02).

    uv = c + s ((R X)_xy + tau) / (1 + rho (R X)_z); pixels, no distortion. Equal
    to ``Camera.project`` of ``invdepth_to_camera(...)`` up to rounding.
    """
    Y = np.asarray(X, float) @ np.asarray(R, float).T
    tau = np.asarray(tau, float).reshape(2)
    den = 1.0 + float(rho) * Y[:, 2:3]
    return float(s) * (Y[:, :2] + tau) / den + np.array([cx, cy])


# ---------------------------------------------------------------------------
# Local virtual cameras for off-axis faces (DESIGN D-12, 4.3 "Per-view camera
# model"; research notes smartphone-camera-pipeline "Camera model per view" and
# camera-perspective-distortion). WP-06 (d).
#
# * Rectilinear: rotating the camera about its centre is an exact image
#   homography H = K R_virt K^-1, so a pinhole photo of an off-axis face equals a
#   virtual pinhole camera pointed at the face (same f) followed by H.
# * Stereographic: face-aware wide-angle correction (Shih, Lai & Liang 2019) makes
#   each face region a similarity of the *stereographic* projection
#   r = 2 f tan(phi/2) about the principal point, which is conformal with local
#   magnification f sec^2(phi/2) in every direction (1.0994 f at 35 deg; a
#   rectilinear image has f sec^2(phi) radially and f sec(phi) tangentially,
#   1.4903 f / 1.2208 f at 35 deg; DESIGN D-12, checked in tests/test_m1_fixes.py).
#   Locally that is a pinhole camera rotated onto the face ray with
#   f' = f sec^2(theta/2) and its principal point at the face centre's
#   stereographic image position.
# ---------------------------------------------------------------------------


def face_ray_angle(cam: Camera, X_centre: np.ndarray) -> float:
    """Angle theta (radians) between the optical axis and the ray to ``X_centre`` (world, mm)."""
    xc = cam.to_camera(np.asarray(X_centre, float).reshape(1, 3))[0]
    return float(np.arctan2(np.hypot(xc[0], xc[1]), xc[2]))


def virtual_rotation(cam: Camera, X_centre: np.ndarray) -> np.ndarray:
    """Minimal rotation R_virt (camera frame) taking the ray to ``X_centre`` onto +z.

    Rotation about the axis d x e_z (d = unit ray direction) by the angle between
    d and e_z, so R_virt @ d = e_z. Identity for an on-axis centre. Raises
    ``ValueError`` when the centre is at the camera centre or directly behind it
    (the minimal rotation is then undefined).
    """
    xc = cam.to_camera(np.asarray(X_centre, float).reshape(1, 3))[0]
    n = float(np.linalg.norm(xc))
    if not n > 0.0:
        raise ValueError("X_centre coincides with the camera centre")
    d = xc / n
    axis = np.array([d[1], -d[0], 0.0])  # d x e_z
    sin_t = float(np.linalg.norm(axis))
    cos_t = float(d[2])
    if sin_t < 1e-15:
        if cos_t > 0.0:
            return np.eye(3)
        raise ValueError("X_centre lies directly behind the camera")
    k = axis / sin_t
    K = skew(k)
    return np.eye(3) + sin_t * K + (1.0 - cos_t) * (K @ K)


def rectilinear_virtual_homography(cam: Camera, R_virt: np.ndarray) -> np.ndarray:
    """Homography H = K R_virt K^-1 mapping real pinhole pixels to the rotated camera's pixels (f' = f)."""
    K = cam.K
    return K @ np.asarray(R_virt, float) @ np.linalg.inv(K)


def apply_homography(H: np.ndarray, uv: np.ndarray) -> np.ndarray:
    """Apply a 3x3 homography to pixel coordinates (N,2) (or a single (2,) point)."""
    uv = np.asarray(uv, float)
    single = uv.ndim == 1
    P = np.atleast_2d(uv)
    h = np.column_stack([P, np.ones(len(P))]) @ np.asarray(H, float).T
    out = h[:, :2] / h[:, 2:3]
    return out[0] if single else out


def rectilinear_virtual_camera(cam: Camera, X_centre: np.ndarray) -> tuple[Camera, np.ndarray]:
    """Virtual pinhole camera rotated about its centre onto the ray to ``X_centre``.

    Returns (camera, H): the camera has R' = R_virt R, t' = R_virt t (same centre),
    the same f, principal point, size and distortion; H = K R_virt K^-1 maps the
    real camera's (distortion-free) pixels exactly onto the virtual camera's.
    """
    Rv = virtual_rotation(cam, X_centre)
    virt = Camera(cam.f, cam.cx, cam.cy, cam.width, cam.height, Rv @ cam.R, Rv @ np.asarray(cam.t, float),
                  np.asarray(cam.k, float).copy())
    return virt, rectilinear_virtual_homography(cam, Rv)


def stereographic_project(Xc: np.ndarray, f: float, cx: float, cy: float) -> np.ndarray:
    """Stereographic projection of camera-frame points (N,3) about the principal point.

    A ray at angle phi from the optical axis lands at radius r = 2 f tan(phi/2)
    from (cx, cy) along its azimuth: uv = c + 2 f (x, y) / (|X| + z). Defined for
    every ray except the backward axis (|X| + z = 0).
    """
    Xc = np.atleast_2d(np.asarray(Xc, float))
    nrm = np.linalg.norm(Xc, axis=1, keepdims=True)
    return 2.0 * float(f) * Xc[:, :2] / (nrm + Xc[:, 2:3]) + np.array([cx, cy])


def stereographic_unproject(uv: np.ndarray, f: float, cx: float, cy: float) -> np.ndarray:
    """Inverse of :func:`stereographic_project`: pixels (N,2) -> unit rays (N,3) in the camera frame.

    With q = (uv - c) / (2 f): ray = (2 q, 1 - |q|^2) / (1 + |q|^2).
    """
    q = (np.atleast_2d(np.asarray(uv, float)) - np.array([cx, cy])) / (2.0 * float(f))
    q2 = np.sum(q * q, axis=1, keepdims=True)
    return np.column_stack([2.0 * q, 1.0 - q2]) / (1.0 + q2)


def stereographic_virtual_camera(cam: Camera, X_centre: np.ndarray):
    """Local pinhole camera equivalent to a stereographic face warp around ``X_centre``.

    Returns ``(virtual_camera, to_virtual)``:

    * ``virtual_camera``: R' = R_virt R, t' = R_virt t (same centre), focal
      f' = f sec^2(theta/2) with theta = :func:`face_ray_angle`, principal point at
      the face centre's stereographic image position c + 2 f tan(theta/2) (azimuth
      of the ray), same image size, no distortion (smartphone-camera-pipeline
      "local virtual camera ... principal point at the face centre").
    * ``to_virtual(uv_stereo) -> uv_virtual``: unproject with the stereographic
      model of ``cam`` (f, cx, cy), rotate by R_virt, pinhole-project with f' and
      the virtual principal point. For a stereographic image of world points X,
      ``to_virtual(stereographic_project(cam.to_camera(X), ...))`` equals
      ``virtual_camera.project(X)`` exactly, and its Jacobian at the face centre
      is the identity (equal local magnification f sec^2(theta/2)), so pixel
      noise keeps its scale near the face.
    """
    Rv = virtual_rotation(cam, X_centre)
    theta = face_ray_angle(cam, X_centre)
    f_virt = float(cam.f) / np.cos(theta / 2.0) ** 2
    xc = cam.to_camera(np.asarray(X_centre, float).reshape(1, 3))
    c_virt = stereographic_project(xc, cam.f, cam.cx, cam.cy)[0]
    virt = Camera(f_virt, float(c_virt[0]), float(c_virt[1]), cam.width, cam.height,
                  Rv @ cam.R, Rv @ np.asarray(cam.t, float))
    f0, cx0, cy0 = float(cam.f), float(cam.cx), float(cam.cy)

    def to_virtual(uv_stereo: np.ndarray) -> np.ndarray:
        rays = stereographic_unproject(uv_stereo, f0, cx0, cy0) @ Rv.T
        return f_virt * rays[:, :2] / rays[:, 2:3] + c_virt

    return virt, to_virtual
