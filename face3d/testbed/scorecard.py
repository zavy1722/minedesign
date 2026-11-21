"""Scorecards: per-scenario medians over seeds, comparison against a committed baseline.

DESIGN 7.5 / D-30: a committed baseline scorecard of the legacy engine is recorded
before any engine change; later engines are compared against it (promotion rule:
no legacy-scenario regression beyond 2 %). Tier-1 CI compares "medians vs stored
baselines +/- 3 MAD over 30 seeds" (research/reconstruction/validation-test-bed.md,
"CI").

Scorecard layout (JSON-serialisable, deterministic)::

    {"meta": {"engine_label", "git_rev", "numpy_version", "blas_threads", "seeds",
              "scenario_defs", "metric_keys", "format"},
     "scenarios": {name: {metric: {"median", "mad", "n_ok"}}},
     "per_seed_first3": {name: [per-seed metric dicts for seeds 1000, 1001, 1002]},
     "per_seed": {name: {"seed": [...], "failed": [...], metric: [one value per seed]}}}

* ``median`` / ``mad`` are NaN-safe over the seeds whose metric is finite; ``mad`` is the
  raw median absolute deviation (not scaled by 1.4826); ``n_ok`` counts finite values.
  Missing values (no finite seed) are stored as JSON ``null``.
* Seeds are ``range(1000, 1000 + n_seeds)`` (WBS WP-01).
* ``per_seed`` (an addition to the WBS layout) keeps every seed's metrics column-wise
  so that :func:`compare` can pair any two scorecards on their shared seeds (e.g. a
  ``--fast`` 5-seed run against the 30-seed baseline).
* ``runtime_s`` is wall-clock and machine dependent, so it is left out of the stored
  scorecard unless ``include_runtime=True`` (keeps the committed file reproducible).
* Floats are rounded to 9 significant digits and keys sorted when written
  (:func:`dumps`).
* ``blas_threads`` records the BLAS thread environment (``OMP_NUM_THREADS``,
  ``OPENBLAS_NUM_THREADS``, ``MKL_NUM_THREADS``; ``null`` = unset). The legacy engine is
  not bit-reproducible across BLAS thread counts: multi-threaded BLAS changes the
  reduction order, and ``camera_roll_legacy`` seed 1017 then hits an ``OverflowError``
  in the legacy ``face3d/solve/lm.py`` (fails with multi-threaded BLAS, succeeds
  single-threaded), which moves that scenario's n_ok and medians slightly. The
  committed baseline ``tests/golden/baseline_scorecard_v0.json`` was generated
  single-threaded; regenerate it with ``OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
  MKL_NUM_THREADS=1`` (the other six scenarios agree across thread counts to ~1e-7
  relative). This caveat stands until WP-07 hardens ``lm.py``.

Comparison (:func:`compare`) is **paired** when both scorecards list the same seeds,
or both store ``per_seed`` values for some shared seeds (the medians are then taken
over the shared seeds): every scenario sees the same subjects, rigs and detections in
both runs (common random numbers), so seed-sampling noise cancels and the DESIGN 7.5
2 % rule applies as is.

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
           "BLAS_THREAD_VARS", "seeds_for", "aggregate", "build_scorecard", "compare",
           "is_paired", "blas_thread_env", "blas_single_threaded", "dumps", "write_scorecard",
           "load_scorecard", "main"]

SEED0 = 1000                     # first seed (WBS WP-01)
FAST_SEEDS = 5                   # --fast: 5 seeds x 3 scenarios (WBS WP-01)
SCORECARD_FORMAT = "face3d-scorecard-v0"
SIG_DIGITS = 9                   # stored precision (WBS WP-01)
BASELINE_LABEL = "legacy-41179a3"
HIGHER_IS_WORSE: tuple[str, ...] = ("config_rms_mm", "now7_rms_mm", "focal_rel_err",
                                    "distance_rel_err", "rmse_px")
# A scenario also regresses when its fraction of usable seeds (finite config_rms_mm)
# drops by more than this, so failures cannot hide behind better medians. Test-bed
# policy choice (PROVISIONAL; 0.10 is 3 of 30 seeds, cf. the n_ok >= 28/30 baseline check).
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


BLAS_THREAD_VARS: tuple[str, ...] = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")


def blas_thread_env() -> dict:
    """The BLAS thread environment variables (None when unset); stored in meta."""
    return {k: os.environ.get(k) for k in BLAS_THREAD_VARS}


def blas_single_threaded() -> bool:
    """True when every BLAS thread variable is set to 1 (the baseline configuration)."""
    return all(v is not None and v.strip() == "1" for v in blas_thread_env().values())


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
            "blas_threads": blas_thread_env(),
            "seeds": seeds,
            "metric_keys": list(keys),
            "scenario_defs": {s.name: _scenario_def(s) for s in scenarios},
            "format": SCORECARD_FORMAT,
        },
        "scenarios": {},
        "per_seed_first3": {},
        "per_seed": {},
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
        sc["per_seed"][s.name] = per_seed_columns(recs, keys)
        if progress is not None:
            progress(s.name, recs, time.perf_counter() - t0)
    return _round(sc)


def per_seed_columns(records: Sequence[dict], metric_keys: Iterable[str] = METRIC_KEYS) -> dict:
    """Column-wise per-seed values: {"seed": [...], "failed": [...], metric: [...]}."""
    return {
        "seed": [int(r["seed"]) for r in records],
        "failed": [bool(r.get("failed", False)) for r in records],
        **{k: [_as_float(r.get(k)) for r in records] for k in metric_keys},
    }


def _shared_seeds(baseline: dict, new: dict, name: str) -> list[int]:
    """Seeds stored in both scorecards' ``per_seed`` for scenario ``name`` (sorted)."""
    pb = (baseline.get("per_seed") or {}).get(name) or {}
    pn = (new.get("per_seed") or {}).get(name) or {}
    try:
        sb = {int(s) for s in pb.get("seed", [])}
        sn = {int(s) for s in pn.get("seed", [])}
    except (TypeError, ValueError):
        return []
    return sorted(sb & sn)


def _subset_aggregate(sc: dict, name: str, seeds: Sequence[int], metric_keys: Iterable[str]) -> dict:
    """:func:`aggregate` of scenario ``name`` restricted to ``seeds`` (from ``per_seed``)."""
    cols = sc["per_seed"][name]
    pos = {int(s): i for i, s in enumerate(cols["seed"])}
    keys = [k for k in metric_keys if k in cols]
    recs = [{k: cols[k][pos[s]] for k in keys} for s in seeds]
    return aggregate(recs, keys)


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


def _seed_list(sc: dict) -> list[int]:
    try:
        return [int(s) for s in sc.get("meta", {}).get("seeds", []) or []]
    except (TypeError, ValueError):
        return []


def is_paired(baseline: dict, new: dict) -> bool:
    """True when both scorecards ran the same (non-empty) seed list.

    Scenario draws depend only on (scenario, seed), so equal seed lists mean identical
    subjects, rigs and detections in both runs: common random numbers
    (validation-test-bed.md "compare settings with common random numbers and paired tests").
    """
    sb = _seed_list(baseline)
    return bool(sb) and sb == _seed_list(new)


def _metric_tolerance(b: float, mad_b: float, n_b: int, n_new: int, paired: bool,
                      rel_tol: float, mad_k: float) -> float:
    """Allowed worsening of a median (see :func:`compare`)."""
    tol = rel_tol * abs(b)
    if not (math.isfinite(mad_b) and mad_k > 0.0):
        return tol
    n_b, n_new = max(n_b, 1), max(n_new, 1)
    if paired:
        # Same seeds: only seeds usable in one run but not the other move the median,
        # each by at most ~half an order-statistic gap (~1.86 MAD / n under normality).
        d = abs(n_b - n_new)
        noise = mad_k * d * mad_b / min(n_b, n_new)
    else:
        # Different seed sets: both medians carry seed-sampling noise (~1.86 MAD / sqrt(n)).
        noise = mad_k * mad_b * math.sqrt(1.0 / n_b + 1.0 / n_new)
    return max(tol, noise)


def compare(baseline: dict, new: dict, rel_tol: float = 0.02, mad_k: float = 3.0,
            higher_is_worse: Sequence[str] = HIGHER_IS_WORSE, paired: bool | None = None
            ) -> list[str]:
    """Return the ``'scenario:metric'`` entries of ``new`` that regressed against ``baseline``.

    Only scenarios present in both are compared (a fast run checks a subset). For each
    metric in ``higher_is_worse`` with finite medians b (baseline) and m (new), the entry
    regresses when ``m - b > max(rel_tol * |b|, noise)``.

    * **Paired** comparison (the default whenever possible). With ``paired=None`` a
      scenario is compared paired when both cards ran the same seeds (:func:`is_paired`,
      e.g. a 30-seed run against the 30-seed baseline), or else when both store
      ``per_seed`` values for some shared seeds; the medians are then recomputed over the
      shared seeds only (e.g. a ``--fast`` run on seeds 1000-1004 against the baseline's
      seeds 1000-1004). Common random numbers remove seed-sampling noise, and a
      deterministic engine reproduces the medians exactly, so the gate is the DESIGN 7.5
      promotion rule: no worsening beyond ``rel_tol`` = 2 %. The only noise term left
      covers seeds usable in one run but not the other (e.g. the BLAS-thread-dependent
      failure in the module docstring): ``noise = mad_k * d * MAD_b / n`` with
      d = |n_ok_b - n_ok_new| (dropping d of n seeds shifts a median by about d/2
      order-statistic gaps, ~1.86 d MAD / n under normality). With equal n_ok the gate
      is exactly 2 %.
    * **Unpaired** (no shared seeds, or ``paired=False``): both medians also carry
      seed-sampling noise, so ``noise = mad_k * MAD_b * sqrt(1/n_ok_b + 1/n_ok_new)``
      (MAD / sqrt(n) is the noise scale of a median up to the factor
      1.4826 * 1.2533 ~= 1.86 under normality; validation-test-bed.md "medians vs stored
      baselines +/- 3 MAD over 30 seeds").

    ``paired=True`` treats the stored aggregates as paired even when the seed lists
    differ. ``mad_k=0`` gives the strict ``rel_tol`` rule in every mode. A metric that
    has a finite baseline median but none in ``new`` also regresses.

    Additionally ``'scenario:n_ok'`` is reported when the fraction of seeds with a finite
    ``config_rms_mm`` drops by more than :data:`N_OK_FRACTION_DROP`.
    """
    out: list[str] = []
    bs = baseline.get("scenarios", {})
    ns = new.get("scenarios", {})
    same_seeds = is_paired(baseline, new)
    n_seeds_b0 = len(_seed_list(baseline)) or None
    n_seeds_n0 = len(_seed_list(new)) or None
    ref = "config_rms_mm"
    for name in sorted(set(bs) & set(ns)):
        bm, nm = bs[name], ns[name]
        n_seeds_b, n_seeds_n = n_seeds_b0, n_seeds_n0
        pair = bool(paired) if paired is not None else same_seeds
        if paired is not False and not same_seeds:
            shared = _shared_seeds(baseline, new, name)
            if shared:
                keys = list(dict.fromkeys(list(higher_is_worse) + [ref]))
                bm = _subset_aggregate(baseline, name, shared, keys)
                nm = _subset_aggregate(new, name, shared, keys)
                n_seeds_b = n_seeds_n = len(shared)
                pair = True
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
            tol = _metric_tolerance(b, _as_float(bm[metric].get("mad")),
                                    int(bm[metric].get("n_ok") or 0),
                                    int(nm[metric].get("n_ok") or 0), pair,
                                    float(rel_tol), float(mad_k))
            if m - b > tol:
                out.append("%s:%s" % (name, metric))
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

    if not blas_single_threaded():
        print("note: BLAS threads not pinned to 1 (%s); the committed baseline was generated with "
              "OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1, and camera_roll_legacy "
              "differs slightly otherwise (see module docstring)"
              % ", ".join("%s=%s" % kv for kv in blas_thread_env().items()), file=sys.stderr)
    t0 = time.perf_counter()
    sc = build_scorecard([SCENARIOS[n] for n in names], n_seeds, default_engine,
                         args.engine_label or _default_label(), git_rev=args.git_rev,
                         include_runtime=args.with_runtime, progress=progress)
    write_scorecard(sc, args.out)
    print("\n".join(_summary_lines(sc)))
    print("wrote %s (%d scenarios x %d seeds) in %.1f s"
          % (args.out, len(names), n_seeds, time.perf_counter() - t0))
    if args.compare:
        base = load_scorecard(args.compare)
        reg = compare(base, sc)
        if is_paired(base, sc):
            mode = "paired (same seeds): 2 % rule"
        elif any(_shared_seeds(base, sc, n) for n in sc["scenarios"]):
            mode = "paired on the shared seeds (per_seed): 2 % rule"
        else:
            mode = "unpaired (no shared seeds): 2 % or seed-noise rule"
        print("comparison: " + mode)
        print("regressions: %s" % (", ".join(reg) if reg else "none"))
        return 1 if reg else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
