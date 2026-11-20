# Engine requirements: photo-to-3D face reconstruction

*For the team designing the numpy-only fitting engine and the Blender add-on. Compiled 2026-11-20 from `research/reconstruction/` (22 notes plus [README](../reconstruction/README.md)). `[note]` means `research/reconstruction/<note>.md`; `Cn` means contradiction n in the README. Verification-log corrections are applied.*

**Badges:** ✅ verified · 📄 single-sourced · ↔️ contested · 🧠 expert knowledge. **Every 🧠 value is PROVISIONAL:** expose it as configuration, tune it on synthetic renders and held-out real views, never hard-code it. σ is 1σ; log-σ is natural-log.

## 0. Invariants

- **INV-1** numpy-only core. Blender bundles numpy; SciPy unconfirmed 🧠 [deformation-fitting-math]. Torch/ONNX backends run out of process [open-source-pipelines].
- **INV-2** Compute in float64 mm. FLAME is stored in metres 🧠 (×1000). The Blender scene stays 1 BU = 1 m; convert only at I/O (C1) [flame-model].
- **INV-3** Every observation and asset carries `{source, version, licence, commercial_ok, measured|generated, consent_id}` [sota-2025-2026, generative-3d-heads, commercial-head-tools].
- **INV-4** Vertex order is sacred; refuse unknown `topology_id` [open-source-pipelines].

## 1. Data formats and landmark schemes

- **FMT-1 `LandmarkSet`** = `{scheme, detector_version, model_hash, uv_px[N,2], cov_px[N,2,2], visible[N], z_rel[N]?, image_wh, iod_px, orientation, mirrored}`. Branch on `scheme`, never on N 🧠 [landmark-detection].
- **FMT-2 Schemes:**
  - iBUG-68 (2D convention: contour slides with yaw); WFLW-98.
  - MediaPipe-478: 478 points + 52 blendshape scores ✅; irises at 468–472 / 473–477 🧠.
  - FLAME embeddings: 51 static + 17-point contour over 79 yaw bins; MICA ≈105 MediaPipe points 🧠 [flame-model].
  - NoW 7; ArcFace 5-point template 📄 [identity-embeddings]; FaceWarehouse 74; BU-3DFE 83 [face-scan-datasets].

  Index map: [landmark-detection] Table 4 🧠. Assign iris left/right geometrically, not by index range.
- **FMT-3 Backend adapter** = `{backend, version, licence_code, licence_assets, topology_id, units, axes, camera_model ∈ {weak_persp, affine, perspective}, K, R, t, convention, landmarks{scheme, xy, σ}, β, ψ, jaw, mesh_path, measured|generated}` [open-source-pipelines].
- **FMT-4 Model adapter** = `{mean (N×3, mm), U_id, σ_id, U_exp?, σ_exp?, joints, LBS, posedirs, landmark_embeddings{scheme: (face_idx, bary)}, region_masks, uv, units, axis_matrix, licence, commercial_ok, population_tag}`. Normalise to β ~ N(0, I) at load (releases store σ or σ²) 🧠 [3dmm-overview].
- **FMT-5 FLAME:**
  - `shapedirs` 5023×3×400 and `posedirs` 5023×3×36 📄; joints regressed on shape+expression 📄;
  - 9,976 triangles, `weights` 5023×5, parents [−1, 0, 1, 1, 1] 🧠;
  - 5,023 vertices and 300/100 components ✅ [multi-view-fitting].

  Convert the chumpy `.pkl` (latin1) to `.npz` once, outside Blender; never ship it [flame-model].
- **FMT-6 Dataset adapter** = `{units, up_axis, forward_axis, handedness, topology_id, landmark_convention, licence_id, commercial_ok, redistribution_ok, population_tags, capture_tech}` [face-scan-datasets].
- **FMT-7 Camera import** [photogrammetry-heads]:
  - COLMAP: QW QX QY QZ + T, world→camera, centre −Rᵀt 📄.
  - Metashape: P1/P2 swapped vs OpenCV; cx, cy from the image centre 📄.
  - RealityScan XMP, AliceVision `.sfm` 🧠.
  - Accept OPENCV only if |fx − fy|/f < 0.1 % with negligible tangential terms; otherwise require undistorted images.
  - Validate by reprojecting the tool's sparse points (< 1 px).
- **FMT-8 Outputs:**
  - OBJ/PLY, `.npz` parameters and a JSON sidecar: cameras + convention, landmarks, units, licence, scale mode (`calibrated|object|measured|prior`), per-photo ψ_v/θ_v, eye and teeth parameters [multi-view-fitting, expression-neutralization, hair-eyes-teeth-recon].
  - Linear float32 albedo EXR with confidence, best-view, source-flag and variance maps [texture-extraction]; an SH JSON stating its convention [albedo-lighting-inverse-rendering].
  - Coefficients carry `{model, version, basis_sha256, K_β, K_ψ}`; refuse mismatches and never zero-pad [flame-model].

## 2. Multi-view perspective camera solving

- **CAM-1** Full pinhole per view (R, t, f). Principal point at the centre, skew 0, aspect 1, unless crop metadata exists. k1 = k2 = 0 for phone JPEG/HEIC; k1 free (σ ≈ 0.1) for ultrawide/webcam 🧠. PnP needs undistorted points 📄 [camera-pose-solving].
- **CAM-2** f_px = f35·√(W² + H²)/43.27, diagonal convention (↔️, ≈4 % from width) 🧠. Keep crop offsets so the original principal point survives [camera-perspective-distortion].
- **CAM-3 Initialisation.** Per-view PnP (EPnP/SQPnP → LM) over f35 hypotheses {13, 24, 26, 35, 50, 77, 85, 120, 135, 200} mm. Restart from pitch-flipped and yaw-mirrored poses, and keep the best that passes cheirality 🧠 [camera-pose-solving]. MediaPipe's transform rotation may seed PnP when |yaw| < 60° [landmark-detection].
- **CAM-4** u = c + s·(x + t)/(1 + ρ·ẑ), s = f/z₀, ρ = 1/z₀ ∈ [0.1, 5] m⁻¹; start at ρ = 0 🧠 [camera-perspective-distortion].
- **CAM-5 Intrinsics groups** keyed on (Make, Model, LensModel, f35, W, H, still/video) share log f, σ 0.02 🧠. Never average distances [camera-perspective-distortion]. Per-view focal diverged in simulation [camera-pose-solving].
- **CAM-6 Priors** (log-σ, all 🧠; C4):

| Source of f | Prior |
|---|---|
| Checkerboard calibration | 0.01–0.02 |
| SfM import | 0.005–0.01, poses frozen (if refined: rotation 0.05°, centre 0.5 mm) |
| EXIF, uncropped | 0.04 (≈0.10 at close focus) |
| fSpy vanishing points | 0.05–0.10 |
| Crop unknown | 0.35 |
| No EXIF | 50 mm-equivalent, 0.5–0.7 |
| VGGT/MASt3R seed | rotation 3–5°, focal 0.15–0.2, never scale [sota-2025-2026] |

  Distance when f is unknown: selfie 0.35 m (σ 0.3), handheld rear camera 0.8 m (0.4), tele 2 m (0.4). Tagged-view yaw σ 15–20°. **Wire `f_prior_log_sigma` through `PhotoLandmarks`/`reconstruct_landmarks`**; it currently falls back to 0.35 [camera-pose-solving].
- **CAM-7 Observability.** Schur-complement posterior σ for log f, t_z and pitch. σ_logf > 0.8 × prior → "focal not observable – prior used". σ_ρ > 0.5ρ → hold depth-related shape modes at the prior. Lock focal when d/Δ ≳ 12. Report P = 100 mm/z 🧠 [camera-pose-solving, camera-perspective-distortion, multi-view-fitting].
- **CAM-8 Mirror test.** Solve the flipped image too and compare cost on asymmetric features; det R < 0 without the Procrustes determinant fix [camera-pose-solving, deformation-fitting-math].
- **CAM-9 Blender export.** lens = f_px·36/W; `sensor_fit` HORIZONTAL; resolution = photo; shift_x = (W/2 − c_x)/max(W, H), shift_y = (c_y − H/2)/max(W, H); OpenCV→Blender diag(1, −1, −1); camera at the solved distance; ORTHO only when P < 0.03; round-trip reprojection test 🧠 [camera-pose-solving, open-source-pipelines].

## 3. Landmark bundle adjustment with anatomical priors

- **BA-1 Unknowns.** Shared X or β; per view R, t, ψ_v, θ_jaw,v and eyes; f per intrinsics group. X_v = X + D·ψ_v + J(θ_v), where D is a low-rank expression basis (K ≈ 10–20) and J a jaw hinge ≈10–13 mm anterior to tragion 🧠. `bundle.py` solves one static X today and must change [expression-neutralization].
- **BA-2 σ per class** in outer-IOD % (README Q5), converted per view. Contours: Σ = R·diag(σ_n², σ_t²)·Rᵀ. Dense MediaPipe: ×√(N/N_eff), N_eff 60–100. σ_eff = max(σ_class, spread over 6–10 test-time augmentations), times expression multipliers 🧠 [landmark-detection, expression-neutralization]. Retire `sigma_px = 1.0` (≈13× too tight; C5).
- **BA-3 Visibility.** Weight 0 below n·(−v) = cos 80°, full at cos 60°; drop far-side oval when |yaw| > 25°; never use occluded MediaPipe points 🧠 [landmark-detection].
- **BA-4 Contours.** Re-select silhouette vertices every iteration, or use point-to-line residuals; beyond 60° yaw, use the silhouette term 🧠 [deformation-fitting-math, multi-view-fitting].
- **BA-5 Robust loss.** Huber δ = 2σ, relative (replaces `huber_px = 3.0`); after convergence drop > 4σ and re-solve; flag a view with > 15 % rejected 🧠 [landmark-detection]. Constants: Huber 1.345σ 📄, Tukey 4.685σ 📄, Cauchy 2.385σ 🧠, σ = 1.4826·MAD 🧠 [deformation-fitting-math] (C6).
- **BA-6 LM.** (JᵀWJ + μ·diag(JᵀWJ))δ = −JᵀWr with Nielsen damping 📄. τ 10⁻³ (10⁻⁶ warm), ‖g‖∞ < 10⁻⁸, 50–100 iterations; QR when cond(J) ≳ 10⁸; R ← exp([δ]×)R; finite-difference step ≈6·10⁻⁶ 🧠 [deformation-fitting-math].
- **BA-7 Gauge.** Fix the 7-DoF similarity with a template prior or a measured length; fix global rotation and neck when the extrinsics carry pose 🧠 [deformation-fitting-math, flame-model].
- **BA-8 Anatomical priors.** Photo fits: symmetry 1.5–2 mm (up to 3), midline 1–1.5 mm. Scans: symmetry ≥ 3–5 mm. Replace the 4–8 mm independent landmark prior (engine 8 mm) with 3DMM covariance 🧠 [multi-view-fitting, deformation-fitting-math, photogrammetry-heads].
- **BA-9 Neutral anchor.** Mean ψ over neutral-tagged views ≈ 0, σ 0.1 SD.
  - With no neutral view, warn "identity uncertain along expression-confounded directions" and suppress sub-mm mouth and lid reports.
  - Tag in ≤ 3 EM rounds: blendshapes < 0.1–0.15, then ‖ψ_v‖ < 0.5 SD neutral / 0.5–1.5 mild / > 1.5 expressive.
  - Never orthogonalise expression against identity ↔️.

  🧠 [expression-neutralization]
- **BA-10 Scale.** `ScaleRef` (two points, mm, σ) combined by inverse variance; warn at > 1 % disagreement 🧠 [photogrammetry-heads]. Iris 11.7 mm, SD 0.24–0.49 ✅; IPD 63 ± 3.8 mm 🧠. With neither, tag "proportions only" [multi-view-fitting].
- **BA-11 Uncertainty.** Output per-landmark (JᵀWJ)⁻¹, leave-one-view-out reprojection and β spread over view subsets [deformation-fitting-math, multi-view-fitting].
- **BA-12 Fixed cameras.** `triangulate_points` → `umeyama` → direct β solve. Landmarks never move SfM cameras (detector noise 10–14 px vs ≈0.5 px for SfM) 🧠 [photogrammetry-heads].

## 4. 3DMM layer and template warping

- **MM-1 Prior.** ½‖β‖² with whitened residuals (λ = 1 is MAP). SVD filter factors d/(d² + λ); monitor k_eff = Σd²/(d² + λ). Self-test: +1 SD on component 1 → 2–8 mm RMS 🧠 [3dmm-overview, deformation-fitting-math].
- **MM-2** Neutral evaluation is linear: v = T̄ + S·β + E·ψ, ∂v/∂β = S. Run LBS only when jaw or eyes are free. Precompute landmark-restricted bases (L×3×K) 🧠 [flame-model].
- **MM-3 Schedule.** Sparse landmarks K_β 20 → 50 → (100); 300 only with dense, silhouette or photometric terms; K_ψ 10–20 per view 🧠 [flame-model, 3dmm-overview].
- **MM-4 Priors.** β N(0, 1), flag |β| > 3. ψ N(0, 0.3²) neutral, N(0, 1) expressive. Jaw σ 1.5° when the tag is confident, 3° otherwise (↔️, C7), x ∈ [−0.05, 0.5–0.6] rad per version, sign checked (C8). Eyes σ 0.3 rad on iris points. Scale N(1, 0.04–0.05²) only with a metric cue 🧠 [flame-model, expression-neutralization, 3dmm-overview].
- **MM-5 Gates.** ‖β‖² above χ²_K 99.9 % (K = 50: 86.7; 100: 149.5; 300: 381.5); per-region Mahalanobis (U_R·U_Rᵀ) for over-flattened noses 🧠 [3dmm-overview].
- **MM-6 Regressor priors.** β ~ N(median β̄, σ_k²), σ_k = max(floor, spread); floor 0.3 with ≥ 3 agreeing photos, 0.5 with 1–2 (↔️, C9), DECA 0.6; σ = 1 where not predicted. Huber 1.4 mm (MICA) / 1.8 mm (DECA). Log-scale σ 0.05 (MICA), 0.10 (non-metric), 0.01 (measured). Weak-perspective/affine backends never set depth or scale; Z₀ = 2f/(s·W_b) 🧠 [single-image-regression, identity-embeddings, open-source-pipelines].
- **MM-7 Basis transfer.** x̄′ = W·x̄, U′ = (W ⊗ I₃)·U, computed locally from user files and never shipped (licence derivative) 🧠/↔️ [3dmm-overview].
- **MM-8 RBF warp.** φ = r in 3D 📄; solve (K − λI)w + Pa = y (sign 🧠, reproduced numerically); λ_i = α·σ_i², α 10⁻³–10⁻¹ in normalised units. **Bug:** `face3d/geometry/rbf.py` adds +λI for φ = r and the multiquadric. Fix it, and test that bending energy falls as λ rises [deformation-fitting-math].
- **MM-9 Bilaplacian refinement.** Solve for d = x − x₀ (cotan Laplacian, lumped mass), constraint weight 10²–10⁴ (engine 10³), CG warm-started from the RBF result; optional ARAP/ASAP 🧠 [deformation-fitting-math].
- **MM-10 Offsets.** Laplacian-regularised, σ 2–3 mm, capped 3–5 mm unless ≥ 2 views agree 🧠 [multi-view-fitting, neural-head-avatars, commercial-head-tools].
- **MM-11 Gates.** det J_warp > 0.2 per vertex; no lip, lid or eyeball interpenetration (risky at |β| > 2.5–3) 🧠 [deformation-fitting-math, flame-model].
- **MM-12 NICP to scans.** Point-to-plane; stiffness 50 → … → 0.2, landmark weight 5 → 2 → 0.5 → 0. Reject > 3σ_region (coarse cap 10 mm, fine 3–5), normals > 45° and boundaries; Huber 1.5σ. Residual σ: rig 0.3–0.5, single camera 0.5–1, periphery 2–3 mm 🧠 [photogrammetry-heads, deformation-fitting-math].
- **MM-13 Region weights.** Face 1; ears 0.3–0.5; scalp 0.1; neck 0.1–0.2; eyeballs, boundary, mouth interior 0. Under hair, a one-sided constraint with an inward prior of 5–15 mm (1–3 under a cap) 🧠 [flame-model, photogrammetry-heads].

## 5. Silhouette and profile fitting

- **SIL-1** Per-view silhouettes from face-parsing masks, residuals along the normal; cheap, and the main depth signal in profile 🧠 [multi-view-fitting].
- **SIL-2** Route ±90° profiles to silhouette tracing, since landmark detectors fail there [landmark-detection]. Mask hair, beard, glasses and neck [multi-view-fitting].
- **SIL-3 Acceptance.** Nose-tip and chin profile ≤ 1–1.5 mm. Interior fits but contour and ears do not → report "f and z wrong", not a shape error 🧠 [sota-2025-2026, camera-perspective-distortion].

## 6. Shape keys and Blender hand-off

- **SK-1** Stage keys on unchanged topology: PCA → RBF → refine → silhouette 🧠 [deformation-fitting-math]. `Basis` = identity (ψ = 0 with a neutral anchor, else the most-neutral-frame ψ; store both, C11). Diagnostic `fit_<IMG>` keys hold ψ_v, θ_v [expression-neutralization]. Separate `detail_normals` and `hallucinated` keys [sota-2025-2026]. FLAME sliders ±3 (API limit ±10) [flame-model].
- **SK-2** Recompute joints J = 𝒥·v_shaped after identity changes; Preserve Volume off 🧠 [flame-model].
- **SK-3** Embed the quad template in FLAME once (barycentric); Multires level 2 for likeness, level 3 for detail 🧠 [flame-model].
- **SK-4** Export ARKit-52 names via deformation transfer and a cm bridge neutral; never ship vendor topology [commercial-head-tools].

## 7. Texture projection (🧠 unless marked; [texture-extraction])

- **TEX-1** `uv_gbuffer` (texel centre (i + 0.5)/N); `zbuffer` 1,000–2,000 px; ε = max(1 mm, 2σ_geom).
- **TEX-2 Weight** = vis·cos^p θ·footprint·semantic·edge, p = 2 ↔️; fade from 60°, cut 75°; erosion 5 px, ramp 10 px; frame margin 2 %; pyramid level ≤ 3.
- **TEX-3 Gains** in linear RGB: log I = log g_v + log a_k, mean log g = 0. σ: exposure 0.05 manual / 0.3 auto; white balance 0.03 / 0.15; vignetting 0.5 stop.
- **TEX-4 Blend:** `two_band` (default, split σ 3 mm), `multiband` (5 levels at 4K), `select_poisson`, `average`. Specular median needs ≥ 3 views.
- **TEX-5 Fill:** mirror (low band only, source ≥ 0.3·w_max) → harmonic (≤ 5 mm) → patch → model. Generative only at confidence < 0.2, off by default ↔️.
- **TEX-6 De-light.** SH order 2 (≈1 % average error 📄); AO^γ, γ 0.5 ↔️. Î = g ⊙ a ⊙ E(R·n)/π ⊙ V; residual log(I + 0.01) − log(Î + 0.01), Huber 0.05. Fix g₀ from a colour chart, else flag "absolute albedo unknown"; broad tone prior with no pull to a mean [albedo-lighting-inverse-rendering].
- **TEX-7** Map 4096 (2048 phone, 8192 at ≥ 24 MP); gutter 16 px at 4K (Blender default 📄). Photometric pose refinement (0.1°, 1 mm) on landmark cameras only, never SfM cameras.
- **TEX-8 Tests.** Synthetic renders with random gains and ±1 mm shape noise: gains within 2 %, no nose colour on occluded cheek texels. ITA sweep over six groups: |ΔITA| ≤ 5° [albedo-lighting-inverse-rendering].

## 8. Optional terms (off by default)

- **OPT-1 Normals and depth.** κ from assumed error: scene 20° (κ ≈ 13), human-specific 15° (κ ≈ 23) (C12). Stride 8 px, grazing cut 70°, rotation bias ≤ 10°. Detail solve on ≤ 1 mm edges, clamp ±2.5 mm, high-pass 6 mm. Depth only as a disparity fit 1/z ≈ s·d̂ + t, never as base shape; DA3 metric Z = f·y/300 📄. 🧠 [monocular-depth-normals]
- **OPT-2 Generator surfaces.** Zero weight on β and face vertices. Seed ensemble σ_v² = σ_region² + s_v², drop s_v > 5 mm; anisotropic along the view axis; Geman–McClure c = 2σ; capped at 25 % of the landmark information. A > 3σ depth contradiction disables the region; f35 < 35 mm doubles σ_d. Silhouettes ≤ 0.1 (likeness) / ≤ 0.25 (blockout) (C10). 🧠 [generative-3d-heads, sota-2025-2026]
- **OPT-3 Gaussian avatars.** Keep α ≥ 0.5, s_min/s_max ≤ 0.3, s_max ≤ 5 mm, |n·n_mesh| ≥ cos 45°. σ_i = √(σ₀² + s_min²), σ₀ 0.5 mm multi-view / 1–1.5 mm monocular; Geman–McClure 2–3 mm; gate out the top 10–20 % specular 🧠 [neural-head-avatars].
- **OPT-4 Eyes.** Shared centres: symmetry σ 1 mm, IPD 63 σ 3.8 mm, HVID 11.8 σ 0.6 mm (free only with ≥ 3 sharp views). Gaze σ 3° into lens (+5° kappa), 1° fixed mark, 15° untagged. Limbus σ 0.5–1 px. Strabismus flag at > 3° in ≥ 2 views 🧠 [hair-eyes-teeth-recon].
- **OPT-5 Teeth.** Intercanine 35 σ 2, intermolar 53 σ 3, tooth width σ 0.5 (lateral incisor 0.7), incisal edge 2.5 below stomion σ 1.5, overjet 2.5 σ 1, overbite 2.5 σ 1.5, midline 0 σ 1.5 (mm). Lips ≥ 0.5 mm outside enamel. Scans are never scaled beyond unit conversion 🧠 [hair-eyes-teeth-recon].
- **OPT-6 Hair gates.** Roots ≤ 1 mm from scalp, zero penetrations, mask IoU ≥ 0.85, orientation ≤ 20°; otherwise Tier 0 🧠 [hair-eyes-teeth-recon].
- **OPT-7 Identity.** `IdentityScorer` (ONNX, no gradients) for evaluation only; `IdentityLoss` off; stop on a held-out recogniser [identity-embeddings].

## 9. Licence constraints

- **LIC-1 Never bundle:**
  - FLAME 2017/2020/2023 (NC 📄), BFM (NC 📄), FLAME texture (BY-NC-SA 📄);
  - InsightFace weights (NC 📄), dlib-68 (NC ✅);
  - Depth Anything V2 Base/Large/Giant (BY-NC 📄), Pixel3DMM (BY-NC 📄), VHAP/GaussianAvatars (BY-NC-SA 📄), DiffLocks (NC 📄), nvdiffrast (1-Way Commercial 📄);
  - dataset-derived bases ↔️.

  [flame-model, identity-embeddings, landmark-detection, open-source-pipelines]
- **LIC-2 Shippable:** own code; MediaPipe code (Apache-2.0; weights ↔️, verify per release); FLAME 2023 Open (CC BY 4.0 with attribution; contents unverified 📄); Depth Anything V2 Small (Apache-2.0 📄); TRELLIS.2 (MIT 📄); MPFB2 code (GPL-3.0 ✅).
- **LIC-3** Fits and transferred bases inherit licences ↔️. Each shape key carries the union of upstream flags; block commercial export without an explicit research flag [open-source-pipelines, face-scan-datasets].
- **LIC-4** Models only from user-supplied paths, SHA-256-pinned, never silently fetched [identity-embeddings]. Record territory flags (Hunyuan3D excludes the EU, UK and South Korea 📄). Cloud steps need matching consent [commercial-head-tools].

## 10. Failure modes the engine must detect

| Failure | Detection | Note |
|---|---|---|
| Unit or axis error | Snap scale to {10⁻⁶, 10⁻³, 10⁻², 1, 10³} from ex–ex/en–en; abort outside 0.6–1.4× | face-scan-datasets |
| Mirrored selfie | Flipped-image cost; det R < 0 | camera-pose-solving |
| Focal or distance unobservable | σ_logf > 0.8 × prior; σ_ρ > 0.5ρ; flat log-f sweep | camera-pose-solving, camera-perspective-distortion |
| Twin PnP solution | Multi-start + cheirality | camera-pose-solving |
| Bad view | > 3 % IOD; held-out > 2× in-sample; > 15 % rejected | camera-pose-solving, benchmarks-metrics |
| Non-neutral photo / no anchor | Blendshape and ‖ψ_v‖ tags; empty neutral set | expression-neutralization |
| Prior-dominated fit | Low k_eff; ‖β‖ ≪ √K; within ≈1 mm RMS of the mean face | deformation-fitting-math, benchmarks-metrics |
| Implausible identity | ‖β‖² > χ² 99.9 %; \|β_i\| > 3 | 3dmm-overview |
| Unconstrained depth | Covariance; < 3 views or triangulation angle < 10–15° | photogrammetry-heads |
| Perspective mismatch | Interior fits, contour and ears fail | camera-perspective-distortion |
| Folds / interpenetration | det J ≤ 0.2; lip, lid or eyeball penetration | deformation-fitting-math |
| Weak-perspective depth leak | Refuse depth or scale from `weak_persp`/`affine` | open-source-pipelines |
| Generated data in identity | Weight assertion on `generated` tags | sota-2025-2026 |
| Texture ghosting | High cross-view variance; doubled features | texture-extraction |
| Blink or motion (scans) | Eye aspect ratio < 0.2; region residual > 3σ | photogrammetry-heads |
| Version mismatch | `basis_sha256` | flame-model |
| Lens risk | f35 < 20 mm; face > 25° off-axis; front camera | camera-perspective-distortion |
| Scale conflict | References > 1 % apart; \|s − 1\| > 3 % | photogrammetry-heads, benchmarks-metrics |
| Strabismus | Gaze residual > 3° in ≥ 2 views | hair-eyes-teeth-recon |

## 11. Evaluation harness [benchmarks-metrics]

- **EV-1 `face3d/eval`:** exact point-to-triangle distance with a grid broad phase, signed by angle-weighted pseudonormals. Alignment modes `landmarks`, `rigid_icp`, `similarity_icp` (NoW-compatible: 7 landmarks, rigid, scan-to-surface, scale solved 📄) and `region`. ICP: 10 % trim, 5–10 mm cap, 60° normal gate, ≤ 30 iterations, 10⁻⁴ mm tolerance 🧠.
- **EV-2 Report:** median, mean, std, RMS, p90, p95, F@0.5/1/2 mm, per-region signed bias, s − 1, configuration RMS over 20–30 landmarks, normal error after ≥ 9 mm smoothing, and the Chamfer formula used.
- **EV-3 Targets** 🧠: RMS ≤ 1.0 mm eyes and lips, ≤ 1.2 nose, ≤ 1.5 forehead and cheeks, ≤ 2.0 jaw, ≤ 3.0 ears; NoW-style median ≤ 0.8, mean ≤ 1.0 mm; scale ≤ 1.5 %.
- **EV-4 Anchors:** scaled mean FLAME 1.21/1.53 mm 📄; MICA 0.90/1.11 ✅; best entry 0.76/0.95 📄; 5-view simulation ≈1.2 mm 🧠; live scan floor ≈0.2–0.5 mm ↔️.
- **EV-5 CI:** synthetic sweeps over z 0.25–5 m and f35 13–200 mm, asserting surface, scale and configuration error; a leakage guard against prior-training subjects [camera-perspective-distortion, face-scan-datasets].

## 12. Open questions

- The measured gain from 1 to N views on real scans; focal recovery on real faces [multi-view-fitting, camera-pose-solving].
- Whether EXIF f35 is diagonal- or width-based, per vendor, under zoom and crops [camera-perspective-distortion].
- FLAME 2023 Open's contents; FLAME's units and triangle count; 2023 UV and jaw changes [flame-model].
- MediaPipe weights' licence and CPython wheels; SciPy in Blender [landmark-detection, deformation-fitting-math].
- A source for the 3D RBF sign rule; detector error distributions (Huber vs Cauchy); prior strength vs likeness [deformation-fitting-math].
- Pixel3DMM dense terms vs 5–9-view landmark fits; VGGT/MASt3R/DA3 cameras on portraits [sota-2025-2026].
- Face-region accuracy of any normal estimator [monocular-depth-normals].
- A permissive large-population head model or scan set [3dmm-overview, face-scan-datasets].
- A benchmark for 3–9 consumer photos with perspective and metric scale, and a map from regional mm error to perceived likeness [benchmarks-metrics].
