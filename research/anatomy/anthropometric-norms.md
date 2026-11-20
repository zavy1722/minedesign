# Quantitative facial anthropometry norms (Farkas and successors)

> Leslie Farkas's caliper-and-tape data on North American White (NAW) subjects aged 1–25 (N = 2,326 [3]) still supply the default millimetre head and face norms. Modern 3D norms (3D Facial Norms database, 3DFN: 2,454 participants aged 3–40 [1][2]) and population studies differ from Farkas through method, era and population. For young NAW adults (M/F), approximate means are: face height n–gn ≈ 121/112 mm (SD 5–7), face width zy–zy ≈ 137/130, intercanthal en–en ≈ 33/32, biocular ex–ex ≈ 90/87, nose width al–al ≈ 35/31, mouth width ch–ch ≈ 53/50, head length ≈ 197/187 and head breadth ≈ 151/144. Population differences in some means (nose width, intercanthal width) are several within-group SDs, so a norm is usable only with its population, sex, age, landmark definition and method attached. A likeness tool should use norms for sanity gates, scale and unseen parts (depth, back of head), never as targets: likeness lives in the deviations.
>
> Evidence status: 6 ✅ / 40 📄 / 82 🧠 / 16 ↔️ — 🧠 items are queued for web verification.

## Key facts

A partial verification pass ran on 2026-11-20 (see the log at the end). The harvest facts come from search snippets, not full texts.

**Datasets and how they were measured**
- **Farkas norms**: direct anthropometry on 2,326 NAW children and adults [3] 📄 (palpation, spreading and sliding calipers, tape; Toronto, about 1970s–80s; young-adult cells of tens to low hundreds per sex, n varying by measurement) 🧠. Primary source: *Anthropometry of the Head and Face* (2nd ed., 1994); full adult tables not retrieved [3] 📄.
- **Criticism.** Kolar (1993) judged inconsistent data-collection protocols the most serious problem in Farkas's dataset [1] 📄. Traditional norm sets cover narrow age ranges and share demographic limits [1] 📄.
- **Farkas's international study** (Farkas, Katic, Forrest et al., J Craniofac Surg 2005;16(4):615–646, exists [19] 📄; the study used 14 measurements [19] 📄 [20]; the figures of roughly 1,470 young adults and about 25 populations were not confirmed 🧠) found, per its abstract summary, nose width significantly greater in Asian and Black groups than NAW, so NAW values do not represent other groups [19] 📄.
- **Inter-ethnic review** (Fang, Clapham & Chung, 2011): 11 neoclassical measurements, 2,359 people, 27 groups, compared by CV; forehead height varied most [5] 📄. Wen et al.'s 2015 Bayesian meta-analysis is a separate work [6] 📄.
- **3DFN**: 2,454 people aged 3–40 (952 M, 1,502 F), cross-sectional, one record per person, captured by stereophotogrammetry [1][2] ✅.
  - Summary-level landmarks, measurements and demographics can be downloaded freely; individual-level data need a Data Access Request [2] 📄.
  - It ships sex-specific 3D growth curves and a MATLAB toolbox [2] 📄, and reports 34 inter-landmark measurements [1] 📄.
  - Participants are described as healthy Caucasian (a Pittsburgh project page says about 2,500 Caucasians aged 3–40) [18] 📄, captured with 3dMD at several US sites (FaceBase says three main sites, the CPCJ paper four) [1][2] ↔️. It therefore adds no population diversity over Farkas.
- **3DFN vs Farkas**: the differences are considerable. The authors attribute them partly to measurement method, and possibly to secular trend and ethnic mix [3] 📄.
- **Headspace** is not a norms table (the harvest found none). It is a capped full-head 3dMD dataset of about 1,500 people behind the Liverpool-York Head Model 🧠. Ergonomic surveys (NIOSH, ANSUR II, SizeChina, CAESAR; Table 3) are large but use their own definitions; menton–sellion is not n–gn 🧠.

**Magnitudes and variation**
- **Face height n–gn.** NAW 121.3 ± 6.8 mm (M) and 111.8 ± 5.2 (F): means 📄 [17] (a Greek study's comparison tables list 121.3 and 111.8 as North American Caucasian "morphological face height"; sex of the 121.3 table inferred from position), SDs not independently checked; the SDs match a secondary copy of Farkas's table [13] 📄. Kosovo Albanian adults: 125.8 ± 6.4 / 115.5 ± 5.0 [4]. Indian students: 121.6 ± 6.5 / 113.6 ± 4.6 [7]. Across samples, adult means run about 120–126 mm (M) and 112–116 (F), with SD about 6–7 and 4.5–5.5 [4][7][13] ✅.
- **ex–ex SD** is 3.6 mm (M) and 4.0 (F) in the secondary Farkas table [13] 📄.
- **en–en** by sample: Kosovo 32.5 ± 2.6 / 31.8 ± 2.3 [4] 📄; Malay (3D) 35.7 / 35.0 [12] 📄; Hong Kong Chinese (3D) 40.6 / 38.3 [11] 📄. That is 32–41 mm across populations and methods ↔️. The sex difference is small, 0.7–2.3 mm [4][11][12] ✅.
- **Sex.** Men are larger on nearly every linear facial dimension [4][7][8][11][12] ✅. The gap is about 3–10%: largest for face height, nose width, jaw and head size (about 1.3–1.7 SD), smallest for en–en and eye-fissure length (about 0.3–0.6 SD) 🧠.
- **Nose width check.** Alare-to-midline is 17.34 / 15.39 mm in 297 adults [8] 📄; doubled (assuming symmetry), al–al ≈ 34.7 / 30.8, matching NAW 34.9 / 31.4 🧠.
- **Width ratios (southern Spain, 3D).** ch–ch/en–en = 1.59 (M) and 1.52 (F); en–en/al–al = 0.89 (M) and 1.01 (F) [9] 📄. Men's noses are wider than their intercanthal distance; women's are about equal to it.
- **Malay nose width** is 39.6 / 36.7 mm [12] 📄. The harvest suspected a different definition. Southeast Asian al–al of about 38–41 mm (M) is plausible as a real population difference ↔️.
- **Variability.** CV is about 3–4% for head length, head breadth and zy–zy, 5–8% for most face widths and heights, and 10–20% for vermilion heights, tip protrusion and philtrum width 🧠.
- **Population vs individual variation.** The spread of population means for al–al (about 31–45 mm) and en–en is 3–5 within-group SDs. For head breadth (cephalic index) it is about 1–2 SD 🧠. A prior with no population label is weak for these measures.
- **Adult ageing.** Nose length and ear length keep increasing, the nasal tip drops, the upper lip lengthens, the vermilion thins, and lower-face height can shrink with tooth loss 🧠.

**Method offsets** (numbers in Table 6)
- **Direct vs 3D** differences are mostly under 2 mm, even where statistically significant [16][14] ✅; CT reads Go–Go 2.34 mm wider than 3dMD [15] 📄.
- **Calipers vs surfaces.** Calipers compress tissue and palpate bone at zy, go, eu, g and op. A 3D surface cannot be palpated, so lateral, fat-covered points shift by several mm 🧠.
- **Chords vs projections.** Farkas distances are straight-line (tangential) chords, with some projective ones in the Frankfort horizontal (FH) frame. A photo gives 2D projections. These agree for en–en and ex–ex in a frontal view, but heights and nasal measures shorten with head pitch 🧠.

## Numbers & reference tables

**Table 1: Default priors, young adult NAW (Farkas-type, direct anthropometry, about 18–25 y), mm.** Recalled ranges of means; single values where recall is firm. More rows (v–gn, ft–ft, tr–gn) are in the data file.

| Measure | Landmarks | Male mean | Female mean | SD (M/F) | CV | Status |
|---|---|---|---|---|---|---|
| Head length | g–op | 194–199 | 184–189 | 6–7 | 3–4% | 🧠 |
| Head breadth | eu–eu | 149–154 | 141–146 | ~5 | 3–4% | 🧠 |
| Head circumference | tape, g–op level | 565–580 | 545–560 | ~15 | ~3% | 🧠 |
| Face width | zy–zy | 135–140 | 127–132 | 4–6 | 3–4% | 🧠 |
| Mandible width (caliper on bone) | go–go | 94–100 | 88–94 | 5–7 | ~6% | 🧠 |
| Morphological face height | n–gn (gn = me′) | 121.3 | 111.8 | 6.8 / 5.2 | 5% | 📄 mean [17]; SD 📄 [13] |
| Upper face height | n–sto | 75–79 | 69–72 | ~4 | 5% | 🧠 |
| Lower face height | sn–gn | 70–75 | 63–67 | 4–5 | 6% | 🧠 |
| Intercanthal width | en–en | 33.3 | 31.8 | 2.7 / 2.3 | 7–8% | 🧠 (Kosovo [4] within 1 mm) |
| Biocular width | ex–ex | 88–92 | 85–89 | 3.6 / 4.0 | 4% | 🧠 mean; SD 📄 [13] |
| Eye fissure length | ex–en | 30–32 | 29–31 | 1–1.5 | 4% | 🧠 |
| Eye fissure height | ps–pi | 9.5–11 | 9.5–11 | ~1 | 10% | 🧠 |
| Interpupillary (far gaze) | p–p | 63–66 | 60–63 | 3–3.5 | 5% | 🧠 (Dodgson) |
| Nose height | n–sn | 53–56 | 49–52 | 3.3 / 3.1 | 6% | 🧠 |
| Nasal bridge length | n–prn | 47–53 | 43–48 | 3–4 | 7% | 🧠 |
| Nose width | al–al | 34.9 | 31.4 | 2.1 / 2.0 | 6% | 🧠 (consistent with [8]) |
| Nasal tip protrusion | sn–prn | 18–22 | 17–20 | ~2 | 10% | 🧠 |
| Mouth width | ch–ch | 51–55 | 48–52 | 3–3.5 | 6% | 🧠 |
| Philtrum width | cph–cph | 10–13 | 9–12 | 1.5–2 | 15% | 🧠 |
| Upper lip height | sn–sto | 21–24 | 19–21 | ~2 | 9% | 🧠 |
| Upper vermilion height | ls–sto | 8–10 | 7.5–9 | ~1.5 | 15–20% | 🧠 |
| Lower vermilion height | sto–li | 9.5–11 | 9–10.5 | ~1.5 | 15% | 🧠 |
| Lower lip + chin height | sto–gn | 48–52 | 43–46 | 3–4 | 7% | 🧠 |
| Ear length | sa–sba | 60–65 | 56–61 | ~3.5 | 6% | 🧠 ↔️ (other populations 57.6–62.9, see `anatomy/ear.md`) |
| Ear width | pra–pa | 32–36 | 30–33 | 2–2.5 | 7% | 🧠 ↔️ |

**Table 2: Harvested population values (mm, mean ± SD).**

| Population / method | n | Measure | Male | Female | Src | Status |
|---|---|---|---|---|---|---|
| Kosovo Albanian adults, direct | not captured | n–gn | 125.82 ± 6.37 | 115.53 ± 5.00 | [4] | 📄 |
| Kosovo Albanian adults, direct | not captured | en–en | 32.49 ± 2.59 | 31.78 ± 2.25 (p = 0.039) | [4] | 📄 |
| Indian medical students (BHU) | 200 (104 M / 96 F) | n–gn | 121.64 ± 6.47 | 113.63 ± 4.61 | [7] | 📄 |
| Adults 19–42 (asymmetry study) | 297 (150 M / 147 F) | right al–midline | 17.34 | 15.39 | [8] | 📄 |
| Hong Kong Chinese young adults, 3D | not captured | en–en | 40.61 | 38.27 | [11] | 📄 ↔️ |
| Malay adults, 3D | not captured | en–en | 35.74 | 35.03 | [12] | 📄 |
| Malay adults, 3D | not captured | nose width | 39.59 | 36.67 | [12] | 📄 ↔️ |
| Southern Spain, 3D, normal occlusion | not captured | ch–ch/en–en | 1.59 | 1.52 | [9] | 📄 |
| Southern Spain, 3D | not captured | en–en/al–al | 0.89 | 1.01 | [9] | 📄 |
| 3D normotypes (labels unclear) | not captured | en–en, mean ± 2 SD range | 20–41 / 21–39 | (37.0, 28.9 in a sex table) | [10] | 📄 ↔️ |

**Table 3: Norm sources and datasets.**

| Source | Method | Size / ages | Population | Access | Status |
|---|---|---|---|---|---|
| Farkas 1994 | calipers, tape | 2,326; 1–25 y | NAW (Toronto) | book | 📄 [3] |
| Farkas et al. 2005 international | calipers | ~1,470; ~18–30 y | ~25 populations | paper | 🧠 |
| Fang et al. 2011 review | pooled | 2,359; 27 groups | multi-ethnic | paper | 📄 [5] |
| 3DFN (FaceBase) | 3dMD stereophotogrammetry | 2,454; 3–40 y | European-ancestry US (🧠) | summary open; individual by DAR | ✅ [1][2] |
| NIOSH respirator survey | calipers + 3D subset | ~4,000 adults | US workforce, multi-ethnic | report and paper | 🧠 |
| ANSUR II | calipers, tape, 3D | public release 4,082 M + 1,986 F (full survey reported as 7,435 M / 3,922 F) [21] | US Army | public summary data | 📄 [21] ↔️ |
| Headspace / LYHM | 3dMD full head, capped | ~1,500; children to elderly | UK | research licence | 🧠 |
| SizeChina | 3D head scans | ~2,000 adults | Chinese | commercial | 🧠 |

**Table 4: Proportion checks (scale-free; NAW midpoints).** σ_log is the suggested prior SD of log(ratio) within one population.

| Ratio | M | F | σ_log | Status |
|---|---|---|---|---|
| en–en / ex–ex | 0.37 | 0.365 | 0.07 | 🧠 |
| ex–en / en–en | 0.94 | 0.97 | 0.08 | 🧠 |
| al–al / en–en | 1.05–1.12 | ~1.0 | 0.08 | 📄 [9] + 🧠 |
| ch–ch / en–en | 1.59 | 1.52–1.57 | 0.07 | 📄 [9] + 🧠 |
| ch–ch / al–al | ~1.52 | ~1.59 | 0.07 | 🧠 |
| ch–ch / interpupillary | ~0.83 | ~0.82 | 0.06 | 🧠 |
| n–gn / zy–zy (facial index) | ~0.88 | ~0.86 | 0.05 | 🧠 |
| zy–zy / eu–eu | ~0.91 | ~0.90 | 0.04 | 🧠 |
| go–go / zy–zy (caliper) | ~0.71 | ~0.70 | 0.06 | 🧠 |
| sn–sto / sn–gn | ~0.31 | ~0.31 | 0.07 | 🧠 |
| n–sn / n–gn | ~0.45 | ~0.45 | 0.05 | 🧠 |
| al–al / n–sn (nasal index) | ~0.64 | ~0.62 | 0.08 | 🧠 |
| sn–prn / n–sn | ~0.36 | ~0.37 | 0.10 | 🧠 |
| eu–eu / g–op (cephalic index) | 0.75–0.80 | 0.75–0.80 | 0.04 | 🧠 |
| sa–sba / n–sn | ~1.13 | ~1.15 | 0.07 | 🧠 |

**Table 5: Approximate population shifts vs NAW (mm or index; direction reliable, magnitude rough).**

| Population | en–en | al–al | zy–zy | sn–prn | Lips | Head | Status |
|---|---|---|---|---|---|---|---|
| East Asian | +2 to +6 (epicanthus inflates visible en) | +3 to +6 | +3 to +8 | −2 to −4 | similar to slightly fuller | cephalic index 80–88 | 🧠 ↔️ |
| Southeast Asian | +2 to +4 | +4 to +6 | +2 to +6 | −2 to −4 | fuller | brachycephalic tendency | 🧠 ↔️ ([12] consistent) |
| African / African American | +1 to +4 | +6 to +10 | 0 to +5 | −1 to −3 | vermilion +2 to +4 each | often dolichocephalic | 🧠 ↔️ |

**Table 6: Systematic offsets and drifts.**

| Effect | Size | Status |
|---|---|---|
| Direct vs 3D, most measures | < 2 mm [16]; max mean difference 0.21 mm (3D), 0.30 mm (2D) in one study, snippet [14] | 📄 |
| CT vs 3dMD, Go–Go | +2.34 mm on CT [15] | 📄 |
| Photo silhouette jaw width vs caliper go–go | silhouette larger by masseter + fat, roughly 10–30 mm | 🧠 |
| Hair at eu, op, v, tr in photos | +5 to +20 mm or more | 🧠 |
| al–al/zy–zy inflated by camera distance | ~8–10% at 0.4 m, ~2% at 1.5 m | 🧠 |
| Ear length, adult drift | ~0.1–0.25 mm/yr (see `anatomy/ear.md`) | 🧠 |
| Upper lip vs vermilion, age 25→70 | sn–sto +1 to +3 mm; ls–sto −1 to −3 mm | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Pick and record the reference row.** Store `norm_population`, `sex`, `age` and `norm_source` as custom properties on the head object. Never fall back silently to NAW 🧠. For a mixed-ancestry subject, use the widest plausible band.
2. **Measure the person directly if you can (with consent).** A 150 mm digital caliper on en–en, ex–ex, al–al and ch–ch (lips relaxed) plus a tape for head circumference takes five minutes. One caliper distance (error about 0.5 mm) fixes scale better than any prior (CV 3–8%) 🧠.
3. **Work in real units.** Use metric with length displayed in millimetres, and keep 1 BU = 1 m so the head is about 0.23 m tall. Measure 3D chords between vertices with the Measure tool snapped to vertices, or the Edit-mode *Edge Length* overlay on a temporary edge. Screen distances are not chords 🧠.
4. **Run a norm gauge after every major fitting stage.** Compute each Table 1 measure from landmark empties and show its z-score:
   - |z| < 2: fine.
   - 2–3: re-check that landmark and the camera.
   - > 3: almost always a landmark, focal-length or definition error rather than anatomy. Fix the cause; do not sculpt toward the mean 🧠.
5. **Quick sculpt checks** (NAW averages): alae roughly below the inner canthi (al–al ≈ en–en); mouth corners near the medial limbus, not the pupils (ch–ch ≈ 52 < interpupillary ≈ 63); eye fissure ≈ one third of ex–ex, with ex about 10–13 mm behind en (derived below); zy–zy ≈ 0.9 × head breadth; ear 5–10 mm longer than the nose; head length 190–200 mm, since a cranium too short behind the ears is the commonest blocking error 🧠.
6. **What goes wrong:** comparing caliper go–go (bone, about 97 mm) with the jaw silhouette; measuring eu or op through hair; taking nose and lips from a 40 cm selfie (perspective inflates the central face); reading the epicanthal fold as en; using cephalometric gnathion where Farkas's gn is the lowest chin point; NAW means for non-European subjects; a smile moving ch, sto and the vermilion. Most damaging: averaging toward the norm, which erases the deviations that make the likeness 🧠.

## Algorithmic implications

- **Schema.** Store each norm as `NormRecord{id, a, b, distance: chord|proj_x|proj_y|proj_z|arc, frame: FH|camera, method: caliper|3d_surface|photo2d|ct, landmark_variant, population, sex, age_band, n, mean, sd, source_ids, status}`. Compare a model measurement with a norm only when `distance`, `method` and `landmark_variant` match, or after an explicit offset (Table 6) 🧠.
- **Priors in log space:** log d ~ N(log μ, (k·CV)²). k = 1 when population, sex and method match; k = 1.5 with unknown population for low-variance measures (zy–zy, head length and breadth, n–gn); a population mixture or k ≈ 2.5 for al–al and en–en with unknown population; ×1.2 on everything by default for Farkas-to-3D method and era drift [3] 🧠.
- **Correlations.** Widths correlate with widths and heights with heights (r ≈ 0.3–0.7) 🧠. Independent Gaussians on dozens of measures over-regularise. Prefer a multivariate prior (a 3D morphable model's scale-normalised shape covariance, recentred on the chosen norm row), or divide prior weight by the effective number of independent terms.
- **Weighting.** With landmarks seen in two or more pose-solved views, cap the prior at about 10–20% of the objective. Let it dominate only where nothing is observed: prn, sn and pg′ depth with no profile, g–op and the occiput with no rear view 🧠.
- **Scale.** Use a global scale s ~ N(1, 0.035) from zy–zy or head breadth (the CVs). Combine it with the iris prior (11.7 ± 0.5 mm) or an interpupillary prior (63 ± 3.5 mm). Any caliper value overrides all of these 🧠.
- **Chord consistency.** Given en–en, ex–ex and ex–en chords, the depth of ex behind en is sqrt(ex–en² − ((ex–ex − en–en)/2)² − Δy²). With NAW means, sqrt(31.3² − 28.5² − 2.5²) ≈ 12.7 mm: such chord constraints recover depth from frontal-only data 🧠.
- **Gates.** Flag |z| > 3 as a probable error. Check perspective by refitting focal length when al–al/zy–zy or prn magnification is above the population upper bound 🧠.
- **Adult age terms.** Add linear drift for ear length (about +0.2 mm/yr), sn–sto (+), ls–sto (−) and n–prn (+), centred at age 25 🧠.

## Disagreements, myths & open questions

- **Farkas vs 3DFN** differ considerably, cause uncertain (method, secular trend, ethnic mix) [3] 📄; direct-vs-3D agreement under 2 mm [16] suggests method alone does not explain it ↔️.
- **Kolar's critique** is cited but unread [1].
- **Intercanthal width** spans 32–41 mm across samples [4][11][12] ↔️. The causes mix population, epicanthal folds and 3D placement of en.
- **Malay nose width** [12]: is it a real population difference or a different definition? ↔️
- **The normotype paper's labels** for 37.0 and 28.9 mm are unclear [10] ↔️.
- **Neoclassical canons** (equal thirds; eye width = intercanthal width = nose width; mouth = 1.5 × nose) held only in a minority of young adults in Farkas's 1985 revision 🧠. NAW means sit near several of them: fine as average checks, wrong as constraints.
- **Myth: the golden ratio defines beauty or averageness.** Average-face ratios do not cluster at 1.618, and the Marquardt mask fits many populations poorly 🧠 ↔️.
- **Myth: mouth corners align with the pupils.** On the means they align with the medial limbus 🧠.
- **Open questions:** full Farkas 1994 adult tables with per-cell n; 3DFN adult means by measurement (summary data in `data/anthropometric-norms.json` should replace Table 1 once pulled); sample sizes for [4][11][12]; the secular trend since the 1970s; whether Headspace-derived norms exist; ear-width norms (Farkas vs other populations ↔️).
- **Time-sensitive:** FaceBase access terms, the Headspace licence and ANSUR II public-data availability.

## Sources

[1] The 3D Facial Norms Database: Part 1. A Web-Based Craniofacial Anthropometric and Image Repository for the Clinical and Research Community — https://pmc.ncbi.nlm.nih.gov/articles/PMC4841760 — paper — 2015
[2] FaceBase 3D Facial Norms Database — https://facebase.org/facial_norms/ — official-docs — n.d.
[3] Weinberg et al., 3D stereophotogrammetry versus traditional craniofacial anthropometry: Comparing measurements from the 3D facial norms database to Farkas's North American norms (Am J Orthod Dentofacial Orthop 2019;155(5):693-701) — https://pmc.ncbi.nlm.nih.gov/articles/PMC6571015 — paper — 2019
[4] Facial Anthropometric Norms among Kosovo-Albanian Adults — https://pmc.ncbi.nlm.nih.gov/articles/PMC5708327/ — paper — 2017
[5] A Systematic Review of Inter-ethnic Variability in Facial Dimensions — https://pmc.ncbi.nlm.nih.gov/articles/PMC3074358/ — paper — 2011
[6] Wen et al., Bayesian meta-analysis of photogrammetric inter-ethnic facial variation (title not captured) — https://pmc.ncbi.nlm.nih.gov/articles/PMC4527668/ — paper — 2015
[7] An Anthropometric Study of the Facial Index Among Undergraduate Medical Students, BHU, Uttar Pradesh — https://pmc.ncbi.nlm.nih.gov/articles/PMC13399996 — paper — n.d.
[8] Evaluation of Facial Asymmetry Determined by Linear Measurements According to Hand Preference and Gender — https://pmc.ncbi.nlm.nih.gov/articles/PMC12500730/ — paper — n.d.
[9] Three-dimensional photographic analysis of the face in European adults from southern Spain with normal occlusion: reference anthropometric measurements — https://pmc.ncbi.nlm.nih.gov/articles/PMC6714104 — paper — n.d.
[10] 3D Facial Normotypes for Maxillofacial Surgical Planning — https://pmc.ncbi.nlm.nih.gov/articles/PMC13666107 — paper — n.d.
[11] Normative Findings for Periocular Anthropometric Measurements among Chinese Young Adults in Hong Kong — https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3730197/ — paper — n.d.
[12] Anthropometric Study of Three-Dimensional Facial Morphology in Malay Adults — https://pmc.ncbi.nlm.nih.gov/articles/PMC5051712/ — paper — n.d.
[13] Exploring Causes of Demographic Variations In Face Recognition Accuracy (reproduces Farkas SDs) — https://arxiv.org/pdf/2304.07175 — paper — 2023
[14] Accuracy and reliability of 3D stereophotogrammetry: a comparison to direct anthropometry and 2D photogrammetry — https://pubmed.ncbi.nlm.nih.gov/26267357 — paper — 2015
[15] Three-Dimensional Anthropometric Facial Analysis and Fitting Discrepancies Between Stereophotogrammetry and CT — https://pubmed.ncbi.nlm.nih.gov/38896864 — paper — 2024
[16] Reproducibility and Accuracy of Facial Soft Tissue Landmarks Across 3D Face Scanning Modalities: Systematic Review — https://pmc.ncbi.nlm.nih.gov/articles/PMC13180338/ — paper — n.d.
[17] Greek facial anthropometry study, comparison table with North American Caucasian values (morphological face height 121.3 / 111.8) — https://pmc.ncbi.nlm.nih.gov/articles/PMC3485457/table/Tab2 — paper — n.d.
[18] University of Pittsburgh dental school, 3D Facial Norms project page (Caucasian, age 3–40) — https://www.dental.pitt.edu/node/1547 — official-docs — n.d.
[19] Farkas et al., International anthropometric study of facial morphology in various ethnic groups/races (J Craniofac Surg 2005) — https://avesis.omu.edu.tr/yayin/8ae669cb-3f4f-4b93-bcf5-b3193aeefce1/international-anthropometric-study-of-facial-morphology-in-various-ethnic-groups-races — paper (record) — 2005
[20] Farkas et al. 2005 abstract record (14 measurements; nose very/extremely wide in Asian and Black groups vs NAW) — https://acikerisim.omu.edu.tr/entities/publication/faa15b82-bd5a-4e41-b1a1-b11d0ae6a11e — paper (record) — 2005
[21] Penn State OpenLab ANSUR II page (public data 4,082 M / 1,986 F; 2012 survey report NATICK/TR-15/007, DTIC) — https://www.openlab.psu.edu/ansur2/ ; https://apps.dtic.mil/sti/pdfs/ADA611869.pdf — official-docs — 2014

**Further reading (by name, not yet linked)**
- Farkas LG, *Anthropometry of the Head and Face*, 2nd ed., Raven Press, 1994 (1st ed. 1981).
- Farkas LG, Munro IR (eds), *Anthropometric Facial Proportions in Medicine*, 1987.
- Farkas LG, Hreczko TA, Kolar JC, Munro IR, "Vertical and horizontal proportions of the face in young adult North American Caucasians: revision of neoclassical canons", *Plast Reconstr Surg*, 1985.
- Farkas LG, Katic MJ, Forrest CR et al., "International anthropometric study of facial morphology in various ethnic groups/races", *J Craniofac Surg*, 2005.
- Kolar JC, Salter EM, *Craniofacial Anthropometry: Practical Measurement of the Head and Face for Clinical, Surgical, and Research Use*, 1997.
- Martin R, Saller K, *Lehrbuch der Anthropologie*, 1957.
- Zhuang Z, Bradtmiller B, "Head-and-face anthropometric survey of U.S. respirator users", *J Occup Environ Hyg*, 2005.
- Gordon CC et al., *2012 Anthropometric Survey of U.S. Army Personnel (ANSUR II): Methods and Summary Statistics*, 2014.
- Ball R et al., "A comparison between Chinese and Caucasian head shapes", *Applied Ergonomics*, 2010.
- Dai H, Pears N, Smith W, Duncan C, "A 3D morphable model of craniofacial shape and texture variation" (Liverpool-York Head Model, Headspace), ICCV 2017.
- Dodgson NA, "Variation and extrema of human interpupillary distance", Proc. SPIE, 2004.
- Porter JP, Olson KL, "Anthropometric facial analysis of the African American woman", *Arch Facial Plast Surg*, 2001.
- Aldridge K et al., "Precision and error of three-dimensional phenotypic measures acquired from 3dMD photogrammetric images", *Am J Med Genet A*, 2005.
- Heike CL et al., "3D digital stereophotogrammetry: a practical guide to facial image acquisition", *Head Face Med*, 2010.

## Verification log (2026-11-20)

No claim list was supplied with the task, so the most load-bearing, searchable claims were chosen. 3 of 4 searches used.

- Farkas NAW face height n–gn means 121.3 (M) / 111.8 (F): confirmed (one source; mapping of "morphological face height" to n–gn is the source's label). https://pmc.ncbi.nlm.nih.gov/articles/PMC3485457/table/Tab2
- Farkas 2005 international study (about 14 measurements, ~1,470 subjects, ~25 populations): study exists and reports wider noses in Asian and Black groups; the numbers are unconfirmed (left 🧠). https://avesis.omu.edu.tr/yayin/8ae669cb-3f4f-4b93-bcf5-b3193aeefce1/international-anthropometric-study-of-facial-morphology-in-various-ethnic-groups-races
- 3DFN 2,454 participants aged 3–40, cross-sectional, 3dMD, vs Farkas N = 2,326: confirmed (already ✅). https://pmc.ncbi.nlm.nih.gov/articles/PMC6571015
- 3DFN "European ancestry": corrected in wording to "Caucasian" (source wording); recruiting sites contested (three vs four). https://www.dental.pitt.edu/node/1547 , https://facebase.org/facial_norms/
- All other claims: not checked, left 🧠.

## Verification log (2026-11-20, second pass)

4 of 4 searches used.

- Farkas 1994 NAW means/SDs (en–en 33.3±2.7/31.8±2.3, al–al 34.9±2.1/31.4±2.0, n–gn, ex–ex, ch–ch): unconfirmed; the search returned only the 1985 Farkas canons paper (153 young adult NAW) and secondary papers without the figures. Left 🧠/📄 as before. https://pubmed.ncbi.nlm.nih.gov/3883374/
- 3DFN differs from Farkas per measurement; 1.2 inflation factor: unconfirmed. Only the paper's title was confirmed (now in [3]); no per-measurement results found. https://pmc.ncbi.nlm.nih.gov/articles/PMC4841760/
- Farkas 2005 international study: 14 measurements confirmed (📄); ~1,470 subjects and ~25 populations unconfirmed (🧠); nose very/extremely wider in Asian and Black groups vs NAW confirmed qualitatively, Middle Eastern nose width equal to NAW. Table 5 magnitudes (+2 to +6 etc.) unconfirmed, left 🧠 ↔️. https://acikerisim.omu.edu.tr/entities/publication/faa15b82-bd5a-4e41-b1a1-b11d0ae6a11e
- ANSUR II sample size: contested. Public release is 4,082 M / 1,986 F; the full survey report (NATICK/TR-15/007) cites 7,435 M / 3,922 F. https://www.openlab.psu.edu/ansur2/ , https://apps.dtic.mil/sti/pdfs/ADA611869.pdf
- Head length/breadth means and CV (g–op, eu–eu): unconfirmed; ANSUR means not retrievable from search results. Left 🧠.
