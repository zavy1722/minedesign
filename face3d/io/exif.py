"""Dependency-free EXIF reader for the fields that matter for camera solving.

Reads JPEG (APP1 'Exif') and bare TIFF headers. Returns focal length (mm),
35 mm-equivalent focal length, pixel dimensions, orientation and make/model.
Only the standard library is used so this also runs inside Blender.

WP-05 additions (DESIGN 3.2 project.json "exif" block, CAM-5 focal groups):
capture time, software, digital zoom, lens make/spec, subject distance,
CustomRendered, artist/copyright, and presence flags for GPS / MakerNote / XMP.
GPS and MakerNote contents are deliberately *not* parsed (privacy; eth digest).
Units: focal lengths and lens spec in mm, subject_distance_m in metres.
"""
from __future__ import annotations

import math
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
    0x9003: "datetime_original", 0x0131: "software", 0xA404: "digital_zoom",
    0xA433: "lens_make", 0xA432: "lens_spec", 0x9206: "subject_distance",
    0xA401: "custom_rendered", 0x013B: "artist", 0x8298: "copyright",
    0x8825: "gps_ifd", 0x927C: "makernote",
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
    datetime_original: str | None = None
    software: str | None = None
    digital_zoom_ratio: float | None = None
    lens_make: str | None = None
    lens_specification: tuple | None = None  # (min_f_mm, max_f_mm, min_fnum, max_fnum)
    subject_distance_m: float | None = None
    custom_rendered: int | None = None       # 0 normal, 1 custom (e.g. portrait/HDR processing)
    artist: str | None = None
    copyright: str | None = None
    has_gps: bool = False                    # GPS IFD present; never parsed
    has_makernote: bool = False
    has_xmp: bool = False

    @property
    def is_front_camera(self) -> bool:
        """True when the lens model names a front camera ('front' in lens_model, case-insensitive)."""
        return bool(self.lens_model) and "front" in self.lens_model.lower()

    def focal_group_key(self, width: int, height: int, still: bool = True) -> str:
        """Focal-group key 'Make|Model|LensModel|f35|W|H|still|video' (DESIGN 4.x CAM-5).

        Missing fields render as empty strings; f35 is rendered via ``%g``.
        """
        f35 = "" if self.focal_35mm is None else f"{self.focal_35mm:g}"
        return "|".join([self.make or "", self.model or "", self.lens_model or "", f35,
                         str(int(width)), str(int(height)), "still" if still else "video"])

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

    raw_rat: dict = {}

    def value(typ: int, count: int, raw: bytes, off_field: int, tag_raw=None):
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
            vals = tuple(nums[i] / nums[i + 1] if nums[i + 1] else None for i in range(0, len(nums), 2))
            if tag_raw is not None and count == 1:
                raw_rat[tag_raw] = (nums[0], nums[1])
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
            if name in ("gps_ifd", "makernote"):  # presence only, never parsed
                out.setdefault(name, True)
                continue
            v = value(typ, count, raw, off_field, tag)
            if name == "exif_ifd" and isinstance(v, int):
                walk(v, depth + 1)
            elif v is not None:
                out.setdefault(name, v)

    walk(struct.unpack(e + "I", buf[4:8])[0])
    out["_raw_rat"] = raw_rat
    return out


def _jpeg_app1_segments(data: bytes) -> list[bytes]:
    """All APP1 segment payloads (after the length field) before start-of-scan."""
    out: list[bytes] = []
    if data[:2] != b"\xff\xd8":
        return out
    i = 2
    n = len(data)
    while i + 4 <= n:
        if data[i] != 0xFF:
            break
        marker = data[i + 1]
        if marker == 0xFF:  # fill byte
            i += 1
            continue
        if marker in (0xD9, 0xDA):  # EOI / start of scan: no more metadata
            break
        if marker == 0x01 or 0xD0 <= marker <= 0xD8:  # standalone markers
            i += 2
            continue
        seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
        if seg_len < 2:
            break
        if marker == 0xE1:
            out.append(data[i + 4:i + 2 + seg_len])
        i += 2 + seg_len
    return out


def _jpeg_app1(data: bytes) -> bytes | None:
    for seg in _jpeg_app1_segments(data):
        if seg[:6] == b"Exif\0\0":
            return seg[6:]
    return None


_XMP_ID = b"http://ns.adobe.com/xap/1.0/"


def _info_from_tiff(tiff: bytes) -> ExifInfo:
    try:
        t = _parse_tiff(tiff)
    except (ValueError, struct.error):
        return ExifInfo()
    f35 = t.get("focal_35mm")
    spec = t.get("lens_spec")
    rr = t.get("_raw_rat", {})
    sd = t.get("subject_distance")
    dz = t.get("digital_zoom")
    # EXIF sentinels: SubjectDistance 0 = unknown, 0xFFFFFFFF = infinity;
    # DigitalZoomRatio 0 = digital zoom not used; zero denominator = invalid.
    if 0x9206 in rr:
        n, d = rr[0x9206]
        sd = None if (d == 0 or n == 0) else (math.inf if n == 0xFFFFFFFF else sd)
    if 0xA404 in rr:
        n, d = rr[0xA404]
        dz = None if d == 0 else (1.0 if n == 0 else dz)
    cr = t.get("custom_rendered")
    return ExifInfo(
        focal_length_mm=float(t["focal_length"]) if t.get("focal_length") else None,
        focal_35mm=float(f35) if f35 else None,
        width=int(t["pixel_x"]) if t.get("pixel_x") else None,
        height=int(t["pixel_y"]) if t.get("pixel_y") else None,
        orientation=int(t.get("orientation", 1) or 1),
        make=t.get("make"), model=t.get("model"), lens_model=t.get("lens_model"),
        focal_plane_x_res=float(t["fp_x_res"]) if t.get("fp_x_res") else None,
        focal_plane_res_unit=int(t["fp_res_unit"]) if t.get("fp_res_unit") else None,
        datetime_original=t.get("datetime_original") or None,
        software=t.get("software") or None,
        digital_zoom_ratio=float(dz) if isinstance(dz, (int, float)) else None,
        lens_make=t.get("lens_make") or None,
        lens_specification=tuple(float(x) for x in spec) if isinstance(spec, tuple) and len(spec) == 4 and None not in spec else None,
        subject_distance_m=float(sd) if isinstance(sd, (int, float)) else None,
        custom_rendered=int(cr) if isinstance(cr, int) else None,
        artist=t.get("artist") or None,
        copyright=t.get("copyright") or None,
        has_gps="gps_ifd" in t,
        has_makernote="makernote" in t,
    )


def _tiff_from_payload(data: bytes) -> bytes | None:
    """Locate the TIFF header in a bare TIFF, 'Exif\\0\\0'-prefixed, or HEIF Exif item payload."""
    if data[:2] in (b"II", b"MM"):
        return data
    if data[:6] == b"Exif\0\0":
        return data[6:]
    if len(data) >= 8:
        off = struct.unpack(">I", data[:4])[0]  # HEIF: offset from end of this field to TIFF header
        rest = data[4 + off:] if 4 + off <= len(data) else b""
        if rest[:6] == b"Exif\0\0":
            rest = rest[6:]
        if rest[:2] in (b"II", b"MM"):
            return rest
    return None


def read_exif_bytes(data: bytes) -> ExifInfo:
    """Parse an EXIF TIFF payload.

    Accepts a bare TIFF, an 'Exif\\0\\0'-prefixed payload (JPEG APP1) or a HEIF
    Exif item (4-byte big-endian offset to the TIFF header, optionally followed
    by 'Exif\\0\\0'). Returns an empty ExifInfo when nothing parses.
    """
    tiff = _tiff_from_payload(bytes(data))
    return _info_from_tiff(tiff) if tiff is not None else ExifInfo()


def read_exif(path: str | Path) -> ExifInfo:
    data = Path(path).read_bytes()
    if data[:2] == b"\xff\xd8":
        segs = _jpeg_app1_segments(data)
        has_xmp = any(g.startswith(_XMP_ID) for g in segs)
        tiff = next((g[6:] for g in segs if g[:6] == b"Exif\0\0"), None)
        info = _info_from_tiff(tiff) if tiff is not None else ExifInfo()
        info.has_xmp = has_xmp
        return info
    if data[:2] in (b"II", b"MM"):
        return _info_from_tiff(data)
    return ExifInfo()
