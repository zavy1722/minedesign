"""Multi-view landmark bundle adjustment with anatomical priors.

Unknowns: per view a camera pose (rotation, translation) and optionally a focal
length; a set of N 3D landmarks in the HEAD FRAME (mm; +x subject's left,
+y up, +z out of the face).

Residuals (all whitened, i.e. divided by their standard deviation):
  * reprojection          (u,v) error / sigma_px       (Huber-robustified by IRLS)
  * landmark prior        (X_i - mu_i) / sigma_i        (population mean shape;
                          also fixes the similarity gauge and the absolute scale)
  * bilateral symmetry    (X_l - Mirror(X_r)) / sigma_sym  for left/right pairs
  * midline               x_i / sigma_mid               for midline landmarks
  * focal prior           (log f - log f_prior) / sigma_logf  (e.g. from EXIF)

The analytic Jacobian uses multiplicative rotation updates R <- exp([w]x) R.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..geometry.camera import Camera
from ..geometry.rotations import rodrigues, rotation_to_rvec, skew
from .lm import levenberg_marquardt

MIRROR = np.array([-1.0, 1.0, 1.0])


@dataclass
class Priors:
    mean: np.ndarray | None = None          # (N,3) prior mean landmark positions (head frame)
    sigma: np.ndarray | float = 8.0         # (N,), (N,3) or scalar, mm
    pairs: list[tuple[int, int]] = field(default_factory=list)  # (left, right) index pairs
    sigma_sym: float = 2.0                  # mm; natural asymmetry is real, keep this soft
    midline: list[int] = field(default_factory=list)
    sigma_mid: float = 1.5                  # mm


@dataclass
class ViewObs:
    uv: np.ndarray                    # (N,2); NaN rows = landmark not visible
    camera: Camera                    # initial camera (pose + focal)
    estimate_focal: bool = True
    f_prior: float | None = None      # px
    f_prior_log_sigma: float = 0.35
    weights: np.ndarray | None = None  # (N,) per-landmark confidence
    sigma_px: float = 1.0


@dataclass
class BundleResult:
    X: np.ndarray
    cameras: list[Camera]
    rmse_px: list[float]
    cost: float
    iterations: int
    per_view_residuals: list[np.ndarray]


class _Layout:
    def __init__(self, views: list[ViewObs], n_pts: int):
        self.view_off = []
        off = 0
        for v in views:
            self.view_off.append(off)
            off += 7 if v.estimate_focal else 6
        self.pts_off = off
        self.n = off + 3 * n_pts
        self.n_pts = n_pts


def _pack(views: list[ViewObs], X: np.ndarray, lay: _Layout) -> np.ndarray:
    p = np.zeros(lay.n)
    for v, o in zip(views, lay.view_off):
        p[o:o + 3] = rotation_to_rvec(v.camera.R)
        p[o + 3:o + 6] = v.camera.t
        if v.estimate_focal:
            p[o + 6] = np.log(v.camera.f)
    p[lay.pts_off:] = X.ravel()
    return p


def _unpack_cam(p: np.ndarray, v: ViewObs, o: int) -> tuple[np.ndarray, np.ndarray, float]:
    R = rodrigues(p[o:o + 3])
    t = p[o + 3:o + 6]
    f = float(np.exp(p[o + 6])) if v.estimate_focal else v.camera.f
    return R, t, f


def bundle_adjust(views: list[ViewObs], X0: np.ndarray, priors: Priors | None = None,
                  huber_px: float | None = 3.0, irls_rounds: int = 3, max_iter: int = 100) -> BundleResult:
    X0 = np.asarray(X0, float)
    N = len(X0)
    pri = priors or Priors()
    lay = _Layout(views, N)
    vis = [~np.isnan(v.uv[:, 0]) for v in views]
    base_w = [np.ones(N) if v.weights is None else np.asarray(v.weights, float) for v in views]
    irls = [np.ones(N) for _ in views]

    sig = None
    if pri.mean is not None:
        sig = np.broadcast_to(np.asarray(pri.sigma, float).reshape(-1, 1) if np.ndim(pri.sigma) == 1
                              else np.asarray(pri.sigma, float), (N, 3)).copy()
    pairs = np.asarray(pri.pairs, np.int64).reshape(-1, 2)
    mid = np.asarray(pri.midline, np.int64)

    def residuals(p: np.ndarray) -> np.ndarray:
        X = p[lay.pts_off:].reshape(N, 3)
        out = []
        for k, (v, o) in enumerate(zip(views, lay.view_off)):
            R, t, f = _unpack_cam(p, v, o)
            m = vis[k]
            Xc = X[m] @ R.T + t
            uv = Xc[:, :2] / Xc[:, 2:3] * f + np.array([v.camera.cx, v.camera.cy])
            sw = np.sqrt(base_w[k][m] * irls[k][m]) / v.sigma_px
            out.append(((uv - v.uv[m]) * sw[:, None]).ravel())
            if v.estimate_focal and v.f_prior is not None:
                out.append(np.array([(p[o + 6] - np.log(v.f_prior)) / v.f_prior_log_sigma]))
        if sig is not None:
            out.append(((X - pri.mean) / sig).ravel())
        if len(pairs):
            out.append(((X[pairs[:, 0]] - X[pairs[:, 1]] * MIRROR) / pri.sigma_sym).ravel())
        if len(mid):
            out.append(X[mid, 0] / pri.sigma_mid)
        return np.concatenate(out)

    def jacobian(p: np.ndarray) -> np.ndarray:
        X = p[lay.pts_off:].reshape(N, 3)
        blocks = []
        for k, (v, o) in enumerate(zip(views, lay.view_off)):
            R, t, f = _unpack_cam(p, v, o)
            m = np.flatnonzero(vis[k])
            RX = X[m] @ R.T
            Xc = RX + t
            x, y, z = Xc[:, 0], Xc[:, 1], Xc[:, 2]
            sw = np.sqrt(base_w[k][m] * irls[k][m]) / v.sigma_px
            # d(u,v)/dXc  (n,2,3)
            Jp = np.zeros((len(m), 2, 3))
            Jp[:, 0, 0] = f / z
            Jp[:, 0, 2] = -f * x / z ** 2
            Jp[:, 1, 1] = f / z
            Jp[:, 1, 2] = -f * y / z ** 2
            Jp *= sw[:, None, None]
            J = np.zeros((2 * len(m), lay.n))
            # rotation (left increment): dXc/dw = -[RX]x
            Jw = -np.einsum("nij,njk->nik", Jp, np.stack([skew(r) for r in RX]))
            J[:, o:o + 3] = Jw.reshape(-1, 3)
            J[:, o + 3:o + 6] = Jp.reshape(-1, 3)
            if v.estimate_focal:
                J[0::2, o + 6] = f * x / z * sw
                J[1::2, o + 6] = f * y / z * sw
            JX = np.einsum("nij,jk->nik", Jp, R)
            for a, idx in enumerate(m):
                J[2 * a:2 * a + 2, lay.pts_off + 3 * idx:lay.pts_off + 3 * idx + 3] = JX[a]
            blocks.append(J)
            if v.estimate_focal and v.f_prior is not None:
                Jf = np.zeros((1, lay.n))
                Jf[0, o + 6] = 1.0 / v.f_prior_log_sigma
                blocks.append(Jf)
        if sig is not None:
            Jm = np.zeros((3 * N, lay.n))
            Jm[np.arange(3 * N), lay.pts_off + np.arange(3 * N)] = 1.0 / sig.ravel()
            blocks.append(Jm)
        if len(pairs):
            Js = np.zeros((3 * len(pairs), lay.n))
            for a, (l, r) in enumerate(pairs):
                for c in range(3):
                    Js[3 * a + c, lay.pts_off + 3 * l + c] += 1.0 / pri.sigma_sym
                    Js[3 * a + c, lay.pts_off + 3 * r + c] -= MIRROR[c] / pri.sigma_sym
            blocks.append(Js)
        if len(mid):
            Jmid = np.zeros((len(mid), lay.n))
            Jmid[np.arange(len(mid)), lay.pts_off + 3 * mid] = 1.0 / pri.sigma_mid
            blocks.append(Jmid)
        return np.vstack(blocks)

    def retract(p: np.ndarray, dp: np.ndarray) -> np.ndarray:
        q = p + dp
        for o in lay.view_off:
            q[o:o + 3] = rotation_to_rvec(rodrigues(dp[o:o + 3]) @ rodrigues(p[o:o + 3]))
        return q

    p = _pack(views, X0, lay)
    res = None
    for _ in range(irls_rounds if huber_px else 1):
        res = levenberg_marquardt(residuals, p, jac=jacobian, retract=retract, max_iter=max_iter)
        p = res.x
        if huber_px:
            for k, (v, o) in enumerate(zip(views, lay.view_off)):
                R, t, f = _unpack_cam(p, v, o)
                X = p[lay.pts_off:].reshape(N, 3)
                m = vis[k]
                Xc = X[m] @ R.T + t
                uv = Xc[:, :2] / Xc[:, 2:3] * f + np.array([v.camera.cx, v.camera.cy])
                e = np.linalg.norm(uv - v.uv[m], axis=1) / v.sigma_px
                w = np.ones(N)
                w[m] = np.where(e <= huber_px, 1.0, huber_px / np.maximum(e, 1e-12))
                irls[k] = w

    X = p[lay.pts_off:].reshape(N, 3).copy()
    cams, rmses, per_view = [], [], []
    for k, (v, o) in enumerate(zip(views, lay.view_off)):
        R, t, f = _unpack_cam(p, v, o)
        c = v.camera.copy()
        c.R, c.t, c.f = R, t.copy(), f
        cams.append(c)
        m = vis[k]
        e = np.full(N, np.nan)
        e[m] = np.linalg.norm(c.project(X[m]) - v.uv[m], axis=1)
        per_view.append(e)
        rmses.append(float(np.sqrt(np.nanmean(e[m] ** 2))) if m.any() else float("nan"))
    return BundleResult(X, cams, rmses, res.cost, res.iterations, per_view)
