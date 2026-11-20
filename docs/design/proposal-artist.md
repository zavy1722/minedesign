# Proposal: artist-in-the-loop photo → sculpt-ready head

*Design angle: UX-first. Date 2026-11-20. Builds on `face3d/` at commit 887c5e5 (42 tests passing).*

**How citations work.** A citation such as `(camera-pose-solving 🧠)` names a research note under `research/<area>/` together with its badge. IDs such as CAM-3 or R4.1 point into the five digests in `research/_raw/requirements_*.md`. Every 🧠 or ↔️ number is a **named, tunable default**, never a constant, and the add-on's expert view shows its badge. These gap notes did not exist when this was written: open-template-head-kit, landmark-index-correspondence, metric-3d-landmark-reference, validation-test-bed, face-segmentation-contours, smartphone-camera-pipeline, ear-reconstruction-sculpting, phone-video-depth-capture, guided-workflow-accessibility and cranium-under-hair. Each decision that depends on one of them is marked **[gap: name]** and can be reversed when the note lands.

---

## 1. Vision and the user journey

The north star is FaceBuilder's interaction model: pins on any surface point, a live re-solve, and one camera per photo (facebuilder-blender 🧠). It is rebuilt on open code and commercially safe data, and it adds three things FaceBuilder lacks:

1. **It tells the truth about what the photos measured.**
2. **It never overwrites the artist's work.**
3. **It ends in Sculpt Mode, not in a locked generated mesh.**

The tool speeds up the artist's judgement. It does not replace it. Every automatic decision shows up as a suggestion card with *why*, *what changes* and *undo*.

### 1.1 Principles

- **P1 Live, then thorough.** Adding a photo or dragging a pin re-solves cameras and the coarse shape within one frame budget (≤30 ms target). The slower stages run in the background and replace the preview when they finish.
- **P2 Plain-language uncertainty.** Every reported number carries a likely range and a source: *measured from N photos*, *partly measured*, or *estimated from the template's average shape*.
- **P3 Non-destructive.** Original photos are never modified. Each solve is an immutable snapshot. Fit, asymmetry and artist sculpt live on separate shape keys or Multires layers. A refit never touches the artist's delta.
- **P4 Flags, not corrections.** The engine never pulls a photo-supported feature toward a population norm. It flags the conflict and lets the artist decide (requirements_anatomy §6; likeness-mistakes 🧠).
- **P5 Accessible by default.** The overlays are colour-blind-safe, every action works from the keyboard, no motion is automatic, and expert detail is opt-in.
- **P6 Consent first.** The pipeline will not run without a consent record that covers the operation (ethics §3).

### 1.2 Journey (target: 7–9 photos to a sculpt-ready head in about 20 minutes)

| # | Artist does | System does live | Artist sees |
|---|---|---|---|
| 0 | Creates a project and fills in the consent wizard (self, subject or guardian) | Writes a `ConsentRecord` and sets the scopes | A scope summary in plain words ("reconstruct: yes; texture: no") |
| 1 | Opens the **Shot card** | Renders the 7-view core set: front, ±45°, ±90°, low, high (reference-photography-protocol 🧠) | Diagrams plus distance and lens advice ("phone: 2–5× lens, 1.5–3 m") |
| 2 | Drops photos into the panel | Reads EXIF, bakes orientation into working copies, groups by lens, runs the quality gates (R1.4) | One card per photo with a status word and icon: *Good*, *Usable with care* or *Texture only* |
| 3 | Clicks **Find landmarks**, or places 6–10 pins by hand | Runs the detector helper as a background job. PnP initialises each camera; a joint solve follows | Cameras appear around the head; each photo shows its residual arrows |
| 4 | Reviews suggestion cards | Mirror test, expression tagging, close-camera warning, focal observability | "Photo 4 looks mirrored (selfie?). Flipping it lowers the error 34 %. [Flip] [Keep] [Show me]" |
| 5 | Drags pins in any camera view | Live re-solve of cameras and shape coefficients | The mesh and every other view update while dragging; a coverage map and a *next best photo* suggestion |
| 6 | Clicks **Refine** | Background stages B–D: warp, silhouettes, offsets | A progress bar; the result replaces the preview when ready, with undo |
| 7 | Opens the **Likeness review** | QA metrics, measurement panel, held-out photo check | A worst-first list, a "measured vs estimated" map, flip and blur compare |
| 8 | Clicks **Hand off to sculpt** | Builds the shape-key stack, a Multires copy, region masks, and cameras bound to markers | Sculpt Mode with camera-matched references; the arrow keys step through photos |
| 9 | Optional: texture and export | Projection gated on TEXTURE consent and photo rights; provenance written to the export | An albedo map and a confidence map; export blocked with reasons if a licence is tainted |

---

## 2. Architecture

### 2.1 Layers

```
L4  face3d_blender/   GPL-3.0-or-later Blender extension: UI, overlays, operators, the only bpy import
L3  face3d/pipeline/  orchestration: stages, live solver session, jobs-as-data, suggestion cards
L2  face3d/{solve,fit,texture,qa,guidance,handoff}/  numpy algorithms
L1  face3d/{geometry,mesh,model,io}/  primitives, shape spaces, landmark registry, formats
L0  face3d/project/   policy: consent, licence taint, data classes, audit (bpy-free, A2)
tools/  out-of-process helpers: MediaPipe landmark helper, template-pack builder, extension builder
```

The engine (L0–L3) imports only `numpy`, `math`, `json` and `tomllib`. It uses relative imports and is vendored into the extension at build time (blender A1). Following ethics A1, the engine is MIT-licensed and the glue is GPL-3.0-or-later, so the combined extension is GPL.

### 2.2 Modules

Status: **exists** = keep as is; **extend** = change the existing file; **new** = add.

| Path | Status | Purpose |
|---|---|---|
| `face3d/geometry/camera.py` | extend | Add `from_blender_camera` (inverse), crop/canvas offsets for one render size (C5), k1 only for f35 < 28 mm |
| `face3d/geometry/procrustes.py` | extend | Reflection mode (det −1 allowed) for fitting the symmetry plane (R3.3) and detecting mirrored sources (W2) |
| `face3d/geometry/rbf.py` | extend | Per-landmark λᵢ = α·σᵢ² in normalised units (MM-8). The sign bug is already fixed (commit 0843516) |
| `face3d/geometry/rotations.py` | exists | Rodrigues, Euler |
| `face3d/solve/lm.py` | extend | Return the normal matrix; warm start (τ 1e-6); a `time_budget_ms` stop for live use |
| `face3d/solve/pnp.py` | extend | f35 hypotheses {13, 24, 26, 35, 50, 77, 85, 120, 135, 200}; pitch-flip and yaw-mirror restarts; cheirality (CAM-3) |
| `face3d/solve/bundle.py` | extend | Free-point BA, kept for fixed-camera triangulation, 3D target generation and the cross-check. Adds per-class anisotropic σ, per-pair σ_sym arrays, Huber δ = 2σ plus 4σ rejection |
| `face3d/solve/reconstruct.py` | extend | Tiered focal priors (wires `f_prior_log_sigma`, CAM-6), view-bin weights, mirror test hook |
| `face3d/solve/triangulate.py` | exists | DLT + LM |
| `face3d/solve/live.py` | new | Reduced-parameter joint solver (poses, focal groups, β, jaw θ_v, ψ_v, pins), warm-started and time-boxed |
| `face3d/solve/observability.py` | new | Posterior covariance, σ(log f), region measuredness k_r, next-best-view scoring |
| `face3d/solve/expression.py` | new | Neutral tagging (EM, ≤3 rounds), jaw hinge, landmark-subset rules |
| `face3d/solve/mirror.py` | new | Flipped-image cost test with a significance check |
| `face3d/model/shape_space.py` | new | `ShapeSpace` adapter (FMT-4): `TargetSpace` (MPFB2 CC0 targets, default); `Flame2023OpenSpace` (user path, CC-BY); research spaces opt-in |
| `face3d/model/landmarks.py` | new | Landmark registry (R2.1), scheme adapters (FMT-1/2), barycentric evaluation, contour classes |
| `face3d/model/template_pack.py` | new | Loads and validates a template pack (§2.4.3); topology-hash refusal (INV-4) |
| `face3d/model/defaults.toml` | new | Every numeric default with `{value, sigma, unit, badge, source}` |
| `face3d/fit/template.py` | extend | Barycentric landmark embeddings (today a vertex index), region masks, mirror map |
| `face3d/fit/silhouette.py` | extend | Normal-direction residuals, a one-sided hair hinge, per-region weights, a grid nearest-neighbour search |
| `face3d/fit/stages.py` | new | The staged schedule 0/A/B/C/D with advance gates (W1, R5.2) |
| `face3d/fit/refine.py` | new | Stage C/D offsets with caps, edge-flow barriers and det J gates |
| `face3d/mesh/core.py` | extend | Topology hash; CSR faces (A7) |
| `face3d/mesh/laplacian.py` | extend | Per-vertex smoothness weights (R5.9) |
| `face3d/mesh/reduced.py`, `sparse.py` | exists | Gaussian-RBF subspace; sparse matrices + CG |
| `face3d/texture/raster.py` | new | numpy UV G-buffer and per-view z-buffer |
| `face3d/texture/project.py` | new | View weights, log-gain solve, two-band blend, hole fill |
| `face3d/qa/metrics.py` | new | %IOD residuals, leave-one-view-out (LOVO), chamfer/IoU, shrinkage, symmetry, χ², det J, sanity ranges |
| `face3d/qa/report.py` | new | Plain-language findings: text plus structured cards |
| `face3d/guidance/` | new | Checklists, measurement definitions, warning catalogue, all data-driven from `research/data/*.json` |
| `face3d/handoff/keys.py` | new | Shape-key layout maths, Basis-Δ propagation (K3), refit rebase |
| `face3d/project/{schema,consent,licence,capture,audit}.py` | new | Project file, gates, taint, capture manifest and coverage, append-only audit log |
| `face3d/io/exif.py` | extend | `DateTimeOriginal`, crop suspicion (pixel size vs native) |
| `face3d/io/landmarks_json.py` | new | Reads the helper output (D1 + FMT-1) |
| `face3d/synthetic.py` | extend | Scenario generator: procedural template pack, subjects, noise, mirrored, cropped, expressive and hair-occluded views |
| `face3d/eval/` | new | Point-to-triangle distance, NoW-style alignment (EV-1/2) |
| `face3d_blender/` | new | `blender_manifest.toml`, `__init__.py`, `bridge.py` (the sole bpy↔numpy module), `compat.py`, `props.py`, `jobs.py`, `keymap.py`, `ops/*.py`, `ui/{panels,overlays,palette}.py` |
| `tools/landmark_helper/detect.py` | new | MediaPipe Tasks API in the user's own venv; writes JSON |
| `tools/template_pack/` | new | Maintainer builder and annotation verification (§2.6) |

### 2.3 Data flow

Photos (originals untouched) → `capture.ingest`: EXIF, orientation bake, hash, gates, focal group → landmarks (helper JSON, manual pins, or both) → `pnp` per view against the current model → `live` joint solve (A-space) → `observability`: σ(log f), k_r, next-best-view → **[artist pins → live]** → `stages` B–D in a background job, using `bundle` with frozen cameras to make 3D targets, then `reduced`, `silhouette` and `refine` → `qa` → `handoff.keys` → bridge writes keys and cameras → optional `texture` → export with provenance.

### 2.4 Key data formats

**2.4.1 Project folder** `<name>.face3d/` sits beside the `.blend`, which stores only its path. Purge operators act by data class (ethics 2.2).

```json
{"schema_version": "1.0", "project_id": "uuid", "consent_id": "…", "commercial_intent": false,
 "photos": [{"sha256": "…", "original_path": "…", "working_copy": "photos/p01.png",
   "orientation_baked": true, "crop": null, "exif": {"f35": 77, "LensModel": "…"},
   "focal_group": "Make|Model|Lens|f|W|H|still", "view_tag": "front", "nominal": {"yaw": 0, "pitch": 0},
   "rights_basis": "self_shot", "audit": {"status": "good", "flags": []}, "excluded_from": []}],
 "pins": [{"id": "…", "photo": "…", "xy_px": [1012.5, 884.0], "surface": {"tri": 4411, "bary": [0.2, 0.5, 0.3]},
   "sigma_pct_iod": 0.75, "source": "user", "created": "…"}],
 "solves": ["solves/0007"], "active_solve": "solves/0007",
 "template": {"topology_id": "mpfb2-hm08-head-v1", "topology_hash": "…"},
 "settings": {"rigidity": 0.5, "symmetry_mode": "assist", "detector": "mediapipe_478"},
 "licence_ledger": [{"component": "…", "spdx": "…", "commercial_ok": true}]}
```

User pins and edited landmarks are artist work. They are kept in the project under RECONSTRUCT consent, like the camera solves (ethics 2.2, "project only"). Raw detector output is a cache with `cache_ttl_days = 0` by default, so it is regenerated on reopen.

**2.4.2 Landmark scheme JSON** `face3d/model/schemes/<scheme>.json` describes what each detector index *means*. It knows nothing of any mesh:

```json
{"scheme": "mediapipe_478", "scheme_version": "1", "n_points": 478,
 "detector": {"name": "MediaPipe Face Landmarker", "model_sha256": "<pinned>", "licence": "Apache-2.0", "commercial_ok": null, "is_ml": true},
 "image_convention": "px, origin top-left pixel corner, y down",
 "points": [{"i": 1, "abbr": "prn", "side": "mid", "kind": "vertex", "tier": "A",
   "sigma_class": "anchor", "verified": false, "badge": "🧠"}],
 "contours": [{"id": "face_oval", "indices": ["…"], "kind": "silhouette", "sigma_class": "oval"}],
 "mirror_pairs": [[33, 263]], "z_policy": "ignore",
 "provenance": {"method": "labels rendered on canonical mesh, 2 annotators", "status": "candidate"}}
```

An entry with `verified: false` is used only as a generic sliding-contour point with inflated σ. It never acts as a named anatomical anchor (R2.4 🧠).

**2.4.3 Template pack** `templates/<topology_id>/` holds `pack.json` plus `arrays.npz` (D5):

```json
{"topology_id": "mpfb2-hm08-head-v1", "topology_hash": "sha256(int32 CSR faces)", "n_vertices": "<measured by builder>",
 "units": "mm", "frame": "head_FH", "source": {"name": "MPFB2 hm08", "version": "<pinned>", "sha256": "…", "licence": "CC0-1.0"},
 "body_index_map": "arrays.npz#head_to_hm08", "regions": "arrays.npz#region_ids", "mirror_map": "arrays.npz#mirror",
 "feature_curves": {"lid_margin_upper_L": "arrays.npz#…"}, "smoothness_weights": "arrays.npz#w_smooth",
 "skin_weights_jaw": "arrays.npz#w_jaw", "uv_checksum": "…",
 "shape_space": {"kind": "targets", "file": "targets.npz", "prior": {"sigma": 0.5, "bounds": [-1, 1], "badge": "🧠"}},
 "embeddings": {"anatomical": "emb/anatomical.json", "mediapipe_478": "emb/mediapipe_478.json"}}
```

Each embedding row is `{landmark, tri, bary, annotator_spread_mm, verified_by[]}`.

**2.4.4 Solve result** `solves/NNNN/result.json` plus `arrays.npz` (FMT-8, D6):
- cameras with `convention: opencv_px_corner`, the engine version, and per-view `{R, t, f, f_source, sigma_logf, observable}`;
- β, θ_v, ψ_v; the vertex arrays per stage; per-vertex σ;
- region `k_r`; `scale_mode ∈ {measured, iris, ipd_prior, proportions_only}`;
- QA findings; the licence union; `consent_id`;
- `{addon_version, blender, python, numpy, seed, solver_config}`.

Solves are immutable. **Revert** activates an older one.

### 2.5 Coordinate conventions

| Space | Convention |
|---|---|
| Head (engine) | mm, float64. +x subject's left, +y up, +z out of the face, origin on the midsagittal plane, levelled to the template's FH (R1.1) |
| Camera (engine) | OpenCV: +x right, +y down, +z forward; X_c = R·X + t (`camera.py`) |
| Image | px, origin at the top-left corner of the top-left pixel, so pixel centres sit at i + 0.5. The helper converts MediaPipe normalised coordinates as u = x·W |
| Blender | One parent empty with rotation R_x(+90°) and scale 0.001 holds the head and all cameras, so engine (x, y, z) mm → Blender (x, −z, y) m. The face looks along −Y and `.L` = +X (R1.1, A8). Camera export uses `to_blender_camera` (exists, C4) |
| UV / image buffers | Blender UV origin at bottom-left; `img.pixels` rows run bottom-up (D3); texel centre at (i + 0.5)/N (TEX-1) |
| Left/right | Always the subject's side; a mirrored photo swaps labels (R1.2) |

### 2.6 Assets: how they are obtained and verified (nothing fabricated)

- **Template [gap: open-template-head-kit].** The default is the MPFB2 hm08 base mesh and its CC0 local face targets (blender-face-addons 📄 licence; vertex counts 🧠, so the builder measures them rather than assuming them).
  - `tools/template_pack/build.py` reads a maintainer's pinned MPFB2/MakeHuman install, checks its SHA-256, cuts head and neck while keeping `head_to_hm08` (so MPFB rigs and MakeTarget still apply), converts to mm in the head frame, and writes the pack.
  - If the face has fewer than 6k quads, it applies one Catmull–Clark level and refits on the limit surface (W4, face-retopology 🧠).
  - The derived pack is dedicated CC0 and bundled (it is under the 25 MB budget, Q5).
  - The Blender Studio Human Base Mesh (CC0 ✅, community L2) is supported as an alternative *delivery* topology through a one-time barycentric embedding (W6).
- **Anatomical landmark embedding.** A developer-mode annotation panel guides two independent annotators through the registry (definitions from craniometric-landmarks).
  - Accept when inter-annotator distance is ≤1.0 mm for junction points (en, ex, ch, sn) and ≤2.5 mm for soft points (g′, zy′, go′), the bounds from R4.1. Otherwise adjudicate.
  - The spread is stored and added in quadrature to σ.
- **MediaPipe 478 → template [gap: landmark-index-correspondence].**
  - Maintainers fetch the Apache-2.0 canonical face mesh (SHA-pinned) and register it to the template with our own NICP (MM-12 schedule), anchored on the verified anatomical landmarks.
  - Each index takes the closest-point barycentric on the template.
  - Verify three ways: labels rendered on both meshes; mirror pairs mapping to mirror points within 1.5 mm; anatomical candidates (R2.4) within their σ.
  - Only the derived table ships, with provenance. Whether derived Apache data may sit in a CC0-only bundle is ethics C7; the fallback is to generate the table on first run from a user-fetched mesh.
- **Priors.** These are loaded from `research/data/<topic>.json` tables (R2.8) into `defaults.toml` entries carrying a badge. A prior whose status is `knowledge` cannot have non-zero weight in canon terms (community §4).
- **Tests never need these assets.** `synthetic.py` builds a procedural template pack with synthetic targets and embeddings. Asset-dependent tests skip when the pack is absent.

---

## 3. Algorithms

### 3.1 Joint objective (live A-space)

The parameters are p = {ω_v, t_v}ᵥ ∪ {ℓ_g = log f_g} ∪ β ∈ ℝᴷ ∪ {θ_v} ∪ {ψ_v}. Landmark i is a barycentric point on the template, X_i(β) = X̄_i + B_i β, where X̄_i = A_i T̄ and B_i = A_i S are precomputed, L×3×K (MM-2).

E(p) = Σ_v w_v Σ_i ρ_δ(‖L_vi⁻¹(π_v(X_i) − u_vi)‖) + E_contour + E_sil + E_pin + E_shape + E_sym + E_mid + E_cam + E_scale + E_canon

- **Noise.** Σ_vi = (s_c · IOD_v)²·κ·I₂, with s_c set by class (blender table P, ADD/FB 🧠): anchors 1.5 %, contour normal 2.5 %, oval 4 %, iris centre 1 %, user pin 0.75 %. IOD is defined once, as pupil-to-pupil in pixels. κ = N/N_eff with N_eff 60–100 for MediaPipe (craniometric-landmarks 🧠). The detector floor is u = face width/256 (ML 🧠). This retires `sigma_px = 1.0` (C5).
- **Robust loss.** Huber with δ = 2 whitened units. After convergence, drop points beyond 4σ and re-solve; flag a view with more than 15 % rejected (BA-5 🧠).
- **View weight.** w_v = 1/n_bin(v), using 15° bins, and no view may carry more than 40 % of the data weight (R1.8 🧠).
- **Solver.** LM (exists) with (JᵀWJ + μ·diag JᵀWJ)δ = −JᵀWr and a multiplicative rotation retraction (BA-6). P ≈ 6V + G + K ≈ 110 parameters, so the dense J at 9 × 478 points is about 8.6k × 110: 2–5 warm-started iterations per drag event.

### 3.2 Camera initialisation

For each view and each hypothesis h: f_h = f35_h·√(W² + H²)/43.27 (CAM-2 🧠). Then an affine pose initialisation (exists), LM over (ω, t, ℓ), restarts from pitch-flipped and yaw-mirrored poses, and the best robust score with every z_c > 0 wins (CAM-3 🧠).

Priors (CAM-6, R2.2, 🧠):

| Focal source | σ(log f) |
|---|---|
| Uncropped EXIF | 0.03–0.04 |
| Crop suspected | 0.08 |
| Phone, no EXIF | 26 mm at 0.25 |
| Unknown | 50 mm at 0.6 |

Other camera terms:
- A focal-group tie of 0.02 (CAM-5).
- Near-frontal distance from d ≈ f_px·63/IPD_px with σ_log 0.06 (R1.5), or a tape distance with σ 5 cm (R2.4).
- Hard bounds 0.25–10 m (C6).
- Pose-tag priors: yaw σ 10° (5° with floor marks), pitch 5° (8–10° on the high and low rings), roll 3° (R2.7 🧠).

### 3.3 Observability and honest camera reporting

At the optimum, H = JᵀWJ + Λ_prior and Σ = H⁻¹; the β block already marginalises the cameras. The following are reported per focal group (CAM-7, C2 🧠):
- σ_ℓ = √Σ_ℓℓ.
- Free the focal only when σ_ℓ < 0.10 and the views span ≥60° of yaw (R2.3).
- If σ_ℓ > 0.8 × the prior σ, show "Lens could not be measured from these photos; using the camera's EXIF".
- Perspective strength P = 100 mm/z: above 0.1 is "strong perspective, focal measurable"; below 0.03, "nearly flat".
- A radial-residual slope against ρ_iδ_i that implies more than 5 % magnification error triggers "Focal or distance may be wrong" (R2.8).

### 3.4 Shape prior and rigidity

E_shape = ½λ(r)·Σ_k(β_k/σ_β)², with λ(r) = 10^(2r−1) and the rigidity slider r ∈ [0, 1], default 0.5, which is MAP (facebuilder-blender 🧠).

- **Default `TargetSpace`.** MPFB targets with σ_β = 0.5, softly bounded to [−1, 1] by a quadratic barrier (blender table P 🧠). This space is **semantic, not statistical**: it has no population covariance. The UI therefore says "estimated from the template's average shape", never "typical for people like the sitter".
- **`Flame2023OpenSpace`, opt-in.** User-supplied (CC-BY-4.0, attribution written into `ATTRIBUTION.txt`). Whitened β ~ N(0, 1), with K raised from 20 to 50 as the gates pass (MM-3 🧠). Flag ‖β‖² > χ²_K(0.999) (86.7 at K = 50, MM-5).
- **Per-landmark σ arrays.** Population-SD based, replacing the scalar 8 mm (R4.1 🧠).
- **Ratio priors.** Weak, on log ratios (R4.3); they become diagnostics when a statistical space is active.
- **Prior share.** Shown as a diagnostic. With ≥2 pose-solved views per landmark, a prior share above 20 % (R1.4 🧠) produces the suggestion "lower Rigidity", not an automatic change.

### 3.5 Contours, silhouettes, hair

- **Sliding contours** (lids, lips, brows). r = n̂ᵀ(u_c − π(γ(s*)))/σ_n, where s* = argmin_s‖u_c − π(γ(s))‖ is re-associated every iteration on the projected template feature curve γ. The tangential residual is free (σ_t ≥ 5u, ML 🧠).
- **Jaw and cheek oval.** γ is the current occluding contour restricted to the jaw and cheek region mask. Beyond 60° yaw, the silhouette term replaces the contour points (BA-4, S1).
- **Silhouette.** Given mask boundary samples o_m with outward normals n_m and the nearest projected silhouette vertex s(m):
  r_m = n_mᵀ(π_v(x_s(m)) − o_m)/σ_sil, with σ_sil = 1–2 px, weighted up in profiles (S2 🧠).
  It is gated on the unoccluded jaw and cheek at mean distance ≤1 % of face height, with IoU reported (S5).
- **Hair.** For scalp silhouette vertices, use a one-sided hinge r_j = max(0, φ_v(π_v(x_j)) + m_px)/σ_h. Here φ is the signed distance to the hair-plus-skin hull, positive outside, and m_px is 2 mm converted at the vertex depth (W7). There are no silhouette terms above the trichion (S3). The cranium is gated on g–op of 182–200 mm (blender §10) **[gap: cranium-under-hair]**.
- **Masks [gap: face-segmentation-contours].** In order of preference:
  1. a user-traced outline (a lasso in camera view);
  2. the MediaPipe oval;
  3. an optional SAM 2 helper mask (Apache-2.0, ethics §5).
  BiSeNet/CelebAMask weights are never used.

### 3.6 Expression and mirror handling

- **Tagging.** Each view is tagged from MediaPipe scores (R2.5). It is non-neutral if mouthSmile > 0.25, eyeBlink > 0.4, jawOpen > 0.08 or browDown > 0.35 (anatomy §6 🧠), using an EM loop of at most 3 rounds over ‖ψ_v‖ when a basis exists (BA-9).
- **Default path (no expression basis).** Identity comes only from neutral views. Lip landmarks are dropped from open-mouth views and lid landmarks from squints (R3.7). A per-view jaw hinge
  x′_j = x_j + ω_j(R(θ_v·a)(x_j − c) − (x_j − c))
  absorbs small openings. Here c is 10–13 mm anterior to tragion (BA-1 🧠), ω_j are the pack's jaw skin weights, and θ_v ~ N(1.5°, 1°²) on neutral views (FACS 🧠).
- **With an expression basis.** X_v = X(β) + Eψ_v, with a neutral anchor ‖mean_{v∈N} ψ_v‖/0.1 (BA-9). If no view is neutral, the card reads: "Mouth and eyelid shape may include expression – add one relaxed photo".
- **Mirror test.** Compute E_v (as shot) and E_v^flip (u → W − u, L/R labels swapped). Suggest a flip when (E_v − E_v^flip)/E_v > 0.2 (R1.6 🧠) **and** E_v − E_v^flip > 2√(2n_v), the χ² noise level (derived). Otherwise report "can't tell (face too symmetric)". The image is never flipped automatically.

### 3.7 Template warp schedule and asymmetry

The stages are 0 (similarity + anisotropic scale), A (β), B, C and D (W1, R5.1). They advance on gates:
- A → B: landmark RMS < 4 % IOD and chamfer < 2–3 mm.
- Leave B: RMS < 3 % IOD in every view, including the held-out photo.
- During C and D, no landmark may move more than 0.5 mm (R5.2 🧠).

How B–D work:
- **3D targets.** With cameras frozen, `bundle_adjust` (exists) triangulates each landmark against the model prior, σ 8 mm in B and 3–4 mm in C (community §4 🧠). This yields X*_i and Σ*_i, and silhouette targets are back-projected at the vertex depth (exists).
- **B.** `ReducedDeformer` (exists): d(x) = Σ_j c_j·exp(−‖x − x_j‖²/2s²) with s = 30–40 mm, solving (ΦᵀWΦ + μK_cc)c = ΦᵀWd with W = Σ*⁻¹.
- **C.** `laplacian_deform` (extended): min_d ‖diag(√w_s)·L·d‖²_M + Σ_c w_c‖x_c + d_c − p_c‖².
  - w_s per vertex (R5.9 🧠): ligament strips ×3–5, lid margins ×3, lips ×0.3, forehead ×0.5; lids, lips, nostrils and ears ×5 for edge flow (W3).
  - |d| is capped at 3–5 mm unless ≥2 views agree (MM-10), enforced by projected IRLS.
  - Gates: quad angles 30–150°, aspect ≤4 (W3), det J > 0.2 (MM-11).
- **D.** Only where ≥2 views agree (R5.1).
- **Two-solver cross-check.** If free-point X*_i and model X_i(β) disagree by more than 3σ, the card reads "the photos say more than the template can express here – sculpt it". The region is added to the `f3d_sculpt_here` mask.
- **Symmetry.** E_sym = Σ_p‖D_p⁻¹(X_l − M·X_r)‖² with per-pair σ (R4.2 🧠): canthi 0.7–1.0 mm, alare 1–1.5, cheilion 1.5–2.0, gonion 2.5–3.0, ears 3–4. Midline σ: n 0.75–1.0, prn and sn 1.5–2.0, pg 2–3 mm. Full weight applies only where k_r < 0.5; elsewhere it is "assist" (×0.25). The plane is re-fitted by weighted reflection Procrustes every outer iteration (R3.3).
- **Never symmetrise the output.** With mirror map m(·), S = ½(X + M·X_m) and `Asym` = X − S (R5.9). Over-symmetry is flagged if RMSD(X, mirror) < 0.3 mm while the photos are asymmetric (anatomy §6).

### 3.8 Detail refinement

Shape is fitted down to wavelengths of about 5 mm. Anything finer is displacement, gated by mm/px: pores ≤0.033, fine lines ≤0.08, line positions ≤0.25 (R5.11 🧠). In the default path the engine adds **no** photometric detail.

Instead it produces sculpt guides:
- a camera-projected **stencil** of the best view per region;
- crease **curves** from multi-view-consistent image edges (each edge is accepted only if it reprojects within 2σ in ≥2 views);
- the `f3d_confidence` attribute.

Optional, off by default: SH9 shading refinement on edges ≤1 mm, clamped to ±2.5 mm with a 6 mm high-pass (OPT-1 🧠), always labelled *estimated*.

### 3.9 Texture projection

This runs only with TEXTURE consent, rights_basis ≠ unknown, and median reprojection ≤1.5 px with max ≤3 px (T2, ethics §3).

- **G-buffer.** Texel centres map to a 3D point p_t and normal n_t. Each view has a z-buffer at 1–2k px. vis_v(t) = [z_v(p_t) ≤ zbuf_v + ε], with ε = max(1 mm, 2σ_geom) (TEX-1).
- **Weights.** w_v(t) = vis·cos²θ·fade(θ; 60°→75°)·footprint·edge, with 5 px erosion and a 10 px ramp (TEX-2 ↔️).
- **Gains.** log I_v(t) = log g_v + log a(t), solved by least squares over overlap texels with Σ_v log g_v = 0 (TEX-3). Directional-light views get gains only and contribute no albedo (R7.2).
- **Blend.** `two_band`: the low band is the weighted mean after a 3 mm Gaussian in UV-mm; the high band comes from the arg-max-weight view (TEX-4). Holes ≤5 mm are filled harmonically. Mirroring is allowed only for the low band, from sources with weight ≥0.3·w_max. Detail is never mirrored (TEX-5, R5.11).
- **Outputs.** Linear float albedo, a confidence map and a per-texel view index. Without a colour chart: "absolute colour unknown" (TEX-6).

### 3.10 Capture coaching: next best photo

For a candidate pose c from the shot list (yaw {0, ±20, ±45, ±90}, elevation {−25, 0, +25}, at 1.75 m with a 77 mm-equivalent lens; reference-photography-protocol 🧠):
1. Predict J_c at the current model.
2. Marginalise the candidate's 6 pose parameters by Schur complement: H′_ββ = H_ββ + J_βᵀWJ_β − J_βᵀWJ_p(J_pᵀWJ_p)⁻¹J_pᵀWJ_β.
3. Score Δ_c = Σ_r w_r[tr_r Σ − tr_r Σ′_c], where tr_r(Σ) = Σ_{j∈r} tr(S_jΣ_ββS_jᵀ) and w_r are the perceptual weights (face-perception-likeness Table B 🧠: lids 1.0, brows 0.9, lips 0.8, nose 0.7, …, ears 0.1–0.2).
4. Show the argmax as one sentence, for example: "Next: left profile – camera at the subject's left, eye height, 1.5–2 m."

Nose and chin projection are labelled "measured" only with a front view plus a view at |yaw| ≥ 60° (R5.9).

### 3.11 QA metrics → plain language

Measuredness of region r: k_r = 1 − tr_r Σ_post / tr_r Σ_prior.

| Metric | Shown as | Threshold (source) |
|---|---|---|
| k_r | **Measured** / **Partly measured** / **Estimated** | ≥0.8 / 0.5–0.8 / <0.5 (≥0.8 from anatomy §6 PER 🧠; 0.5 is a design choice) |
| Per-vertex 2σ | "likely within ±X mm" | linearised; calibrated in CI (§5.2) |
| Landmark residual | "%IOD" in expert view; "off by about N px" otherwise | worst-first (R8.2) |
| LOVO ratio | "This photo disagrees with the others" | held-out > 2× in-sample (camera-pose-solving 🧠) |
| ‖β‖² < K − 2√(2K) | "Pulled toward average – likeness may be weak" | R5.8 🧠 |
| Mirror RMSD | "Too symmetric" / "Unusually asymmetric – check pose" | <0.3 / >1.5 mm (anatomy §6 🧠) |
| IPD, g–op, breadth | "Scale looks wrong" | 55–72 / 182–200 / 140–160 mm (blender §10 🧠) |
| Scale references | "Your measurements disagree" | >1 % (BA-10) |
| Interior OK, contour bad | "Lens or distance wrong, not the face" | SIL-3 🧠 |
| det J ≤ 0.2, flipped quads | "Surface folded – raise Rigidity" | MM-11, W3 |

---

## 4. Blender add-on design

### 4.1 Manifest and permissions

```toml
schema_version = "1.0.0"
id = "face3d_likeness"
version = "0.1.0"
name = "Face3D Likeness"
tagline = "Fit a sculpt-ready head to consented photos"
maintainer = "Face3D contributors <maintainers@example.invalid>"
type = "add-on"
blender_version_min = "4.5.0"
license = ["SPDX:GPL-3.0-or-later"]
copyright = ["2026 Face3D contributors"]
tags = ["Sculpt", "Modeling", "Camera"]
[permissions]
files = "Read reference photos and write project and landmark files"
[build]
paths_exclude_pattern = ["__pycache__/", "*.blend1", "tests/"]
```

- There are no wheels in the core build, so one zip serves every OS and NumPy comes from Blender (packaging 🧠).
- `network` is **not** declared until an optional, consented downloader exists (ethics A3).
- `blender_version_min` declares only what CI tests (packaging ↔️). The engine itself runs on Python 3.11 and 3.13 with NumPy 1.26 and 2.x (A4), so 4.2 works but is not declared.
- **Landmark helper, Path A.** `tools/landmark_helper/` is a script the user runs in their own venv (`pip install mediapipe` is *their* step, not runtime pip). It is invoked through a user-configured interpreter path or run standalone, and it writes JSON.
- **Path B.** An optional platform-split build with onnxruntime wheels (packaging 🧠, ↔️ store policy).
- The **zero-download path** (manual pins plus imported JSON) always works (ethics A4).

### 4.2 Panels: a guided rail

3D View sidebar tab **Face3D**:
- **Guide**: a vertical step list (Consent → Photos → Check → Landmarks → Cameras → Shape → Review → Sculpt → Texture → Share). Each step shows an icon *and* a word (`CHECKMARK` Done, `ERROR` Needs attention, `DOT` Not started), one primary button, and a *Why?* link.
- **Photos**: a thumbnail list with status word, lens group, estimated distance and the suggestion cards.
- **Solve**: Rigidity, Symmetry (assist / prior / enforce), Expressions (off / jaw-only / basis), focal mode per group, **Refine**, and **Revert to solve #n**.
- **Likeness**: findings worst-first, the measurement panel, coverage map and next-best-photo.
- **Sculpt**: hand-off, rebase-on-refit, and the mask toggles.
- **Privacy**: consent scopes, retention clocks, *Prepare for sharing*, *Purge*.
- An **Expert** toggle reveals σ, %IOD, χ², badges and solver configuration.

### 4.3 Operators and keymap

Every operator has `bl_options = {'REGISTER', 'UNDO'}` unless it is modal. All keys are user-rebindable through the add-on keymap.

| Operator | Key (in camera view) | Notes |
|---|---|---|
| `face3d.photos_add` | — | multi-select file browser; runs ingest + gates |
| `face3d.landmarks_detect` / `_import` | — | background job / JSON |
| `face3d.view_next` / `_prev` | PageDown / PageUp | look through the next camera; also bound to timeline markers |
| `face3d.pin_tool` (modal) | P | drag = live solve; Tab/Shift-Tab cycles pins; arrows nudge 1 screen px (Shift ×10, Ctrl ×0.1); Del removes; Enter commits; Esc cancels |
| `face3d.solve_refine` / `_cancel` | Ctrl-R / Esc | background stages B–D |
| `face3d.accept_card` / `_dismiss_card` | Ctrl-Enter / Ctrl-Backspace | acts on the focused suggestion |
| `face3d.compare_flip` (hold) | F | photo ↔ model while held; never auto-flashing |
| `face3d.compare_blur`, `_grey`, `_edges` | B, G, E | likeness aids (R8.1) |
| `face3d.overlay_toggle` | H | hide or show the overlays |
| `face3d.handoff_sculpt`, `face3d.rebase_sculpt` | — | §4.6 |
| `face3d.texture_project` | — | gated |
| `face3d.report_export` | — | HTML/text report for screen readers and sharing (consent-scoped) |
| `face3d.prepare_for_sharing`, `face3d.purge` | — | ethics F9 |
| `face3d.shortcuts` | ? | shortcut sheet |

### 4.4 Overlays and accessibility

- **Drawing.** A `gpu` POST_PIXEL handler maps photo pixels into the camera frame (reference-camera-setup 🧠). The pure mapping functions live in `face3d/qa/overlay_geom.py`, so they are unit-tested outside Blender.
- **Encoding by shape first, colour second.**
  - Observed landmark: a hollow ring. Model landmark: a filled dot. Residual: a line. Pin: a diamond. Uncertainty: a 2σ ellipse.
  - Photo contour dashed; model silhouette solid.
  - Every glyph has a 1 px dark halo, so it reads on any photo.
- **Palettes** in `ui/palette.py`:
  - Categorical: Okabe–Ito (blue #0072B2, orange #E69F00, sky #56B4E9, vermillion #D55E00, plus black and white).
  - Residual bands: blue → orange → vermillion, with band labels.
  - The measured/estimated map is a sequential luminance ramp; a *Monochrome* and a *High contrast* palette are selectable.
  - Red/green is never the only cue.
  - Choosing Okabe–Ito is our design decision; the research does not cover palettes **[gap: guided-workflow-accessibility]**.
- **Mesh map.** `f3d_confidence` is a colour attribute shown with a legend. "Show estimated regions only" uses a face-set mask, which works without any colour.
- **Scale and motion.** Glyph sizes and line widths follow `preferences.view.ui_scale` and `ui_line_width`. Flip compare is hold-to-view. The 3 Hz "blink GIF" from R8.1 is replaced by a manual toggle, because three flashes per second is the common photosensitivity limit (🧠).
- **Language.** Default strings avoid jargon (a glossary sits behind *Why?*) and go through `bpy.app.translations`. Blender has no screen-reader support, so every finding is also in the Info log and in the exported report.

### 4.5 Undo, history, background jobs

- **Writes.** The bridge reads with `foreach_get` into float32 or int32 buffers, converts to float64, and writes back with `foreach_set` and `mesh.update()` in OBJECT mode with the mode restored. It refuses on a topology-hash mismatch or in Edit Mode (A3, K1, K4).
- **Live dragging.** The modal pin tool writes previews into a muted `f3d_live` key from a timer; these writes stay off the undo stack. On release, one `ed.undo_push("Move pin")` is pushed. Pins are PropertyGroups, so Blender's undo restores them. An `undo_post` handler sees the changed pin hash and re-runs the live solve. IDs are re-fetched by name (A5).
- **Jobs.** Short solves run in a worker thread on copied arrays. Refine and texture run as a `sys.executable -I` subprocess exchanging `.npz` files, so a crash cannot take Blender down. Results are applied from `bpy.app.timers` at 0.05–0.1 s with at most 10–20 ms per tick. Esc cancels. Under `blender -b` the same pipeline runs synchronously (A5).
- **History.** Each Refine creates an immutable solve. *Revert* re-applies it to `ID_fit` without touching `artist`.

### 4.6 Shape keys and Multires hand-off

Key stack on the template object (K2, SK-1):
- `Basis` = template mean.
- `ID_fit` = the symmetric fit S. Its `slider_max` is 1.5, but values above 1 are a caricature preview, recorded in metadata (R5.8 ↔️).
- `Asym` = X − S.
- `artist` = the sculpt layer.
- Muted diagnostics `stage_A` … `stage_D`.
- Region keys are masked by vertex groups.

Per-photo expression keys are written **only** with RIG_ANIMATE consent (ethics F4); otherwise ψ_v stays in the solve file.

- **Refit rebase** (`handoff/keys.py`): new `artist` = old `artist` + (new `ID_fit` − old `ID_fit`), which preserves the artist's delta. Python writes to Basis add Δ to every dependent key (K3).
- **Sculpt copy.** Duplicate the object, bake the mix, clear the keys, then add Multires at L2 (likeness) and L3 (detail) (SK-3). The original stays hidden as the *fit snapshot*.
- **Later refits.** Pushed through `multires_reshape` from a subdivided copy with matching topology (K5). Whether Multires detail follows base edits is open (blender Q4), so a test scene guards it and the fallback is "new sculpt copy plus the old one kept".
- **Written alongside:**
  - 15–25 region vertex groups and face sets;
  - `f3d_confidence` and `f3d_sculpt_here` masks feathered at σ 2 mm (W5);
  - brow and hairline curves;
  - eyes as separate rigid 24 mm spheres (R6.4);
  - one locked camera per photo, with Background Image (Front, α 0.4, Stretch) and timeline markers, so ←/→ steps through photos while sculpting;
  - "Lock Camera to View" off (sculpting-likeness-workflow 🧠).
- **Artist edits back into the engine.** A painted sculpt mask m becomes data weight (1 − m) plus a pin term at σ 0.2 mm (W5).
- **Rig-ready.** `head_to_hm08` allows round-tripping as an MPFB `.target`, so MPFB rigs, Rigify and ARKit-named expression tools apply downstream.

### 4.7 From anatomy research to in-app guidance

- **Capture checklist.** Generated from R1.4 and reference-photography-protocol: hair off ears and hairline, glasses off 10–15 min beforehand, gaze on a fixed mark, camera at eye height, ≥1.5 m, the phone's 2–5× lens, no portrait or beauty modes. Each item is ticked automatically when a gate confirms it.
- **Likeness checklist.** Ordered by perceptual rank (face-perception-likeness Table B 🧠): lids → brows → lips → eye spacing and depth → nose → thirds → jaw and hair mass → age cues → ears. Each item opens the camera that best shows it.
- **Measurement panel.** Shows en–en, ex–ex, al–al, ch–ch, n–sn, sn–sto, n–gn, zy–zy, go–go, g–op, ear length, and the nasolabial, gonial and cervicomental angles.
  - Each is shown as *value ± 2σ*, its measuredness, and a population z-score **only when method and landmark variant match** (R1.3, R2.2).
  - Caliper entries become constraints, E_cal = Σ((‖X_a − X_b‖ − d − o)/σ)² (R5.7).
  - |z| > 2.5 where no photo sees the feature is shown as a note, never a correction (R8.2).
- **Warning catalogue** (`guidance/warnings.toml`). Each failure mode from the four digests has a title, a one-line why, actions, its source topic and its badge. For example: "Close camera (~0.45 m): noses look ~20 % larger at this distance (100 mm/d). [Use for texture only] [Keep]".
- **Ordering hinges** (R5.2) appear as warnings, for example "glabella behind nasion".
- **Subject metadata** (age, `sex_prior`, BMI) is asked for, optional, explained, and never inferred. Ancestry is never asked (R2.7, R7.4).

---

## 5. Validation and QA

### 5.1 Automated synthetic tests

All run under plain CPython with pytest; there is no Blender binary in CI here.

- **Q1 suite.** 3–5 cameras at 0.5–1.5 m, 50–85 mm. Noiseless: reprojection < 1e-6 px. With σ = 1 px: RMS ≈ σ√(1 − p/n), failing above 1.2σ.
- **EV-5 sweeps.** z 0.25–5 m, f35 13–200 mm. Focal error < 5 % and rotation < 2° when the span is ≥60° (R8.4 🧠). "Not observable" must be reported for frontal-only views at ≥2 m.
- **Live solver.** Its result converges to within 1e-3 relative of the batch solve. A latency benchmark (9 views, 478 points, K = 50) is recorded, not asserted.
- **Behaviour tests.**
  - mirror detection (§3.6);
  - expression tagging with drop rules;
  - contour sliding under yaw;
  - the hair hinge (no inward pull);
  - stage gates;
  - no landmark moving > 0.5 mm in C and D;
  - fold gates.
- **Hand-off maths.** The rebase preserves `artist − ID_fit` to 1e-9. Basis-Δ propagation is exact. Topology-hash refusal works.
- **Texture (TEX-8).** Random gains are recovered within 2 %; no nose colour lands on occluded cheek texels.
- **Policy.** Gates refuse missing or expired scopes. Licence taint is the AND over components. A socket guard monkeypatches `connect` during a full pipeline run (ethics A7). An AST check finds no `bpy` import under `face3d/`.
- **Packaging.** `tomllib` lints the manifest (tagline ≤64 characters with no trailing period, SPDX licence, permission reason style). Every bundled file needs an SPDX row (ethics §5).
- **Blender runtime.** Smoke scripts for `blender -b --factory-startup --python-exit-code 1` (Q3) exist, but they run in an optional external CI.

### 5.2 Honest uncertainty

**Calibration test.** Over 200 seeded Monte-Carlo subjects, the fraction of vertex and landmark errors inside the displayed 2σ must lie in [0.90, 0.98]. If it does not, the displayed ranges are inflated by the measured factor and the factor is reported.

Every result also carries:
- `scale_mode`;
- "not validated against a scan" until the EV-1 harness has compared it;
- no claim finer than the capture modality (Q4).

The research mostly supplies unverified 🧠 defaults, so the report footer counts how many active defaults are 🧠.

### 5.3 Likeness checks shown to the artist

- **Camera-matched overlay** with an opacity slider.
- **Compare modes:** silhouette, edge (numpy gradient), flip (hold), blur at σ 3 % of face width (the 8–16 cycles-per-face-width band, face-perception-likeness 📄), greyscale and thumbnail (R8.1).
- **Held-out photo.** The artist picks one photo to exclude; its residuals are the honest likeness score.
- **Worst-first residual list** grouped by perceptual rank.
- **Familiar-viewer review sheet.** A PNG grid of photos beside camera-matched renders, consent-scoped, with a 5-question form. Unfamiliar viewers, including the artist, judge poorly (face-perception-likeness 🧠).
- **Caricature preview.** S(α) = M + α(S − M), α from 0.9 to 1.2, preview only (R5.8 ↔️).
- **Identity-embedding scores** are off by default (IDENTITY_CHECK, 1:1, RAM-only, no NC weights).

---

## 6. Milestones

Each milestone ships on its own and is accepted only by tests runnable here.

| M | Ships | Acceptance |
|---|---|---|
| **M1 Honest camera solve** | `pnp`/`reconstruct`/`bundle` extensions; `observability`, `mirror`, `qa.report`; a CLI `python -m face3d solve project.json` printing plain-language findings | Q1 and EV-5 thresholds above; mirror flagged in ≥95 % of seeded mirrored views with ≥1 mm SD asymmetry and ≤2 % false flips; calibration in [0.90, 0.98] for BA points |
| **M2 Project, consent, capture** | `project/*`, capture gates, coverage map, next-best-view, `io/landmarks_json`, the helper script with a fixture JSON | Gate matrix tests (ethics §3, F1–F20 where applicable); the socket guard; next-best-view recovers the profile as top suggestion for frontal-only synthetic sets in ≥90 % of seeds |
| **M3 Template pack + staged fit** | `model/*`, `fit/stages`, `fit/refine`, silhouette extensions, the pack builder (tested on a fixture OBJ), the synthetic pack | In-space synthetic subjects: face vertex RMS ≤0.5 mm noiseless and ≤1.5 mm at 2.5 % IOD noise (7 views). Out-of-space: stage C cuts face RMS ≥30 % against A. Profile error ≤1–1.5 mm at prn and pg (SIL-3); every gate is exercised |
| **M4 Extension MVP** | Manifest, bridge, cameras and backgrounds, import landmarks, background Refine, `ID_fit` + `Asym` keys, static overlays, report panel | Manifest lint; AST bpy isolation; overlay-geometry and key-maths unit tests; `to_blender_camera` ↔ `from_blender_camera` round trip within 1e-6·s |
| **M5 Live pins + guided rail** | `solve/live`, modal pin tool, undo integration, keyboard map, palettes, cards, checklists, measurement panel | Live result ≤1e-3 from batch; every journey step reachable by keyboard (keymap completeness test); palette test: all categorical pairs distinguishable under simulated deuteranopia, protanopia and tritanopia (ΔE ≥ 20, own design target) |
| **M6 Sculpt hand-off + refit without loss** | `handoff/keys`, sculpt copy, Multires rebase plan, masks, curves, markers, likeness aids | Rebase identity to 1e-9; mask feathering; held-out and LOVO metrics; caricature excluded from export unless set |
| **M7 Texture + sharing** | `texture/*`, gates, provenance, *Prepare for sharing* | TEX-8; UV gates (T5); export blocked on taint with the offending components listed |
| **M8 Opt-in statistical spaces** | `Flame2023OpenSpace` (user path, attribution), research adapters behind warnings, expression basis if FLAME 2023 Open carries one (ethics C6) | χ² gates; `basis_sha256` refusal; the default path still passes every test with the CC0 pack alone (L2) |

---

## 7. Risks and deliberate omissions

### Risks

1. **Uncalibrated defaults.** About 72 % of anatomy claims, and most σ values and gates, are 🧠. Mitigations: named defaults with badges, the calibration test, the held-out photo, and a future real-scan set [gap: validation-test-bed, metric-3d-landmark-reference].
2. **A semantic target space is not a population prior.** It may over-flex or shrink. Mitigations: the rigidity slider, the shrinkage and χ² cards, the two-solver cross-check, and the M8 FLAME 2023 Open option.
3. **Template quality and size.** hm08 face loops and counts are unverified; it may need a subdivision. The template is a plug-in pack, so the choice is reversible [gap: open-template-head-kit].
4. **Landmark tables need human annotation.** This is the schedule bottleneck. Mitigation: two-annotator protocol, with `verified: false` entries down-weighted [gap: landmark-index-correspondence].
5. **Helper friction.** A venv is a hurdle for non-experts. Manual pins plus import always work. MediaPipe weight licence is ↔️.
6. **Live latency.** Python LM inside Blender may miss 30 ms. Fallbacks: fewer iterations per event, fewer contour points, a subsampled 100-point MediaPipe set (craniometric-landmarks 🧠).
7. **Multires rebase semantics** are unverified in 5.x (blender Q4).
8. **Store and legal drift.** Extension download rules (C8), biometric law (BIPA, AI Act Art. 50), and Apache-derived data inside a CC0 bundle (C7).
9. **Phone pipelines** may alter geometry (multi-frame fusion, face retouch) [gap: smartphone-camera-pipeline]. Mitigations: lens grouping, retouch-risk flags, robust per-view σ.

### Deliberately left out

- Single-image neural regression (MICA/DECA) and generative or AI meshes as identity sources. The research caps their information at 25 % anyway (OPT-2).
- Neural detail, generative texture fill and default photometric detail.
- Hair strands. Teeth and tongue fitting (OPT-5).
- The two-layer bone/soft-tissue model with FSTT inversion. It waits for a CC0 skull template; FSTT appears only as plausibility guidance.
- Automatic retopology. The topology is fixed by design.
- Expression-rig generation beyond ARKit-named hooks, and only with RIG_ANIMATE.
- Video tracking and phone depth [gap: phone-video-depth-capture]. Video frames enter as stills in their own focal group (R1.9).
- Ear-specific reconstruction beyond low-weight landmarks and profile pins. Ears are left to guided sculpting [gap: ear-reconstruction-sculpting].
- Cloud processing, telemetry, URL or social importers, 1:N identity search, anonymisation claims, and our own encryption: we rely on OS-encrypted folders (ethics A3, A5, F17, F18).
- Child-specific priors by default. Minors require guardian consent, and child CV widening (R4.5) is opt-in.
