# Single-image 3D face reconstruction methods

> Single-image regressors (DECA, MICA, SMIRK, 3DDFA_V2 and successors) turn one photo into parametric face-model coefficients, mostly FLAME. They are only accurate to about 1 mm median and 1.1-1.5 mm mean surface error on the NoW benchmark. By that measure the 2022 MICA identity regressor is about 25% better than DECA (2021). In the MICA paper, the plain *average* FLAME face with only its scale fitted scores 1.53 mm mean. Learned regressors beat that baseline by only about 0.1 mm (DECA validation) to 0.4 mm (MICA), although the papers may not use the same splits. Treat these networks as initialisers and priors for a landmark/photo fitting stage, not as finished likenesses. NoW does not measure fine detail: DECA's detail layer leaves NoW error unchanged. Coverage caveat: this note uses only one harvester pass. Independent re-verification searches were blocked because the shared search budget for this turn was used up. EMOCA, Deep3DFaceRecon, HRN, Pixel3DMM, REALY numbers and **all licences** are unconfirmed (see Open questions).

## Key facts

- **NoW protocol.** The prediction is rigidly aligned to the ground-truth scan using 7 landmarks. Per-vertex distance error is then reported in mm as median, mean and std over all subjects [2][4]. ✅ (two harvested papers agree; not re-checked against the official NoW page)
- **Error metrics differ between papers.** Some report Chamfer-style distance instead of NoW per-vertex error, so cross-paper tables are not strictly comparable [5]. ⚠️
- **DECA, NoW validation set.** Coarse mesh: median 1.18 / mean 1.46 / std 1.25 mm. Detailed mesh: 1.19 / 1.47 / 1.25 mm [1]. Later papers repeat these figures: [2] gives 1.178 / 1.464 mm (coarse) and [3] gives 1.19 / 1.47 mm. ✅
- **DECA's detail layer does not improve NoW.** Coarse to detailed goes from 1.18 to 1.19 mm median (derived from [1][3]). Wrinkle and detail fidelity therefore needs a different metric. ✅
- **A second DECA row.** One DECA table row reads median 1.09 / mean 1.38 / std 1.18 mm [1]. It is unclear which split or protocol it refers to. One likely explanation is the NoW *test* split versus *validation*, but that is **not confirmed**. ↔️
- **MICA (MetrIC fAce)** predicts a *metrical*, neutral-expression FLAME shape from one RGB image. It uses identity features from a face-recognition network and is trained with supervision [4]. ⚠️
- **MICA NoW error is reported anywhere from median 0.90-0.94 to mean 1.11-1.19 mm**, depending on the paper and protocol:
  - [2] lists two MICA rows: 0.913 / 1.130 / 0.948 mm and 0.90 / 1.11 / 0.92 mm (median / mean / std).
  - [6] reports median 0.9432 and mean 1.1606 in a profile-view evaluation.
  - [5] reports about 0.96-1.00 mm per challenge and about 1.19 mm overall, Chamfer-style.

  ↔️
- **MICA's own claim:** 15% lower average error than prior methods on NoW and 24% lower on its metric benchmarks [4]. ⚠️
- **Baseline: the average FLAME mesh.** Mean NoW error is 1.92 mm as-is and **1.53 mm after scale optimisation** [4]. Scale alone accounts for about 20% of the mean-face error. ⚠️
- **"Towards Realistic Generative 3D Face Models"** reports 23% (coarse) and 20% (detailed) better median error than DECA [2]. ⚠️
- **SMIRK** (CVPR 2024) replaces the differentiable rasteriser with a neural renderer. The renderer takes the predicted FLAME geometry plus sparse pixels sampled from the input image, so the photometric loss trains the expression geometry [7]. Official PyTorch code: github.com/georgeretsi/smirk [8]. ✅ (paper and repo agree)
- **SMIRK training data** mixes in-the-wild faces (FFHQ, CelebA), emotional expressions (MEAD) and speech mouth shapes (LRS3) [7]. ⚠️
- **SMIRK repo snapshot:** about 396 stars, last update 31 May 2024 [8]. This is a stale listing snapshot. ⚠️
- **TEASER (2025)** is described in a search summary as more expression-accurate than SMIRK on several benchmarks [9]. Its tables were not read. ⚠️ (unverified)
- **3DDFA_V2** (ECCV 2020) is an official PyTorch implementation [10][11]. ✅ It uses FaceBoxes instead of Dlib for detection and claims over 50 fps on CPU or GPU [10][11]. ⚠️ (author claim, hardware unspecified)
- **3DDFA_V2 limits.** Face detection dominates latency, at about 15 ms for a 720p frame even with ONNX. Alignment can fail beyond about 90° head pose or with very fast motion [10]. ⚠️
- **Dense-Head-Pose-Estimation** is a community TensorFlow Lite reimplementation of 3DDFA_V2 that adds head pose and a mesh preview. It is claimed to run in real time on CPU [12]. ⚠️ (community claim)

## Numbers & reference tables

**Table 1: NoW benchmark errors (mm, scan-to-prediction distance after landmark-based rigid alignment).** Sample: NoW subjects and images. The split sizes were not in the harvested snippets.

| Method / variant | Split as reported | Median | Mean | Std | Source | Status |
|---|---|---|---|---|---|---|
| Average FLAME mesh, no scale fit | not stated | – | 1.92 | – | [4] | ⚠️ |
| Average FLAME mesh, scale optimised | not stated | – | 1.53 | – | [4] | ⚠️ |
| DECA coarse | validation | 1.18 (1.178) | 1.46 (1.464) | 1.25 | [1][2] | ✅ |
| DECA detailed | validation | 1.19 | 1.47 | 1.25 | [1][3] | ✅ |
| DECA (summary row) | unconfirmed (test?) | 1.09 | 1.38 | 1.18 | [1] | ↔️ |
| MICA (row A) | not stated | 0.913 | 1.130 | 0.948 | [2] | ↔️ |
| MICA (row B) | not stated | 0.90 | 1.11 | 0.92 | [2] | ↔️ |
| MICA, profile-view evaluation | profile subset | 0.9432 | 1.1606 | – | [6] | ⚠️ |
| MICA, Chamfer-style | validation | – | ≈1.19 overall (≈0.96-1.00 per challenge) | – | [5] | ⚠️ |

**Table 2: Relative improvement claims (reported by the authors).**

| Claim | Value | Baseline | Source | Status |
|---|---|---|---|---|
| MICA vs prior SOTA, NoW average error | −15% | prior methods | [4] | ⚠️ |
| MICA vs prior SOTA, metric benchmarks | −24% | prior methods | [4] | ⚠️ |
| [2] vs DECA, median (coarse / detailed) | −23% / −20% | DECA | [2] | ⚠️ |
| Effect of scale fitting on the mean FLAME face | 1.92 → 1.53 mm (−20%) | mean mesh | [4] | ⚠️ |

**Table 3: Runtime and robustness.**

| Tool | Figure | Condition | Source | Status |
|---|---|---|---|---|
| 3DDFA_V2 | > 50 fps | "single CPU or GPU", hardware unspecified | [10][11] | ⚠️ |
| 3DDFA_V2 face detection | ≈ 15 ms | 720p image, ONNX | [10] | ⚠️ |
| 3DDFA_V2 | fails at about > 90° pose or fast motion | video tracking | [10] | ⚠️ |
| DECA / MICA / SMIRK | no GPU timings found | – | – | gap |

**Table 4: What each method outputs and what is still unknown.**

| Method | Output useful in Blender | Code | Licence |
|---|---|---|---|
| DECA [1] | coarse parametric mesh plus a detailed (displacement) mesh. FLAME basis assumed, not confirmed in snippets | repo not harvested | **unconfirmed** |
| MICA [4] | neutral-expression **metric-scale** FLAME identity shape | repo not harvested | **unconfirmed** |
| SMIRK [7][8] | FLAME geometry with an expression focus | github.com/georgeretsi/smirk | **unconfirmed** |
| 3DDFA_V2 [10][11] | dense 3DMM alignment, head pose, landmarks; fast | github.com/cleardusk/3DDFA_V2 | **unconfirmed** |
| TEASER [9] | expression reconstruction | not harvested | **unconfirmed** |
| EMOCA, Deep3DFaceRecon, HRN, Pixel3DMM | not searched in this run | – | – |

## Applying this to photo→3D face sculpting in Blender

1. **Choose the regressor for the job.** Use MICA-class metric identity regression for the neutral base head [4]. Use expression-focused regressors such as SMIRK or TEASER only to *estimate and then remove* expression from the photo [7][9]. Use 3DDFA_V2 for fast pose and landmarks, or for video frame selection [10]. Do not take identity shape from an expression regressor without checking it.
2. **Set expectations in mm.** A good single-image result still has about 0.9 mm median and 1.1 mm mean error, with a long tail (std about 0.9-1.25 mm) [1][2]. Plan a sculpt-correction pass. The base mesh is only roughly 0.4 mm better than a correctly scaled average face (Table 1).
3. **Fix scale explicitly.** NoW figures come after rigid alignment, and scale alone moves the mean-face error from 1.92 to 1.53 mm [4]. A NoW score therefore tells you little about absolute head size. If the method is not metric, or the user cannot supply a known measurement, expose scale as a visible parameter in the add-on and show its uncertainty.
4. **Neutralise before sculpting.** Expressive photos bias the identity shape. Fit expression coefficients first, zero them, then sculpt on the neutral identity. MICA predicts neutral shape directly [4].
5. **Check pose before trusting a frame.** Flag photos near or above 90° yaw for 3DDFA_V2-based initialisation [10]. Handle true profiles with a profile-specific model or a multi-view fit. Note that MICA's profile-view errors (0.94 / 1.16 mm) were similar to its frontal-class numbers [6].
6. **Don't judge likeness from the detail layer.** DECA's wrinkle detail changes NoW error by 0.01 mm [1]. Assess likeness from coarse proportions, using a silhouette overlay and landmark reprojection against the photo set as camera background. Treat detail as a separate displacement or multires layer.
7. **Plan the latency budget.** For live preview, detection rather than the 3DMM regression is the bottleneck, at about 15 ms per 720p frame [10]. Detect once, then track.

## Algorithmic implications

- **Use the regressor as a prior.** Initialise FLAME identity β from the regressor and penalise movement away from it with ‖β − β_reg‖²_Σ. Give the photo landmarks and silhouette terms enough weight to override it, because the regressor sits within about 0.1-0.4 mm of the scaled mean face on NoW (Table 1).
- **Residual noise model (derived here, not reported by any source).** Suppose NoW errors were unsigned normal-direction errors drawn from a half-normal distribution. Then median ≈ 0.674σ, mean ≈ 0.798σ and std ≈ 0.603σ. Under that assumption, MICA's 0.90 / 1.11 / 0.92 mm gives σ ≈ 1.33 / 1.39 / 1.53 mm, and DECA validation gives σ ≈ 1.75 / 1.83 / 2.07 mm.
  - The std-implied σ is the largest, and both methods have mean/median ≈ 1.23 against 1.18 for a half-normal. So the tails are heavier than Gaussian.
  - Default to a robust (Huber or Student-t) vertex residual with scale ≈ 1.4 mm for MICA-class initialisation and ≈ 1.8 mm for DECA-class initialisation.
- **Scale as a separate unknown.** Model global scale s with its own prior. Make it tight only when a metric method or a user measurement supplies it [4].
- **Separate the factors:** identity (neutral), expression, pose, camera and detail. Lock expression to zero at sculpt hand-off.
- **Built-in evaluation harness.** Reproduce the NoW-style metric: 7-landmark rigid alignment, then per-vertex distance with median, mean and std [2][4]. Always log split, alignment type (rigid or similarity), metric (scan-to-mesh or Chamfer [5]) and mesh variant (coarse or detailed). Never rank methods across mismatched protocols.
- **Gating rules:** reject or down-weight frames with |yaw| ≳ 90° for 3DDFA_V2 [10]. Prefer the frames where the regressors agree most.
- **Swappable backends.** Expose DECA, MICA, SMIRK and 3DDFA_V2 behind one interface that returns FLAME or 3DMM coefficients, camera and landmarks. Keep a licence field per backend, which is currently unknown (see Open questions).

## Disagreements, myths & refuted claims

- **DECA has two sets of numbers:** 1.09 / 1.38 / 1.18 mm and 1.18 / 1.46 / 1.25 mm, both in [1]. The second set is backed by two independent papers [2][3] and labelled as validation. Cite *split* together with the number. Contested range: median 1.09-1.19, mean 1.38-1.47 mm.
- **MICA's reported numbers range** from median 0.90 to 0.94 mm and mean 1.11 to 1.19 mm across [2][5][6]. Chamfer versus per-vertex metrics and split choice are plausible causes, but this is unconfirmed.
- **Refuted: "MICA's NoW mean error is 1.53 mm."** The harvester's contradiction note misread [4]. The 1.53 mm figure is the scale-optimised *average FLAME mesh* baseline, not MICA. MICA's own numbers sit at about 1.11-1.19 mm mean.
- **Myth: "the detailed mesh is more accurate."** On NoW it is not (1.18 vs 1.19 mm median) [1][3].
- **Myth: "a regressor's fps equals pipeline fps."** For 3DDFA_V2, detection is the main cost [10].
- **"TEASER beats SMIRK"** is unverified. It comes from a search summary, not from the paper's tables [9].

## Open questions

- **Licences.** Not confirmed for any method: DECA, EMOCA, MICA, SMIRK, 3DDFA_V2, Deep3DFaceRecon, HRN, Pixel3DMM or TEASER. The licences of the underlying model assets (FLAME, BFM) are also unconfirmed. Check every repository's LICENSE file and every model-asset licence before shipping an add-on.
- **Methods not searched in this run:** EMOCA, Deep3DFaceRecon, HRN, Pixel3DMM. We have no NoW, REALY, speed or code facts for them. SEREP [13] and KaoLRM [5] (2026) are newer regressors whose own accuracy was not extracted.
- **REALY.** We do not yet have the metric definition, the region-wise errors, or published REALY numbers for any method above.
- **DECA split.** Which split is the 1.09 / 1.38 row? Do NoW validation and test differ systematically?
- **Speed.** No DECA, MICA or SMIRK per-image timings on a named GPU.
- **Split size.** NoW split sizes and image counts, and whether the [4] average-mesh baseline uses the same split as Table 1.
- **Next step.** A follow-up run with search budget should first re-verify Tables 1-3 against independent sources (the NoW leaderboard page and the GitHub repos).

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
