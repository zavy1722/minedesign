# Face & head anatomy for likeness

This area holds the anatomy a sculptor or a fitting engine needs to turn photos of a consenting person into a likeness-accurate, anatomically correct, sculpt-ready 3D head in Blender. Its 26 topic notes cover the skull and soft-tissue depth, landmarks and norms, the eye, nose, mouth, jaw, ear, forehead and their muscles, fat compartments and ligaments, skin detail, expression coding, asymmetry, sex, age, growth and population variation, and the psychology of what makes a likeness read.

The common thread is a reversal. Anatomy texts and forensic tables run from bone outward and describe the average. Photo-based likeness runs from the photographed skin inward, and the likeness lives in how this person *differs* from the average. In this library, anatomy has three jobs:

1. tell the solver what the photos cannot see (bone under thick tissue, depth in a frontal-only set, the back of the head);
2. flag measurements that are probably errors of camera, landmark or definition;
3. tell the artist where form comes from, so a sculpt is built in the right order and does not drift toward a generic face.

Engine-facing requirements (priors with σ, data formats, failure modes, licences) are condensed in [`../_raw/requirements_anatomy.md`](../_raw/requirements_anatomy.md).

## Contents

1. [How to use this area](#how-to-use-this-area)
2. [Core principles](#core-principles)
3. [Quick-reference tables](#quick-reference-tables)
4. [Blender checklist](#blender-checklist)
5. [Cross-topic contradictions and how to resolve them](#cross-topic-contradictions-and-how-to-resolve-them)
6. [Index of topic notes](#index-of-topic-notes)

## How to use this area

**Evidence badges.** Every claim in the notes carries one badge, and this README keeps it:

| Badge | Meaning | How to treat it |
|---|---|---|
| ✅ | Two or more independent sources agree | Usable default |
| 📄 | One source | Usable with its population and method attached |
| 🧠 | Expert knowledge, not yet source-checked | Provisional: a tunable default, a sanity range or a sculpting heuristic, never a constant |
| ↔️ | Contested | Encode the range, not a point; read the note's disagreement section |

Across the 26 notes the tally is **217 ✅ / 579 📄 / 1,555 🧠 / 514 ↔️**: 72% of claims are unverified or contested. Most numbers here are therefore working defaults. The best-supported material is soft-tissue depth at thin midline points, landmark definitions, eye and cornea dimensions, masseter thickness, Hertel norms and the failure of the canons.

**Verification logs win.** Each note ends with a "Verification log" in which a fact-checker confirmed or corrected claims. Corrections in the log override the original text, and this README and the requirements digest already apply them, for example the supraorbital tissue depth (5.7–6.7 mm, not 6–9), resting incisor display by age, Hertel upper limits, canthal height (2–4 mm) and the FLAME licence. Where a note's body or data file still carries a pre-correction value, the conflict is listed under [contradictions](#cross-topic-contradictions-and-how-to-resolve-them).

**Conventions.**
- Distances are in millimetres and angles in degrees.
- Head frame: +x is the subject's left, +y up, +z forward, levelled to the Frankfort horizontal (FH: porion–orbitale on bone, tragion–soft-tissue orbitale on the living). The Blender mapping is (x, y, z) → (x, −z, y), with the face looking down −Y and `.L` on +X ([craniometric-landmarks](./craniometric-landmarks.md)).
- "Left" and "right" always mean the subject's side.
- Landmark abbreviations follow Farkas: en/ex inner and outer eye corners, al nose wing, ch mouth corner, sn subnasale, prn nose tip, sto stomion, n nasion, g glabella, pg pogonion, me menton, zy zygion, go gonion, t tragion, tr trichion, v vertex. A prime (n′) marks the skin point over a bony one. Farkas "gn" is the *lowest* chin point, which cephalometrists call menton.

**Reading paths.**
- *Artist new to the area:* [face-perception-likeness](./face-perception-likeness.md) → [skull-osteology](./skull-osteology.md) → [soft-tissue-thickness](./soft-tissue-thickness.md) → the feature notes (eye, nose, mouth, jaw, ear, forehead) → [facial-asymmetry](./facial-asymmetry.md) → [aging-face](./aging-face.md). Then work through the [Blender checklist](#blender-checklist).
- *Engineer:* [craniometric-landmarks](./craniometric-landmarks.md) → [anthropometric-norms](./anthropometric-norms.md) → [soft-tissue-thickness](./soft-tissue-thickness.md) → [facial-asymmetry](./facial-asymmetry.md) → [facs-expressions](./facs-expressions.md) → [population-variation](./population-variation.md) → [sexual-dimorphism](./sexual-dimorphism.md), then the requirements digest. Machine-readable tables are in `research/data/<topic>.json` as `{topic, tables: [{name, units, columns, rows, population, source_urls}]}`.

## Core principles

**Likeness and priors**

1. **Likeness lives in the deviations from the average.** Faces are coded relative to a norm, caricatures are recognised as well as or better than accurate drawings, and averaging makes a face more attractive and less identifiable 🧠. Any statistical prior shrinks the sitter's deviation by k = σp²/(σp² + σd²), which works as an anti-caricature (exact arithmetic). A frontal-only fit keeps roughly 20–40% of the projection deviation 🧠. → [face-perception-likeness](./face-perception-likeness.md), [facial-proportions-canons](./facial-proportions-canons.md)
2. **Norms are gates and gap-fillers, never targets.** Use them for scale, sanity z-scores and unseen parts; with landmarks seen in two or more pose-solved views, cap the prior at about 10–20% of the objective 🧠. A |z| above 3 is almost always a landmark, focal-length or definition error, so fix the cause rather than sculpting toward the mean 🧠. → [anthropometric-norms](./anthropometric-norms.md), [population-variation](./population-variation.md)
3. **The neoclassical canons fail most people, and the golden ratio has no support.** Most adults in every tested population fail most canons ✅. The best one, the orbital canon (en–en = ex–en), held in only 30.6% of African American women ✅. No evidence supports φ as a facial ideal ✅. Canons are block-out scaffolding and labelled guesses for hidden parts; φ terms never enter a likeness pipeline. → [facial-proportions-canons](./facial-proportions-canons.md)
4. **Get the perceptually heavy cues right first.** Eyelids, then brows, then lips carry the most identity weight; removing the brows hurt celebrity recognition more than removing the eyes 📄. Identity relies on roughly 8–16 cycles per face width 📄, which on a 140 mm face is 9–18 mm form: orbit depth, lid and brow masses, nose and lip volumes, cheek planes 🧠. Pores are not in that band. → [face-perception-likeness](./face-perception-likeness.md)
5. **People who know the sitter are the only reliable judges.** Unfamiliar viewers, the artist included, err on 10–30% of identity matches ↔️. The sitter is biased toward their mirror image and toward enhanced versions of themselves 🧠. Judge multi-view renders with eyes, brows and a hair cap in place. → [face-perception-likeness](./face-perception-likeness.md), [facial-asymmetry](./facial-asymmetry.md)

**Frame, camera and measurement**

6. **Every landmark needs one explicit definition.** Gonion has three constructions, gnathion two (cephalometric midpoint vs Farkas lowest point), and subnasale, labiale superius, stomion and soft-tissue nasion have competing variants ↔️. Detector schemes are annotation conventions: dlib jaw points 0–16 and brow points are spaced contour samples, never gonion or glabella 📄. Store the variant and never compare across variants. → [craniometric-landmarks](./craniometric-landmarks.md)
7. **Solve the cameras and level the head before measuring anything.** Most landmarks are extremal ("most anterior", "lowest"), so they exist only in a fixed frame, and a tilt θ slides them by about R·θ 🧠. Pitch changes forehead slope one for one, and a 10° nod moves the ears about 17 mm against the brow 🧠. → [craniometric-landmarks](./craniometric-landmarks.md), [ear](./ear.md), [forehead-brow-temple-hairline](./forehead-brow-temple-hairline.md)
8. **Distance, not focal length, sets perspective** ✅, so shoot at 1.5 m or more with an 85–135 mm-equivalent lens 🧠. A nose tip about 100 mm nearer the lens than the ears is magnified by (d + 100)/d: ≈20% at 0.5 m and ≈5% at 2 m 🧠. The nose and ears suffer most. → [nose](./nose.md), [facial-proportions-canons](./facial-proportions-canons.md), [ear](./ear.md)
9. **The iris is the best single-photo ruler, and a caliper beats everything.** The pooled corneal diameter is 11.84 mm (SD 0.79) ✅, with single-device SDs of 0.36–0.43 mm. One caliper distance on the sitter (error ≈0.5 mm) fixes scale better than any norm 🧠. Never take scale from hair landmarks (trichion, vertex). → [eye-region](./eye-region.md), [anthropometric-norms](./anthropometric-norms.md)

**Bone and soft tissue**

10. **Bone reads through skin only where the cover is thin.** Pooled depths are glabella 5.5, nasion 6.0 ✅ and rhinion 3.0 mm 📄, against 15–25 mm over the cheek and masseter 🧠. So the forehead → glabella → nasion → rhinion profile must follow bone to about 1 mm, while thick zones follow fat, muscle, age and BMI. → [skull-osteology](./skull-osteology.md), [soft-tissue-thickness](./soft-tissue-thickness.md), [forehead-brow-temple-hairline](./forehead-brow-temple-hairline.md)
11. **For photos, depth tables run backwards.** The photos own the skin. Tables place the hidden bone and flag implausible sculpts, as log-normal priors whose spread is ≈1 mm at thin midline sites and 3–5 mm laterally 🧠. BMI is the strongest covariate ✅, and the measurement method moves values as much as demographics do ↔️. Nose, lip and ear shape must never come from depth tables 📄. → [soft-tissue-thickness](./soft-tissue-thickness.md)
12. **Forensic rules become weak priors for hidden anatomy only.** Bone-to-skin rules carry σ of 2–5 mm, while a calibrated multi-view set sees skin at about 1–2 mm 🧠. The old rim-tangent eye rule under-predicts globe projection by about 4 mm 📄; use a Hertel-type rule. → [forensic-reconstruction](./forensic-reconstruction.md)
13. **Soft tissue is a laminate of fixed lines and mobile masses.** Retaining ligaments tie skin to bone along the orbital rim, the zygomatic body, the anterior masseter border and the anterior mandible; the compartments between them swell, deflate and slide 🧠. Tear trough, lid–cheek junction, nasolabial fold, jowl and prejowl sulcus appear where a tethered line meets a moving mass, so sculpt overhangs, not trenches 🧠. The nasolabial fold is a fat-boundary fold present from infancy 📄. → [smas-ligaments](./smas-ligaments.md), [fat-compartments](./fat-compartments.md), [muscles-mid-face](./muscles-mid-face.md)

**Features**

14. **Eyes: fixed optics, variable dressing.** Globes are about 24 mm with no sex or age difference in adults 📄, so "big", "deep-set" or "prominent" eyes come from fissure, lid position, crease, fold and protrusion, never from scaling the globe 🧠. Place the cornea from population-conditioned Hertel values (white ~15–17, Black ~17.5–18.5, East Asian ~14.4 mm ahead of the lateral rim) ✅. → [eye-region](./eye-region.md)
15. **The nose is the least predictable feature from bone and the most distorted by the camera.** Only 26 of 76 nose–aperture relations were significant, and nose–bone correlations are weak (RV < 0.4) ✅. Projection, rotation and dorsum read almost only in profile, ¾ and basal views 🧠. → [nose](./nose.md), [skull-osteology](./skull-osteology.md)
16. **The mouth sits on the teeth.** Fit it from neutral, lips-closed, bare-lip frames 📄. The lower vermilion is taller than the upper ✅, but 1.6:1 is an aesthetic target; measured midline ratios run about 1.0–1.8 ↔️. Lip projection follows a latent dental arch, and resting upper-incisor display falls from ≈3.4 mm under 30 to ≈0.5 mm in the 50s 📄. → [mouth-lips-teeth](./mouth-lips-teeth.md), [aging-face](./aging-face.md)
17. **Jaw width is bone plus muscle plus fat, and only multiple views separate them.** The frontal silhouette gives one equation; the profile pins the gonial angle and ramus; a relaxed/clenched pair measures the masseter, which thickens about 27–30% on clenching ✅. → [muscles-mastication-jaw](./muscles-mastication-jaw.md), [jaw-chin-neck](./jaw-chin-neck.md)
18. **Ears are rigid, individual and easy to get wrong in photos.** Adult length means run 57.6–62.9 mm 📄, males longer ✅, and length keeps creeping up by ≈0.22 mm a year 📄. Anchor ear height to FH at tragion rather than to the brow/nose-base canon; ears need their own camera views and full perspective. → [ear](./ear.md)
19. **Hair is not anatomy.** Brows are plucked, tattooed and microbladed, and the hairline recedes; neither may set scale or bone 🧠. Brow hair is a separate curve layer over the supraorbital rim. → [forehead-brow-temple-hairline](./forehead-brow-temple-hairline.md), [muscles-upper-face](./muscles-upper-face.md)

**Expression, asymmetry, sex, age, population**

20. **"Neutral" means relaxed, not zero tone.** Leaked action units corrupt identity: AU6+12 widens the mouth, deepens the nasolabial fold and fills the malar area; AU1/2 raises the brows 🧠. Gate frames by blendshape scores and keep expressions as separate shape keys. Habitual tone such as mentalis strain or a chronic AU4 *is* identity 🧠. FACS codes appearance, one AU per muscle or small group ✅; ARKit/MediaPipe coefficients are FACS-inspired regressor outputs, not intensities 🧠. → [facs-expressions](./facs-expressions.md), [muscles-upper-face](./muscles-upper-face.md), [muscles-lower-face](./muscles-lower-face.md)
21. **Asymmetry is universal, visible and identity-bearing.** Whole-face RMSD against the mirror image is ≈0.8 mm 📄, bilateral landmarks differ by 0.6–4.6 mm 📄, and eyelid differences show from ≈2 mm 📄. Keep symmetry for block-out, topology and rigging, and hold the asymmetry as a separate, switchable layer; never mirror detail or texture 🧠. → [facial-asymmetry](./facial-asymmetry.md)
22. **Pose fakes asymmetry.** 3° of yaw on a pair 40 mm behind the nose tip shifts it by ≈4.2 mm (arithmetic 🧠), more than the anatomy. Estimate asymmetry in 3D from views at least 30° apart, and check for mirrored selfies. → [facial-asymmetry](./facial-asymmetry.md)
23. **Sex is a continuous axis with overlapping distributions.** Men's faces are 5–9% larger on most linear measures (d ≈ 1.3–1.8 for face height, nose width, zy–zy) but barely differ around the eyes (en–en d ≈ 0.3) ✅/📄. Whole-face 3D shape still classifies sex at about 90–97% 📄. Use a latent axis with a user-set prior, never a template switch or a classifier on the photos 🧠. → [sexual-dimorphism](./sexual-dimorphism.md)
24. **Age is layered: bone, fat, ligaments, skin.** The orbit and maxilla recede, deep fat deflates, tissue between ligaments loosens and skin thins, each on its own schedule ↔️. An older face is a different volume first and a wrinkle texture second, so model age as several parameters and ask about teeth, toxin and fillers 🧠. → [aging-face](./aging-face.md)
25. **Children are not scaled-down adults.** The cranium follows a fast neural growth curve and the face a slow somatic one, so the younger the child, the lower the eye line and the larger the cranium relative to the face 🧠. Age-matched priors, an iris scale anchor, short capture windows and hard safeguards for minors are requirements 🧠. → [child-growth](./child-growth.md)
26. **Most variation is within populations, but a few traits are not.** Roughly 85–95% of genetic and cranial variance lies within groups 🧠; nose width, radix height, lids, lip fullness and head shape differ by several within-group SDs 🧠. Most 3D face models are European-trained 🧠, so frontal-only fits drift toward European depth. Use balanced pooled priors plus measurement, and never infer or store ancestry 🧠. → [population-variation](./population-variation.md)

**Detail**

27. **Skin detail signals age and realism, not identity.** The exceptions are moles, scars and distinctive lines, which must be placed to about 1 mm 🧠. Pores need ≤0.03–0.05 mm/px, far finer than a normal portrait 🧠. Wrinkles are folded sheets running across their muscle's pull, not knife cuts 🧠. → [skin-wrinkles-microdetail](./skin-wrinkles-microdetail.md)

## Quick-reference tables

Values are copied from the notes with their badges and with verification corrections applied. Ranges are the notes' ranges of means unless stated. "NAW" = young North American White adults (Farkas-type data). Ask the linked note for the population, method and caveats before reusing a value.

### Q1. Scale anchors and eye constants (adults)

| Quantity | Value | Badge | Note |
|---|---|---|---|
| Corneal ("iris") diameter, pooled | 11.84 mm, SD 0.79; single-device series 11.65–11.79 mm, SD 0.36–0.43 | ✅ | [eye-region](./eye-region.md) |
| MediaPipe Iris model assumption | 11.7 ± 0.5 mm | 📄 | [craniometric-landmarks](./craniometric-landmarks.md) |
| Globe, transverse × vertical; axial | 24.2 × 23.7 mm; 22.0–24.8 mm; no sex or age difference | 📄 | [eye-region](./eye-region.md), [sexual-dimorphism](./sexual-dimorphism.md) |
| Corneal radius, anterior / posterior | ≈7.8 / 6.4–6.5 mm | ✅ | [eye-region](./eye-region.md) |
| Interpupillary distance | M ≈64–65, F ≈62 mm, SD ≈3.5–4 | 🧠 | [eye-region](./eye-region.md) |
| Hertel, white adults | mean ≈15–17 mm; upper limit 20.1 (F) / 21.7 (M) | 📄 | [eye-region](./eye-region.md) |
| Hertel, Black adults | means 17.5 (F) / 18.2–18.5 (M); upper limits 22.7–24.7 | ✅ | [eye-region](./eye-region.md) |
| Hertel, East Asian adults | 14.4 ± 2.5; upper ≈19.3–19.4 | ✅ | [eye-region](./eye-region.md) |
| Orbital aperture, height × width | ≈35 × 40 mm | 📄 | [skull-osteology](./skull-osteology.md) |
| Supraorbital notch from midline | ≈20 mm | ✅ | [skull-osteology](./skull-osteology.md) |
| Infraorbital foramen below the rim | ≈6 mm (5–8.5) | ✅ / ↔️ | [eye-region](./eye-region.md), [skull-osteology](./skull-osteology.md) |
| Canthal height | ex ≈2–4 mm above en | ✅ | [eye-region](./eye-region.md) |
| Canthal tilt | white +2° to +8° (4.12° in a general sample); East Asian ≈7.5° (M) / 10° (F) | 📄 | [eye-region](./eye-region.md) |
| Fissure length ex–en / height | 30–32 (M), 29–31 (F) / 8–11 mm | 🧠 | [eye-region](./eye-region.md) |
| MRD1 / MRD2 | 4–5 / 5–5.5 mm | 🧠 | [eye-region](./eye-region.md) |
| ex depth behind en | ≈8–13 mm | 🧠 ↔️ | [eye-region](./eye-region.md) |
| Upper-lid crease above lashes | Caucasian 7.3 (F) / 6.9 (M) mm (secondary); Chinese ≈4.0–6.1 mm or absent | ↔️ | [muscles-upper-face](./muscles-upper-face.md) |

### Q2. Soft-tissue depth, bone to skin (adults, mm)

| Landmark | Depth | Badge | Note |
|---|---|---|---|
| Glabella | 5.5 pooled; 5.11 CBCT | ✅ | [skull-osteology](./skull-osteology.md) |
| Nasion | 6.0 pooled; 6.78 CBCT; 5.57 → 8.25 lowest → highest BMI group | ✅ | [skull-osteology](./skull-osteology.md) |
| Rhinion | 3.0 | 📄 | [skull-osteology](./skull-osteology.md) |
| Supraglabella | ≈3.5–5.1; M > F | ✅ (corrected) | [forehead-brow-temple-hairline](./forehead-brow-temple-hairline.md) |
| Frontal eminence | ≈4.2–4.8 | ✅ (corrected) | [forehead-brow-temple-hairline](./forehead-brow-temple-hairline.md) |
| Supraorbital (mid-brow) | ≈5.7–6.7 | ✅ (corrected) | [forehead-brow-temple-hairline](./forehead-brow-temple-hairline.md) |
| Mid-philtrum | 16.41 (M) / 13.95 (F) Iranian MRI; 10.80 Nigerian women CT | ↔️ | [soft-tissue-thickness](./soft-tissue-thickness.md) |
| Pogonion | 12.3 (M) / 11.0 (F); 11.71 CBCT | ✅ | [skull-osteology](./skull-osteology.md) |
| Gnathion | 8.46 | 📄 | [skull-osteology](./skull-osteology.md) |
| Menton | ≈6–9 | 🧠 | [skull-osteology](./skull-osteology.md) |
| Zygion (arch) | ≈6–10; >2 mm thicker in older adults | 🧠 / 📄 age | [skull-osteology](./skull-osteology.md) |
| Inferior malar | ≈10–18 | 🧠 | [skull-osteology](./skull-osteology.md) |
| Buccal, masseter, occlusal line | ≈15–25 (thickest) | 🧠 | [skull-osteology](./skull-osteology.md) |
| Gonion | ≈8–18; Nigerian CT 16.6 (M) / 15.2 (F) | ↔️ | [muscles-mastication-jaw](./muscles-mastication-jaw.md) |
| Chin, 5 mm lateral of the chin point | skin→mentalis 6.7 ± 1.4; mentalis 4.0 ± 1.4 | 📄 | [muscles-lower-face](./muscles-lower-face.md) |
| Skin only (epidermis + dermis) | ≈1.1–1.6 median by HFUS; mid-cheek dermis 1.877 (M) / 1.580 (F) | ✅ | [smas-ligaments](./smas-ligaments.md) |
| Observer error | inter-observer TEM 0.19–1.45 mm | 📄 | [soft-tissue-thickness](./soft-tissue-thickness.md) |

### Q3. Linear norms (young adults, mm, male / female)

| Measure | Value | Badge | Note |
|---|---|---|---|
| Face height n–gn (gn = lowest chin point) | NAW 121.3 ± 6.8 / 111.8 ± 5.2; across samples ≈120–126 / 112–116 | 📄 mean; ✅ range | [anthropometric-norms](./anthropometric-norms.md) |
| Intercanthal en–en | Kosovo 32.5 / 31.8; Malay 35.7 / 35.0; Hong Kong Chinese 40.6 / 38.3 (3D) | 📄 each; ✅ ↔️ span 31–41 | [anthropometric-norms](./anthropometric-norms.md) |
| Biocular ex–ex | 88–92 / 85–89 (SD 3.6 / 4.0) | 🧠 mean, 📄 SD | [anthropometric-norms](./anthropometric-norms.md) |
| Nose width al–al | 34.9 / 31.4 (alare-to-midline 17.34 / 15.39 📄) | 🧠 | [nose](./nose.md) |
| Mouth width ch–ch | 51–55 / 48–52 | 🧠 | [anthropometric-norms](./anthropometric-norms.md) |
| Face width zy–zy | 135–140 / 127–132 | 🧠 | [anthropometric-norms](./anthropometric-norms.md) |
| Bony jaw width go–go (caliper) | 94–100 / 88–94 (one 3D study 84.6 / 80.7) | 🧠 ↔️ | [anthropometric-norms](./anthropometric-norms.md), [jaw-chin-neck](./jaw-chin-neck.md) |
| Nose height n–sn; tip protrusion sn–prn | 53–56 / 49–52; 18–22 / 17–20 | 🧠 | [nose](./nose.md) |
| Upper lip height sn–sto | 21–24 / 19–21 | 🧠 | [anthropometric-norms](./anthropometric-norms.md) |
| Head length g–op; breadth eu–eu | 194–199 / 184–189; 149–154 / 141–146 | 🧠 | [anthropometric-norms](./anthropometric-norms.md) |
| Ear length | study means 57.6–62.9; Sundanese 62.9 / 60.9 | 📄 | [ear](./ear.md) |
| Typical CV | 3–4% head and zy–zy; 5–8% most face measures; 10–20% vermilion, tip, philtrum | 🧠 | [anthropometric-norms](./anthropometric-norms.md) |
| Method offsets | direct vs 3D mostly < 2 mm 📄 ✅; photo jaw silhouette exceeds caliper go–go by ≈10–30 mm 🧠; hair adds 5–20+ mm at eu, op, v, tr 🧠 | mixed | [anthropometric-norms](./anthropometric-norms.md) |

### Q4. Proportion checks (scale-free)

Use as Student-t log-ratio priors or QA flags in a metric, FH-levelled 3D frame, never as targets. σ is the prior SD of log(ratio) for "same population / any population".

| Ratio | Typical | σ | Badge | Note |
|---|---|---|---|---|
| en–en / ex–en (orbital canon) | 1.05 (East Asian ≈1.1–1.3) | 0.08 / 0.14 | 🧠; canon holds in 30.6% ✅ | [facial-proportions-canons](./facial-proportions-canons.md) |
| al–al / en–en | 1.02; southern Spain en–en/al–al 0.89 (M) / 1.01 (F) 📄 | 0.09 / 0.16 | 🧠 | [facial-proportions-canons](./facial-proportions-canons.md) |
| ch–ch / al–al | 1.55; most adults exceed 1.5 📄 | 0.07 / 0.13 | 🧠 | [facial-proportions-canons](./facial-proportions-canons.md) |
| ch–ch / en–en | 1.59 (M) / 1.52 (F) | — | 📄 | [anthropometric-norms](./anthropometric-norms.md) |
| ch–ch / IPD (rest) | ≈0.83; corners near the medial limbus, not the pupils | 0.07 / 0.10, QA only | 🧠 | [facial-proportions-canons](./facial-proportions-canons.md), [mouth-lips-teeth](./mouth-lips-teeth.md) |
| sn–gn / n–sn | 1.27 | 0.08 / 0.10 | 🧠 | [facial-proportions-canons](./facial-proportions-canons.md) |
| sn–sto / sto–gn | 0.45 | 0.10 / 0.12 | 🧠 | [facial-proportions-canons](./facial-proportions-canons.md) |
| n–gn / zy–zy (facial index) | ≈0.88 (M) / 0.86 (F) | 0.05 | 🧠 | [anthropometric-norms](./anthropometric-norms.md) |
| go–go / zy–zy (bone) | ≈0.70–0.80 (NAW caliper ≈0.71 / 0.70) | 0.06 | 🧠 | [skull-osteology](./skull-osteology.md), [anthropometric-norms](./anthropometric-norms.md) |
| Eye line v–en / v–gn | 0.48–0.53 (prior 0.51) | 0.025 / 0.03 | 🧠 ↔️ | [facial-proportions-canons](./facial-proportions-canons.md) |
| Cephalic index eu–eu / g–op | 0.79 (bands: dolicho < 76, meso 76–80.9, brachy 81–85.4) | 0.04 / 0.07 | 🧠 | [population-variation](./population-variation.md) |
| Interpupillary / face width | ≈46% in average faces | — | 📄 | [facial-proportions-canons](./facial-proportions-canons.md) |
| Face length / width | ≈1.3–1.4, not 1.618 | — | 🧠 | [facial-proportions-canons](./facial-proportions-canons.md) |

### Q5. Profile angles and projection

| Quantity | Value | Badge | Note |
|---|---|---|---|
| Nasofrontal angle g′–n′–prn | 115–135° (samples 124–142°) | ↔️ | [nose](./nose.md) |
| Nasolabial angle | 90–120°; M ≈90–105, F ≈95–115 (samples 98–116°, sex difference inconsistent) | ↔️ | [nose](./nose.md) |
| Goode projection ratio / nasofacial angle | 0.55–0.60 / 30–40°: one triangle, one constraint | 🧠 | [nose](./nose.md) |
| Columellar show in profile | 2–4 mm | 🧠 | [nose](./nose.md) |
| Mentolabial angle | ≈110–135° (acceptable 107–140°) | ↔️ | [muscles-lower-face](./muscles-lower-face.md) |
| Mentolabial sulcus depth | 4 ± 2 mm | 🧠 | [muscles-lower-face](./muscles-lower-face.md) |
| Upper / lower lip to E-line | ≈−4 / −2 mm (white adults); ≥0 in African- and East Asian-descent norms | ↔️ | [mouth-lips-teeth](./mouth-lips-teeth.md) |
| Facial convexity G′–Sn–Pog′ | 12 ± 4° | 🧠 | [jaw-chin-neck](./jaw-chin-neck.md) |
| Gonial angle, adult | cephalometric means 121–125° ✅; CBCT means 125–129° (F higher) ↔️; men 0–4° smaller ↔️ | mixed | [jaw-chin-neck](./jaw-chin-neck.md) |
| Cervicomental angle | youthful ideal 105–120°; measured adults often 115–135°+ | ↔️ | [jaw-chin-neck](./jaw-chin-neck.md) |
| Forehead inclination | ≈5–20° back; Korean 15.9° (M) / 12.5° (F) | ↔️ | [forehead-brow-temple-hairline](./forehead-brow-temple-hairline.md) |

### Q6. Jaw, masticatory muscles, neck

| Quantity | Value | Badge | Note |
|---|---|---|---|
| Masseter thickness, relaxed / clenched (Korean young adults) | F 9.8 ± 1.3 / 12.4 ± 1.4; M 11.3 ± 1.2 / 14.7 ± 1.4 mm | ✅ | [muscles-mastication-jaw](./muscles-mastication-jaw.md) |
| Masseter, systematic review (men) | relaxed 10–15, contracted 14–19 mm | ✅ | [muscles-mastication-jaw](./muscles-mastication-jaw.md) |
| Masseter by vertical pattern | hypo 13.94 / normo 12.53 / hyperdivergent 11.13 mm | 📄 | [muscles-mastication-jaw](./muscles-mastication-jaw.md) |
| Botulinum toxin on masseter | ≈−25% thickness, ≈−30% volume, peak ≈3 months; bone change contested | 📄 / ↔️ | [muscles-mastication-jaw](./muscles-mastication-jaw.md) |
| Temporalis volume (Taiwanese) | M peak 36.9 mL then −38%; F peak 27.9 mL then −60% | 📄 | [muscles-mastication-jaw](./muscles-mastication-jaw.md) |
| Ramus height Co–Go | M ≈55–65, F ≈50–58 mm (means span M 53–77, F 49–70 by method) | ↔️ | [jaw-chin-neck](./jaw-chin-neck.md) |
| Condyle in front of tragus | ≈10–15 mm | 🧠 | [jaw-chin-neck](./jaw-chin-neck.md) |
| Max opening / freeway space | ≈40–55 mm / ≈2–4 mm; rotation for the first 20–25 mm | 🧠 | [jaw-chin-neck](./jaw-chin-neck.md) |
| Thyroid lamina angle | M ≈90°, F ≈120° | 🧠 | [jaw-chin-neck](./jaw-chin-neck.md) |
| Neck circumference | M ≈37–42, F ≈31–36 cm | 🧠 | [jaw-chin-neck](./jaw-chin-neck.md) |

### Q7. Mouth and teeth

| Quantity | Value | Badge | Note |
|---|---|---|---|
| Upper vermilion ls–sto | ≈8.1 mm (20–29 y) → ≈6.6 mm (50–59 y) | 📄 | [mouth-lips-teeth](./mouth-lips-teeth.md) |
| Philtrum width cph–cph; "upper lip height" | ≈11–12 mm; ≈22–23 mm (probably sn–sto); Chinese women | 📄 | [mouth-lips-teeth](./mouth-lips-teeth.md) |
| Skin upper lip sn–ls | ≈12–17 mm | 🧠 | [mouth-lips-teeth](./mouth-lips-teeth.md) |
| Lower : upper vermilion | aesthetic target 1.6:1 ↔️; measured ≈1.0–1.8 (Chinese ≈1.1, Black South African women ≈1.0–1.2, Caucasian women ≈1.8) ↔️ | ↔️ | [mouth-lips-teeth](./mouth-lips-teeth.md) |
| Resting upper-incisor display | ≈3.4 (< 30 y), 1.6 (30s), 1.0 (40s), 0.5 mm (50s) (corrected); F ≈3.4 vs M ≈1.9 | 📄 | [aging-face](./aging-face.md), [mouth-lips-teeth](./mouth-lips-teeth.md) |
| Pleasing display at rest | 2–4 mm | 📄 | [mouth-lips-teeth](./mouth-lips-teeth.md) |
| Inter-canine width rule | ICW ≈ 75% of mouth width (ICW definition unverified) | 📄 | [forensic-reconstruction](./forensic-reconstruction.md) |
| Upper intercanine width, cusp tips | ≈33–37 mm | 🧠 | [mouth-lips-teeth](./mouth-lips-teeth.md) |
| Soft tissue over upper incisors | ≈11–15 mm | 🧠 | [mouth-lips-teeth](./mouth-lips-teeth.md) |
| DAO insertion from commissure; DAO / DLI width | ≈10 mm lateral, 10 mm caudal; 14 ± 3 / 20 ± 4 mm | 📄 | [muscles-lower-face](./muscles-lower-face.md) |
| Modiolus centre from cheilion | ≈10–15 mm lateral, ±5 mm vertical | ↔️ | [muscles-lower-face](./muscles-lower-face.md) |
| Smile arc consonant | 43–83% depending on cohort and classification | ↔️ | [mouth-lips-teeth](./mouth-lips-teeth.md) |

### Q8. Ear

| Quantity | Value | Badge | Note |
|---|---|---|---|
| Length / width (means) | 57.6–62.9 / 28.8–32.8 mm; W/L ≈0.47–0.54 | 📄 | [ear](./ear.md) |
| Sex | males longer ✅; width difference inconsistent ↔️ | mixed | [ear](./ear.md) |
| Adult growth | ≈0.22 mm/year (cross-sectional, ages 30–93); conflicts with "stable to ~70" | 📄 ↔️ | [ear](./ear.md), [aging-face](./aging-face.md) |
| Mature length | by ≈14 y (Chinese sample) | 📄 | [ear](./ear.md) |
| Long-axis tilt (FH) | ≈10–30°, typical ≈20° | 🧠 ↔️ | [ear](./ear.md) |
| Tragion height vs soft orbitale | same level ± 5 mm | 🧠 | [ear](./ear.md) |
| Ear length − nose height n–sn | +5 to +12 mm | 🧠 ↔️ | [ear](./ear.md) |
| Prominent if protrusion exceeds | upper 21.5 (boys) / 17.5 (girls); lower 20.0 / 15.5 mm | 📄 | [ear](./ear.md) |
| Auriculocephalic angle | 20–30° vs < 25° with ≤ 20 mm projection | ↔️ | [ear](./ear.md) |

### Q9. Asymmetry and perception

| Quantity | Value | Badge | Note |
|---|---|---|---|
| Whole-face RMSD vs mirror | 0.8 ± 0.2 mm (rises with age); thirds 0.5 / 0.6 / 0.6 | 📄 | [facial-asymmetry](./facial-asymmetry.md) |
| Bilateral landmark R–L difference | 0.6–4.6 mm, largest lower and lateral | 📄 | [facial-asymmetry](./facial-asymmetry.md) |
| Visible from | eyelid ≈2 mm; brow, mouth corner ≈3 mm; laypeople 4 vs specialists 2 mm; cant 3–4° | 📄 / ↔️ | [facial-asymmetry](./facial-asymmetry.md) |
| Working L–R ranges | lids 0.5–1.5; brows 1–3; nasal tip 0.5–3; chin 0–3; gonion 1–4; ears 0–5 mm | 🧠 | [facial-asymmetry](./facial-asymmetry.md) |
| Identity spatial-frequency band | ≈8–16 cycles per face width, peak ≈10 | 📄 | [face-perception-likeness](./face-perception-likeness.md) |
| Best-likeness caricature level | ≈+4.4% (photos) up to ≈+42%; ≈−14% also reported | ↔️ | [face-perception-likeness](./face-perception-likeness.md) |
| MAP shrinkage k at σp = 4 mm | σd 1 → 0.94; σd 2 → 0.80; σd 4 → 0.50; σd 8 → 0.20 | exact arithmetic | [face-perception-likeness](./face-perception-likeness.md) |

### Q10. Photo geometry (pinhole arithmetic, 🧠)

| Effect | 0.35 m | 0.5 m | 1 m | 1.5–2 m | 3 m | Note |
|---|---|---|---|---|---|---|
| Nose tip vs tragion (Δ ≈100 mm) | ×1.29 | ×1.20 | ×1.10 | ×1.07 (1.5 m) | ×1.03 | [nose](./nose.md) |
| al–al/zy–zy inflation (Δ ≈70 mm) | +20% | +14% | +7% | +3.5% (2 m) | +2.3% | [facial-proportions-canons](./facial-proportions-canons.md) |
| Ear vs nose-tip scale, frontal | ×0.73 (0.3 m) | ×0.82 | ×0.90 | ×0.95 (2 m) | — | [ear](./ear.md) |
| Jaw plane vs nose-tip plane | ×0.80 (0.4 m) | — | ×0.91 | ×0.95 (2 m) | — | [muscles-mastication-jaw](./muscles-mastication-jaw.md) |

| Pose error | Effect | Note |
|---|---|---|
| Yaw 3° / 5°, pair 40 mm behind the nose tip | 4.2 / 7.0 mm of apparent asymmetry | [facial-asymmetry](./facial-asymmetry.md) |
| Roll 3° over a 60 mm baseline | 3.1 mm cant | [facial-asymmetry](./facial-asymmetry.md) |
| Pitch 5° / 10° | nose tip moves 2.6 / 5.2 mm against nasion and alar base; ears ≈9 / 17 mm against the brow | [nose](./nose.md), [ear](./ear.md) |
| Detector noise | 1 px ≈0.15–0.25 mm on a portrait; 3–5 px ≈ the size of real asymmetry | [facial-asymmetry](./facial-asymmetry.md) |

The clinical "selfie effect" is reported as ≈30% wider nasal base at 12 in than at 5 ft 📄 ↔️, against ≈10–12% from geometry alone ([nose](./nose.md)).

### Q11. Age, growth and children

| Quantity | Value | Badge | Note |
|---|---|---|---|
| Upper vermilion prior | μ = 8.0 − 0.05·(age − 25) mm, σ 1.5 | 📄 | [aging-face](./aging-face.md) |
| Ear length prior | +0.2 mm per year after 25 | 📄 | [aging-face](./aging-face.md) |
| Dermal collagen | ≈−1% per year in adults | 🧠 | [aging-face](./aging-face.md) |
| Glogau photoaging | I 20s–30s, II late 30s–40s, III 50s+, IV 60s–70s+ | 🧠 | [aging-face](./aging-face.md) |
| Lid–cheek junction below the lid margin | 10–12 mm young → ≥15–20 mm old (stability also reported) | 🧠 ↔️ | [eye-region](./eye-region.md) |
| Human apparent-age error | ≈5–8 years | 🧠 ↔️ | [aging-face](./aging-face.md) |
| Child globe axial length | ≈16.5–17.5 mm at birth; 21.8 mm at 3 y 📄; ≈24 adult | 🧠 / 📄 | [child-growth](./child-growth.md) |
| Child corneal diameter | term newborn 9.0–10.5 (mean 9.8); adult size by ≈1 y or 2–3 y | ↔️ | [child-growth](./child-growth.md) |
| Eye line from the top (v–en / v–gn) | ≈0.60–0.66 at 1 y; 0.54–0.58 at 6 y; 0.48–0.53 adult | 🧠 ↔️ | [child-growth](./child-growth.md) |
| Facial index n–gn / zy–zy | 0.72–0.78 at 1 y; 0.80–0.86 at 6 y; 0.84–0.92 adult | 🧠 | [child-growth](./child-growth.md) |
| Peak height velocity | ≈11–12 y (girls), ≈13–14 y (boys), ±2 y | 🧠 | [child-growth](./child-growth.md) |
| Max photo-set span | ≤1 week (0–3 mo) … ≤4 months (3–10 y), ≤3 months in the pubertal spurt | 🧠 | [child-growth](./child-growth.md) |

### Q12. Key landmarks and detector indices (0-based)

| Abbr | Tissue | dlib 68 | MediaPipe 478 | Badge | Note |
|---|---|---|---|---|---|
| en (R / L) | skin | 39 / 42 | 133 / 362 | ✅ def, 🧠 map | [craniometric-landmarks](./craniometric-landmarks.md) |
| ex (R / L) | skin | 36 / 45 | 33 / 263 | ✅ def, 🧠 map | ″ |
| ch (R / L) | skin | 48 / 54 | 61 / 291 | ✅ def, 🧠 map | ″ |
| prn | skin | 30 | 1 | ✅ def, 🧠 map | ″ |
| sn | skin | 33 | ≈2 | ↔️ def, 🧠 map | ″ |
| ls / li | skin | 51 / 57 | 0 / 17 | ↔️ def, 🧠 map | ″ |
| sto | skin | mean(62, 66) | mean(13, 14) | ✅ def, ↔️ split | ″ |
| me′ (Farkas gn) | skin | ≈8 | ≈152 | ✅ def, 🧠 map | ″ |
| zy, go | bone / skin | silhouette 0–2 / 14–16; sliding 3–5 / 11–13 | silhouette 234 / 454 | 🧠, never anatomical | ″ |
| Iris centres | — | — | 468 / 473 | 🧠 | ″ |
| Upper / lower lid (R; L) | skin | — | 159 / 145; 386 / 374 | 📄 | [muscles-upper-face](./muscles-upper-face.md) |
| t, po, tr, v, g′ | — | none | none (10 = mesh top, not trichion) | 🧠 | [forehead-brow-temple-hairline](./forehead-brow-temple-hairline.md) |

dlib blocks: jaw 0–16, right brow 17–21, left brow 22–26, nose 27–35, right eye 36–41, left eye 42–47, mouth 48–67 ✅. MediaPipe = 468 mesh + 10 iris points ✅; its z is relative, not metric 🧠. Confirm every MediaPipe index by rendering labels on the canonical mesh.

### Q13. Neutral-frame gate (MediaPipe blendshape scores, 🧠 heuristics)

| Score | Reject or down-weight above | Note |
|---|---|---|
| mouthSmile | 0.25 | [facs-expressions](./facs-expressions.md) |
| cheekSquint, eyeWide, browInnerUp, browOuterUp | 0.3 | ″ |
| browDown | 0.35 | ″ |
| eyeBlink | 0.4 | ″ |
| jawOpen | 0.08 | ″ |
| mouthPress, mouthRoll, mouthShrugLower | 0.3 | ″ |
| Lips parted (inner gap / ch–ch) | 0.04 | [mouth-lips-teeth](./mouth-lips-teeth.md) |
| Brow height above the multi-frame median | 2.5 mm | [muscles-upper-face](./muscles-upper-face.md) |

### Q14. Skin and detail (🧠 unless marked)

| Quantity | Value | Note |
|---|---|---|
| Skin thickness by region | eyelid 0.4–0.9; forehead 1.4–2.2; mid-cheek 1.3–2.0; nasal tip 1.5–3.0 (nasal apex the thickest site, median 1.907 mm, 📄) | [skin-wrinkles-microdetail](./skin-wrinkles-microdetail.md) |
| Wrinkle spacing | eyelid crinkles 0.5–1.5; crow's feet 2–5; forehead lines 6–15 mm ↔️ | ″ |
| Static wrinkle depth | ≈0.05–1 mm, rarely > 1.5 | ″ |
| Pore diameter | ≈0.05–0.4 mm; largest on nose and medial cheek; none on lids or vermilion | ″ |
| Resolution needed (140 mm face, ≥ 3 px per feature) | line position ≤ 0.25 mm/px; fine lines ≤ 0.08; pores ≤ 0.033; microrelief ≤ 0.02 | ″ |
| Worked examples | 24 MP full frame, 85 mm at 1 m ≈0.07 mm/px; 12 MP phone at 0.5 m ≈0.17 mm/px | ″ |
| Mesh vs map | volume folds (NLF, jowl) in base mesh and shape keys; expression lines on Multires; fine lines and crepe in normal or bump maps | [aging-face](./aging-face.md) |

## Blender checklist

A working order for an artist. Each item links the note that explains it.

**Intake and consent**
- [ ] Record, with consent: age (months for a child), sex as the sitter states it, height and weight (BMI), dental status (dentures, missing molars, orthodontics), toxin, fillers, threads or surgery, recent weight change, glasses. Store them as custom properties on the head object; never infer them from the photos ([soft-tissue-thickness](./soft-tissue-thickness.md), [sexual-dimorphism](./sexual-dimorphism.md), [aging-face](./aging-face.md)).
- [ ] If the sitter is a minor: guardian consent plus the child's assent, local processing, limited retention, no sexualised use ([child-growth](./child-growth.md)).
- [ ] If possible, take five minutes of caliper measurements (en–en, ex–ex, al–al, ch–ch with lips relaxed) and a head circumference ([anthropometric-norms](./anthropometric-norms.md)).

**Capture**
- [ ] One session (for a child, within the span in [child-growth](./child-growth.md)). Camera at 1.5 m or more, 85–135 mm-equivalent lens, camera at nose height ([nose](./nose.md)).
- [ ] Frontal, both true profiles, both ¾ views, a basal "worm's-eye" nose view, a top-of-head view, a back view, and one shot per ear about 20–35° behind profile ([nose](./nose.md), [ear](./ear.md), [population-variation](./population-variation.md)).
- [ ] Relaxed neutral: lips lightly touching, teeth just apart, forehead slack, gaze on a target at lens height, glasses off well beforehand, hair pulled back, no earrings ([facs-expressions](./facs-expressions.md), [forehead-brow-temple-hairline](./forehead-brow-temple-hairline.md)). For a true resting brow, have the sitter close the eyes, relax, then open slowly ([muscles-upper-face](./muscles-upper-face.md)).
- [ ] Extra frames: upward and downward gaze (caruncle, crease, fold), lips apart at rest (incisor display), a clenched frontal/¾ pair (masseter), and a separate expression set for shape keys only ([eye-region](./eye-region.md), [muscles-mastication-jaw](./muscles-mastication-jaw.md), [muscles-mid-face](./muscles-mid-face.md)).
- [ ] Diffuse light plus one raking side-light frame; RAW, beauty and noise-reduction modes off ([skin-wrinkles-microdetail](./skin-wrinkles-microdetail.md)).
- [ ] Audit for mirrored selfies (text, hair part, moles) ([facial-asymmetry](./facial-asymmetry.md)).

**Scene, cameras and frame**
- [ ] Units: Metric, length shown in millimetres; pick one unit scale and keep it (see contradiction C-14).
- [ ] Solve every camera before measuring anything; never trace from a photo taken nearer than about 1 m in an orthographic view ([nose](./nose.md), [facial-proportions-canons](./facial-proportions-canons.md)).
- [ ] Level the head to Frankfort horizontal (tragion to the lower-lid/cheek junction in profile) and set the midsagittal plane from en, ex, ch, al and t, weighting the upper face most. Put the object origin and local X axis on that plane, because Mirror and sculpt symmetry use them ([craniometric-landmarks](./craniometric-landmarks.md), [facial-asymmetry](./facial-asymmetry.md)).
- [ ] Set scale from the caliper value; otherwise from the iris (≈11.8 mm, both limbus edges sharp, no spectacles). Check orbit width ≈40 mm, nasal bones ≈20–25 mm and bizygomatic breadth ([eye-region](./eye-region.md), [skull-osteology](./skull-osteology.md)).
- [ ] Place named landmark empties (`LM.prn`, `LM.en.L` …) with custom properties for tissue, variant and σ ([craniometric-landmarks](./craniometric-landmarks.md)).

**Block-out: bone first**
- [ ] Symmetry on for cranium, jaw mass, orbit spacing, topology and UVs; keep topology symmetric for good ([facial-asymmetry](./facial-asymmetry.md)).
- [ ] Bony empties: skin landmarks offset inward along the bone normal by their tissue depth (g −5.5, n −6, rhi −3, pg −11, gn −8 mm); warp a CC0 or self-made skull to them ([soft-tissue-thickness](./soft-tissue-thickness.md)).
- [ ] Sculpt in order of bone confidence: forehead → glabella → nasion → rhinion silhouette within ~1 mm; orbital rims; malar body just below the lateral orbit (not on the arch); mandibular border, angle and chin box; thick zones last, from photo shading ([skull-osteology](./skull-osteology.md)).
- [ ] Check depth with a Geometry Nodes thickness map (Geometry Proximity to the skull, colour ramp at 3, 6, 10, 15 and 20 mm) or peg cylinders ([soft-tissue-thickness](./soft-tissue-thickness.md)).
- [ ] Build the head long enough behind the ears (head length ≈190–200 mm) ([anthropometric-norms](./anthropometric-norms.md)).

**Features**
- [ ] *Eyes:* ≈24 mm globe spheres with a corneal cap (R 7.8, Ø 11.8) aimed along the photo gaze; protrusion from the profile against the Hertel range for the sitter; lids as shells with ≈2 mm margins wrapping the corneal bulge; ex 8–13 mm deeper than en; separate the crease from the fold; never enlarge the globe ([eye-region](./eye-region.md)).
- [ ] *Nose:* radix → bony dorsum (skin 1.5–4 mm over the nasal bones) → cartilaginous dorsum → tip projection → rotation and columellar show → alar crease → widths in the frontal camera → two-dome tip lobule → nostrils from the basal view → real asymmetry ([nose](./nose.md)).
- [ ] *Mouth:* dental proxy first (incisal edges at the observed resting display, default 2–4 mm); wrap the lips around the arch with corners 10–20 mm behind the midline; then philtral columns, bow peaks, white roll, tubercle, contact line, corner pocket, mentolabial sulcus ([mouth-lips-teeth](./mouth-lips-teeth.md)).
- [ ] *Jaw and neck:* profile first for ramus and gonial angle; ¾ for the anterior masseter border; frontal last, splitting width into bone, masseter and fat; jaw pivot at the condyles, never at gonion; larynx 1.5–2.5 cm below the cervical point ([jaw-chin-neck](./jaw-chin-neck.md), [muscles-mastication-jaw](./muscles-mastication-jaw.md)).
- [ ] *Ears:* tragion first, on the FH line just behind the condyle; then tilt, length, width and flare; protrusion from front and back; sculpt as a separate dense object and bridge it in ([ear](./ear.md)).
- [ ] *Forehead and temple:* box with two side planes split by the temporal crests; medial superciliary arch plus flat lateral trigone; a supraglabellar break only where the profile shows one; temple from shading; hairline and brows as hair, not mesh ([forehead-brow-temple-hairline](./forehead-brow-temple-hairline.md)).

**Soft tissue, age and asymmetry**
- [ ] Vertex groups per fat compartment and ligament strip; volume as offsets in mm; folds as overhangs over tethered lines; never smooth across seams ([fat-compartments](./fat-compartments.md), [smas-ligaments](./smas-ligaments.md)).
- [ ] Age as shape keys in anatomical order: bone → deep fat → superficial fat → laxity → skin ([aging-face](./aging-face.md)).
- [ ] Switch symmetry off at the first secondary-form pass. Keep Basis symmetric and add an "Asym" shape key; sculpt asymmetry at base resolution, then add Multires. Work lids → brows and mouth corners → nose → chin and jaw → cheeks and ears ([facial-asymmetry](./facial-asymmetry.md)).
- [ ] Sanity check: register the result to its mirror; adults show ≈0.5–1.5 mm RMSD, and ≈0 means the face was symmetrised ([facial-asymmetry](./facial-asymmetry.md)).

**Expressions and detail**
- [ ] Make Basis active before identity work; name keys with ARKit-52 names; add correctives for AU1+2+4, AU6+12 and AU12+26; use a jaw bone beyond a small opening ([facs-expressions](./facs-expressions.md)).
- [ ] Place identity marks (moles, scars, distinctive lines) from two or more views first; generic pores last, and only if the photos' mm/px allows ([skin-wrinkles-microdetail](./skin-wrinkles-microdetail.md)).
- [ ] Static lines (present in every neutral frame) go in Basis; dynamic lines go in AU keys or wrinkle maps. Cut folds, not V-grooves; follow the RSTL field; never mirror detail or texture ([skin-wrinkles-microdetail](./skin-wrinkles-microdetail.md), [facial-asymmetry](./facial-asymmetry.md)).

**Review**
- [ ] Overlay renders from every solved camera on their photos, including ¾ and profile; compare silhouettes ([face-perception-likeness](./face-perception-likeness.md)).
- [ ] Thumbnail test at 64–128 px across the face before any pores; desaturate photos and compare under a matte matcap with the key light above and to the side, never from below ([face-perception-likeness](./face-perception-likeness.md)).
- [ ] Run a norm gauge (z-scores from the landmark empties): |z| 2–3 means re-check the landmark and camera; > 3 is almost always an error; never sculpt toward the mean ([anthropometric-norms](./anthropometric-norms.md)).
- [ ] Protect the 3–5 largest-|z| ratios: they are the sitter's caricature directions ([facial-proportions-canons](./facial-proportions-canons.md)).
- [ ] Flip render and photo together; view upside down; take breaks every 20–30 minutes against adaptation ([face-perception-likeness](./face-perception-likeness.md)).
- [ ] Final judges: people who know the sitter, shown multi-view renders with eyes, brows and a hair cap; show the sitter both the true and the mirrored render ([face-perception-likeness](./face-perception-likeness.md)).
- [ ] Symptom → cause: "a relative" = shrinkage or symmetrising; "eyes wrong" = lid peak, crease, tilt or depth; "sad or angry" = mouth corners or inner brow; "wrong age" = hooding, folds, jowl or photos from another period; "narrow face, big nose" = selfie distance; "front fine, ¾ wrong" = the prior filled the depth ([face-perception-likeness](./face-perception-likeness.md)).

## Cross-topic contradictions and how to resolve them

| ID | Conflict | Where | Resolution |
|---|---|---|---|
| C-1 | **Forehead and brow tissue depth.** Supraorbital ≈6.5–8 mm (Table 1 🧠) and ~6–9 mm (🧠), with prior μ 7.5 mm in `data/skull-osteology.json`; verification corrected it to ≈5.7–6.7 mm ✅ (prior μ 6.2). Supraglabella and frontal eminence were also corrected (3.5–5.1, 4.2–4.8 ✅). | [soft-tissue-thickness](./soft-tissue-thickness.md), [skull-osteology](./skull-osteology.md), [forehead-brow-temple-hairline](./forehead-brow-temple-hairline.md) | Use the corrected forehead values (supraorbital μ 6.2 mm, σ_log 0.20). Update the skull-osteology data file and soft-tissue Table 1 so the engine does not load 7.5. |
| C-2 | **Which sex is thicker laterally.** Women thicker at malar, lateral orbit and gonion (Korean data 📄, Thai ↔️) vs verification passes that found men generally thicker, with differences often < 1 mm. | [soft-tissue-thickness](./soft-tissue-thickness.md), [skull-osteology](./skull-osteology.md), [sexual-dimorphism](./sexual-dimorphism.md) | Keep the male midline excess (lips, philtrum, pogonion ✅). Centre lateral sex effects near 0 with σ covering both signs (|γ| ≤ 0.2). Let BMI, the stronger covariate, dominate. |
| C-3 | **Gonion and lateral depth magnitude.** ≈11–12 mm (consensus 🧠), 13 mm (skull prior), 16.6 / 15.2 mm (Nigerian CT); the 2023 T-table update raised gonion by 2.5 mm and zygion by 1.5 mm over 2008. | [soft-tissue-thickness](./soft-tissue-thickness.md), [skull-osteology](./skull-osteology.md), [muscles-mastication-jaw](./muscles-mastication-jaw.md) | μ ≈13 mm, σ_log 0.35. Treat gonion and zygion as weak hints (observation weight 0.1–0.2); let only g, n, rhi, pg and gn drive the skull warp. |
| C-4 | **Gonial angle.** ≈120° (StatPearls, dry bone 120.17° ✅) vs cephalometric 121–125° ✅ vs CBCT 125–129° ↔️; sex gap "men 2–6° smaller" vs 0–4° or none; the 90°/110° pair is rejected; newborn 160° 📄 vs 140–150° ↔️. Priors: M N(120, 6²)/F N(124, 6²) (not clearly supported), N(122, 7²), child data adult N(122, 6). | [jaw-chin-neck](./jaw-chin-neck.md), [skull-osteology](./skull-osteology.md), [muscles-mastication-jaw](./muscles-mastication-jaw.md), [sexual-dimorphism](./sexual-dimorphism.md), [child-growth](./child-growth.md) | One prior N(122°, 7²) (consider 124°), bounds 105–145°, and a method tag (CBCT reads higher). Sex offset 0–4°, never a sex switch. Newborn N(150, 10). |
| C-5 | **Cornea ahead of the lateral rim.** The skull ordering hinge [12, 20] mm and the forensic N(16, 2) vs corrected Hertel norms with upper limits up to 24.7 mm (Black adults) and means as low as 14.4 (East Asian). | [skull-osteology](./skull-osteology.md), [forensic-reconstruction](./forensic-reconstruction.md), [eye-region](./eye-region.md) | Use the eye-region population priors (N(14/16/18, 2)) when the sitter declares a population; otherwise a balanced mixture of the three. Widen the hinge to the forensic clamp 11–22 mm and take protrusion from the profile when one exists. |
| C-6 | **Iris scale prior.** 11.7 ± 0.5 mm (the MediaPipe assumption, used in craniometric and anthropometric defaults) vs 11.8 (σ 0.6–0.8) from pooled corneal data ✅; one series has men 12.12 vs women 11.84. Children: cornea adult-sized by 1 y vs 2–3 y. | [craniometric-landmarks](./craniometric-landmarks.md), [anthropometric-norms](./anthropometric-norms.md), [eye-region](./eye-region.md), [child-growth](./child-growth.md) | Use N(11.8, 0.6) mm from age 3; age-specific values under 2 y (10.0, 11.2). Any caliper measurement overrides. 11.7 belongs only inside MediaPipe's own depth estimate. |
| C-7 | **Canthal geometry.** ex 2–4 mm above en ✅ (corrected) vs 1–3 mm ↔️ (upper face, forensic); ex 3–5 mm medial of the lateral orbital margin (forensic) vs 5–7 mm (eye-region). | [eye-region](./eye-region.md), [muscles-upper-face](./muscles-upper-face.md), [forensic-reconstruction](./forensic-reconstruction.md) | Use the verified 2–4 mm and tilt priors N(+5°, 3) (East Asian +8°); measure tilt in FH, never the image. Keep ex ≥ 3 mm inside the bony rim as the hard limit, with a soft prior wide enough to span the reported 3–7 mm. |
| C-8 | **Upper-lid crease height.** 8–11 (F) / 6–8 (M) mm (eye-region 🧠) vs Cartwright 7.3 / 6.9 mm and Chinese 4.0–6.1 mm (verification ↔️); population note EAS 4–7 mm, absent in many. | [eye-region](./eye-region.md), [muscles-upper-face](./muscles-upper-face.md), [population-variation](./population-variation.md) | Wide priors (F 8 ± 2, M 7 ± 2, East Asian 4 ± 2.5, unknown 6.5 ± 3) plus an explicit "no crease" state; measure it in downgaze. |
| C-9 | **Resting upper-incisor display.** Corrected Vig & Brundo values 3.4 / 1.6 / 1.0 / 0.5 mm by age band and F 3.4 / M 1.9 📄 vs the forensic prior "stomion above U1 edge" 2.5 / 1.5 / 0.5 mm (🧠) and an older linear 3 − 0.07·(age − 25). | [aging-face](./aging-face.md), [mouth-lips-teeth](./mouth-lips-teeth.md), [forensic-reconstruction](./forensic-reconstruction.md), [sexual-dimorphism](./sexual-dimorphism.md) | Use the corrected interpolation from aging-face (σ 1.2 mm), with the observed display overriding whenever lips-apart frames exist. Retire the forensic band values. |
| C-10 | **Landmark and symmetry σ.** Engine defaults `sigma = 8.0` (scalar), `sigma_sym = 2.0`, `sigma_mid = 1.5`, vs per-landmark tables: symmetry 0.7–4 mm, defined on d = X_l − M·X_r (asymmetry), 1.5–3 mm on pairs (craniometric), 1.5–2 upper and 3–4 at gonion (skull); positional σ 2.5–8 mm by region (sex note). | [facial-asymmetry](./facial-asymmetry.md), [craniometric-landmarks](./craniometric-landmarks.md), [skull-osteology](./skull-osteology.md), [sexual-dimorphism](./sexual-dimorphism.md), [face-perception-likeness](./face-perception-likeness.md) | Adopt the facial-asymmetry per-landmark table and state which quantity σ applies to (d = 2A). Replace the scalar σ with per-landmark anisotropic arrays; keep 8 mm only as a fallback. |
| C-11 | **Lower-face vertical ratios.** sn–sto/sn–me 0.33 (σ 0.03), sn–sto/sn–gn ≈0.31, sn–sto/sto–gn 0.45, Sn–Stms : Stmi–Me′ 0.50 ± 0.06 and "1 : 2", with gn and sto defined differently. | [mouth-lips-teeth](./mouth-lips-teeth.md), [anthropometric-norms](./anthropometric-norms.md), [facial-proportions-canons](./facial-proportions-canons.md), [muscles-lower-face](./muscles-lower-face.md), [craniometric-landmarks](./craniometric-landmarks.md) | These are one measurement in different notations. Encode it once, with explicit sto (single vs split) and gn (Farkas lowest = me′) variants, and drop the duplicates. |
| C-12 | **Close-camera inflation.** al–al/zy–zy +20% at 0.35 m (canons, Δ ≈70 mm) vs ≈8–10% at 0.4 m (anthropometric, population notes) vs the clinical ≈30% nasal base at 12 in 📄 vs ≈10–12% geometric. | [facial-proportions-canons](./facial-proportions-canons.md), [anthropometric-norms](./anthropometric-norms.md), [population-variation](./population-variation.md), [nose](./nose.md) | The figures assume different depth levers and baselines. Apply no fixed correction: solve full-perspective cameras with a metric cue and refit focal length when ratios exceed population bounds. |
| C-13 | **Vermilion ratio.** 1.6:1 (aesthetic, young white women) vs measured 1.0–1.8 vs NAW norms implying ≈1.1. | [mouth-lips-teeth](./mouth-lips-teeth.md), [anthropometric-norms](./anthropometric-norms.md), [population-variation](./population-variation.md) | Prior 1.3 ± 0.3, clamp 0.8–2.3, as a QA warning; never impose 1.6. |
| C-14 | **Blender unit scale.** Unit Scale 0.001 with mm length (skull, soft-tissue) vs Unit Scale 1.0 with mm display, 1 BU = 1 m, and mm × 0.001 in Displace strengths and procedural scales (anthropometric, masticatory, fat, skin). | [skull-osteology](./skull-osteology.md), [soft-tissue-thickness](./soft-tissue-thickness.md), [anthropometric-norms](./anthropometric-norms.md), [muscles-mastication-jaw](./muscles-mastication-jaw.md), [fat-compartments](./fat-compartments.md), [skin-wrinkles-microdetail](./skin-wrinkles-microdetail.md) | Pick one per project and convert explicitly. Unit Scale 1.0 with mm display matches most notes' numeric recipes; with 0.001, rescale every mm × 0.001 strength and procedural scale accordingly. |
| C-15 | **Brow and lid–cheek ageing.** Classic lateral brow ptosis vs photographic stability or rise; lid–cheek junction descending (10–12 → 15–20 mm) vs staying near bone (Lambros). | [aging-face](./aging-face.md), [muscles-upper-face](./muscles-upper-face.md), [forehead-brow-temple-hairline](./forehead-brow-temple-hairline.md), [eye-region](./eye-region.md), [smas-ligaments](./smas-ligaments.md) | No forced descent: lateral brow N(young value, 4 mm), junction distance with σ 3 mm; take both from the photos. |
| C-16 | **Ear growth.** ≈0.22 mm/year through adult life 📄 vs "stable until ~70" and "mature by 14". | [ear](./ear.md), [aging-face](./aging-face.md), [child-growth](./child-growth.md), [anthropometric-norms](./anthropometric-norms.md) | Use +0.2·max(0, age − 25) mm with σ 3–4.5 mm; the photo's ear length wins. |
| C-17 | **Bigonial width.** Bone 94–100 / 88–94 mm vs 90–105 / 84–97 mm vs one 3D study 84.6 / 80.7 mm; and photo silhouettes are 10–30 mm wider than caliper bone. | [anthropometric-norms](./anthropometric-norms.md), [jaw-chin-neck](./jaw-chin-neck.md), [muscles-mastication-jaw](./muscles-mastication-jaw.md) | Apply bone priors (M 97 ± 6, F 90 ± 5) only to the bone layer; fit the silhouette through the masseter and fat layers; never compare caliper and silhouette widths. |
| C-18 | **Nasal angle priors.** Nasofrontal priors 125 / 130° vs sampled 124–142°; nasolabial priors 100 / 105° vs 98–116°, with an inconsistent sex difference and population shifts (EAS 85–105°, AFR-W 75–95°). | [nose](./nose.md), [population-variation](./population-variation.md), [forehead-brow-temple-hairline](./forehead-brow-temple-hairline.md), [sexual-dimorphism](./sexual-dimorphism.md) | Keep σ 7–10° and widen when population is unknown; read both angles from a true profile; treat surgical "ideals" as warnings only (weight ≤ 0.1 of the population prior). |
| C-19 | **Mandibular ligament.** Osteocutaneous, 9.1 ± 3.1 mm above the border and 51.1 ± 4.5 mm from the midline, vs only sub-platysmal at 63.1 / 59.3 mm (Minelli). | [smas-ligaments](./smas-ligaments.md), [muscles-lower-face](./muscles-lower-face.md) | Anchor the prejowl sulcus where the photos show it; model the anchor as a stiff strip with a wide positional σ. |
| C-20 | **Pooled vs population tables.** Stephan's pooled T-tables vs ancestry- and BMI-specific tables; matched priors help typical members of a group and hurt atypical ones. | [soft-tissue-thickness](./soft-tissue-thickness.md), [forensic-reconstruction](./forensic-reconstruction.md), [population-variation](./population-variation.md) | Library stance: pooled, balanced priors with covariate slopes (BMI, sex, age) and wide σ, plus measurement of the sitter; population-specific rows only for z-score display when the user picks them. |

## Index of topic notes

Evidence counts are ✅ / 📄 / 🧠 / ↔️ from each note's header.

| Note | What it covers | Evidence |
|---|---|---|
| [aging-face](./aging-face.md) | Layered ageing of bone, fat, ligaments, muscle and skin; age-dependent priors; age as sliders | 3 / 18 / 51 / 29 |
| [anthropometric-norms](./anthropometric-norms.md) | Farkas and 3DFN millimetre norms, population and method offsets, log-space norm priors and z-score gates | 6 / 40 / 82 / 16 |
| [child-growth](./child-growth.md) | Craniofacial growth from birth to adulthood, age-conditioned priors, iris scale for children, minor safeguards | 1 / 17 / 81 / 14 |
| [craniometric-landmarks](./craniometric-landmarks.md) | Bony and skin landmark definitions, naming traps, Frankfort frame, dlib/MediaPipe mapping, landmark σ | 36 / 27 / 71 / 18 |
| [ear](./ear.md) | Auricle anatomy, size and growth, FH-anchored position and tilt, protrusion, ear-specific photo errors | 3 / 26 / 51 / 21 |
| [eye-region](./eye-region.md) | Globe, cornea, orbit, Hertel protrusion, fissure, lids, crease, epicanthus, brows; iris as metric ruler | 18 / 33 / 78 / 19 |
| [face-perception-likeness](./face-perception-likeness.md) | How people recognise faces, cue priorities, caricature and prior shrinkage, likeness review protocol | 0 / 4 / 61 / 17 |
| [facial-asymmetry](./facial-asymmetry.md) | Normal asymmetry magnitudes, perception thresholds, pose-induced asymmetry, symmetric/asymmetric decomposition | 4 / 18 / 45 / 9 |
| [facial-proportions-canons](./facial-proportions-canons.md) | Neoclassical canons and their failure, the golden-ratio myth, artist rules vs measurements, ratio priors | 7 / 30 / 46 / 12 |
| [facs-expressions](./facs-expressions.md) | FACS action units, intensities, ARKit/MediaPipe 52, neutral-frame gating, expression shape keys | 10 / 17 / 62 / 9 |
| [fat-compartments](./fat-compartments.md) | Superficial and deep fat compartments, groove formation, weight and age responses, region-wise thickness fields | 0 / 4 / 63 / 12 |
| [forehead-brow-temple-hairline](./forehead-brow-temple-hairline.md) | Frontal bone and brow ridge, temple layers, forehead tissue depth (corrected), hairline and brows as hair | 14 / 28 / 67 / 17 |
| [forensic-reconstruction](./forensic-reconstruction.md) | Skull-to-face methods and rules, their accuracy, and their inverted use as weak priors for hidden anatomy | 0 / 5 / 54 / 26 |
| [jaw-chin-neck](./jaw-chin-neck.md) | Mandible, chin and neck: gonial angle, vertical pattern, cervicomental angle, profile identifiability | 2 / 0 / 49 / 22 |
| [mouth-lips-teeth](./mouth-lips-teeth.md) | Lip surface anatomy, vermilion ratios, dental support and incisor display, smile arc, mouth priors | 3 / 29 / 44 / 23 |
| [muscles-lower-face](./muscles-lower-face.md) | Orbicularis oris, DAO, DLI, mentalis, platysma, modiolus; lip–chin profile; lower-face AUs | 12 / 50 / 39 / 25 |
| [muscles-mastication-jaw](./muscles-mastication-jaw.md) | Masseter and temporalis size, clenching, bruxism and toxin; bone/muscle/fat split of jaw width | 18 / 31 / 33 / 20 |
| [muscles-mid-face](./muscles-mid-face.md) | Lip elevators and zygomatici, nasolabial fold, smile mechanics and direction priors | 15 / 33 / 44 / 26 |
| [muscles-upper-face](./muscles-upper-face.md) | Frontalis, corrugator, procerus, orbicularis oculi, levator; resting brow and lid; wrinkle directions | 13 / 26 / 56 / 25 |
| [nose](./nose.md) | Nasal skeleton and cartilage, landmarks, which view shows what, profile angles, nose parameter block | 15 / 14 / 71 / 19 |
| [population-variation](./population-variation.md) | Within- vs between-group variation, traits that differ, bias in priors and tools, balanced-prior design | 0 / 1 / 88 / 27 |
| [sexual-dimorphism](./sexual-dimorphism.md) | Size and shape differences by sex, effect sizes and overlap, sex as a continuous latent axis | 10 / 43 / 87 / 23 |
| [skin-wrinkles-microdetail](./skin-wrinkles-microdetail.md) | Skin thickness, wrinkle classes, tension lines, pores, resolution gates, procedural detail | 0 / 1 / 74 / 31 |
| [skull-osteology](./skull-osteology.md) | Skull features that shape the surface, thin vs thick tissue zones, bony priors and ordering constraints | 18 / 44 / 52 / 16 |
| [smas-ligaments](./smas-ligaments.md) | The five-layer laminate, retaining ligaments, glide spaces, grooves as tether/mass boundaries | 5 / 15 / 54 / 18 |
| [soft-tissue-thickness](./soft-tissue-thickness.md) | Forensic tissue-depth tables, covariates and method effects, log-normal two-layer priors | 4 / 25 / 52 / 20 |
| **Total** | 26 notes | **217 / 579 / 1,555 / 514** |

Related notes in other areas that these notes lean on: [`../blender/reference-camera-setup.md`](../blender/reference-camera-setup.md), [`../blender/eyes-modeling-blender.md`](../blender/eyes-modeling-blender.md), [`../blender/skin-shading.md`](../blender/skin-shading.md), [`../reconstruction/landmark-detection.md`](../reconstruction/landmark-detection.md), [`../reconstruction/camera-pose-solving.md`](../reconstruction/camera-pose-solving.md) and [`../reconstruction/identity-embeddings.md`](../reconstruction/identity-embeddings.md).
