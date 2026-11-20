# Smartphone camera processing, metadata and lens calibration for face capture

> A phone photo is not a raw pinhole image. The image signal processor (ISP) has already removed most lens distortion, so main and telephoto JPEG/HEIC files are close to rectilinear (residual |k1| ≲ 0.02, negligible for a centred face). It may also have applied things a pinhole solver cannot model: face-aware wide-angle warps near the frame edge, geometric beauty filters, mirroring, digital-zoom and aspect crops that EXIF describes inconsistently, and multi-frame or generative zoom that rewrites fine detail. The engine should trust the main or telephoto module with the face near the centre, give front, ultra-wide and edge-of-frame faces a different camera model, and take focal length from EXIF only after testing the crop and zoom hypotheses. Real calibration exists (Apple AVCameraCalibrationData, Android LENS_INTRINSIC_CALIBRATION/LENS_DISTORTION and Dynamic Depth, DNG WarpRectilinear), but it rarely survives in an ordinary camera-roll file, so the capture protocol matters more than any parser.
>
> Evidence status: 0 ✅ / 0 📄 / 67 🧠 / 24 ↔️ — 🧠 items are queued for web verification.

*No web harvest or earlier draft existed for this topic, so nothing here is web-sourced. Where a sibling note holds a sourced or verified version of a related claim, its path is given in backticks. Vendor menus, model numbers and library versions are time-sensitive (written 2026-11-20).*

## Key facts

**What the ISP does to geometry**
- **Geometric distortion correction (GDC)** is applied to the processed outputs (JPEG/HEIC/YUV) of every module on Apple, Google and Samsung phones. Apple exposes it as `AVCaptureDevice.isGeometricDistortionCorrectionEnabled` (on by default where supported); Android exposes it as `DISTORTION_CORRECTION_MODE` (API 28: OFF/FAST/HIGH_QUALITY) 🧠
- **Residual distortion after GDC** on main and telephoto modules is sub-percent at the corners, about |k1| ≲ 0.01–0.02 in OpenCV focal-normalised units ↔️ (I know of no published per-model survey). In the central third of a 26 mm-equivalent frame, k1 = 0.02 moves a landmark ≤ 2 px and changes local aspect by < 0.5% (Table 3), which is below detector noise (2–3% of inter-ocular distance, IOD) 🧠
- **Before correction:** main modules show roughly 1–3% optical distortion and ultra-wides 10–30%+ barrel. Phone lens designs accept this because the ISP removes it ↔️
- **Face-aware wide-angle correction.** Shih, Lai & Liang (Google, SIGGRAPH 2019) optimise a mesh warp in which each face region is a similarity transform of a *stereographic* projection, while lines elsewhere stay straight. Google shipped versions of it on Pixel wide, ultra-wide and selfie captures (which models and modes is unverified) 🧠. Apple has the equivalent capture switch `AVCapturePhotoSettings.isAutoContentAwareDistortionCorrectionEnabled` (iOS 14+) 🧠. A warped off-centre face is therefore neither pinhole nor globally radial: it looks locally as if a camera had been pointed straight at it 🧠
- **Why vendors warp:** in a rectilinear image, a face at field angle θ is stretched radially by 1/cos θ: 3.5% at 15°, 15.5% at 30°, 30.5% at 40° (Table 1). Corners sit at about 40° on a 26 mm main, 43° on a 23 mm front camera and 59° on a 13 mm ultra-wide (Table 2). The stretch is correct perspective and a pinhole solver models it exactly; the warp that removes it is what the solver cannot model 🧠
- **Beauty and retouching:**
  - China-market Android phones (Xiaomi, Oppo, Vivo, Honor, Huawei) often turn front-camera beauty on by default, including *geometric* sliders: face slimming, eye enlargement, nose and chin 🧠
  - Samsung selfie "face effects" smooth skin, and older models had face-shape sliders 🧠
  - Google switched Pixel face retouching to off by default, with neutral labels, around 2020 ↔️
  - Apple has no beauty mode. "Beautygate" (iPhone XS, 2018) was blamed on Smart HDR noise reduction and changed in iOS 12.1 🧠
- **Multi-frame fusion** (HDR+, Deep Fusion/Photonic Engine, Night mode, Super Res Zoom) aligns tiles to one reference frame. Geometry follows that frame to within a pixel at landmark scale, but subject motion in long night exposures ghosts or softens lids, lips and hair edges 🧠. Pixel 6 "Face Unblur" warps a sharper face from a second module into the frame 🧠
- **Generative zoom** synthesises detail: Samsung's AI-enhanced high zoom (the 2023 moon controversy) and the Pixel 10 Pro "Pro Res Zoom" (diffusion-based, roughly 30–100×, 2025). Nothing beyond optical zoom counts as identity evidence ↔️
- **Portrait mode:**
  - Synthetic bokeh blurs the ears, hair and jaw/neck silhouette that contour fitting needs, and segmentation fails around hair, glasses and ears 🧠
  - Relighting (Portrait Lighting) changes shading, not geometry 🧠
  - On iPhone the effect is non-destructive: Photos → Edit → Portrait off restores the sharp frame and keeps the depth map 🧠
  - iPhone 15 and later can record depth in Photo mode when a person is detected 🧠

**What EXIF says**
- `FocalLength` (0x920A) is the physical module's focal length (for example iPhone main ≈5.7–6.9 mm, ultra-wide ≈1.5–2.2 mm, telephoto ≈6–16 mm). Digital zoom leaves it unchanged, so it identifies the module 🧠
- `FocalLengthIn35mmFilm` (0xA405) usually *includes* digital zoom. A 2× crop of a 48 MP main reports ≈48 mm, and the iPhone 15 Pro "28/35 mm" main-lens options report 28/35, so f35/FocalLength jumps whenever a crop is used ↔️
- **Aspect crops:** whether vendors update f35 for 16:9 or 1:1 crops of the 4:3 sensor is untested. If the value is static, the diagonal formula under-estimates f_px by 8.2% (16:9) or 15% (1:1) (Table 4) ↔️. The diagonal-versus-width convention adds a further 4% ambiguity (`reconstruction/camera-pose-solving.md`, Verification log) ↔️
- `DigitalZoomRatio` (0xA404) is written by iPhones when zoomed beyond a module's native framing; Android vendors write it inconsistently ↔️
- **Subject distance:**
  - `SubjectDistance` (0x9206) is rare and coarse.
  - iPhones write `SubjectArea` (0x9214, the focus/face rectangle) and Apple MakerNote `FocusDistanceRange` and `AccelerationVector`. The acceleration vector is gravity in g, which gives camera pitch and roll 🧠
  - Android Camera2 reports `LENS_FOCUS_DISTANCE` in dioptres, with `LENS_INFO_FOCUS_DISTANCE_CALIBRATION` = UNCALIBRATED/APPROXIMATE/CALIBRATED; on phones it is seldom CALIBRATED 🧠
- **`LensModel`** on iPhones names the module (e.g. "iPhone 15 Pro back triple camera 6.765mm f/1.78", "… front camera 2.69mm f/1.9"). This is the best key for grouping intrinsics and for spotting the front camera. Many Android files omit it 🧠
- Apple uses non-standard `CustomRendered` values: 2/3 = HDR, 6 = panorama, 7 = Portrait HDR, 8 = Portrait. That makes a free Portrait-mode flag 🧠
- **Mirroring:** front-camera files may be mirrored in the pixels with Orientation = 1 and no flag. Mirrored Orientation values (2/4/5/7) are rare from phones 🧠. The iOS "Mirror Front Camera" switch (iOS 14+, default off) and "Save selfies as previewed" on Samsung and Pixel decide whether it happens ↔️
- **Edited exports:** crops and straightening in iOS Photos, Google Photos or Lightroom keep the original f35, which then becomes wrong. Non-native sizes flag this; native sizes include 4032×3024, 5712×4284, 8064×6048, 4080×3072, 4000×3000 and 8160×6144 🧠. `Software` (0x0131) sometimes names the editor (Facetune, Meitu, Snapseed, Lightroom) 🧠. Messaging apps strip EXIF and recompress 🧠

**Calibration a phone can expose**
- **Apple `AVCameraCalibrationData`** 🧠:
  - `intrinsicMatrix` (fx = fy, cx, cy) in pixels of `intrinsicMatrixReferenceDimensions`, usually the full sensor size;
  - `extrinsicMatrix` (3×4, mm) relative to a reference camera, plus `pixelSize` (mm) and `lensDistortionCenter`;
  - `lensDistortionLookupTable` and `inverseLensDistortionLookupTable`: 1-D tables of relative radial magnification m at n linearly spaced radii, from 0 to the distance between the distortion centre and the farthest corner; p′ = c + (p − c)(1 + m(r)).

  The forward table maps rectified → distorted, for resampling; the inverse maps distorted landmarks → rectified ↔️
- **Where Apple calibration appears:**
  - with `AVDepthData` (portrait/depth captures);
  - with `AVCapturePhoto`, in a custom app that enables calibration delivery on a virtual multi-camera device with constituent-photo delivery 🧠

  In HEIC files, depth or disparity is stored as an auxiliary image beside the Portrait Effects Matte and, from iOS 13, the hair/skin/teeth/glasses mattes ↔️. Rear depth is roughly 768×576-class disparity; TrueDepth (front) is roughly 640×480-class depth 🧠. Whether calibration survives in Camera-app HEICs, and how to parse it without Apple frameworks, is unverified ↔️
- **ARKit:** `ARFrame.camera.intrinsics` gives intrinsics per video frame. `ARFaceAnchor` (TrueDepth) gives a metric 1,220-vertex face mesh, a scale and distance source for a companion capture app 🧠
- **Android Camera2** 🧠:
  - `LENS_INTRINSIC_CALIBRATION` = [fx, fy, cx, cy, s] (API 23), in pixels of the pre-correction active array. It is also reported per frame, because OIS and focus move it;
  - `LENS_DISTORTION` = [κ1, κ2, κ3, κ4, κ5] (API 28; Brown–Conrady, 3 radial + 2 tangential), which replaces the deprecated, inconsistently defined `LENS_RADIAL_DISTORTION`;
  - `LENS_POSE_ROTATION/TRANSLATION/REFERENCE`, `SENSOR_INFO_PHYSICAL_SIZE` and `LENS_INFO_AVAILABLE_FOCAL_LENGTHS`.

  These keys are optional. They are reliably present mainly on devices that declare the DEPTH_OUTPUT, LOGICAL_MULTI_CAMERA or MOTION_TRACKING capability, only a capturing app can read them, and stock JPEG EXIF never contains them 🧠
- **LENS_DISTORTION coordinates:** as documented, they are centred on (cx, cy) and normalised so the farthest edge is 1 (|r| ≤ √2), unlike OpenCV's focal-normalised coordinates. Practitioners report OEM values that look focal-normalised ↔️
- **Android Dynamic Depth 1.0** (Android 10; Camera2 `DEPTH_JPEG`) embeds a depth map and an `ImagingModel` (focal lengths, principal point, skew, distortion) in the JPEG's XMP and an appended container 🧠
- **DNG `WarpRectilinear`** (opcode 1, DNG 1.3+, in OpcodeList3) stores per-plane kr0–kr3 (polynomial in r², r⁴, r⁶ with kr0 ≈ 1), tangential kt0–kt1 and a normalised optical centre. It is a backward map (output → source), with the radius normalised to the farthest corner 🧠. Android `DngCreator` writes it from `LENS_DISTORTION`, plus a lens-shading GainMap in OpcodeList2 🧠
- **Apple ProRAW and Samsung Expert RAW** are linear, demosaiced, multi-frame-merged DNGs: processed data in a raw container. ProRAW is DNG 1.6 (ProfileGainTableMap, semantic masks) 🧠, and newer files may use DNG 1.7 JPEG XL compression ↔️. Whether their geometry is pre-corrected or carried as opcodes varies by vendor and version, so inspect OpcodeList3 ↔️
- **Lensfun** profiles interchangeable-lens and some fixed-lens cameras (poly3, poly5 and PTLens models). It has essentially no useful phone coverage, and phone output is already corrected. Use it only for DSLR or mirrorless references shot with in-camera correction off 🧠

## Numbers & reference tables

**Table 1 — Off-axis face in a rectilinear image** (arithmetic; population: any pinhole camera)

| Field angle θ | Radial/tangential stretch 1/cos θ | Area vs centre 1/cos³θ | Stereographic scale vs centre sec²(θ/2) | Badge |
|---|---|---|---|---|
| 15° | 1.035 | 1.11 | 1.017 | 🧠 |
| 25° | 1.103 | 1.34 | 1.049 | 🧠 |
| 30° | 1.155 | 1.54 | 1.072 | 🧠 |
| 40° | 1.305 | 2.23 | 1.132 | 🧠 |
| 50° | 1.556 | 3.77 | 1.217 | 🧠 |
| 60° | 2.000 | 8.00 | 1.333 | 🧠 |

**Table 2 — Field angles by 35 mm-equivalent focal length** (4:3 frame, diagonal convention; module ranges are time-sensitive)

| Module (typical f35) | HFOV, long side | Edge-centre angle (long side) | Corner angle | Badge |
|---|---|---|---|---|
| Ultra-wide (13 mm) | 106° | 53° | 59° | 🧠 |
| Front (≈20–30 mm; 23 mm shown) | 74° | 37° | 43° | ↔️ |
| Main (24–26 mm; 26 mm shown) | 67° | 34° | 40° | 🧠 |
| 2× crop (48 mm) | 40° | 20° | 24° | 🧠 |
| 3× tele (77 mm) | 25° | 13° | 16° | 🧠 |
| 5× tele (120 mm) | 16° | 8° | 10° | 🧠 |

**Table 3 — Effect of residual radial distortion** (4032×3024, f35 26 mm → f_px 3028; displacement px / local anisotropy 2k1r² %; k1 focal-normalised)

| Radius from centre (px, r = px/f) | k1 = 0.01 | k1 = 0.02 | k1 = 0.05 | k1 = −0.10 (uncorrected UW-like) | Badge |
|---|---|---|---|---|---|
| 500 (0.17), centred face | 0.1 / 0.05% | 0.3 / 0.11% | 0.7 / 0.27% | 1.4 / 0.55% | 🧠 |
| 1000 (0.33) | 1.1 / 0.22% | 2.2 / 0.44% | 5.5 / 1.1% | 11 / 2.2% | 🧠 |
| 1500 (0.50) | 3.7 / 0.49% | 7.4 / 0.98% | 18 / 2.5% | 37 / 4.9% | 🧠 |
| 2016 (0.67), long edge | 8.9 / 0.89% | 18 / 1.8% | 45 / 4.4% | 89 / 8.9% | 🧠 |
| 2520 (0.83), corner | 17 / 1.4% | 35 / 2.8% | 87 / 6.9% | 175 / 14% | 🧠 |

**Table 4 — Aspect crops and focal-length error** (sensor native 4:3, 4032 px long side)

| Delivered | Size | Native/delivered diagonal | f_px error if f35 is static but the delivered diagonal is used | Badge |
|---|---|---|---|---|
| 4:3 | 4032×3024 | 1.000 | 0 | 🧠 |
| 3:2 | 4032×2688 | 1.040 | −3.8% | 🧠 |
| 16:9 | 4032×2268 | 1.089 | −8.2% | 🧠 |
| 1:1 | 3024×3024 | 1.179 | −15.2% | 🧠 |
| Width-based f35 convention instead of diagonal | any | 0.962 | +4.0% | ↔️ |

**Table 5 — Decoders usable from Blender** (licences time-sensitive)

| Package | Licence | Reads | Notes | Badge |
|---|---|---|---|---|
| pillow-heif (+ Pillow) | BSD-3 binding; wheels bundle libheif and libde265 (LGPL-3.0) and x265 (GPL-2.0+); Pillow MIT-CMU | HEIC/HEIF, EXIF/XMP, depth images (version-dependent) | Blender bundles neither Pillow nor a HEIC reader; ship cp-tagged wheels | ↔️ |
| rawpy (LibRaw) | MIT binding; LibRaw LGPL-2.1 or CDDL-1.0 | Bayer and linear DNG, vendor raws | opcode warps mostly not applied; JPEG XL DNG support build-dependent | ↔️ |
| tifffile | BSD-3 | DNG/TIFF tags, OpcodeList bytes | NumPy-only; decompression needs imagecodecs | 🧠 |
| ExifTool | GPL or Artistic (Perl) | all tags, Apple MakerNotes, aux images, opcodes | external process | 🧠 |
| exifread | BSD-3 | EXIF from JPEG/TIFF/HEIC | pure Python | 🧠 |
| lensfunpy (Lensfun) | MIT binding; library LGPL-3, database CC BY-SA 3.0 | lens profiles | not useful for phones | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Ingest originals.** Use AirDrop, cable or "original" export. Read EXIF (and Apple MakerNotes via ExifTool) into a JSON sidecar *before* any conversion, because PNG conversion usually drops EXIF. This corrects the "convert HEIC to PNG" step in `community/reference-photography-protocol.md` 🧠. On iPhone, Settings → Camera → Formats → Most Compatible captures JPEG and avoids HEIC entirely 🧠
2. **Triage each photo:** module (`LensModel`, FocalLength), zoom (f35/FocalLength against that module's baseline), aspect, native or edited size, front camera, Portrait (`CustomRendered` 7/8), night (exposure > 1/15 s), and the face's field angle from the image centre. Reject ultra-wide and beyond-optical zoom. Down-weight any face more than 25° off-axis 🧠
3. **Shoot new references in 4:3 at native resolution.** This removes the aspect-crop ambiguity in Table 4 🧠
4. **Mirror check** for every front-camera photo: compare hair parting, moles and background text with an unmirrored reference 🧠
5. **Portrait-mode iPhone photos:** turn the effect off in Photos before export, then keep the depth map separately for a distance prior 🧠
6. **Settings checklist** (menu names vary by OS version ↔️):

| Phone | Switch off or set | Why | Badge |
|---|---|---|---|
| iPhone | Settings → Camera: Mirror Front Camera off; Preserve Settings on (keep the lens and mode); Macro Control on, then macro off in the viewfinder (Auto Macro silently switches to the ultra-wide); Photographic Styles Standard; Night mode off per shot; Portrait off | mirroring, lens swaps, fusion | 🧠 |
| iPhone | Lens Correction (front and ultra-wide): leave **on** unless the engine estimates distortion; it cannot remove the main camera's correction | rectilinear is the solver's model | ↔️ |
| Pixel | Face retouching off; Save selfies as previewed off; Night Sight off; choose the lens explicitly in Pro controls (8 Pro+); RAW+JPEG on; any "lens correction" toggle for the ultra-wide stays on | beauty, mirror, lens swaps | ↔️ |
| Samsung | Face effects / beauty 0; Save selfies as previewed off; Scene optimizer off; Ultra-wide shape correction off only if you must use the ultra-wide (better: don't); no zoom beyond optical; Expert RAW for linear DNG | beauty, warps, AI zoom | ↔️ |
| Xiaomi / Oppo / Vivo / Honor / Huawei | Beautify 0, including slimming, eyes, nose and chin sliders; AI camera off; ultra-wide distortion correction as for Samsung | geometric beauty on by default | 🧠 |
| Any | Third-party manual app (Halide, ProCamera, Open Camera, Blackmagic Camera) to lock one physical lens; video stabilisation off for frame grabs | lens substitution, per-frame stabilisation warps | 🧠 |

7. **Decode inside Blender.** HEIC goes through bundled pillow-heif wheels (see `blender/blender-python-ml-deps.md` for wheel tags and the no-runtime-pip store rule). RAW goes through rawpy: `postprocess(gamma=(1, 1), no_auto_bright=True, output_bps=16, use_camera_wb=True)`, flip vertically for `Image.pixels.foreach_set`, and use a linear colourspace. Apply WarpRectilinear yourself 🧠
8. **What goes wrong** 🧠:
   - The selfie nose is "too big" because it was really shot at 0.35 m (`reconstruction/camera-perspective-distortion.md`).
   - An off-centre group-shot face looks round and correct but solves with a wrong yaw (content-aware warp).
   - The same lens gives two focal lengths (16:9 versus 4:3, or a 2× crop).
   - The jaw is too narrow (beauty slimming).
   - L/R features are swapped (mirror).
   - Ears and hair dissolve (Portrait blur).
   - HEIC images come out rotated twice (HEIF `irot` applied *and* EXIF Orientation applied).

## Algorithmic implications

- **Metadata reader** (`face3d/io/exif.py` handles JPEG/TIFF only) 🧠:
  - Add HEIC: walk ISOBMFF `meta` → `iinf` to the `Exif` item → `iloc`; the payload starts with a 4-byte big-endian offset to the TIFF header.
  - Apply HEIF `irot/imir/clap` and then ignore EXIF Orientation.
  - Add tags 0xA404, 0x9206, 0x9214, 0xA401, 0xA432/0xA433, 0x0131, 0x829A and DNG OpcodeList1/2/3 (0xC740/0xC741/0xC74E).
- **Native frame:** phones are 4:3 native. For other aspects, carry two focal hypotheses: static tag (diag = 1.25 × long side for 16:9 and 3:2; 5/3 × side for 1:1) and updated tag (delivered diagonal). Fit both; choose by consistency inside the intrinsics group, else keep σ_log f = 0.09 🧠
- **Zoom detector:** c = f35/FocalLength. Baseline c₀ = the mode of c per (Make, Model, LensModel); zoom = c/c₀. If zoom > 1.02 the photo is cropped: the principal point stays at the centre and σ_log f rises to 0.06 (UI rounding) 🧠
- **Intrinsics** 🧠:
  - fx = fy, skew 0;
  - principal point at the delivered centre with σ = 1% of width (OIS and assembly), fixed unless there are ≥ 5 views in the group;
  - f35 from an uncropped 4:3 original: σ_log f 0.04 (matches `reconstruction/camera-perspective-distortion.md`).
- **Camera model per view** 🧠:
  1. Corrected main/tele with the face within 25°: k = 0, fixed.
  2. Corrected main/tele beyond 25°, or front camera: k1 free with prior N(0, 0.02²).
  3. Ultra-wide or front with the face beyond 25°, or a content-aware warp likely: use a **local virtual camera**. Rotate by R_v so the face-centre ray becomes the axis, set f′ = f·sec²(θ/2), and put the principal point at the face centre (the stereographic similarity). Alternatively inflate σ_px ×3.
  4. Known calibration (Apple inverse LUT, Android `LENS_DISTORTION`, DNG warp, Dynamic Depth) on an uncorrected image: undistort the landmarks, then k = 0.
- **Mirror hypothesis:** fit front-camera views both ways and keep the lower cost when the margin is > 10%; otherwise ask the user 🧠
- **Distance priors** (log z) 🧠:

  | Source | Prior |
  |---|---|
  | SubjectDistance | σ 0.5 |
  | Apple FocusDistanceRange | log-uniform over the range widened ×1.5 |
  | Android focus distance, CALIBRATED | σ 0.2 |
  | Android focus distance, APPROXIMATE | σ 0.4 |
  | Android focus distance, UNCALIBRATED | ignore |
  | Median of a TrueDepth depth map | σ 0.05–0.1 |
  | Median of a rear disparity map | σ 0.2–0.3 |

- **Gravity:** Apple `AccelerationVector` → camera pitch/roll prior relative to gravity. Use σ 5° for pitch, because head tilt is unknown 🧠
- **Processing-risk score** per view, which sets robust weights and drives UI warnings 🧠. It counts: front camera; Portrait; night; zoom beyond optical; non-native size; an editor named in `Software`; an AI-edit/C2PA marker. Pixels cannot reveal geometric beauty, so flag a view whose eye-width/IOD or bigonial/IOD ratio departs > 3σ from the multi-view consensus.
- **Line-straightness QA:** detect long background edges and fit their curvature. Bending beyond the residual expected from Table 3 means uncorrected distortion or a content-aware warp 🧠
- **Tests:** synthesise images with each warp type (k1 sweep, stereographic face warp, 16:9 static-tag crop, mirror), then assert that the right model is chosen and that shape error stays below 1 mm 🧠

## Disagreements, myths & open questions

- **"Turn lens correction off for accuracy"** ↔️. That is a photogrammetry habit (estimate k1/k2 yourself). For a pinhole face solver, corrected rectilinear output *is* the right model; only face-aware warps must be avoided, and avoiding the ultra-wide and front cameras does that 🧠
- **"RAW is unprocessed."** ProRAW and Expert RAW are merged and denoised; only single-frame Bayer DNG is near-sensor 🧠
- **"Portrait mode is the most accurate face photo."** It is often a telephoto or crop at a good distance, but its blur destroys the silhouette 🧠
- **FocalLengthIn35mmFilm:** diagonal or width convention, and static or crop-updated, varies by vendor ↔️
- **`LENS_DISTORTION` normalisation:** the documentation and practice may differ ↔️
- **Apple's Lens Correction switch:** whether it also governs content-aware face correction on the ultra-wide and front cameras is unclear ↔️
- **Front cameras:** iPhone 11–14 default to a cropped ≈30 mm framing (tap to widen ≈23 mm), and iPhone 17's square-sensor front camera reframes automatically, so f35 varies within one camera ↔️
- **HEVC patents** may matter for distributing a decoder, independently of the copyright licence ↔️
- **Open questions** 🧠:
  - measured residual k1 per phone model;
  - per-vendor f35 behaviour under zoom and aspect (needs a test-shot matrix);
  - whether calibration survives in Camera-app HEIC;
  - how much fusion and Face Unblur move facial landmarks;
  - whether Pixel Pro Res Zoom excludes faces.

## Sources

None. No harvest or earlier draft existed for this topic, so no URLs can be cited here. Sibling notes with sourced or verified related claims:
- `reconstruction/camera-perspective-distortion.md` (distance-driven facial perspective; EXIF f35 convention, contested)
- `reconstruction/camera-pose-solving.md` (undistort before PnP; f35 diagonal convention, unconfirmed)
- `community/reference-photography-protocol.md` (phone lens table; iPhone 17 Pro 4× = 100 mm, sourced)
- `blender/blender-python-ml-deps.md` (wheels in Blender extensions; no runtime pip)

**Further reading (by name, not yet linked)**
- Shih, Lai & Liang, "Distortion-free wide-angle portraits on camera phones", ACM TOG (SIGGRAPH), 2019
- Hasinoff et al., "Burst photography for high dynamic range and low-light imaging on mobile cameras", ACM TOG (SIGGRAPH Asia), 2016
- Wronski et al., "Handheld multi-frame super-resolution", ACM TOG (SIGGRAPH), 2019
- Wadhwa et al., "Synthetic depth-of-field with a single-camera mobile phone", ACM TOG (SIGGRAPH), 2018
- Liba et al., "Handheld mobile photography in very low light", ACM TOG (SIGGRAPH Asia), 2019
- Apple Developer Documentation: AVCameraCalibrationData, AVDepthData, AVCapturePhotoSettings, AVCaptureDevice (geometric distortion correction)
- Apple WWDC 2017, "Capturing Depth in iPhone Photography"
- Android Developers: CameraCharacteristics (LENS_INTRINSIC_CALIBRATION, LENS_DISTORTION, LENS_POSE_*, DISTORTION_CORRECTION_MODE); DngCreator
- Android Dynamic Depth 1.0 specification, 2019
- Adobe, Digital Negative (DNG) Specification 1.4–1.7 (opcodes, ProfileGainTableMap, semantic masks)
- CIPA DC-008, Exif 2.32/3.0
- ISO/IEC 23008-12, HEIF
- Phil Harvey, ExifTool tag documentation (Apple MakerNotes, CustomRendered)
- Lensfun project documentation (distortion models)
- pillow-heif, rawpy and LibRaw documentation (licence sections)
- Brown, "Decentering distortion of lenses", 1966; Zhang, "A flexible new technique for camera calibration", TPAMI 2000
