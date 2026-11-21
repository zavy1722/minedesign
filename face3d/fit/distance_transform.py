"""Exact Euclidean distance transform, bilinear sampling and image gradients (DESIGN D-13, 4.16; WP-17).

The contour term's backward (model -> photo) residual reads the observed contour's
distance transform at the projected model rim (DESIGN 4.16 "Residuals"), and the mask
contour source orients its normals with the distance field of the mask complement.
Blender bundles no SciPy (*face-segmentation-contours* "Use an EDT (Felzenszwalb-
Huttenlocher in NumPy; Blender bundles no SciPy)"), so the transform is implemented here.

Algorithm
---------
Felzenszwalb & Huttenlocher, "Distance Transforms of Sampled Functions", Theory of
Computing 8 (2012): the squared Euclidean transform of a sampled function f is separable,
D(p) = min_q (|p - q|^2 + f(q)), and each 1D pass is the lower envelope of the parabolas
(x - q)^2 + f(q), built left to right and read off in a second sweep (O(n) per line).
:func:`edt_squared` runs the 1D pass down the **columns** (f = 0 on True pixels, +inf
elsewhere) and then along the **rows** of the result.  The 1D pass is vectorised across
all lines of a pass: every line advances in lock-step over q, and the "pop parabolas
while the new intersection lies left of the stored boundary" loop runs on the subset
of lines that still need popping.  The result is **exact**: the squared distances are
integers, every comparison between parabola values at an integer abscissa differs by
at least 1 or not at all, and the final values are evaluated as (p - q)^2 + f(q) in
integer-valued float64 arithmetic (exact below 2^53).

Conventions (DESIGN 3.1)
------------------------
* Arrays are indexed ``[row, col]``.  Continuous image coordinates (u, v) have their
  origin at the top-left *corner*; the pixel ``[r, c]`` has its centre at
  (u, v) = (c + 0.5, r + 0.5) (the pixel (i, j) = (column, row) centre is at
  (i + 1/2, j + 1/2); same as :mod:`face3d.mesh.raster` and the test-bed renderer).
* Distances are in pixels (squared pixels for ``edt_squared``); ``inf`` where the
  mask has no True pixel at all.
* ``nearest[r, c] = (row, col)`` of a nearest True pixel (ties: the lower column in the
  row pass, then the lower row in the column pass), ``(-1, -1)`` when none exists.
* Gradients are with respect to (u, v), i.e. d/dcol and d/drow, in value units per pixel.

numpy + stdlib only.
"""
from __future__ import annotations

import numpy as np

__all__ = ["edt_squared", "edt_with_nearest", "edt", "sample_bilinear", "gradient", "fh_lower_envelope"]


def fh_lower_envelope(f: np.ndarray, return_arg: bool = False):
    """1D squared distance transform along the last axis of ``f`` (L, n), all lines at once.

    D[l, p] = min_q ((p - q)^2 + f[l, q]) with ``+inf`` entries of ``f`` ignored
    (Felzenszwalb-Huttenlocher 2012, Algorithm 1).  Lines without a finite entry give
    ``inf`` (and arg -1).  Returns D, or (D, arg) with ``arg[l, p]`` the minimising q.
    """
    f = np.asarray(f, dtype=np.float64)
    if f.ndim != 2:
        raise ValueError("fh_lower_envelope needs a 2D (lines, n) array")
    L, n = f.shape
    D = np.full((L, n), np.inf)
    arg = np.full((L, n), -1, dtype=np.int64)
    if L == 0 or n == 0:
        return (D, arg) if return_arg else D
    finite = np.isfinite(f)
    v = np.zeros((L, n), dtype=np.int64)          # parabola sites of the envelope
    z = np.empty((L, n + 1))                      # boundaries between envelope parabolas
    z[:, 0] = -np.inf
    z[:, 1:] = np.inf
    k = np.full(L, -1, dtype=np.int64)            # index of the last envelope parabola (-1: none)
    rows = np.arange(L)
    qq = np.arange(n, dtype=np.float64) ** 2
    for q in range(n):
        fin = finite[:, q]
        if not fin.any():
            continue
        start = fin & (k < 0)
        if start.any():
            v[start, 0] = q
            k[start] = 0
        act = np.flatnonzero(fin & ~start)
        if act.size == 0:
            continue
        hq = f[act, q] + qq[q]
        while True:
            kv = k[act]
            vk = v[act, kv]
            s = (hq - (f[act, vk] + qq[vk])) / (2.0 * (q - vk))
            pop = s <= z[act, kv]
            if not pop.any():
                break
            k[act[pop]] -= 1
        kv = k[act] + 1
        k[act] = kv
        v[act, kv] = q
        z[act, kv] = s
        z[act, kv + 1] = np.inf
    has = k >= 0
    if not has.any():
        return (D, arg) if return_arg else D
    lines = rows[has]
    kk = np.zeros(lines.size, dtype=np.int64)
    fl = f[lines]
    vl = v[lines]
    zl = z[lines]
    li = np.arange(lines.size)
    for p in range(n):
        while True:
            adv = zl[li, kk + 1] < p
            if not adv.any():
                break
            kk[adv] += 1
        site = vl[li, kk]
        D[lines, p] = (p - site) ** 2 + fl[li, site]
        arg[lines, p] = site
    return (D, arg) if return_arg else D


def edt_with_nearest(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Exact squared distance (px^2) to the nearest True pixel and that pixel's (row, col).

    ``mask`` (H, W) bool.  Returns ``(d2 (H, W) float64, nearest (H, W, 2) int64)``;
    True pixels have d2 = 0 and themselves as nearest; an all-False mask gives inf and -1.
    Felzenszwalb-Huttenlocher passes: columns, then rows (module docstring).
    """
    m = np.asarray(mask, dtype=bool)
    if m.ndim != 2:
        raise ValueError("mask must be 2D (H, W)")
    H, W = m.shape
    f = np.where(m, 0.0, np.inf)
    # columns: lines are the W columns, each of length H
    d_col, a_col = fh_lower_envelope(f.T, return_arg=True)          # (W, H)
    # rows: lines are the H rows of the column result, each of length W
    d2, a_row = fh_lower_envelope(np.ascontiguousarray(d_col.T), return_arg=True)   # (H, W)
    nearest = np.full((H, W, 2), -1, dtype=np.int64)
    ok = a_row >= 0
    if ok.any():
        r, c = np.nonzero(ok)
        cc = a_row[r, c]
        nearest[r, c, 0] = a_col[cc, r]
        nearest[r, c, 1] = cc
    return d2, nearest


def edt_squared(mask: np.ndarray) -> np.ndarray:
    """Exact squared Euclidean distance (px^2) from every pixel to the nearest True pixel."""
    m = np.asarray(mask, dtype=bool)
    if m.ndim != 2:
        raise ValueError("mask must be 2D (H, W)")
    f = np.where(m, 0.0, np.inf)
    d_col = fh_lower_envelope(f.T)
    return fh_lower_envelope(np.ascontiguousarray(d_col.T))


def edt(mask: np.ndarray) -> np.ndarray:
    """Euclidean distance (px) to the nearest True pixel: ``sqrt(edt_squared(mask))``."""
    return np.sqrt(edt_squared(mask))


def sample_bilinear(img: np.ndarray, uv: np.ndarray, *, fill: float | None = None,
                    return_grad: bool = False):
    """Bilinear interpolation of ``img`` (H, W) or (H, W, C) at continuous points ``uv`` (N, 2).

    Pixel-centre convention: the value of pixel ``[r, c]`` sits at (u, v) = (c + 0.5,
    r + 0.5) (DESIGN 3.1).  Points outside the centre grid take the edge value
    (clamped) when ``fill`` is None, else ``fill`` beyond the outer pixel *edges*
    ([0, W] x [0, H]); between the outermost centre and the image edge the edge value is
    used.  With ``return_grad`` also returns the exact derivative of the interpolant,
    ``(N, 2)`` (or (N, C, 2)) as (d/du, d/dv) per pixel (zero along a clamped axis).
    """
    a = np.asarray(img, dtype=np.float64)
    if a.ndim not in (2, 3):
        raise ValueError("img must be (H, W) or (H, W, C)")
    H, W = a.shape[:2]
    P = np.asarray(uv, dtype=np.float64).reshape(-1, 2)
    x = P[:, 0] - 0.5
    y = P[:, 1] - 0.5
    finite = np.isfinite(x) & np.isfinite(y)
    xs = np.where(finite, x, 0.0)
    ys = np.where(finite, y, 0.0)
    xc = np.clip(xs, 0.0, W - 1.0)
    yc = np.clip(ys, 0.0, H - 1.0)
    x0 = np.minimum(np.floor(xc).astype(np.int64), max(W - 2, 0))
    y0 = np.minimum(np.floor(yc).astype(np.int64), max(H - 2, 0))
    x1 = np.minimum(x0 + 1, W - 1)
    y1 = np.minimum(y0 + 1, H - 1)
    fx = xc - x0
    fy = yc - y0
    if a.ndim == 3:
        fx_ = fx[:, None]
        fy_ = fy[:, None]
    else:
        fx_, fy_ = fx, fy
    v00 = a[y0, x0]
    v01 = a[y0, x1]
    v10 = a[y1, x0]
    v11 = a[y1, x1]
    top = v00 + (v01 - v00) * fx_
    bot = v10 + (v11 - v10) * fx_
    val = top + (bot - top) * fy_
    out_mask = ~finite
    if fill is not None:
        out_mask = out_mask | (P[:, 0] < 0.0) | (P[:, 0] > W) | (P[:, 1] < 0.0) | (P[:, 1] > H)
    if out_mask.any():
        val = np.array(val, dtype=np.float64)
        val[out_mask] = np.nan if fill is None else float(fill)
    if not return_grad:
        return val
    inside_x = ((xs > 0.0) & (xs < W - 1.0)).astype(np.float64)
    inside_y = ((ys > 0.0) & (ys < H - 1.0)).astype(np.float64)
    if a.ndim == 3:
        inside_x = inside_x[:, None]
        inside_y = inside_y[:, None]
    du = ((v01 - v00) * (1.0 - fy_) + (v11 - v10) * fy_) * inside_x
    dv = (bot - top) * inside_y
    grad = np.stack([du, dv], axis=-1)
    if out_mask.any():
        grad[out_mask] = 0.0
    return val, grad


def gradient(img: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Central-difference gradient (d/du, d/dv) of a (H, W) image, one-sided at the borders.

    u runs along columns and v along rows (DESIGN 3.1), so this is
    ``(np.gradient(img, axis=1), np.gradient(img, axis=0))`` in value units per pixel.
    """
    a = np.asarray(img, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError("img must be 2D (H, W)")
    if a.shape[0] < 2 or a.shape[1] < 2:
        return np.zeros_like(a), np.zeros_like(a)
    return np.gradient(a, axis=1), np.gradient(a, axis=0)
