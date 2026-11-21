"""Pipeline stages: pure cached functions and ``run_pipeline`` (DESIGN 2.4, 3.2, 2.1 invariants 3-4).

Every stage is a pure function ``(inputs: dict, config: dict, seed: int) -> dict`` registered in
:data:`STAGES` with its upstream inputs, outputs and data class.  :func:`run_pipeline` runs them in
order, keys each stage by :meth:`face3d.core.cache.StageCache.key` (SHA-256 of the input hashes,
the config snapshot, the seed and the engine version), enforces the consent gates
(:func:`face3d.core.policy.check` 'reconstruct' before ``landmarks``/``solve``, 'texture' before
``texture``) and applies a mirror flip only for a photo with a recorded user decision (D-10).

Order: ``ingest, triage, landmarks, solve, observe, fit, uncertainty, handoff, texture, report``.

Conventions
-----------
* Units: float64 millimetres in the template head frame (DESIGN 3.1: +x subject's left, +y up, +z out
  of the face, origin mid-tragion); image coordinates are continuous pixels with the origin at the
  top-left corner of the project's working frame (the working copy's size, else the EXIF size).
* The engine point list is the 44 anatomical ids of the packaged prior (registry order), followed by
  the non-anatomical points of one scheme that the template kit embeds (conditional template prior,
  DESIGN 4.6).  A scheme that does not list an anatomical id leaves it unobserved (NaN rows).
* Stage outputs are plain data (JSON-able values and ``numpy`` arrays) plus optional in-memory
  objects under keys starting with ``_`` (never hashed, never persisted).
* Landmarks are BIOMETRIC_GEOMETRY with TTL 0: stage outputs of ``landmarks`` and everything derived
  from them are never written to disk by the cache, and the project folder only receives landmark
  files when ``project.landmark_cache.keep`` is true (opt-in, logged).
* QA (DESIGN 4.1): ``triage`` runs the photo checks that need no landmarks; ``landmarks`` runs the
  landmark-aware ones (Q-SMALL face size, off-axis Q-WIDE, Q-FACES; Q-BLINK is not evaluated: no scheme lists
  eyelid contours) and applies the actions (exclude_geometry unless ``include: true``, down_weight as a sigma
  multiplier ``pipeline.downweight_sigma_mult``, drop_class); ``solve`` runs Q-NEAR on the solved distance.
  Every finding reaches ``result.json`` (``findings``, ``views[].findings``, ``excluded_views``, ``flags``).
* Mirror: the latest mirror decision of a photo (``mirror_flip`` / ``mirror_keep``) wins; a flip is applied only
  for photos whose latest decision is ``mirror_flip``; the mirror
  test of the ``solve`` stage only produces decision *cards* (D-10).
* Numeric defaults introduced here are registered under the ``pipeline`` namespace
  (badge new: uncalibrated, DESIGN 8 conventions).
"""
from __future__ import annotations

import hashlib
import os
import time
from collections import Counter, OrderedDict
from contextlib import contextmanager
import dataclasses
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from face3d import __version__ as _FACE3D_VERSION
from face3d.core import config as _config
from face3d.core import policy
from face3d.core.cache import StageCache
from face3d.core.config import Default, register_defaults
from face3d.core.policy import ConsentRecord, DataClass, LicenceTag
from face3d.core.schema import (FormatError, canonical_json, dump_json, save_arrays, sha256_bytes,
                                sha256_file, _clean)
# engine modules that register badged defaults but that no stage needs on every run (contours, edge snapping,
# shape models) are imported here, so the config snapshot and the unverified-default count (H8) do not depend
# on what else the process happened to import
from face3d.fit import contour as _contour  # noqa: F401
from face3d.fit import edge_snap as _edge_snap  # noqa: F401
from face3d.solve import shape_models as _shape_models  # noqa: F401
from face3d.fit import ledger as _ledger
from face3d.fit import symmetry as _sym
from face3d.fit import template as _tpl
from face3d.fit import uncertainty as _unc
from face3d.geometry.camera import Camera
from face3d.handoff import keys as _keys
from face3d.io import image_ops as _imops
from face3d.io.landmarks import LandmarkSet
from face3d.io.png import read_png
from face3d.mesh.subdiv import fit_cage_to_limit
from face3d.model.conditional_prior import ConditionalTemplatePrior
from face3d.model.landmark_prior import CompositePrior, FactorPrior
from face3d.model.procedural_head import build_procedural_head
from face3d.model.registry import ANATOMICAL, anchor_ids, load_scheme
from face3d.model.template_kit import TemplateKit, TopologyMismatch, area_weighted_normals
from face3d.pipeline.project import PhotoRecord, Project, exif_from_summary, resolve_pin_class
from face3d.qa import checks as _qa
from face3d.qa import image_stats as _ims
from face3d.solve import bundle as _bundle
from face3d.solve import camera_model as _cm
from face3d.solve import expression as _expr
from face3d.solve import focal as _focal
from face3d.solve import mirror as _mirror
from face3d.solve import nbv as _nbv
from face3d.solve import noise as _noise
from face3d.solve import observability as _ob
from face3d.solve import scale as _scale
from face3d.solve.bundle import JawConfig, ViewObs, bundle_adjust, view_noise_cov
from face3d.solve.reconstruct import PhotoLandmarks, reconstruct_landmarks
from face3d.solve.robust import RobustSchedule
from face3d.texture import blend as _blend
from face3d.texture import project as _tp

_NEW = "\U0001F195"
ENGINE_VERSION = f"face3d-{_FACE3D_VERSION}/{_bundle.ENGINE_VERSION}"
RESULT_FORMAT = "face3d.result"
RESULT_VERSION = 1
LICENCE_RESULT = "user-data (derived from the subject's photos; consent-scoped)"

PIPELINE = register_defaults("pipeline", {
    "focal_tie_sigma": Default(0.02, _NEW, "WBS WP-20 spec: soft focal tie within a focal group "
                               "(rec CAM-5, DESIGN 4.2)", "ln f", (0.0, 1.0)),
    "unverified_sigma_mult": Default(3.0, _NEW, "WP-20 implementation choice: sigma multiplier of a scheme "
                                     "point with verified=false (DESIGN 3.2 'carry an inflated sigma_def "
                                     "until calibrated')", "", (1.0, 100.0)),
    "max_retag_rounds": Default(3, _NEW, "DESIGN 4.9 / expression.MAX_RETAG_ROUNDS: expression re-tag "
                                "rounds after a solve", "", (0, 10)),
    "lovo_min_views": Default(3, _NEW, "solve.observability.lovo_gamma needs >= 3 views (DESIGN 4.13)",
                              "", (2, 100)),
    "texture_size": Default(256, _NEW, "WP-20 implementation choice: UV map size when texture is "
                            "requested (texture-extraction recommends 2048-4096 for production, "
                            "tests 128-256)", "px", (16, 8192)),
    "downweight_sigma_mult": Default(2.0, _NEW, "WP-20 implementation choice: observation sigma multiplier of a "
                                     "view carrying a 'down_weight' QA finding (Q-SMALL warn, Q-BLUR, Q-NEAR "
                                     "strong/warn; DESIGN 4.1 gives no factor)", "", (1.0, 20.0)),
    "texture_sigma_geom_mm": Default(1.0, _NEW, "texture view_weights geometry sigma (DESIGN 4.18)",
                                     "mm", (0.0, 50.0)),
})
_P = {k: PIPELINE[k].value for k in PIPELINE}

ORDER = ("ingest", "triage", "landmarks", "solve", "observe", "fit", "uncertainty", "handoff",
         "texture", "report")
_REGION_RANK = {"unobserved": 0, "prior-driven": 1, "constrained": 2, "measured": 3}
_OBJ_LRU: "OrderedDict[str, dict]" = OrderedDict()
_OBJ_MAX = 24


#: the active cancel check (set by :func:`lm_cancel_hook` while a stage runs); long non-LM loops call
#: :func:`poll_cancel` so a cancel is honoured inside a stage, not only between stages
_POLL: list = [None]


def poll_cancel() -> None:
    """Raise :class:`Cancelled` (via the job's check) when a cancel was requested; no-op outside a job."""
    fn = _POLL[0]
    if fn is not None:
        fn()


# ============================================================================ errors, helpers
class PipelineError(Exception):
    """A pipeline failure with a stable ``code`` (no paths or coordinates in ``code``)."""

    def __init__(self, code: str, msg: str = ""):
        super().__init__(msg or code)
        self.code = code


class ConsentError(PipelineError):
    """The consent gate refused the operation; ``result`` is the :class:`policy.GateResult`."""

    def __init__(self, operation: str, result: policy.GateResult):
        super().__init__("consent_refused", f"consent gate {operation!r} denied")
        self.operation = operation
        self.result = result


class Cancelled(Exception):
    """Raised when the cancel callback fires (job protocol)."""


def _hash_value(v: Any) -> str:
    """Stable SHA-256 of nested plain data and arrays (keys starting with ``_`` are skipped)."""
    h = hashlib.sha256()

    def feed(o: Any) -> None:
        if isinstance(o, np.ndarray):
            a = np.ascontiguousarray(o)
            h.update(b"A" + str(a.dtype).encode() + str(a.shape).encode())
            h.update(a.tobytes())
        elif isinstance(o, dict):
            h.update(b"D")
            for k in sorted(o, key=str):
                if str(k).startswith("_"):
                    continue
                h.update(str(k).encode() + b"=")
                feed(o[k])
        elif isinstance(o, (list, tuple)):
            h.update(b"L%d" % len(o))
            for x in o:
                feed(x)
        elif is_dataclass(o) and not isinstance(o, type):
            h.update(b"C" + type(o).__name__.encode())
            feed({f.name: getattr(o, f.name) for f in fields(o)})
        else:
            h.update(b"S" + canonical_json(o))

    feed(v)
    return h.hexdigest()


def _plain(o: Any) -> Any:
    """JSON-able copy: numpy to builtins, non-finite to None (see :func:`face3d.core.schema._clean`)."""
    return _clean(o)


def _unit_image(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a)
    if a.dtype == np.uint8:
        return a.astype(np.float64) / 255.0
    if a.dtype == np.uint16:
        return a.astype(np.float64) / 65535.0
    return np.clip(a.astype(np.float64), 0.0, 1.0)


def load_working_copy(root: Path, rel: str) -> np.ndarray:
    """Load a ``.npy`` / ``.png`` working copy (orientation baked) as a float image in [0, 1]."""
    p = Path(rel)
    p = p if p.is_absolute() else Path(root) / p
    if p.suffix.lower() == ".npy":
        arr = np.load(p, allow_pickle=False)
    elif p.suffix.lower() == ".png":
        arr = read_png(p)
    else:
        raise PipelineError("unsupported_working_copy", "working copy must be .npy or .png")
    return _unit_image(arr)


_KIT_CACHE: dict[str, TemplateKit] = {}


def load_kit(template: Mapping[str, Any], root: Path | None = None) -> TemplateKit:
    """The template kit named by ``project.template`` (``procedural-head-v1`` is built in).

    A non-empty ``template['topology_sha256']`` must equal the kit's (invariant INV-4, bl K1);
    ``template['path']`` names a ``<id>.kit.json`` otherwise.
    """
    tid = str(template.get("id", "procedural-head-v1"))
    path = template.get("path")
    key = f"{tid}|{path}"
    kit = _KIT_CACHE.get(key)
    if kit is None:
        if path:
            p = Path(path)
            p = p if p.is_absolute() or root is None else Path(root) / p
            kit = TemplateKit.load(p, expect_topology_sha256=template.get("topology_sha256") or None)
        elif tid == "procedural-head-v1":
            kit = build_procedural_head()
        else:
            raise PipelineError("unknown_template", f"unknown template id {tid!r}")
        _KIT_CACHE[key] = kit
    want = template.get("topology_sha256") or ""
    if want and want != kit.topology_sha256:
        raise TopologyMismatch("project template topology hash does not match the template kit")
    return kit


def _focal_group_mode(exifs: Mapping[str, Any]) -> dict[str, float | None]:
    """Mode of f35 / FocalLength per (make, model, lens) group, as in ``qa.checks.run_set_checks``."""
    groups: dict = {}
    for pid, e in exifs.items():
        if e is not None and e.focal_35mm and e.focal_length_mm:
            groups.setdefault((e.make, e.model, e.lens_model), []).append(
                (pid, float(e.focal_35mm) / float(e.focal_length_mm)))
    out: dict[str, float | None] = {}
    for items in groups.values():
        if len(items) < 2:
            continue
        counts = Counter(round(r, 2) for _, r in items)
        c0 = min(r for r, n in counts.items() if n == max(counts.values()))
        for pid, _ in items:
            out[pid] = c0
    return out


# ============================================================================ stage: ingest
def stage_ingest(inputs: dict, config: dict, seed: int) -> dict:
    """Photos to verified records: SHA-256 check, working-copy size and hash, focal group.

    ``inputs``: ``photos`` (project photo records), ``template`` (project template block),
    ``file_sha256`` ({photo id: {original, working_copy}}: file hashes supplied by ``run_pipeline`` so they are
    part of the cache key; computed here when absent), ``_ctx = {'root': Path}``.  A photo file that exists must match its recorded SHA-256 (a
    changed file is refused: consent covers hashes, eth F2); a missing original is allowed when a
    working copy exists.  Pixels are only read from the working copy (DESIGN 2.5).
    """
    root = Path(inputs["_ctx"]["root"])
    out = []
    fh = inputs.get("file_sha256") or {}
    for rec in inputs["photos"]:
        pid = rec["id"]
        path = rec.get("path")
        src = None if not path else (Path(path) if Path(path).is_absolute() else root / path)
        known = fh.get(pid) or {}
        if src is not None and src.is_file():
            got = known.get("original") or sha256_file(src)
            if got != rec["sha256"]:
                raise PipelineError("photo_sha_mismatch", "photo file does not match its recorded SHA-256")
        wc = rec.get("working_copy")
        wc_sha, wc_wh = None, None
        if wc:
            p = Path(wc) if Path(wc).is_absolute() else root / wc
            if not p.is_file():
                raise PipelineError("working_copy_missing", "working copy file not found")
            wc_sha = known.get("working_copy") or sha256_file(p)
            img = load_working_copy(root, wc)
            wc_wh = [int(img.shape[1]), int(img.shape[0])]
        ex_wh = (rec.get("exif") or {}).get("wh")
        wh = wc_wh or (list(ex_wh) if ex_wh else None)
        out.append({"id": pid, "sha256": rec["sha256"], "rights_basis": rec["rights_basis"],
                    "include": rec.get("include", "auto"), "tags": dict(rec.get("tags") or {}),
                    "exif": dict(rec.get("exif") or {}), "focal_group": rec.get("focal_group"),
                    "working_copy": wc, "working_copy_sha256": wc_sha, "wh": wh,
                    "orientation_applied": wc is not None})
    kit = load_kit(inputs["template"], root)
    return {"photos": out, "template": {"id": kit.id, "topology_sha256": kit.topology_sha256},
            "n_photos": len(out)}


# ============================================================================ stage: triage
def stage_triage(inputs: dict, config: dict, seed: int) -> dict:
    """QA findings, occluder actions and the focal / distance ladders (DESIGN 4.1, 4.2).

    Per photo: ``findings`` (:class:`face3d.qa.checks.Finding` dicts), ``usable`` (False when a
    finding excludes the geometry and the user did not force ``include: true``), ``f_px`` and
    ``f_log_sigma`` with ``f_source`` (the ladder rule), ``distance_mm`` / ``distance_sigma_log``,
    and the ``occluder`` actions.  Set-level findings are in ``set_findings``.
    """
    root = Path(inputs["_ctx"]["root"])
    photos = inputs["photos"]
    exifs = {p["id"]: exif_from_summary(p["exif"]) if p["exif"] else None for p in photos}
    modes = _focal_group_mode(exifs)
    ctxs, per = [], []
    for p in photos:
        wh = p["wh"]
        if not wh:
            raise PipelineError("photo_size_unknown", "photo size unknown: supply a working copy or EXIF")
        gray = None
        if p["working_copy"]:
            gray = _imops.to_gray(load_working_copy(root, p["working_copy"]))
        ctx = _qa.PhotoContext(photo_id=p["id"], exif=exifs[p["id"]], width=int(wh[0]), height=int(wh[1]),
                               orientation_applied=bool(p["orientation_applied"]), image_gray=gray)
        ctxs.append(ctx)
    set_findings = _qa.run_set_checks(ctxs)
    for p, ctx in zip(photos, ctxs):
        ex = ctx.exif
        findings = _qa.run_photo_checks(ctx)
        if ex is None:
            ex = exif_from_summary({})
        fp = _focal.focal_prior_from_evidence(ex, ctx.width, ctx.height,
                                              group_crop_ratio_mode=modes.get(p["id"]))
        dp = _focal.distance_prior_head_origin(ex, is_front_camera=ex.is_front_camera)
        tags = p["tags"]
        occ = _qa.occluder_actions(tags.get("occluders", []))
        blocked = any(f.action == "exclude_geometry" for f in findings)
        inc = p["include"]
        usable = (inc is True) or (inc == "auto" and not blocked)
        per.append({
            "id": p["id"], "usable": bool(usable), "wh": [ctx.width, ctx.height],
            "sha256": p["sha256"], "working_copy_sha256": p.get("working_copy_sha256"),
            "include": p["include"],
            "findings": [_plain(asdict(f)) for f in findings],
            "f_px": float(fp.f_px), "f_log_sigma": float(fp.log_sigma), "f_source": str(fp.source_code),
            "distance_mm": float(dp.median_mm), "distance_sigma_log": float(dp.sigma_log),
            "front_camera": bool(ex.is_front_camera), "focal_group": p["focal_group"],
            "occluder": _plain(occ), "tags": _plain(tags),
            "wide": any(f.code == "Q-WIDE" for f in findings),
        })
    return {"photos": per, "set_findings": [_plain(asdict(f)) for f in set_findings]}


# ============================================================================ landmarks helpers
def _engine_points(kit: TemplateKit, plain_sets: Mapping[str, dict], usable: Sequence[str]) -> dict:
    """Engine point list: the 44 anatomical ids + one scheme's non-anatomical points (see module doc)."""
    ids_A = list(kit.landmark_names("anatomical44"))
    prior_ids = list(FactorPrior.from_package().ids)
    if ids_A != prior_ids:
        raise PipelineError("kit_prior_mismatch", "kit anatomical44 ids differ from the packaged prior")
    c_scheme, c_names, c_kinds = None, [], []
    for pid in usable:
        sname = plain_sets[pid]["scheme"]
        if sname == "anatomical44" or sname not in kit.schemes:
            continue
        sc = load_scheme(sname)
        in_kit = set(kit.landmark_names(sname))
        c_scheme = sname
        for sp in sc.points:
            if sp.anatomical_id is None and sp.name in in_kit and sp.kind != "iris":
                c_names.append(sp.name)
                c_kinds.append(sp.kind)
        break
    ids = ids_A + [f"{c_scheme}:{n}" for n in c_names]
    kinds = [ANATOMICAL[i].kind for i in ids_A] + c_kinds
    return {"ids": ids, "kinds": kinds, "n_A": len(ids_A), "c_scheme": c_scheme, "c_names": c_names}


def _engine_perm(ids: Sequence[str], n_A: int, c_scheme: str | None, c_names: Sequence[str]) -> np.ndarray:
    """Label permutation of a horizontal flip over the engine points (pairs swapped, others fixed)."""
    perm = np.arange(len(ids))
    index = {i: k for k, i in enumerate(ids)}
    for k, lid in enumerate(ids[:n_A]):
        m = ANATOMICAL[lid].mirror_id
        if m and m in index and m != lid:
            perm[k] = index[m]
    if c_scheme:
        sc = load_scheme(c_scheme)
        pi = sc.mirror_permutation()
        names = sc.names()
        for k, n in enumerate(c_names):
            j = pi[names.index(n)]
            partner = names[j]
            key = f"{c_scheme}:{partner}"
            if partner != n and key in index:
                perm[n_A + k] = index[key]
    return perm


def _approx_ppm(uv: np.ndarray, X_ref: np.ndarray) -> float:
    """px per mm from the image spread vs the template spread of the visible points (init only)."""
    vis = np.isfinite(uv[:, 0])
    if vis.sum() < 3:
        return 1.0
    u, x = uv[vis], X_ref[vis]
    s_img = float(np.sqrt(np.mean(np.sum((u - u.mean(0)) ** 2, axis=1))))
    s_mm = float(np.sqrt(np.mean(np.sum((x - x.mean(0)) ** 2, axis=1)))) * np.sqrt(2.0 / 3.0)
    return s_img / max(s_mm, 1e-9)


def _class_ids(ids: Sequence[str], n_A: int, cls: str) -> list[int]:
    """Engine indices of a generic occluder class (``qa.checks.occluder_actions`` names)."""
    out = []
    for k, lid in enumerate(ids[:n_A]):
        lm = ANATOMICAL[lid]
        if cls == "eye" and lm.region == "eyes":
            out.append(k)
        elif cls == "lip_border" and lm.region == "lips":
            out.append(k)
        elif cls == "ear" and lm.region == "ears":
            out.append(k)
        elif cls == "temple" and lm.base == "t":
            out.append(k)
        elif cls == "lid_points_under_frame" and lm.base in ("ps", "pi"):
            out.append(k)
        elif cls == lm.base:
            out.append(k)
    return out


# ============================================================================ stage: landmarks
def stage_landmarks(inputs: dict, config: dict, seed: int) -> dict:
    """LandmarkSets and pins to per-view observations on the engine point list (DESIGN 2.4, 3.1, 4.3, 4.9).

    ``inputs``: ``photos`` (triage rows), ``landmark_sets`` {photo id: plain LandmarkSet}, ``pins``,
    ``flip`` (sorted ids with a recorded mirror_flip decision), ``template``, ``_ctx``.  Steps per
    usable photo: select the face (``config['face_index']``, default 0; a second face is never
    fitted, eth F1), resize into the working frame, apply the recorded flip (``flip_uv`` with the
    scheme permutation, covariances reflected), map the scheme to the engine points, resolve
    geometric L/R groups from geometry (``model.registry.resolve_lr``, finding ``Q-LR-AMBIG``),
    apply occluder drops and sigma multipliers, expression tags (blendshapes, else mouth-width
    fallback) and user pins (sigma by pin class, D-09).  Per-landmark information weights are
    ``1 / multiplier^2`` (``ViewObs.weights``).  Unverified scheme points are inflated by
    ``pipeline.unverified_sigma_mult`` (provisional).
    """
    root = Path(inputs["_ctx"]["root"])
    kit = load_kit(inputs["template"], root)
    rows = [p for p in inputs["photos"] if p["usable"]]
    if not rows:
        raise PipelineError("no_usable_photos", "no photo is usable")
    sets = inputs["landmark_sets"]
    for r in rows:
        if r["id"] not in sets:
            raise PipelineError("missing_landmarks", "no landmark set for a usable photo")
    flip = set(inputs.get("flip", []))
    pts = _engine_points(kit, sets, [r["id"] for r in rows])
    ids, kinds, n_A = pts["ids"], pts["kinds"], pts["n_A"]
    N = len(ids)
    index = {i: k for k, i in enumerate(ids)}
    perm_eng = _engine_perm(ids, n_A, pts["c_scheme"], pts["c_names"])
    prior_mean = FactorPrior.from_package().mean()
    X_ref = np.vstack([prior_mean, np.zeros((N - n_A, 3))])
    tab = _noise.kind_tables()
    face_index = int(config.get("face_index", 0))
    P = len(rows)
    uv = np.full((P, N, 2), np.nan)
    wgt = np.ones((P, N))
    pinm = np.zeros((P, N), bool)
    cov_in = np.full((P, N, 2, 2), np.nan)
    findings, tags, flips_applied, iris_px = [], [], [], np.full((P, 2), np.nan)
    blend = []
    n_ver, n_unv = np.zeros(N), np.zeros(N)         # verified / unverified scheme observations per point
    qa_find: dict = {r["id"]: [] for r in rows}      # landmark-aware QA findings per photo
    set_find = list(inputs["triage"].get("set_findings", []))
    excl: set = set()
    wide_lm = [False] * P
    pin_rows = [p for p in inputs.get("pins", [])]
    for v, r in enumerate(rows):
        pid = r["id"]
        ls = sets[pid]
        if not ls["faces"]:
            raise PipelineError("no_face", "landmark set has no face")
        if len(ls["faces"]) > 1:
            findings.append({"code": "Q-FACES", "photo": pid, "action": "first_face_used"})
        face = ls["faces"][face_index]
        sc = load_scheme(ls["scheme"])
        W, H = r["wh"]
        img = ls.get("image") or {}
        if img.get("sha256") and img["sha256"] not in (r.get("sha256"), r.get("working_copy_sha256")):
            raise PipelineError("landmarks_image_mismatch", "landmark set was detected on another image")
        if img.get("orientation_applied") is False:
            findings.append({"code": "Q-ORIENT", "photo": pid, "action": "ask"})
        u = np.array(face["uv"], float)
        if face.get("visible") is not None:
            vis = np.asarray(face["visible"], bool)
            u[~vis] = np.nan
        wh_in = (ls.get("image") or {}).get("wh")
        if wh_in and (int(wh_in[0]) != int(W) or int(wh_in[1]) != int(H)):
            u = _imops.resize_uv(u, wh_in[0], wh_in[1], W, H)
        cv = None if face.get("cov") is None else np.array(face["cov"], float)
        if img.get("input_flipped"):
            # the detector ran on a mirrored copy of the image: bring the points back to the photo's frame
            pi0 = sc.mirror_permutation()
            u = _imops.flip_uv(u, float(wh_in[0]) if wh_in else W, pi0)
            if cv is not None:
                cv = _mirror.flip_cov(cv, pi0)
            findings.append({"code": "L-INPUT-UNFLIPPED", "photo": pid, "action": "none"})
        if wh_in and cv is not None and (int(wh_in[0]) != int(W) or int(wh_in[1]) != int(H)):
            cv = cv * np.array([W / wh_in[0], H / wh_in[1]])[None, :, None] * \
                np.array([W / wh_in[0], H / wh_in[1]])[None, None, :]
        if pid in flip:
            pi = sc.mirror_permutation()
            u = _imops.flip_uv(u, W, pi)
            if cv is not None:
                cv = _mirror.flip_cov(cv, pi)
            flips_applied.append(pid)
        if len(u) != sc.n:
            raise PipelineError("scheme_size_mismatch", "landmark count does not match its scheme")
        mult = np.ones(N)
        # --- anatomical correspondences
        aidx = sc.anatomical_index()
        for lid, si in aidx.items():
            k = index.get(lid)
            if k is None:
                continue
            uv[v, k] = u[si]
            if cv is not None:
                cov_in[v, k] = cv[si]
            if np.isfinite(u[si]).all():
                (n_ver if sc.points[si].verified else n_unv)[k] += 1
        # --- geometric L/R groups (iris rings): sides from geometry, never from indices (DESIGN 3.1)
        mid_u = [uv[v, k, 0] for k, lid in enumerate(ids[:n_A]) if ANATOMICAL[lid].side == "mid"
                 and np.isfinite(uv[v, k, 0])]
        by_base: dict = {}
        for g in sc.lr_groups:
            if g.get("anatomical_id") and np.isfinite(u[g["indices"]]).any():
                by_base.setdefault(g["anatomical_id"], []).append(g)
        for base, groups in by_base.items():
            if len(groups) > 2:
                continue
            mu = float(np.median(mid_u)) if mid_u else None
            try:
                assign, amb = _registry_resolve_lr({g["name"]: u[g["indices"]] for g in groups}, mu)
            except ValueError:
                continue
            if amb:
                findings.append({"code": "Q-LR-AMBIG", "photo": pid, "action": "ask"})
            for g in groups:
                lid = f"{base}_{assign[g['name']]}"
                k = index.get(lid)
                if k is None:
                    continue
                c_i = int(g.get("centre_index", g["indices"][0]))
                uv[v, k] = u[c_i]
                if np.isfinite(u[c_i]).all():
                    (n_ver if all(sc.points[i].verified for i in g["indices"][:1]) else n_unv)[k] += 1
                ring = u[[i for i in g["indices"] if i != c_i]]
                if np.isfinite(ring).all() and base == "p":
                    rad = float(np.mean(np.linalg.norm(ring - u[c_i], axis=1)))
                    iris_px[v, 0 if assign[g["name"]] == "L" else 1] = rad
        # --- non-anatomical points of the conditional-prior scheme
        if pts["c_scheme"] and ls["scheme"] == pts["c_scheme"]:
            names = sc.names()
            for j, n in enumerate(pts["c_names"]):
                si = names.index(n)
                k = n_A + j
                uv[v, k] = u[si]
                if cv is not None:
                    cov_in[v, k] = cv[si]
                if np.isfinite(u[si]).all():
                    (n_ver if sc.points[si].verified else n_unv)[n_A + j] += 1
        # --- occluder actions (DESIGN 4.1, Rob 3.6)
        occ = r["occluder"]
        for cls_name, f in occ["sigma_mult"].items():
            for k in _class_ids(ids, n_A, cls_name):
                mult[k] *= float(f)
        for cls_name in occ["drop_classes"]:
            for k in _class_ids(ids, n_A, cls_name):
                uv[v, k] = np.nan
        # --- expression tag inputs
        blend.append(face.get("blendshapes"))
        # --- pins (user pins carry the pin-class sigma, D-09)
        ppm = _approx_ppm(uv[v], X_ref)
        face_px = float(np.ptp(uv[v][np.isfinite(uv[v, :, 0]), 0])) if np.isfinite(uv[v, :, 0]).sum() > 1 else None
        iso = np.sqrt(0.5 * np.trace(_noise.NoiseModel(kinds).view_cov(np.full(N, ppm), face_px),
                                     axis1=1, axis2=2))
        for pin in pin_rows:
            if pin["photo"] != pid:
                continue
            k = index.get(pin["target"]["landmark"])
            if k is None:
                raise PipelineError("pin_unknown_landmark", "pin targets an unknown landmark")
            uv[v, k] = np.asarray(pin["xy_px"], float)
            cls = resolve_pin_class(pin.get("cls", "crisp"), pin.get("expertise", "novice"))
            sig = float(_noise.pin_sigma_px(cls, ppm, float(pin.get("zoom", 1.0))))
            mult[k] = float(np.clip(sig / max(iso[k], 1e-9), 0.05, 20.0))
            pinm[v, k] = True
            cov_in[v, k] = np.nan
        # --- landmark-aware QA (DESIGN 4.1): face size, off-axis, blink, faces; actions applied here
        lf = _landmark_qa(r, ls["faces"], uv[v], ids, index, iris_px[v])
        pf = [f for f in lf if f["action"] != "none" or f["severity"] != "info"] + \
            [f for f in set_find if f.get("photo_id") == pid]
        qa_find[pid] = lf
        vm = 1.0
        for f in pf:
            if f["action"] == "down_weight" and f["code"] in ("Q-SMALL", "Q-BLUR"):
                vm = max(vm, float(config.get("downweight_sigma_mult", _P["downweight_sigma_mult"])))
            if f["action"] == "drop_class" and f["code"] == "Q-BLINK":
                for side in (f.get("detail") or {}).get("eyes", []):
                    for base in ("ps", "pi"):
                        k = index.get(f"{base}_{side}")
                        if k is not None:
                            uv[v, k] = np.nan
            if f["action"] == "exclude_geometry" and r.get("include") is not True:
                excl.add(v)
        mult[~pinm[v]] *= vm
        if any(f["code"] == "Q-WIDE" for f in lf):
            wide_lm[v] = True
        wgt[v] = 1.0 / mult ** 2
    if excl:
        keep = [v for v in range(P) if v not in excl]
        if not keep:
            raise PipelineError("no_usable_photos", "no photo passes the size gate")
        excluded = [{"photo": rows[v]["id"], "codes": sorted({f["code"] for f in qa_find[rows[v]["id"]]
                                                               if f["action"] == "exclude_geometry"})}
                    for v in sorted(excl)]
        rows = [rows[v] for v in keep]
        uv, wgt, pinm, iris_px = uv[keep], wgt[keep], pinm[keep], iris_px[keep]
        blend = [blend[v] for v in keep]
        wide_lm = [wide_lm[v] for v in keep]
        flips_applied = [x for x in flips_applied if x in {r["id"] for r in rows}]
        P = len(rows)
    else:
        excluded = []
    # ---- expression tags
    scores = [b if isinstance(b, dict) else None for b in blend]
    neutral_ref = next((i for i, r in enumerate(rows) if r["tags"].get("neutral_reference")), None)
    bs_tags = _expr.tag_from_blendshapes(scores, neutral_ref=neutral_ref)
    sidx = {k: index[k] for k in ("ch_L", "ch_R", "ex_L", "ex_R", "sto", "li") if k in index}
    widths = [_expr.mouth_width(uv[v], sidx) for v in range(P)]
    med_w = float(np.nanmedian(widths)) if np.isfinite(widths).any() else None
    etags, drops = [], []
    for v, r in enumerate(rows):
        user = r["tags"].get("expression", "auto")
        if user in ("neutral", "mild", "expressive"):
            etags.append(user)
            continue
        if bs_tags[v] is not None:
            etags.append(bs_tags[v])
            continue
        tag, drop_ids = _expr.tag_fallback(uv[v], sidx, med_w)
        etags.append(tag)
        for k in drop_ids:
            uv[v, k] = np.nan
            drops.append([rows[v]["id"], ids[k]])
    return {
        "ids": ids, "kinds": kinds, "n_A": n_A, "c_scheme": pts["c_scheme"], "c_names": pts["c_names"],
        "photo_ids": [r["id"] for r in rows], "uv": uv, "weights": wgt, "pin_mask": pinm,
        "perm": perm_eng, "expression_tags": etags, "iris_px": iris_px,
        "flips_applied": flips_applied, "findings": findings, "expression_drops": drops,
        "photo_findings": {pid: [dict(f) for f in fl] + [{"code": f["code"], "severity": "warn",
                                                           "action": f["action"], "detail": None}
                                                          for f in findings if f["photo"] == pid]
                           for pid, fl in qa_find.items()},
        "excluded": excluded, "wide_lm": wide_lm,
        "sigma_def_mult": np.where((n_unv > 0) & (n_ver == 0), float(_P["unverified_sigma_mult"]), 1.0),
        "detectors": [sets[r["id"]].get("detector", {}) for r in rows],
        "image_wh": [list(r["wh"]) for r in rows],
    }


_LM_QA_CODES = ("Q-SMALL", "Q-WIDE", "Q-FACES")


def _landmark_qa(row: dict, faces: Sequence[dict], uv_v: np.ndarray, ids: Sequence[str],
                 index: Mapping[str, int], iris_rad: np.ndarray) -> list:
    """Landmark-aware photo QA (DESIGN 4.1): :func:`face3d.qa.checks.run_photo_checks` with the face size
    (max extent of the observed points), its centre, the iris diameter (2 x mean ring radius), the number
    of detected faces.  Q-BLINK needs the six eyelid-contour points of each eye (``eye_pts6``); no scheme in
    the registry lists them (and none may be invented), so Q-BLINK is not evaluated until one does.  Only
    the findings that need landmarks are returned (Q-SMALL, Q-WIDE off-axis, Q-FACES) and only those the
    triage did not report."""
    fin = np.isfinite(uv_v).all(axis=1)
    face_px = centre = None
    if int(fin.sum()) >= 2:
        pts = uv_v[fin]
        lo, hi = pts.min(axis=0), pts.max(axis=0)
        face_px, centre = float(np.max(hi - lo)), 0.5 * (lo + hi)
    rad = np.asarray(iris_rad, float)
    iris = float(2.0 * np.mean(rad[np.isfinite(rad)])) if np.isfinite(rad).any() else None
    ex = exif_from_summary(row["exif"]) if row.get("exif") else None
    ctx = _qa.PhotoContext(photo_id=row["id"], exif=ex, width=int(row["wh"][0]), height=int(row["wh"][1]),
                           face_px=face_px, face_centre_px=centre, iris_px=iris, f_px=float(row["f_px"]),
                           n_faces=len(faces), face_scores=[float(f.get("score", 1.0)) for f in faces],
                           )
    have = {f["code"] for f in row["findings"]}
    return [_plain(asdict(f)) for f in _qa.run_photo_checks(ctx)
            if f.code in _LM_QA_CODES and f.code not in have]


def _registry_resolve_lr(groups: Mapping[str, np.ndarray], face_midline_u: float | None):
    from face3d.model.registry import resolve_lr
    if len(groups) == 1 and face_midline_u is None:
        raise ValueError("one group needs a midline")
    return resolve_lr(groups, face_midline_u=face_midline_u)


# ============================================================================ stage: solve
def _build_prior(kit: TemplateKit, lm: dict, settings: Mapping[str, Any]):
    """FactorPrior(sex, population) on the anatomical points, composed with the conditional
    template prior for non-anatomical points (DESIGN 4.6)."""
    sex = settings.get("sex_prior", "unspecified")
    pop = settings.get("population", "unknown")
    fp = FactorPrior.from_package(sex=sex, population=pop)
    n_A, N = lm["n_A"], len(lm["ids"])
    if N == n_A:
        return fp
    ctp = ConditionalTemplatePrior(kit, lm["c_scheme"], lm["c_names"], lm["ids"][:n_A],
                                   index_A=np.arange(n_A), index_C=n_A + np.arange(N - n_A), n_total=N)
    return CompositePrior([(fp, np.arange(n_A)), ctp], N, ids=lm["ids"])


def _sigma_def(ids: Sequence[str], kinds: Sequence[str], n_A: int) -> np.ndarray:
    nm = _noise.NoiseModel(list(kinds)).sigma_def_mm()
    out = np.asarray(nm, float).copy()
    for k, lid in enumerate(ids[:n_A]):
        out[k] = ANATOMICAL[lid].sigma_def_mm
    return out


def _focal_obj(f_px: float, log_sigma: float):
    class _F:
        pass
    o = _F()
    o.f_px, o.log_sigma = float(f_px), float(log_sigma)
    return o


def _make_views(res, lm: dict, tri: list, cov_px: list | None, uv_override: list | None,
                jaws: list | None, view_cfg: dict) -> list[ViewObs]:
    views = []
    for v, row in enumerate(tri):
        u = lm["uv"][v] if uv_override is None else uv_override[v]
        views.append(ViewObs(
            uv=u, camera=res.cameras[v].copy(), estimate_focal=True, f_prior=row["f_px"],
            f_prior_log_sigma=row["f_log_sigma"], weights=None if cov_px is not None else lm["weights"][v],
            focal_group=row["focal_group"], kinds=lm["kinds"], cov_px=None if cov_px is None else cov_px[v],
            focal_tie_sigma=float(view_cfg["focal_tie_sigma"]),
            distance_prior=(row["distance_mm"], row["distance_sigma_log"]),
            jaw=jaws[v] if jaws is not None else JawConfig()))
    return views


def _whitened_e2(res, v: int) -> np.ndarray:
    """Squared whitened radial residuals (N,) of view ``v``: ``r^2 / sigma_iso^2`` with r the radial
    pixel residual (``per_view_residuals``) and ``sigma_iso^2 = trace(Sigma) / 2`` of the declared noise
    (chi^2 with 2 dof under the model; NaN where hidden)."""
    r = np.asarray(res.per_view_residuals[v], float)
    cov = np.asarray(res.obs_cov_px[v], float)
    var = 0.5 * (cov[:, 0, 0] + cov[:, 1, 1])
    with np.errstate(invalid="ignore", divide="ignore"):
        return r ** 2 / var


def stage_solve(inputs: dict, config: dict, seed: int) -> dict:
    """Multi-start PnP, bundle v2 with the nuisance passes and the symmetry term (DESIGN 4.3-4.11).

    Pass 1 (:func:`reconstruct_landmarks`): ``CompositePrior(FactorPrior(sex, population),
    ConditionalTemplatePrior)`` (FactorPrior alone for the 44 anatomical points), the log-scale
    zeta with the population source of ``settings.scale_population_source``
    (``solve.scale.population_scale_setup``), caliper chords from ``scale_refs``,
    ``RobustSchedule``, view weighting, the soft focal tie 0.02 (``pipeline.focal_tie_sigma``),
    head-origin distance priors and the gauge anchors.  Nuisances, from the pass-1 estimate:
    the mirror test per view against the leave-one-view-out consensus (decision *cards* only,
    D-10); expression inflation per view tag with up to ``pipeline.max_retag_rounds`` re-tag
    rounds and the jaw hinge; the camera-model selection of Q-WIDE views (recorded; a non-pinhole
    selection is flagged ``C-MODEL-NOT-APPLIED`` and only inflates sigma x3 when ambiguous);
    the evidence-gated symmetry term (plane refitted on the pass-1 points).  Pass 2 re-solves.
    """
    lm = inputs["landmarks"]
    tri_all = {r["id"]: r for r in inputs["triage"]["photos"]}
    tri = [tri_all[pid] for pid in lm["photo_ids"]]
    # iris observations name a view by index into ``landmarks.photo_ids`` (or by photo id): fix them to
    # photo ids now so that dropping a view below cannot shift them onto another camera
    iris = []
    for o in (inputs.get("iris_obs") or []):
        v = o[0]
        pid = v if isinstance(v, str) else (lm["photo_ids"][int(v)] if 0 <= int(v) < len(lm["photo_ids"]) else None)
        iris.append((pid,) + tuple(o[1:]))
    out = _solve_core(inputs, config, seed, lm, tri, iris, None, [])
    return out


def _slice_landmarks(lm: dict, keep: Sequence[int]) -> dict:
    """The landmarks-stage output restricted to the views ``keep`` (per-view arrays and lists)."""
    out = dict(lm)
    for k in ("uv", "weights", "pin_mask", "iris_px"):
        out[k] = np.asarray(lm[k])[list(keep)]
    for k in ("expression_tags", "detectors", "image_wh", "wide_lm"):
        if k in lm:
            out[k] = [lm[k][i] for i in keep]
    out["photo_ids"] = [lm["photo_ids"][i] for i in keep]
    out["flips_applied"] = [x for x in lm["flips_applied"] if x in out["photo_ids"]]
    return out


def _solve_core(inputs: dict, config: dict, seed: int, lm: dict, tri: list, iris_obs: list,
                near_done: Any, post_excl: list) -> dict:
    root = Path(inputs["_ctx"]["root"])
    kit = load_kit(inputs["template"], root)
    settings = inputs["settings"]
    ids, kinds, n_A = lm["ids"], lm["kinds"], lm["n_A"]
    N, P = len(ids), len(tri)
    index = {i: k for k, i in enumerate(ids)}
    cfg = {"focal_tie_sigma": float(_P["focal_tie_sigma"]), "max_iter": 100, **config}
    prior = _build_prior(kit, lm, settings)
    sdef = _sigma_def(ids, kinds, n_A) * np.asarray(lm.get("sigma_def_mult", np.ones(N)), float)
    anchors = [index[a] for a in anchor_ids() if a in index]
    jaw_w = np.array([ANATOMICAL[i].jaw_weight if k < n_A else 0.0 for k, i in enumerate(ids)])
    flags: list[str] = []

    # ---- scale: population source and metric references
    scale_terms, scale_kinds = [], []
    pupil = (index["p_L"], index["p_R"])
    z_med = float(np.median([r["distance_mm"] for r in tri]))
    src = settings.get("scale_population_source", "global_size")
    scale_cfg, pop_terms = _scale.population_scale_setup(src, pupil_idx=pupil, z_mm=z_med)
    scale_terms += pop_terms
    for ref in inputs.get("scale_refs", []):
        kind = ref.get("kind", "caliper")
        if kind not in ("caliper", "tape"):
            flags.append("S-REF-UNSUPPORTED")
            continue
        a, b = index[ref["a"]], index[ref["b"]]
        scale_terms.append(_scale.ChordTerm(a, b, float(ref["mm"]), float(ref.get("sigma_mm", 0.5)),
                                            definition_sigma_mm=(sdef[a], sdef[b]), name=f"chord_{ref['a']}_{ref['b']}"))
        scale_kinds.append("caliper")
    iris_terms, n_iris_dropped = _iris_terms(lm, tri, iris_obs, ids)
    if n_iris_dropped:
        flags.append("S-IRIS-UNUSABLE")
    scale_terms += iris_terms
    if iris_terms:
        scale_kinds.append("iris")
    scale_mode = "measured" if "caliper" in scale_kinds else ("iris" if "iris" in scale_kinds else "prior")

    photos = []
    for v, r in enumerate(tri):
        photos.append(PhotoLandmarks(lm["uv"][v], int(r["wh"][0]), int(r["wh"][1]),
                                     focal_prior=_focal_obj(r["f_px"], r["f_log_sigma"]),
                                     focal_group=r["focal_group"], weights=lm["weights"][v], kinds=kinds))
    dps = [(r["distance_mm"], r["distance_sigma_log"]) for r in tri]
    bkw = dict(prior=prior, scale=scale_cfg, gauge_anchor_idx=anchors, sigma_def_mm=sdef,
               robust=RobustSchedule(), view_weighting=True)
    res1 = reconstruct_landmarks(photos, None, max_iter=int(cfg["max_iter"]), distance_priors=dps,
                                 terms=scale_terms or None, focal_tie_sigma=float(cfg["focal_tie_sigma"]), **bkw)
    # ---- Q-NEAR on the solved head distance (DESIGN 4.1): exclude re-solves without the view, the
    # down-weight levels inflate the view's sigma in pass 2
    post_find: dict = {r["id"]: [] for r in tri}
    near_mult = [1.0] * P
    near_excl: list = []
    for v, r in enumerate(tri):
        z = float(res1.cameras[v].depth(np.zeros((1, 3)))[0])
        for f in _qa.run_photo_checks(_qa.PhotoContext(photo_id=r["id"], width=int(r["wh"][0]),
                                                       height=int(r["wh"][1]), solved_distance_mm=z)):
            if f.code != "Q-NEAR":
                continue
            post_find[r["id"]].append(_plain(asdict(f)))
            if f.action == "down_weight":
                near_mult[v] = float(config.get("downweight_sigma_mult", _P["downweight_sigma_mult"]))
            elif f.action == "exclude_geometry" and r.get("include") is not True:
                near_excl.append(v)
    if near_excl and near_done is None and P - len(near_excl) >= 2:
        keep = [v for v in range(P) if v not in near_excl]
        gone = [{"photo": tri[v]["id"], "codes": ["Q-NEAR"], "findings": post_find[tri[v]["id"]]}
                for v in near_excl]
        return _solve_core(inputs, config, seed, _slice_landmarks(lm, keep), [tri[v] for v in keep],
                           iris_obs, True, post_excl + gone)
    RI = _ob.default_region_index(ids)
    A1 = _ob.assess(res1, region_index=RI, prior_log_sigma=[r["f_log_sigma"] for r in tri])
    views1 = _make_views(res1, lm, tri, None, None, None, cfg)

    # ---- nuisance 1: mirror test per view (cards only)
    cards, mirror_dec = [], []
    all_front = all(r["front_camera"] for r in tri)
    solve_wo = None
    if P >= int(_P["lovo_min_views"]):
        solve_wo = _ob.make_solve_without(views1, res1, bundle_kwargs={**bkw, "terms": None})
    for v, r in enumerate(tri):
        cam = res1.cameras[v]
        C = view_noise_cov(views1[v], res1.X, cam.R, cam.t, cam.f)
        try:
            cons = solve_wo(v).X if solve_wo is not None else res1.X
            d = _mirror.mirror_test(lm["uv"][v], float(r["wh"][0]), lm["perm"], cons, C, cam,
                                    is_front_camera=r["front_camera"], all_views_front=all_front,
                                    other_views_agree=False)
        except ValueError:
            d = None
        mirror_dec.append(d)
        m = {"decision": "undetermined", "delta": None, "g": None, "margin": None} if d is None else \
            {"decision": d.decision, "delta": float(d.delta), "g": float(d.g), "margin": float(d.margin)}
        m["applied"] = lm["photo_ids"][v] in lm["flips_applied"]
        cards.append({"kind": "mirror_flip", "photo": lm["photo_ids"][v], **m,
                      "preselect": bool(d.preselect_flip) if d is not None else False})
    mirror_status = _mirror.project_mirror_status([d for d in mirror_dec if d is not None], all_front) \
        if any(d is not None for d in mirror_dec) else {"status": "undetermined"}
    cards = [c for c in cards if c["decision"] == "suggest_flip" and not c["applied"]] + \
        [c for c in cards if not (c["decision"] == "suggest_flip" and not c["applied"])]

    # ---- nuisance 2: expression tags, jaw, camera-model selection
    classes = _expr.expression_classes([i if k < n_A else None for k, i in enumerate(ids)])
    sig_n = np.array([_noise.kind_tables()["sigma_mm"][k][0] for k in kinds], float)
    tags = list(lm["expression_tags"])
    cam_models = []
    ms = [1.0] * P
    face_c = res1.X[[index[i] for i in ("en_L", "en_R", "prn", "sto") if i in index]].mean(axis=0)
    for v, r in enumerate(tri):
        cam = res1.cameras[v]
        model = {"model": "pinhole", "ambiguous": False, "sigma_mult": 1.0}
        if r["wide"] or (lm.get("wide_lm") or [False] * P)[v]:
            C = view_noise_cov(views1[v], res1.X, cam.R, cam.t, cam.f)
            try:
                out = _cm.select_camera_model(lm["uv"][v], res1.X, cam, C, face_c)
                model = {"model": out["model"], "ambiguous": bool(out["ambiguous"]),
                         "sigma_mult": float(out["sigma_mult"])}
                if out["model"] != "pinhole":
                    flags.append("C-MODEL-NOT-APPLIED")
            except (ValueError, np.linalg.LinAlgError):
                pass
        cam_models.append(model)
        ms[v] = model["sigma_mult"] * near_mult[v]

    sym = _sym.SymmetryTerm.from_ids(ids, region_status=A1["region_status"])
    try:
        sym.update_plane(res1.X)
    except (ValueError, np.linalg.LinAlgError):
        pass
    terms2 = list(scale_terms) + [sym]

    def pass2(tag_list):
        covs, uvs, jaws = [], [], []
        for v in range(P):
            cam = res1.cameras[v]
            base = view_noise_cov(views1[v], res1.X, cam.R, cam.t, cam.f)
            base = base / lm["weights"][v][:, None, None] * ms[v] ** 2
            s_expr, drop = _expr.expression_sigma_mm(classes, sig_n, tag_list[v])
            Pj = _expr.projection_jacobians(cam, res1.X)
            c2 = _expr.inflate_view_cov(base, Pj, s_expr)
            u = lm["uv"][v].copy()
            u[np.asarray(drop, bool)] = np.nan
            c2[~np.isfinite(u[:, 0])] = np.nan
            covs.append(c2)
            uvs.append(u)
            jaws.append(_expr.jaw_config_for_tag(tag_list[v]))
        vws = _make_views(res1, lm, tri, covs, uvs, jaws, cfg)
        for vw in vws:
            vw.weights = None
        kw = dict(bkw)
        return vws, bundle_adjust(vws, res1.X.copy(), None, max_iter=int(cfg["max_iter"]), terms=terms2,
                                  jaw_weights=jaw_w, **kw)

    views, res = pass2(tags)
    for _ in range(int(_P["max_retag_rounds"])):
        changed = False
        for v in range(P):
            e2 = _whitened_e2(res, v)
            # inliers only: an observation the robust schedule rejected must not re-tag the view
            inl = np.asarray(res.inlier_mask[v], bool)
            mob = [k for k in range(N) if classes[k] == "mobile" and np.isfinite(e2[k]) and inl[k]]
            if not mob:
                continue
            new = _expr.retag_from_residuals(_expr.mobile_chi2_red(e2[mob]), tags[v])
            if new != tags[v]:
                tags[v] = new
                changed = True
        if not changed:
            break
        views, res = pass2(tags)
    nn = _expr.no_neutral_view(tags)
    if nn is not None:
        flags.append("E-NO-NEUTRAL")
    flags += list(res.flags)
    flags = sorted(set(flags))
    rv = [np.asarray(res.per_view_residuals[v], float)[np.asarray(res.inlier_mask[v], bool)] for v in range(P)]
    rv = np.concatenate(rv) if rv else np.zeros(0)
    rv = rv[np.isfinite(rv)]

    # ---- plain outputs
    cams = res.cameras
    fx = []
    for c, r in zip(cams, tri):
        fx.append(float(c.f))
    out = {
        "ids": ids, "n_A": n_A, "photo_ids": lm["photo_ids"],
        "X": np.asarray(res.X, float), "cov": np.asarray(res.cov, float),
        "cov_shape": np.asarray(res.cov_shape, float), "point_sigma_mm": np.asarray(res.point_sigma_mm, float),
        "sigma_def_mm": sdef, "inlier_mask": np.asarray(res.inlier_mask, bool),
        "zeta": float(res.zeta), "zeta_sigma": float(res.zeta_sigma), "chi2_red": float(res.chi2_red),
        "cam_K": np.stack([c.K for c in cams]), "cam_R": np.stack([c.R for c in cams]),
        "cam_t": np.stack([c.t for c in cams]), "cam_f": np.array(fx),
        "cam_wh": np.array([[c.width, c.height] for c in cams], float),
        "cam_z": np.array([float(c.depth(np.zeros((1, 3)))[0]) for c in cams]),
        "rmse_px": np.asarray(res.rmse_px, float), "view_stats": _plain(res.view_stats),
        "tags": tags, "camera_models": cam_models, "mirror_cards": cards, "mirror_status": _plain(mirror_status),
        "mirror": [{k: v for k, v in c.items() if k in ("decision", "delta", "g", "margin")}
                   for c in sorted(cards, key=lambda c: lm["photo_ids"].index(c["photo"]))],
        "scale_mode": scale_mode, "scale_kinds": scale_kinds + ([str(src)] if src else []),
        "flags": flags, "iterations": int(res.iterations),
        "symmetry": {"plane_n": np.asarray(sym.n, float).tolist(), "plane_d": float(sym.d),
                     "rmse_mm": None if getattr(sym, "plane_rmse_mm", None) is None else float(sym.plane_rmse_mm)},
        "gamma_pass1": None,
        "reproj_median_px": float(np.median(rv)) if rv.size else None,
        "reproj_max_px": float(np.max(rv)) if rv.size else None,
        "post_findings": post_find, "near_excluded": post_excl,
        "_result": res, "_views": views, "_prior": prior, "_bkw": bkw, "_terms": terms2,
        "_kit": kit, "_jaw_w": jaw_w,
    }
    return out


def _iris_terms(lm: dict, tri: list, iris_obs: Any, ids: Sequence[str]):
    """Iris scale term from supplied limbus observations (``inputs['iris_obs']``: a list of
    ``(view, 'L'|'R', radius_px, sigma_r_px, sharp)`` from a limbus fit, DESIGN 4.7; ``view`` is a photo id
    or an index into ``landmarks.photo_ids``).  Only usable observations are kept
    (:func:`face3d.solve.scale.iris_usable`: diameter >= 20 px, sharp limbus flag supplied with the
    observation, and no glasses tag on that photo); a missing ``sharp`` flag counts as not sharp.
    Landmark-ring radii alone are never used (the 'sharp limbus' gate needs pixels).  Returns
    ``(terms, n_dropped)``; without usable observations there is no iris term."""
    if not iris_obs:
        return [], 0
    index = {i: k for k, i in enumerate(ids)}
    pids = list(lm["photo_ids"])
    obs, dropped = [], 0
    for o in iris_obs:
        v, e, r, sr = o[0], str(o[1]), float(o[2]), float(o[3])
        sharp = bool(o[4]) if len(o) > 4 else False
        if isinstance(v, str):
            v = pids.index(v) if v in pids else -1
        v = -1 if v is None else int(v)
        if not (0 <= v < len(pids)) or e not in ("L", "R") or not (np.isfinite(r) and np.isfinite(sr) and
                                                                     r > 0 and sr > 0):
            dropped += 1
            continue
        d = 2.0 * r
        glasses = bool(tri[v]["occluder"]["flags"].get("no_iris_scale"))
        if not _scale.iris_usable(d, sharp, glasses):
            dropped += 1
            continue
        obs.append(_scale.iris_observation(v, e, r, sr))
    if not obs:
        return [], dropped
    return [_scale.IrisTerm(obs, {"L": index["p_L"], "R": index["p_R"]})], dropped


def _terms_without(terms: Sequence[Any], v: int) -> list:
    """Bundle terms for the leave-one-view-out solve without view ``v``: per-view terms (the iris term)
    drop the observations of ``v`` and renumber the later views, so each observation stays on its camera."""
    out = []
    for t in terms:
        if isinstance(t, _scale.IrisTerm):
            obs = [(w - (1 if w > v else 0), e, d, sg) for (w, e, d, sg) in t.obs if w != v]
            if not obs:
                continue
            pk = None if t.phi_keys is None else {w - (1 if w > v else 0): k for w, k in t.phi_keys.items()
                                                  if w != v}
            t = _scale.IrisTerm(obs, t.eye_idx, (t.mu, t.sd), name=t.name, phi_keys=pk)
        out.append(t)
    return out


def _lovo_solver(views: Sequence[ViewObs], res: Any, bkw: Mapping[str, Any], terms: Sequence[Any],
                 jaw_w: np.ndarray):
    """``solve_without(v)`` for :func:`lovo_gamma` with the per-view terms re-indexed (:func:`_terms_without`)."""
    def solve(v: int):
        poll_cancel()
        kw = {**bkw, "terms": _terms_without(terms, v) or None, "jaw_weights": jaw_w}
        return _ob.make_solve_without(views, res, bundle_kwargs=kw)(v)
    return solve


# ============================================================================ stage: observe
def stage_observe(inputs: dict, config: dict, seed: int) -> dict:
    """Observability, LOVO gamma, sigma_rep, ledger, tier and next-best view (DESIGN 4.12-4.14, D-16..D-19).

    Everything is computed at prior weight 1 by :func:`face3d.solve.observability.assess`.  Occluder
    flags cap region statuses (beard: jaw 'prior-driven'; D-31 caps the ears).  LOVO gamma needs
    ``>= pipeline.lovo_min_views`` views (else gamma = 1 with flag ``L-NO-LOVO``).
    """
    s = inputs["solve"]
    res, views, prior, bkw = s["_result"], s["_views"], s["_prior"], s["_bkw"]
    ids, n_A = s["ids"], s["n_A"]
    tri_all = {r["id"]: r for r in inputs["triage"]["photos"]}
    tri = [tri_all[pid] for pid in s["photo_ids"]]
    RI = _ob.default_region_index(ids)
    flags = list(s["flags"])
    P = len(tri)
    gamma, ratio = 1.0, np.full(P, np.nan)
    if P >= int(_P["lovo_min_views"]):
        wo = _lovo_solver(views, res, bkw, s["_terms"], s["_jaw_w"])
        gamma, ratio, gflags = _ob.lovo_gamma(wo, res, views, res.obs_cov_px)
        flags += list(gflags)
    else:
        flags.append("L-NO-LOVO")
    caps: dict[str, str] = {}
    for r in tri:
        if r["occluder"]["flags"].get("jaw_status"):
            caps["jaw"] = r["occluder"]["flags"]["jaw_status"]
    exif_sig = [r["f_log_sigma"] if r["f_source"] in ("exif_f35", "zoom", "aspect", "calibrated", "sfm",
                                                       "focal_plane") else None for r in tri]
    A = _ob.assess(res, region_index=RI, ids=None, gamma=gamma, views=views,
                   prior_log_sigma=[r["f_log_sigma"] for r in tri], exif_log_sigma=exif_sig,
                   scale_mode=s["scale_mode"], all_selfie=all(r["front_camera"] for r in tri),
                   status_caps=caps or None)
    poll_cancel()
    nm = _noise.NoiseModel(list(inputs["landmarks"]["kinds"]))
    ranked, sentence = _nbv.next_best_view(res.cov_shape, res, res.X, noise_model=nm, region_index=RI,
                                           ids=ids if len(ids) == n_A else None)
    led = _ledger.build_ledger(res, prior, ANATOMICAL, A, next_photo=sentence, flags=flags)
    ref = np.asarray(FactorPrior.from_package().mean(), float)        # the 44 anatomical points (template)
    rs = _scale.reported_scale(res, ref, X=res.X[:n_A], cov=res.cov[:3 * n_A, :3 * n_A],
                               sigma_def_mm=s["sigma_def_mm"][:n_A])
    sc_text = _scale.scale_report(rs["zeta"], rs["sigma"], s["scale_kinds"], reference_sigma=rs["reference_sigma"])
    regions = [{"name": r.name, "status": r.status, "k": _num(r.k), "sigma_rep_mm": _num(r.sigma_rep_mm),
                "coverage": _plain(r.coverage), "why": r.why_key, "next_photo": r.next_photo}
               for r in led.regions]
    flags = sorted(set(flags + list(led.flags)))
    return {
        "regions": regions, "tier": list(led.tier), "scale": {"mode": sc_text["mode"], "zeta": rs["zeta"],
                                                              "sigma_zeta": rs["sigma"], "label": sc_text["label"],
                                                              "sigma_pct": sc_text["sigma_pct"],
                                                              "text": sc_text["text"],
                                                              "reference_sigma": rs["reference_sigma"]},
        "scale_ledger": led.scale_report, "focal_statuses": list(led.focal_statuses),
        "camera_status": _plain(A["camera_status"]), "gamma": float(gamma),
        "lovo_ratio": np.asarray(ratio, float), "sigma_rep_mm": np.asarray(A["sigma_rep_mm"], float),
        "views_used": np.asarray(A["views_used"], bool), "next_photo": sentence, "flags": flags,
        "banner": led.banner, "unverified_defaults": engine_unverified_count(),
        "report_lines": _ledger.report_lines(led), "chi2_red": float(A["chi2_red"]),
        "region_k": _plain(A["region_k"]), "status_caps": _plain(A.get("status_caps", {})),
        "_ledger": led, "_assess": A, "_ranked": ranked,
    }


def _num(x: Any) -> float | None:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if np.isfinite(x) else None


# ============================================================================ stage: fit
def stage_fit(inputs: dict, config: dict, seed: int) -> dict:
    """Staged template warp A-C with gates (DESIGN 4.15) and, when ``inputs['contour_obs']`` holds
    :class:`face3d.fit.contour.ContourObs` (``view`` = index into ``solve.photo_ids``; produced from
    masks or edge snapping on pixels, DESIGN 4.16), stage D: a Gaussian-RBF
    :class:`~face3d.solve.shape_models.LinearBasis` on the stage-C surface, contour residuals with free
    cameras (``fit.template.stage_d``: landmark freeze 0.5 mm with one half-weight retry) and the fold
    gate.  Without ContourObs the stage is skipped and ``contours`` is ``'none'``."""
    s = inputs["solve"]
    kit = s["_kit"]
    n_A = s["n_A"]
    X = s["X"][:n_A]
    ids = s["ids"][:n_A]
    cov = s["cov"][:3 * n_A, :3 * n_A]
    agree = np.sum(s["inlier_mask"][:, :n_A], axis=0)
    poll_cancel()
    r = _tpl.staged_warp(kit, X, ids, sigma_X_mm=_unc.landmark_sigma_mm(cov), views_agree=agree)
    flags = list(r.flags)
    V_fit, stage, contours = np.asarray(r.vertices, float), r.stage, "none"
    cobs = inputs.get("contour_obs")
    poll_cancel()
    if cobs and r.stage in ("B", "C"):
        V_D, cres, dflags = _stage_d(inputs["solve"], kit, V_fit, list(cobs))
        flags += list(dflags)
        if cres is not None and not dflags:
            ok, _ = _tpl.fold_gate(V_fit, V_D, kit.triangles())
            if ok:
                V_fit, stage, contours = V_D, "D", "applied"
            else:
                flags.append("W-FOLD")
                contours = "rolled_back"
        else:
            contours = "rolled_back"
    elif cobs:
        flags.append("W-CONTOURS-SKIPPED")
    out = {"vertices": V_fit, "V_A": np.asarray(r.V_A, float), "stage": stage,
           "flags": [str(f) if not isinstance(f, dict) else str(f.get("code", f)) for f in flags],
           "landmark_rms_mm": _plain(r.landmark_rms_mm), "views_agree": agree.astype(np.int64),
           "similarity_scale": float(r.similarity[0]), "A_rows": np.asarray(r.A_rows, float)
           if r.A_rows is not None else np.zeros((0, 0)), "contours": contours}
    if r.V_B is not None:
        out["V_B"] = np.asarray(r.V_B, float)
    if r.V_C is not None:
        out["V_C"] = np.asarray(r.V_C, float)
    if stage == "D":
        out["V_D"] = V_fit
    return out


def _stage_d(s: dict, kit: TemplateKit, V_C: np.ndarray, obs: list):
    """Stage D (DESIGN 4.15 D): contour fit on a 60-centre Gaussian-RBF basis of the stage-C face."""
    from face3d.mesh.reduced import ReducedDeformer, farthest_point_sample
    from face3d.solve.shape_models import LinearBasis
    res = s["_result"]
    ids = s["ids"]
    X = res.X
    E = X[[ids.index(n) for n in ("en_L", "en_R", "ex_L", "ex_R")]]
    iod_mm = float(np.linalg.norm(0.5 * (E[0] + E[2]) - 0.5 * (E[1] + E[3])))
    views = [dataclasses.replace(v, camera=c.copy(), jaw=JawConfig()) for v, c in zip(s["_views"], res.cameras)]
    iod = [c.f * iod_mm / float(c.depth(E.mean(axis=0, keepdims=True))[0]) for c in res.cameras]
    front = np.flatnonzero(np.asarray(kit.vertices)[:, 2] > 0.0)
    centers = front[farthest_point_sample(np.asarray(kit.vertices)[front], 60)]
    basis = LinearBasis(kit, ReducedDeformer(V_C, centers_idx=centers))
    mask = np.zeros(kit.n_verts, bool)
    mask[front] = True
    return _tpl.stage_d(basis, views, obs, iod, n_outer=2, term_kwargs={"vertex_mask": mask})


# ============================================================================ stage: uncertainty
def stage_uncertainty(inputs: dict, config: dict, seed: int) -> dict:
    """Per-vertex normal sigma sigma_n (DESIGN 4.15 'Uncertainty'): ``Cov(V_j) = A_j Sigma_X A_j^T``
    (stage-B explicit map) plus the region residual sigma, inflated by max(1, gamma^2, chi2_red)
    (4.13); and the measurement support k per vertex (claims ledger) used by the protect mask."""
    s, o, f = inputs["solve"], inputs["observe"], inputs["fit"]
    kit = s["_kit"]
    n_A = s["n_A"]
    cov = s["cov"][:3 * n_A, :3 * n_A]
    A = f["A_rows"]
    V = f["vertices"]
    normals = area_weighted_normals(V, kit.faces)
    normals = normals / np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    regions = np.asarray(kit.vertex_regions(), dtype=object)
    covV = _unc.vertex_cov_stage_b(A, cov) if A.size else np.zeros((len(V), 3, 3))
    lm_regions = [str(kit.vertex_regions()[v]) for v in kit.landmark_vertices("anatomical44", s["ids"][:n_A])]
    sdr = _unc.landmark_region_sigma_def(lm_regions, s["sigma_def_mm"][:n_A])
    infl = max(1.0, float(o["gamma"]) ** 2, float(o["chi2_red"]))
    sig = _unc.vertex_sigma_n(covV, normals, list(regions), inflation=infl, sigma_def_region=sdr)
    support = _ledger.vertex_support(kit, o["_ledger"])
    names = sorted(set(str(r) for r in regions))
    rid = np.array([names.index(str(r)) for r in regions], dtype=np.int32)
    return {"sigma_n": np.asarray(sig, float), "support": np.asarray(support, float), "region_ids": rid,
            "region_names": names, "inflation": float(infl)}


# ============================================================================ stage: handoff
def stage_handoff(inputs: dict, config: dict, seed: int) -> dict:
    """KeyStack arrays (DESIGN 4.17): Basis = template, ID_fit = symmetric part S of the fit, Asym =
    S + the antisymmetric part (so Asym is the fitted shape, never symmetrised, D-15), artist = empty
    sculpt layer, muted ``stage_*`` diagnostics, the protect mask, and (``config['cage']``) the
    limit-fitted cage of an all-quad kit (``mesh.subdiv.fit_cage_to_limit``)."""
    s, f, u = inputs["solve"], inputs["fit"], inputs["uncertainty"]
    kit = s["_kit"]
    V = f["vertices"]
    S, Asym = _sym.split_symmetric(V, np.asarray(kit.mirror_map))
    stages = {"A": f["V_A"]}
    if "V_B" in f:
        stages["B"] = f["V_B"]
    if "V_C" in f:
        stages["C"] = f["V_C"]
    if "V_D" in f:
        stages["D"] = f["V_D"]
    poll_cancel()
    ks = _keys.KeyStack.from_fit(np.asarray(kit.vertices, float), S, Asym, stages)
    ks.validate()
    out = {"key_basis": ks.basis.copy(), "key_ID_fit": ks.keys[_keys.ID].data.copy(),
           "key_Asym": ks.keys[_keys.ASYM].data.copy(), "key_artist": ks.keys[_keys.ARTIST].data.copy(),
           "protect_mask": _keys.protect_mask(u["support"]), "key_names": list(ks.keys),
           "stage_keys": sorted(stages)}
    for nme in stages:
        out["key_stage_" + nme] = np.asarray(stages[nme], float)
    if config.get("cage"):
        if not kit.is_quad:
            raise PipelineError("cage_needs_quads", "limit-fitted cage needs an all-quad template")
        out["cage"] = np.asarray(fit_cage_to_limit(V, np.asarray(kit.faces)), float)
    return out


# ============================================================================ stage: texture
_FLAG_OF_CODE = {"Q-PROCESS": "filtered", "Q-RETOUCH": "retouched", "Q-CLIP": "clipped"}


def texture_gate_findings(project: Project, consent: ConsentRecord | None, solve: dict, triage: dict,
                          now: datetime | None = None, limits: Mapping[str, float] | None = None) -> list:
    """Texture gates for the views of ``solve`` (DESIGN 4.18, bl T2, eth F7): :func:`texture.project.texture_gates`
    with the project's rights bases, the solve's inlier landmark reprojection (median <= 1.5 px, max <= 3 px) and
    the per-view exclusion flags from the triage (Q-PROCESS editor / portrait mode, Q-RETOUCH, Q-CLIP; Q-DATES
    clusters).  ``limits`` (``reproj_median_max_px``, ``reproj_max_max_px``) overrides the T2 limits; the run
    config records it (``result.run.config_sha256``) and the result carries it.  Returns plain finding dicts;
    ``view`` indexes ``solve.photo_ids``."""
    lim = dict(limits or {})
    kw = {}
    if "reproj_median_max_px" in lim:
        kw["median_max_px"] = float(lim["reproj_median_max_px"])
    if "reproj_max_max_px" in lim:
        kw["max_max_px"] = float(lim["reproj_max_max_px"])
    pids = list(solve["photo_ids"])
    tri = {r["id"]: r for r in triage["photos"]}
    flags = []
    for pid in pids:
        fl = [_FLAG_OF_CODE[f["code"]] for f in tri[pid]["findings"] if f["code"] in _FLAG_OF_CODE]
        flags.append(fl)
    clusters = None
    for f in triage.get("set_findings", []):
        if f["code"] == "Q-DATES" and f.get("detail"):
            cl = f["detail"]["clusters"]
            clusters = [cl.get(pid) for pid in pids]
    rights = {p.id: p.rights_basis for p in project.photos}
    out = _tp.texture_gates(consent, [rights[pid] for pid in pids], solve.get("reproj_median_px"),
                            solve.get("reproj_max_px"), flags, now=now, date_clusters=clusters, photo_ids=pids,
                            n_views=len(pids), **kw)
    return [_plain(dict(f)) for f in out]


def stage_texture(inputs: dict, config: dict, seed: int) -> dict:
    """Texture projection and blend (DESIGN 4.18), gated: ``inputs['gate']`` are the
    :func:`texture_gate_findings` (consent scope, rights basis, reprojection median/max, excluded views),
    already enforced by :func:`run_pipeline`; a blocking finding here raises :class:`PipelineError`
    (``texture_blocked``) and views flagged ``exclude_texture`` (Q-PROCESS, Q-RETOUCH, Q-CLIP, other date
    cluster) never feed the albedo.  Linear-light albedo per texel with provenance; mirror fill is off (D-27)."""
    root = Path(inputs["_ctx"]["root"])
    s, f = inputs["solve"], inputs["fit"]
    gate = list(inputs.get("gate") or [])
    if _tp.texture_blocked(gate):
        raise PipelineError("texture_blocked", "texture gates block: " +
                            ",".join(sorted({g["code"] for g in gate if g["severity"] == "block"})))
    kit = s["_kit"]
    size = int(config.get("size", _P["texture_size"]))
    V = f["vertices"]
    tris = kit.triangles()
    poll_cancel()
    gb = _tp.uv_gbuffer(kit, size, V=V)
    photos = {p["id"]: p for p in inputs["ingest"]["photos"]}
    excluded = set(_tp.excluded_views(gate))
    colours, weights, used = [], [], []
    for v, pid in enumerate(s["photo_ids"]):
        p = photos[pid]
        if not p["working_copy"]:
            excluded.add(v)
        if v in excluded:                           # keeps the view count aligned with the gates (eth F7)
            colours.append(np.zeros((size, size, 3)))
            weights.append(np.zeros((size, size)))
            continue
        poll_cancel()
        img = load_working_copy(root, p["working_copy"])
        cam = Camera(f=float(s["cam_f"][v]), cx=float(s["cam_K"][v][0, 2]), cy=float(s["cam_K"][v][1, 2]),
                     width=int(s["cam_wh"][v][0]), height=int(s["cam_wh"][v][1]),
                     R=s["cam_R"][v], t=s["cam_t"][v])
        w, uvimg = _tp.view_weights(gb, V, tris, cam, img.shape[:2], sigma_geom_mm=float(_P["texture_sigma_geom_mm"]))
        poll_cancel()
        col = _tp.sample_image(img, uvimg)
        colours.append(col)
        weights.append(np.asarray(w, float))
        used.append(pid)
    if not used:
        raise PipelineError("no_working_copies", "texture needs at least one usable working copy")
    poll_cancel()
    g = _tp.solve_gains(colours, weights, min_views=2)
    poll_cancel()
    res = _blend.build_texture(np.stack(colours), np.stack(weights), _tp.texel_size_mm(gb), gains=g,
                               views=list(s["photo_ids"]), findings=gate, exclude_views=sorted(excluded))
    return {"albedo_linear": np.asarray(res.albedo_linear, float), "confidence": np.asarray(res.confidence, float),
            "photo_ids": used, "size": size, "gains": np.asarray(g, float),
            "provenance": _plain(res.provenance), "mirror_fill": False,
            "excluded": [s["photo_ids"][v] for v in sorted(excluded)], "gate": gate,
            "gate_limits": {k: float(config[k]) for k in ("reproj_median_max_px", "reproj_max_max_px")
                            if k in config}}


# ============================================================================ stage: report
def _licence(inputs: dict) -> dict:
    """result.licence: AND of component ``commercial_ok`` (invariant 5; fail closed on unknown)."""
    comps = [LicenceTag(spdx="CC0-1.0", commercial_ok=True, redistributable=True, source="template kit"),
             LicenceTag(spdx="CC0-1.0", commercial_ok=True, redistributable=True, source="landmark prior")]
    names = ["template", "landmark_prior"]
    seen = set()
    for det in inputs["landmarks"]["detectors"]:
        key = canonical_json(det)
        if key in seen:
            continue
        seen.add(key)
        comps.append(LicenceTag(spdx=str(det.get("licence", "unknown")),
                                commercial_ok=det.get("commercial_ok"), redistributable=None,
                                source=str(det.get("backend", "unknown"))))
        names.append("detector:" + str(det.get("backend", "unknown")))
    return {"commercial_ok": bool(policy.taint(comps)),
            "components": [{"name": n, "spdx": c.spdx, "commercial_ok": c.commercial_ok}
                           for n, c in zip(names, comps)]}


def report_text(result: dict, lines: Sequence[str]) -> str:
    """Plain-text report: banner, tier, scale (mode and +/-%), focal statuses, region claims
    worst-first, flags, count of active unverified defaults (DESIGN 4.13, 5)."""
    head = [lines[0], f"Tier {result['tier']['code']}: {result['tier']['name']}"]
    sc = result["scale"]
    head.append(f"Scale mode: {sc['mode']} ({sc['label']}), +/-{sc['sigma_pct']:.1f} % ({sc['text']})")
    fs = Counter(result["focal_statuses"])
    head.append("Focal length: " + ", ".join(f"{n} of {len(result['focal_statuses'])} photos {k}"
                                              for k, n in sorted(fs.items())))
    head.append(f"Active unverified defaults: {result['unverified_defaults']}")
    reg = sorted(result["regions"], key=lambda r: (_REGION_RANK.get(r["status"], 9),
                                                   -(r["sigma_rep_mm"] if r["sigma_rep_mm"] is not None else 0.0)))
    claims = {r["name"]: r for r in reg}
    body = ["Region claims (worst first):"]
    for r in reg:
        title = r["name"].replace("_", " ").capitalize()
        match = next((ln for ln in lines if ln.lower().startswith(title.lower() + ":")), None)
        body.append("  " + (match if match else f"{title}: {r['status']}"))
    tail = []
    if result["flags"]:
        tail.append("Flags: " + ", ".join(result["flags"]))
    else:
        tail.append("Flags: none")
    if result.get("next_photo"):
        tail.append(result["next_photo"])
    return "\n".join(head + body + tail) + "\n"


def _gather_findings(inputs: dict) -> tuple[dict, list, list]:
    """All QA findings by photo (triage, set-level with a photo, landmark stage, post-solve), the set-level
    findings without a photo, and the excluded views ``[{photo, stage, codes}]`` (DESIGN 4.1)."""
    s, lmo, tri = inputs["solve"], inputs["landmarks"], inputs["triage"]
    per: dict = {}

    def add(pid, f):
        per.setdefault(pid, []).append({"code": f["code"], "severity": f.get("severity", "warn"),
                                        "action": f.get("action", "none")})
    for r in tri["photos"]:
        for f in r["findings"]:
            add(r["id"], f)
    set_level = []
    for f in tri.get("set_findings", []):
        if f.get("photo_id"):
            add(f["photo_id"], f)
        else:
            set_level.append({"code": f["code"], "severity": f["severity"], "action": f["action"],
                              "detail": f.get("detail")})
    for pid, fl in lmo.get("photo_findings", {}).items():
        for f in fl:
            add(pid, f)
    for pid, fl in s.get("post_findings", {}).items():
        for f in fl:
            add(pid, f)
    excluded = []
    for r in tri["photos"]:
        if not r["usable"]:
            excluded.append({"photo": r["id"], "stage": "triage", "codes": sorted(
                {f["code"] for f in r["findings"] if f["action"] == "exclude_geometry"})})
    excluded += [{"photo": x["photo"], "stage": "landmarks", "codes": x["codes"]} for x in lmo.get("excluded", [])]
    for x in s.get("near_excluded", []):
        add(x["photo"], x["findings"][0]) if x["findings"] else None
        excluded.append({"photo": x["photo"], "stage": "solve", "codes": x["codes"]})
    return per, set_level, excluded


def stage_report(inputs: dict, config: dict, seed: int) -> dict:
    """result.json + arrays.npz (DESIGN 3.2 Result) and the plain-text report."""
    s, o, f = inputs["solve"], inputs["observe"], inputs["fit"]
    u, h = inputs["uncertainty"], inputs["handoff"]
    tri_all = {r["id"]: r for r in inputs["triage"]["photos"]}
    P = len(s["photo_ids"])
    vstats = s["view_stats"]
    per_find, set_level, excluded = _gather_findings(inputs)
    cams = []
    for v in range(P):
        st = o["camera_status"][v] if v < len(o["camera_status"]) else {}
        f_px = float(s["cam_f"][v])
        W, H = s["cam_wh"][v]
        z = float(s["cam_z"][v])
        cams.append({
            "photo": s["photo_ids"][v], "K": s["cam_K"][v].tolist(), "R": s["cam_R"][v].tolist(),
            "t": s["cam_t"][v].tolist(), "f_px": f_px,
            "f35": f_px * float(np.hypot(36.0, 24.0)) / float(np.hypot(W, H)), "z": z, "P": 100.0 / z,
            "sigma_logf": _num(vstats[v].get("sigma_logf")), "focal_status": o["focal_statuses"][v],
            "model": s["camera_models"][v]["model"],
            "mirror": s["mirror"][v] if v < len(s["mirror"]) else {}})
    views = []
    for v in range(P):
        vs = vstats[v]
        views.append({"photo": s["photo_ids"][v], "rms_in": _num(s["rmse_px"][v]),
                      "lovo_ratio": _num(o["lovo_ratio"][v]), "nu": _num(vs.get("nu")),
                      "weight_share": _num(vs.get("weight_share")), "rejected_frac": _num(vs.get("rejected_frac")),
                      "findings": list(dict.fromkeys(x["code"] for x in per_find.get(s["photo_ids"][v], []))),
                      "expression_tag": s["tags"][v]})
    arrays = {"X": s["X"], "cov": s["cov"], "cov_shape": s["cov_shape"], "point_sigma_mm": s["point_sigma_mm"],
              "sigma_rep_mm": o["sigma_rep_mm"], "vertices": f["vertices"], "V_A": f["V_A"],
              "sigma_n": u["sigma_n"], "support": u["support"], "region_ids": u["region_ids"],
              "cam_R": s["cam_R"], "cam_t": s["cam_t"], "cam_K": s["cam_K"]}
    for k in ("V_B", "V_C", "V_D"):
        if k in f:
            arrays[k] = f[k]
    for k in h:
        if k.startswith("key_") or k in ("protect_mask", "cage"):
            arrays["handoff_" + k] = h[k]
    if "texture" in inputs and inputs["texture"] is not None:
        arrays["texture_albedo_linear"] = inputs["texture"]["albedo_linear"]
        arrays["texture_confidence"] = inputs["texture"]["confidence"]
    cfg_sha = inputs["_config_sha256"]
    qa_flags = {x["code"] for fl in per_find.values() for x in fl if x["severity"] in ("warn", "block")}
    qa_flags |= {x["code"] for x in set_level if x["severity"] in ("warn", "block")}
    flags = sorted(set(o["flags"]) | qa_flags)
    result = {
        "format": RESULT_FORMAT, "version": RESULT_VERSION, "licence": LICENCE_RESULT,
        "run": {"config_sha256": cfg_sha, "seed": int(seed), "engine_version": ENGINE_VERSION,
                "input_hashes": {"photos": inputs["ingest"]["photos_sha256"],
                                 "template_topology_sha256": inputs["ingest"]["template"]["topology_sha256"]},
                "licence": _licence(inputs)},
        "ids": s["ids"], "cameras": cams, "views": views,
        "scale": o["scale"], "regions": o["regions"], "tier": {"code": o["tier"][0], "name": o["tier"][1]},
        "flags": flags, "focal_statuses": o["focal_statuses"], "gamma": o["gamma"], "chi2_red": o["chi2_red"],
        "unverified_defaults": o["unverified_defaults"], "next_photo": o["next_photo"],
        "mirror_status": s["mirror_status"], "cards": s["mirror_cards"],
        "banner": o["banner"], "stage": f["stage"], "fit_flags": f["flags"],
        "landmark_rms_mm": f["landmark_rms_mm"],
        "triage_findings": {r["id"]: [x["code"] for x in r["findings"]] for r in inputs["triage"]["photos"]},
        "findings": per_find, "set_findings": set_level, "excluded_views": excluded,
        "texture": None if inputs.get("texture") is None else
        {"size": inputs["texture"]["size"], "photos": inputs["texture"]["photo_ids"], "mirror_fill": False,
         "excluded_views": inputs["texture"]["excluded"], "gate_limits": inputs["texture"]["gate_limits"],
         "provenance": inputs["texture"]["provenance"]},
        "per_vertex": {"region_names": u["region_names"], "inflation": u["inflation"]},
    }
    text = report_text(result, o["report_lines"])
    return {"result": _plain(result), "arrays": arrays, "report_text": text}


def result_summary(result: Mapping[str, Any]) -> dict:
    """Compact summary compared by the golden test: tier, scale mode, region statuses, key numbers."""
    return {
        "tier": result["tier"]["code"], "tier_name": result["tier"]["name"],
        "scale_mode": result["scale"]["mode"], "scale_sigma_pct": result["scale"]["sigma_pct"],
        "region_status": {r["name"]: r["status"] for r in result["regions"]},
        "region_sigma_rep_mm": {r["name"]: r["sigma_rep_mm"] for r in result["regions"]},
        "gamma": result["gamma"], "chi2_red": result["chi2_red"],
        "focal_statuses": list(result["focal_statuses"]),
        "rms_in_px": [v["rms_in"] for v in result["views"]],
        "f_px": [c["f_px"] for c in result["cameras"]],
        "flags": list(result["flags"]),       # the unverified-default count depends on which modules the process imported
        "stage": result["stage"], "landmark_rms_mm": result["landmark_rms_mm"],
    }


# ============================================================================ registry
@dataclass(frozen=True)
class Stage:
    """A registered stage: ``fn(inputs, config, seed) -> dict``; ``inputs`` names upstream stages,
    ``project`` the project parts the stage reads, ``data_class`` its persistence class."""

    name: str
    fn: Callable[[dict, dict, int], dict]
    inputs: tuple
    project: tuple
    outputs: tuple
    data_class: DataClass
    #: the stage emits in-memory ``_`` objects that downstream stages read: a cache hit needs them too
    needs_objects: bool = False


STAGES: dict[str, Stage] = {s.name: s for s in [
    Stage("ingest", stage_ingest, (), ("photos", "template"), ("photos", "template", "n_photos"),
          DataClass.PERSONAL_IMAGE),
    Stage("triage", stage_triage, ("ingest",), (), ("photos", "set_findings"), DataClass.PERSONAL_IMAGE),
    Stage("landmarks", stage_landmarks, ("triage",), ("template", "pins", "flip", "landmark_sets"),
          ("ids", "uv", "weights", "expression_tags"), DataClass.BIOMETRIC_GEOMETRY),
    Stage("solve", stage_solve, ("triage", "landmarks"), ("template", "settings", "scale_refs", "iris_obs"),
          ("X", "cov", "cam_R", "cam_t"), DataClass.BIOMETRIC_GEOMETRY, True),
    Stage("observe", stage_observe, ("triage", "landmarks", "solve"), (), ("regions", "tier", "scale"),
          DataClass.BIOMETRIC_GEOMETRY, True),
    Stage("fit", stage_fit, ("solve",), ("contour_obs",), ("vertices", "V_A"), DataClass.BIOMETRIC_GEOMETRY),
    Stage("uncertainty", stage_uncertainty, ("solve", "observe", "fit"), (), ("sigma_n", "support"),
          DataClass.BIOMETRIC_GEOMETRY),
    Stage("handoff", stage_handoff, ("solve", "fit", "uncertainty"), (), ("key_basis", "key_ID_fit"),
          DataClass.BIOMETRIC_GEOMETRY),
    Stage("texture", stage_texture, ("ingest", "solve", "fit"), (), ("albedo_linear",),
          DataClass.LIKENESS_ASSET),
    Stage("report", stage_report, ("ingest", "triage", "landmarks", "solve", "observe", "fit", "uncertainty",
                                   "handoff", "texture"), (), ("result", "arrays", "report_text"),
          DataClass.BIOMETRIC_GEOMETRY),
]}


# ============================================================================ LM cancel hook
@contextmanager
def lm_cancel_hook(check: Callable[[], None] | None):
    """Call ``check()`` before every Jacobian of every LM outer iteration of the bundle solver.

    ``check`` raises (e.g. :class:`Cancelled`) to abort.  Implemented by wrapping the
    ``levenberg_marquardt`` name that :mod:`face3d.solve.bundle` calls, so the solver files stay
    untouched (a pluggable callback in ``solve.lm`` would be the cleaner follow-up).
    """
    if check is None:
        yield
        return
    orig = _bundle.levenberg_marquardt
    prev_poll = _POLL[0]
    _POLL[0] = check

    def wrapped(fun, x0, jac=None, *a, **k):
        if jac is not None:
            def jac2(x):
                check()
                return jac(x)
            return orig(fun, x0, jac2, *a, **k)

        def fun2(x):
            check()
            return fun(x)
        return orig(fun2, x0, jac, *a, **k)

    _bundle.levenberg_marquardt = wrapped
    try:
        yield
    finally:
        _bundle.levenberg_marquardt = orig
        _POLL[0] = prev_poll


# ============================================================================ plain landmark sets
def landmark_set_to_plain(ls: LandmarkSet) -> dict:
    """:class:`LandmarkSet` to plain data (arrays stay arrays) for stage inputs and job files."""
    faces = []
    for f in ls.faces:
        faces.append({"score": float(f.score), "uv": np.asarray(f.uv, float),
                      "visible": None if f.visible is None else np.asarray(f.visible, bool),
                      "cov": None if f.cov is None else np.asarray(f.cov, float),
                      "blendshapes": None if f.blendshapes is None else dict(f.blendshapes)})
    return {"scheme": ls.scheme, "detector": dict(ls.detector), "image": dict(ls.image), "faces": faces}


def engine_defaults_snapshot() -> dict:
    """Badged defaults the pipeline depends on: every registered default except the test bed's
    (``testbed.*``; imported on demand by tools and tests, never by the pipeline), so the config hash
    and the unverified-default count do not depend on what else the process imported."""
    return {k: v for k, v in _config.snapshot().items() if not k.startswith("testbed.")}


def engine_unverified_count() -> int:
    """Active defaults badged brain / arrows / new (H8) among :func:`engine_defaults_snapshot`."""
    snap = engine_defaults_snapshot()
    return _config.unverified_count({k: None for k in snap})


# ============================================================================ run_pipeline
@dataclass
class PipelineRun:
    """Outcome of :func:`run_pipeline`."""

    outputs: dict = field(default_factory=dict)
    executed: list = field(default_factory=list)
    cache_hits: list = field(default_factory=list)
    keys: dict = field(default_factory=dict)
    flips_recorded: list = field(default_factory=list)
    until: str = "report"

    @property
    def result(self) -> dict | None:
        r = self.outputs.get("report")
        return None if r is None else r["result"]

    @property
    def report_text(self) -> str | None:
        r = self.outputs.get("report")
        return None if r is None else r["report_text"]

    @property
    def arrays(self) -> dict | None:
        r = self.outputs.get("report")
        return None if r is None else r["arrays"]


def _config_for(stage: str, overrides: Mapping[str, Any] | None) -> dict:
    return dict((overrides or {}).get(stage, {}))


def run_pipeline(project: Project, until: str = "report", cache: StageCache | None = None,
                 apply_mirror: Sequence[str] = (), *, landmark_sets: Mapping[str, LandmarkSet] | None = None,
                 consent: ConsentRecord | None = None, config: Mapping[str, Any] | None = None,
                 texture: bool = False, extra_inputs: Mapping[str, Any] | None = None,
                 progress: Callable[[str, float, str], None] | None = None,
                 cancel: Callable[[], bool] | None = None, now: datetime | None = None,
                 seed: int | None = None) -> PipelineRun:
    """Run the stages up to ``until`` (one of :data:`ORDER`), cached, gated and cancellable.

    ``cache``: a :class:`StageCache` (default: a memory-only one).  ``apply_mirror``: photo ids whose
    flip the user asked for on the command line: each one without a recorded ``mirror_flip`` decision
    gets one (``by='cli'``, with an audit entry) *before* the landmarks stage; no other path flips a
    photo (D-10).  ``landmark_sets``: ``{photo id: LandmarkSet}`` (session data); missing entries are
    read from ``<project>/landmarks/<id>.json`` (only present when ``landmark_cache.keep``).
    ``consent``: the :class:`ConsentRecord`; ``check('reconstruct')`` runs before ``landmarks``
    (:class:`ConsentError` on denial) and ``check('texture')`` before ``texture``.  ``texture``
    requests the texture stage.  ``extra_inputs``: optional ``iris_obs`` / ``contour_obs`` lists.
    ``progress(stage, frac, msg_key)`` and ``cancel() -> bool`` serve the job protocol; ``cancel``
    is also polled between LM outer iterations (:func:`lm_cancel_hook`) and inside the long non-LM loops of
    the stages (:func:`poll_cancel`).  ``seed`` overrides ``project.seed`` for this run only (the project
    is not changed, so a job or CLI override is never persisted).
    """
    if until not in ORDER:
        raise PipelineError("bad_until", f"until must be one of {ORDER}")
    cache = cache if cache is not None else StageCache()
    root = project.root
    now = now or datetime.now(timezone.utc)
    run = PipelineRun(until=until)
    run_seed = int(project.seed if seed is None else seed)
    stop_at = ORDER.index(until)

    def check_cancel():
        if cancel is not None and cancel():
            raise Cancelled()

    # --- mirror decisions (D-10): only recorded decisions flip a photo
    # the *latest* mirror decision of a photo wins (flip, keep, flip ...): an explicit flag is never a silent
    # no-op after an earlier revert, and a revert is a recorded ``mirror_keep`` decision
    for pid in apply_mirror:
        project.photo(pid)                                    # KeyError for unknown ids
        if project.mirror_state(pid) != "flip":
            project.record_decision("mirror_flip", pid, "cli")
            run.flips_recorded.append(pid)
    if run.flips_recorded and project.path is not None:
        project.save()
    flip = project.flipped_photos()
    # landmark TTL 0 (D-25, eth 2.2): kept sets are used only while landmark_cache.keep is true; after an
    # opt-out they are purged (and logged) rather than silently reused
    if not project.keep_landmarks:
        project.purge_kept_landmarks()

    proj_json = project.to_json()
    photos_json = proj_json["photos"]
    defaults_sha = sha256_bytes(canonical_json(engine_defaults_snapshot()))
    #: reported in result.run.config_sha256 (defaults + every stage config); stage keys use their own part
    cfg_sha = sha256_bytes(canonical_json({"defaults": defaults_sha, "stage_config": config or {}}))
    ctx = {"root": root}
    outs: dict[str, dict] = {}
    ext_sets: dict[str, dict] = {}

    def get_sets() -> dict:
        if ext_sets:
            return ext_sets
        for p in project.photos:
            ls = None if landmark_sets is None else landmark_sets.get(p.id)
            if ls is None and project.keep_landmarks:
                f = root / "landmarks" / f"{p.id}.json"
                if f.is_file():
                    from face3d.io.landmarks import load_landmarks
                    ls = load_landmarks(f)
            if ls is not None:
                ext_sets[p.id] = landmark_set_to_plain(ls)
                if project.keep_landmarks and landmark_sets is not None and landmark_sets.get(p.id) is not None:
                    _keep_landmarks(project, p, landmark_sets[p.id])
        return ext_sets

    for name in ORDER[:stop_at + 1]:
        spec = STAGES[name]
        if name == "texture" and not texture and until != "texture":
            outs["texture"] = None
            continue
        if progress is not None:
            progress(name, ORDER.index(name) / len(ORDER), f"stage.{name}.start")
        check_cancel()
        # consent gates
        if name == "landmarks":
            _gate_reconstruct(project, consent, outs["triage"], now)
        gate_findings = None
        if name == "texture":
            gate_findings = _gate_texture(project, consent, outs["solve"], outs["triage"], now,
                                           _config_for("texture", config))
        inputs: dict[str, Any] = {"_ctx": ctx}
        for up in spec.inputs:
            inputs[up] = outs.get(up)
        extra = dict(extra_inputs or {})
        if name == "ingest":
            inputs["photos"], inputs["template"] = photos_json, proj_json["template"]
            inputs["file_sha256"] = _file_hashes(project)
        elif name == "triage":
            inputs["photos"] = outs["ingest"]["photos"]
        elif name == "landmarks":
            inputs["photos"] = outs["triage"]["photos"]
            inputs["landmark_sets"] = get_sets()
            inputs["pins"] = proj_json["pins"]
            inputs["flip"] = flip
            inputs["template"] = proj_json["template"]
        elif name == "solve":
            inputs["landmarks"], inputs["template"] = outs["landmarks"], proj_json["template"]
            inputs["settings"], inputs["scale_refs"] = proj_json["settings"], proj_json["scale_refs"]
            inputs["iris_obs"] = extra.get("iris_obs")
            inputs.pop("triage", None)
            inputs["triage"] = outs["triage"]
        elif name == "observe":
            inputs["solve"], inputs["triage"], inputs["landmarks"] = outs["solve"], outs["triage"], outs["landmarks"]
        elif name == "fit":
            inputs["solve"] = outs["solve"]
            inputs["contour_obs"] = extra.get("contour_obs")
        elif name == "uncertainty":
            inputs["solve"], inputs["observe"], inputs["fit"] = outs["solve"], outs["observe"], outs["fit"]
        elif name == "handoff":
            inputs["solve"], inputs["fit"], inputs["uncertainty"] = outs["solve"], outs["fit"], outs["uncertainty"]
        elif name == "texture":
            inputs["ingest"], inputs["solve"], inputs["fit"] = outs["ingest"], outs["solve"], outs["fit"]
            inputs["gate"] = gate_findings
        elif name == "report":
            for up in spec.inputs:
                inputs[up] = outs.get(up)
            inputs["ingest"] = dict(outs["ingest"])
            inputs["ingest"]["photos_sha256"] = [p["sha256"] for p in outs["ingest"]["photos"]]
            inputs["_config_sha256"] = cfg_sha
        scfg = _config_for(name, config)
        key_inputs = {k: _hash_value(v) for k, v in inputs.items() if not k.startswith("_ctx")}
        key = StageCache.key(name, key_inputs, {"stage": scfg, "defaults": defaults_sha}, run_seed,
                             ENGINE_VERSION)
        run.keys[name] = key
        hit = cache.get(key)
        if hit is not None and spec.needs_objects:
            objs = _OBJ_LRU.get(key)
            if objs is None:
                hit = None
            else:
                hit = {**hit, **objs}
        if hit is not None:
            run.cache_hits.append(name)
            outs[name] = hit
        else:
            with lm_cancel_hook(None if cancel is None else check_cancel):
                value = spec.fn(inputs, scfg, run_seed)
            plain = {k: v for k, v in value.items() if not k.startswith("_")}
            objs = {k: v for k, v in value.items() if k.startswith("_")}
            _store(cache, key, plain, spec.data_class)
            if objs:
                _OBJ_LRU[key] = objs
                while len(_OBJ_LRU) > _OBJ_MAX:
                    _OBJ_LRU.popitem(last=False)
            run.executed.append(name)
            outs[name] = value
        if progress is not None:
            progress(name, (ORDER.index(name) + 1) / len(ORDER), f"stage.{name}.done")
    run.outputs = outs
    return run


def _store(cache: StageCache, key: str, plain: dict, dc: DataClass) -> None:
    """Persist per the data-class TTL; values that cannot be serialised stay memory-only."""
    try:
        cache.put(key, plain, dc)
    except (TypeError, ValueError):
        cache._remember(key, plain, dc)                       # noqa: SLF001 - memory-only fallback


def _gate_reconstruct(project: Project, consent: ConsentRecord | None, triage: dict, now: datetime) -> None:
    usable = {r["id"] for r in triage["photos"] if r["usable"]}
    shas = [p.sha256 for p in project.photos if p.id in usable]
    g = policy.check("reconstruct", consent, photos_sha256=shas, now=now)
    if not g.allowed:
        raise ConsentError("reconstruct", g)


def _gate_texture(project: Project, consent: ConsentRecord | None, solve: dict, triage: dict,
                  now: datetime, limits: Mapping[str, float] | None = None) -> list:
    """Texture gates before the stage (DESIGN 4.18): consent scope and rights basis (:class:`ConsentError`),
    landmark reprojection median <= 1.5 px / max <= 3 px and the other blocking findings
    (:class:`PipelineError` ``texture_blocked``).  Returns the plain finding dicts (excluded views included)."""
    g = policy.check("texture", consent, rights_basis=[p.rights_basis for p in project.photos], now=now)
    if not g.allowed:
        raise ConsentError("texture", g)
    findings = texture_gate_findings(project, consent, solve, triage, now, limits)
    if _tp.texture_blocked(findings):
        raise PipelineError("texture_blocked", "texture gates block: " + ",".join(
            sorted({f["code"] for f in findings if f["severity"] == "block"})))
    return findings


def _file_hashes(project: Project) -> dict:
    """SHA-256 of each photo's original and working-copy file (None when absent): part of the ingest cache
    key, so a changed file is a miss and the ingest stage re-verifies it (invariant 4)."""
    out = {}
    for p in project.photos:
        d = {}
        for key, rel in (("original", p.path), ("working_copy", p.working_copy)):
            f = project.resolve(rel) if rel else None
            d[key] = sha256_file(f) if f is not None and f.is_file() else None
        out[p.id] = d
    return out


def _keep_landmarks(project: Project, photo: PhotoRecord, ls: LandmarkSet) -> None:
    """Opt-in persistence of a landmark set under the project (``landmark_cache.keep``), logged."""
    from face3d.io.landmarks import save_landmarks
    d = project.root / "landmarks"
    d.mkdir(parents=True, exist_ok=True)
    save_landmarks(ls, d / f"{photo.id}.json")
    project.audit_log().write("landmarks_kept", DataClass.BIOMETRIC_GEOMETRY, photo.sha256,
                              scope="RECONSTRUCT", detail_code="keep_opt_in")


# ============================================================================ output writing
def write_solve(project: Project, run: PipelineRun, out_dir: Path | None = None) -> Path:
    """Write ``solves/NNNN/{result.json, arrays.npz, report.txt}`` (immutable) and set
    ``project.active_solve``.  Arrays first, ``result.json`` last (its presence marks completion);
    each file is written to a temporary name and renamed (``os.replace``)."""
    rep = run.outputs.get("report")
    if rep is None:
        raise PipelineError("no_report", "the report stage did not run")
    if out_dir is None:
        base = project.root / "solves"
        base.mkdir(parents=True, exist_ok=True)
        n = 1 + max([int(p.name) for p in base.iterdir() if p.name.isdigit()] or [0])
        out_dir = base / f"{n:04d}"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=False)
    write_result_files(out_dir, rep)
    try:
        project.active_solve = os.path.relpath(out_dir, project.root)
    except ValueError:
        project.active_solve = str(out_dir)
    if project.path is not None:
        project.save()
    return out_dir


def write_result_files(out_dir: Path, rep: Mapping[str, Any]) -> None:
    """Atomically write ``arrays.npz``, ``report.txt`` and ``result.json`` of a report output."""
    out_dir = Path(out_dir)
    tmp_npz = out_dir / "arrays.npz.tmp"
    manifest = save_arrays(tmp_npz, **rep["arrays"])
    os.replace(tmp_npz, out_dir / "arrays.npz")
    for m in manifest.values():
        m["file"] = "arrays.npz"
    tmp_txt = out_dir / "report.txt.tmp"
    tmp_txt.write_text(rep["report_text"], encoding="utf-8")
    os.replace(tmp_txt, out_dir / "report.txt")
    res = dict(rep["result"])
    res["arrays"] = manifest
    tmp_js = out_dir / "result.json.tmp"
    dump_json(res, tmp_js)
    os.replace(tmp_js, out_dir / "result.json")


__all__ = ["STAGES", "ORDER", "Stage", "run_pipeline", "PipelineRun", "PipelineError", "ConsentError",
           "Cancelled", "write_solve", "write_result_files", "result_summary", "report_text", "load_kit",
           "landmark_set_to_plain", "lm_cancel_hook", "load_working_copy", "ENGINE_VERSION", "PIPELINE"]
