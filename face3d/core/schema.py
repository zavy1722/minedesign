"""Versioned JSON / npz file formats and hashing helpers.

Conventions: JSON files are ``{"format": str, "version": int, ...}`` written
with sorted keys, indent 1, and no NaN/Inf (non-finite floats become null).
Hashes are lowercase hex SHA-256 (DESIGN 2.1 invariant 3; provenance).
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


class FormatError(ValueError):
    """Raised when a file has the wrong format tag or an unsupported version."""


def _clean(obj: Any, distinct_nonfinite: bool = False) -> Any:
    """Convert numpy types to builtins; non-finite floats to None (or, with
    ``distinct_nonfinite``, to a tagged object so they hash differently from null).
    Raises ValueError when two dict keys collide after ``str()``."""
    if isinstance(obj, np.ndarray):
        return _clean(obj.tolist(), distinct_nonfinite)
    if isinstance(obj, np.generic):
        return _clean(obj.item(), distinct_nonfinite)
    if isinstance(obj, float):
        if math.isfinite(obj):
            return obj
        return {"__nonfinite__": repr(obj)} if distinct_nonfinite else None
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            ks = str(k)
            if ks in out:
                raise ValueError(f"duplicate key {ks!r} after string conversion")
            out[ks] = _clean(v, distinct_nonfinite)
        return out
    if isinstance(obj, (list, tuple)):
        return [_clean(v, distinct_nonfinite) for v in obj]
    return obj


def _no_constant(name: str):
    raise FormatError(f"non-finite JSON constant {name!r} not allowed")


def dump_json(obj: dict, path, *, format: str | None = None, version: int | None = None) -> None:
    """Write ``obj`` as JSON with ``format`` and ``version`` keys.

    ``format``/``version`` may be given as arguments or already be keys of
    ``obj`` (arguments win). Both must end up present.
    """
    d = dict(obj)
    if format is not None:
        d["format"] = format
    if version is not None:
        d["version"] = version
    if "format" not in d or "version" not in d:
        raise FormatError("dump_json requires 'format' and 'version'")
    text = json.dumps(_clean(d), sort_keys=True, indent=1, allow_nan=False)
    Path(path).write_text(text + "\n", encoding="utf-8")


def load_json(path, expect_format: str | None = None, max_version: int | None = None) -> dict:
    """Load a JSON file, validating its format tag and version."""
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=_no_constant)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise FormatError(f"invalid JSON: {e}") from e
    if not isinstance(d, dict) or "format" not in d or "version" not in d:
        raise FormatError("missing 'format'/'version'")
    if expect_format is not None and d["format"] != expect_format:
        raise FormatError(f"expected format {expect_format!r}, got {d['format']!r}")
    v = d["version"]
    if not isinstance(v, int) or isinstance(v, bool):
        raise FormatError(f"bad version {v!r}")
    if max_version is not None and v > max_version:
        raise FormatError(f"version {v} is newer than supported {max_version}")
    return d


def canonical_json(obj: Any) -> bytes:
    """Canonical bytes for hashing: sorted keys, compact separators, arrays as lists.

    Floats use Python repr (shortest round-trip); non-finite values are tagged
    objects (distinct from null and from each other).
    """
    return json.dumps(_clean(obj, True), sort_keys=True, separators=(",", ":"),
                      allow_nan=False, ensure_ascii=True).encode("ascii")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path, chunk: int = 1 << 20) -> str:
    """Streamed SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def save_arrays(path_npz, **arrays) -> dict:
    """Save arrays to an .npz; return manifest {name: {file, sha256, shape, dtype}}.

    The sha256 is of each array's C-contiguous bytes (independent of zip layout).
    """
    path = Path(path_npz)
    arrs = {k: np.ascontiguousarray(v) for k, v in arrays.items()}
    with open(path, "wb") as f:
        np.savez(f, **arrs)
    return {k: {"file": path.name, "sha256": sha256_bytes(a.tobytes()),
                "shape": list(a.shape), "dtype": str(a.dtype)} for k, a in arrs.items()}


def load_arrays(path_npz, manifest: dict | None = None) -> dict:
    """Load arrays; when ``manifest`` is given verify each sha256 (FormatError on mismatch)."""
    with np.load(path_npz, allow_pickle=False) as z:
        out = {k: z[k] for k in z.files}
    if manifest is not None:
        for name, m in manifest.items():
            if name not in out:
                raise FormatError(f"array {name!r} missing from {path_npz}")
            a = out[name]
            if "shape" in m and list(a.shape) != list(m["shape"]):
                raise FormatError(f"shape mismatch for array {name!r}")
            if "dtype" in m and str(a.dtype) != m["dtype"]:
                raise FormatError(f"dtype mismatch for array {name!r}")
            if sha256_bytes(np.ascontiguousarray(a).tobytes()) != m["sha256"]:
                raise FormatError(f"sha256 mismatch for array {name!r}")
    return out
