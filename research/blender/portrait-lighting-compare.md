# Matching photo lighting and verifying likeness renders

> Checking a likeness render against a photo is three separate jobs. First rebuild the camera: focal length *with* sensor width, principal point and pose. Then approximate the light, direction before balance and low-frequency before sharp. Finally compare render and photo in a colour-managed, masked compositor graph. Blender's still-photo camera matchers are third-party vanishing-point or facade tools built for architecture, so portraits need a landmark-based perspective solve. Two independent tutorials rotate the environment until light direction matches and only then refine locally. Diffuse face shading pins down only about 9 spherical-harmonic lighting terms, so cast shadows, catchlights and highlights carry the rest. Blender blends in linear light and ignores alpha, so Difference maps must be masked, and geometric checks must gate photometric or identity scores.
>
> Evidence status: 1 ✅ / 19 📄 / 40 🧠 / 11 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Camera**
- Still-image camera matching for Blender uses third-party tools: fSpy (standalone; successor to the BLAM add-on), Simple Camera Match (extension) and Photo-Match Camera (paid archviz add-on). 80.lv covered one such app; only its title was seen [1][2][3][11] 📄. Blender's own solver (Movie Clip Editor) needs a tracked sequence with parallax and does not solve a single still 🧠.
- fSpy derives FOV and orientation from vanishing points; with one vanishing point the focal length must be supplied or guessed [1] 📄. Simple Camera Match solves focal length, location and rotation from X/Y/Z lines drawn along orthogonal edges [2] 📄. Photo-Match Camera assumes an upright facade and a level camera, and estimates focal length from a known width and distance [3] 📄.
- Solvers need sensor size as well as focal length [4] 📄. FOV depends only on focal/sensor-width, so a 35 mm-equivalent value typed into a non-36 mm sensor gives the wrong FOV 🧠.
- Viewport lens ≈ 2× camera lens: a user reports it, and a maintainer disputed that it is a bug [4] ↔️. Likely both are right 🧠: as I recall Blender's source, the free perspective viewport applies a fixed zoom of 2 (`CAMERA_PARAM_ZOOM_INIT_PERSP`), so a 50 mm viewport ≈ 25 mm camera FOV. Never read lens values off the free viewport.

**Lighting**
- Direction first: rotate the HDRI or environment until light direction on the subject matches the reference [6][7] ✅. Neither source measures accuracy.
- Then edit the map locally. Lightmap reduces light from under the tires and brightens the headlight reflection [6] 📄.
- Poly Light Match (paid) builds an IBL rig from a reference photo. It has a portrait preset and intensity, distance, height and rotation controls; its accuracy is undocumented [5] 📄.
- Lambertian irradiance is captured by order-2 spherical harmonics: 9 coefficients per channel, about 98–99 % of the kernel's energy (Ramamoorthi & Hanrahan 2001; Basri & Jacobs 2003) 🧠. Diffuse skin shading therefore cannot tell an HDRI from a blurred copy. Sharp-light information sits only in cast shadows (nose, brow, chin), penumbra width, specular highlights and catchlights 🧠.
- The cornea is a convex mirror with a radius of about 7.5–8 mm. Catchlight position gives the light direction, and catchlight shape and size give the source shape and angular size, with one estimate per eye (Nishino & Nayar 2004) 🧠.
- Classic patterns (butterfly, loop, Rembrandt, split) are named by nose-shadow geometry and map to key azimuth and elevation bands (Table D) 🧠.
- Penumbra width ≈ occluder-to-receiver distance × the source's angular diameter. In Blender that is the sun light's Angle, or an area light's Size divided by its distance 🧠.
- On-set capture: a chrome ball, an 18 % grey ball and a colour chart, with bracketed exposures merged to HDR (Debevec & Malik 1997; Debevec 1998) 🧠. Learned estimators (SfSNet 2018; Sun et al. 2019; LeGendre et al. 2020; DiffusionLight 2024) infer light from existing photos; their accuracy on arbitrary portraits is unestablished and the field moves fast 🧠.

**Comparison**
- The Mix node's Factor blends regardless of alpha; Alpha Over respects foreground alpha [8] 📄.
- Blender composites in linear light, while After Effects blends in display space by default [10] 📄. AE limits blends to layer alpha and Blender does not, so black outside the render takes part [10] 📄.
- A shader sees only its own (foreground) result, so Overlay- or Difference-style comparison cannot be built in a material [9] 📄.
- AgX has been the default view transform since 4.0, replacing Filmic, and both apply tone curves. For numeric comparison use Standard, Look None, Exposure 0 and Gamma 1, and tag the photo sRGB so it is linearised 🧠. Camera JPEGs are tone-mapped, so linear residuals against them are approximate; RAW decoded to linear is better 🧠.
- Denoising and the pixel filter (Cycles default: Blackman-Harris, about 1.5 px) soften silhouettes, which shows up as rim lines in difference maps 🧠.
- At selfie distance (about 30 cm) the nose looks roughly 30 % wider relative to the face than at about 1.5 m (Ward et al. 2018) 🧠. Compare only through the matched camera.
- Viewing upside down hides local feature distortions (Thatcher illusion; Thompson 1980). Use it for silhouette and proportion checks, not for eyes or mouth 🧠.

## Numbers & reference tables

**Table A — Still-image camera matchers (own pages)**

| Tool | Input | Solves | Hard assumption | Portrait fit | Badge |
|---|---|---|---|---|---|
| fSpy | Vanishing points | FOV, orientation | ≥2 VPs for focal | Poor without architecture | 📄 [1] |
| Simple Camera Match | X/Y/Z lines on camera background image | Focal, location, rotation | Orthogonal edges | Poor for face crops | 📄 [2] |
| Photo-Match Camera | Known width + distance | Focal, placement | Upright facade, level camera | Not applicable | 📄 [3] |
| Poly Light Match | Photo + preset | IBL rig | Undocumented | Untested | 📄 [5] |

**Table B — Compositor operations**

| Operation | Alpha behaviour | Use | Badge |
|---|---|---|---|
| Alpha Over (render over photo) | Respects foreground alpha | Clean overlay | 📄 [8] |
| Mix, Factor 0–1 | Ignores alpha | Opacity "ghost" | 📄 [8] |
| Mix › Difference | Not alpha-limited; multiply by render alpha × face mask | Error map | 📄 [10] |
| Blend inside a material | No background available | Impossible | 📄 [9] |
| Split node (renamed from "Split Viewer" in 4.x, as I recall) | n/a | Wipe | 🧠 |
| RGB to BW → Map Range (0–0.1→0–1) → Color Ramp | n/a | Luminance heat map | 🧠 |

**Table C — Pinhole ↔ Blender (derived; engine `face3d/geometry/camera.py`)**

| Quantity | Relation | Badge |
|---|---|---|
| Pixel focal | f_px = f_mm · W_px / sensor_w_mm | 🧠 |
| Horizontal FOV | 2·atan(W_px / 2f_px) | 🧠 |
| Lens (Sensor Fit = Horizontal) | lens = f_px · sensor_w / W_px | 🧠 |
| Lens shift | shift = offset_px / D, with D = W (Horizontal fit), H (Vertical), max(W,H) (Auto) | ↔️ |

The shift units come from my memory of Blender's source. The engine divides by max(W,H) while forcing Horizontal fit. That is correct for landscape images, but for portrait-orientation photos the shift would be off by H/W (×1.33 at 3:4). Verify with a round-trip render.

**Table D — Portrait key patterns (typical bands; sources vary)**

| Pattern | Key azimuth | Key elevation | Cue | Badge |
|---|---|---|---|---|
| Butterfly | 0–10° | 30–50° | Symmetric shadow under nose and under chin | 🧠 |
| Loop | 25–45° | 25–40° | Small nose-shadow loop toward mouth corner | 🧠 |
| Rembrandt | 45–60° | 35–50° | Nose and cheek shadows merge; lit triangle under far eye | 🧠 |
| Split | 80–100° | 0–20° | Face halved at the nose | 🧠 |
| Rim/kicker | 110–160° | 0–40° | Bright jaw or ear edge | 🧠 |

**Table E — Lighting-ratio labels → lit/shadow difference in stops (two definitions disagree)**

| Label | Def. A (key+fill):fill | Def. B key:fill | Badge |
|---|---|---|---|
| 2:1 | 1.00 | 1.58 | ↔️ |
| 3:1 | 1.58 | 2.00 | ↔️ |
| 4:1 | 2.00 | 2.32 | ↔️ |
| 8:1 | 3.00 | 3.17 | ↔️ |

Measure stops as log2(lit/shadow), using linear luminance from cheek patches that face the camera similarly. Commercial portraits typically fall around 2:1–4:1 (Def. A) 🧠.

**Table F — Objective comparison metrics**

| Metric | Measures | Lighting-sensitive | Reference scale | Badge |
|---|---|---|---|---|
| Landmark NME (÷ outer inter-ocular distance, IOD) | 2D geometry | No | Detector noise ≈ 3–4 % IOD on 300-W-style sets; conventions vary | 🧠 |
| Contour distance on unoccluded jaw/cheek | Outline | No | px; preferred over IoU, which large areas saturate | 🧠 |
| Masked linear MAE per region | Shading + albedo | Yes | Only after geometry passes | 🧠 |
| SSIM (Wang et al. 2004) | Local structure | Partly | 0–1; no universal threshold | 🧠 |
| LPIPS (2018) / ꟻLIP (2020) | Perceptual | Yes | ꟻLIP built for flip-comparison | 🧠 |
| CIEDE2000 ΔE00 | Colour | Yes | ≈1 just noticeable; 2–3 visible at a glance | 🧠 |
| ArcFace cosine | Identity | Yes (domain gap) | Normalise by photo-vs-photo baseline | ↔️ |

**Table G — Portrait cameras and perspective (scale = 1 + Δ/z, with Δ ≈ 0.12 m nose-tip-to-ear depth assumed)**

| Scenario | f (35 mm-eq.) | Distance | Nose:ear-plane scale | Badge |
|---|---|---|---|---|
| Phone selfie | 22–30 mm | 0.25–0.6 m | 1.20–1.48 | 🧠 |
| Phone main, head and shoulders | 23–28 mm | 0.5–1.0 m | 1.12–1.24 | 🧠 |
| Phone tele / portrait mode | 48–120 mm | 1–2.5 m | 1.05–1.12 | 🧠 |
| Portrait lens | 85–135 mm | 1.5–3 m | 1.04–1.08 | 🧠 |
| Long tele | ≥200 mm | ≥4 m | ≤1.03 | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Camera before sculpt.** Solve the camera from landmarks (`face3d/solve/pnp.py`; see `reference-camera-setup.md`). Set:
   - resolution = photo pixels at 100 %
   - Sensor Fit = Horizontal
   - sensor width, lens and shift, all together

   Put the photo in as a camera background image, and judge alignment only in camera view [4]. Use vanishing-point tools only when real orthogonal edges are visible, and treat their focal length as a prior [1][2]. Undistort wide selfies rather than distorting the render.
2. **Shape check under neutral light.** Use a matte grey material (linear albedo 0.18–0.4), Film Transparent and Cycles, with the denoiser off or fixed. Check silhouette, jaw, ear position, hairline and eye and mouth corners first. MatCaps light in view space, so they are fine for reading form but useless for matching.
3. **Read the photo's light.** Take key azimuth and elevation from the nose-shadow pattern (Table D), direction and source shape from the catchlights, source size from the penumbra, key:fill from lit vs shadow cheek stops (Table E), and any back light from rim highlights.
4. **Build the rig.** Rotate an HDRI (Environment Texture → Mapping, Z rotation) until shadows and terminators match, then rebalance locally [6][7]. Alternatively use an area key, the world as fill and a rim. Set colour with a Blackbody input after white-balancing the photo on a known neutral; sclera and teeth are tinted. Light linking (Cycles 4.0+) keeps rims off the shoulders 🧠. Match the photo's depth of field if its ears or hair are blurred.
5. **Compositor graph** (Table B).
   - Load the photo with an Image node set to sRGB and scale it to render size.
   - Alpha Over for the overlay [8].
   - Mix with an exposed Factor for the ghost [8].
   - Difference → BW → × render alpha × face mask → heat map for the error map [10].
   - A Split wipe.

   Keep the view transform at Standard. Never compare against AE or Photoshop numbers [10].
6. **Human protocol.** View side by side at equal size and eye line. Then blink between them at 1–4 Hz, mirror both, compare in greyscale and blur or squint. Check front, ¾ and profile, because a single view can be matched by a wrong shape paired with a wrong focal length.

**What goes wrong:**
- geometry "fixed" to cancel a lighting difference
- bright outlines from one-pixel misregistration
- sliding contour landmarks treated as fixed points
- AgX left on, or a JPEG treated as linear
- lens shift wrong on portrait-orientation images (Table C)
- EXIF focal length used after a crop
- the viewport lens mistaken for the camera lens [4]

## Algorithmic implications

- **Camera priors.** Use log-focal σ ≈ 0.05–0.1 when EXIF focal length and sensor are known and the image is uncropped. Keep the engine's 0.35 and its 24–200 mm hypotheses when the focal length is guessed. Both are engineering values. Fix the principal point at the image centre unless crop data exists. Add an iris-diameter scale prior of 11.7 ± 0.5 mm, recalled from Google's MediaPipe Iris material (verify), to break the focal/depth ambiguity.
- **Export contract.** Export lens, sensor_width, sensor_fit, shift (divided by the sensor-fit dimension), resolution and matrix_world. Add a round-trip test that projects solved landmarks through a real Blender render and asserts sub-pixel agreement.
- **Lighting stage 1 (SH9).**
  - Model: 27 coefficients (9 per RGB channel), fitted by linear least squares to E(n) = Σ Â_l L_lm Y_lm(n), with Â₀ = π, Â₁ = 2π/3, Â₂ = π/4 and constant per-channel albedo.
  - Weights: Huber, δ ≈ 0.05 linear.
  - Exclude eyes, brows, lips, nostrils, hair and beard, the brightest 2–5 % of pixels, and n·v < 0.3.
  - Ridge-regularise band 2.
  - Profile views see half the normal sphere, so add a weak light-from-above prior: elevation ~N(30°, 25°), azimuth ~N(0°, 60°).
- **Stage 2 (hard light).** Take the key direction from the band-1 vector (L₁,₁, L₁,₋₁, L₁,₀) → (x, y, z), and the ambient from L₀₀. Refine by maximising IoU between rendered and segmented nose and brow cast shadows, and take the angular size from the penumbra. Calibrate Blender intensities against a rendered grey sphere (render, measure, rescale) rather than by closed-form watt conversion, which drifts across engines and versions.
- **Gated verification.**
  - G1: landmark NME, with point-to-curve distance for contour points.
  - G2: contour distance on unoccluded jaw and cheek.
  - G3: photometric MAE, SSIM and LPIPS or ꟻLIP per region, reported only after G1 and G2 pass.
  - G4: identity cosine ÷ photo-vs-photo baseline.

  Starting gates, to calibrate: NME ≤ 2–3 % IOD with landmark σ ≈ 1.5–3 % IOD, and contour mean ≤ 1 % of face height. Never auto-accept on G3 or G4.
- **Multi-view.** Require at least 2 views at least 30° apart in yaw before reporting depth-dependent likeness (nose projection, ear position).
- **Reproducibility record** with every comparison: Blender version, engine and sampling settings, colour-management settings, photo colour space, camera and light parameters, and seed.
- **Graph builder.** Generate Table B from Python behind a version guard. As I recall, Blender 5.0 moved compositing to node groups (`scene.compositing_node_group` instead of `scene.node_tree`) and replaced the Composite node with Group Output. Verify against [13] and the API docs.

## Disagreements, myths & open questions

- **Viewport ≈ 2× lens** [4] ↔️: probably a deliberate zoom factor, not a bug 🧠.
- **Lighting-ratio labels**: the two definitions differ by about 0.6 stop at 2:1 (Table E) ↔️. Store stops, not labels.
- **Three myths the sources contradict:** that a blend mode gives the same result in every app [10]; that vanishing-point matchers work on any photo, when they need orthogonal edges, at least 2 vanishing points, or a facade [1][2][3]; and that a photo comparison can be done in a shader [9].
- **"The exact HDRI is recoverable from a portrait":** diffuse shading constrains only about 9 SH terms per channel 🧠. Beyond the shadow direction, any HDRI with matching low-frequency content fits equally well.
- **"Difference map = shape error":** lighting, albedo, depth of field and tone curves all show up in it.
- **"A high identity score proves likeness":** the domain gap and model-specific thresholds make it relative only ↔️ (see the identity-embeddings note).
- **Engine shift units vs Blender** ↔️: pending a round-trip test.
- **Refuted:** none. Apart from the two-source orientation-first method, the sourced claims remain single-source.
- **Open:** calibrated gates on consented portraits; accuracy of learned light estimators once mapped into a Blender rig; Blender 5.x compositor Python identifiers; selfie-distortion magnitude and the anthropometric Δ; whether joint SH-plus-shape fitting beats manual HDRI rotation.

## Sources

[1] Retiring BLAM and announcing fSpy – a stand alone camera matching app (Blender Artists) — https://blenderartists.org/t/retiring-blam-and-announcing-fspy-a-stand-alone-camera-matching-app — forum (developer announcement) — n.d.
[2] Simple Camera Match (Blender Extensions listing) — https://extensions.blender.org/add-ons/simple-camera-match/ — repo / extension listing — n.d.
[3] Photo-Match Camera (Superhive Market listing) — https://superhivemarket.com/products/photo-match-camera — commercial — n.d.
[4] Blender's camera focal length / sensor size values inaccurate? (Blender Artists) — https://blenderartists.org/t/blenders-camera-focal-length-sensor-size-values-inaccurate/1271788 — forum — n.d.
[5] Poly Light Match – Image Based Lighting Setup (docs) — https://superhivemarket.com/products/poly-light-match---image-based-lighting-setup/docs — commercial (vendor docs) — n.d.
[6] Lightmap Blender tutorial 03 (Smart Car HDRI backplate match) — https://www.lightmap.co.uk/learning/blender-tutorial-03/ — vendor tutorial (snippet only) — n.d.
[7] Term 2 lighting course (Maya environment-light matching, student blog) — https://shimin.myblog.arts.ac.uk/2021/02/23/term2-lighting-course_2 — blog — 2021
[8] Difference between the Mix and AlphaOver node? (Blender Artists) — https://blenderartists.org/t/difference-between-the-mix-and-alphaover-node/431442 — forum — n.d.
[9] What are the exact functions of Blend Modes? (Blender Artists) — https://blenderartists.org/t/what-are-the-exact-functions-of-blend-modes/1485612 — forum — n.d.
[10] Can't replicate After Effects result in Blender with basic nodes (Blender Artists) — https://blenderartists.org/t/cant-replicate-after-effects-result-in-blender-with-basic-nodes-compositing-and-post-processing/1524574 — forum — n.d.
[11] Improving Blender workflows with still image camera matching app (80.lv) — https://80.lv/articles/improving-blender-workflows-with-still-image-camera-matching-app — news (title only) — n.d.
[12] How to Setup HDRI Lighting in Blender 2.93 (BlenderNation) — https://www.blendernation.com/2021/06/30/how-to-setup-hdri-lighting-in-blender-2-93/ — news (snippet only; not cited) — 2021
[13] Blender 5.0 Manual: Cameras — https://docs.blender.org/manual/en/5.0/render/cameras.html — official docs (not retrieved) — n.d.

**Further reading (by name, not yet linked)**
- Debevec & Malik, "Recovering High Dynamic Range Radiance Maps from Photographs", SIGGRAPH 1997; Debevec, "Rendering Synthetic Objects into Real Scenes", SIGGRAPH 1998
- Ramamoorthi & Hanrahan, "An Efficient Representation for Irradiance Environment Maps", SIGGRAPH 2001; Basri & Jacobs, "Lambertian Reflectance and Linear Subspaces", IEEE TPAMI 2003
- Nishino & Nayar, "Eyes for Relighting", SIGGRAPH 2004; Blanz & Vetter, "A Morphable Model for the Synthesis of 3D Faces", SIGGRAPH 1999
- Sengupta et al., "SfSNet", CVPR 2018; Sun et al., "Single Image Portrait Relighting", SIGGRAPH 2019; LeGendre et al., "Learning Illumination from Diverse Portraits", SIGGRAPH Asia 2020; Phongthawee et al., "DiffusionLight", CVPR 2024
- Wang et al., SSIM, IEEE TIP 2004; Zhang et al., LPIPS, CVPR 2018; Andersson et al., "FLIP: A Difference Evaluator for Alternating Images", HPG 2020; Sharma, Wu & Dalal, CIEDE2000 notes, 2005; Deng et al., "ArcFace", CVPR 2019
- Fried et al., "Perspective-aware Manipulation of Portrait Photos", SIGGRAPH 2016; Ward et al., "Nasal Distortion in Short-Distance Photographs: The Selfie Effect", JAMA Facial Plastic Surgery 2018; Thompson, "Margaret Thatcher: A New Illusion", Perception 1980
- Hunter, Biver & Fuqua, *Light: Science and Magic*; Hartley & Zisserman, *Multiple View Geometry in Computer Vision*, 2004
- Blender source: `BKE_camera_params_compute_viewplane`, `CAMERA_PARAM_ZOOM_INIT_PERSP`; Google MediaPipe Iris documentation (iris-diameter constant)
