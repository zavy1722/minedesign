"""Small dense Levenberg-Marquardt solver (numpy only).

Intended for problems with up to a few hundred parameters (camera poses,
focal lengths, PCA/shape coefficients). Jacobians may be supplied or are
computed by central finite differences.

Extensions (WP-07; DESIGN 2.3 "Pluggable linear-step solver; box projection in
retract", 4.8 "Solver"):

* ``step_solver(H, lam_diag, g) -> dx``: replaces the dense linear step.  It must
  return dx solving ``(H + diag(lam_diag)) dx = -g`` (H = J^T J, g = J^T r,
  ``lam_diag`` = damping lambda times the Marquardt diagonal) and may raise
  ``numpy.linalg.LinAlgError`` (then the damping is increased, as for the default).
  The default is ``-numpy.linalg.solve(H + diag(lam_diag), g)``, unchanged behaviour.
* ``project(x) -> x``: applied after ``retract`` to every trial point (e.g. box
  constraints on inverse depth, DESIGN D-02).
* :class:`LMResult` ``jtj``: J^T J at the returned ``x`` when the last Jacobian
  evaluation was at that ``x`` (convergence by a small gradient, or no further
  improvement possible), else ``None``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

# rho (actual / predicted reduction) only enters the damping update through
# max(1/3, 1 - (2 rho - 1)^3), which is 1/3 for every rho >= 1; clipping rho here
# changes no result but avoids a Python OverflowError in the cube when the
# predicted reduction underflows (the legacy failure noted in testbed/scorecard.py).
_RHO_CLIP = 1e3


@dataclass
class LMResult:
    x: np.ndarray
    cost: float  # 0.5 * ||r||^2
    iterations: int
    converged: bool
    jtj: np.ndarray | None = None  # J^T J at x if the last Jacobian was evaluated at x


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


def _dense_step(H: np.ndarray, lam_diag: np.ndarray, g: np.ndarray) -> np.ndarray:
    """Default linear step: dx = -(H + diag(lam_diag))^-1 g (dense LU)."""
    return -np.linalg.solve(H + np.diag(lam_diag), g)


def levenberg_marquardt(fun: Callable[[np.ndarray], np.ndarray], x0: np.ndarray,
                        jac: Callable[[np.ndarray], np.ndarray] | None = None,
                        max_iter: int = 100, tol: float = 1e-10, lam0: float = 1e-3,
                        fd_step: float = 1e-6,
                        retract: Callable[[np.ndarray, np.ndarray], np.ndarray] | None = None, *,
                        step_solver: Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray] | None = None,
                        project: Callable[[np.ndarray], np.ndarray] | None = None) -> LMResult:
    """Minimise 0.5*||fun(x)||^2.

    `retract(x, dx)` applies a step on a manifold (e.g. multiplicative rotation
    updates); `jac` must then be the Jacobian w.r.t. that local step. Default is
    plain addition. `step_solver` and `project` are described in the module
    docstring; both default to the legacy behaviour.
    """
    # Damping follows Nielsen's rule (Madsen, Nielsen & Tingleff 2004) with
    # Marquardt diagonal scaling: on success lam *= max(1/3, 1-(2*rho-1)^3), nu = 2;
    # on failure lam *= nu, nu *= 2, where rho = actual / predicted cost reduction.
    step_fn = retract if retract is not None else (lambda a, b: a + b)
    solve = step_solver if step_solver is not None else _dense_step
    x = np.asarray(x0, float).copy()
    if project is not None:
        x = np.asarray(project(x), float)
    r = fun(x)
    cost = 0.5 * float(r @ r)
    lam, nu = lam0, 2.0
    for it in range(1, max_iter + 1):
        J = jac(x) if jac is not None else numeric_jacobian(fun, x, r, fd_step)
        g = J.T @ r
        H = J.T @ J
        if np.max(np.abs(g)) < tol:
            return LMResult(x, cost, it, True, H)
        diag = np.diag(H).copy()
        diag[diag <= 0] = 1e-12
        improved = False
        for _ in range(30):
            try:
                dx = solve(H, lam * diag, g)
            except np.linalg.LinAlgError:
                lam *= nu
                nu *= 2.0
                continue
            x_new = step_fn(x, dx)
            if project is not None:
                x_new = np.asarray(project(x_new), float)
            r_new = fun(x_new)
            cost_new = 0.5 * float(r_new @ r_new)
            predicted = 0.5 * float(dx @ (lam * diag * dx - g))
            if np.isfinite(cost_new) and cost_new < cost and predicted > 0:
                rho = min((cost - cost_new) / predicted, _RHO_CLIP)
                rel = (cost - cost_new) / max(cost, 1e-300)
                x, r, cost = x_new, r_new, cost_new
                lam = max(lam * max(1.0 / 3.0, 1.0 - (2.0 * rho - 1.0) ** 3), 1e-15)
                nu = 2.0
                improved = True
                if rel < tol or np.linalg.norm(dx) < tol * (np.linalg.norm(x) + tol):
                    return LMResult(x, cost, it, True)
                break
            lam *= nu
            nu *= 2.0
        if not improved:
            return LMResult(x, cost, it, True, H)
    return LMResult(x, cost, max_iter, False)
