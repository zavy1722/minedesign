"""Landmark detector simulator (DESIGN 7.2 "Detector simulator", 4.4, D-06).

Model per subject (landmark i of kind k_i) and view v:

* **Definition bias** b_i ~ N(0, sigma_def(k_i)^2 I_3) mm, drawn ONCE per subject and
  shared by every view (D-06: a per-landmark offset, never per-observation noise).
* **Anisotropic noise** in pixels: with px_per_mm p_iv = f_v / z_iv (z_iv the camera
  depth of the observed point), sigma_n,px = noise_scale * sigma_n(k_i) * p_iv along the
  image normal and sigma_t,px = noise_scale * sigma_t(k_i) * p_iv along a tangent
  direction t_i, a fixed random unit 2D image vector per landmark per subject.
* **Outliers**: with probability ``outlier_frac`` per observation, a displacement of
  magnitude U(5, 20) * sigma_iso,px in a uniformly random direction (DESIGN 7.2
  "5 % outliers at 5-20 sigma"), where sigma_iso,px = sqrt((sigma_n,px^2 + sigma_t,px^2)/2)
  is the isotropic-equivalent sigma (the same convention WP-07's noise model uses for an
  unknown tangent).
* **Visibility**: hidden (NaN) when cos(angle((X_i - head_centre), (C_v - X_i))) < -0.1
  (the tests/test_bundle_mesh._scene proxy), when behind the camera, or when the
  observed pixel falls outside the image.

So uv_iv = project_v(X_i + b_i) + R(t_i) [n_t sigma_t,px, n_n sigma_n,px]^T (+ outlier).

Random draws are made in a fixed order and always drawn (bias, tangents, then per view
noise and outlier variables), and disabled effects are zeroed rather than skipped, so
scenarios that differ only in ``definition_bias`` / ``outlier_frac`` / ``noise_scale``
see common random numbers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from .rigs import Rig, facing_mask, in_image_mask

__all__ = ["KIND_SIGMA_MM", "KIND_SIGMA_DEF_MM", "LEGACY_KIND", "OUTLIER_SIGMA_RANGE",
           "Observation", "legacy_kind", "legacy_kinds", "simulate"]

# (normal, tangent) 1-sigma localisation error in mm by landmark kind (DESIGN 4.4 table;
# contour/brow tangents, which DESIGN leaves "free", are given finite values here
# so the simulator can draw them: contour 10 mm, brow 8 mm; WBS WP-01). Mostly 🧠
# (unverified) in DESIGN, i.e. PROVISIONAL.
KIND_SIGMA_MM: dict[str, tuple[float, float]] = {
    "sharp_junction": (1.25, 1.25),
    "extremal": (2.0, 3.0),
    "curve": (1.5, 7.5),
    "contour": (2.5, 10.0),
    "brow": (4.0, 8.0),
    "iris": (0.6, 0.6),
    "generic": (2.0, 2.0),
}

# Definition-bias SD in mm per axis by kind (DESIGN 4.4 sigma_def column, D-06; iris has
# none). PROVISIONAL (🧠 in DESIGN).
KIND_SIGMA_DEF_MM: dict[str, float] = {
    "sharp_junction": 0.5,
    "extremal": 1.5,
    "curve": 1.0,
    "contour": 2.0,
    "brow": 2.0,
    "iris": 0.0,
    "generic": 1.5,
}

# Kinds of the legacy face3d.synthetic landmark names (suffix _L/_R stripped first;
# WBS WP-01, following the DESIGN 4.4 kind examples).
LEGACY_KIND: dict[str, str] = {
    "endocanthion": "sharp_junction", "exocanthion": "sharp_junction", "cheilion": "sharp_junction",
    "subnasale": "sharp_junction", "stomion": "sharp_junction", "alare": "sharp_junction",
    "pronasale": "extremal", "pogonion": "extremal", "menton": "extremal", "glabella": "extremal",
    "zygion": "extremal", "gonion": "extremal", "vertex_front": "extremal",
    "forehead_side": "extremal", "tragion": "extremal",
    "labrale_superius": "curve", "labrale_inferius": "curve", "nasion": "curve",
    "pupil": "iris",
    "brow_inner": "brow", "brow_outer": "brow",
}

# Outlier displacement range in units of the isotropic sigma (DESIGN 7.2: "5 % outliers at 5-20 sigma").
OUTLIER_SIGMA_RANGE = (5.0, 20.0)


@dataclass
class Observation:
    """Simulated detections of one subject in every view of a rig.

    uv            : per view (N, 2) pixels, NaN rows where hidden.
    sigma_px_true : per view (N, 2) true (normal, tangent) noise sigma in px (NaN where hidden).
    outlier_mask  : per view (N,) bool, True where an outlier displacement was applied (visible only).
    bias_3d       : (N, 3) mm, the shared definition bias (zeros when disabled).
    tangent_dirs  : (N, 2) unit image-space tangent direction per landmark.
    visible       : per view (N,) bool (== ~isnan(uv[:, 0])).
    kinds         : the landmark kinds used.
    """

    uv: list[np.ndarray]
    sigma_px_true: list[np.ndarray]
    outlier_mask: list[np.ndarray]
    bias_3d: np.ndarray
    tangent_dirs: np.ndarray
    visible: list[np.ndarray] = field(default_factory=list)
    kinds: list[str] = field(default_factory=list)


def legacy_kind(name: str) -> str:
    """Kind of a legacy synthetic landmark name (``'generic'`` when unknown)."""
    base = name[:-2] if name.endswith(("_L", "_R")) else name
    return LEGACY_KIND.get(base, "generic")


def legacy_kinds(names: Sequence[str]) -> list[str]:
    return [legacy_kind(n) for n in names]


def simulate(X_true: np.ndarray, kinds: Sequence[str], rig: Rig, rng: np.random.Generator,
             outlier_frac: float = 0.05, definition_bias: bool = True, noise_scale: float = 1.0,
             head_centre: Sequence[float] = (0.0, 0.0, 0.0)) -> Observation:
    """Simulate 2D detections of ``X_true`` (N, 3 mm, head frame) in every view of ``rig``.

    ``kinds`` gives each landmark's kind (keys of :data:`KIND_SIGMA_MM`; unknown kinds
    fall back to ``'generic'``). Defaults: 5 % outliers (DESIGN 7.2), definition bias on
    (D-06), noise at the nominal kind sigmas, head centre at the head-frame origin.
    """
    X_true = np.asarray(X_true, float)
    n = len(X_true)
    if len(kinds) != n:
        raise ValueError("kinds must have one entry per landmark")
    kinds = [k if k in KIND_SIGMA_MM else "generic" for k in kinds]
    s_nt = np.array([KIND_SIGMA_MM[k] for k in kinds], float)            # (N, 2) mm
    s_def = np.array([KIND_SIGMA_DEF_MM[k] for k in kinds], float)        # (N,) mm

    # Subject-level draws (always made, so streams stay aligned across settings).
    b = rng.normal(size=(n, 3)) * s_def[:, None]
    if not definition_bias:
        b = np.zeros_like(b)
    theta = rng.uniform(0.0, 2.0 * np.pi, size=n)
    tdir = np.column_stack([np.cos(theta), np.sin(theta)])                 # unit tangent
    ndir = np.column_stack([-tdir[:, 1], tdir[:, 0]])                      # unit normal
    Xo = X_true + b                                                        # observed 3D points

    uvs, sig_list, out_list, vis_list = [], [], [], []
    for cam in rig.cameras:
        g_t = rng.normal(size=n)
        g_n = rng.normal(size=n)
        u_out = rng.random(n)
        mag = rng.uniform(OUTLIER_SIGMA_RANGE[0], OUTLIER_SIGMA_RANGE[1], size=n)
        ang = rng.uniform(0.0, 2.0 * np.pi, size=n)

        front = facing_mask(cam, X_true, head_centre) & (cam.depth(Xo) > 0.0)
        z = cam.depth(Xo)
        ppm = np.where(front, cam.f / np.where(front, z, 1.0), np.nan)    # px per mm
        sig_n = noise_scale * s_nt[:, 0] * ppm
        sig_t = noise_scale * s_nt[:, 1] * ppm
        uv = np.full((n, 2), np.nan)
        if front.any():
            uv[front] = cam.project(Xo[front])
        uv = uv + tdir * (g_t * sig_t)[:, None] + ndir * (g_n * sig_n)[:, None]
        is_out = front & (u_out < outlier_frac)
        sig_iso = np.sqrt(0.5 * (sig_n ** 2 + sig_t ** 2))
        disp = (mag * sig_iso)[:, None] * np.column_stack([np.cos(ang), np.sin(ang)])
        uv[is_out] += disp[is_out]
        vis = front & in_image_mask(cam, uv)
        uv[~vis] = np.nan
        sig = np.column_stack([sig_n, sig_t])
        sig[~vis] = np.nan
        uvs.append(uv)
        sig_list.append(sig)
        out_list.append(is_out & vis)
        vis_list.append(vis)
    return Observation(uv=uvs, sigma_px_true=sig_list, outlier_mask=out_list, bias_3d=b,
                       tangent_dirs=tdir, visible=vis_list, kinds=list(kinds))
