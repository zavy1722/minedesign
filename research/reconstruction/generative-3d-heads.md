# Generative / large reconstruction models for heads (2024-2026)

> Image-to-3D models come in four families: feed-forward large reconstruction models (LRM, TripoSR, InstantMesh, SF3D), native 3D latent diffusion or flow models (CLAY/Rodin, Hunyuan3D, TRELLIS, TripoSG), multi-view-diffusion-then-reconstruct pipelines (Zero123++, Hunyuan3D-2mv, FaceLift, CAP4D), and head-specific 3D GANs or identity-guided optimisers (EG3D, PanoHead, SphereHead, Arc2Avatar). All give a plausible head in seconds to minutes, but none publishes millimetre error against real face scans, and the bar is high: the *average* FLAME face already scores ≈1.5 mm mean on NoW once scaled [2]. Their output is unit-scale, canonical-camera, symmetry-biased triangle soup whose identity lives mostly in the texture, with depth, eyes, lips, ears and hair invented. Use them as a seeded, region-weighted blockout prior and a source for unseen regions, never for landmarks, scale or cameras. Licences run from MIT (TRELLIS, TripoSR) through territory-restricted (Hunyuan3D) to non-commercial (EG3D, most head GANs, anything built on InsightFace weights [4][12]).
>
> Evidence status: 0 ✅ / 16 📄 / 44 🧠 / 28 ↔️ — verified 2026-11-20 (see log); remaining 🧠 items are unconfirmed.

## Key facts

**Families: how each makes geometry**
- **Feed-forward LRMs (2023–24).** LRM (Hong et al., ICLR 2024) maps a DINO-encoded image to a tri-plane NeRF with a ~0.5 B-parameter transformer trained on ~1 M Objaverse and MVImgNet objects, ~5 s per object. Descendants: OpenLRM (open reimplementation); TripoSR (MIT, under 1 s, marching cubes at 256³ by default); InstantMesh (Apache-2.0; six Zero123++ views into a sparse-view LRM with FlexiCubes); LGM and GS-LRM (Gaussians); Stability's SF3D and SPAR3D (UV-unwrapped, de-lit). One regression pass predicts roughly the conditional mean, so faces come out smooth and averaged. 🧠
- **Native 3D latent diffusion and flow (2024–26).** CLAY (SIGGRAPH 2024; basis of Hyper3D Rodin Gen-1) and Hunyuan3D 2.0 (Jan 2025) work in a vector-set shape-VAE latent and extract an occupancy/SDF field by marching cubes at octree resolution 256 by default (raisable to ~384–512) [13] 📄. TRELLIS (CVPR 2025) generates a sparse 64³ structure, then latents on active voxels, decoded to Gaussians, a radiance field or a 256³ FlexiCubes mesh. TripoSG (MIT) and Step1X-3D (Apache-2.0) pair SDF VAEs with rectified flow. Sampling is stochastic: seeds give different noses and chins. 🧠
- **Hosted and next-generation (2025–26):** Hunyuan3D 2.5 (reported ≈10 B-parameter "LATTICE") and 3.0, Rodin Gen-2, Tripo 3.x, Meshy 5–6, and TRELLIS.2 (late 2025: ≈4 B parameters, "O-Voxel", up to 1536³, PBR, MIT; some dependencies such as nvdiffrast/nvdiffrec carry their own licences) [9] 📄. All claim higher resolution; none publishes face-scan accuracy. Hosted-only status of Hunyuan3D 2.5/3.0 unconfirmed. ↔️ (time-sensitive)
- **Multi-view diffusion, then reconstruction.** Generic: Zero123++, SV3D, Era3D, MV-Adapter, Hunyuan3D-2mv (accepts real front/left/back/right views). Head-specific: DiffPortrait3D, Morphable Diffusion (FLAME-conditioned), FaceLift (head multi-view diffusion trained on synthetic heads, then GS-LRM), CAP4D (morphable multi-view diffusion to a 4D avatar). 🧠 GAF fills unseen views of a monocular-video Gaussian avatar with multi-view diffusion, on VHAP-tracked FLAME [6]. 📄 Diffused views agree with each other, but each is a guess.
- **3D-aware head GANs.**
  - EG3D (CVPR 2022) volume-renders a tri-plane (3 × 256² × 32 channels) at 128² and super-resolves in 2D to 512², so detail visible at 512² is **not in the 3D density**. FFHQ training limits it to roughly ±60° yaw.
  - PanoHead (CVPR 2023) adds a depth-split "tri-grid" and back-of-head images (FFHQ-F) for 360°. SphereHead (ECCV 2024) uses spherical tri-planes to suppress a second face on the back of the head [10][11]. 📄 GGHead (SIGGRAPH Asia 2024) generates Gaussians in a template's UV space.
  - A real photo needs GAN inversion (PTI-style fine-tuning), which overfits the input view; identity drifts beyond ~45° yaw.

  🧠
- **Identity-guided optimisation.** Arc2Face (ECCV 2024) is Stable Diffusion conditioned only on an ArcFace embedding; ID-to-3D (2024) and Arc2Avatar (CVPR 2025) distil it by score distillation (SDS) into FLAME-bound Gaussians or meshes. They maximise *recognisability to ArcFace*, which texture can satisfy; geometry stays FLAME-like. Microsoft's Rodin (CVPR 2023) and RodinHD learn from ~100 k synthetic avatars, capping realism at the synthetic generator's. 🧠
- **Face-specific LRMs.** KaoLRM repurposes a pre-trained LRM to regress FLAME parameters instead of a free surface [1]. 📄 The field's fix for LRM faces is to re-impose a 3DMM, gaining scale and correspondence; LAM, GAGAvatar and Avat3r are Gaussian counterparts (`reconstruction/neural-head-avatars.md`). 🧠

**Likeness and accuracy**
- **No public millimetre benchmark** covers generic generators on real faces (NoW, REALY or FaceScape protocols). Preference arenas and vendor demos score appeal, not likeness. ↔️
- **The bar to beat.**
  - On NoW, the average FLAME mesh scores 1.92 mm mean, or 1.53 mm with scale optimised [2]. 📄
  - MICA reaches ≈0.90–0.94 mm median and ≈1.11–1.19 mm mean, depending on metric and split [3][1]. ↔️
  - Some papers report Chamfer distance instead of scan-to-mesh error, so numbers from different papers are not comparable [1]. 📄

  A generated surface adds identity information only in regions where its error is below ~1.5 mm. Invented depth never reaches that.
- **Author estimate (unmeasured)** for 2025 generic generators after similarity alignment: ≈2–4 mm RMS on frontal skin, ≈3–8 mm on nose and chin projection, ≈5–15 mm on occiput and ears; worse from selfies (Table 2). ↔️
- **Regression to the mean, and symmetry.** Distinctive profiles regress toward the training mean, and asymmetry is suppressed. 🧠 Generative models also carry their own learned proportions: "ideal" faces from text-to-image models differ significantly from the neoclassical canons [5]. 📄 A learned prior is not anthropometry.
- **Texture carries the identity.** Textured, the mesh convinces; in clay it reads as "a relative". PBR outputs still bake skin shading (`community/ai-assisted-sculpting.md`). 🧠
- **Training data.** Generic generators learn from Objaverse(-XL)-class assets with few real head scans. Head GANs learn from FFHQ (≈70 k Flickr faces, pose- and demographically biased; CC BY-NC-SA 4.0). Arc2Face uses WebFace42M; Rodin and FaceLift use synthetic heads. Expect weaker results on children, older adults, under-represented groups, beards and headwear. 🧠
- **Identity metrics.** Head papers report ArcFace cosine similarity, which is texture-dominated 🧠. InsightFace's pretrained weights are non-commercial research only [4][12]. 📄

**Topology, camera and scale**
- **Raw output:** 10⁵–10⁶ triangles in a unit cube, uncorresponded, often non-manifold with internal shells, as Y-up GLB. TRELLIS's example export decimates 95 % of faces and bakes a 1024² texture. A vendor "quad remesh" is not animation edge flow. 🧠
- **Canonical camera.** Generators assume a fixed-FoV or near-orthographic view and take no intrinsics. A close photo's perspective is baked into the shape: mid-face magnification is ≈18–30 % at 0.3–0.5 m (`reconstruction/single-image-regression.md`, Table 4). 🧠
- **Conditioning resolution.** TRELLIS and Hunyuan3D 2.x use DINOv2-family encoders at ≈518 px. A bust crop leaves the face only ≈160–240 px wide. 🧠

## Numbers & reference tables

**Table 1 — Catalogue** ("face verdict" is my judgement for a real person, not a measurement)

| Model | Year | Family | Output, native resolution | Input | Face verdict | Badge |
|---|---|---|---|---|---|---|
| LRM / OpenLRM | 2023–24 | feed-forward | tri-plane NeRF → marching cubes | 1 image | soft mean face | 🧠 |
| TripoSR | 2024 | feed-forward | tri-plane, MC 256³ | 1 | blockout | 🧠 |
| InstantMesh | 2024 | MV diffusion + LRM | FlexiCubes mesh | 1 | soft | 🧠 |
| SF3D / SPAR3D | 2024–25 | feed-forward (+ points) | UV mesh, de-lit | 1 | low detail | 🧠 |
| CLAY → Rodin Gen-1/2 | 2024–25 | 3D latent DiT, hosted | SDF mesh, quad mode | 1–5 | clean, generic | ↔️ |
| Hunyuan3D 2.0 / 2.1 / 2mv | 2025 | vecset flow DiT + Paint | MC octree 256–512; PBR in 2.1 | 1 (2mv: up to 4) | best open mass, averaged | ↔️ |
| Hunyuan3D 2.5 / 3.0 | 2025 | hosted | reportedly up to 1536³ | 1+ | sharper; depth still guessed | ↔️ |
| TRELLIS | 2024–25 | sparse structured latent | 64³ → 256³ FlexiCubes, or 3DGS | 1 (multi-image experimental) | good silhouette, soft face | 🧠 |
| TRELLIS.2 | 2025 | "O-Voxel" latent | ≤1536³, PBR [9] | 1 | unreviewed for faces | 📄 |
| TripoSG / Step1X-3D | 2025 | SDF VAE + rectified flow | MC mesh | 1 | crisp objects, generic face | 🧠 |
| EG3D | 2022 | 3D GAN | tri-plane 256²; render 128² → SR 512² | inversion | frontal only | 🧠 |
| PanoHead | 2023 | 360° 3D GAN | tri-grid 256² × 3, 512² | inversion | full head; invented back | 🧠 |
| SphereHead | 2024 | spherical tri-plane GAN | 512² | inversion | fewer back-face artefacts | ↔️ |
| Arc2Avatar / ID-to-3D | 2024–25 | ID-guided SDS | FLAME-bound 3DGS / mesh | 1 | high ArcFace score, FLAME-level shape | ↔️ |
| FaceLift | 2024–25 | head MV diffusion + GS-LRM | Gaussians | 1 | head-specific, synthetic-trained | ↔️ |
| KaoLRM | 2026 | LRM → FLAME | FLAME parameters [1] | 1 | corresponded, near-metric | 📄 |

**Table 2 — Accuracy reference bar** (NoW-style, mm, after alignment)

| Reference | Median | Mean | Population / note | Badge |
|---|---|---|---|---|
| Average FLAME, no scale fit | – | 1.92 | NoW [2] | 📄 |
| Average FLAME, scale optimised | – | 1.53 | NoW [2] | 📄 |
| MICA (single image) | 0.90–0.94 | 1.11–1.19 | NoW, metric and split vary [3][1] | ↔️ |
| Generic generator, frontal skin | – | ≈2–4 RMS | author estimate; unbenchmarked | ↔️ |
| Generic generator, nose and chin projection | – | ≈3–8 | author estimate | ↔️ |
| Generic generator, occiput and ears | – | ≈5–15 | author estimate | ↔️ |

**Table 3 — Internal grid vs physical detail.** Voxel = box ÷ grid; the *whole input* fills the box (head-only crop ≈0.25 m, bust ≈0.45 m). Effective learned detail is ≈2–4 voxels.

| Model / setting | Grid | Voxel, 0.25 m box | Voxel, 0.45 m box | Badge |
|---|---|---|---|---|
| TRELLIS sparse structure | 64³ | 3.9 mm | 7.0 mm | 🧠 |
| TripoSR MC; TRELLIS mesh; Hunyuan3D default | 256³ | 0.98 mm | 1.76 mm | 🧠 |
| Hunyuan3D raised octree | 384–512 | 0.49–0.65 mm | 0.88–1.17 mm | 🧠 |
| TRELLIS.2 / Hunyuan3D 3.0 claims | 1024–1536 | 0.16–0.24 mm | 0.29–0.44 mm | ↔️ |
| EG3D/PanoHead tri-plane texel; 128² ray footprint | 256² / 128² | ≈1–2 mm / ≈2–3 mm | – | 🧠 |

Likeness-bearing relief, such as the lid crease, alar groove and philtral columns, is ≈0.5–5 mm, so even in principle only grids ≥256³ on a head-only crop can hold it. 🧠

**Table 4 — Licence and access** (verify everything before shipping)

| Model | Code / weights | Commercial use | Notes | Badge |
|---|---|---|---|---|
| TRELLIS | MIT / MIT | yes | some CUDA deps (nvdiffrast, 3DGS rasteriser) are non-commercial | ↔️ |
| TripoSR, TripoSG | MIT | yes | – | 🧠 |
| InstantMesh | Apache-2.0 | yes | Zero123++ weight terms apply | ↔️ |
| Step1X-3D | Apache-2.0 | yes | – | ↔️ |
| OpenLRM | Apache-2.0 / CC BY-NC 4.0 | weights no | – | ↔️ |
| SF3D, SPAR3D | Stability Community | below ≈US$1 M annual revenue | – | ↔️ |
| Hunyuan3D 2.x | Tencent Hunyuan Community | yes, outside the EU, UK and South Korea [8] | monthly-active-user cap not confirmed for 2.1 (only a secondary source for 2.0, <1M MAU) | 📄 |
| EG3D | NVIDIA Source Code License-NC | no | FFHQ is CC BY-NC-SA | 🧠 |
| PanoHead, SphereHead, FaceLift, Arc2Avatar | unconfirmed | assume no | ArcFace/InsightFace weights non-commercial [4] | ↔️ |
| Rodin, Tripo, Meshy | hosted terms | paid tiers | entry tiers ≈US$10–30/month; free-tier outputs public or CC BY; face upload = biometric data | ↔️ |

**Table 5 — Generator-surface data term** (design defaults; anisotropic, split along the conditioning view axis **d**)

| Region | σ in-plane (mm) | σ along **d** (mm) | Enabled | Badge |
|---|---|---|---|---|
| Forehead, cheeks, temples (facing the view) | 2–3 | 4–6 | yes | 🧠 |
| Nose dorsum and tip, chin, lips outline | 2–3 | 6–10 | yes, depth weak | 🧠 |
| Lateral face, jaw angle | 4–6 | 8–12 | yes | 🧠 |
| Occiput and vertex (no rear photo) | ≥15 | ≥15 | silhouette only | 🧠 |
| Eyes, lid margins, mouth interior, nostrils, ears, hair and beard | – | – | off | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Choose the role.** Blockout, mass and back-of-head completion: TRELLIS (MIT) or Hunyuan3D 2.1 locally (if your territory is licensed); hosted Rodin, Tripo or Meshy only with written consent to upload. Likeness: the solved-camera fit stays the backbone (`blender/reference-camera-setup.md`).
2. **Feed it well.** Head-only crop from a ≥1024 px original, background removed; eyes open, lips closed, neutral, flat light, hair back, no glasses; shot from ≥1.5 m with a ≥85 mm full-frame-equivalent lens. Generate **4–8 seeds**, from 2–3 different photos if you can. Their spread is your uncertainty.
3. **Multi-view input** (Hunyuan3D-2mv, Rodin multi-image): use real photos at 0°, ±90° and 180°, with the same lens and distance and a levelled eye line. Never feed AI turnarounds; they are consistent but fictional.
4. **Import** with the glTF importer, apply transforms, check which way the face points, and scale from the metric solve (else IPD 63 mm). Keep each seed as a locked `ai_ref_seedN` object with custom properties `model`, `version`, `seed`, `licence`, `commercial_ok`, `cloud_uploaded`, `consent_id`.
5. **Clean and align.** Delete components under 1 % of vertices, Merge by Distance 0.01 mm, Voxel Remesh 0.5–1 mm for a proxy. Umeyama (with scale) on ~8 photo-triangulated landmarks: endocanthia, exocanthia, nasion, subnasale, cheilia, pogonion.
6. **Audit in clay through every solved camera** (matcap, photo at 50 % or Difference). The profile silhouette is decisive. Measure nose-tip projection, chin against the soft-tissue nasion vertical, and glabella depth; check adult head length g–op ≈175–205 mm and breadth eu–eu ≈135–160 mm 🧠. Reject regions that miss the photos by >3 mm frontally or >5 mm in profile.
7. **Use only what survives:** as an in-front wireframe reference, or as a Shrinkwrap target (Project, limit 3–5 mm) restricted to an `ai_ok` vertex group. Rebuild eyes (≈24 mm eyeballs), mouth, nostrils and ears from the template.
8. **Head-GAN completion** (PanoHead/SphereHead inversion; research licence): back-of-head silhouette only, when no rear photos exist, at σ ≥ 10 mm.
9. **What goes wrong:**

| Symptom | Cause | Check / fix |
|---|---|---|
| Right when textured, wrong in clay | texture carries identity | audit untextured; run the identity check on matcap renders |
| Nose and chin too prominent or too flat | invented depth, selfie perspective | profile overlay; regenerate from a distant photo |
| Face on the back of the head; doubled brows | 360° GAN artefact; inconsistent multi-view input | SphereHead-class model; single view |
| Seeds disagree by >5 mm | weak conditioning | treat the region as unknown |
| Too symmetric | training prior | measure asymmetry from photos only |
| Licence or consent breach | cloud upload, non-commercial weights | provenance properties; local models |

## Algorithmic implications

- **Backend contract.** `generate(image, seed) → GLB` plus metadata: model, weights SHA, licence id, `commercial_ok`, `territory_ok`, `cloud_upload`, crop box. Never bundle weights: run each backend in its own venv or subprocess. The term is **off** by default in likeness mode and on in blockout mode. 🧠
- **Seed ensemble.** Align each seed to the template; closest-point correspondences per template vertex v give mean μ_v and spread s_v (mm). Use σ_v² = σ_region² + s_v² per axis (Table 5); drop v where s_v > 5 mm. 🧠
- **Anisotropic residual.** With r = x − μ_v and conditioning view axis **d**: cost = ‖r − (r·**d**)**d**‖²/σ_t² + (r·**d**)²/σ_d². Use a Geman–McClure kernel with c = 2σ. Depth along the view axis is the least constrained direction. 🧠
- **Hierarchy.** Photo landmarks (σ 0.02–0.03 IOD) and silhouettes rank above anatomical priors, which rank above the generator term. Cap the generator's information per region at ≈25 % of the landmark information, as in `community/ai-assisted-sculpting.md`. 🧠
- **Gates.** *Depth contradiction:* generator depth at glabella, pronasale, subnasale or pogonion >3σ from the triangulated point disables that region. *Perspective:* conditioning photo f₃₅ < 35 mm → σ_d × 2. *Symmetry:* never mirror generator data; halve its weight where photo-measured asymmetry exceeds 2 mm. 🧠
- **Discard the generator's scale, pose and implied camera.** Scale comes from the metric solve, or else a log-normal IPD prior (63 ± 3.5 mm). Synthetic views (diffusion views, GAN renders) never feed landmark detection or camera solving. As silhouettes they get weight ≤ 0.25 and a `synthetic` tag. 🧠
- **Parametric route first.** As KaoLRM shows [1], an LRM regressing 3DMM coefficients is directly usable as an initial β with σ ≈ 1. A free-surface generator is only a data term. 📄 / 🧠
- **Detail refinement.** A human-specific normal estimator (Sapiens, pretrained on >300 M human images [7] 📄) is a better source of frontal surface detail than the generator; weights reportedly non-commercial. ↔️
- **Identity QA.** Compare ArcFace cosine on textured versus matcap renders, as relative comparisons only (`reconstruction/identity-embeddings.md`). Record the weights' licence [4]. 🧠

## Disagreements, myths & open questions

- **Myth: "360° head GANs see the back of the head."** They synthesise it from FFHQ-F statistics. 🧠
- **Myth: "a high ArcFace score is a 3D likeness."** SDS against an ArcFace-conditioned prior can meet it through texture. ↔️
- **Myth: "1536³ means sub-millimetre faces."** Latent capacity and object-centric training data cap face detail well below the grid. ↔️
- **Which model is "best for faces" in late 2026** (hosted or open, head-specific or generic) is unknown: arenas measure appeal, and FaceLift, Arc2Avatar, PanoHead and KaoLRM share no millimetre benchmark. KaoLRM implies keeping a 3DMM [1]. ↔️
- **Licences to confirm:** PanoHead, SphereHead, FaceLift, Arc2Avatar, TRELLIS.2, the current Hunyuan territory terms, and vendor free-tier output rights. ↔️
- **Law** (time-sensitive): face data used to identify someone is GDPR special-category biometric data; EU AI Act deep-fake transparency duties apply from August 2026 (verify). ↔️
- **Open:** run generators on NoW neutral and selfie images and report median and mean error; that one experiment would settle most of this note.

## Sources

No topic harvest or draft existed; these URLs are cross-cited from other harvests in `_raw/harvests/` (single-image-regression, identity-embeddings, facial-proportions-canons, multi-view-fitting, monocular-depth-normals).

1. KaoLRM: Repurposing Pre-trained Large Reconstruction Models for Parametric 3D Face Reconstruction — https://arxiv.org/pdf/2601.12736 — paper — 2026
2. Towards Metrical Reconstruction of Human Faces (MICA) — https://ar5iv.labs.arxiv.org/html/2204.06607 — paper — 2022
3. Towards Realistic Generative 3D Face Models — https://arxiv.org/pdf/2304.12483 — paper — 2023
4. InsightFace python-package model_zoo.md — https://github.com/deepinsight/insightface/blob/master/python-package/docs/model_zoo.md — repo — 2024
5. Ideal Facial Proportions in Generative Artificial Intelligence (Sridhar et al.) — https://journals.sagepub.com/doi/10.1089/fpsam.2025.0007 — paper — 2025
6. GAF: Gaussian Avatar Reconstruction from Monocular Videos via Multi-view Diffusion — https://arxiv.org/pdf/2412.10209v2 — paper — 2024
7. Sapiens: Foundation for Human Vision Models — https://arxiv.org/abs/2408.12569 — paper — 2024
8. Hunyuan3D-2.1 LICENSE (mirror) — https://gitserver.onethingai.com/ai-models/Hunyuan3D-2.1/raw/branch/main/LICENSE — licence — 2025
9. microsoft/TRELLIS.2-4B model card — https://huggingface.co/microsoft/trellis.2-4b — model card — 2025
10. SphereHead: Stable 3D Full-head Synthesis with Spherical Tri-plane Representation — https://arxiv.org/abs/2404.05680 — paper — 2024
11. PanoHead: Geometry-Aware 3D Full-Head Synthesis in 360° — https://openaccess.thecvf.com/content/CVPR2023/papers/An_PanoHead_Geometry-Aware_3D_Full-Head_Synthesis_in_360deg_CVPR_2023_paper.pdf — paper — 2023
12. InsightFace python-package README — https://github.com/deepinsight/insightface/blob/master/python-package/README.md — repo — 2024
13. Hunyuan3D-2.1 API_TESTING_SUMMARY.md — https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/blob/main/API_TESTING_SUMMARY.md — repo — 2025

**Further reading (by name, not yet linked)**
- Hong et al., "LRM: Large Reconstruction Model for Single Image to 3D", ICLR 2024; Tochilkin et al., "TripoSR", 2024; Xu et al., "InstantMesh", 2024; Tang et al., "LGM", ECCV 2024; Zhang et al., "GS-LRM", ECCV 2024; Boss et al., "SF3D", 2024
- Zhang et al., "CLAY", SIGGRAPH 2024; Tencent, "Hunyuan3D 2.0" and 2.1 technical reports, 2025; Xiang et al., "Structured 3D Latents…" (TRELLIS), CVPR 2025; Li et al., "TripoSG", 2025; StepFun, "Step1X-3D", 2025
- Shi et al., "Zero123++", 2023; Voleti et al., "SV3D", ECCV 2024
- Chan et al., EG3D, CVPR 2022; An et al., "PanoHead", CVPR 2023; Li et al., "SphereHead", ECCV 2024; Kirschstein et al., "GGHead", SIGGRAPH Asia 2024; Roich et al., "Pivotal Tuning" (PTI), ACM TOG 2022
- Papantoniou et al., "Arc2Face", ECCV 2024; Gerogiannis et al., "Arc2Avatar", CVPR 2025 (verify); Babiloni et al., "ID-to-3D", 2024
- Wang et al., "Rodin" (Microsoft), CVPR 2023; Zhang et al., "RodinHD", ECCV 2024
- Gu et al., "DiffPortrait3D", CVPR 2024; Chen et al., "Morphable Diffusion", CVPR 2024; Lyu et al., "FaceLift", 2024–25 (verify venue); Taubner et al., "CAP4D", CVPR 2025
- Karras et al., FFHQ (StyleGAN), CVPR 2019; Deitke et al., Objaverse / Objaverse-XL, 2023; Poole et al., "DreamFusion" (SDS), ICLR 2023
- Shen et al., "FlexiCubes", SIGGRAPH 2023; Zhang et al., "3DShape2VecSet", SIGGRAPH 2023
- Sanyal et al., NoW (RingNet), CVPR 2019; Chai et al., REALY, ECCV 2022

## Verification log (2026-11-20)

1. Hunyuan3D 2.x licence: territory excludes EU, UK, South Korea — **confirmed** (📄) — https://gitserver.onethingai.com/ai-models/Hunyuan3D-2.1/raw/branch/main/LICENSE. Monthly-active-user cap: **unconfirmed** for 2.1 (only a secondary page on 2.0). Original TRELLIS MIT licence: **unconfirmed** by this search (TRELLIS.2 is MIT, see 3).
2. No published NoW/REALY millimetre error for generic generators or head GANs; author's 2-4/3-8/5-15 mm estimates — **unconfirmed** (search found no such report; absence is not proof). Reference: https://now.is.tue.mpg.de/nonmetricalevaluation.html
3. TRELLIS.2: ~4B parameters, O-Voxel, up to 1536³, MIT — **confirmed** (📄); nvdiffrast/nvdiffrec dependencies have separate licences — https://huggingface.co/microsoft/trellis.2-4b. Hunyuan3D 2.5/3.0 hosted-only and 1536³ claim: **unconfirmed**.
4. EG3D 128² render / 512² super-resolution and tri-plane shape: **unconfirmed** (no numbers in results). PanoHead tri-grid and SphereHead spherical tri-planes to suppress back-of-head faces: **confirmed** (📄) — https://arxiv.org/abs/2404.05680 , https://openaccess.thecvf.com/content/CVPR2023/papers/An_PanoHead_Geometry-Aware_3D_Full-Head_Synthesis_in_360deg_CVPR_2023_paper.pdf. FFHQ-F detail not seen in results.

## Verification log, pass 2 (2026-11-20)

1. InsightFace pretrained weights non-commercial research only — **confirmed** (📄; README and model_zoo.md are the same project, not counted as two independent sources) — https://github.com/deepinsight/insightface/blob/master/python-package/README.md , https://github.com/deepinsight/insightface/blob/master/python-package/docs/model_zoo.md. Licences of PanoHead, SphereHead, FaceLift, Arc2Avatar, Arc2Face: **unconfirmed** (nothing in results); badges unchanged.
2. Hunyuan3D octree_resolution default 256 (range 64-512 in 2.1 API docs) — **confirmed** (📄) — https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/blob/main/API_TESTING_SUMMARY.md. TripoSR MC 256: only a third-party config seen (https://github.com/Anant798/Trellis-Studio), **unconfirmed**. TRELLIS FlexiCubes 256^3 and DINOv2 ~518 px conditioning for TRELLIS/Hunyuan3D 2.x: **unconfirmed** (no results); badges stay 🧠.
