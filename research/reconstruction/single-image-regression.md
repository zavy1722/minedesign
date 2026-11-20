# Single-image 3D face reconstruction methods

> Single-image regressors map one photo to morphable-model coefficients plus a camera. DECA, EMOCA, MICA, SMIRK, TEASER and Pixel3DMM use FLAME. 3DDFA_V2, Deep3DFaceRecon and HRN use the Basel Face Model (BFM). On NoW, the standard neutral-shape benchmark, the best widely used identity regressor (MICA) reaches about 0.9 mm median and 1.1 mm mean error. A correctly scaled *average* FLAME face already reaches about 1.5 mm mean, so regressors capture only part of what makes a face recognisable [2][4]. Expression regressors are judged on perceptual metrics rather than shape accuracy, and REALY ranks methods differently from NoW. Use them as initialisers and priors for a multi-view, perspective-calibrated fit. Most research weights, and the FLAME and BFM assets they depend on, carry non-commercial terms.
>
> Evidence status: 7 ✅ / 26 📄 / 42 🧠 / 7 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Benchmarks**
- **NoW protocol.** The prediction is aligned to the ground-truth scan using 7 landmarks. Error is reported in mm as median, mean and std over subjects [2][4]. ✅
- **NoW details** (Sanyal et al., CVPR 2019). About 2,054 iPhone images of 100 subjects, in four conditions: neutral, expression, occlusion and selfie. Validation has 20 subjects and test has 80, with hidden ground truth. Error is measured from each scan vertex to the predicted *surface*. The standard ("non-metrical") challenge also solves for scale. MICA added a metrical variant that does not. 🧠
- **Metrics differ.** Some papers report Chamfer distance instead of NoW scan-to-mesh error [5]. 📄
- **NoW is blind to detail.** DECA's detail layer moves median error from 1.18 to 1.19 mm [1][3]. ✅
- **NoW does not score** expression, absolute size, texture or likeness; whole-face averaging dilutes the eye, lip and nose errors that drive recognition. 🧠
- **REALY** (Chai et al., ECCV 2022) uses about 100 Headspace/LYHM scans. It aligns each region separately and reports nose, mouth, forehead and cheek errors, so local errors are not averaged away. 🧠

**Methods**
- **DECA (SIGGRAPH 2021), NoW validation scores** (median / mean / std):
  - coarse mesh: 1.18 / 1.46 / 1.25 mm;
  - detailed mesh: 1.19 / 1.47 / 1.25 mm.

  These come from [1] and are repeated by [2][3]. ✅
- **DECA's second row** (1.09 / 1.38 / 1.18 mm) also appears in [1] 📄. It is the **test** split, the same figure as on the public NoW non-metrical leaderboard [16]. 📄
- **DECA architecture.** A ResNet-50 takes a 224 px crop and regresses:
  - FLAME shape (100 coefficients), expression (50), and global and jaw pose;
  - a weak-perspective camera (scale plus 2D translation);
  - albedo (50) and spherical-harmonic (SH) lighting (27);
  - a 128-d detail code, decoded to an expression-conditioned UV displacement map.

  It was trained on roughly 2 M in-the-wild images. 🧠
- **EMOCA** (CVPR 2022) adds an emotion-supervised expression encoder. It keeps DECA's frozen identity encoder, so its NoW scores equal DECA's. v2 lives in the authors' "inferno" repository. 🧠
- **MICA** predicts a *metrical*, neutral FLAME shape from one image. It uses identity features from a face-recognition network and is trained with supervision [4] 📄. It reports 15 % lower error than prior methods on NoW and 24 % lower on the metrical evaluation [4][18]. 📄
- **MICA details.** The backbone is ArcFace, mostly frozen. The output is 300 FLAME shape coefficients in metres. It was trained on about 2,300 subjects from eight registered 3D datasets. Its companion *metrical-tracker* handles video. 🧠
- **MICA score spread** across papers and protocols: median 0.90–0.94 mm, mean 1.11–1.19 mm [2][5][6] ↔️. The 0.90 / 1.11 / 0.92 row matches the public test leaderboard [16]. 📄
- **Baseline: the average FLAME mesh** scores 1.92 mm mean, or 1.53 mm once scale is optimised [4]. 📄
- **"Towards Realistic Generative 3D Face Models"** reports 23 % (coarse) and 20 % (detailed) lower median error than DECA [2]. 📄
- **SMIRK** (CVPR 2024) replaces the differentiable rasteriser with a neural renderer. The renderer is fed the predicted FLAME geometry plus sparse input pixels, so the photometric loss trains the expression geometry [7]. 📄 The repo [8] is by the same authors, so it is not an independent source.
- **SMIRK training data** is FFHQ, CelebA, MEAD and LRS3 [7]. 📄 Repo snapshot: about 396 stars, last update 31 May 2024 [8]. 📄 (stale) Outputs: FLAME expression, eyelids, jaw/head pose, weak-perspective camera; uses MediaPipe landmarks. 🧠
- **TEASER** (ICLR 2025) adds multi-scale tokens and a token-guided neural renderer to a SMIRK-style design. A search summary claims it is more expression-accurate than SMIRK [9]. 📄 The paper's tables have not been checked. ↔️
- **3DDFA_V2** (ECCV 2020) has an official PyTorch implementation [10][11].
  - It detects faces with FaceBoxes and claims more than 50 fps [10][11]. 📄
  - Detection takes about 15 ms per 720p frame, and alignment fails above about 90° pose [10]. 📄
  - A community TFLite port exists [12]. 📄
- **3DDFA_V2 model.** A MobileNet regresses 62 parameters: a 12-value 3×4 pose matrix, 40 BFM shape coefficients and 10 expression coefficients. It has low identity capacity, so use it for pose and landmarks only. 🧠
- **Deep3DFaceRecon** (Deng et al., CVPR-W 2019). A ResNet-50 regresses 257 BFM coefficients: identity 80, expression 64, texture 80, pose 6 and SH lighting 27.
  - It uses a perspective camera with a fixed focal length of about 1015 px at 224 px.
  - Training is weakly supervised with photometric, landmark and face-recognition losses.
  - The output is a face-only mesh with no ears or back of head. 🧠
- **HRN** (Lei et al., CVPR 2023) stacks a BFM base for low frequencies, a deformation map for mid frequencies and a displacement map for high frequencies. It outputs a textured OBJ and has a multi-view variant. It led REALY at release. 🧠
- **Pixel3DMM** (Giebenhain et al., 2025) uses a DINO-family ViT to predict per-pixel normals and FLAME UV coordinates, then *optimises* FLAME against them. It is slow but strong on posed expressions, and comes with a NeRSemble-based benchmark. 🧠 On NoW it matches FlowFace (the best optimisation-based approach) and is worse than TokenFace [19]. 📄
- **Newer and parallel work.** SEREP [13], KaoLRM (an LRM regressing FLAME) [5] and a profile-only regressor [6]. 📄 Also TokenFace, FlowFace, FOCUS (robust to occlusion) and SPECTRE (lip accuracy). 🧠
- **MediaPipe Face Landmarker** gives 478 3D landmarks, 52 blendshape scores and a head transform. It is Apache-2.0 and runs in real time on CPU. 🧠
- **Licences** (verify before shipping):
  - The DECA, EMOCA and MICA code is under non-commercial research licences. 🧠
  - The 3DDFA_V2 and Deep3DFaceRecon_pytorch code is MIT, but both need BFM, which is registration-only and non-commercial [17] 📄 (the MIT claim is unconfirmed 🧠).
  - FLAME was historically non-commercial; a "FLAME 2023 Open" release is CC-BY-4.0, and only that release is commercial-friendly; textures carry separate BY-NC-SA terms [15]. 📄
  - The SMIRK, TEASER, HRN and Pixel3DMM licences are unconfirmed.

## Numbers & reference tables

**Table 1: NoW errors in mm.** Population: NoW subjects. Errors use a similarity alignment unless the row is marked metrical. "Leaderboard" means the public NoW leaderboard, cited by name and not linked; n/s means the split was not stated.

| Method / variant | Split | Median | Mean | Std | Source | Status |
|---|---|---|---|---|---|---|
| Average FLAME, no scale fit | n/s | – | 1.92 | – | [4] | 📄 |
| Average FLAME, scale optimised | n/s | – | 1.53 | – | [4] | 📄 |
| PRNet | test | ≈1.50 | ≈1.98 | ≈1.88 | leaderboard | 🧠 |
| 3DDFA_V2 | test | ≈1.23 | ≈1.57 | ≈1.39 | leaderboard | 🧠 |
| RingNet | test | ≈1.21 | ≈1.53 | ≈1.31 | leaderboard | 🧠 |
| Deep3DFaceRecon (PyTorch) | test | ≈1.11 | ≈1.41 | ≈1.21 | leaderboard | 🧠 |
| DECA coarse | val | 1.18 | 1.46 | 1.25 | [1][2] | ✅ |
| DECA detailed | val | 1.19 | 1.47 | 1.25 | [1][3] | ✅ |
| DECA summary row | test | 1.09 | 1.38 | 1.18 | [1][16] | ✅ |
| EMOCA v1 | test | = DECA | = DECA | = DECA | paper | 🧠 |
| MICA row A | n/s | 0.913 | 1.130 | 0.948 | [2] | ↔️ |
| MICA row B | test | 0.90 | 1.11 | 0.92 | [2][16] | ✅ |
| MICA, profile images | profile | 0.9432 | 1.1606 | – | [6] | 📄 |
| MICA, Chamfer-style | val | – | ≈1.19 | – | [5] | 📄 |
| TokenFace | test | 0.76 | 0.95 | 0.82 | [16] | 📄 |

**Table 2: Method cards.** Speed is an order-of-magnitude figure for one face on a recent consumer GPU, excluding detection, unless a source is cited.

| Method | Model, parameters | Camera | Metric? | Code | Licence (code / assets) | Speed | Status |
|---|---|---|---|---|---|---|---|
| DECA | FLAME 100 shape / 50 expression + detail map | weak-perspective | no | yes | non-commercial / FLAME | ~10 ms | 🧠 |
| EMOCA | DECA + expression encoder | weak-perspective | no | yes | non-commercial / FLAME | ~10 ms | 🧠 |
| MICA | FLAME 300 shape, neutral | none | learned | yes | non-commercial / FLAME + ArcFace | ~10 ms | 🧠 |
| SMIRK | FLAME shape / expression / eyelids | weak-perspective | no | [8] | unconfirmed | ~10 ms | 📄 |
| TEASER | FLAME, SMIRK-style | weak-perspective | no | unconfirmed | unconfirmed | ~10 ms | 🧠 |
| 3DDFA_V2 | BFM 40 shape / 10 expression | 3×4 affine | no | [10] | MIT / BFM | >50 fps [10][11] | 📄 |
| Deep3DFaceRecon | BFM, 257 coefficients | perspective, f≈1015 @224 | no | yes | MIT / BFM | ~10 ms | 🧠 |
| HRN | BFM + deformation and displacement maps | perspective | no | yes | unconfirmed | sub-second | 🧠 |
| Pixel3DMM | FLAME fitted to normals and UVs | perspective | partial | yes | unconfirmed | tens of seconds+ | 🧠 |
| MediaPipe | 478 landmarks + 52 blendshape scores | perspective | no | yes | Apache-2.0 | real-time on CPU | 🧠 |

**Table 3: Morphable-model assets.**

| Asset | Vertices | Bases | Training population | Status |
|---|---|---|---|---|
| FLAME 2017/2020 | 5,023 vertices, 9,976 triangles; head, neck, ears, eyeballs | 300 shape / 100 expression / 5 joints | about 3,800 CAESAR adults + 4D expression scans | 🧠 |
| BFM 2009 | 53,490 | 199 shape / 199 texture | 200 adults (100 F / 100 M), mostly European | 🧠 |
| BFM as cropped by Deep3D | ≈35,709 | 80 identity + 64 expression | as above, plus FaceWarehouse expressions | 🧠 |

**Table 4: Selfie distortion.** Magnification of the nose tip relative to the ears is (D+d)/D, with depth difference d ≈ 0.09 m. Status 🧠 (arithmetic).

| Distance D | 0.3 m | 0.5 m | 1 m | 2 m | 3 m |
|---|---|---|---|---|---|
| Magnification | ≈1.30 | ≈1.18 | ≈1.09 | ≈1.045 | ≈1.03 |

**Table 5: REALY frontal error, averaged over regions, in mm (approximate).**

| Group | Error | Status |
|---|---|---|
| HRN and other detail-hierarchy methods | ≈1.5–1.6 | 🧠 |
| Deep3DFaceRecon | ≈1.6–1.7 | 🧠 |
| DECA, EMOCA, 3DDFA_V2 | ≈1.9–2.2 | ↔️ |

## Applying this to photo→3D face sculpting in Blender

1. **Photo intake.**
   - Subject: neutral expression, lips closed, hair off forehead and ears, no glasses.
   - Camera: ≥1.5–2 m away with an 85 mm+ (full-frame equivalent) lens.
   - Views: 5–9, covering frontal, ±30–45°, both profiles, and slightly high and low.

   Selfies taken at 0.3–0.5 m inflate the mid-face by 18–30 % relative to the ears (Table 4). Weak-perspective regressors bake that inflation into the shape.
2. **Backend per job.**
   - MICA, median-averaged over photos, gives the neutral identity and a size guess [4].
   - SMIRK, EMOCA or TEASER only *measure* expression; reject frames where it is non-trivial [7][9].
   - 3DDFA_V2 or MediaPipe give pose and landmarks [10].
3. **Expectations.** Expect about 1 mm mean error with a heavy tail (std 0.9–1.25 mm) [1][2]. The error concentrates in depth (nose projection, chin, orbits), so budget a correction pass on the profile silhouette and the lips.
4. **Scale.** NoW says nothing about size, because scale is solved during alignment [4].
   - Anchor scale with a measurement: a ruler in frame, head breadth, or iris diameter (adult about 11.7 mm, SD about 0.5 mm 🧠).
   - Sanity-check the adult ranges: bizygomatic breadth 120–150 mm and head length 175–205 mm 🧠.
   - FLAME units are metres, so keep the Blender unit scale at 1.0.
5. **Neutralise.** Fit expression per photo, then zero the expression and jaw on the identity mesh. DECA-style identity absorbs expression. MICA's ArcFace features resist it [4].
6. **Checks.**
   - Use each photo as a camera background under the *solved perspective* camera.
   - Landmark reprojection should be under about 1–2 % of interocular distance.
   - Overlay the profile silhouette.
   - Mirror-compare left and right, because PCA regressors suppress asymmetry.
7. **Typical failures.**
   - Regression to the mean ("everyone looks alike").
   - Flattened depth.
   - Generic ears and cranial vault.
   - Beards hiding the jawline.
   - Wrong eyelid aperture.
   - Worse results on children and under-represented groups, because FLAME and BFM training data is mostly Western adults.
8. **Topology.**
   - FLAME (5,023 vertices) works as a sculpt cage. Add multires and keep the regressor shape as a shape key.
   - BFM outputs are face masks, so warp a full-head template onto them.
   - Keep DECA or HRN detail as a separate displacement layer, and never judge likeness from it [1].
9. **Latency.** Detect once, then track. Detection dominates the per-frame cost [10].

## Algorithmic implications

- **Backend contract.** Each backend returns:
  - topology, coefficients and landmarks;
  - landmark convention (iBUG-68 2D, 3D-consistent, or MediaPipe-478);
  - camera type (weak-perspective, affine or perspective);
  - a metric flag and its licence.

  Ship a default path built only from MIT and Apache parts: MediaPipe plus our own fitter. Research backends are opt-in user installs.
- **Weak-perspective to perspective (derived).** DECA-style projection is x = s·(X + t) in crop coordinates [−1, 1]. For a square crop of side W_b px in the original image and a focal length f px (from EXIF, else a default 50 mm equivalent):
  - initial depth Z₀ = 2f/(s·W_b);
  - lateral offset = (pixel offset of the projected origin) · Z₀/f.

  For 3DDFA_V2, split the 3×4 matrix into scale and rotation with an SVD. 🧠
- **Identity prior.** FLAME shape coefficients are nominally unit-variance 🧠.
  - Take the per-component median β̄ over N photos.
  - Prior: β ~ N(β̄, diag(σ²)), where σ_k is the spread across photos, floored at about 0.3 (MICA) or 0.6 (DECA).
  - Components the regressor does not predict get σ = 1.
  - These are design defaults, not sourced values; tune them on held-out scans.
- **Residual model (derived; the half-normal shape is an assumption).** For half-normal errors, median ≈ 0.674σ, mean ≈ 0.798σ and std ≈ 0.603σ.
  - MICA's 0.90 / 1.11 / 0.92 mm then implies σ ≈ 1.33–1.53 mm.
  - DECA's validation scores imply σ ≈ 1.75–2.07 mm.
  - Both have mean/median ≈ 1.23, against 1.18 for a true half-normal, so the tails are heavy.
  - Use a Huber or Student-t loss with scale ≈ 1.4 mm for MICA initialisation and ≈ 1.8 mm for DECA.
- **Scale prior.** Use a log-scale prior with σ ≈ 0.04–0.05 for MICA (its scale is a statistical guess) and σ ≥ 0.10 for non-metric backends. Tighten it to ≈ 0.01 with a user measurement. These are design defaults. 🧠
- **Contour landmarks.** 2D detectors put jaw points on the silhouette, while 3D-consistent schemes fix them on the mesh. Use sliding correspondences or a silhouette term, or jaw width will be biased with yaw. 🧠
- **Factorisation.**
  - Share identity β and scale across views.
  - Fit expression ψ, jaw and pose per view, and set ψ to 0 at hand-off.
  - Do not initialise from 3DDFA_V2 on frames with |yaw| ≳ 90° [10].
  - Down-weight frames where the backends disagree.
- **Evaluation harness.**
  - NoW-style: 7-landmark alignment, then scan-to-surface median, mean and std [2][4].
  - Run in both similarity and metric (no scale) modes.
  - Add REALY-style per-region errors.
  - Log split, metric and mesh variant [5].

## Disagreements, myths & open questions

- **DECA's two rows.** 1.09 / 1.38 mm is the test split and 1.18 / 1.46 mm is validation (split attribution confirmed by leaderboard [16]; numbers from [1][2][3]). Always cite the split with the number.
- **MICA spread.** Median 0.90–0.94 mm and mean 1.11–1.19 mm across [2][5][6], probably because of different metrics and splits. ↔️
- **Refuted: "MICA's NoW mean is 1.53 mm."** That figure is the scale-optimised average-mesh baseline [4].
- **Myth: "the detailed mesh is more accurate."** Not on NoW [1][3].
- **Myth: "lower NoW means better likeness."** NoW is whole-face, scale-free and neutral-only, and REALY reorders methods. ↔️
- **Myth: "MICA gives true metric size."** Its scale is learned from correlations between appearance and size, so it is a prior, not a measurement. 🧠
- **Myth: "the regressor's fps is the pipeline's fps."** Detection dominates [10].
- **Myth: "generic image-to-3D LRMs beat 3DMMs on faces."** Their meshes are plausible but non-metric and drift in identity. KaoLRM [5] constrains an LRM to FLAME for that reason. ↔️
- **Unverified claims.** "TEASER beats SMIRK" [9], Pixel3DMM's gains and HRN's lead on REALY (🧠).
- **Open questions:** licences (FLAME 2023 Open, SMIRK, HRN, Pixel3DMM, TEASER), measured GPU timings, NoW scores for SMIRK/HRN/Pixel3DMM, exact REALY numbers, and which split the [4] baseline used.

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
15. FLAME model license (FLAME 2023 Open, CC-BY-4.0; other releases non-commercial) — https://flame.is.tue.mpg.de/modellicense.html — official — 2023
16. NoW challenge, non-metrical evaluation leaderboard — https://now.is.tue.mpg.de/nonmetricalevaluation.html — official — 2025
17. Basel Face Model non-commercial license agreement — https://faces.dmi.unibas.ch/bfm/content/basel_face_model/downloads/BFM_NonCommercial_License_Agreement.pdf — official — 2009
18. Towards Metrical Reconstruction of Human Faces (MICA), ECCV 2022 version — https://www.ecva.net/papers/eccv_2022/papers_ECCV/papers/136730249.pdf — paper — 2022
19. Pixel3DMM: Versatile Screen-Space Priors for Single-Image 3D Face Reconstruction — https://arxiv.org/abs/2505.00615 — paper — 2025

**Further reading (by name, not yet linked)**
- Sanyal, Bolkart, Feng, Black — Learning to Regress 3D Face Shape and Expression from an Image without 3D Supervision (RingNet, NoW), CVPR 2019
- Li, Bolkart, Black, Li, Romero — Learning a Model of Facial Shape and Expression from 4D Scans (FLAME), SIGGRAPH Asia 2017
- Paysan et al. — A 3D Face Model for Pose and Illumination Invariant Face Recognition (BFM 2009), AVSS 2009
- Daněček, Black, Bolkart — EMOCA: Emotion Driven Monocular Face Capture and Animation, CVPR 2022
- Deng et al. — Accurate 3D Face Reconstruction with Weakly-Supervised Learning: From Single Image to Image Set, CVPR Workshops 2019
- Chai et al. — REALY: Rethinking the Evaluation of 3D Face Reconstruction, ECCV 2022
- Lei et al. — A Hierarchical Representation Network for Accurate and Detailed Face Reconstruction from In-The-Wild Images (HRN), CVPR 2023
- Giebenhain et al. — Pixel3DMM: Versatile Screen-Space Priors for Single-Image 3D Face Reconstruction, 2025
- Kartynnik et al. — Real-time Facial Surface Geometry from Monocular Video on Mobile GPUs (MediaPipe Face Mesh), CVPR Workshops 2019
- Egger et al. — 3D Morphable Face Models: Past, Present, and Future, ACM TOG 2020

## Verification log (2026-11-20)

- **FLAME licence** (FLAME 2023 Open is CC-BY-4.0; older releases non-commercial): confirmed, 📄. https://flame.is.tue.mpg.de/modellicense.html . Extra: textures are BY-NC-SA 4.0. The DECA/EMOCA/MICA code licences were not confirmed (🧠).
- **NoW test-split scores**: DECA 1.09/1.38/1.18, MICA 0.90/1.11/0.92 and TokenFace 0.76/0.95/0.82 confirmed (DECA and MICA now ✅ with the papers). https://now.is.tue.mpg.de/nonmetricalevaluation.html . 3DDFA_V2 and Deep3DFaceRecon non-metrical rows: unconfirmed (the page says those results are taken from DECA; the search showed only metrical values: 3DDFA_V2 1.53/2.06/1.95, Deep3DFaceRecon PyTorch 1.62/2.21/2.08). The 80 test / 20 validation split: unconfirmed.
- **3DDFA_V2 / Deep3DFaceRecon_pytorch MIT code; MediaPipe Apache-2.0**: unconfirmed (only third-party listings). BFM non-commercial terms confirmed, 📄: https://faces.dmi.unibas.ch/bfm/content/basel_face_model/downloads/BFM_NonCommercial_License_Agreement.pdf
- **MICA 15 % / 24 % lower error**: confirmed (already 📄), https://www.ecva.net/papers/eccv_2022/papers_ECCV/papers/136730249.pdf . 300 coefficients in metres, and the 1.92 / 1.53 mm baseline values and protocol: unconfirmed in this pass (existing [4] citation kept).

## Verification log, pass 2 (2026-11-20)

- **Pixel3DMM more than 15% better on posed expressions**: unconfirmed (🧠 kept). The search surfaced no figure. https://arxiv.org/abs/2505.00615 . New fact added, 📄: on NoW it matches FlowFace and is worse than TokenFace. The paper says code, model and benchmark are planned for release; licence terms not found (unconfirmed).
- **HRN led REALY, region-averaged frontal error about 1.5-1.6 mm vs about 2 mm for DECA**: unconfirmed (🧠 kept). No per-region numbers found. One REALY source describes the metric as normalised mean square error, so the mm units in Table 5 may be wrong; check the REALY paper (https://arxiv.org/pdf/2203.09729) before relying on them.
- **TEASER beats SMIRK**: unconfirmed in this pass (no results).
- **SMIRK, HRN, Pixel3DMM and TEASER licences**: unconfirmed (no results).
