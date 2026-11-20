# Projection painting and texturing heads in Blender

> Texturing a likeness head is two jobs: a UV layout fixed once on the template topology (the face as one upright, centred island; seams hidden at the back midline, behind the ears, inside mouth, lids and nostrils, and around the neck), and projecting the solved photos through their cameras into that layout. Blender projects natively in three ways: **Apply Camera Image** (`paint.project_image`, which projects from the active scene camera using Texture Paint's occlusion, backface and normal settings), **UV Project modifier or Project From View UVs plus an Emit bake**, and a **per-pixel camera-projection shader** built from the camera's Object texture coordinates. None of them blends several photos with visibility-aware weights and gain matching, so the numpy engine (`reconstruction/texture-extraction.md`) should make the albedo, while Blender, Substance or ArmorPaint handle preview, seam cleanup and detail. Per-vertex projections interpolate affinely with error ≈ L·Δz/(4z), negligible with edges ≤10 mm at 0.5 m. No harvest or earlier draft existed, so every item is expert knowledge; UI locations, defaults, licences and prices are time-sensitive and must be checked against Blender 5.2 LTS and 5.3.
>
> Evidence status: 0 ✅ / 3 📄 / 70 🧠 / 18 ↔️ — 🧠 items remain unverified (2026-11-20 pass: Texture Paint option names exist per the 2.82 manual, but project_image behaviour, the 80° Normal default [3.2 API says 80, 2.58 API said 0], Screen Grab Size, Unwrap margin and Smart UV angle stayed unconfirmed; bake margin type default conflicts between API pages).

## Key facts

**UV layout for heads**
- **Unwrap once, on the template.** UVs ride along when the template is warped to each subject, so every subject shares one texture space for masks, mirror maps and statistics. Re-unwrapping or remeshing a fitted head destroys that (`blender/face-retopology.md`) 🧠
- **Seams that hide:** back midline crown→nape; behind each ear in the auriculocephalic sulcus, plus a short cut on the back of the helix; inner lip (wet–dry line) for the mouth bag; lid margins; inside each nostril; neck base. Never cut forehead, cheeks, nose dorsum or vermilion 🧠
- **Face island:** upright, with the midline loop straightened to u = 0.5 and the halves symmetric. A front photo then roughly overlays the UV (easy 2D edits in Krita), and the layout doubles as a mirror map 🧠
- **Unwrap (U) methods:** *Angle Based* (ABF++, default), *Conformal* (LSCM) and *Minimum Stretch* (SLIM, added in about 4.3). Use ABF or Minimum Stretch for the face, and pins plus LSCM or Minimum Stretch for ears. Options: *Fill Holes* (default on; stops eye and mouth openings overlapping), *Correct Aspect*, *Use Subdivision Surface*, *Margin* (default 0.001) 🧠
- **Smart UV Project** (angle limit 66° by default) shatters a face; keep it for teeth, eyeballs and props 🧠
- **Pack Islands** (Ctrl+P, rewritten in 3.6) offers exact-shape packing, lock-pinned and margin methods. Turn rotation off for the face 🧠
- **Check loop:** Live Unwrap with pins, Average Islands Scale, Overlay ▸ Display Stretch (Area or Angle), and a generated *Color Grid* image 🧠
- **No overlapping or mirrored UVs** on a likeness: moles, pigment and scars are asymmetric 🧠
- **UV Smooth:** the Subdivision Surface and Multires *UV Smooth* setting moves UVs near boundaries. Paint, bake and render with identical subdivision settings or the texture swims at seams 🧠
- **UDIMs** (since 2.82) paint and bake, but glTF and most real-time targets want one 0–1 tile, so that is the add-on default 🧠

**Texture Paint mode**
- **Projection painting runs on the CPU, on the evaluated mesh.** Strokes cross UV seams continuously in 3D, and *Bleed* fills the gutter 🧠
- **Slots:** *Material* mode paints the active Image Texture node. *Single Image* paints a chosen image through a chosen UV map, which is simpler for per-view layers 🧠
- **Options:** *Occlude*, *Backface Culling*, *Normal* (fade angle, default ≈80°), *Bleed* (default 2 px), *Dither*, *Cavity Mask*, *Stencil Mask*. Keep X-mirror off 🧠
- **Occlusion only knows the painted object.** Eyeballs, teeth, hair cards and glasses do not block projection, so use face-selection masking or a stencil mask 🧠
- **Brush texture in *Stencil* mapping** overlays a photo in screen space: RMB moves, Shift+RMB scales, Ctrl+RMB rotates, and Alt adds a mask stencil. Align it in camera view 🧠
- **The Clone brush** takes a source image and a source UV map, so it copies texture between UV layouts. That is the manual "re-projection" method 🧠
- **Brushes became assets in 4.3**, so scripts activate brush assets instead of assigning brushes 🧠
- **No native paint layers.** Ucupaint (a free add-on) builds layer stacks from nodes; otherwise use one image per layer and Mix nodes ↔️
- **Sculpt-mode colour painting** (3.2+) is per vertex: 2–6 M vertices is roughly a 2K map. Bake it to an image afterwards 🧠
- **Painted images are not saved with the .blend** unless packed or saved (Image ▸ Save All). This is the classic lost-work disaster 🧠

**Projecting camera-matched photos**
- **`paint.project_image` ("Apply Camera Image")** projects an image from the view stored in its `view_data` ID property (written by Quick Edit / `paint.image_from_view`). Without one, it projects from the **scene camera**, framed by render resolution and pixel aspect. So set the solved camera active and the resolution to the photo's pixels 🧠 (verify on 5.x)
- **Whether brush strength, Normal fade and Bleed all apply to Apply Camera Image** is uncertain; test it on a white sphere ↔️
- **Quick Edit** (`image.project_edit` / `image.project_apply`) round-trips a viewport grab at *Screen Grab Size* (default 512²) through an external editor. Use it for touch-ups, not photos 🧠
- **Project From View**, run in camera view with *Camera Bounds* and *Correct Aspect*, writes a UV map that places the camera frame on 0–1 🧠
- **UV Project modifier:**
  - up to 10 projectors, with Aspect and Scale X/Y;
  - camera projectors use lens and shift;
  - each face takes the projector it faces most, but all projectors write one UV map.

  So use one modifier and UV map per photo 📄 [3] (limit of 10 projectors, closest-aligned projector per face and camera-only Aspect/Scale confirmed; lens/shift use and the single-UV-map consequence not confirmed)
- **Per-vertex projections are affine inside each face**, exact only at vertices (Table 3) 🧠
- **The camera-projection shader is per-pixel exact.**
  - Feed Texture Coordinate ▸ *Object* (object = the camera) into Separate XYZ.
  - With sensor fit HORIZONTAL and k = lens/sensor_width: u = 0.5 + k·x/(−z) + shift_x, and v = 0.5 + k·(W/H)·y/(−z) + shift_y·(W/H).
  - Set the image to *Clip* and mask z < 0.
  - It serves any number of cameras at once. *Window* coordinates only serve the active camera 🧠
- **Blender cameras have no lens distortion,** so undistort the photos first 🧠
- **Blender is believed to ignore JPEG EXIF orientation,** so portrait phone shots can load rotated. Bake the rotation into the pixels before solving 📄 [2] (a bug report documents EXIF rotation being ignored for JPG image textures; current status in 5.x not verified)
- **Judge alignment under the *Standard* view transform.** AgX (default since 4.0) flattens the photo 🧠

**Baking**
- **Baking is Cycles only** (Emit, Diffuse Color, Normal, AO, Combined). The target is the *active* Image Texture node, and it must not feed the material being baked 🧠
- **Selected to Active** transfers a scan texture onto the template. Settings: *Extrusion* or Cage, *Max Ray Distance*, *Margin* (default 16 px; type Adjacent Faces or Extend, about 3.1+). Targets are images or colour attributes 🧠
- **Bake from Multires** (Normals or Displacement) turns a sculpted head into maps for its base level 🧠
- **Bakes write scene-linear values.** The target's colour space sets the encoding: sRGB 8/16-bit for Base Color, linear EXR for float 🧠
- **Bakes run headless** (`blender -b`); projection painting needs a 3D View context 🧠

**Multiple photos**
- **Native layers:** one transparent float image per view via Apply Camera Image (Normal ≈70°), stacked with Mix nodes ↔️
- **Native weighted route:** a Geometry Nodes group writes per-vertex, per-camera weights dot(N, toward camera) and Raycast visibility. Raycasting is done against the head plus hair, glasses and eyeballs. The shader normalises the weights and mixes the camera projections, then an Emit bake writes the texture. There is no gain matching 🧠
- **Engine route:** adds gain compensation, two-band blending, specular rejection and a confidence map. Blender then only loads `albedo.exr` and `confidence.png` 🧠

## Numbers & reference tables

**Table 1 — Blender settings: defaults vs head-scale suggestions** (1 BU = 1 m)

| Setting | Default | Suggested for a head | Badge |
|---|---|---|---|
| Paint Bleed | 2 px | 4 (2K), 8 (4K), 16 (8K) px | 🧠 |
| Paint Normal angle | ≈80° | 70° per-view layer (60–75°) | 🧠 |
| Screen Grab Size | 512×512 | viewport size, ≤4096 | 🧠 |
| Bake Margin | 16 px [1] | N/256 px | 📄 |
| Bake Extrusion | 0 | 0.001–0.003 | 🧠 |
| Bake Max Ray Distance | 0 (unlimited) | 0.005–0.01 | 🧠 |
| Emit bake samples | scene samples | 1–4, denoise off | 🧠 |
| Unwrap Margin | 0.001 | ≈0.004 (16 px at 4K) | 🧠 |

**Table 2 — Texel density by map size** (head + neck ≈0.16 m², 70% UV fill; arithmetic, matches texture-extraction Table 1)

| Map | px/cm | mm/texel | Face at 1.5× density, mm/texel | Badge |
|---|---|---|---|---|
| 2K | 43 | 0.23 | 0.16 | 🧠 |
| 4K | 86 | 0.12 | 0.078 | 🧠 |
| 8K | 171 | 0.058 | 0.039 | 🧠 |

Finer than the best photo's sampling (≈0.07–0.15 mm/px) adds no detail 🧠.

**Table 3 — Affine per-vertex projection error, e ≈ L·Δz/(4z), with Δz = 0.7·L** (45° tilt; arithmetic)

| Edge L (mm) | e at z = 0.5 m (mm) | e at z = 1.0 m (mm) | Badge |
|---|---|---|---|
| 5 | 0.009 | 0.004 | 🧠 |
| 10 | 0.035 | 0.018 | 🧠 |
| 20 | 0.14 | 0.07 | 🧠 |
| 40 | 0.56 | 0.28 | 🧠 |
| 80 | 2.2 | 1.1 | 🧠 |

Inverted: L_max ≈ √(4·e·z), which is ≈10 mm for e = 0.05 mm at 0.5 m. Subdivide a 30–80 mm cage first 🧠.

**Table 4 — View spacing vs worst incidence** (horizontal ring; arithmetic)

| Views | Spacing | Worst θ | Stretch 1/cos θ | cos²θ | Badge |
|---|---|---|---|---|---|
| 0°, ±90° | 90° | 45° | 1.41 | 0.50 | 🧠 |
| 0°, ±60° | 60° | 30° | 1.15 | 0.75 | 🧠 |
| 0°, ±45°, ±90° | 45° | 22.5° | 1.08 | 0.85 | 🧠 |

Add a low view (20–30° below) for the chin, columella and nostrils, which sit at 60–80° in a level front view 🧠.

**Table 5 — RAM per RGBA image** (before undo, mips and the GPU copy)

| Size | 8-bit | 16-bit | float | Badge |
|---|---|---|---|---|
| 4K | 64 MiB | 128 MiB | 256 MiB | 🧠 |
| 8K | 256 MiB | 512 MiB | 1 GiB | 🧠 |

**Table 6 — UV area budget, single tile** (convention)

| Island | Share | Badge |
|---|---|---|
| Face mask (hairline to under-chin, ear to ear) | 45–55% | ↔️ |
| Scalp and back of head | 15–25% | ↔️ |
| Ears (each) | 3–5% | ↔️ |
| Neck | 8–15% | ↔️ |
| Mouth, lid and nostril interiors | 2–5% | ↔️ |

**Table 7 — External tools** (licences and prices are time-sensitive)

| Tool | Licence | Projects from solved cameras? | Best use | Badge |
|---|---|---|---|---|
| Blender | GPL | yes (three routes) | all; weak layers | 🧠 |
| Substance 3D Painter | Adobe subscription; a perpetual Steam edition existed | by eye (stencil/Projection); camera import unclear | layered cleanup, masks | ↔️ |
| ArmorPaint | zlib source (ArmorTools); paid binaries | unclear | free layered painting | ↔️ |
| Foundry Mari | commercial | yes (projectors from imported cameras) | VFX photo projection | ↔️ |
| ZBrush (Maxon) | subscription | Spotlight by eye; polypaint per vertex | sculpt + paint | 🧠 |
| Krita / GIMP | GPL | no (2D) | UV-space edits | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Freeze topology and UVs.** With a Color Grid image applied, face squares should stay under about 1.3:1. Display Stretch (Area) should be clean on the face.
2. **Prepare the photos:**
   - bake EXIF rotation into the pixels;
   - undistort, keeping the principal point;
   - use manual exposure and white balance (≤⅓ stop between views);
   - shoot a flat-lit, ideally cross-polarised texture set of 5–7 views (Table 4).
3. **Camera gate:** sensor fit HORIZONTAL, shift set, render resolution = photo, and the photo as the camera background. Canthi, alar base, mouth corners, tragus and jawline must sit within 1–2 px (`blender/reference-camera-setup.md`). If they do not, fix the fit, not the texture.
4. **Project:**
   - **(a) Preview:** a camera-projection shader per view. Doubled brows or lid creases expose misfit.
   - **(b) Native layers:** Single Image → new 4K image, 32-bit float, alpha 0. Occlude and Backface on, Normal 70°, Bleed 8 px. Set the scene camera and resolution for view k, then F3 → *Apply Camera Image*. Use one image per view.
   - **(c) Curated:** on a mesh with ≤10 mm edges, Project From View (Camera Bounds) → UV map "proj_k". Clone brush with source = photo k through proj_k: front for the central face, ¾ views for cheeks and temples.
   - **(d) Engine:** load `albedo.exr` (Linear) and `confidence.png` (Non-Color).
5. **Mask non-skin** with face-selection masking: lid margins, inner mouth, nostrils, hairline.
6. **Clean up** view transitions by cloning in 3D. Do layered cleanup in Substance or ArmorPaint on the same UVs, and bring the maps back unchanged.
7. **Bake and save.** Bake Multires normals and displacement. Transfer a scan with Selected to Active Emit (extrusion 2 mm, max ray 8 mm). Save float layers as half-float EXR, colour as 16-bit PNG, with relative paths.

| Symptom | Cause | Fix |
|---|---|---|
| Projection offset or scaled | resolution ≠ photo; wrong sensor fit or shift sign | per-view resolution; test on a grid photo |
| Rotated photo | EXIF orientation ignored | rotate pixels before solving |
| Swimming at seams | UV Smooth differs between paint and render | identical subdivision settings |
| Iris on lids, hair on forehead | other objects do not occlude | face mask; Raycast visibility |
| Gaps on nose sides and under chin | tight Normal angle; no low view | 75–80° on that layer; add a low view |
| Dark seam lines | bleed or margin too small for mips | Table 1 |
| Scrambled texture | active UV ≠ render UV | check both UV flags |
| Lost work | unsaved images | Save All; pack |

## Algorithmic implications

- **The template ships its UVs.** After fitting, validate per-face log area ratio and conformal ratio σ₁/σ₂ from the UV→surface Jacobian. On failure, relax interior UVs (SLIM or ARAP) with island boundaries pinned.
- **Backends:** `engine` (default), `shader_preview`, `apply_camera_image` and `uvproject_bake`. Probe availability at runtime: `bpy.ops.paint.project_image`, `margin_type` items, and colour-space names ("Linear Rec.709" vs "Linear").
- **Per-vertex backends** enforce L ≤ √(4·e·z) or subdivide.
- **One camera convention** (HORIZONTAL fit, shift in width units) for solver, shader and modifier. Test it by projecting a synthetic checker through every backend, requiring ≤0.5 px disagreement.
- **Visibility** comes from a Geometry Nodes Raycast that includes extra occluders. Use w = vis·cos^p θ, faded from 60° to 75°, the same as the engine.
- **Bake automation:** `bpy.ops.object.bake(type='EMIT', margin=N//256, cage_extrusion=…, max_ray_distance=…, use_selected_to_active=…, use_clear=True)` with 1 sample, under `blender -b` for tests.

| Parameter | Default | Range / σ | Badge |
|---|---|---|---|
| Map size | 4096 | 2048 phone; 8192 ≥24 MP | 🧠 |
| Face : rest texel density | 1.5 | 1.0–2.0 | ↔️ |
| UV log-area-ratio gate (face) | \|r\| ≤ 0.25 | σ ≈ 0.12 | 🧠 |
| Conformal ratio gate | ≤1.3 face; ≤2 ears | — | 🧠 |
| Pack margin | 16 px at 4K | ≥ bake margin | ↔️ |
| Landmark reprojection gate | median ≤1.5 px, max ≤3 px | σ_px ≈ 0.7 | 🧠 |
| Facing fade | 60° → 75° | 55–80° | 🧠 |
| Per-vertex error budget e | 0.05 mm | ≤0.5 px | 🧠 |
| Views | 5–7 | ≥3; spacing ≤45° plus a low view | 🧠 |
| Transfer extrusion / max ray | 2 / 8 mm | 1–3 / 5–10 mm | 🧠 |

## Disagreements, myths & open questions

- **Myth: "Blender can't project from a solved camera."** It can, by all three routes 🧠
- **Myth: "Project From View and UV Project are perspective-correct."** They are exact only at vertices (Table 3) 🧠
- **Edge length:** texture-extraction asks for ≤2–3 mm, while interpolation alone allows ≈10 mm at 0.5 m. Denser meshes still help normals and silhouettes ↔️
- **Back-midline vs hairline/crown seams** both have advocates ↔️
- **One 8K tile vs UDIMs** (VFX splits face, scalp, ears and neck) ↔️
- **Blender vs Substance vs Mari:** Blender wins on camera fidelity and cost, Substance on layers, Mari on big projection sets ↔️
- **Generative texturing** (ArmorLab, diffusion fills) invents marks that are not the person ↔️
- **Open questions** (time-sensitive):
  - Did 5.x change Texture Paint or `paint.project_image`?
  - Does Substance now import cameras?
  - What are ArmorPaint's current licence, price and projection features?
  - Is a Mari non-commercial edition still offered?
  - Has Blender gained native paint layers?

## Sources

1. Blender Python API, BakeSettings: https://docs.blender.org/api/current/bpy.types.BakeSettings.html (bake margin default 16 px; see also https://docs.blender.org/manual/en/3.6/render/cycles/baking.html)
2. Blender issue #92977, Exif metadata rotation in jpg is ignored in image texture: https://projects.blender.org/blender/blender-manual/issues/92977
3. UV Project Modifier, Blender 5.3 Manual: https://docs.blender.org/manual/en/latest/modeling/modifiers/modify/uv_project.html

All other items are expert knowledge or arithmetic awaiting verification.

**Further reading (by name, not yet linked)**
- Blender Manual: Texture Paint (Options, Texture Slots, External), UV Unwrapping, Cycles Baking, UV Project modifier, Texture Coordinate node
- Lévy, Petitjean, Ray, Maillot, Least Squares Conformal Maps for Automatic Texture Atlas Generation (SIGGRAPH 2002)
- Sheffer, Lévy, Mogilnitsky, Bogomyakov, ABF++: Fast and Robust Angle Based Flattening (ACM TOG 2005)
- Rabinovich, Poranne, Panozzo, Sorkine-Hornung, Scalable Locally Injective Mappings (ACM TOG 2017)
- Sander, Snyder, Gortler, Hoppe, Texture Mapping Progressive Meshes (SIGGRAPH 2001)
- Heckbert, Fundamentals of Texture Mapping and Image Warping (MS thesis, UC Berkeley, 1989)
- Debevec, Taylor, Malik, Modeling and Rendering Architecture from Photographs (SIGGRAPH 1996)
- Lempitsky & Ivanov, Seamless Mosaicing of Image-Based Texture Maps (CVPR 2007)
- Waechter, Moehrle, Goesele, Let There Be Color! Large-Scale Texturing of 3D Reconstructions (ECCV 2014)
- Prada, Kazhdan, Chuang, Hoppe, Gradient-Domain Processing within a Texture Atlas (SIGGRAPH 2018)
- Adobe Substance 3D Painter docs (Projection tool); ArmorPaint/ArmorTools manual; Foundry Mari docs (Projectors); Ucupaint repository

## Verification log (2026-11-20)

- paint.project_image / Apply Camera Image behaviour and presence in 5.2/5.3: unconfirmed (searches returned only older Texture Paint option pages; Occlude, Backface Culling, Normal and Bleed options exist per https://docs.blender.org/manual/en/2.82/sculpt_paint/texture_paint/tool_settings/options.html).
- EXIF orientation ignored: confirmed (one source, a bug report; current status unknown) - https://projects.blender.org/blender/blender-manual/issues/92977
- UV Project modifier: partly confirmed (10 projectors, closest aligned projector per face, camera-only Aspect/Scale); lens shift/sensor fit unconfirmed - https://docs.blender.org/manual/en/latest/modeling/modifiers/modify/uv_project.html
- Defaults bundle: bake margin 16 px confirmed (https://docs.blender.org/api/current/bpy.types.BakeSettings.html); bake margin type default contested (Adjacent Faces on render settings page vs EXTEND on bake operator page, https://docs.blender.org/api/current/bpy_types_enum_items/bake_margin_type_items.html); Normal angle default 80 appears in the 3.2 API (https://docs.blender.org/api/3.2/bpy.types.ImagePaint.html) but was 0 in 2.58, not settled; Bleed 2 px, Screen Grab 512, Unwrap margin 0.001, Smart UV 66 deg: unconfirmed.
