# Face recognition embeddings as identity signals

> A face-recognition network such as ArcFace turns a 112×112 face crop, aligned on five keypoints, into a 512-dimensional vector. Two faces count as the same person when the cosine similarity of their L2-normalised vectors clears a threshold, and that threshold must be calibrated per model, per image domain and ideally per subject. In photo→3D work the embedding plays three roles. It is a frozen **identity encoder** for a scan-supervised shape regressor (MICA, whose loss is geometric, not an ArcFace identity loss), an **identity loss** on renders (Genova 2018, Deng 2019, GANFIT, DECA), and an offline **likeness scorecard** for camera-matched renders of the sculpt. The scorecard can be fooled: it is blind to scale, weak on depth, ears and cranium, and dominated by texture, eyes and brows, so measure it on clay renders against a calibrated genuine/impostor baseline. The common InsightFace weights are reportedly non-commercial only, and embeddings are biometric data, which limits how an add-on ships the model and stores its outputs.
>
> Evidence status: 1 ✅ / 21 📄 / 37 🧠 / 9 ↔️ — 🧠 items are queued for web verification.

## Key facts

**What the embedding is**
- **ArcFace** (Deng, Guo, Yang, Xue, Kotsia, Zafeiriou; CVPR 2019) adds an *additive angular margin* to the angle of the target class. That margin equals a geodesic-distance margin on the normalised hypersphere [1][2]. 📄 ([1] and [2] are two versions of one paper, so they are not independent.)
- ArcFace reports state-of-the-art results on **ten** benchmarks, and the arXiv abstract also describes a **sub-center** variant for noisy training data [1]. 📄
- **Loss form.** The target logit is s·cos(θ_y + m) and every other logit is s·cos θ_j. Usual defaults are **s = 64, m = 0.5 rad (≈28.6°)**. The loss family runs SphereFace (cos mθ) → CosFace (cos θ − m) → ArcFace (cos(θ + m)), and all three fit the combined form cos(m₁θ + m₂) − m₃. 🧠
- **Successors keep the interface** (aligned crop in, 512-d vector out) and change the margin or training scale: CurricularFace, MagFace (feature norm encodes quality), AdaFace (quality-adaptive margin, best on degraded images), Partial FC (millions of identities) and ViT backbones. On good photos they should rank renders similarly; they differ mainly at very low false-match rates and on poor images. 🧠
- For unit vectors **‖a − b‖² = 2 − 2 cos θ**, so cosine and L2 thresholds convert exactly [5]. ✅ (an exact identity, from [5] plus derivation)
- **FaceNet** thresholds the *squared* L2 distance and reports **99.63 % on LFW**. This figure comes from a search summary, not the paper text [5]. 📄
- **LFW protocol.** The threshold is tuned on 9 of 10 folds and tested on the 10th, and the 10 results are averaged [9]. 📄 Modern recognisers score about 99.8 % on LFW, so LFW cannot separate them. Use cross-pose CFP-FP and IJB-C at low false-accept rate (FAR) instead. 🧠
- **There is no canonical threshold for ArcFace.** Thresholds depend on the model and the data, so sweep your own labelled pairs until you reach a target FAR [9]. 📄 One LFW study cites a "conventional" cosine threshold of 0.5 and beats it with an adaptive one [9]. 📄
- **Blind to scale.** The 5-point *similarity* alignment removes scale, in-plane rotation and translation, so the embedding carries no information about head size. 🧠
- **Crop coverage.** The canonical 112² template puts the eyes at about (38, 52) and (74, 52) and the mouth corners at y ≈ 92. The crop therefore runs from roughly mid-forehead to chin and cuts through the cheeks, and the ears, cranium, hairline and neck barely count (Table 2). 🧠

**Identity in 3D face reconstruction**
- **MICA** (Zielonka, Bolkart, Thies; ECCV 2022) uses a **pretrained ArcFace network as its identity encoder**. A small mapping network takes its output into the latent space of a geometry decoder [3][4]. 📄
- MICA keeps ArcFace frozen except for the **last 3 ResNet blocks**. The authors found that fine-tuning more layers overfit [3]. 📄
- **MICA's objective is a masked, supervised 3D geometry loss against scans, with no ArcFace identity term** [3]. 📄 This matches the expert reading: a region-weighted per-vertex L1 loss on a neutral, metric FLAME shape. 🧠
- MICA reports **15 %** (non-metric NoW evaluation) and **24 %** (metric evaluation) lower average error than the prior state of the art [3]. 📄
- MICA's rationale is that ArcFace features are robust to expression, illumination and camera, so a regressor built on them generalises [3]. 📄 The same invariance means the embedding deliberately ignores some things a sculptor must get right.
- **Identity *losses* are an older, separate line of work**, each comparing a recogniser's view of a render with the photo: Genova et al. 2018 (FaceNet features, unsupervised 3DMM regression), Deng et al. 2019 (perceptual cosine loss), GANFIT 2019 (identity and content features during fitting) and DECA 2021 (identity loss from a VGGFace2-trained ResNet50). 🧠
- **Embeddings can be inverted.** NbNet-style decoders and Arc2Face (Stable Diffusion conditioned on ArcFace vectors, ECCV 2024) regenerate recognisable faces from a vector, and ID-guided 3D avatar methods followed in 2024–25. A stored embedding is therefore *not* anonymised. 🧠

**Models, files, licences**
- **buffalo_l** is the SCRFD-10GF detector plus a ResNet50 recogniser trained on WebFace600K, about **326 MB** in total [6]. 📄 Its recogniser `w600k_r50.onnx` is about **166 MB** and outputs **512-d** vectors [7][6]. 📄
- The pack also ships `2d106det.onnx` (106 2D landmarks), `1k3d68.onnx` (68 3D landmarks) and `genderage.onnx`. **antelopev2** swaps in a ResNet100 trained on Glint360K, and **buffalo_s/sc** use MobileFaceNet. 🧠
- **Licence.** The pretrained models are reported as **non-commercial research only**, separately from the MIT-licensed code [7]. 📄 Mirrors on SourceForge, Hugging Face and GitHub releases are unofficial [8][10]. 📄 The legacy CLI command is `insightface-cli model.download buffalo_l`, which saves to `~/.insightface/models/buffalo_l/` [6]. 📄
- **Possibly more permissive alternatives, all needing licence checks:** OpenCV Zoo SFace (128-d, with the YuNet detector), dlib's ResNet (128-d, Euclidean threshold 0.6) and facenet-pytorch (InceptionResNetV1 on VGGFace2). Whatever the code licence says, weights carry their training data's consent and licence baggage. ↔️

**Bias and ethics**
- **Demographic effects.** NIST FRVT Part 3 (NISTIR 8280, 2019) found that, for many algorithms, false-match rates differ between demographic groups by factors of roughly 10–100. Impostor scores run higher between people of the same sex, age band and ancestry. 🧠 Impostor statistics must therefore be matched to the subject's demographics.
- **Training data.** MS-Celeb-1M was withdrawn in 2019 over consent concerns, and most recogniser weights descend from web-scraped celebrity data. 🧠
- **Law (time-sensitive, not legal advice).** GDPR Art. 9 makes biometric data used for unique identification a special category; Illinois BIPA requires written consent and a retention policy; the EU AI Act has banned untargeted scraping for face-recognition databases since February 2025, and its Art. 50 deepfake-labelling duties were scheduled for August 2026, with delay proposals pending. ↔️

## Numbers & reference tables

**Table 1: Sourced numbers**

| Item | Value | Unit | Population / benchmark | Badge |
|---|---|---|---|---|
| MICA error reduction vs prior SOTA, non-metric | 15 | % lower mean error | NoW (sample size not retrieved) | 📄 [3] |
| MICA error reduction vs prior SOTA, metric | 24 | % lower mean error | metric evaluation (benchmark naming varies) | ↔️ [3] |
| ArcFace ResNet blocks fine-tuned in MICA | 3 | blocks (rest frozen) | model design | 📄 [3] |
| Benchmarks with ArcFace SOTA | 10 | count | ArcFace abstract | 📄 [1] |
| FaceNet verification accuracy | 99.63 | % | LFW, 10-fold | 📄 [5] |
| "Conventional" fixed threshold | 0.5 | cosine | LFW-based study | 📄 [9] |
| buffalo_l pack | ~326 | MB | software | 📄 [6] |
| w600k_r50.onnx | ~166; 512 | MB; dims | software | 📄 [7] |

**Table 2: InsightFace ArcFace ONNX contract** (from InsightFace code; time-sensitive)

| Item | Value | Badge |
|---|---|---|
| Input | 1×3×112×112 float32, RGB (feed cv2 BGR with swapRB) | 🧠 |
| Normalisation | (px − 127.5)/127.5, *unless* the graph starts with Sub/Mul nodes (older MXNet conversions), in which case use raw 0–255 | 🧠 |
| Alignment | 5-point similarity transform (`estimateAffinePartial2D`/Umeyama) to the template below | 🧠 |
| Template (x, y) px | L-eye 38.29, 51.70 · R-eye 73.53, 51.50 · nose 56.03, 71.74 · L-mouth 41.55, 92.37 · R-mouth 70.73, 92.20 | 🧠 |
| Template inter-ocular distance | ≈35.2 px | 🧠 (derived) |
| Output | 512 floats, **not** normalised; L2-normalise before the dot product | 🧠 |
| SCRFD defaults | det_size 640×640, det_thresh 0.5 | 🧠 |

**Table 3: Threshold and score anchors** (not portable between models)

| Anchor | Model | Value | Cosine equivalent | Badge |
|---|---|---|---|---|
| LFW study, fixed threshold | unspecified | cos 0.5 | 0.50 | 📄 [9] |
| OpenCV FaceRecognizerSF sample | SFace, 128-d | cos 0.363 / L2 1.128 | 0.363 (the two values are self-consistent) | 🧠 |
| deepface library default | ArcFace (Keras port) | cosine distance ≈0.68 / L2 ≈1.13 | ≈0.32–0.36 | 🧠 |
| Practitioner decision range | buffalo_l / antelopev2 | cos 0.28–0.45 | — | ↔️ |
| Genuine pairs, good frontal photos | buffalo_l | ~0.5–0.8 | — | 🧠 |
| Impostor pairs | buffalo_l | ~−0.1 to 0.2, mean near 0 | — | 🧠 |
| Random unit vectors, d = 512 | math | SD = 1/√512 ≈ 0.044 | — | 🧠 |

**Table 4: Cosine ↔ L2 for unit vectors** (d² = 2 − 2cos; arithmetic, not thresholds)

| cos θ | d² | d | θ (deg) | Badge |
|---|---|---|---|---|
| 1.0 | 0.0 | 0.000 | 0.0 | ✅ |
| 0.7 | 0.6 | 0.775 | 45.6 | ✅ |
| 0.5 | 1.0 | 1.000 | 60.0 | ✅ |
| 0.3 | 1.4 | 1.183 | 72.5 | ✅ |
| 0.0 | 2.0 | 1.414 | 90.0 | ✅ |

**Table 5: Default likeness-scorecard protocol** (design heuristics)

| Parameter | Default | Range | Reason | Badge |
|---|---|---|---|---|
| Reference photos per subject | 6–10 | ≥3 | estimate the genuine ceiling | 🧠 |
| Scored views (yaw) | 0°, ±25°, ±45° | \|yaw\| ≤ 60° | 5-point alignment fails near profile | 🧠 |
| Source inter-ocular distance (IOD) | ≥60 px | floor 35 px; ≥90 px preferred | avoid upsampling to the 35 px template IOD | ↔️ |
| Render resolution | face ≥450 px, area-downsampled | 4–8× the crop | aliasing | 🧠 |
| Blender view transform | Standard, sRGB | — | AgX and Filmic tone curves shift contrast | 🧠 |
| Impostor set | ≥100 demographically matched faces | 50–500 | z-normalisation statistics | 🧠 |
| Keypoint-drift alarm (112² crop) | >3 px | 2–4 px | camera or geometry mismatch | 🧠 |
| Recognisers | 2, one held out | — | Goodhart's law | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Consent gate and quality check at intake.** Embed nothing until "I have this person's permission" is ticked. Reject photos with detector score < 0.5, IOD < 60 px, |yaw| > 45°, sunglasses or heavy occlusion, or a strong expression. Embed the rest and compute all photo-to-photo **genuine** scores; their median is the **ceiling** no render should be expected to beat. Drop any photo more than 2 robust SD below the others (likely mis-detected, retouched or much older/younger).
2. **Match each render to its photo's camera**: focal length, distance and head pose from the multi-view solver (a wide-angle selfie changes nose-to-ear proportions). Render with the **Standard** view transform, not AgX or Filmic, in Workbench or Eevee at the photo's aspect ratio, with the face at least 450 px across.
3. **Render four conditions for each view** (a factorial control):
   - **T**: the sculpt with projected photo texture;
   - **C**: clay with *generic* eyeballs, iris and brows;
   - **X**: the subject's texture UV-transferred onto the *template/mean head*;
   - **G**: the mean head in clay with generic eyes.

   Geometry's contribution is **C − G** (and T − X). Texture's contribution is **X − G**. If T is high but C − G is near zero, the likeness lives in the texture: keep sculpting. 🧠
4. **Use the same warp for the photo and its render.** The render is pixel-registered to the photo, so apply the *photo's* 5-point similarity warp to both. Score differences then come from content rather than alignment. Also run the detector on the render: if a keypoint drifts more than 3 px in the 112² crop, it shows which feature is misplaced (eye spacing, mouth width). Fix that with landmarks first.
5. **Preprocess both images identically**: same resampling (area), face mask and background (neutral grey, or the render composited into the photo). Optionally also score a greyscale, masked pair to remove skin-tone and eye-colour cues. **Do not** average in a flipped copy (a common test-time trick): it hides asymmetry, which is part of the likeness.
6. **Score relative to the baseline.** Per view record raw cosine, **ceiling ratio** s / genuine-median, **impostor z** = (s − μ_imp)/σ_imp, and **rank** among the impostor gallery. Summarise with the median and worst view; a spread above ~0.1 across views points to pose or camera error, not shape.
7. **Know what the score responds to.** It is strongly sensitive to eye spacing and shape, the brow ridge, nose width and length, mouth width and the jaw outline in ¾ view. It is weakly sensitive to nose projection in frontal views, cranial shape, ear shape, absolute size and the hairline. **Never** use it to validate millimetre proportions; use landmark reprojection and scale references for that. MICA needed 3D supervision to turn ArcFace features into metric shape [3]. 🧠
8. **Expect a gap between renders and photos.** Hairless, eyeless or neckless renders score low even when the shape is right. Compare *gains from one iteration to the next* under fixed render settings, never raw scores across setups.
9. **Model handling.** Do not bundle buffalo_l [7]; have the user fetch it by the official route [6], treat mirrors [8][10] as untrusted, and pin each file's SHA-256. Run onnxruntime (CPU) in Blender's Python; extensions can ship platform wheels since Blender 4.2, but check the target release's Python version. 🧠
10. **Privacy.** Run everything locally and keep embeddings in memory only. Persist only scores and model hashes, and never offer search against other people's photos. Build impostor galleries only from licensed or consented datasets.

## Algorithmic implications

- **Three modules with three names**, so the docs never call the scorer a "loss" (MICA does not use it as one [3]):
  - `IdentityScorer`: ONNX, no gradients, used for evaluation, early stopping and model selection;
  - `IdentityPrior`: an embedding→shape regressor of the MICA type;
  - `IdentityLoss`: optional and off by default.
- **MICA-type prior.** Run the regressor on each reference photo and take the coordinate-wise median β̃. Use the prior N(β̃, diag σ²) with σ_k = max(1.4826·MAD_k, σ_floor).
  - With FLAME coefficients in SD units, use σ_floor ≈ 0.5 for the first 20–50 components and 1.0 (the population prior) for the rest.
  - This prior is informative but loose, because MICA beats the scaled mean face by only a fraction of a millimetre (see the single-image-regression note).
  - This is a heuristic: tune it on held-out scans. 🧠
- **Scale never comes from the embedding.** The scale prior comes from the camera solve or the anthropometric notes. 🧠
- **Fine-tuning defaults** for anyone training an embedding→shape regressor: freeze the backbone and train at most the last 3 blocks [3]. 📄
- **Optional `IdentityLoss`.** L_id = λ·Σ_v max(0, τ_v − cos_v)².
  - Compute it **only on C-condition renders**, averaged over random augmentations (±2 px shift, ±3 % scale, ±3° roll, light jitter) and over **≥2 recognisers**. Different models resist adversarial "score hacking" that does not transfer between them (Sharif et al. 2016 showed recognisers can be fooled by local patterns).
  - Set τ_v = the score reached after landmark fitting + 0.05, capped at the genuine ceiling.
  - Choose λ so that L_id is at most 10–20 % of total energy at convergence.
  - Accept a step only if landmark reprojection RMS rises by no more than 0.5 px and every coefficient stays within 3σ of its prior.
  - There are no ONNX gradients in Blender, so optimise ≤50 coefficients with SPSA or CMA-ES. Each evaluation is a Workbench render (~0.05–0.2 s) plus inference (~20–50 ms on CPU for R50). These timings are order-of-magnitude estimates. 🧠
- **Stopping rule.** Stop on the clay impostor z-score from the **held-out** recogniser, never from the one being optimised.
- **Per-model config** (no hard-coded constants): `model_sha256`, `licence`, `embedding_dim` and `input_shape` read from the ONNX graph, `mean`/`std` (detect leading Sub/Mul nodes), `template_5pt`, `metric: cosine`, `threshold: null` until calibrated, `flip_tta: false`.
- **Per-subject calibration record**: genuine n, median and IQR; impostor μ and σ with demographic tags; view buckets; date. Recalibrate whenever the model or render settings change.
- **Licence guard.** Warn when a model tagged non-commercial is enabled in a project flagged as commercial.

## Disagreements, myths & open questions

- **Myth: "MICA trains with an ArcFace identity loss."** The primary source as harvested [3] and expert reading agree that ArcFace is MICA's partly fine-tuned *encoder* and the loss is 3D geometry. Identity losses belong to Genova, Deng, GANFIT and DECA. 📄
- **Myth: "a higher identity score means more accurate geometry."** Recognisers are trained to be invariant [3] and they see texture. Human studies also find surface reflectance about as important as shape (Russell & Sinha 2007). Without the C/G controls, a high score says little about form. 🧠
- **Thresholds disagree.** Published values include cos 0.5 [9], 0.32–0.36 from library defaults, and FaceNet's squared-L2 scale [5]. They are incomparable without fixing model, metric and FAR. ↔️ The harvester's "0.08–0.09" value had no source, so it was dropped.
- **"ArcFace scores 99.83 % on LFW."** This is plausible for R100/MS1MV2 and is also the figure on the buffalo_l zoo row, but it has not been checked against the paper. 🧠
- **Which benchmark MICA's 24 % refers to.** The harvest says the NoW metric variant, while the sibling note says MICA's own metric benchmark. ↔️
- **"Mirror X equals the official buffalo_l."** This is unverified [8][10]. ↔️
- **Licences.** Do the InsightFace weights have commercial terms on request? Are the SFace, dlib and AdaFace weights genuinely permissive? ↔️
- **Open questions:** how much of the score on 3D renders is texture rather than geometry (no study found); whether a depth- or normal-map 3D recogniser could serve as a geometry-only scorer; impostor calibration for under-represented groups; the exact 2025–26 EU AI Act changes ("digital omnibus" delays); whether ViT or AdaFace successors track sculpt edits better than R50.

## Sources

[1] ArcFace: Additive Angular Margin Loss for Deep Face Recognition — https://arxiv.org/abs/1801.07698 — paper — 2019
[2] ArcFace (arXiv HTML v3) — https://arxiv.org/html/1801.07698v3 — paper — 2019
[3] MICA: Towards Metrical Reconstruction of Human Faces (Zielonka, Bolkart, Thies) — https://arxiv.org/abs/2204.06607 — paper — 2022
[4] MICA project page (MPI-IS) — https://is.mpg.de/ncs/en/projects/mica-towards-metrical-reconstruction-of-human-faces — official-docs — 2022
[5] FaceNet: A Unified Embedding for Face Recognition and Clustering — https://arxiv.org/pdf/1503.03832.pdf — paper — 2015
[6] InsightFace python-package model_zoo.md — https://github.com/deepinsight/insightface/blob/master/python-package/docs/model_zoo.md — repo — 2024
[7] Third-party InsightFace buffalo_l wrapper README (licence claim unverified) — https://github.com/wangyifan349/insightface-face-similarity — repo — year unknown
[8] Third-party trimmed buffalo_l release (unverified mirror) — https://github.com/inoveee/eventlens/releases/tag/face-models-v1 — forum — year unknown
[9] Adaptive Threshold for Online Object Recognition and Re-identification Tasks — https://arxiv.org/pdf/2012.14305 — paper — 2020
[10] Third-party weights release (unverified mirror) — https://github.com/finetech-nexus/ai-api/releases/tag/weights-v1 — forum — year unknown

**Further reading (by name, not yet linked)**
- Liu et al., *SphereFace: Deep Hypersphere Embedding for Face Recognition*, CVPR 2017
- Wang et al., *CosFace: Large Margin Cosine Loss for Deep Face Recognition*, CVPR 2018
- Deng et al., *Sub-center ArcFace*, ECCV 2020
- Huang et al., *CurricularFace*, CVPR 2020
- Meng et al., *MagFace: A Universal Representation for Face Recognition and Quality Assessment*, CVPR 2021
- Kim, Jain, Liu, *AdaFace: Quality Adaptive Margin for Face Recognition*, CVPR 2022
- An et al., *Partial FC* (efficient large-scale face recognition training), CVPR 2022
- Zhu et al., *WebFace260M* benchmark, CVPR 2021
- Guo et al., *Sample and Computation Redistribution for Efficient Face Detection* (SCRFD), ICLR 2022
- Genova et al., *Unsupervised Training for 3D Morphable Model Regression*, CVPR 2018
- Deng et al., *Accurate 3D Face Reconstruction with Weakly-Supervised Learning: From Single Image to Image Set*, CVPRW 2019
- Gecer et al., *GANFIT*, CVPR 2019
- Feng, Feng, Black, Bolkart, *Learning an Animatable Detailed 3D Face Model from In-the-Wild Images* (DECA), SIGGRAPH 2021
- Papantoniou et al., *Arc2Face: A Foundation Model for ID-Consistent Human Faces*, ECCV 2024
- Mai et al., *On the Reconstruction of Face Images from Deep Face Templates* (NbNet), IEEE TPAMI
- Sharif et al., *Accessorize to a Crime*, ACM CCS 2016
- Grother, Ngan, Hanaoka, *FRVT Part 3: Demographic Effects*, NISTIR 8280, 2019
- Russell & Sinha, *Real-world face recognition: the importance of surface reflectance properties*, Perception 2007
- Zhong et al., *SFace: Sigmoid-Constrained Hypersphere Loss for Robust Face Recognition*, IEEE TIP 2021
- Regulation (EU) 2024/1689 (AI Act); GDPR Art. 9; Illinois BIPA (740 ILCS 14)
