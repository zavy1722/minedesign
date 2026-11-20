"""Dependency-free EXIF reader for the fields that matter for camera solving.

Reads JPEG (APP1 'Exif') and bare TIFF headers. Returns focal length (mm),
35 mm-equivalent focal length, pixel dimensions, orientation and make/model.
Only the standard library is used so this also runs inside Blender.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

_TAGS = {
    0x010F: "make", 0x0110: "model", 0x0112: "orientation",
    0x8769: "exif_ifd",
    0x920A: "focal_length", 0xA405: "focal_35mm",
    0xA002: "pixel_x", 0xA003: "pixel_y",
    0xA20E: "fp_x_res", 0xA20F: "fp_y_res", 0xA210: "fp_res_unit",
    0xA434: "lens_model",
}
_TYPE_SIZES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 9: 4, 10: 8, 11: 4, 12: 8}


@dataclass
class ExifInfo:
    focal_length_mm: float | None = None
    focal_35mm: float | None = None
    width: int | None = None
    height: int | None = None
    orientation: int = 1
    make: str | None = None
    model: str | None = None
    lens_model: str | None = None
    focal_plane_x_res: float | None = None   # pixels per unit on the sensor
    focal_plane_res_unit: int | None = None  # 2 = inch, 3 = cm, 4 = mm (TIFF spec)

    def focal_px(self, width: int, height: int) -> float | None:
        """Best available pixel focal length for an image of the given (oriented) size."""
        import math
        if self.focal_35mm:
            return self.focal_35mm * math.hypot(width, height) / math.hypot(36.0, 24.0)
        if self.focal_length_mm and self.focal_plane_x_res and self.focal_plane_res_unit in (2, 3, 4):
            unit_mm = {2: 25.4, 3: 10.0, 4: 1.0}[self.focal_plane_res_unit]
            px_per_mm = self.focal_plane_x_res / unit_mm
            # Focal-plane resolution refers to the sensor's native (unrotated) width.
            native_w = self.width or width
            return self.focal_length_mm * px_per_mm * (max(width, height) / max(native_w, 1)) \
                if native_w else None
        return None


def _parse_tiff(buf: bytes) -> dict:
    if buf[:2] == b"II":
        e = "<"
    elif buf[:2] == b"MM":
        e = ">"
    else:
        raise ValueError("not a TIFF header")
    if struct.unpack(e + "H", buf[2:4])[0] != 42:
        raise ValueError("bad TIFF magic")
    out: dict = {}

    def value(typ: int, count: int, raw: bytes, off_field: int):
        size = _TYPE_SIZES.get(typ, 1) * count
        data = raw if size <= 4 else buf[off_field:off_field + size]
        if typ == 2:
            return data[:count].split(b"\0", 1)[0].decode("utf-8", "replace").strip()
        if typ == 3:
            vals = struct.unpack(e + "H" * count, data[:2 * count])
        elif typ == 4:
            vals = struct.unpack(e + "I" * count, data[:4 * count])
        elif typ in (5, 10):
            fmt = "I" if typ == 5 else "i"
            nums = struct.unpack(e + fmt * 2 * count, data[:8 * count])
            vals = tuple(nums[i] / nums[i + 1] if nums[i + 1] else 0.0 for i in range(0, len(nums), 2))
        elif typ == 11:
            vals = struct.unpack(e + "f" * count, data[:4 * count])
        elif typ == 12:
            vals = struct.unpack(e + "d" * count, data[:8 * count])
        elif typ == 9:
            vals = struct.unpack(e + "i" * count, data[:4 * count])
        else:
            return None
        return vals[0] if count == 1 else vals

    def walk(offset: int, depth: int = 0):
        if depth > 4 or offset + 2 > len(buf):
            return
        n = struct.unpack(e + "H", buf[offset:offset + 2])[0]
        for i in range(n):
            p = offset + 2 + 12 * i
            if p + 12 > len(buf):
                return
            tag, typ, count = struct.unpack(e + "HHI", buf[p:p + 8])
            raw = buf[p + 8:p + 12]
            off_field = struct.unpack(e + "I", raw)[0]
            name = _TAGS.get(tag)
            if name is None:
                continue
            v = value(typ, count, raw, off_field)
            if name == "exif_ifd" and isinstance(v, int):
                walk(v, depth + 1)
            elif v is not None:
                out.setdefault(name, v)

    walk(struct.unpack(e + "I", buf[4:8])[0])
    return out


def _jpeg_app1(data: bytes) -> bytes | None:
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            return None
        marker = data[i + 1]
        if marker in (0xD9, 0xDA):  # EOI / start of scan: no more metadata
            return None
        seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
        seg = data[i + 4:i + 2 + seg_len]
        if marker == 0xE1 and seg[:6] == b"Exif\0\0":
            return seg[6:]
        i += 2 + seg_len
    return None


def read_exif(path: str | Path) -> ExifInfo:
    data = Path(path).read_bytes()
    tiff = _jpeg_app1(data) if data[:2] == b"\xff\xd8" else (data if data[:2] in (b"II", b"MM") else None)
    if tiff is None:
        return ExifInfo()
    try:
        t = _parse_tiff(tiff)
    except (ValueError, struct.error):
        return ExifInfo()
    f35 = t.get("focal_35mm")
    return ExifInfo(
        focal_length_mm=float(t["focal_length"]) if t.get("focal_length") else None,
        focal_35mm=float(f35) if f35 else None,
        width=int(t["pixel_x"]) if t.get("pixel_x") else None,
        height=int(t["pixel_y"]) if t.get("pixel_y") else None,
        orientation=int(t.get("orientation", 1) or 1),
        make=t.get("make"), model=t.get("model"), lens_model=t.get("lens_model"),
        focal_plane_x_res=float(t["fp_x_res"]) if t.get("fp_x_res") else None,
        focal_plane_res_unit=int(t["fp_res_unit"]) if t.get("fp_res_unit") else None,
    )
