# Monocular depth and surface normals for faces

> General-purpose monocular depth models (Depth Anything V2/3, Marigold) and normal estimators (DSINE, Marigold-Normals, Lotus, StableNormal) are trained and benchmarked on scenes. This library holds no face-region accuracy figure for any of them, nor for the human-specific Sapiens and DAViD. Single-image depth is ambiguous in relief scale (affine-invariant outputs, bas-relief ambiguity), so it must never set nose projection or head depth; those come from the landmark/3DMM camera fit. Predicted **normals** are the useful signal: they carry mid-frequency form (nasolabial folds, lid creases, lip and chin contours) that can be added to the fitted base as a clamped, landmark-anchored displacement solved in mesh space. Run predictors out of process and cache 16-bit or float outputs, because CPU/ONNX support and weight licences differ per model and several popular weights are non-commercial.
Evidence status: 1 ✅ / 26 📄 / 48 🧠 / 4 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Depth Anything V2 and 3**
- DA V2 is a *relative* depth model: it orders surfaces near to far but recovers no metric distance [1][2] 📄 ([2] mirrors [1]). Its relative checkpoints output MiDaS-style affine-invariant **inverse depth (disparity)**, not depth, so scale/shift must be fitted in disparity space (Table 4) 🧠.
- DA V2 Small: ~25M parameters, 60 ms/image (hardware unstated), DA-2K accuracy 95.3% [1][2] 📄. Ablation: 89.8% with labelled synthetic data only, 95.3% with pseudo-labelled real data only [1] 📄.
- DA V2 ViT-L on NYU-D: δ1 0.984, AbsRel 0.056 [1] 📄. This is very likely the in-domain metric fine-tuned setting, not zero-shot 🧠.
- Sizes and licences: Small (~25M) Apache-2.0; Base (~98M), Large (~335M) and Giant (~1.3B) CC BY-NC 4.0 🧠. The teacher was trained on ~595K synthetic images and the students on ~62M pseudo-labelled real images; default input is 518 px (a multiple of the ViT patch size 14) 🧠.
- Real-world metric quality is disputed: best monocular method in a driving obstacle study [3], significantly worse metric accuracy than LiDAR in robotics [4], metre-level errors in low-overlap drone photogrammetry (MiDaS v3.1 worse) [5] ↔️. No face evaluation was found [2] 📄.
- Depth Anything 3 is arXiv 2511.10647, submitted November 2025 [19][21] ✅ (exact day 14 Nov from the wrapper only 📄). It takes one or many views and predicts depth plus camera rays [19] 📄; the family includes Small/Base/Large/Giant plus Metric and Mono variants 🧠.
- `DA3Metric-Large`: metric depth = focal × net output / 300, focal = mean(fx, fy) in px [20] 📄. Depth is linear in the focal you pass. Which pixel grid the focal must refer to (original photo or the network's processing resolution) was not confirmed 🧠.
- DA3-metric: best SUN-RGBD AbsRel 0.105, second on DIODE [19] 📄; DA3Metric-Large ~350M parameters [21] 📄; a TensorRT ROS2 node exists, no CPU/ONNX latency found [22] 📄.

**Diffusion depth/normals**
- Marigold (Ke et al., CVPR 2024) repurposes Stable Diffusion as an **affine-invariant** depth estimator [6] 📄. It was fine-tuned from Stable Diffusion 2 on ~74K synthetic samples (Hypersim, Virtual KITTI), predicts depth (not disparity), defaults to ~768 px processing, and is in Hugging Face diffusers (depth and normals pipelines); later checkpoints need only 1–4 denoising steps 🧠.
- The extended paper adds **Marigold-Normals** with the same protocol [7] 📄, plus intrinsic decomposition (albedo/shading) that can help separate makeup and pigment from shading 🧠.
- Marigold V2 (arXiv 2609.08084) uses a diffusion-transformer backbone (reportedly Qwen-Image-Edit) and claims state-of-the-art normals; its repo trains normals with an angular loss [8][9] 📄 (authors' own claim).
- StableNormal targets diffusion sample variance [14] 📄; Lotus is diffusion-based dense prediction with a normal benchmark table [13] 📄 and runs in a single step 🧠. GeoWizard predicts depth and normals jointly 🧠.

**DSINE and uncertainty-aware normals**
- DSINE encodes per-pixel ray direction and learns relative rotations between neighbouring normals; code is public [10][11] 📄. Because it consumes rays, feed it the solved, crop-adjusted intrinsics 🧠.
- DSINE mean angular error on NYUv2 ≈ **16.4°**, cited by two later papers [12][13] ✅. Trained on ~160K images versus >12M for Omnidata-V2 (attribution unclear) [10] 📄.
- Bae et al.'s ICCV 2021 normal estimator outputs per-pixel aleatoric uncertainty, directly usable as fitting weights 🧠.

**Metric/geometry foundation models (not in the harvest)**
- Apple Depth Pro: metric depth plus a focal-length estimate from one image, sharp boundaries, ~2.25 MP in ~0.3 s on a V100 (abstract) 🧠. Microsoft MoGe/MoGe-2: point maps with recovered focal (MoGe-2 metric; some variants output normals) 🧠. Metric3D v2 (metric depth and normals, canonical-camera transform) and UniDepth (predicted intrinsics) are the other options 🧠. Their focal estimates are fallbacks when EXIF is missing; a landmark-based solve is stronger 🧠.

**Human- and face-specific**
- Sapiens (Meta): pose, body-part segmentation, depth and normals; pretrained on >300M human images [17] 📄; depth/normal supervision from 600 RenderPeople scans [17] 📄; reports −22.4% relative RMSE on Hi4D and −53.5% relative angular error on THuman2 versus prior work [17] 📄. Sizes 0.3B/0.6B/1B/2B at 1024×768 native input; the 28-class segmentation includes hair, upper/lower lip, teeth and eyeglasses; the pose model has 308 keypoints, most on the face 🧠.
- DAViD trains human depth, normal and segmentation models on synthetic data [18] 📄; reportedly ~300K synthetic images, compact models, ONNX released 🧠.
- Face-normal papers: cross-modal face normals (2020) [16] 📄 and exemplar-based refinement (2026) [15] 📄. Earlier: Trigeorgis et al. 2017 (FCN face normals), SfSNet 2018 (normals, albedo and spherical-harmonic (SH) light), Unsup3d 2020 🧠. Reported face-normal errors on photometric-stereo face sets (e.g. Photoface) roughly span 10–20° mean ↔️ (from memory, ranges only).

**Physics that limits all of them**
- **Bas-relief ambiguity** (Belhumeur, Kriegman & Yuille 1999): under unknown light and albedo a Lambertian image cannot distinguish z from λz + μx + νy. Relief depth and tilt are therefore the least reliable outputs 🧠.
- Nine SH coefficients represent Lambertian irradiance with roughly 1–2% error (Ramamoorthi & Hanrahan 2001; Basri & Jacobs 2003) 🧠.
- Skin scatters light below the surface. Red scatters farthest, so green/blue carry sharper relief; highlights fake bumps; cross-polarised capture removes surface specular (Ma et al. 2007) 🧠.

## Numbers & reference tables

**Table 1: Reported benchmarks (scene or full-body data; none on faces)**

| Model | Output | Params | Benchmark | Value | Src | Status |
|---|---|---|---|---|---|---|
| DA V2 Small | relative disparity | ~25M | DA-2K accuracy; latency | 95.3%; 60 ms (hw unstated) | [1][2] | 📄 |
| DA V2 ablation | relative | — | DA-2K synthetic-only / pseudo-real-only | 89.8% / 95.3% | [1] | 📄 |
| DA V2 ViT-L | metric (fine-tuned, likely) | ~335M 🧠 | NYU-D δ1 / AbsRel | 0.984 / 0.056 | [1] | 📄 |
| DA3Metric-Large | metric depth | ~350M | SUN-RGBD AbsRel | 0.105 (best); DIODE 2nd | [19][21] | 📄 |
| DSINE | normals | — | NYUv2 mean angular error | ≈16.4° | [12][13] | ✅ |
| DSINE vs Omnidata-V2 | normals | — | training images | ~160K vs >12M | [10] | 📄 |
| Sapiens | depth / normals | 0.3–2B 🧠 | Hi4D RMSE / THuman2 angular error, relative | −22.4% / −53.5% | [17] | 📄 |

**Table 2: Runtime, inputs and licences (verify all before shipping)**

| Model | Native input | Export / runtime path | CPU cost (order of magnitude, estimate) | Licence | Status |
|---|---|---|---|---|---|
| DA V2 Small | 518 px | HF transformers; community ONNX | ~0.2–1 s | Apache-2.0 | 🧠 |
| DA V2 Base/Large | 518 px | community ONNX | Large ~2–8 s | CC BY-NC 4.0 | 🧠 |
| DA3 family | ~500 px | PyTorch; TensorRT node [22] | Large: seconds | per-model, unverified | 🧠 |
| Marigold v1.x | ~768 px | diffusers | tens of s to minutes (steps × ensemble) | code Apache-2.0; weights unverified | 🧠 |
| DSINE | any (needs K) | PyTorch | a few s | unverified | 🧠 |
| Sapiens normal/depth | 1024×768 | TorchScript "lite" | 0.3B: ~5–30 s; 2B: minutes | custom Meta licence, unverified | 🧠 |
| DAViD | — | ONNX (reported) | sub-second to seconds | unverified | 🧠 |
| Depth Pro | ~1.5K px | PyTorch | many seconds | Apple custom, unverified | 🧠 |

**Table 3: DA3 metric conversion [20]**

| Quantity | Formula | Consequence | Status |
|---|---|---|---|
| Metric depth | Z = f·y/300, f = (fx+fy)/2 px | 10% focal error → 10% error in distance **and** relief | 📄 (consequence derived) |
| Engine focal | f = `Camera.f` (square pixels) | crop: shift cx, cy; resize: scale f | 🧠 |

**Table 4: Distance-dependent errors (derived; assumes 100 mm visible facial relief and a feature 70 mm off-axis)**

| Camera distance (mm) | Max error if disparity is fitted as depth (mm) | RMS (mm) | Ray obliquity at 70 mm (°) | Status |
|---|---|---|---|---|
| 300 (selfie) | 4.9 | 2.1 | 13.1 | 🧠 |
| 450 | 3.4 | 1.5 | 8.8 | 🧠 |
| 600 | 2.6 | 1.2 | 6.7 | 🧠 |
| 1000 | 1.6 | 0.7 | 4.0 | 🧠 |
| 1500 | 1.1 | 0.5 | 2.7 | 🧠 |

Ray obliquity is the normal-direction error you get from integrating under an orthographic assumption.

**Table 5: Face pixel footprint (derived; bizygomatic width 130–140 mm)**

| Network input | Face share of width | mm/px | Smallest resolvable feature (~2 px) | Status |
|---|---|---|---|---|
| 518 px | 60% (tight crop) | 0.42–0.45 | ~0.9 mm: lid crease, lip line | 🧠 |
| 768 px | 60% | 0.28–0.30 | ~0.6 mm | 🧠 |
| 1024 px | 60% | 0.21–0.23 | ~0.45 mm: coarse wrinkles | 🧠 |
| 518 px | 15% (uncropped half-body) | 1.7–1.8 | ~3.5 mm: folds only | 🧠 |

Pores (~0.05–0.25 mm) are below all of these 🧠.

**Table 6: Mean angular error → von Mises–Fisher concentration, κ = π/(2m²), m in rad (derived; sampling check gives mean 16.5° at κ = 19.2)**

| Mean angular error m | 10° | 15° | 16.4° | 20° | 25° | 30° |
|---|---|---|---|---|---|---|
| κ | 51.6 | 22.9 | 19.2 | 12.9 | 8.3 | 5.7 |

## Applying this to photo→3D face sculpting in Blender

1. **Never use a depth map as the base shape.** Fit the head from landmarks and a morphable model across views first. Relative and affine-invariant depth have no scale or offset [2][6], and DA3 metric scales with the focal you pass [20]; a displaced plane gives arbitrary nose projection.
2. **Capture for shading cues** 🧠: neutral expression, hair off the forehead and ears, no glasses, no contour makeup (contouring is painted fake normals). Use a large soft key 30–45° off-axis, no on-camera flash or hard noon sun, and shoot from ≥1 m at a moderate telephoto. Cross-polarise if you can.
3. **Crop before predicting.** Crop the face to fill ~60% of the network input (Table 5). For DSINE and DA3 metric, pass crop-adjusted intrinsics (cx − x0, cy − y0, f × resize factor). Save outputs as float EXR, NPY or 16-bit PNG: 8-bit depth has only 256 levels across the face and integrates into terraces.
4. **Verify the axis convention once per model** on a synthetic render (`face3d/synthetic.py`). In the engine's OpenCV frame, a frontal forehead must read ≈(0, 0, −1), the image-left cheek nx < 0, and the under-chin and subnasale ny > 0 (y points down). Store the adapter per model and version.
5. **Mask hard.** Use only skin: drop hair, brows, beard, eyes/cornea, lips' vermilion edge band, teeth, nostrils, glasses, blown highlights (V > 0.95), and grazing pixels (base normal more than ~70° from the view ray). Sapiens segmentation [17] or a CelebAMask-HQ face parser works; erode masks by 3–5 px.
6. **Inspect residuals before trusting anything.** Render base-mesh normals and depth through the solved camera and display the angular difference. Residual shaped like the light (a shadow beside the nose, a forehead highlight) or like pigment (brows, freckles, beard shadow) is not geometry. A smooth global tilt is a predictor bias: remove it (algorithm below).
7. **Apply detail as a separate, reversible layer.** Write the result as a shape key ("detail_normals", slider 0–1) on a subdivided copy of the fitted mesh, or push it into Multires via *Reshape* from a same-topology object. Keep it off the base topology.
8. **Check it in Blender.** View through the solved camera with the photo as background at ~50% opacity and compare the silhouette. Judge relief with a MatCap and a raking Studio light. Load normal maps in an Image Texture with colour space *Non-Color*, projected with a UV Project modifier from the solved camera. Measure nose-tip-to-alar-crease depth before and after: a change of more than ~1 mm means the detail pass is altering proportions. Reject it, or lower the clamp.
9. **Diffusion predictors:** run 5+ seeds and keep the per-pixel spread as an uncertainty map [14].
10. **Typical failures:**
    - cast shadows and makeup read as shape;
    - selfie-distance perspective integrated orthographically (Table 4);
    - smearing across lip, nostril and eyelid discontinuities;
    - expression wrinkles baked into a neutral head;
    - eyes rendered as bulges or pits (model eyeballs as spheres instead);
    - scene-trained models under-resolving facial relief (untested here).

## Algorithmic implications

- **Observation registry.** Record each prediction as one of:
  - `relative_disparity` (DA V2 relative, MiDaS);
  - `affine_depth` (Marigold);
  - `metric_depth_focal` (DA3 metric, needs f);
  - `normal_cam`.

  Store with each the axis adapter, model, version, input crop/resize, and licence, set to `unknown` until verified.
- **Depth residual in native space.** For disparity models, fit 1/z_p(V) ≈ s·d̂_p + t by weighted least squares over the mask, closed form each iteration. Require s·d̂ + t > 0. The residual is r_p = z_p(V) − 1/(s·d̂_p + t). Fitting disparity as depth costs up to 1–5 mm of bowl-shaped bias (Table 4).
- **Normal residual.** Use the von Mises–Fisher negative log-likelihood κ_p(1 − n̂_p·n_p(V)) with κ from Table 6 and a robust loss (errors are heavy-tailed). Per-pixel errors are spatially correlated, so subsample at a stride of ~8 px at network resolution (or divide the weight by the correlation area). Otherwise 10⁵ pixels swamp 68–100 landmarks.
- **Rotation-bias correction.** Before using normals, solve one rotation R_b aligning predicted to base normals in the mask (weighted Kabsch: SVD of Σ w n̂ n₀ᵀ). Apply it only if it is ≤10°; a larger value flags a convention or intrinsics error.
- **Mesh-space detail solve (recommended), after Nehab et al. 2005.** Subdivide the fitted face to an edge length of ≤1 mm (FLAME's 5,023 vertices are a few mm apart). Give each visible vertex a target normal: the multi-view average of R⁻¹n̂ from each camera, weighted by κ·cos(view angle) and dropped beyond 70°. Unknowns are offsets δ_i along base normals m_i. For each edge, n̂_ij·((x_j + δ_j m_j) − (x_i + δ_i m_i)) = 0 is linear in δ. Minimise Σ w (·)² + λ_L‖Lδ‖² + λ_0‖δ‖² with δ = 0 at landmark vertices. The system is symmetric positive definite: use `cotan_laplacian` plus `face3d.mesh.sparse.cg`. Re-render and repeat 2–3 times.
- **Image-space alternative.** Under perspective, with ũ = u − cx, ṽ = v − cy, the log-depth gradients are ∂log z/∂u = −nx/(ũ·nx + ṽ·ny + f·nz) and likewise for v. Integrate with discontinuity-aware solvers (bilateral normal integration), then high-pass against the rendered base depth 🧠.
- **Suggested defaults** (all 🧠, unsourced starting points to tune on synthetic and scanned heads):

| Parameter | Default | Range |
|---|---|---|
| Normal mean-error assumption, generic scene model | 20° (κ ≈ 13) | 15–30° |
| Same, human-specific model (Sapiens, DAViD) | 15° (κ ≈ 23) | 10–25° |
| Depth σ after (s, t) | 6 mm, Huber δ = 1.5σ | 3–10 mm |
| Detail high-pass (geodesic Gaussian σ) | 6 mm | 4–10 mm |
| Displacement clamp | ±2.5 mm | 1–4 mm |
| Grazing cutoff | 70° | 60–75° |
| Diffusion seeds; reject pixel if spread exceeds | 5; 10° | 3–10; 6–15° |
| Rotation-bias cap | 10° | 5–15° |

- **Runtime.** Run predictors out of process with ONNX Runtime (CPU EP) where exports exist, else PyTorch. Cache by image hash + model + version. Never bundle non-commercial weights; gate them behind a licence prompt. The add-on itself needs only numpy, plus `mathutils` BVHTree ray casts for pixel-to-face correspondence 🧠.
- **Benchmark harness.** On synthetic heads and real scans (e.g. FaceScape-type data), report angular error by region (forehead, cheek, nose, periorbital, perioral) per model and lighting condition. This fills the main gap.

## Disagreements, myths & open questions

- **DA V2 metric quality** ↔️: best [3] vs clearly worse than LiDAR [4] vs metre-level errors [5]. None of these is a face scenario.
- **95.3% attribution:** snippets attach it to both "Small" and "pseudo-real only". These are consistent if the ablation used the Small student; not confirmed [1][2].
- **DSINE 160K vs 12M** comes from a snippet with unclear attribution [10]. The **"Sapiens fine-tuned on 500K synthetic images"** claim was harvested but linked only to [17]; it is excluded as unsourced.
- **Myth: "a photo plus a depth model gives the true head."** Affine invariance [2][6], focal-scaled metric output [20] and the bas-relief ambiguity rule this out. Absolute projection needs profile or multi-view constraints.
- **Myth: "learned normals are lighting- and albedo-invariant."** They are learned from shading and still leak shadows, makeup and pigment 🧠.
- **Myth: "the newest model is best on faces."** The Marigold V2 [8] and Sapiens [17] claims come from the authors' own non-face benchmarks.
- **Depth vs normals for detail:** clothed-human reconstruction (PIFuHD, ICON, ECON) converged on normals for detail and a parametric body for gross shape 🧠. The same split is recommended here, untested on faces.
- **Refuted in earlier passes:** none.
- **Open:** face-region errors for every model above; whether DA3's metric focal refers to the original or the processed resolution, and its output unit; DA3 multi-view on 2–5 portraits versus landmark bundle adjustment; whether [15][16] release weights; whether Sapiens normals resolve eyelid creases; all licences; CPU latencies (Table 2 is estimates).

## Sources

[1] Depth Anything V2 (arXiv 2406.09414) — https://arxiv.org/abs/2406.09414 — paper — 2024
[2] Depth Anything V2 (alphaXiv mirror of 2406.09414) — https://www.alphaxiv.org/abs/2406.09414 — paper mirror — 2024
[3] Vision-based Perception for Autonomous Vehicles in Obstacle Avoidance Scenarios — https://arxiv.org/pdf/2507.12449 — paper — 2025
[4] Assessing Depth Anything V2 monocular depth estimation as a LiDAR alternative in robotics — https://www.researchgate.net/publication/397955860_Assessing_Depth_Anything_V2_monocular_depth_estimation_as_a_LiDAR_alternative_in_robotics — paper — 2025
[5] A Novel Solution for Drone Photogrammetry with Low-overlap Aerial Images using Monocular Depth Estimation — https://arxiv.org/pdf/2503.04513 — paper — 2025
[6] Repurposing Diffusion-Based Image Generators for Monocular Depth Estimation (Marigold, CVPR 2024) — https://openaccess.thecvf.com/content/CVPR2024/papers/Ke_Repurposing_Diffusion-Based_Image_Generators_for_Monocular_Depth_Estimation_CVPR_2024_paper.pdf — paper — 2024
[7] Marigold: Affordable Adaptation of Diffusion-Based Image Generators for Image Analysis (arXiv 2505.09358) — https://arxiv.org/abs/2505.09358 — paper — 2025
[8] Marigold V2: Revisiting Diffusion Transformers for Monocular Depth Estimation (arXiv 2609.08084) — https://arxiv.org/abs/2609.08084 — paper — 2026
[9] huawei-bayerlab/marigold-v2 — https://github.com/huawei-bayerlab/marigold-v2 — code repo — n.d.
[10] Rethinking Inductive Biases for Surface Normal Estimation (DSINE, arXiv 2403.00712) — https://arxiv.org/abs/2403.00712 — paper — 2024
[11] baegwangbin/DSINE — https://github.com/baegwangbin/DSINE — code repo — n.d.
[12] Let RGB Be the Language of Vision (arXiv 2607.12450) — https://arxiv.org/pdf/2607.12450 — paper — 2026
[13] Lotus: Diffusion-based Visual Foundation Model for High-quality Dense Prediction — https://arxiv.org/html/2409.18124v1 — paper — 2024
[14] StableNormal: Reducing Diffusion Variance for Stable and Sharp Normal (arXiv 2406.16864) — https://arxiv.org/html/2406.16864v1 — paper — 2024
[15] Face Normal Estimation from Rags to Riches (arXiv 2601.01950) — https://arxiv.org/pdf/2601.01950 — paper — 2026
[16] Cross-modal Deep Face Normals with Deactivable Skip Connections (arXiv 2003.09691) — https://arxiv.org/pdf/2003.09691 — paper — 2020
[17] Sapiens: Foundation for Human Vision Models (arXiv 2408.12569) — https://arxiv.org/abs/2408.12569 — paper — 2024
[18] DAViD: Data-efficient and Accurate Vision Models from Synthetic Data — https://arxiv.org/html/2507.15365 — paper — 2025
[19] Depth Anything 3: Recovering the Visual Space from Any Views (arXiv 2511.10647) — https://arxiv.org/abs/2511.10647 — paper — 2025
[20] ByteDance-Seed/Depth-Anything-3 — https://github.com/ByteDance-Seed/Depth-Anything-3 — official code repo — n.d.
[21] 1038lab/ComfyUI-Depth-Anything-3 — https://github.com/1038lab/ComfyUI-Depth-Anything-3 — community wrapper repo — n.d.
[22] ika-rwth-aachen/ros2-depth-anything-v3-trt — https://github.com/ika-rwth-aachen/ros2-depth-anything-v3-trt — community deployment repo — n.d.

**Further reading (by name, not yet linked)**
- Yang et al., *Depth Anything: Unleashing the Power of Large-Scale Unlabeled Data*, CVPR 2024
- Ranftl et al., *Towards Robust Monocular Depth Estimation: Mixing Datasets for Zero-shot Cross-dataset Transfer* (MiDaS), TPAMI
- Bochkovskii et al., *Depth Pro: Sharp Monocular Metric Depth in Less Than a Second*, 2024
- Wang et al., *MoGe*, CVPR 2025, and MoGe-2, 2025
- Hu et al., *Metric3D v2*, TPAMI 2024
- Piccinelli et al., *UniDepth*, CVPR 2024
- Eftekhar et al., *Omnidata*, ICCV 2021
- Bae, Budvytis & Cipolla, *Estimating and Exploiting the Aleatoric Uncertainty in Surface Normal Estimation*, ICCV 2021
- Fu et al., *GeoWizard*, ECCV 2024
- Trigeorgis et al., *Face Normals "in-the-wild" using Fully Convolutional Networks*, CVPR 2017
- Sengupta et al., *SfSNet*, CVPR 2018
- Wu, Rupprecht & Vedaldi, *Unsupervised Learning of Probably Symmetric Deformable 3D Objects from Images in the Wild*, CVPR 2020
- Kemelmacher-Shlizerman & Basri, *3D Face Reconstruction from a Single Image Using a Single Reference Face Shape*, TPAMI 2011
- Belhumeur, Kriegman & Yuille, *The Bas-Relief Ambiguity*, IJCV 1999
- Ramamoorthi & Hanrahan, *An Efficient Representation for Irradiance Environment Maps*, SIGGRAPH 2001
- Basri & Jacobs, *Lambertian Reflectance and Linear Subspaces*, TPAMI 2003
- Nehab et al., *Efficiently Combining Positions and Normals for Precise 3D Geometry*, SIGGRAPH 2005
- Quéau, Durou & Aujol, *Normal Integration: A Survey*, JMIV 2018
- Cao et al., *Bilateral Normal Integration*, ECCV 2022
- Frankot & Chellappa, integrability enforcement in shape from shading, TPAMI 1988
- Saito et al., *PIFuHD*, CVPR 2020
- Xiu et al., *ECON*, CVPR 2023
- Feng et al., *DECA*, SIGGRAPH 2021
- Lei et al., *HRN*, CVPR 2023
- Garrido et al., *Reconstructing Detailed Dynamic Face Geometry from Monocular Video*, SIGGRAPH Asia 2013
- Nicolet, Jacobson & Jakob, *Large Steps in Inverse Rendering of Geometry*, SIGGRAPH Asia 2021
- Ma et al., *Rapid Acquisition of Specular and Diffuse Normal Maps from Polarized Spherical Gradient Illumination*, EGSR 2007
- Wood et al., *Fake It Till You Make It*, ICCV 2021
