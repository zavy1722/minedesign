"""Fault generators for the fault-injection matrix (DESIGN 7.4; WP-11).

Every generator is deterministic given its inputs (and the caller's seeded
``numpy.random.Generator`` where one is taken) and returns the faulted data
together with a ground-truth label dict ``truth`` (at least ``{'fault': name,
'expect': ...}``) so that a harness (WP-23 ``tests/test_fault_matrix.py``) can
score detections, decisions and degradations against the clean run.
Inputs are never modified in place.

:data:`FAULT_MATRIX` lists one entry per generator configuration and covers
every row of the DESIGN 7.4 table (``design_row`` is the table's first column,
verbatim); the DESIGN targets are 🆕 (uncalibrated) and are copied, not
invented, here.

Conventions: image coordinates are continuous pixels with the origin at the
top-left corner (DESIGN 3.1); cameras are :class:`face3d.geometry.camera.Camera`
(OpenCV); world units are mm.  ``perm`` arguments are a scheme's L/R label
permutation (:meth:`face3d.model.registry.Scheme.mirror_permutation`).
"""
from __future__ import annotations

import functools
import math
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from ..core.config import Default, register_defaults
from ..geometry.camera import Camera, stereographic_project
from ..io.image_ops import flip_uv, orientation_point_map
from ..synthetic import orbit_camera
from .rigs import EXIF_PRIOR_LOG_SIGMA, IMAGE_H, IMAGE_W, NO_EXIF_LOG_SIGMA, PITCH_RANGE_DEG, SELFIE_F35, Rig
from .surface_subjects import SurfaceSubject, expression_field

__all__ = [
    "mirror_view", "unbaked_orientation", "exif_crop", "exif_missing", "selfie_rig", "expression_fault",
    "beauty_warp", "beauty_index_map", "off_axis_wide", "OffAxisView", "occluder_fault", "small_face",
    "face_width_px", "gross_outliers", "definition_bias", "FAULT_MATRIX", "ALARM_BUDGET", "FAULT_DEFAULTS",
    "design_fault_rows",
]

_NEW = "\U0001F195"
_BRAIN = "\U0001F9E0"
_D74 = "DESIGN 7.4 fault-injection matrix (targets 🆕)"
_WP = "WBS WP-11 spec"

FAULT_DEFAULTS = register_defaults("testbed.faults", {
    "exif_crop_factor": Default(1.3, _NEW, _D74 + ": EXIF +/-30 % crop", "", (0.1, 10.0)),
    "selfie_distance_mm": Default(350.0, _BRAIN, "DESIGN 4.2 front-camera distance prior 0.35 m; "
                                  + _D74 + " 'Selfies at 0.35 m'", "mm", (50.0, 5000.0)),
    "selfie_yaw_max_deg": Default(30.0, _NEW, "face3d.testbed.rigs selfie yaw U(-30, 30) (WP-01)", "deg",
                                  (0.0, 90.0)),
    "beauty_eye_scale": Default(1.06, _NEW, _D74 + ": beauty warp eyes +6 %", "", (0.5, 2.0)),
    "beauty_jaw_scale": Default(0.96, _NEW, _D74 + ": beauty warp jaw -4 %", "", (0.5, 2.0)),
    "off_axis_theta_deg": Default(35.0, _NEW, "DESIGN D-12 (J2 check at 35 deg); " + _WP, "deg", (0.0, 89.0)),
    "small_face_px": Default(150.0, _NEW, _D74 + ": 'Face 150 px'", "px", (1.0, 10000.0)),
    "outlier_frac": Default(0.05, _NEW, _D74 + ": '5 % gross outliers'", "", (0.0, 1.0)),
    "outlier_min_sigma": Default(5.0, _NEW, "DESIGN 7.2 detector simulator: outliers at 5-20 sigma", "",
                                 (0.0, 1000.0)),
    "outlier_max_sigma": Default(20.0, _NEW, "DESIGN 7.2 detector simulator: outliers at 5-20 sigma", "",
                                 (0.0, 1000.0)),
    "definition_bias_mm": Default(1.0, _NEW, _D74 + ": 'Definition bias 1 mm'", "mm", (0.0, 50.0)),
    "glasses_eye_sigma_mult": Default(2.0, _BRAIN, "DESIGN 4.1 occluder tags: glasses -> eye sigma x2 "
                                      "[Rob 3.6]", "", (1.0, 100.0)),
    "makeup_sigma_mult": Default(2.0, _BRAIN, "DESIGN 4.1 occluder tags: makeup -> lip and brow borders "
                                 "sigma x2 [Rob 3.6]", "", (1.0, 100.0)),
})
_F = {k: FAULT_DEFAULTS[k].value for k in FAULT_DEFAULTS}

_FLIP = np.array([-1.0, 1.0, 1.0])


def _truth(fault: str, expect: Any, **kw: Any) -> dict:
    d = {"fault": fault, "expect": expect}
    d.update(kw)
    return d


# =========================================================================== mirror / orientation
def mirror_view(uv: np.ndarray, W: float, perm: Sequence[int]) -> tuple[np.ndarray, dict]:
    """A horizontally mirrored photo's landmarks: ``out[perm[i]] = (W - u_i, v_i)`` (DESIGN 3.1).

    Uses :func:`face3d.io.image_ops.flip_uv`; with an involutive L/R permutation the
    fault is an involution (applying it twice gives the input back exactly).
    Truth ``{'truth': 'mirrored', 'mirrored': True, 'expect': 'suggest_flip'}``
    (DESIGN 4.10: the engine may only *suggest* a flip).
    """
    out = flip_uv(np.asarray(uv, float), float(W), perm)
    return out, _truth("mirror", "suggest_flip", truth="mirrored", mirrored=True,
                       perm=[int(p) for p in perm], width=float(W))


def unbaked_orientation(uv: np.ndarray, W: int, H: int, o: int = 6) -> tuple[np.ndarray, tuple[int, int], dict]:
    """Landmarks detected on the *stored* (orientation-not-baked) image (DESIGN 4.1 Q-ORIENT).

    ``uv`` are displayed-frame coordinates of a ``W x H`` displayed image.  The stored
    image of EXIF orientation ``o`` is ``(H, W)`` for o in 5..8 and ``(W, H)``
    otherwise; the stored-frame landmarks are ``orientation_point_map(o, Ws, Hs).inverse(uv)``
    (:mod:`face3d.io.image_ops`).  Returns ``(uv_stored, (Ws, Hs), truth)``; applying
    ``orientation_point_map(o, Ws, Hs)`` to ``uv_stored`` gives ``uv`` back.
    """
    o = int(o)
    Ws, Hs = (int(H), int(W)) if o in (5, 6, 7, 8) else (int(W), int(H))
    fwd = orientation_point_map(o, Ws, Hs)
    if fwd.out_wh != (int(W), int(H)):
        raise ValueError(f"orientation {o}: stored {Ws}x{Hs} does not display as {W}x{H}")
    out = fwd.inverse(np.asarray(uv, float))
    return out, (Ws, Hs), _truth("orientation_unbaked", "Q-ORIENT", orientation=o, orientation_applied=False,
                                 displayed_wh=[int(W), int(H)], stored_wh=[Ws, Hs])


# =========================================================================== EXIF and rigs
def exif_crop(f_prior_px: float, factor: float = _F["exif_crop_factor"]) -> tuple[dict, dict]:
    """A focal prior made wrong by an undetected crop: ``f_prior_px * factor`` (DESIGN 7.4, +/-30 %).

    The declared log-sigma stays at the uncropped-EXIF value 0.04 (DESIGN 4.2): the
    fault is that the evidence looks normal.  Returns
    ``({'f_prior_px', 'f_prior_log_sigma'}, truth)`` with ``truth['f_true_px']``.
    """
    f = float(f_prior_px)
    k = float(factor)
    if not (f > 0 and k > 0):
        raise ValueError("f_prior_px and factor must be positive")
    return ({"f_prior_px": f * k, "f_prior_log_sigma": EXIF_PRIOR_LOG_SIGMA},
            _truth("exif_crop", "C-FOCAL-PRIOR when focal is unobservable", factor=k, f_true_px=f))


def exif_missing() -> tuple[dict, dict]:
    """No EXIF focal at all: prior ``None`` with log-sigma 0.6 (DESIGN 4.2 'Nothing' row)."""
    return ({"f_prior_px": None, "f_prior_log_sigma": NO_EXIF_LOG_SIGMA},
            _truth("exif_missing", "C-FOCAL-PRIOR when focal is unobservable"))


@functools.lru_cache(maxsize=1)
def _default_face_target() -> tuple[float, float, float]:
    from ..model.procedural_head import build_procedural_head
    from .render import face_centre

    return tuple(float(v) for v in face_centre(build_procedural_head()))


def selfie_rig(rng: np.random.Generator, n_views: int = 3, *, target: Sequence[float] | None = None,
               distance_mm: float = _F["selfie_distance_mm"], width: int = IMAGE_W,
               height: int = IMAGE_H) -> tuple[Rig, dict]:
    """Front-camera selfies at 0.35 m (DESIGN 7.4 'Selfies at 0.35 m'; Q-NEAR, tier <= B).

    ``n_views`` cameras from :func:`face3d.synthetic.orbit_camera` at ``distance_mm``
    (camera centre to the face centre ``target``) with one shared f35 ~ U(22, 30),
    yaw ~ U(-30, 30) and pitch ~ U(-8, 8) degrees (the WP-01 selfie protocol), front
    camera, focal group ``'front'``, EXIF prior = true focal with log-sigma 0.04.
    ``target`` defaults to the face centre (eye/nose/mouth landmark centroid) of the
    default procedural kit (FH frame, origin mid-tragion).
    Draw order: f35, then (yaw, pitch) per view.
    """
    tgt = _default_face_target() if target is None else tuple(float(v) for v in target)
    f35 = float(rng.uniform(*SELFIE_F35))
    ym = _F["selfie_yaw_max_deg"]
    cams, yaws, pitches = [], [], []
    for _ in range(int(n_views)):
        yaw = float(rng.uniform(-ym, ym))
        pitch = float(rng.uniform(*PITCH_RANGE_DEG))
        cams.append(orbit_camera(float(distance_mm), yaw, pitch, f35, width=int(width), height=int(height),
                                 target=tgt))
        yaws.append(yaw)
        pitches.append(pitch)
    n = len(cams)
    rig = Rig(name="selfie_near", cameras=cams, f_prior_px=[float(c.f) for c in cams],
              f_prior_log_sigma=[EXIF_PRIOR_LOG_SIGMA] * n, focal_group=["front"] * n,
              is_front_camera=[True] * n, view_yaw_deg=yaws, view_pitch_deg=pitches,
              distance_mm=[float(distance_mm)] * n, target=tgt)
    return rig, _truth("selfie_near", ["Q-NEAR", "tier<=B"], distance_mm=float(distance_mm), f35=f35,
                       mirror="unverifiable")


# =========================================================================== expression
def expression_fault(subject: SurfaceSubject, view_index: int, kind: str, amount: float,
                     n_views: int = 5) -> tuple[list[np.ndarray], dict]:
    """Per-view vertex arrays with one expressive view (DESIGN 7.4 'Jaw 5-15 deg, smile in 1 of 5').

    Returns ``(Vs, truth)``: ``Vs[k]`` is ``subject.V_true`` (neutral) for every view
    except ``view_index``, which carries :func:`expression_field` ``(kind, amount)``.
    ``truth['model_matched']`` is True for ``jaw_open`` only.
    """
    n = int(n_views)
    if not 0 <= int(view_index) < n:
        raise ValueError(f"view_index must be in [0, {n}), got {view_index}")
    Vx, meta = expression_field(subject.kit, subject.V_true, kind, amount, return_meta=True)
    Vs = [subject.V_true.copy() for _ in range(n)]
    Vs[int(view_index)] = Vx
    return Vs, _truth("expression", "expressive", view=int(view_index), kind=kind, amount=float(amount),
                      units=meta["units"], model_matched=meta["model_matched"],
                      neutral_views=[k for k in range(n) if k != int(view_index)])


# =========================================================================== beauty warp
def _base_side(name: str) -> tuple[str | None, str | None]:
    from ..model.registry import ANATOMICAL_IDS, BASE_NAMES

    long_to_base = {v: k for k, v in BASE_NAMES.items()}
    side = None
    stem = name
    if name.endswith("_L") or name.endswith("_R"):
        stem, side = name[:-2], name[-1]
    if stem in BASE_NAMES:
        base = stem
    else:
        base = long_to_base.get(stem)
    if base is None:
        return None, side
    if side is None and base not in ANATOMICAL_IDS:
        return None, None
    return base, side


def beauty_index_map(names: Sequence[str], kinds: Sequence[str] | None = None) -> dict:
    """Index map for :func:`beauty_warp` from scheme point names.

    Works with anatomical ids (``'en_L'``) and the legacy long names
    (``'endocanthion_L'``).  ``eyes[side]`` = eye-corner and lid points (en, ex, ps, pi)
    of that side, ``eye_centres[side]`` = the pupil (p) index or None, ``jaw`` = gonion,
    gnathion, menton and pogonion plus every point of kind ``'contour'`` (if ``kinds``),
    ``face_centre`` = None (centroid of all finite points).
    """
    eyes: dict[str, list[int]] = {"L": [], "R": []}
    centres: dict[str, int | None] = {"L": None, "R": None}
    jaw: list[int] = []
    for i, nm in enumerate(names):
        base, side = _base_side(str(nm))
        if base in ("en", "ex", "ps", "pi") and side in ("L", "R"):
            eyes[side].append(i)
        elif base == "p" and side in ("L", "R"):
            centres[side] = i
        elif base in ("go", "gn", "me", "pg"):
            jaw.append(i)
        elif kinds is not None and kinds[i] == "contour":
            jaw.append(i)
    return {"eyes": eyes, "eye_centres": centres, "jaw": sorted(jaw), "face_centre": None}


def beauty_warp(uv: np.ndarray, scheme_index_map: dict, eye_scale: float = _F["beauty_eye_scale"],
                jaw_scale: float = _F["beauty_jaw_scale"]) -> tuple[np.ndarray, dict]:
    """Beauty-filter warp of one view's landmarks (DESIGN 7.4 'eyes +6 %, jaw -4 %'; Q-RETOUCH).

    Eye-corner/lid points of each eye are scaled by ``eye_scale`` about that eye's
    centre (the pupil when given and finite, else the centroid of the eye's points);
    jaw/contour points move toward the face centre (centroid of the ``face_centre``
    indices, default all finite points, taken *before* the warp) by
    ``p' = c + jaw_scale (p - c)``.  Hence eye widths scale by exactly ``eye_scale``
    and the bigonial width by exactly ``jaw_scale``.  NaN rows stay NaN.
    """
    uv = np.asarray(uv, float)
    out = uv.copy()
    moved = np.zeros(len(uv), bool)
    fc_idx = scheme_index_map.get("face_centre")
    ref = uv if fc_idx is None else uv[np.asarray(fc_idx, np.int64)]
    fin = np.isfinite(ref).all(axis=1)
    if not fin.any():
        raise ValueError("no finite points to define the face centre")
    fc = ref[fin].mean(axis=0)
    for side in ("L", "R"):
        idx = np.asarray(scheme_index_map["eyes"].get(side, []), np.int64)
        if idx.size == 0:
            continue
        ok = idx[np.isfinite(uv[idx]).all(axis=1)]
        if ok.size == 0:
            continue
        ci = scheme_index_map.get("eye_centres", {}).get(side)
        c = uv[ci] if ci is not None and np.isfinite(uv[ci]).all() else uv[ok].mean(axis=0)
        out[ok] = c + float(eye_scale) * (uv[ok] - c)
        moved[ok] = True
    jaw = np.asarray(scheme_index_map.get("jaw", []), np.int64)
    if jaw.size:
        ok = jaw[np.isfinite(uv[jaw]).all(axis=1)]
        out[ok] = fc + float(jaw_scale) * (uv[ok] - fc)
        moved[ok] = True
    return out, _truth("beauty_warp", "Q-RETOUCH", eye_scale=float(eye_scale), jaw_scale=float(jaw_scale),
                       moved=moved, face_centre_px=fc.tolist())


# =========================================================================== off-axis wide angle
def _rotation_between(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Minimal rotation taking unit vector a onto unit vector b (Rodrigues)."""
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v = np.cross(a, b)
    s = float(np.linalg.norm(v))
    c = float(a @ b)
    if s < 1e-15:
        if c > 0:
            return np.eye(3)
        raise ValueError("cannot rotate a direction onto its opposite")
    k = v / s
    K = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    ang = math.atan2(s, c)
    return np.eye(3) + math.sin(ang) * K + (1.0 - math.cos(ang)) * (K @ K)


@dataclass
class OffAxisView:
    """A view whose face sits ``theta_deg`` off the optical axis (DESIGN D-12, 4.3).

    camera : the rotated camera (same centre and intrinsics as the input camera).
    model : ``'stereographic'`` (phone face-warp correction: the image is a
        stereographic projection about the principal point,
        :func:`face3d.geometry.camera.stereographic_project`) or ``'rectilinear'``
        (plain pinhole).
    """

    camera: Camera
    model: str
    theta_deg: float
    azimuth_deg: float
    X_centre: np.ndarray

    def project(self, X: np.ndarray) -> np.ndarray:
        """World points (N, 3) -> faulted image coordinates (N, 2) under ``model``."""
        X = np.asarray(X, float).reshape(-1, 3)
        if self.model == "stereographic":
            c = self.camera
            return stereographic_project(c.to_camera(X), c.f, c.cx, c.cy)
        return self.camera.project(X)


def off_axis_wide(camera: Camera, X_centre: Sequence[float], theta_deg: float = _F["off_axis_theta_deg"],
                  model: str = "stereographic", *, azimuth_deg: float | None = None) -> tuple[OffAxisView, dict]:
    """Rotate ``camera`` about its centre so the face centre sits ``theta_deg`` off-axis (Q-WIDE).

    The face ray is rotated (minimal rotation) onto the camera-frame direction
    ``(sin t cos a, sin t sin a, cos t)``; ``azimuth_deg`` ``a`` is measured in the image
    from +u toward +v and defaults to the longer image axis (+v for portrait, +u for
    landscape).  The face centre must stay inside the frame under the chosen model
    (otherwise ValueError: use a wider lens).  Returns ``(OffAxisView, truth)``;
    ``truth['expected_model']`` is ``'virtual_stereo'`` for stereographic and
    ``'pinhole'`` for rectilinear (DESIGN 3.2 camera ``model``), ``truth['f_local_px']``
    the local magnification at the face (``f sec^2(theta/2)`` stereographic, ``f``
    for the rectilinear rotation homography; DESIGN D-12).
    """
    if model not in ("stereographic", "rectilinear"):
        raise ValueError(f"model must be 'stereographic' or 'rectilinear', not {model!r}")
    th = math.radians(float(theta_deg))
    if azimuth_deg is None:
        azimuth_deg = 90.0 if camera.height >= camera.width else 0.0
    az = math.radians(float(azimuth_deg))
    Xc = np.asarray(X_centre, float).reshape(3)
    d = camera.to_camera(Xc[None])[0]
    if d[2] <= 0:
        raise ValueError("the face centre is behind the camera")
    e = np.array([math.sin(th) * math.cos(az), math.sin(th) * math.sin(az), math.cos(th)])
    Q = _rotation_between(d, e)
    cam = camera.copy()
    cam.R = Q @ camera.R
    cam.t = Q @ camera.t
    view = OffAxisView(camera=cam, model=model, theta_deg=float(theta_deg), azimuth_deg=float(azimuth_deg),
                       X_centre=Xc.copy())
    uv = view.project(Xc[None])[0]
    if not (0.0 <= uv[0] <= cam.width and 0.0 <= uv[1] <= cam.height):
        raise ValueError(f"face centre leaves the {cam.width}x{cam.height} frame at {theta_deg} deg "
                         f"(uv {uv.round(1).tolist()}); use a wider lens")
    f_local = cam.f / math.cos(th / 2.0) ** 2 if model == "stereographic" else cam.f
    return view, _truth("off_axis_wide", "Q-WIDE", model=model,
                        expected_model="virtual_stereo" if model == "stereographic" else "pinhole",
                        theta_deg=float(theta_deg), azimuth_deg=float(azimuth_deg), f_local_px=float(f_local),
                        face_centre_uv=uv.tolist())


# =========================================================================== occluders
_EYE_BASES = ("en", "ex", "ps", "pi")
_IRIS_BASES = ("p",)
_BEARD_BASES = ("pg", "gn", "me", "go")
_HAIR_BASES = ("t", "sa", "sba", "tr")
_HAIR_LEGACY = ("forehead_side",)          # legacy temple point
_LIP_BASES = ("ls", "li", "sto", "ch")


def occluder_fault(tags: Sequence[str], *, names: Sequence[str] | None = None, uv: np.ndarray | None = None,
                   kinds: Sequence[str] | None = None) -> tuple[dict, dict]:
    """Occluder-tag fault (DESIGN 4.1 occluder tags, 7.4 'Beard / glasses / hair tags').

    Class-level actions come from :func:`face3d.qa.checks.occluder_actions` (the same
    table the engine applies), resolved to point indices when ``names`` is given:

    * ``beard``: drop the chin/jaw observations (pg, gn, me, go); emit an
      ``outer_bound`` contour flag for the jaw outline (the outline is kept as a
      bound, DESIGN 4.1); expected jaw status ``prior-driven``;
    * ``glasses``: eye-corner/lid noise x2 (``noise_multiplier``), iris points dropped
      (no iris scale);
    * ``hair``: ear (t, sa, sba), trichion and temple points dropped; no silhouette
      above trichion; expected 'scalp inside hull';
    * ``makeup``: lip and brow points noise x2.

    Returns ``(effect, truth)`` with ``effect = {'actions', 'drop' (N,) bool,
    'noise_multiplier' (N,), 'contour_flags', 'uv' (dropped rows NaN, if uv given)}``.
    """
    from ..qa.checks import occluder_actions

    tags = sorted(set(str(t) for t in tags))
    unknown = set(tags) - {"beard", "glasses", "hair", "makeup"}
    if unknown:
        raise ValueError(f"unknown occluder tags {sorted(unknown)}")
    actions = occluder_actions(tags)
    contour_flags = []
    expect: dict[str, Any] = {}
    if "beard" in tags:
        contour_flags.append({"region": "jaw", "kind": "outer_bound"})
        expect["jaw_status"] = "prior-driven"
        expect["contour_kind"] = "outer_bound"
    if "glasses" in tags:
        expect["no_iris_scale"] = True
        expect["eye_sigma_mult"] = _F["glasses_eye_sigma_mult"]
    if "hair" in tags:
        expect["scalp_inside_hull"] = True
        expect["no_silhouette_above"] = "trichion"
    effect: dict[str, Any] = {"actions": actions, "contour_flags": contour_flags}
    if names is not None:
        n = len(names)
        drop = np.zeros(n, bool)
        mult = np.ones(n)
        for i, nm in enumerate(names):
            base, _side = _base_side(str(nm))
            stem = str(nm)[:-2] if str(nm).endswith(("_L", "_R")) else str(nm)
            kind = None if kinds is None else kinds[i]
            if "beard" in tags and base in _BEARD_BASES:
                drop[i] = True          # the jaw outline itself is kept, as an outer_bound contour
            if "glasses" in tags:
                if base in _IRIS_BASES or kind == "iris":
                    drop[i] = True
                elif base in _EYE_BASES:
                    mult[i] *= _F["glasses_eye_sigma_mult"]
            if "hair" in tags and (base in _HAIR_BASES or stem in _HAIR_LEGACY):
                drop[i] = True
            if "makeup" in tags and (base in _LIP_BASES or kind == "brow" or stem.startswith("brow")):
                mult[i] *= _F["makeup_sigma_mult"]
        effect["drop"] = drop
        effect["noise_multiplier"] = mult
        if uv is not None:
            u = np.asarray(uv, float).copy()
            if len(u) != n:
                raise ValueError("uv and names must have the same length")
            u[drop] = np.nan
            effect["uv"] = u
    return effect, _truth("occluder", expect, tags=tags)


# =========================================================================== small face
def face_width_px(camera: Camera, X: np.ndarray, pair: Sequence[int] | None = None) -> float:
    """Face width in pixels: image distance between ``X[pair]`` (e.g. zy_L, zy_R), or the
    horizontal extent ``max u - min u`` of the projected points when ``pair`` is None
    (com R1.4 'face < 250 px wide')."""
    uv = camera.project(np.asarray(X, float).reshape(-1, 3))
    if pair is not None:
        a, b = int(pair[0]), int(pair[1])
        return float(np.linalg.norm(uv[a] - uv[b]))
    return float(uv[:, 0].max() - uv[:, 0].min())


def small_face(rig_view: Camera, face_px: float = _F["small_face_px"], *, X: np.ndarray,
               pair: Sequence[int] | None = None, max_iter: int = 50) -> tuple[Camera, dict]:
    """Move ``rig_view`` back along its optical axis until the face is ``face_px`` wide (Q-SMALL).

    ``X`` (N, 3) are the face points defining the width (:func:`face_width_px`);
    orientation and intrinsics are kept, so the face shrinks toward the principal
    point.  Solved by the fixed point ``D <- D w(D) / face_px`` on the camera-frame
    depth D of the points' centroid (relative error < 1e-9).  Raises ValueError if
    the face is already smaller than ``face_px`` (moving back cannot enlarge it).
    """
    X = np.asarray(X, float).reshape(-1, 3)
    target = float(face_px)
    w0 = face_width_px(rig_view, X, pair)
    if w0 < target:
        raise ValueError(f"face is already {w0:.1f} px < {target} px wide")
    axis = rig_view.R[2]                      # optical axis in world coordinates
    c = X.mean(axis=0)
    C0 = rig_view.center
    D0 = float(rig_view.depth(c[None])[0])
    cam = rig_view.copy()
    D = D0
    for _ in range(int(max_iter)):
        cam.t = -cam.R @ (C0 - (D - D0) * axis)
        w = face_width_px(cam, X, pair)
        if abs(w - target) <= 1e-9 * target:
            break
        D = D * w / target
    w = face_width_px(cam, X, pair)
    return cam, _truth("small_face", "Q-SMALL", face_px=w, target_face_px=target, distance_mm=D,
                       moved_back_mm=D - D0)


# =========================================================================== outliers / bias
def gross_outliers(uv: np.ndarray, frac: float, rng: np.random.Generator,
                   sigma_px: float | np.ndarray) -> tuple[np.ndarray, dict]:
    """Replace ``round(frac * n_finite)`` observations by gross outliers (DESIGN 7.4 '5 % gross outliers').

    The chosen rows (uniform without replacement among finite rows) are displaced by
    ``U(5, 20) * sigma_px`` in a uniform random direction (DESIGN 7.2: outliers at
    5-20 sigma).  ``sigma_px`` is a scalar or per-point (N,).  Draw order: indices,
    magnitudes, angles.  ``truth['outlier_mask']`` marks the displaced rows.
    """
    uv = np.asarray(uv, float)
    n = len(uv)
    fin = np.flatnonzero(np.isfinite(uv).all(axis=1))
    k = int(round(float(frac) * fin.size))
    sig = np.broadcast_to(np.asarray(sigma_px, float), (n,))
    idx = np.sort(rng.choice(fin, size=k, replace=False)) if k > 0 else np.zeros(0, np.int64)
    mag = rng.uniform(_F["outlier_min_sigma"], _F["outlier_max_sigma"], size=k) * sig[idx]
    ang = rng.uniform(0.0, 2.0 * math.pi, size=k)
    out = uv.copy()
    out[idx] += mag[:, None] * np.column_stack([np.cos(ang), np.sin(ang)])
    mask = np.zeros(n, bool)
    mask[idx] = True
    return out, _truth("gross_outliers", "rejection", outlier_mask=mask, magnitude_px=mag.tolist(),
                       frac=float(frac))


def definition_bias(X: np.ndarray, rng: np.random.Generator,
                    sigma_mm: float = _F["definition_bias_mm"]) -> tuple[np.ndarray, dict]:
    """Per-landmark definition bias shared by all views (DESIGN D-06, 7.4 'Definition bias 1 mm').

    ``X + b`` with ``b ~ N(0, sigma_mm^2 I3)`` per landmark, drawn once; project the
    result in every view.  ``truth['bias_3d']`` is ``b`` (N, 3).
    """
    X = np.asarray(X, float)
    b = rng.normal(scale=float(sigma_mm), size=X.shape)
    return X + b, _truth("definition_bias", "NEES/dof with sigma_rep in [0.8, 1.25]", bias_3d=b,
                         sigma_mm=float(sigma_mm))


# =========================================================================== matrix
def _row(name, design_row, generator, kwargs, level, must_raise, metric, threshold, degradation_bound,
         design_must_raise, design_required, design_degradation, sampling=None):
    return {"name": name, "design_row": design_row, "generator": generator, "generator_name": generator.__name__,
            "kwargs": dict(kwargs), "sampling": dict(sampling or {}), "level": level, "must_raise": must_raise,
            "metric": metric, "threshold": dict(threshold), "degradation_bound": degradation_bound, "badge": _NEW,
            "design_must_raise": design_must_raise, "design_required": design_required,
            "design_degradation": design_degradation}


_ROW_MIRROR = "1 mirrored view among ≥ 3"
_ROW_ORIENT = "Orientation not baked"
_ROW_EXIF = "EXIF ±30 % crop or missing"
_ROW_SELFIE = "Selfies at 0.35 m"
_ROW_EXPR = "Jaw 5–15°, smile in 1 of 5"
_ROW_BEAUTY = "Beauty warp (eyes +6 %, jaw −4 %)"
_ROW_WIDE = "Off-axis wide-angle (stereographic and rectilinear)"
_ROW_OCCL = "Beard / glasses / hair tags"
_ROW_SMALL = "Face 150 px"
_ROW_OUTL = "5 % gross outliers"
_ROW_BIAS = "Definition bias 1 mm"

#: One entry per fault configuration; together they cover every DESIGN 7.4 row.
#: Keys: name, design_row (DESIGN 7.4 first column, verbatim), generator (callable in this
#: module), generator_name, kwargs (fixed keyword arguments of the generator), sampling
#: (per-seed draws the harness makes and passes as keyword arguments:
#: ``{param: {'uniform': [lo, hi]}}`` or ``{param: {'choice': [...]}}``), level
#: ('landmark' | 'surface' | 'image' | 'camera'),
#: must_raise (finding / decision / tag code, or None when the row only has a metric),
#: metric, threshold, degradation_bound (dict or None), badge (🆕: DESIGN targets are
#: uncalibrated), and the DESIGN cells verbatim (design_must_raise, design_required,
#: design_degradation).
FAULT_MATRIX: list[dict] = [
    _row("mirror", _ROW_MIRROR, mirror_view, {}, "landmark", "suggest_flip", "mirror_decision_rates",
         {"tpr_min": 0.95, "asym_rms_mm_min": 0.8, "fpr_max": 0.02, "undetermined_when_symmetric_min": 0.9,
          "min_views": 3},
         {"shape_rms_ratio_max": 1.1, "after": "user confirms the flip"},
         "suggest flip", "TPR ≥ 0.95 at ≥ 0.8 mm asymmetry; FPR ≤ 0.02; `undetermined` ≥ 0.9 when symmetric",
         "shape ≤ 1.1× clean after user confirms"),
    _row("orientation_unbaked", _ROW_ORIENT, unbaked_orientation, {"o": 6}, "landmark", "Q-ORIENT", "tpr",
         {"tpr_min": 0.99}, None, "Q-ORIENT", "TPR ≥ 0.99", "—"),
    _row("exif_crop", _ROW_EXIF, exif_crop, {}, "camera", "C-FOCAL-PRIOR", "focal_rel_err",
         {"focal_rel_err_max": 0.05, "when_yaw_span_deg_min": 60.0, "raise_when": "focal unobservable"},
         {"shape_rms_ratio_max": 1.2}, "C-FOCAL-PRIOR when unobservable",
         "focal < 5 % when views span ≥ 60° (com R8.4)", "≤ 1.2× clean",
         sampling={"factor": {"choice": [0.7, 1.3]}}),
    _row("exif_missing", _ROW_EXIF, exif_missing, {}, "camera", "C-FOCAL-PRIOR", "focal_rel_err",
         {"focal_rel_err_max": 0.05, "when_yaw_span_deg_min": 60.0, "raise_when": "focal unobservable"},
         {"shape_rms_ratio_max": 1.2}, "C-FOCAL-PRIOR when unobservable",
         "focal < 5 % when views span ≥ 60° (com R8.4)", "≤ 1.2× clean"),
    _row("selfie_near", _ROW_SELFIE, selfie_rig, {"n_views": 3}, "camera", "Q-NEAR", "distance_rel_err",
         {"distance_rel_err_max": 0.15, "tier_max": "B"}, None, "Q-NEAR, tier ≤ B", "z within 15 %", "—"),
    _row("jaw_open", _ROW_EXPR, expression_fault, {"kind": "jaw_open", "n_views": 5},
         "surface", "expressive", "expression_tag_tpr", {"tpr_min": 0.9},
         {"neutral_identity_shift_mm_max": 0.3, "hard": True}, "expressive tag", "TPR ≥ 0.9",
         "neutral identity moved < 0.3 mm (hard)",
         sampling={"amount": {"uniform": [5.0, 15.0]}, "view_index": {"choice": [0, 1, 2, 3, 4]}}),
    # Smile amplitude U(2, 4) mm around the 3 mm of the WP-15 hard-gate test (DESIGN gives none; 🆕).
    _row("smile", _ROW_EXPR, expression_fault, {"kind": "smile", "n_views": 5},
         "surface", "expressive", "expression_tag_tpr", {"tpr_min": 0.9},
         {"neutral_identity_shift_mm_max": 0.3, "hard": True}, "expressive tag", "TPR ≥ 0.9",
         "neutral identity moved < 0.3 mm (hard)",
         sampling={"amount": {"uniform": [2.0, 4.0]}, "view_index": {"choice": [0, 1, 2, 3, 4]}}),
    _row("beauty_warp", _ROW_BEAUTY, beauty_warp, {"eye_scale": 1.06, "jaw_scale": 0.96}, "landmark",
         "Q-RETOUCH", "retouch_tpr", {"tpr_min": 0.8, "min_clean_views": 3},
         {"identity_bias_mm_max": 0.5}, "Q-RETOUCH", "TPR ≥ 0.8 with ≥ 3 clean views", "identity bias ≤ 0.5 mm"),
    _row("off_axis_stereographic", _ROW_WIDE, off_axis_wide, {"theta_deg": 35.0, "model": "stereographic"},
         "camera", "Q-WIDE", "camera_model_accuracy", {"correct_model_min": 0.8, "expected_model": "virtual_stereo"},
         {"shape_extra_mm_max": 1.0}, "Q-WIDE + correct model", "model chosen correctly ≥ 0.8", "shape < 1 mm extra"),
    _row("off_axis_rectilinear", _ROW_WIDE, off_axis_wide, {"theta_deg": 35.0, "model": "rectilinear"},
         "camera", "Q-WIDE", "camera_model_accuracy", {"correct_model_min": 0.8, "expected_model": "pinhole"},
         {"shape_extra_mm_max": 1.0}, "Q-WIDE + correct model", "model chosen correctly ≥ 0.8", "shape < 1 mm extra"),
    _row("beard", _ROW_OCCL, occluder_fault, {"tags": ["beard"]}, "landmark", None, "tag_actions",
         {"jaw_status": "prior-driven", "contour_kind": "outer_bound"}, None, "tag actions",
         "beard → jaw prior-driven", "scalp inside hull"),
    _row("glasses", _ROW_OCCL, occluder_fault, {"tags": ["glasses"]}, "landmark", None, "tag_actions",
         {"no_iris_scale": True, "eye_sigma_mult": 2.0}, None, "tag actions", "beard → jaw prior-driven",
         "scalp inside hull"),
    _row("hair", _ROW_OCCL, occluder_fault, {"tags": ["hair"]}, "surface", None, "tag_actions",
         {"no_silhouette_above": "trichion"}, {"scalp_inside_hull": True}, "tag actions",
         "beard → jaw prior-driven", "scalp inside hull"),
    _row("small_face", _ROW_SMALL, small_face, {"face_px": 150.0}, "image", "Q-SMALL", "coverage_1s",
         {"coverage_holds": True, "coverage_1s_range": [0.60, 0.76]}, None, "Q-SMALL", "coverage holds", "—"),
    _row("gross_outliers", _ROW_OUTL, gross_outliers, {"frac": 0.05}, "landmark", None, "outlier_rejection",
         {"caught_min": 0.95, "inliers_lost_max": 0.02}, {"shape_rms_ratio_max": 1.1}, "rejection",
         "≥ 95 % caught, ≤ 2 % inliers lost", "≤ 1.1× clean"),
    _row("definition_bias", _ROW_BIAS, definition_bias, {"sigma_mm": 1.0}, "landmark", None, "nees_per_dof",
         {"nees_per_dof_range": [0.8, 1.25], "with": "sigma_rep"}, None, "—",
         "NEES/dof with σ_rep in [0.8, 1.25]", "—"),
]

#: DESIGN 7.4 alarm budget: at most 1 spurious warn/block finding per 10 clean photos (🆕).
ALARM_BUDGET: dict = {"max_spurious_findings_per_photo": 0.1, "severities": ["warn", "block"], "badge": _NEW}


def design_fault_rows(design_md: str) -> list[str]:
    """First-column cells of the DESIGN 7.4 fault table (helper for completeness checks)."""
    rows: list[str] = []
    inside = False
    for line in design_md.splitlines():
        if line.startswith("### 7.4"):
            inside = True
            continue
        if inside and line.startswith("### "):
            break
        if inside and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not cells or cells[0] in ("Fault",) or set(cells[0]) <= set("-: "):
                continue
            rows.append(cells[0])
    return rows
