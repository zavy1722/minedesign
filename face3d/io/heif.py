"""Minimal ISOBMFF/HEIF metadata parser (no pixel decoding).

Extracts what the engine needs from a HEIC/HEIF/AVIF container (DESIGN 2.5, 3.1,
D-23): primary-item size (``ispe``), the geometric transforms ``clap``/``irot``/
``imir`` and the Exif item payload (located through ``iloc`` extents).

Conventions
-----------
* ``irot`` is an anti-clockwise rotation in degrees (0/90/180/270), ``angle = 90 * (b & 3)``
  (ISO/IEC 23008-12).
* ``imir_axis``: ``b & 1``; axis 0 swaps top and bottom (v' = h - v),
  axis 1 swaps left and right (u' = w - u) (ISO/IEC 23008-12 6.5.12; = libheif).
* ``clap`` rationals are stored as numerator/denominator pairs; offsets are signed
  and measure the crop-centre displacement from the image centre, in pixels.
* HEIF transform order is clap, then irot, then imir. **When any HEIF transform
  property is present the EXIF Orientation tag is ignored** (smartphone-camera
  pipeline note, DESIGN 3.1); EXIF Orientation is *always* ignored for HEIF/AVIF
  containers (no fallback), as in libheif.
Only construction_method 0 (file offsets) items are located; others are skipped.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path


@dataclass
class HeifInfo:
    brand: str | None = None
    primary_item_id: int | None = None
    width: int | None = None          # ispe of the primary item (stored, before transforms)
    height: int | None = None
    irot: int = 0                     # degrees counter-clockwise: 0/90/180/270
    imir_axis: int | None = None      # None | 0 | 1
    clap: dict | None = None          # width_n/d, height_n/d, horiz_off_n/d, vert_off_n/d
    exif_bytes: bytes | None = None   # raw Exif item payload (4-byte offset + TIFF)


def _boxes(buf: bytes, start: int, end: int):
    """Yield (type, payload_start, box_end) for sibling boxes in buf[start:end]."""
    p = start
    while p + 8 <= end:
        size, typ = struct.unpack(">I4s", buf[p:p + 8])
        hdr = 8
        if size == 1:
            if p + 16 > end:
                return
            size = struct.unpack(">Q", buf[p + 8:p + 16])[0]
            hdr = 16
        elif size == 0:
            size = end - p
        if size < hdr or p + size > end:
            return
        yield typ.decode("latin-1"), p + hdr, p + size
        p += size


def _uint(buf: bytes, p: int, n: int) -> int:
    return int.from_bytes(buf[p:p + n], "big") if n else 0


def _parse_iinf(buf, s, e):
    ver = buf[s]
    p = s + 4
    p += 2 if ver == 0 else 4
    items = {}
    for typ, ps, pe in _boxes(buf, p, e):
        if typ != "infe":
            continue
        v = buf[ps]
        q = ps + 4
        if v in (2, 3):
            if v == 2:
                iid = _uint(buf, q, 2); q += 2
            else:
                iid = _uint(buf, q, 4); q += 4
            q += 2  # protection index
            items[iid] = buf[q:q + 4].decode("latin-1")
    return items


def _parse_iloc(buf, s, e):
    ver = buf[s]
    p = s + 4
    osz, lsz = buf[p] >> 4, buf[p] & 15
    bsz, isz = buf[p + 1] >> 4, buf[p + 1] & 15
    if ver not in (1, 2):
        isz = 0
    p += 2
    if ver < 2:
        count = _uint(buf, p, 2); p += 2
    else:
        count = _uint(buf, p, 4); p += 4
    out = {}
    for _ in range(count):
        if p + 2 > e:
            break
        if ver < 2:
            iid = _uint(buf, p, 2); p += 2
        else:
            iid = _uint(buf, p, 4); p += 4
        cm = 0
        if ver in (1, 2):
            cm = _uint(buf, p, 2) & 0xF; p += 2
        p += 2  # data_reference_index
        base = _uint(buf, p, bsz); p += bsz
        ec = _uint(buf, p, 2); p += 2
        extents = []
        for _ in range(ec):
            p += isz
            off = _uint(buf, p, osz); p += osz
            ln = _uint(buf, p, lsz); p += lsz
            extents.append((base + off, ln))
        if cm == 0:
            out[iid] = extents
    return out


def _parse_ipma(buf, s, e):
    ver = buf[s]
    flags = _uint(buf, s + 1, 3)
    p = s + 4
    n = _uint(buf, p, 4); p += 4
    out = {}
    for _ in range(n):
        if p >= e:
            break
        if ver < 1:
            iid = _uint(buf, p, 2); p += 2
        else:
            iid = _uint(buf, p, 4); p += 4
        ac = buf[p]; p += 1
        idx = []
        for _ in range(ac):
            if flags & 1:
                v = _uint(buf, p, 2); p += 2
                idx.append(v & 0x7FFF)
            else:
                v = buf[p]; p += 1
                idx.append(v & 0x7F)
        out[iid] = idx
    return out


def _parse_clap(buf, ps, pe):
    if pe - ps < 32:
        return None
    wn, wd, hn, hd = struct.unpack(">IIII", buf[ps:ps + 16])
    hon, hod, von, vod = struct.unpack(">iIiI", buf[ps + 16:ps + 32])
    return {"width_n": wn, "width_d": wd, "height_n": hn, "height_d": hd,
            "horiz_off_n": hon, "horiz_off_d": hod, "vert_off_n": von, "vert_off_d": vod}


def parse_heif(path_or_bytes) -> HeifInfo:
    """Parse HEIF container metadata; never decodes pixels."""
    if isinstance(path_or_bytes, (bytes, bytearray, memoryview)):
        buf = bytes(path_or_bytes)
    else:
        buf = Path(path_or_bytes).read_bytes()
    info = HeifInfo()
    meta = None
    for typ, ps, pe in _boxes(buf, 0, len(buf)):
        if typ == "ftyp" and pe - ps >= 4:
            info.brand = buf[ps:ps + 4].decode("latin-1")
        elif typ == "meta":
            meta = (ps + 4, pe)  # FullBox: skip version/flags
    if meta is None:
        return info

    items: dict[int, str] = {}
    locs: dict[int, list] = {}
    props: list[tuple[str, int, int]] = []
    assoc: dict[int, list[int]] = {}
    for typ, ps, pe in _boxes(buf, *meta):
        if typ == "pitm":
            info.primary_item_id = _uint(buf, ps + 4, 2 if buf[ps] == 0 else 4)
        elif typ == "iinf":
            items = _parse_iinf(buf, ps, pe)
        elif typ == "iloc":
            locs = _parse_iloc(buf, ps, pe)
        elif typ == "iprp":
            for t2, s2, e2 in _boxes(buf, ps, pe):
                if t2 == "ipco":
                    props = [(t3, s3, e3) for t3, s3, e3 in _boxes(buf, s2, e2)]
                elif t2 == "ipma":
                    assoc = _parse_ipma(buf, s2, e2)

    pid = info.primary_item_id
    if pid is None and items:
        pid = min(items)
        info.primary_item_id = pid
    for idx in assoc.get(pid, []):
        if idx < 1 or idx > len(props):
            continue
        t, ps, pe = props[idx - 1]
        if t == "ispe" and pe - ps >= 12:
            info.width, info.height = struct.unpack(">II", buf[ps + 4:ps + 12])
        elif t == "irot" and pe > ps:
            info.irot = 90 * (buf[ps] & 3)
        elif t == "imir" and pe > ps:
            info.imir_axis = buf[ps] & 1
        elif t == "clap":
            info.clap = _parse_clap(buf, ps, pe)

    for iid, typ in items.items():
        if typ == "Exif" and iid in locs:
            chunks = [buf[o:o + n] for o, n in locs[iid]]
            info.exif_bytes = b"".join(chunks)
            break
    return info


def orientation_ops(info: HeifInfo) -> list[tuple]:
    """Ordered display transforms per HEIF semantics: clap, then irot, then imir.

    Entries: ``('crop', clap_dict)``, ``('rotate_ccw', deg)`` (deg in 90/180/270),
    ``('mirror', axis)``. EXIF Orientation must be ignored whenever this list is
    non-empty (see module docstring).
    """
    ops: list[tuple] = []
    if info.clap:
        ops.append(("crop", dict(info.clap)))
    if info.irot:
        ops.append(("rotate_ccw", int(info.irot)))
    if info.imir_axis is not None:
        ops.append(("mirror", int(info.imir_axis)))
    return ops
