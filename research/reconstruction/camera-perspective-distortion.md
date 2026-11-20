# Focal length, subject distance and perspective distortion

> Facial perspective is set by where the camera stands, not by the lens: image scale falls as 1/z, so a feature Δ mm behind the nose tip images (1 + Δ/z)× smaller, and a longer lens only lets you stand farther back at the same framing. At selfie distance (0.25–0.4 m) pinhole geometry inflates nose width against the cheek outline by 12–19% and shrinks the ears by a quarter or more; the one clinical model study reports ~30%, and at 1.5–3 m the effect falls to 2–7%. Beyond ~1 m a face's own perspective no longer reveals focal length, and between-person variation in nose-to-face ratio is as large as the whole distance effect, so focal length must come from EXIF, calibration or a prior. The engine should give each photo a full-perspective camera parameterised by scale and inverse distance and report how observable distance was; the sculptor should judge likeness only through that matched camera, never through a wide viewport or ortho blueprints of near photos.
>
> Evidence status: 1 ✅ / 15 📄 / 71 🧠 / 13 ↔️ — 🧠 items are queued for web verification.

No topic harvest existed; cited URLs come from sibling harvests. Companions: `reconstruction/camera-pose-solving.md`, `blender/reference-camera-setup.md`, `community/reference-photography-protocol.md`.

## Key facts

**Geometry**
- Perspective depends only on the centre of projection. From one spot, a longer lens is a crop of a shorter one. At equal framing a longer lens means standing farther away, and the distance is what flattens the face [1][2]. Face-specific work models and corrects portrait distortion as a function of camera distance [3][4] ✅
- Pinhole law: image scale ∝ f/z, so two points Δ apart in depth image at a scale ratio of 1 + Δ/z, with z measured to the nearer point 🧠. Approximate adult depths behind pronasale: alar base ~20 mm, eye corners 35–45, cheek contour 60–80, tragion 90–120 (Farkas-type norms) 🧠
- **Close-camera signature:** the nose (tip and nostrils most) and the central face are enlarged against the outline. The face reads narrower, and the ears look smaller, set back and partly tucked behind the cheeks. If the phone is held high, the forehead and eyes grow and the chin and jaw shrink. **Far-camera signature:** a broader face, flatter features and prominent ears 🧠
- Perspective also bends the drawing canons: thirds and halves compress with viewing angle [18] 📄
- Three effects are all called "distortion": (1) distance perspective; (2) rectilinear off-axis stretch, where a face θ off the optical axis is elongated radially by ≈1/cos θ (15% at 30°); and (3) lens distortion (radial and tangential, Brown–Conrady). A pinhole camera matched with the true principal point reproduces (1) and (2) 🧠. Effect (3) must be removed first, because PnP assumes undistorted coordinates [9] 📄
- Phones correct main-camera lens distortion in their processing pipelines. Some also apply face-aware warps to people near the edges of wide and ultrawide frames (Shih, Lai & Liang 2019), so those image regions are no longer pinhole 🧠

**Studies that quantify it**
- **Ward et al. (2018)**, a computational head model: at 12 in (~30 cm) the nasal base appears ~30% (men) / ~29% (women) wider than at 5 ft (~1.5 m) 🧠. Pure magnification gives ~12% for the nose-to-face-width ratio (Table 1), so the size of the effect is contested ↔️
- A snippet-level finding: 50 mm portraits were rated less sex-typical, attractive and dominant than portraits at longer focal lengths [5] 📄. The wording matches Třebický et al. (2016), who held framing constant, so distance changed with focal length, and measured the shape change with geometric morphometrics 🧠. The article behind [5] is unconfirmed ↔️
- **Noyes & Jenkins (2017):** photos of the same faces at ~0.3 m and ~2.7 m differ in configuration enough to impair unfamiliar-face matching 🧠
- Distance perspective implicitly shifts social judgements of faces (Bryan, Perona & Adolphs 2012), and distance can be regressed from landmark configuration alone, which people judge poorly (Burgos-Artizzu, Ronchi & Perona 2014) 🧠
- Fried et al. (2016) re-render a portrait from another distance via a fitted 3D head 🧠; Valente et al. [3] and Zhao et al. [4] estimate and undo near-range distortion 📄

**Capture recommendations**
- Clinical facial photography uses a long lens at ≥1 m, most often 90–105 mm macro on full frame. Recommendations span 85–135 mm (Ettorre et al. 2006; Yavuzer et al. 2001; Galdino et al. 2001) ↔️
- Passport and ID standards (ICAO portrait-quality guidance; ISO/IEC 19794-5 and its successor 39794-5) specify a camera-to-subject distance of roughly 1.2–2.5 m 🧠
- Practitioners advise holding the phone at arm's length for selfies [1] 📄. That helps without curing anything: at 0.5–0.6 m the ears are still ~17–20% too small 🧠

**Focal length, EXIF and crop factor**
- f_px = f_mm·W/S_w = f35·√(W²+H²)/43.27 (diagonal convention, as in `face3d/geometry/camera.py`); crop factor = 43.27 mm ÷ sensor diagonal 🧠. Makers may derive f35 from the diagonal or the width, ~4% apart on 4:3 sensors ↔️ (EXIF fields: Table 5)
- "1/x-inch" sensor names are legacy video-tube sizes; the real diagonal is about two-thirds of the figure (a "1-inch" sensor is ~16 mm) 🧠
- EXIF focal length is the nominal infinity-focus value. Unit focusing raises the effective pinhole focal length by (1 + m) (Table 3), internal focusing may lower it (breathing), and marked focal lengths carry a tolerance I recall as ±5% (ISO 517) 🧠
- Blender's `lens` means something only together with the sensor width and sensor fit [11] 📄. Typing f35 into `lens` is exact only for 3:2 images with a 36 mm horizontal sensor; 4:3 needs ×1.040 🧠
- The Blender **viewport** focal length is not a camera. A community thread reports the viewport needing ~2× the camera focal length to match, and a maintainer disputed that this is a bug [12] 📄. My recollection is that the viewport applies a fixed 2× zoom, which makes a 50 mm viewport roughly a 25 mm camera on a 36 mm sensor 🧠
- KeenTools FaceBuilder sets focal length and sensor per photo automatically [15] 📄. fSpy solves focal length from vanishing lines [13], and with a single vanishing point you must supply it [14] 📄. A face has no straight edges, so vanishing points must come from the background 🧠

**Estimating focal length and distance from a face**
- Under a perspective camera, a face's scale is ambiguous [10] 📄. My reading of Bas & Smith [7] is that perspective landmarks fit a family of shape-and-distance pairs almost equally well 🧠
- **Decomposition:** image scale gives f/z, from IPD (63 ± 3.5–4 mm) or the iris (11.7 ± 0.5 mm). Perspective Δ/z gives z only if the person's depth Δ is known, and then f = (f/z)·z. The iris yields f/z, never z, unless f is known 🧠
- **Identity confounds distance.** Alar width varies ~8–10% (CV) between adults and bizygomatic width ~4%, so a nose-to-face ratio is uncertain by ~9–11%. That matches the whole perspective change between 0.5 m and infinity (Table 1), so one photo cannot separate a wide nose from a close camera 🧠
- In the library's engine simulations, single-view focal error is 2% for a known shape and 9–12% for an unknown face at 0.3 m. At 2 m focal length is unobservable. Multi-view shape RMSE stays ~1.2 mm either way (`camera-pose-solving.md`) 🧠
- The heuristic f = image width [8] 📄 equals ≈35 mm-equivalent for 4:3 landscape but ≈26 mm for portrait orientation, and is 2–5× too short for tele shots ↔️
- Learned single-image calibrators exist (GeoCalib [16], Perspective Fields [17]) 📄. They rely on scene geometry and are untested on face close-ups 🧠

**Camera models**
- In increasing fidelity: orthographic (drawings, photos ≥3–5 m), weak perspective (scaled orthographic, 6 DoF; valid while Δ/z ≲ 2–3%, i.e. whole head ≳3 m, interior points ≳1 m), paraperspective (Aloimonos 1990; off-centre faces), affine, full perspective (R, t, f; always valid), then + k1, k2 for uncorrected, ultrawide or webcam lenses 🧠. Weak-perspective image error ≈ (f/z)·X·Δ/z 🧠
- Many monocular 3DMM regressors assume weak perspective. On near photos they therefore bake perspective into the shape: a bigger nose and a narrower face 🧠. Perspective-aware face reconstruction calibrates K offline and then runs PnP [6] 📄, or estimates metric shape directly [10] 📄
- Under weak perspective, pose is measured relative to the ray through the face. An off-centre face θ off-axis therefore picks up a pose bias of ≈θ unless the principal point is honoured 🧠

## Numbers & reference tables

**Table 1 — Distance and frontal proportions** (pinhole arithmetic for a level camera. Depths: alar 20, eyes 40, contour 70, tragion 100 mm; IPD 63 mm. Weak-perspective residual for the ear: X 70 mm, 60 mm behind the eye plane; for interior points: X 35 mm, 30 mm)

| z to nose tip (m) | Situation | Ear shrink vs nose tip | Nose/face-width inflation vs ∞ | IPD/face-width inflation | Weak-persp. residual, ear / interior (% IPD) | Badge |
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
| Crop factor: FF 1.0; APS-C 1.5–1.6; MFT 2.0; 1-inch 2.7; phone main ~3.5–6.5 | data file | 🧠 |

**Table 4 — Capture by purpose**

| Purpose | Distance | Lens (FF-equivalent) | Ear shrink | Badge |
|---|---|---|---|---|
| Likeness/identity set | 1.5–3 m | 85–135 mm, or phone 3–5× tele | 3–7% | 🧠 |
| Clinical standard | ≥1 m, often ~1.5 m | 90–105 mm (85–135 seen) | ≤10% | ↔️ |
| ID/passport | ~1.2–2.5 m | not lens-specific | 4–8% | 🧠 |
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

1. **Triage every photo first.** Read EXIF `LensModel` and f35, then estimate distance from head size (Table 2). Label each photo selfie (<0.6 m), mid (0.6–1.5 m) or portrait (≥1.5 m). Selfies, front-camera and ultrawide shots are perspective evidence, not proportion references 🧠.
2. **New references:** shoot at 1.5–3 m with 85–135 mm-equivalent or a phone 3–5× tele, and crop later rather than step closer. Keep the face near the frame centre: θ < 10–15° keeps stretch under 4%. Lock one physical lens, because phones swap to a cropped main camera inside the tele's minimum focus distance 🧠.
3. **Rebuild each camera** (`blender/reference-camera-setup.md`):
   - Set `lens = f_px·36/W` with Sensor Fit Horizontal.
   - Place the camera at the **solved distance**.
   - Load the photo as a camera background image, and never scale or offset the background to make things fit 🧠.
4. **Sanity-check the distance.** Compare the solved z with Table 2 and with what the subject remembers. If interior features match but the ears and contour do not, f and z are wrong together (the dolly-zoom symptom), not the shape 🧠.
5. **Viewport:** to judge proportions, raise *View → Focal Length* to ~100–170 mm, or sculpt in ortho and judge only through matched cameras. A head filling the default 50 mm viewport is seen from roughly selfie distance, so "fixing" the nose there makes it too small 🧠.
6. **Ortho blueprints** only from photos taken at ≥3 m with yaw and pitch solved near 0. A 0.5 m "front" traced in ortho bakes in ~10% nose inflation and 20% ear shrink 🧠.
7. **Mixed sources:** compare proportions only between photos at similar distances. To use a selfie, render the sculpt through the selfie's own solved camera rather than "correcting" the photo by eye 🧠.
8. **Symptom → cause** 🧠:
   - nose too big and face too narrow → traced a near photo;
   - ears too small or set too far back → close references;
   - small chin and jaw → high-angle selfie;
   - one cheek fuller → yaw plus near-side magnification (at 0.5 m in a ¾ view the near cheek images ~15–20% larger);
   - head looks broad and flat in renders yet matched the screen → sculpted in a wide viewport;
   - pose off by several degrees → an off-centre crop whose principal point was recentred.
9. **Approval renders:** people know their face from mirrors (a mirror 0.4 m away is 0.8 m optically) and from front cameras. Show the subject renders from ~1 m and from the camera of their favourite photo, not only a 3 m tele view ↔️.

## Algorithmic implications

- **Exact reparameterisation:** u = c + s·(x + t_xy)/(1 + ρ·ẑ). Here s = f/z₀ (px/mm), ρ = 1/z₀, and (x, ẑ) are rotated head coordinates relative to a reference point (mid-eyes). Weak perspective is ρ = 0, so one solver starts at ρ = 0 and then frees ρ; f = s/ρ. Bound ρ to 0.1–5 m⁻¹ (z from 0.2 to 10 m) 🧠
- **Priors (log space):**
  - log f from EXIF f35 on an uncropped original: σ 0.04 (rounding, focus, tolerance).
  - EXIF present but crop unknown: σ 0.35.
  - No EXIF: hypotheses {13, 24, 26, 35, 50, 77, 85, 120, 135, 200} mm with σ 0.5–0.7.
  - z when f is unknown: front-camera selfie 0.35 m (σ 0.3); handheld rear main 0.8 m (σ 0.4); tele 2 m (σ 0.4); tape-measured ±5 cm.
  - Scale: IPD 63 ± 3.5–4 mm or iris 11.7 ± 0.5 mm 🧠
- **Observability:** report perspective strength P = 100 mm/z (above 0.1 strong, below 0.03 near-affine) and the posterior σ of ρ from the Gauss–Newton Hessian. If σ_ρ > 0.5ρ, label "distance/focal from prior" and hold depth-related shape modes at their prior or other-view values, so shape cannot absorb perspective 🧠
- **Single-view mode:** expose the (ρ, depth-mode) family as a dolly-zoom slider with its cost curve; this is the Bas & Smith ambiguity [7] made visible 🧠
- **Intrinsics groups** keyed on (Make, Model, LensModel, f35, W, H, still/video): share log f within a group (σ 0.02) and never average distances across photos 🧠
- **Off-axis faces:** carry the original principal point through crops by storing the crop offset. For weak-perspective initialisation, virtually rotate so the face-centre ray becomes the optical axis, initialise, then rotate back; this removes the ≈θ pose bias 🧠
- **Rejection and flag rules** 🧠:
  - ultrawide `LensModel` or f35 < 20 mm;
  - a face centre more than ~25° off-axis in phone images (warp risk);
  - a front camera, which triggers the mirror test and the selfie z prior;
  - never trust distance from landmark ratios when P < 0.05.
- **Lens distortion:** undistort calibrated images before PnP [9] 📄. For phone JPEG/HEIC, fix k at 0 🧠
- **Export:** a Blender camera at the solved distance (mm → m) with `lens = f_px·36/W`, HORIZONTAL fit. Offer an ORTHO camera (`ortho_scale = W/s` in scene units) only when P < 0.03 🧠
- **Feature:** "view as if from D" re-renders the fitted head with the photo projected onto it, giving the artist distance-equalised references (after Fried et al. 2016) 🧠
- **Tests:** a synthetic sweep over z 0.25–5 m and f35 13–200 mm. Check that recovered ρ and f are right, that the ρ = 0 start converges, and that shape error does not grow with P 🧠

## Disagreements, myths & open questions

- **"Telephoto flattens faces":** distance does that [1][2] ✅. The focal-length perception finding [5] confounds lens with distance ↔️
- **"85 mm is undistorted":** at 1.5 m the ears still image ~7% small relative to the nose tip 🧠
- **Size of the selfie effect:** geometry gives 12–16% and Ward et al. ~30% ↔️. Likely causes are the width definition, occluding-contour shift at close range and the model head used 🧠
- **35 mm-equivalent convention** (diagonal or width) ↔️, and **clinical lens choice** (85–135 mm) ↔️
- **"Weak perspective is good enough":** it is for benchmark landmarks at ≥1 m. It is not for ears, contours or anything under ~2 m that is meant to become a likeness 🧠
- **"Farther is always better":** beyond ~3 m the gains are tiny, while focal identifiability and pixels are lost 🧠
- **The "true" face:** for the mesh, geometry is the truth. For recognisability, the distance a person is usually seen from matters (Bryan et al. 2012) ↔️
- **Source [5]:** the snippet text matches Třebický et al. (2016), but the PMC number is in the range assigned around 2012 and could be Bryan et al. ↔️
- **Open** 🧠:
  - Ward et al.'s exact metric and head model;
  - how widely phones apply face warps, and whether they do so on main cameras;
  - per-phone f35 tagging under digital zoom and aspect crops (time-sensitive);
  - focal accuracy on real rather than synthetic faces;
  - whether the viewport 2× factor still holds in Blender 5.x.

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
