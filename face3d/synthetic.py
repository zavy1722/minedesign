"""Synthetic test data.

The landmark coordinates below are ILLUSTRATIVE ONLY: a rough, hand-placed
face-like point set used to exercise the solvers with realistic depth relief.
They are not anatomical reference data; sourced norms live in research/data/.

Head frame: millimetres, +x = subject's left (viewer's right), +y = up,
+z = out of the face toward a frontal camera, origin near the head centre.
"""
from __future__ import annotations

import numpy as np

from .geometry.camera import Camera, focal_px_from_35mm, look_at

_MIDLINE = {
    "vertex_front": (0, 90, 85), "glabella": (0, 45, 92), "nasion": (0, 35, 88),
    "pronasale": (0, -5, 115), "subnasale": (0, -20, 100), "labrale_superius": (0, -32, 102),
    "stomion": (0, -40, 98), "labrale_inferius": (0, -48, 100), "pogonion": (0, -75, 95),
    "menton": (0, -88, 85),
}
_BILATERAL = {
    "endocanthion": (16, 30, 80), "exocanthion": (46, 30, 70), "pupil": (31, 30, 82),
    "alare": (17, -12, 92), "cheilion": (25, -40, 88), "zygion": (68, 20, 40),
    "gonion": (52, -62, 20), "tragion": (72, 15, -5), "brow_inner": (25, 50, 88),
    "brow_outer": (50, 47, 75), "forehead_side": (40, 85, 70),
}


def synthetic_landmarks() -> tuple[list[str], np.ndarray]:
    names, pts = [], []
    for k, v in _MIDLINE.items():
        names.append(k); pts.append(v)
    for k, (x, y, z) in _BILATERAL.items():
        names.append(k + "_L"); pts.append((x, y, z))
        names.append(k + "_R"); pts.append((-x, y, z))
    return names, np.asarray(pts, float)


def orbit_camera(distance_mm: float, yaw_deg: float, pitch_deg: float, f35: float,
                 width: int = 3000, height: int = 4000, target=(0.0, 0.0, 60.0)) -> Camera:
    """Camera on a sphere around `target`; yaw > 0 moves toward the subject's left."""
    yaw, pitch = np.radians([yaw_deg, pitch_deg])
    tgt = np.asarray(target, float)
    eye = tgt + distance_mm * np.array([np.sin(yaw) * np.cos(pitch), np.sin(pitch), np.cos(yaw) * np.cos(pitch)])
    R, t = look_at(eye, tgt)
    return Camera.centered(focal_px_from_35mm(f35, width, height), width, height, R=R, t=t)


def mirror_pairs(names: list[str]) -> list[tuple[int, int]]:
    """(left, right) index pairs from the _L/_R naming convention."""
    idx = {n: i for i, n in enumerate(names)}
    return [(i, idx[n[:-2] + "_R"]) for i, n in enumerate(names) if n.endswith("_L") and n[:-2] + "_R" in idx]


def midline_indices(names: list[str]) -> list[int]:
    return [i for i, n in enumerate(names) if not (n.endswith("_L") or n.endswith("_R"))]


def random_subject(template: np.ndarray, names: list[str], rng: np.random.Generator,
                   identity_sd: float = 4.0, asym_sd: float = 1.0, scale_sd: float = 0.04) -> np.ndarray:
    """A plausible 'other person': smooth symmetric identity change + small asymmetry."""
    pairs = mirror_pairs(names)
    mid = midline_indices(names)
    # Smooth identity field: random low-order polynomial displacement + per-landmark jitter.
    c = template - template.mean(0)
    feats = np.column_stack([np.ones(len(c)), c / 100.0, (c / 100.0) ** 2])
    coef = rng.normal(scale=identity_sd, size=(feats.shape[1], 3))
    d = feats @ coef * 0.5 + rng.normal(scale=identity_sd * 0.5, size=template.shape)
    X = template * (1.0 + rng.normal(scale=scale_sd)) + d
    # Symmetrise, then add a little true asymmetry.
    for l, r in pairs:
        avg = (X[l] + X[r] * np.array([-1, 1, 1])) / 2.0
        X[l], X[r] = avg, avg * np.array([-1, 1, 1])
    X[mid, 0] = 0.0
    return X + rng.normal(scale=asym_sd, size=X.shape)
