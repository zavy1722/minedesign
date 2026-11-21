"""WP-23 release gate: the DESIGN 7.5 honesty metrics through ``face3d.pipeline`` (H12), and the
scorecard-v1 promotion check against the committed baseline.

Runs share the harness, the seeds and the memoised pipeline runs of ``tests/test_fault_matrix.py``
(clean studio-ring sets of WP-11 out-of-prior surface subjects; the 'Definition bias 1 mm' row).  Every
number is the one the pipeline reports: the landmark covariance is rebuilt from the observe stage's own
Sigma1, bias form, calibration chi2_red / gamma and factor, and its diagonal is asserted equal to
``observe['sigma_rep_mm']``^2 (``test_fault_matrix.honesty_of``); per-vertex ``sigma_n`` comes from the
``uncertainty`` stage; the scale z uses ``observe['scale']``.

As shipped (WP-23; docs/RESULTS.md 4.1, 4.2): sigma_rep with the FU-02 factor
max(gamma^2, min(1, chi2_red / kappa), chi2_red, 0.5), chi2_red and gamma against the noise before the QA
sigma multipliers (``pipeline.sigma_rep_deflate``; a recorded deviation from DESIGN D-16 / 4.13), and
sigma_n from ``cov_shape`` x that factor + (``pipeline.sigma_res_scale`` x sigma_res)^2.  The same
covariance under the DESIGN factor max(1, gamma^2, chi2_red) is reported as 'info' (never gated).

Gates (DESIGN 7.5; WBS WP-23 item 4)
------------------------------------
* ``vertex.coverage``: in *measured* regions, 0.90-0.99 of the vertices have |normal error| <= 1.96 sigma_n.
* ``landmark.nees`` / ``landmark.coverage_1s``: gauge-projected NEES/dof in [0.8, 1.25] and aligned 1-sigma
  coverage in [0.60, 0.76] with a 1 mm definition bias.
* ``false_confidence``: <= 5 % of the *measured* landmark regions have an error above 2 x their target.
* ``likeness.labels_invariant``: labels, k, sigma_rep, coverage, focal statuses and tier do not change in
  likeness mode (H2), on every seed, while the widened solve assessed on its own would report different
  numbers (so the check is not vacuous).
* ``scale.z_rms``: RMS of z = (zeta_hat - zeta) / sigma_zeta in [0.8, 1.25].

Each band has an *honesty* side (the report must never be over-confident: coverage not below the band,
NEES not above it), asserted as separate 'honesty' gates.  A gate that is not met may only be listed in
:data:`HONESTY_PENDING` with the measured value and a docs/RESULTS.md entry (empty today); the release run
fails if a pending gate starts to pass (the list cannot go stale).

Sampling slack of the 5-seed per-push subset only: rates by the binomial 95 % bound, NEES and the scale
z RMS by the chi-square 95 % interval (:func:`chi2_band`), the vertex coverage (vertices of one set are
strongly correlated) by 1.96 standard errors of the per-set coverage (:func:`cluster_halfwidth`).  The
>= 30-seed release run (``-m slow``) uses the DESIGN bands as written and point estimates throughout.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from face3d.testbed import scorecard as SC
from face3d.testbed.scenarios import SCENARIOS

import test_fault_matrix as FM
from test_fault_matrix import CLEAN, FAST_SEEDS, SLOW_SEEDS, Gate, _ge, _le, _rate, collect, failed_gates

REPO = Path(__file__).resolve().parents[1]
GOLDEN = Path(__file__).parent / "golden"
BASELINE = GOLDEN / "baseline_scorecard_v0.json"
SCORECARD_V1 = GOLDEN / "scorecard_v1.json"

# DESIGN 7.5 bands (validation-test-bed; badge new)
VERTEX_COVERAGE = (0.90, 0.99)
LM_COVERAGE_1S = (0.60, 0.76)
NEES_BAND = (0.8, 1.25)
FALSE_CONFIDENCE_MAX = 0.05
SCALE_Z_RMS = (0.8, 1.25)
#: Gates not met today: name -> reason (each must be listed in docs/RESULTS.md).  Empty since WP-23 enabled
#: the FU-02 factor in the observe stage and recalibrated the per-vertex sigma_n (docs/RESULTS.md 4.1, 4.2).
HONESTY_PENDING: dict = {}


def cluster_halfwidth(per_set) -> float:
    """1.96 standard errors of the mean of per-set rates (the photo set is the sampling unit: the vertices
    of one set share one solve); the per-push slack of the vertex-coverage band."""
    x = np.asarray(list(per_set), float)
    return float(1.96 * x.std(ddof=1) / math.sqrt(x.size)) if x.size > 1 else float("inf")


def chi2_quantile(z: float, dof: int) -> float:
    """Wilson-Hilferty chi-square quantile at standard-normal deviate ``z``."""
    a = 2.0 / (9.0 * dof)
    return dof * (1.0 - a + z * math.sqrt(a)) ** 3


def chi2_band(dof: int) -> tuple:
    """95 % interval of chi2(dof) / dof: the sampling factor of a mean of ``dof`` unit-variance squares."""
    return chi2_quantile(-1.96, dof) / dof, chi2_quantile(1.96, dof) / dof


# ============================================================================ measurement
def honesty(seeds) -> dict:
    """The honesty counts over ``seeds`` (memoised pipeline runs of the fault-matrix harness)."""
    seeds = list(seeds)
    clean = collect([("clean", s, CLEAN) for s in seeds])
    bias = collect([("bias", s, {}) for s in seeds])
    like = [r["likeness"] for r in clean]
    nv = sum(r["n_vert"] for r in clean)
    out: dict = {"n_seeds": len(seeds)}
    curve = {}
    for key in (clean[0].get("recal") or {}):
        rc = [r["recal"][key] for r in clean if "recal" in r]
        curve[key] = {"coverage": sum(x[0] for x in rc) / max(1, nv), "z_rms": math.sqrt(sum(x[1] for x in rc) / max(1, nv)),
                      "sigma_n_median_mm": float(np.median([x[2] for x in rc]))}
    out["vertex"] = {
        "n": nv, "n_in": sum(r["n_vert_in"] for r in clean),
        "per_set_coverage": [r["n_vert_in"] / r["n_vert"] for r in clean if r["n_vert"]],
        "z_rms": math.sqrt(sum(r["sum_z2"] for r in clean) / max(1, nv)),
        "sigma_n_median_mm": float(np.median([r["sigma_n_median"] for r in clean if r["sigma_n_median"]])),
        "abs_err_median_mm": float(np.median([r["abs_err_median"] for r in clean if r["abs_err_median"]])),
        "sets_with_measured_vertices": sum(r["n_vert"] > 0 for r in clean),
        "measured_kit_regions": FM._count([k for r in clean for k in r["measured_kit_regions"]]),
        "fit_stage": FM._count([r["fit_stage"] for r in clean]),
        "sigma_res_scale": FM._count([r.get("sigma_res_scale") for r in clean]), "curve": curve}
    out["landmark_bias"] = FM._pooled_honesty(bias)
    out["landmark_bias"]["n_coords"] = sum(r["honesty"]["n_z"] for r in bias)
    out["landmark_bias"]["n_in_1s"] = sum(r["honesty"]["n_in_1s"] for r in bias)
    out["landmark_bias"]["dof"] = sum(r["honesty"]["dof"] for r in bias)
    out["landmark_bias"]["nees_max_set"] = float(max(r["honesty"]["nees"] for r in bias))
    out["landmark_bias"]["inflation_median"] = float(np.median([r["inflation"] for r in bias]))
    out["landmark_clean"] = FM._pooled_honesty(clean)
    reg = [x for r in clean for x in r["measured_regions"]]
    out["false_confidence"] = {"n_measured_regions": len(reg), "over_2x_target": sum(x[1] > 2.0 * x[2] for x in reg),
                               "regions": FM._count([x[0] for x in reg]),
                               "worst_ratio": float(max([x[1] / x[2] for x in reg], default=float("nan")))}
    z = np.array([r["scale_z"] for r in clean], float)
    out["scale"] = {"n": int(z.size), "z_rms": float(np.sqrt(np.mean(z ** 2))), "z_mean": float(z.mean()),
                    "sigma_zeta_median": float(np.median([r["scale_sigma"] for r in clean]))}
    out["likeness"] = {"n": len(like), "all_same": sum(all(r["same"].values()) for r in like),
                       "flagged": sum(r["flagged"] for r in like),
                       "refused_without_standard": sum(r["refused_without_standard"] for r in like),
                       "widened": sum(r["rounds"] >= 1 for r in like),
                       "own_differs": sum(r["own_differs"] for r in like),
                       "own_labels_differ": sum(r["own_labels_differ"] for r in like),
                       "own_sigma_rep_rel_change_median": float(np.median(
                           [r["own_sigma_rep_rel_change_max"] for r in like])),
                       "label_source": FM._count([r["label_source"] for r in like]),
                       "max_move_mm_median": float(np.median([r["max_move_mm"] for r in like]))}
    return out


def honesty_gates(h: dict, relax: bool = False) -> list:
    """The DESIGN 7.5 gates on ``h`` = :func:`honesty`.  ``relax`` (per-push subset) applies the sampling
    intervals of the module docstring."""
    G: list = []

    def add(name, kind, target, measured, ok):
        ok, met = ok if isinstance(ok, tuple) else (ok, ok)
        G.append(Gate(name, name.split(".")[0], kind, target, measured, bool(ok), bool(met)))

    v = h["vertex"]
    cov = v["n_in"] / max(1, v["n"])
    lo, hi = VERTEX_COVERAGE
    hw = cluster_halfwidth(v["per_set_coverage"]) if relax else 0.0
    add("vertex.coverage", "design", f"{lo}-{hi} of measured-region vertices within 1.96 sigma_n",
        f"{cov:.4f} over {v['n']} vertices (z RMS {v['z_rms']:.2f}; median sigma_n {v['sigma_n_median_mm']:.1f} mm vs "
        f"median abs error {v['abs_err_median_mm']:.1f} mm)",
        (v["n"] > 0 and lo - hw <= cov <= hi + hw, v["n"] > 0 and lo <= cov <= hi))
    add("vertex.not_overconfident", "honesty", f"coverage >= {lo}", f"{cov:.4f}", v["n"] > 0 and cov >= lo)
    old = v["curve"].get("full:1")
    if old is not None:
        add("vertex.pre_wp23", "info", "sigma_n as before WP-23 (`cov`, DESIGN factor, sigma_res x 1), same vertices",
            f"{old['coverage']:.4f} (z RMS {old['z_rms']:.2f}; median sigma_n {old['sigma_n_median_mm']:.1f} mm)", True)

    b = h["landmark_bias"]
    nlo, nhi = NEES_BAND
    f_lo, f_hi = chi2_band(b["dof"]) if relax else (1.0, 1.0)
    add("landmark.nees", "design", f"NEES/dof in [{nlo}, {nhi}] with 1 mm definition bias",
        f"{b['nees_per_dof']:.3f} (clean sets {h['landmark_clean']['nees_per_dof']:.3f}; sigma_rep factor median "
        f"{b['inflation_median']:.2f})",
        (nlo * f_lo <= b["nees_per_dof"] <= nhi * f_hi, nlo <= b["nees_per_dof"] <= nhi))
    clo, chi = LM_COVERAGE_1S
    add("landmark.coverage_1s", "design", f"aligned 1-sigma coverage in [{clo}, {chi}] with 1 mm definition bias",
        f"{b['coverage_1s']:.3f} (clean sets {h['landmark_clean']['coverage_1s']:.3f})",
        clo <= b["coverage_1s"] <= chi)
    add("landmark.not_overconfident", "honesty", f"coverage >= {clo} and NEES/dof <= {nhi} (bias row and clean sets)",
        f"{b['coverage_1s']:.3f} / {b['nees_per_dof']:.3f}; {h['landmark_clean']['coverage_1s']:.3f} / "
        f"{h['landmark_clean']['nees_per_dof']:.3f}",
        b["coverage_1s"] >= clo and b["nees_per_dof"] <= nhi * f_hi
        and h["landmark_clean"]["coverage_1s"] >= clo and h["landmark_clean"]["nees_per_dof"] <= nhi * f_hi)
    add("landmark.design_factor", "info", "the same covariance under the DESIGN 4.13 factor max(1, gamma^2, chi2_red) "
        "(not shipped)", f"NEES/dof {b['nees_per_dof_design']:.3f}, coverage {b['coverage_1s_design']:.3f}", True)

    fc = h["false_confidence"]
    add("false_confidence", "design", f"<= {FALSE_CONFIDENCE_MAX} of measured regions above 2 x their target",
        f"{_rate(fc['over_2x_target'], fc['n_measured_regions'])} {fc['regions']} (worst error/target "
        f"{fc['worst_ratio']:.2f})", _le(fc["over_2x_target"], fc["n_measured_regions"], FALSE_CONFIDENCE_MAX))

    lk = h["likeness"]
    add("likeness.labels_invariant", "design", "labels, k, sigma_rep, coverage, focal status and tier identical "
        "in likeness mode (H2), and not vacuously", f"{lk['all_same']}/{lk['n']} identical to the pipeline's report; "
        f"widened solve moved landmarks by up to {lk['max_move_mm_median']:.1f} mm (median); assessed on its own it "
        f"would report different sigma_rep / k in {lk['own_differs']}/{lk['n']} sets (sigma_rep by up to "
        f"{100 * lk['own_sigma_rep_rel_change_median']:.0f} %, median; labels in {lk['own_labels_differ']}); refused "
        f"without the standard solve {lk['refused_without_standard']}/{lk['n']}",
        lk["n"] > 0 and lk["all_same"] == lk["n"] and lk["flagged"] == lk["n"]
        and lk["refused_without_standard"] == lk["n"] and lk["widened"] == lk["n"]
        and lk["own_differs"] == lk["n"] and lk["label_source"] == {"standard_result": lk["n"]})

    sc = h["scale"]
    slo, shi = SCALE_Z_RMS
    f_lo, f_hi = (math.sqrt(x) for x in chi2_band(sc["n"])) if relax else (1.0, 1.0)
    add("scale.z_rms", "design", f"scale z RMS in [{slo}, {shi}]",
        f"{sc['z_rms']:.3f} over {sc['n']} sets (mean z {sc['z_mean']:+.2f}; median sigma_zeta "
        f"{sc['sigma_zeta_median']:.3f})", (slo * f_lo <= sc["z_rms"] <= shi * f_hi, slo <= sc["z_rms"] <= shi))
    return G


def honesty_report(h: dict, relax: bool = False) -> str:
    lines = ["| Gate | Kind | Target | Measured | Status |", "|---|---|---|---|---|"]
    for g in honesty_gates(h, relax):
        lines.append(f"| `{g.name}` | {g.kind} | {g.target} | {g.measured} | "
                     f"{FM.status_of(g, pending=HONESTY_PENDING, strict=not relax)} |")
    return "\n".join(lines)


def curve_report(h: dict) -> str:
    """The sigma_n calibration curve of docs/RESULTS.md 4.2."""
    lines = ["| sigma_res scale | landmark covariance x factor | coverage at 1.96 sigma_n | z RMS | median sigma_n (mm) |",
             "|---|---|---|---|---|"]
    names = {"full": "`cov` x DESIGN factor (pre-WP-23)", "shape": "`cov_shape` x sigma_rep factor"}
    for key in sorted(h["vertex"]["curve"], key=lambda k: (k.split(":")[0], -float(k.split(":")[1]))):
        c = h["vertex"]["curve"][key]
        kind, scale = key.split(":")
        lines.append(f"| {scale} | {names[kind]} | {c['coverage']:.4f} | {c['z_rms']:.2f} | {c['sigma_n_median_mm']:.1f} |")
    return "\n".join(lines)


# ============================================================================ tests
def test_chi2_band():
    lo, hi = chi2_band(30)
    assert lo == pytest.approx(16.79 / 30, abs=0.01) and hi == pytest.approx(46.98 / 30, abs=0.01)
    lo, hi = chi2_band(5)
    assert lo == pytest.approx(0.831 / 5, abs=0.02) and hi == pytest.approx(12.83 / 5, abs=0.02)


def test_cluster_halfwidth():
    assert cluster_halfwidth([0.98, 0.99, 1.0, 0.97, 0.96]) == pytest.approx(1.96 * 0.0158114 / math.sqrt(5), rel=1e-4)
    assert cluster_halfwidth([0.9]) == float("inf")


def test_calibration_noise_removes_the_qa_multiplier():
    """Regression (FU-02 release blocker): the observe stage calibrates sigma_rep against the noise before
    the QA sigma multipliers.  A view solved with its sigma x m has whitened residuals 1 / m of those
    against the declared noise; :func:`face3d.pipeline.stages._calibration_noise` undoes exactly that."""
    from types import SimpleNamespace
    from face3d.pipeline import stages as S
    rng = np.random.default_rng(5)
    n = 12
    cov = [np.tile(np.eye(2) * s2, (n, 1, 1)) for s2 in (4.0, 16.0, 4.0)]      # view 1 carries m = 2 (sigma 2 -> 4)
    resid = [rng.uniform(1.0, 3.0, n) for _ in range(3)]
    inl = [np.ones(n, bool) for _ in range(3)]
    inl[2][:3] = False
    res = SimpleNamespace(chi2_red=0.6, obs_cov_px=cov, per_view_residuals=resid, inlier_mask=inl)
    chi, base = S._calibration_noise(res, [1.0, 1.0, 1.0])
    assert chi == 0.6 and all(a is b for a, b in zip(base, cov))                # no multiplier: untouched
    chi, base = S._calibration_noise(res, [1.0, 2.0, 1.0])
    q = [float((r[m] ** 2 / c[m, 0, 0]).sum()) for r, c, m in zip(resid, cov, inl)]
    assert chi == pytest.approx(0.6 * (q[0] + 4.0 * q[1] + q[2]) / sum(q))
    assert np.allclose(base[1], cov[1] / 4.0) and np.allclose(base[0], cov[0]) and 0.6 < chi < 2.4
    chi, _ = S._calibration_noise(res, [2.0, 2.0, 2.0])
    assert chi == pytest.approx(2.4)                                            # every view x2: chi2_red x4
    # the registered defaults behind the shipped behaviour
    assert S.PIPELINE["sigma_rep_deflate"].value is True
    lo, hi = S.PIPELINE["sigma_res_scale"].bounds
    assert lo <= S.PIPELINE["sigma_res_scale"].value <= hi == 1.0


def test_honesty_gates_fast_subset():
    """Per-push: 5 seeds.  Every gate holds within the sampling slack of the module docstring, the honesty
    side of every band without it; nothing is pending (or it is documented in docs/RESULTS.md)."""
    h = honesty(FAST_SEEDS)
    G = honesty_gates(h, relax=True)
    assert {g.name for g in G} >= set(HONESTY_PENDING)
    assert all(g.ok for g in G if g.kind == "honesty"), [g for g in G if not g.ok]
    assert failed_gates(G, pending=HONESTY_PENDING) == []
    assert h["vertex"]["sets_with_measured_vertices"] == len(FAST_SEEDS) and h["vertex"]["n"] > 500
    assert h["vertex"]["fit_stage"] == {"C": len(FAST_SEEDS)}
    assert h["false_confidence"]["n_measured_regions"] >= len(FAST_SEEDS)
    assert h["likeness"]["n"] == len(FAST_SEEDS)
    # FU-02 option (i) and the WP-19 recalibration are what the pipeline ships (regression: WP-23 review)
    lm = {g.name: g for g in G}
    assert lm["landmark.coverage_1s"].ok and lm["landmark.nees"].ok and lm["vertex.coverage"].ok
    assert h["landmark_bias"]["inflation_median"] < 1.0
    assert h["vertex"]["curve"]["full:1"]["coverage"] >= h["vertex"]["n_in"] / h["vertex"]["n"]
    results = (REPO / "docs" / "RESULTS.md").read_text()
    for name in HONESTY_PENDING:
        assert f"`{name}`" in results, f"{name} is pending but not listed in docs/RESULTS.md"


@pytest.mark.slow
def test_honesty_gates_release_run():
    """Release run: >= 30 seeds (likeness mode on every one), the DESIGN 7.5 bands as written, point
    estimates (no binomial or chi-square slack)."""
    h = honesty(SLOW_SEEDS)
    assert h["n_seeds"] >= 30 and h["likeness"]["n"] >= 30
    G = honesty_gates(h)
    assert all(g.ok and g.met for g in G if g.kind == "honesty"), [g for g in G if not g.ok]
    assert failed_gates(G, strict=True, pending=HONESTY_PENDING) == []
    stale = [g.name for g in G if g.ok and g.met and g.name in HONESTY_PENDING]
    assert stale == [], f"these gates now pass: remove them from HONESTY_PENDING and update RESULTS.md: {stale}"


# ---------------------------------------------------------------------------- scorecard v1 (DESIGN 7.5 promotion)
#: The baseline scorecard records no likeness-weighted error (E_like needs per-region errors, which the
#: v0 card of the legacy engine did not store and which cannot be regenerated without that engine), so the
#: shape metrics it does record are compared: configuration RMS and the NoW-7 aligned RMS.
SHAPE_METRICS = ("config_rms_mm", "now7_rms_mm")
#: secondary metrics that are worse than the baseline by more than 2 % (reported in docs/RESULTS.md; neither
#: is a shape metric: a camera distance and a reprojection residual)
KNOWN_SECONDARY_REGRESSIONS = ("rear_phone_smooth:distance_rel_err", "selfie_legacy:rmse_px")


def test_scorecard_v1_not_worse_than_baseline():
    """The committed scorecard v1 (v2 engine, the baseline's scenarios and seeds) shows no legacy-scenario
    regression beyond 2 % in the shape metrics (seed-matched medians, DESIGN 7.5 promotion rule)."""
    base, new = SC.load_scorecard(BASELINE), SC.load_scorecard(SCORECARD_V1)
    assert new["meta"]["engine_label"] == "v2" and new["meta"]["provenance"] == "synthetic"
    assert new["meta"]["seeds"] == base["meta"]["seeds"] and len(new["meta"]["seeds"]) >= 30
    assert set(new["scenarios"]) == set(base["scenarios"]) == set(SCENARIOS)
    assert new["meta"]["scenario_defs"] == base["meta"]["scenario_defs"]
    assert SC.is_paired(base, new)
    reg = SC.compare(base, new, rel_tol=0.02)
    assert [r for r in reg if r.split(":")[1] in SHAPE_METRICS + ("n_ok",)] == []
    assert sorted(reg) == sorted(KNOWN_SECONDARY_REGRESSIONS)          # nothing else regressed, none hidden
    for name in new["scenarios"]:
        for metric in SHAPE_METRICS:
            pm = SC.paired_medians(base, new, name, metric)
            assert pm["n_both"] == 30 and pm["new"] <= 1.02 * pm["baseline"], (name, metric, pm)
        assert new["scenarios"][name]["config_rms_mm"]["n_ok"] == 30    # no failed seed
    results = (REPO / "docs" / "RESULTS.md").read_text()
    for r in KNOWN_SECONDARY_REGRESSIONS:
        assert f"`{r}`" in results


def test_scorecard_v1_is_reproducible():
    """The committed card is what the engine produces: 3 seeds of one scenario re-run and compared with
    the stored per-seed values."""
    new = SC.load_scorecard(SCORECARD_V1)
    name = "rear_phone_legacy"
    again = SC.build_scorecard([SCENARIOS[name]], 3, engine_label="v2", git_rev="test")
    for metric in SHAPE_METRICS + ("focal_rel_err",):
        a = np.array(again["per_seed"][name][metric], float)
        b = np.array(new["per_seed"][name][metric][:3], float)
        assert np.allclose(a, b, rtol=1e-5, atol=1e-9), (metric, a, b)
    assert json.loads(SCORECARD_V1.read_text())["meta"]["format"] == SC.SCORECARD_FORMAT


if __name__ == "__main__":      # regenerate the honesty tables of docs/RESULTS.md
    _h = honesty(SLOW_SEEDS)
    print(honesty_report(_h))
    print(curve_report(_h))
    print(json.dumps(_h, indent=1, sort_keys=True))
