# Open-source end-to-end photo-to-3D-face pipelines

> Every runnable open photo→3D-face pipeline is a research codebase. Each needs Linux plus an NVIDIA CUDA GPU and pinned PyTorch, and most also need model files you register to download (FLAME, BFM). Most carry non-commercial terms on the code, the weights or the rasteriser. They fall into three classes. Per-image regressors (DECA/EMOCA, MICA, SMIRK, 3DDFA_V2, Deep3DFaceRecon_pytorch, HRN, FaceVerse) take milliseconds, but they use weak-perspective or affine cameras and PCA-limited identity. Offline FLAME trackers and optimisers (metrical-tracker, VHAP, flame-head-tracker, Pixel3DMM) take about 1–2 s per frame on an RTX 4090 and are much harder to install [1][3][6]. What Blender needs from any of them is not their renders but a mesh on fixed topology (FLAME's 5,023 vertices or a known BFM crop), plus cameras and landmarks. So the add-on should treat them as optional, user-installed initialisers that run outside Blender behind a strict adapter contract. The default path should ship only permissive parts: MediaPipe, our own numpy multi-view perspective fitter, and an MPFB2-style template.
>
> Evidence status: 8 ✅ / 40 📄 / 47 🧠 / 8 ↔️ — 🧠 items are queued for web verification.

*Provenance: this topic had no harvest file and no earlier draft. The URLs below are reused from sibling harvests in this library (multi-view-fitting, single-image-regression, identity-embeddings, facs-expressions, craniometric-landmarks, blender-face-addons, blender-version-status-2026). Everything else is author knowledge (🧠), reliable to about mid-2025.*

## Key facts

**Trackers and optimisers (multi-frame, offline)**
- **flame-head-tracker v4.1** (2 Aug 2025) fits single images and monocular video, offline only [1].
  - Speed: about 0.9 s/frame with landmarks only, about 1.9 s/frame with the photometric term, on an RTX 4090 [1].
  - Needs an NVIDIA GPU on Ubuntu; Windows is untested [1].
  - FLAME files are downloaded separately for licensing reasons, and it credits DECA and MICA code [1].
  - A fork exists [2]. 📄
- **VHAP** fits FLAME by photometric optimisation through a differentiable mesh rasteriser [3].
  - Adaptive regional appearance priors let hair, ears, neck and shoulders align by appearance [3].
  - GAF (CVPR 2025) uses it to track FLAME [8][9]. ✅
- **VHAP setup and limits.**
  - Assets: FLAME 2023 plus vertex masks; FLAME 2020 also works.
  - Landmarks: STAR by default; face-alignment is faster but less accurate.
  - The authors call photometric alignment "sometimes sensitive", regularise the texture with total variation, and say aligning the lower neck together with the head is especially hard [3]. 📄
  - A 2025 update batches frames for about a 3× speed-up, seen only on a Gitee mirror [4]. 📄
- **The Metrical Tracker is an offline, optimisation-based FLAME fitter** [6][7] ✅, and RealDenseFace puts VHAP in the same class [6]. A 2026 multi-camera paper extends it to keypoints from all 15 of its cameras, with MICA giving the identity [7]. 📄
- **metrical-tracker internals** (Zielonka, Bolkart, Thies):
  - takes a MICA identity code;
  - uses MediaPipe dense landmarks plus 68-point landmarks;
  - renders with PyTorch3D, with spherical-harmonics lighting and a photometric term;
  - stores per-frame FLAME parameters plus intrinsics and extrinsics; confirm whether they follow the PyTorch3D or the OpenCV convention before converting (Table 4).

  INSTA and many avatar papers depend on it. 🧠
- **video-head-tracker** (philgras), the NHA tracker, is CC BY-NC 3.0 and appears unmaintained [5]. 📄
- **Pixel3DMM** (Giebenhain et al., 2025) predicts per-pixel normals and FLAME UV coordinates with a fine-tuned DINO-family ViT, then optimises FLAME against them.
  - Its preprocessing chains several third-party models (MICA, a landmark model and face segmentation) 🧠 (moderate confidence).
  - It is the heaviest install here and needs a large-VRAM GPU. 🧠
- **Dense alternatives to sparse-landmark tracking:** iterative dense UV-to-image flow [29] and real-time dense UV-space priors [6]. 📄

**Per-image regressors**
- **DECA** scores 1.18 / 1.46 mm (median / mean) on NoW validation, coarse mesh [10][11]. ✅
  - Outputs (`--saveObj`): a coarse FLAME OBJ with a texture PNG and normal map, plus a separate `_detail.obj`. The detail OBJ is a dense mesh built from the UV displacement and does **not** keep FLAME vertex correspondence. 🧠
  - Its albedo needs `FLAME_albedo_from_BFM.npz`, which you build yourself from BFM with the BFM_to_FLAME tool. Without it, texture is sampled from the photo. 🧠
- **MICA** predicts a metrical, neutral FLAME shape from one image, using face-recognition (ArcFace) features [12]. Most of ArcFace is frozen; only the last three ResNet blocks are fine-tuned [13]. 📄 Both links are the same paper, so they are not independent.
  - NoW: about 0.90 / 1.11 mm [11]. 📄
  - Average FLAME mesh: 1.92 mm, or 1.53 mm once scale is optimised [12]. 📄
- **MICA demo outputs:** a mesh (PLY/OBJ) plus a `.npy` file holding the 300-dimensional identity code, which metrical-tracker reads. 🧠 The demo writes the mesh with vertices ×1000 (millimetres) [34], while FLAME's native unit is metres. 📄 Check one measurement on import.
- **SMIRK** (CVPR 2024) trains geometry through a neural renderer [14]. Its repo snapshot showed about 396 stars and a last update of May 2024 [15]. 📄 It needs FLAME 2020, a MediaPipe landmarker file and a checkpoint hosted on Google Drive. Its encoders are small enough that CPU inference is plausible. 🧠
- **TEASER** (2025) reportedly beats SMIRK on expression accuracy [16]. 📄 That claim is unverified against the paper's tables. ↔️
- **3DDFA_V2** (official repo [17], paper [18]):
  - uses FaceBoxes and claims more than 50 fps [17][18] ✅;
  - detection costs about 15 ms per 720p image, and alignment fails beyond about 90° of pose [17] 📄;
  - a TFLite reimplementation runs on CPU [19] 📄.
- **3DDFA_V2 outputs** (`demo.py -o`): `obj`, `ply`, `depth`, `pncc`, `uv_tex`, `pose`, `2d_sparse`, `2d_dense`, `3d`. Meshes are written in **image-pixel coordinates** with the affine pose baked in, on a no-neck BFM crop (≈38k vertices). You must build Cython extensions (`build.sh`), and Windows is awkward. 🧠
- **Deep3DFaceRecon_pytorch** (sicxu, CVPR-W 2019 method):
  - code is MIT;
  - needs BFM 2009, the `Exp_Pca.bin` expression basis and nvdiffrast;
  - takes 5 landmarks per image from an external detector;
  - writes a vertex-coloured OBJ of the face region only (≈35,709 vertices) and a `.mat` file of the 257 coefficients. 🧠
- **HRN** (CVPR 2023; also on ModelScope) outputs a textured OBJ on BFM topology plus deformation and displacement maps, and has a multi-view variant (MV-HRN). Its licence is unconfirmed. 🧠
- **FaceVerse** (Wang et al., CVPR 2022) is a 3DMM built from East-Asian scans. It has its own topology, ships fitting and tracking code, and its model is released by agreement. The versions and terms change, so verify both. ↔️

**Landmarks and helpers**
- **MediaPipe Face Landmarker** returns 478 3D landmarks and 52 blendshape scores [22][23]. ✅
  - Blendshapes are off by default.
  - Left and right refer to the subject's face, so a mirrored image swaps them [22]. 📄
  - Code and weights are Apache-2.0, and it runs in real time on CPU. 🧠 (see `reconstruction/landmark-detection.md`)
- **A MIT-licensed converter** maps MediaPipe's 478 points to dlib's 68 [24]. 📄
- **The InsightFace pretrained models (used by MICA) are reported to be non-commercial**, separately from the MIT-licensed code [21]. 📄
- **FaceFit-MPFB** is the closest Blender analogue to this project [25]. 📄
  - It is a v0.1 prototype that fits MPFB2 heads to photos using 57 stable points out of MediaPipe's 478.
  - Its solver runs out of process, in an MCP server.
  - It was tested on Blender 4.2.3 LTS with MPFB2 2.0.18.
- **MPFB2 code is GPL-3.0-or-later** [28][30]. ✅

**Cross-cutting install and runtime facts**
- **Gated assets.** FLAME, BFM and the DECA/EMOCA models need a registered account. The `fetch_data.sh`-style scripts prompt for those credentials, so an add-on cannot legally bundle the files or fetch them silently. 🧠
- **chumpy.** The FLAME `.pkl` files unpickle through chumpy. chumpy breaks with NumPy ≥ 1.24 because of removed aliases such as `np.bool`, and it also breaks on newer Python 3. Convert each `.pkl` once to `.npz`. 🧠
- **Rasterisers.** PyTorch3D has prebuilt wheels only for some combinations of Python, torch and CUDA, so a source build takes tens of minutes. nvdiffrast compiles at first use (JIT) 🧠 and carries an NVIDIA Source Code License (1-Way Commercial) that limits others to non-commercial use [32][33]. 📄
- **New GPUs vs pinned environments.** Repos pinned to PyTorch 1.x and CUDA 10/11 do not run on RTX 50-series (Blackwell) cards, which need PyTorch built with CUDA 12.8 or later (sm_120; cu126 and older wheels lack the kernels); the usual error is "no kernel image is available" [36][37]. 📄
- **Mac and Windows.** Apple Silicon has no CUDA, so the trackers and rasterisers are effectively unavailable there. Windows users typically use WSL2. 🧠
- **Blender's Python.** Blender ships its own Python. Installing torch into it is fragile and bloats the add-on. 🧠
  - Blender 5.0 changed `mathutils` buffers to float32 and non-contiguous [26] 📄.
  - Blender 5.2 LTS was released in July 2026 and is supported to July 2028, so it is the support target [27] 📄. Sources disagree on whether 5.3 is already the current stable release (lib: blender-version-status-2026.md).

## Numbers & reference tables

**Table 1 — Pipeline cards (mid-2025 knowledge; slugs, versions and licences are time-sensitive).** Pain is install difficulty, 1 = pip install and 5 = days.

| Pipeline (repo slug) | Input | Topology | Camera | Blender-usable output | GPU need | Pain | Licence (code / assets) | Status |
|---|---|---|---|---|---|---|---|---|
| MediaPipe Face Landmarker | 1 image or video | 478 points; canonical mesh of 468 vertices | 4×4 transform; metric-ish in cm | landmarks (JSON); canonical OBJ | none (CPU) | 1 | Apache-2.0 / Apache-2.0 | 🧠 |
| 3DDFA_V2 (cleardusk/3DDFA_V2) | 1 image | BFM no-neck crop, ≈38k vertices | 3×4 affine | OBJ/PLY in pixel space; pose | none; ONNX on CPU | 2 | MIT / BFM non-commercial | 📄 speed [17]; 🧠 rest |
| Deep3DFaceRecon_pytorch (sicxu) | 1 image + 5 landmarks | BFM face crop, 35,709 vertices | perspective, f≈1015 px at 224 px | vertex-colour OBJ; `.mat` | CUDA (nvdiffrast) | 3 | MIT / BFM + nvdiffrast non-commercial | 🧠 |
| DECA (YadiraF/DECA) | 1 image | FLAME 5,023 + dense detail mesh | weak-perspective | OBJ + texture, normal and displacement maps | CUDA preferred, about 2–4 GB | 3 | MPI non-commercial / FLAME | 🧠 |
| EMOCA v2 (radekd91/emoca, "inferno") | 1 image | FLAME | weak-perspective | OBJ, FLAME codes | CUDA | 4 | MPI non-commercial / FLAME | 🧠 |
| MICA (Zielonka/MICA) | 1 image | FLAME, neutral, 300 shape | none | PLY/OBJ + `identity.npy` | CUDA preferred | 3 | non-commercial / FLAME + InsightFace [21] | ↔️ |
| SMIRK (georgeretsi/smirk) | 1 image | FLAME | weak-perspective | FLAME parameters (export is DIY) | small; CPU plausible | 2–3 | unconfirmed / FLAME | 📄 [14][15]; licence unconfirmed; 🧠 rest |
| HRN (youngLBW/HRN) | 1 image or multi-view | BFM + maps | perspective | textured OBJ + maps | CUDA (nvdiffrast) | 3–4 | unconfirmed / BFM | 🧠 |
| FaceVerse (LizhenWangT/FaceVerse) | 1 image or video | own topology | perspective | OBJ | CUDA | 3 | agreement-gated | ↔️ |
| flame-head-tracker (PeizhiYan) | 1 image or video | FLAME | perspective | FLAME parameters per frame | NVIDIA, Ubuntu | 4 | MIT / FLAME | 📄 [1] |
| metrical-tracker (Zielonka) | video + MICA code | FLAME | perspective (K, R, t) | per-frame checkpoints, meshes | CUDA, PyTorch3D | 4 | non-commercial / FLAME | ↔️ |
| VHAP (ShenhanQian/VHAP) | video; NeRSemble multi-view 🧠 | FLAME 2023 / 2020 | perspective | FLAME parameters (`.npz`), NeRF-style cameras | CUDA, nvdiffrast 🧠 | 4–5 | CC-BY-NC-SA-4.0 (derived from GaussianAvatars; Toyota Motor Europe commercial restriction) / FLAME | 📄 [3]; 🧠 rest |
| Pixel3DMM (SimonGiebenhain/pixel3dmm) | 1 image or video | FLAME | perspective | FLAME mesh and parameters | large VRAM (≥16–24 GB?) | 5 | CC BY-NC 4.0 / FLAME | 📄 [35]; 🧠 rest |
| video-head-tracker (philgras) | video | FLAME | perspective | FLAME parameters | CUDA | 4 | CC BY-NC 3.0 | 📄 [5] |

**Table 2 — Sourced speed and accuracy anchors**

| Item | Value | Unit | Hardware or population | Source | Status |
|---|---|---|---|---|---|
| flame-head-tracker, landmark mode | ≈0.9 | s/frame | RTX 4090, author-reported | [1] | 📄 |
| flame-head-tracker, photometric mode | ≈1.9 | s/frame | RTX 4090, author-reported | [1] | 📄 |
| VHAP batching speed-up (2025) | ≈3× | ratio | mirror only | [4] | 📄 |
| 3DDFA_V2 throughput | >50 | fps | single CPU or GPU | [17][18] | ✅ |
| 3DDFA_V2 detection | ≈15 | ms per 720p frame | ONNX | [17] | 📄 |
| 3DDFA_V2 pose limit | ≈90 | ° | yaw beyond which it fails | [17] | 📄 |
| DECA, NoW validation (coarse) | 1.18 / 1.46 / 1.25 | mm (median / mean / std) | NoW validation subjects | [10][11] | ✅ |
| DECA, third-party reproduction | 1.19 / 1.47 | mm | NoW validation | [20] | 📄 |
| MICA, NoW | 0.90 / 1.11 / 0.92 | mm | NoW, split not stated | [11] | 📄 |
| Average FLAME, scale-fitted | 1.53 (1.92 unscaled) | mm mean | NoW | [12] | 📄 |

**Table 3 — Topology and unit contract for adapters**

| Output | Vertices | Native units | Axes | Correspondence | Status |
|---|---|---|---|---|---|
| FLAME 2020/2023 | 5,023 (9,976 triangles) | m | Y-up, face toward +Z | fixed across all FLAME tools | 🧠 |
| DECA `_detail.obj` | dense, tens of thousands | as coarse | as FLAME | none to FLAME | 🧠 |
| BFM 2009 full | 53,490 | µm-scale raw, rescaled per repo | Y-up | — | 🧠 |
| Deep3DFaceRecon crop | 35,709 | ≈dm (camera at 10 units) | Y-up, face toward +Z | BFM index subset | 🧠 |
| 3DDFA_V2 crop | ≈38,365 | image pixels | image (y flipped) | BFM index subset | 🧠 |
| MediaPipe canonical | 468 (+10 iris points) | cm | Y-up | fixed indices | 🧠 |

**Table 4 — Camera convention conversions** (pose matrices apply on the camera side; derived)

| From | To the Blender camera frame | Status |
|---|---|---|
| OpenCV (x right, y down, z forward) | multiply by diag(1, −1, −1) | 🧠 |
| PyTorch3D (x left, y up, z forward) | multiply by diag(−1, 1, −1) | 🧠 |
| Weak-perspective s, t (DECA, SMIRK) | Z₀ = 2f/(s·W_crop); then lens_mm = f_px·sensor_mm / W_px | 🧠 (lib: single-image-regression.md) |

## Applying this to photo→3D face sculpting in Blender

1. **Pick by licence, then by job.**
   - Shipping commercially: MediaPipe, our own fitter and an MPFB2 base only.
   - Personal or research use, where the user installs the research tools:
     - MICA for identity;
     - SMIRK or EMOCA for expression gating;
     - flame-head-tracker or VHAP for video;
     - Pixel3DMM when a single photo is all you have.
2. **Run them outside Blender.** Use a conda env or Docker image per pipeline, launched by subprocess, never torch inside Blender. Exchange files: mesh (OBJ/PLY), parameters (`.npz`) and a JSON sidecar with cameras (K, R, t, convention), landmarks, units and licence.
3. **Import without breaking correspondence.**
   - Use `wm.obj_import` or `wm.ply_import`, with no Split by Object/Group and no merge-by-distance.
   - Assert the vertex count: 5,023 for FLAME, 35,709 for Deep3D.
   - FLAME through OBJ with Forward −Z / Up Y stands upright facing −Y.
4. **Settle units from one measurement.** Adult intercanthal width should come out at about 31–41 mm and bizygomatic width at about 120–150 mm (lib: `blender/import-export-scans.md`, anthropometric notes). Factors of 10, 100 or 1,000 mean a unit bug: MICA's mm output, Deep3D's decimetres, or 3DDFA_V2's pixels.
5. **Rebuild cameras rather than eyeballing them.**
   - Lens: lens_mm = f_px·sensor_width_mm / image_width_px.
   - Principal-point shift: shift_x = (W/2 − c_x)/max(W, H) and shift_y = (c_y − H/2)/max(W, H).
   - Convert R and t with Table 4.
   - DECA, SMIRK and 3DDFA_V2 have no perspective camera, so solve one with our fitter.
6. **Check before trusting.** Load each photo as a camera background.
   - Landmark reprojection should be ≤1–2 % of inter-ocular distance, and the profile silhouette should match within about 1–1.5 mm at the nose tip and chin.
   - Mirror-compare left and right, because PCA models symmetrise.
7. **Make it sculpt-ready.**
   - FLAME has no mouth interior, an eyelid rim with no thickness, separate eyeball parts and an open neck. BFM crops have no ears or skull.
   - Wrap your artist template onto the result with a landmark warp followed by non-rigid ICP.
   - Keep the pipeline shape as a shape key, add Multires, and sculpt the likeness on level 1–2.
   - Keep DECA or HRN detail as a separate displacement layer; never judge likeness on it.
8. **What goes wrong.**
   - Silent unit or axis errors, and mirrored meshes after Unreal/Unity round-trips.
   - Expression baked into identity: zero ψ and jaw before hand-off.
   - Selfie perspective baked in by weak-perspective models.
   - Photometric trackers locking onto hair, beards or shadows [3].
   - Install rot: environments pinned to old CUDA, Google-Drive quota errors, removed MediaPipe legacy APIs.
   - Licence contamination of a "free" add-on.

## Algorithmic implications

- **Adapter contract.** Each backend returns:
  - `{backend, version, licence_code, licence_assets, topology_id, units, axes, camera_model ∈ {weak_persp, affine, perspective}, K, R, t, convention, landmarks{scheme, xy, σ}, β, ψ, jaw, mesh_path}`;
  - a `measured|generated` flag.

  The engine refuses any mesh whose topology_id is unknown. 🧠 (design)
- **Own FLAME evaluator in numpy.** Load the converted `.npz` (template, shapedirs, exprdirs, posedirs, J_regressor, weights, kintree) and evaluate v = LBS(T + B_S·β + B_E·ψ + B_P(θ)). With that, every FLAME backend reduces to parameters, with no mesh export and no chumpy. 🧠
- **Defaults**, all design values rather than sourced ones; tune them on scans:

| Quantity | Default | Status |
|---|---|---|
| MICA β prior | median over photos; σ_k = max(0.3, spread across photos) for k ≤ 100, σ = 1 above | 🧠 |
| DECA β prior | σ floor 0.6 | 🧠 |
| Huber scale on vertices initialised by MICA / DECA | 1.4 mm / 1.8 mm (lib: single-image-regression.md) | 🧠 |
| Log-scale prior | σ 0.05 for MICA, 0.10 for non-metric backends, 0.01 with a user measurement | 🧠 |
| Landmark σ, inner points (canthi, alar base, mouth corners, MediaPipe) | 1–1.5 % IOD | 🧠 |
| Landmark σ, contour and brow | 2–4 % IOD, inflated by 1/cos(yaw), with a sliding-contour correspondence | 🧠 |
| ψ on photos gated as neutral | N(0, 0.3²) per component; jaw σ ≈ 2–3° | 🧠 |
| Rotation prior from a 3DDFA_V2 or SMIRK initialiser | σ ≈ 5° | 🧠 |
| Focal prior | log-focal σ ≈ 0.03 with EXIF focal length, ≈ 0.15–0.2 without | 🧠 |

- **Consensus, not trust.**
  - Run two or more backends where available.
  - Down-weight views where their β or pose disagree by more than about 2σ.
  - Never let a weak-perspective or affine backend set depth or scale.
  - Do not initialise from 3DDFA_V2 beyond |yaw| ≈ 90° [17].
- **Photometric terms are opt-in.** VHAP-style appearance alignment is "sometimes sensitive" [3]. For identity from uncontrolled stills, use landmarks plus silhouettes first and add photometric refinement only under even lighting.
- **Licence propagation.** Every derived shape key carries the union of its upstream licence flags, and the UI warns when non-commercial data enters a shippable asset.

## Disagreements, myths & open questions

- **Myth: "on GitHub = open source = free to use."**
  - The code may be MIT (3DDFA_V2, Deep3D) while the model files (BFM, FLAME), the rasteriser (nvdiffrast) or the weights (InsightFace [21], dlib-68) are non-commercial.
  - Whether *outputs* inherit those terms depends on each licence's wording. ↔️
- **FLAME 2023 "Open".** The official licence page says the CC BY 4.0 terms apply only to the FLAME 2023 Open model, and that all other FLAME models stay non-commercial [31]. 📄 Whether Open includes the full expression basis is still unconfirmed. 🧠
- **Myth: "the tracker is end-to-end for a photo set."**
  - VHAP and metrical-tracker assume a video, or a calibrated rig, from one camera model.
  - Unordered stills with different focal lengths need our own bundle adjustment.
  - flame-head-tracker does accept single images [1].
- **"Photometric beats landmarks."** True for video avatars [3][8], but unproven for metric identity from mixed-lighting stills. ↔️
- **"Pixel3DMM / TEASER is best."** Each claims its gain on its own benchmark or in summaries [16]. Independent NoW or REALY confirmation is lacking. ↔️
- **MICA output units**: the demo multiplies vertices by 1000, so the files are in mm [34]; verify on import. 📄
- **Open questions:**
  - the code licences of SMIRK and HRN (VHAP is CC-BY-NC-SA-4.0 [3], flame-head-tracker is MIT [1], Pixel3DMM is CC BY-NC 4.0 [35], all 📄 from README text, verified 2026-11-20);
  - measured VRAM for each pipeline;
  - which repos work today with Python 3.11+, NumPy 2 and CUDA 12.8;
  - whether flame-head-tracker supports multi-view stills.

## Sources

1. PeizhiYan flame-head-tracker (v4.1, Aug 2025) — https://github.com/peizhiyan/flame-head-tracker — repo — 2025 (multi-view-fitting harvest)
2. tikammali flame-head-tracker fork — https://github.com/tikammali/flame-head-tracker — repo — n.d. (multi-view-fitting harvest)
3. VHAP: Versatile Head Alignment with Adaptive Appearance Priors (ShenhanQian) — https://github.com/ShenhanQian/VHAP — repo — n.d. (multi-view-fitting harvest)
4. VHAP Gitee mirror (2025 batching update) — https://gitee.com/hu-hanqing/VHAP — code mirror — 2025 (multi-view-fitting harvest)
5. philgras video-head-tracker (CC BY-NC 3.0) — https://github.com/philgras/video-head-tracker — repo — n.d. (multi-view-fitting harvest)
6. RealDenseFace: Real-time Monocular 3D Face Reconstruction from Dense UV-space Priors — https://arxiv.org/pdf/2608.09238 — paper — 2026 (multi-view-fitting harvest)
7. Multi-View Face and Gesture Animation with Dynamic Gaussians — https://arxiv.org/pdf/2608.04722 — paper — 2026 (multi-view-fitting harvest)
8. GAF: Gaussian Avatar Reconstruction from Monocular Videos via Multi-view Diffusion — https://arxiv.org/pdf/2412.10209v2 — paper — 2024 (multi-view-fitting harvest)
9. Tang et al., GAF, CVPR 2025 supplemental — https://openaccess.thecvf.com/content/CVPR2025/supplemental/Tang_GAF_Gaussian_Avatar_CVPR_2025_supplemental.pdf — paper supplement — 2025 (multi-view-fitting harvest)
10. Learning an Animatable Detailed 3D Face Model from In-The-Wild Images (DECA) — https://arxiv.org/abs/2012.04012 — paper — 2021 (single-image-regression harvest)
11. Towards Realistic Generative 3D Face Models — https://arxiv.org/pdf/2304.12483 — paper — 2023 (single-image-regression harvest)
12. Towards Metrical Reconstruction of Human Faces (MICA), ar5iv — https://ar5iv.labs.arxiv.org/html/2204.06607 — paper — 2022 (single-image-regression harvest)
13. Towards Metrical Reconstruction of Human Faces (MICA), arXiv abstract — https://arxiv.org/abs/2204.06607 — paper — 2022 (identity-embeddings harvest)
14. SMIRK: 3D Facial Expressions through Analysis-by-Neural-Synthesis — https://arxiv.org/html/2404.04104 — paper — 2024 (single-image-regression harvest)
15. georgeretsi/smirk: Official PyTorch Implementation of SMIRK — https://github.com/georgeretsi/smirk — repo — 2024 (single-image-regression harvest)
16. TEASER: Token Enhanced Spatial Modeling for Expressions Reconstruction — https://arxiv.org/pdf/2502.10982 — paper — 2025 (single-image-regression harvest)
17. cleardusk/3DDFA_V2 — https://github.com/cleardusk/3DDFA_V2 — repo — 2020 (single-image-regression harvest)
18. Towards Fast, Accurate and Stable 3D Dense Face Alignment — https://arxiv.org/pdf/2009.09960v2 — paper — 2020 (single-image-regression harvest)
19. 1996scarlet/Dense-Head-Pose-Estimation (3DDFA_V2 TFLite reimplementation) — https://github.com/1996scarlet/Dense-Head-Pose-Estimation — repo — 2020 (single-image-regression harvest)
20. SIDER: Single-Image Neural Optimization for Facial Geometric Detail Recovery — https://arxiv.org/pdf/2108.05465 — paper — 2021 (single-image-regression harvest)
21. InsightFace python-package model_zoo.md — https://github.com/deepinsight/insightface/blob/master/python-package/docs/model_zoo.md — repo docs — 2024 (identity-embeddings harvest)
22. MediaPipe Face Landmarker guide — https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker — official docs — n.d. (facs-expressions harvest)
23. MediaPipe FaceLandmarkerResult API — https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/FaceLandmarkerResult — official docs — n.d. (facs-expressions harvest)
24. PeizhiYan/Mediapipe_2_Dlib_Landmarks — https://github.com/PeizhiYan/Mediapipe_2_Dlib_Landmarks/ — repo — n.d. (craniometric-landmarks harvest)
25. VGCLUB/facefit-mpfb — https://github.com/VGCLUB/facefit-mpfb — repo — n.d. (craniometric-landmarks harvest)
26. Blender 5.0 Python API release notes — https://developer.blender.org/docs/release_notes/5.0/python_api/ — official docs — 2025 (blender-version-status-2026 harvest)
27. Blender 5.2 LTS release page — https://www.blender.org/download/releases/5-2/ — official docs — 2026 (blender-version-status-2026 harvest)
28. MPFB2 LICENSE.CODE.md — https://github.com/makehumancommunity/mpfb2/blob/master/LICENSE.CODE.md — repo — n.d. (blender-face-addons harvest)
29. 3D Face Tracking from 2D Video through Iterative Dense UV to Image Flow — https://arxiv.org/html/2404.09819v1 — paper — 2024 (multi-view-fitting harvest)
30. MPFB on Blender Extensions — https://extensions.blender.org/add-ons/mpfb/ — extension listing — n.d. (blender-face-addons harvest)
31. FLAME model license page — https://flame.is.tue.mpg.de/modellicense.html — official site — n.d. (verification 2026-11-20)
32. nvdiffrast LICENSE.txt (Hugging Face mirror; 'Nvidia Source Code License (1-Way Commercial)') — https://huggingface.co/spaces/ginipick/SORA-3D/blob/e3df509037b8d7a49ea8599caebb1c08922cea96/extensions/nvdiffrast/LICENSE.txt — licence text copy — 2020 (verification 2026-11-20)
33. microsoft/TRELLIS issue 298 on nvdiffrast licensing — https://github.com/microsoft/TRELLIS/issues/298 — issue thread — n.d. (verification 2026-11-20)
34. Zielon/MICA demo.py — https://www.github.com/Zielon/MICA/blob/master/demo.py — source code — n.d. (verification 2026-11-20)
35. SimonGiebenhain/pixel3dmm README (CC BY-NC 4.0) — https://github.com/SimonGiebenhain/pixel3dmm — repo — 2025 (verification pass 2, 2026-11-20)
36. PyTorch Forums: Is there a PyTorch build that supports RTX 5090 (sm_120)? — https://discuss.pytorch.org/t/is-there-a-pytorch-build-that-supports-nvidia-rtx-5090-compute-capability-12-0-sm-120/223536 — forum — 2025 (verification pass 2, 2026-11-20)
37. PyTorch Forums: Pytorch support for sm120 (p.4; cu128 wheels include sm_120, cu126 do not) — https://discuss.pytorch.org/t/pytorch-support-for-sm120/216099?page=4 — forum — 2025 (verification pass 2, 2026-11-20)

**Further reading (by name, not yet linked)**
- Feng, Feng, Black, Bolkart — DECA, SIGGRAPH 2021; Daněček, Black, Bolkart — EMOCA, CVPR 2022
- Zielonka, Bolkart, Thies — Towards Metrical Reconstruction of Human Faces (MICA + metrical tracker), ECCV 2022; INSTA, CVPR 2023
- Qian et al. — GaussianAvatars, CVPR 2024 (origin of VHAP)
- Retsinas et al. — SMIRK, CVPR 2024
- Giebenhain et al. — Pixel3DMM: Versatile Screen-Space Priors for Single-Image 3D Face Reconstruction, 2025
- Guo, Zhu, Yang, Yang, Lei, Li — Towards Fast, Accurate and Stable 3D Dense Face Alignment (3DDFA_V2), ECCV 2020
- Deng et al. — Accurate 3D Face Reconstruction with Weakly-Supervised Learning (Deep3DFaceRecon), CVPR-W 2019
- Lei et al. — HRN, CVPR 2023; Wang et al. — FaceVerse, CVPR 2022
- Li, Bolkart, Black, Li, Romero — FLAME, SIGGRAPH Asia 2017; Paysan et al. — BFM 2009
- Grassal et al. — Neural Head Avatars from Monocular RGB Videos, CVPR 2022
- Ravi et al. — Accelerating 3D Deep Learning with PyTorch3D, 2020; Laine et al. — Modular Primitives for High-Performance Differentiable Rendering (nvdiffrast), SIGGRAPH Asia 2020
- Kartynnik et al. — Real-time Facial Surface Geometry from Monocular Video on Mobile GPUs (MediaPipe Face Mesh), CVPR-W 2019

## Verification log (2026-11-20)

- FLAME 2023 Open under CC BY 4.0, other FLAME models non-commercial: **confirmed** (📄) — https://flame.is.tue.mpg.de/modellicense.html [31]. The "possibly without the full expression basis" part was not addressed by the source and stays unconfirmed.
- nvdiffrast under NVIDIA Source Code License, non-commercial for others: **confirmed** (📄), with the exact licence name "Nvidia Source Code License (1-Way Commercial)" — https://huggingface.co/spaces/ginipick/SORA-3D/blob/e3df509037b8d7a49ea8599caebb1c08922cea96/extensions/nvdiffrast/LICENSE.txt [32] (mirror of the licence text, not the official repo) and https://github.com/microsoft/TRELLIS/issues/298 [33]. Which pipelines use it was not checked.
- MICA demo writes vertices x1000 (mm): **confirmed** (📄) — https://www.github.com/Zielon/MICA/blob/master/demo.py [34]. The 300-dimension size of identity.npy was not shown in the snippet; stays unconfirmed.
- 3DDFA_V2 OBJ/PLY in image-pixel coordinates on a ~38,365-vertex no-neck BFM crop: **unconfirmed** (🧠) — searches found no vertex count for bfm_noneck_v3 (a different project cites 35,709 for its own BFM, and SynergyNet about 45K for a neck-free BFM). Check by counting vertices in an exported OBJ.

## Verification log, pass 2 (2026-11-20)

- Code licences of VHAP, flame-head-tracker, SMIRK, Pixel3DMM: **partly confirmed** (📄, README text via search summary, not LICENSE files). VHAP is CC-BY-NC-SA-4.0 with a Toyota Motor Europe commercial-use restriction inherited from GaussianAvatars (https://github.com/ShenhanQian/VHAP [3]); flame-head-tracker is MIT, with dependency terms still applying (https://github.com/peizhiyan/flame-head-tracker [1]); Pixel3DMM is CC BY-NC 4.0 (https://github.com/SimonGiebenhain/pixel3dmm [35]). SMIRK: **unconfirmed** (🧠), no result for the repo.
- RTX 50-series (Blackwell, sm_120) fails on old pinned PyTorch and needs a CUDA 12.8+ build: **confirmed** (📄) by two forum threads — https://discuss.pytorch.org/t/is-there-a-pytorch-build-that-supports-nvidia-rtx-5090-compute-capability-12-0-sm-120/223536 [36] and https://discuss.pytorch.org/t/pytorch-support-for-sm120/216099?page=4 [37]. Both are user and moderator forum posts, not official release notes, so kept at 📄. The "PyTorch 1.x / CUDA 10/11" detail is consistent but not stated explicitly.
