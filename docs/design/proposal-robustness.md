# Proposal: a robustness-first photo-to-head engine

*Design angle: robustness first, built for the photos people actually take. Written 2026-11-20 against `face3d/` at commit 887c5e5 (42 tests pass) and the requirements digests in `research/_raw/requirements_*.md`.*

**How to read the citations.** Each value names its source note and that note's evidence badge:

- ✅ verified
- 📄 single source
- 🧠 unverified expert knowledge
- ↔️ contested
- 🆕 introduced by this proposal, with no source; it must be calibrated on the test bed (§5)

`open-template-head-kit` and `cranium-under-hair` refer to draft data tables in `research/data/`; their notes do not exist yet. Every 🧠 or 🆕 value is a named configuration entry that carries its badge.

## 0. Thesis

The tool will mostly be judged on bad inputs, not good photos: a mirrored selfie, a messenger copy with no EXIF data, a beard hiding the jaw, a smile in the only three-quarter view. So the engine:

1. detects every known failure mode with a simple test that can be checked;
2. down-weights or excludes weak evidence instead of fitting through it;
3. states, region by region, what the result can still claim;
4. measures all of this on a fault-injection test bed before any number becomes a default.

Where a simple method and a clever but fragile one compete, the simple one wins.

## 1. Vision and user journey

1. **Consent.** The project starts with a `ConsentRecord` (ethics §2.1). Nothing runs without the `RECONSTRUCT` scope.
2. **Photos.** Each photo is hashed, and its EXIF is read: orientation, focal length, lens, date and editing software. Orientation is baked into a working copy; the original is never changed.
3. **Landmarks.** These come from MediaPipe, via an external helper that writes JSON or an optional wheel, or from manual pins. Pins and JSON import always work, so the pipeline never requires a download (ethics A4).
4. **Triage.** Every photo gets a QA card covering distance, focal evidence, lens risk, mirroring, expression, occluders, blur, resolution and retouching. Each flag states its action and why, for example *"selfie at ≈0.35 m: colour and frontal outline only, not nose projection"*.
5. **Solve.** A robust multi-view bundle adjustment (BA) runs, then the mirror check and an observability report (for example "focal from prior").
6. **Fit.** The CC0 template is warped in stages, then matched to contours and silhouettes. Profiles are traced with edge snapping.
7. **Review.** A claims ledger marks each region *measured*, *constrained*, *prior-driven* or *unobserved*. It also shows held-out-view checks, overlays for each camera and the worst landmarks, and recommends the most useful next photo ("add a left profile").
8. **Hand-off.** The fit becomes shape keys on stable topology, with an `artist` layer, a Multires sculpt copy, an optional gated texture, and provenance on export.

**What we promise for each input tier.** The tier is computed from the evidence, never chosen by the user.

| Tier | Typical input | Promise | Label |
|---|---|---|---|
| S | ≥ 5 views over ±60–90° yaw, 1.5–3 m, tele lens, EXIF, a scale reference | metric; depth measured; face RMS ≤ 1.5 mm (benchmarks-metrics T6 🧠) | `metric` |
| A | rear phone camera, ≥ 3 views, one at \|yaw\| ≥ 45°, EXIF present | proportions; depth wherever the coverage rules hold (§3.10); iris scale ±2–4 % (multi-view-fitting 🧠) | `iris-scaled` |
| B | camera roll: mixed devices and dates, missing EXIF, expressions | frontal proportions through the solved cameras; depth from the prior unless some view exceeds 60° yaw | `proportions only` |
| C | a single photo, or selfies only | a blockout that matches through its own camera; no claim about nose projection, ears or cranium | `blockout` |

## 2. Architecture

### 2.1 Modules

The engine imports only `numpy`, `math`, `json`, `struct`, `zlib`, `hashlib` and `tomllib`. Its imports are relative, and it never imports `bpy` (blender digest A1). The St column marks each module as E (exists), X (extend) or N (new).

| Path | St | Purpose |
|---|---|---|
| `face3d/core/{schema,policy,config}.py` | N | Versioned formats; consent scopes and licence taint as an AND over components (ethics A2); defaults carrying badges; config SHA-256 |
| `face3d/io/exif.py` | X | Add DateTimeOriginal, Software, DigitalZoomRatio, LensMake and SubjectDistance; read every APP1 segment |
| `face3d/io/{heif_exif,png,image_ops,landmarks}.py` | N | HEIC EXIF via ISOBMFF boxes (no pixel decoding); stdlib PNG reader; orientation and flip-with-permutation on arrays; landmark adapters |
| `face3d/qa/{image,photo,expression,mirror,retouch,flags}.py` | N | QA gates (§3.1, §3.6) and the flag registry (code, severity, evidence, action, source) |
| `face3d/solve/pnp.py` | X | Multi-start, cheirality check, twin flag, CAM-3 focal hypotheses, Huber threshold in σ units |
| `face3d/solve/{noise,observability}.py` | N | Noise model (§3.2); σ(log f), σ(log z), P, leave-one-view-out (LOVO) |
| `face3d/solve/bundle.py` | X | Covariance blocks, visibility, jaw hinge, distance priors, soft focal ties, view cap, 4σ rejection, Schur marginals |
| `face3d/model/{registry,template_kit,prior,nuisance}.py` | N | Landmark registry (anatomy R2.1); hash-checked template kit; priors and gates; jaw hinge; occluder actions |
| `face3d/fit/{template,silhouette}.py` | X | Gated stages with a reflection check; sliding and one-sided contour terms |
| `face3d/fit/{contour_trace,uncertainty}.py` | N | Dynamic-programming edge snap; vertex σ and claims ledger |
| `face3d/geometry/rbf.py`, `mesh/laplacian.py` | X | Per-landmark smoothing Λ; per-vertex stiffness |
| `face3d/{texture,eval,testbed}/` | N | numpy z-buffer and blending; point-to-triangle metrics (reconstruction EV-1); scenario test bed |
| `face3d/pipeline.py`, `__main__.py` | N | Deterministic stage runner; CLI `python -m face3d {triage,solve,fit,report,testbed}` |
| `tools/{detect_mediapipe,build_template_kit,build_extension}.py` | N | Out-of-process detector (Tasks API, `IMAGE` mode, `num_faces=2`, test-time augmentation (TTA)); hash-checked builds |
| `blender_ext/face3d_head/` | N | The extension (§4), with the engine vendored in at build time |

`lm.py`, `triangulate.py`, `procrustes.py`, `camera.py` and `mesh/{core,sparse,reduced}.py` are unchanged.

### 2.2 Data flow

```
photos → ingest (sha256, EXIF, orientation, consent) → LandmarkSet (+TTA spread)
→ triage (flags, tags, σ multipliers, include/exclude, focal ladder) → multi-start PnP + mirror test
→ robust BA → observability + LOVO → warp A→B→C → contours D → uncertainty → claims ledger
→ result.json/fit.obj/sigma.npy → Blender → artist → gated texture → export
```

Every stage is a pure function. Its output is cached under the hash of its inputs and config, so editing one pin re-runs only the stages after it.

### 2.3 Data formats

Files are JSON with a `format` and a `version` field. Arrays longer than about 1,000 values are stored as `.npy` files and referenced by path and SHA-256.

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

- **Scheme file.** Our own work, bundled as CC0. The scheme is always read from this file, never guessed from the point count N (reconstruction FMT-1). Fields: `n`, `lr_permutation`, `midline`, `classes`, `convention` (surface or semi-contour), `sigma_iod` per class, an `anatomical` map from names to indices, and per-entry `verification`.
- **Template sidecar.** Fields:
  - `source` (upstream SHA-256, `CC0-1.0`, `commercial_ok`);
  - `units: mm`, `topology_sha256`, `order_checksum`;
  - `landmarks` (kind, triangle, barycentric coordinates, σ, provenance);
  - `scheme_maps` for each detector version;
  - `regions`, `mirror_map`, `contours`, `stiffness`;
  - `basis` (K, SHA-256, status).

  The kit builder fills every field.
- **Result file.** Fields:
  - `config_sha256`, `seed`, input hashes, `tier`;
  - per camera: K, R, t, f35, z, P, σ_logf, `focal_status`, and the mirror result `{decision, Δ, status}`;
  - per view: RMS in % IOD (in-sample and LOVO), `noise_scale`, `weight_share`, `rejected_frac`, flags;
  - `scale {mode, s, σ}`;
  - 3D landmarks and their covariance;
  - `regions [{name, status, k, σ_mm, why}]`;
  - `licence {commercial_ok, components}`;
  - the mesh and its per-vertex σ.

### 2.4 Coordinate conventions

These are fixed in `core/schema.py` and each has a round-trip test.

- **Image.** Continuous coordinates with the origin at the top-left pixel's corner, so pixel (i, j) has its centre at (i + ½, j + ½), as in `camera.py`. MediaPipe output maps as u = x·W, and a resize as u·W/W′. The "+0.5" form in blender digest D3 is not used. A flip is u′ = W − u together with the left/right label permutation π.
- **Camera.** OpenCV convention: X_c = R·X_w + t, with +y down and +z forward.
- **Head.** Millimetres, float64. +x is the subject's left, +y up, +z forward, and the origin lies on the midsagittal plane (anatomy R1.1).
- **Blender.** An `R_x(+90°)` parent object maps (x, y, z) to (x, −z, y), with a scale of 0.001 (blender A8). The existing `to_blender_camera` is already tested.
- **IOD.** Outer-canthal distance ex–ex (landmark-detection T2). Values quoted in interpupillary units are multiplied by 0.70 (T3 🧠). Once a camera is solved, IOD_px = f·IOD_mm/z_v. The 2D ex–ex distance is not used, because it halves at 60° yaw.
- **Determinism.** Every random draw uses `default_rng(seed)`. Hypotheses run in a fixed order, sorts are stable, and all maths is float64. Golden values are compared at rtol 1e-5 (blender Q2). CI runs on CPython 3.11 with NumPy 1.26 and on 3.13 with NumPy 2.x (A4).

## 3. Algorithms

### 3.1 Input QA gates

No gate ever corrects a value toward a population norm (anatomy §6). Each one does one of five things: down-weight, drop a landmark class, exclude the photo from geometry, exclude it from texture, or ask the user.

| Failure | Detection and threshold | Action | Source |
|---|---|---|---|
| Orientation ignored | `exif_applied` false, view RMS > 3σ, or roll ≈ ±90° | bake orientation, re-detect | blender §10 🧠 |
| EXIF stripped | no Make, Model or f35 | prior by source type (§3.3) | community R2.2 🧠 |
| Crop or zoom | size ≠ PixelXDimension, non-native aspect, or zoom > 1 | σ_logf 0.08–0.10; free the principal point (σ 10 %) | community R2.5 🧠 |
| Front camera | LensModel contains "front" | mirror test; selfie distance prior | camera-perspective-distortion 🧠 |
| Near camera | solved z, cross-checked against f·63/IPD_px; warn below 1 m, strong warning below 0.8 m | below 0.6 m: 2D and texture use only | community §9 🧠 |
| Face-warp correction | f35 ≤ 16 mm, face beyond 60 % of the half-diagonal, or more than 25° off-axis | σ × 2, or exclude from geometry | community R1.7 (warp ✅, thresholds 🧠) |
| Low resolution | face < 250 px: warn; < 120 px: reject; iris < 20 px | σ floor; no iris scale; no detail | community R1.4 🧠, R4 ↔️ |
| Blur, blink, clipping | Laplacian variance in the bottom 20 %; eye aspect ratio (EAR) < 0.2; > 2 % of skin pixels clipped | down-weight; drop lid points; no photometry | community R1.4 🧠 |
| Mixed dates | date span > 18 months | split into date clusters | community §9 🧠 |
| Two faces; no consent | `num_faces=2` at score ≥ 0.6; photo sha256 not in the consent record | user picks the face; block | blender ML 🧠; ethics F1–F2 |

### 3.2 Noise model

Each landmark i in view v gets an anisotropic covariance, built along its tangent t̂ (taken from neighbouring points):

Σ_iv = s_v²·m(c_i, tag_v)²·R(t̂)·diag(σ_n², σ_t²)·R(t̂)ᵀ,
σ_• = max(σ̂_•(c_i)·IOD_v·√(N/N_eff), σ_tta, σ_floor)

The terms:

- **Class σ̂** in % IOD, normal/tangent (landmark-detection T5 🧠): iris 1.0; anchors 1.5; lid and lip contours 2/5; pronasale 2.5; brows 3–5/6; jaw 2.5/10–15.
- **Dense-point inflation.** √(N/N_eff), with N_eff = 60–100, applies only to points outside a curated subset of about 100.
- **σ_tta** is the spread over 6–10 TTA passes (BA-2 🧠).
- **σ_floor** = max(0.5 px, k·face_px/256), with k = 0.6 for inner points, 0.4 iris, 1.0 brows and 1.5 contours (blender ML 🧠).
- **Per-view scale** s_v² = clip(median‖Σ^{−½}r‖²/1.386, 1, 9). This is a MAD-style estimate; 1.386 is the median of χ²₂ (deformation-fitting-math 🧠). Retouched, warped or misoriented views lose weight automatically, and a view is flagged when s_v > 2 (🆕).
- **View weights.** Each view gets weight 1/(number of views in its 15° yaw bin), and no view may supply more than 40 % of the total information (community R1.8 🧠).

This model replaces `sigma_px = 1.0`, which is about 13× too tight (landmark-detection 🧠), and the isotropic default of 0.006 × the diagonal.

### 3.3 Camera initialisation

**Focal ladder.** The first matching rule sets a log-normal prior on focal length (CAM-6, community R2.2 🧠):

| Evidence | Prior |
|---|---|
| SfM or calibration | σ_log 0.005–0.02 |
| Uncropped EXIF f35 | σ_log 0.04 |
| EXIF f35 with a suspected crop | σ_log 0.08–0.10 |
| FocalLength plus focal-plane resolution | σ_log 0.10 |
| Phone with no focal data | 26 mm, σ_log 0.25 |
| Nothing | 50 mm, σ_log 0.6 |

The current 0.35 fallback cannot cover phone lenses.

**Focal groups.** Photos are grouped by (Make, Model, LensModel, f35, W, H, still/video). Each group gets a soft tie (σ 0.02) instead of one shared value (CAM-5 🧠).

**Distance prior** on log z:
- front camera: 0.35 m, σ 0.3;
- rear camera: 0.8 m, σ 0.4;
- tele: 2 m, σ 0.4 (CAM-6 🧠; we read each σ as log-σ);
- unknown: 1.0 m, σ_log 0.7;
- tape-measured: ±5 cm (community R2.4 🧠).

Distance is bounded to 0.25–10 m (blender C6).

**Multi-start PnP.**
- f35 hypotheses: {13, 24, 26, 35, 50, 77, 85, 120, 135, 200} (CAM-3 🧠). The current list lacks 26, 77 and 120.
- Each hypothesis starts from three poses: affine, pitch-flipped and yaw-mirrored.
- Solutions that fail cheirality (points behind the camera) are rejected.
- If two poses more than 10° apart score within 20 % of each other, the view is flagged `C-TWIN` and both enter BA (🆕).

**Off-axis faces.** Rotate the face-centre ray onto the optical axis, initialise, then rotate back (camera-perspective-distortion 🧠).

**Order.** The most frontal, most complete view is solved first. Later views are initialised against the BA consensus, not the template, which reduces mean-face pull.

### 3.4 Mirrored images

Let X̂ be the consensus shape from the other views, or the template when there is only one view. Let C₀ be the robust PnP cost of a view, and C₁ its cost after flipping, u′ = (W − u_x, u_y)_π. The mirror statistic is Δ_v = (C₀ − C₁)/C₀.

**When the test can decide.** The test needs real asymmetry. Let A = ½(X̂ − M·X̂_π) be the asymmetric part of the shape, and let g = Σ‖Σ^{−½}J_i A_i‖² be the expected cost gap between the two orientations. If g < 4 (🆕), the result is `undetermined`: a near-symmetric face seen through noisy landmarks cannot be told from its mirror image.

**Decision.** A view is mirrored when Δ_v > 0.2 (community R1.6 🧠).
- If the photo came from a front camera, or the other views agree, it is flipped automatically and the flip is logged.
- Otherwise the tool shows both orientations and asks the user to check the hair parting or a mole (likeness-mistakes 🧠).

**All views mirrored.** If every photo is mirrored (a selfie-only set, for example), geometry cannot tell. The result is marked `mirror: unverifiable`, and every claim that depends on asymmetry is flagged.

### 3.5 Robust bundle adjustment

The cost to minimise:

E = Σ_v w_v Σ_i ρ_H(‖Σ_iv^{−½}(π_v(X_i + J_i(θ_v)) − u_iv)‖; δ = 2) + Σ_v E_contour,v
  + Σ_g ((log f_g − μ_g)/σ_g)² + Σ_{v∈g} ((log f_v − log f_g)/0.02)² + Σ_v ((log z_v − μ_z)/σ_z)²
  + E_shape(X) + Σ_pairs ‖Σ_sym^{−½}(X_l − M·X_r)‖² + Σ_mid (x_i/σ_mid,i)² + E_scale + E_pins

- **Robust loss.** Huber at 2σ, in σ units, replaces the current 3 px (PnP) and 3σ (BA) thresholds. After convergence, residuals beyond 4σ are dropped and the problem is solved again. A view that loses more than 15 % of its points is flagged (BA-5 🧠).
- **Visibility weight.** 0 when n·(−v) < cos 80°, rising to 1 at cos 60°. Points on the far side of the face oval are dropped when |yaw| > 25° (BA-3 🧠).
- **Symmetry and midline σ** (anatomy R4.2 🧠):
  - pairs: canthi 0.7–1.0 mm, brows 1.5, alae 1.0–1.5, cheilia 1.5–2.0, gonia 2.5–3, ears 3–4;
  - midline: nasion 0.75–1.0 mm, prn and sn 1.5–2.0, pg and me 2–3.
- **Covariance** comes from the Schur complement once N ≥ 100. Each landmark reports its prior share p_i = σ²_post/σ²_prior. *Likeness mode* widens the prior until p_i ≤ 0.2 wherever at least 2 solved views see the point (anatomy R1.4 🧠).
- **SfM cameras.** These go through triangulate → Umeyama → a 3D shape solve, and landmarks never move them (BA-12 🧠).

### 3.6 Expressions, occluders and retouching

**Expression tags.** Blendshape scores are compared as Δb, the rise above the subject's own minimum across all views, not above zero (landmark-detection 🧠).
- **Neutral:** every Δb is below its threshold: jawOpen 0.08, mouthSmile 0.15, eyeBlink 0.35, browInnerUp 0.2 (landmark-detection 🧠).
- **Expressive:** any score exceeds its limit: smile 0.25; squint, eyeWide or brow 0.3; blink 0.4 (anatomy §6 🧠).
- **Mild:** anything in between.
- **Without blendshapes:**
  - inner-lip gap / ch–ch > 0.04 means parted lips, so sto and li are dropped (anatomy §6 🧠);
  - mouth width > 1.08 × the median across views means a smile (🆕).
- Tags are refined from residuals for at most 3 rounds (BA-9 🧠).

**σ multipliers** for neutral / mild / expressive views (expression-neutralization 🧠):
- rigid points: 1 / 1 / 1–1.5;
- semi-mobile: 1 / 1.5–2 / 2–3;
- mobile: 1 / 3 / dropped;
- jaw-dependent: 1 while the jaw angle θ is fitted.

**Jaw hinge.** This needs no expression dataset:

X_i(θ) = c + R_axis(θ)(X_i − c)

The axis runs through the template condyles, about 10–13 mm in front of tragion (BA-1 🧠). On neutral views θ ~ N(1.5°, 1°), bounded to 0–30° (anatomy §4 🧠).

**Expression basis ψ.** This is opt-in, and only through licence-clean adapters such as FLAME 2023 Open. Neutral views anchor ψ at mean ≈ 0 with σ 0.1 (BA-9 🧠). Without a neutral view, mouth and lid measurements finer than 1 mm are suppressed.

**Occluder tags.** The user sets these with one click; the default path has no licence-clean detector for them.
- **Glasses:** eye σ × 2; no iris scale; lid points under the frame dropped (anatomy R3.4 🧠). Consistency test: lenses magnify ≈1–1.5 % per dioptre, so an iris/(en–ex) ratio more than 3 % off the glasses-free median raises a flag (🆕).
- **Beard:** pg, gn, me and jaw points dropped; the beard outline becomes a one-sided bound; the jaw is *prior-driven* unless a shaven photo exists (reference-photography-protocol, community R5.4 🧠).
- **Hair:** ear and temple weights set to 0; no silhouette above the trichion (blender S3 🧠).
- **Makeup:** lip and brow borders σ × 2 (artstation-likeness 🧠).

**Retouching and beauty filters.** Three independent tests, each judged relative to the other views:
1. EXIF `Software` matches a list of known editors (🆕).
2. Skin-smoothness index SSI_v: band energy of a cheek patch divided by band energy of the brow and iris, measured at matched mm/px. Flag if SSI_v < 0.5 × the set median (🆕).
3. Residual regression on two fixed patterns: eye-radial outward (eye enlargement) and jaw-normal inward (jaw slimming). Flag if t > 3.

A flagged view gets σ × 2–3 and is excluded from texture (artstation-likeness ↔️; tests 🆕). A filter on the only photo cannot be detected, and the ledger says so.

**Non-pinhole processing.** A diagnostic distortion coefficient k₁ (prior σ 0.02) is fitted. On a phone JPEG, |k₁/σ| > 3 means "non-pinhole processing suspected" (CAM-1 🧠). Separately, if the radial residual's slope against ρ_i·δ_i implies more than 5 % magnification error, the distance or focal length is wrong (community R2.8 🧠).

### 3.7 Licence-clean shape prior

No permissive, large-population head model is confirmed to exist (reconstruction §12), so the prior has three layers:

1. **Baseline.** An anisotropic Gaussian per landmark at 1.0–1.5 × the population SD, falling back to 8 mm (anatomy R4.1 🧠). Ratio priors serve only as diagnostics.
2. **Experimental.** X = μ + B·c with c ~ N(0, I). B is a mass-weighted SVD of the CC0 MPFB2 face targets (K = 40–80). Its variances come from an "anthropometric morphable model": 2,000–5,000 sampled heads matched to published norms, keeping 95–99 % of the variance (open-template-head-kit 🧠). This layer stays off until it lowers held-out error while keeping coverage (§5.3).
3. **Opt-in.** FLAME 2023 Open from a user-supplied path, pinned by SHA-256 and attributed (CC-BY-4.0; contents unverified 📄). Any other FLAME release, or BFM, sets `commercial_ok=false` (LIC-1).

**Gates** (MM-5 🧠, community R5.8 🧠):
- ‖c‖² > χ²_K(99.9 %), or any |c_i| > 3: implausible.
- ‖c‖² < K − 2√(2K): "pulled toward average".

**Nothing is fabricated.**
- Template landmarks come from two annotators clicking in Blender, accepted where they agree within 1 mm (🆕).
- MediaPipe maps come from detector-semantics calibration: render the template from 20–50 cameras, run the detector, and store each index's mean barycentric landing point (landmark-detection 🧠).
- Both are built offline with provenance. CI checks hashes, schemas, that the L/R permutation is an involution, and that midline points map to themselves.

### 3.8 Contours, silhouettes, profiles and hair

**Edge snap.** The input is a coarse polyline: at least 5 clicks, or the detector's oval points. Each of M stations may shift by an offset k ∈ [−L, L] along its normal, with L = 3 % IOD. The snap minimises

C = Σ −g_j(k_j) + λΣ|k_j − k_{j−1}|,

where g is the gradient magnitude after a Gaussian of σ = 1 px, and λ = 0.2 × the median of g (🆕). Viterbi solves this in O(M·L²). It is deterministic and uses no learned weights. Each point gets σ_n = max(1 px, 1/√curvature). Segment Anything (Apache-2.0) is optional and runs only in the external helper.

**Sliding residuals.** For each contour point, r = n̂·(p_j − q)/σ_n, matched to the nearest outline segment and re-matched every iteration (BA-4, blender S1 🧠). These are added to the existing outline-to-vertex term, with 10 % trimming. The trim gate is 5 % IOD instead of a fixed 60 px (🆕).

**One-sided masks** for hair, beard and hat:

r = max(0, d_mask + m)/σ, with margin m = 0–3 mm (community R5.4 🧠) and weight 10 × that of skin (cranium-under-hair 🧠).

The scalp stays at least 2 mm inside the hair hull (blender W7 🧠). Cranium σ follows the visual-hull overshoot: 7.8 mm with 4 views around the head, 1.9 mm with 8 (cranium-under-hair, arithmetic).

**Profiles.** For views with |yaw| > 60–70°, detector points are discarded (landmark-detection 🧠). User pins on g, n, prn, sn, ls, li and pg are used instead, at σ = 1 % IOD (blender S4 🧠).

**Acceptance.**
- Profile error at most 1–1.5 mm at the nose tip and chin (SIL-3 🧠).
- Contour error at most 1 % of face height (S5 🧠).
- If the interior fits but the contours fail, the message is "f and z wrong", not a shape error.

### 3.9 Template warp

| Stage | Operation | Advance when |
|---|---|---|
| A | Umeyama, proper and reflected. If the reflected RMS is below half the proper RMS, flag "mirrored source"; never auto-flip. A 7-landmark RMS above 10 mm means the axes are wrong (blender W2 🧠) | always |
| B | RBF with φ = r: (Φ − Λ)w + Pa = y, with Λ = diag(α·σ_i²) and α = 10⁻² (MM-8 🧠; the sign is already fixed in `rbf.py`) | landmark error < 2–3 % IOD (community R5.2 🧠) |
| C | Bilaplacian with per-vertex stiffness: lid margins 3.0, lips 0.3, forehead 0.5, ligaments 3–5 (anatomy R5.9 🧠). Offsets are capped at 3–5 mm unless at least 2 views agree (MM-10 🧠) | RMS improves < 1 % per iteration |
| D | Silhouettes via `ReducedDeformer`; no landmark moves more than 0.5 mm | contour error ≤ 1 % of face height |

**Gates checked at every stage:**
- det J > 0.2, with no flipped triangles (MM-11 🧠);
- lid-to-globe gap between 0 and 0.3 mm (blender §4 🧠);
- mirror RMSD between 0.3 and 1.5 mm (anatomy §6 🧠).

Targets are never symmetrised. The detail pass is off by default. It runs only on neutral, unfiltered views at ≤ 0.08 mm/px, and only where at least 2 views agree. Detail from any other source is labelled `synthetic` (anatomy R5.11 🧠).

### 3.10 Uncertainty and the claims ledger

**Propagation.** Stages B and C are linear in the targets: V = V₀ + A(X − X₀). The matrix A comes from unit solves, so each vertex gets

Cov(V_j) = Σ_ab A_ja A_jb Cov(X_a, X_b) + σ²_res·I

The residual σ_res depends on the region: lids 1–1.5 mm, nose 2–3, cheeks 2.5–4, ears 3–5, scalp 3–6, neck 5–10 (open-template-head-kit 🧠). A finite-difference test checks A.

**Reported σ.** σ_rep² = σ²_post·max(1, κ²) + σ²_bias.
- κ is the LOVO ratio of observed to predicted error.
- σ_bias is 1–3 mm per landmark class until a detector-semantics map exists, because detector bias does not average out (reconstruction principle 5 🧠).
- The raw Hessian σ is never shown alone.

**Region status.** Let k = 1 − σ²_post/σ²_prior.
- *measured*: k ≥ 0.8 (anatomy §6 🧠) and the coverage rules below hold;
- *constrained*: 0.5 ≤ k < 0.8;
- *prior-driven*: k < 0.5 (🆕);
- *unobserved*: no view sees the region.

**Coverage rules.**
- Any depth claim needs at least 2 views at least 30° apart (blender C7 🧠).
- Nose and chin projection need a front view plus one at |yaw| ≥ 60°.
- The jaw underside needs a low view (community R5.9 🧠).
- Ears need |yaw| ≥ 30° and pitch fixed by at least 2 views (R3.3 🧠).

**Focal and scale.**
- Focal length is estimated only when σ(log f) < 0.10 (blender C2 🧠). If σ exceeds 0.8 × the prior σ, the label reads "focal from prior" (CAM-7).
- Scale is one of *measured* (a caliper overrides all else; anatomy R3.4), *iris*, *IPD prior* or *proportions only*. Scale references that disagree by more than 1 % are flagged (BA-10 🧠).

**Next-best photo.** Candidate views on a 15° grid are added to the Hessian in simulation. The tool recommends the one that most reduces σ in prior-driven regions, weighted by the region weights in benchmarks-metrics T6 🧠.

### 3.11 Texture projection

**Gates.** Projection runs only when all of these hold:
- reprojection median ≤ 1.5 px and maximum ≤ 3 px (blender T2 🧠);
- the consent record includes `TEXTURE`;
- `rights_basis` is not `unknown` (ethics §3).

**Method** (TEX-1…7 🧠):
- a numpy z-buffer with tolerance max(1 mm, 2σ_geom);
- view weight vis·cos²θ·footprint·edge, faded between 60° and 75°;
- gains in linear RGB, with log-σ 0.3 under auto exposure;
- a two-band blend split at 3 mm;
- 2048 px maps for phone photos.

**Exclusions.** Filtered, retouched, warped and clipped views never feed albedo, and neither do views from other date clusters. Texture is never mirrored. Without a colour chart, the albedo is labelled "absolute albedo unknown".

## 4. Blender add-on

**Package.** `blender_ext/face3d_head/` contains:
- `blender_manifest.toml`;
- `__init__.py` with `compat.py` probes (under 100 ms);
- `bridge.py`, the only module that converts between bpy and numpy;
- `ops_*.py`, `ui_panels.py`, `overlays.py`, `jobs.py`, `keys.py`;
- the vendored `face3d/`;
- `assets/template/` (CC0), plus `LICENSE` and `NOTICE`.

| Operator | Does | Runs |
|---|---|---|
| `face3d.project_new`, `face3d.photos_add` | Creates the ConsentRecord; hashes photos, reads EXIF, writes orientation-baked copies, strips GPS (ethics F12) | main |
| `face3d.landmarks_import`, `face3d.detect` | Imports landmark JSON, or runs the helper or wheel | job |
| `face3d.pin_edit`, `face3d.trace_contour` | Modal tools in the photo camera: place pins (σ from zoom); draw a polyline, then edge-snap it | modal |
| `face3d.triage`, `face3d.solve`, `face3d.fit` | Run §3.1–3.10 | job |
| `face3d.apply_result` | Writes cameras, keys and attributes. Refuses on a topology-hash mismatch, or in Edit or Sculpt Mode (blender K1/K4) | main, UNDO |
| `face3d.bake_for_sculpt` | Duplicates the object, bakes the key mix, clears keys, adds Multires 2–3 (K5, SK-3 🧠) | main, UNDO |
| `face3d.project_texture`, `face3d.review_sheet`, `face3d.prepare_sharing`, `face3d.export` | Texture (§3.11) and review (§5.5); purges leftover data (ethics F9); exports with provenance and consent gates | job / main |

**Panels** sit in the Sidebar under *Face3D*:
- Project & Consent.
- Photos: a UIList with QA badges, tags, include/exclude and mirror state.
- Solve: tier, focal status, z and P.
- Fit: stages and gates.
- Review: ledger, LOVO, worst landmarks, next-best photo.
- Export: any blocking reasons.

**Overlays** are drawn with `gpu` handlers through each photo's camera:
- σ ellipses;
- residual arrows, exaggerated ×5;
- rejected points in red;
- the traced outline against the projected silhouette;
- a flipped thumbnail for the mirror prompt.

In 3D, the `face3d_sigma_mm` and `face3d_status` attributes colour the viewport, and region face sets drive masks.

**Undo.** Engine state lives in hashed sidecar files, not on the undo stack. Objects carry a `face3d_uuid` and are re-fetched by it after undo. Jobs record their target's topology hash and refuse to apply if it has changed.

**Jobs.** The add-on writes JSON and `.npy` files under `extension_path_user` and spawns `[sys.executable, "-I", launcher.py, job_dir]`. A timer polls every 0.1 s and does at most 20 ms of work per tick (blender A5 🧠). Cancelling kills the process, so a crash never takes sculpt work with it. In background mode (`bpy.app.background`) jobs run synchronously.

**Shape keys** (blender K2/K3 🧠):
- `Basis` holds the template mean.
- `F3D_stageB` and `F3D_stageD` are diagnostic keys, set to 0.
- `F3D_ID_v<n>` holds the likeness, written with `from_mix=False`; `slider_max` is 1.5.
- `artist` is kept as a Δ across refits.
- Expression keys are written only with `RIG_ANIMATE` consent (ethics F4).
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
- The minimum Blender version is the oldest CI-tested line (Q3).

A **GitHub build** adds per-platform MediaPipe wheels plus a NOTICE file. Whether that complies with the extensions platform rules is ↔️. The external helper runs in any Python, so lagging cp313 wheels never block the tool (blender-python-ml-deps 🧠).

## 5. Validation and QA

### 5.1 Test pyramid

1. **Unit and oracle tests.**
   - Analytic Jacobians match numeric ones.
   - Noiseless solves reach RMS < 10⁻⁶.
   - The camera↔Blender round trip holds to 10⁻⁶·s, and the OBJ round trip to under 2 µm (blender Q1/Q2 🧠).
   - Schemas and policy tables are tested.
   - Each QA gate is tested on synthetic arrays: a blurred checker, a clipped ramp, smoothed noise.
2. **Scenario test bed** (`face3d/testbed`, seeded). Each scenario combines a subject, a protocol, a detector model and a set of faults.
   - Subjects: `random_subject` with 0.8 mm RMS asymmetry (facial-asymmetry 📄).
   - Protocols: studio ring, rear phone, selfie, camera-roll mix.
   - Detector model: class σ, a per-index bias field of 1–3 mm shared across views (reconstruction principle 5 🧠), 5 % outliers, and TTA spread.
   - A numpy rasteriser draws masks and procedural images for the contour and QA tests.
3. **Bridge tests.**
   - Pure functions: axis mapping, the key planner, the zip builder.
   - A `tomllib` manifest lint: licence, tagline ≤ 64 characters, no numpy wheel, no network permission.
   - A headless script for `blender -b --factory-startup --python-exit-code 1`, to run in CI elsewhere.

### 5.2 Fault-injection matrix

All targets below are 🆕. M1 first records the current engine as the baseline.

| Fault | Must raise | Required | Degradation bound |
|---|---|---|---|
| 1 mirrored view among ≥ 3 | `Q-MIRROR` | TPR ≥ 0.95 at ≥ 0.8 mm asymmetry; FPR ≤ 0.02; `undetermined` on symmetric faces | shape error ≤ 1.1 × clean |
| Orientation not baked | `Q-ORIENT` | TPR ≥ 0.99 | — |
| EXIF cropped ±30 %, or missing | `C-FOCAL-PRIOR` if unobservable | focal error < 5 % when views span ≥ 60° (community R8.4 🧠) | ≤ 1.2 × clean |
| Selfies at 0.35 m | `Q-SELFIE`, tier ≤ B | z within 15 % | nose-width error ≥ 30 % lower than the ρ = 0 fit |
| Jaw open 5–15°; smile | expressive tag | TPR ≥ 0.9 | rigid regions ≤ 1.1 × clean |
| Beauty warp: eyes +6 %, jaw −4 % | `Q-RETOUCH` | TPR ≥ 0.8 with ≥ 3 clean views | identity bias ≤ 0.5 mm |
| Off-axis wide-angle warp | gate or k₁ test | TPR ≥ 0.8 | — |
| Glasses, beard, hair | tag actions | jaw *prior-driven* under a beard | scalp inside the hull |
| Face 150 px wide | `Q-SMALL` | — | coverage still holds |

### 5.3 Honesty metrics

- **Coverage.** In regions marked *measured*, between 0.90 and 0.99 of vertices must satisfy |error| ≤ 1.96·σ_rep (🆕).
- **False confidence.** At most 5 % of *measured* regions may exceed twice their T6 RMS target (🆕).
- **False alarms.** At most 1 spurious flag per 10 clean photos (🆕).
- **Promotion rule.** A change becomes a default only if held-out error drops and coverage holds.

Shape accuracy is scored by `face3d/eval`: exact point-to-triangle distances under both NoW-style and landmark-only alignment, reporting median, p95, F@1/2 mm, per-region bias, scale error and configuration RMS (EV-1/2 🧠).

### 5.4 Real-data bed (outside CI)

- **Sitters.** Start with 1–3 consenting sitters (benchmarks-metrics 🧠) and grow to about 10, spanning age, skin tone, beards, glasses and hair.
- **Per sitter:**
  - a scan, plus a repeat scan to set the noise floor;
  - a protocol ring;
  - a rear-phone set, a selfie set and a dated camera-roll set.
- **Data handling.** Retention follows ethics §4. Only aggregates are committed, behind a leakage guard.
- **What it calibrates:**
  - every 🧠 and 🆕 σ and gate;
  - detector bias and the semantics maps;
  - a six-face lineup test (target ≥ 80 %).

### 5.5 What the artist sees

- **Per-camera sheets** (community R8.1 🧠): photo, clay render, 50 % overlay, difference image, silhouette chamfer, and flipped, blurred and 64 px versions.
- **Worst landmarks first**, in % IOD.
- **Leave-one-view-out (LOVO) check**: a view is flagged when its held-out error exceeds 2 × its in-sample error (reconstruction principle 15 🧠).
- **Caliper sheet**, flagging any difference above 2 mm.
- **Canon z-scores**, phrased in art vocabulary.
- **Likeness lint**: flags only |model − photo| > 2σ_photo, and never pulls a feature toward the mean (community R8.2 🧠).
- **"Over-symmetric" warning** when the mirror RMSD falls below 0.3 mm.
- **Approval renders** from about 1 m, and from the camera of the sitter's favourite photo (camera-perspective-distortion ↔️).

## 6. Milestones

Each milestone ships on its own and is tested here on synthetic data.

- **M1 – Test bed first:** `face3d/eval`, `face3d/testbed`, scorecard and smoke suite. *Accept:*
  - point-to-triangle matches brute force to 1e-9;
  - a known similarity transform is recovered;
  - the current engine's baseline scorecard is committed;
  - the smoke suite runs in ≤ 90 s.
- **M2 – Ingest and QA:** EXIF, HEIF EXIF and PNG reading; orientation; schemas; policy gates; §3.1; the focal ladder; the `triage` CLI. *Accept:*
  - byte-fixture goldens pass;
  - each gate fires on its fixture and stays silent on clean inputs;
  - runs without consent are refused (ethics F3);
  - output is deterministic.
- **M3 – Robust cameras and BA:** §3.2–3.5, observability, LOVO. *Accept:*
  - sweeps over z (0.25–5 m) and f35 (13–200 mm) meet the §5.2 camera, mirror and orientation rows;
  - unobservable focal lengths are reported;
  - existing tests still pass.
- **M4 – Nuisances:** §3.6. *Accept:* the matching §5.2 rows.
- **M5 – Template kit, warp, uncertainty:** §3.7, §3.9 and §3.10. CI uses a procedural stand-in head; the real CC0 kit is built offline with recorded hashes. *Accept:*
  - the finite-difference propagation check passes;
  - smoke coverage is between 0.90 and 0.99;
  - the experimental basis stays off unless it wins.
- **M6 – Contours:** §3.8. *Accept:*
  - the tracer lands within 1 px of rendered edges;
  - profile error ≤ 1.5 mm;
  - no scalp vertex sits outside the hair hull.
- **M7 – Blender MVP:** §4. *Accept:*
  - bridge and manifest lints pass;
  - the zip contains no wheels and no non-CC0 assets;
  - headless scripts exist for the 4.5 and 5.2 LTS lines.
- **M8 – Detector helper, texture, review:** the helper's JSON contract is tested against a fake backend. *Accept:*
  - gains recovered within 2 % (TEX-8 🧠);
  - no colour on occluded texels;
  - filtered views excluded.
- **M9 – Calibration release:** the §5.4 bed converts 🧠 and 🆕 values into measured ones. Its tooling is tested; its data stays out of CI.

## 7. Risks and deliberate omissions

**Risks**

- **No proven licence-clean statistical shape model.** The baseline prior is weak in depth. Coverage rules and next-best-photo prompts push users toward adding profile views.
- **Most values are provisional.** About 70 % of the cited values are 🧠, and the 🆕 gates are ours. All stay labelled provisional until M9.
- **Synthetic detector errors are not MediaPipe's real errors.** The M9 semantics calibration addresses this.
- **Some faults cannot be detected:** mirroring of near-symmetric faces or selfie-only sets, and a filter on the only photo. These are reported as `undetermined`.
- **Open packaging questions:** cp313 MediaPipe wheels, whether the store accepts bundled models (C7/C8), HEIC loading in Blender, and Blender 5.x attribute names. The helper and manual pins keep every stage usable meanwhile.
- **Solver scale.** The dense Hessian is enough for about 150 landmarks × 12 views; beyond that the Schur complement takes over (M3).
- **Alarm fatigue.** Its rate is measured (§5.3).

**Left out of the default path, on purpose**

- **Monocular depth, generative fill, Gaussian avatars and photometric shape terms.** These are not measurements (reconstruction principles 12–14). They may return later as opt-ins, behind the test bed.
- **Automatic segmentation of beards, glasses and hair.** Covered by user tags plus an optional SAM helper.
- **Identity embeddings.** Opt-in and for evaluation only. Most weights carry non-commercial (NC) licences, and embeddings are never stored.
- **"Un-filtering" retouched photos.** We down-weight them instead.
- **Phone-video depth, ear detail beyond silhouette plus prior, hair grooming, teeth and fine lid detail.** These wait for their gap-topic notes.
- **Symmetrising, anonymising, 1:N matching and URL import.** These are never built (ethics F17, F18, A5).
