# Reconstructing hair, eyes and teeth from images

> Hair, eyes and teeth break photo→3D face pipelines first: hair is a fibre volume whose interior is never seen, the cornea is a transparent refractor on a rotating globe, and teeth are translucent and visible only when the mouth moves. The dependable route is **model-based**: a fixed-size parametric eye with per-view gaze fitted to limbus edges; a dental arch of per-tooth templates fitted to smile photos, or better, the person's own intraoral scan registered to the face; and hair as envelope + hairline + parting + flow field driving a procedural groom. Strand reconstruction from phone video or one image (Neural Haircut, GaussianHaircut, MonoHair, DiffLocks) works in research but is slow, scored on synthetic data and mostly non-commercial: an optional source of guide curves to re-comb. No harvest or draft existed: this is author knowledge (to about mid-2025) cross-checked against sibling notes marked "(lib: file)"; 2025–26 names, licences and runtimes need verification.
>
> Evidence status: 0 ✅ / 1 📄 / 52 🧠 / 27 ↔️ — 🧠 items are queued for web verification; 2026-11-20 pass checked 4 claims (1 confirmed, 1 partly confirmed, 2 unconfirmed; see Verification log).

## Key facts

**Hair**
- **Only the outer layer is observed** (silhouette, 2D orientation, highlights, hairline, parting); interior strands always come from a prior. 🧠
- **Orientation maps are the universal input.** Oriented Gabor filters give an undirected per-pixel orientation plus confidence (Paris et al. 2004; Chai et al. 2012); the 180° ambiguity is resolved by growing root→tip. 🧠
- **Lineage by input** 🧠
  - *One image:* database retrieval (Hu et al. 2015, USC-HairSalon, ~343 styles, recalled; AutoHair 2016) → HairNet (2018), NeuralHDHair (CVPR 2022), HairStep (CVPR 2023; a strand-map + depth-map intermediate narrows the synthetic→real gap).
  - *Calibrated rigs:* Paris 2004/2008, Luo 2013, Neural Strands and DeepMVSHair (2022).
  - *Phone video, per-subject optimisation:* Neural Haircut (ICCV 2023), MonoHair and Dr.Hair (CVPR 2024), strand-aligned 3D Gaussians "GaussianHaircut" (ECCV 2024).
  - *Generative priors:* GroomGen (2023), HAAR (CVPR 2024, text→strands), Perm (ICLR 2025, strands in scalp-UV texture space), DiffLocks (CVPR 2025, one image → strands by diffusion; trained on ~40k Blender-rendered synthetic styles; first method to recover highly curled/afro hair from one image, per its authors) 📄 [1][2].
- **Neural Haircut:** stage 1 fits an implicit hair-and-bust volume with a 3D orientation field supervised by 2D orientation maps and masks (bust from FLAME); stage 2 fits strands under a pretrained strand/hairstyle prior via differentiable strand rendering. 🧠
- **GaussianHaircut** binds thin Gaussians to polyline segments, so the photometric loss moves strands directly; reported faster and sharper than Neural Haircut. 🧠 **GaussianHair** (Luo et al. 2024; venue unverified) targets relightable rendering more than grooming. ↔️
- **2025–26, low-confidence recall:** Im2Haircut (single-view strands), TANGLED, StrandHead, SimAvatar (text→simulation-ready layered hair), Digital Salon. 2026 venues not reviewed. ↔️
- **Evaluation is synthetic:** precision/recall/F-score of strand points within paired thresholds (e.g., 2 mm/20°, 3 mm/30°) against synthetic grooms or CT-scanned wigs (CT2Hair, SIGGRAPH 2023). No benchmark scores real people's interior strands. 🧠
- **Weak cases:** curly/coily hair (curl period ≈ filter wavelength; data skews straight), the back of the head. ↔️
- **Facial hair:** Beeler et al. 2012 captured it with skin on a rig; practical pipelines mask beard and brows and fit skin beneath. 🧠
- **Products (2025):** FaceBuilder, Headshot and Mesh to MetaHuman reconstruct no strands (groom/card libraries instead); image-to-3D generators fuse hair into a shell and Gaussian avatars into uncombable splats (lib: community/ai-assisted-sculpting.md, neural-head-avatars.md). Hairmony (SIGGRAPH Asia 2024) classifies hairstyles to pick library assets. 🧠
- **Licences:** most strand code and priors are research or non-commercial; exact terms unverified. DiffLocks' official licence is confirmed non-commercial (research, education, artistic projects; commercial licences via Meshcapade) [3]; Neural Haircut, GaussianHaircut, MonoHair, Perm and HAAR licences were not found. ↔️

**Eyes**
- **Fit a near-rigid eye with tight size priors:** globe ≈24 mm, corneal radius ≈7.8 mm, visible iris (HVID) ≈11.8 mm, rotation centre 13–14 mm behind the apex (lib: blender/eyes-modeling-blender.md, sourced there). 🧠
- **The limbus is a projected circle.** One ellipse plus known radius gives the circle's 3D pose in closed form with a two-fold ambiguity (Safaee-Rad et al. 1992; Wang, Sung & Venkateswarlu 2003); an eyeball centre shared across views resolves it. 🧠
- **Ellipse shape barely encodes near-frontal gaze:** cos 10° = 0.985, a 1.5 % aspect change (~0.3 px on a 40 px iris). Use the limbus centre's offset from the head-rigid eyeball centre instead. 🧠
- **Fit medial and lateral arcs only;** lids hide top and bottom. Limbus refraction is negligible; the photographed pupil is the entrance pupil, ≈13 % larger (lib). 🧠
- **MediaPipe Face Landmarker:** 478 points (468–477 = 5 per iris) and 52 ARKit-style blendshapes including eyeLook*; good initialisers, jittery at low resolution. MediaPipe Iris assumes HVID ≈11.7 mm for metric depth (Ablavatski et al. 2020). 🧠
- **Gaze accuracy:** appearance-based networks ≈4–5° within MPIIGaze/ETH-XGaze, ≈10–11° on unconstrained Gaze360, worse cross-dataset; IR-glint trackers ≈0.5–1°; model-based limbus fits on sharp high-res photos plausibly 1–3°. ↔️
- **High-end capture:** Bérard et al. 2014 (eyes are not spheres; the iris deforms with the pupil), 2016 (parametric eye from few images), 2019 (no fixed-pivot rotation); EyeNeRF (2022); Wood et al. 2016 eye-region morphable model. 🧠
- **FLAME** has rigid eyeballs on their own 3-DoF joints, fitted to iris landmarks by trackers; blinks are poorly spanned, so trackers add eyelid blendshapes; Gaussian avatars often paint the iris onto the eyeball and control gaze weakly. ↔️
- **Lids follow gaze:** the upper margin tracks vertical gaze with an angular gain of roughly 0.6–1.0, so a down-gaze view shows a lower lid, not hooding. ↔️
- **Confounders:** glasses scale the eye by 1/(1 − dP), ≈1.2 % per dioptre at 12 mm vertex (computed); coloured contacts; strabismus (≈2–4 %); physiological anisocoria ≥0.4 mm (≈20 %). 🧠
- **An iris texture is a biometric.** 🧠

**Teeth**
- **Visible only when the lips part.** At rest adults show ~1–4 mm of upper incisor (lib: anatomy/mouth-lips-teeth.md); a smile shows ~6–10 upper teeth and few lowers; posterior teeth are always inferred. 🧠
- **Model-based teeth reconstruction** (Wu et al., SIGGRAPH Asia 2016) fits a per-tooth statistical shape-and-arrangement model, built from dental scans, to a few smile photos via edges, silhouettes and photo-consistency; Velinov et al. 2018 captured tooth appearance. 🧠
- **Orthodontic research** rebuilds whole arches from five standard *intraoral*, lip-retracted photographs (e.g., TeethDreamer, MICCAI 2024, unverified), not from portraits. ↔️
- **Best source for a consenting person: an existing intraoral scan** (STL/PLY from an iTero-, TRIOS- or Medit-class scanner) registered to the face fit; dentistry already merges face photos with scans ("digital smile design"). 🧠
- **FLAME has no teeth or mouth interior;** GaussianAvatars adds a teeth proxy (lib: neural-head-avatars.md). Photogrammetry fails on enamel translucency, saliva glints and occlusion. 🧠
- **Teeth are not white:** chroma rises toward the neck, the incisal third is translucent grey-blue; enamel IOR ≈1.62–1.63, dentin ≈1.54. 🧠

## Numbers & reference tables

**Table 1. Hair reconstruction methods** (costs and licences unverified)

| Method | Venue | Input | Cost | Artist use | Badge |
|---|---|---|---|---|---|
| HairStep, NeuralHDHair | CVPR 2023 / 2022 | 1 image | ~minutes | silhouette-level guides | 🧠 |
| DiffLocks | CVPR 2025 | 1 image | ~minutes, GPU | best recalled 1-image prior, curls | ↔️ |
| Perm / HAAR | ICLR 2025 / CVPR 2024 | latent fit / text | — | editable style prior | 🧠 |
| Neural Haircut | ICCV 2023 | phone or multi-view video | hours to a day+, 1 GPU | guides after cleanup | ↔️ |
| MonoHair | CVPR 2024 | phone video | hours | guides after cleanup | ↔️ |
| GaussianHaircut | ECCV 2024 | phone or multi-view video | hours | best recalled video method | ↔️ |
| Neural Strands, DeepMVSHair | 2022 | calibrated rig | studio | not for phones | 🧠 |

**Table 2. Hair numbers**

| Quantity | Value | Basis | Badge |
|---|---|---|---|
| Real scalp hairs | 80k–150k | lib: blender/hair-blender.md | 🧠 |
| Research outputs | 10k–100k strands × 32–128 points | method outputs | ↔️ |
| USC-HairSalon convention | 10k strands × 100 points | dataset | 🧠 |
| Strand F-score thresholds | 2 mm/20°, 3 mm/30°, 4 mm/40° | paper convention | 🧠 |
| Video for strand methods | 1–3 min orbit; ~100–300 frames used | method inputs | ↔️ |
| Guides kept for re-combing | 500–3000 curves | practice | 🧠 |

**Table 3. Eye and gaze fitting**

| Quantity | Value | Units | Population / basis | Badge |
|---|---|---|---|---|
| HVID prior | 11.8 ± 0.6 | mm | adults (lib, sourced there) | 🧠 |
| Limbus centre → rotation centre | 10.7 ± 0.6 | mm | schematic eye (lib) | 🧠 |
| Far IPD | 63 ± 3.8 | mm | adults (lib) | 🧠 |
| Kappa, temporal | 5 ± 2 | ° | adults (lib) | 🧠 |
| Appearance-based gaze error | 4–5 lab; 10–11 wild | ° | MPIIGaze, ETH-XGaze; Gaze360 | ↔️ |
| IR eye-tracker accuracy | 0.5–1 | ° | commercial devices | 🧠 |
| Upper-lid gain vs vertical gaze | 0.6–1.0 | °/° | clinical, recalled | ↔️ |
| Spectacle scaling | ∓1.2 | % per D (minus/plus) | computed, 12 mm vertex | 🧠 |
| Strabismus / anisocoria ≥0.4 mm | 2–4 / ≈20 | % | general population | 🧠 |

**Table 4. Gaze geometry** (computed: half-vergence = atan(31.5 mm/d); limbus shift = 10.7 mm × sin error) 🧠

| Camera distance | 0.3 m | 0.5 m | 1.0 m | 1.5 m | 3 m |
|---|---|---|---|---|---|
| Half-vergence per eye | 6.0° | 3.6° | 1.8° | 1.2° | 0.6° |

| Gaze error | 1° | 3° | 5° | 10° |
|---|---|---|---|---|
| Limbus shift on the face | 0.19 mm | 0.56 mm | 0.93 mm | 1.86 mm |

**Table 5. Teeth** (Wheeler-type textbook averages, adults; ancestry and sex shift all rows)

| Quantity | Value (mm) | Badge |
|---|---|---|
| Upper central incisor, crown L × W | 10.5 × 8.5 (W/L 0.75–0.85) | 🧠 |
| Upper lateral incisor | 9.0 × 6.5 (most variable; peg laterals occur) | 🧠 |
| Upper canine / 1st premolar / 1st molar | 10.0 × 7.5 / 8.5 × 7.0 / 7.5 × 10.0 | 🧠 |
| Lower central / lateral / canine | 9.0 × 5.0 / 9.5 × 5.5 / 11.0 × 7.0 | 🧠 |
| Intercanine width, upper / lower | 33–37 / 25–28 | ↔️ |
| Upper intermolar width | 50–56 | ↔️ |
| Overjet, overbite | 2–3 each | 🧠 |
| Gum display in smile | 0–2 normal; ≳3 "gummy" | ↔️ |
| Intraoral-scanner trueness, partial arch | tens of µm | ↔️ |

## Applying this to photo→3D face sculpting in Blender

**Capture (consenting subject, one session)** 🧠
1. *Shape set:* hair off forehead and ears, glasses off, neutral, lips closed. Log per frame whether the subject looked **into the lens** or **at a fixed mark**.
2. *Groom set:* hair as worn, 8–12 views including top and back, soft even light; for a strand method, a slow 360° orbit video at two heights, exposure and focus locked.
3. *Eye set:* sharpest frontal and two ¾ views with the iris ≥150–200 px across.
4. *Teeth set:* full smile (frontal, both ¾), lips retracted in a bite, lips apart at rest; ask whether a dental scan file exists.

**Hair: choose a tier** 🧠
- **Tier 0 (always):** matte, hairline and parting polylines, whorl, envelope thickness, curl class, melanin → the procedural groom in `blender/hair-blender.md`.
- **Tier 1:** a one-image prior (DiffLocks or HairStep class) for starting volume and flow; distrust its back and crown.
- **Tier 2:** a video method (GaussianHaircut, Neural Haircut, MonoHair) only for medium/long static hair, given a CUDA GPU and hours. Never ship its output as the groom.
- **Importing research strands:**
  1. Read polylines (PLY, NPZ, or USC `.data`: strand count, then per strand a point count and xyz floats).
  2. Fix units and Y-up→Z-up; align the method's bust/FLAME frame to your head by similarity ICP on the scalp.
  3. Build a `Curves` object, snap roots to your scalp, delete strands penetrating or floating > 5 mm.
  4. Decimate to 500–3000 guides, Interpolate children, re-comb hairline and parting.
- **Check in every solved camera:** mask IoU, parting, highlight band, scalp show-through.
- **Failures:** roots floating off your scalp; helmet hair; parting lost to interpolation; curls straightened; hair volume read as skull (lib: photogrammetry-heads.md).

**Eyes** 🧠
1. Place eyeballs before sculpting lids: rigid, fixed size, parented to the head, pivot bone at the rotation centre.
2. Initialise from MediaPipe iris points, then fit sub-pixel limbus edges on the medial and lateral arcs.
3. Solve eye centres once in the head frame. Per camera, aim gaze (Damped Track) at the camera if the subject looked into the lens, adding ~5° temporal kappa and the Table 4 vergence.
4. Overlay the projected limbus in every view. Fits in some views but not others → suspect per-view gaze, not eye position.
5. Sculpt lid coverage only after gaze matches: 3° of gaze error moves the limbus ~0.6 mm, read as a lid change.
6. Iris texture: polar-unwrap the sharpest frontal limbus, paint out catchlights, store pupil size per view; local and opt-in.
- **Failures:** gaze ignored and lids sculpted to compensate; globe scaled for "big eyes"; fitting through glasses or coloured contacts; convergence forced on a strabismic subject; unmodelled vergence in 0.3 m selfies.

**Teeth** 🧠
1. **With a scan:** import and decimate the STL; register to the smile photos with 4–6 point pairs (incisal edges, canine cusps, midline embrasure) through the solved cameras, refine against the teeth mask; parent uppers to the skull, lowers to the jaw bone.
2. **Without a scan:** build an arch curve from intercanine width and depth; place template teeth at widths scaled from the measured central incisor (mm via the HVID or IPD scale); set the incisal line to the smile arc, the dental midline (often 1–2 mm off the facial midline; small offsets go unnoticed by laypeople, Kokich et al. 1999), overjet and overbite.
3. **Drape the lips** over the arch with 11–15 mm soft tissue at the upper incisor (lib: anatomy/mouth-lips-teeth.md). Photo shows incisor at rest but the model does not → lip too long or teeth too high.
4. **Shade:** subsurface, off-white, translucent incisal third, darker into the buccal corridors.
- **Failures:** arch too narrow (teeth sink inside the corners); teeth too far forward (pout); identical white teeth; teeth fused to lips; lower arch not following the jaw.

## Algorithmic implications

**Masks:** exclude hair, brows, beard, eyes, teeth and inner mouth from all skin terms; each sub-model has its own residuals and object. 🧠

**Eye sub-model** 🧠
- *Per subject:* centres c_L, c_R in the head frame. Priors: mirror symmetry about the mid-sagittal plane σ 1 mm; IPD 63 mm σ 3.8; apex 16 mm ahead of the lateral orbital rim σ 2.5. Globe and cornea fixed from the eyes note; free HVID (11.8, σ 0.6) only with ≥ 3 sharp views.
- *Per view:* yaw/pitch per eye. Gaze prior by capture tag: "into the lens" → camera direction + kappa, σ 3°; "fixed mark" → shared across views, σ 1°; untagged σ 15°. Vergence coupling σ 1°; flag strabismus when the residual exceeds 3° in ≥ 2 views, then decouple that eye.
- *Residuals:* point-to-projected-circle on limbus edge samples, σ 0.5–1 px; MediaPipe iris centre σ = 0.05 × iris diameter in px; drop arc samples within 1 px of a lid edge.
- *Ambiguity:* try both circle solutions; keep the one whose centre agrees across views.
- *Lid coupling:* expected upper-margin shift = g · Δpitch · 12 mm · π/180, g ~ N(0.8, 0.2²); lid margin 0–0.3 mm off the eye surface (lib).

**Teeth sub-model** 🧠
- Upper set rigid in the skull frame; lower set driven by the template's jaw joint (FLAME jaw pose).
- Priors (Table 5): intercanine width 35 mm σ 2; intermolar 53 σ 3; anterior arch depth ≈8–10 mm ↔️; per-tooth widths σ 0.5 (lateral incisors 0.7); incisal edge 2.5 mm below stomion at rest σ 1.5; overjet 2.5 σ 1; overbite 2.5 σ 1.5; proclination σ 5°; dental midline offset 0 σ 1.5 mm.
- Residuals: incisal-edge polyline, embrasures, gingival margin (σ 1–2 px), teeth-mask IoU. Sapiens parses teeth; CelebAMask-HQ has only "mouth" (lib: monocular-depth-normals.md).
- Constraint: inner lip surface ≥ 0.5 mm outside labial enamel. Scan path: similarity from point pairs, then trimmed ICP to photo edges; never scale a scan beyond unit conversion.

**Hair interface** 🧠
- Skull one-sided under hair: scalp signed distance to the hair hull ≤ −t (2 mm visible, 0 bald), log-normal offset prior by hair class (lib: hair-blender.md).
- Strand plug-in out of process, polylines only. Acceptance gates: roots ≤ 1 mm from scalp after snapping; zero penetrations after Shrinkwrap; per-view hair-mask IoU ≥ 0.85; median orientation error ≤ 20° where confidence > 0.5. Fail → Tier 0.
- Guide decimation: farthest-point sampling on (root UV, first 3–5 PCA coefficients of strand shape).

**Sidecar JSON:** eye centres, HVID, per-view gaze, strabismus flag, arch parameters, tooth widths, scan transform, hair tier and gate scores. 🧠

## Disagreements, myths & open questions

- **"Strand reconstruction from photos is solved."** No: the interior is invented, scores are synthetic, curls and the back of the head lag. ↔️
- **Best video method:** GaussianHaircut vs Neural Haircut vs MonoHair rankings depend on dataset and metric, and 2025–26 feed-forward methods may supersede all three. ↔️
- **Iris as a ruler:** 11.7 (MediaPipe) vs 11.8 mm (clinical pool) hardly matters; SD 0.5–0.8 mm means ±4–7 % scale error, and a blurred photo limbus is not clinical white-to-white. ↔️
- **Appearance-based gaze is too coarse for lid placement:** 4–10° ≈ 0.75–1.9 mm limbus shift. ↔️
- **Myth: the eye is a sphere on a fixed pivot.** The sphere is fine for sculpting; the fixed pivot is not fine for a close-up eye rig (Bérard 2019). 🧠
- **Golden-proportion teeth** do not describe natural dentitions; never a prior (lib). ↔️
- **A dental scan is health data** (special-category under GDPR-type law) even with consent: local storage, deletable. 🧠
- **Open:** strand-code licences; real-photo strand benchmarks; a permissive teeth shape model; tooth widths by ancestry; lid–gaze gain by age; Blender 5.x Alembic/USD curve import. ↔️

## Sources

Numbered sources below were added in the 2026-11-20 verification; most facts remain unsourced; "(lib: …)" sibling notes hold sourced versions of shared figures.

1. Rosu et al., DiffLocks, arXiv 2505.06166 — https://arxiv.org/abs/2505.06166v1
2. DiffLocks, CVPR 2025 open access — https://openaccess.thecvf.com/content/CVPR2025/html/Rosu_DiffLocks_Generating_3D_Hair_from_a_Single_Image_using_Diffusion_CVPR_2025_paper.html
3. DiffLocks software licence — https://difflocks.is.tue.mpg.de/license.html

**Further reading (by name, not yet linked)**
- Hair capture: Paris, Briceño & Sillion, SIGGRAPH 2004; Paris et al., "Hair Photobooth", 2008; Luo, Li & Rusinkiewicz, "Structure-Aware Hair Capture", 2013; Beeler et al., facial hair and skin, SIGGRAPH 2012; Shen et al., "CT2Hair", 2023
- Single image: Hu et al., hairstyle database, SIGGRAPH 2015; Chai et al., "AutoHair", 2016; "HairNet", ECCV 2018; "NeuralHDHair", CVPR 2022; Zheng et al., "HairStep", CVPR 2023; Rosu et al., "DiffLocks", CVPR 2025
- Multi-view and video: Rosu et al., "Neural Strands", ECCV 2022; "DeepMVSHair", 2022; Sklyarova et al., "Neural Haircut", ICCV 2023; Wu et al., "MonoHair", CVPR 2024; "Dr.Hair", CVPR 2024; Zakharov et al., "Human Hair Reconstruction with Strand-Aligned 3D Gaussians", ECCV 2024; Luo et al., "GaussianHair", 2024
- Hair priors: "GroomGen", 2023; Sklyarova et al., "HAAR", CVPR 2024; He et al., "Perm", ICLR 2025; Meishvili et al., "Hairmony", 2024
- Eyes: Bérard et al., eye capture (2014), parametric eye (2016), eye rigging (2019); Li et al., "EyeNeRF", 2022; Wood et al., eye-region morphable model, ECCV 2016; Safaee-Rad et al., IEEE T-RA 1992; Wang, Sung & Venkateswarlu, ICCV 2003; MPIIGaze, ETH-XGaze, Gaze360, L2CS-Net; Ablavatski et al., MediaPipe Iris, 2020
- Teeth: Wu et al., "Model-Based Teeth Reconstruction", SIGGRAPH Asia 2016; Velinov et al., teeth appearance, 2018; *Wheeler's Dental Anatomy, Physiology and Occlusion*; Kokich et al., 1999; Bishara et al., arch-width studies

## Verification log (2026-11-20)

- **Strand code/priors mostly research or non-commercial licences:** partly confirmed. DiffLocks licence is non-commercial, commercial via Meshcapade [3]. Neural Haircut, GaussianHaircut, MonoHair, Perm, HAAR licences: unconfirmed (no usable evidence found). Stays ↔️.
- **Wheeler-type crown sizes and intercanine widths (Table 5):** unconfirmed; searches found only book listings (https://shop.elsevier.com/books/wheelers-dental-anatomy-physiology-and-occlusion/nelson/978-0-323-63878-4), no values. Stays 🧠.
- **Upper-lid gain 0.6–1.0, g ~ N(0.8, 0.2²):** unconfirmed. Only qualitative downgaze lid-lowering and mm-scale changes found (https://pubmed.ncbi.nlm.nih.gov/8090463/); no degrees-per-degree gain. Stays ↔️.
- **DiffLocks CVPR 2025, single image, curly hair, ~40K Blender-rendered styles:** confirmed (one source family: paper/arXiv/CVPR page) 📄 [1][2]. "Strongest single-image prior" is a judgment, kept ↔️ in Table 1. Im2Haircut, TANGLED, StrandHead, SimAvatar: unconfirmed.
