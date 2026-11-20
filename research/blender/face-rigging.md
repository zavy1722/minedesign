# Face rigging for a reconstructed head

> A photo-fitted head can be rigged three ways. It can get a bone rig (Rigify, which ships with Blender, or the paid Auto-Rig Pro). It can get a shape-key rig with Apple ARKit key names, which phone or webcam capture drives directly. Or it can get the industry-standard hybrid: bones for the head, neck, jaw and eyes, ARKit-named keys for the rest, plus correctives. The decisive choice for this project is to **rig the fitting template once, not each scan**. Every fit shares the template's vertex count and order, so weights and keys carry over by index; only the bone positions and the expression deltas are recomputed, and the person's own smile, blink and brows are refitted from their expression photos. Live capture (Live Link Face, Face Cap, iFacialMocap, MediaPipe) arrives as 0–1 coefficients and needs per-performer calibration plus filtering that preserves blinks. This topic had no harvest or draft, so the cited URLs come from two sibling harvests (blender-face-addons, facs-expressions).
Evidence status: 8 ✅ / 22 📄 / 71 🧠 / 13 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Rig families**
- **Rigify** ships with Blender and generates a rig from an editable meta-rig: Human → Generate Rig 🧠.
  - Since 3.0 the face is a modular "skin" system 🧠: glued chains for the lids, lips, brows, nose and cheeks, plus jaw, eye and tongue rigs. The legacy `super_face` has an "Upgrade Face Rig" button.
  - Only `DEF-` bones deform 🧠.
  - It expects the model facing −Y, with Z up and transforms applied 🧠.
  - Bones are placed by hand 🧠, so the landmarks our fitter produces can place them automatically.
- **Auto-Rig Pro** (Artell, paid) has marker-based "Smart" body placement, a bone face rig (brows, lids, lips, jaw, teeth, tongue), its own binder with a voxelised mode for non-manifold or multi-part meshes, Remap retargeting, and Unity/Unreal FBX presets 🧠. It does not generate ARKit keys 🧠. Blender 5.x support is unverified ↔️.
- **Faceit** (paid) generates ARKit-style, Audio2Face, tongue and phoneme shape keys, and bakes modifier, pose and sculpt deformation into keys [1] 📄. It is listed for Blender 3.0–5.2 [1] 📄. Recalled workflow 🧠: landmark guide → Rigify-derived face rig → auto weights → poses → bake. It also imports Live Link Face CSV 🧠.
- **Face Shape Key Rig** (free, GPL) drives *existing* keys from viewport sliders and 2D pads through bones and drivers. It supports iFacialMocap and audio lipsync [2][3] 📄, creates no shapes [2][1] 📄, and needs Blender 5.2+ [3] 📄.
- **CaptureForge** (GPL-3.0) converts a posed face rig to the ARKit 52 and drives them from video or webcam without an iPhone [4] 📄.
- **MPFB2** has GPL-3.0-or-later code [19][20] ✅ and Rigify and game-engine rig options for its hm08 base 🧠, which makes it a licence-clean, rig-ready template.

**Expression vocabularies**
- **FACS.**
  - An action unit (AU) is an elementary movement of one muscle or a small group of muscles [15][16] ✅.
  - AU1 is the inner brow raiser, AU4 the brow lowerer and AU6 the cheek raiser [14][15] ✅.
  - AU12 is zygomaticus major, and AU6 is orbicularis oculi, pars orbitalis [17] 📄.
  - Intensity is scored A (trace) to E (that person's maximum) [14][18] ✅.
- **ARKit.**
  - It reports named coefficients from 0 to 1, updated live [6][8] 📄, and has 52 names [4] 📄. The canonical list is [7]; a by-region table is in `blender/blender-face-addons.md`.
  - Left and right are the subject's 🧠.
  - ARKit shapes are FACS-inspired, not action units, and the mapping between them is many-to-many 🧠.
- **MediaPipe Face Landmarker.**
  - It outputs 478 landmarks and 52 named scores in [0,1] [9][11] 📄. Both systems therefore speak 0–1 [6][9] ✅.
  - Its 52 include `_neutral` and lack `tongueOut` 🧠.
  - Scores are off by default (`output_face_blendshapes`) [10] 📄.
  - Left and right refer to the subject, and mirrored input swaps them [9] 📄.
  - The mesh has 468 points, or 478 with iris refinement [9][12][13] ✅.

**Capture paths** (time-sensitive)
- **Live Link Face** (Epic, free, iOS) 🧠.
  - ARKit mode streams 61 values over UDP: the 52 curves plus yaw/pitch/roll for the head and for each eye. The default port is recalled as 11111.
  - The same columns can be recorded as a timecoded CSV.
  - MetaHuman Animator mode records depth for an Unreal solve.
- **Face Cap** (Bannaflak, iOS) records ARKit weights plus head and eye rotation. It exports FBX or text and streams over OSC. It is freemium ↔️.
- **iFacialMocap** streams ARKit data over UDP; Face Shape Key Rig consumes it [2] 📄.
- **Rokoko** has a Face Capture app and a free "Studio Live" Blender plugin 🧠.
- **ARKit tracking** needs TrueDepth; since iOS 14 it also runs on A12-or-later devices from RGB alone, with weaker results. It runs at up to 60 Hz and its face mesh has 1,220 vertices 🧠.
- **MediaPipe.** mozi1924's project splits a transmitter program from a Blender receiver add-on [5] 📄. That is the right architecture, because Blender bundles neither mediapipe nor OpenCV 🧠. BlendArMocap appears unmaintained 🧠.
- **Blender's tracker.** Track ink dots in a video. A Follow Track constraint with a *Depth Object* then projects each track onto the reconstructed head; head motion needs an object solve from ≥8 rigid markers 🧠.

**Blender mechanics that bite**
- **Shape-key animation lives on the Key datablock**, not the object: `mesh.shape_keys.animation_data`, F-curve path `key_blocks["jawOpen"].value` 🧠.
- **Bone-heat automatic weights** (Baran & Popović 2007) fail with "failed to find solution for one or more bones" 🧠:
  - Causes: non-manifold, duplicate or interior geometry, and tiny real-scale meshes.
  - Common workaround: scale ×10 while weighting.
  - On a closed-mouth, open-eye neutral, the weights bleed across the lips and the lids.
- **Keys interpolate linearly**, so the arcs of the jaw and lids need bones or correctives 🧠. Keys live at Multires base level, so per-expression detail goes into wrinkle normal maps 🧠. Whether Multires detail rides cleanly on a keyed base is reported inconsistently ↔️.
- **Cross-topology tools** 🧠:
  - Data Transfer for weights.
  - Surface Deform, then "Save as Shape Key" for each key.
  - Mesh Deform for cages.
  - Corrective Smooth placed after Armature.
- **Driver simple expressions** (arithmetic, `min`, `max`) run without Python or auto-run permission 🧠.
- **Slotted Actions** arrived in 4.4: F-curves are written through layers, strips and channelbags, and `Action.fcurves` was reportedly removed in 5.0 ↔️.

## Numbers & reference tables

**Table 1 — Tool matrix** (time-sensitive)

| Tool | Makes | Drives / consumes | Licence, price | Blender | Badge |
|---|---|---|---|---|---|
| Rigify | bone body + face rig | — | GPL, bundled | current | 🧠 |
| Auto-Rig Pro | bone face rig, game export | — | paid | 5.x unverified | ↔️ |
| Faceit | ARKit/A2F/phoneme keys, bake | Live Link Face CSV | paid | 3.0–5.2 [1] | 📄 |
| Face Shape Key Rig | controls only | iFacialMocap, audio | free, GPL | ≥5.2 [3] | 📄 |
| CaptureForge | rig → ARKit 52 | video, webcam | GPL-3.0 [4] | — | 📄 |
| Live Link Face | — | 52 + 9 rotations | free app | via CSV/UDP | 🧠 |

**Table 2 — Capture signals**

| Source | Channels | Range | Rate | Badge |
|---|---|---|---|---|
| ARKit (TrueDepth) | 52 + head/eye transforms | 0–1 [6] | ≤60 Hz | 📄 range; 🧠 rate |
| Live Link Face | 52 + 9 yaw/pitch/roll = 61 | 0–1; rotation units unverified | 60 or 30 fps | 🧠 |
| MediaPipe | 478 landmarks + 52 scores [9][11] | 0–1 [9] | ≈30 fps (webcam, CPU) | 📄; 🧠 rate |

**Table 3 — Adult motion ranges for rig limits** (approximate; consistent with `anatomy/facs-expressions.md`)

| Motion | Range | Badge |
|---|---|---|
| Maximum interincisal opening | 40–60 mm | 🧠 |
| Mostly-rotation phase | first ≈20–25 mm | ↔️ |
| Jaw rotation at maximum | ≈20–30° | ↔️ |
| Condylar translation at maximum | ≈10–20 mm | ↔️ |
| Lateral excursion; protrusion | ≈8–12 mm; ≈6–10 mm | 🧠 |
| Palpebral fissure, height × width | 8–12 × 27–32 mm | 🧠 |
| Upper lid at rest | covers ≈1–2 mm of the iris | 🧠 |
| Blink cycle | ≈100–400 ms | 🧠 |
| Eye-rotation rig limits | ±30–35° horizontal; ≈25–30° up, ≈35–45° down | 🧠 |
| Eye centre of rotation | ≈13–14 mm behind the corneal apex | 🧠 |
| Upper incisor display at rest | ≈1–4 mm | 🧠 |

**Table 4 — ARKit key ↔ AU ↔ prime mover** (direction priors for deltas)

| ARKit | ≈AU | Prime mover → displacement | Badge |
|---|---|---|---|
| browInnerUp / browOuterUp | 1 / 2 | frontalis, medial / lateral → brow up | ✅ AU1 [14][15]; rest 🧠 |
| browDown | 4 | corrugator (+ procerus) → brow down and in | ✅ corrugator [14][15]; procerus 🧠 |
| cheekSquint | 6 | orbicularis oculi, orbital part → cheek up | 📄 [17] |
| eyeBlink / eyeSquint / eyeWide | 45 / 7 / 5 | orbicularis oculi, palpebral part; levator palpebrae superioris | 🧠 |
| noseSneer / mouthUpperUp | 9 / 10 | levator labii superioris (alaeque nasi) → ala and upper lip up | 🧠 |
| mouthSmile | 12 | zygomaticus major → commissure up and back | 📄 [17] |
| mouthStretch / mouthFrown / mouthLowerDown | 20 / 15 / 16 | risorius; depressor anguli oris; depressor labii inferioris | 🧠 |
| mouthShrugLower | 17 | mentalis → chin boss and lower lip up | 🧠 |
| mouthPucker / mouthFunnel / mouthPress / mouthRoll | 18 / 22 / 24 / 28 | orbicularis oris | 🧠 |
| jawOpen | 26/27 | lateral pterygoid, digastric → rotation, then translation | 🧠 |

**Table 5 — Moving expression keys onto a new identity**

| Method | Needs | Quality | Badge |
|---|---|---|---|
| Copy deltas by index | same topology | small identity changes only | 🧠 |
| Tangent-frame delta transfer | same topology | good, one NumPy pass | 🧠 |
| Deformation transfer (Sumner & Popović 2004) | correspondence | best for large changes; sparse solve | 🧠 |
| Surface Deform bake | a tight wrap | good | 🧠 |
| Pose → bake (Faceit, CaptureForge) | a weighted rig | as good as the weights | 📄 [1][4] |
| Example-based personalisation (Li et al. 2010) | subject expression fits | best likeness in motion | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Pick the target.**
   - Blender animation: a Rigify face plus ARKit keys.
   - Game engines: the hybrid, as FBX with ARKit morphs.
   - MetaHuman: see `blender/metahuman-cc-bridges.md`.
2. **Make the fit rig-ready**, because photos never show what a rig needs (`blender/face-retopology.md`) 🧠:
   - open lids with thickness and 1–2 loops tucked into the socket;
   - separate globes of r ≈ 12 mm, pivoted per Table 3;
   - a cut wet line and a mouth bag;
   - upper teeth on the head bone, lower teeth and tongue on the jaw.
3. **Neutralise expression first** (`reconstruction/expression-neutralization.md`). Otherwise the residual expression becomes the rest pose, and mocap calibration subtracts it a second time 🧠.
4. **Rigify** 🧠:
   - Add the Human meta-rig at real scale.
   - Snap the lid, lip and brow chains to the fitted contours, and put the jaw at the condyle, not the ear lobe.
   - Generate, then parent with Automatic Weights.
   - Strip the upper-lip and upper-lid `DEF-` groups from the lower lip and lower lid, then smooth.
   - Test a blink, a 30 mm jaw opening and a full smile.
5. **Keys.**
   - Bake the ARKit set with Faceit [1] or CaptureForge [4], or transfer it from the template (Table 5).
   - Re-sculpt the identity-bearing keys from the subject's expression photos: smile + cheekSquint + eyeSquint, blink, brows, jawOpen, pucker/funnel 🧠.
   - Drive the jaw bone from jawOpen and add a corrective 🧠.
6. **Mocap** 🧠:
   - Record 5–10 s of neutral plus one range-of-motion (ROM) take per key.
   - Calibrate and filter (Table 6).
   - Bulk-write the result to the Key's F-curves, resampled to the scene fps.
7. **What goes wrong** 🧠:
   - lips welded at the wet line;
   - auto weights bleeding across the lips and lids;
   - eyeBlink + eyeLookDown overshooting the cornea;
   - mouthClose without jawOpen pushing the lips through each other;
   - mirrored selfie streams swapping left and right [9];
   - generic template smiles erasing the likeness;
   - over-smoothed blinks.
8. **Consent.** Captured performance of a real face is biometric-grade data, so the consent must name animation and any cloud capture apps (`ethics/`) 🧠.

## Algorithmic implications

- **Rig profile** shipped with the template 🧠:
  - Contents: `{template_id, topology_hash, bones[{name, head, tail, roll_ref}], weights, ARKit52 deltas}`.
  - Each joint is one of three kinds: a barycentric surface point plus a normal offset, a combination of landmarks, or an interior point.
  - Refuse to rig on a hash mismatch.
- **Bone re-placement** 🧠:
  - Warp the interior pivots with a thin-plate spline built from ≥30 surface correspondences.
  - Then pull each pivot toward its prior:
    - eye centre: the fitted globe, σ 0.5 mm;
    - condyle: ≈10–15 mm anterior and 0–10 mm inferior to tragion, 15–20 mm deep, σ 3–4 mm;
    - head pivot: near the midpoint of the mastoid tips, σ 6 mm.
  - Rebuild `edit_bones`, then call `pose.rigify_generate()`. Bone names stay stable, so the vertex groups persist.
- **Weights QA** 🧠:
  - per-vertex sum 1 ± 1e-4;
  - ≤4 influences for engine export;
  - weight bleed across the lips or lids ≤ 0.02;
  - rest pose matches the neutral within 1e-5 × head size.
- **Expression transfer** 🧠:
  - Express each template delta in its vertex's (normal, tangent, bitangent) frame. Scale it by √(one-ring area ratio), then re-apply it on the fit.
  - Optional: deformation transfer via matrix-free conjugate gradients in pure NumPy, since Blender bundles no SciPy. This is fine for 52 keys × 5–15k vertices.
  - Reject a key whose main displacement at its control vertex departs more than 30° from Table 4.
- **Personalisation** (Li, Weise & Pauly 2010) 🧠:
  1. Fit ARKit weights w_e to each expression photo, with identity fixed.
  2. Solve min Σ‖(B+ΔB)w_e − X_e‖² + λ‖ΔB‖², starting from λ ≈ 10 (relative) and annealing it down.
  3. Correct only keys with w_e > 0.3 in some photo.
- **Jaw** 🧠:
  - Rotation: θ = θmax·w, with θmax ≈ 25°.
  - Translation: d = dmax·max(0, (w − w0)/(1 − w0)), with w0 ≈ 0.4–0.5 and dmax ≈ 10–15 mm.
  - Clamp mouthClose ≤ jawOpen, and add an eyeBlink × eyeLookDown corrective.
- **Mocap** 🧠:
  - Calibrate with w′ = clip((w − n)/(m − n), 0, 1)·g, where n is the neutral median, m the ROM 98th percentile and g a gain (default 1). Add a deadzone of 0.02–0.05.
  - Map by name through a 52×K matrix (identity by default).
  - Read a non-blocking socket from `bpy.app.timers`, keeping only the newest packet.
  - Record in bulk with `keyframe_points.add(n)` + `foreach_set("co")`.
- **Table 6 — One Euro filter starting points** 🧠

| Channels | min_cutoff (Hz) | β | Note |
|---|---|---|---|
| brows, mouth, cheeks | 1.0–1.5 | 0.01–0.5, tuned from 0 | — |
| eyeBlink, eyeLook | 3–5 | higher | a blink lasts ≈3–12 frames at 30 fps |
| head rotation | 0.5–1.0 | low | filter on quaternions |

- **Expression-likeness metric** 🧠: landmark RMS between the rig's best fit and each expression photo, as % of inter-ocular distance (IOD). Targets: anchors ≤ 1.5%, contours ≤ 2.5%.
- **Licensing** 🧠: never bundle Faceit or Auto-Rig Pro; detect them and hand off.

## Disagreements, myths & open questions

- **Bones vs blendshapes** ↔️. Engines and MetaHuman favour joints plus correctives; mocap-first pipelines favour ARKit keys. A hybrid is the safe default.
- **TrueDepth vs MediaPipe webcam** ↔️. TrueDepth is usually better for the mouth and tongue, but no mm-level benchmark exists in this library.
- **Myth: "mocap makes it look like them."** Capture moves the rig; likeness in motion lives in personal keys 🧠.
- **Myth: "Rigify's face is dated."** Only the legacy face is 🧠.
- **mouthClose** is often treated as relative to jawOpen ↔️; check it against [7].
- **Open questions:**
  - Rigify face changes from 4.x to 5.3.
  - Auto-Rig Pro and Faceit support beyond 5.2 [1].
  - The Live Link Face packet layout and units.
  - Webcam and Android input to MetaHuman Animator since UE 5.6 ↔️.
  - The reported 2025 open-sourcing of NVIDIA Audio2Face ↔️.
  - Unread leads [21][22].

## Sources

[1] Faceit: Facial Expressions and Performance Capture (Superhive) — https://superhivemarket.com/products/faceit — commercial listing — n.d. (face-addons harvest)
[2] Face Shape Key Rig (Blender Extensions) — https://extensions.blender.org/add-ons/face-shapekey-rig/ — official listing — n.d. (face-addons harvest)
[3] Fragid/face-shapekey-rig (GitHub) — https://github.com/Fragid/face-shapekey-rig — repo — n.d. (face-addons harvest)
[4] H0wZy/captureforge (GitHub) — https://github.com/H0wZy/captureforge — repo — n.d. (face-addons harvest)
[5] mozi1924/mediapipe-facecap-for-blender (GitHub) — https://github.com/mozi1924/mediapipe-facecap-for-blender — repo — n.d. (face-addons harvest)
[6] Apple ARKit: ARFaceAnchor.blendShapes — https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapes — official docs — n.d. (facs harvest)
[7] Apple ARKit: ARFaceAnchor.BlendShapeLocation — https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapelocation — official docs — n.d. (facs harvest; unread)
[8] Apple Tech Talks 601: Face Tracking with ARKit — https://developer.apple.com/videos/play/tech-talks/601/ — official video — n.d. (facs harvest)
[9] MediaPipe Face Landmarker — https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker — official docs — n.d. (facs harvest)
[10] MediaPipe Face landmark detection guide for Python — https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python — official docs — n.d. (facs harvest)
[11] MediaPipe FaceLandmarkerResult API — https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/FaceLandmarkerResult — official docs — n.d. (facs harvest)
[12] MediaPipe Face Mesh: All 478 Landmark Points (DEV) — https://dev.to/metsander/mediapipe-face-mesh-all-478-landmark-points-5ec8 — blog — n.d. (face-addons harvest)
[13] MediaPipe Face Mesh (legacy docs mirror) — https://mediapipe.readthedocs.io/en/latest/solutions/face_mesh.html — official docs — n.d. (face-addons harvest)
[14] Facial Action Coding System (Wikipedia) — https://en.wikipedia.org/wiki/Facial_Action_Coding_System — encyclopedia — n.d. (facs harvest)
[15] IEEE Technav: Action units — https://technav.ieee.org/topic/action-units/ — reference — n.d. (facs harvest)
[16] Lancaster University glossary: action unit — https://www.lancaster.ac.uk/fas/psych/glossary/action_unit/ — glossary — n.d. (facs harvest)
[17] The Role of Facial Action Units in Investigating Facial Movements During Speech — https://pmc.ncbi.nlm.nih.gov/articles/PMC13229553/ — paper — n.d. (facs harvest)
[18] Scoring Upper Face Action Units (FACS manual excerpt) — https://pt.slideshare.net/wooo17/manual-1st — manual excerpt — n.d. (facs harvest)
[19] MPFB (Blender Extensions) — https://extensions.blender.org/add-ons/mpfb/ — official listing — n.d. (face-addons harvest)
[20] mpfb2 LICENSE.CODE.md — https://github.com/makehumancommunity/mpfb2/blob/master/LICENSE.CODE.md — repo — n.d. (face-addons harvest)
[21] TalkingHead blender/Faceit/FACEIT.md — https://github.com/met4citizen/TalkingHead/blob/main/blender/Faceit/FACEIT.md — repo doc — n.d. (lead, unread)
[22] wk FaceRig (Superhive) — https://superhivemarket.com/products/wk-facerig — commercial listing — n.d. (lead, unread)

**Further reading (by name, not yet linked)**
- Blender Manual: Rigify; the Data Transfer, Surface Deform and Corrective Smooth modifiers; the Follow Track constraint. Blender 4.4/5.0 Python API release notes
- Auto-Rig Pro documentation (Artell); Epic Games, Live Link Face documentation
- Ekman, Friesen & Hager, *Facial Action Coding System*, 2002
- Baran & Popović, "Automatic Rigging and Animation of 3D Characters", SIGGRAPH 2007
- Sumner & Popović, "Deformation Transfer for Triangle Meshes", SIGGRAPH 2004
- Li, Weise & Pauly, "Example-Based Facial Rigging", SIGGRAPH 2010
- Lewis et al., "Practice and Theory of Blendshape Facial Models", Eurographics STAR 2014
- Orvalho et al., "Transferring the Rig and Animations from a Character to Different Face Models", Computer Graphics Forum 2008
- Casiez, Roussel & Vogel, "1€ Filter", CHI 2012
- Becker & Fuchs, "Lid-eye coordination during vertical gaze changes in man and monkey", J Neurophysiol 1988
- Osipa, *Stop Staring: Facial Modeling and Animation Done Right*, 3rd ed., 2010
