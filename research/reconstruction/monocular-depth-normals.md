# Monocular depth and surface normals for faces

> General-purpose monocular depth models (Depth Anything V2/V3, Marigold) and normal estimators (DSINE, Marigold-Normals, Lotus, StableNormal) are trained and scored on whole scenes. In this pass we found no face-specific accuracy numbers for any of them. Human-specific models (Meta's Sapiens, DAViD) and a small set of face-normal papers exist, but their face-region accuracy is also unquantified here. Relative/affine-invariant depth (DA V2, Marigold) cannot give a head's absolute depth or scale. Depth Anything 3's metric head scales linearly with the focal length you give it. So for likeness work, use predicted **normals** as a mid/high-frequency detail signal on top of a landmark/3DMM base fit, and use predicted **depth** only as a weak, scale/shift-free shape prior. **Verification caveat:** the shared web-search budget ran out before any independent cross-check could be made. Nearly every claim below therefore rests on the harvester's single search pass and is marked ⚠️. Treat the numbers as leads to re-check, not settled facts.

## Key facts

**Depth: Depth Anything V2 (DA V2)**
- Search summaries describe DA V2 as a *relative* depth model: it orders surfaces near to far but does not recover absolute metric distance. This is a secondary description that was not checked against the paper text [1][2] ⚠️
- DA V2 Small: ~25M parameters, 60 ms per image (hardware not stated in the snippet), 95.3% accuracy on the DA-2K relative-depth benchmark [1][2] ⚠️ ([2] is a mirror of [1], not an independent source.)
- Training-data ablation on DA-2K: 89.8% with labelled synthetic data alone and 95.3% with pseudo-labelled real images alone [1] ⚠️
- DA V2 ViT-L on NYU-D: δ1 = 0.984, AbsRel = 0.056. The snippet does not say whether this is zero-shot or fine-tuned [1] ⚠️
- Robotics and outdoor studies disagree on how good its metric depth is. One autonomous-vehicle obstacle study ranks DA V2 the most accurate monocular method, with low, stable error across distances [3]. A robotics study finds higher pixel resolution than LiDAR but significantly worse metric accuracy [4]. A low-overlap drone photogrammetry study reports metre-level errors for both networks tested, with MiDaS v3.1 clearly worse than DA V2 [5] ↔️
- No face-specific evaluation of DA V2 turned up. Its published benchmarks are general scenes [2] ⚠️

**Depth: Depth Anything 3 (DA3)**
- DA3 ("Recovering the Visual Space from Any Views") is arXiv 2511.10647. The ID prefix shows a November 2025 submission, and a community wrapper gives the date as 14 Nov 2025 [19][21]. The month is ✅. The exact day is ⚠️
- The official repo ships a `DA3Metric-Large` model. Metric depth = focal × network output / 300, where focal is the mean of fx and fy in pixels [20] ⚠️
- DA3-metric is reported as best on SUN-RGBD (AbsRel 0.105) and second best on DIODE [19] ⚠️
- A community wrapper lists DA3Metric-Large at ~350M parameters [21] ⚠️
- A third-party TensorRT ROS2 node exists, so a GPU deployment path exists. No CPU or ONNX latency was found [22] ⚠️

**Diffusion-based depth/normals: Marigold family**
- Marigold (Ke et al., CVPR 2024) repurposes the Stable Diffusion image generator as an **affine-invariant** monocular depth estimator, meaning depth is known only up to an unknown scale and shift [6] ⚠️ (primary source; [7] is by the same group).
- The extended Marigold paper adds **Marigold-Normals**, fine-tuned with the same protocol as Marigold-Depth [7] ⚠️
- Marigold V2 (arXiv 2609.08084, 2026) swaps the backbone for a diffusion transformer, reportedly Qwen-Image-Edit per a search summary. The authors claim state-of-the-art surface normals. The repo has a normals config that trains with an angular loss [8][9] ⚠️ (the SOTA claim is the authors' own).
- StableNormal targets the sample-to-sample variance of diffusion normal predictors ("Reducing Diffusion Variance for Stable and Sharp Normal") [14]. Lotus is another diffusion-based dense-prediction model, and its paper includes a normal benchmark table [13] ⚠️

**Normals: DSINE**
- DSINE feeds per-pixel ray direction into the network and learns the relative rotation between neighbouring normals. Code is public [10][11] ⚠️
- DSINE's mean angular error on NYUv2 is about **16.4°**. Two later papers cite this value independently [12][13] ✅
- DSINE is reported as trained on ~160K images and beating Omnidata-V2, which was trained on >12M. The snippet's attribution is unclear [10] ⚠️

**Human- and face-specific estimators**
- Sapiens (Meta) is a human-centric model family covering 2D pose, body-part segmentation, depth and surface normals. It was pretrained on >300M in-the-wild human images [17] ⚠️
- Sapiens depth/normal supervision came from synthetic renders of 600 detailed RenderPeople scans [17] ⚠️
- Reported gains over prior work: 22.4% relative RMSE improvement on Hi4D (depth) and 53.5% relative angular-error improvement on THuman2 (normals). The baselines were not checked [17] ⚠️
- DAViD trains human dense-prediction models (depth, normals) on synthetic data, with a focus on data efficiency [18] ⚠️
- Face-normal papers: *Cross-modal Deep Face Normals with Deactivable Skip Connections* (2020) estimates normals from in-the-wild face photos [16]. *Face Normal Estimation from Rags to Riches* (2026) refines a coarse face normal using exemplars [15] ⚠️ We could not tell whether either paper benchmarks against DSINE, Sapiens or Marigold.

## Numbers & reference tables

**Table 1: Model inventory (reported figures; none measured on faces)**

| Model | Output | Params | Training / pretraining data | Reported benchmark | Src | Status |
|---|---|---|---|---|---|---|
| DA V2 Small | relative depth | ~25M | pseudo-labelled real (student) | DA-2K 95.3%; 60 ms/img (hardware unstated) | [1][2] | ⚠️ |
| DA V2 (ablation) | relative depth | — | labelled synthetic only / pseudo-labelled real only | DA-2K 89.8% / 95.3% | [1] | ⚠️ |
| DA V2 ViT-L | depth | — | — | NYU-D δ1 0.984, AbsRel 0.056 (protocol unclear) | [1] | ⚠️ |
| DA3Metric-Large | metric depth | ~350M (wrapper) | — | SUN-RGBD AbsRel 0.105 (best); DIODE 2nd | [19][21] | ⚠️ |
| DSINE | normals | — | ~160K images | NYUv2 mean angular error ≈16.4° | [10][12][13] | ✅ (error) / ⚠️ (data) |
| Omnidata-V2 | normals | — | >12M images | (comparison baseline for DSINE) | [10] | ⚠️ |
| Sapiens | depth, normals, seg, pose | — | >300M human images pretrain; 600 RenderPeople scans for depth/normal | −22.4% rel. RMSE Hi4D; −53.5% rel. angular error THuman2 | [17] | ⚠️ |

**Table 2: DA3 metric conversion (from the official repo [20], ⚠️)**

| Quantity | Formula | Units | Consequence |
|---|---|---|---|
| Metric depth | `Z = f · y / 300` | Z in the network's metric unit; f in px; y = raw network output | Z is linear in f. A 10% focal error gives a 10% depth error (follows from the formula). |
| f | `(fx + fy) / 2` | px | Our engine uses square pixels (`Camera.f`), so f = `Camera.f`. |

Not found in this pass: CPU/ONNX latency for any model, licences of any weights, and any angular or depth error measured on faces.

## Applying this to photo→3D face sculpting in Blender

1. **Never use the depth map as the base shape.** Fit the base head from landmarks plus a morphable model or template with the engine's PnP/LM solvers first. Relative depth (DA V2) and affine-invariant depth (Marigold) have no scale or offset [2][6]. A raw displaced plane from these maps will have arbitrary nose projection.
2. **Get the focal length before running depth.** Use EXIF 35 mm-equivalent focal → `focal_px_from_35mm`. DA3 metric depth is directly proportional to the focal you pass [20]. Without a trustworthy focal, treat DA3 output as relative too.
3. **Align, then inspect residuals.** Render the fitted mesh's depth from the solved camera. Solve the per-image scale s and shift t that best map predicted depth onto it, inside a skin mask. Then look at the residual image. Residual that follows the lighting (cast shadow from the nose, highlight on the forehead) is a shading artefact, not geometry.
4. **Mask aggressively.** Exclude hair, beard, eyebrows, eyes/cornea, teeth, glasses, specular highlights and the silhouette band. Sapiens provides body-part segmentation alongside depth/normals [17] and is one candidate masker. Licence unverified.
5. **Use normals for detail, depth for gross profile at most.** Bake predicted camera-space normals into a camera-projected texture (Blender: UV → Project from View with the solved camera). Use them for nasolabial folds, eyelid creases, philtrum, and chin and lip contours. Apply the result as a Multires displacement or a height map, not by editing base topology.
6. **Check against the photo set.** Compare the refined mesh's silhouette to a profile photo, if one exists. Compare nose-tip-to-cheek depth before and after refinement. If refinement changes the profile more than the landmarks explain, reject it.
7. **Run diffusion predictors several times.** Marigold-family and other diffusion predictors are stochastic (StableNormal exists to reduce this variance [14]). Run several seeds and keep the per-pixel spread as an uncertainty map.
8. **Typical failures:**
   - Strong directional light or makeup. Normals are inferred from shading, so albedo and shadow leak into shape.
   - Close-range selfies processed with an orthographic assumption, which distorts integrated shape. Always integrate under perspective.
   - Lips, nostrils and eyelids are depth discontinuities. Plain Poisson integration smears across them.
   - Scene-trained models may under-represent fine facial relief. This is untested here and should be measured on our own scans.

## Algorithmic implications

- **Observation types.** Model each input explicitly in a registry:
  - `relative_depth`: unknown s and t; also record whether the model outputs depth or inverse depth, which must be checked per model.
  - `metric_depth_focal`: DA3; needs f [20].
  - `normal_cam`: unit vectors in the camera frame.

  Store with each entry: axis convention, model name and version, date, and licence, set to `unknown` until verified.
- **Convention adapter.** The engine camera frame is OpenCV-style: +x right, +y down, +z forward, millimetres. Every predicted normal map must be mapped into this frame. Validate on a rendered synthetic head (`face3d/synthetic.py`): normals near pronasale should point at the camera, i.e. along −z in the camera frame.
- **Depth residual (affine-invariant).** r_p = s·d̂_p + t − z_p(V). Solve (s, t) in closed form per iteration by weighted least squares over masked pixels, or carry them as nuisance parameters in `levenberg_marquardt`. Use a robust loss and a low weight. Only low-frequency information is trusted.
- **Normal residual.** e_p = 1 − n̂_p · n_p(V), with weight w_p = mask × confidence. Confidence comes from seed variance or a model-provided uncertainty. DSINE's ~16.4° NYUv2 mean error [12][13] gives an order-of-magnitude noise floor for scene data. A face-specific noise level is unknown, so expose the weight in the UI rather than hard-coding a "face" value.
- **Normal integration for detail.** Convert normals to gradients under perspective, using per-pixel rays from `Camera.ray`. Solve the sparse least-squares height field with `face3d.mesh.sparse.cg`. High-pass the integrated height against the rendered base-mesh depth and apply only the residual as per-vertex displacement along vertex normals.
- **Regularization.** Use a Laplacian smoothness term on displacements and a hard anchor on fitted landmarks, so detail cannot move likeness-critical points. Add a user-set displacement clamp. All weights are user parameters; we found no sourced defaults.
- **Discontinuities.** Down-weight smoothness across lip, nostril and eyelid boundaries, using the segmentation mask or an edge detector.
- **Runtime design.** CPU/ONNX availability is unconfirmed for all models. Architect the add-on so predictions are computed out of process (or imported as 16-bit PNG/EXR) and cached per photo. Do not bundle weights until licences are checked.
- **Multi-view.** DA3 is described as working from "any views" [19]. If several photos exist, a multi-view geometry estimate may beat per-image monocular cues. This is unevaluated here.

## Disagreements, myths & refuted claims

- **DA V2 metric quality (↔️).** "Best monocular method" [3] versus "significantly reduced metric accuracy vs LiDAR" [4] versus "metre-level errors" [5]. The setups differ (driving, robotics, aerial). None is a face scenario, and none is evidence about facial relief.
- **95.3% attribution.** Snippets attach the same DA-2K 95.3% to both "DA V2 Small" and "pseudo-labelled real data only". These are consistent if the ablation used the Small student, but this was not confirmed [1][2].
- **DSINE data-efficiency claim (~160K vs >12M images).** The snippet's attribution is unclear. Keep it as a secondary claim [10].
- **"Sapiens fine-tuned on 500K synthetic images".** The harvester attributed this to "a later paper" but linked only the Sapiens paper. It is unsourced and excluded from the tables.
- **Myth: "a single photo plus a depth model gives the true 3D head."** Affine-invariant and relative models have no scale or shift by construction [2][6]. DA3's metric output scales with the assumed focal [20]. Absolute nose projection still has to come from a calibrated multi-view or profile constraint.
- **Myth: "the newest model is best on faces."** The Marigold V2 SOTA claim [8] and the Sapiens gains [17] are authors' benchmarks on non-face or full-body data. No face benchmark backs them here.
- **Refuted:** none in this pass. Search budget prevented independent checks, so nothing could be confirmed or refuted.

## Open questions

- Face-region angular and depth error for DA V2/DA3, Marigold(-Normals, V2), DSINE, Lotus, StableNormal, Sapiens and DAViD, e.g. against FaceScape-style scans. This is the key missing measurement. We should benchmark these ourselves on scanned heads.
- Licences of all weights and code (DA V2 sizes, DA3 sizes, Marigold V1/V2, DSINE, Sapiens, DAViD): not checked.
- ONNX exports and CPU latency at ~512–1024 px input: not confirmed for any model. The 60 ms DA V2 Small figure has no stated hardware [2].
- Mesh-refinement methods from predicted normals, such as normal integration with discontinuity handling (bilateral normal integration is a candidate lead). Detail-transfer pipelines from human-reconstruction work were not retrieved or verified.
- Whether DA3's metric head is reliable at portrait range (~0.3–2 m), and what unit its output uses. The repo formula was seen only as a snippet.
- Whether the two face-normal papers [15][16] release code or weights.
- Sapiens model sizes, input resolution and whether its normal head resolves facial micro-relief.

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
