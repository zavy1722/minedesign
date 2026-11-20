# Photo-to-3D face reconstruction science

*Area guide for artists and engineers. Edited 2026-11-20 from the 22 topic notes in this folder, their data tables in `../data/<topic>.json`, and the area digest. This guide adds no evidence of its own: every value below comes from a note, keeps that note's badge, and links back to it. Where a note's verification log corrected its own text, this guide uses the corrected value.*

## What this area covers

This area covers the science of turning photos of one consenting person into a likeness-accurate head mesh that an artist can sculpt in Blender. It spans:

- **Cameras and perspective.** Solving each photo's camera, why distance (not lens) distorts faces, and how absolute size enters.
- **Correspondence.** Landmark detectors, their noise and bias, and landmark schemes.
- **Shape models and fitting maths.** 3D morphable models (3DMMs), FLAME in depth, Procrustes, RBF and Laplacian warps, non-rigid ICP, robust least squares, and multi-view bundle adjustment with anatomical priors.
- **Identity versus expression.** How to obtain a neutral identity from photos that are never quite neutral.
- **Other signals.** Single-image regressors, monocular depth and normals, photogrammetry, generative 3D models and neural (NeRF/Gaussian) avatars, and what each can and cannot measure.
- **Appearance.** Texture projection, albedo, lighting and skin-tone bias.
- **Hard parts.** Eyes, teeth and hair.
- **Tools and evidence.** Open-source pipelines, commercial tools, datasets, benchmarks and metrics, and the 2025–2026 state of the art.

Blender mechanics, anatomy norms, community practice and law have their own areas (see [Related notes outside this area](#related-notes-outside-this-area)).

## How to use this guide

- **Artists:** read the [principles](#core-principles), then work through the [Blender checklist](#checklist-for-an-artist-working-in-blender). Use the [quick-reference tables](#quick-reference-tables) when you set up cameras, check an import or judge a fit.
- **Engineers:** read the principles, the tables and the [contradictions](#cross-topic-contradictions-and-how-to-resolve-them). Then read the compact engine requirements in [`../_raw/requirements_reconstruction.md`](../_raw/requirements_reconstruction.md), and open the topic notes for derivations and sources.
- **Evidence badges** (used throughout the library):
  - ✅ verified: confirmed by at least two independent sources, or an exact identity;
  - 📄 single-sourced: one cited source;
  - 🧠 expert knowledge, not yet source-checked: a provisional starting point, never a settled fact;
  - ↔️ contested: sources or recollections disagree.
- **Verification logs win.** Each note ends with a dated "Verification log". Where the log corrects the body text (for example the FLAME 2023 Open licence, the Pixel3DMM venue, or scanner repeatability), the log is authoritative, and this guide follows it.
- **Evidence profile.** Summed from the notes' own header counts, the area holds about 1,850 badged claims: 53 ✅ (≈3 %), 240 📄 (≈13 %), 1,190 🧠 (≈64 %) and 369 ↔️ (≈20 %). Most topics had no web harvest, so most numeric defaults are design starting points. Tune them on synthetic renders and held-out real views before you trust them.
- **Time-sensitive items** (prices, licences, versions, "best method" claims) are marked as such in the notes. Re-check them before shipping anything.

## Core principles

1. **Camera distance, not focal length, sets facial perspective.** A feature Δ behind the nose tip images (1 + Δ/z)× smaller. A longer lens only lets you stand farther back at the same framing, and it is the extra distance that flattens the face. ✅ — [camera-perspective-distortion](./camera-perspective-distortion.md), [camera-pose-solving](./camera-pose-solving.md)

2. **Beyond about 1 m, treat focal length as a prior, not an unknown.** A face is only about 10–12 cm deep, so its depth and the camera distance are confounded and only Δ/d is observable. In engine simulation, single-view focal error for an unknown face was about 10–17 % at selfie range, and focal was not recoverable at 2 m. Take f from calibration, EXIF or background vanishing points (fSpy), and report whether it was observable. 🧠 — [camera-pose-solving](./camera-pose-solving.md), [camera-perspective-distortion](./camera-perspective-distortion.md)

3. **Spread of views beats number of views.** For two views θ apart, depth σ ÷ lateral σ = 1/(√2·sin(θ/2)): 5.4× at 15°, 1.4× at 60°. In simulation, five views over ±60° yaw gave ≈1.2 mm landmark RMSE even with wrong per-view focal, and frontal-only sets gave 2.5–3.0 mm. Twenty near-frontal photos constrain depth no better than one. 🧠 — [camera-pose-solving](./camera-pose-solving.md), [multi-view-fitting](./multi-view-fitting.md)

4. **Absolute size needs a metric cue.** Landmark bundle adjustment and structure-from-motion (SfM) recover shape only up to a 7-DoF similarity transform. Put a measured interpupillary distance (IPD), a caliper head breadth, an ID-1 card or an A4 sheet in shot. Failing that, use the iris (≈11.7 mm, SD ≈0.24–0.5 mm, ✅) as a prior, which leaves ≈2–4 % scale error, and label the result "proportions only". 🧠/✅ — [multi-view-fitting](./multi-view-fitting.md), [deformation-fitting-math](./deformation-fitting-math.md), [photogrammetry-heads](./photogrammetry-heads.md)

5. **Landmark detectors pull toward the mean face, and that bias does not average away.** Automatic 68-point detectors reach ≈3–4 % of inter-ocular distance (IOD) on 300-W (✅), about 3–4 mm per point at face scale (🧠). Noise falls as 1/√k over k views; convention offsets of 1–3 mm do not (caruncle vs endocanthion, nose highlight vs pronasale; 🧠). Beyond about 4 views, invest in silhouettes and detector calibration, not a better detector. — [landmark-detection](./landmark-detection.md), [camera-pose-solving](./camera-pose-solving.md)

6. **Express landmark noise in IOD fractions per landmark class, never as a fixed pixel value.** Crisp anchors get about 1–1.5 % IOD. Contours get anisotropic covariance, mostly along the contour. Dense MediaPipe points are correlated, so inflate their σ by √(N/N_eff). The engine's `sigma_px = 1.0` is about 13× too tight for a 12 MP portrait. 🧠 — [landmark-detection](./landmark-detection.md), [multi-view-fitting](./multi-view-fitting.md)

7. **Contour points slide.** 2D-convention jaw and brow points sit on the *visible* outline and move over the skin as yaw changes. Fit them as sliding or silhouette residuals, re-associated every iteration ("landmark marching"), never as fixed vertices. 🧠 — [landmark-detection](./landmark-detection.md), [deformation-fitting-math](./deformation-fitting-math.md), [flame-model](./flame-model.md)

8. **A morphable-model fit is a prior and an initialiser, not the likeness.** On the NoW benchmark, a scale-fitted *average* FLAME scores 1.53 mm mean (📄), MICA 1.11 mm (✅) and the best entry, TokenFace, 0.95 mm (📄). Single-image methods therefore remove only a quarter to two fifths of the mean face's error. What makes the face recognisable sits in the residual the fit smooths away. — [single-image-regression](./single-image-regression.md), [benchmarks-metrics](./benchmarks-metrics.md), [3dmm-overview](./3dmm-overview.md)

9. **Vertex count is not capacity, so choose the number of components K from the constraints.** BFM 2009 has 53,490 vertices (📄) but at most 199 statistical components (🧠).
   - Sparse landmarks: K ≈ 20–50, scheduled upward (10 or 20 → 50).
   - Dense, silhouette or photometric terms: all 300 FLAME components.
   - Afterwards, Laplacian or RBF per-vertex offsets of ≲3–5 mm.

   🧠 — [3dmm-overview](./3dmm-overview.md), [flame-model](./flame-model.md)

10. **Share identity across views; keep expression per view.** Use one identity vector β for all views, with per-view expression ψ, jaw and eyes. A neutral-tagged view with a tight ψ prior anchors the identity/expression gauge; without one, a habitual expression is unidentifiable. Hand off with ψ = 0 and the jaw closed. FLAME's jaw is articulated (linear blend skinning), not part of ψ (📄). 🧠 — [expression-neutralization](./expression-neutralization.md), [multi-view-fitting](./multi-view-fitting.md)

11. **Use perspective cameras only.** Weak-perspective regressors (DECA, SMIRK and most image-to-3D generators) bake selfie magnification, ≈18–30 % at 0.3–0.5 m, into the shape. They may seed pose and β, but never depth or scale. 🧠 — [single-image-regression](./single-image-regression.md), [open-source-pipelines](./open-source-pipelines.md), [camera-perspective-distortion](./camera-perspective-distortion.md)

12. **Measured data outranks generated data.** Diffusion views, image-to-3D or GAN meshes, and Gaussian-avatar regions not covered by photos are sampled from a prior, not measured.
    - They get zero weight on identity β and on face vertices.
    - For ears and the back of the head (occiput) they enter only as heavily down-weighted silhouettes.
    - They are always tagged `generated`.

    🧠 — [sota-2025-2026](./sota-2025-2026.md), [generative-3d-heads](./generative-3d-heads.md), [neural-head-avatars](./neural-head-avatars.md)

13. **Monocular depth never sets proportions; predicted normals may add detail.** Depth Anything V2's relative output is affine-invariant disparity (📄), and DA3's metric depth scales linearly with the focal length you pass (📄). The bas-relief ambiguity (🧠) means shading cannot fix nose projection. Learned normals can add a clamped mid-frequency layer, solved in mesh space (default clamp ±2.5 mm, 🧠). — [monocular-depth-normals](./monocular-depth-normals.md)

14. **Fit landmarks and silhouettes first, photometric terms last.** VHAP's authors call photometric alignment "sometimes sensitive" (📄). With uncontrolled light, hair or makeup, a geometric fit from well-spread views may give an equal or better β (↔️). Keep photometric terms opt-in, behind landmark and contour gates. — [multi-view-fitting](./multi-view-fitting.md), [open-source-pipelines](./open-source-pipelines.md)

15. **Validate where depth lives: in profiles and held-out views.** Residuals on the input images only measure fit. Accept a fit only if the leave-one-view-out landmark error stays ≲2 % IOD and the profile silhouette is within ≈1–1.5 mm at the nose tip and chin. 🧠 — [benchmarks-metrics](./benchmarks-metrics.md), [sota-2025-2026](./sota-2025-2026.md), [multi-view-fitting](./multi-view-fitting.md)

16. **Compare errors only under the same alignment, distance and crop.** NoW uses 7 landmarks, rigid alignment and scan-to-surface distance, with scale solved (📄). Always measure point-to-triangle: nearest-vertex distance adds ≈0.35 × edge length, ≈1–2 mm on raw FLAME (🧠). Report median, mean, p95, scale error and per-region error. — [benchmarks-metrics](./benchmarks-metrics.md)

17. **Units, axes and vertex order fail silently.** FLAME files are in metres (🧠), MICA's demo writes millimetres (📄), 3DDFA_V2 writes image pixels and Deep3DFaceRecon roughly decimetres (🧠). On every import, assert the vertex count and one anthropometric distance. Never Merge by Distance, Join or Sort a mesh whose vertex correspondence you need. — [open-source-pipelines](./open-source-pipelines.md), [flame-model](./flame-model.md), [face-scan-datasets](./face-scan-datasets.md)

18. **Do not sculpt on raw FLAME.** Its level-0 edges are 3–6 mm, so the lid margin, alar groove and vermilion border are each 1–2 edges wide.
    - Transfer the fit to a quad template through a fixed barycentric map.
    - Keep the fit as a shape key.
    - Add Multires: level 2 (≈0.75–1.5 mm) for likeness, level 3 for detail.

    FLAME has no mouth interior, teeth, eyelid thickness or usable eyes. 🧠 — [3dmm-overview](./3dmm-overview.md), [flame-model](./flame-model.md), [sota-2025-2026](./sota-2025-2026.md)

19. **Licences decide the architecture.** These are non-commercial:
    - FLAME 2017, 2020 and 2023, and BFM (📄);
    - InsightFace weights (📄) and the dlib-68 model (✅);
    - nvdiffrast, GaussianAvatars/VHAP and Pixel3DMM (📄).

    Only "FLAME 2023 Open" is CC BY 4.0 (📄), and its contents are unverified. Ship permissive parts only: MediaPipe, your own numpy fitter and a permissive template. Treat research backends as user-installed plug-ins. — [open-source-pipelines](./open-source-pipelines.md), [flame-model](./flame-model.md), [identity-embeddings](./identity-embeddings.md), [landmark-detection](./landmark-detection.md)

20. **Run ML backends out of process, behind an adapter contract.** Every backend returns:
    - topology ID, units and axes;
    - camera model, K, R, t and the axis convention;
    - landmarks with σ;
    - licence and a `measured|generated` flag.

    The engine refuses unknown topologies. Torch never runs inside Blender. 🧠 — [open-source-pipelines](./open-source-pipelines.md), [single-image-regression](./single-image-regression.md)

21. **Fix geometry before texture.** Ghosting and view-transition seams come from misregistration: a sample shifts by Δs ≈ δn·tan θ for a normal-direction error δn. A 1 mm error at 45° is ≈15 px at 0.067 mm/px. Doubled brows or lip lines in a projection are therefore a geometry diagnostic. Work in linear RGB, with per-image gain compensation and two-band blending. 🧠 — [texture-extraction](./texture-extraction.md)

22. **Projected texture is not albedo, and statistical priors bias skin tone.** Order-2 spherical-harmonic (SH9) shading leaves albedo scale and hue ambiguous. TRUST showed that learned albedo tracks the light-skinned training mean (📄). Set tone with a colour chart and per-texel de-lighting, not a PCA prior. — [albedo-lighting-inverse-rendering](./albedo-lighting-inverse-rendering.md), [texture-extraction](./texture-extraction.md)

23. **Eyes, teeth and hair are separate, model-based sub-problems.**
    - Eyes: rigid, fixed-size eyeballs with per-view gaze fitted to the limbus arcs.
    - Teeth: the person's intraoral scan, or an arch template.
    - Hair: an envelope plus hairline and parting, driving a procedural groom.

    Under hair the skull is a one-sided constraint. 🧠 — [hair-eyes-teeth-recon](./hair-eyes-teeth-recon.md), [photogrammetry-heads](./photogrammetry-heads.md)

24. **On a live sitter, photogrammetry is limited by motion, not by the solver.** Triangulation precision is ≈0.05–0.25 mm, but 1 mm of non-rigid motion is 7–20 px at 0.05–0.15 mm/px. Keep each ring of photos to ≤20–30 s, mask the background before alignment, and never let detector landmarks move SfM cameras. 🧠 — [photogrammetry-heads](./photogrammetry-heads.md)

25. **Identity embeddings are a scorecard, never the shape signal.** ArcFace similarity ignores scale and is dominated by texture. Score clay renders against a calibrated genuine/impostor baseline, and keep any identity loss off by default. MICA uses ArcFace as a frozen encoder with a 3D geometry loss, not as an identity loss (📄). 🧠 — [identity-embeddings](./identity-embeddings.md), [sota-2025-2026](./sota-2025-2026.md)

26. **Commercial tools are template fitters with unpublished accuracy.** The one peer-reviewed test, Headshot v1 against optical scans, found 1.77 mm whole-face RMSE (📄). Import vendor heads as down-weighted observations, not as ground truth. — [commercial-head-tools](./commercial-head-tools.md)

27. **Population and consent are engineering constraints.**
    - Large models skew toward European adults (CAESAR, BFM; LSFM ≈80 % White) (🧠). For under-represented sitters, add views rather than tighten priors (↔️).
    - Face geometry, embeddings, iris textures and dental scans are biometric or health data (↔️). Process them locally, record the consent scope, and put provenance on every asset.

    — [face-scan-datasets](./face-scan-datasets.md), [3dmm-overview](./3dmm-overview.md), [identity-embeddings](./identity-embeddings.md), [commercial-head-tools](./commercial-head-tools.md)

## Quick-reference tables

All values come from the linked notes and keep their badges. Wherever a "recommended" value is chosen from a spread across notes, the choice is explained in [contradictions](#cross-topic-contradictions-and-how-to-resolve-them).

### Q1. Distance and perspective

Pinhole arithmetic from [camera-perspective-distortion](./camera-perspective-distortion.md) Table 1. Distances are measured to the nose tip; Δ = 100 mm to the ear plane. Other notes use other conventions (see contradiction C2).

| Camera to nose tip | Situation | Nose tip larger than ear plane by | Nose-to-face-width inflation vs ∞ | Status |
|---|---|---|---|---|
| 0.25 m | close selfie | 40 % | 18.5 % | 🧠 |
| 0.30 m | Ward et al.'s "12 in" | 33 % | 15.6 % | 🧠 |
| 0.40 m | selfie | 25 % | 11.9 % | 🧠 |
| 0.50 m | arm's length | 20 % | 9.6 % | 🧠 |
| 1.0 m | conversation distance | 10 % | 4.9 % | 🧠 |
| 1.5 m | Ward et al.'s "5 ft"; clinical | 6.7 % | 3.3 % | 🧠 |
| 2.0 m | tele portrait | 5.0 % | 2.5 % | 🧠 |
| 3.0 m | long tele; safe for ortho tracing | 3.3 % | 1.7 % | 🧠 |

Ward et al. report ≈30 % wider nasal base at 0.3 m than at 1.5 m, against 12–16 % from pure geometry (↔️; see C3).

| Purpose | Distance | Lens (full-frame equivalent) | Status | Note |
|---|---|---|---|---|
| Likeness/identity photo set | 1.5–3 m | 85–135 mm, or phone 3–5× tele | 🧠 | [camera-perspective-distortion](./camera-perspective-distortion.md) |
| Clinical standard | ≥1 m, often ≈1.5 m | 90–105 mm macro | ↔️ | same |
| Focal-identification shot (known intrinsics only) | 0.4–0.6 m | phone main | 🧠 | same; [camera-pose-solving](./camera-pose-solving.md) |
| Ortho blueprint tracing | ≥3 m, solved yaw and pitch ≈0 | tele | 🧠 | [camera-perspective-distortion](./camera-perspective-distortion.md) |
| Not for proportions | front camera at 0.25–0.5 m; any ultrawide | — | 🧠 | same |
| Identity set for a fit (photo count) | 7–9 photos: frontal, ±30–45°, ±90°, pitch ±15–20° | one lens, one zoom | 🧠 | [multi-view-fitting](./multi-view-fitting.md) |
| Single-camera photogrammetry | 0.8–1.5 m, 3–4 rings, 10–20° steps, 60–120 photos, ≤20–30 s per ring | 50–105 mm, f/8–f/11, ≥1/200 s | 🧠 | [photogrammetry-heads](./photogrammetry-heads.md) |

### Q2. Camera model and conversions

| Item | Formula / value | Status | Note |
|---|---|---|---|
| f in pixels from EXIF 35 mm-equivalent focal | f_px = f35·√(W² + H²)/43.27 (diagonal convention) | 🧠; diagonal vs width ↔️ (≈4 % apart on 4:3) | [camera-perspective-distortion](./camera-perspective-distortion.md) |
| Blender lens | lens = f_px·36/W, Sensor Fit **Horizontal**, render resolution = photo size | 🧠 | [camera-pose-solving](./camera-pose-solving.md) |
| Typing EXIF f35 into the lens field | wrong except for 3:2; correction factor 4:3 = 1.040, 16:9 = 0.955, 1:1 = 1.177 | 🧠 | same |
| Principal-point shift | shift_x = (W/2 − c_x)/max(W, H); shift_y = (c_y − H/2)/max(W, H) | 🧠 | [open-source-pipelines](./open-source-pipelines.md) |
| OpenCV → Blender camera frame | multiply by diag(1, −1, −1) (c2w·diag(1, −1, −1, 1)) | 🧠 | same; [neural-head-avatars](./neural-head-avatars.md) |
| PyTorch3D → Blender camera frame | multiply by diag(−1, 1, −1) | 🧠 | [open-source-pipelines](./open-source-pipelines.md) |
| Weak-perspective (s, t) → perspective | Z₀ = 2f/(s·W_crop) | 🧠 | [single-image-regression](./single-image-regression.md) |
| COLMAP `images.txt` | QW QX QY QZ + T, world→camera; centre = −Rᵀt | 📄 | [photogrammetry-heads](./photogrammetry-heads.md) |
| Metashape XML | P1/P2 swapped vs OpenCV p1/p2; cx, cy offset from image centre (version-dependent) | 📄 | same |
| Lens distortion | PnP expects undistorted points (📄); phone main camera k1 = k2 = 0; k1 free (σ ≈ 0.1) for ultrawide or webcam | 🧠 | [camera-pose-solving](./camera-pose-solving.md) |
| Full-perspective reparameterisation | u = c + s·(x + t)/(1 + ρ·ẑ), s = f/z₀, ρ = 1/z₀ ∈ [0.1, 5] m⁻¹; start at ρ = 0 (weak perspective) | 🧠 | [camera-perspective-distortion](./camera-perspective-distortion.md) |
| Perspective-strength index | P = 100 mm/z: > 0.1 strong; < 0.03 near-affine (ortho export allowed) | 🧠 | same |
| Distance from head size in frame | z ≈ 0.235·f35/(34.6·h) m, h = head height ÷ long side (uncropped 4:3), ±10–15 % | 🧠 | same |

### Q3. Focal and distance priors (σ in log space)

| Situation | Recommended prior | Spread across notes | Status | Notes |
|---|---|---|---|---|
| Checkerboard-calibrated | σ_log 0.01–0.02 | — | 🧠 | [camera-pose-solving](./camera-pose-solving.md) |
| Cameras imported from SfM | σ_log 0.005–0.01; poses frozen (if refined: rotation σ 0.05°, centre σ 0.5 mm) | — | 🧠 | [photogrammetry-heads](./photogrammetry-heads.md) |
| EXIF f35 from an uncropped original | σ_log 0.04 | 0.03–0.10 | 🧠 | [camera-perspective-distortion](./camera-perspective-distortion.md), [camera-pose-solving](./camera-pose-solving.md), [multi-view-fitting](./multi-view-fitting.md), [open-source-pipelines](./open-source-pipelines.md), [commercial-head-tools](./commercial-head-tools.md); see C4 |
| Vanishing points (fSpy) | σ_log 0.05–0.10 | — | 🧠 | [camera-pose-solving](./camera-pose-solving.md) |
| EXIF present, crop or zoom unknown | σ_log 0.35 | — | 🧠 | [camera-perspective-distortion](./camera-perspective-distortion.md) |
| No EXIF | 50 mm-equivalent, σ_log 0.5–0.7, multi-hypothesis over {13, 24, 26, 35, 50, 77, 85, 120, 135, 200} mm | 0.15–0.7 | 🧠 | same; [camera-pose-solving](./camera-pose-solving.md); see C4 |
| Photos from one body + lens + zoom ("intrinsics group") | share log f, σ 0.02 | — | 🧠 | [camera-perspective-distortion](./camera-perspective-distortion.md) |
| Distance when f is unknown | front-camera selfie 0.35 m (σ 0.3); handheld rear main 0.8 m (σ 0.4); tele 2 m (σ 0.4); tape-measured ±5 cm | — | 🧠 | same |
| Focal-observability gate | lock focal when d/Δ ≳ 12 (d ≳ 1.2 m); report "focal not observable – prior used" when posterior σ_logf > 0.8 × prior σ | — | 🧠 | [multi-view-fitting](./multi-view-fitting.md), [camera-pose-solving](./camera-pose-solving.md) |
| Learned camera initialisers (VGGT, MASt3R) | rotation σ 3–5°, focal σ_log 0.15–0.2, never scale; accept only if bundle adjustment converges < 2 % IOD | — | 🧠 | [sota-2025-2026](./sota-2025-2026.md) |

### Q4. Metric scale cues and sanity ranges

| Cue | Value | 1σ scale error if assumed | Status | Notes |
|---|---|---|---|---|
| Horizontal visible iris diameter | ≈11.7 mm (studies 11.64–11.81), SD 0.24–0.49 mm; some biometers read 12.3–12.4 | ≈2–4 % | ✅ | [multi-view-fitting](./multi-view-fitting.md) |
| MediaPipe Iris assumption | 11.7 ± 0.5 mm | — | 📄 | [camera-pose-solving](./camera-pose-solving.md) |
| Interpupillary distance (far gaze) | mean ≈63 mm (61–64), SD ≈3–4 mm (3.8) | ≈5–6 % | 🧠 (mean secondary-supported; SD unconfirmed) | [camera-pose-solving](./camera-pose-solving.md), [multi-view-fitting](./multi-view-fitting.md), [hair-eyes-teeth-recon](./hair-eyes-teeth-recon.md) |
| ID-1 card | 85.60 × 53.98 mm | exact | 🧠 | [multi-view-fitting](./multi-view-fitting.md) |
| A4 sheet | 210 × 297 mm | exact | 🧠 | same |
| Scale bar, 300 mm ± 0.5 mm | — | 0.17 % | 🧠 | [photogrammetry-heads](./photogrammetry-heads.md) |
| Caliper head breadth (eu–eu), ±1–2 mm | — | ≈1 % | 🧠 | same |
| Population-mean template | head breadth SD ≈4–5 % of mean | ≈4–5 % | 🧠 | [multi-view-fitting](./multi-view-fitting.md) |
| Import sanity: outer canthi ex–ex | ≈85–100 mm | — | 🧠 | [face-scan-datasets](./face-scan-datasets.md) |
| Import sanity: inner canthi en–en | ≈28–36 mm, or 31–41 mm | — | 🧠 (see C15) | [face-scan-datasets](./face-scan-datasets.md), [open-source-pipelines](./open-source-pipelines.md) |
| Import sanity: bizygomatic zy–zy | 120–150 mm | — | 🧠 | [single-image-regression](./single-image-regression.md), [3dmm-overview](./3dmm-overview.md) |
| Import sanity: head length g–op / breadth eu–eu | 175–205 mm / 135–160 mm | — | 🧠 | [generative-3d-heads](./generative-3d-heads.md) |

### Q5. Landmark noise, robust losses and acceptance gates

Observation σ as a percentage of the outer inter-ocular distance (ex–ex), from [landmark-detection](./landmark-detection.md) Table 5.

| Landmark class | σ normal | σ tangent | Status |
|---|---|---|---|
| Iris centre | 1.0 | 1.0 | 🧠 |
| Canthi, cheilia, labrale, subnasale | 1.5 | 1.5 | 🧠 |
| Lid and lip contours | 2 | 5 | 🧠 |
| Pronasale | 2.5 | 2.5 | 🧠 |
| Sellion (horizontal / vertical) | 2 | 4 | 🧠 |
| Brows | 3–5 | 6 | 🧠 |
| Jaw / face oval | 2.5 | 10–15, or a silhouette term | 🧠 |

| Item | Value | Status | Note |
|---|---|---|---|
| User pin / auto pin | 0.75 % IOD / 1.5 % corners, 2.5 % lid and lip contours, 4 % face oval | 🧠 | [commercial-head-tools](./commercial-head-tools.md) |
| Dense MediaPipe points | keep 80–120 distinct points, or inflate σ by √(N/N_eff), N_eff ≈ 60–100 (×2.2–2.8) | 🧠 | [landmark-detection](./landmark-detection.md) |
| Dense UV correspondences (Pixel3DMM-style) | σ ≈ 2–3 % IOD, stride 8 px, total weight ≤ summed landmark term | 🧠 | [sota-2025-2026](./sota-2025-2026.md) |
| Expression multipliers on σ (mobile landmarks) | ×1 neutral, ×3 mild, ×5–10 or drop when expressive | 🧠 | [expression-neutralization](./expression-neutralization.md) |
| Visibility ramp | weight 0 when n·(−v) < cos 80°, full weight at cos 60°; drop far-side oval when \|yaw\| > 25° | 🧠 | [landmark-detection](./landmark-detection.md) |
| Huber constant, 95 % efficiency | 1.345σ | 📄 | [deformation-fitting-math](./deformation-fitting-math.md) |
| Tukey constant, 95 % efficiency | 4.685σ | 📄 | same |
| Cauchy constant; MAD scale | 2.385σ; σ = 1.4826·MAD | 🧠 | same |
| Engine robust defaults | Huber δ = 2σ; after convergence drop > 4σ and re-solve; flag a view with > 15 % of points rejected | 🧠 | [landmark-detection](./landmark-detection.md); see C6 |
| Per-view acceptance (in-sample) | ≲2–3 % IOD with detector landmarks, ≲1 % with hand pins; reject a view > 3 % IOD | 🧠 | [camera-pose-solving](./camera-pose-solving.md) |
| Held-out acceptance | leave-one-view-out < 2 % IOD; flag a view whose held-out error > 2× in-sample | 🧠 | [sota-2025-2026](./sota-2025-2026.md), [benchmarks-metrics](./benchmarks-metrics.md) |
| Profile silhouette | ≲1–1.5 mm at nose tip and chin | 🧠 | [sota-2025-2026](./sota-2025-2026.md), [open-source-pipelines](./open-source-pipelines.md) |

### Q6. Model constants and import assertions

| Item | Value | Status | Note |
|---|---|---|---|
| FLAME vertices | 5,023 | ✅ | [multi-view-fitting](./multi-view-fitting.md) |
| FLAME shape / expression components | 300 / 100 | ✅ | same ([expression-neutralization](./expression-neutralization.md)'s own pass did not find them) |
| FLAME triangles | 9,976 | 🧠 (unconfirmed) | [flame-model](./flame-model.md) |
| FLAME frame and units | metres, Y up, face toward +Z, +X = subject's left | 🧠 (units unconfirmed) | same |
| FLAME joints and pose | 5 joints (root, neck, jaw, two eyes); θ ∈ ℝ¹⁵ axis-angle; parents [−1, 0, 1, 1, 1] | 📄 joints and order; 🧠 parents | same |
| FLAME `shapedirs` / `posedirs` | 5023 × 3 × 400 (300 shape + 100 expression) / 5023 × 3 × 36 | 📄 | same |
| FLAME joint regression | uses shape and expression concatenated, so expression moves the joints slightly | 📄 | same |
| FLAME eyeball vertices | ≈1,092 (≈546 each); read from `FLAME_masks.pkl` | 🧠 | same; [3dmm-overview](./3dmm-overview.md) |
| FLAME landmark embeddings | 51 static + 17-point dynamic contour over 79 yaw bins (−39° to +39°); MICA ships ≈105 MediaPipe points | 🧠 | [flame-model](./flame-model.md) |
| FLAME `.pkl` | chumpy pickle (`encoding='latin1'`); convert once to `.npz` outside Blender | 🧠 | same; [open-source-pipelines](./open-source-pipelines.md) |
| BFM 2009 | 53,490 vertices; 199 shape + 199 colour; units sub-mm/µm | 📄 count; ↔️ units | [3dmm-overview](./3dmm-overview.md) |
| Deep3DFaceRecon crop / 3DDFA_V2 crop | 35,709 / ≈38,365 vertices (count an export) | 🧠 | [open-source-pipelines](./open-source-pipelines.md) |
| MediaPipe Face Landmarker | 478 landmarks + 52 blendshape scores | ✅ | same |
| MediaPipe index layout | 468 mesh + iris 468–472 and 473–477; blendshapes include `_neutral`, lack `tongueOut` | 🧠 | [landmark-detection](./landmark-detection.md) |
| MediaPipe z | relative, scaled like x; not metric | 📄 | same |
| ArcFace input | 112×112 crop, 5-point `arcface_dst` template; buffalo_l recogniser outputs 512-d | 📄 | [identity-embeddings](./identity-embeddings.md) |
| ARKit / FaceBuilder blendshapes | 52 incl. `tongueOut` / 51 | 🧠 / ↔️ | [commercial-head-tools](./commercial-head-tools.md) |
| SMPL-X | 10,475 vertices; FLAME-compatible head | 🧠 | [3dmm-overview](./3dmm-overview.md) |
| Basis normalisation self-test | +1 SD on component 1 moves vertices by 2–8 mm RMS | 🧠 | same |
| Multires on FLAME | L0 9,976 tris ≈3–6 mm; L1 29,928 ≈1.5–3 mm; L2 119,712 ≈0.75–1.5 mm; L3 478,848 ≈0.4–0.75 mm | 🧠 | [flame-model](./flame-model.md), [sota-2025-2026](./sota-2025-2026.md) |

### Q7. Accuracy anchors: what "good" means

| Reference | Median / mean (mm) | Status | Note |
|---|---|---|---|
| NoW: average FLAME, no scale fit | 1.49 / 1.92 | 📄 | [benchmarks-metrics](./benchmarks-metrics.md) |
| NoW: average FLAME, scale fitted | 1.21 / 1.53 | 📄 | same |
| NoW: DECA, test split | 1.09 / 1.38 (std 1.18) | ✅ | [single-image-regression](./single-image-regression.md) |
| NoW: DECA, validation (coarse / detailed) | 1.18 / 1.46 · 1.19 / 1.47 | ✅ | same |
| NoW: MICA, test split | 0.90 / 1.11 (std 0.92) | ✅ | same |
| NoW: MICA, profile images | 0.94 / 1.16 | 📄 | same |
| NoW: best entry (TokenFace, leaderboard updated 27.10.2025) | 0.76 / 0.95 | 📄 | [sota-2025-2026](./sota-2025-2026.md) |
| Headshot v1 vs optical scans (clinical study) | RMSE 1.77 whole face, 1.26 perioral | 📄 | [commercial-head-tools](./commercial-head-tools.md) |
| 3dMD nominal accuracy / live repeat capture | 0.2 mm RMS / ≈0.2–0.5 mm | 📄 / ↔️ (corrected in verification) | [benchmarks-metrics](./benchmarks-metrics.md) |
| Engine simulation: 5-view landmark-only fit | ≈1.2 mm landmark RMSE | 🧠 | [camera-pose-solving](./camera-pose-solving.md) |
| 68-point detector NME, 300-W full set | 2.9–3.3 % IOD (≈3.8 % inter-pupil normalised) | ✅ | same |
| HRNetV2-W18 / STAR / ADNet NME on WFLW | 4.60 / 4.02 / 4.14 % | 📄 | [landmark-detection](./landmark-detection.md) |
| DSINE normal error, NYUv2 (scenes, not faces) | 16.4° | ✅ | [monocular-depth-normals](./monocular-depth-normals.md) |
| Proposed tool targets (eyes and lips / nose / jaw / whole crop) | RMS ≤1.0 / ≤1.2 / ≤2.0; NoW-style median ≤0.8, mean ≤1.0; scale ≤1.5 % | 🧠 | [benchmarks-metrics](./benchmarks-metrics.md) |

### Q8. Shape-fitting priors (FLAME-style 3DMM)

| Term | Prior / setting | Status | Note |
|---|---|---|---|
| Identity β | N(0, 1) per component; flag \|β_i\| > 3 | 🧠 | [multi-view-fitting](./multi-view-fitting.md), [flame-model](./flame-model.md) |
| ‖β‖² plausibility gate (χ²_K 99.9 %) | K = 50: 86.7; K = 100: 149.5; K = 300: 381.5. A MAP fit far *below* the median only marks under-constrained modes | 🧠 | [3dmm-overview](./3dmm-overview.md) |
| Expression ψ, neutral-tagged view / expressive view | N(0, 0.3²) / N(0, 1), per view | 🧠 | [multi-view-fitting](./multi-view-fitting.md), [expression-neutralization](./expression-neutralization.md) |
| Neutral gauge anchor | mean ψ over neutral-tagged views ≈ 0, σ 0.1 SD | 🧠 | [expression-neutralization](./expression-neutralization.md) |
| Jaw on neutral views | σ 2–3° (most notes) vs 1–1.5° | ↔️ (see C7) | same; [flame-model](./flame-model.md) |
| Freeway space at rest (justifies the jaw prior) | 2–4 mm | 📄 | [expression-neutralization](./expression-neutralization.md) |
| Eyes / neck (stills) | eyes: nuisance ±30°, or σ 0.3 rad fitted to iris points / neck: fixed at 0 | 🧠 | [3dmm-overview](./3dmm-overview.md), [flame-model](./flame-model.md) |
| Global scale | N(1, 0.04–0.05²) only with a metric cue; otherwise σ_log 0.05–0.1 and label "proportions only" | 🧠 | same |
| Bilateral symmetry / midline | 1.5–3 mm (photo fits; ≥3–5 mm when fitting scans) / 1–2 mm; never a hard symmetric projection | 🧠 | [multi-view-fitting](./multi-view-fitting.md), [photogrammetry-heads](./photogrammetry-heads.md) |
| Independent landmark prior | 5–10 mm (engine 8 mm); replace with PCA covariance | 🧠 | [multi-view-fitting](./multi-view-fitting.md) |
| Per-vertex offsets after the 3DMM | Laplacian-regularised, σ ≈ 2–3 mm, capped ≈3–5 mm | 🧠 | same; [neural-head-avatars](./neural-head-avatars.md) |
| β prior initialised from MICA | median over photos; σ_k = max(0.3, spread) for k ≤ 100, σ = 1 above; DECA floor 0.6 | 🧠 (see C9) | [open-source-pipelines](./open-source-pipelines.md), [single-image-regression](./single-image-regression.md) |
| Residual scale after MICA / DECA initialisation | Huber 1.4 mm / 1.8 mm | 🧠 | [single-image-regression](./single-image-regression.md) |
| Region weights | face 1; ears 0.3–0.5; scalp 0.1; neck 0.1–0.2; eyeballs, boundary, mouth interior 0 | 🧠 | [flame-model](./flame-model.md) |
| Out-of-population sitter | widen σ_id ×1.3–1.5 (a guess) | ↔️ | [3dmm-overview](./3dmm-overview.md), [face-scan-datasets](./face-scan-datasets.md) |
| Levenberg–Marquardt | Nielsen damping update (📄); τ = 10⁻³ (10⁻⁶ from a good start), ‖g‖∞ < 10⁻⁸, 50–100 iterations; switch to QR if cond(J) ≳ 10⁸ (🧠) | 📄 / 🧠 | [deformation-fitting-math](./deformation-fitting-math.md) |
| 3D RBF warp | kernel φ = r (📄); solve with **K − λI**, not K + λI (🧠); λ_i = α·σ_i², α 10⁻³–10⁻¹ in normalised units | 📄 / 🧠 | same |
| Laplacian constraint weight / fold gate | 10²–10⁴ (engine 10³) / det J_warp > 0.2 per vertex | 🧠 | same |
| Non-rigid ICP schedule | stiffness 50 → 20 → 5 → 2 → 0.8 → 0.5 → 0.35 → 0.2; landmark weight 5 → 2 → 0.5 → 0 (recalled menpo3d defaults); reject pairs with normals > 45–60° apart | 🧠 | same |

### Q9. Appearance, texture and detail defaults

| Item | Default | Status | Note |
|---|---|---|---|
| Texture map size | 4096 (2048 for phones; 8192 at ≥24 MP); 4K whole head ≈0.12 mm/texel | 🧠 | [texture-extraction](./texture-extraction.md) |
| View weight | cos^p θ, p = 2 (1–4); fade from 60°, hard cut 75° | ↔️ p; 🧠 angles | same |
| Depth-test tolerance ε | max(1 mm, 2σ_geom) (scan 0.5–1 mm; template-only fit 2–5 mm) | 🧠 | same |
| Edge erosion / ramp | 5 px / 10 px in the source photo | 🧠 | same |
| Gain prior (log) | σ 0.05 with manual exposure; 0.3 with auto exposure | 🧠 | same |
| Two-band split | Gaussian σ 3 mm on the surface | 🧠 | same |
| Bake gutter | 16 px at 4K (Blender's default bake margin is 16) | 📄 | same |
| Generative inpainting | only where confidence < 0.2; off by default | ↔️ | same |
| SH9 lighting | 9 coefficients per channel, ≈1 % average error for Lambertian irradiance | 📄 | same; [albedo-lighting-inverse-rendering](./albedo-lighting-inverse-rendering.md) |
| Skin specular F0 | 0.028 (IOR ≈ 1.4) | 🧠 | same |
| Photometric residual | log(I + 0.01) − log(Î + 0.01), Huber δ 0.05, so dark and light skin weigh equally | 🧠/↔️ | [albedo-lighting-inverse-rendering](./albedo-lighting-inverse-rendering.md) |
| Tone fairness target | \|ΔITA\| ≤ 5° per skin group on synthetic sweeps | 🧠 | same |
| Normal-detail layer | scene model 20° (κ ≈ 13); human-specific 15° (κ ≈ 23); clamp ±2.5 mm; high-pass 6 mm; grazing cut 70°; stride 8 px | 🧠 (see C12) | [monocular-depth-normals](./monocular-depth-normals.md) |
| DA3 metric depth | Z = f·y/300, f = mean(fx, fy) in px; output in metres | 📄 | same |
| Gaussian-avatar point term | keep α ≥ 0.5, s_max ≤ 5 mm; σ₀ 0.5 mm multi-view, 1–1.5 mm monocular; Geman–McClure c 2–3 mm | 🧠 | [neural-head-avatars](./neural-head-avatars.md) |
| Generator surface term | in-plane σ 2–3 mm, along view axis 4–10 mm on the face; ≥15 mm (silhouette only) on the occiput; eyes, ears, mouth, hair off | 🧠 | [generative-3d-heads](./generative-3d-heads.md) |
| Eye sizes | globe ≈24 mm; corneal radius ≈7.8 mm; HVID 11.8 ± 0.6 mm; rotation centre 13–14 mm behind the apex | 🧠 | [hair-eyes-teeth-recon](./hair-eyes-teeth-recon.md) |

### Q10. Licence quick reference (re-check before shipping)

| Asset | Terms | Status | Note |
|---|---|---|---|
| FLAME 2017, 2020, 2023 | non-commercial research; commercial requests to ps-license@tue.mpg.de | 📄 | [flame-model](./flame-model.md) |
| FLAME 2023 Open | CC BY 4.0, attribution required; contents (bases, masks, UVs) unverified | 📄 | same; [3dmm-overview](./3dmm-overview.md) |
| FLAME texture space | CC BY-NC-SA 4.0 | 📄 | [neural-head-avatars](./neural-head-avatars.md), [single-image-regression](./single-image-regression.md) |
| BFM | non-commercial licence agreement | 📄 | [single-image-regression](./single-image-regression.md) |
| InsightFace pretrained weights (buffalo_l, antelopev2) | non-commercial research; commercial licence on request | 📄 | [identity-embeddings](./identity-embeddings.md) |
| dlib 68-point model | trained on 300-W, not for commercial use (Debian lists the file as CC0) | ✅ | [landmark-detection](./landmark-detection.md) |
| MediaPipe Face Landmarker | Apache-2.0 code; weights' terms to verify per release | ↔️ | same |
| nvdiffrast | NVIDIA Source Code License (1-Way Commercial) | 📄 | [open-source-pipelines](./open-source-pipelines.md) |
| GaussianAvatars, VHAP | CC-BY-NC-SA-4.0 (GaussianAvatars adds a Toyota notice) | 📄 | [neural-head-avatars](./neural-head-avatars.md) |
| video-head-tracker | CC BY-NC 3.0 | 📄 | [multi-view-fitting](./multi-view-fitting.md) |
| Pixel3DMM | CC BY-NC 4.0 (README) | 📄 | [sota-2025-2026](./sota-2025-2026.md) |
| Depth Anything V2 | Small: Apache-2.0; Base, Large, Giant: CC BY-NC 4.0 | 📄 | [monocular-depth-normals](./monocular-depth-normals.md) |
| DiffLocks | non-commercial; commercial via Meshcapade | 📄 | [hair-eyes-teeth-recon](./hair-eyes-teeth-recon.md) |
| Hunyuan3D 2.1 | territory excludes the EU, UK and South Korea | 📄 | [generative-3d-heads](./generative-3d-heads.md) |
| TRELLIS.2 | MIT (dependencies such as nvdiffrast licensed separately) | 📄 | same |
| MPFB2 code | GPL-3.0-or-later | ✅ | [open-source-pipelines](./open-source-pipelines.md) |
| MetaHuman (UE 5.6+) | standard UE EULA; usable and sellable outside Unreal | ✅ | [commercial-head-tools](./commercial-head-tools.md) |
| RealityScan 2.0 (ex-RealityCapture) | free below ≈US$1 M annual revenue | ✅ | [photogrammetry-heads](./photogrammetry-heads.md) |
| DECA, EMOCA, MICA code | non-commercial research | 🧠 | [single-image-regression](./single-image-regression.md) |
| Scan datasets (FaceScape, Headspace, NeRSemble, …) | mostly non-commercial research; derived PCA bases are assumed to inherit the terms | ↔️ | [face-scan-datasets](./face-scan-datasets.md) |

## Checklist for an artist working in Blender

**Before the shoot**
- [ ] Get written consent that names capture, storage, where processing happens (local or cloud) and the use (static sculpt or animatable avatar; record animatable consent separately). — [commercial-head-tools](./commercial-head-tools.md), [neural-head-avatars](./neural-head-avatars.md), [../ethics/consent-likeness-law.md](../ethics/consent-likeness-law.md)
- [ ] Pick the licence route. For commercial work, use no FLAME 2017–2023, BFM or InsightFace assets; use FLAME 2023 Open (with attribution, after checking its contents) or a permissive template. — Q10

**Capture the identity set**
- [ ] Use one camera, one zoom setting, and locked focus, exposure and white balance. Turn off portrait, beauty and HDR modes, and turn stabilisation off for video. — [camera-pose-solving](./camera-pose-solving.md), [neural-head-avatars](./neural-head-avatars.md)
- [ ] Shoot from 1.5–2 m (up to 3 m) with an 85–135 mm-equivalent lens or a phone 3–5× tele. Crop later rather than step closer, and keep the face within 10–15° of the frame centre. — Q1
- [ ] Take 7–9 photos: frontal, ±30–45°, both profiles, and about ±15–20° pitch. — [multi-view-fitting](./multi-view-fitting.md)
- [ ] Brief the sitter: "breathe out, let your jaw hang a hair, lips just touching, look at the dot at eye level". Never say "relax and smile". Repeat the frontal neutral at the start and end of the session. — [expression-neutralization](./expression-neutralization.md)
- [ ] Hair off the forehead and ears, glasses off, no contour makeup, soft even light. — [landmark-detection](./landmark-detection.md), [monocular-depth-normals](./monocular-depth-normals.md)
- [ ] Put a scale object (ID-1 card or A4 at cheek depth) in at least two views, or measure IPD or head breadth. — Q4
- [ ] Put a colour chart in the first frame of each lighting setup, and shoot RAW if you can. — [albedo-lighting-inverse-rendering](./albedo-lighting-inverse-rendering.md)
- [ ] Shoot the expression set separately: frontal plus one ¾ of closed smile, teeth smile, jaw open, brows up and down, pucker and squint. Optionally also shoot eye, teeth and hair sets, and ask whether a dental scan exists. — [expression-neutralization](./expression-neutralization.md), [hair-eyes-teeth-recon](./hair-eyes-teeth-recon.md)
- [ ] Keep the originals. Never crop or resize without recording it, and remember that messaging apps strip EXIF. — [camera-pose-solving](./camera-pose-solving.md)

**Triage the photos**
- [ ] Apply the EXIF orientation. Un-mirror front-camera selfies, and check one asymmetric feature (parting, mole). — [camera-pose-solving](./camera-pose-solving.md)
- [ ] Label each photo selfie (< 0.6 m), mid (0.6–1.5 m) or portrait (≥ 1.5 m). Selfies and ultrawide shots are perspective evidence, not proportion references. — [camera-perspective-distortion](./camera-perspective-distortion.md)
- [ ] Gate expressions with MediaPipe blendshape scores, compared with the subject's most neutral photo rather than with zero. — [landmark-detection](./landmark-detection.md)

**Set up cameras in Blender**
- [ ] Make one camera per photo: resolution = photo pixels, Sensor Fit Horizontal, lens = f_px·36/W, shift from the principal point.
- [ ] Place each camera at its solved distance, with the photo as its background. Never scale or offset the photo to make it fit. — Q2, [../blender/reference-camera-setup.md](../blender/reference-camera-setup.md)
- [ ] Never type EXIF f35 into the lens field. — Q2
- [ ] Bind the cameras to timeline markers (Ctrl+B) to flip between photos. — [camera-pose-solving](./camera-pose-solving.md)
- [ ] Judge proportions only through the matched cameras, or with View ▸ Focal Length at about 100–170 mm. A head filling the default 50 mm viewport is seen from roughly selfie distance. — [camera-perspective-distortion](./camera-perspective-distortion.md)

**Import a fit and check it**
- [ ] Assert the vertex count (5,023 for FLAME). Check scale: ex–ex ≈85–100 mm, or head breadth ≈0.14–0.17 Blender units at unit scale 1.0. Check that the nose points −Y and the normals face outward. — Q4, Q6
- [ ] Check reprojection: ≲2 % IOD with detector landmarks or ≲1 % with pins, in every view, and leave-one-view-out ≲2 %. — Q5
- [ ] Overlay the profile silhouette: nose tip and chin within ≈1–1.5 mm. If interior points match but the ears and contour do not, the focal length and distance are wrong together; the shape is not. — Q5, [camera-perspective-distortion](./camera-perspective-distortion.md)
- [ ] Mirror-compare left and right, because priors symmetrise. Check ear height and inclination against the profile photo. — [sota-2025-2026](./sota-2025-2026.md)

**Prepare to sculpt**
- [ ] Keep the fit as a shape key (`flame_identity` / `likeness_base`), and keep an untouched FLAME object for refits.
- [ ] Transfer to a quad template, then add Multires: level 2 for likeness, level 3 for detail. — [flame-model](./flame-model.md), [3dmm-overview](./3dmm-overview.md)
- [ ] Place eyeballs before lids (≈24 mm globe, ≈11.7–11.8 mm visible iris). Match gaze per view before sculpting lid coverage: 3° of gaze error moves the limbus ≈0.6 mm. — [hair-eyes-teeth-recon](./hair-eyes-teeth-recon.md), [../blender/eyes-modeling-blender.md](../blender/eyes-modeling-blender.md)
- [ ] Add a mouth interior and teeth.
- [ ] Treat ears, scalp and occiput as placeholders, and sculpt the scalp *inside* the hair volume. — [3dmm-overview](./3dmm-overview.md), [photogrammetry-heads](./photogrammetry-heads.md)
- [ ] Put any AI-generated geometry on a separate `hallucinated` shape key. Sculpt over it, and never let it move the face. — [sota-2025-2026](./sota-2025-2026.md)
- [ ] Sculpt identity only in `Basis`, and only in regions the photos can vouch for. On a smiling photo, trust the nose, forehead, orbital rims and ears; do not trust mouth width, lips, the nasolabial fold, the lower lid or the chin pad. — [expression-neutralization](./expression-neutralization.md)
- [ ] Judge form in MatCap and in profile, never on the textured head. — [texture-extraction](./texture-extraction.md), [generative-3d-heads](./generative-3d-heads.md)

**Texture**
- [ ] Freeze the UVs first. Put seams behind the ears, along the hairline and under the chin, with no face above ≈25 % area stretch. — [texture-extraction](./texture-extraction.md)
- [ ] Before projecting, check that the canthi, alar base, mouth corners, tragus and jawline sit within 1–2 px of the wireframe in every camera. — same
- [ ] Work in linear colour, in this order: colour-match → blend → fill → de-light → optional mild sharpen. Save albedo as EXR (Linear) and confidence as Non-Color, with a 16 px bake margin at 4K. — same
- [ ] Compare renders with photos under the Standard view transform, not AgX or Filmic. — [identity-embeddings](./identity-embeddings.md), [albedo-lighting-inverse-rendering](./albedo-lighting-inverse-rendering.md)

**Validate and record provenance**
- [ ] If you have a reference scan, scan twice to find your noise floor. Show a signed heatmap at ±2 mm with a grey ±0.3–0.5 mm deadband, and fix errors in perceptual order: configuration, then lids, brows and lips, then the nose profile, then broad planes. — [benchmarks-metrics](./benchmarks-metrics.md)
- [ ] Score likeness on clay renders against the mean-head control (C − G), not on textured renders. — [identity-embeddings](./identity-embeddings.md)
- [ ] Tag every asset with `{source, version, licence, commercial_ok, measured|generated, consent_id}`. — [generative-3d-heads](./generative-3d-heads.md), [commercial-head-tools](./commercial-head-tools.md)

## Cross-topic contradictions and how to resolve them

| # | Topic | What the notes say | Resolution |
|---|---|---|---|
| C1 | Blender scene units | [deformation-fitting-math](./deformation-fitting-math.md): "use a millimetre scene". [flame-model](./flame-model.md), [photogrammetry-heads](./photogrammetry-heads.md), [face-scan-datasets](./face-scan-datasets.md), [single-image-regression](./single-image-regression.md): 1 Blender unit = 1 m at unit scale 1.0. [commercial-head-tools](./commercial-head-tools.md): cm for MetaHuman, CC and Daz. | The engine computes in mm internally (FLAME ×1000, per [flame-model](./flame-model.md) and [neural-head-avatars](./neural-head-avatars.md)). The Blender scene stays 1 BU = 1 m. Convert only at I/O, and use cm only for bridge exports. The Blender-side checks in the notes assume metres (head breadth ≈0.14–0.17 BU; a 0.5 mm voxel remesh is 0.0005). |
| C2 | Selfie magnification at 0.3 m | 1.50 ([deformation-fitting-math](./deformation-fitting-math.md), Z to ear plane), 1.33 ([multi-view-fitting](./multi-view-fitting.md), [camera-perspective-distortion](./camera-perspective-distortion.md), d to nose, Δ = 0.10 m), 1.30 ([single-image-regression](./single-image-regression.md), Δ = 0.09 m), 51 % at 217 mm with Δ = 110 mm ([camera-pose-solving](./camera-pose-solving.md)). | One law, 1 + Δ/z, with different reference distances and assumed depths Δ (0.09–0.11 m, 🧠). Use [camera-perspective-distortion](./camera-perspective-distortion.md) Table 1 (distance to nose tip, Δ = 100 mm) as canonical, and state the convention whenever you quote a number. |
| C3 | Size of the selfie effect | Pinhole geometry: 12–16 % nose-to-face inflation (0.3 → 1.5 m). Ward et al.: ≈30 % (↔️). | Unresolved. The engine uses geometry (a perspective camera reproduces it exactly). Treat Ward's figure as including occlusion of the face's sides and a different width definition ([camera-perspective-distortion](./camera-perspective-distortion.md)). |
| C4 | Focal prior σ_log | With EXIF: 0.03 ([open-source-pipelines](./open-source-pipelines.md), [commercial-head-tools](./commercial-head-tools.md)), 0.04 ([camera-perspective-distortion](./camera-perspective-distortion.md)), 0.04–0.06 ([camera-pose-solving](./camera-pose-solving.md)), 0.05–0.10 ([multi-view-fitting](./multi-view-fitting.md), [deformation-fitting-math](./deformation-fitting-math.md)). Without: 0.15–0.2 (open-source), 0.35 (engine), 0.35–0.5 (multi-view), 0.5 (commercial), 0.5–0.7 (camera-pose, camera-perspective). The engine also never passes `f_prior_log_sigma`. | Tier σ by evidence (Q3). Use 0.04 for an uncropped EXIF original; it covers integer rounding (±0.4–3.8 %) and unit-focus gain at portrait range (+0.6–6 %, Table 3 of camera-perspective). Widen to ≈0.10 for close focus (FF 50 mm at 0.5 m gains +11 %), 0.35 when crop or zoom is unknown, and 0.5–0.7 plus hypotheses with no EXIF. The 0.15–0.2 "no EXIF" value is too tight given the Table 7 simulations (focal error up to 622 % p90 with no prior). Fix the engine wiring. |
| C5 | Landmark σ | 0.01–0.02·d_ip, interpupillary ([deformation-fitting-math](./deformation-fitting-math.md)); 0.025·IOD detector / 0.01 manual ([camera-pose-solving](./camera-pose-solving.md)); 1–1.5 % IOD ([multi-view-fitting](./multi-view-fitting.md), [open-source-pipelines](./open-source-pipelines.md)); per-class 1–2.5 % outer IOD ([landmark-detection](./landmark-detection.md)); engine `sigma_px = 1.0`. | Mostly a normaliser mismatch: outer IOD (85–95 mm) ≈ 1.4× inter-pupil distance (58–70 mm), per [landmark-detection](./landmark-detection.md) Table 3. Always declare the normaliser. Adopt the per-class table (Q5) in outer-IOD units, with dense inflation and expression multipliers. Retire the 1 px default. |
| C6 | Huber threshold | 1.345σ–3σ ([deformation-fitting-math](./deformation-fitting-math.md)); 2.5σ ([camera-pose-solving](./camera-pose-solving.md)); 2σ ([landmark-detection](./landmark-detection.md), [commercial-head-tools](./commercial-head-tools.md)); ≈2× the median residual after pass 1 ([multi-view-fitting](./multi-view-fitting.md)); engine `huber_px = 3.0` absolute. | Always relative to σ, never in pixels. Default δ = 2σ, then drop points beyond 4σ and re-solve. Use 1.345σ only once σ is calibrated (via augmentation spread or calibration renders). |
| C7 | Jaw prior on neutral views | σ 2–3° ([3dmm-overview](./3dmm-overview.md), [multi-view-fitting](./multi-view-fitting.md), [flame-model](./flame-model.md), [open-source-pipelines](./open-source-pipelines.md)) vs 1–1.5° ([expression-neutralization](./expression-neutralization.md), which ties it to the 2–4 mm freeway space 📄 ≈ 1.1–2.4°). | Use 1.5° when the neutral tag is confident (blendshape audit passed), and 3° when it is uncertain. [expression-neutralization](./expression-neutralization.md) itself labels the choice ↔️. |
| C8 | FLAME jaw range and 2023 jaw handling | [flame-model](./flame-model.md) Table 2 gives x −0.05 to 0.5 rad; its Table 6 box gives [−0.05, 0.6]. Indirect evidence says FLAME 2023 folds jaw rotation into the expression basis. | Make bounds part of a per-version config, confirm the +x = open sign on load, and never reuse coefficients across versions ([flame-model](./flame-model.md)). |
| C9 | σ floor on a MICA β prior | 0.3 ([single-image-regression](./single-image-regression.md), [open-source-pipelines](./open-source-pipelines.md), [sota-2025-2026](./sota-2025-2026.md)) vs 0.5 for the first 20–50 components, 1.0 above ([identity-embeddings](./identity-embeddings.md)). | Use 0.5 with 1–2 reference photos and 0.3 with ≥3 photos that agree (the spread term then dominates). Both are heuristics to tune on held-out scans. |
| C10 | Weight of generated or synthetic silhouettes | ≤0.1 of a real view ([sota-2025-2026](./sota-2025-2026.md)) vs ≤0.25 ([generative-3d-heads](./generative-3d-heads.md)), whose generator information is also capped at ≈25 % of the landmark information. | 0.1 by default (likeness mode). Allow up to 0.25 only in blockout mode, for seed-ensemble regions with spread ≤5 mm. The weight on identity β and face vertices is always 0. |
| C11 | Neutral pose exported from video avatars | [neural-head-avatars](./neural-head-avatars.md): export the *most neutral tracked frame's* ψ, not ψ = 0. [expression-neutralization](./expression-neutralization.md), [multi-view-fitting](./multi-view-fitting.md), [flame-model](./flame-model.md): hand off ψ = 0. | The two agree once a neutral anchor exists: the anchor prior makes mean ψ over neutral views ≈ 0, so ψ = 0 *is* the person's relaxed face. Without an anchor (most video), export the most-neutral-frame ψ and store both. A habitual expression is identity ([expression-neutralization](./expression-neutralization.md)). |
| C12 | Assumed normal error (κ) | Scene model 20° (κ ≈ 13), human-specific 15° (κ ≈ 23) ([monocular-depth-normals](./monocular-depth-normals.md)) vs face-specific 12–15° (κ ≈ 23–36) ([sota-2025-2026](./sota-2025-2026.md)). | Use 15° for human-specific models and 20° for scene models. Tighten only after measuring face-region error on synthetic heads; no face figure exists for any model. |
| C13 | Scan repeatability (ground-truth floor) | Recalled as 0.3–1 mm RMS ([benchmarks-metrics](./benchmarks-metrics.md) body) vs ≈0.2–0.5 mm (its verification log) and ≈0.2–0.5 mm surface noise ([face-scan-datasets](./face-scan-datasets.md) Table 2). | The corrected ≈0.2–0.5 mm wins. In practice, measure your own double-scan floor. |
| C14 | FLAME licence and units | Older body text in several notes treated all FLAME as non-commercial; earlier albedo text said ship no FLAME. [single-image-regression](./single-image-regression.md) says MICA outputs "300 coefficients in metres". | Verification logs: only FLAME 2023 Open is CC BY 4.0 (📄); the Meshcapade route is unconfirmed. Coefficients are unitless, the FLAME mesh is in metres (🧠), and MICA's demo mesh is in mm (📄). Check one measurement on import. |
| C15 | Inner-canthal width check | ≈28–36 mm ([face-scan-datasets](./face-scan-datasets.md)) vs ≈31–41 mm ([open-source-pipelines](./open-source-pipelines.md)). | Use the union (≈28–41 mm) only as a coarse unit check (×10, ×1000 errors). Take precise norms from [../anatomy/anthropometric-norms.md](../anatomy/anthropometric-norms.md). |
| C16 | MediaPipe licence and transform | [open-source-pipelines](./open-source-pipelines.md): Apache-2.0 code and weights (🧠); 4×4 transform "metric-ish in cm". [landmark-detection](./landmark-detection.md): weights ↔️; transform translation and scale describe a canonical face under an assumed FOV. | Treat code as Apache-2.0 and the weights' terms as "verify per release". Use only the transform's rotation, and only to seed PnP when \|yaw\| < 60°. Never use MediaPipe z, scale or translation as shape evidence. |
| C17 | Iris and IPD values | 11.7 ± 0.5 mm (MediaPipe, 📄), 11.8 ± 0.6 mm ([hair-eyes-teeth-recon](./hair-eyes-teeth-recon.md), 🧠), studies 11.64–11.81 mm with SD 0.24–0.49 mm (✅). IPD 63 ± 3.5–4, 61–64 ± 3–4, 63 ± 3.8 mm (🧠). | Use the iris at 11.7 ± 0.5 mm (the 0.1 mm difference is far below the SD) and IPD 63 ± 3.8 mm, flagged provisional. Prefer a measured value whenever one exists. |
| C18 | Recommended capture distance | [camera-pose-solving](./camera-pose-solving.md): with *calibrated* focal, 0.4–0.6 m is fine and informative. Elsewhere: 1.5–3 m. | No conflict once purpose is separated. The identity set is shot at 1.5–2(–3) m; an optional close shot is useful only when intrinsics are known, for focal identification. |
| C19 | MICA fine-tuning depth | "Last 3 ResNet blocks" (📄, [identity-embeddings](./identity-embeddings.md), [open-source-pipelines](./open-source-pipelines.md)) vs a secondary source saying "all frozen except the last". | Unresolved. This matters only if you train a MICA-type regressor; check the paper first. |

## Index of topic notes

Evidence counts are copied from each note's header (✅ / 📄 / 🧠 / ↔️).

| Note | One-line description | Evidence |
|---|---|---|
| [3dmm-overview](./3dmm-overview.md) | Survey of morphable models (BFM, FLAME, LSFM, LYHM/UHM, FaceScape, ICT-FaceKit…) by licence, coverage, population and topology; adapter schema and ‖β‖² gates | 0 / 3 / 57 / 24 |
| [flame-model](./flame-model.md) | FLAME in depth: arrays, kinematics, versions, licence, texture spaces, ecosystem, Blender import and fitting priors | 0 / 9 / 80 / 8 |
| [deformation-fitting-math](./deformation-fitting-math.md) | Procrustes, 3D RBF (φ = r, K − λI sign trap and an engine bug), Laplacian/biharmonic, ARAP, NICP, PCA as Tikhonov, robust IRLS, LM | 9 / 18 / 29 / 4 |
| [camera-pose-solving](./camera-pose-solving.md) | PnP, focal/depth ambiguity, vanishing points, bundle adjustment, EXIF→Blender camera, simulation tables, camera priors | 4 / 13 / 55 / 9 |
| [camera-perspective-distortion](./camera-perspective-distortion.md) | Why distance distorts faces; selfie-effect numbers; EXIF fields; camera models; distance/focal observability; capture by purpose | 2 / 15 / 81 / 16 |
| [landmark-detection](./landmark-detection.md) | MediaPipe, dlib, FAN, HRNet, SPIGA, Sapiens, dense landmarks; NME→mm; anatomical index map; per-class σ; visibility and calibration | 2 / 2 / 71 / 17 |
| [multi-view-fitting](./multi-view-fitting.md) | Shared-identity multi-image FLAME fitting; trackers (metrical-tracker, VHAP, flame-head-tracker); scale cues; prior table | 7 / 16 / 43 / 3 |
| [expression-neutralization](./expression-neutralization.md) | Identity/expression gauge, neutral definition, expression bias on measurements, per-view expression blocks and tagging | 0 / 4 / 46 / 14 |
| [single-image-regression](./single-image-regression.md) | DECA, EMOCA, MICA, SMIRK, TEASER, 3DDFA_V2, Deep3D, HRN, Pixel3DMM; NoW/REALY numbers; using regressors as priors | 7 / 25 / 42 / 7 |
| [open-source-pipelines](./open-source-pipelines.md) | Runnable research pipelines, their outputs, units, camera conventions, install pain and licences; adapter contract | 8 / 36 / 50 / 8 |
| [sota-2025-2026](./sota-2025-2026.md) | 2024–26 shifts: dense prediction plus optimisation, Gaussian avatars, generative few-shot, geometry foundation models; backend tiers | 0 / 6 / 52 / 21 |
| [commercial-head-tools](./commercial-head-tools.md) | FaceBuilder, Headshot, MetaHuman, FaceGen, Wrap, Polywink, avatar SDKs: mechanics, outputs, accuracy ladder, pins and camera groups | 4 / 2 / 63 / 40 |
| [photogrammetry-heads](./photogrammetry-heads.md) | SfM/MVS of live sitters: motion limits, capture recipe, GSD and DoF arithmetic, software, camera exports, scan-to-template fitting | 1 / 2 / 57 / 15 |
| [generative-3d-heads](./generative-3d-heads.md) | LRMs, 3D latent diffusion, multi-view diffusion and head GANs: what they invent, licences, and a weighted generator data term | 0 / 15 / 44 / 28 |
| [neural-head-avatars](./neural-head-avatars.md) | NeRF and Gaussian head avatars: what they give a sculptor, mesh extraction, 3DGS PLY layout, Gaussian data term | 0 / 2 / 56 / 14 |
| [monocular-depth-normals](./monocular-depth-normals.md) | Depth Anything, Marigold, DSINE, Sapiens and DAViD for faces; why depth never sets proportions; mesh-space normal detail solve | 3 / 34 / 47 / 3 |
| [texture-extraction](./texture-extraction.md) | UV G-buffer projection, visibility, weighting, gain compensation, two-band blending, honest hole filling, de-lighting | 0 / 1 / 59 / 17 |
| [albedo-lighting-inverse-rendering](./albedo-lighting-inverse-rendering.md) | Image formation, SH9 lighting, albedo models, skin-tone bias (TRUST, ITA), chart-anchored de-lighting and priors | 0 / 2 / 74 / 17 |
| [hair-eyes-teeth-recon](./hair-eyes-teeth-recon.md) | Model-based eyes (limbus, gaze), teeth (arch, intraoral scan) and hair (tiers, strand methods, import gates) | 0 / 1 / 52 / 27 |
| [identity-embeddings](./identity-embeddings.md) | ArcFace and InsightFace: thresholds, ONNX contract, MICA's use, likeness scorecard protocol, licences and privacy | 6 / 28 / 37 / 9 |
| [face-scan-datasets](./face-scan-datasets.md) | Public 3D/4D/multi-view face datasets: populations, noise floors, loader conventions, licences, validation recipe | 0 / 0 / 41 / 42 |
| [benchmarks-metrics](./benchmarks-metrics.md) | NoW, REALY, FaceScape, Florence, AFLW2000-3D; metric mechanics and traps; evaluation module and acceptance targets | 0 / 6 / 54 / 26 |

## Related notes outside this area

- **Blender:**
  - [reference-camera-setup](../blender/reference-camera-setup.md), [import-export-scans](../blender/import-export-scans.md), [blender-face-addons](../blender/blender-face-addons.md)
  - [eyes-modeling-blender](../blender/eyes-modeling-blender.md), [hair-blender](../blender/hair-blender.md), [skin-shading](../blender/skin-shading.md), [texture-projection-painting](../blender/texture-projection-painting.md)
  - [metahuman-cc-bridges](../blender/metahuman-cc-bridges.md), [blender-version-status-2026](../blender/blender-version-status-2026.md), [blender-python-ml-deps](../blender/blender-python-ml-deps.md)
- **Anatomy:** [anthropometric-norms](../anatomy/anthropometric-norms.md), [facial-asymmetry](../anatomy/facial-asymmetry.md), [facs-expressions](../anatomy/facs-expressions.md), [mouth-lips-teeth](../anatomy/mouth-lips-teeth.md), [ear](../anatomy/ear.md), [face-perception-likeness](../anatomy/face-perception-likeness.md)
- **Community:** [likeness-mistakes](../community/likeness-mistakes.md), [ai-assisted-sculpting](../community/ai-assisted-sculpting.md), [reference-photography-protocol](../community/reference-photography-protocol.md), [awesome-lists-resources](../community/awesome-lists-resources.md)
- **Ethics:** [licences-tos](../ethics/licences-tos.md), [biometric-privacy](../ethics/biometric-privacy.md), [consent-likeness-law](../ethics/consent-likeness-law.md)
