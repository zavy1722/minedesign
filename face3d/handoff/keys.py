"""Shape-key stack maths for the Blender hand-off (DESIGN D-22, 4.17; bl K2, K3, W5).

The engine mirrors Blender's *relative* shape keys so that the add-on bridge
only has to copy arrays (``foreach_set``) and never re-derives a mix.

Conventions
-----------
* Units: float64 **millimetres** in the engine frame (DESIGN 2.1 invariant 2).
  The bpy bridge converts to float32 metres; nothing here touches ``bpy``.
* Every key stores **absolute** vertex positions ``data`` of shape ``(n, 3)``,
  exactly like a Blender ``ShapeKey`` (research/blender/shapekeys-blendshapes.md,
  research/blender/bpy-mesh-api.md: "Keys store absolute positions, not deltas").
* Relative evaluation (Blender semantics, shapekeys-blendshapes.md):

      X = Basis + sum_{k not muted} value_k * (data_k - data_of(relative_to_k))

  where ``data_of('Basis')`` is the basis and ``data_of(name)`` is the referenced
  key's **stored data**, not its evaluated mix.  Chained keys therefore add
  their own delta only; the chain is never accumulated.
* Key stack layout (DESIGN 4.17, D-22; bl K2): ``Basis`` = template;
  ``ID_fit`` relative to Basis (slider max 1.5, above 1 is a caricature
  preview); ``Asym`` and ``artist`` relative to ``ID_fit``; muted ``stage_*``
  diagnostics relative to Basis.
* **Exact rebase** (DESIGN 4.17, bl K2/K3): a refit replaces ``ID_fit`` and
  every key that depends on it keeps its own delta, so
  ``artist' - ID' == artist - ID`` (to float64 round-off, ~1e-14 mm).
* **Basis writes propagate** (bl K3): a Python write to Basis does not
  propagate in Blender (shapekeys-blendshapes.md: "The engine must add Delta to
  dependents itself"), so :meth:`KeyStack.write_basis` adds Delta to every key.
* Masks (bl W5): Blender's ``.sculpt_mask`` is a per-vertex float in [0, 1]
  (1 = fully masked).  :func:`protect_mask` and :func:`mask_to_data_weights`
  implement the DESIGN 4.17 conversions literally; see their docstrings.

Numeric defaults are registered under the ``handoff`` namespace of
:mod:`face3d.core.config` with badge and source.
"""
from __future__ import annotations

import copy as _copy
from dataclasses import dataclass, field

import numpy as np

from ..core.config import Default, register_defaults
from ..model.template_kit import TopologyMismatch

__all__ = [
    "BASIS", "ID", "ASYM", "ARTIST", "STAGE_PREFIX", "Key", "KeyStack", "protect_mask",
    "mask_to_data_weights", "topology_guard", "TopologyMismatch", "HANDOFF_DEFAULTS",
]

_BRAIN = "\U0001F9E0"   # expert knowledge, provisional
_NEW = "\U0001F195"     # introduced by this design, uncalibrated

#: Blender key names (DESIGN 4.17 / D-22; bl K2).
BASIS = "Basis"
ID = "ID_fit"
ASYM = "Asym"
ARTIST = "artist"
STAGE_PREFIX = "stage_"

HANDOFF_DEFAULTS = register_defaults("handoff", {
    # DESIGN 4.17 "ID_fit (slider max 1.5; above 1 is a caricature preview)";
    # research/blender/shapekeys-blendshapes.md Recipe step 1 (1.1-1.3 exaggerates the
    # deviation from the mean; valid only if Basis is a mean face).
    "id_fit_slider_max": Default(1.5, _BRAIN, "DESIGN 4.17 / D-22; shapekeys-blendshapes.md recipe 1 "
                                 "(caricature preview above 1)", "", (1.0, 10.0)),
    # DESIGN 4.17 "a pin at sigma 0.2 mm (bl W5)"; proposal-accuracy gives 0.1-0.3 mm.
    "mask_pin_sigma_mm": Default(0.2, _BRAIN, "DESIGN 4.17 painted-mask pin sigma (bl W5; "
                                 "proposal-accuracy 0.1-0.3 mm)", "mm", (1e-6, None)),
    # WP-13 spec: a vertex is pinned where the painted mask m > 0.5.
    "mask_pin_threshold": Default(0.5, _NEW, "WP-13 spec (pin where painted mask m > 0.5; uncalibrated)",
                                  "", (0.0, 1.0)),
})


def _positions(a, name: str, n: int | None = None) -> np.ndarray:
    """Copy ``a`` to a C-contiguous float64 ``(n, 3)`` array, checking shape and finiteness."""
    arr = np.array(a, dtype=np.float64, copy=True)
    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError(f"{name} must be (n, 3) positions, got shape {arr.shape}")
    if n is not None and arr.shape[0] != n:
        raise ValueError(f"{name} has {arr.shape[0]} vertices, expected {n}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains non-finite values")
    return np.ascontiguousarray(arr)


@dataclass(eq=False)
class Key:
    """One Blender-style relative shape key.

    ``data``        (n, 3) float64 **absolute** positions, mm (copied on construction).
    ``relative_to`` name of the reference key (``'Basis'`` or another key of the stack).
    ``value``       mix factor (Blender ``ShapeKey.value``); not clamped here, the
                    bridge clamps to Blender's ``[slider_min, slider_max]``.
    ``slider_max``  Blender ``ShapeKey.slider_max`` (UI range only).
    ``mute``        muted keys contribute nothing to :meth:`KeyStack.evaluate`.

    Equality is identity (the dataclass holds an array).
    """

    data: np.ndarray
    relative_to: str
    value: float = 0.0
    slider_max: float = 1.0
    mute: bool = False

    def __post_init__(self) -> None:
        self.data = _positions(self.data, "Key.data")
        self.relative_to = str(self.relative_to)
        self.value = float(self.value)
        self.slider_max = float(self.slider_max)
        self.mute = bool(self.mute)
        if not (np.isfinite(self.value) and np.isfinite(self.slider_max)):
            raise ValueError("Key.value and Key.slider_max must be finite")


@dataclass(eq=False)
class KeyStack:
    """Basis plus an ordered ``{name: Key}`` dict (Blender ``key_blocks`` order after Basis).

    Invariants (checked by :meth:`validate`, called on construction and at the
    start of :meth:`evaluate`, :meth:`rebase` and :meth:`write_basis`, since
    ``keys`` is a plain mutable dict): every key has the basis shape; no key is
    named ``'Basis'``; every ``relative_to`` names Basis or an existing key;
    relative chains are acyclic and end at Basis ("all keys ultimately relative
    to Basis").  Equality is identity (the dataclass holds arrays).
    """

    basis: np.ndarray
    keys: dict[str, Key] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.basis = _positions(self.basis, "basis")
        self.keys = dict(self.keys)
        self.validate()

    # ------------------------------------------------------------------ structure
    @property
    def n_verts(self) -> int:
        return int(self.basis.shape[0])

    def validate(self) -> None:
        """Raise ``ValueError`` when the stack breaks an invariant (see class doc)."""
        n = self.n_verts
        for name, key in self.keys.items():
            if not isinstance(key, Key):
                raise TypeError(f"key {name!r} must be a Key, got {type(key).__name__}")
            if name == BASIS:
                raise ValueError("the reference key 'Basis' is KeyStack.basis, not an entry of keys")
            if key.data.shape != (n, 3):
                raise ValueError(f"key {name!r} has shape {key.data.shape}, basis is {(n, 3)}")
            if key.relative_to != BASIS and key.relative_to not in self.keys:
                raise ValueError(f"key {name!r} is relative to unknown key {key.relative_to!r}")
            if not np.all(np.isfinite(key.data)) or not np.isfinite(key.value):
                raise ValueError(f"key {name!r} holds non-finite data or value")
        if not np.all(np.isfinite(self.basis)):
            raise ValueError("basis holds non-finite coordinates")
        for name in self.keys:
            self.relative_chain(name)

    def relative_chain(self, name: str) -> list[str]:
        """``[name, relative_to, ..., 'Basis']``; ``ValueError`` on a cycle."""
        chain = [name]
        seen = {name}
        cur = name
        while cur != BASIS:
            if cur not in self.keys:
                raise KeyError(f"unknown key {cur!r}")
            cur = self.keys[cur].relative_to
            if cur in seen:
                raise ValueError(f"relative_to cycle through key {cur!r}: {chain + [cur]}")
            seen.add(cur)
            chain.append(cur)
        return chain

    def data_of(self, name: str) -> np.ndarray:
        """Stored positions of ``name`` (the basis for ``'Basis'``); not a copy."""
        if name == BASIS:
            return self.basis
        try:
            return self.keys[name].data
        except KeyError:
            raise KeyError(f"unknown key {name!r}") from None

    def delta(self, name: str) -> np.ndarray:
        """Own delta of a key, ``data - data_of(relative_to)`` (mm)."""
        key = self.keys[name]
        return key.data - self.data_of(key.relative_to)

    def copy(self) -> "KeyStack":
        """Deep copy (solves are immutable; Revert restores a copy, DESIGN D-22)."""
        return KeyStack(self.basis.copy(), {k: _copy.deepcopy(v) for k, v in self.keys.items()})

    # ------------------------------------------------------------------ evaluation
    def evaluate(self) -> np.ndarray:
        """Blender relative mix: ``basis + sum value_k (data_k - data_of(relative_to_k))``.

        Muted keys are skipped (zero-valued keys contribute zero, as in Blender).
        The reference of a key is its referenced key's *stored* data, never that
        key's evaluated mix (shapekeys-blendshapes.md, "Relative evaluation").
        """
        self.validate()
        X = self.basis.copy()
        for key in self.keys.values():
            if key.mute or key.value == 0.0:
                continue
            X += key.value * (key.data - self.data_of(key.relative_to))
        return X

    # ------------------------------------------------------------------ construction
    @classmethod
    def from_fit(cls, basis, id_fit, asym_delta=None, stages: dict | None = None) -> "KeyStack":
        """Build the hand-off stack of DESIGN 4.17 from an engine fit.

        * ``ID_fit``: data ``id_fit``, relative to Basis, value 1, slider max 1.5
          (``handoff.id_fit_slider_max``).
        * ``Asym``: data ``id_fit + asym_delta`` (zeros when ``None``), relative to
          ``ID_fit``, value 1.
        * ``artist``: data = copy of ``id_fit`` (empty sculpt layer), relative to
          ``ID_fit``, value 1.
        * ``stage_*``: one muted diagnostic key per ``stages`` entry, relative to
          Basis, value 0.  The name gets the ``stage_`` prefix unless it already
          has it.

        All positions are (n, 3) mm and are copied.
        """
        B = _positions(basis, "basis")
        n = B.shape[0]
        idf = _positions(id_fit, "id_fit", n)
        asym = np.zeros_like(idf) if asym_delta is None else _positions(asym_delta, "asym_delta", n)
        keys: dict[str, Key] = {
            ID: Key(idf, BASIS, value=1.0, slider_max=HANDOFF_DEFAULTS.id_fit_slider_max.value),
            ASYM: Key(idf + asym, ID, value=1.0),
            ARTIST: Key(idf.copy(), ID, value=1.0),
        }
        for raw_name, pos in (stages or {}).items():
            name = str(raw_name)
            if not name.startswith(STAGE_PREFIX):
                name = STAGE_PREFIX + name
            if name in keys:
                raise ValueError(f"duplicate stage key {name!r}")
            keys[name] = Key(_positions(pos, f"stages[{raw_name!r}]", n), BASIS, value=0.0, mute=True)
        return cls(B, keys)

    # ------------------------------------------------------------------ edits
    def rebase(self, new_id_fit, new_asym_delta=None) -> None:
        """Replace ``ID_fit`` after a refit, keeping every dependent key's own delta exactly.

        DESIGN 4.17 (bl K2/K3): with ``delta = new_id - old_id``

        * ``artist.data += delta`` (the sculpt delta ``artist - ID_fit`` is unchanged);
        * ``Asym.data = new_id + new_asym_delta`` when given, else ``Asym.data += delta``;
        * ``ID_fit.data = new_id`` (stored exactly as the float64 input).

        Generalisation (same result for the DESIGN stack): any other key whose
        relative chain passes through a replaced key keeps its own delta,
        ``data' = data_of'(relative_to) + (data - data_of(relative_to))``; keys
        relative only to Basis (``stage_*``) are untouched.  The update is
        evaluated as ``new reference + old own delta`` (mathematically equal to
        ``data += delta``) so the preserved delta suffers a single rounding.
        """
        self.validate()
        if ID not in self.keys:
            raise KeyError(f"rebase needs an {ID!r} key")
        n = self.n_verts
        new_data: dict[str, np.ndarray] = {ID: _positions(new_id_fit, "new_id_fit", n)}
        if new_asym_delta is not None:
            if ASYM not in self.keys:
                raise KeyError(f"new_asym_delta given but the stack has no {ASYM!r} key")
            new_data[ASYM] = new_data[ID] + _positions(new_asym_delta, "new_asym_delta", n)
        explicit = set(new_data)

        def changed(name: str) -> bool:
            return any(k in explicit for k in self.relative_chain(name))

        def new_of(name: str) -> np.ndarray:
            if name == BASIS:
                return self.basis
            if name not in new_data:
                key = self.keys[name]
                if changed(name):
                    new_data[name] = new_of(key.relative_to) + (key.data - self.data_of(key.relative_to))
                else:
                    new_data[name] = key.data
            return new_data[name]

        for name in self.keys:
            new_of(name)
        for name, key in self.keys.items():
            key.data = np.ascontiguousarray(new_data[name], dtype=np.float64)

    def write_basis(self, new_basis) -> None:
        """Write Basis and propagate ``delta = new_basis - basis`` to every key (bl K3).

        Every key ultimately rests on Basis, so adding delta to all stored data keeps
        every own delta (hence ``artist - ID_fit``) and shifts the evaluated mix by
        exactly delta, whatever the key values.
        """
        self.validate()
        nb = _positions(new_basis, "new_basis", self.n_verts)
        d = nb - self.basis
        for key in self.keys.values():
            key.data = key.data + d
        self.basis = nb

    def artist_delta(self) -> np.ndarray:
        """The artist's sculpt layer ``artist.data - ID_fit.data`` (mm)."""
        return self.keys[ARTIST].data - self.keys[ID].data


# ====================================================================== masks
def _unit_field(a, name: str) -> np.ndarray:
    arr = np.asarray(a, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be a per-vertex (n,) array, got shape {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains non-finite values")
    return np.clip(arr, 0.0, 1.0)


def protect_mask(support) -> np.ndarray:
    """"Protect measured regions" mask (DESIGN 4.17): ``clip(support, 0, 1)``.

    ``support`` is the per-vertex measurement support in [0, 1] (1 = fully
    data-determined, proposal-artist ``s = 1 - tr Sigma_post / tr Sigma_prior``).
    The result is the value the bridge writes into Blender's ``.sculpt_mask``
    (FLOAT point attribute where 1 = fully masked, i.e. brushes cannot change the
    vertex). Measured vertices are therefore locked and guessed (prior-driven)
    vertices stay free to sculpt, which is the point of the operator.

    History: DESIGN 4.17 originally said "writes 1 - support"; under Blender's
    convention that protects the guessed regions instead (review of WP-13), so the
    design text and this function were corrected together.
    """
    return _unit_field(support, "support").copy()


def mask_to_data_weights(m, pin_sigma_mm: float | None = None,
                         threshold: float | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Painted sculpt mask -> (data weights, pin sigma) for the next refit (DESIGN 4.17, bl W5).

    Returns ``(w, sigma)``, both (n,) float64:

    * ``w = 1 - clip(m, 0, 1)``: per-vertex multiplier of the photo-data weight;
    * ``sigma`` (mm): ``pin_sigma_mm`` (default 0.2 mm, ``handoff.mask_pin_sigma_mm``)
      where ``m > threshold`` (default 0.5, ``handoff.mask_pin_threshold``), else
      ``+inf`` (no pin; information ``1/sigma^2 = 0``).  A pin holds the vertex at its
      current (artist-edited) position; the caller supplies that position.
    """
    mm = _unit_field(m, "mask")
    s = HANDOFF_DEFAULTS.mask_pin_sigma_mm.value if pin_sigma_mm is None else float(pin_sigma_mm)
    t = HANDOFF_DEFAULTS.mask_pin_threshold.value if threshold is None else float(threshold)
    if not (np.isfinite(s) and s > 0.0):
        raise ValueError(f"pin_sigma_mm must be finite and > 0, got {s}")
    w = 1.0 - mm
    sigma = np.where(mm > t, s, np.inf)
    return w, sigma


# ====================================================================== topology
def topology_guard(expected_sha: str, actual_sha: str) -> None:
    """Raise :class:`TopologyMismatch` (a ``ValueError``) unless the topology hashes match.

    Hashes are :func:`face3d.model.template_kit.topology_sha256` hex digests
    (compared case-insensitively).  Shape keys and the limit-stencil cage are only
    meaningful on the exact topology they were computed for (DESIGN 3.2, bl K1).
    """
    for label, val in (("expected", expected_sha), ("actual", actual_sha)):
        if not isinstance(val, str):
            raise TopologyMismatch(f"{label} topology hash must be a hex string, got {type(val).__name__}")
    e = expected_sha.strip().lower()
    a = actual_sha.strip().lower()
    for label, val in (("expected", e), ("actual", a)):
        if len(val) != 64 or any(c not in "0123456789abcdef" for c in val):
            raise TopologyMismatch(f"{label} topology hash is not a SHA-256 hex digest: {val[:16]!r}")
    if e != a:
        raise TopologyMismatch(f"topology {a[:12]}... does not match the expected {e[:12]}...")
