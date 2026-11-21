"""WP-23 release gate: the DESIGN 7.4 fault-injection matrix through ``face3d.pipeline`` (H12).

Harness (shared with ``tests/test_honesty_gates.py``)
------------------------------------------------------
* A *scene* is a WP-11 out-of-prior surface subject of the procedural CC0 head, a rig, and detections
  of the 44 anatomical landmarks from the test-bed detector simulator (DESIGN 7.2).  Everything is
  generated from seeds at test time (provenance ``synthetic``; nothing but aggregate numbers is committed).
* Every scene is run through :func:`face3d.pipeline.stages.run_pipeline` as a project folder with
  LandmarkSets (stages ``ingest .. observe``; surface rows also ``fit``), exactly like a user's project.
  Working copies are seeded noise images of the full frame size (no pixel step is under test here; the
  landmark stage measures Q-SMALL in the working frame, so the frame must have the capture resolution).
* Seed streams: ``SeedSequence(seed).spawn(4)`` = subject, rig, detector, fault.  A faulted scene and
  its clean twin share the first three, so every degradation is paired with the clean run of the
  same seed (WBS WP-23 item 3).
* Base rig (:func:`make_scene`): the studio ring (85 mm, 1.5-3 m, 5 views over +/-90 deg yaw) in a
  1500 x 2000 px frame.  It is the only WP-01 protocol that is *clean* by the engine's own QA thresholds
  (the rear-phone protocol's 0.6-1.5 m draws legitimately raise Q-NEAR below 1 m and Q-SMALL below
  250 px).  Rows that need another camera say so in their runner.

Units: mm (head frame of DESIGN 3.1), pixels with the origin at the top-left corner, OpenCV cameras.

Statistics
----------
Thresholds are the DESIGN 7.4 targets copied by :data:`face3d.testbed.faults.FAULT_MATRIX` (badge new:
uncalibrated).  Every gate carries two verdicts: ``met`` (the point estimate meets the target) and ``ok``
(not rejected at the binomial 95 % bound: a ``>= p0`` gate is rejected when the observed count is below
the 2.5 % quantile of Binomial(n, p0), :func:`binom_lower`; a ``<= p0`` gate when it is above the 97.5 %
quantile, :func:`binom_upper`).  The 5-seed per-push subset is judged on ``ok``: this is the only
relaxation it gets (WBS WP-23 item 3), together with the chi-square half-width on the NEES band.  The
>= 30-seed release run (``-m slow``) is judged on ``met``: point estimates and bands as written
(:func:`failed_gates` with ``strict=True``).  Continuous bounds (ratios, mm) are compared on the median
over seeds without any relaxation.

Design gates that do not meet their target are *not* relaxed: they are listed in
:data:`CALIBRATION_PENDING` with the measured value, asserted against an honest regression floor
(so they cannot get worse silently) and against the honesty conditions that must hold whatever the
detection rate (no false flips, no false 'keep', no silent identity damage), and they are tabulated
in ``docs/RESULTS.md`` (and noted under the DESIGN 7.4 table).  A *honesty* gate can never be
calibration-pending: one that fails is an open release blocker (:data:`OPEN_HONESTY_VIOLATIONS`, H12),
documented as such.  A listed gate that starts to meet its target fails the release run, so that the
lists are cleaned up.

Reported uncertainty: the NEES / coverage numbers are computed from the covariance behind the
``sigma_rep_mm`` the observe stage reports (:func:`honesty_of` asserts the two agree on every run).

FU-03 (closes the WP-23 release blocker): the focal label is earned from the photos
(``exif_crop.focal_label`` passes; :data:`OPEN_HONESTY_VIOLATIONS` is empty), the robust EXIF prior and the
post-BA Q-RETOUCH step are wired and gated for false alarms (``exif_crop.no_false_overrule``,
``beauty_warp.no_false_alarm`` on the pipeline's own findings), C-FOCAL-PRIOR, the hair point drops and
Q-SMALL on the pose-independent face width meet their targets.  :func:`task_exif_near` is a diagnostic
(not a DESIGN 7.4 row) at a range where the photos alone constrain the focal.

FU-04 (image tangents implemented as an opt-in; single-view detectors recalibrated).  The engine can
derive the image tangent of the curve / extremal landmarks from the detected neighbours the scheme names
and declare sigma_n across / sigma_t along it (``pipeline.image_tangents``).  After the FU-04 review the
switch is off by default and **every gate is measured on the WP-01 detector simulator as is** (one random
noise direction per landmark, unrelated to the scheme metadata): scenes whose noise axes were rebuilt from
the scheme's own neighbour pairs (:func:`anatomical_noise_axes`) agree with the engine's assumption by
construction and cannot detect a wrong neighbour choice, so they are diagnostics only
(:data:`FU04_VARIANTS`, with the cost of the opt-in on the gate scenes).  The mirror test uses the declared
predictive noise, a gap threshold from its null (``mirror.flip_alpha``) and a per-view g_min from the power
of its complete decision rule (``mirror.keep_power``); the expression re-tag uses the capped mobile-class
chi^2 and the fitted jaw angle at stated false-alarm rates.  :func:`_fu04_summary` (diagnostics run)
reports the conditions under which the unreachable single-view targets hold, the floor of the identity
gates under a perfect tagger, and the noise-model variants.

Per-push cost: about 105 pipeline runs (21 per seed) plus 15 clean solves for the alarm budget, in a
process pool; :func:`matrix_tasks` with ``fast=True`` leaves out the stages no gate reads (the fit of the
expression rows, the observe stage of the clean rear-phone twin), and the glasses / hair rows stop after
the landmarks stage, where all of their gated actions are decided (the release run solves them too: they
join the Q-RETOUCH false-alarm pool, :func:`_occ_kw`).
"""
from __future__ import annotations

import json
import math
import os
import shutil
import tempfile
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pytest

from face3d.core import policy
from face3d.core.cache import StageCache
from face3d.core.policy import ConsentRecord, Scope
from face3d.core.schema import sha256_file
from face3d.eval import coverage as _cov
from face3d.geometry.camera import focal_35mm_from_px
from face3d.geometry.procrustes import procrustes_rmse, umeyama
from face3d.io.landmarks import Face, LandmarkSet
from face3d.model.procedural_head import build_procedural_head
from face3d.model.registry import ANATOMICAL, load_scheme
from face3d.pipeline import stages as S
from face3d.pipeline.project import Project
from face3d.solve import noise as _noise
from face3d.solve import observability as _ob
from face3d.testbed import detector_sim, faults, rigs
from face3d.testbed.render import face_centre
from face3d.testbed.surface_subjects import out_of_prior_subject

REPO = Path(__file__).resolve().parents[1]
GOLDEN_PROJECT = Path(__file__).parent / "golden" / "pipeline_small" / "project.json"
W, H = 1500, 2000                       # working frame (3:4 portrait, half the WP-01 3000 x 4000 frame)
N_VIEWS = 5
FAST_SEEDS = tuple(range(2300, 2305))   # per-push subset (WBS WP-23: 5 seeds)
SLOW_SEEDS = tuple(range(2300, 2330))   # release run (>= 30 seeds, DESIGN 7.5)
ROWS = {r["name"]: r for r in faults.FAULT_MATRIX}
LOW_NOISE = 0.2                          # detector noise scale of the WP-15 nuisance tests (diagnostic runs)


# ============================================================================ statistics
def _binom_pmf(n: int, p: float) -> np.ndarray:
    """Binomial(n, p) probabilities of 0..n (log-space, exact to rounding for the n used here)."""
    k = np.arange(n + 1)
    if p <= 0.0:
        return (k == 0).astype(float)
    if p >= 1.0:
        return (k == n).astype(float)
    logc = np.array([math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) for i in k])
    return np.exp(logc + k * math.log(p) + (n - k) * math.log1p(-p))


def binom_lower(n: int, p0: float, alpha: float = 0.025) -> int:
    """Smallest count k with P(Binomial(n, p0) <= k) > alpha: observing fewer successes than this
    rejects 'rate >= p0' at the two-sided 95 % level."""
    cdf = np.cumsum(_binom_pmf(n, p0))
    return int(np.argmax(cdf > alpha))


def binom_upper(n: int, p0: float, alpha: float = 0.025) -> int:
    """Largest count k with P(Binomial(n, p0) >= k) > alpha: observing more than this rejects
    'rate <= p0' at the two-sided 95 % level."""
    sf = np.cumsum(_binom_pmf(n, p0)[::-1])[::-1]            # sf[k] = P(X >= k)
    ok = np.flatnonzero(sf > alpha)
    return int(ok.max()) if ok.size else 0


def rate_at_least(k: int, n: int, p0: float) -> bool:
    return n > 0 and k >= binom_lower(n, p0)


def rate_at_most(k: int, n: int, p0: float) -> bool:
    return n > 0 and k <= binom_upper(n, p0)


# ============================================================================ scenes
@dataclass
class Scene:
    """One synthetic capture: subject, cameras, detections and the per-photo metadata of a project."""

    seed: int
    kit: object
    sub: object
    X: np.ndarray                       # (44, 3) true anatomical landmarks, mm
    ids: list
    kinds: list
    rig: object
    uv: list                            # per view (44, 2) px, NaN rows where hidden
    outlier: list                       # per view (44,) bool: detector outliers
    wh: list                            # per view (W, H) of the frame the detections are in
    exif: list                          # per view EXIF summary dict (project.json 'exif')
    tags: list                          # per view project tags
    image_meta: list                    # per view extra LandmarkSet.image fields
    bias_3d: np.ndarray | None = None
    truth: dict = field(default_factory=dict)


_KIT = []


def kit():
    if not _KIT:
        _KIT.append(build_procedural_head())
    return _KIT[0]


def streams(seed: int):
    """(subject, rig, detector, fault) generators of a seed (fresh objects on every call)."""
    return tuple(np.random.default_rng(s) for s in np.random.SeedSequence(int(seed)).spawn(4))


def exif_for(rig, v: int, w: int, h: int) -> dict:
    """EXIF summary whose f35 reproduces the rig's declared focal prior in a ``w x h`` frame."""
    fp = rig.f_prior_px[v]
    front = bool(rig.is_front_camera[v])
    ex = {"digital_zoom": 1.0, "lens_model": "front camera" if front else "back camera", "make": "Apple",
          "model": "iPhone (synthetic)", "orientation": 1, "software": None, "wh": [int(w), int(h)]}
    if fp is not None:
        ex["f35"] = float(focal_35mm_from_px(float(fp), int(w), int(h)))
    return ex


def default_tags() -> dict:
    return {"expression": "auto", "mirrored": "auto", "neutral_reference": False, "occluders": [], "view": "auto"}


_PAIRS = []


def tangent_pairs() -> np.ndarray:
    """(44, 2) neighbour indices of the anatomical44 scheme's ``tangents`` metadata (-1: none)."""
    if not _PAIRS:
        _PAIRS.append(_noise.scheme_tangent_pairs(load_scheme("anatomical44")))
    return _PAIRS[0]


def anatomical_noise_axes(obs, X, rig) -> list:
    """DIAGNOSTIC scenes: the simulator's anisotropic noise re-expressed along the scheme's own neighbour
    chords in each view (FU-04).  Not used by any gate (FU-04 review): the 'true' axes are built from
    exactly the neighbour pairs the engine uses (:func:`tangent_pairs`, the provisional scheme metadata),
    so these scenes are the best case for ``pipeline.image_tangents`` by construction and say nothing
    about whether the metadata is right.  The procedural head has no lid, lip or outline curves from which
    an independent direction could be taken.

    ``detector_sim.simulate`` draws the (tangent, normal) noise components of a landmark along a *random*
    image direction that is the same in every view (WP-01).  For every landmark with scheme neighbours the
    same two noise components (common random numbers: the draws are not changed) are re-applied along /
    across the chord between the true projections of its neighbours in that view (with the shared
    definition bias).  The engine only ever sees ``uv`` and derives its tangents from the detected
    neighbours.
    Landmarks without scheme neighbours, and views in which a neighbour's projection coincides, keep the
    random direction.  Gross-outlier displacements (isotropic in direction) are rotated with the noise.
    Returns the per-view true unit tangents ((N, 2), NaN where the random direction was kept) and edits
    ``obs.uv`` / ``obs.visible`` in place (a point moved outside the frame becomes hidden)."""
    pairs = tangent_pairs()
    has = (pairs >= 0).all(axis=1)
    Xo = np.asarray(X, float) + np.asarray(obs.bias_3d, float)
    t0 = np.asarray(obs.tangent_dirs, float)
    n0 = np.column_stack([-t0[:, 1], t0[:, 0]])
    out = []
    for v, cam in enumerate(rig.cameras):
        clean = cam.project(Xo)
        d = clean[pairs[:, 1]] - clean[pairs[:, 0]]
        L = np.linalg.norm(d, axis=1)
        ok = has & np.isfinite(L) & (L > 1e-6)
        t1 = np.full((len(Xo), 2), np.nan)
        t1[ok] = d[ok] / L[ok][:, None]
        uv = np.asarray(obs.uv[v], float)
        m = ok & np.isfinite(uv).all(axis=1)
        e = uv[m] - clean[m]
        a, b = np.sum(e * t0[m], axis=1), np.sum(e * n0[m], axis=1)
        n1 = np.column_stack([-t1[m, 1], t1[m, 0]])
        uv[m] = clean[m] + t1[m] * a[:, None] + n1 * b[:, None]
        gone = np.isfinite(uv[:, 0]) & ~rigs.in_image_mask(cam, uv)
        uv[gone] = np.nan
        obs.uv[v] = uv
        if obs.visible:
            obs.visible[v] = np.isfinite(uv[:, 0])
        obs.sigma_px_true[v][gone] = np.nan
        obs.outlier_mask[v] = obs.outlier_mask[v] & ~gone
        out.append(t1)
    return out


def detect(X, kinds, rig, seed: int, noise_axes: str = "random", **detector):
    """Detections with the seed's detector stream (identical normal draws for a clean / faulted pair).

    ``noise_axes``: 'random' (default; every gate: the WP-01 simulator as is, one random direction per
    landmark, unrelated to the anatomy and to the scheme's tangent metadata) or 'anatomical' (diagnostic
    only: the anisotropic noise of a landmark with scheme neighbours lies along / across the chord of the
    true projections of *the very neighbours the engine uses*, :func:`anatomical_noise_axes`; the best
    case for ``pipeline.image_tangents`` by construction, so nothing is gated on it except 'the opt-in
    is not over-confident')."""
    obs = detector_sim.simulate(X, kinds, rig, streams(seed)[2], **detector)
    if noise_axes == "anatomical":
        anatomical_noise_axes(obs, X, rig)
    elif noise_axes != "random":
        raise ValueError(f"unknown noise_axes {noise_axes!r}")
    return obs


def make_scene(seed: int, *, rig: str = "studio_ring", n_views: int = N_VIEWS, asym_mm: float | None = None,
               detector: dict | None = None, wh=(W, H), rig_obj=None, X_views=None) -> Scene:
    """The clean scene of a seed.  ``rig``: a ``testbed.rigs`` protocol name; ``rig_obj`` replaces it;
    ``X_views``: per-view landmark arrays (expression rows) used instead of the neutral landmarks."""
    k = kit()
    ids = k.landmark_names("anatomical44")
    kinds = [ANATOMICAL[i].kind for i in ids]
    r_subj, r_rig, _, _ = streams(seed)
    sub = out_of_prior_subject(k, r_subj, **({} if asym_mm is None else {"asym_mm": asym_mm}))
    X = sub.landmarks("anatomical44")
    w, h = wh
    if rig_obj is None:
        rig_obj = rigs.PROTOCOLS[rig](r_rig, n_views, X=X, target=face_centre(k), width=w, height=h)
    obs = detect(X, kinds, rig_obj, seed, **(detector or {}))
    uv = [u.copy() for u in obs.uv]
    if X_views is not None:
        # per-view geometry: re-simulate each view on its own landmark set with the same streams
        for v in range(rig_obj.n_views):
            uv[v] = detect(X_views[v], kinds, rig_obj, seed, **(detector or {})).uv[v].copy()
    n = rig_obj.n_views
    return Scene(seed=int(seed), kit=k, sub=sub, X=X, ids=list(ids), kinds=kinds, rig=rig_obj, uv=uv,
                 outlier=[m.copy() for m in obs.outlier_mask], wh=[(w, h)] * n,
                 exif=[exif_for(rig_obj, v, w, h) for v in range(n)], tags=[default_tags() for _ in range(n)],
                 image_meta=[{} for _ in range(n)], bias_3d=obs.bias_3d)


def focal_group(ex: dict) -> str:
    return "|".join(str(ex.get(k)) for k in ("make", "model", "lens_model", "f35")) + "|still"


def run_scene(scene: Scene, until: str = "observe", *, apply_mirror=(), config=None, extra_inputs=None):
    """Write the scene as a project folder (temporary, removed afterwards) and run the pipeline.

    Returns the :class:`face3d.pipeline.stages.PipelineRun`.  Photos are ``p01..``; the working copy of
    each is a seeded uint8 noise image of the frame size (orientation baked)."""
    tmp = Path(tempfile.mkdtemp(prefix="f3d_fm_"))
    try:
        root = tmp / "proj"
        (root / "photos").mkdir(parents=True)
        doc = json.loads(GOLDEN_PROJECT.read_text())
        tpl = doc["photos"][0]
        doc["photos"], sets = [], {}
        doc["seed"] = int(scene.seed)
        img_rng = np.random.default_rng([int(scene.seed), 77])
        for v in range(scene.rig.n_views):
            pid = "p%02d" % (v + 1)
            w, h = scene.wh[v]
            rec = json.loads(json.dumps(tpl))
            rec.update(id=pid, path=f"photos/{pid}.npy", working_copy=f"photos/{pid}.npy",
                       exif=dict(scene.exif[v]), tags=dict(scene.tags[v]))
            rec["focal_group"] = focal_group(rec["exif"])
            np.save(root / rec["path"], img_rng.integers(96, 160, size=(int(h), int(w)), dtype=np.uint8))
            rec["sha256"] = sha256_file(root / rec["path"])
            doc["photos"].append(rec)
            uv = np.asarray(scene.uv[v], float)
            image = {"sha256": rec["sha256"], "wh": [int(w), int(h)], "orientation_applied": True,
                     "input_flipped": False, "coords": "px_corner"}
            image.update(scene.image_meta[v])
            sets[pid] = LandmarkSet("anatomical44", {"backend": "synthetic", "version": "1", "licence": "CC0-1.0",
                                                     "commercial_ok": True, "is_ml": False},
                                    image, [Face(1.0, uv, np.isfinite(uv[:, 0]))])
        (root / "project.json").write_text(json.dumps(doc))
        prj = Project.load(root / "project.json")
        consent = ConsentRecord(doc["consent_id"], "subject-001", "self", "v1", "test", "2026-01-01T00:00:00+00:00",
                                None, [], [p.sha256 for p in prj.photos], 30, "owner",
                                Scope.RECONSTRUCT | Scope.TEXTURE, attested_age=30)
        with policy.network_guard():
            return S.run_pipeline(prj, until, cache=StageCache(max_items=16), apply_mirror=tuple(apply_mirror),
                                  landmark_sets=sets, consent=consent, config=config, extra_inputs=extra_inputs)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================================ per-run records
def _pid_view(pid: str) -> int:
    return int(pid[1:]) - 1


def _findings(o: dict) -> list:
    """Every QA finding of a run as ``[photo id | None, code, severity]`` (triage, set-level, landmark
    stage, post-solve, observe: C-FOCAL-PRIOR), de-duplicated per photo and code."""
    out = []
    for r in o["triage"]["photos"]:
        out += [[r["id"], f["code"], f.get("severity", "warn")] for f in r["findings"]]
    out += [[f.get("photo_id"), f["code"], f.get("severity", "warn")] for f in o["triage"].get("set_findings", [])]
    if "landmarks" in o:
        for pid, fl in o["landmarks"].get("photo_findings", {}).items():
            out += [[pid, f["code"], f.get("severity", "warn")] for f in fl]
    if "solve" in o:
        for pid, fl in o["solve"].get("post_findings", {}).items():
            out += [[pid, f["code"], f.get("severity", "warn")] for f in fl]
    if "observe" in o:
        out += [[f.get("photo_id"), f["code"], f.get("severity", "warn")] for f in o["observe"].get("findings", [])]
    seen, uniq = set(), []
    for f in out:
        if (f[0], f[1]) not in seen:
            seen.add((f[0], f[1]))
            uniq.append(f)
    return uniq


def aligned_error(X: np.ndarray, X_true: np.ndarray):
    """Similarity alignment of the estimate onto the truth: ``(err (N, 3), s, R)``."""
    s, R, t = umeyama(X, X_true, with_scale=True)
    return s * X @ R.T + t - X_true, float(s), R


def reported_cov_of(res, ob: dict, deflate: bool | None = None) -> np.ndarray:
    """The full reported covariance behind the observe stage's ``sigma_rep_mm``, rebuilt from exactly what
    the stage used: its gauge-projected prior-weight-1 posterior ``Sigma1``, its bias form, its calibration
    chi2_red and gamma (against the noise before the QA sigma multipliers) and its factor setting.
    ``deflate`` None: the pipeline's own setting (``observe['deflate']``); True / False: the same
    covariance under the other factor (evidence columns of docs/RESULTS.md, never gated as 'the pipeline')."""
    import dataclasses
    A = ob["_assess"]
    res_cal = dataclasses.replace(res, chi2_red=float(ob["chi2_red"]))
    d = bool(ob["deflate"]) if deflate is None else bool(deflate)
    return np.asarray(_ob.reported_covariance(res_cal, gamma=float(ob["gamma"]), cov=A["Sigma1"], bias=A["bias"],
                                              deflate=d), float)


def honesty_of(res, ob: dict, X_true: np.ndarray, n: int, deflate: bool | None = None) -> dict:
    """Gauge-projected NEES/dof and aligned 1-sigma coverage (DESIGN 7.3) of the first ``n`` points with the
    covariance the pipeline reports (:func:`reported_cov_of`).  For the pipeline's own setting
    (``deflate`` None) the diagonal is asserted equal to ``observe['sigma_rep_mm']`` squared, so the gate
    measures the reported numbers themselves and a change of the observe stage cannot move them away from
    what is tested here."""
    C = reported_cov_of(res, ob, deflate)
    if deflate is None:
        rep = np.asarray(ob["sigma_rep_mm"], float).reshape(-1)
        if not np.allclose(np.sqrt(np.maximum(np.diag(C), 0.0)), rep, rtol=1e-9, atol=1e-12):
            raise AssertionError("the gate covariance is not the sigma_rep_mm the observe stage reports")
    C = C[:3 * n, :3 * n]
    X = np.asarray(res.X, float)[:n]
    err, s, R = aligned_error(X, X_true)
    B = np.kron(np.eye(n), R)
    C = (s * s) * (B @ C @ B.T)
    val, dof = _cov.nees(err, C, X_true, project=True)
    z = _cov.projected_z(err, C, X_true, project=True)
    z = np.abs(z[np.isfinite(z)])
    return {"nees": float(val), "dof": int(dof), "n_in_1s": int(np.sum(z < 1.0)), "n_z": int(z.size)}


def record(run, scene: Scene) -> dict:
    """Plain (picklable, JSON-able) summary of a pipeline run against the scene's truth."""
    o = run.outputs
    rec: dict = {"seed": scene.seed, "findings": _findings(o), "n_photos": scene.rig.n_views,
                 "truth": scene.truth}
    if "landmarks" in o:
        rec["lm_findings"] = [[f.get("photo"), f["code"]] for f in o["landmarks"].get("findings", [])]
        rec["lm_excluded"] = [x["photo"] for x in o["landmarks"].get("excluded", [])]
        used = {r["id"]: r for r in o["triage"]["photos"]}
        rows = [used[pid] for pid in o["landmarks"]["photo_ids"]]
        rec.update(weights=np.asarray(o["landmarks"]["weights"], float)[:, :len(scene.X)].tolist(),
                   uv_used=np.isfinite(np.asarray(o["landmarks"]["uv"], float)[:, :len(scene.X), 0]).tolist(),
                   lm_qa_sigma_mult=[float(x) for x in o["landmarks"]["qa_sigma_mult"]],
                   occluder_flags=[r["occluder"]["flags"] for r in rows],
                   drop_classes=[r["occluder"]["drop_classes"] for r in rows])
    if "solve" not in o:
        return rec
    s = o["solve"]
    views = [_pid_view(p) for p in s["photo_ids"]]
    n = len(scene.X)
    X = np.asarray(s["X"], float)[:n]
    cams = [scene.rig.cameras[v] for v in views]
    rec.update(
        views=views, X=X.tolist(), config_rms_mm=float(procrustes_rmse(X, scene.X, with_scale=True)),
        tags=list(s["tags"]), mirror=[m["decision"] for m in s["mirror"]],
        mirror_g=[m["g"] for m in s["mirror"]], mirror_gap=[m.get("gap") for m in s["mirror"]],
        # per-view g_min of the complete rule (None: not reachable / no test): g >= g_min <=> 'detectable'
        mirror_det=[m.get("g") is not None and m.get("g_min") is not None and m["g"] >= m["g_min"]
                    for m in s["mirror"]],
        # FU-04: the re-tag evidence of the last round per view (statistics that crossed a threshold)
        retag_by=[(r[-1]["by"] if r else []) for r in s.get("retag", [])],
        retag_first=[([r[0]["mobile_chi2"], r[0]["mobile_dof"], r[0]["jaw_z"]] if r else None)
                     for r in s.get("retag", [])],
        models=[m["model"] for m in s["camera_models"]],
        model_ambiguous=[bool(m["ambiguous"]) for m in s["camera_models"]], solve_flags=list(s["flags"]),
        focal_rel_err=[abs(float(f) / c.f - 1.0) for f, c in zip(s["cam_f"], cams)],
        z_rel_err=[abs(float(z) / float(c.depth(np.zeros((1, 3)))[0]) - 1.0) for z, c in zip(s["cam_z"], cams)],
        inlier=np.asarray(s["inlier_mask"], bool)[:, :n].tolist(), scale_mode=s["scale_mode"],
        chi2_red_solve=float(s["chi2_red"]), qa_sigma_mult=[float(x) for x in s["qa_sigma_mult"]],
        # FU-03: the robust EXIF check per used view (None: not tested) and the post-BA retouch test
        focal_test=[fp["test"] for fp in s["focal_priors"]], focal_source=[fp["f_source"] for fp in s["focal_priors"]],
        retouch_pipeline=[bool(r and r["flagged"]) for r in s["retouch"]])
    if "observe" in o:
        ob = o["observe"]
        ref = np.asarray(S.FactorPrior.from_package().mean(), float)
        rec.update(
            tier=ob["tier"][0], flags=sorted(set(ob["flags"])), gamma=float(ob["gamma"]),
            chi2_red=float(ob["chi2_red"]), focal_statuses=list(ob["focal_statuses"]),
            regions={r["name"]: [r["status"], r["sigma_rep_mm"], r["k"]] for r in ob["regions"]},
            honesty=honesty_of(s["_result"], ob, scene.X, n),
            honesty_design=honesty_of(s["_result"], ob, scene.X, n, deflate=False),
            inflation=float(ob["inflation"]), deflate=bool(ob["deflate"]),
            scale_z=float(_cov.scale_z(ob["scale"]["zeta"], S._scale.log_size(scene.X, ref),
                                       ob["scale"]["sigma_zeta"])),
            scale_sigma=float(ob["scale"]["sigma_zeta"]))
    return rec


def fit_of(run, seed: int) -> dict:
    """The ``fit`` stage on a run's solve output (stage function called directly: the surface rows need
    the warp, not the stages between)."""
    return S.stage_fit({"solve": run.outputs["solve"]}, {}, int(seed))


_FACE = []


def face_vertices() -> np.ndarray:
    """Vertex mask of the facial surface (kit regions eyes, nose, lips, cheeks, forehead, chin, jaw)."""
    if not _FACE:
        reg = kit().vertex_regions()
        _FACE.append(np.isin(reg, ("eyes", "nose", "lips", "cheeks", "forehead", "chin", "jaw")))
    return _FACE[0]


def shape_shift(Xa, Xb) -> dict:
    """RMS and max point displacement (mm) between two solutions after similarity alignment a -> b."""
    Xa, Xb = np.asarray(Xa, float), np.asarray(Xb, float)
    err, _, _ = aligned_error(Xa, Xb)
    d = np.linalg.norm(err, axis=1)
    return {"rms": float(np.sqrt(np.mean(d ** 2))), "max": float(d.max())}


# ============================================================================ row runners
BASE_DETECTOR = {"outlier_frac": 0.0}    # the clean twin has no gross outliers: '5 % gross outliers' is a row
RECAL_SCALES = (1.0, 0.5, 0.35, 0.25, 0.15, 0.0)     # sigma_res multipliers of the docs/RESULTS.md 4.2 curve
RECAL_SCALES_FULL = (1.0, 0.25, 0.0)


def _fault_rng(seed: int):
    return streams(seed)[3]


def surface_honesty(run, scene: Scene, seed: int) -> dict:
    """Fit + per-vertex uncertainty on a run that reached ``observe`` and the honesty counts of DESIGN 7.5.

    Vertices: the fitted surface is similarity-aligned on the 44 landmarks (their positions on the fitted
    and on the true surface) and the signed point-to-surface distance to the true mesh is compared with
    the reported normal sigma ``sigma_n`` (stage ``uncertainty``).  A vertex is in a *measured* region
    when every ledger region its kit region maps to (``fit.ledger.KIT_REGION_MAP``) is labelled
    'measured'.  Landmark regions (false confidence): for every ledger region labelled 'measured', the
    RMS aligned error of its landmarks against 2 x the region target (DESIGN 4.12)."""
    from face3d.fit.ledger import KIT_REGION_MAP
    from face3d.mesh.distance import point_to_mesh
    o = run.outputs
    s, ob = o["solve"], o["observe"]
    k = scene.kit
    f = fit_of(run, seed)
    u = S.stage_uncertainty({"solve": s, "observe": ob, "fit": f}, {}, int(seed))
    V = np.asarray(f["vertices"], float)
    sc_, R, t = umeyama(k.landmark_positions("anatomical44", V), scene.X, with_scale=True)
    Va = sc_ * V @ R.T + t
    status = {r["name"]: r["status"] for r in ob["regions"]}
    kreg = k.vertex_regions()
    measured_kit = [kr for kr, led in KIT_REGION_MAP.items()
                    if led and all(status.get(x) == "measured" for x in led if x in status)
                    and any(x in status for x in led)]
    mask = np.isin(kreg, measured_kit)
    out = {"fit_stage": f["stage"], "V_face": V[face_vertices()].tolist(), "measured_kit_regions": measured_kit,
           "n_vert": int(mask.sum()), "n_vert_in": 0, "sum_z2": 0.0, "sigma_n_median": None, "abs_err_median": None}
    if mask.any():
        d = point_to_mesh(Va[mask], scene.sub.V_true, k.triangles(), signed=True)[0]
        sn = np.asarray(u["sigma_n"], float)[mask]
        out.update(n_vert_in=int(np.sum(np.abs(d) <= 1.96 * sn)), sum_z2=float(np.sum((d / sn) ** 2)),
                   sigma_n_median=float(np.median(sn)), abs_err_median=float(np.median(np.abs(d))))
        # the calibration curve of docs/RESULTS.md 4.2 (evidence; the shipped setting is one of its points):
        # sigma_res scaled by c, with the shipped shape covariance x the sigma_rep factor ('shape'), and with
        # the pre-WP-23 full covariance ``cov`` x the DESIGN factor max(1, gamma^2, chi2_red) ('full')
        from face3d.fit import uncertainty as U
        from face3d.model.template_kit import area_weighted_normals
        n_A = s["n_A"]
        nrm = area_weighted_normals(V, k.faces)
        nrm = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
        lm_regions = [str(kreg[v]) for v in k.landmark_vertices("anatomical44", s["ids"][:n_A])]
        sdr = U.landmark_region_sigma_def(lm_regions, s["sigma_def_mm"][:n_A])
        design = max(1.0, float(ob["gamma"]) ** 2, float(ob["chi2_red"]))
        cand = {}
        for label, cov, infl, scales in (("shape", s["cov_shape"], float(u["inflation"]), RECAL_SCALES),
                                         ("full", s["cov"], design, RECAL_SCALES_FULL)):
            covV = U.vertex_cov_stage_b(f["A_rows"], np.asarray(cov, float)[:3 * n_A, :3 * n_A]) * infl
            for c in scales:
                sr = {r: c * v for r, v in U.SIGMA_RES_MM.items()}
                sn_c = U.vertex_sigma_n(covV, nrm, list(kreg), inflation=1.0, sigma_def_region=sdr,
                                        sigma_res=sr)[mask]
                cand["%s:%g" % (label, c)] = [int(np.sum(np.abs(d) <= 1.96 * sn_c)), float(np.sum((d / sn_c) ** 2)),
                                              float(np.median(sn_c))]
        out["recal"] = cand
        out["sigma_res_scale"] = float(u["sigma_res_scale"])
    A = ob["_assess"]
    err, _, _ = aligned_error(np.asarray(s["X"], float)[:len(scene.X)], scene.X)
    e = err.reshape(-1)
    reg = []
    for name, idx in A["region_index"].items():
        # region error = RMS of the aligned error over the region's coordinates (3 i + a; the projection
        # regions use z only), the same reduction as observability.region_sigma_rep
        c = np.asarray(idx, np.int64).reshape(-1)
        c = c[c < e.size]
        if A["region_status"].get(name) != "measured" or c.size == 0:
            continue
        reg.append([name, float(np.sqrt(np.mean(e[c] ** 2))), float(A["targets"][name]),
                    float(A["region_sigma_rep_mm"][name])])
    out["measured_regions"] = reg
    return out


def _tangent_cfg(tangents: bool | None):
    """Pipeline config of the FU-04 diagnostics: ``tangents`` None is the pipeline as shipped
    (``pipeline.image_tangents`` False since the FU-04 review: isotropic FU-01 noise); True / False set the
    detection-derived image tangents explicitly."""
    return None if tangents is None else {"landmarks": {"image_tangents": bool(tangents)}}


def task_clean(seed: int, until: str = "observe", rig: str = "studio_ring", surface: bool = False,
               noise_scale: float = 1.0, likeness: bool = False, noise_axes: str = "random",
               tangents: bool | None = None, **kw) -> dict:
    """The clean scene (no fault; nominal detector noise and definition bias, no gross outliers).
    ``surface``: also fit + uncertainty and the honesty counts of :func:`surface_honesty`; ``likeness``:
    also the likeness-mode check of :func:`likeness_of` on the same run.  FU-04 diagnostics:
    ``noise_axes`` (:func:`detect`) and ``tangents`` (:func:`_tangent_cfg`)."""
    sc = make_scene(seed, rig=rig, detector=dict(BASE_DETECTOR, noise_scale=noise_scale, noise_axes=noise_axes),
                    **kw)
    run = run_scene(sc, until, config=_tangent_cfg(tangents))
    rec = record(run, sc)
    if surface:
        rec.update(surface_honesty(run, sc, seed))
    if likeness:
        rec["likeness"] = likeness_of(run)
    return rec


def likeness_of(run) -> dict:
    """Likeness mode (DESIGN 4.6: the prior widened where the photos see) on a pipeline run that reached
    ``observe``: every label, k, sigma_rep, coverage, focal status and the tier reported for the widened
    solve must equal those the pipeline reported for the standard solve (H2).  The pipeline does not expose
    likeness mode; this drives the observability API with the pipeline's own solve objects and the
    arguments of its observe stage.

    The comparison is against the pipeline's own assessment (``observe['_assess']``), and it is not
    vacuous: ``own_differs`` records that assessing the widened solve *on its own* (flag removed, i.e.
    what a caller would get without the H2 routing) changes sigma_rep or k, and ``refused_without_standard``
    that the flagged result is refused without the standard solve."""
    import dataclasses
    from face3d.solve.bundle import bundle_adjust
    o = run.outputs
    s, ob = o["solve"], o["observe"]
    res, A = s["_result"], ob["_assess"]
    tri_all = {r["id"]: r for r in o["triage"]["photos"]}
    tri = [tri_all[pid] for pid in s["photo_ids"]]

    def resolve(prior):
        return bundle_adjust(s["_views"], res.X.copy(), None, max_iter=100, terms=s["_terms"],
                             jaw_weights=s["_jaw_w"], **{**s["_bkw"], "prior": prior})
    seen = np.asarray(res.inlier_mask).sum(axis=0)
    wide, res_w = _ob.likeness_mode_prior(s["_prior"], res, seen, resolve=resolve, max_iter=2, return_result=True)
    fpri = S.focal_priors_of(s, tri)          # the priors the solve used (after the robust EXIF check)
    exif_sig = S.exif_log_sigmas(fpri)
    kw = dict(region_index=_ob.default_region_index(s["ids"]), gamma=ob["gamma"], views=s["_views"],
              prior_log_sigma=[r["f_log_sigma"] for r in fpri], exif_log_sigma=exif_sig,
              scale_mode=s["scale_mode"], all_selfie=all(r["front_camera"] for r in tri),
              deflate=bool(ob["deflate"]), focal_conflict=S.focal_conflicts(fpri))
    std = res if float(ob["chi2_red"]) == float(res.chi2_red) else dataclasses.replace(
        res, chi2_red=float(ob["chi2_red"]))
    Aw = _ob.assess(res_w, standard_result=std, **kw)
    keys = ("region_status", "region_k", "region_sigma_rep_mm", "coverage", "tier", "focal_statuses")
    same = {k: bool(Aw[k] == A[k]) for k in keys}
    same["sigma_rep_mm"] = bool(np.array_equal(Aw["sigma_rep_mm"], A["sigma_rep_mm"]))
    refused = False
    try:
        _ob.assess(res_w, **kw)
    except ValueError:
        refused = True
    # the widened solve assessed on its own (no H2 routing): the numbers a wrong caller would report
    bare = dataclasses.replace(res_w, flags=[f for f in res_w.flags if f != _ob.FLAG_LIKENESS])
    Ao = _ob.assess(bare, **kw)
    d_sig = float(np.max(np.abs(np.asarray(Ao["sigma_rep_mm"]) / np.asarray(A["sigma_rep_mm"]) - 1.0)))
    own_differs = bool(d_sig > 1e-6 or Ao["region_k"] != A["region_k"])
    return {"rounds": int(wide.meta["likeness"]["rounds"]) if "likeness" in wide.meta else 0,
            "flagged": bool(_ob.FLAG_LIKENESS in res_w.flags), "same": same, "refused_without_standard": refused,
            "own_differs": own_differs, "own_sigma_rep_rel_change_max": d_sig,
            "own_labels_differ": bool(Ao["region_status"] != A["region_status"]),
            "max_move_mm": float(np.abs(np.asarray(res_w.X) - np.asarray(res.X)).max()),
            "label_source": Aw["label_source"]}


def task_mirror(seed: int, asym_mm: float | None = None, noise_scale: float = 1.0, confirm: bool = False,
                rig: str = "studio_ring") -> dict:
    """One mirrored view among 5 (DESIGN 7.4 row 1).  ``asym_mm`` None: the WP-11 default 0.8 mm RMS
    antisymmetric part (the row's 'at >= 0.8 mm asymmetry'); 0: the symmetric subject.  ``confirm``: the
    user confirms the flip of the mirrored photo (``apply_mirror``)."""
    det = dict(BASE_DETECTOR, noise_scale=noise_scale)
    sc = make_scene(seed, asym_mm=asym_mm, detector=det, rig=rig)
    v = int(_fault_rng(seed).integers(0, sc.rig.n_views))
    perm = load_scheme("anatomical44").mirror_permutation()
    sc.uv[v], truth = faults.mirror_view(sc.uv[v], sc.wh[v][0], perm)
    sc.truth = {"view": v, "asym_rms_mm": float(sc.sub.asym_rms_mm)}
    run = run_scene(sc, "solve", apply_mirror=["p%02d" % (v + 1)] if confirm else ())
    return record(run, sc)


def task_orientation(seed: int) -> dict:
    """Detections made on the stored (not displayed) image of one photo, EXIF orientation 6."""
    sc = make_scene(seed, detector=dict(BASE_DETECTOR))
    v = int(_fault_rng(seed).integers(0, sc.rig.n_views))
    w, h = sc.wh[v]
    uv, (ws, hs), truth = faults.unbaked_orientation(sc.uv[v], w, h, **ROWS["orientation_unbaked"]["kwargs"])
    sc.uv[v] = uv
    sc.image_meta[v] = {"wh": [ws, hs], "orientation_applied": False}
    sc.truth = {"view": v}
    return record(run_scene(sc, "landmarks"), sc)


def task_exif(seed: int, kind: str = "exif_crop", frontal: bool = False) -> dict:
    """EXIF focal wrong by an undetected +/-30 % crop, or missing, on every photo of a rear-phone set
    (yaws -60..60 deg: 'views span >= 60 deg').  ``frontal``: the 3 views at -30, 0, 30 deg are replaced by
    a narrow set (see :func:`_frontal_rig`) where the focal is not observable ('C-FOCAL-PRIOR when
    unobservable': the H5 label must read 'from prior')."""
    rig_obj = _frontal_rig(seed) if frontal else None
    sc = make_scene(seed, rig="rear_phone", detector=dict(BASE_DETECTOR), rig_obj=rig_obj)
    rng = _fault_rng(seed)
    factor = None
    if kind == "exif_crop":
        factor = float(rng.choice(ROWS["exif_crop"]["sampling"]["factor"]["choice"]))
    for v in range(sc.rig.n_views):
        w, h = sc.wh[v]
        if kind == "exif_crop":
            prior, truth = faults.exif_crop(sc.rig.f_prior_px[v], factor)
            sc.exif[v]["f35"] = float(focal_35mm_from_px(prior["f_prior_px"], w, h))
        elif kind == "exif_missing":
            prior, truth = faults.exif_missing()
            sc.exif[v] = {"orientation": 1, "wh": [int(w), int(h)]}
    sc.truth = {"factor": factor, "yaw_span_deg": float(max(sc.rig.view_yaw_deg) - min(sc.rig.view_yaw_deg))}
    return record(run_scene(sc, "observe"), sc)


def _frontal_rig(seed: int):
    """Three rear-phone views within +/-8 deg of yaw at 1.2-1.5 m (26 mm-equivalent): no parallax to
    separate focal length from distance."""
    from face3d.synthetic import orbit_camera
    rng = streams(seed)[1]
    tgt = tuple(float(x) for x in face_centre(kit()))
    cams, yaws, pitches, dists = [], [], [], []
    for yaw in (-8.0, 0.0, 8.0):
        d, pitch = float(rng.uniform(1200.0, 1500.0)), float(rng.uniform(*rigs.PITCH_RANGE_DEG))
        cams.append(orbit_camera(d, yaw, pitch, 26.0, width=W, height=H, target=tgt))
        yaws.append(yaw), pitches.append(pitch), dists.append(d)
    return rigs.Rig(name="frontal_narrow", cameras=cams, f_prior_px=[float(c.f) for c in cams],
                    f_prior_log_sigma=[rigs.EXIF_PRIOR_LOG_SIGMA] * 3, focal_group=["phone"] * 3,
                    is_front_camera=[False] * 3, view_yaw_deg=yaws, view_pitch_deg=pitches, distance_mm=dists,
                    target=tgt)


NEAR_RANGE_MM = (300.0, 350.0)     # FU-03 diagnostic: a range where the photos alone constrain the focal


NEAR_OFF_PRIOR_F35 = 35.0          # second diagnostic: a true focal the ladder's phone guess (26 mm) misses


def _near_rig(seed: int, f35: float = 26.0):
    """Five rear-phone views (``f35`` mm-equivalent, yaw -60..60 deg) at 0.30-0.35 m: strong perspective, so
    the photos alone constrain the focal length (photos-only sigma of ln f about 0.09-0.11 at 26 mm).
    At the default 26 mm the true focal coincides with the centre of the ladder's 'phone, no focal data'
    prior (``focal.phone_f35_mm``), i.e. with the fallback the robust EXIF prior re-solves under: the
    optimistic case.  ``f35`` = :data:`NEAR_OFF_PRIOR_F35` (35 mm: the whole head still fits the
    1500 x 2000 frame at 0.30 m) puts that fallback 26 % short of the truth."""
    from face3d.synthetic import orbit_camera
    rng = streams(seed)[1]
    tgt = tuple(float(x) for x in face_centre(kit()))
    yaws = (-60.0, -30.0, 0.0, 30.0, 60.0)
    cams, pitches, dists = [], [], []
    for yaw in yaws:
        d, pitch = float(rng.uniform(*NEAR_RANGE_MM)), float(rng.uniform(*rigs.PITCH_RANGE_DEG))
        cams.append(orbit_camera(d, yaw, pitch, float(f35), width=W, height=H, target=tgt))
        pitches.append(pitch), dists.append(d)
    n = len(yaws)
    return rigs.Rig(name="near_phone", cameras=cams, f_prior_px=[float(c.f) for c in cams],
                    f_prior_log_sigma=[rigs.EXIF_PRIOR_LOG_SIGMA] * n, focal_group=["phone"] * n,
                    is_front_camera=[False] * n, view_yaw_deg=list(yaws), view_pitch_deg=pitches,
                    distance_mm=dists, target=tgt)


def task_exif_near(seed: int, factor: float = 1.0, f35: float = 26.0) -> dict:
    """FU-03 diagnostic (not a DESIGN 7.4 row): the EXIF focal of every photo of a near-range set
    (:func:`_near_rig`) multiplied by ``factor`` (1.0: correct EXIF).  The photos carry the information
    here, so the robust EXIF prior can be exercised: detection of a wrong EXIF, false alarms on a right one.
    ``f35``: the true focal of the rig (see :func:`_near_rig`: 26 mm is where the fallback prior sits)."""
    sc = make_scene(seed, detector=dict(BASE_DETECTOR), rig_obj=_near_rig(seed, f35))
    for v in range(sc.rig.n_views):
        w, h = sc.wh[v]
        sc.exif[v]["f35"] = float(focal_35mm_from_px(float(sc.rig.f_prior_px[v]) * float(factor), w, h))
    sc.truth = {"factor": float(factor), "f35": float(f35)}
    return record(run_scene(sc, "observe"), sc)


def task_selfie(seed: int) -> dict:
    """Three front-camera selfies at 0.35 m (DESIGN 7.4 'Selfies at 0.35 m')."""
    rig_obj, truth = faults.selfie_rig(streams(seed)[1], target=face_centre(kit()), width=W, height=H,
                                       **ROWS["selfie_near"]["kwargs"])
    sc = make_scene(seed, detector=dict(BASE_DETECTOR), rig_obj=rig_obj)
    sc.truth = {"distance_mm": truth["distance_mm"]}
    return record(run_scene(sc, "observe"), sc)


def task_expression(seed: int, kind: str = "jaw_open", noise_scale: float = 1.0, fit: bool = True,
                    oracle: bool = False, neutral_twin: bool = False) -> dict:
    """One expressive view among 5 (jaw 5-15 deg or a 2-4 mm smile); surface row: also the fit stage
    (``fit``; the per-push subset gates the landmark identity shift only and skips it).

    FU-04 diagnostics (never gated): ``oracle``: the expressive view carries the user tag 'expressive'
    (a perfect tagger); ``neutral_twin``: the *clean* scene with the same view tagged 'expressive' (what
    the tag's own down-weighting moves when nothing moved in the face)."""
    det = dict(BASE_DETECTOR, noise_scale=noise_scale)
    row = ROWS[kind]
    rng = _fault_rng(seed)
    lo, hi = row["sampling"]["amount"]["uniform"]
    amount = float(rng.uniform(lo, hi))
    v = int(rng.choice(row["sampling"]["view_index"]["choice"]))
    base = make_scene(seed, detector=det)
    Vs, truth = faults.expression_fault(base.sub, v, kind, amount, n_views=row["kwargs"]["n_views"])
    Xv = [base.kit.landmark_positions("anatomical44", V) for V in Vs]
    sc = base if neutral_twin else make_scene(seed, detector=det, X_views=Xv)
    if oracle or neutral_twin:
        sc.tags[v]["expression"] = "expressive"
    sc.truth = {"view": v, "amount": amount, "kind": kind}
    run = run_scene(sc, "solve")
    rec = record(run, sc)
    if fit:
        f = fit_of(run, seed)
        rec["fit_stage"] = f["stage"]
        rec["V_face"] = np.asarray(f["vertices"], float)[face_vertices()].tolist()
    return rec


def task_beauty(seed: int, noise_scale: float = 1.0, strength: float = 1.0) -> dict:
    """Beauty warp (eyes +6 %, jaw -4 %) of one view with 4 clean views.  The pipeline's post-BA Q-RETOUCH
    step (FU-03: the engine's residual test against the leave-one-view-out consensus of pass 1) is read
    from the findings and from ``retouch_pipeline``; the record also carries the same engine test evaluated
    here on the pipeline's final solve (``retouch_engine``, per view: the WP-23 evidence column)."""
    from face3d.solve import camera_model as cm
    from face3d.solve.bundle import view_noise_cov
    sc = make_scene(seed, detector=dict(BASE_DETECTOR, noise_scale=noise_scale))
    v = int(_fault_rng(seed).integers(0, sc.rig.n_views))
    kw = dict(ROWS["beauty_warp"]["kwargs"])
    if strength != 1.0:      # FU-04 diagnostic: the same warp ``strength`` times as strong (never gated)
        kw = {"eye_scale": 1.0 + strength * (kw["eye_scale"] - 1.0), "jaw_scale": 1.0 + strength * (kw["jaw_scale"] - 1.0)}
    sc.uv[v], truth = faults.beauty_warp(sc.uv[v], faults.beauty_index_map(sc.ids, sc.kinds), **kw)
    sc.truth = {"view": v, "strength": float(strength)}
    run = run_scene(sc, "solve")
    rec = record(run, sc)
    s = run.outputs["solve"]
    rec["retouch_z"] = [(r["z"] | {"t_eye": r["t_eye"]}) if r else None for r in s["retouch"]]
    res, views, lm = s["_result"], s["_views"], run.outputs["landmarks"]
    idx = {k: sc.ids.index(k) for k in ("en_L", "ex_L", "en_R", "ex_R", "go_L", "go_R", "p_L", "p_R")}
    flagged = []
    for i in range(len(views)):
        cam = res.cameras[i]
        C = view_noise_cov(views[i], res.X, cam.R, cam.t, cam.f)
        try:
            _, _, fl = cm.retouch_residual_test(lm["uv"][i], cam.project(res.X), idx, C,
                                                inliers=np.asarray(res.inlier_mask[i], bool))
        except (ValueError, KeyError, np.linalg.LinAlgError):
            fl = False
        flagged.append(bool(fl))
    rec["retouch_engine"] = flagged
    return rec


WIDE_WH = (3000, 4000)        # the ultra-wide view keeps the WP-01 frame so the face stays > 250 px
WIDE_DISTANCE_MM = 1020.0     # just outside the Q-NEAR warn distance (qa.near_warn_mm = 1000)


def task_wide(seed: int, model: str | None = None) -> dict:
    """One ultra-wide photo (f35 ~ U(13, 16) mm, FAULT_MATRIX ``requires``) replacing a view of the base
    set, with the face 35 deg off-axis under ``model`` ('stereographic' | 'rectilinear'); ``model`` None is
    the clean twin (the same ultra-wide photo with the face on the optical axis)."""
    from face3d.synthetic import orbit_camera
    row = ROWS["off_axis_stereographic"]
    rng = _fault_rng(seed)
    lo, hi = row["requires"]["camera"]["f35_mm"]["uniform"]
    f35 = float(rng.uniform(lo, hi))
    base = make_scene(seed, detector=dict(BASE_DETECTOR))
    v = int(rng.integers(1, base.rig.n_views - 1))          # not a profile view: the whole face is visible
    rig0 = base.rig
    tgt = tuple(float(x) for x in face_centre(kit()))
    cam = orbit_camera(WIDE_DISTANCE_MM, rig0.view_yaw_deg[v], rig0.view_pitch_deg[v], f35,
                       width=WIDE_WH[0], height=WIDE_WH[1], target=tgt)
    view = None
    if model is not None:
        view, truth = faults.off_axis_wide(cam, tgt, row["kwargs"]["theta_deg"], model, face_points=base.X)
        cam = view.camera
    cams = list(rig0.cameras)
    cams[v] = cam
    fpr = list(rig0.f_prior_px)
    fpr[v] = float(cam.f)
    groups = list(rig0.focal_group)
    groups[v] = "ultrawide"
    rig_obj = rigs.Rig(name="studio+ultrawide", cameras=cams, f_prior_px=fpr,
                       f_prior_log_sigma=list(rig0.f_prior_log_sigma), focal_group=groups,
                       is_front_camera=list(rig0.is_front_camera), view_yaw_deg=list(rig0.view_yaw_deg),
                       view_pitch_deg=list(rig0.view_pitch_deg), distance_mm=list(rig0.distance_mm),
                       target=rig0.target)
    sc = make_scene(seed, detector=dict(BASE_DETECTOR), rig_obj=rig_obj)
    sc.wh[v] = WIDE_WH
    sc.exif[v] = exif_for(rig_obj, v, *WIDE_WH)
    sc.exif[v]["lens_model"] = "back ultra wide camera"
    if model == "stereographic":
        # the detector noise of the pinhole simulation, added to the stereographic image of the same points
        Xo = sc.X + sc.bias_3d
        off = sc.uv[v] - cam.project(Xo)
        uv = view.project(Xo) + off
        uv[~np.isfinite(sc.uv[v][:, 0])] = np.nan
        sc.uv[v] = uv
    sc.truth = {"view": v, "f35": f35, "model": model}
    return record(run_scene(sc, "solve"), sc)


def task_occluder(seed: int, tag: str = "beard", until: str | None = None) -> dict:
    """An occluder tag on every photo (DESIGN 4.1 one-click tags).  ``until``: the last stage to run
    (default: 'observe' for the beard, 'landmarks' for glasses / hair; the release run takes glasses and
    hair to 'solve' for the Q-RETOUCH false-alarm pool, :func:`_occ_kw`)."""
    sc = make_scene(seed, detector=dict(BASE_DETECTOR))
    effect, truth = faults.occluder_fault([tag], names=sc.ids, kinds=sc.kinds)
    for t in sc.tags:
        t["occluders"] = [tag]
    sc.truth = {"tag": tag, "drop": effect["drop"].tolist(), "mult": effect["noise_multiplier"].tolist()}
    # glasses / hair: every gated action is an output of the triage and landmarks stages (flags, sigma
    # multipliers, dropped points); only the beard row needs the ledger (jaw status)
    return record(run_scene(sc, until or ("observe" if tag == "beard" else "landmarks")), sc)


def task_small(seed: int) -> dict:
    """Every camera moved back until the face is 150 px wide (Q-SMALL warn; DESIGN 7.4 'Face 150 px')."""
    base = make_scene(seed, detector=dict(BASE_DETECTOR))
    rig0 = base.rig
    cams = [faults.small_face(c, X=base.X, **ROWS["small_face"]["kwargs"])[0] for c in rig0.cameras]
    rig_obj = rigs.Rig(name="studio_small", cameras=cams, f_prior_px=list(rig0.f_prior_px),
                       f_prior_log_sigma=list(rig0.f_prior_log_sigma), focal_group=list(rig0.focal_group),
                       is_front_camera=list(rig0.is_front_camera), view_yaw_deg=list(rig0.view_yaw_deg),
                       view_pitch_deg=list(rig0.view_pitch_deg), distance_mm=list(rig0.distance_mm),
                       target=rig0.target)
    sc = make_scene(seed, detector=dict(BASE_DETECTOR), rig_obj=rig_obj)
    return record(run_scene(sc, "observe"), sc)


def task_outliers(seed: int) -> dict:
    """5 % of every view's detections displaced by 5-20 sigma (faults.gross_outliers)."""
    sc = make_scene(seed, detector=dict(BASE_DETECTOR))
    obs = detect(sc.X, sc.kinds, sc.rig, seed, **BASE_DETECTOR)
    rng = _fault_rng(seed)
    masks = []
    for v in range(sc.rig.n_views):
        sig = np.sqrt(0.5 * np.sum(np.nan_to_num(obs.sigma_px_true[v]) ** 2, axis=1))
        sc.uv[v], truth = faults.gross_outliers(sc.uv[v], ROWS["gross_outliers"]["kwargs"]["frac"], rng, sig)
        masks.append(truth["outlier_mask"].tolist())
    sc.truth = {"outlier_mask": masks}
    return record(run_scene(sc, "solve"), sc)


def task_bias(seed: int, until: str = "observe", noise_axes: str = "random", tangents: bool | None = None) -> dict:
    """A 1 mm isotropic definition bias shared by all views (replaces the simulator's per-kind bias).
    FU-04 diagnostics: ``noise_axes`` (:func:`detect`) and ``tangents`` (:func:`_tangent_cfg`)."""
    k = kit()
    base = make_scene(seed, detector=dict(BASE_DETECTOR, noise_axes=noise_axes))
    Xb, truth = faults.definition_bias(base.X, _fault_rng(seed), **ROWS["definition_bias"]["kwargs"])
    obs = detect(Xb, base.kinds, base.rig, seed, outlier_frac=0.0, definition_bias=False, noise_axes=noise_axes)
    base.uv = [u.copy() for u in obs.uv]
    return record(run_scene(base, until, config=_tangent_cfg(tangents)), base)


TASKS = {"clean": task_clean, "mirror": task_mirror, "orientation": task_orientation, "exif": task_exif,
         "exif_near": task_exif_near,
         "selfie": task_selfie, "expression": task_expression, "beauty": task_beauty, "wide": task_wide,
         "occluder": task_occluder, "small": task_small, "outliers": task_outliers, "bias": task_bias}


# ============================================================================ execution (memoised, parallel)
_MEMO: dict = {}


def _key(task) -> str:
    return json.dumps(task, sort_keys=True)


def _execute(task):
    name, seed, kw = task
    return TASKS[name](int(seed), **kw)


def _workers() -> int:
    env = os.environ.get("FACE3D_GATE_WORKERS")
    if env:
        return max(1, int(env))
    return max(1, min(4, os.cpu_count() or 1))


def collect(tasks) -> list:
    """Run ``(name, seed, kwargs)`` tasks (memoised per session; missing ones in a process pool of
    ``FACE3D_GATE_WORKERS`` workers, default min(4, cpu count)) and return their records in order.
    Every task is a pure function of its arguments (seeded), so the order of execution is irrelevant."""
    tasks = [(n, int(s), dict(kw)) for n, s, kw in tasks]
    todo = [t for t in tasks if _key(t) not in _MEMO]
    todo = list({_key(t): t for t in todo}.values())
    if todo:
        nw = min(_workers(), len(todo))
        if nw > 1:
            import multiprocessing as mp
            try:
                ctx = mp.get_context("fork")
            except ValueError:                               # no fork on this platform: run in-process
                ctx = None
            if ctx is not None:
                with ProcessPoolExecutor(max_workers=nw, mp_context=ctx) as ex:
                    for t, r in zip(todo, ex.map(_execute, todo)):
                        _MEMO[_key(t)] = r
                todo = []
        for t in todo:
            _MEMO[_key(t)] = _execute(t)
    return [_MEMO[_key(t)] for t in tasks]


# ============================================================================ the matrix
STRONG_ASYM_MM = 2.5     # FU-04 diagnostic: antisymmetric RMS of the 'strongly asymmetric' mirror subjects
STRONG_WARP = 3.0        # FU-04 diagnostic: beauty warp 3 x the DESIGN 7.4 row (eyes +18 %, jaw -12 %)
#: FU-04 diagnostics: the opt-in noise model with detection-derived tangents (``pipeline.image_tangents``
#: True) on the gate scenes ('random' axes, the WP-01 simulator: the tangents are misaligned) and on
#: detections whose anisotropic noise follows the scheme's own neighbour chords ('anatomical': aligned by
#: construction, the best case).  The shipped pipeline (tangents off, random axes) is the gated matrix.
FU04_VARIANTS = {"tangents_on": {"tangents": True},
                 "anatomical_axes": {"noise_axes": "anatomical"},
                 "anatomical_axes_tangents_on": {"noise_axes": "anatomical", "tangents": True}}
NEAR_FACTORS = (1.0, 1.3, 0.7)   # EXIF focal factors of the near-range diagnostic (1.0 = correct EXIF)
CONFIRM_SEEDS = 5      # 'after the user confirms' re-runs the flipped photo: exact, so 5 seeds suffice
CLEAN = {"surface": True, "likeness": True}


def _rear_kw(fast: bool) -> dict:
    """The clean rear-phone twin of the EXIF rows: the per-push subset needs its solve only (shape and
    focal ratios); the release run also reports its honesty numbers (docs/RESULTS.md 4.1)."""
    return {"rig": "rear_phone", "until": "solve"} if fast else {"rig": "rear_phone"}


def _occ_kw(tag: str, fast: bool) -> dict:
    """The glasses / hair rows: their gated tag actions are decided by the landmarks stage (per-push
    subset); the release run also solves them, so that the post-BA Q-RETOUCH test is measured for false
    alarms on views whose declared noise carries occluder multipliers (FU-03 review)."""
    return {"tag": tag} if fast else {"tag": tag, "until": "solve"}


def _expr_kw(kind: str, fast: bool) -> dict:
    return {"kind": kind, "fit": False} if fast else {"kind": kind}


def matrix_tasks(seeds, diagnostics: bool = False, frontal: bool = True, fast: bool = False) -> list:
    """Every task of the matrix for ``seeds``.  ``diagnostics`` adds the 0.2 x noise variants of the
    single-view tests (the WP-15 test condition), reported in docs/RESULTS.md; they carry no gate.
    ``fast`` (per-push subset): the same rows and gates with the stages no gate reads left out
    (:func:`_rear_kw`, :func:`_expr_kw`)."""
    T = []
    for i, s in enumerate(seeds):
        T += [("clean", s, CLEAN),
              ("mirror", s, {}), ("mirror", s, {"asym_mm": 0.0}),
              ("orientation", s, {}),
              ("exif", s, {"kind": "exif_crop"}), ("exif", s, {"kind": "exif_missing"}),
              ("clean", s, _rear_kw(fast)),
              ("selfie", s, {}),
              ("expression", s, _expr_kw("jaw_open", fast)), ("expression", s, _expr_kw("smile", fast)),
              ("beauty", s, {}),
              ("wide", s, {}), ("wide", s, {"model": "stereographic"}), ("wide", s, {"model": "rectilinear"}),
              ("occluder", s, {"tag": "beard"}), ("occluder", s, _occ_kw("glasses", fast)),
              ("occluder", s, _occ_kw("hair", fast)),
              ("small", s, {}), ("outliers", s, {}), ("bias", s, {})]
        if i < CONFIRM_SEEDS:
            T += [("mirror", s, {"confirm": True})]
        if frontal:
            T += [("exif", s, {"kind": "exif_missing", "frontal": True})]
        if diagnostics:
            T += [("exif_near", s, {"factor": f}) for f in NEAR_FACTORS]
            T += [("exif_near", s, {"factor": f, "f35": NEAR_OFF_PRIOR_F35}) for f in NEAR_FACTORS]
            T += [("mirror", s, {"noise_scale": LOW_NOISE}), ("clean", s, {"until": "solve", "noise_scale": LOW_NOISE}),
                  ("expression", s, {"kind": "jaw_open", "noise_scale": LOW_NOISE}),
                  ("expression", s, {"kind": "smile", "noise_scale": LOW_NOISE}),
                  ("beauty", s, {"noise_scale": LOW_NOISE}), ("mirror", s, {"rig": "rear_phone"})]
            # FU-04: the conditions under which the single-view targets hold, the floor of the identity
            # gates, and the noise model before / after (and with noise axes unrelated to the anatomy)
            T += [("mirror", s, {"asym_mm": STRONG_ASYM_MM}), ("beauty", s, {"strength": STRONG_WARP})]
            for kind in ("jaw_open", "smile"):
                T += [("expression", s, {"kind": kind, "fit": False, "oracle": True}),
                      ("expression", s, {"kind": kind, "fit": False, "neutral_twin": True})]
            for kw in FU04_VARIANTS.values():
                T += [("clean", s, kw), ("bias", s, kw)]
    return T


def _get(seeds, name, **kw):
    return collect([(name, s, kw) for s in seeds])


def _at_view(rec, values, view):
    """The entry of a per-used-view list for the scene view ``view`` (None when the view was dropped)."""
    return values[rec["views"].index(view)] if view in rec["views"] else None


def _has(rec, pid, code) -> bool:
    return any(f[0] == pid and f[1] == code for f in rec["findings"]) or \
        any(f[0] == pid and f[1] == code for f in rec.get("lm_findings", []))


def _overruled(rec) -> bool:
    """The robust EXIF prior (FU-03) replaced the EXIF focal of at least one photo of the set."""
    return any(bool(t and t["overruled"]) for t in rec.get("focal_test", []))


def _median(x) -> float:
    x = [v for v in x if v is not None]
    return float(np.median(np.asarray(x, float))) if len(x) else float("nan")


def _near_summary(nr) -> dict:
    """The near-range EXIF diagnostic of one (factor, true focal) condition (docs/RESULTS.md 3.2)."""
    fe = [_median(r["focal_rel_err"]) for r in nr]
    kept_c = [r for r in nr if any(t and t["contradicted"] for t in r["focal_test"]) and not _overruled(r)]
    return {
        "n": len(nr), "overruled": sum(_overruled(r) for r in nr),
        "contradicted": sum(any(t and t["contradicted"] for t in r["focal_test"]) for r in nr),
        # contradicted but kept (re-solve within 15 % of EXIF): each must carry a warn C-FOCAL-PRIOR
        "contradicted_kept": len(kept_c),
        "contradicted_kept_warned": sum(any(f[1] == "C-FOCAL-PRIOR" and f[2] == "warn" for f in r["findings"])
                                        for r in kept_c),
        "fallback_sources": _count([s for r in nr if _overruled(r) for s in r["focal_source"]]),
        "focal_rel_err_median": _median(fe),
        "focal_rel_err_median_overruled": _median([e for e, r in zip(fe, nr) if _overruled(r)]),
        "focal_rel_err_median_kept": _median([e for e, r in zip(fe, nr) if not _overruled(r)]),
        "abs_t_max": max(abs(r["focal_test"][0]["t"]) for r in nr),
        "abs_t_median": _median([abs(r["focal_test"][0]["t"]) for r in nr]),
        "sigma_logf_data_median": _median([r["focal_test"][0]["sigma_logf_data"] for r in nr]),
        "focal_status_counts": _count([s for r in nr for s in r["focal_statuses"]]),
        "measured_but_off_by_15pct": sum(1 for r in nr for st_, e in zip(r["focal_statuses"], r["focal_rel_err"])
                                         if st_ == "measured" and e > 0.15),
        "config_rms_mm_median": _median([r["config_rms_mm"] for r in nr])}


_EVAL: dict = {}


def evaluate(seeds, diagnostics: bool = False, frontal: bool = True, fast: bool = False) -> dict:
    """Run the matrix and reduce it to counts and medians per row (see :func:`gates`).  ``frontal``: also
    the focal-unobservable variant of the EXIF rows (release run only); ``fast``: see :func:`matrix_tasks`."""
    seeds = list(seeds)
    key = (tuple(seeds), bool(diagnostics), bool(frontal), bool(fast))
    if key not in _EVAL:
        _EVAL[key] = _evaluate(seeds, diagnostics, frontal, fast)
    return _EVAL[key]


def _evaluate(seeds, full: bool, frontal: bool, fast: bool = False) -> dict:
    collect(matrix_tasks(seeds, full, frontal, fast))
    n = len(seeds)
    clean = _get(seeds, "clean", **CLEAN)
    clean_fit = clean
    out: dict = {"n_seeds": n, "seeds": [seeds[0], seeds[-1]]}

    # ---- mirror
    mir, sym = _get(seeds, "mirror"), _get(seeds, "mirror", asym_mm=0.0)
    conf = _get(seeds[:CONFIRM_SEEDS], "mirror", confirm=True)
    dec = [_at_view(r, r["mirror"], r["truth"]["view"]) for r in mir]
    others = [d for r in mir for v, d in zip(r["views"], r["mirror"]) if v != r["truth"]["view"]]
    others += [d for r in clean for d in r["mirror"]]
    others += [d for r in sym for v, d in zip(r["views"], r["mirror"]) if v != r["truth"]["view"]]
    out["mirror"] = {
        "n": n, "tp": dec.count("suggest_flip"), "keep_on_mirrored": dec.count("keep"),
        "undetermined_on_mirrored": dec.count("undetermined"),
        "g_median": _median([_at_view(r, r["mirror_g"], r["truth"]["view"]) for r in mir]),
        "gap_median": _median([_at_view(r, r["mirror_gap"], r["truth"]["view"]) for r in mir]),
        # reference g_min of the complete rule (44 evenly loaded landmarks, rear camera); per view: mirror_det
        "g_min": float(S._mirror.derived_g_min(n_v=44)), "gap_threshold": float(S._mirror.GAP_THRESHOLD),
        "n_detectable": sum(bool(_at_view(r, r["mirror_det"], r["truth"]["view"])) for r in mir),
        "gap_max_unmirrored": float(max([g for r in list(mir) + list(sym) for v, g in zip(r["views"], r["mirror_gap"])
                                         if v != r["truth"]["view"] and g is not None]
                                        + [g for r in clean for g in r["mirror_gap"] if g is not None])),
        "n_unmirrored_views": len(others), "false_flips": others.count("suggest_flip"),
        "n_symmetric": n, "undetermined_when_symmetric": [
            _at_view(r, r["mirror"], r["truth"]["view"]) for r in sym].count("undetermined"),
        "asym_rms_mm": _median([r["truth"]["asym_rms_mm"] for r in mir]),
        "n_confirmed": len(conf),
        "shape_ratio_after_confirm": float(max(c["config_rms_mm"] / b["config_rms_mm"] for c, b in zip(conf, clean))),
        "flip_applied_only_on_decision": all(r["mirror"] is not None for r in conf),
        "shape_ratio_unconfirmed": _median([c["config_rms_mm"] / b["config_rms_mm"] for c, b in zip(mir, clean)]),
    }
    if full:
        lown = _get(seeds, "mirror", noise_scale=LOW_NOISE)
        clean_low = _get(seeds, "clean", until="solve", noise_scale=LOW_NOISE)
        d2 = [_at_view(r, r["mirror"], r["truth"]["view"]) for r in lown]
        o2 = [d for r in lown for v, d in zip(r["views"], r["mirror"]) if v != r["truth"]["view"]]
        o2 += [d for r in clean_low for d in r["mirror"]]
        low: dict = {"noise_scale": LOW_NOISE, "n": n, "mirror": {
            "tp": d2.count("suggest_flip"), "keep_on_mirrored": d2.count("keep"),
            "n_unmirrored_views": len(o2), "false_flips": o2.count("suggest_flip")}}
        rp = _get(seeds, "mirror", rig="rear_phone")
        d3 = [_at_view(r, r["mirror"], r["truth"]["view"]) for r in rp]
        low["mirror_rear_phone_nominal"] = {"tp": d3.count("suggest_flip"), "keep_on_mirrored": d3.count("keep"),
                                            "g_median": _median([_at_view(r, r["mirror_g"], r["truth"]["view"])
                                                                 for r in rp])}
        for kind in ("jaw_open", "smile"):
            ex = _get(seeds, "expression", kind=kind, noise_scale=LOW_NOISE)
            tg = [_at_view(r, r["tags"], r["truth"]["view"]) for r in ex]
            sh = [shape_shift(a["X"], b["X"])["rms"] for a, b in zip(ex, clean_low)]
            low[kind] = {"expressive": tg.count("expressive"), "non_neutral": n - tg.count("neutral"),
                         "identity_shift_rms_mm_median": _median(sh)}
        be = _get(seeds, "beauty", noise_scale=LOW_NOISE)
        eng = [bool(_at_view(r, r["retouch_engine"], r["truth"]["view"])) for r in be]
        eo = [f for r in be for v, f in zip(r["views"], r["retouch_engine"]) if v != r["truth"]["view"]]
        low["beauty_warp"] = {"engine_test_tp": int(sum(eng)), "engine_test_n_clean_views": len(eo),
                              "engine_test_fp": int(sum(eo)), "identity_bias_rms_mm_median": _median(
                                  [shape_shift(a["X"], b["X"])["rms"] for a, b in zip(be, clean_low)])}
        out["low_noise"] = low
        out["fu04"] = _fu04_summary(seeds, clean)
        for key, kw in (("exif_near", {}), ("exif_near_off_prior", {"f35": NEAR_OFF_PRIOR_F35})):
            out[key] = {"%g" % fac: _near_summary(_get(seeds, "exif_near", factor=fac, **kw)) for fac in NEAR_FACTORS}

    # ---- orientation
    ori = _get(seeds, "orientation")
    out["orientation_unbaked"] = {
        "n": n, "tp": sum(_has(r, "p%02d" % (r["truth"]["view"] + 1), "Q-ORIENT") for r in ori),
        "n_clean_photos": sum(r["n_photos"] for r in clean),
        "fp": sum(1 for r in clean for f in r["findings"] if f[1] == "Q-ORIENT")}

    # ---- EXIF
    rear = _get(seeds, "clean", **_rear_kw(fast))
    for kind in ("exif_crop", "exif_missing"):
        ex = _get(seeds, "exif", kind=kind)
        fe = [_median(r["focal_rel_err"]) for r in ex]
        out[kind] = {"n": n, "focal_rel_err_median": _median(fe),
                     "n_within_5pct": int(sum(e < 0.05 for e in fe)),
                     "clean_focal_rel_err_median": _median([_median(r["focal_rel_err"]) for r in rear]),
                     "yaw_span_deg_min": float(min(r["truth"]["yaw_span_deg"] for r in ex)),
                     "n_views": sum(len(r["focal_statuses"]) for r in ex),
                     "measured_but_off_by_15pct": sum(1 for r in ex for st_, e in zip(r["focal_statuses"],
                                                                                    r["focal_rel_err"])
                                                      if st_ == "measured" and e > 0.15),
                     "shape_ratio": _median([a["config_rms_mm"] / b["config_rms_mm"] for a, b in zip(ex, rear)]),
                     "focal_status_counts": _count([s for r in ex for s in r["focal_statuses"]]),
                     # FU-03: the robust EXIF prior (sets whose EXIF focal the photos overruled / tested) and
                     # the photos-only sigma of ln f the test saw
                     "overruled": sum(_overruled(r) for r in ex),
                     "contradicted": sum(any(t and t["contradicted"] for t in r["focal_test"]) for r in ex),
                     "sigma_logf_data_median": _median([t["sigma_logf_data"] for r in ex for t in r["focal_test"][:1]
                                                        if t]),
                     "abs_t_max": max([abs(t["t"]) for r in ex for t in r["focal_test"][:1] if t and t["t"] is not None],
                                      default=float("nan")),
                     "c_focal_exif": sum(any(f[1] == "C-FOCAL-EXIF" for f in r["findings"]) for r in ex),
                     "c_focal_prior": sum("C-FOCAL-PRIOR" in r["flags"] for r in ex)}
    # clean sets with a correct EXIF (studio ring and, when its observe stage ran, nothing more is needed:
    # the check runs in the solve stage): a false overrule is a false alarm of the robust EXIF prior
    tested = [r for r in list(clean) + list(rear)]
    out["exif_clean"] = {"n": len(tested), "overruled": sum(_overruled(r) for r in tested),
                         "abs_t_max": max([abs(t["t"]) for r in tested for t in r["focal_test"][:1]
                                           if t and t["t"] is not None], default=float("nan")),
                         "sigma_logf_data_median": _median([t["sigma_logf_data"] for r in tested
                                                            for t in r["focal_test"][:1] if t]),
                         "measured_views": sum(st_ == "measured" for r in clean for st_ in r["focal_statuses"]),
                         "n_views": sum(len(r["focal_statuses"]) for r in clean)}
    if frontal:
        fr = _get(seeds, "exif", kind="exif_missing", frontal=True)
        st = [s for r in fr for s in r["focal_statuses"]]
        out["exif_unobservable"] = {"n_views": len(st), "from_prior": st.count("prior_used"),
                                    "measured": st.count("measured"), "focal_status_counts": _count(st),
                                    "c_focal_prior_finding": sum(any(f[1] == "C-FOCAL-PRIOR" for f in r["findings"])
                                                                 or "C-FOCAL-PRIOR" in r["flags"] for r in fr),
                                    "n": n, "focal_rel_err_median": _median([_median(r["focal_rel_err"]) for r in fr]),
                                    "overruled": sum(_overruled(r) for r in fr)}

    # ---- selfies
    sel = _get(seeds, "selfie")
    out["selfie_near"] = {
        "n_photos": sum(r["n_photos"] for r in sel),
        "q_near": sum(_has(r, "p%02d" % (v + 1), "Q-NEAR") for r in sel for v in range(r["n_photos"])),
        "n": n, "tier_le_B": sum(r["tier"] not in ("S", "A") for r in sel),
        "tiers": _count([r["tier"] for r in sel]),
        "z_rel_err_median": _median([_median(r["z_rel_err"]) for r in sel]),
        "n_z_within_15pct": int(sum(_median(r["z_rel_err"]) < 0.15 for r in sel))}

    # ---- expression
    neutral_tags = [t for r in clean for t in r["tags"]]
    for kind in ("jaw_open", "smile"):
        ex = _get(seeds, "expression", **_expr_kw(kind, fast))
        tg = [_at_view(r, r["tags"], r["truth"]["view"]) for r in ex]
        sh = [shape_shift(a["X"], b["X"]) for a, b in zip(ex, clean)]
        vs = [shape_shift(a["V_face"], b["V_face"])["rms"] for a, b in zip(ex, clean_fit) if "V_face" in a]
        out[kind] = {"n": n, "expressive": tg.count("expressive"), "non_neutral": n - tg.count("neutral"),
                     "identity_shift_rms_mm_median": _median([s["rms"] for s in sh]),
                     "identity_shift_rms_mm_max": float(max(s["rms"] for s in sh)),
                     "identity_shift_max_mm_median": _median([s["max"] for s in sh]),
                     # DESIGN 4.9 words the hard gate on the neutral region: the rigid-class landmarks
                     "rigid_shift_rms_mm_median": _median([shift_rigid(a["X"], b["X"]) for a, b in zip(ex, clean)]),
                     "rigid_shift_rms_mm_max": float(max(shift_rigid(a["X"], b["X"]) for a, b in zip(ex, clean))),
                     "tagged_by": _count([x for r in ex for x in (_at_view(r, r["retag_by"], r["truth"]["view"]) or [])]),
                     "surface_shift_rms_mm_median": _median(vs),
                     "surface_shift_rms_mm_max": float(max(vs)) if vs else float("nan"),
                     "fit_stage": _count([r["fit_stage"] for r in ex if "fit_stage" in r])}
    out["expression_false_tags"] = {"n_neutral_views": len(neutral_tags),
                                    "expressive": neutral_tags.count("expressive"),
                                    "mild": neutral_tags.count("mild")}

    # ---- beauty warp
    be = _get(seeds, "beauty")
    eng = [bool(_at_view(r, r["retouch_engine"], r["truth"]["view"])) for r in be]
    eng_other = [f for r in be for v, f in zip(r["views"], r["retouch_engine"]) if v != r["truth"]["view"]]
    sh = [shape_shift(a["X"], b["X"])["rms"] for a, b in zip(be, clean)]
    pipe_other = [f for r in be for v, f in zip(r["views"], r["retouch_pipeline"]) if v != r["truth"]["view"]]
    pipe_other += [f for r in clean for f in r["retouch_pipeline"]]
    # ... and of the other unretouched sets with >= 3 views (the clean rear-phone twins and the selfies)
    pipe_other += [f for r in list(rear) + list(sel) for f in r["retouch_pipeline"]]
    # ... and of the unretouched sets whose declared noise is not the base noise (FU-03 review): the
    # beard-tagged and the 150 px (Q-SMALL, sigma x2) sets on every run, the glasses- (eye sigma x2) and
    # hair-tagged sets on the release run (they stop after the landmarks stage per push, :func:`_occ_kw`)
    occ_pool = list(_get(seeds, "occluder", tag="beard")) + list(_get(seeds, "small"))
    occ_pool += [r for tag in ("glasses", "hair") for r in _get(seeds, "occluder", **_occ_kw(tag, fast))]
    pipe_tagged = [f for r in occ_pool for f in r.get("retouch_pipeline", [])]
    pipe_other += pipe_tagged
    out["beauty_warp"] = {
        "n": n, "pipeline_q_retouch": sum(_has(r, "p%02d" % (r["truth"]["view"] + 1), "Q-RETOUCH") for r in be),
        "pipeline_n_clean_views": len(pipe_other), "pipeline_fp": int(sum(pipe_other)),
        "pipeline_n_tagged_views": len(pipe_tagged), "pipeline_fp_tagged": int(sum(pipe_tagged)),
        "engine_test_tp": int(sum(eng)), "engine_test_n_clean_views": len(eng_other),
        "engine_test_fp": int(sum(eng_other)), "identity_bias_rms_mm_median": _median(sh),
        "identity_bias_rms_mm_max": float(max(sh))}

    # ---- off-axis wide angle
    wide0 = _get(seeds, "wide")
    for name, model, expect in (("off_axis_stereographic", "stereographic", "virtual_stereo"),
                                ("off_axis_rectilinear", "rectilinear", "pinhole")):
        wd = _get(seeds, "wide", model=model)
        chosen = [_at_view(r, r["models"], r["truth"]["view"]) for r in wd]
        extra = [a["config_rms_mm"] - b["config_rms_mm"] for a, b in zip(wd, wide0)]
        out[name] = {"n": n, "q_wide": sum(_has(r, "p%02d" % (r["truth"]["view"] + 1), "Q-WIDE") for r in wd),
                     "model_correct": chosen.count(expect), "models": _count(chosen),
                     "ambiguous": sum(bool(_at_view(r, r["model_ambiguous"], r["truth"]["view"])) for r in wd),
                     "shape_extra_mm_median": _median(extra), "shape_extra_mm_max": float(max(extra)),
                     "not_applied_flag": sum("C-MODEL-NOT-APPLIED" in r["solve_flags"] for r in wd)}

    # ---- occluder tags
    ids = kit().landmark_names("anatomical44")
    be_ = _get(seeds, "occluder", tag="beard")
    jaw_ids = [i for i, nm in enumerate(ids) if nm in ("pg", "gn", "me")]
    out["beard"] = {"n": n, "jaw_prior_driven": sum(r["regions"]["jaw"][0] == "prior-driven" for r in be_),
                    "outer_bound_flag": sum(all(f.get("contour_kind") == "outer_bound" for f in r["occluder_flags"])
                                            for r in be_),
                    "chin_points_dropped": sum(not np.asarray(r["uv_used"])[:, jaw_ids].any() for r in be_),
                    "clean_jaw_status": _count([r["regions"]["jaw"][0] for r in clean])}
    gl = _get(seeds, "occluder", **_occ_kw("glasses", fast))
    eye = [i for i, m in enumerate(gl[0]["truth"]["mult"]) if m > 1.0]
    out["glasses"] = {"n": n, "no_iris_scale": sum(all(f.get("no_iris_scale") for f in r["occluder_flags"])
                                                   for r in gl),
                      # eye sigma x2 = information weight 1/4 on top of the view's own QA multiplier (a view
                      # that is also Q-SMALL carries x2 on every point: 1/4 x 1/4 on its eye points)
                      "eye_sigma_x2": sum(bool(np.allclose(
                          np.asarray(r["weights"])[:, eye] * np.asarray(r["lm_qa_sigma_mult"])[:, None] ** 2, 0.25))
                          for r in gl),
                      "n_eye_points": len(eye)}
    ha = _get(seeds, "occluder", **_occ_kw("hair", fast))
    ear = [i for i, d in enumerate(ha[0]["truth"]["drop"]) if d]
    out["hair"] = {"n": n, "no_silhouette_above_trichion": sum(
        all(f.get("no_silhouette_above") == "trichion" for f in r["occluder_flags"]) for r in ha),
        "ear_temple_points_dropped": sum(not np.asarray(r["uv_used"])[:, ear].any() for r in ha),
        "dropped_ids": [ids[i] for i in ear]}

    # ---- small face
    sm = _get(seeds, "small")
    out["small_face"] = {
        "n_photos": sum(r["n_photos"] for r in sm),
        "q_small": sum(_has(r, "p%02d" % (v + 1), "Q-SMALL") for r in sm for v in range(r["n_photos"])),
        "excluded": sum(len(r["lm_excluded"]) for r in sm),
        "missed": [[r["seed"], v] for r in sm for v in range(r["n_photos"]) if not _has(r, "p%02d" % (v + 1), "Q-SMALL")],
        # every view of a 150 px set carries the x2 Q-SMALL multiplier: chi2_red against the noise before
        # it must be 4 x the solve's own (WBS FU-02: 'chi2_red and gamma BEFORE the QA sigma multipliers')
        "chi2_ratio": [[min(r["qa_sigma_mult"]), max(r["qa_sigma_mult"]), r["chi2_red"] / r["chi2_red_solve"]]
                       for r in sm],
        "inflation_median": _median([r["inflation"] for r in sm]),
        **_pooled_honesty(sm), "clean": _pooled_honesty(clean)}

    # ---- gross outliers
    ou = _get(seeds, "outliers")
    caught = lost = n_out = n_in = 0
    for r in ou:
        m = np.asarray(r["truth"]["outlier_mask"], bool)[r["views"]]
        used, inl = np.asarray(r["uv_used"], bool), np.asarray(r["inlier"], bool)
        n_out += int((m & used).sum())
        caught += int((m & used & ~inl).sum())
        n_in += int((~m & used).sum())
        lost += int((~m & used & ~inl).sum())
    lost_clean = sum(int((np.asarray(r["uv_used"], bool) & ~np.asarray(r["inlier"], bool)).sum()) for r in clean)
    out["gross_outliers"] = {
        "n_outliers": n_out, "caught": caught, "n_inliers": n_in, "inliers_lost": lost,
        "clean_n": sum(int(np.asarray(r["uv_used"], bool).sum()) for r in clean), "clean_lost": lost_clean,
        "shape_ratio": _median([a["config_rms_mm"] / b["config_rms_mm"] for a, b in zip(ou, clean)])}

    # ---- definition bias
    bi = _get(seeds, "bias")
    out["definition_bias"] = {"n": n, **_pooled_honesty(bi)}

    # ---- alarm budget on the clean sets
    sev = [f for r in clean for f in r["findings"] if f[2] in faults.ALARM_BUDGET["severities"]]
    out["alarm"] = {"n_sets": n, "n_photos": sum(r["n_photos"] for r in clean), "spurious": len(sev),
                    "codes": _count([f[1] for f in sev]),
                    "rear_phone_codes": _count([f[1] for r in rear for f in r["findings"]
                                                if f[2] in faults.ALARM_BUDGET["severities"]]),
                    "rear_phone_photos": sum(r["n_photos"] for r in rear)}
    out["clean"] = {"config_rms_mm_median": _median([r["config_rms_mm"] for r in clean]),
                    "tiers": _count([r["tier"] for r in clean]),
                    "gamma_median": _median([r["gamma"] for r in clean]),
                    "chi2_red_median": _median([r["chi2_red"] for r in clean]),
                    "inflation_median": _median([r["inflation"] for r in clean]),
                    "deflate": _count([r["deflate"] for r in clean])}
    return out


def rigid_mask() -> np.ndarray:
    """(44,) bool: rigid expression class (the 'neutral region' of the DESIGN 4.9 hard gate)."""
    return np.array([ANATOMICAL[i].expr_class == "rigid" for i in kit().landmark_names("anatomical44")])


def shift_rigid(Xa, Xb) -> float:
    """RMS displacement (mm) of the rigid-class landmarks between two solutions after the similarity
    alignment of all 44 (the 'neutral-region identity' of DESIGN 4.9; reported next to the 44-landmark gate)."""
    err, _, _ = aligned_error(np.asarray(Xa, float), np.asarray(Xb, float))
    d = np.linalg.norm(err, axis=1)[rigid_mask()]
    return float(np.sqrt(np.mean(d ** 2)))


def _fu04_summary(seeds, clean) -> dict:
    """FU-04 diagnostics of docs/RESULTS.md 3.2 (never gated): conditions under which the single-view
    targets hold, the floor of the identity gates and the noise-model variants."""
    n = len(seeds)
    out: dict = {}
    st = _get(seeds, "mirror", asym_mm=STRONG_ASYM_MM)
    dec = [_at_view(r, r["mirror"], r["truth"]["view"]) for r in st]
    gs = [_at_view(r, r["mirror_g"], r["truth"]["view"]) or 0.0 for r in st]
    det = [d for d, r in zip(dec, st) if _at_view(r, r["mirror_det"], r["truth"]["view"])]
    oth = [d for r in st for v, d in zip(r["views"], r["mirror"]) if v != r["truth"]["view"]]
    out["mirror_strong"] = {"asym_rms_mm": _median([r["truth"]["asym_rms_mm"] for r in st]), "n": n,
                            "tp": dec.count("suggest_flip"), "keep": dec.count("keep"), "g_median": _median(gs),
                            "n_detectable": len(det), "tp_detectable": det.count("suggest_flip"),
                            "false_flips": oth.count("suggest_flip"), "keep_unmirrored": oth.count("keep"),
                            "n_unmirrored_views": len(oth)}
    be = _get(seeds, "beauty", strength=STRONG_WARP)
    out["beauty_strong"] = {"strength": STRONG_WARP, "n": n,
                            "pipeline_tp": sum(bool(_at_view(r, r["retouch_pipeline"], r["truth"]["view"])) for r in be),
                            "pipeline_fp": sum(f for r in be for v, f in zip(r["views"], r["retouch_pipeline"])
                                               if v != r["truth"]["view"])}
    be1 = _get(seeds, "beauty")
    for key, recs in (("beauty_z", be1), ("beauty_strong_z", be)):
        zs = [_at_view(r, r["retouch_z"], r["truth"]["view"]) for r in recs]
        out[key] = {k: _median([z[k] for z in zs if z and z.get(k) is not None])
                    for k in ("eye_width_ratio", "bigonial_ratio", "t_eye")}
    for kind in ("jaw_open", "smile"):
        auto = _get(seeds, "expression", kind=kind)
        orc = _get(seeds, "expression", kind=kind, fit=False, oracle=True)
        twin = _get(seeds, "expression", kind=kind, fit=False, neutral_twin=True)
        pairs = {"auto_vs_clean": (auto, clean), "oracle_vs_clean": (orc, clean),
                 "oracle_vs_same_tag_clean": (orc, twin), "same_tag_clean_vs_clean": (twin, clean)}
        out[kind + "_identity"] = {
            name: {"rms44_median": _median([shape_shift(a["X"], b["X"])["rms"] for a, b in zip(A, B)]),
                   "rms44_max": float(max(shape_shift(a["X"], b["X"])["rms"] for a, b in zip(A, B))),
                   "rigid_median": _median([shift_rigid(a["X"], b["X"]) for a, b in zip(A, B)]),
                   "rigid_max": float(max(shift_rigid(a["X"], b["X"]) for a, b in zip(A, B)))}
            for name, (A, B) in pairs.items()}
    var: dict = {}
    for name, kw in dict(FU04_VARIANTS, shipped={}).items():
        cl = _get(seeds, "clean", **(kw or CLEAN))
        bi = _get(seeds, "bias", **kw)
        var[name] = {"chi2_red_median": _median([r["chi2_red"] for r in cl]),
                     "gamma_median": _median([r["gamma"] for r in cl]),
                     "inflation_median": _median([r["inflation"] for r in cl]),
                     "config_rms_mm_median": _median([r["config_rms_mm"] for r in cl]),
                     "inliers_lost": sum(int((np.asarray(r["uv_used"], bool) & ~np.asarray(r["inlier"], bool)).sum())
                                         for r in cl),
                     "n_obs": sum(int(np.asarray(r["uv_used"], bool).sum()) for r in cl),
                     "clean": _pooled_honesty(cl), "definition_bias": _pooled_honesty(bi),
                     "scale_z_rms": float(np.sqrt(np.mean([r["scale_z"] ** 2 for r in cl])))}
    out["noise_model"] = var
    return out


def _count(items) -> dict:
    out: dict = {}
    for i in items:
        out[str(i)] = out.get(str(i), 0) + 1
    return dict(sorted(out.items()))


def _pooled_honesty(recs) -> dict:
    """Mean NEES/dof over seeds and the pooled aligned 1-sigma coverage of the covariance the pipeline
    reports (``sigma_rep``; the shipped FU-02 factor), and, as evidence (suffix ``_design``), of the same
    covariance under the DESIGN 4.13 factor max(1, gamma^2, chi2_red)."""
    out = {}
    for key, tag in (("honesty", ""), ("honesty_design", "_design")):
        h = [r[key] for r in recs]
        out["nees_per_dof" + tag] = float(np.mean([x["nees"] for x in h]))
        out["coverage_1s" + tag] = float(sum(x["n_in_1s"] for x in h) / max(1, sum(x["n_z"] for x in h)))
    return out


# ============================================================================ gates
@dataclass
class Gate:
    name: str            # '<row>.<what>'
    row: str             # FAULT_MATRIX row name ('alarm' for the budget)
    kind: str            # 'design' (a DESIGN 7.4 target) | 'honesty' (must hold whatever the rate) | 'floor' | 'info'
    target: str
    measured: str
    ok: bool             # passes (rates: not rejected at the binomial 95 % bound)
    met: bool = True     # the point estimate itself meets the target (no statistical slack)


#: Gates that do not meet their DESIGN 7.4 target today, with the reason (docs/RESULTS.md has the measured
#: numbers and the proposed fix).  They are NOT relaxed: each is still evaluated and reported, each must be
#: listed in docs/RESULTS.md and under the DESIGN 7.4 table, and the release run fails when one of them
#: starts to pass (so this list cannot go stale).  The matching 'honesty' and 'floor' gates always apply.
CALIBRATION_PENDING: dict = {
    "mirror.tpr": "FU-04: 1 of 30 mirrored views is flagged (0 before). The test is now calibrated (gap threshold "
                  "tau = 13.83 for a false-flip rate <= 1e-4, per-view g_min >= 11.6 for 95 % power of the "
                  "complete rule, declared predictive noise), but the detectability of the consensus asymmetry "
                  "through the pipeline is g ~1.4 "
                  "(median): no view reaches g_min at nominal noise, nor at 2.5 mm asymmetry (g ~1.7: the "
                  "4-view consensus carries a shrunk asymmetry). Unreachable at nominal noise; never a false "
                  "flip or a false 'keep'",
    "exif_crop.focal": "an EXIF focal that is wrong by +/-30 % is kept (median focal error 0.28): the robust EXIF "
                       "prior of FU-03 fires on 0 of 30 sets, because the photos alone do not constrain the focal "
                       "at 0.6-1.5 m under the engine's declared noise (photos-only sigma of ln f median 0.29 "
                       "against the 0.25 the test requires)",
    "exif_missing.focal": "without EXIF the focal error is 0.11 (median) on a 120 deg rear-phone "
                          "set: above the 5 % target (com R8.4)",
    "jaw_open.identity": "FU-04: the jaw view is now tagged 'expressive' on 28 of 30 sets and the result equals a "
                         "perfect tagger's, but the identity still moves 0.55 mm RMS (1.03 before; hard bound "
                         "0.3 mm): 0.35 mm is what the tag's own down-weighting moves on a neutral face at "
                         "nominal noise, the rest is the jaw hinge under its 3 deg prior",
    "smile.tpr": "a 2-4 mm mouth-corner motion stays inside the null of the mobile-class chi2 at nominal noise "
                 "(0 of 30 tagged 'expressive' at a 1e-3 false-alarm rate; 2 'mild')",
    "smile.identity": "median 0.16 mm but single seeds reach 0.5 mm (hard bound 0.3 mm on every seed); tagging "
                      "would not help: a perfect tagger moves it 0.36 mm (the tag's own down-weighting)",
    "beauty_warp.tpr": "the post-BA Q-RETOUCH test flags 0 of 30 warped views: the warp moves the eye-width ratio "
                       "by 0.7 and the bigonial ratio by 2.2 declared sigmas (medians) against the threshold 3; "
                       "the eye corners are sharp junctions (isotropic 1.25 mm), which image tangents would not "
                       "narrow. A 3 x stronger warp is flagged on 6 of 30",
    "off_axis_stereographic.model": "virtual_stereo is selected for 22 of 30 views (0.73; pinhole 7, k1 1): below "
                                    "the 0.8 target as a point estimate, although not rejected at the binomial "
                                    "95 % bound; the selected model is recorded but not applied "
                                    "(C-MODEL-NOT-APPLIED)",
    "hair.scalp_inside_hull": "not evaluable: the landmark pipeline has no hair silhouette (needs ContourObs / "
                              "stage D inputs); reported as not evaluated, never as passed",
    "small_face.coverage": "sigma_rep stays over-conservative on Q-SMALL sets (1-sigma coverage above 0.76) by "
                           "design: the x2 down-weight widens the posterior, and chi2_red / gamma are taken "
                           "against the noise before the multiplier (FU-02), so the caution is not deflated away",
}

#: Honesty gates that FAIL today.  These are not calibration items: each is an open RELEASE BLOCKER (H12),
#: listed as such in docs/RESULTS.md and under the DESIGN 7.4 table.  The tests keep the tree green only
#: while the entry is failing *and* documented; nothing here is relaxed, and the release run fails when an
#: entry starts to pass (so the list cannot go stale) or when any other honesty gate fails.
#: Empty since FU-03: ``exif_crop.focal_label`` (focal 'measured' inherited from a wrong EXIF prior) was
#: closed by deriving the label from the photos' own information (docs/RESULTS.md 3.1).
OPEN_HONESTY_VIOLATIONS: dict = {}


def _rate(k: int, n: int) -> str:
    return f"{k}/{n} = {k / n:.3f}" if n else "0/0"


def chi2_halfwidth(total_dof: int) -> float:
    """95 % half-width of a mean NEES/dof over ``total_dof`` degrees of freedom under a correct model
    (chi-square: 1.96 sqrt(2 / D)); the continuous analogue of the binomial relaxation, used by the
    per-push subset only."""
    return 1.96 * math.sqrt(2.0 / max(1, int(total_dof)))


def _ge(k: int, n: int, p0: float) -> tuple:
    """(not rejected at the binomial 95 % bound, point estimate meets the target) for 'rate >= p0'."""
    return rate_at_least(k, n, p0), n > 0 and k / n >= p0


def _le(k: int, n: int, p0: float) -> tuple:
    return rate_at_most(k, n, p0), n > 0 and k / n <= p0


def gates(m: dict, relax_continuous: bool = False) -> list:
    """Every gate of the matrix evaluated on ``m`` = :func:`evaluate` output.

    Rates use the one-sided binomial 95 % rule of the module docstring.  ``relax_continuous`` (the
    per-push 5-seed subset) widens the NEES band by :func:`chi2_halfwidth`; nothing else is relaxed."""
    G: list = []

    def add(name, kind, target, measured, ok):
        ok, met = ok if isinstance(ok, tuple) else (ok, ok)
        G.append(Gate(name, name.split(".")[0], kind, target, measured, bool(ok), bool(met)))
    n = m["n_seeds"]
    thr = {r["name"]: r["threshold"] for r in faults.FAULT_MATRIX}
    deg = {r["name"]: r["degradation_bound"] for r in faults.FAULT_MATRIX}

    x, t = m["mirror"], thr["mirror"]
    add("mirror.tpr", "design", f"suggest flip TPR >= {t['tpr_min']} at >= {t['asym_rms_mm_min']} mm asymmetry",
        _rate(x["tp"], x["n"]) + f" at {x['asym_rms_mm']:.2f} mm (detectability g median {x['g_median']:.1f}, "
        f"{x['n_detectable']}/{x['n']} views at g >= their g_min (>= {x['g_min']:.2f}); gap median {x['gap_median']:.1f} "
        f"against tau = {x['gap_threshold']:.2f})", _ge(x["tp"], x["n"], t["tpr_min"]))
    add("mirror.fpr", "design", f"false flips <= {t['fpr_max']}", _rate(x["false_flips"], x["n_unmirrored_views"]),
        _le(x["false_flips"], x["n_unmirrored_views"], t["fpr_max"]))
    add("mirror.undetermined_when_symmetric", "design", f">= {t['undetermined_when_symmetric_min']}",
        _rate(x["undetermined_when_symmetric"], x["n_symmetric"]),
        _ge(x["undetermined_when_symmetric"], x["n_symmetric"], t["undetermined_when_symmetric_min"]))
    add("mirror.shape_after_confirm", "design", f"shape <= {deg['mirror']['shape_rms_ratio_max']} x clean",
        f"max ratio {x['shape_ratio_after_confirm']:.3f} ({x['n_confirmed']} seeds)",
        x["shape_ratio_after_confirm"] <= deg["mirror"]["shape_rms_ratio_max"])
    add("mirror.no_false_keep", "honesty", "'keep' on a mirrored view <= 0.30 (WP-15; else 'undetermined')",
        _rate(x["keep_on_mirrored"], x["n"]), _le(x["keep_on_mirrored"], x["n"], 0.30))
    add("mirror.no_false_flip", "honesty", "no flip suggested on an unmirrored view",
        _rate(x["false_flips"], x["n_unmirrored_views"]) + f" (largest gap {x['gap_max_unmirrored']:.1f} against "
        f"tau = {x['gap_threshold']:.2f})", x["false_flips"] == 0)

    x, t = m["orientation_unbaked"], thr["orientation_unbaked"]
    add("orientation_unbaked.tpr", "design", f"Q-ORIENT TPR >= {t['tpr_min']}", _rate(x["tp"], x["n"]),
        _ge(x["tp"], x["n"], t["tpr_min"]))
    add("orientation_unbaked.no_false_alarm", "honesty", "no Q-ORIENT on a baked photo",
        _rate(x["fp"], x["n_clean_photos"]), x["fp"] == 0)

    for kind in ("exif_crop", "exif_missing"):
        x, t = m[kind], thr[kind]
        add(f"{kind}.focal", "design", f"focal error < {t['focal_rel_err_max']} when views span >= "
            f"{t['when_yaw_span_deg_min']:g} deg", f"median {x['focal_rel_err_median']:.3f} (span "
            f"{x['yaw_span_deg_min']:g} deg; {x['n_within_5pct']}/{x['n']} seeds within"
            + (f"; EXIF overruled in {x['overruled']}/{x['n']} sets, photos-only sigma(ln f) median "
               f"{x['sigma_logf_data_median']:.2f}, largest |t| {x['abs_t_max']:.2f}" if kind == "exif_crop" else "")
            + ")", x["focal_rel_err_median"] < t["focal_rel_err_max"])
        add(f"{kind}.shape", "design", f"shape <= {deg[kind]['shape_rms_ratio_max']} x clean",
            f"median ratio {x['shape_ratio']:.3f}", x["shape_ratio"] <= deg[kind]["shape_rms_ratio_max"])
        add(f"{kind}.focal_floor", "floor", "focal error not worse than recorded (0.35 crop / 0.20 missing)",
            f"median {x['focal_rel_err_median']:.3f}",
            x["focal_rel_err_median"] <= (0.35 if kind == "exif_crop" else 0.20))
    x = m["exif_crop"]
    add("exif_crop.focal_label", "honesty", "H5: no view labelled focal 'measured' while > 15 % off",
        _rate(x["measured_but_off_by_15pct"], x["n_views"]), x["measured_but_off_by_15pct"] == 0)
    x = m["exif_missing"]
    add("exif_missing.focal_label", "honesty", "H5: no view labelled focal 'measured' while > 15 % off",
        _rate(x["measured_but_off_by_15pct"], x["n_views"]), x["measured_but_off_by_15pct"] == 0)
    x = m["exif_clean"]
    from face3d.solve.focal import FOCAL_DEFAULTS as _FD
    alpha = float(_FD["exif_reject_alpha"].value)
    add("exif_crop.no_false_overrule", "honesty", f"a correct EXIF focal overruled on <= {alpha:g} of the clean sets "
        "(focal.exif_reject_alpha: the stated false-alarm rate of the robust EXIF prior)",
        _rate(x["overruled"], x["n"]) + f" (largest |t| {x['abs_t_max']:.2f}; photos-only sigma(ln f) median "
        f"{x['sigma_logf_data_median']:.2f})", _le(x["overruled"], x["n"], alpha))
    if "exif_unobservable" in m:
        x = m["exif_unobservable"]
        add("exif_unobservable.c_focal_prior", "design", "C-FOCAL-PRIOR raised when the focal is unobservable",
            _rate(x["c_focal_prior_finding"], x["n"]) + f"; labels {x['focal_status_counts']}",
            x["c_focal_prior_finding"] == x["n"])
        add("exif_unobservable.never_measured", "honesty", "H5: an unobservable focal is never labelled 'measured'",
            _rate(x["measured"], x["n_views"]), x["measured"] == 0)
        add("exif_unobservable.focal_floor", "floor", "focal error on the unobservable set not worse than recorded "
            "(0.12; WP-23: 0.10) and no prior overruled", f"median {x['focal_rel_err_median']:.3f}; overruled "
            f"{x['overruled']}/{x['n']}", x["focal_rel_err_median"] <= 0.12 and x["overruled"] == 0)

    x, t = m["selfie_near"], thr["selfie_near"]
    add("selfie_near.q_near", "design", "Q-NEAR on every selfie at 0.35 m", _rate(x["q_near"], x["n_photos"]),
        x["q_near"] == x["n_photos"])
    add("selfie_near.tier", "design", f"tier <= {t['tier_max']}", f"{_rate(x['tier_le_B'], x['n'])} {x['tiers']}",
        x["tier_le_B"] == x["n"])
    add("selfie_near.distance", "design", f"z within {t['distance_rel_err_max']}",
        f"median {x['z_rel_err_median']:.3f}; {x['n_z_within_15pct']}/{x['n']} sets within",
        x["z_rel_err_median"] < t["distance_rel_err_max"] and x["n_z_within_15pct"] == x["n"])

    for kind, floor in (("jaw_open", 1.0), ("smile", 0.5)):     # jaw floor 2.0 before FU-04 (measured 1.03 then)
        x, t, d = m[kind], thr[kind], deg[kind]
        add(f"{kind}.tpr", "design", f"expressive tag TPR >= {t['tpr_min']}",
            f"expressive {_rate(x['expressive'], x['n'])}; non-neutral {x['non_neutral']}/{x['n']}; tagged by "
            f"{x['tagged_by']}",
            _ge(x["expressive"], x["n"], t["tpr_min"]))
        add(f"{kind}.identity", "design", f"neutral identity moved < {d['neutral_identity_shift_mm_max']} mm (hard: "
            "every seed)", f"landmark RMS median {x['identity_shift_rms_mm_median']:.2f}, max "
            f"{x['identity_shift_rms_mm_max']:.2f} mm; surface RMS median {x['surface_shift_rms_mm_median']:.2f}, "
            f"max {x['surface_shift_rms_mm_max']:.2f} mm; rigid-class landmarks median "
            f"{x['rigid_shift_rms_mm_median']:.2f}, max {x['rigid_shift_rms_mm_max']:.2f} mm" if x["fit_stage"] else
            f"landmark RMS median {x['identity_shift_rms_mm_median']:.2f}, max {x['identity_shift_rms_mm_max']:.2f} mm "
            f"(rigid-class landmarks median {x['rigid_shift_rms_mm_median']:.2f}; surface fit: release run only)",
            x["identity_shift_rms_mm_max"] < d["neutral_identity_shift_mm_max"])
        add(f"{kind}.identity_floor", "floor", f"median identity shift <= {floor} mm (recorded level, not a target)",
            f"{x['identity_shift_rms_mm_median']:.2f} mm", x["identity_shift_rms_mm_median"] <= floor)
    x = m["expression_false_tags"]
    add("jaw_open.no_false_expressive", "honesty", "no neutral view tagged 'expressive'",
        _rate(x["expressive"], x["n_neutral_views"]) + f" ('mild': {x['mild']})", x["expressive"] == 0)

    x, t, d = m["beauty_warp"], thr["beauty_warp"], deg["beauty_warp"]
    add("beauty_warp.tpr", "design", f"Q-RETOUCH TPR >= {t['tpr_min']} with >= {t['min_clean_views']} clean views",
        f"pipeline (post-BA test against the LOVO consensus) {_rate(x['pipeline_q_retouch'], x['n'])}; the same "
        f"engine test on the final solve {_rate(x['engine_test_tp'], x['n'])}",
        _ge(x["pipeline_q_retouch"], x["n"], t["tpr_min"]))
    add("beauty_warp.identity", "design", f"identity bias <= {d['identity_bias_mm_max']} mm",
        f"RMS median {x['identity_bias_rms_mm_median']:.2f}, max {x['identity_bias_rms_mm_max']:.2f} mm",
        x["identity_bias_rms_mm_median"] <= d["identity_bias_mm_max"])
    ok_p = _le(x["pipeline_fp"], x["pipeline_n_clean_views"], 0.05)
    ok_e = _le(x["engine_test_fp"], x["engine_test_n_clean_views"], 0.05)
    add("beauty_warp.no_false_alarm", "honesty", "Q-RETOUCH on <= 0.05 of the unwarped views (pipeline: the 4 "
        "other views of each warped set and every view of the clean studio, clean rear-phone, selfie, beard, 150 px "
        "and (release run) glasses and hair sets; and the engine test on the final solve)",
        f"pipeline {_rate(x['pipeline_fp'], x['pipeline_n_clean_views'])} (of which occluder-tagged / 150 px "
        f"views {_rate(x['pipeline_fp_tagged'], x['pipeline_n_tagged_views'])}); engine test "
        f"{_rate(x['engine_test_fp'], x['engine_test_n_clean_views'])}", (ok_p[0] and ok_e[0], ok_p[1] and ok_e[1]))

    for kind in ("off_axis_stereographic", "off_axis_rectilinear"):
        x, t, d = m[kind], thr[kind], deg[kind]
        add(f"{kind}.q_wide", "design", "Q-WIDE on the ultra-wide photo", _rate(x["q_wide"], x["n"]),
            x["q_wide"] == x["n"])
        add(f"{kind}.model", "design", f"model {t['expected_model']} chosen >= {t['correct_model_min']}",
            f"{_rate(x['model_correct'], x['n'])} {x['models']}",
            _ge(x["model_correct"], x["n"], t["correct_model_min"]))
        add(f"{kind}.shape", "design", f"shape < {d['shape_extra_mm_max']} mm extra",
            f"median {x['shape_extra_mm_median']:+.2f} mm, max {x['shape_extra_mm_max']:+.2f} mm",
            x["shape_extra_mm_median"] < d["shape_extra_mm_max"])

    x = m["beard"]
    add("beard.jaw_prior_driven", "design", "beard -> jaw prior-driven", _rate(x["jaw_prior_driven"], x["n"])
        + f" (clean: {x['clean_jaw_status']})", x["jaw_prior_driven"] == x["n"])
    add("beard.tag_actions", "design", "chin points dropped, jaw outline flagged outer_bound",
        f"dropped {x['chin_points_dropped']}/{x['n']}, flag {x['outer_bound_flag']}/{x['n']}",
        x["chin_points_dropped"] == x["n"] and x["outer_bound_flag"] == x["n"])
    x = m["glasses"]
    add("glasses.tag_actions", "design", "no iris scale, eye sigma x2",
        f"no_iris_scale {x['no_iris_scale']}/{x['n']}, eye sigma x2 {x['eye_sigma_x2']}/{x['n']}",
        x["no_iris_scale"] == x["n"] and x["eye_sigma_x2"] == x["n"])
    x = m["hair"]
    add("hair.tag_actions", "design", "no silhouette above trichion",
        _rate(x["no_silhouette_above_trichion"], x["n"]), x["no_silhouette_above_trichion"] == x["n"])
    add("hair.points_dropped", "design", "ear / temple / trichion points dropped (" + ", ".join(x["dropped_ids"])
        + ")", _rate(x["ear_temple_points_dropped"], x["n"]), x["ear_temple_points_dropped"] == x["n"])
    add("hair.scalp_inside_hull", "design", "scalp inside hull", "not evaluated (no hair silhouette input)", False)

    x, t = m["small_face"], thr["small_face"]
    lo, hi = t["coverage_1s_range"]
    add("small_face.q_small", "design", "Q-SMALL on every 150 px face", _rate(x["q_small"], x["n_photos"])
        + (f"; missed (seed, view): {x['missed']}" if x["missed"] else ""), x["q_small"] == x["n_photos"])
    add("small_face.coverage", "design", f"coverage holds: 1-sigma coverage in [{lo}, {hi}]",
        f"{x['coverage_1s']:.3f} (NEES/dof {x['nees_per_dof']:.2f}; clean sets {x['clean']['coverage_1s']:.3f}; "
        f"DESIGN factor {x['coverage_1s_design']:.3f})", lo <= x["coverage_1s"] <= hi)
    ratios = [q for _, _, q in x["chi2_ratio"]]
    add("small_face.calibration_noise", "honesty", "chi2_red taken against the noise before the QA multiplier (m^2 x "
        "the solve's own when every view carries the multiplier m); sigma_rep factor above the deflation floor",
        f"chi2_red ratio {min(ratios):.3f}-{max(ratios):.3f}; factor median {x['inflation_median']:.2f}",
        all((abs(q - lo_m ** 2) <= 1e-6 * q) if lo_m == hi_m else (lo_m ** 2 - 1e-9 <= q <= hi_m ** 2 + 1e-9)
            for lo_m, hi_m, q in x["chi2_ratio"]) and max(hi_m for _, hi_m, _ in x["chi2_ratio"]) >= 2.0
        and x["inflation_median"] > 0.5 + 1e-9)
    add("small_face.not_overconfident", "honesty", f"1-sigma coverage >= {lo} and NEES/dof <= 1.25",
        f"{x['coverage_1s']:.3f}, {x['nees_per_dof']:.2f}", x["coverage_1s"] >= lo and x["nees_per_dof"] <= 1.25)

    x, t, d = m["gross_outliers"], thr["gross_outliers"], deg["gross_outliers"]
    add("gross_outliers.caught", "design", f">= {t['caught_min']} of the outliers rejected",
        _rate(x["caught"], x["n_outliers"]), _ge(x["caught"], x["n_outliers"], t["caught_min"]))
    add("gross_outliers.inliers_lost", "design", f"<= {t['inliers_lost_max']} of the inliers lost",
        _rate(x["inliers_lost"], x["n_inliers"]) + f" (clean sets: {_rate(x['clean_lost'], x['clean_n'])})",
        _le(x["inliers_lost"], x["n_inliers"], t["inliers_lost_max"]))
    add("gross_outliers.shape", "design", f"shape <= {d['shape_rms_ratio_max']} x clean",
        f"median ratio {x['shape_ratio']:.3f}", x["shape_ratio"] <= d["shape_rms_ratio_max"])

    x, t = m["definition_bias"], thr["definition_bias"]
    lo, hi = t["nees_per_dof_range"]
    slack = chi2_halfwidth(n * 125) if relax_continuous else 0.0
    add("definition_bias.nees", "design", f"NEES/dof with sigma_rep in [{lo}, {hi}]",
        f"{x['nees_per_dof']:.3f} (DESIGN factor: {x['nees_per_dof_design']:.3f})",
        (lo - slack <= x["nees_per_dof"] <= hi + slack, lo <= x["nees_per_dof"] <= hi))

    x, b = m["alarm"], faults.ALARM_BUDGET
    add("alarm.budget", "design", f"<= {b['max_spurious_findings_per_photo']} spurious warn/block findings per clean "
        "photo", f"{x['spurious']} on {x['n_photos']} photos of {x['n_sets']} sets {x['codes']}",
        x["spurious"] <= b["max_spurious_findings_per_photo"] * x["n_photos"])
    return G


def status_of(g: Gate, pending=None, strict: bool = False) -> str:
    """The Status cell of a gate in docs/RESULTS.md."""
    pending = CALIBRATION_PENDING if pending is None else pending
    good = g.met if strict else g.ok
    if g.name in OPEN_HONESTY_VIOLATIONS:
        return "**FAIL: open release blocker**" if not good else "open release blocker (met on this run)"
    if g.name in pending:
        if g.met:
            return "calibration-pending (met on this run)"
        return "calibration-pending" + (" (within the binomial bound)" if g.ok else "")
    if g.kind == "info":
        return "reported"
    return "pass" if good else "FAIL"


def report(m: dict, relax_continuous: bool = False, strict: bool = True) -> str:
    """Markdown table of the gates (the body of the fault-matrix section of docs/RESULTS.md)."""
    lines = ["| Gate | Kind | Target | Measured | Status |", "|---|---|---|---|---|"]
    for g in gates(m, relax_continuous):
        lines.append(f"| `{g.name}` | {g.kind} | {g.target} | {g.measured} | {status_of(g, strict=strict)} |")
    return "\n".join(lines)


def failed_gates(G, strict: bool = False, pending=None) -> list:
    """Gates of ``G`` that fail and are neither calibration-pending nor a listed open honesty violation
    (must be empty).

    ``strict`` False (per-push 5-seed subset): a rate gate fails when it is rejected at the binomial 95 %
    bound (``Gate.ok``), the only relaxation WBS WP-23 item 3 allows, and only for that subset.
    ``strict`` True (release run): the point estimate itself must meet the DESIGN target (``Gate.met``);
    e.g. 26/30 against 'TPR >= 0.95' fails although the binomial bound would not reject it.
    Honesty and floor gates may only be excused through :data:`OPEN_HONESTY_VIOLATIONS`, never through
    the calibration-pending list."""
    pending = CALIBRATION_PENDING if pending is None else pending
    out = []
    for g in G:
        if g.kind == "info":
            continue
        good = (g.ok and g.met) if strict else g.ok
        excused = g.name in OPEN_HONESTY_VIOLATIONS if g.kind in ("honesty", "floor") else g.name in pending
        if not good and not excused:
            out.append(f"{g.name}: target {g.target}; measured {g.measured}")
    return out


def stale_gates(G, pending=None) -> list:
    """Pending gates and open honesty violations that now meet their target (to be removed from the lists)."""
    pending = CALIBRATION_PENDING if pending is None else pending
    return [g.name for g in G if g.ok and g.met and (g.name in pending or g.name in OPEN_HONESTY_VIOLATIONS)]


def failures(m: dict, relax_continuous: bool = False, strict: bool = False) -> list:
    """:func:`failed_gates` of the matrix ``m``."""
    return failed_gates(gates(m, relax_continuous), strict)


def pending_measured(m: dict) -> dict:
    """{gate name: measured text} of the calibration-pending gates (for docs/RESULTS.md)."""
    return {g.name: g.measured for g in gates(m) if g.name in CALIBRATION_PENDING}


# ============================================================================ tests
def test_binomial_bounds():
    """The relaxation rule: exact binomial quantiles (checked against hand values)."""
    assert binom_lower(5, 0.95) == 4 and binom_lower(30, 0.95) == 26 and binom_lower(30, 0.9) == 23
    assert binom_upper(65, 0.02) == 4 and binom_upper(30, 0.3) == 14 and binom_upper(5, 0.0) == 0
    assert rate_at_least(26, 30, 0.95) and not rate_at_least(25, 30, 0.95)
    assert rate_at_most(4, 65, 0.02) and not rate_at_most(5, 65, 0.02)
    assert not rate_at_least(0, 0, 0.5) and binom_lower(10, 1.0) == 10 and binom_lower(10, 0.0) == 0
    assert chi2_halfwidth(625) == pytest.approx(0.1109, abs=1e-3)


def test_matrix_covers_every_design_row():
    """Every DESIGN 7.4 row is a FAULT_MATRIX row, every FAULT_MATRIX row has a runner and at least one
    'design' gate, and every pending gate exists and is documented (docs/RESULTS.md, DESIGN 7.4 note)."""
    design = (REPO / "docs" / "DESIGN.md").read_text()
    rows = faults.design_fault_rows(design)
    assert len(rows) == 11 and set(rows) == {r["design_row"] for r in faults.FAULT_MATRIX}
    names = {t[0] + (":" + str(sorted(t[2].items())) if t[2] else "") for t in matrix_tasks([0])}
    assert len(names) >= len(faults.FAULT_MATRIX)
    # a synthetic 'everything fails' matrix is not needed to list the gates: evaluate on the fast seeds lazily
    gate_rows = _GATE_ROWS
    for r in faults.FAULT_MATRIX:
        assert r["name"] in gate_rows, r["name"]
    results = (REPO / "docs" / "RESULTS.md").read_text()
    for name in list(CALIBRATION_PENDING) + list(OPEN_HONESTY_VIOLATIONS):
        assert name.split(".")[0] in gate_rows | {"exif_unobservable"}
        assert f"`{name}`" in results, f"{name} is calibration-pending but not listed in docs/RESULTS.md"
    assert "calibration-pending" in design[design.index("### 7.4"):design.index("### 7.5")]


#: rows that :func:`gates` covers (kept in sync by test_fault_matrix_fast_subset, which checks it on real data)
_GATE_ROWS = {"mirror", "orientation_unbaked", "exif_crop", "exif_missing", "selfie_near", "jaw_open", "smile",
              "beauty_warp", "off_axis_stereographic", "off_axis_rectilinear", "beard", "glasses", "hair",
              "small_face", "gross_outliers", "definition_bias"}


def test_fault_matrix_fast_subset():
    """Per-push run: every FAULT_MATRIX row on 5 seeds through the pipeline (solve / observe; fit for the
    clean surface sets), against the clean runs of the same seeds.  Every gate that is not
    calibration-pending passes under the binomial 95 % rule; honesty and floor gates pass without
    exception, apart from the documented open release blockers (which must still be failing)."""
    m = evaluate(FAST_SEEDS, frontal=False, fast=True)
    G = gates(m, relax_continuous=True)
    assert {g.row for g in G if g.kind == "design"} >= _GATE_ROWS
    assert failed_gates(G) == []
    for name in OPEN_HONESTY_VIOLATIONS:
        g = next(g for g in G if g.name == name)
        assert g.kind == "honesty" and not g.ok, f"{name} no longer fails: remove it from OPEN_HONESTY_VIOLATIONS"
    assert m["clean"]["tiers"] == {"B": len(FAST_SEEDS)}        # no metric scale reference: never above B (H4)
    assert m["clean"]["deflate"] == {"True": len(FAST_SEEDS)}   # FU-02 option (i) is what the pipeline ships


def test_open_honesty_violations_are_documented():
    """A failing honesty gate is a release blocker (H12): it must be named as one in docs/RESULTS.md and
    under the DESIGN 7.4 table, and it can never be listed as merely calibration-pending."""
    results = (REPO / "docs" / "RESULTS.md").read_text()
    design = (REPO / "docs" / "DESIGN.md").read_text()
    sec74 = design[design.index("### 7.4"):design.index("### 7.5")]
    assert not set(OPEN_HONESTY_VIOLATIONS) & set(CALIBRATION_PENDING)
    for name in OPEN_HONESTY_VIOLATIONS:
        assert f"`{name}`" in results and f"`{name}`" in sec74, name
    assert "release blocker" in results.lower() and "release blocker" in sec74.lower()


def test_release_run_requires_point_estimates():
    """Regression (WP-23 review): the binomial relaxation belongs to the 5-seed subset only.  In the
    release run a design rate gate must meet its target as a point estimate: 26/30 against 'TPR >= 0.95'
    and 9/85 against '<= 0.05' are inside the binomial 95 % bounds but fail."""
    ok, met = _ge(26, 30, 0.95)
    assert ok and not met
    g = Gate("row.tpr", "row", "design", "TPR >= 0.95", "26/30", ok, met)
    assert failed_gates([g], strict=False, pending={}) == []
    assert len(failed_gates([g], strict=True, pending={})) == 1
    ok, met = _le(9, 85, 0.05)
    assert ok and not met
    g2 = Gate("x.rate", "x", "design", "<= 0.05", "9/85", ok, met)
    assert failed_gates([g2], strict=False, pending={}) == [] and len(failed_gates([g2], strict=True, pending={})) == 1
    # a pending gate is excused in both modes; a honesty gate never through the pending list
    assert failed_gates([g], strict=True, pending={"row.tpr": "why"}) == []
    h = Gate("row.honest", "row", "honesty", "t", "m", False, False)
    assert len(failed_gates([h], strict=False, pending={"row.honest": "why"})) == 1
    assert status_of(g, pending={}, strict=True) == "FAIL" and status_of(g, pending={}, strict=False) == "pass"


def test_gate_measures_the_reported_sigma_rep():
    """Regression (WP-23 review): the honesty gates must be computed from the sigma_rep the pipeline
    reports.  :func:`honesty_of` rebuilds the full covariance from the observe stage's own Sigma1, bias
    form, calibration chi2_red / gamma and factor and requires its diagonal to equal
    ``observe['sigma_rep_mm']``^2; a fault in how the stage produces sigma_rep (here: reported sigmas
    halved, i.e. 2 x over-confident) is therefore caught instead of being invisible."""
    sc = make_scene(FAST_SEEDS[0], detector=dict(BASE_DETECTOR))
    run = run_scene(sc, "observe")
    s, ob = run.outputs["solve"], run.outputs["observe"]
    n = len(sc.X)
    h = honesty_of(s["_result"], ob, sc.X, n)
    assert h["n_z"] > 100 and np.isfinite(h["nees"])
    C = reported_cov_of(s["_result"], ob)
    assert np.allclose(np.sqrt(np.diag(C)), np.asarray(ob["sigma_rep_mm"], float).reshape(-1), rtol=1e-9)
    assert ob["deflate"] is True and ob["inflation"] < 1.0      # clean studio set: the FU-02 factor is active
    bad = dict(ob)
    bad["sigma_rep_mm"] = 0.5 * np.asarray(ob["sigma_rep_mm"], float)
    with pytest.raises(AssertionError, match="sigma_rep_mm"):
        honesty_of(s["_result"], bad, sc.X, n)
    # and the reported numbers respond to the factor: the DESIGN factor gives a larger covariance
    Cd = reported_cov_of(s["_result"], ob, deflate=False)
    assert np.all(np.diag(Cd) >= np.diag(C) - 1e-12) and np.diag(Cd).sum() > np.diag(C).sum()


def test_q_small_fires_on_every_150px_face():
    """Regression for the deterministic Q-SMALL miss of WP-23 (seed 2313, view 3: a face 150 px wide but
    ~246 px tall at 45 deg yaw escaped while the stage measured max(width, height) of the landmark box).
    FU-03: the landmarks stage measures the pose-independent face width (``stages.face_width_px``)."""
    rec = collect([("small", 2313, {})])[0]
    missed = [v for v in range(rec["n_photos"]) if not _has(rec, "p%02d" % (v + 1), "Q-SMALL")]
    assert missed == []


def test_face_width_is_pose_independent():
    """``stages.face_width_px``: the same head at the same distance reads the same width from the front,
    at 45 deg and in profile (within 6 %: perspective and hidden points), while the landmark-box extents
    change by far more; a frontal face reads its landmark-box width."""
    from face3d.synthetic import orbit_camera
    k = kit()
    X = np.asarray(S.FactorPrior.from_package().mean(), float)
    tgt = tuple(float(x) for x in face_centre(k))
    widths, boxes = [], []
    for yaw in (0.0, 45.0, 90.0, -90.0):
        cam = orbit_camera(2000.0, yaw, 5.0, 85.0, width=W, height=H, target=tgt)
        uv = cam.project(X)
        widths.append(S.face_width_px(uv, X))
        boxes.append(np.ptp(uv, axis=0))
    assert max(widths) / min(widths) < 1.06, widths
    assert widths[0] == pytest.approx(boxes[0][0], rel=0.05)              # frontal: the landmark-box width
    assert boxes[2][0] / boxes[0][0] > 1.25 and boxes[0][1] / boxes[0][0] > 1.3   # what the box would say
    # too few points, or a degenerate (collinear) configuration: no width (the stage falls back to the box)
    few = np.full_like(uv, np.nan)
    few[:3] = uv[:3]
    assert S.face_width_px(few, X) is None
    line = np.column_stack([np.linspace(-50.0, 50.0, 10), np.zeros(10), np.zeros(10)])
    assert S.face_width_px(line[:, :2] + 100.0, line) is None
    # a gross outlier does not set the scale
    bad = cam.project(X).copy()
    bad[5] += 400.0
    assert S.face_width_px(bad, X) == pytest.approx(widths[-1], rel=0.03)


def test_focal_label_is_earned_from_the_photos():
    """The FU-03 release blocker (H5 / H12), on the per-push seeds: with an EXIF focal that is wrong by
    +/-30 % no view is labelled focal 'measured' (the solved focal is ~28 % off and the photos cannot say
    otherwise at this range), every such set carries C-FOCAL-PRIOR, and the clean studio sets (correct
    EXIF) read 'prior_used' with an *info* C-FOCAL-PRIOR, never a warn / block alarm."""
    crop = collect([("exif", s, {"kind": "exif_crop"}) for s in FAST_SEEDS])
    for r in crop:
        assert "measured" not in r["focal_statuses"] and _median(r["focal_rel_err"]) > 0.15
        assert "C-FOCAL-PRIOR" in r["flags"]
        assert all(t is not None and not t["overruled"] for t in r["focal_test"])   # tested, EXIF kept
    clean = collect([("clean", s, CLEAN) for s in FAST_SEEDS])
    for r in clean:
        assert set(r["focal_statuses"]) == {"prior_used"} and "C-FOCAL-PRIOR" in r["flags"]
        sev = {f[2] for f in r["findings"] if f[1] == "C-FOCAL-PRIOR"}
        assert sev == {"info"}
        assert not any(f[1] == "C-FOCAL-EXIF" for f in r["findings"]) and not _overruled(r)


def test_exif_overruled_when_the_photos_carry_the_information():
    """The robust EXIF prior (FU-03 task 2) on a near-range set (0.30-0.35 m, 5 views over 120 deg), where
    the photos alone give sigma(ln f) ~0.1: an EXIF focal that is 30 % too short is contradicted (|t| > 2.58),
    the ladder prior without it is adopted, C-FOCAL-EXIF (warn, ask) and the flag C-EXIF-OVERRULED are
    raised and the focal error drops; a correct EXIF on the same photos is kept.  After an overrule the
    focal is never labelled 'measured' (conflicting evidence: 'partial').  Detection rates over 30 seeds
    are in docs/RESULTS.md 3.2 (this is one seed)."""
    seed = FAST_SEEDS[0]
    good, short = collect([("exif_near", seed, {"factor": 1.0}), ("exif_near", seed, {"factor": 0.7})])
    assert not _overruled(good) and not any(f[1] == "C-FOCAL-EXIF" for f in good["findings"])
    assert good["focal_test"][0]["sigma_logf_data"] < 0.25 and abs(good["focal_test"][0]["t"]) < 2.576
    assert _median(good["focal_rel_err"]) < 0.06
    t = short["focal_test"][0]
    assert t["contradicted"] and t["overruled"] and abs(t["t"]) > 2.576 and abs(t["rel"]) > 0.15
    assert t["exif_source"] == "exif_f35" and set(short["focal_source"]) == {"phone"}
    assert "C-EXIF-OVERRULED" in short["solve_flags"]
    cards = [f for f in short["findings"] if f[1] == "C-FOCAL-EXIF"]
    assert len(cards) == short["n_photos"] and {f[2] for f in cards} == {"warn"}
    assert _median(short["focal_rel_err"]) < 0.25           # 0.30 with the EXIF prior kept
    # H5 after the overrule: a focal with contradicting evidence is not claimed as measured
    assert set(short["focal_statuses"]) == {"partial"}
    # ... and a focal that is the EXIF's is 'prior_used' even where the photos could measure it
    assert set(good["focal_statuses"]) <= {"prior_used", "measured"}
    assert all(st != "measured" or e < 0.15 for st, e in zip(good["focal_statuses"], good["focal_rel_err"]))


def test_alarm_budget_20_clean_sets():
    """DESIGN 7.4 alarm budget on 20 clean photo sets (100 photos): <= 1 spurious warn/block finding per 10
    clean photos.  The 5 fast seeds run to ``observe``; 15 more sets run to ``solve`` (every QA finding is
    raised by then: triage, landmark-stage and post-solve Q-NEAR)."""
    full = collect([("clean", s, CLEAN) for s in FAST_SEEDS])
    more = collect([("clean", s, {"until": "solve"}) for s in range(FAST_SEEDS[-1] + 1, FAST_SEEDS[0] + 20)])
    recs = full + more
    assert len(recs) == 20
    photos = sum(r["n_photos"] for r in recs)
    spurious = [f for r in recs for f in r["findings"] if f[2] in faults.ALARM_BUDGET["severities"]]
    assert photos == 100
    assert len(spurious) <= faults.ALARM_BUDGET["max_spurious_findings_per_photo"] * photos, _count(
        [f[1] for f in spurious])
    # and no decision card that asks for an action on a clean photo
    assert not any(d == "suggest_flip" for r in recs for d in r["mirror"])
    assert not any(t == "expressive" for r in recs for t in r["tags"])


@pytest.mark.slow
def test_fault_matrix_release_run():
    """Release run (>= 30 seeds, DESIGN 7.5): same gates, no relaxation at all: continuous bands as
    written and every rate gate on its point estimate (``strict``).  Every failing design gate must be
    calibration-pending and every failing honesty gate a listed open release blocker (both documented in
    docs/RESULTS.md, checked by the per-push tests), and every listed gate must still be failing."""
    m = evaluate(SLOW_SEEDS)
    assert m["n_seeds"] >= 30 and m["alarm"]["n_sets"] >= 20
    G = gates(m)
    assert failed_gates(G, strict=True) == []
    stale = stale_gates(G)
    assert stale == [], f"these gates now pass: remove them from the pending lists and update RESULTS.md: {stale}"
    assert {g.name for g in G} >= set(CALIBRATION_PENDING) | set(OPEN_HONESTY_VIOLATIONS)


if __name__ == "__main__":      # regenerate the fault-matrix table of docs/RESULTS.md
    import sys
    _m = evaluate(SLOW_SEEDS, diagnostics="--diagnostics" in sys.argv)
    print(report(_m, strict=True))
    print(json.dumps(_m, indent=1, sort_keys=True))
