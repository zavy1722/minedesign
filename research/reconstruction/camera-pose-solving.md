# Solving camera pose and intrinsics from face images

> Every photo needs its own camera: rotation, translation, focal length in pixels, principal point and, rarely, lens distortion. For faces these come from perspective-n-point (PnP) against a template landmark set, then a bundle adjustment (BA) that shares one 3D shape across photos. Pose is easy; focal length is hard. A face is only about 10–12 cm deep, so beyond roughly 1 m a long lens far away and a short lens nearer give nearly identical landmarks, and the face's unknown depth trades off against distance (the focal/depth ambiguity). Therefore fix the focal length or give it a strong prior (EXIF, calibration, or background vanishing points via fSpy), shoot views across ±60° or more of yaw, and trust single-view focal estimates only at selfie distance. In engine simulations, multi-view shape stays accurate even when per-view focal is badly wrong; a frontal-only fit has about twice the shape error.
>
> Evidence status: 4 ✅ / 16 📄 / 56 🧠 / 9 ↔️ — 🧠 items are queued for web verification.

## Key facts

**PnP solvers**
- **EPnP** is a non-iterative PnP solver for n ≥ 4 points. OpenCV credits `SOLVEPNP_EPNP` to Moreno-Noguer, Lepetit and Fua [1], and PyPose ships an EPnP module [2]. 📄 EPnP expresses every point through 4 virtual control points, which makes it O(n), and it is weak on near-planar or small point sets. Standard practice is to initialise with EPnP or SQPnP, then refine with Levenberg–Marquardt (LM). 🧠
- `SOLVEPNP_DLS` is documented as broken and falls back to EPnP [1] 📄 (snippet). `SOLVEPNP_UPNP` also falls back to EPnP [25] 📄 and does not estimate focal length in OpenCV. 🧠 P3P has up to 4 solutions (Gao et al. 2003). OpenCV's P3P/AP3P take exactly 4 points, using the 4th to choose among them. 🧠
- PnP expects undistorted landmark coordinates [1]. 📄
- **Unknown-focal solvers:** P4Pf (Bujnak et al. 2008), P3.5Pf (Wu 2015), UPnP (Kneip et al. 2014) and EPnPfr (Penate-Sanchez et al. 2013). Several are in PoseLib and pycolmap. For 40–100 noisy, near-planar face landmarks, multi-hypothesis LM over log f (`face3d.solve.pnp.solve_pnp`) is simpler and adequate. 🧠
- **Heuristic vs calibration:** Bengal-HP_RU solves head pose from 6 landmarks with f = image width and the principal point at the image centre [3] 📄. A 2022 perspective face-reconstruction paper calibrates K offline instead [4] 📄. ↔️ The f = width rule depends on orientation: it corresponds to about 35 mm-equivalent for a 4:3 landscape image but about 26 mm for 3:4 portrait, and it is 2–5× too short for tele portraits. 🧠

**Focal/depth ambiguity**
- Facial perspective is set by **camera distance**. Focal length matters only because it dictates how close you stand [5][6]. Portrait distortion is modelled and corrected as a function of distance [7][8]. ✅
- **Mechanism:** a point at depth z behind distance d projects as u = f·X/(d+z) ≈ (f/d)·X·(1 − z/d). The scale f/d is well determined; the perspective term z/d is small. If the face's depth is unknown by a factor α, only αΔ/d is observable, so depth and distance are confounded and f = (f/d)·d inherits the error. 🧠
- Bas & Smith show that perspective 2D landmarks fit a family of different 3D shapes at different distances almost equally well, so landmarks alone cannot pin down distance or depth-related shape [18]. 🧠 (my summary; the harvest did not extract this result)
- **Engine simulation (Tables 6–7):** for an unknown face in a single view, focal is recoverable to about 10–17% at selfie range and not at all at 2 m. With 5 views spanning ±60° yaw, shape RMSE is about 1.2 mm at every distance, even when focal is wrong. 🧠
- An unidentified study (snippet) rated faces shot at 50 mm as less sex-typical, attractive and dominant than at longer focal lengths [9]. 📄 Ward et al. (2018, "selfie effect") reported about 30% wider noses at 30 cm than at 1.5 m. 🧠 Pinhole arithmetic gives 15–27% (Table 3), and occlusion of the face's sides probably adds the rest. 🧠 Arm's-length selfies help [6]. 📄 Up close the ears hide behind the cheeks, so a frontal photo with no visible ears was taken close. 🧠

**Vanishing points, fSpy, BLAM**
- Two orthogonal vanishing points (VPs) are the minimum needed for a closed-form focal length [14]. 📄 With p the principal point, f² = −(v₁−p)·(v₂−p) (Caprile & Torre 1990), and with three VPs, p is the orthocentre of the VP triangle. 🧠
- One paper says 3 VPs are needed for pose and 4 for pose plus focal [15]. That conflicts with its own two-VP title and with [14]; the count depends on whether orthogonality and the principal point are assumed. ↔️
- BLAM is discontinued, and its maintainers point to fSpy. BLAM's single-VP mode needs a known focal length [10][11]. 📄
- fSpy is a standalone open-source app (1–2 VPs, `.fspy` export, a separate Blender importer). The official Blender importer's latest tagged release is v1.0.3 [26] 📄, which requires Blender 2.80 or newer, and the importer is GPL-3.0 [27] 📄. The release date, the desktop app's own version and compatibility with Blender 4.x/5.x are still unverified (a community fork says the official add-on is not good with contemporary Blender). 🧠 (verify; see `blender/reference-camera-setup.md`) Faces have no straight edges, so VPs must come from the background (door frames, tiles). Use them as a **focal prior**. A wall facing the camera squarely gives one VP and no focal information. 🧠

**Bundle adjustment and fusion**
- multiview_calib calibrates intrinsics per camera with OpenCV, then solves extrinsics linearly and refines them with BA [12]. 📄 Marginalized BA (2026) jointly optimises per-camera K_i and poses, initialising unknown intrinsics from DUSt3R pointmaps [13]. 📄
- BA can fail to converge from poor initial values [21]. 📄 Landmark-only BA also has a 7-DoF similarity gauge (rotation, translation, scale), which you fix with a template prior or a measured length (Triggs et al. 2000; Hartley & Zisserman 2004). 🧠

**Procrustes**
- Faces are aligned by a similarity transform (s, R, t). Generalized Procrustes analysis (GPA) removes all three while iterating to the mean [16], and 3DMM landmark fitting estimates s, R and t [17]. ✅ Scale is handled inconsistently: removed [16], not modelled [18], fitted [17], or made anisotropic [20]. ↔️
- Umeyama (1991) gives a closed form with a determinant guard against reflections. POSIT (DeMenthon & Davis 1995) iterates from scaled-orthographic to full perspective. 🧠

## Numbers & reference tables

**Table 1 — 35 mm equivalent → camera, 4032×3024 (4:3) image, diagonal convention** (`focal_px_from_35mm`; arithmetic)

| f35 (mm) | f_px | HFOV, long side (°) | Blender lens (mm; sensor 36, long-side fit) | Status |
|---|---|---|---|---|
| 13 (phone ultrawide) | 1514 | 106.2 | 13.5 | 🧠 |
| 24–26 (phone main) | 2796–3029 | 71.6–67.3 | 25.0–27.0 | 🧠 |
| 35 (≈ "f = width") | 4077 | 52.6 | 36.4 | 🧠 |
| 50 | 5824 | 38.2 | 52.0 | 🧠 |
| 77 (phone 3×) | 8970 | 25.3 | 80.1 | 🧠 |
| 85 | 9901 | 23.0 | 88.4 | 🧠 |
| 120–135 (5× / long portrait) | 13978–15726 | 16.4–14.6 | 124.8–140.4 | 🧠 |

**Table 2 — Blender lens = EXIF f35 × factor** (sensor 36 mm, long-side fit)

| Aspect | Factor | Status |
|---|---|---|
| 4:3 / 3:2 / 16:9 / 1:1 | 1.040 / 1.000 / 0.955 / 1.177 | 🧠 |
| EXIF convention (diagonal vs width) | unconfirmed; ±4–5% | ↔️ |

**Table 3 — Distance and perspective excess Δ/d** (extra magnification of the nose tip over a plane Δ behind it). "Tight" means 300 mm of head on the long side (±4%). Δ = 60 mm is roughly nose tip to canthus/cheek, Δ = 110 mm roughly nose tip to tragion; both are my adult estimates, ±15 mm.

| Setup | d (mm) | Δ = 60 | Δ = 110 | Status |
|---|---|---|---|---|
| 26 mm, tight | 217 | 28% | 51% | 🧠 |
| 26 mm, typical selfie | 350–500 | 12–17% | 22–31% | 🧠 |
| 50 mm, tight | 417 | 14% | 26% | 🧠 |
| 85 mm, tight / head and shoulders | 708 / ≈1200 | 8% / 5% | 16% / 9% | 🧠 |
| 135 / 200 mm, tight | 1125 / 1667 | 5% / 4% | 10% / 7% | 🧠 |

**Table 4 — Geometry sensitivities** (derived)

| Quantity | Values | Status |
|---|---|---|
| Two-view depth σ ÷ lateral σ = 1/(√2·sin(θ/2)), θ = 10/15/30/45/60/90° | 8.1 / 5.4 / 2.7 / 1.9 / 1.4 / 1.0 | 🧠 |
| Nose-tip shift relative to eyes (40 mm in front), pitch error 2/5/10/15° | 1.4 / 3.5 / 6.9 / 10.4 mm | 🧠 |
| Ear shift relative to nose tip (110 mm behind), same pitch errors | 3.8 / 9.6 / 19.1 / 28.5 mm | 🧠 |
| Pixel scale at IOD ≈ 520–550 px (12 MP; 26 mm at 0.35 m; 85 mm at 1.2 m) | ≈0.12 mm/px | 🧠 |

**Table 5 — Scale and noise references** (from memory; verify before use as priors)

| Quantity | Value | Population / note | Status |
|---|---|---|---|
| Interpupillary distance | mean ≈63 mm, SD ≈3.5–4 mm | adults; men slightly larger (Dodgson 2004) | 🧠 |
| Visible iris diameter | ≈11.7 ± 0.5 mm | adults; used by MediaPipe Iris [22] | 📄 |
| ID-1 card | 85.60 × 53.98 mm | ISO/IEC 7810; target for scale and focal | 🧠 |
| Automatic 68-point landmark error | NME ≈3–4% of IOD (published inter-ocular full-set results ≈2.9–3.3%) [23][24] | 300W benchmark | ✅ |
| Learned single-image head pose | MAE ≈4–6° per angle | AFLW2000/BIWI, depends on method | ↔️ |

**Table 6 — Single-view focal error, `solve_pnp`, focal free, no prior.** Uses illustrative synthetic landmarks (`face3d/synthetic.py`, contour points removed), 3000×4000 px, 40 trials. "Mismatch" means the true face is a `random_subject` (identity SD 4 mm, scale SD 4%) solved against the template.

| d (mm), f35; yaw 0°/30° | Known shape, 1% IOD noise: median / p90 | Mismatch, 2% IOD noise: median / p90 | Status |
|---|---|---|---|
| 300, 26 mm | 2% / 5–7% | 9–12% / 21–27% | 🧠 |
| 500, 26 mm | 3–4% / 7–10% | 13–17% / 35–55% | 🧠 |
| 1000, 50 mm | 8–9% / 17–19% | 38–45% / 139–171% | 🧠 |
| 2000, 85 mm | 11–13% / 31–32% | 45–93% / diverges | 🧠 |

**Table 7 — Multi-view BA, `reconstruct_landmarks`.** 5 views at yaw −60…60° (pitch SD 5°), far-side points hidden beyond 35°, 2% IOD noise, template σ 6 mm, 12 subjects.

| d (mm), f35 | Focal prior | Per-view focal error, median / p90 | Landmark RMSE | Status |
|---|---|---|---|---|
| 400, 26 | none | 9% / 24% | 1.2 mm | 🧠 |
| 1000, 50 | none | 16% / 622% | 1.2 mm | 🧠 |
| 2000, 85 | none | 73% / diverges | 1.2 mm | 🧠 |
| 1000–2000 | generic 50 mm, σ_log 0.35 | 10–45% / 25–71% | 1.3 mm | 🧠 |
| 400–2000, frontal only | none | 8–63% / 20%–diverges | 2.5–3.0 mm | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Capture:** one camera, one zoom setting, with focus and zoom locked. Neutral expression, hair off the ears and forehead. Shoot yaw 0°, ±30°, ±45° and ±90°, plus pitch ±15–20° (chin underside, brow and skull). Views only 10–15° apart give 5–8× worse depth than lateral precision (Table 4).
2. **Distance depends on what you know.** If the focal length is calibrated, 0.4–0.6 m is fine and even informative. If it is unknown, shoot from 1–1.5 m or farther with a 2–3× tele. Perspective then barely matters (Table 3), and the spread of views carries the depth (Table 7).
3. **Calibrate once:** use OpenCV `calibrateCamera` (Zhang checkerboard, 10–20 shots) at the same zoom setting and a similar focus distance. Focus breathing shifts f by a few percent. 🧠 A shortcut is one oblique shot of an ID-1 card or a door frame, which gives f if the principal point is assumed central.
4. **EXIF:**
   - Apply the orientation tag before placing landmarks.
   - Convert `FocalLengthIn35mmFilm` with `focal_px_from_35mm`. It uses the diagonal, so orientation does not matter.
   - A crop invalidates both the 35 mm value and the centred principal point.
   - Digital-zoom tagging varies by phone. 🧠
   - Stabilised video warps every frame.
   - Messaging apps strip EXIF.
5. **Mirrored selfies:** front cameras often save mirror images. No rotation explains a mirror image, but a symmetric template still fits it, so moles and partings land on the wrong side. Check one asymmetric feature, or let the engine try both flips.
6. **Landmarks:**
   - Drop jawline and silhouette points (iBUG 0–16), which slide with yaw, or use them as silhouette constraints.
   - Delete far-side points hallucinated beyond about 30–40° of yaw.
   - Down-weight mouth corners and brows.
   - Rigid anchors: canthi, nasion, pronasale, subnasale, alare, tragion.
7. **Pitch is the weakest angle.** A 10° error moves the nose tip about 7 mm and the ear about 19 mm (Table 4), which mimics a wrong nose length or ear height. Judge those from the ¾ and profile views.
8. **Blender:**
   - One camera per photo. Resolution = photo pixels, Sensor Fit Horizontal, `lens = f_px·36/W`, and shift from the principal point (`to_blender_camera`).
   - Never type EXIF f35 straight into the lens field; it is 4–18% off (Table 2).
   - Bind cameras to timeline markers (Ctrl+B) to flip between photos.
   - UI details: `blender/reference-camera-setup.md`.
9. **Accept a view** when reprojection RMSE is ≲2–3% of IOD (detector landmarks) or ≲1% (hand-placed pins), **and** the silhouette and ears match. If interior points match but the silhouette does not, the focal length and distance are wrong.
10. **Mixing sessions:**
    - Give each body/lens/zoom combination its own intrinsics.
    - Share identity only through rigid anchors. Weight, age (more than 1–2 years apart), facial hair and glasses change soft contours.
    - A 30 cm selfie and an 85 mm portrait differ by 15–30% in apparent nose width, so solve each photo's distance first.

## Algorithmic implications

**Priors and defaults** (tune on held-out real captures)

| Parameter | Default | σ / rule | Status |
|---|---|---|---|
| log f, EXIF f35, uncropped | EXIF value | σ_log 0.04–0.06 | 🧠 |
| log f, calibrated / VP-derived | calibration / fSpy | σ_log 0.01–0.02 / 0.05–0.10 | 🧠 |
| log f, unknown | 50 mm-equivalent | σ_log 0.5–0.7; hypotheses {13, 24, 35, 50, 85, 135, 200} | 🧠 |
| Principal point, skew, aspect | centre, 0, 1 | fixed unless crop metadata exists | 🧠 |
| k1, k2 | 0 | fixed for phone main-camera JPEG/HEIC; k1 free (σ ≈ 0.1) for ultrawide/webcam | 🧠 |
| Landmark σ_px | 0.025·IOD_px (detector); 0.01·IOD_px (manual) | 3× for contour points | 🧠 |
| Huber threshold | 2.5·σ_px | relative, not absolute px | 🧠 |
| Global scale | IPD 63 ± 3.5–4 mm; measured IPD ± 0.5–1 mm; iris 11.7 ± 0.5 mm | if none available, output "proportions only" | 🧠 |
| Tagged-view yaw | tag | σ 15–20° | 🧠 |
| Distance: selfie / portrait | 0.35 m / 1.5 m | σ_log 0.3–0.5 | 🧠 |

- **Engine gaps found while simulating:**
  - `PhotoLandmarks`/`reconstruct_landmarks` do not pass `f_prior_log_sigma`, so EXIF priors run at the weak default of 0.35.
  - BA has one focal length per view. Add **intrinsics groups** keyed on EXIF Make/Model/FocalLength, because per-view focal diverged in Table 7.
  - `huber_px = 3.0` is an absolute pixel value.
  - The f35 hypotheses lack 13 mm.
- **Observability report:**
  - Compute the Schur-complement posterior σ for log f, distance t_z and pitch from the LM Hessian.
  - If posterior σ_logf > 0.8 × prior σ, report "focal not observable – prior used". A flat cost over a log-f sweep means the same thing.
- **Multiple solutions:**
  - Restart PnP from pitch-flipped and yaw-mirrored poses, because near-planar sets have twin solutions. Keep the best result that passes the cheirality check.
  - To detect mirroring, solve the flipped image too and compare the cost on asymmetric features.
- **Pipeline:**
  1. Landmarks and QA.
  2. Per-view PnP over focal hypotheses.
  3. Reject views with RMSE > 3% IOD.
  4. Joint BA: shared X or 3DMM β; per-view R, t; per-group f; symmetry and template priors.
  5. Silhouette-aware warp.
  6. Blender export with a round-trip reprojection test.
- **Expression:** give each view its own expression coefficients with a strong zero-mean prior. Otherwise BA absorbs non-rigid change as pose error.
- **Use SfM instead** (COLMAP-style) when you have more than 30 sharp, overlapping photos of a still subject. Landmark BA is for sparse sets of 3–15 photos, where SfM fails on low-texture skin.

## Disagreements, myths & open questions

- **"Telephoto flattens the face":** distance does that, not the lens [5][6] ✅. The perception result [9] confounds focal length with distance. ↔️
- **"Farther is always better":** distance removes distortion but also removes the focal and depth signal (Tables 6–7). That is fine with many views and harmful with one.
- **f = width [3] vs calibrated K [4]:** the heuristic depends on orientation and ignores the lens. ↔️
- **VP count [14] vs [15]:** depends on what is assumed. ↔️
- **Procrustes scale [16][17][18][20]:** for likeness, fit a uniform scale. Never use anisotropic scale for identity, because it absorbs real width-to-height differences. ↔️
- **Open questions:**
  - How accurately focal can be recovered on real faces, as opposed to synthetic ones.
  - How well learned single-image calibrators work on close-ups.
  - Whether fSpy works with current Blender.
  - How each phone writes EXIF under digital zoom.
  - The identity and sample of study [9].

## Sources

[1] OpenCV calib3d solvePnP (4.x docs) — https://docs.opencv.org/4.x/d5/d1f/calib3d_solvePnP.html — official-docs — 2026
[2] PyPose EPnP module docs — https://pypose.readthedocs.io/stable/generated/pypose.module.EPnP.html — official-docs — n.d.
[3] Bengal-HP_RU: A Dataset of Bengal People For Head Pose Estimation — https://arxiv.org/pdf/2606.24122 — paper — 2026
[4] Perspective Reconstruction of Human Faces by Joint Mesh and Landmark Regression — https://arxiv.org/pdf/2208.07142 — paper — 2022
[5] Digital Trends: lens geometry for portraits — https://www.digitaltrends.com/photography/lens-geometry-portraits/ — blog — n.d.
[6] PhotographyLife: does focal length distort subjects — https://photographylife.com/does-focal-length-distort-subjects — blog — n.d.
[7] Valente et al., Perspective Distortion Modeling (CVPR Workshops 2015) — https://openaccess.thecvf.com/content_cvpr_workshops_2015/W02/papers/Valente_Perspective_Distortion_Modeling_2015_CVPR_paper.pdf — paper — 2015
[8] Learning Perspective Undistortion of Portraits — https://arxiv.org/abs/1905.07515 — paper — 2019
[9] PMC article on focal length and portrait perception (content not read) — https://pmc.ncbi.nlm.nih.gov/articles/3440305 — paper — n.d.
[10] perarnia/blam README — https://github.com/perarnia/blam — repo — n.d.
[11] BLAM user's guide wiki — https://github.com/stuffmatic/blam/wiki/User's-guide — repo — n.d.
[12] cvlab-epfl multiview_calib — https://github.com/cvlab-epfl/multiview_calib — repo — n.d.
[13] Marginalized Bundle Adjustment: Multi-View Camera Pose from Monocular Depth Estimates — https://arxiv.org/html/2602.18906v1 — paper — 2026
[14] Autocamera Calibration for traffic surveillance cameras with wide angle lenses — https://arxiv.org/pdf/2001.07243 — paper — 2020
[15] Pose and Focal Length Estimation Using Two Vanishing Points with Known Camera Position — https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10098530/ — paper — 2023
[16] Review of Statistical Shape Spaces for 3D Data with Comparative Analysis for Human Faces — https://arxiv.org/html/1209.6491.pdf — paper — 2012
[17] Face Frontalization Based on Robustly Fitting a Deformable Shape Model to 3D Landmarks — https://arxiv.org/pdf/2010.13676 — paper — 2020
[18] What does 2D geometric information really tell us about 3D face shape? — https://arxiv.org/html/1708.06703.pdf — paper — 2017
[19] Pose-Invariant 3D Face Alignment — https://arxiv.org/pdf/1506.03799 — paper — 2015
[20] Facial Movement Dynamics Reveal Workload During Complex Multitasking — https://arxiv.org/pdf/2603.17767 — paper — 2026
[21] US patent 12205323 (BA convergence note, snippet only) — https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12205323 — patent — n.d.
[22] MediaPipe Iris: Real-time Iris Tracking & Depth Estimation (Google Research blog) — https://research.google/blog/mediapipe-iris-real-time-iris-tracking-depth-estimation/ — official-blog — 2020
[23] LUVLi Face Alignment: Estimating Landmarks' Location, Uncertainty, and Visibility Likelihood — https://arxiv.org/pdf/2004.02980 — paper — 2020
[24] HIH: Towards More Accurate Face Alignment via Heatmap in Heatmap — https://arxiv.org/pdf/2104.03100 — paper — 2021
[25] OpenCV 4.13.0 calib3d reference (SOLVEPNP_DLS/UPNP flags) — https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html — official-docs — 2026
[26] fSpy-Blender releases (v1.0.3 latest) — https://github.com/stuffmatic/fSpy-Blender/releases — repo — n.d.
[27] fSpy-Blender README (GPL-3.0, Blender 2.80+) — https://github.com/stuffmatic/fSpy-Blender — repo — n.d.

**Further reading (by name, not yet linked):** Lepetit, Moreno-Noguer & Fua, "EPnP: An Accurate O(n) Solution to the PnP Problem" (IJCV 2009); Gao et al., P3P complete solution classification (TPAMI 2003); Terzakis & Lourakis, SQPnP (ECCV 2020); Collins & Bartoli, IPPE (IJCV 2014); Bujnak, Kukelova & Pajdla, P4P with unknown focal length (CVPR 2008); Wu, "P3.5P: Pose estimation with unknown focal length" (CVPR 2015); Kneip et al., UPnP (ECCV 2014); Penate-Sanchez, Andrade-Cetto & Moreno-Noguer, exhaustive linearization for pose and focal (TPAMI 2013); DeMenthon & Davis, POSIT (IJCV 1995); Umeyama, least-squares similarity estimation (TPAMI 1991); Horn, absolute orientation with unit quaternions (JOSA A 1987); Gower, Generalized Procrustes Analysis (Psychometrika 1975); Triggs et al., "Bundle Adjustment — A Modern Synthesis" (2000); Hartley & Zisserman, *Multiple View Geometry in Computer Vision* (2nd ed., 2004); Zhang, flexible camera calibration (TPAMI 2000); Caprile & Torre, vanishing points for camera calibration (IJCV 1990); Schönberger & Frahm, "Structure-from-Motion Revisited" (CVPR 2016); Dodgson, "Variation and extrema of human interpupillary distance" (2004); Ward et al., "Nasal distortion in short-distance photographs: the selfie effect" (JAMA Facial Plastic Surgery 2018); Fried et al., perspective-aware manipulation of portrait photos (SIGGRAPH 2016); Bryan, Perona & Adolphs, perspective distortion and social judgments of faces (PLoS ONE 2012); Třebický et al., "Focal length affects depicted shape and perception of facial images" (PLoS ONE 2016); Google MediaPipe Iris announcement (2020).

## Verification log (2026-11-20)

- EXIF FocalLengthIn35mmFilm is diagonal-based (Blender lens factors 1.040 / 0.955 / 1.177): **unconfirmed**. Secondary sources say the diagonal is the common convention (Wikipedia citing CIPA DCG-001; ExifTool's author scales by the diagonal), but the normative DC-008 text was not retrieved. Badge left as is. https://wikipedia.com/wiki/35mm_equivalent ; https://exiftool.org/forum/index.php?msg=72512
- IPD mean ≈63 mm, SD ≈3.5–4 mm (Dodgson 2004): **unconfirmed**. Secondary sources give a mean near 63 (one review cites 63.36) and an adult range of 50–75 mm, but no SD from the paper itself. Left 🧠. https://pubmed.ncbi.nlm.nih.gov/12090630/ ; https://pmc.ncbi.nlm.nih.gov/articles/PMC5497600
- 300W NME ≈3–4% of IOD: **confirmed** (✅, two independent papers). Inter-ocular full-set NME is about 2.9–3.3% for HRNet/AWing/ADNet/SLPT, slightly below the low end of the claim; inter-pupil normalisation gives about 3.8%. https://arxiv.org/pdf/2004.02980 ; https://arxiv.org/pdf/2104.03100
- Iris diameter 11.7 ± 0.5 mm (MediaPipe Iris): **confirmed** (📄, Google Research blog). https://research.google/blog/mediapipe-iris-real-time-iris-tracking-depth-estimation/

## Verification log, pass 2 (2026-11-20)

- OpenCV `SOLVEPNP_DLS` and `SOLVEPNP_UPNP` fall back to EPnP: **confirmed** (📄); the docs call both implementations broken and say EPnP is used instead. https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html
  - UPNP not estimating focal length, ITERATIVE needing 6 non-planar / 4 planar points, P3P/AP3P taking exactly 4 points, and SQPnP taking at least 3: **unconfirmed** (not in the search results). Left 🧠.
- fSpy: **partly confirmed**. The official fSpy-Blender importer's latest release is v1.0.3 (Blender 2.80+) and it is GPL-3.0 (📄). Release year, desktop app version, 1-2 VP / `.fspy` details and Blender 4.x/5.x compatibility: **unconfirmed** (a community fork, fspy_blender_ng, suggests the official add-on is dated). https://github.com/stuffmatic/fSpy-Blender/releases ; https://github.com/stuffmatic/fSpy-Blender ; https://github.com/yyc12345/fspy_blender_ng
