# Proposal: a robustness-first photo-to-head engine

*Design angle: robustness first, for the photos people actually take. 2026-11-20. Based on `face3d/` at 887c5e5 (42 tests passing) and `research/_raw/requirements_*.md`.*

**How to read the citations.** Each number cites its source note and badge:

- ✅ verified
- 📄 single source
- 🧠 unverified expert knowledge
- ↔️ contested
- 🆕 proposed here, unsourced; to be calibrated on the test bed (§5)

The `open-template-head-kit` and `cranium-under-hair` citations point to draft tables in `research/data/`, because those notes do not exist yet. Every 🧠 and 🆕 value is a named config entry that carries its badge.

## 0. Thesis

Fitting a head to good photos is the easy part. This tool succeeds or fails on mirrored selfies, messenger copies stripped of EXIF, beards and a smile in the only three-quarter view. The design rests on four rules:

- Every known failure mode gets a simple test whose result can be checked.
- Weak evidence is down-weighted or excluded, never fitted through.
- The result states what it can still claim, region by region.
- Everything is measured on a fault-injection test bed before it becomes a default.

When a simple method and a clever one compete, the simple one wins.

## 1. Vision and user journey

1. **Consent.** Every project starts with a `ConsentRecord` (ethics §2.1). Nothing runs without the `RECONSTRUCT` scope.
2. **Photos.** Each photo is hashed and its EXIF read: orientation, focal length, lens, date and editing software. Orientation is baked into a working copy, and the original is never changed.
3. **Landmarks.** They come from MediaPipe, through an external helper or an optional wheel, or from manual pins. Pins and JSON import always work, so no download is ever required (ethics A4).
4. **Triage.** Each photo gets a QA card covering distance, focal evidence, lens risk, mirroring, expression, occluders, blur, resolution and retouching. Every flag names its action and the reason, e.g. *"selfie at ≈0.35 m: colour and frontal outline only, not nose projection"*.
5. **Solve.** A robust multi-view bundle adjustment (BA) runs, followed by the mirror check and an observability report.
6. **Fit.** The CC0 template is warped in stages, then contours and silhouettes are fitted. Profiles are traced with edge snapping.
7. **Review.** A claims ledger marks each region as *measured*, *constrained*, *prior-driven* or *unobserved*. Alongside it the artist gets held-out-view checks, per-camera overlays, the worst landmarks, and a suggested next photo ("add a left profile").
8. **Hand-off.** The fit is delivered as shape keys on a stable topology, plus an `artist` layer, a Multires copy, an optional gated texture and export provenance.

**What we promise at each input tier.** The tier is computed from the evidence, not chosen by the user.

| Tier | Typical input | Promise | Label |
|---|---|---|---|
| S | ≥ 5 views over ±60–90° yaw at 1.5–3 m, tele lens, EXIF, scale reference | Metric; depth measured; face RMS ≤ 1.5 mm (benchmarks-metrics T6 🧠) | `metric` |
| A | Rear phone camera, ≥ 3 views, one at \|yaw\| ≥ 45°, EXIF | Proportions; depth where coverage rules hold (§3.10); iris scale ±2–4 % (multi-view-fitting 🧠) | `iris-scaled` |
| B | Camera roll: mixed devices and dates, no EXIF, expressions | Frontal proportions through solved cameras; depth from the prior unless a view exceeds 60° yaw | `proportions only` |
| C | One photo, or selfies only | Blockout matching its own camera; no claims about nose projection, ears or cranium | `blockout` |

## 2. Architecture

### 2.1 Modules

The engine imports only `numpy`, `math`, `json`, `struct`, `zlib`, `hashlib` and `tomllib`, all as relative imports, and never `bpy` (blender A1). In the status column, E = exists, X = extend, N = new.

| Path | St | Purpose |
|---|---|---|
| `face3d/core/{schema,policy,config}.py` | N | Versioned formats; consent scopes and licence taint as an AND over components (ethics A2); badged defaults; config SHA-256 |
| `face3d/io/exif.py` | X | Add DateTimeOriginal, Software, DigitalZoomRatio, LensMake and SubjectDistance; read every APP1 segment |
| `face3d/io/{heif_exif,png,image_ops,landmarks}.py` | N | HEIC EXIF from ISOBMFF boxes (pixels are never decoded); stdlib PNG; orientation and flip-with-permutation; landmark adapters |
| `face3d/qa/{image,photo,expression,mirror,retouch,flags}.py` | N | Gates from §3.1 and §3.6; flag registry recording code, severity, evidence, action and source |
| `face3d/solve/pnp.py` | X | Multi-start, cheirality, twin flag, CAM-3 hypotheses, Huber in σ units |
| `face3d/solve/{noise,observability}.py` | N | §3.2; σ(log f), σ(log z), P, leave-one-view-out (LOVO) |
| `face3d/solve/bundle.py` | X | Covariance blocks, visibility, jaw hinge, distance priors, soft focal ties, view cap, 4σ rejection, Schur marginals |
| `face3d/model/{registry,template_kit,prior,nuisance}.py` | N | Landmark registry (anatomy R2.1), hash-checked kit, priors and gates, jaw hinge, occluders |
| `face3d/fit/{template,silhouette}.py` | X | Gated stages with a reflection check; sliding and one-sided contour terms |
| `face3d/fit/{contour_trace,uncertainty}.py` | N | Dynamic-programming edge snap; vertex σ; claims ledger |
| `face3d/geometry/rbf.py`, `mesh/laplacian.py` | X | Per-landmark Λ; per-vertex stiffness |
| `face3d/{texture,eval,testbed}/` | N | Z-buffer blending; point-to-triangle metrics (reconstruction EV-1); scenario test bed |
| `face3d/pipeline.py`, `__main__.py` | N | Deterministic runner; CLI `python -m face3d {triage,solve,fit,report,testbed}` |
| `tools/{detect_mediapipe,build_template_kit,build_extension}.py` | N | Out-of-process detector (Tasks API, `IMAGE` mode, `num_faces=2`, test-time augmentation, TTA); hash-checked builds |
| `blender_ext/face3d_head/` | N | Extension (§4); the engine is vendored at build time |

### 2.2 Data flow

```
photos → ingest (sha256, EXIF, orientation, consent) → LandmarkSet (+TTA spread)
→ triage (flags, tags, σ multipliers, focal ladder) → multi-start PnP + mirror test
→ robust BA → observability + LOVO → warp A→B→C → contours D → uncertainty → ledger
→ result.json/fit.obj/sigma.npy → Blender → artist → gated texture → export
```

Every stage is a pure function, cached under the hash of its inputs and config. Editing one pin re-runs only the stages downstream of it.

### 2.3 Data formats

All files are JSON with `format` and `version` fields. Arrays longer than about 1,000 values go to `.npy` files, referenced by path and SHA-256.

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

- **Scheme file.** Bundled; our own work, released CC0. The scheme is read from this file and never guessed from the point count (reconstruction FMT-1). Fields: `n`, `lr_permutation`, `midline`, `classes`, `convention` (surface or semi-contour), `sigma_iod` per class, an `anatomical` name→index map, and `verification` for each entry.
- **Template sidecar.** Filled entirely by the kit builder. Fields:
  - `source`: upstream SHA-256, `CC0-1.0`, `commercial_ok`
  - `units: mm`, `topology_sha256`, `order_checksum`
  - `landmarks`: kind, triangle, barycentric coordinates, σ, provenance
  - `scheme_maps`: one per detector version
  - `regions`, `mirror_map`, `contours`, `stiffness`
  - `basis`: K, SHA-256, status
- **Result file.** Fields:
  - run identity: `config_sha256`, `seed`, input hashes, `tier`
  - per camera: K, R, t, f35, z, P, σ_logf, `focal_status`, and the mirror result `{decision, Δ, status}`
  - per view: in-sample and LOVO RMS in % IOD, `noise_scale`, `weight_share`, `rejected_frac`, flags
  - `scale {mode, s, σ}`
  - 3D landmarks with their covariance
  - `regions [{name, status, k, σ_mm, why}]`
  - `licence {commercial_ok, components}`
  - the mesh and per-vertex σ

### 2.4 Coordinate conventions

All conventions are fixed in `core/schema.py`, and each has a round-trip test.

- **Image.** Coordinates are continuous, with the origin at the top-left pixel's corner, so pixel (i, j) has its centre at (i + ½, j + ½), as `camera.py` already assumes.
  - MediaPipe's normalised x maps to u = x·W.
  - Resizing scales by W/W′. We do not use the "+0.5" form from blender D3.
  - A horizontal flip is u′ = W − u, combined with the label permutation π.
- **Camera.** OpenCV convention: X_c = R·X_w + t, +y down.
- **Head.** Millimetres in float64. +x is the subject's left, +y up and +z forward, with the origin on the midsagittal plane (anatomy R1.1).
- **Blender.** An `R_x(+90°)` parent maps (x, y, z) → (x, −z, y), with a scale of 0.001 (blender A8). `to_blender_camera` is already tested.
- **IOD.** The outer-canthal distance ex–ex (landmark-detection T2). Interpupillary values are multiplied by 0.70 to convert (T3 🧠). Once the camera is solved, IOD_px = f·IOD_mm/z_v. We do not use the 2D ex–ex distance, because it halves at 60° yaw.
- **Determinism.**
  - All randomness comes from `default_rng(seed)`.
  - Hypotheses run in a fixed order, sorts are stable, and arithmetic is float64.
  - Golden values are compared at rtol 1e-5 (blender Q2).
  - CI runs CPython 3.11 with NumPy 1.26 and CPython 3.13 with NumPy 2.x (A4).

## 3. Algorithms

### 3.1 Input QA gates

Gates never pull a value toward a population norm (anatomy §6). Each gate takes one of five actions: down-weight, drop a class, exclude from geometry, exclude from texture, or ask the user.

| Failure | Detection (threshold) | Action | Source |
|---|---|---|---|
| Orientation ignored | `exif_applied` false; view RMS > 3σ; roll ≈ ±90° | Bake orientation and re-detect | blender §10 🧠 |
| EXIF stripped | No Make, Model or f35 | Source-type prior (§3.3) | community R2.2 🧠 |
| Crop or zoom | Size ≠ PixelXDimension; aspect ratio not native; zoom > 1 | σ_logf 0.08–0.10; free principal point (σ 10 %) | community R2.5 🧠 |
| Front camera | LensModel contains "front" | Mirror test; selfie distance prior | camera-perspective-distortion 🧠 |
| Near camera | Solved z, cross-checked with f·63/IPD_px; warn < 1 m, strong < 0.8 m | Below 0.6 m: 2D and texture only | community §9 🧠 |
| Face-warp correction | f35 ≤ 16 mm; face beyond 60 % of half-diagonal; > 25° off-axis | σ × 2, or exclude from geometry | community R1.7 (warp ✅, thresholds 🧠) |
| Low resolution | Face < 250 px: warn; < 120 px: reject; iris < 20 px | σ floor; no iris scale; no detail | community R1.4 🧠, R4 ↔️ |
| Blur, blink, clipping | Laplacian variance in the bottom 20 %; eye aspect ratio (EAR) < 0.2; > 2 % of skin clipped | Down-weight; drop lid points; no photometry | community R1.4 🧠 |
| Mixed dates | Date span > 18 months | Split into date clusters | community §9 🧠 |
| Two faces; no consent | `num_faces=2` at score ≥ 0.6; sha256 not in the consent record | User picks; block | blender ML 🧠; ethics F1–F2 |

### 3.2 Noise model

For landmark i in view v, with tangent t̂ taken from its neighbours, the covariance is

  Σ_iv = s_v²·m(c_i, tag_v)²·R(t̂)·diag(σ_n², σ_t²)·R(t̂)ᵀ

where each directional σ is

  σ_• = max(σ̂_•(c_i)·IOD_v·√(N/N_eff), σ_tta, σ_floor)

- **Class σ̂** (% IOD, normal/tangent): iris 1.0; anchors 1.5; lid and lip contours 2/5; pronasale 2.5; brows 3–5/6; jaw 2.5/10–15 (landmark-detection T5 🧠).
- **Dense points.** N_eff is 60–100. The √(N/N_eff) inflation applies only outside a curated subset of about 100 points.
- **σ_tta** is the spread over 6–10 TTA passes (BA-2 🧠).
- **σ_floor** = max(0.5 px, k·face_px/256), with k = 0.6 for inner points, 0.4 iris, 1.0 brows and 1.5 contours (blender ML 🧠).
- **Per-view scale.** s_v² = clip(median‖Σ^{−½}r‖²/1.386, 1, 9), where 1.386 is the median of χ²₂. This is a MAD-style estimate (deformation-fitting-math 🧠). Retouched, warped or misoriented views lose weight automatically. Flag the view if s_v > 2 (🆕).
- **View weights.** Each view is weighted 1/(views in its 15° yaw bin), and no view may supply more than 40 % of the total information (community R1.8 🧠).

This model replaces `sigma_px = 1.0`, which is ≈13× too tight (landmark-detection 🧠), and the isotropic default of 0.006 × diagonal.

### 3.3 Camera initialisation

**Focal prior.** The first matching rule in this ladder sets the log-normal prior (CAM-6, community R2.2 🧠):

| Evidence | σ_log | Centre |
|---|---|---|
| SfM or calibration | 0.005–0.02 | supplied value |
| EXIF f35, uncropped | 0.04 | EXIF |
| EXIF f35, crop suspected | 0.08–0.10 | EXIF |
| FocalLength + focal-plane resolution | 0.10 | derived |
| Phone, no focal tag | 0.25 | 26 mm |
| Nothing | 0.6 | 50 mm |

Today's fallback of 0.35 cannot reach phone lenses.

**Focal groups.** Photos are grouped by (Make, Model, LensModel, f35, W, H, still/video). Each group gets a soft focal tie of σ 0.02 instead of being hard-shared (CAM-5 🧠).

**Distance prior** on log z (CAM-6 🧠, reading σ as log-σ):

| Camera | Median | σ |
|---|---|---|
| Front camera | 0.35 m | 0.3 |
| Rear camera | 0.8 m | 0.4 |
| Tele | 2 m | 0.4 |
| Unknown | 1.0 m | 0.7 |

A tape-measured distance is good to ±5 cm (community R2.4 🧠). z is bounded to 0.25–10 m (blender C6).

**Multi-start PnP.**
- f35 hypotheses are {13, 24, 26, 35, 50, 77, 85, 120, 135, 200} mm (CAM-3 🧠); the current list lacks 26, 77 and 120.
- Each hypothesis starts from an affine pose, a pitch-flipped pose and a yaw-mirrored pose.
- Poses that fail cheirality are rejected.
- If two poses more than 10° apart score within 20 % of each other, raise `C-TWIN` and carry both into BA (🆕).

**Off-axis faces.** Rotate the face-centre ray onto the optical axis before initialising, then rotate back (camera-perspective-distortion 🧠).

**Order.** Solve the most frontal, most complete view first. Initialise later views against the BA consensus rather than the template, which reduces pull toward the mean face.

### 3.4 Mirrored images

Let X̂ be the consensus from the other views (the template if there is only one view). Let C₀ be the robust PnP cost of the view as given, and C₁ its cost when flipped: u′ = (W − u_x, u_y), with labels permuted by π. Define Δ_v = (C₀ − C₁)/C₀.

**Discriminability.** Let A = ½(X̂ − M·X̂_π) be the shape's asymmetric part, where M mirrors x and π swaps left/right labels. The expected cost gap is g = Σ‖Σ^{−½}J_i A_i‖². If g < 4 (🆕), the answer is `undetermined`: a near-symmetric face seen through noisy landmarks cannot be told apart from its mirror image, and the report says so.

**Decision.** If Δ_v > 0.2 (community R1.6 🧠):
- if the photo is from a front camera, or the other views agree, it is flipped automatically and the flip is logged;
- otherwise the user is asked to compare the two orientations, checking the hair parting or a mole (likeness-mistakes 🧠).

**All views mirrored.** If every view is mirrored (a selfie-only set, say), geometry cannot detect it. The project is marked `mirror: unverifiable` and every claim that depends on asymmetry is flagged.

### 3.5 Robust bundle adjustment

  E = Σ_v w_v Σ_i ρ_H(‖Σ_iv^{−½}(π_v(X_i + J_i(θ_v)) − u_iv)‖; δ = 2) + Σ_v E_contour,v
    + Σ_g ((log f_g − μ_g)/σ_g)² + Σ_{v∈g} ((log f_v − log f_g)/0.02)² + Σ_v ((log z_v − μ_z)/σ_z)²
    + E_shape(X) + Σ_pairs ‖Σ_sym^{−½}(X_l − M·X_r)‖² + Σ_mid (x_i/σ_mid,i)² + E_scale + E_pins

- **Robust loss.** Huber at 2σ, measured in σ units. It replaces today's thresholds of 3 px in PnP and 3σ in BA. After convergence, residuals above 4σ are dropped and the problem is re-solved once. A view that loses more than 15 % of its points is flagged (BA-5 🧠).
- **Visibility.** Weight is 0 when n·(−v) < cos 80°, rising to 1 at cos 60°. Far-side oval points are dropped when |yaw| > 25° (BA-3 🧠).
- **Symmetry and midline σ** (anatomy R4.2 🧠):
  - Bilateral pairs: canthi 0.7–1.0 mm, brows 1.5, alae 1.0–1.5, cheilia 1.5–2.0, gonia 2.5–3, ears 3–4.
  - Midline: n 0.75–1.0 mm, prn/sn 1.5–2.0, pg/me 2–3.
- **Covariance.** Use the Schur complement once N ≥ 100. Each landmark reports its prior share p_i = σ²_post/σ²_prior. *Likeness mode* widens the prior until p_i ≤ 0.2 wherever at least two views see the point (anatomy R1.4 🧠).
- **SfM cameras.** Run triangulation → Umeyama → a 3D shape solve. Landmarks never move SfM cameras (BA-12 🧠).

### 3.6 Expressions, occluders and retouching

**Expression tags.** Each blendshape score is measured as Δb, its rise above the subject's own minimum across views, not above zero (landmark-detection 🧠).
- *Neutral*: every Δb is below its threshold (jawOpen 0.08, mouthSmile 0.15, eyeBlink 0.35, browInnerUp 0.2; landmark-detection 🧠).
- *Expressive*: any of smile > 0.25; squint, eyeWide or brow > 0.3; or blink > 0.4 (anatomy §6 🧠).
- *Mild*: anything between the two.

Without blendshapes, geometry decides:
- if the inner-lip gap divided by mouth width (ch–ch) exceeds 0.04, the lips are parted and sto and li are dropped (anatomy §6 🧠);
- if mouth width exceeds 1.08× its median across views, the view counts as a smile (🆕).

Tags are refined from the residuals for at most three rounds (BA-9 🧠).

**Landmark σ multipliers**, for neutral / mild / expressive views (expression-neutralization 🧠):

| Landmarks | Neutral | Mild | Expressive |
|---|---|---|---|
| Rigid | 1 | 1 | 1–1.5 |
| Semi-mobile | 1 | 1.5–2 | 2–3 |
| Mobile | 1 | 3 | dropped |
| Jaw-dependent | 1 | 1 | 1 |

Jaw-dependent points keep a multiplier of 1 because θ models the jaw directly.

**Jaw hinge.** This needs no expression dataset:

  X_i(θ) = c + R_axis(θ)(X_i − c)

The axis runs through the template's condyles, about 10–13 mm in front of tragion (BA-1 🧠). On neutral views θ ~ N(1.5°, 1°), bounded to [0°, 30°] (anatomy §4 🧠).

**Expression basis ψ** is opt-in and loaded only through licence-clean adapters, such as FLAME 2023 Open. It is anchored by the neutral views: their mean ψ ≈ 0 with σ 0.1 (BA-9 🧠). If no view is neutral, mouth and lid measurements below 1 mm are suppressed.

**Occluder tags.** The user sets these with one click per photo. No licence-clean default detector exists for them.

| Tag | Effect | Source |
|---|---|---|
| Glasses | Eye σ × 2; no iris scale; lid points under the frame dropped | anatomy R3.4 🧠 |
| Beard | pg, gn, me and jaw points dropped; the beard outline becomes a one-sided bound; jaw stays *prior-driven* unless a shaven photo exists | reference-photography-protocol, community R5.4 🧠 |
| Hair | Ear and temple weights set to 0; no silhouette above the trichion | blender S3 🧠 |
| Makeup | Lip and brow borders σ × 2 | artstation-likeness 🧠 |

Glasses get a consistency check: lenses magnify about 1–1.5 % per dioptre, so a view is flagged if its iris diameter divided by en–ex differs by more than 3 % from the glasses-free median (🆕).

**Retouching and beauty filters.** Three independent tests, each judged against the other views:
1. EXIF `Software` matches a known editor (🆕).
2. Skin smoothness: SSI_v = cheek band energy ÷ brow and iris band energy, measured at matched mm/px. Flag if SSI_v < 0.5 × the set median (🆕).
3. Residual patterns: regress the residuals on two fixed fields, eyes pushed radially outward (enlargement) and jaw pushed inward along its normal (slimming). Flag if t > 3.

A flagged view gets σ × 2–3 and is excluded from texture (artstation-likeness ↔️; tests 🆕). A filter applied to the only photo cannot be detected, and the ledger says so.

**Non-pinhole processing.**
- A diagnostic k₁ is fitted with prior σ 0.02. If |k₁/σ| > 3 on a phone JPEG, the report reads "non-pinhole processing suspected" (CAM-1 🧠).
- If the slope of the radial residual against ρ_i·δ_i implies more than 5 % magnification error, the distance or focal is wrong (community R2.8 🧠).

### 3.7 Licence-clean shape prior

No permissive large-population head model is confirmed (reconstruction §12), so the prior has three layers.

1. **Baseline:** an anisotropic Gaussian per landmark, with σ = 1.0–1.5× the population SD and an 8 mm fallback (anatomy R4.1 🧠). Ratio priors are used only as diagnostics.
2. **Experimental:** X = μ + B·c with c ~ N(0, I).
   - B is a mass-weighted SVD of the CC0 MPFB2 face targets, keeping K = 40–80 modes.
   - The variances come from an "anthropometric morphable model": 2,000–5,000 sampled heads matched to published norms, keeping 95–99 % of the variance (open-template-head-kit 🧠).
   - This layer stays off until it lowers held-out error and keeps coverage (§5.3).
3. **Opt-in:** FLAME 2023 Open, loaded from a user path with a SHA-256 pin and attribution (CC-BY-4.0; contents unverified 📄). Any other FLAME version or BFM sets `commercial_ok=false` (LIC-1).

**Gates.**
- ‖c‖² above the 99.9 % χ²_K quantile, or any |c_i| > 3: implausible (MM-5 🧠).
- ‖c‖² < K − 2√(2K): "pulled toward average" (community R5.8 🧠).

**Nothing is fabricated.**
- Template landmarks are clicked in Blender by two annotators and accepted only where they agree within 1 mm (🆕).
- MediaPipe index maps come from detector-semantics calibration: the template is rendered from 20–50 cameras, the detector is run on the renders, and each index's mean landing point is stored as barycentric coordinates (landmark-detection 🧠).
- Both are built offline with provenance. CI checks hashes, schemas, that the L/R map is an involution, and that midline points map to themselves.

### 3.8 Contours, silhouettes, profiles and hair

**Edge snap.** This refines a coarse polyline (at least 5 clicks, or the detector's oval points). There are M stations, and each may move an offset k ∈ [−L, L] along its normal, with L = 3 % of IOD. The snap minimises

  C = Σ −g_j(k_j) + λΣ|k_j − k_{j−1}|,

where g is the gradient magnitude after a 1 px Gaussian and λ = 0.2 × median g (🆕). A Viterbi pass solves this in O(M·L²). It is deterministic and has no learned weights. Each point gets σ_n = max(1 px, 1/√curvature). Segment Anything (SAM, Apache-2.0) is optional and runs only in the helper.

**Sliding residuals.** r = n̂·(p_j − q)/σ_n, where q is the point's nearest outline segment, re-matched every iteration (BA-4, blender S1 🧠). These are combined with the existing outline-to-vertex term and trimmed at 10 %. The fixed 60 px gate becomes 5 % of IOD (🆕).

**One-sided masks** (hair, beard, hat). r = max(0, d_mask + m)/σ, with margin m = 0–3 mm (community R5.4 🧠) and a weight of 10× skin (cranium-under-hair 🧠).
- The scalp must stay at least 2 mm inside the hair hull (blender W7 🧠).
- Cranium σ follows the visual-hull overshoot: 7.8 mm with 4 views, 1.9 mm with 8 (cranium-under-hair, arithmetic).

**Profiles.** For views with |yaw| > 60–70°, detector points are discarded (landmark-detection 🧠). User pins on g, n, prn, sn, ls, li and pg are used instead, at σ 1 % of IOD (blender S4 🧠).

**Acceptance.**
- Profile error ≤ 1–1.5 mm at the nose tip and chin (SIL-3 🧠).
- Contour within 1 % of face height (S5 🧠).
- If the interior fits but contours fail, report "f and z wrong", not a shape error.

### 3.9 Template warp

| Stage | Operation | Advance when |
|---|---|---|
| A | Umeyama, proper and reflected. If reflected RMS < 0.5 × proper, flag "mirrored source" and never auto-flip. If the 7-landmark RMS is > 10 mm, the axes are wrong (blender W2 🧠) | always |
| B | RBF with φ = r: (Φ − Λ)w + Pa = y, with Λ = diag(α·σ_i²) and α = 10⁻² (MM-8 🧠; the sign is already fixed in `rbf.py`) | landmarks < 2–3 % IOD (community R5.2 🧠) |
| C | Bilaplacian with per-vertex stiffness: lid margins 3.0, lips 0.3, forehead 0.5, ligaments 3–5 (anatomy R5.9 🧠). Offsets capped at 3–5 mm unless ≥ 2 views agree (MM-10 🧠) | RMS improves < 1 % per iteration |
| D | Silhouettes via `ReducedDeformer`. No landmark may move > 0.5 mm | contour ≤ 1 % of face height |

**Gates checked at every stage:**
- triangle det J > 0.2, with no flips (MM-11 🧠);
- lid–globe gap between 0 and 0.3 mm (blender §4 🧠);
- mirror RMSD between 0.3 and 1.5 mm (anatomy §6 🧠).

Targets are never symmetrised. The detail layer is off by default. It runs only on neutral, unfiltered views at ≤ 0.08 mm/px where at least 2 views agree; otherwise detail is labelled `synthetic` (anatomy R5.11 🧠).

### 3.10 Uncertainty and the claims ledger

**Vertex covariance.** Stages B and C are linear in the targets: V = V₀ + A(X − X₀). Unit solves give A, and then

  Cov(V_j) = Σ_ab A_ja A_jb Cov(X_a, X_b) + σ²_res·I

The residual σ_res depends on the region: lids 1–1.5 mm, nose 2–3, cheeks 2.5–4, ears 3–5, scalp 3–6, neck 5–10 (open-template-head-kit 🧠). A finite-difference test checks A.

**Reported σ.** σ_rep² = σ²_post·max(1, κ²) + σ²_bias.
- κ is the LOVO ratio of observed to predicted error.
- σ_bias is 1–3 mm per class until a detector-semantics map exists, because detector bias does not average out across views (reconstruction principle 5 🧠).
- The Hessian σ is never shown on its own.

**Region status.** With k = 1 − σ²_post/σ²_prior:
- *measured*: k ≥ 0.8 (anatomy §6 🧠) and the coverage rules below hold;
- *constrained*: 0.5 ≤ k < 0.8;
- *prior-driven*: k < 0.5 (🆕);
- *unobserved*: no view sees the region.

**Coverage rules.**
- Depth needs at least 2 views that differ by at least 30° (blender C7 🧠).
- Nose and chin projection need a front view plus one at |yaw| ≥ 60°.
- The jaw underside needs a low view (community R5.9 🧠).
- Ears need |yaw| ≥ 30° and pitch fixed by at least 2 views (R3.3 🧠).

**Focal and scale.**
- Focal length is estimated only when σ(log f) < 0.10 (blender C2 🧠). If σ exceeds 0.8 × the prior σ, the report says "focal from prior" (CAM-7).
- Scale is reported as *measured* (caliper, which overrides everything; anatomy R3.4), *iris*, *IPD prior* or *proportions only*. Scale references that disagree by more than 1 % are flagged (BA-10 🧠).

**Next-best photo.** The tool simulates candidate poses on a 15° grid and adds each to the Hessian. It recommends the pose that most reduces σ in prior-driven regions, weighted by the T6 region weights (benchmarks-metrics 🧠).

### 3.11 Texture projection

Projection runs only when reprojection error has median ≤ 1.5 px and max ≤ 3 px (blender T2 🧠), the consent covers `TEXTURE`, and `rights_basis ≠ unknown` (ethics §3).

The method (TEX-1…7 🧠):
- a numpy z-buffer with depth tolerance max(1 mm, 2σ_geom);
- view weight vis·cos²θ·footprint·edge, faded out between 60° and 75°;
- per-view gains in linear RGB, with log-σ 0.3 under auto exposure;
- a two-band blend split at 3 mm;
- 2048 px maps for phone sources.

Views that are filtered, retouched, warped or clipped, or that come from another date cluster, never feed the albedo. Texture is never mirrored. Without a colour chart, the albedo is labelled "absolute albedo unknown".

## 4. Blender add-on

**Package layout:** `blender_ext/face3d_head/` holds:
- `blender_manifest.toml`;
- `__init__.py`, plus `compat.py` probes that finish in under 100 ms;
- `bridge.py`, the only bpy↔numpy converter;
- `ops_*.py`, `ui_panels.py`, `overlays.py`, `jobs.py`, `keys.py`;
- the vendored `face3d/`;
- CC0 `assets/template/`, `LICENSE` and `NOTICE`.

| Operator | Does | Runs |
|---|---|---|
| `face3d.project_new`, `face3d.photos_add` | ConsentRecord; hash, EXIF, orientation-baked copies, GPS stripped (ethics F12) | main |
| `face3d.landmarks_import`, `face3d.detect` | Import JSON, or run the detector helper or wheel | job |
| `face3d.pin_edit`, `face3d.trace_contour` | Place pins in the photo camera (σ from zoom); draw a polyline, then edge-snap it | modal |
| `face3d.triage`, `face3d.solve`, `face3d.fit` | §3.1–3.10 | job |
| `face3d.apply_result` | Write cameras, keys and attributes. Refuses on a topology-hash mismatch or in Edit/Sculpt Mode (blender K1/K4) | main, UNDO |
| `face3d.bake_for_sculpt` | Duplicate, bake the key mix, clear keys, add Multires level 2–3 (K5, SK-3 🧠) | main, UNDO |
| `face3d.project_texture`, `face3d.review_sheet`, `face3d.prepare_sharing`, `face3d.export` | §3.11 and §5.5; purge leftovers (ethics F9); export with provenance and consent gates | job / main |

**Panels.** The Sidebar › *Face3D* tab has six panels:
- *Project & Consent*;
- *Photos*: a UIList with QA badges, tags, include toggles and mirror state;
- *Solve*: tier, focal status, z and P;
- *Fit*: stages and gates;
- *Review*: the ledger, LOVO results, worst landmarks and the next-best photo;
- *Export*: any blocking reasons.

**Overlays** use `gpu` draw handlers in each photo's camera view:
- σ ellipses around landmarks;
- residual arrows, exaggerated ×5;
- rejected points drawn in red;
- the traced outline against the projected silhouette;
- a flipped thumbnail for the mirror prompt.

In 3D, the `face3d_sigma_mm` and `face3d_status` attributes colour the viewport, and region face sets drive masks.

**Undo.** Engine state lives in hashed sidecar files, not on the undo stack. Objects carry `face3d_uuid` and are fetched again by it after an undo. Each job records its target's topology hash and refuses to apply if that hash has changed.

**Background jobs.** A job runs as `[sys.executable, "-I", launcher.py, job_dir]`, with its JSON and `.npy` files under `extension_path_user`. A timer polls every 0.1 s and does at most 20 ms of work per tick (blender A5 🧠). Cancelling kills the process, and a worker crash never loses sculpt work. Under `bpy.app.background`, jobs run synchronously.

**Shape keys** (blender K2/K3 🧠):

| Key | Content |
|---|---|
| `Basis` | Template mean |
| `F3D_stageB`, `F3D_stageD` | Diagnostic stages, value 0 |
| `F3D_ID_v<n>` | The likeness; written with `from_mix=False`, `slider_max` 1.5 |
| `artist` | Artist's edits, kept as a Δ across refits |

Expression keys are written only with `RIG_ANIMATE` consent (ethics F4). No key is ever applied in place, and nothing is remeshed.

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

**Store build:**
- no wheels;
- no network permission;
- CC0 assets only (blender L1);
- engine files carry MIT SPDX headers inside the GPL-3.0-or-later package (ethics A1);
- the minimum version is the oldest line CI tests (Q3).

**GitHub build:** adds per-platform MediaPipe wheels and a NOTICE. Whether this complies with platform rules is ↔️. The external helper runs in any Python, so cp313 wheel lag never blocks anything (blender-python-ml-deps 🧠).

## 5. Validation and QA

### 5.1 Test pyramid

1. **Unit and oracle tests.**
   - Analytic Jacobians match numeric ones.
   - Noiseless solves reach RMS < 10⁻⁶.
   - The camera↔Blender round trip holds to 10⁻⁶·s and the OBJ round trip to < 2 µm (blender Q1/Q2 🧠).
   - Schemas and policy tables are checked.
   - Each QA gate is tested on synthetic arrays: a blurred checker, a clipped ramp, smoothed noise.
2. **Scenario test bed** (`face3d/testbed`, seeded). A scenario combines a subject, a protocol, a detector model and a fault set.
   - Subjects: `random_subject` with 0.8 mm RMS asymmetry (facial-asymmetry 📄).
   - Protocols: studio ring, rear phone, selfie, camera-roll mix.
   - Detector model: class σ, a 1–3 mm per-index bias field shared across views (reconstruction principle 5 🧠), 5 % outliers, and TTA spread.
   - A numpy rasteriser draws masks and procedural images for contour and QA tests.
3. **Bridge tests.**
   - Pure functions: axis mapping, the key planner, the zip builder.
   - A manifest lint using `tomllib`: licence, tagline ≤ 64 characters, no numpy wheel, no network.
   - A headless `blender -b --factory-startup --python-exit-code 1` script, for CI that runs elsewhere.

### 5.2 Fault-injection matrix

All thresholds in this table are 🆕. M1 records the current engine as the baseline.

| Fault | Must raise | Required | Degradation bound |
|---|---|---|---|
| 1 mirrored view among ≥ 3 | `Q-MIRROR` | TPR ≥ 0.95 at ≥ 0.8 mm asymmetry; FPR ≤ 0.02; `undetermined` on symmetric faces | shape ≤ 1.1× clean |
| Orientation not baked | `Q-ORIENT` | TPR ≥ 0.99 | — |
| EXIF ±30 % crop, or missing | `C-FOCAL-PRIOR` if unobservable | focal error < 5 % when views span ≥ 60° (community R8.4 🧠) | ≤ 1.2× clean |
| Selfies at 0.35 m | `Q-SELFIE`, tier ≤ B | z within 15 % | nose-width error ≥ 30 % below the ρ = 0 baseline |
| Jaw open 5–15°, smile | expressive tag | TPR ≥ 0.9 | rigid regions ≤ 1.1× clean |
| Beauty warp (eyes +6 %, jaw −4 %) | `Q-RETOUCH` | TPR ≥ 0.8 with ≥ 3 clean views | identity bias ≤ 0.5 mm |
| Off-axis wide-angle warp | gate or k₁ test | TPR ≥ 0.8 | — |
| Glasses, beard, hair | tag actions | jaw *prior-driven* under a beard | scalp inside the hull |
| Face 150 px wide | `Q-SMALL` | — | coverage holds |

### 5.3 Honesty metrics

- **Coverage.** In *measured* regions, 0.90–0.99 of vertices must have |error| ≤ 1.96·σ_rep (🆕).
- **False confidence.** At most 5 % of *measured* regions may exceed 2× their T6 target (🆕).
- **False alarms.** At most 1 spurious flag per 10 clean photos (🆕).
- **Promotion rule.** A setting becomes the default only if held-out error drops and coverage holds.

Shape is scored by `face3d/eval`: exact point-to-triangle distance under NoW-style and landmark-only alignment, reporting median, p95, F@1/2 mm, per-region bias, scale error and configuration RMS (EV-1/2 🧠).

### 5.4 Real-data bed (outside CI)

- **Sitters.** Start with 1–3 consenting sitters (benchmarks-metrics 🧠) and grow to about 10, covering a range of ages, skin tones, beards, glasses and hair.
- **Per sitter:**
  - a scan, plus a repeat scan to measure the noise floor;
  - a protocol ring;
  - a rear-phone set, a selfie set and a dated camera-roll set.
- **Data handling.** Retention follows ethics §4. Only aggregates are committed, behind a leakage guard.
- **What it calibrates:** every 🧠 and 🆕 σ and gate, the detector bias and semantics maps, and the six-face lineup test (target ≥ 80 %).

### 5.5 What the artist sees

- **Per-camera sheets** (community R8.1 🧠): the photo, a clay render, a 50 % overlay, a difference image, the silhouette chamfer, plus flipped, blurred and 64 px versions.
- **Worst landmarks first**, in % IOD.
- **LOVO check**: flag a view when its held-out error exceeds 2× its in-sample error (reconstruction principle 15 🧠).
- **Caliper sheet**, flagging any gap over 2 mm.
- **Canon z-scores**, phrased in art vocabulary.
- **Likeness lint**: it flags only |model − photo| > 2σ_photo and never pulls a feature toward the mean (community R8.2 🧠).
- **"Over-symmetric" warning** when the mirror RMSD is below 0.3 mm.
- **Approval renders** from ≈1 m and from the sitter's favourite photo camera (camera-perspective-distortion ↔️).

## 6. Milestones

Each milestone ships on its own and is tested here on synthetic data.

- **M1, test bed first:** `face3d/eval`, `face3d/testbed`, a scorecard and a smoke suite.
  *Accept:* point-to-triangle distance matches brute force to 1e-9; a known similarity transform is recovered; the baseline scorecard is committed; the smoke suite runs in ≤ 90 s.
- **M2, ingest and QA:** EXIF, HEIF EXIF, PNG, orientation, schemas, policy gates, §3.1, the focal ladder and the `triage` CLI.
  *Accept:* byte-fixture goldens pass; every gate fires on its fixture and stays silent on clean inputs; running without consent is refused (ethics F3); output is deterministic.
- **M3, robust cameras and BA:** §3.2–3.5, observability and LOVO.
  *Accept:* sweeps over z (0.25–5 m) and f35 (13–200 mm) meet the §5.2 camera, mirror and orientation rows; unobservable focal lengths are reported; existing tests still pass.
- **M4, nuisances:** §3.6.
  *Accept:* the matching §5.2 rows pass.
- **M5, kit, warp and uncertainty:** §3.7, §3.9 and §3.10. CI uses a procedural stand-in head; the real CC0 kit is built offline with recorded hashes.
  *Accept:* the finite-difference propagation check passes; smoke coverage lies in 0.90–0.99; the experimental basis stays off unless it wins.
- **M6, contours:** §3.8.
  *Accept:* the tracer lands within 1 px of rendered edges; profile error ≤ 1.5 mm; no scalp vertex lies outside the hair hull.
- **M7, Blender MVP:** §4.
  *Accept:* bridge and manifest lints pass; the zip holds no wheels and no non-CC0 assets; headless scripts exist for 4.5 and 5.2 LTS.
- **M8, detector helper, texture and review:** the helper's JSON contract is tested against a fake backend.
  *Accept:* gains are recovered within 2 % (TEX-8 🧠); no colour lands on occluded texels; filtered views are excluded.
- **M9, calibration release:** the real-data bed (§5.4) turns 🧠 and 🆕 values into measured ones. The tooling is tested; the data stays out of CI.

## 7. Risks and deliberate omissions

**Risks.**
- **No proven licence-clean statistical shape model.** The baseline prior is weak in depth. Coverage rules and next-best-photo prompts push users toward profile views.
- **About 70 % of cited values are 🧠, and the 🆕 gates are our own.** They stay labelled provisional until M9.
- **Synthetic detector errors differ from MediaPipe's.** The M9 detector-semantics calibration addresses this.
- **Some failures cannot be detected:** mirroring of near-symmetric faces, mirroring in selfie-only sets, and a filter on a lone photo. These are reported as `undetermined`.
- **Open packaging questions:** cp313 MediaPipe wheels, the store's position on bundled models (C7/C8), HEIC support in Blender, and 5.x attribute names. The helper and manual pins keep every stage usable in the meantime.
- **The dense Hessian scales only to about 150 landmarks × 12 views.** Beyond that we use the Schur complement (M3).
- **Alarm fatigue.** It is measured (§5.3).

**Left out of the default path, on purpose.**
- **Monocular depth, generative fill, Gaussian avatars and photometric shape terms.** None of these are measurements (reconstruction principles 12–14). They may return later as opt-ins, behind the test bed.
- **Automatic beard, glasses and hair segmentation.** Replaced by user tags plus an optional SAM helper.
- **Identity embeddings.** Opt-in and for evaluation only. The weights are mostly non-commercial (NC), and embeddings are never stored.
- **"Un-filtering" retouched photos.** We down-weight them instead.
- **Phone-video depth, ear detail beyond the silhouette and prior, hair grooming, teeth and fine lid detail.** These wait for their gap-topic notes.
- **Symmetrising, anonymising, 1:N matching and URL import.** These are never built (ethics F17, F18, A5).
