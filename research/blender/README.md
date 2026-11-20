# Blender tools, sculpting & Python practice

> Area guide to 21 topic notes on using Blender to turn photos of a consenting person into a likeness-accurate, anatomically correct, sculpt-ready head. Blender is both the artist's workbench and the delivery target for the project's NumPy fitting engine. Status as of **2026-11-20**: Blender **5.3** is the current feature release and **5.2 LTS** is supported until Jul 2028 ([version status](./blender-version-status-2026.md)).

## What this area covers

- **Blender as a platform:** release lines and bundled Python/NumPy, the `bpy` mesh/shape-key/camera API, extension packaging and licensing, and running ML landmark detectors next to Blender.
- **Getting photos in:** rebuilding each photo's camera, importing scans and 3DMM outputs (units, axes, mirroring, vertex order), FaceBuilder and other existing face add-ons.
- **Making the head:** an open-licence template kit, sculpt-mode features in 4.x–5.x, the coarse-to-fine likeness workflow, face topology and retopology, eyes, hair.
- **Making it usable:** shape keys and blendshape standards (ARKit 52, MediaPipe), rigging, projection texturing, skin shading, render-vs-photo verification, bridges to MetaHuman, Character Creator and Daz, and a guided, accessible workflow for non-expert users.

It does **not** cover anatomy norms (`../anatomy/`), reconstruction maths (`../reconstruction/`), consent law (`../ethics/`) or community practice (`../community/`), though the notes link to them.

## How to use this page

- **Artists:** work through the [checklist](#practical-checklist-for-an-artist-working-in-blender). Look numbers up in the [quick-reference tables](#quick-reference-tables), then follow the link to the note before relying on a value.
- **Engineers:** read the [principles](#principles), the [prior and QA tables](#r7--fitting-priors-σ-for-the-engine), the [contradictions](#cross-topic-contradictions-and-how-to-resolve-them) and the compact engine digest in [`../_raw/requirements_blender.md`](../_raw/requirements_blender.md). Machine-readable tables are in `../data/<topic>.json`.
- **Evidence badges** (kept on every item below): ✅ verified by two or more independent sources · 📄 single-sourced · 🧠 expert knowledge not yet source-checked · ↔️ contested. Every note ends with a dated **verification log**; where it corrects the note's text, **the log wins**, and this page already uses the corrected values.
- **Read the 🧠 share before trusting a number.** Across the area the notes carry 53 ✅ / 342 📄 / 1,341 🧠 / 261 ↔️ badged claims, so about two thirds are unchecked expert knowledge. Fifteen of the 21 topics had no web harvest of their own; the least-sourced notes (bpy API, sculpting workflow, retopology, hair, texture painting, template kit, guided workflow) have no ✅ and at most 7 📄 each. Treat their numbers as starting values to calibrate, not facts.

## Principles

Thirty rules that recur across the notes, grouped by stage. Each keeps the badge of its weakest load-bearing claim.

**Scale, cameras and photos**

1. **Work at real scale: 1 Blender unit = 1 m, unit scale 1.0, object transforms applied.** Voxel size, Dyntopo detail, merge distance, Shrinkwrap limits, bake distances and scene-unit brush radii are all in scene or local units; tutorial values made on Blender's 2 m default sphere are about 10× off, and an unapplied object scale of 0.001 multiplies every threshold by 1000. 🧠 — [sculpting workflow](./sculpting-likeness-workflow.md), [import/export](./import-export-scans.md), [sculpt features](./blender-sculpt-features-5x.md)
2. **Perspective is set by camera distance, not focal length.** The nose tip images about 33 % larger relative to the ears at 0.3 m and about 3 % at 3 m, so choose the distance first (≥1.5 m, ideally 2–3 m, phone tele or 85–135 mm), then zoom and crop. 🧠 (arithmetic) — [reference cameras](./reference-camera-setup.md)
3. **Give every photo its own solved perspective camera, lock it, and judge likeness only through it.** Lock the camera transforms and turn off "Lock Camera to View", or the first orbit destroys the match. Never trace near-field photos in orthographic views; ortho blueprints are acceptable only for photos from ≥3 m with yaw and pitch solved near 0. 🧠 — [reference cameras](./reference-camera-setup.md), [sculpting workflow](./sculpting-likeness-workflow.md), [sculpt features](./blender-sculpt-features-5x.md)
4. **Solve portrait cameras from facial landmarks, not vanishing-point tools.** fSpy and similar matchers need real scene lines and struggle without clear vanishing points ✅; use their output only as a prior. — [reference cameras](./reference-camera-setup.md), [lighting & compare](./portrait-lighting-compare.md)
5. **Export cameras with one fixed convention:** `sensor_fit = 'HORIZONTAL'`, `lens = f_px·sensor_width/W`, shift divided by W for both axes, scene resolution = photo pixels, `clip_start ≈ 0.01 m`. Render resolution is per scene, not per camera, so switch it with the active camera or pad all photos to one canvas. Shift units are ↔️ until a round-trip test passes. — [bpy API](./bpy-mesh-api.md), [reference cameras](./reference-camera-setup.md), [lighting & compare](./portrait-lighting-compare.md)
6. **Normalise photos before anything reads them:** bake EXIF orientation into the pixels (Blender ignores the tag 📄, one bug report), convert HEIC 🧠, un-mirror selfies, keep originals for EXIF, never crop off-centre or resize non-uniformly. — [texture painting](./texture-projection-painting.md), [ML deps](./blender-python-ml-deps.md), [FaceBuilder](./facebuilder-blender.md)
7. **Take metric scale from the eye or a measurement, never from MediaPipe.** Visible iris diameter 11.7 ± 0.5 mm 📄 (MediaPipe Iris), or 11.8 mm across several clinical studies ✅ (SD contested), or a measured IPD or ruler in frame; MediaPipe z is relative and pulled toward the mean face 🧠. — [reference cameras](./reference-camera-setup.md), [eyes](./eyes-modeling-blender.md), [face add-ons](./blender-face-addons.md)
8. **A single-view overlay cannot reveal depth errors.** Check profile and ¾ views, reproject photo A onto the mesh and view it through camera B, and run a dolly-zoom (f and z together) test before sculpting. 🧠 — [reference cameras](./reference-camera-setup.md), [lighting & compare](./portrait-lighting-compare.md)
9. **Coach capture and make uncertainty visible, because non-experts fail at capture and correction, not in the solver.** Check every photo in plain words (distance, expression, sharpness, mirroring, hidden ears or hairline), show pose coverage, encode pins by shape as well as colour-blind-safe colour, show a "measured vs guessed" map, and set user-pin σ by landmark class and expertise, stored in mm. 🧠 — [guided workflow](./guided-workflow-accessibility.md)

**Topology, fitting and data**

10. **Freeze the delivery topology.** Fit a fixed template; never Remesh, Dyntopo, Decimate or merge-Symmetrize it; add Multires only once identity is final. These operations destroy vertex order, shape keys, UVs and the landmark map. 🧠 — [face add-ons](./blender-face-addons.md), [sculpt features](./blender-sculpt-features-5x.md), [retopology](./face-retopology.md)
11. **Write fits as shape keys, not edits.** Use `likeness`/`ID_fit` from the engine and an `artist` key for sculpting. Keys hold absolute positions; once keys exist, writes to `me.vertices` revert from Basis 📄, and a Python write to Basis does not propagate to dependent keys 🧠. — [shape keys](./shapekeys-blendshapes.md), [bpy API](./bpy-mesh-api.md)
12. **Treat every scan or 3DMM import as an unknown similarity plus a possible reflection.** Infer units from one face distance (adult intercanthal width spans only ≈31–41 mm ✅), find orientation from landmarks, flag mirrored sources and never auto-flip, and record s, R, t in a sidecar. — [import/export](./import-export-scans.md)
13. **Use OBJ, PLY or the engine's own parsers for anything that carries correspondence.** glTF splits vertices at UV seams 📄; single-mesh OBJ, PLY and FBX are believed to keep order 🧠. — [import/export](./import-export-scans.md), [bridges](./metahuman-cc-bridges.md)
14. **Shrinkwrap is not Wrap.** Warp on landmarks, then run non-rigid ICP with decreasing stiffness 📄, then a short-range Shrinkwrap (limit 2–5 mm), then Multires Reshape for detail 📄 (Reshape needs matching topology and vertex indices). — [import/export](./import-export-scans.md), [sculpting workflow](./sculpting-likeness-workflow.md)
15. **Never retopologise the likeness mesh; design one quad template once.** It needs a lid-margin pair plus 3–5 upper-lid loops, 3–5 loops per vermilion with a support loop, a nasolabial loop on the crease and an exact x = 0 midline. Poles are unavoidable (net Σ(4 − valence) = 8 closed, 4 with an open neck), so place them at least 2 rings from lid margins, vermilion, commissure, alar rim and canthi. 🧠 — [retopology](./face-retopology.md)
16. **Ship a project-owned CC0 template with a versioned sidecar.** Derive it from a CC0 source: Blender Studio Human Base Meshes (CC0 ✅; only stylized and planar heads were seen in the bundle listing) or the MPFB2/MakeHuman hm08 head (CC0 📄). Ship landmark barycentrics, anthropometric points, contour rings, region masks, a mirror map and priors with a topology hash. Non-CC0 models (FLAME 2023 Open, ICT-FaceKit, MediaPipe canonical) load from user paths through one barycentric adapter 🧠. — [template kit](./open-template-head-kit.md)

**Sculpting**

17. **Likeness lives in the primary and secondary forms.** Fix the largest error at the lowest Multires level that can express it, re-check every camera, and leave pores and wrinkles for last. 🧠 — [sculpting workflow](./sculpting-likeness-workflow.md)
18. **Keep symmetry for blockout only, then break it on purpose, after solving head pose.** Healthy faces deviate from their mirror image by about 0.80 mm RMS 📄 and people notice 2–4 mm, while a 2° yaw in a "front" photo already shifts the nose tip 2.4–3.5 mm 🧠. Use a soft symmetry prior and never hard-mirror the result; a mirrored selfie flips every asymmetry. — [sculpt features](./blender-sculpt-features-5x.md), [import/export](./import-export-scans.md), [reference cameras](./reference-camera-setup.md)
19. **Brushes are assets since 4.3.** Activate them with `bpy.ops.brush.asset_activate` (`paint.brush_set` was removed) 📄; `Brush.sculpt_tool` became `sculpt_brush_type` in **5.0** 📄. Pre-4.3 brush scripts, keymaps and tutorials do not carry over. — [sculpt features](./blender-sculpt-features-5x.md)

**Eyes, hair, skin, texture**

20. **Do not fit globe size; fit lids, eye position and gaze.** The globe is about 24.2 mm wide with a range of 21–27 mm 📄, and "big eyes" come from the lids. The anterior corneal radius of about 7.8 mm is firm ✅. In Cycles a glass cornea darkens the iris: enable MNEE shadow caustics (cast on the cornea, receive on iris and sclera, toggle on each light 📄) or turn off the cornea's shadow visibility 🧠. — [eyes](./eyes-modeling-blender.md)
21. **Fit skin and skull under the hair from priors; take only the envelope, hairline, parting, whorl and flow from photos.** Brow landmarks mark hair, not bone (σ 3–5 mm for the skull fit). Grow hair as Curves on a dedicated non-overlapping HairUV map with Add Rest Position. 🧠 — [hair](./hair-blender.md)
22. **Skin is Subsurface Weight 1 with a physical radius.** Subsurface Radius is a real scattering distance per channel 📄, so Radius × Scale only works on a metric head 🧠, and the 4.x default Scale of 0.05 m gives a ~50 mm red radius, about 10–15× too large 🧠. Random walk needs a watertight, non-overlapping mesh 📄; Random Walk (Skin), Subsurface IOR and Subsurface Anisotropy are Cycles-only 📄. — [skin](./skin-shading.md)
23. **Fix UVs once on the template and project through the solved cameras.** Never re-unwrap per subject and never use mirrored or overlapping UVs. Blender's paint occlusion sees only the painted object and Blender has no visibility-weighted multi-photo blend, so the engine should make the albedo and confidence maps. 🧠 — [texture painting](./texture-projection-painting.md)
24. **Compare render and photo in a masked, linear compositor graph and gate geometry before photometry.** Match light direction first, then balance ✅. Blender blends in linear light and its Mix ignores alpha 📄, so multiply Difference by render alpha × face mask; compare under the Standard view transform 🧠. Never auto-accept on photometric or identity scores. — [lighting & compare](./portrait-lighting-compare.md)

**Rigs and expressions**

25. **Rig the template once, not each scan, and default to a hybrid rig:** bones for head, neck, jaw and eyes; ARKit-52-named shape keys plus correctives for the rest. Fitted heads share the template's vertex order, so weights and keys copy by index; recompute only bone positions and expression deltas, and neutralise expression before rigging. 🧠 — [rigging](./face-rigging.md), [shape keys](./shapekeys-blendshapes.md)
26. **Use exact ARKit camelCase names and normalise naming at the boundary.** MediaPipe outputs 52 scores in [0, 1] 📄 under the same names (its `_neutral`/no-`tongueOut` composition is 🧠); write drivers as simple expressions only, which run without Python auto-run 📄. — [shape keys](./shapekeys-blendshapes.md), [rigging](./face-rigging.md)

**Software, packaging and licences**

27. **Probe features, never branch on version numbers, and pick one build per job.** Use 5.2 LTS for long jobs (supported to Jul 2028 📄); since 5.0, `np.asarray(mathutils)` returns a float32 non-contiguous view 📄, so copy with `np.array(x, dtype=np.float64)`. — [version status](./blender-version-status-2026.md), [bpy API](./bpy-mesh-api.md)
28. **Keep the fitter pure NumPy inside Blender and run detectors out of process.** Bulk I/O goes through `foreach_get/set` with matching dtypes 🧠; bpy is not thread-safe 🧠; never bundle NumPy 🧠. extensions.blender.org add-ons must be GPL-3.0-or-later, bundled assets CC0, with no remote code 📄. — [ML deps](./blender-python-ml-deps.md), [packaging](./blender-extensions-packaging.md), [bpy API](./bpy-mesh-api.md)
29. **Licences, not geometry, are the binding constraint.** MPFB2 code is GPL-3.0-or-later ✅ and its base mesh and targets are CC0 📄; FLAME 2017–2023 is non-commercial, with only **FLAME 2023 Open** under CC-BY-4.0 📄; vendor base meshes (CC, Daz, MetaHuman) must not be redistributed ↔️. Store licence as data and block export of unknown or non-commercial items. — [face add-ons](./blender-face-addons.md), [bridges](./metahuman-cc-bridges.md), [packaging](./blender-extensions-packaging.md)
30. **Face photos, iris textures and performance captures are biometric data.** Work offline by default, send no telemetry, and record consent (who, when, scope, any cloud step such as Mesh to MetaHuman's autorig) in the JSON sidecar. 🧠 — [packaging](./blender-extensions-packaging.md), [eyes](./eyes-modeling-blender.md), [bridges](./metahuman-cc-bridges.md), [rigging](./face-rigging.md)

Existing tools fit into these rules: FaceBuilder gives fast matched cameras and a plausible ARKit-ready base, but not the likeness. Its pins need manual fixes 📄, it should not be pinned on hair, and Expressions should be off for neutral photos 🧠 ([FaceBuilder](./facebuilder-blender.md)).

## Quick-reference tables

All values are copied from the notes, with corrections from their verification logs applied. "Src" links the note.

### R1 — Blender release lines (2026-11-20)

| Line | Released | Support ends | Bundled Python / NumPy | Badge | Src |
|---|---|---|---|---|---|
| 4.2 LTS | Jul 2024 | Jul 2026 (ended; MPFB2 still targets it) | 3.11 | 📄 end, 🧠 Python | [version](./blender-version-status-2026.md) |
| 4.5 LTS | Jul 2025 | Jul 2027 | 3.11 / ≈1.24–1.26 | ✅ end, 🧠 Python | [version](./blender-version-status-2026.md) |
| 5.0 | 18 Nov 2025 | — | 3.11 likely | 📄 date, ↔️ Python | [version](./blender-version-status-2026.md) |
| 5.1 | Mar 2026 (plan) | — | 3.13 (release notes); NumPy 2.3.x requested in the dev tracker | 📄 | [packaging](./blender-extensions-packaging.md), [version](./blender-version-status-2026.md) |
| 5.2 LTS | 14 Jul 2026 | Jul 2028 | 3.13.13 (library tracker); NumPy not confirmed | 📄 | [version](./blender-version-status-2026.md), [ML deps](./blender-python-ml-deps.md) |
| 5.2.4 | 10 Nov 2026 (corrected; 16/17 Nov were stale plans) | — | — | 📄 | [version](./blender-version-status-2026.md) |
| 5.3 | 10 Nov 2026, current feature release | next release | not stated (3.13 expected) | ✅ current, 📄 date | [version](./blender-version-status-2026.md) |

Add-on windows: Faceit lists 3.0–5.2 📄, Face Shape Key Rig needs ≥5.2 📄, MPFB2 needs ≥4.2 📄, so only **5.2 LTS** satisfies all three ([face add-ons](./blender-face-addons.md)). FaceBuilder 2026.1.0 supports up to 5.1 📄; 5.2/5.3 support is unconfirmed ([FaceBuilder](./facebuilder-blender.md)). RetopoFlow 4 lists Blender 4.2–5.2 📄 ([retopology](./face-retopology.md)). Auto-Rig Pro is reported as guaranteed for 2.93–4.5 with some fixes for 5.x ↔️ ([rigging](./face-rigging.md)).

### R2 — Pinhole ↔ Blender camera

| Quantity | Relation | Badge | Src |
|---|---|---|---|
| Pixel focal from mm | f_px = f_mm · W / sensor_width | 🧠 | [reference](./reference-camera-setup.md) |
| Pixel focal from EXIF 35 mm-equivalent | f_px = f35 · √(W² + H²) / 43.27 (diagonal convention; some makers use width) | 🧠 / ↔️ | [reference](./reference-camera-setup.md), [face add-ons](./blender-face-addons.md) |
| Blender lens (HORIZONTAL fit) | lens = f_px · sensor_width / W | 🧠 | [reference](./reference-camera-setup.md) |
| Blender shift (HORIZONTAL fit) | shift_x = (W/2 − cx)/W; shift_y = (cy − H/2)/W | 🧠, units ↔️ | [bpy API](./bpy-mesh-api.md), [lighting](./portrait-lighting-compare.md) |
| Fitted sensor dimension | AUTO: max(W, H) 📄 · HORIZONTAL: W · VERTICAL: H | 📄 / 🧠 | [version](./blender-version-status-2026.md) |
| Axes | OpenCV camera = Blender camera · diag(1, −1, −1); Blender looks down −Z | 🧠 | [version](./blender-version-status-2026.md) |
| Distance from iris | z ≈ f_px · 11.7 mm / iris diameter in px | 🧠 | [reference](./reference-camera-setup.md) |
| Near:far magnification | 1 + Δ/z (Δ = depth behind the nose tip) | 🧠 | [reference](./reference-camera-setup.md) |
| Dolly-zoom invariant | keep f/z constant: z_new = z_ref · f_new / f_old | 🧠 | [reference](./reference-camera-setup.md) |
| Free viewport lens | reads ≈2× the camera lens (built-in zoom factor); never read lens values off it | ↔️ | [lighting](./portrait-lighting-compare.md) |
| Defaults | lens 50 mm, sensor 36 mm, AUTO fit, camera `clip_start` 0.1 m | 🧠 | [reference](./reference-camera-setup.md) |

### R3 — Perspective excess of the nose tip, 100·Δ/z % (arithmetic exact; depths approximate)

| Camera → nose tip | Δ 40 mm (eye corners) | Δ 70 mm (cheek contour) | Δ 100 mm (tragion) | Badge |
|---|---|---|---|---|
| 0.3 m | 13 % | 23 % | 33 % | 🧠 |
| 0.5 m | 8 % | 14 % | 20 % | 🧠 |
| 1.0 m | 4 % | 7 % | 10 % | 🧠 |
| 1.5 m | 2.7 % | 4.7 % | 6.7 % | 🧠 |
| 3.0 m | 1.3 % | 2.3 % | 3.3 % | 🧠 |

Head rotation offsets the nose tip by Δ·sin θ: at Δ = 100 mm, 1.7 mm at 1° and 3.5 mm at 2° 🧠 ([reference](./reference-camera-setup.md)). The reported "selfie effect" of a ~30 % wider nasal base at ~30 cm is 📄 in one note and ↔️ in another (see contradictions).

### R4 — Camera and scale priors (σ in log units for focal)

| Parameter | Prior | σ | Badge | Src |
|---|---|---|---|---|
| log f, EXIF f35, uncropped original | f_px from f35 | 0.03–0.05 (FaceBuilder note: 0.03; lighting note: 0.05–0.1) | 🧠 | [reference](./reference-camera-setup.md), [FaceBuilder](./facebuilder-blender.md) |
| log f, crop, zoom or resize suspected | EXIF value | 0.08 | 🧠 | [FaceBuilder](./facebuilder-blender.md) |
| log f, EXIF present but crop unknown | EXIF value | 0.35 (engine default) | 🧠 | [reference](./reference-camera-setup.md) |
| log f, no EXIF | 24–200 mm f35 hypotheses, or 50 mm-eq | none, or 0.35–0.5 | 🧠 | [reference](./reference-camera-setup.md), [FaceBuilder](./facebuilder-blender.md) |
| Focal tie, same body and zoom | shared | 0.02 | 🧠 | [reference](./reference-camera-setup.md) |
| Focal observability gate | estimate only if posterior σ(log f) < 0.10; flag > 0.15 | — | 🧠 | [FaceBuilder](./facebuilder-blender.md), [reference](./reference-camera-setup.md) |
| Principal point | image centre, fixed | 1–2 % of fit dimension if freed | 🧠 | [reference](./reference-camera-setup.md) |
| Radial k1 | 0 | 0.05 only if f35 < 28 mm or action camera; prefer undistorting | 🧠 | [FaceBuilder](./facebuilder-blender.md) |
| Visible iris diameter | 11.7 mm | 0.5 mm | 📄 | [reference](./reference-camera-setup.md) |
| HVID (clinical) | 11.8 mm (studies 11.65–11.92) | 0.6 (single studies 0.3–0.43; pooled 0.79) | ✅ mean, ↔️ SD | [eyes](./eyes-modeling-blender.md) |
| Adult IPD | 63 mm | 3.5–4 population; ~1 measured | 🧠 | [reference](./reference-camera-setup.md), [face add-ons](./blender-face-addons.md) |
| Camera distance | hard bounds 0.25–10 m | warn below 1 m (FaceBuilder note: 0.8 m) | 🧠 | [reference](./reference-camera-setup.md) |

Single-view relative error of z is about 11 % at 0.5 m, 15–20 % at 2 m and ≥30 % at 5 m, so lock focal beyond about 1.2 m unless side views constrain depth 🧠 ([reference](./reference-camera-setup.md)). A 20 % focal error costs ≈1.4 mm of nose width at 0.5 m but ≈0.35 mm at 2 m 🧠 ([FaceBuilder](./facebuilder-blender.md)).

### R5 — Blender defaults to change for a real-scale head

| Setting | Default | Change to | Badge | Src |
|---|---|---|---|---|
| Voxel remesh size | 0.1 (object units; default unconfirmed) | blockout 1–2 mm (3–5 mm for a sphere-start blockout), detail 0.3–0.5 mm; scans 0.5–1.5 mm | 🧠 | [sculpt features](./blender-sculpt-features-5x.md), [sculpting](./sculpting-likeness-workflow.md), [import](./import-export-scans.md) |
| Viewport clip start / end | 0.01 / 1000 m | 0.001 / 10 m | 🧠 | [import](./import-export-scans.md) |
| Camera clip start | 0.1 m (can clip a nose) | 0.01 m | 🧠 | [bpy API](./bpy-mesh-api.md) |
| Viewport lens | 50 mm | 85–100 mm (judge likeness only in camera view) | 🧠 | [sculpting](./sculpting-likeness-workflow.md) |
| Brush radius | 50 px, view-relative | Radius Unit = Scene; grab 20–40 mm, detail 3–8 mm | 🧠 | [sculpt features](./blender-sculpt-features-5x.md) |
| Lock Camera to View | user setting | off; camera transforms locked | 🧠 | [sculpt features](./blender-sculpt-features-5x.md) |
| Merge by Distance | 0.0001 m | 1e-5–5e-5 m, seam duplicates only | 🧠 | [import](./import-export-scans.md) |
| Shrinkwrap Project limit | 0 (off) | 2–5 mm, after the landmark warp | 🧠 | [import](./import-export-scans.md) |
| Bake margin | 16 px | N/256 px | 📄 default | [texture](./texture-projection-painting.md) |
| Bake extrusion / max ray distance | 0 / 0 | 1–3 mm / 5–10 mm (2 / 8 mm for scan→template) | 🧠 | [texture](./texture-projection-painting.md) |
| Texture-paint Bleed | 2 px | 4 / 8 / 16 px at 2K / 4K / 8K | 🧠 | [texture](./texture-projection-painting.md) |
| Subsurface Scale / Radius | 0.05 m / (1, 0.2, 0.1) | 0.001 / (3.67, 1.37, 0.68) (Jensen skin1) | 🧠 | [skin](./skin-shading.md) |
| View transform | AgX (since 4.0) | Standard for numeric photo comparison | 🧠 | [lighting](./portrait-lighting-compare.md) |
| Undo steps | 32 | 32–64 (memory limit if RAM < 32 GB) | 🧠 | [sculpt features](./blender-sculpt-features-5x.md) |

### R6 — Resolution and density budgets

| Item | Value | Badge | Src |
|---|---|---|---|
| Fitting base | 5k–25k vertices, edges ≈2–4 mm (retopology note: ≈5k-vertex fitting template) | 🧠 | [sculpt features](./blender-sculpt-features-5x.md), [retopology](./face-retopology.md) |
| Delivery head incl. neck, ears, mouth bag | 8–12k quads → ≈2–3 M at Multires L4 | 🧠 | [retopology](./face-retopology.md) |
| Edge length across loops | lid margin, canthi 1–2 mm; lips 1.5–3; nose 1.5–3; cheek, forehead 4–7; scalp, neck 6–12 | 🧠 | [retopology](./face-retopology.md) |
| Multires arithmetic | faces = base × 4^L; edge = base edge / 2^L | 🧠 | [sculpt features](./blender-sculpt-features-5x.md) |
| 10k-quad base (head ≈0.13 m²) | L2 160k / 0.9 mm · L3 640k / 0.45 mm · L4 2.6 M / 0.23 mm · L5 10 M / 0.11 mm | 🧠 | [sculpting](./sculpting-likeness-workflow.md) |
| Stage levels | likeness at L2 (L0–L1 for primaries); L4–L5 for wrinkles; pores as maps | 🧠 | [sculpting](./sculpting-likeness-workflow.md) |
| Feature widths | lid margin ~2 mm → edge ≤ 0.7 mm; lid crease and vermilion ridge → ≤ 0.5 mm | 🧠 | [sculpting](./sculpting-likeness-workflow.md) |
| Catmull–Clark shrink of convex features | ≈ e²/(6R), 0.1–0.4 mm on lips, nose tip, chin | 🧠 | [retopology](./face-retopology.md) |
| Facet-free random-walk SSS | render edges ≲ ¼ red mean free path (≈ ≤1 mm) | 🧠 | [skin](./skin-shading.md) |
| Per-vertex projection error | e ≈ L·Δz/(4z); L ≤ √(4ez) ≈ 10 mm for e = 0.05 mm at 0.5 m | 🧠 | [texture](./texture-projection-painting.md) |
| Texel pitch, whole head | 2K 0.23 mm · 4K 0.12 mm · 8K 0.058 mm | 🧠 | [texture](./texture-projection-painting.md) |
| Practical sculpt budgets (32–64 GB) | plain mesh 1–5 M comfortable; Multires total 2–10 M; Dyntopo 0.2–1 M | ↔️ | [sculpt features](./blender-sculpt-features-5x.md) |

### R7 — Fitting priors (σ) for the engine

| Term | Value / σ | Badge | Src |
|---|---|---|---|
| Landmarks by class (% IOD) | anchors 1.5; lid/lip contours 2.5 (sliding); face oval 4 (silhouette); iris centre 1; user pins 0.75 | 🧠 | [face add-ons](./blender-face-addons.md), [FaceBuilder](./facebuilder-blender.md) |
| Detector noise floor (u = face width px / 256) | inner 0.6u; iris 0.4u; brows 1.0u; contour normal 1.5u, tangent ≥ 5u | 🧠 | [ML deps](./blender-python-ml-deps.md) |
| Robust loss | Huber δ = 2σ; drop points beyond 4σ after the first solve | 🧠 | [face add-ons](./blender-face-addons.md) |
| Feature curves, normal σ | lid margin, vermilion 0.5–1.0 mm; alar rim 1–1.5; nasolabial 2–3; jaw silhouette 1.5–2.5 | 🧠 | [retopology](./face-retopology.md) |
| Symmetry | 1–2 mm lateral, ≈0.5 mm upper midline; staged 1 mm (coarse) → 2–3 mm (per-vertex) | 🧠 | [sculpt features](./blender-sculpt-features-5x.md), [sculpting](./sculpting-likeness-workflow.md) |
| Smoothness | Laplacian σ 0.05–0.1 × mean edge; ARAP 5–15 % of rest edge; loop second difference 0.2–0.5 mm | 🧠 | [sculpt features](./blender-sculpt-features-5x.md), [retopology](./face-retopology.md) |
| Residual offsets | cap ≈5 mm unless several views agree | 🧠 | [face add-ons](./blender-face-addons.md) |
| Shape coefficients | MPFB local targets N(0, 0.5²) in [−1, 1]; macros in [0, 1], σ 0.15 to user values; FLAME β N(0, 1), first 50–100 | 🧠 | [face add-ons](./blender-face-addons.md) |
| Expression | absorb basis σ 0.3 then discard; neutral view ψ half-normal σ 0.07 + L1 0.01–0.05; expressive σ 0.5; MediaPipe score as ψ observation σ 0.15–0.25 (0.3 uncalibrated); jaw N(1.5°, 1°²) | 🧠 | [shape keys](./shapekeys-blendshapes.md), [bridges](./metahuman-cc-bridges.md) |
| Eye | globe 24.2 ± 0.9 mm 📄; R anterior 7.8 ± 0.27 ✅; kappa 5 ± 2° 🧠; limbus→rotation centre 10.7 ± 0.6 🧠; apex ahead of lateral orbital rim 16 ± 2.5 ↔️; lid margin–globe gap in [0, 0.3] mm (hard) 🧠 | mixed | [eyes](./eyes-modeling-blender.md) |
| Hair and cranium | brow landmarks σ 3–5 mm (skull fit); trichion–glabella 60 ± 10 mm; hair-covered cranium σ 5–8 mm; scalp ≥ 2 mm inside the hair hull | 🧠 | [hair](./hair-blender.md), [FaceBuilder](./facebuilder-blender.md) |
| Scale σ by source (log-normal) | clinical scanner 0.5–1 %; phone LiDAR 2–3 %; metrical regressor ≈3 %; non-metric 5–7 %; SfM free | 🧠 | [import](./import-export-scans.md) |
| Coarse-to-fine schedule | A similarity + anisotropic scale (7–9 DOF) → B lattice or 10–30 modes, ≥30–40 mm → C per-vertex, 10–20 mm smoothness → D 2–5 mm (dense data only) | 🧠 | [sculpting](./sculpting-likeness-workflow.md) |
| Jaw rig | θ = θmax·w, θmax ≈25° (measured max rotation ≈20–34°); translation after w0 0.4–0.5, dmax 10–15 mm (onset contested) | 🧠 / ↔️ | [rigging](./face-rigging.md) |

### R8 — QA gates and tolerances

| Check | Threshold | Badge | Src |
|---|---|---|---|
| Engine vs Blender projection | ≤ 0.01 px (more means a convention bug) | 🧠 | [bpy API](./bpy-mesh-api.md) |
| Landmark reprojection before texturing | median ≤ 1.5 px, max ≤ 3 px | 🧠 | [texture](./texture-projection-painting.md) |
| Fit residual on pinned points | per pin ≤ 1 % IOD; per view RMS ≤ 0.5 % IOD | 🧠 | [FaceBuilder](./facebuilder-blender.md) |
| Likeness on independent landmarks | NME ≤ 2–3 % IOD; contour mean ≤ 1 % of face height; silhouette < 1–2 mm; primary ratios within ~2 % | 🧠 | [lighting](./portrait-lighting-compare.md), [sculpting](./sculpting-likeness-workflow.md) |
| Depth claims | ≥ 2 views ≥ 30° apart in yaw | 🧠 | [lighting](./portrait-lighting-compare.md) |
| Scale sanity | IPD 55–72 mm; head breadth 140–160 mm; g–op 182–200 mm | 🧠 | [FaceBuilder](./facebuilder-blender.md), [skin](./skin-shading.md) |
| Rigid 7-landmark alignment | RMS 2–5 mm normal; > 10 mm means wrong landmarks or axes | 🧠 | [import](./import-export-scans.md) |
| Vendor wrap acceptance | face RMS < 0.5 mm; scalp/neck < 1.5 mm; no flips; area ratio ≥ 0.2 | 🧠 | [bridges](./metahuman-cc-bridges.md) |
| Export round trip | max \|Δ\| < 2 µm (OBJ); Blender coordinate round trip 1e-6 · s (s ≈ 0.14 m) | 🧠 | [import](./import-export-scans.md), [bpy API](./bpy-mesh-api.md) |
| Shape keys at weight 1 | lid closure gap 0–0.5 mm, never crossing; L/R mirror RMS ≤ 0.5 mm; spill ≤ 1–2 % | 🧠 | [shape keys](./shapekeys-blendshapes.md) |
| Rig weights | sum 1 ± 1e-4; ≤ 4 influences; lip/lid bleed ≤ 0.02; rest = neutral within 1e-5 × head size | 🧠 | [rigging](./face-rigging.md) |
| UV after fitting | \|log area ratio\| ≤ 0.25; conformal ratio ≤ 1.3 face, ≤ 2 ears | 🧠 | [texture](./texture-projection-painting.md) |
| Reference accuracy | stereophotogrammetry vs direct anthropometry, mean difference 0.21 mm ✅; automatic template registration 53.1 % of landmarks < 2 mm 📄; never claim better than the reference modality | ✅ / 📄 | [import](./import-export-scans.md) |

### R9 — Formats, units and vertex order

| Format / source | Units | Vertex order kept | Badge | Src |
|---|---|---|---|---|
| OBJ | none (6 decimals = 1 µm at 1 BU = 1 m) | yes, single object, no split by group | 🧠 | [import](./import-export-scans.md) |
| PLY | none (scanners: mm) | yes | 🧠 | [import](./import-export-scans.md) |
| FBX | unit-scale factor, often cm | usually (control points) | 🧠 | [import](./import-export-scans.md), [bridges](./metahuman-cc-bridges.md) |
| glTF / GLB | metres, Y-up, front +Z | **no**: split at UV seams and hard edges | 📄 | [import](./import-export-scans.md) |
| USD | `metersPerUnit`, `upAxis` | usually | ↔️ | [import](./import-export-scans.md) |
| FLAME | m, Y-up, face +Z (5,023 vertices) | — | 🧠 | [import](./import-export-scans.md) |
| MICA output | metric FLAME | — | 📄 | [import](./import-export-scans.md) |
| BFM 2009 / 2017 | µm (.mat) or mm (.h5) / mm | — | ↔️ | [import](./import-export-scans.md) |
| MakeHuman/MPFB base | dm (MPFB imports in metres by default) | — | 🧠 | [import](./import-export-scans.md), [face add-ons](./blender-face-addons.md) |
| MediaPipe canonical face | cm | — | ↔️ | [import](./import-export-scans.md) |
| Daz / Maya / MetaHuman DNA | cm, Y-up: from Blender ×100 and (x, z, −y) | — | 🧠 | [bridges](./metahuman-cc-bridges.md) |
| Unreal Engine | cm, Z-up, left-handed: ×100 and (x, −y, z) | — | 🧠 | [bridges](./metahuman-cc-bridges.md) |

Legacy Python OBJ/PLY importers were removed in 4.0 📄; the STL add-on was only marked legacy in 4.1 📄; COLLADA removal in 5.0 is 🧠 ([import](./import-export-scans.md)).

### R10 — Licence quick view

| Asset / tool | Terms | Badge | Src |
|---|---|---|---|
| MPFB2 | code GPL-3.0-or-later; base mesh, targets, system assets CC0; asset packs CC0 or CC-BY | ✅ code, 📄 assets | [face add-ons](./blender-face-addons.md) |
| FLAME 2017/2019/2020/2023 | non-commercial research | 📄 | [face add-ons](./blender-face-addons.md) |
| FLAME 2023 Open | CC-BY-4.0, commercial use with attribution | 📄 | [face add-ons](./blender-face-addons.md) |
| Basel Face Model; ICT-FaceKit | research licence; MIT (verify) | 🧠 | [face add-ons](./blender-face-addons.md) |
| InsightFace pretrained models | reported non-commercial | 📄 / ↔️ | [packaging](./blender-extensions-packaging.md) |
| MediaPipe | Apache-2.0 code 🧠; model-card terms not captured | 🧠 | [ML deps](./blender-python-ml-deps.md) |
| MetaHuman | UE EULA since UE 5.6 (Jun 2025): other engines and DCCs allowed, no engine royalty outside UE | ✅ | [bridges](./metahuman-cc-bridges.md) |
| Character Creator, Daz Genesis | no raw base-mesh redistribution | ↔️ | [bridges](./metahuman-cc-bridges.md) |
| extensions.blender.org | add-ons GPL-3.0-or-later, bundled assets CC0, no remote code or externally downloaded components | 📄 | [packaging](./blender-extensions-packaging.md) |
| FaceBuilder | subscription (Freelancer 19.99 USD/month or 191.88 USD/year; Studio 699 USD/year), 15-day trial, commercial use allowed; GPL front end plus closed core | 📄 price/trial/use, ↔️ licence split | [FaceBuilder](./facebuilder-blender.md), [face add-ons](./blender-face-addons.md) |
| Faceit / Face Shape Key Rig / CaptureForge | paid / free GPL / GPL-3.0 | 📄 | [face add-ons](./blender-face-addons.md) |
| CelebAMask-HQ (and hair parsers trained on it) | non-commercial research only, including derived data | 📄 | [hair](./hair-blender.md) |
| RetopoFlow / Quad Remesher | GPL source sold on Superhive / paid, 109.90–139.90 USD perpetual | 📄 | [retopology](./face-retopology.md) |

### R11 — Version-sensitive APIs and the probe to use

| Since | Change | Probe or rule | Badge | Src |
|---|---|---|---|---|
| 4.0 | operator context-override dicts removed | always `with context.temp_override(...)` | 🧠 | [bpy API](./bpy-mesh-api.md) |
| 4.1 | Auto Smooth removed | `hasattr(bpy.types.Mesh, "corner_normals")` | 🧠 | [version](./blender-version-status-2026.md) |
| all | Blender ignores `PYTHONPATH` and user site-packages unless `--python-use-system-env` | install worker deps into a private folder | ✅ | [ML deps](./blender-python-ml-deps.md) |
| all | a script that raises still exits 0 unless `--python-exit-code N` is passed; `BLENDER_USER_RESOURCES` relocates all user files | always pass both in CI | 📄 | [packaging](./blender-extensions-packaging.md) |
| 4.1 | sculpt mask stored as the FLOAT point attribute `.sculpt_mask` (5.x name unconfirmed) | check the attribute after a test mask fill | 📄 | [guided workflow](./guided-workflow-accessibility.md), [sculpt features](./blender-sculpt-features-5x.md) |
| 4.2 | extensions, `online_access`, `extension_path_user` | `__package__.startswith("bl_ext.")` | 🧠 / 📄 manifest | [packaging](./blender-extensions-packaging.md) |
| 4.3 | brush assets; `paint.brush_set` removed; sculpt refactor (entering Sculpt Mode ≈5× faster on a 16M-face mesh, brushes ≈8×, memory ≈30 % lower) | `hasattr(bpy.ops.brush, "asset_activate")` | 📄 | [sculpt features](./blender-sculpt-features-5x.md) |
| 4.4 | slotted Actions (channelbag API) | `Action.fcurves` removal in 5.0 unconfirmed | 📄 / ↔️ | [rigging](./face-rigging.md) |
| 5.0 | `sculpt_tool` → `sculpt_brush_type` | `"sculpt_brush_type" in Brush.bl_rna.properties` | 📄 | [sculpt features](./blender-sculpt-features-5x.md) |
| 5.0 | mathutils → NumPy float32 non-contiguous view | `np.asarray(Vector((0,0,0))).dtype` | 📄 | [version](./blender-version-status-2026.md) |
| 5.0 | `bgl` removed; `bpy.props` not readable as `id["x"]` | `gpu` only; attribute access only | 📄 | [version](./blender-version-status-2026.md) |
| 5.0 | compositor in `scene.compositing_node_group`; Composite → Group Output | `hasattr(bpy.types.Scene, "compositing_node_group")` | 📄 | [lighting](./portrait-lighting-compare.md) |
| 5.0 | EEVEE id back to `BLENDER_EEVEE`; COLLADA removed | try/except on assignment; `hasattr(bpy.ops.wm, "collada_export")` | 🧠 | [version](./blender-version-status-2026.md) |
| 5.2 | Principled BSDF Thin Wall input | never enable on skin | 📄 | [skin](./skin-shading.md) |
| 5.3 | Multires shows textures in Sculpt Mode; paint settings stored per brush | — | 📄 | [sculpt features](./blender-sculpt-features-5x.md) |

### R12 — Template kit (all design defaults to assert on import)

| Item | Value | Badge | Src |
|---|---|---|---|
| CC0 sources allowed in a listed extension | Blender Studio Human Base Meshes (2023; listing shows stylized and planar heads, a realistic head unconfirmed); MakeHuman/MPFB2 hm08 base, targets and proxies | ✅ / 📄 | [template kit](./open-template-head-kit.md) |
| Off-platform only, with notice or attribution | FLAME 2023 Open (CC BY 4.0); MediaPipe canonical mesh (Apache-2.0); ICT-FaceKit (100 identity / 53 expression components and "contact for commercial use" confirmed; MIT licence unconfirmed, so not commercially clean) | 🧠 / ↔️ | [template kit](./open-template-head-kit.md) |
| Skin budget | 8,000–12,000 vertices; closed scalp, open neck, exact x = 0 midline | 🧠 | [template kit](./open-template-head-kit.md) |
| Sub-meshes | lid tuck 2–3 loops at ≤1.5 mm; mouth bag 300–800 vertices, ≈30–40 mm deep; eyeballs 500–1,000 each; teeth and gums 600–3,000; tongue 300–800 | 🧠 | [template kit](./open-template-head-kit.md) |
| Mirror map | KD-tree match at 1e-5 m; a bijection with M(M(i)) = i; midline vertices map to themselves | 🧠 | [template kit](./open-template-head-kit.md) |
| Landmark conventions in the sidecar | MediaPipe 478 (36 face-oval points semi-contour); iBUG-68 (51 surface + 17 contour); WFLW-98 (65 + 33); FLAME 51 + 17; Farkas ≈40 | 🧠 | [template kit](./open-template-head-kit.md) |
| MediaPipe canonical mesh | 468 vertices; 898 triangles closed (852 open); believed cm | 🧠 / ↔️ | [template kit](./open-template-head-kit.md) |
| Per-region offset σ after the basis fit (1 SD) | lids 1–1.5 mm; lips 1.5–2.5; nose 2–3; brow 2–3; cheek 2.5–4; jaw 2–4; ears 3–5; scalp 3–6; neck 5–10 | 🧠 | [template kit](./open-template-head-kit.md) |
| Barycentric basis transfer | U′ = (W ⊗ I₃)U, prior stays N(0, I); accept projections < 2–3 mm with cos(normals) > 0.5; fill the rest harmonically | 🧠 | [template kit](./open-template-head-kit.md) |
| hm08 face targets | piecewise linear incr/decr, so split into two non-negative columns in [0, 1]; optional mass-weighted SVD to K ≈ 40–80 | 🧠 | [template kit](./open-template-head-kit.md) |

### R13 — Guided workflow: photo checks, pin σ, pose coverage

| Check | Warn | Block / exclude | Badge |
|---|---|---|---|
| Resolution (outer IOD in px) | < 250 | < 100 | ↔️ |
| Sharpness (variance of Laplacian at IOD = 256 px) | < 0.6 × set median | < 0.3 × median | 🧠 |
| Clipped highlights / crushed shadows (% face px) | > 1 % / > 2 % | > 5 % / > 10 % | 🧠 |
| Camera distance, Z ≈ f_px · 88 mm / IOD_px | < 1.2 m | < 0.7 m | 🧠 |
| EXIF focal (35 mm-eq) | < 35 mm | < 28 mm | 🧠 |
| eyeBlink / jawOpen / mouthSmile score | > 0.4 / > 0.10 / > 0.25 | > 0.6 / > 0.25 / > 0.5 (drop from identity) | 🧠 |
| Mirrored photo | x-flip lowers RMSE > 30 % | — (never auto-flip) | 🧠 |
| Over-pinning | > 3–5 user pins per feature per view, or > 60 % of pins in one view | — | 🧠 |

User-pin σ (normal direction, mm): crisp corners 0.8 expert / 1.2 novice; vermilion midline, contours and profile silhouettes 1.0; alar base 1.8; nose tip 2.0 ↔️; soft-tissue nasion 1.0 across / 3.5 vertical; ear points 2.5; palpation-defined points (go, zy, me) 4–5 or curve only ↔️; hair-defined points 5 and never for the skull. Combine with a motor term: σ = √(σ_class² + σ_motor²). Pose coverage: frontal 0 ± 5° and both ¾ at ±30–45° required; profiles at ±80–90° strongly advised; a low view (pitch −15 to −25°) advised. Overlays: Okabe–Ito colours plus distinct shapes, targets ≥ 24 px, WCAG contrast 3:1 for graphics. Live re-solve: 2–5 warm-started LM iterations per mouse event at ≥ 20 fps; solve on release if an iteration exceeds ~50 ms. All 🧠 (the check components follow ISO/IEC 29794-5 and BSI's OFIQ 📄; MediaPipe's docs give no per-blendshape thresholds) — [guided workflow](./guided-workflow-accessibility.md)

## Practical checklist for an artist working in Blender

**Before the shoot** ([reference](./reference-camera-setup.md), [hair](./hair-blender.md), [skin](./skin-shading.md))
- [ ] Written consent covers capture, 3D likeness, animation and any cloud step.
- [ ] Camera at ≥1.5 m (ideally 2–3 m), phone 2–5× tele or 85–135 mm, at nose height; zoom, focus and exposure locked; no portrait mode, beauty filter or ultra-wide.
- [ ] Views: front, ±25°, ±45°, ±90°, plus slightly high and low; one extra low view for chin and nostrils.
- [ ] Neutral expression, eyes on the lens, no glasses; ears and hairline clear (hair back or under a cap); a second set with hair as worn plus top and back views.
- [ ] A scale reference: ruler in the face plane or a measured IPD. Optional colour chart and cross-polarised flat-lit set for albedo.

- [ ] Run the add-on's photo checks (R13) and fill the pose ring; retake rather than click "use anyway" when a check blocks.

**Files** ([texture](./texture-projection-painting.md), [ML deps](./blender-python-ml-deps.md))
- [ ] Keep originals with EXIF; bake EXIF orientation into the pixels; convert HEIC to PNG/JPEG.
- [ ] Un-mirror front-camera selfies (check a mole, parting or text).
- [ ] No off-centre crop, no non-uniform resize; undistort ultra-wides and action cameras first.

**Scene** ([sculpting](./sculpting-likeness-workflow.md), [sculpt features](./blender-sculpt-features-5x.md), [version](./blender-version-status-2026.md))
- [ ] One Blender build for the whole job (5.2 LTS for long jobs); record `bpy.app.version_string`, `sys.version`, `numpy.__version__`.
- [ ] Metric, unit scale 1.0, length shown in mm; viewport clip start 0.001 m; Radius Unit = Scene; View lens 85 mm.
- [ ] Head centred on local X = 0, rotation and scale applied.

**Cameras** ([reference](./reference-camera-setup.md), [bpy API](./bpy-mesh-api.md))
- [ ] One camera per photo from the landmark solve: HORIZONTAL fit, lens and shift from R2, resolution = photo pixels, pixel aspect 1, `clip_start` 0.01 m.
- [ ] Photo as camera background (Front, alpha 0.3–0.5), offset/scale/rotation left at identity.
- [ ] Lock camera transforms; Lock Camera to View off; bind cameras to markers and switch resolution with the camera.
- [ ] Check reprojected landmarks: a median above ~1 px with a good fit means a convention bug, not a likeness problem.

**Landmarks and pins** ([guided workflow](./guided-workflow-accessibility.md), [FaceBuilder](./facebuilder-blender.md))
- [ ] Place the first pins in each view blind (model overlay hidden), then review the residual queue worst first.
- [ ] Pin forms, never highlights or shadow edges; use few pins per feature and spread them across views.
- [ ] Check each pin against its epipolar line from the other views; a pin far off the line marks a different point.

**Fit and imports** ([import](./import-export-scans.md), [face add-ons](./blender-face-addons.md), [FaceBuilder](./facebuilder-blender.md))
- [ ] Engine result lands as a `likeness`/`ID_fit` shape key on the fixed template.
- [ ] Imported scans: apply transforms, measure intercanthal width (≈30–42 mm) and biocular width (≈85–100 mm), check mirror against an unflipped photo, clean on a copy.
- [ ] Scale gate: model IPD 55–72 mm; head breadth 140–160 mm.
- [ ] If using FaceBuilder: few confident pins, profiles pinned by hand, never the hair outline; Expressions off for neutral photos; sculpt on a duplicate.

**Sculpt** ([sculpting](./sculpting-likeness-workflow.md), [sculpt features](./blender-sculpt-features-5x.md))
- [ ] No Remesh, Dyntopo, Decimate or merge-Symmetrize on the delivery mesh; concepts live on a separate object.
- [ ] Sculpt on the `artist` key at value 1 with no other key active.
- [ ] Primary pass with symmetry on: profile silhouette, front widths, ¾ cheek turn and orbit depth.
- [ ] Snapshot the symmetric state, then add measured asymmetries (0.5–4 mm).
- [ ] Secondary pass one feature at a time, isolated with face sets; check every camera after each change.
- [ ] Likeness loop: blink, difference composite, horizontal flip of render and photo, thumbnail size, held-out photo, relight to the photo.
- [ ] Multires only after identity is final: L2–L3 secondary, L4–L5 wrinkles; pores in maps.

**Eyes** ([eyes](./eyes-modeling-blender.md))
- [ ] Separate ~24 mm globes placed first; never scaled to the fissure.
- [ ] Cornea shell R ≈ 7.8 mm, IOR 1.336–1.3375, shadow off (or MNEE); iris near-planar ~3 mm behind the apex.
- [ ] 1.5–2 mm lid margin, tear line, caruncle; lashes never touching the cornea.
- [ ] Eye bone at the rotation centre (~13–14 mm behind the apex), Damped Track plus ~4–5° kappa offset.

**Hair** ([hair](./hair-blender.md))
- [ ] HairUV map, Add Rest Position, Curves with Interpolate (Part by Mesh Islands) → Clump → Curl → Trim → Shrinkwrap → restore segment length (that asset's name is unverified; some bundled hair groups failed to import in 5.0).
- [ ] Irregular 3–10 mm hairline transition; colour from Melanin/Redness matched on a swatch under the matched rig, never eyedropped.
- [ ] After any warp: snap roots to surface (Deform), restore segment length, re-run Shrinkwrap.

**Shading and texture** ([skin](./skin-shading.md), [texture](./texture-projection-painting.md), [lighting](./portrait-lighting-compare.md))
- [ ] Watertight skin; separate closed eyes, teeth and tongue; render subdivision to edges ≲ 1 mm.
- [ ] Subsurface Weight 1, Random Walk (Skin), Radius (3.67, 1.37, 0.68) × Scale 0.001, IOR ≈1.4, regional roughness; roughness/normal maps Non-Color.
- [ ] UVs fixed on the template; projection only after the camera gate passes; mask lids, mouth, nostrils and hairline; save or pack painted images.
- [ ] Light match: direction first, then balance; compare in the compositor with alpha × face mask under Standard; check front, ¾ and profile.

**Rig, expressions and export** ([rigging](./face-rigging.md), [shape keys](./shapekeys-blendshapes.md), [bridges](./metahuman-cc-bridges.md))
- [ ] Neutralise expression before rigging; open lids with thickness, mouth bag, teeth and tongue parented to head and jaw.
- [ ] ARKit camelCase key names; transfer deltas (do not copy) and re-fit lid closure and lip seal; QA every key at 1.
- [ ] Bake masks, relative chains and drivers to plain keys before export; OBJ/FBX with stable vertex order; never glTF for morph round trips.
- [ ] For vendor bridges: ×100 scale, check IPD ≈ 6.3 cm after import; never ship vendor meshes.

## Cross-topic contradictions and how to resolve them

| # | Contradiction | Notes involved | Resolution |
|---|---|---|---|
| 1 | **Lens-shift units.** "Fraction of the sensor-fit dimension, W under HORIZONTAL" 🧠 vs developer PRs that describe AUTO fit differently ↔️; the shift divisor is unverified in every note. | [bpy API](./bpy-mesh-api.md), [reference](./reference-camera-setup.md), [lighting](./portrait-lighting-compare.md) | Always write `HORIZONTAL` and divide by W; make a Blender round-trip test (`calc_matrix_camera`, ≤ 0.01 px, landscape and portrait, centred and shifted) the arbiter. The notes' "engine divides by max(W, H)" bug is fixed in the current `face3d/geometry/camera.py` (checked 2026-11-20); only the Blender-side test is missing. |
| 2 | **Bundled Python in 5.x.** bpy API data says 5.2–5.3 "3.11 or 3.13"; ML-deps says 5.1 unknown; packaging and version notes say 5.1 = 3.13 📄 and 5.2 = 3.13.13 📄. | [version](./blender-version-status-2026.md), [packaging](./blender-extensions-packaging.md), [ML deps](./blender-python-ml-deps.md), [bpy API](./bpy-mesh-api.md) | Use R1: 5.1 and 5.2 bundle 3.13 (📄), 5.3 unstated, NumPy 2.3.x from 5.1 per dev tracker. Still probe `sys.version_info` and `numpy.__version__` at runtime and test the engine on 3.11 + NumPy 1.26 and 3.13 + NumPy 2.x. |
| 3 | **`sculpt_tool` → `sculpt_brush_type`:** the version note said 4.3 🧠 until its pass-2 correction to **5.0** 📄, which matches the sculpt-features log; the version data table (`api_breaking_changes_for_face_addon`) still lists 4.3. | [version](./blender-version-status-2026.md), [sculpt features](./blender-sculpt-features-5x.md), [sculpting](./sculpting-likeness-workflow.md) | 5.0, per both verification logs; fix the data row. Probe the property; never branch on version. |
| 4 | **Where extension wheels go.** Packaging (manual, 📄): each extension's own site-packages. ML-deps (2024 tracker, 📄): one shared module namespace, a conflicting version fails to install. | [packaging](./blender-extensions-packaging.md), [ML deps](./blender-python-ml-deps.md) | Unresolved. Design so it does not matter: the core ships no wheels; an optional ONNX build pins versions and is tested alongside another extension that bundles the same package. |
| 5 | **Can a listed extension bundle compiled wheels?** Packaging (ToS reading): no pre-compiled external packages, no externally downloaded components. ML-deps: wheels must be bundled, unmodified, and runtime pip is banned. | [packaging](./blender-extensions-packaging.md), [ML deps](./blender-python-ml-deps.md) | Both agree on "no runtime pip, no downloaded code". Keep the listed core pure Python; ship any onnxruntime build separately or confirm with moderators first; model weights only by user-supplied path or explicit opt-in download outside the listing. |
| 6 | **Platform licence wording:** add-ons must be GPL-3.0-or-later (packaging verification, ToS) vs the ToS text "compatible with GPL v2 or v3" with GPL-3.0-or-later in the docs (template-kit verification), which also did not see the "no externally downloaded components" rule. | [packaging](./blender-extensions-packaging.md), [template kit](./open-template-head-kit.md) | GPL-3.0-or-later satisfies both readings. Treat "no external downloads" as binding until a moderator says otherwise. |
| 7 | **`blender_version_min`:** "4.2.0" (version, face add-ons, MPFB precedent) vs "4.5.0" (packaging manifest example). | [version](./blender-version-status-2026.md), [packaging](./blender-extensions-packaging.md) | Declare only what CI tests. With CI on 4.5, 5.2 and 5.3, use 4.5.0; drop to 4.2.0 only if 4.2 joins CI. |
| 8 | **Focal prior strength.** EXIF log-σ 0.03–0.05 (reference), 0.03 (FaceBuilder), 0.05–0.1 (lighting); no-EXIF 0.35, 0.35–0.5 or multi-hypothesis. | [reference](./reference-camera-setup.md), [FaceBuilder](./facebuilder-blender.md), [lighting](./portrait-lighting-compare.md) | Use the tiered R4 table (provenance decides σ) plus the observability gate (estimate only when posterior σ(log f) < 0.10). All tiers are 🧠: calibrate on consented portraits. |
| 9 | **Landmark σ and acceptance levels.** Per-class 1.5 / 2.5 / 4 % IOD (face add-ons) vs 3 % interior, 6–8 % contour (sculpting) vs 0.6u noise floor (ML deps); gates of 0.5 % IOD per view (FaceBuilder) vs 2–3 % IOD (sculpting, lighting). The notes also mix pupil-to-pupil and outer-canthal IOD. | [face add-ons](./blender-face-addons.md), [ML deps](./blender-python-ml-deps.md), [sculpting](./sculpting-likeness-workflow.md), [FaceBuilder](./facebuilder-blender.md), [lighting](./portrait-lighting-compare.md) | Store σ in mm, as the guided-workflow note recommends: outer-canthal (≈88 mm) and pupil (≈63 mm) IOD differ 1.4×. Use the per-class σ for fitting, floored by the 256-crop noise model. Read 0.5–1 % IOD as a convergence check on points used in the fit and 2–3 % IOD as the likeness gate on independent landmarks; the best published detectors reach ≈2.9–3.3 % NME on 300-W 📄, so that gate sits near the detector floor. |
| 10 | **Symmetry prior σ:** 1–2 mm (face add-ons, sculpt features, bridges), 1 → 2–3 mm by stage (sculpting), 1.5–3 mm (retopology), 0.5 mm on the upper midline, and by region face 1.5 / lateral and lower 2.5 / ears 3.5 mm (template kit). | [sculpt features](./blender-sculpt-features-5x.md), [sculpting](./sculpting-likeness-workflow.md), [retopology](./face-retopology.md), [template kit](./open-template-head-kit.md) | Stage it (≈1 mm coarse, 2–3 mm per-vertex) and scale it by region (0.5 mm upper midline up to ≈3.5 mm on ears); strong pull only in occluded regions; never hard-mirror (all agree). All values 🧠. |
| 11 | **Iris scale:** 11.7 ± 0.5 mm (MediaPipe Iris, 📄) vs HVID 11.8 ± 0.6 mm (several clinical studies, ✅ mean; SD 0.3–0.8 contested). | [reference](./reference-camera-setup.md), [face add-ons](./blender-face-addons.md), [eyes](./eyes-modeling-blender.md) | They differ by 0.1 mm, well inside σ. Prefer 11.8 ± 0.6 (multi-study) for the prior; keep 11.7 as the MediaPipe-compatible value when comparing with MediaPipe depth. |
| 12 | **Selfie effect size:** ~30 % wider nasal base at 30 cm vs 1.5 m (reference, 📄) vs reference distance 5 ft or infinity (lighting, ↔️); pure geometry predicts ~12 % for the nose/face ratio. | [reference](./reference-camera-setup.md), [lighting](./portrait-lighting-compare.md) | Do not use the 30 % figure as a parameter. The engine's perspective camera model handles the effect; use Tables R3/R4 for capture advice. |
| 13 | **View transform:** Standard for comparisons (lighting, texture, version) vs AgX for lookdev, because Standard clips skin highlights (skin). | [lighting](./portrait-lighting-compare.md), [skin](./skin-shading.md) | Both: Standard (Look None) for numeric or overlay comparison with photos; AgX when judging realism of a lookdev render. |
| 14 | **Multires with shape keys.** "Do not combine" (version, sculpting) vs base edits with `foreach_set` letting detail "ride along" (sculpting, sculpt features; unconfirmed in verification) vs inconsistent reports (rigging). | [version](./blender-version-status-2026.md), [sculpting](./sculpting-likeness-workflow.md), [bpy API](./bpy-mesh-api.md), [rigging](./face-rigging.md) | Follow the bpy-API hand-off: keep the keyed master, duplicate it, bake the mix, clear keys, then add Multires; push late engine refits through `multires_reshape`. Test base edits under Multires before promising "detail rides along". |
| 15 | **NICP settings:** stiffness {100…1} normalised by mean edge length, reject beyond max(3·MAD, 5 mm) (import) vs {100…2} relative to the data term, reject beyond 8 mm (bridges); both reject normals > 60°. | [import](./import-export-scans.md), [bridges](./metahuman-cc-bridges.md) | Same schedule shape; normalise stiffness by mean edge length; use the MAD rule with a 5 mm floor for scans and the 8 mm cut for cross-vendor wraps with larger starting misfit. Both are 🧠 and untuned. |
| 16 | **Voxel sizes:** 1–2 mm blockout (sculpt features) vs 3–5 mm blockout and 1.5–2 mm primaries (sculpting) vs 0.5–1.5 mm for scans (import). | [sculpt features](./blender-sculpt-features-5x.md), [sculpting](./sculpting-likeness-workflow.md), [import](./import-export-scans.md) | Not a real conflict: they serve different purposes (sphere blockout, template-scale concepts, scan targets). Pick by purpose (R5); never the 0.1 default. |
| 17 | **Mesh density for projection:** ≤ 2–3 mm edges (reconstruction/texture-extraction) vs ≈10 mm from interpolation error alone (texture painting). | [texture](./texture-projection-painting.md) | Flagged ↔️ in the note. 10 mm bounds texture misplacement only; denser meshes still help normals and silhouettes. For per-vertex projection use L ≤ √(4ez); the per-pixel shader route has no limit. |
| 18 | **FLAME licence:** "research-only" in several notes vs FLAME 2023 Open under CC-BY-4.0 (face-add-ons verification). | [face add-ons](./blender-face-addons.md), [packaging](./blender-extensions-packaging.md), [retopology](./face-retopology.md) | FLAME 2017–2023 non-commercial; FLAME 2023 Open allowed with attribution. Default to the CC0 MPFB2 base; load any FLAME from a user path. |
| 19 | **Jaw kinematics:** rotation first, translation after w0 ≈ 0.4–0.5 (rigging model) vs combined rotation and translation from the start and max rotation ≈20–34° (rigging verification, ↔️). | [rigging](./face-rigging.md), [shape keys](./shapekeys-blendshapes.md) | Keep the piecewise model as a provisional default but expose w0 (allow 0) and θmax, and fit them per subject from jaw-open photos. |
| 20 | **Cornea IOR:** 1.376 tissue vs 1.336–1.3375 effective single surface vs 1.4–1.5 glass presets. | [eyes](./eyes-modeling-blender.md) | Single cornea shell: 1.336–1.3375 reproduces corneal power; 1.376 over-magnifies slightly. |
| 21 | **MPFB2 latest version:** 2.0.18 (MakeHuman page) vs 2.0.16 (one Extensions listing view). | [face add-ons](./blender-face-addons.md), [version](./blender-version-status-2026.md) | Unresolved ↔️; version correspondence tables by base and release, and check vertex count and a topology hash at load. |
| 22 | **User-pin σ:** 0.75 % IOD (≈0.66 mm) for every user pin (FaceBuilder, face add-ons) vs class- and expertise-dependent σ of 0.8–5 mm (guided workflow), which says 0.75 % over-weights novices or soft points 3–30× ↔️. | [FaceBuilder](./facebuilder-blender.md), [face add-ons](./blender-face-addons.md), [guided workflow](./guided-workflow-accessibility.md) | Use the class table (R13) with σ = √(σ_class² + σ_motor²), defaulting to the novice column; keep ≈0.75 % IOD only for expert pins on crisp corners. Calibrate with a short repeat-placement test. |
| 23 | **Camera-distance warning:** below 1 m (reference cameras) vs 0.8 m (FaceBuilder) vs warn below 1.2 m and block below 0.7 m (guided workflow). | [reference](./reference-camera-setup.md), [FaceBuilder](./facebuilder-blender.md), [guided workflow](./guided-workflow-accessibility.md) | Different jobs: coach capture at 1.2 m (the R3 excess is still ≈8 % at 1.2 m for tragion); flag solved cameras below 0.8–1 m; keep the solver's hard bound at 0.25 m. All 🧠. |
| 24 | **Mirror detection:** flag a mesh when reflected Umeyama RMS < 0.5 × proper (import) vs flag a photo when an x-flip lowers its RMSE by > 30 % while other views are unchanged (guided workflow). | [import](./import-export-scans.md), [guided workflow](./guided-workflow-accessibility.md) | Not a conflict: one tests meshes, the other photos. Keep both, report in plain words, and never auto-flip (both agree). |
| 25 | **Mirror-map tolerance:** 1e-5 · s ≈ 1.4 µm (bpy API) vs 1e-5 m = 10 µm (template kit). | [bpy API](./bpy-mesh-api.md), [template kit](./open-template-head-kit.md) | Both sit far above float32 noise (≈7.5e-9 m at 0.1 m). Use the tight value for templates modelled symmetric; for scan-derived topologies match on the mean shape at 1e-5 m, then repair one-to-one with an assignment solve. |
| 26 | **Contour landmark σ:** 2.5 % IOD for lid/lip contours and 4 % for the face oval (face add-ons) vs 3–5 % for all contour points (template kit) vs 6–8 % (sculpting). | [face add-ons](./blender-face-addons.md), [template kit](./open-template-head-kit.md), [sculpting](./sculpting-likeness-workflow.md) | Fit contours as point-to-curve or silhouette terms, where the normal σ matters more than the % IOD value; use the curve normals in R7 (0.5–2.5 mm) and let points slide along the contour. |

## Index of topic notes

Evidence counts are ✅ / 📄 / 🧠 / ↔️ from each note's header.

| Note | What it gives you | Evidence |
|---|---|---|
| [blender-version-status-2026](./blender-version-status-2026.md) | Release lines, LTS windows, bundled Python/NumPy, breaking API changes, camera↔pinhole mapping, precision tolerances | 6 / 26 / 61 / 3 |
| [bpy-mesh-api](./bpy-mesh-api.md) | `foreach_get/set` attribute map, shape-key and vertex-group writes, cameras and backgrounds, threading and timers, bridge defaults | 0 / 4 / 86 / 5 |
| [blender-extensions-packaging](./blender-extensions-packaging.md) | `blender_manifest.toml`, permissions, wheels, extensions.blender.org rules, GPL obligations, headless CI and the synthetic regression suite | 5 / 39 / 67 / 8 |
| [blender-python-ml-deps](./blender-python-ml-deps.md) | Running MediaPipe, OpenCV and ONNX Runtime with Blender: wheel tags, worker processes, detector contract, landmark noise priors | 2 / 26 / 61 / 8 |
| [blender-face-addons](./blender-face-addons.md) | Ecosystem map: MediaPipe, MPFB2, FLAME, Faceit, Face Shape Key Rig, CaptureForge, licences and version support, solver defaults | 4 / 36 / 49 / 4 |
| [facebuilder-blender](./facebuilder-blender.md) | How KeenTools FaceBuilder works in practice, pin σ, focal observability, QA gates, pricing and trial | 1 / 19 / 47 / 19 |
| [guided-workflow-accessibility](./guided-workflow-accessibility.md) | Guided, accessible add-on UX: where novices fail, plain-language photo checks, pin σ by class and expertise, pose coverage, colour-safe overlays, user testing | 0 / 0 / 92 / 17 |
| [reference-camera-setup](./reference-camera-setup.md) | Rebuilding each photo's camera, perspective vs distance tables, scale anchors, solver priors, fSpy limits | 2 / 25 / 47 / 11 |
| [portrait-lighting-compare](./portrait-lighting-compare.md) | Matching photo lighting (SH9, key patterns), compositor comparison graph, verification gates G1–G4 | 1 / 22 / 38 / 12 |
| [import-export-scans](./import-export-scans.md) | Units, axes, mirroring and vertex order across formats; scan cleanup; landmark-anchored NICP; accuracy references | 6 / 20 / 57 / 4 |
| [sculpting-likeness-workflow](./sculpting-likeness-workflow.md) | Coarse-to-fine likeness process, resolution per stage, symmetry, camera-matched checks, likeness tolerances | 0 / 3 / 77 / 16 |
| [blender-sculpt-features-5x](./blender-sculpt-features-5x.md) | Sculpt mode in 4.x–5.x: brush assets, masks, face sets, filters, Multires, real-scale defaults, engine–artist interface | 1 / 11 / 49 / 7 |
| [face-retopology](./face-retopology.md) | Loop systems, pole placement, budgets and edge lengths, retopology tools, template sidecar and curve terms | 0 / 5 / 72 / 11 |
| [open-template-head-kit](./open-template-head-kit.md) | Choosing and packaging a CC0 template head: candidates and licences, sidecar schema, landmark conventions, region σ, barycentric basis transfer, axis conversions | 4 / 7 / 87 / 27 |
| [shapekeys-blendshapes](./shapekeys-blendshapes.md) | Shape-key data model and pitfalls, ARKit 52 and MediaPipe naming, correctives, priors, delta transfer | 0 / 16 / 64 / 11 |
| [face-rigging](./face-rigging.md) | Rigify, Auto-Rig Pro, ARKit rigs, capture paths, pivot priors, weight QA, personalisation and mocap filtering | 9 / 22 / 70 / 13 |
| [metahuman-cc-bridges](./metahuman-cc-bridges.md) | Getting a likeness into MetaHuman, Character Creator and Daz: doors, units and axes, wrap defaults, licences | 2 / 12 / 59 / 10 |
| [eyes-modeling-blender](./eyes-modeling-blender.md) | Sourced globe and cornea geometry, lids and adnexa, Blender eye build and shading, eye priors for fitting | 8 / 18 / 60 / 12 |
| [hair-blender](./hair-blender.md) | Curves hair system, hair assets, Principled Hair BSDF, fitting under hair, hairline and flow priors | 0 / 7 / 89 / 28 |
| [skin-shading](./skin-shading.md) | Principled v2 skin setup, physical SSS radius, roughness priors, microdetail, engine output contract | 2 / 18 / 41 / 18 |
| [texture-projection-painting](./texture-projection-painting.md) | Template UVs, three native projection routes, bake automation, texel density, projection error and UV gates | 0 / 6 / 68 / 17 |

Totals: 53 ✅ / 342 📄 / 1,341 🧠 / 261 ↔️ (recounted from the note headers when this page was last edited; the notes are still being verified).

## Largest gaps

- **No millimetre benchmark** exists in the library for any Blender photo→head route (FaceBuilder, Mesh to MetaHuman, Headshot) or for this project's fitter ([FaceBuilder](./facebuilder-blender.md), [bridges](./metahuman-cc-bridges.md)).
- **Blender 5.x behaviour is mostly unverified** for sculpt changes after 4.3, EXIF handling, `paint.project_image`, the Curves API, internal attribute names (`.sculpt_mask`, `.sculpt_face_set`) and multires write paths ([sculpt features](./blender-sculpt-features-5x.md), [bpy API](./bpy-mesh-api.md), [hair](./hair-blender.md), [texture](./texture-projection-painting.md)).
- **No numeric perceptual tolerance** for 3D likeness error in mm; all gates are engineering heuristics to calibrate on consented portraits ([sculpting](./sculpting-likeness-workflow.md), [lighting](./portrait-lighting-compare.md)).
- **Names still unconfirmed:** the full ARKit 52 raw strings, MediaPipe category order and `_neutral` semantics, and the MediaPipe iris left/right index split ([shape keys](./shapekeys-blendshapes.md), [face add-ons](./blender-face-addons.md)).
- **No study of novice pin accuracy** in photo-to-head tools; the user-pin σ table is a design default to test on synthetic renders ([guided workflow](./guided-workflow-accessibility.md)).
- **FLAME 2023 Open contents** (component counts, masks, UVs, landmark files and their licences) are unknown, and the ICT-FaceKit licence is contested ([template kit](./open-template-head-kit.md)).
- **Licence terms not captured:** MediaPipe model card, community ONNX conversions, ICT-FaceKit, Basel Face Model, FaceBuilder EULA on exported meshes ([ML deps](./blender-python-ml-deps.md), [face add-ons](./blender-face-addons.md)).
