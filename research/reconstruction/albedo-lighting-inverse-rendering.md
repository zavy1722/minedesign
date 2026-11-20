# Albedo, lighting and inverse rendering for faces

> A face pixel is albedo × shading (+ specular) times unknown exposure and white balance, bent by a tone curve; from one uncalibrated photo the split is ambiguous (albedo-vs-light scale, light colour vs skin hue, bas-relief shape-vs-light). Order-2 spherical harmonics (SH: 9 coefficients per channel, 27 in RGB) hold ≈99 % of Lambertian shading and are the standard lighting model in BFM/FLAME fitting, but encode no cast shadows, specular or light sharpness. "Albedo" models (BFM, FLAME's BFM-derived space, AlbedoMM, TRUST's BalancedAlb) differ in what they really contain, and priors learned from light-skinned data pull skin tone toward the training mean, which TRUST showed hurts darker skin most. The robust fix is capture-side: RAW + colour chart + cross-polarised or soft distant light, then divide the projected photo texture by the fitted mesh's rendered shading, with tone set by the chart, not a PCA prior. No harvest or earlier draft existed, so every item is expert knowledge pending verification.
>
> Evidence status: 0 ✅ / 4 📄 / 73 🧠 / 15 ↔️ — 2026-11-20 verification passes 1 and 2 covered 6 claims; remaining 🧠 items still unverified.

## Key facts

**Image formation and ambiguities**
- Working model: I = T(g ⊙ [a ⊙ E(n)/π ⊙ V + s]): T tone curve, g per-channel exposure × white-balance gain, a linear diffuse albedo, E irradiance, V visibility/AO, s specular. Most face fitters drop V, s and T and fold π and g into the light. 🧠
- **Scale ambiguity:** (a/k)·(k·E) renders identically for any k > 0, per channel. Only a known reflectance in shot (chart, grey card) or a prior fixes k; with a prior, the answer *is* the prior. 🧠
- **Hue ambiguity:** light colour and albedo colour trade freely; "white light" regularisers push any colour cast into the skin. 🧠
- **Generalised bas-relief** (Belhumeur, Kriegman & Yuille 1999): under orthographic projection and unknown distant Lambertian light, depth flattening/stretching plus matching light and albedo changes gives identical images, shadows included. Shading cannot set nose projection; multi-view geometry and landmarks must. 🧠
- **Albedo→geometry leakage:** brows, stubble, freckles, moles, under-eye pigment and contour makeup read as shading and get sculpted as form. 🧠

**Spherical-harmonic lighting**
- Lambertian irradiance = environment ⊛ clamped cosine, with band factors Â₀ = π, Â₁ = 2π/3, Â₂ = π/4, Â₃ = 0, Â₄ = −π/24 (Ramamoorthi & Hanrahan 2001; Basri & Jacobs 2003). Bands 0–2 hold 99.2 % of kernel energy (Table B). 🧠
- Average SH9 shading error for real environments is a few percent or less; worst-case per-pixel error under one point light is larger (quoted near 10 %; bounds differ by source). 🧠 ↔️
- SH9 says almost nothing about light *sharpness*: that lives in cast shadows, penumbrae, speculars and catchlights (see `blender/portrait-lighting-compare.md`). 🧠
- **Conventions are not portable:** basis sign/order, radiance vs pre-convolved irradiance coefficients, where π and Â_l are folded, and normal frame (camera/world/head, y-up/z-up, OpenCV/OpenGL) all vary. Deep3DFaceRecon folds non-standard band factors (a = π, 2π/√3, 2π/√8) into its SH class and adds init_lit = [0.8, 0, …, 0] to the lighting coefficients, i.e. 0.8 on the DC term [4]. 📄
- **Lighting frame in multi-view:** photographer circles a still subject under fixed lights → one lighting shared in the head frame; subject turns on a chair → lighting fixed in the camera/world frame, rotating relative to the head; separate sessions → per-view lighting. SH rotation is exact and cheap (band-wise; band 1 rotates as a vector). 🧠
- **Extensions:** visibility-weighted SH via precomputed radiance transfer (Sloan, Kautz & Snyder 2002); ray-traced self-shadowing plus specular (NextFace, Dib et al. 2021); the Basel Illumination Prior, a Gaussian over SH coefficients learned from real face photos (Egger et al. 2018). 🧠

**Albedo models** (details in Table F)
- **BFM colour is not physical albedo:** flash-captured, residual shading in concavities, display-encoded. 🧠 ↔️
- **Deep3DFaceRecon** (Deng et al. 2019): 80 identity + 64 expression + 80 BFM texture + 3 rotation + 27 SH + 3 translation = 257 coefficients. **DECA**: 50 BFM-derived albedo coefficients in FLAME UV + 27 SH. 🧠
- **AlbedoMM** (Smith et al., CVPR 2020): first statistical diffuse *and* specular albedo model, from polarised light-stage captures (3DRFE), linear colour, BFM2017 and FLAME topologies; small, narrow sample. 🧠
- **TRUST** (Feng, Bolkart, Tesch, Black & Abrevaya, ECCV 2022): showed earlier regressors' albedo tracks the training mean; contributed the synthetic FAIR benchmark (ground-truth albedo, ITA error per skin group), a tone-balanced albedo space (BalancedAlb), and *scene disambiguation*: light is estimated from the whole image, not the face crop. 📄 [1][2]
- **Learned high-res reflectance** (AvatarMe++, FitMe; Lattas et al.) and **FFHQ-UV** (GAN-normalised evenly lit UV maps) are sharper, but plausible rather than measured. 🧠
- **Biophysical alternative:** in optical-density (−log) space skin colour is roughly spanned by melanin and haemoglobin (Tsumura et al. 2003; BioFaceNet, Alotaibi & Smith). Two chromophore maps give a compact albedo prior that is neutral across tones. 🧠

**Skin-tone bias**
- Mechanisms: (1) light-skewed training scans; (2) an L2 pull to the PCA mean resolves the scale ambiguity toward that mean; (3) linear-RGB losses give dark pixels tiny residuals, under-weighting darker skin; (4) auto-exposure, noise and JPEG crush dark-skin shadows; (5) colour-threshold skin masks and parsers drop more pixels on dark skin or in coloured light. 🧠
- **Fitzpatrick types (I–VI) classify UV burn/tan response, not colour.** ITA (CIELAB) or the 10-step Monk scale label tone better. 🧠
- **ITA° = atan2(L* − 50, b*)·180/π** (Table C), defined on unexposed skin; sun-exposed facial skin reads darker. 🧠

**Capture and delighting**
- Cross-polarisation (film on lights, lens polariser at extinction) removes most surface specular, not shading, AO or inter-reflection; parallel minus cross isolates specular; cost ≈2–3 stops. 🧠
- Skin specular is an untinted dielectric reflection: F0 ≈ 0.028 at n ≈ 1.4. 🧠
- On-axis (ring) flash gives shading ≈ n·v / r², dividable once geometry is known, but inverse-square falloff over ≈10 cm of nose-to-ear depth is 21 % at 1 m vs 7 % at 3 m (Table E). 🧠
- **AI delighters** (Agisoft De-Lighter, Substance 3D Sampler's delight filter; portrait models such as Total Relighting, SwitchLight, RGB↔X) return plausible, unmeasured albedo; tone drift per skin group is undocumented; versions change. 🧠 ↔️
- **Phone pipelines** (local tone mapping, multi-frame HDR, beauty smoothing, Display-P3 HEIC, HDR gain maps) break the linear model: honour the embedded profile, prefer RAW/DNG. 🧠

## Numbers & reference tables

**A. Real SH basis, order 2** (unit normal n = (x, y, z); mathematics)

| l, m | Y_lm | Constant | Status |
|---|---|---|---|
| 0, 0 | c | 0.282095 | 🧠 |
| 1, −1 / 0 / 1 | c·y / c·z / c·x | 0.488603 | 🧠 |
| 2, −2 / −1 / 1 | c·xy / c·yz / c·xz | 1.092548 | 🧠 |
| 2, 0 | c·(3z² − 1) | 0.315392 | 🧠 |
| 2, 2 | c·(x² − y²) | 0.546274 | 🧠 |

Irradiance from radiance coefficients (Ramamoorthi & Hanrahan 2001): E(n) = c₁L₂₂(x²−y²) + c₃L₂₀z² + c₄L₀₀ − c₅L₂₀ + 2c₁(L₂,₋₂xy + L₂₁xz + L₂,₋₁yz) + 2c₂(L₁₁x + L₁,₋₁y + L₁₀z); c₁ = 0.429043, c₂ = 0.511664, c₃ = 0.743125, c₄ = 0.886227, c₅ = 0.247708. Diffuse radiance out = a·E/π. 🧠

**B. Clamped-cosine kernel per band** (energy = squared L2 norm on the sphere; total 2π/3)

| Band l | Â_l | Value | Cumulative energy | Status |
|---|---|---|---|---|
| 0 | π | 3.1416 | 37.5 % | 🧠 |
| 1 | 2π/3 | 2.0944 | 87.5 % | 🧠 |
| 2 | π/4 | 0.7854 | 99.2 % | 🧠 |
| 3 | 0 | 0 | 99.2 % | 🧠 |
| 4 | −π/24 | −0.1309 | ≈99.8 % | 🧠 |

**C. ITA skin categories** (Chardon et al. 1991, extended by Del Bino et al.; colorimeter on unexposed skin)

| Very light | Light | Intermediate | Tan | Brown | Dark | Status |
|---|---|---|---|---|---|---|
| > 55° | 41–55° | 28–41° | 10–28° | −30–10° | < −30° | 🧠 |

**D. ColorChecker Classic anchors** (commonly quoted post-2009 sRGB values, linearised with the sRGB curve; editions and measurement sets differ by a few units)

| Patch | sRGB 8-bit | Linear R, G, B | Y | Status |
|---|---|---|---|---|
| White 9.5 | 243, 243, 242 | 0.90, 0.90, 0.89 | 0.90 | ↔️ |
| Neutral 8 / 6.5 / 5 | 200 / 160 / 122 | 0.58 / 0.35 / 0.195 | same | ↔️ |
| Neutral 3.5 / Black 2 | 85 / 52 | 0.091 / 0.034 | same | ↔️ |
| Light skin | 194, 150, 130 | 0.54, 0.31, 0.22 | 0.35 | ↔️ |
| Dark skin | 115, 82, 68 (= #735244, manufacturer value) [5] | 0.17, 0.084, 0.058 | 0.10 | 📄 |

Real skin spans well beyond these patches: ≈0.55–0.65 linear red for very light skin, ≤0.05 linear blue for very dark skin (as in `blender/skin-shading.md`). ↔️

**E. Inverse-square falloff of a compact source across 10 cm of facial depth** (derived; 10 cm is an assumed adult nose-to-ear depth)

| Light distance | 0.5 m | 1 m | 2 m | 3 m | 5 m | Status |
|---|---|---|---|---|---|---|
| Near/far brightness ratio | 1.44 | 1.21 | 1.10 | 1.07 | 1.04 | 🧠 |
| Stops | 0.53 | 0.28 | 0.14 | 0.09 | 0.06 | 🧠 |

**F. Albedo models: what is really inside** (licences time-sensitive)

| Model | Data | Contents | Dims / topology | Licence | Status |
|---|---|---|---|---|---|
| BFM 2009 / 2017 | 200 scans (100 F/100 M), mostly European | per-vertex colour, residual shading, display-encoded | 199 PCs; BFM mesh | free non-commercial, registration | ↔️ |
| FLAME albedo (BFM-derived) | BFM resampled | inherits BFM bias | 50 in DECA; FLAME UV | BFM + FLAME terms | 🧠 |
| FLAME FFHQ texture space | in-the-wild FFHQ fits | baked lighting | FLAME UV | MPI non-commercial | 🧠 |
| AlbedoMM | polarised light stage (3DRFE), small | linear diffuse + specular albedo | BFM2017, FLAME | academic; check | 🧠 |
| TRUST BalancedAlb | tone-balanced texture set | linear albedo | FLAME UV | MPI non-commercial | 🧠 |
| FFHQ-UV | ≈50k GAN-normalised UV maps | evenly lit pseudo-albedo | own UV | check | ↔️ |

## Applying this to photo→3D face sculpting in Blender

1. **Capture.** RAW, manual exposure and fixed white balance for every view; a colour chart beside the cheek in the first frame of each lighting setup. No makeup or sheen, hair off forehead and ears, glasses off. Cross-polarised or large soft light at ≥2 m (Table E), or open shade, away from coloured bounce. No beauty, portrait or HDR modes. 🧠
2. **Circle a still subject** rather than turning the subject, so one lighting is shared in the head frame. 🧠
3. **Linearise.** Develop RAW without a tone curve; set white balance and exposure on the chart so Neutral 5 ≈ 0.19 and neutrals sit within ~5 % of Table D. A JPEG is never linear: invert sRGB and expect residual tone-curve error. 🧠
4. **Measure tone first:** L*a*b* and ITA of a flat, frontal, unshadowed cheek patch in the corrected photo. This is the acceptance target for the albedo. 🧠
5. **Project and bake** each linear photo into UV with weight max(0, n·v)², dropping n·v < 0.3; feather seams. 🧠
6. **Delight.** Convert the fitted SH9 to a world EXR. Cycles Bake ▸ Diffuse with Direct + Indirect on and Color off gives white-mesh shading with AO; divide the photo texture by it in float. A smooth fitted mesh removes only low-frequency shading, so pore and wrinkle shading stays in the albedo; if you also displace those, attenuate the albedo's high-pass luminance or they double. 🧠
7. **Fix tone:** scale per channel until the cheek albedo matches step 4, corrected for the known shading there. Never judge tone on a tone-mapped viewport. 🧠
8. **Clean residues:** mask highlights (low saturation, top few % luminance) and inpaint; hand-paint or mirror the cast shadows AO misses (nostrils, under-nose, eye sockets, under-chin). 🧠
9. **Blender:** albedo EXR in Linear Rec.709 (name varies by version) or 16-bit sRGB PNG into Principled Base Color; Cycles random-walk SSS treats Base Color as overall diffuse albedo. IOR ≈1.4; see `blender/skin-shading.md`. Compare renders with photos under the Standard view transform; AgX for viewing only. 🧠
10. **Validate** by rendering the fitted head under the recovered world through the solved camera, gated as in `blender/portrait-lighting-compare.md`. The real test is relighting: compare with a photo taken under different light. 🧠
11. **What goes wrong:** painted look (shading left in albedo); orange or waxy skin (JPEG saturation, oversized SSS radius); tone off (PCA prior, auto-exposure, no chart); seam colour jumps (per-view exposure/WB drift); fake cheekbones (contour makeup + high photometric weight); bumpy brows (pigment as geometry); blue shadow side (sky fill misassigned by chroma regularisers). 🧠

## Algorithmic implications

- **Forward model per view v:** Î_v = g_v ⊙ [a ⊙ E(R_v n)/π ⊙ V], specular masked rather than modelled in v1. Albedo a is shared; E is shared in head or world frame per capture mode, else per view. 🧠
- **Gauge:** fix g₀ from the chart. Without one, set g₀ = 1, flag "absolute albedo unknown" and expose a tone slider rather than letting a prior choose silently. 🧠
- **Stages:** (A) geometry and cameras from landmarks and silhouettes; (B) geometry fixed, alternate closed-form SH (weighted least squares, 9 × 3 unknowns, Huber IRLS) with per-texel a = I / (g·E·V/π) projected onto the albedo prior, 3–5 iterations; (C) optional photometric refinement of low-order shape or a detail layer, accepted only if landmark and contour gates do not worsen. 🧠
- **Residual:** r = log(I + ε) − log(Î + ε), ε ≈ 0.01 linear, Huber δ ≈ 0.05 (≈5 %), so dark and light skin weigh equally (≈ linear residual weighted by 1/â). 🧠 ↔️
- **Masks:** face-parsing skin only; drop n·v < 0.3, AO < 0.7, any channel > 0.95 after gain, the brightest 2–5 % of skin, pixels below 3× noise floor, and hair, beard, brows, lips, eyes, nostrils. 🧠
- **Priors** (engineering defaults, normalised by L₀₀ after white balance):

| Parameter | Prior / σ | Note | Status |
|---|---|---|---|
| log g_v per channel | N(0, 0.03) with chart; N(0, 0.3) without | per-view exposure/WB | 🧠 |
| SH band 1 / L₀₀ | N(0, 0.8) | | 🧠 |
| SH band 2 / L₀₀ | N(0, 0.35) | ridge; profiles see half the sphere | 🧠 |
| Key elevation, azimuth | N(30°, 25°), N(0°, 60°) | weak; matches portrait-lighting note | 🧠 |
| SH chroma (coeff − RGB mean) | N(0, 0.05·L₀₀) | only after chart WB | 🧠 |
| Radiance non-negativity | hinge on min Σ L_lm Y_lm | stops ringing worlds | 🧠 |
| Global melanin / tone | uniform over plausible range | no pull to a mean | 🧠 |
| PCA albedo coefficients | N(0, 1), tone PCs ×3 broader | or factor tone out as a gain | 🧠 |
| Low-pass log-albedo symmetry | N(0, 0.05) | not on moles/freckles | 🧠 |
| Log-albedo gradient per 5 mm | Huber 0.05 | released at lip, brow, lid edges | 🧠 |
| Specular F0 | fixed 0.028 | | 🧠 |

- **SH→Blender world:** radiance L(ω) = Σ L_lm Y_lm(ω); divide irradiance coefficients by Â_l first. Write an equirect float EXR ≥64 × 32 in Blender's z-up axes, clamp negatives and log the clamped energy. Cycles diffuse returns a·E/π, so a uniform world of radiance 1 renders white Lambertian at 1. 🧠
- **Exports:** albedo EXR; SH JSON stating its convention (radiance/irradiance, basis order, frame, units); world EXR; AO; specular mask; per-view gains; ITA report; confidence map (views × cos). 🧠
- **Fairness tests:** synthetic renders sweeping melanin over all six ITA groups × 5 light rigs × with/without chart; assert no monotone ITA bias and |ΔITA| ≤ 5° per group (engineering target); report stratified. 🧠
- **Licensing:** ship no BFM or original FLAME (2017–2023) assets, which are non-commercial only; FLAME 2023 Open is CC-BY-4.0 and may be shipped with attribution (corrected in verification). Per-texel delighting plus a chromophore prior avoids both the licences and the light-skinned PCA mean. 📄 [3]

## Disagreements, myths & open questions

- **Myths** 🧠: "BFM/FLAME texture = albedo" (residual shading, display encoding, baked FFHQ light; AlbedoMM was built partly to fix this). "Nine SH coefficients capture the lighting" (diffuse only). "Cross-polarised photo = albedo" (shading and AO remain). "Fitzpatrick type = skin colour". "AI delighting returns true skin colour" (unmeasured, may regress toward training data). "More photometric weight = more likeness" (it sculpts makeup and pigment).
- **Loss space** ↔️: linear (physical) vs gamma/sRGB (Deep3D-style, perceptual) vs log (tone-fair); effect on identity accuracy unquantified.
- **Lighting model** ↔️: SH9 suffices for diffuse fitting; visibility-aware SH, spherical Gaussians or ray-traced/neural lighting compete for shadows and specular, with no consensus.
- **Scene disambiguation** ↔️: TRUST's whole-image cue helps with recognisable background reflectances and fails on seamless backdrops; a chart is cheaper and exact.
- **Subsurface scattering** ↔️: SSS softens the terminator, so a Lambertian fit reads broader light; the bias is unquantified.
- **Open** 🧠: no large, tone-balanced, real face-albedo ground truth under an open licence (FAIR is synthetic); benchmarks disagree on tone reporting (ITA vs Monk vs Fitzpatrick); relightable Gaussian/NeRF avatars still need light-stage data, and casual-capture relighting fidelity is unestablished (time-sensitive).

## Sources

1. Feng et al., TRUST, arXiv 2205.03962: https://arxiv.org/abs/2205.03962
2. TRUST project page: https://trust.is.tue.mpg.de/
3. FLAME model license: https://flame.is.tue.mpg.de/modellicense.html
4. Deep3DFaceRecon_pytorch bfm.py (mirror of the repo file): https://huggingface.co/spaces/1dm/talker/blob/main/src/face3d/models/bfm.py
5. ColorChecker, Wikipedia (dark skin #735244, manufacturer sRGB): https://en.wikipedia.org/wiki/ColorChecker

**Further reading (by name, not yet linked)**
- Ramamoorthi & Hanrahan, "An Efficient Representation for Irradiance Environment Maps", SIGGRAPH 2001; "A Signal-Processing Framework for Inverse Rendering", SIGGRAPH 2001
- Basri & Jacobs, "Lambertian Reflectance and Linear Subspaces", TPAMI 2003
- Belhumeur, Kriegman & Yuille, "The Bas-Relief Ambiguity", IJCV 1999
- Sloan, Kautz & Snyder, "Precomputed Radiance Transfer…", SIGGRAPH 2002; Sloan, "Stupid Spherical Harmonics (SH) Tricks", GDC 2008
- Paysan et al., BFM 2009, AVSS 2009; Gerig et al., "Morphable Face Models – An Open Framework", FG 2018; Li et al., FLAME, SIGGRAPH Asia 2017
- Egger et al., "Occlusion-aware 3D Morphable Models and an Illumination Prior…", IJCV 2018
- Deng et al., Deep3DFaceRecon, CVPR Workshops 2019; Feng et al., DECA, SIGGRAPH 2021
- Smith et al., "A Morphable Face Albedo Model", CVPR 2020; Stratou et al., 3DRFE database, FG 2011 (title not confirmed)
- Feng et al., "Towards Racially Unbiased Skin Tone Estimation via Scene Disambiguation" (TRUST), ECCV 2022
- Dib et al., "Practical Face Reconstruction via Differentiable Ray Tracing" (NextFace), Eurographics 2021
- Lattas et al., AvatarMe++ (TPAMI 2021), FitMe (CVPR 2023); Bai et al., FFHQ-UV, CVPR 2023
- Tsumura et al., haemoglobin/melanin skin colour analysis, SIGGRAPH 2003; Alotaibi & Smith, BioFaceNet (venue not confirmed)
- Ma et al., polarised spherical gradient illumination, EGSR 2007
- Pandey et al., Total Relighting, SIGGRAPH 2021; Kim et al., SwitchLight, CVPR 2024; Zeng et al., RGB↔X, SIGGRAPH 2024
- Chardon et al., ITA skin colour typology, Int J Cosmet Sci 1991; Del Bino et al., Pigment Cell Research 2006 (title not confirmed)
- Monk Skin Tone scale (Ellis Monk; released with Google, 2022)

## Verification log (2026-11-20)

- SH band factors and Ramamoorthi constants c1..c5: unconfirmed (search found the paper, https://cseweb.ucsd.edu/~ravir/papers/envmap/, but not the numeric values); stays 🧠.
- ITA formula and category cut-offs: unconfirmed (no source listed the thresholds; https://pubmed.ncbi.nlm.nih.gov/34796498/ only supports ITA not equalling Fitzpatrick); stays 🧠.
- TRUST (FAIR benchmark with ITA scoring, scene-level light, light-skewed priors): confirmed 📄, https://arxiv.org/abs/2205.03962 and https://trust.is.tue.mpg.de/ (project page lists "BalanceAlb"; exact BalancedAlb naming not confirmed).
- Licences: corrected. FLAME 2017/2019/2020/2023 are non-commercial; FLAME 2023 Open is CC-BY-4.0 and commercial-permitted, https://flame.is.tue.mpg.de/modellicense.html. BFM, FFHQ texture, AlbedoMM, BalancedAlb terms not verified.

## Verification log, pass 2 (2026-11-20)

- ColorChecker Classic sRGB values: partly confirmed. Dark skin 115,82,68 (#735244) confirmed 📄 [5]. Light skin 194,150,130, the neutral patch values and Neutral 5 ≈ 0.19 not found in results: unconfirmed, stay ↔️/🧠. BabelColor (https://babelcolor.com/colorchecker-2.htm) notes manufacturer and measured values differ, supporting the ↔️ on the rest.
- Deep3DFaceRecon: SH band constants (π, 2π/√3, 2π/√8) and init_lit 0.8 on the DC term confirmed 📄 [4], https://huggingface.co/spaces/1dm/talker/blob/main/src/face3d/models/bfm.py. The 257-coefficient layout (80+64+80+3+27+3) not confirmed by results: stays 🧠.
