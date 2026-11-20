# Focal length, subject distance and perspective distortion

> Facial perspective is set by camera distance, not the lens: a feature Δ mm behind the nose tip images (1 + Δ/z)× smaller, and a longer lens only lets you stand farther back at the same framing. At selfie distance (0.25–0.4 m) pinhole geometry inflates nose width against the cheek outline by 12–19% and images the ears 20–29% smaller relative to the nose tip; the one clinical model study reports ~30%, and at 1.5–3 m the effect falls to 2–7%. Beyond ~1 m a face's own perspective no longer reveals focal length, and between-person variation in nose-to-face ratio is as large as the whole distance effect, so focal length must come from EXIF, calibration or a prior. The engine should fit each photo with a full-perspective camera parameterised by scale and inverse distance and report how observable distance was; the sculptor should judge likeness only through that matched camera, never a wide viewport or ortho tracings of near photos.
>
> Evidence status: 2 ✅ / 15 📄 / 81 🧠 / 16 ↔️ — 🧠 items are queued for web verification.

No topic harvest existed; cited URLs come from sibling harvests. Companions: `reconstruction/camera-pose-solving.md`, `blender/reference-camera-setup.md`, `community/reference-photography-protocol.md`.

## Key facts

**Geometry**
- Perspective depends only on the centre of projection: from one spot a longer lens is a crop of a shorter one, and at equal framing a longer lens means standing farther back, which is what flattens the face [1][2]. Face-specific work models and corrects portrait distortion as a function of camera distance [3][4] ✅
- Pinhole law: image scale ∝ f/z, so points Δ apart in depth image at a scale ratio of 1 + Δ/z (z to the nearer point) 🧠. Approximate adult depths behind pronasale: alar base ~20 mm, eye corners 35–45, cheek contour 60–80, tragion 90–120 (Farkas-type norms) 🧠
- **Close camera:** nose and central face enlarged against the outline, face narrower, ears smaller and tucked behind the cheeks; held high, also bigger forehead and eyes, smaller chin and jaw. **Far:** broader, flatter face, prominent ears 🧠. Drawing canons shift too: thirds and halves compress with viewing angle [18] 📄
- Three things get called "distortion": (1) distance perspective; (2) rectilinear off-axis stretch, ≈1/cos θ radially for a face θ off-axis (15% at 30°); (3) lens distortion (Brown–Conrady). A matched pinhole with the true principal point reproduces (1) and (2) 🧠; (3) must be removed first, since PnP assumes undistorted coordinates [9] 📄
- Phones correct main-camera lens distortion in-pipeline; some also warp faces near wide-frame edges (Shih, Lai & Liang 2019), which is not pinhole 🧠

**Studies that quantify it**
- **Ward et al. (2018)**, computational head model: at 12 in (~30 cm) the nasal base appears ~30% (men) / ~29% (women) wider than at 5 ft (~1.5 m) 🧠. Pure magnification gives ~12% for the nose-to-face-width ratio (Table 1) ↔️
- Snippet-level: 50 mm portraits were rated less sex-typical, attractive and dominant than longer focal lengths [5] 📄. This matches Třebický et al. (2016), who held framing constant (so distance varied) and measured shape change by geometric morphometrics 🧠; the article behind [5] is unconfirmed ↔️
- **Noyes & Jenkins (2017):** the same faces at ~0.3 m and ~2.7 m differ in configuration enough to impair unfamiliar-face matching 🧠
- Distance perspective implicitly shifts social judgements (Bryan, Perona & Adolphs 2012); distance can be regressed from landmark configuration, which people judge poorly (Burgos-Artizzu, Ronchi & Perona 2014); Fried et al. (2016) re-render portraits from new distances via a fitted 3D head 🧠. Valente et al. [3] and Zhao et al. [4] estimate and undo near-range distortion 📄

**Capture recommendations**
- Clinical photography uses 90–105 mm macro (range 85–135 mm) at ≥1 m ↔️; ID-photo standards specify ~1.2–2.5 m 🧠 (Table 4)
- "Hold the phone at arm's length" [1] 📄 helps but does not cure: at 0.5–0.6 m the nose tip still images 17–20% larger than the ear plane 🧠

**Focal length, EXIF and crop factor**
- f_px = f_mm·W/S_w = f35·√(W²+H²)/43.27 (diagonal convention, as in `face3d/geometry/camera.py`); crop factor = 43.27 mm ÷ sensor diagonal 🧠. Makers may derive f35 from the diagonal or the width, ~4% apart on 4:3 sensors ↔️ (EXIF fields: Table 5)
- "1/x-inch" sensor names are legacy tube sizes; the real diagonal is about two-thirds of the figure (a "1-inch" sensor is ~16 mm) 🧠
- EXIF focal length is the nominal infinity-focus value: unit focusing raises the effective pinhole focal length by (1 + m) (Table 3), internal focusing may lower it (breathing), and markings carry a tolerance I recall as ±5% (ISO 517) 🧠
- Blender's `lens` only means something with sensor width and fit [11] 📄; typing f35 into it is exact only for 3:2 images on a 36 mm horizontal sensor (4:3 needs ×1.040) 🧠
- The **viewport** focal length is not a camera: a community thread reports needing ~2× the camera value to match, which a maintainer disputed as a bug [12] 📄. I recall a fixed 2× viewport zoom (50 mm viewport ≈ 25 mm camera, 36 mm sensor) 🧠
- FaceBuilder sets focal length and sensor per photo automatically [15] 📄. fSpy solves focal length from vanishing lines [13]; with one vanishing point you must supply it [14] 📄. Faces have no straight edges, so vanishing points must come from the background 🧠

**Estimating focal length and distance from a face**
- Under perspective, face scale is ambiguous [10] 📄; my reading of Bas & Smith [7] is that perspective landmarks fit a family of shape-and-distance pairs almost equally well 🧠
- **Decomposition:** image scale gives f/z (IPD 63 ± 3.5–4 mm, iris 11.7 ± 0.5 mm); perspective Δ/z gives z only if the person's depth Δ is known; then f = (f/z)·z. The iris yields z only when f is known 🧠
- **Identity confounds distance:** alar width varies ~8–10% (CV) between adults, bizygomatic ~4%, so a nose-to-face ratio is uncertain by ~9–11%, as large as the whole change from 0.5 m to infinity (Table 1). One photo cannot separate a wide nose from a close camera 🧠
- Engine simulations (`camera-pose-solving.md`): single-view focal error 2–12% at 0.3 m, unobservable at 2 m; multi-view shape RMSE ~1.2 mm regardless 🧠
- The heuristic f = image width [8] 📄 means ≈35 mm-equivalent in 4:3 landscape but ≈26 mm in portrait, 2–5× too short for tele ↔️
- Learned single-image calibrators exist [16][17] 📄 but rely on scene geometry and are untested on face close-ups 🧠

**Camera models**
- In increasing fidelity: orthographic (drawings, photos ≥3–5 m); weak perspective (scaled orthographic, 6 DoF; valid while Δ/z ≲ 2–3%: whole head ≳3 m, interior points ≳1 m); paraperspective (Aloimonos 1990; off-centre faces); affine; full perspective (R, t, f); then + k1, k2 for uncorrected, ultrawide or webcam lenses 🧠. Weak-perspective image error ≈ (f/z)·X·Δ/z 🧠
- Many monocular 3DMM regressors assume weak perspective and so bake near-photo perspective into shape (bigger nose, narrower face) 🧠. Perspective-aware reconstruction calibrates K offline before PnP [6] 📄 or estimates metric shape [10] 📄
- Under weak perspective, pose is relative to the ray through the face: a face θ off-axis gets a ≈θ pose bias unless the principal point is honoured 🧠

## Numbers & reference tables

**Table 1 — Distance and frontal proportions** (pinhole arithmetic, level camera; depths alar 20, eyes 40, contour 70, tragion 100 mm; IPD 63 mm; weak-perspective residual for ear X 70 / Δ 60 mm and interior X 35 / Δ 30 mm about the eye plane)

| z to nose tip (m) | Situation | Nose-tip excess over ear plane | Nose/face-width inflation vs ∞ | IPD/face-width inflation | Weak-persp. residual, ear / interior (% IPD) | Badge |
|---|---|---|---|---|---|---|
| 0.25 | close selfie | 40% | 18.5% | 10.3% | 27 / 6.7 | 🧠 |
| 0.30 | Ward's "12 in" | 33% | 15.6% | 8.8% | 22 / 5.6 | 🧠 |
| 0.40 | selfie | 25% | 11.9% | 6.8% | 17 / 4.2 | 🧠 |
| 0.50 | arm's length | 20% | 9.6% | 5.6% | 13 / 3.3 | 🧠 |
| 1.0 | phone main, conversation | 10% | 4.9% | 2.9% | 6.7 / 1.7 | 🧠 |
| 1.5 | Ward's "5 ft", clinical | 6.7% | 3.3% | 1.9% | 4.4 / 1.1 | 🧠 |
| 2.0 | tele portrait | 5.0% | 2.5% | 1.5% | 3.3 / 0.8 | 🧠 |
| 3.0 | long tele, ortho-safe | 3.3% | 1.7% | 1.0% | 2.2 / 0.6 | 🧠 |
| 5.0 | — | 2.0% | 1.0% | 0.6% | 1.3 / 0.3 | 🧠 |

Between 0.3 and 1.5 m the geometric nose-to-face change is 12% (16% from 0.25 m), against Ward et al.'s ~30% ↔️. Detector noise is ~2–3% of the inter-ocular distance, so weak perspective falls below the noise for interior points beyond ~1 m, but for ears and contour only beyond ~2–3 m 🧠.

**Table 2 — Distance from head size in frame.** z ≈ 0.235·f35 / (34.6·h) m, where h is head height (menton–vertex, adult ≈0.21–0.25 m) as a fraction of the long side. Assumes an uncropped 4:3 photo and the diagonal convention; for 3:2 full frame use 36 instead of 34.6. Accuracy ±10–15%.

| f35 (mm) | h = 0.75 | 0.50 | 0.33 | 0.25 | 0.15 | Badge |
|---|---|---|---|---|---|---|
| 24 (front camera) | 0.22 m | 0.33 | 0.49 | 0.65 | 1.09 | 🧠 |
| 26 (phone main) | 0.24 | 0.35 | 0.54 | 0.71 | 1.18 | 🧠 |
| 48 (phone 2×) | 0.43 | 0.65 | 0.99 | 1.30 | 2.17 | 🧠 |
| 77 (phone 3×) | 0.70 | 1.05 | 1.58 | 2.09 | 3.49 | 🧠 |
| 120 (phone 5×) | 1.09 | 1.63 | 2.47 | 3.26 | 5.43 | 🧠 |
| 85 (full frame 3:2) | 0.74 | 1.11 | 1.68 | 2.22 | 3.70 | 🧠 |

**Table 3 — Other optical quantities**

| Quantity | Values | Badge |
|---|---|---|
| Off-axis stretch 1/cos θ − 1, θ = 10 / 20 / 30 / 40° | 1.5 / 6.4 / 15.5 / 30.5% | 🧠 |
| Half-diagonal FOV, f35 = 13 / 26 / 50 / 77 / 120 mm | 59 / 40 / 23 / 16 / 10° | 🧠 |
| Unit-focus gain (1+m): phone main at 0.35 m / FF 50 mm at 0.5 m / FF 85 mm at 1.5 m / FF 135 mm at 3 m / phone 5× at 2.5 m | +2.0 / +11 / +6.0 / +4.7 / +0.6% | 🧠 |
| Rounding of integer f35 at 13 / 26 / 77 / 120 mm | ±3.8 / ±1.9 / ±0.6 / ±0.4% | 🧠 |
| Diagonal vs width 35 mm convention, 4:3 sensor | ~4% | ↔️ |

**Table 4 — Capture by purpose**

| Purpose | Distance | Lens (FF-equivalent) | Nose-over-ear excess | Badge |
|---|---|---|---|---|
| Likeness/identity set | 1.5–3 m | 85–135 mm, or phone 3–5× tele | 3–7% | 🧠 |
| Clinical standard (Ettorre 2006; Yavuzer 2001; Galdino 2001) | ≥1 m, often ~1.5 m | 90–105 mm macro (85–135 seen) | ≤10% | ↔️ |
| ID/passport (ICAO guidance; ISO/IEC 19794-5, 39794-5) | ~1.2–2.5 m | not lens-specific | 4–8% | 🧠 |
| Focal-identification shot (known intrinsics only) | 0.4–0.6 m | phone main | 17–25% | 🧠 |
| Ortho tracing | ≥3 m, with solved yaw and pitch ≈0 | tele | ≤3.3% | 🧠 |
| Not for proportions | front camera at 0.25–0.5 m; any ultrawide | — | 20–40% | 🧠 |

**Table 5 — EXIF fields**

| Tag (ID) | Use | Pitfall | Badge |
|---|---|---|---|
| FocalLength (0x920A) | true f in mm | needs the real sensor width; nominal at infinity | 🧠 |
| FocalLengthIn35mmFilm (0xA405) | f35 → f_px | integer, 0 = unknown; diagonal or width; updates after aspect crop or zoom vary by vendor | ↔️ |
| FocalPlaneX/YResolution, FocalPlaneResolutionUnit (0xA20E/0xA20F/0xA210) | sensor size | often missing or wrong on phones | 🧠 |
| DigitalZoomRatio (0xA404) | crop zoom | vendor-specific | 🧠 |
| LensMake/LensModel/LensSpecification (0xA433/0xA434/0xA432) | which module, e.g. "front camera" | intrinsics-group key | 🧠 |
| Orientation (0x0112) | rotation | apply before landmarking | 🧠 |
| SubjectDistance (0x9206); maker-note focus distance | distance prior | rare and coarse; weak prior only | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Triage first:** read EXIF `LensModel` and f35, estimate distance from head size (Table 2), and label each photo selfie (<0.6 m), mid (0.6–1.5 m) or portrait (≥1.5 m). Selfie, front-camera and ultrawide shots are perspective evidence, not proportion references 🧠.
2. **New references:** 1.5–3 m with 85–135 mm-equivalent or a phone 3–5× tele; crop later rather than step closer; keep the face within 10–15° of centre (<4% stretch); lock one physical lens, since phones swap to a cropped main camera inside the tele's minimum focus distance 🧠.
3. **One camera per photo** (`blender/reference-camera-setup.md`): `lens = f_px·36/W`, Sensor Fit Horizontal, camera at the **solved distance**, photo as camera background, never scaled or offset to fit 🧠.
4. **Check distance:** solved z against Table 2 and the subject's memory. Interior features matching while ears and contour do not means f and z are wrong together (dolly-zoom symptom), not the shape 🧠.
5. **Viewport:** judge proportions at *View → Focal Length* ~100–170 mm, or sculpt in ortho and judge only through matched cameras. A head filling the default 50 mm viewport is seen from roughly selfie distance, so "fixing" the nose there makes it too small 🧠.
6. **Ortho blueprints** only from ≥3 m photos with yaw and pitch solved near 0; a 0.5 m front traced in ortho bakes in ~10% nose-to-face inflation and a 20% nose-over-ear excess 🧠.
7. **Mixed sources:** compare proportions only between photos at similar distances; to use a selfie, view the sculpt through its solved camera instead of "correcting" the photo by eye 🧠.
8. **Symptom → cause** 🧠: nose too big and face too narrow → traced a near photo; ears small or set back → close references; small chin and jaw → high-angle selfie; one cheek fuller → yaw plus near-side magnification (~15–20% at 0.5 m in ¾ view); broad, flat renders → sculpted in a wide viewport; pose off by degrees → off-centre crop with the principal point recentred.
9. **Approval renders:** people know their face from mirrors (0.4 m from a mirror is 0.8 m optically) and front cameras; show renders from ~1 m and from their favourite photo's camera, not only a 3 m tele view ↔️.

## Algorithmic implications

- **Exact reparameterisation:** u = c + s·(x + t_xy)/(1 + ρ·ẑ), with s = f/z₀ (px/mm), ρ = 1/z₀ and (x, ẑ) rotated head coordinates about a reference point (mid-eyes). Weak perspective is ρ = 0, so the solver starts there and then frees ρ; f = s/ρ; bound ρ to 0.1–5 m⁻¹ 🧠
- **Priors (log space)** 🧠:
  - f from EXIF f35, uncropped original: σ 0.04 (rounding, focus, tolerance); crop unknown: σ 0.35; no EXIF: hypotheses {13, 24, 26, 35, 50, 77, 85, 120, 135, 200} mm, σ 0.5–0.7.
  - z when f is unknown: front-camera selfie 0.35 m (σ 0.3), handheld rear main 0.8 m (σ 0.4), tele 2 m (σ 0.4), tape-measured ±5 cm.
  - Scale: IPD 63 ± 3.5–4 mm or iris 11.7 ± 0.5 mm.
- **Observability:** report P = 100 mm/z (>0.1 strong, <0.03 near-affine) and posterior σ_ρ from the Gauss–Newton Hessian. If σ_ρ > 0.5ρ, label "distance/focal from prior" and hold depth-related shape modes at their prior or other-view values so shape cannot absorb perspective 🧠
- **Single view:** expose the (ρ, depth-mode) family as a dolly-zoom slider with its cost curve, making the Bas & Smith ambiguity [7] visible 🧠
- **Intrinsics groups** keyed on (Make, Model, LensModel, f35, W, H, still/video): share log f within a group (σ 0.02); never average distances across photos 🧠
- **Off-axis faces:** store crop offsets so the original principal point survives. For weak-perspective initialisation, virtually rotate the face-centre ray onto the optical axis, initialise, rotate back; this removes the ≈θ pose bias 🧠
- **Reject or flag** 🧠: ultrawide `LensModel` or f35 < 20 mm; face centre >~25° off-axis in phone images (warp risk); front camera (run the mirror test, use the selfie z prior); distance from landmark ratios when P < 0.05.
- **Lens distortion:** undistort calibrated images before PnP [9] 📄; phone JPEG/HEIC: k fixed at 0 🧠
- **Export:** Blender camera at the solved distance (mm → m), `lens = f_px·36/W`, HORIZONTAL fit; an ORTHO camera (`ortho_scale = W/s` in scene units) only when P < 0.03 🧠
- **Feature:** "view as if from D" re-renders the fitted head with the photo projected onto it, giving distance-equalised references (after Fried et al. 2016) 🧠
- **Tests:** synthetic sweep z 0.25–5 m, f35 13–200 mm: recovered ρ and f, convergence from ρ = 0, shape error flat in P 🧠

## Disagreements, myths & open questions

- **"Telephoto flattens faces":** distance does [1][2] ✅; the perception finding [5] confounds lens with distance ↔️
- **"85 mm is undistorted":** at 1.5 m the nose tip still images ~7% larger than the ear plane 🧠
- **Selfie-effect size:** geometry 12–16% vs Ward et al. ~30% ↔️; likely the width definition, occluding-contour shift up close, and the model head 🧠
- **35 mm-equivalent convention** (diagonal or width) ↔️; **clinical lens** (85–135 mm) ↔️
- **"Weak perspective is good enough":** for benchmark landmarks at ≥1 m, not for ears, contours or any likeness source under ~2 m 🧠
- **"Farther is always better":** past ~3 m gains are tiny while focal identifiability and pixels are lost 🧠
- **The "true" face:** geometry for the mesh; for recognisability, the usual viewing distance matters (Bryan et al. 2012) ↔️
- **Source [5]:** snippet text matches Třebický et al. (2016), but the PMC number falls in the ~2012 range and could be Bryan et al. ↔️
- **Open** 🧠: Ward et al.'s exact metric and head model; how widely phones warp faces, and on which cameras; per-phone f35 tagging under digital zoom and aspect crops (time-sensitive); focal accuracy on real faces; whether the viewport 2× factor holds in Blender 5.x.

## Sources

[1] PhotographyLife: does focal length distort subjects — https://photographylife.com/does-focal-length-distort-subjects — blog — n.d.
[2] Digital Trends: lens geometry for portraits — https://www.digitaltrends.com/photography/lens-geometry-portraits/ — blog — n.d.
[3] Valente et al., Perspective Distortion Modeling (CVPR Workshops 2015) — https://openaccess.thecvf.com/content_cvpr_workshops_2015/W02/papers/Valente_Perspective_Distortion_Modeling_2015_CVPR_paper.pdf — paper — 2015
[4] Learning Perspective Undistortion of Portraits — https://arxiv.org/abs/1905.07515 — paper — 2019
[5] PMC article surfaced for focal-length/portrait perception (content not read) — https://pmc.ncbi.nlm.nih.gov/articles/3440305 — paper — n.d.
[6] Perspective Reconstruction of Human Faces by Joint Mesh and Landmark Regression — https://arxiv.org/pdf/2208.07142 — paper — 2022
[7] What does 2D geometric information really tell us about 3D face shape? — https://arxiv.org/html/1708.06703.pdf — paper — 2017
[8] Bengal-HP_RU: A Dataset of Bengal People For Head Pose Estimation — https://arxiv.org/pdf/2606.24122 — paper — 2026
[9] OpenCV calib3d solvePnP (4.x docs) — https://docs.opencv.org/4.x/d5/d1f/calib3d_solvePnP.html — official-docs — 2026
[10] Towards Metrical Reconstruction of Human Faces — https://arxiv.org/pdf/2204.06607 — paper — 2022
[11] Cameras – Blender 5.3 Manual — https://docs.blender.org/manual/en/latest/render/cameras.html — official-docs — 2026
[12] Blender's camera focal length / sensor size values inaccurate? (Blender Artists) — https://blenderartists.org/t/blenders-camera-focal-length-sensor-size-values-inaccurate/1271788 — forum — n.d.
[13] fSpy – still-image camera matching app (GitHub) — https://github.com/stuffmatic/fSpy — repo — n.d.
[14] Retiring BLAM and announcing fSpy (Blender Artists) — https://blenderartists.org/t/retiring-blam-and-announcing-fspy-a-stand-alone-camera-matching-app — forum — n.d.
[15] Revamped FaceBuilder for Blender (Blender Artists) — https://blenderartists.org/t/revamped-facebuilder-for-blender/1245723 — forum — n.d.
[16] GeoCalib: single-image calibration (arXiv 2409.06704v2) — https://arxiv.org/html/2409.06704v2 — paper — 2024
[17] Perspective Fields for Single Image Camera Calibration (CVPR 2023) — https://openaccess.thecvf.com/content/CVPR2023/papers/Jin_Perspective_Fields_for_Single_Image_Camera_Calibration_CVPR_2023_paper.pdf — paper — 2023
[18] Proko – How to Draw the Head from Any Angle — https://www.proko.com/course-lesson/how-to-draw-the-head-from-any-angle — blog — n.d.

**Further reading (by name, not yet linked):**
- Ward, Ward, Fried & Paskhover, "Nasal distortion in short-distance photographs: the selfie effect", JAMA Facial Plastic Surgery, 2018
- Třebický, Fialová, Kleisner & Havlíček, "Focal length affects depicted shape and perception of facial images", PLoS ONE, 2016
- Noyes & Jenkins, "Camera-to-subject distance affects face configuration and perceived identity", Cognition, 2017
- Bryan, Perona & Adolphs, "Perspective distortion from interpersonal distance is an implicit visual cue for social judgments of faces", PLoS ONE, 2012
- Burgos-Artizzu, Ronchi & Perona, "Distance estimation of an unknown person from a portrait", ECCV, 2014
- Fried, Shechtman, Goldman & Finkelstein, "Perspective-aware manipulation of portrait photos", ACM TOG (SIGGRAPH), 2016
- Shih, Lai & Liang, "Distortion-free wide-angle portraits on camera phones", ACM TOG (SIGGRAPH), 2019
- Aloimonos, "Perspective approximations", Image and Vision Computing, 1990
- Hartley & Zisserman, *Multiple View Geometry in Computer Vision*, 2nd ed., 2004 (affine and weak-perspective cameras)
- Brown, "Decentering distortion of lenses", Photogrammetric Engineering, 1966
- Zhang, "A flexible new technique for camera calibration", IEEE TPAMI, 2000
- Ettorre et al., standards for digital photography in cranio-maxillo-facial surgery, J Cranio-Maxillofacial Surgery, 2006
- Yavuzer, Smirnes & Jackson, "Guidelines for standard photography in plastic surgery", Annals of Plastic Surgery, 2001
- Galdino et al., on standardising digital photography, Plastic and Reconstructive Surgery, 2001
- CIPA DC-008, Exif standard (FocalLengthIn35mmFilm tag)
- ISO/IEC 19794-5 and ISO/IEC 39794-5, face image data; ICAO portrait-quality guidance for travel documents
- ISO 517, photographic lens focal-length designation and tolerances
- Farkas, *Anthropometry of the Head and Face*, 2nd ed., 1994
- Dodgson, "Variation and extrema of human interpupillary distance", Proc. SPIE, 2004
- Google MediaPipe Iris (2020; iris diameter 11.7 mm as a metric cue)
