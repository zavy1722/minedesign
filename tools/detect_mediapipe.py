#!/usr/bin/env python3
"""Run MediaPipe Face Landmarker on photos in the user's own Python and write LandmarkSet JSON.

Maintainer / user helper (DESIGN 2.5 source 2, D-23, D-28; WP-14).  It runs in
the **user's own Python** with a user-installed ``mediapipe`` and ``Pillow``
(optionally ``pillow-heif``) and a **user-supplied, SHA-256-pinned** ``.task``
model; the engine and the Blender extension never import it, never download a
model and never bundle one (eth A3/A4, C8).  ``mediapipe`` and ``Pillow`` are
imported only inside :func:`main`, so importing this module needs numpy and
``face3d`` only.

Usage::

    python3 tools/detect_mediapipe.py --model face_landmarker.task --model-sha256 HEX \\
        --images IMG_0412.HEIC IMG_0413.JPG --out DIR [--tta 8] [--num-faces 2] [--png-out] [--seed 0]

Steps per image (conventions of DESIGN 3.1 / 3.2):

1. **Model check.**  The model file is read once, its SHA-256 compared with
   ``--model-sha256`` and the run refused on a mismatch (eth F15); the verified
   bytes are handed to MediaPipe (``model_asset_buffer``), so the checked file
   is the file used.
2. **Load** with Pillow and ``ImageOps.exif_transpose`` (EXIF orientation baked,
   ``image.orientation_applied = True``); HEIC/HEIF through ``pillow-heif`` when
   installed (its decoder applies ``irot`` / ``imir`` / ``clap`` and EXIF
   Orientation is then ignored, DESIGN 3.1), else the image is refused with
   "convert to PNG".  ``image.sha256``
   is the SHA-256 of the original file bytes, ``image.wh`` the oriented size.
3. **Detect** with the Tasks API ``FaceLandmarker`` in IMAGE mode with
   ``output_face_blendshapes=True``, ``output_facial_transformation_matrixes=True``
   and ``num_faces``, on a copy resized so that the long side is at most
   :data:`DETECT_LONG_SIDE_PX` (2048 px, WP-14 spec).  Normalised landmarks map to
   the original image with the corner convention ``u = x * W``, ``v = y * H``
   (equivalently ``u' * W / W'`` from detection pixels; DESIGN 3.1).  MediaPipe z
   is dropped (scheme ``z_policy: 'ignore'``).
4. **Test-time augmentation** (``--tta N``, N >= 2; default 8; 0 or 1 = off):
   pass 0 is the plain image, passes 1..N-2 apply a random similarity about the
   image centre (scale ``1 +/- 2 %``, shift ``+/- 1 %`` of the size; seeded with
   ``--seed``), and the last pass is a horizontal flip whose labels are permuted
   by the scheme mirror permutation (:func:`face3d.io.image_ops.flip_uv`); points
   without a known mirror (not in a mirror pair and not on the midline) are
   excluded from the flip pass.  Every pass is mapped back exactly to original
   pixels; the output ``uv`` is the per-point median over passes and
   ``tta_spread_px = 1.4826 * median_k |uv_k - median|`` (MAD of the radial
   deviations scaled by the normal consistency constant, WP-14 spec;
   *landmark-detection* "Wood-style uncertainty from test-time augmentation" 🧠).
   For isotropic 2D noise of per-axis sigma this reads about 1.75 sigma, i.e. it
   is conservative.  Faces of later passes are matched to the plain-pass faces by
   landmark centroid (gate: :data:`FACE_MATCH_GATE` x the face's bounding-box
   diagonal).
5. **Write** ``<stem>.landmarks.json`` with :func:`face3d.io.landmarks.save_landmarks`:
   scheme ``mediapipe_478``; detector ``{backend: 'mediapipe-tasks', version,
   model_sha256, licence, commercial_ok: null, is_ml: true}``; **all** faces with
   their scores and blendshapes, in MediaPipe's order -- the engine or the user
   picks the subject (eth F1); nothing here chooses a face.  The Tasks API
   reports no per-face confidence, so ``score`` is the fraction of TTA passes in
   which the face was found (1.0 without TTA).  MediaPipe returns all 478 points
   even when occluded, so ``visible`` only marks finite points; the engine's
   visibility weighting decides (DESIGN 4.8).  The facial transformation
   matrices go to a sidecar ``<stem>.mediapipe_extras.json`` (not used by the
   engine).  ``--png-out`` also writes the oriented image as a PNG working copy
   (:func:`face3d.io.png.write_png`; no EXIF is carried over).

Outputs are biometric geometry of the photographed person (DESIGN 3.3,
D-25): keep them in the project's session cache and never commit them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, NamedTuple, Sequence

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from face3d.io.image_ops import flip_uv  # noqa: E402
from face3d.io.landmarks import Face, LandmarkSet, save_landmarks  # noqa: E402
from face3d.io.png import write_png  # noqa: E402
from face3d.model.registry import load_scheme  # noqa: E402

#: Long side of the image handed to the detector (WP-14 spec).
DETECT_LONG_SIDE_PX = 2048
#: TTA jitter: uniform scale 1 +/- 2 % and shift +/- 1 % of the image size (WP-14 spec; 🆕 provisional).
TTA_SCALE_FRAC = 0.02
TTA_SHIFT_FRAC = 0.01
#: Default number of TTA passes (plain + 6 jittered + 1 flip; WP-14 CLI).
DEFAULT_TTA = 8
#: Normal consistency constant of the MAD (1 / Phi^-1(3/4)).
MAD_TO_SIGMA = 1.4826
#: Face matching gate across TTA passes, fraction of the plain-pass bbox diagonal (🆕 provisional).
FACE_MATCH_GATE = 0.25
#: Licence string recorded with every detection (ethics README licence table; scheme detector block).
DETECTOR_LICENCE = "Apache-2.0 (code); model weights: verify per release (contested)"
HEIF_SUFFIXES = (".heic", ".heif", ".hif")


class Refused(RuntimeError):
    """An input fails a check (model hash, HEIC without pillow-heif, scheme size)."""


# ----------------------------------------------------------------- model and image
def read_verified_model(path: str | Path, expected_sha256: str) -> bytes:
    """Read the ``.task`` file and refuse unless its SHA-256 equals ``expected_sha256`` (eth F15)."""
    exp = str(expected_sha256).strip().lower()
    if len(exp) != 64 or any(c not in "0123456789abcdef" for c in exp):
        raise Refused("--model-sha256 must be 64 hex digits")
    data = Path(path).read_bytes()
    got = hashlib.sha256(data).hexdigest()
    if got != exp:
        raise Refused(f"model SHA-256 mismatch: file has {got}, expected {exp}; refusing to load it")
    return data


def detection_size(W: int, H: int, long_side: int = DETECT_LONG_SIDE_PX) -> tuple[int, int]:
    """(W', H') with max(W', H') <= long_side (unchanged when already small enough)."""
    s = long_side / float(max(W, H))
    if s >= 1.0:
        return int(W), int(H)
    return max(1, int(round(W * s))), max(1, int(round(H * s)))


def load_oriented_rgb(path: Path, Image: Any, ImageOps: Any) -> tuple[np.ndarray, dict[str, Any]]:
    """Open with Pillow, bake the EXIF orientation, return (uint8 RGB (H, W, 3), info)."""
    heif = path.suffix.lower() in HEIF_SUFFIXES
    if heif:
        try:
            import pillow_heif  # type: ignore[import-not-found]
        except ImportError:
            raise Refused(f"{path.name}: HEIC/HEIF needs pillow-heif in this Python; "
                          "install it or convert the photo to PNG") from None
        pillow_heif.register_heif_opener()
    with Image.open(path) as im:
        try:
            exif_orientation = int(im.getexif().get(0x0112, 1))
        except Exception:  # pragma: no cover - exotic files
            exif_orientation = None
        # HEIF: the decoder applies irot/imir/clap and EXIF Orientation is ignored (DESIGN 3.1)
        im2 = im if heif else ImageOps.exif_transpose(im)
        rgb = np.asarray(im2.convert("RGB"), dtype=np.uint8).copy()
    return rgb, {"exif_orientation": exif_orientation,
                 "orientation_source": "heif_transforms" if heif else "exif_orientation"}


def resize_rgb(rgb: np.ndarray, W2: int, H2: int, Image: Any) -> np.ndarray:
    """Pillow bilinear resize (corner-consistent scaling u' = u W'/W)."""
    if rgb.shape[1] == W2 and rgb.shape[0] == H2:
        return rgb
    im = Image.fromarray(rgb)
    resample = getattr(getattr(Image, "Resampling", Image), "BILINEAR")
    return np.asarray(im.resize((W2, H2), resample=resample), dtype=np.uint8)


# ----------------------------------------------------------------- augmentation
class Aug(NamedTuple):
    """One TTA pass: ``kind`` 'plain' | 'jitter' | 'flip'; jitter maps q = s (p - c) + c + t."""

    kind: str
    scale: float = 1.0
    shift: tuple[float, float] = (0.0, 0.0)


def tta_plan(n_passes: int, W: int, H: int, rng: np.random.Generator) -> list[Aug]:
    """Pass list: plain, then n-2 jittered similarities, then one horizontal flip (n >= 2)."""
    if n_passes <= 1:
        return [Aug("plain")]
    plan = [Aug("plain")]
    for _ in range(n_passes - 2):
        s = 1.0 + float(rng.uniform(-TTA_SCALE_FRAC, TTA_SCALE_FRAC))
        t = (float(rng.uniform(-TTA_SHIFT_FRAC, TTA_SHIFT_FRAC)) * W,
             float(rng.uniform(-TTA_SHIFT_FRAC, TTA_SHIFT_FRAC)) * H)
        plan.append(Aug("jitter", s, t))
    plan.append(Aug("flip"))
    return plan


def _axis_weights(n: int, scale: float, shift: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Bilinear source indices/weights along one axis for q = s (p - c) + c + t (pixel centres)."""
    c = n / 2.0
    q = np.arange(n) + 0.5
    p = (q - c - shift) / scale + c          # continuous source coordinate, corner origin
    x = p - 0.5                              # source pixel-index space
    i0 = np.floor(x).astype(np.int64)
    w = x - i0
    inside = (x >= -0.5) & (x <= n - 0.5)
    i0c = np.clip(i0, 0, n - 1)
    i1c = np.clip(i0 + 1, 0, n - 1)
    return i0c, i1c, w, inside


def apply_aug(rgb: np.ndarray, aug: Aug) -> np.ndarray:
    """Augmented copy of ``rgb`` (same size): exact similarity resampling or a horizontal flip."""
    if aug.kind == "plain":
        return rgb
    if aug.kind == "flip":
        return np.ascontiguousarray(rgb[:, ::-1])
    H, W = rgb.shape[:2]
    x0, x1, wx, inx = _axis_weights(W, aug.scale, aug.shift[0])
    y0, y1, wy, iny = _axis_weights(H, aug.scale, aug.shift[1])
    img = rgb.astype(np.float32)
    rows = img[y0] * (1.0 - wy)[:, None, None] + img[y1] * wy[:, None, None]
    out = rows[:, x0] * (1.0 - wx)[None, :, None] + rows[:, x1] * wx[None, :, None]
    out *= (iny[:, None] & inx[None, :])[:, :, None]
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def map_back(xy: np.ndarray, aug: Aug, W: int, H: int, Wd: int, Hd: int, perm: np.ndarray,
             mirror_known: np.ndarray) -> np.ndarray:
    """Normalised detections of one pass -> original-image pixels (N, 2), corner convention.

    ``W, H``: original oriented size; ``Wd, Hd``: detection size.  The plain pass is
    exactly ``(x W, y H)``.  Flip-pass labels are permuted by ``perm`` and points
    without a known mirror are NaN.
    """
    xy = np.asarray(xy, np.float64)[:, :2]
    if aug.kind == "plain":
        return np.stack([xy[:, 0] * W, xy[:, 1] * H], axis=1)
    q = xy * np.array([Wd, Hd], float)                     # detection pixels of the augmented image
    if aug.kind == "jitter":
        c = np.array([Wd / 2.0, Hd / 2.0])
        p = (q - c - np.asarray(aug.shift)) / aug.scale + c
    elif aug.kind == "flip":
        p = flip_uv(q, Wd, perm)
        p[~mirror_known] = np.nan
    else:
        raise ValueError(f"unknown augmentation {aug.kind!r}")
    return p * np.array([W / float(Wd), H / float(Hd)])


def robust_spread(stack: np.ndarray, median: np.ndarray) -> np.ndarray:
    """1.4826 x median radial deviation from the per-point median; NaN with < 2 finite passes."""
    dev = np.linalg.norm(stack - median[None], axis=2)      # (P, N), NaN where missing
    ok = np.isfinite(dev)
    out = np.full(stack.shape[1], np.nan)
    cnt = ok.sum(axis=0)
    has = cnt >= 2
    if has.any():
        out[has] = MAD_TO_SIGMA * np.nanmedian(dev[:, has], axis=0)
    return out


def _centroid_and_diag(uv: np.ndarray) -> tuple[np.ndarray, float]:
    ok = np.all(np.isfinite(uv), axis=1)
    if not ok.any():
        return np.array([np.nan, np.nan]), 0.0
    p = uv[ok]
    return p.mean(axis=0), float(np.linalg.norm(p.max(axis=0) - p.min(axis=0)))


def combine_passes(passes: list[list[np.ndarray]]) -> list[tuple[np.ndarray, list[np.ndarray]]]:
    """Group per-pass face arrays by the plain-pass faces (greedy centroid matching).

    Returns, per plain-pass face, ``(uv_plain, [uv of each pass or None])``.
    """
    base = passes[0]
    groups: list[list[np.ndarray | None]] = [[b] + [None] * (len(passes) - 1) for b in base]
    stats = [_centroid_and_diag(b) for b in base]
    for k in range(1, len(passes)):
        cands = [_centroid_and_diag(c)[0] for c in passes[k]]
        used: set[int] = set()
        for fi, (cb, diag) in enumerate(stats):
            best, best_d = None, np.inf
            for j, cc in enumerate(cands):
                d = float(np.linalg.norm(cc - cb))
                if j not in used and np.isfinite(d) and d < best_d:
                    best, best_d = j, d
            if best is not None and best_d <= FACE_MATCH_GATE * max(diag, 1e-9):
                used.add(best)
                groups[fi][k] = passes[k][best]
    return [(b, g) for b, g in zip(base, groups)]


def nanmedian_passes(stack: np.ndarray) -> np.ndarray:
    """Per-point, per-coordinate median over passes ignoring NaN (all-NaN -> NaN, no warning)."""
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmedian(stack, axis=0)


# ----------------------------------------------------------------- detector glue
def make_landmarker(mp: Any, model_bytes: bytes, num_faces: int) -> Any:
    """FaceLandmarker (Tasks API) in IMAGE mode with blendshapes and transformation matrices."""
    vision = mp.tasks.vision
    options = vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_buffer=model_bytes),
        running_mode=vision.RunningMode.IMAGE,
        num_faces=int(num_faces),
        output_face_blendshapes=True,
        output_facial_transformation_matrixes=True,
    )
    return vision.FaceLandmarker.create_from_options(options)


def run_detector(mp: Any, landmarker: Any, rgb: np.ndarray, n_expected: int) -> list[dict[str, Any]]:
    """One detector call -> ``[{xy (N, 2) normalised, blendshapes, matrix}]`` in MediaPipe's face order."""
    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
    res = landmarker.detect(image)
    faces = []
    blends = list(getattr(res, "face_blendshapes", None) or [])
    mats = list(getattr(res, "facial_transformation_matrixes", None) or [])
    for i, lms in enumerate(getattr(res, "face_landmarks", None) or []):
        xy = np.array([[float(p.x), float(p.y)] for p in lms], dtype=np.float64).reshape(-1, 2)
        if len(xy) != n_expected:
            raise Refused(f"detector returned {len(xy)} points but the scheme expects {n_expected}; "
                          "the scheme is never inferred from the point count")
        bs = None
        if i < len(blends) and blends[i] is not None:
            bs = {str(c.category_name): float(c.score) for c in blends[i]}
        mat = None
        if i < len(mats) and mats[i] is not None:
            mat = np.asarray(mats[i], dtype=np.float64).reshape(4, 4).tolist()
        faces.append({"xy": xy, "blendshapes": bs, "matrix": mat})
    return faces


def detect_image(path: Path, *, mp: Any, landmarker: Any, Image: Any, ImageOps: Any, scheme: Any,
                 n_tta: int, rng: np.random.Generator, detector: dict[str, Any]
                 ) -> tuple[LandmarkSet, np.ndarray, list[Any]]:
    """Detect one photo; returns (LandmarkSet, oriented RGB, per-face transformation matrices)."""
    raw = Path(path).read_bytes()
    rgb, info = load_oriented_rgb(Path(path), Image, ImageOps)
    H, W = rgb.shape[:2]
    Wd, Hd = detection_size(W, H)
    det_rgb = resize_rgb(rgb, Wd, Hd, Image)
    perm = scheme.mirror_permutation()
    sides = np.array(scheme.sides())
    paired = perm != np.arange(scheme.n)
    mirror_known = paired | (sides == "mid")
    plan = tta_plan(n_tta, Wd, Hd, rng)
    passes: list[list[np.ndarray]] = []
    base_meta: list[dict[str, Any]] = []
    for k, aug in enumerate(plan):
        faces = run_detector(mp, landmarker, apply_aug(det_rgb, aug), scheme.n)
        if k == 0:
            base_meta = faces
        passes.append([map_back(f["xy"], aug, W, H, Wd, Hd, perm, mirror_known) for f in faces])
    out_faces = []
    matrices = []
    for (uv_plain, per_pass), meta in zip(combine_passes(passes), base_meta):
        found = [u for u in per_pass if u is not None]
        score = len(found) / float(len(plan))
        if len(plan) > 1:
            stack = np.stack([u if u is not None else np.full_like(uv_plain, np.nan) for u in per_pass])
            uv = nanmedian_passes(stack)
            spread = robust_spread(stack, uv)
        else:
            uv, spread = uv_plain, None
        visible = np.all(np.isfinite(uv), axis=1)
        out_faces.append(Face(score=score, uv=uv, visible=visible, cov=None, tta_spread_px=spread,
                              blendshapes=meta["blendshapes"]))
        matrices.append(meta["matrix"])
    image = {"sha256": hashlib.sha256(raw).hexdigest(), "wh": [int(W), int(H)], "orientation_applied": True,
             "input_flipped": False, "coords": "px_corner", "detect_wh": [int(Wd), int(Hd)],
             "exif_orientation": info["exif_orientation"], "orientation_source": info["orientation_source"]}
    ls = LandmarkSet(scheme=scheme.scheme, detector=dict(detector), image=image, faces=out_faces)
    return ls, rgb, matrices


# ----------------------------------------------------------------- CLI
def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--model", type=Path, required=True, help="FaceLandmarker .task file (user-supplied)")
    ap.add_argument("--model-sha256", required=True, help="expected SHA-256 of the .task file (hex)")
    ap.add_argument("--images", type=Path, nargs="+", required=True, help="photos (JPEG/PNG; HEIC with pillow-heif)")
    ap.add_argument("--out", type=Path, required=True, help="output directory")
    ap.add_argument("--tta", type=int, default=DEFAULT_TTA, help="TTA passes incl. plain and flip (0/1 = off)")
    ap.add_argument("--num-faces", type=int, default=2, help="maximum faces per photo (all are written)")
    ap.add_argument("--png-out", action="store_true", help="also write oriented PNG working copies")
    ap.add_argument("--seed", type=int, default=0, help="seed of the TTA jitter")
    ap.add_argument("--scheme", default="mediapipe_478", help="scheme id (default mediapipe_478)")
    ap.add_argument("--scheme-path", type=Path, default=None, help="scheme JSON or directory (default: package)")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        model_bytes = read_verified_model(args.model, args.model_sha256)
    except (Refused, OSError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    import mediapipe as mp  # user-installed; imported only here
    from PIL import Image, ImageOps  # user-installed; imported only here

    scheme = load_scheme(args.scheme, args.scheme_path)
    detector = {"backend": "mediapipe-tasks", "version": str(getattr(mp, "__version__", "unknown")),
                "model_sha256": hashlib.sha256(model_bytes).hexdigest(), "licence": DETECTOR_LICENCE,
                "commercial_ok": None, "is_ml": True, "running_mode": "IMAGE", "num_faces": int(args.num_faces),
                "detect_long_side_px": DETECT_LONG_SIDE_PX,
                "tta": {"passes": max(1, int(args.tta)), "seed": int(args.seed), "scale_frac": TTA_SCALE_FRAC,
                        "shift_frac": TTA_SHIFT_FRAC, "flip": int(args.tta) >= 2,
                        "spread": "1.4826 * median radial deviation from the per-point median"}}
    args.out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(int(args.seed))
    landmarker = make_landmarker(mp, model_bytes, args.num_faces)
    failures = 0
    used_stems: set[str] = set()
    try:
        for path in args.images:
            stem = path.stem
            k = 1
            while stem in used_stems:
                k += 1
                stem = f"{path.stem}-{k}"
            used_stems.add(stem)
            try:
                ls, rgb, matrices = detect_image(path, mp=mp, landmarker=landmarker, Image=Image, ImageOps=ImageOps,
                                                 scheme=scheme, n_tta=int(args.tta), rng=rng, detector=detector)
            except (Refused, OSError) as e:
                print(f"skipped {path.name}: {e}", file=sys.stderr)
                failures += 1
                continue
            out_json = args.out / f"{stem}.landmarks.json"
            save_landmarks(ls, out_json)
            extras = {"format": "face3d.mediapipe_extras", "version": 1, "landmarks": out_json.name,
                      "note": "FaceLandmarker facial transformation matrices (one per face, MediaPipe order); "
                              "not used by the engine",
                      "faces": [{"facial_transformation_matrix": m} for m in matrices]}
            (args.out / f"{stem}.mediapipe_extras.json").write_text(json.dumps(extras, indent=1, sort_keys=True))
            if args.png_out:
                write_png(args.out / f"{stem}.png", rgb)
            print(f"{path.name}: {len(ls.faces)} face(s) -> {out_json.name}")
    finally:
        close = getattr(landmarker, "close", None)
        if callable(close):
            close()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
