# YouTube: face from photos / likeness in Blender

> YouTube teaches five routes from photos to a real person's head in Blender: a KeenTools FaceBuilder pin fit, modelling over front and side image planes, sculpting by eye from a sphere or base mesh, photogrammetry (Meshroom, RealityCapture/RealityScan, phone apps) followed by cleanup or wrapping, and, since about 2024, AI image-to-3D or vendor bridges (MetaHuman, Character Creator Headshot). The best videos treat any automatic result as a base that still needs a camera-matched sculpting pass. Most popular tutorials skip the step that decides likeness: rebuilding the camera behind each photo (distance, focal length, principal point). Sculpting against orthographic planes or a 50 mm viewport bakes selfie perspective, mirroring and head tilt into the mesh. No harvest or draft existed, so channels are named from expert knowledge only and no video titles are asserted.
>
> Evidence status: 0 ✅ / 0 📄 / 61 🧠 / 20 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Routes as YouTube teaches them**
- **FaceBuilder (KeenTools).** The vendor's own channel is the canonical source; third-party reviews mostly repeat it 🧠. The steps:
  - install the add-on and its downloadable core library;
  - create a head and load photos, one view and camera each;
  - auto-align ("Align face", neural auto-pinning since 2021.1 per `community/blenderartists-forum.md`), then correct pins by dragging, adding or removing them;
  - set focal length per view or per camera group;
  - bake a texture from chosen views, optionally generate ARKit-style blendshapes, then export or sculpt.

  Button names change between releases ↔️.
- **Image-plane modelling.** The classic genre traces a front and a side photo with box or poly-by-poly modelling, or sculpts against Reference/Background image empties. It is accurate only for distant telephoto photos aligned on the same landmarks; with phone photos, front and side never agree 🧠.
- **Sculpt by eye** (sphere or base mesh → voxel-remesh blockout → Dyntopo or Multires → retopology → detail). This is the bulk of Blender "realistic head" content. True likeness of a named person is rarer than generic heads, and few videos match cameras 🧠.
- **Photogrammetry.** Capture a still sitter in rings, reconstruct (Meshroom's default graph: features → matching → StructureFromMotion → DepthMap → Meshing → Texturing), import OBJ, scale, decimate, retopologise or wrap, bake 🧠. Videos focus on objects; heads fail on sitter motion, hair, eyes and shine (`reconstruction/photogrammetry-heads.md`) 🧠.
- **Bridges and AI (2023–2026).** "Photo → MetaHuman → Blender" chains run FaceBuilder or a scan through Mesh to MetaHuman. Character Creator Headshot comes into Blender via the CC/iC Blender Tools add-on. Image-to-3D generators (Hunyuan3D, TRELLIS, Tripo, Meshy, Rodin) are often presented as replacing sculpting. Their outputs are non-metric, mean-biased in profile and untopologised (`community/ai-assisted-sculpting.md`) ↔️.

**Channels worth knowing** (names only; activity, titles and versions are time-sensitive)
- **KeenTools** (official): FaceBuilder, FaceTracker and GeoTracker walkthroughs; the reference for the pin-fit route 🧠.
- **Blender** / **Blender Studio**: Julien Kaspar's Sculpt Mode videos; Blender Studio's free **Human Base Meshes** bundle (2023, believed CC0) is a clean by-eye start 🧠.
- **YanSculpts** (Blender anatomy, heads, portraits), **Grant Abbitt** (beginner head-sculpt and retopology series), **Danny Mac 3D** and **Zacharias Reinhardt** (realistic character heads; moderate confidence) 🧠.
- **FlippedNormals**, **Pablo Muñoz Gómez** (ZBrushGuides): mostly ZBrush, but their likeness method (proportions first, overlay, flip, judge in perspective) transfers directly 🧠.
- **Anatomy for Sculptors** (Uldis Zarins) and **Proko**: skull, muscle and head-plane anatomy 🧠.
- **CG Geek** (Meshroom to Blender) and **Creative Shrimp** (Gleb Alexandrov, Aidy Burrows; photogrammetry course); vendors **Reallusion** (Headshot) and **Unreal Engine** (Mesh to MetaHuman) 🧠.

**Recurring tips the good videos share**
- Proportions and silhouette before features; profile line first (forehead slope, nasion depth, nose projection, lips, chin) 🧠.
- Eyes as separate ~24 mm spheres placed early; lids built over them 🧠.
- Big Grab/Elastic strokes and mask-plus-gizmo moves for proportion, not Draw 🧠.
- Flip, squint, thumbnail, take breaks; check form under one raking light, not a matcap 🧠.
- Keep symmetry for blockout, break it deliberately later; when to break it is debated ↔️.
- Reference from one age and weight period, neutral expression, judged against several photos, not one hero shot; PureRef boards for by-eye work 🧠.

**What most tutorials omit or get wrong**
- Viewport and default camera stay at 50 mm. Photos come from phones with 24–28 mm-equivalent main lenses at arm's length 🧠.
- Render resolution is left at 1920×1080, so a portrait-orientation photo is fitted or stretched into the wrong frame. Cropped photos keep a centred principal point that is no longer true 🧠.
- Selfies are mirrored by front cameras; real asymmetries end up on the wrong side 🧠.
- Head pitch and roll in the photo get sculpted into the face as asymmetry 🧠.
- Voxel sizes demonstrated on Blender's 2 m default sphere are about 10× too coarse for a real-scale head 🧠.
- FaceBuilder follow-alongs over-pin. Pins pulling against each other create lumps, and jawline pins in the front view slide along the silhouette 🧠.
- Speed-sculpt timelapses compress tens of hours into minutes and hide the correction loop; "likeness" side-by-sides are often matched to one flattering photo 🧠.
- Version drift breaks follow-alongs on 5.x: the ≤2.79 UI, pre-2.81 workflows without voxel remesh, pre-4.3 brush panels (brushes are assets since 4.3) and pre-4.2 add-on installs (extensions and core "Images as Planes" arrived in 4.2) 🧠. 5.3 is current and 5.2 is LTS (`blender/blender-version-status-2026.md`) 🧠.

## Numbers & reference tables

**Table 1. Routes compared** (practitioner estimates for an adult head; time is for a competent user and excludes learning)

| Route | Photos | Hands-on time | Output | Likeness ceiling, face region | Main failure | Badge |
|---|---|---|---|---|---|---|
| FaceBuilder pin fit, then sculpt | 3–9 (front, ¾ L/R, profiles) | 0.5–2 h fit; 5–20 h sculpt | fixed KeenTools topology, UVs, texture, ~51 ARKit-style keys | good front/¾; profile only as good as profile pins | over-pinning, wrong focal, expression absorbed | ↔️ |
| Ortho image planes + box/poly modelling | 2 (front, side) | 4–15 h | hand topology | poor unless shot from ≥2 m with tele | perspective mismatch between views | 🧠 |
| Sculpt by eye from sphere or base mesh | 10–50 references | 10–60 h | free topology; needs retopo | high for experts, low for beginners | proportions drift, symmetry, eye depth | ↔️ |
| Photogrammetry + cleanup/wrap | 50–150 | 1–3 h capture/process; 3–10 h cleanup | dense scan → template | best metric shape (mid-face 0.5–2 mm) | motion, hair, eyes, shine | ↔️ |
| AI image-to-3D | 1–4 | minutes | untopologised, non-metric | blockout only | hallucinated profile, averaged features | ↔️ |
| MetaHuman / Headshot bridge | 1–9 or a mesh | 1–3 h | vendor rig topology | as good as the input mesh minus conform drift | vendor drift at nose, lips, lids | ↔️ |

**Table 2. Perspective error that ortho-plane tutorials ignore** (pinhole model; nose tip ~0.10 m in front of the ear plane; magnification ratio = (d+0.10)/d)

| Camera–nose distance d (m) | Nose : ear magnification | Typical source | Usable as shape cue? | Badge |
|---|---|---|---|---|
| 0.3 | 1.33 | arm's-length selfie | no | 🧠 |
| 0.5 | 1.20 | close phone shot | only with a solved camera | 🧠 |
| 1.0 | 1.10 | casual portrait | yes, with a solved camera | 🧠 |
| 2.0 | 1.05 | tele portrait | yes; near-ortho tolerable | 🧠 |
| 3.0 | 1.033 | long tele | ortho planes acceptable | 🧠 |

**Table 3. Blender defaults versus likeness settings** (defaults as recalled; verify per version)

| Setting | Default | For likeness work | Badge |
|---|---|---|---|
| Viewport focal length | 50 mm | 85–100 mm to sculpt; judge only through solved cameras | 🧠 |
| Camera lens / sensor | 50 mm / 36 mm, Sensor Fit Auto | from EXIF or the solver; Auto fit uses the larger image side | 🧠 |
| Render resolution | 1920×1080 | exactly the photo's pixels, original uncropped file | 🧠 |
| Camera background image | opacity 0.5 | 0.3–0.5, Depth Front for overlay, Frame Method Stretch | 🧠 |
| View clip start | 0.01 m (camera clip start 0.1 m) | 0.001 m at real scale | 🧠 |
| Brush Radius Unit | View (pixels) | Scene for measured strokes | 🧠 |
| Voxel remesh size | ~0.1 m on new meshes (uncertain) | 3–5 mm blockout, 1.5–2 mm primaries | ↔️ |
| Lock Camera to View | off | keep off; lock camera transforms | 🧠 |
| Mesh symmetry X | often on (template-dependent) | on until primaries agree in all cameras | ↔️ |

**Table 4. Photo sets the better tutorials ask for**

| Route | Views | Capture settings | Badge |
|---|---|---|---|
| FaceBuilder | front, ¾ L/R, both profiles, optional slight high/low | ≥1 m, 2–3× phone tele or 85–135 mm-equivalent, same zoom for all so views share a camera group, neutral face, hair off ears and forehead, no glasses | 🧠 |
| Photogrammetry | 3 rings (about −20°, 0°, +30–45°), 24–36 shots each, 60–80% overlap | diffuse light, f/8–f/11, shutter ≥1/160 s or flash, low ISO, sitter still, eyes on a fixed point, ring done in ≤20–30 s | 🧠 |
| Sculpt by eye | 8–16 yaw stations plus above/below, plus candid photos for character | as FaceBuilder; add a ruler or a measured IPD for scale | 🧠 |

**Table 5. FaceBuilder pin plan** (6–12 confident pins per view; delete rather than add when pins fight)

| View | Pin | Badge |
|---|---|---|
| Front | inner/outer canthi, nasal tip, alar bases, mouth corners, chin (pogonion); no jaw-contour pins | 🧠 |
| ¾ | outer canthus, cheekbone contour, jaw angle (gonion), ear root, nasal tip | 🧠 |
| Profile | glabella, nasion, pronasale, subnasale, both lips, pogonion, menton, tragus, ear top/bottom | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Pick the route by sitter availability:** able to hold still ~1 min → photogrammetry, then wrap a template; available 10 minutes → the Table 4 FaceBuilder-style set; existing photos only → pin or landmark fit, then sculpt, accepting weak profile depth unless a true profile exists 🧠.
2. **Audit every photo first:** original files with EXIF and orientation applied; front-camera shots un-mirrored (check a parting, text or mole); arm's-length selfies rejected as shape cues (Table 2); expression, glasses and hair occlusion noted per view 🧠.
3. **Rebuild cameras instead of placing planes:** one camera per photo (lens from EXIF or the solver), render resolution equal to the photo's pixels, the photo as that camera's Background Image (Depth Front, opacity 0.3–0.5), transforms locked, cameras bound to markers so one key steps through them. fSpy rarely helps for bare portraits because it needs scene vanishing lines (`blender/reference-camera-setup.md`) 🧠.
4. **FaceBuilder specifics.**
   - Group views shot with one lens and zoom; estimate focal only when EXIF is missing.
   - Pin the front first, then profiles (Table 5). Enable expression handling only for non-neutral photos.
   - Texture from front and ¾ views; profiles smear the cheeks.
   - Duplicate the result before sculpting. Dyntopo or remesh destroys UVs and blendshapes, so sculpt on Multires 🧠.
   - Read the EULA before reusing the exported head as a product base ↔️.
5. **Sculpt pass order.** Profile silhouette → front widths (zygoma, gonion, temples) → ¾ (cheek turn, orbit depth) → eyes and lids → nose (dorsum, tip, alae) → mouth barrel and lips → ears → hairline. Fix the biggest error at the lowest Multires level, then re-check every camera 🧠.
6. **Checks:** blink (toggle background Depth or opacity); flip render and photo together; thumbnail at 100–150 px face height; one photo held out; light matched to each photo's key; a viewer who knows the sitter 🧠.
7. **Typical failures:** eyes too big, open or proud; skull back too short; neck thin and vertical; ears high; nose wide from selfie perspective; smile absorbed as identity; hair read as cranium; ×100 scale errors between MetaHuman/CC (cm) and Blender (m) 🧠.

## Algorithmic implications

- **Productise the vendor UX tutorials made familiar** 🧠: auto-align, then user pins as `Pin{view, xy_px, surface(tri, bary), σ, source}`. User pins σ ≈ 0.75% IOD; auto pins 1.5% (corners), 2.5% (lid and lip contours), 4% (face oval); Huber δ = 2σ; rigidity slider r ∈ [0,1] → λ_shape = 10^(2r−1). These match `reconstruction/commercial-head-tools.md`.
- **Over-pinning is a diagnostic, not a user error** 🧠: report per-pin residuals worst first, flag pins beyond 3σ after convergence as "conflicting", cap auto-suggested pins near 12 per view.
- **Contour pins slide.** Jaw, cheek and ear-outline pins in non-profile views become silhouette constraints re-associated to the nearest occluding-contour vertex each iteration, never fixed vertex IDs 🧠.
- **Photo audit gate**, one check per tutorial mistake 🧠:
  - read EXIF focal (35 mm-equivalent, or focal plus sensor width) and orientation;
  - detect front-camera mirroring from the EXIF lens model, else ask;
  - estimate d ≈ f_px·63 mm / IPD_px; warn below 1.0 m; below 0.6 m use the photo only for texture and 2D cues;
  - flag crops (aspect unlike the camera's native one) so the principal point is freed or the original requested.
- **Camera export contract** 🧠: Sensor Fit AUTO; lens = f_px·36 / max(W,H); shift_x = (W/2 − c_x)/max(W,H), shift_y = (c_y − H/2)/max(W,H); render W×H, pixel aspect 1; unit-test the signs by reprojecting a known landmark.
- **Priors and schedule** (as in sibling notes) 🧠:
  - scale: IPD ~ N(63, 3.5²) mm or iris ~ N(11.7, 0.5²) mm, overridden by a measurement (σ ≈ 1 mm);
  - focal: EXIF-seeded, log-σ ≈ 0.03; without EXIF 50 mm-equivalent, log-σ ≈ 0.5, freed only when ≥2 views or a profile constrain it;
  - symmetry σ ≈ 1 mm in global and low-frequency stages, 2–3 mm per-vertex;
  - similarity → low-frequency modes (length scale ≥30–40 mm) → per-vertex offsets capped near 5 mm unless ≥2 views agree.
- **Imported meshes are observations, not truth** (point-to-plane σ): photogrammetry 0.5–1 mm with eyes, lashes, brows and hair masked or σ ×5; multi-view pin fits such as FaceBuilder 1–1.5 mm; AI image-to-3D 3–5 mm with zero profile weight unless a profile photo confirms it ↔️.
- **Sculpt-ready output** 🧠: fixed quad topology with stable vertex order and UVs; the fit as a shape key or Multires base; separate 24 mm eye spheres; one locked camera per photo; checker operators (blink, flip, thumbnail, held-out view, next camera); never remesh inside the add-on.
- **Follow-along friendliness** 🧠: brushes via the 4.3+ asset API; probe features, not versions; CI on 4.5 LTS, 5.2 LTS and 5.3; a guided "tutorial mode" mirroring the best YouTube workflow with every check automated.

## Disagreements, myths & open questions

- **"Front and side planes give accurate proportions."** True only for distant tele photos (Table 2) 🧠.
- **"FaceBuilder / AI gives you the likeness."** Each gives a base bounded by its shape space. Every serious tutorial ends with sculpting ↔️.
- **"More pins, more accuracy."** Contradicted by pin-conflict lumps; fewer confident pins plus more views win 🧠.
- **Phone photogrammetry of people.** Some creators show good results; others report mush from sitter motion. Success depends on ring speed and stillness ↔️.
- **Sphere vs base mesh**, **Dyntopo vs voxel remesh plus Multires**, and **when to drop symmetry**: schools disagree ↔️.
- **"Blender can't sculpt at ZBrush resolution."** Partly true: Blender stays fluid at a few million faces, ZBrush far beyond. Likeness lives in low frequencies, so it rarely matters ↔️.
- **"Push it a little" (caricature).** Some likeness teachers exaggerate distinctive traits slightly. The recognition advantage is robust in 2D and unproven for realistic 3D ↔️.
- **Pricing and terms.**
  - FaceBuilder: paid subscription with a trial (a forum user mentions 30 days); seat price roughly 100–300 USD per year as recalled; Blender 5.x support not checked ↔️.
  - RealityCapture: free for small studios since 2024 and since renamed RealityScan, per moderate-confidence recollection ↔️.
  - Meshroom: free (MPL-2.0); historically needs an NVIDIA CUDA GPU for depth maps ↔️.
- **Open questions:**
  - No transcript-level evidence has been gathered.
  - Which channels are active on 5.x?
  - Which tutorials show camera matching for portraits?
  - Has any creator measured mm error against a scan?
  - What does the current FaceBuilder EULA say about exported meshes?

## Sources

No harvest or draft existed, so no URLs are cited. Related notes: `blender/reference-camera-setup.md`, `blender/sculpting-likeness-workflow.md`, `blender/blender-face-addons.md`, `reconstruction/commercial-head-tools.md`, `reconstruction/photogrammetry-heads.md`, `community/blenderartists-forum.md`, `community/reddit-face-from-photos.md`, `community/likeness-mistakes.md`.

**Further reading (by name, not yet linked)**
- KeenTools FaceBuilder for Blender documentation and the KeenTools YouTube channel
- Blender Manual: Sculpt Mode (Multiresolution, Dynamic Topology, Voxel Remesh, Brushes); Cameras and Background Images; Image empties
- Blender Studio, Human Base Meshes asset bundle (2023)
- Julien Kaspar, Blender Studio sculpting training
- YouTube channels: YanSculpts; Grant Abbitt; Danny Mac 3D; Zacharias Reinhardt; FlippedNormals; Pablo Muñoz Gómez (ZBrushGuides); Anatomy for Sculptors; Proko; CG Geek; Creative Shrimp; Reallusion; Unreal Engine
- AliceVision/Meshroom documentation; fSpy documentation and the fSpy-Blender importer
- CC/iC Blender Tools add-on (Character Creator to Blender); Epic Games, Mesh to MetaHuman documentation
- Leslie G. Farkas, *Anthropometry of the Head and Face* (2nd ed., 1994)
- Ward et al., "Nasal distortion in short-distance photographs: the selfie effect", JAMA Facial Plastic Surgery (2018)
- Hartley & Zisserman, *Multiple View Geometry in Computer Vision* (2nd ed., 2004)
- Uldis Zarins & Sandis Kondrats, *Anatomy for Sculptors* (2014)
- John Asaro, "Planes of the Head" model
- Rhodes, Brennan & Carey, "Identification and ratings of caricatures", Cognitive Psychology (1987)
