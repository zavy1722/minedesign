"""Photo QA findings (DESIGN 4.1 table; numpy + stdlib).

Units: pixels for image quantities, millimetres for distances, degrees for
angles, focal in 35 mm-equivalent mm (f35). Image arrays are float in [0, 1]
(uint8 is rescaled). No gate pulls a value toward a norm (DESIGN 4.1): each
returns a Finding naming a down-weight / drop / exclude / ask action.

Every threshold is registered in ``core.config`` under namespace ``qa`` with a
badge and source taken from DESIGN 4.1 (brain = engineering judgement there).
Q-RETOUCH: only the pre-BA parts are here (editor named in Software is covered
by Q-PROCESS; the smoothness-index test is ``retouch_findings``); the post-BA
eye/jaw residual pattern belongs to WP-15.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

from face3d.core.config import Default, register_defaults
from face3d.qa import image_stats as ims

_B = "\U0001F9E0"   # engineering judgement
_NEW = "\U0001F195"
_T = "DESIGN 4.1 "

QA = register_defaults("qa", {
    "near_warn_mm": Default(1000.0, _B, _T + "Q-NEAR (com §9)", "mm", (100.0, 10000.0)),
    "near_strong_mm": Default(800.0, _B, _T + "Q-NEAR (com §9)", "mm", (100.0, 10000.0)),
    "near_exclude_mm": Default(600.0, _B, _T + "Q-NEAR (com §9)", "mm", (100.0, 10000.0)),
    "wide_f35_mm": Default(16.0, _B, _T + "Q-WIDE (com R1.7; thresholds judgement)", "mm", (1.0, 100.0)),
    "wide_radius_frac": Default(0.6, _B, _T + "Q-WIDE: fraction of the half-diagonal", "", (0.1, 1.0)),
    "wide_off_axis_deg": Default(25.0, _B, _T + "Q-WIDE: off-axis angle", "deg", (1.0, 89.0)),
    "sigma_logf_zoom": Default(0.06, _B, _T + "Q-CROP / §4.2 (smartphone-camera-pipeline)", "ln f", (0.0, 2.0)),
    "sigma_logf_aspect": Default(0.09, _B, _T + "Q-CROP / §4.2 (smartphone-camera-pipeline)", "ln f", (0.0, 2.0)),
    "zoom_ratio_min": Default(1.0, _B, _T + "Q-CROP: DigitalZoomRatio above this is a crop", "", (1.0, 10.0)),
    "zoom_group_mode_ratio": Default(1.02, _B, _T + "Q-CROP: f35/FocalLength above this x the group mode", "", (1.0, 10.0)),
    "aspect_tol": Default(0.02, _B, _T + "Q-CROP: relative aspect difference counted as non-native", "", (0.0, 0.5)),
    "small_warn_px": Default(250.0, _B, _T + "Q-SMALL (com R1.4)", "px", (10.0, 5000.0)),
    "small_block_px": Default(120.0, _B, _T + "Q-SMALL (com R1.4)", "px", (10.0, 5000.0)),
    "iris_min_px": Default(20.0, _B, _T + "Q-SMALL: iris scale needs this many px", "px", (1.0, 200.0)),
    "blink_ear": Default(0.2, _B, _T + "Q-BLINK (bl §10)", "", (0.0, 1.0)),
    "clip_level": Default(0.98, _B, _T + "Q-CLIP", "", (0.5, 1.0)),
    "clip_fraction": Default(0.02, _B, _T + "Q-CLIP (> 2 % of skin)", "", (0.0, 1.0)),
    "faces_score": Default(0.6, "\U0001F4C4", _T + "Q-FACES (eth F1)", "", (0.0, 1.0)),
    "orient_sigma": Default(3.0, _B, _T + "Q-ORIENT: view RMS in sigma (bl §10)", "sigma", (0.0, 100.0)),
    "orient_roll_tol_deg": Default(15.0, _B, _T + "Q-ORIENT: roll within this of 90/270", "deg", (0.0, 45.0)),
    "blur_ratio": Default(0.6, _B, _T + "Q-BLUR: Laplacian variance vs set median", "", (0.0, 1.0)),
    "dates_gap_days": Default(548.0, _B, _T + "Q-DATES: 18 months (com §9)", "days", (1.0, 36500.0)),
    "group_f35_spread": Default(0.05, _B, _T + "Q-GROUP-SPREAD (CAM-5)", "", (0.0, 1.0)),
    "retouch_ratio": Default(0.5, _NEW, _T + "Q-RETOUCH smoothness index vs set median", "", (0.0, 1.0)),
})

# Native still aspects (long/short). Phones are 4:3 native (smartphone-camera-pipeline
# 'Native frame'; 3:2, 16:9 and 1:1 crops are non-native). Other cameras: 4:3 or 3:2.
PHONE_MAKES = ("apple", "samsung", "google", "huawei", "xiaomi", "oneplus", "oppo", "vivo",
               "motorola", "sony mobile", "honor", "realme", "nothing", "asus", "nokia")
NATIVE_ASPECTS_PHONE = (4.0 / 3.0,)
NATIVE_ASPECTS_OTHER = (4.0 / 3.0, 3.0 / 2.0)

EDITOR_NAMES = ("photoshop", "lightroom", "snapseed", "facetune", "meitu", "faceapp",
                "gimp", "picsart", "vsco", "instagram")


@dataclass
class Finding:
    code: str
    severity: str            # 'info' | 'warn' | 'block'
    value: object
    threshold: object
    action: str              # down_weight|drop_class|exclude_geometry|exclude_texture|ask|none
    msg_key: str
    fix_key: str
    source: str
    badge: str
    photo_id: str | None = None
    detail: dict | None = None   # extra structured data (e.g. date-cluster ids)


@dataclass
class PhotoContext:
    photo_id: str
    exif: object | None = None
    heif: object | None = None
    width: int = 0
    height: int = 0
    orientation_applied: bool = True
    landmarks_uv: object | None = None
    scheme: str | None = None
    face_px: float | None = None
    face_centre_px: object | None = None
    iris_px: float | None = None
    image_gray: object | None = None
    skin_mask: object | None = None
    image_rgb: object | None = None
    solved_distance_mm: float | None = None
    f_px: float | None = None
    n_faces: int = 1
    face_scores: list = field(default_factory=list)
    consent_ok: bool = True
    view_rms_sigma: float | None = None
    roll_deg: float | None = None
    eye_pts6: dict | None = None


def _t(key, cfg=None):
    """Threshold ``key``: resolved config value ('qa.<key>') if given, else the registered default."""
    if cfg:
        v = cfg.get("qa." + key)
        if v is not None:
            return v
    return QA[key].value


def _f(code, sev, value, key, action, pid=None, detail=None, cfg=None, threshold=None):
    d = QA[key]
    return Finding(code, sev, value, _t(key, cfg) if threshold is None else threshold, action, f"qa.{code}", f"qa.{code}.fix",
                   d.source, d.badge, pid, detail)


def _unit_rgb(a):
    """(H,W,3|4) image -> float (H,W,3) in [0,1]; integer dtypes scaled by their max, alpha dropped."""
    a = np.asarray(a)
    if a.ndim != 3 or a.shape[2] not in (3, 4):
        raise ValueError("image_rgb must have shape (H, W, 3) or (H, W, 4)")
    a = a[..., :3]
    if np.issubdtype(a.dtype, np.integer):
        return a.astype(float) / float(np.iinfo(a.dtype).max)
    return a.astype(float)


def _aspect(w, h):
    return max(w, h) / float(min(w, h))


def _aspect_crop(ctx, cfg):
    """(relative deviation, reasons) when the delivered frame is not the native aspect, else None."""
    ex, tol = ctx.exif, _t("aspect_tol", cfg)
    if not (ctx.width and ctx.height):
        return None
    a1 = _aspect(ctx.width, ctx.height)
    reasons: list = []
    dev = 0.0
    maker = ((ex.make or "") if ex is not None else "").lower()
    native = NATIVE_ASPECTS_PHONE if any(m in maker for m in PHONE_MAKES) else NATIVE_ASPECTS_OTHER
    nd = min(abs(a1 / a - 1.0) for a in native)
    if nd > tol:
        reasons.append("non_native_aspect")
        dev = max(dev, nd)
    if ex is not None and ex.width and ex.height:
        ed = abs(a1 / _aspect(ex.width, ex.height) - 1.0)
        if ed > tol:
            reasons.append("exif_dimensions_mismatch")
            dev = max(dev, ed)
    clap = getattr(ctx.heif, "clap", None) if ctx.heif is not None else None
    if clap:
        reasons.append("heif_clap")
    return (dev, reasons) if reasons else None


def run_photo_checks(ctx: PhotoContext, cfg: dict | None = None) -> list:
    """All per-photo gates of DESIGN 4.1 (everything except set-level and post-BA ones)."""
    out: list[Finding] = []
    pid = ctx.photo_id
    ex = ctx.exif

    def add(code, sev, value, key, action, detail=None, threshold=None):
        out.append(_f(code, sev, value, key, action, pid, detail, cfg, threshold))

    # Q-ORIENT
    if not ctx.orientation_applied:
        add("Q-ORIENT", "warn", False, "orient_sigma", "ask", {"orientation_applied": False,
                                                              "orient_sigma": _t("orient_sigma", cfg)})
        out[-1].threshold = None
    elif (ctx.view_rms_sigma is not None and ctx.roll_deg is not None
          and ctx.view_rms_sigma > _t("orient_sigma", cfg)):
        r = abs(ctx.roll_deg) % 360.0
        if min(abs(r - 90.0), abs(r - 270.0)) <= _t("orient_roll_tol_deg", cfg):
            add("Q-ORIENT", "warn", ctx.view_rms_sigma, "orient_sigma", "ask")

    # Q-EXIF-NONE
    if ex is None or not (ex.make or ex.model or ex.focal_35mm):
        out.append(Finding("Q-EXIF-NONE", "info", None, None, "none", "qa.Q-EXIF-NONE",
                           "qa.Q-EXIF-NONE.fix", _T + "Q-EXIF-NONE (com R2.2)", _B, pid))

    if ex is not None:
        # Q-CROP
        z = ex.digital_zoom_ratio
        if z is not None and z > _t("zoom_ratio_min", cfg):
            add("Q-CROP", "warn", float(z), "sigma_logf_zoom", "down_weight",
                {"sigma_logf": _t("sigma_logf_zoom", cfg), "reason": "digital_zoom"},
                threshold=_t("zoom_ratio_min", cfg))
    crop = _aspect_crop(ctx, cfg)
    if crop is not None:
        dev, reasons = crop
        add("Q-CROP", "warn", dev, "sigma_logf_aspect", "down_weight",
            {"sigma_logf": _t("sigma_logf_aspect", cfg), "reasons": reasons},
            threshold=_t("aspect_tol", cfg))

    if ex is not None:
        # Q-FRONTCAM
        if ex.is_front_camera:
            out.append(Finding("Q-FRONTCAM", "info", ex.lens_model, "front", "none",
                               "qa.Q-FRONTCAM", "qa.Q-FRONTCAM.fix", _T + "Q-FRONTCAM", _B, pid))
        # Q-PROCESS
        sw = (ex.software or "").lower()
        names = [n for n in EDITOR_NAMES if n in sw]
        if (ex.custom_rendered not in (None, 0)) or names:
            out.append(Finding("Q-PROCESS", "warn", ex.software if names else ex.custom_rendered,
                               "CustomRendered != 0 or editor named in Software", "exclude_texture",
                               "qa.Q-PROCESS", "qa.Q-PROCESS.fix", _T + "Q-PROCESS", _B, pid,
                               {"actions": ["down_weight", "exclude_texture"]}))

    # Q-NEAR
    d = ctx.solved_distance_mm
    if d is not None:
        if d < _t("near_exclude_mm", cfg):
            add("Q-NEAR", "warn", d, "near_exclude_mm", "exclude_geometry", {"level": "exclude"})
        elif d < _t("near_strong_mm", cfg):
            add("Q-NEAR", "warn", d, "near_strong_mm", "down_weight", {"level": "strong"})
        elif d < _t("near_warn_mm", cfg):
            add("Q-NEAR", "warn", d, "near_warn_mm", "down_weight", {"level": "warn"})

    # Q-WIDE
    if ex is not None and ex.focal_35mm and ex.focal_35mm <= _t("wide_f35_mm", cfg):
        add("Q-WIDE", "warn", float(ex.focal_35mm), "wide_f35_mm", "ask")
    elif ctx.face_centre_px is not None and ctx.width and ctx.height:
        c = np.asarray(ctx.face_centre_px, float)
        r = float(np.hypot(c[0] - ctx.width / 2.0, c[1] - ctx.height / 2.0))
        half_diag = 0.5 * math.hypot(ctx.width, ctx.height)
        f_eff = ctx.f_px or (ex.focal_px(ctx.width, ctx.height) if ex is not None else None)
        if r > _t("wide_radius_frac", cfg) * half_diag:
            add("Q-WIDE", "warn", r / half_diag, "wide_radius_frac", "ask")
        elif f_eff:
            ang = math.degrees(math.atan2(r, f_eff))
            if ang > _t("wide_off_axis_deg", cfg):
                add("Q-WIDE", "warn", ang, "wide_off_axis_deg", "ask")

    # Q-SMALL
    if ctx.face_px is not None:
        if ctx.face_px < _t("small_block_px", cfg):
            add("Q-SMALL", "block", ctx.face_px, "small_block_px", "exclude_geometry")
        elif ctx.face_px < _t("small_warn_px", cfg):
            add("Q-SMALL", "warn", ctx.face_px, "small_warn_px", "down_weight")
    if ctx.iris_px is not None and ctx.iris_px < _t("iris_min_px", cfg):
        add("Q-SMALL", "info", ctx.iris_px, "iris_min_px", "none", {"no_iris_scale": True})
        out[-1].msg_key = "qa.Q-SMALL.no_iris_scale"

    # Q-BLINK
    if ctx.eye_pts6:
        ears = {k: ims.eye_aspect_ratio(v) for k, v in ctx.eye_pts6.items()}
        ears = {k: e for k, e in ears.items() if math.isfinite(e)}
        low = sorted(k for k, e in ears.items() if e < _t("blink_ear", cfg))
        if low:
            add("Q-BLINK", "warn", min(ears.values()), "blink_ear", "drop_class",
                {"drop": "lids", "eyes": low})

    # Q-CLIP
    if ctx.image_rgb is not None and ctx.skin_mask is not None:
        img = _unit_rgb(ctx.image_rgb)
        fr = ims.clipped_fraction(img, ctx.skin_mask, _t("clip_level", cfg))
        if fr > _t("clip_fraction", cfg):
            add("Q-CLIP", "warn", fr, "clip_fraction", "exclude_texture",
                {"exclude": ["photometry", "texture"]})

    # Q-FACES
    if ctx.n_faces > 1 and len(ctx.face_scores) >= 2:
        second = sorted(ctx.face_scores, reverse=True)[1]
        if second >= _t("faces_score", cfg):
            add("Q-FACES", "warn", float(second), "faces_score", "ask")

    # Q-CONSENT
    if not ctx.consent_ok:
        out.append(Finding("Q-CONSENT", "block", False, True, "exclude_geometry",
                           "qa.Q-CONSENT", "qa.Q-CONSENT.fix", _T + "Q-CONSENT (eth F2)",
                           "\U0001F4C4", pid))
    return out


def _parse_dt(s):
    try:
        return datetime.strptime(s.strip()[:19], "%Y:%m:%d %H:%M:%S")
    except (ValueError, AttributeError):
        return None


def run_set_checks(contexts, cfg: dict | None = None) -> list:
    """Set-level gates: Q-BLUR, Q-DATES, Q-GROUP-SPREAD."""
    ctxs = list(contexts)
    out: list[Finding] = []

    # Q-BLUR
    lv = {c.photo_id: (None if c.image_gray is None else ims.laplacian_variance(c.image_gray, c.skin_mask))
          for c in ctxs}
    vals = [v for v in lv.values() if v is not None]
    if len(vals) >= 2:
        d = QA["blur_ratio"]
        thr = _t("blur_ratio", cfg) * float(np.median(vals))
        for c in ctxs:
            v = lv[c.photo_id]
            if v is not None and v < thr:
                out.append(Finding("Q-BLUR", "warn", v, thr, "down_weight", "qa.Q-BLUR",
                                   "qa.Q-BLUR.fix", d.source, d.badge, c.photo_id))

    # Q-DATES
    dated = sorted((dt, c.photo_id) for c in ctxs
                   if c.exif is not None and (dt := _parse_dt(c.exif.datetime_original)) is not None)
    if len(dated) >= 2:
        d = QA["dates_gap_days"]
        cid, ids = 0, {dated[0][1]: 0}
        for (t0, _), (t1, p1) in zip(dated, dated[1:]):
            if (t1 - t0).total_seconds() / 86400.0 > _t("dates_gap_days", cfg):
                cid += 1
            ids[p1] = cid
        if cid > 0:
            out.append(Finding("Q-DATES", "warn", cid + 1, _t("dates_gap_days", cfg), "ask", "qa.Q-DATES",
                               "qa.Q-DATES.fix", d.source, d.badge, None, {"clusters": ids}))

    # Q-GROUP-SPREAD: same (make, model, lens, W, H) group, f35 differing > 5 %
    groups: dict = {}
    for c in ctxs:
        e = c.exif
        if e is not None and e.focal_35mm:
            groups.setdefault((e.make, e.model, e.lens_model, c.width, c.height), []).append(
                (c.photo_id, float(e.focal_35mm)))
    d = QA["group_f35_spread"]
    for key, items in groups.items():
        fs = [f for _, f in items]
        spread = (max(fs) - min(fs)) / float(np.median(fs))
        if len(fs) > 1 and spread > _t("group_f35_spread", cfg):
            out.append(Finding("Q-GROUP-SPREAD", "warn", spread, _t("group_f35_spread", cfg), "ask",
                               "qa.Q-GROUP-SPREAD", "qa.Q-GROUP-SPREAD.fix", d.source, d.badge,
                               None, {"group": list(key), "photos": [p for p, _ in items]}))

    # Q-CROP (zoom): f35 / FocalLength per (make, model, lens) above the group mode x 1.02
    zgroups: dict = {}
    for c in ctxs:
        e = c.exif
        if e is not None and e.focal_35mm and e.focal_length_mm:
            zgroups.setdefault((e.make, e.model, e.lens_model), []).append(
                (c.photo_id, float(e.focal_35mm) / float(e.focal_length_mm)))
    d = QA["sigma_logf_zoom"]
    lim = _t("zoom_group_mode_ratio", cfg)
    for key, items in zgroups.items():
        if len(items) < 2:
            continue
        counts: dict = {}
        for _, r in items:
            counts[round(r, 2)] = counts.get(round(r, 2), 0) + 1
        c0 = min(r for r, n in counts.items() if n == max(counts.values()))
        for pid, r in items:
            if r / c0 > lim:
                out.append(Finding("Q-CROP", "warn", r / c0, lim, "down_weight", "qa.Q-CROP",
                                   "qa.Q-CROP.fix", d.source, d.badge, pid,
                                   {"sigma_logf": _t("sigma_logf_zoom", cfg), "reason": "group_mode_zoom",
                                    "group": list(key), "group_mode_crop": c0}))
    return out


def retouch_findings(smoothness_by_photo: dict, cfg: dict | None = None) -> list:
    """Q-RETOUCH pre-BA part: skin smoothness index (``image_stats.skin_smoothness_index``)
    below ``retouch_ratio`` x the set median -> sigma x2-3, no texture (DESIGN 4.1)."""
    if len(smoothness_by_photo) < 2:
        return []
    d = QA["retouch_ratio"]
    thr = _t("retouch_ratio", cfg) * float(np.median(list(smoothness_by_photo.values())))
    return [Finding("Q-RETOUCH", "warn", v, thr, "exclude_texture", "qa.Q-RETOUCH",
                    "qa.Q-RETOUCH.fix", d.source, d.badge, p, {"sigma_mult": [2.0, 3.0]})
            for p, v in smoothness_by_photo.items() if v < thr]


def occluder_actions(tags) -> dict:
    """Actions for one-click occluder tags (DESIGN 4.1; Rob 3.6).

    Returns {'sigma_mult': {class: factor}, 'drop_classes': [...], 'flags': {...}}.
    Class names are generic landmark-class labels resolved by the scheme layer.
    """
    tags = set(tags)
    mult: dict = {}
    drop: set = set()
    flags: dict = {}
    if "glasses" in tags:
        mult["eye"] = 2.0
        flags["no_iris_scale"] = True
        drop.add("lid_points_under_frame")
    if "beard" in tags:
        drop.update({"pg", "gn", "me", "jaw_contour"})
        flags["contour_kind"] = "outer_bound"
        flags["jaw_status"] = "prior-driven"
    if "hair" in tags:
        drop.update({"ear", "temple"})
        flags["no_silhouette_above"] = "trichion"
    if "makeup" in tags:
        mult["lip_border"] = 2.0
        mult["brow_border"] = 2.0
    return {"sigma_mult": mult, "drop_classes": sorted(drop), "flags": flags}
