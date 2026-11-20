# NeRF and Gaussian-splatting head avatars

> Neural head avatars (NeRF, point and Gaussian-splat families) are optimised to *re-render* a person under new expressions and views, not to recover a sculptable surface. Their output is a radiance field or 10⁴–10⁵ semi-transparent primitives, almost always driven by a tracked FLAME mesh. For a Blender likeness workflow they are worth three things: the refined FLAME fit and cameras; a camera-registered renderer that produces neutral reference views from any virtual camera; and a mid-frequency point and depth signal usable as a robust, confidence-weighted data term. GaussianAvatars (multi-view, mesh-bound) is the best template for engine design. Only the surfel (2DGS/SurFhead) and SDF (IMavatar, MonoNPHM) branches produce geometry close to sculpt quality. No harvest or earlier draft existed for this topic, so every claim is expert knowledge awaiting verification.
>
> Evidence status: 0 ✅ / 0 📄 / 56 🧠 / 14 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Lineage and representations**
- **2021–2022 lineage:**
  - **NeRFace** (CVPR 2021) is an expression-conditioned dynamic NeRF.
  - **Neural Head Avatars** (NHA, CVPR 2022) adds MLP offsets and a neural texture to an upsampled FLAME. The output is an explicit mesh, but hair becomes a shell.
  - **IMavatar** (CVPR 2022) learns a canonical SDF with learned blendshape and skinning fields. It gives the cleanest marching-cubes surface of the cohort but trains slowly.

  🧠
- **PointAvatar** (Zheng et al., CVPR 2023) deforms a canonical point cloud with learned FLAME-style blendshapes and LBS. The cloud grows coarse-to-fine while point radii shrink, and colour splits into albedo and normal-dependent shading. There is no surface, but thin structures (hair, glasses) come out better than with meshes. 🧠
- **INSTA** (Zielonka, Bolkart, Thies, CVPR 2023) is an instant-NGP hash-grid NeRF. Each sample is mapped to canonical space through the *nearest triangle* of the tracked FLAME, in that triangle's local frame. It trains in under ~10 min from monocular video tracked by the MICA-based metrical tracker, typically at 512² crops. 🧠
- **NeRSemble** (Kirschstein et al., ACM TOG 2023) is both a dataset and a method. The method combines a deformation field with an *ensemble of hash grids* blended per frame. It replays a captured sequence from new views and is **not** animatable. 🧠
- **GaussianAvatars** (Qian et al., CVPR 2024) binds each 3D Gaussian to a FLAME triangle (Table 4).
  - It starts with one Gaussian per triangle.
  - In densification, children inherit the parent's triangle, and every triangle keeps at least one Gaussian.
  - Per-frame FLAME pose and expression are fine-tuned jointly with the Gaussians.
  - It adds teeth to FLAME and trains on 16-view NeRSemble data.
  - Its tracker was released as VHAP; sourced facts are in `reconstruction/multi-view-fitting.md`.

  🧠
- **MonoGaussianAvatar** (Chen et al., SIGGRAPH 2024) puts Gaussians on PointAvatar's learned deformation field, from monocular video. Its canonical space is not FLAME-aligned, and it extrapolates more weakly than mesh-bound designs. 🧠
- **Mesh-embedded monocular variants (2024):**
  - **FlashAvatar** (CVPR 2024): UV-sampled Gaussians plus an expression-conditioned offset MLP, about 300 fps at 512².
  - **SplattingAvatar** (CVPR 2024): barycentric coordinates plus a normal offset, with Gaussians "walking" between triangles.
  - **3D Gaussian Blendshapes** (SIGGRAPH 2024): one Gaussian blendshape per expression basis vector.

  🧠
- **Gaussian Head Avatar** (Xu et al., CVPR 2024) is multi-view. It initialises from an SDF→DMTet mesh and uses a super-resolution network for 2K output. **NPGA** (SIGGRAPH Asia 2024) drives Gaussians with a deformation prior distilled from MonoNPHM. 🧠
- **Relightable avatars** need a light stage: Relightable Gaussian Codec Avatars (CVPR 2024), and URAvatar (SIGGRAPH Asia 2024), which adapts a universal prior to a phone scan. Their albedo and normals suit sculpting better than baked-lighting avatars, but code and data are restricted. ↔️
- **Few-shot and feed-forward (2024–2025):**
  - GAGAvatar (NeurIPS 2024) and LAM (SIGGRAPH 2025) work from one image.
  - Avat3r (2025) works from a few images.
  - CAP4D (CVPR 2025) takes 1 to about 100 images through morphable multi-view diffusion.
  - GAF (CVPR 2025) takes monocular video plus multi-view diffusion.

  All of them **hallucinate** unseen regions plausibly rather than measuring them. 🧠
- **Geometry-oriented successors.** SurFhead (ICLR 2025) binds 2D Gaussian surfels to the mesh with Jacobian-based affine blending, which gives far better depth and normals. MeGA-style hybrids model the skin as a mesh with a neural texture and the hair as Gaussians. 🧠 (venues to verify)
- **"Best method" claims for 2025–2026 are time-sensitive.** Current trends are diffusion priors, surfels, relightability and feed-forward models. ↔️

**Inputs**
- **NeRSemble capture:**
  - 16 synchronised cameras, about 7.1 MP (3208×2200) at 73 fps;
  - more than 220 subjects and more than 4,700 sequences, under a research-only agreement;
  - mostly frontal and side coverage, so the back of the head is weak;
  - GaussianAvatars trains on frames downsampled to about 802×550.

  🧠
- **Monocular methods** need 1–3 min of video, a tracked FLAME, matting masks and often face-parsing masks. Quality at large yaw depends on the yaw the video actually covered. 🧠
- **The tracker is the bottleneck.** Every method assumes accurate per-frame FLAME and cameras. Tracking error becomes blur, doubled features, or Gaussians compensating off the surface. 🧠

**Geometry and mesh extraction**
- **3DGS geometry is ill-defined.** Depth is an alpha-blended expectation or a median, and the normal is a heuristic: the axis of smallest scale. Primitives drift millimetres to centimetres off the skin wherever that lowers photometric loss, such as hair, highlights, lashes and the mouth interior. 🧠
- **View-dependent colour fakes geometry.** SH colour (degree 3) and NeRF view-dependence absorb specular highlights, causing dents or floaters on the forehead and nose tip. 🧠
- **Extraction routes:**
  - NeRF density → marching cubes: threshold-sensitive, foggy hair.
  - SDF → marching cubes: clean and watertight.
  - 3DGS → SuGaR (Poisson), 2DGS (TSDF of rendered depth) or Gaussian Opacity Fields (opacity level set).
  - Mesh-bound avatars: take the refined FLAME.

  🧠
- **Avatar papers do not measure geometry in millimetres.** They report PSNR, SSIM and LPIPS, plus identity similarity for one-shot methods. 🧠

**Formats, tooling, licences**
- **3DGS PLY at SH degree 3** has 62 float32 properties per Gaussian (Table 3), about 25 MB per 100k Gaussians. GaussianAvatars-style repos also store each Gaussian's parent triangle and the FLAME parameters, in a repo-specific layout. 🧠
- **Blender has no native 3DGS renderer** as far as I know. Third-party add-ons such as KIRI Engine's 3DGS Render emulate splats with Geometry Nodes and Eevee. Their 2026 status is unverified. ↔️
- **Licences:**
  - Inria's 3DGS rasteriser is non-commercial, while nerfstudio **gsplat** is Apache-2.0.
  - instant-ngp is NVIDIA non-commercial.
  - FLAME is research-licensed, and "FLAME 2023 Open" is reportedly CC-BY-4.0.
  - The GaussianAvatars and VHAP licences are unverified, and NeRSemble is research-only.

  ↔️

## Numbers & reference tables

**Table 1 — Method catalogue** (Geom. = my 1–5 judgement of the usable sculpt surface, not a measurement)

| Method (year) | Representation / deformation | Input | Primitives | Train | Mesh route | Geom. | Status |
|---|---|---|---|---|---|---|---|
| NHA (2022) | mesh + offsets + neural texture | mono | ~16k–60k verts | hours | direct | 3 | 🧠 |
| IMavatar (2022) | SDF + learned blendshapes/LBS | mono | implicit | ~1–2 days | marching cubes | 4 | 🧠 |
| PointAvatar (2023) | points + learned deformation | mono | grows to ~10⁵ | hours–1 day | Poisson (poor) | 2 | ↔️ |
| INSTA (2023) | hash NeRF, nearest-triangle | mono, 512² | implicit | <~10 min | density MC (noisy) / FLAME | 2 | 🧠 |
| NeRSemble (2023) | hash ensemble + deformation | 16 views | implicit | hours | density MC | 2 | 🧠 |
| GaussianAvatars (2024) | 3DGS bound to triangles | 16 views (mono via VHAP) | ~5×10⁴–2×10⁵ | hours | refined FLAME; GS→TSDF | 3 | ↔️ |
| MonoGaussianAvatar (2024) | Gaussians + learned deformation | mono | ~10⁵ | hours | Poisson / TSDF | 2 | 🧠 |
| FlashAvatar (2024) | UV-embedded GS + offset MLP | mono | ~10⁴ | minutes | FLAME + offsets | 3 | 🧠 |
| SplattingAvatar (2024) | barycentric + normal offset | mono | ~10⁵ | <1 h | FLAME | 3 | 🧠 |
| SurFhead (2025) | 2D surfels bound to mesh | multi-view | ~10⁵ | hours | TSDF of depth (good) | 4 | 🧠 |
| MonoNPHM (2024) | neural SDF parametric head | mono | implicit | hours | marching cubes (incl. hair) | 4 | 🧠 |
| CAP4D / Avat3r / LAM / GAGAvatar | GS via diffusion or feed-forward | 1–100 images | ~10⁴–10⁵ | seconds–hours | FLAME; hallucinated detail | 2 | ↔️ |

**Table 2 — Capture targets for a sculpt-oriented avatar** (my recommendations, adult sitter)

| Item | Monocular | Multi-view | Status |
|---|---|---|---|
| Duration | 1–3 min, incl. 10–20 s held neutral | 10–30 s per sequence | 🧠 |
| Yaw / pitch | ±75–90° / ±25–30° | cameras over ≥ ±75° yaw, 2–3 heights | 🧠 |
| Resolution | ≥1080p (4K better); face ≥ 40% of frame height | ≥2 MP per view (NeRSemble 7.1 MP) | 🧠 |
| Shutter | ≥ 1/250 s (1/120 s minimum) | hardware-synced, global shutter preferred | 🧠 |
| Settings | lock exposure, white balance, focus; **stabilisation off**; no beauty or portrait modes | calibrated intrinsics | 🧠 |
| Light / subject | static diffuse light; hair tied back; no glasses; matte skin | same; cross-polarised if possible | 🧠 |

**Table 3 — 3DGS PLY layout (SH degree 3)**

| Property | Count | Stored as | Decode | Status |
|---|---|---|---|---|
| x, y, z | 3 | float32, scene units | — | 🧠 |
| nx, ny, nz | 3 | unused zeros | ignore | 🧠 |
| f_dc_0..2 | 3 | SH degree 0 | rgb = 0.5 + 0.28209479·f_dc | 🧠 |
| f_rest_0..44 | 45 | SH degrees 1–3, channel-major | view-dependence (specular gate) | 🧠 |
| opacity | 1 | logit | α = sigmoid(v) | 🧠 |
| scale_0..2 | 3 | log | s = exp(v) | 🧠 |
| rot_0..3 | 4 | quaternion (w, x, y, z), unnormalised | normalise | 🧠 |

**Table 4 — GaussianAvatars binding and regularisers** (local units are triangle-scaled)

| Quantity | Value | Meaning | Status |
|---|---|---|---|
| World position | μ′ = k·R·μ + T | T = centroid; R = frame from an edge, the normal and their cross product; k = mean of an edge length and its perpendicular | 🧠 |
| Rotation / scale | r′ = R·r ; s′ = k·s | Gaussians stretch with the triangle | 🧠 |
| ε_pos / λ_pos | ≈ 1 / ≈ 0.01 | penalise offsets beyond 1 local unit | ↔️ |
| ε_s / λ_s | ≈ 0.6 / ≈ 1 | penalise large Gaussians | ↔️ |
| FLAME face edge length | ~2–6 mm (scalp larger) | 1 local unit ≈ a few mm | 🧠 |

**Table 5 — Mesh extraction for a ~0.30–0.35 m head box**

| Route | Setting | Value | Status |
|---|---|---|---|
| Marching cubes (density or SDF) | grid | 512³ → ~0.6–0.7 mm voxels | 🧠 |
| TSDF from rendered depth | voxel / truncation / views | 0.5–1 mm / 3–5 voxels / 60–150 over the front hemisphere | 🧠 |
| Poisson from Gaussian centres | octree depth | 9 (~0.6 mm) to 10 (~0.3 mm); deeper amplifies floaters | 🧠 |
| NeRF density threshold | — | no universal value; match the silhouette to the FLAME/mask silhouette | ↔️ |

## Applying this to photo→3D face sculpting in Blender

1. **Know what you get.** An avatar yields (a) a scaled, neutral, clean-topology FLAME fit and (b) camera-registered reference renders as by-products. A dense surface (c) is worth using only from surfel or SDF methods.
2. **Capture to Table 2.** Include a held neutral (lips closed, gaze at the horizon) and an ID-1 card or A4 sheet in some frames. Phone stabilisation and distortion correction change the intrinsics per frame and silently ruin tracking.
3. **Gate on tracking before training.** Run VHAP or metrical-tracker and overlay the landmarks and silhouette at extreme yaw. Require held-out reprojection error below about 2% of the inter-ocular distance. Check scale against IPD (adult mean ~61–64 mm, SD 3–4 mm).
4. **Train a mesh-bound avatar:**
   - multi-view data: GaussianAvatars;
   - monocular data: FlashAvatar, SplattingAvatar, or GaussianAvatars via VHAP;
   - for geometry, SurFhead-style surfels.

   Avoid PointAvatar and MonoGaussianAvatar when the mesh matters.
5. **Export the neutral base.** Use the refined β (plus static offsets) with the parameters of the *most neutral tracked frame*, not ψ = 0: FLAME's zero expression is not this person's relaxed face. Export in metres. In Blender, keep the vertex order (no Merge by Distance, no Join) and store the result as a "likeness_base" shape key.
6. **Render registered references.**
   - Views: front, both profiles, ±45°, top and under-chin, at neutral.
   - Cameras: virtual cameras about 2–3 m away with a narrow field of view; add depth and normal maps where the method supports them.
   - Conversion to Blender: `c2w_blender = c2w_cv · diag(1, −1, −1, 1)`, `lens = f_px·36/W` (Sensor Fit Horizontal), and shift from the principal point via `to_blender_camera`.
   - Set each render as that camera's background. Unlike raw photos, these share the mesh's frame exactly.
7. **Project the dense surface only onto skin.** Subdivide two or three levels, then Shrinkwrap (Project, both directions, limit 3–5 mm) or Multires Reshape onto the TSDF or SDF surface, masked to a skin vertex group (forehead, cheeks, nose, chin, outer lips). Never project hair, brows, eyes, eyelids, the mouth interior or the ear backs.
8. **Sculpt the likeness against the renders *and* the original photos.** Renders inherit the avatar's errors.
9. **What goes wrong:**
   - an over-smooth FLAME nose and ears;
   - specular dents;
   - eyes bulged or sunken (Gaussians paint the iris onto FLAME's eyeball);
   - lips fused to the teeth;
   - a neutral that carries a smile or jaw bias;
   - monocular scale drift;
   - a hallucinated back of head and ears;
   - non-commercial licence contamination.
10. **Consent.** An animatable avatar is deepfake-capable. Keep video and models local, and record consent for animatable use separately from consent for a static sculpt.

## Algorithmic implications

- **Interoperate; do not reimplement.** Import tracker outputs (β, per-frame ψ and pose, K, [R|t]) as the initialisation and avatar outputs as observations. Decode PLY per Table 3. Convert to engine millimetres: FLAME metres ×1000, and undo any NeRF scene normalisation. 🧠
- **Gaussian-centre data term** (per Gaussian i):
  - normal n_i = the rotation column of the smallest scale;
  - keep if α_i ≥ 0.5 (tunable 0.3–0.7), s_min/s_max ≤ 0.3, s_max ≤ 5 mm, the region is skin, and |n_i·n_mesh| ≥ cos 45°;
  - point-to-plane residual r_i = n_i·(x − μ_i) with σ_i = √(σ₀² + s_min²), where σ₀ ≈ 0.5 mm (multi-view) or 1.0–1.5 mm (monocular);
  - weight α_i;
  - Geman–McClure robust scale c ≈ 2–3 mm.

  🧠
- **Specular gate.** Down-weight the top 10–20% of Gaussians by ‖f_rest‖/‖f_dc‖; they sit on highlights and eyes. 🧠
- **Prefer rendered median depth** (2DGS/TSDF) over raw centres, with σ ≈ 1 mm·(1 + |tan θ|) at grazing angle θ. Drop pixels with θ > 70°. 🧠
- **Coverage map.** Count bound Gaussians and their mean opacity per FLAME triangle. Where Gaussians are sparse or oversized, fall back to the β prior and symmetry (σ_sym 1.5–3 mm). 🧠
- **Priors** (consistent with `multi-view-fitting.md`):
  - β ~ N(0, 1);
  - neutral-frame ψ ~ N(0, 0.3²);
  - post-3DMM offsets Laplacian-regularised, σ ≈ 2–3 mm, capped at 5 mm;
  - IPD scale prior only when no scale object is present.

  🧠
- **Neutral-frame selection.** Score frames by ‖ψ‖ + w·|jaw| + eyelid closure − sharpness, and keep the best 5–15 across yaw. Fit β jointly over them, never from a single frame. 🧠
- **Validation outputs:**
  - leave-one-view-out reprojection error;
  - per-region Hausdorff distance between the fit and the extracted surface (alert above ~3 mm on skin);
  - a scale-mode tag;
  - `commercial_ok` provenance on every imported asset.

  🧠

## Disagreements, myths & open questions

- **Myth: "a Gaussian avatar is a 3D scan."** It is an appearance model whose geometry is unreliable off the skin. Surfel and SDF variants narrow the gap by an unmeasured amount. ↔️
- **PSNR is not likeness.** Gains of ~0.5–1.5 dB can come from the background, teeth or hair, and no standard millimetre geometry benchmark exists for animatable avatars. 🧠
- **Mesh-bound vs free deformation.** Mesh-bound designs extrapolate expressions better and map onto Blender rigs; free fields capture glasses and hair better. Rankings vary by dataset. ↔️
- **Does joint FLAME fine-tuning improve geometry or only alignment?** Gaussians can compensate for a wrong mesh, so a good render does not imply a good β. Open. 🧠
- **Diffusion-prior few-shot avatars** (CAP4D, GAF, Avat3r) look convincing, but their unseen geometry is a guess, not *this* person's measurement. ↔️
- **Open questions:**
  - the best 2025–2026 method for millimetre skin geometry from a phone;
  - whether relightable avatars give measurably better normals;
  - the FLAME 2023 Open, GaussianAvatars and VHAP licence terms;
  - native splat support in Blender in 2026.

  ↔️

## Sources

No harvest file or earlier draft existed for this topic, so no URLs are cited. Sourced VHAP and GAF facts are in `reconstruction/multi-view-fitting.md`.

**Further reading (by name, not yet linked)**
- Gafni et al., NeRFace, CVPR 2021; Grassal et al., "Neural Head Avatars from Monocular RGB Videos", CVPR 2022; Zheng et al., IMavatar, CVPR 2022
- Zheng et al., "PointAvatar", CVPR 2023; Zielonka, Bolkart, Thies, "Instant Volumetric Head Avatars" (INSTA), CVPR 2023
- Kirschstein et al., "NeRSemble: Multi-view Radiance Field Reconstruction of Human Heads", ACM TOG 2023
- Qian et al., "GaussianAvatars: Photorealistic Head Avatars with Rigged 3D Gaussians", CVPR 2024
- Chen et al., "MonoGaussianAvatar", SIGGRAPH 2024; Xiang et al., "FlashAvatar", CVPR 2024; Shao et al., "SplattingAvatar", CVPR 2024
- Xu et al., "Gaussian Head Avatar", CVPR 2024; Ma et al., "3D Gaussian Blendshapes for Head Avatar Animation", SIGGRAPH 2024
- Giebenhain et al., NPHM (CVPR 2023), MonoNPHM (CVPR 2024), NPGA (SIGGRAPH Asia 2024)
- Saito et al., "Relightable Gaussian Codec Avatars", CVPR 2024; Lee et al., "SurFhead", ICLR 2025 (verify)
- Taubner et al., "CAP4D", CVPR 2025; Kirschstein et al., "Avat3r", 2025; Chu & Harada, "GAGAvatar", NeurIPS 2024; "LAM: Large Avatar Model", SIGGRAPH 2025
- Kerbl et al., "3D Gaussian Splatting", SIGGRAPH 2023; Huang et al., "2D Gaussian Splatting", SIGGRAPH 2024; Guédon & Lepetit, "SuGaR", CVPR 2024; Yu et al., "Gaussian Opacity Fields", SIGGRAPH Asia 2024
- Müller et al., "Instant Neural Graphics Primitives", SIGGRAPH 2022; Li et al., FLAME, SIGGRAPH Asia 2017
