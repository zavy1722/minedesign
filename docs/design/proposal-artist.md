# Proposal: artist-in-the-loop photo → sculpt-ready head

*Design angle: UX-first. 2026-11-20. Builds on `face3d/` at 887c5e5 (42 tests pass).*

**Citations.**
- `(topic badge)` names a note in `research/<area>/`. IDs such as CAM-3 and R4.1 point into `research/_raw/requirements_*.md`.
- Every 🧠 or ↔️ number ships as a named, tunable default in `defaults.toml`, and the expert view shows its badge.
- Nine of the ten gap notes landed today and are cited by name. **[gap]** marks the missing one, metric-3d-landmark-reference.

---

## 1. Vision and the user journey

FaceBuilder sets the interaction bar: pins on any surface point, a live re-solve, and one camera per photo (facebuilder-blender 🧠). We rebuild that on open code and commercially clean data, and add what FaceBuilder lacks:
- the tool **says what the photos actually measured**;
- it **never overwrites the artist's work**;
- it **ends in Sculpt Mode**.

Automation speeds the artist up but never decides for them: every automatic decision arrives as a card with *why*, *what changes* and *undo*.

**Principles**
- **P1 Live, then thorough.** Adding a photo or dragging a pin re-solves cameras and coarse shape at ≥20 fps. If an update would take more than ~50 ms, it solves on release instead (guided-workflow-accessibility 🧠). Refinement runs in the background.
- **P2 Plain-language uncertainty.** Every number comes with a range in mm and a basis: *measured*, *partly measured* or *guessed from average proportions*.
- **P3 Non-destructive.** Originals stay untouched. Solves are immutable. Fit, asymmetry and sculpt are separate layers, and a refit never touches the artist's changes.
- **P4 Flags, not corrections.** Nothing the photos support is pulled toward a norm (requirements_anatomy §6).
- **P5 Accessible.** Overlays are shape-coded and colour-blind-safe, every action has a key, nothing moves on its own, and expert detail is opt-in.
- **P6 Consent first.** No stage runs without a consent record covering it (ethics §3).

**Journey:** 7–9 photos to a sculpt-ready head in ~20 min.

| # | Artist | System | Artist sees |
|---|---|---|---|
| 0 | Fills in the consent wizard | Writes a `ConsentRecord` | "reconstruct: yes; texture: no" |
| 1 | Opens the **Shot card** | Core views: front, ±45°, ±90°, low, high. Optional: a cap or slicked-hair view and 3 tape measurements (cranium-under-hair 🧠) | Diagrams; "phone: 2–5× lens, 1.5–3 m" |
| 2 | Drops photos in | Reads EXIF/HEIC, bakes orientation, groups lenses, runs photo checks | Each photo: icon, words, fix, *use anyway*; a pose ring |
| 3 | Runs **Find landmarks**, or places first pins blind (overlay hidden, to avoid anchoring) | Helper → PnP → joint solve | Cameras; a review queue |
| 4 | Works through the cards | Mirror, expression, distance, focal and zoom tests | "Photo 4 looks mirrored (selfie?). Flipping lowers error 34 %. [Flip] [Keep] [Show me]" |
| 5 | Drags pins | Live solve; epipolar lines | All views update; a next-best-photo hint |
| 6 | Clicks **Refine** | Stages B–D in the background | Result swaps in as one undo step |
| 7 | Opens **Confidence** | QA, measurements, held-out photo | Hatched guessed regions; a *wobble* of posterior samples |
| 8 | Clicks **Hand off** | Key stack, Multires copy, masks, cameras on markers | Sculpt Mode; ←/→ steps through photos |
| 9 | Texture and export | Gated projection; provenance | Albedo and confidence, or a blocked export with reasons |

---

## 2. Architecture

### 2.1 Layers

```
L4 face3d_blender/   GPL-3.0-or-later extension; the only bpy importer
L3 face3d/pipeline/  stages, live session, jobs-as-data, cards
L2 face3d/{solve,fit,texture,qa,guidance,handoff}/
L1 face3d/{geometry,mesh,model,io}/
L0 face3d/project/   consent, licence taint, data classes, audit
tools/  MediaPipe helper, template-pack builder, extension builder
```

The engine imports only numpy, math, json and tomllib, and is vendored into the extension (blender A1). The engine is MIT and the glue GPL, so the combined extension is GPL (ethics A1).

### 2.2 Modules

| Path | Status | Purpose |
|---|---|---|
| `geometry/{rotations,procrustes}.py`, `mesh/{reduced,sparse}.py`, `solve/triangulate.py` | exists | Kept; Procrustes gains a reflection mode (R3.3) |
| `geometry/camera.py` | extend | `from_blender_camera`; canvas offsets (C5); per-view model k = 0, k1 or local virtual camera (smartphone-camera-pipeline 🧠) |
| `geometry/rbf.py` | extend | λᵢ = α·σᵢ² (MM-8); sign already fixed in 0843516 |
| `solve/lm.py`, `solve/pnp.py` | extend | Normal matrix out, warm start, time budget; CAM-3 hypotheses, flip/mirror restarts, cheirality |
| `solve/bundle.py` | extend | Per-kind σ in mm, σ_def floor, global log-scale, full covariance, redescending last round (validation-test-bed 🧠) |
| `solve/reconstruct.py` | extend | Tiered focal priors; view-bin weights |
| `solve/{live,observability,expression,mirror}.py` | new | Reduced joint solver; posterior, support and next-best-view; neutral tagging and jaw hinge; flip test |
| `model/{shape_space,landmarks,template_pack}.py`, `defaults.toml` | new | FMT-4 adapter; `Scheme`/`Embedding` registry (landmark-index-correspondence 🧠); pack loader that refuses on hash mismatch |
| `fit/template.py`, `fit/silhouette.py` | extend | Barycentric embeddings; `ContourObs` kinds, normal-only residuals, EDT, IOD-relative gates (face-segmentation-contours 🧠) |
| `fit/{stages,refine,cranium,ear}.py` | new | Stage gates; capped offsets; vault parameters; ear part |
| `mesh/core.py`, `mesh/laplacian.py` | extend | Topology hash, CSR faces; per-vertex smoothness weights |
| `texture/{raster,project}.py` | new | UV G-buffer and z-buffer; weights, gains, blending |
| `qa/{metrics,report,overlay_geom,checks}.py` | new | Metrics, cards, overlay maths, photo checks returning `{code, severity, value, threshold, msg_key, fix_key}` |
| `guidance/`, `handoff/keys.py` | new | Checklists, measurements and warnings from `research/data/*.json`; key-stack and rebase maths |
| `project/{schema,consent,licence,capture,audit}.py` | new | Project file, gates, taint, manifest, JSONL audit |
| `io/exif.py`; `io/landmarks_json.py` | extend; new | HEIC, zoom and native-frame tags; reads helper JSON |
| `synthetic.py`; `eval/{surface,coverage}.py` | extend; new | Procedural pack and scenarios; NoW-style alignment, NEES |
| `face3d_blender/` | new | Manifest, `bridge.py` (sole bpy↔numpy module), `compat`, `props`, `jobs`, `keymap`, `ops/`, pin `WorkSpaceTool`, `ui/{panels,overlays,palette}` |
| `tools/landmark_helper/`, `tools/template_pack/` | new | MediaPipe Tasks → JSON; pack builder and annotation checks |

### 2.3 Data flow

Photos → `capture.ingest` (EXIF, orientation, hash, `checks`, lens groups) → landmarks (helper JSON and/or pins) → `pnp` → `live` ⇄ artist pins → `observability` → background `stages` B–D (frozen-camera `bundle` targets → `reduced` / `silhouette` / `cranium` / `refine`) → `qa` → `handoff.keys` → bridge → optional `texture` → export with provenance.

### 2.4 Data formats

**Project folder** `<name>.face3d/` sits next to the `.blend`, which stores only its path. Purges act by data class (ethics 2.2).

```json
{"schema_version":"1.0","consent_id":"…",
 "photos":[{"sha256":"…","working_copy":"photos/p01.png","zoom":1.0,"focal_group":"Make|Model|Lens|f|W|H|still",
   "view_tag":"front","rights_basis":"self_shot","risk":{"front_cam":false},"checks":[]}],
 "pins":[{"photo":"…","xy_px":[1012.5,884.0],"target":{"tri":4411,"bary":[0.2,0.5,0.3]},"cls":"crisp",
   "sigma_n_mm":1.2,"source":"user","expertise":"novice","zoom_at_place":4.0,"blind":true}],
 "active_solve":"solves/0007","template":{"topology_id":"minehead-v1","topology_sha256":"…"}}
```

Pins are artist work and persist under RECONSTRUCT consent. Raw detector output is a cache with `cache_ttl_days = 0`.

**Landmark scheme** `model/schemes/<scheme>.json` holds index semantics only:

```json
{"scheme":"mediapipe_478","n":478,"detector":{"model_sha256":"<pinned>","licence":"Apache-2.0","commercial_ok":null,"is_ml":true},
 "semantics":{"1":{"name":"prn","kind":"extremal","sigma_n_mm":2.0,"sigma_t_mm":3.0,"verified":false,"badge":"🧠"}},
 "polylines":{"lid_upper_R":[]},"mirror_perm":"computed","iris":"bind_to_limbus","z_policy":"ignore"}
```

The mirror permutation and the iris left/right assignment are derived from geometry at load time (landmark-index-correspondence 🧠). An entry marked `verified:false` acts only as a curve or contour sample.

**Template pack** follows the open-template-head-kit 🧠 schema. The loader converts the declared units and axes to engine mm (INV-2).

```json
{"topology_id":"minehead-v1","topology_sha256":"…","units":"m","axes":{"up":"+Z","face":"-Y","left":"+X"},
 "licence":"CC0-1.0","derived_from":[{"name":"MPFB2 hm08","sha256":"…"}],"mirror":"mirror.npy",
 "landmarks":{"anatomical":{},"mediapipe_478":{}},"contours":{"jaw_rings":[]},
 "bases":{"hm08_targets":{"file":"U.npz","sigma":"calibrated","commercial_ok":true,"bundle_ok":true}}}
```

**Solve result** `solves/NNNN/{result.json, arrays.npz}` (FMT-8, D6) contains:
- per-view `{R, t, f, k1, model, sigma_logf, observable}`;
- shape coefficients, θ_v, ψ_v, vault and ear parameters;
- per-stage vertices, support, per-vertex σ in mm, σ_scale;
- `scale_mode`, findings, licence union, consent ID, versions and seed.

Results are immutable; *Revert* re-activates an older one.

### 2.5 Coordinate conventions

| Space | Convention |
|---|---|
| Head | mm, float64; +x subject's left, +y up, +z out of the face; levelled to FH (R1.1) |
| Camera | OpenCV; X_c = R·X + t |
| Image | px from the top-left pixel corner (centres at i + 0.5); MediaPipe u = x_norm·W |
| Blender | Head and cameras sit under one empty with R_x(+90°) and scale 0.001, so engine (x, y, z) mm maps to Blender (x, −z, y) m, the face looks toward −Y and `.L` = +X (A8). `to_blender_camera` exists (C4) |
| UV | Origin bottom-left; `img.pixels` rows run bottom-up; texel centre at (i + 0.5)/N |
| L/R | Always the subject's side (R1.2) |

### 2.6 Assets: how we obtain and verify them

**Template: `minehead`** (open-template-head-kit).
- A project-owned CC0 quad head re-authored from:
  - the hm08 crop (CC0 📄), which keeps the targets and the MPFB round trip via `head_to_hm08`; or
  - the Blender Studio Human Base Mesh (CC0 ✅), whichever passes topology QA. QA (face-retopology 🧠): no non-quads in deforming zones, poles at least 2 rings from lids, lips and alae, and an exact x = 0 midline.
- `tools/template_pack/build.py` pins the source SHA-256 and writes a mirror bijection (checked: M(M(i)) = i), contour rings and eye/teeth bindings.
- It transfers the hm08 targets barycentrically and adds one Catmull–Clark level if the face has fewer than 6k quads (W4).

**Anatomical embedding.** Two annotators work from craniometric-landmarks definitions.
- A point is accepted when they agree within 1.0 mm (en, ex, ch, sn) or 2.5 mm (g′, zy′, go′) (R4.1).
- Their spread feeds σ_def.
- Extremal points are stored as candidate sets plus a rule.

**MediaPipe → template.**
- Maintainers register the SHA-pinned Apache-2.0 canonical mesh with our own NICP (MM-12), seeded by about 20 point pairs.
- A render-and-detect pass then locks the offsets, shrunk by n/(n + 2) (landmark-index-correspondence 🧠).
- If the CC0 rule forbids shipping the derived table (ethics C7), it is built on the user's machine on first run.

**Tests** use a procedural pack from `synthetic.py`. Tests that need the real assets skip when they are absent.

---

## 3. Algorithms

### 3.1 Joint objective (live)

The parameters are p = {ω_v, t_v} ∪ {ℓ_g = log f_g} ∪ log s ∪ c ∪ {θ_v} ∪ {ψ_v}, where c are the shape coefficients. Landmarks are X_i = s·(X̄_i + B_ic), with X̄_i and B_i precomputed (MM-2).

E = Σ_v w_v Σ_i ρ(‖L_vi⁻¹(π_v(X_i) − u_vi)‖) + E_curve + E_contour + E_pin + E_shape + E_sym + E_cam + E_scale + E_vault

**Noise.** σ is held in mm and converted to px at each view's depth.
- **Per-kind σ** (normal/tangent, mm; landmark-index-correspondence 🧠): sharp junctions 1.0–1.5/1.0–1.5; extremal points 1.5–2.5/2–4; curves 1.0–2.0/free; oval 2–3/free; brows 3–5/free. Each point's covariance is Σ = R·diag(σ_n², σ_t²)·Rᵀ.
- **Total variance:** σ² = σ_kind² + σ_def² + σ_px². σ_def is a 0.5–2 mm definition-bias floor shared across views, so it never shrinks as views are added (validation-test-bed 🧠). MediaPipe σ is multiplied by √(N/N_eff), with N_eff 60–100.
- **User pins:** σ = √(σ_class² + σ_motor²), where σ_motor is one screen pixel at the zoom used for placement.
  - σ_class: crisp points 0.8 mm (expert) or 1.2 mm (novice, the default); prn 2.0 mm; palpation points 4–5 mm (guided-workflow-accessibility 🧠).
  - The old fixed 0.75 % IOD gave novices 3–30× too much weight.
- **Iris centres move with gaze** and are never used as shape landmarks.

**Robustness.**
- Huber δ = 2, then a final Tukey round, then rejection at 3.03σ (1 % false alarms).
- A view is rejected above its 99 % reduced-χ² bound (validation-test-bed 🧠).
- View weight is w_v = 1/n_bin, and no view gets more than 40 % of the total (R1.8 🧠).

**Solver.** LM (exists) with multiplicative rotation updates. P ≈ 110, so each mouse event runs 2–5 warm-started iterations.

### 3.2 Cameras

**Initialisation.** f_h = f35_h·√(W² + H²)/43.27 over f35 ∈ {13, 24, 26, 35, 50, 77, 85, 120, 135, 200}. For each hypothesis: affine initialisation, then LM, then pitch-flip and yaw-mirror restarts. The best robust score with every z_c > 0 wins (CAM-3 🧠).

**Focal priors** (σ on log f; CAM-6, R2.2, smartphone-camera-pipeline 🧠):

| Situation | σ |
|---|---|
| Uncropped 4:3 EXIF | 0.04 |
| Zoom crop detected (f35/FocalLength > 1.02 × the lens mode) | 0.06 |
| Native-frame ambiguity | 0.09 |
| Phone with no EXIF | 26 mm at 0.25 |
| Unknown | 50 mm at 0.6 |

Views in the same focal group are tied with σ 0.02.

**Camera model per view.**
- Main or tele lens, face within 25° of the axis: k = 0.
- Front camera, or face beyond 25°: k1 ~ N(0, 0.02²).
- Ultra-wide or face at the frame edge: a local virtual camera with f′ = f·sec²(θ/2), or σ_px ×3.

**Distance prior.** Z ≈ f_px·88 mm/outer-IOD_px on near-frontal views, or a tape measure (σ 5 cm, R2.4). Bounds 0.25–10 m.

**Pose tags** (R2.7 🧠): yaw σ 10°, pitch 5°, roll 3°.

### 3.3 Observability

From Σ = (JᵀWJ + Λ_prior)⁻¹:
- **Focal.** σ_ℓ = √Σ_ℓℓ. Focal is freed only if σ_ℓ < 0.10 and yaw spans ≥60° (C2, R2.3). If σ_ℓ exceeds 0.8 × the prior σ, the card says: "Lens not measurable from these photos; using EXIF."
- **Perspective strength.** P = 100 mm/z.
- **Radial slope.** A slope implying more than 5 % magnification error is flagged (R2.8).
- **Fit quality.** Reduced χ² = 2·cost/(m − n); displayed covariances are inflated by max(1, χ²_red).
- **Scale.** Shown separately ("size ±3 %"), because free-point BA is 2–4× overconfident on scale (validation-test-bed Table 5 🧠).

### 3.4 Shape prior and rigidity

**Default: `TargetSpace`** (open-template-head-kit 🧠/↔️).
- Each hm08 modifier splits into non-negative columns c⁺, c⁻ ∈ [0, 1], with a penalty λ·c⁺c⁻.
- An optional mass-weighted SVD keeps K ≈ 40–80.
- Σ_c is calibrated by moment matching against about 25 Farkas measurements: min ‖JΣ_cJᵀ − Σ_m‖_F subject to Σ_c ⪰ 0.
- This constrains proportions, not detail. The UI therefore says "guessed from average proportions", never "typical of people like the sitter".

**Rigidity.** E_shape = ½λ(r)·cᵀΣ_c⁻¹c, with λ(r) = 10^(2r−1) (facebuilder-blender 🧠). The slider is labelled "Stay close to an average head" at one end and "Follow my pins exactly" at the other.

**Global scale.** log s ~ N(0, 0.045²) until verified (validation-test-bed 🧠). Calipers, an ID-1 card or a sharp-limbus iris override it. Per-landmark σ arrays replace the scalar 8 mm (R4.1), and the ratio priors stay weak (R4.3).

**Opt-in `Flame2023OpenSpace`.** Loaded from a user path, with `ATTRIBUTION.txt`. β ~ N(0, I) with K growing 20 → 50 (MM-3). A ‖β‖² > χ²_K(0.999) flag (86.7 at K = 50) is raised (MM-5).

### 3.5 Curves, silhouettes, cranium, ears

**Curves** (lids, lips, brows): r = n̂ᵀ(u − π(γ(s*)))/σ_n. s* is re-associated each iteration on the projected template polyline; σ_t = 3–5σ_n, or free.

**Contours** (face-segmentation-contours 🧠). Residuals are normal-only, by kind:
- `hard` (skin against background): r = nᵀ(π(X_c) − x)/σ_n;
- `outer_bound` (hair, beard, hat): max(0, r);
- `inner_bound`: max(0, −r).

**Contour matching.**
- The model contour comes from n·v zero-crossings along the template's contour rings, with a visibility test.
- Pairs are re-matched every outer iteration and gated at 0.15·IOD_px, shrinking to 5σ_n. Pairs whose normals differ by more than 30–45° are rejected.
- Distances use an EDT instead of the dense O(M·P) matrix.
- σ_n² = σ_edge² + (0.5·s_model)² + σ_blur², floored at 0.005·IOD_px.
- The main fix to existing code: `fit_silhouettes` today back-projects the full 2D correction, so the contour drifts along itself.

**Masks** come from a user lasso, the MediaPipe oval, or optional Apache-2.0 helpers (MediaPipe selfie, multiclass or hair segmenters; SAM 2). Parsers trained on CelebAMask or LaPa are never used.

**Cranium** (cranium-under-hair 🧠).
- Vault parameters L = g′–op′, B = eu′–eu′ and H = t–v get log-normal priors: σ 0.035, 0.037 and 0.045 for a matched population; 0.05 and 0.065 for L and B when ancestry is "unknown". The user chooses this; it is never inferred.
- Hair outlines are `outer_bound` terms weighted ≥10×. The hairline, parting and nape are skin points (σ 1–2 mm). A slicked-hair view is `hard` (σ 1.5–3 mm). The tape circumference is an arc-length term.
- The face is never stretched to fit the vault. |z| > 3 on L, B or circumference reads "check scale or focal".

**Ears** (ear-reconstruction-sculpting 🧠).
- Each ear is a separate part: E = R(θ)·s·(ē + Uα) + t, hinged at otobasion and anchored at tragion.
- Priors: tilt N(20°, 7°), protrusion N(25°, 8°), twist N(0°, 6°). U holds hand-authored CC0 ear keys.
- An ear gets weight 0 when |yaw| < 30° or hair covers it.

### 3.6 Expression and mirror handling

**Photo checks** (guided-workflow-accessibility Table 1 🧠), relative to the photo the user marks most neutral:

| Signal | Warn | Exclude | Notes |
|---|---|---|---|
| mouthSmile | 0.25 | 0.5 | |
| jawOpen | 0.10 | 0.25 | |
| eyeBlink | 0.4 | 0.6 | lids are ignored above this |
| 52-vector drift | 0.4 | 0.8 | |

A warned view keeps ×0.25 of its identity weight.

**Default (no expression basis).**
- Identity is fitted from neutral views.
- Open mouths drop their lip points, and squints drop their lid points (R3.7).
- A per-view jaw hinge, x′_j = x_j + ω_j(R(θ_v·a)(x_j − c) − (x_j − c)), has its centre c 10–13 mm in front of the tragion (BA-1 🧠) and θ_v ~ N(1.5°, 1°²).

**With a basis.** X_v = X + Eψ_v, with a neutral anchor ‖mean_N ψ_v‖/0.1 (BA-9).

**Mirror test.**
- Compare E_v with E_v^flip (u → W − u, L/R swapped).
- Suggest a flip at a 10 % margin for front-camera views (smartphone-camera-pipeline 🧠), otherwise at 30 % (guided-workflow-accessibility 🧠). In both cases the margin must also exceed the χ² noise 2√(2n_v) (derived).
- Below the threshold the card says "can't tell". The photo is never flipped automatically.

### 3.7 Warp schedule and asymmetry

**Stages** run 0 → A → B → C → D (W1, R5.1). Gates (R5.2 🧠):
- Leave A when landmark RMS < 4 % IOD and chamfer < 2–3 mm.
- Leave B when RMS < 3 % IOD in every view, the held-out view included.
- During C and D, no landmark may move more than 0.5 mm.

**3D targets.** With cameras frozen, `bundle_adjust` triangulates X*_i with Σ*_i, using prior σ of 8 mm in B and 3–4 mm in C.

**Stage B.** d(x) = Σ c_j·exp(−‖x − x_j‖²/2s²) with s = 30–40 mm, solving (ΦᵀWΦ + μK)c = ΦᵀWd with W = Σ*⁻¹.

**Stage C.** min ‖diag(√w_s)·L·d‖²_M + Σ w_c‖x_c + d_c − p_c‖².
- Stiffness w_s (R5.9, W3 🧠): ligaments ×3–5, lid margins ×3, lips ×0.3. For edge flow, lids, lips, nostrils and ears get ×5.
- |d| is capped at 3–5 mm unless ≥2 views agree (MM-10).
- Mesh gates: quad angles 30–150°, aspect ≤4, det J > 0.2 (MM-11).

**Stage D** runs only where ≥2 views agree.

**Template limits.** If X* sits more than 3σ from the model, the card says "photos say more than the template can express – sculpt here", and the region joins `f3d_sculpt_here`.

**Symmetry.** E_sym = Σ‖D_p⁻¹(X_l − M·X_r)‖² with per-pair σ: canthi 0.7–1.0, alare 1–1.5, cheilion 1.5–2.0, gonion 2.5–3.0, ears 3–4 mm (R4.2 🧠).
- Full weight applies only in guessed regions; elsewhere ×0.25.
- The plane is re-fitted by reflection Procrustes (R3.3).
- The output is never symmetrised: S = ½(X + M·X_m) and the `Asym` key holds X − S (R5.9). If mirror RMSD < 0.3 mm on asymmetric photos, the card says "too symmetric".

### 3.8 Detail refinement

Shape resolves to ~5 mm wavelength; finer detail is displacement, gated by mm/px: pores ≤0.033, fine lines ≤0.08, line positions ≤0.25 (R5.11 🧠). The default adds no photometric detail; it writes sculpt guides instead: best-view stencils, crease curves from edges that reproject within 2σ in ≥2 views, and `f3d_support`. Optional SH9 refinement (OPT-1) is labelled *estimated*.

### 3.9 Texture projection

**Gates.** TEXTURE consent, a known rights basis, and reprojection error ≤1.5 px median and ≤3 px max (T2).

**Pipeline.** vis = [z_v(p_t) ≤ zbuf + max(1 mm, 2σ_geom)] (TEX-1); w = vis·cos²θ·fade(60°→75°)·footprint·edge (TEX-2 ↔️); gains log I_v = log g_v + log a with Σ log g_v = 0 (TEX-3); two-band blend, 3 mm low band, high band from the best view (TEX-4). Only the low band may be mirrored (TEX-5). Outputs: linear albedo, confidence, view index; "absolute colour unknown" without a chart.

### 3.10 Coaching: next best photo

Each pose-ring bin (yaw {0, ±20, ±45, ±90} × elevation {−25, 0, +25}) is scored as a candidate shot:
1. Predict its Jacobian J_c.
2. Marginalise the candidate's pose by Schur complement: H′ = H_cc + J_cᵀWJ_c − J_cᵀWJ_p(J_pᵀWJ_p)⁻¹J_pᵀWJ_c, with subscript c here meaning the shape coefficients.
3. Score Δ = Σ_r w_r[tr_rΣ − tr_rΣ′], where tr_r(Σ) = Σ_{j∈r} tr(S_jΣS_jᵀ).

The perceptual weights w_r are: lids 1.0, brows 0.9, lips 0.8, nose 0.7, ears 0.1–0.2 (face-perception-likeness 🧠).

The winner is shown as one sentence, for example "Next: left profile, eye height, 1.5–2 m". Nose and chin projection count as measured only with a front view plus a view at |yaw| ≥ 60° (R5.9).

### 3.11 QA in plain language

Support for region r is s_r = 1 − tr_rΣ_post/tr_rΣ_prior.

| Metric | Shown as | Threshold |
|---|---|---|
| s_r | **measured** / **partly** / **guessed** (hatched) | ≥0.7 / 0.3–0.7 / <0.3 (guided-workflow-accessibility 🧠); ask for a view if <0.8 on a top-5 region (anatomy §6) |
| per-vertex 2σ | "likely within ±X mm" | inflated by χ²_red |
| Leave-one-view-out (LOVO) | "This photo disagrees by ~1.5 mm" | held-out error > 2× in-sample |
| ‖c‖² < K − 2√(2K) | "Pulled toward average" | R5.8 🧠 |
| Mirror RMSD | "Too symmetric" / "Unusually asymmetric – check pose" | <0.3 / >1.5 mm |
| IPD, g–op, head breadth | "Scale looks wrong" | 55–72 / 182–200 / 140–160 mm |
| Interior fits, contour does not | "Lens or distance wrong, not the face" | SIL-3 |
| det J ≤ 0.2 | "Surface folded – raise Rigidity" | MM-11 |
| Over-pinning | "Too many pins here" | >3–5 per feature per view, or one view holding >60 % |

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

**What ships.**
- No wheels: the add-on uses Blender's NumPy, so one zip covers every platform.
- Only CC0 assets are bundled (`minehead` and its targets).
- `network` stays undeclared until a consented downloader exists (ethics A3).
- `blender_version_min` names only versions CI tests (packaging ↔️). The engine itself runs on Python 3.11 and 3.13 with NumPy 1.26 and 2.x (A4).

**How landmarks arrive.**
- **Path A:** a helper script runs in a venv the user creates and writes JSON. Nothing is pip-installed at runtime.
- **Path B:** an optional platform-split onnxruntime build.
- **Always available, no downloads:** manual pins plus imported JSON (ethics A4).

### 4.2 Panels: a guided rail

The **Face3D** sidebar tab has a Guide with ten stages: Consent → Photos → Check → Landmarks → Cameras → Shape → Confidence → Sculpt → Texture → Share.

Each stage shows:
- an icon *and* a word (Done, Needs attention, Not started);
- a "done when" line;
- one primary button gated by `poll()`. `poll_message_set` explains why it is disabled ("2 photos still have blocking issues").

**Expert options** sit in `DEFAULT_CLOSED` sub-panels:
- σ values and badges;
- symmetry: assist, prior or enforce;
- expressions: off, jaw only, or basis;
- per-group focal mode;
- *Revert to solve #n*.

**Optional 2-minute onboarding.** The user places 6 crisp landmarks twice, which personalises σ: σ_crisp = max(RMS(Δ)/√2 + 0.3, 0.5) mm (guided-workflow-accessibility 🧠).

### 4.3 Operators and keymap

All operators use REGISTER + UNDO and report through `self.report`; no traceback ever reaches the user. Keys live in `keyconfigs.addon`, so users can remap them, and every operator is F3-searchable.

| Operator | Key | Behaviour |
|---|---|---|
| Pin tool (`WorkSpaceTool`) | P | Click places a pin; drag uses an offset loupe; Shift-drag moves at ¼ speed. Arrows nudge 1 px (Shift: 0.25). X deletes; H / Alt-H hide and reveal. The status bar shows hints |
| `face3d.review_next` / `_prev` | Tab / Shift-Tab | Spell-checker queue ordered by normalised residual. Shows the plain name, an illustration and the epipolar line |
| `face3d.view_next` / `_prev` | PageDown / PageUp | Also bound to timeline markers |
| `face3d.solve_refine` / cancel | Ctrl-R / Esc | Esc keeps the last good state |
| `face3d.card_accept` / `_dismiss` | Ctrl-Enter / Ctrl-Backspace | Acts on the focused card |
| `face3d.compare_flip` (hold), `_blur`, `_grey`, `_edges` | F, B, G, E | Likeness aids (R8.1) |
| `face3d.wobble` | W | 8–12 posterior samples, stepped by hand or ≤1 Hz |

Also present, each consent-gated: `photos_add`, `landmarks_detect` / `_import`, `handoff_sculpt`, `rebase_sculpt`, `texture_project`, `report_export`, `prepare_for_sharing`, `purge`.

### 4.4 Overlays and accessibility

**Drawing.** `gpu` POST_PIXEL handlers draw with `POLYLINE_*` shaders, since Metal and Vulkan ignore line width, and sizes scale with `ui_scale`. The overlay maths lives in `qa/overlay_geom.py`, so it is tested without Blender.

**Encoding** (Okabe–Ito palette; guided-workflow-accessibility Table 4 🧠). Every element differs by shape as well as colour:

| Element | Colour | Shape |
|---|---|---|
| Auto pin | #56B4E9 | circle |
| User pin | #E69F00 | square |
| Conflict >3σ | #D55E00 | ✕ plus residual line |
| Selected | #F0E442 | ring |
| Model contour | #009E73 | line |
| Guessed region | #CC79A7 | hatching |

Residuals use labelled cividis bins: <1, 1–2, 2–3 and >3σ.

**Legibility.** Every glyph has a dark outline and a light halo, giving ≥3:1 contrast on any skin tone (WCAG 2.2). Pins are 9 px with a 12 px hit radius, and every target is ≥24 px.

**Motion.** Nothing moves on its own:
- Flip-compare works only while the key is held. It replaces R8.1's 3 Hz blink, which sits in the photosensitivity range 🧠.
- Live re-solve can be switched to "on release" (↔️, to be A/B tested).

**Text.** All strings go through `bpy.app.translations`. Blender has no screen-reader support, so every finding is also written to the Info log and to the HTML/text report.

### 4.5 Undo, history, background jobs

**Mesh writes.** `foreach_get` → float64 → `foreach_set` + `mesh.update()`, done in OBJECT mode with the previous mode restored. Writes are refused on a topology-hash mismatch or while in Edit Mode (A3, K1, K4).

**Undo.**
- While dragging, previews go to a muted `f3d_live` key via a timer, which stays off the undo stack.
- Releasing the pin pushes one `undo_push("Move pin")`.
- Pins live in PropertyGroups, never in globals. `undo_post` re-resolves IDs by name and re-runs the live solve (A5).

**Background work.**
- Short solves run in a thread on copied arrays.
- Refine and texture run in a `sys.executable -I` subprocess that exchanges `.npz` files.
- A modal timer applies results in 30–50 ms per tick.
- `blender -b` runs everything synchronously.

### 4.6 Shape keys and Multires hand-off

**Key stack** (K2, SK-1):
- `Basis`: the template mean.
- `ID_fit`: the symmetric fit. `slider_max` is 1.5; values above 1 are a caricature preview (R5.8 ↔️).
- `Asym`: the subject's asymmetry.
- `artist`: the artist's sculpt.
- muted `stage_*` diagnostics.

Per-photo expression keys are written only under RIG_ANIMATE consent (ethics F4).

**Refit rebase.** new `artist` = old `artist` + (new `ID_fit` − old `ID_fit`). Basis writes add Δ to every dependent key (K3).

**Sculpt copy.**
- Bake the key mix, clear the keys, and add Multires L2 (likeness) and L3 (detail) (SK-3).
- The fit snapshot stays hidden in the scene.
- Later refits go through `multires_reshape` (K5). Whether detail follows the base is unverified (Q4); a test scene guards it, and the fallback is a new copy.

**Also written.**
- 15–25 region vertex groups.
- Attributes: `f3d_support`, `f3d_sigma_mm`, `cranium_confidence`.
- A *Protect measured regions* operator that copies (1 − support) into `.sculpt_mask` (a FLOAT attribute since 4.1, 📄).
- Brow and hairline curves.
- Rigid 24 mm eyes.
- A locked camera per photo, with a background image (α 0.4) and its own marker, and "Lock Camera to View" off (sculpting-likeness-workflow 🧠).

**Artist feedback into the fit.** A painted sculpt mask m becomes data weight (1 − m) plus a pin at σ 0.2 mm (W5).

**Rig path.** `head_to_hm08` returns the head to MPFB as a `.target`, which opens MPFB/Rigify rigs and ARKit-named tools.

### 4.7 From anatomy research to in-app guidance

**Capture checklist** (R1.4, reference-photography-protocol, cranium-under-hair). Each item ticks automatically when the photo checks confirm it:
- hair off the ears;
- glasses off for 10–15 min beforehand;
- a fixed gaze mark;
- the lens at eye height;
- ≥1.5 m away;
- a phone's 2–5× lens;
- no portrait or beauty mode;
- optionally, a cap view plus tape measurements.

**Likeness checklist,** in perceptual rank (face-perception-likeness 🧠): lids → brows → lips → eye spacing → nose → facial thirds → jaw and hair → age → ears. Each item opens the camera that shows it best.

**Measurement panel.**
- Measures: en–en, ex–ex, al–al, ch–ch, n–sn, sn–sto, n–gn, zy–zy, go–go, g–op, eu–eu, ear length, and the nasolabial, gonial and cervicomental angles.
- Each shows the value ± 2σ and its support.
- A population z-score appears only when method and landmark variant match (R1.3, R2.2).
- Caliper entries become constraints: E_cal = Σ((‖X_a − X_b‖ − d − o)/σ)² (R5.7).
- |z| > 2.5 in an unobserved region produces a note, never a correction (R8.2).

**Warning catalogue** (`guidance/warnings.toml`): problem → why → fix → source and badge. Example: "Photo 3 was taken from about 40 cm, so the nose will come out too large. Retake from 1.5 m or more and zoom in. [Use for texture only] [Keep]". The R5.2 ordering hinges are included.

**Sitter metadata.** Age, sex prior and BMI are optional and never inferred. Ancestry is never asked (R2.7, R7.4).

---

## 5. Validation and QA

### 5.1 Automated tests (CPython + pytest, no Blender)

Tier 1 of the validation-test-bed 🧠 runs on every push: 30 fixed seeds, with medians compared against stored baselines ± 3 MAD.

| Area | Checks |
|---|---|
| Camera solve (Q1) | noiseless reprojection < 1e-6 px; with σ = 1 px noise, RMS ≈ σ√(1 − p/n), failing above 1.2σ |
| Distance/lens sweep (EV-5) | z 0.25–5 m and f35 13–200 mm: focal error < 5 % and rotation < 2° when yaw spans ≥60° (R8.4 🧠); "not observable" when every view is frontal at ≥2 m |
| Phone cases | k1 sweep, stereographic edge warp, 16:9 static-tag crop and mirrored front view each choose the right camera model, with shape error < 1 mm (smartphone-camera-pipeline 🧠) |
| Behaviour | no tangential contour drift; outer-bound hinges never pull inward; stage gates; 0.5 mm landmark freeze; fold gates; vault parameters within ±3 mm with controlled hair and ±6 mm dry (cranium-under-hair 🧠) |
| Hand-off and texture | rebase exact to 1e-9; Basis-Δ handling; topology refusal; TEX-8 (gains within 2 %, no colour leaking onto occluded texels) |
| Policy and packaging | consent gates; licence-taint AND; socket guard (ethics A7); AST check that `face3d/` never imports bpy; `tomllib` manifest lint; SPDX row per bundled file |

Blender smoke scripts (Q3) run in an optional external CI.

### 5.2 Honest uncertainty

Calibration must hold over ≥30 seeds (validation-test-bed 🧠), including runs with definition bias and with 5 % outliers:
- aligned 1σ coverage between 0.60 and 0.76;
- NEES/dof between 0.8 and 1.25.

If a run misses, the displayed ranges are inflated by the measured factor, and the report says so.

**Tuning order.** Tune the σ ratios first, for accuracy; then the global σ scale, for coverage. Screen parameters with Morris elementary effects and validate leave-one-subject-out.

**Every report carries:**
- `scale_mode`;
- "not validated against a scan", until a tier-3/4 comparison exists;
- no claim finer than the capture modality allows (Q4);
- the count of active 🧠 defaults.

### 5.3 Likeness checks for the artist

- A camera-matched overlay with an opacity control.
- Compare modes: silhouette, edges, hold-to-flip, greyscale, thumbnail, and blur at σ = 3 % of face width (this keeps the 8–16 cycles/face-width identity band; face-perception-likeness 📄).
- A held-out photo chosen by the artist.
- Worst-first residuals in mm.
- The wobble view.
- A familiar-viewer sheet: a photo-versus-render grid with 5 questions, judged blind A/B by ≥5 people who know the sitter (guided-workflow-accessibility 🧠). Its use is limited to what the consent covers.
- A caricature preview, S(α) = M + α(S − M) with α from 0.9 to 1.2, preview only (↔️).
- Identity-embedding scores are off by default (IDENTITY_CHECK scope, 1:1 comparison, kept in RAM only).

**Usability testing:** think-aloud with ~5 users per round over ≥3 rounds, then a summative SUS with 15–20 users, target ≥80.

---

## 6. Milestones

Each milestone ships on its own, and its acceptance tests all run here.

| M | Ships | Acceptance |
|---|---|---|
| **M1 Honest camera solve** | `pnp`, `reconstruct`, `bundle` extensions (σ in mm by landmark kind, σ_def, log-scale, full covariance, redescending round); `observability`, `mirror`, `report`; CLI `python -m face3d solve project.json` | Q1, EV-5 and the phone cases pass. Mirror flagged in ≥95 % of seeded mirrored views with ≤2 % false flips. Coverage 0.60–0.76 and NEES/dof 0.8–1.25, for points and for scale |
| **M2 Project, consent, capture** | `project/*`, `qa/checks`, pose ring, next-best-view, HEIC and zoom EXIF, helper fixture JSON | Gate matrix (ethics F1–F20 where applicable); socket guard; the profile is the top suggestion for frontal-only sets in ≥90 % of seeds |
| **M3 Template pack + staged fit** | `model/*`, `fit/{stages,refine,cranium}`, contour rewrite, pack builder tested on a fixture OBJ, synthetic pack | In-space face RMS ≤0.5 mm without noise and ≤1.5 mm at realistic noise (7 views). Out-of-space: C cuts RMS ≥30 % versus A. Profile error ≤1–1.5 mm at prn and pg (SIL-3). Vault tests pass |
| **M4 Extension MVP** | Manifest, bridge, cameras, landmark import, background Refine, `ID_fit` + `Asym`, static overlays, report | Manifest lint; AST bpy isolation; overlay and key-maths tests; camera round trip within 1e-6·s |
| **M5 Live pins + guided rail** | `solve/live`, pin `WorkSpaceTool`, review queue, epipolar lines, undo, palettes, cards, checklists, measurements, onboarding | Live result within 1e-3 of batch. The keymap reaches every stage. Categorical palette ΔE ≥ 20 under simulated deutan, protan and tritan vision (our target) |
| **M6 Sculpt hand-off + ears** | `handoff/keys`, sculpt copy, rebase, `.sculpt_mask` protection, markers, likeness aids, `fit/ear` | Rebase exact to 1e-9; LOVO and held-out metrics; synthetic ear tilt and protrusion recovered within σ_prior/3 from profiles |
| **M7 Texture + sharing** | `texture/*`, gates, provenance, *Prepare for sharing* | TEX-8; UV gates (T5); a tainted export is blocked and the offending components are listed |
| **M8 Opt-in statistical spaces** | FLAME 2023 Open adapter with attribution; research adapters behind warnings | χ² gates; refusal when `basis_sha256` mismatches; the default path still passes using the CC0 pack alone (L2) |

---

## 7. Risks and deliberate omissions

**Risks**
1. **Most defaults are unverified (🧠).** Mitigation: named defaults, coverage tests, the held-out photo, and validation tiers 2–4 before release [gap: metric-3d-landmark-reference].
2. **The default prior is moment-matched, so it constrains proportions, not shape.** It can over-flex or shrink. Mitigation: the Rigidity slider, shrinkage/χ² cards, the cross-check, and M8.
3. **`minehead` may fail topology QA.** It would then need re-authoring; the pack is a plug-in, so this can be reversed.
4. **Annotation is a bottleneck.** Mitigation: two annotators, render-and-detect locking, and down-weighting `verified:false` points.
5. **The helper venv is hard for non-experts.** Pins and JSON import always work. MediaPipe and segmenter weight licences are ↔️.
6. **Live solving may be slow.** Fallbacks: solve on release, fewer iterations, a 100-point MediaPipe subset.
7. **Multires rebase in 5.x is unverified (Q4).**
8. **Rules may shift:** store policy (C7, C8), biometric law, AI Act Art. 50.
9. **Phone processing (beauty filters, generative zoom) can alter geometry.** Mitigation: risk-based weights and consensus-ratio flags.

**Deliberately left out**
- **Learned shortcuts:** neural single-image regression, AI meshes as identity sources (OPT-2 caps them at 25 %), generative fill, and photometric detail by default.
- **Extra anatomy:** hair strands, teeth and tongue, expression rigs beyond ARKit-named hooks, research ear models, and the bone/soft-tissue layer (it waits for a CC0 skull; FSTT is guidance only).
- **Topology and capture changes:** auto-retopology; phone depth and TrueDepth terms (phone-video-depth-capture 🧠). Video enters only as 12–24 stills in one focal group.
- **Cloud and data features:** cloud processing, telemetry, URL importers, 1:N search, anonymisation claims, and home-made encryption (we rely on OS-encrypted folders).
- **Child-specific priors by default.** Minors need guardian consent; widening for children (R4.5) is opt-in.
