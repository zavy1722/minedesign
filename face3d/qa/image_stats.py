"""Image statistics for photo QA (DESIGN 4.1; numpy only).

Conventions: gray images are float (H, W) arrays (any scale; thresholds that
need [0, 1] say so); masks are boolean (H, W); points are (x, y) pixels.
"""
from __future__ import annotations

import math

import numpy as np


def laplacian_variance(gray, mask=None) -> float:
    """Variance of the 4-neighbour Laplacian over the valid region.

    Valid pixels are interior pixels (all four neighbours exist) that, when a
    mask is given, are True together with their four neighbours. Returns 0.0
    if the valid region is empty.
    """
    g = np.asarray(gray, dtype=float)
    if g.ndim != 2 or g.shape[0] < 3 or g.shape[1] < 3:
        return 0.0
    lap = (g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:] - 4.0 * g[1:-1, 1:-1])
    if mask is not None:
        m = np.asarray(mask, dtype=bool)
        valid = (m[1:-1, 1:-1] & m[:-2, 1:-1] & m[2:, 1:-1] & m[1:-1, :-2] & m[1:-1, 2:])
        lap = lap[valid]
    if lap.size == 0:
        return 0.0
    return float(np.var(lap))


def clipped_fraction(img, mask, thresh: float = 0.98) -> float:
    """Fraction of masked pixels with any channel >= thresh (img float in [0, 1], (H,W) or (H,W,3))."""
    a = np.asarray(img, dtype=float)
    if a.ndim == 3:
        a = a.max(axis=2)
    m = np.asarray(mask, dtype=bool)
    n = int(m.sum())
    if n == 0:
        return 0.0
    return float(np.count_nonzero(a[m] >= thresh)) / n


def eye_aspect_ratio(p) -> float:
    """Soukupova & Cech (2016) EAR for six eye points p1..p6 (p1/p4 corners):
    (|p2-p6| + |p3-p5|) / (2 |p1-p4|)."""
    p = np.asarray(p, dtype=float)
    if p.shape != (6, 2):
        raise ValueError("eye points must be (6, 2)")
    d = lambda i, j: float(np.linalg.norm(p[i] - p[j]))
    w = d(0, 3)
    if w == 0.0 or not math.isfinite(w):
        return float("nan")   # degenerate corners: no EAR (callers must ignore non-finite)
    return (d(1, 5) + d(2, 4)) / (2.0 * w)


def _conv_axis(a: np.ndarray, k: np.ndarray, axis: int) -> np.ndarray:
    r = (len(k) - 1) // 2
    n = a.shape[axis]
    mode = "reflect" if n > r else "edge"
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r, r)
    ap = np.pad(a, pad, mode=mode)
    out = np.zeros_like(a)
    for i, kv in enumerate(k):
        sl = [slice(None)] * a.ndim
        sl[axis] = slice(i, i + n)
        out += kv * ap[tuple(sl)]
    return out


def gaussian_blur(gray, sigma: float) -> np.ndarray:
    """Separable Gaussian blur, reflect padding, kernel radius ceil(3 sigma)."""
    g = np.asarray(gray, dtype=float)
    if sigma <= 0:
        return g.copy()
    r = int(math.ceil(3.0 * sigma))
    x = np.arange(-r, r + 1, dtype=float)
    k = np.exp(-0.5 * (x / sigma) ** 2)
    k /= k.sum()
    return _conv_axis(_conv_axis(g, k, 0), k, 1)


def box_blur(gray, r: int) -> np.ndarray:
    """Separable box blur of radius r (window 2r+1), reflect padding."""
    g = np.asarray(gray, dtype=float)
    r = int(r)
    if r <= 0:
        return g.copy()
    k = np.full(2 * r + 1, 1.0 / (2 * r + 1))
    return _conv_axis(_conv_axis(g, k, 0), k, 1)


def skin_smoothness_index(gray, cheek_mask, ref_mask) -> float:
    """Band energy in the cheeks over that in the reference mask (DESIGN 4.1 Q-RETOUCH).

    Band = gaussian_blur(1 px) - gaussian_blur(3 px); energy = mean of its
    square over the mask. Low values mean over-smoothed (retouched) skin.
    """
    band = gaussian_blur(gray, 1.0) - gaussian_blur(gray, 3.0)
    e2 = band * band
    cm, rm = np.asarray(cheek_mask, bool), np.asarray(ref_mask, bool)
    ec = float(e2[cm].mean()) if cm.any() else 0.0
    er = float(e2[rm].mean()) if rm.any() else 0.0
    if er == 0.0:
        return 1.0 if ec == 0.0 else float("inf")
    return ec / er
