"""Landmark-level synthetic subjects for the test bed (DESIGN 7.2, D-30).

Subjects are generated **independently of the fitted prior** (no inverse crime,
DESIGN D-30): this module must not import anything from ``face3d.model`` (checked
by an AST test). Both generators work on the legacy illustrative landmark template
of :func:`face3d.synthetic.synthetic_landmarks` (32 points, head frame in mm:
+x subject's left, +y up, +z out of the face, origin near the head centre).

Each generator returns ``(names, X_true, meta)`` with ``meta`` holding:

* ``generator``      - ``'legacy_random'`` or ``'smooth_field'``;
* ``log_scale_true`` - log of the Umeyama similarity scale s in
  ``X_true ≈ s R template + t`` (the subject's size relative to the template);
* ``inverse_crime``  - always ``False`` here (diagnostic prior-drawn subjects, if
  ever added, must set it ``True`` and never set thresholds; DESIGN 7.2);
* ``template``       - the (N, 3) template used, i.e. the legacy prior mean.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np

from ..geometry.procrustes import umeyama
from ..synthetic import midline_indices, mirror_pairs, random_subject, synthetic_landmarks

__all__ = ["LOG_SCALE_SD", "legacy_subject", "smooth_field_subject", "log_scale_of"]

# Head-size log-scale SD (DESIGN 4.7: zeta ~ N(0, 0.045^2); validation-test-bed.md
# "head-size CV ~4-5 %"; the CV itself is unverified there, so this is provisional).
LOG_SCALE_SD = 0.045

# Legacy identity generator settings (WBS WP-01; face3d.synthetic.random_subject
# defaults, with scale_sd raised from 0.04 to the 0.045 population value above).
LEGACY_IDENTITY_SD_MM = 4.0
LEGACY_ASYM_SD_MM = 1.0

# Smooth-field generator defaults (WBS WP-01 spec; DESIGN 7.2 "smooth Gaussian-RBF
# displacement fields ... with symmetric and asymmetric parts"). PROVISIONAL: these
# are test-bed design choices, not anatomical measurements.
SMOOTH_AMP_MM = 4.0
# Asymmetry scale: research/anatomy/facial-asymmetry.md gives whole-face mirror RMSD
# ~0.8 mm (and 0.6-4.6 mm bilateral landmark differences); used here as a per-coordinate
# SD, which is a test-bed choice (PROVISIONAL).
SMOOTH_ASYM_MM = 0.8
SMOOTH_N_BUMPS = 12
SMOOTH_WIDTH_MM = (25.0, 60.0)
# Bump centres are drawn around a random template landmark with this isotropic SD
# ("random centres near the face", WBS WP-01). PROVISIONAL.
SMOOTH_CENTRE_JITTER_MM = 10.0

_MIRROR = np.array([-1.0, 1.0, 1.0])


def log_scale_of(X: np.ndarray, template: np.ndarray) -> float:
    """log s of the Umeyama similarity mapping ``template`` onto ``X`` (size ratio)."""
    s, _, _ = umeyama(np.asarray(template, float), np.asarray(X, float), with_scale=True)
    return float(np.log(s))


def _symmetrise(X: np.ndarray, names: Sequence[str]) -> np.ndarray:
    """Exact bilateral symmetrisation as in face3d.synthetic.random_subject."""
    X = X.copy()
    for l, r in mirror_pairs(list(names)):
        avg = (X[l] + X[r] * _MIRROR) / 2.0
        X[l], X[r] = avg, avg * _MIRROR
    X[midline_indices(list(names)), 0] = 0.0
    return X


def legacy_subject(rng: np.random.Generator, *, identity_sd: float = LEGACY_IDENTITY_SD_MM,
                   asym_sd: float = LEGACY_ASYM_SD_MM, scale_sd: float = LOG_SCALE_SD
                   ) -> tuple[list[str], np.ndarray, dict]:
    """Legacy polynomial-field subject: :func:`face3d.synthetic.random_subject` on the
    legacy template (identity_sd 4 mm, asym_sd 1 mm, scale_sd 0.045; WBS WP-01).

    Note (validation-test-bed.md, "Inverse crime"): this warps the legacy prior's own
    template smoothly, so errors measured on it are optimistic lower bounds.
    """
    names, template = synthetic_landmarks()
    X = random_subject(template, names, rng, identity_sd=identity_sd, asym_sd=asym_sd,
                       scale_sd=scale_sd)
    meta = {
        "generator": "legacy_random",
        "log_scale_true": log_scale_of(X, template),
        "inverse_crime": False,
        "template": template,
    }
    return names, X, meta


def smooth_field_subject(rng: np.random.Generator, names: Sequence[str] | None = None,
                         template: np.ndarray | None = None, amp_mm: float = SMOOTH_AMP_MM,
                         asym_mm: float = SMOOTH_ASYM_MM, n_bumps: int = SMOOTH_N_BUMPS,
                         width_mm: tuple[float, float] = SMOOTH_WIDTH_MM,
                         log_scale_sd: float = LOG_SCALE_SD) -> tuple[list[str], np.ndarray, dict]:
    """Independent smooth Gaussian-RBF field subject (DESIGN 7.2; WBS WP-01).

    X = e^zeta * sym(T + sum_k a_k exp(-|T - c_k|^2 / (2 w_k^2)) u_k) + eps, with

    * c_k = T[j_k] + N(0, 10^2 I) mm for a uniformly chosen landmark j_k (near the face),
    * u_k uniform unit directions, a_k ~ N(0, amp_mm^2), w_k ~ U(width_mm) mm,
    * sym(.) the exact bilateral symmetrisation used by ``random_subject``
      (mirror pairs averaged, midline x set to 0),
    * eps ~ N(0, asym_mm^2) per coordinate (true asymmetry),
    * zeta ~ N(0, log_scale_sd^2) (isotropic size about the head-frame origin).

    ``names``/``template`` default to the legacy synthetic landmarks.
    """
    if (names is None) != (template is None):
        raise ValueError("give both names and template, or neither")
    if names is None:
        names, template = synthetic_landmarks()
    names = list(names)
    T = np.asarray(template, float)
    n = len(T)
    # Draw order is fixed (centres, jitter, directions, amplitudes, widths, zeta, eps)
    # so a seed always gives the same subject.
    anchors = rng.integers(0, n, size=n_bumps)
    centres = T[anchors] + rng.normal(scale=SMOOTH_CENTRE_JITTER_MM, size=(n_bumps, 3))
    u = rng.normal(size=(n_bumps, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    a = rng.normal(scale=amp_mm, size=n_bumps)
    w = rng.uniform(width_mm[0], width_mm[1], size=n_bumps)
    zeta = float(rng.normal(scale=log_scale_sd))
    eps = rng.normal(scale=asym_mm, size=T.shape)

    d2 = np.sum((T[:, None, :] - centres[None, :, :]) ** 2, axis=2)        # (N, K)
    phi = np.exp(-d2 / (2.0 * w[None, :] ** 2))                            # (N, K)
    D = T + (phi * a[None, :]) @ u                                          # (N, 3)
    X = _symmetrise(np.exp(zeta) * D, names) + eps
    meta = {
        "generator": "smooth_field",
        "log_scale_true": log_scale_of(X, T),
        "inverse_crime": False,
        "template": T.copy(),
        "zeta_drawn": zeta,
    }
    return names, X, meta
