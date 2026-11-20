# Face, hair and skin segmentation for silhouettes and occlusion

> Silhouettes recover what landmarks miss: the profile line (g′–n′–prn–sn–ls–li–pg′), the jaw and cheek outline, and ear protrusion. Segmentation should supply *semantics* (which stretch of an outline is skin against background, and which is hair, beard, glasses or clothing); sub-pixel image edges should supply *position*. For a commercial GPL add-on, only a few models are clean: MediaPipe's selfie, multiclass and hair segmenters (tiny; weight terms to re-check), SAM/SAM 2 and U²-Net/IS-Net (Apache-2.0), and BiRefNet (MIT weights, research training data). Every public face parser with ear, glasses and earring classes (BiSeNet, FaRL, SegFace) inherits non-commercial CelebAMask-HQ/LaPa terms, and BRIA's RMBG is non-commercial outright. Turn masks into normal-only contour residuals, each with its own σ and a *kind* (two-sided for skin|background, one-sided outer bound for hair, beard and hats); re-pick correspondences every iteration; and find the profile points by ordered curvature analysis.
>
> Evidence status: 0 ✅ / 8 📄 / 60 🧠 / 16 ↔️ — verification pass of 2026-11-20 done; remaining 🧠 items are unverified.

There was no harvest file or earlier draft, so no URL is cited. Related notes: `ethics/licences-tos.md` (licence rows, taint chain), `blender/blender-python-ml-deps.md` (worker, wheels), `reconstruction/landmark-detection.md` and `deformation-fitting-math.md` (contour σ, marching), `monocular-depth-normals.md` (Sapiens, DAViD) and `anatomy/jaw-chin-neck.md` (profile norms). The engine's current fitter is `face3d/fit/silhouette.py`.

## Key facts

**What a mask edge means**
- **The silhouette is an envelope, not a section.** It is the occluding contour (n·v = 0). In profile it runs over the philtral columns rather than the groove, over the bosses of a cleft chin, and over the lateral brow ridges when the glabella is recessed. The true midline therefore lies 0–2 mm *behind* it. Silhouette-to-silhouette fitting is unbiased; "midline landmarks" read off a silhouette are not. 🧠
- **Sliding is first-order free.** Moving the contact point along the contour generator changes the projected outline only to second order, so a fitter can re-pick the silhouette vertex each iteration and hold it fixed in between. 🧠
- **Boundary error is resolution-bound.** Networks typically miss the boundary by 1–3 *output* px. A 256 px model on a 2000 px head crop is therefore 8–24 px off until refined. mIoU and F1 hide shifts of a few pixels; boundary F-score at a 1–2 px tolerance is the relevant metric, and is rarely reported. 🧠
- **Gamma bias.** In sRGB the 50 % crossing of a blurred high-contrast edge sits about 0.78 σ_blur toward the darker side (sRGB 0.5 ≈ linear 0.214). Linearise before sub-pixel localisation. 🧠
- **False edges.** Under top light, the submandibular cast shadow sits *below* the jaw contour. Neither the hair shadows on the forehead nor the shadow terminator on the neck is a contour. Snap to the first strong edge from the face side. 🧠
- **Silhouettes ignore makeup and albedo,** which is why they carry likeness. They fail on low-contrast backdrops (dark hair on dark), and phone portrait mode corrupts them. 🧠

**Region reliability**
- **Forehead–hairline.** In frontal views it is an internal boundary that locates trichion and the hair shape, not geometry. Labels for baby hair and receding hairlines vary by several px at 512². 🧠
- **Temples.** Above the zygomatic arch, the frontal head outline is hair in most people; the skin lies 5–30 mm or more inside it, so this gives an outer bound only. 🧠
- **Beard–jaw.** A full beard hides the mandibular contour and pg′/gn′ and pushes the profile chin forward by its length. Stubble under 3 mm reads as skin but biases the outline about 0.5–2 mm outward. Datasets disagree on whether a beard is "hair" or "skin". ↔️
- **Ears.** In frontal views the helix is a strong protrusion cue, but it is often broken by hair, earrings or glasses arms. Parser ear classes score below skin, and earrings are long-tail. In profile the ear is an internal object. 🧠
- **Face-skin vs body-skin.** In MediaPipe multiclass, this boundary roughly follows the jaw contour under a level head. Its semantics are undocumented, so snap it to an image edge and inflate σ 3–5×. ↔️

**Models (licences are time-sensitive)**
- **MediaPipe segmenters.** *Selfie*: binary, about 0.25 MB. *Selfie multiclass*: 256², with background, hair, body-skin, face-skin, clothes and others; roughly 16 MB. *Hair*: 512², about 0.8 MB; the legacy graph took the previous mask as a 4th channel, so pass zeros for stills. Code is Apache-2.0, but weight terms come from per-model cards that differ and have changed. The hair model card states Apache-2.0 [1]; the multiclass card's licence text was not retrievable, though its six classes (background, hair, body-skin, face-skin, clothes, others) are confirmed [2]. ↔️ They were built for selfie effects: smooth edges, missed strands, and no face detector needed, so they still run in full profile. 🧠
- **SAM / SAM 2.1.** Apache-2.0 code and checkpoints. Landmark-derived point or box prompts give person, head or hair masks; multimask output resolves the ambiguity. Edges are good but not matting-grade. SAM 2's video mode can carry one prompt across a turntable sequence. MobileSAM (Apache-2.0, about 40 MB) is the CPU option. 🧠
- **SAM 3** (Meta, November 2025). Text "concepts" such as *beard* or *glasses*; custom SAM licence (royalty-free, commercial use allowed, with use restrictions and revocable terms) [3]; checkpoints gated on Hugging Face [3]; about 0.85 B parameters (not verified), so impractical on CPU. Read the full licence before use. 📄
- **BiRefNet.** MIT code and weights [4], in general, lite, portrait/matting and 2K variants; the best hair edges of the permissive set. Training mixes DIS5K-TR, HRSOD, UHRSD, DUTS and other research data [7] (P3M not seen in the sources): the weights are clean, but data taint is contested. 📄
- **U²-Net / u2netp / IS-Net.** Apache-2.0, trained on DUTS-TR and DIS5K (research data). ↔️ **rembg** is MIT, but its download zoo mixes clean and NC models (BRIA among them) and its dependencies (pymatting → numba/scipy) are heavy. Load whitelisted ONNX files directly instead. 🧠
- **RMBG-1.4 / 2.0 (BRIA).** Non-commercial (2.0 is CC BY-NC 4.0 per the official README, though some Hugging Face metadata labels it a custom "bria-rmbg-2.0" licence; 1.4 not checked); commercial use needs a BRIA agreement [5]. 📄
- **Face parsers.** *BiSeNet* (face-parsing.PyTorch): MIT code, ResNet-18 at 512 px, 19 CelebAMask-HQ classes including ears, earring, glasses, hat and neck. *FaRL*: LAION-FACE pretraining, then CelebAMask-HQ or LaPa fine-tuning. *SegFace* (AAAI 2025): long-tail classes. All carry non-commercial data. 🧠
- **Matting.** MODNet (about 25 MB) has unclear weight terms. ↔️ RVM is GPL-3.0 in code and weights, so it is compatible with a GPL add-on, but it was trained on research data. ↔️ The guided filter, closed-form matting and GrabCut are licence-free algorithms. 🧠
- **Masks already in the photo.** iPhone Portrait HEICs can embed reduced-resolution hair, skin, teeth and glasses mattes. These are the subject's own data; extracting them through libheif is unverified. ↔️

**Profile soft-tissue points (MediaPipe fails beyond about 70° yaw)**
- **Ordered alternation** down the anterior silhouette: g′(+), n′(−), prn(+, sharpest), sn(−), ls(+), sto(− cusp), li(+), B′(−), pg′(+), then gn′/me′, a convex turn into the submental line, then the cervical point (−). Label the chain by running Viterbi over curvature extrema with arc-length priors. 🧠
- **Concavities are rotation-invariant.** Take n′, sn, sto and B′ as the point of maximum distance from the chord between the flanking convexities. 🧠
- **Convexities are pitch-sensitive.** g′, prn, ls, li and pg′ are extrema along the Frankfort-anterior axis, so they slide by ρ·Δθ (Table 4). 🧠
- **gn′ is constructed:** either the bisector of n′–pg′ and the submental tangent, or the midpoint of pg′–me′. Schools differ, and the point depends on neck posture and submental fat. ↔️

## Numbers & reference tables

**Table 1 — Candidate models** (CPU, ONNX Runtime, fp32; order of magnitude on an 8-core laptop, to benchmark)

| Model | Task | Input px | MB | CPU s/img | Commercial | Badge |
|---|---|---|---|---|---|---|
| MP selfie | person | 256 | ~0.25 | <0.01 | likely (card) | ↔️ |
| MP selfie multiclass | 6 classes | 256 | ~16 | 0.02–0.08 | likely (card) | ↔️ |
| MP hair | hair | 512 | ~0.8 | 0.02–0.08 | Apache-2.0 (card) [1] | 📄 |
| MobileSAM | prompted | 1024 | ~40 | 0.2–0.6 (encoder) | Apache-2.0 | 🧠 |
| SAM 2.1 tiny / small | prompted | 1024 | ~150 / ~180 | 1–4 | Apache-2.0 | 🧠 |
| SAM ViT-B / SAM 2.1 large | prompted | 1024 | ~360 / ~900 | 2–8 / 8–30 | Apache-2.0 | 🧠 |
| SAM 3 | text + prompts | ~1000 | ~3400 | 30–120+ | custom SAM licence [3] | 📄 |
| u2netp / U²-Net | salient object | 320 | 4.7 / 176 | 0.05–0.15 / 0.3–1 | weights yes | 🧠 |
| IS-Net general | dichotomous | 1024 | ~170 | 1–3 | weights yes | 🧠 |
| BiRefNet lite / full | dichotomous | 1024 | ~180 / ~900 | 1–4 / 5–20 | MIT [4] | 📄 |
| RMBG-1.4 / 2.0 | foreground | 1024 | ~176 / ~885 | 1–3 / 5–20 | no (NC) [5] | 📄 |
| BiSeNet parser | 19 face classes | 512 | ~50 | 0.05–0.3 | no | 🧠 |
| FaRL ViT-B parser | 19 / 11 classes | 448 | ~350 | 0.5–2 | no | 🧠 |
| SegFace Swin-B | 19 / 11 classes | 512 | ~400 | 1–3 | no | 🧠 |
| MODNet | portrait alpha | 512 | ~25 | 0.1–0.3 | unclear | ↔️ |

Also budget for the onnxruntime wheel (5–20 MB) and session creation (0.2–2 s). Peak RAM runs about 2–4× the weight size for transformers at 1024². Dynamic int8 quantisation gives about 4× smaller files and 1.5–3× faster runs, at some cost to edges. 🧠

**Table 2 — Parser training data**

| Dataset | Size | Classes | Terms | Badge |
|---|---|---|---|---|
| CelebAMask-HQ | 30 k at 512² | 19, incl. ears, earring, glasses, hat | non-commercial research only [6] | 📄 |
| LaPa | ~22 k | 11, no ears or accessories | research | 🧠 |
| Helen (Smith labels) | ~2.3 k | 11 | research | 🧠 |
| Reported mean F1 | CelebAMask-HQ ≈ 86–89 %; LaPa ≈ 92–93 % | — | — | ↔️ |

**Table 3 — Occluder policy**

| Occluder | Treatment | Dilate | Note | Badge |
|---|---|---|---|---|
| Loose hair, fringe | exclude skin; hair edge = outer bound | 2–3 mm | pull hair back | 🧠 |
| Scalp hair (vault) | outer bound + head breadth/length prior | — | swim cap ≈0.3–1 mm restores the vault | 🧠 |
| Full beard, moustache | exclude jaw, chin, sn–ls; outer bound | 2 mm | flag pg′, gn′, ls | 🧠 |
| Stubble <3 mm | keep; shift −0.5 to −1.5 mm; σ += 1 mm | — | user beard-class toggle | 🧠 |
| Glasses frame | exclude | 1.5 mm | bridge can sit ahead of n′ | 🧠 |
| Contour seen through lens | exclude | lens rim | −4 D at 12 mm ≈ 0.954×; +4 D ≈ 1.05× | 🧠 |
| Hat, headband | exclude vault | 3 mm | tight beanie ≈ outer bound | 🧠 |
| Earrings | exclude lobe | 1.5 mm | stretched lobes are anatomy | 🧠 |
| Collar, scarf, hand | exclude | 3 mm | neck varies with posture | 🧠 |

**Table 4 — Profile-point bias from pose error** (pinhole arithmetic; radii are rough anatomy)

| Error | Feature | Radius | 5° | 10° | Badge |
|---|---|---|---|---|---|
| Yaw: silhouette ahead of midline, R(1−cos δ), mm | forehead | R ≈ 90 mm | 0.34 | 1.37 | 🧠 |
| ″ | chin | R ≈ 30 mm | 0.11 | 0.46 | 🧠 |
| ″ | nose | R ≈ 8 mm | 0.03 | 0.12 | 🧠 |
| Pitch: extremum slide, ρ·Δθ, mm | prn | ρ 3–6 mm | 0.3–0.5 | 0.5–1.0 | 🧠 |
| ″ | pg′ | ρ 10–20 mm | 0.9–1.7 | 1.7–3.5 | 🧠 |
| ″ | g′ | ρ 30–80 mm | 2.6–7.0 | 5.2–14 | 🧠 |

**Table 5 — Along-contour σ for profile points** (adult, sharp photo; σ normal to the contour equals the edge σ)

| prn | sto | sn | ls / li | n′ | pg′ | gn′ | me′ | g′ | Badge |
|---|---|---|---|---|---|---|---|---|---|
| 0.5–1 mm | 0.5–1 | 0.7–1.5 | 1–2 | 1.5–3 | 2–4 | 2–5 | 3–6 | 3–8 | 🧠 |

QA ranges from the library: nasofrontal about 115–135°, nasolabial about 90–110°, convexity g′–sn–pg′ about 12 ± 4°. An outlier means recheck the labels and pose, not pull toward the norm. 🧠

## Applying this to photo→3D face sculpting in Blender

1. **Capture.** Use a plain backdrop at least 1 m behind the subject, with a rim light. Pull the hair back with a cap or band. No glasses, no earrings, no portrait mode. Add one profile frame at exactly 90°, exposed for the background as a pure silhouette, plus ±45° frames. 🧠
2. **Segment in the worker process** on a head crop about 2.2× the face box. Bundled: MP multiclass plus MP hair. Downloads: SAM 2.1-small for hard backgrounds and click fixes, and BiRefNet-lite for the hair-level outline. Face parsers only behind an explicit non-commercial opt-in. 🧠
3. **Refine.** Upsample the logits bilinearly, then guided-filter on linear RGB (radius ≈ 1 % of face height, ε ≈ 1e-3). Take the 0.5 iso-contour with marching squares, then snap to the gradient maximum within ±3 σ_mask along the normal, with parabolic sub-pixel refinement. 🧠
4. **Show the labelled outline** over the camera background, coloured by kind. Let the artist re-label or hand-trace segments with Grease Pencil; manual tracing is the licence-free fallback and test-set ground truth. 🧠
5. **Check.** The profile overlay should be within about 1 mm at prn, sn, ls, li and pg′, and hair bounds should not be violated by more than σ. Temples and vault come from the prior, and ears are fitted only where the helix is hard. 🧠
6. **Failure modes:**
   - a beard fitted as the chin;
   - a fringe flattening the forehead;
   - a glasses bridge deepening n′;
   - jaw shadow edges;
   - raw 256 px masks;
   - the neck traced from a different posture;
   - hidden far-side contours matched with no visibility test. 🧠

## Algorithmic implications

- **Record:** `ContourObs{view, xy (M×2 sub-px), normal_out, sigma_n, kind ∈ {hard, outer_bound, inner_bound}, side_labels, region, source, commercial_ok}`. `outer_bound`: the skin silhouette lies inside it (hair, beard, hat, collar). `inner_bound`: confident skin must lie inside the projected head. 🧠
- **Residuals** are normal-only:
  - hard: r = nᵀ(π(X_c) − x)/σ_n, Huber δ ≈ 2;
  - outer_bound: max(0, r);
  - inner_bound: max(0, −r).
  
  The current `fit_silhouettes` back-projects the full 2D correction, so it drifts along the contour; drop the tangential part. 🧠
- **σ_n² = σ_edge² + (0.5·s_model)² + σ_blur²,** with s_model in full-res px per model px. Snapped crisp edges come out at 0.5–1 px; raw 256 px masks at 3–10 px. Floor σ_n at 0.005·IOD_px. Inflate it by √(ℓ_c/Δs) for correlated samples, with ℓ_c ≈ max(3 px, s_model), and cap each view at about 30–50 effective samples. 🧠
- **Model contour.**
  - Take the n·v zero-crossings interpolated along edges, not whole vertices.
  - Run a visibility test: rasterise a low-res NumPy mask and keep its boundary.
  - Match data → model (closest point on the projected polyline) and re-associate every outer iteration.
  - Reject pairs whose normals differ by more than 30–45°.
  - Gate at 0.15·IOD_px, shrinking to 5σ_n; a fixed 60 px gate is wrong.
  - Use an EDT (Felzenszwalb–Huttenlocher in NumPy; Blender bundles no SciPy) instead of the dense O(M·P) matrix. 🧠
- **Marching.** Landmark marching or a yaw lookup table applies only to the 17 jaw points of 68-point detectors; where a hard contour exists, the dense term supersedes it. 🧠
- **Priors under bounds.** Where only outer bounds exist (vault, temples, bearded jaw), use the anthropometric prior: head breadth and length, σ ≈ 4–6 mm. Add a hair-thickness offset h ≥ 0: about 3–10 mm for short or flat hair, more for volume. 🧠
- **Profile detector.**
  - Smooth at 1 mm (≈0.016·IOD).
  - Compute curvature at 0.5, 1 and 2 mm.
  - Label with Viterbi, using ±25 % arc-length windows from Farkas norms.
  - Run only when |yaw − 90°| < 10°.
  - The points serve initialisation and QA; geometry goes through the silhouette term. 🧠
- **Licence gate.** The segmenter joins the `commercial_ok` AND-chain. Registry entries carry `{url, sha256, bytes, licence}`. Downloads are user-initiated, behind `bpy.app.online_access`, into `bpy.utils.extension_path_user(..., "models")`. Bundle only permissive models under 20 MB. 🧠

## Disagreements, myths & open questions

- **Does NC training data taint MIT- or Apache-licensed weights?** This is unsettled. Meta licenses the SAM weights Apache despite SA-1B's terms, while CelebAMask-HQ-derived weights are redistributed by third parties. Default to the conservative reading. ↔️
- **Can extensions.blender.org add-ons download ONNX weights at runtime?** Unclear: it depends on whether weights count as "executable code". Gate downloads behind online access and consent. ↔️
- **Myth: high IoU means an accurate silhouette.** A 3–5 px shift barely moves IoU. 🧠
- **Myth: SAM is the best at everything.** It is prompt-ambiguous, coarse in hair and slow on CPU. Category models often give better outlines. ↔️
- **Open questions:**
  - How does MP multiclass label beards, ears and brows?
  - What are the current MP card terms?
  - What is SAM 3's licence, and can it be exported to ONNX?
  - How accurate are hairline and temple boundaries? There is no known benchmark, so this needs a consented, hand-traced set.
  - Can a clean face parser be trained on renders of the project's CC0 assets (MPFB2), in the way FaceSynthetics was trained? ↔️

## Sources

1. Google, MediaPipe Hair Segmentation model card (Apache-2.0) — https://dcmpx.remotevs.com/com/googleapis/storage/SL/mediapipe-assets/Model%20Card%20-%20Hair%20Segmentation.pdf
2. Google, MediaPipe Image Segmenter guide (multiclass classes) — https://developers.google.com/edge/mediapipe/solutions/vision/image_segmenter
3. Meta, SAM 3 licence on Hugging Face — https://huggingface.co/facebook/sam3/blob/main/LICENSE (repo: https://github.com/facebookresearch/sam3)
4. BiRefNet official model card (MIT) — https://huggingface.co/ZhengPeng7/BiRefNet
5. BRIA RMBG-2.0 README (CC BY-NC 4.0, commercial agreement) — https://github.com/Bria-AI/RMBG-2.0
6. CelebAMask-HQ project page (non-commercial research only) — https://mmlab.ie.cuhk.edu.hk/projects/CelebA/CelebAMask_HQ.html
7. Zheng et al., BiRefNet paper (training sets) — https://arxiv.org/html/2401.03407v7

**Further reading (by name, not yet linked)**
- Lee et al., "MaskGAN" (CelebAMask-HQ), CVPR 2020; Liu et al., LaPa, AAAI 2020
- Yu et al., "BiSeNet", ECCV 2018; Zheng et al., FaRL, CVPR 2022; Narayan et al., "SegFace", AAAI 2025
- Kirillov et al., "Segment Anything", ICCV 2023; Ravi et al., "SAM 2", 2024; Meta, "SAM 3: Segment Anything with Concepts", 2025; Zhang et al., MobileSAM, 2023
- Zheng et al., BiRefNet, 2024; Qin et al., "U²-Net", Pattern Recognition 2020; Qin et al., IS-Net/DIS5K, ECCV 2022
- Ke et al., "MODNet", AAAI 2022; Lin et al., RVM, WACV 2022
- He, Sun & Tang, "Guided Image Filtering", 2010/2013; Levin et al., closed-form matting, TPAMI 2008; Rother et al., "GrabCut", SIGGRAPH 2004
- Devernay, sub-pixel edge NMS, INRIA 1995; Felzenszwalb & Huttenlocher, "Distance Transforms of Sampled Functions", 2012
- Hertzmann & Zorin, "Illustrating Smooth Surfaces", SIGGRAPH 2000; Cipolla & Giblin, *Visual Motion of Curves and Surfaces*, 2000
- Zhu et al., HPEN, CVPR 2015; Zhu et al., 3DDFA, CVPR 2016; Wood et al., FaceSynthetics, ICCV 2021
- Farkas, *Anthropometry of the Head and Face*, 1994; Legan & Burstone, soft-tissue cephalometric analysis, 1980
- Google MediaPipe model cards: Selfie, Selfie Multiclass and Hair Segmentation

## Verification log (2026-11-20)

| Claim | Outcome | Source |
|---|---|---|
| MediaPipe multiclass (256², six classes, ~16 MB) and hair (512², ~0.8 MB) weights are Apache-2.0 and bundle-able | Partly confirmed: hair card is Apache-2.0; multiclass licence text not retrieved (classes confirmed); size not checked. Row stays ↔️ for multiclass | [1] https://dcmpx.remotevs.com/com/googleapis/storage/SL/mediapipe-assets/Model%20Card%20-%20Hair%20Segmentation.pdf ; [2] https://developers.google.com/edge/mediapipe/solutions/vision/image_segmenter |
| SAM 3: custom SAM licence, gated checkpoints, ~0.85 B params; SAM 2/2.1 Apache-2.0 | Confirmed (licence, gating); params and SAM 2 Apache not checked | https://huggingface.co/facebook/sam3/blob/main/LICENSE ; https://github.com/facebookresearch/sam3 |
| BiRefNet MIT code/weights; trained on DIS5K, HRSOD, UHRSD, P3M etc. | Confirmed MIT; datasets confirmed as DIS5K-TR, HRSOD, UHRSD, DUTS (P3M not seen) | https://huggingface.co/ZhengPeng7/BiRefNet ; https://arxiv.org/html/2401.03407v7 |
| RMBG-2.0 CC BY-NC 4.0; RMBG-1.4 NC; rembg zoo includes them | Confirmed for 2.0 (some HF metadata uses a custom licence label); 1.4 and rembg unconfirmed | https://github.com/Bria-AI/RMBG-2.0 |
| Face parsers (BiSeNet, FaRL, SegFace) inherit NC dataset terms | CelebAMask-HQ NC confirmed; LaPa only via secondary source; parser-specific terms unconfirmed (bullet stays 🧠) | https://mmlab.ie.cuhk.edu.hk/projects/CelebA/CelebAMask_HQ.html |
| MP multiclass face-skin/body-skin boundary follows jaw; beard labelling | Unconfirmed: classes listed, no beard or boundary documentation found | https://developers.google.com/edge/mediapipe/solutions/vision/image_segmenter |
