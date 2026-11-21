#!/usr/bin/env python3
"""CI policy checks of the face3d repository (WBS WP-23 item 2; DESIGN 2.1 invariants, 6.2, H12, eth A7/A8).

Run ``python tools/ci_checks.py`` (exit status 0 = every check passes) or call the functions from
tests (``tests/test_policy_ci.py``).  Every ``check_*`` function returns a list of violation strings
(empty = pass) and has no side effect on the repository.

Checks
------
(a) :func:`check_engine_imports`: no ``import`` of ``bpy``, ``scipy``, ``cv2``, ``torch``, ``mediapipe``
    or ``PIL`` (nor of the other Blender modules) anywhere under ``face3d/`` (AST; DESIGN 2.1
    invariant 1, bl A1/A6).
(b) :func:`check_numpy_neutral`: none of the NumPy 1-only aliases ``np.float_``, ``np.in1d``,
    ``np.product``, ``np.alltrue``, ``np.sometrue``, ``np.Inf``, ``np.NaN`` under ``face3d/``
    (AST; bl A4).
(c) :func:`check_defaults`: import every ``face3d`` module, then every
    :class:`face3d.core.config.Default` in the registry has a valid badge and a non-empty source
    (DESIGN 8 conventions).
(d) :func:`check_blender_ext`: only ``bridge.py`` uses ``foreach_get`` / ``foreach_set`` / ``pixels``;
    the manifest passes the store lint of ``tools/build_extension.py`` (DESIGN 6.1); every ``.py`` of
    the extension starts with the GPL SPDX header (DESIGN 6.2).
(e) :func:`check_fixture_provenance`: every fixture / golden file under ``tests/`` that contains
    landmark or mesh data declares ``provenance`` in {synthetic, cc0, consented} (no real-person
    detections are committed, eth A8, DESIGN D-26).  Binary geometry or image files need a sidecar
    ``<file>.provenance.json`` (or a ``PROVENANCE.json`` in their directory) with that field.
(f) :func:`check_pipeline_offline`: a full synthetic pipeline run (ingest .. report, with texture)
    completes inside :func:`face3d.core.policy.network_guard` (eth A7).

The synthetic project of (f) is generated from a seed at run time in a temporary directory
(:func:`synthetic_project`; provenance ``synthetic``): a WP-11 out-of-prior surface subject of the
procedural CC0 head, a 5-view rear-phone rig at 600 x 800 px, simulated detections and shaded renders.
Units are those of the engine (mm, pixels with the origin at the top-left corner).

This script is a maintainer tool (DESIGN 2.2 L9): the engine never imports it.
"""
from __future__ import annotations

import argparse
import ast
import importlib
import importlib.util
import json
import os
import pkgutil
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Callable, Sequence

REPO = Path(__file__).resolve().parents[1]

# The engine's matrices are small: multithreaded BLAS only slows the reference run down (see
# tests/conftest.py).  numpy is imported lazily by the checks, so this takes effect when run as a script.
for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

#: (a) top-level module names the engine must never import (DESIGN 2.1 invariant 1; WBS WP-23 2a; the
#: Blender-only modules are listed as well: they exist only inside Blender).
FORBIDDEN_IMPORTS = ("bpy", "scipy", "cv2", "torch", "mediapipe", "PIL",
                     "mathutils", "bmesh", "gpu", "gpu_extras", "blf")
#: (b) attributes of ``numpy`` removed or deprecated in NumPy 2 (WBS WP-23 2b; bl A4).
FORBIDDEN_NUMPY = ("float_", "in1d", "product", "alltrue", "sometrue", "Inf", "NaN")
#: (d) attributes only ``bridge.py`` may use (DESIGN 6.2 bridge rule).
BRIDGE_ONLY_ATTRS = ("foreach_get", "foreach_set", "pixels")
GPL_HEADER = "# SPDX-License-Identifier: GPL-3.0-or-later"
#: (e) allowed provenance values (WBS WP-23 2e; eth A8).
PROVENANCES = ("synthetic", "cc0", "consented")
#: (e) JSON keys / formats that mark a file as carrying landmark or mesh data.
GEOMETRY_KEYS = ("uv", "landmarks", "landmark_sets", "faces", "vertices", "triangles", "pins", "points",
                 "X", "V", "detections")
GEOMETRY_FORMATS = ("face3d.landmarks", "face3d.project", "face3d.result", "face3d.template_kit",
                    "face3d.render_records", "face3d.scheme")
#: (e) binary files that can only hold geometry or pixels.
BINARY_SUFFIXES = (".npy", ".npz", ".obj", ".ply", ".stl", ".png", ".jpg", ".jpeg", ".heic", ".heif",
                   ".tif", ".tiff", ".bmp", ".webp", ".blend")


def _py_files(root: Path) -> list[Path]:
    return sorted(p for p in Path(root).rglob("*.py") if "__pycache__" not in p.parts)


def _rel(p: Path, repo: Path) -> str:
    try:
        return str(Path(p).relative_to(repo))
    except ValueError:
        return str(p)


# ---------------------------------------------------------------------------- (a)
def check_engine_imports(repo: Path = REPO, forbidden: Sequence[str] = FORBIDDEN_IMPORTS) -> list[str]:
    """(a) AST scan of ``face3d/``: no ``import x`` / ``from x import`` of a forbidden top-level module
    (also inside functions and ``try`` blocks), and no ``__import__`` / ``importlib.import_module`` of
    one given as a string literal."""
    bad: list[str] = []
    forb = set(forbidden)
    for p in _py_files(Path(repo) / "face3d"):
        tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            elif isinstance(node, ast.Call):
                f = node.func
                fn = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
                if fn in ("__import__", "import_module") and node.args and isinstance(node.args[0], ast.Constant) \
                        and isinstance(node.args[0].value, str):
                    names = [node.args[0].value]
            for n in names:
                if n.split(".")[0] in forb:
                    bad.append(f"{_rel(p, repo)}:{node.lineno}: imports {n!r}")
    return bad


# ---------------------------------------------------------------------------- (b)
def check_numpy_neutral(repo: Path = REPO, forbidden: Sequence[str] = FORBIDDEN_NUMPY) -> list[str]:
    """(b) AST scan of ``face3d/``: no ``np.<alias>`` / ``numpy.<alias>`` attribute (whatever name numpy
    was imported under) and no ``from numpy import <alias>`` for the NumPy 1-only aliases."""
    bad: list[str] = []
    forb = set(forbidden)
    for p in _py_files(Path(repo) / "face3d"):
        tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        aliases = {"numpy"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                aliases |= {a.asname or a.name for a in node.names if a.name == "numpy"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in forb and isinstance(node.value, ast.Name) \
                    and node.value.id in aliases:
                bad.append(f"{_rel(p, repo)}:{node.lineno}: uses {node.value.id}.{node.attr}")
            elif isinstance(node, ast.ImportFrom) and node.module == "numpy":
                for a in node.names:
                    if a.name in forb:
                        bad.append(f"{_rel(p, repo)}:{node.lineno}: imports numpy.{a.name}")
    return bad


# ---------------------------------------------------------------------------- (c)
def import_engine_modules(repo: Path = REPO) -> tuple[list[str], list[str]]:
    """Import every module of the ``face3d`` package of ``repo``.  Returns (names, errors)."""
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    import face3d
    names, errors = [], []
    for m in pkgutil.walk_packages(face3d.__path__, "face3d."):
        if m.name.endswith(".__main__"):
            continue
        names.append(m.name)
        try:
            importlib.import_module(m.name)
        except Exception as e:  # noqa: BLE001 - the check reports every import failure
            errors.append(f"{m.name}: import failed: {type(e).__name__}: {e}")
    return names, errors


def check_defaults(repo: Path = REPO) -> list[str]:
    """(c) After importing every engine module, every registered Default carries one of
    ``core.config.BADGES`` and a non-empty source citation; the registry is not empty and resolves
    within its own bounds."""
    names, bad = import_engine_modules(repo)
    from face3d.core import config
    reg = config._REGISTRY
    if not reg:
        bad.append("core.config registry is empty")
    for full, d in sorted(reg.items()):
        if d.badge not in config.BADGES:
            bad.append(f"default {full}: invalid badge {d.badge!r}")
        if not isinstance(d.source, str) or not d.source.strip():
            bad.append(f"default {full}: empty source")
    try:
        config.resolve()
    except ValueError as e:
        bad.append(f"registered defaults do not resolve: {e}")
    return bad


# ---------------------------------------------------------------------------- (d)
def _load_tool(name: str, repo: Path = REPO):
    spec = importlib.util.spec_from_file_location(f"_ci_{name}", Path(repo) / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def check_blender_ext(repo: Path = REPO, ext: str = "blender_ext/face3d_likeness") -> list[str]:
    """(d) Bridge rule, manifest lint (store rules of ``tools/build_extension.validate_manifest``: required
    keys, permanent id, GPL-3.0-or-later, tagline <= 64 characters, no wheels, no network permission) and
    the GPL SPDX header on the first line of every ``.py`` of the extension."""
    bad: list[str] = []
    root = Path(repo) / ext
    files = _py_files(root)
    if not files:
        return [f"{ext}: no python files found"]
    seen_bridge = False
    for p in files:
        text = p.read_text(encoding="utf-8")
        lines = text.splitlines()
        if not lines or lines[0].strip() != GPL_HEADER:
            bad.append(f"{_rel(p, repo)}: first line is not {GPL_HEADER!r}")
        tree = ast.parse(text, filename=str(p))
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        if p.name == "bridge.py" and p.parent == root:
            seen_bridge = True
            continue
        for a in sorted(attrs & set(BRIDGE_ONLY_ATTRS)):
            bad.append(f"{_rel(p, repo)}: uses .{a} (only bridge.py may)")
    if not seen_bridge:
        bad.append(f"{ext}/bridge.py is missing")
    try:
        be = _load_tool("build_extension", repo)
        be.validate_manifest(root / "blender_manifest.toml", store=True)
    except Exception as e:  # noqa: BLE001 - BuildError or a broken tool both fail the lint
        bad.append(f"{ext}/blender_manifest.toml: {e}")
    return bad


# ---------------------------------------------------------------------------- (e)
def _has_geometry(doc) -> bool:
    """True when a parsed JSON document carries landmark or mesh data (a known face3d geometry format,
    or a non-empty value under one of :data:`GEOMETRY_KEYS` anywhere in the document)."""
    if isinstance(doc, dict):
        if doc.get("format") in GEOMETRY_FORMATS:
            return True
        for k, v in doc.items():
            if k in GEOMETRY_KEYS and v not in (None, [], {}, ""):
                return True
            if _has_geometry(v):
                return True
    elif isinstance(doc, list):
        return any(_has_geometry(v) for v in doc[:64])
    return False


def _declared_provenance(doc) -> str | None:
    if isinstance(doc, dict):
        for holder in (doc, doc.get("meta") if isinstance(doc.get("meta"), dict) else {}):
            p = holder.get("provenance")
            if isinstance(p, str):
                return p
            if isinstance(p, dict) and isinstance(p.get("kind"), str):
                return p["kind"]
    return None


def check_fixture_provenance(repo: Path = REPO, tests_dir: str = "tests") -> list[str]:
    """(e) Walk ``tests/`` (code, ``__pycache__`` and the bpy stub excluded): a JSON file with landmark or
    mesh data must declare ``provenance`` (top level or under ``meta``) in :data:`PROVENANCES`; a
    binary geometry / image file must have a sidecar ``<name>.provenance.json`` or a directory
    ``PROVENANCE.json`` declaring it."""
    bad: list[str] = []
    root = Path(repo) / tests_dir
    for p in sorted(root.rglob("*")):
        if not p.is_file() or "__pycache__" in p.parts or "blender_stub" in p.parts:
            continue
        suf = p.suffix.lower()
        if suf in (".py", ".pyc", ".md", ".txt", ".toml", ".cfg", ".ini"):
            continue
        if p.name == "PROVENANCE.json" or p.name.endswith(".provenance.json"):
            continue
        if suf == ".json":
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
            except ValueError as e:
                bad.append(f"{_rel(p, repo)}: unreadable JSON ({e})")
                continue
            prov = _declared_provenance(doc)
            if prov is not None and prov not in PROVENANCES:
                bad.append(f"{_rel(p, repo)}: provenance {prov!r} not in {list(PROVENANCES)}")
            elif prov is None and _has_geometry(doc):
                bad.append(f"{_rel(p, repo)}: landmark/mesh data without a provenance field")
            continue
        if suf in BINARY_SUFFIXES:
            prov = None
            for side in (p.with_name(p.name + ".provenance.json"), p.parent / "PROVENANCE.json"):
                if side.is_file():
                    try:
                        prov = _declared_provenance(json.loads(side.read_text(encoding="utf-8")))
                    except ValueError:
                        prov = None
                    break
            if prov not in PROVENANCES:
                bad.append(f"{_rel(p, repo)}: binary geometry/image fixture without a provenance sidecar "
                           f"in {list(PROVENANCES)}")
            continue
        bad.append(f"{_rel(p, repo)}: unknown fixture type (add it to the provenance check)")
    return bad


# ---------------------------------------------------------------------------- (f)
def synthetic_project(tmp: Path, seed: int = 11, n_views: int = 5, wh: tuple[int, int] = (600, 800)):
    """Write a synthetic project folder under ``tmp`` and return ``(project, landmark_sets, consent)``.

    Subject: :func:`face3d.testbed.surface_subjects.out_of_prior_subject` on the procedural head; rig:
    :func:`face3d.testbed.rigs.rear_phone`; detections: :func:`face3d.testbed.detector_sim.simulate`
    (nominal noise, 5 % outliers, definition bias); working copies: Lambert renders
    (:func:`face3d.testbed.render.render_view`) saved as ``.npy``.  Streams: ``SeedSequence(seed)
    .spawn(3)`` = subject, rig, detector.  Everything is ``provenance: synthetic``; the LandmarkSets are
    returned in memory (BIOMETRIC_GEOMETRY, TTL 0: never written into the project)."""
    import numpy as np
    from face3d.core.policy import ConsentRecord, Scope
    from face3d.core.schema import sha256_file
    from face3d.geometry.camera import focal_35mm_from_px
    from face3d.io.landmarks import Face, LandmarkSet
    from face3d.model.procedural_head import build_procedural_head
    from face3d.model.registry import ANATOMICAL
    from face3d.pipeline.project import Project
    from face3d.testbed import detector_sim, rigs
    from face3d.testbed.render import face_centre, render_view
    from face3d.testbed.surface_subjects import out_of_prior_subject

    W, H = int(wh[0]), int(wh[1])
    kit = build_procedural_head()
    ids = kit.landmark_names("anatomical44")
    kinds = [ANATOMICAL[i].kind for i in ids]
    r_subj, r_rig, r_det = (np.random.default_rng(s) for s in np.random.SeedSequence(int(seed)).spawn(3))
    sub = out_of_prior_subject(kit, r_subj)
    X = sub.landmarks("anatomical44")
    rig = rigs.rear_phone(r_rig, n_views, X=X, target=face_centre(kit), width=W, height=H)
    obs = detector_sim.simulate(X, kinds, rig, r_det)
    root = Path(tmp) / "proj"
    (root / "photos").mkdir(parents=True)
    f35 = float(focal_35mm_from_px(float(rig.f_prior_px[0]), W, H))
    photos, sets = [], {}
    for k, cam in enumerate(rig.cameras):
        pid = "p%02d" % (k + 1)
        rel = f"photos/{pid}.npy"
        view = render_view(sub.V_true, kit, cam)
        np.save(root / rel, (np.clip(view.image, 0, 1) * 255).astype(np.uint8))
        sha = sha256_file(root / rel)
        exif = {"digital_zoom": 1.0, "f35": f35, "lens_model": "back camera", "make": "Apple",
                "model": "iPhone (synthetic)", "orientation": 1, "software": None, "wh": [W, H]}
        photos.append({"exif": exif, "focal_group": f"Apple|iPhone (synthetic)|back camera|{f35:.4g}|{W}|{H}|still",
                       "id": pid, "include": True, "path": rel, "rights_basis": "self_shot", "sha256": sha,
                       "tags": {"expression": "auto", "mirrored": "auto", "neutral_reference": False,
                                "occluders": [], "view": "auto"}, "working_copy": rel})
        uv = obs.uv[k]
        sets[pid] = LandmarkSet("anatomical44", {"backend": "synthetic", "version": "1", "licence": "CC0-1.0",
                                                 "commercial_ok": True, "is_ml": False},
                                {"sha256": sha, "wh": [W, H], "orientation_applied": True, "input_flipped": False,
                                 "coords": "px_corner"}, [Face(1.0, uv, np.isfinite(uv[:, 0]))])
    doc = {"active_solve": None, "consent_id": "c-synth-ci", "decisions": [], "format": "face3d.project",
           "landmark_cache": {"keep": False}, "licence": "user-data (private; not for redistribution)",
           "photos": photos, "pins": [], "provenance": "synthetic", "scale_refs": [], "seed": int(seed),
           "settings": {"population": "unknown", "scale_population_source": "global_size",
                        "sex_prior": "unspecified"},
           "template": {"id": "procedural-head-v1", "topology_sha256": ""}, "version": 1}
    (root / "project.json").write_text(json.dumps(doc))
    prj = Project.load(root / "project.json")
    consent = ConsentRecord(doc["consent_id"], "subject-001", "self", "v1", "ci", "2026-01-01T00:00:00+00:00",
                            None, [], [p.sha256 for p in prj.photos], 30, "owner",
                            Scope.RECONSTRUCT | Scope.TEXTURE, attested_age=30)
    return prj, sets, consent


def check_pipeline_offline(repo: Path = REPO, seed: int = 11) -> list[str]:
    """(f) Full synthetic pipeline run (every stage, texture included) under
    :func:`face3d.core.policy.network_guard`; the guard itself is verified first (a socket connect must
    raise ``PermissionError`` inside it).  The texture reprojection gates are relaxed for this run only
    (the out-of-prior synthetic scene exceeds the bl T2 limits by design; recorded in the run config)."""
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    import socket
    from face3d.core import policy
    from face3d.pipeline import stages as S
    bad: list[str] = []
    tmp = Path(tempfile.mkdtemp(prefix="f3d_ci_"))
    try:
        prj, sets, consent = synthetic_project(tmp, seed)
        cfg = {"texture": {"reproj_median_max_px": 99.0, "reproj_max_max_px": 999.0}}
        with policy.network_guard():
            try:
                socket.create_connection(("192.0.2.1", 9), timeout=0.01)     # TEST-NET-1: never routed
                bad.append("network_guard did not block socket.create_connection")
            except PermissionError:
                pass
            except OSError:
                bad.append("network_guard did not block socket.create_connection")
            try:
                run = S.run_pipeline(prj, "report", landmark_sets=sets, consent=consent, texture=True, config=cfg)
            except PermissionError as e:
                return bad + [f"the pipeline attempted network access: {e}"]
            except Exception as e:  # noqa: BLE001 - any failure of the reference run fails the check
                return bad + [f"synthetic pipeline run failed: {type(e).__name__}: {e}"]
        res = run.result
        if list(run.executed) != list(S.ORDER):
            bad.append(f"stages executed {run.executed} != {list(S.ORDER)}")
        if prj.provenance != "synthetic":
            bad.append("the reference project is not marked provenance 'synthetic'")
        if not res or res.get("format") != S.RESULT_FORMAT or "texture" not in run.outputs:
            bad.append("the synthetic run produced no result / texture")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return bad


# ---------------------------------------------------------------------------- driver
CHECKS: dict[str, Callable[[], list[str]]] = {
    "a_engine_imports": check_engine_imports,
    "b_numpy_neutral": check_numpy_neutral,
    "c_defaults": check_defaults,
    "d_blender_ext": check_blender_ext,
    "e_fixture_provenance": check_fixture_provenance,
    "f_pipeline_offline": check_pipeline_offline,
}


def run_all(only: Sequence[str] | None = None) -> dict[str, list[str]]:
    """Run the checks (all, or those whose key starts with an entry of ``only``): {name: violations}."""
    out = {}
    for name, fn in CHECKS.items():
        if only and not any(name.startswith(o) or name[2:] == o for o in only):
            continue
        out[name] = fn()
    return out


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="face3d CI policy checks (WP-23)")
    ap.add_argument("--only", nargs="*", default=None, help="check names or letters (a..f)")
    args = ap.parse_args(argv)
    results = run_all(args.only)
    failed = 0
    for name, bad in results.items():
        print(f"[{'ok' if not bad else 'FAIL'}] {name}")
        for b in bad:
            print(f"       {b}")
        failed += bool(bad)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
