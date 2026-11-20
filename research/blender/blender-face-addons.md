# Blender add-ons for heads and faces

> No Blender add-on in this evidence set fits a specific person's identity to photos with open code, open data and a commercial-safe licence; that is the gap this project fills. The ecosystem has three layers: landmark capture (MediaPipe: 468 points, 478 refined), parametric base humans (MPFB2/MakeHuman is the only actively released option with GPL-3-or-later code and CC0/CC-BY assets; FLAME is research-licensed; MB-Lab, CharMorph and Human Generator are legacy, niche or proprietary-content), and expression/rig tools converging on ARKit 52 (Faceit, CaptureForge, Face Shape Key Rig, Auto-Rig Pro, Rigify). KeenTools FaceBuilder is the closed-core, commercial incumbent for photo→head. Recommended: fit identity on a frozen MPFB2 topology, store it as one neutral shape key or MPFB target, add detail with Multires, and leave expressions to the ARKit layer; version rows are perishable (5.2 LTS and 5.3 are current per `blender/blender-version-status-2026.md`).
Evidence status: 4 ✅ / 36 📄 / 49 🧠 / 4 ↔️ — verified 2026-11-20 (see logs, pass 2 added FaceBuilder pricing/trial); remaining 🧠 items are still unverified.

## Key facts

### Landmark capture (MediaPipe)
- Face Mesh estimates **468 3D landmarks** per face in real time [3][2] ✅
- With refinement on, output is **478**: an attention-mesh stage refines eyes and lips and adds iris points [2] 📄. The 10 extra points are two 5-point iris sets (centre + 4 rim), indices 468–472 and 473–477; which set is "left" is described inconsistently across sources 🧠
- The MediaPipe Tasks **Face Landmarker** (successor to the legacy solution) returns 478 landmarks plus optional **52 blendshape scores** with ARKit-style names (to my knowledge including `_neutral` and omitting `tongueOut`) and a 4×4 facial transformation matrix 🧠
- x, y are normalised by image width/height; z is depth relative to the head centre in roughly x's scale (smaller = nearer). z is **not metric** and is pulled strongly toward the mean face 🧠 (confirm wording in [3])
- The "face geometry" module aligns a fixed **468-vertex canonical face model** (centimetres) by Procrustes, so its "metric" scale is the canonical face's, not the subject's 🧠
- MediaPipe code is Apache-2.0 🧠; model-card terms not captured.
- No add-on named "FaceMesh Capture" was found. The nearest is `mozi1924/mediapipe-facecap-for-blender`: an external **transmitter** runs MediaPipe, a Blender **receiver** add-on ingests the stream [1] 📄. Licence, Blender range and raw-landmark access uncaptured. More projects sit under the GitHub topic [4] 📄
- **BlendArMocap** (MediaPipe face/hands/pose → Rigify, GPL) was the best-known Blender MediaPipe add-on; to my knowledge development stopped, so expect breakage on 4.2+/5.x 🧠

### Expression and rig layer
- **Faceit** (paid, Superhive) semi-automatically generates facial shape keys with ARKit-style, Audio2Face, tongue and phoneme presets; a **bake** converts modifier, pose and sculpt deformation into shape keys [5] 📄. Listing states **Blender 3.0–5.2** [5] 📄; price not captured.
- Faceit workflow 🧠: register parts (face, eyes, teeth, tongue) → fit a landmark guide (front, then side) → generate a Rigify-derived face rig → bind with automatic (bone-heat) weights → pose expressions → bake. It also imports ARKit capture recordings (Live Link Face-style CSV).
- **Face Shape Key Rig** (free, GPL, Blender Extensions): viewport sliders and 2D pads driving **existing** shape keys through bones/drivers; iFacialMocap and audio lipsync [6][7] 📄. Requires **Blender 5.2+** [7] 📄. It creates no shapes; Faceit does [6][5] 📄
- **CaptureForge** (GPL-3.0) converts a posed face rig to the **ARKit 52** blendshapes and drives them from video/webcam without an iPhone; lists a quality inspector and auto face rig [8] 📄
- **Auto-Rig Pro** (paid): marker-based "Smart" body placement, a bone-based face rig (jaw, lips, eyelids, tongue, teeth), FBX presets for Unity/Unreal and a retargeting module. Not, to my knowledge, an ARKit-key generator; 5.x status unverified 🧠
- **Rigify** ships with Blender; most free face rigs derive from its face sub-rigs 🧠
- Unexamined leads: wk FaceRig [10] 📄 and Faceit notes in TalkingHead [9] 📄

### Parametric base humans
- **MPFB2** code is **GPL-3.0-or-later** [11][14] ✅
- Assets: "CC0 or CC-BY" per the Extensions listing [11]; MakeHuman Community licence page: base mesh, targets, proxies and system assets are CC0 (since the 2020 change), while asset packs vary, some CC0, some CC-BY (e.g. Bodyparts packs) [18][19] 📄; a third-party note also says CC0 1.0 [16]
- Latest **2.0.18**, **Blender 4.2 LTS+** [11][12] 📄 (snippets; the 10 Oct 2026 date is single-snippet). The MakeHuman Community page says 2.0.18 has been released [18], while one search saw the Extensions listing only up to 2.0.16 ↔️ (2.0.16–2.0.18, unresolved). hm08 vertex counts unconfirmed. Preferred install is the Extensions platform [13] 📄; MPFB1 is deprecated [15] 📄
- MPFB2 internals 🧠: base mesh `hm08` (≈13.4k body vertices, ≈19.2k with helper geometry for clothes fitting, joints and hair, hidden by a Mask modifier); **macro** sliders (gender, age, muscle, weight, height, proportions, population blends) interpolate stored targets; hundreds of local face targets named `region-feature-decr|incr`; **MakeTarget** saves a sculpted shape key as a `.target`; import scale option (metres default); rigs include default, game-engine and a Rigify meta-rig.
- **FLAME** (Li et al. 2017) 🧠: 5,023 vertices, 9,976 triangles, eyeballs included, no mouth interior; FLAME 2020 has 300 shape, 100 expression and 15 pose parameters (global, neck, jaw, two eyes); shape space learnt from ~3.8k CAESAR scans. The MPI **FLAME Blender add-on** loads it as shape keys plus armature with sliders and pose correctives; model files need a registered download.
- FLAME licence: FLAME 2017/2019/2020/2023 are non-commercial research only; commercial use needs a separate licence from the institute [17] 📄. A **FLAME 2023 Open** variant exists, released under CC-BY-4.0 and licensed for commercial use with attribution; only that version is open [17] 📄 (corrected in verification). Treat all other FLAME versions as non-commercial.
- **MB-Lab** 🧠: community continuation of ManuelbastioniLAB (discontinued 2018); AGPL-3.0 code; generated characters under a different licence (possibly CC-BY 4.0) ↔️; releases I know target 2.8x–3.x, so 4.2+/5.x is unknown. Its centimetre body-measurement sliders are a useful UI precedent.
- **CharMorph** 🧠: GPL-3 MB-Lab-inspired rewrite; characters (e.g. "Antonia") ship in a separate data repo; Rigify rigging and asset fitting; maintenance, 5.x status and per-character data licences unknown.
- **Human Generator** 🧠: paid; proprietary realistic content library, one-click expressions and face rig; the GPL-code/proprietary-asset split typical of paid add-ons; price and 5.x status unverified.
- **ICT-FaceKit** (USC ICT, Li et al. 2020) 🧠: morphable head with ~100 identity components and ~53 ARKit-style expression shapes under the MIT licence; the most commercial-friendly FLAME alternative I know of. Verify licence and counts.

### Photo→head: FaceBuilder and alternatives
- **KeenTools FaceBuilder** subscription with a 15-day no-restriction trial; Freelancer $19.99/month monthly or $15.99/month billed yearly, Studio $699/year, commercial use allowed; separate licence per platform [21] 📄. Rest of this bullet 🧠 (GPL front-end/closed core, ARKit blendshapes and EULA terms on exported meshes not found in the pass-2 results): pin-based fit of a fixed KeenTools head topology to several photos, texture projection, ARKit-compatible blendshapes; GPL Python front-end that downloads a proprietary core library; subscription with trial. The library note `community/blenderartists-forum.md` records (single forum source) neural auto-pinning since 2021.1, per-photo focal estimation and expression-tolerant fitting, with manual pin fixes still needed. Siblings: FaceTracker and GeoTracker for video.
- Alternatives 🧠: (a) photogrammetry (Meshroom/AliceVision MPL-2.0, COLMAP BSD, RealityScan) then wrap a template; (b) FLAME regressors outside Blender (see `reconstruction/single-image-regression.md`, `reconstruction/multi-view-fitting.md`), mostly non-commercial; (c) Character Creator Headshot + CC Blender Tools; (d) MetaHuman (Mesh to MetaHuman), whose 2025 licence change reportedly allows use outside Unreal; (e) fSpy (GPL) + its Blender importer for single-image camera calibration; (f) native modifiers: Shrinkwrap, Surface Deform, Laplacian Deform (anchor-constrained), Data Transfer.
- **Extensions platform** (4.2+) 🧠: `blender_manifest.toml`; GPL-compatible code licence (`SPDX:GPL-3.0-or-later`); bundled platform-specific wheels; declared `permissions` (`files`, `network`, `clipboard`, `camera`, `microphone`) with reasons; legacy add-ons still install from disk.

## Numbers & reference tables

**Table 1 — Landmark and expression output counts** (model specifications, no population)

| Item | Count | Units | Status | Source |
|---|---|---|---|---|
| MediaPipe Face Mesh, default | 468 | landmarks | ✅ | [3][2] |
| Refined landmarks on | 478 (+10) | landmarks | 📄 | [2] |
| Iris sets | 2 × 5 (idx 468–477) | landmarks | 🧠 | — |
| Face Landmarker blendshapes | 52 (incl. `_neutral`, no `tongueOut`) | scores 0–1 | 🧠 | — |
| ARKit blendshapes | 52 | shapes | 📄 | [8] |
| MediaPipe canonical face model | 468 | vertices, cm | 🧠 | — |

**Table 2 — Template topologies a fitter might target**

| Template | Vertices | Identity params | Expression / pose | Data licence | Status |
|---|---|---|---|---|---|
| FLAME 2020 | 5,023 (9,976 tris) | 300 PCA | 100 PCA + 15 pose | research NC; FLAME 2023 Open is CC-BY-4.0 [17] | 📄 (licence) |
| MakeHuman hm08 (MPFB2) | ≈13.4k body / ≈19.2k with helpers (quads) | macros + local targets | via rig / face poses | CC0 base, packs CC0/CC-BY [18][19] | 🧠 (counts) / 📄 (licence) |
| Basel Face Model 2009 | 53,490 | 199 PCA | none | research licence | 🧠 |
| ICT-FaceKit | not recalled | ~100 | ~53 shapes | MIT | 🧠 |
| MediaPipe canonical | 468 | none | none | Apache-2.0 | 🧠 |

**Table 3 — Stated Blender support** (Blender release numbers)

| Add-on | Version | Min | Max stated | Status | Source |
|---|---|---|---|---|---|
| Faceit | not captured | 3.0 | 5.2 | 📄 | [5] |
| Face Shape Key Rig | not captured | 5.2 | open | 📄 | [7] |
| MPFB2 | 2.0.18 | 4.2 LTS | open | 📄 snippet | [11][12] |
| CaptureForge, mediapipe-facecap | not captured | — | — | — | [8][1] |
| MB-Lab, CharMorph, Human Generator, ARP, FLAME add-on, FaceBuilder, BlendArMocap | unverified | — | — | 🧠 | — |

Faceit's 5.2 ceiling excludes 5.3; FSKR's 5.2 floor excludes 4.5 LTS. Only 5.2 LTS satisfies all three sourced ranges.

**Table 4 — Licence, cost, role**

| Tool | Code | Data/assets | Cost | Role | Status |
|---|---|---|---|---|---|
| MPFB2 | GPL-3.0+ | CC0 base; packs CC0 / CC-BY | free | parametric base | ✅ code, 📄 assets [11][14][18][19] |
| Faceit | not captured | — | paid | shape-key generator + bake | 📄 [5] |
| Face Shape Key Rig | GPL | — | free | controller for existing keys | 📄 [6][7] |
| CaptureForge | GPL-3.0 | — | not captured | rig → ARKit 52, video drive | 📄 [8] |
| mediapipe-facecap | not captured | MediaPipe models | not captured | live capture | 📄 [1] |
| FLAME add-on | add-on code open | FLAME NC research; 2023 Open CC-BY-4.0 [17] | free (research) | PCA head | 🧠 code / 📄 data licence |
| MB-Lab | AGPL-3.0 | separate licence ↔️ | free | parametric body | 🧠 |
| CharMorph | GPL-3 | per character | free | parametric body | 🧠 |
| Human Generator | GPL (presumed) | proprietary | paid | realistic humans | 🧠 |
| Auto-Rig Pro | GPL (presumed) | — | paid | body + bone face rig | 🧠 |
| FaceBuilder | GPL front + closed core | EULA | subscription, 15-day trial [21] | photo→head | 🧠 code/EULA, 📄 cost [21] |
| ICT-FaceKit | MIT | MIT | free | PCA head + ARKit-style shapes | 🧠 |

**Table 5 — ARKit 52 by region** 🧠 (total 52 matches [8] 📄)

| Region | Count | Members |
|---|---|---|
| Eyes | 14 | blink, lookDown, lookIn, lookOut, lookUp, squint, wide × L/R |
| Jaw | 4 | jawOpen, jawForward, jawLeft, jawRight |
| Mouth | 23 | close, funnel, pucker, left, right, rollUpper/Lower, shrugUpper/Lower; smile, frown, dimple, stretch, press, lowerDown, upperUp × L/R |
| Brows | 5 | browDown L/R, browInnerUp, browOuterUp L/R |
| Cheeks | 3 | cheekPuff, cheekSquint L/R |
| Nose | 2 | noseSneer L/R |
| Tongue | 1 | tongueOut |

**Table 6 — Suggested solver defaults** (design choices 🧠, not measurements; IOD = inter-ocular distance in the image)

| Quantity | Default | Notes |
|---|---|---|
| Anchor landmarks (eye/mouth corners, nose tip, subnasale) | σ = 1.5% IOD | fixed correspondence |
| Eyelid/lip contour points | σ = 2.5% IOD | slide along the contour |
| Face-oval/jaw points | σ = 4% IOD | silhouette residual, re-associate each iteration |
| Iris centre | σ = 1% IOD | 478 mode only |
| MediaPipe z | weight 0 (≥2 views); ≤0.1·w_xy (1 view) | relative, mean-face-biased |
| Horizontal iris diameter scale prior | 11.7 ± 0.5 mm | figure used by MediaPipe Iris [20] 📄 |
| Interpupillary distance prior, adults | mean ≈ 63 mm, σ ≈ 3.5 mm | user-measured value overrides (σ 1 mm) |
| EXIF focal → pixels | f_px = f35 · √(W²+H²) / 43.27 | 43.27 mm = 35 mm-frame diagonal |

## Applying this to photo→3D face sculpting in Blender

1. **Choose the stack by licence first.** Shippable: MediaPipe (out of process) → own numpy fitter → MPFB2 base → Multires detail → expressions via Faceit (user-bought), CaptureForge or Face Shape Key Rig → Rigify or Auto-Rig Pro. Research-only: FLAME add-on and FLAME regressors (except FLAME 2023 Open, CC-BY-4.0 [17]); outputs inherit non-commercial terms. Read FaceBuilder's EULA before reusing its exported mesh as a base.
2. **Prepare the MPFB2 base.** New human, metres, macros set from known age/height/sex; no proxy; keep helpers (masked). Record vertex count and an index-order hash and assert them at every write-back. Fitting a proxy, or deleting helpers, breaks targets and clothes fitting 🧠.
3. **Landmarks.** Run MediaPipe outside Blender, as the transmitter/receiver split in [1] does; use 478 mode and check the count per image [2][3]. Un-mirror front-camera selfies (otherwise L/R swap), apply EXIF orientation, keep native resolution.
4. **Cameras.** Seed focal length from EXIF (Table 6). Phone main lenses (~24–28 mm equivalent) at arm's length enlarge the nose and hide the ears; prefer 2–3× tele at ≥1 m (see `blender/reference-camera-setup.md`). Fix the principal point at centre; allow only k1 for wide lenses.
5. **Write the result non-destructively**: one neutral shape key (e.g. `ID_fit_v1`), optionally exported through MakeTarget as an MPFB `.target` so clothes, proxies and rigs follow.
6. **Sculpt.** Add Multires only after identity keys are final: shape keys live at base level and Multires detail does not propagate into them 🧠. Never Remesh, Dyntopo, Decimate or merge-Symmetrize the delivery mesh, because shape keys need identical vertex count and order. Bake normal/displacement maps from the top level.
7. **Expressions.** Before Faceit or Auto-Rig Pro binding: apply rotation and scale, face −Y, separate eyes/teeth/tongue, remove interior or duplicate faces; bone-heat binding fails on non-manifold or self-intersecting geometry 🧠. Then generate/bake the ARKit set [5]. On Blender >5.2, confirm Faceit support first [5].
8. **Validate in Blender.** One camera per photo with its background image; overlay reprojected landmarks; report reprojection RMS in px and %IOD; compare model IPD with a measured IPD; inspect the profile silhouette (nasal projection, chin, forehead slope), where single-view fits fail most.

**What goes wrong:** controller mistaken for generator [6]; licence contamination (FLAME, BFM, MetaHuman, Human Generator assets); MediaPipe jaw-line points biased toward the mean face; unit mismatches (MediaPipe cm, FLAME m, MakeHuman natively decimetres) 🧠; vertex order silently changed by Join, Separate, Sort Elements or applying Mirror; Blender 5.0 `mathutils` buffers are float32 and non-contiguous, so copy explicitly into float64 numpy arrays (library version note, unconfirmed).

## Algorithmic implications

- **Input schema:** `LandmarkSet{scheme ∈ {mp468, mp478}, xy_px[N], z_rel[N], image_wh, mirrored, exif_rotation}`. Branch on N, not a flag [3][2]; treat 468–477 as optional iris observations 🧠.
- **Landmark classes with per-class σ** (Table 6) and a Huber loss (δ = 2σ). Drop a point from a view beyond 4σ after the first solve. Treat face-oval points as silhouette constraints (nearest occluding-contour vertex), never fixed vertex IDs, because they slide with yaw 🧠.
- **Scale:** combine the iris-diameter prior (11.7 ± 0.5 mm [20]) and the IPD prior (63 ± 3.5 mm); a user-measured IPD or ruler in frame overrides with σ ≈ 1 mm. Never take scale from MediaPipe's canonical model 🧠.
- **Shape priors:** MPFB macros ∈ [0,1] with a box constraint, Gaussian toward user-supplied age/height (σ ≈ 0.15); local face targets ∈ [−1,1], N(0, 0.5²) plus box; FLAME β ~ N(0,1) using the first 50–100 components. Fit a small expression basis (σ ≈ 0.3) only to absorb expression in the photos, then discard it 🧠.
- **Residual warp:** after the parametric fit, solve per-vertex offsets with Laplacian/ARAP regularisation, λ annealed high→low (e.g. 10→1); cap offsets near 5 mm unless several views agree; soft symmetry prior with σ ≈ 1–2 mm (see `anatomy/facial-asymmetry.md`), never hard mirroring 🧠.
- **Correspondence tables** (landmark → vertex or barycentric point) versioned per base and base version (MPFB2 2.0.18 `hm08` [12]); validate vertex count on load.
- **Topology invariance:** the solver moves vertices only; assert count and order before write-back.
- **Licence as data:** each prior, base and asset carries `{licence, attribution, commercial_ok}`; export refuses unknown or `commercial_ok=false` items, FLAME 2017–2023 included by default (FLAME 2023 Open is CC-BY-4.0 and may be allowed with attribution [17]).
- **Outputs:** neutral identity mesh, optional ARKit-52-named keys (Table 5) so Faceit, CaptureForge and FSKR can consume them [5][8][6], an MPFB `.target`, and OBJ with stable vertex order.
- **Packaging:** extension with GPL-3.0-or-later code, matching MPFB2 [14] and CaptureForge [8]; `blender_version_min = "4.2.0"` like MPFB2 [11]; CI-test 4.5 LTS, 5.2 LTS and current 5.x; gate 5.2+ features (FSKR interop [7]); MediaPipe out of process or as an optional wheel; declare `camera` permission only for webcam capture 🧠.

## Disagreements, myths & open questions

- **468 vs 478:** both correct; the count depends on refinement [3][2].
- **MPFB/MakeHuman asset licence:** resolved: base mesh, targets and system assets CC0; asset packs CC0 or CC-BY, so check each pack [18][19] 📄.
- **"Face Shape Key Rig replaces Faceit":** partly; it controls but does not create keys [6][5].
- **Myth: MediaPipe gives a 3D head.** z is relative and mean-face-biased; metric depth needs multi-view geometry or scale priors 🧠.
- **"FLAME is free":** free for research only, except FLAME 2023 Open (CC-BY-4.0, commercial use allowed) [17] 📄 (corrected in verification).
- **"Every bpy add-on must be GPL"** ↔️: Blender Foundation's position, legally untested; paid add-ons split GPL code from proprietary assets or binaries 🧠.
- **Myth: ARKit 52 = FACS.** ARKit shapes are FACS-inspired, not action units; the mapping is many-to-many (see `anatomy/facs-expressions.md`) 🧠.
- **Myth: FaceBuilder output is the likeness.** It is a pinned fit of a low-dimensional head; forum reports say pins need manual correction 🧠.
- **Open:** FaceBuilder EULA terms on exported meshes and current pricing; MediaPipe z convention and iris L/R indexing in [3]; licence and raw-landmark access of [1]; Faceit beyond 5.2 [5]; MB-Lab and CharMorph maintenance on 4.2+/5.x; ICT-FaceKit and MetaHuman licence terms; no accuracy benchmark (mm error) exists here for any Blender add-on's photo fit.

## Sources

[1] mozi1924/mediapipe-facecap-for-blender — https://github.com/mozi1924/mediapipe-facecap-for-blender — repo — n.d.
[2] MediaPipe Face Mesh: All 478 Landmark Points (DEV Community) — https://dev.to/metsander/mediapipe-face-mesh-all-478-landmark-points-5ec8 — blog — n.d.
[3] MediaPipe Face Mesh (legacy docs mirror) — https://mediapipe.readthedocs.io/en/latest/solutions/face_mesh.html — official docs — n.d.
[4] GitHub topic: mediapipe-facemesh — https://github.com/topics/mediapipe-facemesh — index — n.d.
[5] Faceit: Facial Expressions and Performance Capture (Superhive) — https://superhivemarket.com/products/faceit — commercial listing — n.d.
[6] Face Shape Key Rig (Blender Extensions) — https://extensions.blender.org/add-ons/face-shapekey-rig/ — official listing — n.d.
[7] Fragid/face-shapekey-rig — https://github.com/Fragid/face-shapekey-rig — repo — n.d.
[8] H0wZy/captureforge — https://github.com/H0wZy/captureforge — repo — n.d.
[9] TalkingHead blender/Faceit/FACEIT.md — https://github.com/met4citizen/TalkingHead/blob/main/blender/Faceit/FACEIT.md — repo doc — n.d.
[10] wk FaceRig (Superhive) — https://superhivemarket.com/products/wk-facerig — commercial listing — n.d.
[11] MPFB, Blender Extensions listing — https://extensions.blender.org/add-ons/mpfb/ — official listing — n.d.
[12] MPFB version history, Blender Extensions — https://extensions.blender.org/add-ons/mpfb/versions/ — official listing — 2026 (single snippet)
[13] makehumancommunity/mpfb2 — https://github.com/makehumancommunity/mpfb2 — repo — n.d.
[14] mpfb2 LICENSE.CODE.md — https://github.com/makehumancommunity/mpfb2/blob/master/LICENSE.CODE.md — licence file — n.d.
[15] makehuman-plugin-for-blender (MPFB1, deprecated) — https://github.com/makehumancommunity/makehuman-plugin-for-blender — repo — n.d.
[16] kblood/CharacterCreator LICENSE-NOTES.md — https://github.com/kblood/CharacterCreator/blob/master/LICENSE-NOTES.md — third-party notes — n.d.
[17] FLAME model license — https://flame.is.tue.mpg.de/modellicense.html — official licence page — n.d.
[18] MakeHuman Community licence — https://static.makehumancommunity.org/about/license.html — official docs — n.d.
[19] MakeHuman asset packs — https://static.makehumancommunity.org/assets/assetpacks.html — official docs — n.d.
[20] MediaPipe Iris: Real-time Iris Tracking & Depth Estimation (Google Research) — https://research.google/blog/mediapipe-iris-real-time-iris-tracking-depth-estimation/ — official blog — 2020

[21] FaceBuilder for Blender (KeenTools) — https://keentools.io/products/facebuilder-for-blender — official product page — n.d.

**Further reading (by name, not yet linked)**
- Kartynnik, Ablavatski, Grishchenko, Grundmann, "Real-time Facial Surface Geometry from Monocular Video on Mobile GPUs", 2019 (MediaPipe Face Mesh).
- Grishchenko et al., "Attention Mesh: High-fidelity Face Mesh Prediction in Real-time", 2020.
- Ablavatski et al., "Real-time Pupil Tracking from Monocular Video for Digital Puppetry", 2020 (MediaPipe Iris; 11.7 mm iris figure).
- Li, Bolkart, Black, Li, Romero, "Learning a model of facial shape and expression from 4D scans" (FLAME), SIGGRAPH Asia 2017.
- Paysan et al., "A 3D Face Model for Pose and Illumination Invariant Face Recognition" (Basel Face Model), 2009.
- Li et al., "Learning Formation of Physically-Based Face Attributes" (ICT-FaceKit), CVPR 2020.
- Sorkine et al., "Laplacian Surface Editing", 2004; Sorkine & Alexa, "As-Rigid-As-Possible Surface Modeling", 2007.
- Amberg, Romdhani, Vetter, "Optimal Step Nonrigid ICP Algorithms for Surface Registration", CVPR 2007.
- Dodgson, "Variation and extrema of human interpupillary distance", 2004.
- Apple ARKit documentation, `ARFaceAnchor.BlendShapeLocation`.
- Blender Manual: Extensions and `blender_manifest.toml`; Rigify.

## Verification log (2026-11-20)

- FLAME 2023 Open permissive variant: corrected (exists, CC-BY-4.0, commercial use allowed; earlier versions non-commercial) — https://flame.is.tue.mpg.de/modellicense.html
- MPFB2/MakeHuman asset licences (base mesh, targets, system assets CC0; packs CC0 or CC-BY): confirmed — https://static.makehumancommunity.org/about/license.html , https://static.makehumancommunity.org/assets/assetpacks.html
- MPFB2 version 2.0.18: contested (MakeHuman Community page says released; Extensions listing seen only up to 2.0.16 in one search) — https://static.makehumancommunity.org ; https://extensions.blender.org/add-ons/mpfb/versions/
- MPFB2 Blender 4.2+ minimum and hm08 13.4k/19.2k vertex counts: unconfirmed (no usable evidence in results)
- Iris diameter 11.7 ± 0.5 mm (MediaPipe Iris): confirmed — https://research.google/blog/mediapipe-iris-real-time-iris-tracking-depth-estimation/
- Adult IPD 63 mm, σ 3.5 mm: unconfirmed (not addressed by results)
- Face Landmarker 52 blendshapes incl. `_neutral`, omitting `tongueOut`; iris indices 468–472 / 473–477: unconfirmed (478 landmarks and 52 scores confirmed at https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker, but names and index split not shown)

## Verification log, pass 2 (2026-11-20)

- Faceit range 3.0 to 5.2, FSKR 5.2+, 5.2 LTS the only shared version, 5.3 outside Faceit support: unconfirmed (search returned no Faceit Blender add-on page or 5.3 statement; stays 🧠/📄 as before)
- KeenTools FaceBuilder subscription with trial: confirmed (15-day trial; $19.99/mo monthly, $15.99/mo annual, Studio $699/yr; commercial use allowed) — https://keentools.io/products/facebuilder-for-blender
- FaceBuilder GPL Python front-end with proprietary core, ARKit-compatible blendshapes, EULA terms on exported meshes: unconfirmed (EULA text not in results; install page only says the licence agreement must be accepted) — https://keentools.io/download/facebuilder-for-blender
