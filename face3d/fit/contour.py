"""Contours v2: ContourObs, sub-vertex rim, residual kinds, matching and the contour Term
(DESIGN D-13, 4.15 stage D, 4.16, SIL-3; WBS WP-17).

Silhouettes recover what landmarks miss (the profile g'-n'-prn-sn-ls-li-pg', the jaw and
cheek outline; *face-segmentation-contours*).  This module turns traced or segmented
outlines into normal-only residuals against the **sub-vertex** occluding contour of the
mesh and plugs them into the landmark bundle as a :class:`~face3d.solve.terms.Term`.

Conventions
-----------
* Units: mesh in mm (head frame, DESIGN 3.1); image coordinates in px with the origin at
  the top-left *corner*, pixel ``[r, c]`` centred at (c + 0.5, r + 0.5) (DESIGN 3.1).
* OpenCV cameras X_c = R X + t (+y down, +z forward).  Inside the bundle each view uses the
  inverse-depth block of DESIGN D-02 / 4.3 (u = c + s ((R X)_xy + tau) / (1 + rho (R X)_z));
  camera Jacobians follow ``face3d.solve.terms`` (left rotation increment, rho stored in
  1/m so d/d rho_param = 1e-3 d/d rho_mm, a = ln s).
* **Outward normals.** ``ContourObs.normal_out`` points away from the imaged object
  (skin -> background).  The model rim normal ``normal2d`` is the image of the 3D vertex
  normal at the rim point, which points away from the object's image region too.
* **Signed residual** (DESIGN 4.16): r = n_obs . (pi(p) - x) / sigma_n, positive when the
  model rim lies *outside* the observed contour.  Kinds: ``hard`` -> r (Huber delta 2 by
  IRLS weights frozen per outer iteration, the contour stage's solver schedule);
  ``outer_bound`` (hair, beard, hat: the skin silhouette lies inside the observed line) ->
  max(0, r - margin / sigma); ``inner_bound`` (confident skin must lie inside the
  projected head) -> max(0, -r - margin / sigma).  Bounds never pull the model across
  their side (zero residual and zero gradient there).

Model rim (DESIGN 4.16 "Model rim"; [Acc 3.8])
----------------------------------------------
With per-vertex normals n and the camera centre C, q_v = n_v . (x_v - C).  On every edge
(a, b) where q changes sign and at least one adjacent triangle is front-facing
((B - A) x (C - A) . (centroid - C) < 0, the convention of ``silhouette_vertices``),
t = q_a / (q_a - q_b) and p = x_a + t (x_b - x_a).  Within one triangle the zero set of the
linearly interpolated q is the straight segment between its two edge crossings
(``RimPoints.segments``), so :func:`densify_rim` inserts exact samples of that polyline
(each a fixed combination of four vertices) at <= ``spacing_px`` in the image: dense
observations then match a point of the projected rim polyline, not only its vertices,
which removes the half-edge bias of vertex contours.  Visibility: with a raster
(:func:`face3d.mesh.raster.rasterize`, any resolution, mapped by the corner-convention
scale), a sample is visible when the raster depth at its projection, or at a probe
``probe_px`` beyond it along the outward image normal, is >= its camera depth - 1 mm.
The probe is needed because the pixel containing a rim point is often covered by the
grazing surface itself, sqrt(2 r delta) nearer than the rim (several mm for a 0.25 mm
image offset on an 80 mm radius); an occluder in front of the rim covers both pixels.

Matching (DESIGN 4.16 "Matching"): every observed sample takes the nearest rim sample
within ``gate_px`` whose image normal is within ``max_normal_deg`` (40 deg) of its own,
found with a uniform grid of cell ``gate_px`` (3 x 3 cells per query; no M x P matrix).
The gate starts at 0.15 IOD_px and shrinks geometrically to 5 sigma_n over the outer
iterations; pairs, the rim samples' vertex weights (t) and the IRLS weights are frozen
within each outer iteration so the Term's Jacobian is exact.

Backward term: rim samples read the observed contour's distance transform
(:mod:`face3d.fit.distance_transform`, exact squared EDT, sqrt) truncated at 3 sigma,
weight 0.5 (DESIGN 4.16; :func:`backward_residuals`).  :class:`ContourDistance` stores,
besides the EDT, the nearest observed sample of every cell; by default it returns the
distance sqrt(s^2 + e^2) to the short tangent segment that sample stands for (s the
normal offset n_j . (u - x_j), e the tangential excess beyond the half-way points to its
neighbours, :func:`tangent_extents`): a sub-pixel refinement of the cell-centre distance
on the contour's span, and the Euclidean distance past an **open end** (pins, lasso,
edge-snapped jaw), so the truncation applies there with zero gradient as for the
sqrt-EDT (mode ``'edt'`` gives the raw bilinear sqrt-EDT).  Inside the Term the EDT's
nearest sample j of each backward rim sample is frozen per outer iteration; rim samples
are gated on the Euclidean distance and dropped when they do not project onto the
contour's span (excess > 1 px); the row is the signed normal offset n_j . (pi(p) - x_j) /
sigma clipped to +-3: equal to the EDT distance to first order near the contour, and
smooth, so the Jacobian is exact (a nearest-sample switch inside an LM run would make
the residual jump).

Stage driver (DESIGN 4.15 D): :func:`contour_stage` runs the outer iterations through
:func:`face3d.solve.bundle.bundle_adjust` with the LinearBasis shape model, the landmark
data, a landmark hold prior (com R5.2: no landmark moves > 0.5 mm), the coefficient
prior :class:`face3d.solve.shape_models.BasisPrior` and this Term.  SIL-3:
:func:`diagnose_focal_distance` (the rule) and :func:`focal_distance_check` (cameras from
the interior landmarks with the shape held, contours as witnesses, the refit cameras'
uncertainty in sigma); ``contour_stage(witness_views=...)`` keeps views out of the fit
and checks them against the fitted shape.  A shape fitted to a view's own contours
absorbs a focal / distance error (the dolly-zoom ambiguity), so SIL-3 needs witnesses.

Noise and sample weights (DESIGN 4.16 "Noise"): sigma_n^2 = sigma_edge^2 +
(0.5 s_model)^2 + sigma_blur^2 floored at 0.005 IOD_px (:func:`sigma_n_model`); a view
contributes at most 40 effective samples (:func:`effective_sample_weights`), one budget
shared by its forward kinds and its backward rows.

numpy + stdlib only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Any, Sequence

import numpy as np

from ..core.config import Default, register_defaults
from ..geometry.camera import Camera
from ..mesh.raster import RasterResult, rasterize
from ..mesh.reduced import coef_matrix
from .distance_transform import edt_squared, edt_with_nearest, gradient, sample_bilinear
from .silhouette import edge_faces

__all__ = [
    "ContourObs", "RimPoints", "RimSamples", "ContourDistance", "ContourTerm", "ContourStageResult",
    "rim_points", "densify_rim", "match", "grid_nearest", "forward_residuals", "backward_residuals",
    "sigma_n_model", "effective_sample_weights", "diagnose_focal_distance", "contour_stage",
    "landmark_rms_pct_iod", "vertex_normals", "scale_camera", "KINDS", "CONTOUR", "FINDING_FOCAL_DIST",
    "contour_view_stats", "focal_distance_check", "FLAG_LANDMARK_SHIFT", "tangent_extents",
    "interior_landmark_mask", "pose_uv_jacobian", "SIL3_NON_INTERIOR_BASES",
]

_BRAIN = "\U0001F9E0"   # expert knowledge, provisional
_NEW = "\U0001F195"     # introduced by this design / WP spec, uncalibrated
_D416 = "DESIGN 4.16"

CONTOUR = register_defaults("contour", {
    "gate_iod_frac": Default(0.15, _BRAIN, "DESIGN D-13 / 4.16: match gate starts at 0.15 IOD_px "
                             "(face-segmentation-contours)", "IOD", (1e-6, 10.0)),
    "gate_final_sigma": Default(5.0, _BRAIN, _D416 + ": gate shrinks to 5 sigma_n (face-segmentation-contours)",
                                "sigma", (1e-6, 1000.0)),
    "max_normal_deg": Default(40.0, _BRAIN, "DESIGN D-13 / 4.16: reject pairs with normals > 40 deg apart "
                              "(face-segmentation-contours 30-45 deg)", "deg", (0.0, 180.0)),
    "sigma_floor_iod": Default(0.005, _BRAIN, _D416 + " 'Noise': sigma_n floored at 0.005 IOD_px "
                               "(face-segmentation-contours)", "IOD", (0.0, 1.0)),
    "backward_trunc": Default(3.0, _BRAIN, _D416 + ": backward EDT term truncated at 3 sigma", "sigma",
                              (1e-6, 1000.0)),
    "backward_weight": Default(0.5, _BRAIN, _D416 + ": backward EDT term weight 0.5", "", (0.0, 1000.0)),
    "backward_end_px": Default(1.0, _NEW, "WP-17 review fix: a rim sample carries a backward row only when it "
                               "projects onto the observed contour's span (tangential excess <= 1 px); past "
                               "an open end the truncated EDT term is constant (zero gradient)", "px",
                               (0.0, 1000.0)),
    "effective_cap": Default(40.0, _BRAIN, _D416 + ": at most 40 effective samples per view "
                             "(face-segmentation-contours 30-50)", "", (1.0, 1e9)),
    "huber_delta": Default(2.0, _BRAIN, "face-segmentation-contours 'hard: Huber delta ~ 2'; DESIGN D-08 "
                           "Huber delta = 2 sigma", "sigma", (1e-6, 1000.0)),
    "outer_bound_weight": Default(10.0, _BRAIN, _D416 + " 'Residuals': outer_bound weight x10 (hair, beard, hat)",
                                  "", (0.0, 1e6)),
    "visibility_tol_mm": Default(1.0, _NEW, "WBS WP-17: rim visible when raster depth >= camera depth - 1 mm",
                                 "mm", (0.0, 1000.0)),
    "visibility_probe_raster_px": Default(1.5, _NEW, "WP-17 implementation: visibility probe 1.5 raster px "
                                          "beyond the rim along the outward normal (see module docstring)",
                                          "px", (0.0, 100.0)),
    "rim_spacing_px": Default(2.0, _NEW, "WP-17 implementation: rim polyline samples every <= 2 px", "px",
                              (1e-3, 1000.0)),
    "max_rows_per_view": Default(150, _NEW, "WP-17 implementation: residual rows per view and direction "
                                 "(evenly subsampled; the effective-sample cap keeps the information)", "",
                                 (1, 1000000)),
    "mask_sigma_edge_px": Default(1.0 / math.sqrt(12.0), _NEW, "WP-17: binary-mask edge quantisation, uniform "
                                  "over one pixel (SD 1/sqrt 12 px)", "px", (0.0, 100.0)),
    "hold_sigma_mm": Default(0.1, _NEW, "com R5.2 / DESIGN 4.15 D: no landmark moves > 0.5 mm in the contour "
                             "stage; hold prior sigma = gate / 5 (0.25 mm let profile landmarks move 0.6-1.1 mm "
                             "on WP-11 subjects)", "mm", (1e-6, 1000.0)),
    "landmark_shift_gate_mm": Default(0.5, _BRAIN, "com R5.2 / DESIGN 4.15 D: no landmark moves > 0.5 mm in the "
                                      "contour stage (flag C-LM-SHIFT otherwise)", "mm", (0.0, 1000.0)),
    "raster_scale": Default(0.5, _NEW, "WP-17 implementation: visibility raster at half resolution", "",
                            (1e-3, 4.0)),
    "diag_rms_pct_iod": Default(3.0, _BRAIN, "DESIGN 4.16 SIL-3: interior landmark RMS < 3 % IOD", "% IOD",
                                (0.0, 100.0)),
    "diag_sigma_k": Default(3.0, _BRAIN, "DESIGN 4.16 SIL-3: contour residual median > 3 sigma_n", "sigma",
                            (0.0, 1000.0)),
    "diag_min_views": Default(2, _BRAIN, "DESIGN 4.16 SIL-3: on >= 2 views", "", (1, 1000)),
})

#: Contour kinds (DESIGN D-13).
KINDS = ("hard", "outer_bound", "inner_bound")
#: SIL-3 finding code: "focal or distance wrong, not the face" (DESIGN 4.16).
FINDING_FOCAL_DIST = "C-FOCAL-DIST"
#: Contour-stage flag: a landmark moved more than the com R5.2 gate (0.5 mm).
FLAG_LANDMARK_SHIFT = "C-LM-SHIFT"


# =========================================================================== small helpers
def _unit(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, float)
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.where(n > 1e-300, n, 1.0)


def vertex_normals(V: np.ndarray, tris: np.ndarray) -> np.ndarray:
    """Unit area-weighted vertex normals of the triangle mesh (V, tris) (outward for CCW winding)."""
    V = np.asarray(V, float)
    t = np.asarray(tris, np.int64)
    fn = np.cross(V[t[:, 1]] - V[t[:, 0]], V[t[:, 2]] - V[t[:, 0]])
    n = np.zeros_like(V)
    for k in range(3):
        for a in range(3):
            n[:, a] += np.bincount(t[:, k], weights=fn[:, a], minlength=len(V))
    return _unit(n)


def scale_camera(camera: Camera, scale: float) -> Camera:
    """Camera of a round(W s) x round(H s) image with corner-convention intrinsics (DESIGN 3.1)."""
    s = float(scale)
    if s == 1.0:
        return camera.copy()
    W2 = max(1, int(round(camera.width * s)))
    H2 = max(1, int(round(camera.height * s)))
    sx, sy = W2 / float(camera.width), H2 / float(camera.height)
    return Camera(f=camera.f * sx, cx=camera.cx * sx, cy=camera.cy * sy, width=W2, height=H2,
                  R=camera.R.copy(), t=camera.t.copy(), k=camera.k.copy())


def _proj_jac(cam: Camera, P: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """uv (n,2), depth (n,), d uv / d X (n, 2, 3) of the pinhole camera (distortion ignored)."""
    Xc = np.asarray(P, float) @ cam.R.T + cam.t
    z = Xc[:, 2]
    zs = np.where(np.abs(z) > 1e-12, z, 1e-12)
    uv = cam.f * Xc[:, :2] / zs[:, None] + np.array([cam.cx, cam.cy])
    J = np.zeros((len(P), 2, 3))
    J[:, 0, 0] = cam.f / zs
    J[:, 1, 1] = cam.f / zs
    J[:, 0, 2] = -cam.f * Xc[:, 0] / zs ** 2
    J[:, 1, 2] = -cam.f * Xc[:, 1] / zs ** 2
    return uv, z, np.einsum("nij,jk->nik", J, cam.R)


# =========================================================================== observations
@dataclass
class ContourObs:
    """An observed image contour of one view (DESIGN D-13, 4.16 "Observations").

    view : index of the view (``ViewObs`` order of the bundle).
    xy : (M, 2) sub-pixel samples, px (corner convention).
    normal_out : (M, 2) unit outward normals (object -> background); normalised on init.
    sigma_n_px : (M,) or scalar normal sigma, px (broadcast on init).
    kind : 'hard', 'outer_bound' or 'inner_bound'.
    source : free provenance label (e.g. 'pins', 'lasso', 'mediapipe_oval', 'edge_snap', 'mask').
    commercial_ok : licence flag of the source (None = unknown; joins the AND-chain, DESIGN 2.1).
    margin_px : bound margin (px) of the bound kinds (DESIGN 4.16: 0-3 mm in px).
    """

    view: int
    xy: np.ndarray
    normal_out: np.ndarray
    sigma_n_px: Any
    kind: str = "hard"
    source: str = "unspecified"
    commercial_ok: bool | None = None
    margin_px: float = 0.0

    def __post_init__(self) -> None:
        self.view = int(self.view)
        self.xy = np.asarray(self.xy, float).reshape(-1, 2).copy()
        M = len(self.xy)
        nrm = np.asarray(self.normal_out, float).reshape(-1, 2)
        if nrm.shape != (M, 2):
            raise ValueError(f"normal_out must have shape ({M}, 2), got {nrm.shape}")
        ln = np.linalg.norm(nrm, axis=1)
        if M and not np.all(ln > 1e-12):
            raise ValueError("normal_out has zero-length rows")
        self.normal_out = nrm / np.where(ln > 0, ln, 1.0)[:, None]
        sig = np.broadcast_to(np.asarray(self.sigma_n_px, float), (M,)).astype(float).copy()
        if M and not np.all(np.isfinite(sig) & (sig > 0)):
            raise ValueError("sigma_n_px must be finite and > 0")
        self.sigma_n_px = sig
        if self.kind not in KINDS:
            raise ValueError(f"kind must be one of {KINDS}, got {self.kind!r}")
        if not np.all(np.isfinite(self.xy)):
            raise ValueError("xy must be finite")
        self.margin_px = float(self.margin_px)
        if self.margin_px < 0:
            raise ValueError("margin_px must be >= 0")
        self.source = str(self.source)

    @property
    def M(self) -> int:
        return len(self.xy)

    @classmethod
    def from_polyline(cls, points: np.ndarray, closed: bool, outward_ref_point: Sequence[float],
                      sigma_n_px: Any, kind: str = "hard", view: int = 0, *, source: str = "polyline",
                      commercial_ok: bool | None = None, margin_px: float = 0.0) -> "ContourObs":
        """Observation from an ordered polyline (pins, lasso, detector oval, snapped curve).

        Normals by central differences of the vertices (one-sided at the ends of an open
        line), rotated by 90 deg and oriented away from ``outward_ref_point`` (a point
        inside the object, e.g. the face centre): one global orientation, chosen by the
        length-weighted majority of n . (p - ref), so concave stretches keep a consistent
        side.  Coincident consecutive points are dropped first.
        """
        P = np.asarray(points, float).reshape(-1, 2)
        if len(P) >= 2:
            keep = np.r_[True, np.linalg.norm(np.diff(P, axis=0), axis=1) > 1e-12]
            P = P[keep]
            if closed and len(P) > 2 and np.linalg.norm(P[-1] - P[0]) <= 1e-12:
                P = P[:-1]
        if len(P) < 2:
            raise ValueError("a polyline needs at least two distinct points")
        if closed:
            T = np.roll(P, -1, axis=0) - np.roll(P, 1, axis=0)
        else:
            T = np.empty_like(P)
            T[1:-1] = P[2:] - P[:-2]
            T[0] = P[1] - P[0]
            T[-1] = P[-1] - P[-2]
        T = _unit(T)
        N = np.column_stack([T[:, 1], -T[:, 0]])
        ref = np.asarray(outward_ref_point, float).reshape(2)
        seg = np.linalg.norm(np.roll(P, -1, axis=0) - P, axis=1) + np.linalg.norm(P - np.roll(P, 1, axis=0), axis=1)
        if np.sum(seg * np.sum(N * (P - ref), axis=1)) < 0:
            N = -N
        return cls(view, P, N, sigma_n_px, kind, source, commercial_ok, margin_px)

    @classmethod
    def from_mask(cls, mask: np.ndarray, view: int = 0, kind: str = "hard", *, sigma_n_px: Any = None,
                  source: str = "mask", commercial_ok: bool | None = None, margin_px: float = 0.0,
                  offset_px: float = 0.5, smooth: int = 2, image_border: str = "drop") -> "ContourObs":
        """Observation from a binary object mask (True = object; segmenter or painted mask).

        Boundary pixels (in the mask, with a 4-neighbour outside it, the image border
        counting as outside for the tracing) are ordered by Moore-neighbour contour
        following, one chain per traced contour (outer boundaries and holes), chains in
        raster order of their first pixel.  Normals come from the gradient of the signed
        distance field sqrt(EDT(~mask)) - sqrt(EDT(mask)) (the EDT of the complement
        inside, of the mask outside), averaged over +-``smooth`` neighbours along the
        chain.  Each sample is the pixel centre moved ``offset_px`` (0.5) along its
        outward normal, onto the edge between the last inside and the first outside pixel
        centre.  The default sigma is :func:`sigma_n_model` with sigma_edge = 1/sqrt(12) px
        (uniform pixel quantisation) and s_model = 1 px (a full-resolution mask).

        **Image border** (``image_border``): a mask cut off by the image edge (a typical
        head-and-shoulders segmentation) is a *truncation*, not a silhouette.  With
        ``'drop'`` (default) the boundary pixels that lie on the image border and have no
        background 4-neighbour inside the image are not emitted, and the distance field
        used for the normals continues the mask beyond the edge (edge replication), so
        the samples of a contour that runs into the edge keep their true normals.
        ``'keep'`` treats the border as background (the behaviour before the WP-17 review).
        """
        if image_border not in ("drop", "keep"):
            raise ValueError("image_border must be 'drop' or 'keep'")
        m = np.asarray(mask, bool)
        if m.ndim != 2:
            raise ValueError("mask must be 2D")
        if not m.any():
            raise ValueError("mask is empty")
        H, W = m.shape
        rows, cols = np.nonzero(m)
        r0, r1 = max(int(rows.min()) - 3, 0), min(int(rows.max()) + 4, H)
        c0, c1 = max(int(cols.min()) - 3, 0), min(int(cols.max()) + 4, W)
        sub = np.zeros((r1 - r0 + 2, c1 - c0 + 2), bool)          # one-pixel frame = outside
        sub[1:-1, 1:-1] = m[r0:r1, c0:c1]
        chains = _trace_boundaries(sub)
        drop = image_border == "drop"
        sdm = sub
        if drop:
            # the normals' distance field continues the mask across the image edge
            sdm = sub.copy()
            if r0 == 0:
                sdm[0, :] = sdm[1, :]
            if r1 == H:
                sdm[-1, :] = sdm[-2, :]
            if c0 == 0:
                sdm[:, 0] = sdm[:, 1]
            if c1 == W:
                sdm[:, -1] = sdm[:, -2]
        sd = np.sqrt(edt_squared(~sdm)) - np.sqrt(edt_squared(sdm))
        gu, gv = gradient(sd)
        runs: list[tuple[np.ndarray, bool | None]] = []          # (chain, closed: None = by its ends)
        for ch in chains:
            if drop and len(ch):
                ri, ci = ch[:, 0] - 1 + r0, ch[:, 1] - 1 + c0          # image pixel of each chain pixel
                on_edge = (ri == 0) | (ri == H - 1) | (ci == 0) | (ci == W - 1)
                if on_edge.any():
                    bg = np.zeros(len(ch), bool)                        # a background 4-neighbour in the image
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        rn, cn = ri + dr, ci + dc
                        inim = (rn >= 0) & (rn < H) & (cn >= 0) & (cn < W)
                        bg[inim] |= ~m[rn[inim], cn[inim]]
                    keep = ~(on_edge & ~bg)
                    if not keep.any():
                        continue
                    if keep.all():
                        runs.append((ch, None))
                        continue
                    # split into open runs at the dropped pixels (rotated so no run wraps around)
                    first_drop = int(np.argmin(keep))
                    order = np.roll(np.arange(len(ch)), -first_drop)
                    kr = keep[order]
                    starts = np.flatnonzero(kr & ~np.r_[False, kr[:-1]])
                    for st in starts.tolist():
                        en = st
                        while en + 1 < len(kr) and kr[en + 1]:
                            en += 1
                        runs.append((ch[order[st:en + 1]], False))
                    continue
            runs.append((ch, None))
        xy_l, n_l = [], []
        for ch, closed_flag in runs:
            rr, cc = ch[:, 0], ch[:, 1]
            g = np.column_stack([gu[rr, cc], gv[rr, cc]])
            if smooth > 0 and len(ch) > 2:
                closed = (abs(int(rr[0]) - int(rr[-1])) <= 1 and abs(int(cc[0]) - int(cc[-1])) <= 1
                          if closed_flag is None else closed_flag)
                acc = g.copy()
                for s in range(1, int(smooth) + 1):
                    if closed:
                        acc += np.roll(g, s, axis=0) + np.roll(g, -s, axis=0)
                    else:
                        acc[s:] += g[:-s]
                        acc[:-s] += g[s:]
                g = acc
            n = -g
            ln = np.linalg.norm(n, axis=1)
            ok = ln > 1e-12
            n = n[ok] / ln[ok, None]
            uv = np.column_stack([cc[ok] - 1 + c0 + 0.5, rr[ok] - 1 + r0 + 0.5]) + float(offset_px) * n
            xy_l.append(uv)
            n_l.append(n)
        if not xy_l:
            raise ValueError("the mask has no boundary inside the image (it fills the frame)")
        xy = np.vstack(xy_l)
        nn = np.vstack(n_l)
        if sigma_n_px is None:
            sigma_n_px = sigma_n_model(float(CONTOUR["mask_sigma_edge_px"].value), 1.0, 0.0, 0.0)
        return cls(view, xy, nn, sigma_n_px, kind, source, commercial_ok, margin_px)


# Moore neighbourhood, clockwise on screen (rows grow downward): N, NE, E, SE, S, SW, W, NW.
_DIRS = np.array([(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)], np.int64)
_DIR_INDEX = {(int(a), int(b)): i for i, (a, b) in enumerate(_DIRS)}


def _trace_boundaries(m: np.ndarray) -> list[np.ndarray]:
    """Ordered 4-boundary pixel chains (row, col) of mask ``m`` (which has an all-False frame)."""
    interior = np.zeros_like(m)
    interior[1:-1, 1:-1] = (m[1:-1, 1:-1] & m[:-2, 1:-1] & m[2:, 1:-1] & m[1:-1, :-2] & m[1:-1, 2:])
    bnd = m & ~interior
    todo = bnd.copy()
    chains: list[np.ndarray] = []
    rows, cols = np.nonzero(bnd)
    n_b = len(rows)
    for r, c in zip(rows.tolist(), cols.tolist()):
        if not todo[r, c]:
            continue
        back = None
        for d in (6, 0, 2, 4):           # W, N, E, S: a background 4-neighbour to come from
            dr, dc = _DIRS[d]
            if not m[r + dr, c + dc]:
                back = d
                break
        chain = [(r, c)]
        todo[r, c] = False
        if back is None:                 # cannot happen for a 4-boundary pixel
            chains.append(np.array(chain, np.int64))
            continue
        start = (r, c, back)
        cur_r, cur_c, cur_b = r, c, back
        first_move = None
        for _ in range(4 * n_b + 16):
            moved = False
            for i in range(1, 9):
                d = (cur_b + i) % 8
                nr, nc = cur_r + int(_DIRS[d, 0]), cur_c + int(_DIRS[d, 1])
                if m[nr, nc]:
                    pd = (cur_b + i - 1) % 8
                    br, bc = cur_r + int(_DIRS[pd, 0]), cur_c + int(_DIRS[pd, 1])
                    nb = _DIR_INDEX[(br - nr, bc - nc)]
                    move = (nr, nc, nb)
                    moved = True
                    break
            if not moved:
                break                        # isolated pixel
            if first_move is None:
                first_move = move
            elif (cur_r, cur_c) == (start[0], start[1]) and move == first_move:
                break                        # Jacob's stopping criterion
            cur_r, cur_c, cur_b = move
            if (cur_r, cur_c) == (start[0], start[1]) and first_move is not None and cur_b == start[2]:
                break
            if bnd[cur_r, cur_c]:
                if (cur_r, cur_c) != (start[0], start[1]) or len(chain) == 0:
                    chain.append((cur_r, cur_c))
                todo[cur_r, cur_c] = False
        # drop a duplicated closing pixel
        if len(chain) > 1 and chain[-1] == chain[0]:
            chain.pop()
        chains.append(np.array(chain, np.int64))
    return chains


# =========================================================================== model rim
@dataclass
class RimPoints:
    """Sub-vertex rim of a mesh seen by one camera (DESIGN 4.16 "Model rim").

    p (K, 3) mm; edge (K, 2) vertex ids (a, b); t (K,) with p = x_a + t (x_b - x_a);
    normal2d (K, 2) unit outward image normal (zero when the normal is seen end-on);
    visible (K,) bool; uv (K, 2) px; depth (K,) camera z, mm; normal3d (K, 3) interpolated
    unit vertex normal; segments (S, 2) indices of rim points joined inside one triangle.
    """

    p: np.ndarray
    edge: np.ndarray
    t: np.ndarray
    normal2d: np.ndarray
    visible: np.ndarray
    uv: np.ndarray = field(default_factory=lambda: np.zeros((0, 2)))
    depth: np.ndarray = field(default_factory=lambda: np.zeros(0))
    normal3d: np.ndarray = field(default_factory=lambda: np.zeros((0, 3)))
    segments: np.ndarray = field(default_factory=lambda: np.zeros((0, 2), np.int64))

    def __len__(self) -> int:
        return len(self.t)


@dataclass
class RimSamples:
    """Samples of the projected rim polyline, each a fixed combination of four vertices.

    vid (S, 4) vertex ids and w (S, 4) weights (rows sum to 1): p = sum_k w_k x_vid_k.
    p (S, 3), uv (S, 2), depth (S,), normal2d (S, 2), normal3d (S, 3), visible (S,).
    """

    vid: np.ndarray
    w: np.ndarray
    p: np.ndarray
    uv: np.ndarray
    depth: np.ndarray
    normal2d: np.ndarray
    normal3d: np.ndarray
    visible: np.ndarray

    def __len__(self) -> int:
        return len(self.w)


def _normal2d(cam: Camera, P: np.ndarray, n3: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    uv, z, J = _proj_jac(cam, P)
    n2 = np.einsum("nij,nj->ni", J, n3)
    ln = np.linalg.norm(n2, axis=1)
    ok = ln > 1e-9 * np.maximum(np.linalg.norm(J[:, 0], axis=1), 1e-300)
    n2 = np.where(ok[:, None], n2 / np.where(ln > 0, ln, 1.0)[:, None], 0.0)
    return uv, z, n2


def _visibility(raster: RasterResult | None, cam: Camera, uv: np.ndarray, z: np.ndarray, n2: np.ndarray,
                tol_mm: float, probe_px: float | None) -> np.ndarray:
    """Rim-sample visibility from a raster of any resolution (see the module docstring)."""
    ok = np.isfinite(uv).all(axis=1) & (z > 0) & (np.linalg.norm(n2, axis=1) > 0)
    if raster is None:
        return ok
    H, W = raster.depth.shape
    sx, sy = W / float(cam.width), H / float(cam.height)
    if probe_px is None:
        probe_px = float(CONTOUR["visibility_probe_raster_px"].value) / min(sx, sy)

    def depth_at(P: np.ndarray) -> np.ndarray:
        out = np.full(len(P), np.inf)
        with np.errstate(invalid="ignore"):
            i = np.floor(P[:, 0] * sx)
            j = np.floor(P[:, 1] * sy)
            inside = np.isfinite(i) & np.isfinite(j) & (i >= 0) & (j >= 0) & (i < W) & (j < H)
        out[inside] = raster.depth[j[inside].astype(np.int64), i[inside].astype(np.int64)]
        return out

    lim = z - float(tol_mm)
    vis = (depth_at(uv) >= lim) | (depth_at(uv + float(probe_px) * n2) >= lim)
    return ok & vis


def rim_points(V: np.ndarray, tris: np.ndarray, vertex_normals: np.ndarray, cam: Camera,
               raster: RasterResult | None = None, *, topo: tuple[np.ndarray, np.ndarray] | None = None,
               tol_mm: float | None = None, probe_px: float | None = None) -> RimPoints:
    """Sub-vertex occluding contour of (V, tris) seen by ``cam`` (module docstring).

    vertex_normals (V, 3) unit outward normals (e.g. :func:`vertex_normals`).  ``raster``:
    a :class:`~face3d.mesh.raster.RasterResult` of the same mesh and camera (possibly at a
    scaled resolution) for the visibility test; without it every sample in front of the
    camera with a defined image normal is visible.  ``topo``: precomputed
    ``silhouette.edge_faces(tris)``.
    """
    V = np.asarray(V, float)
    tris = np.asarray(tris, np.int64)
    Nn = np.asarray(vertex_normals, float)
    edges, adj = topo if topo is not None else edge_faces(tris)
    C = cam.center
    q = np.einsum("ij,ij->i", Nn, V - C)
    a, b = edges[:, 0], edges[:, 1]
    cross = (q[a] > 0) != (q[b] > 0)
    A, Bv, Cv = V[tris[:, 0]], V[tris[:, 1]], V[tris[:, 2]]
    fn = np.cross(Bv - A, Cv - A)
    front = np.einsum("ij,ij->i", fn, (A + Bv + Cv) / 3.0 - C) < 0
    f0 = front[adj[:, 0]]
    f1 = np.where(adj[:, 1] >= 0, front[np.maximum(adj[:, 1], 0)], False)
    keep = cross & (f0 | f1)
    # triangle -> its three edge ids (edge_faces returns sorted unique edges keyed a * nv + b)
    E = len(edges)
    nv = int(tris.max()) + 1 if len(tris) else 1
    ekey = edges[:, 0] * nv + edges[:, 1]
    order = np.argsort(ekey, kind="stable")
    tri_e = []
    for i, j in ((0, 1), (1, 2), (2, 0)):
        u = np.minimum(tris[:, i], tris[:, j])
        w = np.maximum(tris[:, i], tris[:, j])
        pos = np.searchsorted(ekey[order], u * nv + w)
        tri_e.append(order[np.clip(pos, 0, E - 1)])
    TE = np.stack(tri_e, axis=1)                          # (F, 3) edge ids
    # Keep the rim polyline connected: a q-crossing on an edge whose two faces are both
    # back-facing (vertex-normal q and face-normal facing disagree right at the rim, e.g. on
    # the diagonal of a split quad or along a strip just behind the polyhedral silhouette)
    # is kept when its rim loop reaches a kept crossing: the kept set is grown through
    # triangles with two crossing edges until it stops changing (hidden stretches of a
    # loop are then removed by the raster visibility test).
    two = cross[TE].sum(axis=1) == 2
    for _ in range(len(edges) + 1):
        kc = (keep[TE] & cross[TE]).sum(axis=1)
        link = two & (kc == 1)
        if not link.any():
            break
        add = TE[link][cross[TE[link]]]
        keep[add] = True
    ei = np.flatnonzero(keep)
    ea, eb = a[ei], b[ei]
    t = q[ea] / (q[ea] - q[eb])
    P = V[ea] + t[:, None] * (V[eb] - V[ea])
    n3 = _unit((1.0 - t)[:, None] * Nn[ea] + t[:, None] * Nn[eb])
    uv, z, n2 = _normal2d(cam, P, n3)
    tol = float(CONTOUR["visibility_tol_mm"].value if tol_mm is None else tol_mm)
    vis = _visibility(raster, cam, uv, z, n2, tol, probe_px)
    # segments: triangles with two kept crossing edges
    rim_of_edge = np.full(E, -1, np.int64)
    rim_of_edge[ei] = np.arange(len(ei))
    RE = rim_of_edge[TE]                                  # (F, 3) rim ids or -1
    seg_t = (RE >= 0).sum(axis=1) == 2
    segs = np.sort(RE[seg_t], axis=1)[:, 1:]              # the two valid ids (sorted puts -1 first)
    return RimPoints(p=P, edge=np.column_stack([ea, eb]), t=t, normal2d=n2, visible=vis, uv=uv, depth=z,
                     normal3d=n3, segments=segs.astype(np.int64))


def densify_rim(rim: RimPoints, cam: Camera, spacing_px: float | None = None,
                raster: RasterResult | None = None, *, tol_mm: float | None = None,
                probe_px: float | None = None) -> RimSamples:
    """Rim samples: every rim point plus points along each rim segment every <= ``spacing_px``.

    Segment samples p = (1 - lam) p_i + lam p_j keep their four-vertex weights; their
    normal is the normalised interpolation of the endpoint normals.  Visibility as in
    :func:`rim_points` (recomputed per sample).
    """
    sp = float(CONTOUR["rim_spacing_px"].value if spacing_px is None else spacing_px)
    K = len(rim.t)
    vid0 = np.column_stack([rim.edge[:, 0], rim.edge[:, 1], rim.edge[:, 0], rim.edge[:, 1]])
    w0 = np.column_stack([1.0 - rim.t, rim.t, np.zeros(K), np.zeros(K)])
    vids, ws, Ps, ns = [vid0], [w0], [rim.p], [rim.normal3d]
    S = rim.segments
    if len(S):
        i, j = S[:, 0], S[:, 1]
        L = np.linalg.norm(rim.uv[j] - rim.uv[i], axis=1)
        nseg = np.where(np.isfinite(L), np.ceil(L / sp).astype(np.int64), 1)
        nseg = np.maximum(nseg, 1)
        cnt = nseg - 1                                     # interior samples per segment
        tot = int(cnt.sum())
        if tot:
            sid = np.repeat(np.arange(len(S)), cnt)
            start = np.repeat(np.cumsum(cnt) - cnt, cnt)
            kk = np.arange(tot) - start + 1
            lam = kk / nseg[sid]
            ii, jj = i[sid], j[sid]
            vids.append(np.column_stack([rim.edge[ii, 0], rim.edge[ii, 1], rim.edge[jj, 0], rim.edge[jj, 1]]))
            ws.append(np.column_stack([(1 - lam) * (1 - rim.t[ii]), (1 - lam) * rim.t[ii],
                                       lam * (1 - rim.t[jj]), lam * rim.t[jj]]))
            Ps.append((1 - lam)[:, None] * rim.p[ii] + lam[:, None] * rim.p[jj])
            ns.append(_unit((1 - lam)[:, None] * rim.normal3d[ii] + lam[:, None] * rim.normal3d[jj]))
    vid = np.vstack(vids)
    w = np.vstack(ws)
    P = np.vstack(Ps)
    n3 = np.vstack(ns)
    uv, z, n2 = _normal2d(cam, P, n3)
    tol = float(CONTOUR["visibility_tol_mm"].value if tol_mm is None else tol_mm)
    vis = _visibility(raster, cam, uv, z, n2, tol, probe_px)
    return RimSamples(vid=vid, w=w, p=P, uv=uv, depth=z, normal2d=n2, normal3d=n3, visible=vis)


# =========================================================================== matching
def grid_nearest(query: np.ndarray, ref: np.ndarray, gate_px: float,
                 query_normals: np.ndarray | None = None, ref_normals: np.ndarray | None = None,
                 min_cos: float = -1.0) -> np.ndarray:
    """Nearest ``ref`` point within ``gate_px`` of each ``query`` point via a uniform grid.

    Cell size ``gate_px``; each query visits its 3 x 3 neighbourhood of cells, so the work
    is proportional to the number of candidate pairs (no M x P matrix).  With normals,
    candidates with n_q . n_r < ``min_cos`` are rejected *before* choosing the nearest.
    Returns (P, 2) int64 pairs (query index, ref index), sorted by query index; ties go to
    the lower ref index.
    """
    Q = np.asarray(query, float).reshape(-1, 2)
    Rf = np.asarray(ref, float).reshape(-1, 2)
    g = float(gate_px)
    if len(Q) == 0 or len(Rf) == 0 or not g > 0:
        return np.zeros((0, 2), np.int64)
    okq = np.isfinite(Q).all(axis=1)
    okr = np.flatnonzero(np.isfinite(Rf).all(axis=1))
    if okr.size == 0:
        return np.zeros((0, 2), np.int64)
    cr = np.floor(Rf[okr] / g).astype(np.int64)
    lo = cr.min(axis=0) - 2
    span = cr.max(axis=0) - lo + 3
    key_r = (cr[:, 0] - lo[0]) * span[1] + (cr[:, 1] - lo[1])
    order = np.argsort(key_r, kind="stable")
    ks = key_r[order]
    ref_sorted = okr[order]
    qi = np.flatnonzero(okq)
    cq = np.floor(Q[qi] / g).astype(np.int64) - lo
    qs, rs = [], []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            cx, cy = cq[:, 0] + dx, cq[:, 1] + dy
            inside = (cx >= 0) & (cy >= 0) & (cx < span[0]) & (cy < span[1])
            key = cx * span[1] + cy
            a = np.searchsorted(ks, key, side="left")
            b = np.searchsorted(ks, key, side="right")
            cnt = np.where(inside, b - a, 0)
            tot = int(cnt.sum())
            if tot == 0:
                continue
            rep = np.repeat(np.arange(len(qi)), cnt)
            off = np.arange(tot) - np.repeat(np.cumsum(cnt) - cnt, cnt)
            qs.append(qi[rep])
            rs.append(ref_sorted[np.repeat(a, cnt) + off])
    if not qs:
        return np.zeros((0, 2), np.int64)
    qa = np.concatenate(qs)
    ra = np.concatenate(rs)
    d2 = np.sum((Q[qa] - Rf[ra]) ** 2, axis=1)
    ok = d2 <= g * g
    if query_normals is not None and ref_normals is not None:
        nq = np.asarray(query_normals, float).reshape(-1, 2)
        nr = np.asarray(ref_normals, float).reshape(-1, 2)
        ok &= np.sum(nq[qa] * nr[ra], axis=1) >= float(min_cos)
    qa, ra, d2 = qa[ok], ra[ok], d2[ok]
    if len(qa) == 0:
        return np.zeros((0, 2), np.int64)
    o = np.lexsort((ra, d2, qa))
    qa, ra = qa[o], ra[o]
    first = np.r_[True, qa[1:] != qa[:-1]]
    return np.column_stack([qa[first], ra[first]]).astype(np.int64)


def match(obs: ContourObs, rim_uv: np.ndarray, rim_normal2d: np.ndarray, gate_px: float,
          max_normal_deg: float | None = None) -> np.ndarray:
    """(P, 2) index pairs (obs sample, rim sample): nearest rim sample within ``gate_px`` whose
    normal is within ``max_normal_deg`` (default 40 deg) of the observed one (DESIGN 4.16)."""
    deg = float(CONTOUR["max_normal_deg"].value if max_normal_deg is None else max_normal_deg)
    return grid_nearest(obs.xy, rim_uv, gate_px, obs.normal_out, rim_normal2d, math.cos(math.radians(deg)))


# =========================================================================== residuals
def _forward_core(kind: str, margin_over_sigma: np.ndarray, r: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Residual of a kind from the signed whitened offset r, and d(res)/dr (0 or +-1)."""
    if kind == "hard":
        return r, np.ones_like(r)
    if kind == "outer_bound":
        x = r - margin_over_sigma
        act = x > 0
        return np.where(act, x, 0.0), act.astype(float)
    if kind == "inner_bound":
        x = -r - margin_over_sigma
        act = x > 0
        return np.where(act, x, 0.0), -act.astype(float)
    raise ValueError(f"unknown contour kind {kind!r}")


def forward_residuals(obs: ContourObs, pairs: np.ndarray, rim_uv: np.ndarray) -> np.ndarray:
    """Whitened forward (photo -> model) residuals of matched pairs (DESIGN 4.16).

    r = n_obs . (rim_uv - x) / sigma_n; ``hard`` -> r (Huber is applied by the solver
    schedule), ``outer_bound`` -> max(0, r - margin / sigma), ``inner_bound`` ->
    max(0, -r - margin / sigma).
    """
    pr = np.asarray(pairs, np.int64).reshape(-1, 2)
    i, j = pr[:, 0], pr[:, 1]
    U = np.asarray(rim_uv, float).reshape(-1, 2)
    sig = obs.sigma_n_px[i]
    r = np.sum(obs.normal_out[i] * (U[j] - obs.xy[i]), axis=1) / sig
    res, _ = _forward_core(obs.kind, obs.margin_px / sig, r)
    return res


def tangent_extents(xy: np.ndarray, normals: np.ndarray, chain: np.ndarray | None = None, *,
                    break_factor: float = 4.0, min_break_px: float = 3.0, tol_px: float = 0.5
                    ) -> tuple[np.ndarray, np.ndarray]:
    """Tangential interval [lo_j, hi_j] (px) of the observed contour that sample j stands for.

    Samples are taken in array order within each ``chain`` id (one id per
    :class:`ContourObs`; default one chain): consecutive samples are linked unless the
    step exceeds max(``min_break_px``, ``break_factor`` x the chain's median step) (the
    jump between the traced chains of a mask, or the gap left by dropped samples); a run
    whose last sample is linked to its first by the same rule is closed.  Along the unit
    tangent t_j = (-n_y, n_x) a linked neighbour k at tau = t_j . (x_k - x_j) extends the
    interval to tau / 2 (+- ``tol_px``): sample j covers half the way to each neighbour,
    and nothing beyond an **open end** (lo or hi = 0 there).  Used by
    :class:`ContourDistance` so a point past the end of a partial outline is measured by
    its Euclidean distance, not by the normal offset to the tangent-line extension of the
    last sample (DESIGN 4.16 backward term: truncated Euclidean distance transform).
    """
    P = np.asarray(xy, float).reshape(-1, 2)
    N = _unit(np.asarray(normals, float).reshape(-1, 2))
    M = len(P)
    lo = np.zeros(M)
    hi = np.zeros(M)
    if M < 2:
        return lo, hi
    ch = np.zeros(M, np.int64) if chain is None else np.asarray(chain).reshape(M)
    Tg = np.column_stack([-N[:, 1], N[:, 0]])
    step = np.linalg.norm(P[1:] - P[:-1], axis=1)
    same = ch[1:] == ch[:-1]
    thr = np.full(M, float(min_break_px))
    for c in np.unique(ch):
        sc = step[same & (ch[:-1] == c)]
        if sc.size:
            thr[ch == c] = max(float(min_break_px), float(break_factor) * float(np.median(sc)))
    link = same & (step <= thr[:-1])
    a_l = list(np.flatnonzero(link))
    b_l = [i + 1 for i in a_l]
    # closed runs: the last sample of a run linked back to its first
    starts = np.flatnonzero(np.r_[True, ~link])
    ends = np.r_[starts[1:] - 1, M - 1]
    for s0, e0 in zip(starts.tolist(), ends.tolist()):
        if e0 - s0 >= 2 and ch[s0] == ch[e0] and np.linalg.norm(P[e0] - P[s0]) <= thr[s0]:
            a_l.append(e0)
            b_l.append(s0)
    if not a_l:
        return lo, hi
    a = np.asarray(a_l, np.int64)
    b = np.asarray(b_l, np.int64)
    tol = float(tol_px)
    for i, k in ((a, b), (b, a)):
        tau = np.sum(Tg[i] * (P[k] - P[i]), axis=1)
        end = 0.5 * tau + np.sign(tau) * tol
        np.minimum.at(lo, i, np.minimum(end, 0.0))
        np.maximum.at(hi, i, np.maximum(end, 0.0))
    return lo, hi


class ContourDistance:
    """Distance field of an observed contour on a cropped pixel grid (backward term).

    Built from samples ``xy`` (M, 2) and their normals: every grid cell containing a
    sample is marked; d = sqrt(EDT) (exact, :func:`~face3d.fit.distance_transform.edt_with_nearest`)
    with the nearest marked cell's sample kept.  ``sample(uv)`` returns (distance px,
    d distance / d uv (n, 2), inside-grid mask).  Points off the grid get +inf (callers
    truncate).  The grid covers the samples' bounding box plus ``pad`` pixels.

    ``mode='normal'`` (default) refines the distance for the nearest sample j: with
    s = n_j . (uv - x_j) and the tangential excess e = distance of t_j . (uv - x_j) outside
    the sample's interval [lo_j, hi_j] (:func:`tangent_extents`, ``chain`` ids keep
    separate outlines apart), d = sqrt(s^2 + e^2) - the distance to the short tangent
    segment the sample stands for.  On the contour's span e = 0 and d = |s| (sub-pixel;
    exact for a straight contour); **past an open end** d grows like the Euclidean
    distance, so the 3-sigma truncation caps it with zero gradient, as the spec's
    truncated sqrt-EDT does.  ``'edt'`` interpolates sqrt(EDT) bilinearly.
    """

    def __init__(self, xy: np.ndarray, normals: np.ndarray, pad: float = 64.0, mode: str = "normal",
                 chain: np.ndarray | None = None):
        P = np.asarray(xy, float).reshape(-1, 2)
        self.xy = P
        self.normals = _unit(np.asarray(normals, float).reshape(-1, 2))
        if mode not in ("normal", "edt"):
            raise ValueError("mode must be 'normal' or 'edt'")
        self.mode = mode
        self.tangents = np.column_stack([-self.normals[:, 1], self.normals[:, 0]]) if len(P) else np.zeros((0, 2))
        self.lo, self.hi = tangent_extents(P, self.normals, chain)
        if len(P) == 0:
            self.origin = np.zeros(2, np.int64)
            self.d = np.full((1, 1), np.inf)
            self.owner = np.full((1, 1), -1, np.int64)
            return
        pad_i = int(math.ceil(max(float(pad), 1.0)))
        lo = np.floor(P.min(axis=0)).astype(np.int64) - pad_i
        hi = np.floor(P.max(axis=0)).astype(np.int64) + pad_i + 1
        self.origin = lo                                   # (u0, v0) integer pixel of grid cell [0, 0]
        Wd, Hd = int(hi[0] - lo[0]), int(hi[1] - lo[1])
        cell = np.floor(P).astype(np.int64) - lo
        mask = np.zeros((Hd, Wd), bool)
        owner_cell = np.full((Hd, Wd), -1, np.int64)
        mask[cell[:, 1], cell[:, 0]] = True
        owner_cell[cell[:, 1], cell[:, 0]] = np.arange(len(P))     # last sample in a cell wins
        d2, near = edt_with_nearest(mask)
        self.d = np.sqrt(d2)
        own = np.full((Hd, Wd), -1, np.int64)
        okn = near[..., 0] >= 0
        own[okn] = owner_cell[near[okn, 0], near[okn, 1]]
        self.owner = own

    def nearest(self, uv: np.ndarray) -> np.ndarray:
        """Index of the observed sample owning the nearest marked cell of each point (-1 off-grid)."""
        U = np.asarray(uv, float).reshape(-1, 2)
        Hd, Wd = self.d.shape
        loc = U - self.origin
        inside = (np.isfinite(loc).all(axis=1) & (loc[:, 0] >= 0) & (loc[:, 1] >= 0)
                  & (loc[:, 0] < Wd) & (loc[:, 1] < Hd))
        out = np.full(len(U), -1, np.int64)
        if inside.any():
            ci = np.floor(loc[inside]).astype(np.int64)
            out[inside] = self.owner[ci[:, 1], ci[:, 0]]
        return out

    def project(self, uv: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """(j, s, e, tsign) per point: the nearest sample j (-1 off-grid), the signed normal
        offset s = n_j . (uv - x_j), the tangential excess e >= 0 outside [lo_j, hi_j] and its
        side (+1 past hi, -1 past lo, 0 inside).  Off-grid points get s = e = inf."""
        U = np.asarray(uv, float).reshape(-1, 2)
        j = self.nearest(U)
        s = np.full(len(U), np.inf)
        e = np.full(len(U), np.inf)
        sg = np.zeros(len(U))
        ok = np.flatnonzero(j >= 0)
        if ok.size:
            jj = j[ok]
            dv = U[ok] - self.xy[jj]
            s[ok] = np.sum(self.normals[jj] * dv, axis=1)
            tau = np.sum(self.tangents[jj] * dv, axis=1)
            over, under = tau - self.hi[jj], self.lo[jj] - tau
            e[ok] = np.maximum(0.0, np.maximum(over, under))
            sg[ok] = np.where(over > 0, 1.0, np.where(under > 0, -1.0, 0.0))
        return j, s, e, sg

    def sample(self, uv: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        U = np.asarray(uv, float).reshape(-1, 2)
        Hd, Wd = self.d.shape
        loc = U - self.origin
        inside = (np.isfinite(loc).all(axis=1) & (loc[:, 0] >= 0) & (loc[:, 1] >= 0)
                  & (loc[:, 0] < Wd) & (loc[:, 1] < Hd))
        dist = np.full(len(U), np.inf)
        grad = np.zeros((len(U), 2))
        if not inside.any():
            return dist, grad, inside
        li = loc[inside]
        if self.mode == "edt":
            val, g = sample_bilinear(self.d, li, return_grad=True)
            dist[inside] = val
            grad[inside] = g
            return dist, grad, inside
        j, s, e, sg = self.project(U)
        idx = np.flatnonzero(inside & (j >= 0))
        jj = j[idx]
        d = np.hypot(s[idx], e[idx])
        dist[idx] = d
        nz = d > 0
        g = np.zeros((len(idx), 2))
        g[nz] = (s[idx][nz, None] * self.normals[jj[nz]]
                 + (sg[idx] * e[idx])[nz, None] * self.tangents[jj[nz]]) / d[nz, None]
        grad[idx] = g
        return dist, grad, inside


def backward_residuals(edt_obs_view: Any, rim_uv: np.ndarray, sigma_px: float, trunc: float | None = None,
                       weight: float | None = None, return_grad: bool = False):
    """Backward (model -> photo) residuals of rim samples (DESIGN 4.16).

    r = sqrt(weight) min(D(rim_uv), trunc sigma) / sigma with D the observed contour's
    distance: a (H, W) sqrt-EDT array of the full image (bilinear, pixel-centre
    convention) or a :class:`ContourDistance`.  Defaults trunc 3, weight 0.5 (so the
    cost is 0.5 (D / sigma)^2 per sample).  Off-grid samples are truncated.  With
    ``return_grad`` also returns dr/duv (n, 2) (zero where truncated).
    """
    T = float(CONTOUR["backward_trunc"].value if trunc is None else trunc)
    wgt = float(CONTOUR["backward_weight"].value if weight is None else weight)
    U = np.asarray(rim_uv, float).reshape(-1, 2)
    sig = float(sigma_px)
    if isinstance(edt_obs_view, ContourDistance):
        D, G, _ = edt_obs_view.sample(U)
    else:
        arr = np.asarray(edt_obs_view, float)
        D, G = sample_bilinear(arr, U, fill=np.inf, return_grad=True)
        D = np.where(np.isfinite(D), D, np.inf)
    cap = T * sig
    act = D < cap
    sw = math.sqrt(wgt)
    r = sw * np.where(act, D, cap) / sig
    if not return_grad:
        return r
    return r, np.where(act[:, None], G * (sw / sig), 0.0)


def sigma_n_model(sigma_edge_px: float, model_edge_len_px: float, blur_px: float, iod_px: float) -> float:
    """Normal sigma of a contour sample, px (DESIGN 4.16 'Noise'; face-segmentation-contours).

    max(sqrt(sigma_edge^2 + (0.5 s)^2 + blur^2), 0.005 iod_px), with ``model_edge_len_px``
    = s, the size in full-resolution pixels of one cell of the contour's source (a
    segmentation-mask pixel upsampled to the photo, the research note's "s_model in
    full-res px per model px"; 1 for a full-resolution mask, 0 for an analytic curve).
    """
    s = math.sqrt(float(sigma_edge_px) ** 2 + (0.5 * float(model_edge_len_px)) ** 2 + float(blur_px) ** 2)
    return max(s, float(CONTOUR["sigma_floor_iod"].value) * float(iod_px))


def effective_sample_weights(M: int, cap: float | None = None) -> float:
    """Per-sample weight min(1, cap / M) so a view carries at most ``cap`` (40) effective samples."""
    c = float(CONTOUR["effective_cap"].value if cap is None else cap)
    return 1.0 if M <= 0 else min(1.0, c / float(M))


def _subsample(n: int, m: int) -> np.ndarray:
    """Deterministic evenly spaced subset of range(n) of size min(n, m)."""
    if n <= m:
        return np.arange(n)
    return np.unique(np.floor(np.arange(m) * (n / float(m))).astype(np.int64))


# =========================================================================== the Term
@dataclass
class _Block:
    """Frozen rows of one view (forward or backward) for one outer iteration."""

    view: int
    kind: str                     # 'hard' | 'outer_bound' | 'inner_bound' | 'backward'
    pbar: np.ndarray              # (m, 3) rest part of the sample position
    phi: np.ndarray               # (m, K) basis weights of the sample position
    sw: np.ndarray                # (m,) sqrt of the row weights (sample, kind, Huber)
    x: np.ndarray | None = None   # (m, 2) observed points (forward)
    n: np.ndarray | None = None   # (m, 2) observed outward normals (forward)
    sig: np.ndarray | None = None  # (m,) sigma_n px (forward) / scalar sigma (backward)
    margin: np.ndarray | None = None  # (m,) margin / sigma (forward bound kinds)
    obs_idx: np.ndarray | None = None  # (m,) observed sample index into the view's merged arrays


class ContourTerm:
    """Contour residuals as a bundle :class:`~face3d.solve.terms.Term` (DESIGN 4.16; WBS WP-17).

    Holds the :class:`ContourObs` of every view, a :class:`~face3d.solve.shape_models.LinearBasis`
    with coefficient rows (``basis.with_coefficient_rows()``), and per-view distance
    fields of the 'hard' observations for the backward term.  :meth:`update` (call once
    per outer iteration, before the bundle run) recomputes the visible sub-vertex rim of
    V(c) under the current cameras, matches it with the iteration's gate, and freezes the
    pairs, the rim samples' vertex weights and the Huber IRLS weights.  Within the bundle
    the residuals are

    * forward: sqrt(w) res_kind(n_obs . (pi(p) - x) / sigma), w = (effective-sample weight)
      x (kind weight: outer_bound x10) x (Huber weight min(1, delta / |r|) for 'hard',
      frozen), p = p_bar + phi W(c) (frozen four-vertex weights);
    * backward (if enabled): sqrt(0.5 w_s) clip(n_j . (pi(p) - x_j) / sigma, -3, 3) over the
      visible rim samples whose **Euclidean** distance to the observed hard contour
      (:meth:`ContourDistance.project`) is within the gate and which project onto the
      contour's span (tangential excess <= ``backward_end_px``, 1 px): a rim sample past
      the end of a partial outline (pins, lasso, a snapped jaw line) has no row, as the
      truncated EDT term is constant there; j is the observed sample nearest to the rim
      sample by the contour's EDT (frozen per outer iteration; see the module docstring),
      sigma the view's median hard sigma_n.

    Effective samples (DESIGN 4.16 'Noise'): one budget of ``cap`` (40) per view, shared
    by the forward kinds and the backward rows in proportion to their candidate counts
    (each candidate weighs min(1, cap / total)); rows evenly subsampled to
    ``max_rows_per_view`` carry the weight of the candidates they stand for.

    The Jacobian is dr/dp (frozen t) x dp/dc (basis rows) x Pi in the 'X' block (the
    basis' coefficient rows) plus the camera block 'cam:<v>' in inverse-depth form (and the
    focal-group parameter of a HARD view, named by ``phi_keys[v]``).

    Parameters: ``obs`` list of ContourObs; ``basis``; ``iod_px`` per view (sequence or
    dict; gates and the sigma floor) - the inter-ocular distance at the face's depth in
    px, f IOD_mm / z, not the projected eye distance (which vanishes in a profile);
    ``n_outer`` (gate schedule length); ``vertex_mask`` (V,) bool restricting rim samples
    to vertices that the outlines describe; ``phi_keys`` {view: 'phi_<j>'} for views in a
    HARD focal group (the focal parameter is shared, its Jacobian block is named by the
    group); ``max_rows_per_view`` caps the rows per view and direction (evenly subsampled,
    the per-row weight keeps min(M, cap) effective samples).
    """

    is_prior = False

    def __init__(self, obs: Sequence[ContourObs], basis: Any, iod_px: Any, *, name: str = "contour",
                 n_outer: int = 5, gate_iod_frac: float | None = None, gate_final_sigma: float | None = None,
                 max_normal_deg: float | None = None, backward: bool = True, backward_trunc: float | None = None,
                 backward_weight: float | None = None, cap: float | None = None, huber_delta: float | None = None,
                 kind_weights: dict | None = None, spacing_px: float | None = None,
                 max_rows_per_view: int | None = None, vertex_mask: np.ndarray | None = None,
                 phi_keys: dict | None = None, backward_end_px: float | None = None):
        if not getattr(basis, "expose_coefficients", False):
            raise ValueError("ContourTerm needs a LinearBasis with coefficient rows (with_coefficient_rows())")
        self.name = str(name)
        self.basis = basis
        self.obs = list(obs)
        self.views = sorted({o.view for o in self.obs})
        self.iod = {v: float(iod_px[v]) for v in self.views}
        self.n_outer = max(1, int(n_outer))
        self.gate_iod_frac = float(CONTOUR["gate_iod_frac"].value if gate_iod_frac is None else gate_iod_frac)
        self.gate_final_sigma = float(CONTOUR["gate_final_sigma"].value if gate_final_sigma is None
                                      else gate_final_sigma)
        self.max_normal_deg = float(CONTOUR["max_normal_deg"].value if max_normal_deg is None else max_normal_deg)
        self.backward = bool(backward)
        self.trunc = float(CONTOUR["backward_trunc"].value if backward_trunc is None else backward_trunc)
        self.bweight = float(CONTOUR["backward_weight"].value if backward_weight is None else backward_weight)
        self.cap = float(CONTOUR["effective_cap"].value if cap is None else cap)
        self.delta = float(CONTOUR["huber_delta"].value if huber_delta is None else huber_delta)
        self.kind_w = {"hard": 1.0, "outer_bound": float(CONTOUR["outer_bound_weight"].value), "inner_bound": 1.0}
        if kind_weights:
            self.kind_w.update({str(k): float(v) for k, v in kind_weights.items()})
        self.spacing = float(CONTOUR["rim_spacing_px"].value if spacing_px is None else spacing_px)
        self.max_rows = int(CONTOUR["max_rows_per_view"].value if max_rows_per_view is None else max_rows_per_view)
        self.vertex_mask = None if vertex_mask is None else np.asarray(vertex_mask, bool).reshape(-1)
        self.phi_keys = dict(phi_keys or {})
        self.tris = np.asarray(basis.tris, np.int64)
        self.topo = edge_faces(self.tris)
        # merged per-view observation arrays (+ the backward distance field of the hard samples)
        self._vobs = _merge_obs(self.obs, self.iod)
        self.end_px = float(CONTOUR["backward_end_px"].value if backward_end_px is None else backward_end_px)
        for v in self.views:
            ob = self._vobs[v]
            hard = ob["kind"] == 0
            sig_b = float(np.median(ob["sig"][hard])) if hard.any() else ob["sig_med"]
            dist = None
            if self.backward and hard.any():
                pad = self.gate_iod_frac * self.iod[v] + self.trunc * sig_b + 4.0
                dist = ContourDistance(ob["xy"][hard], ob["n"][hard], pad=pad, chain=ob["chain"][hard])
            ob["sig_b"] = sig_b
            ob["dist"] = dist
        self._blocks: list[_Block] = []
        self._cxy: dict[int, np.ndarray] = {}
        self.iteration = -1
        self.gates: dict[int, float] = {}
        self.last_stats: dict[int, dict] = {}

    # ------------------------------------------------------------------ protocol
    def n_params(self) -> int:
        return 0

    def init_params(self, state: Any) -> np.ndarray:
        return np.zeros(0)

    @property
    def n_rows(self) -> int:
        return int(sum(len(b.sw) for b in self._blocks))

    # ------------------------------------------------------------------ schedule
    def gate_px(self, view: int, iteration: int) -> float:
        """Gate of ``view`` at outer ``iteration``: 0.15 IOD_px shrinking geometrically to
        5 median(sigma_n) at iteration n_outer - 1 (DESIGN 4.16 "Matching")."""
        g0 = self.gate_iod_frac * self.iod[view]
        g1 = min(self.gate_final_sigma * self._vobs[view]["sig_med"], g0)
        k = min(max(int(iteration), 0), self.n_outer - 1)
        if self.n_outer == 1 or g0 <= 0 or g1 <= 0:
            return float(g0)
        return float(g0 * (g1 / g0) ** (k / (self.n_outer - 1)))

    def rim_samples(self, V: np.ndarray, cam: Camera, raster: RasterResult | None = None,
                    normals: np.ndarray | None = None) -> RimSamples:
        """Visible rim samples of V under ``cam`` (vertex mask applied)."""
        nrm = vertex_normals(V, self.tris) if normals is None else normals
        return _rim_samples(np.asarray(V, float), self.tris, self.topo, cam, raster, nrm, self.spacing,
                            self.vertex_mask)

    def update(self, V: np.ndarray, cameras: Sequence[Camera], iteration: int,
               rasters: dict | None = None) -> None:
        """Recompute rims, match with the iteration's gate and freeze the rows (one outer iteration).

        V : (V, 3) current vertices (= basis.vertices_q(q)); cameras : per bundle view;
        rasters : optional {view: RasterResult} for the visibility test (any resolution).
        """
        V = np.asarray(V, float)
        nrm = vertex_normals(V, self.tris)
        Vbar = self.basis.V_bar
        self.iteration = int(iteration)
        blocks: list[_Block] = []
        self.gates = {}
        for v in self.views:
            cam = cameras[v]
            self._cxy[v] = np.array([cam.cx, cam.cy], float)
            ras = None if rasters is None else rasters.get(v)
            smp = self.rim_samples(V, cam, ras, nrm)
            ob = self._vobs[v]
            gate = self.gate_px(v, iteration)
            self.gates[v] = gate
            pairs = grid_nearest(ob["xy"], smp.uv, gate, ob["n"], smp.normal2d,
                                 math.cos(math.radians(self.max_normal_deg)))
            groups: list[tuple[str, np.ndarray]] = []
            if len(pairs):
                kinds = ob["kind"][pairs[:, 0]]
                for kc, kname in enumerate(KINDS):
                    sel = np.flatnonzero(kinds == kc)
                    if sel.size:
                        groups.append((kname, sel))
            near = np.zeros(0, np.int64)
            jn = np.zeros(0, np.int64)
            if self.backward and ob["dist"] is not None and len(smp):
                dist = ob["dist"]
                jn, s_off, exc, _ = dist.project(smp.uv)
                # Euclidean gate on the distance to the observed contour; rim samples that do not
                # project onto its span (past an open end by > end_px) carry no backward row (the
                # truncated EDT term would be constant there, DESIGN 4.16)
                d_e = np.hypot(s_off, exc)
                near = np.flatnonzero((jn >= 0) & np.isfinite(d_e) & (d_e <= gate) & (exc <= self.end_px))
            # one budget of `cap` effective samples per view, shared by the kinds and the backward
            # rows in proportion to their counts (DESIGN 4.16 'Noise': at most 40 per view)
            total = sum(len(sel) for _, sel in groups) + len(near)
            share = min(1.0, self.cap / float(total)) if total else 1.0
            if groups:
                i, j = pairs[:, 0], pairs[:, 1]
                sig = ob["sig"][i]
                r0 = np.sum(ob["n"][i] * (smp.uv[j] - ob["xy"][i]), axis=1) / sig
                for kname, sel in groups:
                    sub = sel[_subsample(len(sel), self.max_rows)]
                    w_s = share * float(len(sel)) / float(len(sub))
                    w = np.full(len(sub), w_s * self.kind_w[kname])
                    if kname == "hard":
                        a = np.abs(r0[sub])
                        w *= np.where(a > self.delta, self.delta / np.maximum(a, 1e-300), 1.0)
                    jj = j[sub]
                    blocks.append(_Block(v, kname, *self._support(smp, jj, Vbar), np.sqrt(w),
                                         x=ob["xy"][i[sub]], n=ob["n"][i[sub]], sig=sig[sub],
                                         margin=ob["margin"][i[sub]] / sig[sub], obs_idx=i[sub]))
            if near.size:
                dist = ob["dist"]
                sub = near[_subsample(len(near), self.max_rows)]
                w_s = share * float(len(near)) / float(len(sub))
                js = jn[sub]
                blocks.append(_Block(v, "backward", *self._support(smp, sub, Vbar),
                                     np.full(len(sub), math.sqrt(w_s * self.bweight)),
                                     x=dist.xy[js], n=dist.normals[js], sig=np.full(len(sub), ob["sig_b"]),
                                     obs_idx=js))
        self._blocks = blocks

    def _support(self, smp: RimSamples, idx: np.ndarray, Vbar: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        vid, w = smp.vid[idx], smp.w[idx]
        pbar = np.einsum("nk,nkd->nd", w, Vbar[vid])
        rows, inv = np.unique(vid.ravel(), return_inverse=True)
        Phi = self.basis.deformer.basis_rows(rows)
        phi = np.einsum("nk,nkj->nj", w, Phi[inv.reshape(vid.shape)])
        return pbar, phi

    # ------------------------------------------------------------------ evaluation
    def _project(self, v: int, inv: dict, P: np.ndarray):
        R, tau, rho, s = inv["R"], inv["tau"], float(inv["rho"]), float(inv["s"])
        Y = P @ R.T
        den = 1.0 + rho * Y[:, 2]
        qv = Y[:, :2] + tau
        g = s / den
        d = qv * g[:, None]
        uv = d + self._cxy[v]
        return uv, Y, den, qv, g, d

    def _eval(self, state: Any, jac: bool):
        b = self.basis
        X = np.asarray(state.X, float)
        qv_ = b.coef_from_points(X)
        W = coef_matrix(b.coefficients(qv_), b.K)
        res, jac_X, jac_cam = [], [], []
        for blk in self._blocks:
            inv = state.invdepth[blk.view]
            P = blk.pbar + blk.phi @ W
            uv, Y, den, qv, g, d = self._project(blk.view, inv, P)
            if blk.kind == "backward":
                r0 = np.sum(blk.n * (uv - blk.x), axis=1) / blk.sig
                act = np.abs(r0) < self.trunc
                r = np.clip(r0, -self.trunc, self.trunc)
                druv = blk.n * (act / blk.sig)[:, None]
            else:
                r0 = np.sum(blk.n * (uv - blk.x), axis=1) / blk.sig
                r, dr = _forward_core(blk.kind, blk.margin, r0)
                druv = blk.n * (dr / blk.sig)[:, None]
            r = r * blk.sw
            druv = druv * blk.sw[:, None]
            res.append(r)
            if not jac:
                continue
            rho = float(inv["rho"])
            # d r / d Y via du/dY = g [[1, 0, -rho q_x / den], [0, 1, -rho q_y / den]]
            gY = np.empty((len(r), 3))
            gY[:, 0] = druv[:, 0] * g
            gY[:, 1] = druv[:, 1] * g
            gY[:, 2] = -(druv[:, 0] * qv[:, 0] + druv[:, 1] * qv[:, 1]) * g * rho / den
            gP = gY @ inv["R"]
            jac_X.append((gP, blk.phi))
            block = inv["block"]
            Jc = np.zeros((len(r), len(block)))
            Jc[:, 0:3] = np.cross(Y, gY)                       # left increment: dY = domega x Y
            Jc[:, 3:5] = druv * g[:, None]
            dd = np.sum(druv * d, axis=1)                      # dr/du . (u - c)
            if inv["kind"] == "free":
                Jc[:, 5] = -dd * Y[:, 2] / den * 1e-3
                Jc[:, 6] = dd
            else:
                Jc[:, 5] = dd / (rho * den) * 1e-3
            jac_cam.append((blk.view, Jc, dd if inv["kind"] == "hard" else None))
        r = np.concatenate(res) if res else np.zeros(0)
        if not jac:
            return r, None
        m = len(r)
        K = b.K
        dc = np.zeros((m, 3 * K))
        row = 0
        for gP, phi in jac_X:
            n = len(gP)
            for dd_ in range(3):
                dc[row:row + n, dd_ * K:(dd_ + 1) * K] = gP[:, dd_:dd_ + 1] * phi
            row += n
        dq = dc @ b.Pi
        n_pts = len(X)
        JX = np.zeros((m, 3 * n_pts))
        jdx = np.arange(K)
        off = b.coef_offset
        for dd_ in range(3):
            JX[:, 3 * (off + jdx) + dd_] = dq[:, dd_ * K + jdx]
        out: dict[str, np.ndarray] = {"X": JX}
        row = 0
        for (v, Jc, dphi), blk in zip(jac_cam, self._blocks):
            n = len(blk.sw)
            key = f"cam:{v}"
            if key not in out:
                out[key] = np.zeros((m, Jc.shape[1]))
            out[key][row:row + n] = Jc
            if dphi is not None:
                pk = self.phi_keys.get(v)
                if pk is None:
                    raise ValueError(f"view {v} is a HARD focal-group view: pass phi_keys={{{v}: 'phi_<j>'}}")
                if pk not in out:
                    out[pk] = np.zeros((m, 1))
                out[pk][row:row + n, 0] = dphi
            row += n
        return r, out

    def residuals(self, state: Any, p: np.ndarray) -> np.ndarray:
        return self._eval(state, False)[0]

    def jacobian(self, state: Any, p: np.ndarray) -> dict:
        return self._eval(state, True)[1]

    # ------------------------------------------------------------------ diagnostics
    def view_stats(self, V: np.ndarray, cameras: Sequence[Camera], rasters: dict | None = None,
                   gate_px: dict | None = None) -> dict:
        """Per view contour statistics of V under ``cameras`` (:func:`contour_view_stats`) at the
        final gate of the schedule (``gate_px`` overrides) and at the wide 0.15 IOD_px gate."""
        gates = {v: (gate_px or {}).get(v, self.gate_px(v, self.n_outer - 1)) for v in self.views}
        wide = {v: self.gate_iod_frac * self.iod[v] for v in self.views}
        out = _stats(V, self.tris, self.topo, self._vobs, cameras, rasters, gates, wide, self.max_normal_deg,
                     self.spacing, self.vertex_mask)
        self.last_stats = out
        return out


def _rim_samples(V: np.ndarray, tris: np.ndarray, topo: Any, cam: Camera, raster: RasterResult | None,
                 normals: np.ndarray, spacing: float, vertex_mask: np.ndarray | None) -> RimSamples:
    rim = rim_points(V, tris, normals, cam, raster, topo=topo)
    smp = densify_rim(rim, cam, spacing, raster)
    keep = smp.visible.copy()
    if vertex_mask is not None:
        keep &= np.all(vertex_mask[smp.vid] | (smp.w <= 0), axis=1)
    return RimSamples(*(getattr(smp, f)[keep] for f in ("vid", "w", "p", "uv", "depth", "normal2d",
                                                         "normal3d", "visible")))


def _merge_obs(obs: Sequence[ContourObs], iod: dict) -> dict:
    """Per view merged observation arrays (sigma floored at 0.005 IOD_px)."""
    floor = float(CONTOUR["sigma_floor_iod"].value)
    out = {}
    for v in sorted({o.view for o in obs}):
        ol = [o for o in obs if o.view == v]
        out[v] = dict(xy=np.vstack([o.xy for o in ol]), n=np.vstack([o.normal_out for o in ol]),
                      sig=np.concatenate([np.maximum(o.sigma_n_px, floor * iod[v]) for o in ol]),
                      kind=np.concatenate([np.full(o.M, KINDS.index(o.kind)) for o in ol]),
                      margin=np.concatenate([np.full(o.M, o.margin_px) for o in ol]),
                      chain=np.concatenate([np.full(o.M, k) for k, o in enumerate(ol)]))
        out[v]["sig_med"] = float(np.median(out[v]["sig"]))
    return out


def _view_kind(view: Any) -> str:
    """Bundle camera kind of a ViewObs: 'fixed_f', 'hard' (shared focal) or 'free' (WP-10 layout)."""
    if not getattr(view, "estimate_focal", True):
        return "fixed_f"
    if getattr(view, "focal_group", None) is not None and getattr(view, "focal_tie_sigma", None) is None:
        return "hard"
    return "free"


def pose_uv_jacobian(cam: Camera, P: np.ndarray, kind: str = "free") -> np.ndarray:
    """d uv / d (bundle camera block) at points P (n, 3): (n, 2, k) (WBS WP-10 parameterisation).

    Columns: omega (3, left rotation increment R <- exp([omega]x) R), tau (2, mm), rho
    (1, stored in 1/m), then a = ln s for 'free' or phi = ln f for 'hard'; 'fixed_f' has the
    six pose columns only (s = f rho).  The order of ``BundleResult.camera_cov``.
    """
    from ..geometry.camera import camera_to_invdepth

    d = camera_to_invdepth(cam)
    R, tau, s, rho = d["R"], d["tau"], float(d["s"]), float(d["rho"])
    P = np.asarray(P, float).reshape(-1, 3)
    Y = P @ R.T
    den = 1.0 + rho * Y[:, 2]
    q = Y[:, :2] + tau
    g = s / den
    uc = q * g[:, None]                                    # uv - principal point
    dY = np.zeros((len(P), 2, 3))
    dY[:, 0, 0] = g
    dY[:, 1, 1] = g
    dY[:, :, 2] = -(uc * (rho / den)[:, None])
    ncol = 6 if kind == "fixed_f" else 7
    J = np.zeros((len(P), 2, ncol))
    eye = np.eye(3)
    for k in range(3):
        J[:, :, k] = np.einsum("nij,nj->ni", dY, np.cross(eye[k], Y))
    J[:, 0, 3] = g
    J[:, 1, 4] = g
    if kind == "free":
        J[:, :, 5] = -uc * (Y[:, 2] / den)[:, None] * 1e-3
        J[:, :, 6] = uc
    else:
        J[:, :, 5] = uc / (rho * den)[:, None] * 1e-3
        if kind == "hard":
            J[:, :, 6] = uc
    return J


def _pose_var(cam: Camera, cov: np.ndarray, kind: str, P: np.ndarray, n2: np.ndarray) -> np.ndarray:
    """Variance (px^2) of n2 . uv(P) under the camera covariance ``cov`` (bundle camera_cov)."""
    J = pose_uv_jacobian(cam, P, kind)
    C = np.asarray(cov, float)
    k = J.shape[2]
    if C.shape[0] < k:
        raise ValueError(f"camera covariance {C.shape} too small for a {kind!r} view ({k} parameters)")
    a = np.einsum("ni,nik->nk", np.asarray(n2, float), J)
    return np.maximum(np.einsum("nk,kl,nl->n", a, C[:k, :k], a), 0.0)


def _stats(V: np.ndarray, tris: np.ndarray, topo: Any, vobs: dict, cameras: Sequence[Camera], rasters: dict | None,
           gates: dict, wide_gates: dict, max_normal_deg: float, spacing: float,
           vertex_mask: np.ndarray | None, pose: dict | None = None) -> dict:
    V = np.asarray(V, float)
    nrm = vertex_normals(V, tris)
    cmin = math.cos(math.radians(max_normal_deg))
    out = {}
    for v, ob in vobs.items():
        smp = _rim_samples(V, tris, topo, cameras[v], None if rasters is None else rasters.get(v), nrm, spacing,
                           vertex_mask)
        stats = {"n_obs": int(len(ob["xy"])), "n_rim": int(len(smp)), "gate_px": float(gates[v]),
                 "sigma_n_px": float(ob["sig_med"])}
        pv = None if pose is None else pose.get(v)
        for tag, g in (("", gates[v]), ("wide_", wide_gates[v])):
            pr = grid_nearest(ob["xy"], smp.uv, g, ob["n"], smp.normal2d, cmin)
            stats[tag + "n_pairs"] = int(len(pr))
            if len(pr):
                i, j = pr[:, 0], pr[:, 1]
                off = np.sum(ob["n"][i] * (smp.uv[j] - ob["xy"][i]), axis=1)
                sig = ob["sig"][i]
                if pv is not None:
                    pvar = _pose_var(cameras[v], pv[0], pv[1], smp.p[j], ob["n"][i])
                    stats[tag + "pose_sigma_px"] = float(np.median(np.sqrt(pvar)))
                    sig = np.sqrt(sig ** 2 + pvar)
                r = off / sig
                rk = np.empty_like(r)
                for kc, kname in enumerate(KINDS):
                    sel = ob["kind"][i] == kc
                    rk[sel] = _forward_core(kname, ob["margin"][i][sel] / sig[sel], r[sel])[0]
                stats[tag + "median_abs_sigma"] = float(np.median(np.abs(rk)))
                stats[tag + "median_signed_sigma"] = float(np.median(r))
                stats[tag + "rms_px"] = float(np.sqrt(np.mean(off ** 2)))
                stats[tag + "coverage"] = float(len(np.unique(i)) / max(len(ob["xy"]), 1))
            else:
                stats[tag + "median_abs_sigma"] = float("inf")
                stats[tag + "median_signed_sigma"] = float("nan")
                stats[tag + "rms_px"] = float("inf")
                stats[tag + "coverage"] = 0.0
        out[v] = stats
    return out


def contour_view_stats(V: np.ndarray, tris: np.ndarray, obs: Sequence[ContourObs], cameras: Sequence[Camera],
                       iod_px: Any, rasters: dict | None = None, gate_px: dict | None = None, *,
                       max_normal_deg: float | None = None, spacing_px: float | None = None,
                       vertex_mask: np.ndarray | None = None, pose_cov: dict | None = None) -> dict:
    """Per view contour residual statistics of mesh (V, tris) under ``cameras`` (no basis needed).

    For every view with observations: rim samples (visible with ``rasters``), forward pairs
    at ``gate_px[v]`` (default 5 median sigma_n, the end of the gate schedule) and at the
    wide gate 0.15 IOD_px (``wide_*`` keys, so a badly fitting view is not hidden by a small
    gate): ``median_abs_sigma`` (kind-aware |r| in sigma units; the SIL-3 statistic),
    ``median_signed_sigma``, ``rms_px`` (normal offsets), ``coverage`` (fraction of
    observed samples matched), ``n_pairs``, ``n_obs``, ``n_rim``, ``sigma_n_px`` (median).
    ``pose_cov`` {view: (camera_cov, kind)} (a bundle's ``camera_cov`` and
    :func:`pose_uv_jacobian` kind) inflates each pair's sigma to
    sqrt(sigma_n^2 + n^T J Sigma_cam J^T n), the camera's own uncertainty projected on the
    observed normal (``pose_sigma_px``: its median).
    """
    views = sorted({o.view for o in obs})
    iod = {v: float(iod_px[v]) for v in views}
    vobs = _merge_obs(obs, iod)
    gf = float(CONTOUR["gate_final_sigma"].value)
    gi = float(CONTOUR["gate_iod_frac"].value)
    gates = {v: (gate_px or {}).get(v, min(gf * vobs[v]["sig_med"], gi * iod[v])) for v in views}
    wide = {v: gi * iod[v] for v in views}
    tris = np.asarray(tris, np.int64)
    deg = float(CONTOUR["max_normal_deg"].value if max_normal_deg is None else max_normal_deg)
    sp = float(CONTOUR["rim_spacing_px"].value if spacing_px is None else spacing_px)
    vm = None if vertex_mask is None else np.asarray(vertex_mask, bool).reshape(-1)
    return _stats(V, tris, edge_faces(tris), vobs, cameras, rasters, gates, wide, deg, sp, vm, pose_cov)


# =========================================================================== diagnosis
def diagnose_focal_distance(landmark_rms_pct_iod: float, contour_resid_median_sigma: Any,
                            ears_fail: bool = False, *, rms_max_pct: float | None = None,
                            sigma_k: float | None = None, min_views: int | None = None):
    """SIL-3 (DESIGN 4.16 "Diagnosis"; rec SIL-3, [Acc 3.8]): "focal or distance wrong, not the face".

    Returns a :class:`face3d.qa.checks.Finding` with code ``'C-FOCAL-DIST'`` when the
    interior landmark RMS is below 3 % IOD **and** the contour residual median exceeds
    3 sigma_n on at least 2 views (``contour_resid_median_sigma``: per-view medians of
    |r| in sigma units, a sequence or a {view: value} dict), or the ears fail; else None.
    ``detail['views_failing']`` lists the failing positions (the dict keys for a dict).

    The rule reads residuals; what they are measured against decides its power.  A
    shape fitted to the same views' contours absorbs a focal / distance error shared by
    them (a free shape explains the dolly-zoom), so the rule is meant for **witness**
    contours: a shape fitted without them, the cameras from the interior landmarks
    (:func:`focal_distance_check`, ``contour_stage(witness_views=...)``).
    """
    rms_max = float(CONTOUR["diag_rms_pct_iod"].value if rms_max_pct is None else rms_max_pct)
    k = float(CONTOUR["diag_sigma_k"].value if sigma_k is None else sigma_k)
    nmin = int(CONTOUR["diag_min_views"].value if min_views is None else min_views)
    is_dict = isinstance(contour_resid_median_sigma, dict)
    keys = list(contour_resid_median_sigma.keys()) if is_dict else None
    vals = list(contour_resid_median_sigma.values()) if is_dict else list(contour_resid_median_sigma)
    vals = [float(x) for x in vals]
    bad = [i for i, x in enumerate(vals) if x > k]
    lm_ok = float(landmark_rms_pct_iod) < rms_max
    if not (lm_ok and (len(bad) >= nmin or bool(ears_fail))):
        return None
    from ..qa.checks import Finding   # data class only (lazy: qa sits above fit in DESIGN 2.2)

    return Finding(code=FINDING_FOCAL_DIST, severity="warn",
                   value={"landmark_rms_pct_iod": float(landmark_rms_pct_iod), "contour_median_sigma": vals,
                          "ears_fail": bool(ears_fail)},
                   threshold={"landmark_rms_pct_iod_lt": rms_max, "contour_median_sigma_gt": k, "min_views": nmin},
                   action="ask", msg_key="contour.focal_or_distance_wrong",
                   fix_key="contour.check_focal_distance", source="DESIGN 4.16 SIL-3 (rec SIL-3; [Acc 3.8])",
                   badge=_BRAIN, detail={"views_failing": [keys[i] for i in bad] if is_dict else bad})


def landmark_rms_pct_iod(X: np.ndarray, cameras: Sequence[Camera], uv: Sequence[np.ndarray],
                         iod_px: Any, idx: Any = None) -> float:
    """Pooled RMS of landmark reprojection errors in % of each view's IOD_px (NaN rows skipped).

    ``idx``: optional landmark subset (indices or a bool mask), e.g. the SIL-3 interior
    landmarks (:func:`interior_landmark_mask`); default all."""
    acc, n = 0.0, 0
    Xa = np.asarray(X, float)
    for k, cam in enumerate(cameras):
        U = np.asarray(uv[k], float)
        m = np.isfinite(U).all(axis=1)
        if idx is not None:
            m &= _as_mask(idx, len(U))
        if not m.any():
            continue
        e = np.linalg.norm(cam.project(Xa[:len(U)][m]) - U[m], axis=1) / float(iod_px[k]) * 100.0
        acc += float(np.sum(e ** 2))
        n += int(m.sum())
    return math.sqrt(acc / n) if n else float("nan")


#: Anatomical bases that are *not* interior for SIL-3: the outline (zy, go), ear (t, sa, sba),
#: cranial (v, op, eu) and hairline (tr) landmarks.  DESIGN 4.16 SIL-3 contrasts the interior
#: landmarks with the contour and the ears; camera-perspective-distortion: "interior features
#: matching while ears and contour do not means f and z are wrong together" (provisional, 🧠).
SIL3_NON_INTERIOR_BASES: tuple[str, ...] = ("v", "tr", "op", "eu", "t", "sa", "sba", "zy", "go")


def interior_landmark_mask(names: Sequence[str]) -> np.ndarray:
    """(N,) bool: True for the SIL-3 interior landmarks of a scheme (DESIGN 4.16 "Diagnosis").

    A name's anatomical base is the part before the first '_' (``'en_L'`` -> ``'en'``);
    bases in :data:`SIL3_NON_INTERIOR_BASES` (outline, ear, cranial, hairline) are not
    interior.  Names of other schemes that carry no anatomical base count as interior."""
    return np.array([str(n).split("_")[0] not in SIL3_NON_INTERIOR_BASES for n in names], bool)


def _as_mask(idx: Any, n: int) -> np.ndarray:
    a = np.asarray(idx)
    if a.dtype == bool:
        if a.shape != (n,):
            raise ValueError(f"landmark mask has shape {a.shape}, expected ({n},)")
        return a.copy()
    m = np.zeros(n, bool)
    m[a.astype(np.int64).reshape(-1)] = True
    return m


# =========================================================================== the stage
@dataclass
class ContourStageResult:
    """Output of :func:`contour_stage` (DESIGN 4.15 stage D).

    V (V, 3) mm; q (3K,) parameters c~; c (3K,) coefficients; X (N, 3) landmarks;
    cameras (one per input view; a witness view's is its SIL-3 refit); history (per outer
    iteration: gates, row counts, cost); view_stats (final, :meth:`ContourTerm.view_stats`,
    keyed by input view index); initial_stats (the same at the start of the stage);
    landmark_shift_mm (N,) |X - X_start|; landmark_rms_pct_iod (interior landmarks of the
    fitted views); findings (SIL-3: the witness check, and the rule on the fitted views'
    final state); bundle (last BundleResult); flags (``C-LM-SHIFT`` when a landmark moved
    more than 0.5 mm, com R5.2); V_start (the surface the stage started from, e.g. the
    landmark-stage surface, for a held-shape :func:`focal_distance_check`); witness (the
    :func:`focal_distance_check` info of the witness views, keyed by input view index, or
    None); interior (N,) bool, the SIL-3 interior landmarks used.
    """

    V: np.ndarray
    q: np.ndarray
    c: np.ndarray
    X: np.ndarray
    cameras: list
    history: list
    view_stats: dict
    landmark_shift_mm: np.ndarray
    landmark_rms_pct_iod: float
    findings: list
    bundle: Any = None
    initial_stats: dict | None = None
    flags: list = field(default_factory=list)
    V_start: np.ndarray | None = None
    witness: dict | None = None
    interior: np.ndarray | None = None


class _LandmarkHold:
    """Prior term N(X_start, sigma^2 I) on the first N points (the landmarks) of a basis with
    coefficient rows: rows only for the landmarks (DESIGN 4.15 D; com R5.2 gate)."""

    is_prior = True

    def __init__(self, X_start: np.ndarray, sigma_mm: float, n_points: int, name: str = "landmark_hold"):
        self.name = name
        self.X0 = np.asarray(X_start, float).reshape(-1, 3)
        self.sigma = float(sigma_mm)
        if not self.sigma > 0:
            raise ValueError("hold_sigma_mm must be > 0")
        n3 = 3 * len(self.X0)
        J = np.zeros((n3, 3 * int(n_points)))
        J[np.arange(n3), np.arange(n3)] = 1.0 / self.sigma
        self._J = J

    def n_params(self) -> int:
        return 0

    def init_params(self, state: Any) -> np.ndarray:
        return np.zeros(0)

    def residuals(self, state: Any, p: np.ndarray) -> np.ndarray:
        return ((np.asarray(state.X, float)[:len(self.X0)] - self.X0) / self.sigma).ravel()

    def jacobian(self, state: Any, p: np.ndarray) -> dict:
        return {"X": self._J}


def _pad_view(v: Any, n_extra: int) -> Any:
    """ViewObs with ``n_extra`` unobserved rows appended (the basis' coefficient rows)."""
    N = len(np.asarray(v.uv))

    def pad(a: Any, fill: Any, tail: tuple = ()) -> Any:
        if a is None:
            return None
        arr = np.asarray(a)
        if arr.ndim == 0:
            return a
        ext = np.full((n_extra,) + tail, fill, dtype=np.result_type(arr.dtype, np.asarray(fill).dtype))
        return np.concatenate([arr.reshape((N,) + tail), ext])

    kw = dict(uv=pad(np.asarray(v.uv, float), np.nan, (2,)), weights=pad(v.weights, 1.0),
              cov_px=pad(v.cov_px, 0.0, (2, 2)), multipliers=pad(v.multipliers, 1.0),
              tangents=pad(v.tangents, np.nan, (2,)), tta_px=pad(v.tta_px, 0.0),
              dense_mask=pad(v.dense_mask, False))
    if kw["cov_px"] is not None:
        kw["cov_px"][N:] = np.eye(2)
    if v.sigma_px is not None and np.ndim(v.sigma_px) > 0:
        kw["sigma_px"] = pad(v.sigma_px, 1.0)
    if v.kinds is not None:
        kw["kinds"] = list(v.kinds) + ["generic"] * n_extra
    return replace(v, **kw)


def _phi_keys(views: Sequence[Any]) -> dict:
    """{view: 'phi_<j>'} for HARD focal-group views, j the group's order of first appearance
    among the estimated focal groups (the bundle's ``param_index`` naming, WP-10)."""
    order: dict = {}
    out = {}
    for k, v in enumerate(views):
        if not getattr(v, "estimate_focal", True) or getattr(v, "focal_group", None) is None:
            continue
        j = order.setdefault(v.focal_group, len(order))
        if getattr(v, "focal_tie_sigma", None) is None:
            out[k] = f"phi_{j}"
    return out


def contour_stage(basis: Any, views: Sequence[Any], obs: Sequence[ContourObs], iod_px: Any, *,
                  n_outer: int = 5, hold_sigma_mm: float | None = None, coef_sigma_mm: float | None = None,
                  raster_scale: float | None = None, max_iter: int = 20, max_iter_inner: int | None = 6,
                  huber_px: float | None = 3.0,
                  irls_rounds: int = 1, term_kwargs: dict | None = None, bundle_kwargs: dict | None = None,
                  q0: np.ndarray | None = None, witness_views: Sequence[int] = (),
                  interior: Any = None) -> ContourStageResult:
    """Contour stage with free cameras through the landmark bundle (DESIGN 4.15 D, 4.16; WBS WP-17).

    basis : :class:`~face3d.solve.shape_models.LinearBasis` on the landmark-stage mesh
        V_bar (its scheme points are the landmarks of ``views``).
    views : bundle :class:`~face3d.solve.bundle.ViewObs` of those landmarks; their cameras
        initialise the stage (e.g. the landmark bundle's cameras) and their focal settings
        (FREE / grouped / FIXED_F) are kept.
    obs : :class:`ContourObs` list (``view`` indexes ``views``); iod_px per view (f IOD_mm / z).
    q0 : optional starting parameters c~ (default 0: start at V_bar).
    term_kwargs / bundle_kwargs : passed to :class:`ContourTerm` / ``bundle_adjust``
        (``phi_keys`` of HARD focal-group views are derived from ``views`` unless given).
    witness_views : views kept out of the fit (neither their landmarks nor their contours
        enter it) and checked afterwards by SIL-3 against the fitted shape
        (:func:`focal_distance_check`: cameras from their interior landmarks with the shape
        held, contours as witnesses, the camera uncertainty in sigma).  Their cameras must
        be usable starting points (e.g. a PnP of their landmarks on the landmark stage).
    interior : the SIL-3 interior landmarks (indices or (N,) bool); default
        :func:`interior_landmark_mask` of ``basis.names``.

    Each of ``n_outer`` outer iterations rasterises V(c) per view at ``raster_scale``
    (visibility), calls :meth:`ContourTerm.update` (rim, gate, matches, frozen weights)
    and runs :func:`~face3d.solve.bundle.bundle_adjust` with the basis as shape model
    (scale disabled: size is fixed by the landmark stage and Pi), the landmark data, a
    hold prior N(X_start, hold_sigma^2) on the landmarks (com R5.2: no landmark moves
    > 0.5 mm; default 0.1 mm), the :class:`~face3d.solve.shape_models.BasisPrior` and
    the contour term.  The correspondences change between outer iterations, so the inner
    LM runs are capped at ``max_iter_inner`` (6) iterations and only the last one runs to
    ``max_iter``.

    SIL-3 (DESIGN 4.16 "Diagnosis"): the witness views are diagnosed as above; the rule is
    also applied to the fitted views' final state (interior landmark RMS, wide-gate median
    |r| / sigma_n).  The latter rarely fires: the free shape and poses absorb a focal or
    distance error that all fitted views share (WP-17 review sweep: a +25 % focal on all
    views of a 0.35 m selfie set leaves every view below 1 sigma_n), so a mis-set focal is
    found only against contours the shape was not fitted to.
    """
    from ..solve.bundle import bundle_adjust                  # L3 solver; imported lazily
    from ..solve.shape_models import BasisPrior

    b = basis if basis.expose_coefficients else basis.with_coefficient_rows()
    views = list(views)
    N = b.N
    for k, v in enumerate(views):
        if len(np.asarray(v.uv)) != N:
            raise ValueError(f"view {k} has {len(np.asarray(v.uv))} landmarks; the basis has {N}")
    wit = sorted({int(w) for w in witness_views})
    if any(w < 0 or w >= len(views) for w in wit):
        raise ValueError(f"witness_views {wit} out of range for {len(views)} views")
    fit = [k for k in range(len(views)) if k not in wit]
    if not fit:
        raise ValueError("contour_stage needs at least one fitted (non-witness) view")
    pos = {k: i for i, k in enumerate(fit)}                  # input view -> fitted (compact) index
    imask = (_as_mask(interior, N) if interior is not None
             else interior_landmark_mask(getattr(b, "names", [""] * N)))
    fviews = [views[k] for k in fit]
    fobs = [replace(o, view=pos[o.view]) for o in obs if o.view in pos]
    iod = {i: float(iod_px[k]) for i, k in enumerate(fit)}
    tk = dict(term_kwargs or {})
    tk.setdefault("phi_keys", _phi_keys(fviews))
    term = ContourTerm(fobs, b, iod, n_outer=n_outer, **tk)
    prior = BasisPrior(b, coef_sigma_mm)
    hold = float(CONTOUR["hold_sigma_mm"].value if hold_sigma_mm is None else hold_sigma_mm)
    rs = float(CONTOUR["raster_scale"].value if raster_scale is None else raster_scale)
    q = np.zeros(b.n_params) if q0 is None else np.asarray(q0, float).reshape(-1).copy()
    X_start = b.points(q)[:N].copy()
    V_start = b.vertices_q(q)
    hold_term = _LandmarkHold(X_start, hold, b.n_points)
    pviews = [_pad_view(v, b.K) for v in fviews]
    cams = [v.camera.copy() for v in fviews]
    history = []
    res = None
    bk = dict(bundle_kwargs or {})
    initial = None
    back = {i: k for k, i in pos.items()}
    for it in range(int(n_outer)):
        V = b.vertices_q(q)
        rasters = {}
        for v in term.views:
            rc = scale_camera(cams[v], rs)
            rasters[v] = rasterize(V, b.tris, rc, cull_backfaces=True)
        if it == 0:
            initial = term.view_stats(V, cams, rasters)
        term.update(V, cams, it, rasters)
        vin = [replace(pv, camera=c.copy()) for pv, c in zip(pviews, cams)]
        last = it == int(n_outer) - 1
        mi = max_iter if (last or max_iter_inner is None) else min(int(max_iter_inner), max_iter)
        res = bundle_adjust(vin, b.points(q), None, huber_px=huber_px, irls_rounds=irls_rounds, max_iter=mi,
                            scale=None, shape_model=b, terms=[term, prior, hold_term], **bk)
        q = b.coef_from_points(res.X)
        cams = [c.copy() for c in res.cameras]
        history.append({"iteration": it, "gates_px": {back[v]: g for v, g in term.gates.items()},
                        "rows": term.n_rows, "cost": float(res.cost), "lm_iterations": int(res.iterations)})
    V = b.vertices_q(q)
    rasters = {v: rasterize(V, b.tris, scale_camera(cams[v], rs), cull_backfaces=True) for v in term.views}
    stats = {back[v]: st for v, st in term.view_stats(V, cams, rasters).items()}
    initial = {back[v]: st for v, st in (initial or {}).items()}
    X = b.points(q)[:N]
    lm_rms = landmark_rms_pct_iod(X, cams, [np.asarray(v.uv, float) for v in fviews], iod, imask)
    findings = []
    f = diagnose_focal_distance(lm_rms, {v: st["wide_median_abs_sigma"] for v, st in stats.items()})
    if f is not None:
        findings.append(f)
    out_cams: list = [None] * len(views)
    for i, k in enumerate(fit):
        out_cams[k] = cams[i]
    witness = None
    if wit:
        wobs = [o for o in obs if o.view in wit]
        if wobs:
            f_w, witness = focal_distance_check(V, b.tris, X, views, wobs, iod_px, interior=imask,
                                                raster_scale=rs, views_subset=wit)
            if f_w is not None:
                findings.append(f_w)
            for k in wit:
                out_cams[k] = witness["cameras"][k]
    for k in range(len(views)):
        if out_cams[k] is None:
            out_cams[k] = views[k].camera.copy()
    shift = np.linalg.norm(X - X_start, axis=1)
    flags = [FLAG_LANDMARK_SHIFT] if shift.max(initial=0.0) > float(CONTOUR["landmark_shift_gate_mm"].value) else []
    return ContourStageResult(V=V, q=q, c=b.coefficients(q), X=X, cameras=out_cams, history=history,
                              view_stats=stats, landmark_shift_mm=shift, landmark_rms_pct_iod=lm_rms,
                              findings=findings, bundle=res, initial_stats=initial, flags=flags, V_start=V_start,
                              witness=witness, interior=imask)


def focal_distance_check(V: np.ndarray, tris: np.ndarray, X: np.ndarray, views: Sequence[Any],
                         obs: Sequence[ContourObs], iod_px: Any, *, refit_cameras: bool = True,
                         hold_sigma_mm: float = 0.01, raster_scale: float | None = None,
                         ears_fail: bool = False, interior: Any = None,
                         landmark_names: Sequence[str] | None = None, pose_inflation: bool = True,
                         views_subset: Sequence[int] | None = None) -> tuple[Any, dict]:
    """SIL-3 witness check with the shape held (DESIGN 4.16 "Diagnosis"): is the focal or distance wrong?

    V (V, 3) / tris: a surface **not fitted to these contours** (e.g. the contour stage's
    shape from other views, a scan); X (N, 3) its landmarks; ``views``: bundle ``ViewObs``
    of those landmarks (their cameras start the refit; their focal settings are kept, so
    FIXED_F views keep their focal frozen); ``obs`` their contours (``view`` indexes
    ``views``); ``views_subset``: the views to check (default every view with contours).

    With ``refit_cameras`` each view's camera is re-solved from its **interior** landmarks
    only (``interior``: indices or (N,) bool; default :func:`interior_landmark_mask` of
    ``landmark_names``, or every landmark when neither is given), the points held at X
    (sigma ``hold_sigma_mm``): a contour-free camera fit, so the contours are pure
    witnesses.  With ``pose_inflation`` each contour residual is divided by
    sqrt(sigma_n^2 + sigma_pose^2), sigma_pose the refit camera's posterior uncertainty
    (``BundleResult.camera_cov``) projected on the observed normal
    (:func:`pose_uv_jacobian`), so a view whose interior landmarks barely fix its pose
    (a profile) is not flagged for that.  The per-view wide-gate median |r| / sigma and the
    interior landmark RMS (% IOD) go to :func:`diagnose_focal_distance`.

    The check is only as good as V along the witnessed outlines: on the WP-17 review sweep
    the landmark-stage surface (template warped to the landmarks) is 2-7 sigma_n off the
    outline of out-of-prior subjects, as large as a +25 % focal at 0.35 m, so that surface
    misclassifies about a third of the cases; a shape fitted to other views' contours
    separates them (tests/test_contours.py::test_focal_distance_diagnosis).

    Returns (finding or None, {'landmark_rms_pct_iod', 'contour_median_sigma' {view: value},
    'view_stats', 'cameras' (one per input view; refit for the checked views),
    'interior' (N,) bool}).
    """
    from ..solve.bundle import Priors, bundle_adjust          # L3 solver; imported lazily

    X = np.asarray(X, float)
    views = list(views)
    N = len(X)
    if interior is not None:
        imask = _as_mask(interior, N)
    elif landmark_names is not None:
        imask = interior_landmark_mask(landmark_names)
    else:
        imask = np.ones(N, bool)
    vids = sorted({o.view for o in obs} if views_subset is None else {int(v) for v in views_subset})
    obs_c = [o for o in obs if o.view in vids]
    vids = sorted({o.view for o in obs_c})
    cams = [v.camera.copy() for v in views]
    pose = None
    if refit_cameras and vids:
        sub = []
        for k in vids:
            U = np.asarray(views[k].uv, float).copy()
            U[~imask[:len(U)]] = np.nan
            sub.append(replace(views[k], uv=U))
        res = bundle_adjust(sub, X.copy(), Priors(mean=X, sigma=float(hold_sigma_mm)), scale=None)
        for i, k in enumerate(vids):
            cams[k] = res.cameras[i].copy()
        if pose_inflation and res.camera_cov is not None:
            pose = {k: (res.camera_cov[i], _view_kind(views[k])) for i, k in enumerate(vids)}
    rs = float(CONTOUR["raster_scale"].value if raster_scale is None else raster_scale)
    tris = np.asarray(tris, np.int64)
    V = np.asarray(V, float)
    rasters = {v: rasterize(V, tris, scale_camera(cams[v], rs), cull_backfaces=True) for v in vids}
    iod = {k: float(iod_px[k]) for k in range(len(views))}
    st = contour_view_stats(V, tris, obs_c, cams, iod, rasters, pose_cov=pose) if vids else {}
    lm = landmark_rms_pct_iod(X, [cams[k] for k in vids], [np.asarray(views[k].uv, float) for k in vids],
                              [iod[k] for k in vids], imask)
    med = {v: st[v]["wide_median_abs_sigma"] for v in vids}
    f = diagnose_focal_distance(lm, med, ears_fail) if vids else None
    return f, {"landmark_rms_pct_iod": lm, "contour_median_sigma": med, "view_stats": st, "cameras": cams,
               "interior": imask}
