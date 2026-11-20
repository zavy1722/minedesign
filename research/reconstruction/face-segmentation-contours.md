# Face, hair and skin segmentation for silhouettes and occlusion

> Silhouettes recover what landmarks miss: the profile line (g′–n′–prn–sn–ls–li–pg′), the jaw and cheek outline, and ear protrusion. Segmentation should supply *semantics* (which stretch of an outline is skin against background, and which is hair, beard, glasses or clothing); sub-pixel image edges should supply *position*. For a commercial GPL add-on, only a few models are clean: MediaPipe's selfie, multiclass and hair segmenters (tiny; weight terms to re-check), SAM/SAM 2 and U²-Net/IS-Net (Apache-2.0), and BiRefNet (MIT weights, research training data). Every public face parser with ear, brow, glasses and earring classes (BiSeNet, FaRL, SegFace) inherits non-commercial CelebAMask-HQ/LaPa terms, and BRIA's RMBG is non-commercial outright. Masks should become normal-only contour residuals, each with its own σ and a *kind*: two-sided for skin|background, one-sided outer bound for hair, beard and hats. Correspondences are re-picked every iteration, and the profile soft-tissue points come from ordered curvature analysis of the silhouette.
>
> Evidence status: 0 ✅ / 0 📄 / 52 🧠 / 14 ↔️ — 🧠 items are queued for web verification.

This topic had no harvest file and no earlier draft, so no URL is cited. Related material in this library: `ethics/licences-tos.md` (BiSeNet/CelebAMask-HQ and SAM licence rows, taint propagation), `blender/blender-python-ml-deps.md` (worker process, wheels, onnxruntime size), `reconstruction/landmark-detection.md` and `deformation-fitting-math.md` (contour σ, landmark marching), `monocular-depth-normals.md` (Sapiens, DAViD), `anatomy/forehead-brow-temple-hairline.md` and `anatomy/jaw-chin-neck.md` (profile norms). The engine's current contour fitter is `face3d/fit/silhouette.py`.

## Key facts

**What a mask edge means**
- **The silhouette is an envelope, not a section.** It is the occluding contour, where view rays graze the surface (n·v = 0). In profile it runs over the philtral columns rather than the philtral groove, over the bosses of a cleft chin, and over the lateral brow ridges when the glabella is recessed. Midline points therefore sit 0–2 mm *behind* the silhouette. Silhouette-to-silhouette fitting is unbiased; silhouette-derived "midline landmarks" are not. 🧠
- **Sliding is first-order free.** Moving the contact point along the contour generator changes the projected outline only to second order, so a fitter may re-pick the silhouette vertex each iteration and treat it as fixed in between. 🧠
- **Boundary error is resolution-bound.** Networks typically miss the boundary by 1–3 *output* pixels. A 256 px model on a 2000 px head crop is therefore 8–24 px off at full resolution until the boundary is refined. Region metrics (mIoU, F1) hide systematic shifts of a few pixels; boundary F-score at a 1–2 px tolerance is the relevant metric, and is rarely reported. 🧠
- **Gamma bias.** In sRGB the 50 % crossing of a blurred high-contrast edge sits about 0.78–0.79 σ_blur toward the darker side (sRGB 0.5 ≈ linear 0.214). Fair skin on a dark backdrop grows the silhouette; a dark face on white shrinks it. Linearise before sub-pixel edge localisation. 🧠 (arithmetic)
- **False edges.** Under top light the submandibular cast shadow sits *below* the jaw contour. Hair shadows on the forehead and the shadow terminator on the neck are not contours either, so edge snapping must take the first strong edge from the face side. 🧠
- **Silhouettes ignore makeup and albedo**, which is why they carry likeness. They fail where foreground and background are similar (dark hair on a dark backdrop), and phone "portrait mode" corrupts them with its own segmentation and blur. 🧠

**Region reliability**
- **Forehead–hairline.** In frontal views the skin|hair boundary is an internal boundary, not a contour; it locates trichion and the hair shape, not geometry. Datasets label baby hair, receding and thinning hairlines inconsistently, by several pixels at 512 px. In profile the forehead silhouette is skin only where no fringe covers it. 🧠
- **Temples.** Above the zygomatic arch the frontal head outline is hair in most people. The temporal skin contour is hidden 5–30 mm or more inside it, so it gives only an outer bound. 🧠
- **Beard–jaw.** A full beard hides the mandibular contour and pg′/gn′ and moves the profile chin forward by the beard length. Stubble (under about 3 mm) reads as skin but biases the contour outward by about 0.5–2 mm. Datasets disagree on whether a beard is "hair" or "skin". ↔️
- **Ears.** In frontal views the helix is a strong contour for ear protrusion, but hair, earrings and glasses arms interrupt it. Face-parser ear classes score lower than skin, and earring classes are long-tail (low F1). In profile the ear is an internal object; segment it separately or trace it by hand. 🧠
- **Face-skin vs body-skin.** MediaPipe multiclass separates face skin from neck skin. Under a level head that boundary roughly follows the jaw contour, but its semantics are undocumented: snap it to an image edge and inflate σ. ↔️

**Models (licences are time-sensitive: re-check per release)**
- **MediaPipe Image Segmenter models.** *Selfie* (binary; 256×256 and 144×256; about 0.25 MB). *Selfie multiclass* (256×256; background, hair, body-skin, face-skin, clothes, others/accessories; roughly 16 MB). *Hair segmenter* (512×512, about 0.8 MB; the legacy graph fed the previous mask as a 4th channel, so pass zeros for stills). Code is Apache-2.0; weight terms come from per-model cards, which differ and have changed. ↔️ They are trained for selfie effects, so boundaries are smooth and strands are missed, but they are fast and need no face detector, so they still run in full profile. 🧠
- **SAM (2023) and SAM 2/2.1 (2024).** Code and checkpoints are Apache-2.0, and SA-V is CC BY 4.0. Prompts from landmarks (points, box) give person, head or hair masks; multimask output resolves the ambiguity. Edges are good, but not matting-grade. SAM 2's video mode can carry one prompt across a turntable sequence. MobileSAM (Apache-2.0, about 40 MB) is the CPU-friendly encoder. 🧠
- **SAM 3** (Meta, Nov 2025; text-prompted "concepts" such as *beard* or *glasses*). It ships under a custom SAM licence with gated checkpoints, not Apache, and has roughly 0.85 B parameters, so it is impractical on CPU. Verify before any use. ↔️
- **BiRefNet** (high-resolution dichotomous segmentation). Code and HF weights are MIT, with a 1024 px general model, lite, portrait/matting and 2K variants. It gives the best hair-edge detail of the permissive set. Training mixes DIS5K, HRSOD, UHRSD, P3M and others, all research datasets: weights clean, data taint contested. ↔️
- **U²-Net / u2netp / IS-Net.** Code and weights are Apache-2.0; the models were trained on DUTS-TR and DIS5K (research) ↔️. **rembg** is MIT but downloads a zoo that mixes clean and NC models (it includes BRIA). Its deps (pymatting → numba/scipy, scikit-image) are heavy, so reuse whitelisted ONNX files rather than the package. 🧠
- **RMBG-1.4 / 2.0 (BRIA).** NC licences (2.0 is CC BY-NC 4.0); commercial use needs a BRIA agreement. Its training data is licensed, but the weights are not shippable. 🧠
- **Face parsers.** *BiSeNet* face-parsing.PyTorch: MIT code, about 50 MB ResNet-18, 512 px, 19 CelebAMask-HQ classes including ears, earring, glasses, hat and neck. *FaRL* (facer): LAION-FACE pretraining, then CelebAMask-HQ or LaPa fine-tuning, at 448 px. *SegFace* (AAAI 2025): built for long-tail classes (earrings, glasses). All carry non-commercial data. 🧠 (The library already treats BiSeNet as `commercial_ok: false`.)
- **Matting.** *MODNet*: portrait, about 25 MB; weight terms unclear. ↔️ *RVM*: GPL-3.0 code and weights, compatible with a GPL add-on; the training data is research data. ↔️ Guided filtering, closed-form matting and GrabCut are licence-free algorithms. 🧠
- **Free masks in the photo.** iPhone Portrait-mode HEICs can embed semantic mattes (hair, skin, teeth, glasses) at reduced resolution. They are the subject's own data with no model licence; extraction through libheif or pillow-heif is unverified. ↔️

**Profile soft-tissue points (where MediaPipe fails, beyond about 70° yaw)**
- **Ordered alternation.** Down the anterior silhouette, convex (+) and concave (−) features alternate: g′(+), n′(−), prn(+, the sharpest), sn(−), ls(+), sto(− cusp), li(+), sm/B′(−), pg′(+), gn′/me′ (a + turn into the submental line), then the cervical point (−). Labelling is a chain problem: use Viterbi over curvature extrema with arc-length priors. 🧠
- **Concavities are rotation-invariant.** Take n′, sn, sto and B′ as the point of maximum distance from the chord between the flanking convexities. 🧠
- **Convexities are pitch-sensitive.** g′, prn, ls, li and pg′ are extrema along the Frankfort-anterior axis, so they shift along the contour by ρ·Δθ (ρ = sagittal radius of curvature); see Table 4. 🧠
- **gn′ is constructed,** either from the bisector of the facial line (n′–pg′) and the submental tangent, or as the midpoint of pg′–me′. Definitions differ by school, and both depend on neck posture and submental fat. ↔️

## Numbers & reference tables

**Table 1 — Candidate models (CPU via ONNX Runtime; fp32; times are order-of-magnitude for one 8-core laptop, to benchmark)**

| Model | Classes / task | Input px | Weights MB | CPU s/img | Commercial ship | Badge |
|---|---|---|---|---|---|---|
| MP selfie | person | 256 | ~0.25 | <0.01 | likely (card) | ↔️ |
| MP selfie multiclass | 6 incl. hair, face-skin | 256 | ~16 | 0.02–0.08 | likely (card) | ↔️ |
| MP hair segmenter | hair | 512 | ~0.8 | 0.02–0.08 | likely (card) | ↔️ |
| MobileSAM | prompted | 1024 | ~40 | 0.2–0.6 enc | yes, Apache-2.0 | 🧠 |
| SAM 2.1 tiny / small | prompted | 1024 | ~150 / ~180 | 1–4 enc | yes, Apache-2.0 | 🧠 |
| SAM ViT-B / SAM 2.1 large | prompted | 1024 | ~360 / ~900 | 2–8 / 8–30 | yes, Apache-2.0 | 🧠 |
| SAM 3 | text + prompts | ~1000 | ~3400 | 30–120+ | custom licence, verify | ↔️ |
| u2netp / U²-Net | salient object | 320 | 4.7 / 176 | 0.05–0.15 / 0.3–1 | weights yes; data ↔️ | ↔️ |
| IS-Net general | dichotomous | 1024 | ~170 | 1–3 | weights yes; data ↔️ | ↔️ |
| BiRefNet lite / full | dichotomous | 1024 | ~180 / ~900 | 1–4 / 5–20 | MIT; data ↔️ | ↔️ |
| RMBG-1.4 / 2.0 | foreground | 1024 | ~176 / ~885 | 1–3 / 5–20 | no (NC) | 🧠 |
| BiSeNet parser | 19 face classes | 512 | ~50 | 0.05–0.3 | no (CelebAMask-HQ) | 🧠 |
| FaRL ViT-B parser | 19 or 11 classes | 448 | ~350 | 0.5–2 | no | 🧠 |
| SegFace Swin-B | 19 / 11 classes | 512 | ~400 | 1–3 | no | 🧠 |
| MODNet | portrait alpha | 512 | ~25 | 0.1–0.3 | unclear | ↔️ |

Add the onnxruntime wheel (5–20 MB) and session creation (0.2–2 s for large models). Peak RAM is about 2–4× the weights for transformers at 1024². Dynamic int8 quantisation cuts size by about 4× and time by 1.5–3×, at some cost in edge quality. 🧠

**Table 2 — Training datasets behind face parsers**

| Dataset | Size | Classes | Terms | Badge |
|---|---|---|---|---|
| CelebAMask-HQ | 30 k imgs, 512² | 19 (incl. ears, earring, glasses, hat) | non-commercial research | 🧠 |
| LaPa | ~22 k | 11 (no ears, no accessories) | research only | 🧠 |
| Helen (Smith labels) | ~2.3 k | 11 | research | 🧠 |
| FaceSynthetics | 100 k synthetic | 19-like | research only | 🧠 |
| Reported mean F1 | CelebAMask-HQ ≈ 86–89 %; LaPa ≈ 92–93 % | — | — | ↔️ |

**Table 3 — Occluder policy**

| Occluder | Treatment | Dilate | Note | Badge |
|---|---|---|---|---|
| Loose hair, fringe | exclude skin contour; hair edge = outer bound | 2–3 mm | ask subject to pull hair back | 🧠 |
| Scalp hair (vault) | outer bound + head-breadth/length prior | — | swim cap (≈0.3–1 mm) restores the vault | 🧠 |
| Full beard / moustache | exclude jaw, chin, sn–ls skin; outer bound | 2 mm | pg′, gn′, ls flagged unreliable | 🧠 |
| Stubble < 3 mm | keep as skin; bias −0.5 to −1.5 mm; σ += 1 mm | — | user toggle by beard class | 🧠 |
| Glasses frame | exclude | 1.5 mm | bridge can sit ahead of n′ in profile | 🧠 |
| Contour behind lens | exclude | lens rim | −4 D at 12 mm ≈ 0.954× minification; +4 D ≈ 1.05× | 🧠 |
| Hat, headband | exclude vault; brim shadow | 3 mm | tight beanie ≈ outer bound | 🧠 |
| Earrings, piercings | exclude lobe region | 3–5 px or 1.5 mm | stretched lobes are real anatomy | 🧠 |
| Collar, scarf, hand | exclude | 3 mm | neck contour also varies with posture | 🧠 |

**Table 4 — Profile-point bias from pose error** (pinhole arithmetic; ρ and R values are rough anatomy)

| Error | Feature | Local radius | 5° | 10° | Badge |
|---|---|---|---|---|---|
| Yaw: silhouette ahead of midline, R(1−cos δ) | forehead | R ≈ 90 mm (transverse) | 0.34 mm | 1.37 mm | 🧠 |
| ″ | chin | R ≈ 30 mm | 0.11 | 0.46 | 🧠 |
| ″ | nasal dorsum/tip | R ≈ 8 mm | 0.03 | 0.12 | 🧠 |
| Pitch: extremum slide, ρ·Δθ | prn | ρ 3–6 mm | 0.3–0.5 | 0.5–1.0 | 🧠 |
| ″ | pg′ | ρ 10–20 mm | 0.9–1.7 | 1.7–3.5 | 🧠 |
| ″ | g′ | ρ 30–80 mm | 2.6–7.0 | 5.2–14 | 🧠 |

**Table 5 — Suggested along-contour σ for profile points** (adult, sharp photo; σ normal to the contour equals the edge σ)

| prn | sto | sn | ls / li | n′ | pg′ | gn′ | me′ | g′ | Badge |
|---|---|---|---|---|---|---|---|---|---|
| 0.5–1 mm | 0.5–1 | 0.7–1.5 | 1–2 | 1.5–3 | 2–4 | 2–5 | 3–6 | 3–8 | 🧠 |

Plausibility checks (library norms): nasofrontal angle about 115–135°, nasolabial about 90–110°, convexity g′–sn–pg′ about 12 ± 4° (Legan–Burstone). Out-of-range values mean recheck the labelling or the pose, never pull toward the norm. 🧠

## Applying this to photo→3D face sculpting in Blender

1. **Capture for silhouettes.** Use a plain backdrop 1 m or more behind the subject: mid-grey, or bright for a dark-haired subject. Add a rim light and pull the hair back with a cap or band; no glasses, no earrings, no portrait mode. Add one exposed-for-background "silhouette" profile frame at exactly 90°, plus ±45° frames. 🧠
2. **Run segmentation in the worker process,** on a head crop of about 2.2× the face box so it includes hair and ears. Default stack: MP multiclass for semantics plus MP hair. SAM 2.1-small (download) handles hard backgrounds and click corrections; BiRefNet-lite (download) gives the person outline at hair level. Face parsers stay behind an explicit "non-commercial" opt-in. 🧠
3. **Refine before tracing:** bilinear logit upsampling, then a guided filter on linear-light RGB (radius ≈ 1 % of face height, ε ≈ 1e-3). Take the 0.5 iso-contour with marching squares, then snap to the gradient maximum within ±3 σ_mask along the normal (parabolic sub-pixel). 🧠
4. **Show the artist the labelled outline** in the camera background, coloured by kind (hard skin, hair bound, excluded), with Grease Pencil to repaint a segment's kind or trace it by hand. Manual tracing stays the licence-free fallback and the ground truth for a test set. 🧠
5. **Check after the fit:** the profile overlay is within about 1 mm at prn, sn, ls, li and pg′. The hair bound is never violated by more than σ. The temple and vault come from the prior, not hair. Ears are fitted only where the helix is labelled hard. 🧠
6. **What goes wrong.** Beards counted as chin; fringe flattening the forehead; glasses bridges deepening n′; shadow edges under the jaw; mirrored selfies; 256 px masks used raw; neck contour from a different head posture; a hidden far-side contour (for example behind the nose in ¾ view) matched because no visibility test was run. 🧠

## Algorithmic implications

- **Observation record:** `ContourObs{view, xy (M×2 sub-px), normal_out, sigma_n, kind ∈ {hard, outer_bound, inner_bound}, side_labels, region, source, commercial_ok}`. `outer_bound` = the true skin silhouette lies inside (hair, beard, hat, collar). `inner_bound` = confidently segmented skin must be inside the projected head. 🧠
- **Residuals.** Normal-only: hard r = nᵀ(π(X_c) − x)/σ_n with Huber δ ≈ 2. For outer_bound, r = max(0, ·); for inner_bound, r = max(0, −·). Drop the tangential component: the current `fit_silhouettes` back-projects the full 2D correction, which drifts along the contour. 🧠
- **σ_n² = σ_edge² + (0.5·s_model)² + σ_blur²,** where s_model is full-res px per model px. Snapped crisp edges come out at 0.5–1 px, raw 256 px masks at 3–10 px. Floor it at 0.005·IOD_px. Inflate by √(ℓ_c/Δs) for correlated samples (ℓ_c ≈ max(3 px, s_model)), and cap each view at about 30–50 effective samples. 🧠
- **Model contour.** Interpolate n·v zero-crossings along edges, not whole vertices, and keep only visible segments: rasterise a low-res mask/depth in NumPy and take its boundary. Match data → model (closest point on the projected polyline) and re-associate each outer iteration. Reject matches whose normals differ by more than 30–45°. Gate the distance at 0.15·IOD_px early (not a fixed 60 px), shrinking to 5σ_n. An EDT of the observed contour (Felzenszwalb–Huttenlocher in NumPy; Blender ships no SciPy) replaces the dense O(M·P) distance matrix. 🧠
- **Landmark marching vs dense contours.** Keep marching or the yaw table only for the 17 jaw landmarks of 68-point detectors. The dense contour term supersedes them wherever a hard contour exists. 🧠
- **Priors under bounds.** Where only outer bounds exist (vault, temples, bearded jaw), fall back to the anthropometric prior (head breadth and length σ ≈ 4–6 mm). A hair-thickness prior h ≥ 0 also helps: about 3–10 mm for short or flat hair, wider for volume. 🧠
- **Profile detector defaults.** Smooth at 1 mm (≈0.016·IOD); compute curvature at 0.5/1/2 mm scales; label the chain with Viterbi, with ±25 % arc-length windows from Farkas norms. Accept only |yaw − 90°| < 10°. Use the points for initialisation and QA; fit geometry through the silhouette term. 🧠
- **Licence gate.** The segmenter enters the `commercial_ok` AND-chain (`ethics/licences-tos.md`). The registry stores `{url, sha256, bytes, licence}`; downloads are user-initiated, behind `bpy.app.online_access`, into `bpy.utils.extension_path_user(..., "models")`. Bundle only sub-20 MB permissive models. 🧠

## Disagreements, myths & open questions

- **"Weights trained on NC data are clean if the weights licence says MIT or Apache."** This is unsettled: Meta licenses SAM weights Apache despite SA-1B's terms, while CelebAMask-HQ-derived weights are redistributed by third parties. Default to the conservative reading. ↔️
- **Runtime downloads of weights on extensions.blender.org.** Whether ONNX weights count as "executable code" is unclear; gate behind online access and consent. ↔️
- **Myth: "high IoU means an accurate silhouette".** IoU is dominated by area, so a 3–5 px shift barely moves it. 🧠
- **Myth: "SAM is the best segmenter for everything".** It is prompt-ambiguous, coarse in hair and slow on CPU; category models (MP, BiRefNet) often give better outlines. ↔️
- **Open questions:**
  - How MP multiclass labels beards, ears and eyebrows.
  - The current MP model-card terms.
  - SAM 3's licence and the feasibility of an ONNX export.
  - Boundary accuracy at the hairline and temples (no published benchmark is known), which needs a consented, hand-traced test set.
  - Whether a commercially clean face parser can be trained on renders of the project's own CC0 assets (MPFB2), as FaceSynthetics showed for research use. ↔️

## Sources

No harvest or earlier draft existed for this topic; no URLs are cited.

**Further reading (by name, not yet linked)**
- Lee, Liu, Wu & Luo, "MaskGAN" (CelebAMask-HQ), CVPR 2020
- Liu et al., LaPa face-parsing dataset, AAAI 2020
- Yu et al., "BiSeNet", ECCV 2018
- Zheng et al., "General Facial Representation Learning in a Visual-Linguistic Manner" (FaRL), CVPR 2022
- Narayan et al., "SegFace: Face Segmentation of Long-Tail Classes", AAAI 2025
- Kirillov et al., "Segment Anything", ICCV 2023; Ravi et al., "SAM 2", 2024; Meta, "SAM 3: Segment Anything with Concepts", 2025
- Zhang et al., MobileSAM ("Faster Segment Anything"), 2023
- Zheng et al., "Bilateral Reference for High-Resolution Dichotomous Image Segmentation" (BiRefNet), 2024
- Qin et al., "U²-Net", Pattern Recognition 2020; Qin et al., "Highly Accurate Dichotomous Image Segmentation" (IS-Net, DIS5K), ECCV 2022
- Ke et al., "MODNet", AAAI 2022; Lin et al., "Robust High-Resolution Video Matting" (RVM), WACV 2022
- He, Sun & Tang, "Guided Image Filtering", ECCV 2010 / TPAMI 2013; Levin, Lischinski & Weiss, closed-form matting, TPAMI 2008; Rother et al., "GrabCut", SIGGRAPH 2004
- Devernay, sub-pixel non-maxima suppression for edges, INRIA report, 1995; Felzenszwalb & Huttenlocher, "Distance Transforms of Sampled Functions", 2012
- Hertzmann & Zorin, "Illustrating Smooth Surfaces", SIGGRAPH 2000; Cipolla & Giblin, *Visual Motion of Curves and Surfaces*, 2000
- Zhu et al., "High-Fidelity Pose and Expression Normalization", CVPR 2015; Zhu et al., "Face Alignment Across Large Poses: A 3D Solution", CVPR 2016
- Wood et al., "Fake It Till You Make It" (FaceSynthetics), ICCV 2021
- Farkas, *Anthropometry of the Head and Face*, 1994; Legan & Burstone, soft-tissue cephalometric analysis, 1980
- Google MediaPipe model cards: Selfie Segmentation, Selfie Multiclass Segmentation, Hair Segmentation
