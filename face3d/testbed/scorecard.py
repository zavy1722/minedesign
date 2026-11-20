"""Scorecards: per-scenario medians over seeds, comparison against a committed baseline.

DESIGN 7.5 / D-30: a committed baseline scorecard of the legacy engine is recorded
before any engine change; later engines are compared against it (promotion rule:
no legacy-scenario regression beyond 2 %). Tier-1 CI compares "medians vs stored
baselines +/- 3 MAD over 30 seeds" (research/reconstruction/validation-test-bed.md,
"CI").

Scorecard layout (JSON-serialisable, deterministic)::

    {"meta": {"engine_label", "git_rev", "numpy_version", "seeds", "scenario_defs",
              "metric_keys", "format"},
     "scenarios": {name: {metric: {"median", "mad", "n_ok"}}},
     "per_seed_first3": {name: [per-seed metric dicts for seeds 1000, 1001, 1002]}}

* ``median`` / ``mad`` are NaN-safe over the seeds whose metric is finite; ``mad`` is the
  raw median absolute deviation (not scaled by 1.4826); ``n_ok`` counts finite values.
  Missing values (no finite seed) are stored as JSON ``null``.
* Seeds are ``range(1000, 1000 + n_seeds)`` (WBS WP-01).
* ``runtime_s`` is wall-clock and machine dependent, so it is left out of the stored
  scorecard unless ``include_runtime=True`` (keeps the committed file reproducible).
* Floats are rounded to 9 significant digits and keys sorted when written
  (:func:`dumps`).

CLI::

    python -m face3d.testbed.scorecard --seeds 30 --out PATH [--fast] [--scenarios a,b]
        [--engine-label LABEL] [--git-rev REV] [--compare BASELINE.json]

``--fast`` runs 5 seeds on :data:`face3d.testbed.scenarios.FAST_SCENARIOS` (3 scenarios).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from typing import Iterable, Sequence

import numpy as np

from .scenarios import FAST_SCENARIOS, METRIC_KEYS, SCENARIOS, Scenario, default_engine, run_scenario

__all__ = ["SEED0", "FAST_SEEDS", "SCORECARD_FORMAT", "HIGHER_IS_WORSE", "BASELINE_LABEL",
           "seeds_for", "aggregate", "build_scorecard", "compare", "dumps", "write_scorecard",
           "load_scorecard", "main"]

SEED0 = 1000                     # first seed (WBS WP-01)
FAST_SEEDS = 5                   # --fast: 5 seeds x 3 scenarios (WBS WP-01)
SCORECARD_FORMAT = "face3d-scorecard-v0"
SIG_DIGITS = 9                   # stored precision (WBS WP-01)
BASELINE_LABEL = "legacy-41179a3"
HIGHER_IS_WORSE: tuple[str, ...] = ("config_rms_mm", "now7_rms_mm", "focal_rel_err",
                                    "distance_rel_err", "rmse_px")
# A scenario also regresses when its fraction of usable seeds (finite config_rms_mm)
# drops by more than this (failures must not hide behind better medians).
N_OK_FRACTION_DROP = 0.10


def seeds_for(n_seeds: int) -> list[int]:
    return list(range(SEED0, SEED0 + int(n_seeds)))


def _git_rev() -> str:
    """Best-effort ``git rev-parse HEAD``; 'unknown' when unavailable."""
    env = os.environ.get("FACE3D_GIT_REV")
    if env:
        return env
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=here, capture_output=True,
                             text=True, timeout=10, check=False)
        rev = out.stdout.strip()
        return rev if out.returncode == 0 and rev else "unknown"
    except Exception:  # noqa: BLE001 - best effort only
        return "unknown"


def _round(x):
    """Round floats to SIG_DIGITS significant digits; NaN/inf -> None; recurse into containers."""
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        x = float(x)
        if not math.isfinite(x):
            return None
        return float("%.*g" % (SIG_DIGITS, x))
    if isinstance(x, dict):
        return {str(k): _round(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_round(v) for v in x]
    if isinstance(x, np.ndarray):
        return [_round(v) for v in x.tolist()]
    return x


def _as_float(v) -> float:
    if v is None:
        return float("nan")
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def aggregate(records: Sequence[dict], metric_keys: Iterable[str] = METRIC_KEYS) -> dict:
    """{metric: {median, mad, n_ok}} over the finite values of each metric (NaN-safe)."""
    out = {}
    for k in metric_keys:
        v = np.array([_as_float(r.get(k)) for r in records], float)
        v = v[np.isfinite(v)]
        if len(v):
            med = float(np.median(v))
            mad = float(np.median(np.abs(v - med)))
        else:
            med = mad = float("nan")
        out[k] = {"median": med, "mad": mad, "n_ok": int(len(v))}
    return out


def _scenario_def(s: Scenario) -> dict:
    return {
        "subject_fn": getattr(s.subject_fn, "__name__", repr(s.subject_fn)),
        "rig_fn": getattr(s.rig_fn, "__name__", repr(s.rig_fn)),
        "detector_kwargs": dict(s.detector_kwargs),
    }


def build_scorecard(scenarios: Sequence[Scenario] | dict | None = None, n_seeds: int = 30,
                    engine_fn=default_engine, engine_label: str = BASELINE_LABEL, *,
                    git_rev: str | None = None, include_runtime: bool = False,
                    progress=None) -> dict:
    """Run every scenario on seeds 1000 .. 1000 + n_seeds - 1 and aggregate.

    ``scenarios``: a list of :class:`Scenario`, a name -> Scenario dict, or None for all
    :data:`SCENARIOS`. ``git_rev`` overrides the best-effort ``git rev-parse HEAD``
    lookup (env ``FACE3D_GIT_REV`` also does). ``progress`` is an optional callable
    ``progress(name, records, seconds)`` called after each scenario.
    """
    if scenarios is None:
        scenarios = list(SCENARIOS.values())
    elif isinstance(scenarios, dict):
        scenarios = list(scenarios.values())
    seeds = seeds_for(n_seeds)
    keys = tuple(k for k in METRIC_KEYS if include_runtime or k != "runtime_s")
    sc = {
        "meta": {
            "engine_label": str(engine_label),
            "git_rev": git_rev if git_rev is not None else _git_rev(),
            "numpy_version": np.__version__,
            "seeds": seeds,
            "metric_keys": list(keys),
            "scenario_defs": {s.name: _scenario_def(s) for s in scenarios},
            "format": SCORECARD_FORMAT,
        },
        "scenarios": {},
        "per_seed_first3": {},
    }
    for s in scenarios:
        t0 = time.perf_counter()
        recs = run_scenario(s, seeds, engine_fn)
        sc["scenarios"][s.name] = aggregate(recs, keys)
        first = []
        for r in recs[:3]:
            d = {k: r[k] for k in ("seed", "failed", "error") if k in r}
            d.update({k: r.get(k, float("nan")) for k in keys})
            first.append(d)
        sc["per_seed_first3"][s.name] = first
        if progress is not None:
            progress(s.name, recs, time.perf_counter() - t0)
    return _round(sc)


def dumps(scorecard: dict) -> str:
    """Deterministic JSON text: rounded floats, NaN as null, sorted keys, trailing newline."""
    return json.dumps(_round(scorecard), sort_keys=True, indent=1, allow_nan=False) + "\n"


def write_scorecard(scorecard: dict, path: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(dumps(scorecard))


def load_scorecard(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def compare(baseline: dict, new: dict, rel_tol: float = 0.02, mad_k: float = 3.0,
            higher_is_worse: Sequence[str] = HIGHER_IS_WORSE) -> list[str]:
    """Return the ``'scenario:metric'`` entries of ``new`` that regressed against ``baseline``.

    Only scenarios present in both are compared (a fast run checks a subset). For each
    metric in ``higher_is_worse`` with finite medians b (baseline) and m (new), the entry
    regresses when

        m - b > max(rel_tol * |b|, mad_k * MAD_b / sqrt(n_ok_b)),

    i.e. the median worsened by more than 2 % (DESIGN 7.5 promotion rule) **and** by more
    than the seed noise of a median, mad_k robust standard errors (MAD / sqrt(n) is the
    noise scale of a median over n seeds up to the factor 1.4826 * 1.2533 ~= 1.86 under
    normality, so mad_k = 3 is ~1.6 standard errors; validation-test-bed.md "medians vs
    stored baselines +/- 3 MAD over 30 seeds"). A metric that has a finite baseline
    median but none in ``new`` also regresses.

    Additionally ``'scenario:n_ok'`` is reported when the fraction of seeds with a finite
    ``config_rms_mm`` drops by more than :data:`N_OK_FRACTION_DROP`.
    """
    out: list[str] = []
    bs = baseline.get("scenarios", {})
    ns = new.get("scenarios", {})
    n_seeds_b = len(baseline.get("meta", {}).get("seeds", [])) or None
    n_seeds_n = len(new.get("meta", {}).get("seeds", [])) or None
    for name in sorted(set(bs) & set(ns)):
        bm, nm = bs[name], ns[name]
        for metric in higher_is_worse:
            if metric not in bm or metric not in nm:
                continue
            b = _as_float(bm[metric].get("median"))
            m = _as_float(nm[metric].get("median"))
            if not math.isfinite(b):
                continue
            if not math.isfinite(m):
                out.append("%s:%s" % (name, metric))
                continue
            mad = _as_float(bm[metric].get("mad"))
            n_ok = max(int(bm[metric].get("n_ok") or 0), 1)
            tol = rel_tol * abs(b)
            if math.isfinite(mad):
                tol = max(tol, mad_k * mad / math.sqrt(n_ok))
            if m - b > tol:
                out.append("%s:%s" % (name, metric))
        ref = "config_rms_mm"
        if ref in bm and ref in nm and n_seeds_b and n_seeds_n:
            fb = int(bm[ref].get("n_ok") or 0) / n_seeds_b
            fn = int(nm[ref].get("n_ok") or 0) / n_seeds_n
            if fb - fn > N_OK_FRACTION_DROP:
                out.append("%s:n_ok" % name)
    return out


def _default_label() -> str:
    """'legacy-41179a3' for the legacy engine, else the engine's ENGINE_VERSION."""
    try:
        from ..solve import bundle as _bundle
        ver = getattr(_bundle, "ENGINE_VERSION", None)
    except Exception:  # noqa: BLE001
        ver = None
    return BASELINE_LABEL if ver is None else str(ver)


def _summary_lines(sc: dict) -> list[str]:
    cols = ("config_rms_mm", "now7_rms_mm", "nees_per_dof", "coverage_1s", "focal_rel_err",
            "distance_rel_err", "rmse_px")
    lines = ["%-22s %5s " % ("scenario", "n_ok") + " ".join("%12s" % c[:12] for c in cols)]
    for name, metrics in sc["scenarios"].items():
        n_ok = metrics.get("config_rms_mm", {}).get("n_ok", 0)
        vals = []
        for c in cols:
            v = _as_float(metrics.get(c, {}).get("median"))
            vals.append("%12.4g" % v if math.isfinite(v) else "%12s" % "-")
        lines.append("%-22s %5d " % (name, n_ok) + " ".join(vals))
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m face3d.testbed.scorecard",
                                 description="Run the landmark test bed and write a scorecard JSON.")
    ap.add_argument("--seeds", type=int, default=30, help="number of seeds (from 1000); default 30")
    ap.add_argument("--out", required=True, help="output JSON path")
    ap.add_argument("--fast", action="store_true",
                    help="5 seeds on 3 scenarios (%s)" % ", ".join(FAST_SCENARIOS))
    ap.add_argument("--scenarios", default=None, help="comma-separated scenario names")
    ap.add_argument("--engine-label", default=None,
                    help="label stored in meta (default: %s for the legacy engine, else ENGINE_VERSION)"
                    % BASELINE_LABEL)
    ap.add_argument("--git-rev", default=None, help="override the git revision stored in meta")
    ap.add_argument("--with-runtime", action="store_true", help="also store runtime_s (not reproducible)")
    ap.add_argument("--compare", default=None, help="baseline scorecard to compare against")
    args = ap.parse_args(list(argv) if argv is not None else None)

    n_seeds = args.seeds
    names = list(SCENARIOS)
    if args.fast:
        n_seeds = FAST_SEEDS
        names = list(FAST_SCENARIOS)
    if args.scenarios:
        names = [s.strip() for s in args.scenarios.split(",") if s.strip()]
    unknown = [n for n in names if n not in SCENARIOS]
    if unknown:
        ap.error("unknown scenario(s): %s (known: %s)" % (", ".join(unknown), ", ".join(SCENARIOS)))

    def progress(name, recs, dt):
        n_fail = sum(1 for r in recs if r.get("failed"))
        print("  %-22s %3d seeds  %3d failed  %6.1f s" % (name, len(recs), n_fail, dt), file=sys.stderr)

    t0 = time.perf_counter()
    sc = build_scorecard([SCENARIOS[n] for n in names], n_seeds, default_engine,
                         args.engine_label or _default_label(), git_rev=args.git_rev,
                         include_runtime=args.with_runtime, progress=progress)
    write_scorecard(sc, args.out)
    print("\n".join(_summary_lines(sc)))
    print("wrote %s (%d scenarios x %d seeds) in %.1f s"
          % (args.out, len(names), n_seeds, time.perf_counter() - t0))
    if args.compare:
        reg = compare(load_scorecard(args.compare), sc)
        print("regressions: %s" % (", ".join(reg) if reg else "none"))
        return 1 if reg else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
