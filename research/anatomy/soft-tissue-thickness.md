# Facial soft-tissue thickness (forensic tissue depth tables)

> Facial soft-tissue thickness (FSTT) is the skin-to-bone distance at craniometric landmarks; in photo-based work it runs backwards, from the photographed skin to the hidden bone. Adult means rise from ~3 mm at rhinion and ~5–6.5 mm at glabella and nasion, through ~10–13 mm at the lips and chin, to ~15–21 mm over the buccal and masseter region, with SDs of ~1 mm at thin midline sites and 3–5 mm laterally. BMI is the strongest covariate; sex effects depend on the site; age and ancestry effects are small and contested; and the method (cadaver needle, ultrasound, CT, CBCT, MRI; supine or upright) moves values as much as demographics do. Use the tables as wide log-normal priors for hidden bone and as a plausibility check, never as a source of likeness or of nose, lip or ear shape.
>
> Evidence status: 4 ✅ / 25 📄 / 52 🧠 / 20 ↔️ — 🧠 items are queued for web verification.

## Key facts

Legend: ✅ two or more independent input sources agree · 📄 one input source · 🧠 author knowledge, not yet checked · ↔️ contested. Citations rest on harvested search snippets, not full texts.

**What the tables are**
- **Definition.** FSTT is the bone-to-skin distance at a landmark, normally taken perpendicular to the bone. The convention matters: in 100 Brazilian CBCT scans, "perpendicular to bone" was reproducible at all 32 landmarks, while "perpendicular to skin" and "direct" were not [15] 📄.
- **Landmark sets are sparse and not standardised.** Typical sets have fewer than ~53 points [23]: 22 in Greek CT [3], 31 in Korean CBCT [10], 33 in Chinese CT [11], and 41 or 60 in other Chinese samples [12][13] ✅. A scoping review lists landmark standardisation and table validation as open problems [18] 📄.
- **Size of the literature.** It spans 139 studies since 1883, with more than 220,000 measurements from more than 19,500 adults. The pooled T-tables were first calculated in 2008 and are still in use [8] 📄. A 2023 systematic review found that 30 of 84 articles gave sex-, age- or ethnicity-specific databases [7] 📄. A pooled table from 66 studies showed wide variation between techniques [9] 📄.
- **T-table logic (Stephan).** A T-table gives weighted means of study means, pooled across sex, ancestry and method. Stephan's case is that subgroup differences (~1–2 mm) are smaller than the within-group SD plus measurement error, so splitting the data rarely helps 🧠 ↔️. Later tallies add the robust "shorth" and "75-shormax" statistics 🧠. The brief's "Stephan 2009" is really Stephan & Simpson 2008 (*J Forensic Sci*, part I adults, part II sub-adults) 🧠, which matches the 2008 date in [8].
- **Rhine & Moore (1984).** These are needle-puncture data from American "Caucasoid" cadavers: 21 landmarks split by sex and build (slender, normal, obese), with small subgroups and no modern validation 🧠. Rhine & Campbell (1980) is the matching table for American Black cadavers 🧠.
- **De Greef et al. (2006).** An in-vivo ultrasound database of 967 Belgian adults [22] 📄, with ~52 landmarks stratified by sex, age and BMI 🧠. The "12 CT scans" in the same snippet probably belong to Leuven's computerised-reconstruction work ↔️.

**Magnitudes**
- **Thin midline zone.** Forehead, glabella, nasion and rhinion carry 3–7 mm, so the profile follows the bone within a few mm 🧠. The library's pooled values for glabella, nasion and rhinion are 5.5 / 6.0 / 3.0 mm (`skull-osteology.md`, Table 1).
- **Lips, philtrum and chin: 9–16 mm**, varying widely between studies. Mid-philtrum was 16.41 mm (men) and 13.95 mm (women) by Iranian MRI [2], but 10.80 mm in Nigerian women by CT, whose labiomental fold was 11.79 mm [4] ↔️.
- **Cheek and masseter** are the thickest sites at 15–25 mm, so in normal-BMI faces only the zygomatic arch (~7 mm) and the mandibular border read through 🧠.
- **Skin alone is a small part of the total.** Mid-cheek dermis was 1.877 mm (men) and 1.580 mm (women) by ultrasound; epidermis did not differ by sex, and skin thickness did not track BMI [6] 📄.

**Covariates**
- **BMI is the dominant covariate** [16], and it raises depth [2][5][19] ✅. Iranian nasion rose from 5.57 to 8.25 mm between the lowest and highest BMI groups [2]. Thai underweight and normal-BMI groups differed at every landmark [5]. Obese children and adolescents have thicker tissue [19].
- **Sex differences depend on the site** ↔️. Iranian MRI and Korean CBCT samples show men thicker at most landmarks [2][10]. Thai data show women thicker at several sites and men only in the nasal and perioral regions [5]. Expect men to be +1–2.5 mm on the midline lower face (philtrum, lips, chin) and women equal or thicker over the malar region, the infraorbital region and gonion 🧠.
- **Age is contested** ↔️. Greek CT found limited age and sex effects [3]. Chinese layered CT (n = 1174, ages 18–90) found significant age and sex effects on total, fat and muscle thickness [11]. Thai subjects over 50 changed little [5], and [16] says FSTT falls as muscle tone is lost. Expert pattern: lips thin with age, infraorbital and jowl depth rises, and midlife weight gain confounds the trend 🧠.
- **Ancestry** ↔️. Rhine-type tables and Flynn (1989) use ancestry-specific values; Flynn reports a thicker soft-tissue chin in Black than White Americans [27] 📄 (secondary copy). Stephan argues that ancestry categories add little 🧠. Studies also compare regions within a single country [1] 📄.

**Method**
- **CBCT is usable** [14][15], with 0.3 mm voxels recommended and weaker soft-tissue contrast than CT or MRI [25] ✅.
- **Observer error is about 0.2–1.5 mm** (inter-observer TEM 0.19–1.45 mm [3]); a 2D-versus-3D comparison found no significant difference in observer error [17] ↔️. Disease lowers reliability: ICC 0.49 in linear scleroderma against 0.66 in controls [24] 📄.
- **Needles and posture bias values.** Needles compress tissue, cadavers dehydrate or bloat, and supine CT or MRI lets cheek and jowl tissue fall back compared with an upright photo ↔️ 🧠.
- **Dense methods.** Per-vertex FSTT statistics come from registering a template skull to CT skulls [20] 📄. Skull-to-Face (2024) learns the joint distribution at landmarks, limited by a small paired dataset [21] 📄.
- **Mean-depth tables are weakest** at the nose, mouth and ears, which have little bony support [26] 📄.

## Numbers & reference tables

**Table 1: Adult consensus ranges (mixed sex, normal BMI; mostly European-derived pooled literature).** Use these as engine defaults. Every value is 🧠 except where marked.

| Landmark (abbr) | Typical mean, mm | Range of study means, mm | Typical SD, mm | Sex | BMI sensitivity | Status |
|---|---|---|---|---|---|---|
| Supraglabella / mid-forehead (sg) | ≈4.5 | 3.5–6 | ~1.0 | M≥F | low | 🧠 |
| Glabella (g) | ≈5.5 | 4.5–6.5 | 1.0–1.3 | M≥F | low | 🧠 |
| Nasion (n) | ≈6–6.5 | 5–7.5 (5.57→8.25 by BMI) | 1.2–1.5 | M≥F | moderate | 🧠; BMI 📄 [2] |
| Rhinion (rhi) | ≈3 | 2–4 | 0.7–1.0 | ≈ | very low | 🧠 |
| Mid-philtrum (mp) | ≈11–12 | 10.8 (NG F) – 16.4 (IR M) | 2–2.5 | M>F | moderate | ↔️ [2][4] |
| Labrale superius (ls) | ≈11–12 | 9–14 | ~2 | M>F | moderate | 🧠 |
| Labrale inferius (li) | ≈12–13 | 10–16 | 2–2.5 | M>F | moderate | 🧠 |
| Supramentale / labiomental (sm) | ≈10.5–11 | 9–13 (11.79 NG F) | 1.5–2 | M>F | moderate | 🧠; 📄 [4] |
| Pogonion (pg) | ≈11 | 9–13 | 2–2.5 | M≥F | moderate | 🧠 |
| Gnathion (gn) | ≈8 | 6.5–10 | ~2 | M≥F | high | 🧠 |
| Menton (me) | ≈7 | 5–9 | 2–2.5 | ↔ | high | ↔️ |
| Frontal eminence (fe) | ≈4–4.5 | 3.5–5.5 | ~1.0 | ≈ | low | 🧠 |
| Mid-supraorbital (mso) | ≈6.5–8 | 5–9 | 1.2–1.5 | M≥F | low | 🧠 |
| Mid-infraorbital (mio) | ≈6–7 | 4.5–9 | 1.5–2 | F≥M, rises with age | moderate | 🧠 |
| Lateral orbit (lo) | ≈6–10 | 5–11, definition-dependent | 1.5–2 | F≥M | moderate | ↔️ |
| Zygion / arch (zy) | ≈7 | 5–9 | 1.5–2 | ≈ | moderate | 🧠 |
| Inferior malar (imal) | ≈12–14 | 10–18 | 2.5–3.5 | F≥M | high | 🧠 |
| Supraglenoid (sgl) | ≈8–9 | 6–12 | ~2 | ≈ | moderate | 🧠 |
| Supra-M2 (buccal, maxillary) | ≈18–21 | 15–25 | 3.5–5 | ↔ | very high | 🧠 |
| Occlusal line / mid-masseter (ocl) | ≈17–19 | 14–24 | 3.5–5 | M≥F (muscle) | very high | 🧠 |
| Sub-M2 (mandibular) | ≈15–17 | 12–22 | 3.5–5 | ↔ | very high | 🧠 |
| Mid-ramus (mr) | ≈15–18 | 12–22 | 3–4 | M≥F | high | 🧠 |
| Gonion (go) | ≈11–12 | 8–18 | 3–4 | F≥M in some samples | high | ↔️ |
| Mid-mandibular border (mm) | ≈9–10 | 7–12 | 2–2.5 | ≈ | high | 🧠 |

**Table 2: Rhine & Moore 1984, American "Caucasoid", normal build, cadaver needle (mm).** These values are recalled from widely reproduced copies (e.g. Taylor, *Forensic Art and Illustration*). Treat them as ±0.5 mm until checked against the original 🧠. Cadaver values may run thinner than living upright values.

| # | Landmark | M | F | # | Landmark | M | F |
|---|---|---|---|---|---|---|---|
| 1 | Supraglabella | 4.25 | 3.5 | 12 | Supraorbital | 8.25 | 7.0 |
| 2 | Glabella | 5.25 | 4.75 | 13 | Suborbital | 5.75 | 6.0 |
| 3 | Nasion | 6.5 | 5.5 | 14 | Inferior malar | 13.25 | 12.75 |
| 4 | End of nasals | 3.0 | 2.75 | 15 | Lateral orbit | 10.0 | 10.75 |
| 5 | Mid-philtrum | 10.0 | 8.5 | 16 | Zygomatic arch | 7.25 | 7.5 |
| 6 | Upper lip margin | 9.75 | 9.0 | 17 | Supraglenoid | 8.5 | 8.0 |
| 7 | Lower lip margin | 11.0 | 10.0 | 18 | Gonion | 11.5 | 12.0 |
| 8 | Chin–lip fold | 10.75 | 9.5 | 19 | Supra-M2 | 19.5 | 19.25 |
| 9 | Mental eminence | 11.25 | 10.0 | 20 | Occlusal line | 18.25 | 17.0 |
| 10 | Beneath chin | 7.25 | 5.75 | 21 | Sub-M2 | 16.0 | 15.5 |
| 11 | Frontal eminence | 4.25 | 3.5 | | | | |

The sourced point values (Iranian, Nigerian, skin-layer, TEM, ICC, voxel) are in Key facts and in `data/soft-tissue-thickness.json` (`sourced_point_values`).

**Table 3: Datasets worth mining.**

| Study | Modality / posture | n | Landmarks | Covariates | Src | Status |
|---|---|---|---|---|---|---|
| De Greef 2006, Belgium | ultrasound, living | 967 | ~52 🧠 | sex, age, BMI | [22] | 📄 |
| Korean | CBCT | 100 (50 M / 50 F) | 31 | sex | [10] | 📄 |
| Chinese, layered | CT, skin/fat/muscle | 1174 (18–90 y) | 33 | sex, age | [11] | 📄 |
| Yangtze Han | CBCT, 3D models | 424 | 60 | sex, age, BMI, malocclusion | [12] | 📄 |
| Central Chinese | CT | 280 | 41 | total and fat | [13] | 📄 |
| Greek | CT | 100 (50 M / 50 F)? | 22 (5 + 17) | sex, age | [3] | 📄 (n unconfirmed) |
| Thai, ≥ middle age | ultrasound | see `skull-osteology.md` | — | sex, age, BMI | [5] | 📄 |
| Rhine & Moore 1984; Helmer 1984 (US); Manhein 2000 (US, children and adults) | needle / ultrasound | small–moderate | 21–34 | sex, build, ancestry | — | 🧠 |

**Table 4: How method and covariates shift values.**

| Factor | Direction | Approx. magnitude | Most affected | Status |
|---|---|---|---|---|
| BMI | up | ~+0.1–0.2 mm/BMI unit at thin midline sites; ~+0.3–0.7 at cheek, jaw and submental | buccal, gonion, menton | ✅ direction [2][5]; 🧠 slopes |
| Sex (M−F) | site-dependent | +1–2.5 mm lips and philtrum; −0.5–1.5 mm malar and gonion | lower midline, lateral cheek | ↔️ |
| Age (adult) | mixed | lips −0.2–0.4 mm/decade after ~40; infraorbital up | lips, infraorbital, jowl | ↔️ 🧠 |
| Cadaver vs living | cadaver usually thinner or distorted | ~0.5–2 mm | most sites | ↔️ 🧠 |
| Supine vs upright | gravity shift | <1 mm midline; ~1–3 mm lateral and lower face | cheek, gonion, submental | 🧠 |
| Needle / ultrasound probe pressure | thinner | ~0.5–1+ mm at thick sites | cheek | 🧠 |
| Vector convention | bone-normal most reproducible | up to several mm at curved sites | gonion, malar | 📄 [15] |

## Applying this to photo→3D face sculpting in Blender

1. **Ask before you guess.** With consent, record height, weight (giving BMI), age, sex, dental status (dentures, missing molars, orthodontics), recent weight change and fillers. BMI and dentition move depth more than ancestry does 🧠.
2. **Work in millimetres:** Metric, Unit Scale 0.001, Length = Millimeters, as in `skull-osteology.md`.
3. **Photos own the visible skin.** Tables never override a calibrated silhouette; their job is the hidden layer.
4. **Place bony empties from skin landmarks.** Offset each skin landmark inward along the local bone normal by the Table 1 mean: g −5.5, n −6, rhi −3, pg −11, gn −8 mm. Midline offsets hold to about ±1–2 mm, cheek and jaw offsets only to ±4–6 mm 🧠.
5. **Warp a skull template** (a CC0 or self-made skull, in mm) to those empties with Lattice or Mesh Deform. Use it to place the brow-ridge break, the zygomatic arch line, the mandibular border and the jaw angle.
6. **Peg check.** This is the American method: cylinders on the skull at each landmark, along the bone normal, with length equal to the depth. Tips should touch the sculpt at thin sites. A tip poking through means the skin is too thin or the skull too big; a gap at g, n or rhi means the skull is too small or misplaced 🧠.
7. **Thickness map.** In Geometry Nodes on the skin, take Object Info (skull) → Geometry Proximity, or Raycast along the inverted normal. Store the distance with Store Named Attribute `fstt_mm` and show it through a Color Ramp with stops at 3, 6, 10, 15 and 20 mm. Node names change between releases, so verify them 🧠.
8. **Quick envelope.** On a skull duplicate, paint a vertex group with weight = t / t_max and add Solidify (thickness t_max, offset +1, that group). The result is an "average skin" shell to read against the sculpt 🧠.
9. **Photos from different weights.** Sculpt one neutral BMI and add a "weight" shape key along normals, scaled regionally: large at cheek, jowl and submental areas, near zero on the nasal dorsum and forehead.
10. **What goes wrong:** one uniform depth everywhere; Rhine cadaver numbers on a living upright subject; supine CT values for jowls; skin-normal measurement on curved bone; bone inferred from the cheek outline; nose, lips or ears taken from depth tables [26]; false trust in ancestry tables; ignored dentures or lost molars, which collapse perioral and buccal depth; a uniform BMI "inflate".

## Algorithmic implications

- **Two-layer model.** `skin(x) = bone(x) + t(x)·n̂_bone(x)`, where n̂ is the skull normal smoothed over ~5–10 mm (rough bone gives noisy vectors). This follows the reproducible perpendicular-to-bone convention [15]. Midline landmarks are constrained to the midsagittal plane.
- **Per-landmark prior.** Use a log-normal: `log t_i ~ N(log μ_i + β_bmi,i·(BMI−22) + δ_sex,i/μ_i·s + β_age,i·(age−40), σ_i²)`, with s = +½ for male and −½ for female, and 0 if sex is unknown. Defaults (🧠):
  - **σ_log:** 0.15–0.20 at sg, g, n, rhi, fe and mso; 0.20–0.25 at lips, pg, gn and the orbital rims; 0.30–0.40 at imal, buccal, ocl, mr and go; 0.30 at me. This matches `skull-osteology.md`.
  - **Missing covariates:** add 0.05–0.10 to σ_log when BMI is missing, and 0.05–0.10 on lateral and lower-face sites when the source data are supine or cadaveric.
  - **β_bmi (log per BMI unit):** ≈0.01 at forehead and rhinion, 0.02–0.03 at nasion, lips and chin, 0.03–0.05 at cheek, jaw and menton. As a check, nasion 6 mm at BMI 22 becomes ≈7.3–8 mm at BMI 32, consistent with [2].
  - **δ_sex (M−F, mm):** +0.5 at forehead and nasion, +1.5 to +2.5 at mp, ls and li, +1 at pg; −0.5 to −1.5 at imal, mio and go. β_age gets a low weight (↔️).
- **Converting a published mean ± SD to log-normal:** `σ_log = sqrt(ln(1 + (SD/mean)²))` and `μ_log = ln(mean) − σ_log²/2`. Pool several studies by n-weighted means of means within a modality, and use median or shorth across modalities.
- **Hard constraints.** Penalise skin inside bone with a hinge on signed distance, plus `t ≥ t_min`, where t_min = 2 mm (1.5 mm at rhinion and the nasal dorsum) and the weight is large.
- **Inverse use (skin → bone)** for photo-first fitting: `b_i = s_i − t_i n̂_i`, with `Σ_b = Σ_s + (μ_i σ_i)² n̂n̂ᵀ + Σ_def`, where Σ_def is the 1–3 mm tangential uncertainty in the landmark definition. Thin sites pin the bone to ~1–1.5 mm, cheek sites only to 5–8 mm. Let g, n, rhi, pg and gn drive the skull warp (TPS); zy, go and imal are weak hints.
- **Dense field.** Interpolate μ and σ over the skull from the landmarks with geodesic RBF, or adopt dense statistics [20].
- **Diagnostics.** Report a z-score per landmark and flag |z| > 2.5 (sculpt error or unusual subject) on a heatmap. Never auto-correct: likeness wins.
- **Shared parameters.** When photo sessions span a weight change, treat BMI as a per-session latent and share the skull across sessions.
- **Out of scope.** Do not encode nose, lip or ear shape through FSTT (see `mouth-lips-teeth.md` and `ear.md`); children need sub-adult priors (`child-growth.md`).

## Disagreements, myths & open questions

- **Pool or split** ↔️. Stephan's T-tables pool everything 🧠, while population databases [7][10]–[13] and regional studies [1] split by group. Neither has been tested for likeness. Recommendation: pooled means with covariate slopes and wide σ.
- **Sex and age** ↔️. The sex effect is regional, not global [2][5][10]. The age effect was limited in [3], significant in [11] and minimal over 50 in [5].
- **Living and dead** ↔️. A Japanese cadaver MDCT study (secondary report, unconfirmed) found cadaveric data thinner than living data. Supine-to-upright corrections exist (Munn & Stephan 2018) 🧠 but are not in this library.
- **Observer error** ↔️: judged unreliable in [3], comparable across 2D and 3D in [17].
- **Myth: "the pegs give you the face."** Tables give only an average envelope, and reconstructions keep errors of several mm, worst at the nose and mouth [26] 📄 🧠.
- **Myth: "ultrasound only measures skin."** Skin-only studies exist [6], but total-depth ultrasound is routine [5][22] 📄.
- **Myths: "heavier means uniformly thicker" and "skull size predicts depth."** The BMI effect is strongly regional, and craniometric dimensions correlate only weakly with FSTT (Simpson & Henneberg 2002) 🧠.
- **Open questions:**
  - dense, upright, living, multi-ancestry data;
  - layered skin/fat/muscle priors [11];
  - public paired skull–face data, which are scarce [21] (decedent CT archives such as NMDID: access terms to verify 🧠);
  - validation of tables for perceived likeness rather than mm error.

## Sources

[1] Facial soft tissue thickness in forensic facial reconstruction: Impact of regional differences in Brazil — https://pmc.ncbi.nlm.nih.gov/articles/PMC9286276/ — paper — n.d.
[2] Facial Soft Tissue Thickness of Midline in an Iranian Sample: MRI Study — https://pmc.ncbi.nlm.nih.gov/articles/PMC5543663/ — paper — n.d.
[3] Facial soft tissue depth of a contemporary adult Greek population — https://pmc.ncbi.nlm.nih.gov/articles/PMC11490456/ — paper — n.d.
[4] A preliminary study of facial soft tissue thickness for forensic facial reconstruction in a Nigerian adult female community — https://pmc.ncbi.nlm.nih.gov/articles/PMC13499785/ — paper — n.d.
[5] Sex, age, and body mass index influence on facial soft tissue thickness in a Thai population above middle age by ultrasonographic imaging — https://pubmed.ncbi.nlm.nih.gov/41701465/ — paper — 2026 (unconfirmed)
[6] Ultrasonographic analysis of facial skin thickness in relation to age, site, sex, and body mass index — https://pmc.ncbi.nlm.nih.gov/articles/PMC10370326/ — paper — n.d.
[7] Systematic review on forensic craniofacial reconstruction. I. Facial soft-tissue thickness — https://pubmed.ncbi.nlm.nih.gov/37531497/ — review — 2023
[8] International Journal of Legal Medicine review of global FSTT data (s00414-023-03087-x) — https://link.springer.com/article/10.1007/s00414-023-03087-x — review — 2023
[9] NCJRS abstract: pooled soft-tissue-depth table from 66 studies — https://ojp.gov/index%2Ephp/node/1311086 — abstract — n.d.
[10] Facial soft tissue thickness database for craniofacial reconstruction in Korean adults — https://pubmed.ncbi.nlm.nih.gov/22621203/ — paper — n.d.
[11] Layer-specific facial soft-tissue thickness in 1174 Chinese adults — https://pubmed.ncbi.nlm.nih.gov/42385786/ — paper — n.d.
[12] Facial soft tissue thickness in Yangtze River delta Han population (CBCT) — https://pubmed.ncbi.nlm.nih.gov/32217445 — paper — n.d.
[13] Age- and Sex-Related Measurements of Total Craniofacial Soft Tissue Thickness and Fat in a Central Chinese Population — https://pubmed.ncbi.nlm.nih.gov/34238872/ — paper — n.d.
[14] Accuracy and reliability of facial soft tissue depth measurements using cone beam computer tomography — https://pubmed.ncbi.nlm.nih.gov/20236780/ — paper — n.d.
[15] Reproducibility of Facial Soft Tissue Thickness Measurements Using Cone-Beam CT According to the Measurement Methods — https://pubmed.ncbi.nlm.nih.gov/25845397/ — paper — n.d.
[16] Assessing the contribution of orthodontic profiles in predicting facial soft tissue thickness for forensic facial approximation — https://pmc.ncbi.nlm.nih.gov/articles/PMC12532767/ — paper — n.d.
[17] Evaluating the compatibility of the 2D and 3D facial soft tissue depth measurement methods — https://pmc.ncbi.nlm.nih.gov/articles/PMC12808181/ — paper — 2025
[18] Forensic facial approximation methodologies applied to the Brazilian population: a scoping review — https://pmc.ncbi.nlm.nih.gov/articles/PMC13658438 — review — n.d.
[19] Obesity and Overweight Conditions in Children and Adolescents and Their Impact on Craniofacial Morphology: A Systematic Review — https://pmc.ncbi.nlm.nih.gov/articles/PMC11940931/ — review — n.d.
[20] A method for automatic forensic facial reconstruction based on dense statistics of soft tissue thickness — https://arxiv.org/pdf/1808.07334 — preprint (PLOS ONE 2019) — 2018
[21] Skull-to-Face: Anatomy-Guided 3D Facial Reconstruction and Editing — https://arxiv.org/pdf/2403.16207 — preprint — 2024
[22] KU Leuven postprint (De Greef-related in-vivo / CT soft-tissue abstract; attribution inferred from snippet) — https://lirias.kuleuven.be/bitstream/123456789/420593/1/3606_postprint.pdf — paper — n.d.
[23] de Buhan & Nardoni, sparse-landmark soft-tissue thickness and dense reconstruction (Paris-Saclay) — https://www.imo.universite-paris-saclay.fr/~de-buhan/deBuhanNardoni.pdf — paper — n.d.
[24] Linear scleroderma CBCT soft-tissue thickness reliability study — https://pubmed.ncbi.nlm.nih.gov/29298697/ — paper — n.d.
[25] CBCT review on facial soft-tissue measurement (voxel size, contrast) — https://pmc.ncbi.nlm.nih.gov/articles/PMC6631689/ — review — n.d.
[26] Computerized facial approximation based on FSTT and geometric morphometrics — https://pmc.ncbi.nlm.nih.gov/articles/PMC10557396/ — paper — 2023 (unconfirmed)
[27] Flynn 1989 cephalometric soft-tissue norms, Black vs White American adults (secondary Scribd copy) — https://www.scribd.com/document/684241970/Flynn-1989 — secondary copy — 1989

**Further reading (by name, not yet linked)**
- Stephan CN & Simpson EK, "Facial soft tissue depths in craniofacial identification (part I: adults; part II: sub-adults)", *J Forensic Sci*, 2008.
- Stephan CN, "The application of the central limit theorem and the law of large numbers to facial soft tissue depths: T-Table robustness and trends since 2008", *J Forensic Sci*, 2014.
- Stephan CN, "2018 tallied facial soft tissue thicknesses for adults and sub-adults", *Forensic Sci Int*, 2017.
- Rhine JS & Moore CE, *Tables of Facial Tissue Thickness of American Caucasoids in Forensic Anthropology*, Maxwell Museum Technical Series 1, 1984; Rhine JS & Campbell HR, "Thickness of facial tissues in American Blacks", *J Forensic Sci*, 1980.
- De Greef S et al., "Large-scale in-vivo Caucasian facial soft tissue thickness database for craniofacial reconstruction", *Forensic Sci Int*, 2006.
- Helmer R, *Schädelidentifizierung durch elektronische Bildmischung*, 1984 (ultrasound depths).
- Manhein MH et al., "In vivo facial tissue depth measurements for children and adults", *J Forensic Sci*, 2000.
- Simpson E & Henneberg M, "Variation in soft-tissue thicknesses on the human face and their relation to craniometric dimensions", *Am J Phys Anthropol*, 2002.
- Domaracki M & Stephan CN, "Facial soft tissue thicknesses in Australian adult cadavers", *J Forensic Sci*, 2006.
- Munn L & Stephan CN, "Changes in face topography from supine-to-upright position — and soft tissue correction values for craniofacial identification", *Forensic Sci Int*, 2018.
- Wilkinson C, *Forensic Facial Reconstruction*, Cambridge University Press, 2004; Taylor KT, *Forensic Art and Illustration*, CRC Press, 2001.
- Claes P, Vandermeulen D et al., "Computerized craniofacial reconstruction: conceptual framework and review", *Forensic Sci Int*, 2010.
- Gietzen T et al., dense FSTT statistics for automatic facial reconstruction, *PLOS ONE*, 2019.
- New Mexico Decedent Image Database (NMDID), whole-body decedent CT archive (access terms to verify).

## Verification log (2026-11-20)

Four searches were run. No badge changed, so the evidence-status line stands. No data or sources JSON was modified.

1. **Pooled adult FSTT means (Stephan T-table).** Outcome: unconfirmed. Search results gave only bibliographic context (Stephan & Simpson 2008, J Forensic Sci 53(6):1257-1272; the 2014 follow-up found a maximum change of 1.7 mm at gonion; the 2023/2024 IJLM update is the already cited [8]) and no landmark means. Sources seen: https://ojp.gov/ncjrs/virtual-library/abstracts/application-central-limit-theorem-and-law-large-numbers-facial-soft , https://link.springer.com/article/10.1007/s00414-023-03087-x
2. **Rhine & Moore 1984 values (Table 2).** Outcome: unconfirmed. No result reproduced the table. Keep the ±0.5 mm caveat.
3. **De Greef 2006 and BMI slopes.** Outcome: unconfirmed for the BMI slopes and for the ~52 landmarks. Secondary snippets agree on 967 adults and A-mode ultrasound but could not be tied to a verifiable primary URL. The slopes are not verified.
4. **Sex-difference pattern.** Outcome: unconfirmed. The results leaned toward men thicker at most sites; none gave per-landmark data showing women thicker at malar, infraorbital or gonion. Candidate full texts to check later: https://pmc.ncbi.nlm.nih.gov/articles/PMC9914978 , https://pmc.ncbi.nlm.nih.gov/articles/PMC3762959
