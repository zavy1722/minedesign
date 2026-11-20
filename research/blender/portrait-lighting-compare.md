# Matching photo lighting and verifying likeness renders

> Checking a likeness render against a reference photo breaks into three separate jobs. First recover the camera (focal length, sensor/aspect, pose). Then approximate the light: get the direction right before the balance. Finally compare render and photo in a controlled compositing setup. Still-photo camera matching in Blender relies on third-party vanishing-point tools (fSpy, Simple Camera Match) and facade-oriented add-ons. Those tools need orthogonal straight edges or a level, upright camera, which head-and-shoulders portraits rarely provide. That makes a landmark-based perspective-n-point solve the better fit for faces. Two independent lighting tutorials, one for Blender and one for Maya, both start by rotating the environment until the light direction on the subject matches the reference, and only then refine local intensity. For comparison overlays, Blender's compositor blends in linear colour and its blend operations ignore layer alpha. Difference and overlay results therefore differ from After Effects and have to be masked. **Verification status of this pass:** the web-search budget ran out before any independent cross-check could run, so almost every claim below is single-source practitioner or vendor material. No numeric value could be sourced.

## Key facts

- Still-image camera matching in Blender is done with third-party tools. The harvest found three: **fSpy**, a standalone app announced as the successor to the BLAM add-on; **Simple Camera Match**, a Blender extension; and **Photo-Match Camera**, a paid archviz add-on. An 80.lv article covers a "still image camera matching app" for Blender workflows (title only). The claim that Blender has no built-in still-photo matcher is the harvester's inference and was not confirmed against the manual. [1][2][3][11] ⚠️ single-source
- fSpy's developer describes still-image camera matching as computing field of view and camera orientation from an image, given vanishing points. With only one discernible vanishing point, the user has to supply the focal length or find it by trial and error. [1] ⚠️ single-source
- In Simple Camera Match, the user draws X, Y and Z vanishing lines over a background image in the camera view, and the add-on solves focal length, location and rotation. The guidance is to trace orthogonal references such as building edges or box edges, one axis per line set. [2] ⚠️ single-source
- Photo-Match Camera assumes a flat upright facade. The photo plane stands upright, the camera is placed level with no tilt or roll, and focal length is estimated from a known real-world width and the camera distance. [3] ⚠️ single-source
- Camera-matching solvers need **sensor size as well as focal length**. A community thread questions whether Blender's focal-length and sensor-size values are accurate. [4] ⚠️ single-source
- One user reports that the Blender **viewport** lens has to be set to roughly **2×** the camera focal length to match the camera view. Per the thread, a maintainer disputed that this is a bug. The bug tracker was not checked. [4] ↔️ contested
- **Lighting match: orientation first.** The Lightmap Blender tutorial first rotates the HDRI to agree with the backplate photo. A Maya lighting course separately rotates the environment light until the light direction on the object matches the reference. Both are practitioner tutorials, and neither measures accuracy. [6][7] ✅ verified (two independent sources agree on the method)
- **Then refine the map locally.** After fixing orientation, the Lightmap tutorial edits the HDRI itself: it reduces light coming from under the tires and brightens the headlight reflection. [6] ⚠️ single-source
- Poly Light Match is a paid Blender add-on that builds an image-based lighting rig from a reference photo. It has movie, portrait, landscape and product presets, plus intensity, distance, height and rotation controls. [5] ⚠️ single-source (vendor docs)
- In the Blender compositor, the **Mix** node's Factor sets the blend amount regardless of alpha, while **Alpha Over** respects the foreground alpha. [8] ⚠️ single-source
- Blender compositing works in **linear** colour, while After Effects blends in display space by default, so the same blend mode (e.g. Difference) gives different numbers in the two apps. [10] ⚠️ single-source
- After Effects limits blend modes to a layer's alpha by default. Blender blend operations do not, so black outside a render's alpha takes part in the blend. [10] ⚠️ single-source
- Blend modes are per-pixel formulas that combine foreground and background pixels. A shader only sees its own (foreground) result, so background-dependent modes such as Overlay cannot be rebuilt inside a material. Photo comparison belongs in the compositor, not in a shader. [9] ⚠️ single-source

## Numbers & reference tables

No sourced numeric values were obtained in this pass: no focal-length error, no lighting-match accuracy, no colour-difference magnitudes, no likeness thresholds. The tables below are qualitative and sourced, apart from Table C, which is plain pinhole geometry derived here and labelled as such. No data JSON was written because there were no sourced values to put in it.

**Table A — Still-image camera-matching tools (as described by their own pages/threads)**

| Tool | Form | User input | Solves | Hard assumptions | Fit for portrait photos (inference) | Source |
|---|---|---|---|---|---|---|
| fSpy | Standalone app (successor to BLAM) | Vanishing points | FOV, camera orientation | Needs ≥2 VPs to recover focal; 1 VP → focal supplied by user | Poor unless the background has architecture | [1] |
| Simple Camera Match | Blender extension | X/Y/Z vanishing lines drawn on camera background image | Focal length, location, rotation | Orthogonal straight edges (buildings, boxes) | Poor for tight face crops | [2] |
| Photo-Match Camera | Paid add-on (archviz) | Known real-world width + camera distance | Focal length, placement | Upright flat facade; level camera, no tilt/roll | Not applicable to heads | [3] |
| Poly Light Match | Paid add-on (lighting) | Reference photo + preset (incl. portrait) | IBL rig with intensity/distance/height/rotation controls | Not documented in harvest | Unknown; untested | [5] |

**Table B — Compositor operations for render-vs-photo checks**

| Operation | Alpha behaviour | Colour space | Use in likeness checks | Source |
|---|---|---|---|---|
| Alpha Over (render over photo) | Respects foreground alpha | Linear (Blender compositor) | Clean overlay of head on photo | [8][10] |
| Mix, Factor 0–1 | Ignores alpha; Factor alone sets blend | Linear | Opacity "ghost" overlay or wipe | [8][10] |
| Mix, Difference mode | Not limited to alpha; black outside alpha participates | Linear (differs from AE display-space result) | Error heat-map; must be masked by render alpha | [10] |
| Overlay-type modes in a material shader | n/a | n/a | Not possible: a shader sees no background | [9] |

**Table C — Pinhole relations used for camera export (derived, not externally sourced; implemented in `face3d/geometry/camera.py`)**

| Quantity | Relation | Units |
|---|---|---|
| Pixel focal from sensor | f_px = f_mm · W_px / sensor_width_mm | px |
| Horizontal FOV | FOV_x = 2·atan(W_px / (2·f_px)) | degrees |
| Blender lens for a given sensor width (sensor_fit = HORIZONTAL) | lens_mm = f_px · sensor_width_mm / W_px | mm |
| Principal-point offset → Blender shift | shift_x = (W/2 − c_x)/max(W,H); shift_y = (c_y − H/2)/max(W,H) | fraction of larger image side |

The lens value only reproduces the photo when sensor width, sensor fit and render resolution are set together. That follows from [4]'s point that solvers need sensor size as well as focal length.

## Applying this to photo→3D face sculpting in Blender

**1. Solve the camera before touching the sculpt.** A wrong focal length or camera distance changes apparent facial proportions in ways no amount of sculpting can reconcile across several photos.
- Treat EXIF focal length (35 mm-equivalent, when present) as a **prior, not truth**. The engine's `focal_px_from_35mm` converts it on the image diagonal.
- Use vanishing-point tools [1][2] only when the photo contains real orthogonal straight edges, such as a door frame or wall corner. Even then they recover the *camera*, not the head pose. A single vanishing point leaves focal length unsolved [1]. For plain-background portraits, use landmark-based PnP with focal estimation (`face3d/solve/pnp.py`).
- Set the render resolution to the photo's exact pixel dimensions, and set lens, sensor width, sensor fit and shift together (`to_blender_camera`). Judge alignment in **camera view**, never with the free-viewport lens, which is disputed and may not equal the camera lens [4].
- Show the photo as the camera's background image, the same mechanism Simple Camera Match uses [2], and use it to check the silhouette, jaw line, ear position and hairline before working on detail.

**2. Match the light: direction first, then balance.**
- If an HDRI is used, rotate it (or the key light) until the light *direction* on the head matches the photo, before changing any intensity [6][7]. On a face, the most readable direction cues are the nose cast shadow, the cheek and jaw terminator line and the eye catchlights. This cue list is practitioner reasoning that was not sourced here.
- Then refine locally: suppress unwanted fill and boost the dominant specular source, as Lightmap does by editing the HDRI map [6]. A portrait preset from a tool such as Poly Light Match can be a starting rig [5], but its accuracy is undocumented.
- For **shape** verification, render with a neutral material so skin texture and albedo errors do not hide geometry errors. Use a textured render only for final appearance checks. This too is reasoning, not a sourced claim.

**3. Compare in the compositor, with masks.**
- Render with an alpha channel, then Alpha Over the render onto the photo for a clean overlay [8].
- Use a Mix node with an animatable Factor for the ghost or opacity view. Mix ignores alpha [8].
- Use Mix in Difference mode for an error map, and multiply it by the render's alpha (and ideally a face mask). Blender blend operations are not alpha-limited, so the photo's background would otherwise flood the map [10].
- Expect different numbers from the same comparison done in After Effects or Photoshop, because Blender blends in linear space and AE in display space by default [10]. Pick one space and keep it.
- Do not try to build the overlay or difference inside a material [9].

**What goes wrong**
- Difference maps light up from lighting mismatch as well as from shape error, which leads to "fixing" geometry that was correct. Check shape with silhouettes and landmarks first, and read the difference map only after the lighting direction is matched.
- Sub-pixel misregistration produces bright edge outlines that are not shape errors.
- Viewport-lens readings are mistaken for camera lens values [4].
- Focal length is assumed from one vanishing point [1].
- Results are compared across apps with different blend spaces [10].

## Algorithmic implications

- **Camera model.** Use full perspective with focal length as a free parameter under a soft prior (log-normal from EXIF when present) and multi-hypothesis initialisation. The engine already does this. Its defaults (35 mm-equivalent hypotheses 24–200 mm, prior log-σ 0.35) are engineering choices, not research-derived, and need validating on real portraits. Vanishing-point solving should be an optional input path for photos with architecture [1][2], not the default.
- **Export contract.** Always export lens, sensor_width, sensor_fit, shift_x/shift_y and resolution together, never lens alone, because sensor size is part of the solution [4]. Generate an automatic check that renders the solved camera's landmark projections over the photo.
- **Two-stage verification metric.** Keep geometry and photometry separate:
  - (a) Geometric: landmark reprojection RMSE in pixels (`PnPResult.rmse_px`), plus silhouette/contour agreement between the render alpha and a segmented face mask. Neither depends on lighting.
  - (b) Photometric: a linear-space difference restricted to render alpha ∩ face mask and reported per region (forehead, nose, cheeks, jaw). Run it only after the lighting direction is fixed.
  Thresholds are not sourced and must be calibrated (see Open questions).
- **Lighting parameterisation.** Optimise environment or key-light *rotation* (yaw/pitch) first, and intensity and local balance second, mirroring the two-stage practice in [6][7]. A low-order analytic lighting model would be the natural fitting-side representation. That is unsourced in this pass, so it is listed as an open question rather than encoded as fact.
- **Colour management.** Convert the photo to the compositor's linear space before differencing, and record the source colour space and view transform with every comparison, because the blend space changes results [10].
- **Compositor graph generation (add-on).** The add-on can build the comparison graph from Python: Alpha Over for overlay, Mix (Factor) for ghosting and Mix (Difference) × alpha for the error map. The Factor should be exposed as a UI slider [8][10]. Node identifiers and API changes in Blender 5.x were **not verified**. Check them against the 5.0 manual [13] before coding.
- **Never auto-accept likeness** from a photometric score alone: lighting confounds it. Gate acceptance on geometric metrics, and show the overlay and difference views to a human.

## Disagreements, myths & refuted claims

- **"Viewport lens ≈ 2× camera lens."** One user reports it, and a maintainer in the same thread disputed it as a bug [4]. Unresolved; the primary bug tracker was not checked. ↔️
- **"The same blend mode gives the same result everywhere."** False per [10]: linear vs display blending and alpha limiting differ between Blender and After Effects. The explanation is single-source.
- **"Vanishing-point matchers work for any reference photo."** This is a myth by implication. The tools' own requirements are orthogonal edges [2], at least two vanishing points to recover focal length [1], or a level camera facing an upright facade [3]. Tight face crops meet none of these.
- **"An Overlay or Difference comparison can be done in a shader."** A shader has no background pixels, so it cannot [9].
- **Refuted:** none. Without independent searches, no harvested claim could be shown false. None of the claims should be treated as confirmed either.

## Open questions

- **Search budget exhausted** in both the harvest (5 of 8 queries never ran) and this verification pass (0 independent searches completed). Every ⚠️ claim needs a follow-up cross-check, with priority on [4] (viewport vs camera lens) and [10] (linear blending, alpha behaviour).
- Blender 5.0 manual content: camera sensor fit, lens, shift and background-image (opacity/depth) settings [13], and the current compositor Mix/Alpha Over node names and Python identifiers. These were not retrieved.
- Objective likeness metrics with published numbers: landmark error normalisation, silhouette IoU, perceptual or identity-embedding similarity, and thresholds for "same person". None were sourced.
- How strongly does camera distance or focal length distort facial proportions (e.g. selfie distance vs portrait-lens distance)? Clinical literature on this exists, but none was retrieved, so no figures are given.
- Light-probe practice (grey or chrome ball, on-set HDRI) and how accurately a portrait key/fill ratio can be recovered from a single photo: no sources.
- Is a low-order lighting model, fitted jointly with shape, accurate enough to replace manual HDRI rotation? Unsourced.
- Whether Blender's motion-tracking camera solver could help with multi-photo stills of a non-rigid face: not investigated.

## Sources

[1] Retiring BLAM and announcing fSpy – a stand alone camera matching app (Blender Artists) — https://blenderartists.org/t/retiring-blam-and-announcing-fspy-a-stand-alone-camera-matching-app — forum (developer announcement) — n.d.
[2] Simple Camera Match (Blender Extensions listing) — https://extensions.blender.org/add-ons/simple-camera-match/ — extension listing — n.d.
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
