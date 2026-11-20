import math

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

from face3d.io.exif import read_exif  # noqa: E402


def _jpeg_with_exif(path, focal=(26, 10), f35=26, make="TestPhone", orientation=1, size=(400, 300)):
    img = Image.new("RGB", size, (128, 100, 90))
    ex = Image.Exif()
    ex[0x010F] = make
    ex[0x0112] = orientation
    ifd = ex.get_ifd(0x8769)
    # Cameras store FocalLength as an unsigned RATIONAL (type 5).
    from PIL.TiffImagePlugin import IFDRational
    ifd[0x920A] = IFDRational(*focal)
    if f35 is not None:
        ifd[0xA405] = f35
    img.save(path, exif=ex)


def test_reads_focal_and_35mm(tmp_path):
    p = tmp_path / "a.jpg"
    _jpeg_with_exif(p, focal=(57, 10), f35=26)
    info = read_exif(p)
    assert info.make == "TestPhone"
    assert math.isclose(info.focal_length_mm, 5.7, rel_tol=1e-3)
    assert info.focal_35mm == 26
    fpx = info.focal_px(4000, 3000)
    assert math.isclose(fpx, 26 * 5000 / math.hypot(36, 24), rel_tol=1e-9)


def test_missing_exif_is_graceful(tmp_path):
    p = tmp_path / "b.jpg"
    Image.new("RGB", (10, 10)).save(p)
    info = read_exif(p)
    assert info.focal_35mm is None and info.focal_px(10, 10) is None


def test_orientation_and_no_35mm(tmp_path):
    p = tmp_path / "c.jpg"
    _jpeg_with_exif(p, f35=None, orientation=6)
    info = read_exif(p)
    assert info.orientation == 6
    assert info.focal_35mm is None
