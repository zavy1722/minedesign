# Proposal: artist-in-the-loop photo → sculpt-ready head

*Design angle: UX-first. 2026-11-20. Builds on `face3d/` at 887c5e5 (42 tests pass).*

**How to read the citations**
- **`(topic badge)`** names a note in `research/<area>/`. For example, `(camera-pose-solving 🧠)` means that note, whose claim is unverified expert knowledge.
- **IDs such as CAM-3 or R4.1** point to rules in the digests `research/_raw/requirements_*.md`.
- **🧠 and ↔️ numbers are defaults, not constants.** Every such number ships as a named, tunable default in `defaults.toml`, and the expert view shows its badge.
- **Gap notes.** Nine of the ten gap notes landed today and are cited by name. `metric-3d-landmark-reference` is still missing and is marked **[gap]**.

---

## 1. Vision and the user journey

FaceBuilder sets the interaction bar: pins on any surface point, a live re-solve, and one camera per photo (facebuilder-blender 🧠). We rebuild that on open code and commercially clean data, and add three things it lacks. The tool says what the photos actually measured. It never overwrites the artist's work. And it ends in Sculpt Mode.

Automation speeds the artist up; it does not decide for them. Every automatic decision arrives as a card showing *why*, *what changes* and *undo*.

**Principles**
- **P1 Live, then thorough.** Adding a photo or dragging a pin re-solves the cameras and coarse shape at 20 fps or better. If an update would take more than about 50 ms, the solve waits until the pin is released (guided-workflow-accessibility 🧠). Refinement runs in the background.
- **P2 Plain-language uncertainty.** Every number comes with a range and a basis: *measured*, *partly measured* or *guessed from average proportions*. Ranges are given in mm, never as px RMSE.
- **P3 Non-destructive.** Originals are never modified. Solves are immutable. The fit, the asymmetry and the artist's sculpt sit on separate layers, and a refit never touches the artist's delta.
- **P4 Flags, not corrections.** Nothing the photos support is pulled toward a norm (requirements_anatomy §6).
- **P5 Accessible.** Shape-coded, colour-blind-safe overlays; a full keymap; no automatic motion. Expert detail is opt-in.
- **P6 Consent first.** No stage runs unless a consent record covers it (ethics §3).

**Journey: 7–9 photos → a sculpt-ready head in about 20 minutes**

| # | The artist… | The system… | The artist sees… |
|---|---|---|---|
| 0 | Fills in the consent wizard | Writes a `ConsentRecord` | "reconstruct: yes; texture: no" |
| 1 | Opens the **Shot card** | Shows the core views: front, ±45°, ±90°, low, high. Optional: a slicked-hair or cap view plus 3 tape measurements (cranium-under-hair 🧠) | Diagrams; "phone: 2–5× lens, 1.5–3 m" |
| 2 | Drops photos in | Reads EXIF and HEIC, bakes orientation, groups by lens, runs the photo checks, fills the pose ring | Per photo: icon + words + fix + *use anyway* |
| 3 | Clicks **Find landmarks**, or places the first pins blind (overlay hidden, against anchoring) | Helper job → PnP → joint solve | Cameras appear; a review queue of problem points |
| 4 | Works through the cards | Runs the mirror, expression, distance, focal and zoom tests | "Photo 4 looks mirrored (selfie?). Flipping lowers error 34 %. [Flip] [Keep] [Show me]" |
| 5 | Drags pins | Re-solves live; draws epipolar lines | All views update; next-best-photo hint |
| 6 | Clicks **Refine** | Runs stages B–D in the background | Progress, then the result swaps in (one undo step) |
| 7 | Opens **Confidence** | QA, measurements, held-out photo | Hatched "guessed" regions; a *wobble* of 8–12 posterior samples |
| 8 | Clicks **Hand off** | Builds the key stack, a Multires copy and masks; binds cameras to markers | Sculpt Mode; ←/→ steps through the photos |
| 9 | Texture and export (optional) | Gated projection; provenance | Albedo plus confidence, or a blocked export with reasons |

---

## 2. Architecture

### 2.1 Layers

```
L4 face3d_blender/   GPL-3.0-or-later extension; only bpy importer
L3 face3d/pipeline/  stages, live session, jobs-as-data, cards
L2 face3d/{solve,fit,texture,qa,guidance,handoff}/
L1 face3d/{geometry,mesh,model,io}/
L0 face3d/project/   consent, licence taint, data classes, audit (bpy-free)
tools/  MediaPipe helper, template-pack builder, extension builder
```

- The engine imports only numpy, math, json and tomllib, uses relative imports, and is vendored into the extension at build time (blender A1).
- The engine is MIT and the glue GPL, so the extension as a whole is GPL (ethics A1).

### 2.2 Modules

| Path | Status | Purpose |
|---|---|---|
| `geometry/{rotations,procrustes}.py`, `mesh/{reduced,sparse}.py`, `solve/triangulate.py` | exists | Kept. Procrustes gains a reflection mode (R3.3, W2) |
| `geometry/camera.py` | extend | Adds `from_blender_camera`; canvas offsets (C5); a per-view model (k = 0, k1 or a local virtual camera); crop and zoom hypotheses (smartphone-camera-pipeline 🧠) |
| `geometry/rbf.py` | extend | λᵢ = α·σᵢ² (MM-8). The sign bug was already fixed in 0843516 |
| `solve/lm.py` | extend | Returns the normal matrix; warm start; `time_budget_ms` |
| `solve/pnp.py` | extend | Uses the CAM-3 hypotheses, flip/mirror restarts and cheirality |
| `solve/bundle.py` | extend | Free-point BA: per-kind anisotropic σ in mm; σ_def floor; a global log-scale; full covariance; redescending final round (validation-test-bed 🧠) |
| `solve/reconstruct.py` | extend | Tiered focal priors (wires `f_prior_log_sigma`); view-bin weights |
| `solve/{live,observability,expression,mirror}.py` | new | Reduced joint solver; posterior, support, next-best-view; neutral tagging and jaw hinge; flip test |
| `model/{shape_space,landmarks,template_pack}.py`, `model/defaults.toml` | new | FMT-4 adapter; `Scheme` and `Embedding` registry (landmark-index-correspondence 🧠); pack loader with hash refusal; defaults as `{value, sigma, unit, badge, source}` |
| `fit/template.py`, `fit/silhouette.py` | extend | Barycentric embeddings; `ContourObs` kinds, normal-only residuals, EDT instead of the O(M·P) matrix, gates in IOD units (face-segmentation-contours 🧠) |
| `fit/{stages,refine,cranium,ear}.py` | new | Stage gates; offsets with caps; vault parameters; ear part model |
| `mesh/core.py`, `mesh/laplacian.py` | extend | Topology hash and CSR faces; per-vertex smoothness weights |
| `texture/{raster,project}.py` | new | UV G-buffer and z-buffer; weights, gains, blending |
| `qa/{metrics,report,overlay_geom,checks}.py` | new | Metrics; cards; overlay mapping; photo checks returning `{code, severity, value, threshold, msg_key, fix_key}` |
| `guidance/`, `handoff/keys.py` | new | Checklists, measurements and warnings, generated from `research/data/*.json`; key-stack and rebase maths |
| `project/{schema,consent,licence,capture,audit}.py` | new | Project file, gates, taint, capture manifest, JSONL audit |
| `io/exif.py`; `io/landmarks_json.py` | extend; new | Adds HEIC, zoom and native-frame tags; reader for the helper's JSON |
| `synthetic.py`; `eval/{surface,coverage}.py` | extend; new | Procedural pack and scenarios; NoW-style alignment, NEES and reliability curves |
| `face3d_blender/` | new | `blender_manifest.toml`, `bridge.py` (the sole bpy↔numpy module), `compat.py`, `props.py`, `jobs.py`, `keymap.py`, `ops/`, `tools.py` (pin `WorkSpaceTool`), `ui/{panels,overlays,palette}.py` |
| `tools/landmark_helper/`, `tools/template_pack/` | new | MediaPipe Tasks script that writes JSON; pack builder and annotation checks |

### 2.3 Data flow

1. **Ingest.** `capture.ingest` reads EXIF, bakes orientation, hashes and runs `checks`, then assigns lens groups.
2. **Landmarks.** From the helper JSON, from pins, or both.
3. **Initial solve.** `pnp`, then `live`, then `observability`. Artist pins feed back into `live`.
4. **Refinement** (stages B–D). With cameras frozen, `bundle` produces 3D targets. `reduced`, `silhouette`, `cranium` and `refine` then deform the mesh.
5. **Hand-off.** `qa` → `handoff.keys` → bridge → (texture) → export with provenance.

### 2.4 Data formats

**Project folder** (`<name>.face3d/`, next to the `.blend`, which stores only its path). Purges act by data class (ethics 2.2).

```json
{"schema_version":"1.0","consent_id":"…","commercial_intent":false,
 "photos":[{"sha256":"…","working_copy":"photos/p01.png","crop":null,"zoom":1.0,"focal_group":"Make|Model|Lens|f|W|H|still",
   "view_tag":"front","rights_basis":"self_shot","risk":{"front_cam":false,"portrait_mode":false},"checks":[]}],
 "pins":[{"photo":"…","xy_px":[1012.5,884.0],"target":{"tri":4411,"bary":[0.2,0.5,0.3]},"cls":"crisp",
   "sigma_n_mm":1.2,"sigma_t_mm":1.2,"source":"user","expertise":"novice","zoom_at_place":4.0,"blind":true}],
 "active_solve":"solves/0007","template":{"topology_id":"minehead-v1","topology_sha256":"…"},
 "settings":{"rigidity":0.5,"symmetry":"assist"}}
```

- Pins are artist work. They persist under RECONSTRUCT consent, like camera solves (ethics 2.2).
- Raw detector output is a cache with `cache_ttl_days = 0`.

**Landmark scheme** (`model/schemes/<scheme>.json`). It records index semantics only, independent of any mesh:

```json
{"scheme":"mediapipe_478","n":478,"detector":{"model_sha256":"<pinned>","licence":"Apache-2.0","commercial_ok":null,"is_ml":true},
 "image_convention":"px, top-left pixel corner, y down","mirror_perm":"computed","midline":[],
 "semantics":{"1":{"name":"prn","kind":"extremal","sigma_n_mm":2.0,"sigma_t_mm":3.0,"verified":false,"badge":"🧠"}},
 "polylines":{"lid_upper_R":[]},"iris":"bind_to_limbus_model","z_policy":"ignore"}
```

- `mirror_perm` and the iris left/right assignment are derived geometrically at load time, never taken from a table (landmark-index-correspondence 🧠).
- Entries marked `verified: false` act only as generic curve or contour samples.

**Template pack** (`templates/<topology_id>/pack.json` + `.npz`). The schema follows open-template-head-kit 🧠:

```json
{"topology_id":"minehead-v1","topology_sha256":"…","units":"m","axes":{"up":"+Z","face":"-Y","left":"+X"},
 "licence":"CC0-1.0","derived_from":[{"name":"MPFB2 hm08","sha256":"…"}],"submeshes":{"eyes":[0,0]},
 "mirror":"mirror.npy","landmarks":{"anatomical":{},"mediapipe_478":{}},"contours":{"jaw_rings":[]},
 "regions":{},"bases":{"hm08_targets":{"file":"U.npz","sigma":"calibrated","commercial_ok":true,"bundle_ok":true}}}
```

The loader converts the declared units and axes into engine mm (INV-2).

**Solve result** (`solves/NNNN/{result.json, arrays.npz}`, FMT-8 and D6). Contents:
- per-view cameras `{R, t, f, k1, model, sigma_logf, observable}`;
- β, θ_v, ψ_v, vault parameters and ear θ/α;
- per-stage vertices;
- the support map, per-vertex σ in mm, and σ_scale;
- `scale_mode`, QA findings, the licence union, the consent ID, versions and seed.

Solves are immutable; *Revert* re-activates an older one.

### 2.5 Coordinate conventions

| Space | Convention |
|---|---|
| Head | mm, float64; +x = subject's left, +y up, +z out of the face; FH-levelled (R1.1) |
| Camera | OpenCV; X_c = R·X + t |
| Image | px from the top-left pixel corner (pixel centres at i + 0.5); MediaPipe u = x_norm·W |
| Blender | The head and cameras sit under one empty with R_x(+90°) and scale 0.001. Engine (x, y, z) mm maps to Blender (x, −z, y) m: the face looks along −Y and `.L` is +X (A8). `to_blender_camera` exists (C4) |
| UV | Origin at bottom-left; `img.pixels` rows run bottom-up; texel centre at (i + 0.5)/N |
| L/R | Always the subject's side (R1.2) |

### 2.6 Assets: obtained and verified, never fabricated

**Template: `minehead`** (open-template-head-kit 🧠/📄).
- A project-owned quad head, released CC0, re-authored from a CC0 source:
  - the hm08 crop (CC0 📄). This keeps the targets and the MPFB rig round trip through `head_to_hm08`; or
  - the Blender Studio Human Base Mesh (CC0 ✅), if it passes topology QA better.
- `tools/template_pack/build.py` takes a pinned source and checks its SHA-256.
- Topology QA (face-retopology 🧠): no non-quads in deforming zones; poles at least 2 rings from lids, lips and alae; an exact x = 0 midline.
- The builder also writes:
  - a mirror bijection with M(M(i)) = i;
  - contour rings;
  - sub-mesh bindings for eyes and teeth.
- hm08 targets are transferred barycentrically.
- If the face has fewer than 6k quads, the builder adds one Catmull–Clark level (W4).

**Anatomical embedding.**
- Two annotators work in a developer panel, from definitions in craniometric-landmarks.
- Acceptance: agreement within 1.0 mm (en, ex, ch, sn) or 2.5 mm (g′, zy′, go′) (R4.1). Otherwise the points are adjudicated.
- The annotators' spread is added to σ_def.
- Extremal points (zy, go, eu, v, op) are stored as candidate sets plus a rule.

**MediaPipe → template.**
- Maintainers register the SHA-pinned Apache-2.0 canonical mesh to `minehead` with our own NICP (MM-12), seeded by about 20 hand pairs.
- A render-and-detect check locks the table: render the template, detect, and compare offsets. The offset is shrunk as w = n/(n + 2) (landmark-index-correspondence 🧠).
- If the CC0 rule forbids shipping the Apache-derived table (ethics C7), it is built on the user's machine on first run instead.

**Tests** use a procedural pack from `synthetic.py`. Tests that need the real assets skip when the pack is absent.

---

## 3. Algorithms

### 3.1 Joint objective (live A-space)

**Parameters.** p = {ω_v, t_v} ∪ {ℓ_g = log f_g} ∪ log s ∪ β ∪ {θ_v} ∪ {ψ_v}.

**Landmark positions.** X_i = s·(X̄_i + B_iβ), with X̄_i and B_i precomputed (MM-2).

**Energy.**

E = Σ_v w_v Σ_i ρ(‖L_vi⁻¹(π_v(X_i) − u_vi)‖) + E_curve + E_contour + E_pin + E_shape + E_sym + E_cam + E_scale + E_vault

**Noise model** (mm, mapped to px at each view's depth).
- Per-kind σ (landmark-index-correspondence 🧠):

| Kind | σ_n | σ_t |
|---|---|---|
| Sharp junctions | 1.0–1.5 | 1.0–1.5 |
| Extremal points | 1.5–2.5 | 2–4 |
| Curves | 1.0–2.0 | free |
| Oval | 2–3 | free |
| Brows | 3–5 | free |

- Contours use Σ = R·diag(σ_n², σ_t²)·Rᵀ.
- Full variance: σ² = σ_kind² + σ_def² + (px/mm·σ_px)².
  - σ_def is a per-landmark definition-bias floor of 0.5–2 mm, shared across views so it does not shrink as views are added (validation-test-bed 🧠).
  - MediaPipe σ is inflated by √(N/N_eff), N_eff 60–100.
- User pins: σ = √(σ_class² + σ_motor²) (guided-workflow-accessibility 🧠).
  - σ_class: crisp 0.8 mm (expert) or 1.2 mm (novice); prn 2.0; palpation points 4–5.
  - σ_motor: one screen px at the placement zoom.
  - The default is the novice column. The old 0.75 % IOD over-weights novices 3–30×.
- Iris centres move with gaze: they are never shape landmarks.

**Robustness.**
- Huber δ = 2, then a Tukey round, then outliers rejected at 3.03σ (1 % false alarm).
- A view is rejected above its 99 % reduced-χ² bound (validation-test-bed 🧠).
- View weights are 1/n_bin, and no view may carry more than 40 % of the total (R1.8 🧠).

**Solver.** LM (exists) with a multiplicative rotation update. With P ≈ 110 parameters, each mouse event runs 2–5 warm iterations.

### 3.2 Camera initialisation and per-view models

**Focal hypotheses.** f_h = f35_h·√(W² + H²)/43.27 for f35 ∈ {13, 24, 26, 35, 50, 77, 85, 120, 135, 200}. Each hypothesis gets affine initialisation, LM, and pitch-flip and yaw-mirror restarts. The best robust score with every z_c > 0 wins (CAM-3 🧠).

**Focal priors** (CAM-6, R2.2, smartphone-camera-pipeline 🧠), σ on log f:

| Source of f | σ |
|---|---|
| Uncropped 4:3 EXIF | 0.04 |
| Zoom crop detected (c = f35/FocalLength exceeds the lens mode by >2 %) | 0.06 |
| Native-frame ambiguity | 0.09 |
| Phone without EXIF (26 mm) | 0.25 |
| Unknown (50 mm) | 0.6 |

- Views in one focal group are tied with σ 0.02.

**Per-view camera model.**
- Main or tele lens, face within 25° of centre: k = 0.
- Front camera, or face beyond 25°: k1 ~ N(0, 0.02²).
- Ultra-wide or edge-of-frame face: a local virtual camera with f′ = f·sec²(θ/2), or σ_px ×3.

**Distance prior.** Z ≈ f_px·88 mm / outer-IOD_px (±6 %) on near-frontal views, or a tape measurement (σ 5 cm, R2.4). Hard bounds 0.25–10 m.

**Pose-tag priors** (R2.7 🧠): yaw σ 10°, pitch 5°, roll 3°.

### 3.3 Observability

Σ = (JᵀWJ + Λ_prior)⁻¹ at the optimum. Reported values:
- **Focal length.** σ_ℓ = √Σ_ℓℓ. Focal is freed only when σ_ℓ < 0.10 and yaw spans ≥60° (C2, R2.3). Above 0.8× the prior σ, the card reads "Lens not measurable from these photos; using EXIF."
- **Perspective.** P = 100 mm / z.
- **Radial slope.** A radial-residual slope implying more than 5 % magnification error raises "focal or distance may be wrong" (R2.8).
- **Fit quality.** Reduced χ² = 2·cost/(m − n). The covariance is inflated by max(1, χ²_red) before anything is displayed.
- **Scale.** Shown separately ("size ±3 %"), because free-point BA is 2–4× overconfident about scale (validation-test-bed Table 5 🧠).

### 3.4 Shape prior and rigidity

**Default `TargetSpace`** (open-template-head-kit 🧠/↔️).
- Each hm08 modifier is split into two non-negative columns, c⁺ and c⁻ ∈ [0, 1], with a penalty λ·c⁺c⁻ so the fit cannot use both at once.
- An optional mass-weighted SVD keeps K ≈ 40–80 modes.
- σ is calibrated by moment matching against about 25 Farkas measurements: min ‖JΣ_cJᵀ − Σ_m‖_F with Σ_c ⪰ 0, where J = ∂m/∂c.
- The resulting prior describes proportions, not detail. The UI says "guessed from average proportions", never "typical of people like the sitter".

**Rigidity.** E_shape = ½λ(r)·cᵀΣ_c⁻¹c, with λ(r) = 10^(2r−1) (facebuilder-blender 🧠). The slider is labelled in words, from "Stay close to an average head" to "Follow my pins exactly".

**Opt-in `Flame2023OpenSpace`.**
- Loaded from a user path and recorded in `ATTRIBUTION.txt`.
- β ~ N(0, I) with K growing from 20 to 50 (MM-3).
- ‖β‖² above χ²_K(0.999) is flagged; that bound is 86.7 at K = 50 (MM-5).

**Other priors.**
- Global scale: log s ~ N(0, 0.045²) until verified (validation-test-bed 🧠). It is overridden by calipers, an ID-1 card, or the iris (only when the limbus is sharp).
- Per-landmark σ arrays replace the scalar 8 mm (R4.1).
- Ratio priors stay weak (R4.3).

### 3.5 Curves, contours, silhouettes, cranium, ears

**Curves** (lids, lips, brows).
- r = n̂ᵀ(u − π(γ(s*)))/σ_n, with s* re-associated every iteration on the projected template polyline.
- σ_t = 3–5 σ_n, or free.

**Silhouette observations** (face-segmentation-contours 🧠). Each `ContourObs` has a kind:
- `hard` (skin|background): r = nᵀ(π(X_c) − x)/σ_n;
- `outer_bound` (hair, beard, hat): max(0, r);
- `inner_bound`: max(0, −r).

**Silhouette pipeline.**
- **Model contour.** Taken from n·v zero-crossings on edges, restricted to the template's contour rings and visibility-tested.
- **Matching.** Pairs are re-matched every outer iteration and gated at 0.15·IOD_px, shrinking to 5σ_n. Pairs whose normals differ by more than 30–45° are rejected.
- **Normal-only update.** Only the normal component is applied. Today `fit_silhouettes` back-projects the full 2D correction and drifts along the contour; this is the main fix to that module.
- **Noise.** σ_n² = σ_edge² + (0.5·s_model)² + σ_blur², floored at 0.005·IOD_px and inflated for correlated samples.

**Mask sources.**
1. User lasso.
2. MediaPipe oval.
3. Optional helpers: MediaPipe selfie, multiclass and hair segmenters, or SAM 2 (all Apache-2.0; weights re-checked). Parsers trained on CelebAMask or LaPa never run.

**Cranium** (cranium-under-hair 🧠).
- Vault parameters L = g′–op′, B = eu′–eu′ and H = t–v. Log-normal σ: 0.035, 0.037 and 0.045 for a matched population; 0.05 for L and 0.065 for B when ancestry is unknown (never inferred: the user picks "unknown").
- Hair outlines act as `outer_bound`, weighted ≥10× the skin terms.
- Hairline, parting and nape points are skin points with σ 1–2 mm.
- A slicked-hair view becomes `hard` (σ 1.5–3 mm).
- The tape-measured circumference becomes an arc-length term (σ ≈ 4 mm plus hair).
- The face is never stretched to fit the vault.
- Any parameter with |z| > 3 on L, B or circumference raises "check scale or focal length".

**Ears** (ear-reconstruction-sculpting 🧠).
- Each ear is its own part: E = R(θ)·s·(ē + Uα) + t, hinged on otobasion and anchored at tragion. θ covers tilt N(20°, 7°), protrusion N(25°, 8°) and twist N(0°, 6°).
- U is a set of hand-authored CC0 ear keys; research ear models are never used.
- Ears get weight 0 when |yaw| < 30° or when hair is detected over them.

### 3.6 Expression and mirror handling

**Checks** (guided-workflow-accessibility Table 1 🧠), each compared against the photo the user marks as most neutral:

| Signal | Warn | Exclude |
|---|---|---|
| mouthSmile | >0.25 | >0.5 |
| jawOpen | >0.10 | >0.25 |
| eyeBlink | >0.4 | >0.6 (lids ignored) |
| L2 drift of the 52-score vector | >0.4 | >0.8 |

Warned views get identity weight ×0.25.

**Default path (no expression basis).**
- Identity comes from neutral views only.
- Open-mouth views drop their lip points; squints drop their lid points (R3.7).
- A per-view jaw hinge absorbs small openings: x′_j = x_j + ω_j(R(θ_v·a)(x_j − c) − (x_j − c)), where c lies 10–13 mm anterior to tragion (BA-1 🧠) and θ_v ~ N(1.5°, 1°²).

**With a basis.** X_v = X + Eψ_v, with a neutral anchor ‖mean_N ψ_v‖/0.1 (BA-9).

**Mirror test.**
- The cost E_v is compared against E_v^flip, the cost with the image flipped (u → W − u) and L/R labels swapped.
- Front-camera views are suggested for flipping when the relative margin exceeds 10 % (smartphone-camera-pipeline 🧠); other views at 30 % (guided-workflow-accessibility 🧠).
- The margin must also exceed the χ² noise of 2√(2n_v), a derived threshold. Otherwise the card reads "can't tell".
- Images are never flipped automatically.

### 3.7 Warp schedule and asymmetry

**Stages** 0 → A → B → C → D (W1, R5.1).

| Leave stage | When (R5.2 🧠) |
|---|---|
| A | landmark RMS < 4 % IOD and chamfer < 2–3 mm |
| B | RMS < 3 % IOD in every view, the held-out view included |
| C–D | (constraint while running: no landmark moves more than 0.5 mm) |

**Targets.** With cameras frozen, `bundle_adjust` triangulates X*_i, Σ*_i against the model, with prior σ 8 mm in stage B and 3–4 mm in C. Silhouettes back-project along the normal.

**B.** A reduced Gaussian deformer: d(x) = Σ c_j·exp(−‖x − x_j‖²/2s²), s = 30–40 mm, solving (ΦᵀWΦ + μK)c = ΦᵀWd with W = Σ*⁻¹.

**C.** min ‖diag(√w_s)·L·d‖²_M + Σ w_c‖x_c + d_c − p_c‖².
- w_s (R5.9, W3 🧠): ligaments ×3–5, lid margins ×3, lips ×0.3; lids, lips, nostrils and ears ×5 for edge flow.
- |d| is capped at 3–5 mm unless at least 2 views agree (MM-10).
- Gates: quad angles 30–150°, aspect ratio ≤ 4, det J > 0.2 (MM-11).

**D.** Only where at least 2 views agree.

**Cross-check.** If X* and the model differ by more than 3σ, the card reads "photos say more than the template can express – sculpt here", and the region joins `f3d_sculpt_here`.

**Symmetry.** E_sym = Σ‖D_p⁻¹(X_l − M·X_r)‖² with per-pair σ (R4.2 🧠):

| Pair | σ |
|---|---|
| canthi | 0.7–1.0 mm |
| alare | 1–1.5 mm |
| cheilion | 1.5–2.0 mm |
| gonion | 2.5–3.0 mm |
| ears | 3–4 mm |

- Full weight applies only in "guessed" regions; elsewhere ×0.25.
- The symmetry plane is refit by weighted reflection Procrustes (R3.3).
- The output is never symmetrised. S = ½(X + M·X_m) and the `Asym` key = X − S (R5.9).
- A face is flagged as too symmetric when its mirror RMSD < 0.3 mm against asymmetric photos.

### 3.8 Detail refinement

- **Shape vs displacement.** Shape is resolved to wavelengths of about 5 mm. Anything finer goes to displacement, gated by mm per px: pores ≤ 0.033, fine lines ≤ 0.08, line positions ≤ 0.25 (R5.11 🧠).
- **Default: guides, not detail.** No photometric detail is added. The default produces sculpt guides instead:
  - per-region best-view projection stencils;
  - crease curves from image edges that reproject within 2σ in at least 2 views;
  - `f3d_support`.
- **Optional SH9 refinement** (OPT-1) is labelled *estimated*.

### 3.9 Texture projection

**Gates.** TEXTURE consent, a known rights basis, and reprojection within 1.5 px median and 3 px max (T2).

**Visibility.** vis = [z_v(p_t) ≤ zbuf + ε], with ε = max(1 mm, 2σ_geom) (TEX-1).

**Weights.** w = vis·cos²θ·fade(60° → 75°)·footprint·edge (TEX-2 ↔️).

**Gains.** log I_v = log g_v + log a, subject to Σ log g_v = 0 (TEX-3). Views lit directionally get a gain only.

**Blending.** `two_band`. The low band comes from a 3 mm UV-space blend, the high band from the best view. Mirroring applies to the low band only; detail is never mirrored (TEX-4, TEX-5).

**Outputs.** Linear albedo, a confidence map and a view index. Without a colour chart, the result is labelled "absolute colour unknown".

### 3.10 Coaching: next best photo

The candidates are the pose-ring bins: yaw {0, ±20, ±45, ±90}, elevation {−25, 0, +25}.

For each candidate:
1. Predict its Jacobian J_c.
2. Marginalise the candidate's own pose by Schur complement: H′_ββ = H_ββ + J_βᵀWJ_β − J_βᵀWJ_p(J_pᵀWJ_p)⁻¹J_pᵀWJ_β.
3. Score it: Δ_c = Σ_r w_r[tr_rΣ − tr_rΣ′_c], with tr_r(Σ) = Σ_{j∈r} tr(S_jΣS_jᵀ).

The weights w_r rank regions by perceptual importance (face-perception-likeness Table B 🧠):

| Region | w_r |
|---|---|
| lids | 1.0 |
| brows | 0.9 |
| lips | 0.8 |
| nose | 0.7 |
| ears | 0.1–0.2 |

The winning candidate is shown as one sentence: "Next: left profile, eye height, 1.5–2 m".

Nose and chin projection count as measured only with a front view plus one at |yaw| ≥ 60° (R5.9).

### 3.11 QA in plain language

Support for region r is s_r = 1 − tr_rΣ_post/tr_rΣ_prior.

| Metric | Shown as | Threshold (source) |
|---|---|---|
| s_r | **measured** / **partly** / **guessed** (hatched) | ≥0.7 / 0.3–0.7 / <0.3 (guided-workflow-accessibility 🧠); a view is requested when s_r < 0.8 on a top-5 region (anatomy §6) |
| per-vertex 2σ | "likely within ±X mm" | inflated by χ²_red |
| Leave-one-view-out (LOVO) | "This photo disagrees by about 1.5 mm" | held-out error > 2× in-sample |
| ‖c‖² < K − 2√(2K) | "Pulled toward average" | R5.8 🧠 |
| Mirror RMSD | "Too symmetric" / "Unusually asymmetric – check pose" | <0.3 / >1.5 mm |
| IPD, g–op, breadth | "Scale looks wrong" | 55–72 / 182–200 / 140–160 mm |
| Interior fits but contour off | "Lens or distance wrong, not the face" | SIL-3 |
| det J ≤ 0.2 | "Surface folded – raise Rigidity" | MM-11 |
| Over-pinning | "Too many pins here" | >3–5 per feature per view, or one view holding >60 % of pins (guided-workflow-accessibility 🧠) |

---

## 4. Blender add-on design

### 4.1 Manifest and permissions

```toml
schema_version = "1.0.0"
id = "face3d_likeness"
version = "0.1.0"
name = "Face3D Likeness"
tagline = "Fit a sculpt-ready head to consented photos"
maintainer = "Face3D contributors <maintainers@example.invalid>"
type = "add-on"
blender_version_min = "4.5.0"
license = ["SPDX:GPL-3.0-or-later"]
copyright = ["2026 Face3D contributors"]
tags = ["Sculpt", "Modeling", "Camera"]
[permissions]
files = "Read reference photos and write project and landmark files"
```

**Contents and permissions.**
- No wheels ship. Blender's own NumPy is used, so one zip serves every platform.
- The bundled assets are CC0 only: `minehead` and its targets (open-template-head-kit 📄).
- `network` is not declared until a consented downloader exists (ethics A3).
- The minimum Blender version is set to the oldest one CI tests (packaging ↔️). The engine itself runs on Python 3.11 and 3.13, with NumPy 1.26 and 2.x (A4).

**Landmark detection: three paths.**
- **Path A (default):** the helper runs in a venv the user creates and writes JSON. There is no pip at runtime.
- **Path B:** an optional platform-split onnxruntime build.
- **Zero-download path:** manual pins plus imported JSON (ethics A4).

### 4.2 Panels: a guided rail

The **Face3D** sidebar tab holds a Guide panel with ten stages:

> Consent → Photos → Check → Landmarks → Cameras → Shape → Confidence → Sculpt → Texture → Share

**Each stage shows:**
- an icon plus a word: Done, Needs attention or Not started;
- a "done when" line;
- one primary button, gated by `poll()`, with `poll_message_set` explaining why it is greyed out ("2 photos still have blocking issues");
- a *Why?* link.

**Expert options** sit in sub-panels collapsed by default (`DEFAULT_CLOSED`) and expose:
- σ values and badges;
- symmetry mode (assist / prior / enforce);
- expression mode (off / jaw / basis);
- focal mode per group;
- *Revert to solve #n*.

**Optional onboarding** (2 minutes): the user places 6 crisp landmarks twice, from which their personal crisp σ is computed:
- σ_rep = RMS(Δ)/√2
- σ_crisp = max(σ_rep + 0.3, 0.5) mm

(guided-workflow-accessibility 🧠).

### 4.3 Operators and keymap

- Every operator is REGISTER + UNDO.
- Errors go through `self.report`; no traceback reaches the user.
- All keys can be remapped through `keyconfigs.addon`, and every operator is findable with F3.

| Operator | Key | Notes |
|---|---|---|
| Pin tool (`WorkSpaceTool`) | P | Click places a pin; drag moves it, with an offset loupe; Shift-drag moves at ¼ speed. Arrows nudge 1 px (Shift: 0.25 px). X deletes. H / Alt-H hide and reveal. The status bar shows hints |
| `face3d.review_next` / `_prev` | Tab / Shift-Tab | Spell-checker queue sorted by normalised residual. Each item shows the landmark's plain name, an illustration and its epipolar line |
| `face3d.view_next` / `_prev` | PageDown / PageUp | Also bound to timeline markers |
| `face3d.solve_refine` / cancel | Ctrl-R / Esc | Esc keeps the last good state |
| `face3d.card_accept` / `_dismiss` | Ctrl-Enter / Ctrl-Backspace | The focused card |
| `face3d.compare_flip` (hold), `_blur`, `_grey`, `_edges` | F, B, G, E | R8.1 likeness aids |
| `face3d.wobble` | W | 8–12 posterior samples, stepped manually or at ≤1 Hz |
| `photos_add`, `landmarks_detect`, `landmarks_import`, `handoff_sculpt`, `rebase_sculpt`, `texture_project`, `report_export`, `prepare_for_sharing`, `purge` | — | Each is gated by consent |

### 4.4 Overlays and accessibility

Overlays are drawn by `gpu` POST_PIXEL handlers using `POLYLINE_*` shaders, so wide lines survive Metal and Vulkan. Sizes are multiplied by `ui_scale`. The mapping maths lives in `qa/overlay_geom.py`, which keeps it testable without Blender.

**Glyph encoding.** Okabe–Ito colours, from Table 4 of guided-workflow-accessibility 🧠:

| Element | Colour | Shape |
|---|---|---|
| Auto pin | #56B4E9 sky | circle |
| User pin | #E69F00 orange | square |
| Conflict >3σ | #D55E00 | ✕ with residual line |
| Selected | #F0E442 | 2 px ring |
| Model contours | #009E73 | polyline |
| Guessed region | #CC79A7 | hatching |
| Residuals | cividis bins <1 / 1–2 / 2–3 / >3σ, labelled | — |

**Legibility on any photo.**
- Every glyph has a dark outline and a light halo, giving ≥3:1 contrast on any skin tone (WCAG 2.2).
- Pins are 9 px with a 12 px hit radius, and the target area is at least 24 px.

**Motion.** Nothing moves on its own:
- Flip-compare is hold-to-view. It replaces the 3 Hz blink of R8.1, which falls in the photosensitivity range 🧠.
- Live re-solve can be switched to "on release" for users who find the moving surface confusing (↔️, to be A/B tested).

**Text access.** Strings go through `bpy.app.translations`. Blender exposes nothing to screen readers, so every finding is also written to the Info log and to the exported HTML/text report.

### 4.5 Undo, history, background jobs

**Writing.**
- `foreach_get` → float64 → `foreach_set` and `mesh.update()`, in OBJECT mode with the previous mode restored.
- Writes are refused on a hash mismatch or while in Edit Mode (A3, K1, K4).

**Undo.**
- During a drag, the live preview goes into a muted `f3d_live` key from a timer, so it stays off the undo stack.
- Release pushes one `undo_push("Move pin")`.
- Pins live in PropertyGroups, never in Python globals. After an undo, an `undo_post` handler re-resolves IDs by name and re-runs the live solve (A5).

**Background jobs.**
- Short solves: a worker thread on copied arrays.
- Refine and texture: a `sys.executable -I` subprocess exchanging `.npz` files.
- A modal timer applies results at 30–50 ms of work per tick.
- Under `blender -b` everything runs synchronously.

### 4.6 Shape keys and Multires hand-off

**Key stack** (K2, SK-1):

| Key | Content |
|---|---|
| `Basis` | template mean |
| `ID_fit` | symmetric fit; `slider_max` 1.5, values >1 are a caricature preview (R5.8 ↔️) |
| `Asym` | the subject's asymmetry |
| `artist` | sculpt layer |
| `stage_*` | muted diagnostics |

Per-photo expression keys are written only under RIG_ANIMATE consent (ethics F4).

**Rebase after a refit.** The artist's work is carried forward: new `artist` = old `artist` + (new `ID_fit` − old `ID_fit`). Writes to `Basis` add Δ to every dependent key (K3).

**Sculpt copy.**
- Bake the key mix and clear the keys.
- Add Multires L2 (likeness) and L3 (detail) (SK-3).
- Keep the fit snapshot hidden.
- Later refits go through `multires_reshape` (K5). Whether sculpted detail follows the base is unverified (blender Q4): a test scene guards this, and the fallback is a fresh copy.

**Also written.**
- 15–25 region vertex groups and face sets.
- Point attributes `f3d_support` and `f3d_sigma_mm`.
- A *Protect measured regions* operator that copies (1 − support) into `.sculpt_mask`, a FLOAT attribute since 4.1 (📄).
- `cranium_confidence`.
- Brow and hairline curves.
- Rigid 24 mm eyes.
- One locked camera per photo, with a background image (α 0.4) on its own marker, and "Lock Camera to View" off (sculpting-likeness-workflow 🧠).

**Sculpt mask back to the engine.** A painted mask m becomes data weight (1 − m) plus a pin term at σ 0.2 mm (W5).

**Rig path.** `head_to_hm08` allows the head to go back to MPFB as a `.target`. From there, MPFB or Rigify rigs and ARKit-named tools apply.

### 4.7 From anatomy research to in-app guidance

- **Capture checklist.** Generated from R1.4, reference-photography-protocol and cranium-under-hair:
  - hair off the ears;
  - glasses off 10–15 minutes before shooting;
  - gaze fixed on a mark;
  - camera at eye height, at least 1.5 m away;
  - phone on the 2–5× lens;
  - no portrait or beauty modes;
  - optionally, a cap or slicked-hair photo and tape measurements.

  Items tick automatically once the photo checks confirm them.
- **Likeness checklist.** Ordered by perceptual rank: lids → brows → lips → eye spacing → nose → thirds → jaw and hair → age → ears (face-perception-likeness 🧠). Each item opens its best camera.
- **Measurement panel.**
  - Measurements: en–en, ex–ex, al–al, ch–ch, n–sn, sn–sto, n–gn, zy–zy, go–go, g–op, eu–eu, ear length, and the nasolabial, gonial and cervicomental angles.
  - Each shows value ± 2σ, plus its support level.
  - A population z-score appears only when the method and landmark variant match the norm (R1.3, R2.2).
  - Caliper entries become constraints: E_cal = Σ((‖X_a − X_b‖ − d − o)/σ)² (R5.7).
  - |z| > 2.5 in an unobserved region produces a note, never a correction (R8.2).
- **Warning catalogue** (`guidance/warnings.toml`). Each entry has: problem → why → fix → source and badge. Example: "Photo 3 was taken from about 40 cm, so the nose will come out too large. Retake from 1.5 m or more and zoom in. [Use for texture only] [Keep]". The ordering hinges (R5.2) are included.
- **Metadata.** Age, sex prior and BMI are optional, explained, and never inferred. Ancestry is never asked (R2.7, R7.4).

---

## 5. Validation and QA

### 5.1 Automated tests (CPython + pytest, no Blender)

Tier 1 of the validation-test-bed 🧠 runs on every push: 30 fixed seeds, with medians compared against stored baselines ± 3 MAD.

- **Q1 (camera solve).** Noiseless reprojection error < 1e-6 px. With σ = 1 px noise, RMS ≈ σ√(1 − p/n), failing above 1.2σ.
- **EV-5 (range sweep).** Over z 0.25–5 m and f35 13–200 mm: focal error < 5 % and rotation error < 2° when yaw spans ≥60° (R8.4 🧠). Frontal-only sets at ≥2 m must report "not observable".
- **Phone cases** (smartphone-camera-pipeline 🧠). A synthetic k1 sweep, a stereographic edge warp, a 16:9 static-tag crop and a mirrored front view must each select the correct camera model, with shape error < 1 mm.
- **Behaviour.**
  - Contours slide without tangential drift.
  - The outer-bound hinge never pulls inward.
  - Stage gates and the 0.5 mm landmark freeze in C/D hold.
  - Fold gates catch inversions.
  - Vault parameters recover within ±3 mm (controlled hair) and ±6 mm (dry hair) (cranium-under-hair 🧠).
- **Hand-off.** Rebase preserves `artist − ID_fit` to 1e-9. Basis-Δ propagation and topology refusal are tested.
- **Texture.** TEX-8: gains recovered within 2 %, and no colour leaks onto occluded texels.
- **Policy and packaging.** Consent gates; licence taint computed as an AND over components; a socket guard (ethics A7); an AST check that no module under `face3d/` imports bpy; a `tomllib` manifest lint (tagline ≤ 64 characters, SPDX identifiers); an SPDX row for every bundled file.
- **Blender smoke scripts** (`blender -b --factory-startup --python-exit-code 1`, Q3) run in an optional external CI.

### 5.2 Honest uncertainty

**Calibration targets** (validation-test-bed 🧠), over at least 30 seeds:
- similarity-aligned 1σ coverage between 0.60 and 0.76;
- NEES/dof between 0.8 and 1.25.

This includes a definition-bias case and a 5 % outlier case. A miss inflates the displayed ranges by the measured factor and says so.

**Tuning order.**
1. First tune the σ *ratios*, for accuracy.
2. Then tune the global σ scale, for coverage.
3. Screen the parameters (Morris), then validate leave-one-subject-out.

**Labels on every report.**
- `scale_mode`.
- "Not validated against a scan" until a tier-3/4 comparison exists.
- No claim finer than the capture modality allows (Q4).
- A count of the active 🧠 defaults.

### 5.3 Likeness checks for the artist

- A camera-matched overlay with an opacity slider.
- Compare modes: silhouette, edges, hold-flip, blur, greyscale, thumbnail. The blur is σ = 3 % of face width, which keeps the 8–16 cycles/face-width identity band (face-perception-likeness 📄).
- A held-out photo, chosen by the artist.
- A worst-first residual list in mm.
- The wobble view.
- A familiar-viewer sheet: photo vs render grid with 5 questions, consent-scoped. At least 5 people who know the sitter, blind A/B (guided-workflow-accessibility 🧠).
- Caricature preview S(α) = M + α(S − M), α 0.9–1.2, preview only (↔️).
- Identity-embedding scores are off by default (IDENTITY_CHECK, 1:1, RAM-only).

**Usability testing:** think-aloud with about 5 users per round over at least 3 rounds; summative SUS with 15–20 users, target ≥ 80.

---

## 6. Milestones

Each milestone ships alone and is accepted only by tests that run here.

| M | Ships | Acceptance |
|---|---|---|
| **M1 Honest camera solve** | `pnp`, `reconstruct` and `bundle` extensions (per-kind mm σ, σ_def, log-scale, full covariance, redescending round); `observability`, `mirror`, `report`; CLI `python -m face3d solve project.json` | Q1, EV-5 and phone cases pass. Mirror flagged in ≥95 % of seeded mirrored views with ≤2 % false flips. Coverage 0.60–0.76 and NEES/dof 0.8–1.25 for BA points and scale |
| **M2 Project, consent, capture** | `project/*`, `qa/checks`, pose ring, next-best-view, HEIC/zoom EXIF, helper with fixture JSON | Gate matrix (ethics F1–F20 where applicable); socket guard; profile is the top suggestion for frontal-only sets in ≥90 % of seeds |
| **M3 Template pack + staged fit** | `model/*`, `fit/{stages,refine,cranium}`, contour rewrite (EDT, kinds), pack builder tested on a fixture OBJ, synthetic pack | In-space subjects, face RMS ≤0.5 mm noiseless and ≤1.5 mm at realistic σ (7 views). Out-of-space subjects, stage C cuts RMS ≥30 % vs A. Profile error ≤1–1.5 mm at prn and pg (SIL-3). Vault tests pass |
| **M4 Extension MVP** | Manifest, bridge, cameras, landmark import, background Refine, `ID_fit` + `Asym`, static overlays, report | Manifest lint; AST bpy-isolation; overlay and key-maths tests; camera round trip ≤1e-6·s |
| **M5 Live pins + guided rail** | `solve/live`, pin `WorkSpaceTool`, review queue, epipolar lines, undo, palettes, cards, checklists, measurements, onboarding | Live within 1e-3 of batch. Keymap reaches every stage. Categorical palette pairs ΔE ≥ 20 under simulated deutan, protan and tritan vision (own target). Pin σ maths unit-tested |
| **M6 Sculpt hand-off + ears** | `handoff/keys`, sculpt copy, rebase, `.sculpt_mask` protection, markers, likeness aids, `fit/ear` with CC0 ear keys | Rebase exact to 1e-9; LOVO and held-out metrics; ear part recovers synthetic tilt and protrusion within their prior σ/3 from profile views |
| **M7 Texture + sharing** | `texture/*`, gates, provenance, *Prepare for sharing* | TEX-8; UV gates (T5); tainted exports blocked with the offending components listed |
| **M8 Opt-in statistical spaces** | FLAME 2023 Open adapter (attribution); research adapters behind warnings | χ² gates; `basis_sha256` refusal; default path still passes with the CC0 pack alone (L2) |

---

## 7. Risks and deliberate omissions

### Risks

1. **Defaults are mostly unverified.** Most σ values, gates and thresholds are 🧠. Mitigation: named defaults, coverage tests, the held-out photo, and test-bed tiers 2–4 before release [gap: metric-3d-landmark-reference].
2. **The prior is weak.** A moment-matched target prior constrains proportions, not shape detail, so fits can over-flex or shrink toward average. Mitigation: rigidity, shrinkage and χ² cards, the free-point cross-check, and M8.
3. **The template may need rework.** If `minehead` fails topology QA, it must be re-authored. The pack is a plug-in, so this is reversible.
4. **Annotation is a bottleneck.** Two annotators, render-and-detect locking, and `verified: false` down-weighting.
5. **Setup friction.** Creating the helper venv is hard for non-experts. Mitigation: manual pins and JSON import always work. MediaPipe and segmenter weight licences are ↔️.
6. **Live solving may be too slow.** Mitigation: solve on release, fewer iterations, a 100-point MediaPipe subset.
7. **Multires rebase** behaviour in 5.x is unverified (Q4).
8. **Rules may change.** Store rules (C7, C8), biometric law and AI Act Art. 50 may shift.
9. **Phones may alter geometry.** Beauty filters, generative zoom. Mitigation: processing-risk weights and consensus-ratio flags.

### Deliberately left out

- Neural single-image regression and AI meshes as identity sources (OPT-2 caps them at 25 %).
- Generative fill.
- Photometric detail by default.
- Hair strands, teeth and tongue.
- Expression rigs beyond ARKit-named hooks.
- The bone/soft-tissue two-layer model, which waits for a CC0 skull. Tissue thickness (FSTT) is used as guidance only.
- Auto-retopology.
- Phone depth and TrueDepth terms (phone-video-depth-capture 🧠). Video frames enter as 12–24 stills in one focal group.
- Research ear models.
- Cloud processing, telemetry, URL importers, 1:N search and anonymisation claims.
- Home-made encryption: we rely on OS-encrypted folders.
- Child priors by default. Minors need guardian consent, and widened child priors (R4.5) are opt-in.
