#!/usr/bin/env python3
"""Build a template kit (``face3d.template_kit`` v1) from an OBJ and landmark annotations.

Maintainer tool (DESIGN 2.2 layer L9; WP-08, used offline by WP-24 for the real
CC0 template).  Stdlib + numpy + the ``face3d`` engine; never imported by
``face3d``.

Usage::

    python3 tools/build_template_kit.py --obj HEAD.obj --annotations ANN.json \\
        --licence CC0-1.0 --source-sha256 HEX --out KIT.kit.json \\
        [--regions REGIONS.json] [--mirror-tol 1e-4] [--allow-noncc0] \\
        [--id KIT_ID] [--generated] [--symmetrize]

Steps and refusals (exit status 2 with a report on stderr):

* **OBJ** read with :func:`face3d.mesh.read_obj`, in mm, FH head frame (+x subject's
  left, +y up, +z forward; DESIGN 3.1).  This version requires an all-quad mesh.
* **Mirror map**: every vertex is reflected (x -> -x) and matched to the nearest
  vertex within ``mirror_tol * bbox diagonal`` (default 1e-4, WP-08 spec;
  *open-template-head-kit* "Build the mirror map": bijection, ``M(M(i)) = i``,
  midline fixed 🧠).  Refused unless the matching is a bijection and an
  involution.  The kit then requires an exact reflection (1e-6 mm,
  :data:`face3d.model.template_kit.MIRROR_TOL_MM`); a mesh that only matches
  within the tolerance is refused unless ``--symmetrize`` snaps it
  (``V <- (V + V[m] * (-1, 1, 1)) / 2``, midline x = 0).
* **Licence**: anything but ``CC0-1.0`` is refused unless ``--allow-noncc0``; such
  a kit has ``bundle_ok == False`` and may not ship in the extension (DESIGN D-28,
  eth A3/A4).
* **Annotations** JSON ``{scheme: {name: {vertex | tri + bary, sigma_annot_mm,
  annotator_spread_mm, [provenance]}}}``.  Two-annotator acceptance: the spread
  between the annotators must be <= 1.0 mm for ``sharp_junction`` / ``curve``
  kinds and <= 2.5 mm otherwise (WP-08 spec, WP-24 step 3; 🧠).  Kinds come from
  :data:`face3d.model.registry.ANATOMICAL` for ``anatomical44`` (keyed by
  anatomical id) and from the scheme file otherwise (``generic`` if unknown).
  Every failing entry is listed in the report.  A ``vertex`` annotation is
  embedded one-hot on the lowest-index fan triangle containing it.
* **Regions** from ``--regions`` (``{name: [vertex ids]}``) or, when absent, the
  geometric rules of :func:`face3d.model.procedural_head.geometric_regions` (they
  need the anatomical44 landmarks p, prn, sn, n, sto, pg, t, go).  Jaw weights and
  stiffness use the same rules as the procedural head; normals are area-weighted;
  UVs come from the OBJ when every vertex has a single UV, else from a spherical
  projection about the bounding-box centre (``meta['uv_source']``).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Mapping

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from face3d.mesh.core import read_obj  # noqa: E402
from face3d.model.procedural_head import (REGION_LANDMARKS, geometric_regions, jaw_weights_rule,  # noqa: E402
                                          region_weights_default, spherical_uv, stiffness_rule)
from face3d.model.registry import ANATOMICAL, load_scheme  # noqa: E402
from face3d.model.template_kit import (MIRROR_TOL_MM, TemplateKit, area_weighted_normals,  # noqa: E402
                                       fan_triangles, midline_ring, vertex_embedding)

#: Two-annotator acceptance: maximum spread (mm) by landmark kind (WP-08 spec, WP-24; 🧠).
SPREAD_LIMIT_MM: dict[str, float] = {"sharp_junction": 1.0, "curve": 1.0}
SPREAD_LIMIT_OTHER_MM = 2.5

#: Default relative mirror-matching tolerance (fraction of the bbox diagonal; WP-08 spec).
DEFAULT_MIRROR_TOL = 1e-4

_SPDX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+\-]*$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class BuildRefused(ValueError):
    """The inputs fail a check; ``report`` lists every problem found."""

    def __init__(self, title: str, report: list[str]):
        self.title = title
        self.report = list(report)
        super().__init__(title + ("\n  - " + "\n  - ".join(report) if report else ""))


# =========================================================================== mirror map
def mirror_map_from_vertices(V: np.ndarray, tol_rel: float = DEFAULT_MIRROR_TOL) -> tuple[np.ndarray, float]:
    """Mirror map by nearest-vertex matching of the x-reflection within ``tol_rel * diag``.

    Uses a uniform grid with cell size = tolerance (27-cell neighbourhood), so it is
    O(V).  Returns ``(mirror_map, max_mismatch_mm)``.  Raises :class:`BuildRefused`
    listing unmatched vertices, vertices claimed twice and involution failures.
    """
    V = np.asarray(V, float)
    lo, hi = V.min(axis=0), V.max(axis=0)
    diag = float(np.linalg.norm(hi - lo))
    tol = float(tol_rel) * diag
    if not tol > 0.0:
        raise BuildRefused("mirror tolerance must be positive", [f"tol_rel={tol_rel}, bbox diagonal={diag}"])
    keys = np.floor((V - lo) / tol).astype(np.int64)
    grid: dict[tuple[int, int, int], list[int]] = {}
    for i, k in enumerate(map(tuple, keys.tolist())):
        grid.setdefault(k, []).append(i)
    Q = V * np.array([-1.0, 1.0, 1.0])
    qkeys = np.floor((Q - lo) / tol).astype(np.int64)
    m = np.full(len(V), -1, dtype=np.int64)
    dist = np.zeros(len(V))
    offs = [(a, b, c) for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1)]
    for i, (kx, ky, kz) in enumerate(qkeys.tolist()):
        cand: list[int] = []
        for a, b, c in offs:
            cand.extend(grid.get((kx + a, ky + b, kz + c), ()))
        if not cand:
            continue
        ca = np.asarray(sorted(cand), dtype=np.int64)
        d = np.linalg.norm(V[ca] - Q[i], axis=1)
        j = int(np.argmin(d))
        if d[j] <= tol:
            m[i] = int(ca[j])
            dist[i] = float(d[j])
    problems: list[str] = []
    unmatched = np.flatnonzero(m < 0)
    if unmatched.size:
        problems.append(f"{unmatched.size} vertices have no mirror partner within {tol:.4g} mm "
                        f"(first: {unmatched[:10].tolist()})")
    used = m[m >= 0]
    vals, counts = np.unique(used, return_counts=True)
    if np.any(counts > 1):
        problems.append(f"{int(np.sum(counts > 1))} vertices are the mirror of several vertices "
                        f"(first: {vals[counts > 1][:10].tolist()}); not a bijection")
    if not problems:
        bad = np.flatnonzero(m[m] != np.arange(len(V)))
        if bad.size:
            problems.append(f"mirror map is not an involution at {bad.size} vertices (first: {bad[:10].tolist()})")
    if problems:
        raise BuildRefused("mesh is not mirror-symmetric", problems)
    return m, float(dist.max()) if len(dist) else 0.0


# =========================================================================== annotations
def _kinds_for(scheme: str) -> dict[str, str]:
    if scheme == "anatomical44":
        return {lid: lm.kind for lid, lm in ANATOMICAL.items()}
    try:
        sch = load_scheme(scheme)
    except (FileNotFoundError, ValueError):
        return {}
    return {p.name: p.kind for p in sch.points}


def spread_limit_mm(kind: str) -> float:
    """Two-annotator acceptance threshold (mm) for a landmark kind."""
    return SPREAD_LIMIT_MM.get(kind, SPREAD_LIMIT_OTHER_MM)


def _finite_nonneg(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x >= 0


def parse_annotations(doc: Mapping[str, Any], tris: np.ndarray, n_verts: int
                      ) -> dict[str, dict[str, dict[str, Any]]]:
    """Validate the annotation JSON and convert it to kit embeddings.

    Raises :class:`BuildRefused` listing every rejected entry (spread above its
    kind's limit, missing fields, bad indices or barycentric coordinates).
    """
    problems: list[str] = []
    out: dict[str, dict[str, dict[str, Any]]] = {}
    T = len(tris)
    for scheme, pts in doc.items():
        if scheme in ("format", "version", "licence", "notes") and not isinstance(pts, dict):
            continue
        if not isinstance(pts, dict):
            problems.append(f"scheme {scheme!r}: expected an object of landmarks")
            continue
        kinds = _kinds_for(scheme)
        emb: dict[str, dict[str, Any]] = {}
        for name, e in pts.items():
            where = f"{scheme}/{name}"
            if not isinstance(e, dict):
                problems.append(f"{where}: expected an object")
                continue
            if scheme == "anatomical44" and name not in ANATOMICAL:
                problems.append(f"{where}: unknown anatomical id")
                continue
            kind = kinds.get(name, "generic")
            limit = spread_limit_mm(kind)
            spread = e.get("annotator_spread_mm")
            if spread is None:
                problems.append(f"{where}: missing annotator_spread_mm (two-annotator acceptance)")
            elif not _finite_nonneg(spread):
                problems.append(f"{where}: annotator_spread_mm must be a finite number >= 0, got {spread!r}")
            elif float(spread) > limit:
                problems.append(f"{where} ({kind}): annotator spread {float(spread):.3g} mm exceeds {limit:g} mm")
            sigma = e.get("sigma_annot_mm")
            if not _finite_nonneg(sigma):
                problems.append(f"{where}: sigma_annot_mm must be a finite number >= 0, got {sigma!r}")
            if "vertex" in e:
                v = e["vertex"]
                if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v < n_verts:
                    problems.append(f"{where}: vertex {v!r} out of range (V={n_verts})")
                    continue
                try:
                    tri, bary = vertex_embedding(tris, v)
                except ValueError as ex:
                    problems.append(f"{where}: {ex}")
                    continue
            elif "tri" in e and "bary" in e:
                tri = e["tri"]
                if not isinstance(tri, int) or isinstance(tri, bool) or not 0 <= tri < T:
                    problems.append(f"{where}: triangle {tri!r} out of range (T={T})")
                    continue
                try:
                    bary = np.asarray(e["bary"], dtype=float).reshape(-1)
                except (TypeError, ValueError):
                    problems.append(f"{where}: bary is not numeric")
                    continue
                if bary.shape != (3,) or not np.all(np.isfinite(bary)) or bary.min() < -1e-9 \
                        or abs(float(bary.sum()) - 1.0) > 1e-6:
                    problems.append(f"{where}: bary must be 3 non-negative numbers summing to 1, got {e['bary']!r}")
                    continue
            else:
                problems.append(f"{where}: needs 'vertex' or 'tri' + 'bary'")
                continue
            if _finite_nonneg(sigma):
                emb[str(name)] = {"tri": int(tri), "bary": np.asarray(bary, float), "sigma_annot_mm": float(sigma),
                                  "provenance": str(e.get("provenance", "two_annotator"))}
        out[str(scheme)] = emb
    if problems:
        raise BuildRefused(f"annotations rejected ({len(problems)} problems)", problems)
    if not out:
        raise BuildRefused("annotations rejected", ["no landmark schemes found"])
    return out


def _regions_from_json(doc: Mapping[str, Any], n_verts: int) -> dict[str, np.ndarray]:
    reg = doc.get("regions", doc) if isinstance(doc, dict) else doc
    problems: list[str] = []
    out: dict[str, np.ndarray] = {}
    for name, ids in reg.items():
        if name in ("format", "version", "licence", "notes"):
            continue
        try:
            a = np.asarray(ids, dtype=np.int64).reshape(-1)
        except (TypeError, ValueError):
            problems.append(f"region {name!r}: not a list of vertex ids")
            continue
        if a.size and (a.min() < 0 or a.max() >= n_verts):
            problems.append(f"region {name!r}: vertex id out of range (V={n_verts})")
            continue
        out[str(name)] = np.unique(a)
    if problems:
        raise BuildRefused("regions rejected", problems)
    return out


def _vertex_uv(mesh: Any, n_verts: int) -> np.ndarray | None:
    if mesh.uvs is None or mesh.face_uvs is None:
        return None
    uv = np.full((n_verts, 2), np.nan)
    for f, fu in zip(mesh.faces, mesh.face_uvs):
        for v, t in zip(f, fu):
            u = mesh.uvs[t]
            if np.isnan(uv[v, 0]):
                uv[v] = u
            elif not np.array_equal(uv[v], u):
                return None  # a seam: per-vertex UV is not single-valued
    return None if np.isnan(uv).any() else uv


# =========================================================================== build
def build_kit(obj_path: str | Path, annotations: Mapping[str, Any], licence: str, source_sha256: str, *,
              regions: Mapping[str, Any] | None = None, mirror_tol: float = DEFAULT_MIRROR_TOL,
              allow_noncc0: bool = False, kit_id: str = "template", generated: bool = False,
              symmetrize: bool = False) -> TemplateKit:
    """Build and validate a :class:`TemplateKit` (see the module docstring); raises BuildRefused."""
    if not _SPDX.match(licence or ""):
        raise BuildRefused("invalid licence", [f"not an SPDX identifier: {licence!r}"])
    if licence != "CC0-1.0" and not allow_noncc0:
        raise BuildRefused("licence refused", [f"licence {licence!r} is not CC0-1.0; only CC0 kits may be bundled "
                                               "(DESIGN D-28). Pass --allow-noncc0 to build a non-bundlable kit."])
    if not _HEX64.match(source_sha256 or ""):
        raise BuildRefused("invalid source sha256", [f"expected 64 lowercase hex digits, got {source_sha256!r}"])
    mesh = read_obj(obj_path)
    V = np.asarray(mesh.vertices, float)
    if V.ndim != 2 or len(V) == 0:
        raise BuildRefused("OBJ has no vertices", [str(obj_path)])
    sizes = np.asarray([len(f) for f in mesh.faces])
    if sizes.size == 0 or np.any(sizes != 4):
        raise BuildRefused("quads required", [f"{int(np.sum(sizes != 4))} of {sizes.size} faces are not quads"])
    faces = np.asarray(mesh.faces, dtype=np.int64)
    m, mismatch = mirror_map_from_vertices(V, mirror_tol)
    flip = np.array([-1.0, 1.0, 1.0])
    midline = np.flatnonzero(m == np.arange(len(V)))
    if symmetrize:
        V = 0.5 * (V + V[m] * flip)
        V[midline, 0] = 0.0
    else:
        err = float(np.abs(V[m] * flip - V).max())
        mid_x = float(np.abs(V[midline, 0]).max()) if midline.size else 0.0
        if err > MIRROR_TOL_MM or mid_x > MIRROR_TOL_MM:
            raise BuildRefused("mesh is not exactly mirror-symmetric", [
                f"max reflection error {err:.3g} mm, max midline |x| {mid_x:.3g} mm (kit tolerance "
                f"{MIRROR_TOL_MM:g} mm); symmetrise the mesh or pass --symmetrize"])
    tris = fan_triangles(faces)
    landmarks = parse_annotations(annotations, tris, len(V))
    lm_positions: dict[str, np.ndarray] = {}
    if "anatomical44" in landmarks:
        a = landmarks["anatomical44"]
        T3 = tris[np.asarray([e["tri"] for e in a.values()], np.int64)]
        P = np.einsum("nk,nkd->nd", np.asarray([e["bary"] for e in a.values()]), V[T3])
        lm_positions = {k: P[i] for i, k in enumerate(a)}
    if regions is not None:
        reg = _regions_from_json(regions, len(V))
        region_source = "json"
    else:
        missing = [k for k in REGION_LANDMARKS if k not in lm_positions]
        if missing:
            raise BuildRefused("regions needed", [f"no --regions given and the geometric rules need anatomical44 "
                                                  f"landmarks {missing}"])
        reg = geometric_regions(V, lm_positions)
        region_source = "geometric_rules"
    weights = region_weights_default()
    region_weights = {k: weights.get(k, weights["other"]) for k in reg}
    edges = np.unique(np.sort(np.concatenate([np.stack([faces[:, i], faces[:, (i + 1) % 4]], 1)
                                              for i in range(4)]), axis=1), axis=0)
    jaw = jaw_weights_rule(V, lm_positions["sto"][1]) if "sto" in lm_positions else np.zeros(len(V))
    uv = _vertex_uv(mesh, len(V))
    uv_source = "obj"
    if uv is None:
        d = V - 0.5 * (V.min(axis=0) + V.max(axis=0))
        uv = spherical_uv(d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-300))
        uv_source = "spherical_projection"
    meta = {"builder": "tools/build_template_kit.py", "uv_source": uv_source, "region_source": region_source,
            "mirror_tol_rel": float(mirror_tol), "mirror_max_mismatch_mm": mismatch, "symmetrized": bool(symmetrize),
            "jaw_weights": "rule" if "sto" in lm_positions else "zeros (no sto annotation)"}
    return TemplateKit(id=kit_id, licence=licence, generated=generated, source_sha256=source_sha256,
                       vertices=V, faces=faces, landmarks=landmarks, mirror_map=m, midline=midline,
                       regions=reg, region_weights=region_weights,
                       contour_rings={"midline_profile": midline_ring(V, midline)},
                       jaw_weights=jaw, stiffness=stiffness_rule(len(V), edges, reg),
                       normals=area_weighted_normals(V, faces), uv=uv, meta=meta)


def _default_id(out: Path) -> str:
    name = out.name
    for suf in (".kit.json", ".json"):
        if name.endswith(suf):
            return name[: -len(suf)]
    return out.stem


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--obj", required=True, type=Path, help="quad mesh in mm, FH head frame")
    ap.add_argument("--annotations", required=True, type=Path, help="landmark annotation JSON")
    ap.add_argument("--licence", required=True, help="SPDX licence id of the mesh (CC0-1.0 to bundle)")
    ap.add_argument("--source-sha256", required=True, help="SHA-256 of the source asset")
    ap.add_argument("--out", required=True, type=Path, help="output kit JSON (a sibling .npz is written)")
    ap.add_argument("--regions", type=Path, default=None, help="optional {name: [vertex ids]} JSON")
    ap.add_argument("--mirror-tol", type=float, default=DEFAULT_MIRROR_TOL,
                    help="mirror matching tolerance as a fraction of the bbox diagonal (default 1e-4)")
    ap.add_argument("--allow-noncc0", action="store_true", help="build a non-CC0 kit (bundle_ok false)")
    ap.add_argument("--id", default=None, help="kit id (default: output file name)")
    ap.add_argument("--generated", action="store_true", help="mark the kit as procedurally generated")
    ap.add_argument("--symmetrize", action="store_true",
                    help="snap a mesh that mirror-matches within tolerance to exact symmetry")
    args = ap.parse_args(argv)
    try:
        ann = json.loads(args.annotations.read_text(encoding="utf-8"))
        reg = json.loads(args.regions.read_text(encoding="utf-8")) if args.regions is not None else None
        kit = build_kit(args.obj, ann, args.licence, args.source_sha256, regions=reg, mirror_tol=args.mirror_tol,
                        allow_noncc0=args.allow_noncc0, kit_id=args.id or _default_id(args.out),
                        generated=args.generated, symmetrize=args.symmetrize)
    except BuildRefused as e:
        print(f"build_template_kit: REFUSED: {e}", file=sys.stderr)
        return 2
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(f"build_template_kit: ERROR: {e}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    npz = kit.save(args.out)
    print(json.dumps({"id": kit.id, "out": str(args.out), "arrays": str(npz), "n_verts": kit.n_verts,
                      "n_faces": kit.n_faces, "topology_sha256": kit.topology_sha256, "licence": kit.licence,
                      "bundle_ok": kit.bundle_ok, "schemes": kit.schemes}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
