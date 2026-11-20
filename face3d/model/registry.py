"""Anatomical landmark registry, landmark scheme files and geometric L/R resolution.

Implements DESIGN 3.1 (conventions), 3.2 (scheme file format), 4.4 (sigma in mm by
landmark kind), 4.9 (jaw weights), 4.11 (symmetry sigmas) and 4.6 (gauge anchors)
for the 44 metric landmarks of the research note *metric-3d-landmark-reference*
(table ``landmark_definitions``; the same ids and order as the packaged prior
``face3d/data/landmark_prior_v1.json``).

Conventions
-----------
* Ids: the 14 midline ids ``v tr g n prn sn ls sto li sl pg gn me op`` followed by
  the 15 bilateral bases ``t or p en ex ps pi al ac ch zy go sa sba eu``, each as
  ``<base>_L`` then ``<base>_R`` (44 ids).
* ``L``/``R`` is always the **subject's** side (anat R1.2): ``_L`` has +x in the
  head frame (mm; +x subject's left, +y up, +z out of the face), which is the
  viewer's right in a non-mirrored frontal photo.
* Image coordinates are continuous pixels with the origin at the top-left corner
  (DESIGN 3.1); ``u`` grows to the right.
* All sigmas are millimetres.  Every numeric default below is provisional
  (badge 🧠 unless noted) and cites its source; none is measured here.

Scheme files
------------
``face3d/schemes/<id>.json`` (DESIGN 3.2)::

    {format: 'face3d.scheme', version: 1, licence, scheme, n,
     points: [{index, name, anatomical_id|null, kind, side, verified, badge}],
     polylines: {}, mirror_pairs: [[a, b], ...], lr_groups: [{indices, rule: 'geometric'}],
     z_policy: 'ignore'}

``kind`` is one of :data:`SCHEME_KINDS`, ``side`` one of :data:`SIDES`.  Points with
``verified: false`` are not trusted as anatomical landmarks (DESIGN 3.2).  Groups
with ``rule: 'geometric'`` never take their side from the index; it is assigned
from geometry by :func:`resolve_lr` (DESIGN 3.1, MediaPipe iris ↔️).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

__all__ = [
    "MIDLINE_BASES", "BILATERAL_BASES", "ANATOMICAL_IDS", "BASE_NAMES", "KIND_SIGMA_MM",
    "SCHEME_KINDS", "SIDES", "Landmark", "ANATOMICAL", "landmark_base", "anchor_ids",
    "SchemePoint", "Scheme", "load_scheme", "resolve_lr", "SCHEME_DIR",
]

# --------------------------------------------------------------------------- ids
#: Midline bases in the order of the research table mean_landmarks_* (metric-3d-landmark-reference).
MIDLINE_BASES: tuple[str, ...] = ("v", "tr", "g", "n", "prn", "sn", "ls", "sto", "li", "sl", "pg", "gn", "me", "op")
#: Bilateral bases in the same order; each expands to ``_L`` then ``_R``.
BILATERAL_BASES: tuple[str, ...] = ("t", "or", "p", "en", "ex", "ps", "pi", "al", "ac", "ch", "zy", "go",
                                    "sa", "sba", "eu")
#: The 44 anatomical ids in prior order (row i of the prior mean is ANATOMICAL_IDS[i]).
ANATOMICAL_IDS: tuple[str, ...] = MIDLINE_BASES + tuple(b + s for b in BILATERAL_BASES for s in ("_L", "_R"))

#: Base names, from the research table landmark_definitions (metric-3d-landmark-reference).
BASE_NAMES: dict[str, str] = {
    "v": "vertex", "tr": "trichion", "g": "glabella", "n": "nasion", "prn": "pronasale",
    "sn": "subnasale", "ls": "labrale_superius", "sto": "stomion", "li": "labrale_inferius",
    "sl": "sublabiale", "pg": "pogonion", "gn": "gnathion", "me": "menton", "op": "opisthocranion",
    "t": "tragion", "or": "orbitale", "p": "pupil", "en": "endocanthion", "ex": "exocanthion",
    "ps": "palpebrale_superius", "pi": "palpebrale_inferius", "al": "alare", "ac": "alar_curvature",
    "ch": "cheilion", "zy": "zygion", "go": "gonion", "sa": "superaurale", "sba": "subaurale",
    "eu": "euryon",
}

#: Every kind a scheme point may carry (DESIGN 3.2).
SCHEME_KINDS: tuple[str, ...] = ("sharp_junction", "extremal", "curve", "contour", "brow", "iris", "hair", "generic")
#: Every side a scheme point may carry (DESIGN 3.2); 'geometric' = resolved by resolve_lr.
SIDES: tuple[str, ...] = ("L", "R", "mid", "geometric")

# ----------------------------------------------------------------- kind tables
_KIND_OF: dict[str, str] = {}
for _b in ("en", "ex", "ch", "sn", "sto", "ac"):
    _KIND_OF[_b] = "sharp_junction"
for _b in ("prn", "pg", "me", "gn", "g", "zy", "go", "v", "op", "eu", "t", "sa", "sba", "al", "or"):
    _KIND_OF[_b] = "extremal"
for _b in ("ls", "li", "ps", "pi", "n", "sl"):
    _KIND_OF[_b] = "curve"
_KIND_OF["p"] = "iris"
_KIND_OF["tr"] = "hair"

#: (sigma_normal, sigma_tangent, sigma_def) in mm per anatomical kind.
#: DESIGN 4.4 table (anat R4.1; *landmark-index-correspondence*; badge 🧠); the iris
#: definition bias 0.0 follows DESIGN 4.4 ("—": the iris centre is never a shape
#: landmark), and 'hair' (trichion) 4.0 / 8.0 / 3.0 is the WP-03 value (🆕, provisional).
KIND_SIGMA_MM: dict[str, tuple[float, float, float]] = {
    "sharp_junction": (1.25, 1.25, 0.5),
    "extremal": (2.0, 3.0, 1.5),
    "curve": (1.5, 7.5, 1.0),
    "iris": (0.6, 0.6, 0.0),
    "hair": (4.0, 8.0, 3.0),
}
#: Per-base sigma_def overrides: soft-tissue orbitale is palpation-defined (WP-03; 🧠).
_SIGMA_DEF_OVERRIDE: dict[str, float] = {"or": 2.0}

_REGION_OF: dict[str, str] = {}
for _region, _bases in (
        ("eyes", ("en", "ex", "ps", "pi", "p")), ("nose", ("n", "prn", "sn", "al", "ac")),
        ("lips", ("ls", "sto", "li", "ch")), ("chin", ("pg", "gn", "me", "sl")), ("jaw", ("go",)),
        ("cheeks", ("zy", "or")), ("forehead", ("g", "tr")), ("ears", ("t", "sa", "sba")),
        ("cranium", ("v", "op", "eu"))):
    for _b in _bases:
        _REGION_OF[_b] = _region

# Expression classes for covariance inflation (DESIGN 4.9; [Rob 3.6] 🧠).
_EXPR_OF: dict[str, str] = {}
for _cls, _bases in (
        ("rigid", ("n", "g", "en", "ex", "t", "or", "zy", "eu", "op", "v", "tr", "p", "sa", "sba")),
        ("semi_mobile", ("prn", "al", "ac", "sn", "ps", "pi", "go")),
        ("mobile", ("ls", "sto", "li", "ch", "sl")),
        ("jaw", ("pg", "gn", "me"))):
    for _b in _bases:
        _EXPR_OF[_b] = _cls

#: Jaw-hinge weights omega_i (DESIGN 4.9: me, gn, pg, sl, li 1.0; sto 0.5; ch 0.4; go 1.0; others 0; bl K8 ↔️).
_JAW_WEIGHT: dict[str, float] = {"me": 1.0, "gn": 1.0, "pg": 1.0, "sl": 1.0, "li": 1.0, "go": 1.0,
                                 "sto": 0.5, "ch": 0.4}

#: Per-pair symmetry sigma (mm, equal on x, y, z) on d = X_l - M X_r (DESIGN 4.11; anat R4.2 🧠 provisional).
_SYM_SIGMA: dict[str, float] = {}
for _s, _bases in ((0.85, ("en", "ex", "ps", "pi", "p")), (1.25, ("al", "ac", "or", "zy")),
                   (1.75, ("ch",)), (2.75, ("go",)), (3.5, ("t", "sa", "sba", "eu"))):
    for _b in _bases:
        _SYM_SIGMA[_b] = _s

#: Midline x sigma (mm; DESIGN 4.11; anat R4.2 🧠): n, g 0.9; prn, sn 1.75; pg, me, gn 2.5; others 2.0.
_MIDLINE_SIGMA: dict[str, float] = {"n": 0.9, "g": 0.9, "prn": 1.75, "sn": 1.75, "pg": 2.5, "me": 2.5, "gn": 2.5}
_MIDLINE_SIGMA_DEFAULT = 2.0

#: Gauge anchors (DESIGN 4.6): well-observed landmarks that fix rotation and translation.
_ANCHOR_BASES: frozenset[str] = frozenset({"en", "ex", "p", "n", "prn", "sn", "ch", "ls", "li", "sto"})


@dataclass(frozen=True)
class Landmark:
    """One of the 44 anatomical landmarks (all lengths in mm).

    ``sigma_n_mm`` / ``sigma_t_mm`` are the across / along-curve definition
    sigmas used by the noise model (DESIGN 4.4), ``sigma_def_mm`` the shared
    definition bias floor (DESIGN D-06).  ``sym_sigma_mm`` is the per-axis (x, y, z)
    symmetry sigma of a bilateral landmark (None on the midline); ``midline_sigma_mm``
    the x sigma of a midline landmark (None for bilateral ones).
    """

    id: str
    name: str
    base: str
    side: str
    mirror_id: str
    kind: str
    region: str
    expr_class: str
    jaw_weight: float
    sigma_n_mm: float
    sigma_t_mm: float
    sigma_def_mm: float
    sym_sigma_mm: tuple[float, float, float] | None
    midline_sigma_mm: float | None
    is_anchor: bool

    @property
    def bilateral(self) -> bool:
        return self.side in ("L", "R")


def landmark_base(landmark_id: str) -> str:
    """``'en_L'`` -> ``'en'``; midline ids are their own base."""
    return landmark_id[:-2] if landmark_id.endswith(("_L", "_R")) else landmark_id


def _make_landmark(lid: str) -> Landmark:
    b = landmark_base(lid)
    side = "L" if lid.endswith("_L") else ("R" if lid.endswith("_R") else "mid")
    mirror = (b + "_R") if side == "L" else ((b + "_L") if side == "R" else lid)
    kind = _KIND_OF[b]
    sn, st, sdef = KIND_SIGMA_MM[kind]
    sdef = _SIGMA_DEF_OVERRIDE.get(b, sdef)
    if side == "mid":
        sym, mid_sigma = None, _MIDLINE_SIGMA.get(b, _MIDLINE_SIGMA_DEFAULT)
    else:
        s = _SYM_SIGMA[b]
        sym, mid_sigma = (s, s, s), None
    name = BASE_NAMES[b] + ("" if side == "mid" else "_" + side)
    return Landmark(id=lid, name=name, base=b, side=side, mirror_id=mirror, kind=kind,
                    region=_REGION_OF[b], expr_class=_EXPR_OF[b], jaw_weight=_JAW_WEIGHT.get(b, 0.0),
                    sigma_n_mm=sn, sigma_t_mm=st, sigma_def_mm=sdef, sym_sigma_mm=sym,
                    midline_sigma_mm=mid_sigma, is_anchor=b in _ANCHOR_BASES)


#: id -> Landmark for the 44 anatomical ids, in prior order.
ANATOMICAL: dict[str, Landmark] = {lid: _make_landmark(lid) for lid in ANATOMICAL_IDS}


def anchor_ids() -> list[str]:
    """The gauge-anchor ids (DESIGN 4.6) in prior order."""
    return [lid for lid, lm in ANATOMICAL.items() if lm.is_anchor]


# --------------------------------------------------------------------- schemes
#: Package directory holding the scheme JSON files.
SCHEME_DIR = Path(__file__).resolve().parents[1] / "schemes"


@dataclass(frozen=True)
class SchemePoint:
    """One point of a landmark scheme (see the module docstring for the fields)."""

    index: int
    name: str
    anatomical_id: str | None
    kind: str
    side: str
    verified: bool
    badge: str


class Scheme:
    """A landmark scheme loaded from ``face3d/schemes/<id>.json`` (DESIGN 3.2).

    The constructor validates the structure (format, version, ``n``, contiguous
    indices, unique names and anatomical ids, known kinds and sides, side agreement
    with the registry).  :meth:`mirror_permutation` validates the mirror pairs.
    """

    def __init__(self, doc: Mapping[str, Any], path: str | Path | None = None):
        if doc.get("format") != "face3d.scheme":
            raise ValueError(f"not a face3d.scheme document (format={doc.get('format')!r})")
        if int(doc.get("version", -1)) != 1:
            raise ValueError(f"unsupported scheme version {doc.get('version')!r}")
        self.path = Path(path) if path is not None else None
        self.scheme: str = str(doc["scheme"])
        self.n: int = int(doc["n"])
        self.licence: str | None = doc.get("licence")
        self.notes: str | None = doc.get("notes")
        self.polylines: dict[str, list[int]] = {k: [int(i) for i in v] for k, v in dict(doc.get("polylines", {})).items()}
        self.z_policy: str = str(doc.get("z_policy", "ignore"))
        self.raw: dict[str, Any] = dict(doc)
        pts = []
        for k, p in enumerate(doc["points"]):
            sp = SchemePoint(index=int(p["index"]), name=str(p["name"]),
                             anatomical_id=None if p.get("anatomical_id") is None else str(p["anatomical_id"]),
                             kind=str(p["kind"]), side=str(p["side"]), verified=bool(p["verified"]),
                             badge=str(p.get("badge", "")))
            if sp.index != k:
                raise ValueError(f"scheme {self.scheme}: point {k} has index {sp.index} (indices must be 0..n-1 in order)")
            if sp.kind not in SCHEME_KINDS:
                raise ValueError(f"scheme {self.scheme}: point {sp.name!r} has unknown kind {sp.kind!r}")
            if sp.side not in SIDES:
                raise ValueError(f"scheme {self.scheme}: point {sp.name!r} has unknown side {sp.side!r}")
            if sp.anatomical_id is not None:
                lm = ANATOMICAL.get(sp.anatomical_id)
                if lm is None:
                    raise ValueError(f"scheme {self.scheme}: point {sp.name!r} maps to unknown anatomical id "
                                     f"{sp.anatomical_id!r}")
                if sp.side != "geometric" and sp.side != lm.side:
                    raise ValueError(f"scheme {self.scheme}: point {sp.name!r} has side {sp.side!r} but "
                                     f"{sp.anatomical_id!r} is side {lm.side!r}")
            pts.append(sp)
        if len(pts) != self.n:
            raise ValueError(f"scheme {self.scheme}: n={self.n} but {len(pts)} points listed")
        names = [p.name for p in pts]
        if len(set(names)) != len(names):
            dup = sorted({x for x in names if names.count(x) > 1})
            raise ValueError(f"scheme {self.scheme}: duplicate point names {dup}")
        aids = [p.anatomical_id for p in pts if p.anatomical_id is not None]
        if len(set(aids)) != len(aids):
            dup = sorted({x for x in aids if aids.count(x) > 1})
            raise ValueError(f"scheme {self.scheme}: anatomical ids mapped twice {dup}")
        self.points: list[SchemePoint] = pts
        mp = doc.get("mirror_pairs", [])
        if isinstance(mp, str):
            # DESIGN 3.2 allows "computed"; a loader cannot compute pairs without geometry.
            raise ValueError(f"scheme {self.scheme}: mirror_pairs {mp!r} must be expanded to explicit index "
                             "pairs by the scheme build tool before loading")
        self.mirror_pairs: list[tuple[int, int]] = []
        for pair in mp:
            if len(pair) != 2:
                raise ValueError(f"scheme {self.scheme}: mirror pair {pair!r} is not a pair")
            self.mirror_pairs.append((int(pair[0]), int(pair[1])))
        self.lr_groups: list[dict[str, Any]] = []
        for g in doc.get("lr_groups", []):
            idx = [int(i) for i in g["indices"]]
            if any(i < 0 or i >= self.n for i in idx):
                raise ValueError(f"scheme {self.scheme}: lr_group index out of range in {idx}")
            if g.get("rule", "geometric") != "geometric":
                raise ValueError(f"scheme {self.scheme}: unknown lr_group rule {g.get('rule')!r}")
            gg = dict(g)
            gg["indices"] = idx
            gg["rule"] = "geometric"
            self.lr_groups.append(gg)

    # ------------------------------------------------------------- accessors
    @classmethod
    def from_file(cls, path: str | Path) -> "Scheme":
        path = Path(path)
        return cls(json.loads(path.read_text(encoding="utf-8")), path=path)

    def names(self) -> list[str]:
        return [p.name for p in self.points]

    def kinds(self) -> list[str]:
        return [p.kind for p in self.points]

    def sides(self) -> list[str]:
        return [p.side for p in self.points]

    def index_of(self, name: str) -> int:
        for p in self.points:
            if p.name == name:
                return p.index
        raise KeyError(f"scheme {self.scheme} has no point named {name!r}")

    def anatomical_index(self) -> dict[str, int]:
        """{anatomical_id: point index} for every point with an anatomical id."""
        return {p.anatomical_id: p.index for p in self.points if p.anatomical_id is not None}

    def mirror_permutation(self) -> np.ndarray:
        """Label permutation pi of a horizontal flip (DESIGN 3.1): pairs swapped, others fixed.

        Validates that every pair joins two distinct in-range points with sides
        (L, R) or (geometric, geometric), that no point is in two pairs, that
        midline ('mid') points are fixed and that pi[pi] is the identity.  Raises
        ``ValueError`` otherwise.
        """
        pi = np.arange(self.n, dtype=np.int64)
        seen: set[int] = set()
        for a, b in self.mirror_pairs:
            for i in (a, b):
                if i < 0 or i >= self.n:
                    raise ValueError(f"scheme {self.scheme}: mirror pair ({a}, {b}) index out of range")
            if a == b:
                raise ValueError(f"scheme {self.scheme}: mirror pair ({a}, {b}) maps a point to itself")
            if a in seen or b in seen:
                raise ValueError(f"scheme {self.scheme}: point in more than one mirror pair: ({a}, {b})")
            seen.update((a, b))
            sa, sb = self.points[a].side, self.points[b].side
            if "mid" in (sa, sb):
                raise ValueError(f"scheme {self.scheme}: midline point in mirror pair "
                                 f"({self.points[a].name}, {self.points[b].name})")
            if {sa, sb} != {"L", "R"} and not (sa == sb == "geometric"):
                raise ValueError(f"scheme {self.scheme}: mirror pair ({self.points[a].name}, {self.points[b].name}) "
                                 f"has sides ({sa}, {sb}); expected one L and one R")
            pi[a], pi[b] = b, a
        if not np.array_equal(pi[pi], np.arange(self.n)):
            raise ValueError(f"scheme {self.scheme}: mirror permutation is not an involution")
        mid = [p.index for p in self.points if p.side == "mid"]
        if mid and not np.array_equal(pi[mid], mid):
            raise ValueError(f"scheme {self.scheme}: midline points are not fixed by the mirror permutation")
        return pi

    def to_dict(self) -> dict[str, Any]:
        out = dict(self.raw)
        out["points"] = [{"index": p.index, "name": p.name, "anatomical_id": p.anatomical_id, "kind": p.kind,
                          "side": p.side, "verified": p.verified, "badge": p.badge} for p in self.points]
        out["mirror_pairs"] = [list(p) for p in self.mirror_pairs]
        out["lr_groups"] = [dict(g) for g in self.lr_groups]
        return out

    def __repr__(self) -> str:
        return f"Scheme({self.scheme!r}, n={self.n})"


def load_scheme(name: str, path: str | Path | None = None) -> Scheme:
    """Load scheme ``name`` from the package (``face3d/schemes/<name>.json``).

    ``path`` may be a directory holding ``<name>.json`` or the JSON file itself.
    The document's ``scheme`` field must equal ``name``.
    """
    if path is None:
        file = SCHEME_DIR / f"{name}.json"
    else:
        p = Path(path)
        file = p / f"{name}.json" if p.is_dir() else p
    if not file.is_file():
        raise FileNotFoundError(f"scheme file not found: {file}")
    sch = Scheme.from_file(file)
    if sch.scheme != name:
        raise ValueError(f"{file} holds scheme {sch.scheme!r}, not {name!r}")
    return sch


# ------------------------------------------------------------------ L/R by geometry
#: Distance-ratio threshold (far / near projected eye centre) below which a group's
#: side is ambiguous (WP-03; 🆕 provisional).
LR_RATIO_MIN = 1.5
#: Minimum horizontal separation (px) of two groups for the camera-free rule (WP-03; 🆕).
LR_MIN_DU_PX = 2.0


def _centroid(uv: Any, key: str) -> np.ndarray:
    a = np.asarray(uv, float).reshape(-1, 2)
    ok = np.all(np.isfinite(a), axis=1)
    if not ok.any():
        raise ValueError(f"lr group {key!r} has no finite points")
    return a[ok].mean(axis=0)


def resolve_lr(groups_uv: Mapping[str, Any], *, camera: Any = None,
               eye_centres_world: Mapping[str, Any] | None = None, image_mirrored: bool = False,
               face_midline_u: float | None = None) -> tuple[dict[str, str], bool]:
    """Assign geometric L/R groups (e.g. the two MediaPipe iris rings) to the subject's sides.

    Parameters
    ----------
    groups_uv:
        ``{group_key: (n, 2) pixel coordinates}`` (one or two groups; NaN rows ignored).
    camera, eye_centres_world:
        Given together: a camera with ``project((k, 3)) -> (k, 2)`` (``face3d.geometry.camera.Camera``)
        and the subject's eye centres ``{'L': (3,), 'R': (3,)}`` in the head frame (mm).
        Each group goes to the nearer projected eye centre (centroid distance); the
        result is ambiguous when both groups pick the same eye or a group's distance
        ratio far/near is below :data:`LR_RATIO_MIN` (1.5).  With ``image_mirrored`` the
        projected centres are reflected ``u' = W - u`` (``W = camera.width``, DESIGN 3.1).
    face_midline_u:
        Camera-free rule: in a non-mirrored image the subject-left group has the
        larger mean ``u`` relative to ``face_midline_u`` (subject left = viewer right);
        ``image_mirrored`` swaps the sides.  Ambiguous when the groups are less than
        :data:`LR_MIN_DU_PX` (2 px) apart in ``u``, or, when ``face_midline_u`` is given,
        when they do not straddle it.  One group alone needs ``face_midline_u``.

    Returns
    -------
    (assignment, ambiguous): ``{group_key: 'L' | 'R'}`` (a best guess even when
    ambiguous) and the ambiguity flag.  The caller asks the user when ambiguous;
    scheme indices never decide the side (DESIGN 3.1).
    """
    keys = list(groups_uv)
    if not 1 <= len(keys) <= 2:
        raise ValueError(f"resolve_lr expects one or two groups, got {len(keys)}")
    cents = {k: _centroid(groups_uv[k], k) for k in keys}
    if (camera is None) != (eye_centres_world is None):
        raise ValueError("camera and eye_centres_world must be given together")

    if camera is not None:
        E = np.array([np.asarray(eye_centres_world["L"], float).reshape(3),
                      np.asarray(eye_centres_world["R"], float).reshape(3)])
        P = np.asarray(camera.project(E), float).reshape(2, 2)
        if image_mirrored:
            width = getattr(camera, "width", None)
            if width is None:
                raise ValueError("image_mirrored with a camera needs camera.width")
            P[:, 0] = float(width) - P[:, 0]
        d = {k: (float(np.linalg.norm(cents[k] - P[0])), float(np.linalg.norm(cents[k] - P[1]))) for k in keys}
        pick = {k: ("L" if d[k][0] <= d[k][1] else "R") for k in keys}

        def ratio(k: str) -> float:
            lo, hi = min(d[k]), max(d[k])
            return float("inf") if lo == 0.0 else hi / lo

        ambiguous = any(ratio(k) < LR_RATIO_MIN for k in keys)
        if len(keys) == 1:
            return pick, ambiguous
        a, b = keys
        if pick[a] == pick[b]:
            ambiguous = True
            # best joint assignment: minimise the summed distance over the two permutations
            if d[a][0] + d[b][1] <= d[a][1] + d[b][0]:
                pick = {a: "L", b: "R"}
            else:
                pick = {a: "R", b: "L"}
        return pick, ambiguous

    # camera-free rule
    def side_of(du: float) -> str:
        left = du > 0.0
        if image_mirrored:
            left = not left
        return "L" if left else "R"

    if len(keys) == 1:
        if face_midline_u is None:
            raise ValueError("one group without a camera needs face_midline_u")
        k = keys[0]
        du = float(cents[k][0] - face_midline_u)
        return {k: side_of(du)}, abs(du) < LR_MIN_DU_PX
    a, b = keys
    du = float(cents[a][0] - cents[b][0])
    sa = side_of(du)
    assignment = {a: sa, b: "R" if sa == "L" else "L"}
    ambiguous = abs(du) < LR_MIN_DU_PX
    if face_midline_u is not None:
        oa, ob = cents[a][0] - face_midline_u, cents[b][0] - face_midline_u
        if oa * ob > 0.0:
            ambiguous = True
    return assignment, ambiguous
