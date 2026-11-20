# Natural facial asymmetry

> Every normal adult face is asymmetric. Whole-face asymmetry, measured as the RMS distance between a face and its registered mirror image, averages about 0.8 mm [6][7]. Individual bilateral landmarks differ by 0.6–4.6 mm, mostly in the lower and lateral face [2], and the midline itself bends [1]. Observers notice asymmetry at roughly 2–4 mm or 3–4°, depending on the feature, the observer and the viewing time; eyelids are the most sensitive feature [9][10][11][12]. Mirroring a sculpt deletes exactly these visible, identity-bearing differences, so use symmetry only for block-out, topology and rigging, and keep asymmetry as a separate, measured layer that can be switched on and off. The opposite error is just as real: 3° of head yaw or 2° of roll in a photo creates more apparent asymmetry than the anatomy has, so asymmetry must be estimated in 3D from pose-solved views.

Evidence status: 5 ✅ / 21 📄 / 49 🧠 / 9 ↔️ — 🧠 items are queued for web verification.

## Key facts

**How much**
- **Asymmetry is universal, and no cut-off separates normal from abnormal.** No published threshold separates normal from increased asymmetry [1]. Some slight asymmetry is always present [8], and asymmetry increases with age [7]. ✅
- **Whole-face surface asymmetry is about 0.8 mm RMSD.** It was 0.8 ± 0.2 mm in 191 people aged 0.3–88 years [7]. In healthy volunteers scanned with 3dMD it was 0.80 ± 0.24 mm, measuring the face against its reflection about the plane of maximum symmetry [6]. The link from [6] to that URL was inferred from search excerpts. The value may come from Taylor et al. 2014, the same research group as [7], so treat [6] and [7] as one line of evidence. 📄
- **Per facial third:** upper 0.5 mm, middle 0.6 mm, lower 0.6 mm [7]. 📄 These cannot have used the same registration as the whole-face value: with a shared registration, the whole-face RMS would have to fall between the RMS values of its parts. Either each third was aligned separately, or the whole-face region also covers the periphery (this note's arithmetic). 🧠
- **Landmark differences are several times larger than the surface RMSD.** In 48 adults with normal occlusion (CBCT soft tissue, 9 bilateral pairs), right–left differences ran from 0.6 to 4.6 mm, and were larger at lower and lateral landmarks [2]. 📄 Closest-point surface RMSD ignores sliding along the surface, so correspondence-based measures (landmark or dense correspondence) always read higher. 🧠
- **2D skeletal ranges are inflated by the method.** Posteroanterior cephalograms give a "normal" right–left range of 0–12 mm [3]. ↔️ (conflicts with [2][7])
- **Index metrics are not in millimetres.** Normal male controls scored 1.77–3.38 on a 10-landmark 3D asymmetry index [5]. 📄
- **The facial midline bends.** In a birth cohort, mean landmark offsets were about 0.25 mm, and lower-face midline landmarks shifted to the opposite side from the upper face [1] (figure from an excerpt). 📄 In adults, chin and nasal-tip deviations of 1–3 mm are common, and the upper face is the most stable midline reference. 🧠

**Where**
- **The lower and lateral face is the most asymmetric; the upper face is the least** [2][7][1]. ✅ Among dentofacial-deformity patients with asymmetry, Severt & Proffit (1997) reported chin involvement in roughly three-quarters of cases, the midface in about a third and the upper face in only about 5%. This is a patient population, not normal faces. 🧠
- **Soft features are more asymmetric than bone.** Brows (from habitual frontalis use), eyelid creases and openings, the nasal tip and columella (septal deviation), mouth corners and ears all carry visible asymmetry where the bone beneath is nearly symmetric. Left–right differences of a few millimetres in ear height and protrusion are routine (see `anatomy/ear.md`). 🧠
- **Asymmetry grows with age** [7]. 📄 The usual explanations are soft-tissue ptosis, tooth loss, a preferred chewing side and sleep posture. 🧠

**When it is seen**
- **Perception thresholds depend on the feature and fall between about 2 and 4 mm.** ↔️
  - Eyelid position at rest is the most sensitive feature, at about 2 mm [10].
  - Naive observers see mouth-corner or brow asymmetry at about 3 mm [9].
  - Laypersons and general dentists put the threshold of abnormality at 4 mm; orthodontists and oral surgeons put it at 2 mm [11].
  - Asymmetry under about 3–4 mm or 3–4° is generally not recognised [12] (URL attribution unconfirmed).
  - 3 mm is used as a treatment-planning convention [4].
- **The degree and millimetre thresholds agree once converted.** A 3–4° cant across a baseline of about 60 mm (pupils or mouth corners) is a 3–4 mm height difference (Table D). 🧠 A 6° lower-face deviation was detected only by orthodontists [11]. 📄
- **Viewing time matters** [9]. 📄 Longer inspection lowers detection thresholds, and a likeness review is long inspection.
- **An abnormality threshold is not a likeness threshold.** Studies [9]–[12] ask whether a face looks asymmetric or abnormal. Likeness asks whether the face matches the person the viewer knows. Familiar viewers are probably more sensitive to that, but no study has measured it. 🧠
- **Metrics and thresholds from different studies are not interchangeable** [10][8]. ✅

**Why mirroring hurts likeness**
- **Mirroring one half-face distorts the face.** Reflecting one half made some features abnormally large or small; later studies blended each face with its mirror instead [15]. 📄 Left–left and right–right chimeras look like different people (classic chimeric-face work, e.g. Gilbert & Bakan 1973). 🧠
- **People know their own mirror image.** Subjects prefer a mirror-reversed photo of themselves, while their friends prefer the true image (Mita, Dermer & Knight 1977). 🧠 This effect exists only because faces are asymmetric. The sitter and their friends will judge the same sculpt differently.
- **Symmetrising pulls a face toward the average, and distinctiveness helps recognition.** Caricatures improve identification and distinctive faces are easier to recognise (Rhodes, Brennan & Carey 1987; Valentine 1991). Removing asymmetry therefore works as an anti-caricature (inference). 🧠
- **The symmetry preference concerns attractiveness, not likeness** [13][14]. ✅ Even for attractiveness the evidence is mixed: Swaddle & Cuthill 1995 found perfectly symmetric faces less attractive, while Perrett et al. 1999 found symmetry preferred. ↔️ 🧠
- **Expressions are more asymmetric than the face at rest.** The left hemiface tends to express emotion more intensely (Sackeim, Gur & Saucy 1978). 🧠 Dynamic asymmetry belongs in left/right-split shape keys, not in the neutral sculpt.

## Numbers & reference tables

### A. Magnitude in normal faces

| Measure | Value | Units | Population / n | Method | Src | Status |
|---|---|---|---|---|---|---|
| Whole-face RMSD vs mirror | 0.8 ± 0.2 | mm | 191, ages 0.3–88 y | 3D surface vs mirror | [7] | 📄 |
| Whole-face RMSD vs mirror | 0.80 ± 0.24 | mm | healthy volunteers (n unknown) | 3dMD, plane of max. symmetry | [6] (attribution unconfirmed) | 📄 |
| Upper / middle / lower third RMSD | 0.5 / 0.6 / 0.6 | mm | 191 | as above, region alignment unclear | [7] | 📄 |
| Bilateral landmark R–L difference | 0.6–4.6 | mm | 48 adults, normal occlusion | CBCT soft tissue, 9 pairs | [2] | 📄 |
| Skeletal R–L difference | 0–12 | mm | normal adults | 2D PA cephalogram | [3] | ↔️ |
| Mean midline landmark offset | ≈0.25 | mm | birth cohort to 6 y | 3D longitudinal | [1] | 📄 |
| 3D asymmetry index, 10 landmarks | 1.77–3.38 | index | 25 male controls | 3D CT | [5] | 📄 |

### B. Working left–right ranges by feature (adults at rest; estimates for setting priors, wide uncertainty)

| Feature | Typical L–R difference | Visible from about | Notes | Status |
|---|---|---|---|---|
| Pupil / outer eye corner height | 0–1.5 mm | 2 mm [10] | bony orbits nearly symmetric | 🧠 |
| Upper-lid margin / eye opening | 0.5–1.5 mm | 2 mm [10] | lid crease height varies more | 🧠 |
| Brow height | 1–3 mm | 3 mm [9] | habitual, changes with expression | 🧠 |
| Nasal tip / columella off midline | 0.5–3 mm | 2–3 mm | septal deviation is common | 🧠 |
| Nostril and alar-base shape | 0.5–2 mm | — | nostril outlines often differ visibly | 🧠 |
| Mouth-corner height | 0.5–2 mm | 3 mm [9] | larger in a smile | 🧠 |
| Chin off midline (pogonion/menton) | 0–3 mm | 3–4 mm [12] | the most common clinical asymmetry | 🧠 |
| Jaw angle (gonion) | 1–4 mm | — | masseter bulk, ramus height | 🧠 |
| Ear height / protrusion | 0–5 mm / 0–4 mm | — | glasses sit tilted on the face | 🧠 |

### C. Perception and clinical thresholds

| Feature / context | Threshold | Units | Observers | Src | Status |
|---|---|---|---|---|---|
| Eyelid position at rest | ≈2 | mm | literature review | [10] | 📄 |
| Mouth corner, brow | ≈3 | mm | naive observers, paralysis model | [9] | 📄 |
| Threshold of abnormality (frontal view) | 4 vs 2 | mm | laypeople/GPs vs orthodontists/OMFS | [11] | ↔️ |
| Lower-face deviation | 6 | ° | detected by orthodontists only | [11] | 📄 |
| Not recognised below | 3–4 / 3–4 | mm / ° | prospective study | [12] | 📄 |
| Treatment cut-off (convention) | 3 | mm | clinical 3D/AI | [4] | 📄 |

### D. How pose creates apparent asymmetry, and how angles convert to mm

Formulas: yaw θ → half-width difference 2·Δz·sin θ (Δz = depth of the bilateral pair behind the midline reference); roll or cant φ over baseline b → b·sin φ; midline deviation angle α measured over length L → L·tan α. All values in mm (this note's arithmetic).

| Case | 1° | 3° | 5° | 10° | Status |
|---|---|---|---|---|---|
| Yaw, Δz = 20 mm (alar base vs nose tip, approx.) | 0.7 | 2.1 | 3.5 | 6.9 | 🧠 |
| Yaw, Δz = 40 mm (eye corners vs nose tip, approx.) | 1.4 | 4.2 | 7.0 | 13.9 | 🧠 |
| Yaw, Δz = 80 mm (jaw angle/cheekbone, approx.) | 2.8 | 8.4 | 13.9 | 27.8 | 🧠 |
| Roll/cant, b = 60 mm (pupils, mouth corners) | 1.0 | 3.1 | 5.2 | 10.4 | 🧠 |
| Midline angle, L = 120 mm (nasion→menton) | 2.1 | 6.3 | 10.5 | 21.2 | 🧠 |

A face 10 cm off-centre in a frame shot from 40 cm is seen about 14° obliquely. A "6° lower-face deviation" is about 12 mm if it is measured from nasion, so the definition behind [11] matters. ↔️

## Applying this to photo→3D face sculpting in Blender

1. **Audit the photos before trusting any asymmetry.**
   - Mirrored selfies flip the person's real asymmetry; many front cameras save mirrored images depending on a setting. Check text, the hair part, moles and scars. 🧠
   - Make sure the L/R labels follow the subject's left.
   - Shoot the frontal from 1.5 m or more with the subject centred, a relaxed neutral expression and even lighting. Side light turns into fake geometry in shading-based depth and normal estimates. 🧠
   - Pair the yaw views (±30°, ±60°, ±90°) so both sides are seen equally.
2. **Fix the symmetry frame.** Solve the poses in 3D. Fit the plane of best symmetry, weighting the upper face most. Put the object origin and local X axis on that plane and apply the rotation: Sculpt-mode symmetry and the Mirror modifier mirror about the object's local origin and axes. 🧠 Never snap the nose tip or chin onto x = 0 [1].
3. **Block out with symmetry on** (Sculpt X symmetry, a Mirror modifier with Clipping, Symmetrize). This covers the cranium, jaw mass, orbit spacing, topology and UVs. **Keep the topology symmetric for good**, even when the shape is not. Topology Mirror, Mirror Shape Key (Topology), .L/.R vertex groups and left/right FACS splitting all depend on it. 🧠
4. **Turn symmetry off at the first secondary-form pass,** or as soon as any Table B feature differs by 1 mm or more consistently across two views. Keep the symmetric shape S as Basis and the asymmetric shape S + A as a key named "Asym". Sculpt mode writes into the active shape key on a plain mesh. It cannot do this with Dyntopo, and Multires detail levels are not shape-keyable (check this for your Blender version). 🧠 So sculpt asymmetry at base resolution, then use New Shape from Mix or apply the key, and only then add Multires. (The earlier draft suggested storing asymmetry as a Multires level; that does not give you a layer you can switch on and off.)
5. **Match features in perceptual order:**
   1. eyelids and eye openings (2 mm);
   2. brows and mouth corners (3 mm);
   3. nasal tip, columella and nostrils;
   4. chin and jaw deviation, and cant angles (3–4°);
   5. cheeks and ears.

   Snap empties to vertices and read the left/right values in the N-panel. Cant = atan(Δy/Δx).
6. **Sanity-check the result** by registering the finished head to its mirror.
   - In an adult, whole-face RMSD should be about 0.5–1.5 mm, higher with age [6][7], and landmark differences about 0.5–5 mm [2].
   - An RMSD near 0 means the asymmetry has been symmetrised away.
   - Several mm of global RMSD points to a pose, lens or L/R-label error. If none is found, it may be a real condition, which the sitter should confirm.
7. **Never mirror detail or texture.** Pores, wrinkles, moles, scars and photo textures must not be mirrored: a duplicated mole immediately reads as fake. Project-paint each side from its own photos. 🧠
8. **Review the result.**
   - Compare against camera-matched background images at the solved focal lengths, and take your time [9].
   - Flip the render and the photo together, for example with the compositor's Flip node, to refresh your eye.
   - Show the sitter a mirrored render as well, because they know their face from the mirror. 🧠
   - Scrub the Asym key from 0 to 1 to 1.5 (raise the slider maximum) to see what the asymmetry contributes.
9. **If one side is hidden in every photo,** build that side from the blended symmetric S, not a copy of the other half [15], and mark it as low-confidence.

## Algorithmic implications

- **Decomposition** (Klingenberg et al. 2002; Mardia et al. 2000).
  - Reflect with M = diag(−1, 1, 1), swap the L/R labels (P), and align MPX to X with `face3d/geometry/procrustes.py::umeyama`, which returns a proper rotation.
  - Then S = ½(X + aligned MPX) and A = X − S.
  - Rotating X by half the alignment rotation puts the symmetry plane at x = 0. 🧠
- **Gauge.** The antisymmetric subspace contains three rigid degrees of freedom: x-translation, yaw and roll. Procrustes removes them. The symmetry residuals `(X_l − M·X_r)/sigma_sym` and the midline residuals `x_i/sigma_mid` in `face3d/solve/bundle.py` assume the head frame is the symmetry frame. Re-estimate that frame after each outer iteration and let the cameras absorb the rigid change. Otherwise a 2° frame error reads as about 3 mm of A at lateral landmarks (Table D), and the prior fights it. 🧠
- **Plane estimation.** Use robust weights: upper face 1.0 (inner and outer eye corners, nasion, glabella, orbitale), midface 0.5, lower face 0.25, ears 0.1, with a Huber loss at about 1 mm. 🧠
- **Priors.** These σ values are per axis on d = X_l − M·X_r, the full left–right difference, which equals 2A. Mean |d| ≈ 1.6σ. They are design values to calibrate, not published priors. 🧠

| Landmarks | σ_sym per axis (mm) | σ_mid on midline x (mm) |
|---|---|---|
| Inner/outer eye corners, pupils, lid margins | 0.7–1.0 | — |
| Nasion, glabella | — | 0.75–1.0 |
| Brows | 1.5 (vertical 2.0) | — |
| Alare, subalare, orbitale, zygion | 1.0–1.5 | — |
| Pronasale, columella, subnasale | — | 1.5–2.0 |
| Cheilion; labrale superius/inferius | 1.5–2.0 | 1.5 |
| Pogonion, menton | — | 2.0–3.0 |
| Gonion | 2.5–3.0 | — |
| Ear landmarks | 3.0–4.0 | — |

  The current defaults (`sigma_sym = 2.0` and `sigma_mid = 1.5`, both uniform) are acceptable fallbacks. Replace them with per-landmark arrays. Use a Student-t (ν ≈ 4) or Huber loss on the symmetry residuals so that real large asymmetries (an old fracture, palsy, hemifacial microsomia, tooth loss) survive. Calibrate by sampling: generated faces should show |d| mostly between 0.5 and 4.5 mm [2] and a surface RMSD near 0.8 mm [6][7].
- **Schedule.** `symmetry_mode`:
  - `assist` multiplies σ_sym by 0.25 during the initial pose and coarse shape fit, so that pose and asymmetry do not get confused early;
  - `prior` uses the table values for refinement;
  - `enforce` is a user block-out option only, never the output.
- **Pose–asymmetry confound.** In a single view, yaw/roll and A trade off against each other. Accept A for a pair only when at least two views about 30° or more apart observe it. Otherwise shrink σ_A by 4× and mark it low-confidence. Take the posterior σ of each d from (JᵀJ)⁻¹ in the LM solve, and show asymmetry only where |d| exceeds 2σ_post. 🧠
- **Detector noise.** In a typical portrait the face spans about 140 mm over 600–1000 px, so 1 px is about 0.15–0.25 mm. A detector error of 3–5 px therefore puts 0.5–1.2 mm of noise into each view, about the size of real asymmetry. Average over views. Detectors trained with flip augmentation may be biased toward symmetric placement (a hypothesis). 🧠
- **Mirrored-input test.** Refit each view with u → W − u and the L/R labels swapped. If the flipped fit consistently lowers the reprojection error and A then agrees with the other views, flag the photo as mirrored and ask the user. The test is weak when |A| is small. 🧠
- **Template warping.** Use the RBF warp in `face3d/geometry/rbf.py` in two stages: base = warp(template, S), then Asym = warp(template, S + A) − base, exported as a Blender shape key. Never symmetrise the target landmarks. Ship the template with an explicit vertex mirror map.
- **Report.**
  - Measurements: global and per-third RMSD against the mirror; |d| for each pair; bipupillary, intercanthal, commissural and brow cants; nasal-tip and pogonion deviation in mm and degrees.
  - Flags: eyelid ≥2 mm [10]; brow or mouth ≥3 mm [9]; cant ≥3° [12]; global RMSD above 1.5 mm or below 0.3 mm. 🧠
  - Flags ask the user to confirm; nothing is auto-corrected.
- **Evaluation and tests.**
  - Score errors on S and A separately, and add an asymmetry-recovery score: the cosine between A_est and A_true, and the ratio |A_est|/|A_true|. A symmetrised fit can score a low total error while recovering none of the asymmetry. 🧠
  - In `face3d/synthetic.py`, `random_subject` adds isotropic `asym_sd = 1.0` to every coordinate. Scale it by region instead, and add a test of a symmetric face at 3° yaw that must return |A| ≈ 0.

## Disagreements, myths & open questions

- **Different metrics give different numbers** ↔️: 0.25 mm child midline offsets [1], 0.6–4.6 mm landmark differences [2], 0.8 mm surface RMSD [6][7] and 0–12 mm 2D skeletal ranges [3]. Never mix them.
- **Perception thresholds disagree** (2–4 mm and 3–6°) ↔️. The claim that asymmetry under 3 mm is undetectable [4] conflicts with the 2 mm eyelid and specialist thresholds [10][11].
- **Directional asymmetry is unresolved.** Some studies find the right side systematically larger, others the left or neither, and some patient samples report the chin deviating more often to one side. ↔️ 🧠 The Raine-study claim (the midline deviating to the right in almost all young adults; more than half of faces with over 2 mm of asymmetry by surface area) is still unsourced.
- **Myth: symmetric = attractive = better likeness.** The attractiveness findings are themselves contested (see Key facts), and none of them measures likeness.
- **Myth: mirroring a half-face shows the person's symmetric version.** It produces a chimera with distorted widths. Blend with the mirror instead [15].
- **Myth: asymmetry measured in a photo is anatomy.** Pose, lens, lighting, expression and mirrored files all create apparent asymmetry (Table D).
- **Nuance about who notices.** Unfamiliar viewers often miss a mirror-flipped face, because recognition generalises across mirror views (Troje & Bülthoff 1998). The sitter and familiar viewers do notice (Mita et al. 1977). So the strict test of likeness is family, friends and the sitter. 🧠
- **3DMM regressors probably under-reconstruct asymmetry.** A small number of components plus regularisation toward a near-symmetric mean shape should suppress it. This is plausible but untested here. 🧠
- **Open questions:**
  - Is there direct evidence that symmetrising a 3D head lowers likeness or identity ratings? None found.
  - Adult dense-surface asymmetry norms by region, sex and ancestry.
  - The age slope in [7].
  - The just-noticeable displacement of a feature in a familiar face (Haig 1984 suggests high sensitivity; moderate confidence in that reference).
  - The angle definition behind the 6° figure in [11].
  - Re-checks against full texts: the attribution of [6], the 3–4 mm / 3–4° statement in [12], and the 0.25 mm figure in [1].
- **Unsourced, and kept out of the priors:** perception thresholds at asymmetry-index values of about 1.1 and 3.1 (2024); "directional asymmetry does not affect judgements but fluctuating asymmetry does"; "attractiveness correlates only weakly with 3D asymmetry indices".

## Sources

1. A longitudinal study of facial asymmetry in a normal birth cohort up to 6 years of age and the predisposing factors — https://pmc.ncbi.nlm.nih.gov/articles/PMC10389059/ — paper — 2023
2. Three-dimensional soft tissue analysis for the evaluation of facial asymmetry in normal occlusion individuals — https://pubmed.ncbi.nlm.nih.gov/23112933/ — paper — 2012
3. Analysis of hard tissue facial symmetry after unilateral mandibular reconstruction — https://pmc.ncbi.nlm.nih.gov/articles/PMC8166985/ — paper — 2021
4. Precision Assessment of Facial Asymmetry Using 3D Imaging and Artificial Intelligence — https://pmc.ncbi.nlm.nih.gov/articles/PMC12565447/ — paper — 2025
5. Quantification of three-dimensional facial asymmetry for diagnosis and postoperative evaluation of orthognathic surgery — https://pmc.ncbi.nlm.nih.gov/articles/PMC7248163/ — paper — 2020
6. Facial asymmetry assessment in adults using three-dimensional surface imaging — https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4614853/ — paper — 2015
7. The Relationship between Age and Facial Asymmetry — https://pubmed.ncbi.nlm.nih.gov/30511968/ — paper — 2018
8. Comparison of Different 3D Surface Registration-Based Methods to Assess Facial Asymmetry — https://pmc.ncbi.nlm.nih.gov/articles/PMC11593128/ — paper — 2024
9. Threshold of visual perception of facial asymmetry in a facial paralysis model — https://pubmed.ncbi.nlm.nih.gov/21242426/ — paper — 2011
10. Discriminative Thresholds in Facial Asymmetry: A Review of the Literature — https://pubmed.ncbi.nlm.nih.gov/28200081/ — review — 2017
11. Thresholds of Abnormality Perception in Facial Esthetics among Laypersons and Dental Professionals: Frontal Esthetics — https://pmc.ncbi.nlm.nih.gov/articles/PMC7603600/ — paper — 2020
12. Limits in the Perception of Facial Symmetry – A Prospective Study — https://pmc.ncbi.nlm.nih.gov/articles/PMC11595402/ — paper — 2024
13. Preferences for symmetry in human faces in two cultures: UK and Hadza — https://pmc.ncbi.nlm.nih.gov/articles/PMC2293939/ — paper — 2008
14. Attractiveness of facial averageness and symmetry in non-western cultures — https://pubmed.ncbi.nlm.nih.gov/11430245/ — paper — 2001
15. Measuring facial symmetry: a perception-based approach using 3D shape and color — https://pubmed.ncbi.nlm.nih.gov/25296669/ — paper — 2014

**Further reading (by name, not yet linked)**
- Farkas, *Anthropometry of the Head and Face* (2nd ed., 1994)
- Taylor et al. 2014, "Quantitative facial asymmetry: using three-dimensional photogrammetry to measure baseline facial surface symmetry", J Craniofac Surg (the probable origin of 0.80 ± 0.24 mm)
- Severt & Proffit 1997, "The prevalence of facial asymmetry in the dentofacial deformities population at the University of North Carolina"
- Ferrario, Sforza, Poggio & Tartaglia 1994, "Distance from symmetry: a three-dimensional evaluation of facial asymmetry", J Oral Maxillofac Surg
- Padwa, Kaiser & Kaban 1997, "Occlusal cant in the frontal plane as a reflection of facial asymmetry", J Oral Maxillofac Surg
- Van Valen 1962, "A study of fluctuating asymmetry", Evolution; Palmer & Strobeck 1986, "Fluctuating asymmetry: measurement, analysis, patterns", Annu Rev Ecol Syst
- Klingenberg, Barluenga & Meyer 2002, "Shape analysis of symmetric structures", Evolution; Mardia, Bookstein & Moreton 2000, "Statistical assessment of bilateral symmetry of shapes", Biometrika
- Mita, Dermer & Knight 1977, "Reversed facial images and the mere-exposure hypothesis", J Pers Soc Psychol
- Gilbert & Bakan 1973, "Visual asymmetry in perception of faces", Neuropsychologia
- Sackeim, Gur & Saucy 1978, "Emotions are expressed more intensely on the left side of the face", Science
- Rhodes, Brennan & Carey 1987, caricature identification, Cognitive Psychology; Valentine 1991, face-space account of distinctiveness, QJEP
- Troje & Bülthoff 1998, "How is bilateral symmetry of human faces used for recognition of novel views?", Vision Research
- Swaddle & Cuthill 1995, "Asymmetry and human facial attractiveness: symmetry may not always be beautiful", Proc R Soc B; Perrett et al. 1999, "Symmetry and human facial attractiveness", Evol Hum Behav
- Kokich, Kiyak & Shapiro 1999, "Comparing the perception of dentists and lay people to altered dental esthetics", J Esthet Dent
- Haig 1984, "The effect of feature displacement on face recognition", Perception
- Umeyama 1991, "Least-squares estimation of transformation parameters between two point patterns", IEEE TPAMI
