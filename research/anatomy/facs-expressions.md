# FACS action units and expression mechanics

> The Facial Action Coding System (FACS) codes every visible facial movement as a numbered action unit (AU), defined as the appearance change made by one muscle or a small muscle group. Intensity is scored from A (trace) to E (the person's maximum). For likeness work FACS does two jobs. It is the vocabulary behind the 52 ARKit/MediaPipe blendshape coefficients and most face rigs. It also predicts which identity features an expression corrupts when it leaks into a reference photo: brow height, lid aperture, nasolabial depth, mouth width, chin shape and lower-face height. So the identity mesh must be the subject's *relaxed* neutral, with no active AUs, the jaw at rest and the lips lightly sealed. A fitter cannot reliably separate a slight AU6+12 smile or an AU26 jaw drop from bone and soft-tissue shape.
>
> Evidence status: 10 ✅ / 19 📄 / 60 🧠 / 9 ↔️ — 🧠 items are queued for web verification.

## Key facts

- **What an AU is.** An AU is an elementary movement corresponding to the contraction (or relaxation) of one muscle or a small group of muscles [2][3]. ✅ FACS codes visible *appearance*, not muscle activity [1]. 📄
- **Lineage.** FACS grew out of Hjortsjö's work. Ekman and Friesen published it in 1978, and Ekman, Friesen and Hager substantially revised it in 2002 [1]. 📄
- **How many AUs.** One source counts 44 AUs (1978). Another counts about 30 numbered muscular units, plus separate descriptors for head pose, gaze and gross behaviour [1][2]. ↔️ The usual reconciliation: 44 codes in total, about 30 of them tied to specific muscles (12 upper-face, 18 lower-face) [17]. The rest are action descriptors (ADs) and head and eye position codes (51–58, 61–64). 📄
- **Core AUs.** AU1 is the inner brow raiser (medial frontalis), AU4 the brow lowerer (corrugator group) and AU6 the cheek raiser [1][2]. ✅ AU6 = orbicularis oculi pars orbitalis; AU12, the lip corner puller, = zygomaticus major [14]. 📄
- **Intensity A–E** is appended to the AU number (for example 1E): A = trace, B = slight, C = marked, D = severe, E = maximum *for that person* [1][5]. ✅ The scale is not interval: C and D each cover more change than A, B or E [5]. 📄
- **Asymmetry and reliability.** When the two sides differ, FACS scores the stronger side unless asymmetry is being coded [5]. 📄 Reliable coding needs at least two independent certified coders [5]. 📄
- **Prototypes.** Happiness = AU6+12; sadness = AU1+4+15 [1]. 📄 Other commonly cited prototypes: surprise 1+2+5B+26, fear 1+2+4+5+7+20+26, anger 4+5+7+23, disgust 9+15+16, contempt unilateral 12A+14A. 🧠
- **The Duchenne smile (AU6+12) as a sign of genuine enjoyment is contested** [14][15]. ↔️ A strong AU12 alone lifts the cheek and bunches the lower lid, mimicking AU6; this is a classic coding trap. 🧠
- **One AU is not always one muscle.** Orbicularis oris drives AU8, 18, 22, 23, 24 and 28. Orbicularis oculi splits into AU6 (orbital part) and AU7 (palpebral part). Some AUs are *relaxations*: AU26 (masseter, temporalis and medial pterygoid relax), AU43 (levator palpebrae relaxes) and partly AU25. 🧠
- **Muscle anatomy varies.** Risorius is absent in some people and zygomaticus major is bifid in a minority (the usual explanation for cheek dimples), so the same coded intensity looks different on different faces. 🧠 See `anatomy/muscles-lower-face.md`.
- **FACS needs each person's neutral face as a baseline.** Permanent wrinkles, a deep nasolabial fold, a low brow or a down-turned commissure can imitate AUs. This is the same confound that makes neutral capture essential for identity. 🧠
- **ARKit** gives `blendShapes` as named coefficients, floats from 0 to 1, updated live [6][8]. 📄 The harvest could not confirm the full 52-name list [7][12]. From expert knowledge the list breaks down as 14 eye, 5 brow, 3 cheek, 2 nose, 4 jaw, 23 mouth and 1 tongue coefficient. "Left" means the subject's left. 🧠
- **MediaPipe Face Landmarker** outputs 478 3D landmarks plus 52 named blendshape scores in [0, 1] [9][11]. 📄 Blendshapes are off by default; enable them with `output_face_blendshapes` [10]. 📄 Left/right labels are the subject's, so a mirrored input swaps them [9]. 📄 The 478 points are the 468-point Face Mesh plus 10 iris points. The 52 scores are ARKit's names minus `tongueOut`, plus a `_neutral` category at index 0. 🧠
- **Blendshape coefficients are not FACS intensities.** They are uncalibrated regressor outputs that differ between ARKit and MediaPipe for the same face, and `browInnerUp` is a single coefficient although AU1 can be unilateral. 🧠

## Numbers & reference tables

### AU → muscle → surface change → blendshape

Muscle assignments follow the FACS manual tradition. Everything in a row is 🧠 unless that row cites a source.

| AU | Name | Muscle(s) | Surface change (sculpt cue) | ARKit / MediaPipe ≈ | Badge |
|---|---|---|---|---|---|
| 1 | Inner brow raiser | frontalis, medial | medial brow up and oblique; central forehead lines | browInnerUp | ✅ [1][2] |
| 2 | Outer brow raiser | frontalis, lateral | lateral brow arches; lateral forehead lines | browOuterUp L/R | 🧠 |
| 4 | Brow lowerer | corrugator, depressor supercilii, procerus | brows down and in; vertical glabellar lines; nasal-root line; lid fold hidden | browDown L/R | ✅ name [1][2] |
| 5 | Upper lid raiser | levator palpebrae superioris | sclera visible above the iris; lid fold shrinks | eyeWide | 🧠 |
| 6 | Cheek raiser | orbicularis oculi, orbital part | cheek lifts; lower lid bunches; crow's feet | cheekSquint | 📄 [14] |
| 7 | Lid tightener | orbicularis oculi, palpebral part | lower lid straightens and rises | eyeSquint | 🧠 |
| 9 | Nose wrinkler | levator labii sup. alaeque nasi | nasal dorsum lines; alae up; medial brow down | noseSneer | 🧠 |
| 10 | Upper lip raiser | levator labii superioris | central upper lip up; upper nasolabial fold deepens | mouthUpperUp | 🧠 |
| 11 | Nasolabial deepener | zygomaticus minor | middle nasolabial fold deepens | — | 🧠 |
| 12 | Lip corner puller | zygomaticus major | corner up, out and back; nasolabial fold deepens; cheek bulge; eye narrows at D–E | mouthSmile | 📄 [14] |
| 13 | Sharp lip puller | levator anguli oris | steep corner lift; puff beside the corner | — | 🧠 |
| 14 | Dimpler | buccinator | corners tighten inward; fold lateral to the corner | mouthDimple | 🧠 |
| 15 | Lip corner depressor | depressor anguli oris | corners down; bulge in the marionette area | mouthFrown | 🧠 |
| 16 | Lower lip depressor | depressor labii inferioris | lower lip down and out; lower teeth show | mouthLowerDown | 🧠 |
| 17 | Chin raiser | mentalis | chin boss up and dimpled; lower lip pushed out | mouthShrugLower (+Upper) | 🧠 |
| 18 | Lip pucker | incisivus labii (orbicularis oris) | lips forward and toward the midline | mouthPucker | 🧠 |
| 20 | Lip stretcher | risorius (+ platysma) | corners lateral; mouth flattens | mouthStretch | 🧠 |
| 22 | Lip funneler | orbicularis oris | lips everted into a funnel | mouthFunnel | 🧠 |
| 23 | Lip tightener | orbicularis oris | red lip narrows; margins roll | partial (mouthPress/Roll) | 🧠 |
| 24 | Lip pressor | orbicularis oris | lips pressed; bulge above and below | mouthPress | 🧠 |
| 25 | Lips part | DLI, or mentalis/orbicularis oris relaxing | lips separate | jawOpen − mouthClose | 🧠 |
| 26 | Jaw drop | masticators relax | mandible rotates; lower face lengthens | jawOpen (low) | 🧠 |
| 27 | Mouth stretch | lateral pterygoid, digastric | forced wide opening; condyle translates | jawOpen (high) | 🧠 |
| 28 | Lip suck | orbicularis oris | lips drawn over the teeth | mouthRollUpper/Lower | 🧠 |
| 29/30, 34, 19 | Jaw thrust/sideways, cheek puff, tongue show | pterygoids; ADs | — | jawForward, jawLeft/Right, cheekPuff, tongueOut | 🧠 |
| 43/45/46 | Eyes closed / blink / wink | levator relaxes; orbicularis oculi | lid closure | eyeBlink L/R | 🧠 |
| 61–64 | Eye position codes | extraocular muscles | gaze | eyeLookIn/Out/Up/Down | 🧠 |

ARKit has no clean equivalent for AU11, AU13, AU21 (platysma), AU31 (masseter clench) or AU38/39 (nostril dilate/compress). 🧠 The 2002 revision reorganised the lid-droop codes (41, 42, 44). Check the manual before relying on them. ↔️

### Intensity scale and suggested weight mapping

| Code | Label [1][5] | Ordinal (0–5, as in DISFA/OpenFace) | Suggested blendshape-weight band | Badge |
|---|---|---|---|---|
| — | absent | 0 | 0–0.05 | 🧠 |
| A | trace | 1 | 0.05–0.15 | ✅ label; band 🧠 |
| B | slight | 2 | 0.15–0.35 | ✅ label; band 🧠 |
| C | marked | 3 | 0.35–0.65 (wide [5]) | ✅ label; band 🧠 |
| D | severe | 4 | 0.65–0.90 (wide [5]) | ✅ label; band 🧠 |
| E | person's maximum | 5 | 0.90–1.0 | ✅ label; band 🧠 |

The bands are a design choice that copies the manual's unequal widths. They are not a FACS standard.

### ARKit 52 / MediaPipe 52

| Region | Count | Names (each "L/R" is a pair) | Badge |
|---|---|---|---|
| Eyes | 14 | eyeBlink, eyeLookDown, eyeLookIn, eyeLookOut, eyeLookUp, eyeSquint, eyeWide — all L/R | 🧠 |
| Brows | 5 | browDown L/R, browInnerUp, browOuterUp L/R | 🧠 |
| Cheeks, nose | 3 + 2 | cheekPuff, cheekSquint L/R; noseSneer L/R | 🧠 |
| Jaw | 4 | jawOpen, jawForward, jawLeft, jawRight | 🧠 |
| Mouth | 23 | mouthClose, mouthFunnel, mouthPucker, mouthLeft, mouthRight, mouthRollUpper/Lower, mouthShrugUpper/Lower; mouthSmile, mouthFrown, mouthDimple, mouthStretch, mouthPress, mouthLowerDown, mouthUpperUp — the last seven L/R | 🧠 |
| Tongue | 1 | tongueOut (ARKit only; MediaPipe has `_neutral` instead) | 🧠 |
| Range | — | 0–1 (ARKit [6][8]; MediaPipe [9][11]) | 📄 |

### Expression resources and jaw numbers (time-sensitive: confirm)

| Item | Value | Badge |
|---|---|---|
| MediaPipe Face Landmarker | 478 landmarks, 52 scores [9][11]; licence believed Apache-2.0 | 📄 / licence 🧠 |
| MediaPipe input sizes | detector 192² or 128², landmarker 256² [9][13] | ↔️ |
| FLAME (Li et al. 2017) | 5,023 vertices [18]; 300 shape and 100 expression components (project site viewer, not tied to a release); jaw, neck and eye joints; versions 2017/2019/2020/2023 under a non-commercial Academic Model License; a separate FLAME 2023 Open model is CC-BY-4.0 and allows commercial use [19] (corrected in verification) | 📄 vertices and licence; components 🧠 |
| DISFA | 27 adults, 12 AUs, intensity 0–5 | 🧠 |
| OpenFace 2.0 | academic/non-profit non-commercial research licence [24][25]; intensity for 17 AUs (a fork lists AU 1, 2, 4, 5, 6, 7, 9, 10, 12, 14, 15, 17, 20, 23, 25, 26, 45); presence for 18 unconfirmed | 📄 licence; counts 🧠 |
| Interocclusal rest gap ("freeway space") | ~2–4 mm [20] | 📄 |
| Maximum interincisal opening | ~30–55 mm: 30–50 [21], 40–55 [22], adult means 44 (women) to 51 mm (men) [23] | ↔️ |
| Opening that is mainly rotation | first ~20–25 mm | 🧠 ↔️ |
| Incisor-to-condyle radius | ~90–110 mm, so a 3 mm gap ≈ 1.5–2° (derived) | 🧠 |

## Applying this to photo→3D face sculpting in Blender

**Capture.** Ask for a *relaxed* neutral, not a suppressed one:

- Lips touching but not pressed (no AU23/24).
- Teeth just apart, not clenched. A clench bulges the masseter (AU31); see `anatomy/muscles-mastication-jaw.md`.
- Eyes open naturally on a target at lens height; forehead slack.
- Diffuse light, so the subject does not squint (AU4/6/7).
- Shoot bursts and keep the most neutral frame.
- Shoot expressions (smile, brow raise, jaw open, pucker) as a separate rig set. Never put them in the identity solve.
- In sequential multi-view capture, have the subject hold face and gaze between shots, because drift breaks triangulation.

**Screen.** Run MediaPipe blendshapes on every view [10]. Tag a view as non-neutral if any heuristic limit is exceeded (🧠, calibrate on your own data):

| Score | Limit |
|---|---|
| mouthSmile | 0.25 |
| cheekSquint, eyeWide, browInnerUp, browOuterUp | 0.3 |
| browDown | 0.35 |
| eyeBlink | 0.4 |
| jawOpen | 0.08 |
| mouthPress, mouthRoll, mouthShrugLower | 0.3 |

A left/right difference that persists across neutral frames is structure or habitual tone. A difference that appears in one frame only is expression. Never mirror the input [9].

**What a leaked expression does to identity (🧠):**

| Leaked AU | Identity error | Fix |
|---|---|---|
| 12 (+6) | mouth too wide, nasolabial fold too deep, malar area too full, eyes narrow | reject, or fit, remove and down-weight corners and lower lids |
| 1/2 | brows high, forehead short, lid fold small | reshoot; low brow weights |
| 4/7 | brows low and close, short palpebral fissure | diffuse light |
| 5 | eyes too round | settle the subject; more frames |
| 25/26 | lower face long, chin low and retruded, lips thin | model jaw rotation |
| 17 | flat, pebbled chin; everted lower lip | if habitual (lip incompetence), it *is* identity: sculpt it as rest state |
| 23/24 | lips thin | "let your lips go soft" |

**In Blender (🧠):**

- The Basis shape key is the neutral identity. Sculpt mode edits the *active* key, so make Basis active before identity work.
- Name expression keys with the ARKit-52 names so ARKit and MediaPipe mocap can drive them.
- Big identity edits distort existing expression deltas. Regenerate the keys by deformation transfer from a generic FACS rig.
- Use a jaw bone beyond about AU26-B, because shape-key interpolation moves the chin in a straight line, not an arc.
- Add correctives for non-additive combinations (AU1+2+4, AU6+12, AU12+26), driven by the product of their weights.
- Keep dynamic wrinkles as AU-driven normal maps: forehead lines (AU1/2), glabellar lines (AU4), crow's feet (AU6), bunny lines (AU9), perioral lines (AU18/22–24). Sculpt only the static lines that remain at rest into Basis.

## Algorithmic implications

- **State.** One identity vector β shared across views. Per view: expression ψ_v ∈ [0,1]^K (K = 51–52, ARKit-named), jaw angle θ_v about a TMJ hinge, head pose and camera. Only views tagged neutral constrain β.
- **Priors** (🧠 starting values):
  - Neutral views: half-normal on ψ with σ ≈ 0.05–0.10, plus an L1 sparsity term.
  - Expression views: σ ≈ 0.5.
  - Sequential neutral sets: cross-view term ‖ψ_v − ψ̄‖ with σ ≈ 0.05.
  - Jaw, neutral views (derived): θ ~ N(1.5°, 1°²), bounded to [0°, 30°]. Above about 20–25 mm of interincisal opening, add condylar translation. Treat jawOpen = 1 as roughly the maximum opening.
- **Antagonist penalties only where co-activation is impossible.** That means eyeBlink against eyeWide on the same eye, jawLeft against jawRight, mouthLeft against mouthRight, and eyeLookIn against eyeLookOut on the same eye. Do *not* penalise AU1+4, AU5+7 or AU12+15, which are real combinations (sadness, anger, suppressed smile).
- **Expression-aware landmark weights for the identity solve** (🧠 heuristic):
  - Nasion, pronasale, endocanthion and ear points: 1.0.
  - Exocanthion: 0.7.
  - Subnasale and alae: 0.6.
  - Gonion and menton: 0.5, rising to 1.0 once θ is modelled.
  - Lips and stomion: 0.4.
  - Brows and cheilion: 0.3.
  - Lid margins: 0.2, dropped entirely when eyeBlink > 0.4.
- **Initialise, don't trust.** Seed ψ_v from MediaPipe through a per-system calibration map. The scores are uncalibrated and pose-sensitive.
- **Template AU basis.** Define each AU on the template as a vertex mask plus a displacement field along the muscle's line of action. AU12 runs from the commissure toward the zygoma; AU15 from the commissure toward the mandibular oblique line. This gives an anatomical expression subspace that can be projected out of the identity fit.
- **De-expression is a fallback.** Subtracting ψ cannot restore the folds and volume shifts the expression created. Recapture instead, and lower the confidence score on any result built from a de-expressed photo.

## Disagreements, myths & open questions

- **AU count:** 44 against about 30 [1][2]. ↔️ The difference is mostly whether ADs and position codes are counted.
- **Duchenne smile as a genuine-enjoyment marker:** contested [14][15]. ↔️ Duchenne smiles can be posed (Krumhuber & Manstead 2009). 🧠
- **Universal basic-emotion prototypes:** disputed (Barrett et al. 2019). 🧠 This affects emotion presets, not geometry.
- **Myth: "ARKit blendshapes are FACS."** They are FACS-inspired tracking outputs. 🧠
- **Myth: "neutral = zero muscle activity."** Resting tone and habitual activation (chronic AU4, mentalis strain) belong to identity. Capture must avoid only *transient* activation. 🧠
- **Myth: "AU14 makes cheek dimples."** Cheek dimples are usually attributed to a bifid zygomaticus major. 🧠
- **MediaPipe input sizes** differ between Google's pages [9][13]. ↔️
- **Open questions:**
  - The verified ARKit-to-AU mapping and left/right convention [7].
  - The behaviour of MediaPipe's `_neutral` score.
  - The current FLAME and OpenFace licences.
  - How well blendshape scores from a still, non-frontal photo track AU intensity.
  - Per-AU surface displacement in mm. No 4D-scan statistics were harvested; D3DFACS is the obvious source.

## Sources

[1] Facial Action Coding System (Wikipedia) — https://en.wikipedia.org/wiki/Facial_Action_Coding_System — encyclopedia — n.d.
[2] IEEE Technav: Action units — https://technav.ieee.org/topic/action-units/ — topic overview — n.d.
[3] Lancaster University psychology glossary: action unit — https://www.lancaster.ac.uk/fas/psych/glossary/action_unit/ — glossary — n.d.
[4] FACS Visual Reference (UCSD) — https://facsref.ucsd.edu/ — visual reference (surfaced, not read) — n.d.
[5] Scoring Upper Face Action Units (FACS manual excerpt, SlideShare copy) — https://pt.slideshare.net/wooo17/manual-1st — manual excerpt — n.d.
[6] Apple ARKit: ARFaceAnchor.blendShapes — https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapes — official docs — n.d.
[7] Apple ARKit: ARFaceAnchor.BlendShapeLocation — https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapelocation — official docs — n.d.
[8] Apple Tech Talks 601: Face Tracking with ARKit — https://developer.apple.com/videos/play/tech-talks/601/ — official video — n.d.
[9] MediaPipe Face Landmarker (Google AI Edge) — https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker — official docs — n.d.
[10] MediaPipe Face landmark detection guide for Python — https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python — official docs — n.d.
[11] MediaPipe FaceLandmarkerResult API — https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/FaceLandmarkerResult — API reference — n.d.
[12] Apple Developer Forums thread 703686 — https://developer.apple.com/forums/thread/703686 — forum — n.d.
[13] MediaPipe Face Landmarker (ai.google.dev) — https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker — official docs — n.d.
[14] The Role of Facial Action Units in Investigating Facial Movements During Speech — https://pmc.ncbi.nlm.nih.gov/articles/PMC13229553/ — paper — n.d.
[15] A Psychological Guide to Upper Face Botulinum Toxin Injections — https://pmc.ncbi.nlm.nih.gov/articles/PMC12539761/ — paper — n.d.
[17] Tian, Kanade & Cohn, Recognizing Action Units for Facial Expression Analysis (CMU RI copy) — https://www.ri.cmu.edu/pub_files/pub3/cohn_jeffrey_2001_1/cohn_jeffrey_2001_1.pdf — paper — 2001
[18] CVTHead: One-shot Controllable Head Avatar with Vertex-feature Transformer — https://arxiv.org/pdf/2311.06443 — paper — 2023
[19] FLAME model license (MPI-IS) — https://flame.is.tue.mpg.de/modellicense.html — official licence page — n.d.
[20] Complete Rehabilitation of a Patient with Occlusal Wear: A Case Report — https://pmc.ncbi.nlm.nih.gov/articles/PMC3416936/ — paper — n.d.
[21] Surgical Treatment of Mandibular Coronoid Process Hypertrophy Syndrome — https://pmc.ncbi.nlm.nih.gov/articles/PMC12295069 — paper — n.d.
[22] Arthrocentesis vs other modalities in TMD, systematic review — https://pmc.ncbi.nlm.nih.gov/articles/PMC13094472/ — paper — n.d.
[23] Normal Mouth Opening in an Adult Indian Population — https://pmc.ncbi.nlm.nih.gov/articles/PMC3428458/ — paper — n.d.
[24] OpenFace Copyright.txt (academic/non-profit noncommercial research use only) — https://github.com/TadasBaltrusaitis/OpenFace/blob/master/Copyright.txt — licence — n.d.
[25] OpenFace repository (CMU commercial licensing pointer) — https://github.com/TadasBaltrusaitis/OpenFace — official repo — n.d.
[16] Facial Expressions as a Nexus for Health Assessment — https://pmc.ncbi.nlm.nih.gov/articles/PMC12938733/ — paper (surfaced; nothing extracted) — n.d.

**Further reading (by name, not yet linked)**
- Hjortsjö, *Man's Face and Mimic Language* (1969/70)
- Ekman & Friesen, *Facial Action Coding System* (1978)
- Ekman, Friesen & Hager, *FACS Manual and Investigator's Guide* (2002)
- Tian, Kanade & Cohn, "Recognizing Action Units for Facial Expression Analysis", TPAMI 2001
- Li et al., FLAME, SIGGRAPH Asia 2017
- Cosker, Krumhuber & Hilton, D3DFACS, ICCV 2011
- Mavadati et al., DISFA, IEEE TAC 2013
- Baltrušaitis et al., OpenFace 2.0, FG 2018
- Sumner & Popović, "Deformation Transfer for Triangle Meshes", SIGGRAPH 2004
- Lewis et al., "Practice and Theory of Blendshape Facial Models", Eurographics STAR 2014
- Waller, Cray & Burrows, "Selection for universal facial emotion", *Emotion* 2008
- Krumhuber & Manstead, "Can Duchenne smiles be feigned?", *Emotion* 2009
- Barrett et al., "Emotional Expressions Reconsidered", PSPI 2019
- Faigin, *The Artist's Complete Guide to Facial Expression* (1990)
- ICAO Doc 9303 / ISO/IEC 19794-5 (now 39794-5): neutral-expression portrait rules

## Verification log (2026-11-20)

- ARKit exposes exactly 52 names (14/5/3/2/4/23/1), Left = subject's left, AU mapping: **unconfirmed**. Apple pages surfaced (cheekSquintLeft etc.) but no full list or convention was retrieved. https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapelocation
- MediaPipe 52 = ARKit minus tongueOut plus `_neutral` at index 0: **unconfirmed** (names are camelCase like ARKit; `_neutral` not found). Left/right = subject's side is stated by Google. https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker
- FLAME 5,023 vertices: **confirmed** (one source) https://arxiv.org/pdf/2311.06443 ; 300 shape/100 expression: **unconfirmed** for a specific release (project site mentions 300/100 viewer only). Licence: **corrected/updated**: 2017-2023 academic models are non-commercial; FLAME 2023 Open is CC-BY-4.0 and allows commercial use. https://flame.is.tue.mpg.de/modellicense.html
- FACS 44 AUs, ~30 muscle-tied (12 upper, 18 lower): **confirmed** (one source, 2001, pre-2002 revision) https://www.ri.cmu.edu/pub_files/pub3/cohn_jeffrey_2001_1/cohn_jeffrey_2001_1.pdf ; 2002 reorganisation of AU41/42/44 and the specific muscle assignments (AU13, 14, 20): **unconfirmed**.

## Verification log, pass 2 (2026-11-20)

- Freeway space ~2-4 mm: **confirmed** (one source) https://pmc.ncbi.nlm.nih.gov/articles/PMC3416936/
- Maximum interincisal opening ~40-60 mm: **contested**, range ~30-55 mm (30-50, 40-55; adult means 44-51 mm). https://pmc.ncbi.nlm.nih.gov/articles/PMC12295069 ; https://pmc.ncbi.nlm.nih.gov/articles/PMC13094472/ ; https://pmc.ncbi.nlm.nih.gov/articles/PMC3428458/
- Rotation-only first 20-25 mm and the N(1.5 deg, 1 deg^2) prior: **unconfirmed** (no condylar kinematics numbers found; prior is derived).
- OpenFace 2.0 academic non-commercial licence: **confirmed** (one source) https://github.com/TadasBaltrusaitis/OpenFace/blob/master/Copyright.txt ; 17 AUs intensity: only a fork's doc listing was surfaced, presence for 18: **unconfirmed**.
- MediaPipe Apache-2.0: **unconfirmed** (no result tied to a URL).
