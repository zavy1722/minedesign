# Proposal: artist-in-the-loop photo → sculpt-ready head

*Design angle: UX-first. Date 2026-11-20. Builds on `face3d/` at commit 887c5e5 (42 tests passing).*

**How citations work.**
- `(topic badge)` names a note in `research/<area>/`; IDs such as CAM-3 or R4.1 point into `research/_raw/requirements_*.md`.
- Every 🧠 or ↔️ number is a **named, tunable default** whose badge appears in the add-on's expert view.
- **[gap: x]** marks a decision that waits on an unwritten gap note. None existed at writing time; each such decision is reversible.

---

## 1. Vision and the user journey

FaceBuilder sets the interaction bar: pins on any surface point, a live re-solve, and one camera per photo (facebuilder-blender 🧠). We rebuild that on open code and commercially safe data, and add three things it lacks:
- **We say what the photos actually measured.**
- **We never overwrite the artist's work.**
- **We finish in Sculpt Mode.**

Automation speeds the artist up but never decides alone: every automatic choice arrives as a suggestion card with *why*, *what changes* and *undo*.

**Principles**
- **P1 Live, then thorough.** Adding a photo or dragging a pin re-solves cameras and coarse shape within one frame budget (target ≤30 ms); slower stages refine in the background.
- **P2 Plain-language uncertainty.** Every number has a likely range and a basis: *measured from N photos*, *partly measured*, or *estimated from the template's average shape*.
- **P3 Non-destructive.** Original photos stay untouched, solves are immutable snapshots, and fit, asymmetry and sculpt sit on separate layers. A refit never touches the artist's delta.
- **P4 Flags, not corrections.** Nothing the photos support is pulled toward a norm (requirements_anatomy §6).
- **P5 Accessible by default.** Colour-blind-safe overlays, full keyboard operation, no automatic motion, and expert detail only when asked for.
- **P6 Consent first.** No stage runs without a consent record covering it (ethics §3).

**Journey:** 7–9 photos to a sculpt-ready head in about 20 minutes.

| # | Artist | System (live) | Artist sees |
|---|---|---|---|
| 0 | Consent wizard (self, subject or guardian) | `ConsentRecord`, scopes | "reconstruct: yes; texture: no" |
| 1 | Opens the **Shot card** | The 7-view core set: front, ±45°, ±90°, low, high (reference-photography-protocol 🧠) | Diagrams; "phone: 2–5× lens, 1.5–3 m" |
| 2 | Drops photos in | EXIF, orientation baked into working copies, lens grouping, quality gates (R1.4) | Per photo: an icon plus *Good*, *Usable with care* or *Texture only* |
| 3 | **Find landmarks**, or 6–10 manual pins | Helper job → PnP → joint solve | Cameras around the head; residual arrows |
| 4 | Reviews cards | Mirror, expression, close-camera and focal-observability tests | "Photo 4 looks mirrored (selfie?). Flipping lowers error 34 %. [Flip] [Keep] [Show me]" |
| 5 | Drags pins in any view | Live re-solve | Every view updates; coverage map; "next best photo" |
| 6 | **Refine** | Background stages B–D | Progress; the result swaps in, with undo |
| 7 | **Likeness review** | QA, measurements, held-out photo | Worst-first list; measured-vs-estimated map; flip and blur compare |
| 8 | **Hand off to sculpt** | Key stack, Multires copy, masks, cameras on markers | Sculpt Mode; ←/→ steps through photo cameras |
| 9 | Texture and export (optional) | Gated projection; provenance | Albedo and confidence maps, or an export blocked with its reasons |

---

## 2. Architecture

### 2.1 Layers

```
L4 face3d_blender/   GPL-3.0-or-later extension; UI, overlays, operators; sole bpy importer
L3 face3d/pipeline/  stages, live session, jobs-as-data, suggestion cards
L2 face3d/{solve,fit,texture,qa,guidance,handoff}/  numpy algorithms
L1 face3d/{geometry,mesh,model,io}/  primitives, shape spaces, landmark registry, formats
L0 face3d/project/   consent, licence taint, data classes, audit (bpy-free, ethics A2)
tools/  landmark helper (MediaPipe), template-pack builder, extension builder
```

- The engine imports only numpy, math, json and tomllib, uses relative imports, and is vendored into the extension at build time (blender A1).
- Engine code is MIT and the glue is GPL, so the extension as a whole is GPL (ethics A1).

### 2.2 Modules (exists / extend / new)

| Path | Status | Purpose |
|---|---|---|
| `face3d/geometry/{rotations,procrustes}.py`, `mesh/{reduced,sparse}.py`, `solve/triangulate.py` | exists | Primitives kept as is. Procrustes gains a reflection mode for symmetry-plane fitting and mirrored-source detection (R3.3, W2) |
| `face3d/geometry/camera.py` | extend | Add `from_blender_camera`, crop and canvas offsets (C5), and k1 only when f35 < 28 mm |
| `face3d/geometry/rbf.py` | extend | λᵢ = α·σᵢ² in normalised units (MM-8); sign bug already fixed in 0843516 |
| `face3d/solve/lm.py` | extend | Return the normal matrix; warm start τ = 1e-6; `time_budget_ms` |
| `face3d/solve/pnp.py` | extend | CAM-3 hypothesis set; pitch-flip and yaw-mirror restarts; cheirality |
| `face3d/solve/bundle.py` | extend | Free-point BA for 3D targets, fixed-camera triangulation and cross-checks. Adds anisotropic per-class σ, per-pair σ_sym and Huber 2σ with 4σ rejection |
| `face3d/solve/reconstruct.py` | extend | Tiered focal priors (wires `f_prior_log_sigma`), view-bin weights, mirror hook |
| `face3d/solve/{live,observability,expression,mirror}.py` | new | Reduced joint solver; posterior, k_r and next-best-view; neutral tagging and jaw hinge; flip test |
| `face3d/model/shape_space.py` | new | FMT-4 adapter: `TargetSpace` (MPFB2 CC0, default), `Flame2023OpenSpace` (user path), research spaces opt-in |
| `face3d/model/{landmarks,template_pack}.py`, `defaults.toml` | new | Registry (R2.1) and scheme adapters; pack loader with topology-hash refusal (INV-4); defaults stored as `{value, sigma, unit, badge, source}` |
| `face3d/fit/template.py`, `fit/silhouette.py` | extend | Barycentric embeddings (today a vertex index), regions, mirror map; normal residuals, hair hinge, region weights, grid nearest-neighbour search |
| `face3d/fit/{stages,refine}.py` | new | Stage schedule and gates (W1, R5.2); offsets with caps, edge-flow and det J gates |
| `face3d/mesh/core.py`, `mesh/laplacian.py` | extend | Topology hash and CSR faces (A7); per-vertex smoothness weights (R5.9) |
| `face3d/texture/{raster,project}.py` | new | UV G-buffer and z-buffer; weights, gains, blending, hole fill |
| `face3d/qa/{metrics,report,overlay_geom}.py` | new | Metrics; plain-language cards; overlay mapping that can be tested without Blender |
| `face3d/guidance/`, `face3d/handoff/keys.py` | new | Checklists, measurements and warnings, built from `research/data/*.json`; key-stack and rebase maths |
| `face3d/project/{schema,consent,licence,capture,audit}.py` | new | Project file, gates, taint, capture manifest and coverage, JSONL audit log |
| `face3d/io/exif.py`; `io/landmarks_json.py` | extend; new | DateTimeOriginal and crop suspicion; helper JSON reader (D1, FMT-1) |
| `face3d/synthetic.py`; `face3d/eval/` | extend; new | Procedural template pack and scenarios (mirrored, cropped, expressive, hair); point-to-triangle distance and NoW-style alignment (EV-1) |
| `face3d_blender/` | new | `blender_manifest.toml`, `bridge.py` (sole bpy↔numpy module), `compat.py`, `props.py`, `jobs.py`, `keymap.py`, `ops/`, `ui/{panels,overlays,palette}.py` |
| `tools/landmark_helper/`, `tools/template_pack/` | new | MediaPipe Tasks script that writes JSON; maintainer pack builder and annotation checks |

### 2.3 Data flow

1. **Ingest.** Photos → `capture.ingest`: EXIF, orientation bake, hash, gates, focal group.
2. **Landmarks.** Helper JSON and/or pins.
3. **Cameras and coarse shape.** Per-view `pnp`, then the `live` A-space solve, then `observability`. Artist pins loop back into `live`.
4. **Refine (background).** `stages` B–D: frozen-camera `bundle` → 3D targets → `reduced`/`silhouette`/`refine`.
5. **Check and hand off.** `qa` → `handoff.keys` → bridge → optional `texture` → export with provenance.

### 2.4 Data formats

**Project folder.** `<name>.face3d/` sits beside the `.blend`, which stores only its path. Purges act by data class (ethics 2.2).

```json
{"schema_version": "1.0", "consent_id": "…", "commercial_intent": false,
 "photos": [{"sha256": "…", "working_copy": "photos/p01.png", "orientation_baked": true, "crop": null,
   "focal_group": "Make|Model|Lens|f|W|H|still", "view_tag": "front", "rights_basis": "self_shot",
   "audit": {"status": "good", "flags": []}}],
 "pins": [{"photo": "…", "xy_px": [1012.5, 884.0], "surface": {"tri": 4411, "bary": [0.2, 0.5, 0.3]},
   "sigma_pct_iod": 0.75, "source": "user"}],
 "active_solve": "solves/0007", "template": {"topology_id": "mpfb2-hm08-head-v1", "topology_hash": "…"},
 "settings": {"rigidity": 0.5, "symmetry_mode": "assist"}, "licence_ledger": []}
```

Pins and edited landmarks are artist work. They persist under RECONSTRUCT consent, like camera solves ("project only", ethics 2.2). Raw detector output is a cache with `cache_ttl_days = 0`.

**Landmark scheme JSON** (`model/schemes/<scheme>.json`). It says what each detector index means and is independent of any mesh:

```json
{"scheme": "mediapipe_478", "n_points": 478, "image_convention": "px, top-left pixel corner, y down",
 "detector": {"model_sha256": "<pinned>", "licence": "Apache-2.0", "commercial_ok": null, "is_ml": true},
 "points": [{"i": 1, "abbr": "prn", "side": "mid", "tier": "A", "sigma_class": "anchor", "verified": false, "badge": "🧠"}],
 "contours": [{"id": "face_oval", "kind": "silhouette", "sigma_class": "oval", "indices": []}],
 "mirror_pairs": [[33, 263]], "z_policy": "ignore"}
```

An index with `verified: false` serves only as a generic contour point with inflated σ, never as an anatomical anchor (R2.4).

**Template pack** (`templates/<topology_id>/pack.json` plus `arrays.npz`, D5):

```json
{"topology_id": "mpfb2-hm08-head-v1", "topology_hash": "sha256(int32 CSR)", "n_vertices": "<measured>",
 "units": "mm", "frame": "head_FH", "source": {"name": "MPFB2 hm08", "version": "<pinned>", "sha256": "…", "licence": "CC0-1.0"},
 "arrays": ["head_to_hm08", "region_ids", "mirror", "w_smooth", "w_jaw", "feature_curves"],
 "shape_space": {"kind": "targets", "file": "targets.npz", "prior": {"sigma": 0.5, "bounds": [-1, 1]}},
 "embeddings": {"anatomical": "emb/anatomical.json", "mediapipe_478": "emb/mediapipe_478.json"}}
```

Each embedding row is `{landmark, tri, bary, annotator_spread_mm, verified_by}`.

**Solve result** (`solves/NNNN/result.json` plus `arrays.npz`, FMT-8 and D6). Solves are immutable, and *Revert* re-activates an older one. Each holds:
- Per-view cameras `{R, t, f, f_source, sigma_logf, observable}`, convention `opencv_px_corner`.
- β, θ_v and ψ_v; per-stage vertices.
- Per-vertex σ and region k_r.
- `scale_mode ∈ {measured, iris, ipd_prior, proportions_only}`.
- QA findings, the licence union and the consent ID.
- Versions and seed.

### 2.5 Coordinate conventions

| Space | Convention |
|---|---|
| Head | mm, float64; +x subject's left, +y up, +z out of the face; midsagittal origin; levelled to the template's FH (R1.1) |
| Camera | OpenCV; X_c = R·X + t (exists) |
| Image | px with origin at the top-left pixel *corner*, so pixel centres sit at i + 0.5; MediaPipe gives u = x_norm·W |
| Blender | Head and cameras share a parent empty with rotation R_x(+90°) and scale 0.001: engine (x, y, z) mm → Blender (x, −z, y) m, face toward −Y, `.L` = +X (A8). `to_blender_camera` exists (C4) |
| UV | Blender UV origin bottom-left; `img.pixels` rows run bottom-up; texel centres at (i + 0.5)/N |
| L/R | Always the subject's side; mirrored photos swap labels (R1.2) |

### 2.6 Assets: how we obtain and check them (no fabricated data)

**Template** [gap: open-template-head-kit]. The default is the MPFB2 hm08 base and its CC0 face targets. The licence is sourced (blender-face-addons 📄); the vertex counts are 🧠, so the builder measures them.
- `tools/template_pack/build.py` takes a pinned MPFB2/MakeHuman install and verifies its SHA-256.
- It cuts the head and neck but keeps `head_to_hm08`, so MPFB rigs and MakeTarget still work.
- It converts to mm in the head frame and writes the pack.
- If the face has fewer than 6k quads, it applies one Catmull–Clark level (W4).
- The pack is released as CC0 and fits the size budget (Q5).
- The Blender Studio Human Base Mesh (CC0 ✅) can be used as a delivery topology through a one-time embedding (W6).

**Anatomical embedding.**
- Two annotators place each registry landmark in a developer panel, working from the definitions in craniometric-landmarks.
- Accept a landmark if they agree within 1.0 mm (en, ex, ch, sn) or 2.5 mm (g′, zy′, go′), the bounds in R4.1; otherwise adjudicate.
- The annotators' spread is added to σ in quadrature.

**MediaPipe 478 → template** [gap: landmark-index-correspondence].
- Maintainers register the SHA-pinned Apache-2.0 canonical mesh to the template with our own NICP (MM-12), anchored on the verified landmarks, and take closest-point barycentrics.
- The table must pass three checks:
  - rendered labels agree;
  - mirror pairs land within 1.5 mm of mirror positions;
  - candidates from R2.4 fall within their σ.
- Only the derived table ships. If a CC0-only bundle may not include Apache-derived data (ethics C7), the add-on builds the table on first run.

**Priors** load from `research/data/<topic>.json` (R2.8) into `defaults.toml`.

**Tests** use a procedural pack from `synthetic.py`; tests that need real assets skip when the pack is absent.

---

## 3. Algorithms

### 3.1 Joint objective (live, A-space)

Parameters p = {ω_v, t_v} ∪ {ℓ_g = log f_g} ∪ β ∈ ℝᴷ ∪ {θ_v} ∪ {ψ_v}. A landmark is X_i(β) = X̄_i + B_iβ, with X̄_i = A_iT̄ and B_i = A_iS precomputed (MM-2).

E(p) = Σ_v w_v Σ_i ρ(‖L_vi⁻¹(π_v(X_i) − u_vi)‖) + E_contour + E_sil + E_pin + E_shape + E_sym + E_mid + E_cam + E_scale + E_canon

- **Landmark noise.** Σ_vi = (s_c·IOD_v)²·κ·I₂ (blender table P 🧠), retiring `sigma_px = 1.0` (C5).
  - s_c by class: anchors 1.5 %, contour normal 2.5 %, oval 4 %, iris 1 %, user pin 0.75 %.
  - κ = N/N_eff, with N_eff 60–100 for MediaPipe (craniometric-landmarks 🧠).
  - IOD is defined once, pupil to pupil.
- **Robust loss.** Huber with δ = 2, then 4σ rejection; flag a view if more than 15 % of its points are rejected (BA-5 🧠).
- **View weight.** w_v = 1/n_bin(v), in 15° bins, with any one view capped at 40 % (R1.8 🧠).
- **Solver.** LM (exists), with (JᵀWJ + μ·diag)δ = −JᵀWr and a multiplicative rotation update. P ≈ 110, so 2–5 warm iterations per drag event.

### 3.2 Camera initialisation

f_h = f35_h·√(W² + H²)/43.27 over the CAM-3 hypotheses {13, 24, 26, 35, 50, 77, 85, 120, 135, 200}. Each hypothesis gets an affine initialisation, LM over (ω, t, ℓ), and pitch-flip and yaw-mirror restarts. The best robust score with every z_c > 0 wins (camera-pose-solving 🧠).

**Focal priors** (CAM-6, R2.2 🧠):

| EXIF state | Prior on log f |
|---|---|
| Uncropped | σ 0.03–0.04 |
| Crop suspected | σ 0.08 |
| Phone, no EXIF | 26 mm, σ 0.25 |
| Nothing known | 50 mm, σ 0.6 |

The focal-group tie is 0.02.

**Other camera priors** (🧠):
- Distance: d ≈ f_px·63/IPD_px in near-frontal views, σ_log 0.06 (R1.5); or a tape measurement, σ 5 cm (R2.4). Bounds 0.25–10 m.
- Pose tags: yaw σ 10° (5° with floor marks), pitch 5° (8–10° for high and low shots), roll 3° (R2.7).

### 3.3 Observability

H = JᵀWJ + Λ_prior and Σ = H⁻¹. The β block already marginalises the cameras.

**Focal** (CAM-7, C2 🧠). Let σ_ℓ = √Σ_ℓℓ.
- Free focal only when σ_ℓ < 0.10 and yaw spans ≥60° (R2.3).
- If σ_ℓ > 0.8 × the prior σ: "Lens could not be measured from these photos; using EXIF."

**Perspective.** P = 100 mm/z, shown as "strong" above 0.1 and "nearly flat" below 0.03.

**Radial-slope test.** Regress the residuals on ρ_iδ_i. A slope implying more than 5 % magnification error raises "focal or distance may be wrong" (R2.8).

### 3.4 Shape prior and rigidity

E_shape = ½λ(r)·Σ(β_k/σ_β)², with λ(r) = 10^(2r−1). The rigidity slider r defaults to 0.5, the MAP setting (facebuilder-blender 🧠).

**`TargetSpace` (default).**
- σ_β = 0.5, with a soft barrier at [−1, 1] (table P 🧠).
- It is **semantic, not statistical**, so the UI says "estimated from the template's average shape", never "typical for people like the sitter".

**`Flame2023OpenSpace` (opt-in).**
- User-supplied under CC-BY-4.0; attribution goes into `ATTRIBUTION.txt`.
- β ~ N(0, 1), with K growing 20 → 50 (MM-3), and a flag when ‖β‖² > χ²_K(0.999), which is 86.7 at K = 50 (MM-5).

**Other priors.**
- Per-landmark σ arrays replace the scalar 8 mm (R4.1).
- Ratio priors are weak and log-scale (R4.3).
- With ≥2 views solved, a prior share above 20 % suggests lowering Rigidity, without changing it (R1.4 🧠).

### 3.5 Contours, silhouettes, hair

- **Sliding contours** (lids, lips, brows): r = n̂ᵀ(u_c − π(γ(s*)))/σ_n, re-associating s* on the projected feature curve γ every iteration; the tangent is free (ML 🧠).
- **Jaw and cheek oval.** γ is the current occluding contour inside the jaw and cheek mask. Beyond 60° yaw the silhouette term replaces it (BA-4, S1).
- **Silhouette.** r_m = n_mᵀ(π_v(x_s(m)) − o_m)/σ_sil, with σ_sil = 1–2 px, weighted up in profiles (S2 🧠). Gate: mean distance ≤1 % of face height on the unoccluded jaw and cheek, with IoU reported (S5).
- **Hair.** A one-sided hinge r_j = max(0, φ_v(π(x_j)) + m)/σ_h, where φ is the signed distance to the hair-plus-skin hull (positive outside) and m is 2 mm converted to pixels (W7). There is no silhouette term above the trichion (S3), and the cranium is gated to g–op 182–200 mm [gap: cranium-under-hair].
- **Masks** [gap: face-segmentation-contours]: a user lasso, then the MediaPipe oval, then an optional SAM 2 helper (Apache-2.0). Non-commercial parsers are never used.

### 3.6 Expression and mirror handling

**Neutral tagging.** A view counts as non-neutral if any of (anatomy §6 🧠):
- mouthSmile > 0.25;
- eyeBlink > 0.4;
- jawOpen > 0.08;
- browDown > 0.35.

With an expression basis, tagging also runs an EM over ‖ψ_v‖ for at most 3 rounds (BA-9).

**Default path: no expression basis.**
- Identity comes only from neutral views.
- Open-mouth views drop the lip points; squints drop the lid points (R3.7).
- A per-view jaw hinge, x′_j = x_j + ω_j(R(θ_v·a)(x_j − c) − (x_j − c)), absorbs small openings. Here c is 10–13 mm anterior to tragion (BA-1 🧠), the ω_j come from the pack, and θ_v ~ N(1.5°, 1°²).

**With a basis.** X_v = X(β) + Eψ_v, plus a neutral anchor ‖mean_N ψ_v‖/0.1. If no view is neutral, the add-on asks for one relaxed photo.

**Mirror test.**
- Compare E_v with E_v^flip (u → W − u, L/R swapped).
- Suggest flipping when the relative drop exceeds 0.2 (R1.6 🧠) **and** the absolute drop exceeds 2√(2n_v), the cost noise derived from χ².
- Otherwise report "can't tell (face too symmetric)".
- The add-on never flips automatically.

### 3.7 Warp schedule and asymmetry

**Stages** 0 → A → B → C → D (W1, R5.1). Gates (R5.2 🧠):
- Advance past A when landmark RMS < 4 % IOD and chamfer < 2–3 mm.
- Advance past B when RMS < 3 % IOD in every view, the held-out view included.
- In C and D, no landmark may move more than 0.5 mm.

**3D targets.** With cameras frozen, `bundle_adjust` triangulates against the model, using prior σ 8 mm in B and 3–4 mm in C (community §4). Silhouettes back-project at the vertex depth (exists). The result is X*_i with covariance Σ*_i.

**B: smooth global warp.** d(x) = Σ_j c_j·exp(−‖x − x_j‖²/2s²), with s = 30–40 mm. Solve (ΦᵀWΦ + μK)c = ΦᵀWd with W = Σ*⁻¹ (`ReducedDeformer`).

**C: local refinement.** min ‖diag(√w_s)·L·d‖²_M + Σ_c w_c‖x_c + d_c − p_c‖².
- Weights w_s (R5.9 🧠): ligaments ×3–5, lid margins ×3, lips ×0.3, forehead ×0.5; lids, lips, nostrils and ears ×5 (W3).
- |d| is capped at 3–5 mm unless ≥2 views agree (MM-10).
- Mesh gates: quad angles 30–150°, aspect ratio ≤4, det J > 0.2 (MM-11).

**D: final pass.** Only where ≥2 views agree.

**Cross-check.** If the triangulated X* and the model X(β) differ by more than 3σ, the card reads "the photos say more than the template can express – sculpt here", and the region is added to `f3d_sculpt_here`.

**Symmetry prior.** E_sym = Σ_p‖D_p⁻¹(X_l − M·X_r)‖², with per-pair σ (R4.2 🧠): canthi 0.7–1.0, alare 1–1.5, cheilion 1.5–2.0, gonion 2.5–3.0, ears 3–4 mm. Midline σ: n 0.75–1.0, prn 1.5–2.0, pg 2–3 mm.
- Full weight only where k_r < 0.5, otherwise ×0.25.
- The plane is re-fitted by weighted reflection Procrustes (R3.3).

**Asymmetry is kept, never averaged away.** S = ½(X + M·X_m) and `Asym` = X − S (R5.9). If the result is more symmetric than the photos (RMSD < 0.3 mm against an asymmetric photo set), it is flagged.

### 3.8 Detail refinement

- Shape goes down to wavelengths of about 5 mm. Anything finer becomes displacement, gated by resolution: pores ≤0.033 mm/px, fine lines ≤0.08, line positions ≤0.25 (R5.11 🧠).
- The default path adds **no** photometric detail. Instead it gives sculpt guides:
  - a best-view projection stencil for each region;
  - crease curves from image edges that agree across views (each must reproject within 2σ in ≥2 views);
  - the `f3d_confidence` attribute.
- Optional SH9 refinement (OPT-1: ±2.5 mm clamp, 6 mm high-pass) is labelled *estimated*.

### 3.9 Texture projection

**Gates.** TEXTURE consent, a known rights basis, and reprojection error ≤1.5 px median and ≤3 px max (T2, ethics §3).

1. **Visibility.** Texel centres give p_t and n_t. Per-view z-buffers run at 1–2k px, with vis = [z_v(p_t) ≤ zbuf + ε] and ε = max(1 mm, 2σ_geom) (TEX-1).
2. **View weights.** w = vis·cos²θ·fade(60°→75°)·footprint·edge (TEX-2 ↔️).
3. **Exposure gains.** Fit log I_v = log g_v + log a with Σ log g_v = 0 (TEX-3). Directional-light views get a gain only (R7.2).
4. **Blending** (`two_band`). The low band is a weighted mean after a 3 mm UV-space Gaussian; the high band comes from the highest-weight view (TEX-4).
5. **Hole filling.** Holes ≤5 mm fill harmonically. Mirroring is allowed for the low band only, from sources with weight ≥0.3·w_max; detail is never mirrored (TEX-5).
6. **Outputs.** Linear albedo, a confidence map and the per-texel view index. Without a chart, the result is labelled "absolute colour unknown" (TEX-6).

### 3.10 Capture coaching: next best photo

For each candidate c from the shot list (yaw {0, ±20, ±45, ±90}, elevation {−25, 0, +25}, 1.75 m, 77 mm-eq):
1. Predict J_c at the current fit.
2. Marginalise the candidate's own pose by Schur complement: H′_ββ = H_ββ + J_βᵀWJ_β − J_βᵀWJ_p(J_pᵀWJ_p)⁻¹J_pᵀWJ_β.
3. Score Δ_c = Σ_r w_r[tr_rΣ − tr_rΣ′_c], with tr_r(Σ) = Σ_{j∈r} tr(S_jΣ_ββS_jᵀ). The perceptual weights w_r are lids 1.0, brows 0.9, lips 0.8, nose 0.7 … ears 0.1–0.2 (face-perception-likeness 🧠).
4. Show the best candidate as one sentence, for example "Next: left profile, eye height, 1.5–2 m".

Nose and chin projection count as measured only with a front view plus a view at |yaw| ≥ 60° (R5.9).

### 3.11 QA metrics in plain language

k_r = 1 − tr_rΣ_post/tr_rΣ_prior measures how much of region r the photos determined.

| Metric | The artist sees | Threshold (source) |
|---|---|---|
| k_r | **Measured** / **Partly measured** / **Estimated** | ≥0.8 / 0.5–0.8 / <0.5 (0.8 from anatomy §6 🧠; 0.5 design) |
| Per-vertex 2σ | "likely within ±X mm" | linearised and calibrated (§5.2) |
| Leave-one-view-out (LOVO) | "This photo disagrees with the others" | held-out error > 2× in-sample (camera-pose-solving 🧠) |
| ‖β‖² < K − 2√(2K) | "Pulled toward average" | R5.8 🧠 |
| Mirror RMSD | "Too symmetric" / "Unusually asymmetric – check pose" | <0.3 / >1.5 mm 🧠 |
| IPD, g–op, head breadth | "Scale looks wrong" | 55–72 / 182–200 / 140–160 mm 🧠 |
| Scale references | "Your measurements disagree" | >1 % (BA-10) |
| Interior fits, contour doesn't | "Lens or distance wrong, not the face" | SIL-3 🧠 |
| det J ≤ 0.2 | "Surface folded – raise Rigidity" | MM-11 |

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
```

**Packaging.** No wheels ship, so one zip serves every platform and Blender supplies NumPy. `network` is declared only once a consented downloader exists (ethics A3).

**Version floor.** `blender_version_min` names only what CI tests (packaging ↔️). The engine itself runs on Python 3.11 and 3.13 with NumPy 1.26 or 2.x (A4).

**Landmark detection, three routes.**
- **Path A:** the helper runs in a venv the user creates; Blender never runs pip, and the helper writes JSON.
- **Path B (optional):** a build split by platform with onnxruntime.
- **Always available:** manual pins plus imported JSON, with no download at all (ethics A4).

### 4.2 Panels: a guided rail

The **Face3D** sidebar tab holds:
- **Guide.** The steps are Consent → Photos → Check → Landmarks → Cameras → Shape → Review → Sculpt → Texture → Share. Each shows an icon and a word (Done, Needs attention, Not started), one primary button, and a *Why?* link.
- **Photos.** Status, lens group, estimated distance, and suggestion cards.
- **Solve.** Rigidity; Symmetry (assist, prior or enforce); Expressions (off, jaw-only or basis); per-group focal mode; *Refine*; *Revert to solve #n*.
- **Likeness.** Findings worst first, the measurement panel, the coverage map and the next best photo.
- **Sculpt.** Hand-off, rebase, masks.
- **Privacy.** Scopes, retention clocks, *Prepare for sharing*, *Purge*.
- **Expert** toggle. Reveals σ, %IOD, χ², badges and the solver configuration.

### 4.3 Operators and keymap

Every operator uses REGISTER and UNDO, except the modal ones. All keys can be rebound.

| Operator | Key (camera view) | Notes |
|---|---|---|
| `face3d.photos_add` | — | runs ingest and gates |
| `face3d.landmarks_detect` / `_import` | — | background job / JSON |
| `face3d.view_next` / `_prev` | PageDown / PageUp | also bound to timeline markers |
| `face3d.pin_tool` (modal) | P | drag runs the live solve. Tab/Shift-Tab cycles pins. Arrow keys nudge by 1 px (×10 with Shift, ×0.1 with Ctrl). Del removes, Enter commits, Esc cancels |
| `face3d.solve_refine` / `_cancel` | Ctrl-R / Esc | stages B–D |
| `face3d.accept_card` / `_dismiss_card` | Ctrl-Enter / Ctrl-Backspace | acts on the focused card |
| `face3d.compare_flip` (hold) | F | photo ↔ model while held |
| `face3d.compare_blur` / `_grey` / `_edges` | B / G / E | R8.1 aids |
| `face3d.overlay_toggle`, `face3d.shortcuts` | H, ? | |
| `face3d.handoff_sculpt`, `rebase_sculpt`, `texture_project`, `report_export`, `prepare_for_sharing`, `purge` | — | §4.6; gated; HTML or text report; ethics F9 |

### 4.4 Overlays and accessibility

**Drawing.** A `gpu` POST_PIXEL handler draws the overlays (reference-camera-setup 🧠). The coordinate mapping lives in `qa/overlay_geom.py`, so it can be unit-tested outside Blender.

**Shape before colour.**

| Element | Glyph |
|---|---|
| Observed landmark | hollow ring |
| Model landmark | filled dot |
| Residual | line |
| Pin | diamond |
| Uncertainty | 2σ ellipse |
| Photo contour | dashed line |
| Model silhouette | solid line |

Every glyph gets a 1 px dark halo so it stays visible on any photo.

**Palettes** (`ui/palette.py`):
- Categorical: Okabe–Ito (#0072B2, #E69F00, #56B4E9, #D55E00).
- Residual bands: blue → orange → vermillion, each band labelled.
- The confidence map uses a luminance ramp.
- *Monochrome* and *High contrast* modes are available.
- Red against green never carries a meaning on its own.
- The palette choice is our own design decision [gap: guided-workflow-accessibility].

**Prior-driven regions** can be shown as a face-set mask, which needs no colour.

**Size and motion.**
- Glyph sizes follow `ui_scale` and `ui_line_width`.
- The flip compare is hold-to-view. It replaces R8.1's 3 Hz blink GIF, because 3 flashes per second is the usual photosensitivity limit 🧠.

**Language.** Strings avoid jargon; a glossary sits behind *Why?*, and everything passes through `bpy.app.translations`. Blender has no screen reader, so every finding also goes to the Info log and the exported report.

### 4.5 Undo, history, background jobs

**Writing to the mesh.**
- Read with `foreach_get`, convert float32 → float64 once, write back with `foreach_set` and `mesh.update()` (A3, K1, K4).
- Writes happen in OBJECT mode, with the previous mode restored.
- Refuse on a topology-hash mismatch or while in Edit Mode.

**Live pin drag.**
- The preview goes to a muted `f3d_live` key, written from a timer, so it stays off the undo stack.
- Releasing the pin pushes one `ed.undo_push("Move pin")`.
- Pins are PropertyGroups, so undo restores them. An `undo_post` handler then re-runs the live solve, and IDs are re-fetched by name (A5).

**Background jobs.**
- Short solves run in a thread on copied arrays.
- Refine and texture run as a `sys.executable -I` subprocess exchanging `.npz` files, so a crash cannot take Blender down.
- Results are applied by a timer every 0.05–0.1 s, with at most 10–20 ms of work per tick. Esc cancels.
- Under `blender -b` everything runs synchronously.

### 4.6 Shape keys and Multires hand-off

**Key stack** (K2, SK-1):

| Key | Contents |
|---|---|
| `Basis` | template mean |
| `ID_fit` | symmetric fit S; `slider_max` 1.5, where values above 1 are a caricature preview (R5.8 ↔️) |
| `Asym` | X − S |
| `artist` | the artist's sculpt |
| `stage_A`…`stage_D` | diagnostics, muted |

Per-photo expression keys are written only with RIG_ANIMATE consent (ethics F4).

**Rebase after a refit.** new `artist` = old `artist` + (new `ID_fit` − old `ID_fit`). Python writes to `Basis` add the change Δ to every dependent key (K3).

**Sculpt copy.**
- Bake the key mix and clear the keys, then add Multires L2 (likeness) and L3 (detail) (SK-3).
- The fit snapshot stays as a hidden object.
- Later refits go through `multires_reshape` from a subdivided copy (K5). Whether detail follows base edits is unverified (blender Q4); a test scene guards it, and the fallback is a new sculpt copy.

**Also written.**
- 15–25 region vertex groups and face sets.
- `f3d_confidence` and `f3d_sculpt_here` masks, feathered with σ 2 mm (W5).
- Brow and hairline curves.
- Rigid 24 mm eyes (R6.4).
- One locked camera per photo, with a background image (Front, α 0.4) and a timeline marker, so ←/→ steps through photos. "Lock Camera to View" is off (sculpting-likeness-workflow 🧠).

**Feeding sculpt edits back.** A painted sculpt mask m becomes data weight (1 − m) plus a pin term at σ 0.2 mm (W5).

**Rig-ready.** Through `head_to_hm08` the head round-trips as an MPFB `.target`, so it works with MPFB and Rigify rigs and with ARKit-named expression tools.

### 4.7 From anatomy research to in-app guidance

- **Capture checklist** (R1.4, reference-photography-protocol): hair off the ears, glasses removed 10–15 min earlier, a fixed gaze mark, the camera at eye height, ≥1.5 m away, the phone's 2–5× lens, no portrait or beauty modes. Items tick automatically as the gates confirm them.
- **Likeness checklist,** in perceptual rank order: lids → brows → lips → eye spacing → nose → thirds → jaw and hair → age → ears (face-perception-likeness 🧠). Each item opens its best camera.
- **Measurement panel.** Shows en–en, ex–ex, al–al, ch–ch, n–sn, sn–sto, n–gn, zy–zy, go–go, g–op, ear length, and the nasolabial, gonial and cervicomental angles.
  - Each reads as value ± 2σ with its measuredness.
  - A population z-score appears **only when method and landmark variant match** (R1.3, R2.2). If |z| > 2.5 and no photo sees the region, the panel adds a note but never a correction (R8.2).
  - Caliper entries become constraints: E_cal = Σ((‖X_a − X_b‖ − d − o)/σ)² (R5.7).
- **Warning catalogue** (`guidance/warnings.toml`). Each entry has a title, a one-line why, actions, its source and its badge. Example: "Close camera (~0.45 m): noses look ~20 % larger here (100 mm/d). [Use for texture only] [Keep]". The ordering hinges in R5.2 appear as warnings too.
- **Personal metadata.** Age, sex prior and BMI are optional and explained, never inferred. Ancestry is never asked (R2.7, R7.4).

---

## 5. Validation and QA

### 5.1 Automated synthetic tests (pytest, CPython, no Blender)

| Area | What is checked |
|---|---|
| Q1 suite | Noiseless reprojection < 1e-6 px; with σ = 1 px, RMS ≈ σ√(1 − p/n), failing above 1.2σ |
| EV-5 sweeps (z 0.25–5 m, f35 13–200 mm) | Focal error < 5 % and rotation < 2° when views span ≥60° (R8.4 🧠); "not observable" reported for frontal views at ≥2 m |
| Live solver | Within 1e-3 of the batch solve; latency is recorded, not asserted |
| Behaviour | Mirror detection, expression tagging, contour sliding under yaw, hair hinge (never pulls inward), stage gates, the 0.5 mm landmark freeze in C and D, fold gates |
| Hand-off | Rebase preserves `artist − ID_fit` to 1e-9; Basis-Δ propagation; topology refusal |
| Texture | TEX-8: gains within 2 %, no colour leaking onto occluded texels |
| Policy | Consent gates; licence taint computed as an AND; a socket guard (ethics A7); an AST check that no `bpy` import exists under `face3d/` |
| Packaging | `tomllib` manifest lint (tagline ≤64 characters with no trailing period; SPDX identifiers; permission wording); an SPDX row for every bundled file |

Blender smoke scripts (`blender -b --factory-startup --python-exit-code 1`, Q3) run in an optional external CI.

### 5.2 Honest uncertainty

**Calibration.** Across 200 seeded subjects, the fraction of errors that fall inside the displayed 2σ must lie in [0.90, 0.98]. Otherwise the ranges are inflated by the measured factor, and the report says so.

**Report labels.**
- Each report carries its `scale_mode`.
- It reads "not validated against a scan" until EV-1 has compared it with one.
- No accuracy is claimed finer than the capture method allows (Q4).
- A footer counts the active 🧠 defaults.

### 5.3 Likeness checks shown to the artist

- **Overlays.** A camera-matched overlay with an opacity slider, plus silhouette, edge, hold-to-flip, blur, greyscale and thumbnail modes (R8.1). The blur uses σ = 3 % of face width, which keeps the 8–16 cycles-per-face-width band that carries identity (face-perception-likeness 📄).
- **Held-out photo.** The artist picks one photo the fit never sees; its residuals give an honest score.
- **Worst-first residuals,** grouped by perceptual rank.
- **Familiar-viewer review sheet.** A grid of each photo beside its camera-matched render, plus 5 questions, covered by the consent scope. People who don't know the sitter, the artist included, judge likeness poorly 🧠.
- **Caricature preview.** S(α) = M + α(S − M) for α 0.9–1.2, shown in preview only (↔️).
- **Identity-embedding scores** are off by default: they need the IDENTITY_CHECK scope, run 1:1, stay in memory only, and never use non-commercial weights.

---

## 6. Milestones

Each milestone ships on its own and is accepted by tests that run here.

| M | Ships | Acceptance |
|---|---|---|
| **M1 Honest camera solve** | Extensions to pnp, reconstruct and bundle; observability, mirror and report modules; CLI `python -m face3d solve project.json` | Q1 and EV-5 pass. Mirror flagged in ≥95 % of seeded mirrored views (asymmetry SD ≥1 mm), with ≤2 % false flips. BA calibration in [0.90, 0.98] |
| **M2 Project, consent, capture** | `project/*`, gates, coverage, next-best-view, helper and JSON reader | Gate-matrix tests (ethics F1–F20 where applicable); socket guard; profile is the top suggestion for frontal-only sets in ≥90 % of seeds |
| **M3 Template pack + staged fit** | model, stages and refine modules; silhouette extensions; pack builder tested on a fixture OBJ; synthetic pack | In-space subjects: face RMS ≤0.5 mm noiseless and ≤1.5 mm at 2.5 % IOD noise, 7 views. Out-of-space subjects: C cuts RMS ≥30 % against A. Profile error at prn and pg ≤1–1.5 mm (SIL-3) |
| **M4 Extension MVP** | Manifest, bridge, cameras, landmark import, background Refine, `ID_fit` + `Asym` keys, static overlays, report | Manifest lint; bpy-isolation AST check; overlay and key-maths tests; camera round trip within 1e-6·s |
| **M5 Live pins + guided rail** | Live solver, modal pin tool, undo, keymap, palettes, cards, checklists, measurements | Live within 1e-3 of batch. Every step reachable by keyboard. Categorical palette pairs differ by ΔE ≥ 20 under simulated deutan, protan and tritan vision (our own target) |
| **M6 Sculpt hand-off** | `handoff/keys`, sculpt copy, rebase, masks, curves, markers, likeness aids | Rebase identity to 1e-9; LOVO and held-out metrics; caricature never exported unless the user sets it |
| **M7 Texture + sharing** | `texture/*`, gates, provenance, *Prepare for sharing* | TEX-8; UV gates (T5); export blocked on tainted components, with the offending items listed |
| **M8 Opt-in statistical spaces** | FLAME 2023 Open adapter, research adapters (with warnings), expression basis if FLAME 2023 Open has one (C6) | χ² gates; refusal on `basis_sha256` mismatch; the default path still passes with the CC0 pack alone (L2) |

---

## 7. Risks and deliberate omissions

**Risks**
1. **Uncalibrated defaults.** About 72 % of anatomy claims, and most σ values and gates, are 🧠. Mitigation: named defaults, the calibration test, the held-out photo, and a real-scan set later [gap: validation-test-bed, metric-3d-landmark-reference].
2. **The default shape space is semantic, not statistical.** It may over-flex or shrink. Mitigation: the rigidity slider, the shrinkage and χ² cards, the free-point cross-check, and the M8 statistical space.
3. **Template quality.** hm08's loops and vertex counts are unverified, so it may need subdivision. The pack is a plug-in, so this choice is reversible [gap: open-template-head-kit].
4. **Annotation bottleneck.** Every landmark table needs two annotators. Unverified entries are down-weighted [gap: landmark-index-correspondence].
5. **Helper friction.** Setting up a venv is hard for non-experts. Manual pins and JSON import always work. The licence of the MediaPipe weights is ↔️.
6. **Live latency.** If Python is too slow, use fewer iterations, fewer contour points, or a 100-point MediaPipe subset.
7. **Unverified Blender behaviour.** Multires rebase semantics in 5.x are unconfirmed (Q4).
8. **Policy and law may change.** Extension download rules (C8), Apache-derived data in a CC0 bundle (C7), biometric law, and AI Act Art. 50.
9. **Phone processing.** Phone pipelines may alter face geometry [gap: smartphone-camera-pipeline]. Mitigation: lens grouping, retouch flags, robust per-view σ.

**Deliberately left out**
- **Reconstruction shortcuts:** single-image neural regression and AI meshes as identity sources (the research caps them at 25 %, OPT-2), neural or generative detail, and photometric detail by default.
- **Features beyond the head shape:** hair strands; teeth and tongue; expression rigs beyond ARKit-named hooks, which also need RIG_ANIMATE.
- **Modelling extensions:** the bone/soft-tissue two-layer model, which waits for a CC0 skull (FSTT is used as guidance only), and auto-retopology, since topology is fixed by design.
- **Other capture sources:**
  - Video and phone depth [gap: phone-video-depth-capture]; video frames are treated as stills in their own focal group (R1.9).
  - Ear-specific reconstruction [gap: ear-reconstruction-sculpting]; ears get low-weight landmarks and profile pins, then guided sculpting.
- **Data and privacy:** cloud processing, telemetry, URL importers, 1:N search, anonymisation claims, and home-made encryption (we rely on OS-encrypted folders).
- **Children:** child-specific priors by default. Minors need guardian consent, and widening for children (R4.5) is opt-in.
