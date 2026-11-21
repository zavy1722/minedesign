"""bpy-free overlay geometry (DESIGN 6.5). Returns polylines in image-pixel coordinates.

A polyline is an (m, 2) float array of (x, y) pixels. Closed shapes repeat their
first point as the last point, so every polyline can be drawn as an open strip.
Exception: sigma_ellipse returns an (n, 2) implicitly closed loop.
"""
from __future__ import annotations

import math

import numpy as np

from face3d.qa import palette

HIT_RADIUS_PX = 12   # pick radius around a pin (DESIGN 6.5; engineering judgement)
MIN_TARGET_PX = 24   # minimum interactive target size (WCAG 2.5.8)

_ROLE_WIDTH_PX = {"model_contour": 2.5}


def sigma_ellipse(center, cov2, k: float = 1.0, n: int = 32) -> np.ndarray:
    """k-sigma ellipse of a 2x2 covariance: (n, 2) implicitly closed loop (first point NOT repeated;
    the drawing layer closes it).

    Point i is at angle 2 pi i / n in the eigenbasis, so for an axis-aligned
    covariance the axis extremes are sampled exactly when n is divisible by 4.
    """
    cov = np.asarray(cov2, dtype=float)
    cov = 0.5 * (cov + cov.T)
    w, v = np.linalg.eigh(cov)
    w = np.maximum(w, 0.0)
    t = 2.0 * np.pi * np.arange(n) / n
    pts = (v * (k * np.sqrt(w))) @ np.vstack([np.cos(t), np.sin(t)])
    out = pts.T + np.asarray(center, dtype=float)
    return out


def residual_arrow(p_obs, p_model, scale: float = 5.0, head_px: float = 6.0):
    """Arrow from the model point towards the observation, residual magnified by ``scale``.

    Returns [shaft, head] (two polylines); only [shaft] when the residual is zero.
    """
    a = np.asarray(p_model, dtype=float)
    d = (np.asarray(p_obs, dtype=float) - a) * scale
    b = a + d
    shaft = np.array([a, b])
    ln = float(np.linalg.norm(d))
    if ln < 1e-12:
        return [shaft]
    u = d / ln
    h = min(head_px, ln)
    ang = math.radians(25.0)
    c, s = math.cos(ang), math.sin(ang)
    back = -u * h
    l = b + np.array([c * back[0] - s * back[1], s * back[0] + c * back[1]])
    r = b + np.array([c * back[0] + s * back[1], -s * back[0] + c * back[1]])
    return [shaft, np.array([l, b, r])]


def _circle(c, r, n=16):
    t = 2 * np.pi * np.arange(n + 1) / n
    return np.stack([c[0] + r * np.cos(t), c[1] + r * np.sin(t)], axis=1)


def glyph(kind: str, center, size_px: float = 9.0, ui_scale: float = 1.0):
    """Marker polylines for a glyph kind, ``size_px * ui_scale`` across (diameter / side / span)."""
    c = np.asarray(center, dtype=float)
    s = float(size_px) * float(ui_scale)
    h = s / 2.0
    x, y = c
    if kind == "circle":
        return [_circle(c, h)]
    if kind == "square":
        return [np.array([[x - h, y - h], [x + h, y - h], [x + h, y + h], [x - h, y + h], [x - h, y - h]])]
    if kind == "cross":
        return [np.array([[x - h, y - h], [x + h, y + h]]), np.array([[x - h, y + h], [x + h, y - h]])]
    if kind == "ring":
        return [_circle(c, h * 1.3), _circle(c, h * 0.6)]
    if kind == "line":
        return [np.array([[x - h, y], [x + h, y]])]
    if kind == "hatch":
        return [np.array([[x - h, y + o + h], [x + h, y + o - h]]) for o in (-h / 2, 0.0, h / 2)]
    raise ValueError(f"unknown glyph kind {kind!r}")


def styled(polylines, role: str, width_px: float | None = None):
    """Draw list for a role: [(polyline, width_px, colour_hex)], ordered light halo
    (width + 4), dark outline (width + 2), colour (width); all halos first so the
    colour layer is never covered."""
    colour, _ = palette.ROLES[role]
    w = float(width_px if width_px is not None else _ROLE_WIDTH_PX.get(role, 2.0))
    out = []
    for extra, col in ((4.0, palette.HALO), (2.0, palette.OUTLINE), (0.0, colour)):
        out.extend((p, w + extra, col) for p in polylines)
    return out


def hatch_polygon(poly, spacing_px: float = 6.0, angle_deg: float = 45.0):
    """Parallel hatch segments clipped to a polygon (even-odd rule).

    ``poly`` is (m, 2), open or closed. Lines have direction ``angle_deg`` and
    are spaced ``spacing_px`` apart at a phase fixed to the image origin.
    Returns a list of (2, 2) arrays.
    """
    P = np.asarray(poly, dtype=float)
    if len(P) > 1 and np.allclose(P[0], P[-1]):
        P = P[:-1]
    if len(P) < 3:
        return []
    a = math.radians(angle_deg)
    d = np.array([math.cos(a), math.sin(a)])
    nrm = np.array([-d[1], d[0]])
    u, v = P @ d, P @ nrm
    segs = []
    k0, k1 = int(math.ceil(v.min() / spacing_px)), int(math.floor(v.max() / spacing_px))
    v2, u2 = np.roll(v, -1), np.roll(u, -1)
    for k in range(k0, k1 + 1):
        c = k * spacing_px
        cross = (v <= c) != (v2 <= c)       # half-open rule: robust at vertices
        if not cross.any():
            continue
        t = (c - v[cross]) / (v2[cross] - v[cross])
        us = np.sort(u[cross] + t * (u2[cross] - u[cross]))
        for i in range(0, len(us) - 1, 2):
            if us[i + 1] - us[i] > 1e-9:
                segs.append(np.array([d * us[i] + nrm * c, d * us[i + 1] + nrm * c]))
    return segs


def blur_sigma_px(face_width_px: float) -> float:
    """Comparison blur sigma = 3 % of face width (DESIGN 6.5)."""
    return 0.03 * float(face_width_px)


def thumbnail_shape(h: int, w: int, target: int = 64):
    """(h, w) of a thumbnail whose longer side is ``target`` px (each side >= 1)."""
    s = target / max(h, w)
    return max(1, int(round(h * s))), max(1, int(round(w * s)))
