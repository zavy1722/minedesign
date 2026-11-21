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
* Image tangents ``t_i`` are 2D image-space vectors.  The covariance axes are the unit
  normal n = (-t_y, t_x) with sigma_n and the unit tangent t with sigma_t.  For kinds whose
  tangent is "free" in DESIGN 4.4 (contour, brow) the tangent sigma is a large finite number
  (normal-only in practice).
* **Direction confidence is a separate column (WBS FU-04; review fix).**  A tangent array of
  shape (N, 2) holds directions that are known exactly, whatever their length (a unit vector,
  an unnormalised chord in px, any non-zero vector): the pre-FU-04 meaning, unchanged.  A
  tangent *estimated from detections* (:func:`image_tangents`) is an (N, 3) array
  (t_x, t_y, rho): rho in (0, 1] is the mean resultant length E[cos 2 delta] of the (axial)
  direction error delta.  The covariance is then the exact second moment of the error ellipse
  under that direction error, E[R(delta) diag(sigma_n^2, sigma_t^2) R(delta)^T] =
  diag(sigma_n^2 + s D, sigma_t^2 - s D) in the (n, t) frame with D = sigma_t^2 - sigma_n^2 and
  s = E[sin^2 delta] = (1 - rho) / 2.  It tends to the orientation average
  (sigma_n^2 + sigma_t^2) / 2 I_2 as rho -> 0 and never declares the normal direction
  tighter than the direction is known.  (The first FU-04 version encoded rho in the vector
  length, which silently changed the meaning of non-normalised (N, 2) tangents.)
* **'Free' tangent kinds under an uncertain direction (review fix).**  For contour and brow
  the tangent SD (1000 / 40 mm) is an *encoding* of 'no constraint along the curve', not an
  error spread, so it must not leak into the normal direction through the term s D: at
  rho = 0.95 a contour point would be declared 158 mm across its curve.  For
  :data:`FREE_ENCODED_KINDS` the leakage uses the finite slide of a curve sample,
  ``noise.free_tangent_leak_mm`` (7.5 mm, the DESIGN 4.4 curve tangent SD):
  sigma_n^2 + s max(leak^2 - sigma_n^2, 0) across, the 'free' sigma_t^2 along (unchanged).
* **Tangents come from the detections, never from ground truth (WBS FU-04).**
  :func:`image_tangents` derives the tangent of a landmark from the chord between its two
  scheme-defined neighbours on the same anatomical curve (scheme file key ``tangents``,
  :func:`scheme_tangent_pairs`), with rho (third column) from the neighbours' own declared noise; a chord
  that is hidden, shorter than its noise (rho < ``noise.tangent_min_rho``) or not defined by
  the scheme gives an *unknown* tangent.
* A tangent that is ``None``, non-finite or of zero length (or whose rho is non-finite or
  <= 0) is *unknown*, and the covariance
  is isotropic, sigma_iso^2 I_2 (before the p^2 m^2 eta factor), by kind
  (:data:`FREE_TANGENT_KINDS`):

  - curve-sample kinds whose tangent SD is 'free' (contour, brow: DESIGN 4.4 'free'; curve:
    *landmark-index-correspondence* '5 or free'), :data:`FREE_TANGENT_KINDS`: the orientation
    average sigma_iso^2 = (sigma_n^2 + sigma_t^2) / 2 (WBS WP-07, unchanged);
  - every other kind (sharp_junction, extremal, iris, hair, generic: a finite tangent SD
    that belongs to the point itself): sigma_iso^2 = max(sigma_n^2, sigma_t^2) (WBS FU-01).
    The error ellipse diag(sigma_n^2, sigma_t^2) has an unknown orientation, and the
    smallest isotropic covariance that dominates it in every orientation is max(.) I_2; the
    WP-07 rule sigma_n^2 understated the noise along the unknown tangent (extremal: 2.0 mm
    instead of DESIGN 4.4's 3.0 mm tangent SD).  Where sigma_n = sigma_t (sharp_junction,
    iris, generic) nothing changes; extremal goes from 2.0 to 3.0 mm and hair (trichion,
    4.0 / 8.0) from the average 6.3 to 8.0 mm.
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
``n_eff``, ``tangent_min_rho``, ``free_tangent_leak_mm``), each with its badge and source.  Almost all are 🧠 / ↔️ / 🆕, i.e.
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
    "FREE_TANGENT_KINDS", "unknown_tangent_var_mm2",
    "KIND_SIGMA_MM", "KIND_SIGMA_DEF_MM", "PIN_CLASS_SIGMA_MM", "FLOOR_K", "N_EFF",
    "FLOOR_MIN_PX", "FLOOR_CROP_PX", "NoiseModel", "pin_sigma_px", "whitening", "kind_tables",
]
# WBS FU-04 additions (public, import from this module: TANGENT_MIN_RHO, FREE_ENCODED_KINDS, tangent_rho,
# scheme_tangent_pairs, image_tangents).  They are not in __all__ because the package export list of face3d.solve is owned by
# WP-23 (tests/test_policy_ci.py requires every __all__ name to be re-exported there).

_BRAIN = "\U0001F9E0"   # expert knowledge, provisional
_ARROWS = "↔️"          # contested
_NEW = "\U0001F195"     # introduced by this design / WP spec, uncalibrated

#: Landmark kinds (DESIGN 3.2 scheme ``kind``; same set as model.registry.SCHEME_KINDS).
KINDS: tuple[str, ...] = ("sharp_junction", "extremal", "curve", "contour", "brow", "iris", "hair", "generic")
#: Point landmarks named by WBS WP-07 (sharp_junction, extremal, iris).  Kept for
#: compatibility; since WBS FU-01 the unknown-tangent rule is keyed on
#: :data:`FREE_TANGENT_KINDS` (these kinds use max(sigma_n^2, sigma_t^2), not sigma_n^2).
POINT_LIKE_KINDS: frozenset[str] = frozenset({"sharp_junction", "extremal", "iris"})
#: Curve-sample kinds whose tangent SD is 'free' (DESIGN 4.4: contour, brow; curve:
#: landmark-index-correspondence '5 or free'): with an unknown image tangent they keep the
#: WP-07 orientation average (sigma_n^2 + sigma_t^2) / 2.  Every other kind has a finite
#: tangent SD and uses max(sigma_n^2, sigma_t^2) (WBS FU-01; see the module docstring).
FREE_TANGENT_KINDS: frozenset[str] = frozenset({"curve", "contour", "brow"})
#: Kinds whose tangent SD is an encoding of 'free' (DESIGN 4.4: contour 1000 mm, brow 40 mm; WBS WP-07),
#: not a slide spread: under an uncertain tangent direction their leakage into the normal uses
#: ``noise.free_tangent_leak_mm`` (module docstring; WBS FU-04 review).
FREE_ENCODED_KINDS: frozenset[str] = frozenset({"contour", "brow"})
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
    d["tangent_min_rho"] = Default(0.5, _NEW, "WBS FU-04 task 1: a detection-derived image tangent is used only "
                                   "when the mean resultant length rho = exp(-2 sigma_delta^2) of its direction "
                                   "is >= 0.5 (direction SD <= 34 deg); below that the point keeps the "
                                   "unknown-tangent rule (FU-01). Provisional, uncalibrated", "", (0.0, 1.0))
    d["free_tangent_leak_mm"] = Default(7.5, _NEW, "WBS FU-04 review: slide spread used for the leakage of an "
                                        "uncertain tangent direction into the normal variance of the 'free' "
                                        "tangent kinds (contour, brow), whose tangent SD (1000 / 40 mm) only "
                                        "encodes 'unconstrained'. Value = DESIGN 4.4 curve tangent SD 7.5 mm "
                                        "(landmark-index-correspondence '5 or free'). Provisional, uncalibrated",
                                        "mm", (1e-6, None))
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
#: Smallest direction confidence rho of a usable detection-derived tangent (WBS FU-04; registered default).
TANGENT_MIN_RHO: float = float(NOISE["tangent_min_rho"].value)


def _split_tangents(tangents: Any, n: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    """(unit directions (N, 2) with NaN rows where unknown, rho (N,) with NaN where unknown) of a
    tangent array (N, 2) (exact directions of any length: rho = 1) or (N, 3) (t_x, t_y, rho)."""
    T = np.asarray(tangents, dtype=float)
    if T.ndim != 2 or T.shape[1] not in (2, 3) or (n is not None and len(T) != n):
        want = "(N" if n is None else f"({n}"
        raise ValueError(f"tangents must have shape {want}, 2) or {want}, 3), got {T.shape}")
    norm = np.linalg.norm(T[:, :2], axis=1)
    known = np.isfinite(norm) & (norm > 1e-12)
    rho = np.ones(len(T))
    if T.shape[1] == 3:
        r = T[:, 2]
        known &= np.isfinite(r) & (r > 0.0)
        rho = np.minimum(np.where(known, r, 1.0), 1.0)
    t = np.full((len(T), 2), np.nan)
    t[known] = T[known, :2] / norm[known, None]
    return t, np.where(known, rho, np.nan)


def tangent_rho(tangents: Any) -> np.ndarray:
    """(N,) direction confidence rho of image tangents: 1 for an (N, 2) row of any non-zero length
    (exact direction), the third column (clipped to 1) for (N, 3) rows; NaN for an unknown tangent
    (non-finite or zero direction, non-finite or non-positive rho).  See the module docstring."""
    return _split_tangents(tangents)[1]


def scheme_tangent_pairs(scheme: Any, ids: Sequence[str | None] | None = None) -> np.ndarray:
    """(N, 2) int neighbour indices (a, b) per landmark from a scheme's ``tangents`` metadata; -1 = none.

    ``scheme``: a :class:`face3d.model.registry.Scheme` (its ``raw`` document is read) or the
    scheme document itself.  The optional top-level key ``tangents`` holds
    ``{"neighbours": {point: [a, b], ...}}`` where ``point``, ``a`` and ``b`` are anatomical ids
    (or point names) of the scheme: the image tangent of ``point`` is the direction of the chord
    from ``a`` to ``b``, its two neighbours on the same anatomical curve / outline (``b`` may be
    the point itself for a one-sided chord).  A scheme without the key gives all -1 (every
    tangent unknown: the pre-FU-04 behaviour).

    ``ids`` None: rows follow the scheme's own point order.  Otherwise ``ids`` are the caller's
    landmark ids (anatomical ids or scheme point names; e.g. the pipeline's engine point list)
    and rows / indices refer to positions in ``ids``; an entry whose point or neighbours are not
    in ``ids`` is -1.  Raises ValueError for a malformed entry or an unknown point of the scheme.
    """
    doc = getattr(scheme, "raw", scheme)
    meta = (doc or {}).get("tangents") or {}
    nb = meta.get("neighbours") or {}
    pts = (doc or {}).get("points") or []
    known = set()
    order = []
    for p in pts:
        key = p.get("anatomical_id") or p.get("name")
        order.append(key)
        known.add(p.get("name"))
        if p.get("anatomical_id") is not None:
            known.add(p["anatomical_id"])
    names = list(order if ids is None else ids)
    pos = {k: i for i, k in enumerate(names) if k is not None}
    out = np.full((len(names), 2), -1, dtype=np.int64)
    for point, pair in nb.items():
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError(f"scheme tangents: neighbours of {point!r} must be a pair, got {pair!r}")
        a, b = str(pair[0]), str(pair[1])
        for k in (point, a, b):
            if k not in known:
                raise ValueError(f"scheme tangents: {k!r} is not a point of the scheme")
        if a == b:
            raise ValueError(f"scheme tangents: neighbours of {point!r} are the same point")
        if point in pos and a in pos and b in pos:
            out[pos[point]] = (pos[a], pos[b])
    return out


def image_tangents(uv: Any, pairs: Any, sigma_px: Any = None, min_rho: float | None = None) -> np.ndarray:
    """(N, 3) image tangents (t_x, t_y, rho) of one view from its own detections (DESIGN 4.4 't-hat from neighbouring
    curve points'; WBS FU-04 task 1).  Never uses anything but ``uv``.

    ``uv`` (N, 2) px detections (NaN rows hidden); ``pairs`` (N, 2) int neighbour indices
    (:func:`scheme_tangent_pairs`; a negative entry: no tangent defined); ``sigma_px`` (N,) or
    scalar isotropic-equivalent detection SD of every landmark in px (the declared noise of the
    neighbours; None: the direction is taken as exact).

    Row i is the unit chord direction (uv[b] - uv[a]) / |uv[b] - uv[a]| followed by its direction
    confidence rho_i = exp(-2 sigma_delta^2), with sigma_delta^2 = (sigma_a^2 + sigma_b^2) / |chord|^2 the
    first-order variance of the chord direction (radians^2) under the neighbours' noise: rho is
    the mean resultant length of the axial direction, which :meth:`NoiseModel.view_cov` turns
    into the exact covariance under that direction error (module docstring).  Rows are NaN
    (unknown tangent: the point keeps the FU-01 isotropic rule) when no pair is defined, the
    point or a neighbour is hidden, the chord has zero length, or rho < ``min_rho`` (default
    ``noise.tangent_min_rho``, 0.5: a foreshortened chord, e.g. the lip line in a profile view).
    """
    U = np.asarray(uv, dtype=float)
    if U.ndim != 2 or U.shape[1] != 2:
        raise ValueError(f"uv must have shape (N, 2), got {U.shape}")
    N = len(U)
    P = np.asarray(pairs, dtype=np.int64)
    if P.shape != (N, 2):
        raise ValueError(f"pairs must have shape ({N}, 2), got {P.shape}")
    if np.any(P >= N):
        raise ValueError("pairs index out of range")
    rmin = TANGENT_MIN_RHO if min_rho is None else float(min_rho)
    out = np.full((N, 3), np.nan)
    has = (P >= 0).all(axis=1)
    if not has.any():
        return out
    idx = np.flatnonzero(has)
    a, b = P[idx, 0], P[idx, 1]
    d = U[b] - U[a]
    L = np.linalg.norm(d, axis=1)
    ok = np.isfinite(L) & (L > 1e-9) & np.isfinite(U[idx]).all(axis=1)
    if sigma_px is None:
        var = np.zeros(len(idx))
    else:
        sg = np.broadcast_to(np.asarray(sigma_px, dtype=float), (N,)) if np.ndim(sigma_px) == 0 \
            else np.asarray(sigma_px, dtype=float).reshape(-1)
        if sg.shape != (N,):
            raise ValueError(f"sigma_px must be a scalar or ({N},), got {np.shape(sigma_px)}")
        var = sg[a] ** 2 + sg[b] ** 2
        ok &= np.isfinite(var)
    with np.errstate(invalid="ignore", divide="ignore"):
        rho = np.exp(-2.0 * var / L ** 2)
    ok &= np.isfinite(rho) & (rho >= rmin) & (rho > 0)
    sel = idx[ok]
    out[sel, :2] = d[ok] / L[ok][:, None]
    out[sel, 2] = rho[ok]
    return out


def unknown_tangent_var_mm2(kinds: Sequence[str], sigma_nt_mm: Any) -> np.ndarray:
    """(N,) isotropic variance in mm^2 for landmarks whose image tangent is unknown.

    ``kinds`` (N,) valid kind names; ``sigma_nt_mm`` (N, 2) (sigma_n, sigma_t) in mm.  Kinds in
    :data:`FREE_TANGENT_KINDS` (curve, contour, brow; tangent SD 'free') get the orientation
    average (sigma_n^2 + sigma_t^2) / 2 (WBS WP-07); every other kind gets
    max(sigma_n^2, sigma_t^2), the smallest isotropic variance that dominates the error ellipse
    in every orientation (WBS FU-01; DESIGN 4.4 sigma_t, e.g. 3.0 mm for extremal).
    """
    s = np.asarray(sigma_nt_mm, dtype=float).reshape(-1, 2)
    if len(kinds) != len(s):
        raise ValueError(f"{len(kinds)} kinds for {len(s)} sigma rows")
    free = np.array([k in FREE_TANGENT_KINDS for k in kinds], bool)
    sn2, st2 = s[:, 0] ** 2, s[:, 1] ** 2
    return np.where(free, 0.5 * (sn2 + st2), np.maximum(sn2, st2))


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
        # isotropic SD used when the image tangent is unknown (WBS WP-07 / FU-01)
        self.sigma_iso_mm = np.sqrt(unknown_tangent_var_mm2(self.kinds, s))   # (N,)
        self.floor_k = np.array([tab["floor_k"][FLOOR_CLASS_OF_KIND[k]] for k in self.kinds], float)
        # tangent variance that leaks into the normal under an uncertain direction (FREE_ENCODED_KINDS:
        # the finite slide spread, not the 'free' encoding; WBS FU-04 review)
        leak = float(_cfg_value("free_tangent_leak_mm", cfg))
        self._leak_t2 = np.where([k in FREE_ENCODED_KINDS for k in self.kinds], leak ** 2, s[:, 1] ** 2)
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
        (None: floor_min_px only); ``tangents`` (N, 2) exact image tangents of any length, or (N, 3)
        (t_x, t_y, rho) with the direction confidence rho of a detection-derived tangent
        (module docstring, :func:`image_tangents`), or None (unknown rows: NaN / zero; their
        covariance is isotropic with ``sigma_iso_mm``, see :func:`unknown_tangent_var_mm2`);
        ``multipliers`` (N,) m_iv (default 1); ``tta_px`` (N,)
        test-time augmentation spread in px (default 0).  Rows with non-finite ``px_per_mm``
        are NaN.
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
            tu, rho = _split_tangents(tangents, n)
            known = np.isfinite(rho)
            if known.any():
                t = tu[known]
                nv = np.column_stack([-t[:, 1], t[:, 0]])
                # direction confidence rho: E[sin^2 delta] = (1 - rho) / 2 (WBS FU-04)
                s_dir = 0.5 * (1.0 - rho[known])
                free = np.array([k in FREE_ENCODED_KINDS for k in self.kinds], bool)[known]
                leak = np.maximum(self._leak_t2[known] - sn2[known], 0.0) * s_dir
                # 'free' kinds: the tangent stays free; other kinds: exact second moment (trace kept)
                var_t = np.where(free, st2[known], st2[known] - leak)
                S[known] = ((sn2[known] + leak)[:, None, None] * np.einsum("ni,nj->nij", nv, nv)
                            + var_t[:, None, None] * np.einsum("ni,nj->nij", t, t))
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
