# Phone video and depth-sensor capture as engine input

> A 10–20 s head-turn video gives the engine what a few photos cannot: dense yaw coverage through one lens at one focal length, so every frame can share a single unknown focal while the turn supplies the parallax. The costs are lossy, often HDR, often stabilised frames whose intrinsics differ from the still camera's and may wander per frame, plus motion blur; rolling shutter is second-order at sensible turn speeds. The front TrueDepth sensor (structured light, VGA-class, best at 25–50 cm) is the only phone sensor that resolves facial shape at the millimetre-to-few-millimetre scale with metric scale; rear LiDAR and Android ToF are good for scale and gross head size only, and ARKit's 1,220-vertex face mesh is a fitted model, not a measurement. The robust pipeline: record SDR, unstabilised, lens-locked video (or raw RGB-D with intrinsics); decode it outside Blender's Python; pick 12–24 sharp, neutral frames across yaw bins; solve them in the engine's bundle adjustment with one focal group; and add depth as a robust point-to-plane term with a distance-dependent σ. No harvest or earlier draft existed for this topic, so every item is expert knowledge or arithmetic.
>
> Evidence status: 0 ✅ / 0 📄 / 87 🧠 / 31 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Decoding video in and around Blender**
- Blender links FFmpeg into its binary (Movie Clip Editor, VSE, movie images, video render) but ships no `ffmpeg` executable and no Python binding; `bpy.app.ffmpeg` only reports `supported` and library version strings 🧠.
- `bpy.data.movieclips.load(path)` opens a video or a numbered image sequence (`size`, `fps`, `frame_duration`, `frame_start`, `colorspace_settings`, `tracking`). There is no supported per-frame pixel read: `Image.pixels` on a MOVIE image yields one cached frame. The dependency-free route is a background Blender job that renders a VSE movie strip (or Compositor Movie Clip → File Output) to an image sequence with View Transform = Standard 🧠.
- The VSE Python API renamed `sequences` → `strips` (deprecated around 4.4, removed in 5.0, to my recollection): probe with `hasattr` ↔️.
- Clip-editor operators (`clip.track_markers`, `clip.solve_camera`) need a Clip Editor area in context, so they do not run under `blender -b`; libmv is not exposed as a Python module 🧠.
- **PyAV** (Python bindings to FFmpeg's libraries) is BSD-3-Clause; its wheels bundle FFmpeg shared libraries, built (to my knowledge) in an LGPL configuration. Either way it is GPL-compatible and may ship in a GPL extension; codec patents (HEVC, H.264) are the residual question, not copyright ↔️. Blender 5.1+ bundles Python 3.13, so cp313 wheels are needed (`blender/blender-python-ml-deps.md`) 🧠.
- **OpenCV** `VideoCapture` (FFmpeg backend in the pip wheels, Apache-2.0) is already in the add-on's dependency set but returns 8-bit BGR: 10-bit HDR is truncated without tone mapping 🧠.
- **YUV→RGB matrix bugs are common.** swscale-style conversion falls back to BT.601 when the stream is untagged or the caller passes no colourspace; phone HD is BT.709 and HDR is BT.2020 non-constant-luminance. Decode to planar YUV (`yuv420p10le`) and convert in NumPy with the tagged matrix and range 🧠.
- Phone video is stored in sensor (landscape) orientation with a display-matrix rotation; PyAV, and at least older Blender versions, do not auto-rotate ↔️. Phone video is often variable-frame-rate: index frames by PTS, not index × fps. Blender MovieClip proxies built with a Record Run timecode index give frame-accurate seeking 🧠.

**Intrinsics in video**
- iPhone QuickTime files carry `mdta` keys (`com.apple.quicktime.make`, `.model`, `.software`) and, on recent iOS, a lens-model string and a 35 mm-equivalent focal (`com.apple.quicktime.camera.lens_model`, `com.apple.quicktime.camera.focal_length.35mm_equivalent`). Whether that number describes the stabilised video crop or the still frame is unclear ↔️.
- Android camera MP4s carry no focal tag in my experience. Intrinsics come from a still taken with the same lens and zoom (EXIF, then Table 1 scaling), from Camera2 in a capture app (`LENS_INTRINSIC_CALIBRATION` = [fx, fy, cx, cy, s], `LENS_DISTORTION`, `LENS_FOCAL_LENGTH` with `SENSOR_INFO_PHYSICAL_SIZE`), or from self-calibration 🧠.
- **Video is a crop of the photo frame.** A 16:9 readout of a 4:3 sensor keeps the width but shortens the diagonal, so a 26 mm-equivalent main camera is ≈28 mm on the video diagonal before stabilisation and ≈31–35 mm with a 10–20 % EIS margin (Table 1). Reusing the photo's f35 for video is an 8–25 % focal error 🧠.
- **Electronic stabilisation (EIS)** warps each frame, usually with a gyro-driven rotation homography plus rolling-shutter correction, then crops. A pure-rotation warp keeps a pinhole camera with constant f, but crop-window translation moves the principal point by up to the margin (≈5–10 % of width) and decentres lens distortion. Cinematic/Action modes crop more ↔️.
- **Lens switching:** zooming while recording hops between physical cameras (different f, distortion, and optical centres ≈1–2 cm apart). iOS has a "Lock Camera" record-video setting 🧠.
- **Auto-reframing:** Center Stage (iPads; the front camera of the 2025 iPhone 17 line, to my knowledge) pans and zooms digitally during video, so intrinsics change per frame ↔️ (time-sensitive).
- Front-camera video may be stored mirrored, depending on the "Mirror Front Camera" setting ↔️; run the mirror test in `reconstruction/camera-pose-solving.md`.
- iPhone Live Photos (a ≈3 s HEVC clip paired with each still) and Android Motion Photos are free micro-videos for choosing the most neutral or sharpest moment 🧠.

**HDR**
- iPhone 12 and later record HDR by default as Dolby Vision Profile 8.4: 10-bit HEVC whose base layer is HLG/BT.2020, with dynamic metadata that decoders may ignore. Android records HLG (e.g., Pixel) or HDR10/HDR10+ PQ (e.g., Samsung) when HDR is on 🧠.
- HLG or PQ decoded as if Rec.709 gives flat, desaturated frames: detectors mostly cope, but sharpness scores, colour and texture are wrong 🧠.
- HLG is nearly scene-referred, so a static conversion works: inverse OETF → optional OOTF (γ 1.2 at 1,000 cd/m²) → BT.2020→BT.709 matrix → exposure normalisation → soft clip → sRGB OETF (Table 6). PQ needs real tone mapping (BT.2390 EETF; FFmpeg `zscale`+`tonemap` or `libplacebo`) 🧠. Best of all, record SDR.
- Blender gained high-bit-depth and HDR (PQ/HLG) video handling during the 4.x–5.x cycle as I recall; whether a given build reads 10-bit HLG as correctly tagged float must be tested per version ↔️.

**Motion**
- Face blur = ω·r·t_exp, independent of the camera: a 30°/s turn at 1/60 s smears the nose tip (≈100 mm from the yaw axis) by ≈0.9 mm, ≈3 px at 1080p selfie scale (Table 2). Phones pick 1/30–1/120 s indoors 🧠.
- Rolling-shutter readout is ≈10–30 ms per frame ↔️. With the phone upright, sensor rows run across the face, so a yaw turn stretches or squeezes face width rather than shearing it: ≈0.35 % at 30°/s and 20 ms (Table 3), below landmark noise. It matters for depth–RGB timing and fast handheld pans 🧠.
- Camera2 reports `SENSOR_ROLLING_SHUTTER_SKEW` and `SENSOR_EXPOSURE_TIME` per frame; Google's CAMM metadata track has a rolling-shutter-skew field, but few phones write it 🧠.

**Depth sensors**
- **TrueDepth** (front, Face ID): IR dot projector (Apple says >30,000 dots), flood illuminator and IR camera; absolute depth registered to the colour camera; ≈640×480 depth/disparity at up to ≈30 fps in video, larger in stills; best at ≈25–50 cm, poor beyond ≈1 m 🧠.
- `AVDepthData`: Float16/Float32 depth or disparity, where disparity is 1/metres, not pixels; `depthDataAccuracy` is absolute (TrueDepth, LiDAR) or relative (dual-camera); `isDepthDataFiltered` means holes filled and smoothed; `cameraCalibrationData` gives `intrinsicMatrix` relative to `intrinsicMatrixReferenceDimensions` (rescale to the depth-map size), lens-distortion lookup tables and `pixelSize` 🧠.
- Portrait HEIC stills embed the disparity map, a portrait-effects matte and (since iOS 13) semantic mattes for hair, skin and teeth: free masks for excluding hair 🧠. Recent iPhones store depth with ordinary photos of people; rear-camera depth is usually relative, not metric ↔️.
- **ARKit face tracking** (`ARFaceAnchor`): pose at up to 60 Hz; `ARFaceGeometry` with 1,220 vertices and 2,304 triangles in a fixed topology, in metres, +x = subject's left, +y up, +z out of the face (the engine's head frame); eye transforms, `lookAtPoint` and 52 blend-shape coefficients 🧠. `capturedDepthData` arrives at a lower rate (≈15 Hz) than colour 🧠. The mesh is a low-dimensional fit, smooth at the 5–10 mm scale, with no ears, back of head, eyeballs or mouth interior: an initialiser, not a scan 🧠.
- `capturedImage` is in sensor (landscape) orientation and unmirrored, and ARKit intrinsics refer to it; the on-screen selfie preview is mirrored 🧠. Without TrueDepth (A12+, iOS 14+) ARKit face tracking runs from RGB at an assumed scale 🧠.
- **LiDAR** (rear, dToF): `sceneDepth` 256×192 at 60 Hz with a confidence map, from a sparse emitter grid densified with RGB; ≈1 cm absolute error at 1–2 m; meshes are smooth at the centimetre scale. Useful for scale (σ 2–3 %, as in `blender/import-export-scans.md`), useless for nose or lip shape 🧠.
- **Android:** front face depth is effectively unavailable to apps. Rear ToF (Galaxy S10 5G–S20, Huawei P30/Mate Pro and others) left most flagships after ≈2021; ≈240×180–640×480, with multipath and flying pixels at the silhouette, weak on dark hair. ARCore Depth (16-bit mm) uses ToF when present, otherwise depth-from-motion; ARCore Augmented Faces gives a 468-vertex RGB-only mesh without true metric scale 🧠.
- **Face accuracy:** fused TrueDepth scans versus clinical stereophotogrammetry report ≈0.5–1.5 mm mean deviation over the central face and 2–3+ mm laterally and at the ears; single raw frames are noisier (≈0.5–2 mm at 30–40 cm), with a systematic floor that averaging does not remove ↔️.

**Apps** (Table 5; terms change)
- Per-frame depth + intrinsics + poses: Record3D, Stray Scanner and Polycam's raw-data export. Fused meshes: Heges, Scaniverse, KIRI Engine, Polycam, RealityScan Mobile 🧠.
- Cloud apps (Polycam photo mode, KIRI, RealityScan Mobile) upload face images to a vendor; that is biometric data (`ethics/biometric-privacy.md`) ↔️. Bellus3D, the best-known TrueDepth face scanner, closed in 2022 🧠: build on formats you can parse, not on one vendor app.

## Numbers & reference tables

**Table 1 — Video focal arithmetic.** A main camera that is 26 mm-equivalent on its 4032×3024 photo (f_px 3,029, diagonal convention); assumes full-width 16:9 readout; EIS margin = fraction cropped per axis.

| Video | EIS margin | f_px | f35 (diagonal) | f35 (36 mm width) | HFOV | Badge |
|---|---|---|---|---|---|---|
| 3840×2160 | 0 | 2,884 | 28.3 mm | 27.0 mm | 67.3° | 🧠 arithmetic |
| 3840×2160 | 10 % | 3,205 | 31.5 mm | 30.0 mm | 61.8° | 🧠 arithmetic |
| 3840×2160 | 20 % | 3,606 | 35.4 mm | 33.8 mm | 56.1° | 🧠 arithmetic |
| 1920×1080 | 0 / 10 / 20 % | 1,442 / 1,602 / 1,803 | as above | as above | as above | 🧠 arithmetic |
| typical phone EIS margin | 5–20 % | — | — | — | — | ↔️ |

**Table 2 — Motion blur on the face, mm** (point 100 mm from the yaw axis). To convert: selfie at 0.4 m, ≈28 mm-equivalent video: 3.6 px/mm at 1080p (IOD ≈227 px), 7.2 at 4K; 2× crop at 1.2 m: 2.4 and 4.8 px/mm.

| Turn speed | 1/30 s | 1/60 s | 1/120 s | 1/250 s | 1/500 s | Badge |
|---|---|---|---|---|---|---|
| 15°/s | 0.87 | 0.44 | 0.22 | 0.10 | 0.05 | 🧠 arithmetic |
| 30°/s | 1.75 | 0.87 | 0.44 | 0.21 | 0.10 | 🧠 arithmetic |
| 60°/s | 3.49 | 1.75 | 0.87 | 0.42 | 0.21 | 🧠 arithmetic |
| 90°/s | 5.24 | 2.62 | 1.31 | 0.63 | 0.31 | 🧠 arithmetic |

**Table 3 — Rolling-shutter width distortion**, phone upright (readout sweeps across the face). Landmark noise is ≈2–3 % of IOD.

| Motion | 10 ms readout | 20 ms | 30 ms | Badge |
|---|---|---|---|---|
| Head yaw 30°/s | 0.17 % | 0.35 % | 0.52 % | 🧠 arithmetic |
| Head yaw 90°/s | 0.52 % | 1.05 % | 1.57 % | 🧠 arithmetic |
| Handheld camera rotation 5°/s / 20°/s | — | 0.23 % / 0.93 % | — | 🧠 arithmetic |

**Table 4 — Phone depth sources for faces**

| Source | Resolution, rate | Range | Metric | Face-shape value | Scale σ (log) | Badge |
|---|---|---|---|---|---|---|
| TrueDepth `AVDepthData` | ≈640×480, ≤30 fps | 0.2–1 m (best 0.25–0.5) | absolute | nose, lips, brow at 2–5 mm wavelengths; raw σ 0.5–2 mm | 1–2 % | ↔️ |
| ARKit face mesh (TrueDepth) | 1,220 v / 2,304 tris, 60 Hz | same | yes | model fit, ≈2–5 mm vs scan (estimate) | 1–2 % | ↔️ |
| ARKit face mesh, RGB-only | same | — | assumed | weak | 5–10 % | 🧠 |
| LiDAR `sceneDepth` | 256×192, 60 Hz + confidence | 0.3–5 m | absolute | none below ≈1 cm | 2–3 % | 🧠 |
| Rear dual-camera/ML portrait depth | ≈VGA, stills | — | relative | masks only | — | 🧠 |
| Android rear ToF | ≈240×180–640×480 | 0.2–4 m | absolute | gross only; edge artefacts | 2–4 % | 🧠 |
| ARCore Depth without ToF | low-res, 16-bit mm | best ≤ 5 m | approximate | none | 5–10 % | 🧠 |
| Video only (SfM / landmark BA) | — | — | no | via landmarks, silhouettes | free; IPD or card prior | 🧠 |

**Table 5 — Capture apps** (terms as last known; verify before relying on them)

| App | Sensors | Output | Per-frame depth + K + pose | Terms | Badge |
|---|---|---|---|---|---|
| Record3D (iOS) | LiDAR or TrueDepth | `.r3d` zip (JSON metadata with K and poses, LZFSE-compressed float32 depth, JPG colour, confidence), EXR+JPG, PLY sequences, USB/Wi-Fi stream | yes | free app, paid unlocks for export/streaming | ↔️ |
| Stray Scanner (iOS) | LiDAR | `rgb.mp4`, 16-bit PNG depth in mm, confidence, `camera_matrix.csv`, `odometry.csv` | yes | open source (licence unverified) | 🧠 |
| Polycam | LiDAR, cloud photo mode, splats | OBJ, FBX, GLB, USDZ, PLY, STL…; developer-mode raw data: images, per-frame camera JSON (fx, fy, cx, cy, pose, `blur_score`), depth | yes (raw) | freemium subscription | ↔️ |
| Heges (iOS) | TrueDepth, LiDAR | fused coloured mesh (PLY, STL, OBJ) | no | paid unlock | ↔️ |
| Scaniverse | LiDAR + on-device photogrammetry, splats | OBJ, FBX, GLB, USDZ, PLY, STL, LAS, SPZ | no | free (Niantic Spatial) | ↔️ |
| KIRI Engine | cloud photogrammetry, LiDAR, 3DGS | OBJ, FBX, GLB, STL, PLY, USDZ | no | freemium | ↔️ |
| RealityScan Mobile | photos, cloud | mesh via Epic's pipeline; images to desktop RealityScan (`reconstruction/photogrammetry-heads.md`) | no | free, Epic terms | ↔️ |
| Live Link Face (iOS) | TrueDepth | MetaHuman Animator take (video, depth, calibration, Epic format); ARKit CSV | depth, proprietary | free, Epic terms | 🧠 |
| Apple Object Capture | LiDAR + photos | HEIC with depth and gravity → USDZ | per-photo depth | free | 🧠 |

**Table 6 — HDR decode constants** (ITU-R BT.2100, BT.2020, BT.709; SMPTE ST 2084)

| Item | Value | Badge |
|---|---|---|
| HLG inverse OETF | E = E′²/3 for E′ ≤ 0.5; else E = (exp((E′ − c)/a) + b)/12 | 🧠 |
| HLG a, b, c | 0.17883277, 0.28466892, 0.55991073 | 🧠 (b, c recomputed) |
| HLG system γ | 1.2 at 1,000 cd/m²; 1.2 + 0.42·log10(L_W/1000) | 🧠 |
| PQ m1, m2 / c1, c2, c3 | 0.1593017578125, 78.84375 / 0.8359375, 18.8515625, 18.6875 | 🧠 |
| Luma Kr, Kb | BT.2020 0.2627, 0.0593; BT.709 0.2126, 0.0722 | 🧠 (recomputed) |
| 10-bit narrow range | Y 64–940, Cb/Cr 64–960 | 🧠 |
| BT.2020 → BT.709, linear | [[1.6605, −0.5876, −0.0728], [−0.1246, 1.1329, −0.0083], [−0.0182, −0.1006, 1.1187]] | 🧠 (recomputed from primaries) |

## Applying this to photo→3D face sculpting in Blender

1. **Phone settings.** HDR Video off (or SDR Rec.709 in a manual-control recorder such as Blackmagic Camera ↔️); 4K at 60 fps if offered; Lock Camera on; Center Stage, Cinematic, Portrait video and Action mode off (synthetic blur, heavy crops); stabilisation off where the app allows, on a tripod; AE/AF locked; diffuse light of ≥500–1,000 lux so the shutter lands at ≤1/250 s 🧠.
2. **Head-turn capture** (phone fixed). Either the rear main camera on a tripod at 1–1.5 m with the 2× crop and a helper, or the front camera at 35–45 cm (strong perspective, which the solver exploits when f is known). Turn profile to profile at ≤20–30°/s (≥8 s per 180°), pausing 1 s at 0°, ±45° and ±90°, then chin up and down 15–20°. Neutral face, lips together, eyes straight ahead of the nose (not tracking the lens), hair off ears and forehead, no glasses. Without depth, hold an ID-1 card (85.60 × 53.98 mm) flat at the cheek plane for 2 s 🧠.
3. **Orbit capture** (helper walks, subject still) at a constant 1–1.5 m, eye level and +20°, ≈15–20 s per arc. Lighting stays fixed on the head, which suits texture extraction (`reconstruction/albedo-lighting-inverse-rendering.md`) 🧠.
4. **Depth capture.** Front camera (TrueDepth) at 30–40 cm on a stand or held by a helper; subject turns ±60°. Record with Record3D or a small custom ARKit app that saves per-frame colour, depth, K, anchor pose and the 1,220-vertex mesh 🧠.
5. **Ingest.** Read container metadata (make, model, lens, f35, rotation, transfer function, VFR) and show it to the artist. Detect HLG/PQ and convert (Table 6) or ask for SDR. Decode in a worker process with PyAV; fall back to OpenCV, then to a background Blender VSE render to 16-bit PNG 🧠.
6. **Frame selection.** Run landmarks on a 1080-px proxy of every frame; compute yaw/pitch, sharpness (variance of the Laplacian on a skin-masked crop resampled to IOD = 100 px, compared with the best frame within ±0.5 s), landmark speed and blend-shape scores. Keep the best full-resolution frame per bin (yaw 0, ±10, ±20, ±30, ±45, ±60, ±75, ±90; pitch ±15). Reject blink > 0.35, jawOpen > 0.08 or smile > 0.15 above the clip's frontal median. Use 12–24 frames to solve, up to 40–60 for texture 🧠.
7. **Solve.** One focal group per clip, f prior from Table 1 rather than the photo's f35. Accept at reprojection RMSE ≲2–3 % of IOD (detector landmarks). With libmv, community lore calls a solve error < 0.3 px good and > 1 px broken; libmv also needs ≥8 tracks shared by its two keyframes and only rigid, textured features (dot stickers on forehead, temples, nasal bridge and chin, or the background in orbit mode) 🧠.
8. **Blender QA.** Write the selected frames as an image sequence and load that as a MovieClip (deterministic, VFR-proof frame mapping); key one camera per selected frame, show the clip as camera background and scrub for silhouette and ear alignment. Show depth points as a point-cloud object with a signed-distance heat map: nose tip and chin should sit within ±1–2 mm on TrueDepth data 🧠.
9. **What goes wrong:** a mid-clip lens switch (a sudden jump in face scale); principal-point jitter under EIS; flat HDR frames; VFR drift between Blender and the decoder; mirrored front video; ARKit images left in sensor orientation; depth–colour timing offsets during motion; holes on IR-dark hair, brows and beard; IR refraction through glasses; expression creep over long clips; lighting rotating across the face in head-turn mode 🧠.

## Algorithmic implications

- **Source record:** path, codec, bit depth, transfer (sdr | hlg | pq), primaries, matrix, range, rotation, mirrored flag, VFR flag, user-declared stabilisation, lens id, metadata f35, size. Per selected frame: PTS, yaw/pitch, sharpness, blend-shape scores, landmarks, optional depth path with K rescaled to depth resolution 🧠.
- **Focal:** one `focal_group` per (clip, lens, resolution, stabilisation). log-f σ: metadata f35 with EIS off 0.05; scaled from a same-lens photo 0.08; EIS on with unknown margin 0.12; nothing known 0.35 with the hypothesis set from `reconstruction/camera-perspective-distortion.md`. Re-solve with per-frame free focal as a diagnostic: a step means a lens switch, so split the group 🧠.
- **Principal point:** fixed at the centre when EIS is off; with EIS on, add a per-frame offset (new parameter) with σ ≈3 % of width. Keep k1 = 0 for ISP-corrected main-camera video; reject ultrawide 🧠.
- **Pose regularisation (static camera, head turning):** second-difference priors on rotation (σ 0.5–1° per frame at 30 fps) and translation (σ 1–2 mm), plus an optional pivot prior: a head-frame point, initialised on the midline 2–4 cm below the ear canals (the atlanto-axial joint provides about half of axial neck rotation), stays fixed in camera space with σ 10–20 mm and is estimated jointly 🧠.
- **Correlated frames:** detector errors in neighbouring frames are correlated; keep ≤1–3 frames per 5° of yaw or inflate σ_px by √(frames per bin) 🧠.
- **Rolling shutter:** skip when the predicted stretch is < 0.5 %. Otherwise use a first-order model with per-row time and pose velocity from neighbouring frames (no new unknowns); readout from Camera2 metadata, else 20 ms ± 10 ms ↔️.
- **Depth term:** back-project depth pixels with the rescaled K, transform by the frame pose, and use point-to-plane residuals to the template, r = n·(P − Q)/σ, with σ(z, θ) = √[(σ0·(z/0.35 m)²/cos θ)² + σ_align²], σ0 = 0.7 mm (range 0.4–1.5), σ_align = 0.5 mm, cut at θ > 70°, Huber δ = 2σ. Mask out hair, brows, beard, lashes, eyes, mouth interior, glasses and ear backs (use the HEIC semantic mattes when present). Drop depth frames where the head turns faster than 10°/s. For N fused frames, σ_eff = √(σ²/N + σ_floor²) with σ_floor = 0.5 mm 🧠 ↔️.
- **Scale prior (log-normal σ):** TrueDepth 1–2 %, LiDAR 2–3 %, ARKit RGB-only 5–10 %, ID-1 card in the face plane 1–2 %, IPD only ≈6 % 🧠.
- **ARKit mesh prior:** build a fixed 1,220 → template correspondence once (NICP on a neutral ARKit mesh). Per subject, average neutral-gated anchor meshes, similarity-align them, and add vertex targets with σ 2–3 mm (forehead, nasal dorsum, cheeks, chin) and 4–6 mm (jawline, lateral cheeks), zero on eyelids, lips and nostrils ↔️.
- **What depth buys:** anterior–posterior quantities (nasal and chin projection, brow-to-cornea depth) that frontal photos cannot fix because of the focal/depth ambiguity. Report their posterior σ with and without depth 🧠.

## Disagreements, myths & open questions

- **Myth: more frames give more accuracy.** Errors are correlated; ≈20 well-spread frames capture most of the gain 🧠.
- **Myth: LiDAR scans faces.** Rear LiDAR is centimetre-class; TrueDepth is the face sensor 🧠.
- **Myth: the ARKit face mesh is a scan.** It is a fitted, temporally filtered model 🧠.
- **Myth: AVDepthData disparity is in pixels.** It is 1/m 🧠.
- **Contested: can stabilised video be treated as pinhole?** Near-pinhole if the warp is a pure rotation; not if the crop window translates or distortion correction is decentred. Implementations differ by vendor and mode ↔️.
- **Contested:** what the iPhone video f35 key describes (stabilised crop or still frame) ↔️; TrueDepth accuracy figures, which vary with app, fusion, face region and reference scanner ↔️.
- **Open:** Blender's 10-bit/HDR reading and rotation-metadata handling per version ↔️; PyAV wheel FFmpeg configuration and codec-patent exposure ↔️; app formats and terms ↔️; front-facing depth on Android 🧠.
- **Emerging:** Apple spatial video (MV-HEVC stereo with a stored baseline, decodable by FFmpeg since about 7.1 to my knowledge) offers ≈2 cm-baseline stereo; Cinematic-mode files store disparity tracks. Both are unexplored as face-depth sources ↔️.

## Sources

No web harvest or earlier draft existed for this topic, so no URLs are cited; everything above is expert knowledge (🧠) or contested (↔️) and awaits verification.

**Further reading (by name, not yet linked)**
- ITU-R BT.2100 (PQ and HLG), BT.2020, BT.709, BT.2087 (colour conversion) and BT.2390 (HDR report, EETF); SMPTE ST 2084
- Apple Developer Documentation: ARFaceAnchor, ARFaceGeometry, ARFrame (capturedDepthData, sceneDepth), AVDepthData, AVCameraCalibrationData; WWDC 2017 "Capturing Depth in iPhone Photography"
- Android Camera2 reference (LENS_INTRINSIC_CALIBRATION, LENS_DISTORTION, SENSOR_ROLLING_SHUTTER_SKEW); ARCore Depth API and Augmented Faces documentation; Google Camera Motion Metadata (CAMM) specification
- Blender Manual, Movie Clip Editor and Motion Tracking; Blender Python API (MovieClip, MovieTrackingCamera, MovieTrackingSettings)
- PyAV documentation; FFmpeg filter documentation (zscale, tonemap, libplacebo); nerfstudio data-processing docs for Record3D and Polycam captures
- Khoshelham & Elberink, "Accuracy and Resolution of Kinect Depth Data for Indoor Mapping Applications", Sensors 2012
- Newcombe et al., "KinectFusion: Real-Time Dense Surface Mapping and Tracking", ISMAR 2011
- Karpenko, Jacobs, Baek & Levoy, "Digital Video Stabilization and Rolling Shutter Correction using Gyroscopes", Stanford CS Tech Report 2011
- Grundmann, Kwatra & Essa, "Auto-Directed Video Stabilization with Robust L1 Optimal Camera Paths", CVPR 2011
- Hedborg, Forssén, Felsberg & Ringaby, "Rolling Shutter Bundle Adjustment", CVPR 2012
- Pertuz, Puig & Garcia, "Analysis of focus measure operators for shape-from-focus", Pattern Recognition 2013
- Zhang, "A Flexible New Technique for Camera Calibration", IEEE TPAMI 2000
- Zollhöfer et al., "State of the Art on Monocular 3D Face Reconstruction, Tracking, and Applications", Eurographics STAR 2018

**Related library notes:** `reconstruction/camera-pose-solving.md`, `reconstruction/camera-perspective-distortion.md`, `reconstruction/photogrammetry-heads.md`, `reconstruction/expression-neutralization.md`, `reconstruction/albedo-lighting-inverse-rendering.md`, `blender/import-export-scans.md`, `blender/blender-python-ml-deps.md`, `ethics/biometric-privacy.md`.
