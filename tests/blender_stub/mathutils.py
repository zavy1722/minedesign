"""Minimal mathutils stub."""
import numpy as np


class Vector:
    def __init__(self, seq=(0.0, 0.0, 0.0)):
        self._a = np.array(seq, dtype=np.float64)

    def __array__(self, dtype=None, copy=None):
        return self._a if dtype is None else self._a.astype(dtype)

    def __iter__(self):
        return iter(self._a.tolist())

    def __len__(self):
        return len(self._a)

    def __getitem__(self, i):
        return float(self._a[i])


class Matrix:
    def __init__(self, rows=None):
        self._a = np.eye(4) if rows is None else np.array(rows, dtype=np.float64)

    def __array__(self, dtype=None, copy=None):
        return self._a if dtype is None else self._a.astype(dtype)

    def __matmul__(self, other):
        return Matrix(self._a @ np.asarray(other))

    def __getitem__(self, i):
        return self._a[i].tolist()

    @property
    def translation(self):
        return Vector(self._a[:3, 3])
