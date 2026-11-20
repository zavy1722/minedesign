import json

import numpy as np
import pytest

from face3d.io.landmarks import (Face, FormatError, LandmarkSet, from_mediapipe_normalized,
                                 load_landmarks, save_landmarks, select_face)


def _ls(n=478):
    rng = np.random.default_rng(0)
    uv = rng.uniform(0, 1000, (n, 2))
    uv[3] = np.nan
    cov = np.tile(np.eye(2), (n, 1, 1)) * 0.5
    f = Face(0.97, uv, rng.random(n) > 0.1, cov, rng.random(n), {"jawOpen": 0.25})
    g = Face(0.5, uv[:5].copy(), np.ones(5, bool))
    det = {"backend": "x", "version": "1", "model_sha256": "ab", "licence": "Apache-2.0",
           "commercial_ok": True, "is_ml": True}
    img = {"sha256": "cd", "wh": [1000, 800], "orientation_applied": 6, "input_flipped": False,
           "coords": "px_corner"}
    return LandmarkSet("mediapipe478", det, img, [f, g])


def test_landmarkset_roundtrip_scheme_required_and_npy_refs(tmp_path):
    ls = _ls()
    p = tmp_path / "lm.json"
    save_landmarks(ls, p)
    assert (tmp_path / "lm.face0.cov.npy").exists()          # 1912 values > threshold
    assert isinstance(json.loads(p.read_text())["faces"][0]["uv"], list)  # 956 values: inline
    doc = json.loads(p.read_text())
    assert isinstance(doc["faces"][0]["cov"], dict) and "sha256" in doc["faces"][0]["cov"]
    assert isinstance(doc["faces"][1]["uv"], list)           # small -> inline
    back = load_landmarks(p)
    assert back.scheme == "mediapipe478" and back.detector == ls.detector
    assert back.image["wh"] == [1000, 800]
    for a, b in zip(ls.faces, back.faces):
        np.testing.assert_array_equal(a.uv, b.uv)
        np.testing.assert_array_equal(a.visible, b.visible)
        assert a.score == b.score and a.blendshapes == b.blendshapes
    assert np.isnan(back.faces[0].uv[3]).all()
    np.testing.assert_array_equal(back.faces[0].cov, ls.faces[0].cov)

    # inline-only roundtrip with NaN -> null -> NaN
    p2 = tmp_path / "inline.json"
    save_landmarks(ls, p2, inline_threshold=10**9)
    assert "null" in p2.read_text()
    np.testing.assert_array_equal(load_landmarks(p2).faces[0].uv, ls.faces[0].uv)

    # scheme missing -> FormatError
    d = json.loads(p2.read_text())
    del d["scheme"]
    p3 = tmp_path / "noscheme.json"
    p3.write_text(json.dumps(d))
    with pytest.raises(FormatError):
        load_landmarks(p3)
    # wrong coords
    d = json.loads(p2.read_text())
    d["image"]["coords"] = "px_center"
    p3.write_text(json.dumps(d))
    with pytest.raises(FormatError):
        load_landmarks(p3)
    # sha mismatch
    np.save(tmp_path / "lm.face0.cov.npy", np.zeros((478, 2, 2)))
    with pytest.raises(FormatError):
        load_landmarks(p)


def test_from_mediapipe_normalized_and_select_face():
    pts = np.array([[0.25, 0.5, 0.1], [1.0, 0.0, -0.2]])
    uv = from_mediapipe_normalized(pts, 4032, 3024)
    assert uv.shape == (2, 2)
    assert uv[0, 0] == 0.25 * 4032 and uv[0, 1] == 0.5 * 3024
    assert from_mediapipe_normalized(pts[:, :2], 10, 20)[1, 0] == 10.0
    ls = _ls()
    assert select_face(ls, 1) is ls.faces[1]
    with pytest.raises(IndexError):
        select_face(ls, 2)


def test_licence_written_and_shapes_validated(tmp_path):
    ls = LandmarkSet("s", {"licence": "Apache-2.0"}, {"coords": "px_corner"},
                     [Face(1.0, np.zeros((5, 2)), np.ones(5, bool))])
    p = tmp_path / "a.json"
    save_landmarks(ls, p)
    assert json.loads(p.read_text())["licence"] == "Apache-2.0"
    load_landmarks(p)
    bad = LandmarkSet("s", {}, {"coords": "px_corner"},
                      [Face(1.0, np.zeros((5, 2)), np.ones(3, bool), np.zeros((2, 2, 2)))])
    with pytest.raises(FormatError):
        save_landmarks(bad, tmp_path / "b.json")
    doc = json.loads(p.read_text())
    doc["faces"][0]["visible"] = [True, False]
    p.write_text(json.dumps(doc))
    with pytest.raises(FormatError):
        load_landmarks(p)


def test_npy_reference_must_stay_in_folder(tmp_path):
    (tmp_path / "sub").mkdir()
    np.save(tmp_path / "other.npy", np.zeros((5, 2)))
    import hashlib
    sha = hashlib.sha256((tmp_path / "other.npy").read_bytes()).hexdigest()
    for ref in ("../other.npy", str(tmp_path / "other.npy")):
        doc = {"format": "face3d.landmarks", "version": 1, "scheme": "s",
               "image": {"coords": "px_corner"},
               "faces": [{"score": 1.0, "uv": {"file": ref, "sha256": sha}, "visible": None}]}
        p = tmp_path / "sub" / "lm.json"
        p.write_text(json.dumps(doc))
        with pytest.raises(FormatError):
            load_landmarks(p)
