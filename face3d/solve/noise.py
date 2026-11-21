"""Observation noise model in millimetres by landmark kind (DESIGN 4.4, D-05, D-06, D-09).

Implements the per-view landmark covariance of DESIGN 4.4 (without the robust scale
nu_v of 4.5 and the expression term of 4.9, which later work packages add):

    Sigma_iv = p_iv^2 m_iv^2 eta_i R(t_i) diag(sigma_n,i^2, sigma_t,i^2) R(t_i)^T
               + (sigma_tta,iv^2 + sigma_floor,iv^2) I_2                       [px^2]

Conventions and units
---------------------
* ``px_per_mm`` p_iv = f_v / z_iv: pixels per millimetre at the landmark's camera
  depth z_iv (D-05: sigma is stored in mm and converted per view at each point's
  depth, which removes the 63-vs-88 mm IOD ambiguity of percentage-of-IOD rules).
* Image tangents ``t_i`` are 2D image-space vectors (any length; normalised here).
  The covariance axes are the unit normal n = (-t_y, t_x) with sigma_n and the unit
  tangent t with sigma_t.  A tangent that is ``None``, non-finite or of zero length is
  *unknown*: the covariance is isotropic with sigma_iso^2 = (sigma_n^2 + sigma_t^2)/2,
  except for the point-like kinds sharp_junction, extremal and iris, which use sigma_n
  (WBS WP-07).  For kinds whose tangent is "free" in DESIGN 4.4 (contour, brow) the
  tangent sigma is a large finite number (normal-only in practice).
* ``m_iv`` are occluder / makeup multipliers (DESIGN 4.1, 1 by default); ``eta_i`` is
  the dense-point inflation N/N_eff for points flagged in ``dense_mask`` (DESIGN 4.4,
  rec BA-2: correlated dense MediaPipe points), else 1.  N is ``n_total`` (default:
  the number of landmarks).
* ``sigma_floor = max(floor_min_px, k * face_px / floor_crop_px)`` px, with k by floor
  class (inner 0.6, iris 0.4, brow 1.0, contour 1.5; bl ML: "u = face width px / 256").
  ``face_px`` is the face width in image pixels.
* The **definition bias** sigma_def (D-06) is a per-landmark offset shared by all
  views; it is *never* part of Sigma_iv.  :meth:`NoiseModel.sigma_def_mm` returns it
  for the reported-uncertainty floor of the bundle (DESIGN 4.13).
* User pins (D-09): sigma_px = sqrt((p * sigma_class)^2 + (1 / zoom)^2) with zoom in
  screen px per image px at placement (:func:`pin_sigma_px`).

Numeric defaults
----------------
Every number is registered with :mod:`face3d.core.config` under the namespace
``noise`` (keys ``<kind>_sigma_n_mm``, ``<kind>_sigma_t_mm``, ``<kind>_sigma_def_mm``,
``pin_<class>_mm``, ``floor_k_<class>``, ``floor_min_px``, ``floor_crop_px``,
``n_eff``), each with its badge and source.  Almost all are 🧠 / ↔️ / 🆕, i.e.
PROVISIONAL until the M7 calibration (DESIGN 8).  The module constants
:data:`KIND_SIGMA_MM`, :data:`KIND_SIGMA_DEF_MM`, :data:`PIN_CLASS_SIGMA_MM`,
:data:`FLOOR_K` and :data:`N_EFF` are the registered default values; pass a resolved
config (``core.config.resolve`` output) as ``cfg`` to use overrides.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from ..core.config import Default, register_defaults

__all__ = [
    "NOISE", "KINDS", "PIN_CLASSES", "FLOOR_CLASSES", "FLOOR_CLASS_OF_KIND", "POINT_LIKE_KINDS",
    "KIND_SIGMA_MM", "KIND_SIGMA_DEF_MM", "PIN_CLASS_SIGMA_MM", "FLOOR_K", "N_EFF",
    "FLOOR_MIN_PX", "FLOOR_CROP_PX", "NoiseModel", "pin_sigma_px", "whitening", "kind_tables",
]

_BRAIN = "\U0001F9E0"   # expert knowledge, provisional
_ARROWS = "↔️"          # contested
_NEW = "\U0001F195"     # introduced by this design / WP spec, uncalibrated

#: Landmark kinds (DESIGN 3.2 scheme ``kind``; same set as model.registry.SCHEME_KINDS).
KINDS: tuple[str, ...] = ("sharp_junction", "extremal", "curve", "contour", "brow", "iris", "hair", "generic")
#: Kinds that use sigma_n (not the normal/tangent average) when the tangent is unknown (WBS WP-07).
POINT_LIKE_KINDS: frozenset[str] = frozenset({"sharp_junction", "extremal", "iris"})
#: Detector-floor classes (bl ML; research/blender/README.md "Detector noise floor").
FLOOR_CLASSES: tuple[str, ...] = ("inner", "iris", "brow", "contour")
#: Floor class of each kind.  bl ML names inner points, iris, brows and contour; the
#: mapping of sharp_junction / extremal / curve / generic to 'inner' and of hair
#: (an outline) to 'contour' is a WP-07 choice (🆕, provisional).
FLOOR_CLASS_OF_KIND: dict[str, str] = {
    "sharp_junction": "inner", "extremal": "inner", "curve": "inner", "generic": "inner",
    "iris": "iris", "brow": "brow", "contour": "contour", "hair": "contour",
}
#: User-pin classes (D-09; research/blender/guided-workflow-accessibility.md Table 2).
PIN_CLASSES: tuple[str, ...] = ("crisp_expert", "crisp_novice", "contour", "alar_base", "nose_tip", "ears",
                                "palpation", "hair_defined")

_D44 = "DESIGN 4.4 table"
_LIC = "landmark-index-correspondence 'Default sigma'"
# kind: (sigma_n, sigma_t, sigma_def, badge_n_t, source_n_t, badge_def, source_def)
_KIND_TABLE: dict[str, tuple[float, float, float, str, str, str, str]] = {
    "sharp_junction": (1.25, 1.25, 0.5, _BRAIN, f"{_D44} sharp_junction 1.25/1.25 (anat R4.1; {_LIC} 1.0-1.5)",
                       _BRAIN, f"{_D44} sigma_def 0.5 (D-06)"),
    "extremal": (2.0, 3.0, 1.5, _BRAIN, f"{_D44} extremal 2.0/3.0 ({_LIC} 1.5-2.5 / 2-4)",
                 _BRAIN, f"{_D44} sigma_def 1.5 (D-06)"),
    "curve": (1.5, 7.5, 1.0, _BRAIN, f"{_D44} curve 1.5/7.5 ({_LIC} 1.0-2.0 / 5 or free)",
              _BRAIN, f"{_D44} sigma_def 1.0 (D-06)"),
    # Contour tangent is 'free (normal-only)' in DESIGN 4.4; 1000 mm encodes it (WBS WP-07).
    "contour": (2.5, 1000.0, 2.0, _BRAIN, f"{_D44} contour 2.5 / free; tangent 1000 mm = normal-only (WBS WP-07)",
                _BRAIN, f"{_D44} sigma_def 2.0 (D-06)"),
    # Brow tangent is 'free' in DESIGN 4.4; 40 mm encodes it (WBS WP-07).
    "brow": (4.0, 40.0, 2.0, _BRAIN, f"{_D44} brow 4.0 / free; tangent 40 mm (WBS WP-07) ({_LIC} 3-5)",
             _BRAIN, f"{_D44} sigma_def 2.0 (D-06)"),
    # Iris centre: gaze-dependent, never a shape landmark; no definition bias ('-').
    "iris": (0.6, 0.6, 0.0, _BRAIN, f"{_D44} iris centre 0.6/0.6 ([Art 3.1])",
             _BRAIN, f"{_D44} iris sigma_def '-' (never a shape landmark) -> 0"),
    # Hair-defined points (trichion) are not in the DESIGN 4.4 table; WBS WP-07 / WP-03 value.
    "hair": (4.0, 8.0, 3.0, _NEW, "WBS WP-07 / WP-03 hair (trichion) 4.0/8.0 (not in DESIGN 4.4)",
             _NEW, "WBS WP-07 / WP-03 hair sigma_def 3.0"),
    "generic": (2.0, 2.0, 1.5, _NEW, f"{_D44} generic dense point 2.0/2.0 (🆕)",
                _NEW, f"{_D44} generic sigma_def 1.5 (🆕)"),
}

_GW = "D-09 / DESIGN 4.4 user pins; guided-workflow-accessibility Table 2"
# class: (sigma_mm, badge, source)
_PIN_TABLE: dict[str, tuple[float, str, str]] = {
    "crisp_expert": (0.8, _BRAIN, f"{_GW} crisp corners, expert 0.8 mm"),
    "crisp_novice": (1.2, _BRAIN, f"{_GW} crisp corners, novice 1.2 mm (default class)"),
    "contour": (1.0, _BRAIN, f"{_GW} contours / profile silhouettes 1.0 mm"),
    "alar_base": (1.8, _BRAIN, f"{_GW} alar base 1.8 mm"),
    "nose_tip": (2.0, _ARROWS, f"{_GW} nose tip 2.0 mm (contested)"),
    "ears": (2.5, _BRAIN, f"{_GW} ear points 2.5 mm"),
    "palpation": (4.5, _ARROWS, f"{_GW} palpation-defined 4-5 mm (midpoint 4.5, contested)"),
    "hair_defined": (5.0, _BRAIN, f"{_GW} hair-defined 5 mm"),
}

_ML = "bl ML (research/blender/README.md 'Detector noise floor', u = face width px / 256)"
_FLOOR_TABLE: dict[str, float] = {"inner": 0.6, "iris": 0.4, "brow": 1.0, "contour": 1.5}


def _build_defaults() -> dict[str, Default]:
    d: dict[str, Default] = {}
    for kind, (sn, st, sdef, b_nt, s_nt, b_def, s_def) in _KIND_TABLE.items():
        d[f"{kind}_sigma_n_mm"] = Default(sn, b_nt, s_nt + " (normal)", "mm", (1e-6, None))
        d[f"{kind}_sigma_t_mm"] = Default(st, b_nt, s_nt + " (tangent)", "mm", (1e-6, None))
        d[f"{kind}_sigma_def_mm"] = Default(sdef, b_def, s_def, "mm", (0.0, None))
    for cls, (s, badge, src) in _PIN_TABLE.items():
        d[f"pin_{cls}_mm"] = Default(s, badge, src, "mm", (1e-6, None))
    for cls, k in _FLOOR_TABLE.items():
        d[f"floor_k_{cls}"] = Default(k, _BRAIN, f"{_ML}: {cls} {k}u", "", (0.0, None))
    d["floor_min_px"] = Default(0.5, _BRAIN, f"{_ML}; DESIGN 4.4 sigma_floor = max(0.5 px, k face_px/256)", "px",
                                (0.0, None))
    d["floor_crop_px"] = Default(256.0, _BRAIN, f"{_ML}: detector input crop 256 px", "px", (1.0, None))
    d["n_eff"] = Default(80.0, _BRAIN, "DESIGN 4.4 eta = N/N_eff, N_eff 80 (range 60-100; rec BA-2; "
                                       "landmark-detection 'Correlated dense outputs')", "points", (1.0, None))
    return d


#: The registered ``noise`` namespace (DESIGN 0: every provisional number is a named default).
NOISE = register_defaults("noise", _build_defaults())


def _cfg_value(key: str, cfg: Mapping[str, Any] | None = None) -> Any:
    """Resolved value of ``noise.<key>`` from ``cfg`` (``core.config.resolve`` output) or the default."""
    if cfg:
        v = cfg.get("noise." + key)
        if v is not None:
            return v
    return NOISE[key].value


def kind_tables(cfg: Mapping[str, Any] | None = None) -> dict[str, dict]:
    """The kind / pin / floor tables with ``cfg`` overrides applied.

    Returns ``{'sigma_mm': {kind: (sigma_n, sigma_t)}, 'sigma_def_mm': {kind: s},
    'pin_mm': {class: s}, 'floor_k': {class: k}, 'floor_min_px', 'floor_crop_px', 'n_eff'}``.
    """
    return {
        "sigma_mm": {k: (float(_cfg_value(f"{k}_sigma_n_mm", cfg)), float(_cfg_value(f"{k}_sigma_t_mm", cfg)))
                     for k in KINDS},
        "sigma_def_mm": {k: float(_cfg_value(f"{k}_sigma_def_mm", cfg)) for k in KINDS},
        "pin_mm": {c: float(_cfg_value(f"pin_{c}_mm", cfg)) for c in PIN_CLASSES},
        "floor_k": {c: float(_cfg_value(f"floor_k_{c}", cfg)) for c in FLOOR_CLASSES},
        "floor_min_px": float(_cfg_value("floor_min_px", cfg)),
        "floor_crop_px": float(_cfg_value("floor_crop_px", cfg)),
        "n_eff": float(_cfg_value("n_eff", cfg)),
    }


_T = kind_tables()
#: (sigma_normal, sigma_tangent) in mm by kind (DESIGN 4.4; registered defaults).
KIND_SIGMA_MM: dict[str, tuple[float, float]] = dict(_T["sigma_mm"])
#: Definition-bias SD in mm per axis by kind (DESIGN 4.4 / D-06; registered defaults).
KIND_SIGMA_DEF_MM: dict[str, float] = dict(_T["sigma_def_mm"])
#: User-pin class sigma in mm (D-09; registered defaults).
PIN_CLASS_SIGMA_MM: dict[str, float] = dict(_T["pin_mm"])
#: Detector-floor multipliers k by floor class (bl ML; registered defaults).
FLOOR_K: dict[str, float] = dict(_T["floor_k"])
#: Effective number of independent dense points (DESIGN 4.4; registered default).
N_EFF: float = _T["n_eff"]
#: Minimum detector floor in px and the detector crop size in px (bl ML).
FLOOR_MIN_PX: float = _T["floor_min_px"]
FLOOR_CROP_PX: float = _T["floor_crop_px"]
del _T


def _check_kinds(kinds: Sequence[Any]) -> list[str]:
    out = []
    for i, k in enumerate(kinds):
        k = "generic" if k is None else str(k)
        if k not in KIND_SIGMA_MM:
            raise ValueError(f"landmark {i}: unknown kind {k!r} (expected one of {KINDS})")
        out.append(k)
    return out


def _vec(a: Any, n: int, name: str, default: float) -> np.ndarray:
    if a is None:
        return np.full(n, float(default))
    v = np.asarray(a, dtype=float)
    if v.ndim == 0:
        return np.full(n, float(v))
    v = v.reshape(-1)
    if v.shape != (n,):
        raise ValueError(f"{name} must have shape ({n},), got {np.shape(a)}")
    return v


class NoiseModel:
    """Per-landmark observation noise from landmark kinds (DESIGN 4.4).

    Parameters
    ----------
    kinds : one kind per landmark (:data:`KINDS`; ``None`` entries mean 'generic').
    dense_mask : optional (N,) bool, True for correlated dense detector points outside
        the curated subset; their variance is inflated by eta = max(1, n_total / N_EFF).
        The WBS formula is eta = n_total / N_EFF; the floor at 1 (an inflation never
        deflates, DESIGN 4.4 / rec BA-2 "inflate sigma") is a WP-07 choice.
    n_total : N of eta (the detector's total point count); default ``len(kinds)``.
    cfg : optional resolved config (``core.config.resolve()``) with ``noise.*`` overrides.
    """

    def __init__(self, kinds: Sequence[str | None], dense_mask: Any = None, n_total: int | None = None, *,
                 cfg: Mapping[str, Any] | None = None):
        self.kinds = _check_kinds(list(kinds))
        n = len(self.kinds)
        self.n = n
        tab = kind_tables(cfg)
        self._tab = tab
        s = np.array([tab["sigma_mm"][k] for k in self.kinds], float).reshape(n, 2)
        self.sigma_nt_mm = s                                                   # (N, 2)
        point_like = np.array([k in POINT_LIKE_KINDS for k in self.kinds], bool)
        iso2 = np.where(point_like, s[:, 0] ** 2, 0.5 * (s[:, 0] ** 2 + s[:, 1] ** 2))
        self.sigma_iso_mm = np.sqrt(iso2)                                      # (N,)
        self.floor_k = np.array([tab["floor_k"][FLOOR_CLASS_OF_KIND[k]] for k in self.kinds], float)
        self.n_total = int(n if n_total is None else n_total)
        if self.n_total <= 0:
            raise ValueError("n_total must be positive")
        if dense_mask is None:
            dm = np.zeros(n, bool)
        else:
            dm = np.asarray(dense_mask, bool).reshape(-1)
            if dm.shape != (n,):
                raise ValueError(f"dense_mask must have shape ({n},), got {np.shape(dense_mask)}")
        self.dense_mask = dm
        eta_dense = max(1.0, self.n_total / tab["n_eff"])
        self.eta = np.where(dm, eta_dense, 1.0)                                # (N,)

    # ------------------------------------------------------------------ covariances
    def floor_px(self, face_px: float | None) -> np.ndarray:
        """Detector floor (N,) px: max(floor_min_px, k * face_px / floor_crop_px); min only if face_px is None."""
        fmin = self._tab["floor_min_px"]
        if face_px is None or not np.isfinite(face_px):
            return np.full(self.n, fmin)
        if face_px < 0:
            raise ValueError("face_px must be >= 0")
        return np.maximum(fmin, self.floor_k * float(face_px) / self._tab["floor_crop_px"])

    def view_cov(self, px_per_mm: Any, face_px: float | None, tangents: Any = None, multipliers: Any = None,
                 tta_px: Any = None) -> np.ndarray:
        """(N, 2, 2) image covariance in px^2 for one view (DESIGN 4.4, without nu_v and expression).

        ``px_per_mm`` (N,) = f / z_i at each landmark's depth; ``face_px`` face width in px
        (None: floor_min_px only); ``tangents`` (N, 2) image tangents or None (unknown rows:
        NaN / zero); ``multipliers`` (N,) m_iv (default 1); ``tta_px`` (N,) test-time
        augmentation spread in px (default 0).  Rows with non-finite ``px_per_mm`` are NaN.
        """
        n = self.n
        p = _vec(px_per_mm, n, "px_per_mm", np.nan)
        m = _vec(multipliers, n, "multipliers", 1.0)
        tta = _vec(tta_px, n, "tta_px", 0.0)
        if np.any(m[np.isfinite(m)] < 0) or np.any(tta[np.isfinite(tta)] < 0):
            raise ValueError("multipliers and tta_px must be >= 0")
        sn2 = self.sigma_nt_mm[:, 0] ** 2
        st2 = self.sigma_nt_mm[:, 1] ** 2
        S = np.zeros((n, 2, 2))
        iso2 = self.sigma_iso_mm ** 2
        S[:, 0, 0] = iso2
        S[:, 1, 1] = iso2
        if tangents is not None:
            T = np.asarray(tangents, dtype=float)
            if T.shape != (n, 2):
                raise ValueError(f"tangents must have shape ({n}, 2), got {T.shape}")
            norm = np.linalg.norm(T, axis=1)
            known = np.isfinite(norm) & (norm > 1e-12)
            if known.any():
                t = T[known] / norm[known, None]
                nv = np.column_stack([-t[:, 1], t[:, 0]])
                S[known] = (sn2[known, None, None] * np.einsum("ni,nj->nij", nv, nv)
                            + st2[known, None, None] * np.einsum("ni,nj->nij", t, t))
        S *= (p ** 2 * m ** 2 * self.eta)[:, None, None]
        add = tta ** 2 + self.floor_px(face_px) ** 2
        S[:, 0, 0] += add
        S[:, 1, 1] += add
        S[~np.isfinite(p)] = np.nan
        return S

    def sigma_def_mm(self) -> np.ndarray:
        """Definition-bias SD (N,) in mm per axis (D-06; DESIGN 4.4 sigma_def column)."""
        return np.array([self._tab["sigma_def_mm"][k] for k in self.kinds], float)

    def __repr__(self) -> str:
        return f"NoiseModel(n={self.n}, dense={int(self.dense_mask.sum())}, n_total={self.n_total})"


def pin_sigma_px(cls: str, px_per_mm: Any, zoom: Any, cfg: Mapping[str, Any] | None = None) -> np.ndarray | float:
    """User-pin sigma in px: sqrt((px_per_mm * sigma_class)^2 + (1 / zoom)^2) (D-09, DESIGN 4.4).

    ``cls`` is one of :data:`PIN_CLASSES` (novice crisp, 1.2 mm, is the default class for a
    crisp corner); ``zoom`` = screen px per image px at placement (> 0).  Broadcasts over
    array inputs; returns a float for scalar inputs.
    """
    if cls not in PIN_CLASSES:
        raise ValueError(f"unknown pin class {cls!r} (expected one of {PIN_CLASSES})")
    s = float(_cfg_value(f"pin_{cls}_mm", cfg))
    p = np.asarray(px_per_mm, dtype=float)
    z = np.asarray(zoom, dtype=float)
    if np.any(~(z > 0)):
        raise ValueError("zoom must be > 0 (screen px per image px)")
    out = np.sqrt((p * s) ** 2 + (1.0 / z) ** 2)
    return float(out) if out.ndim == 0 else out


def whitening(cov: Any) -> np.ndarray:
    """Inverse lower Cholesky factors W_i (N, 2, 2) of covariances ``cov`` (N, 2, 2).

    With cov_i = L_i L_i^T (L_i lower), W_i = L_i^-1, so W_i^T W_i = cov_i^-1 and
    ||W_i r||^2 = r^T cov_i^-1 r.  Rows with non-finite entries give NaN rows; a finite
    row that is not symmetric positive definite raises ``ValueError``.
    """
    C = np.asarray(cov, dtype=float)
    if C.ndim != 3 or C.shape[1:] != (2, 2):
        raise ValueError(f"cov must have shape (N, 2, 2), got {C.shape}")
    W = np.full(C.shape, np.nan)
    ok = np.isfinite(C).all(axis=(1, 2))
    if not ok.any():
        return W
    c = C[ok]
    s11 = c[:, 0, 0]
    s21 = 0.5 * (c[:, 1, 0] + c[:, 0, 1])
    s22 = c[:, 1, 1]
    bad = ~(s11 > 0)
    a = np.sqrt(np.where(bad, 1.0, s11))
    b = s21 / a
    c2 = s22 - b * b
    bad |= ~(c2 > 1e-14 * np.maximum(np.abs(s22), 1e-300))
    if bad.any():
        idx = np.flatnonzero(ok)[bad]
        raise ValueError(f"covariance rows {idx[:10].tolist()} are not symmetric positive definite")
    cc = np.sqrt(c2)
    w = np.zeros_like(c)
    w[:, 0, 0] = 1.0 / a
    w[:, 1, 0] = -b / (a * cc)
    w[:, 1, 1] = 1.0 / cc
    W[ok] = w
    return W
