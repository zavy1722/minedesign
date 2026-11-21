# SPDX-License-Identifier: GPL-3.0-or-later
"""Sidebar 'Face3D': the guided rail, stage panels, expert sub-panels and the confidence ledger (DESIGN 6.4, H1-H9).

Conventions
-----------
* `rail_state` is PURE (no bpy; this module imports without Blender): from plain dicts it returns one tuple
  per stage ``(stage, status, done_when_key, primary_op, disabled_reason_key)`` for Consent, Photos, Check,
  Landmarks, Cameras, Shape, Confidence, Sculpt, Texture, Share. ``status`` is ``done`` / ``attention`` /
  ``not_started``; the keys index `messages.MESSAGES`; ``disabled_reason_key`` is None when the primary button
  is enabled. The disabled-reason order mirrors the operators' poll order (project, running job, consent,
  photos, landmarks), so the rail text and the greyed-out tooltip agree.
* Input dicts. ``project_dict``: ``project.json`` content (face3d.project) plus optional keys supplied by
  `collect_rail_inputs`: ``consent`` (ConsentRecord as a dict or None), ``cards`` ([{severity, decided}]),
  ``landmark_photos`` (photo ids with an imported landmark set this session), ``cameras_applied``,
  ``keys_applied``, ``sculpt``, ``share_reviewed``. ``result_dict``: ``result.json`` of the active solve (or
  None). ``job_state``: ``{'status': idle|running|ready|failed|cancelled, ...}`` (props.F3DJob).
* Every stage shows an icon AND a word (Done / Needs attention / Not started), its done-when line and ONE
  primary button; expert options sit in sub-panels with ``bl_options = {'DEFAULT_CLOSED'}`` that show the
  engine defaults WITH their badges, read-only (H2: they never change labels).
* The Confidence panel prints the claims ledger in plain language: ranges, never finer than the report floor
  (face3d.fit.ledger LEDGER.report_floor_mm, H8), and always the banner 'Not validated against a scan.' (H9).
"""
import json
import os
from datetime import datetime, timezone

try:                                  # rail_state / ledger_lines must import without Blender
    import bpy
except ImportError:                   # pragma: no cover - exercised only outside Blender
    bpy = None

try:
    from . import ensure_engine_on_path
except ImportError:                   # pragma: no cover - imported outside the package
    ensure_engine_on_path = lambda: None  # noqa: E731

from .messages import MESSAGES, text

ensure_engine_on_path()

from face3d.core import config as _config  # noqa: E402
from face3d.core import policy  # noqa: E402
from face3d.fit import ledger as _ledger  # noqa: E402

STAGES = ("consent", "photos", "check", "landmarks", "cameras", "shape", "confidence", "sculpt", "texture", "share")
STATUS_ICON = {"done": "CHECKMARK", "attention": "ERROR", "not_started": "RADIOBUT_OFF"}
MAX_DEFAULTS_SHOWN = 24               # the expert list is a read-only sample; the full set is in the report
_EXCLUDED = ("exclude", False)
_UNSEEN = ("unobserved", "prior-driven")


# ------------------------------------------------------------------ pure rail
def consent_status(consent, now=None):
    """'missing' | 'no_scope' | 'expired' | 'ok' for a ConsentRecord dict (None = missing; fail closed)."""
    if not consent:
        return "missing"
    try:
        rec = policy.ConsentRecord(**consent)
    except (TypeError, ValueError):
        return "missing"
    if not rec.scopes & policy.Scope.RECONSTRUCT:
        return "no_scope"
    res = policy.check("reconstruct", rec, photos_sha256=tuple(rec.photo_sha256) or ("0" * 64,),
                       now=now or datetime.now(timezone.utc))
    bad = [r for r in res.reasons if "sha256" not in r]
    if not bad and not res.missing:
        return "ok"
    return "expired" if any("expired" in r for r in bad) else "no_scope"


def _has_scope(consent, scope):
    try:
        return bool(policy.ConsentRecord(**consent).scopes & scope)
    except (TypeError, ValueError):
        return False


def rail_state(project_dict, result_dict, job_state):
    """Rail rows for the ten stages (see module docstring). Pure; never raises on missing keys."""
    p = project_dict or {}
    js = job_state or {}
    has_project = project_dict is not None
    running = js.get("status") == "running"
    cstat = consent_status(p.get("consent"))
    photos = [ph for ph in p.get("photos", []) if ph.get("include") not in _EXCLUDED]
    known = set((p.get("consent") or {}).get("photo_sha256", []))
    uncovered = [ph for ph in photos if ph.get("sha256") not in known]
    cards = p.get("cards", [])
    open_cards = [c for c in cards if not c.get("decided") and c.get("severity") in ("warn", "block")]
    lm_ids = set(p.get("landmark_photos", [])) | {pin.get("photo") for pin in p.get("pins", [])}
    lm_have = [ph for ph in photos if ph.get("id") in lm_ids]
    has_result = bool(result_dict)
    unseen = [r for r in (result_dict or {}).get("regions", []) if r.get("status") in _UNSEEN]

    def consent_reason():
        return None if cstat == "ok" else ("consent_expired" if cstat == "expired" else "consent_missing")

    def launch_reason():
        if not has_project:
            return "no_project"
        if running:
            return "job_running"
        r = consent_reason()
        if r:
            return r
        if not photos:
            return "no_photos"
        if uncovered:
            return "photo_not_consented"
        if not lm_have:
            return "no_landmarks"
        return None

    def apply_reason(need_keys=False):
        if not has_project:
            return "no_project"
        if running:
            return "job_running"
        if not has_result:
            return "no_result"
        return None

    rows = []

    # Consent
    if not has_project:
        rows.append(("consent", "not_started", "rail.consent.done_when", "face3d.project_new", None))
    else:
        st = "done" if cstat == "ok" else ("not_started" if cstat == "missing" else "attention")
        rows.append(("consent", st, "rail.consent.done_when", "face3d.consent_edit",
                     "job_running" if running else None))
    # Photos
    if not has_project:
        why = "no_project"
    elif running:
        why = "job_running"
    else:
        why = consent_reason()
    st = "not_started" if not photos else ("attention" if uncovered else "done")
    rows.append(("photos", st, "rail.photos.done_when", "face3d.photos_add", why))
    # Check
    st = "not_started" if not photos else ("attention" if open_cards else "done")
    rows.append(("check", st, "rail.check.done_when", "face3d.review_next",
                 "no_photos" if not photos else (None if open_cards else "review_empty")))
    # Landmarks
    st = "not_started" if not lm_have else ("done" if len(lm_have) == len(photos) else "attention")
    why = why if why else ("no_photos" if not photos else None)
    rows.append(("landmarks", st, "rail.landmarks.done_when", "face3d.landmarks_import", why))
    # Cameras and Shape (one solve produces both; applying puts them in the scene)
    applied_c, applied_k = bool(p.get("cameras_applied")), bool(p.get("keys_applied"))
    for stage, op_run, applied in (("cameras", "face3d.solve", applied_c), ("shape", "face3d.fit", applied_k)):
        if has_result and applied:
            rows.append((stage, "done", "rail.%s.done_when" % stage, op_run, launch_reason()))
        elif has_result:
            rows.append((stage, "attention", "rail.%s.done_when" % stage, "face3d.apply_result", apply_reason()))
        else:
            st = "attention" if js.get("status") == "failed" else "not_started"
            rows.append((stage, st, "rail.%s.done_when" % stage, op_run, launch_reason()))
    # Confidence
    st = "not_started" if not has_result else ("attention" if unseen else "done")
    rows.append(("confidence", st, "rail.confidence.done_when", "face3d.view_next",
                 "no_photos" if not photos else None))
    # Sculpt
    if not has_project:
        why = "no_project"
    elif running:
        why = "job_running"
    else:
        why = None if applied_k else "no_result"
    rows.append(("sculpt", "done" if p.get("sculpt") else "not_started", "rail.sculpt.done_when",
                 "face3d.handoff_sculpt", why))
    # Texture
    if why is None and not _has_scope(p.get("consent"), policy.Scope.TEXTURE):
        why_t = "consent_denied_scope"
    else:
        why_t = why
    tex = bool((result_dict or {}).get("texture"))
    rows.append(("texture", "done" if tex else "not_started", "rail.texture.done_when",
                 "face3d.texture_project", why_t))
    # Share
    rows.append(("share", "done" if p.get("share_reviewed") else "not_started", "rail.share.done_when",
                 "face3d.prepare_for_sharing", None if has_project else "no_project"))
    return rows


def ledger_lines(result):
    """Plain-language ledger lines of a result.json dict (H1, H4, H5, H8, H9); pure.

    First line is the banner; then the tier, one line per region (sigma shown at 1 sigma and never below
    the report floor), the count of uncalibrated defaults and the next-photo advice.
    """
    if not result:
        return [text("ledger.banner"), text("ledger.none")]
    floor = float(_ledger.LEDGER.report_floor_mm.value)
    lines = [result.get("banner") or text("ledger.banner")]
    tier = result.get("tier") or {}
    if tier:
        lines.append(text("ledger.tier", code=tier.get("code", "?"), name=tier.get("name", "")))
    for r in result.get("regions", []):
        label = _ledger.REGION_LABELS.get(r["name"], r["name"].replace("_", " ").capitalize())
        sig = r.get("sigma_rep_mm")
        sig = max(float(sig), floor) if sig is not None else floor
        line = text("ledger.region." + r["status"], label=label, sigma=sig)
        if r.get("next_photo") and r["status"] != "measured":
            line += " - " + r["next_photo"]
        lines.append(line)
    if result.get("unverified_defaults") is not None:
        lines.append(text("ledger.defaults", n=result["unverified_defaults"]))
    if result.get("next_photo"):
        lines.append(result["next_photo"])
    return lines


def focal_summary(result):
    """'measured in 2 of 3 photos; ...' from result['focal_statuses'] (words as face3d.fit.ledger)."""
    st = (result or {}).get("focal_statuses") or []
    words = {"measured": "measured", "partial": "partly measured", "prior_used": "from prior"}
    counts = {}
    for s in st:
        counts[s] = counts.get(s, 0) + 1
    return "; ".join("%s in %d of %d photos" % (words.get(k, k), c, len(st)) for k, c in counts.items()) or "-"


# ------------------------------------------------------------------ data collection (bpy)
_CACHE = {}


def _mtime(path):
    try:
        return os.stat(path).st_mtime_ns
    except OSError:
        return None


def _cached_json(path):
    m = _mtime(path)
    hit = _CACHE.get(path)
    if hit and hit[0] == m:
        return hit[1]
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        data = None
    _CACHE[path] = (m, data)
    return data


def collect_rail_inputs(context):
    """(project_dict, result_dict, job_state) from the scene and the project folder (bpy side)."""
    from . import ops_landmarks, ops_project as P
    s = context.scene.face3d
    job = {"status": s.job.status, "stage": s.job.stage, "progress": s.job.progress, "msg_key": s.job.msg_key}
    root = P.project_root(context)
    if root is None:
        return None, None, job
    prj = _cached_json(str(root / "project.json"))
    if prj is None:
        return None, None, job
    prj = dict(prj)
    prj["consent"] = _cached_json(str(P.consent_path(root)))
    prj["cards"] = [{"severity": c.severity, "decided": c.decided, "code": c.code} for c in s.cards]
    prj["landmark_photos"] = sorted(ops_landmarks.session_sets(context))
    objs = [o for o in bpy.data.objects if getattr(o, "type", "") == "MESH"]
    prj["keys_applied"] = any("f3d_applied_solve" in o for o in objs)
    prj["cameras_applied"] = prj["keys_applied"]
    prj["sculpt"] = any("f3d_sculpt_of" in o for o in objs)
    prj["share_reviewed"] = bool(context.scene.get("f3d_share_reviewed", False))
    result = None
    if prj.get("active_solve"):
        result = _cached_json(str(root / prj["active_solve"] / "result.json"))
    return prj, result, job


def rail_rows(context):
    """{stage: row} for the current scene."""
    return {r[0]: r for r in rail_state(*collect_rail_inputs(context))}


# ------------------------------------------------------------------ panels (bpy only)
def _draw_stage(layout, context, stage):
    row = rail_rows(context)[stage]
    _stage, status, done_key, op, why = row
    layout.label(text=text("status." + status), icon=STATUS_ICON[status])
    layout.label(text=text(done_key))
    sub = layout.row()
    sub.enabled = why is None
    sub.operator(op, text=text("btn." + op.split(".", 1)[1]))
    if why:
        layout.label(text=text(why), icon="INFO")


def _make_panels():
    classes = []
    base = dict(bl_space_type="VIEW_3D", bl_region_type="UI", bl_category="Face3D")

    def stage_draw(stage):
        def draw(self, context):
            _draw_stage(self.layout, context, stage)
            if stage == "confidence":
                prj, res, _job = collect_rail_inputs(context)
                for line in ledger_lines(res):
                    self.layout.label(text=line)
        return draw

    parents = {}
    for stage in STAGES:
        attrs = dict(base, bl_idname="FACE3D_PT_" + stage, bl_label=text("rail." + stage), draw=stage_draw(stage))
        if stage == "confidence":
            attrs["bl_label"] = text("panel.ledger")
        cls = type("FACE3D_PT_" + stage, (bpy.types.Panel,), attrs)
        parents[stage] = cls
        classes.append(cls)

    def defaults_draw(self, context):
        names = sorted(_config.snapshot())
        for name in names[:MAX_DEFAULTS_SHOWN]:
            d = _config.get(name)
            self.layout.label(text="%s %s = %s %s" % (d.badge, name, d.value, d.unit))
        self.layout.label(text="%d / %d" % (min(len(names), MAX_DEFAULTS_SHOWN), len(names)))

    def modes_draw(self, context):
        _p, res, _j = collect_rail_inputs(context)
        self.layout.label(text=text("mode.symmetry"))
        self.layout.label(text=text("mode.expression"))
        self.layout.label(text=text("mode.focal", summary=focal_summary(res)))

    def history_draw(self, context):
        from . import ops_project as P
        root = P.project_root(context)
        base_dir = root / "solves" if root else None
        nums = sorted(int(d.name) for d in base_dir.iterdir() if d.name.isdigit()) if base_dir and base_dir.is_dir() else []
        for n in nums:
            op = self.layout.operator("face3d.revert_solve", text="%s #%d" % (text("btn.revert_solve"), n))
            op.n = n

    for ident, label_key, fn in (("expert_defaults", "panel.expert_defaults", defaults_draw),
                                 ("expert_modes", "panel.expert_modes", modes_draw),
                                 ("expert_history", "panel.expert_history", history_draw)):
        attrs = dict(base, bl_idname="FACE3D_PT_" + ident, bl_label=text(label_key), bl_parent_id="FACE3D_PT_shape",
                     bl_options={"DEFAULT_CLOSED"}, draw=fn)
        classes.append(type("FACE3D_PT_" + ident, (bpy.types.Panel,), attrs))

    def job_draw(self, context):
        s = context.scene.face3d
        if s.job.status == "running":
            self.layout.label(text=text("job_progress", stage=s.job.stage, pct=int(100 * s.job.progress)))
            self.layout.operator("face3d.job_cancel", text=text("btn.job_cancel"))
        elif s.job.status in ("failed", "cancelled") and s.job.msg_key:
            self.layout.label(text=text(s.job.msg_key), icon="ERROR")
    classes.insert(0, type("FACE3D_PT_job", (bpy.types.Panel,), dict(
        base, bl_idname="FACE3D_PT_job", bl_label="Face3D", draw=job_draw)))
    return classes


_classes = []


def register():
    global _classes
    if bpy is None:
        return
    _classes = _make_panels()
    for c in _classes:
        bpy.utils.register_class(c)


def unregister():
    global _classes
    if bpy is None:
        return
    for c in reversed(_classes):
        bpy.utils.unregister_class(c)
    _classes = []
