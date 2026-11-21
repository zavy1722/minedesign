#!/usr/bin/env python3
"""Recalibrate the landmark prior from user-supplied data: ANSUR II CSV or 3D landmark samples.

Maintainer tool (DESIGN 2.2 layer L9, D-03, D-04, 4.6, 8 M7; WP-14, run offline
by WP-24).  Stdlib + numpy + ``face3d``; never imported by ``face3d``.  The
input files are supplied by the maintainer and are **never bundled or
committed**; only the derived prior (aggregate statistics) is written.

Two modes (exactly one):

**(a) ``--ansur CSV``** -- the public ANSUR II CSV (one file per sex or both
sexes in one file; several ``--ansur`` files are concatenated).

* Columns follow the research table ``ansur2_head_columns``
  (*metric-3d-landmark-reference*): ``Gender``, ``DODRace`` and the head
  measures.  The seven measures mapped to prior chords (:data:`ANSUR_TARGETS`,
  WP-14 spec) are required: headlength -> g-op, headbreadth -> eu_L-eu_R,
  bizygomaticbreadth -> zy_L-zy_R, mentonsellionlength -> n-me (sellion
  approximated by n), interpupillarybreadth -> p_L-p_R, earlength -> sa_L-sba_L,
  tragiontopofhead -> v.y (height of v above the tragion midpoint in the FH
  frame).  Other listed measures present in the file are summarised too.
* Unit plausibility (the research note says "verify per-column unit scaling"):
  the median of each used column must lie in its plausible range -- headlength
  150..250 mm (WP-14 spec), every other column 0.75 x the lowest to 1.25 x the
  highest research mean range (🆕 margins).  An implausible column is tried
  divided by 10 (stored in 0.1 mm) and refused if still implausible.
* Statistics **by Gender only**, pooled across the file's DODRace groups with
  **equal weight per group** (balanced pooling, anat R5.5):
  ``mu = mean_g mu_g``, ``Sigma = mean_g [Sigma_g + (mu_g - mu)(mu_g - mu)^T]``.
  Groups with fewer than ``--min-group-n`` (30, 🆕) complete rows are left out
  of the pooling.  **No group-conditioned statistic or prior is ever written**
  (anat R7.4): the output holds pooled per-sex means, SDs and correlations and
  only the number of groups pooled.
* The per-sex pooled SDs replace the target SDs of the mapped chords in the
  factor-sigma calibration ported from ``research/_raw/scripts/build_lm.py``
  (``calibrate``: weighted NNLS on squared chord SDs with a ridge (lambda 0.15)
  toward the initial guesses ``SIG0``, floor 0.5 x guess except ``size``); the
  other targets (``TARGETS``, ``SD_ONLY``, ``FUNC``) are the ported research
  values.  Means, loadings and the residual covariance are **kept** from the
  base prior (the packaged v1 by default), so only ``factor_sigma`` changes.
* ``scale_sigma_log`` is proposed as the mean over the sexes of the mean
  balanced log-SD of head length, head breadth and face height
  (menton-sellion) (WP-14 spec; DESIGN D-03, 4.7).

**(b) ``--landmark-samples NPZ``** -- an array ``samples`` (S, 44, 3) in the FH
frame (mm; origin mid-tragion; +x subject's left), e.g. computed by the user
from FLAME 2023 Open (CC BY 4.0: ``--attribution`` is required), optional
``ids`` (44,) to check the order and optional ``sex`` (S,) of 'M' / 'F'.  The
empirical mean and covariance are fitted per sex (or once, shared by both,
without ``sex``) by a low-rank + diagonal factor model with K = 18 factors
(``--factors``) by **iterated principal factors** (principal-axis factoring of
the correlation matrix: eigen-decomposition of ``Rc - diag(psi)``, uniquenesses
updated until stable; residual SD floored at 0.3 mm on the mm scale, WP-14 spec;
see :func:`principal_factors`).  Coordinates fixed by the frame (zero sample
variance: t_L.y, t_L.z, t_R.y, t_R.z when every sample is re-expressed in its own
FH frame) are accepted: they get zero loadings and the 0.3 mm floor as residual,
and are listed in ``recalibration.frame_fixed_coordinates``.  Factors are named ``pf01..pf18``; loadings are unit
columns with ``factor_sigma`` the column norms.  Caveat: these factors include
isometric size (no ``size`` column), so with the global log-scale zeta the size
direction is counted twice (D-03); WP-24 decides before promotion.

Output (both modes): a ``face3d.landmark_prior`` document (format version 1,
``data_version`` 2) loadable with
``FactorPrior.from_package(path=...)``, with ``provenance {source, file,
sha256, n per sex, date, badge '📄', tool, base_prior}``, ``licence`` from
``--licence`` and, for samples, the attribution text.  Written deterministically
(``tools/build_prior_tables.dumps``).

Usage::

    python3 tools/recalibrate_prior.py --ansur ANSUR_II_MALE.csv ANSUR_II_FEMALE.csv --licence CC0-1.0 \\
        --out face3d/data/landmark_prior_v2.json [--date 2026-12-01]
    python3 tools/recalibrate_prior.py --landmark-samples flame_samples.npz --licence CC-BY-4.0 \\
        --attribution "Derived from FLAME 2023 Open (CC BY 4.0) ..." --out prior_flame.json
"""
from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from face3d.model.landmark_prior import PACKAGE_PRIOR_PATH, load_prior_package  # noqa: E402
from face3d.model.registry import landmark_base  # noqa: E402

RESEARCH_REL = "research/data/metric-3d-landmark-reference.json"
DEFAULT_RESEARCH = REPO / RESEARCH_REL
BADGE_SINGLE_SOURCE = "\U0001F4C4"


def _load_tool(name: str):
    spec = importlib.util.spec_from_file_location(f"_face3d_tool_{name}", Path(__file__).resolve().parent / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class RecalibrationError(ValueError):
    """Input refused (implausible units, wrong frame, missing columns ...)."""


# =========================================================================== ported calibration
# Ported VERBATIM from research/_raw/scripts/build_lm.py: initial guesses for factor SDs
# (mm, size = CV) -- the ridge target and the floor reference of calibrate().
SIG0 = {
    "size": 0.03, "lower_face_height": 3.5, "face_depth": 4.0, "mandible_projection": 3.5,
    "face_width": 2.0, "nose_projection": 2.0, "nose_width": 0.8, "interorbital": 1.0,
    "lips": 1.8, "mouth_width": 1.2, "cephalic_index": 3.0, "brow_projection": 2.0,
    "upper_face_height": 2.5, "ear_length": 1.5, "ear_protrusion": 2.5, "soft_tissue": 2.5,
    "eye_opening": 0.8, "vault_height": 4.0,
}

# Ported VERBATIM from build_lm.py: calibration targets (a, b, mean_M, sd_M, mean_F, sd_F, status);
# the same values are the norm columns of the research table model_vs_norm_chords.
TARGETS = [
    ("en_L", "en_R", 33.3, 2.7, 31.8, 2.3, "knowledge (Farkas NAW; Kosovo-Albanian sample within 1 mm)"),
    ("ex_L", "ex_R", 90.0, 3.6, 87.0, 4.0, "mean knowledge; SD sourced (arXiv 2304.07175 copy of Farkas SDs)"),
    ("en_L", "ex_L", 31.0, 1.4, 30.0, 1.4, "knowledge"),
    ("p_L", "p_R", 64.5, 3.5, 62.0, 3.3, "knowledge (ANSUR 1988 via Dodgson 2004)"),
    ("al_L", "al_R", 34.9, 2.1, 31.4, 2.0, "knowledge (Farkas NAW)"),
    ("ch_L", "ch_R", 53.0, 3.3, 50.0, 3.0, "knowledge"),
    ("zy_L", "zy_R", 141.0, 5.0, 132.0, 4.6, "knowledge (soft-tissue/ANSUR-type bizygomatic)"),
    ("go_L", "go_R", 108.0, 6.5, 100.0, 6.0, "knowledge (soft-tissue jaw-angle width, not caliper on bone)"),
    ("t_L", "t_R", 145.0, 5.5, 137.0, 5.0, "knowledge (bitragion breadth)"),
    ("eu_L", "eu_R", 152.0, 5.3, 145.0, 5.0, "knowledge (Farkas/ANSUR range)"),
    ("g", "op", 197.0, 6.6, 187.0, 6.3, "knowledge"),
    ("n", "sn", 54.0, 3.3, 50.5, 3.1, "knowledge"),
    ("sn", "prn", 20.0, 2.0, 19.0, 1.9, "knowledge"),
    ("n", "prn", 49.0, 3.5, 45.0, 3.2, "knowledge"),
    ("sn", "sto", 22.0, 2.2, 20.0, 2.0, "knowledge"),
    ("sn", "me", 70.0, 4.8, 64.0, 4.2, "knowledge"),
    ("n", "me", 121.3, 6.8, 111.8, 5.2, "means sourced (PMC3485457 table); SDs sourced (arXiv 2304.07175)"),
    ("sa_L", "sba_L", 63.5, 3.6, 59.5, 3.4, "knowledge (Farkas/ANSUR range)"),
    ("ps_L", "pi_L", 9.5, 1.0, 9.5, 1.0, "knowledge"),
    ("ls", "sto", 8.5, 1.5, 7.5, 1.4, "knowledge"),
    ("sto", "li", 10.0, 1.5, 9.5, 1.4, "knowledge"),
]
# Ported VERBATIM from build_lm.py: SD-only targets on derived quantities (no mean claim).
SD_ONLY = [("t_L", "n", 5.0, 4.7), ("t_L", "prn", 6.0, 5.6), ("t_L", "me", 6.5, 6.0)]
# Ported VERBATIM from build_lm.py: SD of coordinate differences (axis, a, b, sd_M, sd_F).
FUNC = [(2, "ls", "sn", 1.8, 1.7), (2, "li", "pg", 2.2, 2.0), (2, "prn", "sn", 1.8, 1.7), (2, "pg", "n", 3.5, 3.2)]
#: Ridge weight of calibrate() (build_lm.py).
RIDGE_LAMBDA = 0.15

#: ANSUR II column -> prior target (WP-14 spec; research ansur2_head_columns frame_mapping).
#: ('chord', a, b) is the 3D distance; ('vy', 'v') the height of v above the tragion midpoint.
ANSUR_TARGETS: dict[str, tuple[str, ...]] = {
    "headlength": ("chord", "g", "op"),
    "headbreadth": ("chord", "eu_L", "eu_R"),
    "bizygomaticbreadth": ("chord", "zy_L", "zy_R"),
    "mentonsellionlength": ("chord", "n", "me"),
    "interpupillarybreadth": ("chord", "p_L", "p_R"),
    "earlength": ("chord", "sa_L", "sba_L"),
    "tragiontopofhead": ("vy", "v"),
}
#: Columns whose balanced log-SDs propose scale_sigma_log (head length, breadth, face height; WP-14 spec).
SCALE_COLUMNS = ("headlength", "headbreadth", "mentonsellionlength")
#: Explicit plausible range for headlength, mm (WP-14 spec); other columns use research ranges x (0.75, 1.25).
EXPLICIT_RANGE_MM = {"headlength": (150.0, 250.0)}
RANGE_MARGIN = (0.75, 1.25)
#: Minimum complete rows of a group to enter the balanced pooling (🆕 provisional).
MIN_GROUP_N = 30
#: Iterated principal factors: number of factors and residual SD floor (WP-14 spec).
N_FACTORS = 18
RESIDUAL_FLOOR_MM = 0.3
#: A coordinate whose sample SD is at most this (mm) is fixed by the frame, e.g. t_L.y / t_L.z / t_R.y /
#: t_R.z in the FH frame (origin mid-tragion, FH plane through both tragia); 🆕.
FIXED_SD_MM = 1e-6


def nnls(A, b, tol=1e-12, maxit=500):
    """Lawson-Hanson NNLS, ported VERBATIM from build_lm.py."""
    m, n = A.shape
    P = np.zeros(n, bool); x = np.zeros(n)  # noqa: E702
    w = A.T @ (b - A @ x)
    it = 0
    while (~P).any() and w[~P].max() > tol and it < maxit:
        it += 1
        j = np.argmax(np.where(~P, w, -np.inf)); P[j] = True  # noqa: E702
        while True:
            z = np.zeros(n)
            z[P] = np.linalg.lstsq(A[:, P], b, rcond=None)[0]
            if (z[P] > 0).all():
                x = z; break  # noqa: E702
            mask = P & (z <= 0)
            alpha = np.min(x[mask] / (x[mask] - z[mask]))
            x = x + alpha * (z - x)
            P = P & (x > tol)
        w = A.T @ (b - A @ x)
    return x


def target_gradient(X: np.ndarray, ids: Sequence[str], target: tuple) -> tuple[float, np.ndarray]:
    """(value, d value / d X (n, 3)) of a target at the mean ``X`` (build_lm.py ``dist_grad`` + v.y).

    ``('chord', a, b)``: |X_a - X_b|; ``('axis', ax, a, b)``: X_a[ax] - X_b[ax];
    ``('vy', 'v')``: X_v.y - (X_tL.y + X_tR.y) / 2.
    """
    idx = {k: i for i, k in enumerate(ids)}
    g = np.zeros_like(X)
    if target[0] == "chord":
        ia, ib = idx[target[1]], idx[target[2]]
        d = X[ia] - X[ib]
        L = float(np.linalg.norm(d))
        g[ia] = d / L
        g[ib] = -d / L
        return L, g
    if target[0] == "axis":
        ax, a, b = target[1], idx[target[2]], idx[target[3]]
        g[a, ax] = 1.0
        g[b, ax] = -1.0
        return float(X[a, ax] - X[b, ax]), g
    if target[0] == "vy":
        iv, tl, tr = idx[target[1]], idx["t_L"], idx["t_R"]
        g[iv, 1] = 1.0
        g[tl, 1] = -0.5
        g[tr, 1] = -0.5
        return float(X[iv, 1] - 0.5 * (X[tl, 1] + X[tr, 1])), g
    raise ValueError(f"unknown target {target!r}")


def default_targets(sex: str) -> list[tuple[tuple, float, str]]:
    """build_lm.py target list for sex 'M' / 'F': [(target, sd_mm, label)]."""
    out = []
    for a, b, _mM, sM, _mF, sF, _st in TARGETS:
        out.append((("chord", a, b), sM if sex == "M" else sF, f"{a}-{b}"))
    for a, b, sM, sF in SD_ONLY:
        out.append((("chord", a, b), sM if sex == "M" else sF, f"{a}-{b}"))
    for ax, a, b, sM, sF in FUNC:
        out.append((("axis", ax, a, b), sM if sex == "M" else sF, f"{a}.{'xyz'[ax]}-{b}.{'xyz'[ax]}"))
    return out


def calibrate_sigmas(X: np.ndarray, ids: Sequence[str], loadings: np.ndarray, factor_names: Sequence[str],
                     resvar: np.ndarray, targets: Sequence[tuple[tuple, float, str]]) -> np.ndarray:
    """Factor sigmas by build_lm.py ``calibrate`` (weighted NNLS + ridge toward SIG0, floor 0.5 x SIG0).

    ``loadings``: (3n, K) with sigma NOT applied (the packaged convention), evaluated at ``X``.
    """
    rows, tv, sds = [], [], []
    for tgt, sd, _ in targets:
        _, g = target_gradient(X, ids, tgt)
        gv = g.reshape(-1)
        proj = gv @ loadings
        rows.append(proj ** 2)
        tv.append(sd ** 2 - float(gv @ resvar @ gv))
        sds.append(sd)
    A = np.array(rows)
    t = np.array(tv)
    s0 = np.array([SIG0[k] ** 2 for k in factor_names])
    W = 1.0 / np.array(sds) ** 2
    scale = s0.copy()
    scale[scale == 0] = 1
    Aa = np.vstack([A * W[:, None], np.sqrt(RIDGE_LAMBDA) * np.diag(1 / scale)])
    ta = np.concatenate([t * W, np.sqrt(RIDGE_LAMBDA) * s0 / scale])
    x = nnls(Aa, ta)
    floor = 0.25 * s0  # keep every factor alive: sigma >= 0.5 * initial guess
    if "size" in factor_names:
        floor[list(factor_names).index("size")] = 0.0
    x = np.maximum(x, floor)
    return np.sqrt(x)


def implied_sd(X: np.ndarray, ids: Sequence[str], L: np.ndarray, R: np.ndarray, target: tuple) -> float:
    _, g = target_gradient(X, ids, target)
    gv = g.reshape(-1)
    return float(math.sqrt(float(gv @ (L @ (L.T @ gv)) + gv @ R @ gv)))


# =========================================================================== (a) ANSUR II
def _research_ranges(path: Path) -> dict[str, tuple[float, float]]:
    """Plausible column ranges from the research table ansur2_head_columns (mm)."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    table = next(t for t in doc["tables"] if t["name"] == "ansur2_head_columns")
    cols = table["columns"]
    out = {}
    for row in table["rows"]:
        r = dict(zip(cols, row))
        name = str(r["csv_column"])
        try:
            lo = min(float(str(r["male_mean_range"]).split("-")[0]), float(str(r["female_mean_range"]).split("-")[0]))
            hi = max(float(str(r["male_mean_range"]).split("-")[1]), float(str(r["female_mean_range"]).split("-")[1]))
        except (ValueError, IndexError):
            continue  # demographics row
        out[name] = (RANGE_MARGIN[0] * lo, RANGE_MARGIN[1] * hi)
    out.update(EXPLICIT_RANGE_MM)
    return out


def read_ansur(paths: Sequence[Path], ranges: dict[str, tuple[float, float]]
               ) -> tuple[dict[str, dict[str, np.ndarray]], list[str], dict[str, float], list[dict[str, Any]]]:
    """Read CSV(s) -> ({'M'|'F': {'X': (n, p), 'group': (n,)}}, columns, unit_scale, file records).

    Header matching is case-insensitive.  Rows without a recognised Gender or with
    a missing / non-numeric used column are dropped.
    """
    headers_all: list[list[str]] = []
    raw_rows: list[dict[str, str]] = []
    files = []
    for p in paths:
        data = Path(p).read_bytes()
        files.append({"file": Path(p).name, "sha256": hashlib.sha256(data).hexdigest()})
        text = data.decode("utf-8-sig", errors="replace").splitlines()
        rd = csv.reader(text)
        header = [h.strip() for h in next(rd)]
        headers_all.append(header)
        low = [h.lower() for h in header]
        for row in rd:
            if not row:
                continue
            raw_rows.append({low[i]: row[i].strip() for i in range(min(len(low), len(row)))})
    common = set(h.lower() for h in headers_all[0])
    for h in headers_all[1:]:
        common &= set(x.lower() for x in h)
    if "gender" not in common:
        raise RecalibrationError("CSV has no Gender column")
    missing = [c for c in ANSUR_TARGETS if c not in common]
    if missing:
        raise RecalibrationError(f"CSV lacks the required ANSUR II columns {missing}")
    columns = [c for c in ranges if c in common]
    columns = list(ANSUR_TARGETS) + [c for c in columns if c not in ANSUR_TARGETS]
    has_group = "dodrace" in common
    sex_map = {"male": "M", "m": "M", "female": "F", "f": "F"}
    vals: dict[str, list[list[float]]] = {"M": [], "F": []}
    grp: dict[str, list[str]] = {"M": [], "F": []}
    for r in raw_rows:
        s = sex_map.get(r.get("gender", "").strip().lower())
        if s is None:
            continue
        try:
            x = [float(r[c]) for c in columns]
        except (KeyError, ValueError):
            continue
        if not all(math.isfinite(v) for v in x):
            continue
        vals[s].append(x)
        grp[s].append(r.get("dodrace", "") if has_group else "all")
    out = {s: {"X": np.array(vals[s], float).reshape(-1, len(columns)), "group": np.array(grp[s], dtype=object)}
           for s in ("M", "F")}
    for s in ("M", "F"):
        if len(out[s]["X"]) < 2:
            raise RecalibrationError(f"CSV has fewer than 2 complete rows for sex {s}")
    # unit plausibility per column on the pooled median
    unit_scale = {}
    allX = np.vstack([out["M"]["X"], out["F"]["X"]])
    for j, c in enumerate(columns):
        lo, hi = ranges[c]
        m = float(np.median(allX[:, j]))
        if lo <= m <= hi:
            unit_scale[c] = 1.0
        elif lo <= m / 10.0 <= hi:
            unit_scale[c] = 0.1
        else:
            raise RecalibrationError(f"column {c!r}: median {m:g} is implausible in mm (expected {lo:g}..{hi:g}), "
                                     f"also after /10; refusing")
        for s in ("M", "F"):
            out[s]["X"][:, j] *= unit_scale[c]
    return out, columns, unit_scale, files


def balanced_pool(X: np.ndarray, group: np.ndarray, min_group_n: int = MIN_GROUP_N
                  ) -> tuple[np.ndarray, np.ndarray, int, int]:
    """Equal-weight pooled (mean, covariance) over groups (anat R5.5); returns (mu, Sigma, K, n_used).

    ``Sigma = mean_g [Sigma_g + (mu_g - mu)(mu_g - mu)^T]`` with per-group ddof=1 covariances.
    """
    labels = sorted({str(g) for g in group})
    mus, covs, n_used = [], [], 0
    for lab in labels:
        Xg = X[np.array([str(g) == lab for g in group])]
        if len(Xg) < max(2, min_group_n):
            continue
        mus.append(Xg.mean(axis=0))
        covs.append(np.cov(Xg, rowvar=False, ddof=1).reshape(X.shape[1], X.shape[1]))
        n_used += len(Xg)
    if not mus:
        raise RecalibrationError(f"no group has at least {min_group_n} complete rows")
    mu = np.mean(mus, axis=0)
    Sig = np.mean([C + np.outer(m - mu, m - mu) for m, C in zip(mus, covs)], axis=0)
    return mu, Sig, len(mus), n_used


def ansur_statistics(data: dict[str, dict[str, np.ndarray]], columns: Sequence[str],
                     min_group_n: int = MIN_GROUP_N) -> dict[str, dict[str, Any]]:
    """Pooled per-sex statistics: mean, sd, corr (mm) and balanced log-SDs of the scale columns."""
    stats = {}
    for s in ("M", "F"):
        X, g = data[s]["X"], data[s]["group"]
        mu, Sig, K, n_used = balanced_pool(X, g, min_group_n)
        sd = np.sqrt(np.diag(Sig))
        corr = Sig / np.outer(sd, sd)
        sc = [columns.index(c) for c in SCALE_COLUMNS]
        _, Sl, _, _ = balanced_pool(np.log(X[:, sc]), g, min_group_n)
        log_sd = np.sqrt(np.diag(Sl))
        stats[s] = {"n": int(len(X)), "n_pooled": int(n_used), "n_groups_pooled": int(K),
                    "columns": list(columns), "mean_mm": mu, "sd_mm": sd, "corr": corr,
                    "log_sd": {c: float(v) for c, v in zip(SCALE_COLUMNS, log_sd)}}
    return stats


# =========================================================================== (b) landmark samples
def frame_fixed(C: np.ndarray, fixed_sd: float = FIXED_SD_MM) -> np.ndarray:
    """Boolean mask of coordinates whose sample SD is at most ``fixed_sd`` (mm): fixed by the frame."""
    return np.sqrt(np.clip(np.diag(np.asarray(C, float)), 0.0, None)) <= fixed_sd


def principal_factors(C: np.ndarray, K: int = N_FACTORS, floor_sd: float = RESIDUAL_FLOOR_MM,
                      max_iter: int = 3000, tol: float = 1e-8) -> tuple[np.ndarray, np.ndarray]:
    """Iterated principal (axis) factors: C ~ L L^T + diag(psi), residual SD >= ``floor_sd`` (mm).

    Coordinates whose SD is at most :data:`FIXED_SD_MM` are fixed by the frame (in
    the FH frame t_L.y, t_L.z, t_R.y and t_R.z are zero in every sample): they are
    kept out of the correlation step and get zero loadings and ``psi = floor_sd^2``.

    The other coordinates go through standard principal-axis factoring on the
    correlation matrix ``Rc = D^-1 C D^-1`` (``D = sqrt(diag C)``): start from the
    uniquenesses ``1 / diag(Rc^-1)`` (squared multiple correlations; pseudo-inverse
    fallback), then repeat: top-K eigenpairs of ``Rc - diag(psi)`` (negative
    eigenvalues clipped), ``psi = max(1 - rowsum(L^2), min((floor_sd / D)^2, 1))``,
    until the uniquenesses change by less than ``tol``.  The result is rescaled to
    mm (``L <- D L``) and the floor is applied **on the mm scale**,
    ``psi_mm = max(D^2 psi, floor_sd^2)``, so a coordinate whose total SD is below
    ``floor_sd`` still gets the full floor.  Working on correlations keeps
    high-variance coordinates (vault, ears) from swamping weak factors (e.g. nasal
    width).  Column signs are fixed so that each column's largest-magnitude entry
    is positive.
    """
    C = 0.5 * (np.asarray(C, float) + np.asarray(C, float).T)
    p = C.shape[0]
    if not 0 < K < p:
        raise ValueError(f"K must be in 1..{p - 1}")
    if not floor_sd >= 0.0:
        raise ValueError("floor_sd must be >= 0")
    free = ~frame_fixed(C)
    q = int(free.sum())
    if not K < q:
        raise RecalibrationError(f"only {q} landmark coordinates vary across the samples; "
                                 f"{K} factors need more than {K}")
    D = np.sqrt(np.diag(C)[free])
    Rc = C[np.ix_(free, free)] / np.outer(D, D)
    floor = np.minimum((floor_sd / D) ** 2, 1.0)
    try:
        psi = 1.0 / np.diag(np.linalg.inv(Rc))
    except np.linalg.LinAlgError:
        psi = 1.0 / np.diag(np.linalg.pinv(Rc))
    psi = np.clip(np.nan_to_num(psi, nan=1.0, posinf=1.0, neginf=0.0), floor, 1.0)
    Lf = np.zeros((q, K))
    for _ in range(max_iter):
        w, V = np.linalg.eigh(Rc - np.diag(psi))
        order = np.argsort(w)[::-1][:K]
        w, V = np.clip(w[order], 0.0, None), V[:, order]
        Lf = V * np.sqrt(w)[None, :]
        new = np.maximum(1.0 - np.sum(Lf * Lf, axis=1), floor)
        done = float(np.max(np.abs(new - psi))) <= tol
        psi = new
        if done:
            break
    L = np.zeros((p, K))
    L[free] = D[:, None] * Lf
    psi_mm = np.full(p, float(floor_sd) ** 2)
    psi_mm[free] = np.maximum(psi * D ** 2, float(floor_sd) ** 2)
    big = np.argmax(np.abs(L), axis=0)
    L = L * np.where(L[big, np.arange(K)] < 0, -1.0, 1.0)[None, :]
    return L, psi_mm


def check_sample_frame(samples: np.ndarray, ids: Sequence[str]) -> None:
    """Refuse samples not in the FH frame in mm (+x subject's left, origin mid-tragion)."""
    idx = {k: i for i, k in enumerate(ids)}
    mu = samples.mean(axis=0)
    breadth = float(np.linalg.norm(mu[idx["eu_L"]] - mu[idx["eu_R"]]))
    if not 100.0 <= breadth <= 220.0:
        hint = " (looks like metres: multiply by 1000)" if 0.1 <= breadth <= 0.22 else ""
        raise RecalibrationError(f"mean eu_L-eu_R breadth {breadth:g} is not a head breadth in mm{hint}")
    if not mu[idx["t_L"], 0] > 0.0 > mu[idx["t_R"], 0]:
        raise RecalibrationError("t_L must have +x (subject's left) and t_R -x: wrong side convention")
    mid = 0.5 * (mu[idx["t_L"]] + mu[idx["t_R"]])
    if float(np.linalg.norm(mid)) > 10.0:
        raise RecalibrationError(f"mean tragion midpoint is {np.linalg.norm(mid):.1f} mm from the origin; "
                                 "samples must be in the FH frame with origin mid-tragion")


def sample_model(samples: np.ndarray, K: int) -> dict[str, Any]:
    """Empirical mean and K-factor + diagonal model of samples (S, n, 3)."""
    S, n, _ = samples.shape
    Y = samples.reshape(S, 3 * n)
    mu = Y.mean(axis=0)
    C = np.cov(Y, rowvar=False, ddof=1)
    L, psi = principal_factors(C, K)
    sig = np.linalg.norm(L, axis=0)
    load = L / np.where(sig > 0, sig, 1.0)[None, :]
    return {"mean": mu.reshape(n, 3), "factor_sigma": sig, "loadings": load, "psi": psi, "n": int(S),
            "fixed": frame_fixed(C)}


# =========================================================================== documents
def _base_doc(base: Path) -> tuple[dict[str, Any], str]:
    raw = Path(base).read_bytes()
    return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()


def build_from_ansur(paths: Sequence[Path], *, base: Path = PACKAGE_PRIOR_PATH, research: Path = DEFAULT_RESEARCH,
                     licence: str, date: str, min_group_n: int = MIN_GROUP_N) -> dict[str, Any]:
    """Prior document recalibrated to ANSUR II statistics (mode a)."""
    ranges = _research_ranges(research)
    data, columns, unit_scale, files = read_ansur(paths, ranges)
    stats = ansur_statistics(data, columns, min_group_n)
    doc, base_sha = _base_doc(base)
    pkg = load_prior_package(base)
    ids, fnames = pkg["ids"], pkg["factor_names"]
    R = pkg["residual_cov"]
    targets_out: dict[str, list[dict[str, Any]]] = {}
    sig_v1: dict[str, list[float]] = {}
    for s in ("M", "F"):
        X = pkg["sexes"][s]["mean"]
        Lo = pkg["sexes"][s]["loadings"]
        tg = default_targets(s)
        ansur_sd = {c: float(stats[s]["sd_mm"][columns.index(c)]) for c in ANSUR_TARGETS}
        new_tg = []
        replaced = set()
        for tgt, sd, label in tg:
            for c, m in ANSUR_TARGETS.items():
                if m[0] == "chord" and tgt[0] == "chord" and {tgt[1], tgt[2]} == {m[1], m[2]}:
                    sd = ansur_sd[c]
                    replaced.add(c)
            new_tg.append((tgt, sd, label))
        for c, m in ANSUR_TARGETS.items():
            if c not in replaced:
                new_tg.append((m, ansur_sd[c], c))
        sig_old = pkg["sexes"][s]["factor_sigma"]
        sig_new = calibrate_sigmas(X, ids, Lo, fnames, R, new_tg)
        sig_v1[s] = [float(v) for v in sig_old]
        doc["sexes"][s]["factor_sigma"] = [float(v) for v in sig_new]
        rows = []
        for c, m in ANSUR_TARGETS.items():
            j = columns.index(c)
            val, _ = target_gradient(X, ids, m)
            rows.append({"csv_column": c, "target": "-".join(m[1:]) if m[0] == "chord" else "v.y",
                         "ansur_mean_mm": float(stats[s]["mean_mm"][j]), "ansur_sd_mm": float(stats[s]["sd_mm"][j]),
                         "model_value_mm": val,
                         "model_sd_v1_mm": implied_sd(X, ids, Lo * sig_old[None, :], R, m),
                         "model_sd_v2_mm": implied_sd(X, ids, Lo * sig_new[None, :], R, m)})
        targets_out[s] = rows
    per_sex_scale = {s: float(np.mean(list(stats[s]["log_sd"].values()))) for s in ("M", "F")}
    proposed = round(float(np.mean(list(per_sex_scale.values()))), 4)
    old_scale = doc["defaults"]["scale_sigma_log"]
    doc["defaults"]["scale_sigma_log"] = proposed
    doc.setdefault("defaults_provenance", {})["scale_sigma_log"] = (
        "proposed by tools/recalibrate_prior.py: mean balanced log-SD of headlength, headbreadth and "
        f"mentonsellionlength (ANSUR II, per sex then averaged); v1 value {old_scale} (badge \U0001F4C4)")
    doc["data_version"] = 2
    doc["licence"] = licence
    doc["badge"] = BADGE_SINGLE_SOURCE
    doc["status"] = ("factor sigmas recalibrated to ANSUR II head measures (single source, balanced pooling by "
                     "sex); means, loadings and residuals from the base prior (expert knowledge)")
    doc["provenance"] = {
        "source": "ANSUR II public CSV (user-supplied; never bundled)", "files": files,
        "sha256": hashlib.sha256("".join(f["sha256"] for f in files).encode()).hexdigest(),
        "n": {s: stats[s]["n"] for s in ("M", "F")}, "date": date, "badge": BADGE_SINGLE_SOURCE,
        "tool": "tools/recalibrate_prior.py --ansur", "base_prior": {"path": Path(base).name, "sha256": base_sha},
        "pooling": "by sex only; equal weight per demographic group of the file (anat R5.5); "
                   "no group-conditioned output (anat R7.4)",
        "unit_scale": unit_scale,
    }
    doc["recalibration"] = {
        "method": "ansur",
        "statistics": {s: {"n": stats[s]["n"], "n_pooled": stats[s]["n_pooled"],
                           "n_groups_pooled": stats[s]["n_groups_pooled"], "columns": stats[s]["columns"],
                           "mean_mm": stats[s]["mean_mm"].tolist(), "sd_mm": stats[s]["sd_mm"].tolist(),
                           "corr": stats[s]["corr"].tolist(), "log_sd": stats[s]["log_sd"]} for s in ("M", "F")},
        "targets": targets_out,
        "factor_sigma_base": sig_v1,
        "scale_sigma_log": {"proposed": proposed, "per_sex": per_sex_scale, "base": old_scale,
                            "rule": "mean over sexes of the mean balanced log-SD of " + ", ".join(SCALE_COLUMNS)},
        "calibration": ("build_lm.py calibrate (weighted NNLS, ridge 0.15 toward SIG0, floor 0.5 x SIG0) with "
                        "the ANSUR SDs replacing the mapped targets; means kept"),
    }
    return doc


def build_from_samples(path: Path, *, base: Path = PACKAGE_PRIOR_PATH, licence: str, attribution: str, date: str,
                       n_factors: int = N_FACTORS) -> dict[str, Any]:
    """Empirical K-factor prior document from landmark samples (mode b)."""
    if not str(attribution).strip():
        raise RecalibrationError("--attribution is required for landmark samples (e.g. FLAME 2023 Open, CC BY 4.0)")
    raw = Path(path).read_bytes()
    pkg = load_prior_package(base)
    ids = pkg["ids"]
    with np.load(path, allow_pickle=False) as z:
        keys = list(z.files)
        if "samples" in z.files:
            samples = np.asarray(z["samples"], float)
        elif len(keys) == 1:
            samples = np.asarray(z[keys[0]], float)
        else:
            raise RecalibrationError(f"NPZ must hold 'samples' (S, 44, 3); found {keys}")
        sid = [str(x) for x in z["ids"]] if "ids" in z.files else None
        sex = np.array([str(x) for x in z["sex"]]) if "sex" in z.files else None
    if samples.ndim != 3 or samples.shape[1:] != (len(ids), 3):
        raise RecalibrationError(f"samples must have shape (S, {len(ids)}, 3), got {samples.shape}")
    if sid is not None and sid != list(ids):
        raise RecalibrationError("sample ids differ from the prior id order")
    if not np.all(np.isfinite(samples)):
        raise RecalibrationError("samples contain non-finite values")
    check_sample_frame(samples, ids)
    groups = {"M": samples, "F": samples}
    shared = True
    if sex is not None:
        if sex.shape != (len(samples),) or not set(sex) <= {"M", "F"}:
            raise RecalibrationError("'sex' must be (S,) of 'M' / 'F'")
        groups = {s: samples[sex == s] for s in ("M", "F")}
        shared = False
    S_min = n_factors + 2
    for s, g in groups.items():
        if len(g) <= max(S_min, 3 * len(ids)):
            raise RecalibrationError(f"sex {s}: {len(g)} samples are too few for a {3 * len(ids)}-dim covariance")
    models = {"M": sample_model(groups["M"], n_factors)}
    models["F"] = models["M"] if shared else sample_model(groups["F"], n_factors)
    doc, base_sha = _base_doc(base)
    psi = 0.5 * (models["M"]["psi"] + models["F"]["psi"])
    total = np.sqrt(psi).reshape(len(ids), 3)
    asym = np.array([total[i] if landmark_base(k) != k else np.zeros(3) for i, k in enumerate(ids)])
    names = [f"pf{k + 1:02d}" for k in range(n_factors)]
    fixed_mask = (models["M"]["fixed"] | models["F"]["fixed"]).reshape(len(ids), 3)
    fixed = [f"{ids[i]}.{'xyz'[a]}" for i, a in zip(*np.nonzero(fixed_mask))]
    out = {
        "format": "face3d.landmark_prior", "version": 1, "data_version": 2,
        "licence": licence, "attribution": str(attribution),
        "status": ("empirical factor model (iterated principal factors) of user-supplied landmark samples; "
                   "factors include isometric size"),
        "badge": BADGE_SINGLE_SOURCE,
        "source": {"path": Path(path).name, "sha256": hashlib.sha256(raw).hexdigest(), "tables": []},
        "frame": doc["frame"], "ids": list(ids), "names": list(doc["names"]), "factor_names": names,
        "sexes": {s: {"mean": m["mean"].tolist(), "factor_sigma": m["factor_sigma"].tolist(),
                      "loadings": m["loadings"].tolist()} for s, m in models.items()},
        "residual_cov": np.diag(psi).tolist(),
        "residual_total": total.tolist(),
        "residual_asym": asym.tolist(),
        "residual_note": (f"diagonal residual (iterated principal factors, SD floor {RESIDUAL_FLOOR_MM} mm on the mm "
                          "scale, averaged over the sex models); bilateral residuals are independent per side; "
                          "coordinates fixed by the frame have zero loadings and the floor as residual"),
        "loadings_note": "rows 3*i + axis; unit columns; sigma NOT applied; columns pf01..",
        "defaults": doc["defaults"],
        "defaults_provenance": doc.get("defaults_provenance", {}),
        "provenance": {"source": "user-supplied 3D landmark samples (never bundled)", "file": Path(path).name,
                       "sha256": hashlib.sha256(raw).hexdigest(),
                       "n": {s: int(m["n"]) for s, m in models.items()}, "shared_between_sexes": shared,
                       "date": date, "badge": BADGE_SINGLE_SOURCE, "tool": "tools/recalibrate_prior.py --landmark-samples",
                       "base_prior": {"path": Path(base).name, "sha256": base_sha}},
        "recalibration": {"method": "landmark_samples", "n_factors": n_factors,
                          "residual_floor_mm": RESIDUAL_FLOOR_MM,
                          "frame_fixed_coordinates": fixed, "frame_fixed_sd_mm": FIXED_SD_MM,
                          "caveat": "size is inside the factors (no 'size' column): with the global log-scale "
                                    "zeta it is counted twice (D-03); decide before promotion (WP-24)"},
    }
    return out


def write(doc: dict[str, Any], out: Path) -> bytes:
    bpt = _load_tool("build_prior_tables")
    return bpt.write(doc, out)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--ansur", type=Path, nargs="+", help="ANSUR II CSV file(s) (user-supplied, never bundled)")
    mode.add_argument("--landmark-samples", type=Path, help="NPZ with samples (S, 44, 3) in the FH frame, mm")
    ap.add_argument("--out", type=Path, required=True, help="output prior JSON (e.g. face3d/data/landmark_prior_v2.json)")
    ap.add_argument("--licence", required=True, help="SPDX licence of the derived prior (bundling needs CC0-1.0)")
    ap.add_argument("--attribution", default="", help="attribution text (required for landmark samples)")
    ap.add_argument("--base", type=Path, default=PACKAGE_PRIOR_PATH, help="base prior (default: packaged v1)")
    ap.add_argument("--research", type=Path, default=DEFAULT_RESEARCH, help=f"research JSON (default {RESEARCH_REL})")
    ap.add_argument("--date", default=None, help="provenance date YYYY-MM-DD (default: today, UTC)")
    ap.add_argument("--min-group-n", type=int, default=MIN_GROUP_N, help="minimum rows of a pooled group")
    ap.add_argument("--factors", type=int, default=N_FACTORS, help="number of principal factors (samples)")
    args = ap.parse_args(argv)
    date = args.date or datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    try:
        if args.ansur:
            doc = build_from_ansur(args.ansur, base=args.base, research=args.research, licence=args.licence,
                                   date=date, min_group_n=args.min_group_n)
        else:
            doc = build_from_samples(args.landmark_samples, base=args.base, licence=args.licence,
                                     attribution=args.attribution, date=date, n_factors=args.factors)
    except (RecalibrationError, OSError, KeyError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    data = write(doc, args.out)
    print(f"wrote {args.out} ({len(data)} bytes, sha256 {hashlib.sha256(data).hexdigest()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
