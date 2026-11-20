# ZBrush likeness methods translated to Blender

> The ZBrush likeness tradition (Scott Spencer, Rafael Grassetti, Pablo Muñoz Gómez, Ryan Kingslien and peers) is one loop: collect many long-lens photos, block primary forms at low resolution, match a perspective camera to each photo, overlay it (Spotlight, See-through, grid images), and move big masses until silhouette and features agree in every view at once, then break symmetry, test changes on Layers, and judge with hair and matched light. Blender has every ingredient plus one structural advantage: each photo keeps its own persistent camera object with the photo as a front-depth background image, so you flip between solved views instead of re-matching ZBrush's single canvas camera. Its weak spots are sculpt layers and a morph brush (shape keys and Geometry Nodes only partly replace them) and a default viewport whose "50 mm" is, we believe, wide-angle. No harvest or earlier draft existed, so everything here is expert knowledge or pinhole arithmetic. For the fitting engine this becomes a joint multi-view perspective solve, coarse-to-fine stages exported as dialable shape keys, and a symmetry prior relaxed late.
>
> Evidence status: 0 ✅ / 1 📄 / 59 🧠 / 21 ↔️ — 🧠 items are queued for web verification.

## Key facts

**The shared ZBrush likeness method.** Which teacher said exactly what is not verified here; the steps are the common core of ZBrush-era likeness teaching.

- **Teachers (roles only).** Spencer: Sybex ZBrush books, likeness collectibles, film creatures. Grassetti: character art director, *God of War* (2018). Muñoz Gómez: ZBrushGuides and courses. Kingslien: early Pixologic evangelist, ZBrush Workshops founder. 🧠
- **Reference first.** Many photos from one age and weight window, neutral face, teeth together: front, both ¾, both profiles, slightly high and low; known lenses, long distances. Film grabs are secondary (unknown lens, varying expression). 🧠
- **Primary forms at low resolution.** Block the cranium, jaw width and angle, brow mass, cheek mass, nose block and ear position on a low DynaMesh or subdivision level 1–2. The common rule: if it does not read as the person when blurred, detail will not save it. 🧠
- **Camera match, then overlay.** Perspective on (P), set angle of view or focal length, load the photo into Spotlight (Texture → Add To Spotlight; Shift+Z shows/hides, Z toggles the dial; lower its opacity) [2], or raise the **See-through** slider to see a photo viewer behind the translucent ZBrush window. Place the model until stable landmarks (canthi, alar base, tragus, menton) align, then fix silhouette and placement with a large **Move** brush. 📄 (Spotlight shortcuts only, [2]; rest unverified)
- **Spotlight is screen-space**: you move the *model* into the photo, and any view rotation breaks the match, so artists store views (timeline keys, ImagePlane plugin views). 🧠
- **Whack-a-mole across views.** A front-view fix moves the ¾ and profile, so cycle all views until they agree; fitting one "hero" photo is the classic failure. 🧠
- **Profile is most diagnostic**: forehead slope, nasion depth, nose projection and tip angle, lip protrusion, chin projection read unambiguously in silhouette; front widths come next. 🧠
- **Then secondary forms** (lids, nasolabial region, lips, ears), **then symmetry off**, then hairline, brows and hair (in ZBrush, FiberMesh or proxies), because a bald, browless head on a grey matcap rarely reads as anyone. 🧠
- **Layers for A/B tests.** Record a change (wider jaw, deeper nasion) on a 3D Layer and dial its intensity to compare. **Morph Target** (StoreMT plus the Morph brush) brushes regions back to a stored state. 🧠
- **Fresh eyes**: flip, blink-compare, step away, ask people who know the sitter. 🧠

**ZBrush camera specifics**

- ZBrush opens in a non-perspective (orthographic-like) view; P toggles perspective; the Draw palette holds Angle of View. 🧠
- ZBrush 4R8 (2017) added a "Universal Camera" with a real focal length in mm and stored or exportable cameras. Before that, perspective did not map cleanly to a physical lens, so many artists matched by eye. ↔️ (Universal Camera with real focal length confirmed by Maxon [1]; the 4R8/2017 date, storable cameras and defaults remain unverified)
- Orthographic grid images (Draw palette Front-Back/Left-Right maps, the ImagePlane plugin) suit blueprint-style long-lens references only. 🧠

**Blender equivalents**

- **Camera match = one camera object per photo**: Sensor Fit Horizontal, 36 mm width with the EXIF 35 mm-equivalent focal length (or physical focal length with the true sensor width), resolution = photo pixels, Shift X/Y for an off-centre principal point, photo as camera **Background Image** (Stretch). 🧠
- **Spotlight overlay → Background Image with Depth: Front** and opacity 0.3–0.5. **Spotlight projection painting → Texture Paint Stencil mapping** (RMB drag moves, Shift+RMB scales, Ctrl+RMB rotates) or a **UV Project modifier** with the solved cameras as projectors, then bake. 🧠
- **See-through** has no native equivalent: use X-ray (Alt+Z, alpha) or an always-on-top reference viewer such as PureRef at reduced opacity. ↔️
- **Grid images → Image Empties** set to show only in axis-aligned views. **Saved views → cameras bound to timeline markers** (Timeline → Marker → Bind Camera to Markers, Ctrl+B), so scrubbing the timeline steps through the solved photo views. 🧠
- **Brushes and structure:** Move → Grab, Elastic Deform, Snake Hook; Gizmo or Transpose moves → Pose, Boundary, sculpt-mode Transform, or edit-mode proportional editing (Connected Only); Subdivision levels → **Multires** (Subdivide, Unsubdivide, Rebuild Subdivisions, Apply Base, Reshape); DynaMesh → voxel remesh (Ctrl+R) or Dyntopo; Polygroups → Face Sets; ZRemesher → Quad Remesher (paid, by ZRemesher's author) or the free Quadriflow and Instant Meshes; Project All → Shrinkwrap, Multires Reshape, Data Transfer. 🧠
- **Layers → shape keys.** Sculpt mode sculpts into the active key; slider range can exceed 0–1 to exaggerate. Limits: multires detail cannot live per key; remesh and Dyntopo destroy keys. A Geometry Nodes mix of two same-topology objects driven by a painted attribute acts as a masked layer. Native sculpt layers had not shipped as of this writing. ↔️ (time-sensitive)
- **Morph Target → a "Basis" shape key plus edit-mode Blend from Shape** on a selection. There is no native morph brush. 🧠
- **Flip check:** tick the background image's Flip Horizontally and set the camera's X scale to −1 to mirror both (community trick; verify on current versions). 🧠
- **Matcaps:** Workbench MatCap/Studio for form; Eevee or Cycles with lights matched to the photo's catchlights and shadows for likeness judgement. 🧠
- **Bridge:** GoZ-to-Blender works through the open-source **GoB** add-on. ↔️ (compatibility with current ZBrush and Blender releases unverified)
- **Viewport lens trap:** viewport Focal Length defaults to 50 mm, but we believe the view uses a doubled sensor (perspective zoom factor 2, ≈72 mm), so viewport 50 mm ≈ 25 mm full-frame, ≈71° horizontal on a wide window. Set ≈150–200 mm, or sculpt through a matched camera (Lock Camera to View). ↔️ (contested: one tracker report says viewport and camera 50 mm do not match [3], another could not reproduce [4]; no source states the 72 mm doubled sensor)

**Camera physics both programs rely on**

- Perspective depends only on camera-to-subject distance. Focal length and sensor only crop. 🧠 (pinhole geometry)
- Focal length in pixels survives cropping but not resizing; the 35 mm-equivalent survives resizing but not cropping. 🧠
- Front-camera selfies are often saved mirrored, which swaps the sitter's asymmetries. 🧠

## Numbers & reference tables

**Table 1 — Lens to field of view (36 × 24 mm full-frame equivalent)**. Derived: FOV = 2·atan(s / 2f). Population: n/a.

| f (mm, 35 eq.) | Horizontal FOV (°) | Vertical FOV (°) | Diagonal FOV (°) | Badge |
|---|---|---|---|---|
| 14 | 104.3 | 81.2 | 114.2 | 🧠 |
| 26 | 69.4 | 49.6 | 79.5 | 🧠 |
| 35 | 54.4 | 37.8 | 63.4 | 🧠 |
| 50 | 39.6 | 27.0 | 46.8 | 🧠 |
| 85 | 23.9 | 16.1 | 28.6 | 🧠 |
| 105 | 19.5 | 13.0 | 23.3 | 🧠 |
| 135 | 15.2 | 10.2 | 18.2 | 🧠 |
| 200 | 10.3 | 6.9 | 12.3 | 🧠 |

**Table 2 — Camera distance needed to frame a 0.40 m-tall field (head plus margin)**. d = f · 0.40 / sensor side; landscape uses the 24 mm side, portrait the 36 mm side. Derived.

| f (mm, 35 eq.) | Landscape d (m) | Portrait d (m) | Badge |
|---|---|---|---|
| 26 (phone 1×) | 0.43 | 0.29 | 🧠 |
| 50 | 0.83 | 0.56 | 🧠 |
| 85 | 1.42 | 0.94 | 🧠 |
| 135 | 2.25 | 1.50 | 🧠 |

A phone's 1× camera framing a head tightly forces selfie distance. Shoot at 2–3× zoom, or from 1.5 m or more and crop. 🧠

**Table 3 — Magnification of the nose tip relative to the ear plane** (depth gap Δz = 0.10 m assumed; ratio = (d + Δz)/d). Derived.

| Distance to nose tip (m) | 0.3 | 0.5 | 1.0 | 1.5 | 2.0 | 3.0 | 5.0 |
|---|---|---|---|---|---|---|---|
| Ratio | 1.333 | 1.200 | 1.100 | 1.067 | 1.050 | 1.033 | 1.020 |

Badge 🧠. Matches the library's Instagram-sculptors note and the reported "selfie effect": nasal base about 30 % wider at ~30 cm than at ~1.5 m (Ward et al., 2018). ↔️ (figure recalled, to verify)

**Table 4 — Typical phone camera 35 mm-equivalent focal lengths** (2020s flagships; varies by model). ↔️ time-sensitive.

| Module | f eq. (mm) | Badge |
|---|---|---|
| Ultrawide 0.5× | 13–16 | ↔️ |
| Main 1× | 23–28 | ↔️ |
| Front (selfie) | 22–30 | ↔️ |
| 2× (crop or tele) | 46–52 | ↔️ |
| 3× tele | 70–77 | ↔️ |
| 5× periscope | 100–125 | ↔️ |

**Table 5 — Real-scale Blender settings for a life-size head** (head height vertex–menton ≈ 0.21–0.25 m in adults).

| Setting | Suggested value | Reason | Badge |
|---|---|---|---|
| Units | Metric, scale 1.0, display mm | camera distances become physical | 🧠 |
| Viewport clip start | 1–10 mm | avoid clipping when zoomed onto lids | 🧠 |
| Voxel remesh size | 2–3 mm blocking; 0.5–1 mm refining | the default voxel size suits larger objects | 🧠 |
| Multires base | 2–10 k quads; likeness at L0–L2 (≤ ~150 k) | each level ×4 faces | 🧠 |
| Interpupillary distance (scale anchor) | adult mean ≈ 63 mm, SD ≈ 3.5–4 mm | Dodgson (2004) | 🧠 |
| Prescription "PD" | distance PD; near PD ≈ 3 mm less | a real measured scale for the sitter | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Capture or curate** 8–20 photos: front, ¾ both sides, true profiles, 15–20° above and below, from ≥1.5 m or at 2–3× on a phone (Tables 2–3). Keep EXIF, avoid crops (or record the crop box), drop beauty/"portrait" filters (they slim faces), un-mirror selfies (check parting, moles, text). Record one real dimension: prescription PD or a ruler at the face plane.
2. **Scene.** Real scale (Table 5); head at the origin; **move cameras, never the mesh**, the key inversion from ZBrush.
3. **One camera per photo**: resolution = photo pixels, Sensor Fit Horizontal 36 mm, lens = EXIF 35 mm-equivalent (else solve it), shift for crops; background image Depth Front, opacity ≈0.4, Stretch; name cameras after photos and bind them to markers.
4. **Solve pose before sculpting** from 6–10 stable landmarks (endocanthion, exocanthion, subnasale, pronasale, cheilion, tragion, menton), focal length included if unknown. Hand-aligning to a wrong focal length silently warps every later fix.
5. **Block through the cameras** with large-radius Grab or Elastic Deform, symmetry X on: profile silhouette, then front widths, then ¾ jaw and cheek contour. Cycle all cameras every few strokes.
6. **Check every view at every stage**: blink the overlay between 0 and 1 opacity, flip, squint, compare renders in render slots (J). A change that helps one view and hurts two is wrong.
7. **Then asymmetry and secondary forms**; record each experiment as a shape key and dial it; add brow and hairline proxies before judging.
8. **Light-match check**: key light placed from catchlights and shadow directions, render per camera, compare shading, not just contours; cheek and temple plane errors show here.
9. **What goes wrong:** the wide default viewport lens; orthographic tracing of near-field photos (nose too big, ears too far back, face too narrow); principal-point errors from cropped social-media images; photos mixed across ages, weights or expressions (an open jaw adds lower-face height); overfitting a single photo; detailing before the primaries converge; scale mismatch when importing ZBrush meshes (ZBrush's arbitrary units).

## Algorithmic implications

- **Joint, not sequential**: ZBrush whack-a-mole as one least-squares problem. Per view: rotation, translation; focal length shared per device and zoom; global: shape, scale. 🧠
- **Focal-depth ambiguity.** For distant cameras only f/d is well constrained. Parametrise with inverse depth, start from weak perspective, then refine under full perspective with priors on f and d. 🧠
- **Blender export conventions.** lens = f_px · 36 / W with Sensor Fit Horizontal and resolution W × H; shift_x = (W/2 − c_x)/max(W, H); shift_y = (c_y − H/2)/max(W, H) for pixel y pointing down. To convert OpenCV camera axes to Blender, flip the y and z axes. Check the signs with a test render. 🧠
- **Coarse-to-fine stages** that mirror subdivision levels: (1) a similarity transform plus about 10–50 identity parameters; (2) about 50–200 RBF or cage control points; (3) per-vertex offsets with Laplacian regularisation, decreasing weight per stage. Export each stage as a **shape key** (slider max 1.5) to emulate ZBrush Layers, so artists can dial or exaggerate it. 🧠
- **Anti-mean bias.** Morphable-model fits regress toward the average face, and distinctiveness drives recognition (caricature effect). Keep stage 3 weak enough to capture idiosyncrasy, and offer an optional "distinctiveness" factor k on deviation from the template (default 1.0, range 0.9–1.2). ↔️
- **Contours slide.** Jaw and cheek outlines in non-frontal views are occluding contours: fit them to silhouette points, not to fixed vertex IDs. Weight profile-silhouette landmarks (nasion, pronasale, subnasale, pogonion) highest. 🧠
- **Symmetry schedule.** Mirror penalty σ ≈ 0.5 mm in stages 1–2, then 2–3 mm in stage 3. Real faces carry millimetre-scale asymmetry (see the library's facial-asymmetry note). 🧠
- **Per-view expression and jaw parameters**, with priors pulling them to zero, absorb small smiles and jaw drop instead of distorting identity. 🧠
- **Report** per-view reprojection RMS (px and % inter-ocular distance) and 3D residuals (mm); flag views above 2× the median residual (wrong focal length, mirrored image, filter). 🧠

**Suggested priors and defaults**

| Parameter | Prior / default | Badge |
|---|---|---|
| f (35 eq.), EXIF present, uncropped | log-normal, σ_log 0.03 | 🧠 |
| f, physical focal length with guessed sensor | σ_log 0.10 | 🧠 |
| f, no EXIF | median 50 mm, σ_log 0.6 | 🧠 |
| Camera distance | median 1.0 m, σ_log 0.7 (selfie 0.3–0.6 m) | 🧠 |
| Principal point | centre, σ 1 % of max(W, H); 10 % if cropped | 🧠 |
| Radial k1 | 0, σ 0.02 (reject ultrawide) | 🧠 |
| Scale | IPD 63 ± 3.7 mm; measured PD ± 1 mm | 🧠 |
| Landmark noise (σ, % of inter-ocular distance) | inner points 2–3; brows 4–6; jaw contour 5–8 | ↔️ |
| Overlay opacity | 0.4 | 🧠 |

## Disagreements, myths & open questions

- **Orthographic blueprints versus perspective matching.** Classic ZBrush habit (perspective off, front and side grid images) works only with telephoto references. Perspective matching is correct but slower by hand. ↔️
- **"The 85 mm lens flatters" or "focal length changes the face" is a myth.** Distance changes the face; focal length only crops. 🧠
- **Single best photo versus many.** Most teachers warn against a hero photo. Some portraitists argue one well-lit long-lens photo beats a dozen inconsistent ones. ↔️
- **When to drop symmetry**: right after blocking, or only at finishing. ↔️
- **Exaggeration**: pushing distinctive traits helps in 2D caricature research (Rhodes et al., 1987); whether it helps realistic 3D is unsettled. ↔️
- **Base mesh versus morphable-model start** (FaceBuilder, Mesh to MetaHuman): faster, but mean-biased. ↔️
- **Open:** what millimetre tolerance makes a likeness "read"? People detect small feature displacements (Haig, 1984), but no sculpt-scale threshold is established. A working target is about 1–2 mm on eyes, nose and mouth. ↔️
- **Open:** Blender's native sculpt layers and the exact viewport sensor convention need checking against current releases.

## Sources

Numbered sources (added in verification):

1. Maxon, ZBrush Universal Camera: https://www.maxon.net/en/zbrush/features/universal-camera
2. Maxon, ZBrush Shortcuts: https://help.maxon.net/zbr/en-us/Content/Resources/Uploads/ZBrush-Shortcuts.pdf
3. Blender tracker T78320: https://developer.blender.org/T78320
4. Blender tracker T43039: https://developer.blender.org/T43039
5. Review citing Dodgson (2004) mean IPD 63.36 mm: https://pmc.ncbi.nlm.nih.gov/articles/PMC5497600

Related notes in this library: `research/blender/reference-camera-setup.md`, `research/community/instagram-social-sculptors.md`, `research/anatomy/facial-asymmetry.md`, `research/blender/blender-face-addons.md`.

**Further reading (by name, not yet linked)**

- Scott Spencer, *ZBrush Character Creation: Advanced Digital Sculpting* (Sybex, 2008; 2nd ed. 2011)
- Scott Spencer, *ZBrush Digital Sculpting Human Anatomy* (Sybex, 2010)
- Eric Keller, *Introducing ZBrush* (Sybex, several editions)
- Maxon/Pixologic ZBrush documentation: Spotlight, Universal Camera, Layers, Morph Target, See-through
- Blender Manual: Camera (Lens, Sensor, Background Images), Sculpt Mode, Multiresolution modifier, Shape Keys, UV Project modifier, Texture Paint stencil
- Pablo Muñoz Gómez, ZBrushGuides (website and courses)
- Uldis Zarins & Sandis Kondrats, *Anatomy for Sculptors* (2014) and *Anatomy of Facial Expression* (2017)
- Philippe Faraut, *Portrait Sculpting: Anatomy & Expressions in Clay* (2004)
- Leslie G. Farkas, *Anthropometry of the Head and Face* (2nd ed., 1994)
- Neil A. Dodgson, "Variation and extrema of human interpupillary distance" (SPIE, 2004)
- Ward, Ward, Fried & Paskhover, "Nasal distortion in short-distance photographs: the selfie effect" (JAMA Facial Plastic Surgery, 2018)
- Fried, Shechtman, Goldman & Finkelstein, "Perspective-aware manipulation of portrait photos" (SIGGRAPH, 2016)
- Rhodes, Brennan & Carey, "Identification and ratings of caricatures" (Cognitive Psychology, 1987)
- Haig, "The effect of feature displacement on face recognition" (Perception, 1984)
- Hartley & Zisserman, *Multiple View Geometry in Computer Vision* (2nd ed., 2004)

## Verification log (2026-11-20)

- Viewport focal length doubled sensor (about 72 mm; 50 mm viewport about 25 mm full-frame): CONTESTED. Tracker reports disagree on whether a mismatch exists [3][4]; no source gives the 72 mm figure. Badge changed to ↔️.
- Blender camera export conventions (lens, shift_x/shift_y, OpenCV axis flip): UNCONFIRMED. Search found only a loosely related conversion script (https://jsan3386.github.io/avatar/camera.html) giving c_x = w(0.5 - shift_x); no source states the max(W,H) normalisation. Stays 🧠.
- Adult IPD mean about 63 mm, SD 3.5-4 mm, near PD 3 mm less: PARTLY CONFIRMED. A secondary review attributes a 63.36 mm mean to Dodgson [5]; SD and near-PD offset unconfirmed. Row stays 🧠.
- ZBrush Universal Camera and Spotlight shortcuts: Universal Camera with real focal length CONFIRMED [1]; Shift+Z (Spotlight) and Z (dial) CONFIRMED [2] (badge 📄). 4R8/2017 date, storable cameras, and perspective-off default UNCONFIRMED.
