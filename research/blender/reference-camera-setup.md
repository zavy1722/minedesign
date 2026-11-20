# Reference images and camera matching in Blender

> Blender has two ways to show reference photos. Camera background images are drawn only when you look through a camera and are framed by that camera's sensor and the render aspect ratio. Image empties are scene objects that show in perspective and orthographic views, and they replaced the pre-2.8 per-viewport background images [1][2][4]. To match a photo you have to rebuild the camera that took it: focal length relative to sensor width (that is, field of view), principal point, pose, and ideally lens distortion. fSpy and its Blender importer do this from vanishing lines, which suits architecture but usually not a bare portrait [10][13][18]. For faces, solve the camera from facial landmarks with focal length as an unknown, and compare the photo and the mesh through that perspective camera. Do not trace near-field photos in orthographic front and side views. **Verification status: none of these claims was checked against an independent source in this run** (see the banner below). Treat this note as a provisional draft.

**Run banner (honesty).** The harvester got 4 searches through before its budget ran out. In this verification pass the shared per-turn web-search budget (200 calls) was already used up, so every search was refused. One direct fetch of docs.blender.org failed at DNS. So every fact below rests on the harvester's search snippets, and the best status any claim can have is ⚠️ single-source. No sourced number was found for portrait focal length, camera distance, or perspective distortion of facial proportions. Re-run this topic with search budget before citing it as settled.

## Key facts

- Blender's current manual describes the camera's sensor **Size** (Width/Height) as an alternative to focal length for setting field of view. It is meant for matching a physical camera and lens, for example in motion tracking [1] ⚠️
- **Sensor Fit:** *Auto* uses the larger render-resolution dimension to define a square sensor. *Horizontal* sets the sensor width by hand and derives the height from the output aspect ratio [1] ⚠️
- Camera background image framing: *Fit* scales the image to fit inside the camera view without changing its aspect ratio. *Crop* scales it to fill the camera view and cuts off part of the image [1] ⚠️
- In Python, `Camera.sensor_width` and `Camera.sensor_height` are in **millimetres**. The Camera Info geometry node outputs sensor size as a 2D vector in mm. For real footage, take the sensor width from the camera's spec sheet [1] ⚠️
- The 2.79 manual documents a legacy View-panel background-image workflow [2]. Developer proposal #52668 argued for replacing those with **image empties** in 2.8x and moving camera-view drawing into the camera data-block [4]. Tracker discussion describes image empties as drawn in perspective and orthographic views, while camera background images remain the way to draw in camera view with framing options [4][5]. Exact shipped behaviour per version was not confirmed ⚠️
- Add an image empty with *Shift+A → Empty → Image*; its settings are in Object Data Properties. A third-party guide says the Image Empty and the "Image Object" differ only in the underlying data-blocks [9] ⚠️
- Tracker issue #120929 reports camera background images or clips not appearing in animation renders [6]. Two other reports are T98875 ("Image not found" error when adding a camera background image) [7] and T44096 (background image size/offset has no effect in camera view) [8]. Fixed or open status was not captured. Reference overlays are a viewport aid, not render content ⚠️
- **fSpy** is an open-source, cross-platform still-image camera-matching app. It computes approximate focal length, orientation and position from control points and vanishing lines the user places, and the usual route is to export the result to Blender [10][11] ⚠️ (two harvest URLs, neither independently re-checked)
- fSpy is its author's stand-alone successor to the Blender add-on **BLAM** (Per Gantelius's announcement) [12] ⚠️. 80.lv covered fSpy for Blender workflows; only the title was seen [22].
- The **fSpy-Blender importer** reads the principal point, horizontal field of view and image dimensions from the `.fspy` project JSON, and rejects files whose project version is not 1 [13] ⚠️ (from a search summary of `fspy.py`, not from reading the file)
- fSpy-Blender open issue #89 (Sept 2025) asks whether the importer works in Blender 4.5, and #88 reports failed matches with strong vanishing points [14] ⚠️ (titles only). Compatibility with Blender 4.5 and later is **unconfirmed**.
- The **perspective-match** Blender extension says its solver is a port of fSpy's solver, with GPL-3.0 named, and that its Blender camera mapping follows the fSpy importer [17] ⚠️. Whether the licence label refers to fSpy, the extension or both was not confirmed.
- fSpy struggles when an image has no clear vanishing points [18] ⚠️. A vanishing-point workflow uses 1–3 vanishing points, depending on how many sets of parallel lines the image shows [19] ⚠️ (tutorial statement)
- GeoCalib's authors call classical vanishing-point geometry accurate but not robust, which is why they turn to learned single-image calibration [20] ⚠️. Perspective Fields (CVPR 2023) is another learned single-image calibration method; its abstract was not read [21] ⚠️
- fSpy issue #119 asks for known-size reference shapes to help match focal length, and #53 asks for image zoom [15][16]. Both are feature requests, not shipped features ⚠️
- Other camera-matching tools, identified by title only with capabilities unverified: Blender-AI-Camera-Match [23], Perspective Plotter [24], and Blenspy (commercial) [25].

## Numbers & reference tables

**Gap:** no sourced quantitative data was obtained on portrait focal length or distance versus facial proportions. Tables 1–2 are sourced parameter semantics. Tables 3–4 are pinhole-camera derivations, which are arithmetic and not empirical claims about faces.

**Table 1 — Blender camera parameters that matter for photo matching** (source [1], ⚠️ single-source; population: n/a)

| Parameter | Unit / values | Meaning |
|---|---|---|
| `sensor_width`, `sensor_height` | mm | Physical sensor size. Defines FOV together with focal length |
| Camera Info node "sensor size" | 2D vector, mm | Same values, exposed to Geometry Nodes |
| Sensor Fit = Auto | — | Larger render dimension defines a square sensor |
| Sensor Fit = Horizontal | — | Width set by hand; height derived from output aspect |
| Background image Fit | — | Scale to fit inside the camera frame, aspect kept |
| Background image Crop | — | Scale to fill the camera frame, overflow cropped |

**Table 2 — `.fspy` fields consumed by the fSpy-Blender importer** (source [13], ⚠️ search summary only)

| Field | Use |
|---|---|
| project version | Must equal **1**, otherwise the import is rejected |
| principal point | Maps to camera lens shift |
| horizontal field of view | Sets the Blender lens/FOV |
| image width, height | Sets the render resolution and aspect |

**Table 3 — Pinhole relations to encode (derived)**

| Quantity | Formula |
|---|---|
| Horizontal FOV | `FOV_x = 2·atan(S_w / (2·f_mm))` (sensor-width fit) |
| Focal length in pixels | `f_px = f_mm · W_px / S_w` |
| Blender lens from a solved camera | `lens = f_px · S_w / W_px` (with Sensor Fit = Horizontal and resolution = photo pixels) |
| Image scale of a feature at depth z | ∝ `f / z`, so for a given distance the focal length changes framing, not perspective |

**Table 4 — Relative magnification of a near feature against a far feature (derived arithmetic, not a face measurement)**

Two features lie on the viewing axis, Δ apart in depth, and the nearer one is at distance `z` from the camera. Their image-scale ratio is `1 + Δ/z`.

| z / Δ | 2 | 3 | 5 | 10 | 20 | 50 |
|---|---|---|---|---|---|---|
| near:far scale ratio | 1.50 | 1.33 | 1.20 | 1.10 | 1.05 | 1.02 |

Doubling the camera distance roughly halves the excess magnification. To turn this into face-specific numbers, the anthropometric depth Δ (for example nose tip to ear or cheek plane) has to come from a sourced anthropometry note. No such value is asserted here.

## Applying this to photo→3D face sculpting in Blender

1. **Collect per-photo metadata first.** Record the pixel dimensions, the EXIF focal length, the EXIF 35 mm-equivalent focal length, and the camera model. Look up the sensor width on the spec sheet [1]. If the photo was cropped or resized, the EXIF values describe the *original* frame, so record the crop.
2. **One Blender camera per photo.** Set the scene render resolution to the photo's exact pixel size. If the aspect ratios differ, the Fit/Crop framing changes where the photo lands in the camera frame [1], and every later alignment inherits that offset. Set Sensor Fit to *Horizontal*, the sensor width in mm, and the lens in mm [1]. If you only have a 35 mm equivalent, convert through pixel focal length (Table 3) and do not type it straight into a 36 mm-wide sensor. The engine (`face3d/geometry/camera.py`) defines the equivalence on the image diagonal, which matters for 4:3 phone images. That definition is an engine assumption that still needs an external citation.
3. **Attach the photo as a camera background image, not an image empty,** for any view where perspective matters [1][4]. Keep offset at 0, scale at 1 and rotation at 0. An unmatched transform hides a mismatched camera, and T44096 shows offset/scale behaviour in camera view has had bugs [8]. bpy identifiers from the author's working knowledge, not re-checked in this run: `cam.data.show_background_images`, `cam.data.background_images.new()`, `.image`, `.alpha`, `.display_depth` (`'BACK'`/`'FRONT'`), `.frame_method` (`'STRETCH'`/`'FIT'`/`'CROP'`).
4. **Solve the pose and focal length from landmarks, not by eye or with fSpy.** A portrait rarely has the parallel scene lines fSpy needs [18]. Use fSpy only when the photo shows strong architecture, such as a room corner behind the subject. Even then, treat its focal length as a prior.
5. **Principal point.** Assume the image centre for uncropped photos. An off-centre crop moves the principal point, and Blender represents that as lens shift. The engine's `to_blender_camera` encodes shift in units of the larger image dimension, which is an engine convention still to be verified against the API docs.
6. **Overlay compare (practice suggestions, unsourced in this run):** (a) background display depth *Front* at partial opacity puts the photo over the mesh; (b) flicker between Front and Back, or toggle visibility, to catch small offsets; (c) render the head through the matched camera and difference it against the photo in the compositor; (d) compare silhouette and ear position, not only internal features. Internal features can match even with a wrong focal length, because focal length and distance trade off on a shallow object.
7. **Orthographic front/side blueprints.** A photo is a perspective projection. If you trace it in an orthographic view, the depth-dependent magnification of Table 4 gets baked into the mesh: features nearer the lens come out enlarged relative to farther ones. Front and side photos also rarely share distance, camera height, and an exact 90° yaw, so their outlines will not agree. If you must use image empties in ortho views, use only photos taken from far away, align on stable landmarks rather than edges, and expect errors in nose and ear proportions. No sourced measurement of the error size was obtained.
8. **Typical failure modes:** aspect-ratio mismatch; Auto sensor fit on a portrait-orientation photo (the larger dimension becomes the sensor reference [1]); EXIF focal length used after a crop; uncorrected lens distortion; a "front" photo with head yaw or pitch; different expressions across photos; and focal/depth ambiguity producing a head that is too flat or too deep.

## Algorithmic implications

- **Camera model:** use a full-perspective pinhole per photo, with log focal length, principal point (default = image centre, fixed unless crop metadata exists), rotation, translation and optional radial terms (k1, k2), and one head shape shared across views. Use scaled-orthographic only for initialisation, as `face3d/solve/pnp.py` already does. Never use it as the final model for near-field portraits.
- **Focal prior:** use a log-normal prior centred on the EXIF value when one exists, and multi-hypothesis initialisation when it does not. The current engine defaults (σ = 0.35 in log space; 35 mm-equivalent hypotheses 24–200 mm) are **unsourced engineering choices**. Calibrate them on a test set before release.
- **Focal/depth ambiguity:** a face is shallow relative to typical shooting distance, so f and z are weakly separable from one view. Encode an anthropometric scale prior (from the anthropometry notes) and prefer multi-view solves. Expose a **perspective-strength index** `z/Δ` and a confidence score. When `z/Δ` is large, the perspective cue carries little depth information, so the tool should rely more on side views or the statistical shape prior.
- **Blender export contract:** set resolution = photo pixels, Sensor Fit = Horizontal, `lens = f_px·S_w/W_px`, shift from the principal point, and camera background image with frame method irrelevant once aspects match [1]. After export, run a **round-trip check**: project the solved 3D landmarks through the Blender camera and assert sub-pixel agreement with the engine's projection.
- **fSpy interop (optional input):** accept `.fspy` files, check version = 1, and read the principal point, horizontal FOV and image dimensions [13]. Convert them to the engine camera as a *prior*, not ground truth. If you port fSpy's solver, plan for GPL-3.0 obligations [17].
- **Learned calibration fallback:** single-image calibrators such as GeoCalib [20] and Perspective Fields [21] could supply a focal prior when EXIF is missing. Their accuracy on close-up faces is unknown, so weight them weakly.
- **Version robustness:** draw camera-view overlays through camera background images, and non-camera reference views through image empties [4][5]. Never rely on background images appearing in renders [6]. Write regression tests for frame mapping, given the bugs reported in [7][8].
- **QA outputs:** per-landmark reprojection residuals (px), silhouette overlap, estimated distance and focal length with uncertainty. Show these in the add-on next to the overlay.

## Disagreements, myths & refuted claims

- **Where reference images live depends on the Blender version.** In 2.79 they were View-panel background images [2]; from 2.8x the direction was image empties plus camera background images [4]. Older tutorials therefore give conflicting instructions. ↔️ (version-dependent rather than contradictory)
- **fSpy-Blender on current Blender:** an open issue asks whether it works in 4.5 [14]. Treat any claim that it works in 4.x or 5.x as unconfirmed.
- **Excluded claim:** the harvest reported that a "third-party benchmark" found `.fspy` imports reproduce the camera matrix to a maximum difference of 1.4e-7 and that `.fspy` files do not store vanishing points. It was attributed to the `fspy.py` source URL, which does not match its description as a third-party benchmark. Its provenance is unclear, so it is left out of the main text. It is not refuted, just unconfirmed.
- **Myth: orthographic front/side blueprints are accurate references for faces.** By pinhole geometry a near-field photo is not an orthographic projection (Table 4), so tracing it orthographically distorts depth-dependent proportions. No empirical measurement was sourced in this run. The magnitude for real faces is an open question, not a refuted claim.
- **Classical versus learned calibration:** vanishing-point methods are described as accurate but not robust [20], and fSpy fails without clear vanishing points [18]. Learned methods trade that robustness for unknown accuracy on faces [21].
- **Refuted:** none. No independent check was possible, so nothing could be refuted.

## Open questions

1. Measured effect of camera distance and focal length on facial proportions (nose width, ear visibility, face width), with sample sizes. This is the highest priority for a re-run: search clinical facial-photography and multi-distance portrait literature (PMC, arXiv, CVF).
2. Current Blender 4.x/5.x UI and API for camera background images (Stretch option, display depth, opacity) and image empties (depth, side, ortho/perspective visibility). The bpy names above need checking against docs.blender.org/api.
3. Lens-distortion models available in the current Movie Clip Editor ([3] covers only 2.79), and how to apply them to still-photo matching.
4. Whether fSpy-Blender works in Blender 4.5 or 5.x, and the licence of perspective-match versus fSpy [14][17].
5. How accurate GeoCalib and Perspective Fields focal estimates are on close-up face images [20][21].
6. Practitioner overlay and compare workflows on Blender Artists and Polycount. Not researched.
7. Primary citation for diagonal-based 35 mm equivalence and for Blender lens-shift units, both currently engine assumptions.

## Sources

[1] Cameras — Blender 5.3 Manual — https://docs.blender.org/manual/en/latest/render/cameras.html — official-docs — 2026
[2] Background Images — Blender 2.79 Manual (legacy View-panel workflow) — https://docs.blender.org/manual/en/2.79/editors/3dview/properties/background_images.html — official-docs — 2017
[3] Camera Data — Blender 2.79 Manual (movie clip editor) — https://docs.blender.org/manual/en/2.79/editors/movie_clip_editor/tracking/clip/properties/camera_data.html — official-docs — 2017
[4] Proposal: Replace background images with Image Empties in 2.8x (issue #52668) — https://projects.blender.org/blender/blender/issues/52668 — repo — 2019
[5] Blender developer tracker task T51366 (title not captured by harvest) — https://developer.blender.org/T51366 — repo — unknown
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
