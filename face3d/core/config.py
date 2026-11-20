"""Badged defaults registry (DESIGN 2.1 invariant 4, section 5 H8, eth A2).

Every numeric default is a ``Default`` carrying a badge and a source citation:
  checkmark verified, page = from a cited document, brain = engineering judgement,
  arrows = tunable/relative, new = new/unvalidated, numbers = derived.
Overrides come from a TOML file (nested ``[namespace]`` tables) or a dict, and
are bounds- and type-checked. Units are documented per Default.
Every namespace must be registered (module imported) before ``resolve()``: an
override for an unregistered key raises ValueError.
"""
from __future__ import annotations

import math
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from face3d.core.schema import _clean, canonical_json

BADGES = ("✅", "\U0001F4C4", "\U0001F9E0", "↔️", "\U0001F195", "\U0001F522")
UNVERIFIED_BADGES = ("\U0001F9E0", "↔️", "\U0001F195")  # brain, arrows, new (H8)


@dataclass(frozen=True)
class Default:
    value: Any
    badge: str
    source: str
    unit: str = ""
    bounds: tuple | None = None  # inclusive (lo, hi); either may be None

    def __post_init__(self):
        if self.badge not in BADGES:
            raise ValueError(f"invalid badge {self.badge!r}")
        if not self.source:
            raise ValueError("Default requires a source citation")
        v = self.value
        if isinstance(v, float) and math.isnan(v):
            raise ValueError("Default value must not be NaN")
        if self.bounds is not None:
            _check_bounds("Default", self, v)


class Namespace:
    def __init__(self, name: str, mapping: dict):
        self._name = name
        self._map = dict(mapping)

    def __getattr__(self, k):
        try:
            return self.__dict__["_map"][k]
        except KeyError:
            raise AttributeError(k) from None

    def __getitem__(self, k):
        return self._map[k]

    def __iter__(self):
        return iter(self._map)

    def __len__(self):
        return len(self._map)

    def items(self):
        return self._map.items()


_REGISTRY: dict[str, Default] = {}


def _same(a: Default, b: Default) -> bool:
    return (a.badge, a.source, a.unit, a.bounds) == (b.badge, b.source, b.unit, b.bounds) \
        and canonical_json(a.value) == canonical_json(b.value) \
        and type(a.value) is type(b.value)


def register_defaults(namespace: str, mapping: dict) -> Namespace:
    """Register ``mapping`` under ``namespace``; idempotent if identical, else ValueError."""
    for k, d in mapping.items():
        if not isinstance(d, Default):
            raise TypeError(f"{namespace}.{k} must be a Default")
        full = f"{namespace}.{k}"
        if full in _REGISTRY and not _same(_REGISTRY[full], d):
            raise ValueError(f"conflicting re-registration of default {full!r}")
    for k, d in mapping.items():
        _REGISTRY[f"{namespace}.{k}"] = d
    return Namespace(namespace, mapping)


def get(full_name: str) -> Default:
    try:
        return _REGISTRY[full_name]
    except KeyError:
        raise KeyError(f"unknown default {full_name!r}") from None


def load_overrides(path_toml) -> dict:
    with open(path_toml, "rb") as f:
        return tomllib.load(f)


def _flatten(overrides: dict) -> dict:
    flat = {}
    for k, v in overrides.items():
        if isinstance(v, dict):
            for k2, v2 in _flatten(v).items():
                flat[f"{k}.{k2}"] = v2
        else:
            flat[k] = v
    return flat


def _check_bounds(full: str, d: Default, v) -> None:
    if isinstance(v, float) and math.isnan(v):
        raise ValueError(f"{full}: NaN is not an allowed value")
    if d.bounds is None:
        return
    lo, hi = d.bounds
    try:
        bad = (lo is not None and v < lo) or (hi is not None and v > hi)
    except TypeError as e:
        raise ValueError(f"{full}: value {v!r} is not comparable with bounds {d.bounds!r}") from e
    if bad:
        raise ValueError(f"{full}: value {v!r} outside bounds {d.bounds!r}")


def _check_type(full: str, d: Default, v) -> None:
    dv = d.value
    if isinstance(dv, bool):
        ok = isinstance(v, bool)
    elif isinstance(dv, int):
        ok = isinstance(v, int) and not isinstance(v, bool)
    elif isinstance(dv, float):
        ok = isinstance(v, (int, float)) and not isinstance(v, bool)
    else:
        ok = isinstance(v, type(dv)) or dv is None
    if not ok:
        raise ValueError(f"{full}: override {v!r} has type {type(v).__name__}, "
                         f"expected {type(dv).__name__}")


def resolve(overrides: dict | None = None) -> dict:
    """Return {full_name: value} for all defaults with overrides applied and bounds checked."""
    out = {k: d.value for k, d in _REGISTRY.items()}
    for full, v in _flatten(overrides or {}).items():
        if full not in _REGISTRY:
            raise ValueError(f"unknown default override {full!r}")
        _check_type(full, _REGISTRY[full], v)
        _check_bounds(full, _REGISTRY[full], v)
        out[full] = v
    for full, d in _REGISTRY.items():
        _check_bounds(full, d, out[full])
    return out


def unverified_count(resolved: dict | None = None) -> int:
    """Count active defaults badged brain/arrows/new (H8). ``resolved`` limits to its keys."""
    keys = _REGISTRY.keys() if resolved is None else [k for k in resolved if k in _REGISTRY]
    return sum(1 for k in keys if _REGISTRY[k].badge in UNVERIFIED_BADGES)


def snapshot() -> dict:
    """Sorted JSON-serialisable view of all defaults (for config hashing)."""
    return {k: {"value": _clean(d.value), "badge": d.badge, "source": d.source, "unit": d.unit,
                "bounds": list(d.bounds) if d.bounds is not None else None}
            for k, d in sorted(_REGISTRY.items())}
