# AI-assisted head creation: practitioner reviews

> By 2025–26, artists routinely start heads with image-to-3D generators (Hunyuan3D, TRELLIS, Rodin, Meshy, Tripo) or face fitters (KeenTools FaceBuilder, Reallusion Headshot, Mesh to MetaHuman). The verdict is consistent: a plausible bust in minutes, a likeness almost never. Generators carry identity mostly in the projected photo texture; in clay the head reads as "a relative", with invented profile depth, fused eyes and lips, helmet hair and triangle-soup topology that must be wrapped before sculpting. Face fitters keep clean topology but inherit a low-dimensional prior, so the likeness is still sculpted by eye against solved cameras. Rule: "AI for mass and speed, real photos for truth"; use AI output as a weak, region-weighted shape prior, never as landmark ground truth. No harvest or earlier draft existed, so all of this is author synthesis to verify; versions, licences and prices go stale within months.
>
> Evidence status: 0 ✅ / 6 📄 / 47 🧠 / 20 ↔️ — verified 2026-11-20; remaining 🧠 items are unverified.

## Key facts

**What each tool family gives you**
- **Generic generators** run diffusion or flow models over learned 3D shape latents, then extract a surface (marching cubes, FlexiCubes-type). Training data is mostly Objaverse-class objects and game assets; real-person head scans are rare. Expect a well-formed generic head, not this person 🧠
- **Hunyuan3D (Tencent).** 2.0 (Jan 2025): shape DiT plus a separate texture model (Paint). Variants 2mini, 2mv (multi-view input) and 2.1 (mid-2025, open PBR texturing); 2.5 and 3.x reported hosted only. The Tencent Hunyuan Community License excludes the EU, UK and South Korea and caps monthly users (1M MAU threshold) 📄 [1][2]. Community view: best open geometry; faces sharp but averaged ↔️ (time-sensitive)
- **TRELLIS (Microsoft, Dec 2024; CVPR 2025).** Structured latent on a sparse 64³ voxel grid, decoded to Gaussians, radiance fields or mesh. MIT code and weights, but some CUDA rasteriser dependencies (nvdiffrast, nvdiffrec) carry separate NVIDIA terms restricting use to research/non-commercial 📄 [3][4]; ≥16 GB VRAM. TRELLIS.2 released Dec 2025 (17 Dec), MIT code and weights, same NVIDIA dependency caveat 📄 [3][5]. Community view: good silhouettes, soft faces ↔️
- **Rodin (Hyper3D, Deemos):** commercial; quad-mesh mode, multi-image input, T/A pose; reachable from Blender via the community "Blender MCP" bridge. Deemos also runs ChatAvatar, a face product from its DreamFace research. Unrelated to Microsoft's 2023 "Rodin" avatar paper 🧠
- **Meshy and Tripo:** freemium services with Blender bridges, quad/triangle remeshing to a target count and humanoid auto-rigging. Open spin-offs: TripoSR (2024, MIT, with Stability AI) and TripoSG. Meshy: free-plan outputs are CC BY 4.0 (attribution required), paid plans private 📄 [6]; Tripo's terms not verified ↔️ (verify per vendor)
- **Face fitters.** FaceBuilder: pin-based fit of a fixed KeenTools head, neural auto-pins since 2021.1 (`community/blenderartists-forum.md`), GPL front-end, closed core, subscription. Headshot 2 (Character Creator 4): photo mode plus a mesh mode that wraps CC topology onto any head mesh, AI output included. Mesh to MetaHuman (Unreal). All keep production topology and rigs; likeness is bounded by their shape spaces 🧠

**Community verdicts on likeness (2025–26)**
- **"The texture does the likeness."** The front view convinces because the input photo is projected onto it; in clay or matcap the geometry reads as generic. Experienced artists judge AI heads untextured first 🧠
- **Depth is invented.** From one frontal photo the generator guesses nose and chin projection, brow-to-eye depth, forehead slope and occiput. Distinctive profiles (aquiline, very flat, retrognathic) regress toward the training mean 🧠
- **Eyes and mouth are fused:** no eyeball, no lid thickness, painted lashes, lips welded shut with no mouth bag, smeared canthi and commissures. Print users accept this; sculptors cut and rebuild 🧠
- **Hair and beards** become a solid shell that inflates the cranium and hides hairline and jaw. Back of head and ears are hallucinated; ears are often generic, small or at the wrong height 🧠
- **Baked lighting.** Albedo keeps the photo's highlights and shadows; PBR outputs (Hunyuan3D 2.1, Rodin) reduce but do not remove it on skin 🧠
- **Selfie perspective is baked in.** Generators assume a canonical camera, so an arm's-length photo yields a big nose and narrow face in 3D (perspective table in `community/reddit-face-from-photos.md`) 🧠
- **Multi-view input needs consistent views.** Hunyuan3D 2mv expects front, left, back and right at 90°; real photos with differing focal lengths and poses give doubled brows and lids. AI turnaround sheets (e.g. Gemini 2.5 Flash Image, "Nano Banana", 2025) are consistent but hallucinate the profile ↔️
- **Rankings change monthly.** Preference arenas (Hugging Face "3D Arena") rank object appeal, not likeness; no public benchmark scores these tools on real faces against scans ↔️

**Topology and usability**
- **Raw output:** 10⁵–10⁶ triangles, uneven density, floaters, internal shells, non-manifold edges, holes at ears and nostrils; unit-cube scale; GLB is Y-up 🧠
- **Vendor "quad remesh"** gives quads, not animation edge flow (no loops around eyes and mouth, misplaced poles). Consensus: wrap a known base (FaceBuilder head, CC4 via Headshot 2, MetaHuman, MPFB2, own template) rather than retopologise by hand ↔️
- **Wrappers need readable eyes and mouth.** Mesh to MetaHuman and Headshot mesh mode want open eyes with lid margins, a closed neutral mouth and a clear forehead; fused eyes or helmet hair break their landmark tracking 🧠
- **Blender-native route:** Voxel Remesh then QuadriFlow, Quad Remesher or Instant Meshes for a sculpt proxy; for production, landmark-align a template, Shrinkwrap or Surface Deform it, then reproject with Multires 🧠

**Practice, ethics, licensing**
- **Privacy.** Cloud generators need face photos uploaded; check retention and training-use terms. Under GDPR, face data processed to identify someone is special-category biometric data. Local options: TRELLIS (MIT); Hunyuan3D outside excluded territories ↔️
- **Consent.** A real person's head needs their consent; vendor terms forbid uploading others' photos without rights 🧠
- **Disclosure.** Steam requires AI-content disclosure (since 2024); some studios and clients ban AI-generated assets over training-data provenance; ArtStation communities are hostile. Label AI-started heads ↔️

## Numbers & reference tables

**Table 1 — Tool landscape for real-person heads** (all access, licence and version facts time-sensitive)

| Tool | Type | Access / licence (verify) | Output | Verdict for a real person | Badge |
|---|---|---|---|---|---|
| Hunyuan3D 2.0 / 2.1 / 2mv | open generator | Tencent community licence; excludes EU/UK/KR [1][2] | dense tris; PBR in 2.1 | best open blockout; averaged identity | ↔️ |
| Hunyuan3D 2.5 / 3.x | hosted | Tencent cloud terms | higher-res tris | sharper; same depth guessing | ↔️ |
| TRELLIS | open generator | MIT; some deps non-commercial [3][4] | mesh / Gaussians | soft faces; good mass | 📄 |
| TRELLIS.2 | open generator | MIT, Dec 2025 [3][5] | PBR mesh | unreviewed for likeness | 📄 |
| TripoSR / TripoSG | open generator | MIT | tris | blockout only | 🧠 |
| Stable Fast 3D / SPAR3D | open generator | Stability Community License | UV'd tris | fast, low detail | 🧠 |
| Tripo, Meshy | services | freemium credits; Meshy free outputs CC BY 4.0, paid private [6]; Tripo unverified | tris or quads, auto-rig | blockout, figurines | ↔️ |
| Rodin (Hyper3D) | service | paid credits | quad mode, PBR | cleanest service mesh; generic face | 🧠 |
| KeenTools FaceBuilder | photo fitter (Blender) | subscription; closed core | fixed head topology, UVs, blendshapes | best quick base; sculpt after | 🧠 |
| Headshot 2 (CC4) | photo or mesh wrapper | paid plug-in | CC4 rigged head | mesh mode is the useful part | 🧠 |
| Mesh to MetaHuman | mesh wrapper (UE) | free with UE; outside-UE use changed 2025 | MetaHuman rig | best rig; needs clean eyes and mouth | ↔️ |

**Table 2 — Local inference requirements** (single image, consumer or datacentre GPU; vendor READMEs as remembered)

| Model | VRAM | Time per head | Badge |
|---|---|---|---|
| TripoSR | ≈6 GB | < 1 s (A100 class) | 🧠 |
| Stable Fast 3D | ≈6–7 GB | ≈1 s | 🧠 |
| TRELLIS image-large | ≥16 GB | ≈10–60 s | 🧠 |
| Hunyuan3D 2.0 | ≈6 GB shape; ≈16 GB with texture | ≈0.5–3 min | 🧠 |
| Hunyuan3D 2.1 | ≈10 GB shape; ≈21 GB texture; ≈29 GB both | ≈1–5 min | 🧠 |

**Table 3 — Extraction grid versus likeness detail** (arithmetic: voxel = bounding-box extent ÷ grid resolution; features need about 2 voxels)

| Grid | Voxel, head-only box 0.25 m | Voxel, bust box 0.45 m | Smallest feature, head-only | Badge |
|---|---|---|---|---|
| 64³ | 3.9 mm | 7.0 mm | ≈8 mm | 🧠 |
| 256³ | 0.98 mm | 1.76 mm | ≈2 mm | 🧠 |
| 512³ | 0.49 mm | 0.88 mm | ≈1 mm | 🧠 |
| 1024³ | 0.24 mm | 0.44 mm | ≈0.5 mm | 🧠 |

Likeness-bearing relief (upper-lid crease, alar groove, philtral columns, vermilion ridge, nasolabial fold) is about 0.5–5 mm 🧠. The grid is an upper bound: learned detail is coarser. A busy bust input halves effective resolution on the face.

**Table 4 — Face size inside the conditioning image** (DINOv2-style encoders at ≈518 px 🧠; subject fills 90% of the frame height; bizygomatic width 140 mm, IPD 63 mm)

| Framing | Field height | Face width (px) | IPD (px) | Badge |
|---|---|---|---|---|
| Full body | 1.75 m | ≈37 | ≈17 | 🧠 |
| Waist up | 0.90 m | ≈73 | ≈33 | 🧠 |
| Head and shoulders | 0.40 m | ≈163 | ≈73 | 🧠 |
| Head only | 0.27 m | ≈242 | ≈109 | 🧠 |

**Table 5 — Multires density on a 10k-quad head base** (assumed surface area ≈0.13 m², from the "head and neck ≈ 9% of body surface" rule; edge ≈ √(area/faces))

| Level | Faces | Mean edge | Enough for | Badge |
|---|---|---|---|---|
| 0 | 10 k | 3.6 mm | primary forms | 🧠 |
| 1 | 40 k | 1.8 mm | AI-mesh detail at 256³ | 🧠 |
| 2 | 160 k | 0.9 mm | lid creases, alar groove | 🧠 |
| 3 | 640 k | 0.45 mm | fine wrinkles | 🧠 |
| 4 | 2.56 M | 0.23 mm | pores (with displacement) | 🧠 |

**Table 6 — Where an artist's time goes** (wide practitioner estimates for one realistic head)

| Stage | Time | Badge |
|---|---|---|
| AI generation (several seeds) | 1–15 min | ↔️ |
| Cleanup and wrap to clean topology | 1–4 h | ↔️ |
| Likeness sculpt against solved cameras | 8–40 h | ↔️ |
| Eyes, hair, texture | 4–20 h | ↔️ |

## Applying this to photo→3D face sculpting in Blender

1. **Decide the AI's role.** For blockouts, figurines and stylised work it can be the main source. For a likeness the backbone is the solved-camera pipeline (`blender/reference-camera-setup.md`); AI is optional mass.
2. **Feed the generator well:** one neutral photo, eyes open, lips closed, shot from ≥1.5 m, flat light, hair back, filters off; crop to the head (Table 4); remove the background. Multi-view generators get real photos rectified to a level eye line and equal scale, never AI turnarounds.
3. **Import** with the glTF importer, apply transforms, check the face points to −Y, scale from the metric solve or to IPD 63 mm (metric units, scale 1.0).
4. **Clean:** separate loose parts and delete floaters; Merge by Distance (≈0.01 mm), Delete Loose, Fill Holes; Voxel Remesh at 0.5–1 mm for a watertight proxy.
5. **Align** with Umeyama on about 8 stable landmarks (eye corners, nasion, subnasale, mouth corners, pogonion), then cycle every solved camera with the photo overlaid at 50% or in Difference mode.
6. **Triage regions.** Keep the frontal mass. Replace AI eyes with eyeballs (≈24 mm, iris ≈11.7 mm); cut the mouth; strip the hair shell and rebuild the cranium (adult head length ≈18–20 cm, breadth ≈14–16 cm, Farkas-type norms 🧠); place a template ear from photos.
7. **Transfer to clean topology:** landmark-align the template, Shrinkwrap (Nearest Surface Point) with corrective smoothing, masking nostrils, lids and ears where projection folds; or use Headshot 2 or Mesh to MetaHuman. Then Multires and reproject.
8. **Sculpt the likeness in clay:** matcap, cycle cameras after each pass, thumbnail and flipped views, symmetry off after blockout.
9. **Texture from photos** projected through the solved cameras, then de-light; discard the AI albedo.

**What goes wrong**

| Symptom | Cause | Fix |
|---|---|---|
| Right when textured, wrong in clay | texture carries the identity | judge in clay; sculpt depth against profile |
| Head wide, short, flat at back | hair shell, invented occiput | strip hair; cranium priors |
| Big nose, narrow face | selfie baked in | regenerate from a distant photo or discard AI nose |
| Doubled brows or lids | inconsistent multi-view input | single view, or rectify views |
| Creases at nostrils, lids, ears | Shrinkwrap projecting into concavities | mask; Surface Deform; non-rigid ICP |
| Mesh to MetaHuman fails | fused eyes, helmet hair | sculpt sockets and lid margins; remove hair |
| Smile in the neutral | expression in the source photo | neutral photo, or fit expression separately |

## Algorithmic implications

- **Ingest (new `load_reference_mesh`):** GLB→OBJ on the Blender side, then `read_obj`; drop components with <1% of vertices; recompute normals.
- **Auto-orient:** render the AI mesh orthographically from 8–12 yaws, run the 2D landmark detector, take the most confident and most symmetric frontal view, then `umeyama` (with scale) to the template landmarks; report `procrustes_rmse` in IOD units.
- **Scale** comes from the metric multi-view solve (`reconstruct_landmarks`); otherwise use IPD 63 ± 3.5 mm (`community/reddit-face-from-photos.md`).
- **Region-weighted point-to-plane term** r = n·(x − closest point), with Huber δ = 2σ. Weight by c = cos(surface normal, conditioning view direction):

| Region | σ (mm) | Badge |
|---|---|---|
| Frontal skin, c > 0.7 | 3–5 | 🧠 |
| Lateral face, 0.3 < c ≤ 0.7 | 6–10 | 🧠 |
| Back of head, under chin, c ≤ 0.3 | ≥15 or off | 🧠 |
| Hair or beard mask, eyes, lips interior, ears | off | 🧠 |

- **Hierarchy.** Photo landmarks (σ 0.02–0.03 IOD) and `fit_silhouettes` outrank anatomical priors, which outrank the AI term. Cap the AI term's total information per region at about 25% of the landmark information (heuristic 🧠).
- **Non-rigid ICP defaults** (Amberg et al., 2007): stiffness annealed from about 50 to 1 over 5–8 steps. Reject correspondences farther than 10 mm, with normals more than 45° apart, or on a boundary. Finish with `laplacian_deform` anchored at landmarks.
- **Depth-contradiction detector.** Compare AI depth at glabella, pronasale, subnasale and pogonion with `triangulate_points`. If |Δ| > 3σ, switch the AI term off in that region and report "AI depth contradicts photos".
- **Perspective guard.** If the conditioning photo is in the solved set and its f₃₅ < 35 mm (distance under about 0.6 m), multiply the AI depth weights by 0.25.
- **Never use AI eyes or lips.** Insert template eyeballs (24 mm, iris 11.7 mm); landmarks come only from real photos.
- **Write vertex attributes** `ai_prior_weight` and `confidence` to the Blender mesh for use as sculpt masks.
- **Texture–clay gap QA.** Compute the identity-embedding cosine on textured and matcap renders through the solved cameras (`reconstruction/identity-embeddings.md`). A large gap means the geometry is not carrying the likeness. Thresholds are uncalibrated, so compare runs relative to each other.

## Disagreements, myths & open questions

- ↔️ **"AI is good enough for likeness."** True for a recognisable textured thumbnail or a 5 cm figurine; false for a clay sculpt seen in profile.
- ↔️ **Vendor quad remesh as "production-ready".** Fine for static props and prints; riggers reject its edge flow.
- ↔️ **AI turnarounds as multi-view input.** They are consistent but fictional; they improve mesh quality, not truth.
- ↔️ **Open versus hosted.** Hosted Hunyuan 3.x, Rodin and Tripo are often rated sharper. Open models win on privacy and control. Rankings flip within months.
- **Myth: more triangles means more detail.** Latent resolution caps detail; a dense mesh of a soft surface is still soft 🧠
- **Myth: PBR output means de-lit.** Skin albedo still carries shading 🧠
- **Myth: Hyper3D Rodin is Microsoft's Rodin.** Only the name is shared 🧠
- **Open questions:** mm error of 2025–26 generators against real-face scans (NoW-style protocol)? Do face-specialised LRMs (e.g. KaoLRM, `reconstruction/single-image-regression.md`) close the gap? Current free-tier licences, Hunyuan territory terms, TRELLIS.2 terms? Do studio AI bans cover AI-started, fully re-sculpted heads?

## Sources

Numbered sources added in verification, 2026-11-20:

1. Tencent Hunyuan 3D 2.0 Community License (Hugging Face): https://huggingface.co/tencent/Hunyuan3D-2/blob/main/LICENSE
2. DeepWiki, Hunyuan3D-2 license and terms (secondary; MAU threshold): https://deepwiki.com/Tencent/Hunyuan3D-2/9-license-and-terms
3. Microsoft TRELLIS.2-4B model card, MIT and dependency licence notes: https://huggingface.co/microsoft/TRELLIS.2-4B/blob/main/README.md
4. microsoft/TRELLIS issue 298, nvdiffrast non-commercial licence: https://github.com/microsoft/TRELLIS/issues/298
5. CG World Japan, TRELLIS.2 release report (secondary; 17 Dec): https://cgworld.jp/flashnews/01-202601-TRELLIS2.html
6. Meshy docs, Pricing & Credits (free plan CC BY 4.0, paid private): https://docs.meshy.ai/pricing

Otherwise no harvested sources exist for this topic. Related notes: `community/reddit-face-from-photos.md`, `community/blenderartists-forum.md` (FaceBuilder release threads), `blender/blender-face-addons.md`, `reconstruction/single-image-regression.md`, `reconstruction/identity-embeddings.md`, `blender/reference-camera-setup.md`.

**Further reading (by name, not yet linked)**
- Xiang et al., "Structured 3D Latents for Scalable and Versatile 3D Generation" (TRELLIS), CVPR 2025
- Tencent Hunyuan3D team, "Hunyuan3D 2.0: Scaling Diffusion Models for High Resolution Textured 3D Assets Generation", technical report, 2025
- Tencent Hunyuan Community License Agreement (Hunyuan3D repositories)
- Tochilkin et al., "TripoSR: Fast 3D Object Reconstruction from a Single Image", 2024
- Hong et al., "LRM: Large Reconstruction Model for Single Image to 3D", ICLR 2024
- Boss et al., "SF3D: Stable Fast 3D Mesh Reconstruction with UV-unwrapping and Illumination Disentanglement", 2024
- Deitke et al., "Objaverse: A Universe of Annotated 3D Objects", CVPR 2023; Objaverse-XL, NeurIPS 2023
- Oquab et al., "DINOv2: Learning Robust Visual Features without Supervision", 2023
- Shen et al., "Flexible Isosurface Extraction for Gradient-Based Mesh Optimization" (FlexiCubes), SIGGRAPH 2023
- Zhang et al., "DreamFace: Progressive Generation of Animatable 3D Faces under Text Guidance", ACM TOG 2023
- Wang et al., "Rodin: A Generative Model for Sculpting 3D Digital Avatars Using Diffusion", CVPR 2023 (Microsoft; unrelated to Hyper3D Rodin)
- Amberg, Romdhani, Vetter, "Optimal Step Nonrigid ICP Algorithms for Surface Registration", CVPR 2007
- Umeyama, "Least-squares estimation of transformation parameters between two point patterns", IEEE TPAMI 1991
- Farkas, *Anthropometry of the Head and Face*, 1994
- KeenTools FaceBuilder for Blender documentation; Reallusion Headshot 2 documentation; Epic Games MetaHuman documentation (Mesh to MetaHuman)

## Verification log (2026-11-20)

- Hunyuan3D licence territory excludes EU/UK/South Korea, MAU cap: confirmed (cap is 1M MAU per secondary source). https://huggingface.co/tencent/Hunyuan3D-2/blob/main/LICENSE ; https://deepwiki.com/Tencent/Hunyuan3D-2/9-license-and-terms . "Best open generator" is a community opinion, left ↔️.
- AI mesh accuracy 3-5 mm frontal / 6-10 mm lateral: unconfirmed. Search found no NoW-style mm benchmark for Hunyuan3D or TRELLIS (NoW suits parametric face models). The sigmas remain 🧠 heuristics.
- TRELLIS MIT with NVIDIA non-commercial dependencies; TRELLIS.2 late-2025 release, MIT: confirmed (released 17 Dec 2025). https://huggingface.co/microsoft/TRELLIS.2-4B/blob/main/README.md ; https://github.com/microsoft/TRELLIS/issues/298 ; https://cgworld.jp/flashnews/01-202601-TRELLIS2.html
- Meshy free tier CC BY 4.0, paid private: confirmed for Meshy ("public" not stated; CC BY 4.0 is the stated term). https://docs.meshy.ai/pricing . Tripo: unconfirmed.
