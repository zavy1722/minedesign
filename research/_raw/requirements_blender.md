# Engine requirements: Blender tools, sculpting & Python practice

For the team building the NumPy-only engine (`face3d`) and its Blender add-on; drawn only from the 21 notes in `research/blender/`, verification corrections (passes 1–2, 2026-11-20) applied. Overview: [`../blender/README.md`](../blender/README.md).

**Badges:** ✅ verified · 📄 single source · 🧠 expert knowledge, **provisional: calibrate before use** · ↔️ contested. Outside section 4, an unbadged item is 🧠.

**Sources** (`../blender/<file>.md`; tables `../data/<file>.json`): VER blender-version-status-2026 · BPY bpy-mesh-api · PKG blender-extensions-packaging · ML blender-python-ml-deps · ADD blender-face-addons · FB facebuilder-blender · CAM reference-camera-setup · LIT portrait-lighting-compare · IMP import-export-scans · SCU sculpting-likeness-workflow · SF blender-sculpt-features-5x · TOPO face-retopology · SK shapekeys-blendshapes · RIG face-rigging · BR metahuman-cc-bridges · EYE eyes-modeling-blender · HAIR hair-blender · SKIN skin-shading · TEX texture-projection-painting · TK open-template-head-kit · GW guided-workflow-accessibility.

## 1. Architecture and runtime

- **A1** The engine imports only `numpy`, `math`, `json` and `tomllib`, never `bpy`, and uses relative imports, so it also runs under plain pytest. [PKG]
- **A2** One bridge module imports `bpy` and passes float64 arrays, never IDs. [BPY]
- **A3** **Precision boundary:** `foreach_get` into contiguous float32 (coordinates) or int32 (indices); solve in float64; write back with `astype(float32)`, `foreach_set`, `mesh.update()`. Assert dtype and contiguity. Copy mathutils values with `np.array(x, dtype=float64)`: since 5.0 `np.asarray` gives float32 views 📄. [BPY, VER]
- **A4** **NumPy 1/2-neutral code:** no `np.float_` or `np.in1d`; explicit dtypes (NEP 50); `default_rng(seed)`. Test on CPython 3.11 + NumPy 1.26 and on 3.13 + NumPy 2.x; 5.1 and 5.2 LTS bundle Python 3.13 📄, 5.3 is unconfirmed. [VER, PKG]
- **A5** **Threading:** bpy is not thread-safe. Solve copied arrays in a worker thread or subprocess; apply results from `bpy.app.timers` (0.05–0.1 s, ≤ 10–20 ms per tick); re-fetch IDs by name after undo. A synchronous path must work under `blender -b`. [BPY, PKG]
- **A6** **No SciPy:** LM, preconditioned CG and sparse Poisson solves in NumPy; in Blender, closest-point and ray queries via `mathutils.bvhtree`/`kdtree` (µs per call). [SF, SK, BPY]
- **A7** **Faces in CSR form** (`offsets` + `corner_verts`, int32), mapping 1:1 to `loop_start`/`vertex_index`; `loop_total` is read-only 📄. [BPY]
- **A8** **Frames and units:** engine frame Y-up, face toward +Z; in Blender one R_x(+90°) parent empty holds head and cameras [BPY]. Blender is 1 BU = 1 m but the engine's synthetic data are in mm (observed in `face3d/synthetic.py`), so the bridge scales by 0.001.
- **A9** **Probe features, not versions:** `compat.py` at `register()` (< 100 ms) returns `{blender, python_tag, numpy, online_access, platform, has_onnxruntime}`; failing backends are disabled with a message. [PKG, VER]
- **A10** **Detectors run out of process:** worker (`sys.executable -I` or a venv), else in-process ONNX Runtime, else imported JSON (always available). ORT threads `max(1, cores − 2)`; timeouts 60 s cold, 10 s per image. [ML]

## 2. Data formats and landmark schemes

- **D1** **Detector output:** `{points[N,2]` px (origin top-left, y down), `visibility, scheme, image_wh, exif_applied, mirrored, backend, backend_version, model_sha256}`. [ML]
- **D2** **MediaPipe:** 468 points ✅, 478 with refinement 📄; branch on N. Indices 468–477 are optional iris points (L/R split unconfirmed). z (relative, mean-face-biased) gets weight 0 with ≥ 2 views, ≤ 0.1·w_xy with one. [ADD]
- **D3** **Preprocessing:** bake EXIF orientation into the pixels (Blender ignores it 📄); un-mirror selfies; RGB, 8-bit sRGB; detect at a long side ≤ 2048 px and map back with x = (x′ + 0.5)·s − 0.5; `img.pixels` rows run bottom-up. [ML, BPY, TEX]
- **D4** **ImportRecord** per mesh: hash, units (declared, inferred), axis matrix, reflection flag, s/R/t, vertex-order checksum. [IMP]
- **D5** **Template sidecar** (JSON + `.npz`): `topology_sha256` (refuse mismatches), units m, axes, licence, sub-mesh ranges, named loops and poles, mirror map (bijection, M(M(i)) = i), regions (soft masks), landmark (tri, bary) per convention (MediaPipe 478, iBUG-68, WFLW-98, FLAME 51 + 17, Farkas ≈40), anthropometric points as a vertex or candidates + rule, contour candidate rings, and bases `{U, σ, licence, commercial_ok, bundle_ok}`. Version per base release (MPFB2 version ↔️). [TK, TOPO, BR]
- **D6** **Fit sidecar:** consent (who, when, scope, cloud steps); cameras, landmarks, coefficients; asset licences; `{addon_version, blender, python, numpy, seed, solver_config}`. [PKG, VER, BR]
- **D7** **Expression names:** ARKit camelCase, 52 keys 📄; adapters for raw `_L/_R`, PascalCase CSV and MediaPipe `_neutral`. [SK]
- **D8** **Meshes:** use the engine's own OBJ/PLY readers; never glTF for correspondence (it splits seams 📄). **Unit inference:** u ∈ {1e-6 … 1} minimising |log(d·u/d_ref)| on en–en (31–41 mm across populations ✅); accept within ±30 %, else flag. [IMP]
- **D9** **Pins** live in a PropertyGroup (undo-safe): `{view, xy_px, target (tri, bary) or curve, class, σ_normal_mm, σ_tangent_mm, source, expertise, zoom, blind}`. `face3d/solve/bundle.py` takes them as weights w = (σ_px/σ_i,px)². [GW]

## 3. Camera model and multi-view solving

- **C1** **Camera model:** per photo a perspective pinhole `[rvec, t, log f]`, one shared shape; principal point at the centre (σ 1–2 % if freed); k1 = 0 (σ 0.05 only for f35 < 28 mm); scaled-orthographic only to initialise. [CAM, FB]
- **C2** **Observability:** expose a dolly-zoom coordinate (f/z constant) and report posterior σ(log f). Estimate focal only when σ(log f) < 0.10, else hold the prior and say "not observable"; flag > 0.15. Lock focal beyond ~1.2 m without side views (single-view z error 15–20 % at 2 m). [FB, CAM]
- **C3** **Metric scale** comes from the iris, IPD or a ruler (section 4), never MediaPipe's canonical face; vergence shrinks IPD ≈ 2 mm at 0.35 m. [CAM, ADD]
- **C4** **Export:** `sensor_fit='HORIZONTAL'`, `lens = f_px·36/W`, `shift_x = (W/2 − cx)/W`, `shift_y = (cy − H/2)/W`, `clip_start` 0.01 m, resolution = photo pixels; shift units are ↔️. `face3d/geometry/camera.py` already divides by W, tested on a 3000×4000 portrait (checked 2026-11-20). **Still required:** a Blender round-trip test (`calc_matrix_camera`/`world_to_camera_view`) within **0.01 px**, landscape and portrait, centred and shifted, via PyPI `bpy`. [BPY, CAM, LIT]
- **C5** **Resolution is per scene:** pad photos to one canvas (offset cx, cy) or switch it per camera. [CAM, BPY]
- **C6** **Distance:** hard bounds 0.25–10 m; flag solved cameras below 0.8–1 m; coach capture below 1.2 m (block < 0.7 m). [CAM, FB, GW]
- **C7** **Depth claims** (nose projection, ear position) need ≥ 2 views ≥ 30° apart in yaw. [LIT]

## 4. Bundle-adjustment priors

Store σ in mm: the notes mix outer-canthal (≈88 mm) and pupil (≈63 mm) IOD, 1.4× apart.

- **Landmarks** [ADD, FB, ML, TOPO, HAIR]: anchors (canthi, cheilion, pronasale, subnasale) σ 1.5 % IOD; lid and lip contours 2.5 % IOD, point-to-curve and sliding; face oval 4 % IOD as a silhouette term; iris centre 1 %. Detector floor with u = face width px/256: inner points 0.6u, iris 0.4u, brows 1.0u, contour normal 1.5u, tangent ≥ 5u. Huber δ = 2σ; drop points beyond 4σ after the first solve. Feature-curve normal σ: lid margin and vermilion 0.5–1 mm, alar rim 1–1.5, nasolabial 2–3, jaw 1.5–2.5. Brow landmarks in the skull fit 3–5 mm (1–2 mm for brow placement). All 🧠.
- **User pins** [GW]: σ = √(σ_class² + σ_motor²); class σ crisp corners 0.8 mm expert / 1.2 novice, contours 1.0, alar base 1.8, nose tip 2.0 ↔️, ears 2.5, palpation points 4–5 ↔️, hair-defined 5 (never skull) 🧠. Default to novice; the 0.75 % IOD user σ fits experts on crisp corners only ↔️.
- **Region offsets after the basis fit** [TK]: lids 1–1.5 mm, lips 1.5–2.5, nose 2–3, brow 2–3, cheek 2.5–4, jaw 2–4, ears 3–5, scalp 3–6, neck 5–10 🧠.
- **Scale** [EYE, CAM, ADD, IMP]: visible iris diameter 11.8 mm, σ 0.6, bounds 10.5–13 (✅ μ, ↔️ σ; MediaPipe's 11.7 ± 0.5 is 📄). Adult IPD 63 mm, σ 3.5–4 (≈ 1 if measured) 🧠. Scale σ by source: clinical scan 0.5–1 %, phone LiDAR 2–3 %, MICA-type 3 %, non-metric regressor 5–7 %, SfM free 🧠.
- **Focal, log units** [CAM, FB]: EXIF f35 on an uncropped original σ 0.03–0.05, f_px = f35·√(W²+H²)/43.27 🧠; crop suspected 0.08; crop unknown 0.35; no EXIF: 24–200 mm hypotheses, or 0.35–0.5 around 50 mm-eq; same device and zoom tied at 0.02; neck pose σ 10–15° (all 🧠).
- **Shape** [SCU, SF, TOPO, ADD]: soft symmetry ≈ 1 mm in coarse stages, 2–3 mm for per-vertex offsets, 0.5 mm on the upper midline; Laplacian 0.05–0.1 × mean edge; ARAP 5–15 % of rest edge; per-vertex offset cap ≈ 5 mm unless several views agree; MPFB local targets N(0, 0.5²) in [−1, 1], macros σ 0.15 in [0, 1]; FLAME β N(0, 1) over 50–100 components, licensed users only (all 🧠).
- **Expression** [ADD, BR, SK]: basis to absorb then discard, σ 0.3; ψ on neutral views half-normal 0.07 + L1 0.01–0.05, expressive views 0.5; MediaPipe score as a ψ observation σ 0.15–0.25 (0.3 uncalibrated), prior only; neutral jaw rotation N(1.5°, 1°²) (all 🧠).
- **Eyes** [EYE]: globe 24.2 ± 0.9 mm (21–27) 📄; axial length fixed at 24.0 📄; anterior corneal radius 7.8 ± 0.27 mm ✅; kappa 5 ± 2° 🧠; limbus → rotation centre 10.7 ± 0.6 mm 🧠; corneal apex ahead of lateral orbital rim 16 ± 2.5 mm ↔️; upper-lid cover 1.5 ± 1.0 mm, lower-lid show 0.3 ± 0.7 mm 🧠. **Hard constraints** 🧠: lid margin within [0, 0.3] mm of the eye surface; lash roots ≥ 0.2 mm from the cornea; eyeballs rigid, never scaled.
- **Hair and cranium** [HAIR, FB]: trichion–glabella 60 ± 10 mm; hairline L/R 0 ± 3 mm; hair-envelope offset, log-normal μ/σ: bald 1/1, short 10/5, medium 20/10, long 15/8, curly 60/30 mm; hair-covered cranium σ 5–8 mm (all 🧠).

## 5. Template warping

- **W1** **Coarse-to-fine schedule** [SCU]: A similarity plus anisotropic scale (7–9 DOF) → B a 3³–4³ lattice or 10–30 low-frequency modes at ≥ 30–40 mm → C per-vertex offsets with 10–20 mm smoothness → D 2–5 mm, dense data only. Advance when landmarks are < 2–3 % IOD, silhouettes within 1–2 mm and ratios within ~2 %, or RMS gains < 1 % per iteration.
- **W2** **Scan and 3DMM targets** [IMP, BR]: (1) Umeyama proper and reflected, flagging "mirrored source" if reflected RMS < 0.5 × proper, never auto-flipping; rigid 7-landmark RMS 2–5 mm is normal, > 10 mm means wrong landmarks or axes. (2) TPS warp regularised as K + λI ✅. (3) NICP, stiffness {100, 50, 20, 10, 5, 2, 1} × mean edge, landmark weight 1 → 0.05; reject pairs beyond max(3·MAD, 5 mm) (8 mm cross-vendor), normals > 60°, or on boundaries. Region weights: interiors 0, hair-covered scalp 0.1, ears 0.3–0.5, face 1.
- **W3** **Edge flow:** barriers on quad angles outside 30–150°, aspect ratio > 4 and normal flips; ×5 stiffness on lids, lips, nostrils and ears. [TOPO, BR]
- **W4** **Subdivided deliveries:** fit on the Catmull–Clark limit surface, or features shrink by ≈ e²/(6R) = 0.1–0.4 mm. [TOPO]
- **W5** **Artist data:** sculpt mask m → data weight (1 − m) plus a pin to the artist's shape (σ 0.1–0.3 mm); feather engine masks (σ 1.5–2.5 mm); vertex-group weights → confidence; 15–25 region IDs as face sets. Hand-off writes `(1 − support)` into the sculpt mask. [SF, BPY, GW]
- **W6** **Cross-topology:** embed the delivery template barycentrically in the fitting template once; accept vendor wraps at face RMS < 0.5 mm, scalp/neck < 1.5 mm, area ratio ≥ 0.2. [TOPO, BR]
- **W7** **Hair:** hair, brow and beard pixels are excluded from skin terms; scalp vertices stay ≥ 2 mm inside the hair visual hull (hinge). [HAIR]
- **W8** **Basis transfer:** U′ = (W ⊗ I₃)U keeps the N(0, I) prior. Accept projections < 2–3 mm with normal cosine > 0.5; fill the rest harmonically. hm08 targets become two non-negative columns (incr, decr) in [0, 1]. Store W; build U′ at load from the user's file. [TK]

## 6. Silhouette and profile fitting

- **S1** Jaw, cheek and chin outlines are occluding-contour constraints, re-associated every iteration, never fixed vertex IDs [CAM, ADD]. Chamfer distance between rendered silhouette and segmented contour, σ 1–2 px, weighted up in profile views [SCU].
- **S2** No silhouette terms above the trichion or on occluded ears; the hair outline is never the cranium. [FB, HAIR]
- **S3** Profile points are user-pinnable [FB]; gate on mean contour distance ≤ 1 % of face height [LIT].

## 7. Shape keys and write-back

- **K1** Refuse write-back on vertex-count or topology-hash mismatch, or in Edit Mode. [BPY, BR]
- **K2** **Keys:** `Basis` = template mean; `ID_fit` = engine output (`from_mix=False`); `artist` = sculpt layer; optional region keys masked by vertex groups; `slider_max` 1.5. [SK, SCU]
- **K3** **Absolute positions:** with keys present, `me.vertices` writes revert from Basis 📄; Python writes to Basis do not propagate, so add Δ to every dependent key; refits never overwrite `artist − ID_fit`. [BPY, SK, SF]
- **K4** **Mode discipline:** OBJECT mode, `foreach_set`, `mesh.update()`, restore the mode, in one REGISTER/UNDO operator; writes in Sculpt Mode are lost. [SF]
- **K5** **Multires:** never write displacement directly; use `multires_reshape` from a subdivided copy (matching topology and indices 📄), or duplicate, bake the mix and clear keys first. [SF, BPY]
- **K6** **Expressions:** X(ψ) = X₀ + Σψₖ Dₖ + Σ_c (Π ψ) D_c, D at landmark barycentrics; ψ ∈ [0, 1]; ridge when cond(DᵀD) > 1e4; deformation transfer by preconditioned CG. [SK]
- **K7** **Drivers:** simple expressions only 📄; bake them, masks and relatives before export. [SK]
- **K8** **Rig pivots:** eye centre σ 0.5 mm; condyle 10–15 mm anterior, 0–10 mm inferior to tragion, σ 3–4 mm ↔️; head pivot at the mastoid midpoint, σ 6 mm. [RIG]

## 8. Texture projection

- **T1** One camera convention for solver, shader and UV Project; backends agree within 0.5 px on a synthetic checker. [TEX]
- **T2** Project only when landmark reprojection median ≤ 1.5 px, max ≤ 3 px. [TEX]
- **T3** **Weights and outputs:** w = visibility·cos^p θ, faded 60° → 75°, raycasting hair, glasses and eyeballs as occluders; per-texel view index, gain compensation, specular rejection. Write `albedo.exr` (half-float, linear) and `confidence.png` (Non-Color) at 4096 px from 5–7 views plus a low view. [TEX, FB]
- **T4** **UV gates:** |log area ratio| ≤ 0.25 and conformal ratio ≤ 1.3 on the face (≤ 2 on ears); on failure, relax interior UVs with pinned boundaries. Per-vertex backends need edges ≤ √(4ez), e = 0.05 mm. [TEX]
- **T5** **Photometry:** skin shading is low-pass (use low frequencies or G/B, mask specular); SH9 lighting, Huber δ 0.05, excluding the top 2–5 % of pixels and n·v < 0.3; light prior elevation N(30°, 25°), azimuth N(0°, 60°). [SKIN, LIT]
- **T6** **Headless bakes:** `bake(type='EMIT', margin=N//256)`, extrusion ≈ 2 mm, max ray ≈ 8 mm, 1 sample. [TEX]

## 9. Licence constraints

- **L1** Add-on code GPL-3.0-or-later; extensions.blender.org requires CC0 bundled assets and bans remote code and externally downloaded components 📄. [PKG]
- **L2** **Licence as data** on every prior, template and model `{licence, attribution, commercial_ok, bundle_ok}`; unknown or non-commercial items never default and block export; fitting must work with the CC0 template alone; a CC-BY basis writes `ATTRIBUTION.txt`. [PKG, ADD, TK]
- **L3** **Template and models:** default to a project-owned CC0 template derived from the Blender Studio Human Base Meshes or MPFB2 hm08 head (CC0 per sibling notes; MPFB2 code GPL ✅). FLAME 2023 Open (CC-BY-4.0 📄), the MediaPipe canonical mesh and ICT-FaceKit (licence ↔️) are not CC0: user paths or off-platform builds only. FLAME 2017–2023 📄, InsightFace weights 📄 and CelebAMask-HQ-trained parsers 📄 are non-commercial. [ADD, TK, HAIR]
- **L4** Never ship vendor meshes, index lists or priors (MetaHuman, CC3+, Daz, KeenTools); generate correspondence packs locally from the user's licensed copy ↔️. [BR, FB]
- **L5** Porting fSpy/perspective-match solver code makes the engine GPL-3.0 📄. [CAM, PKG]
- **L6** **Bundling:** never bundle NumPy; a model registry `{name, url, sha256, licence, commercial_ok}` downloads only with `online_access` on and user consent, checks the hash, and stores files in `extension_path_user`. [PKG]
- **L7** **Biometric data:** offline by default, no telemetry, iris textures opt-in and deletable, consent naming any cloud step. [PKG, EYE, BR]

## 10. Failure modes the engine must detect

- **Inputs** [ML, GW, CAM]: zero or two faces (need one at confidence ≥ 0.6; request `num_faces=2`); mirrored photo (x-flip lowers RMSE > 30 %, or view RMS > 3σ); EXIF rotation (view RMS > 3σ, `exif_applied` false); expression (warn at smile 0.25, jawOpen 0.10, blink 0.4; drop from identity at 0.5, 0.25, 0.6); blur (< 0.6 × set-median Laplacian variance); detectors disagreeing > 3σ; over-pinning (> 3–5 pins per feature per view); unsolved "front" pose (2° ≈ 2.4–3.5 mm nose shift).
- **Cameras** [FB, BPY, LIT]: focal vs EXIF > 10–15 % or group spread > 5 %; σ(log f) > 0.10; convention bug (C4); depth claims without C7.
- **Geometry** [IMP, FB, SKIN, HAIR, EYE]: unit error (D8; IPD outside 55–72 mm; head breadth > 10 % off 140–160 mm); mirrored mesh or wrong axes (W2); hair read as cranium (W7; g–op outside 182–200 mm); expression absorbed on neutral views; lid–globe gap outside [0, 0.3] mm.
- **Outputs** [BPY, BR, SK, TEX, TOPO]: K1/K4 violations; wrap failure (W6, flips); key QA (lid gap 0–0.5 mm, mirror RMS ≤ 0.5 mm, spill ≤ 1–2 %); UV gate (T4); poles < 2 rings from feature loops or W3 barriers.

## 11. Tests and reproducibility

- **Q1** **Synthetic suite:** s ≈ 0.14 m, 3–5 cameras at 0.5–1.5 m, 50–85 mm-eq lenses, 68–100 landmarks. Noiseless: reprojection RMS < 1e-6 px, vertex RMS < 1e-6·s. At σ = 1 px noise expect RMS ≈ σ√(1 − p/n); fail above 1.2σ. [PKG]
- **Q2** **Tolerances:** round trip 1e-6·s; convergence at relative cost < 1e-10 or step < 1e-8·s; goldens rtol 1e-5; detector goldens 0.05 px; OBJ round trip < 2 µm. [VER, ML, IMP]
- **Q3** **Headless CI:** `blender -b --factory-startup --python-exit-code 1` (without it a failing script exits 0 📄) on 4.5 LTS, 5.2 LTS and 5.3, isolated via `BLENDER_USER_RESOURCES`; `blender_version_min` = oldest line tested. [PKG, VER]
- **Q4** **Accuracy:** NoW-style 7-landmark alignment, then per-vertex scan error ✅; target a face median < 0.5 mm, never better than the reference modality (≈ 0.2–1 mm 📄). Pin accuracy: synthetic renders with known landmarks, RMS mm per class. [IMP, GW]

## 12. Open questions

1. Lens-shift units (C4 test); Python and NumPy shipped in 5.1–5.3. [BPY, VER]
2. Own vs shared wheel site-packages; store rules on compiled wheels; upload cap (unofficially 200 MB). [PKG, ML]
3. 5.x sculpt attribute names, multires write paths, EXIF/HEIC loading. [SF, BPY, TEX]
4. ARKit raw strings; MediaPipe category order and iris indices; MediaPipe, ICT-FaceKit and FLAME 2023 Open auxiliary-file licences. [SK, ADD, TK]
5. Calibration of every 🧠 prior and gate, including novice pin σ, on consented portraits and synthetic renders; no mm likeness tolerance exists. [CAM, SCU, GW]
6. Jaw θmax and translation onset per subject; hm08 counts; FaceBuilder camera naming. [RIG, ADD, FB]
