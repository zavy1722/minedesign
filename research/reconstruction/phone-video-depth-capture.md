# Phone video and depth-sensor capture as engine input

> A 10–20 s head-turn video gives dense yaw coverage through one lens, so every frame can share one unknown focal while the turn supplies the parallax. The costs are lossy, often HDR, often stabilised frames whose intrinsics differ from the still camera's and may wander per frame, plus motion blur; rolling shutter is second-order at sensible turn speeds. Front TrueDepth (structured light, VGA-class, best at 25–50 cm) is the only phone sensor that resolves facial shape at the 1–5 mm scale with metric scale; rear LiDAR and Android ToF give scale and gross size only, and ARKit's 1,220-vertex face mesh is a fitted model, not a measurement. The robust pipeline: record SDR, unstabilised, lens-locked video (or raw RGB-D with intrinsics), decode outside Blender's Python, pick 12–24 sharp neutral frames across yaw bins, solve them with one focal group, and add depth as a robust point-to-plane term with a distance-dependent σ.
>
> Evidence status: 0 ✅ / 0 📄 / 70 🧠 / 31 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Decoding video in and around Blender**
- Blender links FFmpeg into its binary (Movie Clip Editor, VSE, video render) but ships no `ffmpeg` executable or Python binding; `bpy.app.ffmpeg` only reports `supported` and library versions 🧠.
- `bpy.data.movieclips.load(path)` opens a video or image sequence, but there is no supported per-frame pixel read (`Image.pixels` on a MOVIE image yields one cached frame). The dependency-free route is a background job rendering a VSE movie strip to images with View Transform = Standard 🧠. The VSE API renamed `sequences` → `strips` (old name gone in 5.0, as I recall): probe with `hasattr` ↔️.
- Clip-editor operators (`clip.track_markers`, `clip.solve_camera`) need a Clip Editor area, so they fail under `blender -b`; libmv has no Python module 🧠.
- **PyAV** is BSD-3-Clause; its wheels bundle FFmpeg libraries built, to my knowledge, as LGPL. Either way it can ship in a GPL extension; codec patents are the open question ↔️. Blender 5.1+ bundles Python 3.13, so cp313 wheels are needed 🧠.
- **OpenCV** `VideoCapture` is already a dependency but returns 8-bit BGR, truncating 10-bit HDR 🧠.
- **YUV→RGB matrix bugs:** swscale-style conversion falls back to BT.601 when untagged; phone HD is BT.709, HDR BT.2020. Decode to `yuv420p10le` and convert in NumPy with the tagged matrix and range 🧠.
- Phone video is stored landscape plus a rotation matrix that PyAV and older Blender builds ignore ↔️, and is often variable-frame-rate: index frames by PTS 🧠.

**Intrinsics in video**
- iPhone `.mov` files carry `mdta` keys (`com.apple.quicktime.make`, `.model`) and, on recent iOS, `com.apple.quicktime.camera.lens_model` and `com.apple.quicktime.camera.focal_length.35mm_equivalent`; whether the latter describes the stabilised video crop or the still frame is unclear ↔️.
- Android camera MP4s carry no focal tag in my experience. Use a still from the same lens and zoom (EXIF, scaled per Table 1), Camera2 (`LENS_INTRINSIC_CALIBRATION` = [fx, fy, cx, cy, s], `LENS_DISTORTION`) in a capture app, or self-calibration 🧠.
- **Video is a crop of the photo frame.** A 16:9 readout of a 4:3 sensor shortens the diagonal, so a 26 mm-equivalent main camera is ≈28 mm on the video diagonal before stabilisation and ≈31–35 mm with a 10–20 % EIS margin (Table 1): reusing the photo's f35 is an 8–25 % focal error 🧠.
- **EIS** warps each frame (usually a gyro rotation homography plus rolling-shutter correction) and crops. A pure-rotation warp keeps a constant-f pinhole, but crop-window translation moves the principal point by up to the margin (≈5–10 % of width) and decentres distortion ↔️.
- **Lens switching** while zooming changes f, distortion and optical centre (cameras sit ≈1–2 cm apart); iOS has a "Lock Camera" video setting 🧠. **Center Stage** (iPads; iPhone 17 front camera, to my knowledge) reframes digitally during video ↔️ (time-sensitive).
- Front-camera video may be saved mirrored ↔️: run the mirror test (`reconstruction/camera-pose-solving.md`). Live Photos and Motion Photos are free ≈3 s micro-videos 🧠.

**HDR**
- iPhone 12+ records HDR by default as Dolby Vision Profile 8.4: 10-bit HEVC with an HLG/BT.2020 base layer. Android uses HLG (e.g., Pixel) or HDR10/HDR10+ PQ (e.g., Samsung) 🧠.
- HLG/PQ read as Rec.709 looks flat and desaturated: detectors cope, sharpness scores and texture do not 🧠. HLG is nearly scene-referred, so a static path works: inverse OETF → optional OOTF → BT.2020→709 matrix → exposure normalisation → soft clip → sRGB (Table 6). PQ needs real tone mapping (BT.2390 EETF; FFmpeg `zscale`+`tonemap` or `libplacebo`) 🧠. Best: record SDR.
- Blender added 10-bit/HDR video handling during 4.x–5.x as I recall; test each build ↔️.

**Motion**
- Face blur = ω·r·t_exp, camera-independent: a 30°/s turn at 1/60 s smears the nose tip (≈100 mm from the yaw axis) ≈0.9 mm, ≈3 px at 1080p selfie scale (Table 2) 🧠.
- Readout takes ≈10–30 ms per frame ↔️. With the phone upright, readout sweeps across the face, so yaw stretches face width rather than shearing it: ≈0.35 % at 30°/s (Table 3), below landmark noise; it matters for depth–RGB timing and fast pans. Camera2 reports `SENSOR_ROLLING_SHUTTER_SKEW` and `SENSOR_EXPOSURE_TIME` per frame 🧠.

**Depth sensors**
- **TrueDepth** (front): IR dot projector (Apple: >30,000 dots), flood illuminator, IR camera; absolute depth registered to colour; ≈640×480 at ≤30 fps in video; best ≈25–50 cm, poor beyond ≈1 m 🧠.
- **`AVDepthData`:** depth or disparity (1/m, not pixels); `depthDataAccuracy` absolute (TrueDepth, LiDAR) or relative (dual camera); `isDepthDataFiltered` = holes filled, smoothed; `intrinsicMatrix` refers to `intrinsicMatrixReferenceDimensions`: rescale it to the depth map 🧠.
- Portrait HEIC stills embed disparity plus portrait, hair, skin and teeth mattes (free masks) 🧠; rear-camera portrait depth is relative ↔️.
- **ARKit `ARFaceAnchor`:** pose at ≤60 Hz; `ARFaceGeometry` 1,220 vertices, 2,304 triangles, fixed topology, metres, +x = subject's left, +y up, +z out of the face (the engine's head frame); 52 blend shapes 🧠. `capturedDepthData` arrives at ≈15 Hz 🧠. The mesh is a smooth low-dimensional fit without ears, eyeballs or mouth interior: an initialiser, not a scan 🧠. `capturedImage` is landscape and unmirrored, and the intrinsics refer to it 🧠.
- **LiDAR** (rear dToF): `sceneDepth` 256×192 at 60 Hz with confidence, densified from a sparse emitter grid; ≈1 cm error at 1–2 m. Good for scale (σ 2–3 %, as in `blender/import-export-scans.md`), useless for nose or lips 🧠.
- **Android:** no app-accessible front face depth. Rear ToF (Galaxy S10 5G–S20, Huawei P30/Mate Pro) largely vanished after ≈2021, with flying pixels at silhouettes. ARCore Depth (16-bit mm) uses ToF or depth-from-motion; Augmented Faces gives a 468-vertex RGB-only mesh without true scale 🧠.
- **Face accuracy:** fused TrueDepth scans versus clinical stereophotogrammetry: ≈0.5–1.5 mm mean deviation centrally, 2–3+ mm laterally and at the ears; single raw frames ≈0.5–2 mm at 30–40 cm, with a systematic floor averaging cannot remove ↔️.

**Apps** (Table 5; terms change)
- Per-frame depth + intrinsics + poses: Record3D, Stray Scanner, Polycam raw export. Fused meshes: Heges, Scaniverse, KIRI Engine, Polycam, RealityScan Mobile 🧠.
- Cloud apps upload faces to a vendor (`ethics/biometric-privacy.md`) ↔️. Bellus3D, the best-known TrueDepth face scanner, closed in 2022: depend on parseable formats, not vendors 🧠.

## Numbers & reference tables

**Table 1 — Video focal arithmetic.** Main camera 26 mm-equivalent on its 4032×3024 photo (f_px 3,029, diagonal convention), full-width 16:9 readout; margin = fraction cropped per axis.

| Video | EIS margin | f_px | f35 diagonal | f35 width | HFOV | Badge |
|---|---|---|---|---|---|---|
| 3840×2160 | 0 | 2,884 | 28.3 mm | 27.0 mm | 67.3° | 🧠 arithmetic |
| 3840×2160 | 10 % | 3,205 | 31.5 mm | 30.0 mm | 61.8° | 🧠 arithmetic |
| 3840×2160 | 20 % | 3,606 | 35.4 mm | 33.8 mm | 56.1° | 🧠 arithmetic |
| 1920×1080 | 0 / 10 / 20 % | 1,442 / 1,602 / 1,803 | same | same | same | 🧠 arithmetic |
| Typical phone EIS margin | 5–20 % | — | — | — | — | ↔️ |

**Table 2 — Motion blur on the face, mm** (point 100 mm from the yaw axis). Scale: selfie at 0.4 m, 3.6 px/mm at 1080p (IOD ≈227 px), 7.2 at 4K; 2× crop at 1.2 m, 2.4 and 4.8 px/mm.

| Turn speed | 1/30 s | 1/60 s | 1/120 s | 1/250 s | 1/500 s | Badge |
|---|---|---|---|---|---|---|
| 15°/s | 0.87 | 0.44 | 0.22 | 0.10 | 0.05 | 🧠 arithmetic |
| 30°/s | 1.75 | 0.87 | 0.44 | 0.21 | 0.10 | 🧠 arithmetic |
| 60°/s | 3.49 | 1.75 | 0.87 | 0.42 | 0.21 | 🧠 arithmetic |
| 90°/s | 5.24 | 2.62 | 1.31 | 0.63 | 0.31 | 🧠 arithmetic |

**Table 3 — Rolling-shutter width distortion**, phone upright. Landmark noise ≈2–3 % of IOD.

| Motion | 10 ms readout | 20 ms | 30 ms | Badge |
|---|---|---|---|---|
| Head yaw 30°/s | 0.17 % | 0.35 % | 0.52 % | 🧠 arithmetic |
| Head yaw 90°/s | 0.52 % | 1.05 % | 1.57 % | 🧠 arithmetic |
| Handheld rotation 5 / 20°/s | — | 0.23 / 0.93 % | — | 🧠 arithmetic |

**Table 4 — Phone depth sources for faces**

| Source | Resolution, rate | Range | Metric | Face-shape value | Scale σ (log) | Badge |
|---|---|---|---|---|---|---|
| TrueDepth `AVDepthData` | ≈640×480, ≤30 fps | 0.2–1 m | absolute | 2–5 mm features; raw σ 0.5–2 mm | 1–2 % | ↔️ |
| ARKit mesh, TrueDepth | 1,220 v, 60 Hz | same | yes | fit, ≈2–5 mm vs scan (estimate) | 1–2 % | ↔️ |
| ARKit mesh, RGB-only | same | — | assumed | weak | 5–10 % | 🧠 |
| LiDAR `sceneDepth` | 256×192, 60 Hz | 0.3–5 m | absolute | none below ≈1 cm | 2–3 % | 🧠 |
| Rear portrait depth | ≈VGA, stills | — | relative | masks only | — | 🧠 |
| Android rear ToF | ≈240×180–640×480 | 0.2–4 m | absolute | gross; edge artefacts | 2–4 % | 🧠 |
| ARCore Depth, no ToF | low-res, mm | ≤5 m | approximate | none | 5–10 % | 🧠 |
| Video only | — | — | no | landmarks, silhouettes | free; IPD/card prior | 🧠 |

**Table 5 — Capture apps** (last known terms; verify)

| App | Sensors | Output | Depth + K + pose per frame | Terms | Badge |
|---|---|---|---|---|---|
| Record3D (iOS) | LiDAR or TrueDepth | `.r3d` zip (JSON with K and poses, LZFSE float32 depth, JPG), EXR+JPG, PLY, live stream | yes | paid unlocks | ↔️ |
| Stray Scanner (iOS) | LiDAR | `rgb.mp4`, 16-bit PNG depth (mm), `camera_matrix.csv`, `odometry.csv` | yes | open source | 🧠 |
| Polycam | LiDAR, cloud photos, splats | meshes; developer-mode raw data (images, per-frame fx, fy, cx, cy, pose, `blur_score`, depth) | yes (raw) | freemium | ↔️ |
| Heges (iOS) | TrueDepth, LiDAR | fused coloured mesh (PLY, STL, OBJ) | no | paid unlock | ↔️ |
| Scaniverse | LiDAR, on-device photogrammetry, splats | OBJ, FBX, GLB, USDZ, PLY, STL, SPZ | no | free | ↔️ |
| KIRI Engine | cloud photos, LiDAR, 3DGS | OBJ, FBX, GLB, STL, PLY, USDZ | no | freemium | ↔️ |
| RealityScan Mobile | photos, cloud | mesh; images for desktop (`reconstruction/photogrammetry-heads.md`) | no | free, Epic terms | ↔️ |
| Live Link Face (iOS) | TrueDepth | MetaHuman Animator take (video, depth, calibration); ARKit CSV | proprietary | free, Epic terms | 🧠 |
| Apple Object Capture | LiDAR + photos | HEIC with depth → USDZ | per photo | free | 🧠 |

**Table 6 — HDR decode constants** (ITU-R BT.2100/BT.2020/BT.709, SMPTE ST 2084)

| Item | Value | Badge |
|---|---|---|
| HLG inverse OETF | E = E′²/3 for E′ ≤ 0.5; else (exp((E′ − c)/a) + b)/12 | 🧠 |
| HLG a, b, c | 0.17883277, 0.28466892, 0.55991073 | 🧠 (b, c recomputed) |
| HLG system γ | 1.2 + 0.42·log10(L_W/1000) (1.2 at 1,000 cd/m²) | 🧠 |
| PQ m1, m2; c1, c2, c3 | 0.1593017578125, 78.84375; 0.8359375, 18.8515625, 18.6875 | 🧠 |
| Luma Kr, Kb | BT.2020 0.2627, 0.0593; BT.709 0.2126, 0.0722 | 🧠 (recomputed) |
| 10-bit narrow range | Y 64–940, C 64–960 | 🧠 |
| BT.2020→709 linear | [[1.6605, −0.5876, −0.0728], [−0.1246, 1.1329, −0.0083], [−0.0182, −0.1006, 1.1187]] | 🧠 (recomputed) |

## Applying this to photo→3D face sculpting in Blender

1. **Phone settings:** HDR off (or SDR in a manual recorder such as Blackmagic Camera ↔️); 4K60 if offered; Lock Camera on; Center Stage, Cinematic, Portrait video and Action mode off; stabilisation off on a tripod; AE/AF locked; ≥500–1,000 lux diffuse light so the shutter is ≤1/250 s 🧠.
2. **Head-turn capture:** rear main camera on a tripod at 1–1.5 m with the 2× crop, or front camera at 35–45 cm (strong perspective, informative when f is known). Turn profile to profile at ≤20–30°/s, pausing 1 s at 0°, ±45°, ±90°, then chin up/down 15–20°. Neutral face, lips together, eyes ahead, hair off ears and forehead, no glasses. Without depth, hold an ID-1 card (85.60 × 53.98 mm) at the cheek plane for 2 s 🧠.
3. **Orbit capture:** subject still; helper circles at 1–1.5 m, eye level and +20°, ≈15–20 s per arc; lighting stays fixed on the head, which suits texture 🧠.
4. **Depth capture:** TrueDepth at 30–40 cm on a stand; subject turns ±60°; record with Record3D or a small ARKit app saving colour, depth, K, anchor pose and mesh per frame 🧠.
5. **Ingest:** show the artist make, model, lens, f35, rotation, transfer and VFR; convert HLG/PQ or ask for SDR; decode in a worker with PyAV, falling back to OpenCV, then a background VSE render to 16-bit PNG 🧠.
6. **Frame selection:** landmark a 1080-px proxy of every frame; score yaw/pitch, sharpness (variance of Laplacian on a skin-masked crop resampled to IOD = 100 px, relative to the best frame within ±0.5 s), landmark speed and blend shapes. Keep the best full-resolution frame per bin (yaw 0, ±10, ±20, ±30, ±45, ±60, ±75, ±90; pitch ±15); reject blink > 0.35, jawOpen > 0.08 or smile > 0.15 above the clip's frontal median. Solve with 12–24 frames 🧠.
7. **Solve:** one focal group per clip, f prior from Table 1; accept at reprojection RMSE ≲2–3 % of IOD. With libmv, lore calls < 0.3 px good and > 1 px broken; it needs ≥8 tracks shared by both keyframes and rigid, textured features (dot stickers on forehead, temples, nasal bridge and chin, or background in orbit mode) 🧠.
8. **Blender QA:** load the selected frames as an image-sequence MovieClip (VFR-proof), key one camera per frame with the clip as camera background, and scrub silhouette and ears. Show depth as points with a signed-distance heat map; nose tip and chin should sit within ±1–2 mm on TrueDepth 🧠.
9. **What goes wrong:** lens switches (sudden scale jump); EIS principal-point jitter; flat HDR; VFR drift; mirrored selfies; ARKit images left landscape; depth–colour timing offsets; depth holes on hair, brows and beard; IR refraction through glasses; expression creep; lighting rotating across the face 🧠.

## Algorithmic implications

- **Source record:** codec, bit depth, transfer, primaries, matrix, range, rotation, mirrored, VFR, stabilisation, lens, f35; per frame PTS, yaw/pitch, sharpness, blend shapes, landmarks, depth with K rescaled to depth resolution 🧠.
- **Focal:** one `focal_group` per (clip, lens, resolution, stabilisation). log-f σ: metadata f35 with EIS off 0.05; scaled same-lens photo 0.08; EIS on, margin unknown 0.12; unknown 0.35 with the hypothesis set in `reconstruction/camera-perspective-distortion.md`. A per-frame free-focal diagnostic that steps means a lens switch: split the group 🧠.
- **Principal point:** centred with EIS off; with EIS on, a new per-frame offset with σ ≈3 % of width. k1 = 0 for ISP-corrected main-camera video 🧠.
- **Pose (static camera):** second-difference priors on rotation (σ 0.5–1°/frame at 30 fps) and translation (σ 1–2 mm), plus an optional neck pivot initialised on the midline 2–4 cm below the ear canals (the atlanto-axial joint gives about half of axial neck rotation), fixed in camera space with σ 10–20 mm, estimated jointly 🧠.
- **Correlated frames:** keep ≤1–3 frames per 5° of yaw or inflate σ_px by √(frames per bin) 🧠.
- **Rolling shutter:** ignore below 0.5 % predicted stretch; otherwise first-order per-row timing with pose velocity from neighbouring frames; readout from Camera2, else 20 ± 10 ms ↔️.
- **Depth term:** point-to-plane r = n·(P − Q)/σ with σ(z, θ) = √[(σ0·(z/0.35 m)²/cos θ)² + σ_align²], σ0 = 0.7 mm (0.4–1.5), σ_align = 0.5 mm, cut at θ > 70°, Huber δ = 2σ. Mask hair, brows, beard, lashes, eyes, mouth interior, glasses and ear backs (HEIC mattes when present); drop frames turning > 10°/s. Fused frames: σ_eff = √(σ²/N + σ_floor²), σ_floor = 0.5 mm ↔️.
- **Scale prior (log-normal σ):** TrueDepth 1–2 %, LiDAR 2–3 %, ARKit RGB-only 5–10 %, ID-1 card in the face plane 1–2 %, IPD alone ≈6 % 🧠.
- **ARKit mesh prior:** precompute a 1,220 → template correspondence once (NICP); per subject, average neutral-gated meshes, similarity-align, add vertex targets σ 2–3 mm (forehead, nasal dorsum, cheeks, chin) and 4–6 mm (jawline, lateral cheeks), zero on eyelids, lips and nostrils ↔️.
- **What depth buys:** anterior–posterior quantities (nasal and chin projection, brow-to-cornea depth) that frontal photos cannot fix because of the focal/depth ambiguity; report their posterior σ with and without depth 🧠.

## Disagreements, myths & open questions

- **Myth: more frames, more accuracy.** Errors correlate; ≈20 well-spread frames capture most of the gain 🧠.
- **Myth: LiDAR scans faces.** It is centimetre-class; TrueDepth is the face sensor 🧠.
- **Myth: the ARKit face mesh is a scan.** It is a fitted, filtered model 🧠.
- **Contested: stabilised video as pinhole.** Near-pinhole for pure-rotation warps, not when the crop translates; vendors and modes differ ↔️.
- **Contested:** what the iPhone video f35 key describes ↔️; TrueDepth accuracy, which varies with app, fusion, region and reference scanner ↔️.
- **Open:** Blender HDR and rotation handling per version; PyAV's FFmpeg configuration; app formats and terms ↔️.
- **Emerging:** Apple spatial video (MV-HEVC stereo, ≈2 cm baseline; FFmpeg decodes it from about 7.1, to my knowledge) and Cinematic-mode disparity tracks are untested face-depth sources ↔️.

## Sources

No web harvest or earlier draft existed for this topic, so no URLs are cited.

**Further reading (by name, not yet linked)**
- ITU-R BT.2100, BT.2020, BT.709, BT.2087, BT.2390; SMPTE ST 2084
- Apple docs: ARFaceAnchor, ARFaceGeometry, ARFrame, AVDepthData, AVCameraCalibrationData; WWDC 2017 "Capturing Depth in iPhone Photography"
- Android Camera2 reference; ARCore Depth and Augmented Faces docs; Google CAMM spec
- Blender Manual (Motion Tracking), Python API (MovieClip); PyAV docs; FFmpeg filters (zscale, tonemap, libplacebo); nerfstudio Record3D/Polycam docs
- Khoshelham & Elberink, "Accuracy and Resolution of Kinect Depth Data for Indoor Mapping Applications", Sensors 2012
- Newcombe et al., "KinectFusion", ISMAR 2011
- Karpenko et al., "Digital Video Stabilization and Rolling Shutter Correction using Gyroscopes", Stanford tech report 2011
- Hedborg et al., "Rolling Shutter Bundle Adjustment", CVPR 2012
- Pertuz, Puig & Garcia, "Analysis of focus measure operators for shape-from-focus", Pattern Recognition 2013
**Related library notes:** `reconstruction/camera-pose-solving.md`, `reconstruction/camera-perspective-distortion.md`, `reconstruction/photogrammetry-heads.md`, `reconstruction/expression-neutralization.md`, `blender/import-export-scans.md`, `blender/blender-python-ml-deps.md`, `ethics/biometric-privacy.md`.
