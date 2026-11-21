"""Metric scale: scale-reference terms, iris limbus fit, population size source and scale report.

DESIGN D-03, 4.7, section 5 H4 (WBS WP-15).  Absolute size is unobservable from photos
alone (a head twice as large twice as far away gives the same images), so the bundle's
metric scale comes from exactly one *population* source plus any number of *metric*
references (DESIGN D-03, rec BA-10, anat R3.4):

* population (exactly one, :func:`population_scale_setup`): ``'global_size'`` = the
  bundle's explicit log-scale prior zeta ~ N(0, 0.045^2) (DESIGN D-03), or ``'ipd'`` =
  :class:`IpdTerm` (63 +/- 3.8 mm, vergence-corrected) with the zeta prior made flat.
  Requesting both raises ``ValueError`` (no double counting, DESIGN 4.7 "may replace it,
  never join it").
* metric references, all :class:`~face3d.solve.terms.Term` blocks for
  :func:`~face3d.solve.bundle.bundle_adjust`: :class:`ChordTerm` (caliper or tape),
  :class:`CardTerm` (ID-1 card held against a landmark) and :class:`IrisTerm` (visible
  iris diameter with a shared D ~ N(11.8, 0.6^2) mm, used only when :func:`iris_usable`).

Reported scale (H4, :func:`reported_scale` -> :func:`scale_report`): the printed value is the
**metric log-size of the reconstruction**, zeta = log s with s the Umeyama similarity scale
mapping a reference shape (the template / prior mean; the same definition as the test bed's
``log_scale_true``) onto the solved landmarks (:func:`log_size`), and the printed +/- % is an SD
that covers the error of that value: the **reference component** (:func:`scale_mode`: the data
are blind to scaling the head and every camera translation together, so only the metric
references and the population source pin it; iris alone 5.1 %, iris + population 3.4 %, a
0.5 mm caliper 0.5 / L, DESIGN 4.7) plus the **shape** part of the log-size (points only the
prior places, focal, pose; chi^2-inflated as sigma_rep) and the landmarks' **definition bias**
(D-06).  The reference component is common to every length of the reconstruction, but each
length adds its own shape error, so it is not the size uncertainty: with a caliper on zy-zy the
WP-01 test bed's log-size SD is ~2.5 % (reference ~1.5 % once the end points' definition bias is
in the chord, shape ~1.4 % x chi^2), not the caliper's 0.4 %.  The bundle's own zeta parameter
is the subject's size *relative to the prior mean*; its posterior keeps the shape-prior
ambiguity (how much of a given shape is "size") even when the metric size is known exactly, so
it is not the reported scale either.

Conventions
-----------
* Head frame in mm (+x subject's left, +y up, +z out of the face); OpenCV cameras
  X_c = R X + t; image pixels with the origin at the top-left *corner*, pixel (i, j)
  centred at (j + 1/2, i + 1/2) for row i, column j (DESIGN 3.1).
* Terms follow the :mod:`face3d.solve.terms` protocol; camera blocks ``'cam:<v>'`` are the
  inverse-depth blocks (omega, tau, rho_per_m[, a]) with rho stored in 1/m, so
  d/d rho_param = 1e-3 d/d rho_mm (WP-10 integration note (b)).  For a view whose focal is
  shared *exactly* by a focal group ('hard' block, s = e^phi_G rho) the derivative with
  respect to phi_G goes to the key named by ``phi_keys[view]`` (:func:`focal_phi_keys`).
* Log-scales are natural logs (0.01 ~ 1 %).

Numeric defaults are registered under the ``scale`` namespace of :mod:`face3d.core.config`
with badges and sources; the iris mean is verified (✅), every other value is provisional
(🧠 / ↔️ / 🆕) until the M7 calibration (DESIGN 8).
numpy + stdlib only.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import numpy as np

from ..core.config import Default, register_defaults
from ..geometry.procrustes import umeyama
from .bundle import BUNDLE, RHO_MM_PER_PARAM, ScaleConfig

__all__ = [
    "SCALE", "ChordTerm", "CardTerm", "IrisTerm", "IpdTerm", "vergence_correction_mm", "iris_usable",
    "fit_limbus", "limbus_is_sharp", "iris_observation", "POPULATION_SOURCES", "population_scale_source",
    "population_scale_setup", "focal_phi_keys", "scale_mode", "reported_scale", "log_size", "log_size_gradient",
    "log_size_posterior",
    "scale_source", "chord_scale_source", "iris_scale_source", "card_scale_source", "fuse_log_scale",
    "scale_report", "FLAG_SCALE_CONFLICT", "METRIC_KINDS",
]

_OK = "✅"
_PAGE = "\U0001F4C4"
_BRAIN = "\U0001F9E0"
_ARROWS = "↔️"
_NEW = "\U0001F195"

SCALE = register_defaults("scale", {
    # ---- caliper / tape chord (DESIGN 4.7)
    "chord_sigma_mm": Default(0.5, _BRAIN, "DESIGN 4.7 caliper or tape chord sigma 0.5 mm (research/anatomy/README "
                              "'one caliper distance ... error ~0.5 mm')", "mm", (1e-6, None)),
    "chord_offset_mm": Default(0.0, _ARROWS, "DESIGN 4.7 pressed-landmark offset o, default 0 (contested +2-5 mm "
                               "for bony points)", "mm", (None, None)),
    # ---- ID-1 card (DESIGN 4.7)
    "card_length_mm": Default(85.60, _PAGE, "DESIGN 4.7 ID-1 card chord 85.60 mm (ISO/IEC 7810 ID-1 width)", "mm",
                              (1.0, None)),
    "card_sigma_mm": Default(0.5, _NEW, "DESIGN 4.7 card chord 85.60 +/- 0.5 mm", "mm", (1e-6, None)),
    "card_depth_sigma_mm": Default(10.0, _NEW, "DESIGN 4.7 'held against landmark k' depth prior sigma 10 mm", "mm",
                                   (1e-6, None)),
    "card_sigma_px": Default(1.0, _NEW, "WBS WP-15 card corner reprojection sigma 1 px", "px", (1e-6, None)),
    "card_tilt_sigma_mm": Default(10.0, _NEW, "WP-15 extension of the card term: corner depth difference / 10 mm "
                                  "(card held roughly parallel to the image plane; without it the chord is met by "
                                  "tilting the card and the scale is lost)", "mm", (1e-6, None)),
    # ---- iris (DESIGN 4.7; anat R3.4; research/anatomy/README C-6)
    "iris_mean_mm": Default(11.8, _OK, "DESIGN 4.7 visible iris (corneal) diameter 11.8 mm (research/anatomy/"
                            "eye-region.md pooled 11.84 mm; README C-6)", "mm", (5.0, 20.0)),
    "iris_sd_mm": Default(0.6, _ARROWS, "DESIGN 4.7 iris SD 0.6 mm (contested: pooled SD 0.79, single-device "
                          "0.36-0.43; research/anatomy/README C-6)", "mm", (1e-6, None)),
    "iris_min_px": Default(20.0, _BRAIN, "DESIGN 4.7 / 4.1 Q-SMALL: iris scale only at >= 20 px (com R1.4)", "px",
                           (1.0, None)),
    # ---- limbus fit (DESIGN 4.7 'radial gradient profiles ... circle by IRLS'; WBS WP-15)
    "limbus_n_rays": Default(64, _NEW, "WBS WP-15 limbus fit: 64 rays", "", (8, 4096)),
    "limbus_search_lo": Default(0.6, _NEW, "WBS WP-15 limbus fit: search radii 0.6-1.5 x r_guess", "",
                                (0.05, 1.0)),
    "limbus_search_hi": Default(1.5, _NEW, "WBS WP-15 limbus fit: search radii 0.6-1.5 x r_guess", "",
                                (1.0, 10.0)),
    "limbus_exclude_deg": Default(40.0, _NEW, "WBS WP-15 limbus fit: rays within +/-40 deg of vertical skipped "
                                  "(upper and lower lids cover the limbus; research/anatomy/eye-region.md)", "deg",
                                  (0.0, 89.0)),
    "limbus_step_px": Default(0.25, _NEW, "WP-15 implementation choice: radial sampling step 0.25 px", "px",
                              (0.01, 2.0)),
    "limbus_deriv_halfwidth_px": Default(1.0, _NEW, "WP-15 implementation choice: radial derivative by central "
                                         "differences over +/-1 px (smooths pixel noise before the peak search)",
                                         "px", (0.01, 10.0)),
    "limbus_huber_k": Default(1.345, _PAGE, "WBS WP-15 IRLS Huber 1.345 sigma (rec BA-5 constants; "
                              "deformation-fitting-math)", "sigma", (0.1, 10.0)),
    "limbus_irls_rounds": Default(3, _NEW, "WBS WP-15 limbus fit: 3 IRLS rounds", "", (0, 50)),
    "limbus_sigma_floor_px": Default(0.5, _BRAIN, "DESIGN 4.7 limbus sigma floored at 0.5 px (rec OPT-4 limbus "
                                     "0.5-1 px)", "px", (0.0, None)),
    "limbus_noise_exclude_px": Default(3.0, _NEW, "WP-15 implementation choice: the scleral noise band starts 3 px "
                                       "outside the fitted edge (the blurred edge stays out of the noise statistic)",
                                       "px", (0.0, 50.0)),
    "limbus_noise_band_min_px": Default(6.0, _NEW, "WP-15 implementation choice: the noise band on the sclera "
                                        "is at least 6 px wide", "px", (1.0, 100.0)),
    "limbus_noise_band_frac": Default(0.5, _NEW, "WP-15 implementation choice: the noise band on the sclera is "
                                      "0.5 r wide (eye corners lie ~2.5 iris radii from the centre, eye-region.md)",
                                      "", (0.0, 5.0)),
    "limbus_noise_margin_deg": Default(10.0, _NEW, "WP-15 implementation choice: the noise statistic uses the "
                                       "kept sectors narrowed by 10 deg (lid edges stay out of it)", "deg",
                                       (0.0, 80.0)),
    "limbus_min_peak_frac": Default(0.6, _NEW, "WP-15 implementation choice: a ray whose strongest edge is below "
                                    "0.6 x the median ray's is treated as occluded (lid, lashes) and not used",
                                    "", (0.0, 1.0)),
    "limbus_min_rays": Default(8, _NEW, "WP-15 implementation choice: a circle fit needs >= 8 rays with an edge",
                               "", (3, 4096)),
    # Usable-limbus gate (DESIGN 4.7 "the limbus is sharp"), two conditions.  Calibrated on the
    # synthetic limbus of tests/test_nuisances.py over iris/sclera contrast 0.15-0.60, pixel noise
    # SD 0.005-0.05, radius 12-30 px, with and without lids, blur 0-4 px (WP-15 review):
    # * the edge width sigma_e (blur + pixel footprint) <= 2.2 px: blur <= 1.5 px gives
    #   sigma_e <= 1.7 px and blur 3 px >= 2.75 px wherever the edge stands out of the noise;
    # * the contrast-to-noise statistic 'sharpness' (WBS definition) >= 1.0: below it the width
    #   estimate itself is noise (blur-3 px edges then read 0.3-1.9 px) and the radius error
    #   reaches 1-4 px.
    "limbus_sharpness_min": Default(1.0, _NEW, "WP-15 calibration on synthetic limbus images (contrast 0.15-0.60, "
                                    "noise SD 0.005-0.05, radius 12-30 px): below 1.0 the edge width and the radius "
                                    "are noise-dominated (DESIGN 4.7 'sharp limbus')", "", (0.0, None)),
    "limbus_edge_sigma_max_px": Default(2.2, _NEW, "WP-15 calibration on synthetic limbus images (contrast 0.15-0.60, "
                                        "noise SD 0.005-0.05, radius 12-30 px): edge-profile SD of blur <= 1.5 px "
                                        "<= 1.7 px, of blur 3 px >= 2.75 px (DESIGN 4.7 'sharp limbus')", "px",
                                        (0.0, None)),
    "limbus_width_inner_frac": Default(0.4, _NEW, "WP-15 implementation choice: the edge-width profile starts "
                                       "0.4 r inside the limbus (the pupil edge sits at ~0.4 r; eye-region.md)", "",
                                       (0.05, 0.9)),
    "limbus_width_inner_max_px": Default(8.0, _NEW, "WP-15 implementation choice: edge-width profile at most 8 px "
                                         "inside the limbus", "px", (1.0, 100.0)),
    "limbus_width_outer_frac": Default(0.6, _NEW, "WP-15 implementation choice: the edge-width profile ends 0.6 r "
                                       "outside the limbus (eye corners ~2.5 r from the centre)", "", (0.05, 2.0)),
    "limbus_width_outer_max_px": Default(10.0, _NEW, "WP-15 implementation choice: edge-width profile at most "
                                         "10 px outside the limbus", "px", (1.0, 100.0)),
    # ---- population sources (DESIGN D-03, 4.7)
    "ipd_mean_mm": Default(63.0, _BRAIN, "DESIGN 4.7 IPD 63 mm far gaze (rec BA-10; bl section 4)", "mm",
                           (30.0, 90.0)),
    "ipd_sd_mm": Default(3.8, _BRAIN, "DESIGN 4.7 IPD SD 3.8 mm (rec BA-10, OPT-4)", "mm", (1e-6, None)),
    "vergence_ipd_mm_at_350": Default(2.0, _BRAIN, "DESIGN 4.7 / bl C3: vergence shrinks IPD ~2 mm at 0.35 m",
                                      "mm", (0.0, 10.0)),
    "vergence_cap_mm": Default(2.5, _NEW, "WBS WP-15 vergence correction capped at 2.5 mm", "mm", (0.0, 10.0)),
    "vergence_near_mm": Default(1000.0, _BRAIN, "research/blender/reference-camera-setup.md 'IPD vergence-"
                                "corrected when z < 1 m'", "mm", (0.0, None)),
    "free_zeta_sigma_log": Default(10.0, _NEW, "WP-15 implementation choice: a flat zeta prior (sigma 10 in log) "
                                   "stands in for 'no global-size prior' when IPD (or nothing) is the population "
                                   "source", "log", (1.0, None)),
    # ---- report (DESIGN 4.7, H4)
    "conflict_rel": Default(0.01, _BRAIN, "DESIGN 4.7: references disagreeing by > 1 % (and > 2 sigma) raise "
                            "S-CONFLICT (rec BA-10 'warn at > 1 % disagreement')", "log", (0.0, 1.0)),
    "conflict_nsigma": Default(2.0, _BRAIN, "DESIGN 4.7: S-CONFLICT needs > 2 combined sigma", "sigma",
                               (0.0, None)),
})
_S = {k: SCALE[k].value for k in SCALE}

#: Finding code for metric scale references that disagree (DESIGN 4.7).
FLAG_SCALE_CONFLICT = "S-CONFLICT"
#: Population size sources (DESIGN D-03, 4.7): exactly one may be active.
POPULATION_SOURCES: tuple[str, ...] = ("global_size", "ipd")
#: Metric reference kinds (scale mode 'measured' for caliper/card, 'iris' for iris).
METRIC_KINDS: tuple[str, ...] = ("caliper", "card", "iris")
_MEASURED_KINDS = ("caliper", "card")
_LABEL_ORDER = ("caliper", "card", "iris", "ipd", "global_size")
_LABEL_NAME = {"caliper": "caliper", "card": "card", "iris": "iris", "ipd": "ipd", "global_size": "population"}
_KIND_ALIASES = {"tape": "caliper", "chord": "caliper", "population": "global_size", "global": "global_size"}
_RHO_MM_PER_PARAM = RHO_MM_PER_PARAM      # rho is stored in 1/m inside the bundle (WP-10 note (b))


# =========================================================================== camera helpers
def _view_block(state: Any, v: int, phi_keys: Mapping[int, str] | None, who: str) -> dict:
    """Inverse-depth block of view ``v`` from a SolverState, plus the phi key for a 'hard' view."""
    if not 0 <= int(v) < state.n_views:
        raise ValueError(f"{who}: view {v} out of range (bundle has {state.n_views} views)")
    d = state.invdepth[int(v)]
    out = {"R": np.asarray(d["R"], float), "tau": np.asarray(d["tau"], float), "rho": float(d["rho"]),
           "s": float(d["s"]), "kind": d["kind"], "block": tuple(d["block"]), "phi_key": None}
    if d["kind"] == "hard":
        key = None if phi_keys is None else phi_keys.get(int(v))
        if key is None:
            raise ValueError(f"{who}: view {v} shares its focal exactly with a focal group ('hard' block, "
                             f"s = e^phi rho); pass phi_keys (see face3d.solve.scale.focal_phi_keys)")
        out["phi_key"] = str(key)
    return out


def _proj_and_jac(Y_world: np.ndarray, blk: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray,
                                                          np.ndarray]:
    """Inverse-depth projection of points (m, 3) (no principal point added) and its derivatives.

    Returns ``(q, dq_dY, dq_domega, dq_dtau_rho_a, dq_dphi)`` with q = s (Y_c,xy + tau) /
    (1 + rho Y_c,z), Y_c = R Y; dq_dY (m, 2, 3) w.r.t. the world point, dq_domega (m, 2, 3)
    w.r.t. the left rotation increment, dq_dtau_rho_a (m, 2, 4) w.r.t. (tau_x, tau_y,
    rho_param [1/m], a) (the a column is meaningful for 'free' blocks only) and dq_dphi (m, 2)
    (for 'hard' blocks).
    """
    R, tau, rho, s, kind = blk["R"], blk["tau"], blk["rho"], blk["s"], blk["kind"]
    Yc = np.asarray(Y_world, float) @ R.T
    den = 1.0 + rho * Yc[:, 2]
    num = Yc[:, :2] + tau
    q = s * num / den[:, None]
    m = len(Yc)
    A = np.zeros((m, 2, 3))                       # dq / dY_c
    A[:, 0, 0] = s / den
    A[:, 1, 1] = s / den
    A[:, :, 2] = -(q * rho / den[:, None])
    dY = np.einsum("mij,jk->mik", A, R)
    S = np.zeros((m, 3, 3))                       # [Y_c]_x
    S[:, 0, 1], S[:, 0, 2] = -Yc[:, 2], Yc[:, 1]
    S[:, 1, 0], S[:, 1, 2] = Yc[:, 2], -Yc[:, 0]
    S[:, 2, 0], S[:, 2, 1] = -Yc[:, 1], Yc[:, 0]
    dW = -np.einsum("mij,mjk->mik", A, S)         # dY_c/domega = -[Y_c]_x
    dT = np.zeros((m, 2, 4))
    dT[:, 0, 0] = s / den
    dT[:, 1, 1] = s / den
    if kind == "free":
        drho = -q * (Yc[:, 2] / den)[:, None]
        dT[:, :, 3] = q
    else:                                         # s = k rho (k = e^phi or the fixed focal)
        drho = (s / rho) * num / (den ** 2)[:, None]
    dT[:, :, 2] = drho * _RHO_MM_PER_PARAM
    dphi = q.copy() if kind == "hard" else np.zeros_like(q)
    return q, dY, dW, dT, dphi


def _cam_cols(blk: dict, dW: np.ndarray, dT: np.ndarray) -> np.ndarray:
    """(m, 2, block_size) camera-block derivative in the block order (omega, tau, rho[, a])."""
    m = dW.shape[0]
    size = len(blk["block"])
    J = np.zeros((m, 2, size))
    J[:, :, 0:3] = dW
    J[:, :, 3:6] = dT[:, :, 0:3]
    if size == 7:
        J[:, :, 6] = dT[:, :, 3]
    return J


def _depth_rows(Y_world: np.ndarray, R: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(R Y)_z of points (m, 3) and its derivatives w.r.t. Y (m, 3) and the left increment omega (m, 3)."""
    Yc = np.asarray(Y_world, float) @ R.T
    dY = np.broadcast_to(R[2], Yc.shape).copy()
    dW = np.column_stack([Yc[:, 1], -Yc[:, 0], np.zeros(len(Yc))])
    return Yc[:, 2], dY, dW


def focal_phi_keys(views: Sequence[Any]) -> dict[int, str]:
    """``{view: 'phi_<j>'}`` for every view whose block is 'hard' (focal shared exactly by a group).

    Mirrors the parameter layout of :func:`face3d.solve.bundle.bundle_adjust` (WBS WP-10):
    focal groups get one phi each in order of first appearance among the views with
    ``estimate_focal`` and a ``focal_group``; a view is 'hard' when it is grouped and its
    ``focal_tie_sigma`` is None.  ``views`` are :class:`~face3d.solve.bundle.ViewObs` (or any
    objects with those three attributes) in bundle order.
    """
    order: dict[Any, int] = {}
    out: dict[int, str] = {}
    for k, v in enumerate(views):
        if not getattr(v, "estimate_focal", True) or getattr(v, "focal_group", None) is None:
            continue
        g = v.focal_group
        if g not in order:
            order[g] = len(order)
        if getattr(v, "focal_tie_sigma", None) is None:
            out[k] = f"phi_{order[g]}"
    return out


# =========================================================================== terms
def _definition_pair(definition_sigma_mm: Any) -> tuple[float, float]:
    """(sigma_a, sigma_b) mm from a scalar (both end points) or a pair; finite and >= 0."""
    d = np.broadcast_to(np.asarray(definition_sigma_mm, float), (2,))
    if not (np.all(np.isfinite(d)) and np.all(d >= 0.0)):
        raise ValueError("definition_sigma_mm must be finite and >= 0 (a scalar or one value per end point)")
    return float(d[0]), float(d[1])


class ChordTerm:
    """Caliper or tape chord between two landmarks (DESIGN 4.7).

    Residual (||X_a - X_b|| - L - o) / sigma (mm), no own parameters; ``length_mm`` L is
    the measured distance, ``offset_mm`` o the pressed-landmark offset (default 0 ↔️,
    +2-5 mm for bony points), ``sigma_mm`` the measurement SD (default 0.5 mm 🧠).  The row
    is data (``is_prior`` False).

    The caliper measures the *anatomical* points while the bundle's X_a, X_b are the
    *detected* landmark definitions, which carry a per-subject definition bias that no number
    of views removes (DESIGN D-06, H3).  ``definition_sigma_mm`` (a scalar for both end points
    or a pair; e.g. ``NoiseModel(kinds).sigma_def_mm()[[a, b]]``, 1.5 mm for extremal points
    such as zygion) adds the bias along the chord, sigma_a^2 + sigma_b^2 (isotropic per-axis SD),
    to the residual's variance: sigma = sqrt(sigma_mm^2 + sigma_a^2 + sigma_b^2).  Leaving it at
    0 (the WBS residual) trusts the detected end points exactly and overstates the scale
    precision whenever the detector has a definition bias (zy-zy: 0.36 % instead of ~1.5 %).
    """

    is_prior = False

    def __init__(self, a_idx: int, b_idx: int, length_mm: float, sigma_mm: float = _S["chord_sigma_mm"],
                 offset_mm: float = _S["chord_offset_mm"], *, definition_sigma_mm: Any = 0.0,
                 name: str = "chord"):
        self.a, self.b = int(a_idx), int(b_idx)
        if self.a == self.b:
            raise ValueError("ChordTerm needs two different landmarks")
        self.L, self.sigma_mm, self.offset = float(length_mm), float(sigma_mm), float(offset_mm)
        if not (self.L > 0 and self.sigma_mm > 0 and math.isfinite(self.offset)):
            raise ValueError("ChordTerm needs length_mm > 0, sigma_mm > 0 and a finite offset_mm")
        self.definition_sigma_mm = _definition_pair(definition_sigma_mm)
        #: residual SD (mm): measurement and end-point definition bias in quadrature
        self.sigma = math.sqrt(self.sigma_mm ** 2 + sum(x * x for x in self.definition_sigma_mm))
        self.name = str(name)

    def n_params(self) -> int:
        return 0

    def init_params(self, state: Any) -> np.ndarray:
        return np.zeros(0)

    def residuals(self, state: Any, p: np.ndarray) -> np.ndarray:
        d = state.X[self.a] - state.X[self.b]
        return np.array([(float(np.linalg.norm(d)) - self.L - self.offset) / self.sigma])

    def jacobian(self, state: Any, p: np.ndarray) -> dict:
        d = state.X[self.a] - state.X[self.b]
        n = float(np.linalg.norm(d))
        u = d / max(n, 1e-12) / self.sigma
        J = np.zeros((1, 3 * len(state.X)))
        J[0, 3 * self.a:3 * self.a + 3] = u
        J[0, 3 * self.b:3 * self.b + 3] = -u
        return {"X": J}


class CardTerm:
    """ID-1 card held against a landmark in one view (DESIGN 4.7).

    Own parameters: the two 3D card corners C1, C2 (head frame, mm; 6 parameters) at the
    ends of a long edge whose image positions are ``corner_uv`` (2, 2) px in view ``view``.
    Residual rows (all data, ``is_prior`` False):

    * 4 corner reprojections (u(C_k) - corner_uv_k) / sigma_px in the view's inverse-depth
      camera;
    * the chord (||C1 - C2|| - length_mm) / sigma_mm (85.60 +/- 0.5 mm, ISO/IEC 7810 ID-1);
    * the contact depth (mean corner depth - depth of landmark ``touch_idx``) / depth_sigma_mm
      in that camera ("held against landmark k", sigma 10 mm 🆕); the camera distance 1/rho
      cancels, so the row is (mean (R C_k)_z - (R X_k)_z) / depth_sigma;
    * with ``tilt_sigma_mm`` (default 10 mm 🆕; None leaves it out) the flatness row
      ((R C1)_z - (R C2)_z) / tilt_sigma: the card is held roughly parallel to the image
      plane.  Without it the card's tilt is free and the chord can be met by tilting the card
      instead of moving it: whenever the head is estimated smaller than the card implies, the
      card then carries no scale information (found in WP-15 testing; a WBS-spec extension).

    ``phi_keys`` (:func:`focal_phi_keys`) is needed when the view's focal is shared exactly
    by a focal group.  The card corners are initialised by back-projecting ``corner_uv`` to
    the touch landmark's depth.
    """

    is_prior = False

    def __init__(self, view: int, corner_uv: Any, touch_idx: int, length_mm: float = _S["card_length_mm"],
                 sigma_mm: float = _S["card_sigma_mm"], depth_sigma_mm: float = _S["card_depth_sigma_mm"],
                 sigma_px: float = _S["card_sigma_px"], *, tilt_sigma_mm: float | None = _S["card_tilt_sigma_mm"],
                 name: str = "card", phi_keys: Mapping[int, str] | None = None):
        self.view = int(view)
        self.uv = np.asarray(corner_uv, float).reshape(2, 2).copy()
        if not np.all(np.isfinite(self.uv)):
            raise ValueError("CardTerm corner_uv must be finite")
        self.k = int(touch_idx)
        self.L, self.sigma, self.depth_sigma, self.sigma_px = (float(length_mm), float(sigma_mm),
                                                               float(depth_sigma_mm), float(sigma_px))
        self.tilt_sigma = None if tilt_sigma_mm is None else float(tilt_sigma_mm)
        if not (self.L > 0 and self.sigma > 0 and self.depth_sigma > 0 and self.sigma_px > 0
                and (self.tilt_sigma is None or self.tilt_sigma > 0)):
            raise ValueError("CardTerm lengths and sigmas must be > 0")
        self.name = str(name)
        self.phi_keys = None if phi_keys is None else dict(phi_keys)

    def n_params(self) -> int:
        return 6

    def init_params(self, state: Any) -> np.ndarray:
        cam = state.cameras[self.view]
        z = float(cam.depth(state.X[self.k][None])[0])
        z = z if z > 0 else float(cam.t[2])
        rays = np.column_stack([(self.uv[:, 0] - cam.cx) / cam.f, (self.uv[:, 1] - cam.cy) / cam.f, np.ones(2)])
        Xc = rays * z
        return ((Xc - cam.t) @ cam.R).reshape(-1)

    def _cx(self, state: Any) -> np.ndarray:
        like = state.cameras[self.view]
        return np.array([like.cx, like.cy])

    def residuals(self, state: Any, p: np.ndarray) -> np.ndarray:
        blk = _view_block(state, self.view, self.phi_keys, f"CardTerm {self.name!r}")
        C = np.asarray(p, float).reshape(2, 3)
        q = _proj_and_jac(C, blk)[0]
        r_uv = ((q + self._cx(state)) - self.uv) / self.sigma_px
        r_ch = (float(np.linalg.norm(C[0] - C[1])) - self.L) / self.sigma
        zc, _, _ = _depth_rows(C, blk["R"])
        zk, _, _ = _depth_rows(state.X[self.k][None], blk["R"])
        rows = [r_ch, (0.5 * (zc[0] + zc[1]) - zk[0]) / self.depth_sigma]
        if self.tilt_sigma is not None:
            rows.append((zc[0] - zc[1]) / self.tilt_sigma)
        return np.concatenate([r_uv.reshape(-1), rows])

    def jacobian(self, state: Any, p: np.ndarray) -> dict:
        blk = _view_block(state, self.view, self.phi_keys, f"CardTerm {self.name!r}")
        C = np.asarray(p, float).reshape(2, 3)
        N = len(state.X)
        m = 6 if self.tilt_sigma is None else 7
        _, dY, dW, dT, dphi = _proj_and_jac(C, blk)
        Js = np.zeros((m, 6))
        Jc = np.zeros((m, len(blk["block"])))
        Jx = np.zeros((m, 3 * N))
        cam = _cam_cols(blk, dW, dT) / self.sigma_px        # (2, 2, size)
        for k in range(2):
            Js[2 * k:2 * k + 2, 3 * k:3 * k + 3] = dY[k] / self.sigma_px
            Jc[2 * k:2 * k + 2] = cam[k]
        d = C[0] - C[1]
        u = d / max(float(np.linalg.norm(d)), 1e-12) / self.sigma
        Js[4, 0:3], Js[4, 3:6] = u, -u
        _, dYc, dWc = _depth_rows(C, blk["R"])
        _, dYk, dWk = _depth_rows(state.X[self.k][None], blk["R"])
        Js[5, 0:3] = 0.5 * dYc[0] / self.depth_sigma
        Js[5, 3:6] = 0.5 * dYc[1] / self.depth_sigma
        Jx[5, 3 * self.k:3 * self.k + 3] = -dYk[0] / self.depth_sigma
        Jc[5, 0:3] = (0.5 * (dWc[0] + dWc[1]) - dWk[0]) / self.depth_sigma
        if self.tilt_sigma is not None:
            Js[6, 0:3] = dYc[0] / self.tilt_sigma
            Js[6, 3:6] = -dYc[1] / self.tilt_sigma
            Jc[6, 0:3] = (dWc[0] - dWc[1]) / self.tilt_sigma
        out = {"self": Js, f"cam:{self.view}": Jc, "X": Jx}
        if blk["kind"] == "hard":
            Jp = np.zeros((m, 1))
            Jp[0:4, 0] = (dphi / self.sigma_px).reshape(-1)
            out[blk["phi_key"]] = Jp
        return out


class IrisTerm:
    """Visible iris diameter as a metric ruler with one shared diameter D (DESIGN 4.7).

    ``obs``: list of ``(view, eye, d_px, sigma_px)`` with eye 'L' or 'R' (subject's side),
    d_px the limbus diameter in px (:func:`fit_limbus`: 2 x radius) and sigma_px its SD;
    ``eye_idx`` = {'L': index, 'R': index} of the pupil landmarks; ``prior_mm`` = (11.8, 0.6)
    (DESIGN 4.7: ✅ mean, ↔️ SD).  Own parameter: D (mm).  Rows: the prior (D - 11.8) / 0.6 and
    per observation (f_v D / z_eye,v - d_px) / sigma_px, z_eye,v the pupil landmark's depth in
    camera v; in inverse-depth form f D / z = s D / (1 + rho (R X_p)_z).  All rows are data
    (``is_prior`` False; the single prior row is negligible in chi^2).  Use only observations
    that pass :func:`iris_usable`.
    """

    is_prior = False

    def __init__(self, obs: Sequence[tuple], eye_idx: Mapping[str, int],
                 prior_mm: tuple[float, float] = (_S["iris_mean_mm"], _S["iris_sd_mm"]), *, name: str = "iris",
                 phi_keys: Mapping[int, str] | None = None):
        rows = []
        for o in obs:
            v, eye, d, s = o
            if eye not in ("L", "R"):
                raise ValueError(f"IrisTerm: eye must be 'L' or 'R', not {eye!r}")
            if eye not in eye_idx:
                raise ValueError(f"IrisTerm: no pupil landmark index for eye {eye!r}")
            d, s = float(d), float(s)
            if not (d > 0 and s > 0 and math.isfinite(d) and math.isfinite(s)):
                raise ValueError("IrisTerm: d_px and sigma_px must be finite and > 0")
            rows.append((int(v), eye, d, s))
        if not rows:
            raise ValueError("IrisTerm needs at least one observation")
        self.obs = rows
        self.eye_idx = {k: int(i) for k, i in eye_idx.items()}
        self.mu, self.sd = float(prior_mm[0]), float(prior_mm[1])
        if not (self.mu > 0 and self.sd > 0):
            raise ValueError("IrisTerm prior must have mean > 0 and SD > 0")
        self.name = str(name)
        self.phi_keys = None if phi_keys is None else dict(phi_keys)

    def n_params(self) -> int:
        return 1

    def init_params(self, state: Any) -> np.ndarray:
        """Mean of the per-observation diameters d_px z / f at the current state (else the prior mean)."""
        vals = []
        for v, eye, d, _ in self.obs:
            blk = _view_block(state, v, self.phi_keys, f"IrisTerm {self.name!r}")
            Yz = float(state.X[self.eye_idx[eye]] @ blk["R"][2])
            g1 = blk["s"] / (1.0 + blk["rho"] * Yz)          # f / z, px per mm at the pupil
            if g1 > 0 and math.isfinite(g1):
                vals.append(d / g1)
        return np.array([float(np.mean(vals)) if vals else self.mu])

    def residuals(self, state: Any, p: np.ndarray) -> np.ndarray:
        D = float(p[0])
        out = [(D - self.mu) / self.sd]
        for v, eye, d, s in self.obs:
            blk = _view_block(state, v, self.phi_keys, f"IrisTerm {self.name!r}")
            Yz = float(state.X[self.eye_idx[eye]] @ blk["R"][2])
            out.append((blk["s"] * D / (1.0 + blk["rho"] * Yz) - d) / s)
        return np.array(out)

    def jacobian(self, state: Any, p: np.ndarray) -> dict:
        D = float(p[0])
        m = 1 + len(self.obs)
        N = len(state.X)
        Js = np.zeros((m, 1))
        Js[0, 0] = 1.0 / self.sd
        Jx = np.zeros((m, 3 * N))
        cams: dict[str, np.ndarray] = {}
        for r, (v, eye, _d, s) in enumerate(self.obs, start=1):
            blk = _view_block(state, v, self.phi_keys, f"IrisTerm {self.name!r}")
            R, rho, sv = blk["R"], blk["rho"], blk["s"]
            i = self.eye_idx[eye]
            Y = R @ state.X[i]
            den = 1.0 + rho * Y[2]
            g = sv * D / den
            Js[r, 0] = sv / den / s
            dg_dYz = -sv * D * rho / den ** 2
            Jx[r, 3 * i:3 * i + 3] += dg_dYz * R[2] / s
            key = f"cam:{v}"
            Jc = cams.setdefault(key, np.zeros((m, len(blk["block"]))))
            Jc[r, 0:3] = dg_dYz * np.array([Y[1], -Y[0], 0.0]) / s
            if blk["kind"] == "free":
                Jc[r, 5] = -sv * D * Y[2] / den ** 2 * _RHO_MM_PER_PARAM / s
                Jc[r, 6] = g / s
            else:
                Jc[r, 5] = (sv / rho) * D / den ** 2 * _RHO_MM_PER_PARAM / s
            if blk["kind"] == "hard":
                Jp = cams.setdefault(blk["phi_key"], np.zeros((m, 1)))
                Jp[r, 0] += g / s
        out = {"self": Js, "X": Jx}
        out.update(cams)
        return out


def vergence_correction_mm(z_mm: float | None, *, near_mm: float = _S["vergence_near_mm"],
                           at_350_mm: float = _S["vergence_ipd_mm_at_350"], cap_mm: float = _S["vergence_cap_mm"]
                           ) -> float:
    """IPD shrinkage by vergence for a near view: min(2.5, 2.0 x 350 / z) mm when z < 1 m, else 0.

    DESIGN 4.7 / bl C3 ("vergence shrinks IPD ~2 mm at 0.35 m"), capped at 2.5 mm (WBS WP-15);
    ``z_mm`` is the camera-to-eye distance in mm (None: no correction).
    """
    if z_mm is None:
        return 0.0
    z = float(z_mm)
    if not z > 0:
        raise ValueError("z_mm must be > 0")
    if z >= near_mm:
        return 0.0
    return float(min(cap_mm, at_350_mm * 350.0 / z))


class IpdTerm:
    """Inter-pupillary distance as the population size source (DESIGN 4.7; ``is_prior`` True).

    Residual (||X_pL - X_pR|| - (mean - dIPD)) / sd with mean 63 mm (far gaze) and sd 3.8 mm
    (🧠, rec BA-10), dIPD = :func:`vergence_correction_mm` (z_mm) subtracted when the views are
    near (z_mm: typical camera-to-eye distance of the views that see the pupils, mm).  It
    *replaces* the global-size zeta prior (:func:`population_scale_setup`), never joins it.
    """

    is_prior = True

    def __init__(self, p_L_idx: int, p_R_idx: int, mean_mm: float = _S["ipd_mean_mm"], sd_mm: float = _S["ipd_sd_mm"],
                 *, z_mm: float | None = None, name: str = "ipd"):
        self.a, self.b = int(p_L_idx), int(p_R_idx)
        if self.a == self.b:
            raise ValueError("IpdTerm needs two different pupil landmarks")
        self.mean_far, self.sd = float(mean_mm), float(sd_mm)
        if not (self.mean_far > 0 and self.sd > 0):
            raise ValueError("IpdTerm needs mean_mm > 0 and sd_mm > 0")
        self.d_vergence = vergence_correction_mm(z_mm)
        self.mean = self.mean_far - self.d_vergence
        self.name = str(name)

    def n_params(self) -> int:
        return 0

    def init_params(self, state: Any) -> np.ndarray:
        return np.zeros(0)

    def residuals(self, state: Any, p: np.ndarray) -> np.ndarray:
        d = state.X[self.a] - state.X[self.b]
        return np.array([(float(np.linalg.norm(d)) - self.mean) / self.sd])

    def jacobian(self, state: Any, p: np.ndarray) -> dict:
        d = state.X[self.a] - state.X[self.b]
        u = d / max(float(np.linalg.norm(d)), 1e-12) / self.sd
        J = np.zeros((1, 3 * len(state.X)))
        J[0, 3 * self.a:3 * self.a + 3] = u
        J[0, 3 * self.b:3 * self.b + 3] = -u
        return {"X": J}


# =========================================================================== population source
def population_scale_source(requested: Any) -> str | None:
    """Normalise the requested population size source (DESIGN D-03, 4.7): exactly one of
    ``'global_size'`` / ``'ipd'`` (or None / 'none' for no population source).

    Accepts a string or a collection of strings; requesting both sources raises ``ValueError``
    (one population source only: they would double count the same population information).
    """
    if requested is None:
        return None
    items = [requested] if isinstance(requested, str) else list(requested)
    norm = []
    for it in items:
        if it is None or str(it).lower() == "none":
            continue
        s = _KIND_ALIASES.get(str(it), str(it))
        if s not in POPULATION_SOURCES:
            raise ValueError(f"unknown population scale source {it!r} (expected one of {POPULATION_SOURCES})")
        if s not in norm:
            norm.append(s)
    if len(norm) > 1:
        raise ValueError("exactly one population scale source may be active: 'global_size' and 'ipd' together "
                         "would count the population size twice (DESIGN D-03 / 4.7)")
    return norm[0] if norm else None


def population_scale_setup(source: Any, *, pupil_idx: tuple[int, int] | None = None, z_mm: float | None = None,
                           sigma_log: float | None = None, ipd_mean_mm: float = _S["ipd_mean_mm"],
                           ipd_sd_mm: float = _S["ipd_sd_mm"]) -> tuple[ScaleConfig, list]:
    """(ScaleConfig, extra terms) for the bundle given the population size source.

    * ``'global_size'``: zeta prior N(0, sigma_log^2), sigma_log default 0.045 (DESIGN D-03),
      no extra term;
    * ``'ipd'``: a flat zeta prior (sigma 10 in log, 🆕) plus :class:`IpdTerm` on
      ``pupil_idx`` = (p_L, p_R) with the vergence correction for ``z_mm``;
    * None: a flat zeta prior and no term (metric size only from the metric references).
    """
    src = population_scale_source(source)
    free = float(_S["free_zeta_sigma_log"])
    if src == "global_size":
        sl = float(BUNDLE["scale_sigma_log"].value) if sigma_log is None else float(sigma_log)
        return ScaleConfig(enabled=True, sigma_log=sl), []
    if src == "ipd":
        if pupil_idx is None:
            raise ValueError("the 'ipd' population source needs pupil_idx = (p_L, p_R)")
        return ScaleConfig(enabled=True, sigma_log=free), [IpdTerm(pupil_idx[0], pupil_idx[1], ipd_mean_mm,
                                                                   ipd_sd_mm, z_mm=z_mm)]
    return ScaleConfig(enabled=True, sigma_log=free), []


# =========================================================================== iris gating and limbus fit
def iris_usable(d_px: float, sharp: bool, glasses: bool, *, min_px: float = _S["iris_min_px"]) -> bool:
    """Iris diameter usable as a ruler: d_px >= 20 and a sharp limbus and no glasses (DESIGN 4.7, anat R3.4).

    ``sharp``: the verdict of :func:`limbus_is_sharp` (``fit_limbus(..., full_output=True)[4]['sharp']``).
    """
    d = float(d_px)
    return bool(math.isfinite(d) and d >= float(min_px) and bool(sharp) and not bool(glasses))


def limbus_is_sharp(sharpness: float, edge_sigma_px: float | None, *,
                    threshold: float = _S["limbus_sharpness_min"],
                    max_edge_sigma_px: float = _S["limbus_edge_sigma_max_px"]) -> bool:
    """Usable-limbus gate (DESIGN 4.7 'the limbus is sharp'; 🆕 thresholds, see SCALE).

    Two conditions: the edge is narrow, ``edge_sigma_px`` (the fitted edge-profile SD from
    ``fit_limbus(..., full_output=True)``) <= ``max_edge_sigma_px`` (blur biases the radius
    whatever the pixel noise), and the edge stands out of the pixel noise, ``sharpness`` >=
    ``threshold`` (the WBS contrast-to-noise statistic of :func:`fit_limbus`).  Without
    ``edge_sigma_px`` only the noise condition can be checked and the result is False: a limbus
    whose blur is unknown (None or NaN) is not usable as a ruler.
    """
    s = float(sharpness)
    if edge_sigma_px is None:
        return False
    w = float(edge_sigma_px)
    return bool(math.isfinite(s) and s >= float(threshold) and math.isfinite(w) and w <= float(max_edge_sigma_px))


def _bilinear(img: np.ndarray, uv: np.ndarray) -> np.ndarray:
    """Bilinear samples at continuous pixel coordinates (..., 2) = (u, v), corner origin; NaN outside."""
    H, W = img.shape
    x = uv[..., 0] - 0.5
    y = uv[..., 1] - 0.5
    inside = (x >= 0.0) & (x <= W - 1) & (y >= 0.0) & (y <= H - 1)
    xc = np.clip(x, 0.0, W - 1.0)
    yc = np.clip(y, 0.0, H - 1.0)
    x0 = np.minimum(np.floor(xc).astype(np.int64), max(W - 2, 0))
    y0 = np.minimum(np.floor(yc).astype(np.int64), max(H - 2, 0))
    fx = xc - x0
    fy = yc - y0
    x1 = np.minimum(x0 + 1, W - 1)
    y1 = np.minimum(y0 + 1, H - 1)
    v = (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x1] * fx * (1 - fy)
         + img[y1, x0] * (1 - fx) * fy + img[y1, x1] * fx * fy)
    return np.where(inside, v, np.nan)


def _mad_sigma(a: np.ndarray) -> float:
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return float("nan")
    return float(1.4826 * np.median(np.abs(a - np.median(a))))


def _kasa(P: np.ndarray, w: np.ndarray | None = None) -> tuple[np.ndarray, float]:
    """Algebraic (Kasa) circle fit: min sum w (x^2 + y^2 + D x + E y + F)^2."""
    w = np.ones(len(P)) if w is None else w
    A = np.column_stack([P[:, 0], P[:, 1], np.ones(len(P))]) * np.sqrt(w)[:, None]
    b = -(P[:, 0] ** 2 + P[:, 1] ** 2) * np.sqrt(w)
    D, E, F = np.linalg.lstsq(A, b, rcond=None)[0]
    c = np.array([-D / 2.0, -E / 2.0])
    r2 = float(c @ c - F)
    return c, math.sqrt(max(r2, 0.0))


def _geometric_fit(P: np.ndarray, c: np.ndarray, r: float, w: np.ndarray, iters: int = 10
                   ) -> tuple[np.ndarray, float]:
    """Weighted geometric circle fit (Gauss-Newton on e_k = |P_k - c| - r) from (c, r)."""
    c = c.copy()
    for _ in range(iters):
        d = P - c
        n = np.linalg.norm(d, axis=1)
        n = np.maximum(n, 1e-12)
        e = n - r
        J = np.column_stack([-d[:, 0] / n, -d[:, 1] / n, -np.ones(len(P))])
        sw = np.sqrt(w)
        step, *_ = np.linalg.lstsq(J * sw[:, None], -e * sw, rcond=None)
        c = c + step[:2]
        r = r + float(step[2])
        if float(np.max(np.abs(step))) < 1e-9:
            break
    return c, float(r)


def _half_max_distance(m: np.ndarray, rr: np.ndarray, j: int, step: int) -> float:
    """Distance from sample j (the peak) to where ``m`` first falls to half its peak value,
    walking in direction ``step`` (+1 / -1), linearly interpolated; inf if it never does."""
    half = 0.5 * float(m[j])
    k = j
    while 0 <= k + step < len(m) and m[k + step] > half:
        k += step
    if not 0 <= k + step < len(m):
        return float("inf")
    t = (float(m[k]) - half) / (float(m[k]) - float(m[k + step]))
    return abs(float(rr[k]) + t * float(rr[k + step] - rr[k]) - float(rr[j]))


def _edge_sigma_px(g: np.ndarray, centre: np.ndarray, r: float, dirs: np.ndarray, h: float, kd: int) -> float:
    """Edge-profile SD sigma_e (px) of the limbus: blur plus pixel footprint.

    Radial profiles from the fitted ``centre`` along the rays used (``dirs``), on
    [r - min(0.4 r, 8), r + min(0.6 r, 10)] px (inside the pupil edge at ~0.4 r and before the
    eye corners), differentiated as in :func:`fit_limbus`; the ray-wise **median** derivative
    profile (noise averages down with the number of rays, a lid crossing a minority of rays does
    not move it) gives the full width at half maximum about its peak near r, and for a Gaussian
    edge sigma^2 = (FWHM / 2.3548)^2 - (2 kd h)^2 / 12 (derivative box) - 1/6 (bilinear
    interpolation).  inf when the half maximum is not reached inside the window (a very blurred
    edge), NaN without a usable profile.
    """
    inner = min(float(_S["limbus_width_inner_frac"]) * r, float(_S["limbus_width_inner_max_px"]))
    outer = min(float(_S["limbus_width_outer_frac"]) * r, float(_S["limbus_width_outer_max_px"]))
    rad = np.arange(r - inner, r + outer + 0.5 * h, h)
    if len(rad) < 2 * kd + 3 or len(dirs) == 0:
        return float("nan")
    prof = _bilinear(g, centre[None, None, :] + rad[None, :, None] * dirs[:, None, :])
    d = (prof[:, 2 * kd:] - prof[:, :-2 * kd]) / (2.0 * kd * h)
    ok = np.all(np.isfinite(d), axis=1)
    if int(ok.sum()) < 3:
        return float("nan")
    m = np.median(d[ok], axis=0)
    rr = rad[kd:-kd]
    near = np.flatnonzero(np.abs(rr - r) <= 2.0)
    if near.size == 0:
        return float("nan")
    j = int(near[np.argmax(m[near])])
    if not m[j] > 0.0:
        return float("nan")
    hw = 0.5 * (_half_max_distance(m, rr, j, 1) + _half_max_distance(m, rr, j, -1))
    if not math.isfinite(hw):
        return float("inf")
    s2 = (hw / math.sqrt(2.0 * math.log(2.0))) ** 2 - (2.0 * kd * h) ** 2 / 12.0 - 1.0 / 6.0
    return math.sqrt(max(s2, 0.0))


def fit_limbus(gray: Any, centre_guess: Any, r_guess: float, n_rays: int = int(_S["limbus_n_rays"]),
               search: tuple[float, float] = (_S["limbus_search_lo"], _S["limbus_search_hi"]),
               exclude_deg: float = _S["limbus_exclude_deg"], *, step_px: float = _S["limbus_step_px"],
               deriv_halfwidth_px: float = _S["limbus_deriv_halfwidth_px"], full_output: bool = False
               ) -> tuple:
    """Fit the iris limbus as a circle by radial gradient profiles (DESIGN 4.7; WBS WP-15).

    ``gray`` (H, W) float image; ``centre_guess`` (u, v) px and ``r_guess`` px (e.g. from the
    iris landmarks).  Pixel (row i, column j) is centred at (j + 1/2, i + 1/2) (DESIGN 3.1).

    1. ``n_rays`` rays at angles 2 pi k / n_rays from the centre guess, skipping the upper and
       lower sectors within +/- ``exclude_deg`` of vertical (the lids cover the limbus there).
    2. Bilinear radial profile on [search_lo, search_hi] x r_guess with step ``step_px``;
       per ray the strongest positive derivative (dark iris to bright sclera, outward), located
       to sub-sample precision by a parabola through the derivative peak.
    3. Kasa algebraic circle fit of the edge points, then 3 IRLS rounds with Huber weights
       (k = 1.345 x 1.4826 MAD of the geometric residuals |P - c| - r), each a weighted
       geometric (Gauss-Newton) fit.

    4. Edge width sigma_e (px, blur plus pixel footprint) from the ray-median derivative profile
       about the fitted circle (:func:`_edge_sigma_px`); the radius is corrected for the
       curvature bias sigma_e^2 / (2 r) of a blurred disc's gradient maximum.

    Returns ``(centre (2,), radius, sigma_r, sharpness)``: px, px, px (sigma_r =
    max(0.5, 1.4826 MAD(residual) / sqrt(n_used)), DESIGN 4.7 floor) and the dimensionless
    sharpness = median peak derivative / (1.4826 MAD of the profile second differences at
    1 px spacing, taken on the raw row and column profiles of the image in the scleral band just
    outside the edge, away from the lids): contrast per blur width over the pixel noise.  With
    ``full_output=True`` a fifth element, ``{'edge_sigma_px', 'n_used', 'peak', 'noise',
    'sharp'}``, carries the edge width and the usable-limbus verdict
    ``limbus_is_sharp(sharpness, edge_sigma_px)`` (:func:`limbus_is_sharp`: the sharpness
    statistic alone measures contrast-to-noise, not blur, so the gate needs the edge width).
    Raises ``ValueError`` when fewer than 8 rays find an edge.
    """
    g = np.asarray(gray, float)
    if g.ndim != 2 or min(g.shape) < 3:
        raise ValueError("gray must be a 2-D image of at least 3 x 3 pixels")
    c0 = np.asarray(centre_guess, float).reshape(2)
    r0 = float(r_guess)
    if not (r0 > 0 and np.all(np.isfinite(c0))):
        raise ValueError("fit_limbus needs a finite centre_guess and r_guess > 0")
    lo, hi = float(search[0]) * r0, float(search[1]) * r0
    h = float(step_px)
    ang = 2.0 * np.pi * np.arange(int(n_rays)) / int(n_rays)
    # angular distance to the nearest vertical direction (90 or 270 deg)
    dv = np.abs((np.degrees(ang) % 180.0) - 90.0)
    keep = dv > float(exclude_deg)
    ang = ang[keep]
    dirs = np.column_stack([np.cos(ang), np.sin(ang)])
    radii = np.arange(lo, hi + 0.5 * h, h)
    if len(radii) < 5 or len(ang) == 0:
        raise ValueError("fit_limbus: search range too small or every ray excluded")
    pts = c0[None, None, :] + radii[None, :, None] * dirs[:, None, :]
    prof = _bilinear(g, pts)                                       # (n_rays, n_r)
    kd = max(1, int(round(float(deriv_halfwidth_px) / h)))
    if len(radii) < 2 * kd + 3:
        raise ValueError("fit_limbus: search range too small for the derivative width")
    deriv = (prof[:, 2 * kd:] - prof[:, :-2 * kd]) / (2.0 * kd * h)   # at radii[kd:-kd]
    edges, peaks, used_dirs = [], [], []
    tiny = 1e-9 * (1.0 + float(np.nanmax(np.abs(g))))            # no edge in a flat profile
    for k in range(len(ang)):
        d = deriv[k]
        if not np.all(np.isfinite(d)):
            continue
        j = int(np.argmax(d))
        if d[j] <= tiny or j == 0 or j == len(d) - 1:
            continue
        dm, d0, dp = d[j - 1], d[j], d[j + 1]
        den = dm - 2.0 * d0 + dp
        off = 0.5 * (dm - dp) / den if den < 0.0 else 0.0
        off = float(np.clip(off, -0.5, 0.5))
        edges.append(radii[j + kd] + off * h)
        peaks.append(d0 - 0.25 * (dm - dp) * off)
        used_dirs.append(dirs[k])
    if len(edges) < int(_S["limbus_min_rays"]):
        raise ValueError(f"fit_limbus: only {len(edges)} rays found an edge (need {int(_S['limbus_min_rays'])})")
    # rays whose strongest edge is much weaker than the median are occluded (lids, lashes,
    # specular highlights): no limbus there
    pk = np.asarray(peaks)
    strong = pk >= float(_S["limbus_min_peak_frac"]) * float(np.median(pk))
    if int(strong.sum()) < int(_S["limbus_min_rays"]):
        raise ValueError(f"fit_limbus: only {int(strong.sum())} rays found a limbus edge "
                         f"(need {int(_S['limbus_min_rays'])})")
    edges = [e for e, ok in zip(edges, strong) if ok]
    peaks = [p_ for p_, ok in zip(peaks, strong) if ok]
    used_dirs = [d_ for d_, ok in zip(used_dirs, strong) if ok]
    E = np.asarray(edges)
    U = np.asarray(used_dirs)
    P = U * E[:, None]                                             # relative to c0
    c, r = _kasa(P)
    w = np.ones(len(P))
    kh = float(_S["limbus_huber_k"])
    for _ in range(int(_S["limbus_irls_rounds"])):
        c, r = _geometric_fit(P, c, r, w)
        e = np.linalg.norm(P - c, axis=1) - r
        s = max(_mad_sigma(e), 1e-6)
        a = np.abs(e)
        w = np.where(a <= kh * s, 1.0, kh * s / np.maximum(a, 1e-12))
    c, r = _geometric_fit(P, c, r, w)
    e = np.linalg.norm(P - c, axis=1) - r
    n_used = len(P)
    sigma_r = max(float(_S["limbus_sigma_floor_px"]), _mad_sigma(e) / math.sqrt(n_used))
    # Edge width sigma_e (the blur gate of :func:`limbus_is_sharp`) from the ray-median radial
    # derivative profile about the fitted circle, and the curvature bias: the gradient maximum
    # of a blurred disc sits sigma_e^2 / (2 r) inside the true edge.
    edge_sigma = _edge_sigma_px(g, c0 + c, r, U, h, kd)
    if math.isfinite(edge_sigma):
        r = r + min(edge_sigma ** 2, (0.5 * r) ** 2) / (2.0 * r)
    # Noise statistic: second differences of the image's row and column profiles at one-pixel
    # spacing (raw pixels: bilinear ray samples would average 1-4 pixels depending on the ray and
    # bias the noise level) in the scleral band r + 3 px .. r + 3 px + max(6 px, 0.5 r) outside
    # the fitted circle (the iris side carries the pupil edge and iris texture), in the kept
    # sectors narrowed by a further limbus_noise_margin_deg (away from the lid edges).
    H, W = g.shape
    cf = c0 + c
    reach = r + float(_S["limbus_noise_exclude_px"]) + max(float(_S["limbus_noise_band_min_px"]),
                                                             float(_S["limbus_noise_band_frac"]) * r)
    jj = np.arange(max(0, int(math.floor(cf[0] - reach)) - 1), min(W, int(math.ceil(cf[0] + reach)) + 2))
    ii = np.arange(max(0, int(math.floor(cf[1] - reach)) - 1), min(H, int(math.ceil(cf[1] + reach)) + 2))
    noise = float("nan")
    if len(jj) >= 3 and len(ii) >= 1:
        patch = g[np.ix_(ii, jj)]
        ex_px = float(_S["limbus_noise_exclude_px"])
        band_px = max(float(_S["limbus_noise_band_min_px"]), float(_S["limbus_noise_band_frac"]) * r)
        min_vert = float(exclude_deg) + float(_S["limbus_noise_margin_deg"])
        samples = []
        for axis in (1, 0):                         # row profiles, then column profiles
            if patch.shape[axis] < 3:
                continue
            if axis == 1:
                d2 = patch[:, 2:] - 2.0 * patch[:, 1:-1] + patch[:, :-2]
                du = (jj[1:-1] + 0.5)[None, :] - cf[0]
                dvv = (ii + 0.5)[:, None] - cf[1]
            else:
                d2 = patch[2:, :] - 2.0 * patch[1:-1, :] + patch[:-2, :]
                du = (jj + 0.5)[None, :] - cf[0]
                dvv = (ii[1:-1] + 0.5)[:, None] - cf[1]
            rad = np.hypot(du, dvv)
            vert = np.degrees(np.arctan2(np.abs(du), np.abs(dvv)))     # angle from vertical
            sel = (rad > r + ex_px) & (rad <= r + ex_px + band_px) & (vert > min_vert)
            samples.append(d2[sel])
        d2 = np.concatenate(samples) if samples else np.zeros(0)
        if d2.size >= 10:
            noise = _mad_sigma(d2)
    peak = float(np.median(peaks))
    sharp = float("nan") if not np.isfinite(noise) else (float("inf") if not noise > 0 else peak / noise)
    out = (c0 + c, float(r), float(sigma_r), float(sharp))
    if not full_output:
        return out
    info = {"edge_sigma_px": float(edge_sigma), "n_used": int(n_used), "peak": peak, "noise": float(noise),
            "sharp": limbus_is_sharp(sharp, edge_sigma)}
    return out + (info,)


def iris_observation(view: int, eye: str, radius_px: float, sigma_r_px: float) -> tuple[int, str, float, float]:
    """``(view, eye, d_px, sigma_px)`` for :class:`IrisTerm` from a limbus fit: d = 2 r, sigma_d = 2 sigma_r."""
    return int(view), str(eye), 2.0 * float(radius_px), 2.0 * float(sigma_r_px)


# =========================================================================== metric log-size
def log_size(X: Any, ref: Any) -> float:
    """log s of the Umeyama similarity mapping ``ref`` onto ``X`` (both (N, 3) mm; NaN rows ignored).

    The same definition as the test bed's ``log_scale_true`` (face3d.testbed.subjects.log_scale_of).
    """
    X, ref = np.asarray(X, float), np.asarray(ref, float)
    m = np.isfinite(X).all(axis=1) & np.isfinite(ref).all(axis=1)
    s, _, _ = umeyama(ref[m], X[m], with_scale=True)
    return float(math.log(s))


def log_size_gradient(X: Any, ref: Any) -> np.ndarray:
    """d log s / dX (N, 3) of :func:`log_size` (envelope theorem at the optimal rotation).

    With s = sum_i (X_i - X_bar) . R (T_i - T_bar) / sum_i |T_i - T_bar|^2 maximised over R,
    d s / d X_i = R (T_i - T_bar) / sum |T - T_bar|^2 and d log s = d s / s.  Rows of
    non-finite points are 0.
    """
    X, ref = np.asarray(X, float), np.asarray(ref, float)
    m = np.isfinite(X).all(axis=1) & np.isfinite(ref).all(axis=1)
    s, R, _ = umeyama(ref[m], X[m], with_scale=True)
    T = ref[m] - ref[m].mean(axis=0)
    G = np.zeros_like(X)
    G[m] = (T @ np.asarray(R).T) / (s * float(np.sum(T * T)))
    return G


def log_size_posterior(X: Any, cov: Any, ref: Any) -> tuple[float, float]:
    """(zeta, sigma): metric log-size of the reconstruction relative to ``ref`` and its posterior SD.

    ``cov`` is the (3N, 3N) point covariance in mm^2 (point-major; e.g. ``BundleResult.cov``,
    which has cameras, focal, the bundle's zeta and term parameters eliminated); sigma =
    sqrt(g^T cov g) with g = :func:`log_size_gradient`.
    """
    X = np.asarray(X, float)
    C = np.asarray(cov, float)
    n = len(X)
    if C.shape != (3 * n, 3 * n):
        raise ValueError(f"cov must be ({3 * n}, {3 * n}), got {C.shape}")
    g = log_size_gradient(X, ref).reshape(-1)
    var = float(g @ C @ g)
    return log_size(X, ref), math.sqrt(max(var, 0.0))


# =========================================================================== global scale mode
def scale_mode(result: Any, *, X: Any = None, cov: Any = None) -> dict:
    """Posterior precision of the head's global scale (DESIGN D-03, 4.7, H4).

    Scaling the head about the head-frame origin, X -> k X, together with every camera
    translation leaves all reprojection residuals unchanged (inverse-depth model, D-02), and the
    bundle's log-scale zeta absorbs it in the shape prior on e^-zeta X: the data are blind to the
    global scale.  With C = ``result.cov`` (the points' marginal posterior, cameras, focal,
    zeta and term parameters eliminated by Schur complement) and x = vec(X) the scale direction in
    point space, the information about the head's scale with every nuisance re-adjusted is
    I = x^T C^-1 x, and sigma = 1 / sqrt(I) is the posterior SD of the best point-space scale
    coordinate (the functional l = C^-1 x / I, l^T x = 1, of smallest variance).  I collects
    exactly the metric references (a caliper chord directly; a card through its contact-depth
    prior; the iris through D's prior), the population source (zeta prior or IPD) and any
    distance priors: iris alone gives sigma = 0.6 / 11.8 = 0.051, with the 0.045 population prior
    0.034, a 0.5 mm caliper on a chord L about 0.5 / L (DESIGN 4.7 🔢; with the end points'
    definition bias in the chord, :class:`ChordTerm`, about 2.2 / L for extremal points).

    This is the *reference component* of the size uncertainty, not the uncertainty of any
    printed size: for every log-length (or log-size) functional h of the points (h^T x = 1),
    h = l + (h - l) with the two parts uncorrelated, so its variance is sigma^2 plus a shape
    part (h - l)^T C (h - l) >= 0.  Every length's error contains this common component, and
    each length adds its own shape error on top (with a caliper on zy-zy the Umeyama log-size
    of the WP-01 test bed adds ~1.4 % to the caliper's 0.4 %).  The reported scale pair is
    :func:`reported_scale`.  A rank-deficient ``cov`` (low-dimensional shape model) is
    pseudo-inverted.

    ``X`` / ``cov`` override ``result.X`` / ``result.cov``.  Returns ``{'direction': x (3N,),
    'information': I, 'sigma': sigma, 'functional': l (3N,)}``.
    """
    X = np.asarray(result.X if X is None else X, float)
    C = np.asarray(result.cov if cov is None else cov, float)
    x = X.reshape(-1)
    if C.shape != (x.size, x.size):
        raise ValueError(f"cov must be ({x.size}, {x.size}), got {C.shape}")
    try:
        y = np.linalg.solve(C, x)
        if not np.all(np.isfinite(y)):
            raise np.linalg.LinAlgError
    except np.linalg.LinAlgError:
        y = np.linalg.pinv(C, rcond=1e-10, hermitian=True) @ x
    info = float(x @ y)
    if not info > 0:
        return {"direction": x, "information": max(info, 0.0), "sigma": float("inf"), "functional": np.zeros_like(x)}
    return {"direction": x, "information": info, "sigma": 1.0 / math.sqrt(info), "functional": y / info}


def reported_scale(result: Any, ref: Any, *, X: Any = None, cov: Any = None, sigma_def_mm: Any = None,
                   chi2_red: float | None = None) -> dict:
    """The scale pair printed by the report (DESIGN 4.7, H4, H12): a value and an SD that covers it.

    ``zeta`` = :func:`log_size` (X, ref): the Umeyama log-size of the reconstruction relative
    to ``ref`` (the template / prior mean; the test bed's ``log_scale_true`` definition).  Its
    SD has three uncorrelated parts (with g = :func:`log_size_gradient`, C = ``result.cov``):

    * ``reference_sigma`` = :func:`scale_mode` sigma, what the metric references and the
      population source leave of the global scale (iris + population ~3.4 %);
    * ``shape_sigma`` = sqrt(g^T C g - reference_sigma^2), the shape part of the log-size
      (points that only the prior places, focal and pose), inflated by max(1, chi2_red) as
      ``sigma_rep_mm`` is (DESIGN 4.13; the detector noise misfit enters the shape, not the
      references);
    * ``definition_sigma`` = sqrt(sum_i sigma_def,i^2 |g_i|^2), the definition bias of the
      detected landmarks (D-06; ``result.sigma_def_mm`` unless ``sigma_def_mm`` is given).

    ``sigma`` = sqrt(reference^2 + chi2 x shape^2 + definition^2) >= reference_sigma: pass
    ``zeta`` and ``sigma`` to :func:`scale_report` (``reference_sigma`` too).  ``X`` / ``cov`` /
    ``chi2_red`` override the result's.  Returns ``{'zeta', 'sigma', 'reference_sigma',
    'shape_sigma', 'definition_sigma', 'chi2_inflation'}`` (log units).
    """
    X = np.asarray(result.X if X is None else X, float)
    C = np.asarray(result.cov if cov is None else cov, float)
    n = len(X)
    if C.shape != (3 * n, 3 * n):
        raise ValueError(f"cov must be ({3 * n}, {3 * n}), got {C.shape}")
    zeta = log_size(X, ref)
    g = log_size_gradient(X, ref)
    gv = g.reshape(-1)
    var_size = max(float(gv @ C @ gv), 0.0)
    ref_sigma = float(scale_mode(result, X=X, cov=C)["sigma"])
    var_shape = max(var_size - ref_sigma ** 2, 0.0) if math.isfinite(ref_sigma) else 0.0
    chi = getattr(result, "chi2_red", None) if chi2_red is None else chi2_red
    infl = float(chi) if chi is not None and math.isfinite(float(chi)) and float(chi) > 1.0 else 1.0
    sd = getattr(result, "sigma_def_mm", None) if sigma_def_mm is None else sigma_def_mm
    sd = np.zeros(n) if sd is None else np.broadcast_to(np.asarray(sd, float), (n,))
    var_def = float(np.sum(np.where(np.isfinite(sd), sd, 0.0) ** 2 * np.sum(g * g, axis=1)))
    total = math.sqrt(ref_sigma ** 2 + infl * var_shape + var_def) if math.isfinite(ref_sigma) else float("inf")
    return {"zeta": float(zeta), "sigma": float(total), "reference_sigma": ref_sigma,
            "shape_sigma": math.sqrt(var_shape), "definition_sigma": math.sqrt(var_def), "chi2_inflation": infl}


# =========================================================================== sources and report
def _kind(kind: str) -> str:
    k = _KIND_ALIASES.get(str(kind), str(kind))
    if k not in _LABEL_ORDER:
        raise ValueError(f"unknown scale source kind {kind!r} (expected one of {_LABEL_ORDER})")
    return k


def scale_source(kind: str, zeta: float | None = None, sigma: float | None = None, **detail: Any) -> dict:
    """A scale source record ``{'kind', 'zeta', 'sigma', ...}`` for :func:`scale_report`.

    ``zeta`` is the metric log-size this source alone implies for the reconstruction and
    ``sigma`` its SD (log units); both may be None for a source that only labels the mode.
    """
    return {"kind": _kind(kind), "zeta": None if zeta is None else float(zeta),
            "sigma": None if sigma is None else float(sigma), **detail}


def chord_scale_source(X: Any, a_idx: int, b_idx: int, length_mm: float, ref: Any, *,
                       sigma_mm: float = _S["chord_sigma_mm"], offset_mm: float = _S["chord_offset_mm"],
                       definition_sigma_mm: Any = 0.0, kind: str = "caliper") -> dict:
    """Log-size implied by a chord measurement: zeta_X + log((L + o) / |X_a - X_b|).

    sigma = sqrt(sigma_L^2 + sigma_def,a^2 + sigma_def,b^2) / (L + o): the measurement SD and
    the end points' definition bias along the chord (see :class:`ChordTerm`).
    """
    X = np.asarray(X, float)
    dist = float(np.linalg.norm(X[int(a_idx)] - X[int(b_idx)]))
    if not dist > 0:
        raise ValueError("chord end points coincide")
    L = float(length_mm) + float(offset_mm)
    da, db = _definition_pair(definition_sigma_mm)
    sig = math.sqrt(float(sigma_mm) ** 2 + da * da + db * db) / L
    return scale_source(kind, log_size(X, ref) + math.log(L / dist), sig, length_mm=float(length_mm))


def iris_scale_source(X: Any, cameras: Sequence[Any], obs: Sequence[tuple], eye_idx: Mapping[str, int], ref: Any,
                      *, prior_mm: tuple[float, float] = (_S["iris_mean_mm"], _S["iris_sd_mm"])) -> dict:
    """Log-size implied by iris observations alone.

    Each observation (view, eye, d_px, sigma_px) gives the reconstruction-scale diameter
    D_o = d_px z / f (z the pupil landmark's depth in that camera, f its focal); D_rec is
    their inverse-variance mean.  The implied log-size is zeta_X + log(mu / D_rec) with
    sigma = sqrt((sd / mu)^2 + var(log D_rec)) (DESIGN 4.7: 11.8 +/- 0.6 mm).
    """
    X = np.asarray(X, float)
    vals, wts = [], []
    for v, eye, d, s in obs:
        cam = cameras[int(v)]
        z = float(cam.depth(X[int(eye_idx[eye])][None])[0])
        Do = float(d) * z / float(cam.f)
        sd = float(s) * z / float(cam.f)
        vals.append(Do)
        wts.append(1.0 / sd ** 2)
    if not vals:
        raise ValueError("iris_scale_source needs at least one observation")
    w = np.asarray(wts)
    D = float(np.sum(w * np.asarray(vals)) / np.sum(w))
    var_log = 1.0 / float(np.sum(w)) / D ** 2
    mu, sd = float(prior_mm[0]), float(prior_mm[1])
    return scale_source("iris", log_size(X, ref) + math.log(mu / D), math.sqrt((sd / mu) ** 2 + var_log),
                        d_rec_mm=D, n_obs=len(vals))


def card_scale_source(X: Any, camera: Any, corner_uv: Any, touch_idx: int, ref: Any, *,
                      length_mm: float = _S["card_length_mm"], sigma_mm: float = _S["card_sigma_mm"],
                      depth_sigma_mm: float = _S["card_depth_sigma_mm"], sigma_px: float = _S["card_sigma_px"]
                      ) -> dict:
    """Log-size implied by an ID-1 card held against landmark ``touch_idx`` in one view.

    The corners are back-projected to the touch landmark's depth z; the implied log-size is
    zeta_X + log(L / |C1 - C2|) with sigma^2 = (sigma_L / L)^2 + (depth_sigma / z)^2 +
    2 (sigma_px / |uv1 - uv2|)^2 (the card length scales with its depth).
    """
    X = np.asarray(X, float)
    uv = np.asarray(corner_uv, float).reshape(2, 2)
    z = float(camera.depth(X[int(touch_idx)][None])[0])
    rays = np.column_stack([(uv[:, 0] - camera.cx) / camera.f, (uv[:, 1] - camera.cy) / camera.f, np.ones(2)])
    C = rays * z
    dist = float(np.linalg.norm(C[0] - C[1]))
    duv = float(np.linalg.norm(uv[0] - uv[1]))
    L = float(length_mm)
    var = (float(sigma_mm) / L) ** 2 + (float(depth_sigma_mm) / z) ** 2 + 2.0 * (float(sigma_px) / duv) ** 2
    return scale_source("card", log_size(X, ref) + math.log(L / dist), math.sqrt(var))


def fuse_log_scale(sources: Sequence[Any]) -> tuple[float, float]:
    """Inverse-variance fusion of independent log-scale estimates (anat R3.4).

    ``sources``: :func:`scale_source` dicts or (zeta, sigma) pairs; entries without a finite
    sigma are ignored.  Returns (zeta, sigma); e.g. iris 0.6 / 11.8 = 0.0508 with the
    population 0.045 gives 0.0337 (DESIGN 4.7 🔢).
    """
    num, den = 0.0, 0.0
    for s in sources:
        z, sg = (s.get("zeta"), s.get("sigma")) if isinstance(s, Mapping) else (s[0], s[1])
        if sg is None or not (float(sg) > 0 and math.isfinite(float(sg))):
            continue
        z = 0.0 if z is None else float(z)
        w = 1.0 / float(sg) ** 2
        num += w * z
        den += w
    if den == 0.0:
        raise ValueError("fuse_log_scale needs at least one source with a finite sigma")
    return num / den, 1.0 / math.sqrt(den)


def _as_source(s: Any) -> dict:
    if isinstance(s, str):
        return scale_source(s)
    if isinstance(s, Mapping):
        d = dict(s)
        d["kind"] = _kind(d.get("kind", ""))
        return d
    raise TypeError(f"scale source must be a kind string or a dict, not {type(s).__name__}")


def scale_report(zeta: float, zeta_sigma: float, sources: Sequence[Any], *, reference_sigma: float | None = None,
                 conflict_rel: float = _S["conflict_rel"], conflict_nsigma: float = _S["conflict_nsigma"]) -> dict:
    """Scale mode, label and uncertainty for the report (DESIGN 4.7, H4).

    ``zeta`` / ``zeta_sigma``: the printed metric log-size and an SD that covers its error,
    i.e. ``reported_scale(...)['zeta']`` and ``['sigma']`` (:func:`reported_scale`; the scale
    mode's sigma alone leaves out the shape and definition parts and is far too confident for
    the size it would be printed next to).  ``reference_sigma`` (optional,
    ``reported_scale(...)['reference_sigma']``) is echoed as the metric references' share.
    ``sources``: kinds ('caliper', 'card', 'iris', 'ipd', 'global_size') or
    :func:`scale_source` dicts.  Returns::

        {mode: 'measured' | 'iris' | 'prior', label: e.g. 'iris+population',
         sigma_pct: 100 zeta_sigma, conflict: bool, zeta, zeta_sigma,
         reference_sigma, reference_sigma_pct (None without reference_sigma),
         text: 'scale: iris+population +/-3.7 %', pairs: [...], findings: [S-CONFLICT finding dicts]}

    mode is 'measured' with a caliper or card, else 'iris' with an iris source, else 'prior'.
    The label lists the sources in the order caliper, card, iris, ipd, population ('none'
    without any).  ``conflict``: two *metric* sources (caliper, card, iris) whose implied
    zeta differ by more than 1 % **and** more than 2 combined sigma (finding ``S-CONFLICT``).
    """
    srcs = [_as_source(s) for s in sources]
    kinds = {s["kind"] for s in srcs}
    if kinds & set(_MEASURED_KINDS):
        mode = "measured"
    elif "iris" in kinds:
        mode = "iris"
    else:
        mode = "prior"
    label = "+".join(_LABEL_NAME[k] for k in _LABEL_ORDER if k in kinds) or "none"
    sig = float(zeta_sigma)
    pct = 100.0 * sig
    metric = [s for s in srcs if s["kind"] in METRIC_KINDS and s.get("zeta") is not None
              and s.get("sigma") is not None]
    pairs, findings = [], []
    conflict = False
    for i in range(len(metric)):
        for j in range(i + 1, len(metric)):
            a, b = metric[i], metric[j]
            diff = abs(float(a["zeta"]) - float(b["zeta"]))
            comb = math.hypot(float(a["sigma"]), float(b["sigma"]))
            bad = diff > float(conflict_rel) and diff > float(conflict_nsigma) * comb
            pairs.append({"a": a["kind"], "b": b["kind"], "diff": diff, "combined_sigma": comb, "conflict": bad})
            if bad:
                conflict = True
                findings.append({
                    "code": FLAG_SCALE_CONFLICT, "severity": "warn", "value": diff,
                    "threshold": [float(conflict_rel), float(conflict_nsigma) * comb], "action": "ask",
                    "msg_key": f"solve.{FLAG_SCALE_CONFLICT}", "fix_key": f"solve.{FLAG_SCALE_CONFLICT}.fix",
                    "source": SCALE["conflict_rel"].source, "badge": SCALE["conflict_rel"].badge,
                    "photo_id": None, "detail": {"a": a["kind"], "b": b["kind"]},
                })
    rs = None if reference_sigma is None else float(reference_sigma)
    return {"mode": mode, "label": label, "sigma_pct": pct, "conflict": conflict, "zeta": float(zeta),
            "zeta_sigma": sig, "reference_sigma": rs, "reference_sigma_pct": None if rs is None else 100.0 * rs,
            "text": f"scale: {label} ±{pct:.1f} %", "pairs": pairs, "findings": findings}
