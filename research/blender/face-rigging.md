# Face rigging for a reconstructed head

> A photo-fitted head can be made to animate in three ways. The first is a bone rig: Rigify, which ships free with Blender, or the paid Auto-Rig Pro. The second is a shape-key rig named after Apple's ARKit set, so that phone or webcam capture drives it directly. The third, and the industry norm, is a hybrid: bones for the head, neck, jaw and eyes, plus ARKit-named keys and correctives. The design choice that matters most for this project is to **rig the fitting template once, not each scan**. Every fitted head keeps the template's vertex count and order, so weights and expression keys carry over by index; only bone positions and expression deltas need recomputing, and then the person's own smile, blink and brows should be refitted from their expression photos. Live capture (Live Link Face, Face Cap, iFacialMocap, or MediaPipe's 52 webcam scores) delivers 0–1 coefficients that need calibrating per performer and filtering with care around blinks. This topic had no harvest and no earlier draft. Sourced items reuse URLs from the library's blender-face-addons and facs-expressions harvests, and the Rigify internals, Auto-Rig Pro and iOS app details are expert knowledge awaiting verification.
Evidence status: 7 ✅ / 21 📄 / 99 🧠 / 15 ↔️ — 🧠 items are queued for web verification.

## Key facts

### Rig families
- **Rigify** ships with Blender. It generates a body-and-face rig from an editable meta-rig (Add → Armature → Human, then Generate Rig) 🧠.
  - Since 3.0 the face has been a modular "skin" system: chains for the lids, lips, brows, nose and cheeks, glued to one another, plus jaw, eye and tongue rigs. The legacy `super_face` survives behind an "Upgrade Face Rig" button 🧠.
  - Only `DEF-` bones deform, and vertex groups must carry `DEF-` names 🧠.
  - It expects the character to face −Y with Z up and transforms applied, and it has no landmark detection: bones are placed by hand 🧠. Our fitter can do that placement.
- **Auto-Rig Pro** (Artell, paid) 🧠:
  - "Smart" places body bones from clicked markers.
  - A bone face rig covers the brows, lids, lips, jaw, teeth and tongue.
  - Its own binder has a voxelised mode for non-manifold or multi-part meshes.
  - "Remap" handles retargeting, and FBX presets cover Unity and Unreal.
  - It does not generate ARKit keys 🧠, and its Blender 5.x status is unverified ↔️.
- **Faceit** (paid) semi-automatically generates ARKit-style, Audio2Face, tongue and phoneme shape keys, and bakes modifier, pose and sculpt deformation into keys [1] 📄. Its listing gives Blender 3.0–5.2 [1] 📄. The recalled workflow is landmark guide → Rigify-derived face rig → automatic weights → poses → bake, and it imports Live Link Face CSV 🧠.
- **Face Shape Key Rig** (free, GPL) builds viewport sliders and 2D pads that drive *existing* keys through bones and drivers. It supports iFacialMocap capture and audio lipsync [2][3] 📄, creates no shapes itself [2][1] 📄, and needs Blender 5.2+ [3] 📄.
- **CaptureForge** (GPL-3.0) converts a posed face rig into the ARKit 52 blendshapes and drives them from video or webcam without an iPhone. It also lists a quality inspector and an auto face rig [4] 📄.
- **MPFB2** has GPL-3.0-or-later code [19][20] ✅ and offers Rigify and game-engine rigs for its hm08 base 🧠, making it a licence-clean template that is ready to rig.

### Expression vocabularies
- A FACS action unit (AU) is an elementary movement of one muscle or a small group of muscles [15][16] ✅. AU1 is the inner brow raiser, AU4 the brow lowerer and AU6 the cheek raiser [14][15] ✅. AU12 is zygomaticus major, and AU6 is orbicularis oculi, pars orbitalis [17] 📄. Intensity runs from A (trace) to E (the person's maximum) [14][18] ✅.
- ARKit reports named blendshape coefficients from 0 to 1, updated live [6][8] 📄, across 52 names [4] 📄. The canonical list is [7]; a by-region table is in `blender/blender-face-addons.md`. ARKit names are from the subject's side 🧠.
- MediaPipe Face Landmarker outputs 478 landmarks and 52 named scores in [0, 1] [9][11] 📄, so both systems speak 0–1 [6][9] ✅. Its 52 include `_neutral` and lack `tongueOut` 🧠. Scores are off by default (`output_face_blendshapes`) [10] 📄. L/R refers to the subject, and a mirrored input swaps them [9] 📄.
- The base mesh has 468 points, and 478 with iris refinement [9][12][13] ✅.
- ARKit shapes are FACS-inspired, not AUs; the mapping is many-to-many 🧠 (Table 4; `anatomy/facs-expressions.md`).

### Capture paths (time-sensitive)
- **Live Link Face** (Epic, free, iOS):
  - ARKit mode streams 52 curves plus head and per-eye yaw/pitch/roll, 61 values in all, over UDP (default port recalled as 11111). It records a timecoded CSV with the same columns 🧠.
  - MetaHuman Animator mode records depth for an offline solve in Unreal 🧠.
- **Face Cap** (Bannaflak, iOS) records ARKit weights plus head and eye rotation. It exports FBX (a generic head with keys) or text and streams OSC live. It has a free tier with limits and a paid unlock ↔️.
- **iFacialMocap** (iOS) streams ARKit weights over UDP to the desktop. Face Shape Key Rig consumes it [2] 📄; other app details are 🧠.
- **Rokoko**: the Face Capture app and Studio, with a free "Studio Live" Blender plugin 🧠.
- **ARKit tracking** needs a TrueDepth camera, or since iOS 14 an A12-or-later device using RGB only (weaker) 🧠. It runs at up to 60 Hz, and its face mesh has 1,220 vertices 🧠.
- **MediaPipe** in Blender:
  - mozi1924's project splits a transmitter program from a Blender receiver add-on [5] 📄. That is the right architecture, because Blender bundles neither mediapipe nor OpenCV 🧠.
  - BlendArMocap (MediaPipe → Rigify) appears unmaintained 🧠.
- **Blender's own tracker** can do marker capture. Track ink dots in a video, then use a Follow Track constraint with a *Depth Object* to project each track onto the reconstructed head 🧠. The head needs an object solve from ≥8 rigid markers 🧠.

### Blender mechanics that bite
- Shape-key animation lives on the Key datablock (`mesh.shape_keys.animation_data`, path `key_blocks["jawOpen"].value`), not on the object 🧠.
- **Bone-heat automatic weights** (Baran & Popović 2007) 🧠:
  - They fail with "failed to find solution for one or more bones" on non-manifold, duplicate or interior geometry, and on small meshes at real scale. Scaling ×10 while weighting is a common workaround.
  - On a closed-mouth, open-eye neutral they bleed upper-lip bones into the lower lip and upper-lid bones into the lower lid.
- **Shape keys interpolate linearly**, so the arcs of the jaw and lids need bones or correctives 🧠. Keys live at Multires base level, so per-expression fine detail belongs in wrinkle normal maps 🧠. Whether Multires displacement rides cleanly on a keyed base is reported inconsistently ↔️.
- **Cross-topology tools** 🧠:
  - Data Transfer copies weights by nearest-face interpolation.
  - Surface Deform binds a mesh, then "Save as Shape Key" captures each key.
  - Mesh Deform uses a cage.
  - Corrective Smooth runs after the Armature modifier.
- **Driver "simple expressions"** (arithmetic, `min`, `max`) evaluate without Python or auto-run permission 🧠.
- **Writing F-curves:** 4.4 brought slotted Actions, and in 4.4+/5.x F-curves are written through layers, strips and channelbags. The legacy `Action.fcurves` path was deprecated and reportedly removed in 5.0 ↔️.

## Numbers & reference tables

**Table 1 — Tool matrix** (versions and prices are time-sensitive)

| Tool | Makes | Drives | Licence / price | Blender | Badge |
|---|---|---|---|---|---|
| Rigify | bone body + face rig | — | GPL, bundled | all current | 🧠 |
| Auto-Rig Pro | bone face rig, game export | — | paid, GPL code presumed | 5.x ? | 🧠 / ↔️ |
| Faceit | ARKit, A2F, phoneme keys; bake | LLF CSV | paid | 3.0–5.2 [1] | 📄 |
| Face Shape Key Rig | controls only | iFacialMocap, audio | free GPL | ≥5.2 [3] | 📄 |
| CaptureForge | rig → ARKit 52 | video, webcam | GPL-3.0 [4] | — | 📄 |
| mediapipe-facecap | receiver add-on | MediaPipe | — [5] | — | 📄 |
| Live Link Face | — | ARKit 52 + 9 rotations | free app | via CSV/UDP | 🧠 |
| Face Cap / iFacialMocap / Rokoko | — | ARKit | freemium / paid | add-ons or OSC | ↔️ |

**Table 2 — Capture signals**

| Source | Channels | Range | Rate | Badge |
|---|---|---|---|---|
| ARKit (TrueDepth) | 52 coefficients + head and eye transforms | 0–1 [6] | ≤60 Hz | 📄 range; 🧠 rate |
| Live Link Face CSV/UDP | 52 + head and L/R eye yaw/pitch/roll = 61 | 0–1; rotation units unverified | 60 or 30 fps | 🧠 |
| MediaPipe Face Landmarker | 478 landmarks + 52 scores [9][11] | 0–1 [9] | ≈30 fps webcam, CPU | 📄 / 🧠 rate |
| ARKit face mesh | 1,220 vertices | — | — | 🧠 |
| FLAME | 100 expression components + jaw, neck, eye joints | unbounded (σ-scaled) | — | 🧠 |

**Table 3 — Adult motion ranges for rig limits** (approximate; values consistent with `anatomy/facs-expressions.md`)

| Motion | Range | Badge |
|---|---|---|
| Maximum interincisal opening | 40–60 mm | 🧠 |
| Mainly-rotation phase of opening | first ≈20–25 mm | ↔️ |
| Jaw rotation at maximum opening | ≈20–30° | ↔️ (derived) |
| Condylar forward translation at maximum | ≈10–20 mm | ↔️ |
| Speech opening | ≈5–20 mm | 🧠 |
| Lateral excursion / protrusion | ≈8–12 mm / ≈6–10 mm | 🧠 |
| Freeway space at rest | 2–4 mm | 🧠 |
| Palpebral fissure height × width | 8–12 × 27–32 mm | 🧠 |
| Upper lid at rest | covers ≈1–2 mm of the upper iris | 🧠 |
| Blink, full cycle | ≈100–400 ms; closing is faster | 🧠 |
| Eye rotation, artistic rig limits | ±30–35° horizontal; ≈25–30° up, ≈35–45° down | 🧠 |
| Eye centre of rotation | ≈13–14 mm behind the corneal apex | 🧠 |
| Upper incisor display at rest | ≈1–4 mm (more in younger and female subjects) | 🧠 |

**Table 4 — ARKit key ↔ AU ↔ prime mover** (direction priors for deltas)

| ARKit | ≈AU | Prime mover | Main displacement | Badge |
|---|---|---|---|---|
| browInnerUp / browOuterUp | 1 / 2 | frontalis, medial / lateral | brow up | ✅ AU1 [14][15]; rest 🧠 |
| browDown | 4 | corrugator, procerus, depressor supercilii | brow down and in | ✅ AU4 [14][15]; muscles 🧠 |
| cheekSquint | 6 | orbicularis oculi, orbital | cheek up, lower lid bunched | 📄 [17] |
| eyeBlink / eyeSquint / eyeWide | 45 / 7 / 5 | orbicularis oculi, palpebral / same / levator palpebrae | lid closed / lower lid up / upper lid up | 🧠 |
| noseSneer | 9 | levator labii superioris alaeque nasi | ala and lip up | 🧠 |
| mouthUpperUp | 10 | levator labii superioris | upper lip up | 🧠 |
| mouthSmile | 12 | zygomaticus major | commissure up and back toward the zygoma | 📄 [17] |
| mouthDimple / mouthStretch | 14 / 20 | buccinator / risorius, platysma | commissure back / lateral | 🧠 |
| mouthFrown / mouthLowerDown | 15 / 16 | depressor anguli oris / depressor labii inferioris | corner down / lip down | 🧠 |
| mouthShrugLower | 17 | mentalis | chin boss and lower lip up | 🧠 |
| mouthPucker / mouthFunnel / mouthPress / mouthRoll | 18 / 22 / 24 / 28 | orbicularis oris | forward-narrow / flare / press / roll in | 🧠 |
| jawOpen | 26/27 | lateral pterygoid, digastric | rotation, then translation | 🧠 |

**Table 5 — Moving expression keys onto a new identity**

| Method | Needs | Quality | Cost | Badge |
|---|---|---|---|---|
| Copy deltas by index | same topology | fine for small identity changes | trivial | 🧠 |
| Tangent-frame delta transfer | same topology | good | one numpy pass | 🧠 |
| Deformation transfer (Sumner & Popović 2004) | correspondence | best for large identity changes | sparse solve | 🧠 |
| Surface Deform bake | wrapped surface | good if the wrap is tight | native | 🧠 |
| Rig pose → bake (Faceit, CaptureForge) | a weighted rig | as good as the weights | native | 📄 [1][4] |
| Example-based personalisation (Li et al. 2010) | subject expression fits | best likeness in motion | heavy | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Choose the target first.** Animation inside Blender: a Rigify face plus ARKit keys. Engines: the hybrid, exported as FBX with ARKit morphs. MetaHuman: see `blender/metahuman-cc-bridges.md`. Quick mocap: keys alone.
2. **Make the fit rig-ready**, since photos never show the parts a rig needs (see `blender/face-retopology.md`) 🧠:
   - Lids: open, with thickness and 1–2 loops tucking into the socket.
   - Eyes: separate globes of radius ≈12 mm, with the pivot from Table 3.
   - Mouth: a cut wet line and a mouth bag.
   - Teeth and tongue: upper teeth parented to the head; lower teeth and tongue to the jaw.
3. **Neutralise** residual expression before rigging (see `reconstruction/expression-neutralization.md`). Otherwise the residual stays baked into the rest pose and calibration subtracts it a second time 🧠.
4. **Rigify:**
   - Add the Human meta-rig at real scale.
   - Snap the lid, lip and brow chains to the fitted contours and the jaw to the condyle (Table 3), then Generate.
   - Parent with Automatic Weights.
   - Remove upper-lip and upper-lid `DEF-` groups from the lower lip and lower lid, then smooth.
   - Test a blink, a 30 mm jaw opening and a full smile.
5. **Keys:**
   - Bake ARKit keys with Faceit [1] or CaptureForge [4], or transfer the template's keys (Table 5).
   - Then re-sculpt the identity-bearing ones from the subject's expression photos: mouthSmile + cheekSquint + eyeSquint, eyeBlink, the brows, jawOpen, and pucker/funnel.
   - Drive the jaw bone from jawOpen and add a corrective key.
6. **Mocap:**
   - Record 5–10 s of neutral and one range-of-motion take per key.
   - Calibrate, filter (Table 6), and record onto the Key's F-curves in bulk.
   - Resample Live Link Face 60 fps data to the scene's frame rate 🧠.
7. **What goes wrong** 🧠:
   - a closed-mouth neutral welded at the wet line, so the lips cannot part;
   - auto weights bleeding across the lips and lids;
   - a jaw pivot at the ear lobe or the chin's centre;
   - eyeBlink combined with eyeLookDown overshooting the cornea;
   - mouthClose fired without jawOpen, pushing the lips through each other;
   - a mirrored selfie stream swapping L/R [9];
   - generic template smiles erasing the likeness in motion;
   - over-smoothed blinks.
8. **Consent:** recorded performance of a real face is biometric-grade data. The consent form should cover animation and capture apps that send data to the cloud (see `ethics/`) 🧠.

## Algorithmic implications

- **Rig profile** stored with the template 🧠: `{template_id, topology_hash, bones:[{name, head, tail, roll_ref}], weights (by index), keys: ARKit52 deltas}`. Each joint is one of:
  - a barycentric surface point plus an offset along the normal;
  - a fixed combination of landmark vertices;
  - an interior point.
  The profile refuses to rig on a hash mismatch.
- **Bone re-placement** 🧠:
  - Map interior pivots with a thin-plate spline built from ≥30 surface correspondences, then pull each toward its anatomical prior:
    - eye centre from the fitted globe, σ 0.5 mm;
    - condyle ≈10–15 mm anterior and 0–10 mm inferior to tragion, 15–20 mm deep, σ 3–4 mm;
    - head pivot near the midpoint of the mastoid tips, σ 6 mm.
  - Rebuild `edit_bones`, then call `pose.rigify_generate()`. Names are stable, so the vertex groups persist.
- **Weights** 🧠: copy by index and renormalise. Assert a per-vertex sum of 1 ± 1e-4, ≤4 influences for engine export, cross-lip and cross-lid bleed ≤0.02, and a rig rest pose matching the neutral within 1e-5·head size.
- **Expression transfer** 🧠:
  - Express each template delta in its vertex's (normal, tangent, bitangent) frame, scale it by √(one-ring area ratio), and re-apply it on the fit.
  - Optional deformation transfer uses matrix-free conjugate gradients in pure NumPy; Blender bundles no SciPy. 52 keys × 5–15k vertices is fine.
  - Reject any key whose main displacement at its control vertex departs >30° from the Table 4 direction.
- **Personalisation** (Li, Weise & Pauly 2010) 🧠:
  1. For each subject expression photo, fit ARKit weights w_e with identity fixed.
  2. Solve corrections ΔB that minimise Σ‖(B+ΔB)w_e − X_e‖² + λ‖ΔB‖², starting at λ≈10 (relative) and annealing.
  3. Correct only keys with w_e > 0.3 somewhere.
- **Jaw model** 🧠: θ = θmax·w, with θmax ≈ 25° (Table 3) and condylar translation d = dmax·max(0, (w − w0)/(1 − w0)), where w0 ≈ 0.4–0.5 and dmax ≈ 10–15 mm. Clamp mouthClose ≤ jawOpen and add an eyeBlink×eyeLookDown corrective.
- **Mocap pipeline** 🧠:
  - Calibrate each key with w′ = clip((w − n)/(m − n), 0, 1)·g, where n is the neutral median, m the 98th percentile of the ROM take, g a gain (default 1), and a deadzone of 0.02–0.05.
  - Filter with a One Euro filter (Table 6).
  - Map by name through a 52×K matrix (identity by default).
  - Receive on a non-blocking socket under `bpy.app.timers`, keeping the newest packet.
  - Record by buffering and then using `keyframe_points.add(n)` plus `foreach_set("co")`.
- **Table 6 — mocap defaults** 🧠:

| Channel | min_cutoff (Hz) | β (tune from 0) | Notes |
|---|---|---|---|
| brows, mouth, cheeks | 1.0–1.5 | 0.01–0.5 | — |
| eyeBlink, eyeLook | 3–5 | higher | blink lasts ≈3–12 frames at 30 fps |
| head rotation | 0.5–1.0 | low | quaternion domain |

- **Likeness in motion** 🧠: report landmark RMS (%IOD) between the rig's best fit and each expression photo. Targets: anchors ≤1.5% and contours ≤2.5%, matching the library's σ conventions.
- **Licensing** 🧠: never bundle Faceit or Auto-Rig Pro. Detect them and hand off. Generated rigs and meshes are user data, not GPL code.

## Disagreements, myths & open questions

- **Bones vs blendshapes** ↔️: games and MetaHuman lean on joints plus correctives, while mocap-first pipelines lean on ARKit keys. A hybrid is the safe default.
- **ARKit TrueDepth vs a MediaPipe webcam** ↔️: TrueDepth is usually better at the mouth and tongue, but no mm-level benchmark exists in this library.
- **Myth: "mocap makes it look like them."** Capture moves the rig; likeness in motion lives in personal keys 🧠.
- **Myth: "Rigify's face is dated."** That describes the legacy face; the modular skin face dates from 3.0 🧠.
- **mouthClose semantics** ↔️: many pipelines treat it as relative to jawOpen; check against [7].
- **KeenTools blendshape count:** 51 vs 52 ↔️ (`reconstruction/commercial-head-tools.md`).
- **Open questions:**
  - Rigify face changes from 4.x to 5.3;
  - Auto-Rig Pro and Faceit support beyond 5.2 [1];
  - Live Link Face packet layout and units;
  - Android and webcam MetaHuman Animator from UE 5.6 ↔️;
  - the reported 2025 open-sourcing of NVIDIA Audio2Face ↔️;
  - Face Cap pricing;
  - the unread leads [21][22].

## Sources

[1] Faceit: Facial Expressions and Performance Capture (Superhive) — https://superhivemarket.com/products/faceit — commercial listing — n.d. (blender-face-addons harvest)
[2] Face Shape Key Rig (Blender Extensions) — https://extensions.blender.org/add-ons/face-shapekey-rig/ — official listing — n.d. (blender-face-addons harvest)
[3] Fragid/face-shapekey-rig (GitHub) — https://github.com/Fragid/face-shapekey-rig — repo — n.d. (blender-face-addons harvest)
[4] H0wZy/captureforge (GitHub) — https://github.com/H0wZy/captureforge — repo — n.d. (blender-face-addons harvest)
[5] mozi1924/mediapipe-facecap-for-blender (GitHub) — https://github.com/mozi1924/mediapipe-facecap-for-blender — repo — n.d. (blender-face-addons harvest)
[6] Apple ARKit: ARFaceAnchor.blendShapes — https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapes — official docs — n.d. (facs-expressions harvest)
[7] Apple ARKit: ARFaceAnchor.BlendShapeLocation — https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapelocation — official docs — n.d. (facs-expressions harvest; not read)
[8] Apple Tech Talks 601: Face Tracking with ARKit — https://developer.apple.com/videos/play/tech-talks/601/ — official video — n.d. (facs-expressions harvest)
[9] MediaPipe Face Landmarker (Google AI Edge) — https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker — official docs — n.d. (facs-expressions harvest)
[10] MediaPipe Face landmark detection guide for Python — https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python — official docs — n.d. (facs-expressions harvest)
[11] MediaPipe FaceLandmarkerResult API — https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/FaceLandmarkerResult — official docs — n.d. (facs-expressions harvest)
[12] MediaPipe Face Mesh: All 478 Landmark Points (DEV Community) — https://dev.to/metsander/mediapipe-face-mesh-all-478-landmark-points-5ec8 — blog — n.d. (blender-face-addons harvest)
[13] MediaPipe Face Mesh (legacy docs mirror) — https://mediapipe.readthedocs.io/en/latest/solutions/face_mesh.html — official docs — n.d. (blender-face-addons harvest)
[14] Facial Action Coding System (Wikipedia) — https://en.wikipedia.org/wiki/Facial_Action_Coding_System — encyclopedia — n.d. (facs-expressions harvest)
[15] IEEE Technav: Action units — https://technav.ieee.org/topic/action-units/ — reference — n.d. (facs-expressions harvest)
[16] Lancaster University psychology glossary: action unit — https://www.lancaster.ac.uk/fas/psych/glossary/action_unit/ — glossary — n.d. (facs-expressions harvest)
[17] The Role of Facial Action Units in Investigating Facial Movements During Speech (PMC) — https://pmc.ncbi.nlm.nih.gov/articles/PMC13229553/ — paper — n.d. (facs-expressions harvest)
[18] Scoring Upper Face Action Units (FACS manual excerpt, SlideShare copy) — https://pt.slideshare.net/wooo17/manual-1st — manual excerpt — n.d. (facs-expressions harvest)
[19] MPFB, Blender Extensions listing — https://extensions.blender.org/add-ons/mpfb/ — official listing — n.d. (blender-face-addons harvest)
[20] mpfb2 LICENSE.CODE.md — https://github.com/makehumancommunity/mpfb2/blob/master/LICENSE.CODE.md — repo — n.d. (blender-face-addons harvest)
[21] TalkingHead blender/Faceit/FACEIT.md — https://github.com/met4citizen/TalkingHead/blob/main/blender/Faceit/FACEIT.md — repo doc — n.d. (lead, unread)
[22] wk FaceRig (Superhive) — https://superhivemarket.com/products/wk-facerig — commercial listing — n.d. (lead, unread)

**Further reading (by name, not yet linked)**
- Blender Manual: Rigify (meta-rigs, face "skin" rig types, Upgrade Face Rig); Armature, Data Transfer, Surface Deform, Corrective Smooth modifiers; Follow Track constraint
- Blender developer docs: 4.4 slotted Actions and 5.0 Python API changes
- Auto-Rig Pro documentation (Artell); Faceit documentation
- Epic Games, Live Link Face app documentation
- Ekman, Friesen & Hager, *Facial Action Coding System*, 2002
- Baran & Popović, "Automatic Rigging and Animation of 3D Characters", SIGGRAPH 2007
- Sumner & Popović, "Deformation Transfer for Triangle Meshes", SIGGRAPH 2004
- Li, Weise & Pauly, "Example-Based Facial Rigging", SIGGRAPH 2010
- Bouaziz, Wang & Pauly, "Online Modeling for Realtime Facial Animation", SIGGRAPH 2013
- Lewis et al., "Practice and Theory of Blendshape Facial Models", Eurographics STAR 2014
- Orvalho et al., "Transferring the Rig and Animations from a Character to Different Face Models", Computer Graphics Forum 2008
- Le & Deng, "Smooth Skinning Decomposition with Rigid Bones", SIGGRAPH Asia 2012
- Casiez, Roussel & Vogel, "1€ Filter", CHI 2012
- Becker & Fuchs, "Lid-eye coordination during vertical gaze changes in man and monkey", J Neurophysiol 1988
- Vig & Brundo, "The kinetics of anterior tooth display", J Prosthet Dent 1978
- Osipa, *Stop Staring: Facial Modeling and Animation Done Right*, 3rd ed., 2010
