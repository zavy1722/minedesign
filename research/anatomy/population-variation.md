# Craniofacial variation across human populations

> Human faces vary continuously, and mostly within populations. For genetic markers and for whole-skull shape, roughly 85–95% of variance lies among individuals of the same population and roughly 5–15% between continental regions 🧠. A few facial features break that pattern, with group means several within-group SDs apart: nose width, nasal-root height, midface projection ("facial flatness"), lip fullness and protrusion, the epicanthal fold and lid crease, and head shape 🧠. Most of these are depth and projection features, which a frontal photo constrains least. A photo→3D fit that leans on a 3D morphable model (3DMM) prior trained mostly on European-ancestry scans therefore pulls other faces toward European proportions 🧠. Ethnic templates are not the fix, because they replace the individual with a stereotype. The fix is to measure first, use balanced and widened priors, treat folds and creases as discrete states, take profile views, and audit errors per group 🧠.
>
> Evidence status: 0 ✅ / 0 📄 / 84 🧠 / 27 ↔️ — 🧠 items are queued for web verification.

EUR, EAS and AFR-W label European-ancestry, East Asian, and West African or African-American samples. They name samples, not types.

## Key facts

**How variation is partitioned**
- **Genetic markers.**
  - Lewontin (1972): about 85% of variation lies within populations, about 8% among populations within a continental group, and about 6% among continental groups 🧠.
  - Rosenberg et al. (2002), 377 microsatellites: 93–95% within populations, 3–5% among major regions 🧠.
- **Skulls.** About 11–14% of global craniometric variation lies among regions (Relethford 2002, on Howells' data). For skin colour the figure is about 88% 🧠. Most cranial shape fits neutral drift and isolation by distance, and diversity falls with distance from Africa (Manica et al. 2007) 🧠.
- **Different regions carry different signals.** The basicranium tracks population history, the face (especially the nose) tracks climate, and the mandible tracks diet (Harvati & Weaver 2006; von Cramon-Taubadel 2011) 🧠.
- **Weak per-trait separation still adds up.** Correlated traits combine into accurate multivariate classification (Edwards 2003), so face recognisers and 3DMM latent spaces encode ancestry whether or not anyone asks them to 🧠.
- **Variation is clinal**, and continental averages hide large spreads. Africa holds the most genetic and cranial diversity: East African faces and noses are narrower on average than West African ones (Hiernaux 1974). A single "African" template is therefore the least valid of all 🧠.
- **Labels are social proxies.** Self-identified African Americans average roughly three-quarters West African ancestry, with a wide individual range (Bryc et al. 2015) 🧠.

**Traits with the largest between-group differences** (Table 2; the direction is reliable, the size is rough)
- **Nose.** Alar width and nasal index (al–al / n–sn × 100) are narrower in cold, dry climates (Thomson & Buxton 1923). Zaidi et al. (2017) found that nostril and alar-base width differ more than drift alone predicts 🧠. Tip protrusion, columella length, nostril shape and radix height co-vary but are separable. A GWAS found separate loci for bridge breadth, nostril breadth and tip shape (Adhikari et al. 2016) 🧠.
- **"Facial flatness"** in East Asian and Arctic samples is mainly a low nasal root plus forward-placed zygomas, which give a wide nasomalar angle. The face is not flat overall (Hanihara 2000) 🧠. African samples have low nasal bones and more alveolar prognathism. EUR samples have the highest radix and the most receding malars 🧠.
- **Eyelids.**
  - In many East Asian upper lids the orbital septum fuses to the levator below the tarsus, so fat sits low and the crease is low or absent (Jeong et al. 1999) 🧠.
  - Epicanthal folds are common in East and Central Asian, Arctic, some Indigenous American and Khoisan populations, rare in European adults, and common in infants of every ancestry 🧠.
  - The fold hides the caruncle. The visible en–en therefore looks larger and the visible fissure shorter, while bony intercanthal width and interpupillary distance differ little 🧠 ↔️.
- **Globe position.** Hertel exophthalmometry averages about 1.5–2 mm higher in African-ancestry samples and lower in East Asian samples (Migliori & Gladstone 1984) 🧠 ↔️.
- **Lips and profile.** AFR-W samples have fuller vermilion and lips further ahead of the Ricketts E-line, and EAS samples are intermediate. Bimaxillary protrusion is more common outside EUR samples. The nasolabial angle is more acute where the lips protrude and the tip projects less 🧠.
- **Head shape.** The cephalic index (eu–eu / g–op × 100) runs from about 72 to 85 or more across populations. It is partly plastic: infant sleeping position flattens the occiput 🧠.

**Most variation is within groups**
- For face height, eye-fissure length, mouth width, interpupillary distance and ear length, group means lie within about 1 within-group SD of each other 🧠.
- Even nose-width distributions overlap widely. Ofodile described several distinct nose forms within self-identified Black Americans 🧠.
- The forensic "macromorphoscopic" traits (Hefner 2009) overlap across groups. None is exclusive to one group, and the "typical" state is often absent in most members 🧠.
- Sex, age, BMI and dentition usually change the face as much as ancestry does, often more 🧠.

**Bias in priors and tools**
- **Training data.** The main 3DMMs (BFM, FLAME, LSFM, LYHM) were built largely from European-ancestry scans (Table 4). FaceScape (Chinese) is the main counterweight 🧠.
- **Regression to the training mean.** With one frontal image and strong regularisation, a unimodal Gaussian prior returns the training mean wherever the photo is uninformative. The result is a narrower alar base, higher radix, more projected tip, thinner vermilion and longer head 🧠.
- **Albedo.** Albedo models trained on light skin explain dark skin as shadow (Feng et al. 2022, TRUST and the FAIR benchmark) 🧠.
- **Recognition.** NIST IR 8280 found false-match rates 10–100× higher for some demographic groups in many algorithms 🧠.
- **Landmarks** degrade at low-contrast alar creases and vermilion borders on dark skin in dim light, at folds over en, and on absent lid creases 🧠.
- **Character-creator sliders.** MakeHuman/MPFB-style ancestry sliders bundle dozens of independent traits into one stereotype axis 🧠.

## Numbers & reference tables

**Table 1: Share of variance within and between groups.**

| Data | Within populations | Among regions | Reference | Status |
|---|---|---|---|---|
| Classical genetic markers | ~85% | ~6% (+~8% among populations within region) | Lewontin 1972 | 🧠 |
| 377 microsatellites (HGDP) | 93–95% | 3–5% | Rosenberg 2002 | 🧠 |
| Craniometrics | ~86–89% | ~11–14% | Relethford 2002 | 🧠 |
| Skin reflectance | ~12% | ~88% | Relethford 2002 | 🧠 |
| One trait, two equal groups whose means are d within-SDs apart | 1 − share | share = d²/(d²+4): d = 1 → 20%, 2 → 50%, 3 → 69%, 4 → 80% | derived | 🧠 |

**Table 2: Trait tendencies, adults** (sexes pooled unless stated). "Extreme d" is the separation of the most distant group means, in within-group SDs. Values are recalled ranges: use them for widening priors and for sanity gates, never as targets.

| Trait | Units | EUR | EAS | AFR-W | Within SD | Extreme d | Status |
|---|---|---|---|---|---|---|---|
| al–al, male | mm | 33–36 | 37–41 | 40–46 | 2–2.5 | 3–4 | 🧠 ↔️ |
| al–al, female | mm | 30–32 | 34–38 | 36–42 | ~2 | 3–4 | 🧠 ↔️ |
| Nasal index (living) | index | 60–70 | 72–85 | 85–105 | 6–9 | 3–4 | 🧠 ↔️ |
| Tip protrusion sn–prn, male | mm | 18–22 | 15–19 | 15–19 | ~2 | 1–2 | 🧠 ↔️ |
| Radix projection, relative to EUR | mm | 0 | −3 to −6 | −3 to −6 | 2–3 | 1.5–2.5 | ↔️ |
| Nasolabial angle | ° | 95–115 | 85–105 | 75–95 | 10–12 | 1.5–2 | ↔️ |
| Visible en–en | mm | 31–34 | 35–41 | 33–37 | 2.3–2.7 | 2–3 | 🧠 ↔️ |
| Interpupillary distance | mm | 60–66 | 60–66 | 61–67 | 3–3.5 | < 0.5 | 🧠 |
| Visible ex–en | mm | 29–32 | 27–31 | 29–32 | 1–1.5 | ~1 | 🧠 |
| Lid-crease height, if present | mm above lashes | 8–11 | 4–7 (absent in ~40–60% of people) | not recalled | ~1.5 | bimodal | ↔️ |
| Epicanthal fold, adults | % | < 5 | ~40–90, by definition used | low | — | discrete | ↔️ |
| Hertel exophthalmometry | mm | 14–18 | 12–16 | 16–21 | ~2 | ~1.5 | 🧠 ↔️ |
| Upper vermilion ls–sto | mm | 7.5–10 | 8–11 | 10–14 | ~1.5 | ~2 | 🧠 ↔️ |
| Lower vermilion sto–li | mm | 9–11 | 9.5–12 | 11–15 | ~1.5 | ~2 | 🧠 ↔️ |
| Lower lip to E-line (+ = ahead) | mm | −2 ± 2 | 0 to +2 | +2 to +6 | 2–2.5 | ~2 | ↔️ |
| Soft-tissue convexity (180° − G′–Sn–Pg′) | ° | 8–16 | 10–16 | 12–20 | ~4 | ~1 | ↔️ |
| zy–zy, male | mm | 135–140 | 139–147 | 135–145 | 4–6 | 1–1.5 | 🧠 |
| Nasomalar angle fmo–n–fmo (skull) | ° | 135–140 | 143–150 | 138–144 | ~4 | ~2 | ↔️ |
| Cephalic index | index | 76–84 | 80–88 | 72–78 | 3–4 | 2–4 | 🧠 ↔️ |

**Table 3: Martin–Saller index bands (living subjects)** 🧠

| Index | Bands |
|---|---|
| Nasal | hyperleptorrhine < 55; leptorrhine 55–69.9; mesorrhine 70–84.9; platyrrhine 85–99.9; hyperplatyrrhine ≥ 100 |
| Cephalic | dolichocephalic < 76; mesocephalic 76–80.9; brachycephalic 81–85.4; hyperbrachycephalic ≥ 85.5 |

**Table 4: Who is in common 3D face data** (time-sensitive).

| Model / dataset | Subjects | Population | Status |
|---|---|---|---|
| BFM 2009/2017 | 200, ages ~8–62 | mostly European (Basel) | 🧠 |
| FLAME identity space (2017) | ~3,800 CAESAR scans | North America, Netherlands, Italy | 🧠 |
| LSFM (2016/18) | ~9,700, London | large White majority; per-group sub-models | 🧠 ↔️ |
| LYHM / Headspace (2017) | ~1,200 of ~1,500 | UK, mostly White | 🧠 |
| FaceScape (2020) | ~900+ | Chinese | 🧠 |
| FaceWarehouse (2014) | 150, ages 7–80 | captured in China | 🧠 |
| BU-3DFE (2006) | 100 | deliberately mixed (6 groups) | 🧠 |
| MICA training union (2022) | ~2,300 from ~8 sets | mostly European and East Asian | 🧠 |
| 3DFN (FaceBase) | 2,454 | European-ancestry US | 🧠 |

**Table 5: Prior widening when the population is unknown** (k = σ_pooled / σ_within) 🧠

| Trait | k | Form |
|---|---|---|
| al–al, nasal index, alar base | 2.0–2.5 | log-normal |
| Radix projection, nasomalar depth | 1.8–2.2 | normal |
| Visible en–en | 1.8 | normal, plus fold offset |
| Vermilion heights; lip protrusion to Sn–Pg′ | 1.6–1.8 | log-normal / normal |
| Cephalic index, head length | 1.6–2.0 | normal |
| Nasolabial angle, tip protrusion | 1.3–1.5 | normal |
| zy–zy, ch–ch | 1.2–1.3 | log-normal |
| n–gn, ex–en, interpupillary distance, ear length | 1.0–1.15 | log-normal |
| Lid crease, epicanthal fold | — | categorical latent |

## Applying this to photo→3D face sculpting in Blender

1. **Capture for depth.** Between-group differences sit mostly in projection, so a fit from frontal photos plus a prior drifts toward the training population. Collect a true profile (both sides if possible), a ¾ view, a basal ("worm's-eye") nose view and a top-of-head view. Shoot from 1.5 m or more with an 85–135 mm-equivalent lens. A 40 cm selfie widens the nose and lips by about 8–10%, which can mimic a population difference 🧠.
2. **Measure, with consent.**
   - Caliper al–al, ch–ch and visible en–en; note whether there is an epicanthal fold and its type.
   - Head length and breadth.
   - Lid-crease height in downgaze, or "none".

   Store these as custom properties. Store no ancestry label 🧠.
3. **Use a neutral base.** Start from a pooled or neutral mean head. If you use an MPFB-type base, leave the ancestry sliders at the neutral mix and sculpt the measured deviations: each slider moves the nose, lips, lids, malars and skull together, along an axis no real person follows 🧠.
4. **Nose.**
   - Basal view: alar base (ac–ac) against maximum flare (al–al), nostril axis and shape, columella-to-lobule ratio.
   - Profile: radix height, judged by where sellion sits relative to the lash line and the corneal apex.
   - Typical errors: a high European radix on a low-radix face; a nose widened without shortening the columella and tip 🧠.
5. **Eyes.**
   - Sculpt the epicanthal fold as a skin web over the medial canthus, matching its type (palpebral, tarsal or inversus). Keep the true medial canthus and the eyeball in place.
   - Monolid: keep the upper lid continuous from brow to lashes, partly hiding the lash root, with less pretarsal show.
   - Set canthal tilt from the measured ex–en angle, not from a group expectation 🧠.
6. **Midface.** A "flat" midface comes from a lower radix with the malars brought forward. Pushing the cheeks back makes the face look gaunt 🧠.
7. **Lips and profile.**
   - Judge protrusion against the Sn–Pg′ line. The E-line moves with nose and chin.
   - Model vermilion eversion, not only vermilion height.
   - On darker skin the vermilion border may be a pigment boundary rather than a white-roll ridge.
   - Check prognathism at the subnasal and incisor level 🧠.
8. **Head shape.** Measure the cephalic index from the top photo. A flattened occiput from back-sleeping is common in every ancestry 🧠.
9. **Look-dev.** Use a grey card or colour checker, with cross-polarised capture if possible. Expose for the skin, and do not let an albedo prior "correct" skin tone. On dark skin, specular sheen carries much of the form, so check the sculpt under a rim light as well 🧠.
10. **What goes wrong:**
    - reading the fold edge as en;
    - treating a missing crease as a detection failure;
    - fitting from frontal views only, which inherits European depth;
    - using "ethnic" presets;
    - computing z-scores against a single global norm set;
    - averaging toward a group mean, which erases the person;
    - exaggerating group-typical traits beyond what you measured, which makes a caricature 🧠.

## Algorithmic implications

- **Balanced pooled prior.** For K group models (μ_k, Σ_k), weight each group equally, never by its frequency in the training data: μ = (1/K)Σμ_k and Σ = (1/K)Σ[Σ_k + (μ_k−μ)(μ_k−μ)ᵀ] 🧠. With a single dataset, inflate variance along the known between-group directions by Table 5's k 🧠.
- **Explicit between-group basis.** When building a shape PCA:
  1. Procrustes-align the scans.
  2. Estimate the within-group covariance.
  3. Keep the group-mean offsets as separate basis vectors with wide priors (σ ≈ half the largest offset).
  4. Reweight scans by inverse group frequency.

  This stops the dominant group's mean from becoming the zero point 🧠.
- **Mixture without labels.**
  - Use a Gaussian mixture over shape clusters with uniform weights and responsibilities computed only from observed geometry. It avoids a unimodal compromise; Koppen et al. 2018 is precedent 🧠.
  - Never surface or store a cluster as an ethnicity. Racial or ethnic origin is special-category data under GDPR Art. 9 🧠.
  - A user may pin a named norm set for z-score display only.
- **Discrete latents.**
  - Fold: {none, palpebral, tarsal, inversus}. Crease: {absent, low, high}. Give each state its own shape keys, so PCA does not smear them into a half-fold nobody has 🧠.
  - Fit `true_en = visible_en + δ·medial`, with δ ~ HalfNormal(2 mm) when a fold is present and N(0, 0.7 mm) otherwise. Keep narrow priors on bony intercanthal width and interpupillary distance 🧠.
- **Prior weight only where data are missing.**
  - Cap the prior at about 10–20% of the objective where landmarks are seen in two or more views.
  - Report posterior SD per region.
  - If the radix, tip, lip or occiput estimate is more than 70% prior-determined, request a profile or top view instead of returning the mean 🧠.
- **Landmark reliability.** Weight landmarks by local contrast and detector confidence, never by how typical they look to the training set 🧠.
- **Albedo.** Do not regularise skin tone toward an albedo PCA mean. Solve lighting from a grey card or from multiple views 🧠.
- **Audit.** On a consented test set with self-reported groups, report per-group signed bias on al–al, radix, sn–prn, vermilion and cephalic index, and the worst-group/best-group error ratio. Targets: |bias| < 0.25 within-group SD and a ratio < 1.2. Benchmarks such as NoW and REALY are not demographically balanced, so their mean errors hide group gaps 🧠 ↔️.
- **User interface.** Default the reference set to "pooled (balanced)". Label z-scores "outside reference", never "abnormal". A gate at |z| > 3 should prompt re-checking landmarks and camera, never sculpting toward the mean 🧠.
- **Licences.** BFM and older FLAME releases were research-only, and newer FLAME terms may differ. Verify a prior's licence before shipping it 🧠 ↔️.

## Disagreements, myths & open questions

- **Lewontin vs Edwards** ↔️. Both are right at different levels: single traits separate groups weakly, but traits combined classify well. Priors should therefore have wide marginals with correlated structure.
- **Race vs clines** ↔️. Livingstone (1962) and modern genetics favour continuous clines. Typologies in the style of Coon, Garn & Birdsell (1950) persist in art references and character-creator presets.
- **Climate adaptation** ↔️.
  - Nose shape: well supported, though drift explains much of the variation.
  - East Asian facial flatness as cold adaptation: contested; Steegmann's frostbite studies gave weak support.
  - Epicanthal fold as an adaptation to cold, glare or UV: speculative.
- **Plasticity** ↔️. Boas (1912) reported cranial-index change in immigrants' children. Sparks & Jantz (2002) found the effect small; Gravlee, Bernard & Leonard (2003) defended it. Secular change (Jantz & Jantz 2000) also ages old norms 🧠.
- **Myths:**
  - "Asian eyes are small": fissure length is similar; the fold, fat and crease change what is visible 🧠.
  - "African noses are wide and flat": Africa is the most variable region 🧠.
  - "East Asian faces are flat in profile": the radix is low, but profile convexity is similar or greater 🧠.
  - "The golden ratio / Marquardt mask is universal": it is a Eurocentric ideal 🧠 ↔️.
- **Matched vs pooled priors** ↔️. Matched priors help typical members of a group and hurt atypical ones. Pooled-balanced priors are fairer but weaker. This library's stance is pooled-balanced priors plus measurement.
- **Open questions:**
  - Multi-population 3D soft-tissue norms are scarce. South Asian, Middle Eastern and North African, Indigenous American, Pacific, Aboriginal Australian, Central Asian and admixed people are underrepresented.
  - Radix and lid-crease norms in millimetres are not established.
  - How biased are the 2024–2026 3DMMs and landmark detectors (time-sensitive)?
  - Table 2 needs sourced values whose measurement method matches.

## Sources

No harvest file or earlier draft existed for this topic, so no URLs are cited. Sourced population values elsewhere in the library: `anatomy/anthropometric-norms.md` (Tables 2 and 5), `anatomy/forensic-reconstruction.md`, `anatomy/mouth-lips-teeth.md`, `anatomy/face-perception-likeness.md`.

**Further reading (by name, not yet linked)**
- Lewontin 1972, "The apportionment of human diversity", *Evol Biol*.
- Rosenberg et al. 2002, "Genetic structure of human populations", *Science*.
- Relethford 2002, "Apportionment of global human genetic diversity based on craniometrics and skin color", *AJPA*.
- Howells 1973, *Cranial Variation in Man*.
- Manica, Amos, Balloux & Hanihara 2007, "The effect of ancient population bottlenecks on human phenotypic variation", *Nature*.
- Harvati & Weaver 2006, "Human cranial anatomy and the differential preservation of population history and climate signatures", *Anat Rec*.
- von Cramon-Taubadel 2011, "Global human mandibular variation reflects differences in agricultural and hunter-gatherer subsistence strategies", *PNAS*.
- Edwards 2003, "Human genetic diversity: Lewontin's fallacy", *BioEssays*.
- Livingstone 1962, "On the non-existence of human races", *Curr Anthropol*.
- Hanihara 2000, "Frontal and facial flatness of major human populations", *AJPA*.
- Thomson & Buxton 1923, "Man's nasal index in relation to certain climatic conditions", *JRAI*.
- Zaidi et al. 2017, "Investigating the case of human nose shape and climate adaptation", *PLoS Genet*.
- Adhikari et al. 2016, "A genome-wide association scan in admixed Latin Americans identifies loci influencing facial and scalp hair features", *Nat Commun*.
- Claes et al. 2018, "Genome-wide mapping of global-to-local genetic effects on human facial shape", *Nat Genet*.
- Jeong et al. 1999, "The Asian upper eyelid: an anatomical study with comparison to the Caucasian eyelid", *Arch Ophthalmol*.
- Migliori & Gladstone 1984, "Determination of the normal range of exophthalmometric values for black and white adults", *Am J Ophthalmol*.
- Farkas et al. 2005, "International anthropometric study of facial morphology in various ethnic groups/races", *J Craniofac Surg*.
- Porter & Olson 2001, "Anthropometric facial analysis of the African American woman", *Arch Facial Plast Surg*.
- Ofodile, Bokhari & Ellis 1993, "The black American nose", *Ann Plast Surg*.
- Legan & Burstone 1980, "Soft tissue cephalometric analysis for orthognathic surgery", *J Oral Surg*.
- Hefner 2009, "Cranial nonmetric variation and estimating ancestry", *J Forensic Sci*.
- Hiernaux 1974, *The People of Africa*.
- Bryc et al. 2015, "The genetic ancestry of African Americans, Latinos, and European Americans across the United States", *AJHG*.
- Sparks & Jantz 2002, "A reassessment of human cranial plasticity: Boas revisited", *PNAS*.
- Gravlee, Bernard & Leonard 2003, "Heredity, environment, and cranial form", *Am Anthropol*.
- Jantz & Meadows Jantz 2000, "Secular change in craniofacial morphology", *Am J Hum Biol*.
- Coon, Garn & Birdsell 1950, *Races*.
- Martin & Saller 1957, *Lehrbuch der Anthropologie*.
- Grother, Ngan & Hanaoka 2019, NISTIR 8280 (FRVT Part 3: Demographic Effects).
- Paysan et al. 2009, BFM, AVSS.
- Li, Bolkart, Black, Li & Romero 2017, FLAME, SIGGRAPH Asia.
- Booth et al. 2016, "A 3D morphable model learnt from 10,000 faces", CVPR.
- Yang et al. 2020, FaceScape, CVPR.
- Yin et al. 2006, BU-3DFE, FG.
- Koppen et al. 2018, "Gaussian mixture 3D morphable face model", *Pattern Recognit*.
- Zielonka, Bolkart & Thies 2022, MICA, ECCV.
- Feng, Bolkart, Tesch, Black & Abrevaya 2022, "Towards racially unbiased skin tone estimation via scene disambiguation" (TRUST), ECCV.
