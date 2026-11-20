# Engine requirements: Blender tools, sculpting & Python practice

Digest for the team building the NumPy-only fitting engine (`face3d`) and its Blender add-on. It covers camera solving, landmark bundle adjustment, template warping, silhouettes, shape keys and texture projection. It draws only on the 19 notes in `research/blender/`, with every verification-log correction (passes 1 and 2, 2026-11-20) applied. Area overview: [`../blender/README.md`](../blender/README.md).

**Badges:** ✅ verified · 📄 single source · 🧠 expert knowledge, **provisional, so calibrate before relying on it** · ↔️ contested. About two thirds of the area's claims are 🧠, so most numeric defaults here are provisional.

**Source keys** (notes are at `../blender/<note>.md`, tables at `../data/<note>.json`): VER version-status-2026 · BPY bpy-mesh-api · PKG extensions-packaging · ML python-ml-deps · ADD face-addons · FB facebuilder · CAM reference-camera-setup · LIT portrait-lighting-compare · IMP import-export-scans · SCU sculpting-likeness-workflow · SF sculpt-features-5x · TOPO face-retopology · SK shapekeys-blendshapes · RIG face-rigging · BR metahuman-cc-bridges · EYE eyes-modeling · HAIR hair · SKIN skin-shading · TEX texture-projection-painting.

## 1. Architecture and runtime

- **A1** The engine imports only `numpy`, `math`, `json` and `tomllib`. It never imports `bpy` and uses relative imports, so the same code runs as an extension and under plain-CPython pytest. 🧠 [PKG]
- **A2** Exactly one bridge module imports `bpy`. It hands the engine float64 arrays, never IDs. 🧠 [BPY]
- **A3** **Precision boundary:**
  - read with `foreach_get` into contiguous float32 (coordinates) or int32 (indices) buffers;
  - convert to float64 once and solve in float64;
  - write back with `astype(float32)`, `foreach_set`, `mesh.update()`;
  - assert dtype and contiguity, since a mismatch is slow 🧠 or raises `TypeError` (verification);
  - copy mathutils values with `np.array(x, dtype=np.float64)`, because since 5.0 `np.asarray` returns float32 views 📄. [BPY, VER]
- **A4** **NumPy 1/2-neutral code:** no `np.float_`, `np.NaN`, `np.product` or `np.in1d`; explicit dtypes (NEP 50); `lstsq(rcond=None)`; `default_rng(seed)`. CI runs CPython 3.11 + NumPy 1.26 and 3.13 + NumPy 2.x, because 5.1 and 5.2 LTS bundle Python 3.13 📄 and 5.3 is unconfirmed. [VER, PKG]
- **A5** **Threading:** bpy is not thread-safe 🧠.
  - Solve on copied arrays in a worker thread or a `sys.executable` subprocess.
  - Apply results from `bpy.app.timers` (0.05–0.1 s interval, ≤10–20 ms of work per tick).
  - Re-fetch IDs by name after undo.
  - A synchronous path must also work under `blender -b`, which has no timers, modal operators or 3D View. [BPY, PKG]
- **A6** **No SciPy.** LM, Jacobi-preconditioned CG and sparse Poisson solves are written in NumPy. Inside Blender, closest-point and ray queries use `mathutils.bvhtree`/`kdtree` (a few µs per call, so not for per-vertex work). 🧠 [SF, SK, BPY]
- **A7** **Faces in CSR form** (`offsets` + `corner_verts`, int32), which map 1:1 onto `loop_start`/`vertex_index` 🧠. `loop_total` is read-only 📄. [BPY]
- **A8** **Frames and units:**
  - The engine frame is Y-up with the face toward +Z. In Blender, one R_x(+90°) parent empty holds the head and all cameras 🧠. [BPY]
  - Blender uses 1 BU = 1 m. The engine's synthetic data are in mm (`face3d/synthetic.py`), so the bridge scales by 0.001.
- **A9** **Probe features, never version numbers.** `compat.py` runs at `register()` and reports `{blender, python_tag, numpy, online_access, platform, has_onnxruntime}`. A backend that fails is disabled with a UI message, not a traceback. 🧠 [PKG, VER]
- **A10** **Detectors run out of process:**
  - tiers: a worker (`sys.executable -I` or a separate venv), then in-process ONNX Runtime, then imported JSON (always available; also the test harness);
  - ORT threads: `max(1, physical_cores − 2)`, inter-op 1;
  - timeouts: 60 s cold, 10 s per image.

  Blender ignores `PYTHONPATH` and user site-packages by default ✅, so worker dependencies go in a private folder. 🧠 [ML]

## 2. Data formats and landmark schemes

- **D1** **Detector contract:** `detect(rgb_uint8, meta) → {points[N,2]` px (origin top-left, y down), `visibility, scheme, image_wh, exif_applied, mirrored, backend, backend_version, model_sha256}`. 🧠 [ML]
- **D2** **MediaPipe:**
  - 468 points ✅, or 478 with iris refinement 📄; branch on N;
  - indices 468–477 are optional iris points, with the L/R split unconfirmed 🧠;
  - z gets weight 0 with ≥ 2 views and ≤ 0.1·w_xy with one view, because it is relative and biased toward the mean face 🧠. [ADD]
- **D3** **Preprocessing:** 🧠 unless marked [ML, BPY, TEX]
  - bake EXIF orientation into the pixels (Blender ignores it 📄);
  - un-mirror selfies;
  - convert to RGB, 8-bit sRGB;
  - detect at a long side ≤ 2048 px and map back with x = (x′ + 0.5)·s − 0.5;
  - remember that `img.pixels` rows run bottom-up.
- **D4** **ImportRecord sidecar** per mesh: file hash, declared and inferred units, axis matrix, reflection flag, s/R/t, vertex count and order checksum. 🧠 [IMP]
- **D5** **Template sidecar:**
  - named ordered loops, poles and feature curves mapped to 2D contours;
  - regions, symmetry map and midline;
  - a topology hash of the face-index arrays;
  - landmark → (triangle, barycentric) tables, versioned per base and release (MPFB2 hm08; 2.0.16 vs 2.0.18 is ↔️). 🧠 [TOPO, BR, ADD]
- **D6** **Fit sidecar:**
  - consent (who, when, scope, any cloud step);
  - cameras, landmarks and coefficients;
  - each asset's licence;
  - `{addon_version, blender, python, numpy, seed, solver_config}`. 🧠 [PKG, VER, BR]
- **D7** **Expression names:** canonical ARKit camelCase, 52 keys 📄, with adapters for raw `_L/_R`, PascalCase CSV and MediaPipe `_neutral` 🧠. [SK]
- **D8** **Mesh I/O:** use the engine's own NumPy OBJ/PLY readers, and never glTF for anything with correspondence (it splits seams 📄).
  - **Unit inference:** choose u ∈ {1e-6, 1e-3, 1e-2, 1e-1, 1} minimising |log(d·u/d_ref)| on en–en, which spans 31–41 mm across populations ✅.
  - Accept within ±30 % 🧠, otherwise flag. [IMP]

## 3. Camera model and multi-view solving

- **C1** **Camera model:** per photo, a full-perspective pinhole `[rvec, t, log f]`, with one shared head shape.
  - Principal point fixed at the centre (σ 1–2 % of the fit dimension if freed).
  - k1 = 0; enable it (σ 0.05) only for f35 < 28 mm, and prefer undistorting first.
  - Scaled-orthographic only for initialisation. 🧠 [CAM, FB]
- **C2** **Observability:**
  - Expose the dolly-zoom coordinate (f/z constant) and report posterior σ(log f).
  - Estimate focal only when σ(log f) < 0.10; otherwise hold the prior and report "not observable". Flag σ(log f) > 0.15.
  - Single-view z error is ≈ 11 % at 0.5 m and 15–20 % at 2 m, so lock focal beyond ~1.2 m unless side views constrain depth. 🧠 [FB, CAM]
- **C3** **Metric scale** comes from the iris, IPD or a ruler (table P), never MediaPipe's canonical face. Correct IPD for vergence below 1 m (≈ 2 mm less at 0.35 m, derived 🧠). [CAM, ADD]
- **C4** **Blender export:** `sensor_fit='HORIZONTAL'`, `lens = f_px·36/W`, `shift_x = (W/2 − cx)/W`, `shift_y = (cy − H/2)/W`, `clip_start` 0.01 m, resolution = photo pixels. Shift units are ↔️.
  - `face3d/geometry/camera.py` already divides by W, and `tests/test_geometry.py` covers a 3000×4000 portrait (checked 2026-11-20).
  - **Still required:** a Blender round-trip test of `calc_matrix_camera`/`world_to_camera_view` (u = x·W, v = (1 − y)·H) within **0.01 px**, landscape and portrait, centred and shifted, using the PyPI `bpy` module. [BPY, CAM, LIT]
- **C5** **Render resolution is per scene.** Pad all photos to one canvas (offsetting cx, cy) or switch resolution with the active camera. 🧠 [CAM, BPY]
- **C6** **Camera distance:** hard bounds 0.25–10 m; warn below 1 m (FB: 0.8 m). Report P = 100 mm/z (> 0.1 strong, < 0.03 near-affine). 🧠 [CAM, FB]
- **C7** **Depth claims** (nose projection, ear position) require ≥ 2 views at least 30° apart in yaw. 🧠 [LIT]

## 4. Landmark bundle adjustment: priors (table P)

| Parameter | μ | σ / bounds | Units | Badge | Src |
|---|---|---|---|---|---|
| Anchors (canthi, cheilion, pronasale, subnasale) | 0 | 1.5 | % IOD | 🧠 | ADD |
| Lid/lip contours, point-to-curve, sliding | 0 | 2.5 | % IOD | 🧠 | ADD |
| Face oval, silhouette, re-associated each iteration | 0 | 4 | % IOD | 🧠 | ADD |
| Iris centre / user pin | 0 | 1 / 0.75 | % IOD | 🧠 | ADD, FB |
| Detector floor, u = face width px/256 | — | inner 0.6u; iris 0.4u; brows 1.0u; contour normal 1.5u, tangent ≥ 5u | px | 🧠 | ML |
| Robust loss | Huber δ = 2σ | drop beyond 4σ after the first solve | — | 🧠 | ADD |
| Feature-curve normal | 0 | lid margin, vermilion 0.5–1; alar rim 1–1.5; nasolabial 2–3; jaw 1.5–2.5 | mm | 🧠 | TOPO |
| Brow landmarks in the skull fit | 0 | 3–5 (1–2 for brow placement) | mm | 🧠 | HAIR |
| Visible iris diameter | 11.8 | 0.6 [10.5, 13]; MediaPipe figure 11.7 ± 0.5 📄 | mm | ✅ μ, ↔️ σ | EYE, CAM |
| Adult IPD | 63 | 3.5–4; ≈ 1 if measured | mm | 🧠 | CAM, ADD |
| log f, EXIF f35, uncropped | f35·√(W²+H²)/43.27 | 0.03–0.05 | log | 🧠 | CAM, FB |
| log f, crop suspected / crop unknown | EXIF | 0.08 / 0.35 | log | 🧠 | FB, CAM |
| log f, no EXIF | 24–200 mm hypotheses or 50 mm-eq | none or 0.35–0.5 | log | 🧠 | CAM, FB |
| Focal tie, same device and zoom | shared | 0.02 | log | 🧠 | CAM |
| Neck pose | 0 | 10–15 | deg | 🧠 | FB |
| Symmetry (soft) | 0 | ≈ 1 coarse → 2–3 per-vertex; 0.5 upper midline | mm | 🧠 | SCU, SF |
| Smoothness | — | Laplacian 0.05–0.1 × mean edge; ARAP 5–15 % of rest edge | — | 🧠 | SF, TOPO |
| Per-vertex offset cap | — | ≈ 5 unless several views agree | mm | 🧠 | ADD |
| MPFB local targets / macros | 0 / user | N(0, 0.5²) in [−1, 1] / 0.15 in [0, 1] | slider | 🧠 | ADD |
| FLAME β (licensed users) | 0 | 1, first 50–100 | SD | 🧠 | ADD |
| Expression to absorb, then discard | 0 | 0.3 | 0–1 | 🧠 | ADD, BR |
| ψ, neutral / expressive views | 0 | half-normal 0.07 + L1 0.01–0.05 / 0.5 | 0–1 | 🧠 | SK |
| MediaPipe score as ψ observation | score | 0.15–0.25 (0.3 uncalibrated); prior only | 0–1 | 🧠 | SK |
| Jaw rotation, neutral | 1.5 | 1 | deg | 🧠 | SK |
| Globe transverse / axial (fixed) | 24.2 / 24.0 | 0.9 [21, 27] / — | mm | 📄 | EYE |
| Anterior corneal radius | 7.8 | 0.27 | mm | ✅ | EYE |
| Kappa / limbus → rotation centre | 5 / 10.7 | 2 / 0.6 | deg / mm | 🧠 | EYE |
| Apex ahead of lateral orbital rim | 16 | 2.5 [10, 24] | mm | ↔️ | EYE |
| Upper-lid cover / lower-lid show | 1.5 / 0.3 | 1.0 / 0.7 | mm | 🧠 | EYE |
| Trichion–glabella; hairline L/R | 60; 0 | 10; 3 | mm | 🧠 | HAIR |
| Hair envelope (log-normal) | bald 1, short 10, medium 20, long 15, curly 60 | 1, 5, 10, 8, 30 | mm | 🧠 | HAIR |
| Hair-covered cranium | prior | 5–8 | mm | 🧠 | FB |
| Scale by source | — | clinical 0.5–1 %; LiDAR 2–3 %; MICA-type 3 %; non-metric 5–7 %; SfM free | log | 🧠 | IMP |

**Hard constraints** 🧠 [EYE]:
- the posterior lid margin stays within [0, 0.3] mm of the eye surface, cornea included;
- lash roots stay ≥ 0.2 mm from the cornea;
- eyeballs move rigidly and are never scaled.

**Define IOD once** (the notes mix pupil and outer-canthal IOD) and convert every % IOD value to that definition.

## 5. Template warping

- **W1** **Coarse-to-fine schedule:** 🧠 [SCU]
  - A: similarity plus anisotropic scale (7–9 DOF);
  - B: a 3³–4³ lattice, or 10–30 low-frequency modes at ≥ 30–40 mm;
  - C: per-vertex offsets with 10–20 mm smoothness;
  - D: 2–5 mm, only with dense scan or depth data.

  Advance a stage when landmarks are < 2–3 % IOD, silhouettes within 1–2 mm and ratios within ~2 %, or when RMS improves by < 1 % per iteration.
- **W2** **Scan and 3DMM targets:** 🧠 unless marked [IMP, BR]
  1. Umeyama twice, proper and reflected. Flag "mirrored source" if reflected RMS < 0.5 × proper; never auto-flip.
  2. Rigid 7-landmark RMS of 2–5 mm is normal; above 10 mm, the landmarks or axes are wrong.
  3. TPS landmark warp, regularised as K + λI ✅.
  4. NICP with stiffness {100, 50, 20, 10, 5, 2, 1} × mean edge length, landmark weight 1 → 0.05, 3–10 iterations per stage. Reject pairs beyond max(3·MAD, 5 mm) (8 mm for cross-vendor wraps), with normals > 60°, or on scan boundaries.
  5. Region weights: interiors 0, hair-covered scalp 0.1, ears 0.3–0.5, face 1.
- **W3** **Edge-flow barriers:** quad angles outside 30–150°, aspect ratio > 4, normal flips. Lids, lips, nostrils and ears get ×5 stiffness. 🧠 [TOPO, BR]
- **W4** **Subdivided deliveries:** fit on the Catmull–Clark limit surface, or lips and nose tip shrink by ≈ e²/(6R) = 0.1–0.4 mm. 🧠 [TOPO]
- **W5** **Artist data as constraints:** 🧠 [SF, BPY]
  - sculpt mask m → data weight (1 − m) plus a pin term m·‖x − x_artist‖²/σ², σ 0.1–0.3 mm;
  - feather engine-written masks with Gaussian σ 1.5–2.5 mm;
  - painted vertex-group weights → data confidence;
  - write 15–25 anatomical region IDs as face sets (attribute name unconfirmed).
- **W6** **Cross-topology:** embed the delivery template barycentrically in the fitting template once. Accept vendor wraps at face RMS < 0.5 mm, scalp and neck < 1.5 mm, triangle area ratio ≥ 0.2. 🧠 [TOPO, BR]
- **W7** **Hair:** exclude hair, brow and beard pixels from the skin terms, and keep every scalp vertex ≥ 2 mm inside the hair visual hull (hinge penalty). 🧠 [HAIR]

## 6. Silhouette and profile fitting

- **S1** Jaw, cheek and chin outlines are occluding-contour constraints, re-associated to the nearest contour point every iteration, never fixed vertex IDs. 🧠 [CAM, ADD]
- **S2** Chamfer distance between the rendered silhouette and the segmented photo contour, σ 1–2 px, weighted up in profile views. 🧠 [SCU]
- **S3** No silhouette terms above the trichion or on occluded ears; never treat the hair outline as the cranium. 🧠 [FB, HAIR]
- **S4** Profile points (glabella, nasion, pronasale, subnasale, lips, pogonion) can be user-pinned at σ 1 % IOD. 🧠 [FB]
- **S5** Gate on mean contour distance ≤ 1 % of face height on the unoccluded jaw and cheek, and report silhouette IoU. 🧠 [LIT, CAM]

## 7. Shape keys and write-back

- **K1** Refuse write-back on a vertex-count or topology-hash mismatch, or while the object is in Edit Mode. 🧠 [BPY, BR]
- **K2** **Key layout:** 🧠 [SK, SCU]
  - `Basis` = template mean;
  - `ID_fit`/`likeness` = engine output, written with `from_mix=False`;
  - `artist` = sculpt layer;
  - optional region keys masked by vertex groups;
  - `ID_fit.slider_max` = 1.5 (caricature 1.1–1.3; valid only when Basis is the mean face).
- **K3** **Absolute positions:**
  - with keys present, writes to `me.vertices` revert from Basis 📄;
  - Python writes to Basis do not propagate, so the bridge adds Δ to every dependent key 🧠;
  - refits never overwrite `artist − likeness`. [BPY, SK, SF]
- **K4** **Mode discipline:** OBJECT mode, `foreach_set`, `mesh.update()`, restore the mode, all in one REGISTER/UNDO operator. Writes made in Sculpt Mode are overwritten. 🧠 [SF]
- **K5** **Multires:** never write displacement directly. Push dense results through `multires_reshape` from a subdivided copy (it needs matching topology and indices 📄), or duplicate, bake the mix and clear keys before adding Multires. [SF, BPY]
- **K6** **Expressions:** 🧠 [SK]
  - forward model X(ψ) = X₀ + Σψₖ Dₖ + Σ_c (Π ψ) D_c, with D precomputed at landmark barycentrics (51 × 51 per view);
  - ψ ∈ [0, 1], with ridge regularisation when cond(DᵀD) > 1e4;
  - deformation transfer by preconditioned CG, after a first pass that scales by s = IOD_subject/IOD_template ∈ [0.86, 1.14].
- **K7** **Drivers:** simple expressions only (`min`, `max`, `abs`, products) 📄. Bake masks, relative keys and drivers before export. [SK]
- **K8** **Rig pivots:** eye centre σ 0.5 mm; condyle 10–15 mm anterior and 0–10 mm inferior to tragion, σ 3–4 mm ↔️; head pivot at the mastoid-tip midpoint, σ 6 mm. Jaw translation onset is contested ↔️. 🧠 [RIG]

## 8. Texture projection

- **T1** One camera convention for the solver, the shader and the UV Project modifier. Shader mapping: u = 0.5 + k·x/(−z) + shift_x, v = 0.5 + k·(W/H)·y/(−z) + shift_y·(W/H), with k = lens/sensor_width. Every backend must agree within ≤ 0.5 px on a synthetic checker. 🧠 [TEX]
- **T2** Project only when landmark reprojection has median ≤ 1.5 px and max ≤ 3 px. 🧠 [TEX]
- **T3** **View weights:** w = visibility · cos^p θ, faded from 60° to 75°. Visibility raycasts include hair, glasses and eyeballs. Keep a per-texel view index, gain compensation and specular rejection. 🧠 [TEX, FB]
- **T4** **Outputs:** `albedo.exr` (half-float, linear) and `confidence.png` (Non-Color). Maps of 4096 px (2048 for phones, 8192 for ≥ 24 MP); 5–7 views spaced ≤ 45° plus one low view. 🧠 [TEX]
- **T5** **UV gates after fitting:** |log area ratio| ≤ 0.25 and conformal ratio ≤ 1.3 on the face (≤ 2 on ears); on failure, relax interior UVs with pinned boundaries. Per-vertex backends need edges ≤ √(4ez), with e = 0.05 mm. 🧠 [TEX]
- **T6** **Photometry:** 🧠 [SKIN, LIT]
  - treat skin shading as low-pass: low frequencies or G/B channels, specular masked;
  - SH9 lighting (27 coefficients) with Huber δ 0.05, excluding the top 2–5 % of pixels and n·v < 0.3;
  - weak light-from-above prior: elevation N(30°, 25°), azimuth N(0°, 60°).
- **T7** **Headless bakes:** `bake(type='EMIT', margin=N//256)`, cage extrusion ≈ 2 mm, max ray ≈ 8 mm, 1 sample. 🧠 [TEX]

## 9. Licence constraints

- **L1** The add-on is GPL-3.0-or-later. extensions.blender.org requires GPL v3-or-later code and CC0 bundled assets, and bans remote code and externally downloaded components 📄. [PKG]
- **L2** **Licence as data:** every prior, template, table and model carries `{licence, attribution, commercial_ok}`. Unknown or non-commercial items can never be defaults and block export. Fitting must succeed with the CC0 template alone. 🧠 [PKG, ADD]
- **L3** **Default template and restricted models:**
  - the default is the MPFB2 base (CC0 📄; code GPL ✅);
  - FLAME 2017–2023 is non-commercial 📄, while FLAME 2023 Open is CC-BY-4.0 📄; load either only from a user path;
  - InsightFace weights 📄 and CelebAMask-HQ-trained hair parsers 📄 are non-commercial. [ADD, PKG, HAIR]
- **L4** Never ship vendor meshes, index lists or priors (MetaHuman, CC3+, Daz, KeenTools). Generate correspondence packs locally from the user's licensed copy ↔️. [BR, FB]
- **L5** Porting fSpy or perspective-match solver code makes the engine GPL-3.0 📄. [CAM, PKG]
- **L6** **Bundling and downloads:**
  - never bundle NumPy;
  - keep a model registry `{name, url, sha256, licence, commercial_ok}`;
  - download only with `bpy.app.online_access` on and user consent;
  - verify the hash and store files in `extension_path_user`. 🧠 [PKG]
- **L7** **Biometric data:** offline by default, no telemetry; iris textures opt-in and deletable; consent names any cloud step. 🧠 [PKG, EYE, BR]

## 10. Failure modes the engine must detect

| Failure | Detector and threshold | Badge | Src |
|---|---|---|---|
| Mirrored photo | per-view inner RMS > 3σ; asymmetry flip check | 🧠 | ML, IMP |
| Mirrored mesh source | reflected Umeyama RMS < 0.5 × proper | 🧠 | IMP |
| EXIF rotation ignored | view RMS > 3σ; `exif_applied` false | 🧠 | ML |
| Wrong focal (crop, zoom) | solved vs EXIF > 10–15 %; group spread > 5 % | 🧠 | FB |
| Focal not observable | σ(log f) > 0.10 | 🧠 | FB |
| Camera convention bug | engine vs Blender > 0.01 px; median reprojection > 1 px on a good fit | 🧠 | BPY |
| Unit error | inference outside ±30 %; IPD outside 55–72 mm; head breadth > 10 % off 140–160 mm | 🧠 | IMP, FB, SKIN |
| Wrong axes or landmarks | rigid 7-landmark RMS > 10 mm | 🧠 | IMP |
| Zero or two faces | exactly one at confidence ≥ 0.6 (`num_faces=2`) | 🧠 | ML |
| Detector disagreement | backends differ by > 3σ | 🧠 | ML |
| Expression baked into identity | non-zero absorbed coefficients on neutral views | 🧠 | ADD, SK |
| Hair read as cranium | scalp outside the hair hull; g–op outside 182–200 mm | 🧠 | HAIR, FB |
| Near-field photo | z < 0.8–1 m | 🧠 | CAM, FB |
| Unsolved pose in a "front" photo | yaw or pitch residual (2° ≈ 2.4–3.5 mm nose offset) | 🧠 | CAM |
| Topology changed | count, hash or order checksum mismatch | 🧠 | BPY, BR |
| Write in the wrong mode | Edit or Sculpt Mode active | 🧠 | BPY, SF |
| Wrap failure | flipped triangles; area ratio < 0.2; face RMS > 0.5 mm | 🧠 | BR |
| Lid–globe misfit | gap outside [0, 0.3] mm | 🧠 | EYE |
| Bad expression key | lid gap outside 0–0.5 mm; mirror RMS > 0.5 mm; spill > 1–2 % | 🧠 | SK |
| UV distortion | \|log area ratio\| > 0.25 | 🧠 | TEX |
| Pole or quad violation | pole < 2 rings from feature loops; angle outside 30–150° | 🧠 | TOPO |
| Unsupported depth claim | fewer than 2 views ≥ 30° apart | 🧠 | LIT |

## 11. Tests and reproducibility

- **Q1** **Synthetic suite** (seeded): s ≈ 0.14 m, 3–5 cameras at 0.5–1.5 m, 50–85 mm-equivalent lenses, 68–100 landmarks.
  - Noiseless: reprojection RMS < 1e-6 px and vertex RMS < 1e-6·s.
  - With σ = 1 px noise: expect RMS ≈ σ√(1 − p/n); fail above 1.2σ. 🧠 [PKG]
- **Q2** **Tolerances:** 🧠 [VER, ML, IMP]
  - round trip 1e-6·s;
  - convergence: relative cost < 1e-10 or step < 1e-8·s;
  - goldens rtol 1e-5, never bit-exact;
  - no finite differences on float32 data;
  - detector goldens 0.05 px across machines;
  - OBJ round trip < 2 µm.
- **Q3** **Headless CI:** `blender -b --factory-startup --python-exit-code 1` on 4.5 LTS, 5.2 LTS and 5.3, with an isolated `BLENDER_USER_RESOURCES`. Without the exit-code flag a raised script exits 0 📄. Set `blender_version_min` to the oldest line CI tests. [PKG, VER]
- **Q4** **Accuracy:** NoW-style 7-landmark rigid alignment, then per-vertex scan error ✅. Aim for a median below 0.5 mm on the face 🧠, and never claim better than the reference modality (≈ 0.2–1 mm) 📄. [IMP]
- **Q5** **Budgets:** core zip ≤ 5 MB (≤ 25 MB with a template); `register()` < 100 ms. 🧠 [PKG]

## 12. Open questions

1. Lens-shift units under each sensor fit (C4 test). [BPY, LIT]
2. Python and NumPy actually shipped in 5.1–5.3; NumPy 2.3.x is development-tracker evidence only. [VER]
3. Where wheels install (own vs shared site-packages), whether the store accepts compiled wheels, and the upload limit (a tracker reports 200 MB, unofficial). [PKG, ML]
4. 5.x names `.sculpt_mask`/`.sculpt_face_set`; any Python write path to multires displacement; whether Multires detail follows base edits. [SF, SCU]
5. EXIF and HEIC handling in the 5.x image loader. [BPY, TEX]
6. ARKit raw strings and L/R convention; MediaPipe category order and iris index split; MediaPipe model-card and ONNX-conversion licences. [SK, ADD, ML]
7. Calibration of every 🧠 prior and gate on consented portraits with known cameras; no mm perceptual tolerance for likeness exists. [CAM, SCU, LIT]
8. Jaw kinematics: should θmax and translation onset be fitted per subject? [RIG]
9. Exact hm08 vertex counts; MPFB2 2.0.16 vs 2.0.18. [ADD]
10. FaceBuilder camera naming (for importing existing solves) and EULA terms on exported meshes. [FB]
