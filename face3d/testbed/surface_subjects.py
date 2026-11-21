"""Surface-level synthetic subjects and expression fields for the test bed (DESIGN 7.2, D-30; WP-11).

Subjects are deformations of a :class:`face3d.model.template_kit.TemplateKit`
(by default the procedural CC0 head) generated **independently of the fitted
prior**: this module never imports ``face3d.model.landmark_prior`` (no inverse
crime, DESIGN D-30 / 7.2; checked by an AST test) and imports nothing from
``face3d.model`` at run time.  Every displacement is a smooth field on the
template surface, and several of them (dorsal hump, chin cleft, lip-line
curvature, cheek fullness, the antisymmetric part) are shapes the 18-factor
landmark model cannot express, so errors measured on these subjects are not
the optimistic in-span numbers an inverse crime would give (*validation-test-bed*
"Inverse crime"; DESIGN 7.2).

Conventions
-----------
* Units: float64 millimetres in the kit's head frame (Frankfort horizontal,
  origin mid-tragion; +x subject's left, +y up, +z out of the face; DESIGN 3.1).
* ``V_true`` keeps the kit topology (same vertex order), so every landmark
  embedding ``(tri, bary)`` of the kit evaluates on it directly
  (:meth:`SurfaceSubject.landmarks`); landmarks follow the vertices exactly.
* Mirror: ``F = diag(-1, 1, 1)``; ``kit.mirror_map[i]`` is the vertex at
  ``F V[i]``.  A field ``s`` is symmetric when ``s[m[i]] = F s[i]`` and
  antisymmetric when ``s[m[i]] = -F s[i]``; for ``V = S + A`` (S symmetric, A
  antisymmetric) the mirror image is ``S - A``, so the correspondence mirror
  RMSD is ``2 * RMS|A|``.
* ``asym_rms_mm`` = RMS over the face hemisphere (rest ``z > FACE_MIN_Z_MM``) of
  ``|A_i|`` with ``A = (V - F V[m]) / 2`` measured on the final ``V_true``.
* ``log_scale_true`` = log of the Umeyama similarity scale mapping the kit's
  rest ``anatomical44`` landmarks onto the subject's (all vertices when the kit
  has no ``anatomical44`` scheme); the same definition as the landmark-level
  test bed (:func:`face3d.testbed.subjects.log_scale_of`).
* Determinism: every random number comes from the caller's
  ``numpy.random.Generator`` in a fixed draw order.

Every numeric default is registered with a badge and a source in the
``testbed.surface`` namespace (:mod:`face3d.core.config`); all are test-bed
design values (badge 🆕 unless a source is cited), not anatomical measurements.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Sequence

import numpy as np

from ..core.config import Default, register_defaults
from ..geometry.procrustes import umeyama

if TYPE_CHECKING:  # typing only: no run-time import from face3d.model
    from ..model.template_kit import TemplateKit

__all__ = [
    "SurfaceSubject", "out_of_prior_subject", "expression_field", "expression_meta",
    "EXPRESSION_KINDS", "area_ratios", "face_hemisphere", "symmetric_part", "antisymmetric_part",
    "asymmetry_rms", "region_weight", "SURFACE_DEFAULTS", "FACE_MIN_Z_MM", "SubjectGenerationError",
]

_NEW = "\U0001F195"     # introduced by this design, uncalibrated
_BRAIN = "\U0001F9E0"   # expert knowledge, provisional
_WP = "WBS WP-11 spec (test-bed generator design value)"
_THIS = "WP-11 implementation choice (test-bed generator; not in the spec)"

SURFACE_DEFAULTS = register_defaults("testbed.surface", {
    # --- symmetric smooth field (WP-11 spec)
    "amp_mm": Default(3.0, _NEW, _WP + ": bump amplitudes N(0, amp^2)", "mm", (0.0, 50.0)),
    "n_bumps": Default(15, _NEW, _WP + ": number of mirrored Gaussian bumps", "", (0, 1000)),
    "width_min_mm": Default(20.0, _NEW, _WP + ": bump widths U(20, 60) mm", "mm", (1.0, 500.0)),
    "width_max_mm": Default(60.0, _NEW, _WP + ": bump widths U(20, 60) mm", "mm", (1.0, 500.0)),
    "face_min_z_mm": Default(0.0, _NEW, _THIS + ": face hemisphere = rest z > 0 (in front of mid-tragion, "
                             "DESIGN 3.1 frame)", "mm", (-200.0, 200.0)),
    # --- features outside the 18-factor model (WP-11 spec; DESIGN 7.2)
    "hump_amp_min_mm": Default(-1.5, _NEW, _WP + ": dorsal hump amplitude U(-1.5, 2.5)", "mm", (-20.0, 20.0)),
    "hump_amp_max_mm": Default(2.5, _NEW, _WP + ": dorsal hump amplitude U(-1.5, 2.5)", "mm", (-20.0, 20.0)),
    "hump_sigma_mm": Default(6.0, _NEW, _WP + ": dorsal hump sigma 6 mm", "mm", (0.1, 100.0)),
    "cleft_depth_max_mm": Default(1.2, _NEW, _WP + ": chin cleft depth U(0, 1.2)", "mm", (0.0, 20.0)),
    "cleft_sigma_mm": Default(3.0, _NEW, _WP + ": chin cleft lateral sigma 3 mm", "mm", (0.1, 100.0)),
    "cleft_vertical_sigma_mm": Default(8.0, _NEW, _THIS + ": vertical extent of the chin groove", "mm",
                                       (0.1, 100.0)),
    "lip_curve_amp_mm": Default(1.0, _NEW, _WP + ": lip-line curvature c*(|x|/30)^3*U(-1,1) mm", "mm",
                                (0.0, 20.0)),
    "lip_curve_ref_mm": Default(30.0, _NEW, _WP + ": lip-line curvature reference half-width 30 mm", "mm",
                                (1.0, 200.0)),
    "mouth_falloff_mm": Default(8.0, _NEW, _THIS + ": mouth-line proximity weight sigma", "mm", (0.1, 100.0)),
    "cheek_amp_mm": Default(2.0, _NEW, _WP + ": cheek fullness +/-2 mm", "mm", (0.0, 20.0)),
    "cheek_falloff_mm": Default(8.0, _NEW, _THIS + ": cheek-region falloff sigma", "mm", (0.1, 100.0)),
    # --- antisymmetric part
    # facial-asymmetry.md: whole-face mirror RMSD ~0.8 mm (Taylor et al. [6][7], 📄); used here as the
    # RMS of the antisymmetric field (a test-bed choice; correspondence mirror RMSD = 2x this).
    "asym_mm": Default(0.8, _BRAIN, "facial-asymmetry.md whole-face RMSD ~0.8 mm [6][7]; WP-11 spec",
                       "mm", (0.0, 20.0)),
    "n_asym_bumps": Default(8, _NEW, _THIS + ": bumps in the asymmetric field before antisymmetrising", "",
                            (1, 1000)),
    # --- global size
    "aniso_sd": Default(0.02, _NEW, _WP + ": anisotropic scale diag(1 + N(0, 0.02^2))", "", (0.0, 0.5)),
    "log_scale_sd": Default(0.045, _BRAIN, "DESIGN 4.7 / D-03 zeta ~ N(0, 0.045^2) (validation-test-bed T5)",
                            "", (0.0, 1.0)),
    # --- fold gate
    "min_area_ratio": Default(0.2, _BRAIN, "WP-11 spec; DESIGN 4.15 gate det J_warp > 0.2 (rec MM-11)", "",
                              (0.0, 1.0)),
    "max_attempts": Default(50, _NEW, _THIS + ": bounded resampling attempts", "", (1, 10000)),
    # --- expression fields (WP-11 spec)
    "smile_up": Default(0.6, _NEW, _WP + ": smile corners up 0.6*amount", "", (0.0, 10.0)),
    "smile_out": Default(0.4, _NEW, _WP + ": smile corners outward 0.4*amount", "", (0.0, 10.0)),
    "smile_sigma_mm": Default(15.0, _NEW, _WP + ": smile Gaussian falloff sigma 15 mm", "mm", (0.1, 200.0)),
    "smile_cheek_up": Default(0.25, _NEW, _WP + ": smile cheeks up 0.25*amount", "", (0.0, 10.0)),
    "smile_cheek_falloff_mm": Default(15.0, _NEW, _THIS + ": cheek-region falloff for the smile", "mm",
                                      (0.1, 200.0)),
    # DESIGN 4.9: hinge c = mid-tragion + (0, -5, +11.5) mm (bl K8, contested range 10-13 mm anterior).
    "jaw_hinge_y_mm": Default(-5.0, "↔️", "DESIGN 4.9 jaw hinge (bl K8)", "mm", (-50.0, 50.0)),
    "jaw_hinge_z_mm": Default(11.5, "↔️", "DESIGN 4.9 jaw hinge 10-13 mm anterior (bl K8)", "mm", (-50.0, 50.0)),
    "brow_falloff_mm": Default(10.0, _NEW, _THIS + ": brow-raise falloff around the forehead region", "mm",
                               (0.1, 200.0)),
    "blink_ramp_min_mm": Default(2.0, _NEW, _THIS + ": blink vertical ramp above the pupil (min)", "mm",
                                 (0.1, 50.0)),
    "blink_ramp_per_mm": Default(1.5, _NEW, _THIS + ": blink ramp = max(min, 1.5*amount) keeps the field "
                                 "fold-free (gradient < 1)", "", (1.0, 10.0)),
    "blink_falloff_mm": Default(4.0, _NEW, _THIS + ": blink falloff outside the eyes region", "mm",
                                (0.1, 50.0)),
})
_D = {k: SURFACE_DEFAULTS[k].value for k in SURFACE_DEFAULTS}

FACE_MIN_Z_MM: float = _D["face_min_z_mm"]

_FLIP = np.array([-1.0, 1.0, 1.0])

#: Supported expression kinds (WP-11 spec).
EXPRESSION_KINDS: tuple[str, ...] = ("smile", "jaw_open", "brow_raise", "blink")


class SubjectGenerationError(RuntimeError):
    """No fold-free subject was drawn within the attempt budget."""


# =========================================================================== helpers
def face_hemisphere(kit: "TemplateKit", min_z: float = FACE_MIN_Z_MM) -> np.ndarray:
    """Vertex ids of the face hemisphere: rest vertices with ``z > min_z`` (mm, head frame)."""
    return np.flatnonzero(kit.vertices[:, 2] > float(min_z))


def area_ratios(V_rest: np.ndarray, V: np.ndarray, tris: np.ndarray) -> np.ndarray:
    """Signed area ratio of every triangle in its rest tangent plane (determinant proxy).

    ``ratio_t = (n0_t . ((B - A) x (C - A))) / |(B0 - A0) x (C0 - A0)|`` with ``n0`` the
    unit rest normal: 1 for an unchanged triangle, ``s^2`` under a uniform scale ``s``,
    <= 0 for a folded (flipped) one.  Degenerate rest triangles give ratio 1.
    """
    V0 = np.asarray(V_rest, float)
    V1 = np.asarray(V, float)
    t = np.asarray(tris, np.int64)
    n0 = np.cross(V0[t[:, 1]] - V0[t[:, 0]], V0[t[:, 2]] - V0[t[:, 0]])
    a0 = np.linalg.norm(n0, axis=1)
    n1 = np.cross(V1[t[:, 1]] - V1[t[:, 0]], V1[t[:, 2]] - V1[t[:, 0]])
    ok = a0 > 1e-300
    out = np.ones(len(t))
    out[ok] = np.einsum("ij,ij->i", n0[ok], n1[ok]) / (a0[ok] * a0[ok])
    return out


def symmetric_part(V: np.ndarray, mirror_map: np.ndarray) -> np.ndarray:
    """S = (V + F V[m]) / 2 (exactly mirror-symmetric up to round-off)."""
    V = np.asarray(V, float)
    return 0.5 * (V + V[np.asarray(mirror_map)] * _FLIP)


def antisymmetric_part(V: np.ndarray, mirror_map: np.ndarray) -> np.ndarray:
    """A = (V - F V[m]) / 2, so that V = S + A and mirror(V) = S - A."""
    V = np.asarray(V, float)
    return 0.5 * (V - V[np.asarray(mirror_map)] * _FLIP)


def asymmetry_rms(kit: "TemplateKit", V: np.ndarray, min_z: float = FACE_MIN_Z_MM) -> float:
    """RMS over the face hemisphere of |A_i| (mm), A the antisymmetric part of V."""
    A = antisymmetric_part(V, kit.mirror_map)
    idx = face_hemisphere(kit, min_z)
    if idx.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.sum(A[idx] ** 2, axis=1))))


def _symmetrise(kit: "TemplateKit", V: np.ndarray) -> np.ndarray:
    S = symmetric_part(V, kit.mirror_map)
    S[kit.midline, 0] = 0.0
    return S


def _min_dist(P: np.ndarray, Q: np.ndarray, chunk: int = 4096) -> np.ndarray:
    """Distance from each row of P to the nearest row of Q (brute force, chunked)."""
    P = np.asarray(P, float)
    Q = np.asarray(Q, float)
    if len(Q) == 0:
        return np.full(len(P), np.inf)
    out = np.empty(len(P))
    qq = np.sum(Q * Q, axis=1)
    for s in range(0, len(P), chunk):
        p = P[s:s + chunk]
        d2 = np.sum(p * p, axis=1)[:, None] - 2.0 * p @ Q.T + qq[None, :]
        out[s:s + chunk] = np.sqrt(np.maximum(d2.min(axis=1), 0.0))
    return out


def region_weight(kit: "TemplateKit", V: np.ndarray, name: str, falloff_mm: float) -> np.ndarray:
    """Smooth region indicator: 1 on the region's vertices, ``exp(-d^2 / (2 f^2))`` elsewhere,
    with ``d`` the distance (in ``V``) to the nearest region vertex.  C1 at the boundary.
    An absent or empty region gives zeros."""
    V = np.asarray(V, float)
    idx = np.asarray(kit.regions.get(name, np.zeros(0, np.int64)), np.int64)
    w = np.zeros(len(V))
    if idx.size == 0:
        return w
    d = _min_dist(V, V[idx])
    w = np.exp(-0.5 * (d / float(falloff_mm)) ** 2)
    w[idx] = 1.0
    return w


def _point_segment_dist(P: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    ab = b - a
    L2 = float(ab @ ab)
    t = np.zeros(len(P)) if L2 <= 0 else np.clip((P - a) @ ab / L2, 0.0, 1.0)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)


def _lm(kit: "TemplateKit", V: np.ndarray, names: Sequence[str], scheme: str = "anatomical44") -> np.ndarray | None:
    """Landmark positions on V, or None when the kit lacks the scheme or a name."""
    pts = kit.landmarks.get(scheme)
    if pts is None or any(n not in pts for n in names):
        return None
    return kit.landmark_positions(scheme, V, list(names))


def _bumps(P: np.ndarray, centres: np.ndarray, widths: np.ndarray) -> np.ndarray:
    """(n, K) Gaussian kernels exp(-|P - c_k|^2 / (2 w_k^2))."""
    d2 = (np.sum(P * P, axis=1)[:, None] - 2.0 * P @ centres.T + np.sum(centres * centres, axis=1)[None, :])
    return np.exp(-0.5 * np.maximum(d2, 0.0) / (widths[None, :] ** 2))


def _log_scale(kit: "TemplateKit", V: np.ndarray) -> tuple[float, str]:
    if "anatomical44" in kit.landmarks:
        src = kit.landmark_positions("anatomical44")
        dst = kit.landmark_positions("anatomical44", V)
        source = "umeyama(anatomical44 rest -> subject)"
    else:
        src, dst, source = kit.vertices, np.asarray(V, float), "umeyama(vertices rest -> subject)"
    s, _, _ = umeyama(src, dst, with_scale=True)
    return float(math.log(s)), source


# =========================================================================== subject
@dataclass
class SurfaceSubject:
    """A surface-level synthetic subject on a template kit's topology (WP-11).

    kit : the template kit (topology, embeddings, regions).
    V_true : (V, 3) true vertex positions, mm (kit vertex order).
    log_scale_true : log size relative to the kit rest shape (see module conventions).
    asym_rms_mm : RMS of the antisymmetric part over the face hemisphere, mm.
    meta : ``{'generator', 'inverse_crime': False, ...}`` plus the drawn parameters.
    """

    kit: "TemplateKit"
    V_true: np.ndarray
    log_scale_true: float
    asym_rms_mm: float
    meta: dict = field(default_factory=dict)

    def landmarks(self, scheme: str = "anatomical44", names: Sequence[str] | None = None) -> np.ndarray:
        """(N, 3) landmark positions: the kit's barycentric embeddings evaluated on ``V_true``."""
        return self.kit.landmark_positions(scheme, self.V_true, names)

    def landmark_names(self, scheme: str = "anatomical44") -> list[str]:
        return self.kit.landmark_names(scheme)

    def triangles(self) -> np.ndarray:
        """Fan triangles of the kit (the index space of the landmark embeddings)."""
        return self.kit.triangles()

    @property
    def symmetric(self) -> np.ndarray:
        return symmetric_part(self.V_true, self.kit.mirror_map)

    @property
    def asymmetric(self) -> np.ndarray:
        return antisymmetric_part(self.V_true, self.kit.mirror_map)


def _features(kit: "TemplateKit", V0: np.ndarray, N0: np.ndarray, rng: np.random.Generator
              ) -> tuple[np.ndarray, dict]:
    """Symmetric feature displacements outside the factor model (WP-11 spec; DESIGN 7.2).

    Draw order: hump amplitude, cleft depth, lip-curve coefficient, cheek amplitude
    (always drawn, so the stream does not depend on which landmarks the kit has).
    """
    hump_amp = float(rng.uniform(_D["hump_amp_min_mm"], _D["hump_amp_max_mm"]))
    cleft = float(rng.uniform(0.0, _D["cleft_depth_max_mm"]))
    lip_u = float(rng.uniform(-1.0, 1.0)) * _D["lip_curve_amp_mm"]
    cheek = float(rng.uniform(-_D["cheek_amp_mm"], _D["cheek_amp_mm"]))
    D = np.zeros_like(V0)
    used: dict[str, Any] = {}
    # Dorsal hump: centred on the midline vertex nearest the n-prn chord midpoint, along normals.
    P = _lm(kit, V0, ["n", "prn"])
    if P is not None and kit.midline.size:
        mid = 0.5 * (P[0] + P[1])
        c = V0[kit.midline[np.argmin(np.linalg.norm(V0[kit.midline] - mid, axis=1))]]
        g = np.exp(-0.5 * np.sum((V0 - c) ** 2, axis=1) / _D["hump_sigma_mm"] ** 2)
        D += (hump_amp * g)[:, None] * N0
        used["dorsal_hump_mm"] = hump_amp
    # Chin cleft: a narrow midline groove (lateral sigma 3 mm) through pogonion, inward along normals.
    P = _lm(kit, V0, ["pg"])
    if P is not None:
        c = P[0]
        g = np.exp(-0.5 * (V0[:, 0] - c[0]) ** 2 / _D["cleft_sigma_mm"] ** 2
                   - 0.5 * ((V0[:, 1] - c[1]) ** 2 + (V0[:, 2] - c[2]) ** 2) / _D["cleft_vertical_sigma_mm"] ** 2)
        D -= (cleft * g)[:, None] * N0
        used["chin_cleft_mm"] = cleft
    # Lip-line curvature: vertical shift u * (|x| / 30)^3 near the mouth line ch_R - sto - ch_L
    # (|x|^3 keeps it mirror-symmetric: corners up or down together).
    P = _lm(kit, V0, ["ch_R", "sto", "ch_L"])
    if P is not None:
        d = np.minimum(_point_segment_dist(V0, P[0], P[1]), _point_segment_dist(V0, P[1], P[2]))
        w = np.exp(-0.5 * (d / _D["mouth_falloff_mm"]) ** 2) * (N0[:, 2] > 0.0)
        D[:, 1] += lip_u * (np.abs(V0[:, 0]) / _D["lip_curve_ref_mm"]) ** 3 * w
        used["lip_curve_mm"] = lip_u
    # Cheek fullness: +/-2 mm along normals on the cheeks region (smooth falloff outside).
    if kit.regions.get("cheeks") is not None and len(kit.regions["cheeks"]):
        w = region_weight(kit, V0, "cheeks", _D["cheek_falloff_mm"])
        D += (cheek * w)[:, None] * N0
        used["cheek_fullness_mm"] = cheek
    return D, used


def _draw_once(kit: "TemplateKit", rng: np.random.Generator, amp_mm: float, asym_mm: float,
               log_scale_sd: float, features: bool, n_bumps: int) -> tuple[np.ndarray, dict]:
    V0 = kit.vertices
    N0 = kit.normals
    m = kit.mirror_map
    face = face_hemisphere(kit)
    if face.size == 0:
        raise ValueError("kit has no face-hemisphere vertices (rest z > %g mm)" % FACE_MIN_Z_MM)
    # 1. symmetric smooth field along the vertex normals (bump + its mirror copy).
    ci = rng.choice(face, size=int(n_bumps), replace=True) if n_bumps > 0 else np.zeros(0, np.int64)
    widths = rng.uniform(_D["width_min_mm"], _D["width_max_mm"], size=int(n_bumps))
    amps = rng.normal(scale=amp_mm, size=int(n_bumps))
    h = np.zeros(len(V0))
    if n_bumps > 0:
        C = V0[ci]
        h = (_bumps(V0, C, widths) + _bumps(V0, C * _FLIP, widths)) @ amps
    V = V0 + h[:, None] * N0
    # 2. features outside the factor model.
    feat: dict = {}
    if features:
        Df, feat = _features(kit, V0, N0, rng)
        V = V + Df
    V = _symmetrise(kit, V)
    # 3. antisymmetric part with RMS asym_mm over the face hemisphere.
    K = int(_D["n_asym_bumps"])
    ai = rng.choice(face, size=K, replace=True)
    aw = rng.uniform(_D["width_min_mm"], _D["width_max_mm"], size=K)
    adir = rng.normal(size=(K, 3))
    adir /= np.linalg.norm(adir, axis=1, keepdims=True)
    acoef = rng.normal(size=K)
    d = _bumps(V0, V0[ai], aw) @ (acoef[:, None] * adir)
    A = 0.5 * (d - d[m] * _FLIP)
    rms = float(np.sqrt(np.mean(np.sum(A[face] ** 2, axis=1))))
    A = A * (float(asym_mm) / rms) if rms > 1e-12 else np.zeros_like(A)
    V = V + A
    # 4. global anisotropic scale, then e^zeta (about the head-frame origin, mid-tragion).
    aniso = 1.0 + rng.normal(scale=_D["aniso_sd"], size=3)
    zeta = float(rng.normal(scale=log_scale_sd))
    V = math.exp(zeta) * V * aniso[None, :]
    params = {"bump_centres": ci.tolist(), "bump_widths_mm": widths.tolist(), "bump_amps_mm": amps.tolist(),
              "features": feat, "asym_target_mm": float(asym_mm), "aniso_scale": aniso.tolist(),
              "zeta_drawn": zeta}
    return V, params


def out_of_prior_subject(kit: "TemplateKit", rng: np.random.Generator, *, amp_mm: float = _D["amp_mm"],
                         asym_mm: float = _D["asym_mm"], log_scale_sd: float = _D["log_scale_sd"],
                         features: bool = True, n_bumps: int = _D["n_bumps"]) -> SurfaceSubject:
    """Draw an out-of-prior surface subject on ``kit`` (DESIGN 7.2; WP-11 spec).

    Construction, in draw order (all displacements in mm on the rest surface):

    1. **Symmetric smooth field**: ``n_bumps`` Gaussian bumps along the rest vertex
       normals, ``h = sum_k a_k (g_k(c_k) + g_k(F c_k))`` with centres ``c_k`` drawn
       uniformly from face-hemisphere vertices (rest ``z > 0``) and mirrored, widths
       ``U(20, 60)`` mm, amplitudes ``N(0, amp_mm^2)``.
    2. **Features outside the 18-factor model** (``features=True``): dorsal hump
       (bump at the midline vertex nearest the n-prn chord midpoint, amplitude
       ``U(-1.5, 2.5)`` mm, sigma 6 mm); chin cleft (groove ``-U(0, 1.2)`` mm through
       pg, lateral sigma 3 mm, vertical sigma 8 mm); lip-line curvature (vertical
       ``u (|x|/30)^3`` with ``u ~ U(-1, 1)`` mm near the ch-sto-ch mouth line, falloff
       sigma 8 mm); cheek fullness (``U(-2, 2)`` mm along normals on the cheeks
       region, falloff 8 mm).  Then exact symmetrisation (midline x = 0).
    3. **Antisymmetric part**: a smooth field ``d`` of 8 Gaussian bumps with random
       3D directions, made antisymmetric ``A = (d - F d[m]) / 2`` and scaled so that
       RMS|A| over the face hemisphere equals ``asym_mm``.
    4. **Global size**: ``V <- e^zeta V diag(1 + N(0, 0.02^2))`` about the origin with
       ``zeta ~ N(0, log_scale_sd^2)``.

    Fold gate: a draw whose smallest triangle area ratio (:func:`area_ratios` against
    the rest kit) is below 0.2 (DESIGN 4.15 det J > 0.2) is rejected and the whole
    subject is redrawn from ``rng`` (at most 50 attempts, then
    :class:`SubjectGenerationError`).

    The ``x^3`` of the WP-11 lip-curvature formula is used as ``|x|^3`` so the
    feature stays symmetric (an odd ``x^3`` would be a lip cant, which belongs to
    the antisymmetric part controlled by ``asym_mm``).
    """
    if asym_mm < 0 or amp_mm < 0 or log_scale_sd < 0 or n_bumps < 0:
        raise ValueError("amp_mm, asym_mm, log_scale_sd and n_bumps must be >= 0")
    tris = kit.triangles()
    fails: list[float] = []
    for attempt in range(int(_D["max_attempts"])):
        V, params = _draw_once(kit, rng, float(amp_mm), float(asym_mm), float(log_scale_sd), bool(features),
                               int(n_bumps))
        ratios = area_ratios(kit.vertices, V, tris)
        rmin = float(ratios.min())
        if rmin >= _D["min_area_ratio"] and np.all(np.isfinite(V)):
            log_s, src = _log_scale(kit, V)
            mirror_rmsd = float(2.0 * asymmetry_rms(kit, V))
            meta = {
                "generator": "out_of_prior_surface",
                "inverse_crime": False,
                "kit_id": kit.id, "kit_topology_sha256": kit.topology_sha256,
                "amp_mm": float(amp_mm), "n_bumps": int(n_bumps), "features_enabled": bool(features),
                "log_scale_sd": float(log_scale_sd), "log_scale_source": src,
                "min_area_ratio": rmin, "attempts": attempt + 1, "rejected_min_ratios": fails,
                "mirror_rmsd_mm": mirror_rmsd,
                **params,
            }
            return SurfaceSubject(kit=kit, V_true=V, log_scale_true=log_s,
                                  asym_rms_mm=asymmetry_rms(kit, V), meta=meta)
        fails.append(rmin)
    raise SubjectGenerationError(f"no fold-free subject in {int(_D['max_attempts'])} attempts "
                                 f"(min area ratios {fails[:5]}...)")


# =========================================================================== expressions
def expression_meta(kind: str, amount: float) -> dict:
    """Ground-truth labels of an expression field (units, whether the engine's model matches it).

    ``model_matched`` is True only for ``jaw_open``: the DESIGN 4.9 jaw hinge
    (rotation about +x through mid-tragion + (0, -5, 11.5) mm, per-vertex jaw
    weights) reproduces it exactly; the other kinds are outside the engine's model
    and must be handled by covariance inflation (DESIGN D-14).
    """
    if kind not in EXPRESSION_KINDS:
        raise ValueError(f"kind must be one of {EXPRESSION_KINDS}, not {kind!r}")
    return {"kind": kind, "amount": float(amount), "units": "deg" if kind == "jaw_open" else "mm",
            "model_matched": kind == "jaw_open"}


def _rot_x(deg: float) -> np.ndarray:
    a = math.radians(float(deg))
    c, s = math.cos(a), math.sin(a)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def expression_field(kit: "TemplateKit", V: np.ndarray, kind: str, amount: float, *,
                     scheme: str = "anatomical44", hinge_mm: Sequence[float] | None = None,
                     return_meta: bool = False):
    """Displace ``V`` (kit topology) by a synthetic expression (WP-11 spec; DESIGN 7.4 jaw/smile rows).

    kind / amount:

    * ``'smile'`` (mm): each mouth corner (the ch_L / ch_R landmark vertices on ``V``)
      moves up ``0.6 a`` and outward (+x for ch_L, -x for ch_R) ``0.4 a`` with a
      Gaussian falloff ``exp(-|X - ch|^2 / (2 * 15^2))`` (the two corner fields add);
      the cheeks region moves up ``0.25 a`` (falloff 15 mm outside it).
    * ``'jaw_open'`` (degrees): ``X' = X + w (R_x(a) (X - c) - (X - c))`` with ``w`` the
      kit's jaw weights and ``c`` = mid-tragion of ``V`` (midpoint of t_L, t_R) +
      (0, -5, 11.5) mm (DESIGN 4.9; for the rest kit, mid-tragion is the origin, i.e.
      the axis through (0, -5, 11.5)).  A positive angle opens the mouth (chin down
      and back).  ``hinge_mm`` overrides ``c``.  This kind is ``model_matched``.
    * ``'brow_raise'`` (mm): the forehead region moves up ``a`` (falloff 10 mm).
    * ``'blink'`` (mm): upper-lid vertices (eyes region, above the pupil of their
      side) move down ``a``, ramped in over ``max(2, 1.5 a)`` mm above the pupil and
      with a 4 mm falloff outside the eyes region (keeps the field fold-free).

    Returns the displaced (V, 3) array, or ``(V', meta)`` with
    ``return_meta=True`` (see :func:`expression_meta`).  ``amount = 0`` returns an
    unchanged copy.
    """
    meta = expression_meta(kind, amount)
    V = np.asarray(V, float)
    if V.shape != kit.vertices.shape:
        raise ValueError(f"V must have the kit's shape {kit.vertices.shape}, got {V.shape}")
    a = float(amount)
    D = np.zeros_like(V)
    if kind == "smile":
        P = _lm(kit, V, ["ch_L", "ch_R"], scheme)
        if P is None:
            raise KeyError(f"kit {kit.id!r} has no ch_L/ch_R in scheme {scheme!r}")
        sig = _D["smile_sigma_mm"]
        for c, sgn in ((P[0], 1.0), (P[1], -1.0)):
            g = np.exp(-0.5 * np.sum((V - c) ** 2, axis=1) / sig ** 2)
            D[:, 1] += _D["smile_up"] * a * g
            D[:, 0] += sgn * _D["smile_out"] * a * g
        D[:, 1] += _D["smile_cheek_up"] * a * region_weight(kit, V, "cheeks", _D["smile_cheek_falloff_mm"])
        meta["corners"] = P.tolist()
    elif kind == "jaw_open":
        if hinge_mm is not None:
            c = np.asarray(hinge_mm, float).reshape(3)
        else:
            T = _lm(kit, V, ["t_L", "t_R"], scheme)
            mid = np.zeros(3) if T is None else 0.5 * (T[0] + T[1])
            c = mid + np.array([0.0, _D["jaw_hinge_y_mm"], _D["jaw_hinge_z_mm"]])
        R = _rot_x(a)
        Y = V - c
        D = kit.jaw_weights[:, None] * (Y @ R.T - Y)
        meta["hinge_mm"] = c.tolist()
        meta["axis"] = [1.0, 0.0, 0.0]
    elif kind == "brow_raise":
        D[:, 1] = a * region_weight(kit, V, "forehead", _D["brow_falloff_mm"])
    else:  # blink
        P = _lm(kit, V, ["p_L", "p_R"], scheme)
        if P is None:
            raise KeyError(f"kit {kit.id!r} has no p_L/p_R in scheme {scheme!r}")
        w = region_weight(kit, V, "eyes", _D["blink_falloff_mm"])
        near_L = np.linalg.norm(V - P[0], axis=1) <= np.linalg.norm(V - P[1], axis=1)
        y_p = np.where(near_L, P[0, 1], P[1, 1])
        ramp = max(_D["blink_ramp_min_mm"], _D["blink_ramp_per_mm"] * abs(a))
        wy = np.clip((V[:, 1] - y_p) / ramp, 0.0, 1.0)
        D[:, 1] = -a * w * wy
        meta["ramp_mm"] = ramp
    out = V + D
    return (out, meta) if return_meta else out
