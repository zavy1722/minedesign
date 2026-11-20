# 3D morphable models: survey

> A 3D morphable model (3DMM) is a template mesh in dense correspondence with many registered scans, plus linear statistics: x = x̄ + U_id·diag(σ_id)·β + U_exp·diag(σ_exp)·ψ, with jaw, neck and eye joints in FLAME-type models. Mesh density says nothing about statistical capacity. The Basel Face Model (BFM) has 53,490 vertices but only 199 components from 200 people. FLAME has 5,023 vertices and 300 components from about 3,800 people. For sculpt-ready likeness, models differ mainly in four things:
>
> - licence;
> - coverage (face, full head, mouth interior);
> - training population;
> - topology.
>
> No large-population model is plainly free for commercial use. ICT-FaceKit (MIT) is the main permissive exception, and "FLAME 2023 Open" is CC BY 4.0 per the official FLAME site [1] (verified; the other FLAME releases stay non-commercial). Use a 3DMM as a *prior and initialiser* behind an adapter. Ship a CC0 or MIT template, and treat research models as user-supplied plug-ins.
>
> Evidence status: 0 ✅ / 3 📄 / 57 🧠 / 24 ↔️ — 🧠 items are queued for web verification; 4 claims checked 2026-11-20 (see Verification log).

*No web harvest or earlier draft existed for this topic, so nothing here is web-sourced. Where a sibling note cites a source for a related claim, it is named in backticks. Per-model counts are in Table 1.*

## Key facts

**Concept and lineage**
- **Blanz & Vetter (SIGGRAPH 1999)** set the pattern every later model refines:
  - 200 Cyberware laser scans, 100 women and 100 men;
  - shape and texture PCA;
  - correspondence by optical flow;
  - analysis-by-synthesis fitting to photos.

  Later models change the data, the registration, the basis or the fitting. 🧠
- **Registration defines the model.**
  - BFM 2009 and LSFM: non-rigid ICP (Amberg et al. 2007).
  - BFM 2017: Gaussian-process registration (Scalismo).
  - FLAME: co-registration, with the model in the loop.

  Registration error shows up as blurred lips, eyelids and nostrils in the mean and the leading components. 🧠
- **Capacity ≠ density.** PCA on n scans yields at most n − 1 non-zero components, and the tail ones are mostly registration noise. 🧠
- **Models are compared on three measures** (Styner et al. 2003), each plotted against the number of components K:
  - compactness: how much variance K components capture;
  - generalisation: error when reconstructing held-out scans;
  - specificity: how realistic random samples look.

  🧠
- **Expression is modelled in two ways.**
  - Additive: BFM 2017, FLAME and ICT-FaceKit add expression offsets to the identity shape.
  - Multilinear: FaceWarehouse and FaceScape use a bilinear tensor, so expression depends on identity.

  FLAME also rotates the jaw, neck and eyes with linear blend skinning (LBS) and pose correctives. 🧠

**Basel family**
- **BFM 2009** 🧠:
  - Training set: 200 neutral, mostly European adults (structured light).
  - Mesh: face, ears and upper neck; no eyeballs and no mouth interior.
  - Colour is stored per vertex.
  - Extras: a 4-segment model and attribute directions (age, weight, height, sex).
- **BFM 2017** re-registers the *same* 200 identities and adds a 100-component expression model 🧠. It ships `face12` and `bfm` crops in "nomouth" variants. ↔️
- **BFM 2019** adds a full-head variant. I do not reliably recall its other changes. ↔️
- **Regressors use BFM crops.** 3DDFA and Deep3DFaceRecon crop BFM 2009 and take their expression bases from FaceWarehouse (`expression-neutralization.md`). 🧠

**FLAME family**
- **Model structure** 🧠:
  - Covers head, neck and eyeballs; no teeth or mouth interior.
  - Five 3-DoF joints (root, neck, jaw and two eyes) plus pose-corrective blendshapes.
  - Bases are scaled so that β and ψ have roughly unit variance.
  - Identity comes from CAESAR scans; expression from D3DFACS plus MPI 4D captures, about 33k registered scans in total.
- **Releases.**
  - FLAME 2017 came in male, female and generic versions; fit the generic one unless you know the sex. 🧠
  - Most regressors (DECA, EMOCA, MICA) use FLAME 2020 (`single-image-regression.md`). 🧠
  - VHAP uses FLAME 2023 (`multi-view-fitting.md`), which reportedly revises the eyelids. ↔️
  - A CC BY 4.0 "FLAME 2023 Open" exists: the official site says it is released under CC-BY-4.0 and allows commercial use with attribution; all other FLAME models remain non-commercial [1] (corrected in verification). 📄
- **Ecosystem** 🧠:
  - landmark embeddings: 51 static points, 17 yaw-binned contour points, and about 105 MediaPipe points used by MICA and metrical-tracker;
  - region masks;
  - albedo models built from BFM and from FFHQ;
  - a BFM→FLAME converter by Bolkart;
  - a FLAME-compatible head in SMPL-X.
- **MICA** registered eight scan datasets (about 2,300 subjects) into FLAME topology. This gives FLAME the most *metric* identity supervision of any public model. 🧠

**Large-population and full-head models**
- **LSFM** (Booth et al. 2016/2018) is built from about 9,663 3dMD scans of Science Museum (London) visitors, children included. Besides the global model it releases age-bracket and ethnicity-specific (White, Chinese, Black) sub-models. 🧠
- **LYHM** (Dai et al. 2017) is built from Headspace, whose subjects wore tight caps. It is the only mainstream model with cranium shape not hidden by hair. 🧠
- **UHM** (Ploumpis et al. 2019/2021) fuses LSFM face statistics with LYHM cranium statistics by covariance completion. The TPAMI version adds ears (York Ear Model), eyes and the mouth interior. 🧠
- **Surrey Face Model** (Huber et al. 2016): a multi-resolution academic model, with the permissively licensed `eos` fitter. 🧠

**Population-specific and production models**
- **FaceWarehouse** (Kinect RGB-D) and **FaceScape** (68-DSLR array, 4K displacement maps) are bilinear identity × expression models. FaceScape is mostly Chinese. ↔️ (component counts)
- **ICT-FaceKit** (USC ICT 2020, Light Stage) 🧠:
  - artist-style quad topology;
  - eyes, lacrimal and occlusion meshes, teeth, gums and tongue;
  - about 53 shapes that follow ARKit naming.

  It is the closest public model to a production rig. Counts and data provenance are ↔️.
- **FaceVerse** (Tsinghua 2022) is a PCA base with a neural detail layer, from mixed RGB-D and scan data of East Asian subjects. ↔️
- **HIFI3D++** (Tencent; REALY, ECCV 2022) merges FaceScape, Headspace and HIFI3D into about 1,957 identities, which makes it the most population-balanced public PCA I know of. ↔️

**Non-linear successors.** NPHM and MonoNPHM, i3DMM, Gaussian parametric heads and non-linear mesh 3DMMs (Tran & Liu 2018) can generalise better. They lack fixed topology or interpretable controls, so treat them as initialisers or evaluators, not sculpt bases (`neural-head-avatars.md`). 🧠

**Licences** ↔️
- BFM, FLAME, LSFM, LYHM, UHM, FaceScape and FaceWarehouse are free for non-commercial research after registration.
- Commercial terms are negotiated: Basel for BFM; MPI or Meshcapade for FLAME.
- Fitted meshes and transferred bases are derivatives, so assume they inherit these terms.

## Numbers & reference tables

**Table 1: Catalogue** (counts as recalled; assert them at load time)

| Model (year) | Vertices | Coverage | Identity / expression basis | Training data | Population | Licence (verify) | Status |
|---|---|---|---|---|---|---|---|
| Blanz–Vetter (1999) | ~70k, not released | face | PCA ≤ 199 | 200 laser scans | 100 f / 100 m, European | not released | 🧠 |
| BFM 2009 | 53,490 (tris) | face, ears, upper neck | 199 shape + 199 colour / none | 200 structured-light scans | mostly European, ~8–62 y | NC research | 🧠 |
| BFM 2017 | face12 ≈ 28.6k; bfm ≈ 53.1k | face (± ears) | 199 + 199 / 100 | same 200 + small expression set | as 2009 | NC research | ↔️ |
| BFM 2019 | face12, bfm, full head | up to full head | not recalled | not recalled | – | NC research | ↔️ |
| FaceWarehouse (2014) | 11,510 | face, front of head | bilinear ≈ 50 × 25–47 | 150 people × 20 expressions, Kinect | 7–80 y, mixed | research, on request | ↔️ |
| LSFM (2016) | not recalled | face | ≈ 158 + sub-models | ≈ 9,663 3dMD scans | incl. children, ≈ 80 % White | NC, on request | 🧠 |
| FLAME 2017/2020 | 5,023; 9,976 tris | head, neck, eyeballs | 300 / 100 + 15 pose | ≈ 3,800 CAESAR (identity) + 4D (expression) | 18–65 y, N. America + Europe | NC; commercial via MPI or Meshcapade | 🧠 |
| FLAME 2023 | 5,023 | same | 300 / 100 (verify) | not recalled | – | NC; "FLAME 2023 Open" is CC BY 4.0 [1] (corrected in verification) | 📄 |
| LYHM (2017) | not recalled | full head + cranium | global + age/sex sub-models | ≈ 1,200 of ≈ 1,500 Headspace | UK, children–elderly | academic | 🧠 |
| UHM (2019/21) | not recalled | head + ears, eyes, mouth | LSFM ⊕ LYHM | ≈ 9.7k + ≈ 1.2k | as parents | academic NC | 🧠 |
| Surrey FM (2016) | 3,448 (low res) | face | not recalled | ≈ 169 scans | not recalled | academic | 🧠 |
| FaceScape (2020) | ≈ 26k + 4K displacement | face, front of head | bilinear ≈ 50 × 52 (v1.6) | 938 people × 20 expressions = 18,760 | mostly Chinese adults | NC, application | ↔️ |
| ICT-FaceKit (2020) | quads, count not recalled | head, eyes, mouth interior | ≈ 100 / 53 | Light Stage | diverse | MIT | ↔️ |
| FaceVerse (2022) | not recalled | head | PCA + neural detail | ≈ 60k RGB-D frames + ≈ 2k scans, ≈ 128 people | East Asian | NC (believed) | ↔️ |
| HIFI3D++ (2022) | ≈ 20,481 | face, front of head | ≈ 526 | ≈ 1,957 identities | mixed, Asian-weighted | research | ↔️ |
| NPHM (2023) | implicit SDF | head | latent identity + expression | ≈ 5,200 scans, ≈ 255 people | mostly European | NC | 🧠 |

**Table 2: Load-time assertions** (fail loudly on mismatch)

| Mesh | Expected vertices | Units | Axes | Status |
|---|---|---|---|---|
| FLAME (all releases) | 5,023, of which ≈ 1,092 are eyeball vertices (select by mask) | m | Y-up, face toward +Z | 🧠 |
| BFM 2009 | 53,490 | sub-mm, commonly read as µm | Y-up, face toward +Z | ↔️ |
| BFM 2017/2019 | ≈ 28.6k (face12) / ≈ 53.1k (bfm) | mm | Y-up, face toward +Z | ↔️ |
| 3DDFA BFM crop / Deep3DFaceRecon crop | 53,215 / 35,709 | as BFM 2009 | as BFM | 🧠 |
| SMPL-X | 10,475 | m | Y-up | 🧠 |
| Any model, after unit conversion | adult zygion–zygion width ≈ 125–150 mm | mm | – | 🧠 |

**Table 3: Plausibility of ‖β‖² for a population sample with β ~ N(0, I_K)** (χ²_K quantiles, Wilson–Hilferty approximation)

| K | 1 % | median | 99 % | 99.9 % | Status |
|---|---|---|---|---|---|
| 10 | 2.5 | 9.3 | 23.2 | 29.8 | 🧠 computed |
| 50 | 29.7 | 49.3 | 76.2 | 86.7 | 🧠 computed |
| 100 | 70.0 | 99.3 | 135.8 | 149.5 | 🧠 computed |
| 300 | 246.0 | 299.3 | 359.9 | 381.5 | 🧠 computed |

**Table 4: Resolution vs sculpting** (edge length estimated from vertex count and surface area; order of magnitude only)

| Base | Typical edge on the face | Multires levels to reach ≈ 0.5 mm | Notes | Status |
|---|---|---|---|---|
| FLAME | ≈ 3–6 mm | 3 (≈ 480k quads from 9,976 tris) | Catmull–Clark on triangles leaves poles and lumps; transfer to a quad template first | 🧠 |
| BFM | ≈ 1 mm | 1 | triangles; no UVs in 2009 (per-vertex colour) | 🧠 |
| FaceScape / HIFI3D / ICT | ≈ 1.5–3 mm | 2 | ICT has quads and UVs | ↔️ |

## Applying this to photo→3D face sculpting in Blender

1. **Choose by licence, then coverage, then population.** 🧠
   - Client work: the CC0 MPFB2 base (`blender-face-addons.md`), or ICT-FaceKit once its MIT terms and data provenance are confirmed.
   - Research or personal work: FLAME (head, eyes, jaw) or BFM (dense face).
   - Tag every asset with `{licence, commercial_ok}`.
2. **On import, assert vertex count, units and axes (Table 2), then measure face width.** A face 0.15 mm or 150 m wide is a unit bug. FLAME needs ×1000 to work in mm. 🧠
3. **Do not sculpt on raw FLAME.** At 3–6 mm spacing, the eyelid margin, alar groove and vermilion border are each 1–2 edges wide. 🧠
   - Fit FLAME.
   - Transfer the fit to a quad template through a fixed barycentric correspondence.
   - Add Multires.
   - Keep the FLAME-topology fit as a shape key so you can re-fit later.
4. **Swap the eyeballs and add a mouth interior.** Fit the eyelids to FLAME's coarse spheres, then replace them with proper eye assets (`eyes-modeling-blender.md`). If the mouth will be open, start from ICT-FaceKit, which has teeth and gums. 🧠
5. **Treat ears, scalp and occiput as placeholders.** No mainstream 3DMM fits ears well from photos (`ear.md`). The cranium under hair is a guess. 🧠
6. **Neutralise before sculpting identity.** Set ψ = 0 and jaw ≈ 0, and check that the lips close without stretch. BFM 2009 has no expression basis, so a smile *becomes* identity (`expression-neutralization.md`). 🧠
7. **Check mean-face bias in profile.** Regularised fits flatten nose projection, eye depth, chin and brow ridge. Overlay the silhouette from the solved profile camera before sculpting (`likeness-mistakes.md`). 🧠
8. **Match the prior to the sitter.** 🧠
   - BFM, FLAME and LSFM skew European.
   - FaceScape, FaceVerse and HIFI3D skew East Asian.
   - Children fall outside FLAME's adult range.

   For sitters outside the prior's population, expect larger residuals and widen σ. ↔️
9. **Never copy coefficients between models.** Convert by fitting geometry. 🧠

## Algorithmic implications

- **Adapter schema.** Each model provides:
  - geometry: `mean (N×3, mm)`, `U_id`, `sigma_id`, and optionally `U_exp`, `sigma_exp`, joints, LBS weights and pose correctives;
  - correspondence: `landmark_embeddings {scheme: (face_idx, bary)}`, `region_masks` and `uv`;
  - metadata: `units`, `axis_matrix`, `licence`, `commercial_ok` and `population_tag`.

  Normalise at load so that β ~ N(0, I). Releases differ: some store σ, some σ², and FLAME pre-scales its basis. Self-test: +1 on component 1 should move vertices by an RMS of about 2–8 mm. 🧠
- **Prior.** Use ½‖β‖². Whiten residuals by the landmark σ (Table 5 of `multi-view-fitting.md`: 1–1.5 % of inter-ocular distance for crisp points); then λ = 1 is the MAP estimate. For sitters outside the population, scale σ_id by about 1.5 (a guess). ↔️
- **Choose K from the constraint count.** 🧠
  - Sparse landmarks, 3–9 views: K ≈ 30–50.
  - Dense multi-view or photometric fitting: K ≈ 100–300.
  - Schedule K as 10 → 50 → full.
  - Beyond that, add Laplacian/RBF per-vertex offsets (≲ 3–5 mm).
- **‖β‖² gate** (Table 3). 🧠
  - Above the 99.9 % quantile, flag the fit: it is implausible, or the sitter is outside the population.
  - A MAP fit sits far *below* the median because unconstrained modes shrink to 0. That signals under-constrained modes, not an error.
  - Report a per-region Mahalanobis distance (marginal covariance U_R U_Rᵀ) to catch an over-flattened nose.
- **Expression and pose.** 🧠
  - Neutral-tagged views: ψ ~ N(0, 0.3²) and jaw σ ≈ 2–3°.
  - Expressive views: ψ ~ N(0, 1) per view, with β shared across views.
  - Eye rotations are nuisance parameters, bounded to ±30°.
- **Scale.** Fit a global scale with prior N(1, 0.04–0.05²) only when a metric cue exists. Otherwise the calibrated focal length fixes it; never let β absorb it. 🧠
- **Exact basis transfer.** Let W be a sparse barycentric map from your template to the 3DMM surface. Then x̄′ = W x̄ and U′ = (W ⊗ I₃) U, and the prior stays N(0, I). 🧠 This puts a FLAME or BFM prior on an MPFB2 or ICT template without remeshing at run time. The transferred basis is a licence derivative: compute it locally from user-supplied files and never ship it. ↔️
- **Multiple models.** Fit each model separately in the same camera frame and compare reprojection residuals; never average coefficients. 🧠
- **Symmetry.** PCA bases contain real asymmetric modes. Use a soft bilateral prior (1.5–3 mm), not a symmetric projection. 🧠

## Disagreements, myths & open questions

- **"More vertices means more accuracy."** BFM has 53k vertices but only 199 statistical degrees of freedom. 🧠
- **"A large N removes bias."** LSFM is about 80 % White, and CAESAR covers adults only. 🧠
- **"FLAME is open source."** The code is open, but the model files are licence-gated. The 2023 "Open" variant is CC BY 4.0 [1], but earlier releases remain NC (corrected in verification). 📄
- **"A 3DMM fit is the likeness."** A scale-fitted *average* FLAME scores about 1.5 mm mean on NoW (sourced in `single-image-regression.md`). Whatever makes the face recognisable lies in the residual the fit smooths away. 🧠
- **Additive vs multilinear expression.** It is unresolved how much person-specific expression leaks into β. ↔️
- **Linear vs neural models.** Neural models generalise better, but sculptors need fixed topology, so PCA plus free offsets stays the practical default. ↔️
- **Open questions (time-sensitive, as of 2026-11)** ↔️:
  - what FLAME 2023 and its "Open" variant contain (terms are CC BY 4.0 [1]; contents vs. the original 2023 model still unchecked);
  - what changed in BFM 2019;
  - whether LSFM, LYHM and UHM are still distributed;
  - ICT-FaceKit counts and training-data consent;
  - the FaceVerse and HIFI3D++ licences;
  - whether any 2025–26 head model is large-population and commercially licensable.

## Sources

1. FLAME model license page (FLAME 2023 Open = CC-BY-4.0): https://flame.is.tue.mpg.de/modellicense.html (homepage: https://flame.is.tue.mpg.de/)
2. What does 2D geometric information really tell us about 3D face shape? (cites BFM 2009 with 53,490 vertices): https://arxiv.org/pdf/1708.06703

No other harvested URLs were provided. Sibling notes with sourced related claims:
- `reconstruction/single-image-regression.md`
- `reconstruction/multi-view-fitting.md`
- `blender/import-export-scans.md`
- `blender/blender-face-addons.md`

**Further reading (by name, not yet linked)**
- Blanz & Vetter, "A Morphable Model for the Synthesis of 3D Faces", SIGGRAPH 1999
- Paysan et al., "A 3D Face Model for Pose and Illumination Invariant Face Recognition" (BFM), AVSS 2009
- Gerig et al., "Morphable Face Models – An Open Framework" (BFM 2017), FG 2018
- Lüthi et al., "Gaussian Process Morphable Models", IEEE TPAMI 2018
- Li, Bolkart, Black, Li & Romero, "Learning a model of facial shape and expression from 4D scans" (FLAME), SIGGRAPH Asia 2017
- Booth et al., "A 3D Morphable Model learnt from 10,000 faces" (LSFM), CVPR 2016; "Large Scale 3D Morphable Models", IJCV 2018
- Dai, Pears, Smith & Duncan, "A 3D Morphable Model of Craniofacial Shape and Texture Variation" (LYHM), ICCV 2017
- Ploumpis et al., "Combining 3D Morphable Models: A Large Scale Face-and-Head Model", CVPR 2019; TPAMI extension 2021
- Cao et al., "FaceWarehouse", IEEE TVCG 2014
- Yang et al., "FaceScape", CVPR 2020
- Li et al., "Learning Formation of Physically-Based Face Attributes" (ICT-FaceKit), CVPR 2020
- Wang et al., "FaceVerse", CVPR 2022
- Chai et al., "REALY: Rethinking the Evaluation of 3D Face Reconstruction" (HIFI3D++), ECCV 2022
- Huber et al., "A Multiresolution 3D Morphable Face Model and Fitting Framework", VISAPP 2016
- Giebenhain et al., "Learning Neural Parametric Head Models", CVPR 2023
- Tran & Liu, "Nonlinear 3D Face Morphable Model", CVPR 2018
- Amberg, Romdhani & Vetter, "Optimal Step Nonrigid ICP Algorithms for Surface Registration", CVPR 2007
- Styner et al., "Evaluation of 3D correspondence methods for model building", IPMI 2003
- Egger et al., "3D Morphable Face Models — Past, Present and Future", ACM TOG 2020

## Verification log (2026-11-20)

| Claim | Outcome | Source |
|---|---|---|
| FLAME 2017/2020 NC only; "FLAME 2023 Open" CC BY 4.0 | corrected: Open variant confirmed as CC-BY-4.0 (commercial use allowed with attribution); all other FLAME models NC. Contents vs original 2023 model unconfirmed | https://flame.is.tue.mpg.de/modellicense.html ; https://flame.is.tue.mpg.de/ |
| ICT-FaceKit MIT, ~100 id / 53 expression shapes, quads, eyes/teeth/gums/tongue | unconfirmed (only a secondary news post said MIT, and cited >150 blendshapes; no repo LICENSE seen) | none usable |
| Units and vertex counts (FLAME m; BFM 2009 sub-mm/µm; BFM 2017 face12 28,588 / bfm 53,149) | unconfirmed; only BFM 2009 = 53,490 vertices and "absolute distance units" seen, no unit named, no 2017 counts | https://arxiv.org/pdf/1708.06703 |
| FLAME basis pre-scaled to unit variance; BFM orthonormal PCs with separate sigma/variance | unconfirmed (no source on shapedirs/shapeEV/pcaVariance conventions) | none usable |
