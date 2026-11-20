# Multi-image and video 3DMM fitting

> Multi-image or video fitting of a 3D morphable model (in practice FLAME) optimises **one shared identity vector β** against per-image camera, pose and expression. The losses are landmark reprojection and, optionally, a photometric render-and-compare term [1][2][4]. The open-source references are the Metrical Tracker (monocular, MICA identity prior), VHAP (photometric, with adaptive appearance priors) and flame-head-tracker (about 0.9–1.9 s/frame on an RTX 4090), and all three run offline [2][9]. 2026 multi-camera papers fit one FLAME parameter set to residuals from all views and report better robustness, but **no source here quantifies the gain over single-image fitting** [1][2]. From expert knowledge, the gain comes from side views turning depth (nose and chin projection, forehead slope) into image-plane measurements. It is capped by FLAME's capacity and by landmark-definition bias, and absolute scale stays unknown without a known baseline or an object of known size in shot.
>
> Evidence status: 5 ✅ / 15 📄 / 43 🧠 / 3 ↔️ — 🧠 items are queued for web verification.

## Key facts

- **Multi-view fitting solves for one parameter set across all views.** [1] fits jointly to 2D keypoints from all its cameras, and RealDenseFace's multi-view extension optimises "a single set of FLAME parameters" from correspondence residuals across views [2]. ✅
- **[1] uses keypoints from all 15 front-facing cameras of its rig.** It reports stronger geometric constraints and better robustness under hard poses and complex expressions, but gives no numeric gain [1]. 📄
- **The Metrical Tracker is an offline, optimisation-based FLAME fitter built for monocular RGB.** [1] cites it as "ZBT22", and RealDenseFace calls it, and VHAP, offline pipelines [2]. ✅
- **MICA is the shared identity prior.** [1] predicts identity shape with the MICA regressor, and flame-head-tracker credits MICA and DECA code [9]. ✅
- **Where the tracker comes from.** The harvested snippet of *Towards Metrical Reconstruction of Human Faces* covers only MICA [3]. 📄 From knowledge, that ECCV 2022 work (Zielonka, Bolkart, Thies) also presents the tracker, released as a separate "metrical-tracker" repo. It combines MICA shape, MediaPipe dense and 68-point landmarks, and photometric spherical-harmonic (SH) lighting, and INSTA and later avatar papers reuse it. 🧠
- **Scale.** A single perspective image cannot fix the face's absolute size [3]. 📄 Uncalibrated multi-view, including structure-from-motion, also recovers shape only up to a similarity transform. Millimetres need a known baseline, a known object, or a metric prior (MICA-style, or the population mean in this engine's `Priors`). 🧠
- **VHAP** aligns FLAME by photometric optimisation through differentiable mesh rasterisation. Its adaptive regional appearance priors let hair, ears, neck and shoulders align by appearance [4]. GAF (CVPR 2025) uses VHAP for FLAME tracking [7][8], and RealDenseFace describes it as FLAME plus appearance modelling [2]. ✅
- **VHAP setup:** FLAME 2023 plus vertex masks (FLAME 2020 also supported). STAR landmarks are the default; face-alignment is faster but less accurate [4]. 📄
- **VHAP's stated weak points:** photometric alignment is "versatile but sometimes sensitive", the texture needs total-variation regularisation, FLAME has limited degrees of freedom, and aligning the lower neck together with the head is especially hard [4]. 📄
- **A 2025 VHAP update batches frames for about a 3× speedup.** This was seen only on a Gitee mirror [5]. 📄
- **VHAP comes from GaussianAvatars.** From knowledge, it is the released tracking pipeline of GaussianAvatars (Qian et al., CVPR 2024). It handles NeRSemble's 16-camera captures as well as monocular video, but the multi-view support is not confirmed in [4]. 🧠
- **flame-head-tracker v4.1 (2 Aug 2025)** does single-image and monocular-video fitting offline, at about 0.9 s/frame in landmark mode and 1.9 s/frame in photometric mode on an RTX 4090. It needs an NVIDIA GPU on Ubuntu (Windows untested), and FLAME files are downloaded separately for licensing reasons [9]. A fork exists [10]. 📄
- **video-head-tracker** is licensed CC BY-NC 3.0 (non-commercial) [11]. 📄 From knowledge, it is the tracker behind *Neural Head Avatars from Monocular RGB Videos* (Grassal et al., CVPR 2022). 🧠
- **Alternatives to sparse-landmark tracking:** dense UV-to-image flow tracking [12], real-time dense UV-space priors [2], and the neural parametric head model MonoNPHM [13]. 📄
- **FLAME basics.** FLAME has 5,023 vertices and 9,976 triangles. It has joints for global rotation, neck, jaw and both eyes, with 3 axis-angle parameters each. Public releases ship 300 shape and 100 expression components, with bases scaled so that β and ψ are roughly in standard-deviation units. Coordinates are in **metres**, while this engine works in millimetres (×1000). 🧠
- **Per-frame regressors do not share identity.** DECA, EMOCA, SMIRK and MICA run per image, so β jitters from frame to frame. Taking the median of β over frames is a cheap baseline. Joint optimisation with one β is the principled version, as in Face2Face's "non-rigid model-based bundling" over keyframes. Earlier lineage: analysis-by-synthesis (Blanz & Vetter 1999), model-based stereo (Amberg et al. 2007), and region-wise fusion of per-image fits (Piotraschke & Blanz 2016). 🧠
- **Landmark-definition bias does not average away.** 2D detectors put jawline and brow points on the *visible* contour, while a 3DMM embeds fixed vertices. On turned views the contour slides, so adding views shrinks random noise roughly as 1/√N but leaves this systematic error. FLAME tooling handles it with a yaw-dependent dynamic contour embedding (RingNet/DECA code). 🧠
- **Focal length and distance trade off.** Apparent perspective scales with relative depth Δ/d. Beyond roughly 1–1.5 m (Δ/d < ~0.07–0.1), focal length and distance are nearly degenerate, and a face alone barely constrains focal length (see Table 3). 🧠

## Numbers & reference tables

**Table 1 — Open-source FLAME trackers**

| Tool | Input | Fitting signal | Speed | Licence / model | Status |
|---|---|---|---|---|---|
| flame-head-tracker v4.1 (2 Aug 2025) | single image; monocular video | landmarks, or landmarks + photometric | ~0.9 s/frame landmark; ~1.9 s/frame photometric (RTX 4090, author) | FLAME downloaded separately; repo licence unverified | 📄 [9] |
| VHAP | video; multi-view 🧠 | photometric + adaptive regional appearance priors; STAR landmarks | ~3× from frame batching (2025) | FLAME 2023 (+ masks) or 2020; repo licence unverified | 📄 [4][5] |
| Metrical Tracker | monocular RGB; multi-view extension in [1] | optimisation; MICA identity; dense + sparse landmarks, photometric/SH 🧠 | offline | licence unverified | ✅ offline [1][2]; 🧠 rest |
| video-head-tracker (philgras) | monocular video | FLAME tracking | — | CC BY-NC 3.0 | 📄 [11] |

**Table 2 — Multi-view configurations**

| Work | Views | Shared across views | Quantified gain vs 1 view | Status |
|---|---|---|---|---|
| Multi-View Face and Gesture Animation with Dynamic Gaussians (2026) | 15 front-facing cameras | single FLAME fit; MICA identity | none (qualitative only) | 📄 [1] |
| RealDenseFace multi-view extension (2026) | "all views" | single FLAME parameter set | none in snippet | 📄 [2] |
| GaussianAvatars / NeRSemble tracking (VHAP) | 16 cameras | identity and per-frame expression/pose | not known to me | 🧠 |
| MVF-Net (CVPR 2019) | 3 (front + two sides) | one 3DMM regressed from all views | reported, numbers not recalled | 🧠 |

**Table 3 — Perspective magnification of nose tip vs ear plane** (derived: ratio = 1 + Δ/d with Δ ≈ 0.10 m nose-tip-to-tragus depth, plausible adult range 0.09–0.12 m; lens = 35 mm-equivalent focal that frames ~0.45 m on the long side)

| Camera–nose distance d (m) | Nose-plane magnification vs ear plane | Lens for head-and-shoulders | Typical capture | Status |
|---|---|---|---|---|
| 0.30 | 1.33 (+33%) | ~24 mm | arm's-length selfie | 🧠 |
| 0.45 | 1.22 | ~36 mm | selfie stick / close phone | 🧠 |
| 0.60 | 1.17 | ~48 mm | close portrait | 🧠 |
| 1.00 | 1.10 | ~80 mm | portrait | 🧠 |
| 1.50 | 1.07 | ~120 mm | recommended minimum for likeness | 🧠 |
| 2.00 | 1.05 | ~160 mm | near-orthographic; focal weakly observable | 🧠 |

**Table 4 — Metric scale cues** (adult populations; inter-person SD is the floor on scale error when the cue is assumed rather than measured)

| Cue | Value | Notes | Status |
|---|---|---|---|
| Horizontal visible iris diameter | mean ≈ 11.7 mm, SD ≈ 0.4–0.5 mm | ~4% 1σ; MediaPipe Iris assumes ~11.7 mm | 🧠 |
| Interpupillary distance (far gaze) | mean ≈ 61–64 mm, SD ≈ 3–4 mm | ~5–6% 1σ; near gaze shortens it | 🧠 |
| Population-mean head template | head breadth SD ≈ 4–5% of mean | default scale of `Priors` fits | 🧠 |
| A4 sheet in shot | 210 × 297 mm (ISO 216) | exact; flat, near face plane | 🧠 |
| ID-1 card (credit card) | 85.60 × 53.98 mm (ISO/IEC 7810) | exact; hold at cheek depth | 🧠 |

**Table 5 — Suggested priors and robust scales** (starting values for a FLAME-style fitter; tune by held-out-view error)

| Term | Suggested σ / setting | Engine knob (current default) | Status |
|---|---|---|---|
| Identity β | N(0, 1) per component; flag \|β\| > 3 | new 3DMM layer | 🧠 |
| Expression ψ, neutral-tagged views | N(0, 0.3²) | per-view block | 🧠 |
| Expression ψ, expressive views/frames | N(0, 1) | per-view block | 🧠 |
| Jaw rotation, neutral views | σ ≈ 2–3° | per-view block | 🧠 |
| Crisp landmarks (eye/mouth corners, subnasale) | σ ≈ 1–1.5% of inter-ocular distance (IOD) in px | `ViewObs.sigma_px` (1.0) | 🧠 |
| Contour landmarks (jaw, brows) | σ ≈ 3–5% IOD, or sliding/dynamic | `ViewObs.weights` | 🧠 |
| Huber threshold | ~2× median residual after pass 1 | `huber_px` (3.0) | 🧠 |
| Focal, trusted EXIF | σ_log ≈ 0.05–0.10 | `f_prior_log_sigma` (0.35) | 🧠 |
| Focal, unknown | σ_log ≈ 0.35–0.5; shared for same camera and zoom | `f_prior_log_sigma` (0.35) | 🧠 |
| Bilateral symmetry | 1.5–3 mm | `Priors.sigma_sym` (2.0) | 🧠 |
| Midline | 1–2 mm | `Priors.sigma_mid` (1.5) | 🧠 |
| Independent landmark prior | 5–10 mm; replace with PCA covariance | `Priors.sigma` (8.0) | 🧠 |
| Video pose smoothness, 30 fps | rotation ≈ 0.5–2°/frame, translation ≈ 1–5 mm/frame | — | 🧠 |
| Post-3DMM per-vertex offsets | Laplacian-regularised; typically ≲ 3–5 mm | `laplacian_deform` | 🧠 |

**Planning arithmetic from [9]:** a 300-frame clip takes about 4.5 min in landmark mode and 9.5 min in photometric mode, and a 12-photo identity set takes 11–23 s (RTX 4090; resolution and iterations unknown). 📄

## Applying this to photo→3D face sculpting in Blender

1. **Capture an identity set separately from expressions.** Use one camera at one zoom setting, 1.5–2 m away with an 85–135 mm-equivalent lens. The subject holds a neutral face, lips closed, gaze at the horizon. Take frontal, ±30–45° and ±90° yaw, plus about ±15–20° pitch: from below for the jaw underside and nostrils, from above for the brow ridge. That is 7–9 photos under even light. Twenty near-frontal photos constrain depth no better than one. Shoot expressions afterwards, as video. 🧠
2. **Put metric scale in the photo.** Tape an A4 sheet or ID-1 card near cheek depth in at least two views, or measure head breadth or pupillary distance with calipers or a pupillometer. With none of these, label the result "proportions only" and expect about ±4–5% size error from the prior (Table 4).
3. **Never crop asymmetrically or resize without recording it.** Cropping moves the principal point, and digital zoom changes the effective focal length. Read the EXIF 35 mm-equivalent focal length (`focal_px_from_35mm`), keep originals, and avoid phone "portrait mode", which can switch to a tele lens and apply beauty warps.
4. **Solve cameras and landmarks jointly.** Use `reconstruct_landmarks` (PnP per photo, then `bundle_adjust`), then build each Blender camera with `to_blender_camera`. With a textured background and a still subject, an SfM solve of the full frames (e.g., COLMAP) gives better cameras. Scale them from the A4 or card.
5. **Validate in profile first.** Overlay projected landmarks and the silhouette on every photo. Profile views expose the depth errors a frontal fit cannot see: nose projection, chin projection, forehead slope, lip protrusion and ear position. Fail the fit if any view's RMSE exceeds about 2% of IOD.
6. **Mask what FLAME cannot model.** Exclude hair, beard, glasses and the neck from fitting (face parsing), and treat the neck and back of skull as rough base geometry [4].
7. **Import the fit, then sculpt.** Keep FLAME topology and vertex order. Put tracked expressions on shape keys, and put likeness detail on Multires or a separate "likeness" shape key so you can re-fit later. Use the camera-matched photos as background images on the solved cameras, not orthographic tracing.
8. **Check licences before commercial likeness work.** FLAME files are licence-gated [9], and video-head-tracker is non-commercial [11]. From knowledge, FLAME 2020 is research-only, and a 2023 "FLAME Open" variant is reportedly CC BY 4.0. 🧠 Verify this.

## Algorithmic implications

- **Parameter blocks.**
  - Shared across views: β, albedo, intrinsics per physical camera and zoom setting.
  - Per view: R, t, ψ, jaw and eye pose, SH lighting (27 values), and a per-view exposure and white-balance gain (3 values), which multi-camera photometric fitting needs. 🧠
  - Video adds velocity and acceleration priors.

  This matches [1][2][4][9].
- **Replace independent landmark priors with a covariance model.** The current `Priors` treats each landmark as independent within 8 mm. A 3DMM layer, X = μ + Bβ with a Mahalanobis prior on β, carries correlations such as nasal depth with dorsum height, so two or three views constrain the unseen depth far better. 🧠
- **Staged solve:**
  1. Rigid PnP with focal on the mean shape.
  2. Joint landmark LM over β and the per-view blocks (alternate β and ψ when starting cold).
  3. Silhouette/contour term from face-parsing masks; this is cheap in numpy and very informative in profile.
  4. Optional photometric or dense-UV refinement [2][4][12].
  5. Laplacian or RBF offsets for detail FLAME cannot reach [4].
- **Calibrated fast path.** With known extrinsics, `triangulate_points` (with visibility) and then `umeyama` give a direct 3D-to-3D β solve before the 2D refinement.
- **Focal observability gate.** If estimated d/Δ exceeds about 12 (d > ~1.2 m), lock focal to EXIF or the shared value, since otherwise focal and scale drift together.
- **Contours.** Use sliding or dynamic correspondences for jaw and brow points on |yaw| > 15°. Drop them past 60° and replace them with the silhouette term.
- **Keyframes from video.** Pick neutral frames by expression magnitude (e.g., MediaPipe blendshape scores near zero) and sharpness (variance of the Laplacian), spread over yaw −70…+70° and pitch ±20°. Use 8–15 frames, not hundreds.
- **Report confidence:** leave-one-view-out reprojection error, the spread of β over view subsets in per-vertex mm, and a scale-mode tag (calibrated / object / measured / prior) in the export metadata [3].

## Disagreements, myths & open questions

- **"More views always help."** Only views that add new directions help. Inconsistent expression, lighting or focal length between photos can worsen β. ↔️ [1] claims the benefit qualitatively, but the size of the gain is unquantified here.
- **"Multi-view gives true size."** It does not without a known baseline, object or measurement (see Scale). 🧠
- **Photometric vs landmark-plus-silhouette for identity.** Photometric terms improve alignment and expression [2][4] but are "sometimes sensitive" [4]. With uncontrolled lighting, hair or makeup, a geometric fit from well-spread views may give equal or better β. ↔️
- **The FLAME fit is not the likeness.** Capacity limits ("limited degrees of freedom" [4]) mean ears, nose detail and asymmetry need offsets or sculpting.
- **Licences.** FLAME 2023 terms, the VHAP repo licence and the Metrical Tracker repo licence are unconfirmed. ↔️
- **Open questions.**
  - Measured gain from 1 to N views in mm on a scan benchmark, landmark versus photometric.
  - Whether VHAP officially supports calibrated multi-view input.
  - The resolution and iteration settings behind the speeds in [9].

## Sources

[1] Multi-View Face and Gesture Animation with Dynamic Gaussians — https://arxiv.org/pdf/2608.04722 — paper — 2026
[2] RealDenseFace: Real-time Monocular 3D Face Reconstruction from Dense UV-space Priors — https://arxiv.org/pdf/2608.09238 — paper — 2026
[3] Towards Metrical Reconstruction of Human Faces — https://arxiv.org/pdf/2204.06607 — paper — 2022
[4] VHAP: Versatile Head Alignment with Adaptive Appearance Priors (ShenhanQian) — https://github.com/ShenhanQian/VHAP — code repository — n.d.
[5] VHAP Gitee mirror (2025 batching update) — https://gitee.com/hu-hanqing/VHAP — code mirror — 2025
[6] VHAP-mod (community fork) — https://github.com/ydvaayan/VHAP-mod — code repository — n.d.
[7] GAF: Gaussian Avatar Reconstruction from Monocular Videos via Multi-view Diffusion — https://arxiv.org/pdf/2412.10209v2 — paper — 2024
[8] GAF: Gaussian Avatar Reconstruction, CVPR 2025 supplemental — https://openaccess.thecvf.com/content/CVPR2025/supplemental/Tang_GAF_Gaussian_Avatar_CVPR_2025_supplemental.pdf — paper supplement — 2025
[9] flame-head-tracker (PeizhiYan) — https://github.com/peizhiyan/flame-head-tracker — code repository — 2025
[10] flame-head-tracker fork (tikammali) — https://github.com/tikammali/flame-head-tracker — code repository — n.d.
[11] video-head-tracker (philgras) — https://github.com/philgras/video-head-tracker — code repository — n.d.
[12] 3D Face Tracking from 2D Video through Iterative Dense UV to Image Flow — https://arxiv.org/html/2404.09819v1 — paper — 2024
[13] MonoNPHM: Dynamic Head Reconstruction from Monocular Videos — https://arxiv.org/pdf/2312.06740 — paper — 2023

**Further reading (by name, not yet linked)**
- Li, Bolkart, Black, Li, Romero, "Learning a model of facial shape and expression from 4D scans" (FLAME), SIGGRAPH Asia 2017
- Blanz & Vetter, "A Morphable Model for the Synthesis of 3D Faces", SIGGRAPH 1999
- Amberg et al., "Reconstructing High Quality Face-Surfaces using Model Based Stereo", ICCV 2007
- Piotraschke & Blanz, "Automated 3D Face Reconstruction from Multiple Images using Quality Measures", CVPR 2016
- Thies et al., "Face2Face: Real-time Face Capture and Reenactment of RGB Videos", CVPR 2016
- Wu et al., "MVF-Net: Multi-View 3D Face Morphable Model Regression", CVPR 2019
- Qian et al., "GaussianAvatars: Photorealistic Head Avatars with Rigged 3D Gaussians", CVPR 2024
- Kirschstein et al., "NeRSemble: Multi-view Radiance Field Reconstruction of Human Heads", ACM TOG 2023
- Zielonka, Bolkart, Thies, "Instant Volumetric Head Avatars" (INSTA), CVPR 2023
- Grassal et al., "Neural Head Avatars from Monocular RGB Videos", CVPR 2022
- Sanyal et al., RingNet and the NoW benchmark, CVPR 2019
- Schönberger & Frahm, "Structure-from-Motion Revisited" (COLMAP), CVPR 2016
- Hartley & Zisserman, *Multiple View Geometry in Computer Vision*, 2nd ed., 2004
- Farkas, *Anthropometry of the Head and Face*, 1994
