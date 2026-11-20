# Facial landmark detectors

> In photo→3D likeness work, a landmark detector supplies the correspondences behind camera solving, multi-view triangulation and the first template warp. It does not supply the likeness, because every learned detector pulls its output toward the mean face. MediaPipe Face Landmarker (478 points, 52 blendshape scores, a 4×4 transform; Apache-2.0; milliseconds on CPU) is the only widely used detector whose code and weights are both permissively licensed, so it is the default. The 68/98-point heatmap models (FAN, HRNet, SPIGA, STAR) are research-licensed cross-checks. Good detectors reach about 3–4.5 % inter-ocular NME on benchmark photos, roughly 3–4 mm per point at face scale; inner anchors do about twice as well, jaw contours do worse, and error climbs past about 45° yaw. The model of choice for a fitter is Wood et al. 2022: about 700 landmarks, each with a predicted σ and trained on synthetic data only, but its weights are, to my knowledge, unreleased.
>
> Evidence status: 2 ✅ / 2 📄 / 71 🧠 / 17 ↔️ — 🧠 items are queued for web verification.

This topic had no harvest file and no earlier draft. Every item below is either expert knowledge or a design recommendation. Related sourced material is in `blender/blender-face-addons.md` (MediaPipe's 468/478 counts are cited there), `reconstruction/camera-pose-solving.md` and `blender/portrait-lighting-compare.md`.

## Key facts

**MediaPipe Face Landmarker** (MediaPipe Tasks)
- **Pipeline.** A BlazeFace short-range detector feeds a mesh regressor (v2 with attention refinement, about a 256 px crop; legacy Face Mesh used 192 px). An optional blendshape head and a geometry stage follow. All of it ships as one `face_landmarker.task` bundle of a few MB. 🧠
- **Outputs.** 478 landmarks: 468 mesh vertices plus two 5-point iris sets, 468–472 and 473–477. 52 blendshape scores in [0,1] with ARKit-style names; the set includes `_neutral` and lacks `tongueOut`. Optionally, a 4×4 `facial_transformation_matrixes` (sic) per face. 🧠
- **Coordinates.** x is normalised by image width and y by image height. z is depth relative to the head centre, smaller meaning nearer, on "roughly the same scale as x" [1]. z is **not metric** and is strongly mean-biased. 📄
- **Transform matrix.** It aligns a fixed canonical face (in cm) under an *assumed* perspective camera; the legacy config used a vertical FOV of about 63°. Its rotation is a usable initialiser. Its translation and scale describe the canonical face and that assumed FOV, not the subject or the lens. ↔️
- **Blendshapes.** A small model reads a subset of the landmarks (reportedly 146). Scores are not calibrated per identity: hooded lids or downturned mouth corners read as non-zero `eyeSquint` or `mouthFrown` at rest. 🧠
- **Pose range.** Reliable to about ±45° yaw and usable to about ±60–70°; at full profile, detection usually fails. Self-occluded points are still returned, hallucinated from the prior, because face landmarks carry no visibility or presence values. 🧠
- **Use `IMAGE` mode for stills.** `VIDEO` and `LIVE_STREAM` modes track from frame to frame, so they contaminate independent photos. 🧠
- **Licence.** Code is Apache-2.0, and the model card states Apache-2.0 for the weights, the cleanest terms here. ↔️ Re-check per release.

**dlib 68** (Kazemi & Sullivan ERT, 2014)
- **Model and speed.** Regression trees on pixel-difference features. About 1–3 ms per face on CPU, plus 20–100 ms for the HOG detector. The HOG detector is near-frontal only, to about ±30–40° yaw. 🧠
- **Licence trap.** The code is Boost-licensed. `shape_predictor_68_face_landmarks.dat` (about 95–100 MB) is trained on iBUG 300-W, whose terms exclude commercial use [2][3]. ✅ (Debian packaging lists the .dat as CC0 [8]; dlib's own notes still warn against commercial use.)
- **Accuracy.** About 6–6.5 % NME on 300-W full. Output collapses toward the mean shape at large pose or with an open mouth. 🧠

**FAN / 3D-FAN** (Bulat & Tzimiropoulos, ICCV 2017; the `face_alignment` package)
- **Architecture.** Four stacked hourglasses on a 256 px crop, producing 64×64 heatmaps, so sub-pixel decoding is required. 3D-FAN outputs 2D *projections of 3D* landmarks, plus z from a separate network. 🧠
- **Pose, licence and cost.** Trained on 300W-LP and LS3D-W (about 230 k images) to cover ±90° yaw. Code is BSD-3; the weights come from research datasets. Takes 0.1–1 s per face on CPU. Enum names changed between package versions. ↔️

**HRNetV2-W18** (Wang et al., TPAMI 2020)
- **Model.** High-resolution parallel branches with 64×64 heatmaps. Scores about 3.3 % NME on 300-W full and about 4.6 % on WFLW. MIT licence, about 10 M parameters, ONNX-exportable, tens of ms on CPU. 🧠

**SPIGA** (Prados-Torreblanca et al., BMVC 2022)
- **Model.** CNN features feed cascaded graph-attention regressors, initialised from a 3D mean face posed by a predicted 6-DoF head pose, so it also returns head pose. About 4.06 % NME on WFLW and about 3.0 % on 300-W full, and strong on the pose subsets. Weights are published per dataset: WFLW-98, 300W-68, MERL-RAV with visibility, and COFW. Licence reportedly BSD-3. ↔️

**Sapiens** (Khirodkar et al., Meta, ECCV 2024)
- **Model.** ViTs of 0.3–2 B parameters, pretrained on about 300 M human images at 1024 px. The pose head outputs 308 keypoints, about 243 of them facial, *including ears*. Robust in profile. 🧠
- **Cost and licence.** Weights take about 1.2–8 GB in fp32, and CPU inference takes seconds to minutes. The custom licence is believed to be non-commercial. ↔️

**Dense landmarks** (Wood et al., ECCV 2022, Microsoft)
- **Method.** 703 landmarks over the whole head. Each predicts a 2D mean and an isotropic σ, trained with a Gaussian NLL loss on synthetic renders only (the "Fake It Till You Make It" pipeline). A 3DMM is then fitted by minimising Σ‖(π(x)−μ)/σ‖² plus priors, in real time, with NoW scores competitive for its year. 🧠
- **Availability.** Neither the model nor its weights is public, to my knowledge. FaceSynthetics (100 k images, 70 landmarks plus segmentation) is research-only. ↔️

**Benchmarks and conventions**
- **NME normalisers.** NME is the mean per-point error divided by a normaliser: outer inter-ocular distance (IOD) on 300-W and WFLW, sometimes inter-pupil distance, and √(w·h) of the box on AFLW2000-3D. Results under different normalisers are not comparable. 🧠
- **Dataset sizes.** 300-W has 68 points, with common (554), challenging (135) and full (689) test sets. WFLW has 98 points over 7,500 training and 2,500 test images, split into pose, expression, illumination, make-up, occlusion and blur subsets. AFLW2000-3D has 2,000 images with noisy 3DDFA-fitted labels. 🧠
- **2D vs 3D convention.** In 2D-convention sets (300-W, WFLW), jaw points sit on the *visible outline* and slide over the skin as yaw changes. In 3D-convention outputs (3D-FAN, AFLW2000-3D, the MediaPipe mesh), each index is a fixed surface point even when it is hidden. 🧠
- **Anisotropic error.** Contour points err mostly *along* the contour. This semantic ambiguity is what ADNet (ICCV 2021) and STAR (CVPR 2023) target. 🧠
- **Detector vs anthropometric definitions.** The inner eye corner sits at the caruncle edge rather than at endocanthion. The nose tip follows the highlight. Brow points follow hair. Expect 1–3 mm systematic offsets. 🧠

## Numbers & reference tables

**Table 1: Detector cards.** CPU time is an order of magnitude for one face on a recent laptop, detection excluded. "Weights" covers the weights and their training data.

| Detector | Points | Convention | Input | CPU time | Usable yaw | Code / weights licence | Status |
|---|---|---|---|---|---|---|---|
| MediaPipe Face Landmarker | 478 (+52 scores, 4×4) | 3D mesh, relative z | ~256 px crop | ~2–20 ms | ±60–70° | Apache-2.0 / Apache-2.0 | ↔️ |
| dlib ERT 68 | 68 | 2D | full image | ~1–3 ms | ±30–40° | BSL-1.0 / 300-W non-commercial [2][3] | ✅ |
| FAN / 3D-FAN | 68 (+z) | 2D / 3D | 256 px | 0.1–1 s | ±90° (3D) | BSD-3 / research data | 🧠 |
| HRNetV2-W18 | 68 / 98 | 2D | 256 px | ~10–50 ms | ~±60° | MIT / research data | 🧠 |
| SPIGA | 98 / 68 + head pose | 2D (+visibility) | 256 px | ~50–300 ms | ~±90° | BSD-3? / research data | ↔️ |
| PIPNet | 68 / 98 | 2D | 256 px | ~5–30 ms | ~±60° | MIT / research data | 🧠 |
| InsightFace 2d106 / 1k3d68 | 106 / 68 3D | 2D / 3D | 192 px | ~5 ms (ONNX) | ~±75° | MIT / non-commercial models | 🧠 |
| 3DDFA_V2 | 68 (dense BFM) | 3D | 120 px | ~5–20 ms | ±90° | MIT / BFM non-commercial | 🧠 |
| Sapiens pose | 308 (≈243 face) | 2D | 1024×768 | s–min | ±90° | custom, NC? | ↔️ |
| Wood et al. 2022 | 703 + σ | 3D dense | n/s | real-time | full head | unreleased | 🧠 |

**Table 2: Benchmark NME (% of outer IOD).** Values as commonly tabulated in later papers, ±0.1–0.2. Population: in-the-wild web photos.

| Method | 300-W common | 300-W challenging | 300-W full | WFLW full | Status |
|---|---|---|---|---|---|
| ERT (dlib-style) | – | – | ≈6.4 | – | 🧠 |
| LAB 2018 | ≈3.0 | ≈5.2 | ≈3.5 | ≈5.3 | 🧠 |
| HRNetV2-W18 | ≈2.9 | ≈5.2 | ≈3.3 [6] | ≈4.6 [4] | 📄 |
| PIPNet-R101 | ≈2.8 | ≈4.9 | ≈3.2 | ≈4.3 | 🧠 |
| ADNet 2021 | ≈2.5 | ≈4.6 | ≈2.9 | ≈4.1 | 🧠 |
| SPIGA 2022 | ≈2.6 | ≈4.7 | ≈3.0 | ≈4.06 | 🧠 |
| STAR 2023 | ≈2.5 | ≈4.3 | ≈2.9 | ≈4.0 | 🧠 |
| Best 2023–25 | – | – | ≈2.8 | ≈3.9–4.0 | ↔️ |
| WFLW pose subset, 2021–23 methods | – | – | – | ≈6.5–8 | ↔️ |
| MediaPipe Face Mesh (own protocol, 2019) | – | – | – | MAD ≈3–5 % | ↔️ |

**Table 3: NME to millimetres** (adult sizes after Farkas 1994).

| Normaliser | Adult size | 1 % ≈ | 4 % NME ≈ | Status |
|---|---|---|---|---|
| Outer IOD (ex–ex) | 85–95 mm | 0.85–0.95 mm | 3.4–3.8 mm | 🧠 |
| Inter-pupil | 58–70 mm | 0.6–0.7 mm | 2.4–2.8 mm | 🧠 |
| √(w·h) of the 68-point box | 120–140 mm | 1.2–1.4 mm | 4.8–5.6 mm | 🧠 |
| Inner-face / contour vs full NME | ≈0.5–0.7× / ≈1.5–2× | – | – | 🧠 |

**Table 4: Anatomical mapping** (0-based indices; MediaPipe "left" = subject's left; verify visually before freezing).

| Anthropometric point | dlib-68 | MediaPipe 478 | Reliability | Status |
|---|---|---|---|---|
| Exocanthion R / L | 36 / 45 | 33 / 263 | high | 🧠 |
| Endocanthion R / L | 39 / 42 | 133 / 362 | high (caruncle offset) | 🧠 |
| Iris centre R / L | – | 468 / 473 | high (478 mode) | ↔️ |
| Lid apex upper / lower, R | 37–38 / 40–41 | 159 / 145 | medium | 🧠 |
| Lid apex upper / lower, L | 43–44 / 46–47 | 386 / 374 | medium | 🧠 |
| Sellion region | 27 | 168 | low along bridge | 🧠 |
| Pronasale | 30 | 1 (or 4) | medium (lighting) | 🧠 |
| Subnasale | 33 | 2 (or 94) | medium-high | 🧠 |
| Alar region R / L | 31 / 35 | 129/358, 64/294 or 48/278 | medium | ↔️ |
| Cheilion R / L | 48 / 54 | 61 / 291 | high | 🧠 |
| Labrale superius / inferius | 51 / 57 | 0 / 17 | high | 🧠 |
| Stomion | mean(62, 66) | mean(13, 14) | high if closed | 🧠 |
| Soft-tissue gnathion | 8 | 152 | contour-like | 🧠 |
| Face outline | 0–16 | oval incl. 234 / 454 | contour only | 🧠 |
| Upper forehead (not trichion) | – | 10 | low | 🧠 |
| Brows | 17–26 | 70, 105, 107 / 300, 334, 336 … | hair feature | 🧠 |

**Table 5: Observation noise** (design defaults, % of image outer IOD).

| Class | σ normal | σ tangent | Status |
|---|---|---|---|
| Iris centre | 1.0 | 1.0 | 🧠 |
| Canthi, cheilia, labrale, subnasale | 1.5 | 1.5 | 🧠 |
| Lid and lip contours | 2 | 5 | 🧠 |
| Pronasale | 2.5 | 2.5 | 🧠 |
| Sellion (horizontal / vertical) | 2 | 4 | 🧠 |
| Brows | 3–5 | 6 | 🧠 |
| Jaw / oval | 2.5 | 10–15, or a silhouette term | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Shoot for the detector.**
   - Neutral expression, eyes on the lens, glasses off, hair clear of brows, forehead and ears.
   - Landmark views: frontal, ±20–30° and ±45°.
   - Profiles at ±90° go to silhouette tracing (`face3d/fit/silhouette.py`), where MediaPipe and dlib fail.
   - Beards turn jaw points into beard-outline points.
2. **Pre-process.**
   - Apply EXIF orientation.
   - Un-mirror front-camera selfies, or left and right swap.
   - Undistort wide-angle shots.
   - Crop with a 25–50 % margin and map coordinates back in float.
   - MediaPipe resamples the face to about 256 px, so above an IOD of about 150 px extra resolution adds nothing. 🧠
3. **Run out of process.** Blender bundles NumPy but not MediaPipe or OpenCV (`blender/blender-version-status-2026.md`). Run in `IMAGE` mode with `num_faces=1`. Write JSON holding the scheme, detector version, model hash, image size and flip/orientation flags. MediaPipe wheels lag new CPython releases, so check this for each release. 🧠
4. **Gate expression with blendshapes.** Starting thresholds, uncalibrated: `jawOpen` < 0.08, `mouthSmile*` < 0.15, `eyeBlink*` < 0.35, `browInnerUp` < 0.2. Compare against the subject's most neutral photo, not against zero. 🧠
5. **Inspect in Blender.** Set up one camera per photo with a background image. Draw landmarks as empties with σ-sized circles, coloured by augmentation spread. Check the nose tip and inner canthi at 400 %; they are the usual 1–3 mm offenders.
6. **Set σ in pixels.** In a 3024×4032 portrait with a face about 1,360 px wide, IOD ≈ 880 px, so 1 % ≈ 9 px ≈ 0.9 mm and anchors get σ ≈ 13 px. The engine's `sigma_px = 1.0` default is about 13× too tight. That over-weights reprojection about 170× against the mm-based priors in `face3d/solve/bundle.py`. 🧠
7. **What goes wrong.**
   - Left/right swaps, from mirrored selfies or iris indices.
   - Detections snapping to glasses frames or a fringe.
   - Point 10 read as the hairline.
   - Beard or fat outlines taken for the jaw.
   - Parted lips biasing stomion.
   - Side light dragging the nose tip toward the highlight.
   - Above all, mean-face bias flattening distinctive noses, chins and eye tilt. Landmarks get within a few mm; silhouette and photometric terms must finish the likeness.

## Algorithmic implications

- **Input schema.** `LandmarkSet{scheme, detector_version, uv_px[N,2], cov_px[N,2,2], visible[N], z_rel[N]?, image_wh, iod_px, orientation, mirrored}`. Branch on `scheme`, never on N. 🧠
- **σ.** Store σ in IOD fractions (Table 5) and convert to pixels per view. Contour classes get anisotropic covariance: Σ = R·diag(σ_n², σ_t²)·Rᵀ, with the tangent taken from neighbouring points. 🧠
- **Correlated dense outputs.** MediaPipe's 478 points share one regression and a mesh prior. Either keep 80–120 semantically distinct points, or inflate every σ by √(N/N_eff) with N_eff ≈ 60–100 (a factor of about 2.2–2.8). 🧠
- **Wood-style uncertainty from test-time augmentation.**
  - Run 6–10 passes: flip with an L/R permutation, scale ×0.9–1.1, rotate ±10°, shift ±3 %.
  - Use σ = max(σ_class, spread). Add a second detector's disagreement in quadrature.
  - This is cheap on CPU with MediaPipe. 🧠
- **Left/right correspondence.**
  - Build the permutation by mirroring the canonical mesh (x→−x, nearest vertex).
  - Assign iris left/right geometrically, by which eye-corner pair encloses each iris centre. Do not trust documented index ranges. 🧠
- **Visibility.**
  - After the first PnP, take each landmark's template normal *n* and view direction *v*.
  - Weight 0 when n·(−v) < cos 80°, ramping up to full weight at cos 60°.
  - Drop far-side oval points when |yaw| > 25°.
  - Never use returned-but-occluded MediaPipe points. 🧠
- **Residual type by convention.** 2D-convention jaw and oval points become silhouette residuals, re-associated each iteration. Fixed-vertex residuals are only for visible 3D-convention points. 🧠
- **Robust loss.**
  - Huber with δ = 2σ (in px, replacing the fixed 3 px).
  - After convergence, drop points beyond 4σ and re-solve.
  - Flag views with more than 15 % of points rejected. 🧠
- **Calibrate detector semantics.**
  - Render the template (e.g. MPFB2) in Blender from 20–50 known cameras and run the detector on the renders.
  - Store each index's mean landing point as barycentric coordinates per (scheme, detector version, template version).
  - This removes systematic offsets that averaging across views cannot. 🧠
- **Never shape evidence.** MediaPipe z, the transform's translation and scale, and the canonical model. The transform's rotation may seed PnP when |yaw| < 60°. Scale comes from the iris (11.7 ± 0.5 mm), the IPD (63 ± 3.5 mm) or a measured value, as `blender/blender-face-addons.md` specifies. 🧠
- **Bias outweighs noise.** Noise falls as 1/√k over k views; mean-face bias does not. Beyond about 4 views, invest in calibration and silhouettes rather than a better detector. 🧠
- **Future detector.** A Wood-style dense σ-predicting model trained on renders of CC0 MPFB2 heads. Correspondence would hold by construction and the licence would be clean. 🧠

## Disagreements, myths & open questions

- **Myth: "More landmarks, more accuracy."** Correlated, prior-driven points add confidence, not information, unless σ is modelled. 🧠
- **Myth: "Lowest NME = best detector."** NME measures agreement with in-the-wild 2D annotation. This task needs consistency across views of one neutral face, plus anatomical meaning. A 0.1 % WFLW gap is noise next to 1–3 mm convention offsets. ↔️
- **Myth: "MediaPipe gives metric 3D."** z and the transform are relative or canonical-scaled. 🧠
- **"dlib is free for commercial use."** True of the code, not of the 68-point model. ↔️
- **Weights trained on research-only data.** Their commercial status is legally unsettled. Treat FAN, HRNet, SPIGA, PIPNet and STAR as optional, user-installed, research-only. ↔️
- **Open questions.**
  - Sapiens licence and successors.
  - Any public reimplementation of Wood et al.
  - MediaPipe's current model version, input size and Python support.
  - Measured MediaPipe error against yaw on controlled portraits; the calibration renders can provide it.
  - 2025–26 detectors not covered here.

## Sources

1. https://developers.googleblog.com/en/mediapipe-3d-face-transform/ (MediaPipe 3D Face Transform: z relative, scaled like x)
2. https://github.com/davisking/dlib-models (dlib models README: 300-W licence excludes commercial use)
3. https://ibug.doc.ic.ac.uk/resources/facial-point-annotations/ (iBUG annotations: research use only)
4. https://arxiv.org/pdf/2104.03100 (HIH paper: HRNetW18C WFLW 4.60)
5. https://arxiv.org/pdf/2306.02763 (STAR paper: STAR 4.02, ADNet 4.14 on WFLW)
6. https://arxiv.org/pdf/2508.14929 (Heatmap Regression without Soft-Argmax: HRNet 300-W full 3.32)
7. https://arxiv.org/pdf/2210.07233 (SPIGA paper: 300-W 2.99; WFLW 4.06 not seen)
8. https://sources.debian.org/src/dlib/20.0%2Bdfsg-2/python_examples/face_landmark_detection.py (dlib example: commercial-use warning); Debian copyright file lists CC0 for the .dat

**Further reading (by name, not yet linked)**
- Kartynnik et al. — Real-time Facial Surface Geometry from Monocular Video on Mobile GPUs, CVPR Workshops 2019
- Grishchenko et al. — Attention Mesh: High-fidelity Face Mesh Prediction in Real-time, CVPR Workshops 2020
- Ablavatski et al. — Real-time Pupil Tracking from Monocular Video for Digital Puppetry (MediaPipe Iris), 2020
- Kazemi & Sullivan — One Millisecond Face Alignment with an Ensemble of Regression Trees, CVPR 2014
- Sagonas et al. — 300 Faces In-The-Wild Challenge: database and results, Image and Vision Computing 2016
- Bulat & Tzimiropoulos — How far are we from solving the 2D & 3D Face Alignment problem?, ICCV 2017
- Wang et al. — Deep High-Resolution Representation Learning for Visual Recognition, TPAMI 2020
- Wu et al. — Look at Boundary: A Boundary-Aware Face Alignment Algorithm (WFLW), CVPR 2018
- Huang et al. — ADNet: Leveraging Error-Bias Towards Normal Direction in Face Alignment, ICCV 2021
- Zhou et al. — STAR Loss: Reducing Semantic Ambiguity in Facial Landmark Detection, CVPR 2023
- Kumar et al. — LUVLi Face Alignment: Estimating Landmarks' Location, Uncertainty, and Visibility Likelihood, CVPR 2020
- Jin, Liao & Shao — Pixel-in-Pixel Net: Towards Efficient Facial Landmark Detection in the Wild, IJCV 2021
- Prados-Torreblanca, Buenaposada & Baumela — Shape Preserving Facial Landmarks with Graph Attention Networks, BMVC 2022
- Khirodkar et al. — Sapiens: Foundation for Human Vision Models, ECCV 2024
- Wood et al. — 3D Face Reconstruction with Dense Landmarks, ECCV 2022
- Wood et al. — Fake It Till You Make It: Face Analysis in the Wild Using Synthetic Data Alone, ICCV 2021
- Zhu et al. — Face Alignment Across Large Poses: A 3D Solution, CVPR 2016
- Guo et al. — Towards Fast, Accurate and Stable 3D Dense Face Alignment (3DDFA_V2), ECCV 2020
- Farkas — Anthropometry of the Head and Face, 1994

## Verification log (2026-11-20)

- MediaPipe face_landmarker.task weights Apache-2.0 per model card; wheel/CPython support: unconfirmed. Search found only a third-party Hugging Face copy that points to the BlazeFace card; no official card text seen. Badge left as is.
- dlib 68-point model trained on 300-W, not for commercial use: confirmed (✅). Sources: https://github.com/davisking/dlib-models, https://ibug.doc.ic.ac.uk/resources/facial-point-annotations/, https://sources.debian.org/src/dlib/20.0%2Bdfsg-2/python_examples/face_landmark_detection.py. Caveat: Debian lists the .dat as CC0, so legal status is still murky. The 5-point model claim was not checked.
- MediaPipe z relative, scaled like x: confirmed (📄) https://developers.googleblog.com/en/mediapipe-3d-face-transform/. Canonical model in cm and the ~63 deg legacy vertical FOV: unconfirmed (the blog confirms an assumed virtual perspective camera, no value); transform-matrix badge stays ↔️.
- WFLW/300-W NME: HRNetV2-W18 WFLW 4.60 confirmed (https://arxiv.org/pdf/2104.03100) and 300-W full 3.32 confirmed (https://arxiv.org/pdf/2508.14929), so the row is 📄. STAR 4.02 and ADNet 4.14 on WFLW confirmed (https://arxiv.org/pdf/2306.02763), consistent with the table's rounded values; their rows stay 🧠 because the 300-W values were not checked. SPIGA WFLW 4.06 unconfirmed (300-W 2.99 seen, https://arxiv.org/pdf/2210.07233). STAR 300-W full 2.87 and the "best 2023-25" range unconfirmed.
