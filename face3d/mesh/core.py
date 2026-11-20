"""Polygon mesh container, OBJ I/O and basic topology utilities."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class Mesh:
    vertices: np.ndarray                      # (V,3) float
    faces: list[list[int]]                    # polygons (tris/quads/ngons), 0-based
    uvs: np.ndarray | None = None             # (T,2)
    face_uvs: list[list[int]] | None = None   # per-face uv indices
    groups: dict[str, np.ndarray] = field(default_factory=dict)  # named vertex sets

    @property
    def n_vertices(self) -> int:
        return len(self.vertices)

    def copy(self) -> "Mesh":
        return Mesh(self.vertices.copy(), [list(f) for f in self.faces],
                    None if self.uvs is None else self.uvs.copy(),
                    None if self.face_uvs is None else [list(f) for f in self.face_uvs],
                    {k: v.copy() for k, v in self.groups.items()})

    def triangles(self) -> np.ndarray:
        """Fan-triangulated faces as (F,3) int array."""
        tris = [(f[0], f[i], f[i + 1]) for f in self.faces for i in range(1, len(f) - 1)]
        return np.asarray(tris, np.int64).reshape(-1, 3)

    def edges(self) -> np.ndarray:
        """Unique undirected edges (E,2)."""
        e = [(f[i], f[(i + 1) % len(f)]) for f in self.faces for i in range(len(f))]
        e = np.sort(np.asarray(e, np.int64), axis=1)
        return np.unique(e, axis=0)

    def vertex_normals(self) -> np.ndarray:
        tri = self.triangles()
        v = self.vertices
        fn = np.cross(v[tri[:, 1]] - v[tri[:, 0]], v[tri[:, 2]] - v[tri[:, 0]])  # area-weighted
        n = np.zeros_like(v)
        for k in range(3):
            np.add.at(n, tri[:, k], fn)
        ln = np.linalg.norm(n, axis=1, keepdims=True)
        return n / np.where(ln > 0, ln, 1.0)

    def boundary_vertices(self) -> np.ndarray:
        e = [(f[i], f[(i + 1) % len(f)]) for f in self.faces for i in range(len(f))]
        e = np.sort(np.asarray(e, np.int64), axis=1)
        uniq, counts = np.unique(e, axis=0, return_counts=True)
        return np.unique(uniq[counts == 1])

    def bounding_box(self) -> tuple[np.ndarray, np.ndarray]:
        return self.vertices.min(0), self.vertices.max(0)


def read_obj(path: str | Path) -> Mesh:
    vs, vts, faces, fuvs = [], [], [], []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("v "):
                vs.append([float(x) for x in line.split()[1:4]])
            elif line.startswith("vt "):
                vts.append([float(x) for x in line.split()[1:3]])
            elif line.startswith("f "):
                f, fu = [], []
                for tok in line.split()[1:]:
                    parts = tok.split("/")
                    vi = int(parts[0])
                    f.append(vi - 1 if vi > 0 else len(vs) + vi)
                    if len(parts) > 1 and parts[1]:
                        ti = int(parts[1])
                        fu.append(ti - 1 if ti > 0 else len(vts) + ti)
                faces.append(f)
                fuvs.append(fu)
    has_uv = bool(vts) and all(len(fu) == len(f) for f, fu in zip(faces, fuvs))
    return Mesh(np.asarray(vs, float), faces, np.asarray(vts, float) if has_uv else None,
                fuvs if has_uv else None)


def write_obj(mesh: Mesh, path: str | Path, precision: int = 6) -> None:
    fmt = f"{{:.{precision}f}}"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# face3d\n")
        for v in mesh.vertices:
            fh.write("v " + " ".join(fmt.format(c) for c in v) + "\n")
        if mesh.uvs is not None and mesh.face_uvs is not None:
            for t in mesh.uvs:
                fh.write("vt " + " ".join(fmt.format(c) for c in t) + "\n")
            for f, fu in zip(mesh.faces, mesh.face_uvs):
                fh.write("f " + " ".join(f"{a + 1}/{b + 1}" for a, b in zip(f, fu)) + "\n")
        else:
            for f in mesh.faces:
                fh.write("f " + " ".join(str(a + 1) for a in f) + "\n")


def uv_sphere(radius: float = 1.0, n_lat: int = 24, n_lon: int = 48, radii: tuple[float, float, float] | None = None) -> Mesh:
    """Closed quad-dominant (ellipsoidal) sphere; y is the polar axis."""
    rx, ry, rz = radii if radii is not None else (radius, radius, radius)
    verts = [(0.0, ry, 0.0)]
    for i in range(1, n_lat):
        th = np.pi * i / n_lat
        for j in range(n_lon):
            ph = 2 * np.pi * j / n_lon
            verts.append((rx * np.sin(th) * np.sin(ph), ry * np.cos(th), rz * np.sin(th) * np.cos(ph)))
    verts.append((0.0, -ry, 0.0))
    V = np.asarray(verts)
    faces: list[list[int]] = []
    ring = lambda i, j: 1 + (i - 1) * n_lon + (j % n_lon)
    for j in range(n_lon):
        faces.append([0, ring(1, j), ring(1, j + 1)])
    for i in range(1, n_lat - 1):
        for j in range(n_lon):
            faces.append([ring(i, j), ring(i + 1, j), ring(i + 1, j + 1), ring(i, j + 1)])
    last = len(V) - 1
    for j in range(n_lon):
        faces.append([ring(n_lat - 1, j), last, ring(n_lat - 1, j + 1)])
    return Mesh(V, faces)
