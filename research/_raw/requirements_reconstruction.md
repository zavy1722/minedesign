# Engine requirements: photo-to-3D face reconstruction

*For the team designing the numpy-only fitting engine and the Blender add-on. Compiled 2026-11-20 from `research/reconstruction/` (22 notes plus [README](../reconstruction/README.md)). A citation `[note]` means `research/reconstruction/<note>.md`; `Cn` means contradiction n in the README. Verification-log corrections are applied.*

**Badges:** ✅ verified · 📄 single-sourced · ↔️ contested · 🧠 expert knowledge. **Every 🧠 value is PROVISIONAL.** Expose it as configuration, tune it on synthetic renders and held-out real views, and never hard-code it. σ is 1σ, and log-σ is in natural-log units.

## 0. Invariants

- **INV-1** The core is numpy-only. Blender bundles numpy; whether it ships SciPy is unconfirmed 🧠 [deformation-fitting-math]. Torch and ONNX backends run out of process [open-source-pipelines].
- **INV-2** Compute internally in float64 millimetres. FLAME is stored in metres 🧠, so multiply by 1000. The Blender scene keeps 1 BU = 1 m. Convert only at I/O (C1) [flame-model].
- **INV-3** Every observation and asset carries `{source, version, licence, commercial_ok, measured|generated, consent_id}` [sota-2025-2026, generative-3d-heads, commercial-head-tools].
- **INV-4** Vertex order is sacred. Refuse any unknown `topology_id` [open-source-pipelines].

## 1. Data formats and landmark schemes

- **FMT-1 `LandmarkSet`** = `{scheme, detector_version, model_hash, uv_px[N,2], cov_px[N,2,2], visible[N], z_rel[N]?, image_wh, iod_px, orientation, mirrored}`. Branch on `scheme`, never on N 🧠 [landmark-detection].
- **FMT-2 Landmark schemes:**
  - iBUG-68: 2D convention, so contour points slide with yaw.
  - WFLW-98.
  - MediaPipe-478: 478 points + 52 blendshape scores ✅. Of these, 468 are mesh points and the irises are 468–472 / 473–477 🧠.
  - FLAME embeddings: 51 static points plus a 17-point contour over 79 yaw bins; MICA adds ≈105 MediaPipe points 🧠 [flame-model].
  - NoW: 7 points.
  - ArcFace: 5-point `arcface_dst` template 📄 [identity-embeddings].
  - FaceWarehouse: 74; BU-3DFE: 83 [face-scan-datasets].

  Anatomical index map in [landmark-detection] Table 4 🧠. Assign iris left/right geometrically, not by documented index range.
- **FMT-3 Backend adapter** = `{backend, version, licence_code, licence_assets, topology_id, units, axes, camera_model ∈ {weak_persp, affine, perspective}, K, R, t, convention, landmarks{scheme, xy, σ}, β, ψ, jaw, mesh_path, measured|generated}` [open-source-pipelines].
- **FMT-4 Model adapter** = `{mean (N×3, mm), U_id, σ_id, U_exp?, σ_exp?, joints, LBS weights, posedirs, landmark_embeddings{scheme: (face_idx, bary)}, region_masks, uv, units, axis_matrix, licence, commercial_ok, population_tag}`. Normalise at load so that β ~ N(0, I); releases differ in storing σ or σ² 🧠 [3dmm-overview].
- **FMT-5 FLAME arrays:**
  - `shapedirs` 5023×3×400 and `posedirs` 5023×3×36 📄;
  - joints regressed from shape and expression concatenated 📄;
  - `v_template` 5023×3, `f` 9976×3, `weights` 5023×5, parents [−1, 0, 1, 1, 1] 🧠;
  - 5,023 vertices and 300/100 components ✅ [multi-view-fitting].

  The chumpy `.pkl` (latin1) is converted once to `.npz` outside Blender and never shipped [flame-model].
- **FMT-6 Dataset adapter** = `{units, up_axis, forward_axis, handedness, topology_id, landmark_convention, licence_id, commercial_ok, redistribution_ok, population_tags, capture_tech}` [face-scan-datasets].
- **FMT-7 Camera import:**
  - COLMAP `images.txt`: QW QX QY QZ + T, world→camera, centre = −Rᵀt 📄.
  - Metashape XML: P1/P2 swapped against OpenCV; cx, cy offset from the image centre 📄.
  - RealityScan XMP and AliceVision `.sfm` 🧠.
  - Accept OPENCV only when |fx − fy|/f < 0.1 % and tangential terms are negligible; otherwise require undistorted images.
  - Validate by reprojecting the tool's sparse points (< 1 px) [photogrammetry-heads].
- **FMT-8 Outputs:**
  - Mesh: OBJ/PLY, `.npz` parameters, and a JSON sidecar holding cameras with their convention, landmarks, units, licence, scale mode (`calibrated|object|measured|prior`), per-photo ψ_v and θ_v, eye centres and gaze, arch parameters and hair tier [multi-view-fitting, expression-neutralization, hair-eyes-teeth-recon].
  - Texture: linear float32 albedo EXR, confidence, best-view index, per-texel source flag and cross-view variance [texture-extraction]; an SH JSON that states its convention [albedo-lighting-inverse-rendering].
  - Coefficients carry `{model, version, basis_sha256, K_β, K_ψ}`. Refuse version mismatches and never zero-pad [flame-model].

## 2. Multi-view perspective camera solving

- **CAM-1** Each view is a full pinhole camera with R, t and f. The principal point sits at the centre, skew is 0 and aspect is 1, unless crop metadata exists. k1 = k2 = 0 for phone JPEG/HEIC; k1 is free (σ ≈ 0.1) for ultrawide or webcam lenses 🧠. PnP needs undistorted points 📄 [camera-pose-solving].
- **CAM-2** f_px = f35·√(W² + H²)/43.27, using the diagonal convention (↔️ ≈4 % from the width convention) 🧠. Store crop offsets so the original principal point survives [camera-perspective-distortion].
- **CAM-3 Initialisation.** Per-view PnP (EPnP or SQPnP, then LM) over f35 hypotheses {13, 24, 26, 35, 50, 77, 85, 120, 135, 200} mm. Restart from pitch-flipped and yaw-mirrored poses, and keep the best solution that passes the cheirality check 🧠 [camera-pose-solving]. MediaPipe's transform rotation may seed PnP when |yaw| < 60° [landmark-detection].
- **CAM-4 Parameterisation.** u = c + s·(x + t)/(1 + ρ·ẑ), with s = f/z₀ and ρ = 1/z₀ ∈ [0.1, 5] m⁻¹. Start at ρ = 0 (weak perspective) 🧠 [camera-perspective-distortion].
- **CAM-5 Intrinsics groups** keyed on (Make, Model, LensModel, f35, W, H, still/video) share log f with σ 0.02 🧠. Never average distances across photos [camera-perspective-distortion]. BA currently has one focal length per view, and per-view focal diverged in simulation [camera-pose-solving].
- **CAM-6 Priors** (log-σ, all 🧠; C4):

| Source of f | Prior |
|---|---|
| Checkerboard calibration | 0.01–0.02 |
| SfM import | 0.005–0.01 with poses frozen (if refined: rotation 0.05°, centre 0.5 mm) |
| EXIF, uncropped | 0.04 (≈0.10 at close focus) |
| fSpy vanishing points | 0.05–0.10 |
| Crop unknown | 0.35 |
| No EXIF | 50 mm-equivalent, 0.5–0.7 |
| VGGT/MASt3R seed | rotation 3–5°, focal 0.15–0.2, never scale [sota-2025-2026] |

  Distance when f is unknown: selfie 0.35 m (σ 0.3), handheld rear camera 0.8 m (σ 0.4), tele 2 m (σ 0.4). Tagged-view yaw σ 15–20°. **Wire `f_prior_log_sigma` through `PhotoLandmarks`/`reconstruct_landmarks`**; today it falls back to 0.35 [camera-pose-solving].
- **CAM-7 Observability.** Compute Schur-complement posterior σ for log f, t_z and pitch.
  - If σ_logf > 0.8 × prior σ, report "focal not observable – prior used".
  - If σ_ρ > 0.5ρ, hold depth-related shape modes at their prior.
  - Lock focal when d/Δ ≳ 12.
  - Report P = 100 mm/z.

  🧠 [camera-pose-solving, camera-perspective-distortion, multi-view-fitting]
- **CAM-8 Mirror test.** Solve the flipped image as well and compare the cost on asymmetric features. Procrustes without the determinant fix shows mirroring as det R < 0 [camera-pose-solving, deformation-fitting-math].
- **CAM-9 Blender export.**
  - lens = f_px·36/W, `sensor_fit = HORIZONTAL`, resolution = photo size;
  - shift_x = (W/2 − c_x)/max(W, H), shift_y = (c_y − H/2)/max(W, H);
  - OpenCV → Blender camera frame: multiply by diag(1, −1, −1);
  - place the camera at the solved distance (mm → m);
  - export an ORTHO camera only when P < 0.03;
  - run a round-trip reprojection test.

  🧠 [camera-pose-solving, open-source-pipelines, camera-perspective-distortion]

## 3. Landmark bundle adjustment with anatomical priors

- **BA-1 Unknowns.** Shared X or β; per view R, t, ψ_v, θ_jaw,v and eyes; f per intrinsics group. Each view sees X_v = X + D·ψ_v + J(θ_v):
  - D is a low-rank expression basis (K ≈ 10–20);
  - J is a jaw hinge about the bicondylar axis, ≈10–13 mm anterior to tragion 🧠.

  `face3d/solve/bundle.py` solves one static X today, which must change [expression-neutralization].
- **BA-2 σ per landmark class** in outer-IOD % (README Q5), converted to pixels per view. Contours use Σ = R·diag(σ_n², σ_t²)·Rᵀ. Inflate dense MediaPipe σ by √(N/N_eff), N_eff 60–100. σ_eff = max(σ_class, test-time-augmentation spread over 6–10 passes). Apply expression multipliers per view tag 🧠 [landmark-detection, expression-neutralization]. Retire `sigma_px = 1.0` (≈13× too tight) (C5).
- **BA-3 Visibility.** Weight 0 when n·(−v) < cos 80°, full weight at cos 60°. Drop far-side oval points when |yaw| > 25°. Never use returned-but-occluded MediaPipe points 🧠 [landmark-detection].
- **BA-4 Contours.** Re-select the silhouette vertex every iteration, or use point-to-line residuals. Beyond 60° yaw, replace contour points with the silhouette term 🧠 [deformation-fitting-math, multi-view-fitting].
- **BA-5 Robust loss.** Huber δ = 2σ, relative; replace `huber_px = 3.0`. After convergence, drop points beyond 4σ and re-solve; flag a view with > 15 % rejected 🧠 [landmark-detection]. Constants: Huber 1.345σ 📄, Tukey 4.685σ 📄, Cauchy 2.385σ 🧠, σ = 1.4826·MAD 🧠 [deformation-fitting-math]. (C6)
- **BA-6 Levenberg–Marquardt.**
  - Step: (JᵀWJ + μ·diag(JᵀWJ))δ = −JᵀWr, with the Nielsen damping update 📄.
  - τ 10⁻³ (10⁻⁶ when warm-started), stop at ‖g‖∞ < 10⁻⁸, 50–100 iterations 🧠.
  - Use QR on [√W·J; √μ·D] when cond(J) ≳ 10⁸ 🧠.
  - Rotation update R ← exp([δ]×)R; central-difference step ≈6·10⁻⁶ 🧠 [deformation-fitting-math].
- **BA-7 Gauge.** Fix the 7-DoF similarity with the template prior or a measured length. Fix global rotation and neck to 0 when the extrinsics carry pose 🧠 [deformation-fitting-math, flame-model].
- **BA-8 Anatomical priors.**
  - Symmetry pairs 1.5–2 mm (up to 3 mm) and midline 1–1.5 mm on photo fits; symmetry ≥3–5 mm on scans 🧠.
  - The independent 3D landmark prior of 4–8 mm (engine 8 mm) is replaced by 3DMM covariance 🧠 [multi-view-fitting, deformation-fitting-math, photogrammetry-heads].
- **BA-9 Neutral anchor.** Mean ψ over neutral-tagged views ≈ 0, σ 0.1 SD.
  - If no view is tagged neutral, warn "identity uncertain along expression-confounded directions" and suppress sub-mm mouth and lid measurements.
  - Tag views in an EM loop of ≤ 3 rounds: first from blendshape scores (< 0.1–0.15), then by ‖ψ_v‖ (< 0.5 SD neutral, 0.5–1.5 mild, > 1.5 expressive).
  - Never orthogonalise the expression basis against identity ↔️.

  🧠 [expression-neutralization]
- **BA-10 Scale.**
  - `ScaleRef` (two points, length in mm, σ), combined by inverse variance; warn when references disagree by > 1 % 🧠 [photogrammetry-heads].
  - Iris 11.7 mm, SD 0.24–0.49 mm ✅; IPD 63 ± 3.8 mm 🧠 [multi-view-fitting, hair-eyes-teeth-recon].
  - With neither, tag the output "proportions only".
- **BA-11 Uncertainty.** Output per-landmark (JᵀWJ)⁻¹, leave-one-view-out reprojection error, and β spread over view subsets in mm per vertex [deformation-fitting-math, multi-view-fitting].
- **BA-12 Fixed cameras.** With known extrinsics, run `triangulate_points` → `umeyama` → a direct 3D β solve. Landmarks never move SfM cameras: detector noise is 10–14 px against ≈0.5 px for SfM 🧠 [multi-view-fitting, photogrammetry-heads].

## 4. 3DMM layer and template warping

- **MM-1 Prior.** ½‖β‖² with whitened residuals, so λ = 1 is the MAP estimate. Solve by SVD with filter factors d/(d² + λ), and monitor k_eff = Σd²/(d² + λ). Self-test: +1 SD on component 1 should move vertices 2–8 mm RMS 🧠 [3dmm-overview, deformation-fitting-math].
- **MM-2 Linear neutral evaluation.** v = T̄ + S·β + E·ψ with ∂v/∂β = S; run LBS only when jaw or eyes are free. Precompute landmark-restricted bases (L×3×K) 🧠 [flame-model].
- **MM-3 Component schedule.** Sparse landmarks: K_β 20 → 50 → (100). All 300 only with dense, silhouette or photometric terms. K_ψ 10–20 per view 🧠 [flame-model, 3dmm-overview].
- **MM-4 Priors.**
  - β N(0, 1), flag |β| > 3.
  - ψ N(0, 0.3²) on neutral views, N(0, 1) on expressive ones.
  - Jaw σ 1.5° when the neutral tag is confident, 3° when uncertain (↔️, C7); bound x ∈ [−0.05, 0.5–0.6] rad per version, checking the sign (C8).
  - Eyes σ 0.3 rad, fitted to iris points.
  - Global scale N(1, 0.04–0.05²) only with a metric cue.

  🧠 [flame-model, expression-neutralization, 3dmm-overview]
- **MM-5 Plausibility gates.** Flag ‖β‖² above the χ²_K 99.9 % quantile (K = 50: 86.7; K = 100: 149.5; K = 300: 381.5). Report per-region Mahalanobis distance (U_R·U_Rᵀ) to catch an over-flattened nose 🧠 [3dmm-overview].
- **MM-6 Regressor priors** (optional backends).
  - β ~ N(β̄, σ_k²), with β̄ the median over photos and σ_k = max(floor, spread across photos); floor 0.3 with ≥ 3 agreeing photos, 0.5 with 1–2 (↔️, C9), 0.6 for DECA; σ = 1 for components the regressor does not predict.
  - Huber scale 1.4 mm (MICA) or 1.8 mm (DECA).
  - Log-scale σ 0.05 (MICA), 0.10 (non-metric backends), 0.01 (user measurement).

  Weak-perspective or affine backends never set depth or scale; convert them with Z₀ = 2f/(s·W_b) 🧠 [single-image-regression, identity-embeddings, open-source-pipelines].
- **MM-7 Basis transfer.** x̄′ = W·x̄ and U′ = (W ⊗ I₃)·U, computed locally from user-supplied files and never shipped, because it is a licence derivative 🧠/↔️ [3dmm-overview].
- **MM-8 RBF residual warp.**
  - Kernel φ = r in 3D 📄; solve (K − λI)w + Pa = y (sign 🧠, reproduced numerically).
  - λ_i = α·σ_i², α 10⁻³–10⁻¹, in normalised units (centred, landmark RMS radius 1).
  - **Bug:** `face3d/geometry/rbf.py` adds +λI for φ = r and for the multiquadric. Fix it and add a test that bending energy falls as λ rises [deformation-fitting-math].
- **MM-9 Bilaplacian refinement.** Solve for the displacement d = x − x₀ with a cotan Laplacian and lumped mass. Constraint weight 10²–10⁴ (engine 10³). Warm-start CG from the RBF result. Optional ARAP/ASAP polish 🧠 [deformation-fitting-math].
- **MM-10 Offsets.** Laplacian-regularised, σ 2–3 mm, capped at 3–5 mm unless ≥ 2 views agree 🧠 [multi-view-fitting, neural-head-avatars, commercial-head-tools].
- **MM-11 Fold and penetration gates.** det J_warp > 0.2 per vertex; check lip and lid interpenetration and, for |β| > 2.5–3, lids cutting into the eyeballs 🧠 [deformation-fitting-math, flame-model].
- **MM-12 Non-rigid ICP to scans.**
  - Point-to-plane; stiffness 50 → … → 0.2, landmark weight 5 → 2 → 0.5 → 0.
  - Reject pairs beyond 3σ_region (coarse cap 10 mm, fine 3–5 mm), with normals > 45° apart, or on boundaries; Huber 1.5σ.
  - Residual σ: rig 0.3–0.5 mm, single camera 0.5–1 mm, periphery 2–3 mm.

  🧠 [photogrammetry-heads, deformation-fitting-math]
- **MM-13 Region weights.** Face 1, ears 0.3–0.5, scalp 0.1, neck 0.1–0.2, eyeballs, boundary and mouth interior 0. Under hair, a one-sided constraint penalises only skin outside the hair hull, with an inward prior of 5–15 mm (1–3 mm under a cap) 🧠 [flame-model, photogrammetry-heads].

## 5. Silhouette and profile fitting

- **SIL-1** Per-view silhouettes from face-parsing masks, with residuals along the normal. This is cheap and is the main depth signal in profile 🧠 [multi-view-fitting].
- **SIL-2** Route ±90° profiles to silhouette tracing, because landmark detectors fail there [landmark-detection]. Mask hair, beard, glasses and neck out of shape terms [multi-view-fitting].
- **SIL-3 Acceptance.** Profile error ≤ 1–1.5 mm at the nose tip and chin. If interior points fit but the contour and ears do not, report "f and z wrong" (the dolly-zoom symptom), not a shape error 🧠 [sota-2025-2026, camera-perspective-distortion].

## 6. Shape keys and Blender hand-off

- **SK-1** Stage keys on unchanged topology: PCA → RBF → refine → silhouette 🧠 [deformation-fitting-math].
  - `Basis` = identity: ψ = 0 when a neutral anchor exists, otherwise the most-neutral-frame ψ; store both (C11).
  - Diagnostic keys `fit_<IMG>` hold each photo's ψ_v and θ_v [expression-neutralization].
  - Separate keys `detail_normals` and `hallucinated` [sota-2025-2026].
  - FLAME component sliders ±3 (the API limit is ±10) [flame-model].
- **SK-2** Recompute joints (J = 𝒥·v_shaped) after any identity change. Armature modifier Preserve Volume off 🧠 [flame-model].
- **SK-3** Embed the quad template barycentrically in FLAME once. Deliver Multires level 2 for likeness and level 3 for detail 🧠 [flame-model].
- **SK-4** Export ARKit-52 names via deformation transfer, plus a cm "bridge-ready" neutral. Never ship vendor topology [commercial-head-tools].

## 7. Texture projection (all 🧠 unless marked; [texture-extraction])

- **TEX-1** `uv_gbuffer` (texel centre at (i + 0.5)/N) and `zbuffer` at 1,000–2,000 px. Depth tolerance ε = max(1 mm, 2σ_geom).
- **TEX-2 View weight** w = vis·cos^p θ·footprint·semantic·edge, with:
  - p = 2 ↔️;
  - fade from 60°, cut at 75°;
  - edge erosion 5 px with a 10 px ramp; frame margin 2 %;
  - pyramid level log₂(footprint), at most 3.
- **TEX-3 Gains** in linear RGB: log I = log g_v + log a_k, with mean log g = 0. Exposure σ 0.05 (manual) / 0.3 (auto); white balance σ 0.03 / 0.15; vignetting σ 0.5 stop.
- **TEX-4 Blending modes:** `two_band` (default; split σ 3 mm), `multiband` (5 levels at 4K), `select_poisson`, `average`. A specular median needs ≥ 3 views.
- **TEX-5 Fill order:** mirror (low band only; source weight ≥ 0.3·w_max) → harmonic (holes ≤ 5 mm) → patch → model. Generative fill only where confidence < 0.2, off by default ↔️.
- **TEX-6 De-lighting.** SH order 2: 9 coefficients, ≈1 % average error 📄. Divide by AO^γ with γ = 0.5 ↔️. Forward model Î = g ⊙ a ⊙ E(R·n)/π ⊙ V. Residual log(I + 0.01) − log(Î + 0.01) with Huber 0.05. Fix the gain gauge g₀ from a colour chart; without one, flag "absolute albedo unknown". Tone prior is broad, with no pull to a mean [albedo-lighting-inverse-rendering].
- **TEX-7** Map size 4096 (2048 for phones, 8192 at ≥ 24 MP). Gutter 16 px at 4K (Blender's default margin 📄). Photometric pose refinement (σ 0.1°, 1 mm) applies to landmark cameras only, never to SfM cameras.
- **TEX-8 Tests.** Synthetic renders with random gains and ±1 mm shape noise must recover gains within 2 % and put no nose colour on occluded cheek texels. An ITA sweep across six skin groups must stay within |ΔITA| ≤ 5° [albedo-lighting-inverse-rendering].

## 8. Optional terms (off by default)

- **OPT-1 Normals and depth** [monocular-depth-normals].
  - κ from assumed mean error: scene models 20° (κ ≈ 13), human-specific 15° (κ ≈ 23) (C12); stride 8 px; grazing cut 70°; rotation-bias Kabsch ≤ 10°.
  - Detail solve on ≤ 1 mm edges; clamp ±2.5 mm; high-pass 6 mm.
  - Depth enters only as a disparity fit, 1/z ≈ s·d̂ + t, never as base shape. DA3 metric depth Z = f·y/300 📄.

  🧠
- **OPT-2 Generator surfaces** [generative-3d-heads, sota-2025-2026].
  - Zero weight on β and on face vertices.
  - Seed ensemble: σ_v² = σ_region² + s_v²; drop vertices with s_v > 5 mm; anisotropic σ along the conditioning view axis; Geman–McClure c = 2σ.
  - Information capped at 25 % of the landmark term.
  - A > 3σ depth contradiction disables that region; f35 < 35 mm doubles σ_d.
  - Silhouettes weighted ≤ 0.1 (likeness mode) or ≤ 0.25 (blockout mode) (C10).

  🧠
- **OPT-3 Gaussian avatars** [neural-head-avatars]. Keep Gaussians with α ≥ 0.5, s_min/s_max ≤ 0.3, s_max ≤ 5 mm and |n·n_mesh| ≥ cos 45°. σ_i = √(σ₀² + s_min²), σ₀ 0.5 mm (multi-view) or 1–1.5 mm (monocular); Geman–McClure 2–3 mm; gate out the top 10–20 % by specular energy 🧠.
- **OPT-4 Eyes** [hair-eyes-teeth-recon].
  - Shared eye centres: symmetry σ 1 mm; IPD 63 σ 3.8 mm; HVID 11.8 σ 0.6 mm, freed only with ≥ 3 sharp views.
  - Gaze σ: 3° when looking into the lens (+5° kappa), 1° for a fixed mark, 15° untagged.
  - Limbus σ 0.5–1 px; strabismus flag at > 3° residual in ≥ 2 views.

  🧠
- **OPT-5 Teeth** [hair-eyes-teeth-recon]. Intercanine 35 σ 2 mm; intermolar 53 σ 3 mm; tooth width σ 0.5 mm (lateral incisors 0.7); incisal edge 2.5 mm below stomion σ 1.5; overjet 2.5 σ 1; overbite 2.5 σ 1.5; dental midline 0 σ 1.5 mm. Lips stay ≥ 0.5 mm outside the enamel. A scan is never scaled beyond unit conversion 🧠.
- **OPT-6 Hair plug-in gates.** Roots ≤ 1 mm from the scalp, zero penetrations, mask IoU ≥ 0.85, orientation error ≤ 20°; otherwise fall back to Tier 0 🧠 [hair-eyes-teeth-recon].
- **OPT-7 Identity.** `IdentityScorer` (ONNX, no gradients) for evaluation only; `IdentityLoss` off by default; stopping decided by a held-out recogniser [identity-embeddings].

## 9. Licence constraints

- **LIC-1 Never bundle:**
  - FLAME 2017/2020/2023 (NC 📄), BFM (NC 📄), the FLAME texture space (BY-NC-SA 📄);
  - InsightFace weights (NC 📄), dlib-68 (NC ✅);
  - Depth Anything V2 Base/Large/Giant (CC BY-NC 📄), Pixel3DMM (CC BY-NC 📄), VHAP/GaussianAvatars (CC-BY-NC-SA 📄), DiffLocks (NC 📄), nvdiffrast (1-Way Commercial 📄);
  - dataset-derived bases (↔️).

  [flame-model, identity-embeddings, landmark-detection, open-source-pipelines]
- **LIC-2 Shippable:**
  - our own code;
  - MediaPipe code (Apache-2.0; weights ↔️, verify per release);
  - FLAME 2023 Open (CC BY 4.0 with attribution; contents unverified 📄);
  - Depth Anything V2 Small (Apache-2.0 📄), TRELLIS.2 (MIT 📄), MPFB2 code (GPL-3.0 ✅).
- **LIC-3** Fitted meshes and transferred bases inherit licences ↔️. Each shape key carries the union of its upstream flags; commercial export is blocked unless the user sets an explicit research flag [open-source-pipelines, flame-model, face-scan-datasets].
- **LIC-4** Load models only from user-supplied paths, with SHA-256 pinning and no silent fetch [open-source-pipelines, identity-embeddings]. Record territory flags (Hunyuan3D excludes the EU, UK and South Korea 📄). A cloud step requires matching consent [commercial-head-tools].

## 10. Failure modes the engine must detect

| Failure | Detection rule | Note |
|---|---|---|
| Unit or axis error | Snap scale to {10⁻⁶, 10⁻³, 10⁻², 1, 10³} from ex–ex or en–en; abort outside 0.6–1.4× | face-scan-datasets |
| Mirrored selfie / left-right swap | Flipped-image cost comparison; det R < 0 | camera-pose-solving |
| Focal or distance unobservable | Posterior σ_logf > 0.8 × prior; σ_ρ > 0.5ρ; flat log-f sweep | camera-pose-solving, camera-perspective-distortion |
| Twin PnP solution | Multi-start plus cheirality check | camera-pose-solving |
| Bad view | In-sample > 3 % IOD; held-out > 2× in-sample; > 15 % of points rejected | camera-pose-solving, benchmarks-metrics, landmark-detection |
| Non-neutral photo or missing neutral anchor | Blendshape and ‖ψ_v‖ tagging; empty neutral set | expression-neutralization |
| Prior-dominated fit | k_eff low; ‖β‖ ≪ √K; within ≈1 mm RMS of the mean face → request another view | deformation-fitting-math, benchmarks-metrics |
| Implausible identity | ‖β‖² > χ² 99.9 %; any \|β_i\| > 3 | 3dmm-overview |
| Unconstrained depth | Per-landmark covariance; fewer than 3 views or a triangulation angle < 10–15° | deformation-fitting-math, photogrammetry-heads |
| Perspective mismatch | Interior fits but contour and ears fail | camera-perspective-distortion |
| Folds or interpenetration | det J ≤ 0.2; lip, lid or eyeball penetration | deformation-fitting-math, flame-model |
| Weak-perspective depth leak | Refuse depth or scale from `weak_persp`/`affine` backends | open-source-pipelines |
| Generated data in identity | Weight assertion on `generated` tags | sota-2025-2026 |
| Texture ghosting | High cross-view variance; doubled features | texture-extraction |
| Blink or motion (scans) | Eye aspect ratio < 0.2; per-region residual > 3σ | photogrammetry-heads |
| Version mismatch | `basis_sha256` check | flame-model |
| Lens risk | f35 < 20 mm; face > 25° off-axis; front camera | camera-perspective-distortion |
| Scale conflict | References disagree by > 1 %; \|s − 1\| > 3 % | photogrammetry-heads, benchmarks-metrics |
| Strabismus | Gaze residual > 3° in ≥ 2 views | hair-eyes-teeth-recon |

## 11. Evaluation harness

- **EV-1 `face3d/eval`** [benchmarks-metrics].
  - Exact point-to-triangle distance with a grid broad phase, signed with angle-weighted pseudonormals.
  - Alignment modes: `landmarks`, `rigid_icp`, `similarity_icp` (NoW-compatible: 7 landmarks, rigid, scan-to-surface, scale solved 📄) and `region`.
  - ICP: 10 % trimming, 5–10 mm correspondence cap, 60° normal gate, ≤ 30 iterations, 10⁻⁴ mm tolerance 🧠.
- **EV-2 Report** median, mean, std, RMS, p90, p95, F@0.5/1/2 mm, per-region signed bias, s − 1, configuration RMS over 20–30 landmarks, and normal error after ≥ 9 mm smoothing. Always print the Chamfer formula used.
- **EV-3 Targets** 🧠: RMS ≤ 1.0 mm for eyes and lips, ≤ 1.2 mm nose, ≤ 1.5 mm forehead and cheeks, ≤ 2.0 mm jaw, ≤ 3.0 mm ears; NoW-style median ≤ 0.8 and mean ≤ 1.0 mm; scale ≤ 1.5 %.
- **EV-4 Anchors:** scaled mean FLAME 1.21/1.53 mm 📄; MICA 0.90/1.11 mm ✅; best entry 0.76/0.95 mm 📄; 5-view simulation ≈1.2 mm 🧠; live scan floor ≈0.2–0.5 mm ↔️.
- **EV-5 CI.** Synthetic sweeps over z 0.25–5 m and f35 13–200 mm, asserting surface error, scale error and configuration RMS. A leakage guard stops evaluation on subjects that trained a prior [camera-perspective-distortion, face-scan-datasets].

## 12. Open questions

- The measured gain from 1 to N views on real scans, landmark vs photometric [multi-view-fitting]. Focal recovery accuracy on real faces rather than synthetic ones [camera-pose-solving].
- Whether EXIF f35 uses the diagonal or the width, per vendor, under digital zoom and crops [camera-perspective-distortion].
- FLAME 2023 Open's contents (bases, masks, UVs); FLAME's metre units and 9,976-triangle count; whether 2023 changed the UVs or the jaw handling [flame-model].
- The MediaPipe weights' licence; MediaPipe wheels for Blender's CPython; whether Blender 4.x/5.x bundles SciPy [landmark-detection, deformation-fitting-math].
- A source for the 3D kernel sign rule; the detector error distribution (which decides Huber vs Cauchy); prior strength vs likeness [deformation-fitting-math].
- Whether Pixel3DMM-style dense terms beat 5–9-view landmark fits; how VGGT, MASt3R and DA3 cameras perform on portrait sets [sota-2025-2026].
- Face-region error for any normal estimator [monocular-depth-normals].
- Whether a permissive large-population head model or scan set exists [3dmm-overview, face-scan-datasets].
- A benchmark for 3–9 consumer photos with perspective and metric scale, and a map from regional mm error to perceived likeness [benchmarks-metrics].
