"""Template kit: a template head mesh plus its sidecar (DESIGN 3.2 "Template kit").

A :class:`TemplateKit` is the unit the fitter, the conditional template prior
(:mod:`face3d.model.conditional_prior`), the test bed and the Blender bridge share:
the rest mesh, its landmark embeddings per scheme, the mirror map, regions,
jaw weights, stiffness, normals and UVs, together with its licence and
provenance.  The default kit is the procedural CC0 head of
:mod:`face3d.model.procedural_head` (``generated=True``, not anatomical; DESIGN 0).
Real kits are built offline by ``tools/build_template_kit.py`` (WP-08, WP-24).

Conventions
-----------
* Units: float64 millimetres in the Frankfort-horizontal head frame of the
  landmark prior mean (origin mid-tragion; +x subject's left, +y up, +z out of
  the face; DESIGN 3.1).  ``units`` is always ``'mm'``.
* Faces: ``(F, 4)`` int64 for an all-quad mesh (the only kind this version's
  build tool accepts) or, for a mixed mesh, a list of index lists.  Faces are
  oriented outward (counter-clockwise seen from outside).
* Triangles (:meth:`TemplateKit.triangles`): the fan split of each face in face
  order, ``(f0, f_i, f_i+1)`` for ``i = 1..k-2``; for quads triangle ``2f`` is
  ``(a, b, c)`` and ``2f + 1`` is ``(a, c, d)``.  This is the same split as
  :meth:`face3d.mesh.Mesh.triangles`, and landmark embeddings index it.
* Landmarks: ``landmarks[scheme][name] = {'tri': int, 'bary': (3,) float64,
  'sigma_annot_mm': float, 'provenance': str}``; the point is
  ``sum_k bary[k] * V[tris[tri, k]]``.  Scheme ``'anatomical44'`` is keyed by the
  anatomical ids of :data:`face3d.model.registry.ANATOMICAL` (``'prn'``,
  ``'en_L'``...); other schemes by their point names.
* ``topology_sha256`` = SHA-256 of ``int64(n_verts)`` followed by the face index
  array as int32, both little-endian (WP-08 spec; the Blender bridge's
  ``topology_sha`` uses the same definition, WP-21).  Mixed meshes hash
  ``int64(n_verts)``, the int32 face sizes, then the concatenated int32 indices.
* Mirror map: ``mirror_map[i]`` is the vertex at ``(-x, y, z)`` of vertex ``i``;
  it must be an involution and an exact reflection (``|V[m] * (-1, 1, 1) - V|``
  at most ``MIRROR_TOL_MM`` = 1e-6 mm; WP-08 spec), and ``midline`` must be its
  fixed points, with ``x = 0``.  Research basis: *open-template-head-kit*
  "Build the mirror map" (bijection, ``M(M(i)) = i``, midline fixed; 🧠).
* Persistence (:meth:`TemplateKit.save` / :meth:`TemplateKit.load`): a JSON
  document ``{format: 'face3d.template_kit', version: 1, ...}`` plus a sibling
  ``.npz`` written with :func:`face3d.core.schema.save_arrays` (SHA-256 per
  array).  The loader refuses a topology-hash mismatch with
  :class:`TopologyMismatch` (rec INV-4, bl K1; DESIGN 3.2).
* ``bundle_ok`` is ``licence == 'CC0-1.0'``: only CC0 assets may ship inside the
  extension (DESIGN D-28, eth A3/A4).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from ..core.schema import (FormatError, _clean, dump_json, load_arrays, load_json, save_arrays,
                           sha256_bytes)

__all__ = [
    "TemplateKit", "TopologyMismatch", "KIT_FORMAT", "KIT_VERSION", "MIRROR_TOL_MM",
    "fan_triangles", "topology_sha256", "vertex_embedding", "vertex_embeddings",
    "area_weighted_normals", "midline_ring", "npz_path_for",
]

#: Format tag and version of the kit JSON (DESIGN 3.2).
KIT_FORMAT = "face3d.template_kit"
KIT_VERSION = 1

#: Exact-reflection tolerance of the mirror map, mm (WP-08 spec).
MIRROR_TOL_MM = 1e-6

#: Tolerance on barycentric coordinates summing to one.
_BARY_TOL = 1e-6


class TopologyMismatch(ValueError):
    """The kit's face topology does not match the expected topology hash."""


# =========================================================================== helpers
def _faces_array(faces: Any) -> np.ndarray | list[list[int]]:
    """Normalise faces: a rectangular set becomes an (F, k) int64 array, a mixed set a list."""
    if isinstance(faces, np.ndarray):
        a = np.asarray(faces)
        if a.ndim != 2 or a.shape[1] < 3:
            raise ValueError(f"faces array must be (F, k>=3), got {a.shape}")
        if a.dtype.kind not in "iu":
            raise ValueError("faces must be integer indices")
        return np.ascontiguousarray(a, dtype=np.int64)
    lst = [[int(i) for i in f] for f in faces]
    if any(len(f) < 3 for f in lst):
        raise ValueError("every face needs at least 3 vertices")
    sizes = {len(f) for f in lst}
    if len(sizes) == 1:
        return np.asarray(lst, dtype=np.int64).reshape(len(lst), sizes.pop())
    if not lst:
        return np.zeros((0, 4), np.int64)
    return lst


def _face_lists(faces: np.ndarray | list[list[int]]) -> list[list[int]]:
    if isinstance(faces, np.ndarray):
        return faces.tolist()
    return [list(f) for f in faces]


def fan_triangles(faces: Any) -> np.ndarray:
    """Fan split ``(f0, f_i, f_i+1)`` of every face, in face order: (T, 3) int64.

    For an (F, 4) quad array triangle ``2f`` is ``(a, b, c)`` and ``2f + 1`` is
    ``(a, c, d)`` (consistent with :meth:`face3d.mesh.Mesh.triangles`).
    """
    f = _faces_array(faces)
    if isinstance(f, np.ndarray):
        k = f.shape[1]
        parts = [np.stack([f[:, 0], f[:, i], f[:, i + 1]], axis=1) for i in range(1, k - 1)]
        return np.stack(parts, axis=1).reshape(-1, 3)
    tris = [(g[0], g[i], g[i + 1]) for g in f for i in range(1, len(g) - 1)]
    return np.asarray(tris, np.int64).reshape(-1, 3)


def topology_sha256(n_verts: int, faces: Any) -> str:
    """SHA-256 of ``int64(n_verts)`` + face indices as int32 (little-endian; WP-08 spec).

    Mixed (non-rectangular) face lists hash ``int64(n_verts)``, the int32 face
    sizes and then the concatenated int32 indices.
    """
    f = _faces_array(faces)
    head = np.asarray([n_verts], dtype="<i8").tobytes()
    if isinstance(f, np.ndarray):
        return sha256_bytes(head + np.ascontiguousarray(f, dtype="<i4").tobytes())
    sizes = np.asarray([len(g) for g in f], dtype="<i4")
    flat = np.asarray([i for g in f for i in g], dtype="<i4")
    return sha256_bytes(head + sizes.tobytes() + flat.tobytes())


def vertex_embeddings(tris: np.ndarray, n_verts: int) -> tuple[np.ndarray, np.ndarray]:
    """For every vertex the lowest-index triangle containing it and its corner (0..2).

    Returns ``(tri (V,), corner (V,))``; ``tri = -1`` for unreferenced vertices.
    """
    T = len(tris)
    big = np.iinfo(np.int64).max
    first = np.full(n_verts, big, dtype=np.int64)
    ar = np.arange(T, dtype=np.int64)
    for k in range(3):
        np.minimum.at(first, tris[:, k], ar)
    corner = np.full(n_verts, -1, dtype=np.int64)
    ok = first < big
    tri = np.where(ok, first, -1)
    t_ok = tri[ok]
    v_ok = np.flatnonzero(ok)
    for k in (2, 1, 0):  # lowest corner index wins if a vertex appears twice (degenerate)
        hit = tris[t_ok, k] == v_ok
        corner[v_ok[hit]] = k
    return tri, corner


def vertex_embedding(tris: np.ndarray, v: int) -> tuple[int, np.ndarray]:
    """One-hot embedding ``(tri, bary)`` of vertex ``v``: the lowest-index triangle
    of the fan split containing ``v`` and the barycentric unit vector of its corner."""
    rows, cols = np.nonzero(np.asarray(tris) == int(v))
    if rows.size == 0:
        raise ValueError(f"vertex {v} is not referenced by any face")
    k = int(np.argmin(rows * 3 + cols))
    bary = np.zeros(3)
    bary[int(cols[k])] = 1.0
    return int(rows[k]), bary


def area_weighted_normals(V: np.ndarray, faces: Any) -> np.ndarray:
    """Unit vertex normals: sum of the (area-weighted) fan-triangle normals, normalised.

    Same definition as :meth:`face3d.mesh.Mesh.vertex_normals`.
    """
    V = np.asarray(V, float)
    tri = fan_triangles(faces)
    fn = np.cross(V[tri[:, 1]] - V[tri[:, 0]], V[tri[:, 2]] - V[tri[:, 0]])
    n = np.zeros_like(V)
    for k in range(3):
        np.add.at(n, tri[:, k], fn)
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    return n / np.where(ln > 0, ln, 1.0)


def midline_ring(V: np.ndarray, midline: np.ndarray) -> np.ndarray:
    """Midline vertices ordered by angle ``atan2(y - c_y, z - c_z)`` about their (y, z) centroid.

    The angle runs from -pi (back of the head, below the centroid) through the
    face (0, +z) to the vertex and the back again, so the result is the closed
    sagittal profile loop used as the ``'midline_profile'`` contour ring
    (*open-template-head-kit*, "Define contour rings": the profile midline; 🧠).
    Ties break by vertex index (stable sort).
    """
    mid = np.asarray(midline, dtype=np.int64)
    if mid.size == 0:
        return mid.copy()
    P = np.asarray(V, float)[mid]
    c = P[:, 1:].mean(axis=0)
    ang = np.arctan2(P[:, 1] - c[0], P[:, 2] - c[1])
    return mid[np.argsort(ang, kind="stable")]


def npz_path_for(path_json: str | Path) -> Path:
    """Sibling arrays file of a kit JSON: ``<id>.kit.json`` -> ``<id>.npz``; ``x.json`` -> ``x.npz``."""
    p = Path(path_json)
    name = p.name
    if name.endswith(".kit.json"):
        base = name[: -len(".kit.json")]
    elif name.endswith(".json"):
        base = name[: -len(".json")]
    else:
        base = name
    return p.with_name(base + ".npz")


def _int_array(a: Any, name: str) -> np.ndarray:
    arr = np.asarray(a)
    if arr.size == 0:
        return np.zeros(0, np.int64)
    if arr.dtype.kind not in "iu":
        if arr.dtype.kind == "f" and np.all(np.isfinite(arr)) and np.all(arr == np.round(arr)):
            arr = arr.astype(np.int64)
        else:
            raise ValueError(f"{name} must hold integer vertex indices")
    return np.ascontiguousarray(arr.reshape(-1), dtype=np.int64)


def _float_array(a: Any, shape_tail: tuple[int, ...], n: int, name: str) -> np.ndarray:
    arr = np.ascontiguousarray(np.asarray(a, dtype=np.float64))
    if arr.shape != (n,) + shape_tail:
        raise ValueError(f"{name} must have shape {(n,) + shape_tail}, got {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} has non-finite values")
    return arr


def _norm_landmarks(lm: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> dict[str, dict[str, dict[str, Any]]]:
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for scheme, pts in lm.items():
        d: dict[str, dict[str, Any]] = {}
        for name, e in pts.items():
            bary = np.ascontiguousarray(np.asarray(e["bary"], dtype=np.float64).reshape(-1))
            d[str(name)] = {
                "tri": int(e["tri"]),
                "bary": bary,
                "sigma_annot_mm": float(e.get("sigma_annot_mm", 0.0)),
                "provenance": str(e.get("provenance", "")),
            }
        out[str(scheme)] = d
    return out


# =========================================================================== TemplateKit
@dataclass(kw_only=True, eq=False)
class TemplateKit:
    """A template head mesh with its sidecar (DESIGN 3.2; WP-08).

    Fields (all keyword-only; arrays are normalised to contiguous float64 /
    int64 copies and the kit is validated on construction):

    id : str, e.g. ``'procedural-head-v1'``.
    licence : SPDX id; ``bundle_ok`` iff ``'CC0-1.0'``.
    generated : True for a procedurally generated (non-anatomical) asset,
        False for a measured / artist-made one (DESIGN 2.1 invariant 6).
    source_sha256 : SHA-256 hex of the source asset (for the procedural head:
        of the canonical generator parameters and the prior file hash).
    units : always ``'mm'``.
    vertices : (V, 3) rest positions, mm.
    faces : (F, 4) int64 quads, or a list of index lists.
    landmarks : ``{scheme: {name: {'tri', 'bary', 'sigma_annot_mm', 'provenance'}}}``.
    mirror_map : (V,) int64; midline : (k,) int64 (fixed points of the mirror map).
    regions : ``{name: (n_r,) int64 vertex ids}``; region_weights : ``{name: float}``.
    contour_rings : ``{name: (n,) int64 ordered vertex ids}``.
    jaw_weights : (V,) in [0, 1]; stiffness : (V,) > 0 (Laplacian weights, DESIGN 4.15 C).
    normals : (V, 3) unit area-weighted vertex normals; uv : (V, 2).
    meta : free JSON-serialisable provenance (generator parameters, notes).
    """

    id: str
    licence: str
    generated: bool
    source_sha256: str
    units: str = "mm"
    vertices: np.ndarray
    faces: Any
    landmarks: dict = field(default_factory=dict)
    mirror_map: np.ndarray
    midline: np.ndarray
    regions: dict = field(default_factory=dict)
    region_weights: dict = field(default_factory=dict)
    contour_rings: dict = field(default_factory=dict)
    jaw_weights: np.ndarray | None = None
    stiffness: np.ndarray | None = None
    normals: np.ndarray | None = None
    uv: np.ndarray | None = None
    meta: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ init
    def __post_init__(self) -> None:
        self.id = str(self.id)
        self.licence = str(self.licence)
        self.generated = bool(self.generated)
        self.source_sha256 = str(self.source_sha256)
        if self.units != "mm":
            raise ValueError(f"template kits are in mm, got units={self.units!r}")
        V = np.ascontiguousarray(np.asarray(self.vertices, dtype=np.float64))
        if V.ndim != 2 or V.shape[1] != 3 or len(V) == 0:
            raise ValueError(f"vertices must be (V, 3), got {V.shape}")
        if not np.all(np.isfinite(V)):
            raise ValueError("vertices have non-finite values")
        self.vertices = V
        n = len(V)
        self.faces = _faces_array(self.faces)
        self.mirror_map = _int_array(self.mirror_map, "mirror_map")
        self.midline = _int_array(self.midline, "midline")
        self.regions = {str(k): _int_array(v, f"regions[{k!r}]") for k, v in self.regions.items()}
        self.region_weights = {str(k): float(v) for k, v in self.region_weights.items()}
        self.contour_rings = {str(k): _int_array(v, f"contour_rings[{k!r}]")
                              for k, v in self.contour_rings.items()}
        self.landmarks = _norm_landmarks(self.landmarks)
        self.jaw_weights = (np.zeros(n) if self.jaw_weights is None
                            else _float_array(self.jaw_weights, (), n, "jaw_weights"))
        self.stiffness = (np.ones(n) if self.stiffness is None
                          else _float_array(self.stiffness, (), n, "stiffness"))
        self.normals = (area_weighted_normals(V, self.faces) if self.normals is None
                        else _float_array(self.normals, (3,), n, "normals"))
        self.uv = np.zeros((n, 2)) if self.uv is None else _float_array(self.uv, (2,), n, "uv")
        self.meta = _clean(dict(self.meta))
        self._tris: np.ndarray | None = None
        self.validate()

    # ------------------------------------------------------------------ properties
    @property
    def n_verts(self) -> int:
        return len(self.vertices)

    @property
    def n_faces(self) -> int:
        return len(self.faces)

    @property
    def is_quad(self) -> bool:
        return isinstance(self.faces, np.ndarray) and self.faces.shape[1] == 4

    @property
    def topology_sha256(self) -> str:
        """SHA-256 of int64(n_verts) + int32 faces (little-endian)."""
        return topology_sha256(self.n_verts, self.faces)

    @property
    def order_checksum(self) -> str:
        """SHA-256 of the rest positions quantised to 1 um (little-endian int64).

        Pins vertex order *and* rest shape (DESIGN 3.2 ``order_checksum``); the
        topology hash alone does not change when positions are edited.
        """
        q = np.round(self.vertices * 1000.0).astype("<i8")
        return sha256_bytes(q.tobytes())

    @property
    def bundle_ok(self) -> bool:
        """Only CC0 kits may be bundled with the extension (DESIGN D-28)."""
        return self.licence == "CC0-1.0"

    @property
    def schemes(self) -> list[str]:
        return list(self.landmarks)

    # ------------------------------------------------------------------ topology
    def triangles(self) -> np.ndarray:
        """Fan split of the faces, (T, 3) int64 (the index space of ``landmarks[...]['tri']``)."""
        if self._tris is None:
            t = fan_triangles(self.faces)
            t.setflags(write=False)
            self._tris = t
        return self._tris

    def face_lists(self) -> list[list[int]]:
        return _face_lists(self.faces)

    def edges(self) -> np.ndarray:
        """Unique undirected face edges (E, 2), sorted rows."""
        if isinstance(self.faces, np.ndarray):
            f = self.faces
            e = np.concatenate([np.stack([f[:, i], f[:, (i + 1) % f.shape[1]]], 1) for i in range(f.shape[1])])
        else:
            e = np.asarray([(g[i], g[(i + 1) % len(g)]) for g in self.faces for i in range(len(g))], np.int64)
        return np.unique(np.sort(e, axis=1), axis=0)

    def mesh(self, V: np.ndarray | None = None):
        """A :class:`face3d.mesh.Mesh` of the kit (vertex UVs as per-corner UVs; regions as groups)."""
        from ..mesh.core import Mesh

        verts = self.vertices.copy() if V is None else np.asarray(V, float).copy()
        faces = self.face_lists()
        return Mesh(verts, faces, uvs=self.uv.copy(), face_uvs=[list(f) for f in faces],
                    groups={k: v.copy() for k, v in self.regions.items()})

    # ------------------------------------------------------------------ landmarks
    def landmark_names(self, scheme: str) -> list[str]:
        return list(self._scheme(scheme))

    def _scheme(self, scheme: str) -> dict[str, dict[str, Any]]:
        try:
            return self.landmarks[scheme]
        except KeyError:
            raise KeyError(f"kit {self.id!r} has no landmark embeddings for scheme {scheme!r}") from None

    def _entries(self, scheme: str, names: Sequence[str] | None) -> tuple[list[str], np.ndarray, np.ndarray]:
        pts = self._scheme(scheme)
        nm = list(pts) if names is None else [str(x) for x in names]
        missing = [x for x in nm if x not in pts]
        if missing:
            raise KeyError(f"scheme {scheme!r} of kit {self.id!r} has no landmarks {missing}")
        tri = np.asarray([pts[x]["tri"] for x in nm], dtype=np.int64)
        bary = np.asarray([pts[x]["bary"] for x in nm], dtype=np.float64).reshape(-1, 3)
        return nm, tri, bary

    def landmark_positions(self, scheme: str, V: np.ndarray | None = None,
                           names: Sequence[str] | None = None) -> np.ndarray:
        """Barycentric evaluation ``sum_k bary_k V[tris[tri, k]]`` -> (n, 3) mm.

        ``V`` defaults to the rest vertices; ``names`` to the scheme's stored order.
        """
        _, tri, bary = self._entries(scheme, names)
        Vx = self.vertices if V is None else np.asarray(V, float)
        if Vx.shape != self.vertices.shape:
            raise ValueError(f"V must have shape {self.vertices.shape}, got {Vx.shape}")
        T = self.triangles()[tri]
        return np.einsum("nk,nkd->nd", bary, Vx[T])

    def landmark_vertices(self, scheme: str, names: Sequence[str] | None = None) -> np.ndarray:
        """The vertex with the largest barycentric weight of each landmark (n,) int64."""
        _, tri, bary = self._entries(scheme, names)
        T = self.triangles()[tri]
        return T[np.arange(len(tri)), np.argmax(bary, axis=1)]

    def to_template(self, scheme: str):
        """A legacy :class:`face3d.fit.template.Template` (landmark = vertex with max bary)."""
        from ..fit.template import Template

        names = self.landmark_names(scheme)
        lv = self.landmark_vertices(scheme, names)
        meta = {"kit_id": self.id, "scheme": scheme, "topology_sha256": self.topology_sha256,
                "licence": self.licence, "generated": self.generated}
        return Template(mesh=self.mesh(), names=names, landmark_vertices=lv, meta=meta)

    def annotations(self, schemes: Sequence[str] | None = None,
                    annotator_spread_mm: float = 0.0) -> dict[str, dict[str, dict[str, Any]]]:
        """Export embeddings in the build-tool annotation format.

        ``{scheme: {name: {'tri', 'bary', 'sigma_annot_mm', 'annotator_spread_mm',
        'provenance'}}}``.  For a generated kit the placements are deterministic, so
        the default spread is 0.0 mm (one "annotator": the generator).
        """
        out: dict[str, dict[str, dict[str, Any]]] = {}
        for s in (self.schemes if schemes is None else schemes):
            out[s] = {name: {"tri": e["tri"], "bary": [float(b) for b in e["bary"]],
                             "sigma_annot_mm": e["sigma_annot_mm"],
                             "annotator_spread_mm": float(annotator_spread_mm),
                             "provenance": e["provenance"]}
                      for name, e in self._scheme(s).items()}
        return out

    # ------------------------------------------------------------------ regions
    def vertex_regions(self, default: str = "other") -> np.ndarray:
        """Region name of every vertex (V,) (first region in ``regions`` order wins; else ``default``)."""
        names = list(self.regions)
        width = max([len(default)] + [len(s) for s in names])
        out = np.full(self.n_verts, default, dtype=f"<U{width}")
        assigned = np.zeros(self.n_verts, bool)
        for name in names:
            idx = self.regions[name]
            new = idx[~assigned[idx]]
            out[new] = name
            assigned[new] = True
        return out

    def region_of_vertex(self, v: int, default: str = "other") -> str:
        for name, idx in self.regions.items():
            if np.any(idx == int(v)):
                return name
        return default

    # ------------------------------------------------------------------ validation
    def validate(self, tol_mm: float = MIRROR_TOL_MM) -> None:
        """Check indices, mirror map (involution, exact reflection within ``tol_mm``),
        midline (= fixed points, x = 0), landmark embeddings and per-vertex arrays.

        Raises ValueError naming the first problem.
        """
        n = self.n_verts
        flat = (self.faces.reshape(-1) if isinstance(self.faces, np.ndarray)
                else np.asarray([i for g in self.faces for i in g], np.int64))
        if flat.size and (flat.min() < 0 or flat.max() >= n):
            raise ValueError("face index out of range")
        if isinstance(self.faces, np.ndarray):
            f = self.faces
            if np.any([np.any(f[:, i] == f[:, j]) for i in range(f.shape[1]) for j in range(i + 1, f.shape[1])]):
                raise ValueError("a face repeats a vertex")
        m = self.mirror_map
        if m.shape != (n,):
            raise ValueError(f"mirror_map must have shape ({n},), got {m.shape}")
        if m.min() < 0 or m.max() >= n:
            raise ValueError("mirror_map index out of range")
        if not np.array_equal(m[m], np.arange(n)):
            bad = int(np.flatnonzero(m[m] != np.arange(n))[0])
            raise ValueError(f"mirror_map is not an involution (vertex {bad})")
        err = np.abs(self.vertices[m] * np.array([-1.0, 1.0, 1.0]) - self.vertices).max(axis=1)
        if err.max() > tol_mm:
            bad = int(np.argmax(err))
            raise ValueError(f"mirror_map is not an exact reflection: vertex {bad} is "
                             f"{err[bad]:.3g} mm from its mirror image (tolerance {tol_mm:g} mm)")
        fixed = np.flatnonzero(m == np.arange(n))
        if not np.array_equal(np.sort(self.midline), fixed):
            raise ValueError("midline must be exactly the fixed points of mirror_map")
        if fixed.size and np.abs(self.vertices[fixed, 0]).max() > tol_mm:
            raise ValueError("midline vertices must have x = 0")
        for name, idx in list(self.regions.items()) + list(self.contour_rings.items()):
            if idx.size and (idx.min() < 0 or idx.max() >= n):
                raise ValueError(f"vertex index out of range in {name!r}")
        T = len(self.triangles())
        for scheme, pts in self.landmarks.items():
            for name, e in pts.items():
                if not 0 <= e["tri"] < T:
                    raise ValueError(f"landmark {scheme}/{name}: triangle {e['tri']} out of range (T={T})")
                b = e["bary"]
                if b.shape != (3,) or not np.all(np.isfinite(b)) or b.min() < -_BARY_TOL \
                        or abs(float(b.sum()) - 1.0) > _BARY_TOL:
                    raise ValueError(f"landmark {scheme}/{name}: invalid barycentric coordinates {b.tolist()}")
                if not (math.isfinite(e["sigma_annot_mm"]) and e["sigma_annot_mm"] >= 0.0):
                    raise ValueError(f"landmark {scheme}/{name}: sigma_annot_mm must be finite and >= 0")
        if np.any((self.jaw_weights < 0) | (self.jaw_weights > 1)):
            raise ValueError("jaw_weights must lie in [0, 1]")
        if np.any(self.stiffness <= 0):
            raise ValueError("stiffness must be positive")

    # ------------------------------------------------------------------ equality / copies
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TemplateKit):
            return NotImplemented
        scal = ("id", "licence", "generated", "source_sha256", "units", "region_weights", "meta")
        if any(getattr(self, k) != getattr(other, k) for k in scal):
            return False
        arrs = ("vertices", "mirror_map", "midline", "jaw_weights", "stiffness", "normals", "uv")
        if any(not np.array_equal(getattr(self, k), getattr(other, k)) for k in arrs):
            return False
        if self.topology_sha256 != other.topology_sha256:
            return False
        for a, b in ((self.regions, other.regions), (self.contour_rings, other.contour_rings)):
            if list(a) != list(b) or any(not np.array_equal(a[k], b[k]) for k in a):
                return False
        if list(self.landmarks) != list(other.landmarks):
            return False
        for s, pts in self.landmarks.items():
            op = other.landmarks[s]
            if list(pts) != list(op):
                return False
            for k, e in pts.items():
                f = op[k]
                if (e["tri"], e["sigma_annot_mm"], e["provenance"]) != (f["tri"], f["sigma_annot_mm"], f["provenance"]) \
                        or not np.array_equal(e["bary"], f["bary"]):
                    return False
        return True

    __hash__ = None  # type: ignore[assignment]

    def replace(self, **changes: Any) -> "TemplateKit":
        """A validated copy with some fields changed (e.g. ``licence``)."""
        return replace(self, **changes)

    def __repr__(self) -> str:
        return (f"TemplateKit(id={self.id!r}, licence={self.licence!r}, generated={self.generated}, "
                f"n_verts={self.n_verts}, n_faces={self.n_faces}, schemes={self.schemes})")

    # ------------------------------------------------------------------ persistence
    def to_json_dict(self, arrays_manifest: Mapping[str, Any]) -> dict[str, Any]:
        lm = {s: {k: {"tri": e["tri"], "bary": e["bary"].tolist(), "sigma_annot_mm": e["sigma_annot_mm"],
                      "provenance": e["provenance"]} for k, e in pts.items()}
              for s, pts in self.landmarks.items()}
        return {
            "format": KIT_FORMAT, "version": KIT_VERSION,
            "id": self.id, "licence": self.licence, "generated": self.generated,
            "bundle_ok": self.bundle_ok, "source_sha256": self.source_sha256, "units": self.units,
            "topology_sha256": self.topology_sha256, "order_checksum": self.order_checksum,
            "n_verts": self.n_verts, "n_faces": self.n_faces,
            "face_size": int(self.faces.shape[1]) if isinstance(self.faces, np.ndarray) else None,
            "landmarks": lm, "landmark_order": {s: list(p) for s, p in self.landmarks.items()},
            "region_names": list(self.regions), "region_weights": dict(self.region_weights),
            "contour_ring_names": list(self.contour_rings),
            "arrays": dict(arrays_manifest), "meta": self.meta,
        }

    def save(self, path_json: str | Path) -> Path:
        """Write ``path_json`` (format ``face3d.template_kit`` v1) and its sibling ``.npz``.

        Returns the path of the arrays file.  Region and ring arrays are stored as
        ``region__<name>`` / ``ring__<name>``.
        """
        path_json = Path(path_json)
        npz = npz_path_for(path_json)
        arrays: dict[str, np.ndarray] = {
            "vertices": self.vertices, "mirror_map": self.mirror_map, "midline": self.midline,
            "jaw_weights": self.jaw_weights, "stiffness": self.stiffness, "normals": self.normals, "uv": self.uv,
        }
        if isinstance(self.faces, np.ndarray):
            arrays["faces"] = self.faces
        else:
            arrays["face_sizes"] = np.asarray([len(g) for g in self.faces], np.int64)
            arrays["faces_flat"] = np.asarray([i for g in self.faces for i in g], np.int64)
        for k, v in self.regions.items():
            arrays[f"region__{k}"] = v
        for k, v in self.contour_rings.items():
            arrays[f"ring__{k}"] = v
        manifest = save_arrays(npz, **arrays)
        dump_json(self.to_json_dict(manifest), path_json)
        return npz

    @classmethod
    def load(cls, path_json: str | Path, expect_topology_sha256: str | None = None) -> "TemplateKit":
        """Load a kit; verify array hashes, the stored topology hash and, if given,
        ``expect_topology_sha256``.

        Raises :class:`TopologyMismatch` when the topology differs from either hash,
        :class:`face3d.core.schema.FormatError` for a wrong format/version or a
        corrupted arrays file, ValueError when the kit fails validation.
        """
        path_json = Path(path_json)
        doc = load_json(path_json, expect_format=KIT_FORMAT, max_version=KIT_VERSION)
        manifest = doc["arrays"]
        files = {m["file"] for m in manifest.values()}
        if len(files) != 1:
            raise FormatError(f"kit arrays must live in one .npz file, got {sorted(files)}")
        arr = load_arrays(path_json.parent / files.pop(), manifest)
        if "faces" in arr:
            faces: Any = arr["faces"]
        else:
            sizes, flat = arr["face_sizes"], arr["faces_flat"]
            starts = np.concatenate([[0], np.cumsum(sizes)[:-1]])
            faces = [flat[s:s + k].tolist() for s, k in zip(starts, sizes)]
        n_verts = len(arr["vertices"])
        topo = topology_sha256(n_verts, faces)
        if topo != doc["topology_sha256"]:
            raise TopologyMismatch(f"{path_json.name}: arrays have topology {topo[:12]}..., "
                                   f"the kit records {str(doc['topology_sha256'])[:12]}...")
        if expect_topology_sha256 is not None and topo != expect_topology_sha256:
            raise TopologyMismatch(f"{path_json.name}: topology {topo[:12]}... does not match the "
                                   f"expected {expect_topology_sha256[:12]}...")
        order = doc.get("landmark_order", {})
        landmarks = {}
        for s, pts in doc["landmarks"].items():
            names = order.get(s, list(pts))
            if sorted(names) != sorted(pts):
                raise FormatError(f"landmark_order of scheme {s!r} does not match its landmarks")
            landmarks[s] = {k: pts[k] for k in names}
        kit = cls(
            id=doc["id"], licence=doc["licence"], generated=doc["generated"],
            source_sha256=doc["source_sha256"], units=doc.get("units", "mm"),
            vertices=arr["vertices"], faces=faces, landmarks=landmarks,
            mirror_map=arr["mirror_map"], midline=arr["midline"],
            regions={k: arr[f"region__{k}"] for k in doc["region_names"]},
            region_weights=doc.get("region_weights", {}),
            contour_rings={k: arr[f"ring__{k}"] for k in doc["contour_ring_names"]},
            jaw_weights=arr["jaw_weights"], stiffness=arr["stiffness"], normals=arr["normals"], uv=arr["uv"],
            meta=doc.get("meta", {}),
        )
        if "order_checksum" in doc and kit.order_checksum != doc["order_checksum"]:
            raise FormatError(f"{path_json.name}: order_checksum mismatch (vertices reordered or edited)")
        return kit

    def content_sha256(self) -> str:
        """SHA-256 of the canonical kit JSON with the array hashes (no file names)."""
        from ..core.schema import canonical_json

        arrays = {"vertices": self.vertices, "mirror_map": self.mirror_map, "midline": self.midline,
                  "jaw_weights": self.jaw_weights, "stiffness": self.stiffness, "normals": self.normals,
                  "uv": self.uv}
        man = {k: sha256_bytes(np.ascontiguousarray(v).tobytes()) for k, v in arrays.items()}
        man.update({f"region__{k}": sha256_bytes(v.tobytes()) for k, v in self.regions.items()})
        man.update({f"ring__{k}": sha256_bytes(v.tobytes()) for k, v in self.contour_rings.items()})
        return sha256_bytes(canonical_json(self.to_json_dict(man)))
