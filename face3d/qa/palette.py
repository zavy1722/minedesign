"""Accessible overlay palette and colour maths (DESIGN 6.5; numpy + stdlib).

Conventions: colours are sRGB in [0, 1] (float arrays, last axis 3) unless a
function says it takes hex strings ('#RRGGBB'). Colour-vision-deficiency (CVD)
simulation uses the Machado, Oliveira & Fernandes 2009 severity-1.0 matrices
applied in LINEAR RGB, clipped to [0, 1] and re-encoded to sRGB (WP-09 spec).
Delta-E is CIE76 in CIELAB (D65 white). Contrast is the WCAG 2.x relative
luminance ratio.

The role colours are the Okabe-Ito set named in DESIGN 6.5; each role is always
drawn with a distinct glyph shape, a dark outline and a light halo.
"""
from __future__ import annotations

import numpy as np

# DESIGN 6.5: role -> (colour hex, glyph kind).
ROLES = {
    "auto_pin": ("#56B4E9", "circle"),
    "user_pin": ("#E69F00", "square"),
    "conflict": ("#D55E00", "cross"),
    "selected": ("#F0E442", "ring"),
    "model_contour": ("#009E73", "line"),
    "guessed": ("#CC79A7", "hatch"),
}
OUTLINE = "#000000"
HALO = "#FFFFFF"
# Residual colour bins for <1, 1-2, 2-3, >3 sigma: cividis-like (colour-blind
# safe, monotone in lightness). PROVISIONAL values sampled by hand from the
# cividis ramp (engineering judgement, DESIGN 6.5); not validated beyond monotone luminance.
RESIDUAL_BINS = ("#00204D", "#575C6D", "#A69D75", "#FFEA46")

_CVD = {
    "protan": np.array([[0.152286, 1.052583, -0.204868],
                        [0.114503, 0.786281, 0.099216],
                        [-0.003882, -0.048116, 1.051998]]),
    "deutan": np.array([[0.367322, 0.860646, -0.227968],
                        [0.280085, 0.672501, 0.047413],
                        [-0.011820, 0.042940, 0.968881]]),
    "tritan": np.array([[1.255528, -0.076749, -0.178779],
                        [-0.078411, 0.930809, 0.147602],
                        [0.004733, 0.691367, 0.303900]]),
}
_RGB2XYZ = np.array([[0.4124564, 0.3575761, 0.1804375],
                     [0.2126729, 0.7151522, 0.0721750],
                     [0.0193339, 0.1191920, 0.9503041]])
_WHITE = _RGB2XYZ @ np.ones(3)


def hex_to_rgb(h: str) -> np.ndarray:
    """'#RRGGBB' -> float sRGB array (3,) in [0, 1]."""
    h = h.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"bad hex colour {h!r}")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=float) / 255.0


def srgb_to_linear(c) -> np.ndarray:
    c = np.asarray(c, dtype=float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c) -> np.ndarray:
    c = np.asarray(c, dtype=float)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.maximum(c, 0.0) ** (1 / 2.4) - 0.055)


def simulate_cvd(rgb_srgb, kind: str) -> np.ndarray:
    """Simulate protan/deutan/tritan vision (Machado 2009, severity 1.0, linear RGB)."""
    if kind not in _CVD:
        raise ValueError(f"unknown CVD kind {kind!r}")
    lin = srgb_to_linear(rgb_srgb)
    out = np.clip(lin @ _CVD[kind].T, 0.0, 1.0)
    return np.clip(linear_to_srgb(out), 0.0, 1.0)


def _as_rgb(c) -> np.ndarray:
    return hex_to_rgb(c) if isinstance(c, str) else np.asarray(c, dtype=float)


def srgb_to_lab(rgb) -> np.ndarray:
    xyz = srgb_to_linear(_as_rgb(rgb)) @ _RGB2XYZ.T / _WHITE
    eps = 216 / 24389
    kap = 24389 / 27
    f = np.where(xyz > eps, np.cbrt(xyz), (kap * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]),
                     200 * (f[..., 1] - f[..., 2])], axis=-1)


def delta_e76(a, b) -> float:
    """CIE76 colour difference between two sRGB colours (hex or float triples)."""
    d = srgb_to_lab(a) - srgb_to_lab(b)
    return float(np.sqrt(np.sum(d * d, axis=-1)))


def relative_luminance(c) -> float:
    lin = srgb_to_linear(_as_rgb(c))
    return float(lin @ np.array([0.2126, 0.7152, 0.0722]))


def contrast_ratio(c1, c2) -> float:
    """WCAG contrast ratio (L_hi + 0.05)/(L_lo + 0.05), in [1, 21]."""
    l1, l2 = relative_luminance(c1), relative_luminance(c2)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)
