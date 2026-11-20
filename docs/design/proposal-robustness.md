# Proposal: a robustness-first photo-to-head engine

*Angle: robustness first, for the photos people actually take. Written 2026-11-20 against `face3d/` at commit 887c5e5 (42 tests pass) and `research/_raw/requirements_*.md`.*

**How to read the citations.** Each value cites a topic note and that note's badge:

- ✅ verified
- 📄 single source
- 🧠 unverified expert knowledge
- ↔️ contested
- 🆕 introduced by this proposal, with no source; it must be calibrated on the test bed (§5)

Two gap topics have no note yet. For `open-template-head-kit` and `cranium-under-hair`, the citations point to their draft tables in `research/data/`. Every 🧠 and 🆕 value ships as a named config entry that carries its badge.

## 0. Thesis

Accuracy on good photos is the easy part. Real inputs include mirrored selfies, messenger copies with no EXIF, beards over the jaw, and a smile in the only three-quarter view. The engine therefore does four things:

1. It detects each failure mode with a simple, verifiable test.
2. It degrades gracefully: weak evidence is down-weighted or excluded, not fitted through.
3. It states, region by region, what the result can still claim.
4. It measures all of this on a fault-injection test bed before any number becomes a default.

When a simple method and a clever but fragile one compete, the simple one wins.

## 1. Vision and user journey

1. **Consent.** The user creates a project and a `ConsentRecord` (ethics §2.1). Nothing runs without the `RECONSTRUCT` scope.
2. **Photos.** Each photo is hashed, and its EXIF is read: orientation, focal length, lens, date and editing software. Orientation is baked into working copies, and the originals are never modified.
3. **Landmarks.** Landmarks come from MediaPipe, through an external helper that writes JSON or an optional bundled wheel, or the user places pins by hand. Pins and JSON import always work, so the pipeline needs no downloads (ethics A4).
4. **Triage.** Each photo gets a QA card covering distance, focal evidence, lens risk, mirroring, expression, occluders, blur, resolution and retouching. Each flag states its action and reason, for example: *"selfie at ≈0.35 m: used for colour and frontal outline, not nose projection"*.
5. **Solve.** A robust multi-view bundle adjustment (BA) runs, followed by a mirror check and an observability report (for example, "focal from prior").
6. **Fit.** The CC0 template is warped in stages, then fitted to contours and silhouettes. Profiles are traced with edge snapping.
7. **Review.** The tool shows a claims ledger that marks each region *measured*, *constrained*, *prior-driven* or *unobserved*. It also shows held-out-view checks, per-camera overlays and the worst landmarks, and suggests the most useful next photo ("add a left profile").
8. **Hand-off.** The result arrives as shape keys on a stable topology, with an `artist` layer, a Multires sculpt copy, an optional gated texture and export provenance.

**What each input tier promises.** The tier is computed from the evidence; the user never picks it.

| Tier | Typical input | Promise | Label |
|---|---|---|---|
| S | ≥ 5 views over ±60–90° yaw, 1.5–3 m, tele, EXIF, scale reference | metric; depth measured; ≤ 1.5 mm face RMS (benchmarks-metrics T6 🧠) | `metric` |
| A | phone rear camera, ≥ 3 views, one at \|yaw\| ≥ 45°, EXIF | proportions; depth where coverage rules hold (§3.10); iris scale ±2–4 % (multi-view-fitting 🧠) | `iris-scaled` |
| B | camera roll: mixed devices and dates, no EXIF, expressions | frontal proportions through the solved cameras; depth from the prior unless a view exceeds 60° yaw | `proportions only` |
| C | one photo, or selfies only | blockout matched to its own camera; no claims on nose projection, ears or cranium | `blockout` |

## 2. Architecture

### 2.1 Modules

The engine imports only `numpy`, `math`, `json`, `struct`, `zlib`, `hashlib` and `tomllib`. All imports are relative, and the engine never imports `bpy` (blender digest A1). In the St column, E = exists, X = extend, N = new.

| Path | St | Purpose |
|---|---|---|
| `face3d/core/{schema,policy,config}.py` | N | Versioned formats (§2.3); consent scopes and licence taint (an AND over components; ethics A2); named, badged defaults; config SHA-256 |
| `face3d/io/exif.py` | X | Adds DateTimeOriginal, Software, DigitalZoomRatio, LensMake and SubjectDistance; reads every APP1 segment |
| `face3d/io/{heif_exif,png,image_ops,landmarks}.py` | N | HEIC EXIF from ISOBMFF boxes (no pixel decoding); stdlib PNG reader; orientation and flip-with-permutation on arrays; detector-JSON and pin adapters |
| `face3d/qa/{image,photo,expression,mirror,retouch,flags}.py` | N | Image metrics; lens and distance triage; focal ladder; intrinsics groups; date span; mirror and retouch tests; flag registry |
| `face3d/solve/pnp.py` | X | Multi-start, cheirality check, twin flag, CAM-3 hypotheses, Huber in σ units |
| `face3d/solve/{noise,observability}.py` | N | Class σ, anisotropic covariance, per-view noise scale; σ(log f), σ(log z), P, radial signature, leave-one-view-out (LOVO) |
| `face3d/solve/bundle.py` | X | Covariance blocks, visibility, jaw hinge, distance priors, soft focal tie, view cap, 4σ rejection, Schur marginals |
| `face3d/model/{registry,template_kit,prior,nuisance}.py` | N | Landmark registry (anatomy R2.1); hash-checked template kit; shape priors and gates; jaw hinge and occluder actions |
| `face3d/fit/{template,silhouette}.py` | X | Gated stages, reflection check, per-landmark RBF λ; sliding and one-sided contour residuals |
| `face3d/fit/{contour_trace,uncertainty}.py` | N | Dynamic-programming edge snap; vertex σ propagation and claims ledger |
| `face3d/geometry/rbf.py`, `mesh/laplacian.py` | X | Diagonal smoothing Λ; per-vertex stiffness |
| `face3d/texture/*`, `face3d/eval/*`, `face3d/testbed/*` | N | numpy z-buffer and blending; point-to-triangle metrics (reconstruction EV-1); scenario test bed (§5) |
| `face3d/pipeline.py`, `__main__.py` | N | Deterministic stage runner; CLI `python -m face3d {triage,solve,fit,report,testbed}` |
| `tools/{detect_mediapipe,build_template_kit,build_extension}.py` | N | External detector helper (Tasks API, `IMAGE` mode, `num_faces=2`, test-time augmentation (TTA)); hash-checked builds |
| `blender_ext/face3d_head/` | N | The extension (§4); the engine is vendored at build time |

These modules stay unchanged: `lm.py`, `triangulate.py`, `procrustes.py`, `camera.py` and `mesh/{core,sparse,reduced}.py`.

### 2.2 Data flow

```
photos → ingest (sha256, EXIF, orientation, consent gate) → LandmarkSet (+TTA spread)
→ triage (flags, tags, σ multipliers, include/exclude, focal ladder) → multi-start PnP + mirror test
→ robust BA → observability + LOVO → warp A→B→C → contours/silhouettes D
→ uncertainty → claims ledger → result.json/fit.obj/sigma.npy → Blender → artist → gated texture → export
```

Each stage is a pure function, cached under the hash of its inputs and config. Editing one pin re-runs only the stages downstream of it.

### 2.3 Data formats

Every file is JSON with a `format` name and a `version`. Arrays longer than about 1,000 values go to `.npy` files, referenced by path and SHA-256.

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

- **Scheme file.** Bundled and released by us as CC0. The scheme is always read from this file, never inferred from N (reconstruction FMT-1). Fields:
  - `n`, `lr_permutation`, `midline`
  - `classes` and `convention` (surface or semi-contour)
  - `sigma_iod` per class
  - `anatomical` name→index map
  - `verification` per entry
- **Template sidecar.** Fields:
  - `source` (upstream SHA-256, `CC0-1.0`, `commercial_ok`)
  - `units: mm`, `topology_sha256`, `order_checksum`
  - `landmarks` (kind, tri, bary, σ, provenance)
  - `scheme_maps` per detector version
  - `regions`, `mirror_map`, `contours`, `stiffness`
  - `basis` (K, SHA-256, status)

  All fields are filled by the kit builder.
- **Result file.** Fields:
  - `config_sha256`, `seed`, input hashes, `tier`
  - per camera: K, R, t, f35, z, P, σ_logf, `focal_status`, and mirror `{decision, Δ, status}`
  - per view: in-sample and LOVO RMS in % IOD, `noise_scale`, `weight_share`, `rejected_frac`, flags
  - `scale {mode, s, σ}`
  - 3D landmarks with their covariance
  - `regions [{name, status, k, σ_mm, why}]`
  - `licence {commercial_ok, components}`
  - the mesh and the per-vertex σ

### 2.4 Coordinate conventions

All conventions are defined in `core/schema.py` and have round-trip tests.

- **Image.** Coordinates are continuous, with the origin at the top-left corner of the top-left pixel; pixel (i, j) has its centre at (i + ½, j + ½), as in `camera.py`.
  - MediaPipe output: u = x·W.
  - Resize: u·W/W′. This replaces the "+0.5" form in blender digest D3.
  - Horizontal flip: u′ = W − u, with label permutation π.
- **Camera.** OpenCV convention: X_c = R·X_w + t, +y down, +z forward.
- **Head frame.** Millimetres, float64. +x is the subject's left, +y up, +z forward, and the origin is midsagittal (anatomy R1.1).
- **Blender.** A parent with `R_x(+90°)` maps (x, y, z) → (x, −z, y), with a 0.001 scale (blender A8). `to_blender_camera` already passes its tests.
- **IOD.** Outer-canthal ex–ex, the normaliser used in landmark-detection T2. Values given in interpupillary units are multiplied by 0.70 (T3 🧠). Once a camera exists, IOD_px = f·IOD_mm/z_v, because the 2D ex–ex distance halves at 60° yaw.

**Determinism.**
- Every random draw uses `default_rng(seed)`.
- Hypotheses run in a fixed order, sorts are stable, and everything is computed in float64.
- Golden tests use rtol 1e-5 (blender Q2).
- CI covers CPython 3.11 with NumPy 1.26, and 3.13 with NumPy 2.x (A4).

## 3. Algorithms

### 3.1 Input QA gates

A gate never pulls a result toward a norm (anatomy §6). Each gate takes one action: down-weight, drop a landmark class, exclude the photo from geometry, exclude it from texture, or ask the user.

| Failure | Detection and threshold | Action | Source |
|---|---|---|---|
| Orientation ignored | `exif_applied` false; view RMS > 3σ; roll ≈ ±90° | bake orientation, re-detect | blender §10 🧠 |
| EXIF stripped | no Make, Model or f35 | source-type prior (§3.3) | community R2.2 🧠 |
| Crop or zoom | size ≠ PixelXDimension; aspect not native; zoom > 1 | σ_logf 0.08–0.10; free principal point (σ 10 %) | community R2.5 🧠 |
| Front camera | LensModel contains "front" | mirror test; selfie distance prior | camera-perspective-distortion 🧠 |
| Near camera | solved z (check f·63/IPD_px): warn < 1 m, strong < 0.8 m | < 0.6 m: 2D and texture only | community §9 🧠 |
| Face-warp correction | f35 ≤ 16 mm, face beyond 60 % of the half-diagonal, or > 25° off-axis | σ × 2, or exclude from geometry | community R1.7 (warp ✅, thresholds 🧠) |
| Low resolution | face < 250 px warn, < 120 px reject; iris < 20 px | σ floor; no iris scale; no detail | community R1.4 🧠, R4 ↔️ |
| Blur, blink, clipping | Laplacian variance in the bottom 20 %; EAR < 0.2; > 2 % skin clipped | down-weight; drop lids; no photometry | community R1.4 🧠 |
| Mixed dates | date span > 18 months | split into date clusters | community §9 🧠 |
| Two faces; no consent | `num_faces=2` at score ≥ 0.6; sha256 not in the consent record | user picks a face; block | blender ML 🧠; ethics F1–F2 |

### 3.2 Noise model

For landmark i in view v, with tangent t̂ taken from neighbouring points:

Σ_iv = s_v²·m(c_i, tag_v)²·R(t̂)·diag(σ_n², σ_t²)·R(t̂)ᵀ, σ_• = max(σ̂_•(c_i)·IOD_v·√(N/N_eff), σ_tta, σ_floor).

- **σ̂ by class, in % IOD** (landmark-detection T5 🧠):

  | Class | σ |
  |---|---|
  | iris | 1.0 |
  | anchors | 1.5 |
  | lid and lip contours | 2 / 5 |
  | pronasale | 2.5 |
  | brows | 3–5 / 6 |
  | jaw | 2.5 / 10–15 |

  Paired values are normal / tangent.
- **Dense points.** N_eff is 60–100. It applies only outside a curated subset of about 100 points.
- **TTA.** σ_tta is the spread over 6–10 test-time augmentation passes (BA-2 🧠).
- **Floor.** σ_floor = max(0.5 px, k_c·face_px/256), with k_c = 0.6 for inner points, 0.4 for the iris, 1.0 for brows and 1.5 for contours (blender ML 🧠).
- **Per-view scale.** s_v² = clip(median‖Σ^{−½}r‖²/1.386, 1, 9). This is a MAD-style estimate, since 1.386 is the median of χ²₂ (deformation-fitting-math 🧠). Retouched, warped or misoriented views therefore lose weight automatically. A view is flagged when s_v > 2 (🆕).
- **View weights.** Each view gets w_v = 1/(number of views in its 15° yaw bin), and no single view may contribute more than 40 % of the total information (community R1.8 🧠).

This model replaces `sigma_px = 1.0`, which is about 13× too tight (landmark-detection 🧠), and the isotropic 0.006 × diagonal default.

### 3.3 Camera initialisation

**Focal prior.** The first matching rule sets a log-normal prior (reconstruction CAM-6, community R2.2 🧠):

| Evidence | Prior |
|---|---|
| SfM or calibration | σ_log 0.005–0.02 |
| EXIF f35, uncropped | 0.04 |
| EXIF f35, crop suspected | 0.08–0.10 |
| FocalLength and focal-plane resolution | 0.10 |
| Phone without a focal tag | 26 mm, 0.25 |
| Nothing | 50 mm, 0.6 |

The current 0.35 fallback cannot cover phone lenses.

- **Focal groups.** Photos are grouped by (Make, Model, LensModel, f35, W, H, still/video). Within a group, focal lengths are tied softly with σ 0.02 instead of being shared outright (CAM-5 🧠).
- **Distance prior (log z).**
  - Front camera: 0.35 m (σ 0.3). Rear handheld: 0.8 m. Tele: 2 m (σ 0.4). Source: CAM-6 🧠, reading σ as log-σ.
  - Unknown: 1.0 m, σ_log 0.7. Tape-measured: ±5 cm (community R2.4 🧠).
  - Hard bounds: 0.25–10 m (blender C6).
- **Multi-start PnP.**
  - f35 is tried over {13, 24, 26, 35, 50, 77, 85, 120, 135, 200} (CAM-3 🧠). The current list lacks 26, 77 and 120.
  - Each focal is started from the affine solution, a pitch-flipped pose and a yaw-mirrored pose.
  - Solutions that fail the cheirality check are rejected.
  - If two poses more than 10° apart score within 20 % of each other, the view is flagged `C-TWIN` and both enter BA (🆕).
- **Off-axis faces.** The face-centre ray is rotated onto the optical axis, the pose initialised, and the rotation undone (camera-perspective-distortion 🧠).
- **Order.** The most frontal, most complete view is solved first. Later views are initialised against the BA consensus, not the template, which reduces mean-face pull.

### 3.4 Mirrored images

With X̂ the consensus of the other views (or the template if there is only one view):

- C₀ is the robust PnP cost of the image as given.
- C₁ is the cost for u′ = (W − u_x, u_y)_π, the flipped image with labels permuted.
- Δ_v = (C₀ − C₁)/C₀.

**When the test can decide.** Let A = ½(X̂ − M·X̂_π) be the asymmetric part of the shape, and g = Σ‖Σ^{−½}J_i A_i‖² the expected cost gap. If g < 4 (🆕), the result is `undetermined`. A near-symmetric face seen through noisy landmarks cannot be told from its mirror image, and the tool says so.

**Decision.** Δ_v > 0.2 marks the view as mirrored (community R1.6 🧠). The flip is automatic, and logged, if the photo came from a front camera or the other views agree. Otherwise the tool shows both orientations and asks the user, suggesting they check the hair parting or a mole (likeness-mistakes 🧠).

If every view is mirrored, as in a set of selfies, the geometry cannot detect it. The project is marked `mirror: unverifiable`, and claims that depend on asymmetry are flagged.

### 3.5 Robust bundle adjustment

E = Σ_v w_v Σ_i ρ_H(‖Σ_iv^{−½}(π_v(X_i + J_i(θ_v)) − u_iv)‖; δ = 2) + Σ_v E_contour,v
  + Σ_g ((log f_g − μ_g)/σ_g)² + Σ_{v∈g} ((log f_v − log f_g)/0.02)² + Σ_v ((log z_v − μ_z)/σ_z)²
  + E_shape(X) + Σ_pairs ‖Σ_sym^{−½}(X_l − M·X_r)‖² + Σ_mid (x_i/σ_mid,i)² + E_scale + E_pins.

- **Robust loss.** Huber with δ = 2σ, in σ units. This replaces the 3 px threshold in PnP and the 3σ threshold in BA. After convergence, residuals beyond 4σ are dropped and the problem is re-solved. A view that loses more than 15 % of its points is flagged (BA-5 🧠).
- **Visibility.** Weight is 0 at n·(−v) < cos 80° and rises to 1 at cos 60°. Far-side oval points are dropped when |yaw| > 25° (BA-3 🧠).
- **Symmetry and midline σ (mm)** (anatomy R4.2 🧠):

  | Point | σ |
  |---|---|
  | canthi | 0.7–1.0 |
  | brows | 1.5 |
  | alae | 1.0–1.5 |
  | cheilia | 1.5–2.0 |
  | gonia | 2.5–3 |
  | ears | 3–4 |
  | midline n | 0.75–1.0 |
  | midline prn, sn | 1.5–2.0 |
  | midline pg, me | 2–3 |
- **Covariance.** Computed by Schur complement once N ≥ 100. Each landmark reports its prior share p_i = σ²_post/σ²_prior. *Likeness mode* widens the prior until p_i ≤ 0.2 wherever two or more solved views see the point (anatomy R1.4 🧠).
- **SfM cameras.** Known cameras go through triangulation, then Umeyama, then a 3D shape solve. Landmarks never move SfM cameras (BA-12 🧠).

### 3.6 Expressions, occluders and retouching

**Expression tagging.** Blendshape scores are measured as Δb above the subject's own minimum across views, not above zero (landmark-detection 🧠).

| Tag | Rule | Source |
|---|---|---|
| *Neutral* | every Δb below: jawOpen 0.08, mouthSmile 0.15, eyeBlink 0.35, browInnerUp 0.2 | landmark-detection 🧠 |
| *Expressive* | any Δb above: smile 0.25; squint, eyeWide or brow 0.3; blink 0.4 | anatomy §6 🧠 |
| *Mild* | anything in between | — |

- **Without blendshape scores:**
  - lip gap / ch–ch > 0.04 means parted lips; sto and li are dropped (anatomy §6 🧠);
  - mouth width > 1.08× the median across views means a smile (🆕).
- **Retagging.** Tags are re-estimated from residuals for up to three rounds (BA-9 🧠).
- **σ multipliers m** (expression-neutralization 🧠):

  | Point class | Neutral | Mild | Expressive |
  |---|---|---|---|
  | rigid | 1 | 1 | 1–1.5 |
  | semi-mobile | 1 | 1.5–2 | 2–3 |
  | mobile | 1 | 3 | dropped |
  | jaw-dependent | 1 | 1 if θ fitted, else 3 | 1 if θ fitted, else dropped |

**Jaw hinge.** This needs no expression data. Jaw points move as X_i(θ) = c + R_axis(θ)(X_i − c). The axis runs through the template condyles, about 10–13 mm anterior to tragion (BA-1 🧠). The prior is θ ~ N(1.5°, 1°) on neutral views, bounded to [0, 30°] (anatomy §4 🧠).

**Expression basis ψ (opt-in).** Only licence-clean adapters are allowed, such as FLAME 2023 Open. The neutral views anchor it: mean ψ ≈ 0, σ 0.1 (BA-9 🧠). If no view is neutral, mouth and lid measurements finer than 1 mm are suppressed.

**Occluder tags.** The user sets these with one click per photo. The default path has no licence-clean detector for beards or glasses.

| Tag | Effect | Source |
|---|---|---|
| Glasses | eye-region σ × 2; no iris scale; lid points under the frame dropped | anatomy R3.4 🧠 |
| Beard | pg, gn, me and jaw points dropped; the beard outline becomes a one-sided bound; jaw marked *prior-driven* unless a shaven photo exists | reference-photography-protocol, community R5.4 🧠 |
| Hair | ears and temples get weight 0; no silhouette above the trichion | blender S3 🧠 |
| Makeup | lip and brow borders σ × 2 | artstation-likeness 🧠 |

A consistency test checks the glasses tag. Lenses magnify by about 1–1.5 % per dioptre (anatomy R3.4 🧠), so a view whose iris diameter relative to en–ex is more than 3 % off the median of glasses-free views is flagged (🆕).

**Retouching and beauty filters.** Three independent tests, each compared against the other views:

1. **EXIF `Software`** matches a list of known editors (🆕).
2. **Skin-smoothness index.** SSI_v = band energy of a cheek patch ÷ band energy of the brow and iris, measured at matched mm/px. The view is flagged when SSI_v < 0.5× the set median (🆕).
3. **Residual signature.** Whitened residuals are regressed on two fixed patterns: eye-radial outward (eye enlargement) and jaw-normal inward (jaw slimming). The view is flagged when t > 3.

A flagged view gets σ × 2–3 and is excluded from texture (artstation-likeness ↔️; tests 🆕). These tests compare views, so a filter on the only photo cannot be detected, and the ledger says so.

**Non-pinhole processing.**
- A diagnostic radial distortion k₁ (prior σ 0.02) is fitted. On a phone JPEG, |k₁/σ| > 3 means "non-pinhole processing suspected" (CAM-1 🧠).
- If the radial residual's slope against ρ_i·δ_i implies more than 5 % magnification error, the distance or focal length is wrong (community R2.8 🧠).

### 3.7 Licence-clean shape prior

No permissive large-population head model is confirmed to exist (reconstruction §12), so the prior is built in three layers:

1. **Baseline.** An anisotropic Gaussian per landmark, at 1.0–1.5× the population SD, with 8 mm as the fallback (anatomy R4.1 🧠). Ratio priors are used only as diagnostics.
2. **Experimental.** X = μ + B·c with c ~ N(0, I). B is a mass-weighted SVD of the CC0 MPFB2 face targets, with K = 40–80. Its variances are scaled by an "anthropometric morphable model": 2,000–5,000 sampled heads matched to published norms, keeping 95–99 % of the variance (open-template-head-kit 🧠). This layer stays off until it lowers held-out error and keeps coverage (§5.3).
3. **Opt-in.** FLAME 2023 Open, loaded from a user-supplied path with a SHA-256 pin and attribution (CC-BY-4.0; contents unverified 📄). Any other FLAME version, or BFM, sets `commercial_ok=false` (LIC-1).

**Gates.**
- ‖c‖² > χ²_K(99.9 %), or any |c_i| > 3: the shape is flagged implausible (MM-5 🧠).
- ‖c‖² < K − 2√(2K): the fit is flagged as "pulled toward average" (community R5.8 🧠).

**Data is never fabricated.**
- Template landmarks are clicked by two annotators in Blender and kept only if they agree within 1 mm (🆕).
- MediaPipe index maps come from detector-semantics calibration: render the template from 20–50 cameras, run the detector, and store the mean landing barycentric for each index (landmark-detection 🧠).
- Both datasets are built offline with provenance. CI checks only hashes, schemas, that the L/R permutation is an involution, and that midline points map to themselves.

### 3.8 Contours, silhouettes, profiles and hair

**Edge snap.** The input is a coarse polyline: at least 5 clicks, or the detector's face-oval points. Each of M stations may move by an offset k ∈ [−L, L] along its normal, with L = 3 % IOD. The snap minimises

C = Σ −g_j(k_j) + λΣ|k_j − k_{j−1}|,

where g is gradient magnitude after a 1 px Gaussian and λ = 0.2·median g (🆕). Viterbi solves this in O(M·L²). The result is deterministic and uses no learned weights. Each point gets σ_n = max(1 px, 1/√curvature). Segment Anything (SAM, Apache-2.0) is optional and runs only in the external helper.

**Sliding residuals.** Each occluding-contour vertex is matched to its nearest outline segment, giving r = n̂·(p_j − q)/σ_n. Matches are recomputed every iteration (BA-4, blender S1 🧠). The existing outline-to-vertex direction is kept, with 10 % trimming, and the fixed 60 px gate becomes 5 % IOD (🆕).

**Hair, beard and hat masks.** These constrain from one side only:

r = max(0, d_mask + m)/σ, with m = 0–3 mm (community R5.4 🧠) and weight 10× that of skin (cranium-under-hair 🧠).

The scalp must stay at least 2 mm inside the hair hull (blender W7 🧠). Cranium σ follows visual-hull overshoot: 7.8 mm with 4 views around the head, 1.9 mm with 8 (cranium-under-hair, arithmetic).

**Profiles.** For |yaw| > 60–70°, detector output is discarded (landmark-detection 🧠). User pins on g, n, prn, sn, ls, li and pg are used instead, with σ = 1 % IOD (blender S4 🧠).

**Acceptance.**
- Profile error ≤ 1–1.5 mm at the nose tip and chin (SIL-3 🧠).
- Contour error ≤ 1 % of face height (S5 🧠).
- If interior points fit but the contours do not, report "f and z wrong", not a shape error.

### 3.9 Template warp

| Stage | Operation | Advance when |
|---|---|---|
| A | Umeyama, proper and reflected. If the reflected RMS is below 0.5× the proper RMS, flag "mirrored source" (never auto-flip). A 7-landmark RMS above 10 mm means the axes are wrong (blender W2 🧠). | always |
| B | RBF with φ = r, solving (Φ − Λ)w + Pa = y with Λ = diag(α·σ_i²), α = 10⁻² (MM-8 🧠; the sign is already fixed in `rbf.py`) | landmarks < 2–3 % IOD (community R5.2 🧠) |
| C | Bilaplacian with per-vertex stiffness (lid margins 3.0, lips 0.3, forehead 0.5, ligament strips 3–5; anatomy R5.9 🧠); offsets capped at 3–5 mm unless ≥ 2 views agree (MM-10 🧠) | RMS gain < 1 % per iteration |
| D | Silhouettes via `ReducedDeformer`; no landmark may move > 0.5 mm | contour ≤ 1 % of face height |

**Gates on every stage.**
- det J > 0.2, with no flipped triangles (MM-11 🧠).
- Lid–globe gap within 0–0.3 mm (blender §4 🧠).
- Mirror RMSD between 0.3 and 1.5 mm (anatomy §6 🧠).

Targets are never symmetrised. Detail is off by default. It is allowed only from neutral, unfiltered views at ≤ 0.08 mm/px where at least 2 views agree; otherwise it is labelled `synthetic` (anatomy R5.11 🧠).

### 3.10 Uncertainty and the claims ledger

**Propagation.** Stages B and C are linear in their targets: V = V₀ + A(X − X₀). Unit solves give A, so

Cov(V_j) = Σ_ab A_ja A_jb Cov(X_a, X_b) + σ²_res·I.

The residual σ_res depends on the region: lids 1–1.5, nose 2–3, cheeks 2.5–4, ears 3–5, scalp 3–6, neck 5–10 mm (open-template-head-kit 🧠). A finite-difference test checks A.

**Reported σ.** σ_rep² = σ²_post·max(1, κ²) + σ²_bias, where:
- κ is the LOVO ratio of observed to predicted error;
- σ_bias is 1–3 mm per landmark class until a semantics map exists, because detector bias does not average away (reconstruction principle 5 🧠).

The raw Hessian σ is never shown on its own.

**Region status.** With k = 1 − σ²_post/σ²_prior:

| Status | Rule |
|---|---|
| *measured* | k ≥ 0.8 (anatomy §6 🧠) and the coverage rules below are met |
| *constrained* | k from 0.5 to 0.8 |
| *prior-driven* | k < 0.5 (🆕) |
| *unobserved* | no view sees the region |

**Coverage rules.**
- Depth needs at least 2 views 30° or more apart (blender C7 🧠).
- Nose and chin projection need a front view plus one at |yaw| ≥ 60°.
- The jaw underside needs a low view (community R5.9 🧠).
- Ears need |yaw| ≥ 30° and pitch fixed by at least 2 views (R3.3 🧠).

**Focal length** is estimated only when σ(log f) < 0.10 (blender C2 🧠). If σ exceeds 0.8× the prior σ, the result reads "focal from prior" (CAM-7).

**Scale** is reported as *measured* (a caliper overrides everything; anatomy R3.4), *iris*, *IPD prior* or *proportions only*. References that disagree by more than 1 % are flagged (BA-10 🧠).

**Next-best photo.** The tool simulates candidate views on a 15° grid, adds each to the Hessian, and recommends the pose that most reduces σ over prior-driven regions, weighted by the benchmarks-metrics T6 region weights (🧠).

### 3.11 Texture projection

Texture projection runs only when all of these hold:
- median reprojection error ≤ 1.5 px and maximum ≤ 3 px (blender T2 🧠);
- the `TEXTURE` consent scope is granted;
- `rights_basis` is not `unknown` (ethics §3).

The method:
- numpy z-buffer with tolerance max(1 mm, 2σ_geom);
- view weight w = vis·cos²θ·footprint·edge, fading out between 60° and 75°;
- linear-RGB gains with log-σ 0.3 under auto exposure;
- two-band blend split at 3 mm;
- 2048 px maps for phone sources (TEX-1…7 🧠).

Some views never feed the albedo: filtered, retouched, warped or clipped views, and views from other date clusters. Texture is never mirrored. Without a colour chart, the output is labelled "absolute albedo unknown".

## 4. Blender add-on

**Package.** `blender_ext/face3d_head/` contains:
- `blender_manifest.toml`;
- `__init__.py`, with `compat.py` probes that finish in under 100 ms;
- `bridge.py`, the only module that converts between bpy and numpy;
- `ops_*.py`, `ui_panels.py`, `overlays.py`, `jobs.py`, `keys.py`;
- the vendored `face3d/`;
- CC0 `assets/template/`, `LICENSE` and `NOTICE`.

| Operator | Does | Runs |
|---|---|---|
| `face3d.project_new`, `face3d.photos_add` | ConsentRecord; hash, EXIF, orientation-baked copies, GPS stripped (ethics F12) | main |
| `face3d.landmarks_import`, `face3d.detect` | Import JSON, or run the helper or wheel | job |
| `face3d.pin_edit`, `face3d.trace_contour` | Modal pins in the photo camera (σ from zoom); polyline, then edge snap | modal |
| `face3d.triage`, `face3d.solve`, `face3d.fit` | §3.1–3.10 | job |
| `face3d.apply_result` | Cameras, keys, attributes; refused if the topology hash differs or the object is in Edit or Sculpt Mode (blender K1/K4) | main, UNDO |
| `face3d.bake_for_sculpt` | Duplicate, bake the key mix, clear keys, add Multires at level 2–3 (K5, SK-3 🧠) | main, UNDO |
| `face3d.project_texture`, `face3d.review_sheet`, `face3d.prepare_sharing`, `face3d.export` | §3.11, §5.5; purge leftovers (ethics F9); export with provenance and consent gates | job / main |

**Panels** (Sidebar › *Face3D*):
- *Project & Consent*.
- *Photos*: a UIList with QA badges, tags, include/exclude and mirror state.
- *Solve*: tier, focal status, z, P.
- *Fit*: stages and gates.
- *Review*: ledger, LOVO, worst landmarks, next-best photo.
- *Export*: blocking reasons.

**Overlays** use `gpu` draw handlers in each photo's camera: σ ellipses, residual arrows (×5), rejected points in red, the traced outline against the projected silhouette, and a flipped thumbnail for the mirror prompt. In 3D, the `face3d_sigma_mm` and `face3d_status` attributes colour the viewport, and region face sets drive masks.

**Undo.** Engine state lives in hashed sidecars outside the undo stack. Objects carry a `face3d_uuid` and are re-fetched by it after an undo. A job records the topology hash of its target and refuses to apply if the hash has changed.

**Jobs.** The add-on writes JSON and `.npy` files under `extension_path_user`, then runs `[sys.executable, "-I", launcher.py, job_dir]`. A timer polls every 0.1 s with at most 20 ms of work per tick (blender A5 🧠). Cancel kills the process, so a crash never loses sculpt work. Under `bpy.app.background`, jobs run synchronously.

**Shape keys** (blender K2/K3 🧠):

| Key | Contents |
|---|---|
| `Basis` | Template mean |
| `F3D_stageB`, `F3D_stageD` | Diagnostics, set to 0 |
| `F3D_ID_v<n>` | Likeness: `from_mix=False`, `slider_max` 1.5 |
| `artist` | Artist edits, kept as a Δ across refits |

Expression keys are created only with `RIG_ANIMATE` consent (ethics F4). Shape keys are never applied in place, and the mesh is never remeshed.

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
- No wheels and no `network` permission.
- CC0 assets only (blender L1).
- Engine files carry MIT SPDX headers inside the GPL-3.0-or-later package (ethics A1).
- `blender_version_min` is set to the oldest version line CI tests (Q3).

**GitHub build.** Adds per-platform MediaPipe wheels and a NOTICE file. Whether this build complies with the extensions platform rules is contested (↔️).

**Detector helper.** `tools/detect_mediapipe.py` runs in any Python install, so the lag in cp311 → cp313 wheels does not matter (blender-python-ml-deps 🧠).

## 5. Validation and QA

### 5.1 Test pyramid

1. **Unit and oracle tests.**
   - Jacobians match numeric derivatives.
   - Noiseless solves reach RMS < 10⁻⁶.
   - The camera↔Blender round trip holds to 10⁻⁶·s, and the OBJ round trip to < 2 µm (blender Q1/Q2 🧠).
   - Schemas and policy tables are checked.
   - Every QA gate is tested on synthetic arrays: a blurred checker, a clipped ramp, smoothed noise.
2. **Scenario test bed** (`face3d/testbed`, seeded). Each scenario combines a subject, a protocol, a detector model and a set of faults.
   - **Subjects:** `random_subject` with 0.8 mm RMS asymmetry (facial-asymmetry 📄).
   - **Protocols:** studio ring, rear phone, selfie, camera-roll mix.
   - **Detector model:** class σ, a 1–3 mm per-index bias field shared across views (reconstruction principle 5 🧠), 5 % outliers and TTA spread.
   - **Images:** a numpy rasteriser draws masks and procedural images for the contour and QA tests.
3. **Bridge tests.**
   - Pure functions: axis and unit mapping, the key planner, the zip builder.
   - A `tomllib` manifest lint: licence, tagline ≤ 64 characters, no numpy wheel, no network.
   - A headless `blender -b --factory-startup --python-exit-code 1` script, for CI elsewhere.

### 5.2 Fault-injection matrix

All thresholds here are 🆕. M1 first records the current engine's numbers as a baseline.

| Fault | Must raise | Required | Degradation bound |
|---|---|---|---|
| 1 mirrored view of ≥ 3 | `Q-MIRROR` | TPR ≥ 0.95 at ≥ 0.8 mm asymmetry; FPR ≤ 0.02; `undetermined` on symmetric faces | shape ≤ 1.1× clean |
| Orientation not baked | `Q-ORIENT` | TPR ≥ 0.99 | — |
| EXIF ±30 % crop, or missing | `C-FOCAL-PRIOR` if unobservable | focal error < 5 % when views span ≥ 60° (community R8.4 🧠) | shape ≤ 1.2× clean |
| Selfies at 0.35 m | `Q-SELFIE`, tier ≤ B | z within 15 % | nose-width error ≥ 30 % below the ρ = 0 fit |
| Jaw open 5–15°, smile | expressive tag | TPR ≥ 0.9 | rigid regions ≤ 1.1× clean |
| Beauty warp (eyes +6 %, jaw −4 %) | `Q-RETOUCH` | TPR ≥ 0.8 with ≥ 3 clean views | identity bias ≤ 0.5 mm |
| Off-axis wide-angle warp | gate or k₁ test | TPR ≥ 0.8 | — |
| Glasses, beard, hair | tag actions | jaw *prior-driven* under a beard | scalp inside the hull |
| Face 150 px wide | `Q-SMALL` | — | coverage holds |

### 5.3 Honesty metrics

- **Interval coverage.** For *measured* regions, 0.90–0.99 of vertices must satisfy |error| ≤ 1.96·σ_rep (🆕).
- **False confidence.** At most 5 % of *measured* regions may exceed 2× the T6 RMS target (🆕).
- **False alarms.** At most 1 spurious flag per 10 clean photos (🆕).
- **Promotion rule.** A new prior or default becomes the default only if held-out error drops and coverage holds.

Shape error is measured with `face3d/eval`:
- exact point-to-triangle distance;
- NoW-style alignment and landmark-only alignment;
- median, p95, F@1/2 mm, per-region bias, scale error and configuration RMS (EV-1/2 🧠).

### 5.4 Real-data bed (outside CI)

- **Sitters.** Start with 1–3 consenting sitters (benchmarks-metrics 🧠) and grow to about 10, spread across age, skin tone, beards, glasses and hair.
- **Per sitter:**
  - a scan, plus a repeat scan that sets the noise floor;
  - a protocol ring;
  - a rear-phone set, a selfie set and a dated camera-roll set.
- **Data handling.** Retention follows ethics §4. Only aggregate results are committed, with a leakage guard.
- **What it calibrates:** every 🧠 and 🆕 σ and gate, the detector bias and semantics map, and the six-face lineup (target ≥ 80 %).

### 5.5 What the artist sees

- **Per-camera sheets** (community R8.1 🧠): the photo, a clay render, a 50 % overlay, a difference image, the silhouette chamfer, and flipped, blurred and 64 px versions.
- **Worst landmarks first**, in % IOD.
- **Leave-one-view-out (LOVO) check:** a view is flagged when its held-out error exceeds 2× its in-sample error (reconstruction principle 15 🧠).
- **Caliper sheet**, flagging any difference over 2 mm.
- **Canon z-scores**, described in art vocabulary.
- **Likeness lint.** It flags only |model − photo| > 2σ_photo and never pulls a feature toward the mean (community R8.2 🧠).
- **"Over-symmetric" warning** when mirror RMSD is below 0.3 mm.
- **Approval renders** from about 1 m and from the sitter's favourite photo camera (camera-perspective-distortion ↔️).

## 6. Milestones

Each milestone can ship on its own and is tested here on synthetic data.

- **M1 – Test bed first.** Builds `face3d/eval`, `face3d/testbed`, the scorecard and a smoke suite. *Accept:*
  - point-to-triangle distances match brute force to 1e-9;
  - a known similarity transform is recovered;
  - the current engine's baseline scorecard is committed;
  - the smoke suite runs in ≤ 90 s.
- **M2 – Ingest and QA.** EXIF, HEIF EXIF and PNG reading; orientation; schemas; policy gates; the §3.1 gates; the focal ladder; the `triage` CLI. *Accept:*
  - byte-fixture golden tests pass;
  - each gate fires on its own fixture and stays silent on clean ones;
  - runs without consent are refused (ethics F3);
  - output is deterministic.
- **M3 – Robust cameras and BA.** §3.2–3.5, observability and LOVO. *Accept:*
  - z sweeps (0.25–5 m) and f35 sweeps (13–200 mm) meet the §5.2 camera, mirror and orientation rows;
  - unobservable focal lengths are reported;
  - existing tests pass with the updated defaults.
- **M4 – Nuisances.** Expression tags, the jaw hinge, the ψ adapter interface, occluders, retouch and warp tests, date clusters. *Accept:* the matching §5.2 rows.
- **M5 – Template kit, warp and uncertainty.** CI uses a procedural stand-in head; the real CC0 kit is built offline with recorded hashes. *Accept:*
  - the propagation check against finite differences passes;
  - smoke-suite coverage lands in 0.90–0.99;
  - the experimental basis stays off unless it wins.
- **M6 – Contours.** *Accept:*
  - the tracer lands within 1 px of rendered mask edges;
  - profile error ≤ 1.5 mm at the nose tip and chin;
  - no scalp vertex sits outside the hair hull.
- **M7 – Blender MVP.** *Accept:*
  - the bridge and manifest lints pass;
  - the zip contains no wheels and no non-CC0 assets;
  - headless scripts exist for the 4.5 and 5.2 LTS lines.
- **M8 – Helper, texture and review.** The JSON contract is tested against a fake backend. *Accept:*
  - gains are recovered within 2 % (TEX-8 🧠);
  - no colour lands on occluded texels;
  - filtered views are excluded.
- **M9 – Calibration release.** The real-data bed (§5.4) moves 🧠 and 🆕 values to measured ones. Only the tooling is tested in CI.

## 7. Risks and deliberate omissions

**Risks**
- **No proven licence-clean statistical shape model.** The baseline prior is weak in depth. Coverage rules and next-best-photo prompts push the user toward profile views rather than leaning on the prior.
- **About 70 % of the cited values are 🧠, and the 🆕 gates are our own.** All of them are labelled provisional until M9.
- **Synthetic detector errors do not match MediaPipe's real ones.** The M9 detector-semantics calibration addresses this.
- **Some faults cannot be detected.** These include mirroring on near-symmetric faces or all-selfie sets, and a filter on the only photo. We report `undetermined` rather than guess.
- **Packaging questions are open:**
  - cp313 MediaPipe wheels;
  - whether the store accepts bundled models (C7/C8);
  - HEIC support in Blender;
  - attribute names in Blender 5.x.

  The helper and manual pins keep every stage usable in the meantime.
- **The dense Hessian scales only to about 150 landmarks × 12 views.** Beyond that, use the Schur complement (M3).
- **Over-flagging.** Alarm fatigue is a real risk, so it is measured (§5.3).

**Left out of the default path, on purpose**
- **Monocular depth, generative fill, Gaussian avatars and photometric shape terms.** None of these are measurements (reconstruction principles 12–14). Each may return later as an opt-in, gated by the test bed.
- **Automatic beard, glasses and hair segmentation.** Users tag these instead, with an optional SAM helper.
- **Identity embeddings.** For evaluation only, and opt-in. The weights are mostly non-commercial (NC), and embeddings are never stored.
- **"Un-filtering" retouched photos.** We only down-weight them.
- **Phone video depth, ear detail beyond silhouette plus prior, hair grooming, teeth and fine lid detail.** These wait for their gap-topic notes.
- **Symmetrising, anonymising, 1:N matching and URL import.** These are never built (ethics F17, F18, A5).
