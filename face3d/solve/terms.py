"""Pluggable residual terms and shape models of the landmark bundle (DESIGN D-01, 4.8; WBS WP-10).

Two protocols let later work packages extend :func:`face3d.solve.bundle.bundle_adjust`
without a second solver (DESIGN D-01 "one landmark solver"):

* :class:`Term`: an extra residual block with its own parameters (scale references such as
  a caliper chord, iris diameter, contours, pins on surfaces; DESIGN 4.7, 4.8, 4.16).
* :class:`ShapeModel`: the parameterisation of the N landmarks, X = points(q).  The default
  :class:`FreePoints` is the identity (q = vec X, 3N parameters) and keeps the bundle's
  fast per-point Jacobian path; a low-dimensional model (e.g. WP-17's ``LinearBasis``,
  X = e^zeta (X_bar + Phi Pi c)) supplies a dense Jacobian dX/dq and every residual on X
  (data, shape prior, symmetry, gauge, terms) reaches q through the chain rule.

Conventions (DESIGN 3.1)
------------------------
Head frame in mm (+x subject's left, +y up, +z out of the face); OpenCV cameras
X_c = R X + t.  Inside the solver each view uses the inverse-depth block of DESIGN D-02 /
4.3: u = c + s ((R X)_xy + tau) / (1 + rho (R X)_z), f = s / rho, t = (tau, 1 / rho), with
the parameter block (in this order)

* ``'free'``: (omega_x, omega_y, omega_z, tau_x, tau_y, rho_per_m, a), a = ln s, 7 parameters;
* ``'hard'`` (focal shared exactly by a focal group, s = e^phi_G rho) and ``'fixed_f'``
  (known focal, s = f rho): (omega_x, omega_y, omega_z, tau_x, tau_y, rho_per_m), 6 parameters.

omega is a *left-multiplicative* rotation increment, R <- exp([omega]_x) R; tau in mm,
a in ln(px/mm); the stored rho parameter is in 1/m (= 1000 x rho in 1/mm, so a block
derivative d/d rho_param = 1e-3 d/d rho_mm), while ``SolverState.invdepth[v]['rho']`` is
in 1/mm.  Derivatives of a term with respect to a camera block
(``'cam:<v>'``) must use the same convention: d/d omega is the derivative with respect
to the left increment at omega = 0.

Term protocol
-------------
``name`` (str); ``n_params()`` -> k; ``init_params(state)`` -> (k,) initial values;
``residuals(state, p)`` -> (m,) whitened residuals (already divided by their sigma);
``jacobian(state, p)`` -> ``dict`` block name -> (m, size) array with block names

* ``'X'``: (m, 3N), derivative with respect to the point-major vec(X) (head frame, mm);
* ``'zeta'``: (m,) or (m, 1), derivative with respect to the global log-scale (only when
  the bundle has zeta enabled);
* ``'cam:<v>'``: (m, 6 or 7), derivative with respect to view v's camera block in the
  order above;
* ``'self'``: (m, k), derivative with respect to the term's own parameters;
* any other key equal to a name of ``state.param_index`` (e.g. ``'focal_0'``, ``'jaw_2'``):
  (m, width of that slice).

Missing blocks are zero.  An optional attribute ``is_prior`` (default False) routes the
rows to H_prior (else H_data, where they also count in chi^2_red and p_eff).  The bundle
allocates each term's k parameters after the shape parameters, in the order of the
``terms`` list (``param_index['term:<name>']``).  ``state`` is a :class:`SolverState`
built at the parameter vector being evaluated.

ShapeModel protocol
-------------------
``n_params`` (int attribute or property); ``init(X0)`` -> q0; ``points(q)`` -> (N, 3);
``jacobian(q)`` -> (3N, n_params) dense dX/dq (point-major rows).  A model with a true
``is_identity`` attribute must be the identity map (only :class:`FreePoints`).

numpy + stdlib only.
"""
from __future__ import annotations

from typing import Any, Protocol, Sequence, runtime_checkable

import numpy as np

from ..geometry.camera import Camera, invdepth_to_camera

__all__ = ["SolverState", "Term", "ShapeModel", "FreePoints", "shape_n_params", "BLOCK_NAMES"]

#: Parameter names of the inverse-depth camera blocks by kind (DESIGN 4.3).
BLOCK_NAMES: dict[str, tuple[str, ...]] = {
    "free": ("omega_x", "omega_y", "omega_z", "tau_x", "tau_y", "rho_per_m", "a"),
    "hard": ("omega_x", "omega_y", "omega_z", "tau_x", "tau_y", "rho_per_m"),
    "fixed_f": ("omega_x", "omega_y", "omega_z", "tau_x", "tau_y", "rho_per_m"),
}


def _ro(a: Any) -> np.ndarray:
    out = np.array(a, dtype=float, copy=True)
    out.flags.writeable = False
    return out


class SolverState:
    """Read-only view of the bundle's state at one parameter vector (passed to :class:`Term`).

    Attributes
    ----------
    X : (N, 3) landmarks in the head frame, mm (the neutral points, before any jaw hinge).
    zeta : global log-scale, or None when disabled.
    invdepth : one dict per view with ``R`` (3, 3), ``tau`` (2,) mm, ``rho`` 1/mm, ``s``
        px/mm, ``a`` = ln s, ``f`` = s / rho px, ``kind`` ('free', 'hard', 'fixed_f') and
        ``block`` (parameter names of the view's camera block, :data:`BLOCK_NAMES`).
    param_index : name -> slice into the full parameter vector (``BundleResult.param_index``).
    cameras : list of :class:`~face3d.geometry.camera.Camera` (built on first access with
        :func:`~face3d.geometry.camera.invdepth_to_camera`).
    """

    __slots__ = ("_X", "_zeta", "_inv", "_like", "_cams", "_pi")

    def __init__(self, X: np.ndarray, zeta: float | None, invdepth: Sequence[dict], like: Sequence[Camera],
                 param_index: dict):
        self._X = _ro(X)
        self._zeta = None if zeta is None else float(zeta)
        inv = []
        for d in invdepth:
            e = dict(d)
            e["R"] = _ro(e["R"])
            e["tau"] = _ro(e["tau"])
            e["block"] = tuple(e["block"])
            inv.append(e)
        self._inv = tuple(inv)
        self._like = tuple(like)
        self._cams: list[Camera] | None = None
        self._pi = dict(param_index)

    @property
    def X(self) -> np.ndarray:
        return self._X

    @property
    def zeta(self) -> float | None:
        return self._zeta

    @property
    def invdepth(self) -> tuple[dict, ...]:
        return self._inv

    @property
    def param_index(self) -> dict:
        return dict(self._pi)

    @property
    def n_views(self) -> int:
        return len(self._inv)

    @property
    def cameras(self) -> list[Camera]:
        if self._cams is None:
            self._cams = [invdepth_to_camera(d["R"], d["tau"], d["s"], d["rho"], like)
                          for d, like in zip(self._inv, self._like)]
        return [c.copy() for c in self._cams]


@runtime_checkable
class Term(Protocol):
    """Extra residual block with its own parameters (see the module docstring)."""

    name: str

    def n_params(self) -> int: ...

    def init_params(self, state: SolverState) -> np.ndarray: ...

    def residuals(self, state: SolverState, p: np.ndarray) -> np.ndarray: ...

    def jacobian(self, state: SolverState, p: np.ndarray) -> dict: ...


@runtime_checkable
class ShapeModel(Protocol):
    """Parameterisation X = points(q) of the N landmarks (see the module docstring)."""

    def init(self, X0: np.ndarray) -> np.ndarray: ...

    def points(self, q: np.ndarray) -> np.ndarray: ...

    def jacobian(self, q: np.ndarray) -> np.ndarray: ...


def shape_n_params(model: Any) -> int:
    """``model.n_params`` as an int (accepts an attribute, a property or a method)."""
    n = getattr(model, "n_params")
    n = n() if callable(n) else n
    return int(n)


class FreePoints:
    """Identity shape model: q = vec(X) point-major, 3N parameters (the bundle default).

    ``is_identity`` tells :func:`~face3d.solve.bundle.bundle_adjust` to use its fast
    per-point Jacobian path (no dense 3N x 3N chain rule).
    """

    is_identity = True

    def __init__(self, n_points: int):
        n_points = int(n_points)
        if n_points < 0:
            raise ValueError("FreePoints needs n_points >= 0")
        self.N = n_points

    @property
    def n_params(self) -> int:
        return 3 * self.N

    def init(self, X0: np.ndarray) -> np.ndarray:
        X0 = np.asarray(X0, float)
        if X0.shape != (self.N, 3):
            raise ValueError(f"FreePoints({self.N}).init needs X0 of shape ({self.N}, 3), got {X0.shape}")
        return X0.reshape(-1).copy()

    def points(self, q: np.ndarray) -> np.ndarray:
        return np.asarray(q, float).reshape(self.N, 3)

    def jacobian(self, q: np.ndarray) -> np.ndarray:
        return np.eye(3 * self.N)

    def __repr__(self) -> str:
        return f"FreePoints({self.N})"
