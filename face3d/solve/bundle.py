"""Multi-view landmark bundle adjustment with anatomical priors.

Unknowns: per view a camera pose (rotation, translation) and optionally a focal
length; optionally a global log-scale zeta; a set of N 3D landmarks in the HEAD
FRAME (mm; +x subject's left, +y up, +z out of the face; DESIGN 3.1).

Parameter vector (:class:`_Layout`)::

    [6 pose per view | 1 log-focal per focal group | zeta (if enabled) | 3N points]

Residuals (all whitened, i.e. multiplied by the inverse square root of their
covariance):

  * reprojection   W_iv (u_iv(X) - u_obs)       (Huber-robustified by IRLS; DATA rows)
  * focal prior    (log f - log f_prior) / sigma_logf   (e.g. from EXIF)
  * scale prior    zeta / sigma_log                       (DESIGN D-03, 4.7)
  * shape prior    either the legacy ``Priors`` term (X~_i - mu_i) / sigma_i, or a
                   ``LandmarkPrior`` W (X~ - mu) / its generalised residual on X~
                   (DESIGN 4.6), with X~ = e^-zeta X (X~ = X when zeta is disabled)
  * symmetry       (X_l - Mirror(X_r)) / sigma_sym   for left/right pairs
  * midline        x_i / sigma_mid                   for midline landmarks
  * gauge          G_a (X~_A - mu_A) / 0.01 mm       six rigid rows, only when the
                   LandmarkPrior is rigid-invariant (DESIGN 4.6 "Gauge")

The analytic Jacobian uses multiplicative rotation updates R <- exp([w]x) R.

Observation noise (DESIGN 4.4, D-05; :mod:`face3d.solve.noise`)
---------------------------------------------------------------
Per view, in this order: ``ViewObs.cov_px`` (explicit (N,2,2) px^2) -> ``sigma_px``
(legacy isotropic float, px) -> :class:`~face3d.solve.noise.NoiseModel` of
``ViewObs.kinds`` (or 'generic') with px_per_mm_i = f / z_i from the CURRENT estimate.
The legacy default ``sigma_px = 1.0`` (about 13x too tight; rec C5) is gone: the
default is now ``None`` -> the noise model.  Noise is FROZEN within each LM run: it
is recomputed before each IRLS round, never inside the residual function, so the
analytic Jacobian stays exact.

Scale (DESIGN D-03, 4.7)
------------------------
With a ``LandmarkPrior`` the default ``scale='auto'`` enables an explicit global
log-scale zeta ~ N(0, 0.045^2), the single population size source.  With only the
legacy ``Priors`` it stays disabled, which preserves the legacy numerics exactly.

Covariance (DESIGN 4.8 "Covariance", 4.13)
------------------------------------------
After the final solve: J at the solution (weights and noise frozen), H = J^T J split
into H_data (reprojection rows) and H_prior (everything else).  A ridge of
1e-12 * mean(diag H) is added (legacy value).  The cameras (poses, focals and, for
``cov``, zeta) are eliminated by Schur complement:
``cov_shape = (H_XX - H_Xc H_cc^-1 H_cX)^-1`` with zeta removed (conditional on zeta),
``cov`` = the same with zeta eliminated too (unconditional), both in the template
gauge.  ``point_sigma_mm = sqrt(diag(cov_shape))`` keeps its legacy meaning.
Reported uncertainty: ``sigma_rep_mm = sqrt(diag(cov_shape) * max(1, chi2_red) +
sigma_def^2)`` with the definition-bias floor sigma_def (D-06; gamma from LOVO is
added later by WP-16).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from ..core.config import Default, register_defaults
from ..geometry.camera import Camera
from ..geometry.rotations import rodrigues, rotation_to_rvec, skew
from .lm import levenberg_marquardt
from .noise import NoiseModel, whitening

#: Engine version label (scorecards record it; WBS WP-07).
ENGINE_VERSION = "v2-fixes"

MIRROR = np.array([-1.0, 1.0, 1.0])

_BRAIN = "\U0001F9E0"   # expert knowledge, provisional
_NEW = "\U0001F195"     # introduced by this design / WP spec, uncalibrated

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
})

#: Flag raised when the Gauss-Newton Hessian is not positive definite (pinv fallback).
FLAG_COV_SINGULAR = "COV-SINGULAR"


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
    # Views sharing a focal_group share ONE focal length (same camera + zoom).
    focal_group: str | int | None = None
    kinds: list[str] | None = None            # (N,) landmark kinds (noise.KINDS); None -> 'generic'
    cov_px: np.ndarray | None = None          # (N,2,2) explicit image covariance, px^2 (highest priority)
    multipliers: np.ndarray | None = None     # (N,) occluder / makeup sigma multipliers m_iv (DESIGN 4.1)
    tangents: np.ndarray | None = None        # (N,2) image tangents (NaN / zero rows = unknown)
    tta_px: np.ndarray | None = None          # (N,) test-time-augmentation spread, px
    face_px: float | None = None              # face width in px (detector floor); None -> landmark bbox width
    dense_mask: np.ndarray | None = None      # (N,) bool dense detector points (eta = N / N_eff inflation)


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
    cov: np.ndarray | None = None            # (3N,3N) mm^2, unconditional (zeta marginalised), template gauge
    cov_shape: np.ndarray | None = None      # (3N,3N) mm^2, conditional on zeta
    zeta: float | None = None                # global log-scale (None when disabled)
    zeta_sigma: float | None = None
    chi2_red: float | None = None            # sum r_data^2 / (m_data - p_eff), p_eff = tr(H_data Sigma)
    sigma_def_mm: np.ndarray | None = None   # (N,) definition-bias floor (D-06)
    sigma_rep_mm: np.ndarray | None = None   # (N,3) sqrt(diag(cov_shape) max(1, chi2_red) + sigma_def^2)
    camera_cov: list[np.ndarray] | None = None  # per view: cov of [pose 6 | log f] (7x7, or 6x6 if f fixed)
    H_data: np.ndarray | None = None         # (n,n) J_data^T J_data at the solution
    H_prior: np.ndarray | None = None        # (n,n) J_prior^T J_prior at the solution
    param_index: dict | None = None          # name -> slice into the parameter vector
    obs_cov_px: list[np.ndarray] | None = None  # per view (N,2,2) px^2 noise used in the final round (NaN hidden)
    m_data: int | None = None                # number of reprojection residual rows
    p_eff: float | None = None               # tr(H_data Sigma)
    cov_ridge: float | None = None           # ridge added to diag(H) before inversion
    flags: list[str] = field(default_factory=list)
    engine_version: str = ENGINE_VERSION


class _Layout:
    """Parameter vector: [6 pose per view | 1 log-focal per focal group | zeta? | 3N points]."""

    def __init__(self, views: list[ViewObs], n_pts: int, zeta: bool = False):
        self.view_off = [6 * k for k in range(len(views))]
        off = 6 * len(views)
        self.focal_idx: list[int] = []
        self.group_views: dict[int, list[int]] = {}
        key_to_idx: dict = {}
        for k, v in enumerate(views):
            if not v.estimate_focal:
                self.focal_idx.append(-1)
                continue
            key = ("g", v.focal_group) if v.focal_group is not None else ("v", k)
            if key not in key_to_idx:
                key_to_idx[key] = off
                off += 1
            idx = key_to_idx[key]
            self.focal_idx.append(idx)
            self.group_views.setdefault(idx, []).append(k)
        # One focal prior per group: the tightest prior among its views.
        self.group_prior: list[tuple[int, float, float]] = []
        for idx, ks in self.group_views.items():
            cands = [(views[k].f_prior_log_sigma, views[k].f_prior) for k in ks if views[k].f_prior is not None]
            if cands:
                sig, fp = min(cands)
                self.group_prior.append((idx, float(np.log(fp)), float(sig)))
        self.focal_end = off
        self.zeta_idx = -1
        if zeta:
            self.zeta_idx = off
            off += 1
        self.pts_off = off
        self.n = off + 3 * n_pts
        self.n_pts = n_pts

    def param_index(self) -> dict:
        out: dict[str, slice] = {}
        for k, o in enumerate(self.view_off):
            out[f"pose_{k}"] = slice(o, o + 6)
        for j, idx in enumerate(sorted(self.group_views)):
            out[f"focal_{j}"] = slice(idx, idx + 1)
        out["cameras"] = slice(0, self.focal_end)
        if self.zeta_idx >= 0:
            out["zeta"] = slice(self.zeta_idx, self.zeta_idx + 1)
        out["points"] = slice(self.pts_off, self.n)
        return out


def _pack(views: list[ViewObs], X: np.ndarray, lay: _Layout, zeta0: float = 0.0) -> np.ndarray:
    p = np.zeros(lay.n)
    for v, o in zip(views, lay.view_off):
        p[o:o + 3] = rotation_to_rvec(v.camera.R)
        p[o + 3:o + 6] = v.camera.t
    for idx, ks in lay.group_views.items():
        p[idx] = float(np.mean([np.log(views[k].camera.f) for k in ks]))
    if lay.zeta_idx >= 0:
        p[lay.zeta_idx] = float(zeta0)
    p[lay.pts_off:] = X.ravel()
    return p


def _unpack_cam(p: np.ndarray, v: ViewObs, k: int, lay: _Layout) -> tuple[np.ndarray, np.ndarray, float]:
    o = lay.view_off[k]
    R = rodrigues(p[o:o + 3])
    t = p[o + 3:o + 6]
    fi = lay.focal_idx[k]
    f = float(np.exp(p[fi])) if fi >= 0 else v.camera.f
    return R, t, f


# =========================================================================== noise
class _ViewNoise:
    """Frozen noise of one view for one LM run: isotropic sigma (legacy) or whitening W."""

    __slots__ = ("iso", "sigma", "W", "C")

    def __init__(self, iso: bool, sigma: Any = None, W: np.ndarray | None = None, C: np.ndarray | None = None):
        self.iso = iso
        self.sigma = sigma      # float or (n_vis,) px (iso)
        self.W = W              # (n_vis, 2, 2) inverse lower Cholesky factors (full)
        self.C = C              # (n_vis, 2, 2) px^2 (full)

    def cov_full(self, m: np.ndarray) -> np.ndarray:
        """(N,2,2) px^2 with NaN rows where hidden."""
        N = len(m)
        out = np.full((N, 2, 2), np.nan)
        if self.iso:
            s2 = np.broadcast_to(np.asarray(self.sigma, float) ** 2, (int(m.sum()),))
            blk = np.zeros((len(s2), 2, 2))
            blk[:, 0, 0] = s2
            blk[:, 1, 1] = s2
            out[m] = blk
        else:
            out[m] = self.C
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
    model = NoiseModel(kinds, dense_mask=v.dense_mask)
    z = (X[m] @ R.T + t)[:, 2]
    ppm = np.full(N, np.nan)
    ppm[m] = f / np.maximum(np.abs(z), 1e-6)
    face = v.face_px if v.face_px is not None else _face_width_px(np.asarray(v.uv, float)[m])
    C = model.view_cov(ppm, face, tangents=v.tangents, multipliers=v.multipliers, tta_px=v.tta_px)[m]
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


# =========================================================================== covariance
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


def _schur_inverse(H: np.ndarray, c: np.ndarray, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Full inverse of SPD ``H`` by eliminating the block ``c`` (cameras) onto ``x`` (points).

    Returns ``(Sigma (n, n), Sigma_xx)`` with Sigma_xx = (H_xx - H_xc H_cc^-1 H_cx)^-1
    (the Schur complement), Sigma_cx = -H_cc^-1 H_cx Sigma_xx and
    Sigma_cc = H_cc^-1 + H_cc^-1 H_cx Sigma_xx H_xc H_cc^-1.
    """
    Hcc = H[np.ix_(c, c)]
    Hcx = H[np.ix_(c, x)]
    Hxx = H[np.ix_(x, x)]
    Hcc_inv = _inv_spd(Hcc)
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


def _posterior(H: np.ndarray, lay: _Layout, ridge_rel: float) -> dict:
    """Sigma (full), cov (points, unconditional) and cov_shape (points, conditional on zeta)."""
    n = len(H)
    ridge = ridge_rel * max(float(np.trace(H)) / n, 1e-300)
    Hr = H.copy()
    Hr[np.diag_indices_from(Hr)] += ridge
    x = np.arange(lay.pts_off, lay.n)
    c = np.arange(0, lay.pts_off)
    flags: list[str] = []
    try:
        Sig, cov = _schur_inverse(Hr, c, x)
        if lay.zeta_idx >= 0:
            keep = np.array([i for i in range(n) if i != lay.zeta_idx])
            Hk = Hr[np.ix_(keep, keep)]
            ck = np.arange(0, lay.pts_off - 1)            # zeta sits just before the points
            xk = np.arange(lay.pts_off - 1, n - 1)
            _, cov_shape = _schur_inverse(Hk, ck, xk)
        else:
            cov_shape = cov
    except np.linalg.LinAlgError:
        flags.append(FLAG_COV_SINGULAR)
        Sig = np.linalg.pinv(0.5 * (Hr + Hr.T), hermitian=True)
        cov = Sig[np.ix_(x, x)]
        if lay.zeta_idx >= 0:
            keep = np.array([i for i in range(n) if i != lay.zeta_idx])
            Sk = np.linalg.pinv(Hr[np.ix_(keep, keep)], hermitian=True)
            cov_shape = Sk[lay.pts_off - 1:, lay.pts_off - 1:]
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
            return NoiseModel(v.kinds).sigma_def_mm()
    return np.zeros(N)


# =========================================================================== solver
def bundle_adjust(views: list[ViewObs], X0: np.ndarray, priors: Priors | None = None,
                  huber_px: float | None = 3.0, irls_rounds: int = 3, max_iter: int = 100, *,
                  prior: Any = None, scale: ScaleConfig | str | None = "auto",
                  gauge_anchor_idx: Sequence[int] | None = None,
                  sigma_def_mm: np.ndarray | None = None) -> BundleResult:
    """Joint refinement of cameras, focal lengths, (optionally) zeta and landmarks.

    ``huber_px`` is the Huber threshold in units of each observation's whitened
    residual (i.e. in standard deviations), so it scales with face size and depth.

    New keyword arguments (WBS WP-07, backward compatible):

    * ``prior``: a ``LandmarkPrior`` (WP-03 protocol, including the generalised
      residual/jacobian interface for joint-index priors) used for the shape term
      instead of ``priors.mean`` / ``priors.sigma``.  ``priors.pairs`` / ``midline``
      still add the symmetry and midline terms.
    * ``scale``: ``'auto'`` (default: zeta enabled with sigma_log 0.045 when ``prior`` is
      given, disabled with legacy ``Priors`` only), ``None`` (disabled) or a
      :class:`ScaleConfig`.
    * ``gauge_anchor_idx``: global point indices of the six rigid gauge residuals,
      used only when ``prior.meta['rigid_invariant']`` (DESIGN 4.6).
    * ``sigma_def_mm``: (N,) definition-bias floor in mm (D-06); default from the
      views' ``kinds`` via the noise table, else zeros.
    """
    X0 = np.asarray(X0, float)
    N = len(X0)
    pri = priors or Priors()
    sc = _resolve_scale(scale, prior)
    lay = _Layout(views, N, zeta=sc.enabled)
    zi = lay.zeta_idx
    vis = [~np.isnan(np.asarray(v.uv, float)[:, 0]) for v in views]
    base_w = [np.ones(N) if v.weights is None else np.asarray(v.weights, float) for v in views]
    irls = [np.ones(N) for _ in views]
    noise: list[_ViewNoise | None] = [None] * len(views)
    gauge_sigma = float(BUNDLE["gauge_sigma_mm"].value)

    # ---- shape prior
    shape: Any = None
    if prior is not None:
        shape = _PriorShape(prior, N)
    elif pri.mean is not None:
        sig = np.broadcast_to(np.asarray(pri.sigma, float).reshape(-1, 1) if np.ndim(pri.sigma) == 1
                              else np.asarray(pri.sigma, float), (N, 3)).copy()
        shape = _LegacyShape(pri.mean, sig)
    gauge = _gauge_rows(prior, N, gauge_anchor_idx, X0) if prior is not None else None

    pairs = np.asarray(pri.pairs, np.int64).reshape(-1, 2)
    mid = np.asarray(pri.midline, np.int64)
    S_sym = np.broadcast_to(np.asarray(pri.sigma_sym, float).reshape(-1, 1) if np.ndim(pri.sigma_sym) == 1
                            else np.asarray(pri.sigma_sym, float), (len(pairs), 3)).copy()
    S_mid = np.broadcast_to(np.asarray(pri.sigma_mid, float), (len(mid),)).copy()
    if np.any(~(S_sym > 0)) or np.any(~(S_mid > 0)):
        raise ValueError("sigma_sym and sigma_mid must be > 0")

    def scaled(p: np.ndarray, X: np.ndarray) -> tuple[np.ndarray, float]:
        if zi >= 0:
            s = float(np.exp(-p[zi]))
            return s * X, s
        return X, 1.0

    # ---- residual blocks: data first, then priors (legacy order preserved)
    def data_residuals(p: np.ndarray) -> list[np.ndarray]:
        X = p[lay.pts_off:].reshape(N, 3)
        out = []
        for k, v in enumerate(views):
            R, t, f = _unpack_cam(p, v, k, lay)
            m = vis[k]
            Xc = X[m] @ R.T + t
            uv = Xc[:, :2] / Xc[:, 2:3] * f + np.array([v.camera.cx, v.camera.cy])
            nz = noise[k]
            if nz.iso:
                sw = np.sqrt(base_w[k][m] * irls[k][m]) / nz.sigma
                out.append(((uv - v.uv[m]) * sw[:, None]).ravel())
            else:
                sw = np.sqrt(base_w[k][m] * irls[k][m])
                out.append((np.einsum("nij,nj->ni", nz.W, uv - v.uv[m]) * sw[:, None]).ravel())
        return out

    def prior_residuals(p: np.ndarray) -> list[np.ndarray]:
        X = p[lay.pts_off:].reshape(N, 3)
        out = []
        for idx, mu, s_ in lay.group_prior:
            out.append(np.array([(p[idx] - mu) / s_]))
        if zi >= 0:
            out.append(np.array([p[zi] / sc.sigma_log]))
        Xt, _ = scaled(p, X)
        if shape is not None:
            out.append(shape.residual(Xt))
        if len(pairs):
            out.append(((X[pairs[:, 0]] - X[pairs[:, 1]] * MIRROR) / S_sym).ravel())
        if len(mid):
            out.append(X[mid, 0] / S_mid)
        if gauge is not None:
            out.append(gauge[0] @ (Xt.ravel() - gauge[1]) / gauge_sigma)
        return out

    def residuals(p: np.ndarray) -> np.ndarray:
        return np.concatenate(data_residuals(p) + prior_residuals(p))

    def data_jacobian(p: np.ndarray) -> list[np.ndarray]:
        X = p[lay.pts_off:].reshape(N, 3)
        blocks = []
        for k, v in enumerate(views):
            o = lay.view_off[k]
            R, t, f = _unpack_cam(p, v, k, lay)
            m = np.flatnonzero(vis[k])
            RX = X[m] @ R.T
            Xc = RX + t
            x, y, z = Xc[:, 0], Xc[:, 1], Xc[:, 2]
            # d(u,v)/dXc  (n,2,3)
            Jp = np.zeros((len(m), 2, 3))
            Jp[:, 0, 0] = f / z
            Jp[:, 0, 2] = -f * x / z ** 2
            Jp[:, 1, 1] = f / z
            Jp[:, 1, 2] = -f * y / z ** 2
            nz = noise[k]
            fi = lay.focal_idx[k]
            if nz.iso:
                sw = np.sqrt(base_w[k][m] * irls[k][m]) / nz.sigma
                Jp *= sw[:, None, None]
                if fi >= 0:
                    Jf = np.column_stack([f * x / z * sw, f * y / z * sw])
            else:
                A = nz.W * np.sqrt(base_w[k][m] * irls[k][m])[:, None, None]
                Jp = np.einsum("nij,njk->nik", A, Jp)
                if fi >= 0:
                    Jf = np.einsum("nij,nj->ni", A, np.column_stack([f * x / z, f * y / z]))
            J = np.zeros((2 * len(m), lay.n))
            # rotation (left increment): dXc/dw = -[RX]x
            Jw = -np.einsum("nij,njk->nik", Jp, np.stack([skew(r) for r in RX]) if len(m) else np.zeros((0, 3, 3)))
            J[:, o:o + 3] = Jw.reshape(-1, 3)
            J[:, o + 3:o + 6] = Jp.reshape(-1, 3)
            if fi >= 0:
                J[0::2, fi] = Jf[:, 0]
                J[1::2, fi] = Jf[:, 1]
            JX = np.einsum("nij,jk->nik", Jp, R)
            for a, idx in enumerate(m):
                J[2 * a:2 * a + 2, lay.pts_off + 3 * idx:lay.pts_off + 3 * idx + 3] = JX[a]
            blocks.append(J)
        return blocks

    def prior_jacobian(p: np.ndarray) -> list[np.ndarray]:
        X = p[lay.pts_off:].reshape(N, 3)
        blocks = []
        for idx, mu, s_ in lay.group_prior:
            Jf = np.zeros((1, lay.n))
            Jf[0, idx] = 1.0 / s_
            blocks.append(Jf)
        if zi >= 0:
            Jz = np.zeros((1, lay.n))
            Jz[0, zi] = 1.0 / sc.sigma_log
            blocks.append(Jz)
        Xt, s = scaled(p, X)
        if shape is not None:
            Js = shape.jacobian(Xt)
            Jm = np.zeros((Js.shape[0], lay.n))
            Jm[:, lay.pts_off:] = Js * s if zi >= 0 else Js
            if zi >= 0:
                Jm[:, zi] = -(Js @ Xt.ravel())           # d X~ / d zeta = -X~
            blocks.append(Jm)
        if len(pairs):
            Js = np.zeros((3 * len(pairs), lay.n))
            for a, (l, r) in enumerate(pairs):
                for c in range(3):
                    Js[3 * a + c, lay.pts_off + 3 * l + c] += 1.0 / S_sym[a, c]
                    Js[3 * a + c, lay.pts_off + 3 * r + c] -= MIRROR[c] / S_sym[a, c]
            blocks.append(Js)
        if len(mid):
            Jmid = np.zeros((len(mid), lay.n))
            Jmid[np.arange(len(mid)), lay.pts_off + 3 * mid] = 1.0 / S_mid
            blocks.append(Jmid)
        if gauge is not None:
            Jg = np.zeros((6, lay.n))
            Jg[:, lay.pts_off:] = gauge[0] * (s / gauge_sigma)
            if zi >= 0:
                Jg[:, zi] = -(gauge[0] @ Xt.ravel()) / gauge_sigma
            blocks.append(Jg)
        return blocks

    def jacobian(p: np.ndarray) -> np.ndarray:
        return np.vstack(data_jacobian(p) + prior_jacobian(p))

    def retract(p: np.ndarray, dp: np.ndarray) -> np.ndarray:
        q = p + dp
        for o in lay.view_off:
            q[o:o + 3] = rotation_to_rvec(rodrigues(dp[o:o + 3]) @ rodrigues(p[o:o + 3]))
        return q

    def refresh_noise(p: np.ndarray) -> None:
        """Freeze each view's noise at the current estimate (before an LM run)."""
        X = p[lay.pts_off:].reshape(N, 3)
        for k, v in enumerate(views):
            R, t, f = _unpack_cam(p, v, k, lay)
            noise[k] = _resolve_view_noise(v, X, R, t, f, vis[k])

    def whitened_norms(p: np.ndarray, k: int) -> np.ndarray:
        X = p[lay.pts_off:].reshape(N, 3)
        v = views[k]
        R, t, f = _unpack_cam(p, v, k, lay)
        m = vis[k]
        Xc = X[m] @ R.T + t
        uv = Xc[:, :2] / Xc[:, 2:3] * f + np.array([v.camera.cx, v.camera.cy])
        nz = noise[k]
        if nz.iso:
            return np.linalg.norm(uv - v.uv[m], axis=1) / nz.sigma
        return np.linalg.norm(np.einsum("nij,nj->ni", nz.W, uv - v.uv[m]), axis=1)

    p = _pack(views, X0, lay, sc.init if sc.enabled else 0.0)
    res = None
    for _ in range(max(1, irls_rounds) if huber_px else 1):
        refresh_noise(p)
        res = levenberg_marquardt(residuals, p, jac=jacobian, retract=retract, max_iter=max_iter)
        p = res.x
        if huber_px:
            for k in range(len(views)):
                e = whitened_norms(p, k)
                w = np.ones(N)
                w[vis[k]] = np.where(e <= huber_px, 1.0, huber_px / np.maximum(e, 1e-12))
                irls[k] = w

    X = p[lay.pts_off:].reshape(N, 3).copy()

    # ---- covariance and diagnostics at the solution (weights and noise frozen)
    out: dict[str, Any] = {}
    try:
        Jd_blocks = data_jacobian(p)
        Jd = np.vstack(Jd_blocks) if Jd_blocks else np.zeros((0, lay.n))
        Jp_blocks = prior_jacobian(p)
        Jpr = np.vstack(Jp_blocks) if Jp_blocks else np.zeros((0, lay.n))
        H_data = Jd.T @ Jd
        H_prior = Jpr.T @ Jpr
        post = _posterior(H_data + H_prior, lay, float(BUNDLE["cov_ridge_rel"].value))
        Sig, cov, cov_shape = post["Sigma"], post["cov"], post["cov_shape"]
        rd = np.concatenate(data_residuals(p)) if views else np.zeros(0)
        m_data = int(rd.size)
        p_eff = float(np.sum(H_data * Sig))
        dof = m_data - p_eff
        chi2_red = float(rd @ rd) / dof if dof > 0 else float("nan")
        if sigma_def_mm is None:
            sdef = _default_sigma_def(views, N)
        else:
            sdef = np.broadcast_to(np.asarray(sigma_def_mm, float), (N,)).copy()
        dvar = np.maximum(np.diag(cov_shape), 0.0).reshape(N, 3)
        infl = max(1.0, chi2_red) if np.isfinite(chi2_red) else 1.0
        cam_cov = []
        for k in range(len(views)):
            idx = list(range(lay.view_off[k], lay.view_off[k] + 6))
            if lay.focal_idx[k] >= 0:
                idx.append(lay.focal_idx[k])
            cam_cov.append(Sig[np.ix_(idx, idx)].copy())
        out = dict(
            point_sigma_mm=np.sqrt(dvar), cov=cov, cov_shape=cov_shape,
            zeta=float(p[zi]) if zi >= 0 else None,
            zeta_sigma=float(np.sqrt(max(Sig[zi, zi], 0.0))) if zi >= 0 else None,
            chi2_red=chi2_red, sigma_def_mm=sdef,
            sigma_rep_mm=np.sqrt(dvar * infl + sdef[:, None] ** 2),
            camera_cov=cam_cov, H_data=H_data, H_prior=H_prior, param_index=lay.param_index(),
            obs_cov_px=[noise[k].cov_full(vis[k]) for k in range(len(views))],
            m_data=m_data, p_eff=p_eff, cov_ridge=post["ridge"], flags=list(post["flags"]),
        )
    except (np.linalg.LinAlgError, ValueError):
        out = dict(flags=[FLAG_COV_SINGULAR], param_index=lay.param_index())

    cams, rmses, per_view = [], [], []
    for k, v in enumerate(views):
        R, t, f = _unpack_cam(p, v, k, lay)
        c = v.camera.copy()
        c.R, c.t, c.f = R, t.copy(), f
        cams.append(c)
        m = vis[k]
        e = np.full(N, np.nan)
        e[m] = np.linalg.norm(c.project(X[m]) - v.uv[m], axis=1)
        per_view.append(e)
        rmses.append(float(np.sqrt(np.nanmean(e[m] ** 2))) if m.any() else float("nan"))
    return BundleResult(X, cams, rmses, res.cost, res.iterations, per_view, **out)
