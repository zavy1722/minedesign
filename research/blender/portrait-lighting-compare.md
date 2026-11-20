# Matching photo lighting and verifying likeness renders

> Checking a likeness render against a photo is three separate jobs. First rebuild the camera: focal length *with* sensor width, principal point and pose. Then approximate the light, getting direction right before balance and low-frequency light before sharp detail. Finally compare render and photo in a colour-managed, masked compositor graph. Blender's still-photo camera matchers are third-party vanishing-point or facade tools built for architecture, so bare portraits need a landmark-based perspective solve. Two independent tutorials rotate the environment until light direction matches and only then refine locally. Physics adds a limit: diffuse face shading pins down only about 9 spherical-harmonic lighting coefficients, so cast shadows, catchlights and highlights have to carry the rest. Blender blends in linear light and ignores alpha, so Difference maps must be masked, and geometric checks must gate photometric or identity scores, because a lighting error looks like a shape error.
>
> Evidence status: 1 ✅ / 26 📄 / 50 🧠 / 6 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Camera**
- Still-image camera matching for Blender is done with third-party tools: fSpy (a standalone successor to the BLAM add-on), Simple Camera Match (an extension) and Photo-Match Camera (a paid archviz add-on). 80.lv covered a still-image matching app, but only its title was seen [1][2][3][11] 📄. Blender's built-in camera solver is in the Movie Clip Editor and needs a tracked image sequence with parallax, so it does not solve a single still 🧠.
- fSpy computes field of view and camera orientation from vanishing points. With only one vanishing point, the user has to supply the focal length or find it by trial and error [1] 📄.
- Simple Camera Match: draw X/Y/Z lines along orthogonal edges, such as buildings or boxes, over the camera background image; it solves focal length, location and rotation [2] 📄.
- Photo-Match Camera: assumes an upright flat facade and a level camera with no tilt or roll; focal length comes from a known width and the camera distance [3] 📄.
- Solvers need sensor size as well as focal length [4] 📄. FOV depends only on the ratio of focal length to sensor width. A focal length without its sensor width, or a 35 mm-equivalent value typed into a non-36 mm sensor, gives the wrong FOV 🧠.
- A forum user reports that the free viewport needs about 2× the camera lens value to show the same view, and a maintainer disputed that this is a bug [4] ↔️. Likely resolution 🧠: as I recall Blender's source, the non-camera perspective viewport applies a fixed zoom factor of 2 (`CAMERA_PARAM_ZOOM_INIT_PERSP`). A 50 mm viewport lens then shows roughly the FOV of a 25 mm camera lens. The effect is real and intended, so both sides are right. Never read lens values off the free viewport.

**Lighting**
- Direction comes first. One tutorial rotates the HDRI to agree with the backplate; another rotates the environment light until the light direction on the object matches the reference [6][7] ✅. Neither measures accuracy.
- Then the map is edited locally: light from under the tires is reduced and the headlight reflection is brightened [6] 📄.
- Poly Light Match (paid) builds an image-based-lighting rig from a reference photo. It has a portrait preset and intensity, distance, height and rotation controls [5] 📄. Its accuracy is undocumented.
- Lambertian irradiance from distant light is well approximated by order-2 spherical harmonics: 9 coefficients per channel, holding roughly 98–99 % of the reflectance kernel's energy (Ramamoorthi & Hanrahan 2001; Basri & Jacobs 2003) 🧠. So diffuse shading cannot tell an HDRI from a blurred copy of it. Sharp-light information lives only in cast shadows (nose, brow, chin, ear), shadow-edge softness, specular highlights and catchlights 🧠.
- The cornea acts as a convex mirror with an anterior radius of about 7.5–8 mm. Catchlight position gives the light direction, and its shape and size give the source shape and angular size. Two eyes give two estimates (Nishino & Nayar, "Eyes for Relighting", 2004) 🧠.
- The classic portrait patterns (butterfly, loop, Rembrandt, split) are named by the geometry of the nose shadow. Each corresponds to a band of key azimuth and elevation (Table D), which makes them the fastest way to set the key by eye 🧠.
- Shadow softness depends on the source's angular size as seen from the face. Penumbra width ≈ occluder-to-receiver distance × angular diameter. In Blender this is the Sun light's Angle, or an area light's Size at a given distance 🧠.
- On-set capture uses a chrome ball (environment and direction), an 18 % grey ball (diffuse response) and a colour chart, with bracketed exposures merged to HDR (Debevec & Malik 1997; Debevec 1998) 🧠. For existing photos without probes, learned estimators infer the light: SfSNet 2018, Sun et al. 2019, LeGendre et al. 2020, DiffusionLight 2024. Their accuracy on arbitrary portraits is unestablished, and this field moves fast 🧠.

**Comparison**
- The Mix node's Factor blends regardless of alpha; Alpha Over respects foreground alpha [8] 📄.
- Blender composites in linear light, while After Effects blends in display space by default, so Difference results differ between them [10] 📄. AE limits blends to layer alpha and Blender does not, so black outside the render participates in Blender [10] 📄.
- A shader sees only its own (foreground) result, so Overlay- or Difference-style comparison cannot be built in a material [9] 📄.
- Since Blender 4.0 the default view transform is AgX, which replaced Filmic. Both apply a tone curve, so for numeric comparison set View Transform = Standard, Look = None, Exposure 0 and Gamma 1, and tag the photo as sRGB so it is linearised 🧠. Camera JPEGs are themselves tone-mapped, so linear-space residuals against them are approximate. Use RAW decoded to linear when possible 🧠.
- Denoising and the pixel filter (Cycles default: Blackman-Harris, about 1.5 px) soften silhouettes, and the softened edges show up as rim lines in difference maps 🧠.
- Viewing distance changes facial proportions. A selfie at about 30 cm makes the nose look roughly 30 % wider relative to the face than at about 1.5 m (Ward et al. 2018) 🧠. A likeness check is therefore valid only through the matched camera.
- Viewing a face upside down hides distortions of individual features (the Thatcher illusion; Thompson 1980). Use inversion for silhouette and proportion checks, not for checking eyes or mouth 🧠.

## Numbers & reference tables

**Table A — Still-image camera matchers (from their own pages)**

| Tool | Input | Solves | Hard assumption | Portrait fit | Badge |
|---|---|---|---|---|---|
| fSpy | Vanishing points | FOV, orientation | ≥2 VPs for focal; 1 VP → user supplies focal | Poor without architecture | 📄 [1] |
| Simple Camera Match | X/Y/Z lines on camera background image | Focal, location, rotation | Orthogonal straight edges | Poor for face crops | 📄 [2] |
| Photo-Match Camera | Known width + distance | Focal, placement | Upright facade, level camera | Not applicable | 📄 [3] |
| Poly Light Match | Reference photo + preset | IBL rig | Undocumented | Untested | 📄 [5] |

**Table B — Compositor operations for render-vs-photo checks**

| Operation | Alpha behaviour | Use | Badge |
|---|---|---|---|
| Alpha Over (render over photo) | Respects foreground alpha | Clean overlay | 📄 [8] |
| Mix, Factor 0–1 | Ignores alpha | Opacity "ghost" | 📄 [8] |
| Mix › Difference | Not alpha-limited; must be multiplied by render alpha × face mask | Error map | 📄 [10] |
| Blend inside a material | No background available | Impossible | 📄 [9] |
| Split node (renamed from "Split Viewer" in 4.x, as recalled) | n/a | Wipe A/B | 🧠 |
| RGB to BW → Map Range (0–0.1 → 0–1) → Color Ramp | n/a | Luminance-only heat map | 🧠 |

**Table C — Pinhole ↔ Blender relations (derived; engine `face3d/geometry/camera.py`)**

| Quantity | Relation | Badge |
|---|---|---|
| Pixel focal | f_px = f_mm · W_px / sensor_w_mm | 🧠 |
| Horizontal FOV | 2·atan(W_px / 2f_px) | 🧠 |
| Blender lens (Sensor Fit = Horizontal) | lens = f_px · sensor_w / W_px | 🧠 |
| Lens shift | shift = offset_px / D, where D = W for Horizontal fit, H for Vertical, max(W,H) for Auto (Blender source, as recalled) | ↔️ |

The engine divides by max(W,H) while forcing Horizontal fit. That is correct for landscape photos, but for portrait-orientation photos it would be off by a factor of H/W (1.33 at 3:4). Verify with a round-trip render before trusting it.

**Table D — Portrait key-light patterns (typical bands; sources vary)** 🧠

| Pattern | Key azimuth from camera axis | Key elevation | Readable cue |
|---|---|---|---|
| Butterfly / Paramount | 0–10° | 30–50° | Symmetric shadow under nose, shadow under chin |
| Loop | 25–45° | 25–40° | Small nose-shadow loop toward mouth corner, not touching the cheek shadow |
| Rembrandt | 45–60° | 35–50° | Nose shadow merges with the cheek shadow; lit triangle under the far eye |
| Split | 80–100° | 0–20° | Face halved along the nose line |
| Rim / kicker | 110–160° | 0–40° | Bright edge on the jaw or ear, no frontal key |

**Table E — Lighting-ratio conventions** ↔️ (the two definitions disagree)

| Label | Def. A: (key+fill):fill, lit/shadow difference | Def. B: key:fill, lit/shadow difference |
|---|---|---|
| 2:1 | 1.00 stop | 1.58 stops |
| 3:1 | 1.58 | 2.00 |
| 4:1 | 2.00 | 2.32 |
| 8:1 | 3.00 | 3.17 |

To measure the ratio, sample linear luminance on lit-cheek and shadow-cheek patches that face the camera similarly; stops = log2(lit/shadow). Commercial portraits typically fall around 2:1–4:1 (Def. A) 🧠.

**Table F — Objective comparison metrics** 🧠

| Metric | Measures | Lighting-sensitive? | Reference scale |
|---|---|---|---|
| Landmark NME (÷ outer inter-ocular distance) | 2D geometry | No | Detector noise floor ≈ 3–4 % IOD on 300-W-style sets (convention-dependent ↔️) |
| Contour distance / silhouette IoU (unoccluded jaw and cheek) | Outline | No | Pixel-level; IoU is saturated by large areas, so prefer contour distance |
| Masked linear MAE per region | Shading + albedo | Yes | Only after geometry passes |
| SSIM (Wang et al. 2004) | Local structure | Partly | 0–1, no universal threshold |
| LPIPS (Zhang et al. 2018) / ꟻLIP (Andersson et al. 2020) | Perceptual difference | Yes | ꟻLIP is designed for flip-comparison |
| CIEDE2000 ΔE00 | Colour | Yes | ≈1 is about a just-noticeable difference; 2–3 noticeable at a glance |
| ArcFace cosine | Identity | Yes (domain gap) | Normalise by a photo-vs-photo baseline of the same person; see identity-embeddings note |

**Table G — Typical portrait cameras and perspective strength (Δ ≈ 0.12 m nose-tip-to-ear depth assumed; derived 1+Δ/z)** 🧠

| Scenario | f (35 mm-eq.) | Distance z | Nose-tip : ear-plane scale |
|---|---|---|---|
| Phone selfie, arm's length | 22–30 mm | 0.25–0.6 m | 1.20–1.48 |
| Phone main camera, head and shoulders | 23–28 mm | 0.5–1.0 m | 1.12–1.24 |
| Phone tele / "portrait mode" | 48–120 mm | 1–2.5 m | 1.05–1.12 |
| Portrait lens | 85–135 mm | 1.5–3 m | 1.04–1.08 |
| Long tele | ≥200 mm | ≥4 m | ≤1.03 |

## Applying this to photo→3D face sculpting in Blender

1. **Camera before sculpt.** Solve focal length and pose from landmarks (`face3d/solve/pnp.py`); see `reference-camera-setup.md`. Set the render resolution to the photo's exact pixels at 100 %, Sensor Fit = Horizontal, sensor width, lens and shift together. Show the photo as a camera background image and judge alignment only in camera view, never with the free-viewport lens [4]. Use vanishing-point tools only when real orthogonal edges are visible, and treat their focal length as a prior [1][2]. Undistort wide-angle selfies; do not try to distort the render.
2. **Shape check under neutral light.** Use a mid-grey matte material (linear albedo about 0.18–0.4), Film → Transparent on, Cycles, with denoising off or held fixed. Check the silhouette, jaw line, ear position, hairline and eye/mouth corners first. A MatCap in Solid mode is good for reading form, but it lights in view space and cannot match a photo.
3. **Read the photo's light.** Find the nose-shadow pattern (Table D) for key azimuth and elevation. Read the catchlight clock position and shape for direction and source shape. Use the penumbra width for size: sun Angle, or area Size at distance. Measure lit/shadow cheek stops for the key:fill ratio (Table E). Read the rim highlights for any back light.
4. **Build the rig.** Either rotate an HDRI (Environment Texture → Mapping Z rotation) until the shadow and terminator directions match, then rebalance locally [6][7]. Or use one area key, the world as fill, and an optional rim. Match the colour temperature with a Blackbody input after white-balancing the photo on a known neutral (a grey card or white clothing). Sclera and teeth are tinted, so do not balance on them. Light linking (Cycles 4.0+) keeps a rim light off the shoulders 🧠. If the photo has shallow depth of field, enable camera DOF at its f-stop so the ears and hair blur alike.
5. **Compositor graph** (Table B). Load the photo in an Image node set to the sRGB colour space and scale it to the render size. Build Alpha Over for the overlay [8], Mix with an exposed Factor for the ghost [8], and Difference → BW × render alpha × face mask → heat map for the error map [10], plus a Split wipe. Keep the view transform at Standard while comparing. Never compare against numbers from AE or Photoshop [10].
6. **Human protocol.** View side by side at the same size and eye line, then blink between the two at 1–4 Hz, then mirror both horizontally, then compare in greyscale, then blur or squint. Check at least front, ¾ and profile; a single view can be matched by a wrong shape paired with a wrong focal length.

**What goes wrong:** "fixing" geometry because of a lighting-driven difference; one-pixel misregistration showing up as bright outlines; contour landmarks treated as fixed points when they slide along the jaw; AgX or Filmic left on; a JPEG treated as linear; a portrait-orientation photo with a lens-shift mismatch (Table C); EXIF focal length used after a crop; and the free-viewport lens mistaken for the camera lens [4].

## Algorithmic implications

- **Camera priors.** Fit log-focal with σ ≈ 0.05–0.1 when EXIF focal length and sensor are known and the image is uncropped, and keep the engine's 0.35 (with 24–200 mm hypotheses) when it is a guess. These are engineering values, not research-derived. Fix the principal point at the image centre unless crop data exists. Add a metric-scale prior from the visible iris diameter, 11.7 ± 0.5 mm, as stated in Google's MediaPipe Iris material (recalled, verify), to break the focal/depth ambiguity.
- **Export contract.** Export lens, sensor_width, sensor_fit, shift (divided by the sensor-fit dimension), resolution and matrix_world. Then run a round-trip test that projects solved landmarks through a Blender render and asserts sub-pixel agreement; this catches the shift issue in Table C.
- **Lighting stage 1 (SH9).** Fit 27 coefficients (9 per RGB channel) by linear least squares, E(n) = Σ Â_l L_lm Y_lm(n), with Â₀ = π, Â₁ = 2π/3, Â₂ = π/4, on mask pixels with constant per-channel albedo. Use Huber weights (δ ≈ 0.05 linear). Exclude eyes, brows, lips, nostrils, hair and beard, the brightest 2–5 % of pixels (specular), and grazing normals (n·v < 0.3). Ridge-regularise band 2. A profile view sees only half the normal sphere, so add a weak light-from-above prior: elevation ~N(30°, 25°), azimuth ~N(0°, 60°).
- **Stage 2 (hard light).** Take the key direction from the band-1 vector (L₁,₁, L₁,₋₁, L₁,₀) → (x, y, z), and the ambient from L₀₀. Refine it by maximising IoU between the rendered and segmented nose/brow cast-shadow masks, and take the source angular size from the penumbra. Map to Blender by calibrating with renders of a grey sphere (render, measure, rescale). Avoid closed-form watt conversions, which drift across engines and versions.
- **Gated verification, in order.** (G1) Landmark NME, using point-to-curve distance for jaw and contour points. (G2) Contour distance on unoccluded jaw and cheek. (G3) Photometric MAE, SSIM, LPIPS or ꟻLIP per region, reported only once G1 and G2 pass. (G4) Identity cosine normalised by the photo-vs-photo baseline. Starting gates, to be calibrated: NME ≤ 2–3 % IOD with landmark σ ≈ 1.5–3 % IOD; contour mean ≤ 1 % of face height. Never auto-accept on G3 or G4 alone.
- **Multi-view.** Require at least 2 views at least 30° apart in yaw before reporting depth-dependent likeness (nose projection, ear position).
- **Reproducibility record** stored with every comparison: Blender version, engine, samples, denoiser, filter width, view transform, look, exposure, gamma, photo colour space, camera parameters, light parameters and seed.
- **Add-on graph builder.** Generate the Table B graph from Python behind a version guard. As I recall, Blender 5.0 moved compositing to node-group data-blocks (`scene.compositing_node_group` instead of `scene.node_tree`) and replaced the Composite node with Group Output. Verify this before coding [13].

## Disagreements, myths & open questions

- **Viewport ≈ 2× lens:** reported and disputed [4] ↔️. Most likely a deliberate zoom factor, not a bug 🧠.
- **Lighting-ratio label:** Def. A versus Def. B differ by up to about 0.6 stop at 2:1 (Table E) ↔️. Always store stops, not labels.
- **"Same blend mode, same result everywhere":** false. Linear versus display space and alpha limiting both differ between apps [10].
- **"Vanishing-point matchers work on any photo":** they need orthogonal edges [2], at least 2 VPs for focal length [1], or a level camera facing a facade [3].
- **"Overlay or Difference in a shader":** impossible [9].
- **"The exact HDRI can be recovered from a portrait":** diffuse shading constrains only about 9 SH terms per channel 🧠. Beyond that the choice is underdetermined, and any HDRI with the right low-frequency content and shadow direction is equally valid.
- **"Difference map = shape error":** lighting, albedo, depth of field and the tone curve all show up in it.
- **"A high identity score proves likeness":** the render-versus-photo domain gap and per-model thresholds make it a relative measure only ↔️ (see the identity-embeddings note).
- **Engine shift units versus Blender** (Table C) ↔️: pending a round-trip test.
- **Refuted:** none. No harvested claim was contradicted. Except for the two-source orientation-first method, everything sourced here is still single-source.
- **Open:** calibrated thresholds for NME, contour and photometric gates on real consented portraits; how accurate learned portrait light estimators are when converted to a Blender rig; current Blender 5.x compositor node and Python identifiers; the selfie-distortion magnitude and the anthropometric Δ (from the anthropometry notes); whether jointly fitting SH lighting and shape beats manual HDRI rotation for sculptors.

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
[12] How to Setup HDRI Lighting in Blender 2.93 (BlenderNation) — https://www.blendernation.com/2021/06/30/how-to-setup-hdri-lighting-in-blender-2-93/ — news (title/snippet only; not cited in text) — 2021
[13] Blender 5.0 Manual: Cameras — https://docs.blender.org/manual/en/5.0/render/cameras.html — official docs (content not retrieved) — n.d.

**Further reading (by name, not yet linked)**
- Debevec & Malik, "Recovering High Dynamic Range Radiance Maps from Photographs", SIGGRAPH 1997
- Debevec, "Rendering Synthetic Objects into Real Scenes", SIGGRAPH 1998
- Ramamoorthi & Hanrahan, "An Efficient Representation for Irradiance Environment Maps", SIGGRAPH 2001
- Basri & Jacobs, "Lambertian Reflectance and Linear Subspaces", IEEE TPAMI 2003
- Nishino & Nayar, "Eyes for Relighting", SIGGRAPH 2004
- Blanz & Vetter, "A Morphable Model for the Synthesis of 3D Faces", SIGGRAPH 1999
- Sengupta et al., "SfSNet", CVPR 2018; Sun et al., "Single Image Portrait Relighting", SIGGRAPH 2019; LeGendre et al., "Learning Illumination from Diverse Portraits", SIGGRAPH Asia 2020; Phongthawee et al., "DiffusionLight", CVPR 2024
- Wang, Bovik, Sheikh & Simoncelli, "Image Quality Assessment: From Error Visibility to Structural Similarity", IEEE TIP 2004
- Zhang et al., "The Unreasonable Effectiveness of Deep Features as a Perceptual Metric" (LPIPS), CVPR 2018
- Andersson et al., "FLIP: A Difference Evaluator for Alternating Images", HPG 2020
- Sharma, Wu & Dalal, CIEDE2000 implementation notes, Color Research & Application 2005
- Deng et al., "ArcFace", CVPR 2019
- Fried, Shechtman, Goldman & Finkelstein, "Perspective-aware Manipulation of Portrait Photos", SIGGRAPH 2016
- Ward et al., "Nasal Distortion in Short-Distance Photographs: The Selfie Effect", JAMA Facial Plastic Surgery 2018
- Thompson, "Margaret Thatcher: A New Illusion", Perception 1980
- Hunter, Biver & Fuqua, *Light: Science and Magic* (portrait lighting patterns)
- Hartley & Zisserman, *Multiple View Geometry in Computer Vision*, 2nd ed., 2004
- Blender source: `BKE_camera_params_compute_viewplane`, `CAMERA_PARAM_ZOOM_INIT_PERSP` (shift units, viewport zoom)
