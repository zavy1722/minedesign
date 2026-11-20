# Reference images and camera matching in Blender

> A reference photo is a perspective projection from one point, so sculpting against it means rebuilding that camera in Blender: focal length in pixels (lens relative to sensor), principal point, pose, and any uncorrected distortion. Camera background images are drawn only through a camera, framed by its sensor fit and the render aspect. Image empties are scene objects that replaced the pre-2.8 per-viewport backgrounds [1][2][4]. fSpy solves cameras from vanishing lines, which suits architecture but rarely a bare portrait, so for faces you solve from landmarks with focal length free and an anatomical scale prior [10][18]. Facial perspective is set by distance, not focal length: at ~0.3 m the nose tip images about a third larger relative to the ears than from far away. Ortho tracing of near photos bakes this into the mesh, and a single-view overlay cannot reveal depth errors 🧠.
>
> Evidence status: 2 ✅ / 23 📄 / 49 🧠 / 11 ↔️ — 🧠 items are queued for web verification.

All 📄 items rest on harvested search snippets, not on opened pages. No claim has been refuted.

## Key facts

**Blender mechanics**
- Sensor **Size** is an alternative to focal length for setting field of view, intended for matching a physical camera [1] 📄. `sensor_width`/`sensor_height` are in mm, and the Camera Info geometry node exposes sensor size as a 2D mm vector [1] 📄. Only the ratio lens/sensor affects the image 🧠.
- **Sensor Fit:** *Auto* lets the larger render dimension define a square sensor. *Horizontal* sets the width and derives the height from the aspect ratio [1] 📄. So under Auto, a portrait-orientation photo's *height* is what `sensor_width` and `lens` describe 🧠.
- **Lens shift** is measured in units of the sensor-fit dimension: the larger dimension under Auto, the width under Horizontal 🧠 (from memory of Blender's view-plane code; verify).
- Background framing: *Fit* places the image inside the frame with its aspect kept; *Crop* fills the frame and cuts the overflow [1] 📄. *Stretch*, Opacity, Depth (Back/Front), Offset, Rotation, Scale and Flip also exist. A Movie Clip source can be displayed undistorted using the clip's tracking-camera distortion model 🧠.
- Backgrounds are viewport-only and do not render [6] 📄. Disabling Overlays hides them 🧠. Reported bugs: "Image not found" when adding one [7], and offset/scale having no effect in camera view [8] 📄.
- **History:** 2.79 had per-viewport background images [2] 📄. The 2.8x proposal swapped them for image empties and moved camera drawing into the camera data-block [4] 📄. Empties draw in perspective and ortho views, while camera backgrounds remain the camera-view mechanism [4][5] 📄.
- **Image empty:** *Shift+A → Empty → Image*, configured in Object Data properties [9] 📄. You can also use *Add → Image → Reference/Background* or drop an image into an ortho view. Options include Depth, Side, visibility in Orthographic/Perspective/Only Axis Aligned, and opacity through *Use Alpha*. "Images as Planes" has been core since 4.2 🧠.
- The free viewport's Focal Length is not a calibrated camera: judge likeness only through the matched camera (Numpad 0). *Align Active Camera to View* (Ctrl+Alt+Numpad 0) and *Lock Camera to View* silently destroy a match. Each scene has one render resolution, with no per-camera override 🧠.

**Optics of faces**
- Perspective depends only on camera-to-subject distance. Focal length and sensor set the framing, so a long lens is a crop of a wide one taken from the same spot 🧠 (Hartley & Zisserman).
- "Wide-angle distortion" is two things, near-distance perspective and rectilinear edge stretch; a matched pinhole camera reproduces both 🧠.
- At selfie distance (~30 cm) the apparent nasal base is roughly 30% wider than at ~1.5 m (Ward et al. 2018) 🧠. Camera distance alters facial configuration enough to impair identity matching (Noyes & Jenkins 2017) and shift social judgements (Bryan, Perona & Adolphs 2012) 🧠.
- Phone JPEG/HEIC output is usually distortion-corrected; some phones also unwarp faces in wide shots (Shih, Lai & Liang 2019), breaking the pinhole model near frame edges 🧠.
- Clinical facial photography uses long lenses at ≥1 m, but recommendations range from 85 to 135 mm full-frame equivalent, most often 90–105 mm (e.g. Ettorre et al. 2006) ↔️.
- The EXIF 35 mm-equivalent focal length is usually derived from the diagonal crop factor, but some makers use width ↔️. The engine (`face3d/geometry/camera.py`) assumes the diagonal.
- Scale anchors: horizontal visible iris diameter ≈11.7 ± 0.5 mm (Google MediaPipe Iris, 2020) 🧠. Adult IPD mean ≈63 mm, SD ≈3.5–4 mm, most adults 50–75 mm (Dodgson 2004) 🧠. Vergence at 35 cm shrinks the photographed inter-pupil distance by ~2 mm 🧠 (derived).

**fSpy and other matchers**
- **fSpy** is an open-source, cross-platform still-image matcher. It computes approximate focal length, orientation and position from user-placed control points and vanishing lines, and is usually exported to Blender [10][11] ✅.
- fSpy is the successor to the **BLAM** add-on [12] 📄. With one vanishing point the user must supply focal length [12] 📄. Two orthogonal vanishing points yield focal length, assuming the principal point is at the image centre 🧠.
- fSpy needs real scene lines and struggles without clear vanishing points [10][18] ✅. Workflows use one to three vanishing points [19] 📄.
- The **fSpy-Blender importer** reads principal point, horizontal FOV and image size from the `.fspy` JSON (principal point → lens shift, size → render resolution). It rejects project versions other than 1 [13] 📄 (from a search summary of `fspy.py`).
- Open issue #89 (Sept 2025) asks whether the importer works in Blender 4.5, and #88 reports failures with strong vanishing points [14] 📄. Compatibility with 4.5 and 5.x is **unconfirmed**.
- **perspective-match** says it ports fSpy's solver, names GPL-3.0, and follows fSpy's camera mapping [17] 📄.
- GeoCalib calls classical vanishing-point geometry accurate but not robust, which motivates learned calibration [20] 📄. Perspective Fields (CVPR 2023) is another learned calibrator [21] 📄. Neither has known accuracy on close-up faces 🧠.
- Also seen: fSpy feature requests #119 (known-size shapes) and #53 (zoom) [15][16], and tools known by title only [22]–[25] 📄.

## Numbers & reference tables

**Table 1 — Blender camera parameters for photo matching**

| Parameter | Unit / values | Meaning | Status |
|---|---|---|---|
| `sensor_width`, `sensor_height` | mm | With `lens`, sets the FOV | 📄 [1] |
| `sensor_fit` AUTO / HORIZONTAL | enum | Larger dimension / width uses `sensor_width` | 📄 [1] |
| Background `frame_method` FIT / CROP | enum | Inside the frame / fill the frame | 📄 [1] |
| `frame_method` STRETCH, `display_depth` BACK/FRONT, `alpha`, `offset`, `scale`, `rotation`, `use_flip_x/y` | bpy names | Overlay controls | 🧠 |
| `shift_x`, `shift_y` | fraction of the fit dimension | Principal-point offset | 🧠 |
| Defaults | lens 50 mm, sensor 36 mm, Auto, `clip_start` 0.1 m | The default `clip_start` can clip a nose | 🧠 |

**Table 2 — Pinhole relations** (standard geometry 🧠; W, H in px; OpenCV pixel coordinates, y down)

| Quantity | Formula |
|---|---|
| Horizontal FOV | `2·atan(S_w/(2 f_mm)) = 2·atan(W/(2 f_px))` |
| f_px | `f_mm·W/S_w`; from the 35 mm equivalent (diagonal): `f35·√(W²+H²)/43.27` |
| Blender lens (HORIZONTAL fit) | `f_px·S_w/W` |
| Blender shift (HORIZONTAL fit) | `shift_x = (W/2 − c_x)/W`, `shift_y = (c_y − H/2)/W` |
| Real sensor width (uncropped image) | `43.27·(f_mm/f35)·W/√(W²+H²)` |
| Distance from iris | `z ≈ f_px·11.7 mm / d_iris_px` |
| Near:far scale ratio | `1 + Δ/z` |
| Dolly-zoom invariant | keep `f/z_ref` constant: `z_new = z_ref·f_new/f_old` |

**Table 3 — Excess magnification of the nose tip over deeper landmarks, `100·Δ/z` %** (the arithmetic is exact; depths behind pronasale are approximate adult values 🧠, and Δ = 100 mm for the ear matches the library's multi-view note)

| z (to nose tip) | Δ≈40 mm (eye corners) | Δ≈70 mm (cheek contour) | Δ≈100 mm (tragion) | Status |
|---|---|---|---|---|
| 0.3 m | 13% | 23% | 33% | 🧠 |
| 0.5 m | 8% | 14% | 20% | 🧠 |
| 1.0 m | 4% | 7% | 10% | 🧠 |
| 1.5 m | 2.7% | 4.7% | 6.7% | 🧠 |
| 2.0 m | 2.0% | 3.5% | 5.0% | 🧠 |
| 3.0 m | 1.3% | 2.3% | 3.3% | 🧠 |
| 5.0 m | 0.8% | 1.4% | 2.0% | 🧠 |

Pure magnification predicts only a ~12% change in the nose-width/face-width ratio between 0.3 and 1.5 m (alar base at Δ≈20 mm against cheeks at 70 mm). The clinically reported ~30% is larger, probably because the occluding contour moves forward at close range and because width is defined differently ↔️.

**Table 4 — Capture set-ups** (derived 🧠; face width 140 mm; phone 4032×3024 with diagonal crop; full frame 6000×4000)

| Set-up | f35 | z | f_px | Face width (px) | Ear excess |
|---|---|---|---|---|---|
| Phone selfie, arm's length | 24 mm | 0.35 m | 2796 | 1118 | 29% |
| Phone main | 26 mm | 1.0 m | 3029 | 424 | 10% |
| Phone 3× tele | 77 mm | 2.0 m | 8970 | 628 | 5.0% |
| Phone 5× tele | 120 mm | 3.0 m | 13978 | 652 | 3.3% |
| Full frame, 24 MP | 135 mm | 3.0 m | 22500 | 1050 | 3.3% |

**Table 5 — Apparent offset of the nose tip against deeper landmarks from head rotation, `Δ·sin θ`** (derived 🧠; yaw gives a lateral offset, pitch a vertical one)

| θ | 1° | 2° | 3° | 5° | 10° |
|---|---|---|---|---|---|
| Δ = 70 mm | 1.2 mm | 2.4 mm | 3.7 mm | 6.1 mm | 12.2 mm |
| Δ = 100 mm | 1.7 mm | 3.5 mm | 5.2 mm | 8.7 mm | 17.4 mm |

The library's facial-asymmetry note gives natural asymmetry of ~0.8 mm RMSD and perception thresholds of 2–4 mm. A 2° yaw in a "front" photo therefore creates visible fake asymmetry.

**Table 6 — Suggested solver priors** (🧠 engineering choices; calibrate on real data)

| Parameter | Prior / default | σ |
|---|---|---|
| log f, EXIF f35, uncropped original | f_px from f35 | 0.03–0.05 |
| log f, EXIF f_mm + spec-sheet sensor | f_mm·W/S_w | 0.05 |
| log f, EXIF present but crop unknown | as above | 0.35 (engine default) |
| log f, no EXIF | multi-hypothesis 24–200 mm f35 (engine) | none, or weak 0.5 |
| Same device and zoom across photos | tie f | 0.02 (focus breathing) |
| Principal point | image centre, fixed | 1–2% of the fit dimension if freed |
| k1, k2 (phone JPEG) | 0, fixed | from checkerboard calibration only |
| Iris diameter | 11.7 mm per eye | 0.5 mm |
| IPD | 63 mm, or the user's measurement | 3.5–4 mm population; ~1 mm measured |
| Camera distance | hard bounds 0.25–10 m | warn below 1 m |

## Applying this to photo→3D face sculpting in Blender

1. **Capture (consenting subject).** Distance first: ≥1.5 m, ideally 2–3 m. Then zoom (phone 2–5× tele or 85–135 mm) and crop later (Table 4). Camera at nose height; neutral expression, eyes on lens, no glasses, ears and hairline clear. Shoot front, ±25°, ±45°, ±90°, plus slight high and low views. Lock zoom, focus and exposure; no portrait mode, beauty filters or ultra-wide; keep the face centred. Add scale with a ruler in the face plane or a measured IPD. One ~0.5 m shot with intact EXIF *helps* the solver identify focal length, but never trace it in ortho.
2. **Files.** Keep the originals and their EXIF. Bake the EXIF orientation into the pixels, because Blender has historically ignored the Orientation tag 🧠. Convert HEIC to PNG or JPEG 🧠. Record any crop, and never resize non-uniformly. If the camera was calibrated, undistort the photo and use the new intrinsics.
3. **One camera per photo** (bpy names from memory 🧠):
   ```python
   cd = bpy.data.cameras.new(name); cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0
   cd.lens = f_px * 36.0 / W
   cd.shift_x = (W/2 - cx) / W; cd.shift_y = (cy - H/2) / W   # divide by W under HORIZONTAL
   cd.clip_start = 0.01; cd.show_background_images = True
   bg = cd.background_images.new(); bg.image = bpy.data.images.load(path)
   bg.display_depth = 'FRONT'; bg.alpha = 0.4
   ```
   Scene resolution W×H, pixel aspect 1. Keep background offset, scale and rotation at identity: adjusting them only hides a mismatched camera. Lock the camera's transforms, and bind cameras to timeline markers (Ctrl+B) to scrub between views, applying each camera's resolution on switch 🧠.
4. **Solve, don't eyeball.** Detect landmarks, run PnP with focal length free, then export. Use fSpy only when architecture is visible, and treat its focal length as a prior [10][18].
5. **Overlay checks, weakest to strongest** 🧠:
   - (a) Flicker the background on and off (Front, α 0.3–0.5); blinking exposes offsets that side-by-side viewing misses.
   - (b) Check silhouette, ears and jaw contour (Outline plus X-ray, or Line Art), not just interior features.
   - (c) Difference-blend a render against the photo; the compositor blends in linear space and ignores alpha (portrait-lighting note).
   - (d) **Cross-view reprojection:** project photo A onto the mesh (UV Project modifier with the camera, aspect W:H, or Geometry Nodes) and view it through camera B over photo B. Only this reveals depth errors.
   - (e) **Dolly-zoom test:** interior features match but the silhouette is too wide, or the model shows ears the photo hides? Suspect a camera solved too far with too long a focal length, not the shape. Scrub along `f/z` before sculpting.
6. **Ortho blueprints, if you must:** only photos from ≥3 m (ear excess <~3%) with yaw and pitch solved near 0; empties set to *Only Axis Aligned*; align on landmark heights (pronasale, tragion, menton), not outlines; expect the Table 3 error (side photos also enlarge the near ear).
7. **Failure modes:** aspect mismatch; Auto fit on portrait-orientation photos; EXIF focal after a crop; mirrored selfies (check a hair part or mole); phone face-unwarping; yaw or pitch in the "front" photo (Table 5); unequal camera heights (1.6 m camera, 1.2 m seated eye level, 1.5 m away ≈ 15° pitch); vergence; expression or hair changes; `clip_start` clipping the nose; mm/m mixups.

## Algorithmic implications

- **Camera model:** per photo, a full-perspective pinhole with `[rvec, t, log f]`, the principal point fixed at the image centre, optional (k1, k2), and one shared head shape. Use scaled-orthographic only for initialisation, as `face3d/solve/pnp.py` already does. Priors are in Table 6 🧠.
- **Make the ambiguity explicit.** Expose a dolly-zoom coordinate (f and z move together, eye-plane scale fixed) and report the posterior SD of log f, flagging values above ~0.15. Single-view relative error of z ≈ √((σ_Δ/Δ)² + (σ_m/m)²) with m = Δ/z. With ~10% head-depth variation and σ_m ≈ 0.005–0.01, that is ~11% at 0.5 m, 15–20% at 2 m and ≥30% at 5 m 🧠, consistent with the multi-view note's lock-focal-beyond-1.2 m rule. Side views fix depth; frontal perspective then fixes f.
- **Contour landmarks are not surface points.** Jaw, cheek and chin-outline landmarks lie on a view-dependent occluding contour. Fit them as silhouette constraints (nearest contour point), and weight interior landmarks higher 🧠.
- **Metric scale** comes from the iris (σ 0.5 mm), a measured IPD (vergence-corrected when z < 1 m), or a ruler. Without any of these, scale and distance are degenerate across all views 🧠.
- **Export contract, and a probable engine bug:** `to_blender_camera` sets `sensor_fit='HORIZONTAL'` but divides shift by `max(W, H)`. If shift units follow the fit dimension 🧠, portrait-orientation photos get shift scaled by W/H (≈0.75). Divide by W, or use AUTO with the larger dimension for both lens and shift, and add an H > W test. Convert mm to m and set `clip_start` ≈ 0.01 m.
- **One scene resolution:** pad all photos into a common square canvas and offset (cx, cy) to match. f_px stays unchanged, so every camera shares the render resolution 🧠.
- **Round-trip test:** for each camera, run `bpy_extras.object_utils.world_to_camera_view`, take `u = x·W` and `v = (1−y)·H`, and require agreement with the engine within 0.01 px on synthetic data 🧠.
- **Add-on overlay:** a `gpu` POST_PIXEL handler maps photo pixels into the frame rectangle (`Camera.view_frame(scene=…)` projected with `view3d_utils.location_3d_to_region_2d`) and draws observed and reprojected landmarks with residual vectors 🧠. Scale the Huber threshold (engine: fixed 3 px) to ~1–2% of the inter-ocular pixel distance 🧠.
- **fSpy interop:** check version = 1, read principal point, FOV and size [13], and use the result only as a prior. Porting its solver brings GPL-3.0 [17]: fine for a GPL add-on, not for a permissively licensed engine 🧠.
- **Version robustness:** camera backgrounds in camera view, empties elsewhere [4][5]. Never rely on backgrounds in renders [6]. Add frame-mapping regression tests [7][8].
- **QA outputs:**
  - landmark residuals in px;
  - silhouette IoU;
  - cross-view reprojection error;
  - estimated z and f with their uncertainty;
  - perspective strength P = 100 mm/z, where above 0.1 is strong and below 0.03 is near-affine.

## Disagreements, myths & open questions

- **Where reference images live depends on the Blender version** [2][4] ↔️. 2.79-era tutorials contradict 2.8+ ones.
- **Myths:** "an 85 mm lens prevents distortion" (distance distorts; the lens only makes you stand back); "remove perspective before sculpting" (in a matched camera it is depth information); "ortho front/side blueprints are accurate for faces" (only for drawings or ≥3 m photos with solved pose; Tables 3, 5) 🧠.
- **How large the effect is:** the geometry gives ~12%, the clinical report ~30% ↔️. Whether the 35 mm equivalent is defined on the diagonal or the width is also disputed ↔️, as is the clinical lens choice (85–135 mm) ↔️.
- **fSpy-Blender on 4.5 and 5.x** is unconfirmed [14] ↔️. **perspective-match licence:** it is unclear whether "GPL-3.0" covers fSpy, the extension, or both [17] ↔️.
- **Excluded claim:** a "third-party benchmark" attributed to `fspy.py` [13] (camera matrix reproduced to 1.4e-7; `.fspy` stores no vanishing points). The provenance is inconsistent, so it is unconfirmed, not refuted ↔️.
- **Classical or learned calibration:** vanishing-point methods are accurate but brittle [18][20], and learned methods have not been tested on close-up faces [21] ↔️.
- **Open:**
  - EXIF orientation and HEIC support in Blender 5.x;
  - whether UV Project honours camera shift;
  - Line Art under Grease Pencil v3;
  - per-camera resolution;
  - validating the Table 6 priors on real portrait sets.

Sensor-format sizes and crop factors are in the data file `research/data/reference-camera-setup.json`.

## Sources

[1] Cameras — Blender 5.3 Manual — https://docs.blender.org/manual/en/latest/render/cameras.html — official-docs — 2026
[2] Background Images — Blender 2.79 Manual (legacy View-panel workflow) — https://docs.blender.org/manual/en/2.79/editors/3dview/properties/background_images.html — official-docs — 2017
[3] Camera Data — Blender 2.79 Manual (movie clip editor) — https://docs.blender.org/manual/en/2.79/editors/movie_clip_editor/tracking/clip/properties/camera_data.html — official-docs — 2017
[4] Proposal: Replace background images with Image Empties in 2.8x (issue #52668) — https://projects.blender.org/blender/blender/issues/52668 — repo — 2019
[5] Blender developer tracker task T51366 (title not captured) — https://developer.blender.org/T51366 — repo — unknown
[6] Blender not taking movie clip or image in camera background when rendering animation (issue #120929) — https://projects.blender.org/blender/blender/issues/120929 — repo — unknown
[7] Regression: Adding Camera background image pops an Image not found error (T98875) — https://developer.blender.org/T98875 — repo — unknown
[8] In viewport, Background image size/offset has no effect in camera view (T44096) — https://developer.blender.org/T44096 — repo — unknown
[9] Add a Background Image (katsbits codex) — https://www.katsbits.com/codex/background-image/ — blog — unknown
[10] fSpy — still-image camera matching app — https://github.com/stuffmatic/fSpy — repo — unknown
[11] fSpy still image camera matching software (LinuxLinks) — https://linuxlinks.com/fspy-still-image-camera-matching-software — blog — unknown
[12] Retiring BLAM and announcing fSpy (Blender Artists) — https://blenderartists.org/t/retiring-blam-and-announcing-fspy-a-stand-alone-camera-matching-app — forum — unknown
[13] fSpy-Blender importer source fspy.py — https://github.com/stuffmatic/fSpy-Blender/blob/master/fspy_blender/fspy.py — repo — unknown
[14] fSpy-Blender issue tracker (issues #88, #89) — https://github.com/stuffmatic/fSpy-Blender/issues — repo — 2025
[15] Feature idea: basic reference shapes for focal length matching (fSpy issue #119) — https://github.com/stuffmatic/fSpy/issues/119 — repo — unknown
[16] Zoom on image? (fSpy issue #53) — https://github.com/stuffmatic/fSpy/issues/53 — repo — unknown
[17] perspective-match: Blender extension, live perspective-line camera matching — https://github.com/voki6/perspective-match — repo — unknown
[18] V-Sekai decision record on fSpy — https://v-sekai.github.io/manuals/decisions/20240111-fspy.html — other — 2024
[19] 3D Environment Design with Blender (Packt) — https://www.packtpub.com/en-be/product/3d-environment-design-with-blender-9781803235851 — book — unknown
[20] GeoCalib: single-image calibration (arXiv 2409.06704v2) — https://arxiv.org/html/2409.06704v2 — paper — 2024
[21] Perspective Fields for Single Image Camera Calibration (CVPR 2023) — https://openaccess.thecvf.com/content/CVPR2023/papers/Jin_Perspective_Fields_for_Single_Image_Camera_Calibration_CVPR_2023_paper.pdf — paper — 2023
[22] Improving Blender workflows with still image camera matching app (80.lv) — https://80.lv/articles/improving-blender-workflows-with-still-image-camera-matching-app — news — unknown
[23] Blender-AI-Camera-Match — https://github.com/parthmital/Blender-AI-Camera-Match — repo — unknown
[24] Perspective Plotter docs — https://perspective-plotter.readthedocs.io/ — official-docs — unknown
[25] Blenspy — camera matching from photos — https://superhivemarket.com/products/blenspy — commercial — unknown

**Further reading (by name, not yet linked)**
- Hartley & Zisserman, *Multiple View Geometry in Computer Vision*, 2nd ed., 2004
- Zhang, "A flexible new technique for camera calibration", IEEE TPAMI, 2000
- Brown, "Decentering distortion of lenses", Photogrammetric Engineering, 1966
- Caprile & Torre, "Using vanishing points for camera calibration", IJCV, 1990
- Lepetit, Moreno-Noguer & Fua, "EPnP: an accurate O(n) solution to the PnP problem", IJCV, 2009
- Bujnak, Kukelova & Pajdla, "A general solution to the P4P problem for camera with unknown focal length", CVPR, 2008
- Ward, Ward, Fried & Paskhover, "Nasal distortion in short-distance photographs: the selfie effect", JAMA Facial Plastic Surgery, 2018
- Noyes & Jenkins, "Camera-to-subject distance affects face configuration and perceived identity", Cognition, 2017
- Bryan, Perona & Adolphs, "Perspective distortion from interpersonal distance is an implicit visual cue for social judgments of faces", PLoS ONE, 2012
- Fried, Shechtman, Goldman & Finkelstein, "Perspective-aware manipulation of portrait photos", ACM TOG (SIGGRAPH), 2016
- Shih, Lai & Liang, "Distortion-free wide-angle portraits on camera phones", ACM TOG (SIGGRAPH), 2019
- Dodgson, "Variation and extrema of human interpupillary distance", Proc. SPIE 5291, 2004
- Google Research, MediaPipe Iris announcement (iris-based depth estimation), 2020
- Farkas, *Anthropometry of the Head and Face*, 2nd ed., 1994
- Ettorre et al., "Standards for digital photography in cranio-maxillo-facial surgery – Part I", J Craniomaxillofac Surg, 2006
- CIPA DC-008, Exif standard (FocalLengthIn35mmFilm tag)
- Blender Python API reference: `CameraBackgroundImage`, `Object.empty_image_*`, `Camera.view_frame`, `bpy_extras.object_utils.world_to_camera_view`
- OpenCV documentation, calib3d module (calibrateCamera, undistort)
