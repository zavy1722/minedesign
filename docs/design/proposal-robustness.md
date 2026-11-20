# Proposal: a robustness-first photo-to-head engine

*Design angle: robustness first, built for the photos people actually take. Dated 2026-11-20. Based on `face3d/` at 887c5e5 (42 tests passing) and `research/_raw/requirements_*.md`.*

**Citation badges.** Each cited value carries its note's badge:

| Badge | Meaning |
|---|---|
| ✅ | verified |
| 📄 | single source |
| 🧠 | unverified expert knowledge |
| ↔️ | contested |
| 🆕 | introduced here; unsourced, so it must be calibrated on the test bed (§5) |

The notes for `open-template-head-kit` and `cranium-under-hair` are not written yet, so citations to them refer to draft tables in `research/data/`. Every 🧠 and 🆕 value is a named, badged config entry.

## 0. Thesis

The tool will be judged on mirrored selfies, EXIF-less messenger copies, beards, and a smile in the only three-quarter view. Four rules follow:

1. Every failure mode gets a simple test that can be checked.
2. Weak evidence is down-weighted or excluded, never fitted through.
3. Each region states what it can still claim.
4. Every default is earned on a fault-injection test bed.

When a simple method and a clever one compete, the simple one wins.

## 1. Vision and user journey

1. **Consent.** A `ConsentRecord` is created first (ethics §2.1). Nothing runs without the `RECONSTRUCT` scope.
2. **Photos.** Each photo is hashed and its EXIF read: orientation, focal length, lens, date and editing software. Orientation is baked into a working copy, and the original is left untouched.
3. **Landmarks.** They come from MediaPipe (an external helper or an optional wheel) or from manual pins. Pins and JSON import always work, so no download is ever needed (ethics A4).
4. **Triage.** Each photo gets a QA card. Each flag states its action and the reason, for example *"selfie at ≈0.35 m: colour and frontal outline only"*.
5. **Solve.** Robust multi-view bundle adjustment (BA) runs, followed by a mirror check and an observability report.
6. **Fit.** The CC0 template is warped in stages, then fitted to contours. Profiles are traced with edge snapping.
7. **Review.** A claims ledger rates each region *measured*, *constrained*, *prior-driven* or *unobserved*. It comes with held-out checks, per-camera overlays, the worst landmarks, and the next photo that would help most ("add a left profile").
8. **Hand-off.** The fit lands as shape keys on stable topology, with an `artist` layer, a Multires copy, an optional gated texture and export provenance.

**Promise by input tier.** The tier is computed from the evidence, never picked by the user.

| Tier | Typical input | Promise | Label |
|---|---|---|---|
| S | ≥ 5 views over ±60–90° yaw at 1.5–3 m; tele lens; EXIF; scale reference | Metric; depth measured; face RMS ≤ 1.5 mm (benchmarks-metrics T6 🧠) | `metric` |
| A | Rear phone camera; ≥ 3 views, one at \|yaw\| ≥ 45°; EXIF | Proportions; depth where coverage holds (§3.10); iris scale ±2–4 % (multi-view-fitting 🧠) | `iris-scaled` |
| B | Camera roll: mixed devices and dates, missing EXIF | Frontal proportions; depth from the prior unless some view is beyond 60° yaw | `proportions only` |
| C | One photo, or selfies only | Blockout through its own camera; no claims on nose projection, ears or cranium | `blockout` |

## 2. Architecture

### 2.1 Modules

The engine imports only `numpy`, `math`, `json`, `struct`, `zlib`, `hashlib` and `tomllib`. All imports are relative, and `bpy` is never imported (blender A1). The St column marks each module as E (exists), X (extend) or N (new).

| Path | St | Purpose |
|---|---|---|
| `face3d/core/{schema,policy,config}.py` | N | Formats; consent scopes; licence taint (AND over components; ethics A2); badged defaults |
| `face3d/io/exif.py` | X | Add DateTimeOriginal, Software, DigitalZoomRatio, LensMake, SubjectDistance; read all APP1 segments |
| `face3d/io/{heif_exif,png,image_ops,landmarks}.py` | N | HEIC EXIF from ISOBMFF boxes; stdlib PNG; orientation and flip with label permutation; landmark adapters |
| `face3d/qa/{image,photo,expression,mirror,retouch,flags}.py` | N | Gates (§3.1, §3.6); flag registry (code, severity, evidence, action, source) |
| `face3d/solve/pnp.py` | X | Multi-start, cheirality, twin flag, CAM-3 hypotheses, Huber in σ units |
| `face3d/solve/{noise,observability}.py` | N | §3.2; σ(log f), σ(log z), P, leave-one-view-out (LOVO) |
| `face3d/solve/bundle.py` | X | Covariance blocks, visibility, jaw hinge, distance priors, soft focal tie, view cap, rejection, Schur marginals |
| `face3d/model/{registry,template_kit,prior,nuisance}.py` | N | Landmark registry (anatomy R2.1), hash-checked kit, priors, jaw, occluders |
| `face3d/fit/{template,silhouette}.py` | X | Gated stages, reflection check; sliding and one-sided contours |
| `face3d/fit/{contour_trace,uncertainty}.py` | N | Dynamic-programming edge snap; vertex σ; ledger |
| `face3d/geometry/rbf.py`, `mesh/laplacian.py` | X | Per-landmark Λ; per-vertex stiffness |
| `face3d/{texture,eval,testbed}/` | N | Z-buffer blending; point-to-triangle metrics (reconstruction EV-1); scenarios |
| `face3d/pipeline.py`, `__main__.py` | N | Deterministic runner; CLI `python -m face3d {triage,solve,fit,report,testbed}` |
| `tools/{detect_mediapipe,build_template_kit,build_extension}.py` | N | Detector helper (Tasks API, `IMAGE` mode, `num_faces=2`, test-time augmentation (TTA)); hash-checked builds |
| `blender_ext/face3d_head/` | N | The extension (§4); engine vendored at build time |

### 2.2 Data flow

```
photos → ingest (sha256, EXIF, orientation, consent) → LandmarkSet (+TTA spread)
→ triage (flags, tags, σ multipliers, focal ladder) → multi-start PnP + mirror test
→ robust BA → observability + LOVO → warp A→B→C → contours D → uncertainty → ledger
→ result.json/fit.obj/sigma.npy → Blender → artist → gated texture → export
```

Each stage is a pure function, cached by the hash of its inputs and config. Editing one pin re-runs only the stages downstream of it.

### 2.3 Data formats

Files are JSON with `format` and `version` fields. Arrays larger than about 1,000 values go to `.npy` files, referenced by path and SHA-256.

```json
{"format":"face3d.project","version":1,"seed":1234,"consent_id":"…","template":"mpfb2-hm08-head@1",
 "photos":[{"id":"p03","path":"photos/IMG_0412.HEIC","sha256":"…","rights_basis":"self_shot",
   "exif":{"f35":26,"lens_model":"…front…","datetime":"…","software":null,"orientation":6,"pixel_wh":[3024,4032]},
   "tags":{"view":"front","expression":"auto","occluders":["glasses"],"mirrored":"auto"},
   "landmarks":"lm/p03.json","contours":["ct/p03_profile.json"],"include":"auto"}],
 "scale_refs":[{"kind":"card_id1","photo":"p01","mm":85.60,"sigma_mm":0.5}],
 "pins":[{"photo":"p03","landmark":"prn","uv":[1510.2,2011.7],"sigma_px":4}]}
```

```json
{"format":"face3d.landmarks","version":1,"scheme":"mediapipe478",
 "detector":{"backend":"mediapipe-tasks","version":"…","model_sha256":"…","licence":"Apache-2.0","commercial_ok":true,"is_ml":true},
 "image":{"sha256":"…","wh":[3024,4032],"orientation_applied":true,"input_flipped":false,"coords":"px_corner"},
 "faces":[{"score":0.97,"uv":"lm/p03_uv.npy","blendshapes":{"jawOpen":0.02},"tta_spread_px":"lm/p03_sd.npy"}]}
```

- **Scheme file.** Our own CC0 file, bundled with the add-on. The scheme is always read from this file, never inferred from N (reconstruction FMT-1). Fields:
  - `lr_permutation`, `midline`, `classes`
  - `convention`: surface or semi-contour
  - `sigma_iod` per class
  - `anatomical` name → index map
  - `verification`
- **Template sidecar.** Built by the kit builder. Fields:
  - `source`: upstream SHA-256 and `CC0-1.0`
  - `units: mm`, `topology_sha256`, `order_checksum`
  - `landmarks`: kind, tri, bary, σ, provenance
  - `scheme_maps` per detector version
  - `regions`, `mirror_map`, `contours`, `stiffness`
  - `basis`: K, SHA-256, status
- **Result file.** Fields:
  - `config_sha256`, `seed`, input hashes, `tier`
  - per camera: K, R, t, f35, z, P, σ_logf, `focal_status`, mirror `{decision, Δ, status}`
  - per view: RMS in % IOD (in-sample and LOVO), `noise_scale`, `weight_share`, `rejected_frac`, flags
  - `scale {mode, s, σ}`
  - landmarks with covariance
  - `regions [{name, status, k, σ_mm, why}]`
  - `licence {commercial_ok, components}`
  - mesh and per-vertex σ

### 2.4 Coordinate conventions

All conventions live in `core/schema.py` and each has a round-trip test.

- **Image.** Coordinates are continuous, with the origin at the top-left pixel's corner, so pixel (i, j) has its centre at (i + ½, j + ½), as in `camera.py`.
  - MediaPipe maps as u = x·W.
  - Resizing maps as u·W/W′. The "+0.5" form from blender D3 is not used.
  - A flip is u′ = W − u with the label permutation π.
- **Camera.** OpenCV, X_c = R·X_w + t.
- **Head frame.** Millimetres, float64. +x is the subject's left, +y up, +z forward; the origin is midsagittal (anatomy R1.1).
- **Blender.** An `R_x(+90°)` parent maps (x, y, z) → (x, −z, y) at scale 0.001 (blender A8).
- **IOD** means ex–ex (landmark-detection T2). Interpupillary values are converted with ×0.70 (T3 🧠). Per view, IOD_px = f·IOD_mm/z_v. The raw 2D ex–ex distance halves at 60° yaw, so it is not used.
- **Determinism.** Use `default_rng(seed)`, fixed hypothesis order, stable sorts and float64 throughout. Golden tests use rtol 1e-5 (blender Q2). CI runs Python 3.11 with NumPy 1.26 and Python 3.13 with NumPy 2.x (A4).

## 3. Algorithms

### 3.1 Input QA gates

No gate ever pulls a value toward a norm (anatomy §6). Each gate takes one of five actions: down-weight, drop a landmark class, exclude the photo from geometry, exclude it from texture, or ask the user.

| Failure | Detection | Action | Source |
|---|---|---|---|
| Orientation ignored | `exif_applied` false; view RMS > 3σ; roll ≈ ±90° | Bake, re-detect | blender §10 🧠 |
| EXIF stripped | No Make, Model or f35 | Source-type prior (§3.3) | community R2.2 🧠 |
| Crop or zoom | Size ≠ PixelXDimension; aspect not native; zoom > 1 | σ_logf 0.08–0.10; free principal point (σ 10 %) | community R2.5 🧠 |
| Front camera | LensModel contains "front" | Mirror test; selfie distance prior | camera-perspective-distortion 🧠 |
| Near camera | Solved z, checked against f·63/IPD_px. Warn below 1 m, strong warning below 0.8 m | Below 0.6 m: 2D and texture only | community §9 🧠 |
| Face-warp correction | f35 ≤ 16 mm, face beyond 60 % of the half-diagonal, or > 25° off-axis | σ × 2 or exclude | community R1.7 (warp ✅, thresholds 🧠) |
| Low resolution | Face < 250 px warns, < 120 px rejects; iris < 20 px | σ floor; no iris scale; no detail | community R1.4 🧠, R4 ↔️ |
| Blur, blink, clipping | Laplacian variance in bottom 20 %; eye aspect ratio (EAR) < 0.2; > 2 % of skin clipped | Down-weight; drop lids; no photometry | community R1.4 🧠 |
| Mixed dates | Span > 18 months | Date clusters | community §9 🧠 |
| Two faces; no consent | `num_faces=2` at ≥ 0.6; sha256 not consented | User picks; block | blender ML 🧠; ethics F1–F2 |

### 3.2 Noise model

For landmark i in view v, with t̂ the tangent taken from neighbouring points:

Σ_iv = s_v²·m(c_i, tag_v)²·R(t̂)·diag(σ_n², σ_t²)·R(t̂)ᵀ
σ_• = max(σ̂_•(c_i)·IOD_v·√(N/N_eff), σ_tta, σ_floor)

- **σ̂ by class**, in % IOD, normal/tangent (landmark-detection T5 🧠): iris 1.0; anchors 1.5; lid and lip contours 2/5; pronasale 2.5; brows 3–5/6; jaw 2.5/10–15.
- **Dense-point inflation.** N_eff = 60–100. The √(N/N_eff) term applies only outside a curated subset of about 100 points.
- **σ_tta** is the spread over 6–10 TTA passes (BA-2 🧠).
- **σ_floor** = max(0.5 px, k·face_px/256), with k = 0.6 for inner points, 0.4 for the iris, 1.0 for brows and 1.5 for contours (blender ML 🧠).
- **Per-view scale.** s_v² = clip(median‖Σ^{−½}r‖²/1.386, 1, 9), where 1.386 is the median of χ²₂ (a MAD-style estimate; deformation-fitting-math 🧠). Retouched, warped or misoriented views therefore lose weight automatically. Flag the view if s_v > 2 (🆕).
- **View weights.** w_v = 1/(views in the same 15° yaw bin). No view may contribute more than 40 % of the total information (community R1.8 🧠).

This model replaces `sigma_px = 1.0`, which is about 13× too tight (landmark-detection 🧠).

### 3.3 Camera initialisation

**Focal prior.** The first matching rule sets the log-normal prior (CAM-6, community R2.2 🧠):

| Evidence | Prior |
|---|---|
| SfM import or calibration | σ_log 0.005–0.02 |
| Uncropped EXIF f35 | σ_log 0.04 |
| EXIF f35, suspected crop | σ_log 0.08–0.10 |
| Focal-plane resolution | σ_log 0.10 |
| Phone without focal data | 26 mm, σ_log 0.25 |
| Nothing | 50 mm, σ_log 0.6 |

The current 0.35 fallback cannot reach phone lenses.

**Focal groups.** Photos sharing (Make, Model, LensModel, f35, W, H, still/video) form a group with a soft tie, σ 0.02 (CAM-5 🧠).

**Distance prior on log z.** Front camera 0.35 m (σ 0.3); rear camera 0.8 m (σ 0.4); tele 2 m (σ 0.4) (CAM-6 🧠, σ read as log). Unknown: 1.0 m, σ_log 0.7. Taped: ±5 cm (community R2.4 🧠). Bounds 0.25–10 m (blender C6).

**Multi-start PnP.**
- f35 hypotheses: {13, 24, 26, 35, 50, 77, 85, 120, 135, 200} (CAM-3 🧠). The current list lacks 26, 77 and 120.
- Each hypothesis starts from an affine, a pitch-flipped and a yaw-mirrored pose.
- Poses that fail cheirality are dropped.
- If two poses more than 10° apart score within 20 % of each other, raise `C-TWIN` and carry both into BA (🆕).

**Off-axis faces.** Rotate the face ray onto the optical axis, initialise, then rotate back (camera-perspective-distortion 🧠).

**View order.** Solve the most frontal, most complete view first. Initialise the remaining views against the BA consensus, not the template, to reduce mean-face pull.

### 3.4 Mirrored images

Let X̂ be the consensus of the other views (or the template if there is only one view). Let C₀ be the robust PnP cost of a view as given, and C₁ its cost after a flip (u′ = W − u, labels permuted). The test statistic is Δ_v = (C₀ − C₁)/C₀.

**When the test can decide.** Let A = ½(X̂ − M·X̂_π) be the asymmetric part of the shape, and g = Σ‖Σ^{−½}J_i A_i‖² the expected cost gap. If g < 4 (🆕), the result is `undetermined`: a near-symmetric face seen through noisy landmarks cannot be told from its mirror image, and the tool says so.

**Decision.** If Δ_v > 0.2 (community R1.6 🧠), the view is mirrored.
- If the photo came from a front camera, or the other views agree, it is flipped automatically and the flip is logged.
- Otherwise the user decides, prompted to check the hair parting or a mole (likeness-mistakes 🧠).

**All views mirrored.** If every view is mirrored (for example, selfies only), the geometry cannot detect it. The result is marked `mirror: unverifiable`, and every asymmetry claim is flagged.

### 3.5 Robust bundle adjustment

E = Σ_v w_v Σ_i ρ_H(‖Σ_iv^{−½}(π_v(X_i + J_i(θ_v)) − u_iv)‖; δ = 2) + Σ_v E_contour,v
  + Σ_g ((log f_g − μ_g)/σ_g)² + Σ_{v∈g} ((log f_v − log f_g)/0.02)² + Σ_v ((log z_v − μ_z)/σ_z)²
  + E_shape(X) + Σ_pairs ‖Σ_sym^{−½}(X_l − M·X_r)‖² + Σ_mid (x_i/σ_mid,i)² + E_scale + E_pins

- **Robust loss.** Huber at 2σ in σ units, replacing the 3 px threshold in PnP and 3σ in BA. After convergence, drop residuals beyond 4σ and re-solve once. Flag any view that loses more than 15 % of its points (BA-5 🧠).
- **Visibility.** Weight is 0 when n·(−v) < cos 80° and rises to 1 at cos 60°. Far-side oval points are dropped when |yaw| > 25° (BA-3 🧠).
- **Symmetry and midline σ** (anatomy R4.2 🧠):
  - pairs: canthi 0.7–1.0 mm, brows 1.5, alae 1.0–1.5, cheilia 1.5–2.0, gonia 2.5–3, ears 3–4;
  - midline: n 0.75–1.0 mm, prn and sn 1.5–2.0, pg and me 2–3.
- **Covariance.** Use the Schur complement once N ≥ 100. Report each landmark's prior share p_i = σ²_post/σ²_prior. *Likeness mode* widens the prior until p_i ≤ 0.2 wherever at least 2 views see the landmark (anatomy R1.4 🧠).
- **SfM cameras.** Triangulate, align with Umeyama, then run a 3D shape solve. Landmarks never move SfM cameras (BA-12 🧠).

### 3.6 Expressions, occluders and retouching

**Expression tags.** Blendshape scores are read as Δb, the rise above the subject's own minimum across views (landmark-detection 🧠).

| Tag | Rule |
|---|---|
| *Neutral* | Every Δb under its limit: jawOpen 0.08, mouthSmile 0.15, eyeBlink 0.35, browInnerUp 0.2 |
| *Expressive* | Smile > 0.25; squint, eyeWide or brow > 0.3; or blink > 0.4 (anatomy §6 🧠) |
| *Mild* | In between |

Without blendshapes, geometric proxies apply:
- Inner-lip gap / ch–ch > 0.04 means parted lips; drop sto and li (anatomy §6 🧠).
- Mouth width > 1.08× the median means a smile (🆕).

Tags are refined from the residuals for at most 3 rounds (BA-9 🧠).

**σ multipliers** (neutral / mild / expressive; expression-neutralization 🧠):

| Landmark class | Neutral | Mild | Expressive |
|---|---|---|---|
| Rigid | 1 | 1 | 1–1.5 |
| Semi-mobile | 1 | 1.5–2 | 2–3 |
| Mobile | 1 | 3 | dropped |
| Jaw-dependent (θ fitted) | 1 | 1 | 1 |

**Jaw hinge.** X_i(θ) = c + R_axis(θ)(X_i − c). The axis runs through the template condyles, about 10–13 mm anterior to tragion (BA-1 🧠). On neutral views, θ ~ N(1.5°, 1°), bounded to 0–30° (anatomy §4 🧠). The hinge needs no expression data.

**Expression basis ψ.** Opt-in only, through licence-clean adapters such as FLAME 2023 Open. The neutral views anchor it with mean ψ ≈ 0, σ 0.1 (BA-9 🧠). If no view is neutral, sub-millimetre mouth and lid measurements are suppressed.

**Occluders.** The user sets tags with one click; there is no licence-clean default detector.

| Occluder | Handling |
|---|---|
| Glasses | Eye σ ×2; no iris scale; lid points under the frame dropped (anatomy R3.4 🧠). Consistency check: lenses magnify ≈1–1.5 % per dioptre, so flag a view whose iris/(en–ex) ratio is more than 3 % off the glasses-free median (🆕) |
| Beard | pg, gn, me and jaw points dropped; the beard outline becomes a one-sided bound; jaw is *prior-driven* unless a shaven photo exists (reference-photography-protocol, community R5.4 🧠) |
| Hair | Ear and temple weight 0; no silhouette above the trichion (blender S3 🧠) |
| Makeup | Lip and brow borders σ ×2 (artstation-likeness 🧠) |

**Retouching and beauty filters.** Three tests, each relative to the other views:
1. EXIF `Software` names a known editor (🆕).
2. SSI_v = cheek band energy ÷ brow-and-iris band energy, measured at matched mm/px, falls below 0.5× the set median (🆕).
3. Regressing the residuals on fixed eye-radial-outward and jaw-normal-inward patterns gives t > 3.

A flagged view gets σ ×2–3 and is excluded from texture (artstation-likeness ↔️; tests 🆕). A filter on the only photo cannot be detected, and the ledger says so.

**Non-pinhole processing.**
- A diagnostic k₁ (prior σ 0.02) with |k₁/σ| > 3 on a phone JPEG means "non-pinhole processing suspected" (CAM-1 🧠).
- A radial-residual slope against ρ_i·δ_i that implies more than 5 % magnification error means the distance or focal length is wrong (community R2.8 🧠).

### 3.7 Licence-clean shape prior

No permissive head model built from a large population is confirmed to exist (reconstruction §12). The prior therefore has three layers:

1. **Baseline:** an anisotropic Gaussian per landmark, at 1.0–1.5× the population SD, falling back to 8 mm (anatomy R4.1 🧠). Ratio priors are used only as diagnostics.
2. **Experimental:** X = μ + B·c, with c ~ N(0, I). B is a mass-weighted SVD of the CC0 MPFB2 face targets (K 40–80). Its variances come from an "anthropometric morphable model": 2,000–5,000 sampled heads matched to published norms, keeping 95–99 % of the variance (open-template-head-kit 🧠). It stays off until it lowers held-out error without losing coverage.
3. **Opt-in:** FLAME 2023 Open, loaded from a user path, SHA-256 pinned and attributed (CC-BY-4.0; contents unverified 📄). Any other FLAME version, or BFM, sets `commercial_ok=false` (LIC-1).

**Gates.**
- ‖c‖² > χ²_K(99.9 %) or any |c_i| > 3: implausible (MM-5 🧠).
- ‖c‖² < K − 2√(2K): "pulled toward average" (community R5.8 🧠).

**Nothing is fabricated.**
- Template landmarks are clicked by two annotators, who must agree within 1 mm (🆕).
- MediaPipe maps come from detector-semantics calibration: render the template from 20–50 cameras, run the detector, and store each index's mean barycentric landing point (landmark-detection 🧠).
- Both are built offline with provenance. CI checks only hashes, schemas, L/R involution and midline fixity.

### 3.8 Contours, silhouettes, profiles and hair

**Edge snap.** The input is a coarse polyline: at least 5 clicks, or the oval points. Each of its M stations may move by an offset k ∈ [−L, L] along its normal, with L = 3 % IOD. The snap minimises

C = Σ −g_j(k_j) + λΣ|k_j − k_{j−1}|

where g is the gradient magnitude after a 1 px Gaussian and λ = 0.2·median g (🆕). Viterbi solves this in O(M·L²). It is deterministic and has no learned weights. Each point gets σ_n = max(1 px, 1/√curvature). SAM (Apache-2.0) is available as an optional mask source, and only in the helper.

**Sliding residuals.** r = n̂·(p_j − q)/σ_n, against the nearest outline segment, re-matched every iteration (BA-4, blender S1 🧠). This is combined with the existing outline-to-vertex term at 10 % trimming. The match gate is 5 % IOD rather than 60 px (🆕).

**One-sided masks.** For hair, beards and hats, r = max(0, d_mask + m)/σ, with m = 0–3 mm (community R5.4 🧠) and weight 10× that of skin (cranium-under-hair 🧠).
- The scalp stays at least 2 mm inside the hair hull (blender W7 🧠).
- Cranium σ follows the visual-hull overshoot: 7.8 mm with 4 views, 1.9 mm with 8 (cranium-under-hair, arithmetic).

**Profiles.** When |yaw| > 60–70°, detector points are discarded (landmark-detection 🧠). User pins on g, n, prn, sn, ls, li and pg are used instead, at σ 1 % IOD (blender S4 🧠).

**Acceptance.**
- Profile error ≤ 1–1.5 mm at the nose tip and chin (SIL-3 🧠).
- Contour within 1 % of face height (S5 🧠).
- If the interior fits but the contours fail, report "f and z wrong", not a shape error.

### 3.9 Template warp

| Stage | Operation | Advance when |
|---|---|---|
| A | Umeyama, proper and reflected. If the reflected RMS is below 0.5× the proper RMS, flag "mirrored source" and never auto-flip. If the 7-landmark RMS exceeds 10 mm, the axes are wrong (blender W2 🧠) | Always |
| B | RBF with φ = r: (Φ − Λ)w + Pa = y, Λ = diag(α·σ_i²), α = 10⁻² (MM-8 🧠; sign already fixed) | Landmark RMS < 2–3 % IOD (community R5.2 🧠) |
| C | Bilaplacian with per-vertex stiffness: lid margins 3.0, lips 0.3, forehead 0.5, ligaments 3–5 (anatomy R5.9 🧠). Offsets capped at 3–5 mm unless at least 2 views agree (MM-10 🧠) | RMS gain < 1 % per iteration |
| D | Silhouettes via `ReducedDeformer`; no landmark may move more than 0.5 mm | Contour ≤ 1 % of face height |

**Gates at every stage:**
- det J > 0.2 with no flipped triangles (MM-11 🧠);
- lid–globe gap of 0–0.3 mm (blender §4 🧠);
- mirror RMSD of 0.3–1.5 mm (anatomy §6 🧠).

Targets are never symmetrised. Detail transfer is off by default. It is allowed only from neutral, unfiltered views at ≤ 0.08 mm/px, and only where at least 2 views agree. Otherwise detail is labelled `synthetic` (anatomy R5.11 🧠).

### 3.10 Uncertainty and the claims ledger

**Propagation.** Stages B and C are linear in the targets: V = V₀ + A(X − X₀). Unit solves give A, and then

Cov(V_j) = Σ_ab A_ja A_jb Cov(X_a, X_b) + σ²_res·I

- σ_res by region: lids 1–1.5 mm, nose 2–3, cheeks 2.5–4, ears 3–5, scalp 3–6, neck 5–10 (open-template-head-kit 🧠).
- A is verified by finite differences.

**Reported σ.** σ_rep² = σ²_post·max(1, κ²) + σ²_bias.
- κ is the LOVO ratio of observed to predicted error.
- σ_bias is 1–3 mm per class until a semantics map exists, because detector bias does not average away (reconstruction principle 5 🧠).

**Status.** With k = 1 − σ²_post/σ²_prior:
- *measured*: k ≥ 0.8 (anatomy §6 🧠) and the coverage rule below holds;
- *constrained*: 0.5 ≤ k < 0.8;
- *prior-driven*: k < 0.5 (🆕);
- *unobserved*: no view sees it.

**Coverage rules.**
- Depth needs at least 2 views at least 30° apart (blender C7 🧠).
- Nose and chin projection need a front view plus one at |yaw| ≥ 60°.
- The jaw underside needs a low view (community R5.9 🧠).
- Ears need |yaw| ≥ 30° and pitch fixed by at least 2 views (R3.3 🧠).

**Focal length and scale.**
- Focal length is estimated only when σ(log f) < 0.10 (blender C2 🧠). If σ exceeds 0.8× the prior σ, the result reads "focal from prior" (CAM-7).
- Scale is labelled *measured* (a caliper overrides all other cues; anatomy R3.4), *iris*, *IPD prior* or *proportions only*. References that disagree by more than 1 % are flagged (BA-10 🧠).

**Next-best photo.** Simulate candidate views on a 15° grid. Recommend the one that most reduces σ in prior-driven regions, weighted by the T6 region weights (benchmarks-metrics 🧠).

### 3.11 Texture projection

Projection runs only if all three gates pass:
- reprojection error has median ≤ 1.5 px and maximum ≤ 3 px (blender T2 🧠);
- consent includes `TEXTURE`;
- `rights_basis ≠ unknown` (ethics §3).

Method (TEX-1…7 🧠):
- numpy z-buffer with tolerance max(1 mm, 2σ_geom);
- view weight vis·cos²θ·footprint·edge, fading between 60° and 75°;
- linear-RGB gains with log-σ 0.3 under auto exposure;
- two-band blend split at 3 mm;
- 2048 px maps for phone sources.

Filtered, retouched, warped or clipped views, and views from other date clusters, never feed the albedo. Texture is never mirrored. Without a colour chart, the result is labelled "absolute albedo unknown".

## 4. Blender add-on

`blender_ext/face3d_head/` contains:
- the manifest;
- `__init__.py`, with `compat.py` probes that finish in under 100 ms;
- `bridge.py`, the only module that converts between bpy and numpy;
- `ops_*.py`, `ui_panels.py`, `overlays.py`, `jobs.py` and `keys.py`;
- the vendored `face3d/`;
- the CC0 `assets/template/`;
- `LICENSE` and `NOTICE`.

| Operator | Does | Runs |
|---|---|---|
| `project_new`, `photos_add` | ConsentRecord; hash, EXIF, orientation-baked copies, GPS stripped (ethics F12) | main |
| `landmarks_import`, `detect` | Imports JSON, or runs the helper or wheel | job |
| `pin_edit`, `trace_contour` | Pins in the photo camera, with σ from zoom; polyline, then edge snap | modal |
| `triage`, `solve`, `fit` | §3.1–3.10 | job |
| `apply_result` | Writes cameras, keys and attributes. Refuses if the topology hash differs or the object is in Edit or Sculpt mode (blender K1/K4) | main, UNDO |
| `bake_for_sculpt` | Duplicate, bake the key mix, clear keys, add Multires 2–3 (K5, SK-3 🧠) | main, UNDO |
| `project_texture`, `review_sheet`, `prepare_sharing`, `export` | §3.11, §5.5; purges leftovers (ethics F9); provenance and consent gates | job / main |

Operator ids are prefixed `face3d.`.

**Panels and overlays.**
- Panels (Sidebar › *Face3D*):
  - Project & Consent;
  - Photos: UIList with QA badges, tags, include and mirror state;
  - Solve: tier, focal status, z, P;
  - Fit: stages and gates;
  - Review: ledger, LOVO, worst landmarks, next-best photo;
  - Export: blocking reasons.
- `gpu` overlays in each photo camera: σ ellipses, residual arrows (×5), rejected points in red, traced outline against the projected silhouette, and a flipped thumbnail for the mirror prompt.
- In 3D, the `face3d_sigma_mm` and `face3d_status` attributes colour the viewport, and region face sets drive masks.

**Undo.** Engine state lives in hashed sidecars, outside the undo stack. Objects carry `face3d_uuid` and are re-fetched by it after undo. Jobs record the target's topology hash and refuse to apply if it has changed.

**Background jobs.**
- A job runs `[sys.executable, "-I", launcher.py, job_dir]`, with its JSON and `.npy` files under `extension_path_user`.
- A timer polls every 0.1 s and does at most 20 ms of work per tick (blender A5 🧠).
- Cancel kills the process, so a crash never loses sculpt work.
- Under `bpy.app.background`, jobs run synchronously.

**Shape keys** (blender K2/K3 🧠):
- `Basis` holds the template mean.
- `F3D_stageB` and `F3D_stageD` are diagnostics, set to 0.
- `F3D_ID_v<n>` holds the likeness, written with `from_mix=False`, `slider_max` 1.5.
- `artist` is kept as a Δ across refits.
- Expression keys need `RIG_ANIMATE` consent (ethics F4).
- Nothing is applied in place or remeshed.

```toml
schema_version = "1.0.0"
id = "face3d_head"
version = "0.1.0"
name = "Face3D Head Fitter"
tagline = "Fit a sculpt-ready head to photos of a consenting person"
maintainer = "Face3D contributors <maintainers@example.invalid>"
type = "add-on"
blender_version_min = "4.5.0"
license = ["SPDX:GPL-3.0-or-later"]
tags = ["Sculpt", "Mesh", "Camera"]

[permissions]
files = "Read reference photos and write project sidecars and textures"

[build]
paths_exclude_pattern = ["__pycache__/", "*.pyc", "tests/", "*.blend1"]
```

**Store build.**
- No wheels and no network permission.
- CC0 assets only (blender L1).
- Engine files carry MIT SPDX headers inside the GPL-3.0-or-later package (ethics A1).
- The minimum Blender version is the oldest line CI tests (Q3).

**GitHub build.** Adds per-platform MediaPipe wheels and a NOTICE. Whether this is compliant is ↔️. The helper runs in any Python, so cp313 wheel lag never blocks anything (blender-python-ml-deps 🧠).

## 5. Validation and QA

### 5.1 Test pyramid

1. **Unit and oracle tests.**
   - Jacobians match numeric derivatives.
   - Noiseless RMS < 10⁻⁶.
   - Camera↔Blender round trip within 10⁻⁶·s; OBJ round trip within 2 µm (blender Q1/Q2 🧠).
   - Schema and policy tables.
   - Each QA gate on synthetic arrays: blurred checker, clipped ramp, smoothed noise.
2. **Scenario test bed** (`face3d/testbed`, seeded). Each scenario combines a subject, a protocol, a detector model and a set of faults.
   - Subjects: `random_subject` with 0.8 mm RMS asymmetry (facial-asymmetry 📄).
   - Protocols: studio ring, rear phone, selfie, camera-roll mix.
   - Detector model: class σ; a per-index bias field of 1–3 mm, shared across views (reconstruction principle 5 🧠); 5 % outliers; TTA spread.
   - A numpy rasteriser renders masks and procedural images.
3. **Bridge tests.** Pure functions (axis mapping, key planner, zip builder). A `tomllib` manifest lint checks the licence, a tagline of at most 64 characters, no numpy wheel and no network permission. A headless script runs `blender -b --factory-startup --python-exit-code 1` for CI elsewhere.

### 5.2 Fault-injection matrix

All targets are 🆕. M1 records the current engine as the baseline.

| Fault | Must raise | Required | Degradation bound |
|---|---|---|---|
| 1 mirrored view among ≥ 3 | `Q-MIRROR` | TPR ≥ 0.95 at ≥ 0.8 mm asymmetry; FPR ≤ 0.02; `undetermined` if symmetric | shape ≤ 1.1× clean |
| Orientation not baked | `Q-ORIENT` | TPR ≥ 0.99 | — |
| EXIF ±30 % crop, or missing | `C-FOCAL-PRIOR` if unobservable | focal < 5 % off when views span ≥ 60° (community R8.4 🧠) | ≤ 1.2× clean |
| Selfies at 0.35 m | `Q-SELFIE`, tier ≤ B | z within 15 % | nose-width error ≥ 30 % below ρ = 0 |
| Jaw 5–15°, smile | expressive | TPR ≥ 0.9 | rigid regions ≤ 1.1× clean |
| Beauty warp (eyes +6 %, jaw −4 %) | `Q-RETOUCH` | TPR ≥ 0.8 with ≥ 3 clean views | identity bias ≤ 0.5 mm |
| Off-axis wide-angle warp | gate or k₁ | TPR ≥ 0.8 | — |
| Glasses, beard, hair | tag actions | beard → jaw *prior-driven* | scalp inside the hull |
| Face 150 px | `Q-SMALL` | — | coverage holds |

### 5.3 Honesty metrics

- **Coverage.** In *measured* regions, 0.90–0.99 of vertices must have |error| ≤ 1.96·σ_rep (🆕).
- **False confidence.** At most 5 % of *measured* regions may exceed 2× their T6 target (🆕).
- **Alarms.** No more than 1 spurious flag per 10 clean photos (🆕).
- **Promotion.** A default changes only if held-out error drops and coverage holds.

Shape is scored with `face3d/eval`: exact point-to-triangle distance, under both NoW-style and landmark-only alignment. Reported: median, p95, F@1/2 mm, per-region bias, scale error and configuration RMS (EV-1/2 🧠).

### 5.4 Real-data bed (outside CI)

- **Sitters.** Start with 1–3 consenting sitters (benchmarks-metrics 🧠), growing to about 10, varied in age, skin tone, beards, glasses and hair.
- **Per sitter:** a scan and a repeat scan (the noise floor); a protocol ring; rear-phone, selfie and dated camera-roll sets.
- **Data handling.** Retention follows ethics §4. Only aggregate results are committed, behind a leakage guard.
- **What it calibrates:** every 🧠 and 🆕 value, detector bias and semantics maps, and a six-face lineup (target ≥ 80 %).

### 5.5 What the artist sees

- **Per-camera sheets** (community R8.1 🧠): photo, clay render, 50 % overlay, difference, silhouette chamfer, and flipped, blurred and 64 px versions.
- **Worst landmarks**, listed first, in % IOD.
- **LOVO check**, flagged when held-out error exceeds 2× in-sample (reconstruction principle 15 🧠).
- **Caliper sheet**, flagging differences over 2 mm.
- **Canon z-scores**, phrased in art vocabulary.
- **Likeness lint.** It flags only |model − photo| > 2σ_photo, and never pulls toward the mean (community R8.2 🧠).
- **"Over-symmetric" warning** when mirror RMSD < 0.3 mm.
- **Approval renders** from ≈1 m and from the sitter's favourite photo camera (camera-perspective-distortion ↔️).

## 6. Milestones

Each milestone ships on its own and is tested here on synthetic data.

- **M1: Test bed first.** `face3d/eval`, `face3d/testbed`, scorecard, smoke suite.
  - Point-to-triangle matches brute force to 1e-9.
  - A known similarity transform is recovered.
  - The baseline scorecard is committed.
  - The smoke suite runs in ≤ 90 s.
- **M2: Ingest and QA.** EXIF, HEIF-EXIF, PNG, orientation, schemas, policy gates, §3.1, focal ladder, `triage` CLI.
  - Byte-fixture golden tests pass.
  - Each gate fires on its fixture and stays silent on clean inputs.
  - A run without consent is refused (ethics F3).
  - Output is deterministic.
- **M3: Robust cameras and BA.** §3.2–3.5, observability, LOVO.
  - z sweeps (0.25–5 m) and f35 sweeps (13–200 mm) meet the §5.2 camera, mirror and orientation rows.
  - Unobservable focal length is reported.
  - Existing tests still pass.
- **M4: Nuisances.** §3.6.
  - Its §5.2 rows pass.
- **M5: Kit, warp and uncertainty.** §3.7, §3.9, §3.10. CI uses a procedural stand-in head; the real CC0 kit is built offline with recorded hashes.
  - The propagation check matches finite differences.
  - Smoke-suite coverage is 0.90–0.99.
  - The experimental basis stays off unless it wins.
- **M6: Contours.** §3.8.
  - The tracer lands within 1 px of rendered edges.
  - Profile error ≤ 1.5 mm.
  - No scalp vertex lies outside the hull.
- **M7: Blender MVP.** §4.
  - Bridge and manifest lints pass.
  - The zip contains no wheels and no non-CC0 assets.
  - Headless scripts are provided for 4.5 and 5.2 LTS.
- **M8: Helper, texture and review.** The JSON contract is tested via a fake backend.
  - Gains are recovered within 2 % (TEX-8 🧠).
  - No colour on occluded texels.
  - Filtered views are excluded.
- **M9: Calibration release.** The §5.4 bed turns 🧠 and 🆕 values into measured ones. Its tooling is tested; its data stays out of CI.

## 7. Risks and deliberate omissions

**Risks**

- **No proven licence-clean statistical shape model.** The baseline is weak in depth. Coverage rules and next-best-photo prompts push users toward profile views.
- **Unsourced values.** About 70 % of cited values are 🧠, and the 🆕 gates are ours. All stay provisional until M9.
- **Synthetic detector errors are not MediaPipe's.** M9 calibrates the detector semantics.
- **Undetectable cases.** Mirroring of near-symmetric faces or selfie-only sets, and filters on a lone photo, cannot be detected. These are reported `undetermined`.
- **Packaging.** Four questions are open: cp313 MediaPipe wheels, the store's stance on bundled models (C7/C8), HEIC in Blender, and attribute names in 5.x. The helper and manual pins keep every stage usable meanwhile.
- **Solver scale.** The dense Hessian handles about 150 landmarks × 12 views; beyond that, the Schur complement takes over (M3).
- **Alarm fatigue.** It is measured (§5.3).

**Deliberately left out of the default path**

- **Monocular depth, generative fill, Gaussian avatars and photometric shape terms.** These are not measurements (reconstruction principles 12–14). They may come later as opt-ins, gated by the test bed.
- **Automatic beard, glasses and hair segmentation.** User tags plus an optional SAM helper do this job.
- **Identity embeddings.** Opt-in, for evaluation only. Their weights are mostly NC (non-commercial), and embeddings are never stored.
- **"Un-filtering" retouched photos.** We down-weight them instead.
- **Phone-video depth, ear detail beyond silhouette plus prior, hair grooming, teeth and fine lid detail.** These wait for their gap-topic notes.
- **Symmetrising, anonymising, 1:N matching and URL import.** These are never built (ethics F17, F18, A5).
