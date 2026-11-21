#!/usr/bin/env python3
"""Build the MediaPipe Face Landmarker scheme file ``face3d/schemes/mediapipe_478.json``.

Maintainer tool (DESIGN 2.2 layer L9; WP-14).  Stdlib only, plus the
``face3d`` registry for validation; never imported by ``face3d``.

Known fact (DESIGN 3.1, 3.2; *landmark-index-correspondence*): **no MediaPipe
index is verified here**, not even the iris left/right naming.  The scheme is
therefore pure data built from the research tables, every point carries
``verified: false``, and the iris groups take their side from geometry
(:func:`face3d.model.registry.resolve_lr`), never from the index.  The
render-and-detect calibration (``tools/calibrate_scheme.py``, WP-24 M3b) is
what may later flip ``verified`` on the maintainer's machine.

Input: ``research/data/landmark-index-correspondence.json`` tables

* ``mediapipe_semantic_points`` -- candidate index -> anatomical semantics
  (status ``knowledge`` / ``contested`` / ``sourced``);
* ``mediapipe_region_polylines`` -- ordered polylines from the MediaPipe
  connection sets (oval, lips, eyes, brows, nose, irises, midline);
* ``mediapipe_mirror_pairs`` -- 70 (right, left) pairs derived from the polylines;
* ``default_sigma_by_kind`` and ``detector_vs_definition_offsets`` -- copied as
  reference data (mm, estimates; badge 🧠) for the noise model and calibration;
* ``set_sizes`` -- used as a self-check of the polylines (oval 36, lips 40,
  eyes 16 each, brows 10 each, contour union 128, midline 28, 478 points).

Rules (WP-14 spec):

* 478 points, ``index`` 0..477.  Names: the research ``engine_name`` with
  ``_R`` / ``_L`` for semantic points (subject's side), ``iris_a_*`` /
  ``iris_b_*`` for the two iris groups (468-472 / 473-477; letters, not sides),
  ``mp_NNN`` for everything else.
* ``anatomical_id`` from the ``farkas_abbr`` column only when it maps to one of
  :data:`ANATOMICAL_BASES` (prn, sn, ls, li, ch, en, ex, ps, pi, n, g, pg, me,
  sl, al); primes and the "(Farkas gn)" remark are stripped, "~" (approximate)
  and "not ..." entries never map.  ``sto`` is deliberately not mapped: it is
  the mean of two indices (13, 14) when the lips are closed.  The iris centre
  becomes ``p`` only through ``lr_groups`` (``anatomical_id: 'p'`` on the group).
* ``kind`` of a semantic point from its ``type`` column: extremal* -> extremal,
  curve* -> curve, fixed* -> sharp_junction, contour / oval* -> contour,
  gaze_dependent -> iris; rows of region ``brow`` -> brow.  Other points in a
  region polyline get the polyline's kind (oval -> contour, brows -> brow, iris
  rings -> iris, eyes / lips / nose / midline -> curve; precedence contour >
  iris > brow > curve).  All remaining points are ``generic`` (DESIGN 4.4
  "generic dense point", badge 🆕).
* ``side``: ``mid`` for the midline polyline and single-index semantic rows,
  ``geometric`` for the iris groups, R / L from the mirror pairs, semantic
  columns and one-sided polylines, and ``geometric`` (side unknown, to be
  resolved from geometry) for every other point.  No side is guessed.
* ``verified: false`` everywhere; ``badge`` from the research row status
  (verified ✅, sourced 📄, knowledge 🧠, contested ↔️); generic points 🆕.
* ``mirror_pairs`` = the 70 research pairs as ``[right, left]`` with
  ``mirror_complete: false`` (points without a listed partner are not
  mirrored: the flip pass of the detector helper excludes them).
* ``lr_groups``: ``[{indices: 468..472, rule: 'geometric'}, {indices: 473..477,
  rule: 'geometric'}]`` plus a ``provisional_side`` copied from the contested
  research column (R for 468, L for 473).  It is never used to assign a side;
  ``tools/calibrate_scheme.py`` flags a group that sits nearer the other eye.
* ``z_policy: 'ignore'`` (research ``default_sigma_by_kind`` row mediapipe_z:
  "off or very weak"; DESIGN 4.8).
* ``detector``: code Apache-2.0, weights "verify per release (contested)",
  ``commercial_ok: null`` (ethics README licence table; the official model
  card was not retrieved).
* ``licence: 'CC0-1.0'`` for this file, with the note that store acceptance of
  derived index tables is contested (ethics C7).

Output is deterministic (sorted keys, one point per line, UTF-8, ``\\n``), so
rebuilding gives byte-identical files.

Usage::

    python3 tools/build_scheme_mediapipe.py [--research PATH] [--out PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

RESEARCH_REL = "research/data/landmark-index-correspondence.json"
DEFAULT_RESEARCH = REPO / RESEARCH_REL
DEFAULT_OUT = REPO / "face3d" / "schemes" / "mediapipe_478.json"

SCHEME_ID = "mediapipe_478"
#: Total MediaPipe Face Landmarker points (468 mesh + 10 iris; research set_sizes, status verified).
N_POINTS = 478
#: The two iris groups (research mediapipe_region_polylines iris_*_centre_then_ring, contested).
IRIS_GROUPS = (("iris_a", list(range(468, 473))), ("iris_b", list(range(473, 478))))

#: farkas_abbr bases that may become an anatomical id (WP-14 spec).
ANATOMICAL_BASES = ("prn", "sn", "ls", "li", "ch", "en", "ex", "ps", "pi", "n", "g", "pg", "me", "sl", "al")

#: Research status -> badge (DESIGN "Badges").
BADGE = {"verified": "✅", "sourced": "\U0001F4C4", "knowledge": "\U0001F9E0", "contested": "↔️"}
#: Badge of a generic point: the kind 'generic' is the DESIGN 4.4 default for dense points (🆕).
GENERIC_BADGE = "\U0001F195"

#: Kind of the points of each region polyline (WP-14 spec) and their precedence.
POLYLINE_KIND_RULES = (("face_oval", "contour"), ("iris_", "iris"), ("brow_", "brow"), ("eye_", "curve"),
                       ("lip_", "curve"), ("nose_outline_", "curve"), ("midline", "curve"))
KIND_PRECEDENCE = ("contour", "iris", "brow", "curve")

#: Expected set sizes (research set_sizes rows) checked against the polylines.
SET_CHECKS = {
    "FACE_OVAL": ("face_oval",),
    "LIPS": ("lip_upper_outer_R_to_L", "lip_lower_outer_R_to_L", "lip_upper_inner_R_to_L",
             "lip_lower_inner_R_to_L"),
    "RIGHT_EYE": ("eye_R_upper_outer_to_inner", "eye_R_lower_outer_to_inner"),
    "LEFT_EYE": ("eye_L_upper_outer_to_inner", "eye_L_lower_outer_to_inner"),
    "RIGHT_EYEBROW": ("brow_R_upper_outer_to_inner", "brow_R_lower_outer_to_inner"),
    "LEFT_EYEBROW": ("brow_L_upper_outer_to_inner", "brow_L_lower_outer_to_inner"),
    "midline": ("midline_top_to_chin",),
}
UNION_CHECK = ("CONTOURS union", ("FACE_OVAL", "LIPS", "RIGHT_EYE", "LEFT_EYE", "RIGHT_EYEBROW", "LEFT_EYEBROW"))

LICENCE_NOTE = ("This file holds index semantics derived from public descriptions of the Apache-2.0 MediaPipe "
                "connection sets and expert candidates; the project releases it as CC0-1.0. Whether an "
                "extension store accepts bundled derived index tables is contested (ethics C7): if refused, "
                "ship tools/build_scheme_mediapipe.py + tools/calibrate_scheme.py and build the map locally.")
NOTES = ("MediaPipe Face Landmarker 478-point scheme (468 mesh + 10 iris), 0-based. L/R = the subject's side. "
         "NO index is verified (verified=false everywhere, even the iris naming): semantics are research "
         "candidates until the render-and-detect calibration (tools/calibrate_scheme.py) confirms them. "
         "Iris groups are resolved geometrically (lr_groups rule 'geometric'); 'provisional_side' is the "
         "contested research column and is never used to assign a side. Points with side 'geometric' "
         "outside lr_groups have no known side (resolve from the template embedding). mirror_pairs are "
         "[right_index, left_index] and incomplete (mirror_complete=false). MediaPipe z is ignored.")


class BuildError(ValueError):
    """The research tables are inconsistent with the scheme rules."""


# ----------------------------------------------------------------- research input
def _tables(doc: dict) -> dict[str, dict]:
    return {t["name"]: t for t in doc["tables"]}


def _rows(table: dict) -> list[dict[str, Any]]:
    cols = table["columns"]
    return [dict(zip(cols, r)) for r in table["rows"]]


def _badge(status: str) -> str:
    try:
        return BADGE[status]
    except KeyError:
        raise BuildError(f"unknown research status {status!r}") from None


def anatomical_base(farkas_abbr: Any) -> str | None:
    """Map a research ``farkas_abbr`` entry to one of :data:`ANATOMICAL_BASES`, else None.

    ``"g'"`` -> g, ``"n'/se"`` -> n, ``"me' (Farkas gn)"`` -> me, ``"pg'"`` -> pg;
    approximate (``"~p"``, ``"~zy'"``) and negated (``"not tr"``) entries never map.
    """
    if farkas_abbr is None:
        return None
    s = str(farkas_abbr).strip()
    if not s or s.startswith("~") or s.lower().startswith("not"):
        return None
    token = re.split(r"[\s/(]", s, maxsplit=1)[0].replace("'", "").replace("′", "")
    return token if token in ANATOMICAL_BASES else None


def semantic_kind(row: dict[str, Any]) -> str:
    """Scheme kind of a ``mediapipe_semantic_points`` row (WP-14 spec mapping)."""
    typ = str(row["type"])
    if row["region"] == "brow":
        return "brow"
    if typ == "gaze_dependent":
        return "iris"
    if typ.startswith("extremal"):
        return "extremal"
    if typ.startswith("curve"):
        return "curve"
    if typ.startswith("fixed"):
        return "sharp_junction"
    if typ.startswith("contour") or typ.startswith("oval"):
        return "contour"
    raise BuildError(f"semantic point {row['engine_name']!r}: unknown type {typ!r}")


def polyline_kind(name: str) -> str:
    for prefix, kind in POLYLINE_KIND_RULES:
        if name.startswith(prefix):
            return kind
    raise BuildError(f"polyline {name!r} has no kind rule")


def _parse_mp_indices(text: str) -> list[int]:
    """``'MP 133/362; iBUG 39/42'`` -> [133, 362]; ``'MP 1 (4)'`` -> [1, 4]."""
    m = re.search(r"MP\s+([^;]*)", text)
    return [int(x) for x in re.findall(r"\d+", m.group(1))] if m else []


# ----------------------------------------------------------------- build
def build(research_path: Path = DEFAULT_RESEARCH, source_rel: str = RESEARCH_REL) -> dict[str, Any]:
    """Return the scheme document (plain containers); raises :class:`BuildError` on inconsistent tables."""
    raw = Path(research_path).read_bytes()
    T = _tables(json.loads(raw.decode("utf-8")))
    sem = _rows(T["mediapipe_semantic_points"])
    polys = _rows(T["mediapipe_region_polylines"])
    pairs = [(int(r["right_index"]), int(r["left_index"])) for r in _rows(T["mediapipe_mirror_pairs"])]
    sigma_rows = _rows(T["default_sigma_by_kind"])
    offset_rows = _rows(T["detector_vs_definition_offsets"])
    set_sizes = {r["set"]: int(r["n_unique_points"]) for r in _rows(T["set_sizes"])}

    if set_sizes.get("total with iris") != N_POINTS:
        raise BuildError(f"research set_sizes 'total with iris' is {set_sizes.get('total with iris')}, not {N_POINTS}")
    n = N_POINTS
    iris_idx = {i for _, g in IRIS_GROUPS for i in g}

    # ---- polyline self-checks against set_sizes
    poly_by_name = {p["polyline"]: p for p in polys}
    sets: dict[str, set[int]] = {}
    for key, names in SET_CHECKS.items():
        s: set[int] = set()
        for nm in names:
            if nm not in poly_by_name:
                raise BuildError(f"polyline {nm!r} missing from the research table")
            s.update(int(i) for i in poly_by_name[nm]["indices"])
        if len(s) != set_sizes[key]:
            raise BuildError(f"set {key}: {len(s)} unique indices, research set_sizes says {set_sizes[key]}")
        sets[key] = s
    union = set().union(*(sets[k] for k in UNION_CHECK[1]))
    if len(union) != set_sizes[UNION_CHECK[0]]:
        raise BuildError(f"contour union has {len(union)} indices, research says {set_sizes[UNION_CHECK[0]]}")
    for p in polys:
        idx = [int(i) for i in p["indices"]]
        if len(idx) != int(p["n"]) or any(not 0 <= i < n for i in idx):
            raise BuildError(f"polyline {p['polyline']!r}: bad length or index out of range")
    midline = {int(i) for i in poly_by_name["midline_top_to_chin"]["indices"]}

    # ---- per-point attributes
    name: dict[int, str] = {}
    anat: dict[int, str | None] = {}
    kind: dict[int, str] = {}
    side: dict[int, str] = {}
    badge: dict[int, str] = {}
    semantics = []

    def set_side(i: int, s: str, why: str) -> None:
        if i in side and side[i] != s:
            raise BuildError(f"index {i}: side {s!r} from {why} conflicts with {side[i]!r}")
        side[i] = s

    for r in sem:
        ir, il = r["mp_right_or_mid"], r["mp_left"]
        k = semantic_kind(r)
        b = _badge(r["status"])
        base = anatomical_base(r["farkas_abbr"])
        entry = {"engine_name": r["engine_name"], "farkas_abbr": r["farkas_abbr"], "region": r["region"],
                 "type": r["type"], "kind": k, "status": r["status"], "badge": b,
                 "alternates": [int(a) for a in r["alternates"]], "notes": r["notes"]}
        if il is None:  # midline row
            i = int(ir)
            name[i], kind[i], badge[i] = r["engine_name"], k, b
            anat[i] = base
            set_side(i, "mid", "semantic midline row")
            entry.update({"index": i, "index_R": None, "index_L": None, "anatomical_id": base})
        else:
            ir, il = int(ir), int(il)
            entry.update({"index": None, "index_R": ir, "index_L": il})
            if ir in iris_idx or il in iris_idx:
                # iris centre: never side-named; p only through lr_groups
                entry.update({"anatomical_id": None, "anatomical_id_via_lr_groups": "p"})
                for i in (ir, il):
                    kind[i], badge[i] = k, b
                    anat[i] = None
                continue
            for i, sd in ((ir, "R"), (il, "L")):
                name[i], kind[i], badge[i] = f"{r['engine_name']}_{sd}", k, b
                anat[i] = None if base is None else f"{base}_{sd}"
                set_side(i, sd, "semantic row")
            entry["anatomical_id"] = None if base is None else f"{base}_L/{base}_R"
        semantics.append(entry)

    # iris groups: names, side geometric, kind iris
    lr_groups = []
    iris_rows = {p["polyline"]: p for p in polys if p["polyline"].startswith("iris_")}
    iris_status = {tuple(int(i) for i in p["indices"]): p["status"] for p in iris_rows.values()}
    for (gname, idx), prov in zip(IRIS_GROUPS, ("R", "L")):
        status = iris_status.get(tuple(idx))
        if status is None:
            raise BuildError(f"iris group {gname} {idx} is not a research polyline")
        for j, i in enumerate(idx):
            name[i] = f"{gname}_centre" if j == 0 else f"{gname}_ring{j}"
            kind[i] = "iris"
            badge.setdefault(i, _badge(status))
            anat[i] = None
            set_side(i, "geometric", "iris group")
        lr_groups.append({
            "name": gname, "indices": list(idx), "rule": "geometric", "centre_index": idx[0],
            "anatomical_id": "p", "provisional_side": prov,
            "provisional_note": ("contested research column (mp_right_or_mid / mp_left of iris_centre); "
                                 "never used to assign a side; calibration flags a group nearer the other eye"),
            "badge": _badge(status),
        })

    # region polylines: kind / side / badge for the remaining points
    poly_kind: dict[int, str] = {}
    poly_badge: dict[int, str] = {}
    for p in polys:
        pk = polyline_kind(p["polyline"])
        pb = _badge(p["status"])
        for i in (int(x) for x in p["indices"]):
            old = poly_kind.get(i)
            if old is None or KIND_PRECEDENCE.index(pk) < KIND_PRECEDENCE.index(old):
                poly_kind[i] = pk
                poly_badge[i] = pb
            if p["side"] == "mid":
                set_side(i, "mid", f"polyline {p['polyline']}")
    for p in polys:
        if p["side"] in ("R", "L"):
            for i in (int(x) for x in p["indices"]):
                if i not in midline and i not in iris_idx:
                    set_side(i, p["side"], f"polyline {p['polyline']}")

    # mirror pairs
    seen: set[int] = set()
    for a, b in pairs:
        if a in seen or b in seen or a == b:
            raise BuildError(f"mirror pair ({a}, {b}) repeats an index")
        seen.update((a, b))
        if a in iris_idx or b in iris_idx:
            if not (a in iris_idx and b in iris_idx):
                raise BuildError(f"mirror pair ({a}, {b}) mixes an iris and a mesh point")
            continue
        if a in midline or b in midline:
            raise BuildError(f"mirror pair ({a}, {b}) contains a midline point")
        set_side(a, "R", "mirror pair right_index")
        set_side(b, "L", "mirror pair left_index")
    for e in semantics:
        if e["index_R"] is not None and (e["index_R"], e["index_L"]) not in set(pairs):
            raise BuildError(f"semantic pair {e['engine_name']} ({e['index_R']}, {e['index_L']}) is not a mirror pair")

    points = []
    for i in range(n):
        k = kind.get(i, poly_kind.get(i, "generic"))
        points.append({
            "index": i,
            "name": name.get(i, f"mp_{i:03d}"),
            "anatomical_id": anat.get(i),
            "kind": k,
            "side": side.get(i, "geometric"),
            "verified": False,
            "badge": badge.get(i, poly_badge.get(i, GENERIC_BADGE)),
        })

    polylines = {p["polyline"]: {"indices": [int(i) for i in p["indices"]], "closed": bool(p["closed"]),
                                 "side": p["side"], "kind": polyline_kind(p["polyline"]),
                                 "status": p["status"], "badge": _badge(p["status"])} for p in polys}

    offsets = []
    for r in offset_rows:
        offsets.append({"point": r["point"], "mp_indices": _parse_mp_indices(str(r["detector_indices"])),
                        "offset_min_mm": r["offset_min_mm"], "offset_max_mm": r["offset_max_mm"],
                        "direction": r["direction"], "mechanism": r["mechanism"], "pin_or_slide": r["pin_or_slide"],
                        "status": r["status"], "badge": _badge(r["status"])})
    sigma_by_kind = {r["kind"]: {"examples": r["examples"], "sigma_normal_min_mm": r["sigma_normal_min"],
                                 "sigma_normal_max_mm": r["sigma_normal_max"], "sigma_tangent_mm": r["sigma_tangent"],
                                 "residual": r["residual"]} for r in sigma_rows}

    doc = {
        "format": "face3d.scheme",
        "version": 1,
        "licence": "CC0-1.0",
        "licence_note": LICENCE_NOTE,
        "scheme": SCHEME_ID,
        "n": n,
        "notes": NOTES,
        "detector": {"backend": "mediapipe-tasks", "model": "face_landmarker .task (user-supplied, SHA-256 pinned)",
                     "code_licence": "Apache-2.0", "weights_licence": "verify per release (contested)",
                     "commercial_ok": None, "is_ml": True},
        "source": {"path": source_rel, "sha256": hashlib.sha256(raw).hexdigest(),
                   "tables": ["mediapipe_semantic_points", "mediapipe_region_polylines", "mediapipe_mirror_pairs",
                              "default_sigma_by_kind", "detector_vs_definition_offsets", "set_sizes"],
                   "tool": "tools/build_scheme_mediapipe.py"},
        "points": points,
        "polylines": polylines,
        "mirror_pairs": [[a, b] for a, b in pairs],
        "mirror_complete": False,
        "lr_groups": lr_groups,
        "z_policy": "ignore",
        "semantics": semantics,
        "definition_offsets": {"units": "mm (estimates or derived bounds, not measurements; research "
                                        "detector_vs_definition_offsets)", "rows": offsets},
        "sigma_by_kind": {"units": "mm (research default_sigma_by_kind, design defaults, badge \U0001F9E0)",
                          "rows": sigma_by_kind},
    }
    _validate(doc)
    return doc


def _validate(doc: dict[str, Any]) -> None:
    """Load the document through the engine's scheme loader and check the involution."""
    from face3d.model.registry import Scheme

    sch = Scheme(doc)
    pi = sch.mirror_permutation()
    if sch.n != N_POINTS or len(pi) != N_POINTS:
        raise BuildError("scheme size mismatch")
    if any(p.verified for p in sch.points):
        raise BuildError("no MediaPipe index may be verified by this tool")


# ----------------------------------------------------------------- deterministic JSON
def _flat(v: Any) -> bool:
    if isinstance(v, dict):
        return all(not isinstance(x, (dict, list)) or (isinstance(x, list) and all(
            not isinstance(y, (dict, list)) for y in x)) for x in v.values())
    if isinstance(v, list):
        return all(not isinstance(x, (dict, list)) for x in v)
    return True


def dumps(obj: Any, indent: int = 0) -> str:
    """Deterministic JSON: sorted keys; flat dicts and scalar lists on one line."""
    pad = " " * indent
    if isinstance(obj, (dict, list)) and _flat(obj) and (not isinstance(obj, dict) or len(json.dumps(
            obj, ensure_ascii=False)) <= 400):
        return json.dumps(obj, ensure_ascii=False, sort_keys=True)
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        items = [f"{pad} {json.dumps(str(k), ensure_ascii=False)}: {dumps(obj[k], indent + 1)}" for k in sorted(obj)]
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"
    if isinstance(obj, list):
        if not obj:
            return "[]"
        items = [pad + " " + dumps(v, indent + 1) for v in obj]
        return "[\n" + ",\n".join(items) + "\n" + pad + "]"
    return json.dumps(obj, ensure_ascii=False)


def write(doc: dict[str, Any], out: Path) -> bytes:
    data = (dumps(doc) + "\n").encode("utf-8")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return data


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--research", type=Path, default=DEFAULT_RESEARCH, help=f"research JSON (default {RESEARCH_REL})")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output (default face3d/schemes/mediapipe_478.json)")
    args = ap.parse_args(argv)
    try:
        doc = build(args.research)
    except BuildError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    data = write(doc, args.out)
    print(f"wrote {args.out} ({len(data)} bytes, sha256 {hashlib.sha256(data).hexdigest()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
