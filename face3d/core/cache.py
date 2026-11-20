"""Stage cache with data-class TTLs (DESIGN 2.1 invariant 5, eth F1-F20).

In-memory LRU always; disk only when ``root`` is set and the TTL for the entry's
data class is > 0 days. Biometric geometry and personal images are TTL 0:
never written to disk. TTL defaults: BIOMETRIC_GEOMETRY 0, PERSONAL_IMAGE 0,
LIKENESS_ASSET 30, AGGREGATE_PRIOR 365 days (spec WP-04; eth digest section 3).
Recognition embeddings (BIOMETRIC_TEMPLATE) are RAM-only (TTL > 0 is refused unless
POLICY['persist_embeddings']); BIOMETRIC_GEOMETRY / PERSONAL_IMAGE TTL is capped at 30 days.

Disk round trip: scalars/containers go through JSON, so tuples come back as lists,
nested arrays as lists, and non-finite floats are restored as floats; top-level
ndarray values round trip exactly. ``get`` returns a shallow copy.
"""
from __future__ import annotations

import json
import math
import os
import time
from collections import OrderedDict
from pathlib import Path

import numpy as np

from face3d.core.policy import POLICY, DataClass
from face3d.core.schema import canonical_json, sha256_bytes

DEFAULT_TTL_DAYS = {
    DataClass.BIOMETRIC_GEOMETRY: 0,
    DataClass.PERSONAL_IMAGE: 0,
    DataClass.LIKENESS_ASSET: 30,
    DataClass.AGGREGATE_PRIOR: 365,
}


_MAX_TTL_RESTRICTED = 30
_NF = "__nonfinite__"


def _decode(o):
    if isinstance(o, dict):
        if set(o) == {_NF}:
            return float(o[_NF])
        return {k: _decode(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_decode(v) for v in o]
    return o


class StageCache:
    def __init__(self, root: Path | None = None, ttl_days: dict | None = None, max_items: int = 64):
        self.root = Path(root) if root is not None else None
        self.ttl_days = dict(DEFAULT_TTL_DAYS)
        if ttl_days:
            self.ttl_days.update(ttl_days)
        if self.ttl_days.get(DataClass.BIOMETRIC_TEMPLATE, 0) > 0 \
                and not POLICY["persist_embeddings"]:
            raise ValueError("BIOMETRIC_TEMPLATE (embeddings) must never be persisted (F10)")
        for dc in (DataClass.BIOMETRIC_GEOMETRY, DataClass.PERSONAL_IMAGE):
            t = self.ttl_days.get(dc, 0)
            if not (0 <= t <= _MAX_TTL_RESTRICTED):
                raise ValueError(f"ttl_days[{dc.name}]={t} outside 0-{_MAX_TTL_RESTRICTED}")
        self.max_items = max_items
        self._mem: OrderedDict[str, tuple[dict, DataClass]] = OrderedDict()

    @staticmethod
    def key(stage: str, inputs_hashes: dict, config_snapshot: dict, seed: int,
            engine_version: str) -> str:
        return sha256_bytes(canonical_json({
            "stage": stage, "inputs": inputs_hashes, "config": config_snapshot,
            "seed": int(seed), "engine_version": engine_version}))

    def _paths(self, key):
        return self.root / f"{key}.npz", self.root / f"{key}.json"

    def _ttl(self, dc) -> int:
        return self.ttl_days.get(dc, 0)

    def get(self, key: str):
        if key in self._mem:
            self._mem.move_to_end(key)
            return dict(self._mem[key][0])
        if self.root is None:
            return None
        npz, js = self._paths(key)
        if not js.exists():
            return None
        meta = json.loads(js.read_text(encoding="utf-8"))
        dc = DataClass[meta["data_class"]]
        ttl = self._ttl(dc)
        if ttl <= 0 or time.time() - js.stat().st_mtime > ttl * 86400:
            self._unlink(key)
            return None
        value = dict(_decode(meta["value"]))
        if npz.exists():
            with np.load(npz, allow_pickle=False) as z:
                value.update({k: z[k] for k in z.files})
        self._remember(key, value, dc)
        return dict(value)

    def put(self, key: str, value: dict, data_class: DataClass) -> None:
        self._remember(key, value, data_class)
        if self.root is None or self._ttl(data_class) <= 0:
            return
        arrays = {k: v for k, v in value.items() if isinstance(v, np.ndarray)}
        plain = {k: v for k, v in value.items() if k not in arrays}
        # serialise first so a failure leaves nothing on disk
        text = json.dumps({"data_class": data_class.name,
                           "value": json.loads(canonical_json(plain))})
        self.root.mkdir(parents=True, exist_ok=True)
        npz, js = self._paths(key)
        tmp_npz = npz.with_name(npz.name + ".tmp")
        tmp_js = js.with_name(js.name + ".tmp")
        try:
            if arrays:
                with open(tmp_npz, "wb") as f:
                    np.savez(f, **arrays)
                os.replace(tmp_npz, npz)
            else:
                npz.unlink(missing_ok=True)  # drop stale arrays from an earlier put
            tmp_js.write_text(text, encoding="utf-8")
            os.replace(tmp_js, js)
        finally:
            tmp_npz.unlink(missing_ok=True)
            tmp_js.unlink(missing_ok=True)

    def _remember(self, key, value, dc):
        self._mem[key] = (dict(value), dc)
        self._mem.move_to_end(key)
        while len(self._mem) > self.max_items:
            self._mem.popitem(last=False)

    def _unlink(self, key):
        if self.root is None:
            return
        for p in self._paths(key):
            p.unlink(missing_ok=True)

    def _disk_entries(self):
        """Yield (key, DataClass | None) for every key on disk; None = unreadable/orphan."""
        if self.root is None or not self.root.exists():
            return
        keys = {p.stem for p in self.root.glob("*.json")} | {p.stem for p in self.root.glob("*.npz")}
        for k in sorted(keys):
            dc = None
            try:
                meta = json.loads((self.root / f"{k}.json").read_text(encoding="utf-8"))
                dc = DataClass[meta["data_class"]]
            except (OSError, ValueError, KeyError, TypeError):
                dc = None
            yield k, dc

    def purge(self, data_class: DataClass | None = None) -> list:
        """Delete entries (all or of one class); return the purged key hashes only.

        Orphaned/unreadable disk entries (class unknown) are always deleted (fail closed).
        """
        purged = set()
        for k, (_, dc) in list(self._mem.items()):
            if data_class is None or dc == data_class:
                del self._mem[k]
                purged.add(k)
        for k, dc in list(self._disk_entries()):
            if dc is None or data_class is None or dc == data_class:
                self._unlink(k)
                purged.add(k)
        return sorted(purged)

    def close(self) -> None:
        """Purge TTL-0 (and orphaned) disk entries and clear memory."""
        for k, dc in list(self._disk_entries()):
            if dc is None or self._ttl(dc) <= 0:
                self._unlink(k)
        self._mem.clear()
