"""Minimal sparse matrix + conjugate gradient (numpy only; SciPy is not available
inside every Blender build, so the engine carries its own)."""
from __future__ import annotations

import numpy as np


class Sparse:
    """Coalesced COO matrix with fast mat-vec via np.bincount."""

    def __init__(self, rows, cols, vals, shape: tuple[int, int], coalesce: bool = True):
        rows = np.asarray(rows, np.int64)
        cols = np.asarray(cols, np.int64)
        vals = np.asarray(vals, float)
        if coalesce and len(rows):
            key = rows * shape[1] + cols
            order = np.argsort(key, kind="stable")
            key, rows, cols, vals = key[order], rows[order], cols[order], vals[order]
            starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
            vals = np.add.reduceat(vals, starts)
            rows, cols = rows[starts], cols[starts]
        self.rows, self.cols, self.vals, self.shape = rows, cols, vals, shape

    @property
    def nnz(self) -> int:
        return len(self.vals)

    @property
    def T(self) -> "Sparse":
        return Sparse(self.cols, self.rows, self.vals, (self.shape[1], self.shape[0]))

    def __matmul__(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, float)
        if x.ndim == 1:
            return np.bincount(self.rows, weights=self.vals * x[self.cols], minlength=self.shape[0])
        return np.column_stack([self @ x[:, j] for j in range(x.shape[1])])

    def diagonal(self) -> np.ndarray:
        d = np.zeros(min(self.shape))
        m = self.rows == self.cols
        np.add.at(d, self.rows[m], self.vals[m])
        return d

    def scale_rows(self, s: np.ndarray) -> "Sparse":
        return Sparse(self.rows, self.cols, self.vals * np.asarray(s)[self.rows], self.shape, coalesce=False)

    def __add__(self, other: "Sparse") -> "Sparse":
        assert self.shape == other.shape
        return Sparse(np.r_[self.rows, other.rows], np.r_[self.cols, other.cols],
                      np.r_[self.vals, other.vals], self.shape)

    def __mul__(self, a: float) -> "Sparse":
        return Sparse(self.rows, self.cols, self.vals * a, self.shape, coalesce=False)

    __rmul__ = __mul__

    def toarray(self) -> np.ndarray:
        A = np.zeros(self.shape)
        np.add.at(A, (self.rows, self.cols), self.vals)
        return A

    @staticmethod
    def diag(d: np.ndarray) -> "Sparse":
        n = len(d)
        idx = np.arange(n)
        return Sparse(idx, idx, d, (n, n), coalesce=False)


def cg(matvec, b: np.ndarray, x0: np.ndarray | None = None, precond: np.ndarray | None = None,
       tol: float = 1e-8, max_iter: int = 2000) -> tuple[np.ndarray, int]:
    """Jacobi-preconditioned conjugate gradient for SPD systems. b may be (n,) or (n,k)."""
    b = np.asarray(b, float)
    if b.ndim == 2:
        cols = [cg(matvec, b[:, j], None if x0 is None else x0[:, j], precond, tol, max_iter) for j in range(b.shape[1])]
        return np.column_stack([c[0] for c in cols]), max(c[1] for c in cols)
    x = np.zeros_like(b) if x0 is None else np.asarray(x0, float).copy()
    Minv = None if precond is None else 1.0 / np.where(np.abs(precond) > 1e-300, precond, 1.0)
    r = b - matvec(x)
    z = r * Minv if Minv is not None else r
    p = z.copy()
    rz = r @ z
    bnorm = np.linalg.norm(b) or 1.0
    for it in range(1, max_iter + 1):
        if np.linalg.norm(r) <= tol * bnorm:
            return x, it - 1
        Ap = matvec(p)
        pAp = p @ Ap
        if pAp <= 0:
            break
        alpha = rz / pAp
        x += alpha * p
        r -= alpha * Ap
        z = r * Minv if Minv is not None else r
        rz_new = r @ z
        p = z + (rz_new / rz) * p
        rz = rz_new
    return x, max_iter
