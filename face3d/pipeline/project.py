"""Project file ``face3d.project`` v1 (DESIGN 3.2 "Project", 2.1 invariant 5, 3.3).

A :class:`Project` mirrors ``<name>.face3d/project.json``.  It holds *references*
(paths, SHA-256 hashes) and user decisions; it never holds pixels, landmarks or
meshes.  Conventions: image coordinates are continuous pixels with the origin at the
top-left corner (DESIGN 3.1); lengths are millimetres; timestamps are ISO-8601 UTC
strings; hashes are lowercase hex SHA-256.

Rules enforced here (fail closed, DESIGN 3.3 / eth F7 / D-10):

* ``rights_basis`` must be one of :data:`face3d.core.policy.RIGHTS_BASES`.
* ``settings.sex_prior`` is an optional *consented input*: ``unspecified`` (default),
  ``male`` or ``female``; it is never inferred by the engine.  ``settings.population``
  is ``unknown`` or ``matched`` (a user statement that the population size prior
  matches the subject); it is never stored as ancestry.
* Landmarks are BIOMETRIC_GEOMETRY with TTL 0: ``landmark_cache.keep`` is ``False``
  unless the user opts in explicitly (the pipeline then writes copies under
  ``<project>/landmarks/`` and logs the opt-in).
* A mirror flip is applied only for a photo with a recorded user decision
  (:meth:`Project.record_decision`; D-10: never silent flips).
"""
from __future__ import annotations

import os
import struct
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from face3d.core.audit import AuditLog
from face3d.core.policy import RIGHTS_BASES, DataClass
from face3d.core.schema import FormatError, dump_json, load_json, sha256_file
from face3d.io import exif as _exif
from face3d.solve.noise import PIN_CLASSES
from face3d.io import heif as _heif

FORMAT = "face3d.project"
VERSION = 1
LICENCE = "user-data (private; not for redistribution)"
DEFAULT_TEMPLATE_ID = "procedural-head-v1"
SEX_PRIORS = ("unspecified", "male", "female")
POPULATIONS = ("unknown", "matched")
#: decision kinds this version understands (DESIGN 3.2 ``decisions``).
DECISION_KINDS = ("mirror_flip", "mirror_keep", "include", "exclude")
DECISION_BY = ("user", "cli")
#: pin ``expertise`` values (DESIGN 3.2 / 4.4: changes only the crisp-pin sigma, 1.2 vs 0.8 mm)
PIN_EXPERTISE = ("novice", "expert")
#: legacy ``cls`` spellings that mean a crisp pin of that expertise
_LEGACY_CRISP = {"novice": "crisp_novice", "expert": "crisp_expert"}


def resolve_pin_class(cls: str, expertise: str = "novice") -> str:
    """Noise-model pin class (:data:`face3d.solve.noise.PIN_CLASSES`) of a pin (DESIGN 4.4, D-09).

    ``cls='crisp'`` takes its class from ``expertise`` (``crisp_novice`` / ``crisp_expert``); the other
    :data:`PIN_CLASSES` names are used as they are (``expertise`` does not change them); the legacy
    spellings ``'novice'`` / ``'expert'`` of ``cls`` mean the crisp pin of that name.  Anything else is
    a :class:`ProjectError`."""
    if expertise not in PIN_EXPERTISE:
        raise ProjectError(f"pin expertise must be one of {PIN_EXPERTISE}")
    if cls == "crisp":
        return "crisp_" + expertise
    if cls in PIN_CLASSES:
        return cls
    if cls in _LEGACY_CRISP:
        return _LEGACY_CRISP[cls]
    raise ProjectError(f"unknown pin class {cls!r}")
INCLUDE_VALUES = ("auto", True, False)
_HEIF_EXT = (".heic", ".heif", ".avif")


class ProjectError(ValueError):
    """Raised for an invalid project file or an invalid edit."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class PhotoRecord:
    """One photo of the project (DESIGN 3.2).  ``working_copy`` is a ``.npy``/``.png``
    path relative to the project folder (EXIF-stripped, orientation baked)."""

    id: str
    path: str
    sha256: str
    rights_basis: str
    working_copy: str | None = None
    exif: dict = field(default_factory=dict)
    tags: dict = field(default_factory=lambda: {
        "view": "auto", "expression": "auto", "occluders": [], "mirrored": "auto",
        "neutral_reference": False})
    include: Any = "auto"
    focal_group: str | None = None

    def validate(self) -> None:
        if not self.id or any(c in self.id for c in "/\\"):
            raise ProjectError(f"invalid photo id {self.id!r}")
        if self.rights_basis not in RIGHTS_BASES:
            raise ProjectError(f"rights_basis {self.rights_basis!r} not in {sorted(RIGHTS_BASES)} (F7)")
        if not (self.include == "auto" or isinstance(self.include, bool)):
            raise ProjectError(f"include must be 'auto', true or false, got {self.include!r}")
        if len(self.sha256) != 64:
            raise ProjectError("photo sha256 must be 64 hex chars")


@dataclass
class Pin:
    """A user pin: landmark ``target`` of ``photo`` at ``xy_px`` (DESIGN 3.2, 4.4, D-09)."""

    photo: str
    landmark: str
    xy_px: tuple
    cls: str = "crisp"
    expertise: str = "novice"
    zoom: float = 1.0

    def validate(self) -> None:
        resolve_pin_class(self.cls, self.expertise)
        if not (float(self.zoom) > 0):
            raise ProjectError("pin zoom must be > 0")

    def to_json(self) -> dict:
        return {"photo": self.photo, "target": {"landmark": self.landmark},
                "xy_px": [float(self.xy_px[0]), float(self.xy_px[1])], "cls": self.cls,
                "expertise": self.expertise, "zoom": float(self.zoom)}

    @classmethod
    def from_json(cls, d: dict) -> "Pin":
        xy = d["xy_px"]
        return cls(photo=str(d["photo"]), landmark=str(d["target"]["landmark"]),
                   xy_px=(float(xy[0]), float(xy[1])), cls=str(d.get("cls", "crisp")),
                   expertise=str(d.get("expertise", "novice")), zoom=float(d.get("zoom", 1.0)))


@dataclass
class Project:
    """The DESIGN 3.2 project document (see module docstring)."""

    seed: int = 1234
    consent_id: str = ""
    template: dict = field(default_factory=lambda: {"id": DEFAULT_TEMPLATE_ID, "topology_sha256": ""})
    settings: dict = field(default_factory=lambda: {
        "sex_prior": "unspecified", "population": "unknown",
        "scale_population_source": "global_size"})
    photos: list = field(default_factory=list)
    pins: list = field(default_factory=list)
    scale_refs: list = field(default_factory=list)
    decisions: list = field(default_factory=list)
    active_solve: str | None = None
    landmark_cache: dict = field(default_factory=lambda: {"keep": False})
    #: optional data provenance label (e.g. ``'synthetic'`` for generated golden projects)
    provenance: str | None = None
    #: file the project was loaded from / saved to (not serialised)
    path: Path | None = field(default=None, repr=False, compare=False)

    # ------------------------------------------------------------------ helpers
    @property
    def root(self) -> Path:
        """Project folder (the folder holding ``project.json``)."""
        if self.path is None:
            raise ProjectError("project has no path yet (save() it first)")
        return Path(self.path).parent

    def photo(self, pid: str) -> PhotoRecord:
        for p in self.photos:
            if p.id == pid:
                return p
        raise KeyError(f"no photo {pid!r}")

    def resolve(self, rel: str | None) -> Path | None:
        """Absolute path of a project-relative (or absolute) path."""
        if rel is None:
            return None
        p = Path(rel)
        return p if p.is_absolute() else self.root / p

    @property
    def keep_landmarks(self) -> bool:
        return bool(self.landmark_cache.get("keep", False))

    def audit_log(self) -> AuditLog:
        return AuditLog(self.root / "audit.jsonl")

    # ------------------------------------------------------------------ validation
    def validate(self) -> None:
        s = self.settings
        if s.get("sex_prior", "unspecified") not in SEX_PRIORS:
            raise ProjectError(f"settings.sex_prior must be one of {SEX_PRIORS} (never inferred)")
        if s.get("population", "unknown") not in POPULATIONS:
            raise ProjectError(f"settings.population must be one of {POPULATIONS} (never stored as ancestry)")
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise ProjectError("seed must be an int")
        ids = [p.id for p in self.photos]
        if len(set(ids)) != len(ids):
            raise ProjectError("duplicate photo ids")
        for p in self.photos:
            p.validate()
        for pin in self.pins:
            if pin.photo not in ids:
                raise ProjectError(f"pin refers to unknown photo {pin.photo!r}")
            pin.validate()
        for d in self.decisions:
            if d.get("photo") not in ids:
                raise ProjectError(f"decision refers to unknown photo {d.get('photo')!r}")
            if d.get("kind") not in DECISION_KINDS or d.get("by") not in DECISION_BY:
                raise ProjectError(f"invalid decision {d!r}")
        if not isinstance(self.landmark_cache, dict) or \
                not isinstance(self.landmark_cache.get("keep", False), bool):
            raise ProjectError("landmark_cache.keep must be a bool")

    # ------------------------------------------------------------------ (de)serialisation
    def to_json(self) -> dict:
        self.validate()
        return {
            "format": FORMAT, "version": VERSION, "licence": LICENCE,
            "seed": int(self.seed), "consent_id": self.consent_id,
            "template": dict(self.template), "settings": dict(self.settings),
            "photos": [asdict(p) for p in self.photos],
            "pins": [p.to_json() for p in self.pins],
            "scale_refs": [dict(r) for r in self.scale_refs],
            "decisions": [dict(d) for d in self.decisions],
            "active_solve": self.active_solve,
            "landmark_cache": dict(self.landmark_cache),
            **({"provenance": self.provenance} if self.provenance else {}),
        }

    @classmethod
    def from_json(cls, d: dict) -> "Project":
        if d.get("format") != FORMAT:
            raise FormatError(f"expected format {FORMAT!r}")
        photos = []
        for p in d.get("photos", []):
            kw = {k: p[k] for k in PhotoRecord.__dataclass_fields__ if k in p}
            photos.append(PhotoRecord(**kw))
        prj = cls(seed=int(d.get("seed", 1234)), consent_id=str(d.get("consent_id", "")),
                  template=dict(d.get("template", {"id": DEFAULT_TEMPLATE_ID, "topology_sha256": ""})),
                  settings={**{"sex_prior": "unspecified", "population": "unknown",
                               "scale_population_source": "global_size"}, **dict(d.get("settings", {}))},
                  photos=photos, pins=[Pin.from_json(x) for x in d.get("pins", [])],
                  scale_refs=[dict(r) for r in d.get("scale_refs", [])],
                  decisions=[dict(x) for x in d.get("decisions", [])],
                  active_solve=d.get("active_solve"),
                  landmark_cache={"keep": False, **dict(d.get("landmark_cache", {}))},
                  provenance=d.get("provenance"))
        prj.validate()
        return prj

    def save(self, path: str | Path | None = None) -> Path:
        """Write ``project.json`` atomically (tmp then ``os.replace``); returns the path."""
        if path is not None:
            p = Path(path)
            self.path = p / "project.json" if p.is_dir() or p.suffix == "" else p
        if self.path is None:
            raise ProjectError("save() needs a path")
        self.path = Path(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        dump_json(self.to_json(), tmp)
        os.replace(tmp, self.path)
        return self.path

    @classmethod
    def load(cls, path: str | Path) -> "Project":
        p = Path(path)
        if p.is_dir():
            p = p / "project.json"
        prj = cls.from_json(load_json(p, expect_format=FORMAT, max_version=VERSION))
        prj.path = p
        return prj

    # ------------------------------------------------------------------ edits
    def add_photo(self, path: str | Path, rights_basis: str, *, working_copy: str | None = None,
                  photo_id: str | None = None, tags: dict | None = None) -> PhotoRecord:
        """Register a photo: SHA-256, EXIF (JPEG/TIFF via :mod:`face3d.io.exif`, HEIF via
        :mod:`face3d.io.heif`) and the focal-group key.  Pixels are not decoded (DESIGN 2.5);
        ``working_copy`` is a caller-supplied ``.npy``/``.png`` (orientation baked)."""
        if rights_basis not in RIGHTS_BASES:
            raise ProjectError(f"rights_basis {rights_basis!r} not in {sorted(RIGHTS_BASES)} (F7)")
        src = Path(path)
        if not src.is_file():
            raise ProjectError("photo file not found")
        sha = sha256_file(src)
        if any(p.sha256 == sha for p in self.photos):
            raise ProjectError("photo already in the project")
        info, wh = _read_photo_meta(src)
        pid = photo_id or f"p{len(self.photos) + 1:02d}"
        if any(p.id == pid for p in self.photos):
            raise ProjectError(f"duplicate photo id {pid!r}")
        key = info.focal_group_key(wh[0], wh[1]) if wh and info.focal_35mm else None
        try:
            rel = os.path.relpath(src, self.root) if self.path is not None else str(src)
        except ValueError:                                            # different drive (Windows)
            rel = str(src)
        rec = PhotoRecord(id=pid, path=rel, sha256=sha, rights_basis=rights_basis,
                          working_copy=working_copy, exif=exif_summary(info, wh),
                          focal_group=key)
        if tags:
            rec.tags.update(tags)
        rec.validate()
        self.photos.append(rec)
        return rec

    def record_decision(self, kind: str, photo: str, by: str, *, audit: AuditLog | None = None) -> dict:
        """Append a user decision and write an audit entry (hash + code only, eth F19)."""
        if kind not in DECISION_KINDS:
            raise ProjectError(f"unknown decision kind {kind!r}")
        if by not in DECISION_BY:
            raise ProjectError(f"decision 'by' must be one of {DECISION_BY}")
        rec = self.photo(photo)
        d = {"kind": kind, "photo": photo, "by": by, "time": _now_iso()}
        self.decisions.append(d)
        log = audit
        if log is None and self.path is not None:
            log = self.audit_log()
        if log is not None:
            log.write("decision_" + kind, DataClass.BIOMETRIC_GEOMETRY, rec.sha256,
                      scope="RECONSTRUCT", detail_code="by_" + by)
        return d

    def purge_kept_landmarks(self) -> int:
        """Delete ``<project>/landmarks/*.json`` (TTL 0 after an opt-out, D-25 / eth 2.2), one audit
        entry per file; returns how many were removed.  A project without a path has nothing on disk."""
        if self.path is None:
            return 0
        d = self.root / "landmarks"
        n = 0
        if d.is_dir():
            by_id = {p.id: p for p in self.photos}
            for f in sorted(d.glob("*.json")):
                f.unlink()
                n += 1
                rec = by_id.get(f.stem)
                self.audit_log().write("landmarks_purged", DataClass.BIOMETRIC_GEOMETRY,
                                       rec.sha256 if rec else "0" * 64, scope="RECONSTRUCT",
                                       detail_code="keep_opt_out")
            try:
                d.rmdir()
            except OSError:
                pass
        return n

    def set_landmark_keep(self, keep: bool) -> None:
        """Set ``landmark_cache.keep``; turning it off purges what was kept (and logs it)."""
        self.landmark_cache = {**self.landmark_cache, "keep": bool(keep)}
        if not keep:
            self.purge_kept_landmarks()

    def mirror_state(self, photo: str) -> str | None:
        """``'flip'`` / ``'keep'`` from the *latest* mirror decision of ``photo`` (decisions are
        chronological), or None when there is none (D-10: explicit, logged and reversible)."""
        for d in reversed(self.decisions):
            if d["photo"] == photo and d["kind"] in ("mirror_flip", "mirror_keep"):
                return "flip" if d["kind"] == "mirror_flip" else "keep"
        return None

    def flipped_photos(self) -> list:
        """Sorted ids of photos whose latest mirror decision is a flip."""
        return sorted(p.id for p in self.photos if self.mirror_state(p.id) == "flip")

    def decision_for(self, kind: str, photo: str) -> dict | None:
        for d in reversed(self.decisions):
            if d["kind"] == kind and d["photo"] == photo:
                return d
        return None


def exif_summary(info: _exif.ExifInfo, wh) -> dict:
    """DESIGN 3.2 ``exif`` block (f35, lens_model, software, digital_zoom, orientation, wh) plus
    the other fields the focal ladder and QA gates read (all plain JSON)."""
    d = {"f35": info.focal_35mm, "lens_model": info.lens_model, "software": info.software,
         "digital_zoom": info.digital_zoom_ratio, "orientation": int(info.orientation or 1),
         "wh": [int(wh[0]), int(wh[1])] if wh else None,
         "make": info.make, "model": info.model, "focal_length_mm": info.focal_length_mm,
         "datetime_original": info.datetime_original, "custom_rendered": info.custom_rendered,
         "subject_distance_m": info.subject_distance_m,
         "focal_plane_x_res": info.focal_plane_x_res, "focal_plane_res_unit": info.focal_plane_res_unit,
         "native_wh": [info.width, info.height] if info.width and info.height else None,
         "artist": info.artist, "copyright": info.copyright}
    return d


def exif_from_summary(d: dict) -> _exif.ExifInfo:
    """Inverse of :func:`exif_summary` (an ``ExifInfo`` for the QA gates and focal ladder)."""
    d = d or {}
    nw = d.get("native_wh") or (None, None)
    return _exif.ExifInfo(
        focal_length_mm=d.get("focal_length_mm"), focal_35mm=d.get("f35"), width=nw[0], height=nw[1],
        orientation=int(d.get("orientation") or 1), make=d.get("make"), model=d.get("model"),
        lens_model=d.get("lens_model"), focal_plane_x_res=d.get("focal_plane_x_res"),
        focal_plane_res_unit=d.get("focal_plane_res_unit"), datetime_original=d.get("datetime_original"),
        software=d.get("software"), digital_zoom_ratio=d.get("digital_zoom"),
        subject_distance_m=d.get("subject_distance_m"), custom_rendered=d.get("custom_rendered"),
        artist=d.get("artist"), copyright=d.get("copyright"))


def _png_size(data: bytes):
    if data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
        return struct.unpack(">II", data[16:24])
    return None


def _read_photo_meta(src: Path):
    """(ExifInfo, (W, H) | None) of a photo without decoding pixels."""
    ext = src.suffix.lower()
    with open(src, "rb") as fh:
        head = fh.read(64)
    if ext in _HEIF_EXT:
        h = _heif.parse_heif(src)
        info = _exif.read_exif_bytes(h.exif_bytes) if h.exif_bytes else _exif.ExifInfo()
        wh = (h.width, h.height) if h.width and h.height else None
        if wh and h.irot in (90, 270):
            wh = (wh[1], wh[0])                                      # HEIF: irot replaces EXIF orientation
        info.orientation = 1
        return info, wh
    if ext == ".npy":
        arr = np.load(src, mmap_mode="r", allow_pickle=False)
        return _exif.ExifInfo(), (int(arr.shape[1]), int(arr.shape[0]))
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        wh = _png_size(head)
        return _exif.ExifInfo(), (int(wh[0]), int(wh[1])) if wh else None
    info = _exif.read_exif(src)
    wh = (info.width, info.height) if info.width and info.height else None
    if wh and info.orientation in (5, 6, 7, 8):
        wh = (wh[1], wh[0])
    return info, wh


__all__ = ["Project", "PhotoRecord", "Pin", "ProjectError", "exif_summary", "exif_from_summary",
           "FORMAT", "VERSION", "DECISION_KINDS"]
