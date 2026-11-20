"""Pixel-array and pixel-coordinate operations (DESIGN 3.1 image conventions).

Conventions
-----------
* Arrays are (H, W[, C]), row 0 at the top. Continuous image coordinates ``uv`` have
  their origin at the top-left *corner*: the centre of pixel (i, j) (column i, row j)
  is (i + 0.5, j + 0.5). MediaPipe normalised coordinates map as u = x*W, v = y*H.
* The eight EXIF orientations are exact coordinate maps. ``orientation_point_map``
  maps stored-frame uv to displayed-frame uv and carries ``.inverse`` and
  ``.out_wh`` (displayed width, height). EXIF 6 displays the stored image rotated
  90 degrees clockwise: (u, v) -> (H - v, u).
* Resize: u' = u*W'/W (no +0.5 form). Horizontal flip: u' = W - u with labels
  permuted by the scheme's L/R permutation (flip_uv).
* HEIF ops come from ``face3d.io.heif.orientation_ops`` (clap, irot, imir); the
  crop window is rounded to whole pixels so array and point maps agree exactly.
* sRGB transfer functions: IEC 61966-2-1. ``to_gray`` uses Rec.709 luma weights
  (0.2126, 0.7152, 0.0722) applied to the sRGB-*encoded* values (not linearised).
"""
from __future__ import annotations

import math

import numpy as np

_O_ARRAY = {
    1: lambda a: a,
    2: lambda a: np.flip(a, axis=1),
    3: lambda a: np.flip(a, axis=(0, 1)),
    4: lambda a: np.flip(a, axis=0),
    5: lambda a: np.swapaxes(a, 0, 1),
    6: lambda a: np.rot90(a, k=-1),
    7: lambda a: np.flip(np.rot90(a, k=1), axis=1),
    8: lambda a: np.rot90(a, k=1),
}


class AffinePointMap:
    """uv' = A @ uv + b for (2,) or (N, 2) inputs; exact for the +-1 matrices used here."""

    def __init__(self, A, b, out_wh, in_wh=(0, 0)):
        self.in_wh = (int(in_wh[0]), int(in_wh[1]))
        self.A = np.asarray(A, dtype=np.float64)
        self.b = np.asarray(b, dtype=np.float64)
        self.out_wh = (int(out_wh[0]), int(out_wh[1]))

    def __call__(self, uv):
        x = np.asarray(uv, dtype=np.float64)
        return x @ self.A.T + self.b

    @property
    def inverse(self) -> "AffinePointMap":
        Ai = np.linalg.inv(self.A)
        Ai = np.where(np.abs(Ai - np.round(Ai)) < 1e-12, np.round(Ai), Ai)
        inv = AffinePointMap(Ai, -Ai @ self.b, self.in_wh, self.out_wh)
        return inv

    def then(self, other: "AffinePointMap") -> "AffinePointMap":
        return AffinePointMap(other.A @ self.A, other.A @ self.b + other.b, other.out_wh, self.in_wh)


def _check_o(o: int) -> int:
    o = int(o)
    if o not in _O_ARRAY:
        raise ValueError("EXIF orientation must be 1..8")
    return o


def apply_orientation(img: np.ndarray, o: int) -> np.ndarray:
    """Return the displayed image for EXIF orientation ``o`` (1..8), as a contiguous copy."""
    return np.ascontiguousarray(_O_ARRAY[_check_o(o)](np.asarray(img)))


def orientation_point_map(o: int, W: int, H: int) -> AffinePointMap:
    """Stored-frame uv -> displayed-frame uv for EXIF orientation ``o`` of a W x H stored image."""
    o = _check_o(o)
    M = {
        1: ([[1, 0], [0, 1]], [0, 0], (W, H)),
        2: ([[-1, 0], [0, 1]], [W, 0], (W, H)),
        3: ([[-1, 0], [0, -1]], [W, H], (W, H)),
        4: ([[1, 0], [0, -1]], [0, H], (W, H)),
        5: ([[0, 1], [1, 0]], [0, 0], (H, W)),
        6: ([[0, -1], [1, 0]], [H, 0], (H, W)),
        7: ([[0, -1], [-1, 0]], [H, W], (H, W)),
        8: ([[0, 1], [-1, 0]], [0, W], (H, W)),
    }[o]
    return AffinePointMap(*M, in_wh=(W, H))


def _heif_steps(ops, W: int, H: int):
    """Yield (op, params, in_wh, out_wh) with crop windows rounded to whole pixels."""
    w, h = int(W), int(H)
    for op in ops:
        kind = op[0]
        if kind == "crop":
            c = op[1]
            if not c["width_d"] or not c["height_d"]:
                raise ValueError("clap has a zero denominator in width/height")
            cw = c["width_n"] / c["width_d"]
            ch = c["height_n"] / c["height_d"]
            ho = c["horiz_off_n"] / c["horiz_off_d"] if c["horiz_off_d"] else 0.0
            vo = c["vert_off_n"] / c["vert_off_d"] if c["vert_off_d"] else 0.0
            # Documented rounding (matches libheif): floor for the left/top edge,
            # floor(x + 0.5) (half up) for the window size.
            x0 = math.floor(w / 2 + ho - cw / 2)
            y0 = math.floor(h / 2 + vo - ch / 2)
            nw, nh = math.floor(cw + 0.5), math.floor(ch + 0.5)
            x0 = max(0, min(x0, w - 1))
            y0 = max(0, min(y0, h - 1))
            nw = max(1, min(nw, w - x0))
            nh = max(1, min(nh, h - y0))
            yield kind, (x0, y0), (w, h), (nw, nh)
            w, h = nw, nh
        elif kind == "rotate_ccw":
            deg = int(op[1]) % 360
            if deg not in (0, 90, 180, 270):
                raise ValueError("rotate_ccw must be a multiple of 90")
            nw, nh = (h, w) if deg in (90, 270) else (w, h)
            yield kind, deg, (w, h), (nw, nh)
            w, h = nw, nh
        elif kind == "mirror":
            yield kind, int(op[1]) & 1, (w, h), (w, h)
        else:
            raise ValueError(f"unknown HEIF op {kind!r}")


def apply_heif_ops(img: np.ndarray, ops) -> np.ndarray:
    """Apply ``heif.orientation_ops`` output to an array (clap, irot, imir order)."""
    a = np.asarray(img)
    h, w = a.shape[:2]
    for kind, p, _in, out in _heif_steps(ops, w, h):
        if kind == "crop":
            x0, y0 = p
            a = a[y0:y0 + out[1], x0:x0 + out[0]]
        elif kind == "rotate_ccw":
            a = np.rot90(a, k=p // 90)
        else:
            a = np.flip(a, axis=p)   # imir axis 0: top<->bottom, 1: left<->right (ISO 23008-12)
    return np.ascontiguousarray(a)


def heif_point_map(ops, W: int, H: int) -> AffinePointMap:
    """Stored-frame uv -> displayed-frame uv for a HEIF op list (corner-origin coordinates)."""
    m = AffinePointMap(np.eye(2), [0, 0], (W, H), (W, H))
    for kind, p, (w, h), out in _heif_steps(ops, W, H):
        if kind == "crop":
            s = AffinePointMap(np.eye(2), [-p[0], -p[1]], out)
        elif kind == "rotate_ccw":
            s = {0: AffinePointMap(np.eye(2), [0, 0], out),
                 90: AffinePointMap([[0, 1], [-1, 0]], [0, w], out),
                 180: AffinePointMap([[-1, 0], [0, -1]], [w, h], out),
                 270: AffinePointMap([[0, -1], [1, 0]], [h, 0], out)}[p]
        elif p == 1:   # imir axis 1: left <-> right, u' = w - u
            s = AffinePointMap([[-1, 0], [0, 1]], [w, 0], out)
        else:          # imir axis 0: top <-> bottom, v' = h - v
            s = AffinePointMap([[1, 0], [0, -1]], [0, h], out)
        m = m.then(s)
    return m


def flip_horizontal(img: np.ndarray) -> np.ndarray:
    """Mirror an image left <-> right (contiguous copy)."""
    return np.ascontiguousarray(np.flip(np.asarray(img), axis=1))


def flip_uv(uv, W: float, perm) -> np.ndarray:
    """Landmarks of a horizontally flipped image: out[perm[i]] = (W - u_i, v_i).

    ``perm`` is the scheme's L/R label permutation; NaN rows stay NaN.
    """
    uv = np.asarray(uv, dtype=np.float64)
    perm = np.asarray(perm, dtype=np.int64)
    if uv.shape[0] != perm.shape[0]:
        raise ValueError("perm length must match number of landmarks")
    if not np.array_equal(np.sort(perm), np.arange(perm.shape[0])):
        raise ValueError("perm must be a permutation of range(N)")
    out = np.empty_like(uv)
    out[perm] = np.stack([W - uv[:, 0], uv[:, 1]], axis=1)
    return out


def resize_uv(uv, W: float, H: float, W2: float, H2: float) -> np.ndarray:
    """Corner-origin resize map: (u, v) -> (u*W2/W, v*H2/H)."""
    uv = np.asarray(uv, dtype=np.float64)
    return uv * np.array([W2 / W, H2 / H])


def srgb_to_linear(x) -> np.ndarray:
    """IEC 61966-2-1 decode: sRGB-encoded [0,1] -> linear light."""
    x = np.asarray(x, dtype=np.float64)
    return np.where(x <= 0.04045, x / 12.92, np.power(np.maximum(x + 0.055, 0.0) / 1.055, 2.4))


def linear_to_srgb(x) -> np.ndarray:
    """IEC 61966-2-1 encode: linear light [0,1] -> sRGB-encoded."""
    x = np.asarray(x, dtype=np.float64)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(np.maximum(x, 0.0), 1 / 2.4) - 0.055)


_REC709 = np.array([0.2126, 0.7152, 0.0722])


def to_gray(img) -> np.ndarray:
    """Rec.709 luma of an sRGB-encoded float image in [0, 1] (alpha ignored); 2-D input is returned as-is."""
    a = np.asarray(img, dtype=np.float64)
    if a.ndim == 2:
        return a
    if a.shape[2] in (1, 2):   # grey or grey+alpha
        return a[..., 0]
    return a[..., :3] @ _REC709
