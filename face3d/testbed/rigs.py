"""Camera rigs (capture protocols) for the landmark test bed (DESIGN 7.2 "Rigs").

Every protocol places cameras with :func:`face3d.synthetic.orbit_camera` around a
``target`` point (default (0, 0, 60) mm, the legacy-frame face centre) in a
3000 x 4000 px portrait image (WBS WP-01). Cameras follow the engine convention
(OpenCV: X_c = R X + t, +y down, +z forward; DESIGN 3.1); yaw > 0 moves the camera
toward the subject's left.

Focal-length priors mimic EXIF (DESIGN 4.2): the declared prior is
``f_true * exp(N(0, EXIF_VALUE_LOG_SD^2))``, drawn once per focal group (all photos
from one camera + zoom carry the same EXIF value), with log-sigma
``EXIF_PRIOR_LOG_SIGMA`` = 0.04 (DESIGN 4.2 "EXIF f35, uncropped original"). Views
without EXIF get ``f_prior_px = None`` and log-sigma 0.6 (DESIGN 4.2 "Nothing").

Visibility guarantee: each view is redrawn (same protocol distribution,
deterministic, at most ``MAX_VIEW_ATTEMPTS`` times) until at least ``MIN_VISIBLE``
landmarks pass the detector visibility proxy :func:`visible_mask` for the points
``X`` (the subject, or the legacy template when ``X`` is None).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

import numpy as np

from ..geometry.camera import Camera
from ..synthetic import orbit_camera, synthetic_landmarks

__all__ = [
    "Rig", "visible_mask", "facing_mask", "in_image_mask", "studio_ring", "rear_phone",
    "selfie", "camera_roll", "PROTOCOLS", "IMAGE_W", "IMAGE_H", "DEFAULT_TARGET",
    "MIN_VISIBLE", "MAX_VIEW_ATTEMPTS", "VISIBILITY_COS_MIN",
]

IMAGE_W, IMAGE_H = 3000, 4000                    # portrait 3:4 (WBS WP-01)
DEFAULT_TARGET = (0.0, 0.0, 60.0)                # mm, legacy-frame face centre (orbit_camera default)
MIN_VISIBLE = 6                                  # reconstruct_landmarks needs >= 6 per photo
MAX_VIEW_ATTEMPTS = 200                          # bounded redraws per view
# Self-occlusion proxy: hidden if cos(angle((X_i - head_centre), (C - X_i))) < -0.1
# (same proxy as tests/test_bundle_mesh._scene; WBS WP-01).
VISIBILITY_COS_MIN = -0.1

EXIF_PRIOR_LOG_SIGMA = 0.04                      # DESIGN 4.2, EXIF f35 uncropped
EXIF_VALUE_LOG_SD = 0.01                         # EXIF rounding/report error (WBS WP-01; PROVISIONAL)
NO_EXIF_LOG_SIGMA = 0.6                          # DESIGN 4.2, "Nothing" row
PITCH_RANGE_DEG = (-8.0, 8.0)                    # as tests/test_bundle_mesh._scene (PROVISIONAL for all rigs)

# Protocol ranges (WBS WP-01; DESIGN 7.2 "Rigs"; validation-test-bed.md Table 2).
STUDIO_F35 = 85.0
STUDIO_DIST_MM = (1500.0, 3000.0)
REAR_YAWS_DEG = (-60.0, -30.0, 0.0, 30.0, 60.0)
REAR_F35 = (24.0, 28.0)
REAR_DIST_MM = (600.0, 1500.0)
SELFIE_F35 = (22.0, 30.0)
SELFIE_DIST_MM = (250.0, 450.0)
SELFIE_YAW_DEG = (-30.0, 30.0)
ROLL_F35_CHOICES = (24.0, 26.0, 50.0, 77.0)
ROLL_DIST_MM = (500.0, 3000.0)
ROLL_YAW_DEG = (-45.0, 45.0)


@dataclass
class Rig:
    """A set of views of one subject. Lists are per view, in view order."""

    name: str
    cameras: list[Camera]
    f_prior_px: list[float | None]
    f_prior_log_sigma: list[float]
    focal_group: list[str | None]
    is_front_camera: list[bool]
    view_yaw_deg: list[float]
    view_pitch_deg: list[float] = field(default_factory=list)
    distance_mm: list[float] = field(default_factory=list)   # camera to target
    target: tuple[float, float, float] = DEFAULT_TARGET

    @property
    def n_views(self) -> int:
        return len(self.cameras)


# --------------------------------------------------------------------------- visibility
def facing_mask(cam: Camera, X: np.ndarray, head_centre: Sequence[float] = (0.0, 0.0, 0.0),
                cos_min: float = VISIBILITY_COS_MIN) -> np.ndarray:
    """True where the self-occlusion proxy keeps the point and it is in front of the camera."""
    X = np.asarray(X, float)
    out = (X - np.asarray(head_centre, float))
    view = cam.center - X
    no = np.linalg.norm(out, axis=1)
    nv = np.linalg.norm(view, axis=1)
    cos = np.einsum("ij,ij->i", out, view) / np.maximum(no * nv, 1e-12)
    cos = np.where(no < 1e-9, 1.0, cos)               # a point at the head centre: no normal
    return (cos >= cos_min) & (cam.depth(X) > 0.0)


def in_image_mask(cam: Camera, uv: np.ndarray) -> np.ndarray:
    """True where pixel coordinates lie inside [0, W] x [0, H] (DESIGN 3.1 corner origin)."""
    uv = np.asarray(uv, float)
    with np.errstate(invalid="ignore"):
        return (np.isfinite(uv).all(1) & (uv[:, 0] >= 0.0) & (uv[:, 0] <= cam.width)
                & (uv[:, 1] >= 0.0) & (uv[:, 1] <= cam.height))


def visible_mask(cam: Camera, X: np.ndarray, head_centre: Sequence[float] = (0.0, 0.0, 0.0)) -> np.ndarray:
    """Detector visibility proxy on noise-free projections: facing and inside the image."""
    m = facing_mask(cam, X, head_centre)
    uv = np.full((len(X), 2), np.nan)
    if m.any():
        uv[m] = cam.project(np.asarray(X, float)[m])
    return m & in_image_mask(cam, uv)


# --------------------------------------------------------------------------- helpers
def _points(X: np.ndarray | None) -> np.ndarray:
    if X is None:
        return synthetic_landmarks()[1]
    return np.asarray(X, float)


def _draw_view(rng: np.random.Generator, draw: Callable[[np.random.Generator], tuple[float, float, float, float]],
               X: np.ndarray, target, head_centre, width: int, height: int
               ) -> tuple[Camera, float, float, float]:
    """Draw (yaw, pitch, distance, f35) until the view sees >= MIN_VISIBLE points."""
    for _ in range(MAX_VIEW_ATTEMPTS):
        yaw, pitch, dist, f35 = draw(rng)
        cam = orbit_camera(dist, yaw, pitch, f35, width=width, height=height, target=target)
        if int(visible_mask(cam, X, head_centre).sum()) >= MIN_VISIBLE:
            return cam, yaw, pitch, dist
    raise RuntimeError("rig: could not place a view with >= %d visible landmarks in %d attempts"
                       % (MIN_VISIBLE, MAX_VIEW_ATTEMPTS))


def _exif_priors(rng: np.random.Generator, cams: list[Camera], groups: list[str | None],
                 has_exif: list[bool]) -> tuple[list[float | None], list[float]]:
    """One EXIF value per focal group (or per view when ungrouped)."""
    per_group: dict = {}
    priors: list[float | None] = []
    sigmas: list[float] = []
    for k, (cam, g, ok) in enumerate(zip(cams, groups, has_exif)):
        key = ("g", g) if g is not None else ("v", k)
        if key not in per_group:
            per_group[key] = float(rng.normal(scale=EXIF_VALUE_LOG_SD))
        if ok:
            priors.append(float(cam.f * np.exp(per_group[key])))
            sigmas.append(EXIF_PRIOR_LOG_SIGMA)
        else:
            priors.append(None)
            sigmas.append(NO_EXIF_LOG_SIGMA)
    return priors, sigmas


def _build(name, rng, draws, X, target, head_centre, width, height, groups, front, has_exif) -> Rig:
    Xp = _points(X)
    cams, yaws, pitches, dists = [], [], [], []
    for draw in draws:
        cam, yaw, pitch, dist = _draw_view(rng, draw, Xp, target, head_centre, width, height)
        cams.append(cam); yaws.append(float(yaw)); pitches.append(float(pitch)); dists.append(float(dist))
    priors, sigmas = _exif_priors(rng, cams, groups, has_exif)
    return Rig(name=name, cameras=cams, f_prior_px=priors, f_prior_log_sigma=sigmas,
               focal_group=list(groups), is_front_camera=list(front), view_yaw_deg=yaws,
               view_pitch_deg=pitches, distance_mm=dists, target=tuple(float(v) for v in target))


# --------------------------------------------------------------------------- protocols
def studio_ring(rng: np.random.Generator, n_views: int = 7, *, X: np.ndarray | None = None,
                target=DEFAULT_TARGET, head_centre=(0.0, 0.0, 0.0),
                width: int = IMAGE_W, height: int = IMAGE_H) -> Rig:
    """Studio ring: yaws evenly spaced over [-90, 90] deg, pitch U(-8, 8), 85 mm-eq,
    distance U(1500, 3000) mm per view, EXIF prior sigma 0.04, one focal group 'studio'."""
    yaws = np.linspace(-90.0, 90.0, n_views) if n_views > 1 else np.zeros(1)

    def mk(yaw):
        return lambda r: (float(yaw), r.uniform(*PITCH_RANGE_DEG), r.uniform(*STUDIO_DIST_MM), STUDIO_F35)
    return _build("studio_ring", rng, [mk(y) for y in yaws], X, target, head_centre, width, height,
                  ["studio"] * n_views, [False] * n_views, [True] * n_views)


def rear_phone(rng: np.random.Generator, n_views: int = 5, *, X: np.ndarray | None = None,
               target=DEFAULT_TARGET, head_centre=(0.0, 0.0, 0.0),
               width: int = IMAGE_W, height: int = IMAGE_H) -> Rig:
    """Helper-held rear phone: yaws (-60, -30, 0, 30, 60)[:n], one shared f35 U(24, 28),
    distance U(600, 1500) mm per view, pitch U(-8, 8), group 'phone', EXIF sigma 0.04."""
    if not 1 <= n_views <= len(REAR_YAWS_DEG):
        raise ValueError("rear_phone supports 1..%d views" % len(REAR_YAWS_DEG))
    f35 = float(rng.uniform(*REAR_F35))

    def mk(yaw):
        return lambda r: (float(yaw), r.uniform(*PITCH_RANGE_DEG), r.uniform(*REAR_DIST_MM), f35)
    return _build("rear_phone", rng, [mk(y) for y in REAR_YAWS_DEG[:n_views]], X, target, head_centre,
                  width, height, ["phone"] * n_views, [False] * n_views, [True] * n_views)


def selfie(rng: np.random.Generator, n_views: int = 3, *, X: np.ndarray | None = None,
           target=DEFAULT_TARGET, head_centre=(0.0, 0.0, 0.0),
           width: int = IMAGE_W, height: int = IMAGE_H) -> Rig:
    """Front-camera selfies: one shared f35 U(22, 30), distance U(250, 450) mm, yaw U(-30, 30),
    pitch U(-8, 8), group 'front', EXIF sigma 0.04."""
    f35 = float(rng.uniform(*SELFIE_F35))

    def draw(r):
        return r.uniform(*SELFIE_YAW_DEG), r.uniform(*PITCH_RANGE_DEG), r.uniform(*SELFIE_DIST_MM), f35
    return _build("selfie", rng, [draw] * n_views, X, target, head_centre, width, height,
                  ["front"] * n_views, [True] * n_views, [True] * n_views)


def camera_roll(rng: np.random.Generator, n_views: int = 5, *, X: np.ndarray | None = None,
                target=DEFAULT_TARGET, head_centre=(0.0, 0.0, 0.0),
                width: int = IMAGE_W, height: int = IMAGE_H) -> Rig:
    """Mixed camera roll: f35 per view from {24, 26, 50, 77}, distance U(500, 3000) mm,
    yaw U(-45, 45), pitch U(-8, 8); n_views // 2 randomly chosen views lack EXIF
    (f_prior None, log-sigma 0.6); one focal group per f35 ('roll_f24', ...)."""
    f35s = [float(v) for v in rng.choice(ROLL_F35_CHOICES, size=n_views)]
    no_exif = set(int(i) for i in rng.choice(n_views, size=n_views // 2, replace=False))

    def mk(f35):
        return lambda r: (r.uniform(*ROLL_YAW_DEG), r.uniform(*PITCH_RANGE_DEG), r.uniform(*ROLL_DIST_MM), f35)
    groups = ["roll_f%d" % int(round(f)) for f in f35s]
    return _build("camera_roll", rng, [mk(f) for f in f35s], X, target, head_centre, width, height,
                  groups, [False] * n_views, [k not in no_exif for k in range(n_views)])


PROTOCOLS: dict[str, Callable[..., Rig]] = {
    "studio_ring": studio_ring,
    "rear_phone": rear_phone,
    "selfie": selfie,
    "camera_roll": camera_roll,
}

