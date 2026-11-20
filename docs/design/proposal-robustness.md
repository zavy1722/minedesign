# Proposal: a robustness-first photo-to-head engine

*Design angle: robustness first, built for the photos people actually take. Dated 2026-11-20. Based on `face3d/` at 887c5e5 (42 tests passing) and `research/_raw/requirements_*.md`.*

**Badges:** ✅ verified, 📄 single source, 🧠 unverified expert knowledge, ↔️ contested, 🆕 introduced here and unsourced (must be calibrated on the test bed, §5). The gap-topic notes arrived during drafting and are cited by name. Every 🧠 and 🆕 value is a named config entry that carries its badge.

## 0. Thesis

The tool will be judged on mirrored selfies, EXIF-less messenger copies, beards, and a smile in the only three-quarter view. Four rules follow:

1. Every failure mode gets a simple test that can be checked.
2. Weak evidence is down-weighted or excluded, never fitted through.
3. Each region states what it can still claim.
4. Every default is earned on a fault-injection test bed.

When a simple method and a clever one compete, the simple one wins.

## 1. Vision and user journey

1. **Consent.** A `ConsentRecord` with `RECONSTRUCT` scope is required before anything runs (ethics §2.1).
2. **Photos.** Each photo is hashed, its EXIF is read, and orientation is baked into a working copy. Originals are never modified.
3. **Landmarks.** From MediaPipe, via a helper or a wheel, or placed as manual pins. Pins always work, so no download is ever required (ethics A4).
4. **Triage.** Each photo gets a QA card, and every flag names its action, e.g. *"selfie at ≈0.35 m: colour and frontal outline only"*.
5. **Solve.** Robust multi-view bundle adjustment (BA), a mirror check, and an observability report.
6. **Fit.** A staged warp of the CC0 template, contour fitting, and edge-snapped profiles.
7. **Review.** A claims ledger marks each region *measured*, *constrained*, *prior-driven* or *unobserved*. Alongside it: held-out checks, overlays, and the next photo that would help most.
8. **Hand-off.** Shape keys, an `artist` layer, a Multires copy, gated texture, and provenance.

**Promise by input tier.** The tier is computed from the evidence, never picked by the user.

| Tier | Typical input | Promise | Label |
|---|---|---|---|
| S | ≥ 5 views over ±60–90° yaw at 1.5–3 m; tele lens; EXIF; scale reference | Metric; depth measured; regional targets met (benchmarks-metrics T6 🧠) | `metric` |
| A | Rear phone camera; ≥ 3 views, one at \|yaw\| ≥ 45°; EXIF | Proportions; depth where coverage holds (§3.10); iris scale ±2–4 % (multi-view-fitting 🧠) | `iris-scaled` |
| B | Camera roll: mixed devices and dates, missing EXIF | Frontal proportions; depth from the prior unless some view is beyond 60° yaw | `proportions only` |
| C | One photo, or selfies only | Blockout through its own camera; no claims on nose projection, ears or cranium | `blockout` |

## 2. Architecture

### 2.1 Modules

The engine imports only `numpy`, `math`, `json`, `struct`, `zlib`, `hashlib` and `tomllib`. All imports are relative, and `bpy` is never imported (blender A1). The St column marks each module as E (exists), X (extend) or N (new).

| Path | St | Purpose |
|---|---|---|
| `face3d/core/{schema,policy,config}.py` | N | Formats; consent scopes; licence taint (AND over components; ethics A2); badged defaults |
| `face3d/io/exif.py` | X | Add DateTimeOriginal, Software, DigitalZoomRatio, LensMake/Specification, SubjectDistance, CustomRendered; read all APP1 segments |
| `face3d/io/{heif_exif,png,image_ops,landmarks}.py` | N | HEIC: apply HEIF `irot/imir/clap`, then ignore EXIF Orientation (smartphone-camera-pipeline 🧠); stdlib PNG; flip with label permutation; landmark adapters |
| `face3d/qa/{image,photo,expression,mirror,retouch,flags}.py` | N | Gates (§3.1, §3.6); flag registry (code, severity, evidence, action, source) |
| `face3d/solve/pnp.py` | X | Multi-start, cheirality, twin flag, CAM-3 hypotheses, Huber in σ units |
| `face3d/solve/{noise,observability}.py` | N | §3.2; σ(log f), σ(log z), P, leave-one-view-out (LOVO) |
| `face3d/solve/bundle.py` | X | Covariance blocks, visibility, jaw hinge, distance priors, soft focal tie, view cap, rejection, Schur marginals |
| `face3d/model/{registry,template_kit,prior,nuisance}.py` | N | Landmark registry (anatomy R2.1), hash-checked kit, priors, jaw, occluders |
| `face3d/fit/{template,silhouette}.py` | X | Gated stages, reflection check; sliding and one-sided contours |
| `face3d/fit/{contour_trace,uncertainty}.py` | N | Dynamic-programming edge snap; vertex σ; ledger |
| `face3d/geometry/rbf.py`, `mesh/laplacian.py` | X | Per-landmark Λ; per-vertex stiffness |
| `face3d/solve/{lm,triangulate}.py`, `geometry/{camera,procrustes,rotations}.py`, `mesh/{core,sparse,reduced}.py`, `synthetic.py` | E | Reused unchanged |
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

- **Scheme file** (bundled, our own CC0 work; the scheme is never inferred from N, reconstruction FMT-1): `lr_permutation`, `midline`, `classes`, `convention` (surface or semi-contour), `sigma_iod` per class, `anatomical` name→index map, `verification`.
- **Template sidecar** (written by the kit builder): `source` (upstream SHA-256, `CC0-1.0`), `units: mm`, `topology_sha256`, `order_checksum`, `landmarks` (kind, tri, bary, σ, provenance), `scheme_maps` per detector version, `regions`, `mirror_map`, `contours`, `stiffness`, `basis` (K, SHA-256, status).
- **Result file:**
  - run: `config_sha256`, `seed`, input hashes, `tier`;
  - per camera: K, R, t, f35, z, P, σ_logf, `focal_status`, mirror `{decision, Δ, status}`;
  - per view: in-sample and LOVO RMS (% IOD), `noise_scale`, `weight_share`, `rejected_frac`, flags;
  - `scale {mode, s, σ}`, landmarks with covariance, `regions [{name, status, k, σ_mm, why}]`, `licence {commercial_ok, components}`, mesh, per-vertex σ.

### 2.4 Coordinate conventions

All conventions live in `core/schema.py` and each has a round-trip test.

- **Image.** The origin is the top-left pixel's *corner*, so pixel (i, j) has its centre at (i + ½, j + ½), as in `camera.py`.
  - MediaPipe: u = x·W.
  - Resize: u·W/W′. The +0.5 form from blender D3 is not used.
  - Flip: u′ = W − u, plus the label permutation π.
- **Camera.** OpenCV convention: X_c = R·X_w + t.
- **Head frame.** mm, float64. +x is the subject's left, +y up, +z forward, origin midsagittal (anatomy R1.1).
- **Blender.** An `R_x(+90°)` parent maps (x, y, z) to (x, −z, y), with scale 0.001 (blender A8).
- **IOD.** Measured ex–ex (landmark-detection T2). Interpupillary figures are multiplied by 0.70 (T3 🧠). Per view, IOD_px = f·IOD_mm/z_v. The 2D ex–ex distance is not used, because it halves at 60° yaw.
- **Determinism.** Fixed seeds, ordered hypotheses, stable sorts, float64, golden tests at rtol 1e-5 (blender Q2). CI runs on 3.11 with NumPy 1.26 and on 3.13 with NumPy 2.x (A4).

## 3. Algorithms

### 3.1 Input QA gates

No gate ever pulls a value toward a norm (anatomy §6). Each gate takes one of five actions: down-weight, drop a landmark class, exclude the photo from geometry, exclude it from texture, or ask the user.

| Failure | Detection | Action | Source |
|---|---|---|---|
| Orientation ignored | `exif_applied` false; view RMS > 3σ; roll ≈ ±90° | Bake, re-detect | blender §10 🧠 |
| EXIF stripped | No Make, Model or f35 | Source-type prior (§3.3) | community R2.2 🧠 |
| Crop or zoom | Non-4:3 aspect: test the static-tag and updated-tag hypotheses; c = f35/FocalLength exceeds the group mode by > 2 % | σ_logf 0.09 (aspect crop) or 0.06 (zoom) | smartphone-camera-pipeline 🧠 |
| Front camera | LensModel contains "front" | Mirror test; selfie distance prior | camera-perspective-distortion 🧠 |
| Near camera | Solved z, checked against f·63/IPD_px. Warn below 1 m, strong warning below 0.8 m | Below 0.6 m: 2D and texture only | community §9 🧠 |
| Face-warp correction | f35 ≤ 16 mm; face beyond 60 % of the half-diagonal or > 25° off-axis; curved background lines | Local virtual camera: rotate the face ray onto the axis, f′ = f·sec²(θ/2); otherwise σ × 3 | community R1.7 (warp ✅); smartphone-camera-pipeline 🧠 |
| Processing risk | Portrait mode (CustomRendered), night, beyond-optical zoom, editor, C2PA AI-edit marker | Robust weight plus a warning | smartphone-camera-pipeline 🧠 |
| Low resolution | Face < 250 px warns, < 120 px rejects; iris < 20 px | σ floor; no iris scale; no detail | community R1.4 🧠, R4 ↔️ |
| Blur, blink, clipping | Laplacian variance in bottom 20 %; eye aspect ratio (EAR) < 0.2; > 2 % of skin clipped | Down-weight; drop lids; no photometry | community R1.4 🧠 |
| Mixed dates | Span > 18 months | Date clusters | community §9 🧠 |
| Two faces; no consent | `num_faces=2` at ≥ 0.6; sha256 not consented | User picks; block | blender ML 🧠; ethics F1–F2 |

### 3.2 Noise model

For landmark i in view v, with t̂ the tangent taken from neighbouring points:

Σ_iv = s_v²·m(c_i, tag_v)²·R(t̂)·diag(σ_n², σ_t²)·R(t̂)ᵀ
σ_• = max(σ̂_•(c_i)·IOD_v·√(N/N_eff), σ_tta, σ_floor)

- **σ̂ by class**, in % IOD, normal/tangent (landmark-detection T5 🧠): iris 1.0; anchors 1.5; lid and lip contours 2/5; pronasale 2.5; brows 3–5/6; jaw 2.5/10–15.
- **N_eff** = 60–100, applied only to points outside the curated ~100-point subset.
- **σ_tta** is the spread over 6–10 test-time-augmentation passes (BA-2 🧠).
- **σ_floor** = max(0.5 px, k·face_px/256), with k = 0.6 inner, 0.4 iris, 1.0 brows, 1.5 contours (blender ML 🧠).
- **Per-view scale.** s_v² = clip(median‖Σ^{−½}r‖²/1.386, 1, 9), where 1.386 is the median of χ²₂ (deformation-fitting-math 🧠). Bad views lose weight automatically. Flag any view with s_v > 2 (🆕).
- **View weight.** w_v = 1/(number of views in its 15° yaw bin), and no single view may carry more than 40 % of the information (community R1.8 🧠).

This model replaces `sigma_px = 1.0`, which is about 13× too tight (landmark-detection 🧠).

### 3.3 Camera initialisation

**Focal prior.** The first matching rule sets the log-normal prior (CAM-6, community R2.2 🧠):

| Evidence | Prior |
|---|---|
| SfM import or calibration | σ_log 0.005–0.02 |
| Uncropped EXIF f35 | σ_log 0.04 |
| EXIF f35, suspected crop | σ_log 0.08–0.10 |
| FocalLength + focal-plane resolution | σ_log 0.10 |
| Phone without focal data | 26 mm, σ_log 0.25 |
| Nothing | 50 mm, σ_log 0.6 |

The current 0.35 fallback cannot reach phone lenses.

**Focal groups.** Groups are keyed on (Make, Model, LensModel, f35, W, H, still/video) and tied softly with σ 0.02 (CAM-5 🧠).

**Distance prior on log z.**

| Camera | Prior |
|---|---|
| Front camera | 0.35 m, σ 0.3 |
| Rear camera | 0.8 m, σ 0.4 |
| Tele | 2 m, σ 0.4 |
| Unknown | 1.0 m, σ 0.7 |
| Taped distance | ±5 cm |

Sources: CAM-6 and community R2.4 (🧠). Bounds are 0.25–10 m (blender C6).

**Multi-start PnP.**
- f35 hypotheses: {13, 24, 26, 35, 50, 77, 85, 120, 135, 200} (CAM-3 🧠). Today's list lacks 26, 77 and 120.
- Each hypothesis starts from three poses: affine, pitch-flipped and yaw-mirrored.
- Solutions that fail cheirality are rejected.
- If two poses more than 10° apart score within 20 % of each other, raise `C-TWIN` and keep both (🆕).

**Off-axis faces.** Rotate the face ray onto the optical axis before initialising (camera-perspective-distortion 🧠).

**Solve order.** Start with the most frontal, most complete view. Initialise later views against the BA consensus rather than the template.

### 3.4 Mirrored images

**Test statistic.** Fit the view against X̂, the consensus of the other views (or the template when there is only one view). C₀ is the robust PnP cost as given; C₁ is the cost after flipping, u′ = W − u with labels permuted. Then Δ_v = (C₀ − C₁)/C₀.

**Undetermined case.** A = ½(X̂ − M·X̂_π) is the shape's asymmetric part, and g = Σ‖Σ^{−½}J_i A_i‖² is the expected cost gap. If g < 4 (🆕), the answer is `undetermined`, because a near-symmetric face cannot be told from its mirror image.

**Thresholds (↔️).** Community R1.6 says 0.2; smartphone-camera-pipeline says 0.1. So:
- **Δ_v > 0.2**, plus a front camera or agreeing views: flip automatically and log it.
- **0.1 < Δ_v ≤ 0.2:** ask the user to check the parting or a mole (likeness-mistakes 🧠).

**All views mirrored** (e.g. selfies only): this is undetectable, so the project is marked `mirror: unverifiable` and asymmetry claims are flagged.

### 3.5 Robust bundle adjustment

E = Σ_v w_v Σ_i ρ_H(‖Σ_iv^{−½}(π_v(X_i + J_i(θ_v)) − u_iv)‖; δ = 2) + Σ_v E_contour,v
  + Σ_g ((log f_g − μ_g)/σ_g)² + Σ_{v∈g} ((log f_v − log f_g)/0.02)² + Σ_v ((log z_v − μ_z)/σ_z)²
  + E_shape(X) + Σ_pairs ‖Σ_sym^{−½}(X_l − M·X_r)‖² + Σ_mid (x_i/σ_mid,i)² + E_scale + E_pins

- **Robust loss.** Huber at 2σ in σ units replaces the current 3 px and 3σ thresholds.
  - After convergence, hard-reject residuals beyond 4σ (BA-5 🧠) and re-solve. Calibrate the cut-off against 3.03σ, the 1 % false-alarm point in 2D (validation-test-bed 🧠).
  - Flag any view with more than 15 % of its points rejected.
- **Scale.** Explicit log-normal prior: σ_log 0.03 with no anchor, 0.04 with an iris, 0.005 with a caliper chord (metric-3d-landmark-reference 🧠). Under an iid prior the scale posterior was 2–4× overconfident (validation-test-bed T5 🧠).
- **Visibility.** Weight 0 at n·(−v) < cos 80°, rising to 1 at cos 60°. Far-side oval points drop out when |yaw| > 25° (BA-3 🧠).
- **Symmetry σ** (anatomy R4.2 🧠):
  - pairs: canthi 0.7–1.0 mm, brows 1.5, alae 1.0–1.5, cheilia 1.5–2.0, gonia 2.5–3, ears 3–4;
  - midline: n 0.75–1.0 mm, prn and sn 1.5–2.0, pg and me 2–3.
- **Covariance.** Return the full 3N×3N matrix, using the Schur complement once N ≥ 100. Report each landmark's prior share p_i = σ²_post/σ²_prior. *Likeness mode* widens the prior until p_i ≤ 0.2 wherever two or more views see the point (anatomy R1.4 🧠).
- **SfM cameras.** Triangulate, align with Umeyama, then solve shape. Landmarks never move SfM cameras (BA-12 🧠).

### 3.6 Expressions, occluders and retouching

**Expression tags.** Scores are read as Δb, the change from the subject's own minimum, not from 0 (landmark-detection 🧠).
- *Neutral*: jawOpen < 0.08, mouthSmile < 0.15, eyeBlink < 0.35, browInnerUp < 0.2.
- *Expressive*: smile > 0.25; squint, eyeWide or brow > 0.3; blink > 0.4 (anatomy §6 🧠).
- *Mild*: anything between.
- *No scores available*: an inner-lip gap / ch–ch > 0.04 drops sto and li (anatomy §6 🧠); a mouth width > 1.08× the median marks a smile (🆕).
- Tags are refined from residuals for at most 3 rounds (BA-9 🧠).

**σ multipliers** (neutral / mild / expressive; expression-neutralization 🧠): rigid 1/1/1–1.5; semi-mobile 1/1.5–2/2–3; mobile 1/3/drop; jaw-dependent 1 while θ is fitted.

**Jaw hinge.** X_i(θ) = c + R_axis(θ)(X_i − c), with the axis through condyles ≈10–13 mm anterior to tragion (BA-1 🧠). On neutral views θ ~ N(1.5°, 1°), bounded to 0–30° (anatomy §4 🧠). No expression data is needed.

**Expression basis ψ.** Opt-in, through licence-clean adapters (e.g. FLAME 2023 Open), anchored at a neutral-view mean ψ ≈ 0 with σ 0.1 (BA-9 🧠). With no neutral view, mouth and lid measurements finer than 1 mm are suppressed.

**Occluders.** Users tag these with one click. Hair masks may come from MediaPipe's hair segmenter in the helper (weights ↔️). Parsers with glasses or ear classes are NC (face-segmentation-contours 🧠).
- **Glasses:** eye σ ×2, no iris scale, lid points under the frame dropped (anatomy R3.4 🧠). Flag the view if iris/(en–ex) is more than 3 % off the glasses-free median, since lenses magnify ≈1–1.5 % per dioptre (🆕).
- **Beard:** drop pg, gn, me and the jaw; the outline becomes an outer bound; the jaw stays *prior-driven* without a shaven photo (community R5.4 🧠).
- **Hair:** ear and temple weight 0; no silhouette above the trichion (blender S3 🧠).
- **Makeup:** lip and brow borders σ ×2 (artstation-likeness 🧠).

**Retouching and beauty filters.** Three tests, each relative to the other views:
1. EXIF `Software` names an editor (🆕).
2. Skin-smoothness index (cheek ÷ brow-and-iris band energy) < 0.5× the set median (🆕).
3. Eye-enlarging or jaw-slimming residual patterns give t > 3, or eye-width/IOD or bigonial/IOD sits > 3σ from consensus (smartphone-camera-pipeline 🧠).

A flagged view gets σ ×2–3 and no texture use (artstation-likeness ↔️). A filter applied to the only photo cannot be detected, and the ledger says so.

**Non-pinhole processing.**
- A diagnostic k₁ (σ 0.02) with |k₁/σ| > 3 on a phone JPEG suggests non-pinhole processing (CAM-1 🧠).
- A radial-residual slope against ρ_i·δ_i implying > 5 % magnification error means z or f is wrong (community R2.8 🧠).

### 3.7 Licence-clean shape prior

No permissive, large-population head model is confirmed (reconstruction §12), so the prior comes in three layers.

1. **Baseline.** A factor prior on 44 metric landmarks in the Frankfort horizontal (FH) frame (metric-3d-landmark-reference 🧠). It is synthesised from sourced chord norms by `research/_raw/scripts/`, and it never uses ancestry (anatomy R7.4).
   - E = ½rᵀ(κ²S)⁻¹r, with S = LLᵀ + R (18 factors; solved by Woodbury).
   - κ = 1 when the population matches, 1.5 when it is unknown, and 2.5 on the al and en x-coordinates.
   - An extra 6 mm depth factor applies until the prior is verified.
   - It is replaced by FLAME 2023 Open, 3DFN or ANSUR II statistics as those become available.
2. **Experimental.** X = μ + B·c, c ~ N(0, I).
   - B is a mass-weighted SVD of the CC0 MPFB2 face targets (K = 40–80).
   - Variances come from an anthropometric morphable model: 2,000–5,000 norm-matched samples, keeping 95–99 % of the variance (open-template-head-kit 🧠).
   - It stays off until it beats the baseline on held-out error and coverage.
3. **Opt-in.** FLAME 2023 Open from a user path, SHA-pinned and attributed (CC-BY-4.0; contents unverified 📄). Any other FLAME version or BFM sets `commercial_ok=false` (LIC-1).

**Gates.**
- ‖c‖² > χ²_K(99.9 %) or any |c_i| > 3: implausible (MM-5 🧠).
- ‖c‖² < K − 2√(2K): "pulled toward average" (community R5.8 🧠).

**Nothing is fabricated.**
- **Template mesh.** `build_template_kit.py` cuts it from a CC0 base: MPFB2 (📄) or Blender Studio Human Base Meshes (✅). It pins the upstream SHA-256, records the topology hash and refuses anything else. The hm08 vertex counts are unconfirmed (🧠), so they are read from the file, never assumed.
- **Template landmarks** come from two annotators who must agree within 1 mm (🆕).
- **MediaPipe maps** come from render-and-detect calibration over 20–50 cameras. Offsets are shrunk by w = n/(n + 2), and the calibration spread is added to Σ (landmark-index-correspondence 🧠).
- **CI** checks hashes, schemas, that the L/R map is an involution, and that midline points map to themselves.

### 3.8 Contours, silhouettes, profiles and hair

**Edge snap.** The input is a coarse polyline: at least 5 clicks, or the oval points. Each of its M stations may move by an offset k ∈ [−L, L] along its normal, with L = 3 % IOD. The snap minimises

C = Σ −g_j(k_j) + λΣ|k_j − k_{j−1}|

where g is the gradient magnitude after a 1 px Gaussian and λ = 0.2·median g (🆕). The Viterbi solve takes O(M·L²) and is deterministic. Each point gets σ_n = max(1 px, 1/√curvature). SAM (Apache-2.0) is an optional mask source and runs only in the helper.

**Contour terms.** Each observation is a `ContourObs{xy, normal_out, σ_n, kind ∈ {hard, outer_bound, inner_bound}, source, commercial_ok}` (face-segmentation-contours 🧠). Residuals are normal-only, r = n̂ᵀ(π(X_c) − x)/σ_n:
- `hard`: Huber.
- `outer_bound` (hair, beard, hat): max(0, r), with margin 0–3 mm (community R5.4 🧠) and weight 10× skin (cranium-under-hair 🧠).
- `inner_bound`: max(0, −r).

Today's `fit_silhouettes` back-projects the full 2D correction and drifts along the contour, so the tangential part is dropped.

**Matching.**
- The model contour is the n·v zero-crossing, interpolated along edges.
- Matches are closest points, re-associated every iteration (BA-4 🧠).
- Pairs whose normals differ by more than 30–45° are rejected.
- The gate is 0.15·IOD_px, shrinking to 5σ_n, instead of a fixed 60 px.
- A numpy Felzenszwalb–Huttenlocher distance transform replaces the dense O(M·P) matrix.

**Contour noise.** σ_n² = σ_edge² + (0.5·s_model)² + σ_blur², with a floor of 0.005·IOD_px. Correlated samples inflate σ_n, and no view gets more than 30–50 effective samples.

**Scalp.**
- It stays at least 2 mm inside the hair hull (blender W7 🧠).
- Cranium σ follows the visual-hull overshoot: 7.8 mm with 4 views, 1.9 mm with 8.
- A taped circumference (σ_log 0.028) enters as an arc-length equality (cranium-under-hair 🧠).

**Profiles.** Detector points are dropped when |yaw| > 60–70° (landmark-detection 🧠). Curvature-Viterbi profile labels are computed only when |yaw − 90°| < 10°, and only for initialisation and QA; the geometry goes through the contour term. Pins on g, n, prn, sn, ls, li and pg take σ 1 % IOD (blender S4 🧠).

**Acceptance.**
- Profile error ≤ 1–1.5 mm at the nose tip and chin (SIL-3 🧠).
- Contour within 1 % of face height (S5 🧠).
- If the interior fits but the contours fail, report "f and z wrong", not a shape error.

### 3.9 Template warp

| Stage | Operation | Advance when |
|---|---|---|
| A | Umeyama, proper and reflected. Reflected RMS < 0.5× proper → flag "mirrored source", never auto-flip. 7-landmark RMS > 10 mm → wrong axes (blender W2 🧠) | always |
| B | RBF, φ = r: (Φ − Λ)w + Pa = y, Λ = diag(α·σ_i²), α = 10⁻² (MM-8 🧠) | landmarks < 2–3 % IOD (community R5.2 🧠) |
| C | Bilaplacian, per-vertex stiffness: lid margins 3.0, lips 0.3, forehead 0.5, ligaments 3–5 (anatomy R5.9 🧠). Offsets capped at 3–5 mm unless ≥ 2 views agree (MM-10 🧠) | RMS gain < 1 %/iteration |
| D | Silhouettes via `ReducedDeformer`; no landmark moves > 0.5 mm | contour ≤ 1 % of face height |

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

**Reported σ.** σ_rep² = σ²_post·max(1, η², χ²_red) + σ²_bias, where:
- η is the LOVO ratio of observed to predicted error;
- σ_bias is 1–3 mm per class until a semantics map exists.

Bias does not average away (reconstruction principle 5 🧠). In the engine's own coverage check, a 1 mm definition bias gave NEES/dof 3.6 (validation-test-bed T5 🧠).

**Status** depends on k = 1 − σ²_post/σ²_prior:

| Status | Rule |
|---|---|
| *measured* | k ≥ 0.8 (anatomy §6 🧠) and coverage met |
| *constrained* | k from 0.5 to 0.8 |
| *prior-driven* | k < 0.5 (🆕) |
| *unobserved* | no view sees the region |

**Coverage rules.**
- Depth needs 2 views at least 30° apart (blender C7 🧠).
- Nose and chin projection need a front view plus one at |yaw| ≥ 60°.
- The jaw underside needs a low view (community R5.9 🧠).
- Ears need |yaw| ≥ 30° and pitch fixed by at least 2 views (R3.3 🧠).

**Focal length** is estimated only when σ(log f) < 0.10 (blender C2 🧠). Otherwise the result reads "focal from prior" (CAM-7).

**Scale** is one of *measured* (a caliper overrides everything; anatomy R3.4), *iris*, *IPD prior* or *proportions only*. References that disagree by more than 1 % are flagged (BA-10 🧠).

**Next-best photo.** The tool simulates candidate poses on a 15° grid and recommends the one that most reduces σ in prior-driven regions, weighted by T6 (benchmarks-metrics 🧠).

### 3.11 Texture projection

**Gates.** Projection runs only when reprojection error is at most 1.5 px median and 3 px max (blender T2 🧠), consent includes `TEXTURE`, and `rights_basis ≠ unknown` (ethics §3).

**Method** (TEX-1…7 🧠):
- numpy z-buffer, depth tolerance max(1 mm, 2σ_geom);
- per-view weight w = vis·cos²θ, faded out between 60° and 75°;
- linear-RGB gains;
- two-band blend split at 3 mm.

**Exclusions.** Views that are filtered, retouched, warped or clipped, or that come from another date cluster, never feed the albedo. Texture is never mirrored.

## 4. Blender add-on

**Package layout** (`blender_ext/face3d_head/`):
- the manifest;
- `__init__.py` and `compat.py` probes (< 100 ms);
- `bridge.py`, the only module that converts between bpy and numpy;
- `ops_*.py`, `ui_panels.py`, `overlays.py`, `jobs.py`, `keys.py`;
- the vendored `face3d/`;
- CC0 `assets/template/`, `LICENSE` and `NOTICE`.

**Operators** (all prefixed `face3d.`):

| Operator | Does | Runs |
|---|---|---|
| `project_new`, `photos_add` | ConsentRecord; hash, read EXIF, orientation-baked copies, strip GPS (ethics F12) | main |
| `landmarks_import`, `detect` | JSON import, or the helper or wheel | job |
| `pin_edit`, `trace_contour` | Pins in the photo camera (σ from zoom); polyline, then edge snap | modal |
| `triage`, `solve`, `fit` | §3.1–3.10 | job |
| `apply_result` | Cameras, keys, attributes. Refuses on topology-hash mismatch or in Edit or Sculpt mode (blender K1/K4) | main, UNDO |
| `bake_for_sculpt` | Duplicate, bake the key mix, clear keys, add Multires 2–3 (K5, SK-3 🧠) | main, UNDO |
| `project_texture`, `review_sheet`, `prepare_sharing`, `export` | §3.11, §5.5; purge leftovers (ethics F9); gated export | job / main |

**Panels** (Sidebar › *Face3D*):
- Project & Consent
- Photos: QA badges, tags, include, mirror
- Solve: tier, focal status, z, P
- Fit: stages, gates
- Review: ledger, LOVO, worst landmarks, next-best photo
- Export: blocking reasons

**Overlays** (`gpu`, one per photo camera):
- σ ellipses;
- residual arrows ×5;
- pin type and status shown by *shape* as well as colour (guided-workflow-accessibility 🧠);
- traced outline against the projected silhouette;
- a flipped thumbnail for the mirror prompt.

In 3D, the `face3d_sigma_mm` and `face3d_status` attributes colour the viewport, and region face sets drive masks.

**Undo.** Engine state lives in hashed sidecars outside the undo stack. Objects are re-fetched by `face3d_uuid` after an undo. A job refuses to apply if its target's topology hash has changed.

**Background jobs.**
- Each job runs as `[sys.executable, "-I", launcher.py, job_dir]` with files under `extension_path_user`.
- A timer polls every 0.1 s and does at most 20 ms of work per tick (blender A5 🧠).
- Cancel kills the process, so a crash never costs sculpt work.
- Under `bpy.app.background`, jobs run synchronously.

**Shape keys** (blender K2/K3 🧠):
- `Basis`: the template mean.
- `F3D_stageB` and `F3D_stageD`: diagnostics, set to 0.
- `F3D_ID_v<n>`: the likeness, written with `from_mix=False`, slider max 1.5.
- `artist`: preserved as a delta across refits.

Expression keys need `RIG_ANIMATE` consent (ethics F4). No key is applied in place, and the mesh is never remeshed.

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
- minimum version = the oldest line CI tests (Q3).

**GitHub build:** adds per-platform MediaPipe wheels and a NOTICE. Its compliance with platform rules is ↔️. The helper runs in any Python, so cp313 wheel lag never blocks anything (blender-python-ml-deps 🧠).

## 5. Validation and QA

### 5.1 Test pyramid

1. **Unit and oracle tests.**
   - Jacobians match numeric derivatives.
   - Noiseless RMS < 10⁻⁶.
   - Camera and OBJ round trips (blender Q1/Q2 🧠).
   - Schemas and policy tables.
   - Each QA gate on synthetic arrays.
2. **Scenario test bed** (`face3d/testbed`, seeded; validation-test-bed tier 1 🧠). A scenario combines four parts:
   - **Subject:** x = μ + Lz + Ce, drawn from the metric-3d-landmark-reference factor model.
   - **Protocol:** studio ring, rear phone, selfie, or camera-roll mix.
   - **Detector model:** class σ plus a 1–3 mm per-index bias shared across views (reconstruction principle 5 🧠), 5 % outliers, and TTA spread.
   - **Faults** to inject.

   A numpy rasteriser draws masks and images.
3. **Bridge tests.**
   - Pure functions.
   - A `tomllib` manifest lint: licence, tagline ≤ 64 characters, no numpy wheel, no network.
   - A headless Blender script (`--python-exit-code 1`) for CI elsewhere.

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

- **Coverage.** In *measured* regions, 0.90–0.99 of vertices must have |error| ≤ 1.96·σ_rep (🆕). Landmarks must show aligned 1σ coverage of 0.6–0.76 and NEES/dof of 0.8–1.25 over at least 30 seeds (validation-test-bed 🧠).
- **False confidence.** At most 5 % of *measured* regions may exceed 2× their T6 target (🆕).
- **Alarms.** No more than 1 spurious flag per 10 clean photos (🆕).
- **Promotion.** A default changes only if held-out error drops and coverage holds.

`face3d/eval` scores shape with exact point-to-triangle distance under NoW-style and landmark-only alignment (EV-1/2 🧠). It reports the median, p95, F@1/2 mm, per-region bias, scale error and configuration RMS.

### 5.4 Tiers 2–4 (outside per-push CI)

These follow validation-test-bed 🧠.

- **Tier 2 (nightly).** CC0 and CC-BY scans are rendered in Blender, passed through a simulated phone pipeline, then run through MediaPipe. The detection JSON is committed together with the licences.
- **Tier 3.** A 3D-printed CC0 head, photographed with real phones.
- **Tier 4.** Consenting sitters: 1–3 at first, growing to about 10, varied in age, skin tone, beards, glasses and hair (benchmarks-metrics 🧠).
  - Each sitter provides a scan, a repeat scan as the noise floor, a protocol ring, and rear-phone, selfie and dated camera-roll sets.
  - Retention follows ethics §4.
  - Only aggregate results are committed.

The tiers calibrate every 🧠 and 🆕 value and the detector-bias maps. They also run a six-face lineup test, with a target of ≥ 80 % correct.

### 5.5 What the artist sees

- **Per-camera sheets** (community R8.1 🧠): photo, clay render, 50 % overlay, difference image and silhouette chamfer, plus flipped, blurred and 64 px versions.
- **Error listings:** the worst landmarks first; per-view LOVO, flagged when held-out error exceeds 2× in-sample (reconstruction principle 15 🧠).
- **Measurement checks:** a caliper sheet (Δ > 2 mm) and canon z-scores phrased in art vocabulary.
- **Likeness lint.** It flags only |model − photo| > 2σ_photo, and never pulls a feature toward the mean (community R8.2 🧠).
- **"Over-symmetric" warning** below 0.3 mm mirror RMSD.
- **Approval renders** from ≈1 m and from the sitter's favourite photo camera (camera-perspective-distortion ↔️).

## 6. Milestones

Each milestone ships on its own and is tested here on synthetic data.

| Milestone | Scope | Acceptance |
|---|---|---|
| **M1** Test bed first | `eval`, `testbed`, scorecard, smoke suite | point-to-triangle matches brute force to 1e-9; baseline scorecard committed; smoke ≤ 90 s |
| **M2** Ingest and QA | EXIF/HEIF, PNG, schemas, policy, §3.1, `triage` CLI | each gate fires on its fixture and stays silent on clean ones; no-consent runs refused (ethics F3); deterministic |
| **M3** Cameras and BA | §3.2–3.5, LOVO | z and f35 sweeps meet the §5.2 rows; NEES/dof 0.8–1.25; existing tests pass |
| **M4** Nuisances | §3.6 | its §5.2 rows pass |
| **M5** Kit, warp, uncertainty | §3.7, §3.9, §3.10; procedural stand-in head in CI | propagation matches finite differences; coverage 0.90–0.99 |
| **M6** Contours | §3.8 | tracer within 1 px; profile ≤ 1.5 mm; scalp inside hull |
| **M7** Blender MVP | §4 | lints pass; zip holds no wheels and no non-CC0 assets |
| **M8** Helper, texture, review | fake detector backend | gains within 2 % (TEX-8 🧠); occluded texels uncoloured |
| **M9** Calibration release | §5.4 tiers | 🧠/🆕 values replaced by measured ones |

## 7. Risks and deliberate omissions

**Risks**

- **No measured, licence-clean shape model.** The baseline prior is synthesised (🧠), and it is weakest in profile depth (prn sits 108–130 mm ahead of tragion). Coverage rules and next-best-photo prompts push users toward taking profile shots.
- **About 70 % of the values are 🧠, plus our own 🆕 gates.** All are provisional until M9.
- **Synthetic detector errors are not MediaPipe's.** M9 calibrates the semantics.
- **Some cases are undetectable:** near-symmetric or all-selfie mirroring, and a filter on the only photo. These are reported as `undetermined`.
- **Packaging is open:** cp313 MediaPipe wheels, bundled models (C7/C8), HEIC loading in Blender, and 5.x attribute names. Helpers and manual pins keep every stage usable meanwhile.
- **Dense Hessian.** It is fine up to about 150 landmarks × 12 views; beyond that we use the Schur complement (M3).
- **Alarm fatigue.** It is measured (§5.3).

**Left out of the default path, on purpose**

- **Monocular depth, generative fill, Gaussian avatars and photometric shape terms.** These are not measurements (reconstruction principles 12–14). Each can be added later as an opt-in, gated by the test bed.
- **Automatic beard and glasses segmentation.** User tags handle these.
- **Identity embeddings.** Evaluation only; most weights are non-commercial (NC), and embeddings are never stored.
- **"Un-filtering" photos.** We down-weight them instead.
- **Phone video and TrueDepth.** A later milestone: one focal group and 12–24 sharp frames spread across yaw bins (phone-video-depth-capture 🧠).
- **Ears as hinged parts** (ear-reconstruction-sculpting 🧠), hair grooming, teeth and fine lid detail. These come after M9.
- **Symmetrising, anonymising, 1:N matching and URL import.** Never built (ethics F17, F18, A5).
