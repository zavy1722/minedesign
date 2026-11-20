"""Stdlib + numpy PNG reader/writer (D-23: pixels reach the engine as decoded arrays).

Reader: colour types 0 (grey), 2 (RGB), 3 (palette, 8-bit; with tRNS -> RGBA,
otherwise RGB), 4 (grey+alpha), 6 (RGBA); bit depths 8 and 16 (16-bit returns
uint16, big-endian samples decoded). Chunk CRCs are verified. Adam7 interlacing
and other bit depths raise NotImplementedError. Arrays are (H, W) or (H, W, C),
row 0 at the top, values unscaled (no gamma handling; sRGB is assumed by callers).
Performance: the Average/Paeth filters run a per-byte Python loop (~3.6 MB/s), so a
12 MP RGB all-Paeth image takes ~10 s (~20 s at 16 bit); filters 0-2 are numpy-vectorised.
Writer: uint8/uint16 grey/RGB/RGBA, filter type 0, zlib level 6.
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

import numpy as np

_SIG = b"\x89PNG\r\n\x1a\n"
_CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


def _chunks(buf: bytes):
    if buf[:8] != _SIG:
        raise ValueError("not a PNG file (bad signature)")
    p = 8
    while p + 12 <= len(buf):
        n, typ = struct.unpack(">I4s", buf[p:p + 8])
        data = buf[p + 8:p + 8 + n]
        if len(data) != n or p + 12 + n > len(buf):
            raise ValueError("truncated PNG chunk")
        crc = struct.unpack(">I", buf[p + 8 + n:p + 12 + n])[0]
        if zlib.crc32(typ + data) & 0xFFFFFFFF != crc:
            raise ValueError(f"PNG CRC mismatch in chunk {typ!r}")
        yield typ, data
        p += 12 + n
        if typ == b"IEND":
            return


def _unfilter(raw: bytes, h: int, stride: int, bpp: int) -> np.ndarray:
    out = np.zeros((h, stride), dtype=np.uint8)
    src = np.frombuffer(raw, dtype=np.uint8).reshape(h, stride + 1)
    prev = np.zeros(stride, dtype=np.uint8)
    for y in range(h):
        ft = int(src[y, 0])
        line = src[y, 1:]
        if ft == 0:
            cur = line.copy()
        elif ft == 1:  # Sub: running sum per byte lane (mod 256)
            lanes = line.reshape(-1, bpp)
            cur = np.cumsum(lanes, axis=0, dtype=np.uint8).reshape(-1)
        elif ft == 2:  # Up
            cur = line + prev  # uint8 wraparound
        elif ft == 3:  # Average (sequential dependency on left pixel)
            ba = bytearray(line.tobytes())
            pv = prev.tobytes()
            for i in range(stride):
                left = ba[i - bpp] if i >= bpp else 0
                ba[i] = (ba[i] + ((left + pv[i]) >> 1)) & 255
            cur = np.frombuffer(bytes(ba), dtype=np.uint8)
        elif ft == 4:  # Paeth
            ba = bytearray(line.tobytes())
            pv = prev.tobytes()
            for i in range(stride):
                a = ba[i - bpp] if i >= bpp else 0
                b = pv[i]
                c = pv[i - bpp] if i >= bpp else 0
                pa = abs(b - c)
                pb = abs(a - c)
                pc = abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                ba[i] = (ba[i] + pr) & 255
            cur = np.frombuffer(bytes(ba), dtype=np.uint8)
        else:
            raise ValueError(f"bad PNG filter type {ft}")
        out[y] = cur
        prev = out[y]
    return out


def read_png(path_or_bytes) -> np.ndarray:
    """Decode a PNG to an ndarray (H, W) or (H, W, C), uint8 or uint16."""
    if isinstance(path_or_bytes, (bytes, bytearray, memoryview)):
        buf = bytes(path_or_bytes)
    else:
        buf = Path(path_or_bytes).read_bytes()
    ihdr = None
    idat: list[bytes] = []
    plte = None
    trns = None
    for typ, data in _chunks(buf):
        if typ == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", data)
        elif typ == b"PLTE":
            plte = np.frombuffer(data, dtype=np.uint8).reshape(-1, 3)
        elif typ == b"tRNS":
            trns = np.frombuffer(data, dtype=np.uint8)
        elif typ == b"IDAT":
            idat.append(data)
    if ihdr is None:
        raise ValueError("PNG missing IHDR")
    w, h, depth, ctype, comp, filt, interlace = ihdr
    if comp != 0 or filt != 0:
        raise ValueError("unsupported PNG compression/filter method")
    if interlace:
        raise NotImplementedError("Adam7 interlaced PNG not supported; re-save non-interlaced")
    if ctype not in _CHANNELS:
        raise ValueError(f"bad PNG colour type {ctype}")
    if depth not in (8, 16) or (ctype == 3 and depth != 8):
        raise NotImplementedError(f"PNG bit depth {depth} (colour type {ctype}) not supported")
    nch = _CHANNELS[ctype]
    bps = depth // 8
    bpp = nch * bps
    stride = w * bpp
    raw = zlib.decompress(b"".join(idat))
    if len(raw) < h * (stride + 1):
        raise ValueError("PNG image data too short")
    rows = _unfilter(raw[:h * (stride + 1)], h, stride, bpp)
    if depth == 16:
        arr = rows.reshape(h, w * nch * 2).view(">u2").astype(np.uint16).reshape(h, w, nch)
    else:
        arr = rows.reshape(h, w, nch)
    if ctype == 3:
        if plte is None:
            raise ValueError("palette PNG missing PLTE")
        pal = np.zeros((256, 3), dtype=np.uint8)
        pal[:len(plte)] = plte
        idx = arr[..., 0]
        if trns is not None:
            alpha = np.full(256, 255, dtype=np.uint8)
            alpha[:len(trns)] = trns[:256]
            return np.concatenate([pal[idx], alpha[idx][..., None]], axis=-1)
        return pal[idx]
    if nch == 1:
        return arr[..., 0]
    return arr


def _chunk(typ: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + typ + data + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)


def write_png(path, arr: np.ndarray) -> None:
    """Write uint8/uint16 grey (H,W|H,W,1), RGB (H,W,3) or RGBA (H,W,4) PNG, filter 0, zlib level 6."""
    a = np.asarray(arr)
    if a.dtype not in (np.uint8, np.uint16):
        raise ValueError("write_png requires uint8 or uint16 arrays")
    if a.ndim == 2:
        a = a[..., None]
    if a.ndim != 3 or a.shape[2] not in (1, 3, 4):
        raise ValueError("write_png supports grey, RGB and RGBA arrays")
    h, w, nch = a.shape
    ctype = {1: 0, 3: 2, 4: 6}[nch]
    depth = 8 if a.dtype == np.uint8 else 16
    rows = a.astype(">u2" if depth == 16 else np.uint8, copy=False).reshape(h, -1).view(np.uint8)
    rows = rows.reshape(h, -1)
    raw = np.concatenate([np.zeros((h, 1), dtype=np.uint8), rows], axis=1).tobytes()
    out = _SIG + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, depth, ctype, 0, 0, 0))
    out += _chunk(b"IDAT", zlib.compress(raw, 6)) + _chunk(b"IEND", b"")
    Path(path).write_bytes(out)
