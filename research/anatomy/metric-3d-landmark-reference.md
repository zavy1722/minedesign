# Metric 3D mean landmark configuration and covariance

> No source in this library gives a complete mean 3D soft-tissue landmark configuration in a Frankfort-horizontal (FH) frame, so this note synthesises one: 44 landmarks for young European-ancestry adults by sex, origin at mid-tragion, built to reproduce sourced and recalled chord norms (n–me′ 121.3 / 111.8 mm [5], its SDs [6], head size, ear length, IPD), with an 18-factor covariance and a synthetic-subject recipe. The most consequential number is profile depth: pronasale lies about 119 mm (M) / 111 mm (F) in front of tragion along FH (plausible 108–130 / 100–122), deeper than the 100 mm working value in the library's camera notes. The alar crest sits about 29 / 27 mm, endocanthion 42 / 39, exocanthion 52 / 49 and soft zygion 92 / 86 mm behind the tip; implied tragion chords are t–n′ ≈ 121 / 113, t–sn ≈ 129 / 121 and t–gn′ ≈ 150 / 139 mm. Treat every coordinate as a calibrated expert prior until replaced by values computed from FLAME 2023 Open [17][18], 3DFN summary landmarks [1][2] or the ANSUR II CSV [4]; `data/metric-3d-landmark-reference.json` holds every number.
>
> Evidence status: 4 ✅ / 17 📄 / 94 🧠 / 21 ↔️ — 🧠 items are queued for web verification.

## Key facts

This topic's own harvest and earlier draft were absent. The URLs cited here were harvested and partly verified for sibling notes (`anatomy/anthropometric-norms.md`, `anatomy/craniometric-landmarks.md`, `anatomy/nose.md`, `reconstruction/flame-model.md`, `reconstruction/landmark-detection.md`).

**Sources and what each can give**
- **3D Facial Norms (3DFN):** 2,454 people aged 3–40 (952 M, 1,502 F), one 3dMD capture each [1][2] ✅. Summary-level landmarks, measurements and demographics download freely; individual data need a Data Access Request [2] 📄. It reports 34 inter-landmark measurements [1] 📄. It is the best route to empirical mean coordinates by age band and sex, but adds little ancestry diversity (European-ancestry participants) 🧠.
- **3DFN vs Farkas.** The two differ considerably; the authors point to method, secular trend and ethnic mix [3] 📄. Direct calipers and 3D surfaces agree within about 2 mm for most chords [10][12] ✅. CT reads Go–Go 2.34 mm wider than 3dMD [11] 📄.
- **ANSUR II** public release: 4,082 men and 1,986 women [4] 📄; the survey report cites 7,435 / 3,922 [4] ↔️.
  - Its head columns give size marginals and their correlations by sex and race, but no profile depth 🧠 (Table 5).
  - Menton–sellion is measured to the deepest nasal-root point, not to Farkas's palpated nasion 🧠.
- **Face-height anchor.** For North American White young adults, Farkas n–gn is 121.3 (M) / 111.8 (F) mm [5] 📄, with SD 6.8 / 5.2 [6] 📄. Kosovo-Albanian adults measure 125.8 ± 6.4 / 115.5 ± 5.0 [7] 📄. Adult means therefore run about 120–126 / 112–116 mm [5][7] ✅.
- **Definitions.**
  - FH is the porion–orbitale plane [13] 📄; living anthropometry substitutes tragion and soft-tissue orbitale, as this frame does 🧠.
  - Pronasale is the most anterior midline point of the nasal tip [14] 📄.
  - "Soft-tissue gnathion" means the lowest chin point in some schemes and the anterior-inferior point in others [14] ↔️. This file calls the lowest point me′ (Farkas's "gn") and the anterior-inferior point gn′.
- **Nasion soft tissue** is about 6 mm thick (pooled) [15], rising from 5.6 to 8.3 mm across BMI groups [16] ✅; used below to carry skull-based depths to the skin.
- **FLAME 2023 Open** is CC BY 4.0, while the other FLAME releases are non-commercial [17][18] 📄. Its training data and component counts are not yet established 🧠.
  - FLAME's axes (metres, +X = subject's left, +Y up, face toward +Z) match this frame; only the origin and FH tilt differ 🧠.
  - A correctly scaled average FLAME scores 1.53 mm mean NoW error, down from 1.92 mm before scale optimisation [21] 📄. A mean-shape prior is therefore a strong start, but it carries no likeness.
- **MediaPipe.** Face Landmarker returns 478 landmarks [20] 📄. Its z is relative, scaled like x, under an assumed virtual camera [19] 📄. The canonical mesh covers forehead to chin, with no ears, tragion or occiput, so it can neither define FH nor supply profile depths 🧠.

**The synthesised configuration** (Tables 1–4; data file)
- **Frame:** origin at the tragion midpoint; +x = subject's left; FH through both tragia and the mid-orbitale point; +y up; +z forward. The axes match `face3d/synthetic.py` 🧠.
- **Vertical anchors (M / F):** canthi 13–16 / 12–15 mm above FH; n′ +21 / +19; sn −32.5 / −31; me′ −100 / −92; vertex +130 / +126 (ANSUR-type tragion–top of head) 🧠.
- **Depth anchors.** Four independent routes agree within about ±8 mm 🧠:
  - n′ lies about 12 mm ahead of the corneal plane (`anatomy/nose.md`).
  - Spectacle temples (about 95–105 mm from hinge to bend) put the cornea about 80–90 mm in front of the ear root.
  - The cephalometric porion–nasion horizontal is about 90–100 mm, plus about 6 mm of soft tissue at nasion [15].
  - Tragion lies near mid-length of g–op (197 / 187 mm).
  - Result: n′ sits 94 / 88 mm and prn 119 / 111 mm in front of tragion.
- **Profile sanity checks (M / F)** 🧠:
  - nasofrontal angle 127° / 134°;
  - facial convexity g′–sn–pg′ 10° / 11° (Legan–Burstone 12 ± 4°);
  - soft-tissue facial angle ≈ 90.5° (Holdaway 90–92°);
  - E-line: upper lip −5 / −4.5 mm, lower lip about −0.5 mm;
  - mentolabial sulcus about 5 mm; n–prn 49 / 45 mm; sn–prn 20 / 19 mm.
  - Pg′ sits 7 / 6 mm behind a true vertical through sn, versus −3.5 / −2.6 in Arnett's natural-head-position series ↔️.
- **Covariance.** 18 named integration factors, plus a residual split into a mirror-symmetric part and an independent per-side part (asymmetry) 🧠.
  - Factors: size, lower-face height, facial depth, mandibular projection, face width, nasal projection and width, interorbital spacing, lips, mouth width, cephalic index, brow, upper-face height, ear length and protrusion, soft tissue, eye opening, vault height.
  - Factor SDs were fitted by non-negative least squares, so the implied chord SDs reproduce the recalled norms within ±0.5 mm. The exceptions are ex–ex and IPD (model 0.3–0.9 mm low) and g–op (0.9 mm high) 🧠.
- **Implied correlations (male):** zy–zy with go–go 0.81 and with eu–eu 0.69; n–me′ with n–sn 0.83 and with sn–me′ 0.86; n–sn with sn–me′ 0.45; en–en 0.65 with ex–ex but only 0.15–0.25 with other widths 🧠. Published width–width correlations usually sit at r ≈ 0.3–0.6, so the face-width couplings here are probably too strong ↔️.

## Numbers & reference tables

**Table 1 — Mean landmark coordinates, FH head frame, mm** (young European-ancestry adults; bilateral rows give the left side, so mirror x for the right; SD = √diag of the factor covariance)

| Landmark | Male x, y, z | SD x/y/z | Female x, y, z | SD x/y/z | Status |
|---|---|---|---|---|---|
| v vertex | 0, 130, 0 | 2/5.6/12 | 0, 126, 0 | 2/5.5/12 | 🧠 |
| tr trichion | 0, 80, 86 | 1/8.6/5 | 0, 76, 81 | 1/8.6/5 | 🧠 |
| g′ glabella | 0, 33, 99 | 0.8/4.3/5.2 | 0, 30, 91 | 0.8/4.3/4.8 | 🧠 |
| n′ nasion | 0, 21, 94 | 0.6/2.5/4.7 | 0, 19, 88 | 0.6/2.4/4.5 | 🧠 |
| prn | 0, −21.5, 119 | 0.8/2.3/5.9 | 0, −20, 111 | 0.8/2.0/5.5 | 🧠 ↔️ |
| sn | 0, −32.5, 102 | 0.6/2.6/5 | 0, −31, 95 | 0.6/2.1/4.7 | 🧠 |
| ls | 0, −46, 105 | 0.6/3.1/5.2 | 0, −43.5, 98 | 0.6/2.4/4.8 | 🧠 |
| sto | 0, −54.5, 101.5 | 0.6/3.4/5 | 0, −51, 95 | 0.6/2.7/4.7 | 🧠 |
| li | 0, −64.5, 103 | 0.6/3.9/5.3 | 0, −60.5, 96 | 0.6/3.1/5 | 🧠 |
| sl (B′) | 0, −75, 94 | 0.6/4.7/5.3 | 0, −69.5, 89 | 0.6/3.8/5 | 🧠 |
| pg′ | 0, −88, 95 | 0.8/5.3/5.5 | 0, −80.5, 89 | 0.8/4.2/5.1 | 🧠 |
| gn′ | 0, −96, 90 | 0.8/5.5/5.3 | 0, −87.5, 84 | 0.8/4.3/4.9 | 🧠 |
| me′ (Farkas gn) | 0, −100, 82 | 1/5.9/5.7 | 0, −92, 77 | 1/4.7/5.3 | 📄 n–me′ [5]; 🧠 |
| op | 0, 40, −98 | 1.5/10/3.8 | 0, 38, −96 | 1.5/10/3.8 | 🧠 |
| t tragion | 72.5, 0, 0 | 2.5/0/0 | 68.5, 0, 0 | 2.3/0/0 | 🧠 |
| or′ orbitale | 33, 0, 78 | 1.6/1/4 | 31.5, 0, 73 | 1.5/1/3.8 | 🧠 |
| p pupil (corneal apex) | 32, 14, 82 | 1.5/1.1/4 | 31, 13, 77 | 1.4/1.1/3.8 | 🧠 |
| en | 16.5, 13, 77 | 1.4/1.1/3.8 | 16, 12, 72 | 1.3/1.1/3.6 | 🧠 |
| ex | 45, 16, 67 | 1.7/1.3/3.5 | 43.5, 15, 62.5 | 1.7/1.3/3.3 | 🧠 |
| ps | 31, 18.5, 80.5 | 1.4/1.1/4 | 30, 17.5, 75.5 | 1.3/1.1/3.7 | 🧠 |
| pi | 32, 9, 79.5 | 1.4/1/3.9 | 31, 8, 74.5 | 1.3/0.9/3.7 | 🧠 |
| al | 17.5, −27.5, 96 | 1.2/2.4/4.8 | 15.7, −26, 89.5 | 1.1/1.9/4.6 | 🧠 |
| ac (alar crest) | 15, −30.5, 90 | 1.1/2.5/4.5 | 13.5, −29, 84 | 1/2/4.3 | 🧠 |
| ch | 26.5, −53.5, 86 | 1.7/3.5/4.4 | 25, −50, 81 | 1.6/2.7/4.2 | 🧠 |
| zy′ | 70.5, −3, 27 | 2.9/4/5.2 | 66, −3, 25 | 2.7/4/5.1 | 🧠 |
| go′ | 54, −64, 17 | 3.3/3.8/4.1 | 50, −58, 16 | 3.1/3.6/4.1 | 🧠 ↔️ |
| sa | 80, 29, −12 | 3.8/2.1/3 | 75.5, 27, −11 | 3.7/2/3 | 🧠 |
| sba | 76, −34, −3 | 3.1/2.2/3 | 72, −32, −3 | 3/2.1/3 | 🧠 |
| eu | 76, 68, −20 | 2.9/12/12 | 72.5, 63, −18 | 2.8/12/12 | 🧠 |

**Table 2 — Profile depths behind pronasale along FH (mm)**

| Point | Male (SD) | Female (SD) | Earlier library value | Status |
|---|---|---|---|---|
| alare | 23 (2.3) | 21.5 (2.3) | — | 🧠 |
| alar crest (alar base) | 29 (2.6) | 27 (2.5) | ~20 | 🧠 ↔️ |
| subnasale | 17 (2.1) | 16 (2.0) | — | 🧠 |
| soft nasion | 25 (2.3) | 23 (2.3) | — | 🧠 |
| corneal apex | 37 (2.6) | 34 (2.5) | — | 🧠 |
| endocanthion / exocanthion | 42 / 52 (2.8 / 3.3) | 39 / 48.5 | 35–45 ("eye corners") | 🧠 ↔️ |
| cheilion | 33 (2.7) | 30 (2.7) | — | 🧠 |
| cheek silhouette, frontal, alar level | 79 (9) | 73 (8.5) | 60–80 | 🧠 ↔️ |
| soft zygion / soft gonion | 92 / 102 | 86 / 95 | — | 🧠 |
| tragion | 119 (5.8; mean ±8) | 111 (5.5; mean ±8) | 90–120, nominal 100 | 🧠 ↔️ |
| opisthocranion | 217 | 207 | — | 🧠 |

**Table 3 — Tragion distances (mm; chord = 3D straight line; depth = forward along FH)**

| Measure | Male chord (SD) | Male depth | Female chord (SD) | Female depth | Status |
|---|---|---|---|---|---|
| t–n′ (upper face depth) | 120.6 (4.6) | 94 | 113.1 (4.4) | 88 | 🧠 ↔️ |
| t–sn (maxillary depth) | 129.3 (4.9) | 102 | 121.2 (4.6) | 95 | 🧠 ↔️ |
| t–prn | 141.0 (5.7) | 119 | 132.0 (5.4) | 111 | 🧠 ↔️ |
| t–gn′ / t–me′ (mandibular depth) | 150.2 / 148.3 | 90 / 82 | 139.3 / 138.1 | 84 / 77 | 🧠 ↔️ |
| t–en / t–ex | 96.1 / 74.2 | 77 / 67 | 89.9 / 69.0 | 72 / 62.5 | 🧠 |
| t–go′ | 68.8 (3.9) | 17 | 62.9 (3.7) | 16 | 🧠 |

**Table 4 — Model vs norm (mm, mean (SD))**

| Chord | Model M | Norm M | Model F | Norm F | Norm status |
|---|---|---|---|---|---|
| n–me′ | 121.6 (6.7) | 121.3 (6.8) | 111.5 (5.6) | 111.8 (5.2) | 📄 [5][6] |
| ex–ex | 90.0 (3.3) | 88–92 (3.6) | 87.0 (3.2) | 85–89 (4.0) | SD 📄 [6]; mean 🧠 |
| en–en | 33.0 (2.7) | 33.3 (2.7) | 32.0 (2.4) | 31.8 (2.3) | 🧠 |
| al–al | 35.0 (2.2) | 34.9 (2.1) | 31.4 (2.1) | 31.4 (2.0) | 🧠 |
| ch–ch | 53.0 (3.3) | 51–55 (3.3) | 50.0 (3.1) | 48–52 (3.0) | 🧠 |
| zy′–zy′ (skin) | 141 (5.6) | 139–145 | 132 (5.2) | 130–136 | 🧠 |
| eu–eu / g′–op | 152 / 197 | 149–158 / 194–202 | 145 / 187 | 141–151 / 184–193 | 🧠 |
| p–p (IPD) | 64.0 (3.0) | 64.5 (3.5) | 62.0 (2.7) | 62.0 (3.3) | 🧠 |
| sa–sba | 63.8 (3.7) | 62–65 | 59.6 (3.5) | 58–61 | 🧠 ↔️ |

**Table 5 — ANSUR II head columns to pull** (names and ranges recalled; compute from the CSV [4])

| Column | Maps to | M mean range | F mean range | Status |
|---|---|---|---|---|
| headlength / headbreadth | g′–op / eu–eu | 195–202 / 150–158 | 186–193 / 143–151 | 🧠 |
| bizygomaticbreadth | zy′–zy′ | 139–145 | 130–136 | 🧠 |
| mentonsellionlength | sellion–me′ | 120–126 | 111–117 | 🧠 |
| interpupillarybreadth | p–p | 63–66 | 60–63 | 🧠 (check unit scaling) |
| tragiontopofhead | v.y | 128–134 | 124–130 | 🧠 |
| earlength | sa–sba | 62–66 | 58–61 | 🧠 |
| bitragionchinarc | ≈ 2 × surface path t→pg′ | 320–335 | 300–315 | 🧠 |

**Table 6 — Perspective ratio (d + Δ)/d, nose tip vs a plane Δ behind it** (d = camera to tip)

| Δ (mm) | 0.3 m | 0.5 m | 1 m | 1.5 m | 3 m | Status |
|---|---|---|---|---|---|---|
| 100 (earlier library value) | 1.333 | 1.200 | 1.100 | 1.067 | 1.033 | 🧠 |
| 111 (female tragion) | 1.370 | 1.222 | 1.111 | 1.074 | 1.037 | 🧠 |
| 119 (male tragion) | 1.397 | 1.238 | 1.119 | 1.079 | 1.040 | 🧠 |
| 52 (male exocanthion) | 1.173 | 1.104 | 1.052 | 1.035 | 1.017 | 🧠 |

**Ancestry and age** (full tables in the data file; sourced population values for en–en and nose width [8][9] via `anatomy/anthropometric-norms.md`). East Asian means relative to European, same sex: en–en +3, al–al +4, zy–zy +6, head length −8, radix −4 and tip −5 mm in depth. African-descent means: al–al +8, lips 4 mm more protrusive and taller vermilion, sn +2, head length +6 🧠 ↔️. Per decade after 30: subaurale −1.2, pronasale −0.8, stomion −0.6, cheilion −0.5 and soft menton −0.5 mm vertically, while the cranium and canthal width stay stable 🧠.

## Applying this to photo→3D face sculpting in Blender

1. **Build the frame before sculpting.** Place empties on both tragia and both soft orbitale points from the pose-solved cameras, then compute FH (data table `head_frame_definition`). Parent the head to an empty at mid-tragion. In Blender, X = x, Y = −z, Z = y, with metres = mm × 0.001.
2. **Load the sex-matched prior as a ghost:** one small sphere empty per Table 1 point, scaled by the subject's metric anchor, In Front enabled. It is a reference cage, not a target; likeness lives in the deviations.
3. **Measure the one number this file is least sure of (with consent).** Measure the tragion-to-pronasale chord with a caliper (expect about 141 / 132 mm). Alternatively, take a true profile from at least 1.5 m with rulers at the ear and nose planes. The FH depth is √(chord² − t.x² − Δy²). This single measurement removes most of the depth uncertainty.
4. **Profile checks (Right Ortho, FH level).** Expect:
   - prn about 119 / 111 mm and n′ about 94 / 88 mm in front of tragion; ex about 67 / 62;
   - go′ only about 17 mm in front of tragion and about 60 mm below FH;
   - the earlobe bottom near subnasale height.
   - Ratios that survive scale: t→prn ≈ 0.60 × g′–op; t→n′ ≈ 0.48 × g′–op; op about 98 mm behind tragion 🧠.
5. **Frontal checks.** At 0.5 m the tip images about 1.24× larger than tragion-plane features and about 1.16× larger than the cheek silhouette (Table 6). Undo perspective before judging nose or face width.
6. **What goes wrong:**
   - ears set too far forward (tragion placed 90–100 mm behind a male tip);
   - a cranium too short behind the ears;
   - the jaw angle drawn at the earlobe;
   - a nose too shallow from frontal-only fits;
   - FH confused with the camera horizon: a 10° pitch error moves prn about 21 mm vertically relative to tragion;
   - the MediaPipe canonical face treated as metric;
   - skin go′ width compared with a caliper bigonial on bone 🧠.

## Algorithmic implications

- **Prior.** S = L Lᵀ + R, where L holds the 18 factors (σ × loading) and R is the residual covariance (data tables `factor_*`, `residual_sd`). Penalise ½ rᵀ(κ²S)⁻¹r on residuals in the FH frame, after similarity alignment (`face3d/geometry/procrustes.py`) or directly in mm when a metric anchor exists. S is 132 × 132, so precompute its Cholesky factor or use Woodbury on the low-rank form 🧠.
- **Inflation.** κ = 1 when sex and population match; κ = 1.5 when the population is unknown; κ = 2.5 on al/ac x and en x when ancestry is unknown. Until verified, add an extra facial-depth factor with σ = 6 mm (dz weight 1 on n′, g′, prn, sn, lips, pg′, gn′, me′) 🧠.
- **Weighting.** With two or more pose-solved views, cap the prior at 10–20% of the objective. Let it dominate only unobserved coordinates: prn, sn and pg′ depth with no profile; op, v and eu with no rear or top view 🧠.
- **Pose and scale.** Treat FH pitch as a latent with σ ≈ 5° relative to the photographed head posture. Global scale: σ_log 0.03 with no anchor, about 0.04 per iris (11.7 ± 0.5 mm), about 0.005 with one caliper chord 🧠.
- **Mixtures.** Use sex × ancestry components (log-sum-exp of component penalties) with the shift tables, plus a linear age drift; never infer ancestry from the photo to choose a component 🧠.
- **Synthetic subjects.** x = μ + shifts + L z + C e, with z ~ N(0, I₁₈), e ~ N(0, I), C Cᵀ = R; then rebuild the frame from the sampled t and or′. A 5,000-sample check gives en–en 33.0 ± 2.7, n–me′ 121.5 ± 6.8 and t→prn depth 118.9 ± 6.0 mm (M), with 0.7 mm mean canthal asymmetry. Use it to test depth recovery at camera distances of 0.3–3 m 🧠.
- **Replacement pipeline, in priority order** 🧠:
  1. FLAME 2023 Open: embed each landmark barycentrically, solve FH on the template, take the template landmarks as μ and Σ = B_L B_Lᵀ, since β ~ N(0, 1) per component. Its mean is mixed-sex.
  2. 3DFN summary landmarks by sex × age band; check whether tragion is included.
  3. ANSUR II: compute means, SDs and the 13 × 13 correlation matrix per Gender × DODRace, then refit the factor σ by the same NNLS calibration.
  4. Keep this file as the fallback and as a regression test: `model_vs_norm_chords` within 1 mm and 20% SD.

## Disagreements, myths & open questions

- **Tragion depth** behind pronasale: 100 mm (camera and nose notes) vs 119 / 111 mm here ↔️. Measuring it on the FLAME 2023 Open template settles the mean in minutes.
- **Farkas face depths** t–n, t–sn and t–gn are not in this library. The model predicts 121 / 129 / 150 mm (M); if the published values are about 10 mm smaller, the depth anchor is too deep ↔️.
- **Naming:** gn′ vs me′ [14] ↔️; sellion vs n′ (ANSUR menton–sellion vs Farkas n–gn) 🧠.
- **Bigonial width:** a caliper on bone reads 94–100 mm against skin go′ of about 108 mm, and ergonomic surveys differ again ↔️.
- **Datasets:** the ANSUR II sample size is contested [4] ↔️; 3DFN vs Farkas also disagree [3] (see above).
- **Myth: "the MediaPipe canonical face is a metric average head."** Its z is relative [19], and it has no ears or tragion 🧠.
- **Myth: "FH is horizontal in a photo."** Natural head posture departs from FH with a between-person SD of about 3–5° 🧠.
- **Myth: "FLAME's mean is a male European."** It is a mixed-sex mean of its training set: the CAESAR heads for 2017/2020, and unconfirmed for 2023 Open 🧠.
- **Open questions:** an empirical inter-landmark covariance (none in the library); ancestries beyond European, East Asian and African; ages over 40 (3DFN stops at 40); whether this model's face-width correlations are too high.
- **Time-sensitive:** FLAME 2023 Open terms and contents, FaceBase access rules, ANSUR II hosting.

## Sources

[1] The 3D Facial Norms Database: Part 1. A Web-Based Craniofacial Anthropometric and Image Repository for the Clinical and Research Community — https://pmc.ncbi.nlm.nih.gov/articles/PMC4841760 — paper — 2015
[2] FaceBase 3D Facial Norms Database — https://facebase.org/facial_norms/ — official-docs — n.d.
[3] Weinberg et al., 3D stereophotogrammetry versus traditional craniofacial anthropometry: 3DFN vs Farkas's North American norms — https://pmc.ncbi.nlm.nih.gov/articles/PMC6571015 — paper — 2019
[4] Penn State OpenLab ANSUR II page (public data 4,082 M / 1,986 F; NATICK/TR-15/007) — https://www.openlab.psu.edu/ansur2/ — official-docs — 2014
[5] Greek facial anthropometry study, comparison table with North American Caucasian values (morphological face height 121.3 / 111.8) — https://pmc.ncbi.nlm.nih.gov/articles/PMC3485457/table/Tab2 — paper — n.d.
[6] Exploring Causes of Demographic Variations in Face Recognition Accuracy (reproduces Farkas SDs) — https://arxiv.org/pdf/2304.07175 — paper — 2023
[7] Facial Anthropometric Norms among Kosovo-Albanian Adults — https://pmc.ncbi.nlm.nih.gov/articles/PMC5708327/ — paper — 2017
[8] Normative Findings for Periocular Anthropometric Measurements among Chinese Young Adults in Hong Kong — https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3730197/ — paper — n.d.
[9] Anthropometric Study of Three-Dimensional Facial Morphology in Malay Adults — https://pmc.ncbi.nlm.nih.gov/articles/PMC5051712/ — paper — n.d.
[10] Accuracy and reliability of 3D stereophotogrammetry: a comparison to direct anthropometry and 2D photogrammetry — https://pubmed.ncbi.nlm.nih.gov/26267357 — paper — 2015
[11] Three-Dimensional Anthropometric Facial Analysis and Fitting Discrepancies Between Stereophotogrammetry and CT — https://pubmed.ncbi.nlm.nih.gov/38896864 — paper — 2024
[12] Reproducibility and Accuracy of Facial Soft Tissue Landmarks Across 3D Face Scanning Modalities: Systematic Review — https://pmc.ncbi.nlm.nih.gov/articles/PMC13180338/ — paper — n.d.
[13] Columbia anatomy craniology slides (landmark definitions; FH = porion–orbitale) — https://columbia.edu/itc/hs/medical/humanAnatomy/yuan/craniologyISlides_files/slide0061.html — other — n.d.
[14] Nobel Biocare: Definition of 3D cephalometric soft tissue landmarks — https://nobellicense.nobelbiocare.com/help/d3d046fb-52e8-4b33-9f51-d3fd98ca3ed4/2.0/EN/3D_cephalometric_soft_tissue_landmarks.htm — commercial docs — n.d.
[15] Global facial soft tissue thicknesses for craniofacial identification — https://pmc.ncbi.nlm.nih.gov/articles/PMC10861615/ — review — 2023
[16] Facial Soft Tissue Thickness of Midline in an Iranian Sample: MRI Study — https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5543663/ — paper — n.d.
[17] FLAME project site (FLAME 2023 Open, CC BY 4.0) — https://flame.is.tue.mpg.de/ — official-docs — n.d.
[18] FLAME model licence — https://flame.is.tue.mpg.de/modellicense.html — official-docs — n.d.
[19] MediaPipe 3D Face Transform (Google Developers Blog) — https://developers.googleblog.com/en/mediapipe-3d-face-transform/ — blog — n.d.
[20] Google AI Edge Face Landmarker documentation — https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker — official-docs — n.d.
[21] Towards Metrical Reconstruction of Human Faces (MICA) — https://arxiv.org/pdf/2204.06607 — paper — 2022

**Further reading (by name, not yet linked)**
- Farkas LG, *Anthropometry of the Head and Face*, 2nd ed., 1994.
- Gordon CC et al., *2012 Anthropometric Survey of U.S. Army Personnel (ANSUR II): Methods and Summary Statistics*, 2014.
- Zhuang Z, Bradtmiller B, "Head-and-face anthropometric survey of U.S. respirator users", *J Occup Environ Hyg*, 2005.
- Robinette KM et al., CAESAR (Civilian American and European Surface Anthropometry Resource) final report, early 2000s.
- Li T, Bolkart T, Black MJ, Li H, Romero J, "Learning a model of facial shape and expression from 4D scans" (FLAME), SIGGRAPH Asia 2017.
- Kartynnik Y et al., "Real-time facial surface geometry from monocular video on mobile GPUs", 2019.
- Arnett GW et al., "Soft tissue cephalometric analysis: diagnosis and treatment planning of dentofacial deformity", *Am J Orthod Dentofacial Orthop*, 1999.
- Legan HL, Burstone CJ, "Soft tissue cephalometric analysis for orthognathic surgery", *J Oral Surg*, 1980.
- Holdaway RA, "A soft-tissue cephalometric analysis and its use in orthodontic treatment planning", *Am J Orthod*, 1983.
- Dodgson NA, "Variation and extrema of human interpupillary distance", Proc. SPIE, 2004.
- Booth J et al., "Large Scale 3D Morphable Models" (LSFM), *IJCV*, 2018.
- Dai H, Pears N, Smith W, Duncan C, "A 3D morphable model of craniofacial shape and texture variation" (Liverpool-York Head Model), ICCV 2017.
- Ball R et al., "A comparison between Chinese and Caucasian head shapes", *Applied Ergonomics*, 2010.
