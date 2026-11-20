# Engine requirements: Blender tools, sculpting & Python practice

Digest for the team building the NumPy-only fitting engine (`face3d`) and its Blender add-on: multi-view camera solving, landmark bundle adjustment with anatomical priors, template warping, silhouette and profile fitting, shape keys and texture projection. It draws only on the 19 notes in `research/blender/`, with their verification-log corrections applied (2026-11-20). Area overview: [`../blender/README.md`](../blender/README.md).

**Badges:** ✅ verified · 📄 single source · 🧠 expert knowledge, **provisional: calibrate before relying on it** · ↔️ contested. About two thirds of the area's claims are 🧠, so nearly every numeric default below is provisional.

**Source keys** (all at `../blender/<note>.md`; tables at `../data/<note>.json`): VER blender-version-status-2026 · BPY bpy-mesh-api · PKG blender-extensions-packaging · ML blender-python-ml-deps · ADD blender-face-addons · FB facebuilder-blender · CAM reference-camera-setup · LIT portrait-lighting-compare · IMP import-export-scans · SCU sculpting-likeness-workflow · SF blender-sculpt-features-5x · TOPO face-retopology · SK shapekeys-blendshapes · RIG face-rigging · BR metahuman-cc-bridges · EYE eyes-modeling-blender · HAIR hair-blender · SKIN skin-shading · TEX texture-projection-painting.

## 1. Architecture and runtime

- **A1** The engine imports only `numpy`, `math`, `json` and `tomllib`, never `bpy`, and uses relative imports only, so it runs both inside Blender and under plain-CPython pytest. 🧠 [PKG]
- **A2** Exactly one bridge module imports `bpy`. It exchanges float64 arrays with the engine and never passes IDs. 🧠 [BPY]
- **A3** **Precision boundary:**
  - read with `foreach_get` into contiguous float32 (coordinates) or int32 (indices) buffers;
  - convert to float64 once and solve in float64;
  - write back with `astype(float32)`, `foreach_set`, `mesh.update()`;
  - assert dtype and contiguity, because a mismatch is slow 🧠 or raises `TypeError` for some dtypes (verification);
  - copy mathutils values with `np.array(x, dtype=np.float64)`, because since 5.0 `np.asarray` returns float32 views 📄. [BPY, VER]
- **A4** **NumPy 1/2-neutral code:** no `np.float_`, `np.NaN`, `np.Inf`, `np.product`, `np.in1d` or `np.row_stack`; explicit dtypes (NEP 50); `lstsq(rcond=None)`; `default_rng(seed)`. Test on CPython 3.11 + NumPy 1.26 and 3.13 + NumPy 2.x. 5.1 and 5.2 LTS bundle Python 3.13 📄; 5.3 is unconfirmed. [VER, PKG]
- **A5** **Threading:** bpy is not thread-safe 🧠.
  - Solve on copied arrays in a worker thread or a `sys.executable` subprocess.
  - Apply results from `bpy.app.timers` (interval 0.05–0.1 s, ≤10–20 ms of work per tick).
  - Re-fetch IDs by name after undo.
  - A synchronous path must work under `blender -b`, which has no timers, modal operators or 3D View. [BPY, PKG]
- **A6** **No SciPy in Blender.** Write LM, sparse CG (Jacobi-preconditioned) and Poisson solves in NumPy. Inside Blender, use `mathutils.bvhtree`/`kdtree` for closest-point and ray queries (a few µs per call, so not per-vertex work). 🧠 [SF, SK, RIG, BPY]
- **A7** **Mesh representation:** CSR faces (`offsets` + `corner_verts`, int32) that map 1:1 onto `loop_start`/`vertex_index`. 🧠 [BPY]
- **A8** **Frames and units:**
  - The engine frame is Y-up with the face looking toward +Z; one R_x(+90°) parent empty holds the head and all cameras in Blender, so mesh data round-trips exactly. 🧠 [BPY]
  - Blender uses 1 BU = 1 m. The engine's synthetic data are in mm (observed in `face3d/synthetic.py`), so the bridge scales by 0.001.
- **A9** **Feature probes, never version branches.** `compat.py` runs at `register()` and returns `{blender, python_tag, numpy, online_access, platform, has_onnxruntime}`. A backend that fails the probe is disabled with a UI message. 🧠 [PKG, VER]
- **A10** **Detectors run out of process.** Tiers: a worker (`sys.executable -I` or a separate venv, the default), then in-process ONNX Runtime, then imported JSON (always available, and also the test harness). ORT settings: `intra_op = max(1, physical_cores − 2)`, `inter_op = 1`. Timeouts: 60 s on the cold first run, 10 s per image after. 🧠 [ML]

## 2. Data formats and landmark schemes

- **D1** **Detector contract:** `detect(rgb_uint8, meta) → {points[N,2]` (px, origin top-left, y down), `visibility[N], scheme, image_wh, exif_applied, mirrored, backend, backend_version, model_sha256}`. 🧠 [ML]
- **D2** **MediaPipe:** 468 points ✅, or 478 with iris refinement 📄. Branch on N; indices 468–477 are optional iris observations (their L/R split is unconfirmed 🧠). z gets weight 0 with ≥2 views and ≤0.1·w_xy with one view, because it is relative and biased toward the mean face 🧠. [ADD, ML]
- **D3** **Image preprocessing:**
  - bake EXIF orientation into the pixels (Blender ignores it 📄);
  - un-mirror selfies and record `mirrored`;
  - convert BGR to RGB, 8-bit sRGB;
  - detect at a long side ≤2048 px and map back with x = (x′ + 0.5)·s − 0.5;
  - remember that `img.pixels` rows run bottom to top. 🧠 [ML, BPY, TEX]
- **D4** **ImportRecord sidecar** per mesh: format, file hash, declared and inferred units, 3×3 axis matrix, reflection flag, s/R/t, vertex count, vertex-order checksum. 🧠 [IMP]
- **D5** **Template sidecar:**
  - named ordered loops (closed/open), poles, `feature_curves` mapped to 2D contours, regions, `symmetry_map`, midline;
  - a topology hash of the face-index arrays;
  - correspondence tables landmark → (triangle, barycentric), versioned per base and release (MPFB2 hm08; 2.0.16 vs 2.0.18 is ↔️). 🧠 [TOPO, BR, ADD]
- **D6** **Fit sidecar:**
  - consent (who, when, scope, any cloud step);
  - cameras (intrinsics and extrinsics), landmarks and coefficients;
  - each asset's licence;
  - `{addon_version, blender, python, numpy, seed, solver_config}`. 🧠 [PKG, VER, BR]
- **D7** **Expression names:** canonical ARKit camelCase, 52 keys 📄, with adapters for raw `_L/_R`, PascalCase Live Link CSV and MediaPipe `_neutral` 🧠. [SK]
- **D8** **Mesh files:**
  - Use the engine's own NumPy OBJ/PLY readers, which guarantee order; never use glTF for anything with correspondence (it splits seams 📄).
  - **Unit inference:** choose u ∈ {1e-6, 1e-3, 1e-2, 1e-1, 1} minimising |log(d·u/d_ref)| on en–en, which spans 31–41 mm across populations ✅. Accept within ±30 % 🧠, otherwise flag. [IMP]

## 3. Camera model and multi-view solving

- **C1** **Camera model:** per photo, a full-perspective pinhole `[rvec, t, log f]` with the principal point fixed at the image centre (σ 1–2 % of the fit dimension if freed) and one shared head shape. Distortion k1 = 0 by default; enable it (σ 0.05) only for f35 < 28 mm, and prefer undistorting first. Use scaled-orthographic only for initialisation. 🧠 [CAM, FB]
- **C2** **Focal priors:** see table P. Tie focal across photos from the same body and zoom.
- **C3** **Observability:** expose the dolly-zoom coordinate (f/z constant) and report posterior σ(log f).
  - Estimate focal only when σ(log f) < 0.10; otherwise hold the prior and report "not observable". Flag σ(log f) > 0.15.
  - Single-view z error is ≈11 % at 0.5 m and 15–20 % at 2 m, so lock focal beyond ~1.2 m unless side views constrain depth. 🧠 [FB, CAM]
- **C4** **Metric scale** comes from the iris, IPD or a ruler (table P), never from MediaPipe's canonical face. Correct IPD for vergence below 1 m (≈2 mm less at 0.35 m, derived 🧠). [CAM, ADD]
- **C5** **Blender export contract:** `sensor_fit='HORIZONTAL'`, `lens = f_px·36/W`, `shift_x = (W/2 − cx)/W`, `shift_y = (cy − H/2)/W`, `clip_start` 0.01 m, resolution = photo pixels. Shift units are ↔️.
  - Status: `face3d/geometry/camera.py` already divides by W and `tests/test_geometry.py` covers a 3000×4000 portrait case (both checked 2026-11-20).
  - **Still required:** a Blender round-trip test of `calc_matrix_camera` / `world_to_camera_view` (u = x·W, v = (1 − y)·H) within **0.01 px**, for landscape and portrait, centred and shifted, run under the PyPI `bpy` module. [BPY, CAM, LIT]
- **C6** **Resolution is per scene.** Either pad all photos to a common canvas, offsetting cx and cy, or switch resolution with the active camera. 🧠 [CAM, BPY]
- **C7** **Distance:** hard bounds 0.25–10 m; warn below 1 m (FB: 0.8 m). Report perspective strength P = 100 mm/z (> 0.1 strong, < 0.03 near-affine). 🧠 [CAM, FB]
- **C8** **Depth claims** (nose projection, ear position) need ≥2 views at least 30° apart in yaw. 🧠 [LIT]

## 4. Landmark bundle adjustment: priors (table P)

| Parameter | μ | σ / bounds | Units | Badge | Src |
|---|---|---|---|---|---|
| Anchor landmarks (canthi, cheilion, pronasale, subnasale) | 0 | 1.5 | % IOD | 🧠 | ADD |
| Lid and lip contours, point-to-curve, sliding | 0 | 2.5 | % IOD | 🧠 | ADD |
| Face oval, silhouette, re-associated every iteration | 0 | 4 | % IOD | 🧠 | ADD |
| Iris centre / user pin | 0 | 1 / 0.75 | % IOD | 🧠 | ADD, FB |
| Detector floor, u = face width px / 256 | — | inner 0.6u; iris 0.4u; brows 1.0u; contour normal 1.5u, tangent ≥ 5u | px | 🧠 | ML |
| Robust loss | Huber δ = 2σ | drop points beyond 4σ after the first solve | — | 🧠 | ADD |
| Feature-curve normal σ | 0 | lid margin and vermilion 0.5–1; alar rim 1–1.5; nasolabial 2–3; jaw 1.5–2.5 | mm | 🧠 | TOPO |
| Brow landmarks in the skull fit | 0 | 3–5 (1–2 for brow placement only) | mm | 🧠 | HAIR |
| Visible iris diameter (HVID) | 11.8 | 0.6 [10.5, 13.0]; MediaPipe figure 11.7 ± 0.5 📄 | mm | ✅ μ, ↔️ σ | EYE, CAM |
| Adult IPD | 63 | 3.5–4 population; ≈1 if measured | mm | 🧠 | CAM, ADD |
| log f, EXIF f35, uncropped | f35·√(W²+H²)/43.27 | 0.03–0.05 | log | 🧠 | CAM, FB |
| log f, crop/zoom suspected / crop unknown | EXIF | 0.08 / 0.35 | log | 🧠 | FB, CAM |
| log f, no EXIF | 24–200 mm f35 hypotheses or 50 mm-eq | none or 0.35–0.5 | log | 🧠 | CAM, FB |
| Focal tie, same device and zoom | shared | 0.02 | log | 🧠 | CAM |
| Neck pose (yaw, pitch, roll) | 0 | 10–15 | deg | 🧠 | FB |
| Symmetry (soft, from the mirror map) | 0 | ≈1 coarse → 2–3 per-vertex; 0.5 upper midline | mm | 🧠 | SCU, SF |
| Smoothness | — | Laplacian 0.05–0.1 × mean edge; ARAP 5–15 % of rest edge; loop 2nd difference 0.2–0.5 mm | — | 🧠 | SF, TOPO |
| Residual per-vertex offset cap | — | ≈5 mm unless several views agree | mm | 🧠 | ADD |
| MPFB local targets / macros | 0 / user value | N(0, 0.5²), box [−1, 1] / 0.15, box [0, 1] | slider | 🧠 | ADD |
| FLAME β (licensed users only) | 0 | 1, first 50–100 components | SD | 🧠 | ADD |
| Expression to absorb, then discard | 0 | 0.3 | 0–1 | 🧠 | ADD, BR |
| ψ on neutral / expressive views | 0 | half-normal 0.07 + L1 0.01–0.05 / 0.5 | 0–1 | 🧠 | SK |
| MediaPipe blendshape score as ψ observation | score | 0.15–0.25 (0.3 uncalibrated); prior only | 0–1 | 🧠 | SK |
| Jaw rotation, neutral | 1.5 | 1 | deg | 🧠 | SK |
| Globe transverse / axial (axial fixed) | 24.2 / 24.0 | 0.9 [21, 27] / fixed | mm | 📄 | EYE |
| Anterior corneal radius | 7.8 | 0.27 | mm | ✅ | EYE |
| Kappa (temporal) / limbus → rotation centre | 5 / 10.7 | 2 / 0.6 | deg / mm | 🧠 | EYE |
| Corneal apex ahead of lateral orbital rim | 16 | 2.5 [10, 24] | mm | ↔️ | EYE |
| Eye L–R shape difference | 0 | 0.3 | mm | 🧠 | EYE |
| Upper-lid cover / lower-lid show | 1.5 / 0.3 | 1.0 / 0.7 | mm | 🧠 | EYE |
| Eyeball radius (vendor rigs) | 12.0 | 0.5 | mm | 🧠 | BR |
| Trichion–glabella; hairline L/R deviation | 60; 0 | 10; 3 | mm | 🧠 | HAIR |
| Hair envelope offset (log-normal) | bald 1, short 10, medium 20, long 15, curly 60 | 1, 5, 10, 8, 30 | mm | 🧠 | HAIR |
| Hair-covered cranium vertices | prior | 5–8 | mm | 🧠 | FB |
| Scale prior by source | — | clinical 0.5–1 %; phone LiDAR 2–3 %; MICA-type 3 %; non-metric 5–7 %; SfM free | log | 🧠 | IMP |
| FaceBuilder head as observation | point-to-plane | 1–1.5 (3–4 on cranium and ears) | mm | 🧠 | FB |

**Hard constraints** 🧠 [EYE]:
- posterior lid margin to eye surface (cornea included) within [0, 0.3] mm, enforced by projection;
- lash roots ≥ 0.2 mm from the cornea;
- eyeballs move rigidly and are never scaled.

**Define IOD once** (the notes mix pupil and outer-canthal IOD) and convert every % IOD value to it.

## 5. Template warping

- **W1** **Coarse-to-fine schedule:** 🧠 [SCU]
  - A: similarity plus anisotropic scale (7–9 DOF);
  - B: an FFD lattice of 3³–4³, or 10–30 Laplacian/PCA modes with length scale ≥ 30–40 mm;
  - C: per-vertex offsets with 10–20 mm smoothness;
  - D: 2–5 mm, only with dense scan or depth data.

  Advance a stage when landmarks are below 2–3 % IOD, silhouettes within 1–2 mm and primary ratios within ~2 % in all views, or when RMS improves by less than 1 % per iteration.
- **W2** **Scan or 3DMM targets:** 🧠 unless marked [IMP, BR]
  1. Umeyama twice, with det(R) = +1 and with reflection allowed. Flag "mirrored source" if the reflected RMS is below 0.5× the proper RMS; never auto-flip.
  2. Rigid 7-landmark RMS of 2–5 mm is normal; above 10 mm, treat the landmarks or axes as wrong.
  3. TPS landmark warp, regularised as K + λI ✅.
  4. NICP with stiffness {100, 50, 20, 10, 5, 2, 1} × mean edge length and landmark weight 1 → 0.05, 3–10 iterations per stage. Reject pairs beyond max(3·MAD, 5 mm) (8 mm for cross-vendor wraps), with normals > 60°, or on scan boundaries.
  5. Region weights: eyeball, mouth and nostril interiors 0; hair-covered scalp 0.1; ears 0.3–0.5; face 1.
- **W3** **Edge-flow preservation:** barriers on quad angles outside 30–150°, aspect ratio > 4 and normal flips; ×5 stiffness on lids, lips, nostrils and ears. 🧠 [TOPO, BR]
- **W4** If the delivery mesh is subdivided, fit residuals on the Catmull–Clark limit surface S·V; otherwise lips and nose tip shrink by ≈ e²/(6R) = 0.1–0.4 mm. 🧠 [TOPO]
- **W5** **Artist data as constraints:** 🧠 [SF, BPY]
  - sculpt mask m → data weight (1 − m) plus a pin term m·‖x − x_artist‖²/σ_pin², σ_pin 0.1–0.3 mm;
  - feather engine-written masks with Gaussian σ 1.5–2.5 mm;
  - painted vertex-group weights w → data confidence, and Laplacian σ scaled by 1/w²;
  - write 15–25 anatomical region IDs as face sets (`.sculpt_face_set`; the name is unconfirmed).
- **W6** **Cross-topology:** embed the delivery template barycentrically in the fitting template once. Accept vendor wraps at face RMS < 0.5 mm, scalp and neck < 1.5 mm, triangle area ratio ≥ 0.2. 🧠 [TOPO, BR]
- **W7** **Hair:** exclude hair, brow and beard pixels from the skin terms, and keep every scalp vertex ≥ 2 mm inside the hair visual hull (hinge penalty). 🧠 [HAIR]

## 6. Silhouette and profile fitting

- **S1** Jaw, cheek and chin outline landmarks are occluding-contour constraints (nearest contour point, re-associated every iteration), never fixed vertex IDs. 🧠 [CAM, ADD]
- **S2** Chamfer distance between the rendered silhouette and the segmented photo contour, σ 1–2 px, weighted up in profile views. 🧠 [SCU]
- **S3** Disable silhouette terms above the trichion and on occluded ears; never use the hair outline as the cranium. 🧠 [FB, HAIR]
- **S4** Profile points (glabella, nasion, pronasale, subnasale, lips, pogonion) can be user-pinned at σ 1 % IOD. 🧠 [FB]
- **S5** Gate on mean contour distance ≤ 1 % of face height on the unoccluded jaw and cheek, and report silhouette IoU. 🧠 [LIT, CAM]

## 7. Shape keys and Blender write-back

- **K1** Refuse write-back when `len(V) ≠ len(me.vertices)`, the topology hash differs, or the object is in Edit Mode. 🧠 [BPY, BR]
- **K2** **Key layout:** 🧠 [SK, SCU, BPY]
  - `Basis` = template mean;
  - `ID_fit`/`likeness` = engine output, written with `from_mix=False`;
  - `artist` = sculpt layer;
  - optional `fit_primary`, `fit_secondary`, `asym` and region keys masked by vertex groups (0–1.2);
  - `ID_fit.slider_max` = 1.5 (caricature 1.1–1.3; valid only when Basis is a mean face).
- **K3** **Absolute positions:**
  - With keys present, writes to `me.vertices` revert from Basis 📄.
  - Python writes to Basis do not propagate, so the bridge adds Δ to every dependent key 🧠.
  - Respect `lock_shape`.
  - A refit never overwrites `artist − likeness`. [BPY, SK, SF]
- **K4** **Mode discipline:** switch to OBJECT mode, `foreach_set`, `mesh.update()`, restore the mode, all inside one REGISTER/UNDO operator. Writes made in Sculpt Mode are overwritten. 🧠 [SF]
- **K5** **Multires:** never write displacement directly. Push dense results through `multires_reshape` from a temporary subdivided copy (Reshape needs matching topology and indices 📄), or use the hand-off: duplicate, bake the mix, clear keys, then add Multires. [SF, SCU, BPY]
- **K6** **Expression model:** 🧠 [SK]
  - forward model X(ψ) = X₀ + Σψₖ Dₖ + Σ_c (Π ψ) D_c, with D precomputed at landmark barycentrics (51 × 51 per view, `tongueOut` dropped);
  - ψ ∈ [0, 1];
  - ridge regularisation when cond(DᵀD) > 1e4;
  - deformation transfer by Jacobi-preconditioned CG, after a first pass that scales by s = IOD_subject/IOD_template ∈ [0.86, 1.14].
- **K7** **Drivers:** simple expressions only (`min`, `max`, `abs`, products) 📄. Bake masks, relative keys and drivers before export. [SK]
- **K8** **Rig profile per template:** 🧠 / ↔️ [RIG]
  - bones as barycentric points plus a normal offset;
  - a thin-plate-spline pivot warp from ≥ 30 correspondences;
  - pivots: eye centre σ 0.5 mm; condyle 10–15 mm anterior and 0–10 mm inferior to tragion, 15–20 mm deep, σ 3–4 mm ↔️; head pivot at the mastoid-tip midpoint, σ 6 mm.

## 8. Texture projection

- **T1** Use one camera convention for the solver, the shader and the UV Project modifier. The shader maps u = 0.5 + k·x/(−z) + shift_x and v = 0.5 + k·(W/H)·y/(−z) + shift_y·(W/H), with k = lens/sensor_width. A synthetic checker must agree within ≤ 0.5 px across all backends. 🧠 [TEX]
- **T2** Project only after the landmark gate passes: median ≤ 1.5 px, max ≤ 3 px. 🧠 [TEX]
- **T3** **View weights:** 🧠 [TEX, FB]
  - w = visibility · cos^p θ, faded from 60° to 75°;
  - raycast visibility includes hair, glasses and eyeballs;
  - keep a per-texel view-index map, gain compensation and specular rejection.
- **T4** **Outputs:** `albedo.exr` (half-float, linear) and `confidence.png` (Non-Color). Maps of 4096 px (2048 for phone photos, 8192 for ≥ 24 MP); 5–7 views spaced ≤ 45° plus one low view. 🧠 [TEX]
- **T5** **UV gates after fitting:** |log area ratio| ≤ 0.25 (σ ≈ 0.12); conformal ratio ≤ 1.3 on the face, ≤ 2 on ears. On failure, relax interior UVs with pinned island boundaries. Per-vertex backends require edges L ≤ √(4ez) with e = 0.05 mm. 🧠 [TEX]
- **T6** **Photometric and lighting terms:** 🧠 [SKIN, LIT]
  - treat skin shading as low-pass: use low frequencies or the G/B channels, mask specular pixels, prefer cross-polarised input;
  - fit SH9 lighting (27 coefficients) with Huber δ 0.05;
  - exclude the brightest 2–5 % of pixels and n·v < 0.3;
  - light-from-above prior: elevation N(30°, 25°), azimuth N(0°, 60°).
- **T7** Headless bake: `bake(type='EMIT', margin=N//256, cage_extrusion≈2 mm, max_ray_distance≈8 mm, use_clear=True)` with 1 sample. 🧠 [TEX]

## 9. Licence constraints

- **L1** Ship the add-on as GPL-3.0-or-later. extensions.blender.org requires GPL v3-or-later code and CC0 bundled assets, and forbids remote code, externally downloaded components and runtime pip 📄. [PKG, ML]
- **L2** **Licence as data:** every prior, template, table and model carries `{licence, attribution, commercial_ok}`. Unknown or `commercial_ok=false` items can never be defaults and block export. Fitting must succeed with the CC0 template alone. 🧠 [PKG, ADD]
- **L3** **Default template:** MPFB2 base, CC0 📄 (code GPL ✅).
  - FLAME 2017–2023 are non-commercial 📄; FLAME 2023 Open is CC-BY-4.0 📄. Load either only from a user-supplied path.
  - BFM is research-only 🧠; InsightFace weights are reportedly non-commercial 📄. [ADD, PKG]
- **L4** Never ship vendor meshes, index lists or priors (MetaHuman, CC3+, Daz G8/G9, KeenTools). Generate correspondence packs locally from the user's licensed copy ↔️. [BR, FB]
- **L5** Porting fSpy or perspective-match solver code makes the engine GPL-3.0 📄. [CAM, PKG]
- **L6** **Bundling and downloads:**
  - never bundle NumPy;
  - keep a model registry `{name, url, sha256, bytes, licence, commercial_ok, needs_network}`;
  - download only with `bpy.app.online_access` on and user confirmation;
  - verify the hash before loading and store files in `extension_path_user`. 🧠 [PKG]
- **L7** **Biometric data:** offline by default, no telemetry; iris textures opt-in and deletable; consent names any cloud step. 🧠 [PKG, EYE, BR]

## 10. Failure modes the engine must detect

| Failure | Detector and threshold | Badge | Src |
|---|---|---|---|
| Mirrored photo or selfie | per-view inner-point RMS > 3σ; L/R asymmetry flip check | 🧠 | ML, IMP |
| Mirrored mesh source | reflected Umeyama RMS < 0.5 × proper; flag, never flip | 🧠 | IMP |
| EXIF rotation ignored | view RMS > 3σ; `exif_applied` false | 🧠 | ML |
| Wrong focal (crop, digital zoom) | solved vs EXIF > 10–15 %; group spread > 5 % | 🧠 | FB |
| Focal not observable | posterior σ(log f) > 0.10 | 🧠 | FB |
| Camera convention bug | engine vs Blender > 0.01 px; median reprojection > 1 px on a good fit | 🧠 | BPY |
| Unit error | inference outside ±30 %; IPD outside 55–72 mm; head breadth > 10 % off 140–160 mm | ✅ / 🧠 | IMP, FB, SKIN |
| Wrong axes or landmarks | rigid 7-landmark RMS > 10 mm | 🧠 | IMP |
| Zero or two faces | require exactly one at confidence ≥ 0.6 (request `num_faces=2`) | 🧠 | ML |
| Detector disagreement | two backends differ by > 3σ | 🧠 | ML |
| Expression baked into identity | non-zero absorbed expression coefficients; neutral ψ prior violated | 🧠 | ADD, SK |
| Hair read as cranium | scalp outside hair hull; g–op outside 182–200 mm | 🧠 | HAIR, FB |
| Near-field photo | z < 0.8–1 m | 🧠 | CAM, FB |
| Pose left in "front" photo | yaw or pitch residual (2° ≈ 2.4–3.5 mm nose offset) | 🧠 | CAM |
| Topology changed | vertex count, hash or order checksum mismatch | 🧠 | BPY, BR |
| Wrong mode at write | Edit or Sculpt Mode active | 🧠 | BPY, SF |
| Wrap failure | flipped triangles; area ratio < 0.2; face RMS > 0.5 mm | 🧠 | BR |
| Lid–globe misfit | gap outside [0, 0.3] mm (rig QA ≤ 0.5 mm) | 🧠 | EYE, RIG |
| Bad expression key | lid gap outside 0–0.5 mm or crossing; L/R mirror RMS > 0.5 mm; spill > 1–2 % | 🧠 | SK |
| UV distortion | \|log area ratio\| > 0.25 | 🧠 | TEX |
| Pole or quad violation | pole < 2 rings from feature loops; quad angle outside 30–150°; aspect > 4 | 🧠 | TOPO |
| Unsupported depth claim | fewer than 2 views ≥ 30° apart | 🧠 | LIT |

## 11. Tests and reproducibility

- **Q1** **Synthetic suite** (seeded): s ≈ 0.14 m; 3–5 cameras at 0.5–1.5 m; 50–85 mm-equivalent lenses; 68–100 landmarks.
  - Noiseless runs need reprojection RMS < 1e-6 px and vertex RMS < 1e-6·s.
  - With σ = 1 px noise, expect RMS ≈ σ√(1 − p/n) and fail above 1.2σ. 🧠 [PKG]
- **Q2** **Tolerances:** 🧠 [VER, ML, IMP]
  - round trip 1e-6·s;
  - convergence: relative cost change < 1e-10 or step < 1e-8·s;
  - golden files rtol 1e-5, never bit-exact;
  - no finite differences on float32-round-tripped data;
  - detector goldens 0.05 px across machines;
  - OBJ export round trip < 2 µm.
- **Q3** **Headless CI:** `blender -b --factory-startup --python-exit-code 1` on 4.5 LTS, 5.2 LTS and 5.3, plus the daily alpha during betas, with an isolated `BLENDER_USER_RESOURCES`. Declare `blender_version_min` = the oldest CI-tested line (4.5.0 unless 4.2 joins CI). 🧠 [PKG, VER]
- **Q4** **Accuracy protocol:** NoW-style rigid alignment on 7 landmarks, then per-vertex scan error ✅. Target a median below 0.5 mm on the face 🧠, and never claim better than the reference modality (≈0.2–1 mm) 📄. [IMP]
- **Q5** **Budgets:** core zip ≤ 5 MB (≤ 25 MB with the template); `register()` < 100 ms with lazy imports. 🧠 [PKG]

## 12. Open questions

1. Lens-shift units under each sensor fit: confirm with the Blender round-trip test (C5). [BPY, LIT]
2. Python and NumPy actually shipped in 5.1–5.3; NumPy 2.3.x is development-tracker evidence only. [VER]
3. Where extension wheels install (own vs shared site-packages), how collisions behave, and whether the store accepts compiled wheels or consented model downloads. [PKG, ML]
4. `.sculpt_mask` / `.sculpt_face_set` names in 5.x; any Python write path for multires displacement; `foreach` access to vertex-group weights. [SF, BPY]
5. Whether Multires detail follows base-coordinate edits made from Python. [SCU, RIG]
6. EXIF and HEIC handling in the 5.x image loader. [BPY, TEX]
7. ARKit raw strings and L/R convention; MediaPipe category order and `_neutral`; MediaPipe iris index split; licences of the MediaPipe model card and the ONNX conversion. [SK, ADD, ML]
8. Calibrating every 🧠 prior (focal tiers, landmark σ, symmetry, NICP schedule, gates) on consented portraits with known cameras; no mm perceptual likeness tolerance exists. [CAM, SCU, LIT]
9. Jaw kinematics: does translation start immediately (verification ↔️)? Should θmax and w0 be fitted per subject? [RIG]
10. Exact hm08 vertex counts; MPFB2 2.0.16 vs 2.0.18. [ADD]
11. FaceBuilder camera object naming (for "import existing solve") and EULA terms on exported meshes. [FB]
