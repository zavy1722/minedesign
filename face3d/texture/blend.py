"""Two-band blending, harmonic hole filling and the opt-in mirror fill (WP-18).

Implements DESIGN D-27 and section 4.18 (rec TEX-4, TEX-5; bl T3) on per-view texel
colours produced by :mod:`face3d.texture.project`:

* :func:`two_band_blend`: low band = normalised-convolution Gaussian of the weighted
  mean of all views (split sigma 3 mm on the surface); high band = the best view's own
  ``colour - lowpass(colour)`` (texture-extraction, "Two-band on the surface":
  seam-free by construction and keeps pores from one view);
* :func:`fill_holes`: harmonic (4-neighbour Jacobi) fill of unobserved texels, started
  from a push-pull estimate;
* :func:`mirror_fill_low_band`: **off by default** (D-27).  Only when ``allow_mirror``
  is True does it copy the *low band* of the mirrored texel into unobserved texels
  whose mirror source has confidence >= 0.3 (rec TEX-5: source >= 0.3 w_max), and it
  marks every such texel (texture-extraction: "Mirror fill copies marks and lighting.
  Mirror only the low band");
* :func:`build_texture`: gains -> two-band blend -> optional mirror fill -> harmonic
  fill, returning a :class:`TextureResult` with provenance.

Conventions
-----------
* Texture arrays are ``S x S`` with element ``[j, i]`` at UV ``((i + 0.5)/S,
  (j + 0.5)/S)`` (see :mod:`face3d.texture.project`).  Colours are linear light
  (sRGB/Rec.709 primaries), per view ``(n, S, S, 3)``; weights ``(n, S, S)`` >= 0.
  A texel is *observed* when its total weight is > 0.
* Gaussian blurs are separable on the texel grid, zero-padded at the map border, and
  always used as normalised convolutions ``G*(w c) / G*(w)``, so unobserved texels and
  the gutter contribute nothing.  ``texel_mm`` converts the surface split sigma to
  texels (``sigma = split_sigma_mm / texel_mm``); UV layouts are not isometric, so it
  is a representative scalar (:func:`face3d.texture.project.texel_size_mm`).  Blurs do
  not wrap across the u seam of a periodic layout (the seam sits behind the head).
* ``confidence = sum_v w_v / max_texels(sum_v w_v)`` in [0, 1] (0 = unobserved).
* Absolute colour is unknown without a colour chart (DESIGN 4.18, rec TEX-6): only
  gains *relative* to the geometric mean of the views are solved.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from ..core.config import Default, register_defaults
from .project import excluded_views as _excluded_views
from .project import solve_gains, texture_blocked

__all__ = [
    "BLEND_DEFAULTS", "TextureResult", "TextureBlocked", "ABSOLUTE_COLOUR_NOTE",
    "gaussian_blur", "normalized_blur", "two_band_blend", "fill_holes", "mirror_fill_low_band",
    "build_texture",
]

_BRAIN = "\U0001F9E0"
_NEW = "\U0001F195"

#: Badged defaults of the blend stage (DESIGN 2.1: no hard-coded 🧠/🆕 numbers).
BLEND_DEFAULTS = register_defaults("texture.blend", {
    "split_sigma_mm": Default(
        3.0, _BRAIN, "DESIGN 4.18 / rec TEX-4: two-band split at Gaussian sigma 3 mm on the surface "
        "(texture-extraction Table 4: 2-5 mm)", "mm", (0.01, 100.0)),
    "mirror_min_confidence": Default(
        0.3, _BRAIN, "rec TEX-5: mirror-fill source weight >= 0.3 w_max (texture-extraction Table 4: "
        "0.2-0.5)", "", (0.0, 1.0)),
    "fill_iterations": Default(
        500, _NEW, "WBS WP-18 spec: harmonic Jacobi iterations of fill_holes", "", (0, 1000000)),
})
_B = {k: BLEND_DEFAULTS[k].value for k in BLEND_DEFAULTS}

#: Provenance note required by DESIGN 4.18 ("absolute colour unknown" without a chart).
ABSOLUTE_COLOUR_NOTE = "absolute colour unknown without a chart"

#: Kernels longer than this are convolved with an FFT (same result up to rounding).
_FFT_MIN_TAPS = 65

#: Relative cut-off of :func:`normalized_blur` (numerical constant, not a model default).
_REL_MIN_DEN = 1e-8


class TextureBlocked(PermissionError):
    """A blocking texture gate finding was passed to :func:`build_texture`."""


# =========================================================================== blurs
def _kernel(sigma: float) -> np.ndarray:
    r = max(1, int(math.ceil(3.0 * sigma)))
    x = np.arange(-r, r + 1, dtype=np.float64)
    k = np.exp(-0.5 * (x / sigma) ** 2)
    return k / k.sum()


def _conv_axis(a: np.ndarray, k: np.ndarray, axis: int) -> np.ndarray:
    """'Same'-size convolution of ``a`` with the symmetric kernel ``k`` along ``axis``, zero padding."""
    r = (len(k) - 1) // 2
    a = np.moveaxis(a, axis, 0)
    N = a.shape[0]
    if len(k) < _FFT_MIN_TAPS:
        p = np.zeros((N + 2 * r,) + a.shape[1:])
        p[r:r + N] = a
        out = np.zeros_like(a, dtype=np.float64)
        for i in range(len(k)):
            out += k[i] * p[i:i + N]
    else:
        L = N + len(k) - 1
        nfft = 1 << (L - 1).bit_length()
        fa = np.fft.rfft(a, n=nfft, axis=0)
        fk = np.fft.rfft(k, n=nfft)
        full = np.fft.irfft(fa * fk.reshape((-1,) + (1,) * (a.ndim - 1)), n=nfft, axis=0)
        out = full[r:r + N]
    return np.moveaxis(out, 0, axis)


def gaussian_blur(a: np.ndarray, sigma_texels: float) -> np.ndarray:
    """Separable Gaussian blur (radius ceil(3 sigma), zero padding) of an (S, S[, C]) array."""
    a = np.asarray(a, np.float64)
    s = float(sigma_texels)
    if not s > 0:
        return a.copy()
    k = _kernel(s)
    return _conv_axis(_conv_axis(a, k, 0), k, 1)


def normalized_blur(values: np.ndarray, weights: np.ndarray, sigma_texels: float,
                    rel_min_den: float = _REL_MIN_DEN) -> tuple[np.ndarray, np.ndarray]:
    """Normalised convolution ``G*(w c) / G*(w)`` of (S, S, C) ``values`` with (S, S) weights.

    Returns ``(blurred (S, S, C), den (S, S) = G*(w))``.  The cut-off is relative, so
    the result does not depend on the scale of ``w``: texels where ``G*(w)`` is at most
    ``rel_min_den`` times ``k0^2 max(w)`` (the blurred weight of a lone texel holding the
    maximum weight; ``k0`` is the kernel's centre tap) have no weighted texel within
    reach and are 0 there, with ``den`` 0.  The default 1e-8 sits far above the FFT
    round-off of wide kernels (~1e-15 relative) and far below any weight
    :func:`face3d.texture.project.view_weights` produces next to its maximum.
    Non-finite values count as weight 0.
    """
    c = np.asarray(values, np.float64)
    w = np.asarray(weights, np.float64)
    ok = np.isfinite(c).all(axis=-1) & np.isfinite(w) & (w > 0)
    w = np.where(ok, w, 0.0)
    c = np.where(ok[..., None], c, 0.0)
    wmax = float(w.max()) if w.size else 0.0
    if not wmax > 0:
        return np.zeros(c.shape), np.zeros(w.shape)
    ws = w / wmax                                    # scale-free: max weight 1
    s = float(sigma_texels)
    k0 = float(_kernel(s).max()) if s > 0 else 1.0
    num = gaussian_blur(c * ws[..., None], s)
    den = gaussian_blur(ws, s)
    good = den > float(rel_min_den) * k0 * k0
    out = np.zeros_like(num)
    out[good] = num[good] / den[good][:, None]
    return out, np.where(good, den * wmax, 0.0)


# =========================================================================== two-band
def _prepare(colours: Any, weights: Any) -> tuple[np.ndarray, np.ndarray]:
    C = np.asarray(colours, np.float64)
    if C.ndim == 3:
        C = C[None]
    w = np.asarray(weights, np.float64)
    if w.ndim == 2:
        w = w[None]
    if C.ndim != 4 or C.shape[-1] != 3 or w.shape != C.shape[:-1]:
        raise ValueError("colours must be (n, S, S, 3) and weights (n, S, S)")
    ok = np.isfinite(C).all(axis=-1) & np.isfinite(w) & (w > 0)
    return np.where(ok[..., None], C, 0.0), np.where(ok, w, 0.0)


def _two_band(colours: Any, weights: Any, texel_mm: float, split_sigma_mm: float):
    C, w = _prepare(colours, weights)
    if not (float(texel_mm) > 0):
        raise ValueError("texel_mm must be > 0")
    sigma = float(split_sigma_mm) / float(texel_mm)
    Wsum = w.sum(axis=0)
    observed = Wsum > 0
    num = np.einsum("vij,vijc->ijc", w, C)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(observed[..., None], num / np.where(observed, Wsum, 1.0)[..., None], 0.0)
    low, den = normalized_blur(mean, Wsum, sigma)
    # No weighted texel within reach of the low-pass (a lone, relatively tiny weight):
    # no band split there, the low band is the texel's own weighted mean.
    low = np.where((den > 0)[..., None], low, mean)
    best = np.where(observed, np.argmax(w, axis=0), -1).astype(np.int64)
    high = np.zeros_like(low)
    for v in np.unique(best[best >= 0]):
        low_v, den_v = normalized_blur(C[v], w[v], sigma)
        # Where the best view's own low-pass is undefined its high band is unknown:
        # leave it 0 so the albedo falls back to the low band (never c_b - 0).
        sel = (best == v) & (den_v > 0)
        high[sel] = C[v][sel] - low_v[sel]
    albedo = np.where(observed[..., None], np.clip(low + high, 0.0, None), 0.0)
    wmax = float(Wsum.max()) if Wsum.size else 0.0
    confidence = Wsum / wmax if wmax > 0 else np.zeros_like(Wsum)
    return albedo, confidence, best, low


def two_band_blend(colours: Any, weights: Any, texel_mm: float,
                   split_sigma_mm: float = _B["split_sigma_mm"]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Two-band blend of gain-levelled per-view texel colours (DESIGN 4.18, rec TEX-4).

    colours : (n, S, S, 3) linear colours (already divided by the view gains); NaN =
        not sampled.  weights : (n, S, S) from :func:`face3d.texture.project.view_weights`.
    texel_mm : surface size of a texel (mm); ``split_sigma_mm`` = 3 mm -> Gaussian sigma
        ``split_sigma_mm / texel_mm`` texels.

    * low band ``L = G*(sum_v w_v c_v) / G*(sum_v w_v)`` (normalised convolution of the
      weighted mean);
    * best view ``b`` = argmax_v w_v per texel (ties to the lower view index; -1 where no
      view sees the texel);
    * high band ``H = c_b - G*(w_b c_b) / G*(w_b)``: the best view minus *its own*
      low-pass (texture-extraction "Two-band on the surface"); ``H = 0`` where that
      low-pass is undefined (:func:`normalized_blur` cut-off), and ``L`` is the texel's
      own weighted mean where the all-view low-pass is undefined, so an observed texel
      never doubles its colour or drops to 0;
    * ``albedo = max(L + H, 0)`` on observed texels, 0 elsewhere;
    * ``confidence = sum_v w_v / max(sum_v w_v)``.

    When all views agree on a colour field, ``H`` re-adds exactly what the low-pass
    removed, so a constant albedo stays constant.  Returns
    ``(albedo (S, S, 3) float64, confidence (S, S) float64, best_view (S, S) int64)``.
    """
    albedo, confidence, best, _low = _two_band(colours, weights, texel_mm, split_sigma_mm)
    return albedo, confidence, best


# =========================================================================== fills
def _pushpull(A: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Push-pull estimate everywhere: 2x2 weighted averages down the pyramid, then fill
    each level's empty cells from the next coarser level (nearest upsampling)."""
    vals = [np.where(valid[..., None], A, 0.0)]
    wts = [valid.astype(np.float64)]
    while max(vals[-1].shape[:2]) > 1:
        v, w = vals[-1], wts[-1]
        h, wd = v.shape[:2]
        H2, W2 = (h + 1) // 2, (wd + 1) // 2
        vp = np.zeros((2 * H2, 2 * W2) + v.shape[2:])
        wp = np.zeros((2 * H2, 2 * W2))
        vp[:h, :wd] = v * w[..., None]
        wp[:h, :wd] = w
        sv = vp.reshape(H2, 2, W2, 2, -1).sum(axis=(1, 3))
        sw = wp.reshape(H2, 2, W2, 2).sum(axis=(1, 3))
        with np.errstate(invalid="ignore", divide="ignore"):
            nv = np.where(sw[..., None] > 0, sv / np.where(sw > 0, sw, 1.0)[..., None], 0.0)
        vals.append(nv)
        wts.append(np.minimum(sw, 1.0))
    est = vals[-1]
    for lvl in range(len(vals) - 2, -1, -1):
        v, w = vals[lvl], wts[lvl]
        h, wd = v.shape[:2]
        up = np.repeat(np.repeat(est, 2, axis=0), 2, axis=1)[:h, :wd]
        est = np.where(w[..., None] > 0, v, up)
    return est


def fill_holes(albedo: np.ndarray, valid_mask: np.ndarray, iterations: int = _B["fill_iterations"], *,
               region: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Harmonic fill of the invalid texels (DESIGN 4.18 / rec TEX-5 "harmonic").

    The invalid texels (inside ``region`` when given, e.g. the G-buffer mask; the whole
    map otherwise) are initialised with a push-pull estimate from the valid texels and
    then relaxed by ``iterations`` Jacobi sweeps of the 4-neighbour Laplace equation:
    each becomes the mean of its neighbours inside the domain (valid | to-fill; other
    neighbours are ignored, i.e. a Neumann boundary).  Valid texels never change.
    Returns ``(filled (S, S, C) float64, filled_mask (S, S) bool)``; with no valid texel
    nothing is filled.
    """
    A = np.array(albedo, dtype=np.float64, copy=True)
    squeeze = A.ndim == 2
    if squeeze:
        A = A[..., None]
    valid = np.asarray(valid_mask, bool)
    if valid.shape != A.shape[:2]:
        raise ValueError("valid_mask must match the albedo's (S, S)")
    target = ~valid
    if region is not None:
        target &= np.asarray(region, bool)
    if not valid.any() or not target.any():
        return (A[..., 0] if squeeze else A), np.zeros(valid.shape, bool)
    A[target] = _pushpull(A, valid)[target]
    domain = valid | target
    dp = np.pad(domain, 1, constant_values=False).astype(np.float64)
    cnt = dp[:-2, 1:-1] + dp[2:, 1:-1] + dp[1:-1, :-2] + dp[1:-1, 2:]
    upd = target & (cnt > 0)
    inv = np.where(upd, 1.0 / np.where(cnt > 0, cnt, 1.0), 0.0)[..., None]
    dom3 = domain[..., None]
    for _ in range(int(iterations)):
        p = np.pad(np.where(dom3, A, 0.0), ((1, 1), (1, 1), (0, 0)))
        s = p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]
        A = np.where(upd[..., None], s * inv, A)
    return (A[..., 0] if squeeze else A), target


def mirror_fill_low_band(albedo: np.ndarray, valid_mask: np.ndarray, mirror_uv_map: np.ndarray,
                         allow_mirror: bool = False, *, confidence: np.ndarray | None = None,
                         low_band: np.ndarray | None = None,
                         min_source_confidence: float = _B["mirror_min_confidence"]
                         ) -> tuple[np.ndarray, np.ndarray]:
    """Opt-in mirror fill of the low band (DESIGN D-27, rec TEX-5).

    With ``allow_mirror=False`` (the default) this does nothing: it returns a copy of
    ``albedo`` and an all-False mask, whatever else is passed.  Texture is never
    mirrored silently (D-27; anat R5.11: mirroring copies moles, partings and the
    lighting of the other side).

    With ``allow_mirror=True`` every texel that is not valid and whose mirror texel
    ``mirror_uv_map[j, i] = (row, col)`` (from
    :func:`face3d.texture.project.mirror_texel_map`) is valid with
    ``confidence >= min_source_confidence`` (0.3, i.e. source weight >= 0.3 w_max)
    receives the source's **low band only** (``low_band[row, col]``, the
    :func:`two_band_blend` low band; no high-frequency detail, so no unique marks), and
    is marked in the returned ``mirrored_mask``.  ``confidence`` and ``low_band`` are
    then required.  Returns ``(albedo (S, S, C) float64, mirrored_mask (S, S) bool)``.
    """
    out = np.array(albedo, dtype=np.float64, copy=True)
    valid = np.asarray(valid_mask, bool)
    mirrored = np.zeros(valid.shape, bool)
    if not allow_mirror:
        return out, mirrored
    if confidence is None or low_band is None:
        raise ValueError("allow_mirror=True needs the source confidence and low band")
    conf = np.asarray(confidence, np.float64)
    low = np.asarray(low_band, np.float64)
    mp = np.asarray(mirror_uv_map, np.int64)
    if mp.shape != valid.shape + (2,) or conf.shape != valid.shape or low.shape != out.shape:
        raise ValueError("mirror_uv_map (S, S, 2), confidence (S, S) and low_band must match the albedo")
    tgt = ~valid & (mp[..., 0] >= 0) & (mp[..., 1] >= 0)
    jj, ii = np.nonzero(tgt)
    r, c = mp[jj, ii, 0], mp[jj, ii, 1]
    ok = valid[r, c] & (conf[r, c] >= float(min_source_confidence))
    jj, ii, r, c = jj[ok], ii[ok], r[ok], c[ok]
    out[jj, ii] = low[r, c]
    mirrored[jj, ii] = True
    return out, mirrored


# =========================================================================== result
@dataclass
class TextureResult:
    """Projected texture (DESIGN 4.18 outputs).

    albedo_linear : (S, S, 3) float32 linear albedo-with-shading (no de-lighting in
        WP-18), relative to the views' geometric-mean exposure.
    confidence : (S, S) float32 in [0, 1], ``sum_v w_v / max``; 0 on mirrored and filled
        texels.
    view_index : (S, S) int32 best (max-weight) view per texel, -1 where unobserved.
    filled_mask : (S, S) bool, texels filled harmonically.
    mirrored_mask : (S, S) bool, texels whose low band was mirrored (only with
        ``allow_mirror``; D-27).
    provenance : dict with ``views``, ``gains`` (n x 3), ``allow_mirror``,
        ``filled_fraction``, ``mirrored_fraction``, ``absolute_colour`` (=
        :data:`ABSOLUTE_COLOUR_NOTE`), ``observed_fraction``, ``excluded_views``,
        ``method``, ``fill_order``, ``split_sigma_mm``, ``texel_mm``, ``colour_space``,
        ``gated`` and ``gated_n_views`` (the view count the gates checked, None if unknown).
    """

    albedo_linear: np.ndarray
    confidence: np.ndarray
    view_index: np.ndarray
    filled_mask: np.ndarray
    mirrored_mask: np.ndarray
    provenance: dict = field(default_factory=dict)


def _gated_view_count(findings: Sequence[Mapping], n_attr: Any = None) -> int | None:
    """The view count the texture gates checked: ``n_attr`` (``GateFindings.n_views`` of
    :class:`face3d.texture.project.GateFindings`), else the ``detail['n_views']`` the
    (already materialised) findings agree on (TextureBlocked when they disagree), else
    None (unknown)."""
    if n_attr is not None:
        return int(n_attr)
    seen = set()
    for f in findings:
        d = f.get("detail") if isinstance(f, Mapping) else None
        if isinstance(d, Mapping) and d.get("n_views") is not None:
            seen.add(int(d["n_views"]))
    if len(seen) > 1:
        raise TextureBlocked(f"texture gate findings disagree on the number of views: {sorted(seen)}")
    return seen.pop() if seen else None


def build_texture(colours: Any, weights: Any, texel_mm: float, *, gains: np.ndarray | None = None,
                  views: Sequence[Any] | None = None, region: np.ndarray | None = None,
                  mirror_uv_map: np.ndarray | None = None, allow_mirror: bool = False,
                  findings: Iterable[Mapping] | None = None, exclude_views: Iterable[int] = (),
                  split_sigma_mm: float = _B["split_sigma_mm"],
                  fill_iterations: int = _B["fill_iterations"],
                  min_mirror_confidence: float = _B["mirror_min_confidence"]) -> TextureResult:
    """Gains -> two-band blend -> (opt-in) mirror low band -> harmonic fill (DESIGN 4.18).

    colours : (n, S, S, 3) linear samples from :func:`face3d.texture.project.sample_image`
        (not yet gain-levelled).  weights : (n, S, S) from ``view_weights``.
    gains : (n, 3) known gains; default solved by
        :func:`face3d.texture.project.solve_gains` over the views kept.
    views : view identifiers for the provenance (default ``0..n-1``).
    region : (S, S) bool texels to produce (normally the G-buffer mask); fills stay
        inside it (default: the whole map).
    mirror_uv_map, allow_mirror : see :func:`mirror_fill_low_band`; mirroring needs both
        ``allow_mirror=True`` and a map (D-27: off by default).
    findings : texture gate findings (:func:`face3d.texture.project.texture_gates`): a
        blocking finding raises :class:`TextureBlocked`, and so does a gate that checked
        a different number of views than ``colours`` holds (``GateFindings.n_views`` or
        ``detail['n_views']``: views whose rights were never checked must not feed
        albedo); views marked ``exclude_texture`` are dropped (weight 0).
        ``exclude_views`` drops more views.

    Raises ValueError ("no usable views") when, after the exclusions, no texel of the
    region is observed by any view: an all-black albedo is never returned silently.

    Fill order follows rec TEX-5 (mirror, then harmonic); "patch" and "model" fills are
    not part of WP-18.
    """
    C = np.asarray(colours, np.float64)
    w = np.array(weights, dtype=np.float64, copy=True)
    if C.ndim != 4 or C.shape[-1] != 3 or w.shape != C.shape[:-1]:
        raise ValueError("colours must be (n, S, S, 3) and weights (n, S, S)")
    n, S = C.shape[0], C.shape[1]
    drop = {int(v) for v in exclude_views}
    gated = findings is not None
    n_gated = None
    if findings is not None:
        n_attr = getattr(findings, "n_views", None)
        findings = list(findings)            # once: a generator must not be consumed twice
        n_gated = _gated_view_count(findings, n_attr)
        if texture_blocked(findings):
            codes = sorted({f.get("code") for f in findings if f.get("severity") == "block"})
            raise TextureBlocked(f"texture projection blocked by {codes}")
        if n_gated is not None and n_gated != n:
            raise TextureBlocked(f"texture gates checked the rights of {n_gated} views but {n} colour views "
                                 "were given: every view must pass texture_gates (eth F7)")
        drop |= set(_excluded_views(findings))
    for v in drop:
        if 0 <= v < n:
            w[v] = 0.0
    reg = np.ones((S, S), bool) if region is None else np.asarray(region, bool)
    if reg.shape != (S, S):
        raise ValueError(f"region must be (S, S) = {(S, S)}, got {reg.shape}")
    usable = (np.isfinite(C).all(axis=-1) & np.isfinite(w) & (w > 0)).any(axis=0)
    if not (usable & reg).any():
        raise ValueError(f"no usable views: no texel{' of the region' if region is not None else ''} is observed "
                         f"by any of the {n} views after excluding views {sorted(drop)}")
    if gains is None:
        g = solve_gains(list(C), list(w))
    else:
        g = np.asarray(gains, np.float64).reshape(n, 3)
    levelled = C / g[:, None, None, :]
    albedo, conf, best, low = _two_band(levelled, w, texel_mm, split_sigma_mm)
    valid = conf > 0
    mirrored = np.zeros((S, S), bool)
    if allow_mirror and mirror_uv_map is not None:
        albedo, mirrored = mirror_fill_low_band(albedo, valid, mirror_uv_map, True, confidence=conf,
                                                low_band=low, min_source_confidence=min_mirror_confidence)
        mirrored &= reg
    albedo, filled = fill_holes(albedo, valid | mirrored, fill_iterations, region=reg)
    n_reg = max(int(reg.sum()), 1)
    prov = {
        "views": list(range(n)) if views is None else list(views),
        "gains": np.asarray(g).tolist(),
        "allow_mirror": bool(allow_mirror),
        "filled_fraction": float(filled.sum()) / n_reg,
        "mirrored_fraction": float(mirrored.sum()) / n_reg,
        "observed_fraction": float((valid & reg).sum()) / n_reg,
        "absolute_colour": ABSOLUTE_COLOUR_NOTE,
        "excluded_views": sorted(drop),
        "method": "two_band",
        "fill_order": (["mirror"] if allow_mirror and mirror_uv_map is not None else []) + ["harmonic"],
        "split_sigma_mm": float(split_sigma_mm),
        "texel_mm": float(texel_mm),
        "colour_space": "linear, sRGB/Rec.709 primaries",
        "gated": gated,
        "gated_n_views": n_gated,
    }
    return TextureResult(
        albedo_linear=np.where(reg[..., None], albedo, 0.0).astype(np.float32),
        confidence=np.where(valid & reg, conf, 0.0).astype(np.float32),
        view_index=np.where(valid & reg, best, -1).astype(np.int32),
        filled_mask=filled & reg,
        mirrored_mask=mirrored,
        provenance=prov,
    )
