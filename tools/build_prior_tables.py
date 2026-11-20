#!/usr/bin/env python3
"""Build the packaged landmark prior ``face3d/data/landmark_prior_v1.json``.

Maintainer tool (DESIGN 2.2 layer L9): stdlib + numpy only, never imported by
``face3d``.  It reads the research note data
``research/data/metric-3d-landmark-reference.json`` (topic
*metric-3d-landmark-reference*) and writes the CC0, project-owned prior file
described in DESIGN 3.2 ("Packaged prior") and used by
``face3d.model.landmark_prior.FactorPrior.from_package`` (DESIGN D-04, 4.6).

What is taken from where (nothing is invented here):

* ``ids`` / ``names`` / per-sex ``mean``: tables
  ``mean_landmarks_male_european_young_adult`` and
  ``mean_landmarks_female_european_young_adult`` (44 rows, mm, FH head frame,
  origin mid-tragion, +x subject's left, +y up, +z forward).  The id order is the
  table order: 14 midline ids then the 15 bilateral bases, each ``_L``, ``_R``.
* ``factor_names`` / ``factor_sigma``: tables ``factor_sigmas_male`` and
  ``factor_sigmas_female`` (18 factors; mm per unit loading, ``size`` is a
  fractional CV).
* ``loadings`` (132 x 18, sigma NOT applied, row ``3*i + axis``): the
  ``factors(X)`` rules of ``research/_raw/scripts/build_lm.py`` ported VERBATIM
  below and evaluated on each sex's mean (the research table
  ``factor_loadings`` shows them for the male mean, rounded to 0.01; the
  acceptance test checks the port against it).
* ``residual_total`` / ``residual_asym`` / ``residual_cov``: table
  ``residual_sd`` and ``residual_cov()`` of ``build_lm.py`` ported VERBATIM
  (diagonal total^2; for an L/R pair the off-diagonal block is
  ``diag((total^2 - asym^2) * [-1, 1, 1])`` with ``asym = min(ASYM, total)``).
* ``defaults``: DESIGN D-03, D-04 and 4.6 (kappa 1.5 / 1.0 / 2.5 on al, ac, en x,
  anat R4.4; extra face-depth factor 6 mm, research table
  ``engine_prior_defaults`` row ``tragion_to_face_depth_extra_sd_mm``; tragion
  floor (1.0, 1.5, 2.0) mm, rigid invariance 100 mm / 0.5 rad and the scale prior
  sigma 0.045 are DESIGN 4.6 / D-03 values, badge 🧠 / 🆕, provisional).

The research table ``ancestry_mean_shifts_vs_european`` is deliberately NOT
copied: the engine never conditions on ancestry (anat R7.4, DESIGN D-04).

Output is deterministic: keys sorted, floats rounded to 6 decimals, ``-0.0``
normalised, numeric rows written one per line, UTF-8, ``\\n`` line endings.

Usage::

    python3 tools/build_prior_tables.py [--research PATH] [--out PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
RESEARCH_REL = "research/data/metric-3d-landmark-reference.json"
DEFAULT_RESEARCH = REPO / RESEARCH_REL
DEFAULT_OUT = REPO / "face3d" / "data" / "landmark_prior_v1.json"

# Landmark id order (= research table order; checked against the table at build time).
MID = ["v", "tr", "g", "n", "prn", "sn", "ls", "sto", "li", "sl", "pg", "gn", "me", "op"]
BIL = ["t", "or", "p", "en", "ex", "ps", "pi", "al", "ac", "ch", "zy", "go", "sa", "sba", "eu"]
IDS = MID + [b + s for b in BIL for s in ("_L", "_R")]
IDX = {k: i for i, k in enumerate(IDS)}

MEAN_TABLES = {"M": "mean_landmarks_male_european_young_adult",
               "F": "mean_landmarks_female_european_young_adult"}
SIGMA_TABLES = {"M": "factor_sigmas_male", "F": "factor_sigmas_female"}

# Filled from the research table residual_sd in load_research() before residual_cov() runs.
RES: dict[str, tuple[float, float, float]] = {}
ASYM: dict[str, tuple[float, float, float]] = {}

# DESIGN D-03 / D-04 / 4.6 defaults written into the package (provisional, see module doc).
DEFAULTS = {
    "kappa_unknown": 1.5,          # anat R4.4: unknown population, low-variance measures (🧠)
    "kappa_matched": 1.0,          # anat R4.4: matched population (🧠)
    "kappa_wide": {"value": 2.5,   # anat R4.4: al-al, en-en widths (🧠)
                   "coords": [["al", "x"], ["ac", "x"], ["en", "x"]]},
    "extra_depth": {"sigma_mm": 6.0,  # engine_prior_defaults tragion_to_face_depth_extra_sd_mm (🧠)
                    "exclude": ["t", "sa", "sba", "eu", "op", "v"]},
    "tragion_floor_mm": [1.0, 1.5, 2.0],   # DESIGN 4.6 R_floor (🆕)
    "rigid_invariance": {"translation_mm": 100.0, "rotation_rad": 0.5},  # DESIGN 4.6 (🆕)
    "scale_sigma_log": 0.045,      # DESIGN D-03 / 4.7 population scale prior (🧠)
}

DEFAULTS_PROVENANCE = {
    "kappa_unknown": "anat R4.4; DESIGN D-04, 4.6 (badge 🧠, provisional)",
    "kappa_matched": "anat R4.4; DESIGN 4.6 (badge 🧠, provisional)",
    "kappa_wide": "anat R4.4 (al-al, en-en); DESIGN 4.6 (badge 🧠, provisional)",
    "extra_depth": "research engine_prior_defaults tragion_to_face_depth_extra_sd_mm; DESIGN 4.6 L_d (badge 🧠)",
    "tragion_floor_mm": "DESIGN 4.6 R_floor: tragion definition noise; source has zero variance by frame construction (badge 🆕)",
    "rigid_invariance": "DESIGN 4.6 G Lambda_g G^T: translation sigma 100 mm, rotation sigma 0.5 rad (badge 🆕)",
    "scale_sigma_log": "DESIGN D-03, 4.7: zeta ~ N(0, 0.045^2), the single population size source (badge 🧠)",
}


def sgn(i):
    k = IDS[i]
    return 1.0 if k.endswith("_L") else (-1.0 if k.endswith("_R") else 0.0)


def base(k):
    return k[:-2] if k.endswith(("_L", "_R")) else k


# ---------- factor loadings (per +1 SD, before sigma) ----------
# Ported VERBATIM from research/_raw/scripts/build_lm.py (factors).
def factors(X):
    n = len(IDS)
    F = {}

    def new():
        return np.zeros((n, 3))

    # 1 isometric size about the tragion-midpoint origin (sigma = CV)
    F["size"] = X.copy()
    # 2 lower-face height (long vs short face), per 100 mm below nasion
    L = new(); yn = X[IDX["n"], 1]
    face = {"prn", "sn", "ls", "sto", "li", "sl", "pg", "gn", "me", "al", "ac", "ch"}
    for i, k in enumerate(IDS):
        b = base(k)
        if b in face:
            dyf = (yn - X[i, 1]) / 100.0
            L[i, 1] = -dyf
            if b in {"pg", "gn", "me", "sl"}:
                L[i, 2] = -0.15 * dyf
        if b == "go":
            L[i, 1] = -0.5 * (yn - X[i, 1]) / 100.0
    F["lower_face_height"] = L
    # 3 facial depth relative to the ears (whole face forward/back)
    L = new()
    for i, k in enumerate(IDS):
        b = base(k)
        if b in {"t", "sa", "sba", "eu", "op", "v"}:
            continue
        L[i, 2] = float(np.clip(X[i, 2] / 100.0, 0, 1.25))
    F["face_depth"] = L
    # 4 mandibular projection
    L = new()
    w = {"pg": 1.0, "gn": 1.0, "me": 1.0, "sl": 0.9, "li": 0.6, "sto": 0.3, "ch": 0.2}
    for i, k in enumerate(IDS):
        if base(k) in w:
            L[i, 2] = w[base(k)]
    F["mandible_projection"] = L
    # 5 bizygomatic / bigonial / bitragal width
    L = new()
    w = {"zy": 1.0, "go": 0.8, "t": 1.0, "eu": 0.6, "sa": 1.0, "sba": 1.0, "ex": 0.35, "p": 0.2, "or": 0.3, "ch": 0.15}
    for i, k in enumerate(IDS):
        if base(k) in w:
            L[i, 0] = sgn(i) * w[base(k)]
    F["face_width"] = L
    # 6 nasal projection / size
    L = new()
    L[IDX["prn"]] = (0, -0.25, 1.0)
    L[IDX["sn"], 2] = 0.15
    L[IDX["n"], 2] = 0.3
    for s in ("_L", "_R"):
        L[IDX["al" + s]] = (sgn(IDX["al" + s]) * 0.3, 0, 0.4)
        L[IDX["ac" + s], 0] = sgn(IDX["ac" + s]) * 0.25
    F["nose_projection"] = L
    # 7 nasal width
    L = new()
    for s in ("_L", "_R"):
        L[IDX["al" + s], 0] = sgn(IDX["al" + s]) * 1.0
        L[IDX["ac" + s], 0] = sgn(IDX["ac" + s]) * 0.9
    F["nose_width"] = L
    # 8 interorbital spacing
    L = new()
    w = {"en": 1.0, "p": 0.9, "ps": 0.8, "pi": 0.8, "ex": 0.6, "or": 0.6}
    for i, k in enumerate(IDS):
        if base(k) in w:
            L[i, 0] = sgn(i) * w[base(k)]
    F["interorbital"] = L
    # 9 lip fullness / protrusion
    L = new()
    L[IDX["ls"]] = (0, 0.0, 1.0)
    L[IDX["li"]] = (0, 0.0, 1.0)
    L[IDX["sto"], 2] = 0.7
    for s in ("_L", "_R"):
        L[IDX["ch" + s], 2] = 0.3
    F["lips"] = L
    # 10 mouth width
    L = new()
    for s in ("_L", "_R"):
        L[IDX["ch" + s], 0] = sgn(IDX["ch" + s])
    F["mouth_width"] = L
    # 11 cephalic index (broad-short vs narrow-long vault)
    L = new()
    for s in ("_L", "_R"):
        L[IDX["eu" + s], 0] = sgn(IDX["eu" + s])
    L[IDX["op"], 2] = 1.5
    L[IDX["v"], 1] = 0.3
    F["cephalic_index"] = L
    # 12 brow / glabella projection
    L = new()
    L[IDX["g"], 2] = 1.0
    L[IDX["n"], 2] = 0.4
    L[IDX["tr"], 2] = 0.4
    F["brow_projection"] = L
    # 13 upper-face height (nasion/eyes above FH)
    L = new()
    w = {"n": 1.0, "g": 1.0, "tr": 1.0, "en": 0.5, "ex": 0.5, "p": 0.5, "ps": 0.5, "pi": 0.5}
    for i, k in enumerate(IDS):
        if base(k) in w:
            L[i, 1] = w[base(k)]
    F["upper_face_height"] = L
    # 14 ear length
    L = new()
    for s in ("_L", "_R"):
        L[IDX["sa" + s], 1] = 1.0
        L[IDX["sba" + s], 1] = -1.0
    F["ear_length"] = L
    # 15 ear protrusion
    L = new()
    for s in ("_L", "_R"):
        L[IDX["sa" + s], 0] = sgn(IDX["sa" + s])
        L[IDX["sba" + s], 0] = sgn(IDX["sba" + s]) * 0.6
    F["ear_protrusion"] = L
    # 16 soft-tissue / adiposity
    L = new()
    for s in ("_L", "_R"):
        L[IDX["go" + s], 0] = sgn(IDX["go" + s]) * 1.0
        L[IDX["zy" + s], 0] = sgn(IDX["zy" + s]) * 0.5
        L[IDX["ch" + s], 0] = sgn(IDX["ch" + s]) * 0.2
    L[IDX["me"], 1] = -0.5
    L[IDX["gn"], 1] = -0.3
    F["soft_tissue"] = L
    # 17 eye opening
    L = new()
    for s in ("_L", "_R"):
        L[IDX["ps" + s], 1] = 1.0
        L[IDX["pi" + s], 1] = -0.4
    F["eye_opening"] = L
    # 18 vault height
    L = new()
    L[IDX["v"], 1] = 1.0
    L[IDX["tr"], 1] = 0.5
    for s in ("_L", "_R"):
        L[IDX["eu" + s], 1] = 0.5
    F["vault_height"] = L
    return F


# Ported VERBATIM from research/_raw/scripts/build_lm.py (residual_cov); RES and ASYM
# are filled from the research table residual_sd instead of being typed in.
def residual_cov():
    n = len(IDS)
    D = np.zeros((3 * n, 3 * n))
    for i, k in enumerate(IDS):
        b = base(k)
        tot = np.array(RES[b], float)
        if b in MID:
            D[3 * i:3 * i + 3, 3 * i:3 * i + 3] = np.diag(tot ** 2)
            continue
        asy = np.minimum(np.array(ASYM[b], float), tot)
        sym2 = tot ** 2 - asy ** 2
        D[3 * i:3 * i + 3, 3 * i:3 * i + 3] = np.diag(tot ** 2)
        if k.endswith("_L"):
            j = IDX[b + "_R"]
            # symmetric component: mirrored x (anti-correlated), equal y and z
            c = np.diag(sym2 * np.array([-1.0, 1.0, 1.0]))
            D[3 * i:3 * i + 3, 3 * j:3 * j + 3] = c
            D[3 * j:3 * j + 3, 3 * i:3 * i + 3] = c
    return D


# ----------------------------------------------------------------- research input
def _tables(research: dict) -> dict:
    return {t["name"]: t for t in research["tables"]}


def load_research(path: Path) -> tuple[dict, bytes]:
    """Parse the research JSON; fill RES / ASYM from table residual_sd."""
    raw = Path(path).read_bytes()
    research = json.loads(raw.decode("utf-8"))
    T = _tables(research)
    RES.clear()
    ASYM.clear()
    for row in T["residual_sd"]["rows"]:
        b = row[0]
        RES[b] = (float(row[1]), float(row[2]), float(row[3]))
        if b in BIL:
            if any(v is None for v in row[4:7]):
                raise ValueError(f"residual_sd: bilateral landmark {b!r} has no asym SD")
            ASYM[b] = (float(row[4]), float(row[5]), float(row[6]))
    missing = [b for b in MID + BIL if b not in RES]
    if missing:
        raise ValueError(f"residual_sd lacks rows for {missing}")
    return research, raw


def mean_table(T: dict, sex: str) -> tuple[list[str], list[str], np.ndarray]:
    rows = T[MEAN_TABLES[sex]]["rows"]
    ids = [r[0] for r in rows]
    names = [r[1] for r in rows]
    X = np.array([[float(r[2]), float(r[3]), float(r[4])] for r in rows])
    if ids != IDS:
        raise ValueError(f"{MEAN_TABLES[sex]}: id order {ids} differs from the expected 44-id order {IDS}")
    return ids, names, X


def sigma_table(T: dict, sex: str) -> tuple[list[str], np.ndarray]:
    rows = T[SIGMA_TABLES[sex]]["rows"]
    return [r[0] for r in rows], np.array([float(r[1]) for r in rows])


def loading_matrix(X: np.ndarray, names: list[str]) -> np.ndarray:
    """(3n, K) loadings, row 3*i + axis, column k = factor names[k] (sigma not applied)."""
    F = factors(X)
    if list(F) != list(names):
        raise ValueError(f"factor order {list(F)} differs from the research sigma table {names}")
    return np.stack([F[k].reshape(-1) for k in names], axis=1)


def build(research_path: Path = DEFAULT_RESEARCH, source_rel: str = RESEARCH_REL) -> dict:
    """Return the packaged-prior document (plain Python containers)."""
    research, raw = load_research(research_path)
    T = _tables(research)
    sexes = {}
    names_ref = None
    factor_names = None
    for sex in ("M", "F"):
        ids, names, X = mean_table(T, sex)
        if names_ref is None:
            names_ref = names
        elif names != names_ref:
            raise ValueError("male and female mean tables disagree on landmark names")
        fnames, sig = sigma_table(T, sex)
        if factor_names is None:
            factor_names = fnames
        elif fnames != factor_names:
            raise ValueError("male and female factor sigma tables disagree on factor names")
        Lo = loading_matrix(X, factor_names)
        sexes[sex] = {"mean": X.tolist(), "factor_sigma": sig.tolist(), "loadings": Lo.tolist()}
    D = residual_cov()
    total = np.array([RES[base(k)] for k in IDS], float)
    asym = np.array([np.minimum(np.array(ASYM[base(k)], float), np.array(RES[base(k)], float))
                     if base(k) in BIL else (0.0, 0.0, 0.0) for k in IDS], float)
    return {
        "format": "face3d.landmark_prior",
        "version": 1,
        "licence": "CC0-1.0",
        "status": "expert prior (knowledge); not published coordinates",
        "badge": "\U0001F9E0",
        "source": {"path": source_rel, "sha256": hashlib.sha256(raw).hexdigest(),
                   "tables": [MEAN_TABLES["M"], MEAN_TABLES["F"], SIGMA_TABLES["M"], SIGMA_TABLES["F"],
                              "factor_loadings (rules ported from research/_raw/scripts/build_lm.py)",
                              "residual_sd"]},
        "calibration_note": ("Expert synthesis calibrated to Farkas/ANSUR-type chord norms of young adults "
                             "of one reference population; unknown-population use inflates the covariance "
                             "by kappa (anat R4.4). Never conditioned on the subject's population (anat R7.4)."),
        "frame": "FH; origin mid-tragion; +x subject left, +y up, +z forward; mm",
        "ids": list(IDS),
        "names": list(names_ref),
        "factor_names": list(factor_names),
        "sexes": sexes,
        "residual_cov": D.tolist(),
        "residual_total": total.tolist(),
        "residual_asym": asym.tolist(),
        "residual_note": ("residual_asym is 0 for midline ids (no pair); residual_cov = diag(total^2) with "
                          "L/R off-diagonal blocks diag((total^2 - asym^2) * [-1, 1, 1])"),
        "loadings_note": "rows 3*i + axis (x, y, z); columns follow factor_names; sigma NOT applied; size column = mean (CV units)",
        "defaults": DEFAULTS,
        "defaults_provenance": DEFAULTS_PROVENANCE,
    }


# ----------------------------------------------------------------- deterministic JSON
def _scalar(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if isinstance(v, (float, np.floating)):
        x = round(float(v), 6)
        if not math.isfinite(x):
            raise ValueError("non-finite float in prior table")
        if x == 0.0:
            x = 0.0  # normalise -0.0
        return repr(x)
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    raise TypeError(f"unsupported value {type(v)!r}")


def _is_scalar(v) -> bool:
    return not isinstance(v, (dict, list, tuple))


def dumps(obj, indent: int = 0) -> str:
    """Deterministic JSON: sorted keys, 6-decimal floats, scalar lists on one line."""
    pad = " " * indent
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        items = [f'{pad} {json.dumps(str(k), ensure_ascii=False)}: {dumps(obj[k], indent + 1)}'
                 for k in sorted(obj)]
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"
    if isinstance(obj, (list, tuple)):
        if all(_is_scalar(v) for v in obj):
            return "[" + ", ".join(_scalar(v) for v in obj) + "]"
        items = [pad + " " + dumps(v, indent + 1) for v in obj]
        return "[\n" + ",\n".join(items) + "\n" + pad + "]"
    return _scalar(obj)


def write(doc: dict, out: Path) -> bytes:
    data = (dumps(doc) + "\n").encode("utf-8")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return data


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--research", type=Path, default=DEFAULT_RESEARCH,
                    help=f"research JSON (default {RESEARCH_REL})")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT,
                    help="output JSON (default face3d/data/landmark_prior_v1.json)")
    args = ap.parse_args(argv)
    doc = build(args.research)
    data = write(doc, args.out)
    print(f"wrote {args.out} ({len(data)} bytes, sha256 {hashlib.sha256(data).hexdigest()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
