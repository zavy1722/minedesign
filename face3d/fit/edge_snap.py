"""Viterbi edge snap: the zero-download contour source (DESIGN D-13, 4.16 "Edge snap"; WBS WP-17).

A coarse polyline (>= 5 user clicks, or the detector's oval points) is snapped to the
strongest coherent image edge along its normals: the polyline is resampled to M stations
every ``spacing_px``, each station may move by an integer offset k in [-L, L] along its
normal (L = ceil(0.03 IOD_px)), and the offsets minimise

    E(k) = sum_j -g_j(k_j) + lam sum_j |k_j - k_{j-1}|,

g = gradient magnitude (Sobel) of the image after a Gaussian blur of ``smooth_sigma``
(1 px), sampled bilinearly at station + k normal; lam = ``lam_factor`` (0.2) x median(g)
over the band.  The chain is solved exactly by Viterbi dynamic programming, vectorised as a
(2L+1) x (2L+1) transition per station, O(M L^2).  A closed curve is broken at the station
with the highest band maximum of g and solved as an open chain starting there.  Ties go
to the smallest offset index (``argmin`` order), so the result is deterministic.

Uncertainty (DESIGN 4.16): sigma_g = 1.4826 MAD(g over the band) (robust noise of the
unary), and at the optimum sigma_snap,j = sqrt(sigma_g^2 / max(-g_j''(k*), 1e-6)) with
g'' the second difference of g_j over k; sigma_n = max(1 px, sigma_snap).  The returned
points carry a parabolic sub-pixel refinement of k* (the vertex of the parabola through
g_j(k* - 1), g_j(k*), g_j(k* + 1), clipped to +-0.5; *face-segmentation-contours*
"snap to the gradient maximum ... with parabolic sub-pixel refinement").

Conventions (DESIGN 3.1): ``gray`` is (H, W) float indexed [row, col]; points are
(u, v) px with the pixel [r, c] centred at (c + 0.5, r + 0.5).  Station normals are the unit
central-difference tangent t rotated in the (u, v) plane, n = (t_v, -t_u), and flipped as a
whole to point away from ``outward_ref_point`` when one is given.  Offsets are in px along n.

numpy + stdlib only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ..core.config import Default, register_defaults
from .distance_transform import sample_bilinear

__all__ = ["SnapResult", "edge_snap", "resample_polyline", "gaussian_blur", "sobel_magnitude", "EDGE_SNAP"]

_BRAIN = "\U0001F9E0"
_NEW = "\U0001F195"

EDGE_SNAP = register_defaults("edge_snap", {
    "band_iod_frac": Default(0.03, _BRAIN, "DESIGN 4.16 'Edge snap': L = ceil(0.03 IOD_px)", "IOD", (1e-6, 1.0)),
    "lam_factor": Default(0.2, _BRAIN, "DESIGN 4.16 'Edge snap': lam = 0.2 median g", "", (0.0, 100.0)),
    "smooth_sigma_px": Default(1.0, _BRAIN, "DESIGN 4.16 'Edge snap': gradient after a 1 px Gaussian", "px",
                               (0.0, 100.0)),
    "spacing_px": Default(2.0, _NEW, "WBS WP-17: stations every 2 px", "px", (1e-3, 1000.0)),
    "mad_scale": Default(1.4826, _BRAIN, "DESIGN 4.16: sigma_g = 1.4826 MAD (normal-consistent MAD)", "",
                         (0.0, 10.0)),
    "curv_eps": Default(1e-6, _NEW, "DESIGN 4.16: max(-g'', eps) with eps = 1e-6", "", (0.0, 1.0)),
    "sigma_min_px": Default(1.0, _BRAIN, "DESIGN 4.16: sigma_n = max(1 px, sigma_snap)", "px", (0.0, 100.0)),
})


@dataclass
class SnapResult:
    """Snapped curve (DESIGN 4.16).

    points (M, 2) px; normals (M, 2) unit station normals; sigma_n_px (M,);
    offsets (M,) px along the normals (sub-pixel refined); cost = E(k*) of the integer chain.
    """

    points: np.ndarray
    normals: np.ndarray
    sigma_n_px: np.ndarray
    offsets: np.ndarray
    cost: float


def resample_polyline(points: np.ndarray, spacing_px: float, closed: bool = False) -> np.ndarray:
    """Points every ``spacing_px`` of arc length (the last point kept for an open line; a closed
    line is resampled around the full loop with uniform spacing)."""
    P = np.asarray(points, float).reshape(-1, 2)
    if len(P) < 2:
        raise ValueError("a polyline needs at least two points")
    Q = np.vstack([P, P[:1]]) if closed else P
    seg = np.linalg.norm(np.diff(Q, axis=0), axis=1)
    s = np.r_[0.0, np.cumsum(seg)]
    total = float(s[-1])
    if not total > 0:
        raise ValueError("degenerate polyline")
    if closed:
        n = max(3, int(math.ceil(total / float(spacing_px))))
        st = np.arange(n) * (total / n)
    else:
        n = max(2, int(math.ceil(total / float(spacing_px))) + 1)
        st = np.linspace(0.0, total, n)
    keep = np.r_[True, seg > 0]
    s_u, Q_u = s[keep], Q[keep]
    return np.column_stack([np.interp(st, s_u, Q_u[:, 0]), np.interp(st, s_u, Q_u[:, 1])])


def _conv1d(a: np.ndarray, k: np.ndarray, axis: int) -> np.ndarray:
    """'same' correlation with a symmetric/odd 1D kernel along ``axis``, edge-replicated borders."""
    r = len(k) // 2
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r, r)
    p = np.pad(a, pad, mode="edge")
    out = np.zeros_like(a)
    n = a.shape[axis]
    for i, w in enumerate(k):
        if w == 0.0:
            continue
        sl = [slice(None)] * a.ndim
        sl[axis] = slice(i, i + n)
        out += w * p[tuple(sl)]
    return out


def gaussian_blur(img: np.ndarray, sigma_px: float) -> np.ndarray:
    """Separable Gaussian blur (radius ceil(3 sigma), edge replication); sigma <= 0 returns a copy."""
    a = np.asarray(img, float)
    if not sigma_px > 0:
        return a.copy()
    r = max(1, int(math.ceil(3.0 * float(sigma_px))))
    x = np.arange(-r, r + 1, dtype=float)
    k = np.exp(-0.5 * (x / float(sigma_px)) ** 2)
    k /= k.sum()
    return _conv1d(_conv1d(a, k, 0), k, 1)


def sobel_magnitude(img: np.ndarray) -> np.ndarray:
    """|grad| from the 3 x 3 Sobel operator normalised by 1/8 (value units per pixel)."""
    a = np.asarray(img, float)
    smooth = np.array([1.0, 2.0, 1.0]) / 4.0
    diff = np.array([-1.0, 0.0, 1.0]) / 2.0
    gx = _conv1d(_conv1d(a, smooth, 0), diff, 1)
    gy = _conv1d(_conv1d(a, diff, 0), smooth, 1)
    return np.hypot(gx, gy)


def _normals(P: np.ndarray, closed: bool) -> np.ndarray:
    if closed:
        T = np.roll(P, -1, axis=0) - np.roll(P, 1, axis=0)
    else:
        T = np.empty_like(P)
        T[1:-1] = P[2:] - P[:-2]
        T[0] = P[1] - P[0]
        T[-1] = P[-1] - P[-2]
    ln = np.linalg.norm(T, axis=1, keepdims=True)
    T = T / np.where(ln > 0, ln, 1.0)
    return np.column_stack([T[:, 1], -T[:, 0]])


def _viterbi(G: np.ndarray, lam: float) -> tuple[np.ndarray, float]:
    """Exact minimiser of sum -G[j, k_j] + lam |k_j - k_{j-1}| over an open chain."""
    M, S = G.shape
    k = np.arange(S)
    trans = lam * np.abs(k[:, None] - k[None, :]).astype(float)      # [prev, cur]
    cost = -G[0].copy()
    back = np.zeros((M, S), np.int64)
    for j in range(1, M):
        tot = cost[:, None] + trans
        back[j] = np.argmin(tot, axis=0)
        cost = tot[back[j], k] - G[j]
    path = np.zeros(M, np.int64)
    path[-1] = int(np.argmin(cost))
    best = float(cost[path[-1]])
    for j in range(M - 1, 0, -1):
        path[j - 1] = back[j, path[j]]
    return path, best


def edge_snap(gray: np.ndarray, polyline: np.ndarray, iod_px: float, closed: bool = False, L: int | None = None,
              lam_factor: float | None = None, smooth_sigma: float | None = None, spacing_px: float | None = None,
              *, outward_ref_point: np.ndarray | None = None, subpixel: bool = True) -> SnapResult:
    """Snap a coarse polyline to the image edge by Viterbi (module docstring; DESIGN 4.16).

    gray : (H, W) float image (any linear scale; sigma_g scales with it).
    polyline : (K, 2) px, ordered.  iod_px : inter-ocular distance in px (band size).
    L : band half-width in px (default ceil(0.03 iod_px)).
    outward_ref_point : optional point inside the object; normals are oriented away from
        it (length-weighted majority, as :meth:`face3d.fit.contour.ContourObs.from_polyline`).
    """
    img = np.asarray(gray, float)
    if img.ndim != 2:
        raise ValueError("gray must be (H, W)")
    lamf = float(EDGE_SNAP["lam_factor"].value if lam_factor is None else lam_factor)
    sig = float(EDGE_SNAP["smooth_sigma_px"].value if smooth_sigma is None else smooth_sigma)
    sp = float(EDGE_SNAP["spacing_px"].value if spacing_px is None else spacing_px)
    Lb = int(math.ceil(float(EDGE_SNAP["band_iod_frac"].value) * float(iod_px))) if L is None else int(L)
    Lb = max(Lb, 1)
    P = resample_polyline(polyline, sp, closed)
    Nrm = _normals(P, closed)
    if outward_ref_point is not None:
        ref = np.asarray(outward_ref_point, float).reshape(2)
        if np.sum(np.sum(Nrm * (P - ref), axis=1)) < 0:
            Nrm = -Nrm
    gmag = sobel_magnitude(gaussian_blur(img, sig))
    ks = np.arange(-Lb, Lb + 1, dtype=float)
    pts = P[:, None, :] + ks[None, :, None] * Nrm[:, None, :]          # (M, S, 2)
    G = sample_bilinear(gmag, pts.reshape(-1, 2)).reshape(len(P), len(ks))
    med = float(np.median(G))
    lam = lamf * med
    M = len(P)
    if closed:
        j0 = int(np.argmax(G.max(axis=1)))
        order = np.r_[np.arange(j0, M), np.arange(0, j0)]
    else:
        order = np.arange(M)
    path_o, cost = _viterbi(G[order], lam)
    path = np.empty(M, np.int64)
    path[order] = path_o
    kstar = path.astype(float) - Lb
    # sigma from the unary curvature at the optimum (DESIGN 4.16)
    mad = float(np.median(np.abs(G - np.median(G))))
    sigma_g = float(EDGE_SNAP["mad_scale"].value) * mad
    S = len(ks)
    jm = np.clip(path, 1, S - 2)
    rows = np.arange(M)
    g0, gm, gp = G[rows, jm], G[rows, jm - 1], G[rows, jm + 1]
    d2 = gp - 2.0 * g0 + gm
    eps = float(EDGE_SNAP["curv_eps"].value)
    sigma_snap = np.sqrt(sigma_g ** 2 / np.maximum(-d2, eps))
    sigma_n = np.maximum(float(EDGE_SNAP["sigma_min_px"].value), sigma_snap)
    off = kstar.copy()
    if subpixel:
        interior = (path >= 1) & (path <= S - 2) & (d2 < 0)
        delta = np.zeros(M)
        delta[interior] = 0.5 * (gm[interior] - gp[interior]) / d2[interior]
        off = off + np.clip(delta, -0.5, 0.5)
    points = P + off[:, None] * Nrm
    return SnapResult(points=points, normals=Nrm, sigma_n_px=sigma_n, offsets=off, cost=float(cost))
