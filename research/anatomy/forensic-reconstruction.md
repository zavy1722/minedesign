# Forensic facial reconstruction rules (skull to face)

> Forensic facial reconstruction (Stephan prefers "approximation") builds a face on a skull from three ingredients: soft-tissue depth tables at bony landmarks, a build-up of the masticatory and facial muscles, and feature rules that place the eyes, nose, mouth and ears relative to bone. The classic schools are Russian anatomical (Gerasimov), American tissue-depth (Krogman; Gatliff & Snow) and the Manchester combination method (Neave, Wilkinson). Blind tests against CT of living people put good reconstructions at a few millimetres of mean surface error, with the largest errors where likeness lives: nose tip, lips, eyelids and ears. For photo-to-3D work the transfer runs backwards: photos give the skin, so forensic rules become weak priors for hidden parts (eyeballs, teeth, skull, ear canal) and for depths no view constrains, never overrides of photo evidence. No harvest or draft existed for this topic; sourced tissue depths live in `anatomy/skull-osteology.md`.
>
> Evidence status: 0 ✅ / 7 📄 / 53 🧠 / 25 ↔️ — verified 2026-11-20 (passes 1–2) against abstracts only; remaining 🧠 items still queued.

## Key facts

**Methods**
- **Gerasimov (Russian anatomical)** 🧠: Mikhail Gerasimov (1907–1970) modelled muscles from their attachment relief, used few depth markers and read features from bony morphology. His historical portraits (Ivan IV, Timur) are famous but were never blind-tested.
- **American tissue-depth** 🧠: pegs cut to mean depths at ~20–35 landmarks (Rhine & Moore-type tables), joined by clay strips and filled. No muscle layer; fast and reproducible, but bland.
- **Manchester / combination** 🧠: Neave (Manchester, 1970s), then Wilkinson (Manchester → Dundee → Liverpool John Moores Face Lab). Depth pegs plus individually modelled muscles, skin laid to the peg tips, features placed by rule. Since the 2000s it is done in haptic sculpting software (FreeForm; verify current product) with libraries of pre-modelled muscles and features.
- **Computerized / template warping** 🧠: a reference head CT (skull plus face) is warped to the target skull by landmark thin-plate splines or dense registration, carrying the face along; statistical variants add a face PCA with depth constraints (Claes, Vandermeulen et al.). Blender "anatomical deformation" of a donor CT head (Cícero Moraes; OrtogOnBlender add-on) is the open-source analogue ↔️ (status and licence unverified).
- **Craniofacial superimposition** 🧠: overlaying a skull on an antemortem photo by solving camera pose and focal length with soft-tissue offsets at landmarks. It is the forensic task closest to this project's camera solve.

**Eyes and orbit**
- The old guideline (cornea touches a line from mid-supraorbital to mid-infraorbital rim) sets the eye too deep; Stephan (2002) falsified it with exophthalmometry data (the guideline under-predicts globe projection by ~4 mm on average) 📄 [1]. Use a Hertel rule instead: corneal apex ≈16 mm (normal 12–20) ahead of the lateral orbital rim 🧠.
- Hertel values average ≈1.5–2 mm higher in people of African ancestry and are often lower in East Asian samples ↔️. A left–right difference above ~2 mm is clinically abnormal 🧠.
- The globe sits slightly off the aperture centre, nearer the roof and lateral wall in most accounts (Stephan & Davidson 2008; Guyomarc'h et al. 2012); cadaver dissection found the globe 1–2 mm closer to the roof and lateral wall on average, and CT of living people supported superior and lateral placement 📄 [2] (exact CT offsets unverified).
- **Canthi** 🧠: the medial tendon inserts on the anterior lacrimal crest, putting endocanthion ≈4–6 mm lateral to dacryon. The lateral tendon inserts on Whitnall's tubercle, ≈3–5 mm inside the rim and ≈10 mm below the frontozygomatic suture, so exocanthion lies ≈3–5 mm medial to the lateral orbital margin and usually 1–3 mm above endocanthion.
- Adult globe ≈23–25 mm axial (longer in high myopia, which also raises Hertel values) 🧠. Corneal diameter ≈11.8 mm (SD ≈0.6–0.8), matching the sourced value in `blender/eyes-modeling-blender.md` 🧠.
- **Brows** ↔️: a strong supraorbital ridge is said to carry a low, straight brow and a weak ridge a higher, arched one (Gerasimov; Fedosyutkin & Nainys). Qualitative and unvalidated.

**Nose**
- The bony dorsum is the most predictable part: cover at rhinion is only ≈2–3.5 mm, so nasion→rhinion follows the nasal bones within ~1 mm 🧠. Tip, alae and columella are cartilage and weakly predicted 🧠.
- **Gerasimov two-tangent** ↔️: a tangent to the distal third of the nasal bones and a line along the anterior nasal spine (ANS) meet at pronasale. Tests (Stephan, Henneberg & Sampson 2003; Rynn & Wilkinson 2006) found the lines often fail to meet usefully, with errors of several mm.
- **Krogman** ↔️: projection ≈3 × ANS length added to mid-philtrum depth. Sensitive to how ANS is measured (spines are often broken); tested as unreliable.
- **Rynn, Wilkinson & Peters (2010)** 🧠: CT-based regressions from aperture and spine measures, reported to beat the traditional rules; the current best published bone→nose method (formulas and errors still to extract).
- **Alar width** ↔️: aperture width + ≈10 mm (European descent), +≈12–16 mm (East Asian, African descent); equivalently al–al ≈1.4–1.7 × aperture width.
- **Tip direction and deviation** ↔️: ANS angle and septal or aperture asymmetry are said to predict tip rotation and soft-nose deviation; weak effects.

**Mouth**
- **75 % rule** 📄 [3]: inter-canine width (ICW) ≈75 % of mouth width, so ch–ch ≈ ICW / 0.75 (Stephan & Henneberg 2003); the ICW definition used remains unverified 🧠. The ICW definition matters: cusp-tip ICW (≈33–37 mm) would give too narrow a mouth.
- "Corners at the canine–first premolar contact" underestimates mouth width; resting corners usually sit over the first premolar 🧠.
- At rest, stomion lies ≈1–4 mm above the upper incisal edges in young adults (more in women); display falls toward 0 mm by the 60s while lower-incisor display rises (Vig & Brundo pattern) 🧠.
- Lip projection follows incisor position, but soft tissue moves less than teeth (lip/incisor ratios ≈0.4–0.9) ↔️. "Vermilion height = incisor enamel height" is weakly supported ↔️.

**Ears**
- The tragus overlies the front of the external acoustic meatus. Tragion lies ≈8–14 mm lateral of porion and roughly level with it, i.e. near Frankfort height (±5 mm) 🧠.
- Guyomarc'h & Stephan (2012) found traditional ear guidelines (ear length = nose length; axis parallel to ramus or nasal dorsum) poor ↔️. Adult ears run 5–12 mm longer than n–sn (`anatomy/ear.md`) 🧠. Mastoid→lobe rules are folklore 🧠.

**Validated accuracy**
- Stephan & Henneberg (2001): of 16 approximations from dry skulls, one was recognized above chance 🧠.
- Blind tests against CT of living subjects (Wilkinson et al. 2006; Lee, Wilkinson & Hwang 2012; Short et al. 2014): Lee, Wilkinson & Hwang 2012 (cone-beam CT, three reconstructions) found 54 %, 65 % and 77 % of the surface within 2.5 mm [4]; Wilkinson et al. 2006 found the majority of the surface under 2.5 mm, with ears and nose tip the main error areas [5] (corrected in verification: threshold is 2.5 mm, range 54–77 %; Short 2014 and the ±2 mm figure not found) 📄. Smallest errors on forehead, dorsum and chin; largest at nose tip, lips, eyelids, ears and lateral cheeks ↔️.
- Automated CT-template methods report mean surface errors of roughly 2–4 mm ↔️. Surface error is not likeness: recognition hinges on a few mm at eyes, nose and mouth 🧠. Casework "identification-aid" rates (~50–70 % quoted) are uncontrolled ↔️.

## Numbers & reference tables

**Table 1 — Bone→soft rules (adults, neutral expression)**

| Feature | Rule | Error / spread | Population | Status |
|---|---|---|---|---|
| Corneal apex depth | 16 mm (12–20) ahead of lateral orbital rim | SD ≈2 mm | European descent; +1.5–2 African descent | 🧠 ↔️ |
| Rim-tangent rule | cornea touches tangent | under-predicts projection ~4 mm [1] | — | 📄 |
| Endocanthion | 4–6 mm lateral to dacryon | ±1.5 mm | adults | 🧠 |
| Exocanthion | 3–5 mm medial to lateral orbital margin | ±1.5–2 mm | adults | 🧠 |
| Canthal tilt (ex above en) | +2 to +6° | wide | European descent; higher East Asian | 🧠 |
| Nasal dorsum | follows nasal bones, 2–3.5 mm cover at rhinion | ~1 mm | pooled | 🧠 |
| Pronasale (two-tangent / 3 × ANS) | see text | often ≥4–5 mm | mixed | ↔️ |
| Alar width | aperture + 10 (Eur.) / +12–16 mm (EAs., Afr.) | ±3 mm | population-specific | ↔️ |
| Alar ratio | al–al ≈1.4–1.7 × aperture width | ±0.15 | mixed | ↔️ |
| Mouth width | ch–ch ≈ ICW / 0.75 [3] | ±3–5 mm | adults | 📄 |
| Stomion vs upper incisal edge | 1–4 mm above (young) → ≈0 (60s+) | ±1.5 mm | adults | 🧠 |
| Lip vs incisor movement | 0.4–0.9 : 1 | wide | orthodontic samples | ↔️ |
| Tragion vs porion | 8–14 mm lateral; level ±5 mm | ±3–5 mm | adults | 🧠 |
| Ear length − nose height (n–sn) | +5 to +12 mm | ±5 mm | adults; grows with age | 🧠 |

**Table 2 — Eye reference values (adults)**

| Quantity | Value | Status |
|---|---|---|
| Globe axial length | 23–25 mm | 🧠 |
| Corneal diameter (HVID) | ≈11.8 mm, SD 0.6–0.8 | 🧠 |
| Corneal radius of curvature | ≈7.5–8.0 mm | 🧠 |
| Interpupillary distance | 58–70 mm (M ≈64, F ≈62) | 🧠 |
| en–en / ex–ex | 28–35 / 85–95 mm | 🧠 |
| Palpebral fissure ex–en | 27–32 mm | 🧠 |

**Table 3 — Accuracy benchmarks (bone→face)**

| Study / method | Metric | Reported | Status |
|---|---|---|---|
| Stephan & Henneberg 2001 | face-pool recognition | 1 of 16 above chance | 🧠 |
| Manchester digital vs CT (2006–2014) | surface within 2.5 mm | 54–77 % (Lee 2012) [4][5] (corrected in verification) | 📄 |
| CT-template / statistical | mean surface error | ~2–4 mm | ↔️ |
| Casework identification aid | % of cases | ~50–70 % (uncontrolled) | ↔️ |

## Applying this to photo→3D face sculpting in Blender

1. **Invert the logic** 🧠. Rules run bone→skin with σ of 2–5 mm; a calibrated multi-view set observes skin at ~1–2 mm. Photos win wherever a view sees the feature. Rules fill blind directions only: corneal depth and tip projection in frontal-only sets, ear position, lip projection relative to teeth.
2. **Hidden-anatomy rig** 🧠: eyeballs (≈24 mm sphere plus cornea of radius ≈7.8 mm), a dental arch and a template skull, parented to the head and driven by the fit. Place eyes by the Hertel rule, never the rim tangent. In profile, the lateral canthus must sit well behind the cornea, near the globe's equator.
3. **Scale** 🧠: corneal diameter is a weak scale prior (±5–7 %). Never measure it through spectacles or on a squinting or smiling subject.
4. **Canthi → orbit** 🧠: from fitted en/ex, place dacryon ≈5 mm medial and the lateral orbital margin ≈4 mm lateral per side, fit the skull orbit, check orbit width ≈40 mm.
5. **Nose** 🧠: dorsum, tip and alae come from the photos. Use aperture ≈ al–al − 10…16 mm (by ancestry) only to place the skull. Without a profile, constrain tip projection with the face-model prior and a Goode-ratio check, not ANS rules: ANS is hidden too.
6. **Teeth** 🧠: size the arch so ICW ≈0.75 × ch–ch (cross-check cusp-tip ICW 33–37 mm). Set incisal edges 1–4 mm below a neutral stomion (less with age) unless teeth are visible.
7. **Ears** 🧠: after the skull fit, put tragion ≈11 mm lateral of porion at Frankfort height; take ear length from the photo, not the nose.
8. **Manchester QA pegs** 🧠: Empties at ~25–35 skull landmarks along the bone normal, length = depth prior (`data/skull-osteology.json`). Raycast in Geometry Nodes, colour skin by z-score, and investigate beyond 2σ rather than auto-fixing: BMI, age and ancestry shift depths.
9. **What goes wrong** 🧠: forensic means used as targets (the face drifts to average); supine-CT depths applied to upright photos (cheek tissue falls back when lying down); neutral rules applied to smiling photos; camera distance under ~1 m enlarging the nose against the ears; ignoring age (tip droop, thinner lips, less incisor show, longer ears); European-derived rules applied to other ancestries.

## Algorithmic implications

- **Factor graph** 🧠: bone landmarks, soft landmarks, eyes and teeth are variables; rules are Gaussian or Huber factors with weight 1/σ²; photo reprojection residuals are separate factors. With honest σ the observed terms dominate without manual switching.
- **Superimposition-style interval constraints** 🧠: for paired landmarks require (s − b)·n̂ within the log-normal depth prior from `skull-osteology.json`, with tangential slack τ ≈2–4 mm because soft and bony points slide (gnathion, menton, gonion).
- **Suggested rule priors** (Frankfort-aligned frame, mm) 🧠:

| Parameter | μ | σ | Note |
|---|---|---|---|
| `cornea_ahead_lat_rim` | 16 | 2.0 | +1.75 Afr., −1.5 EAs. ↔️; clamp 11–22 |
| `hertel_lr_diff` | 0 | 1.0 | warn > 2 |
| `globe_offset_sup`, `_lat` | +1, +1 | 1.5 | superolateral sign confirmed [2]; size ≈1–2 mm |
| `globe_axial_len` | 23.8 | 1.0 | L–R σ 0.3 |
| `corneal_diam` | 11.8 | 0.7 | low-weight scale prior |
| `en_lat_of_dacryon` | 5 | 1.5 | per side |
| `ex_med_of_ectoconchion` | 4 | 1.5 | per side |
| `ex_below_fz_suture` | 10 | 3 | Whitnall's tubercle |
| `alar_minus_aperture` | 10 / 13 / 16 | 3 | Eur. / EAs. / Afr. ↔️ |
| `tip_projection_from_bone` | — | ≥5 | only without a profile view |
| `icw_over_mouth_width` | 0.75 | 0.05 | ICW definition unverified |
| `stomion_above_U1_edge` | 2.5 / 1.5 / 0.5 | 1.5 | age <30 / 30–50 / >50 |
| `tragion_lat_of_porion` | 11 | 3 | vertical 0 ± 5 |

- **Conditioning** 🧠: expose `sex`, `age`, `bmi` and a soft `ancestry` mixture; default to pooled values and ask the user rather than infer ancestry from the photo.
- **No double counting** 🧠: if skin already carries a PCA/3DMM prior, apply forensic rules only between hidden layers and skin.
- **Evaluation** 🧠: report per-region error (forehead, orbit, nose, lips, chin, cheeks, ears) plus en/ex/prn/ch landmark error, as the forensic literature does, not one RMS.

## Disagreements, myths & open questions

- **Pooled vs population tables** ↔️: Stephan argues pooled "T-table" depths lose little; Wilkinson and others build ancestry- and BMI-specific tables. Support both.
- **Muscle modelling** ↔️: Manchester holds that muscle build-up improves shape; critics say muscle bulk cannot be read from bone.
- **Nose prediction** ↔️: two-tangent, 3 × ANS, "aperture mirrors the nasal profile" and regressions disagree, and none predicts tip shape well.
- **Myths** 🧠: "the skull determines the face" (fat, cartilage, lids, lips and ears are loosely constrained); "the cornea touches the rim tangent"; "ear length = nose length"; "mouth corners under the pupils" (resting ch–ch/IPD ≈0.8–0.9); "Gerasimov's portraits prove the method".
- **Open** 🧠: dense upright depth maps with SDs; validated soft→bone inverse models; whether the forensic per-region error ranking holds for photo fitting; child-specific canthal and incisor rules (`anatomy/child-growth.md`).

## Sources

Numbered sources (added in verification, 2026-11-20; abstracts only, full texts not read):
1. Stephan CN 2002, globe projection guideline falsified — https://ojp.gov/ncjrs/virtual-library/abstracts/facial-approximation-globe-projection-guideline-falsified ; https://digital.library.adelaide.edu.au/items/f51c9e26-39d1-4c17-ad30-bc52cfdcf781
2. Stephan & Davidson 2008, eyeball and canthi placement (J Forensic Sci 53:612–619) — https://www.pubmed.gov/18471206/ ; https://ojp.gov/ncjrs/virtual-library/abstracts/placement-human-eyeball-and-canthi-craniofacial-identification ; Guyomarc'h 2012 CT follow-up via NCJRS abstract https://www.ncjrs.gov/App/Publications/abstract.aspx?ID=248542
3. Stephan & Henneberg 2003, 75 % rule (J Forensic Sci 48:725–727) — https://digital.library.adelaide.edu.au/dspace/handle/2440/5388 ; https://www.ojp.gov/ncjrs/virtual-library/abstracts/predicting-mouth-width-inter-canine-width-75-percent-rule

4. Lee WJ, Wilkinson CM & Hwang HS 2012, accuracy assessment of forensic computerized facial reconstruction employing cone-beam CT — https://ojp.gov/ncjrs/virtual-library/abstracts/accuracy-assessment-forensic-computerized-facial-reconstruction
5. Wilkinson C, Rynn C et al. 2006, blind accuracy assessment of computer-modeled forensic facial reconstruction using CT data from live subjects — https://researchonline.ljmu.ac.uk/id/eprint/5337/ ; https://link.springer.com/article/10.1007%2Fs12024-006-0007-9

Otherwise no URLs are cited. Linked material on tissue depth, aperture–nose relations and Manchester accuracy: `anatomy/skull-osteology.md` (its [1], [16], [17], [39], [42], [43], [46]–[48], [51]); corneal scale: `blender/eyes-modeling-blender.md`; ear canons: `anatomy/ear.md`; mouth norms: `anatomy/mouth-lips-teeth.md`.

**Further reading (by name, not yet linked)**
- Gerasimov MM, *The Face Finder*, 1971 (Russian original 1955).
- Krogman WM & İşcan MY, *The Human Skeleton in Forensic Medicine*, 2nd ed., 1986.
- Wilkinson C, *Forensic Facial Reconstruction*, Cambridge UP, 2004.
- Taylor KT, *Forensic Art and Illustration*, 2001; Clement JG & Marks MK (eds), *Computer-Graphic Facial Reconstruction*, 2005; İşcan MY & Helmer RP (eds), *Forensic Analysis of the Skull*, 1993.
- Snow CC, Gatliff BP & McWilliams KR, Am J Phys Anthropol, 1970.
- Stephan CN & Henneberg M, "Building faces from dry skulls: are they recognized above chance rates?", J Forensic Sci, 2001.
- Stephan CN, "Facial approximation: globe projection guideline falsified by exophthalmometry literature", J Forensic Sci, 2002.
- Stephan CN, Henneberg M & Sampson W, nose projection and pronasale prediction, Am J Phys Anthropol, 2003.
- Stephan CN & Henneberg M, "Predicting mouth width from inter-canine width — a 75% rule", J Forensic Sci, 2003.
- Stephan CN & Davidson PL, "The placement of the human eyeball and canthi in craniofacial identification", J Forensic Sci, 2008.
- Wilkinson CM & Mautner SA, eyeball protrusion in facial reconstruction, J Forensic Sci, 2003.
- Rynn C & Wilkinson CM, Am J Phys Anthropol, 2006; Rynn C, Wilkinson CM & Peters HL, "Prediction of nasal morphology from the skull", Forensic Sci Med Pathol, 2010.
- Prokopec M & Ubelaker DH, nose shape from the skull, Forensic Sci Commun, 2002; George RM, lateral craniographic method, J Forensic Sci, 1987.
- Guyomarc'h P & Stephan CN, "The validity of ear prediction guidelines used in facial approximation", J Forensic Sci, 2012; Guyomarc'h P et al., eyeball placement from CT, J Forensic Sci, 2012.
- Wilkinson C, Rynn C, Peters H et al., Forensic Sci Med Pathol, 2006; Lee WJ, Wilkinson CM & Hwang HS, J Forensic Sci, 2012; Short LJ et al., Forensic Sci Int, 2014.
- Claes P, Vandermeulen D, De Greef S et al., "Computerized craniofacial reconstruction: conceptual framework and review", Forensic Sci Int, 2010.
- Damas S, Cordón O, Ibáñez O et al., craniofacial superimposition survey, ACM Computing Surveys, 2011.
- Vig RG & Brundo GC, "The kinetics of anterior tooth display", J Prosthet Dent, 1978; Migliori ME & Gladstone GJ, Am J Ophthalmol, 1984.
- Moraes C et al., Blender forensic approximation and OrtogOnBlender (to verify); Schlager S, *Morpho* R package.

## Verification log (2026-11-20)

- Claim 1, Hertel prior (cornea 16 mm ahead of lateral rim, +1.5–2 mm African ancestry): PARTLY CONFIRMED. Stephan 2002 falsification of the rim-tangent rule confirmed (under-predicts projection ~4 mm) — https://ojp.gov/ncjrs/virtual-library/abstracts/facial-approximation-globe-projection-guideline-falsified . The 16 mm / 12–20 / ancestry values were not found in results: left 🧠 / ↔️.
- Claim 2, 75 % rule: CONFIRMED (existence and ratio; ICW definition unconfirmed) — https://digital.library.adelaide.edu.au/dspace/handle/2440/5388
- Claim 3, canthi and globe offset: globe 1–2 mm toward roof and lateral wall CONFIRMED (Stephan & Davidson 2008; CT support by Guyomarc'h 2012) — https://www.pubmed.gov/18471206/ . Canthi distances (4–6 mm, 3–5 mm, 10 mm): UNCONFIRMED, left 🧠.
- Claim 4, alar width = aperture + 10 / +12–16 mm, ratio 1.4–1.7: UNCONFIRMED (Hoffman 1991 addition formula exists but its constant was not shown) — https://www.ojp.gov/ncjrs/virtual-library/abstracts/relationship-between-piriform-aperture-and-interalar-nasal-widths

## Verification log, pass 2 (2026-11-20)

- Claim 1, Manchester blind-test accuracy (50–70 % within ±2–2.5 mm; CT-template 2–4 mm): CORRECTED for the Manchester part. Lee et al. 2012: 54/65/77 % within 2.5 mm — https://ojp.gov/ncjrs/virtual-library/abstracts/accuracy-assessment-forensic-computerized-facial-reconstruction ; Wilkinson et al. 2006: majority under 2.5 mm — https://researchonline.ljmu.ac.uk/id/eprint/5337/ . Short 2014 and any ±2 mm figure not found; CT-template 2–4 mm UNCONFIRMED (left ↔️).
- Claim 2, OrtogOnBlender / Moraes Blender method (status, licence, version): UNCONFIRMED. Search found only a Blender tracker note that OrtogOnBlender is not maintained by the Blender project (https://developer.blender.org/T61207) and a pointer to https://github.com/cogitas3d/OrtogOnBlender/issues; no licence or version evidence. Left ↔️/unverified.
