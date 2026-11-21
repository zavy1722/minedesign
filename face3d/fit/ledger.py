"""Claims ledger: per-region evidence states, tier, scale and the plain-language report.

Implements DESIGN D-16 (four states computed at prior weight 1), D-17 (tiers and the
"not validated against a scan" banner) and the honesty contract of DESIGN section 5:
H1 (every number carries sigma_rep and a basis, worded plainly), H2 (labels at prior
weight 1: the ledger only reads outputs of :mod:`face3d.solve.observability`, which
computes them from the prior-weight-1 posterior), H4 (scale printed with its mode and
+/- %), H5 (focal 'measured' only when sigma_post(ln f) < 0.10), H8 (tier, count of
active unverified defaults, banner, no claim finer than the reference modality) and H9
(prior-driven regions listed with the photo that would measure them).  WBS WP-16.

Inputs come from :func:`face3d.solve.observability.assess` (a dict); the region-level
next-photo advice follows the coverage rule that failed (DESIGN 4.12), and the overall
next-best photo sentence from :func:`face3d.solve.nbv.next_best_view` can be attached.

Conventions: millimetres; sigma values are 1-sigma ``sigma_rep`` (DESIGN 4.13) as the RMS
over a region's coordinates (:func:`face3d.solve.observability.region_sigma_rep`);
statuses ``'measured' | 'constrained' | 'prior-driven' | 'unobserved'``; support k in
[0, 1] (1 = data-determined).  numpy + stdlib only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

from ..core.config import Default, register_defaults, unverified_count
from ..solve.observability import (REGION_COVERAGE_RULES, REGION_ORDER, REGION_TARGET_MM, coverage_ok,
                                   default_region_index)

__all__ = ["LEDGER", "BANNER", "RegionClaim", "ClaimsLedger", "build_ledger", "vertex_support", "report_lines",
           "KIT_REGION_MAP", "REGION_LABELS"]

_BRAIN = "\U0001F9E0"

LEDGER = register_defaults("ledger", {
    # DESIGN H8: "No claim is finer than the reference modality (0.2-1 mm, bl Q4)".
    "report_floor_mm": Default(0.2, _BRAIN, "DESIGN H8: no claim finer than the reference modality 0.2-1 mm "
                               "(bl Q4); lower end", "mm", (0.0, None)),
})

#: DESIGN D-17 / H8: printed on every report until the M7 calibration passes.
BANNER = "Not validated against a scan."

#: Display names of the ledger regions.
REGION_LABELS: dict[str, str] = {
    "eyes": "Eyes", "brows": "Brows", "lips": "Lips", "nose": "Nose", "nose_projection": "Nose projection",
    "cheeks": "Cheeks", "forehead": "Forehead", "chin": "Chin", "chin_projection": "Chin projection",
    "jaw": "Jaw", "ears": "Ears", "cranium": "Cranium",
}

#: Template-kit vertex regions -> ledger regions (the vertex takes the smallest k of the
#: listed regions present, so a nose vertex is only as supported as the nose projection;
#: 'neck' and 'other' have no landmarks and get k = 0, i.e. guessed and sculptable).
KIT_REGION_MAP: dict[str, tuple[str, ...]] = {
    "eyes": ("eyes",), "nose": ("nose", "nose_projection"), "lips": ("lips",), "chin": ("chin", "chin_projection"),
    "ears": ("ears",), "jaw": ("jaw",), "cheeks": ("cheeks",), "forehead": ("forehead", "brows"),
    "scalp": ("cranium",), "neck": (), "other": (),
}

# Advice for the first failing coverage rule (DESIGN 4.12 rules; H9).
_ADVICE: dict[str, str] = {
    "projection": "take a left or right profile",
    "depth": "take a three-quarter view (about 45 degrees to one side)",
    "jaw_underside": "take a photo from below, camera at chin height looking up",
    "ears": "take a side view at eye height and one from slightly above or below",
}
_RULE_ORDER = ("projection", "depth", "jaw_underside", "ears")

_SCALE_LABELS = {"measured": "caliper/card", "iris": "iris+population", "prior": "population prior"}
_FOCAL_WORDS = {"measured": "measured", "partial": "partly measured", "prior_used": "from prior"}


@dataclass
class RegionClaim:
    """One region of the ledger (DESIGN D-16).

    ``k``: evidence at prior weight 1; ``sigma_rep_mm``: region RMS of sigma_rep (1 sigma);
    ``coverage``: the region's coverage-rule booleans; ``why_key``: message key explaining
    the status (``ledger.why.*``); ``next_photo``: advice for regions not measured.
    """

    name: str
    status: str
    k: float
    sigma_rep_mm: float
    coverage: dict
    why_key: str
    next_photo: str | None = None


@dataclass
class ClaimsLedger:
    """The claims ledger of one solve (DESIGN D-16, D-17, H1-H9)."""

    regions: list[RegionClaim]
    tier: tuple[str, str]
    scale_report: str
    focal_statuses: list[str]
    banner: str = BANNER
    unverified_defaults: int = 0
    next_photo: str | None = None
    flags: list[str] = field(default_factory=list)
    gamma: float | None = None

    def region(self, name: str) -> RegionClaim:
        for r in self.regions:
            if r.name == name:
                return r
        raise KeyError(name)

    def statuses(self) -> dict[str, str]:
        return {r.name: r.status for r in self.regions}


def _why(status: str, k: float, cov_ok: bool, sigma: float, target: float, capped: str | None) -> str:
    if status == "unobserved":
        return "ledger.why.unobserved"
    if status == "measured":
        return "ledger.why.measured"
    if capped == "design_d31":
        return "ledger.why.not_modelled"
    if capped:
        return "ledger.why.tagged"
    if not cov_ok:
        return "ledger.why.coverage_missing" if status == "constrained" else "ledger.why.prior_no_coverage"
    if status == "constrained":
        return "ledger.why.sigma_above_target" if sigma > target else "ledger.why.partial_evidence"
    return "ledger.why.prior_low_evidence"


def _advice(region: str, rules: Mapping[str, bool], status: str, nbv_sentence: str | None,
            capped: str | None = None) -> str | None:
    if status == "measured":
        return None
    if status == "unobserved" or not rules.get("observed", False):
        return f"take a photo that shows the {REGION_LABELS.get(region, region).lower()}"
    if capped == "design_d31":
        return "shape not fitted in this version; sculpt it from a side photo"
    need = REGION_COVERAGE_RULES.get(region, ("depth",))
    for rule in _RULE_ORDER:
        if rule in need and not rules.get(rule, False):
            return _ADVICE[rule]
    if nbv_sentence:
        s = nbv_sentence[len("Next: "):] if nbv_sentence.startswith("Next: ") else nbv_sentence
        return f"next-best photo: {s}"
    return "add a photo from a different angle"


def _scale_report(scale: Mapping[str, Any] | str | None, result: Any, prior: Any) -> str:
    if isinstance(scale, str) or scale is None:
        scale = {"mode": scale or "prior"}
    mode = str(scale.get("mode", "prior"))
    pct = scale.get("sigma_pct")
    if pct is None:
        sl = scale.get("sigma_log")
        if sl is None:
            sl = getattr(result, "zeta_sigma", None)
        if sl is None and prior is not None:
            sl = (getattr(prior, "meta", None) or {}).get("scale_sigma_log")
        pct = None if sl is None else 100.0 * (float(np.exp(float(sl))) - 1.0)
    label = _SCALE_LABELS.get(mode, mode)
    if pct is None:
        return f"Scale: {label}, uncertainty unknown"
    return f"Scale: {label} +/-{float(pct):.1f} %"


def build_ledger(result: Any, prior: Any, registry: Any, observability: Mapping[str, Any], *,
                 next_photo: str | None = None, flags: Sequence[str] = ()) -> ClaimsLedger:
    """Assemble the claims ledger (DESIGN D-16, D-17, H1-H9).

    ``result``: the ``BundleResult`` (zeta_sigma for the scale line); ``prior``: the
    landmark prior (fallback scale sigma, ``meta['scale_sigma_log']``); ``registry``: the
    landmark ids (a sequence, or a mapping such as ``registry.ANATOMICAL`` whose keys are
    the ids in order), used for the region index when ``observability`` has none;
    ``observability``: the dict of :func:`face3d.solve.observability.assess` (keys
    ``region_k``, ``coverage``, ``region_sigma_rep_mm``, ``region_status``, ``tier``,
    ``focal_statuses``, ``scale``, optional ``targets``, ``gamma``, ``status_caps``,
    ``cap_reasons``; a region capped by DESIGN D-31 (ears) reads 'shape not fitted in this
    version').
    ``next_photo``: the next-best photo sentence (:func:`face3d.solve.nbv.next_best_view`),
    also used as advice for regions whose coverage holds but whose evidence is weak.
    ``unverified_defaults`` is :func:`face3d.core.config.unverified_count` (H8).
    """
    obs = observability
    region_index = obs.get("region_index")
    if region_index is None:
        ids = list(registry.keys()) if isinstance(registry, Mapping) else list(registry or [])
        region_index = default_region_index(ids)
    kk = obs["region_k"]
    cov = obs["coverage"]
    rs = obs["region_sigma_rep_mm"]
    st = obs["region_status"]
    tg = dict(REGION_TARGET_MM)
    tg.update(obs.get("targets") or {})
    caps = obs.get("status_caps") or {}
    reasons = dict(obs.get("cap_reasons") or {})
    for r in caps:
        reasons.setdefault(r, "tag")
    order = [r for r in REGION_ORDER if r in region_index] + [r for r in region_index if r not in REGION_ORDER]
    claims = []
    for r in order:
        rules = dict(cov.get(r, {}))
        ok = coverage_ok(r, rules)
        status = st[r]
        k = float(kk.get(r, float("nan")))
        sig = float(rs.get(r, float("nan")))
        claims.append(RegionClaim(name=r, status=status, k=k, sigma_rep_mm=sig, coverage=rules,
                                  why_key=_why(status, k, ok, sig, tg.get(r, float("inf")), reasons.get(r)),
                                  next_photo=_advice(r, rules, status, next_photo, reasons.get(r))))
    tier_v = tuple(obs["tier"]) if obs.get("tier") is not None else ("B", "proportions only")
    return ClaimsLedger(regions=claims, tier=(str(tier_v[0]), str(tier_v[1])),
                        scale_report=_scale_report(obs.get("scale"), result, prior),
                        focal_statuses=list(obs.get("focal_statuses") or []), banner=BANNER,
                        unverified_defaults=int(unverified_count()), next_photo=next_photo,
                        flags=list(flags), gamma=None if obs.get("gamma") is None else float(obs["gamma"]))


def vertex_support(kit: Any, ledger: ClaimsLedger) -> np.ndarray:
    """(V,) measurement support k per template vertex, by region (DESIGN 4.17 protect mask).

    Each kit region maps to ledger regions by :data:`KIT_REGION_MAP` (the smallest k of
    those present); unobserved regions, regions whose status was capped (an occluder tag or
    DESIGN D-31 for the ear shape), regions without landmarks and NaN evidence give 0 (the
    claim says the photos do not determine them, so they stay sculptable); values are
    clipped to [0, 1].  ``kit``: a :class:`~face3d.model.template_kit.TemplateKit`
    (``vertex_regions()``) or an object with ``regions`` {name: vertex ids} and ``n_verts``.
    """
    if hasattr(kit, "vertex_regions"):
        names = np.asarray(kit.vertex_regions(), dtype=object)
    else:
        n = int(kit.n_verts)
        names = np.full(n, "other", dtype=object)
        for name, idx in kit.regions.items():
            names[np.asarray(idx, np.int64)] = name
    by = {}
    for c in ledger.regions:
        capped = c.why_key in ("ledger.why.tagged", "ledger.why.not_modelled")
        k = 0.0 if c.status == "unobserved" or capped or not np.isfinite(c.k) else float(np.clip(c.k, 0.0, 1.0))
        by[c.name] = k
    out = np.zeros(len(names))
    for kr in set(names.tolist()):
        targets = [by[r] for r in KIT_REGION_MAP.get(kr, (kr,)) if r in by]
        out[names == kr] = min(targets) if targets else 0.0
    return out


def report_lines(ledger: ClaimsLedger) -> list[str]:
    """Plain-language report (DESIGN H1, H4, H5, H8, H9).

    Lines: the banner; the tier; the scale with its mode and +/- %; the focal status; the
    count of active unverified defaults; one line per region, e.g.
    'Eyes: likely within +/-0.9 mm (measured)' or 'Nose projection: guessed from average
    proportions (prior-driven) - take a left or right profile'; the next-best photo.
    Sigma values are 1-sigma sigma_rep, never shown finer than 0.2 mm (H8).
    """
    floor = float(LEDGER.report_floor_mm.value)
    code, name = ledger.tier
    lines = [ledger.banner, f"Tier {code}: {name}", ledger.scale_report]
    if ledger.focal_statuses:
        counts: dict[str, int] = {}
        for s in ledger.focal_statuses:
            counts[s] = counts.get(s, 0) + 1
        n = len(ledger.focal_statuses)
        parts = [f"{_FOCAL_WORDS.get(s, s)} in {c} of {n} photos" for s, c in counts.items()]
        lines.append("Focal length: " + "; ".join(parts))
    lines.append(f"{ledger.unverified_defaults} defaults are expert estimates not yet calibrated")
    for c in ledger.regions:
        label = REGION_LABELS.get(c.name, c.name.replace("_", " ").capitalize())
        sig = max(float(c.sigma_rep_mm), floor) if np.isfinite(c.sigma_rep_mm) else float("nan")
        if c.status == "measured":
            line = f"{label}: likely within +/-{sig:.1f} mm (measured)"
        elif c.status == "constrained":
            line = f"{label}: likely within +/-{sig:.1f} mm, partly from average proportions (constrained)"
        elif c.status == "prior-driven":
            line = f"{label}: guessed from average proportions (prior-driven)"
        else:
            line = f"{label}: not seen in any photo (unobserved)"
        if c.next_photo and c.status != "measured":
            line += f" - {c.next_photo}"
        lines.append(line)
    if ledger.next_photo:
        lines.append(ledger.next_photo)
    return lines
