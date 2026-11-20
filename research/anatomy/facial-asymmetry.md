# Natural facial asymmetry

> Every normal adult face is asymmetric. Whole-face asymmetry (the RMS distance between a face and its registered mirror image) averages about 0.8 mm [6][7], but bilateral landmarks differ by 0.6–4.6 mm, mostly in the lower and lateral face [2], and the midline itself bends [1]. Observers notice asymmetry at roughly 2–4 mm or 3–4°, depending on feature, observer and viewing time; eyelids are the most sensitive [9][10][11][12]. Mirroring a sculpt deletes exactly these visible, identity-bearing differences, so keep symmetry for block-out, topology and rigging, and hold the asymmetry as a separate, measured layer you can switch on and off. The reverse error is just as real: 3° of head yaw or 2° of roll in a photo creates more apparent asymmetry than the anatomy has, so estimate asymmetry in 3D from pose-solved views.

Evidence status: 4 ✅ / 18 📄 / 45 🧠 / 9 ↔️ — 🧠 items are queued for web verification.

## Key facts

**How much**
- **Asymmetry is universal.** No published threshold separates normal from increased asymmetry [1], some slight asymmetry is always present [8], and asymmetry increases with age [7]. ✅
- **Whole-face surface asymmetry is about 0.8 mm RMSD.** Reported values: 0.8 ± 0.2 mm in 191 people aged 0.3–88 years [7], and 0.80 ± 0.24 mm in healthy volunteers scanned with 3dMD, measured against the reflection about the plane of maximum symmetry [6]. The URL for [6] was inferred from search excerpts. Verification found that PMC4614853 describes 55 adults (28 symmetric, 27 asymmetric faces, 3dMDface), so the 0.80 ± 0.24 mm figure probably does not come from it and stays unconfirmed. The 0.80 ± 0.24 mm figure may come from Taylor et al. 2014, the same group as [7], so count [6] and [7] as one line of evidence. 📄
- **Per facial third:** upper 0.5 mm, middle 0.6 mm, lower 0.6 mm [7]. 📄 If one registration had been used throughout, the whole-face RMS would have to lie between its parts' values. So the thirds were aligned separately, or the whole-face region also covers the periphery (arithmetic). 🧠
- **Landmark differences are several times larger than surface RMSD.** In 48 normal-occlusion adults (CBCT soft tissue, 9 bilateral pairs), right–left differences were 0.6–4.6 mm, larger at lower and lateral landmarks [2]. 📄 Closest-point RMSD ignores sliding along the surface, so correspondence-based measures always read higher. 🧠
- **2D skeletal ranges are inflated by the method.** Posteroanterior cephalograms give a "normal" range of 0–12 mm [3]. ↔️ This conflicts with [2][7].
- **The midline bends.** In a birth cohort, landmarks sat about 0.25 mm off the midline on average, and lower-face midline landmarks shifted to the opposite side from upper-face ones [1] (figure from a search excerpt). 📄 In adults, the chin and nasal tip are commonly 1–3 mm off the midline; the upper face is the most stable midline reference. 🧠

**Where**
- **The lower and lateral face is the most asymmetric; the upper face is the least** [2][7][1]. ✅
- **Clinical pattern (patients, not normal faces).** In dentofacial-deformity patients with asymmetry, Severt & Proffit (1997) found the chin involved in about three-quarters of cases, the midface in about a third and the upper face in about 5%. 🧠
- **Soft features are more asymmetric than the bone beneath them.** Brows (habitual frontalis use), lid creases and eye openings, the nasal tip and columella (septal deviation), the mouth corners and the ears (see `anatomy/ear.md`) all carry visible asymmetry. 🧠
- **Asymmetry grows with age** [7]. 📄 Likely causes are tissue ptosis, tooth loss, a preferred chewing side and sleep posture. 🧠

**When it is seen**
- **Perception thresholds are feature-specific, about 2–4 mm** (Table C) ↔️. Eyelid position at rest is the most sensitive, at about 2 mm [10]. Mouth corners and brows are seen at about 3 mm [9]. Laypeople put the threshold of abnormality at 4 mm, specialists at 2 mm [11].
- **Degree and millimetre thresholds agree once converted.** A 3–4° cant across a ~60 mm baseline, such as the pupils or the mouth corners, is a 3–4 mm height difference (Table D). 🧠
- **Viewing time matters.** Longer inspection lowers the threshold [9], and a likeness review is long inspection. 📄
- **An abnormality threshold is not a likeness threshold.** Studies [9]–[12] ask "does this face look asymmetric?", while likeness asks "is this the person I know?". Familiar viewers are probably more sensitive, but no study has measured it. 🧠
- **Metrics and thresholds from different studies are not interchangeable** [10][8]. ✅

**Why mirroring hurts likeness**
- **Mirroring a half-face distorts the face.** It made some features abnormally large or small, so later studies blended each face with its mirror instead [15]. 📄 Left–left and right–right chimeras look like different people (Gilbert & Bakan 1973). 🧠
- **People know their own mirror image.** Sitters prefer a mirror-reversed photo of themselves, while their friends prefer the true image (Mita, Dermer & Knight 1977). 🧠 This only happens because faces are asymmetric, so the sitter and their friends will judge the same sculpt differently.
- **Symmetrising pulls a face toward the average.** Distinctiveness and caricature help recognition (Rhodes, Brennan & Carey 1987; Valentine 1991). Removing asymmetry therefore works as an anti-caricature (inference). 🧠
- **The symmetry preference concerns attractiveness, not likeness** [13][14]. ✅ Even for attractiveness the evidence is mixed: Swaddle & Cuthill 1995 found perfectly symmetric faces less attractive, while Perrett et al. 1999 found symmetry preferred. ↔️
- **Expressions are more asymmetric than the face at rest.** The left hemiface tends to express emotion more intensely (Sackeim, Gur & Saucy 1978). 🧠 Model expressions as left/right-split shape keys, not in the neutral sculpt.

## Numbers & reference tables

### A. Magnitude in normal faces

| Measure | Value | Units | Population / n | Method | Src | Status |
|---|---|---|---|---|---|---|
| Whole-face RMSD vs mirror | 0.8 ± 0.2 | mm | 191, ages 0.3–88 y | 3D surface vs mirror | [7] | 📄 |
| Whole-face RMSD vs mirror | 0.80 ± 0.24 | mm | healthy volunteers, n unknown | 3dMD, plane of max. symmetry | [6] (attribution unconfirmed) | 📄 |
| Upper / middle / lower third RMSD | 0.5 / 0.6 / 0.6 | mm | 191 | as above | [7] | 📄 |
| Bilateral landmark R–L difference | 0.6–4.6 | mm | 48 adults, normal occlusion | CBCT soft tissue, 9 pairs | [2] | 📄 |
| Skeletal R–L difference | 0–12 | mm | normal adults | 2D PA cephalogram | [3] | ↔️ |
| Mean midline landmark offset | ≈0.25 | mm | birth cohort to 6 y | 3D, longitudinal | [1] | 📄 |
| 3D asymmetry index, 10 landmarks | 1.77–3.38 | index (not mm) | 25 male controls | 3D CT | [5] | 📄 |

### B. Working left–right ranges by feature (adults at rest; estimates for priors, wide uncertainty)

| Feature | Typical L–R difference | Visible from about | Note | Status |
|---|---|---|---|---|
| Pupil / outer eye-corner height | 0–1.5 mm | 2 mm [10] | orbits nearly symmetric | 🧠 |
| Upper-lid margin / eye opening | 0.5–1.5 mm | 2 mm [10] | lid crease varies more | 🧠 |
| Brow height | 1–3 mm | 3 mm [9] | habitual | 🧠 |
| Nasal tip / columella off midline | 0.5–3 mm | 2–3 mm | septal deviation | 🧠 |
| Nostril / alar base | 0.5–2 mm | — | shapes often differ | 🧠 |
| Mouth-corner height | 0.5–2 mm | 3 mm [9] | larger in a smile | 🧠 |
| Chin off midline | 0–3 mm | 3–4 mm [12] | most common clinical asymmetry | 🧠 |
| Gonion (jaw angle) | 1–4 mm | — | masseter, ramus | 🧠 |
| Ear height / protrusion | 0–5 / 0–4 mm | — | glasses sit tilted | 🧠 |

### C. Perception and clinical thresholds

| Feature / context | Threshold | Units | Observers | Src | Status |
|---|---|---|---|---|---|
| Eyelid position at rest | ≈2 | mm | literature review | [10] | 📄 |
| Mouth corner, brow | ≈3 | mm | naive observers, paralysis model | [9] | 📄 |
| Abnormality, frontal view | 4 vs 2 | mm | laypeople and GPs vs orthodontists and OMFS | [11] | ↔️ |
| Lower-face deviation | 6 | ° | orthodontists only | [11] | 📄 |
| Not recognised below | 3–4 / 3–4 | mm / ° | prospective study (attribution unconfirmed) | [12] | 📄 |
| Treatment cut-off (convention) | 3 | mm | clinical 3D/AI study | [4] | 📄 |

### D. Pose-induced apparent asymmetry and angle-to-mm conversion (mm, arithmetic)

Yaw θ changes the two half-widths by 2·Δz·sin θ, where Δz is the depth of the bilateral pair behind the midline reference. A cant φ across a baseline b is b·sin φ. A midline angle α over a length L is L·tan α.

| Case | 1° | 3° | 5° | 10° | Status |
|---|---|---|---|---|---|
| Yaw, Δz 20 mm (alar base vs nose tip) | 0.7 | 2.1 | 3.5 | 6.9 | 🧠 |
| Yaw, Δz 40 mm (eye corners vs nose tip) | 1.4 | 4.2 | 7.0 | 13.9 | 🧠 |
| Yaw, Δz 80 mm (jaw angle, cheekbone) | 2.8 | 8.4 | 13.9 | 27.8 | 🧠 |
| Roll/cant, b 60 mm (pupils, mouth corners) | 1.0 | 3.1 | 5.2 | 10.4 | 🧠 |
| Midline angle, L 120 mm (nasion→menton) | 2.1 | 6.3 | 10.5 | 21.2 | 🧠 |

Δz values are approximate. A face 10 cm off-centre in a frame shot from 40 cm is seen about 14° obliquely. Measured from nasion, the 6° deviation in [11] is about 12 mm, so the definition [11] used matters. ↔️

## Applying this to photo→3D face sculpting in Blender

1. **Audit the photos before trusting any asymmetry.**
   - Mirrored selfies flip the real asymmetry. Check text, the hair part and moles. 🧠
   - Label L/R by the subject's left.
   - Shoot the frontal from at least 1.5 m, with the subject centred, a neutral expression and even light. Side light becomes fake geometry in shading-based depth or normal estimators. 🧠
   - Pair the yaw views (±30°, ±60°, ±90°) so both sides are seen equally.
2. **Fix the symmetry frame.**
   - Solve the poses in 3D, then fit the plane of best symmetry with the upper face weighted most.
   - Put the object origin and local X axis on that plane and apply the rotation. Sculpt symmetry and the Mirror modifier both mirror about the object's local origin and axes. 🧠
   - Never snap the nose tip or chin to x = 0 [1].
3. **Block out with symmetry on** (Sculpt X symmetry, a Mirror modifier with Clipping, Symmetrize): cranium, jaw mass, orbit spacing, topology and UVs. Keep the topology symmetric permanently even when the shape is not. Topology Mirror, Mirror Shape Key (Topology), .L/.R vertex groups and FACS left/right splits all rely on it. 🧠
4. **Turn symmetry off at the first secondary-form pass,** or as soon as any Table B feature differs by 1 mm or more consistently across two views.
   - Keep Basis as the symmetric shape S and add a key named "Asym" holding S + A.
   - Sculpt mode writes into the active shape key on a plain mesh. This does not work with Dyntopo, and Multires detail levels cannot hold shape keys; verify both for your Blender version. 🧠
   - So sculpt the asymmetry at base resolution, use New Shape from Mix, and add Multires only after that. The earlier draft's idea of keeping the asymmetry "as a Multires level" does not give a layer you can toggle.
5. **Work in perceptual order:**
   1. lids and eye openings (2 mm)
   2. brows and mouth corners (3 mm)
   3. nasal tip, columella and nostrils
   4. chin and jaw deviation, and cants (3–4°)
   5. cheeks and ears

   Snap empties to vertices and read the left/right values in the N-panel. Cant = atan(Δy/Δx).
6. **Sanity-check** by registering the result to its mirror.
   - Adults should show about 0.5–1.5 mm whole-face RMSD (more with age) [6][7], and landmark differences of about 0.5–5 mm [2].
   - An RMSD near 0 means the face has been symmetrised away.
   - Several mm of global RMSD means a pose, lens or L/R-label error, or a real condition the sitter should confirm.
7. **Never mirror detail or texture.** Mirrored pores, wrinkles, moles and photo texture are obvious; a duplicated mole reads as fake. Project-paint each side from its own photos. 🧠
8. **Review.**
   - Compare against camera-matched background images and take your time [9].
   - Flip the render and the photo together (the compositor's Flip node) to refresh your eye.
   - Show the sitter a mirrored render as well. 🧠
   - Scrub the Asym key from 0 to 1 to 1.5 (raise the slider maximum) to see what the asymmetry contributes.
9. **If a side is hidden in every photo,** build it from the blended S, not from a copy of the other half [15]. Mark it low-confidence.

## Algorithmic implications

- **Decomposition** (Klingenberg et al. 2002; Mardia et al. 2000). Reflect with M = diag(−1, 1, 1) and swap the L/R labels (P). Align MPX to X with `face3d/geometry/procrustes.py::umeyama`, which returns a proper rotation. Then S = ½(X + aligned MPX) and A = X − S. Rotating X by half the alignment rotation puts the symmetry plane at x = 0. 🧠
- **Gauge.** Three rigid degrees of freedom are antisymmetric: x-translation, yaw and roll.
  - The symmetry residual `(X_l − M·X_r)/sigma_sym` and the midline residual `x_i/sigma_mid` in `face3d/solve/bundle.py` assume the head frame is the symmetry frame.
  - Re-estimate the frame after each outer iteration and let the cameras absorb the change.
  - Otherwise a 2° frame error reads as about 3 mm of A at lateral landmarks (Table D). 🧠
- **Plane-fit weights:**
  - upper face 1.0 (eye corners, nasion, glabella, orbitale)
  - midface 0.5
  - lower face 0.25
  - ears 0.1

  Use a Huber loss at about 1 mm. 🧠
- **Priors.** σ is per axis on d = X_l − M·X_r, which equals 2A, and mean |d| ≈ 1.6σ. These are design values to calibrate, not published priors. 🧠

| Landmarks | σ_sym per axis (mm) | σ_mid on midline x (mm) |
|---|---|---|
| Eye corners, pupils, lid margins | 0.7–1.0 | — |
| Nasion, glabella | — | 0.75–1.0 |
| Brows | 1.5 (vertical 2.0) | — |
| Alare, subalare, orbitale, zygion | 1.0–1.5 | — |
| Pronasale, columella, subnasale | — | 1.5–2.0 |
| Cheilion; labrale sup./inf. | 1.5–2.0 | 1.5 |
| Pogonion, menton | — | 2.0–3.0 |
| Gonion | 2.5–3.0 | — |
| Ear landmarks | 3.0–4.0 | — |

  The current uniform defaults (`sigma_sym = 2.0`, `sigma_mid = 1.5`) are acceptable fallbacks; replace them with per-landmark arrays. Use a Student-t loss (ν ≈ 4) or a Huber loss so that real large asymmetries survive: old fracture, palsy, hemifacial microsomia, tooth loss. Calibrate by sampling until |d| is mostly 0.5–4.5 mm [2] and the warped-surface RMSD is about 0.8 mm [6][7].
- **`symmetry_mode`:**
  - `assist` (σ_sym × 0.25) for the initial pose and coarse fit;
  - `prior` (table values) for refinement;
  - `enforce` only as a user block-out option, never for output.
- **Pose–asymmetry confound.** In a single view, yaw/roll trades off against A.
  - Accept A for a pair only when two or more views at least ~30° apart observe it. Otherwise shrink σ_A by 4× and mark it low-confidence.
  - Take the posterior σ of d from (JᵀJ)⁻¹ in the LM solve, and display asymmetry only where |d| > 2σ_post. 🧠
- **Detector noise.** A portrait face spans about 140 mm across 600–1000 px, so 1 px is about 0.15–0.25 mm. A 3–5 px landmark error is therefore 0.5–1.2 mm per view, the same size as real asymmetry. Average across views. Detectors trained with flip augmentation may be biased toward symmetric placements (hypothesis). 🧠
- **Mirrored-input test.**
  - Refit each view with u → W − u and the labels swapped.
  - If that consistently lowers the reprojection error and makes A agree with the other views, flag the photo as probably mirrored and ask the user.
  - The test is weak when |A| is small. 🧠
- **Template warping** (`face3d/geometry/rbf.py`). base = warp(template, S) and Asym = warp(template, S + A) − base; export Asym as a Blender shape key. Never symmetrise the target landmarks. Ship the template with a vertex mirror map.
- **Report.**
  - Contents: global and per-third RMSD against the mirror; |d| for each pair; the bipupillary, commissural and brow cants; nasal-tip and pogonion deviation in mm and degrees.
  - Flags: eyelid ≥ 2 mm [10]; brow or mouth ≥ 3 mm [9]; cant ≥ 3° [12]; global RMSD above 1.5 mm or below 0.3 mm. 🧠
  - Flags ask the user to confirm and never auto-correct.
- **Evaluation.** Score S and A separately, plus an asymmetry-recovery score: the cosine between A_est and A_true, and the ratio |A_est|/|A_true|. A symmetrised fit can have a low total error and no likeness. 🧠 In `face3d/synthetic.py`, `random_subject` currently adds isotropic `asym_sd = 1.0`, including on midline x. Scale it by region, and add a test that a symmetric face at 3° yaw returns |A| ≈ 0.

## Disagreements, myths & open questions

- **Metrics disagree.** ↔️ Child midline offsets are 0.25 mm [1], landmark differences 0.6–4.6 mm [2], surface RMSD 0.8 mm [6][7] and 2D skeletal differences 0–12 mm [3]. Never mix these metrics.
- **Thresholds disagree.** ↔️ The figures span 2–4 mm and 3–6°. The claim that asymmetry under 3 mm is undetectable [4] conflicts with the 2 mm thresholds for eyelids [10] and for specialist observers [11].
- **Directional asymmetry is unresolved.** ↔️ Studies variously find the right side larger, the left side larger, or neither, and some patient samples report the chin deviating mostly to one side. 🧠 The Raine-study claim (midline deviating right in almost all young adults, and more than half of faces with over 2 mm of asymmetry by area) remains unsourced.
- **Myth: "symmetric = attractive = better likeness."** The attractiveness evidence is itself contested, and none of it measures likeness.
- **Myth: "a mirrored half-face shows the symmetric version."** It is a chimera with distorted widths. Blend the face with its mirror instead [15].
- **Myth: "asymmetry in a photo is anatomy."** Pose, lens, lighting, expression and mirrored files all create it (Table D).
- **Who notices.** Unfamiliar viewers often miss a mirror-flipped face, because recognition generalises across mirror views (Troje & Bülthoff 1998). The sitter and their friends notice (Mita 1977), so they are the strict likeness test. 🧠
- **3DMM regressors probably under-reconstruct asymmetry.** They use few components and regularise toward a near-symmetric mean. This is untested here. 🧠
- **Open questions:**
  - Is there direct evidence that symmetrising a 3D head lowers likeness or identity ratings?
  - What are adult dense-surface norms by region, sex and ancestry?
  - What is the age slope in [7]?
  - What displacement of a feature in a familiar face is just noticeable? Haig 1984 suggests high sensitivity (moderate confidence in that reference).
  - What angle definition is behind the 6° in [11]?
  - Re-check against the full texts: the attribution of [6], the 3–4 mm / 3–4° figures in [12], and the 0.25 mm in [1].
- **Unsourced and kept out of the priors:**
  - asymmetry-index perception thresholds of about 1.1 and 3.1 (2024);
  - "directional asymmetry does not affect judgements, fluctuating asymmetry does";
  - "attractiveness correlates only weakly with 3D asymmetry indices".

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
- Farkas, *Anthropometry of the Head and Face*, 2nd ed., 1994
- Taylor et al. 2014, "Quantitative facial asymmetry: using three-dimensional photogrammetry to measure baseline facial surface symmetry", J Craniofac Surg (probable origin of 0.80 ± 0.24 mm)
- Severt & Proffit 1997, "The prevalence of facial asymmetry in the dentofacial deformities population at the University of North Carolina"
- Ferrario, Sforza, Poggio & Tartaglia 1994, "Distance from symmetry: a three-dimensional evaluation of facial asymmetry", J Oral Maxillofac Surg
- Padwa, Kaiser & Kaban 1997, "Occlusal cant in the frontal plane as a reflection of facial asymmetry", J Oral Maxillofac Surg
- Van Valen 1962, "A study of fluctuating asymmetry"; Palmer & Strobeck 1986, "Fluctuating asymmetry: measurement, analysis, patterns"
- Klingenberg, Barluenga & Meyer 2002, "Shape analysis of symmetric structures"; Mardia, Bookstein & Moreton 2000, "Statistical assessment of bilateral symmetry of shapes"
- Mita, Dermer & Knight 1977, "Reversed facial images and the mere-exposure hypothesis"
- Gilbert & Bakan 1973, "Visual asymmetry in perception of faces"
- Sackeim, Gur & Saucy 1978, "Emotions are expressed more intensely on the left side of the face"
- Rhodes, Brennan & Carey 1987 (caricature identification); Valentine 1991 (face-space and distinctiveness)
- Troje & Bülthoff 1998, "How is bilateral symmetry of human faces used for recognition of novel views?"
- Swaddle & Cuthill 1995, "Asymmetry and human facial attractiveness: symmetry may not always be beautiful"; Perrett et al. 1999, "Symmetry and human facial attractiveness"
- Haig 1984, "The effect of feature displacement on face recognition"
- Umeyama 1991, "Least-squares estimation of transformation parameters between two point patterns"

## Verification log (2026-11-20)

- Whole-face RMSD 0.80 ± 0.24 mm (3dMD; Taylor et al. 2014) and 0.8 ± 0.2 mm (191 subjects): unconfirmed. Searches confirmed only the Taylor 2014 citation (J Craniofac Surg 25:124-128) and that PMC4614853 covers 55 adults (28 symmetric, 27 asymmetric), not a 0.80 mm healthy-volunteer figure. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4614853/ ; https://pmc.ncbi.nlm.nih.gov/articles/PMC11593128/
- Landmark R–L differences 0.6–4.6 mm in 48 normal-occlusion adults (CBCT): unconfirmed for the numbers. The PubMed abstract confirms 48 adults, 9 bilateral pairs, and larger differences at lower and lateral landmarks, but the range was not visible. https://pubmed.ncbi.nlm.nih.gov/23112933/
- Eyelid 2 mm and 3–4 mm / 3–4° thresholds: unconfirmed. PMC11595402 is a 50-subject Caucasian surface-rating study with tentative thresholds, and no figures were visible. Related chin-asymmetry studies give 3° (orthodontists) and 4° (dentists, laypersons), which are different studies. https://pmc.ncbi.nlm.nih.gov/articles/PMC11595402/ ; https://pmc.ncbi.nlm.nih.gov/articles/PMC12237000/
- Table B working ranges (chin, nasal tip, brow, ear, gonion): unconfirmed; no usable evidence found.

## Verification log, pass 2 (2026-11-20)

- Severt & Proffit 1997 (chin about 74-75%, midface about 36%, upper face about 5%): unconfirmed. The abstract-level results give only 495 of 1,460 UNC Dentofacial Clinic patients (34%) with clinically apparent asymmetry, and chin deviation described as the most remarkable feature; the regional percentages were not visible. Badge stays 🧠. https://pesquisa.bvsalud.org/bolivia/resource/pt/mdl-9511487 ; https://pubmed.ncbi.nlm.nih.gov/8010527/
- Blender sculpt/shape-key behaviour (sculpt writes to the active non-Basis key; no shape keys with Dyntopo; Multires levels cannot hold shape keys; symmetry about local origin and axes): unconfirmed. The manual pages found only say that vertex-moving sculpt/edit tools abort when the active shape key is locked, and that Mirror Shape Key needs a perfectly symmetric mesh; nothing on Dyntopo, Multires or Mirror modifier origin. Badge stays 🧠; keep the "verify for your Blender version" caveat. https://docs.blender.org/manual/en/latest/animation/shape_keys/shape_keys_panel.html ; https://docs.blender.org/manual/en/latest/sculpt_paint/sculpting/editing/sculpt.html
