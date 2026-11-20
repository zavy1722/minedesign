# Smartphone camera processing, metadata and lens calibration for face capture

> A phone photo is not a raw pinhole image. The ISP has already removed most lens distortion, so main and telephoto JPEG/HEIC files are near-rectilinear (residual |k1| ≲ 0.02, negligible for a centred face). It may also have applied what a pinhole solver cannot model: face-aware wide-angle warps near the frame edge, geometric beauty filters, mirroring, zoom and aspect crops that EXIF describes inconsistently, and generative zoom. The engine should trust main or telephoto pixels with the face near the centre, give front, ultra-wide and edge-of-frame faces a different camera model, and use EXIF focal length only after testing crop and zoom hypotheses. Real calibration exists (Apple AVCameraCalibrationData, Android LENS_INTRINSIC_CALIBRATION/LENS_DISTORTION and Dynamic Depth, DNG WarpRectilinear) but rarely survives in a camera-roll file, so the capture protocol matters more than any parser.
>
> Evidence status: 0 ✅ / 0 📄 / 59 🧠 / 21 ↔️ — 🧠 items are queued for web verification.

*No harvest or earlier draft existed, so nothing here is web-sourced; sibling notes with related sourced claims are named in backticks. Menus, models and library versions are time-sensitive (2026-11-20).*

## Key facts

**What the ISP does to geometry**
- **Geometric distortion correction (GDC)** is applied to processed outputs (JPEG/HEIC) of every module on Apple, Google and Samsung phones: Apple `AVCaptureDevice.isGeometricDistortionCorrectionEnabled` (default on where supported), Android `DISTORTION_CORRECTION_MODE` (API 28) 🧠
- **Residual after GDC** on main and telephoto is sub-percent at the corners, |k1| ≲ 0.01–0.02 in OpenCV focal-normalised units; before correction main modules carry ~1–3% and ultra-wides 10–30%+ barrel ↔️ (no per-model survey known). In the central third of a 26 mm-equivalent frame, k1 = 0.02 moves a landmark ≤ 2 px and changes local aspect < 0.5% (Table 3), below detector noise (2–3% of inter-ocular distance, IOD) 🧠
- **Face-aware wide-angle correction:** Shih, Lai & Liang (Google, SIGGRAPH 2019) solve a mesh warp making each face region a similarity transform of a *stereographic* projection while background lines stay straight; versions shipped on Pixel wide/selfie captures (models unverified) 🧠. Apple's capture switch is `AVCapturePhotoSettings.isAutoContentAwareDistortionCorrectionEnabled` (iOS 14+) 🧠. A warped off-centre face looks locally as if a camera were pointed straight at it, so it is neither pinhole nor globally radial 🧠
- **Why vendors warp:** in a rectilinear image a face at field angle θ is stretched radially by 1/cos θ: 3.5% at 15°, 15.5% at 30°, 30.5% at 40° (Table 1); corners sit at ~40° (26 mm main), ~43° (23 mm front), ~59° (13 mm ultra-wide) (Table 2). A pinhole solver models that stretch; the warp removing it breaks the solver 🧠
- **Beauty:** China-market Android phones (Xiaomi, Oppo, Vivo, Honor, Huawei) often default front-camera beauty on, with *geometric* sliders (face slimming, eye enlargement, nose, chin) 🧠; Samsung "face effects" smooth skin, older models reshaped 🧠; Google made Pixel face retouching off by default around 2020 ↔️; Apple has no beauty mode ("Beautygate", iPhone XS 2018, was Smart HDR noise reduction, changed in iOS 12.1) 🧠
- **Multi-frame fusion** (HDR+, Deep Fusion, Night mode, Super Res Zoom) aligns tiles to a reference frame, preserving geometry to about a pixel; motion in night exposures softens lids, lips and hair 🧠. Pixel 6 "Face Unblur" warps a sharper face in from a second module 🧠
- **Generative zoom** (Samsung AI high zoom; Pixel 10 Pro "Pro Res Zoom", diffusion-based, ~30–100×) synthesises detail; nothing beyond optical zoom is identity evidence ↔️
- **Portrait mode** blurs ears, hair and the jaw/neck silhouette, and segmentation fails around hair, glasses and ears 🧠. On iPhone it is non-destructive (Photos → Edit → Portrait off keeps the depth map); iPhone 15+ records depth in Photo mode when a person is detected 🧠

**What EXIF says**
- `FocalLength` (0x920A) is the physical module's focal length (iPhone main ≈5.7–6.9 mm, ultra-wide ≈1.5–2.2 mm, tele ≈6–16 mm), unchanged by digital zoom, so it identifies the module 🧠
- `FocalLengthIn35mmFilm` (0xA405) usually *includes* digital zoom (a 2× crop of a 48 MP main reports ≈48 mm; iPhone 15 Pro "28/35 mm" options report 28/35) ↔️. Whether it is updated for 16:9 or 1:1 crops of the 4:3 sensor is untested; if static, the diagonal formula under-estimates f_px by 8.2% or 15% (Table 4) ↔️. Diagonal vs width convention adds 4% (`reconstruction/camera-pose-solving.md`) ↔️
- `DigitalZoomRatio` (0xA404) is written by iPhones when zoomed past a module's native framing, inconsistently by Android vendors ↔️
- **Distance:** `SubjectDistance` (0x9206) is rare and coarse. iPhones write `SubjectArea` (0x9214, focus/face rectangle) and MakerNote `FocusDistanceRange` and `AccelerationVector` (gravity in g → camera pitch/roll) 🧠. Android `LENS_FOCUS_DISTANCE` is in dioptres with a declared calibration level, seldom CALIBRATED on phones 🧠
- **`LensModel`** on iPhones names the module ("iPhone 15 Pro back triple camera 6.765mm f/1.78", "… front camera 2.69mm f/1.9"), the best intrinsics-group and front-camera key; many Android files omit it 🧠
- Apple's non-standard `CustomRendered` values (7 Portrait HDR, 8 Portrait) give a free Portrait flag 🧠
- **Mirroring:** front-camera files may be mirrored in pixels with Orientation = 1 🧠; iOS "Mirror Front Camera" (default off) and "Save selfies as previewed" (Samsung, Pixel) decide it ↔️
- **Edited exports** (iOS Photos, Google Photos, Lightroom crops) keep the original f35, which becomes wrong; non-native sizes (native e.g. 4032×3024, 5712×4284, 4080×3072, 4000×3000) and `Software` naming an editor (Facetune, Meitu) flag this. Messaging apps strip EXIF 🧠

**Calibration a phone can expose**
- **Apple `AVCameraCalibrationData`:** `intrinsicMatrix` in pixels of `intrinsicMatrixReferenceDimensions` (usually full sensor); `extrinsicMatrix` (3×4, mm); `pixelSize`; `lensDistortionCenter`; forward and inverse `lensDistortionLookupTable` of relative radial magnification m at n radii up to the farthest corner, p′ = c + (p − c)(1 + m(r)) 🧠. The inverse table maps distorted landmarks → rectified ↔️
- It arrives with `AVDepthData`, or with `AVCapturePhoto` in a custom app that enables calibration delivery on a virtual multi-camera device 🧠. HEIC stores depth/disparity as an auxiliary image beside Portrait and semantic mattes ↔️ (rear ~768×576-class, TrueDepth ~640×480-class 🧠); whether calibration survives in Camera-app HEICs is unverified ↔️
- **ARKit:** `ARFrame.camera.intrinsics` per frame; `ARFaceAnchor` (TrueDepth) gives a metric 1,220-vertex face mesh, a scale and distance source for a companion app 🧠
- **Android Camera2:** `LENS_INTRINSIC_CALIBRATION` [fx, fy, cx, cy, s] (API 23; pre-correction active-array pixels; per frame as OIS moves it); `LENS_DISTORTION` [κ1–κ5] (API 28; Brown–Conrady 3 radial + 2 tangential, replacing the inconsistent `LENS_RADIAL_DISTORTION`); `LENS_POSE_*` 🧠. All optional, dependable mainly on devices declaring DEPTH_OUTPUT or LOGICAL_MULTI_CAMERA, readable only by the capturing app, never in stock EXIF 🧠
- Documented `LENS_DISTORTION` coordinates are centred on (cx, cy) with the farthest edge = 1 (|r| ≤ √2), unlike OpenCV's focal-normalised ones; practitioners report OEM values that look focal-normalised ↔️
- **Android Dynamic Depth 1.0** (`DEPTH_JPEG`) embeds a depth map and an `ImagingModel` (focal, principal point, distortion) in the JPEG 🧠
- **DNG `WarpRectilinear`** (opcode 1, OpcodeList3): per-plane kr0–kr3 (in r², r⁴, r⁶; kr0 ≈ 1), kt0–kt1 and a normalised centre; a backward map, radius normalised to the farthest corner 🧠. Android `DngCreator` writes it from `LENS_DISTORTION` 🧠
- **ProRAW and Samsung Expert RAW** are linear, demosaiced, multi-frame-merged DNGs (ProRAW: DNG 1.6 with semantic masks 🧠; newer files may use DNG 1.7 JPEG XL ↔️); whether geometry is pre-corrected or in opcodes varies ↔️
- **Lensfun** has essentially no useful phone coverage and phone output is pre-corrected; use it only for DSLR/mirrorless references shot with in-camera correction off 🧠

## Numbers & reference tables

**Table 1 — Off-axis face in a rectilinear image** (arithmetic; any pinhole camera)

| Field angle θ | Radial/tangential stretch 1/cos θ | Area vs centre 1/cos³θ | Stereographic scale sec²(θ/2) | Badge |
|---|---|---|---|---|
| 15° | 1.035 | 1.11 | 1.017 | 🧠 |
| 30° | 1.155 | 1.54 | 1.072 | 🧠 |
| 40° | 1.305 | 2.23 | 1.132 | 🧠 |
| 50° | 1.556 | 3.77 | 1.217 | 🧠 |

**Table 2 — Field angles by 35 mm-equivalent focal** (4:3, diagonal convention; module ranges time-sensitive)

| Module (f35) | HFOV | Long-edge angle | Corner angle | Badge |
|---|---|---|---|---|
| Ultra-wide (13 mm) | 106° | 53° | 59° | 🧠 |
| Front (≈20–30; 23 mm shown) | 74° | 37° | 43° | ↔️ |
| Main (24–26; 26 mm shown) | 67° | 34° | 40° | 🧠 |
| 3× tele (77 mm) | 25° | 13° | 16° | 🧠 |
| 5× tele (120 mm) | 16° | 8° | 10° | 🧠 |

**Table 3 — Residual radial distortion** (4032×3024, f35 26 mm → f_px 3028; cells: displacement px / local anisotropy 2k1r²)

| Radius px (r = px/f) | k1 0.01 | k1 0.02 | k1 0.05 | k1 −0.10 (uncorrected UW-like) | Badge |
|---|---|---|---|---|---|
| 500 (0.17), centred face | 0.1 / 0.05% | 0.3 / 0.11% | 0.7 / 0.27% | 1.4 / 0.55% | 🧠 |
| 1000 (0.33) | 1.1 / 0.22% | 2.2 / 0.44% | 5.5 / 1.1% | 11 / 2.2% | 🧠 |
| 2016 (0.67), long edge | 8.9 / 0.89% | 18 / 1.8% | 45 / 4.4% | 89 / 8.9% | 🧠 |
| 2520 (0.83), corner | 17 / 1.4% | 35 / 2.8% | 87 / 6.9% | 175 / 14% | 🧠 |

**Table 4 — Aspect crops** (native 4:3, 4032 px long side; error if f35 is static but the delivered diagonal is used)

| Delivered | Size | Native/delivered diagonal | f_px error | Badge |
|---|---|---|---|---|
| 4:3 | 4032×3024 | 1.000 | 0 | 🧠 |
| 3:2 | 4032×2688 | 1.040 | −3.8% | 🧠 |
| 16:9 | 4032×2268 | 1.089 | −8.2% | 🧠 |
| 1:1 | 3024×3024 | 1.179 | −15.2% | 🧠 |
| Width-based f35 convention | any | — | +4.0% | ↔️ |

**Table 5 — Decoders for Blender** (licences time-sensitive)

| Package | Licence | Reads | Badge |
|---|---|---|---|
| pillow-heif + Pillow | BSD-3 binding; wheels bundle libheif, libde265 (LGPL-3.0), x265 (GPL-2.0+); Pillow MIT-CMU | HEIC, EXIF/XMP, depth (version-dependent) | ↔️ |
| rawpy (LibRaw) | MIT; LibRaw LGPL-2.1 or CDDL-1.0 | Bayer/linear DNG, vendor raws; opcode warps mostly not applied | ↔️ |
| tifffile / ExifTool | BSD-3 / GPL or Artistic | DNG opcodes; all tags, Apple MakerNotes | 🧠 |
| lensfunpy | MIT; Lensfun LGPL-3, database CC BY-SA 3.0 | lens profiles (not phones) | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Ingest originals** (AirDrop, cable, "original" export). Dump EXIF and MakerNotes to a JSON sidecar *before* converting, since PNG usually drops EXIF (this amends the "convert HEIC to PNG" step in `community/reference-photography-protocol.md`) 🧠. iPhone Formats → Most Compatible captures JPEG 🧠
2. **Triage:** module, zoom (f35/FocalLength vs baseline), aspect, native size, front camera, Portrait (`CustomRendered` 7/8), night (exposure > 1/15 s), face field angle. Reject ultra-wide and beyond-optical zoom; down-weight faces > 25° off-axis 🧠
3. **New references:** 4:3, native resolution, face central (removes Table 4's ambiguity) 🧠
4. **Mirror-check** front-camera photos (hair parting, moles, background text) 🧠
5. **Portrait iPhone photos:** effect off before export; keep the depth map as a distance prior 🧠
6. **Settings checklist** (menu names vary by OS version ↔️):

| Phone | Switch off or set | Badge |
|---|---|---|
| iPhone | Mirror Front Camera off; Preserve Settings on; Macro Control on, macro off (Auto Macro switches to the ultra-wide); Styles Standard; Night and Portrait off. Leave Lens Correction **on** (front/ultra-wide only; rectilinear suits the solver) | ↔️ |
| Pixel | Face retouching off; Save selfies as previewed off; Night Sight off; pick the lens in Pro controls (8 Pro+); RAW+JPEG on | ↔️ |
| Samsung | Face effects 0; Save selfies as previewed off; Scene optimizer off; no zoom beyond optical; Expert RAW for linear DNG | ↔️ |
| Xiaomi / Oppo / Vivo / Honor / Huawei | Beautify 0 including slimming, eye, nose and chin sliders; AI camera off | 🧠 |
| Any | Manual app (Halide, Open Camera, Blackmagic Camera) to lock one lens; stabilisation off for video frame grabs | 🧠 |

7. **Decode in Blender:** HEIC via bundled pillow-heif wheels (`blender/blender-python-ml-deps.md`); RAW via rawpy `postprocess(gamma=(1, 1), no_auto_bright=True, output_bps=16)`, flipped vertically for `Image.pixels.foreach_set`, linear colourspace; apply WarpRectilinear yourself 🧠
8. **What goes wrong** 🧠: off-centre group-shot face solves with wrong yaw (content-aware warp); one lens, two focal lengths (16:9 vs 4:3, or 2× crop); jaw too narrow (beauty slimming); L/R swapped (mirror); ears dissolve (Portrait blur); HEIC rotated twice (`irot` *and* EXIF Orientation).

## Algorithmic implications

- **Metadata reader** (`face3d/io/exif.py` reads JPEG/TIFF only): add HEIC (ISOBMFF `meta` → `iinf` `Exif` item → `iloc`; payload = 4-byte big-endian offset, then TIFF); apply HEIF `irot/imir/clap`, then ignore EXIF Orientation; add 0xA404, 0x9206, 0x9214, 0xA401, 0xA432, 0x0131, 0x829A and OpcodeList1–3 (0xC740/0xC741/0xC74E) 🧠
- **Native frame:** phones are 4:3 native; for other aspects fit two hypotheses, static tag (diagonal = 1.25 × long side for 16:9/3:2, 5/3 × side for 1:1) and updated tag (delivered diagonal); choose by intrinsics-group consistency, else σ_log f = 0.09 🧠
- **Zoom detector:** c = f35/FocalLength; c₀ = mode of c per (Make, Model, LensModel); zoom = c/c₀ > 1.02 means a centred crop: principal point stays central, σ_log f 0.06 (UI rounding) 🧠
- **Intrinsics:** fx = fy, skew 0; principal point at the delivered centre, σ = 1% of width (OIS, assembly), fixed unless ≥ 5 views share the group; f35 from an uncropped 4:3 original σ_log f 0.04 (as `reconstruction/camera-perspective-distortion.md`) 🧠
- **Camera model per view** 🧠:
  1. Corrected main/tele, face within 25°: k = 0 fixed.
  2. Main/tele beyond 25°, or front camera: k1 free, prior N(0, 0.02²).
  3. Ultra-wide or front with the face beyond 25°, or content-aware warp likely: **local virtual camera**, i.e. rotate so the face-centre ray is the axis, f′ = f·sec²(θ/2), principal point at the face centre (the stereographic similarity); or inflate σ_px ×3.
  4. Known calibration (Apple inverse LUT, Android `LENS_DISTORTION`, DNG warp, Dynamic Depth) on an uncorrected image: undistort landmarks, then k = 0.
- **Mirror hypothesis:** fit front-camera views both ways; keep the lower cost if the margin is > 10%, else ask the user 🧠
- **Distance priors (σ on log z)** 🧠: SubjectDistance 0.5; Apple FocusDistanceRange log-uniform over the range widened ×1.5; Android focus distance CALIBRATED 0.2, APPROXIMATE 0.4, UNCALIBRATED ignored; median face depth from TrueDepth 0.05–0.1, from rear disparity 0.2–0.3.
- **Gravity:** Apple `AccelerationVector` → camera pitch/roll prior, σ 5° on pitch because head tilt is unknown 🧠
- **Processing-risk score** per view (front, Portrait, night, beyond-optical zoom, non-native size, editor, C2PA AI-edit marker) sets robust weights and warnings. Geometric beauty is invisible in pixels: flag a view whose eye-width/IOD or bigonial/IOD departs > 3σ from the multi-view consensus 🧠
- **Line-straightness QA:** fit curvature of long background edges; bending beyond Table 3's residual means uncorrected distortion or a content-aware warp 🧠
- **Tests:** synthetic k1 sweep, stereographic face warp, static-tag 16:9 crop and mirror; assert the right model is chosen and shape error < 1 mm 🧠

## Disagreements, myths & open questions

- **"Turn lens correction off for accuracy"** ↔️ is a photogrammetry habit. For a pinhole face solver, rectilinear output *is* the model; only face-aware warps must be avoided, which skipping ultra-wide and front cameras achieves 🧠
- **"RAW is unprocessed":** ProRAW and Expert RAW are merged and denoised; only single-frame Bayer DNG is near-sensor 🧠
- **"Portrait mode is the most accurate face photo":** often a good distance and focal, but the blur destroys the silhouette 🧠
- **Contested:** f35 diagonal vs width, static vs crop-updated ↔️; `LENS_DISTORTION` normalisation, documentation vs practice ↔️; whether Apple's Lens Correction also governs content-aware face correction ↔️; front framing varying within one module (iPhone 11–14 cropped ≈30 mm vs wide ≈23 mm; iPhone 17 square-sensor auto-reframing) ↔️; HEVC patent exposure for decoder distribution ↔️
- **Open** 🧠: residual k1 per model; per-vendor f35 under zoom and aspect (needs a test-shot matrix); calibration in Camera-app HEIC; landmark shifts from fusion; whether Pro Res Zoom excludes faces.

## Sources

None (no harvest or draft existed). Related sourced claims: `reconstruction/camera-perspective-distortion.md`, `reconstruction/camera-pose-solving.md`, `community/reference-photography-protocol.md` (iPhone 17 Pro 4× = 100 mm), `blender/blender-python-ml-deps.md`.

**Further reading (by name, not yet linked)**
- Shih, Lai & Liang, "Distortion-free wide-angle portraits on camera phones", ACM TOG (SIGGRAPH), 2019
- Hasinoff et al., HDR+ burst photography, SIGGRAPH Asia 2016; Wronski et al., "Handheld multi-frame super-resolution", SIGGRAPH 2019
- Apple Developer Documentation: AVCameraCalibrationData, AVDepthData, AVCapturePhotoSettings; WWDC 2017 "Capturing Depth in iPhone Photography"
- Android Developers: CameraCharacteristics, DngCreator; Android Dynamic Depth 1.0 specification (2019)
- Adobe, Digital Negative (DNG) Specification 1.4–1.7
- CIPA DC-008 (Exif); ISO/IEC 23008-12 (HEIF)
- Phil Harvey, ExifTool tag documentation (Apple MakerNotes, CustomRendered)
- Lensfun documentation; pillow-heif, rawpy and LibRaw licence documentation
- Brown, "Decentering distortion of lenses", 1966; Zhang, "A flexible new technique for camera calibration", TPAMI 2000
