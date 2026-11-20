"""LandmarkSet I/O (DESIGN 3.2 landmark files, 3.1 coordinates; eth F1).

File: JSON ``{"format": "face3d.landmarks", "version": 1, "licence": ..., "scheme": ...,
"detector": {...}, "image": {...}, "faces": [...]}``. Each per-face array is either an
inline nested list (NaN stored as null) or a reference ``{"file": "x.npy", "sha256": ...}``
to a ``.npy`` path relative to the JSON file; the SHA-256 is verified on load. Arrays
with more than ``inline_threshold`` values are written to ``.npy`` (DESIGN 3.2: ~1,000).

Conventions: ``uv`` are continuous pixel coordinates with a top-left *corner* origin
(``image.coords == 'px_corner'``, the only accepted value), float64, NaN for missing
landmarks. The scheme name is mandatory and never inferred from the landmark count.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

try:  # WP-04 provides the shared error type; fall back so this module stands alone.
    from face3d.core.schema import FormatError
except ImportError:  # pragma: no cover - depends on tree state
    class FormatError(ValueError):
        """Raised for malformed or unsupported face3d JSON files."""

FORMAT = "face3d.landmarks"
VERSION = 1
COORDS = "px_corner"


@dataclass
class Face:
    score: float
    uv: np.ndarray                      # (N, 2) float64, NaN = missing
    visible: np.ndarray                 # (N,) bool
    cov: np.ndarray | None = None       # (N, 2, 2) px^2
    tta_spread_px: np.ndarray | None = None  # (N,) px
    blendshapes: dict | None = None


@dataclass
class LandmarkSet:
    scheme: str
    detector: dict = field(default_factory=dict)  # backend, version, model_sha256, licence, commercial_ok, is_ml
    image: dict = field(default_factory=dict)     # sha256, wh, orientation_applied, input_flipped, coords
    faces: list = field(default_factory=list)


def from_mediapipe_normalized(points, W: float, H: float) -> np.ndarray:
    """MediaPipe normalised (x, y[, z]) -> corner-origin pixels: u = x*W, v = y*H; z is dropped."""
    p = np.asarray(points, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] not in (2, 3):
        raise ValueError("points must be (N, 2) or (N, 3)")
    return np.stack([p[:, 0] * W, p[:, 1] * H], axis=1)


def select_face(ls: LandmarkSet, index: int) -> Face:
    """Return the face the caller chose (eth F1). The engine never auto-fits a second face."""
    if not ls.faces:
        raise IndexError("landmark set has no faces")
    if not -len(ls.faces) <= index < len(ls.faces):
        raise IndexError(f"face index {index} out of range (0..{len(ls.faces) - 1})")
    return ls.faces[index]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _to_list(a: np.ndarray):
    out = np.asarray(a).tolist()

    def fix(x):
        if isinstance(x, list):
            return [fix(y) for y in x]
        if isinstance(x, float) and x != x:
            return None
        return x
    return fix(out) if np.asarray(a).dtype.kind == "f" else out


def _from_list(x, dtype):
    a = np.array(x, dtype=object) if dtype == np.float64 else np.array(x)
    if dtype == np.float64:
        flat = [np.nan if v is None else v for v in a.ravel().tolist()]
        return np.array(flat, dtype=np.float64).reshape(a.shape)
    return a.astype(dtype)


def _check_shapes(n, vis, cov, tta, err, where):
    if tuple(vis) != (n,):
        raise err(f"{where}: visible must have shape ({n},), got {tuple(vis)}")
    if cov is not None and tuple(cov) != (n, 2, 2):
        raise err(f"{where}: cov must have shape ({n}, 2, 2), got {tuple(cov)}")
    if tta is not None and tuple(tta) != (n,):
        raise err(f"{where}: tta_spread_px must have shape ({n},), got {tuple(tta)}")


def save_landmarks(ls: LandmarkSet, path, inline_threshold: int = 1000) -> None:
    """Write ``ls`` as JSON; arrays above ``inline_threshold`` values go to sibling ``.npy`` files."""
    if not ls.scheme:
        raise FormatError("landmark set has no scheme")
    path = Path(path)
    image = dict(ls.image)
    image.setdefault("coords", COORDS)
    if image["coords"] != COORDS:
        raise FormatError(f"coords must be {COORDS!r}")

    def put(arr, key, fi):
        arr = np.asarray(arr)
        if arr.size > inline_threshold:
            fn = f"{path.stem}.face{fi}.{key}.npy"
            np.save(path.parent / fn, arr, allow_pickle=False)
            return {"file": fn, "sha256": _sha256(path.parent / fn)}
        return _to_list(arr)

    faces = []
    for fi, f in enumerate(ls.faces):
        uv = np.asarray(f.uv, dtype=np.float64)
        _check_shapes(len(uv), np.shape(f.visible), None if f.cov is None else np.shape(f.cov),
                      None if f.tta_spread_px is None else np.shape(f.tta_spread_px), FormatError, "face")
        d = {"score": float(f.score), "uv": put(uv, "uv", fi),
             "visible": put(np.asarray(f.visible, dtype=bool), "visible", fi)}
        d["cov"] = None if f.cov is None else put(np.asarray(f.cov, dtype=np.float64), "cov", fi)
        d["tta_spread_px"] = (None if f.tta_spread_px is None
                              else put(np.asarray(f.tta_spread_px, dtype=np.float64), "tta_spread_px", fi))
        d["blendshapes"] = (None if f.blendshapes is None
                            else {str(k): float(v) for k, v in f.blendshapes.items()})
        faces.append(d)
    doc = {"format": FORMAT, "version": VERSION,
           "licence": ls.detector.get("licence"), "scheme": ls.scheme,
           "detector": ls.detector, "image": image, "faces": faces}
    path.write_text(json.dumps(doc, indent=1, sort_keys=True, allow_nan=False))


def load_landmarks(path) -> LandmarkSet:
    """Read a landmark JSON, resolving and SHA-verifying ``.npy`` references."""
    path = Path(path)
    try:
        doc = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise FormatError(f"{path}: invalid JSON ({e})") from e
    if not isinstance(doc, dict) or doc.get("format") != FORMAT:
        raise FormatError(f"{path}: not a {FORMAT} file")
    ver = doc.get("version")
    if not isinstance(ver, int) or ver > VERSION:
        raise FormatError(f"{path}: unsupported version {ver!r}")
    scheme = doc.get("scheme")
    if not scheme or not isinstance(scheme, str):
        raise FormatError(f"{path}: 'scheme' is required (never inferred from landmark count)")
    image = dict(doc.get("image") or {})
    if image.get("coords") != COORDS:
        raise FormatError(f"{path}: image.coords must be {COORDS!r}, got {image.get('coords')!r}")

    def get(v, dtype):
        if isinstance(v, dict) and "file" in v:
            fp = path.parent / v["file"]
            if Path(v["file"]).is_absolute() or not fp.resolve().is_relative_to(path.parent.resolve()):
                raise FormatError(f"{path}: array reference {v['file']!r} escapes the JSON folder")
            if not fp.is_file():
                raise FormatError(f"{path}: missing array file {v['file']}")
            if _sha256(fp) != v.get("sha256"):
                raise FormatError(f"{path}: SHA-256 mismatch for {v['file']}")
            return np.load(fp, allow_pickle=False).astype(dtype, copy=False)
        return _from_list(v, dtype)

    faces = []
    for d in doc.get("faces", []):
        uv = get(d["uv"], np.float64)
        if uv.ndim != 2 or uv.shape[1] != 2:
            raise FormatError(f"{path}: uv must be (N, 2)")
        vis = get(d["visible"], bool) if d.get("visible") is not None else np.ones(len(uv), bool)
        cov = None if d.get("cov") is None else get(d["cov"], np.float64)
        tta = None if d.get("tta_spread_px") is None else get(d["tta_spread_px"], np.float64)
        _check_shapes(len(uv), vis.shape, None if cov is None else cov.shape,
                      None if tta is None else tta.shape, lambda m: FormatError(f"{path}: {m}"), "face")
        faces.append(Face(
            score=float(d["score"]), uv=uv, visible=vis, cov=cov, tta_spread_px=tta,
            blendshapes=None if d.get("blendshapes") is None else dict(d["blendshapes"]),
        ))
    return LandmarkSet(scheme=scheme, detector=dict(doc.get("detector") or {}), image=image, faces=faces)
