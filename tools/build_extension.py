#!/usr/bin/env python3
"""Build the Face3D Likeness Blender extension zip (WP-21; DESIGN 6.1, D-28, D-29).

Vendors ``face3d/`` into ``engine/face3d/`` inside a copy of the extension,
validates it and writes a deterministic zip (sorted entries, fixed timestamps).

Refuses (raises :class:`BuildError`) when:

* the manifest lacks a required key, has another id than ``face3d_likeness``,
  a licence other than ``SPDX:GPL-3.0-or-later`` or a tagline over 64
  characters (Blender's limit; DESIGN 6.1);
* a store build has a ``network`` permission or no GPL-3.0 full-text file;
* a file under ``assets/`` is not listed in ``assets.toml`` (``[[asset]]``
  entries with ``path`` and ``license``) with licence ``CC0-1.0`` (known fact 3,
  D-28);
* any ``.whl`` is present or any file exceeds 25 MB (store rule, D-28);
* an extension ``.py`` lacks the GPL SPDX header, or (with ``add_spdx=False``)
  a vendored engine file lacks an SPDX header (DESIGN 6.1);
* the vendored engine imports anything outside numpy and the standard library.

Vendored engine files that lack a header get ``# SPDX-License-Identifier: MIT``
(they stay MIT inside the GPL package, DESIGN 6.1). Files matching the
manifest's ``[build] paths_exclude_pattern`` are left out: ``dir/`` matches a
directory at any depth, ``/dir/`` only at the extension root, other patterns
are fnmatch globs on the file name (or the relative path if they contain ``/``).
Engine ``tests`` and ``__pycache__`` directories are never vendored.
"""
from __future__ import annotations

import ast
import fnmatch
import os
import sys
import tomllib
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MAX_FILE_BYTES = 25 * 1024 * 1024
TAGLINE_MAX = 64
GPL_SPDX = "# SPDX-License-Identifier: GPL-3.0-or-later"
MIT_SPDX = "# SPDX-License-Identifier: MIT"
REQUIRED_KEYS = ("schema_version", "id", "version", "name", "tagline", "maintainer", "type",
                 "blender_version_min", "license")
EXT_ID = "face3d_likeness"
_ALWAYS_EXCLUDE_DIRS = {"__pycache__", "tests"}   # engine vendoring (not the manifest list)
_ZIP_DATE = (2026, 1, 1, 0, 0, 0)


class BuildError(ValueError):
    """The build was refused; the message says why."""


def _resolve(p) -> Path:
    p = Path(p)
    return p if p.is_absolute() or p.exists() else REPO_ROOT / p


# ---------------------------------------------------------------- manifest
def validate_manifest(path: Path, store: bool = True) -> dict:
    try:
        with open(path, "rb") as fh:
            m = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise BuildError("manifest unreadable: %s" % e)
    for k in REQUIRED_KEYS:
        if k not in m:
            raise BuildError("manifest missing required key %r" % k)
    if m["id"] != EXT_ID:
        raise BuildError("manifest id must be %r (ids are permanent)" % EXT_ID)
    if "SPDX:GPL-3.0-or-later" not in list(m["license"]):
        raise BuildError("manifest licence must contain SPDX:GPL-3.0-or-later")
    if len(str(m["tagline"])) > TAGLINE_MAX:
        raise BuildError("tagline longer than %d characters" % TAGLINE_MAX)
    if store and "network" in (m.get("permissions") or {}):
        raise BuildError("store builds must not request the network permission")
    return m


# ---------------------------------------------------------------- exclusion
def _excluded(rel: str, patterns) -> bool:
    parts = rel.split("/")
    for pat in patterns:
        if pat.endswith("/"):
            d = pat.strip("/")
            if pat.startswith("/"):
                if parts[0] == d and len(parts) > 1:
                    return True
            elif d in parts[:-1]:
                return True
        elif "/" in pat.strip("/"):
            if fnmatch.fnmatch(rel, pat.lstrip("/")):
                return True
        elif fnmatch.fnmatch(parts[-1], pat):
            return True
    return False


# ---------------------------------------------------------------- checks
def check_engine_imports(src: str, name: str, allowed_extra=("numpy", "face3d")) -> None:
    std = set(sys.stdlib_module_names) | {"__future__"}
    tree = ast.parse(src, filename=name)
    for node in ast.walk(tree):
        mods = []
        if isinstance(node, ast.Import):
            mods = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods = [node.module]
        for mod in mods:
            top = mod.split(".")[0]
            if top not in std and top not in allowed_extra:
                raise BuildError("%s imports %r (engine allows numpy and the standard library only)"
                                 % (name, mod))


def _has_spdx(text: str) -> bool:
    return any(ln.startswith("# SPDX-License-Identifier:") for ln in text.splitlines()[:5])


def _with_header(text: str, header: str) -> str:
    lines = text.splitlines(keepends=True)
    if lines and lines[0].startswith("#!"):
        return lines[0] + header + "\n" + "".join(lines[1:])
    return header + "\n" + text


def _check_assets(ext_dir: Path) -> None:
    adir = ext_dir / "assets"
    if not adir.is_dir():
        return
    files = sorted(p.relative_to(ext_dir).as_posix() for p in adir.rglob("*") if p.is_file())
    listed = {}
    for tp in (ext_dir / "assets" / "assets.toml", ext_dir / "assets.toml"):
        if tp.is_file():
            with open(tp, "rb") as fh:
                doc = tomllib.load(fh)
            for e in doc.get("asset", []):
                listed[str(e.get("path"))] = str(e.get("license"))
    for rel in files:
        if rel == "assets/assets.toml":
            continue
        lic = listed.get(rel)
        if lic is None:
            raise BuildError("asset %s is not listed in assets.toml" % rel)
        if lic != "CC0-1.0":
            raise BuildError("asset %s has licence %r; only CC0-1.0 is allowed" % (rel, lic))


# ---------------------------------------------------------------- build
def build(out_zip, engine_src="face3d", ext_src="blender_ext/face3d_likeness", gpl_text=None,
          store=True, add_spdx=True) -> dict:
    """Build ``out_zip``; returns a report dict (files, spdx_added, size, manifest)."""
    engine = _resolve(engine_src)
    ext = _resolve(ext_src)
    if not engine.is_dir():
        raise BuildError("engine source %s not found" % engine)
    manifest = validate_manifest(ext / "blender_manifest.toml", store=store)
    patterns = list((manifest.get("build") or {}).get("paths_exclude_pattern", []))

    gpl_bytes = None
    if store or gpl_text is not None:
        if gpl_text is None or not Path(gpl_text).is_file():
            raise BuildError("store builds require the GPL-3.0 full-text file (gpl_text)")
        gpl_bytes = Path(gpl_text).read_bytes()
        if b"GNU GENERAL PUBLIC LICENSE" not in gpl_bytes or b"Version 3" not in gpl_bytes:
            raise BuildError("gpl_text does not look like the GPL-3.0 full text")

    _check_assets(ext)

    entries: dict[str, bytes] = {}
    spdx_added: list[str] = []

    def add(rel: str, data: bytes):
        if rel.endswith(".whl"):
            raise BuildError("wheels must not be bundled: %s" % rel)
        if len(data) > MAX_FILE_BYTES:
            raise BuildError("%s exceeds 25 MB" % rel)
        entries[rel] = data

    for p in sorted(ext.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(ext).as_posix()
        if _excluded(rel, patterns):
            continue
        data = p.read_bytes()
        if rel.endswith(".py"):
            text = data.decode("utf-8")
            if GPL_SPDX not in text.splitlines()[:3]:
                raise BuildError("%s lacks the header %r" % (rel, GPL_SPDX))
        add(rel, data)

    for p in sorted(engine.rglob("*")):
        if not p.is_file():
            continue
        sub = p.relative_to(engine).as_posix()
        if set(sub.split("/")[:-1]) & _ALWAYS_EXCLUDE_DIRS or sub.endswith(".pyc"):
            continue
        rel = "engine/face3d/%s" % sub
        if _excluded(rel, patterns):
            continue
        data = p.read_bytes()
        if sub.endswith(".py"):
            text = data.decode("utf-8")
            check_engine_imports(text, rel)
            if not _has_spdx(text):
                if not add_spdx:
                    raise BuildError("%s lacks an SPDX header" % rel)
                data = _with_header(text, MIT_SPDX).encode("utf-8")
                spdx_added.append(rel)
        add(rel, data)

    if gpl_bytes is not None:
        add("LICENSE", gpl_bytes)

    out_zip = Path(out_zip)
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_zip.with_name(out_zip.name + ".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in sorted(entries):
            zi = zipfile.ZipInfo(rel, date_time=_ZIP_DATE)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zf.writestr(zi, entries[rel])
    os.replace(tmp, out_zip)
    return {"out_zip": str(out_zip), "files": sorted(entries), "n_files": len(entries),
            "spdx_added": spdx_added, "size": out_zip.stat().st_size, "manifest": manifest,
            "store": bool(store)}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out_zip")
    ap.add_argument("--gpl-text", default=None, help="path to the GPL-3.0 full text (required for store)")
    ap.add_argument("--no-store", action="store_true", help="off-store build (network permission allowed)")
    ap.add_argument("--no-spdx", action="store_true", help="refuse instead of adding MIT headers")
    a = ap.parse_args(argv)
    try:
        rep = build(a.out_zip, gpl_text=a.gpl_text, store=not a.no_store, add_spdx=not a.no_spdx)
    except BuildError as e:
        print("build refused: %s" % e, file=sys.stderr)
        return 2
    print("wrote %s (%d files, %d bytes, %d SPDX headers added)"
          % (rep["out_zip"], rep["n_files"], rep["size"], len(rep["spdx_added"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
