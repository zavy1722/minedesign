"""Append-only audit log holding hashes and codes only (eth 2.6, F19).

No coordinates, arrays or file paths may be logged.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from face3d.core.policy import DataClass

_ALLOWED = ("event", "data_class", "sha256", "scope", "detail_code")
_MAX_LEN = 128
_DRIVE = re.compile(r"^[A-Za-z]:")
_CODE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,63}$")
_SHA = re.compile(r"^[0-9a-f]{64}$")
_NUM_TOKEN = re.compile(r"\d+(?:\.\d+)?")


def _check_code(name: str, v, allow_empty: bool = False) -> str:
    """Event/scope/detail codes: short identifier-like tokens only (no filenames,
    coordinate payloads or free text)."""
    _check_str(name, v)
    if v == "" and allow_empty:
        return v
    if not _CODE.match(v) or len(_NUM_TOKEN.findall(v)) >= 2 or \
            re.search(r"\.(jpe?g|png|heic|tiff?|obj|ply|npz|json)$", v, re.I):
        raise ValueError(f"audit field {name!r} is not a short code")
    return v


def _check_str(name: str, v) -> str:
    if not isinstance(v, str):
        raise ValueError(f"audit field {name!r} must be a string (got {type(v).__name__})")
    if len(v) > _MAX_LEN or "/" in v or "\\" in v or _DRIVE.match(v) or v.startswith("~"):
        raise ValueError(f"audit field {name!r} looks like a path or free text")
    return v


def _check_sha(v) -> str:
    _check_str("sha256", v)
    if v != "" and not _SHA.match(v):
        raise ValueError("audit field 'sha256' must be 64 lowercase hex chars or empty")
    return v


class AuditLog:
    def __init__(self, path):
        self.path = Path(path)

    def write(self, event: str, data_class: DataClass, sha256: str, scope: str = "",
              detail_code: str = "") -> None:
        if not isinstance(data_class, DataClass):
            raise ValueError("data_class must be a DataClass")
        rec = {
            "event": _check_code("event", event),
            "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "data_class": data_class.name,
            "sha256": _check_sha(sha256),
            "scope": _check_code("scope", scope, True),
            "detail_code": _check_code("detail_code", detail_code, True),
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
