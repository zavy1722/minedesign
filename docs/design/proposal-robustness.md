# Proposal: a robustness-first photo-to-head engine

*Angle: robustness first, for the photos people actually take. Written 2026-11-20 against `face3d/` at commit 887c5e5 (42 tests passing) and `research/_raw/requirements_*.md`.*

**Citations** name the topic note and its badge: ✅ verified, 📄 single-sourced, 🧠 unverified expert knowledge, ↔️ contested. **🆕** marks a value this proposal introduces; it has no source and must be calibrated on the test bed (§5). Gap-topic notes were not in the repo yet, so `open-template-head-kit` and `cranium-under-hair` refer to their draft tables in `research/data/`. Every 🧠 or 🆕 number ships as a named config value carrying its badge.

## 0. Thesis

Accuracy on good photos is the easy part. The tool succeeds or fails on mirrored front-camera selfies, WhatsApp copies with no EXIF, a beard over the jaw, and a smile in the only three-quarter view. So the engine:

1. detects each failure mode with a simple test that can be checked on its own;
2. degrades gracefully, down-weighting or excluding bad evidence instead of fitting through it;
3. states what the result can still claim, region by region;
4. measures all of this on a fault-injection test bed before any number becomes a default.

When a simple, verifiable method competes with a clever, fragile one, the simple one wins.

## 1. Vision and user journey

1. **Project and consent.** A `ConsentRecord` is created (ethics §2.1). Nothing runs without the `RECONSTRUCT` scope.
2. **Add photos.** Each photo is hashed and its EXIF read: orientation, focal length, lens, date and editing software. Orientation is baked into working copies; originals stay untouched.
3. **Landmarks.** These come from MediaPipe, through an external helper that writes JSON or an optional wheel, or from manual pins. Pins and JSON import always work, so the whole pipeline runs without downloading anything (ethics A4).
4. **Triage.** Each photo gets a QA card: distance, focal evidence, lens risk, mirror status, expression, occluders, blur, resolution and a retouch flag. Every flag names its action and the reason, for example *"selfie at ≈0.35 m: used for colour and frontal outline, not nose projection"*.
5. **Solve.** Robust multi-view bundle adjustment (BA) runs, then a mirror check and an observability report, for example "focal length came from the prior".
6. **Fit.** A CC0 template is warped in stages, then contours and silhouettes are fitted. Profiles are traced with edge snapping.
7. **Review.** The artist sees a claims ledger (each region *measured*, *constrained*, *prior-driven* or *unobserved*), held-out-view checks, per-camera overlay sheets and the worst landmarks first. The tool also names the most useful next photo, for example "add a left profile".
8. **Hand-off.** The fit becomes shape keys on stable topology, plus an `artist` layer, a Multires sculpt copy, optional gated texture and provenance on export.

**Promise by input tier.** The engine computes the tier from the evidence; the user does not pick it.

| Tier | Typical input | Promise | Label |
|---|---|---|---|
| S | ≥ 5 views over ±60–90° yaw, 1.5–3 m, tele lens, EXIF, scale reference | Metric; depth measured; ≤ 1.5 mm RMS on the face (benchmarks-metrics Table 6 🧠) | `metric` |
| A | Rear phone camera, ≥ 3 views, one at \|yaw\| ≥ 45°, EXIF intact | Proportions; depth measured where coverage rules hold (§3.10); scale from the iris ±2–4 % (multi-view-fitting 🧠) | `iris-scaled` |
| B | Camera roll: mixed devices and dates, missing EXIF, expressions | Frontal proportions through the solved cameras; depth from the prior unless a view exceeds 60° yaw | `proportions only` |
| C | One photo, or selfies only | Blockout that matches its own camera; no claim on nose projection, ears or cranium | `blockout` |

## 2. Architecture

### 2.1 Modules

The engine imports only `numpy`, `math`, `json`, `struct`, `zlib`, `hashlib` and `tomllib`, always through relative imports, and never `bpy` (blender digest A1). Status: **E** exists, **X** extend, **N** new.

| Path | St | Purpose |
|---|---|---|
| `face3d/core/{schema,policy,config}.py` | N | Versioned formats (§2.3); consent scopes, `LicenceTag` and taint as an AND over components (ethics A2); named defaults with badge, source and config SHA-256 |
| `face3d/io/exif.py` | X | Add DateTimeOriginal 0x9003, Software 0x0131, DigitalZoomRatio 0xA404, LensMake 0xA433 and SubjectDistance 0x9206; scan every APP1 segment |
| `face3d/io/{heif_exif,png,image_ops,landmarks}.py` | N | HEIC EXIF via ISOBMFF boxes (never decodes pixels); stdlib PNG decoder; orientation baking and flip-with-permutation on arrays; detector-JSON and pin adapters |
| `face3d/qa/{image,photo,expression,mirror,retouch,flags}.py` | N | Image metrics; lens and distance triage, focal ladder, intrinsics groups, date span; expression tags; mirror test; retouch and warp tests; flag registry (code, severity, evidence, action, source) |
| `face3d/solve/pnp.py` | X | Multi-start (pitch-flip, yaw-mirror), cheirality, twin flag, CAM-3 f35 set, Huber in σ units |
| `face3d/solve/noise.py` | N | Class σ in IOD fractions; anisotropic covariance; floors; per-view noise scale |
| `face3d/solve/bundle.py` | X | Covariance blocks, visibility, jaw hinge, distance priors, soft focal tie, view cap, 4σ rejection, Schur marginals |
| `face3d/solve/observability.py` | N | σ(log f), σ(log z), P = 100 mm/z, radial signature, leave-one-view-out (LOVO) |
| `face3d/model/{registry,template_kit,prior,nuisance}.py` | N | Landmark registry (vertex, barycentric, extremal, contour; anatomy R2.1); template kit loader with hash checks; shape priors and gates; jaw hinge and occluder actions |
| `face3d/fit/template.py`, `silhouette.py` | X | Staged warp with gates, reflected-Umeyama check and per-landmark RBF λ; sliding point-to-line residuals and one-sided masks |
| `face3d/fit/{contour_trace,uncertainty}.py` | N | Dynamic-programming (DP) edge snap; vertex σ propagation; claims ledger |
| `face3d/geometry/rbf.py`, `mesh/laplacian.py` | X | Diagonal smoothing Λ; per-vertex stiffness |
| `face3d/texture/{raster,project,blend}.py` | N | numpy z-buffer, view weights, gains, two-band blend |
| `face3d/eval/*`, `face3d/testbed/*` | N | Point-to-triangle metrics and alignment (reconstruction EV-1); synthetic scenarios and fault injection (§5) |
| `face3d/pipeline.py`, `__main__.py` | N | Deterministic stage runner; CLI `python -m face3d {triage,solve,fit,report,testbed}` |
| `tools/detect_mediapipe.py`, `build_template_kit.py`, `build_extension.py` | N | External detector helper (Tasks API, `IMAGE` mode, `num_faces=2`, test-time augmentation (TTA)); reproducible, hash-checked builds |
| `blender_ext/face3d_head/` | N | Extension: manifest, bridge, operators, panels, overlays, jobs, key planner; the engine is vendored at build time |

Unchanged: `lm.py`, `triangulate.py`, `procrustes.py`, `camera.py`, `mesh/{core,sparse,reduced}.py`.

### 2.2 Data flow

```
photos → ingest (sha256, EXIF, orientation, consent gate) → LandmarkSet (+TTA spread)
→ triage (flags, tags, σ multipliers, include/exclude, focal ladder, groups)
→ camera init (multi-start PnP, mirror test) → robust BA (+jaw, priors, rejection, caps)
→ observability + LOVO → tier/scale/focal status
→ warp A→B→C (gated) → contours/silhouettes D → uncertainty → claims ledger
→ result.json + fit.obj + sigma.npy → Blender bridge → artist sculpt → gated texture → export
```

Each stage is a pure function from typed inputs to typed outputs, cached under the hash of its inputs and config. Editing one pin recomputes only the stages downstream of it.

### 2.3 Data formats

All formats are JSON with `format` and `version` fields. Arrays larger than about 1,000 numbers go to `.npy` files, referenced by path and SHA-256.

```json
{"format":"face3d.project","version":1,"seed":1234,"consent_id":"…","template":"mpfb2-hm08-head@1",
 "photos":[{"id":"p03","path":"photos/IMG_0412.HEIC","sha256":"…","rights_basis":"self_shot",
   "exif":{"f35":26,"lens_model":"…front…","datetime":"…","software":null,"orientation":6,"pixel_wh":[3024,4032]},
   "working":{"orientation_applied":true,"crop":null},
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

The **scheme file** is bundled and is our own CC0 work. It records the convention per index and never infers it from N (reconstruction FMT-1). Fields: `n`, `lr_permutation`, `midline`, `classes` (iris, anchor, lid, oval, …), `convention` (surface_3d or semi_contour), `sigma_iod` per class, an `anatomical` name→index map, and per-entry `verification`.

The **template sidecar** has these fields:
- `source` (upstream file SHA-256, `CC0-1.0`, `commercial_ok`);
- `units: mm`; `n_vertices`; `topology_sha256`; `order_checksum`;
- `landmarks` (name → kind, tri, bary, σ_mm, provenance);
- `scheme_maps` (per detector version: file, number of renders, p95 spread);
- `regions`, `mirror_map`, `midline`, `contours` (jaw, profile, hairline);
- `stiffness`;
- `basis` (kind, K, SHA-256, status).

The kit builder fills every one of these. None is typed by hand (§3.7).

The **result file** has these fields:
- `config_sha256`, `seed`, input hashes, `tier`;
- per camera: K, R, t, convention, f35, z_mm, P, σ_logf, `focal_status`, focal group, mirror `{decision, Δ, status}`;
- per view: in-sample and LOVO RMS in % IOD, `noise_scale`, `weight_share`, `rejected_frac`, tags and flags;
- `scale {mode, s, σ_rel}`;
- 3D landmarks with covariance;
- `regions [{name, status, k, σ_mm, why}]`;
- `flags`;
- `licence {commercial_ok, components}`;
- the mesh and per-vertex σ.

### 2.4 Coordinate conventions

These are fixed in `core/schema.py` and covered by round-trip tests.

- **Image coordinates** are continuous, with the origin at the top-left corner of the top-left pixel, so pixel (i, j) has its centre at (i + ½, j + ½), as in `camera.py`. MediaPipe output maps as u = x·W. Resizing maps as u·W/W′; we do not use the "+0.5" form in blender digest D3, which assumes the centre-at-integer convention. A horizontal flip is u′ = W − u together with the label permutation π.
- **Camera** follows OpenCV: X_c = R·X_w + t, with +y down and +z forward.
- **Head frame** is in millimetres, float64: +x is the subject's left, +y up, +z out of the face, with the origin on the midsagittal plane (anatomy R1.1).
- **Blender**: an `R_x(+90°)` parent maps (x, y, z) → (x, −z, y), then scales by 0.001 (blender digest A8). `to_blender_camera` (lens = f·36/W, HORIZONTAL fit, shifts divided by W) is already tested.
- **IOD** means outer-canthal distance (ex–ex), the normaliser in landmark-detection Table 2. Values quoted in interpupillary units are multiplied by 0.70 (63/90; Table 3 🧠). Per view, IOD_px = f·IOD_mm/z_v once the camera is known. The raw 2D ex–ex distance halves at 60° yaw, so it is not used.

**Determinism.**
- Every random draw uses `default_rng(seed)`.
- Hypotheses are tried in a fixed order, sorts are stable and all arithmetic is float64.
- Goldens are compared at rtol 1e-5 (blender digest Q2).
- CI runs CPython 3.11 + NumPy 1.26 and 3.13 + NumPy 2.x (A4).

## 3. Algorithms

### 3.1 Input QA gates

A gate never corrects toward a norm (anatomy §6). Each gate's action is one of: down-weight, drop a landmark class, exclude from geometry, exclude from texture, or ask the user.

| Failure | Detection and threshold | Action | Source |
|---|---|---|---|
| Orientation not applied | `exif_applied` false; view RMS > 3σ; roll ≈ ±90° | bake and re-detect | blender §10 🧠 |
| Missing or stripped EXIF | no Make, Model or f35 | source-type prior (§3.3) | community R2.2 🧠 |
| Crop or digital zoom | working size ≠ PixelXDimension; aspect not native; DigitalZoomRatio > 1 | σ_logf 0.08–0.10; principal point free, σ 10 % | community R2.5 🧠 |
| Front camera | LensModel contains "front" | mirror test; selfie distance prior | camera-perspective-distortion 🧠 |
| Near camera | solved z, checked against f·63/IPD_px: warn < 1 m, strong < 0.8 m | below 0.6 m: 2D and texture only | community §9 🧠 |
| Wide-angle face-warp correction | f35 ≤ 16 mm, face beyond 60 % of half-diagonal, or > 25° off-axis | σ × 2 or geometry-excluded | community R1.7 (warp ✅, thresholds 🧠) |
| Low resolution | face < 250 px warn, < 120 px reject; iris < 20 px | σ floor; no iris scale; no detail | community R1.4 🧠, R4 ↔️ |
| Blur, blink, clipping | Laplacian variance in bottom 20 %; eye aspect ratio < 0.2; clipped skin > 2 % | down-weight; drop lids; no photometry | community R1.4 🧠 |
| Mixed dates | DateTimeOriginal span > 18 months | date clusters | community §9 🧠 |
| Two faces; photo not consented | count at score ≥ 0.6 with `num_faces=2`; sha256 ∉ consent list | user picks; block | blender ML 🧠; ethics F1–F2 |

Expression, occluders and retouching are covered in §3.6.

### 3.2 Noise model

For landmark i in view v, with tangent t̂ from neighbouring points:

Σ_iv = s_v²·m(c_i, tag_v)²·R(t̂)·diag(σ_n², σ_t²)·R(t̂)ᵀ,  σ_• = max(σ̂_•(c_i)·IOD_v·√(N/N_eff), σ_tta, σ_floor).

- **Class σ̂ (% IOD):** iris 1.0; canthi, cheilia, labrale and subnasale 1.5; lid and lip contours 2/5 (normal/tangent); pronasale 2.5; brows 3–5/6; jaw 2.5/10–15 (landmark-detection Table 5 🧠).
- **Dense inflation:** N_eff ≈ 60–100, applied only outside the curated subset of about 100 points (🧠).
- **σ_tta:** the spread over 6–10 TTA passes (reconstruction BA-2 🧠).
- **σ_floor:** max(0.5 px, k_c·face_px/256), with k_c = 0.6 inner, 0.4 iris, 1.0 brows, 1.5 contour (blender ML 🧠).
- **Per-view scale** after the first pass: s_v² = clip(median_i ‖Σ^{−½}r‖²/1.386, 1, 9), where 1.386 is the median of χ²₂. This is a MAD-style scale (deformation-fitting-math 🧠). Retouched, warped or misoriented views therefore lose weight automatically. Flag when s_v > 2 (🆕).
- **View weight:** w_v = 1/(number of views in the same 15° yaw bin). No view may supply more than 40 % of the total information tr(JᵀΣ⁻¹J) (community R1.8 🧠).

This replaces `sigma_px = 1.0`, which is ≈13× too tight (landmark-detection 🧠), and the isotropic default of 0.006 × the face-box diagonal.

### 3.3 Camera initialisation

**Focal evidence ladder.** The first rule that matches sets the log-normal prior:

| Evidence | Prior on f |
|---|---|
| SfM import or calibration | σ_log 0.005–0.02 |
| EXIF f35, uncropped | σ_log 0.04 |
| EXIF f35, crop suspected | σ_log 0.08–0.10 |
| FocalLength and focal-plane resolution | σ_log 0.10 |
| Phone make or model, no focal | 26 mm, σ_log 0.25 |
| Nothing | 50 mm, σ_log 0.6 |

Sources: reconstruction CAM-6 and community R2.2 (🧠). The community note shows that today's 0.35 fallback cannot cover phone lenses.

- **Focal groups:** keyed on (Make, Model, LensModel, f35, W, H, still/video), with a soft tie of σ 0.02 in place of hard sharing (CAM-5 🧠).
- **Distance prior** on log z: front camera 0.35 m (σ 0.3), rear handheld 0.8 m (σ 0.4), tele 2 m (σ 0.4); CAM-6 🧠, with σ read as log-σ. Unknown: 1.0 m, σ_log 0.7. Tape-measured: ±5 cm (community R2.4 🧠). Bounds 0.25–10 m (blender C6).
- **Multi-start PnP** against the template:
  - f35 ∈ {13, 24, 26, 35, 50, 77, 85, 120, 135, 200} mm (CAM-3 🧠; today's list lacks 26, 77 and 120);
  - three starts per focal value: affine, pitch-flipped and yaw-mirrored;
  - reject any solution that fails cheirality;
  - if two poses more than 10° apart score within 20 %, flag `C-TWIN` and carry both into BA (🆕).
- **Off-axis faces:** rotate the face-centre ray onto the optical axis, initialise, then rotate back (camera-perspective-distortion 🧠).
- **Order:** start with the most frontal and most complete view. Initialise later views against the BA consensus, not the template, to reduce pull toward the mean face.

### 3.4 Mirrored images

Let X̂ be the consensus from the other views (or the template if there is only one view). Compute C₀, the best robust PnP cost for the view as given, and C₁, the same for u′ = (W − u_x, u_y) with labels permuted by π. Then Δ_v = (C₀ − C₁)/C₀.

- **Discriminability.** Let A = ½(X̂ − M·X̂_π) be the asymmetric part and g = Σ_i ‖Σ_iv^{−½} J_i A_i‖² the expected cost gap. If g < 4, return `undetermined` (🆕). A nearly symmetric face seen through noisy landmarks cannot be told from its mirror image, and the tool says so.
- **Decision.** Δ_v > 0.2 marks the view as mirrored (community R1.6 🧠). It is flipped automatically, with a log entry, if the photo is from a front camera or the other views agree. Otherwise the tool shows both orientations and asks the user to check the hair parting or a mole (likeness-mistakes 🧠).
- **When every view is mirrored** (for example a selfie-only set), geometry cannot detect it. The set is marked `mirror: unverifiable` and claims that depend on asymmetry are flagged.

### 3.5 Robust bundle adjustment

The cost has one data term per view and landmark, plus contour, camera and shape terms:

E = Σ_v w_v Σ_i ρ_H(‖Σ_iv^{−½}(π_v(X_i + J_i(θ_v)) − u_iv)‖; δ = 2)
  + Σ_v E_contour,v
  + Σ_g ((log f_g − μ_g)/σ_g)² + Σ_{v∈g} ((log f_v − log f_g)/0.02)²
  + Σ_v ((log z_v − μ_z)/σ_z)²
  + E_shape(X)
  + Σ_pairs ‖Σ_sym^{−½}(X_l − M·X_r)‖² + Σ_mid (x_i/σ_mid,i)²
  + E_scale + E_pins.

- **Robust loss:** Huber at 2σ in σ units, replacing 3 px in PnP and 3σ in BA. After convergence, drop residuals beyond 4σ and re-solve. Flag any view with more than 15 % rejected (reconstruction BA-5 🧠).
- **Visibility weight:** 0 at n·(−v) < cos 80°, rising to 1 at cos 60°. Drop far-side oval points when |yaw| > 25° (BA-3 🧠).
- **Symmetry σ per pair (mm):** canthi 0.7–1.0, brows 1.5, alae 1.0–1.5, cheilia 1.5–2.0, gonia 2.5–3, ears 3–4. **Midline σ:** n 0.75–1.0, prn/sn 1.5–2.0, pg/me 2–3 (anatomy R4.2 🧠).
- **Posterior covariance:** Schur complement over camera blocks once N ≥ 100. Each landmark also reports its prior share p_i = σ²_post/σ²_prior. *Likeness mode* widens the prior until p_i ≤ 0.2 wherever at least 2 solved views see the landmark (anatomy R1.4 🧠).
- **Fixed SfM cameras:** triangulate, Umeyama, then a 3D shape solve. Landmarks never move SfM cameras (BA-12 🧠).

### 3.6 Expressions, occluders and retouching

**Expression tags.**
- Blendshape scores are measured as Δb above the subject's own baseline (the per-channel minimum over all their views), not above zero (landmark-detection 🧠).
- *Neutral* if every Δb is below jawOpen 0.08, mouthSmile 0.15, eyeBlink 0.35 and browInnerUp 0.2 (landmark-detection 🧠).
- *Expressive* if any score exceeds the anatomy §6 limits (🧠): mouthSmile 0.25, squint, eyeWide or brow 0.3, blink 0.4.
- *Mild* otherwise.
- Without scores, geometric proxies apply: inner-lip gap / mouth width (ch–ch) > 0.04 means parted lips, so sto and li are dropped (anatomy §6 🧠); mouth width > 1.08× the median means a smile (🆕).
- Tags are refined over at most three rounds of re-tagging from residuals (BA-9 🧠).

**Multipliers m** (expression-neutralization 🧠):

| Landmark class | Neutral | Mild | Expressive |
|---|---|---|---|
| Rigid | 1 | 1 | 1–1.5 |
| Semi-mobile | 1 | 1.5–2 | 2–3 |
| Mobile | 1 | 3 | drop |
| Jaw-dependent | 1 | 1 (θ fitted) | 1 (θ fitted) |

**Jaw hinge.** The default path needs no expression data. For jaw-dependent points, X_i(θ) = c + R_axis(θ)(X_i − c), with the axis through condyles placed ≈10–13 mm anterior to tragion on the template (BA-1 🧠). The prior on θ is N(1.5°, 1°) on neutral views, bounded to [0, 30°] (anatomy §4 🧠).

A ψ expression basis is opt-in, and only through licence-clean adapters such as FLAME 2023 Open. With it, the neutral-view mean ψ is held near 0 with σ 0.1 (BA-9 🧠). If no view is neutral, mouth and lid measurements finer than 1 mm are suppressed and the reason is shown.

**Occluder tags.** The user sets these with one click. The default path has no licence-clean detector for beards or glasses.

| Tag | Action | Source |
|---|---|---|
| Glasses | Eye σ ×2; no iris scale; lid points under the frame dropped. Consistency test: iris diameter / (en–ex) more than 3 % off the median of glasses-free views (lenses magnify ≈1–1.5 % per dioptre) | anatomy R3.4 🧠; test 🆕 |
| Beard | Drop pg, gn, me and jaw points; the beard outline becomes a one-sided bound; jaw is *prior-driven* unless a shaven photo exists | reference-photography-protocol, community R5.4 🧠 |
| Hair over ears or forehead | Ear and temple weight 0; no silhouette above the trichion | community R1.4, blender S3 🧠 |
| Makeup | Lip and brow borders σ ×2 | artstation-likeness 🧠 |

**Retouching and beauty filters.** Three independent tests:
1. EXIF `Software` matches a list of known editors (🆕).
2. Skin-smoothness index SSI_v = high-band energy of a cheek patch ÷ high-band energy of the brow and iris, at matched mm/px. Flag when it falls below 0.5× the set median (🆕).
3. Regress whitened residuals on two fixed patterns: radial-outward about the eyes (eye enlargement) and inward along the jaw normal (jaw slimming). Flag when t > 3, then set σ ×2–3 and exclude the view from texture (artstation-likeness ↔️; test 🆕).

All three tests are relative to the other views. A filter on the only photo is undetectable, and the ledger says so.

**Non-pinhole warps.** A diagnostic k₁ with prior σ 0.02 is fitted. On a phone JPEG, |k₁/σ| > 3 means "non-pinhole processing suspected" (reconstruction CAM-1 🧠). A radial-residual slope on ρ_i·δ_i implying more than 5 % magnification error means the distance or focal length is wrong (community R2.8 🧠).

### 3.7 Licence-clean shape prior

No permissive, large-population statistical head model is confirmed to exist (reconstruction §12), so the default is layered:

1. **Baseline.** A per-landmark anisotropic Gaussian about the template, at 1.0–1.5× population SD, with 8 mm as the fallback (anatomy R4.1 🧠). Ratio priors are diagnostics only.
2. **Experimental.** X = μ + B·c with c ~ N(0, I). B is a mass-weighted SVD of the CC0 MPFB2 face targets (K 40–80). Its variances come from an "anthropometric morphable model": 2,000–5,000 sampled heads matched to published norms, keeping 95–99 % of the variance (open-template-head-kit 🧠). It stays off until it lowers held-out error and keeps coverage (§5.3).
3. **Opt-in.** FLAME 2023 Open, loaded from a user path with a SHA-256 pin and attribution (CC-BY-4.0; contents unverified 📄). Other FLAME versions and BFM set `commercial_ok=false` (LIC-1).

**Gates.**
- ‖c‖² > χ²_K at 99.9 %, or any |c_i| > 3: implausible (MM-5 🧠).
- ‖c‖² < K − 2√(2K): "pulled toward average" (community R5.8 🧠).

**Nothing is fabricated.**
- Template landmarks are clicked in Blender by two annotators, who must agree within 1 mm (🆕).
- MediaPipe maps come from detector-semantics calibration: render the template from 20–50 cameras, detect, and store mean barycentric landing points (landmark-detection 🧠).
- Both are built offline with provenance. CI checks hashes, schemas, that the L/R permutation is an involution, and midline fixity.

### 3.8 Contours, silhouettes, profiles and hair

**Edge snapping.** Start from a coarse polyline (at least 5 clicks, or detector oval points) with M stations, each with an offset k ∈ [−L, L] along the normal, L = 3 % IOD.
- Minimise C = Σ_j −g_j(k_j) + λ·Σ_j |k_j − k_{j−1}|, where g is Gaussian-smoothed gradient magnitude (σ 1 px) and λ = 0.2·median g (🆕).
- Solve by Viterbi dynamic programming in O(M·L²): deterministic, with no learned weights.
- σ_n per sample is max(1 px, 1/√(cost curvature)).
- Segment Anything (Apache-2.0) is optional and runs only in the helper.

**Sliding residuals.** r_j = n̂_seg·(p_j − q)/σ_n, from each projected occluding-contour vertex to its nearest outline segment, re-associated every iteration (BA-4, blender S1 🧠). These are combined with the existing outline-to-vertex terms in both directions, 10 % trimming, and a trim distance of 5 % IOD in place of the fixed 60 px (🆕).

**One-sided masks** (hair, beard, hat). r_j = max(0, d_mask(p_j) + m)/σ with m = 0–3 mm (community R5.4 🧠) and weight 10× skin (cranium-under-hair 🧠). The scalp stays at least 2 mm inside the hair hull (blender W7 🧠). Cranium σ comes from visual-hull overshoot: 7.8 mm with 4 views around the head, 1.9 mm with 8 (cranium-under-hair, arithmetic).

**Profile routing.** For |yaw| > 60–70°, detector output is discarded (landmark-detection 🧠). User pins on g, n, prn, sn, ls, li and pg are allowed at σ 1 % IOD (blender S4 🧠).

**Acceptance.**
- Profile error ≤ 1–1.5 mm at the nose tip and chin (SIL-3 🧠).
- Contour within ≤ 1 % of face height (blender S5 🧠).
- Interior fits but contours fail → report "f and z wrong", not a shape error.

### 3.9 Template warp

| Stage | Operation | Advance when |
|---|---|---|
| A | Umeyama, proper and reflected. If reflected RMS < 0.5× proper, flag "mirrored source" and never auto-flip. If the 7-landmark RMS > 10 mm, the axes are wrong (blender W2 🧠). | always |
| B | RBF with φ = r: (Φ − Λ)w + Pa = y, Λ = diag(α·σ_i²), α = 10⁻² normalised (MM-8 🧠; the sign is already fixed in `rbf.py`) | landmarks < 2–3 % IOD (community R5.2 🧠) |
| C | Bilaplacian with per-vertex stiffness (lid margins 3.0, lips 0.3, forehead 0.5, ligaments 3–5; anatomy R5.9 🧠); weight 10³; offsets capped at 3–5 mm unless ≥ 2 views agree (MM-10 🧠) | RMS gain < 1 % per iteration |
| D | Silhouettes via `ReducedDeformer`; no landmark moves > 0.5 mm | contour ≤ 1 % of face height |

**Gates after every stage:**
- triangle det J > 0.2 and no flips (MM-11 🧠);
- lid–globe gap within [0, 0.3] mm (blender §4 🧠);
- mirror RMSD within 0.3–1.5 mm (anatomy §6 🧠).

Targets are never symmetrised. Detail transfer is off by default; it is allowed only from neutral, unfiltered views at ≤ 0.08 mm/px where 2 or more views agree, and is otherwise labelled `synthetic` (anatomy R5.11 🧠).

### 3.10 Uncertainty and the claims ledger

- **Propagation.** Stages B and C are linear in the targets: V = V₀ + A·(X − X₀). Unit solves give A, so
  Cov(V_j) = Σ_ab A_ja A_jb Cov(X_a, X_b) + σ²_res,region·I.
  The residual σ by region: lids 1–1.5, nose 2–3, cheeks 2.5–4, ears 3–5, scalp 3–6 and neck 5–10 mm (open-template-head-kit 🧠). A finite-difference test verifies A.
- **Reported σ.** σ_rep² = σ²_post·max(1, κ²) + σ²_bias.
  - κ is the LOVO ratio of observed to predicted error.
  - σ_bias is 1–3 mm per class until a detector-semantics map exists, because detector bias does not average away (reconstruction principle 5 🧠).
  - The Hessian alone is never shown.
- **Status** with k = 1 − σ²_post/σ²_prior:
  - *measured*: k ≥ 0.8 (anatomy §6 🧠) and the coverage rules below hold;
  - *constrained*: 0.5 ≤ k < 0.8;
  - *prior-driven*: k < 0.5 (🆕);
  - *unobserved*: no view sees it.
- **Coverage rules.**
  - Depth needs 2 or more views at least 30° apart (blender C7 🧠).
  - Nose and chin projection need a front view plus one at |yaw| ≥ 60°.
  - The underside of the jaw needs a low view (community R5.9 🧠).
  - Ears need |yaw| ≥ 30° and pitch fixed by 2 or more views (community R3.3 🧠).
- **Focal length** is estimated only when σ(log f) < 0.10 (blender C2 🧠). If σ > 0.8× the prior σ, the result reads "focal from prior" (CAM-7).
- **Scale** is *measured* (a caliper overrides everything else; anatomy R3.4), *iris*, *IPD prior* or *proportions only*. Flag references that disagree by more than 1 % (BA-10 🧠).
- **Next-best photo.** Simulate a candidate view on a 15° yaw/pitch grid by adding its landmarks to the Hessian. Recommend the pose that most reduces σ in prior-driven regions, weighted by the perceptual region weights in benchmarks-metrics Table 6 (🧠).

### 3.11 Texture projection

**Gates.** Projection runs only if reprojection median ≤ 1.5 px and max ≤ 3 px (blender T2 🧠), the `TEXTURE` scope is granted and `rights_basis ≠ unknown` (ethics §3).

**Method.**
- numpy z-buffer with tolerance max(1 mm, 2σ_geom).
- Per-view weight w = vis·cos²θ·footprint·edge, fading out from 60° to 75°.
- Gains in linear RGB with log-gain σ 0.3 under auto exposure.
- Two-band blend split at 3 mm; maps 2048 px for phone photos (TEX-1…7 🧠).

**Excluded from albedo:** filtered, retouched, warped or clipped views, and other date clusters. Texture is never mirrored. Without a colour chart, the albedo is labelled "absolute albedo unknown".

## 4. Blender add-on

**Package** `blender_ext/face3d_head/` contains:
- `blender_manifest.toml`
- `__init__.py`, with `compat.py` probes that finish in under 100 ms
- `bridge.py`, the only module that converts between bpy and numpy
- `ops_*.py`, `ui_panels.py`, `overlays.py`, `jobs.py`, `keys.py`
- the vendored `face3d/`
- `assets/template/` (CC0 only), plus `LICENSE` and `NOTICE`

| Operator | Purpose | Runs |
|---|---|---|
| `face3d.project_new` | ConsentRecord form, project folder | main |
| `face3d.photos_add` | Hash, EXIF/HEIF-EXIF, orientation-baked working copies, GPS stripped (ethics F12) | main |
| `face3d.landmarks_import`, `face3d.detect` | JSON import, or the configured helper or wheel | job |
| `face3d.pin_edit`, `face3d.trace_contour` | Modal pins in the photo camera, with σ set by zoom; polyline then edge snap | modal |
| `face3d.triage`, `face3d.solve`, `face3d.fit` | §3.1–3.10 | job |
| `face3d.apply_result` | Cameras, keys and attributes. Refused on a topology-hash mismatch or in Edit or Sculpt Mode (blender K1/K4) | main, UNDO |
| `face3d.bake_for_sculpt` | Duplicate, bake the key mix, clear keys, add Multires level 2–3 (K5, SK-3 🧠) | main, UNDO |
| `face3d.project_texture`, `face3d.review_sheet`, `face3d.prepare_sharing`, `face3d.export` | Texture (§3.11) and review sheets (§5.5); purge leftovers (ethics F9); licence and consent gates with provenance | job / main |

**Panels** live in Sidebar › *Face3D*:
- Project & Consent;
- Photos: a UIList with QA badges, tag toggles, include/exclude and mirror state;
- Solve: tier, focal status, z and P;
- Fit: stages and gates;
- Review: ledger, LOVO, worst landmarks, next-best photo;
- Export: blocking reasons.

**Overlays** use `gpu` draw handlers through each photo camera: σ ellipses, residual arrows at ×5, rejected points in red, the traced outline against the projected silhouette, and a flipped thumbnail for the mirror prompt. In 3D, the `face3d_sigma_mm` and `face3d_status` attributes colour the viewport, and region face sets drive masks.

**Undo.** Engine state lives in hashed sidecars, not on the undo stack. Objects carry a `face3d_uuid` property and are re-fetched by it after undo. Jobs record the topology hash of their target and refuse to apply if it has changed.

**Background jobs.**
- `jobs.py` writes JSON and `.npy` files under `extension_path_user`, then spawns `[sys.executable, "-I", launcher.py, job_dir]`.
- A timer polls every 0.1 s and does at most 20 ms of work per tick (blender A5 🧠).
- Cancel kills the process, so a worker crash cannot lose sculpt work.
- When `bpy.app.background` is set, jobs run synchronously.

**Shape keys** (blender K2/K3 🧠):
- `Basis` is the template mean.
- `F3D_stageB` and `F3D_stageD` are diagnostics, set to 0.
- `F3D_ID_v<n>` holds the likeness, written with `from_mix=False`, `slider_max` 1.5.
- `artist` is kept as a delta across refits.
- Per-view expression keys are written only with `RIG_ANIMATE` consent (ethics F4).
- Nothing is applied in place or remeshed.

**Manifest** (store build):

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

- **Store build.** No wheels, no `network` permission, CC0 assets only (blender L1). Engine files carry MIT SPDX headers inside the GPL-3.0-or-later distribution (ethics A1). The minimum version is the oldest line CI tests (Q3).
- **Full build (GitHub only).** Adds per-platform MediaPipe wheels and a NOTICE. Its compliance with the platform rules is ↔️.
- **Detector helper.** `tools/detect_mediapipe.py` runs in any Python, so the cp311 → cp313 wheel lag stops mattering (blender-python-ml-deps 🧠).

## 5. Validation and QA

### 5.1 Test pyramid

1. **Unit and oracle tests.**
   - Jacobians match numeric derivatives.
   - Noiseless solves reach RMS < 10⁻⁶.
   - Camera ↔ Blender round trip to 10⁻⁶·s; OBJ round trip < 2 µm (blender Q1/Q2 🧠).
   - Schema and policy tables.
   - Each QA gate is tested on synthetic arrays (blurred checker, clipped ramp, smoothed noise).
2. **Scenario test bed** (`face3d/testbed`, seeded). A scenario is a subject × a capture protocol × a detector model × a set of faults.
   - **Subjects:** the existing `random_subject` with 0.8 mm RMS asymmetry (facial-asymmetry 📄).
   - **Protocols:** studio ring, rear-phone handheld, selfie set, camera-roll mix.
   - **Detector model:** class σ, a fixed per-index bias field of 1–3 mm shared across views (reconstruction principle 5 🧠), 5 % outliers and TTA spread.
   - **Rendering:** a small numpy rasteriser draws masks and procedurally textured images for the contour and QA tests.
3. **Bridge tests.**
   - Pure-function tests: axis and unit mapping, the key planner, the zip builder.
   - A manifest lint via `tomllib`: licence, tagline ≤ 64 characters, no numpy wheel, no `network` permission.
   - A headless script (`blender -b --factory-startup --python-exit-code 1`) is provided for CI elsewhere.

### 5.2 Fault-injection matrix

All targets here are 🆕. M1 first records the current engine as the baseline.

| Fault | Must raise | Required | Degradation bound |
|---|---|---|---|
| 1 mirrored view of ≥ 3 | `Q-MIRROR` | TPR ≥ 0.95 at ≥ 0.8 mm asymmetry; FPR ≤ 0.02; `undetermined` on symmetric subjects | shape ≤ 1.1× clean |
| Orientation not baked | `Q-ORIENT` | TPR ≥ 0.99 | — |
| EXIF ±30 % crop, or missing | `C-FOCAL-PRIOR` when unobservable | focal < 5 % off when views span ≥ 60° (community R8.4 🧠) | shape ≤ 1.2× clean |
| Selfies at 0.35 m | `Q-SELFIE`, tier ≤ B | z within 15 % | nose-width error ≥ 30 % lower than at ρ = 0 |
| Jaw 5–15°, smile | expressive tag | TPR ≥ 0.9 | rigid regions ≤ 1.1× clean |
| Beauty warp: eyes +6 %, jaw −4 % | `Q-RETOUCH` | TPR ≥ 0.8 with ≥ 3 clean views | identity bias ≤ 0.5 mm |
| Off-axis wide-angle warp | risk gate or k₁ | TPR ≥ 0.8 | — |
| Glasses, beard, hair | tag actions | jaw *prior-driven* under a beard | scalp inside the hull |
| Face 150 px wide | `Q-SMALL` | — | coverage holds |

### 5.3 Honesty metrics

- **Interval coverage.** For regions marked *measured*, between 0.90 and 0.99 of vertices must have |error| ≤ 1.96·σ_rep (🆕).
- **False confidence.** At most 5 % of *measured* regions may have an RMS above twice the benchmarks-metrics Table 6 target (🆕).
- **Flag precision.** No more than 1 spurious flag per 10 clean photos (🆕). Alarm fatigue is a failure too.
- **Promotion rule.** A prior or default becomes the default only if held-out error falls and coverage holds.

Shape is scored with `face3d/eval`: exact point-to-triangle distance under both NoW-style and landmark-only alignment, reporting median, p95, F@1/2 mm, per-region bias, scale error and configuration RMS (reconstruction EV-1/2 🧠).

### 5.4 Real-data bed

This runs outside CI.
- **Sitters.** Start with 1–3 consenting sitters (benchmarks-metrics 🧠) and grow to about 10, spread across age, skin tone, beards, glasses and hair.
- **Captures per sitter:** a reference scan and a repeat scan (the noise floor), the protocol ring, a rear-phone set, a selfie set and a dated camera-roll set.
- **Data handling.** Data is held under ethics §4 retention rules. Only aggregates are committed, and a leakage guard keeps tuning sitters out of the reports.
- **What it calibrates:** every 🧠 and 🆕 σ and gate, the per-class bias, the detector-semantics map, and the six-face lineup (target ≥ 80 %).

### 5.5 What the artist sees

- **Per-camera sheets** (community R8.1 🧠): photo, clay render, 50 % overlay, difference, silhouette chamfer, plus flipped, blurred and 64 px versions.
- **Worst landmarks first**, in % IOD.
- **LOVO per view**, flagged when held-out error exceeds 2× in-sample (reconstruction principle 15 🧠).
- **Caliper sheet**, flagging differences over 2 mm.
- **Canon z-scores** in art vocabulary.
- **Likeness lint** that flags only |model − photo| > 2σ_photo and never pulls a supported feature toward the mean (community R8.2 🧠).
- **"Over-symmetric" warning** when mirror RMSD < 0.3 mm.
- **Approval renders** from ≈1 m and from the sitter's favourite photo camera (camera-perspective-distortion ↔️).

## 6. Milestones

Each milestone ships on its own and is tested here on synthetic data.

- **M1 – Test bed first.** `face3d/eval`, `face3d/testbed`, the scorecard JSON and the `testbed --suite smoke` command. *Accept:*
  - point-to-triangle matches brute force to 1e-9;
  - a known similarity is recovered;
  - the current engine's baseline scorecard is committed;
  - the smoke suite runs in ≤ 90 s.
- **M2 – Ingest and QA.** EXIF additions, HEIF-EXIF, PNG reading, orientation, schemas, policy gates, the §3.1 gates, the focal ladder, focal groups and the `triage` CLI. *Accept:*
  - byte-fixture goldens pass;
  - each gate fires on its fixture and stays silent on clean ones;
  - running without consent is refused (ethics F3);
  - results are deterministic.
- **M3 – Robust cameras and BA.** §3.2–3.5, observability and LOVO. *Accept:*
  - the z (0.25–5 m) and f35 (13–200 mm) sweeps meet the camera, mirror and orientation rows of §5.2;
  - unobservable focal length is reported;
  - existing tests pass with updated defaults.
- **M4 – Nuisances.** Expression tags, the jaw hinge, the ψ adapter interface, occluders, the retouch and warp tests, date clusters. *Accept:* the matching §5.2 rows.
- **M5 – Template kit, warp and uncertainty.** Kit builder (CI uses a procedural stand-in head; the real CC0 kit is built offline with recorded hashes), registry, staged warp, gates, σ propagation and the ledger. *Accept:*
  - the finite-difference check passes;
  - smoke-suite coverage is within [0.90, 0.99];
  - the experimental basis stays off unless it wins.
- **M6 – Contours and silhouettes.** §3.8. *Accept:*
  - the tracer lands within 1 px of rendered mask edges;
  - synthetic profile error ≤ 1.5 mm at the nose tip and chin;
  - no scalp vertex lies outside the hair hull.
- **M7 – Blender MVP.** §4. *Accept:*
  - bridge pure-function tests and the manifest lint pass;
  - the zip contains no wheels and no non-CC0 assets;
  - headless scripts exist for the 4.5 and 5.2 LTS lines.
- **M8 – Helper, texture and review.** The detector helper, with its JSON contract tested via a fake backend, plus §3.11 and §5.5. *Accept:*
  - gains recovered within 2 % (TEX-8 🧠);
  - no colour lands on occluded texels;
  - filtered views are excluded.
- **M9 – Calibration release.** The §5.4 bed and a published calibration report that moves 🧠 and 🆕 values to measured ones. The tooling is tested; the data is not in CI.

## 7. Risks and deliberate omissions

**Risks**

- **No proven licence-clean statistical shape model.** The baseline is weak in depth. Coverage rules and next-best-photo prompts push users to add profiles rather than lean on the prior.
- **Most values are uncalibrated.** About 70 % of the cited values are 🧠, and the 🆕 gates are ours. They stay labelled provisional until M9.
- **Synthetic detector errors are not MediaPipe's real errors.** M9 calibration of detector semantics addresses this.
- **Some faults are undetectable:** mirroring on near-symmetric faces or all-selfie sets, and a filter on a single photo. We report `undetermined` instead of guessing.
- **Packaging is unresolved:** cp313 MediaPipe wheels, the store's position on bundled models (C7/C8), HEIC loading inside Blender, and 5.x attribute names. The helper and manual pins keep every stage usable regardless.
- **Performance:** the dense Hessian is fine up to about 150 landmarks × 12 views; beyond that we need the Schur complement (M3).
- **Over-flagging:** alarm fatigue is measured (§5.3).

**Left out of the default path, on purpose**

- **Monocular depth, generative fill, Gaussian avatars and photometric shape terms.** None of these are measurements (reconstruction principles 12–14). They may return later as opt-in features, gated by the test bed.
- **Automatic beard, glasses and hair segmentation.** User tags plus an optional SAM helper cover this.
- **Identity embeddings.** Evaluation-only and opt-in. The weights are mostly non-commercial (NC), and embeddings are never stored.
- **"Un-filtering" retouched photos.** We only down-weight them.
- **Phone video depth, ear detail beyond silhouette plus prior, hair grooming, teeth and fine eyelid detail.** These wait for their gap-topic notes.
- **Symmetrising, anonymising, 1:N matching and URL import.** Never built (ethics F17, F18, A5).
