# Single-image 3D face reconstruction methods

> Single-image regressors map one photo to the coefficients of a morphable model plus a camera. DECA, EMOCA, MICA, SMIRK, TEASER and Pixel3DMM use FLAME; 3DDFA_V2, Deep3DFaceRecon and HRN use the Basel Face Model (BFM). Some also output albedo, lighting or a detail map. On NoW, the standard neutral-shape benchmark, the best widely used identity regressor (MICA) scores about 0.9 mm median and 1.1 mm mean error. A correctly scaled *average* FLAME face scores about 1.5 mm mean, so a regressor captures only part of what makes a face recognisably that person [2][4]. Expression regressors (EMOCA, SMIRK, TEASER) are judged on perceptual metrics rather than shape accuracy, and the region-wise REALY benchmark ranks methods differently from NoW. For a likeness tool, treat these networks as initialisers and priors for a multi-view, perspective-calibrated fit, not as finished heads. Most research weights, and the FLAME and BFM assets they depend on, carry non-commercial terms that must be verified before shipping.
>
> Evidence status: 3 ✅ / 15 📄 / 39 🧠 / 8 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Benchmarks and what they measure**
- **NoW protocol.** The prediction is rigidly aligned to the ground-truth scan using 7 landmarks. Error is then reported in mm as median, mean and std over all subjects [2][4]. ✅
- **NoW details** (Sanyal et al., CVPR 2019). The dataset has about 2,054 iPhone images of 100 subjects in four conditions: neutral, expression, occlusion and selfie. The validation split has 20 subjects and the test split has 80, with hidden ground truth. The error is the distance from each scan vertex to the predicted *surface*. The standard ("non-metrical") challenge also solves for scale. MICA added a *metrical* variant that does not. 🧠
- **Metrics differ between papers.** Some report Chamfer distance instead of NoW scan-to-mesh error, so cross-paper tables are not strictly comparable [5]. 📄
- **NoW is blind to fine detail.** DECA's detail layer moves median error from 1.18 to 1.19 mm [1][3]. ✅
- **What NoW does not measure.** NoW scores neutral shape only. It does not measure expression fidelity, absolute size (scale is solved away), texture or perceived likeness. Errors are averaged over the whole face, which dilutes the eye, lip and nose differences that drive recognition. 🧠
- **REALY** (Chai et al., ECCV 2022) uses about 100 Headspace/LYHM scans. It aligns each region separately and reports errors for the nose, mouth, forehead and cheek, so it penalises local shape errors that NoW averages out. 🧠

**Methods**
- **DECA** (SIGGRAPH 2021). On NoW **validation** it scores 1.18 / 1.46 / 1.25 mm (median / mean / std) for the coarse mesh and 1.19 / 1.47 / 1.25 mm for the detailed mesh [1]. Two later papers repeat these figures [2][3]. ✅
- **DECA's second row.** A DECA row of 1.09 / 1.38 / 1.18 mm also appears in [1] 📄. This is almost certainly the NoW **test**-split figure, which also appears on the public leaderboard 🧠.
- **DECA outputs.** A ResNet-50 regresses, from a 224 px crop:
  - FLAME shape (100 coefficients) and expression (50);
  - global and jaw pose;
  - a weak-perspective camera (scale plus 2D translation);
  - albedo (50) and spherical-harmonic lighting (27);
  - a 128-d detail code that decodes to a UV displacement map conditioned on expression.
  
  It was trained on roughly 2 M in-the-wild images. 🧠
- **EMOCA** (Daněček, Black, Bolkart, CVPR 2022) adds an expression encoder trained with an emotion-consistency loss. Identity comes from DECA's frozen coarse encoder, so its NoW shape numbers equal DECA's. EMOCA v2 lives in the authors' "inferno" repository. 🧠
- **MICA** predicts a *metrical*, neutral-expression FLAME shape from one image. It takes identity features from a face-recognition network and is trained with supervision [4]. 📄 MICA reports 15 % lower error than prior methods on NoW and 24 % lower on the metrical evaluation [4]. 📄
- **MICA details.** The face-recognition network is ArcFace, mostly frozen. The output is 300 FLAME shape coefficients in metres. MICA was trained on about 2,300 subjects pooled from eight registered 3D datasets. It is paired with the authors' *metrical-tracker* for video. 🧠
- **MICA scores** range from 0.90 to 0.94 mm median and 1.11 to 1.19 mm mean, depending on the paper and protocol [2][5][6]. ↔️ The value 0.90 / 1.11 / 0.92 matches the public test leaderboard. 🧠
- **Baseline: the average FLAME mesh** scores 1.92 mm mean, or 1.53 mm once its scale is optimised [4]. 📄
- **"Towards Realistic Generative 3D Face Models"** reports 23 % (coarse) and 20 % (detailed) better median error than DECA [2]. 📄
- **SMIRK** (CVPR 2024) replaces the differentiable rasteriser with a neural renderer. The renderer takes the predicted FLAME geometry plus sparse pixels from the input image, so the image reconstruction loss trains the expression geometry [7]. 📄 The paper and repository [8] come from the same authors, so they are not independent sources.
- **SMIRK training data** mixes FFHQ, CelebA, MEAD and LRS3 [7]. 📄 The repo snapshot showed about 396 stars and a last update on 31 May 2024 [8]. 📄 (stale)
- **SMIRK outputs** FLAME expression plus eyelid parameters, jaw and head pose, and a weak-perspective camera. It uses MediaPipe landmarks. 🧠
- **TEASER** (ICLR 2025) adds multi-scale appearance tokens and a token-guided neural renderer on top of a SMIRK-style pipeline. A search summary credits it with better expression accuracy than SMIRK [9]. 📄 This was not checked against the paper's tables. ↔️
- **3DDFA_V2** (ECCV 2020) has an official PyTorch implementation [10][11]. It detects faces with FaceBoxes and claims more than 50 fps [10][11]. 📄 Face detection dominates its latency at about 15 ms per 720p frame, and alignment can fail above about 90° pose [10]. 📄 A community TFLite port exists [12]. 📄
- **3DDFA_V2 details.** A MobileNet regresses 62 parameters: a 12-value 3×4 pose matrix, 40 BFM shape coefficients and 10 expression coefficients. The mesh is a reduced BFM. Identity capacity is low, so use it for pose and landmarks, not likeness. 🧠
- **Deep3DFaceRecon** (Deng et al., CVPR-W 2019, Microsoft) uses a ResNet-50 that regresses 257 BFM coefficients:
  - 80 identity, 64 expression and 80 texture coefficients;
  - 3 rotation and 3 translation values;
  - 27 SH lighting values.

  It uses a *perspective* camera with a fixed focal length (about 1015 px for a 224 px crop). Training is weakly supervised, combining a photometric, a landmark and a face-recognition perceptual loss. The output is a face-only mesh with no ears or back of the head. 🧠
- **HRN** (Lei et al., CVPR 2023, Alibaba) is a hierarchical model. A BFM base carries the low frequencies, a deformation map the mid frequencies and a displacement map the high frequencies. It outputs a textured OBJ and has a multi-view variant (MV-HRN). At release it led REALY. 🧠
- **Pixel3DMM** (Giebenhain et al., 2025) fine-tunes a DINO-family ViT to predict per-pixel surface normals and FLAME UV coordinates, then *optimises* FLAME against them. It is slow but strong on posed expressions, and introduced a NeRSemble-based benchmark. 🧠
- **Newer and parallel work:**
  - SEREP [13] (expression), KaoLRM [5] (an LRM backbone regressing FLAME) and a profile-only regressor [6]. 📄
  - TokenFace, FlowFace, FOCUS (robust to occlusion) and SPECTRE (accurate on speech and lips). 🧠
- **MediaPipe Face Landmarker** is not a 3DMM. It outputs 478 3D landmarks, 52 blendshape scores and a head transform, under Apache-2.0, and runs in real time on CPU. 🧠
- **Licences.**
  - The DECA, EMOCA and MICA code is under MPI-style non-commercial research licences. 🧠
  - The 3DDFA_V2 and Deep3DFaceRecon_pytorch code is MIT-licensed, but both depend on BFM, which requires registration and is for non-commercial use. 🧠
  - FLAME was historically non-commercial. A later "FLAME 2023 Open" release is reportedly CC-BY-4.0. ↔️
  - The SMIRK, TEASER, HRN and Pixel3DMM licences are unconfirmed.

## Numbers & reference tables

**Table 1: NoW errors (mm).** Population: NoW subjects (20 in validation, 80 in test 🧠). The prediction is aligned with a similarity transform unless the row is labelled metrical.

| Method / variant | Split | Median | Mean | Std | Source | Status |
|---|---|---|---|---|---|---|
| Average FLAME, no scale fit | n/s | – | 1.92 | – | [4] | 📄 |
| Average FLAME, scale optimised | n/s | – | 1.53 | – | [4] | 📄 |
| PRNet | test | ≈1.50 | ≈1.98 | ≈1.88 | leaderboard (name) | 🧠 |
| 3DDFA_V2 | test | ≈1.23 | ≈1.57 | ≈1.39 | leaderboard (name) | 🧠 |
| RingNet | test | ≈1.21 | ≈1.53 | ≈1.31 | leaderboard (name) | 🧠 |
| Deep3DFaceRecon (PyTorch) | test | ≈1.11 | ≈1.41 | ≈1.21 | leaderboard (name) | 🧠 |
| DECA coarse | val | 1.18 | 1.46 | 1.25 | [1][2] | ✅ |
| DECA detailed | val | 1.19 | 1.47 | 1.25 | [1][3] | ✅ |
| DECA (summary row) | test (🧠) | 1.09 | 1.38 | 1.18 | [1] | 📄 |
| EMOCA v1 | test | = DECA | = DECA | = DECA | (name) | 🧠 |
| MICA row A | n/s | 0.913 | 1.130 | 0.948 | [2] | ↔️ |
| MICA row B (= leaderboard test) | test (🧠) | 0.90 | 1.11 | 0.92 | [2] | ↔️ |
| MICA, profile images | profile | 0.9432 | 1.1606 | – | [6] | 📄 |
| MICA, Chamfer-style | val | – | ≈1.19 | – | [5] | 📄 |
| TokenFace | test | ≈0.76 | ≈0.95 | ≈0.82 | (name) | 🧠 |

**Table 2: Method cards.** Speeds are order-of-magnitude figures for one face on a recent consumer GPU, excluding detection, unless a citation is given.

| Method | Model, parameters | Camera | Metric scale? | Code | Licence (code / assets) | Speed | Status |
|---|---|---|---|---|---|---|---|
| DECA | FLAME 100 shape / 50 expression + detail UV | weak-perspective | no | yes | non-commercial / FLAME | ~10 ms | 🧠 |
| EMOCA | DECA + expression encoder | weak-perspective | no | yes | non-commercial / FLAME | ~10 ms | 🧠 |
| MICA | FLAME 300 shape, neutral | none (shape only) | yes, learned | yes | non-commercial / FLAME + ArcFace | ~10 ms + detection | 🧠 |
| SMIRK | FLAME shape, expression and eyelids | weak-perspective | no | [8] | unconfirmed | ~10 ms | 📄/🧠 |
| TEASER | FLAME (SMIRK-style) | weak-perspective | no | unconfirmed | unconfirmed | ~10 ms | 🧠 |
| 3DDFA_V2 | BFM 40 shape / 10 expression, 3×4 pose | weak-perspective (affine) | no | [10] | MIT / BFM | >50 fps [10][11] | 📄 |
| Deep3DFaceRecon | BFM 80 / 64 / 80, 257 coefficients | perspective, f≈1015 px @224 | no | yes | MIT / BFM | ~10 ms | 🧠 |
| HRN | BFM + deformation and displacement maps | perspective | no | yes | unconfirmed | sub-second | 🧠 |
| Pixel3DMM | FLAME, fitted to ViT normals and UVs | perspective (optimised) | partial | yes | unconfirmed | tens of s+ | 🧠 |
| MediaPipe | 478 landmarks, 52 blendshape scores | perspective transform | no | yes | Apache-2.0 | real-time on CPU | 🧠 |

**Table 3: Morphable-model assets.**

| Asset | Vertices | Bases | Training population | Status |
|---|---|---|---|---|
| FLAME (2017/2020) | 5,023 vertices, 9,976 triangles; full head with neck, ears and eyeballs | 300 shape, 100 expression, 5 joints | about 3,800 CAESAR heads (Western adults) plus 4D expression scans | 🧠 |
| BFM 2009 | 53,490 | 199 shape / 199 texture | 200 adults, 100 female and 100 male, mostly European | 🧠 |
| BFM as cropped by Deep3D | about 35,709 | 80 identity + 64 expression | as above, with FaceWarehouse expressions | 🧠 |

**Table 4: Selfie distortion (geometry).** Magnification of the nose tip relative to the ears is (D+d)/D, with depth difference d ≈ 0.09 m.

| Camera distance D | 0.3 m | 0.5 m | 1 m | 2 m | 3 m |
|---|---|---|---|---|---|
| Nose-tip vs ear magnification | ≈1.30 | ≈1.18 | ≈1.09 | ≈1.045 | ≈1.03 |

Status: 🧠 (arithmetic)

**Table 5: REALY, frontal track, average over regions (mm).** The figures are approximate.

| Group | Error | Status |
|---|---|---|
| HRN and other detail-hierarchy methods | ≈1.5–1.6 | 🧠 |
| Deep3DFaceRecon | ≈1.6–1.7 | 🧠 |
| DECA, EMOCA, 3DDFA_V2 | ≈1.9–2.2 | ↔️ |

## Applying this to photo→3D face sculpting in Blender

1. **Photo intake.**
   - Have the subject keep a neutral expression with lips closed and relaxed.
   - Keep hair off the forehead and ears, and remove glasses.
   - Shoot from ≥1.5–2 m with a lens of 85 mm or longer (full-frame equivalent).
   - Take 5–9 views: frontal, ±30–45°, both profiles, and slightly high and low.

   Selfies taken at 0.3–0.5 m inflate the nose and mid-face by 18–30 % relative to the ears (Table 4). Weak-perspective regressors (DECA, EMOCA, SMIRK, 3DDFA_V2) bake that inflation into the *shape*.
2. **Pick a backend per job.**
   - Use MICA (or a MICA average over several photos) for the neutral identity and an initial size estimate [4].
   - Use SMIRK, EMOCA or TEASER only to *measure* expression. Reject frames where expression or jaw opening is non-trivial [7][9].
   - Use 3DDFA_V2 or MediaPipe for pose and landmarks [10].
3. **Set expectations.** The base mesh will still carry about 1 mm mean error with a heavy tail (std 0.9–1.25 mm) [1][2]. The error concentrates in depth (nose projection, chin, orbits), because a frontal image observes depth weakly. Budget a correction pass for the profile silhouette and lips.
4. **Fix scale explicitly.** NoW figures say nothing about absolute size, because scale is solved during alignment [4].
   - Anchor scale with a measured quantity: a ruler in frame, measured head breadth, or iris diameter (adult average about 11.7 mm, SD about 0.5 mm 🧠).
   - Check the anthropometrics: bizygomatic breadth 120–150 mm and head length 175–205 mm for adults 🧠.
   - FLAME's native unit is metres. Keep the Blender unit scale at 1.0.
5. **Neutralise before sculpting.** Fit expression per photo, then zero the expression and jaw values on the identity mesh. Expressive photos leak into DECA-style identity estimates. MICA is more robust here because its identity features are expression-invariant [4].
6. **Check in Blender.**
   - Load each photo as a camera background, using the solved perspective camera rather than the regressor's orthographic one.
   - Compare landmark reprojection; the target is under about 1–2 % of interocular distance.
   - Compare the profile silhouette overlay.
   - Mirror-compare the two halves: PCA regressors suppress real asymmetry.
7. **Expect these failures:**
   - regression toward the mean, which looks "generic" or "everyone looks alike";
   - flattened depth;
   - generic ears and cranial vault, since they are never observed under hair;
   - a jawline hidden by beards;
   - wrong eyelid aperture;
   - lower accuracy for children and under-represented populations (FLAME and BFM training sets are mostly Western adults).
8. **Topology.** FLAME (5,023 vertices) is a usable sculpt cage: add multires levels and keep the base as a shape key. BFM outputs are a face mask with no back of head, so warp a full template onto them instead. Treat DECA and HRN detail as a separate displacement layer and do not judge likeness from it [1].
9. **Latency.** For live preview, detect once and then track. Detection, not regression, dominates the per-frame cost [10].

## Algorithmic implications

- **Backend contract.** Each backend returns:
  - topology (FLAME or BFM), coefficients and landmarks;
  - landmark convention: iBUG-68 2D, 3D-consistent, or MediaPipe-478;
  - camera type (weak-perspective, affine or perspective);
  - a flag for whether the output is metric;
  - its licence.

  Ship the default path with only MIT and Apache components (MediaPipe plus our own fitter). Make research backends user-installed opt-ins.
- **Converting weak perspective to perspective (derived).** DECA-style projections are x = s·(X + t) in [−1, 1] crop coordinates. For a square crop of side W_b pixels in the original image and a focal length of f px (from EXIF, or a default 50 mm equivalent):
  - initial depth Z₀ = 2f / (s·W_b);
  - lateral position = (pixel offset of the crop-space translation) · Z₀ / f.

  For 3DDFA_V2, split its 3×4 matrix into scale and rotation by SVD before refining. 🧠
- **Identity prior.** FLAME shape coefficients have nominally unit variance 🧠. Run the regressor on each of the N photos and take the median code β̄ per component, so that one bad frame does not drag the estimate.
  - Prior: β ~ N(β̄, diag(σ²)), where σ_k is the spread of β_k across photos with a floor of about 0.3 (MICA) or 0.6 (DECA).
  - Components the regressor does not predict (DECA's 101–300) get σ = 1.
  - These σ values are design defaults, not sourced values. Tune them on held-out scans.
- **Residual model.** The draft's own derivation assumes half-normal errors, which gives median ≈ 0.674σ, mean ≈ 0.798σ and std ≈ 0.603σ.
  - Then MICA's 0.90 / 1.11 / 0.92 mm implies σ ≈ 1.33–1.53 mm, and DECA validation implies σ ≈ 1.75–2.07 mm.
  - In both cases mean/median ≈ 1.23, against 1.18 for a true half-normal, so the tails are heavy.
  - Use Huber or Student-t losses with scale ≈ 1.4 mm for MICA initialisation and ≈ 1.8 mm for DECA.
- **Scale prior.** Use a separate log-scale prior with σ ≈ 0.04–0.05 for MICA-derived scale (a statistical guess) and ≥ 0.10 for non-metric backends. Tighten it to ≈ 0.01 with a user measurement. These are design defaults. 🧠
- **Contour landmarks.** 2D detectors place jawline points on the visible silhouette, while 3D-consistent schemes fix them on the mesh. Use sliding contour correspondences or a silhouette term, or yaw-dependent bias will distort jaw width. 🧠
- **Factorisation.** Share identity β and scale across views. Fit expression ψ, jaw and pose per view. Set ψ to 0 at hand-off. Gate out frames with |yaw| ≳ 90° for 3DDFA_V2 initialisation [10], and down-weight views where backends disagree.
- **Evaluation harness.** Implement a NoW-style metric: 7-landmark alignment, scan-to-surface distance, and median, mean and std [2][4]. Run it in both a similarity mode and a metric (no-scale) mode, and add REALY-style per-region errors. Log the split, metric and mesh variant [5].

## Disagreements, myths & open questions

- **DECA's two rows.** 1.09 / 1.38 mm is the test split and 1.18 / 1.46 mm is the validation split (attribution 🧠; numbers [1][2][3]). Always cite the split with the number.
- **MICA spread.** MICA's median ranges from 0.90 to 0.94 mm and its mean from 1.11 to 1.19 mm across [2][5][6]. Metric and split differences are the likely causes. ↔️
- **Refuted: "MICA's NoW mean is 1.53 mm."** That figure is the scale-optimised *average-mesh* baseline [4].
- **Myth: "a detailed mesh is more accurate."** On NoW it is not [1][3].
- **Myth: "a lower NoW score means better likeness."** NoW is a whole-face, scale-free, neutral-shape metric, and REALY reorders methods. ↔️
- **Myth: "MICA gives true metric size."** MICA's scale is learned from appearance–size correlations, which makes it a prior, not a measurement. 🧠
- **Myth: "a regressor's fps equals pipeline fps."** Detection dominates [10].
- **Myth: "generic image-to-3D models (LRMs) beat 3DMMs for faces."** They produce plausible but non-metric and identity-drifting meshes. KaoLRM [5] constrains an LRM to FLAME for this reason. ↔️
- **"TEASER beats SMIRK"** is unverified [9]. Pixel3DMM's improvement claims and HRN's REALY lead are also unverified (🧠).
- **Open questions.**
  - Every licence, especially FLAME 2023 Open and the SMIRK, HRN, Pixel3DMM and TEASER repositories.
  - Measured GPU timings.
  - NoW scores for SMIRK, HRN and Pixel3DMM.
  - The exact REALY numbers.
  - Whether the [4] average-mesh baseline used the same split as the other NoW rows.

## Sources

1. Learning an Animatable Detailed 3D Face Model from In-The-Wild Images (DECA) — https://arxiv.org/abs/2012.04012 — paper — 2021
2. Towards Realistic Generative 3D Face Models — https://arxiv.org/pdf/2304.12483 — paper — 2023
3. SIDER: Single-Image Neural Optimization for Facial Geometric Detail Recovery — https://arxiv.org/pdf/2108.05465 — paper — 2021
4. Towards Metrical Reconstruction of Human Faces (MICA) — https://ar5iv.labs.arxiv.org/html/2204.06607 — paper — 2022
5. KaoLRM: Repurposing Pre-trained Large Reconstruction Models for Parametric 3D Face Reconstruction — https://arxiv.org/pdf/2601.12736 — paper — 2026
6. Profile-Specific 3DMM Regression from a Single Lateral Face Image — https://arxiv.org/html/2605.01746 — paper — 2026
7. SMIRK: 3D Facial Expressions through Analysis-by-Neural-Synthesis — https://arxiv.org/html/2404.04104 — paper — 2024
8. georgeretsi/smirk: Official PyTorch Implementation of SMIRK (CVPR 2024) — https://github.com/georgeretsi/smirk — repo — 2024
9. TEASER: Token Enhanced Spatial Modeling for Expressions Reconstruction — https://arxiv.org/pdf/2502.10982 — paper — 2025
10. cleardusk/3DDFA_V2: Official PyTorch implementation of ECCV 2020 3D dense face alignment — https://github.com/cleardusk/3DDFA_V2 — repo — 2020
11. Towards Fast, Accurate and Stable 3D Dense Face Alignment — https://arxiv.org/pdf/2009.09960v2 — paper — 2020
12. 1996scarlet/Dense-Head-Pose-Estimation (3DDFAv2 TFLite reimplementation) — https://github.com/1996scarlet/Dense-Head-Pose-Estimation — repo — 2020
13. SEREP: Semantic Facial Expression Representation for Robust In-the-Wild Capture and Retargeting — https://arxiv.org/pdf/2412.14371 — paper — 2024
14. A survey and classification of face alignment methods based on face models — https://arxiv.org/pdf/2311.03082 — paper — 2023

**Further reading (by name, not yet linked)**
- Sanyal, Bolkart, Feng, Black — Learning to Regress 3D Face Shape and Expression from an Image without 3D Supervision (RingNet; NoW benchmark), CVPR 2019
- Li, Bolkart, Black, Li, Romero — Learning a Model of Facial Shape and Expression from 4D Scans (FLAME), SIGGRAPH Asia 2017
- Paysan, Knothe, Amberg, Romdhani, Vetter — A 3D Face Model for Pose and Illumination Invariant Face Recognition (BFM 2009), AVSS 2009
- Blanz & Vetter — A Morphable Model for the Synthesis of 3D Faces, SIGGRAPH 1999
- Daněček, Black, Bolkart — EMOCA: Emotion Driven Monocular Face Capture and Animation, CVPR 2022
- Deng et al. — Accurate 3D Face Reconstruction with Weakly-Supervised Learning: From Single Image to Image Set, CVPR Workshops 2019
- Chai et al. — REALY: Rethinking the Evaluation of 3D Face Reconstruction, ECCV 2022
- Lei et al. — A Hierarchical Representation Network for Accurate and Detailed Face Reconstruction from In-The-Wild Images (HRN), CVPR 2023
- Giebenhain et al. — Pixel3DMM: Versatile Screen-Space Priors for Single-Image 3D Face Reconstruction, 2025
- Feng et al. — Joint 3D Face Reconstruction and Dense Alignment with Position Map Regression Network (PRNet), ECCV 2018
- Filntisis et al. — Visual Speech-Aware Perceptual 3D Facial Expression Reconstruction from Videos (SPECTRE), 2022
- Kartynnik et al. — Real-time Facial Surface Geometry from Monocular Video on Mobile GPUs (MediaPipe Face Mesh), CVPR Workshops 2019
- Egger et al. — 3D Morphable Face Models: Past, Present, and Future, ACM TOG 2020
- Zollhöfer et al. — State of the Art on Monocular 3D Face Reconstruction, Tracking, and Applications, Eurographics STAR 2018
