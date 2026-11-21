"""Focal-length and camera-distance prior ladders (DESIGN 4.2; rec CAM-5, CAM-6; com R2.2, R2.4).

Every photo gets a log-normal prior on its focal length in pixels and on its
camera distance, chosen by the *first matching rule* of a ladder ordered from the
strongest to the weakest evidence. All numbers are engineering judgement (🧠) or
new to this design (🆕), registered below as badged defaults under the ``focal``
namespace (``face3d.core.config``), overridable through ``cfg`` (the output of
``config.resolve``) and recalibrated in M7.

Focal ladder (:func:`focal_prior_from_evidence`; DESIGN 4.2 table, CAM-6, com R2.2,
research note smartphone-camera-pipeline "Zoom detector" / "Native frame"):

  1. SfM import or calibration (f in px given) .......... sigma 0.01  'sfm' / 'calibrated'
  2. EXIF f35 with digital zoom: DigitalZoomRatio > 1, or
     f35/FocalLength > 1.02 x the focal group's mode ratio  sigma 0.06  'zoom'
  3. EXIF f35 with a non-native aspect (1 % tolerance) ... sigma 0.09  'aspect'
  4. EXIF f35 otherwise ................................. sigma 0.04  'exif_f35'
  5. FocalLength + focal-plane resolution (ExifInfo.focal_px)
                                                          sigma 0.10  'focal_plane'
  6. phone without focal data: 26 mm-eq ................. sigma 0.25  'phone'
  7. nothing: 50 mm-eq .................................. sigma 0.6   'nothing'

f_px = f35 * hypot(W, H) / 43.2666 (diagonal convention, ``focal_px_from_35mm``;
com R2.6 / CAM-2, contested ↔️: ≈4 % from the width convention).

Distance ladder (:func:`distance_prior`; DESIGN 4.2, CAM-6, com R2.4): returns the
median camera-to-face distance in mm and sigma of ln z: taped (taped, 50/taped);
front camera (350, 0.3); tele f35 >= 70 mm (2000, 0.4); rear phone or known camera
(800, 0.4); unknown (1000, 0.7). :func:`distance_prior_head_origin` refers it to
the head origin (mid-tragion), HEAD_ORIGIN_OFFSET_MM = 100 mm behind the face.
The distance prior is never derived from IOD pixels (that would double-count the
scale prior; DESIGN 4.2).

Units: f in pixels, f35 in 35 mm-equivalent mm, distances in mm, sigmas on the
natural log.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, NamedTuple

from ..core.config import Default, register_defaults
from ..geometry.camera import focal_px_from_35mm
from ..io.exif import ExifInfo

_BRAIN = "\U0001F9E0"   # expert knowledge, provisional
_NEW = "\U0001F195"     # introduced by this design, uncalibrated
_ARROWS = "↔️"          # contested
_D42 = "DESIGN 4.2 "

FOCAL_DEFAULTS = register_defaults("focal", {
    # --- focal ladder (sigma on ln f) ---
    "sigma_log_calibrated": Default(0.01, _BRAIN, _D42 + "SfM/calibration 0.005-0.02 (rec CAM-6)", "ln f",
                                    (0.0, 5.0)),
    "sigma_log_zoom": Default(0.06, _BRAIN, _D42 + "EXIF f35, zoom crop (smartphone-camera-pipeline 'Zoom detector')",
                              "ln f", (0.0, 5.0)),
    "sigma_log_aspect": Default(0.09, _BRAIN, _D42 + "EXIF f35, aspect crop (smartphone-camera-pipeline "
                                "'Native frame')", "ln f", (0.0, 5.0)),
    "sigma_log_exif": Default(0.04, _BRAIN, _D42 + "EXIF f35, uncropped (rec CAM-6; smartphone-camera-pipeline "
                              "'Intrinsics')", "ln f", (0.0, 5.0)),
    "sigma_log_focal_plane": Default(0.10, _BRAIN, _D42 + "FocalLength + focal-plane resolution (com R2.2 "
                                     "'physical focal length' 0.10)", "ln f", (0.0, 5.0)),
    "phone_f35_mm": Default(26.0, _BRAIN, _D42 + "phone, no focal data: 26 mm (com R2.2 [RD])", "mm",
                            (1.0, 2000.0)),
    "sigma_log_phone": Default(0.25, _BRAIN, _D42 + "phone, no focal data: sigma 0.25 (com R2.2 [RD])", "ln f",
                               (0.0, 5.0)),
    "nothing_f35_mm": Default(50.0, _BRAIN, _D42 + "nothing known: 50 mm (com R2.2 [RD][ZB]; rec CAM-6)", "mm",
                              (1.0, 2000.0)),
    "sigma_log_nothing": Default(0.6, _BRAIN, _D42 + "nothing known: sigma 0.6 (com R2.2; rec CAM-6 0.5-0.7)",
                                 "ln f", (0.0, 5.0)),
    "zoom_ratio_factor": Default(1.02, _BRAIN, "DESIGN 4.1 Q-CROP / smartphone-camera-pipeline 'Zoom detector': "
                                 "f35/FocalLength > 1.02 x group mode", "", (1.0, 10.0)),
    "aspect_rel_tol": Default(0.01, _NEW, "WP-06 (c): an aspect within 1 % of a native one counts as native",
                              "", (0.0, 0.5)),
    # --- distance ladder (median camera-to-face distance, sigma on ln z) ---
    "distance_front_mm": Default(350.0, _BRAIN, _D42 + "front camera 0.35 m (rec CAM-6 selfie)", "mm",
                                 (50.0, 100000.0)),
    "sigma_log_distance_front": Default(0.3, _BRAIN, _D42 + "front camera sigma 0.3 (rec CAM-6)", "ln z",
                                        (0.0, 5.0)),
    "distance_tele_mm": Default(2000.0, _BRAIN, _D42 + "tele 2 m (rec CAM-6)", "mm", (50.0, 100000.0)),
    "sigma_log_distance_tele": Default(0.4, _BRAIN, _D42 + "tele sigma 0.4 (rec CAM-6)", "ln z", (0.0, 5.0)),
    "tele_f35_min_mm": Default(70.0, _NEW, "WP-06 (c): f35 >= 70 mm counts as tele for the distance prior", "mm",
                               (1.0, 2000.0)),
    "distance_rear_mm": Default(800.0, _BRAIN, _D42 + "rear phone / known camera 0.8 m (rec CAM-6 handheld rear)",
                                "mm", (50.0, 100000.0)),
    "sigma_log_distance_rear": Default(0.4, _BRAIN, _D42 + "rear sigma 0.4 (rec CAM-6)", "ln z", (0.0, 5.0)),
    "distance_unknown_mm": Default(1000.0, _BRAIN, _D42 + "unknown 1.0 m (com R2.4 [RPP][ZB])", "mm",
                                   (50.0, 100000.0)),
    "sigma_log_distance_unknown": Default(0.7, _BRAIN, _D42 + "unknown sigma 0.7 (com R2.4)", "ln z",
                                          (0.0, 5.0)),
    "tape_sigma_mm": Default(50.0, _BRAIN, _D42 + "taped distance +-5 cm (com R2.4 'tape z sigma 5 cm')", "mm",
                             (0.0, 10000.0)),
    "head_origin_offset_mm": Default(100.0, _ARROWS, _D42 + "face distance + 100 mm to the head origin; "
                                     "metric-3d-landmark-reference Table 2 tragion depth 90-120, nominal 100 "
                                     "(n' 94/88, prn 119/111 mm in front of tragion)", "mm", (0.0, 300.0)),
})

#: Distance from the face (the photographed surface) back to the head origin at
#: mid-tragion, mm (DESIGN 4.2; metric-3d-landmark-reference: nominal 100, range 90-120 ↔️).
HEAD_ORIGIN_OFFSET_MM = float(FOCAL_DEFAULTS.head_origin_offset_mm.value)

#: EXIF Make prefixes treated as phone makers when ``is_phone`` is not given
#: (WP-06 (c) list; matched case-insensitively at the start of Make). "Sony mobile"
#: matches "Sony Mobile Communications" but not Sony's camera Make "SONY".
PHONE_MAKERS = ("apple", "samsung", "google", "xiaomi", "oneplus", "huawei", "oppo", "vivo", "sony mobile")

#: Native still aspects (W:H) accepted by default (WP-06 (c)); 16:9 is included so
#: video stills and 16:9 camera modes are not flagged as crops (provisional).
DEFAULT_NATIVE_ASPECTS = ((4, 3), (3, 4), (3, 2), (2, 3), (16, 9), (9, 16))


def _cfg_value(key: str, cfg: Mapping[str, Any] | None = None) -> Any:
    """Resolved value of ``focal.<key>`` from ``cfg`` (``core.config.resolve`` output) or the default."""
    if cfg:
        v = cfg.get("focal." + key)
        if v is not None:
            return v
    return FOCAL_DEFAULTS[key].value


@dataclass
class FocalPrior:
    """Log-normal focal prior: ln f ~ N(ln f_px, log_sigma^2); f in pixels.

    ``source_code`` names the ladder rule that fired: 'sfm', 'calibrated', 'zoom',
    'aspect', 'exif_f35', 'focal_plane', 'phone' or 'nothing'.
    """
    f_px: float
    log_sigma: float
    source_code: str


class DistancePrior(NamedTuple):
    """Log-normal distance prior, a 2-tuple (median_mm, sigma_log): ln z ~ N(ln median_mm, sigma_log^2)."""
    median_mm: float
    sigma_log: float


def is_phone_make(make: str | None) -> bool:
    """True when EXIF Make starts with one of :data:`PHONE_MAKERS` (case-insensitive)."""
    if not make:
        return False
    m = " ".join(make.strip().lower().split())
    return any(m.startswith(p) for p in PHONE_MAKERS)


def aspect_is_native(width: int, height: int,
                     native_aspects=DEFAULT_NATIVE_ASPECTS, rel_tol: float = 0.01) -> bool:
    """True when W/H is within ``rel_tol`` (relative) of some a/b in ``native_aspects``."""
    if width <= 0 or height <= 0:
        return False
    r = float(width) / float(height)
    return any(abs(r / (a / b) - 1.0) <= rel_tol for a, b in native_aspects)


def focal_prior_from_evidence(exif: ExifInfo | None, width: int, height: int, *,
                              sfm_f_px: float | None = None, calibrated_f_px: float | None = None,
                              is_phone: bool | None = None,
                              native_aspects=DEFAULT_NATIVE_ASPECTS,
                              group_crop_ratio_mode: float | None = None,
                              cfg: Mapping[str, Any] | None = None) -> FocalPrior:
    """Focal prior for a W x H image (as delivered, orientation applied) by the first matching rule.

    Parameters
    ----------
    exif : parsed EXIF (``face3d.io.exif.ExifInfo``) or None.
    width, height : delivered image size in pixels.
    sfm_f_px, calibrated_f_px : focal in pixels from an SfM import or a calibration
        (rule 1; SfM wins when both are given).
    is_phone : overrides the Make-based phone test (:func:`is_phone_make`).
    native_aspects : W:H pairs counted as uncropped (rule 3 fires when none is
        within ``focal.aspect_rel_tol``, 1 %).
    group_crop_ratio_mode : mode of f35/FocalLength over the photo's focal group
        (same Make/Model/LensModel); rule 2 fires when this photo's ratio exceeds
        it by ``focal.zoom_ratio_factor`` (1.02). None skips that test.
    cfg : resolved config overrides (``core.config.resolve``).
    """
    if sfm_f_px is not None:
        return FocalPrior(float(sfm_f_px), float(_cfg_value("sigma_log_calibrated", cfg)), "sfm")
    if calibrated_f_px is not None:
        return FocalPrior(float(calibrated_f_px), float(_cfg_value("sigma_log_calibrated", cfg)), "calibrated")
    f35 = exif.focal_35mm if exif is not None else None
    if f35:
        f_px = focal_px_from_35mm(float(f35), width, height)
        dz = exif.digital_zoom_ratio
        zoom = dz is not None and dz > 1.0
        if not zoom and group_crop_ratio_mode and exif.focal_length_mm:
            ratio = float(f35) / float(exif.focal_length_mm)
            zoom = ratio > float(_cfg_value("zoom_ratio_factor", cfg)) * float(group_crop_ratio_mode)
        if zoom:
            return FocalPrior(f_px, float(_cfg_value("sigma_log_zoom", cfg)), "zoom")
        if not aspect_is_native(width, height, native_aspects, float(_cfg_value("aspect_rel_tol", cfg))):
            return FocalPrior(f_px, float(_cfg_value("sigma_log_aspect", cfg)), "aspect")
        return FocalPrior(f_px, float(_cfg_value("sigma_log_exif", cfg)), "exif_f35")
    if exif is not None:
        f_fp = exif.focal_px(width, height)
        if f_fp:
            return FocalPrior(float(f_fp), float(_cfg_value("sigma_log_focal_plane", cfg)), "focal_plane")
    phone = is_phone if is_phone is not None else (exif is not None and is_phone_make(exif.make))
    if phone:
        return FocalPrior(focal_px_from_35mm(float(_cfg_value("phone_f35_mm", cfg)), width, height),
                          float(_cfg_value("sigma_log_phone", cfg)), "phone")
    return FocalPrior(focal_px_from_35mm(float(_cfg_value("nothing_f35_mm", cfg)), width, height),
                      float(_cfg_value("sigma_log_nothing", cfg)), "nothing")


def _known_camera(exif: ExifInfo | None) -> bool:
    return exif is not None and bool(exif.make or exif.model or exif.focal_35mm or exif.focal_length_mm)


def distance_prior(exif: ExifInfo | None, *, is_front_camera: bool | None = None,
                   taped_mm: float | None = None, cfg: Mapping[str, Any] | None = None) -> DistancePrior:
    """Camera-to-face distance prior (median_mm, sigma_log) by the first matching rule (DESIGN 4.2).

    1. taped distance: (taped_mm, 50 / taped_mm), i.e. +-5 cm on z (com R2.4);
    2. front camera (``is_front_camera``, else ``ExifInfo.is_front_camera``): (350, 0.3);
    3. tele, EXIF f35 >= 70 mm: (2000, 0.4);
    4. rear phone or known camera (any of Make/Model/f35/FocalLength): (800, 0.4);
    5. unknown: (1000, 0.7).
    """
    if taped_mm is not None:
        taped = float(taped_mm)
        if not taped > 0:
            raise ValueError(f"taped_mm must be > 0; got {taped_mm!r}")
        return DistancePrior(taped, float(_cfg_value("tape_sigma_mm", cfg)) / taped)
    front = is_front_camera if is_front_camera is not None else (exif is not None and exif.is_front_camera)
    if front:
        return DistancePrior(float(_cfg_value("distance_front_mm", cfg)),
                             float(_cfg_value("sigma_log_distance_front", cfg)))
    if exif is not None and exif.focal_35mm and exif.focal_35mm >= float(_cfg_value("tele_f35_min_mm", cfg)):
        return DistancePrior(float(_cfg_value("distance_tele_mm", cfg)),
                             float(_cfg_value("sigma_log_distance_tele", cfg)))
    if _known_camera(exif):
        return DistancePrior(float(_cfg_value("distance_rear_mm", cfg)),
                             float(_cfg_value("sigma_log_distance_rear", cfg)))
    return DistancePrior(float(_cfg_value("distance_unknown_mm", cfg)),
                         float(_cfg_value("sigma_log_distance_unknown", cfg)))


def distance_prior_head_origin(exif: ExifInfo | None, *, is_front_camera: bool | None = None,
                               taped_mm: float | None = None,
                               cfg: Mapping[str, Any] | None = None) -> DistancePrior:
    """Distance prior referred to the head origin (mid-tragion): the offset is added before the log.

    Returns (median_face_mm + HEAD_ORIGIN_OFFSET_MM, sigma_log). The population
    rules keep their sigma on ln z (DESIGN 4.2 states the sigmas on log z of the
    head-origin distance); a taped distance keeps its absolute +-5 cm, so its
    sigma becomes 50 / (taped + offset).
    """
    off = float(_cfg_value("head_origin_offset_mm", cfg))
    med, sig = distance_prior(exif, is_front_camera=is_front_camera, taped_mm=taped_mm, cfg=cfg)
    if taped_mm is not None:
        return DistancePrior(med + off, float(_cfg_value("tape_sigma_mm", cfg)) / (med + off))
    return DistancePrior(med + off, sig)


def focal_group_key(exif: ExifInfo | None, width: int, height: int, still: bool = True) -> str | None:
    """Focal-group key (Make|Model|LensModel|f35|W|H|still/video; rec CAM-5) or None.

    Delegates to ``ExifInfo.focal_group_key``. Video frames always form their own
    group, separate from stills (the key ends in 'video'). Returns None (the photo
    is ungrouped: its focal prior acts on it alone, DESIGN 4.3) when there is no
    EXIF or the EXIF names neither Make, Model nor f35 (Q-EXIF-NONE): grouping
    such photos by size alone would tie unrelated cameras.
    """
    if exif is None or not (exif.make or exif.model or exif.focal_35mm):
        return None
    return exif.focal_group_key(width, height, still=still)
