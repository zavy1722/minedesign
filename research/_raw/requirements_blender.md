# Engine requirements: Blender tools, sculpting & Python practice

For the team building the NumPy-only engine (`face3d`) and its Blender add-on. Drawn only from the 19 notes in `research/blender/`, with verification corrections (passes 1–2, 2026-11-20) applied. Overview: [`../blender/README.md`](../blender/README.md).

**Badges:** ✅ verified · 📄 single source · 🧠 expert knowledge, **provisional: calibrate before use** · ↔️ contested. Outside section 4, an unbadged item is 🧠.

**Sources** (`../blender/<file>.md`; tables `../data/<file>.json`): VER blender-version-status-2026 · BPY bpy-mesh-api · PKG blender-extensions-packaging · ML blender-python-ml-deps · ADD blender-face-addons · FB facebuilder-blender · CAM reference-camera-setup · LIT portrait-lighting-compare · IMP import-export-scans · SCU sculpting-likeness-workflow · SF blender-sculpt-features-5x · TOPO face-retopology · SK shapekeys-blendshapes · RIG face-rigging · BR metahuman-cc-bridges · EYE eyes-modeling-blender · HAIR hair-blender · SKIN skin-shading · TEX texture-projection-painting.

## 1. Architecture and runtime

- **A1** The engine imports only `numpy`, `math`, `json` and `tomllib`, never `bpy`, and uses relative imports, so it runs both as an extension and under plain pytest. [PKG]
- **A2** Exactly one bridge module imports `bpy`; it hands the engine float64 arrays, never IDs. [BPY]
- **A3** **Precision boundary:** `foreach_get` into contiguous float32 (coordinates) or int32 (indices); solve in float64; write back with `astype(float32)`, `foreach_set`, `mesh.update()`. Assert dtype and contiguity (a mismatch is slow or raises `TypeError`). Copy mathutils values with `np.array(x, dtype=float64)`: since 5.0 `np.asarray` gives float32 views 📄. [BPY, VER]
- **A4** **NumPy 1/2-neutral code:** no `np.float_`, `np.NaN`, `np.product` or `np.in1d`; explicit dtypes (NEP 50); `lstsq(rcond=None)`; `default_rng(seed)`. Test on CPython 3.11 + NumPy 1.26 and on 3.13 + NumPy 2.x; 5.1 and 5.2 LTS bundle Python 3.13 📄, 5.3 is unconfirmed. [VER, PKG]
- **A5** **Threading:** bpy is not thread-safe. Solve copied arrays in a worker thread or subprocess; apply results from `bpy.app.timers` (0.05–0.1 s, ≤ 10–20 ms per tick); re-fetch IDs by name after undo. A synchronous path must work under `blender -b` (no timers, modals or 3D View). [BPY, PKG]
- **A6** **No SciPy:** LM, preconditioned CG and sparse Poisson solves are written in NumPy. In Blender, closest-point and ray queries use `mathutils.bvhtree`/`kdtree` (µs per call, so not per-vertex). [SF, SK, BPY]
- **A7** **Faces in CSR form** (`offsets` + `corner_verts`, int32), which map 1:1 onto `loop_start`/`vertex_index`; `loop_total` is read-only 📄. [BPY]
- **A8** **Frames and units:** engine frame Y-up, face toward +Z; in Blender one R_x(+90°) parent empty holds head and cameras [BPY]. Blender is 1 BU = 1 m but the engine's synthetic data are in mm (observed in `face3d/synthetic.py`), so the bridge scales by 0.001.
- **A9** **Probe features, not versions.** `compat.py` runs at `register()` and returns `{blender, python_tag, numpy, online_access, platform, has_onnxruntime}`. A failing backend is disabled with a UI message. [PKG, VER]
- **A10** **Detectors run out of process:** worker (`sys.executable -I` or a venv), else in-process ONNX Runtime, else imported JSON (always available; the test harness). ORT threads `max(1, cores − 2)`; timeouts 60 s cold, 10 s per image. [ML]

## 2. Data formats and landmark schemes

- **D1** **Detector output:** `{points[N,2]` px (origin top-left, y down), `visibility, scheme, image_wh, exif_applied, mirrored, backend, backend_version, model_sha256}`. [ML]
- **D2** **MediaPipe:** 468 points ✅, 478 with refinement 📄; branch on N. Indices 468–477 are optional iris points (L/R split unconfirmed). z gets weight 0 with ≥ 2 views and ≤ 0.1·w_xy with one, because it is relative and mean-face-biased. [ADD]
- **D3** **Preprocessing:** bake EXIF orientation into the pixels (Blender ignores it 📄); un-mirror selfies; RGB, 8-bit sRGB; detect at a long side ≤ 2048 px and map back with x = (x′ + 0.5)·s − 0.5; `img.pixels` rows run bottom-up. [ML, BPY, TEX]
- **D4** **ImportRecord** per mesh: hash, declared and inferred units, axis matrix, reflection flag, s/R/t, vertex count, order checksum. [IMP]
- **D5** **Template sidecar:** named loops, poles, feature curves mapped to 2D contours, regions, symmetry map, midline, a topology hash of the face indices, and landmark → (triangle, barycentric) tables versioned per base and release (MPFB2 hm08; 2.0.16 vs 2.0.18 ↔️). [TOPO, BR, ADD]
- **D6** **Fit sidecar:** consent (who, when, scope, cloud steps); cameras, landmarks, coefficients; asset licences; `{addon_version, blender, python, numpy, seed, solver_config}`. [PKG, VER, BR]
- **D7** **Expression names:** ARKit camelCase, 52 keys 📄; adapters for raw `_L/_R`, PascalCase CSV and MediaPipe `_neutral`. [SK]
- **D8** **Meshes:** use the engine's own OBJ/PLY readers; never glTF for correspondence (it splits seams 📄). **Unit inference:** u ∈ {1e-6 … 1} minimising |log(d·u/d_ref)| on en–en (31–41 mm across populations ✅); accept within ±30 %, else flag. [IMP]

## 3. Camera model and multi-view solving

- **C1** **Camera model:** per photo, a full-perspective pinhole `[rvec, t, log f]` with one shared shape; principal point fixed at the centre (σ 1–2 % if freed); k1 = 0 (σ 0.05 only for f35 < 28 mm; prefer undistorting); scaled-orthographic only to initialise. [CAM, FB]
- **C2** **Observability:** expose a dolly-zoom coordinate (f/z constant) and report posterior σ(log f). Estimate focal only when σ(log f) < 0.10, else hold the prior and say "not observable"; flag > 0.15. Single-view z error is ≈ 11 % at 0.5 m and 15–20 % at 2 m, so lock focal beyond ~1.2 m without side views. [FB, CAM]
- **C3** **Metric scale** comes from the iris, IPD or a ruler (section 4), never from MediaPipe's canonical face. IPD shrinks by ≈ 2 mm from vergence at 0.35 m. [CAM, ADD]
- **C4** **Export:** `sensor_fit='HORIZONTAL'`, `lens = f_px·36/W`, `shift_x = (W/2 − cx)/W`, `shift_y = (cy − H/2)/W`, `clip_start` 0.01 m, resolution = photo pixels. Shift units are ↔️.
  - `face3d/geometry/camera.py` already divides by W and `tests/test_geometry.py` covers a 3000×4000 portrait (checked 2026-11-20).
  - **Still required:** a Blender round-trip test of `calc_matrix_camera`/`world_to_camera_view` within **0.01 px**, landscape and portrait, centred and shifted, via the PyPI `bpy` module. [BPY, CAM, LIT]
- **C5** **Resolution is per scene:** pad all photos to one canvas (offsetting cx, cy) or switch resolution with the active camera. [CAM, BPY]
- **C6** **Distance:** hard bounds 0.25–10 m; warn below 1 m (FB: 0.8 m). Report P = 100 mm/z (> 0.1 strong, < 0.03 near-affine). [CAM, FB]
- **C7** **Depth claims** (nose projection, ear position) need ≥ 2 views at least 30° apart in yaw. [LIT]

## 4. Bundle-adjustment priors (σ, units, badge)

Define IOD once (the notes mix pupil and outer-canthal IOD) and convert every % IOD value to it.

- **Landmarks** [ADD, FB, ML, TOPO, HAIR]: anchors (canthi, cheilion, pronasale, subnasale) σ 1.5 % IOD 🧠; lid and lip contours 2.5 % IOD, point-to-curve and sliding 🧠; face oval 4 % IOD as a silhouette term 🧠; iris centre 1 %, user pins 0.75 % 🧠. Detector floor with u = face width px/256: inner points 0.6u, iris 0.4u, brows 1.0u, contour normal 1.5u, tangent ≥ 5u 🧠. Huber δ = 2σ; drop points beyond 4σ after the first solve 🧠. Feature-curve normal σ: lid margin and vermilion 0.5–1 mm, alar rim 1–1.5, nasolabial 2–3, jaw 1.5–2.5 🧠. Brow landmarks in the skull fit 3–5 mm (1–2 mm for brow placement) 🧠.
- **Scale** [EYE, CAM, ADD, IMP]: visible iris diameter 11.8 mm, σ 0.6, bounds 10.5–13 (✅ μ, ↔️ σ; MediaPipe's 11.7 ± 0.5 is 📄). Adult IPD 63 mm, σ 3.5–4 (≈ 1 if measured) 🧠. Scale σ by source: clinical scan 0.5–1 %, phone LiDAR 2–3 %, MICA-type 3 %, non-metric regressor 5–7 %, SfM free 🧠.
- **Focal, log units** [CAM, FB]: EXIF f35 on an uncropped original σ 0.03–0.05, f_px = f35·√(W²+H²)/43.27 🧠; crop suspected 0.08 🧠; crop unknown 0.35 🧠; no EXIF: 24–200 mm hypotheses, or 0.35–0.5 around 50 mm-eq 🧠; same device and zoom tied at 0.02 🧠. Neck pose σ 10–15° 🧠.
- **Shape** [SCU, SF, TOPO, ADD]: soft symmetry ≈ 1 mm in coarse stages, 2–3 mm for per-vertex offsets, 0.5 mm on the upper midline 🧠. Laplacian 0.05–0.1 × mean edge; ARAP 5–15 % of rest edge 🧠. Per-vertex offset cap ≈ 5 mm unless several views agree 🧠. MPFB local targets N(0, 0.5²) in [−1, 1]; macros σ 0.15 in [0, 1] 🧠. FLAME β N(0, 1) over the first 50–100 components, licensed users only 🧠.
- **Expression** [ADD, BR, SK]: basis to absorb then discard, σ 0.3 🧠. ψ on neutral views half-normal 0.07 + L1 0.01–0.05; expressive views 0.5 🧠. MediaPipe score as a ψ observation σ 0.15–0.25 (0.3 uncalibrated), prior only 🧠. Neutral jaw rotation N(1.5°, 1°²) 🧠.
- **Eyes** [EYE]: globe 24.2 ± 0.9 mm (21–27) 📄; axial length fixed at 24.0 📄; anterior corneal radius 7.8 ± 0.27 mm ✅; kappa 5 ± 2° 🧠; limbus → rotation centre 10.7 ± 0.6 mm 🧠; corneal apex ahead of lateral orbital rim 16 ± 2.5 mm ↔️; upper-lid cover 1.5 ± 1.0 mm, lower-lid show 0.3 ± 0.7 mm 🧠. **Hard constraints** 🧠: lid margin within [0, 0.3] mm of the eye surface; lash roots ≥ 0.2 mm from the cornea; eyeballs rigid, never scaled.
- **Hair and cranium** [HAIR, FB]: trichion–glabella 60 ± 10 mm; hairline L/R 0 ± 3 mm 🧠. Hair-envelope offset, log-normal μ/σ: bald 1/1, short 10/5, medium 20/10, long 15/8, curly 60/30 mm 🧠. Hair-covered cranium σ 5–8 mm 🧠.

## 5. Template warping

- **W1** **Coarse-to-fine schedule** [SCU]: A similarity plus anisotropic scale (7–9 DOF) → B a 3³–4³ lattice or 10–30 low-frequency modes at ≥ 30–40 mm → C per-vertex offsets with 10–20 mm smoothness → D 2–5 mm, dense data only. Advance when landmarks are < 2–3 % IOD, silhouettes within 1–2 mm and ratios within ~2 %, or RMS gains < 1 % per iteration.
- **W2** **Scan and 3DMM targets** [IMP, BR]: (1) Umeyama proper and reflected, flagging "mirrored source" if reflected RMS < 0.5 × proper, never auto-flipping; rigid 7-landmark RMS 2–5 mm is normal, > 10 mm means wrong landmarks or axes. (2) TPS warp regularised as K + λI ✅. (3) NICP, stiffness {100, 50, 20, 10, 5, 2, 1} × mean edge, landmark weight 1 → 0.05; reject pairs beyond max(3·MAD, 5 mm) (8 mm cross-vendor), normals > 60°, or on boundaries. Region weights: interiors 0, hair-covered scalp 0.1, ears 0.3–0.5, face 1.
- **W3** **Edge flow:** barriers on quad angles outside 30–150°, aspect ratio > 4 and normal flips; ×5 stiffness on lids, lips, nostrils and ears. [TOPO, BR]
- **W4** **Subdivided deliveries:** fit on the Catmull–Clark limit surface, or features shrink by ≈ e²/(6R) = 0.1–0.4 mm. [TOPO]
- **W5** **Artist data:** sculpt mask m → data weight (1 − m) plus a pin to the artist's shape (σ 0.1–0.3 mm); feather engine masks with σ 1.5–2.5 mm; painted vertex-group weights → confidence; write 15–25 region IDs as face sets (attribute name unconfirmed). [SF, BPY]
- **W6** **Cross-topology:** embed the delivery template barycentrically in the fitting template once. Accept vendor wraps at face RMS < 0.5 mm, scalp/neck < 1.5 mm, triangle area ratio ≥ 0.2. [TOPO, BR]
- **W7** **Hair:** exclude hair, brow and beard pixels from skin terms; keep each scalp vertex ≥ 2 mm inside the hair visual hull (hinge penalty). [HAIR]

## 6. Silhouette and profile fitting

- **S1** Jaw, cheek and chin outlines are occluding-contour constraints, re-associated every iteration, never fixed vertex IDs. [CAM, ADD]
- **S2** Chamfer distance between the rendered silhouette and the segmented contour, σ 1–2 px, weighted up in profile views. [SCU]
- **S3** No silhouette terms above the trichion or on occluded ears; the hair outline is never the cranium. [FB, HAIR]
- **S4** Profile points (glabella to pogonion) are user-pinnable at σ 1 % IOD [FB]. Gate on mean contour distance ≤ 1 % of face height (unoccluded jaw and cheek); report silhouette IoU. [LIT, CAM]

## 7. Shape keys and write-back

- **K1** Refuse write-back on a vertex-count or topology-hash mismatch, or in Edit Mode. [BPY, BR]
- **K2** **Key layout:** `Basis` = template mean; `ID_fit` = engine output (`from_mix=False`); `artist` = sculpt layer; optional region keys masked by vertex groups; `slider_max` 1.5 (caricature 1.1–1.3, only when Basis is the mean). [SK, SCU]
- **K3** **Absolute positions:** with keys present, `me.vertices` writes revert from Basis 📄; Python writes to Basis do not propagate, so the bridge adds Δ to every dependent key; refits never overwrite `artist − ID_fit`. [BPY, SK, SF]
- **K4** **Mode discipline:** OBJECT mode, `foreach_set`, `mesh.update()`, then restore the mode, all in one REGISTER/UNDO operator. Writes in Sculpt Mode are overwritten. [SF]
- **K5** **Multires:** never write displacement directly. Use `multires_reshape` from a subdivided copy (needs matching topology and indices 📄), or duplicate, bake the mix and clear keys before adding Multires. [SF, BPY]
- **K6** **Expressions:** X(ψ) = X₀ + Σψₖ Dₖ + Σ_c (Π ψ) D_c with D at landmark barycentrics (51 × 51 per view); ψ ∈ [0, 1]; ridge when cond(DᵀD) > 1e4; deformation transfer by preconditioned CG after scaling by the IOD ratio ∈ [0.86, 1.14]. [SK]
- **K7** **Drivers:** simple expressions only 📄; bake masks, relative keys and drivers before export. [SK]
- **K8** **Rig pivots:** eye centre σ 0.5 mm; condyle 10–15 mm anterior and 0–10 mm inferior to tragion, σ 3–4 mm ↔️; head pivot at the mastoid midpoint, σ 6 mm; jaw translation onset ↔️. [RIG]

## 8. Texture projection

- **T1** One camera convention for solver, shader and UV Project, with shader UV u = 0.5 + k·x/(−z) + shift_x, v = 0.5 + k·(W/H)·y/(−z) + shift_y·(W/H), k = lens/sensor_width. All backends must agree within ≤ 0.5 px on a synthetic checker. [TEX]
- **T2** Project only when landmark reprojection has median ≤ 1.5 px and max ≤ 3 px. [TEX]
- **T3** **Weights and outputs:** w = visibility·cos^p θ, faded 60° → 75°, raycasting hair, glasses and eyeballs as occluders; per-texel view index, gain compensation, specular rejection. Write `albedo.exr` (half-float, linear) and `confidence.png` (Non-Color) at 4096 px (2048 phone, 8192 for ≥ 24 MP) from 5–7 views ≤ 45° apart plus a low view. [TEX, FB]
- **T4** **UV gates:** |log area ratio| ≤ 0.25 and conformal ratio ≤ 1.3 on the face (≤ 2 on ears); on failure, relax interior UVs with pinned boundaries. Per-vertex backends need edges ≤ √(4ez), e = 0.05 mm. [TEX]
- **T5** **Photometry:** treat skin shading as low-pass (low frequencies or G/B channels, specular masked); SH9 lighting (27 coefficients), Huber δ 0.05, excluding the top 2–5 % of pixels and n·v < 0.3; weak prior on light elevation N(30°, 25°) and azimuth N(0°, 60°). [SKIN, LIT]
- **T6** **Headless bakes:** `bake(type='EMIT', margin=N//256)`, extrusion ≈ 2 mm, max ray ≈ 8 mm, 1 sample. [TEX]

## 9. Licence constraints

- **L1** The add-on is GPL-3.0-or-later. extensions.blender.org requires GPL v3+ code and CC0 assets and bans remote code and externally downloaded components 📄. [PKG]
- **L2** **Licence as data:** every prior, template, table and model carries `{licence, attribution, commercial_ok}`. Unknown or non-commercial items are never defaults and block export, and fitting must work with the CC0 template alone. [PKG, ADD]
- **L3** **Template and models:** default to the MPFB2 base (CC0 📄; code GPL ✅). FLAME 2017–2023 is non-commercial 📄 and FLAME 2023 Open CC-BY-4.0 📄: load either only from a user path. InsightFace weights 📄 and CelebAMask-HQ-trained hair parsers 📄 are non-commercial. [ADD, PKG, HAIR]
- **L4** Never ship vendor meshes, index lists or priors (MetaHuman, CC3+, Daz, KeenTools); generate correspondence packs locally from the user's licensed copy ↔️. [BR, FB]
- **L5** Porting fSpy or perspective-match solver code makes the engine GPL-3.0 📄. [CAM, PKG]
- **L6** **Bundling and downloads:** never bundle NumPy. A model registry `{name, url, sha256, licence, commercial_ok}` downloads only with `online_access` on and user consent, verifies the hash, and stores files in `extension_path_user`. [PKG]
- **L7** **Biometric data:** offline by default; no telemetry; iris textures opt-in and deletable; consent names any cloud step. [PKG, EYE, BR]

## 10. Failure modes the engine must detect

- **Inputs** [ML, IMP, CAM, FB]: mirrored photo (per-view inner RMS > 3σ; asymmetry flip check); EXIF rotation (view RMS > 3σ, `exif_applied` false); zero or two faces (need exactly one at confidence ≥ 0.6, request `num_faces=2`); detectors disagreeing by > 3σ; near-field photo (z < 0.8–1 m); unsolved pose in a "front" photo (2° yaw ≈ 2.4–3.5 mm nose offset).
- **Cameras** [FB, BPY, LIT]: wrong focal (solved vs EXIF > 10–15 %, group spread > 5 %); unobservable focal (σ(log f) > 0.10); convention bug (engine vs Blender > 0.01 px, or median reprojection > 1 px on a good fit); depth claims from < 2 views ≥ 30° apart.
- **Geometry and scale** [IMP, FB, SKIN, HAIR, SK, EYE]: unit error (inference outside ±30 %, IPD outside 55–72 mm, head breadth > 10 % off 140–160 mm); mirrored mesh (reflected Umeyama RMS < 0.5 × proper); wrong axes or landmarks (rigid RMS > 10 mm); hair read as cranium (scalp outside the hair hull, g–op outside 182–200 mm); expression baked into identity (non-zero absorbed coefficients on neutral views); lid–globe gap outside [0, 0.3] mm.
- **Outputs** [BPY, BR, SF, SK, TEX, TOPO]: topology changed (count, hash or order) or Edit/Sculpt Mode at write; wrap failure (flips, area ratio < 0.2, face RMS > 0.5 mm); bad expression key (lid gap outside 0–0.5 mm, mirror RMS > 0.5 mm, spill > 1–2 %); UV |log area ratio| > 0.25; pole < 2 rings from feature loops, or quad angle outside 30–150°.

## 11. Tests and reproducibility

- **Q1** **Synthetic suite** (seeded): s ≈ 0.14 m, 3–5 cameras at 0.5–1.5 m, 50–85 mm-eq lenses, 68–100 landmarks. Noiseless: reprojection RMS < 1e-6 px, vertex RMS < 1e-6·s. At σ = 1 px noise expect RMS ≈ σ√(1 − p/n); fail above 1.2σ. [PKG]
- **Q2** **Tolerances:** round trip 1e-6·s; convergence at relative cost < 1e-10 or step < 1e-8·s; goldens rtol 1e-5, never bit-exact; no finite differences on float32 data; detector goldens 0.05 px across machines; OBJ round trip < 2 µm. [VER, ML, IMP]
- **Q3** **Headless CI:** `blender -b --factory-startup --python-exit-code 1` (without it a failing script exits 0 📄) on 4.5 LTS, 5.2 LTS and 5.3, isolated via `BLENDER_USER_RESOURCES`; `blender_version_min` = oldest line tested. [PKG, VER]
- **Q4** **Accuracy:** NoW-style 7-landmark rigid alignment, then per-vertex scan error ✅; target a face median < 0.5 mm; never claim better than the reference modality (≈ 0.2–1 mm 📄). Budgets: core zip ≤ 5 MB (≤ 25 MB with template), `register()` < 100 ms. [IMP, PKG]

## 12. Open questions

1. Lens-shift units under each sensor fit (the C4 test). [BPY, LIT]
2. Python and NumPy shipped in 5.1–5.3 (NumPy 2.3.x is tracker evidence only). [VER]
3. Own vs shared site-packages for wheels; whether the store accepts compiled wheels; the upload cap (unofficially 200 MB). [PKG, ML]
4. 5.x sculpt attribute names, multires write paths, EXIF/HEIC loading; whether Multires detail follows base edits. [SF, SCU, BPY, TEX]
5. ARKit raw strings and L/R convention; MediaPipe category order, iris index split and model licences. [SK, ADD, ML]
6. Calibrating every 🧠 prior and gate on consented portraits with known cameras; no mm likeness tolerance exists. [CAM, SCU, LIT]
7. Per-subject jaw θmax and translation onset; exact hm08 counts and MPFB2 version; FaceBuilder camera naming and EULA. [RIG, ADD, FB]
