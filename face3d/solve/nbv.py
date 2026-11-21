"""Next-best photo with the candidate pose Schur-marginalised (DESIGN D-19, 4.14; WBS WP-16).

For each candidate camera (yaw x pitch on a sphere about the head origin, the user's own
focal and distance) the expected information about the landmarks X from one more photo
is predicted, with the candidate's own pose unknown and eliminated, and the candidate is
scored by the perceptually weighted drop of the per-region posterior trace.

Maths (whitened units; DESIGN 4.14)
-----------------------------------
With J_c (2n x 3N) the projection Jacobian of the visible landmarks with respect to the
points and J_p (2n x 6) the Jacobian with respect to the candidate pose
p = (omega 3 rad, tau 2 mm, l = ln rho) (focal known: s = f rho; the inverse-depth block of
DESIGN D-02 / 4.3, with the depth in log units so that its prior is scale-free), both
whitened by the noise model at that distance (DESIGN 4.4) and weighted by the visibility
ramp, and Lambda_p = diag(1/0.5^2 x3, 1/100^2 x2, 1/0.5^2) the pose prior:

    W~ = I - J_p (J_p^T J_p + Lambda_p)^-1 J_p^T                 (Schur complement of p)
    H' = H + J_c^T W~ J_c          (= H + J_c^T J_c - J_c^T J_p (J_p^T J_p + Lambda_p)^-1 J_p^T J_c)
    Sigma' = Sigma - Sigma U^T (I + U Sigma U^T)^-1 U Sigma,   U = W~^1/2 J_c   (Woodbury)
    score  = sum_r w_r (tr_r Sigma - tr_r Sigma')

Sigma is the gauge-projected posterior (``cov_shape`` projected with
:func:`face3d.eval.align.gauge_projector` at X), so H = pinv(Sigma) is never formed: the
Woodbury update of the projected Sigma is the posterior of H' on the shape subspace (the
similarity directions keep zero variance).  The known-pose score (W~ = I, accuracy
proposal's gain) is returned for comparison; since W~ <= I it is never smaller.

Conventions
-----------
Head frame in mm (+x subject's left, +y up, +z out of the face; DESIGN 3.1); OpenCV
cameras.  Candidate cameras look at ``target`` (default the head-frame origin, mid-tragion)
from ``target + d (sin yaw cos pitch, sin pitch, cos yaw cos pitch)``, exactly like
:func:`face3d.synthetic.orbit_camera`: yaw > 0 is the subject's LEFT, pitch > 0 above.
Visibility: in front of the camera, inside the image, and the ramp
w = clip((cos th - cos 80) / (cos 60 - cos 80), 0, 1) of DESIGN 4.8 (rec BA-3) with
cos th = n_i . (C - X_i) / |C - X_i|.  The normals n_i are the *template normals* of
DESIGN 4.8 by default: the vertex normals of the procedural template head
(:func:`face3d.model.procedural_head.build_procedural_head`, cached) at the kit's landmark
vertices when ``ids`` names landmarks of a kit scheme (anatomical44, legacy_synthetic),
else at the kit vertices nearest to X after a similarity ICP of X onto the template
surface (:func:`template_normals`), rotated into the frame of X.  ``normals='radial'``
selects the radial direction from ``head_centre`` (the test-bed proxy of
:mod:`face3d.testbed.rigs`) explicitly; it is never a silent fallback (it under-weights
profiles: WP-16 review, 23/30 frontal-only sets picked |yaw| >= 60 deg with it).

Measured acceptance (DESIGN 4.14 'frontal-only sets pick |yaw| >= 60 deg in >= 90 % of
seeds'; three views with |yaw| < 15 deg, template normals, tests/test_observability.py):
the rate depends on the subject distance because at close range the far side of the face
turns away from a 60 deg camera (perspective), so a 45 deg view sees more landmarks and
the two can tie within ~1-2 %.  See :data:`ACCEPTANCE_RATES`.

Numeric defaults (namespace ``nbv``): region weights lids/eyes 1.0, brows 0.9, lips 0.8,
nose 0.7, nose projection 0.7, jaw 0.5, cheeks 0.4, forehead 0.3, ears 0.15 (DESIGN 4.14,
*face-perception-likeness* 🧠); chin and chin projection 0.5 and cranium 0.1 (WBS WP-16 🆕);
candidate grid yaw -90..90 step 15 x pitch {-20, 0, 20} deg (DESIGN 4.14 🧠); pose prior
0.5 rad / 100 mm / 0.5 in ln rho (WBS WP-16; the rigid-invariance sigmas of DESIGN 4.6 🆕).

numpy + stdlib only; deterministic.
"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Any, Mapping, Sequence

import numpy as np

from ..core.config import Default, register_defaults
from ..eval.align import gauge_projector
from ..geometry.camera import Camera, look_at
from .noise import NoiseModel, whitening

__all__ = ["NBV", "REGION_WEIGHTS", "CANDIDATE_YAWS", "CANDIDATE_PITCHES", "POSE_PRIOR", "ACCEPTANCE_RATES",
           "candidate_camera", "describe_view", "template_normals", "pose_jacobians", "next_best_view"]

_BRAIN = "\U0001F9E0"
_NEW = "\U0001F195"

_W = (("eyes", 1.0, _BRAIN, "DESIGN 4.14: lids 1.0 (face-perception-likeness)"),
      ("brows", 0.9, _BRAIN, "DESIGN 4.14: brows 0.9 (face-perception-likeness)"),
      ("lips", 0.8, _BRAIN, "DESIGN 4.14: lips 0.8 (face-perception-likeness)"),
      ("nose", 0.7, _BRAIN, "DESIGN 4.14: nose 0.7 (face-perception-likeness)"),
      ("nose_projection", 0.7, _BRAIN, "DESIGN 4.14: nose projection 0.7 (face-perception-likeness)"),
      ("jaw", 0.5, _BRAIN, "DESIGN 4.14: jaw 0.5 (face-perception-likeness)"),
      ("chin", 0.5, _NEW, "WBS WP-16: chin 0.5 (as jaw)"),
      ("chin_projection", 0.5, _NEW, "WBS WP-16: chin projection 0.5 (as jaw)"),
      ("cheeks", 0.4, _BRAIN, "DESIGN 4.14: cheeks 0.4 (face-perception-likeness)"),
      ("forehead", 0.3, _BRAIN, "DESIGN 4.14: forehead 0.3 (face-perception-likeness)"),
      ("ears", 0.15, _BRAIN, "DESIGN 4.14: ears 0.15 (face-perception-likeness; proposal-artist 0.1-0.2)"),
      ("cranium", 0.1, _NEW, "WBS WP-16: cranium 0.1"))

NBV = register_defaults("nbv", {
    **{f"weight_{name}": Default(val, badge, src, "", (0.0, None)) for name, val, badge, src in _W},
    "yaw_min_deg": Default(-90.0, _BRAIN, "DESIGN 4.14: candidate yaw -90..90 deg", "deg", (-180.0, 180.0)),
    "yaw_max_deg": Default(90.0, _BRAIN, "DESIGN 4.14: candidate yaw -90..90 deg", "deg", (-180.0, 180.0)),
    "yaw_step_deg": Default(15.0, _BRAIN, "DESIGN 4.14: candidate yaw step 15 deg", "deg", (1e-6, 360.0)),
    "pitch_deg": Default(20.0, _BRAIN, "DESIGN 4.14: candidate pitch {-20, 0, +20} deg", "deg", (0.0, 90.0)),
    "pose_prior_rot_rad": Default(0.5, _NEW, "WBS WP-16 pose prior 0.5 rad (DESIGN 4.6 rigid sigma)", "rad",
                                  (1e-9, None)),
    "pose_prior_trans_mm": Default(100.0, _NEW, "WBS WP-16 pose prior 100 mm (DESIGN 4.6 rigid sigma)", "mm",
                                   (1e-9, None)),
    "pose_prior_log_depth": Default(0.5, _NEW, "WBS WP-16 pose prior 0.5 in ln rho (ln distance)", "ln",
                                    (1e-9, None)),
    "front_max_yaw_deg": Default(22.5, _NEW, "WP-16 wording: |yaw| < 22.5 deg is 'front'", "deg", (0.0, 90.0)),
    "profile_min_yaw_deg": Default(60.0, _BRAIN, "WP-16 wording: |yaw| >= 60 deg is 'profile' (com R5.9)", "deg",
                                   (0.0, 180.0)),
    "eye_height_max_pitch_deg": Default(10.0, _NEW, "WP-16 wording: |pitch| < 10 deg is 'eye height'", "deg",
                                        (0.0, 90.0)),
    "distance_band": Default(0.15, _NEW, "WP-16 wording: distance range d x (1 -/+ 0.15)", "", (0.0, 0.9)),
})

#: Perceptual region weights (DESIGN 4.14; registered as ``nbv.weight_<region>``).
REGION_WEIGHTS: dict[str, float] = {name: float(NBV[f"weight_{name}"].value) for name, *_ in _W}
#: Candidate grid (DESIGN 4.14): 13 yaws x 3 pitches = 39 candidates.
CANDIDATE_YAWS: tuple[float, ...] = tuple(float(y) for y in range(-90, 91, 15))
CANDIDATE_PITCHES: tuple[float, ...] = (-20.0, 0.0, 20.0)
#: Candidate pose prior (rotation rad, translation mm, ln rho).
POSE_PRIOR: tuple[float, float, float] = (float(NBV.pose_prior_rot_rad.value), float(NBV.pose_prior_trans_mm.value),
                                          float(NBV.pose_prior_log_depth.value))

_COS0 = math.cos(math.radians(80.0))   # DESIGN 4.8 / rec BA-3 visibility ramp (bundle defaults)
_COS1 = math.cos(math.radians(60.0))

#: Measured rate of |yaw| >= 60 deg picks for frontal-only sets (3 views, |yaw| < 15 deg,
#: 30 seeds, factor prior; default template normals, no ids) by subject distance in mm
#: (camera to face centre; 'band' = U(600, 1500) mm per seed, the rear-phone rig range),
#: with the DESIGN 4.4 noise model as of the FU-01 change (point kinds without a tangent
#: isotropic at max(sigma_n, sigma_t)).  DESIGN 4.14 asks >= 0.9.  Before FU-01 the rates
#: were 0.87 / 0.93 / 1.0 / 1.0 / 0.97 (band 1.0): at 0.6 m and closer, perspective turns
#: the far side of the face away from a 60 deg camera and the 45 deg view ties with the
#: profile (score margins within ~1-2 %), so close-range sets are the first to drop below
#: 0.9 when the noise model moves.  ``normals='radial'`` gives 0.83-0.87 now and gave
#: 0.07 / 0.2 / 0.3 / 0.63 / 0.8 before FU-01.  Measured by WP-16 (scratch runs of the
#: tests/test_observability.py scenes); a tracking item for the M7 calibration (WP-23).
ACCEPTANCE_RATES: dict[Any, float] = {600.0: 0.97, 700.0: 1.0, 800.0: 1.0, 1000.0: 1.0, 1500.0: 1.0,
                                      "band": 1.0}

_ICP_ITERS = 8


@lru_cache(maxsize=1)
def _template_kit() -> Any:
    from ..model.procedural_head import build_procedural_head
    return build_procedural_head()


def template_normals(X: np.ndarray, ids: Sequence[str] | None = None) -> np.ndarray:
    """Template normals at the landmarks X (N, 3), DESIGN 4.8 (unit, frame of X).

    The vertex normals of the procedural template head (deterministic, cached).  With
    ``ids`` naming landmarks of one kit scheme (``anatomical44`` or ``legacy_synthetic``)
    each landmark takes the normal of its kit landmark vertex, rotated by the similarity
    that maps the kit's landmark positions onto X (Umeyama).  Otherwise (no ids, or ids no
    scheme knows) each landmark takes the normal of the nearest kit vertex after a
    similarity ICP of X onto the template vertices (``X`` in the head frame of DESIGN 3.1,
    as every solve returns it; 8 iterations from the identity).
    """
    from ..geometry.procrustes import umeyama
    kit = _template_kit()
    X = np.asarray(X, float)
    V = np.asarray(kit.vertices, float)
    Nv = np.asarray(kit.normals, float)
    if ids is not None:
        names = [str(i) for i in ids]
        for scheme in kit.schemes:
            known = set(kit.landmark_names(scheme))
            if len(names) == len(X) and all(n in known for n in names):
                lv = kit.landmark_vertices(scheme, names)
                _, R, _ = umeyama(V[lv], X, with_scale=True)
                n = Nv[lv] @ R.T
                return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    # similarity ICP of X onto the template surface (vertices), nearest-vertex normals
    s, R, t = 1.0, np.eye(3), np.zeros(3)
    nn = np.zeros(len(X), np.int64)
    for it in range(_ICP_ITERS):
        Y = s * X @ R.T + t                                        # X in the kit frame
        d2 = ((Y[:, None, :] - V[None, :, :]) ** 2).sum(axis=2)
        nn_new = np.argmin(d2, axis=1)
        if it > 0 and np.array_equal(nn_new, nn):
            break
        nn = nn_new
        s, R, t = umeyama(X, V[nn], with_scale=True)
    n = Nv[nn] @ R                                                 # kit frame -> frame of X
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def candidate_camera(yaw_deg: float, pitch_deg: float, distance_mm: float, focal_px: float,
                     image_wh: tuple[int, int], target: Sequence[float] = (0.0, 0.0, 0.0)) -> Camera:
    """Orbit camera about ``target`` (``face3d.synthetic.orbit_camera`` geometry, focal in px)."""
    yaw, pitch = math.radians(float(yaw_deg)), math.radians(float(pitch_deg))
    tgt = np.asarray(target, float)
    eye = tgt + float(distance_mm) * np.array([math.sin(yaw) * math.cos(pitch), math.sin(pitch),
                                                math.cos(yaw) * math.cos(pitch)])
    R, t = look_at(eye, tgt)
    W, H = int(image_wh[0]), int(image_wh[1])
    return Camera.centered(float(focal_px), W, H, R=R, t=t)


def _fmt_m(x: float) -> str:
    s = f"{x:.1f}"
    return s[:-2] if s.endswith(".0") else s


def describe_view(yaw_deg: float, pitch_deg: float, distance_mm: float) -> str:
    """One plain sentence: 'Next: {left|right} {profile|three-quarter|front}, {eye height|from
    below|from above}, {a-b} m' (subject's left = positive yaw; a front view has no side)."""
    y = float(yaw_deg)
    ay = abs(y)
    if ay < float(NBV.front_max_yaw_deg.value):
        pose = "front"
    else:
        side = "left" if y > 0 else "right"
        pose = f"{side} {'profile' if ay >= float(NBV.profile_min_yaw_deg.value) else 'three-quarter'}"
    p = float(pitch_deg)
    if abs(p) < float(NBV.eye_height_max_pitch_deg.value):
        height = "eye height"
    else:
        height = "from above" if p > 0 else "from below"
    b = float(NBV.distance_band.value)
    d = float(distance_mm) / 1000.0
    return f"Next: {pose}, {height}, {_fmt_m(d * (1 - b))}-{_fmt_m(d * (1 + b))} m"


def _noise_cov(noise_model: Any, ppm: np.ndarray, face_px: float, N: int) -> np.ndarray:
    if noise_model is None:
        noise_model = NoiseModel(["generic"] * N)
    if isinstance(noise_model, (int, float)):
        s = float(noise_model)
        return np.broadcast_to(np.eye(2) * s * s, (N, 2, 2)).copy()
    if hasattr(noise_model, "view_cov"):
        return np.asarray(noise_model.view_cov(ppm, face_px), float)
    raise TypeError("noise_model must be a NoiseModel, a float sigma in px, or None")


def _skews(Y: np.ndarray) -> np.ndarray:
    S = np.zeros((len(Y), 3, 3))
    S[:, 0, 1], S[:, 0, 2] = -Y[:, 2], Y[:, 1]
    S[:, 1, 0], S[:, 1, 2] = Y[:, 2], -Y[:, 0]
    S[:, 2, 0], S[:, 2, 1] = -Y[:, 1], Y[:, 0]
    return S


def pose_jacobians(cam: Camera, X: np.ndarray, normals: np.ndarray, noise_model: Any = 1.0,
                   subset: Any = None) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Whitened, visibility-weighted Jacobians of one candidate camera (DESIGN 4.14).

    Returns ``(J_c (2n, 3N), J_p (2n, 6), idx (n,), w (n,))``: the projection Jacobian of
    the n visible landmarks ``idx`` with respect to the points and with respect to the
    pose p = (omega, tau_x, tau_y, ln rho) (left rotation increment R <- exp([omega]) R,
    translation t_x, t_y in mm, t_z = 1/rho = e^-ln rho; focal known), each 2-row block
    multiplied by sqrt(w_i) Sigma_i^-1/2 (visibility ramp weight w_i, noise model at the
    landmark's depth).  ``noise_model`` as :func:`next_best_view` (a float = isotropic
    sigma in px); ``subset`` a bool mask (N,) of the landmarks a detector would report.
    """
    X = np.asarray(X, float)
    nrm = np.asarray(normals, float)
    nrm = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
    sel = np.ones(len(X), bool) if subset is None else np.asarray(subset, bool).reshape(len(X))
    return _jacobians(cam, X, nrm, noise_model, sel, full=True)


def _jacobians(cam: Camera, X: np.ndarray, normals: np.ndarray, noise_model: Any, sel: np.ndarray,
               full: bool = False):
    """Whitened, visibility-weighted (J_c (2n, 3N), J_p (2n, 6)) of the candidate camera."""
    N = len(X)
    Y = X @ cam.R.T
    Yc = Y + cam.t
    z = Yc[:, 2]
    C = cam.center
    view = C - X
    cos = np.einsum("ij,ij->i", normals, view) / np.maximum(np.linalg.norm(view, axis=1), 1e-12)
    w = np.clip((cos - _COS0) / (_COS1 - _COS0), 0.0, 1.0)
    front = z > 1e-9
    u = np.full((N, 2), np.nan)
    u[front] = cam.f * Yc[front, :2] / z[front, None] + np.array([cam.cx, cam.cy])
    inside = front & (u[:, 0] >= 0) & (u[:, 0] <= cam.width) & (u[:, 1] >= 0) & (u[:, 1] <= cam.height)
    vis = inside & (w > 0) & sel
    idx = np.flatnonzero(vis)
    n = len(idx)
    if n == 0:
        if full:
            return np.zeros((0, 3 * N)), np.zeros((0, 6)), idx, np.zeros(0)
        return np.zeros((0, 3 * N)), np.zeros((0, 6))
    zi = z[idx]
    dudY = np.zeros((n, 2, 3))
    dudY[:, 0, 0] = cam.f / zi
    dudY[:, 1, 1] = cam.f / zi
    dudY[:, 0, 2] = -cam.f * Yc[idx, 0] / zi ** 2
    dudY[:, 1, 2] = -cam.f * Yc[idx, 1] / zi ** 2
    dudX = dudY @ cam.R                                            # (n, 2, 3)
    d_om = -dudY @ _skews(Y[idx])                                  # left increment: dY = -[R X]_x d omega
    d_tau = dudY[:, :, :2]
    d_l = -dudY[:, :, 2:3] * cam.t[2]                              # t_z = 1/rho = e^-l
    Jp = np.concatenate([d_om, d_tau, d_l], axis=2)                # (n, 2, 6)
    ppm = np.full(N, np.nan)
    ppm[idx] = cam.f / zi
    face = float(np.ptp(u[idx, 0])) if n >= 2 else None
    Wh = whitening(_noise_cov(noise_model, ppm, face, N)[idx])     # (n, 2, 2)
    sw = np.sqrt(w[idx])[:, None, None]
    Wv = Wh * sw
    Jc_blocks = np.einsum("nij,njk->nik", Wv, dudX)
    Jp_w = np.einsum("nij,njk->nik", Wv, Jp).reshape(2 * n, 6)
    Jc = np.zeros((2 * n, 3 * N))
    rows = np.arange(2 * n).reshape(n, 2)
    cols = 3 * idx[:, None] + np.arange(3)
    Jc[rows[:, :, None], cols[:, None, :]] = Jc_blocks
    if full:
        return Jc, Jp_w, idx, w[idx]
    return Jc, Jp_w


def _trace_drop(Sig: np.ndarray, U: np.ndarray) -> np.ndarray:
    """diag(Sigma) - diag(Sigma') for Sigma' = Sigma - Sigma U^T (I + U Sigma U^T)^-1 U Sigma."""
    if U.shape[0] == 0:
        return np.zeros(len(Sig))
    A = Sig @ U.T                                                  # (3N, m)
    M = np.eye(U.shape[0]) + U @ A
    B = np.linalg.solve(0.5 * (M + M.T), A.T)                      # (m, 3N)
    return np.einsum("ij,ji->i", A, B)


def next_best_view(cov_shape: np.ndarray, result: Any = None, X: np.ndarray | None = None,
                   focal_px: float | None = None, distance_mm: float | None = None,
                   image_wh: tuple[int, int] | None = None, noise_model: Any = None,
                   region_index: Mapping[str, Any] | None = None, weights: Mapping[str, float] | None = None,
                   subset: Any = None, yaws: Sequence[float] = CANDIDATE_YAWS,
                   pitches: Sequence[float] = CANDIDATE_PITCHES,
                   pose_prior: tuple[float, float, float] = POSE_PRIOR, *,
                   normals: np.ndarray | str | None = None, ids: Sequence[str] | None = None,
                   head_centre: Sequence[float] = (0.0, 0.0, 0.0),
                   target: Sequence[float] = (0.0, 0.0, 0.0), project: bool = True,
                   return_known: bool = False):
    """Rank candidate photos by the marginalised information gain (DESIGN D-19, 4.14).

    Parameters
    ----------
    cov_shape : (3N, 3N) mm^2 posterior of the points (e.g. ``BundleResult.cov_shape`` or
        the prior-weight-1 posterior); gauge-projected at X here unless ``project=False``.
    result : optional ``BundleResult`` supplying defaults: X (``result.X``), focal (median
        solved focal: the user's own lens), distance (median camera-centre distance to the
        head origin) and the image size (first camera).
    X : (N, 3) mm, the current estimate (linearisation point).
    focal_px, distance_mm, image_wh : the candidate camera (focal in px, distance from the
        camera centre to ``target`` in mm, image (width, height) px).
    noise_model : :class:`~face3d.solve.noise.NoiseModel` (sigma in mm by kind at each
        point's depth, DESIGN 4.4), a float isotropic sigma in px, or None (generic kinds).
    region_index : region -> coordinate indices (3 i + a), e.g.
        :func:`face3d.solve.observability.default_region_index`.
    weights : region -> weight (default :data:`REGION_WEIGHTS`); regions without a weight
        score 0.
    subset : optional bool mask (N,) or indices of the landmarks a detector would report
        in the new photo (default all).
    yaws, pitches : candidate grid in degrees (default 13 x 3 = 39 candidates).
    pose_prior : (rotation rad, translation mm, ln rho) sigmas of the candidate's pose prior.
    normals : (N, 3) outward normals for the visibility ramp; default (None) the template
        normals of DESIGN 4.8 (:func:`template_normals`, using ``ids`` when given);
        ``'radial'`` = the direction from ``head_centre`` (test-bed proxy, explicit only).
    ids : optional landmark ids of X (kit scheme names) for the template normals.
    return_known : also return ``{(yaw, pitch): known-pose score}``.

    Returns
    -------
    ``(ranked, sentence)`` with ``ranked`` a list of ``(yaw, pitch, score)`` sorted by
    decreasing score (score in weighted mm^2 of trace reduction; ties keep grid order) and
    ``sentence`` the plain description of the best one (:func:`describe_view`), or
    ``(ranked, sentence, known)`` with ``return_known``.
    """
    if X is None:
        if result is None:
            raise ValueError("next_best_view needs X or a result")
        X = result.X
    X = np.asarray(X, float)
    N = len(X)
    cams = list(getattr(result, "cameras", []) or []) if result is not None else []
    if focal_px is None:
        if not cams:
            raise ValueError("focal_px is required without a result")
        focal_px = float(np.median([c.f for c in cams]))
    if distance_mm is None:
        if not cams:
            raise ValueError("distance_mm is required without a result")
        distance_mm = float(np.median([np.linalg.norm(c.center - np.asarray(target, float)) for c in cams]))
    if image_wh is None:
        if not cams:
            raise ValueError("image_wh is required without a result")
        image_wh = (int(cams[0].width), int(cams[0].height))
    if region_index is None:
        raise ValueError("region_index is required (see observability.default_region_index)")
    wts = dict(REGION_WEIGHTS if weights is None else weights)
    Sig = np.asarray(cov_shape, float)
    if Sig.shape != (3 * N, 3 * N):
        raise ValueError(f"cov_shape must be ({3 * N}, {3 * N})")
    if project:
        P = gauge_projector(X)
        Sig = P @ Sig @ P
    Sig = 0.5 * (Sig + Sig.T)
    coord_w = np.zeros(3 * N)
    for r, c in region_index.items():
        coord_w[np.asarray(c, np.int64)] += float(wts.get(r, 0.0))
    if normals is None:
        nrm = template_normals(X, ids)
    elif isinstance(normals, str):
        if normals != "radial":
            raise ValueError(f"normals must be an (N, 3) array, None or 'radial', not {normals!r}")
        nrm = X - np.asarray(head_centre, float)
    else:
        nrm = np.asarray(normals, float)
        if nrm.shape != X.shape:
            raise ValueError(f"normals must have shape {X.shape}")
    nrm = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
    sel = np.ones(N, bool)
    if subset is not None:
        s = np.asarray(subset)
        sel = s.astype(bool).reshape(N) if s.dtype == bool else np.isin(np.arange(N), s.astype(np.int64))
    s_rot, s_t, s_l = (float(v) for v in pose_prior)
    Lam = np.diag([1 / s_rot ** 2] * 3 + [1 / s_t ** 2] * 2 + [1 / s_l ** 2])
    scored, known = [], {}
    for pitch in pitches:
        for yaw in yaws:
            cam = candidate_camera(yaw, pitch, distance_mm, focal_px, image_wh, target)
            Jc, Jp = _jacobians(cam, X, nrm, noise_model, sel)
            if Jc.shape[0] == 0:
                sc_m = sc_k = 0.0
            else:
                K = Jp.T @ Jp + Lam
                Wt = np.eye(Jc.shape[0]) - Jp @ np.linalg.solve(K, Jp.T)
                ev, Q = np.linalg.eigh(0.5 * (Wt + Wt.T))
                U = (Q * np.sqrt(np.clip(ev, 0.0, None))) @ Q.T @ Jc
                sc_m = float(coord_w @ _trace_drop(Sig, U))
                sc_k = float(coord_w @ _trace_drop(Sig, Jc))
            scored.append((float(yaw), float(pitch), sc_m))
            known[(float(yaw), float(pitch))] = sc_k
    order = sorted(range(len(scored)), key=lambda i: (-scored[i][2], i))
    ranked = [scored[i] for i in order]
    sentence = describe_view(ranked[0][0], ranked[0][1], distance_mm) if ranked else ""
    if return_known:
        return ranked, sentence, known
    return ranked, sentence
