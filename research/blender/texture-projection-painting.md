# Projection painting and texturing heads in Blender

> Texturing a likeness head is two jobs: a UV layout fixed once on the template topology, and projecting the solved photos through their cameras into that layout. The layout puts the face in one upright, centred island and hides seams at the back midline, behind the ears, inside the mouth, lids and nostrils, and around the neck. Blender can project natively in three ways:
> - **Apply Camera Image** (`paint.project_image`) projects an image from the active scene camera, using Texture Paint's occlusion, backface and normal settings.
> - **UV Project modifier or Project From View UVs**, followed by an Emit bake.
> - **A per-pixel camera-projection shader** built from the camera's Object texture coordinates.
>
> None of these blends several photos with visibility-aware weights and gain matching. So the numpy engine (`reconstruction/texture-extraction.md`) should make the albedo, and Blender, Substance or ArmorPaint are for preview, seam cleanup and detail. Per-vertex projections interpolate affinely, with an error of about L·Δz/(4z): negligible with edges ≤10 mm at 0.5 m. No harvest or earlier draft existed, so every item is expert knowledge. UI locations, defaults, licences and prices are time-sensitive and must be checked against Blender 5.2 LTS and 5.3.
>
> Evidence status: 0 ✅ / 0 📄 / 75 🧠 / 13 ↔️ — 🧠 items are queued for web verification.

## Key facts

**UV layout for heads**
- **Unwrap once, on the template.** UVs ride along when the template is warped to each subject. That gives every subject the same texture space for masks, mirror maps and texture statistics. Re-unwrapping or remeshing a fitted head destroys this (`blender/face-retopology.md`) 🧠
- **Seams that hide well:**
  - the back midline from crown to nape (under hair);
  - the auriculocephalic sulcus behind each ear, plus a short cut on the back of the helix so the ear unfolds;
  - the inner lip (wet–dry line) to separate the mouth bag;
  - the lid margins, where lids meet the socket or eyeball;
  - inside each nostril;
  - around the neck base.

  Never cut the visible face mask: forehead, cheeks, nose dorsum or vermilion 🧠
- **Face island:** upright, with the midline loop straightened to u = 0.5 and the two halves symmetric. A front photo then roughly overlays the UV, which helps 2D editing in Krita or Photoshop and gives a direct mirror map 🧠
- **Unwrap methods (U):**
  - *Angle Based* (ABF++, the default);
  - *Conformal* (LSCM);
  - *Minimum Stretch* (SLIM), added in about 4.3.

  Use ABF or Minimum Stretch for the face, and pins plus LSCM or Minimum Stretch for ears 🧠 (verify the version)
- **Unwrap options worth knowing:** *Fill Holes* (on by default; stops eye and mouth openings from overlapping), *Correct Aspect*, *Use Subdivision Surface* and *Margin* (default 0.001) 🧠
- **Smart UV Project** (angle limit 66° by default) shatters a face into many islands, so it is wrong for heads. It is fine for teeth, eyeballs and accessories 🧠
- **Pack Islands** (Ctrl+P), rewritten in 3.6: shape methods Exact / Convex / Bounding box, rotation, lock pinned islands and margin method. Pack with rotation off for the face so its axis stays vertical 🧠
- **Checking and adjusting:** Live Unwrap plus pins (P), Average Islands Scale (Ctrl+A), and Overlay ▸ Display Stretch (Area or Angle) with a generated *UV Grid* or *Color Grid* image are the checking loop 🧠
- **No overlapping or mirrored UVs** on a likeness head: real faces are asymmetric in pigment, moles and scars. Game-style mirrored halves save memory and destroy identity 🧠
- **Subdivision UV Smooth:** the Subdivision Surface and Multires *UV Smooth* settings change UVs near boundaries. Paint and bake with the same subdivision settings used for render and export, or the texture swims at seams 🧠
- **UDIM** tiles (since 2.82) paint and bake in Blender. glTF and many real-time targets do not support UDIM, so a single 0–1 tile is the safer add-on default 🧠

**Texture Paint mode**
- **Projection painting runs on the CPU** and paints on the evaluated mesh. Strokes therefore cross UV seams continuously in 3D, and *Bleed* extends paint into the gutter 🧠
- **Texture Slots:** *Material* mode paints into the active Image Texture node. *Single Image* mode paints a chosen image through a chosen UV map, which is simpler for per-view projection layers 🧠
- **Options:**
  - *Occlude* (only visible pixels);
  - *Backface Culling*;
  - *Normal* with an angle (default ≈80°; fades paint on grazing faces);
  - *Bleed* (default 2 px);
  - *Dither*, *Cavity Mask* and *Stencil Mask*.

  Keep X-mirror off 🧠
- **Occlusion only knows the painted object.** Eyeballs, teeth, hair cards and glasses do not block projection. Restrict painting with face-selection masking (select faces, enable the paint mask) or a stencil mask 🧠
- **Brush texture in Stencil mapping** overlays a photo in the viewport. RMB moves it, Shift+RMB scales, Ctrl+RMB rotates, and Alt+ is used for the mask stencil. It lives in screen space, so align it in camera view 🧠
- **Clone brush with a source image and a source UV map** copies texture between UV layouts. That is the manual "re-projection" method (Applying, step 4c) 🧠
- **Brushes became assets in 4.3**, so scripts must activate brush assets instead of assigning a brush 🧠
- **No native paint layers.** Ucupaint (free add-on) adds a layer stack built from nodes; otherwise use one image per layer and Mix nodes ↔️ (time-sensitive)
- **Colour painting in Sculpt mode** (3.2+) paints a colour attribute per vertex. Resolution equals vertex density (2–6 M verts ≈ a 2K map). Bake it to an image afterwards. Voxel remesh can preserve colour attributes 🧠
- **Painted images are not saved with the .blend** unless packed or saved (Image ▸ Save All). Losing a session of painting this way is the classic disaster 🧠

**Projecting camera-matched photos**
- **`paint.project_image` ("Apply Camera Image"):** "project an edited render from the active camera back onto the object".
  - An image carrying a `view_data` ID property (written by `paint.image_from_view` / Quick Edit) is projected from that stored view.
  - Otherwise it projects from the **scene camera**, framed by the render resolution and pixel aspect.

  So set the solved camera active and the resolution to the photo's pixel size 🧠 (verify the 5.x behaviour)
- **Whether brush strength, normal falloff and bleed all apply to Apply Camera Image** is unclear from memory ↔️. Test on a white sphere.
- **Quick Edit:** `image.project_edit` grabs the viewport at *Screen Grab Size* (default 512²), opens it in the external editor set in Preferences ▸ File Paths, and `image.project_apply` re-projects the edited result. Use it for touch-ups, not for photos 🧠
- **Project From View** (U in camera view, with *Camera Bounds*) writes UVs that put the camera frame on 0–1. Combined with *Correct Aspect* and a photo of the render's aspect, it gives a second UV map for projection 🧠
- **UV Project modifier:**
  - up to 10 projectors, Aspect X/Y and Scale X/Y;
  - a camera projector uses its lens and shift;
  - with several projectors, each face takes the one it faces most directly, but all write one UV map, so one image.

  Multiple photos therefore need one modifier and UV map per camera 🧠
- **Per-vertex projections are affine inside a face.** The UVs are exact only at vertices; Table 3 gives the error 🧠
- **The camera-projection shader is per-pixel exact.**
  - Feed Texture Coordinate ▸ *Object* (object = the camera) into Separate XYZ (x, y, z).
  - With sensor fit HORIZONTAL and k = lens/sensor_width: u = 0.5 + k·x/(−z) + shift_x and v = 0.5 + k·(W/H)·y/(−z) + shift_y·(W/H).
  - Set the Image Texture extension to *Clip* and mask z < 0.
  - It works for any number of cameras at once, unlike *Window* coordinates, which follow the active camera only 🧠
- **Blender cameras have no lens distortion.** Undistort photos first, or project with the solver's undistorted intrinsics 🧠
- **Blender is believed to ignore JPEG EXIF orientation.** Portrait phone shots can load rotated, and a camera solved on the rotated pixels then mismatches. Bake the orientation into the pixels before solving 🧠
- **Judge alignment under the *Standard* view transform.** AgX (the default since 4.0) desaturates and flattens the photo 🧠

**Baking**
- **Baking is Cycles only.** Useful types: Emit, Diffuse (Color / Direct / Indirect), Normal, AO and Combined. The target is the *active* Image Texture node, which must not feed the material being baked (a circular read) 🧠
- **Selected to Active** transfers scan → template. Settings: Cage or *Extrusion*, *Max Ray Distance*, and *Margin* (default 16 px; type Adjacent Faces or Extend, about 3.1+). It can target image textures or colour attributes 🧠
- **Bake from Multires** (Normals or Displacement) turns a sculpted Multires head into maps for its base level 🧠
- **Bake writes scene-linear values.** The target image's colour space decides the encoding: sRGB for 8-bit Base Color, linear EXR for float 🧠
- **Baking runs headless** (`blender -b`). Projection painting needs a 3D View context, so automate through bakes 🧠

**Multiple photos**
- **Native layered route:** one transparent float image per view, projected with Apply Camera Image (Occlude on, Normal ≈70°), stacked front-most-last with Mix nodes or Ucupaint layers ↔️
- **Native weighted route:**
  - A Geometry Nodes group computes, per vertex and camera, a facing weight dot(N, toward camera) and visibility. Visibility uses *Raycast* toward the camera, against the head plus hair, glasses and eyeball objects.
  - The weights go out as named attributes and are normalised in the shader.
  - The shader mixes the per-camera projections, and an Emit bake writes the result.

  Gain matching must be added by hand 🧠
- **The engine route** (texture-extraction note) adds gain compensation, two-band blending, specular rejection and confidence. Blender then only loads `albedo.exr` and `confidence.png` 🧠

## Numbers & reference tables

**Table 1 — Blender settings: defaults vs head-scale suggestions** (1 BU = 1 m)

| Setting | Default | Suggested for a head | Badge |
|---|---|---|---|
| Paint Bleed | 2 px | 4 (2K), 8 (4K), 16 (8K) px | 🧠 |
| Paint Normal angle | ≈80° | 70° per-view layer; 60–75° | 🧠 |
| Occlude / Backface Culling | on / on | on / on | 🧠 |
| Screen Grab Size | 512×512 | viewport size, ≤4096 | 🧠 |
| Bake Margin | 16 px | N/256 px (16 at 4K, 32 at 8K) | 🧠 |
| Bake Extrusion | 0 | 0.001–0.003 | 🧠 |
| Bake Max Ray Distance | 0 (unlimited) | 0.005–0.01 | 🧠 |
| Emit/Diffuse-Color bake samples | scene samples | 1–4, denoise off | 🧠 |
| Unwrap Margin | 0.001 | 0.004 at 4K (≈16 px) | 🧠 |
| Smart UV angle limit | 66° | do not use on the face | 🧠 |

**Table 2 — Texel density by map size** (head + neck ≈0.16 m², 70% UV fill; arithmetic, matches texture-extraction Table 1)

| Map | px/cm | mm/texel | Face at 1.5× density, mm/texel | Badge |
|---|---|---|---|---|
| 1K | 21 | 0.47 | 0.31 | 🧠 |
| 2K | 43 | 0.23 | 0.16 | 🧠 |
| 4K | 86 | 0.12 | 0.078 | 🧠 |
| 8K | 171 | 0.058 | 0.039 | 🧠 |

Do not exceed the best photo's sampling (≈0.07–0.15 mm/px; `reconstruction/texture-extraction.md`) 🧠.

**Table 3 — Affine (per-vertex) projection error, e ≈ L·Δz/(4z), with Δz = 0.7·L** (45° tilt; arithmetic)

| Edge L (mm) | e at z = 0.5 m (mm) | e at z = 1.0 m (mm) | Badge |
|---|---|---|---|
| 5 | 0.009 | 0.004 | 🧠 |
| 10 | 0.035 | 0.018 | 🧠 |
| 20 | 0.14 | 0.07 | 🧠 |
| 40 | 0.56 | 0.28 | 🧠 |
| 80 | 2.2 | 1.1 | 🧠 |

Inverted: L_max ≈ √(4·e·z). For e = 0.05 mm at 0.5 m that is ≈10 mm. A low cage of 30–80 mm quads must be subdivided before using the modifier or Project From View 🧠.

**Table 4 — View spacing vs worst incidence** (horizontal ring; arithmetic)

| Views | Spacing | Worst θ | Stretch 1/cos θ | cos²θ | Badge |
|---|---|---|---|---|---|
| 0°, ±90° | 90° | 45° | 1.41 | 0.50 | 🧠 |
| 0°, ±60°, (±120°) | 60° | 30° | 1.15 | 0.75 | 🧠 |
| 0°, ±45°, ±90° | 45° | 22.5° | 1.08 | 0.85 | 🧠 |

Add one low view (~20–30° below) for the chin, columella and nostrils, which sit at 60–80° in a level front view 🧠.

**Table 5 — RAM per image** (uncompressed; undo, mips and the GPU copy come on top)

| Size | RGBA 8-bit | RGBA 16-bit | RGBA float | Badge |
|---|---|---|---|---|
| 2K | 16 MiB | 32 MiB | 64 MiB | 🧠 |
| 4K | 64 MiB | 128 MiB | 256 MiB | 🧠 |
| 8K | 256 MiB | 512 MiB | 1 GiB | 🧠 |

**Table 6 — UV area budget, single 0–1 tile** (convention, not standard)

| Island | Share of tile | Badge |
|---|---|---|
| Face mask (hairline to under-chin, ear to ear) | 45–55% | ↔️ |
| Scalp and back of head | 15–25% | ↔️ |
| Ears (each) | 3–5% | ↔️ |
| Neck | 8–15% | ↔️ |
| Mouth bag, lid and nostril interiors | 2–5% | ↔️ |

**Table 7 — External tools** (licences and prices are time-sensitive and unverified)

| Tool | Licence model | Projects from solved cameras? | Role | Badge |
|---|---|---|---|---|
| Blender | GPL, free | yes (Apply Camera Image, modifier, shader) | everything; weak layers | 🧠 |
| Substance 3D Painter | Adobe subscription; perpetual Steam edition existed | stencil/Projection tool by eye; camera import unclear | layered cleanup, masks, detail | ↔️ |
| ArmorPaint | open source (zlib, ArmorTools repo); paid binaries | unclear | free layered painting, Blender-like | ↔️ |
| Foundry Mari | commercial | yes (projectors from imported cameras) | VFX-grade photo projection | ↔️ |
| 3DCoat | perpetual or rental | reference-image projection | painting, retopo, UV | ↔️ |
| ZBrush (Maxon) | subscription | Spotlight, by eye; polypaint is per vertex | sculpt + paint | 🧠 |
| Krita / GIMP | GPL, free | no (2D) | seam and detail edits in UV space | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Freeze topology and UVs first.** Check them with a Color Grid image: face squares should stay below about 1.3:1 aspect, and Display Stretch (Area) should show no blue or red patches on the face. Check texel density per island (Texel Density Checker or TexTools; time-sensitive).
2. **Prepare the photos.**
   - Bake EXIF rotation into the pixels.
   - Undistort with the solver's model, keeping the principal point.
   - Use manual exposure and white balance, with ≤⅓-stop differences between views.
   - Shoot one flat-lit texture set, cross-polarised if possible.
   - Shoot 5–7 views (Table 4).
3. **Camera gate.**
   - Import the solved cameras with sensor fit HORIZONTAL, lens shift and render resolution set to the photo size.
   - Use the photo as the camera's background image.
   - The inner canthi, alar base, mouth corners, tragus and jawline must sit within 1–2 px (`blender/reference-camera-setup.md`). If they do not, fix the fit rather than the texture.
4. **Project.**
   - **(a) Preview:** camera-projection shader per view, toggled with a Mix factor. It is per-pixel exact, needs no bake, and makes misfit visible as doubled brows or lid creases.
   - **(b) Native layers:** Single Image slot → new 4K image, 32-bit float, alpha 0; Occlude on, Backface on, Normal 70°, Bleed 8 px. Then set the scene camera to view k and render resolution = photo k, and run F3 → *Apply Camera Image*. Repeat into one image per view.
   - **(c) Artist-curated:** add UV map "proj_k" via Project From View (Camera Bounds) on a mesh subdivided to ≤10 mm edges. Clone brush: source image = photo k, source UV = proj_k, target = main UV. Hand-paint which region takes which view: front for the central face, ¾ views for the cheeks and temples.
   - **(d) Engine:** load `albedo.exr` (linear) and `confidence.png` (Non-Color).
5. **Mask what is not skin.** Use face-selection masking to exclude the lid margins, inner mouth, nostrils and hairline. Hair, lashes and glasses never occlude in paint mode.
6. **Clean up.** Clone or soften across view transitions in 3D, never in 2D across UV seams. Use Substance or ArmorPaint for layered cleanup via FBX/OBJ with the same UVs, then bring maps back unchanged.
7. **Bake and save.**
   - Bake Multires normals and displacement if the head is sculpted.
   - For a scan texture, transfer it to the template with Selected to Active Emit (extrusion 2 mm, max ray 8 mm).
   - Save float layers as half-float EXR and colour as 16-bit PNG, with relative paths.

**What goes wrong (Blender-specific)**

| Symptom | Cause | Fix |
|---|---|---|
| Projection offset or scaled | render resolution ≠ photo, wrong sensor fit, shift sign | per-view resolution; HORIZONTAL fit; test on a grid photo |
| Rotated or mirrored photo | EXIF orientation ignored | rotate pixels before solving |
| Swimming at subdivided seams | UV Smooth differs between paint and render | same subdivision settings everywhere |
| Iris colour on eyelids, hair on forehead | other objects do not occlude | face mask; Raycast visibility in Geometry Nodes |
| Gaps on the nose sides and under the chin | Normal angle too tight; no low view | 75–80° on that layer; add a low view |
| Dark seam lines in render | Bleed or bake margin too small for mips | Table 1 values |
| Texture scrambled | painting the active UV ≠ the render UV | check both UV map flags |
| Banding after blending | 8-bit sRGB paint target | float or 16-bit targets |
| Lost work | unsaved images | Save All Images; pack |

## Algorithmic implications

- **The template ships its UV layout.** The engine fits geometry only, then validates UVs: per-face log area ratio (normalised by total area) and conformal ratio σ₁/σ₂ from the 2×2 UV→surface Jacobian. On failure, it relaxes interior UVs with SLIM or ARAP, keeping island boundaries pinned.
- **Projection backends:** `engine` (default), `shader_preview`, `apply_camera_image` and `uvproject_bake`. Pick the backend at runtime by probing operator and enum availability (`bpy.ops.paint.project_image`, `margin_type` items, colour-space names such as "Linear Rec.709" vs "Linear"), not by version number.
- **Per-vertex backends** must check the edge budget L ≤ √(4·e·z) (Table 3) and subdivide or warn.
- **Camera export:** one convention for solver, shader and modifier (sensor fit HORIZONTAL, shift in width units). Unit-test it by projecting a synthetic checker through each backend; require ≤0.5 px disagreement.
- **Visibility in Blender** via a Geometry Nodes Raycast group that includes extra occluder objects. Weight w = vis·cos^p θ, fading from 60° to 75° (shared with the engine).
- **Bake automation:** `bpy.ops.object.bake(type='EMIT', margin=N//256, cage_extrusion=…, max_ray_distance=…, use_selected_to_active=…, use_clear=True)`, Cycles samples 1, under `blender -b` for tests.

**Engine/add-on defaults**

| Parameter | Default | Range / σ | Badge |
|---|---|---|---|
| Map size | 4096 | 2048 phone; 8192 ≥24 MP | 🧠 |
| Face : rest texel-density ratio | 1.5 | 1.0–2.0 | ↔️ |
| UV log-area-ratio gate (face) | \|r\| ≤ 0.25 | σ ≈ 0.12 | 🧠 |
| Conformal ratio gate | ≤1.3 face; ≤2 ears | — | 🧠 |
| Pack margin | 16 px at 4K | 2–4× bake bleed of mip chain | ↔️ |
| Bake margin / paint bleed | N/256 / N/512 px | — | 🧠 |
| Landmark reprojection gate | median ≤1.5 px; max ≤3 px | σ_px ≈ 0.7 | 🧠 |
| Facing fade | 60° → 75° | 55–80° | 🧠 |
| Per-vertex projection error budget e | 0.05 mm | ≤0.5 px | 🧠 |
| Views | 5–7 | ≥3; spacing ≤45° plus one low view | 🧠 |
| Transfer bake extrusion / max ray | 2 mm / 8 mm | 1–3 / 5–10 mm | 🧠 |

## Disagreements, myths & open questions

- **Myth: "Blender can't project from a solved camera."** Apply Camera Image, the UV Project modifier and the camera-coordinate shader all can 🧠
- **Myth: "Project From View and UV Project are perspective-correct."** They are exact only at vertices; the error is small on dense meshes (Table 3) 🧠
- **Mesh density for per-vertex projection:** the texture-extraction note asks for edges ≤2–3 mm. Interpolation error alone allows ≈10 mm at 0.5 m; denser meshes still help normals and silhouettes ↔️
- **Seam on the back midline vs along the hairline and crown:** both are used. The back midline keeps the scalp one island, while a hairline seam isolates hair-covered texels ↔️
- **One 8K tile vs UDIMs:** VFX splits the head over several UDIM tiles (face, scalp, ears, neck), while real-time and glTF want one tile ↔️
- **Paint in Blender, Substance or Mari?** Blender wins on camera fidelity and price, Substance on layers and masks, Mari on large photo-projection sets ↔️
- **Vertex colour vs image painting:** vertex colour is tied to mesh density and topology, but is quick on a sculpt 🧠
- **Generative texture tools** (ArmorLab, diffusion in Substance) invent pores, moles and pigment that are not the person; keep them out of observed texels ↔️
- **Open questions** (time-sensitive):
  - Did 5.x change Texture Paint, the External panel or `paint.project_image`?
  - Does Substance 3D Painter now import cameras for projection?
  - What are ArmorPaint's current licence, price and projection features?
  - Is Mari still offered in a non-commercial or indie edition?
  - Has Blender gained native paint layers?

## Sources

No harvest file or earlier draft existed for this topic, so no URL can be cited. Every item above is expert knowledge or arithmetic awaiting verification.

**Further reading (by name, not yet linked)**
- Blender Manual: Texture Paint (Tool Settings ▸ Options, Texture Slots, External), UV Editor ▸ Unwrapping, Cycles ▸ Baking, UV Project modifier, Texture Coordinate node
- Lévy, Petitjean, Ray, Maillot, Least Squares Conformal Maps for Automatic Texture Atlas Generation (SIGGRAPH 2002)
- Sheffer, Lévy, Mogilnitsky, Bogomyakov, ABF++: Fast and Robust Angle Based Flattening (ACM TOG 2005)
- Rabinovich, Poranne, Panozzo, Sorkine-Hornung, Scalable Locally Injective Mappings (ACM TOG 2017)
- Sander, Snyder, Gortler, Hoppe, Texture Mapping Progressive Meshes (SIGGRAPH 2001), for the stretch metric
- Heckbert, Fundamentals of Texture Mapping and Image Warping (MS thesis, UC Berkeley, 1989), for perspective-correct interpolation
- Debevec, Taylor, Malik, Modeling and Rendering Architecture from Photographs (SIGGRAPH 1996), for view-dependent texture mapping
- Lempitsky & Ivanov, Seamless Mosaicing of Image-Based Texture Maps (CVPR 2007)
- Waechter, Moehrle, Goesele, Let There Be Color! Large-Scale Texturing of 3D Reconstructions (ECCV 2014)
- Prada, Kazhdan, Chuang, Hoppe, Gradient-Domain Processing within a Texture Atlas (SIGGRAPH 2018)
- Adobe Substance 3D Painter documentation (Projection tool); ArmorPaint / ArmorTools repository and manual; Foundry Mari documentation (Projectors); Ucupaint add-on repository
