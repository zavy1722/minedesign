"""Observability, evidence at prior weight 1, coverage rules, LOVO gamma, sigma_rep, gates and tiers.

Implements DESIGN D-16 (claims at prior weight 1), D-17 (tiers), D-18 (shrinkage gate),
4.6 "Prior share" / likeness mode, 4.12 (focal status, evidence, coverage rules, region
status, tiers), 4.13 (sigma_rep, LOVO gamma, shrinkage and plausibility) and the honesty
contract H1-H9 of DESIGN section 5 (WBS WP-16).  The claims ledger built from these
outputs lives in :mod:`face3d.fit.ledger`; the next-best photo in :mod:`face3d.solve.nbv`.

Conventions
-----------
* Points: (N, 3) float64 millimetres in the template head frame (+x subject's left, +y up,
  +z out of the face; DESIGN 3.1).  Flattened vectors and 3N x 3N covariances are
  **point-major** (coordinate ``3 i + a``, a = 0, 1, 2 for x, y, z), as in
  :mod:`face3d.eval.align` and ``BundleResult.cov``.
* A *region index* maps a region name to an int array of coordinate indices (3 i + a).
  Most regions take all three coordinates of their landmarks; the projection regions take
  only the depth (z) coordinates (see :func:`default_region_index`).
* *Gauge projection*: P = I - U U^T with U an orthonormal basis of the 7-DoF similarity
  tangent at the estimate (:func:`face3d.eval.align.gauge_projector`; DESIGN 4.12, 7.3).
  Evidence, prior shares and the next-best photo compare covariances only on the shape
  subspace, so the gauge the solver picked (template gauge, DESIGN D-20) never counts as
  "measured".
* Angles in degrees; yaw > 0 puts the camera on the subject's left (``atan2(C_x, C_z)``
  of the camera centre C, as :func:`face3d.synthetic.orbit_camera` and
  ``BundleResult.view_stats``); pitch > 0 puts the camera above the head
  (``asin(C_y / |C|)``).
* Status vocabulary (DESIGN D-16, shared with :mod:`face3d.fit.symmetry`):
  ``'measured'``, ``'constrained'``, ``'prior-driven'``, ``'unobserved'``.
  Focal status: ``'measured'``, ``'partial'``, ``'prior_used'``.
* Prior weight 1 (H2): labels of a likeness-mode (widened-prior) solve are those of the
  standard solve of the same photos (``assess(widened, standard_result=standard)``), so
  they are identical by construction; widened results carry :data:`FLAG_LIKENESS` and
  are refused without it.  Tiers and coverage count only views with evidence (frozen
  views are left out, D-17).

Numeric defaults
----------------
Every threshold is a registered default (namespace ``observability``,
:mod:`face3d.core.config`) with its badge and source; almost all are 🧠/🆕 and
PROVISIONAL until the M7 calibration (DESIGN 8, risk 1).  Sources:

* focal 'measured' if sigma_post(ln f) < 0.10: DESIGN 4.12 / H5 (bl C2) 🧠;
  'prior used' if sigma_post > 0.8 sigma_prior: DESIGN 4.12 (rec CAM-7) 🧠;
  P = 100 mm / z: rec CAM-7 🧠.
* evidence k >= 0.8 measured, >= 0.5 constrained: DESIGN 4.12 ([Rob 3.10]) 🆕.
* coverage: depth needs two views >= 30 deg apart (bl C7) 🧠; projection a view with
  |yaw| < 15 deg plus one with |yaw| >= 60 deg (com R5.9; 15 deg = WBS WP-16) 🧠; jaw
  underside a view with pitch <= -15 deg (DESIGN 4.12) 🧠; ears |yaw| >= 30 deg and pitch
  fixed by >= 2 views (com R3.3 and the "unsolved pitch" row of the community digest) 🧠,
  "distinct pitch" meaning >= 5 deg apart (🆕 this WP); a view "sees" a region when it
  observes at least half of the region's points (🆕 this WP).
* region targets (mm): rec EV-3 and *benchmarks-metrics* ``acceptance_targets`` 🧠 (design
  defaults, not measured norms); chin and chin projection 1.5 mm are the WBS values (the
  research table groups jaw_chin at 2.0 mm).
* LOVO: >= 3 views, <= 10 warm-started iterations, flag held-out RMS > 2 x in-sample:
  DESIGN 4.13 🆕.
* shrinkage gate alpha_lo 0.01 (z = -2.326), alpha_hi 0.001 (z = 3.090): DESIGN D-18,
  4.13 🔢 (Wilson-Hilferty calibration checked in tests/test_observability.py).
* likeness mode: prior share <= 0.2 where >= 2 views see the point (DESIGN 4.6, anat R1.4)
  🧠; widening factor 1.5 per round, <= 5 rounds (🆕 this WP).
* tiers: S needs >= 5 views and focal measured or EXIF sigma <= 0.04 (DESIGN 4.2 'EXIF
  f35, uncropped'); A >= 3 views with max |yaw| >= 45 deg; C one photo, all |yaw| < 20 deg
  or all selfies: DESIGN 4.12 / D-17 🧠.

numpy + stdlib only; deterministic.
"""
from __future__ import annotations

import math
from dataclasses import replace
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from ..core.config import Default, register_defaults
from ..eval.align import gauge_projector
from .robust import norm_ppf

__all__ = [
    "OBS", "REGION_TARGET_MM", "REGION_ORDER", "REGION_COVERAGE_RULES", "STATUSES", "TIER_NAMES",
    "FLAG_L_HELDOUT", "FLAG_L_TOO_FEW_VIEWS", "FINDING_PULLED", "FINDING_IMPLAUSIBLE", "FLAG_LIKENESS",
    "default_region_index", "region_points", "camera_status", "focal_prior_log_sigmas", "frozen_parameters",
    "posterior_at_prior_weight_one", "prior_covariance", "shape_prior_info", "standard_prior_info",
    "region_evidence", "coverage_rules", "coverage_ok", "region_sigma_rep", "region_status",
    "lovo_gamma", "make_solve_without", "bias_gain", "reported_covariance", "sigma_rep", "shrinkage_gate",
    "legacy_shrinkage_gate",
    "shape_prior_cov", "prior_shares", "widen_prior", "likeness_mode_prior", "tier", "assess",
]

_BRAIN = "\U0001F9E0"   # expert knowledge, provisional
_NEW = "\U0001F195"     # introduced by this design / WP, uncalibrated
_NUM = "\U0001F522"     # checked numerically

# =========================================================================== defaults
_TARGETS: tuple[tuple[str, float, str], ...] = (
    ("eyes", 1.0, "rec EV-3; benchmarks-metrics acceptance_targets eyes_lids_canthi 1.0 mm"),
    ("lips", 1.0, "rec EV-3; benchmarks-metrics acceptance_targets lips_perioral 1.0 mm"),
    ("brows", 1.2, "benchmarks-metrics acceptance_targets brows_supraorbital 1.2 mm"),
    ("nose", 1.2, "rec EV-3; benchmarks-metrics acceptance_targets nose 1.2 mm"),
    ("nose_projection", 1.5, "benchmarks-metrics acceptance_targets nose_projection 1.5 mm"),
    ("forehead", 1.5, "rec EV-3; benchmarks-metrics acceptance_targets forehead_cheeks 1.5 mm"),
    ("cheeks", 1.5, "rec EV-3; benchmarks-metrics acceptance_targets forehead_cheeks 1.5 mm"),
    ("chin", 1.5, "WBS WP-16 (stricter than benchmarks-metrics jaw_chin 2.0 mm)"),
    ("chin_projection", 1.5, "WBS WP-16 (as nose projection; benchmarks-metrics has no chin-projection row)"),
    ("jaw", 2.0, "rec EV-3; benchmarks-metrics acceptance_targets jaw_chin 2.0 mm"),
    ("ears", 3.0, "rec EV-3; benchmarks-metrics acceptance_targets ears_cranium 3.0 mm"),
    ("cranium", 3.0, "benchmarks-metrics acceptance_targets ears_cranium 3.0 mm"),
)

OBS = register_defaults("observability", {
    "focal_measured_sigma_log": Default(0.10, _BRAIN, "DESIGN 4.12 / H5: focal measured if sigma_post(ln f) < 0.10 "
                                        "(bl C2)", "ln f", (0.0, None)),
    "focal_prior_used_ratio": Default(0.8, _BRAIN, "DESIGN 4.12: 'prior used' if sigma_post > 0.8 sigma_prior "
                                      "(rec CAM-7)", "", (0.0, 1.0)),
    "perspective_ref_mm": Default(100.0, _BRAIN, "rec CAM-7: report P = 100 mm / z", "mm", (1e-9, None)),
    "evidence_measured_k": Default(0.8, _NEW, "DESIGN 4.12 / D-16: measured needs k >= 0.8 ([Rob 3.10])", "",
                                   (0.0, 1.0)),
    "evidence_constrained_k": Default(0.5, _NEW, "DESIGN 4.12: constrained 0.5 <= k < 0.8 ([Rob 3.10])", "",
                                      (0.0, 1.0)),
    "depth_min_sep_deg": Default(30.0, _BRAIN, "DESIGN 4.12: depth needs 2 views >= 30 deg apart in yaw (bl C7)",
                                 "deg", (0.0, 180.0)),
    "projection_front_max_yaw_deg": Default(15.0, _BRAIN, "WBS WP-16 / DESIGN 4.12: projection needs a front view "
                                            "(|yaw| < 15 deg; com R5.9)", "deg", (0.0, 90.0)),
    "projection_side_min_yaw_deg": Default(60.0, _BRAIN, "DESIGN 4.12: projection needs a view at |yaw| >= 60 deg "
                                           "(com R5.9)", "deg", (0.0, 180.0)),
    "jaw_underside_max_pitch_deg": Default(-15.0, _BRAIN, "DESIGN 4.12: jaw underside needs a view with pitch "
                                           "<= -15 deg", "deg", (-90.0, 90.0)),
    "ears_min_yaw_deg": Default(30.0, _BRAIN, "DESIGN 4.12: ears need |yaw| >= 30 deg (com R3.3)", "deg",
                                (0.0, 180.0)),
    "ears_pitch_sep_deg": Default(5.0, _NEW, "WP-16: 'pitch fixed by >= 2 views' read as two ear-seeing views "
                                  ">= 5 deg apart in pitch (com R3.3, 'unsolved pitch')", "deg", (0.0, 90.0)),
    "region_seen_frac": Default(0.5, _NEW, "WP-16: a view sees a region when it observes >= half of its points",
                                "", (0.0, 1.0)),
    "lovo_min_views": Default(3, _NEW, "DESIGN 4.13: LOVO gamma needs >= 3 views", "", (2, None)),
    "lovo_max_iter": Default(10, _NEW, "DESIGN 4.13: warm-started LOVO re-solves, <= 10 iterations", "",
                             (1, None)),
    "lovo_heldout_ratio_flag": Default(2.0, _NEW, "DESIGN 4.13: flag LOVO error > 2 x in-sample (L-HELDOUT)", "",
                                       (1.0, None)),
    "shrink_alpha_lo": Default(0.01, _NUM, "DESIGN D-18 / 4.13: pulled toward average if T < q(z = -2.326)", "",
                               (1e-12, 0.5)),
    "shrink_alpha_hi": Default(0.001, _NUM, "DESIGN D-18 / 4.13: implausible if T > q(z = 3.090)", "",
                               (1e-12, 0.5)),
    "likeness_max_share": Default(0.2, _BRAIN, "DESIGN 4.6: likeness mode widens kappa until p_i <= 0.2 "
                                  "(anat R1.4)", "", (1e-6, 1.0)),
    "likeness_factor": Default(1.5, _NEW, "WP-16: kappa multiplier per likeness round", "", (1.0 + 1e-9, None)),
    "likeness_max_iter": Default(5, _NEW, "WP-16: at most 5 likeness rounds", "", (1, None)),
    "likeness_min_views": Default(2, _BRAIN, "DESIGN 4.6: widen only where >= 2 views see the point (anat R1.4)",
                                  "", (1, None)),
    "tier_s_min_views": Default(5, _BRAIN, "DESIGN 4.12: tier S needs >= 5 views", "", (1, None)),
    "tier_s_exif_sigma_log": Default(0.04, _BRAIN, "DESIGN 4.2 / WBS WP-16: EXIF prior sigma <= 0.04 confirms "
                                     "focal for tier S", "ln f", (0.0, None)),
    "tier_a_min_views": Default(3, _BRAIN, "DESIGN 4.12: tier A needs >= 3 views", "", (1, None)),
    "tier_a_min_yaw_deg": Default(45.0, _BRAIN, "DESIGN 4.12: tier A needs one view at |yaw| >= 45 deg", "deg",
                                  (0.0, 180.0)),
    "ears_shape_prior_driven": Default(True, _BRAIN, "DESIGN D-31 / 10: ears are silhouette-only and labelled "
                                       "prior-driven until hinged ears with CC0 ear keys land (after M7)", "", None),
    "tier_c_max_yaw_deg": Default(20.0, _BRAIN, "DESIGN 4.12: tier C when all views are within |yaw| < 20 deg "
                                  "(com R5.9)", "deg", (0.0, 180.0)),
    **{f"target_{name}_mm": Default(val, _BRAIN, f"DESIGN 4.12 region target; {src}", "mm", (1e-9, None))
       for name, val, src in _TARGETS},
})

#: Region targets in mm (DESIGN 4.12, rec EV-3 🧠; registered as ``observability.target_<region>_mm``).
REGION_TARGET_MM: dict[str, float] = {name: float(OBS[f"target_{name}_mm"].value) for name, _, _ in _TARGETS}

#: Report order of the regions (DESIGN 4.12 targets; WBS WP-16).
REGION_ORDER: tuple[str, ...] = ("eyes", "brows", "lips", "nose", "nose_projection", "cheeks", "forehead",
                                 "chin", "chin_projection", "jaw", "ears", "cranium")

#: Hard coverage rules each region needs for 'measured' (DESIGN 4.12 'Coverage rules'):
#: depth everywhere (bl C7: every 3D claim needs two views >= 30 deg apart), the
#: front + |yaw| >= 60 deg pair for the projection regions (com R5.9), the low view for the
#: jaw underside and the ear rule for ears.  The rule-to-region mapping is this WP's
#: reading of DESIGN 4.12 (🆕).
REGION_COVERAGE_RULES: dict[str, tuple[str, ...]] = {
    "eyes": ("depth",), "brows": ("depth",), "lips": ("depth",), "nose": ("depth",),
    "nose_projection": ("depth", "projection"), "cheeks": ("depth",), "forehead": ("depth",),
    "chin": ("depth",), "chin_projection": ("depth", "projection"), "jaw": ("depth", "jaw_underside"),
    "ears": ("depth", "ears"), "cranium": ("depth",),
}

STATUSES: tuple[str, ...] = ("measured", "constrained", "prior-driven", "unobserved")
_STATUS_RANK = {s: i for i, s in enumerate(STATUSES)}

#: Tier codes and names (DESIGN D-17, 4.12).
TIER_NAMES: dict[str, str] = {"S": "metric", "A": "iris-scaled", "B": "proportions only", "C": "blockout"}

#: LOVO findings (DESIGN 4.13).
FLAG_L_HELDOUT = "L-HELDOUT"
FLAG_L_TOO_FEW_VIEWS = "L-TOO-FEW-VIEWS"
#: Shrinkage / plausibility findings (DESIGN D-18, 4.13).
FINDING_PULLED = "P-PULLED-TO-AVERAGE"
FINDING_IMPLAUSIBLE = "P-IMPLAUSIBLE"
#: Added to ``result.flags`` of a solve made with a likeness-mode (widened) prior
#: (:func:`likeness_mode_prior`); :func:`assess` then requires the standard solve (H2).
FLAG_LIKENESS = "LIKENESS-MODE"


def _d(key: str) -> Any:
    return OBS[key].value


# =========================================================================== regions
# Regions of the 44 anatomical landmarks: face3d.model.registry ('eyes', 'nose', 'lips',
# 'chin', 'jaw', 'cheeks', 'forehead', 'ears', 'cranium').  The anatomical set has no brow
# points.  Projection regions (🆕 this WP, depth coordinates only):
#   nose_projection = z of prn, sn, ac_L, ac_R: tip projection measured from the alar
#     crease (Goode; research/anatomy/nose.md Table 2 and 'Projection ratios disagree by
#     baseline'); the base points keep the region relative to the face, not to the frame.
#   chin_projection = z of pg, gn, sl: soft-tissue chin projection relative to the
#     labiomental fold (research/anatomy/jaw-chin-neck.md 'Projection references').
_PROJECTION_BASES: dict[str, tuple[str, ...]] = {"nose_projection": ("prn", "sn", "ac"),
                                                 "chin_projection": ("pg", "gn", "sl")}

# The legacy illustrative landmark names of face3d.synthetic (not anatomical data; their
# regions follow the same anatomy as the registry).
_LEGACY_REGION: dict[str, str] = {
    "endocanthion": "eyes", "exocanthion": "eyes", "pupil": "eyes",
    "brow_inner": "brows", "brow_outer": "brows",
    "nasion": "nose", "pronasale": "nose", "subnasale": "nose", "alare": "nose",
    "labrale_superius": "lips", "stomion": "lips", "labrale_inferius": "lips", "cheilion": "lips",
    "pogonion": "chin", "menton": "chin", "gonion": "jaw", "zygion": "cheeks",
    "glabella": "forehead", "forehead_side": "forehead", "tragion": "ears", "vertex_front": "cranium",
}
_LEGACY_PROJECTION: dict[str, tuple[str, ...]] = {"nose_projection": ("pronasale", "subnasale"),
                                                  "chin_projection": ("pogonion", "menton")}


def _base(name: str) -> str:
    return name[:-2] if name.endswith(("_L", "_R")) else name


def default_region_index(ids: Sequence[str]) -> dict[str, np.ndarray]:
    """Region name -> coordinate indices (3 i + a) for landmark ``ids``.

    Anatomical ids (``face3d.model.registry.ANATOMICAL``) use the registry region of each
    landmark (all three coordinates); legacy :mod:`face3d.synthetic` names use the same
    anatomy (``brow_*`` -> brows).  The projection regions take only z (see the module
    notes above: nose_projection = z of prn, sn, ac; chin_projection = z of pg, gn, sl).
    Unknown names belong to no region.  Regions without points are omitted; the order
    follows :data:`REGION_ORDER`.
    """
    from ..model.registry import ANATOMICAL
    ids = [str(i) for i in ids]
    members: dict[str, list[int]] = {r: [] for r in REGION_ORDER}
    for i, lid in enumerate(ids):
        if lid in ANATOMICAL:
            reg = ANATOMICAL[lid].region
            members.setdefault(reg, []).extend([3 * i, 3 * i + 1, 3 * i + 2])
            for pr, bases in _PROJECTION_BASES.items():
                if ANATOMICAL[lid].base in bases:
                    members[pr].append(3 * i + 2)
        else:
            b = _base(lid)
            reg = _LEGACY_REGION.get(b)
            if reg is not None:
                members[reg].extend([3 * i, 3 * i + 1, 3 * i + 2])
            for pr, bases in _LEGACY_PROJECTION.items():
                if b in bases:
                    members[pr].append(3 * i + 2)
    order = list(REGION_ORDER) + [r for r in members if r not in REGION_ORDER]
    return {r: np.array(sorted(members[r]), dtype=np.int64) for r in order if members.get(r)}


def region_points(region_index: Mapping[str, Any]) -> dict[str, np.ndarray]:
    """Region name -> sorted unique point indices (coordinate index // 3)."""
    return {r: np.unique(np.asarray(c, np.int64) // 3) for r, c in region_index.items()}


# =========================================================================== cameras
def camera_status(view_stats: Sequence[Mapping[str, Any]], prior_log_sigma: Any,
                  cameras: Sequence[Any] | None = None) -> list[dict]:
    """Per-view focal and distance observability (DESIGN 4.12, H5; rec CAM-7).

    ``view_stats``: ``BundleResult.view_stats`` (``sigma_logf``, ``sigma_logz``).
    ``prior_log_sigma``: the focal prior's sigma in ln f, scalar or one per view (None =
    unknown; ``inf`` = no focal prior; see :func:`focal_prior_log_sigmas`).  ``cameras``:
    optional solved cameras, for P = 100 mm / z with z the distance from the camera centre
    to the head-frame origin (mm).

    Returns per view ``{'sigma_logf', 'sigma_logz', 'P', 'focal_status',
    'prior_dominated'}`` with focal_status, in the order of WBS WP-16 / DESIGN 4.12:

    * ``'measured'`` if sigma_logf < 0.10 (bl C2, H5; a known focal, sigma_logf 0, too),
    * else ``'prior_used'`` if sigma_logf > 0.8 sigma_prior (CAM-7: the data did not shrink
      the prior by 20 %),
    * else ``'partial'``.

    Conservative cases (H5 'otherwise from prior'): a frozen view (sigma_logf None) and an
    unknown prior (``prior_log_sigma`` None) with sigma_logf >= 0.10 read ``'prior_used'``,
    never 'partial'.  ``prior_dominated`` records the CAM-7 test on its own (True when
    sigma_logf > 0.8 sigma_prior, e.g. a 'measured' focal that merely echoes a tight EXIF
    prior; None when the prior or the posterior is unknown), for reports that want to say
    so; tier S accepts EXIF sigma <= 0.04 separately (:func:`tier`).
    """
    V = len(view_stats)
    if prior_log_sigma is None or np.ndim(prior_log_sigma) == 0:
        ps = [prior_log_sigma] * V
    else:
        ps = list(prior_log_sigma)
        if len(ps) != V:
            raise ValueError(f"prior_log_sigma has {len(ps)} entries for {V} views")
    if cameras is not None and len(cameras) != V:
        raise ValueError(f"cameras has {len(cameras)} entries for {V} views")
    thr = float(_d("focal_measured_sigma_log"))
    ratio = float(_d("focal_prior_used_ratio"))
    ref = float(_d("perspective_ref_mm"))
    out = []
    for k, st in enumerate(view_stats):
        sf = st.get("sigma_logf")
        sz = st.get("sigma_logz")
        p = ps[k]
        known = sf is not None and bool(np.isfinite(sf))
        dominated = None if (not known or p is None) else bool(float(sf) > ratio * float(p))
        if not known:
            status = "prior_used"                      # frozen view: held, not estimated
        elif float(sf) < thr:
            status = "measured"
        elif p is None or dominated:
            status = "prior_used"                      # unknown prior: conservative (H5)
        else:
            status = "partial"
        P = None
        if cameras is not None:
            z = float(np.linalg.norm(np.asarray(cameras[k].center, float)))
            P = ref / z if z > 0 else None
        out.append({"sigma_logf": None if sf is None else float(sf), "sigma_logz": None if sz is None else float(sz),
                    "P": P, "focal_status": status, "prior_dominated": dominated})
    return out


def focal_prior_log_sigmas(views: Sequence[Any]) -> list[float]:
    """Per-view focal prior sigma in ln f as the bundle applies it (DESIGN 4.2), for
    :func:`camera_status` / :func:`assess`.

    ``views``: the ``ViewObs`` (``f_prior``, ``f_prior_log_sigma``, ``focal_group``) or
    ``PhotoLandmarks`` (``resolved_focal_prior()``) of the solve.  A focal group carries the
    tightest prior of its views (as :class:`face3d.solve.bundle` builds it); a view
    without any focal prior gets ``inf`` (its focal is data-determined).
    """
    fp: list[tuple[float | None, float]] = []
    for v in views:
        if hasattr(v, "resolved_focal_prior"):
            f, sg = v.resolved_focal_prior()
        else:
            f, sg = getattr(v, "f_prior", None), getattr(v, "f_prior_log_sigma", None)
        fp.append((f, float("inf") if sg is None else float(sg)))
    groups: dict[Any, float] = {}
    for v, (f, sg) in zip(views, fp):
        g = getattr(v, "focal_group", None)
        if g is not None and f is not None:
            groups[g] = min(groups.get(g, float("inf")), sg)
    out = []
    for v, (f, sg) in zip(views, fp):
        g = getattr(v, "focal_group", None)
        if g is not None:
            out.append(groups.get(g, float("inf")))
        else:
            out.append(sg if f is not None else float("inf"))
    return out


# =========================================================================== posterior
def _param_index(result: Any) -> dict:
    pi = getattr(result, "param_index", None)
    if not pi or "points" not in pi:
        raise ValueError("result.param_index with a 'points' slice is required (a WP-07+ BundleResult)")
    return pi


def frozen_parameters(result: Any) -> np.ndarray:
    """Parameter indices the bundle held rather than estimated (rejected / empty views).

    The camera block (``cam_<v>``) and jaw angle (``jaw_<v>``) of every view whose
    ``view_stats[v]['frozen']`` is true, plus every focal-group ``phi_<j>`` without data
    coupling (zero ``H_data`` diagonal while some view is frozen: its group lost all live
    views).  :func:`face3d.solve.bundle._posterior_fixed` conditions on them (their stiff
    holding rows must not enter the ridge or the inversion).
    """
    pi = _param_index(result)
    stats = getattr(result, "view_stats", None) or []
    frozen = [k for k, st in enumerate(stats) if st.get("frozen")]
    idx: list[int] = []
    for k in frozen:
        for key in (f"cam_{k}", f"jaw_{k}"):
            if key in pi:
                sl = pi[key]
                idx.extend(range(sl.start, sl.stop))
    if frozen and getattr(result, "H_data", None) is not None:
        Hd = np.asarray(result.H_data)
        for key, sl in pi.items():
            if key.startswith("phi_"):
                if np.all(np.diag(Hd)[sl] == 0.0):
                    idx.extend(range(sl.start, sl.stop))
    return np.unique(np.asarray(idx, np.int64))


def _inv_spd(A: np.ndarray) -> np.ndarray:
    from .bundle import _inv_spd as inv
    return inv(A)


def _point_cov(H: np.ndarray, result: Any, conditional_on_zeta: bool = False) -> np.ndarray:
    """Point block of inv(H) with every other parameter eliminated by Schur (bundle maths)."""
    from .bundle import BUNDLE, _posterior_fixed, _SubLayout
    pi = _param_index(result)
    pts = pi["points"]
    n = len(H)
    zi = pi["zeta"].start if "zeta" in pi else -1
    lay = _SubLayout(pts_off=pts.start, pts_end=pts.stop, n=n, zeta_idx=zi)
    fixed = frozen_parameters(result)
    post = _posterior_fixed(np.asarray(H, float), lay, float(BUNDLE["cov_ridge_rel"].value),
                            fixed if fixed.size else None)
    return post["cov_shape"] if conditional_on_zeta else post["cov"]


def posterior_at_prior_weight_one(result: Any, standard_prior_info: np.ndarray | None = None, *,
                                  project: bool = True, conditional_on_zeta: bool = False) -> np.ndarray:
    """Sigma1: the point posterior at prior weight 1 (DESIGN D-16, 4.12, H2), (3N, 3N) mm^2.

    Sigma1 = inv(H_data + H_prior_standard) with every non-point parameter (cameras, phi,
    jaw angles, zeta, term parameters) eliminated by Schur complement (the bundle's own
    :func:`~face3d.solve.bundle._posterior_fixed`, frozen views conditioned on).
    ``standard_prior_info``: the (n, n) prior information of the *standard* prior in the
    result's parameter layout, when the solve used a widened (likeness-mode) prior or a
    rigidity slider (see :func:`standard_prior_info`); None uses ``result.H_prior``.
    With ``project`` the result is gauge-projected at the estimate, P Sigma1 P with
    P = :func:`face3d.eval.align.gauge_projector` (``result.X``).
    ``conditional_on_zeta`` returns the covariance conditional on the log-scale instead
    (as ``cov_shape``); by default zeta is marginalised (the 'globals' of WBS WP-16).
    Only the identity shape model (FreePoints) is supported.
    """
    Hd = getattr(result, "H_data", None)
    Hp = getattr(result, "H_prior", None) if standard_prior_info is None else standard_prior_info
    if Hd is None or Hp is None:
        raise ValueError("result has no H_data / H_prior (covariance failed or a legacy result)")
    X = np.asarray(result.X, float)
    pts = _param_index(result)["points"]
    if pts.stop - pts.start != X.size:
        raise ValueError("posterior_at_prior_weight_one supports the identity (FreePoints) shape model only")
    Hp = np.asarray(Hp, float)
    if Hp.shape != np.shape(Hd):
        raise ValueError(f"standard_prior_info has shape {Hp.shape}, expected {np.shape(Hd)}")
    cov = _point_cov(np.asarray(Hd, float) + Hp, result, conditional_on_zeta)
    if project:
        P = gauge_projector(X)
        cov = P @ cov @ P
    return 0.5 * (cov + cov.T)


def prior_covariance(result: Any, standard_prior_info: np.ndarray | None = None, *,
                     project: bool = True) -> np.ndarray:
    """Point covariance of the prior alone, (3N, 3N) mm^2, from the prior information.

    The [zeta, points] block of ``standard_prior_info`` (default ``result.H_prior``) holds
    every shape-side prior row of the solve (zeta prior, shape prior, symmetry, midline,
    gauge); camera priors do not couple to it, so its inverse's point block is the prior
    point covariance with zeta marginalised (X = e^zeta X~).  Inverted by the bundle's
    Jacobi-scaled Cholesky (pseudo-inverse fallback when the prior leaves a point free:
    its unbounded prior variance then reads as the pseudo-inverse's 0, so the region
    gets no evidence).  Gauge-projected at ``result.X`` when ``project``.
    """
    Hp = getattr(result, "H_prior", None) if standard_prior_info is None else standard_prior_info
    if Hp is None:
        raise ValueError("result has no H_prior")
    Hp = np.asarray(Hp, float)
    pi = _param_index(result)
    pts = pi["points"]
    idx = list(range(pts.start, pts.stop))
    if "zeta" in pi:
        idx = [pi["zeta"].start] + idx
    A = Hp[np.ix_(idx, idx)]
    A = 0.5 * (A + A.T)
    try:
        # Jacobi-scaled Cholesky (the bundle's own inverse): the gauge and zeta columns make
        # H span ~12 decades, which an eigenvalue cut-off would truncate.
        S = _inv_spd(A)
    except np.linalg.LinAlgError:
        S = np.linalg.pinv(A, rcond=1e-15, hermitian=True)
    off = 1 if "zeta" in pi else 0
    cov = S[off:, off:]
    if project:
        P = gauge_projector(np.asarray(result.X, float))
        cov = P @ cov @ P
    return 0.5 * (cov + cov.T)


def shape_prior_info(prior: Any, result: Any) -> np.ndarray:
    """(n, n) Gauss-Newton information of the shape-prior rows of ``prior`` at ``result``.

    Rows r = W (e^-zeta X - mu) as the bundle builds them (WP-07; the generalised
    ``prior.residual`` / ``prior.jacobian`` interface when present, else W = whiten_matrix):
    dr/dX = e^-zeta J, dr/dzeta = -J X~.  Only the zeta and point columns are non-zero.
    """
    pi = _param_index(result)
    X = np.asarray(result.X, float)
    N = len(X)
    pts = pi["points"]
    if pts.stop - pts.start != 3 * N:
        raise ValueError("shape_prior_info supports the identity (FreePoints) shape model only")
    n = int(np.shape(result.H_prior)[0])
    zeta = float(result.zeta) if ("zeta" in pi and result.zeta is not None) else None
    s = math.exp(-zeta) if zeta is not None else 1.0
    Xt = s * X
    if hasattr(prior, "residual") and hasattr(prior, "jacobian"):
        J = np.asarray(prior.jacobian(Xt), float)
    else:
        W = np.asarray(prior.whiten_matrix(), float)
        if W.shape != (3 * N, 3 * N):
            raise ValueError("a prior without the generalised interface must cover all points")
        J = W
    if J.shape[1] != 3 * N:
        raise ValueError(f"prior jacobian has {J.shape[1]} columns, expected {3 * N}")
    Jf = np.zeros((J.shape[0], n))
    Jf[:, pts] = J * s
    if zeta is not None:
        Jf[:, pi["zeta"].start] = -(J @ Xt.ravel())
    return Jf.T @ Jf


def standard_prior_info(result: Any, used_prior: Any, standard_prior: Any) -> np.ndarray:
    """``result.H_prior`` with the shape-prior information of ``used_prior`` (e.g. the
    likeness-mode widened prior) replaced by that of ``standard_prior`` (DESIGN H2).

    Pass the output as ``standard_prior_info`` to :func:`posterior_at_prior_weight_one`
    and :func:`prior_covariance` so that labels are computed at prior weight 1.
    """
    Hp = np.asarray(result.H_prior, float)
    H = Hp - shape_prior_info(used_prior, result) + shape_prior_info(standard_prior, result)
    return 0.5 * (H + H.T)


# =========================================================================== evidence
def region_evidence(Sigma_post: np.ndarray, Sigma_prior: np.ndarray, region_index: Mapping[str, Any], *,
                    X_ref: np.ndarray | None = None) -> dict[str, float]:
    """Evidence k_r = 1 - tr(Sigma_post,rr) / tr(Sigma_prior,rr) per region (DESIGN 4.12).

    Both covariances must be gauge-projected (pass ``X_ref`` to project them here with
    :func:`~face3d.eval.align.gauge_projector`).  ``region_index``: region -> coordinate
    indices.  k = 1 means the photos fixed the region; 0 means the posterior is the prior.
    A region whose prior trace is not positive gets NaN.
    """
    Sp = np.asarray(Sigma_post, float)
    Sq = np.asarray(Sigma_prior, float)
    if Sp.shape != Sq.shape or Sp.ndim != 2 or Sp.shape[0] != Sp.shape[1]:
        raise ValueError("Sigma_post and Sigma_prior must be square and of the same shape")
    if X_ref is not None:
        P = gauge_projector(np.asarray(X_ref, float))
        Sp, Sq = P @ Sp @ P, P @ Sq @ P
    dp, dq = np.diag(Sp), np.diag(Sq)
    out = {}
    for r, c in region_index.items():
        c = np.asarray(c, np.int64)
        tq = float(dq[c].sum()) if c.size else 0.0
        out[r] = float(1.0 - dp[c].sum() / tq) if tq > 0.0 else float("nan")
    return out


def coverage_rules(view_yaw_deg: Sequence[float], view_pitch_deg: Sequence[float], visibility: np.ndarray,
                   region_points: Mapping[str, Any]) -> dict[str, dict[str, bool]]:
    """Hard coverage rules per region (DESIGN 4.12 'Coverage rules').

    ``visibility``: (V, N) bool, landmark observed (and used) in view v.  A view *sees* a
    region when it observes at least ``region_seen_frac`` (half) of the region's points
    (at least one).  Per region:

    * ``observed``: some view observes at least one of its points;
    * ``depth``: two views >= 30 deg apart in yaw both see it (bl C7);
    * ``projection``: a seeing view with |yaw| < 15 deg plus one with |yaw| >= 60 deg
      (com R5.9);
    * ``jaw_underside``: a seeing view with pitch <= -15 deg;
    * ``ears``: a seeing view with |yaw| >= 30 deg and two seeing views whose pitch differs
      by >= 5 deg (com R3.3).

    Every rule is evaluated for every region; :data:`REGION_COVERAGE_RULES` says which ones
    a region needs (:func:`coverage_ok`).
    """
    yaw = np.asarray(view_yaw_deg, float).reshape(-1)
    pitch = np.asarray(view_pitch_deg, float).reshape(-1)
    vis = np.asarray(visibility, bool)
    if vis.ndim != 2 or vis.shape[0] != len(yaw) or len(pitch) != len(yaw):
        raise ValueError("visibility must be (V, N) with one yaw and one pitch per view")
    frac = float(_d("region_seen_frac"))
    sep = float(_d("depth_min_sep_deg"))
    front, side = float(_d("projection_front_max_yaw_deg")), float(_d("projection_side_min_yaw_deg"))
    low = float(_d("jaw_underside_max_pitch_deg"))
    ear_yaw, ear_sep = float(_d("ears_min_yaw_deg")), float(_d("ears_pitch_sep_deg"))
    out: dict[str, dict[str, bool]] = {}
    for r, pts in region_points.items():
        pts = np.asarray(pts, np.int64)
        cnt = vis[:, pts].sum(axis=1) if pts.size else np.zeros(len(yaw), int)
        need = max(1, int(math.ceil(frac * pts.size - 1e-12))) if pts.size else 1
        sees = cnt >= need
        ys, ps = yaw[sees], pitch[sees]
        depth = bool(ys.size >= 2 and (ys.max() - ys.min()) >= sep)
        proj = bool(np.any(np.abs(ys) < front) and np.any(np.abs(ys) >= side))
        jaw = bool(np.any(ps <= low))
        ears = bool(np.any(np.abs(ys) >= ear_yaw) and ps.size >= 2 and (ps.max() - ps.min()) >= ear_sep)
        out[r] = {"depth": depth, "projection": proj, "jaw_underside": jaw, "ears": ears,
                  "observed": bool(np.any(cnt > 0))}
    return out


def coverage_ok(region: str, rules: Mapping[str, bool]) -> bool:
    """True when ``rules`` (one region's :func:`coverage_rules` entry) meets every rule the
    region needs (:data:`REGION_COVERAGE_RULES`; unknown regions need ``depth``)."""
    need = REGION_COVERAGE_RULES.get(region, ("depth",))
    return all(bool(rules.get(k, False)) for k in need)


def region_sigma_rep(sigma_rep_mm: np.ndarray, region_index: Mapping[str, Any]) -> dict[str, float]:
    """Region sigma_rep (mm): RMS of the per-coordinate sigma_rep over the region's coordinates.

    sigma_rep_mm is (N, 3); the projection regions therefore use the z sigmas only.  The
    RMS (not the max) is the region-level analogue of the per-region RMS targets (EV-3).
    """
    s = np.asarray(sigma_rep_mm, float).reshape(-1)
    return {r: float(np.sqrt(np.mean(s[np.asarray(c, np.int64)] ** 2))) if len(c) else float("nan")
            for r, c in region_index.items()}


def region_status(k: float, coverage_ok: bool, sigma_rep_mm: float, target: float, observed: bool) -> str:
    """Claims-ledger state of one region (DESIGN D-16, 4.12).

    'unobserved' if no view sees it; 'measured' if k >= 0.8, its coverage rules hold and
    sigma_rep <= target; else 'constrained' if k >= 0.5; else 'prior-driven' (also for a
    NaN k).
    """
    if not observed:
        return "unobserved"
    k = float(k)
    if not np.isfinite(k):
        return "prior-driven"
    if k >= float(_d("evidence_measured_k")) and coverage_ok and float(sigma_rep_mm) <= float(target):
        return "measured"
    if k >= float(_d("evidence_constrained_k")):
        return "constrained"
    return "prior-driven"


# =========================================================================== LOVO
def _uv_of(view: Any) -> np.ndarray:
    return np.asarray(view.uv if hasattr(view, "uv") else view, float)


def _proj_jac(cam: Any, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Pinhole projection (N, 2) and d u / d X (N, 2, 3) (no distortion)."""
    Y = X @ cam.R.T + cam.t
    z = Y[:, 2]
    u = cam.f * Y[:, :2] / z[:, None] + np.array([cam.cx, cam.cy])
    A = np.zeros((len(X), 2, 3))
    A[:, 0, 0] = 1.0 / z
    A[:, 1, 1] = 1.0 / z
    A[:, 0, 2] = -Y[:, 0] / z ** 2
    A[:, 1, 2] = -Y[:, 1] / z ** 2
    return u, cam.f * A @ cam.R


def _whiteners(C: np.ndarray) -> np.ndarray:
    from .noise import whitening
    return whitening(np.asarray(C, float))


def _repose(cam0: Any, X: np.ndarray, uv: np.ndarray, Wh: np.ndarray, iters: int = 20) -> Any:
    """Gauss-Newton re-pose of a camera (rotation increment and translation; focal fixed)
    against fixed points X, whitened by Wh (n, 2, 2).  Deterministic, warm-started."""
    from ..geometry.rotations import rodrigues
    cam = cam0.copy()
    prev = None
    for _ in range(iters):
        u, Jx = _proj_jac(cam, X)
        Y = X @ cam.R.T
        # dY/domega = -[R X]_x (left increment), dY/dt = I
        Jy_dom = np.zeros((len(X), 3, 3))
        Jy_dom[:, 0, 1], Jy_dom[:, 0, 2] = Y[:, 2], -Y[:, 1]
        Jy_dom[:, 1, 0], Jy_dom[:, 1, 2] = -Y[:, 2], Y[:, 0]
        Jy_dom[:, 2, 0], Jy_dom[:, 2, 1] = Y[:, 1], -Y[:, 0]
        Yc = Y + cam.t
        z = Yc[:, 2]
        dudY = np.zeros((len(X), 2, 3))
        dudY[:, 0, 0] = cam.f / z
        dudY[:, 1, 1] = cam.f / z
        dudY[:, 0, 2] = -cam.f * Yc[:, 0] / z ** 2
        dudY[:, 1, 2] = -cam.f * Yc[:, 1] / z ** 2
        J = np.concatenate([dudY @ Jy_dom, dudY], axis=2)          # (n, 2, 6)
        r = np.einsum("nij,nj->ni", Wh, u - uv).reshape(-1)
        Jw = np.einsum("nij,njk->nik", Wh, J).reshape(-1, 6)
        cost = float(r @ r)
        if prev is not None and cost > prev * (1 + 1e-12):
            break
        H = Jw.T @ Jw
        dx = -np.linalg.solve(H + 1e-9 * np.trace(H) / 6 * np.eye(6), Jw.T @ r)
        cam.R = rodrigues(dx[:3]) @ cam.R
        cam.t = cam.t + dx[3:]
        prev = cost
        if np.linalg.norm(dx) < 1e-10:
            break
    return cam


def lovo_gamma(solve_without: Callable[[int], Any], result: Any, views: Sequence[Any],
               noise_covs: Sequence[np.ndarray]) -> tuple[float, np.ndarray, list[str]]:
    """Leave-one-view-out calibration factor gamma (DESIGN 4.13, D-16).

    For every view v (needs >= 3 views): ``solve_without(v)`` re-solves without v (the
    caller warm-starts it, <= 10 iterations: :func:`make_solve_without`); v's camera is
    re-posed (rotation and translation, focal kept from ``result``) against the reduced
    consensus X(-v) held fixed; every held-out observation i of v gets the predictive
    covariance Sigma_pred,i = noise_i + J_i Sigma_X(-v),ii J_i^T, with J_i = du/dX at the
    re-posed camera and Sigma_X(-v) the reduced solve's ``cov_shape`` gauge-projected at
    X(-v) (the re-pose absorbs rigid motion and, through depth, scale).  Then

        gamma^2 = sum_v sum_i e_i^T Sigma_pred,i^-1 e_i / sum_v (2 n_v - 6),

    i.e. the mean of e^T Sigma^-1 e / 2 over held-out points with the six pose degrees of
    freedom of each re-pose removed from the count (without that correction gamma^2 is
    biased low by 3 / n_v).

    ``views``: per view, an object with ``uv`` (N, 2) (ViewObs, PhotoLandmarks) or the
    array; NaN rows are unobserved.  Observations rejected by the full solve
    (``result.inlier_mask``) are left out.  ``noise_covs``: per view (N, 2, 2) px^2 noise
    covariances as *declared* to the solver (e.g. ``result.obs_cov_px``; pass the base
    covariances without nu^2 to test the declared noise itself).

    Returns ``(gamma, per_view_ratio, flags)``: ``per_view_ratio[v]`` = held-out RMS (px)
    / in-sample RMS (px, ``result.per_view_residuals`` on the same points); flag
    ``'L-HELDOUT'`` when any ratio exceeds 2 (DESIGN 4.13).  With fewer than 3 views:
    ``(1.0, NaN ratios, ['L-TOO-FEW-VIEWS'])`` (gamma 1 is neutral in sigma_rep).
    """
    V = len(views)
    if len(noise_covs) != V:
        raise ValueError(f"noise_covs has {len(noise_covs)} entries for {V} views")
    ratios = np.full(V, np.nan)
    if V < int(_d("lovo_min_views")):
        return 1.0, ratios, [FLAG_L_TOO_FEW_VIEWS]
    inl = getattr(result, "inlier_mask", None)
    per_view = getattr(result, "per_view_residuals", None)
    num, den = 0.0, 0.0
    flags: list[str] = []
    lim = float(_d("lovo_heldout_ratio_flag"))
    for v in range(V):
        uv = _uv_of(views[v])
        m = np.isfinite(uv).all(axis=1)
        if inl is not None and inl[v] is not None:
            m &= np.asarray(inl[v], bool)
        if m.sum() < 4:
            continue
        red = solve_without(v)
        Xr = np.asarray(red.X, float)
        covr = getattr(red, "cov_shape", None)
        if covr is None:
            covr = red.cov
        P = gauge_projector(Xr)
        covp = P @ np.asarray(covr, float) @ P
        C = np.asarray(noise_covs[v], float)[m]
        idx = np.flatnonzero(m)
        cam = _repose(result.cameras[v], Xr[idx], uv[idx], _whiteners(C))
        u, J = _proj_jac(cam, Xr[idx])
        e = uv[idx] - u
        blocks = np.stack([covp[3 * i:3 * i + 3, 3 * i:3 * i + 3] for i in idx])
        S = C + np.einsum("nij,njk,nlk->nil", J, blocks, J)
        q = np.einsum("ni,nij,nj->n", e, np.linalg.inv(S), e)
        num += float(q.sum())
        den += max(2.0 * len(idx) - 6.0, 1.0)
        held = float(np.sqrt(np.mean(np.sum(e * e, axis=1))))
        ins = float("nan")
        if per_view is not None:
            r = np.asarray(per_view[v], float)[idx]
            r = r[np.isfinite(r)]
            if r.size:
                ins = float(np.sqrt(np.mean(r * r)))
        ratios[v] = held / ins if ins > 0 else float("nan")
        if np.isfinite(ratios[v]) and ratios[v] > lim and FLAG_L_HELDOUT not in flags:
            flags.append(FLAG_L_HELDOUT)
    gamma = math.sqrt(num / den) if den > 0 else 1.0
    return float(gamma), ratios, flags


def make_solve_without(views: Sequence[Any], result: Any, X0: np.ndarray | None = None,
                       bundle_kwargs: Mapping[str, Any] | None = None,
                       max_iter: int | None = None) -> Callable[[int], Any]:
    """A warm-started ``solve_without(v)`` for :func:`lovo_gamma` (DESIGN 4.13).

    ``views``: the ``ViewObs`` list of the full solve; each reduced solve starts from the
    full solve's cameras (``result.cameras``) and points (``X0``, default ``result.X``) and
    runs :func:`face3d.solve.bundle.bundle_adjust` with ``bundle_kwargs`` (prior, priors,
    robust, ...) and at most ``max_iter`` (10) LM iterations per run.  Keyword arguments
    indexed per view (``terms`` referencing views) are the caller's responsibility.
    """
    from .bundle import bundle_adjust
    kw = dict(bundle_kwargs or {})
    priors = kw.pop("priors", None)
    it = int(_d("lovo_max_iter")) if max_iter is None else int(max_iter)
    Xs = np.asarray(result.X if X0 is None else X0, float)

    def solve(v: int) -> Any:
        keep = [replace(views[k], camera=result.cameras[k].copy()) for k in range(len(views)) if k != v]
        return bundle_adjust(keep, Xs.copy(), priors, max_iter=it, **kw)
    return solve


def _inflation(result: Any, gamma: float) -> float:
    chi = getattr(result, "chi2_red", None)
    chi = float(chi) if chi is not None and np.isfinite(chi) else 1.0
    return max(1.0, float(gamma) ** 2, chi)


def _sigma_def(result: Any, N: int) -> np.ndarray:
    sdef = getattr(result, "sigma_def_mm", None)
    return np.zeros(N) if sdef is None else np.asarray(sdef, float).reshape(N)


def bias_gain(result: Any, prior_info: np.ndarray | None = None) -> np.ndarray:
    """Data gain K = I - cov_shape H_prior,pp (3N, 3N) of the solve (linearised).

    For the linear-Gaussian model the estimate responds to a perturbation b of the
    observed points (the shared definition bias, D-06) as K b, K = Sigma H_data,eff =
    I - Sigma H_prior (Sigma the posterior with the cameras eliminated, H_prior the point
    block of the prior information; both conditional on zeta).  K -> I where the photos
    dominate and -> 0 where the prior does.  ``prior_info`` replaces ``result.H_prior``
    (standard prior information, :func:`standard_prior_info`); Sigma is then recomputed
    from H_data + prior_info, so the gain is the prior-weight-1 gain (H2).
    """
    X = np.asarray(result.X, float)
    pts = _param_index(result)["points"]
    if prior_info is None:
        Hp, Sig = result.H_prior, result.cov_shape
        if Sig is None or Hp is None:
            raise ValueError("result has no cov_shape / H_prior")
    else:
        Hp = prior_info
        Sig = posterior_at_prior_weight_one(result, prior_info, project=False, conditional_on_zeta=True)
    Hpp = np.asarray(Hp, float)[pts, pts]
    return np.eye(X.size) - np.asarray(Sig, float) @ Hpp


def reported_covariance(result: Any, gamma: float = 1.0, cov: np.ndarray | None = None, bias: str = "gain",
                        prior_info: np.ndarray | None = None) -> np.ndarray:
    """Full reported covariance (3N, 3N) mm^2 behind sigma_rep (DESIGN D-06, D-16, 4.13).

    C_rep = C * max(1, gamma^2, chi2_red) + B, with C = ``cov`` or ``result.cov_shape`` and
    the definition-bias term B (D = diag(sigma_def^2) per coordinate):

    * ``bias='floor'``: B = D, the literal DESIGN D-16 / 4.13 formula (an isotropic floor
      added in full to every landmark);
    * ``bias='gain'`` (default): B = K D K^T with K = :func:`bias_gain`, the exact
      linearised propagation of a bias shared across views.  It tends to D where the
      photos determine a point (so the floor still never shrinks with more views, D-06 /
      H3) and to 0 where the prior does (a bias the solve did not follow cannot be in the
      error).

    **Honesty** (DESIGN 7.5 gates: NEES/dof 0.8-1.25, aligned 1-sigma coverage 0.60-0.76
    over >= 30 seeds; H12).  Re-measured by WBS FU-02 after the FU-01 noise change (point
    kinds without an image tangent isotropic at max(sigma_n, sigma_t)).  All numbers:
    gauge-projected NEES/dof / 1-sigma coverage of the similarity-aligned error, means over
    seeds 1000-1029 of the WP-01 legacy scenarios, legacy prior, robust schedule (DESIGN
    4.5), the scenario's 5 % outliers (10 % in ``rear_phone_outliers``), gamma 1, PnP start
    (``reconstruct_landmarks``) followed by the bundle with the stated noise.

    (a) No tangents (the WP-16 set-up; every point kind at its conservative fallback).
    Under-confident everywhere, as FU-01 reported; this is not the correct noise model:

    ====================  =============  =============  =============  ========
    scenario              posterior      floor form     gain form      chi2_red
    ====================  =============  =============  =============  ========
    studio_ring_legacy    1.04 / 0.737   0.61 / 0.819   0.72 / 0.792   0.68
    rear_phone_legacy     0.94 / 0.739   0.60 / 0.824   0.71 / 0.794   0.66
    selfie_legacy         0.82 / 0.793   0.57 / 0.844   0.67 / 0.826   0.62
    camera_roll_legacy    0.96 / 0.745   0.60 / 0.826   0.70 / 0.794   0.65
    rear_phone_smooth     0.90 / 0.746   0.57 / 0.832   0.67 / 0.799   0.64
    rear_phone_outliers   0.94 / 0.745   0.60 / 0.827   0.71 / 0.794   0.66
    rear_phone_nobias     0.69 / 0.813   0.44 / 0.879   0.53 / 0.856   0.64
    ====================  =============  =============  =============  ========

    (b) The detector simulator's own image tangents passed to the views
    (``ViewObs.tangents = obs.tangent_dirs``):

    ====================  =============  =============  =============  ========
    scenario              posterior      floor form     gain form      chi2_red
    ====================  =============  =============  =============  ========
    studio_ring_legacy    1.367 / 0.621  0.695 / 0.761  0.812 / 0.726  0.84
    rear_phone_legacy     1.238 / 0.635  0.694 / 0.758  0.811 / 0.727  0.81
    selfie_legacy         1.047 / 0.725  0.668 / 0.790  0.777 / 0.764  0.78
    camera_roll_legacy    1.25 / 0.650   0.68 / 0.764   0.80 / 0.727   0.80
    rear_phone_smooth     1.208 / 0.643  0.669 / 0.771  0.777 / 0.735  0.77
    rear_phone_outliers   1.214 / 0.648  0.695 / 0.764  0.813 / 0.732  0.82
    rear_phone_nobias     0.812 / 0.731  0.482 / 0.846  0.573 / 0.819  0.78
    ====================  =============  =============  =============  ========

    (c) Tangents, and the detector floor the engine's noise model declares
    (sigma_floor = max(0.5 px, k face_px / 256), DESIGN 4.4) but the simulator does not
    draw, drawn by the test bed (isotropic, a stream of its own).  This is the set-up of
    tests/test_observability.py::test_sigma_rep_honesty_on_testbed:

    ====================  =============  =============  =============  ========
    scenario              posterior      floor form     gain form      chi2_red
    ====================  =============  =============  =============  ========
    studio_ring_legacy    1.407 / 0.618  0.719 / 0.759  0.838 / 0.719  0.86
    rear_phone_legacy     1.269 / 0.626  0.714 / 0.755  0.833 / 0.712  0.86
    selfie_legacy         1.073 / 0.714  0.686 / 0.784  0.796 / 0.757  0.80
    camera_roll_legacy    1.282 / 0.654  0.704 / 0.761  0.818 / 0.727  0.84
    rear_phone_smooth     1.237 / 0.634  0.687 / 0.759  0.797 / 0.721  0.80
    rear_phone_outliers   1.256 / 0.640  0.724 / 0.758  0.843 / 0.716  0.83
    rear_phone_nobias     0.841 / 0.729  0.500 / 0.840  0.592 / 0.812  0.81
    ====================  =============  =============  =============  ========

    (d) The simulator's exact covariance as ``ViewObs.cov_px`` (its tangents and its
    (sigma_n, sigma_t) table, no floor; differs from (c) by the brow tangent, which DESIGN
    4.4 leaves 'free' (engine 40 mm) and the simulator draws at 8 mm):

    ====================  =============  =============  =============  ========
    scenario              posterior      floor form     gain form      chi2_red
    ====================  =============  =============  =============  ========
    studio_ring_legacy    1.453 / 0.603  0.721 / 0.756  0.842 / 0.717  0.94
    rear_phone_legacy     1.314 / 0.613  0.722 / 0.747  0.841 / 0.708  0.95
    selfie_legacy         1.122 / 0.692  0.704 / 0.776  0.815 / 0.745  0.90
    camera_roll_legacy    1.347 / 0.627  0.723 / 0.753  0.839 / 0.711  0.93
    rear_phone_smooth     1.286 / 0.619  0.700 / 0.759  0.812 / 0.718  0.94
    rear_phone_outliers   1.286 / 0.630  0.726 / 0.752  0.847 / 0.718  0.91
    rear_phone_nobias     0.869 / 0.707  0.509 / 0.832  0.600 / 0.800  0.92
    ====================  =============  =============  =============  ========

    Reading (FU-02):

    * With the noise the simulator really draws (d), the gain form is inside both gates on
      all six scenarios that draw a definition bias.  With the engine's own model and
      tangents (c) it is inside on four; ``selfie_legacy`` and ``rear_phone_smooth`` read
      NEES 0.796 / 0.797 against the 0.8 gate (coverage inside): NOT met there, by 0.004,
      and the difference to (d) is the engine's deliberately wide 'free' brow tangent.
      Tangents alone (b): inside on studio_ring, rear_phone, camera_roll (at the gate) and
      outliers; selfie 0.777 / 0.764 and smooth 0.777 fail.
    * In (b)-(d) the posterior alone is over-confident whenever a definition bias is drawn
      (NEES 1.05-1.45) and inside the gates when none is (``rear_phone_nobias`` 0.81-0.87): the
      noise model is honest, the excess is the shared bias (D-06).  The WP-16 statement
      'posterior-only NEES > 1.25' is not a property of the model (1.24 in (b)).
    * ``rear_phone_nobias`` with the gain or floor form is under-confident by construction:
      the engine declares a sigma_def the scenario does not draw.
    * The literal floor form fails the NEES gate in every row.
    * **No recalibration of the formula was made**, and none is warranted: the gain form is
      the exact linear-Gaussian propagation, and the remaining distance from 1 is the test
      bed's legacy symmetry prior, which is wider than its subjects (sigma_sym 2.0 mm for a
      pair difference of SD 1.41 mm, sigma_mid 1.5 mm for 1.0 mm).  Evidence
      (``rear_phone``, exact covariance, no outliers, plain least squares, 30 seeds): with
      the legacy prior the posterior reads 0.837 / 0.712 without bias and the gain form
      0.826 / 0.710 with it; with sigma_sym 1.41 and sigma_mid 1.0 they read 0.963 / 0.700
      and 0.918 / 0.705.  The shape sigma (8 mm against the subjects' 4 mm) changes
      nothing (0.835, 0.831).  What FU-02 changed is the test bed's side of the comparison:
      tangents passed, and the declared floor drawn.
    * Not re-measured by FU-02: the D-04 factor prior and the WP-11 out-of-prior subjects.
      WP-16 measured them before FU-01 without tangents (factor prior, gain form: rear_phone
      0.83 / 0.75, studio_ring 0.88 / 0.71, selfie 0.68 / 0.81 FAIL, camera_roll 0.83 /
      0.74); those numbers are stale and belong to the release gates (WP-23; DESIGN 7.5).
    """
    X = np.asarray(result.X, float)
    N = len(X)
    C = result.cov_shape if cov is None else cov
    if C is None:
        raise ValueError("result has no cov_shape")
    C = np.asarray(C, float)
    D = np.repeat(_sigma_def(result, N) ** 2, 3)
    if bias == "floor":
        B = np.diag(D)
    elif bias == "gain":
        K = bias_gain(result, prior_info)
        B = (K * D[None, :]) @ K.T
    else:
        raise ValueError(f"bias must be 'floor' or 'gain', not {bias!r}")
    out = C * _inflation(result, gamma) + B
    return 0.5 * (out + out.T)


def sigma_rep(result: Any, gamma: float = 1.0, cov: np.ndarray | None = None, bias: str = "floor",
              prior_info: np.ndarray | None = None) -> np.ndarray:
    """Reported sigma per landmark and axis, (N, 3) mm (DESIGN D-16, 4.13).

    sigma_rep^2 = diag(cov_shape) * max(1, gamma^2, chi2_red) + sigma_def^2 (default
    ``bias='floor'``, the WBS / DESIGN formula), with ``cov_shape``, ``chi2_red`` and
    ``sigma_def_mm`` from the result (a non-finite chi2_red counts as 1).  ``cov``
    optionally replaces ``cov_shape`` (e.g. the gauge-projected posterior at prior weight 1
    of :func:`posterior_at_prior_weight_one`, which the ledger reports, H2).
    ``bias='gain'`` propagates the definition bias through the data gain instead
    (:func:`reported_covariance`; the calibrated form the ledger uses).  The
    definition-bias floor never shrinks with more views (D-06).
    """
    N = len(np.asarray(result.X))
    if bias == "floor":
        C = result.cov_shape if cov is None else cov
        if C is None:
            raise ValueError("result has no cov_shape")
        d = np.maximum(np.diag(np.asarray(C, float)), 0.0).reshape(N, 3)
        return np.sqrt(d * _inflation(result, gamma) + _sigma_def(result, N)[:, None] ** 2)
    Cr = reported_covariance(result, gamma, cov, bias, prior_info)
    return np.sqrt(np.maximum(np.diag(Cr), 0.0)).reshape(N, 3)


# =========================================================================== gates
def _wh_quantile(g: float, h: float, z: float) -> float:
    """Wilson-Hilferty quantile of g chi^2_h at the standard-normal point z (DESIGN 4.5, 4.13)."""
    c = 2.0 / (9.0 * h)
    base = 1.0 - c + z * math.sqrt(c)
    return g * h * max(base, 0.0) ** 3


def shrinkage_gate(x_hat: np.ndarray, S_rr: np.ndarray, Sigma_rr: np.ndarray, alpha_lo: float | None = None,
                   alpha_hi: float | None = None) -> dict[str, Any]:
    """Shrinkage and plausibility gate against the predictive distribution (DESIGN D-18, 4.13).

    ``x_hat`` (3n,): the region's estimate minus the prior mean in the prior's units
    (x~ - mu); ``S_rr``: the region's prior covariance; ``Sigma_rr``: its posterior
    covariance.  T = x^T S^-1 x; lambda = eig(I - S^-1/2 Sigma S^-1/2) clipped to [0, 1];
    m = sum(lambda) (= k_eff, the number of effectively measured dimensions);
    v = 2 sum(lambda^2); g = v / (2m); h = 2 m^2 / v.  Under a correct prior T is
    distributed as sum lambda_i chi^2_1, matched by g chi^2_h with the Wilson-Hilferty
    quantile q(z) = g h (1 - 2/(9h) + z sqrt(2/(9h)))^3.  Finding
    ``'P-PULLED-TO-AVERAGE'`` if T < q(norm_ppf(alpha_lo)) (default 0.01, z = -2.326),
    ``'P-IMPLAUSIBLE'`` if T > q(norm_ppf(1 - alpha_hi)) (0.001, z = 3.090), else None.

    Returns ``{'T', 'k_eff', 'q_lo', 'q_hi', 'finding'}`` (q NaN and no finding when the
    photos measured nothing, k_eff = 0).
    """
    a_lo = float(_d("shrink_alpha_lo")) if alpha_lo is None else float(alpha_lo)
    a_hi = float(_d("shrink_alpha_hi")) if alpha_hi is None else float(alpha_hi)
    x = np.asarray(x_hat, float).reshape(-1)
    S = np.asarray(S_rr, float)
    Sg = np.asarray(Sigma_rr, float)
    w, Q = np.linalg.eigh(0.5 * (S + S.T))
    if w.min() <= 0:
        raise ValueError("S_rr must be positive definite")
    Sih = (Q / np.sqrt(w)) @ Q.T                                   # S^-1/2 (symmetric)
    y = Sih @ x
    T = float(y @ y)
    M = np.eye(len(x)) - Sih @ (0.5 * (Sg + Sg.T)) @ Sih
    lam = np.clip(np.linalg.eigvalsh(0.5 * (M + M.T)), 0.0, 1.0)
    m = float(lam.sum())
    v = 2.0 * float(np.sum(lam ** 2))
    if m <= 0 or v <= 0:
        return {"T": T, "k_eff": m, "q_lo": float("nan"), "q_hi": float("nan"), "finding": None}
    g = v / (2.0 * m)
    h = 2.0 * m * m / v
    q_lo = _wh_quantile(g, h, norm_ppf(a_lo))
    q_hi = _wh_quantile(g, h, norm_ppf(1.0 - a_hi))
    finding = FINDING_PULLED if T < q_lo else (FINDING_IMPLAUSIBLE if T > q_hi else None)
    return {"T": T, "k_eff": m, "q_lo": q_lo, "q_hi": q_hi, "finding": finding}


def legacy_shrinkage_gate(c_hat: np.ndarray, K: int) -> bool:
    """The OLD gate ||c||^2 < K - 2 sqrt(2K) (com R5.8), kept only to document D-18.

    It compares whitened coefficients with chi^2_K, ignoring that the posterior mean is
    shrunk, so it fires on most faces drawn from the prior itself (DESIGN D-18: 85 %).
    Never use it for a finding.
    """
    c = np.asarray(c_hat, float).reshape(-1)
    return bool(float(c @ c) < K - 2.0 * math.sqrt(2.0 * K))


# =========================================================================== likeness mode
def _rigid_columns(prior: Any) -> np.ndarray:
    cols = (getattr(prior, "meta", None) or {}).get("columns")
    L = getattr(prior, "L", None)
    if L is None:
        return np.zeros(0, bool)
    if cols is None or len(cols) != L.shape[1]:
        return np.zeros(L.shape[1], bool)
    return np.array([str(c).startswith("rigid_") for c in cols], bool)


def shape_prior_cov(prior: Any) -> np.ndarray:
    """The prior's shape covariance (3n, 3n) mm^2 without its rigid-invariance columns.

    A FactorPrior built with ``rigid_invariance`` carries translation (100 mm) and rotation
    (0.5 rad) columns that model pose, not shape (DESIGN 4.6); they are dropped here (named
    ``rigid_*`` in ``meta['columns']``).  Other priors return ``prior.cov()``.
    """
    L = getattr(prior, "L", None)
    R = getattr(prior, "R", None)
    if L is None or R is None:
        return np.asarray(prior.cov(), float)
    keep = ~_rigid_columns(prior)
    Ls = np.asarray(L, float)[:, keep]
    return Ls @ Ls.T + np.asarray(R, float)


def prior_shares(Sigma_post: np.ndarray, Sigma_prior: np.ndarray) -> np.ndarray:
    """Prior share p_i = sigma_post^2 / sigma_prior^2 per landmark (DESIGN 4.6), (N,).

    Traces of the 3 x 3 diagonal blocks of the (gauge-projected) covariances; NaN where
    the prior block is 0.
    """
    dp = np.diag(np.asarray(Sigma_post, float)).reshape(-1, 3).sum(1)
    dq = np.diag(np.asarray(Sigma_prior, float)).reshape(-1, 3).sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(dq > 0, dp / np.where(dq > 0, dq, 1.0), np.nan)


def widen_prior(prior: Any, multiplier: np.ndarray) -> Any:
    """A copy of ``prior`` with per-coordinate kappa multiplied by ``multiplier`` (3n,).

    FactorPrior: L_shape <- M L_shape (rigid columns untouched), R <- M R M; DiagonalPrior:
    sigma <- M sigma.  The global ``index`` and ids are kept; ``meta['likeness_multiplier']``
    records M.  Other priors raise ``TypeError``.
    """
    from ..model.landmark_prior import DiagonalPrior, FactorPrior
    m = np.asarray(multiplier, float).reshape(-1)
    if isinstance(prior, FactorPrior):
        if m.shape != (3 * prior.n,):
            raise ValueError(f"multiplier must have {3 * prior.n} entries")
        L = np.array(prior.L, float)
        rig = _rigid_columns(prior)
        L[:, ~rig] = m[:, None] * L[:, ~rig]
        R = m[:, None] * np.asarray(prior.R, float) * m[None, :]
        meta = dict(prior.meta)
        meta["likeness_multiplier"] = m.tolist()
        return FactorPrior(prior.mean(), L, R, ids=list(prior.ids), meta=meta, index=prior.index)
    if isinstance(prior, DiagonalPrior):
        sig = prior.marginal_sd().reshape(-1)
        if m.shape != sig.shape:
            raise ValueError(f"multiplier must have {sig.size} entries")
        meta = dict(prior.meta)
        meta["likeness_multiplier"] = m.tolist()
        return DiagonalPrior(prior.mean(), (sig * m).reshape(-1, 3), ids=list(prior.ids), meta=meta,
                             index=prior.index)
    raise TypeError(f"likeness mode cannot widen a {type(prior).__name__}")


def _flag_likeness(res: Any) -> None:
    flags = getattr(res, "flags", None)
    if flags is None:
        try:
            res.flags = [FLAG_LIKENESS]
        except AttributeError:
            pass
    elif FLAG_LIKENESS not in flags:
        flags.append(FLAG_LIKENESS)


def likeness_mode_prior(prior: Any, result: Any, seen_counts: np.ndarray, max_share: float | None = None,
                        factor: float | None = None, max_iter: int | None = None,
                        resolve: Callable[[Any], Any] | None = None, *, return_result: bool = False) -> Any:
    """Likeness mode (DESIGN 4.6 'Prior share', anat R1.4): widen kappa where the photos see.

    Repeats at most ``max_iter`` (5) times: compute the prior shares p_i (gauge-projected
    posterior / prior traces of the current solve, :func:`prior_shares`); for every
    landmark seen in >= 2 views (``seen_counts``, global point indices) with p_i >
    ``max_share`` (0.2), multiply its kappa by ``factor`` (1.5, :func:`widen_prior`); then
    ``result = resolve(widened_prior)``.  Stops when no landmark offends.

    The widened prior is a presentation choice: labels and sigma stay at prior weight 1
    (DESIGN H2).  They are computed from the standard solve ``result`` itself
    (``assess(widened_result, standard_result=result)``, exact); every re-solved result is
    flagged :data:`FLAG_LIKENESS` in ``flags`` so that :func:`assess` refuses to label it on
    its own.  (:func:`standard_prior_info` with :func:`posterior_at_prior_weight_one` is
    the WBS linearised route; it re-linearises at the widened estimate and is not exact.)
    Returns the widened prior (``meta['likeness']`` holds the rounds and the final shares),
    or ``(prior, result)`` with ``return_result`` (``result`` is the input standard solve
    when no round was needed).
    """
    if resolve is None:
        raise ValueError("likeness_mode_prior needs a resolve(prior) -> BundleResult callable")
    share = float(_d("likeness_max_share")) if max_share is None else float(max_share)
    fac = float(_d("likeness_factor")) if factor is None else float(factor)
    its = int(_d("likeness_max_iter")) if max_iter is None else int(max_iter)
    min_views = int(_d("likeness_min_views"))
    seen = np.asarray(seen_counts).reshape(-1)
    n_local = int(getattr(prior, "n", len(np.asarray(prior.mean()))))
    index = getattr(prior, "index", None)
    glob = np.arange(n_local) if index is None else np.asarray(index, np.int64)
    mult = np.ones(3 * n_local)
    cur, res = prior, result
    rounds = 0
    shares = prior_shares(posterior_at_prior_weight_one(res), prior_covariance(res))
    for _ in range(its):
        p = shares[glob]
        bad = (seen[glob] >= min_views) & np.isfinite(p) & (p > share)
        if not bad.any():
            break
        cols = (3 * np.flatnonzero(bad)[:, None] + np.arange(3)).reshape(-1)
        mult[cols] *= fac
        cur = widen_prior(prior, mult)
        res = resolve(cur)
        _flag_likeness(res)
        rounds += 1
        shares = prior_shares(posterior_at_prior_weight_one(res), prior_covariance(res))
    if cur is prior:
        cur = widen_prior(prior, mult)
    cur.meta["likeness"] = {"rounds": rounds, "max_share": share, "factor": fac,
                            "final_shares": [None if not np.isfinite(s) else float(s) for s in shares[glob]]}
    return (cur, res) if return_result else cur


# =========================================================================== tiers
def tier(scale_mode: str, region_statuses: Mapping[str, str], n_views: int, yaws: Sequence[float],
         focal_statuses: Sequence[str], all_selfie: bool, *,
         exif_log_sigma: Sequence[float | None] | float | None = None) -> tuple[str, str]:
    """Evidence tier (DESIGN D-17, 4.12): ('S', 'metric') | ('A', 'iris-scaled') |
    ('B', 'proportions only') | ('C', 'blockout').

    * C: one photo, all views within |yaw| < 20 deg, or all selfies (checked first: the
      most conservative claim wins);
    * S: scale ``'measured'`` (caliper or card), nose_projection and chin_projection
      'measured', >= 5 views and every view's focal 'measured' or confirmed by an EXIF
      prior with sigma <= 0.04 (``exif_log_sigma``, per view or scalar);
    * A: scale in {'measured', 'iris'}, >= 3 views and max |yaw| >= 45 deg;
    * B: everything else (H4: without a metric source the tier never exceeds B).

    ``n_views``, ``yaws``, ``focal_statuses`` and a per-view ``exif_log_sigma`` describe the
    views that contributed evidence (D-17): :func:`assess` leaves frozen (rejected or
    empty) views out.
    """
    y = np.abs(np.asarray(list(yaws), float))
    n_views = int(n_views)
    if n_views <= 1 or (y.size and np.all(y < float(_d("tier_c_max_yaw_deg")))) or bool(all_selfie):
        return "C", TIER_NAMES["C"]
    fs = list(focal_statuses)
    if exif_log_sigma is None or np.ndim(exif_log_sigma) == 0:
        ex = [exif_log_sigma] * len(fs)
    else:
        ex = list(exif_log_sigma)
    lim = float(_d("tier_s_exif_sigma_log"))
    focal_ok = bool(fs) and all(s == "measured" or (e is not None and float(e) <= lim) for s, e in zip(fs, ex))
    if (scale_mode == "measured" and region_statuses.get("nose_projection") == "measured"
            and region_statuses.get("chin_projection") == "measured"
            and n_views >= int(_d("tier_s_min_views")) and focal_ok):
        return "S", TIER_NAMES["S"]
    if (scale_mode in ("measured", "iris") and n_views >= int(_d("tier_a_min_views"))
            and y.size and float(y.max()) >= float(_d("tier_a_min_yaw_deg"))):
        return "A", TIER_NAMES["A"]
    return "B", TIER_NAMES["B"]


# =========================================================================== convenience
def _cap(status: str, cap: str | None) -> str:
    if cap is None:
        return status
    cap = "prior-driven" if cap == "prior_driven" else cap
    if cap not in _STATUS_RANK:
        raise ValueError(f"unknown status cap {cap!r}")
    return status if _STATUS_RANK[status] >= _STATUS_RANK[cap] else cap


def _views_used(stats: Sequence[Mapping[str, Any]], vis: np.ndarray) -> np.ndarray:
    """(V,) bool: views that contributed evidence (not frozen, at least one used observation)."""
    V = vis.shape[0]
    frozen = np.zeros(V, bool)
    if len(stats) == V:
        frozen = np.array([bool(st.get("frozen", False)) for st in stats], bool)
    return vis.any(axis=1) & ~frozen


def _per_view(value: Any, V: int, name: str) -> list:
    if value is None or np.ndim(value) == 0:
        return [value] * V
    out = list(value)
    if len(out) != V:
        raise ValueError(f"{name} has {len(out)} entries for {V} views")
    return out


def assess(result: Any, *, region_index: Mapping[str, Any] | None = None, ids: Sequence[str] | None = None,
           visibility: np.ndarray | None = None, view_yaw_deg: Sequence[float] | None = None,
           view_pitch_deg: Sequence[float] | None = None, gamma: float = 1.0,
           standard_prior_info: np.ndarray | None = None, standard_result: Any = None,
           prior_log_sigma: Any = None, views: Sequence[Any] | None = None,
           exif_log_sigma: Any = None, scale_mode: str = "prior", all_selfie: bool = False,
           status_caps: Mapping[str, str] | None = None, targets: Mapping[str, float] | None = None,
           bias: str = "gain") -> dict:
    """Every observability output of one solve, at prior weight 1 (DESIGN 4.12, 4.13, H1-H9).

    ``region_index`` (or ``ids`` for :func:`default_region_index`); ``visibility`` (V, N)
    defaults to ``result.inlier_mask``; yaw / pitch default to ``result.view_stats``;
    ``gamma`` from :func:`lovo_gamma`; ``prior_log_sigma`` / ``exif_log_sigma`` per view
    or scalar (focal status, tier S); without ``prior_log_sigma`` the focal priors are read
    from ``views`` (the ViewObs / PhotoLandmarks of the solve, :func:`focal_prior_log_sigmas`),
    and with neither the prior is unknown and a focal with sigma_logf >= 0.10 reads
    'prior_used' (H5, conservative); ``scale_mode`` 'measured' | 'iris' | 'prior';
    ``status_caps`` {region: status} lowers a region's status (occluder tags, e.g. beard
    -> jaw 'prior-driven'; never raises one; DESIGN D-31 caps 'ears' at 'prior-driven' by
    default, ``observability.ears_shape_prior_driven``); ``bias`` selects the
    definition-bias term of sigma_rep (:func:`reported_covariance`; 'gain' by default).

    **Prior weight 1 (H2).**  When ``result`` was solved with a widened prior (likeness
    mode, :func:`likeness_mode_prior`, or a rigidity slider), pass the standard solve of the
    same photos as ``standard_result``: every label, k, sigma_rep, coverage, focal status
    and the tier are then computed from it, so they are *identical* to
    ``assess(standard_result)`` whatever the widening (``result`` only supplies the
    presented geometry and is checked for the same landmark and view count).  A result
    flagged by :func:`likeness_mode_prior` (:data:`FLAG_LIKENESS`) is refused without
    ``standard_result``.  ``standard_prior_info`` (the standard prior information at
    ``result``, :func:`standard_prior_info`) is the WBS linearised alternative for a solve
    without a standard counterpart: it re-linearises at the widened estimate, so a region
    whose k sits within ~0.01 of 0.5 or 0.8 can change label (WP-16 review: 2-4 of 10
    frontal sets at 0.6-0.8 m).

    **Evidence only.**  Views that contributed no evidence (frozen: rejected by the robust
    schedule or empty, ``view_stats[v]['frozen']``, or without any used observation) are
    left out of the coverage rules and of the tier (their count, yaws, focal statuses and
    EXIF sigmas; DESIGN D-17), so an empty profile photo cannot lift a frontal set.

    Returns a dict with ``Sigma1`` and ``Sigma_prior`` (gauge-projected, mm^2),
    ``region_index``, ``region_k``, ``coverage``, ``coverage_ok``, ``sigma_rep_mm`` (N, 3;
    from Sigma1 with gamma, chi2_red and the definition bias), ``region_sigma_rep_mm``,
    ``targets``, ``region_status``, ``camera_status``, ``focal_statuses`` (every view),
    ``tier`` (code, name), ``scale`` {'mode', 'sigma_log', 'sigma_pct'}, ``gamma``,
    ``chi2_red``, ``n_views`` (views with evidence), ``n_views_total``, ``views_used``
    (V,) bool, ``yaws``, ``pitches`` (every view), ``status_caps``, ``cap_reasons``
    ({region: 'tag' | 'design_d31'}), ``bias`` and ``label_source`` ('result',
    'standard_result' or 'standard_prior_info').
    """
    kw = dict(region_index=region_index, ids=ids, visibility=visibility, view_yaw_deg=view_yaw_deg,
              view_pitch_deg=view_pitch_deg, gamma=gamma, prior_log_sigma=prior_log_sigma, views=views,
              exif_log_sigma=exif_log_sigma, scale_mode=scale_mode, all_selfie=all_selfie,
              status_caps=status_caps, targets=targets, bias=bias)
    if standard_result is not None:
        if standard_prior_info is not None:
            raise ValueError("pass standard_result or standard_prior_info, not both")
        if FLAG_LIKENESS in (getattr(standard_result, "flags", None) or []):
            raise ValueError("standard_result was itself solved with a widened (likeness-mode) prior")
        if np.shape(standard_result.X) != np.shape(result.X):
            raise ValueError("standard_result has a different landmark count than result")
        n_a = len(getattr(result, "cameras", []) or [])
        n_b = len(getattr(standard_result, "cameras", []) or [])
        if n_a != n_b:
            raise ValueError(f"standard_result has {n_b} views, result has {n_a}")
        out = _assess(standard_result, None, **kw)
        out["label_source"] = "standard_result"
        return out
    if FLAG_LIKENESS in (getattr(result, "flags", None) or []):
        raise ValueError("result was solved with a likeness-mode (widened) prior: pass the standard solve as "
                         "standard_result so labels stay at prior weight 1 (DESIGN H2)")
    out = _assess(result, standard_prior_info, **kw)
    out["label_source"] = "result" if standard_prior_info is None else "standard_prior_info"
    return out


def _assess(result: Any, standard_prior_info: np.ndarray | None, *, region_index, ids, visibility, view_yaw_deg,
            view_pitch_deg, gamma, prior_log_sigma, views, exif_log_sigma, scale_mode, all_selfie, status_caps,
            targets, bias) -> dict:
    X = np.asarray(result.X, float)
    N = len(X)
    if region_index is None:
        if ids is None:
            raise ValueError("assess needs region_index or ids")
        region_index = default_region_index(ids)
    region_index = {r: np.asarray(c, np.int64) for r, c in region_index.items()}
    stats = list(getattr(result, "view_stats", None) or [])
    if visibility is None:
        inl = getattr(result, "inlier_mask", None)
        if inl is None:
            raise ValueError("assess needs visibility (V, N) or result.inlier_mask")
        visibility = np.array([np.asarray(m, bool) for m in inl]).reshape(-1, N)
    vis = np.asarray(visibility, bool)
    V = vis.shape[0]
    yaws = [float(s["yaw_deg"]) for s in stats] if view_yaw_deg is None else [float(y) for y in view_yaw_deg]
    pitches = [float(s["pitch_deg"]) for s in stats] if view_pitch_deg is None else [float(p) for p in view_pitch_deg]
    if len(yaws) != V or len(pitches) != V:
        raise ValueError(f"{len(yaws)} yaws / {len(pitches)} pitches for {V} views")
    used = _views_used(stats, vis)
    vis_used = vis & used[:, None]                                  # frozen views carry no evidence
    S1 = posterior_at_prior_weight_one(result, standard_prior_info)
    Sq = prior_covariance(result, standard_prior_info)
    k = region_evidence(S1, Sq, region_index)
    cov = coverage_rules(yaws, pitches, vis_used, region_points(region_index))
    srep = sigma_rep(result, gamma, cov=S1, bias=bias, prior_info=standard_prior_info)
    rs = region_sigma_rep(srep, region_index)
    tg = dict(REGION_TARGET_MM)
    if targets:
        tg.update({str(a): float(b) for a, b in targets.items()})
    caps = {str(a): ("prior-driven" if b == "prior_driven" else str(b)) for a, b in (status_caps or {}).items()}
    reasons = {r: "tag" for r in caps}
    if bool(_d("ears_shape_prior_driven")) and "ears" in region_index:
        # DESIGN D-31: ear shape is not fitted in this version (silhouette only)
        if "ears" not in caps or _STATUS_RANK.get(caps["ears"], 0) < _STATUS_RANK["prior-driven"]:
            caps["ears"] = "prior-driven"
            reasons["ears"] = "design_d31"
    status, cok = {}, {}
    for r in region_index:
        cok[r] = coverage_ok(r, cov[r])
        st = region_status(k[r], cok[r], rs[r], tg.get(r, float("inf")), cov[r]["observed"])
        status[r] = _cap(st, caps.get(r))
    if prior_log_sigma is None and views is not None:
        if len(views) != len(stats):
            raise ValueError(f"views has {len(views)} entries for {len(stats)} views")
        prior_log_sigma = focal_prior_log_sigmas(views)
    cams = list(getattr(result, "cameras", []) or [])
    cs = camera_status(stats, prior_log_sigma, cams if len(cams) == len(stats) else None) if stats else []
    fstat = [c["focal_status"] for c in cs]
    zs = getattr(result, "zeta_sigma", None)
    scale = {"mode": scale_mode, "sigma_log": None if zs is None else float(zs),
             "sigma_pct": None if zs is None else float(100.0 * (math.exp(float(zs)) - 1.0))}
    ui = np.flatnonzero(used)
    f_used = [fstat[i] for i in ui] if len(fstat) == V else list(fstat)
    ex = exif_log_sigma
    if ex is not None and np.ndim(ex) > 0:
        ex = [_per_view(ex, V, "exif_log_sigma")[i] for i in ui]
    t = tier(scale_mode, status, int(used.sum()), [yaws[i] for i in ui], f_used, all_selfie, exif_log_sigma=ex)
    chi = getattr(result, "chi2_red", None)
    return {"Sigma1": S1, "Sigma_prior": Sq, "region_index": region_index, "region_k": k, "coverage": cov,
            "coverage_ok": cok, "sigma_rep_mm": srep, "region_sigma_rep_mm": rs, "targets": tg,
            "region_status": status, "camera_status": cs, "focal_statuses": fstat, "tier": t, "scale": scale,
            "gamma": float(gamma), "chi2_red": None if chi is None else float(chi), "n_views": int(used.sum()),
            "n_views_total": V, "views_used": used.tolist(), "yaws": yaws, "pitches": pitches,
            "status_caps": caps, "cap_reasons": reasons, "bias": bias}
