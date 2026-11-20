# Engine requirements digest: face & head anatomy

Compiled 2026-11-20 from the 27 `research/anatomy/` notes, verification corrections applied. Summary: [`anatomy/README.md`](../anatomy/README.md).

**Badges.** ✅ verified (≥2 sources) · 📄 single source · 🧠 expert knowledge, unverified · ↔️ contested. 72% of the area's 2,960 badged claims are 🧠 (1,590) or ↔️ (553). **Every 🧠 value is provisional: ship it as a named, tunable default carrying its badge, never as a constant.**

**Note codes:** AGE [aging-face](../anatomy/aging-face.md) · ANT [anthropometric-norms](../anatomy/anthropometric-norms.md) · ASY [facial-asymmetry](../anatomy/facial-asymmetry.md) · CAN [facial-proportions-canons](../anatomy/facial-proportions-canons.md) · CHI [child-growth](../anatomy/child-growth.md) · CRL [craniometric-landmarks](../anatomy/craniometric-landmarks.md) · CUH [cranium-under-hair](../anatomy/cranium-under-hair.md) · EAR [ear](../anatomy/ear.md) · EYE [eye-region](../anatomy/eye-region.md) · FACS [facs-expressions](../anatomy/facs-expressions.md) · FAT [fat-compartments](../anatomy/fat-compartments.md) · FHB [forehead-brow-temple-hairline](../anatomy/forehead-brow-temple-hairline.md) · FOR [forensic-reconstruction](../anatomy/forensic-reconstruction.md) · JAW [jaw-chin-neck](../anatomy/jaw-chin-neck.md) · MLF [muscles-lower-face](../anatomy/muscles-lower-face.md) · MLT [mouth-lips-teeth](../anatomy/mouth-lips-teeth.md) · MMF [muscles-mid-face](../anatomy/muscles-mid-face.md) · MMJ [muscles-mastication-jaw](../anatomy/muscles-mastication-jaw.md) · MUF [muscles-upper-face](../anatomy/muscles-upper-face.md) · NOSE [nose](../anatomy/nose.md) · PER [face-perception-likeness](../anatomy/face-perception-likeness.md) · POP [population-variation](../anatomy/population-variation.md) · SEX [sexual-dimorphism](../anatomy/sexual-dimorphism.md) · SKIN [skin-wrinkles-microdetail](../anatomy/skin-wrinkles-microdetail.md) · SKO [skull-osteology](../anatomy/skull-osteology.md) · SMAS [smas-ligaments](../anatomy/smas-ligaments.md) · STT [soft-tissue-thickness](../anatomy/soft-tissue-thickness.md)

## 1. Conventions

- **R1.1** Units mm and degrees. Head frame +x subject's left, +y up, +z forward, origin on the midsagittal plane, levelled to Frankfort horizontal (FH). Blender mapping (x, y, z) → (x, −z, y); `.L` = +X [CRL].
- **R1.2** Left/right is the subject's side in dlib, MediaPipe and ARKit; mirrored inputs swap labels [CRL, FACS].
- **R1.3** Every prior row carries `population, sex, age_band, method, posture (upright|supine), landmark_variant, badge, source`; compare only when method and variant match; down-weight supine or cadaver priors over mobile tissue [ANT, STT, SMAS].
- **R1.4** Likeness is the sitter's deviation from the mean. Priors fill only what no view observes; with landmarks seen in ≥2 pose-solved views, cap prior weight at 10–20% of the objective 🧠 [ANT, POP, PER].
- **R1.5** Noise belongs in `ViewObs.sigma_px`, population spread in `Priors.sigma`, perceptual weight only in evaluation 🧠 [PER].

## 2. Data formats and landmark schemes

- **R2.1 Landmark registry** [CRL]: `abbr, aliases, tissue (bone|skin|hair), side, bookstein_type, variant, kind ∈ {vertex, barycentric, extremal(dir, region), constructed(fn), contour(sliding|silhouette)}, visibility, sigma_t, sigma_n, source_ids`. Required variants: `go: outer|bisector|tangents`, `gn: ceph_mid|anthro_lowest` (Farkas gn = cephalometric menton), `sto: single|sup|inf`, `ls: border|prominent`, `n′: deepest|over_n`. Route `synthetic.py` names (`pogonion`, `labrale_superius`, `vertex_front`) through aliases.
- **R2.2 NormRecord** [ANT]: `{id, a, b, distance: chord|proj_x|proj_y|proj_z|arc, frame: FH|camera, method, landmark_variant, population, sex, age_band, n, mean, sd, source_ids, status}`.
- **R2.3 dlib-68** (0-based): jaw 0–16, right brow 17–21, left brow 22–26, nose 27–35, right eye 36–41, left eye 42–47, mouth 48–67 ✅. Points: ex 36/45, en 39/42, ch 48/54, prn 30, sn 33, ls 51, li 57, sto = mean(62, 66). Jaw and brow points are sliding contours, never gonion or glabella 📄 [CRL].
- **R2.4 MediaPipe 478** = 468 mesh + 10 iris points (468–477) ✅. Corners 61/291 📄 and lids 159/145, 386/374 📄; other anatomical candidates (prn 1, n′ ~168, en 133/362, ex 33/263, ls 0, li 17, sto mean(13, 14), me′ ~152, zy silhouette 234/454, iris 468/473) are 🧠: render labels on the canonical mesh and version-lock the map. z is relative, not mm: ignore or σ ≥ 10 mm 🧠. No vertex for t, po, tr, v; 10 is mesh top, not trichion [CRL, MLT, MUF, FHB].
- **R2.5 Expressions**: ARKit-52 shape-key names; MediaPipe's 52 scores in [0, 1] (count 📄) via `output_face_blendshapes` [FACS, MMF].
- **R2.6 Template annotations** on fixed topology: fat-region atlas [FAT]; ligament paths `lig_*` and fold curves on the bone layer [SMAS]; plane-break curves (temporal crest, orbital rim, arch, mandibular border) [SKO, FHB]; RSTL, skin-thickness and pore maps [SKIN]; vertex mirror map [ASY].
- **R2.7 Subject metadata**, consented and never inferred from photos: age (months for minors), `sex_prior` or numeric s, BMI, dental status, toxin/filler/surgery history, `hrt_years`, hair state per capture. No ancestry label is stored [SEX, POP, CHI, AGE, CUH].
- **R2.8 Defaults** live in `research/data/<topic>.json` = `{topic, tables:[{name, units, columns, rows, population, source_urls}]}`, e.g. `skull-osteology:engine_priors_suggested`, `facial-asymmetry:fitting_prior_sigmas`.

## 3. Camera, frame and scale

- **R3.1** Full perspective everywhere: weak-perspective errors at ear (4–36%) and nose exceed population SDs 🧠 [EAR, NOSE].
- **R3.2** Recompute extremal landmarks (softmax argmax ⟨p, d⟩ over a region mask) after every pose update 🧠 [CRL].
- **R3.3** Fit the symmetry plane by reflection Procrustes (`umeyama`), weights upper face 1.0, midface 0.5, lower 0.25, ears 0.1; re-estimate every outer iteration (a 2° frame error reads as ≈3 mm asymmetry) 🧠 [ASY].
- **R3.4** Inverse-variance scale fusion; a caliper or tape value overrides iris, IPD and global priors. Iris only with both limbus edges sharp and no spectacles; never trichion, vertex or hair 🧠 [ANT, EYE, CRL, CUH].
- **R3.5** Head–neck pitch per photo: N(0, 10²)° [JAW].

## 4. Default priors

Log-normal μ values are medians. Use Student-t (ν ≈ 4) or Huber on identity priors so real outliers survive 🧠 [PER, ASY, CAN].

| Parameter | Default | σ | Unit | Badge | Src |
|---|---|---|---|---|---|
| Corneal diameter, ≥3 y | 11.8 | 0.6 | mm | ✅ mean (pooled 11.84, SD 0.79) | EYE, CHI |
| IPD, weak check | 63 (M 64, F 61.5) | 3.5–3.8 | mm | 🧠 | ANT, SEX |
| Global scale s | 1.0 | 0.035 | ratio | 🧠 | ANT |
| Globe radius / corneal radius | 12.0 / 7.8 | 0.5 / 0.27 | mm | 🧠 / ✅ | EYE |
| Hertel: cornea ahead of lateral rim | 16 white, 18 Black, 14 East Asian; L–R 0 | 2; L–R 0.7 | mm | ✅ corrected; L–R 🧠 | EYE |
| Canthal tilt vs FH | +5 (East Asian +8) | 3 (3.5) | ° | 🧠 ↔️; ex 2–4 mm above en ✅ | EYE |
| ex depth behind en | 10.5 | 2.5 | mm | 🧠 ↔️ | EYE |
| Upper-lid crease (+ P(absent)) | Western F 7.3, M 6.9; East Asian 4; unknown 6.5 | 1.5 / 1.2 / 2.5 / 3 | mm | ↔️ corrected | EYE, MUF |
| FSTT glabella / nasion / rhinion | 5.5 / 6.0 / 3.0 | σ_log 0.15–0.20 | mm | ✅ / ✅ / 📄 | SKO, STT |
| FSTT supraglabella / frontal eminence / supraorbital | 4.5 / 4.5 / 6.2 | σ_log 0.15–0.20 | mm | ✅ corrected | FHB |
| FSTT pogonion / gnathion / menton | 11.5 / 8.5 / 7.5 | σ_log 0.22 / 0.18 / 0.25 | mm | ✅ / 📄 / 🧠 | SKO, JAW |
| FSTT philtrum, lips | 11–13 | σ_log 0.20–0.25 | mm | ↔️ | STT |
| FSTT zygion / gonion | 7–8 / 13 | σ_log 0.30 / 0.35 | mm | 🧠 / ↔️ | STT, MMJ |
| FSTT inferior malar / buccal | 14 / 20 | σ_log 0.30–0.40 | mm | 🧠 | STT |
| FSTT BMI slope, log per unit | 0.01 forehead; 0.02–0.03 n, lips, chin; 0.03–0.05 cheek, jaw | σ_log +0.05–0.10 if BMI missing | — | ✅ direction, 🧠 slopes | STT |
| FSTT sex effect M − F | +1.5–2.5 lips, philtrum; +1 pg; +0.5 forehead; lateral ≈0 | \|γ\| ≤ 0.2 (log) | mm | ✅ midline, ↔️ lateral | STT, SEX |
| Sex axis s | declared N(±1, ·); unspecified ½N(−1, ·) + ½N(+1, ·) or N(0, 1.2²) | 0.65 (×1.3 if population unknown) | — | 🧠 | SEX |
| Size log k per sex | ±0.035 | 0.04 | log | 🧠 | SEX |
| Gonial angle, sex-neutral | 122 (consider 124; CBCT 125–129) | 7 | ° | ↔️; sex gap 0–8° with no consistent sign | JAW, MMJ, SEX |
| Bony go–go | M 97, F 90 | 6 / 5 | mm | 🧠 ↔️ | JAW, MMJ |
| Masseter relaxed, per side | F 10, M 12, unknown 11 | 1.8 / 2.0 / 2.3 | mm | ✅ anchors (9.8 / 11.3), 🧠 widening | MMJ |
| Masseter clench gain κ | 0.28 | 0.05 | ratio | 🧠 derived from ✅ data | MMJ |
| Cervicomental angle, canonical pose | 118 | 12 | ° | 🧠 ↔️ | JAW |
| n–sn / sn–prn | M 54.5, F 50.5 / M 20, F 18.5 | 3.3, 3.1 / 2.0 | mm | 🧠 | NOSE |
| al–al | M 34.9, F 31.4 (unknown population 36 / 33, σ 4) | 2.1 / 2.0 | mm | 🧠 | NOSE |
| Nasolabial / nasofrontal angle | M 100, F 105 / M 125, F 130 | 9 / 7 | ° | ↔️ (samples 98–116 / 124–142) | NOSE |
| ls–sto | 8.0 − 0.05·(age − 25) | 1.5 | mm | 📄 | MLT, AGE |
| sto–li / ls–sto | 1.3, clamp 0.8–2.3 | 0.3 | ratio | ↔️ | MLT |
| Resting upper-incisor display | interpolate (25, 3.4), (35, 1.6), (45, 1.0), (55, 0.5), (65, 0) | 1.2 | mm | 📄 corrected | AGE, MLT |
| Mentolabial depth / angle | 4 / 125 | 2 / 12 | mm / ° | 🧠 / ↔️ | MLF |
| Lower lip to E-line | −2 | 2 (3 if ancestry unknown) | mm | ↔️ | MLF, JAW |
| Ear length | 61, +2 male, +0.2·max(0, age − 25) | 4.5 | mm | 📄 | EAR, AGE |
| Ear width/length; tilt; tragion vs orbitale | 0.50; 20°; 0 mm | 0.05; 7°; 5 mm | — | 📄; 🧠; 🧠 | EAR |
| Vault L, B, OFC, t–v (log, matched population) | sex means, CUH Table 1 | σ_log 0.035 / 0.037 / 0.028 / 0.045 (unknown ancestry L 0.05, B 0.065) | — | 🧠 | CUH |
| Vertex behind tragion; opisthocranion above FH | 10; 35 | 10; 10 | mm | 🧠 | CUH |
| Symmetric flattening; CVAI | 0, heavier right tail after ≈1992 births; 0.9·HalfNormal(2%) + 0.1·N(6%, 2%) | 4 mm; — | — | ↔️ | CUH |
| Face → vault | ρ(B∣zy–zy) 0.5, ρ(L∣face) 0.25, ρ(t–v∣face) 0.3; σ_post = σ√(1 − ρ²) | — | — | 🧠 | CUH |
| Expression weights ψ, neutral views | half-normal + L1 | 0.05–0.10 (expression views 0.5) | — | 🧠 | FACS |

- **R4.1 Landmark σ.** Replace scalar `Priors.sigma = 8.0` with per-landmark (N, 3) arrays (1.0–1.5× population SD) 🧠 [PER, SEX]. Across/along contour (mm): sharp junctions (en, ex, ch, sn) 1.0–1.5/1.0–1.5; prn, pg′, me′ 1–2/2–4; g′, zy′, go′ 1.5–3/5–10; jaw oval 1.5–2.5/free; brows 3–5/free [CRL]. Anisotropic (x, y, z): g, n (3, 4, 2); zy, go (6, 8, 8). Observation weights: n, g, pg, canthi 1.0; tragion 0.5; zy, go 0.1–0.2 [SKO].
- **R4.2 Symmetry σ** per axis on d = X_l − M·X_r (= 2A): canthi, pupils, lids 0.7–1.0; brows 1.5 (vertical 2.0); alare, orbitale, zygion 1.0–1.5; cheilion 1.5–2.0; gonion 2.5–3.0; ears 3–4. Midline x: nasion, glabella 0.75–1.0; prn, sn 1.5–2.0; pg, me 2–3 mm 🧠. `sigma_sym` must become a per-pair array; modes `assist` (×0.25), `prior`, `enforce` (block-out only) [ASY].
- **R4.3 Ratio priors** on log ratio, σ same/any population: en–en/ex–en 1.05 (0.08/0.14); al–al/en–en 1.02 (0.09/0.16); ch–ch/al–al 1.55 (0.07/0.13); sn–gn/n–sn 1.27 (0.08/0.10); ch–ch/IPD ≈0.83–0.85 QA only 🧠 [CAN, MLT]. Encode each fact once (Goode, Crumley and nasofacial are one triangle); with a 3DMM prior, ratios become diagnostics or σ ×2 [NOSE, CAN].
- **R4.4 Norm widening**: log d ~ N(log μ, (k·CV)²), k = 1 matched; 1.5 unknown population (low-variance measures); 2.5 or a balanced mixture for al–al, en–en; ×1.2 Farkas-to-3D drift 🧠 [ANT, POP].
- **R4.5 Children**: cornea 10.0 (0 y), 11.2 (1 y), σ 0.6 mm ↔️; CV 0.06–0.08; sex terms × logistic((age − a_PHV)/1.5 y), a_PHV 11.5 F / 13.5 M; regularise to the age-matched mean 🧠 [CHI].

## 5. Model structure

- **R5.1 Two layers**: skin = bone + t·n̂_bone, n̂ smoothed over 5–10 mm (perpendicular-to-bone convention, 📄 most reproducible). Hinge on skin inside bone; t ≥ 2 mm (1.5 rhinion). Inverse b = s − t·n̂, Σ_b = Σ_s + (μσ)²n̂n̂ᵀ + 1–3 mm tangential; only g, n, rhi, pg, gn drive the skull warp [STT, SKO].
- **R5.2 Ordering hinges (FH)**: z(g) > z(n); z(cornea) − z(lateral rim) ∈ [11, 22] mm (widen `ordering_constraints` from [12, 20], README C-5); z(supraorbital rim) > z(lateral rim) 📄; orbit w/h 1.1–1.2 📄; g′ ≥ n′ + 1 mm; ex ≥ 3 mm inside the bony rim; no lid–globe penetration; columella show 0–7 mm [SKO, FHB, EYE, NOSE].
- **R5.3 Eyes** are rigid spheres excluded from warps, centred ≈1–2 mm superolateral of the aperture centre (σ 1.5) ✅; upper lid follows corneal pitch ≈0.8–1.0, lower ≈0.3 in downgaze 🧠 [EYE, CHI].
- **R5.4 Sex**: X = k·R(μ̄ + (s/2)Δ_sex + Σc_iφ_i) + t, PCs from within-sex covariance; hinges only, no sex-specific bounds 🧠 [SEX].
- **R5.5 Population**: balanced pooled prior μ = (1/K)Σμ_k, Σ = (1/K)Σ[Σ_k + (μ_k − μ)(μ_k − μ)ᵀ], or a uniform-weight mixture driven by geometry only. Crease {absent, low, standard} and epicanthus {none, palpebral, tarsal, inversus} are categorical latents; true en = visible en + δ, δ ~ HalfNormal(2 mm) with a fold 🧠 [POP, EYE].
- **R5.6 Expression**: shared identity β; per view ψ_v (51–52) and jaw θ_v about the condyles (translation beyond ≈20–25 mm opening 📄); only neutral views constrain β; the AU subspace is projected out of the identity basis [FACS, MMF, MUF, MLF, JAW].
- **R5.7 Age basis**, separate from identity: `laxity`, `deep_cheek_volume`, `orbital_fat_prolapse`, `temporal_hollow`, `orbit_rim_recession`, `maxilla_retrusion_deg`, `mandible_loss` (gated by dental status), `alveolar_collapse_mm`, `skin_age` (texture only); age σ 1 y declared, 6 y estimated 🧠 [AGE, SMAS].
- **R5.8 Soft tissue**: δ_r = μ_r + a_r·z_adip + b_r·z_age + ε_r per fat region [FAT]; σ_t(x) = σ_lig + (σ_space − σ_lig)·m(x) with 1.0/3.5 mm, m from a Laplace solve [SMAS]; jaw width = bone + 2(masseter·(1 + κc) + fat) + parotid, clench c per image [MMJ] 🧠.
- **R5.9 Warping**: `laplacian_deform` needs per-vertex smoothness weights: ligament strips ×3–5, spaces ×0.5–0.7, lips 0.3, lid margins 3.0, forehead 0.5, NLF bending 0.2–0.3, lower across plane-break curves 🧠. Never symmetrise targets; export Asym = warp(S + A) − warp(S) as a shape key [SMAS, MUF, MMF, SKO, ASY].
- **R5.10 Silhouettes**: jawline, chin, neck, nose profile, ear helix and (beyond ≈35–45° yaw) lips are occluding contours re-matched every iteration; ear terms weighted max(0, cos(ray, ear normal))² [JAW, NOSE, MLT, EAR].
- **R5.11 Detail and texture**: fit shape to wavelengths ≥ ≈5 mm, residual to UV displacement in mm; gate by mm/px (pores ≤ 0.033, fine lines ≤ 0.08, line positions ≤ 0.25); never mirror texture or detail; never pull skin tone toward an albedo mean 🧠 [SKIN, ASY, POP].
- **R5.12 Vault**, parameterised apart from the face (L, B, t–v, vertex AP, op height, flattening, plagiocephaly shear). Dry-hair silhouettes are one-sided hinges (scalp inside the outline, weight ≥ 10× skin terms); controlled-hair silhouettes two-sided, σ 1.5–3 mm after subtracting the hair-class offset; tape loop = C_tape − θ_hair·t_c, σ² = 4² + (θ_hair·σ_t)² mm²; skull 4–7 mm inside the scalp; output per-vertex `cranium_confidence` 🧠 [CUH].

## 6. Failure modes to detect

Flags ask the user; never auto-correct toward a norm [STT, CAN].

| Failure | Test and threshold | Src |
|---|---|---|
| Non-neutral frame | MediaPipe scores above README Q13 limits (mouthSmile 0.25, jawOpen 0.08, others 0.3–0.4) 🧠 | FACS |
| Parted lips | inner gap / ch–ch > 0.04: drop sto, li 🧠 | MLT, CRL |
| Raised brows | > 2.5 mm above multi-frame median 🧠 | MUF |
| Off-axis gaze | gaze pitch > 10–15°: drop lid residuals 🧠 | EYE |
| Mirrored photo | refit with u → W − u and swapped labels lowers error consistently 🧠 | ASY |
| Close camera, wrong focal | al–al/zy–zy or prn magnification above population bound, or norm \|z\| > 3: refit focal 🧠 | ANT, CAN |
| Prior-dominated region | k = 1 − σ²_post/σ²_prior < 0.8 on top-5 regions, or > 70% prior at radix, tip, lips, occiput: request a view 🧠 | PER, POP |
| Symmetrised or broken fit | whole-face RMSD vs mirror < 0.3 or > 1.5 mm; confirm eyelid ≥ 2, brow/mouth ≥ 3 mm, cant ≥ 3° 🧠 | ASY |
| Single-view asymmetry | < 2 views ≥ 30° apart: σ_A ÷ 4 🧠 | ASY |
| Implausible tissue depth | FSTT \|z\| > 2.5 on a heatmap 🧠 | STT |
| Eye anomaly | Hertel L–R or dystopia > 2 mm 🧠 | EYE |
| Sex-prior conflict | \|s − s₀\| > 2σ_s: check lens, pitch, beard, makeup 🧠 | SEX |
| Vault errors | scalp outside the hair outline (vault too big); \|z\| > 3 on L, B, OFC (scale or focal error); < 8 views around the head (hull overshoot ≈8 mm at 4) 🧠 | CUH |
| Occlusion | hair, glasses, beard masks gate ear, forehead, jaw terms | EAR, FHB, JAW |
| Head flexion | pitch < −10°: freeze jowl and submental terms 🧠 | FAT, JAW |
| Mixed states | EXIF span beyond the child window (refuse > 2× for infants); clench or toxin changes 🧠 | CHI, MMJ |
| Low resolution | mm/px below detail gate: synthesise and label "synthetic" 🧠 | SKIN |

## 7. Licence, privacy, safety

- **R7.1** Do not bundle dlib's 68-point model: its 300-W training licence excludes commercial use ✅. MediaPipe is Apache-2.0 🧠 [CRL, FACS].
- **R7.2** FLAME 2017–2023, BFM 2009 and the York Ear Model are non-commercial 📄. FLAME 2023 Open is CC-BY-4.0 📄, but its vault is scalp plus hair ↔️. LYHM and Headspace are non-commercial 📄, UHM unknown: no commercial vault prior is known. LSFM models need a medical-research application 📄 [FACS, SEX, EAR, CUH, CHI].
- **R7.3** 3DFN: summary open, individual data by Data Access Request ✅. OpenFace non-commercial 📄; CaptureForge GPL-3.0; 478→68 converter MIT 📄 [ANT, FACS, CRL].
- **R7.4** Never infer or store ancestry, and never surface mixture clusters as ethnicity (GDPR Art. 9) 🧠. Never infer sex, age or minor status from photos [POP, SEX, CHI].
- **R7.5** Minors: guardian consent plus child assent, local processing by default, limited retention, provenance metadata, irreversible block on sexualised or nude pipelines 🧠. The 2025 COPPA amendments add facial templates to under-13 personal information (compliance by 2026-04-22) 📄 [CHI].

## 8. Open questions

1. Farkas 1994 / 3DFN means to replace 🧠 norms; MediaPipe indices; ARKit AU map [ANT, CRL, FACS].
2. Tragion→porion offset [CRL]; T-table values, BMI slopes, supine-to-upright corrections, lateral sex sign [STT, SEX].
3. MAP vs de-shrunk estimates; 3D just-noticeable displacement; does symmetrising lower likeness? [PER, ASY]
4. Per-AU displacement in mm [FACS]; multi-population radix and crease norms, bias audits (|bias| < 0.25 SD) [POP].
5. Sub-adult FSTT [CHI]; upright compartment volumes, SMAS thickness [FAT, SMAS]; nasal angle norms [NOSE]; ear tilt [EAR]; photo reliability of profile angles [JAW].
6. Adult plagiocephaly prevalence, hair-envelope thickness by hair type, a commercially usable full-head model [CUH].
