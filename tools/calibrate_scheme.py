#!/usr/bin/env python3
"""Render-and-detect calibration of a landmark scheme on a template kit.

Maintainer tool (DESIGN 2.2 layer L9, 3.2 "Scheme" / "Template kit", 8 M3b;
WP-14, run offline by WP-24).  Stdlib + numpy + ``face3d``; never imported by
``face3d``.

Procedure (*landmark-index-correspondence* "Calibrate detector semantics" and
"Apply the calibrated offset, then shrink it", badge 🧠):

1. Render the template kit in Blender from many calibrated views (yaw -60..+60,
   pitch -15/0/+15, several key lights; 20-50 views), run the detector on the
   renders (``tools/detect_mediapipe.py``) and list every render in a records
   file (below).  Only renders of the (CC0) template are calibrated: the records
   file must declare ``"source": "template_render"``.
2. For each scheme index this tool

   * starts from the kit's current embedding of that point (the *prior
     embedding*) or, when the kit has none, from the template surface point hit
     by the back-projected ray of the first detection (z-buffer ``tri_id``
     lookup with :func:`face3d.mesh.raster.rasterize`, then the exact ray /
     triangle-plane intersection);
   * keeps the renders in which it was detected and in which the current
     surface point is visible (camera-facing: ``n . view >= cos 80 deg``,
     DESIGN 4.8 visibility ramp start; and not occluded in the render's
     z-buffer, tolerance :data:`OCCLUSION_TOL_MM` + 2 pixel footprints);
   * refines the surface point by damped Gauss-Newton over ``(tri, bary)``
     minimising ``sum_r ||pi_r(p) - u_r||^2`` (pixels), walking to the neighbour
     triangle across an edge whenever a barycentric goes negative (piecewise
     planar surface; a boundary or a cycle clamps to the triangle);
   * trims renders whose residual exceeds ``max(3 px, 3.035 sigma_hat)``
     (DESIGN D-08 2D 1 % point; sigma_hat = median radial residual / 1.1774)
     and re-solves;
   * shrinks toward the prior embedding with ``w = n / (n + 2)``
     (n = renders used): ``p = p0 + w (p_hat - p0)``, projected back onto the
     surface (no shrink when there is no prior embedding);
   * computes ``sigma_cal`` = RMS over renders of the reprojection residual at
     ``p_hat`` converted to mm at that render's depth (``|r| z / f``), and the
     point's new definition sigma ``sqrt(sigma_def_kind^2 + sigma_cal^2)``
     (DESIGN 4.4 sigma_def by kind; D-06), which becomes the embedding's
     ``sigma_annot_mm``;
   * marks it ``verified`` when ``n >= 20`` and ``sigma_cal <= 1.0 mm``
     (sharp_junction / curve) or ``<= 2.5 mm`` (other kinds) (WP-14 / WP-24
     acceptance limits, 🧠).
3. Checks: every listed mirror pair must map to mirrored surface points
   (``|M p_a - p_b| <= 2 mm`` with ``M = diag(-1, 1, 1)``) else both points get
   ``pair_mismatch``; every geometric ``lr_group`` is resolved by comparing the
   group's 3D centroid with the template eye centres (anatomical44 ``p_L`` /
   ``p_R`` of the kit, else the en/ex midpoints) and recorded as
   ``lr_resolved {group: 'L' | 'R'}``; a group nearer the eye opposite to its
   ``provisional_side`` gets ``lr_unexpected``, a distance ratio below 1.5
   (:data:`face3d.model.registry.LR_RATIO_MIN`) ``lr_ambiguous``, two groups on
   one side ``lr_conflict``.  Sides are never written into the scheme as data
   (they stay ``geometric``); the record is the calibration result.

Inputs::

    records.json = {"format": "face3d.render_records", "version": 1, "source": "template_render",
                    "renders": [{"K": 3x3, "R": 3x3, "t": [3], "W": int, "H": int,
                                 "detections": "relative/path.landmarks.json", "face_index": 0}, ...]}

``K``, ``R``, ``t`` follow DESIGN 3.1 (OpenCV, X_c = R X + t, mm, square
pixels, corner-origin pixels); detections are ``face3d.landmarks`` files of the
scheme (``image.wh == [W, H]``, not flipped).

Outputs: the kit with updated embeddings for the scheme (``--out-kit``), a
report JSON (``--report``: per index n, sigma_cal, verified, flags; pairs;
lr_resolved), and optionally the scheme with updated ``verified`` flags and a
``calibration`` record (``--scheme-out``).  The report holds aggregates and
template-surface positions only, **never detections**; the tool never writes
detections of real people (DESIGN D-26, eth A8).

Usage::

    python3 tools/calibrate_scheme.py --kit KIT.kit.json --renders records.json --scheme mediapipe_478 \\
        --out-kit OUT.kit.json --report REPORT.json [--scheme-path DIR] [--scheme-out SCHEME.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from face3d.geometry.camera import Camera  # noqa: E402
from face3d.io.landmarks import load_landmarks, select_face  # noqa: E402
from face3d.mesh.distance import TriangleGrid, closest_point_on_triangle, point_to_mesh  # noqa: E402
from face3d.mesh.raster import rasterize  # noqa: E402
from face3d.model.registry import LR_RATIO_MIN, Scheme, load_scheme  # noqa: E402
from face3d.model.template_kit import TemplateKit  # noqa: E402

#: Definition-bias sigma by kind, mm (DESIGN 4.4 sigma_def column; hair = WP-03 trichion; 🧠/🆕 provisional).
SIGMA_DEF_MM: dict[str, float] = {"sharp_junction": 0.5, "extremal": 1.5, "curve": 1.0, "contour": 2.0,
                                  "brow": 2.0, "iris": 0.0, "generic": 1.5, "hair": 3.0}
#: Verification: minimum renders and maximum sigma_cal by kind (WP-14 spec, WP-24 M3b; 🧠).
VERIFY_MIN_RENDERS = 20
VERIFY_MAX_SIGMA_MM: dict[str, float] = {"sharp_junction": 1.0, "curve": 1.0}
VERIFY_MAX_SIGMA_OTHER_MM = 2.5
#: Shrinkage pseudo-count: w = n / (n + 2) (*landmark-index-correspondence* 🧠).
SHRINK_PSEUDO_COUNT = 2.0
#: Mirror-pair tolerance, mm (WP-14 spec; 🆕).
PAIR_TOL_MM = 2.0
#: Visibility: facing cosine at the start of the DESIGN 4.8 ramp (cos 80 deg) and z-buffer tolerance (🆕).
FACING_MIN_COS = math.cos(math.radians(80.0))
OCCLUSION_TOL_MM = 1.0
#: Outlier trimming: DESIGN D-08 2D 1 % point (3.035 sigma), floor 3 px (🆕).
OUTLIER_SIGMA = 3.035
OUTLIER_MIN_PX = 3.0
#: Median of a 2D isotropic radial residual / per-axis sigma = sqrt(2 ln 2).
RAYLEIGH_MEDIAN = math.sqrt(2.0 * math.log(2.0))
#: Gauss-Newton limits: trust region per step (mm), iterations, convergence (mm).
MAX_STEP_MM = 5.0
MAX_ITER = 60
STEP_TOL_MM = 1e-7
RECORDS_FORMAT = "face3d.render_records"
REPORT_FORMAT = "face3d.scheme_calibration_report"


class CalibrationError(ValueError):
    """Inputs inconsistent with the calibration contract."""


# =========================================================================== renders
class Render:
    """One calibrated render: camera (square pixels), size and the scheme's detections (N, 2)."""

    def __init__(self, K: Any, R: Any, t: Any, W: int, H: int, uv: np.ndarray, label: str = ""):
        K = np.asarray(K, float).reshape(3, 3)
        fx, fy = float(K[0, 0]), float(K[1, 1])
        if abs(fx - fy) > 1e-9 * abs(fx) or abs(K[0, 1]) > 1e-12 or not np.allclose(K[2], [0, 0, 1]):
            raise CalibrationError(f"render {label}: K must have square pixels, no skew, last row (0, 0, 1)")
        Rm = np.asarray(R, float).reshape(3, 3)
        if np.abs(Rm @ Rm.T - np.eye(3)).max() > 1e-6 or np.linalg.det(Rm) <= 0:
            raise CalibrationError(f"render {label}: R is not a rotation")
        self.cam = Camera(f=fx, cx=float(K[0, 2]), cy=float(K[1, 2]), width=int(W), height=int(H),
                          R=Rm, t=np.asarray(t, float).reshape(3))
        self.uv = np.asarray(uv, float).reshape(-1, 2)
        self.label = label
        self._raster = None

    def raster(self, V: np.ndarray, tris: np.ndarray):
        if self._raster is None:
            self._raster = rasterize(V, tris, self.cam, cull_backfaces=False)
        return self._raster


def load_records(path: str | Path, scheme: Scheme) -> list[Render]:
    """Read the render records file and its LandmarkSet detections (see the module docstring)."""
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or doc.get("format") != RECORDS_FORMAT:
        raise CalibrationError(f"{path.name}: not a {RECORDS_FORMAT} file")
    if doc.get("source") != "template_render":
        raise CalibrationError(f"{path.name}: calibration runs only on renders of the template "
                               "(records 'source' must be 'template_render'); never on photos of people")
    renders = []
    for k, rec in enumerate(doc.get("renders", [])):
        det = path.parent / rec["detections"]
        ls = load_landmarks(det)
        if ls.scheme != scheme.scheme:
            raise CalibrationError(f"{det.name}: scheme {ls.scheme!r}, expected {scheme.scheme!r}")
        if list(ls.image.get("wh", [])) != [int(rec["W"]), int(rec["H"])]:
            raise CalibrationError(f"{det.name}: image wh {ls.image.get('wh')} != render size {[rec['W'], rec['H']]}")
        if ls.image.get("input_flipped"):
            raise CalibrationError(f"{det.name}: flipped detections cannot calibrate a scheme")
        face = select_face(ls, int(rec.get("face_index", 0)))
        if face.uv.shape != (scheme.n, 2):
            raise CalibrationError(f"{det.name}: {face.uv.shape[0]} points, scheme has {scheme.n}")
        uv = np.where(np.asarray(face.visible, bool)[:, None], face.uv, np.nan)
        renders.append(Render(rec["K"], rec["R"], rec["t"], rec["W"], rec["H"], uv, label=str(k)))
    if not renders:
        raise CalibrationError(f"{path.name}: no renders")
    return renders


# =========================================================================== surface helpers
class Surface:
    """Triangle surface of the kit with edge adjacency, normals and a closest-point grid."""

    def __init__(self, kit: TemplateKit):
        self.V = kit.vertices
        self.T = kit.triangles()
        self.N = kit.normals
        self.grid = TriangleGrid(self.V, self.T)
        adj: dict[tuple[int, int], list[int]] = {}
        for f, (a, b, c) in enumerate(self.T.tolist()):
            for e in ((a, b), (b, c), (c, a)):
                adj.setdefault((min(e), max(e)), []).append(f)
        self.adj = adj

    def corners(self, tri: int) -> np.ndarray:
        return self.V[self.T[tri]]

    def point(self, tri: int, bary: np.ndarray) -> np.ndarray:
        return np.asarray(bary, float) @ self.corners(tri)

    def normal(self, tri: int, bary: np.ndarray) -> np.ndarray:
        n = np.asarray(bary, float) @ self.N[self.T[tri]]
        ln = np.linalg.norm(n)
        if ln == 0.0:
            A, B, C = self.corners(tri)
            n = np.cross(B - A, C - A)
            ln = np.linalg.norm(n)
        return n / ln

    def neighbour(self, tri: int, k: int) -> int | None:
        """Triangle across the edge opposite corner ``k`` of ``tri`` (None on a boundary)."""
        v = self.T[tri]
        e = (int(v[(k + 1) % 3]), int(v[(k + 2) % 3]))
        others = [f for f in self.adj.get((min(e), max(e)), []) if f != tri]
        return others[0] if others else None

    @staticmethod
    def plane_bary(A: np.ndarray, B: np.ndarray, C: np.ndarray, q: np.ndarray) -> np.ndarray:
        E = np.column_stack([B - A, C - A])
        beta = np.linalg.lstsq(E, q - A, rcond=None)[0]
        return np.array([1.0 - beta[0] - beta[1], beta[0], beta[1]])

    def walk(self, tri: int, q: np.ndarray, max_steps: int = 256) -> tuple[int, np.ndarray]:
        """Locate ``q`` (a point near the surface) by walking across edges from ``tri``.

        While a barycentric (in the current triangle's plane) is negative, step to the
        neighbour across the edge opposite the most negative corner; on a boundary or a
        cycle, clamp to the closest point of the current triangle.
        """
        seen = {tri}
        cur = tri
        for _ in range(max_steps):
            A, B, C = self.corners(cur)
            b = self.plane_bary(A, B, C, q)
            if b.min() >= -1e-12:
                b = np.clip(b, 0.0, None)
                return cur, b / b.sum()
            nb = self.neighbour(cur, int(np.argmin(b)))
            if nb is None or nb in seen:
                break
            seen.add(nb)
            cur = nb
        A, B, C = self.corners(cur)
        _, _, bb = closest_point_on_triangle(q, A, B, C)
        return cur, bb[0]

    def project(self, P: np.ndarray) -> tuple[int, np.ndarray]:
        _, _, tri, bary = point_to_mesh(np.asarray(P, float).reshape(1, 3), self.V, self.T, grid=self.grid)
        return int(tri[0]), bary[0]


def _proj_jac(renders: Sequence[Render], p: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Projections (m, 2), Jacobians d u / d p (m, 2, 3) and depths (m,) of point ``p``."""
    out = np.empty((len(renders), 2))
    J = np.empty((len(renders), 2, 3))
    z = np.empty(len(renders))
    for k, r in enumerate(renders):
        c = r.cam
        Xc = c.R @ p + c.t
        zz = Xc[2]
        out[k] = (c.f * Xc[0] / zz + c.cx, c.f * Xc[1] / zz + c.cy)
        dXc = np.array([[c.f / zz, 0.0, -c.f * Xc[0] / zz ** 2], [0.0, c.f / zz, -c.f * Xc[1] / zz ** 2]])
        J[k] = dXc @ c.R
        z[k] = zz
    return out, J, z


def visible_in(render: Render, surf: Surface, tri: int, bary: np.ndarray) -> bool:
    """Camera-facing (n . view >= cos 80 deg) and not occluded in the render's z-buffer."""
    p = surf.point(tri, bary)
    c = render.cam
    Xc = c.R @ p + c.t
    if Xc[2] <= 0.0:
        return False
    view = c.center - p
    if float(surf.normal(tri, bary) @ view) < FACING_MIN_COS * float(np.linalg.norm(view)):
        return False
    u = c.f * Xc[0] / Xc[2] + c.cx
    v = c.f * Xc[1] / Xc[2] + c.cy
    i, j = int(math.floor(u)), int(math.floor(v))
    if not (0 <= i < c.width and 0 <= j < c.height):
        return False
    depth = render.raster(surf.V, surf.T).depth[j, i]
    tol = OCCLUSION_TOL_MM + 2.0 * Xc[2] / c.f
    return bool(Xc[2] <= depth + tol)


def ray_init(obs: Sequence[tuple[Render, np.ndarray]], surf: Surface) -> tuple[int, np.ndarray] | None:
    """Surface point hit by the back-projected ray of the first usable detection (z-buffer tri_id)."""
    for r, u in obs:
        i, j = int(math.floor(u[0])), int(math.floor(u[1]))
        if not (0 <= i < r.cam.width and 0 <= j < r.cam.height):
            continue
        tri = int(r.raster(surf.V, surf.T).tri_id[j, i])
        if tri < 0:
            continue
        o, d = r.cam.ray(np.asarray(u, float))
        d = d[0]
        A, B, C = surf.corners(tri)
        n = np.cross(B - A, C - A)
        den = float(n @ d)
        q = o + (float(n @ (A - o)) / den) * d if abs(den) > 1e-12 else surf.point(tri, np.full(3, 1.0 / 3.0))
        return surf.walk(tri, q)
    return None


def _cost(surf: Surface, renders: Sequence[Render], U: np.ndarray, tri: int, bary: np.ndarray) -> float:
    pr, _, _ = _proj_jac(renders, surf.point(tri, bary))
    return float(np.sum((pr - U) ** 2))


def refine(surf: Surface, tri: int, bary: np.ndarray, renders: Sequence[Render], U: np.ndarray
           ) -> tuple[int, np.ndarray]:
    """Damped Gauss-Newton over (tri, bary) with triangle walking (see the module docstring)."""
    if not renders:
        return tri, bary
    lam = 1e-3
    cost = _cost(surf, renders, U, tri, bary)
    for _ in range(MAX_ITER):
        A, B, C = surf.corners(tri)
        E = np.column_stack([B - A, C - A])
        p = surf.point(tri, bary)
        pr, Jp, _ = _proj_jac(renders, p)
        J = (Jp @ E).reshape(-1, 2)
        r = (pr - U).reshape(-1)
        Hm = J.T @ J
        g = J.T @ r
        accepted = False
        for _ in range(12):
            D = Hm + lam * np.diag(np.diag(Hm)) + 1e-12 * np.eye(2)
            delta = -np.linalg.solve(D, g)
            step = E @ delta
            sl = float(np.linalg.norm(step))
            if sl > MAX_STEP_MM:
                delta *= MAX_STEP_MM / sl
                step = E @ delta
            q = p + step
            t2, b2 = surf.walk(tri, q)
            c2 = _cost(surf, renders, U, t2, b2)
            if c2 < cost:
                moved = float(np.linalg.norm(surf.point(t2, b2) - p))
                tri, bary, cost = t2, b2, c2
                lam = max(lam * 0.1, 1e-9)
                accepted = True
                break
            lam *= 10.0
        if not accepted or moved < STEP_TOL_MM:
            break
    return tri, bary


# =========================================================================== calibration
def kit_key(scheme: Scheme, point: Any) -> str:
    """Kit embedding key: anatomical id for 'anatomical44', the point name otherwise (WP-08 kit format)."""
    if scheme.scheme == "anatomical44" and point.anatomical_id is not None:
        return str(point.anatomical_id)
    return str(point.name)


def eye_centres(kit: TemplateKit) -> dict[str, np.ndarray]:
    """Template eye centres {'L', 'R'}: anatomical44 p_L / p_R, else the en/ex midpoints."""
    if "anatomical44" not in kit.landmarks:
        raise CalibrationError("the kit has no anatomical44 embeddings: cannot locate the template eyes")
    names = kit.landmark_names("anatomical44")
    out = {}
    for s in ("L", "R"):
        if f"p_{s}" in names:
            out[s] = kit.landmark_positions("anatomical44", names=[f"p_{s}"])[0]
        elif f"en_{s}" in names and f"ex_{s}" in names:
            out[s] = kit.landmark_positions("anatomical44", names=[f"en_{s}", f"ex_{s}"]).mean(axis=0)
        else:
            raise CalibrationError(f"the kit lacks p_{s} and en_{s}/ex_{s}: cannot locate the template eyes")
    return out


def verify_limit(kind: str) -> float:
    return VERIFY_MAX_SIGMA_MM.get(kind, VERIFY_MAX_SIGMA_OTHER_MM)


def calibrate_point(surf: Surface, renders: Sequence[Render], idx: int, kind: str,
                    prior: tuple[int, np.ndarray] | None) -> dict[str, Any]:
    """Calibrate one scheme index; returns its report entry with 'tri', 'bary' and 'position'."""
    obs = [(r, r.uv[idx]) for r in renders if np.all(np.isfinite(r.uv[idx]))]
    entry: dict[str, Any] = {"n_detected": len(obs), "n": 0, "flags": [], "w": None, "sigma_cal_mm": None,
                             "rms_px": None, "init": None, "outliers": 0, "shift_mm": 0.0}
    if prior is not None:
        tri0, b0 = prior
        entry["init"] = "prior_embedding"
    else:
        if not obs:
            entry["flags"].append("not_detected")
            return entry
        hit = ray_init(obs, surf)
        if hit is None:
            entry["flags"].append("no_surface_hit")
            return entry
        tri0, b0 = hit
        entry["init"] = "ray"
    p0 = surf.point(tri0, b0)
    tri, bary = tri0, b0
    used: list[tuple[Render, np.ndarray]] = []
    for _ in range(3):  # visibility depends on the estimate: iterate to a fixed set
        cur = [(r, u) for r, u in obs if visible_in(r, surf, tri, bary)]
        if [id(r) for r, _ in cur] == [id(r) for r, _ in used]:
            break
        used = cur
        tri, bary = refine(surf, tri0, b0, [r for r, _ in used], np.array([u for _, u in used]).reshape(-1, 2))
    if used:
        pr, _, _ = _proj_jac([r for r, _ in used], surf.point(tri, bary))
        e = np.linalg.norm(pr - np.array([u for _, u in used]), axis=1)
        thr = max(OUTLIER_MIN_PX, OUTLIER_SIGMA * float(np.median(e)) / RAYLEIGH_MEDIAN)
        keep = e <= thr
        if not keep.all() and keep.sum() >= 1:
            entry["outliers"] = int((~keep).sum())
            entry["flags"].append("outliers_rejected")
            used = [o for o, k in zip(used, keep) if k]
            tri, bary = refine(surf, tri, bary, [r for r, _ in used], np.array([u for _, u in used]).reshape(-1, 2))
    n = len(used)
    entry["n"] = n
    if n == 0:
        entry["flags"].append("not_visible" if obs else "not_detected")
        if prior is None:
            return entry
        entry.update({"tri": int(tri0), "bary": np.asarray(b0, float), "position": p0, "calibrated": False})
        return entry
    p_hat = surf.point(tri, bary)
    pr, _, z = _proj_jac([r for r, _ in used], p_hat)
    e_px = np.linalg.norm(pr - np.array([u for _, u in used]), axis=1)
    f = np.array([r.cam.f for r, _ in used])
    e_mm = e_px * z / f
    sigma_cal = float(np.sqrt(np.mean(e_mm ** 2)))
    if prior is not None:
        w = n / (n + SHRINK_PSEUDO_COUNT)
        tri_s, bary_s = surf.project(p0 + w * (p_hat - p0))
    else:
        w = 1.0
        tri_s, bary_s = tri, bary
    pos = surf.point(tri_s, bary_s)
    sdef_kind = SIGMA_DEF_MM.get(kind, SIGMA_DEF_MM["generic"])
    entry.update({
        "w": w, "sigma_cal_mm": sigma_cal, "rms_px": float(np.sqrt(np.mean(e_px ** 2))),
        "sigma_def_kind_mm": sdef_kind, "sigma_def_mm": float(math.hypot(sdef_kind, sigma_cal)),
        "verified": bool(n >= VERIFY_MIN_RENDERS and sigma_cal <= verify_limit(kind)),
        "tri": int(tri_s), "bary": np.asarray(bary_s, float), "position": pos,
        "p_hat": p_hat, "shift_mm": float(np.linalg.norm(pos - p0)) if prior is not None else 0.0,
        "calibrated": True,
    })
    return entry


def calibrate(kit: TemplateKit, renders: Sequence[Render], scheme: Scheme) -> tuple[TemplateKit, dict[str, Any]]:
    """Run the calibration; returns (kit with updated embeddings for the scheme, report dict)."""
    surf = Surface(kit)
    prior_lm = kit.landmarks.get(scheme.scheme, {})
    results: list[dict[str, Any]] = []
    for pt in scheme.points:
        key = kit_key(scheme, pt)
        prior = None
        if key in prior_lm:
            prior = (int(prior_lm[key]["tri"]), np.asarray(prior_lm[key]["bary"], float))
        e = calibrate_point(surf, renders, pt.index, pt.kind, prior)
        e.update({"index": pt.index, "name": pt.name, "kit_key": key, "kind": pt.kind})
        e.setdefault("verified", False)
        results.append(e)

    # mirror pairs
    pos = {e["index"]: e["position"] for e in results if "position" in e}
    M = np.array([-1.0, 1.0, 1.0])
    pairs = []
    for a, b in scheme.mirror_pairs:
        if a in pos and b in pos:
            d = float(np.linalg.norm(pos[a] * M - pos[b]))
            ok = d <= PAIR_TOL_MM
            pairs.append({"pair": [int(a), int(b)], "mirror_distance_mm": d, "ok": ok})
            if not ok:
                for i in (a, b):
                    if "pair_mismatch" not in results[i]["flags"]:
                        results[i]["flags"].append("pair_mismatch")

    # geometric L/R groups
    groups = []
    lr_resolved: dict[str, str] = {}
    if scheme.lr_groups:
        eyes = eye_centres(kit)
        for k, g in enumerate(scheme.lr_groups):
            gname = str(g.get("name", f"group{k}"))
            P = [pos[i] for i in g["indices"] if i in pos]
            rec: dict[str, Any] = {"name": gname, "indices": list(g["indices"]),
                                   "provisional_side": g.get("provisional_side"), "flags": []}
            if not P:
                rec["flags"].append("unresolved")
                groups.append(rec)
                continue
            c = np.mean(P, axis=0)
            dL, dR = float(np.linalg.norm(c - eyes["L"])), float(np.linalg.norm(c - eyes["R"]))
            side = "L" if dL <= dR else "R"
            ratio = max(dL, dR) / max(min(dL, dR), 1e-12)
            rec.update({"resolved": side, "d_L_mm": dL, "d_R_mm": dR, "distance_ratio": ratio})
            if ratio < LR_RATIO_MIN:
                rec["flags"].append("lr_ambiguous")
            if g.get("provisional_side") in ("L", "R") and side != g["provisional_side"]:
                rec["flags"].append("lr_unexpected")
            lr_resolved[gname] = side
            groups.append(rec)
        sides = [g["resolved"] for g in groups if "resolved" in g]
        if len(sides) != len(set(sides)):
            for g in groups:
                if "resolved" in g:
                    g["flags"].append("lr_conflict")
        for g in groups:
            for i in g["indices"]:
                for fl in g["flags"]:
                    if fl not in results[i]["flags"]:
                        results[i]["flags"].append(fl)

    # updated kit embeddings
    lms = {s: {k: dict(v) for k, v in pts.items()} for s, pts in kit.landmarks.items()}
    out = dict(lms.get(scheme.scheme, {}))
    for e in results:
        if not e.get("calibrated"):
            continue
        out[e["kit_key"]] = {
            "tri": e["tri"], "bary": e["bary"], "sigma_annot_mm": e["sigma_def_mm"],
            "provenance": (f"calibrate_scheme render-and-detect: n={e['n']}, w={e['w']:.4f}, "
                           f"sigma_cal={e['sigma_cal_mm']:.3f} mm, sigma_def_kind={e['sigma_def_kind_mm']:.2f} mm, "
                           f"init={e['init']}, verified={e['verified']}"),
        }
    lms[scheme.scheme] = out
    new_kit = kit.replace(landmarks=lms)

    points = []
    for e in results:
        points.append({k: e.get(k) for k in ("index", "name", "kind", "n_detected", "n", "sigma_cal_mm", "rms_px",
                                              "sigma_def_kind_mm", "sigma_def_mm", "verified", "w", "init",
                                              "outliers", "shift_mm", "flags")}
                      | ({"tri": e["tri"], "bary": [float(x) for x in e["bary"]]} if e.get("calibrated") else {}))
    report = {
        "format": REPORT_FORMAT, "version": 1, "scheme": scheme.scheme,
        "kit": {"id": kit.id, "topology_sha256": kit.topology_sha256, "licence": kit.licence,
                "generated": kit.generated},
        "n_renders": len(renders),
        "settings": {"verify_min_renders": VERIFY_MIN_RENDERS, "verify_max_sigma_mm": dict(VERIFY_MAX_SIGMA_MM),
                     "verify_max_sigma_other_mm": VERIFY_MAX_SIGMA_OTHER_MM,
                     "shrink": f"w = n / (n + {SHRINK_PSEUDO_COUNT:g})", "pair_tol_mm": PAIR_TOL_MM,
                     "sigma_def_mm_by_kind": dict(SIGMA_DEF_MM), "outlier": f"max({OUTLIER_MIN_PX} px, "
                                                                            f"{OUTLIER_SIGMA} sigma)",
                     "facing_min_cos": FACING_MIN_COS, "occlusion_tol_mm": OCCLUSION_TOL_MM},
        "points": points,
        "pairs": pairs,
        "lr_groups": groups,
        "lr_resolved": lr_resolved,
        "summary": {"n_points": len(points), "n_verified": sum(1 for p in points if p["verified"]),
                    "n_calibrated": sum(1 for e in results if e.get("calibrated")),
                    "n_pair_mismatch": sum(1 for p in pairs if not p["ok"])},
        "note": ("Aggregate render-and-detect calibration of a template render set. Contains template-surface "
                 "positions and statistics only, never detections; do not run on photos of people."),
    }
    return new_kit, report


def _clean(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return _clean(obj.tolist())
    if isinstance(obj, (np.floating, float)):
        x = float(obj)
        return round(x, 6) if math.isfinite(x) else None
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def report_bytes(report: Mapping[str, Any]) -> bytes:
    return (json.dumps(_clean(report), indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def updated_scheme(scheme: Scheme, report: Mapping[str, Any], report_sha256: str) -> dict[str, Any]:
    """Scheme document with ``verified`` from the report and a ``calibration`` record (sides unchanged)."""
    doc = scheme.to_dict()
    ver = {p["index"]: bool(p["verified"]) for p in report["points"]}
    for p in doc["points"]:
        p["verified"] = ver.get(p["index"], False)
    doc["calibration"] = {"report_sha256": report_sha256, "kit_id": report["kit"]["id"],
                          "kit_topology_sha256": report["kit"]["topology_sha256"],
                          "n_renders": report["n_renders"], "lr_resolved": dict(report["lr_resolved"]),
                          "n_verified": report["summary"]["n_verified"],
                          "note": "sides of lr_groups stay 'geometric'; lr_resolved records the template result"}
    return doc


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--kit", type=Path, required=True, help="template kit JSON")
    ap.add_argument("--renders", type=Path, required=True, help="render records JSON")
    ap.add_argument("--scheme", required=True, help="scheme id, e.g. mediapipe_478")
    ap.add_argument("--scheme-path", type=Path, default=None, help="scheme JSON or directory (default: package)")
    ap.add_argument("--out-kit", type=Path, required=True, help="output kit JSON (+ .npz)")
    ap.add_argument("--report", type=Path, required=True, help="output report JSON")
    ap.add_argument("--scheme-out", type=Path, default=None, help="optional updated scheme JSON")
    args = ap.parse_args(argv)
    try:
        scheme = load_scheme(args.scheme, args.scheme_path)
        kit = TemplateKit.load(args.kit)
        renders = load_records(args.renders, scheme)
        new_kit, report = calibrate(kit, renders, scheme)
    except (CalibrationError, ValueError, FileNotFoundError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    new_kit.save(args.out_kit)
    data = report_bytes(report)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_bytes(data)
    if args.scheme_out is not None:
        doc = updated_scheme(scheme, report, hashlib.sha256(data).hexdigest())
        args.scheme_out.write_text(json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                                   encoding="utf-8")
    s = report["summary"]
    print(f"{scheme.scheme}: {s['n_calibrated']} calibrated, {s['n_verified']} verified, "
          f"{s['n_pair_mismatch']} pair mismatches; lr_resolved={report['lr_resolved']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
