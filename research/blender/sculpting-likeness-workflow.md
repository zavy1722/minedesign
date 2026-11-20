# Blender portrait likeness sculpting workflow

> Likeness sculpting goes coarse to fine: masses and silhouette, primary proportions and planes, secondary features and soft tissue, then tertiary skin detail. Most of the likeness is settled in the first two stages, each worked at the lowest resolution that can express it. Voxel remesh and Dyntopo give free topology for blockout; Multires gives fixed topology that keeps UVs and the landmark↔vertex map, so it is the home for a photo-fitted template. Symmetry stays on until primary proportions agree in every matched camera, then is broken on purpose, and likeness is judged only through perspective cameras solved from the photos (blink, flip, thumbnail, held-out photo), never in ortho front/side views. No harvest or draft existed for this topic, so all claims are expert knowledge awaiting verification; related notes: `blender/reference-camera-setup.md`, `blender/blender-version-status-2026.md`, `anatomy/facial-asymmetry.md`, `blender/eyes-modeling-blender.md`.
>
> Evidence status: 0 ✅ / 3 📄 / 77 🧠 / 16 ↔️ — 🧠 items are queued for web verification. Verification pass 2026-11-20 (pass 2 added voxel remesh and caricature confirmations): 1 claim part-confirmed (Reshape), 3 claims partly supported or unconfirmed (see log).

## Key facts

**Scene and scale**
- **Work at real scale** (1 unit = 1 m, head ≈ 0.18–0.20 m long). Voxel size, Dyntopo constant detail, Scene-unit brush radius and clipping are all in scene units; tutorials sculpting Blender's default 2 m sphere use voxel sizes ~10× too large for a real head 🧠.
- **Brush Radius Unit = Scene** keeps strokes a fixed size in mm at any zoom (measured work); *View* (pixels) suits freehand blending 🧠.
- **The viewport lens defaults to 50 mm**, which exaggerates perspective when orbiting close. Sculpt at a View focal length of ~85–100 mm; judge likeness only through solved cameras 🧠. Set view clip start ≈ 1 mm at real scale 🧠.
- **Since 4.3, brushes are assets** (Essentials library); several were renamed or split into variants, and scripts assigning `tool_settings.sculpt.brush` break 🧠 (time-sensitive; see the version note).

**Resolution strategies**
- **Voxel remesh** (OpenVDB; `Ctrl+R` remesh, `R` sets size) gives an even quad-dominant surface and fuses intersecting pieces. It discards UVs, shape keys, multires and vertex groups (mask, face sets, colour survive only with their Preserve options), and each pass smooths away forms narrower than ~2 voxels. Manual [5] confirms: the Remesh panel's Paint Mask, Face Sets and Color Attributes options reproject those onto the new mesh, all other mesh data layers are lost, shape keys are ignored and Multires is unsupported; `R` sets voxel size 📄 [5]. The face-count figures are the note's own arithmetic (Table 2).
- **Dyntopo** (`Ctrl+D`) refines/collapses triangles locally (Relative px, Constant scene units, Brush % of radius, Manual). Good for pulling out ears, nostrils and additive forms; it triangulates, destroys UVs and custom data, cannot coexist with Multires, slows on dense meshes, and its future in Blender is debated ↔️.
- **Multires**: fixed quad base, Catmull–Clark levels (×4 faces each). Detail is displacement relative to the subdivided base, so moving base vertices (same topology) carries sculpted detail along; tools include *Sculpt Base Mesh*, *Unsubdivide*, *Rebuild Subdivisions*, *Apply Base*, *Reshape* (copies vertex coordinates from another selected mesh with matching topology and vertex indices; Python operator `bpy.ops.object.multires_reshape`) 📄 [1]. It cannot change topology, does not combine with shape keys, and its displacement cannot be written directly from Python 🧠.
- **Shape keys are Blender's nearest thing to sculpt layers**: without Multires/Dyntopo, Sculpt Mode edits the active key, dialled 0–1. Native ZBrush-style layers did not exist as of the author's knowledge ↔️ (verify for 5.x).
- **Back to clean topology:** QuadriFlow (Remesh → Quad), Instant Meshes, Quad Remesher (paid) or manual retopo with face snapping; recover detail by subdividing the retopo, Shrinkwrapping a copy, then Multires *Reshape* 🧠 (moderate confidence on Reshape's vertex-count requirement).

**Stages, forms and brushes**
- **Blockout:** cranium egg, jaw block, neck cylinder tilted forward, brow, cheek and side planes, nose wedge, mouth "barrel" around the dental arch, chin box, eye sockets, ear position 🧠.
- **Primary forms** carry the proportions: head length and breadth, face height-to-width, bizygomatic vs bigonial width, the profile line (forehead slope, glabella, nasal bridge depth, nose projection, lip protrusion, chin), orbit depth, cheekbone apex and ear position 🧠.
- **Secondary forms:** eyelids and crease, lid margins resting on the globe, alar lobule and nostrils, philtrum, vermilion border and tubercle, nasolabial fold, malar fat pad, masseter, jowl, mentalis, ear helix and antihelix, SCM and larynx 🧠.
- **Tertiary forms:** wrinkles, lip lines, pores and scars. They carry age cues but little identity 🧠.
- **Brows and hairline matter more than effort spent on them suggests**: removing eyebrows impaired recognition more than removing eyes (Sadr, Jarudi & Sinha 2003) 🧠; unfamiliar viewers lean on external features such as hair (Ellis, Shepherd & Davies 1979) 🧠.
- **Familiar faces stay recognisable at tens of pixels across** (Sinha et al. 2006), so likeness lives in low spatial frequencies (primary/secondary forms), not pores 🧠.
- **Front Faces Only** plus auto-masking (Topology, Face Sets, Face Set Boundary, Cavity, View/Area Normal) stops lip and lid strokes bleeding onto the opposing surface 🧠.

**Symmetry**
- Mirroring works in the object's **local** axes about its origin: centre the head on local X = 0 with no pose baked in. Since ~2.91 the toggles are stored per mesh (`Mesh.use_mirror_x`); check them every session 🧠.
- **Keep symmetry on through blockout and primaries**; break it once primaries agree in all matched cameras. Typical L–R differences are 0.5–4 mm (`anatomy/facial-asymmetry.md`) 🧠. Teachers disagree on breaking right after blockout vs only for finishing ↔️.
- Fix head pose/tilt (the camera solve) **before** sculpting asymmetry, or the tilt gets baked into the face 🧠. **Mirrored selfies flip real asymmetry**: confirm orientation from a hair parting, mole or text 🧠.

**Camera-matched checking**
- Each photo gets its solved camera with the photo as that camera's Background Image (Opacity ~0.3–0.7; Depth *Front* overlays, *Back* underlays). Render resolution = photo pixels; Sensor Fit and Shift encode the principal point. **Cropped photos break the principal point**: use originals 🧠.
- **Turn off "Lock Camera to View"** and lock camera transforms; orbiting in camera view with it on silently destroys the solve 🧠.
- **Depth errors are invisible from the front**: nose projection, orbit depth, lip protrusion and chin show only in profile and 3/4 cameras 🧠.
- **Matcaps hide planar errors.** Check form under one raking key, then likeness under light matched to the photo's key direction (EEVEE/Cycles) 🧠.
- Grab's **Grab Silhouette** option, used through the matched camera, moves the outline without dragging the front surface 🧠 (moderate confidence).

**Iterating likeness**
- Loop: compare through every camera → take the **largest** error → fix it at the **lowest** Multires level that can express it → re-check all cameras. Early detailing locks proportion errors in 🧠.
- **Fresh-eye checks:** horizontal flip, thumbnail size, blink, greyscale, a break, and a viewer who knows the person 🧠.
- **Use photos from one age period** and hold one out. Photos of one person vary a lot (Jenkins et al. 2011), so matching one flattering photo overfits ↔️.
- **Smoothing drifts the face toward the average.** Mild caricature sometimes raises rated likeness (Rhodes, Brennan & Carey 1987; Benson & Perrett 1991) 📄 [6][7]; the best-likeness level is small for photographic faces (Benson & Perrett: about 4.4% on average) and larger for line drawings (about 16%, Rhodes et al.), and the effect size for 3D sculpts is unsettled ↔️ 0–~16%.

## Numbers & reference tables

**Table 1. Stage → resolution → tools.** Assumes a real-scale adult head plus neck with about 0.13 m² of surface; scale counts with the area. All rows are workflow heuristics.

| Stage | Method | Edge/voxel (mm) | ≈ Faces | Brush radius (mm, Scene) | Key brushes | Symmetry | Badge |
|---|---|---|---|---|---|---|---|
| Blockout | Voxel remesh, or fitted template L0 | 3–5 | 5–15 k | 30–120 | Grab, Elastic Grab, Snake Hook, Pose, Clay Strips, Inflate, Mesh Filter, mask + gizmo, Lattice | on | 🧠 |
| Primary | Voxel 1.5–2.5, or Multires L0–L1 | 1.5–3 | 20–80 k | 10–40 | Clay Strips, Clay, Draw, Flatten/Contrast, Scrape, Fill, Grab, Smooth, Box/Lasso Trim | on → break at end | 🧠 |
| Secondary | Multires L2–L3 on a 10–20 k base | 0.4–1.0 | 0.16–1.3 M | 2–15 | Draw Sharp, Crease, Pinch, Blob, Inflate, Layer, Clay Thumb, Slide Relax, Face Sets | off | 🧠 |
| Tertiary | Multires L4–L5, or displacement map | 0.08–0.25 | 2.5–20 M | 0.3–3 | Draw Sharp / Crease with stabiliser, Layer, alpha textures (Area Plane / Stencil), Multires Displacement Eraser and Smear | off | 🧠 |

**Table 2. Voxel size → faces.** Arithmetic: faces ≈ area / voxel², with area 0.13 m² (0.12–0.14); expect ±30% for shape.

| Voxel (mm) | 5 | 4 | 3 | 2 | 1.5 | 1 | 0.5 | Badge |
|---|---|---|---|---|---|---|---|---|
| ≈ Faces | 5.2 k | 8.1 k | 14 k | 33 k | 58 k | 130 k | 520 k | 🧠 |

**Table 3. Multires level → faces / mean edge length.** Arithmetic: faces = base × 4^L; edge ≈ √(area/faces), area 0.13 m².

| Level | 5 k base | 10 k base | 20 k base | Badge |
|---|---|---|---|---|
| 0 | 5 k / 5.1 mm | 10 k / 3.6 mm | 20 k / 2.5 mm | 🧠 |
| 1 | 20 k / 2.5 mm | 40 k / 1.8 mm | 80 k / 1.3 mm | 🧠 |
| 2 | 80 k / 1.3 mm | 160 k / 0.9 mm | 320 k / 0.64 mm | 🧠 |
| 3 | 320 k / 0.64 mm | 640 k / 0.45 mm | 1.3 M / 0.32 mm | 🧠 |
| 4 | 1.3 M / 0.32 mm | 2.6 M / 0.23 mm | 5.1 M / 0.16 mm | 🧠 |
| 5 | 5.1 M / 0.16 mm | 10 M / 0.11 mm | 20 M / 0.08 mm | 🧠 |

Bases usually put about half or more of their density on the face, so facial edges run roughly 1.5× finer than these means 🧠.

**Table 4. Feature width → required edge length.** Rule: at least 3 edges across a feature; 2 is the bare minimum.

| Feature | Typical width (mm) | Edge needed (mm) | Badge |
|---|---|---|---|
| Lid margin thickness | ~2 | ≤0.7 | 🧠 |
| Upper-lid crease / fold | 1–3 | ≤0.5 | 🧠 |
| Vermilion border ridge | 1–2 | ≤0.5 | 🧠 |
| Philtral column | 2–4 | ≤1 | 🧠 |
| Alar groove | 2–3 | ≤0.8 | 🧠 |
| Fine wrinkle | 0.2–1 | 0.1–0.3 | ↔️ |
| Pore | 0.05–0.3 | ≤0.05–0.1 (better as a texture) | ↔️ |

**Table 5. Real-scale sanity checks**, adult, sexes pooled. These are approximate ranges from Farkas-type norms and vary by population; see the anthropometric notes for sourced values.

| Measure | Range (mm) | Badge |
|---|---|---|
| Head length g–op | 175–210 | 🧠 |
| Head breadth eu–eu | 140–165 | 🧠 |
| Vertex–menton height | 210–245 | 🧠 |
| Bizygomatic width | 120–145 | 🧠 |
| Bigonial width | 90–115 | 🧠 |
| Interpupillary distance | 56–72 (mean ≈ 63) | 🧠 |
| Mouth width ch–ch | 45–58 | 🧠 |
| Nasal width al–al | 30–40 | 🧠 |
| Ear length | 55–70 | 🧠 |
| Lateral orbital rim → corneal apex (Hertel) | ~12–20 | ↔️ |

**Table 6. Likeness tolerance targets.** Engineering heuristics, not measured perceptual thresholds.

| Check | Target | Badge |
|---|---|---|
| Interior-landmark reprojection, per view | < 2–3% IOD (≈1.3–2 mm) | 🧠 |
| Silhouette deviation in matched cameras | < 1–2 mm | 🧠 |
| Primary ratios (face W/H, bigonial/bizygomatic) | within ~2% | 🧠 |
| Asymmetry left uncorrected | < 2–3 mm (roughly the lay detection threshold; see asymmetry note) | ↔️ |

## Applying this to photo→3D face sculpting in Blender

1. **Scene setup.** Metric, unit scale 1.0, mm display; view clip start 0.001 m; View lens 85 mm; Radius Unit Scene. Place both eyeballs first as separate ~24 mm spheres; they anchor sockets and lids (see the eyes note). In profile, a straightedge from supraorbital to infraorbital rim should not touch the cornea 🧠.
2. **Base route.** **(A) Recommended:** the fitting engine's template as a shape key ("likeness", 0–1) on fixed topology, then Multires. **(B) Freeform:** sphere → voxel blockout at 3–5 mm → primaries at 1.5–2 mm → retopo or wrap onto the template → Multires Reshape; it trains the eye but loses the landmark map 🧠.
3. **Cameras.** Import solved cameras, attach each photo as Background Image, match resolution and principal point, lock them, and bind them to markers or a switcher so one key cycles views 🧠.
4. **Primary pass**, symmetry on, Multires L0–L1 or the shape key: (i) profile silhouette (forehead slope, nose projection, chin); (ii) front widths (zygoma, gonion, temples); (iii) 3/4 (cheek turn, orbit depth). Big Grab/Elastic strokes in camera view; Grab Silhouette for outlines 🧠.
5. **Break symmetry.** Confirm head pose, snapshot the symmetric state (duplicate or shape-key basis), then add measured asymmetries: brow, lids, nasal tip, mouth corners, chin, gonion, ears 🧠.
6. **Secondary pass, one feature at a time** (isolate with face sets, check after each): eyes (lid exposure, canthal tilt, crease height); nose (dorsum line, tip width, alar base, columella show); mouth (width vs pupils, lip volumes, corner depth); ears (angle, protrusion) 🧠.
7. **Likeness loop:** blink (Background Image Front/Back), Difference composite, horizontal flip of render *and* photo (compositor Flip node), view at ~100–150 px face height, held-out photo, relight to the photo; fix at the lowest level that can express each error 🧠.
8. **Tertiary and output:** Multires L4–L5 or Texturing-XYZ-style displacement for pores; bake normal/displacement from Multires or selected-to-active from a high copy 🧠.

**What goes wrong** 🧠: ortho planes traced from near-field photos; tutorial-scale voxel sizes; detailing before proportions; symmetry kept to the end (mannequin look); Lock Camera to View ruining a solve; cropped photos with a centred principal point; mirrored selfies; sculpting to one photo; eyeballs too proud, back of skull too short, neck too thin and vertical, ears too high, front plane too wide and flat, lips without dental-arch curvature; Dyntopo or remeshing after the fit, silently breaking shape keys, UVs and the landmark map.

## Algorithmic implications

- **Coarse-to-fine DOF schedule mirroring the stages** 🧠: **A** similarity + anisotropic scale (7–9 DOF); **B** FFD lattice (3³–4³) or 10–30 low-frequency Laplacian/PCA modes, length scale ≥ 30–40 mm ("primary"); **C** per-vertex offsets with ~10–20 mm smoothness length ("secondary"); **D** 2–5 mm only with dense data (scan, depth). Photos rarely support D; tertiary detail is texture or artist work.
- **Fixed-topology contract:** never remesh in the add-on; emit `fit_primary`, `fit_secondary`, `asym` as separate shape keys the artist can blend and audit 🧠. If Multires exists, update **base** coordinates (`foreach_set`, same topology) so sculpted detail rides along; push dense targets via `multires_reshape` from a temporary subdivided object 🧠.
- **Symmetry prior:** σ_sym ≈ 1 mm in A/B, 2–3 mm in C; only occluded regions keep a strong pull; never symmetrize the output (consistent with the Instagram and BlenderArtists notes) 🧠.
- **Landmark σ:** ~0.03×IOD interior, 0.06–0.08×IOD contour, Huber loss; scale prior IPD 63 ± 3.5 mm (1σ), overridden by a caliper measurement 🧠.
- **Silhouette term:** chamfer distance, rendered silhouette vs segmented photo contour, σ ≈ 1–2 px, weighted up in profile views where depth is observable 🧠.
- **Stopping rule:** advance a stage when Table 6 targets hold in **all** views or RMS improves < 1% per iteration. Write per-region residuals and JᵀJ depth confidence as colour attributes (heat maps) 🧠.
- **Anti-averaging:** down-weight the template/PCA prior where data are strong; offer an exaggeration slider (default 0, range 0–20% of deviation from the mean) ↔️.
- **Checker operators:** blink (toggle Background Image depth), flip render, thumbnail render, held-out-view error, next camera: each studio check made one click 🧠.
- **Defaults:** unit scale 1.0; View lens 85 mm; clip start 0.001 m; Radius Unit Scene; background alpha 0.5; `SpaceView3D.lock_camera = False`; camera transforms locked; `Mesh.use_mirror_x = True` until the asymmetry stage; route-B voxel 0.002–0.004 m; Multires L2 for likeness, L4–L5 for detail 🧠.
- **Version safety:** activate brushes via the 4.3+ asset API, probe for `sculpt_brush_type`, never hard-code brush names 🧠.

## Disagreements, myths & open questions

- **Sphere vs base mesh:** sphere/voxel blockout trains seeing; studios mostly start from a base head; for photo fitting, fixed topology wins ↔️.
- **Is Dyntopo obsolete?** Some call voxel remesh + Multires enough; others still use it for ears and nostrils; long-term support unclear ↔️.
- **When to drop symmetry:** right after blockout or only for finishing ↔️.
- **Myth: "front/side reference planes give accuracy."** Valid only for distant telephoto shots 🧠.
- **Myth: "more polygons, more likeness."** Identity sits in low frequencies; pores add realism, not likeness 🧠.
- **Myth: "proportion canons give likeness."** Eyes at half height, mouth corners under the pupils etc. are scaffolds that often hold only loosely ↔️.
- **Caricature in 3D:** O'Toole et al. (1997) linked 3D exaggeration to distinctiveness and perceived age; the best strength for a portrait is open ↔️.
- **Open:** do 5.2 LTS / 5.3 add sculpt layers, unify the plane brushes (Flatten/Fill/Scrape) or change Dyntopo? Practical Multires face limits after the 4.2–4.4 sculpt refactor? Does Reshape still require matching vertex counts at the sculpt level?

## Sources

Only the items cited below have been verified; every other item is 🧠 or ↔️ pending verification.

1. Blender 5.3 Manual, Multiresolution Modifier (Reshape): https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/multiresolution.html
2. Blender 4.3: Sculpt, Paint, Texture (brush assets, `bpy.ops.brush.asset_activate`, Essentials library): https://developer.blender.org/docs/release_notes/4.3/sculpt/
3. Blender 5.2 LTS Manual, Dyntopo: https://docs.blender.org/manual/en/dev/sculpt_paint/sculpting/tool_settings/dyntopo.html
4. Blender 2.91 Manual, Sculpt Symmetry (mirror across local axes): https://docs.blender.org/manual/en/2.91/sculpt_paint/sculpting/tool_settings/symmetry.html
5. Blender 5.2 LTS Manual, Remesh (voxel remesh, preserve/reproject options): https://docs.blender.org/manual/en/latest/sculpt_paint/sculpting/tool_settings/remesh.html
6. Benson & Perrett, perception and recognition of photographic quality facial caricatures (St Andrews research portal): https://research-portal.st-andrews.ac.uk/en/publications/perception-and-recognition-of-photographic-quality-facial-caricat/
7. Rhodes, Brennan & Carey 1987, Identification and ratings of caricatures: https://researchconnect.stonybrook.edu/en/publications/identification-and-ratings-of-caricatures-implications-for-mental/

**Further reading (by name, not yet linked)**
- Blender Manual, *Sculpt Mode* chapter (Multiresolution, Dynamic Topology, Voxel Remesh, Brushes, Symmetry)
- Blender release notes 2.81–5.3, sculpt sections (voxel remesh, face sets, multires rewrite, brush assets)
- Julien Kaspar, Blender Studio sculpting training
- Scott Spencer, *ZBrush Digital Sculpting Human Anatomy* (2010)
- Uldis Zarins & Sandis Kondrats, *Anatomy for Sculptors* (2014)
- Philippe Faraut, *Mastering Portraiture*
- Daisy Grubbs, *Modeling a Likeness in Clay* (1982)
- John Asaro, "Planes of the Head" model
- Andrew Loomis, *Drawing the Head and Hands* (1956)
- Farkas LG, *Anthropometry of the Head and Face*, 2nd ed. (1994)
- Sinha P, Balas B, Ostrovsky Y, Russell R, "Face recognition by humans: nineteen results all computer vision researchers should know about", Proc. IEEE (2006)
- Sadr J, Jarudi I, Sinha P, "The role of eyebrows in face recognition", Perception (2003)
- Ellis HD, Shepherd JW, Davies GM, identification of familiar and unfamiliar faces from internal and external features, Perception (1979)
- Rhodes G, Brennan S, Carey S, "Identification and ratings of caricatures", Cognitive Psychology (1987)
- Benson PJ, Perrett DI, photographic-quality facial caricatures, European Journal of Cognitive Psychology (1991)
- O'Toole AJ, Vetter T, Volz H, Salter EM, three-dimensional caricatures of human heads, Perception (1997)
- Jenkins R, White D, Van Montfort X, Burton AM, "Variability in photos of the same face", Cognition (2011)

## Verification log (2026-11-20)

- **Multires base edits carry detail; Reshape copies coordinates; no direct Python displacement write** — partly confirmed 📄. Manual [1] confirms Reshape copies vertex coordinates from another mesh with matching topology and vertex indices, and the operator `bpy.ops.object.multires_reshape` exists. Not confirmed: "carries detail along" via `foreach_set`, the subdivided-level wording, and the Python-displacement limit (left 🧠). https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/multiresolution.html
- **4.3 brush assets / `asset_activate` / `sculpt_brush_type` / renamed brushes / radius unit in 5.x** — partly confirmed. [2] confirms brush assets, the Essentials library and `bpy.ops.brush.asset_activate` replacing `paint.brush_set`. `sculpt_brush_type`, specific renames and 5.x radius-unit settability not found; items stay 🧠. https://developer.blender.org/docs/release_notes/4.3/sculpt/
- **5.2 LTS / 5.3: no sculpt layers, Dyntopo present, plane brushes unified?** — Dyntopo still present in 5.2 LTS manual [3] (supports that clause only). Sculpt layers, 5.3 status and plane-brush unification unconfirmed; the 5.2 sculpt release notes (https://developer.blender.org/docs/release_notes/5.2/sculpt/) list no sculpt layers but absence is not proof. Left 🧠/↔️.
- **Symmetry in local axes; `Mesh.use_mirror_x` since ~2.91; sculpting active shape key** — local-axes mirroring confirmed by the 2.91 manual [4]. Per-mesh storage / `use_mirror_x` and shape-key sculpting not confirmed; left 🧠.

## Verification log, pass 2 (2026-11-20)

- **Mild caricature improves rated likeness; slider 0-20%, default 0** — confirmed (direction) 📄, with refinement: best-likeness exaggeration is small for photographs (about 4.4% average, Benson & Perrett) and about 16% for line drawings (Rhodes et al.); 0-20% slider range is plausible and stays ↔️. https://research-portal.st-andrews.ac.uk/en/publications/perception-and-recognition-of-photographic-quality-facial-caricat/ ; https://researchconnect.stonybrook.edu/en/publications/identification-and-ratings-of-caricatures-implications-for-mental/
- **Voxel remesh loses data layers; mask/face sets/colour survive via options; Ctrl+R / R** — confirmed 📄. Manual: data layers lost, shape keys ignored, Multires unsupported, Paint Mask/Face Sets/Color Attributes reprojected. Face-count formula is the note's own arithmetic. https://docs.blender.org/manual/en/latest/sculpt_paint/sculpting/tool_settings/remesh.html
