import struct

import numpy as np
import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image, ImageCms  # noqa: E402,F401
from PIL.TiffImagePlugin import IFDRational  # noqa: E402

from face3d.io import image_ops as ops  # noqa: E402
from face3d.io.exif import read_exif, read_exif_bytes  # noqa: E402
from face3d.io.heif import orientation_ops, parse_heif  # noqa: E402
from face3d.io.png import read_png, write_png  # noqa: E402


# ---------------------------------------------------------------- EXIF
def test_exif_new_tags(tmp_path):
    ex = Image.Exif()
    ex[0x010F] = "Apple"
    ex[0x0110] = "iPhone 15"
    ex[0x0131] = "17.1"
    ex[0x013B] = "Me"
    ex[0x8298] = "(c) me"
    ex[0x0112] = 6
    ifd = ex.get_ifd(0x8769)
    ifd[0x9003] = "2024:01:02 03:04:05"
    ifd[0xA404] = IFDRational(3, 2)
    ifd[0xA434] = "iPhone 15 front camera"
    ifd[0xA433] = "Apple"
    ifd[0xA401] = 1
    ifd[0x9206] = IFDRational(7, 10)
    ifd[0xA432] = (IFDRational(2, 1), IFDRational(2, 1), IFDRational(19, 10), IFDRational(19, 10))
    ex.get_ifd(0x8825)[1] = "N"
    p = tmp_path / "a.jpg"
    Image.new("RGB", (40, 30)).save(p, exif=ex)
    i = read_exif(p)
    assert i.datetime_original == "2024:01:02 03:04:05"
    assert i.software == "17.1" and i.artist == "Me" and i.copyright == "(c) me"
    assert i.digital_zoom_ratio == 1.5 and i.lens_make == "Apple"
    assert i.custom_rendered == 1 and i.subject_distance_m == pytest.approx(0.7)
    assert i.lens_specification == pytest.approx((2.0, 2.0, 1.9, 1.9))
    assert i.is_front_camera and i.has_gps and not i.has_xmp and not i.has_makernote
    assert i.orientation == 6
    key = i.focal_group_key(3024, 4032)
    assert key == "Apple|iPhone 15|iPhone 15 front camera||3024|4032|still"
    assert i.focal_group_key(1, 2, still=False).endswith("|video")


def test_exif_multiple_app1_segments(tmp_path):
    ex = Image.Exif()
    ex[0x010F] = "Cam"
    ex[0x0112] = 3
    p = tmp_path / "b.jpg"
    Image.new("RGB", (16, 16)).save(p, exif=ex)
    data = p.read_bytes()
    xmp = b"http://ns.adobe.com/xap/1.0/\0<x:xmpmeta/>"
    seg = b"\xff\xe1" + struct.pack(">H", len(xmp) + 2) + xmp
    q = tmp_path / "c.jpg"
    q.write_bytes(data[:2] + seg + data[2:])
    i = read_exif(q)
    assert i.has_xmp and i.make == "Cam" and i.orientation == 3
    assert not read_exif(p).has_xmp


# ---------------------------------------------------------------- HEIF
def _box(t, payload):
    return struct.pack(">I4s", 8 + len(payload), t) + payload


def _full(t, ver, flags, payload):
    return _box(t, bytes([ver]) + flags.to_bytes(3, "big") + payload)


def _synthetic_heif(exif_tiff):
    exif_item = struct.pack(">I", 0) + exif_tiff
    ftyp = _box(b"ftyp", b"heic" + b"\0\0\0\0" + b"mif1heic")
    hdlr = _full(b"hdlr", 0, 0, b"\0" * 4 + b"pict" + b"\0" * 12 + b"\0")
    pitm = _full(b"pitm", 0, 0, struct.pack(">H", 1))
    infe1 = _full(b"infe", 2, 0, struct.pack(">HH4s", 1, 0, b"hvc1") + b"\0")
    infe2 = _full(b"infe", 2, 0, struct.pack(">HH4s", 2, 0, b"Exif") + b"\0")
    iinf = _full(b"iinf", 0, 0, struct.pack(">H", 2) + infe1 + infe2)
    ispe = _full(b"ispe", 0, 0, struct.pack(">II", 4032, 3024))
    irot = _box(b"irot", b"\x01")
    imir = _box(b"imir", b"\x01")
    ipco = _box(b"ipco", ispe + irot + imir)
    ipma = _full(b"ipma", 0, 0, struct.pack(">I", 1) + struct.pack(">HB", 1, 3) + bytes([0x81, 2, 3]))
    iprp = _box(b"iprp", ipco + ipma)

    def iloc(off):
        body = bytes([0x44, 0x00]) + struct.pack(">H", 1)  # offset_size 4, length_size 4, base 0
        body += struct.pack(">HHHH", 2, 0, 0, 1) + struct.pack(">II", off, len(exif_item))
        return _full(b"iloc", 1, 0, body)

    def meta(off):
        return _full(b"meta", 0, 0, hdlr + pitm + iinf + iloc(off) + iprp)

    off = len(ftyp) + len(meta(0)) + 8  # past the mdat header
    return ftyp + meta(off) + _box(b"mdat", exif_item)


def test_heif_box_parser_on_synthetic_bytes(tmp_path):
    ex = Image.Exif()
    ex[0x0112] = 8
    ex[0x010F] = "Apple"
    tiff = ex.tobytes()[6:] if ex.tobytes()[:6] == b"Exif\0\0" else ex.tobytes()
    data = _synthetic_heif(tiff)
    info = parse_heif(data)
    assert info.brand == "heic" and info.primary_item_id == 1
    assert (info.width, info.height) == (4032, 3024)
    assert info.irot == 90 and info.imir_axis == 1 and info.clap is None
    assert info.exif_bytes is not None
    e = read_exif_bytes(info.exif_bytes)
    assert e.orientation == 8 and e.make == "Apple"
    assert orientation_ops(info) == [("rotate_ccw", 90), ("mirror", 1)]
    f = tmp_path / "x.heic"
    f.write_bytes(data)
    assert parse_heif(f).irot == 90
    # Exif\0\0-prefixed and bare TIFF are also accepted
    assert read_exif_bytes(b"Exif\0\0" + tiff).orientation == 8
    assert read_exif_bytes(tiff).orientation == 8


# ---------------------------------------------------------------- PNG
def _pil_arr(im):
    return np.asarray(im)


@pytest.mark.parametrize("mode", ["RGB", "RGBA", "L", "LA"])
def test_png_roundtrip_and_pillow_parity(tmp_path, mode):
    rng = np.random.default_rng(1)
    nch = {"RGB": 3, "RGBA": 4, "L": 1, "LA": 2}[mode]
    a = rng.integers(0, 256, (23, 31, nch), dtype=np.uint8)
    # smooth areas so all filter types occur
    a[:, :10] = np.arange(10, dtype=np.uint8)[None, :, None]
    im = Image.fromarray(a[..., 0] if nch == 1 else a, mode)
    p = tmp_path / "p.png"
    im.save(p)
    np.testing.assert_array_equal(read_png(p), _pil_arr(im))
    q = tmp_path / "q.png"
    if nch in (1, 3, 4):
        arr = read_png(p)
        write_png(q, arr)
        np.testing.assert_array_equal(read_png(q), arr)
        np.testing.assert_array_equal(_pil_arr(Image.open(q)), arr)


def test_png_16bit_palette_interlace(tmp_path):
    rng = np.random.default_rng(2)
    g = rng.integers(0, 65536, (17, 19), dtype=np.uint16)
    p = tmp_path / "g16.png"
    write_png(p, g)
    r = read_png(p)
    assert r.dtype == np.uint16
    np.testing.assert_array_equal(r, g)
    np.testing.assert_array_equal(_pil_arr(Image.open(p)), g)
    rgb = rng.integers(0, 65536, (5, 6, 3), dtype=np.uint16)
    write_png(p, rgb)
    np.testing.assert_array_equal(read_png(p), rgb)

    # Pillow-written 16-bit grey (exercises real filters)
    sm = (np.add.outer(np.arange(20), np.arange(30)) * 700).astype(np.uint16)
    Image.fromarray(sm).save(tmp_path / "s16.png")
    np.testing.assert_array_equal(read_png(tmp_path / "s16.png"), sm)

    pal = Image.fromarray(rng.integers(0, 7, (12, 14), dtype=np.uint8), "P")
    pal.putpalette([int(x) for x in rng.integers(0, 256, 21)])
    pal.save(tmp_path / "pal.png", bits=8)
    np.testing.assert_array_equal(read_png(tmp_path / "pal.png"), _pil_arr(pal.convert("RGB")))
    pal.save(tmp_path / "palt.png", transparency=2, bits=8)
    out = read_png(tmp_path / "palt.png")
    np.testing.assert_array_equal(out, _pil_arr(Image.open(tmp_path / "palt.png").convert("RGBA")))

    with pytest.raises(NotImplementedError, match="Adam7"):
        _write_interlaced(tmp_path / "i.png")
        read_png(tmp_path / "i.png")
    with pytest.raises(ValueError):
        b = bytearray((tmp_path / "pal.png").read_bytes())
        b[-6] ^= 0xFF  # corrupt IEND CRC region
        read_png(bytes(b))


def _write_interlaced(path):
    import zlib

    def ch(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 1)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", ihdr) + ch(b"IDAT", zlib.compress(b"\0\0"))
                     + ch(b"IEND", b""))


# ---------------------------------------------------------------- image_ops
@pytest.mark.parametrize("o", range(1, 9))
def test_orientation_maps_consistent(o):
    W, H = 5, 3
    for (i, j) in [(0, 0), (4, 0), (0, 2), (3, 1), (4, 2)]:
        img = np.zeros((H, W), dtype=np.uint8)
        img[j, i] = 1
        out = ops.apply_orientation(img, o)
        m = ops.orientation_point_map(o, W, H)
        assert out.shape == m.out_wh[::-1]
        uv = m(np.array([i + 0.5, j + 0.5]))
        assert out[int(uv[1]), int(uv[0])] == 1 and out.sum() == 1
        assert uv[0] % 1 == 0.5 and uv[1] % 1 == 0.5
        np.testing.assert_array_equal(m.inverse(uv), [i + 0.5, j + 0.5])
        assert m.inverse.out_wh == (W, H)
    m6 = ops.orientation_point_map(6, W, H)
    np.testing.assert_array_equal(m6([1.0, 2.0]), [H - 2.0, 1.0])
    np.testing.assert_array_equal(ops.orientation_point_map(3, W, H)([1.0, 2.0]), [W - 1.0, H - 2.0])
    np.testing.assert_array_equal(ops.orientation_point_map(2, W, H)([1.0, 2.0]), [W - 1.0, 2.0])
    # o=6 really is a clockwise rotation: stored top-left pixel ends up top-right
    a = np.arange(6).reshape(2, 3)
    np.testing.assert_array_equal(ops.apply_orientation(a, 6), [[3, 0], [4, 1], [5, 2]])


def test_heif_ops_consistent():
    W, H = 8, 6
    clap = {"width_n": 6, "width_d": 1, "height_n": 4, "height_d": 1,
            "horiz_off_n": 1, "horiz_off_d": 1, "vert_off_n": 0, "vert_off_d": 1}
    for ops_list in ([("crop", clap), ("rotate_ccw", 90), ("mirror", 0)],
                     [("rotate_ccw", 270), ("mirror", 1)], [("rotate_ccw", 180)], []):
        for (i, j) in [(3, 2), (4, 3), (5, 2)]:
            img = np.zeros((H, W), np.uint8)
            img[j, i] = 1
            out = ops.apply_heif_ops(img, ops_list)
            m = ops.heif_point_map(ops_list, W, H)
            assert out.shape == m.out_wh[::-1]
            uv = m(np.array([i + 0.5, j + 0.5]))
            assert out[int(uv[1]), int(uv[0])] == 1 and out.sum() == 1
            np.testing.assert_allclose(m.inverse(uv), [i + 0.5, j + 0.5])


def test_flip_uv_involution_with_permutation():
    rng = np.random.default_rng(3)
    n = 10
    perm = np.arange(n)
    perm[[0, 1]] = [1, 0]
    perm[[4, 7]] = [7, 4]
    uv = rng.uniform(0, 100, (n, 2))
    f = ops.flip_uv(uv, 100.0, perm)
    np.testing.assert_allclose(f[1], [100 - uv[0, 0], uv[0, 1]])
    np.testing.assert_allclose(f[2], [100 - uv[2, 0], uv[2, 1]])
    np.testing.assert_allclose(ops.flip_uv(f, 100.0, perm), uv)
    img = rng.random((4, 5))
    np.testing.assert_array_equal(ops.flip_horizontal(ops.flip_horizontal(img)), img)


def test_resize_uv_corner_convention():
    uv = np.array([[0.0, 0.0], [100.0, 50.0], [50.0, 25.0]])
    out = ops.resize_uv(uv, 100, 50, 10, 20)
    np.testing.assert_allclose(out, [[0, 0], [10, 20], [5, 10]])


def test_colour_helpers():
    x = np.linspace(0, 1, 101)
    np.testing.assert_allclose(ops.linear_to_srgb(ops.srgb_to_linear(x)), x, atol=1e-12)
    assert ops.srgb_to_linear(0.5) == pytest.approx(0.21404114, abs=1e-7)
    g = ops.to_gray(np.ones((2, 2, 3)))
    np.testing.assert_allclose(g, 1.0)
    assert ops.to_gray(np.array([[[1.0, 0, 0]]]))[0, 0] == pytest.approx(0.2126)


# ---------------------------------------------------------------- review fixes
def test_heif_imir_axes_match_iso_and_exif():
    rng = np.random.default_rng(0)
    img = rng.integers(0, 255, (5, 7, 3), dtype=np.uint8)
    # ISO/IEC 23008-12: axis 0 swaps top/bottom (= EXIF 4), axis 1 left/right (= EXIF 2)
    assert np.array_equal(ops.apply_heif_ops(img, [("mirror", 1)]), ops.apply_orientation(img, 2))
    assert np.array_equal(ops.apply_heif_ops(img, [("mirror", 0)]), ops.apply_orientation(img, 4))
    assert np.array_equal(ops.apply_heif_ops(img, [("rotate_ccw", 90), ("mirror", 0)]),
                          ops.apply_orientation(img, 5))
    assert np.array_equal(ops.apply_heif_ops(img, [("rotate_ccw", 270), ("mirror", 0)]),
                          ops.apply_orientation(img, 7))
    # point maps agree with the EXIF maps
    for hops, o in (([("mirror", 1)], 2), ([("mirror", 0)], 4),
                    ([("rotate_ccw", 90), ("mirror", 0)], 5),
                    ([("rotate_ccw", 270), ("mirror", 0)], 7)):
        pts = np.array([[0.5, 0.5], [3.25, 1.75]])
        np.testing.assert_allclose(ops.heif_point_map(hops, 7, 5)(pts),
                                   ops.orientation_point_map(o, 7, 5)(pts))


def test_clap_rounding_and_zero_denominator():
    img = np.arange(30 * 40).reshape(30, 40)
    clap = dict(width_n=10, width_d=1, height_n=8, height_d=1, horiz_off_n=6, horiz_off_d=1,
                vert_off_n=-4, vert_off_d=1)
    out = ops.apply_heif_ops(img, [("crop", clap)])
    assert out.shape == (8, 10) and out[0, 0] == img[15 - 4 - 4, 20 + 6 - 5]
    odd = dict(clap, width_n=39, horiz_off_n=0, horiz_off_d=1)  # half-integer left edge -> floor
    assert ops.apply_heif_ops(img, [("crop", odd)]).shape[1] == 39
    bad = dict(clap, width_d=0)
    with pytest.raises(ValueError):
        ops.apply_heif_ops(img, [("crop", bad)])


def test_flip_uv_rejects_non_permutation():
    uv = 100 + np.arange(8, dtype=float).reshape(4, 2)
    with pytest.raises(ValueError):
        ops.flip_uv(uv, 1000.0, [1, 0, 0, 3])


def test_colour_helper_robustness():
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        ops.srgb_to_linear([-0.1, 0.5])
    ga = np.stack([np.full((2, 2), 0.3), np.ones((2, 2))], axis=-1)
    assert np.allclose(ops.to_gray(ga), 0.3)


def test_exif_sentinels(tmp_path):
    def read(tags):
        ex = Image.Exif()
        sub = ex.get_ifd(0x8769)
        for k, v in tags.items():
            sub[k] = v
        p = tmp_path / "s.jpg"
        Image.new("RGB", (8, 8)).save(p, exif=ex)
        return read_exif(p)
    assert read({0x9206: IFDRational(0, 1)}).subject_distance_m is None
    assert read({0x9206: IFDRational(0xFFFFFFFF, 1)}).subject_distance_m == float("inf")
    assert read({0x9206: IFDRational(5, 2)}).subject_distance_m == 2.5
    assert read({0xA404: IFDRational(0, 100)}).digital_zoom_ratio == 1.0
    assert read({0xA404: IFDRational(3, 2)}).digital_zoom_ratio == 1.5


def test_exif_makernote_flag(tmp_path):
    ex = Image.Exif()
    ex.get_ifd(0x8769)[0x927C] = b"abcdefgh"
    p = tmp_path / "m.jpg"
    Image.new("RGB", (8, 8)).save(p, exif=ex)
    assert read_exif(p).has_makernote


def _png_chunk(t, d):
    import zlib
    c = struct.pack(">I", len(d)) + t + d
    return c + struct.pack(">I", zlib.crc32(t + d))


def test_png_all_filter_types_independent_encoder():
    import zlib
    rng = np.random.default_rng(1)
    H, W, bpp = 10, 9, 3
    img = rng.integers(0, 256, (H, W, bpp), dtype=np.uint8)
    prev = bytearray(W * bpp)
    raw = bytearray()
    for y in range(H):
        row = img[y].tobytes()
        ft = y % 5
        out = bytearray()
        for i, x in enumerate(row):
            a = row[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if ft == 0:
                pred = 0
            elif ft == 1:
                pred = a
            elif ft == 2:
                pred = b
            elif ft == 3:
                pred = (a + b) // 2
            else:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pred = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
            out.append((x - pred) & 255)
        raw += bytes([ft]) + out
        prev = bytearray(row)
    data = (b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
            + _png_chunk(b"IDAT", zlib.compress(bytes(raw))) + _png_chunk(b"IEND", b""))
    assert np.array_equal(read_png(data), img)


def _heif_variant(exif_tiff, large=False, ipma_flags=0, clap=None):
    def box(t, p):
        if large:
            return struct.pack(">I4sQ", 1, t, 16 + len(p)) + p
        return _box(t, p)

    def full(t, ver, flags, p):
        return box(t, bytes([ver]) + flags.to_bytes(3, "big") + p)
    ftyp = _box(b"ftyp", b"avif" + b"\0\0\0\0" + b"mif1avif")
    pitm = full(b"pitm", 1, 0, struct.pack(">I", 1))
    infe = full(b"infe", 2, 0, struct.pack(">HH4s", 1, 0, b"av01") + b"\0")
    iinf = full(b"iinf", 0, 0, struct.pack(">H", 1) + infe)
    ispe = full(b"ispe", 0, 0, struct.pack(">II", 40, 30))
    props, idx = ispe, [1]
    if clap:
        props += box(b"clap", struct.pack(">IIIIiIiI", *clap))
        idx.append(2)
    if ipma_flags & 1:
        ent = b"".join(struct.pack(">H", 0x8000 | i) for i in idx)
        ipma = full(b"ipma", 1, 1, struct.pack(">I", 1) + struct.pack(">IB", 1, len(idx)) + ent)
    else:
        ent = bytes(0x80 | i for i in idx)
        ipma = full(b"ipma", 0, 0, struct.pack(">I", 1) + struct.pack(">HB", 1, len(idx)) + ent)
    iprp = box(b"iprp", box(b"ipco", props) + ipma)
    return ftyp + full(b"meta", 0, 0, pitm + iinf + iprp)


@pytest.mark.parametrize("large,flags", [(False, 0), (True, 0), (False, 1)])
def test_heif_variants_largesize_ipma15_clap(large, flags):
    clap = (10, 1, 8, 1, 6, 1, -4, 1)
    info = parse_heif(_heif_variant(b"", large=large, ipma_flags=flags, clap=clap))
    assert info.primary_item_id == 1 and (info.width, info.height) == (40, 30)
    assert info.clap == dict(width_n=10, width_d=1, height_n=8, height_d=1,
                             horiz_off_n=6, horiz_off_d=1, vert_off_n=-4, vert_off_d=1)
    img = np.arange(30 * 40).reshape(30, 40)
    out = ops.apply_heif_ops(img, orientation_ops(info))
    # window centre = (20+6, 15-4) = (26, 11); left = 21, top = 7
    assert out.shape == (8, 10) and out[0, 0] == img[7, 21]
