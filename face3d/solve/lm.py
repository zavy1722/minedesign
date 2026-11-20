"""Small dense Levenberg-Marquardt solver (numpy only).

Intended for problems with up to a few hundred parameters (camera poses,
focal lengths, PCA/shape coefficients). Jacobians may be supplied or are
computed by central finite differences.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np


@dataclass
class LMResult:
    x: np.ndarray
    cost: float  # 0.5 * ||r||^2
    iterations: int
    converged: bool


def numeric_jacobian(fun: Callable[[np.ndarray], np.ndarray], x: np.ndarray,
                     r0: np.ndarray | None = None, step: float = 1e-6) -> np.ndarray:
    x = np.asarray(x, float)
    r0 = fun(x) if r0 is None else r0
    J = np.empty((r0.size, x.size))
    for j in range(x.size):
        h = step * max(1.0, abs(x[j]))
        xp = x.copy(); xp[j] += h
        xm = x.copy(); xm[j] -= h
        J[:, j] = (fun(xp) - fun(xm)) / (2.0 * h)
    return J


def levenberg_marquardt(fun: Callable[[np.ndarray], np.ndarray], x0: np.ndarray,
                        jac: Callable[[np.ndarray], np.ndarray] | None = None,
                        max_iter: int = 100, tol: float = 1e-10, lam0: float = 1e-3,
                        fd_step: float = 1e-6,
                        retract: Callable[[np.ndarray, np.ndarray], np.ndarray] | None = None) -> LMResult:
    """Minimise 0.5*||fun(x)||^2.

    `retract(x, dx)` applies a step on a manifold (e.g. multiplicative rotation
    updates); `jac` must then be the Jacobian w.r.t. that local step. Default is
    plain addition.
    """
    step_fn = retract if retract is not None else (lambda a, b: a + b)
    x = np.asarray(x0, float).copy()
    r = fun(x)
    cost = 0.5 * float(r @ r)
    lam = lam0
    for it in range(1, max_iter + 1):
        J = jac(x) if jac is not None else numeric_jacobian(fun, x, r, fd_step)
        g = J.T @ r
        if np.max(np.abs(g)) < tol:
            return LMResult(x, cost, it, True)
        H = J.T @ J
        diag = np.diag(H).copy()
        diag[diag <= 0] = 1e-12
        improved = False
        for _ in range(20):
            try:
                dx = -np.linalg.solve(H + lam * np.diag(diag), g)
            except np.linalg.LinAlgError:
                lam *= 10.0
                continue
            x_new = step_fn(x, dx)
            r_new = fun(x_new)
            cost_new = 0.5 * float(r_new @ r_new)
            if np.isfinite(cost_new) and cost_new < cost:
                rel = (cost - cost_new) / max(cost, 1e-300)
                x, r, cost = x_new, r_new, cost_new
                lam = max(lam / 3.0, 1e-12)
                improved = True
                if rel < tol or np.linalg.norm(dx) < tol * (np.linalg.norm(x) + tol):
                    return LMResult(x, cost, it, True)
                break
            lam *= 4.0
        if not improved:
            return LMResult(x, cost, it, True)
    return LMResult(x, cost, max_iter, False)
