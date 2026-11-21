"""Surface error statistics between an estimated and a reference triangle mesh.

Implements the surface metrics of DESIGN §7.3 (rec EV-1/EV-2 in
``research/_raw/requirements_reconstruction.md``; definitions in
``research/reconstruction/benchmarks-metrics.md`` Table 4):

* distances are exact point-to-surface distances
  (:func:`face3d.mesh.distance.point_to_mesh`), never nearest-vertex ones;
* the default direction is **reference → estimate** ("scan-to-surface", the NoW
  protocol: every reference/scan point is measured to the nearest point of the
  predicted surface; benchmarks-metrics "NoW protocol");
* reported: median, mean, std, RMS, p90, p95, F@0.5/1/2 mm (fraction of samples
  within the threshold; DESIGN §7.3), signed bias and per-region statistics;
* alignment is *not* done here: pass meshes already in a common frame (e.g.
  landmark alignment with ``face3d.eval.align.align``; DESIGN §7.3 lists the
  NoW-style, landmark and region alignment modes).

Units are those of the vertices (mm in the engine; DESIGN §2.1).

Sign convention for signed statistics (``signed=True``): values are positive
where the **estimate lies outside the reference** ("too much clay", the sculpt
heat-map convention of benchmarks-metrics "Applying this", item 4), whichever
direction is sampled. For ``est_to_ref`` this is the pseudonormal-signed
distance of the estimate's samples to the reference surface; for
``ref_to_est`` it is minus the signed distance of the reference samples to the
estimate surface. Both meshes must be wound counter-clockwise seen from outside
(see :mod:`face3d.mesh.distance`).
"""
from __future__ import annotations

import numpy as np

from ..mesh.distance import TriangleGrid, point_to_mesh

__all__ = ["surface_error", "chamfer", "likeness_weighted_error", "sample_surface",
           "LIKENESS_WEIGHTS", "F_THRESHOLDS_MM"]

# F@τ thresholds in mm (DESIGN §7.3; rec EV-2).
F_THRESHOLDS_MM = (0.5, 1.0, 2.0)

# Perceptual region weights for the likeness-weighted error E_like (DESIGN §7.3
# and §4.14; research/anatomy/face-perception-likeness.md Table B,
# research/reconstruction/benchmarks-metrics.md Table 6). PROVISIONAL default
# (🧠 expert synthesis, to be recalibrated by DESIGN §7.6 tiers): eyes (lids)
# 1.0, brows 0.9, lips 0.8, nose and nose projection 0.7, jaw 0.5, cheeks 0.4,
# forehead 0.3 and ears 0.15 are the §4.14 values; chin (= jaw), scalp 0.1 and
# neck 0.05 are the WP-02 spec's extensions for regions §4.14 does not list
# (Table B puts ears/cranium at 0.1-0.2 and does not rate the neck).
LIKENESS_WEIGHTS: dict[str, float] = {
    "eyes": 1.0,
    "brows": 0.9,
    "lips": 0.8,
    "nose": 0.7,
    "nose_projection": 0.7,
    "jaw": 0.5,
    "chin": 0.5,
    "cheeks": 0.4,
    "forehead": 0.3,
    "ears": 0.15,
    "scalp": 0.1,
    "neck": 0.05,
}

# Seed used when rng is None, so area-sampled metrics are reproducible
# (DESIGN §2.1 invariant 3: fixed seeds). The default n_samples = 20000 per
# sampled mesh is the WP-02 spec value (sampling error of a mean ≈ σ/141).
_DEFAULT_SEED = 0


def _as_rng(rng) -> np.random.Generator:
    if rng is None:
        return np.random.default_rng(_DEFAULT_SEED)
    if isinstance(rng, np.random.Generator):
        return rng
    return np.random.default_rng(rng)


def _mesh(V, tris) -> tuple[np.ndarray, np.ndarray]:
    return (np.asarray(V, np.float64).reshape(-1, 3), np.asarray(tris, np.int64).reshape(-1, 3))


def sample_surface(V: np.ndarray, tris: np.ndarray, n: int,
                   rng: np.random.Generator | int | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Area-uniform random points on a triangle mesh.

    Triangles are drawn with probability proportional to area; within a
    triangle the point is uniform via the square-root trick: with r₁, r₂ ~ U(0,1)
    and s = √r₁, barycentrics (1 − s, s(1 − r₂), s·r₂).

    Returns (points (n,3), tri_id (n,), bary (n,3)). Deterministic for a seeded
    ``rng`` (default seed 0).
    """
    V, tris = _mesh(V, tris)
    rng = _as_rng(rng)
    A, B, C = V[tris[:, 0]], V[tris[:, 1]], V[tris[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(B - A, C - A), axis=1)
    cdf = np.cumsum(area)
    if cdf[-1] <= 0:
        raise ValueError("mesh has zero surface area")
    t = np.searchsorted(cdf, rng.random(n) * cdf[-1], side="right")
    t = np.minimum(t, len(tris) - 1)
    s = np.sqrt(rng.random(n))
    r2 = rng.random(n)
    bary = np.column_stack([1.0 - s, s * (1.0 - r2), s * r2])
    pts = bary[:, 0:1] * A[t] + bary[:, 1:2] * B[t] + bary[:, 2:3] * C[t]
    return pts, t, bary


def _samples(V, tris, sample, n_samples, rng):
    """Sample points and the vertex id that labels each one (for regions)."""
    if sample == "vertices":
        used = np.unique(tris)
        return V[used], used
    if sample == "area":
        pts, t, bary = sample_surface(V, tris, n_samples, rng)
        # label transfer: the triangle vertex with the largest barycentric (nearest vertex)
        vid = tris[t, np.argmax(bary, axis=1)]
        return pts, vid
    raise ValueError("sample must be 'vertices' or 'area'")


def _stats(dabs: np.ndarray) -> dict:
    if dabs.size == 0:
        nan = float("nan")
        return {"median": nan, "mean": nan, "std": nan, "rms": nan, "p90": nan, "p95": nan,
                "f_at": {t: nan for t in F_THRESHOLDS_MM}, "n": 0}
    return {
        "median": float(np.median(dabs)),
        "mean": float(dabs.mean()),
        "std": float(dabs.std()),
        "rms": float(np.sqrt(np.mean(dabs * dabs))),
        "p90": float(np.percentile(dabs, 90)),
        "p95": float(np.percentile(dabs, 95)),
        "f_at": {t: float(np.mean(dabs <= t)) for t in F_THRESHOLDS_MM},
        "n": int(dabs.size),
    }


def surface_error(est_V: np.ndarray, est_tris: np.ndarray, ref_V: np.ndarray, ref_tris: np.ndarray,
                  direction: str = "ref_to_est", sample: str = "vertices", n_samples: int = 20000,
                  rng: np.random.Generator | int | None = None, regions: dict | None = None,
                  signed: bool = False) -> dict:
    """Surface error statistics between two aligned meshes.

    Parameters
    ----------
    est_V, est_tris : estimated mesh (mm). ref_V, ref_tris : reference mesh (mm).
    direction : ``'ref_to_est'`` (default; NoW scan-to-surface: reference samples
        measured to the estimate's surface), ``'est_to_ref'`` (estimate samples to
        the reference surface) or ``'symmetric'`` (both sets pooled).
    sample : ``'vertices'`` (every vertex referenced by a triangle of the sampled
        mesh; a vertex mean is an area mean only for uniform meshes,
        benchmarks-metrics "Heavy tails") or ``'area'`` (``n_samples`` area-
        uniform points per sampled mesh, see :func:`sample_surface`).
    n_samples : points per sampled mesh for ``sample='area'``.
    rng : Generator or seed for area sampling (default seed 0: deterministic).
    regions : optional ``{name: vertex ids}`` on the *sampled* mesh. Area samples
        take the label of the triangle vertex with the largest barycentric. With
        ``'symmetric'`` the ids are applied to both meshes, which must then share
        vertex indexing (e.g. both are fits of one template).
    signed : compute signed distances (convention in the module docstring) for
        ``signed_bias`` and the per-region ``bias``; otherwise these are NaN.

    Returns
    -------
    dict with ``median, mean, std, rms, p90, p95`` of the unsigned distances,
    ``f_at`` ``{0.5, 1.0, 2.0: fraction of samples with distance ≤ t}``,
    ``signed_bias`` (mean signed distance), ``n`` (sample count) and
    ``per_region`` ``{name: {rms, median, bias, n}}``.
    """
    if direction not in ("ref_to_est", "est_to_ref", "symmetric"):
        raise ValueError("direction must be 'ref_to_est', 'est_to_ref' or 'symmetric'")
    est_V, est_tris = _mesh(est_V, est_tris)
    ref_V, ref_tris = _mesh(ref_V, ref_tris)
    rng = _as_rng(rng)
    legs = []
    if direction in ("ref_to_est", "symmetric"):
        legs.append(("ref", ref_V, ref_tris, est_V, est_tris))
    if direction in ("est_to_ref", "symmetric"):
        legs.append(("est", est_V, est_tris, ref_V, ref_tris))

    dabs, dsgn, vids = [], [], []
    for src, sV, sT, tV, tT in legs:
        pts, vid = _samples(sV, sT, sample, n_samples, rng)
        d, _, _, _ = point_to_mesh(pts, tV, tT, signed=signed, grid=TriangleGrid(tV, tT))
        dabs.append(np.abs(d))
        if signed:
            # positive = estimate outside reference
            dsgn.append(d if src == "est" else -d)
        vids.append(vid)
    dabs_all = np.concatenate(dabs)
    out = _stats(dabs_all)
    nan = float("nan")
    sg = np.concatenate(dsgn) if signed else None
    out["signed_bias"] = float(sg.mean()) if signed and sg.size else nan
    per_region: dict[str, dict] = {}
    if regions:
        vid_all = np.concatenate(vids)
        for name, ids in regions.items():
            sel = np.isin(vid_all, np.asarray(ids, np.int64).ravel())
            n = int(sel.sum())
            dr = dabs_all[sel]
            per_region[name] = {
                "rms": float(np.sqrt(np.mean(dr * dr))) if n else nan,
                "median": float(np.median(dr)) if n else nan,
                "bias": float(sg[sel].mean()) if (signed and n) else nan,
                "n": n,
            }
    out["per_region"] = per_region
    return out


def chamfer(A_V: np.ndarray, A_tris: np.ndarray, B_V: np.ndarray, B_tris: np.ndarray,
            n_samples: int = 20000, rng: np.random.Generator | int | None = None) -> float:
    """Symmetric Chamfer distance (unsquared, mm).

    CD(A, B) = ½ · ( mean_{a∈S_A} d(a, B) + mean_{b∈S_B} d(b, A) ),

    where S_A, S_B are ``n_samples`` area-uniform samples on each surface and
    d(·, M) is the exact point-to-surface distance — the "½(mean S2M + mean
    M2S), unsquared" definition of benchmarks-metrics Table 4. Papers mix sums,
    squares and ×10³ scalings, so always quote this formula with the number.
    """
    A_V, A_tris = _mesh(A_V, A_tris)
    B_V, B_tris = _mesh(B_V, B_tris)
    rng = _as_rng(rng)
    pa, _, _ = sample_surface(A_V, A_tris, n_samples, rng)
    pb, _, _ = sample_surface(B_V, B_tris, n_samples, rng)
    da, _, _, _ = point_to_mesh(pa, B_V, B_tris)
    db, _, _, _ = point_to_mesh(pb, A_V, A_tris)
    return float(0.5 * (da.mean() + db.mean()))


def likeness_weighted_error(per_region_rms: dict, weights: dict | None = None) -> float:
    """E_like = Σ_r w_r·RMS_r / Σ_r w_r over the regions present (DESIGN §7.3).

    per_region_rms : ``{region: rms_mm}``; a ``surface_error()['per_region']``
        dict (values ``{'rms': ...}``) is accepted too.
    weights : ``{region: weight}``; default :data:`LIKENESS_WEIGHTS` (provisional).

    Regions without a weight, or whose RMS is NaN/None (no samples), are left
    out. Returns NaN when no region contributes. Perceptual weights steer
    evaluation and guidance only, never the data term (face-perception-likeness
    "Keep three weights separate").
    """
    w = LIKENESS_WEIGHTS if weights is None else weights
    num = 0.0
    den = 0.0
    for name, val in per_region_rms.items():
        if isinstance(val, dict):
            val = val.get("rms")
        if name not in w or val is None:
            continue
        val = float(val)
        wr = float(w[name])
        if not np.isfinite(val) or wr <= 0:
            continue
        num += wr * val
        den += wr
    return num / den if den > 0 else float("nan")
