"""Evidence-gated bilateral symmetry: per-pair sigma, plane weights, the symmetry term, S/Asym split, checks.

Implements DESIGN D-15 and section 4.11 (with the plane fit of
:mod:`face3d.geometry.procrustes`) and the detection rule of 4.15 stage A.
The engine **never symmetrises its output** (D-15, H6; anat R5.9): symmetry only
enters as a soft prior term on the landmarks, and :func:`split_symmetric` is an
exact, lossless decomposition ``V = S + Asym`` so that ``Asym`` can be exported
as its own shape key (D-22).

Conventions
-----------
* Millimetres in the head frame (DESIGN 3.1: +x subject's left, +y up, +z out of
  the face).  ``_L`` ids have +x.
* A symmetry plane is ``(n, d)``: ``{x : n . x = d}``, unit ``n``; the reflection
  is ``reflect(x; n, d) = (I - 2 n n^T) x + 2 d n``
  (:func:`face3d.geometry.procrustes.reflect`).  The default plane is the
  head-frame sagittal plane ``n = (1, 0, 0)``, ``d = 0``.
* The pair difference ``d_k = X_l - reflect(X_r)`` equals ``2 A`` for the
  asymmetric part ``A``; sigmas are per axis (x, y, z) on ``d_k`` (anat R4.2).
* Evidence states are those of the claims ledger (DESIGN D-16, 4.12):
  ``'measured'``, ``'constrained'``, ``'prior-driven'``, ``'unobserved'``
  (``'prior_driven'`` is accepted as a spelling of ``'prior-driven'``).

Numeric defaults
----------------
Every number is registered in :mod:`face3d.core.config` under the namespace
``symmetry`` with its badge and source (DESIGN 0: "Every 🧠, ↔️ and 🆕 number ...
ships as a named default").  The per-landmark pair and midline sigmas live in
the landmark registry (:data:`face3d.model.registry.ANATOMICAL`, WP-03, from
DESIGN 4.11 / anat R4.2, all 🧠 provisional); this module adds only the brow
sigma (brows are not among the 44 anatomical landmarks).
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import numpy as np

from ..core.config import Default, register_defaults
from ..geometry.procrustes import fit_symmetry_plane, reflect, reflection_matrix, umeyama_proper_and_reflected
from ..model.registry import ANATOMICAL, Landmark

__all__ = [
    "SYM", "EVIDENCE_STATES", "GATED_STATES", "FULL_SIGMA_STATES", "FACE_REGIONS", "PLANE_GROUPS",
    "pair_sigmas", "midline_sigmas", "gate_symmetry_sigmas", "plane_weights", "plane_group",
    "SymmetryTerm", "split_symmetric", "mirror_rmsd", "face_vertex_mask", "symmetry_checks",
    "detect_mirrored_source", "check_mirror_map",
]

_BRAIN = "\U0001F9E0"   # expert knowledge, provisional
_NEW = "\U0001F195"     # introduced by this design, uncalibrated

SYM = register_defaults("symmetry", {
    # Evidence gating (DESIGN D-15, 4.11): weight x0.25 where the region is measured or
    # constrained, i.e. sigma / sqrt(0.25) = 2 sigma (anat R4.2 'assist' mode x0.25).
    "assist_factor": Default(0.25, _BRAIN, "DESIGN D-15 / 4.11 evidence gating (anat R4.2 assist mode x0.25)",
                             "", (1e-6, 1.0)),
    # Plane-fit weights by region (DESIGN 4.11; anat R3.3; research note facial-asymmetry
    # 'Plane-fit weights').
    "plane_weight_upper": Default(1.0, _BRAIN, "DESIGN 4.11 / anat R3.3: upper face 1.0", "", (0.0, None)),
    "plane_weight_midface": Default(0.5, _BRAIN, "DESIGN 4.11 / anat R3.3: midface 0.5", "", (0.0, None)),
    "plane_weight_lower": Default(0.25, _BRAIN, "DESIGN 4.11 / anat R3.3: lower face 0.25", "", (0.0, None)),
    "plane_weight_ears": Default(0.1, _BRAIN, "DESIGN 4.11 / anat R3.3: ears 0.1", "", (0.0, None)),
    "plane_weight_cranium": Default(0.1, _NEW, "WP-12: cranium (v, op, eu) not in anat R3.3; treated like ears",
                                    "", (0.0, None)),
    # Brow pair sigma (DESIGN 4.11 'brows 1.5 (vertical 2.0)'; anat R4.2).
    "brow_sigma_mm": Default(1.5, _BRAIN, "DESIGN 4.11 / anat R4.2: brows 1.5 mm (x, z)", "mm", (1e-6, None)),
    "brow_sigma_vertical_mm": Default(2.0, _BRAIN, "DESIGN 4.11 / anat R4.2: brows vertical 2.0 mm", "mm",
                                      (1e-6, None)),
    # Output checks (DESIGN 4.11; anat section 6 'Symmetrised or broken fit'; facial-asymmetry 'Report').
    "too_symmetric_rmsd_mm": Default(0.3, _BRAIN, "DESIGN 4.11 / anat section 6: mirror RMSD < 0.3 mm", "mm",
                                     (0.0, None)),
    "too_asymmetric_rmsd_mm": Default(1.5, _BRAIN, "DESIGN 4.11 / anat section 6: mirror RMSD > 1.5 mm", "mm",
                                      (0.0, None)),
    # Pose-asymmetry confound (DESIGN 4.11; anat section 6 'Single-view asymmetry';
    # facial-asymmetry 'Pose-asymmetry confound').
    "min_views_30deg": Default(2, _BRAIN, "DESIGN 4.11: fewer than 2 views >= 30 deg apart", "views", (0, None)),
    "single_view_asym_multiplier": Default(4.0, _BRAIN, "DESIGN 4.11 / anat section 6: asymmetry sigma x4",
                                           "", (1.0, None)),
    # Stage A mirrored-source rule (DESIGN 4.15 stage A).
    "mirrored_source_ratio": Default(0.5, _BRAIN, "DESIGN 4.15 stage A: reflected RMS < 0.5x proper", "",
                                     (0.0, 1.0)),
})

#: Ledger states (DESIGN D-16, 4.12).
EVIDENCE_STATES: tuple[str, ...] = ("measured", "constrained", "prior-driven", "unobserved")
#: States whose symmetry weight is reduced by ``assist_factor`` (DESIGN D-15, 4.11).
GATED_STATES: frozenset[str] = frozenset({"measured", "constrained"})
#: States that keep the full per-pair sigma (DESIGN D-15).
FULL_SIGMA_STATES: frozenset[str] = frozenset({"prior-driven", "unobserved"})

#: Template regions over which the mirror RMSD is evaluated (WP-12 spec: eyes, nose,
#: lips, cheeks, chin, forehead; the face proper, excluding ears, jaw, scalp and neck).
FACE_REGIONS: tuple[str, ...] = ("eyes", "nose", "lips", "cheeks", "chin", "forehead")

#: Plane-fit group of each landmark-registry region (DESIGN 4.11 / anat R3.3 and the
#: WP-12 spec): upper face = eyes, forehead (+ n, g); midface = nose, cheeks
#: (prn, sn, al, ac, or, zy); lower = lips, chin, jaw; ears; cranium (🆕, see SYM).
#: The research note *facial-asymmetry* lists orbitale with the upper face; the WP-12
#: spec places it in the midface (cheeks region) -- provisional either way.
PLANE_GROUPS: dict[str, str] = {
    "eyes": "upper", "forehead": "upper", "brows": "upper",
    "nose": "midface", "cheeks": "midface",
    "lips": "lower", "chin": "lower", "jaw": "lower",
    "ears": "ears", "cranium": "cranium",
}
#: Per-base overrides of the region rule: nasion is in the registry's nose region but
#: belongs to the upper face for the plane fit (WP-12 spec 'upper face (eyes, forehead, n, g)').
_PLANE_GROUP_BASE: dict[str, str] = {"n": "upper", "g": "upper"}


def _cfg_value(key: str, cfg: Mapping[str, Any] | None = None) -> Any:
    """Resolved value of ``symmetry.<key>`` from ``cfg`` (``core.config.resolve`` output) or the default."""
    if cfg:
        v = cfg.get("symmetry." + key)
        if v is not None:
            return v
    return SYM[key].value


# ============================================================================ lookups
def _name_index(registry: Mapping[str, Landmark]) -> dict[str, Landmark]:
    return {lm.name: lm for lm in registry.values()}


def _lookup(lid: str, registry: Mapping[str, Landmark], names: dict[str, Landmark] | None) -> Landmark | None:
    lm = registry.get(lid)
    if lm is None and names is not None:
        lm = names.get(lid)
    return lm


def _is_brow(lid: str) -> bool:
    return "brow" in str(lid).lower()


def _status_key(status: str) -> str:
    s = str(status).strip().lower().replace("_", "-")
    if s not in EVIDENCE_STATES:
        raise ValueError(f"unknown evidence state {status!r}; expected one of {EVIDENCE_STATES}")
    return s


# ============================================================================ sigmas
def pair_sigmas(ids_pairs: Sequence[tuple[str, str]], registry: Mapping[str, Landmark] = ANATOMICAL, *,
                fallback_mm: float | None = None, cfg: Mapping[str, Any] | None = None) -> np.ndarray:
    """Per-pair, per-axis symmetry sigma (mm) on ``d = X_l - reflect(X_r)`` -> (P, 3).

    ``ids_pairs`` is a sequence of ``(left_id, right_id)``; ids are registry ids
    (``'en_L'``) or registry names (``'endocanthion_L'``).  Values come from
    :attr:`Landmark.sym_sigma_mm` (DESIGN 4.11 / anat R4.2 🧠: canthi/lids 0.85,
    alare/orbitale/zygion 1.25, cheilion 1.75, gonion 2.75, ears 3.5 mm).  Brow
    pairs (any id containing ``'brow'``; not anatomical landmarks) get
    ``(1.5, 2.0, 1.5)`` mm (DESIGN 4.11 'brows 1.5 (vertical 2.0)').  Other
    unknown ids raise KeyError unless ``fallback_mm`` is given (the research
    note *facial-asymmetry* calls the legacy uniform 2.0 mm an acceptable
    fallback).  A pair whose two ids are not registry mirrors raises ValueError.
    """
    names = _name_index(registry)
    out = []
    for pair in ids_pairs:
        a, b = pair
        la, lb = _lookup(a, registry, names), _lookup(b, registry, names)
        if la is not None and la.sym_sigma_mm is not None:
            if lb is None or lb.id != la.mirror_id:
                raise ValueError(f"{a!r} and {b!r} are not a registry mirror pair")
            out.append(tuple(float(v) for v in la.sym_sigma_mm))
        elif la is not None or lb is not None:
            raise ValueError(f"({a!r}, {b!r}) is not a registry mirror pair (midline or mixed ids)")
        elif _is_brow(a) and _is_brow(b):
            s = float(_cfg_value("brow_sigma_mm", cfg))
            out.append((s, float(_cfg_value("brow_sigma_vertical_mm", cfg)), s))
        elif fallback_mm is not None:
            out.append((float(fallback_mm),) * 3)
        else:
            raise KeyError(f"no symmetry sigma for pair ({a!r}, {b!r}); pass fallback_mm")
    return np.asarray(out, dtype=float).reshape(-1, 3)


def midline_sigmas(ids: Sequence[str], registry: Mapping[str, Landmark] = ANATOMICAL, *,
                   fallback_mm: float | None = None) -> np.ndarray:
    """Midline sigma (mm) on the signed plane distance ``n . X - d`` -> (M,).

    From :attr:`Landmark.midline_sigma_mm` (DESIGN 4.11 / anat R4.2 🧠: n, g 0.9;
    prn, sn 1.75; pg, me, gn 2.5; other midline ids 2.0 mm).  A bilateral id
    raises ValueError; an unknown id raises KeyError unless ``fallback_mm`` is
    given (*facial-asymmetry*: legacy ``sigma_mid = 1.5`` is an acceptable fallback).
    """
    names = _name_index(registry)
    out = []
    for lid in ids:
        lm = _lookup(lid, registry, names)
        if lm is None:
            if fallback_mm is None:
                raise KeyError(f"no midline sigma for {lid!r}; pass fallback_mm")
            out.append(float(fallback_mm))
        elif lm.midline_sigma_mm is None:
            raise ValueError(f"{lid!r} is bilateral, not a midline landmark")
        else:
            out.append(float(lm.midline_sigma_mm))
    return np.asarray(out, dtype=float)


def gate_symmetry_sigmas(pair_sigma: np.ndarray, pair_status: Sequence[str],
                         assist_factor: float = float(SYM.assist_factor.value)) -> np.ndarray:
    """Evidence gating of symmetry sigmas (DESIGN D-15, 4.11; anat R4.2 assist mode).

    ``pair_sigma`` is (P, 3) (or any (P, ...) array, e.g. (M,) midline sigmas) and
    ``pair_status`` the ledger state of each pair's region.  States
    ``'measured'`` / ``'constrained'`` get ``sigma / sqrt(assist_factor)`` (weight
    x ``assist_factor``; 2 sigma at the default 0.25); ``'prior-driven'`` /
    ``'unobserved'`` keep the full-strength sigma.  Returns a new array.
    """
    s = np.asarray(pair_sigma, dtype=float)
    if s.ndim == 0:
        raise ValueError("pair_sigma must be at least 1-D")
    status = list(pair_status)
    if len(status) != s.shape[0]:
        raise ValueError(f"pair_status has {len(status)} entries for {s.shape[0]} pairs")
    a = float(assist_factor)
    if not (0.0 < a <= 1.0) or not math.isfinite(a):
        raise ValueError(f"assist_factor must be in (0, 1], got {assist_factor!r}")
    gated = 1.0 / math.sqrt(a)
    f = np.array([gated if _status_key(st) in GATED_STATES else 1.0 for st in status], dtype=float)
    return s * f.reshape((-1,) + (1,) * (s.ndim - 1))


# ============================================================================ plane weights
def _group(lid: str, registry: Mapping[str, Landmark], names: dict[str, Landmark]) -> str | None:
    lm = _lookup(lid, registry, names)
    if lm is not None:
        return _PLANE_GROUP_BASE.get(lm.base, PLANE_GROUPS.get(lm.region))
    return "upper" if _is_brow(lid) else None


def plane_group(lid: str, registry: Mapping[str, Landmark] = ANATOMICAL) -> str | None:
    """Plane-fit group of a landmark id or name: 'upper', 'midface', 'lower', 'ears', 'cranium' or None."""
    return _group(lid, registry, _name_index(registry))


def plane_weights(ids: Sequence[str], registry: Mapping[str, Landmark] = ANATOMICAL, *,
                  default: float | None = None, cfg: Mapping[str, Any] | None = None) -> np.ndarray:
    """Per-landmark weights for the symmetry-plane fit (DESIGN 4.11; anat R3.3 🧠) -> (N,).

    Upper face (eyes, forehead, n, g; brows) 1.0; midface (nose, cheeks: prn, sn,
    al, ac, or, zy) 0.5; lower face (lips, chin, jaw) 0.25; ears 0.1; cranium
    (v, op, eu) 0.1 (🆕, WP-12).  Unknown ids raise KeyError unless ``default``
    is given.
    """
    names = _name_index(registry)
    out = []
    for lid in ids:
        group = _group(lid, registry, names)
        if group is None:
            if default is None:
                raise KeyError(f"no plane-fit weight for {lid!r}; pass default")
            out.append(float(default))
        else:
            out.append(float(_cfg_value(f"plane_weight_{group}", cfg)))
    return np.asarray(out, dtype=float)


# ============================================================================ the term
def _points(state: Any) -> np.ndarray:
    X = state.X if hasattr(state, "X") else state
    X = np.asarray(X, dtype=float)
    if X.ndim != 2 or X.shape[1] != 3:
        raise ValueError(f"symmetry term needs points (N, 3), got {X.shape}")
    return X


def _zeta(state: Any) -> float | None:
    """The global log-scale of a solver state / bundle result, or None (disabled, or a bare array)."""
    z = getattr(state, "zeta", None)
    if z is None:
        return None
    z = float(z)
    if not math.isfinite(z):
        raise ValueError("state.zeta must be finite")
    return z


def _scale_free(state: Any) -> tuple[np.ndarray, float | None, float]:
    """``(X~, zeta, s)``: the points the term acts on, with ``s = d X~ / d X``.

    zeta disabled (``state.zeta`` is None or absent, or ``state`` is an array): ``X~`` is
    ``state.X`` itself in mm and ``s = 1`` (legacy path, no arithmetic on X).  zeta enabled:
    ``X~ = exp(-zeta) X`` (DESIGN D-03: "zeta carries size"), ``s = exp(-zeta)``.
    """
    X = _points(state)
    z = _zeta(state)
    if z is None:
        return X, None, 1.0
    s = math.exp(-z)
    return s * X, z, s


class SymmetryTerm:
    """Bilateral symmetry and midline prior on the landmark points (DESIGN 4.8 Term protocol, 4.11).

    Duck-typed to the solver's Term protocol (``face3d.solve.terms``, WP-10; not
    imported here): ``name``, ``is_prior = True``, ``n_params() = 0``,
    ``init_params(state)``, ``residuals(state, p)`` and ``jacobian(state, p) ->
    {'X': (m, 3N)}`` (plus ``'zeta': (m,)`` when the state's zeta is enabled).  ``state``
    is any object with an ``X`` (N, 3) attribute (a solver state, a bundle result) or the
    (N, 3) array itself; ``p`` is ignored (no own parameters).

    Residuals (dimensionless, whitened), in this order, on the points ``Y``:

    * pairs, row ``3k + c``: ``(Y_l - reflect(Y_r; n, d))_c / sigma_pair[k, c]``;
    * midline, row ``3P + j``: ``(n . Y_m - d) / sigma_mid[j]``.

    Which points (WBS FU-02; DESIGN D-03 "zeta carries size", 4.7):

    * zeta disabled (``state.zeta`` is None or absent, or ``state`` is a bare array):
      ``Y = X`` in mm, the plane offset ``d`` in mm.  This is the legacy WP-12 behaviour,
      unchanged.
    * zeta enabled (``state.zeta`` is a float, as in ``SolverState`` / ``BundleResult``
      when the bundle's explicit log-scale is on): ``Y = X~ = exp(-zeta) X``, the
      scale-free points the shape prior also acts on, and ``d`` is an offset in that
      scale-free frame (mm of the prior-size head).  The term then constrains shape and
      not size: on X in mm its energy would scale as ``e^(2 zeta)`` at fixed shape and
      pull a weakly determined scale toward smaller heads (the defect WBS FU-01 fixed
      for the bundle's built-in ``Priors.pairs`` / ``Priors.midline`` rows).  The
      Jacobian is exact: ``d r / d X = exp(-zeta) J0`` with ``J0`` the constant legacy
      block, and ``d r / d zeta = -J0 vec(X~)`` (since ``d X~ / d zeta = -X~``; this is
      ``-(r - r(0))``, not ``-r``, because the offset ``d`` does not scale).
      :meth:`update_plane`, :meth:`pair_differences` and :meth:`cost` follow the same
      rule, so the plane refitted from a state is the plane the residuals use.

    The plane ``(n, d)`` is held fixed within a solve (the residuals are then
    linear in X and the Jacobian is constant) and refitted between outer
    iterations with :meth:`update_plane` (weighted reflection Procrustes; anat
    R3.3: "a 2 deg frame error reads as ~3 mm asymmetry").

    Parameters
    ----------
    pairs : (P, 2) point indices ``(l, r)``.
    midline : (M,) point indices.
    pair_sigma : (P, 3) mm (already evidence-gated, see :func:`gate_symmetry_sigmas`).
    midline_sigma : (M,) mm.
    plane_weights : (N,) weights for :meth:`update_plane` (None = all 1).
    n, d : initial plane (default: head-frame sagittal plane).
    """

    is_prior: bool = True

    def __init__(self, pairs: np.ndarray, midline: np.ndarray, pair_sigma: np.ndarray,
                 midline_sigma: np.ndarray, *, plane_weights: np.ndarray | None = None,
                 n: Sequence[float] = (1.0, 0.0, 0.0), d: float = 0.0, name: str = "symmetry"):
        self.name = str(name)
        self.pairs = np.asarray(pairs, dtype=np.int64).reshape(-1, 2)
        self.midline = np.asarray(midline, dtype=np.int64).reshape(-1)
        self.pair_sigma = np.asarray(pair_sigma, dtype=float).reshape(-1, 3)
        self.midline_sigma = np.asarray(midline_sigma, dtype=float).reshape(-1)
        if len(self.pair_sigma) != len(self.pairs):
            raise ValueError(f"pair_sigma has {len(self.pair_sigma)} rows for {len(self.pairs)} pairs")
        if len(self.midline_sigma) != len(self.midline):
            raise ValueError(f"midline_sigma has {len(self.midline_sigma)} entries for {len(self.midline)} points")
        for arr, what in ((self.pair_sigma, "pair_sigma"), (self.midline_sigma, "midline_sigma")):
            if arr.size and (not np.all(np.isfinite(arr)) or np.any(arr <= 0)):
                raise ValueError(f"{what} must be finite and positive")
        flat = np.concatenate([self.pairs.ravel(), self.midline])
        if flat.size and flat.min() < 0:
            raise ValueError("point indices must be non-negative")
        if len(np.unique(flat)) != len(flat):
            raise ValueError("each point may appear once among the pairs and the midline")
        self.plane_weights = None if plane_weights is None else np.asarray(plane_weights, dtype=float).reshape(-1)
        self.n = np.zeros(3)
        self.d = 0.0
        self.set_plane(n, d)
        self.plane_rmse_mm: float | None = None
        #: Optional labels (set by :meth:`from_ids`): ``(left_id, right_id)`` per pair, midline ids.
        self.pair_ids: list[tuple[str, str]] | None = None
        self.midline_ids: list[str] | None = None

    # -------------------------------------------------------------- construction
    @classmethod
    def from_ids(cls, ids: Sequence[str], *, region_status: Mapping[str, str] | None = None,
                 pair_status: Sequence[str] | None = None, assist_factor: float | None = None,
                 registry: Mapping[str, Landmark] = ANATOMICAL, n: Sequence[float] = (1.0, 0.0, 0.0),
                 d: float = 0.0, name: str = "symmetry", cfg: Mapping[str, Any] | None = None) -> "SymmetryTerm":
        """Build the term for points labelled ``ids`` (the order of the solver's X).

        Pairs are the ``_L`` ids whose ``_R`` mirror is present (registry ids, or
        any ``*_L`` / ``*_R`` brow names), midline points are registry midline ids;
        other ids are not constrained.  Evidence gating (DESIGN D-15) uses
        ``pair_status`` (one state per pair, in the order of :attr:`pair_ids`) or
        else ``region_status`` (ledger region -> state; a pair takes the state of
        its registry region, brows the 'brows' region; missing regions count as
        'prior-driven', i.e. full sigma).  Midline sigmas are not gated (DESIGN
        4.11 gates the pairs).  Plane weights from :func:`plane_weights`
        (unconstrained points get 0).
        """
        ids = [str(i) for i in ids]
        index = {lid: k for k, lid in enumerate(ids)}
        if len(index) != len(ids):
            raise ValueError("ids must be unique")
        names = _name_index(registry)
        pairs, pair_ids, mids, mid_ids, regions = [], [], [], [], []
        for k, lid in enumerate(ids):
            lm = _lookup(lid, registry, names)
            if lm is not None:
                if lm.side == "mid":
                    mids.append(k)
                    mid_ids.append(lid)
                elif lm.side == "L":
                    partner = lm.mirror_id if lm.mirror_id in index else registry[lm.mirror_id].name
                    if partner in index:
                        pairs.append((k, index[partner]))
                        pair_ids.append((lid, partner))
                        regions.append(lm.region)
            elif _is_brow(lid) and lid.endswith("_L") and (lid[:-2] + "_R") in index:
                pairs.append((k, index[lid[:-2] + "_R"]))
                pair_ids.append((lid, lid[:-2] + "_R"))
                regions.append("brows")
        sig = pair_sigmas(pair_ids, registry, cfg=cfg)
        if pair_status is None:
            rs = dict(region_status or {})
            pair_status = [rs.get(r, "prior-driven") for r in regions]
        a = float(_cfg_value("assist_factor", cfg) if assist_factor is None else assist_factor)
        sig = gate_symmetry_sigmas(sig, list(pair_status), a)
        msig = midline_sigmas(mid_ids, registry)
        w = np.zeros(len(ids))
        used = [k for pr in pairs for k in pr] + mids
        if used:
            w[used] = plane_weights([ids[k] for k in used], registry, cfg=cfg)
        term = cls(np.asarray(pairs, dtype=np.int64).reshape(-1, 2), np.asarray(mids, dtype=np.int64),
                   sig, msig, plane_weights=w, n=n, d=d, name=name)
        term.pair_ids = pair_ids
        term.midline_ids = mid_ids
        return term

    # -------------------------------------------------------------- plane
    def set_plane(self, n: Sequence[float], d: float) -> None:
        """Hold the plane ``{x : n . x = d}`` fixed (``n`` is normalised together with ``d``)."""
        n = np.asarray(n, dtype=float).reshape(3)
        norm = float(np.linalg.norm(n))
        if not np.isfinite(norm) or norm == 0.0:
            raise ValueError("plane normal must be finite and non-zero")
        self.n = n / norm
        self.d = float(d) / norm

    def update_plane(self, X: Any, *, huber_mm: float | None = None) -> tuple[np.ndarray, float, float]:
        """Refit the plane to ``X`` (between outer iterations; DESIGN 4.11, anat R3.3).

        Weighted reflection Procrustes (:func:`face3d.geometry.procrustes.fit_symmetry_plane`)
        over this term's pairs and midline with :attr:`plane_weights`.  Stores and
        returns ``(n, d, rmse_mm)``.  ``X`` is an (N, 3) array or a state / bundle result;
        with zeta enabled on it the plane is fitted to ``exp(-zeta) X``, the points the
        residuals act on (class docstring), so ``d`` and the rmse are in that scale-free
        frame.  ``huber_mm`` is applied in the same frame.
        """
        X, _, _ = _scale_free(X)
        n, d, rmse = fit_symmetry_plane(X, self.pairs, self.midline, self._weights(len(X)), huber_mm=huber_mm)
        self.set_plane(n, d)
        self.plane_rmse_mm = rmse
        return self.n.copy(), self.d, rmse

    def _weights(self, N: int) -> np.ndarray | None:
        if self.plane_weights is None:
            return None
        if len(self.plane_weights) != N:
            raise ValueError(f"plane_weights has {len(self.plane_weights)} entries for {N} points")
        return self.plane_weights

    # -------------------------------------------------------------- Term protocol
    def n_params(self) -> int:
        """No own parameters (the plane is held fixed within a solve)."""
        return 0

    def init_params(self, state: Any = None) -> np.ndarray:
        return np.zeros(0)

    def n_residuals(self) -> int:
        return 3 * len(self.pairs) + len(self.midline)

    def _check_indices(self, N: int) -> None:
        flat = np.concatenate([self.pairs.ravel(), self.midline])
        if flat.size and flat.max() >= N:
            raise ValueError(f"symmetry term indexes point {int(flat.max())} but X has {N} points")

    def pair_differences(self, X: Any) -> np.ndarray:
        """``Y_l - reflect(Y_r; n, d)`` per pair, (P, 3) mm (= 2x the asymmetric part).

        ``Y`` is ``X`` in mm, or ``exp(-zeta) X`` when ``X`` is a state with zeta enabled
        (class docstring)."""
        X, _, _ = _scale_free(X)
        self._check_indices(len(X))
        return X[self.pairs[:, 0]] - reflect(X[self.pairs[:, 1]], self.n, self.d)

    def residuals(self, state: Any, p: Any = None) -> np.ndarray:
        """Whitened residuals (m,), m = 3P + M (see the class docstring for the order)."""
        X, _, _ = _scale_free(state)
        self._check_indices(len(X))
        r_pair = (self.pair_differences(X) / self.pair_sigma).ravel()
        r_mid = (X[self.midline] @ self.n - self.d) / self.midline_sigma
        return np.concatenate([r_pair, r_mid])

    def jacobian(self, state: Any, p: Any = None) -> dict[str, np.ndarray]:
        """``{'X': (m, 3N)}``: d residuals / d vec(X) (column ``3i + c``); constant for a fixed plane.

        With zeta enabled on ``state`` (class docstring) the ``'X'`` block is
        ``exp(-zeta)`` times that constant block and a ``'zeta'`` block (m,) is added:
        ``d r / d zeta = -J0 vec(exp(-zeta) X)``.  Without zeta the dict has the ``'X'``
        block only (the bundle rejects a ``'zeta'`` block when zeta is disabled).
        """
        X, zeta, s = _scale_free(state)
        N = len(X)
        self._check_indices(N)
        P, M = len(self.pairs), len(self.midline)
        J = np.zeros((3 * P + M, 3 * N))
        if P:
            H = reflection_matrix(self.n)
            k = np.arange(P)
            inv = 1.0 / self.pair_sigma                                   # (P, 3)
            for c in range(3):
                rows = 3 * k + c
                np.add.at(J, (rows, 3 * self.pairs[:, 0] + c), inv[:, c])
                for c2 in range(3):
                    np.add.at(J, (rows, 3 * self.pairs[:, 1] + c2), -H[c, c2] * inv[:, c])
        if M:
            rows = 3 * P + np.arange(M)
            for c in range(3):
                np.add.at(J, (rows, 3 * self.midline + c), self.n[c] / self.midline_sigma)
        if zeta is None:
            return {"X": J}
        return {"X": J * s, "zeta": -(J @ X.ravel())}

    def cost(self, state: Any) -> float:
        """``0.5 |r|^2`` (the term's energy E_sym, DESIGN 4.8)."""
        r = self.residuals(state)
        return 0.5 * float(r @ r)


# ============================================================================ S / Asym
def check_mirror_map(mirror_map: Any, n_verts: int) -> np.ndarray:
    """Validate a vertex mirror map: (n,) int, in range, an involution (``m[m] == id``)."""
    m = np.asarray(mirror_map)
    if m.shape != (n_verts,):
        raise ValueError(f"mirror_map must have shape ({n_verts},), got {m.shape}")
    if not np.issubdtype(m.dtype, np.integer):
        raise ValueError("mirror_map must be an integer array")
    m = m.astype(np.int64)
    if n_verts and (m.min() < 0 or m.max() >= n_verts):
        raise ValueError("mirror_map indices out of range")
    if not np.array_equal(m[m], np.arange(n_verts)):
        raise ValueError("mirror_map must be an involution (m[m] == identity)")
    return m


def split_symmetric(V: np.ndarray, mirror_map: np.ndarray, n_plane: Sequence[float] = (1.0, 0.0, 0.0),
                    d: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """Exact symmetric / asymmetric split (DESIGN 4.11, D-15, D-22): ``(S, Asym)``.

    ``S = (V + reflect(V[mirror_map]; n_plane, d)) / 2`` and ``Asym = V - S``, both
    (n, 3) mm.  ``S`` is exactly mirror-symmetric (``reflect(S[m]) == S``; bit-exact
    for the default sagittal plane, to rounding for a general plane) and
    ``S + Asym == V`` to rounding.  ``V`` itself is never modified: the engine
    does not symmetrise its output; ``Asym`` is exported as its own key.
    """
    V = np.asarray(V, dtype=float)
    if V.ndim != 2 or V.shape[1] != 3:
        raise ValueError(f"V must be (n, 3), got {V.shape}")
    m = check_mirror_map(mirror_map, len(V))
    S = 0.5 * (V + reflect(V[m], n_plane, d))
    return S, V - S


def face_vertex_mask(regions: Mapping[str, Any], n_verts: int,
                     names: Sequence[str] = FACE_REGIONS) -> np.ndarray:
    """Boolean (n,) mask of the vertices in the named template regions (default :data:`FACE_REGIONS`)."""
    mask = np.zeros(n_verts, dtype=bool)
    for name in names:
        idx = regions.get(name)
        if idx is not None:
            mask[np.asarray(idx, dtype=np.int64)] = True
    return mask


def mirror_rmsd(V: np.ndarray, mirror_map: np.ndarray, vertex_mask: Any = None,
                n_plane: Sequence[float] = (1.0, 0.0, 0.0), d: float = 0.0) -> float:
    """Whole-face mirror RMSD (mm): ``sqrt(mean_i |V_i - reflect(V[m_i])|^2)`` over masked vertices.

    ``vertex_mask`` is a boolean (n,) mask or an index array (None = all
    vertices).  Correspondence-based (via the template's mirror map), so it
    equals 2x the RMS of the asymmetric part ``Asym`` over the mask.  Thresholds
    are in :func:`symmetry_checks` (DESIGN 4.11).
    """
    V = np.asarray(V, dtype=float)
    m = check_mirror_map(mirror_map, len(V))
    if vertex_mask is None:
        sel = np.arange(len(V))
    else:
        vm = np.asarray(vertex_mask)
        sel = np.flatnonzero(vm) if vm.dtype == bool else vm.astype(np.int64).reshape(-1)
        if vm.dtype == bool and vm.shape != (len(V),):
            raise ValueError(f"vertex_mask must have shape ({len(V)},)")
    if len(sel) == 0:
        raise ValueError("vertex_mask selects no vertices")
    diff = V[sel] - reflect(V[m[sel]], n_plane, d)
    return float(np.sqrt(np.mean(np.sum(diff * diff, axis=1))))


def registered_plane(V: np.ndarray, mirror_map: np.ndarray, vertex_mask: Any = None) -> tuple[np.ndarray, float]:
    """Best symmetry plane ``(n, d)`` of ``V`` from its own vertex mirror map.

    Pairs are ``(i, m[i])`` with ``m[i] > i`` and midline vertices are ``m[i] == i``,
    both restricted to ``vertex_mask`` (None = all); unweighted reflection Procrustes
    (:func:`face3d.geometry.procrustes.fit_symmetry_plane`).  Falls back to the
    head-frame plane when there are too few pairs.
    """
    V = np.asarray(V, dtype=float)
    m = check_mirror_map(mirror_map, len(V))
    if vertex_mask is None:
        sel = np.arange(len(V))
    else:
        vm = np.asarray(vertex_mask)
        sel = np.flatnonzero(vm) if vm.dtype == bool else vm.astype(np.int64).reshape(-1)
    pairs = np.array([(i, int(m[i])) for i in sel if m[i] > i], dtype=np.int64).reshape(-1, 2)
    midline = np.array([i for i in sel if m[i] == i], dtype=np.int64)
    n, d, _ = fit_symmetry_plane(V, pairs, midline)
    return np.asarray(n, float), float(d)


def symmetry_checks(V: np.ndarray, mirror_map: np.ndarray, regions: Mapping[str, Any] | None,
                    photos_show_asymmetry: bool, n_view_pairs_30deg: int, *,
                    n_plane: Sequence[float] | None = None, d: float = 0.0,
                    cfg: Mapping[str, Any] | None = None) -> tuple[list[dict[str, Any]], float]:
    """Output symmetry checks (DESIGN 4.11; anat section 6; *facial-asymmetry* 'Report').

    Computes :func:`mirror_rmsd` over the face regions (:data:`FACE_REGIONS` of
    ``regions``; all vertices when ``regions`` is None) and returns
    ``(findings, asym_sigma_multiplier)``:

    * ``findings``: list of dicts ``{code, value, threshold, msg_key, action, source}``
      (``value`` = RMSD in mm, ``action`` always ``'ask'``: flags ask the user and
      never auto-correct, H6):

      - ``'S-TOO-SYMMETRIC'`` if RMSD < 0.3 mm and ``photos_show_asymmetry``
        (the fit has symmetrised away asymmetry the photos show);
      - ``'S-TOO-ASYMMETRIC'`` if RMSD > 1.5 mm ("unusually asymmetric - check pose").

    * ``asym_sigma_multiplier``: 4.0 when ``n_view_pairs_30deg < 2`` else 1.0;
      the reported asymmetry sigma is multiplied by it (DESIGN 4.11 "with fewer
      than 2 views >= 30 deg apart ... multiplied by 4"; anat section 6).
      ``n_view_pairs_30deg`` is read as the number of views that have a partner
      view at least 30 deg away in yaw (0 when no such pair exists, otherwise >= 2).

    Plane: the RMSD must be measured about the head's own symmetry plane, not the
    template's head frame -- a perfectly symmetric head 1 deg off the frame reads as
    ~2.7 mm "asymmetry" (WP-12 review; anat R3.3 "a 2 deg frame error reads as ~3 mm").
    With ``n_plane=None`` (default) the plane is therefore fitted to ``V`` from the
    vertex mirror map over the evaluated vertices (:func:`registered_plane`); pass an
    explicit ``n_plane, d`` (e.g. the current plane P of the solve) to override.
    """
    V = np.asarray(V, dtype=float)
    if regions is None:
        mask = None
    else:
        mask = face_vertex_mask(regions, len(V))
        if not mask.any():
            raise ValueError(f"no vertices in the face regions {FACE_REGIONS}")
    if n_plane is None:
        n_plane, d = registered_plane(V, mirror_map, mask)
    rmsd = mirror_rmsd(V, mirror_map, mask, n_plane, d)
    lo = float(_cfg_value("too_symmetric_rmsd_mm", cfg))
    hi = float(_cfg_value("too_asymmetric_rmsd_mm", cfg))
    findings: list[dict[str, Any]] = []
    if rmsd < lo and bool(photos_show_asymmetry):
        findings.append({"code": "S-TOO-SYMMETRIC", "value": rmsd, "threshold": lo,
                         "msg_key": "symmetry.S-TOO-SYMMETRIC", "action": "ask",
                         "source": SYM.too_symmetric_rmsd_mm.source})
    if rmsd > hi:
        findings.append({"code": "S-TOO-ASYMMETRIC", "value": rmsd, "threshold": hi,
                         "msg_key": "symmetry.S-TOO-ASYMMETRIC", "action": "ask",
                         "source": SYM.too_asymmetric_rmsd_mm.source})
    min_views = int(_cfg_value("min_views_30deg", cfg))
    mult = float(_cfg_value("single_view_asym_multiplier", cfg)) if int(n_view_pairs_30deg) < min_views else 1.0
    return findings, mult


# ============================================================================ stage A
def detect_mirrored_source(src: np.ndarray, dst: np.ndarray, weights: np.ndarray | None = None, *,
                           with_scale: bool = True, ratio: float | None = None,
                           cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """DESIGN 4.15 stage A: is ``src`` (e.g. template landmarks) a mirror image of ``dst``?

    Fits the best proper and the best reflected similarity
    (:func:`face3d.geometry.procrustes.umeyama_proper_and_reflected`) and reports
    ``{'mirrored': reflected_rmse < ratio * proper_rmse, 'proper_rmse',
    'reflected_rmse', 'ratio', 'threshold', 'fits'}`` (rmse in the units of
    ``dst``; ``ratio`` default 0.5, DESIGN 4.15).  Detection only: the engine
    never flips anything automatically (DESIGN D-10, H6).
    """
    thr = float(_cfg_value("mirrored_source_ratio", cfg) if ratio is None else ratio)
    fits = umeyama_proper_and_reflected(src, dst, weights=weights, with_scale=with_scale)
    rp, rr = fits["proper"][3], fits["reflected"][3]
    r = rr / rp if rp > 0 else (0.0 if rr == 0 else math.inf)
    return {"mirrored": bool(rr < thr * rp), "proper_rmse": rp, "reflected_rmse": rr,
            "ratio": float(r), "threshold": thr, "fits": fits}

