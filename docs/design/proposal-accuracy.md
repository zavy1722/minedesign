# Proposal: an accuracy-first photo-to-head engine and Blender extension

*Design angle: geometric and perceptual likeness accuracy. Written 2026-11-20 against `face3d/` at commit `fe13b73` (42 tests passing) and the five digests in `research/_raw/requirements_*.md`.*

**Citations** take the form `[area/topic badge]`, for example `[rec/camera-pose-solving 🧠]`. Here `rec` = reconstruction, `anat` = anatomy, `bl` = blender, `com` = community and `eth` = ethics. A digest rule ID such as `BA-5` or `R4.1` points to the digest for that area. Badges: ✅ verified, 📄 single-sourced, 🧠 unverified expert knowledge, ↔️ contested. **Every 🧠 number is a named, tunable default carrying its badge, never a constant.** Values marked *(design default)* are this proposal's own starting points: they are uncalibrated and the M1 harness tunes them.

---

## 0. Principles

1. **Measure before building.** No fitting stage merges until the synthetic harness (M1) shows it lowers per-region millimetre error.
2. **Every signal declares what it can and cannot determine.** The engine never turns a prior into a "measurement" without saying so.
3. **Uncertainty is a deliverable.** Every vertex carries a posterior σ, and every region is labelled *measured*, *partial* or *prior-driven*.
4. **Priors fill only what nothing observes.** Likeness is the sitter's deviation from the mean [anat/face-perception-likeness 🧠], and shrinkage toward the mean is the commonest likeness failure, so we audit it.
5. **No fabricated data.** Template meshes, landmark tables and prior tables are produced by scripts from licensed sources, carry hashes and badges, and are verified (§2.4).

## 1. Vision and user journey

**Vision.** A consenting sitter's photos become a head in Blender that is measurably closer to the real person, region by region in millimetres, than existing Blender tools. The head comes with an honest map of where it is measured and where it is guessed, and it is ready for an artist to sculpt on top of.

### 1.1 What each signal can determine

| Signal | Determines | Cannot determine | Typical σ |
|---|---|---|---|
| Frontal landmarks | Lateral (x, y) feature layout up to scale | Depth (nose projection, orbit depth); focal vs distance | lateral 0.5–1 mm with ≥ 3 views; depth from frontal only 10–20 mm [anat/face-perception-likeness 🧠] |
| Oblique views ≥ 30° apart | Depth by triangulation | Scale | depth ≈ 2× lateral [same 🧠]; depth claims need ≥ 2 views ≥ 30° apart [bl C7 🧠] |
| Profile silhouette | Midsagittal profile (g, n, prn, sn, ls, li, pg) and the jaw outline | Interior detail; anything hidden by hair | 1–2 px [bl S2 🧠]; target ≤ 1–1.5 mm at prn and pg [rec SIL-3 🧠] |
| Perspective (near camera) | Distance z, but only if the person's depth relief Δ is known | z beyond about 1 m; identity confounds it (nose-to-face ratio varies 9–11% between people) | single-view focal error 2–12% at 0.3 m, unobservable at 2 m [rec/camera-perspective-distortion 🧠] |
| EXIF focal length | f, with the dolly-zoom ambiguity broken | Crops and digital zoom | log-σ 0.03–0.04 uncropped [rec CAM-6, com R2.2 🧠] |
| Iris diameter | Metric scale | — | HVID 11.8 ± 0.6 mm ✅ [anat/eye-region], i.e. ≈ 5% from population spread alone |
| Caliper, PD or card | Metric scale | — | 0.5–1 mm [anat R3.4, com §4 🧠] |
| Photo-consistency across views | Dense surface offsets along normals where skin texture exists | Textureless regions; anything coarser than the sweep range | design default ±3 mm sweep |
| Shading | High-frequency normals (lines, folds) | Low-frequency shape, because of the albedo–light–shape (bas-relief) ambiguity | used only below 5 mm wavelength [anat R5.11 🧠] |

### 1.2 The journey

1. **Consent and project.** The add-on refuses to fit without a `ConsentRecord` that has the `RECONSTRUCT` scope and lists each photo's sha256 [eth §3].
2. **Capture guidance.** Before capture, the add-on states which accuracy **tier** the planned set reaches:
   - **T0**, front only: proportions plus frontal likeness; depth is labelled prior-driven.
   - **T1**, 5–9 photos (front, ±30–45°, ±90° profiles, one low view) from the rear main camera at ≥ 1 m [com R1.4–R1.7, bl T4 🧠]. Expected to meet the per-region targets in §5.2.
   - **T2**, T1 plus one measured length (optician PD, caliper or an ID-1 card held at face depth). Scale error ≤ 1.5% [rec EV-3 🧠].
   - **T3**, a dense turntable or video set with cameras solved externally by COLMAP (BSD) and imported [rec FMT-7, BA-12]. Sub-mm, bounded by the modality floor of 0.2–0.5 mm [rec EV-4 ↔️].
3. **Ingest and audit.** The add-on reads EXIF, bakes orientation, assigns focal groups, and runs the quality gates (blink, blur, face size, clipping, mirrored selfie) [com R1.1–R1.6].
4. **Landmarks.** An external MediaPipe helper writes JSON. Manual pins are always available (the zero-download path [eth A4]).
5. **Solve.** Staged joint estimation runs in a background process with live progress (§3.5).
6. **Review.** The artist sees matched-camera overlays, held-out-view error, region heat maps of σ and evidence, and a **next-best-photo advisor** that names the single photo that would most reduce likeness-weighted uncertainty (§3.11).
7. **Correct.** Pins, sculpt masks and paint-overs become observations with σ, cross-validated against the other views [com R5.10, bl W5].
8. **Hand-off.** The add-on writes staged shape keys on the fixed topology, a Multires-ready cage fitted to the Catmull–Clark limit surface, an optional texture, and a fit sidecar with a QA report.

## 2. Architecture

### 2.1 Layers

```
L0  policy/        consent gates, licence taint, data classes      (pure Python)
L1  io/, schemes/  project, landmark, template and result formats   (numpy + stdlib)
L2  obs/           observation models: σ, visibility, contours, quality, mirror
L3  model/, priors/ shape adapters (template-RBF | MPFB targets | FLAME 2023 Open), anatomical priors
L4  solve/         PnP, joint LM with Schur complement, observability, scale, expression
L5  fit/, texture/ silhouettes, dense warp, photo-consistency, shading, projection
L6  eval/, synth/  metrics, regions, procedural test bed, numpy rasteriser
L7  cli.py, pipeline.py   staged orchestration with gates (subprocess entry point)
L8  addon/face3d_blender/  GPL extension: bridge, operators, panels, overlays, jobs
L9  tools/         detector helper, template kit, prior-table builder (never imported by the engine)
```

The engine (L0–L7) imports only `numpy`, `math`, `json`, `zlib` and `tomllib` [bl A1], and stays NumPy 1/2-neutral [bl A4]. Only `addon/face3d_blender/bridge.py` converts between bpy data and arrays [bl A2, A3].

### 2.2 Modules

Status: **exists** = keep as is; **extend** = change; **new** = to write.

| Path | Status | Purpose |
|---|---|---|
| `face3d/geometry/camera.py` | extend | Add inverse-depth parameters (log s, log ρ), crop-aware principal point, optional k1. The Blender export already exists and is tested. |
| `face3d/geometry/procrustes.py` | extend | Reflection Procrustes for the symmetry plane, with weights [anat R3.3]. |
| `face3d/geometry/rbf.py` | extend | Per-landmark λᵢ = α·σᵢ² (the sign fix for φ = r is already done) [rec MM-8]. |
| `face3d/io/exif.py` | extend | Add DateTimeOriginal, crop hints and the intrinsics-group key [com R1.3]. |
| `face3d/io/{png,project,landmarks,template,results}.py` | new | stdlib-zlib PNG reader and writer, plus the format loaders and validators in §2.4. |
| `face3d/schemes/*.json` | new | Landmark scheme registry (§2.4.2). |
| `face3d/obs/{noise,visibility,contours,quality,mirror}.py` | new | Observation model (§3.3), photo gates and the mirror test. |
| `face3d/model/{adapter,template_rbf,mpfb_targets,flame_open,embedding,limit}.py` | new | Shape adapters (FMT-4), barycentric and extremal landmark embeddings, Catmull–Clark limit stencils. |
| `face3d/priors/{tables,anatomical}.py` | new | Load the research-derived prior tables; build landmark, symmetry, ratio and ordering terms. |
| `face3d/solve/lm.py` | extend | Block normal equations, Schur elimination, QR fallback when cond > 10⁸ [rec BA-6]. |
| `face3d/solve/pnp.py` | extend | Full f35 hypothesis set, pitch-flip and yaw-mirror restarts, cheirality [rec CAM-3]. |
| `face3d/solve/bundle.py` | exists | Landmark-only bundle adjustment. Kept as the fixed-camera (T3) and scaffolding path. |
| `face3d/solve/joint.py` | new | Model-based joint estimation (§3.5). |
| `face3d/solve/{observability,scale,expression}.py` | new | Posterior σ, evidence fraction, next-best view; scale fusion and iris; expression tagging and inflation. |
| `face3d/solve/{triangulate,reconstruct}.py` | exists | DLT and LM triangulation; the current two-step reconstruction. |
| `face3d/fit/silhouette.py` | extend | Sub-vertex contour generators, two-way chamfer, hair hinge, joint-LM residual form. |
| `face3d/fit/template.py` | extend | Region stiffness, offset caps, fold gates. |
| `face3d/fit/{photoconsistency,shading}.py` | new | Normal-sweep NCC refinement (§3.9); optional SH9 detail band. |
| `face3d/mesh/{core,laplacian,sparse,reduced}.py` | extend | Per-vertex Laplacian weights; null-space projection of the similarity transform for the reduced basis. |
| `face3d/mesh/{raster,distance}.py` | new | numpy z-buffer rasteriser (depth, triangle id, barycentrics); exact point-to-triangle distance [rec EV-1]. |
| `face3d/texture/project.py` | new | UV G-buffer, view weights, gains, two-band blend [rec TEX]. |
| `face3d/eval/{metrics,align,regions,report}.py` | new | Evaluation harness [rec EV-1, EV-2]. |
| `face3d/synthetic.py` → `face3d/synth/` | extend | Procedural heads, camera rigs, detector simulator, renderer. |
| `face3d/policy/{consent,licence}.py` | new | Default-deny gates and taint propagation [eth A2]. |
| `face3d/{pipeline,cli}.py` | new | Stage graph, gates, and a JSON-lines progress protocol. |
| `addon/face3d_blender/…` | new | Extension (§4). |
| `tools/detect_landmarks.py`, `tools/template_kit/`, `tools/build_priors.py`, `tools/build_extension.py` | new | §2.4 and §4.6. |

### 2.3 Data flow

```
photos ─► ingest(exif, orientation, groups, gates) ─► LandmarkObs JSON ◄─ helper / pins
                    │                                        │
template kit ─► Template + sidecar ─► ModelAdapter ◄─ priors/tables (research/data)
                    │                                        │
          S0 PnP init ─► S1 rigid BA + mirror test ─► S2 shape + expression EM ─►
          S3 + silhouettes, fine RBF ─► S4 dense (photo-consistency | scan) ─► QA
                    │
          fit.npz + fit.json ─► bridge ─► shape keys, cameras, attributes, texture
```

### 2.4 Data formats

All formats are JSON with `format` and `version` keys, plus `.npz` for arrays. Every object carries `{source, version, licence, commercial_ok, measured|generated, consent_id}` [rec INV-3] and a `data_class` [eth §2.2].

**2.4.1 Project (`project.f3d.json`).**
- `consent_id`
- `photos[]`, each with:
  - `sha256`, `path`, `rights_basis`;
  - EXIF intrinsics and `focal_group`;
  - `view_tag`, with nominal yaw and pitch;
  - `mirrored`, `crop_px`, `orientation_baked`, `expression_tag`;
  - `landmarks` (a file reference), `masks` (PNG references with labels: skin, hair, background, occluder);
  - `pins[]`.
- `scale_refs[]`: `{a, b, length_mm, sigma_mm, kind}`.
- `template_ref`, `model_ref`.
- `settings`: every 🧠 default, keyed by name.

**2.4.2 Landmark scheme (`schemes/<id>.json`).**
- `{scheme, version, n, canonical_mesh_sha256}`.
- `points[]`, each with:
  - `index`, `abbr` [anat R2.1];
  - `kind ∈ {anchor, contour, extremal, iris}`;
  - `side`, `mirror_index`, `class`, `sigma_n_pct_iod`, `sigma_t_pct_iod`, `badge`.
- `contours[]`: ordered index chains.

The MediaPipe-478 anatomical map is 🧠 [anat R2.4]. It is **verified, not typed in**: labels are rendered on the canonical mesh, and `mirror_index` is computed as the nearest neighbour of each reflected canonical vertex, with the residual stored.

**2.4.3 Landmark observation (`*.lmk.json`).**
- `{scheme, detector, detector_version, model_sha256, image_wh, exif_applied, mirrored, coord: "px_corner_origin"}`.
- `uv[N][2]`, `visible[N]`, optional `cov[N][2][2]` (from the test-time-augmentation spread [rec BA-2]), `blendshapes{}`, `transform[4][4]`, `n_faces`.

This matches FMT-1 and D1.

**2.4.4 Template sidecar (`template.f3d.json` + `template.npz`).**
- Template identity: `{template_id, source, licence, sha256, topology_hash, n_verts, units: "mm", frame: "head"}`.
- `regions` (a per-vertex label with ~20 regions matching the acceptance table in §5.2).
- `symmetry_map`, `midline`.
- `embeddings{scheme: (tri, bary)}`, each carrying a per-point `bias_px_pct_iod` and an annotator-disagreement σ.
- `contour_chains`, `stiffness` (per-vertex weights [anat R5.9]), `jaw_weights` with the condylar axis.
- `exclude` (eyeballs, mouth interior), `eye_sockets`, `uv`.
- `limit_stencils` (a sparse cage-to-limit map).

**How the template is obtained, never fabricated.**
- `tools/template_kit/extract.py` runs inside Blender on the user's installed MPFB2 (hm08 base: CC0 📄 [eth §5]; the 2.0.16 vs 2.0.18 version question is ↔️). Blender Studio Human Base Meshes (CC0 ✅ [com L2]) is the fallback.
- The script writes the OBJ and computes the hashes.
- Anatomical landmarks are clicked by two annotators against the craniometric definitions [anat R2.1]. Their disagreement becomes the embedding σ.
- The MediaPipe-478 embedding comes from registering the Apache-2.0 canonical face mesh to the template: anchor landmarks first, then NICP [rec MM-12].
- Detector bias per point is calibrated on consented captures that have reference geometry (the validation-test-bed gap topic).

**2.4.5 Results (`fit.npz` + `fit.json`).**
- `fit.npz` holds vertices per stage, `β`, `c`, `ψ_v`, `θ_v`, per-vertex σ_n, evidence `k`, and region labels.
- `fit.json` holds:
  - cameras in both OpenCV and Blender form;
  - the scale mode (`calibrated|measured|iris|prior`) and σ;
  - focal observability per group;
  - flags;
  - QA tables;
  - provenance `{addon_version, blender, python, numpy, seed, solver_config}` [bl D6];
  - licence taint.

### 2.5 Coordinate conventions

- **Image.** Continuous pixels with the origin at the top-left *corner*, x right and y down, so pixel (i, j) has its centre at (i + 0.5, j + 0.5). Orientation is baked before any coordinate is stored. MediaPipe normalised coordinates map as (x·W, y·H); a synthetic-image test verifies this. Blender `img.pixels` rows run bottom-up.
- **Camera.** OpenCV convention, X_c = R·X + t; rotations are updated left-multiplicatively, R ← exp([δ]×)·R.
- **Head frame.** float64 millimetres; +x is the subject's left, +y up, +z out of the face. The template fixes the gauge. A separate *presentation transform* levels the head to a Frankfort-horizontal proxy (tragion–orbitale, 0 ± 5 mm 🧠 [anat/ear]).
- **Blender.** 1 BU = 1 m. P_bl = 0.001·A·P_head, with A = [[1,0,0],[0,0,−1],[0,1,0]] (R_x(+90°)); `.L` = +X [anat R1.1].
- **Blender camera.** OpenCV axes → Blender camera axes by diag(1, −1, −1). `lens = f·36/W`, `sensor_fit = HORIZONTAL`, `shift_x = (W/2 − c_x)/W`, `shift_y = (c_y − H/2)/W` (already in `camera.py`) [bl C4].
- **Precision.** float32 at the bpy boundary only.

## 3. Algorithms

### 3.1 Ingest and focal priors

The pixel focal length is f_px = f35·√(W² + H²)/43.27 [rec CAM-2 🧠, diagonal convention ↔️].

| Source of f | Prior on log f |
|---|---|
| EXIF, uncropped | σ 0.03–0.04 |
| EXIF, crop suspected | σ 0.08 |
| EXIF, crop unknown | σ 0.35 |
| Phone, no EXIF | 26 mm, σ 0.25 |
| Nothing known | 50 mm, σ 0.6 |

[rec CAM-6, com R2.2 🧠]

- **Focal groups** are keyed on (Make, Model, LensModel, f35, W, H, still/video), with a tie σ of 0.02 [rec CAM-5 🧠].
- **Distance priors** on log z: selfie 0.35 m (σ 0.3), rear camera 0.8 m (σ 0.4), tele 2 m (σ 0.4), unknown 1.0 m (σ 0.7) [rec CAM-6, com R2.4 🧠]. Hard bounds are 0.25–10 m [bl C6].
- **Phone lens risk:** if f35 ≤ 16 mm or the face lies beyond 60% of the half-diagonal, inflate σ ×2 or exclude the photo [com R1.7 🧠].

### 3.2 Camera parameterisation and initialisation

Each view is parameterised by (ω_v, τ_v ∈ ℝ², a_v = log s_v, ℓ_v = log ρ_v), where s_v is the image scale in px/mm and ρ_v = 1/z_v:

  u = c + s_v·(R_v X|ₓᵧ + τ_v) / (1 + ρ_v·(R_v X)_z),  with f_v = s_v/ρ_v.  [rec CAM-4]

The dolly-zoom direction (a fixed, ℓ varying) is therefore a single coordinate. The weak-perspective limit ρ → 0 is regular. Views are tied to their focal group g by the residual

  (a_v − ℓ_v − φ_g)/σ_tie,

and the focal prior acts on φ_g. Initialisation runs PnP against the template landmarks:
- f35 hypotheses {13, 24, 26, 35, 50, 77, 85, 120, 135, 200} mm (the current code uses 7 of them);
- an affine start;
- pitch-flipped and yaw-mirrored restarts;
- a cheirality check [rec CAM-3 🧠];
- view-tag pose priors: yaw σ 10° (5° with floor marks), pitch σ 5°, roll σ 3° [com R2.7 🧠].

### 3.3 Observation model

The landmark residual uses a full 2×2 covariance per point:

  r_vi = L_vi⁻¹ (û_vi(θ) − u_vi),  L_vi L_viᵀ = Σ_vi

  Σ_vi = (IOD_v)²·σ²_cls,i·R_i diag(1, κ_i²) R_iᵀ·η + P_vi Σ_expr,vi P_viᵀ

Where:
- **IOD_v** := s_v·63 mm. This is the IPD scale in pixels, defined once [bl table P]. It is not foreshortened by yaw.
- **σ_cls (% IOD)**: anchors 1.5, lid and lip contours 2.5, face oval 4, iris centre 1, user pin 0.75 [bl table P 🧠]. Tangential σ is ≥ 5× larger for contours, i.e. they slide [rec BA-2 🧠].
- **R_i** is aligned with the normal of the *projected model contour*, re-evaluated every outer iteration.
- **η** = N/N_eff (N_eff 60–100) for dense MediaPipe points [rec BA-2 🧠]. Without this, 478 correlated points over-count by about 5×.
- **P_vi** = ∂û/∂X, the 2×3 projection Jacobian. It carries the expression covariance into the image (§3.6).
- **Visibility weight** ramps from 0 at n·(−v) = cos 80° to 1 at cos 60°. Far-side oval points are dropped when |yaw| > 25°. MediaPipe z gets weight 0 with ≥ 2 views [rec BA-3, bl D2 🧠].
- **Detector biases** enter as embedding offsets. For example, an epicanthal fold read as en gets σ 2.5 mm, and prn is pulled 1–2 mm toward the specular highlight [anat §6].
- **Robust loss:** Huber δ = 2 in whitened units. After convergence, drop residuals > 4σ and re-solve; flag a view when > 15% of its points are rejected [rec BA-5 🧠].
- **Extremal landmarks** (g′, zy′, go′, pg′) are recomputed each pose update as a softmax argmax of ⟨p, d⟩ over a region mask, temperature 1–2 mm [anat R3.2 🧠].

### 3.4 Shape model and priors

The identity surface is

  V(g, β, c) = e^g · (T̄ + S·β + Φ·Πc)

- **T̄** is the template, evaluated through limit stencils W_lim when fitting to Multires delivery [bl W4].
- **S·β** is the optional statistical basis.
- **Φ** is the Gaussian-RBF reduced basis (`mesh/reduced.py`, exists).
- **Π** projects out the 7-DoF similarity of the displacement at the anchor landmarks. Without this, Φc trades a rigid motion against the cameras, which is a gauge leak in the current design [rec BA-7].

Three `ModelAdapter`s (FMT-4) provide S and the prior:

| Adapter | Basis S | Prior | Licence |
|---|---|---|---|
| `template_rbf` (default) | none | Anatomical: per-landmark anisotropic Σ_pop,i on scale-normalised positions X_i/e^g (sharp junctions 1.0–1.5 mm, prn/pg′ 1–2 mm normal and 2–4 mm tangential, g/n (3, 4, 2), zy/go (6, 8, 8), 8 mm fallback only [anat R4.1, `craniometric-landmarks.json:suggested_landmark_sigmas` 🧠]); log-ratio priors at σ×2 [anat R4.3]; ordering hinges [anat R5.2]; RKHS ½λ_c cᵀK_cc c | CC0 template |
| `mpfb_targets` | User-installed MPFB2 local face targets as linear columns | N(0, 0.5²) clipped to [−1, 1]; macros σ 0.15 [bl table P 🧠]; artist-made, so a **plausibility** prior and not a covariance | CC0 📄 |
| `flame_open` | FLAME 2023 Open bases transferred to the template, U′ = (W ⊗ I₃)U, computed locally and never shipped [rec MM-7] | β ~ N(0, I), whitened at load; K_β schedule 20 → 50 [rec MM-3 🧠]; Student-t ν = 4 option [anat §4] | CC-BY-4.0, attribution; contents unverified 📄 |

**Population-prior honesty.** Without a commercially usable statistical covariance, the default prior constrains landmarks independently. Correlation enters only through ratios and symmetry, so with frontal-only data the depth of unobserved regions stays near the template. The engine therefore *reports* this (§3.11) instead of hiding it.

**Symmetry.** The term is d = X_l − M·X_r, with per-pair σ: canthi, pupils and lids 0.7–1.0 mm; alare and zygion 1.0–1.5 mm; cheilion 1.5–2.0 mm; gonion 2.5–3.0 mm; ears 3–4 mm. Midline x has σ 0.75–1.0 mm at n and g, 1.5–2.0 mm at prn and sn, and 2–3 mm at pg and me [anat R4.2 🧠]. Outputs are never symmetrised; the asymmetry is exported as its own shape key [anat R5.9].

### 3.5 Joint estimation

The unknowns are θ = {cameras, φ_g, g, β, c, ψ_v, θ_jaw,v, D_iris}. The estimate is the minimiser of

  E(θ) = Σ_vi ρ_H(‖r_vi‖) + Σ_vj ρ_H(r^sil_vj) + Σ hinges + ½‖β‖² + ½λ_c cᵀK_cc c
     + Σ_i ½‖X_i/e^g − μ_i‖²_{Σ_pop,i⁻¹} + E_sym + E_ratio + Σ_v ½ψ_vᵀΛ_vψ_v
     + E_scale + E_focal + E_dist + E_pose

The solver is Levenberg–Marquardt with Nielsen damping (exists). Normal equations are assembled in blocks. Per-view blocks (pose, a, ℓ, ψ_v, θ_jaw: ≤ 30 parameters) are eliminated by Schur complement. The reduced system over shared parameters (≤ 50 + 3·600 + 2) is solved by Cholesky.

The schedule is coarse to fine [bl W1, com R5.1–R5.2 🧠]:

- **S0** PnP initialisation per view.
- **S1** Similarity plus cameras on Tier A anchors; mirror test.
- **S2** g, β (20 → 50) and coarse c (n_c ≈ 40, width 30–40 mm); expression EM in up to 3 rounds.
- **S3** All landmarks, silhouettes and fine c (n_c ≈ 600, 10–20 mm). Cameras stay free, so profile silhouettes also correct pitch and f/z.
- **S4** Per-vertex offsets d (σ 2–3 mm, cap 3–5 mm unless ≥ 2 views agree [rec MM-10]), driven by dense data only (§3.9 or a scan via NICP [rec MM-12]).

A stage advances when landmark RMS is < 2–3% IOD and silhouettes are within 1–2 mm, or when RMS improves by < 1% per iteration. During S4, no landmark may move > 0.5 mm [com R5.2 🧠].

With known SfM cameras (T3), cameras are frozen and landmarks never move them: SfM is good to ≈ 0.5 px against 10–14 px for the detector [rec BA-12 🧠].

### 3.6 Expression, jaw and mirror

- **Tagging.** Blendshape scores are measured *relative to the subject's most neutral photo* [rec/landmark-detection 🧠]. A view is non-neutral when, for example, mouthSmile > 0.25, cheekSquint, eyeWide or browUp > 0.3, browDown > 0.35, eyeBlink > 0.4 or jawOpen > 0.08 [anat §6 🧠]. After the first fit, ‖ψ_v‖ re-tags views (< 0.5 SD neutral, > 1.5 SD expressive) [rec BA-9 🧠].
- **With an expression basis E** (FLAME Open, or a verified ARKit-style basis): X_v = X + E·ψ_v. The prior is ψ ~ N(0, 0.3²) on neutral views and N(0, 1) on expressive ones [rec MM-4 🧠]. The basis is never orthogonalised against identity [rec BA-9 ↔️].
- **Without a basis (default).** Expression is *marginalised*. Each mobile landmark gets per-view nuisance η_vi ~ N(0, m²_{v,r}·σ²_expr,r·I₃), which integrates out exactly to the term P_vi Σ_expr P_viᵀ in §3.3. The multiplier m_{v,r} = clip(score_r/threshold_r, 0, 3) comes from the blendshape scores. σ_expr is 3 mm for the mouth, lids and brows and 1 mm elsewhere *(design default)*. Neutral views therefore dominate identity in mobile regions automatically. Lip points are dropped when inner gap/ch–ch > 0.04 [anat §6 🧠]; lid points are dropped on a blink (EAR < 0.2) or when gaze pitch > 10–15° [com R1.4, anat §6].
- **Neutral anchor.** If no view is neutral, warn "identity uncertain along expression-confounded directions" and suppress lip and lid measurements [rec BA-9].
- **Jaw.** A per-view hinge about the condylar axis, 10–13 mm anterior to tragion [rec BA-1 🧠], weighted by `jaw_weights`. σ is 1.5° when neutral, 3° when uncertain [rec MM-4 ↔️].
- **Mirror.** Each view is re-solved with u′ = W − u and swapped labels. If the robust cost falls by > 20% [com R1.6 🧠], or the pose lands > 3σ from its tag, the view is flagged. The user confirms; the engine never flips silently. A front-camera `LensModel` pre-flags the view.

### 3.7 Metric scale

The global log-scale g is fused from independent sources:

| Source | Residual |
|---|---|
| Measured references | (‖X_a − X_b‖ − L)/σ_L. Caliper ≈ 0.5 mm; ID-1 card 85.60 mm, σ 0.5 mm [com §4 🧠]. Warn when references disagree by > 1% [rec BA-10]. |
| Iris | A shared HVID D ~ N(11.8, 0.6²) mm ✅. Limbus σ 0.5–1 px [rec OPT-4 🧠]. Used only when the iris spans ≥ 20 px, both edges are sharp and there are no spectacles [anat R3.4, com §4]. |
| Population size | Exactly **one** of: global size σ 0.035 [anat §4 🧠], or IPD 63 ± 3.8 mm with vergence correction (≈ 2 mm less at 0.35 m [bl C3 🧠]). |

IPD and head size are correlated, so treating both as independent would understate σ_g.

Without a measured reference the output is tagged "scale: iris/prior, ±x%". Iris alone cannot beat ≈ 5% [anat/eye-region ✅ arithmetic].

### 3.8 Silhouettes and profiles

**Masks.** Masks are painted in Blender or produced by an optional helper (SAM 2, Apache-2.0 [eth §5]). They are converted to labelled polylines: skin boundary, hair-occluded boundary, occluder.

**Model contour.** For each view, the model's occluding contour is computed *sub-vertex*. On every edge (a, b) where g = n·(x − C_v) changes sign, the contour point is p = x_a + g_a/(g_a − g_b)·(x_b − x_a). Points are kept only if they lie on the boundary of the rasterised model mask. Vertex-level contours, as in the current `silhouette_vertices`, carry a bias of up to half an edge, which is 1–2 mm on a 13k-vertex head.

**Residuals.** Correspondences are fixed per outer iteration:
- **Forward** (photo → model): r = n_cᵀ(π_v(p_a(j)) − c_j)/σ_sil, with σ_sil = 1–2 px [bl S2 🧠].
- **Backward** (model → photo): truncated at 3σ, weight 0.5 *(design default)*. The current code is forward-only, so it ignores model contour that overshoots the photo outline.
- **Hair-occluded segments:** one-sided hinge max(0, −sd(π(p)))/σ. Only skin outside the hair hull is penalised. Scalp vertices stay ≥ 2 mm inside, and an inward prior of 5–15 mm applies [bl W7, rec MM-13 🧠].
- **No silhouette** above the trichion or on occluded ears [bl S3].

**Profiles.** When |yaw| > 60°, contour landmarks are replaced by the silhouette term and its weight is raised [rec BA-4, SIL-2].

**Diagnosis.** If interior points fit but the contour and ears do not, report "focal or distance wrong" rather than a shape error [rec SIL-3].

### 3.9 Dense refinement

**(a) Warp.** The engine keeps the existing RBF → bilaplacian chain (φ = r; λᵢ = α·σᵢ² with α 10⁻³–10⁻¹; constraint weight 10³ [rec MM-8, MM-9]). Laplacian weights vary per vertex: ligament strips ×3–5, lid margins 3.0, lips 0.3, forehead 0.5 [anat R5.9 🧠]. A fold gate requires det J > 0.2 [rec MM-11].

**(b) Photo-consistency normal sweep** (new; the main dense signal for T1/T2). Run it for each vertex k seen by view pairs with a 10–45° baseline and a mm/px small enough for the band [anat R5.11 🧠]:
1. Sweep h ∈ [−H_k, H_k] along the normal n_k in 0.2 mm steps, with H_k = min(3σ_n,k, 3 mm).
2. Project a 7×7 tangent-plane patch into each view (bilinear sampling).
3. Score S_k(h) = Σ_ab w_ab·NCC_ab(h); NCC is invariant to per-view gain and offset.
4. Fit a parabola at the peak to get ĥ_k. Confidence c_k combines curvature, peak ratio and patch contrast. Accept only where NCC > 0.7.
5. Solve min Σ c_k(h_k − ĥ_k)² + λ hᵀLᵀM⁻¹Lh by CG (exists).

The pass is rejected if any landmark moves > 0.5 mm or any view's landmark RMS rises > 0.5% IOD [com R5.2, R5.10 🧠]. The sweep step, patch size and NCC threshold are *(design defaults)*. Visibility comes from `mesh/raster.py`.

**(c) Shading detail** (optional, off by default). SH9 lighting is fitted per view on the S4 surface:
- Huber 0.05 on log residuals;
- the top 2–5% of pixels and n·v < 0.3 are excluded;
- a light-from-above prior, elevation N(30°, 25°) [bl T6 🧠].

The high-pass normal residual (< 5 mm wavelength; clamp ±2.5 mm [rec OPT-1 🧠]) is integrated by a Poisson solve and written **only** to a `detail_inferred` layer, never to the base shape.

### 3.10 Texture projection

- **Visibility and G-buffer:** z-buffer visibility (ε = max(1 mm, 2σ_geom)) and a UV G-buffer at texel centres (i + 0.5)/N [rec TEX-1].
- **View weight:** w = vis·cos²θ·footprint·edge, fading from 60° to a cut at 75° [rec TEX-2 🧠].
- **Gains:** solved in the log domain with mean log g = 0 [rec TEX-3].
- **Blend:** two-band, split at σ 3 mm. Fill order: mirror (low band only) → harmonic → model [rec TEX-4, TEX-5].
- **Map size:** 4096 (2048 for phones) [rec TEX-7].
- **Gate:** projection runs only when landmark reprojection has median ≤ 1.5 px and max ≤ 3 px [bl T2 🧠].
- **Rights:** the texture path requires the `TEXTURE` scope and `rights_basis ≠ unknown` [eth §3].
- **QA use:** the per-texel cross-view variance after gain compensation is a **geometry error locator**. Doubled features mean misregistration.

### 3.11 Uncertainty, QA metrics and next-best view

**Posterior.** The Laplace approximation is Σ_θ = (JᵀWJ)⁻¹ at the IRLS weights. Cameras are marginalised by Schur complement. The per-vertex normal σ is

  σ_n,k = √(n_kᵀ J_k Σ_θ J_kᵀ n_k)

and the evidence fraction is

  k_k = 1 − σ²_n,post/σ²_n,prior  [anat/face-perception-likeness 🧠]

Regions are labelled measured (k ≥ 0.8), partial (0.5–0.8) or prior-driven (< 0.5). A k < 0.8 on any of the top-5 perceptual regions asks for another view [anat §6].

**Calibration.** A Laplace σ ignores model error, so it is too small. Leave-one-view-out (LOVO) gives

  γ² = mean(r²_held/σ²_pred)

and the engine reports γ·σ, with γ itself shown.

**Gates.**
- Prior share of Fisher information > 20% in a region seen by ≥ 2 views [anat R1.4 🧠] means σ_pop is too tight or the data are weak.
- ‖β‖² > χ²_K at the 99.9% level (86.7 for K = 50), or ‖c̃‖² < k − 2√(2k), signals implausibility or shrinkage [rec MM-5, com R5.8 🧠].
- Focal: *measured* if σ_post(log f) < 0.10 [bl C2]; *prior used* if > 0.8·σ_prior [rec CAM-7].
- Perspective strength is reported as P = 100 mm/z.

**Next-best view.** For candidate poses (yaw −90…90° in 15° steps, pitch −20/0/20°) at the user's lens and distance, the engine simulates landmark and silhouette Jacobians J_c on the current fit. It then ranks candidates by the likeness-weighted gain

  G = Σ_r w_r·[log σ²_r − log σ²_r(Σ_θ⁻¹ + J_cᵀW J_c)]

where w_r is the perceptual weight per region (`benchmarks-metrics.json:acceptance_targets`). This is a rank-update and costs milliseconds.

## 4. Blender add-on design

### 4.1 Package and manifest

The source lives in `addon/face3d_blender/`. `tools/build_extension.py` vendors `face3d/` into it as `engine/` with relative imports. The extension carries no compiled wheels [bl/blender-extensions-packaging].

```toml
schema_version = "1.0.0"
id = "face3d_likeness"
version = "0.1.0"
name = "Face3D Likeness"
tagline = "Fit a measured likeness head to consented photos"
maintainer = "Face3D contributors <maintainers@example.invalid>"
type = "add-on"
blender_version_min = "4.5.0"   # oldest LTS CI will test; 4.2 code-compatible but EOL
license = ["SPDX:GPL-3.0-or-later"]
copyright = ["2026 Face3D contributors"]
[permissions]
files = "Read photos, landmark JSON and templates; write fit results"
[build]
paths_exclude_pattern = ["__pycache__/", "/tests/", "*.blend1"]
```

- **No `network` permission in the core.** The core never touches the network [eth A3, A7].
- **Template.** The CC0 template is bundled only after its licence is verified (budget ≤ 25 MB [bl Q5]). Until then, `face3d.template_import` builds it from the user's MPFB2 install.
- **Persistent data** lives in `extension_path_user` [bl L6].
- **Probing.** `compat.py` probes features at `register()`; a failing backend is disabled with a UI message [bl A9].

### 4.2 Operators

All operators are `bl_options = {'REGISTER', 'UNDO'}` unless noted.

| Operator | Function |
|---|---|
| `face3d.project_new` / `consent_edit` | Create the project; the ConsentRecord form; default-deny gates [eth §3]. |
| `face3d.photos_add` | File browser; EXIF; orientation baked into working copies; groups; gates; one camera per photo with its background image. |
| `face3d.landmarks_detect` | Runs the external helper (§4.6) as a subprocess; never in-process. |
| `face3d.landmarks_import` | Imports `*.lmk.json`. |
| `face3d.pin_edit` | Modal tool in camera view: drag a pin; σ 1–2 screen px at the placement zoom [com R3.3]. |
| `face3d.mask_edit` | Paint and label masks in Image Editor; polyline extraction. |
| `face3d.solve` | Starts a background job for the chosen stage S0–S4 (not UNDO itself). |
| `face3d.solve_cancel` | Cancels the job. |
| `face3d.apply_result` | One undo step: shape keys, cameras, attributes [bl K1–K4]. |
| `face3d.next_view` | Shows the next-best-photo suggestion with a ghost camera. |
| `face3d.texture_project` | Background job, then bake to image. |
| `face3d.handoff_multires` | Bakes the key mix to a copy and reshapes Multires [bl K5]. |
| `face3d.qa_report` | Writes the breakdown sheet and region table [com R8.1, R8.2]. |
| `face3d.prepare_for_sharing` / `purge` | Biometric leftover purge [eth F9]. |

### 4.3 Panels and overlays

The sidebar tab "Face3D" has these panels:
- **Project & Consent.**
- **Photos:** a UIList with per-photo status icons for landmarks, mirror, expression tag, focal group, gates and LOVO error.
- **Solve:** stage buttons, progress, a log.
- **Accuracy:** region table with RMS-to-data, σ, k and label; focal and scale observability; flags worst first.
- **Likeness Review.**
- **Hand-off.**

Overlays use `gpu` POST_PIXEL draw handlers in camera view:
- detected landmarks against reprojected model points;
- residual arrows coloured by z-score;
- the photo mask contour against the model silhouette;
- a held-out-view badge.

Colour attributes `f3d_sigma_n_mm`, `f3d_evidence` and `f3d_region` drive viewport heat maps. Likeness Review offers matched-camera switching (render resolution follows the active camera via markers [bl C5]), background opacity 0.3–0.5, a blink comparator, and an edge/difference overlay [com R6.4, R8.1].

### 4.4 Jobs, threading and undo

- **Inputs:** the bridge copies arrays (float32 → float64) into a job folder [bl A3].
- **Process:** `sys.executable -I -m face3d_blender.engine.cli` runs as a subprocess. stdout carries JSON-lines progress. A `bpy.app.timers` poll at 0.1 s does ≤ 10 ms of work per tick [bl A5].
- **Completion:** the job ends in a "Ready – Apply" state. Applying is a separate undoable operator that re-fetches objects by name and refuses on a topology-hash mismatch, or while the object is in Edit or Sculpt mode [bl K1, K4].
- **Background mode:** `blender -b` runs a synchronous path.

### 4.5 Shape keys and Multires hand-off

**Keys.** These follow [bl K2, rec SK-1]:
- `Basis` = template;
- stage keys `f3d_S1_similarity`, `f3d_S2_shape`, `f3d_S3_silhouette`, `f3d_S4_dense`;
- `f3d_ID_fit`, the final key (`slider_max` 1.5);
- `f3d_asym`, `f3d_detail_measured`, `f3d_detail_inferred`;
- `f3d_caricature`, a preview slider for S(α) = M + α(S − M) [com R6.2];
- `artist`, never overwritten by refits [bl K3].

Python writes to Basis add Δ to every dependent key [bl K3]. Per-photo expression keys `fit_<photo>` are created only with the `RIG_ANIMATE` scope [eth F4].

**Artist edits as data.** A sculpt mask m becomes a data weight (1 − m) plus a pin term at σ 0.1–0.3 mm [bl W5].

**Multires.** The cage is fitted through limit stencils, so Multires levels 2 (likeness) and 3 (detail) [rec SK-3] land on the data without the 0.1–0.4 mm shrink at lips and nose tip [bl W4]. Detail reaches Multires only through `multires_reshape` from a displaced subdivided copy [bl K5].

### 4.6 Landmark helper

`tools/detect_landmarks.py` runs in the user's own Python, where the user has installed `mediapipe` themselves. It uses the MediaPipe Tasks `FaceLandmarker`:
- `running_mode=IMAGE`, `num_faces=2` (to detect bystanders [eth F1]);
- blendshapes and transformation matrix enabled;
- the `.task` model path supplied by the user and pinned by SHA-256.

It runs 6–10 test-time-augmentation passes (scale and shift jitter, plus horizontal flip through the computed `mirror_index`) to produce the per-point covariance [rec BA-2], then writes `*.lmk.json`.

An optional, separately published "detector pack" extension may bundle platform wheels if the platform permits compiled wheels ↔️ [bl/blender-extensions-packaging]. The core never depends on it.

## 5. Validation and QA

### 5.1 Synthetic test bed (runs here, no Blender)

The test bed lives in `face3d/synth/`:
- **Heads.** Procedural heads: an ellipsoid with analytic nose, brow, orbit, lip and chin features. They are explicitly non-anatomical and are perturbed by smooth random fields and asymmetry. When a template is present locally, they are replaced by the template plus a random adapter draw.
- **Cameras.** Rigs at 0.25–5 m, f35 13–200 mm, yaw ±90° [rec EV-5, com R8.4].
- **Detector simulator.**
  - anisotropic noise per class;
  - systematic per-point bias;
  - correlated dense noise (to exercise N_eff);
  - 5% outliers;
  - occlusion by yaw.
- **Images.** The numpy rasteriser renders silhouettes and Lambert + SH textured images (for NCC and gains).

### 5.2 Test classes and acceptance

| Class | Assertion |
|---|---|
| Exactness | Noiseless: reprojection < 1e-6 px; vertex RMS < 1e-6·scale [bl Q1]. Engine-to-Blender camera agreement < 0.01 px (a Blender round trip runs only where the PyPI `bpy` module exists; skipped here) [bl C4]. |
| Calibration | Over 200 seeded trials: normalised χ²/dof in [0.8, 1.2]; posterior coverage 60–76% within 1σ and 90–98% within 2σ, per region, after γ. |
| Observability | Frontal-only sets label nose projection prior-driven. Focal is flagged "not observable" at z ≥ 2 m without EXIF. Focal error < 5% and rotation error < 2° when yaw spans ≥ 60° [com R8.4 🧠]. |
| Accuracy | T1 synthetic, σ at detector-realistic levels, per-region RMS ≤ `acceptance_targets`: eyes and lips 1.0, brows 1.2, nose 1.2, nose projection 1.5, forehead and cheeks 1.5, jaw and chin 2.0, ears and cranium 3.0 mm [`benchmarks-metrics.json` 🧠]. Profile error at prn and pg ≤ 1.5 mm [rec SIL-3]. Scale ≤ 1.5% with a reference. |
| Robustness | Mirrored view detected in ≥ 95% of asymmetric trials. A smiling view shifts neutral-region identity by < 0.3 mm *(design default)*. The outlier view is flagged. |
| Regression | A golden per-region error table (rtol 1e-5, never bit-exact [bl Q2]). Any stage that worsens likeness-weighted error by > 2% fails CI. |
| Policy | No `bpy` import under `face3d/` (AST check). Socket guard during a full run [eth A7]. Manifest parsed with `tomllib` and checked against required keys. SPDX entry for every bundled file [eth §5]. |

**Error metrics** [rec EV-1, EV-2]:
- exact point-to-triangle distance (no nearest-vertex shortcut);
- NoW-style 7-landmark rigid alignment, plus similarity-ICP variants;
- median, mean, RMS, p95, F@0.5/1/2 mm and signed bias per region;
- a likeness-weighted score E_like = Σ w_r RMS_r / Σ w_r.

### 5.3 Honest-uncertainty reporting

Every result states:
- tier;
- scale mode and σ;
- focal status per group;
- per-region RMS-to-data, γ·σ, k and label;
- LOVO error on ≥ 2 held-out photos [com R8.2];
- flags, worst first.

Claims never exceed the reference modality (0.2–1 mm) [bl Q4]. Without a neutral view, lid and lip numbers are suppressed.

### 5.4 Likeness checks shown to the artist

- **Matched-camera comparison** for every photo: clay render against the photo, blink at 3 Hz, edge overlay, and a 64 px thumbnail (the 8–16 cycles-per-face band [anat/face-perception-likeness 📄]).
- **Held-out views** rendered *before* the artist sees their error.
- **Region bars** against the export tolerances. Lid margins, vermilion and alar rim 0.2–0.3 mm; nose tip and chin 0.5 mm [com R8.6 🧠]. Exceeding them blocks "approved".
- **Shrinkage audit** with a protect list: the 3–5 largest |z| deviations are never pulled toward canons [anat/face-perception-likeness 🧠].
- **Familiar-viewer checklist** with eyes, brows and hair in place.

## 6. Milestones

Each milestone ships as a tagged release with passing CI here.

| M | Deliverable | Acceptance |
|---|---|---|
| **M1** Measurement first | `eval/`, `synth/`, `mesh/raster.py`, `mesh/distance.py`; baseline report of the current engine | Distances on analytic spheres and planes exact to 1e-9; rasteriser silhouette equals `silhouette_vertices` on convex meshes; baseline per-region table committed; suite < 90 s |
| **M2** Observation model and cameras | `obs/*`, scheme registry, inverse-depth cameras, PnP restarts, Huber 2σ / 4σ rejection, mirror test, observability report | Calibration and observability rows of §5.2 pass; ≥ 20% lower nose-projection error than M1 baseline on T1 sweeps |
| **M3** Metric scale | `solve/scale.py`, iris limbus fit, references, fusion, tags | Scale ≤ 1.5% with caliper; iris-only σ reported 4–6% and true error within 2σ in ≥ 95% of trials |
| **M4** Shape model and expression | `model/*`, `priors/*` (tables built from `research/data`), `solve/joint.py`, expression marginalisation and EM, jaw | Accuracy row for eyes, lips and nose on T1; smile-robustness row; χ² and shrinkage gates fire on crafted cases |
| **M5** Silhouettes and profiles | Sub-vertex contours, two-way chamfer, hair hinge, joint residuals, PNG mask I/O | prn and pg ≤ 1.5 mm; jaw ≤ 2.0 mm; "focal or distance wrong" diagnosis triggers on a mis-set focal |
| **M6** Extension MVP | `addon/` (manifest, bridge, import, solve job, apply, cameras, keys), template kit, helper script, `cli.py` | Policy row passes; bridge maths (axis map, key deltas, camera dicts) unit-tested in numpy; job runner test runs `cli` on a synthetic project; Blender round trip queued for CI with Blender |
| **M7** Dense and review | Photo-consistency sweep, limit stencils, next-best view, QA panel, overlays | Sweep lowers feature-region error ≥ 20% at ≤ 0.25 mm/px with 2 views 20–40° apart and never worsens other regions > 0.1 mm; the next-best view picks the profile for frontal-only sets |
| **M8** Texture and options | `texture/project.py`, shading detail layer, `flame_open` adapter | TEX-8: gains within 2%, no occluded leakage [rec TEX-8]; the FLAME adapter refuses on a `basis_sha256` mismatch and records attribution |

## 7. Risks and deliberate omissions

### Risks

- **No permissive statistical covariance.** The default prior is weaker than a 3DMM, so T0/T1 depth in unobserved regions stays near the template. *Mitigation:* honest labels, the next-best view, and the FLAME Open adapter. FLAME 2023 Open's contents are unverified 📄.
- **All 🧠 σ and gates are uncalibrated,** and synthetic data do not reproduce real detector bias. *Mitigation:* γ calibration, plus the validation-test-bed gap topic (consented captures with reference scans).
- **The MediaPipe weights licence is ↔️,** and its anatomical index map is 🧠. *Mitigation:* the helper stays external, pins remain, and index-map verification is a template-kit acceptance step.
- **Phone computational photography** (HDR, beauty or face warping, portrait blur) breaks photo-consistency and geometry. *Mitigation:* gates, a capture protocol (beauty modes off, rear main or tele camera), and NCC rejection.
- **Performance.** Dense LM in numpy needs ≤ 2,000 shared parameters, and the photo-consistency sweep is O(V·pairs·steps). *Mitigation:* reduced bases and per-region scheduling.
- **Extension platform rules** on wheels, downloads and non-CC0 data are ↔️, which affects the detector pack and the MediaPipe correspondence table.
- **Likeness thresholds in mm** are unknown [com §11 Q1]. The perceptual weights are 🧠.

### Deliberately left out

- **Learned regressors** (MICA, DECA, 3DDFA): research licences, and weak-perspective depth leaks [rec MM-6, LIC-1]. They are allowed only as an opt-in import that never sets depth or scale.
- **Generative 3D heads and monocular depth or normal networks in identity:** zero weight [rec OPT-2].
- **Gaussian avatars, hair strands, teeth, ears beyond silhouettes, full inverse rendering of albedo, identity-embedding losses** [rec OPT-3–OPT-7].
- **Differentiable GPU rendering.**
- **Fitting minors** without guardian consent and age-matched priors [eth F5].
- **Any network path in the core.**
