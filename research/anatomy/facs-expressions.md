# FACS action units and expression mechanics

> The Facial Action Coding System (FACS) codes every visible facial movement as a numbered action unit (AU). Each AU is the appearance change produced by one muscle or a small group of muscles, and its intensity is scored from A (trace) to E (the person's maximum). The system descends from Hjortsjö's work and was published by Ekman and Friesen in 1978, then revised with Hager in 2002. For likeness work FACS does two jobs. It is the vocabulary behind the 52 blendshape coefficients that ARKit and MediaPipe output and behind most production face rigs. It also predicts which identity features an expression will corrupt when it leaks into a reference photo: brow height, lid aperture, nasolabial depth, mouth width, chin shape and lower-face height. The identity mesh must therefore be the subject's *relaxed* neutral: no active AUs, jaw at rest, lips lightly sealed. A fitter cannot reliably tell a slight AU6+12 smile or an AU26 jaw drop apart from bone and soft-tissue shape.
>
> Evidence status: 5 ✅ / 14 📄 / 38 🧠 / 7 ↔️ — 🧠 items are queued for web verification.

## Key facts

- **What an AU is.** An AU is an elementary facial movement corresponding to the contraction (or relaxation) of one muscle or a small muscle group [2][3]. ✅ FACS codes *appearance*, not muscle activity, and coders train on that distinction [1]. 📄
- **Lineage.** FACS grew out of Hjortsjö's work. Ekman and Friesen published it in 1978, and Ekman, Friesen and Hager substantially revised it in 2002 [1]. 📄
- **How many AUs.** One source counts 44 AUs in the 1978 system. Another says roughly 30 numbered muscular units, plus separate descriptors for head pose, gaze and gross behaviour [1][2]. ↔️ The two counts probably fit together. The figure usually quoted in computer vision is 44 AUs in total, of which about 30 are tied to specific muscles (about 12 in the upper face and 18 in the lower face). The rest are action descriptors (ADs) and codes for head and eye position (51–58, 61–64). 🧠
- **Core upper-face AUs.** AU1 is the inner brow raiser (medial frontalis), AU4 the brow lowerer (corrugator group) and AU6 the cheek raiser [1][2]. ✅ AU6 is produced by orbicularis oculi pars orbitalis, and AU12, the lip corner puller, by zygomaticus major [14]. 📄
- **Intensity is scored A–E,** appended to the AU number (for example 1E): A = trace, B = slight, C = marked/pronounced, D = severe/extreme, E = maximum possible *for that person* [1][5]. ✅ The scale is **not interval**: C and D each span a wider range of change than A, B or E [5]. 📄
- **Bilateral scoring.** When the two sides differ, FACS scores one intensity from the stronger side unless asymmetry is being coded [5]. 📄 Reliable coding needs agreement between at least two independent certified coders [5]. 📄
- **Canonical combinations.** Happiness = AU6+12 and sadness = AU1+4+15 [1]. 📄 Other commonly cited prototypes are surprise 1+2+5B+26, fear 1+2+4+5+7+20+26, anger 4+5+7+23, disgust 9+15+16 and contempt R12A+R14A (unilateral). 🧠
- **The Duchenne smile (AU6+12)** is often treated as a marker of genuine enjoyment, but the sources disagree [14][15]. ↔️ Two further problems: AU6 can be produced deliberately, and a strong AU12 by itself pushes the cheek up and bunches the lower lid, which mimics AU6. The manual warns coders about this. 🧠
- **One AU is not always one muscle.** Orbicularis oris alone drives AU18, 22, 23, 24 and 28 (and AU8). The two parts of orbicularis oculi split into AU6 (orbital) and AU7 (palpebral). Several AUs are *relaxations*: AU26 (jaw drop: masseter, temporalis and medial pterygoid relax), AU43 (eye closure: levator palpebrae relaxes) and partly AU25. 🧠
- **Muscle anatomy varies.** Risorius is absent or rudimentary in some people, and zygomaticus major is bifid in a minority. The bifid form is the usual explanation for cheek dimples. So an AU's surface signature varies between individuals even at the same coded intensity (Waller et al. 2008; Pessa et al. 1998). 🧠 See `anatomy/muscles-lower-face.md` for how the perioral muscles attach.
- **FACS requires a neutral baseline.** Coders score change relative to the person's neutral face, because permanent wrinkles, deep nasolabial folds, a low-set brow or a down-turned commissure can imitate AUs. This is the same reason identity capture needs a neutral face: resting morphology and active expression are visually confounded. 🧠
- **ARKit** returns `blendShapes`, a dictionary of named coefficients for specific facial features. The values are floats from 0 to 1 and update live [6][8]. 📄 The harvest did not confirm the full list of 52 names [7][12]. From expert knowledge, the list breaks down as 14 eye, 5 brow, 3 cheek, 2 nose, 4 jaw, 23 mouth and 1 tongue coefficient (table below). 🧠 In ARKit, "Left" means the *subject's* left. 🧠
- **MediaPipe Face Landmarker** outputs 478 3D landmarks per face plus 52 named blendshape scores in [0, 1], for example browDownLeft, jawOpen and eyeBlinkRight [9][11]. 📄 Blendshape output is off by default; turn it on with `output_face_blendshapes` [10]. 📄 Left/right labels refer to the subject's face, so a mirrored image swaps them [9]. 📄 The 478 landmarks are the 468-point Face Mesh plus 10 iris points. MediaPipe's 52 scores are ARKit's names minus `tongueOut`, plus a `_neutral` category at index 0. 🧠
- **Blendshape coefficients are not FACS intensities.** ARKit and MediaPipe values are regressor outputs that have not been calibrated against each other or against FACS letters. The same face gives different numbers in the two systems. Bilateral names do not always map one-to-one either: `browInnerUp` is a single coefficient even though AU1 can be scored unilaterally. 🧠

## Numbers & reference tables

### AU → muscle → surface change → blendshape equivalent

Muscle assignments follow the FACS manual tradition. The surface-change column is what a sculptor should see on the mesh. Unless a row cites a source, everything in it is 🧠.

| AU | Name | Muscle(s) | Surface change (sculpt cue) | ARKit / MediaPipe ≈ | Badge |
|---|---|---|---|---|---|
| 1 | Inner brow raiser | frontalis, pars medialis | medial brow up and oblique; horizontal forehead lines centred medially | browInnerUp | ✅ name [1][2]; rest 🧠 |
| 2 | Outer brow raiser | frontalis, pars lateralis | lateral brow arches up; lateral forehead lines; lateral upper-lid skin stretched | browOuterUp L/R | 🧠 |
| 4 | Brow lowerer | corrugator supercilii, depressor supercilii, procerus | brows down and together; vertical glabellar lines; horizontal line at nasal root; upper-lid fold covered | browDown L/R | ✅ name [1][2]; muscles 🧠 |
| 5 | Upper lid raiser | levator palpebrae superioris | aperture widens; sclera visible above iris; upper-lid fold shrinks | eyeWide | 🧠 |
| 6 | Cheek raiser | orbicularis oculi, pars orbitalis | infraorbital cheek lifts; lower lid bunches; crow's feet; eye narrows from below | cheekSquint | 📄 [14] |
| 7 | Lid tightener | orbicularis oculi, pars palpebralis | lids tense; lower lid straightens and rises; aperture narrows | eyeSquint | 🧠 |
| 9 | Nose wrinkler | levator labii superioris alaeque nasi | dorsal and root wrinkles ("bunny lines"); alae rise; medial brow pulled down; upper lip rises | noseSneer | 🧠 |
| 10 | Upper lip raiser | levator labii superioris | central upper lip up; upper nasolabial fold deepens; alae widen | mouthUpperUp | 🧠 |
| 11 | Nasolabial deepener | zygomaticus minor | middle nasolabial fold deepens | none | 🧠 |
| 12 | Lip corner puller | zygomaticus major | commissure pulled up, out and back; nasolabial fold deepens; cheek bulges; at D–E the eye narrows (mimics AU6) | mouthSmile | 📄 [14] |
| 13 | Sharp lip puller | levator anguli oris | corner rises steeply; cheek puffs beside it | none (partly mouthSmile) | 🧠 |
| 14 | Dimpler | buccinator | corners tighten and pull inward; dimple-like fold lateral to the corner | mouthDimple | 🧠 |
| 15 | Lip corner depressor | depressor anguli oris | corners down; lower lip flattens; bulge or fold below the corner (marionette area) | mouthFrown | 🧠 |
| 16 | Lower lip depressor | depressor labii inferioris | lower lip pulled down and out; lower teeth show | mouthLowerDown | 🧠 |
| 17 | Chin raiser | mentalis | chin boss pushed up; dimpled skin; lower lip protrudes; mentolabial sulcus reshapes | mouthShrugLower (+Upper) | 🧠 |
| 18 | Lip pucker | incisivus labii sup./inf. (orbicularis oris) | lips pushed forward and toward the midline | mouthPucker | 🧠 |
| 20 | Lip stretcher | risorius (+ platysma) | corners pulled laterally; mouth flattens and widens | mouthStretch | 🧠 |
| 22 | Lip funneler | orbicularis oris | lips everted into a funnel | mouthFunnel | 🧠 |
| 23 | Lip tightener | orbicularis oris | red lip narrows; rolled margin; no press | (mouthPress / mouthRoll, partial) | 🧠 |
| 24 | Lip pressor | orbicularis oris | lips pressed together; bulging above and below | mouthPress | 🧠 |
| 25 | Lips part | DLI, or mentalis / orbicularis oris relaxing | lips separate | jawOpen − mouthClose | 🧠 |
| 26 | Jaw drop | masseter, temporalis, medial pterygoid relax | mandible rotates down; lower face lengthens | jawOpen (low) | 🧠 |
| 27 | Mouth stretch | lateral pterygoid, digastric | wide forced opening; condyle translates | jawOpen (high) | 🧠 |
| 28 | Lip suck | orbicularis oris | lips drawn in over the teeth | mouthRollUpper/Lower | 🧠 |
| 29 / 30 | Jaw thrust / sideways | pterygoids | chin forward / to one side | jawForward, jawLeft/Right | 🧠 |
| 34 | Cheek puff | (air, AD) | cheeks inflate | cheekPuff | 🧠 |
| 19 | Tongue show | (AD) | tongue visible | tongueOut (ARKit only) | 🧠 |
| 43 / 45 / 46 | Eyes closed / blink / wink | levator palpebrae relaxes; orbicularis oculi | lid closure | eyeBlink L/R | 🧠 |
| 61–64 | Eyes left / right / up / down | extraocular | gaze direction | eyeLookIn/Out/Up/Down | 🧠 |

ARKit has no clean equivalent for AU11, AU13, AU21 (neck tightener, platysma), AU31 (jaw clencher, masseter) or AU38/39 (nostril dilator and compressor, nasalis). `mouthLeft/Right` and `mouthClose` have no single AU. 🧠 The 2002 revision reorganised the lid-droop codes (41, 42, 44). Check the manual before relying on them. ↔️

### FACS intensity scale and a suggested blendshape-weight mapping

| Code | Label [1][5] | Ordinal (0–5 convention, e.g. DISFA, OpenFace) | Suggested weight band (heuristic) | Badge |
|---|---|---|---|---|
| — | absent | 0 | 0–0.05 | 🧠 |
| A | trace | 1 | 0.05–0.15 | ✅ label; band 🧠 |
| B | slight | 2 | 0.15–0.35 | ✅ label; band 🧠 |
| C | marked/pronounced | 3 | 0.35–0.65 (wide [5]) | ✅ label; band 🧠 |
| D | severe/extreme | 4 | 0.65–0.90 (wide [5]) | ✅ label; band 🧠 |
| E | maximum for this person | 5 | 0.90–1.0 | ✅ label; band 🧠 |

The bands are a design choice that copies the manual's unequal widths [5]. They are not a FACS standard.

### ARKit 52 / MediaPipe 52

| Region | Count | Names (L/R pairs collapsed) | Badge |
|---|---|---|---|
| Eyes | 14 | eyeBlink, eyeLookDown, eyeLookIn, eyeLookOut, eyeLookUp, eyeSquint, eyeWide (each L/R) | 🧠 |
| Brows | 5 | browDown L/R, browInnerUp, browOuterUp L/R | 🧠 |
| Cheeks | 3 | cheekPuff, cheekSquint L/R | 🧠 |
| Nose | 2 | noseSneer L/R | 🧠 |
| Jaw | 4 | jawOpen, jawForward, jawLeft, jawRight | 🧠 |
| Mouth | 23 | mouthClose, mouthFunnel, mouthPucker, mouthLeft, mouthRight, mouthRollUpper, mouthRollLower, mouthShrugUpper, mouthShrugLower; mouthSmile, mouthFrown, mouthDimple, mouthStretch, mouthPress, mouthLowerDown, mouthUpperUp (each L/R) | 🧠 |
| Tongue | 1 | tongueOut (ARKit only; MediaPipe has `_neutral` in its place) | 🧠 |
| Value range | — | 0–1 floats (ARKit [6][8]); [0.0, 1.0] (MediaPipe [9][11]) | 📄 |

### Expression-model resources (time-sensitive: confirm versions and licences)

| Resource | What it gives | Key numbers | Badge |
|---|---|---|---|
| MediaPipe Face Landmarker | landmarks + blendshapes | 478 landmarks, 52 scores [9][11]; licence believed Apache-2.0 | 📄 / licence 🧠 |
| MediaPipe model input sizes | detector / landmarker | 192×192 or 128×128 detector, 256×256 landmarker [9][13] | ↔️ |
| FLAME (Li et al. 2017) | identity + expression + jaw/neck/eyeball joints | 5,023 vertices; 300 shape and 100 expression components | 🧠; licence ↔️ |
| FaceWarehouse (Cao et al. 2014) | bilinear identity × expression | 150 subjects × 20 expressions; FACS-like per-person blendshapes (~46) | 🧠 |
| DISFA (Mavadati et al. 2013) | AU intensity ground truth | 27 adults; 12 AUs; 0–5 | 🧠 |
| OpenFace 2.0 (Baltrušaitis et al. 2018) | AU detector | intensity for 17 AUs, presence for 18; academic licence | 🧠 |

### Jaw state (affects lower-face height in every photo)

| Quantity | Typical adult value | Badge |
|---|---|---|
| Interocclusal rest gap ("freeway space") | ~2–4 mm | 🧠 |
| Maximum voluntary interincisal opening | ~40–60 mm (below ~35–40 mm is usually called restricted) | 🧠 ↔️ |
| Opening that is mostly condylar rotation | first ~20–25 mm interincisal | 🧠 ↔️ |
| Incisor-to-condyle radius (derived) | ~90–110 mm, so a 3 mm rest gap ≈ 1.5–2° of rotation | 🧠 |

## Applying this to photo→3D face sculpting in Blender

**Capture protocol.** Ask for a *relaxed*, not suppressed, neutral. Lips lightly touching but not pressed (no AU23/24), teeth just apart and not clenched (no AU31 masseter bulge; see `anatomy/muscles-mastication-jaw.md`). Eyes open naturally on a target at lens height. Forehead slack. Use diffuse light so the subject does not squint (AU4/6/7). Shoot bursts and keep the most neutral frame. Photograph expressions (smile, brow raise, jaw open, pucker) as a *separate* set for rigging, and never feed them into the identity solve. In sequential multi-view capture, have the subject hold the same face and gaze between shots, because expression drift breaks triangulation.

**Screen every photo.** Run MediaPipe with `output_face_blendshapes` on each view [10]. Reject or tag a view when any of these heuristic thresholds (🧠, calibrate on your own data) is exceeded:

- mouthSmile > 0.25
- cheekSquint > 0.3
- eyeBlink > 0.4
- eyeWide > 0.3
- browInnerUp or browOuterUp > 0.3
- browDown > 0.35
- jawOpen > 0.08
- mouthPress, mouthRoll or mouthShrugLower > 0.3

A left/right blendshape difference that persists across all neutral frames points to structural asymmetry or habitual tone. One that appears in only one frame is expression. Never mirror the image before scoring [9].

**What leaks into identity if an expression is baked into the Basis mesh (🧠):**

| Leaked AU | Identity error | Fix |
|---|---|---|
| 12 (+6), slight smile | mouth too wide, nasolabial fold too deep, malar area too full and high, eyes too narrow | reject; or fit and remove AU12/6 and down-weight commissure and lower-lid landmarks |
| 1/2, brow raise | brows too high, forehead too short, upper-lid fold too small | reshoot relaxed; weight brow landmarks low |
| 4/7, squint at light | brows too low and close, palpebral fissure too short | diffuse lighting |
| 5, "camera eyes" | eyes too round, scleral show | settle the subject; take more frames |
| 25/26, lips apart | lower face too long, chin too low and retruded, lips thin | model jaw rotation explicitly |
| 17, mentalis strain (common with incompetent lips) | flat, pebbled chin; lower lip everted; shallow mentolabial sulcus | if it is habitual, it is identity: record it and sculpt it as a rest-state feature |
| 23/24, forced neutral | lips too thin, vermilion reduced | "let your lips go soft" |

**In Blender (🧠).** The Basis shape key is the neutral identity. Sculpt mode edits the *active* shape key, so make Basis active before identity work. Expression keys are deltas relative to Basis. Large identity edits made after the expression keys exist will distort those deltas, so rebuild them with deformation transfer from a generic FACS rig. Name expression keys with the ARKit-52 names so that existing ARKit and MediaPipe mocap pipelines can drive them. Use a jaw bone for openings beyond about AU26-B, because linear shape-key interpolation moves the chin along a straight line instead of an arc. Linear blendshape sums break down on combinations such as AU1+2+4, AU6+12 and AU12+26: add corrective keys driven by the product of their weights. Keep dynamic wrinkles as AU-driven normal maps rather than geometry: forehead lines (AU1/2), glabellar lines (AU4), crow's feet (AU6), bunny lines (AU9), perioral lines (AU18/22–24). Sculpt into Basis only the *static* lines that remain at rest.

## Algorithmic implications

- **State.** One identity vector β shared across all views. Per view v: an expression vector ψ_v ∈ [0,1]^K (K = 51–52, ARKit-named), jaw rotation θ_v about a TMJ hinge axis, head pose and camera. Fit β only through views tagged neutral. Expression views constrain the rig, not β.
- **Expression prior.** For views tagged neutral, use a half-normal on each ψ with σ ≈ 0.05–0.10 plus an L1 sparsity term. For expression views, use a weak prior (σ ≈ 0.5). For a sequential neutral set, add a cross-view consistency term ‖ψ_v − ψ̄‖ with σ ≈ 0.05. Box-constrain ψ to [0, 1]. All of these are 🧠 starting values; tune them.
- **Jaw prior** (neutral views, derived 🧠): θ ~ N(1.5°, 1°²), bounded to [0°, 30°]. Treat jawOpen = 1 as roughly the maximum voluntary opening. Rotation alone holds up to about 20–25 mm of interincisal opening; past that, add condylar translation.
- **Antagonist penalties only where co-activation is impossible.** That means eyeBlink against eyeWide on the same eye, jawLeft against jawRight, mouthLeft against mouthRight, and eyeLookIn against eyeLookOut. Do *not* penalise AU1+4 (sadness), AU5+7 (anger) or AU12+15, which are real combinations.
- **Expression-aware landmark weights in the identity solve (🧠 heuristic):**
  - Nasion, pronasale and endocanthion: 1.0. Tragion and ear points: 1.0.
  - Subnasale and alar points: 0.6 (they move under AU9/10).
  - Exocanthion: 0.7 (moves under AU6/7/12).
  - Gonion and menton: 0.5, rising to 1.0 once θ is modelled.
  - Labial points and stomion: 0.4.
  - Brow points: 0.3.
  - Cheilion: 0.3.
  - Eyelid margins: 0.2, and drop them for any view with eyeBlink > 0.4.
- **Initialisation.** Seed ψ_v from MediaPipe scores after a per-system calibration map. Never take them as ground truth: they are uncalibrated and can be biased by pose.
- **Deformation basis for template warping.** Define each AU on the template as a vertex mask plus a displacement field oriented along the muscle's line of action. For example, AU12 runs from the commissure toward the zygoma near the zygomaticotemporal suture, and AU15 from the commissure toward the mandibular oblique line. This gives an anatomically plausible low-dimensional expression subspace that can be projected out of the identity fit.
- **De-expression is a fallback.** Subtracting a fitted ψ cannot recover the soft-tissue folds and volume shifts that the expression produced. Prefer recapture, and flag any result built from a de-expressed photo with a lower confidence score.

## Disagreements, myths & open questions

- **AU count:** 44 versus about 30 muscular AUs [1][2]. ↔️ This is mostly a counting convention (whether ADs and position codes are included).
- **Duchenne smile as a genuine-enjoyment marker** is contested [14][15]. ↔️ The literature includes work showing that Duchenne smiles can be posed (Krumhuber & Manstead 2009). 🧠
- **Universality of basic-emotion prototypes** is disputed (Barrett et al. 2019). 🧠 For a sculpting tool this only affects "emotion presets", not geometry.
- **Myth: "ARKit blendshapes are FACS."** They are FACS-inspired tracking outputs, not FACS scores. 🧠
- **Myth: "neutral = zero muscle activity."** Resting tone and habitual activation (chronic AU4, mentalis strain) belong to the person's identity. What capture must avoid is *transient* activation. 🧠
- **Myth: "the AU14 dimpler makes cheek dimples."** Cheek dimples are usually attributed to a bifid zygomaticus major. 🧠
- **MediaPipe model input sizes** differ between Google's doc pages [9][13]. ↔️
- **Open questions:**
  - The verified ARKit 52-to-AU mapping and the ARKit left/right convention, from Apple's BlendShapeLocation pages [7].
  - The behaviour of MediaPipe's `_neutral` score.
  - The current FLAME and OpenFace licences.
  - How well blendshape scores from a still, non-frontal photo track true AU intensity.
  - Per-AU surface displacement in millimetres. No 4D-scan statistics were harvested (D3DFACS is the obvious source).

## Sources

[1] Facial Action Coding System (Wikipedia) — https://en.wikipedia.org/wiki/Facial_Action_Coding_System — encyclopedia — n.d.
[2] IEEE Technav: Action units — https://technav.ieee.org/topic/action-units/ — topic overview — n.d.
[3] Lancaster University psychology glossary: action unit — https://www.lancaster.ac.uk/fas/psych/glossary/action_unit/ — glossary — n.d.
[4] FACS Visual Reference (UCSD) — https://facsref.ucsd.edu/ — visual reference (surfaced, not read) — n.d.
[5] Scoring Upper Face Action Units (FACS manual excerpt, SlideShare copy) — https://pt.slideshare.net/wooo17/manual-1st — manual excerpt (third-party upload) — n.d.
[6] Apple ARKit: ARFaceAnchor.blendShapes — https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapes — official docs — n.d.
[7] Apple ARKit: ARFaceAnchor.BlendShapeLocation — https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapelocation — official docs — n.d.
[8] Apple Tech Talks 601: Face Tracking with ARKit — https://developer.apple.com/videos/play/tech-talks/601/ — official video — n.d.
[9] MediaPipe Face Landmarker (Google AI Edge) — https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker — official docs — n.d.
[10] MediaPipe Face landmark detection guide for Python — https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python — official docs — n.d.
[11] MediaPipe mp.tasks.vision.FaceLandmarkerResult API — https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/FaceLandmarkerResult — API reference — n.d.
[12] Apple Developer Forums thread 703686 (partial blendshape list) — https://developer.apple.com/forums/thread/703686 — forum — n.d.
[13] MediaPipe Face Landmarker (ai.google.dev page) — https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker — official docs — n.d.
[14] The Role of Facial Action Units in Investigating Facial Movements During Speech — https://pmc.ncbi.nlm.nih.gov/articles/PMC13229553/ — paper — n.d.
[15] A Psychological Guide to Upper Face Botulinum Toxin Injections: Baseline Emotional Functions of Facial Expressions — https://pmc.ncbi.nlm.nih.gov/articles/PMC12539761/ — paper — n.d.
[16] Facial Expressions as a Nexus for Health Assessment — https://pmc.ncbi.nlm.nih.gov/articles/PMC12938733/ — paper (surfaced; no facts extracted) — n.d.

**Further reading (by name, not yet linked)**
- Hjortsjö, *Man's Face and Mimic Language* (1969/1970)
- Ekman & Friesen, *Facial Action Coding System* (1978)
- Ekman, Friesen & Hager, *Facial Action Coding System: Manual and Investigator's Guide* (2002)
- Tian, Kanade & Cohn, "Recognizing Action Units for Facial Expression Analysis", IEEE TPAMI 2001
- Li, Bolkart, Black, Li & Romero, "Learning a model of facial shape and expression from 4D scans" (FLAME), SIGGRAPH Asia 2017
- Cao et al., "FaceWarehouse", IEEE TVCG 2014
- Cosker, Krumhuber & Hilton, D3DFACS, ICCV 2011
- Mavadati et al., "DISFA", IEEE Trans. Affective Computing 2013
- Baltrušaitis et al., "OpenFace 2.0", FG 2018
- Kartynnik et al., "Real-time Facial Surface Geometry from Monocular Video on Mobile GPUs", 2019
- Sumner & Popović, "Deformation Transfer for Triangle Meshes", SIGGRAPH 2004
- Lewis et al., "Practice and Theory of Blendshape Facial Models", Eurographics STAR 2014
- Waller, Cray & Burrows, "Selection for universal facial emotion", *Emotion* 2008
- Pessa et al., midfacial muscle variability in cadaver dissections, *Plast Reconstr Surg* 1998
- Krumhuber & Manstead, "Can Duchenne smiles be feigned?", *Emotion* 2009
- Barrett et al., "Emotional Expressions Reconsidered", *Psychological Science in the Public Interest* 2019
- Faigin, *The Artist's Complete Guide to Facial Expression* (1990)
- ICAO Doc 9303 / ISO/IEC 19794-5 (now 39794-5) portrait requirements for a neutral expression
