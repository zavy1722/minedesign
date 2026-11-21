"""Multi-view landmark bundle adjustment with anatomical priors (engine v2; DESIGN 4.3-4.9).

Unknowns: per view an inverse-depth camera block (DESIGN D-02, 4.3); per focal group a
log-focal phi_G; per view an optional jaw-hinge angle theta_v (4.9); optionally a global
log-scale zeta (D-03, 4.7); the N landmarks in the HEAD FRAME through a shape model
(mm; +x subject's left, +y up, +z out of the face; DESIGN 3.1); the parameters of any
extra :class:`~face3d.solve.terms.Term`.

Parameter vector (:class:`_Layout`, ``BundleResult.param_index``)::

    [camera block per view | phi per focal group | theta per jaw view | zeta? |
     shape parameters (3N for FreePoints) | term parameters]

Cameras (DESIGN D-02, 4.3)
--------------------------
u = c + s ((R X)_xy + tau) / (1 + rho (R X)_z), f = s / rho, t = (tau_x, tau_y, 1 / rho).
Block kinds (stored order; the first six are always the pose (omega, tau, rho)):

* FREE (``ViewObs.estimate_focal``; ungrouped, or grouped with a soft tie):
  (omega 3, tau 2 mm, rho, a = ln s); log f_v = a_v - ln rho_v.  (The WBS lists the block as
  (omega, tau, a, rho); a is stored last so that the first six entries are always the pose.)
* HARD (grouped with ``focal_tie_sigma`` None, the legacy exact sharing): (omega, tau, rho)
  with s_v = e^phi_G rho_v, so every view of the group has f = e^phi_G exactly.
* FIXED_F (``estimate_focal`` False): (omega, tau, rho) with s = f rho.

omega is a multiplicative rotation increment R <- exp([omega]_x) R (stored as a rotation
vector, retracted multiplicatively).  rho is box-projected to [1e-4, 4e-3] 1/mm (0.25-10 m,
DESIGN D-02 / 4.2 / bl C6) by the LM ``project`` hook, never inside ``retract``, so the
analytic Jacobian stays exact.  The parameter vector stores rho in 1/m (rho_param =
1000 rho, the box [0.1, 4] 1/m of DESIGN D-02) so that it is scaled like the other
parameters (a scalar covariance ridge and fixed finite-difference steps stay meaningful);
everything reported (``Camera``, ``SolverState.invdepth``, priors) uses 1/mm.  Cameras enter
and leave as :class:`Camera` objects via :func:`~face3d.geometry.camera.camera_to_invdepth` /
``invdepth_to_camera`` (WP-06).

Residual rows (all whitened), in this order::

    [reprojection (data) | data terms | focal priors | focal ties | distance priors |
     pose-tag priors | jaw priors | frozen-view rows | zeta prior | shape prior |
     symmetry | midline | gauge | prior terms]

* reprojection  sqrt(w_iv) W_iv (u_iv(X_iv) - u_obs) / nu_v, W_iv the frozen whitening of
  the noise (DESIGN 4.4), w_iv = user weight x IRLS weight x visibility weight x view weight.
* focal prior   (phi_G - ln f_prior) / sigma (tightest prior of the group) or, for an
  ungrouped FREE view, (a_v - ln rho_v - ln f_prior) / sigma.
* focal tie     (a_v - ln rho_v - phi_G) / focal_tie_sigma for the live (not frozen) FREE
  views of a group (DESIGN 4.2 / rec CAM-5 sigma_tie 0.02, passed by the pipeline).
* distance      (-ln rho_v - ln median) / sigma_log (``ViewObs.distance_prior``; DESIGN 4.2).
* pose tag      (yaw_v - yaw_tag) / sigma_yaw, (pitch_v - pitch_tag) / sigma_pitch in degrees,
  yaw = atan2(C_x, C_z), pitch = asin(C_y / |C|) of the camera centre C = -R^T t (head frame).
* jaw prior     (theta_v - mean) / sigma (``JawConfig``; DESIGN 4.9 N(1.5 deg, 1 deg^2)).
* frozen views  rows (p - p_frozen) / tiny on the camera block (and jaw angle) of a view the
  robust schedule rejected or left without observations (its observations are excluded; the
  rows keep its block non-singular), and on the phi of a focal group with no live view left.
  A frozen view keeps no row coupling its block to shared parameters (its focal tie is
  dropped), so it cannot bias phi_G; the covariance is conditional on the frozen parameters
  (their rows and columns of Sigma are zero) and their stiff rows do not enter the ridge.
* zeta, shape, symmetry, midline, gauge: unchanged from WP-07 (D-03, 4.6, 4.11).

Jaw hinge (DESIGN 4.9): X_iv = X_i + w_i (R_x(theta_v)(X_i - c) - (X_i - c)), axis +x through
``jaw_center_mm`` (default (0, -5, 11.5) mm: mid-tragion + (0, -5, +11.5) mm, the head-frame
origin being mid-tragion; bl K8 ↔️), per-landmark weights ``jaw_weights``; theta in
[bounds] by ``project``; positive theta opens the mouth (chin moves down and back).

Visibility (DESIGN 4.8, rec BA-3 🧠), two independent rules recomputed before every IRLS
round: with ``landmark_normals``, the weight clip((cos th - cos 80 deg) / (cos 60 deg -
cos 80 deg), 0, 1), cos th = n_i . (C_v - X_i) / |C_v - X_i|, multiplies the information;
whenever a view has 'contour' kinds (normals or not), its contour points with x on the side
opposite to the view's yaw are dropped when |yaw| > 25 deg.

View weights (DESIGN D-07, 4.4; ``view_weighting=True``): w_v = 1 / n_bin with 15 deg yaw
bins (centred on 0) x pitch bands (< -15, -15..15, > 15 deg); then two passes cap every
view's share of the shape-block information trace at 0.40 (water-filling: a view capped in the
first pass stays capped in the second, which caps the views the first pushed over the cap,
so two dominant views both end at 0.40).  Yaw and pitch are those of the
current camera centre; the weights are frozen before each LM run, so the shares reported at
the final solution (``view_stats[v]['weight_share']``) can differ from the cap by O(1e-5).

Robust schedule (DESIGN D-07, D-08, 4.5; :mod:`face3d.solve.robust`): with
``robust=RobustSchedule()`` Huber rounds, a Tukey round, rejection at 3.035 sigma, a view
chi^2 test and a final plain least-squares solve on the inliers, the per-view scale nu_v
re-estimated before each round.  With ``robust=None`` and ``huber_px`` set the legacy
Huber-only IRLS runs unchanged.  Noise, IRLS, visibility and view weights are FROZEN within
each LM run (recomputed between runs), so ``jac`` is the exact Jacobian of ``fun``.

Linear step (DESIGN 4.8 "Solver"): dense Jacobi-scaled Cholesky when the parameter count is
<= 2500; above, the points flagged in ``schur_point_idx`` (3x3 block-diagonal Hessian
blocks) are eliminated by Schur complement (:func:`schur_step`).

Covariance (DESIGN 4.8, 4.13): H = J^T J at the solution (everything frozen), split into
H_data (reprojection and data-term rows) and H_prior (the rest).  ``cov`` is the full
posterior of the points with every other parameter (cameras, phi, theta, zeta, terms)
eliminated by Schur complement; ``cov_shape`` is the same conditional on zeta (template
gauge).  Neither includes sigma_def nor any chi^2 inflation; ``sigma_rep_mm`` =
sqrt(diag(cov_shape) max(1, chi2_red) + sigma_def^2) (WP-16 adds gamma).  With a
non-identity shape model the point covariances are J_S Sigma_qq J_S^T.  Frozen parameters
are conditioned on (see 'frozen views').  ``chi2_red`` = chi^2 / ``chi2_dof`` over the final
inliers with the noise model only (base noise x nu_v^2 / user and visibility weights; the view
weights w_v, which de-duplicate correlated views, are left out), chi2_dof = m_data - p_eff,
p_eff = tr(H_data Sigma), plus with view weighting the first-order excess of
:func:`_view_weight_dof_correction` (a weighted fit does not minimise the unweighted chi^2).

Observation noise resolution is unchanged from WP-07 (``ViewObs.cov_px`` -> ``sigma_px`` ->
:class:`~face3d.solve.noise.NoiseModel` of ``kinds`` at each point's depth).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from ..core.config import Default, register_defaults
from ..geometry.camera import Camera, camera_to_invdepth, invdepth_to_camera
from ..geometry.rotations import rodrigues, rotation_to_rvec, skew
from .lm import levenberg_marquardt
from .noise import NoiseModel, whitening
from .robust import RobustSchedule, huber_weights, nu2_view, tukey_weights, view_chi2_test
from .terms import BLOCK_NAMES, FreePoints, SolverState, shape_n_params

#: Engine version label (scorecards record it; WBS WP-10).
ENGINE_VERSION = "v2"

MIRROR = np.array([-1.0, 1.0, 1.0])

_BRAIN = "\U0001F9E0"   # expert knowledge, provisional
_NEW = "\U0001F195"     # introduced by this design / WP spec, uncalibrated
_ARROWS = "↔️"          # contested

BUNDLE = register_defaults("bundle", {
    # DESIGN D-03 / 4.7: zeta ~ N(0, 0.045^2) is the single population size source
    # (validation-test-bed 'head-size CV ~4-5 %', unverified).
    "scale_sigma_log": Default(0.045, _BRAIN, "DESIGN D-03 / 4.7: zeta ~ N(0, 0.045^2) "
                               "(validation-test-bed head-size CV ~4-5 %)", "log", (1e-6, None)),
    # DESIGN 4.6 'Gauge': six residuals G_a^T (X~_a - mu_a) / 0.01 mm.
    "gauge_sigma_mm": Default(0.01, _NEW, "DESIGN 4.6 gauge: six rigid residuals / 0.01 mm", "mm", (1e-9, None)),
    # WBS WP-07 / legacy bundle.py: ridge 1e-12 * mean(diag H) before inversion.
    "cov_ridge_rel": Default(1e-12, _NEW, "WBS WP-07 covariance ridge 1e-12 * mean(diag) (legacy bundle.py)", "",
                             (0.0, 1e-3)),
    # ---- WP-10 (engine v2) ----
    "rho_min_per_mm": Default(1e-4, _BRAIN, "DESIGN D-02 / 4.3: rho box [1e-4, 4e-3] 1/mm = 10-0.25 m "
                              "(bl C6; DESIGN 4.2)", "1/mm", (1e-9, None)),
    "rho_max_per_mm": Default(4e-3, _BRAIN, "DESIGN D-02 / 4.3: rho box upper bound 4e-3 1/mm = 0.25 m (bl C6)",
                              "1/mm", (1e-9, None)),
    "focal_tie_sigma": Default(0.02, _BRAIN, "DESIGN 4.2 / rec CAM-5: soft focal tie sigma_tie 0.02 in log f "
                               "(passed by the pipeline; None = hard sharing)", "ln f", (1e-9, None)),
    "vis_cos_zero_deg": Default(80.0, _BRAIN, "DESIGN 4.8 / rec BA-3: visibility weight 0 at n.(-v) = cos 80 deg",
                                "deg", (0.0, 180.0)),
    "vis_cos_one_deg": Default(60.0, _BRAIN, "DESIGN 4.8 / rec BA-3: visibility weight 1 at cos 60 deg",
                               "deg", (0.0, 180.0)),
    "contour_far_yaw_deg": Default(25.0, _BRAIN, "DESIGN 4.8: far-side oval points drop out at |yaw| > 25 deg "
                                   "(rec BA-3, bl D2)", "deg", (0.0, 180.0)),
    "view_bin_yaw_deg": Default(15.0, _BRAIN, "DESIGN 4.4 / D-07: view weight 1/n_bin, 15 deg yaw bins ([Rob 3.2], "
                                "com R1.8)", "deg", (1e-6, 360.0)),
    "view_pitch_band_deg": Default(15.0, _NEW, "WBS WP-10: pitch bands < -15, -15..15, > 15 deg", "deg",
                                   (0.0, 90.0)),
    "view_share_cap": Default(0.40, _BRAIN, "DESIGN D-07 / 4.4: no view > 40 % of the shape information "
                              "([Rob 3.2]; com R1.8)", "", (1e-6, 1.0)),
    "view_cap_passes": Default(2, _NEW, "DESIGN 4.4: share cap applied in two passes", "", (1, 100)),
    "jaw_center_x_mm": Default(0.0, _ARROWS, "DESIGN 4.9: hinge on the midline", "mm", (None, None)),
    "jaw_center_y_mm": Default(-5.0, _ARROWS, "DESIGN 4.9: c = mid-tragion + (0, -5, +11.5) mm (0-10 mm inferior; "
                               "bl K8)", "mm", (None, None)),
    "jaw_center_z_mm": Default(11.5, _ARROWS, "DESIGN 4.9: hinge 10-13 mm anterior to tragion (bl K8, BA-1)", "mm",
                               (None, None)),
    "jaw_prior_mean_deg": Default(1.5, _BRAIN, "DESIGN D-14 / 4.9: theta ~ N(1.5 deg, 1 deg^2) on neutral views",
                                  "deg", (None, None)),
    "jaw_prior_sigma_deg": Default(1.0, _BRAIN, "DESIGN D-14 / 4.9: neutral-view sigma 1 deg (3 deg expressive)",
                                   "deg", (1e-9, None)),
    "jaw_bound_max_deg": Default(30.0, _BRAIN, "DESIGN D-14 / 4.9: theta bounded to [0, 30] deg", "deg",
                                 (0.0, 180.0)),
    "dense_max_params": Default(2500, _NEW, "DESIGN 4.8 'Solver': dense Cholesky steps up to 2500 parameters",
                                "", (0, None)),
    "freeze_sigma_rel": Default(1e-6, _NEW, "WBS WP-10: a rejected view's camera block is held by rows "
                                "(p - p_frozen) / (1e-6 x unit)", "", (1e-15, 1.0)),
})

#: Flag raised when the Gauss-Newton Hessian is not positive definite (pinv fallback).
FLAG_COV_SINGULAR = "COV-SINGULAR"
#: Robust-schedule findings (DESIGN 4.5): view rejected by its chi^2 test, noisy view
#: (nu_v > 2), view with more than 15 % of its points rejected.
FLAG_VIEW_REJECT = "F-VIEW-REJECT"
FLAG_VIEW_NOISY = "F-VIEW-NOISY"
FLAG_VIEW_OUTLIERS = "F-VIEW-OUTLIERS"
#: A view left without any usable observation (its camera block is frozen).
FLAG_VIEW_EMPTY = "F-VIEW-EMPTY"

FREE, HARD, FIXED_F = "free", "hard", "fixed_f"
_DEG = 180.0 / math.pi
#: rho in 1/mm per unit of the stored parameter (rho is stored in 1/m; see the module docstring).
RHO_MM_PER_PARAM = 1e-3


@dataclass
class Priors:
    mean: np.ndarray | None = None          # (N,3) prior mean landmark positions (head frame)
    sigma: np.ndarray | float = 8.0         # (N,), (N,3) or scalar, mm
    pairs: list[tuple[int, int]] = field(default_factory=list)  # (left, right) index pairs
    sigma_sym: float | np.ndarray = 2.0     # mm; scalar, (P,) or (P,3) per pair/axis. Asymmetry is real: keep soft
    midline: list[int] = field(default_factory=list)
    sigma_mid: float | np.ndarray = 1.5     # mm; scalar or (M,) per midline landmark


@dataclass
class ScaleConfig:
    """Explicit global log-scale zeta (DESIGN D-03, 4.7): X = e^zeta X~.

    ``enabled``: add zeta to the parameter vector; ``sigma_log``: prior SD of zeta
    (prior mean 0; 0.045 = population head-size CV, 🧠); ``init``: starting value.
    """

    enabled: bool = True
    sigma_log: float = BUNDLE["scale_sigma_log"].value
    init: float = 0.0


@dataclass
class JawConfig:
    """Per-view jaw hinge (DESIGN D-14, 4.9).

    ``enabled`` adds theta_v (radians inside the solver); prior N(prior_mean_deg,
    prior_sigma_deg^2) (1.5 deg / 1 deg on neutral views 🧠; use 3 deg on expressive views);
    ``bounds_deg`` box-projected by the LM ``project`` hook.
    """

    enabled: bool = False
    prior_mean_deg: float = float(BUNDLE["jaw_prior_mean_deg"].value)
    prior_sigma_deg: float = float(BUNDLE["jaw_prior_sigma_deg"].value)
    bounds_deg: tuple[float, float] = (0.0, float(BUNDLE["jaw_bound_max_deg"].value))


@dataclass
class ViewObs:
    uv: np.ndarray                    # (N,2); NaN rows = landmark not visible
    camera: Camera                    # initial camera (pose + focal)
    estimate_focal: bool = True
    f_prior: float | None = None      # px
    f_prior_log_sigma: float = 0.35   # ~0.05 with trustworthy EXIF, 0.25-0.6 when guessed
    weights: np.ndarray | None = None  # (N,) per-landmark confidence (information multiplier)
    # Legacy isotropic landmark noise (px). None (default, WP-07) -> cov_px or the
    # noise model of `kinds` at each point's depth (DESIGN 4.4); an explicit float
    # overrides for backward compatibility.
    sigma_px: float | None = None
    # Views sharing a focal_group share ONE focal length (same camera + zoom): exactly
    # (focal_tie_sigma None) or softly (focal_tie_sigma float, DESIGN 4.2).
    focal_group: str | int | None = None
    kinds: list[str] | None = None            # (N,) landmark kinds (noise.KINDS); None -> 'generic'
    cov_px: np.ndarray | None = None          # (N,2,2) explicit image covariance, px^2 (highest priority)
    multipliers: np.ndarray | None = None     # (N,) occluder / makeup sigma multipliers m_iv (DESIGN 4.1)
    tangents: np.ndarray | None = None        # (N,2) image tangents (NaN / zero rows = unknown)
    tta_px: np.ndarray | None = None          # (N,) test-time-augmentation spread, px
    face_px: float | None = None              # face width in px (detector floor); None -> landmark bbox width
    dense_mask: np.ndarray | None = None      # (N,) bool dense detector points (eta = N / N_eff inflation)
    # ---- WP-10 additions (DESIGN 4.2, 4.3, 4.9) ----
    # Soft focal tie in ln f to the group's phi_G; None = hard sharing (legacy, exact).
    # The pipeline passes 0.02 (rec CAM-5).
    focal_tie_sigma: float | None = None
    # (median distance in mm from the camera to the head-frame origin, sigma of ln):
    # residual (-ln rho - ln median) / sigma_log (DESIGN 4.2; never derived from IOD pixels).
    distance_prior: tuple[float, float] | None = None
    # (yaw_deg, pitch_deg, sigma_yaw_deg, sigma_pitch_deg) of the camera centre in the head
    # frame (yaw = atan2(C_x, C_z), pitch = asin(C_y / |C|); DESIGN 4.2 pose tags).
    pose_tag: tuple[float, float, float, float] | None = None
    jaw: JawConfig = field(default_factory=JawConfig)


@dataclass
class BundleResult:
    X: np.ndarray
    cameras: list[Camera]
    rmse_px: list[float]
    cost: float
    iterations: int
    per_view_residuals: list[np.ndarray]
    # 1-sigma posterior uncertainty of each 3D landmark (mm, per axis, head frame):
    # sqrt(diag(cov_shape)), the Gauss-Newton covariance conditional on zeta. Large
    # values mark landmarks the photos barely constrain (e.g. depth of a frontal-only
    # nose tip) where the result is mostly prior.
    point_sigma_mm: np.ndarray | None = None
    # ---- WP-07 additions (all optional; DESIGN 4.8, 4.13) ----
    cov: np.ndarray | None = None            # (3N,3N) mm^2, full posterior (all else eliminated), template gauge
    cov_shape: np.ndarray | None = None      # (3N,3N) mm^2, conditional on zeta
    zeta: float | None = None                # global log-scale (None when disabled)
    zeta_sigma: float | None = None
    # sum r_data^2 / chi2_dof over the final inliers, residuals WITHOUT the view weights
    # (noise model only), chi2_dof = m_data - p_eff (+ view-weight correction), p_eff = tr(H_data Sigma)
    chi2_red: float | None = None
    sigma_def_mm: np.ndarray | None = None   # (N,) definition-bias floor (D-06)
    sigma_rep_mm: np.ndarray | None = None   # (N,3) sqrt(diag(cov_shape) max(1, chi2_red) + sigma_def^2)
    # per view: cov of the camera block in the solver parameterisation
    # [omega 3 | tau 2 mm | rho (1/m) | a (FREE)] + [phi_G] for grouped views (7x7, 8x8 or 6x6 FIXED_F)
    camera_cov: list[np.ndarray] | None = None
    H_data: np.ndarray | None = None         # (n,n) J_data^T J_data at the solution
    H_prior: np.ndarray | None = None        # (n,n) J_prior^T J_prior at the solution
    param_index: dict | None = None          # name -> slice into the parameter vector
    obs_cov_px: list[np.ndarray] | None = None  # per view (N,2,2) px^2 noise of the final round (incl. nu^2; NaN hidden)
    m_data: int | None = None                # number of data residual rows (reprojection + data terms)
    p_eff: float | None = None               # tr(H_data Sigma)
    cov_ridge: float | None = None           # ridge added to diag(H) before inversion
    flags: list[str] = field(default_factory=list)
    engine_version: str = ENGINE_VERSION
    # ---- WP-10 additions ----
    # per view {nu, rejected_frac, chi2, dof, chi2_threshold, flags, weight_share, view_weight,
    # sigma_logf, sigma_logz, jaw_deg, jaw_sigma_deg, yaw_deg, pitch_deg, n_inliers, kind, frozen}
    # (+ chi2_test, chi2_test_threshold, dof_test with a robust schedule).  A frozen view (rejected
    # or empty) has sigma_logz, jaw_sigma_deg and, unless HARD (f = e^phi_G), sigma_logf None:
    # its block is held, not estimated (its camera_cov entries are zero).
    view_stats: list[dict] | None = None
    # per view (N,) bool: observation used in the final solve (visible, visibility weight > 0,
    # not rejected by the robust schedule, view not rejected)
    inlier_mask: list[np.ndarray] | None = None
    term_params: dict | None = None          # term name -> (k,) solved parameters
    # denominator of chi2_red: m_data - p_eff (+ the view-weight correction of
    # _view_weight_dof_correction when view weighting is on; exactly m_data - p_eff otherwise)
    chi2_dof: float | None = None


# =========================================================================== layout
class _Layout:
    """Parameter vector layout (see the module docstring).

    ``param_index()`` keys: ``cam_<v>`` (the view's whole block), ``pose_<v>`` (omega, tau,
    rho), ``omega_<v>``, ``tau_<v>``, ``rho_<v>`` (stored in 1/m), ``a_<v>`` (FREE views),
    ``phi_<j>`` (focal groups), ``focal_<j>`` (the parameters carrying a focal prior: each
    group's phi and each ungrouped FREE view's a, in parameter order; the legacy name),
    ``cameras`` (all camera and phi parameters), ``jaw_<v>``, ``zeta``, ``points`` (the shape
    parameters) and ``term:<name>``.
    """

    def __init__(self, views: list[ViewObs], n_pts: int, zeta: bool = False, n_shape: int | None = None,
                 term_sizes: Sequence[tuple[str, int]] = ()):
        self.n_pts = n_pts
        self.kind: list[str] = []
        self.view_off: list[int] = []
        self.block_size: list[int] = []
        off = 0
        for v in views:
            if not v.estimate_focal:
                kind = FIXED_F
            elif v.focal_group is not None and v.focal_tie_sigma is None:
                kind = HARD
            else:
                kind = FREE
            size = 7 if kind == FREE else 6
            self.kind.append(kind)
            self.view_off.append(off)
            self.block_size.append(size)
            off += size
        self.rho_idx = [o + 5 for o in self.view_off]
        self.a_idx = [o + 6 if kd == FREE else -1 for o, kd in zip(self.view_off, self.kind)]
        self.cam_end = off
        # focal groups: one phi per group holding at least one HARD or soft-tied FREE view
        self.phi_idx = [-1] * len(views)
        self.tie_sigma: list[float | None] = [None] * len(views)
        self.group_views: dict[int, list[int]] = {}
        key_to_idx: dict = {}
        for k, v in enumerate(views):
            if not v.estimate_focal or v.focal_group is None:
                continue
            key = v.focal_group
            if key not in key_to_idx:
                key_to_idx[key] = off
                off += 1
            idx = key_to_idx[key]
            self.phi_idx[k] = idx
            self.group_views.setdefault(idx, []).append(k)
            if self.kind[k] == FREE:
                self.tie_sigma[k] = float(v.focal_tie_sigma)
        self.focal_end = off
        # focal priors: on phi (tightest of the group) or on a_v - ln rho_v (ungrouped FREE)
        self.focal_carriers: list[tuple[int, int | None]] = []   # (param idx, view k for 'a' carriers)
        for k, kd in enumerate(self.kind):
            if kd == FREE and self.phi_idx[k] < 0:
                self.focal_carriers.append((self.a_idx[k], k))
        for idx in sorted(self.group_views):
            self.focal_carriers.append((idx, None))
        self.focal_carriers.sort(key=lambda c: c[0])
        self.focal_prior: list[tuple[int, int | None, float, float]] = []   # (idx, k|None, ln fp, sigma)
        for idx, k in self.focal_carriers:
            ks = [k] if k is not None else self.group_views[idx]
            cands = [(views[j].f_prior_log_sigma, views[j].f_prior) for j in ks if views[j].f_prior is not None]
            if cands:
                sig, fp = min(cands)
                self.focal_prior.append((idx, k, float(np.log(fp)), float(sig)))
        # jaw hinge angles
        self.jaw_idx = [-1] * len(views)
        for k, v in enumerate(views):
            if v.jaw is not None and v.jaw.enabled:
                self.jaw_idx[k] = off
                off += 1
        self.jaw_end = off
        self.zeta_idx = -1
        if zeta:
            self.zeta_idx = off
            off += 1
        self.pts_off = off
        self.n_shape = 3 * n_pts if n_shape is None else int(n_shape)
        self.pts_end = off + self.n_shape
        off = self.pts_end
        self.term_off: list[int] = []
        self.term_names: list[str] = []
        for name, size in term_sizes:
            self.term_off.append(off)
            self.term_names.append(name)
            off += int(size)
        self.term_sizes = [int(s) for _, s in term_sizes]
        self.n = off

    def param_index(self) -> dict:
        out: dict[str, slice] = {}
        for k, o in enumerate(self.view_off):
            out[f"cam_{k}"] = slice(o, o + self.block_size[k])
            out[f"pose_{k}"] = slice(o, o + 6)
            out[f"omega_{k}"] = slice(o, o + 3)
            out[f"tau_{k}"] = slice(o + 3, o + 5)
            out[f"rho_{k}"] = slice(o + 5, o + 6)
            if self.a_idx[k] >= 0:
                out[f"a_{k}"] = slice(o + 6, o + 7)
        for j, (idx, _) in enumerate(self.focal_carriers):
            out[f"focal_{j}"] = slice(idx, idx + 1)
        for j, idx in enumerate(sorted(self.group_views)):
            out[f"phi_{j}"] = slice(idx, idx + 1)
        out["cameras"] = slice(0, self.focal_end)
        for k, ji in enumerate(self.jaw_idx):
            if ji >= 0:
                out[f"jaw_{k}"] = slice(ji, ji + 1)
        if self.zeta_idx >= 0:
            out["zeta"] = slice(self.zeta_idx, self.zeta_idx + 1)
        out["points"] = slice(self.pts_off, self.pts_end)
        for name, o, s in zip(self.term_names, self.term_off, self.term_sizes):
            out[f"term:{name}"] = slice(o, o + s)
        return out


def _pack(views: list[ViewObs], q0: np.ndarray, lay: _Layout, zeta0: float = 0.0,
          rho_box: tuple[float, float] | None = None) -> np.ndarray:
    """Initial parameter vector from the views' cameras (inverse depth, WP-06), q0 and zeta0."""
    p = np.zeros(lay.n)
    for k, v in enumerate(views):
        o = lay.view_off[k]
        d = camera_to_invdepth(v.camera)
        rho = d["rho"] if rho_box is None else float(np.clip(d["rho"], rho_box[0], rho_box[1]))
        p[o:o + 3] = rotation_to_rvec(d["R"])
        p[o + 3:o + 5] = d["tau"]
        p[o + 5] = rho / RHO_MM_PER_PARAM
        if lay.kind[k] == FREE:
            p[o + 6] = float(np.log(v.camera.f * rho))
    for idx, ks in lay.group_views.items():
        p[idx] = float(np.mean([np.log(views[k].camera.f) for k in ks]))
    for k, ji in enumerate(lay.jaw_idx):
        if ji >= 0:
            jc = views[k].jaw
            lo, hi = np.radians(jc.bounds_deg)
            p[ji] = float(np.clip(np.radians(jc.prior_mean_deg), lo, hi))
    if lay.zeta_idx >= 0:
        p[lay.zeta_idx] = float(zeta0)
    p[lay.pts_off:lay.pts_end] = np.asarray(q0, float).reshape(-1)
    return p


# =========================================================================== noise
class _ViewNoise:
    """Frozen noise of one view for one LM run: isotropic sigma (legacy) or whitening W."""

    __slots__ = ("iso", "sigma", "W", "C")

    def __init__(self, iso: bool, sigma: Any = None, W: np.ndarray | None = None, C: np.ndarray | None = None):
        self.iso = iso
        self.sigma = sigma      # float or (n_vis,) px (iso)
        self.W = W              # (n_vis, 2, 2) inverse lower Cholesky factors (full)
        self.C = C              # (n_vis, 2, 2) px^2 (full)

    def cov_full(self, m: np.ndarray, scale2: float = 1.0) -> np.ndarray:
        """(N,2,2) px^2 with NaN rows where hidden, times ``scale2`` (nu^2)."""
        N = len(m)
        out = np.full((N, 2, 2), np.nan)
        if self.iso:
            s2 = np.broadcast_to(np.asarray(self.sigma, float) ** 2, (int(m.sum()),))
            blk = np.zeros((len(s2), 2, 2))
            blk[:, 0, 0] = s2
            blk[:, 1, 1] = s2
            out[m] = blk * scale2
        else:
            out[m] = self.C * scale2
        return out


def _face_width_px(uv_vis: np.ndarray) -> float | None:
    """Face width in px from the visible landmarks' u extent (WP-07 default, 🆕 provisional)."""
    if len(uv_vis) < 2:
        return None
    return float(np.max(uv_vis[:, 0]) - np.min(uv_vis[:, 0]))


def view_noise_cov(view: ViewObs, X: np.ndarray, R: np.ndarray, t: np.ndarray, f: float) -> np.ndarray:
    """(N,2,2) image covariance (px^2) of ``view`` at the estimate (X, R, t, f); NaN rows where hidden.

    Resolution order (WBS WP-07): ``view.cov_px`` -> ``view.sigma_px`` (isotropic) ->
    :class:`~face3d.solve.noise.NoiseModel` of ``view.kinds`` (or 'generic') with
    px_per_mm_i = f / z_i at the current depth z_i of each landmark (DESIGN 4.4, D-05).
    """
    m = ~np.isnan(np.asarray(view.uv, float)[:, 0])
    return _resolve_view_noise(view, np.asarray(X, float), R, t, f, m).cov_full(m)


def _resolve_view_noise(v: ViewObs, X: np.ndarray, R: np.ndarray, t: np.ndarray, f: float,
                        m: np.ndarray) -> _ViewNoise:
    N = len(m)
    if v.cov_px is not None:
        C = np.asarray(v.cov_px, float)
        if C.shape != (N, 2, 2):
            raise ValueError(f"ViewObs.cov_px must have shape ({N}, 2, 2), got {C.shape}")
        Cm = 0.5 * (C[m] + np.swapaxes(C[m], 1, 2))
        if not np.isfinite(Cm).all():
            raise ValueError("ViewObs.cov_px has non-finite entries for visible landmarks")
        return _ViewNoise(False, W=whitening(Cm), C=Cm)
    if v.sigma_px is not None:
        s = v.sigma_px
        if np.ndim(s) == 0:
            s = float(s)
            if not s > 0:
                raise ValueError("ViewObs.sigma_px must be > 0")
            return _ViewNoise(True, sigma=s)
        sa = np.asarray(s, float).reshape(-1)
        if sa.shape != (N,):
            raise ValueError(f"ViewObs.sigma_px must be a float or ({N},), got {np.shape(s)}")
        sm = sa[m]
        if not np.all(sm > 0):
            raise ValueError("ViewObs.sigma_px must be > 0 for visible landmarks")
        return _ViewNoise(True, sigma=sm)
    kinds = v.kinds if v.kinds is not None else ["generic"] * N
    if len(kinds) != N:
        raise ValueError(f"ViewObs.kinds has {len(kinds)} entries for {N} landmarks")
    # Non-finite multipliers / TTA spreads on visible landmarks would turn every
    # residual into NaN and LM would silently return the initial estimate: reject
    # them here, as the cov_px branch does (hidden rows may hold anything).
    for name, a in (("multipliers", v.multipliers), ("tta_px", v.tta_px)):
        if a is None:
            continue
        arr = np.asarray(a, float)
        if arr.ndim:
            arr = arr.reshape(-1)
            if arr.shape != (N,):
                raise ValueError(f"ViewObs.{name} must be a float or ({N},), got {np.shape(a)}")
            arr = arr[m]
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"ViewObs.{name} has non-finite entries for visible landmarks")
    model = NoiseModel(kinds, dense_mask=v.dense_mask)
    z = (X[m] @ R.T + t)[:, 2]
    ppm = np.full(N, np.nan)
    ppm[m] = f / np.maximum(np.abs(z), 1e-6)
    face = v.face_px if v.face_px is not None else _face_width_px(np.asarray(v.uv, float)[m])
    C = model.view_cov(ppm, face, tangents=v.tangents, multipliers=v.multipliers, tta_px=v.tta_px)[m]
    if not np.isfinite(C).all():
        raise ValueError("noise-model covariance is non-finite for visible landmarks "
                         "(non-finite camera, focal or landmark estimate?)")
    return _ViewNoise(False, W=whitening(C), C=C)


# =========================================================================== shape terms
class _LegacyShape:
    """Legacy Priors.mean / sigma term: ((X~ - mean) / sigma).ravel()."""

    def __init__(self, mean: np.ndarray, sig: np.ndarray):
        self.mean = np.asarray(mean, float)
        self.sig = sig
        self._J = np.diag(1.0 / sig.ravel())

    def residual(self, Xt: np.ndarray) -> np.ndarray:
        return ((Xt - self.mean) / self.sig).ravel()

    def jacobian(self, Xt: np.ndarray) -> np.ndarray:
        return self._J


class _PriorShape:
    """A LandmarkPrior over the global point array (WP-03 protocol).

    Uses the generalised ``residual(X_all)`` / ``jacobian(X_all)`` interface when the
    prior offers it (joint-index priors, CompositePrior, bound priors); otherwise the
    plain protocol W vec(X~ - mean) with ``len(mean) == N``.
    """

    def __init__(self, prior: Any, N: int):
        self.prior = prior
        self.N = N
        self.general = hasattr(prior, "residual") and hasattr(prior, "jacobian")
        if not self.general:
            mu = np.asarray(prior.mean(), float)
            if mu.shape != (N, 3):
                raise ValueError(f"prior mean has shape {mu.shape}; a prior without the generalised "
                                 f"residual/jacobian interface must cover all {N} points")
            self.mu = mu.ravel()
            self.W = np.asarray(prior.whiten_matrix(), float)

    def residual(self, Xt: np.ndarray) -> np.ndarray:
        if self.general:
            return np.asarray(self.prior.residual(Xt), float).reshape(-1)
        return self.W @ (Xt.ravel() - self.mu)

    def jacobian(self, Xt: np.ndarray) -> np.ndarray:
        if self.general:
            J = np.asarray(self.prior.jacobian(Xt), float)
            if J.ndim != 2 or J.shape[1] != 3 * self.N:
                raise ValueError(f"prior jacobian has shape {J.shape}, expected (m, {3 * self.N})")
            return J
        return self.W


def _coord_cols(idx: np.ndarray) -> np.ndarray:
    return (3 * np.asarray(idx, np.int64)[:, None] + np.arange(3)).reshape(-1)


def _rigid_rows(ref: np.ndarray) -> np.ndarray:
    """Six unit-norm rigid gauge rows (6, 3n) on points ``ref`` (n, 3).

    Same construction as ``FactorPrior.rigid_gauge_rows`` (WP-03): rows 0-2 mean
    displacement, rows 3-5 infinitesimal rotation about the centroid.
    """
    D = ref - ref.mean(axis=0)
    r_rms = float(np.sqrt(np.mean(np.sum(D * D, axis=1))))
    n = len(ref)
    G = np.zeros((6, 3 * n))
    eye = np.eye(3)
    for k in range(3):
        G[k, k::3] = 1.0 / n
        G[3 + k] = (np.cross(eye[k], D) / max(r_rms, 1e-300)).reshape(-1)
    norms = np.linalg.norm(G, axis=1)
    if np.any(norms < 1e-12):
        raise ValueError("gauge anchors are degenerate (collinear or coincident)")
    return G / norms[:, None]


def _gauge_rows(prior: Any, N: int, anchor_idx: Sequence[int] | None, X0: np.ndarray
                ) -> tuple[np.ndarray, np.ndarray] | None:
    """(G (6, 3N), mu (3N,)) of the six rigid gauge residuals, or None.

    Only for a prior whose ``meta['rigid_invariant']`` is true (DESIGN 4.6).
    ``anchor_idx`` are GLOBAL point indices (rows of X).  With a prior that offers
    ``rigid_gauge_rows`` and ``mean`` (FactorPrior / DiagonalPrior), the rows and the
    reference mu come from the prior (default anchors: the registry anchors present
    in the prior, else all of its points).  Otherwise (e.g. a CompositePrior) the
    rows are built on X0 at the anchors (default: all points), with mu = X0.
    """
    meta = getattr(prior, "meta", None) or {}
    if not meta.get("rigid_invariant", False):
        return None
    G = np.zeros((6, 3 * N))
    mu_full = np.zeros(3 * N)
    if hasattr(prior, "rigid_gauge_rows") and hasattr(prior, "mean"):
        mu = np.asarray(prior.mean(), float)
        n_p = len(mu)
        index = getattr(prior, "index", None)
        if index is None:
            if n_p != N:
                raise ValueError(f"prior covers {n_p} points but X has {N}; bind it with with_index()")
            glob = np.arange(N)
        else:
            glob = np.asarray(index, np.int64)
        if anchor_idx is None:
            try:
                Gl = prior.rigid_gauge_rows(None)
            except (ValueError, KeyError):
                Gl = prior.rigid_gauge_rows(list(range(n_p)))
        else:
            pos = {int(g): i for i, g in enumerate(glob)}
            try:
                local = [pos[int(a)] for a in anchor_idx]
            except KeyError as e:
                raise ValueError(f"gauge anchor {e.args[0]} is not covered by the prior") from None
            Gl = prior.rigid_gauge_rows(local)
        cols = _coord_cols(glob)
        G[:, cols] = np.asarray(Gl, float)
        mu_full[cols] = mu.ravel()
        return G, mu_full
    A = np.arange(N) if anchor_idx is None else np.asarray(anchor_idx, np.int64).reshape(-1)
    if len(A) < 3:
        raise ValueError("rigid gauge needs at least 3 anchors")
    cols = _coord_cols(A)
    ref = np.asarray(X0, float)[A]
    G[:, cols] = _rigid_rows(ref)
    mu_full[cols] = ref.ravel()
    return G, mu_full


# =========================================================================== linear algebra
def _inv_spd(M: np.ndarray) -> np.ndarray:
    """Inverse of a symmetric positive definite matrix via Jacobi-scaled Cholesky.

    Raises ``numpy.linalg.LinAlgError`` if M is not positive definite.
    """
    M = 0.5 * (M + M.T)
    d = np.diag(M).copy()
    if not np.all(d > 0):
        raise np.linalg.LinAlgError("non-positive diagonal")
    s = 1.0 / np.sqrt(d)
    L = np.linalg.cholesky(M * s[:, None] * s[None, :])
    Li = np.linalg.solve(L, np.eye(len(L)))
    out = (Li.T @ Li) * s[:, None] * s[None, :]
    return 0.5 * (out + out.T)


def _chol_solve(A: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Solve the SPD system A x = b by Jacobi-scaled Cholesky (``LinAlgError`` if not PD)."""
    d = np.diag(A).copy()
    if not np.all(d > 0):
        raise np.linalg.LinAlgError("non-positive diagonal")
    s = 1.0 / np.sqrt(d)
    L = np.linalg.cholesky(A * s[:, None] * s[None, :])
    y = np.linalg.solve(L, b * s)
    return np.linalg.solve(L.T, y) * s


def dense_step(H: np.ndarray, lam_diag: np.ndarray, g: np.ndarray) -> np.ndarray:
    """LM step dx = -(H + diag(lam_diag))^-1 g by dense Jacobi-scaled Cholesky (DESIGN 4.8)."""
    A = H + np.diag(lam_diag)
    return -_chol_solve(0.5 * (A + A.T), g)


def schur_step(H: np.ndarray, lam_diag: np.ndarray, g: np.ndarray, elim_cols: np.ndarray) -> np.ndarray:
    """LM step by eliminating 3x3 block-diagonal point blocks (DESIGN 4.8 "Solver").

    ``elim_cols`` (3m,) are the parameter columns of m points, three consecutive
    columns per point.  With A = H + diag(lam_diag), E = ``elim_cols`` and R the rest,
    A_EE must be block-diagonal in 3x3 blocks (no factor-prior coupling); then

        S = A_RR - A_RE A_EE^-1 A_ER,   S dx_R = -(g_R - A_RE A_EE^-1 g_E),
        dx_E = -A_EE^-1 (g_E + A_ER dx_R).

    Falls back to :func:`dense_step` when A_EE is not block-diagonal.  Equals the dense
    step up to rounding (WBS WP-10: 1e-8 relative).
    """
    E = np.asarray(elim_cols, np.int64).reshape(-1)
    n = len(g)
    if E.size == 0 or E.size % 3:
        return dense_step(H, lam_diag, g)
    m = E.size // 3
    E3 = E.reshape(m, 3)
    mask = np.ones(n, bool)
    mask[E] = False
    Rc = np.flatnonzero(mask)
    A_EE = H[np.ix_(E, E)]
    blk = A_EE.reshape(m, 3, m, 3)
    off = blk.copy()
    off[np.arange(m), :, np.arange(m), :] = 0.0
    if np.any(off != 0.0):
        return dense_step(H, lam_diag, g)
    B = H[E3[:, :, None], E3[:, None, :]].copy()                      # (m, 3, 3)
    B[:, np.arange(3), np.arange(3)] += lam_diag[E3]
    B = 0.5 * (B + np.swapaxes(B, 1, 2))
    Binv = np.linalg.inv(B)
    A_RE = H[np.ix_(Rc, E)]
    r = len(Rc)
    ARE_B = np.einsum("rmi,mij->rmj", A_RE.reshape(r, m, 3), Binv).reshape(r, 3 * m)
    S = H[np.ix_(Rc, Rc)] + np.diag(lam_diag[Rc]) - ARE_B @ A_RE.T
    gE = g[E]
    rhs = -(g[Rc] - ARE_B @ gE)
    dR = _chol_solve(0.5 * (S + S.T), rhs)
    tmp = (gE + A_RE.T @ dR).reshape(m, 3)
    dE = -np.einsum("mij,mj->mi", Binv, tmp).reshape(-1)
    dx = np.empty(n)
    dx[Rc] = dR
    dx[E] = dE
    return dx


@dataclass
class _SubLayout:
    """The fields of :class:`_Layout` that :func:`_posterior` reads (a reduced layout)."""

    pts_off: int
    pts_end: int
    n: int
    zeta_idx: int


def _schur_inverse(H: np.ndarray, c: np.ndarray, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Full inverse of SPD ``H`` by eliminating the block ``c`` (cameras) onto ``x`` (points).

    Returns ``(Sigma (n, n), Sigma_xx)`` with Sigma_xx = (H_xx - H_xc H_cc^-1 H_cx)^-1
    (the Schur complement), Sigma_cx = -H_cc^-1 H_cx Sigma_xx and
    Sigma_cc = H_cc^-1 + H_cc^-1 H_cx Sigma_xx H_xc H_cc^-1.
    """
    Hcc = H[np.ix_(c, c)]
    Hcx = H[np.ix_(c, x)]
    Hxx = H[np.ix_(x, x)]
    Hcc_inv = _inv_spd(Hcc) if len(c) else np.zeros((0, 0))
    A = Hcc_inv @ Hcx                           # H_cc^-1 H_cx
    S = Hxx - Hcx.T @ A
    Sxx = _inv_spd(S)
    Scx = -A @ Sxx
    Scc = Hcc_inv + A @ Sxx @ A.T
    n = len(H)
    Sig = np.zeros((n, n))
    Sig[np.ix_(c, c)] = 0.5 * (Scc + Scc.T)
    Sig[np.ix_(c, x)] = Scx
    Sig[np.ix_(x, c)] = Scx.T
    Sig[np.ix_(x, x)] = Sxx
    return Sig, Sxx


def _posterior_fixed(H: np.ndarray, lay: Any, ridge_rel: float, fixed: np.ndarray | None) -> dict:
    """:func:`_posterior` conditional on the parameters ``fixed`` (held, not estimated).

    ``fixed``: parameter indices of the blocks of frozen views (and orphaned phi), whose
    stiff holding rows would otherwise dominate trace(H) and with it the ridge, making every
    point covariance overconfident.  Their rows and columns are removed from H before the
    ridge and the inversion (conditioning on them), and their rows and columns of Sigma are
    zero.  They must lie outside the point block and differ from zeta.  Without fixed
    parameters this is exactly ``_posterior(H, lay, ridge_rel)``.
    """
    n = len(H)
    fx = np.zeros(0, np.int64) if fixed is None else np.unique(np.asarray(fixed, np.int64).reshape(-1))
    if fx.size == 0:
        return _posterior(H, lay, ridge_rel)
    pts_end = int(getattr(lay, "pts_end", lay.n))
    zi = int(lay.zeta_idx)
    if np.any((fx >= lay.pts_off) & (fx < pts_end)) or zi in set(fx.tolist()):
        raise ValueError("fixed parameters must lie outside the point block and differ from zeta")
    keep = np.setdiff1d(np.arange(n), fx)
    shift_pts = int(np.sum(fx < lay.pts_off))
    sub = _SubLayout(pts_off=int(lay.pts_off) - shift_pts, pts_end=pts_end - shift_pts, n=len(keep),
                     zeta_idx=zi - int(np.sum(fx < zi)) if zi >= 0 else -1)
    out = dict(_posterior(H[np.ix_(keep, keep)], sub, ridge_rel))
    Sig = np.zeros((n, n))
    Sig[np.ix_(keep, keep)] = out["Sigma"]
    out["Sigma"] = Sig
    return out


def _posterior(H: np.ndarray, lay: Any, ridge_rel: float) -> dict:
    """Sigma (full), cov (points, unconditional) and cov_shape (points, conditional on zeta).

    ``lay`` needs ``pts_off``, ``n`` and ``zeta_idx`` (and optionally ``pts_end``, default
    ``n``): the point (shape-parameter) block is [pts_off, pts_end); every other
    parameter is eliminated by Schur complement.  (Frozen parameters: :func:`_posterior_fixed`.)
    """
    n = len(H)
    pts_end = int(getattr(lay, "pts_end", lay.n))
    ridge = ridge_rel * max(float(np.trace(H)) / n, 1e-300)
    Hr = H.copy()
    Hr[np.diag_indices_from(Hr)] += ridge
    x = np.arange(lay.pts_off, pts_end)
    xmask = np.zeros(n, bool)
    xmask[x] = True
    c = np.flatnonzero(~xmask)
    zi = int(lay.zeta_idx)
    flags: list[str] = []
    if zi >= 0:
        keep = np.array([i for i in range(n) if i != zi])
        pos = np.full(n, -1)
        pos[keep] = np.arange(len(keep))
        xk = pos[x]
        ck = pos[c[c != zi]]
    try:
        Sig, cov = _schur_inverse(Hr, c, x)
        if zi >= 0:
            _, cov_shape = _schur_inverse(Hr[np.ix_(keep, keep)], ck, xk)
        else:
            cov_shape = cov
    except np.linalg.LinAlgError:
        flags.append(FLAG_COV_SINGULAR)
        Sig = np.linalg.pinv(0.5 * (Hr + Hr.T), hermitian=True)
        cov = Sig[np.ix_(x, x)]
        if zi >= 0:
            Hk = Hr[np.ix_(keep, keep)]
            Sk = np.linalg.pinv(0.5 * (Hk + Hk.T), hermitian=True)
            cov_shape = Sk[np.ix_(xk, xk)]
        else:
            cov_shape = cov
    return {"Sigma": Sig, "cov": 0.5 * (cov + cov.T), "cov_shape": 0.5 * (cov_shape + cov_shape.T),
            "ridge": ridge, "flags": flags}


def _resolve_scale(scale: Any, prior: Any) -> ScaleConfig:
    if isinstance(scale, str):
        if scale != "auto":
            raise ValueError(f"scale must be 'auto', None or a ScaleConfig, not {scale!r}")
        return ScaleConfig() if prior is not None else ScaleConfig(enabled=False)
    if scale is None:
        return ScaleConfig(enabled=False)
    if isinstance(scale, ScaleConfig):
        if scale.enabled and not scale.sigma_log > 0:
            raise ValueError("ScaleConfig.sigma_log must be > 0")
        return scale
    raise TypeError(f"scale must be 'auto', None or a ScaleConfig, not {type(scale).__name__}")


def _default_sigma_def(views: list[ViewObs], N: int) -> np.ndarray:
    for v in views:
        if v.kinds is not None:
            if len(v.kinds) != N:
                raise ValueError(f"ViewObs.kinds has {len(v.kinds)} entries for {N} landmarks")
            return NoiseModel(v.kinds).sigma_def_mm()
    return np.zeros(N)


def _resolve_sigma_def(sigma_def_mm: Any, views: list[ViewObs], N: int) -> np.ndarray:
    """(N,) definition-bias floor in mm: validated ``sigma_def_mm`` (scalar or (N,), finite,
    >= 0) or the default from the views' ``kinds`` (zeros without kinds)."""
    if sigma_def_mm is None:
        return _default_sigma_def(views, N)
    a = np.asarray(sigma_def_mm, float)
    if a.ndim == 0:
        a = np.full(N, float(a))
    elif a.shape != (N,):
        raise ValueError(f"sigma_def_mm must be a float or ({N},), got {a.shape}")
    else:
        a = a.copy()
    if not np.all(np.isfinite(a)) or np.any(a < 0):
        raise ValueError("sigma_def_mm must be finite and >= 0")
    return a


def _skews(Y: np.ndarray) -> np.ndarray:
    """Stack of cross-product matrices [Y_i]_x, (n, 3, 3)."""
    S = np.zeros((len(Y), 3, 3))
    S[:, 0, 1], S[:, 0, 2] = -Y[:, 2], Y[:, 1]
    S[:, 1, 0], S[:, 1, 2] = Y[:, 2], -Y[:, 0]
    S[:, 2, 0], S[:, 2, 1] = -Y[:, 1], Y[:, 0]
    return S


def _rot_x(th: float) -> tuple[np.ndarray, np.ndarray]:
    """R_x(theta) and dR_x/dtheta."""
    c, s = math.cos(th), math.sin(th)
    return (np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]]),
            np.array([[0.0, 0.0, 0.0], [0.0, -s, -c], [0.0, c, -s]]))


def jaw_hinge(X: np.ndarray, weights: np.ndarray, theta: float,
              center: Sequence[float] = (0.0, -5.0, 11.5)) -> np.ndarray:
    """X_iv = X_i + w_i (R_x(theta)(X_i - c) - (X_i - c)) (DESIGN 4.9; theta in radians, mm)."""
    Rx, _ = _rot_x(float(theta))
    D = np.asarray(X, float) - np.asarray(center, float)
    w = np.asarray(weights, float).reshape(-1, 1)
    return np.asarray(X, float) + w * (D @ Rx.T - D)


def camera_angles_deg(cam: Camera) -> tuple[float, float]:
    """(yaw, pitch) in degrees of the camera centre C in the head frame (DESIGN 4.2 pose tags):
    yaw = atan2(C_x, C_z), pitch = asin(C_y / |C|)."""
    C = cam.center
    return float(np.degrees(np.arctan2(C[0], C[2]))), float(np.degrees(np.arctan2(C[1], np.hypot(C[0], C[2]))))


def _exp(x: float) -> float:
    """exp that returns inf instead of raising (an LM trial step may overshoot; its cost is then rejected)."""
    with np.errstate(over="ignore"):
        return float(np.exp(x))


def _log(x: float) -> float:
    """log that returns nan / -inf instead of raising (out-of-domain LM trial points are rejected)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return float(np.log(x))


def _wrap_deg(a: float) -> float:
    return (a + 180.0) % 360.0 - 180.0


# =========================================================================== problem
class _Problem:
    """Residuals, exact Jacobian and the frozen per-round state of one bundle solve."""

    def __init__(self, views: list[ViewObs], N: int, lay: _Layout, shape: Any, sc: ScaleConfig,
                 shape_term: Any, gauge: Any, pairs: np.ndarray, mid: np.ndarray, S_sym: np.ndarray,
                 S_mid: np.ndarray, base_w: list[np.ndarray], vis: list[np.ndarray], terms: list,
                 normals: np.ndarray | None, jaw_w: np.ndarray | None, jaw_c: np.ndarray,
                 view_weighting: bool, step_solver: Any):
        self.views, self.N, self.lay, self.shape, self.sc = views, N, lay, shape, sc
        self.V = len(views)
        self.identity = bool(getattr(shape, "is_identity", False))
        self.shape_term, self.gauge = shape_term, gauge
        self.pairs, self.mid, self.S_sym, self.S_mid = pairs, mid, S_sym, S_mid
        self.base_w, self.vis = base_w, vis
        self.terms = terms
        self.normals, self.jaw_w, self.jaw_c = normals, jaw_w, jaw_c
        self.normal_unknown = np.zeros(N, bool)
        self.view_weighting = view_weighting
        self.step_solver = step_solver
        self.gauge_sigma = float(BUNDLE["gauge_sigma_mm"].value)
        self.rho_box = (float(BUNDLE["rho_min_per_mm"].value), float(BUNDLE["rho_max_per_mm"].value))
        self.uv = [np.asarray(v.uv, float) for v in views]
        self.cxy = [np.array([v.camera.cx, v.camera.cy], float) for v in views]
        self.f_fixed = [float(v.camera.f) for v in views]
        self.contour = [None if v.kinds is None else np.array([k == "contour" for k in v.kinds], bool)
                        for v in views]
        # ext layout: identical to the real one except that the shape block is 3N wide (X space)
        self.n_ext = lay.pts_off + 3 * N + (lay.n - lay.pts_end)
        self.ext_term_off = [o - lay.pts_end + lay.pts_off + 3 * N for o in lay.term_off]
        # frozen per-round state
        self.noise: list[_ViewNoise | None] = [None] * self.V
        self.iso = [True] * self.V
        self.sig = [np.full(N, np.nan) for _ in views]
        self.W = [np.full((N, 2, 2), np.nan) for _ in views]
        self.nu = np.ones(self.V)
        self.irls = [np.ones(N) for _ in views]
        self.vis_w = [np.ones(N) for _ in views]
        self.view_w = np.ones(self.V)
        self.rejected = [np.zeros(N, bool) for _ in views]
        self.frozen: dict[int, np.ndarray] = {}
        # phi of a focal group all of whose views are frozen (no live coupling left)
        self.frozen_phi: dict[int, float] = {}
        self.active = [np.flatnonzero(m) for m in vis]
        self.update_active()

    # ------------------------------------------------------------------ state
    def X(self, p: np.ndarray) -> np.ndarray:
        q = p[self.lay.pts_off:self.lay.pts_end]
        if self.identity:
            return q.reshape(self.N, 3)
        return np.asarray(self.shape.points(q), float).reshape(self.N, 3)

    def cam(self, p: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray, float, float]:
        """(R, tau, rho, s) of view k; rho in 1/mm (the stored parameter is in 1/m)."""
        lay = self.lay
        o = lay.view_off[k]
        R = rodrigues(p[o:o + 3])
        tau = p[o + 3:o + 5]
        rho = float(p[o + 5]) * RHO_MM_PER_PARAM
        kd = lay.kind[k]
        if kd == FREE:
            s = _exp(p[o + 6])
        elif kd == HARD:
            s = _exp(p[lay.phi_idx[k]]) * rho
        else:
            s = self.f_fixed[k] * rho
        return R, tau, rho, s

    def camera(self, p: np.ndarray, k: int) -> Camera:
        R, tau, rho, s = self.cam(p, k)
        return invdepth_to_camera(R, tau, s, rho, like=self.views[k].camera)

    def centre(self, p: np.ndarray, k: int) -> np.ndarray:
        R, tau, rho, _ = self.cam(p, k)
        return -R.T @ np.array([tau[0], tau[1], 1.0 / rho])

    def angles(self, p: np.ndarray, k: int) -> tuple[float, float]:
        C = self.centre(p, k)
        return math.degrees(math.atan2(C[0], C[2])), math.degrees(math.atan2(C[1], math.hypot(C[0], C[2])))

    def considered(self, k: int) -> np.ndarray:
        """(N,) bool: visible with a positive visibility weight."""
        return self.vis[k] & (self.vis_w[k] > 0)

    def update_active(self) -> None:
        for k in range(self.V):
            if k in self.frozen:
                self.active[k] = np.zeros(0, np.int64)
                continue
            w = self.base_w[k] * self.irls[k] * self.vis_w[k]
            m = self.vis[k] & ~self.rejected[k] & (w > 0)
            self.active[k] = np.flatnonzero(m)

    def refresh_noise(self, p: np.ndarray) -> None:
        """Freeze each view's base noise at the current estimate (before an LM run)."""
        X = self.X(p)
        for k, v in enumerate(self.views):
            R, tau, rho, s = self.cam(p, k)
            t = np.array([tau[0], tau[1], 1.0 / rho])
            nz = _resolve_view_noise(v, X, R, t, s / rho, self.vis[k])
            self.noise[k] = nz
            m = self.vis[k]
            if nz.iso:
                self.iso[k] = True
                sig = np.full(self.N, np.nan)
                sig[m] = nz.sigma
                self.sig[k] = sig
            else:
                self.iso[k] = False
                W = np.full((self.N, 2, 2), np.nan)
                W[m] = nz.W
                self.W[k] = W

    def refresh_visibility(self, p: np.ndarray) -> None:
        """Visibility weights (DESIGN 4.8): the normal ramp (only with ``landmark_normals``) and,
        independently of the normals, the far-side contour rule (needs only the kinds and the yaw)."""
        has_contour = any(c is not None and c.any() for c in self.contour)
        if self.normals is None and not has_contour:
            return
        X = self.X(p)
        c0 = math.cos(math.radians(float(BUNDLE["vis_cos_zero_deg"].value)))
        c1 = math.cos(math.radians(float(BUNDLE["vis_cos_one_deg"].value)))
        far = float(BUNDLE["contour_far_yaw_deg"].value)
        for k in range(self.V):
            C = self.centre(p, k)
            if self.normals is not None:
                d = C - X
                dn = np.linalg.norm(d, axis=1)
                cos = np.einsum("ij,ij->i", self.normals, d) / np.maximum(dn, 1e-12)
                w = np.clip((cos - c0) / (c1 - c0), 0.0, 1.0)
                w[self.normal_unknown] = 1.0
            else:
                w = np.ones(self.N)
            yaw = math.degrees(math.atan2(C[0], C[2]))
            if self.contour[k] is not None and abs(yaw) > far:
                w[self.contour[k] & (X[:, 0] * yaw < 0)] = 0.0
            self.vis_w[k] = w

    # ------------------------------------------------------------------ reprojection
    def _whiten_factor(self, k: int, idx: np.ndarray, raw: bool, view_weight: bool):
        if raw:
            sw = np.ones(len(idx))
        else:
            w = self.base_w[k][idx] * self.irls[k][idx] * self.vis_w[k][idx]
            if view_weight:
                w = w * self.view_w[k]
            sw = np.sqrt(w) / self.nu[k]
        if self.iso[k]:
            return sw / self.sig[k][idx]
        return self.W[k][idx] * sw[:, None, None]

    @staticmethod
    def _apply(A: np.ndarray, M: np.ndarray) -> np.ndarray:
        """Whiten M (n, 2, ...) with A ((n,) scalars or (n, 2, 2))."""
        if A.ndim == 1:
            return M * A.reshape((-1,) + (1,) * (M.ndim - 1))
        if M.ndim == 2:
            return np.einsum("nij,nj->ni", A, M)
        return np.einsum("nij,njk->nik", A, M)

    def view_data(self, p: np.ndarray, k: int, X: np.ndarray, jac: bool, idx: np.ndarray | None = None,
                  raw: bool = False, view_weight: bool = True):
        """Whitened reprojection residuals (n, 2) of view k at points ``idx`` (default: active),
        and with ``jac`` the whitened Jacobian pieces."""
        lay = self.lay
        if idx is None:
            idx = self.active[k]
        R, tau, rho, s = self.cam(p, k)
        Xi = X[idx]
        ji = lay.jaw_idx[k]
        if ji >= 0:
            Rx, dRx = _rot_x(float(p[ji]))
            wj = self.jaw_w[idx]
            D = Xi - self.jaw_c
            Xi = Xi + wj[:, None] * (D @ Rx.T - D)
        Y = Xi @ R.T
        den = 1.0 + rho * Y[:, 2]
        qv = Y[:, :2] + tau
        g = s / den
        d = qv * g[:, None]                                  # u - c
        r = d + self.cxy[k] - self.uv[k][idx]
        A = self._whiten_factor(k, idx, raw, view_weight)
        rw = self._apply(A, r)
        if not jac:
            return rw
        n = len(idx)
        Jp = np.zeros((n, 2, 3))
        Jp[:, 0, 0] = g
        Jp[:, 1, 1] = g
        Jp[:, 0, 2] = -g * rho * qv[:, 0] / den
        Jp[:, 1, 2] = -g * rho * qv[:, 1] / den
        Jom = -np.einsum("nij,njk->nik", Jp, _skews(Y))      # left increment: dY = -[Y]x domega
        Jtau = Jp[:, :, :2]
        if lay.kind[k] == FREE:
            Jrho = -d * (Y[:, 2] / den * RHO_MM_PER_PARAM)[:, None]      # -s q Y_z / den^2
        else:
            Jrho = d * (RHO_MM_PER_PARAM / (rho * den))[:, None]         # s = K rho: K q / den^2
        JX = np.einsum("nij,jk->nik", Jp, R)
        Jth = None
        if ji >= 0:
            Jth = np.einsum("nij,nj->ni", JX, wj[:, None] * (D @ dRx.T))
            JX = (1.0 - wj)[:, None, None] * JX + wj[:, None, None] * np.einsum("nij,jk->nik", JX, Rx)
        out = dict(om=self._apply(A, Jom), tau=self._apply(A, Jtau), rho=self._apply(A, Jrho),
                   log=self._apply(A, d), X=self._apply(A, JX))
        if Jth is not None:
            out["th"] = self._apply(A, Jth)
        return rw, out

    def base_e(self, p: np.ndarray, k: int, idx: np.ndarray) -> np.ndarray:
        """Whitened radial residuals with the base noise (no weights, no nu), (len(idx),)."""
        if len(idx) == 0:
            return np.zeros(0)
        rw = self.view_data(p, k, self.X(p), False, idx=idx, raw=True)
        return np.linalg.norm(rw, axis=1)

    def view_trace(self, p: np.ndarray, k: int, X: np.ndarray, view_weight: bool) -> float:
        """Shape-block information trace of view k (with the current weights)."""
        idx = self.active[k]
        if len(idx) == 0:
            return 0.0
        _, J = self.view_data(p, k, X, True, view_weight=view_weight)
        JX = J["X"]
        if self.identity:
            return float(np.sum(JX * JX))
        Jd = np.zeros((2 * len(idx), 3 * self.N))
        rr = np.arange(2 * len(idx)).reshape(-1, 2)
        cols = 3 * idx[:, None] + np.arange(3)
        Jd[rr[:, :, None], cols[:, None, :]] = JX
        Jq = Jd @ np.asarray(self.shape.jacobian(p[self.lay.pts_off:self.lay.pts_end]), float)
        return float(np.sum(Jq * Jq))

    def refresh_view_weights(self, p: np.ndarray) -> None:
        """w_v = 1 / n_bin, then cap every view's shape-information share (DESIGN 4.4, D-07)."""
        if not self.view_weighting:
            self.view_w = np.ones(self.V)
            return
        live = [k for k in range(self.V) if k not in self.frozen and len(self.active[k])]
        by = float(BUNDLE["view_bin_yaw_deg"].value)
        pb = float(BUNDLE["view_pitch_band_deg"].value)
        keys = {}
        for k in live:
            yaw, pitch = self.angles(p, k)
            band = 0 if pitch < -pb else (2 if pitch > pb else 1)
            keys[k] = (int(math.floor((yaw + 0.5 * by) / by)), band)
        w = np.ones(self.V)
        for k in live:
            w[k] = 1.0 / sum(1 for j in live if keys[j] == keys[k])
        X = self.X(p)
        T = np.zeros(self.V)
        for k in live:
            T[k] = self.view_trace(p, k, X, view_weight=False)
        cap = float(BUNDLE["view_share_cap"].value)
        capped: set[int] = set()
        for _ in range(int(BUNDLE["view_cap_passes"].value)):
            wt = w * T
            tot = float(wt[live].sum()) if live else 0.0
            if tot <= 0:
                break
            # water-filling: a view capped in an earlier pass stays capped (rescaling the
            # others raises its share again), new views above the cap join it
            new = {k for k in live if k not in capped and wt[k] > cap * tot * (1.0 + 1e-12)}
            if not new:
                break
            over = capped | new
            rest = float(sum(wt[k] for k in live if k not in over))
            if rest <= 0 or len(over) * cap >= 1.0:
                break
            capped = over
            S = rest / (1.0 - len(over) * cap)
            for k in over:
                w[k] = cap * S / T[k]
        self.view_w = w

    def shares(self, p: np.ndarray) -> np.ndarray:
        X = self.X(p)
        T = np.array([self.view_trace(p, k, X, view_weight=True) if k not in self.frozen else 0.0
                      for k in range(self.V)])
        tot = T.sum()
        return T / tot if tot > 0 else np.zeros(self.V)

    # ------------------------------------------------------------------ terms
    def state(self, p: np.ndarray) -> SolverState:
        inv = []
        for k in range(self.V):
            R, tau, rho, s = self.cam(p, k)
            inv.append({"R": R, "tau": tau.copy(), "rho": rho, "s": s, "a": _log(s), "f": s / rho,
                        "kind": self.lay.kind[k], "block": BLOCK_NAMES[self.lay.kind[k]]})
        zi = self.lay.zeta_idx
        return SolverState(self.X(p), float(p[zi]) if zi >= 0 else None, inv,
                           [v.camera for v in self.views], self.lay.param_index())

    def _term_cols(self, key: str, width: int, t: int) -> np.ndarray:
        lay = self.lay
        if key == "X":
            return lay.pts_off + np.arange(3 * self.N)
        if key == "zeta":
            if lay.zeta_idx < 0:
                raise ValueError(f"term {lay.term_names[t]!r} returned a 'zeta' block but zeta is disabled")
            return np.array([lay.zeta_idx])
        if key == "self":
            return self.ext_term_off[t] + np.arange(lay.term_sizes[t])
        if key.startswith("cam:"):
            k = int(key[4:])
            return lay.view_off[k] + np.arange(lay.block_size[k])
        pi = lay.param_index()
        if key in pi and key not in ("points",) and not key.startswith("term:"):
            sl = pi[key]
            return np.arange(sl.start, sl.stop)
        raise ValueError(f"term {lay.term_names[t]!r}: unknown Jacobian block {key!r}")

    def term_rows(self, p: np.ndarray, jac: bool, prior: bool):
        if not self.terms:
            return [], []
        st = self.state(p)
        res, jacs = [], []
        for t, term in enumerate(self.terms):
            if bool(getattr(term, "is_prior", False)) != prior:
                continue
            o, k = self.lay.term_off[t], self.lay.term_sizes[t]
            pt = p[o:o + k]
            r = np.asarray(term.residuals(st, pt), float).reshape(-1)
            res.append(r)
            if jac:
                J = np.zeros((len(r), self.n_ext))
                for key, blk in term.jacobian(st, pt).items():
                    B = np.asarray(blk, float)
                    if B.ndim == 1:
                        B = B[:, None]
                    cols = self._term_cols(key, B.shape[1], t)
                    if B.shape != (len(r), len(cols)):
                        raise ValueError(f"term {term.name!r} block {key!r} has shape {B.shape}, "
                                         f"expected {(len(r), len(cols))}")
                    J[:, cols] += B
                jacs.append(J)
        return res, jacs

    # ------------------------------------------------------------------ priors
    def _pose_rows(self, p: np.ndarray, k: int, jac: bool):
        """Pose-tag residuals (2,) of view k and their Jacobian (2, 6) on (omega, tau, rho)."""
        yaw_t, pitch_t, s_y, s_p = (float(a) for a in self.views[k].pose_tag)
        R, tau, rho, _ = self.cam(p, k)
        t = np.array([tau[0], tau[1], 1.0 / rho])
        C = -R.T @ t
        h = math.hypot(C[0], C[2])
        r2 = float(C @ C)
        yaw = math.degrees(math.atan2(C[0], C[2]))
        pitch = math.degrees(math.atan2(C[1], h))
        res = np.array([_wrap_deg(yaw - yaw_t) / s_y, _wrap_deg(pitch - pitch_t) / s_p])
        if not jac:
            return res, None
        dC = np.zeros((3, 6))
        dC[:, 0:3] = -R.T @ skew(t)
        dC[:, 3:5] = -R.T[:, :2]
        dC[:, 5] = R.T[:, 2] / rho ** 2 * RHO_MM_PER_PARAM
        dyaw = np.array([C[2], 0.0, -C[0]]) / max(h * h, 1e-300)
        dpitch = (np.array([0.0, 1.0, 0.0]) - C[1] * C / r2) / max(h, 1e-300)
        J = np.vstack([dyaw @ dC * (_DEG / s_y), dpitch @ dC * (_DEG / s_p)])
        return res, J

    def camera_prior_rows(self, p: np.ndarray, jac: bool):
        lay = self.lay
        res: list[np.ndarray] = []
        jacs: list[np.ndarray] = []

        def row(cols_vals: list[tuple[int, float]]) -> np.ndarray:
            J = np.zeros((1, self.n_ext))
            for c, v in cols_vals:
                J[0, c] += v
            return J

        for idx, k, lfp, sig in lay.focal_prior:
            if k is None:
                res.append(np.array([(p[idx] - lfp) / sig]))
                if jac:
                    jacs.append(row([(idx, 1.0 / sig)]))
            else:
                ri = lay.rho_idx[k]
                res.append(np.array([(p[idx] - _log(p[ri] * RHO_MM_PER_PARAM) - lfp) / sig]))
                if jac:
                    jacs.append(row([(idx, 1.0 / sig), (ri, -1.0 / (p[ri] * sig))]))
        for k in range(self.V):
            ts = lay.tie_sigma[k]
            # A frozen (rejected or empty) view keeps no row that couples its frozen block to
            # shared parameters: its tie would pull phi_G toward the focal of a block fitted
            # to the very observations the robust schedule rejected.
            if ts is None or k in self.frozen:
                continue
            ai, ri, gi = lay.a_idx[k], lay.rho_idx[k], lay.phi_idx[k]
            res.append(np.array([(p[ai] - _log(p[ri] * RHO_MM_PER_PARAM) - p[gi]) / ts]))
            if jac:
                jacs.append(row([(ai, 1.0 / ts), (ri, -1.0 / (p[ri] * ts)), (gi, -1.0 / ts)]))
        for k, v in enumerate(self.views):
            if v.distance_prior is None:
                continue
            med, sl = (float(a) for a in v.distance_prior)
            ri = lay.rho_idx[k]
            res.append(np.array([(-_log(p[ri] * RHO_MM_PER_PARAM) - math.log(med)) / sl]))
            if jac:
                jacs.append(row([(ri, -1.0 / (p[ri] * sl))]))
        for k, v in enumerate(self.views):
            if v.pose_tag is None:
                continue
            r, J6 = self._pose_rows(p, k, jac)
            res.append(r)
            if jac:
                J = np.zeros((2, self.n_ext))
                o = lay.view_off[k]
                J[:, o:o + 6] = J6
                jacs.append(J)
        for k, ji in enumerate(lay.jaw_idx):
            if ji < 0:
                continue
            jc = self.views[k].jaw
            mu, sg = math.radians(jc.prior_mean_deg), math.radians(jc.prior_sigma_deg)
            res.append(np.array([(p[ji] - mu) / sg]))
            if jac:
                jacs.append(row([(ji, 1.0 / sg)]))
        for k in sorted(self.frozen):
            p0 = self.frozen[k]
            o, size = lay.view_off[k], lay.block_size[k]
            cols = list(range(o, o + size))
            if lay.jaw_idx[k] >= 0:
                cols.append(lay.jaw_idx[k])
            unit = np.ones(len(cols))
            unit[3:5] = 1e3                                   # tau in mm
            unit[5] = max(abs(p0[5]), 1e-12)                  # rho relative
            sig = unit * float(BUNDLE["freeze_sigma_rel"].value)
            R0 = rodrigues(p0[0:3])
            r = np.empty(len(cols))
            r[0:3] = rotation_to_rvec(rodrigues(p[o:o + 3]) @ R0.T)
            r[3:] = p[cols[3:]] - p0[3:]
            res.append(r / sig)
            if jac:
                J = np.zeros((len(cols), self.n_ext))
                J[np.arange(len(cols)), cols] = 1.0 / sig
                jacs.append(J)
        if self.frozen_phi:
            sig = float(BUNDLE["freeze_sigma_rel"].value)          # phi is a log: absolute units
            gi = sorted(self.frozen_phi)
            res.append(np.array([(p[i] - self.frozen_phi[i]) / sig for i in gi]))
            if jac:
                J = np.zeros((len(gi), self.n_ext))
                J[np.arange(len(gi)), gi] = 1.0 / sig
                jacs.append(J)
        return res, jacs

    def shape_prior_rows(self, p: np.ndarray, jac: bool):
        lay, N = self.lay, self.N
        zi = lay.zeta_idx
        X = self.X(p)
        res: list[np.ndarray] = []
        jacs: list[np.ndarray] = []
        po = lay.pts_off
        if zi >= 0:
            res.append(np.array([p[zi] / self.sc.sigma_log]))
            if jac:
                J = np.zeros((1, self.n_ext))
                J[0, zi] = 1.0 / self.sc.sigma_log
                jacs.append(J)
        s = _exp(-p[zi]) if zi >= 0 else 1.0
        Xt = s * X if zi >= 0 else X
        if self.shape_term is not None:
            res.append(self.shape_term.residual(Xt))
            if jac:
                Js = self.shape_term.jacobian(Xt)
                J = np.zeros((Js.shape[0], self.n_ext))
                J[:, po:po + 3 * N] = Js * s if zi >= 0 else Js
                if zi >= 0:
                    J[:, zi] = -(Js @ Xt.ravel())               # d X~ / d zeta = -X~
                jacs.append(J)
        pairs = self.pairs
        if len(pairs):
            res.append(((X[pairs[:, 0]] - X[pairs[:, 1]] * MIRROR) / self.S_sym).ravel())
            if jac:
                J = np.zeros((3 * len(pairs), self.n_ext))
                a = np.arange(len(pairs))
                for c in range(3):
                    J[3 * a + c, po + 3 * pairs[:, 0] + c] += 1.0 / self.S_sym[:, c]
                    J[3 * a + c, po + 3 * pairs[:, 1] + c] -= MIRROR[c] / self.S_sym[:, c]
                jacs.append(J)
        mid = self.mid
        if len(mid):
            res.append(X[mid, 0] / self.S_mid)
            if jac:
                J = np.zeros((len(mid), self.n_ext))
                J[np.arange(len(mid)), po + 3 * mid] = 1.0 / self.S_mid
                jacs.append(J)
        if self.gauge is not None:
            G, mu = self.gauge
            res.append(G @ (Xt.ravel() - mu) / self.gauge_sigma)
            if jac:
                J = np.zeros((6, self.n_ext))
                J[:, po:po + 3 * N] = G * (s / self.gauge_sigma)
                if zi >= 0:
                    J[:, zi] = -(G @ Xt.ravel()) / self.gauge_sigma
                jacs.append(J)
        return res, jacs

    # ------------------------------------------------------------------ assembly
    def data_residuals(self, p: np.ndarray, view_weight: bool = True) -> list[np.ndarray]:
        """Whitened data rows; ``view_weight=False`` leaves out the view weights w_v (which
        de-duplicate correlated views and are not part of the noise model) for chi^2."""
        X = self.X(p)
        out = [self.view_data(p, k, X, False, view_weight=view_weight).ravel() for k in range(self.V)]
        tr, _ = self.term_rows(p, False, prior=False)
        return out + tr

    def prior_residuals(self, p: np.ndarray) -> list[np.ndarray]:
        a, _ = self.camera_prior_rows(p, False)
        b, _ = self.shape_prior_rows(p, False)
        c, _ = self.term_rows(p, False, prior=True)
        return a + b + c

    def residuals(self, p: np.ndarray) -> np.ndarray:
        blocks = self.data_residuals(p) + self.prior_residuals(p)
        return np.concatenate(blocks) if blocks else np.zeros(0)

    def _to_real(self, J: np.ndarray, p: np.ndarray) -> np.ndarray:
        if self.identity:
            return J
        lay = self.lay
        S = np.asarray(self.shape.jacobian(p[lay.pts_off:lay.pts_end]), float)
        po, N3 = lay.pts_off, 3 * self.N
        return np.hstack([J[:, :po], J[:, po:po + N3] @ S, J[:, po + N3:]])

    def data_jacobian_ext(self, p: np.ndarray) -> np.ndarray:
        lay = self.lay
        X = self.X(p)
        m = sum(2 * len(a) for a in self.active)
        J = np.zeros((m, self.n_ext))
        row = 0
        for k in range(self.V):
            idx = self.active[k]
            n = len(idx)
            if n == 0:
                continue
            _, P = self.view_data(p, k, X, True)
            sl = slice(row, row + 2 * n)
            o = lay.view_off[k]
            J[sl, o:o + 3] = P["om"].reshape(-1, 3)
            J[sl, o + 3:o + 5] = P["tau"].reshape(-1, 2)
            J[sl, o + 5] = P["rho"].reshape(-1)
            if lay.kind[k] == FREE:
                J[sl, o + 6] = P["log"].reshape(-1)
            elif lay.kind[k] == HARD:
                J[sl, lay.phi_idx[k]] = P["log"].reshape(-1)
            if lay.jaw_idx[k] >= 0:
                J[sl, lay.jaw_idx[k]] = P["th"].reshape(-1)
            rr = row + np.arange(2 * n).reshape(n, 2)
            cols = lay.pts_off + 3 * idx[:, None] + np.arange(3)
            J[rr[:, :, None], cols[:, None, :]] = P["X"]
            row += 2 * n
        _, tj = self.term_rows(p, True, prior=False)
        return np.vstack([J] + tj) if tj else J

    def prior_jacobian_ext(self, p: np.ndarray) -> np.ndarray:
        _, a = self.camera_prior_rows(p, True)
        _, b = self.shape_prior_rows(p, True)
        _, c = self.term_rows(p, True, prior=True)
        blocks = a + b + c
        return np.vstack(blocks) if blocks else np.zeros((0, self.n_ext))

    def jacobian(self, p: np.ndarray) -> np.ndarray:
        J = np.vstack([self.data_jacobian_ext(p), self.prior_jacobian_ext(p)])
        return self._to_real(J, p)

    def retract(self, p: np.ndarray, dp: np.ndarray) -> np.ndarray:
        q = p + dp
        for o in self.lay.view_off:
            q[o:o + 3] = rotation_to_rvec(rodrigues(dp[o:o + 3]) @ rodrigues(p[o:o + 3]))
        return q

    def project(self, p: np.ndarray) -> np.ndarray:
        """Box projection of rho (and jaw theta) on every LM trial point (DESIGN D-02, 4.9)."""
        q = np.asarray(p, float).copy()
        lo, hi = self.rho_box[0] / RHO_MM_PER_PARAM, self.rho_box[1] / RHO_MM_PER_PARAM
        for ri in self.lay.rho_idx:
            q[ri] = min(max(q[ri], lo), hi)
        for k, ji in enumerate(self.lay.jaw_idx):
            if ji >= 0:
                blo, bhi = np.radians(self.views[k].jaw.bounds_deg)
                q[ji] = min(max(q[ji], blo), bhi)
        return q

    def freeze_empty(self, p: np.ndarray) -> list[int]:
        """Freeze views left without an active observation; returns the newly frozen views."""
        new = []
        for k in range(self.V):
            if k not in self.frozen and len(self.active[k]) == 0:
                self.freeze_view(p, k)
                new.append(k)
        if new:
            self.update_active()
        return new

    def freeze_view(self, p: np.ndarray, k: int) -> None:
        """Hold view k's camera block (and jaw angle) at its current value (rejected or empty view).

        Its tie row is dropped (:meth:`camera_prior_rows`); a focal group left without any
        live view gets its phi frozen too, as nothing but its prior would determine it.
        """
        if k not in self.frozen:
            self.frozen[k] = p[self._freeze_cols(k)].copy()
        for idx, ks in self.lay.group_views.items():
            if idx not in self.frozen_phi and all(j in self.frozen for j in ks):
                self.frozen_phi[idx] = float(p[idx])

    def frozen_cols(self) -> np.ndarray:
        """Sorted parameter indices held fixed: frozen views' blocks (+ jaw) and orphaned phi."""
        cols = [c for k in self.frozen for c in self._freeze_cols(k)] + list(self.frozen_phi)
        return np.unique(np.asarray(cols, np.int64))

    def _freeze_cols(self, k: int) -> list[int]:
        o, size = self.lay.view_off[k], self.lay.block_size[k]
        cols = list(range(o, o + size))
        if self.lay.jaw_idx[k] >= 0:
            cols.append(self.lay.jaw_idx[k])
        return cols


# =========================================================================== solver
def _validate_view_extras(views: list[ViewObs]) -> None:
    for k, v in enumerate(views):
        if v.estimate_focal and v.focal_group is not None and v.focal_tie_sigma is not None:
            if not (np.isfinite(v.focal_tie_sigma) and v.focal_tie_sigma > 0):
                raise ValueError(f"ViewObs.focal_tie_sigma of view {k} must be > 0 or None")
        if v.distance_prior is not None:
            med, sl = (float(a) for a in v.distance_prior)
            if not (med > 0 and sl > 0 and np.isfinite(med) and np.isfinite(sl)):
                raise ValueError(f"ViewObs.distance_prior of view {k} must be (median_mm > 0, sigma_log > 0)")
        if v.pose_tag is not None:
            t = np.asarray(v.pose_tag, float).reshape(-1)
            if t.shape != (4,) or not np.all(np.isfinite(t)) or not (t[2] > 0 and t[3] > 0):
                raise ValueError(f"ViewObs.pose_tag of view {k} must be (yaw, pitch, sigma_yaw > 0, "
                                 f"sigma_pitch > 0) in degrees")
        if v.jaw is not None and v.jaw.enabled:
            lo, hi = (float(a) for a in v.jaw.bounds_deg)
            if not (lo <= hi and v.jaw.prior_sigma_deg > 0):
                raise ValueError(f"ViewObs.jaw of view {k}: need bounds lo <= hi and prior_sigma_deg > 0")


def _view_weight_dof_correction(prob: _Problem, Jd: np.ndarray, H_data: np.ndarray, Sig: np.ndarray) -> float:
    """Degrees-of-freedom correction of chi^2 for view weights (0 when every w_v is 1).

    chi^2 is taken over the residuals WITHOUT the view weights w_v, while the fit (and
    H_data, Sigma) uses them: a weighted fit does not minimise the unweighted chi^2
    (Gauss-Markov), so its expectation exceeds m - tr(H_data Sigma).  To first order (weak
    priors) E chi^2 = m - 2 tr(A) + tr(A A^T) with the oblique hat matrix
    A = J Sigma J^T W, i.e. tr(A A^T) = tr(Sigma H_w2 Sigma H_u); the correction
    tr(Sigma H_w2 Sigma H_u) - tr(Sigma H_w Sigma H_w), with H_u = sum_v H_v,
    H_w = sum_v w_v H_v = H_data and H_w2 = sum_v w_v^2 H_v (H_v the unweighted
    information of view v), adds that excess and vanishes identically for w = 1, where
    m - p_eff is the exact expectation under the linear-Gaussian prior model.
    ``Jd``: the (real-parameter) data Jacobian with the view weights, rows in view order.
    """
    vw = prob.view_w
    if np.all(vw == 1.0):
        return 0.0
    Hu = H_data.copy()
    Hw2 = H_data.copy()
    row = 0
    for k in range(prob.V):
        nr = 2 * len(prob.active[k])
        if nr and vw[k] > 0 and vw[k] != 1.0:
            Jk = Jd[row:row + nr]
            Hk = Jk.T @ Jk                        # w_v H_v
            Hu += Hk * (1.0 / vw[k] - 1.0)
            Hw2 += Hk * (vw[k] - 1.0)
        row += nr
    SH = Sig @ H_data
    return float(np.sum((Sig @ Hw2 @ Sig) * Hu) - np.sum(SH * SH.T))


def bundle_adjust(views: list[ViewObs], X0: np.ndarray, priors: Priors | None = None,
                  huber_px: float | None = 3.0, irls_rounds: int = 3, max_iter: int = 100, *,
                  prior: Any = None, scale: ScaleConfig | str | None = "auto",
                  gauge_anchor_idx: Sequence[int] | None = None,
                  sigma_def_mm: np.ndarray | None = None,
                  robust: RobustSchedule | None = None, view_weighting: bool = False,
                  landmark_normals: np.ndarray | None = None,
                  jaw_weights: np.ndarray | None = None, jaw_center_mm: Sequence[float] | None = None,
                  terms: Sequence[Any] | None = None, shape_model: Any = None,
                  schur_point_idx: np.ndarray | None = None,
                  dense_max_params: int | None = None) -> BundleResult:
    """Joint refinement of cameras, focal lengths, jaw angles, zeta, landmarks and term parameters.

    ``huber_px`` is the Huber threshold in units of each observation's whitened
    residual (i.e. in standard deviations), so it scales with face size and depth.
    It drives the legacy Huber-only IRLS (``irls_rounds`` rounds) when ``robust`` is None.

    WP-07 keyword arguments: ``prior`` (a ``LandmarkPrior``, WP-03 protocol), ``scale``
    ('auto', None or :class:`ScaleConfig`), ``gauge_anchor_idx`` (global point indices of
    the rigid gauge rows, used when ``prior.meta['rigid_invariant']``), ``sigma_def_mm``
    ((N,) or scalar definition-bias floor, mm).

    WP-10 keyword arguments (DESIGN 4.3-4.9; see the module docstring):

    * ``robust``: a :class:`~face3d.solve.robust.RobustSchedule` (Huber -> Tukey ->
      reject -> plain re-solve with nu_v and the view chi^2 test); None keeps the legacy
      Huber IRLS.  ``chi2_red`` is then computed over the inliers of the final solve.
    * ``view_weighting``: 1 / n_bin view weights with the 40 % information cap.
    * ``landmark_normals``: (N, 3) template normals in the head frame; enables the
      visibility weights.  The far-side contour rule needs only ``ViewObs.kinds`` and runs
      with or without normals.
    * ``jaw_weights`` (N,) and ``jaw_center_mm`` (3,) for views whose ``ViewObs.jaw`` is
      enabled (hinge axis +x).
    * ``terms``: extra :class:`~face3d.solve.terms.Term` blocks.
    * ``shape_model``: a :class:`~face3d.solve.terms.ShapeModel` (default ``FreePoints(N)``);
      ``X0`` initialises it through ``shape_model.init``.
    * ``schur_point_idx``: (N,) bool, points whose Hessian blocks are 3x3 block-diagonal,
      eliminated by Schur complement in the LM step when the parameter count exceeds
      ``dense_max_params`` (default 2500).

    Invalid input raises ``ValueError``; the flag ``COV-SINGULAR`` is reserved for
    numerical failure of the covariance.
    """
    X0 = np.asarray(X0, float)
    N = len(X0)
    views = list(views)
    pri = priors or Priors()
    sc = _resolve_scale(scale, prior)
    _validate_view_extras(views)
    shape = FreePoints(N) if shape_model is None else shape_model
    identity = bool(getattr(shape, "is_identity", False))
    q0 = np.asarray(shape.init(X0), float).reshape(-1)
    n_shape = shape_n_params(shape)
    if q0.shape != (n_shape,):
        raise ValueError(f"shape_model.init returned {q0.shape}, expected ({n_shape},)")
    terms = list(terms or [])
    names = [str(t.name) for t in terms]
    if len(set(names)) != len(names):
        raise ValueError("term names must be unique")
    lay = _Layout(views, N, zeta=sc.enabled, n_shape=n_shape,
                  term_sizes=[(nm, int(t.n_params())) for nm, t in zip(names, terms)])
    zi = lay.zeta_idx
    vis = [~np.isnan(np.asarray(v.uv, float)[:, 0]) for v in views]
    base_w = [np.ones(N) if v.weights is None else np.asarray(v.weights, float).reshape(-1) for v in views]
    for k, w in enumerate(base_w):
        if w.shape != (N,):
            raise ValueError(f"ViewObs.weights of view {k} must have shape ({N},), got {w.shape}")
        wv = w[vis[k]]
        if not (np.all(np.isfinite(wv)) and np.all(wv >= 0)):
            raise ValueError(f"ViewObs.weights of view {k} must be finite and >= 0 for visible landmarks")
        base_w[k] = np.where(vis[k], w, 0.0)
    # Input checks before the solve, so invalid input raises instead of being reported
    # as a numerical COV-SINGULAR flag after it.
    sdef = _resolve_sigma_def(sigma_def_mm, views, N)
    if robust is not None:
        if not isinstance(robust, RobustSchedule):
            raise TypeError("robust must be a RobustSchedule or None")
        robust.validate()
    normals = None
    normal_unknown = np.zeros(N, bool)
    if landmark_normals is not None:
        nm = np.asarray(landmark_normals, float)
        if nm.shape != (N, 3) or not np.all(np.isfinite(nm)):
            raise ValueError(f"landmark_normals must be finite with shape ({N}, 3)")
        nn = np.linalg.norm(nm, axis=1)
        normal_unknown = nn < 1e-12
        normals = nm / np.where(normal_unknown, 1.0, nn)[:, None]
    jaw_w = None
    jaw_c = np.array([float(BUNDLE[f"jaw_center_{a}_mm"].value) for a in "xyz"])
    if jaw_center_mm is not None:
        jaw_c = np.asarray(jaw_center_mm, float).reshape(3)
    if any(j >= 0 for j in lay.jaw_idx):
        if jaw_weights is None:
            raise ValueError("a view enables the jaw hinge but jaw_weights is None")
        jaw_w = np.asarray(jaw_weights, float).reshape(-1)
        if jaw_w.shape != (N,) or not np.all(np.isfinite(jaw_w)) or np.any(jaw_w < 0):
            raise ValueError(f"jaw_weights must be finite, >= 0, with shape ({N},)")

    # ---- shape prior
    shape_term: Any = None
    if prior is not None:
        shape_term = _PriorShape(prior, N)
    elif pri.mean is not None:
        sig = np.broadcast_to(np.asarray(pri.sigma, float).reshape(-1, 1) if np.ndim(pri.sigma) == 1
                              else np.asarray(pri.sigma, float), (N, 3)).copy()
        shape_term = _LegacyShape(pri.mean, sig)
    gauge = _gauge_rows(prior, N, gauge_anchor_idx, X0) if prior is not None else None

    pairs = np.asarray(pri.pairs, np.int64).reshape(-1, 2)
    mid = np.asarray(pri.midline, np.int64)
    S_sym = np.broadcast_to(np.asarray(pri.sigma_sym, float).reshape(-1, 1) if np.ndim(pri.sigma_sym) == 1
                            else np.asarray(pri.sigma_sym, float), (len(pairs), 3)).copy()
    S_mid = np.broadcast_to(np.asarray(pri.sigma_mid, float), (len(mid),)).copy()
    if np.any(~(S_sym > 0)) or np.any(~(S_mid > 0)):
        raise ValueError("sigma_sym and sigma_mid must be > 0")

    # ---- linear step (DESIGN 4.8 "Solver")
    dmax = int(BUNDLE["dense_max_params"].value) if dense_max_params is None else int(dense_max_params)
    step = dense_step
    if schur_point_idx is not None:
        sel = np.asarray(schur_point_idx, bool).reshape(-1)
        if sel.shape != (N,):
            raise ValueError(f"schur_point_idx must be a bool array of shape ({N},)")
        if not identity:
            raise ValueError("schur_point_idx needs the identity shape model (FreePoints)")
        if lay.n > dmax and sel.any():
            cols = lay.pts_off + _coord_cols(np.flatnonzero(sel))

            def step(H: np.ndarray, lam_diag: np.ndarray, g: np.ndarray, _c=cols) -> np.ndarray:
                return schur_step(H, lam_diag, g, _c)

    prob = _Problem(views, N, lay, shape, sc, shape_term, gauge, pairs, mid, S_sym, S_mid, base_w, vis,
                    terms, normals, jaw_w, jaw_c, view_weighting, step)
    prob.normal_unknown = normal_unknown

    p = _pack(views, q0, lay, sc.init if sc.enabled else 0.0, rho_box=prob.rho_box)
    if terms:
        st = prob.state(p)
        for t, term in enumerate(terms):
            o, k = lay.term_off[t], lay.term_sizes[t]
            init = np.asarray(term.init_params(st), float).reshape(-1)
            if init.shape != (k,):
                raise ValueError(f"term {term.name!r}.init_params returned {init.shape}, expected ({k},)")
            p[o:o + k] = init
    p = prob.project(p)

    flags: list[str] = []
    view_flags: list[list[str]] = [[] for _ in views]
    chi2_test: list[tuple[float, float, int] | None] = [None] * len(views)
    rej_frac = np.zeros(len(views))

    def prepare(pp: np.ndarray) -> None:
        prob.refresh_noise(pp)
        prob.refresh_visibility(pp)
        prob.update_active()

    res = None
    if robust is None:
        for _ in range(max(1, irls_rounds) if huber_px else 1):
            prepare(p)
            for k in prob.freeze_empty(p):
                view_flags[k].append(FLAG_VIEW_EMPTY)
            prob.refresh_view_weights(p)
            res = levenberg_marquardt(prob.residuals, p, jac=prob.jacobian, retract=prob.retract,
                                      max_iter=max_iter, step_solver=prob.step_solver, project=prob.project)
            p = res.x
            if huber_px:
                for k in range(len(views)):
                    m = prob.vis[k]
                    w = np.ones(N)
                    w[m] = huber_weights(prob.base_e(p, k, np.flatnonzero(m)), huber_px)
                    prob.irls[k] = w
                prob.update_active()
    else:
        rounds = ([("huber", robust.huber_delta)] * int(robust.huber_rounds)
                  + [("tukey", robust.tukey_c)] * int(robust.tukey_rounds))

        def set_nu_and_e(pp: np.ndarray) -> list[np.ndarray]:
            es = []
            for k in range(len(views)):
                idx = np.flatnonzero(prob.considered(k))
                e = prob.base_e(pp, k, idx)
                prob.nu[k] = math.sqrt(nu2_view(e * e, robust.nu_clip))
                es.append(e)
            return es

        for kind, cst in rounds:
            prepare(p)
            es = set_nu_and_e(p)
            for k in range(len(views)):
                idx = np.flatnonzero(prob.considered(k))
                w = np.zeros(N)
                en = es[k] / prob.nu[k]
                w[idx] = huber_weights(en, cst) if kind == "huber" else tukey_weights(en, cst)
                prob.irls[k] = w
            prob.update_active()
            for k in prob.freeze_empty(p):
                view_flags[k].append(FLAG_VIEW_EMPTY)
            prob.refresh_view_weights(p)
            res = levenberg_marquardt(prob.residuals, p, jac=prob.jacobian, retract=prob.retract,
                                      max_iter=max_iter, step_solver=prob.step_solver, project=prob.project)
            p = res.x
        # rejection, view test and the final plain least-squares solve on the inliers
        prepare(p)
        es = set_nu_and_e(p)
        fails = []
        for k in range(len(views)):
            idx = np.flatnonzero(prob.considered(k))
            en = es[k] / prob.nu[k]
            out = en > robust.reject_k
            rej = np.zeros(N, bool)
            rej[idx[out]] = True
            prob.rejected[k] = rej
            prob.irls[k] = np.where(prob.considered(k) & ~rej, 1.0, 0.0)
            rej_frac[k] = float(out.mean()) if len(idx) else 0.0
            n_in = int((~out).sum())
            dof = 2 * n_in - 7
            chi2, thr, bad = view_chi2_test(en[~out] ** 2, dof, robust.view_chi2_q)
            chi2_test[k] = (chi2, thr, dof)
            if bad or n_in == 0:
                fails.append(k)
            if prob.nu[k] > robust.nu_flag:
                view_flags[k].append(FLAG_VIEW_NOISY)
            if rej_frac[k] > robust.view_reject_frac_flag:
                view_flags[k].append(FLAG_VIEW_OUTLIERS)
        live = [k for k in range(len(views)) if k not in prob.frozen]
        if fails and len(set(live) - set(fails)) >= 1:
            for k in fails:
                prob.freeze_view(p, k)
                view_flags[k].append(FLAG_VIEW_REJECT)
        prob.update_active()
        for k in prob.freeze_empty(p):
            view_flags[k].append(FLAG_VIEW_EMPTY)
        prob.refresh_view_weights(p)
        res = levenberg_marquardt(prob.residuals, p, jac=prob.jacobian, retract=prob.retract,
                                  max_iter=max_iter, step_solver=prob.step_solver, project=prob.project)
        p = res.x
    for vf in view_flags:
        for f in vf:
            if f not in flags:
                flags.append(f)

    X = prob.X(p).copy()

    # ---- covariance and diagnostics at the solution (weights and noise frozen)
    out: dict[str, Any] = {}
    Sig = None
    try:
        Jd = prob._to_real(prob.data_jacobian_ext(p), p)
        Jpr = prob._to_real(prob.prior_jacobian_ext(p), p)
        H_data = Jd.T @ Jd
        H_prior = Jpr.T @ Jpr
        # frozen views (rejected / empty) are conditioned on, not inverted with their stiff rows
        post = _posterior_fixed(H_data + H_prior, lay, float(BUNDLE["cov_ridge_rel"].value), prob.frozen_cols())
        Sig, cov, cov_shape = post["Sigma"], post["cov"], post["cov_shape"]
        if not identity:
            Sj = np.asarray(shape.jacobian(p[lay.pts_off:lay.pts_end]), float)
            cov = Sj @ cov @ Sj.T
            cov_shape = Sj @ cov_shape @ Sj.T
        # chi^2 over the final inliers with the noise model only (base noise x nu^2 / user and
        # visibility weights): the view weights w_v = 1 / n_bin are left out, so chi2_red stays
        # a calibration measure (~1 for a correct noise model) with view weighting on.
        rdl = prob.data_residuals(p, view_weight=False)
        rd = np.concatenate(rdl) if rdl else np.zeros(0)
        m_data = int(rd.size)
        p_eff = float(np.sum(H_data * Sig))
        dof = m_data - p_eff + _view_weight_dof_correction(prob, Jd, H_data, Sig)
        chi2_red = float(rd @ rd) / dof if dof > 0 else float("nan")
        dvar = np.maximum(np.diag(cov_shape), 0.0).reshape(N, 3)
        infl = max(1.0, chi2_red) if np.isfinite(chi2_red) else 1.0
        cam_cov = []
        for k in range(len(views)):
            idx = list(range(lay.view_off[k], lay.view_off[k] + lay.block_size[k]))
            if lay.phi_idx[k] >= 0:
                idx.append(lay.phi_idx[k])
            cam_cov.append(Sig[np.ix_(idx, idx)].copy())
        out = dict(
            point_sigma_mm=np.sqrt(dvar), cov=cov, cov_shape=cov_shape,
            zeta=float(p[zi]) if zi >= 0 else None,
            zeta_sigma=float(np.sqrt(max(Sig[zi, zi], 0.0))) if zi >= 0 else None,
            chi2_red=chi2_red, sigma_def_mm=sdef,
            sigma_rep_mm=np.sqrt(dvar * infl + sdef[:, None] ** 2),
            camera_cov=cam_cov, H_data=H_data, H_prior=H_prior, param_index=lay.param_index(),
            obs_cov_px=[prob.noise[k].cov_full(vis[k], float(prob.nu[k]) ** 2) for k in range(len(views))],
            m_data=m_data, p_eff=p_eff, cov_ridge=post["ridge"], flags=list(post["flags"]) + flags,
            chi2_dof=float(dof),
        )
    except np.linalg.LinAlgError:
        # Numerical failure only (e.g. pinv's SVD not converging on a non-finite H);
        # input errors are validated before the solve and raise.
        out = dict(flags=[FLAG_COV_SINGULAR] + flags, param_index=lay.param_index())

    # ---- per-view statistics (DESIGN 4.5, 4.12)
    shares = prob.shares(p)
    stats = []
    inl = []
    for k, v in enumerate(views):
        R, tau, rho, s = prob.cam(p, k)
        a_i, r_i, g_i = lay.a_idx[k], lay.rho_idx[k], lay.phi_idx[k]
        s_logf = s_logz = None
        frozen_k = k in prob.frozen
        if Sig is not None:
            # a frozen view's block is held, not estimated: its own sigmas are None (not 0)
            s_logz = None if frozen_k else float(math.sqrt(max(Sig[r_i, r_i], 0.0)) / p[r_i])
            if frozen_k and lay.kind[k] != HARD:
                s_logf = None
            elif lay.kind[k] == FREE:
                gv = np.zeros(lay.n)
                gv[a_i], gv[r_i] = 1.0, -1.0 / p[r_i]
                s_logf = float(math.sqrt(max(gv @ Sig @ gv, 0.0)))
            elif lay.kind[k] == HARD:
                s_logf = float(math.sqrt(max(Sig[g_i, g_i], 0.0)))
            else:
                s_logf = 0.0
        idx = prob.active[k]
        if k in prob.frozen and robust is not None:
            idx = np.flatnonzero(prob.considered(k) & ~prob.rejected[k])
        e = prob.base_e(p, k, idx) / prob.nu[k] if len(idx) else np.zeros(0)
        dof_k = 2 * len(idx) - 7
        chi2_k, thr_k, _ = view_chi2_test(e * e, dof_k, robust.view_chi2_q if robust is not None else 0.99)
        ji = lay.jaw_idx[k]
        jaw_deg = jaw_sd = None
        if ji >= 0:
            jaw_deg = float(np.degrees(p[ji]))
            if Sig is not None and not frozen_k:
                jaw_sd = float(np.degrees(math.sqrt(max(Sig[ji, ji], 0.0))))
        yaw, pitch = prob.angles(p, k)
        m_in = np.zeros(N, bool)
        m_in[prob.active[k]] = True
        inl.append(m_in)
        stats.append(dict(nu=float(prob.nu[k]), rejected_frac=float(rej_frac[k]), chi2=chi2_k, dof=int(dof_k),
                          chi2_threshold=thr_k, flags=list(view_flags[k]), weight_share=float(shares[k]),
                          view_weight=float(prob.view_w[k]), sigma_logf=s_logf, sigma_logz=s_logz,
                          jaw_deg=jaw_deg, jaw_sigma_deg=jaw_sd, yaw_deg=yaw, pitch_deg=pitch,
                          n_inliers=int(len(prob.active[k])), kind=lay.kind[k], frozen=frozen_k))
        if chi2_test[k] is not None:
            stats[-1]["chi2_test"], stats[-1]["chi2_test_threshold"], stats[-1]["dof_test"] = chi2_test[k]

    cams, rmses, per_view = [], [], []
    for k, v in enumerate(views):
        c = prob.camera(p, k)
        cams.append(c)
        m = vis[k]
        Xk = X if lay.jaw_idx[k] < 0 else jaw_hinge(X, jaw_w, float(p[lay.jaw_idx[k]]), jaw_c)
        e = np.full(N, np.nan)
        e[m] = np.linalg.norm(c.project(Xk[m]) - v.uv[m], axis=1)
        per_view.append(e)
        rmses.append(float(np.sqrt(np.nanmean(e[m] ** 2))) if m.any() else float("nan"))
    term_params = {nm: p[o:o + s].copy() for nm, o, s in zip(lay.term_names, lay.term_off, lay.term_sizes)}
    return BundleResult(X, cams, rmses, res.cost, res.iterations, per_view, view_stats=stats, inlier_mask=inl,
                        term_params=term_params or None, **out)
