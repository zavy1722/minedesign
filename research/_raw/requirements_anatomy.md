# Engine requirements digest: face & head anatomy

Compiled 2026-11-20 from the 26 notes in `research/anatomy/`, with every verification-log correction applied. Audience: the team building the numpy-only fitting engine (`face3d`) and the Blender add-on. Human-facing summary: [`anatomy/README.md`](../anatomy/README.md).

**Badges.** ✅ verified (≥2 sources) · 📄 single source · 🧠 expert knowledge, unverified · ↔️ contested. Across the area, 1,555 of 2,865 badged claims are 🧠 and 514 are ↔️ (72%). **Every 🧠 value below is provisional: ship it as a named, tunable default with its badge in the data file, never as a constant.**

**Note codes:** AGE [aging-face](../anatomy/aging-face.md) · ANT [anthropometric-norms](../anatomy/anthropometric-norms.md) · ASY [facial-asymmetry](../anatomy/facial-asymmetry.md) · CAN [facial-proportions-canons](../anatomy/facial-proportions-canons.md) · CHI [child-growth](../anatomy/child-growth.md) · CRL [craniometric-landmarks](../anatomy/craniometric-landmarks.md) · EAR [ear](../anatomy/ear.md) · EYE [eye-region](../anatomy/eye-region.md) · FACS [facs-expressions](../anatomy/facs-expressions.md) · FAT [fat-compartments](../anatomy/fat-compartments.md) · FHB [forehead-brow-temple-hairline](../anatomy/forehead-brow-temple-hairline.md) · FOR [forensic-reconstruction](../anatomy/forensic-reconstruction.md) · JAW [jaw-chin-neck](../anatomy/jaw-chin-neck.md) · MLF [muscles-lower-face](../anatomy/muscles-lower-face.md) · MLT [mouth-lips-teeth](../anatomy/mouth-lips-teeth.md) · MMF [muscles-mid-face](../anatomy/muscles-mid-face.md) · MMJ [muscles-mastication-jaw](../anatomy/muscles-mastication-jaw.md) · MUF [muscles-upper-face](../anatomy/muscles-upper-face.md) · NOSE [nose](../anatomy/nose.md) · PER [face-perception-likeness](../anatomy/face-perception-likeness.md) · POP [population-variation](../anatomy/population-variation.md) · SEX [sexual-dimorphism](../anatomy/sexual-dimorphism.md) · SKIN [skin-wrinkles-microdetail](../anatomy/skin-wrinkles-microdetail.md) · SKO [skull-osteology](../anatomy/skull-osteology.md) · SMAS [smas-ligaments](../anatomy/smas-ligaments.md) · STT [soft-tissue-thickness](../anatomy/soft-tissue-thickness.md)

## 1. Conventions

- **R1.1** Units are mm and degrees. Head frame: +x subject's left, +y up, +z forward, origin on the midsagittal plane, levelled to Frankfort horizontal (FH). Blender mapping (x, y, z) → (x, −z, y); `.L` = +X [CRL].
- **R1.2** "Left/right" means the subject's side in every scheme (dlib, MediaPipe, ARKit). Mirrored inputs swap labels [CRL, FACS].
- **R1.3** Every prior row carries `population, sex, age_band, method (caliper | 3d_surface | photo2d | ct | cbct | mri | us | cadaver), posture (upright | supine), landmark_variant, badge, source`. Compare a model value with a norm only when method and variant match, or after an explicit offset [ANT, SKO, STT].
- **R1.4** The likeness objective is the sitter's deviation from the mean. Priors fill only what no view observes; with landmarks seen in ≥2 pose-solved views, cap total prior weight at 10–20% of the objective 🧠 [ANT, POP, PER].
- **R1.5** Keep three weights separate: noise in the data term (`ViewObs.sigma_px`, `weights`), population spread in `Priors.sigma`, perceptual weight only in evaluation and view requests 🧠 [PER].

## 2. Data formats and landmark schemes

- **R2.1 Landmark registry** [CRL]: `abbr, aliases, tissue (bone|skin|hair), side, bookstein_type, variant, kind ∈ {vertex, barycentric, extremal(dir, region), constructed(fn), contour(sliding|silhouette)}, visibility, sigma_t, sigma_n, source_ids`. Mandatory variants: `go: outer|bisector|tangents`, `gn: ceph_mid|anthro_lowest` (Farkas gn = cephalometric menton), `sto: single|sup|inf`, `ls: border|prominent`, `n′: deepest|over_n`. Route `synthetic.py` names (`pogonion`, `labrale_superius`, `vertex_front`) through aliases.
- **R2.2 NormRecord** [ANT]: `{id, a, b, distance: chord|proj_x|proj_y|proj_z|arc, frame: FH|camera, method, landmark_variant, population, sex, age_band, n, mean, sd, source_ids, status}`.
- **R2.3 dlib-68**, 0-based: jaw 0–16, right brow 17–21, left brow 22–26, nose 27–35, right eye 36–41, left eye 42–47, mouth 48–67 ✅. Point correspondences: ex 36/45, en 39/42, ch 48/54, prn 30, sn 33, ls 51, li 57, sto = mean(62, 66). Points 0–16 and 17–26 are sliding contours, never gonion or glabella 📄 [CRL].
- **R2.4 MediaPipe 478** = 468 mesh + 10 iris points (468–477) ✅. Anatomical index candidates (prn 1, n′ ~168, en 133/362, ex 33/263, ch 61/291, ls 0, li 17, sto mean(13, 14), me′ ~152, zy silhouette 234/454, iris centres 468/473) are 🧠: render index labels on the canonical mesh and version-lock the map. Lid points 159/145 and 386/374 📄. The z output is relative, not mm: ignore it or give it σ ≥ 10 mm 🧠. There is no vertex for t, po, tr or v; index 10 is mesh top, not trichion [CRL, FHB, MUF].
- **R2.5 Expression naming**: shape keys use ARKit-52 names. MediaPipe emits 52 scores in [0, 1] (count 📄, name list unconfirmed) when `output_face_blendshapes` is on [FACS, MMF].
- **R2.6 Template annotations**, authored once on a fixed-topology template: region masks; the 17-region fat atlas [FAT]; ligament paths `lig_*` and fold curves `fold_nlf`, `fold_marionette` defined on the bone layer [SMAS]; plane-break curves (temporal crest, lateral orbital rim, arch, key ridge, mandibular border, mental tubercles) [SKO, FHB]; RSTL tangent field, skin-thickness and pore-spacing maps [SKIN]; vertex mirror map [ASY]; stable nose vertex IDs [NOSE].
- **R2.7 Subject metadata**, consented and never inferred from photos: age (years and months for minors), `sex_prior` or numeric s, BMI, dental status, toxin/filler/surgery history, `hrt_years`, glasses. No ancestry label is stored [SEX, POP, CHI, AGE].
- **R2.8 Defaults file format**: `research/data/<topic>.json` = `{topic, tables:[{name, units, columns, rows, population, source_urls}]}`. Load from tables such as `skull-osteology:engine_priors_suggested`, `facial-asymmetry:fitting_prior_sigmas`, `facs-expressions:neutral_view_qc_thresholds`.

## 3. Camera, frame and scale

- **R3.1** Full perspective everywhere. Weak-perspective scale errors at the ear (4–36%) and nose exceed population SDs 🧠 [EAR, NOSE].
- **R3.2** Recompute extremal landmarks as a softmax-weighted argmax ⟨p, d⟩ over a region mask (temperature 1–2 mm) after every pose update. A frame tilt slides them ≈ R·θ (prn 0.5–0.9 mm per 5°, g′ 2.6–7 mm) 🧠 [CRL].
- **R3.3** Fit the symmetry plane by reflection Procrustes (`umeyama`), weights upper face 1.0, midface 0.5, lower face 0.25, ears 0.1, Huber ≈1 mm. Re-estimate after every outer iteration: a 2° frame error reads as ≈3 mm of fake asymmetry 🧠 [ASY].
- **R3.4** Scale by inverse-variance fusion: any caliper value (≈0.5 mm error) overrides corneal diameter, IPD and the global scale prior. Use the iris only when both limbus edges are sharp (ellipse major axis), never through spectacles (≈1–1.5% per dioptre). Never trichion, vertex or hair 🧠 [ANT, EYE, CRL].
- **R3.5** Head–neck pitch is per photo, N(0, 10²)°; add 2–3° pitch σ to reported forehead inclination 🧠 [JAW, FHB].

## 4. Default priors

Log-normal "μ" values are medians. Use Student-t (ν ≈ 4) or Huber on identity priors so real outliers survive 🧠 [PER, ASY, CAN].

| Parameter | Default | σ | Unit | Badge | Src |
|---|---|---|---|---|---|
| Corneal diameter, adult and ≥3 y | 11.8 | 0.6 | mm | ✅ mean (pooled 11.84, SD 0.79) | EYE, CHI |
| Corneal diameter, 0 y / 1 y | 10.0 / 11.2 | 0.6 | mm | 🧠 ↔️ | CHI |
| IPD (weak check) | 63 (M 64, F 61.5) | 3.5–3.8 | mm | 🧠 | ANT, SEX, EYE |
| Global scale s | 1.0 | 0.035 | ratio | 🧠 | ANT |
| Globe radius / corneal radius | 12.0 / 7.8 | 0.5 / 0.27 | mm | 🧠 / ✅ | EYE |
| Hertel: cornea ahead of lateral rim | 16 white, 18 Black, 14 East Asian | 2 | mm | ✅ (corrected) | EYE |
| Hertel L–R / vertical dystopia | 0 | 0.7 / 1.0 | mm | 🧠 | EYE |
| Globe offset, superior and lateral | +1, +1 | 1.5 | mm | 📄 sign | FOR |
| Fissure length / height | 30 / 9.5 | 1.6 / 1.0 | mm | 🧠 | EYE |
| Canthal tilt vs FH | +5 (East Asian +8) | 3 (3.5) | ° | 🧠 ↔️; ex 2–4 mm above en ✅ | EYE |
| ex depth behind en | 10.5 | 2.5 | mm | 🧠 ↔️ | EYE |
| MRD1 / MRD2 | 4.5 / 5.25 | 0.8 | mm | 🧠 | EYE |
| Upper-lid crease | F 8, M 7, East Asian 4, unknown 6.5; plus P(absent) | 2 / 2 / 2.5 / 3 | mm | ↔️ | MUF, EYE |
| True en − visible en, with epicanthus | HalfNormal | 2 | mm | 🧠 | POP |
| FSTT glabella / nasion / rhinion | 5.5 / 6.0 / 3.0 | σ_log 0.15–0.20 | mm | ✅ / ✅ / 📄 | SKO, STT |
| FSTT supraglabella / frontal eminence / supraorbital | 4.5 / 4.5 / 6.2 | σ_log 0.15–0.20 | mm | ✅ corrected | FHB |
| FSTT pogonion / gnathion / menton | 11.5 / 8.5 / 7.5 | σ_log 0.22 / 0.18 / 0.25 | mm | ✅ / 📄 / 🧠 | SKO, JAW |
| FSTT philtrum, lips | 11–13 | σ_log 0.20–0.25 | mm | ↔️ | STT |
| FSTT zygion / gonion | 7–8 / 13 | σ_log 0.30 / 0.35 | mm | 🧠 / ↔️ | STT, MMJ |
| FSTT inferior malar / buccal | 14 / 20 | σ_log 0.30–0.40 | mm | 🧠 | STT |
| FSTT BMI slope (log per unit) | 0.01 forehead; 0.02–0.03 n, lips, chin; 0.03–0.05 cheek, jaw | +0.05–0.10 σ_log if BMI missing | — | ✅ direction, 🧠 slopes | STT |
| FSTT sex effect M−F | +1.5–2.5 lips, philtrum; +1 pg; +0.5 forehead; lateral ≈0 | |γ| ≤ 0.2 in log | mm | ✅ midline, ↔️ lateral | STT, SEX |
| Sex axis s | declared N(±1, ·); unspecified ½N(−1,·)+½N(+1,·) or N(0, 1.2²) | 0.65 (×1.3 if population unknown) | — | 🧠 | SEX |
| Size log k (per sex) | ±0.035 | 0.04 | log | 🧠 | SEX |
| Gonial angle | 122 (consider 124; CBCT means 125–129) | 7 | ° | ↔️ (cephalometric mean 121–125 ✅) | JAW, MMJ |
| Gonial angle, M − F | 0 to −4 | — | ° | ↔️ | JAW |
| Bony go–go | M 97, F 90 | 6 / 5 | mm | 🧠 ↔️ | JAW, MMJ |
| Ramus height Co–Go | M 60, F 54 | 5 / 4 | mm | 🧠 ↔️ | JAW |
| Masseter, relaxed, per side | F 10, M 12, unknown 11 | 1.8 / 2.0 / 2.3 | mm | ✅ anchors (9.8 / 11.3), 🧠 widening | MMJ |
| Masseter clench gain κ | 0.28 | 0.05 | ratio | 📄 derived | MMJ |
| Cervicomental angle, canonical pose | 118 | 12 | ° | 🧠 ↔️ | JAW |
| n–sn / sn–prn | 54.5 M, 50.5 F / 20 M, 18.5 F | 3.3, 3.1 / 2.0 | mm | 🧠 | NOSE |
| al–al | 34.9 M, 31.4 F (unknown population 36 / 33, σ 4) | 2.1 / 2.0 | mm | 🧠 | NOSE |
| Nasolabial / nasofrontal angle | 100 M, 105 F / 125 M, 130 F | 9 / 7 | ° | ↔️ (samples 98–116 / 124–142) | NOSE |
| ls–sto | 8.0 − 0.05·(age − 25) | 1.5 | mm | 📄 | MLT, AGE |
| sto–li / ls–sto | 1.3, clamp 0.8–2.3 | 0.3 | ratio | ↔️ | MLT |
| Resting upper-incisor display | interpolate (25, 3.4), (35, 1.6), (45, 1.0), (55, 0.5), (65, 0) | 1.2 | mm | 📄 corrected | AGE, MLT |
| cph–cph | 11.5 | 1.5 | mm | 📄 | MLT |
| Modiolus from cheilion | 12 lateral, −3 vertical | 4 / 5 | mm | 🧠 | MLF, MMF |
| Mentolabial depth / angle | 4 / 125 | 2 / 12 | mm / ° | 🧠 / ↔️ | MLF |
| Lower lip to E-line | −2 | 2 (3 if ancestry unknown) | mm | ↔️ | MLF, JAW |
| Ear length | 61, +2 if male, +0.2·max(0, age − 25) | 4.5 | mm | 📄 | EAR, AGE |
| Ear width / length; tilt; tragion vs orbitale | 0.50; 20°; 0 mm | 0.05; 7°; 5 mm | — | 📄; 🧠; 🧠 | EAR |
| Forehead inclination | M 12, F 8 | 5 | ° | ↔️ | FHB |
| Neutral-view expression weights ψ | half-normal + L1 | 0.05–0.10 (expression views 0.5) | — | 🧠 | FACS |
| Jaw angle in neutral views | 1.5, bounded 0–30 | 1 | ° | 🧠 | FACS |
| Age, declared / estimated | as given | 1 / 6 | y | 🧠 | AGE |

- **R4.1 Landmark position σ** (replace scalar `Priors.sigma = 8.0` with per-landmark (N, 3) arrays at 1.0–1.5× population SD; keep 8 mm only as a fallback) 🧠 [PER, SEX]. Across/along the contour: sharp junctions (en, ex, ch, sn, closed sto) 1.0–1.5 / 1.0–1.5 mm; curvature extremes (prn, pg′, me′) 1–2 / 2–4 mm; flat extremal points (g′, zy′, go′, v) 1.5–3 / 5–10 mm; jaw oval 1.5–2.5 / free; brows 3–5 / free [CRL]. Anisotropic (x, y, z): g, n (3, 4, 2); pg (3, 4, 3); zy, go (6, 8, 8). Observation weights: n, g, pg, canthi 1.0; tragion 0.5; zy, go 0.1–0.2 [SKO].
- **R4.2 Symmetry σ per axis on d = X_l − M·X_r (= 2A)**: canthi, pupils, lids 0.7–1.0; brows 1.5 (vertical 2.0); alare, orbitale, zygion 1.0–1.5; cheilion 1.5–2.0; gonion 2.5–3.0; ears 3–4. Midline σ on x: nasion, glabella 0.75–1.0; prn, sn 1.5–2.0; pg, me 2–3 mm 🧠. `sigma_sym` must become a per-pair array; modes `assist` (×0.25), `prior`, `enforce` (block-out only) [ASY].
- **R4.3 Ratio priors** on log ratios, σ same population / any population: en–en/ex–en 1.05 (0.08/0.14); al–al/en–en 1.02 (0.09/0.16); ch–ch/al–al 1.55 (0.07/0.13); sn–gn/n–sn 1.27 (0.08/0.10); ch–ch/IPD 0.83–0.85 QA only 🧠 [CAN, MLT]. Encode each geometric fact once: Goode, Crumley and nasofacial are one triangle; with a 3DMM prior, ratios are diagnostics or σ ×2 [NOSE, CAN].
- **R4.4 Norm widening**: log d ~ N(log μ, (k·CV)²), k = 1 matched; 1.5 unknown population for low-variance measures; 2.5 (or a balanced mixture) for al–al and en–en; ×1.2 for Farkas-to-3D drift 🧠 [ANT, POP].
- **R4.5 Children**: CV 0.06–0.08; sex terms weighted by logistic((age − a_PHV)/1.5 y), a_PHV 11.5 F / 13.5 M; regularise to the age-matched mean 🧠 [CHI].

## 5. Model structure

- **R5.1 Two-layer model**: skin = bone + t·n̂_bone, n̂ smoothed over 5–10 mm, the perpendicular-to-bone convention (📄 most reproducible). Hinge on skin inside bone; t ≥ 2 mm (1.5 at rhinion). Inverse use b = s − t·n̂ with Σ_b = Σ_s + (μσ)² n̂n̂ᵀ + 1–3 mm tangential; only g, n, rhi, pg, gn drive the skull warp [STT, SKO].
- **R5.2 Ordering hinges (FH)**: z(g) > z(n); z(cornea) − z(lateral rim) ∈ [11, 22] mm (widened from `ordering_constraints` [12, 20], see README C-5); z(supraorbital rim) > z(lateral rim) 📄; orbit w/h 1.1–1.2 📄; zygion within ±10 mm of FH 🧠; soft g′ ≥ n′ + 1 mm; ex ≥ 3 mm inside the bony lateral rim; no lid–globe penetration, margin 1.5–2.5 mm; columella show 0–7 mm, ac 8–16 mm behind sn [SKO, FHB, EYE, NOSE].
- **R5.3 Eyes** are rigid spheres excluded from template warps; upper lid follows corneal pitch ≈0.8–1.0, lower ≈0.3 in downgaze 🧠 [EYE, CHI].
- **R5.4 Sex** X = k·R(μ̄ + (s/2)Δ_sex + Σc_iφ_i) + t with PCs from within-sex covariance; hinges only, never sex-specific bounds 🧠 [SEX].
- **R5.5 Population**: balanced pooled prior μ = (1/K)Σμ_k, Σ = (1/K)Σ[Σ_k + (μ_k − μ)(μ_k − μ)ᵀ], or a uniform-weight mixture driven only by geometry. Crease {absent, low, standard} and epicanthus {none, palpebral, tarsal, inversus} are categorical latents with their own shape keys 🧠 [POP, EYE].
- **R5.6 Expression**: one identity β; per view ψ_v (51–52 ARKit-named), jaw θ_v about the condyles (rotation for the first 20–25 mm of opening, then translation); only neutral-tagged views constrain β; the AU subspace (muscle-line displacement fields) is projected out of the identity basis. Antagonist penalties only for impossible pairs (blink vs wide, jawLeft vs jawRight) [FACS, MMF, MUF, MLF, JAW].
- **R5.7 Age basis**, separate from identity: `laxity`, `deep_cheek_volume`, `orbital_fat_prolapse`, `temporal_hollow`, `orbit_rim_recession`, `maxilla_retrusion_deg`, `mandible_loss` (gated by dental status), `alveolar_collapse_mm`, `skin_age` (texture only) 🧠 [AGE, SMAS].
- **R5.8 Soft-tissue fields**: δ_r = μ_r + a_r·z_adip + b_r·z_age + ε_r per fat region [FAT]; σ_t(x) = σ_lig + (σ_space − σ_lig)·m(x), σ_lig 1.0, σ_space 3.5 mm, m from a Laplace solve [SMAS]; jaw width = bone + 2(masseter·(1 + κc) + fat) + parotid, c per image [MMJ] (all 🧠).
- **R5.9 Warping**: `laplacian_deform` needs per-vertex smoothness weights: ligament strips ×3–5, spaces ×0.5–0.7, lips 0.3, lid margins 3.0, forehead 0.5 (tangential sliding), zygomatic body 1.5–2.0, NLF bending 0.2–0.3; lower weights across tagged plane-break curves 🧠. Never symmetrise warp targets; export Asym = warp(S + A) − warp(S) as a shape key [SMAS, MUF, MMF, MLF, SKO, ASY].
- **R5.10 Silhouettes**: jawline, chin, neck front, nose profile, ear helix and lip outline beyond ≈35–45° yaw are occluding contours with correspondences recomputed every iteration; ear contours weighted max(0, cos(ray, ear normal))² [JAW, MMJ, NOSE, MLT, EAR].
- **R5.11 Detail and texture**: fit shape only to wavelengths ≥ ≈5 mm and write residuals to UV displacement in mm; gate extraction by mm/px (pores ≤ 0.033, fine lines ≤ 0.08, line positions ≤ 0.25); never mirror texture or detail; never regularise skin tone toward an albedo PCA mean 🧠 [SKIN, ASY, POP].

## 6. Failure modes the engine must detect

Flags ask the user and never auto-correct toward a norm [STT, CAN, ASY].

| Failure | Test | Threshold | Src |
|---|---|---|---|
| Non-neutral frame | MediaPipe scores | mouthSmile > 0.25; cheekSquint, eyeWide, browInnerUp/OuterUp > 0.3; browDown > 0.35; eyeBlink > 0.4; jawOpen > 0.08; mouthPress/Roll/ShrugLower > 0.3 🧠 | FACS |
| Parted lips | inner gap / ch–ch | > 0.04: drop sto, li 🧠 | MLT, CRL |
| Raised brows | brow vs multi-frame median | > 2.5 mm 🧠 | MUF |
| Off-axis gaze | iris ellipse | pitch > 10–15°: drop lid residuals 🧠 | EYE |
| Mirrored photo | refit with u → W − u, labels swapped | consistently lower error 🧠 | ASY |
| Close camera or wrong focal | al–al/zy–zy, prn magnification vs population bound; norm z | |z| > 3: refit focal length 🧠 | ANT, CAN |
| Prior-dominated region | k = 1 − σ²_post/σ²_prior from diag((JᵀJ)⁻¹) | k < 0.8 on top-5 regions, or > 70% prior at radix, tip, lips, occiput: request a view 🧠 | PER, POP |
| Symmetrised or broken fit | whole-face RMSD vs mirror | < 0.3 or > 1.5 mm 🧠 | ASY |
| Visible asymmetry to confirm | pair differences | eyelid ≥ 2, brow or mouth ≥ 3 mm, cant ≥ 3° | ASY |
| Single-view asymmetry | views per pair | < 2 views ≥ 30° apart: σ_A ÷ 4, show only |d| > 2σ_post 🧠 | ASY |
| Implausible tissue depth | per-landmark FSTT z | |z| > 2.5, heatmap 🧠 | STT |
| Eye anomaly | Hertel L–R, dystopia | > 2 mm 🧠 | EYE |
| Sex-prior conflict | |s − s₀| | > 2σ_s: check lens, pitch, beard, makeup 🧠 | SEX |
| Occlusion | hair, hat, glasses, beard, collar masks | gate ears, forehead, jaw; Huber or Tukey | EAR, FHB, JAW |
| Head flexion | pitch | < −10°: freeze jowl and submental terms 🧠 | FAT, JAW |
| Mixed states | EXIF dates; clench, toxin, smile frames | child span per CHI Table 4; refuse > 2× span for infants 🧠 | CHI, MMJ |
| Insufficient resolution | mm/px per view | below band gate: synthesise and label "synthetic" 🧠 | SKIN |
| Domain shift | supine or cadaver priors | down-weight where mobility m > 0.5 🧠 | SMAS, STT |
| Definition mismatch | variant of norm vs landmark | refuse the comparison | CRL, ANT |
| Detector bias | epicanthal corner as en; colour-edge lips; prn drawn 1–2 mm to highlight | en σ 2.5 mm with fold; edge terms | EYE, MLT, NOSE |

## 7. Licence, privacy and safety constraints

- **R7.1** Do not bundle dlib's 68-point model: it is trained on 300-W images whose licence excludes commercial use 🧠. MediaPipe is Apache-2.0 🧠 [CRL, FACS].
- **R7.2** FLAME 2017–2023 models are non-commercial academic; FLAME 2023 Open is CC-BY-4.0 and allows commercial use 📄 (corrected). BFM 2009 is non-commercial 📄. Re-check every 3DMM, ear model (York Ear Model, UHM) and LSFM licence before shipping 🧠 [FACS, SEX, POP, EAR, CHI].
- **R7.3** 3DFN: summary data open, individual data by Data Access Request ✅. Headspace/LYHM research licence; SizeChina commercial; OpenFace academic 🧠. CaptureForge is GPL-3.0; the 478→68 converter is MIT 📄 [ANT, CHI, FACS, CRL].
- **R7.4** Never infer or store ancestry; mixture clusters are never surfaced as ethnicity (GDPR Art. 9) 🧠. Never infer sex, age or minor status from photos [POP, SEX, CHI].
- **R7.5** Minors: guardian consent plus child assent, local processing by default, limited retention, provenance metadata, and an irreversible block on sexualised or nude pipelines (legal details time-sensitive) 🧠 [CHI].

## 8. Open questions

1. Farkas 1994 and 3DFN summary means to replace the 🧠 linear norms; secular drift [ANT, CRL].
2. Verified MediaPipe anatomical indices and blendshape names; ARKit L/R convention and AU map [CRL, FACS, MUF].
3. tragion→porion and or′→orbitale offsets [CRL].
4. Per-landmark T-table values, BMI slopes, supine-to-upright corrections; sign of lateral sex differences [STT, SEX].
5. Do MAP or de-shrunk estimates look more like the sitter? What is the 3D just-noticeable displacement for familiar viewers? [PER, ASY]
6. Does symmetrising a 3D head measurably lower likeness? [ASY]
7. Per-AU displacement in mm (D3DFACS) [FACS].
8. Multi-population 3D norms, radix and crease norms, detector and 3DMM bias audits (targets |bias| < 0.25 SD, worst/best error ratio < 1.2) [POP].
9. Sub-adult FSTT and child-capable 3DMM licences [CHI].
10. Upright compartment volumes, SMAS thickness by region, 3D ligament positions [FAT, SMAS].
11. Sourced nasal angle and projection norms by population [NOSE].
12. Ear tilt and height norms [EAR]; ex depth behind en and Hertel L–R threshold [EYE].
13. Photo reliability of cervicomental and gonial angles against CBCT [JAW].
14. Pore, wrinkle-depth and microrelief atlases [SKIN].
