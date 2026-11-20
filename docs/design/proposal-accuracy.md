# Proposal: an accuracy-first photo-to-head engine and Blender extension

*Design angle: geometric and perceptual likeness accuracy. Written 2026-11-20 against `face3d/` at `fe13b73` (42 tests passing) and `research/_raw/requirements_*.md`.*

**Citations** take the form `[area/topic badge]` or a digest rule ID. Areas: `rec` reconstruction, `anat` anatomy, `bl` blender, `com` community, `eth` ethics. Badges: ✅ verified, 📄 single-sourced, 🧠 expert, ↔️ contested.
- **Every 🧠 number is a named, tunable default.**
- *(design default)* marks this proposal's own uncalibrated starting values, which M1 tunes.

## 0. Principles

1. **Measure before building.** A stage merges only after the synthetic harness shows it lowers per-region error in millimetres.
2. **Declare what each signal can determine.** A prior is never reported as a measurement.
3. **Ship the uncertainty.** Every vertex carries a σ, and every region is labelled *measured*, *partial* or *prior-driven*.
4. **Priors fill only what nothing observes.** Likeness is deviation from the mean, so shrinkage is audited [anat/face-perception-likeness 🧠].
5. **Fabricate nothing.** Templates, landmark tables and prior tables are built by scripts from licensed sources, with hashes and badges (§2.4).

## 1. Vision and user journey

**Vision.** Photos of a consenting sitter become a Blender head that is measurably closer to the real person, region by region, than existing Blender tools. It comes with an honest map of what is measured and what is guessed, and it is ready to sculpt.

### 1.1 What each signal can determine

| Signal | Determines | Cannot determine | Typical σ |
|---|---|---|---|
| Frontal landmarks | Lateral layout | Depth; focal vs distance | Lateral 0.5–1 mm (≥ 3 views). Depth 10–20 mm frontal-only [anat/face-perception-likeness 🧠] |
| Views ≥ 30° apart | Depth | Scale | ≈ 2× lateral [same 🧠; bl C7] |
| Profile silhouette | Midline profile; jaw outline | Anything under hair | 1–2 px [bl S2 🧠] |
| Near-camera perspective | Distance z, but only if depth relief is known | z beyond ≈ 1 m; identity confounds it | Focal error 2–12% at 0.3 m, unobservable at 2 m [rec/camera-perspective-distortion 🧠] |
| EXIF focal | f (breaks the dolly-zoom ambiguity) | Crops, digital zoom | log-σ 0.03–0.04 [rec CAM-6 🧠] |
| Iris | Metric scale | — | HVID 11.8 ± 0.6 mm ✅ [anat/eye-region], ≈ 5% |
| Caliper, PD, card | Metric scale | — | 0.5–1 mm [anat R3.4 🧠] |
| Cross-view photo-consistency | Offsets along normals | Textureless skin | ±3 mm sweep *(design default)* |
| Shading | Fine normals | Low-frequency shape (bas-relief ambiguity) | Wavelengths < 5 mm only [anat R5.11 🧠] |

### 1.2 The journey

1. **Consent.** A `ConsentRecord` with the `RECONSTRUCT` scope that lists every photo's sha256 [eth §3].
2. **Capture plan, by accuracy tier.**
   - **T0**, front only: proportions only, depth labelled prior-driven.
   - **T1**, 5–9 photos: front, ±30–45°, ±90° profiles and a low view, from the rear main camera at ≥ 1 m [com R1.4–R1.7, bl T4 🧠].
   - **T2**, T1 plus one measured length: scale ≤ 1.5% [rec EV-3 🧠].
   - **T3**, a dense set with COLMAP cameras imported (BSD licence) [rec FMT-7, BA-12]: bounded by the scan floor of 0.2–0.5 mm [rec EV-4 ↔️].
3. **Ingest.** EXIF, orientation baking, focal groups, and gates for blink, blur, size, clipping and mirroring [com R1.1–R1.6].
4. **Landmarks.** An external MediaPipe helper writes JSON. Manual pins are always available, so the pipeline works with no downloads [eth A4].
5. **Solve.** Staged joint estimation runs as a background job (§3.5).
6. **Review.** Matched-camera overlays, held-out-view error, σ and evidence heat maps, and a **next-best-photo advisor** (§3.11).
7. **Correct.** Pins, masks and sculpt edits become observations with a σ, cross-validated against the other views [com R5.10, bl W5].
8. **Hand-off.** Staged shape keys, a Multires-ready cage fitted to the limit surface, an optional texture, and a sidecar with QA.

## 2. Architecture

### 2.1 Layers

```
L0 policy/            consent gates, licence taint, data classes
L1 io/, schemes/      project, landmark, template, result formats
L2 obs/               noise, visibility, contours, quality, mirror
L3 model/, priors/    shape adapters, anatomical priors
L4 solve/             PnP, joint LM + Schur, observability, scale, expression
L5 fit/, texture/     silhouettes, dense warp, photo-consistency, shading, projection
L6 eval/, synth/      metrics, regions, procedural test bed, numpy rasteriser
L7 pipeline.py, cli.py   staged orchestration (subprocess entry point)
L8 addon/face3d_blender/ GPL extension: bridge, operators, panels, overlays, jobs
L9 tools/             detector helper, template kit, prior builder (not imported by engine)
```

- L0–L7 import only `numpy`, `math`, `json`, `zlib` and `tomllib`, and are NumPy 1/2-neutral [bl A1, A4].
- Only `bridge.py` converts between bpy data and arrays [bl A2, A3].

### 2.2 Modules

Status: **exists**, **extend** or **new**.

**Exists, kept as is:**
- `solve/{bundle,triangulate,reconstruct}.py`: landmark-only bundle adjustment, kept for the fixed-camera T3 path and as scaffolding;
- `mesh/{core,sparse}.py`.

**Extend:**
- `geometry/camera.py`: inverse-depth parameters, crop-aware principal point, optional k1. The Blender export already exists.
- `geometry/procrustes.py`: weighted reflection Procrustes [anat R3.3].
- `geometry/rbf.py`: per-landmark λᵢ = α·σᵢ² (the sign fix is done) [rec MM-8].
- `io/exif.py`: date, crop hints, group key [com R1.3].
- `solve/lm.py`: block normal equations, Schur elimination, QR fallback [rec BA-6].
- `solve/pnp.py`: hypotheses, flip restarts, cheirality [rec CAM-3].
- `fit/silhouette.py`: sub-vertex contours, two-way chamfer, hair hinge.
- `fit/template.py`: region stiffness, caps, fold gates.
- `mesh/{laplacian,reduced}.py`: per-vertex weights; null-space projection of the similarity transform.
- `synthetic.py` → `synth/`: heads, rigs, detector simulator, renderer.

**New:**
- `io/{png,project,landmarks,template,results}.py`: zlib PNG I/O and validators.
- `schemes/*.json`.
- `obs/{noise,visibility,contours,quality,mirror}.py`.
- `model/{adapter,template_rbf,mpfb_targets,flame_open,embedding,limit}.py`.
- `priors/{tables,anatomical}.py`.
- `solve/{joint,observability,scale,expression}.py`.
- `fit/{photoconsistency,shading}.py`.
- `mesh/{raster,distance}.py`: rasteriser; exact point-to-triangle distance [rec EV-1].
- `texture/project.py`.
- `eval/{metrics,align,regions,report}.py`.
- `policy/{consent,licence}.py` [eth A2].
- `pipeline.py`, `cli.py`.
- `addon/face3d_blender/` (§4).
- `tools/{detect_landmarks.py, template_kit/, build_priors.py, build_extension.py}`.

All engine paths are under `face3d/`.

### 2.3 Data flow

```
photos ─► ingest ─► *.lmk.json ◄─ helper | pins        template kit ─► Template ─► ModelAdapter ◄─ priors
   S0 PnP ─► S1 rigid + mirror ─► S2 shape + expression EM ─► S3 + silhouettes ─► S4 dense ─► QA
   ─► fit.npz + fit.json ─► bridge ─► shape keys, cameras, attributes, texture
```

### 2.4 Data formats

Everything is JSON plus `.npz` arrays. Every object carries `{source, version, licence, commercial_ok, measured|generated, consent_id}` [rec INV-3] and a `data_class` [eth §2.2].

**Project (`project.f3d.json`).**
- `consent_id`.
- `photos[]`, each with:
  - `sha256`, `rights_basis`;
  - EXIF data, `focal_group`;
  - `view_tag` (nominal yaw and pitch);
  - `mirrored`, `crop_px`, `expression_tag`;
  - a `landmarks` reference;
  - `masks` (labelled PNGs: skin, hair, background, occluder);
  - `pins[]`.
- `scale_refs[{a, b, length_mm, sigma_mm}]`.
- `template_ref`, `model_ref`.
- `settings` (every 🧠 default, by name).

**Landmark scheme (`schemes/<id>.json`).**
- `points[{index, abbr, kind ∈ {anchor, contour, extremal, iris}, side, mirror_index, class, sigma_n, sigma_t, badge}]`;
- `contours[]`, `canonical_mesh_sha256`.

The MediaPipe anatomical map is 🧠 [anat R2.4]. It is verified by rendering labels on the canonical mesh. `mirror_index` is *computed* as the nearest neighbour of each reflected canonical vertex, with the residual stored.

**Observation (`*.lmk.json`)** [rec FMT-1, bl D1].
- `{scheme, detector_version, model_sha256, image_wh, exif_applied, mirrored, coord: "px_corner_origin"}`;
- `uv`, `visible`, optional `cov[N][2][2]` (from TTA spread), `blendshapes`, `transform`, `n_faces`.

**Template sidecar.**
- `{template_id, licence, sha256, topology_hash, n_verts, units: "mm"}`;
- `regions` (about 20, matching §5.2), `symmetry_map`, `midline`;
- `embeddings{scheme: (tri, bary, bias, σ_annot)}`, `contour_chains`;
- `stiffness` [anat R5.9];
- `jaw_weights` plus the condylar axis;
- `exclude` (eyeballs, mouth interior);
- `uv`, `limit_stencils`.

*How the template and tables are obtained:*
- `tools/template_kit/extract.py` runs in Blender on the user's MPFB2 install (hm08 base CC0 📄 [eth §5]; 2.0.16 vs 2.0.18 is ↔️). The fallback is Blender Studio Human Base Meshes (CC0 ✅ [com L2]).
- Two annotators click the anatomical landmarks against the craniometric definitions [anat R2.1]. Their disagreement becomes σ_annot.
- The MediaPipe-478 embedding comes from registering the Apache-2.0 canonical mesh: anchors first, then NICP [rec MM-12].
- Per-point detector bias is calibrated on consented captures with reference scans (validation-test-bed topic).
- `tools/build_priors.py` converts `research/data/*.json` rows into prior tables, carrying each row's badge and source.

**Results.**
- `fit.npz`: stage vertices, `β`, `c`, `ψ_v`, `θ_v`, σ_n, evidence k.
- `fit.json`:
  - cameras (OpenCV and Blender form);
  - scale mode (`measured|iris|prior`) and σ;
  - focal status per group;
  - flags, QA tables;
  - provenance [bl D6];
  - licence taint.

### 2.5 Coordinate conventions

- **Image.** Continuous pixels, origin at the top-left *corner*, y down; pixel (i, j) is centred at (i + 0.5, j + 0.5). Orientation is baked before any coordinate is stored. MediaPipe normalised coordinates map as (x·W, y·H), verified by a synthetic test. Blender `img.pixels` rows run bottom-up.
- **Camera.** OpenCV convention, X_c = R·X + t; updates are R ← exp([δ]×)·R.
- **Head.** float64 mm; +x is the subject's left, +y up, +z out of the face. The template fixes the gauge. A separate presentation transform levels the head to a tragion–orbitale proxy (0 ± 5 mm 🧠 [anat/ear]).
- **Blender.** 1 BU = 1 m. P_bl = 0.001·A·P_head, with A = R_x(+90°) = [[1,0,0],[0,0,−1],[0,1,0]] [anat R1.1].
- **Blender camera.** Axes map by diag(1, −1, −1). `lens = f·36/W`, `HORIZONTAL` fit, `shift_x = (W/2 − c_x)/W`, `shift_y = (c_y − H/2)/W` (exists) [bl C4].
- **Precision.** float32 only at the bpy boundary.

## 3. Algorithms

### 3.1 Ingest and focal priors

The pixel focal length is f_px = f35·√(W² + H²)/43.27 (diagonal convention ↔️ [rec CAM-2]).

| Source | Prior on log f [rec CAM-6, com R2.2 🧠] |
|---|---|
| EXIF, uncropped | σ 0.03–0.04 |
| Crop suspected | σ 0.08 |
| Crop unknown | σ 0.35 |
| Phone without EXIF | 26 mm, σ 0.25 |
| Nothing known | 50 mm, σ 0.6 |

- **Groups** are keyed on (Make, Model, LensModel, f35, W, H, still/video), with a tie σ of 0.02 [rec CAM-5].
- **Distance** priors on log z: selfie 0.35 m (σ 0.3), rear camera 0.8 m (0.4), tele 2 m (0.4), unknown 1 m (0.7) [rec CAM-6, com R2.4 🧠]. Bounds are 0.25–10 m [bl C6].
- **Wide lenses:** if f35 ≤ 16 mm, or the face lies beyond 60% of the half-diagonal, inflate σ ×2 or exclude [com R1.7 🧠].

### 3.2 Camera parameterisation and initialisation

Each view v has rotation ω_v, offset τ_v ∈ ℝ², a_v = log s_v (px/mm) and ℓ_v = log ρ_v (ρ = 1/z):

  u = c + s_v·((R_vX)ₓᵧ + τ_v)/(1 + ρ_v·(R_vX)_z),  f_v = s_v/ρ_v  [rec CAM-4]

The dolly-zoom direction is now one coordinate, and the weak-perspective limit ρ → 0 stays regular.

- **Focal groups:** the tie residual (a_v − ℓ_v − φ_g)/σ_tie, with the focal prior on φ_g.
- **PnP initialisation:**
  - f35 hypotheses {13, 24, 26, 35, 50, 77, 85, 120, 135, 200} mm (the code has 7 of these);
  - pitch-flip and yaw-mirror restarts;
  - a cheirality check [rec CAM-3 🧠].
- **Tag priors:** yaw σ 10° (5° with floor marks), pitch 5°, roll 3° [com R2.7 🧠].

### 3.3 Observation model

  r_vi = L_vi⁻¹(û_vi(θ) − u_vi),  L L ᵀ = Σ_vi = IOD_v²·σ²_cls,i·R_i diag(1, κ_i²) R_iᵀ·η + P_vi Σ_expr,vi P_viᵀ

- **IOD_v** := s_v·63 mm. It is defined once and is not foreshortened by yaw [bl table P].
- **σ_cls** in % IOD: anchors 1.5, lid and lip contours 2.5, oval 4, iris 1, user pin 0.75 [bl table P 🧠].
- **Contours:** κ ≥ 5, so points slide along the curve. R_i follows the projected model curve and is refreshed every outer iteration [rec BA-2].
- **η** = N/N_eff (N_eff 60–100) for dense MediaPipe points [rec BA-2 🧠]. Without it, 478 correlated points over-count by about 5×.
- **P_vi** = ∂û/∂X carries expression covariance into the image (§3.6).
- **Visibility:**
  - weight ramps from 0 at n·(−v) = cos 80° to 1 at cos 60°;
  - far-side oval points are dropped when |yaw| > 25°;
  - MediaPipe z is ignored with ≥ 2 views [rec BA-3, bl D2 🧠].
- **Known detector biases** (an epicanthal fold read as en, σ 2.5 mm; prn pulled 1–2 mm toward the highlight [anat §6]) enter as embedding offsets.
- **Robust loss:** Huber δ = 2σ. After convergence, drop > 4σ and re-solve. Flag a view when > 15% of its points are rejected [rec BA-5 🧠].
- **Extremal points** (g′, zy′, go′, pg′) are a softmax argmax over a region, temperature 1–2 mm, re-evaluated per pose [anat R3.2].

### 3.4 Shape model and priors

  V(g, β, c) = e^g·(T̄ + S·β + Φ·Πc)

- **T̄** is evaluated through limit stencils when the delivery is Multires [bl W4].
- **Φ** is the existing Gaussian-RBF reduced basis.
- **Π** projects out the 7-DoF similarity at the anchor landmarks. Without it, Φc trades rigid motion with the cameras: a gauge leak in the current design [rec BA-7].

| Adapter | S | Prior | Licence |
|---|---|---|---|
| `template_rbf` (default) | none | Anisotropic landmark prior on X_i/e^g: sharp junctions 1–1.5 mm; prn and pg′ 1–2 mm normal, 2–4 mm tangential; g and n (3, 4, 2); zy and go (6, 8, 8); 8 mm fallback [anat R4.1, `craniometric-landmarks.json` 🧠]. Log-ratio priors at σ×2 [anat R4.3]. Ordering hinges [anat R5.2]. RKHS ½λ_c cᵀK_cc c. | CC0 |
| `mpfb_targets` | User's MPFB2 face targets | N(0, 0.5²), clipped to ±1; macros σ 0.15 [bl table P 🧠]. A *plausibility* prior, not a covariance. | CC0 📄 |
| `flame_open` | FLAME 2023 Open, transferred locally as U′ = (W ⊗ I₃)U and never shipped [rec MM-7] | β ~ N(0, I); K_β 20 → 50 [rec MM-3 🧠]; Student-t ν = 4 option [anat §4] | CC-BY-4.0, contents unverified 📄 |

**Honesty.** Without a permissive covariance, the default prior is per-landmark. Depth that nothing observes therefore stays near the template, and the engine **reports** this (§3.11).

**Symmetry** d = X_l − M·X_r, per-pair σ [anat R4.2 🧠]:
- canthi and lids 0.7–1.0 mm; alare and zygion 1.0–1.5 mm; cheilion 1.5–2.0 mm; gonion 2.5–3.0 mm; ears 3–4 mm;
- midline x: n and g 0.75–1.0 mm, prn and sn 1.5–2.0 mm, pg 2–3 mm.

The output is never symmetrised; asymmetry is exported as its own key [anat R5.9].

### 3.5 Joint estimation

The unknowns are θ = {cameras, φ_g, g, β, c, ψ_v, θ_jaw,v, D_iris}:

  E(θ) = Σ ρ_H(‖r_vi‖) + Σ ρ_H(r^sil) + Σ hinges + ½‖β‖² + ½λ_c cᵀK_cc c + Σ ½‖X_i/e^g − μ_i‖²_{Σ_pop,i⁻¹}
     + E_sym + E_ratio + Σ_v ½ψ_vᵀΛ_vψ_v + E_scale + E_focal + E_dist + E_pose

- **Solver:** LM with Nielsen damping (exists). Per-view blocks (≤ 30 parameters) are eliminated by Schur complement. The shared system (≤ ≈ 1,900 parameters) is solved by Cholesky.
- **Stages** [bl W1, com R5.1–5.2 🧠]:
  - **S0** PnP.
  - **S1** Similarity and cameras on Tier A anchors, plus the mirror test.
  - **S2** g, β (20 → 50) and coarse c (≈ 40 centres, 30–40 mm), plus expression EM (≤ 3 rounds).
  - **S3** All landmarks, silhouettes and fine c (≈ 600 centres, 10–20 mm). Cameras stay free, so profile silhouettes also correct pitch and f/z.
  - **S4** Per-vertex offsets (σ 2–3 mm, capped at 3–5 mm unless ≥ 2 views agree [rec MM-10]), driven only by dense data: §3.9, or a scan through NICP [rec MM-12].
- **Advance** a stage when landmark RMS is < 2–3% IOD and silhouettes are within 1–2 mm, or when gains fall below 1% per iteration.
- **S4 safety:** no landmark may move > 0.5 mm [com R5.2].
- **T3:** SfM cameras stay frozen. Landmarks never move them (≈ 0.5 px vs 10–14 px) [rec BA-12 🧠].

### 3.6 Expression, jaw and mirror

- **Tagging.** Blendshapes are scored relative to the subject's most neutral photo [rec/landmark-detection 🧠].
  - A view is non-neutral if: mouthSmile > 0.25; cheekSquint, eyeWide or browUp > 0.3; browDown > 0.35; eyeBlink > 0.4; or jawOpen > 0.08 [anat §6 🧠].
  - Re-tag by ‖ψ_v‖ (< 0.5 SD neutral, > 1.5 SD expressive) [rec BA-9].
- **With a basis E:** X_v = X + Eψ_v, with ψ ~ N(0, 0.3²) on neutral and N(0, 1) on expressive views [rec MM-4 🧠]. E is never orthogonalised against identity [rec BA-9 ↔️].
- **Default (no basis): expression is marginalised.**
  - Nuisance η_vi ~ N(0, m²_v,r·σ²_expr,r·I₃) integrates out exactly to the P Σ_expr Pᵀ term in §3.3.
  - m_v,r = clip(score_r/threshold_r, 0, 3).
  - σ_expr = 3 mm for the mouth, lids and brows and 1 mm elsewhere *(design default)*.
  - Neutral views thus dominate identity in mobile regions automatically.
  - Drop lip points when the inner gap/ch–ch > 0.04, and lid points on a blink (EAR < 0.2) or gaze pitch > 10–15° [anat §6, com R1.4].
- **No neutral view:** warn, and suppress lip and lid numbers [rec BA-9].
- **Jaw:** a hinge about the condylar axis, 10–13 mm anterior to tragion [rec BA-1 🧠]. σ 1.5° when neutral, 3° otherwise [rec MM-4 ↔️].
- **Mirror:** re-solve with u′ = W − u and swapped labels. Flag the view when the cost falls > 20% or its pose lands > 3σ from the tag [com R1.6, R2.7]. The user confirms; the engine never flips silently.

### 3.7 Metric scale

The global scale g is fused from independent sources:

| Source | Term |
|---|---|
| Measured references | (‖X_a − X_b‖ − L)/σ_L. Caliper 0.5 mm; ID-1 card 85.60 mm σ 0.5 [com §4 🧠]. Warn when references disagree by > 1% [rec BA-10]. |
| Iris | Shared D ~ N(11.8, 0.6²) mm ✅; limbus σ 0.5–1 px [rec OPT-4 🧠]. Only when the iris is ≥ 20 px, edges are sharp and there are no spectacles [anat R3.4]. |
| Population | Exactly **one** of: global size σ 0.035 [anat §4 🧠], or IPD 63 ± 3.8 mm with vergence correction (≈ 2 mm at 0.35 m [bl C3 🧠]). |

IPD and head size are correlated, so using both would understate σ_g. Iris alone cannot beat ≈ 5%. Without a reference, the output is tagged "scale: iris/prior ±x%".

### 3.8 Silhouettes and profiles

**Inputs.** Masks are painted in Blender, or come from an optional SAM 2 helper (Apache-2.0 [eth §5]). They become labelled polylines.

**Model contour, sub-vertex.** On each edge where g = n·(x − C_v) changes sign, the contour point is p = x_a + g_a/(g_a − g_b)·(x_b − x_a). Only points on the rasterised mask boundary are kept. The vertex-level contours in the current code carry up to half an edge of bias (1–2 mm).

**Residuals** (correspondences fixed per outer iteration):
- **Forward:** n_cᵀ(π(p) − c_j)/σ_sil, σ 1–2 px [bl S2 🧠].
- **Backward** (model → photo): truncated at 3σ, weight 0.5 *(design default)*. The code is forward-only today, so overshoot goes unpenalised.
- **Hair segments:** a one-sided hinge that penalises only skin outside the hull. The scalp stays ≥ 2 mm inside, with an inward prior of 5–15 mm [bl W7, rec MM-13].
- **No terms** above the trichion or on occluded ears [bl S3].

**Profiles.** When |yaw| > 60°, contour landmarks are replaced by the silhouette term [rec BA-4, SIL-2].

**Diagnosis.** If the interior fits but the contour and ears do not, report "focal or distance wrong" rather than a shape error [rec SIL-3].

### 3.9 Dense refinement

**(a) Warp.** RBF (φ = r, α 10⁻³–10⁻¹) followed by bilaplacian (weight 10³) [rec MM-8, MM-9]. Per-vertex stiffness: ligaments ×3–5, lid margins 3.0, lips 0.3, forehead 0.5 [anat R5.9 🧠]. Fold gate det J > 0.2 [rec MM-11].

**(b) Photo-consistency normal sweep** (new; the dense signal for T1 and T2). It runs on vertices seen by view pairs with a 10–45° baseline, where mm/px suits the band [anat R5.11]:
1. Sweep h along n_k over ±min(3σ_n, 3 mm) in 0.2 mm steps.
2. Project a 7×7 tangent patch into each view.
3. Score S(h) = Σ w_ab·NCC_ab(h); NCC is gain- and offset-invariant.
4. Fit a parabola at the peak to get ĥ_k. Confidence c_k comes from curvature and contrast; reject NCC < 0.7.
5. Solve min Σ c_k(h_k − ĥ_k)² + λ hᵀLᵀM⁻¹Lh by CG.

The pass is rejected if any landmark moves > 0.5 mm or any view's RMS rises > 0.5% IOD [com R5.10]. Step, patch and threshold are *(design defaults)*.

**(c) Shading** (off by default).
- SH9 per view, Huber 0.05 on log residuals.
- Exclude the top 2–5% of pixels and n·v < 0.3.
- Light elevation prior N(30°, 25°) [bl T6 🧠].
- The high-pass residual (< 5 mm; clamp ±2.5 mm [rec OPT-1]) goes **only** into `detail_inferred`.

### 3.10 Texture projection

- **Visibility and G-buffer:** z-buffer visibility with ε = max(1 mm, 2σ_geom); a UV G-buffer [rec TEX-1].
- **View weight:** w = vis·cos²θ·footprint·edge, with a 60–75° fade [rec TEX-2 🧠].
- **Gains** in the log domain [rec TEX-3].
- **Blend:** two-band, split at σ 3 mm. Fill order: mirror (low band) → harmonic → model [rec TEX-4, TEX-5].
- **Map size:** 4096 (2048 for phones) [rec TEX-7].
- **Gate:** reprojection median ≤ 1.5 px and max ≤ 3 px [bl T2].
- **Rights:** the `TEXTURE` scope and known photo rights [eth §3].
- **QA use:** cross-view variance after gain compensation is a **geometry error locator**.

### 3.11 Uncertainty, QA metrics and next-best view

**Posterior.** Laplace: Σ_θ = (JᵀWJ)⁻¹, with cameras marginalised by Schur complement:

  σ_n,k = √(n_kᵀ J_k Σ_θ J_kᵀ n_k),  k_k = 1 − σ²_n,post/σ²_n,prior  [anat/face-perception-likeness 🧠]

- **Labels:** measured (k ≥ 0.8), partial (0.5–0.8), prior-driven (< 0.5).
- **Requests:** k < 0.8 in a top-5 perceptual region asks for another view [anat §6].

**Calibration.** Laplace ignores model error. Leave-one-view-out (LOVO) gives γ² = mean(r²_held/σ²_pred), and the engine reports γ·σ.

**Gates.**
- A prior share of Fisher information > 20% in a region seen by ≥ 2 views [anat R1.4].
- ‖β‖² > χ²_K at 99.9% (86.7 for K = 50), or ‖c̃‖² < k − 2√(2k) for shrinkage [rec MM-5, com R5.8].
- Focal *measured* when σ_post(log f) < 0.10 [bl C2]; *prior used* when > 0.8·σ_prior [rec CAM-7].
- Perspective strength P = 100 mm/z.

**Next-best view.** For each candidate pose (yaw −90…90° in 15° steps, pitch −20/0/20°), using the user's lens and distance, simulate J_c and rank by

  G = Σ_r w_r·[log σ²_r − log σ²_r((Σ_θ⁻¹ + J_cᵀWJ_c)⁻¹)]

where w_r comes from `benchmarks-metrics.json:acceptance_targets`. It is a rank update and costs milliseconds.

## 4. Blender add-on design

### 4.1 Package and manifest

`tools/build_extension.py` vendors `face3d/` into `addon/face3d_blender/engine/`. There are no compiled wheels [bl/blender-extensions-packaging].

```toml
schema_version = "1.0.0"
id = "face3d_likeness"
version = "0.1.0"
name = "Face3D Likeness"
tagline = "Fit a measured likeness head to consented photos"
maintainer = "Face3D contributors <maintainers@example.invalid>"
type = "add-on"
blender_version_min = "4.5.0"  # oldest LTS CI tests; code stays 3.11-compatible
license = ["SPDX:GPL-3.0-or-later"]
copyright = ["2026 Face3D contributors"]
[permissions]
files = "Read photos, landmarks and templates; write fit results"
[build]
paths_exclude_pattern = ["__pycache__/", "/tests/"]
```

- **No `network` permission:** the core is offline [eth A3, A7].
- **Template:** a CC0 template is bundled only after its licence is verified (≤ 25 MB [bl Q5]). Until then, `face3d.template_import` builds it from the user's MPFB2 install.
- **User data** lives in `extension_path_user`.
- **Probing:** `compat.py` probes features at register time [bl A9].

### 4.2 Operators

All are `REGISTER|UNDO` except the job operators.

All operators carry the `face3d.` prefix.
- `project_new`, `consent_edit`: project and ConsentRecord, with default-deny gates.
- `photos_add`: EXIF, orientation, groups, gates; one locked camera with a background image per photo.
- `landmarks_detect`, `landmarks_import`: run the helper (§4.6), or import JSON.
- `pin_edit`: modal tool in camera view; σ 1–2 screen px at the placement zoom [com R3.3].
- `mask_edit`: paint and label masks.
- `solve`, `solve_cancel`: background job for stage S0–S4.
- `apply_result`: one undo step [bl K1–K4].
- `next_view`: ghost camera at the suggested pose.
- `texture_project`: job, then bake.
- `handoff_multires` [bl K5].
- `qa_report` [com R8.1–8.2].
- `prepare_for_sharing` [eth F9].

### 4.3 Panels and overlays

**Sidebar tab "Face3D":**
- **Project & Consent.**
- **Photos:** per-photo landmark, mirror, expression, group, gate and LOVO status.
- **Solve.**
- **Accuracy:** per region, RMS, γσ, k and label; focal and scale status; flags.
- **Likeness Review.**
- **Hand-off.**

**Camera-view overlays** (`gpu` POST_PIXEL): detected vs model landmarks, z-score-coloured residual arrows, mask contour vs silhouette.

**Heat maps** come from colour attributes `f3d_sigma_n_mm`, `f3d_evidence` and `f3d_region`.

**Review** offers matched-camera switching (resolution follows the camera via markers [bl C5]), a blink comparator and an edge overlay [com R6.4, R8.1].

### 4.4 Jobs, threading and undo

1. The bridge copies arrays to a job folder [bl A3].
2. `sys.executable -I -m face3d_blender.engine.cli` streams JSON-lines progress.
3. A `bpy.app.timers` poll (0.1 s, ≤ 10 ms of work per tick) shows "Ready – Apply" [bl A5].
4. Applying is a separate undoable operator. It re-fetches objects by name and refuses on a topology-hash mismatch or in Edit or Sculpt mode [bl K1, K4].

`blender -b` uses a synchronous path.

### 4.5 Shape keys and Multires hand-off

**Keys** [bl K2, rec SK-1]:
- `Basis` = template;
- `f3d_S1…S4` stage keys;
- `f3d_ID_fit` (slider max 1.5);
- `f3d_asym`, `f3d_detail_measured`, `f3d_detail_inferred`;
- `f3d_caricature`, a preview of S(α) = M + α(S − M) [com R6.2];
- `artist`, which refits never overwrite [bl K3].

Writes to Basis propagate Δ to dependent keys [bl K3]. `fit_<photo>` expression keys need the `RIG_ANIMATE` scope [eth F4]. Sculpt masks become data weights (1 − m) plus pins at σ 0.1–0.3 mm [bl W5].

**Multires.** Because the cage is fitted through limit stencils, Multires levels 2 and 3 [rec SK-3] avoid the 0.1–0.4 mm lip and tip shrink [bl W4]. Detail reaches Multires only through `multires_reshape` [bl K5].

### 4.6 Landmark helper

`tools/detect_landmarks.py` runs in the user's own Python with a user-installed `mediapipe`, via the Tasks `FaceLandmarker`:
- IMAGE mode;
- `num_faces=2`, to detect bystanders [eth F1];
- blendshapes and transform enabled;
- the `.task` path supplied by the user and SHA-256-pinned.

It runs 6–10 test-time-augmentation passes (jitter plus a flip via `mirror_index`) to estimate σ [rec BA-2], and writes `*.lmk.json`.

An optional "detector pack" extension may bundle wheels only if the platform allows it (↔️). The core never needs it.

## 5. Validation and QA

### 5.1 Synthetic test bed (runs here, no Blender)

`face3d/synth/` provides:
- **Heads:** procedural, explicitly non-anatomical ellipsoids with analytic features, plus smooth random fields and asymmetry. When a template is installed locally, the template plus an adapter draw is used instead.
- **Rigs:** 0.25–5 m, f35 13–200 mm, yaw ±90° [rec EV-5, com R8.4].
- **Detector simulator:** anisotropic noise, per-point bias, correlated dense noise, 5% outliers, yaw occlusion.
- **Images:** rasterised masks and Lambert + SH textured images.

### 5.2 Tests and acceptance

| Class | Assertion |
|---|---|
| Exactness | Noiseless: reprojection < 1e-6 px; vertices < 1e-6·scale [bl Q1]. The Blender camera round trip (< 0.01 px [bl C4]) is skipped where `bpy` is absent. |
| Calibration | Over 200 seeded trials: χ²/dof in [0.8, 1.2]; after γ, 60–76% of errors within 1σ and 90–98% within 2σ, per region. |
| Observability | Frontal-only sets label nose projection prior-driven. Focal is flagged at z ≥ 2 m without EXIF. Focal error < 5% and rotation error < 2° when yaw spans ≥ 60° [com R8.4 🧠]. |
| Accuracy (T1) | Per-region RMS ≤ eyes and lips 1.0, brows 1.2, nose 1.2, nose projection 1.5, forehead and cheeks 1.5, jaw 2.0, ears and cranium 3.0 mm [`benchmarks-metrics.json:acceptance_targets` 🧠]. prn and pg ≤ 1.5 mm. Scale ≤ 1.5% with a reference. |
| Robustness | Mirror detected in ≥ 95% of trials. A smile shifts neutral-region identity < 0.3 mm *(design default)*. Outlier view flagged. |
| Regression | Golden region table (rtol 1e-5 [bl Q2]). Fail CI when likeness-weighted error worsens > 2%. |
| Policy | AST check: no `bpy` under `face3d/`. Socket guard [eth A7]. Manifest checked with `tomllib`. SPDX entry for every bundled file. |

**Metrics** [rec EV-1, EV-2]:
- exact point-to-triangle distance;
- NoW-style 7-landmark rigid alignment, plus similarity-ICP;
- median, RMS, p95, F@0.5/1/2 mm and signed bias per region;
- E_like = Σ w_r RMS_r / Σ w_r.

### 5.3 Honest-uncertainty reporting

Every result states:
- tier;
- scale mode and σ;
- focal status;
- per region: RMS-to-data, γσ, k and label;
- LOVO error on ≥ 2 held-out photos [com R8.2];
- flags, worst first.

It never claims better than the reference modality (0.2–1 mm) [bl Q4].

### 5.4 Likeness checks shown to the artist

- **Matched-camera comparison** per photo: a clay render, a 3 Hz blink, an edge overlay and a 64 px thumbnail (the 8–16 cycles-per-face band [anat/face-perception-likeness 📄]).
- **Held-out views,** shown before their error is.
- **Region bars** against export tolerances. Lids, vermilion and alar rim 0.2–0.3 mm; nose tip and chin 0.5 mm [com R8.6 🧠]. Exceeding them blocks "approved".
- **Shrinkage audit** with a protect list of the 3–5 largest |z| deviations.
- **Familiar-viewer checklist.**

## 6. Milestones

Each milestone ships tagged, with CI passing here.

| M | Deliverable | Acceptance |
|---|---|---|
| **M1** Measure first | `eval/`, `synth/`, `mesh/raster.py`, `mesh/distance.py`; baseline report of the current engine | Analytic distances exact to 1e-9; rasteriser silhouette = `silhouette_vertices` on convex meshes; baseline table committed; suite < 90 s |
| **M2** Observations and cameras | `obs/*`, schemes, inverse-depth cameras, PnP restarts, robust rejection, mirror test, observability | Calibration and observability rows pass; nose-projection error ≥ 20% below M1 on T1 sweeps |
| **M3** Metric scale | `solve/scale.py`, iris limbus fit, references | ≤ 1.5% with a caliper; iris-only σ 4–6% with true error inside 2σ in ≥ 95% of trials |
| **M4** Shape and expression | `model/*`, `priors/*`, `solve/joint.py`, expression marginalisation and EM, jaw | Eyes, lips and nose accuracy rows; smile robustness; χ² and shrinkage gates fire on crafted cases |
| **M5** Silhouettes | Sub-vertex contours, two-way chamfer, hair hinge, PNG masks | prn and pg ≤ 1.5 mm; jaw ≤ 2.0 mm; "focal or distance wrong" fires on a mis-set focal |
| **M6** Extension MVP | `addon/` (manifest, bridge, import, job, apply, cameras, keys), template kit, helper, `cli.py` | Policy row passes; bridge maths unit-tested in numpy; `cli` runs a synthetic project in a subprocess; Blender round trip queued for Blender CI |
| **M7** Dense and review | Photo-consistency sweep, limit stencils, next-best view, QA panel, overlays | ≥ 20% lower feature error at ≤ 0.25 mm/px with 2 views 20–40° apart; no region worsens > 0.1 mm; next-best view picks the profile for frontal-only sets |
| **M8** Texture and options | `texture/project.py`, shading layer, `flame_open` adapter | TEX-8: gains within 2%, no occluded leakage [rec TEX-8]; FLAME refused on a `basis_sha256` mismatch, attribution recorded |

## 7. Risks and deliberate omissions

### Risks

- **No permissive statistical covariance.** Unobserved depth in T0 and T1 stays near the template. *Mitigation:* honest labels, the next-best view, and the FLAME Open adapter (its contents are unverified 📄).
- **All 🧠 σ values and gates are uncalibrated,** and synthetic noise misses real detector bias. *Mitigation:* γ calibration and the validation-test-bed captures.
- **The MediaPipe weights licence is ↔️** and its index map is 🧠. *Mitigation:* an external helper, pins as fallback, and index verification in the template kit.
- **Phone pipelines** (HDR, beauty and face warping, portrait blur) corrupt geometry and photo-consistency. *Mitigation:* gates, the capture protocol, and NCC rejection.
- **numpy performance.** The shared system stays ≤ 2,000 parameters; the sweep is O(V·pairs·steps), so it is scheduled per region.
- **Extension rules** on wheels, downloads and non-CC0 tables are ↔️.
- **No millimetre likeness threshold** is known [com §11]. The perceptual weights are 🧠.

### Deliberately left out

- **Learned regressors** (MICA, DECA, 3DDFA): research licences and weak-perspective depth leaks [rec MM-6, LIC-1]. Allowed only as an opt-in import that never sets depth or scale.
- **Generative heads, and monocular depth or normal networks, in identity:** zero weight [rec OPT-2].
- **Not attempted:** Gaussian avatars, hair strands, teeth, ear detail beyond silhouettes, albedo inverse rendering, identity-embedding losses [rec OPT-3–7], and differentiable GPU rendering.
- **Fitting minors** without guardian consent and age-matched priors [eth F5].
- **Any network path in the core.**
