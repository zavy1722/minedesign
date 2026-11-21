# Face3D: final design for the engine and the Blender extension

*Chief-architect synthesis, 2026-11-20. Baseline code: `face3d/` at 41179a3 (42 tests passing). Inputs: `docs/design/proposal-{accuracy,artist,robustness}.md`, `research/_raw/requirements_*.md`, `research/data/*.json`, and the two judges' verdicts. This document replaces the three proposals as the reference for implementation. Work packages (WP-01 … WP-24) are defined in the workflow output and cited here.*

**Badges.** ✅ verified (≥ 2 sources) · 📄 single source · 🧠 expert knowledge, provisional · ↔️ contested · 🆕 introduced by this design, uncalibrated · 🔢 checked numerically during this review (one-line numpy check; reproduced in the WP acceptance tests).
**Citation keys.** [Acc §x], [Art §x], [Rob §x] = the proposals; J1/J2 = the judges; digest rule IDs: `rec` CAM/BA/MM/SIL/SK/TEX/EV, `bl` A/D/C/W/S/K/T/L/Q, `anat` R, `com` R, `eth` A/F. Notes are cited by file name (e.g. *validation-test-bed*).

Every 🧠, ↔️ and 🆕 number below ships as a named default in `face3d/core/defaults.toml`, carrying its badge and source, and is recalibrated in M7 (§8). None is a hard-coded constant.

---

## 0. Summary

We ship **robustness's base plan** (extend the existing `bundle.py` and warp code; compute evidence tiers; fault-injection matrix) with **accuracy's solver maths** (inverse-depth cameras, explicit log-scale, gauge projection, sub-vertex contours, limit-surface cages, LOVO γ) and **artist's product layer** (σ in mm by landmark kind, the user-pin model, the key stack with exact rebase, the guided rail, accessible overlays, the Schur-marginalised next-best photo). Five defects are fixed first: tangential silhouette drift, the 1 px `sigma_px` default, the implicit scale, the definition-bias floor, and diagonal-only covariance. Each fix gets a regression test, and a committed baseline scorecard of today's engine is recorded before any of them lands.

The engine stays numpy-only and bpy-free. The Blender extension stores no wheels, needs no network, bundles CC0 assets only, and runs every heavy step in a `sys.executable -I launcher.py job_dir` subprocess. Everything in M1–M6 is implementable and testable in this sandbox (Python 3.13, numpy, Pillow, pytest; no Blender, no MediaPipe). Blender code is verified with AST checks and a bpy stub. The default template is a procedurally generated CC0 head built by our own code. Two milestones need the real world (M3b: real template and MediaPipe index map; M7: calibration tiers 2–4). They are delivered as tools, scripts and docs that are tested on synthetic inputs here.

---

## 1. Decisions

| # | Decision | Rationale | Sources |
|---|---|---|---|
| D-01 | **One landmark solver**: extend `solve/bundle.py`. A low-dimensional *shape model* (free points or a linear basis) is a pluggable parameterisation of the same solver, not a second solver. | Keeps the 42 tests meaningful; avoids a parallel bundle/joint pair. | J1 graft [Rob 2.1, 3.5]; J1 conflict "solver architecture" |
| D-02 | **Inverse-depth cameras inside the solver**: u = c + s((RX)ₓᵧ + τ)/(1 + ρ(RX)_z), f = s/ρ, t = (τ, 1/ρ). ρ itself is the parameter, bounded to [0.1, 4] m⁻¹ (0.25–10 m). Convert to `Camera` at the boundary. | Exact (5e-13 px, J1/J2); dolly-zoom becomes one coordinate; the weak-perspective limit ρ→0 stays regular, which fails under log ρ. | [Acc 3.2]; rec CAM-4; bl C6; J1/J2 fatal flaw on log ρ |
| D-03 | **Explicit global log-scale ζ** with the population prior N(0, 0.045²) as the *only* population size source; the factor prior's `size` factor is removed when ζ is active. Caliper or card overrides; iris HVID 11.8 ± 0.6 mm only at ≥ 20 px, sharp limbus, no glasses. Report scale mode and σ. | Today's 8 mm iid prior fixes scale implicitly at ≈2 % and is 2–4× overconfident. Exactly one population source avoids double counting. | [Acc 3.4, 3.7]; *validation-test-bed* T5 🧠; anat R3.4; J1/J2 scale conflict |
| D-04 | **Default landmark prior = the 44-landmark, 18-factor covariance** from `metric-3d-landmark-reference.json`: E = ½rᵀ(κ²S)⁻¹r, S = LLᵀ + R, solved by Woodbury. Defaults: unknown-population κ 1.5 (2.5 on al/ac/en x), sex mixture, an extra 6 mm face-depth factor, widened tragion residuals. Never conditioned on ancestry. | It is the only calibrated covariance in the library. hm08/MPFB TargetSpace is under-determined, non-convex and licence-disputed. | [Rob 3.7]; J1/J2; anat R4.4, R5.5, R7.4 |
| D-05 | **σ stored in mm by landmark kind** (normal/tangent), converted per view at each point's depth: σ_px = (f/z_i)·σ_mm. | Removes the 63-vs-88 mm IOD ambiguity (1.4×). | [Art 3.1]; bl §4 header; J1/J2 |
| D-06 | **Definition bias is a per-landmark offset shared across views**, entering the reported covariance as a floor σ_def² (0.5–2 mm by kind). It is never added to per-observation variance. | Per-observation σ_def averages down as 1/√views (J2 checked: 0.82→0.47 mm vs 1.15→1.05 shared). | J2 fatal flaw [Art 3.1]; *validation-test-bed* R4 (NEES 3.63) |
| D-07 | Per-view robust noise scale ν_v² = clip(median‖Σ^-½r‖²/1.386, 1, 9); flag ν_v > 2. View weights 1/n_bin, no view > 40 % of the information. | 1.386 = median χ²₂ 🔢. | [Rob 3.2]; com R1.8 |
| D-08 | Robust schedule: Huber δ = 2σ → one Tukey round (c 4.685) → reject at 3.035σ (1 % false alarm in 2D 🔢) → re-solve. Reject a view above its 99 % χ² bound; flag a view with > 15 % rejected. | Calibrated cut-off; rec BA-5's 4σ is looser than the 2D 1 % point. | [Art 3.1]; [Rob 3.5]; J1 |
| D-09 | User pins: σ² = σ_class² (mm, at depth) + σ_motor² (1 screen px at placement zoom); novice crisp 1.2 mm is the default. | 0.75 % IOD over-weights novices 3–30×. | [Art 3.1, 4.2]; bl §4 GW |
| D-10 | **Mirror test returns {Δ, g, margin, decision}**; `undetermined` when the predicted gap g < 4, `unverifiable` for all-selfie sets. A flip is suggested only when Δ passes 10 % (front camera) / 20 % (other) **and** the absolute gap exceeds 2√(2n_v). **Never flipped silently**; the CLI applies a flip only with an explicit flag, logged and reversible. | Robustness's auto-flip mirrors moles and partings silently. | [Rob 3.4]; [Art 3.6]; J1/J2 fatal flaw |
| D-11 | Multi-start PnP over 10 f35 hypotheses × {affine, pitch-flip, yaw-mirror} with cheirality; raise `C-TWIN` when two poses > 10° apart score within 20 %. First-matching-rule focal ladder. | Today's 7 hypotheses miss 26/77/120 mm. | rec CAM-3, CAM-6; [Rob 3.3] |
| D-12 | Off-axis faces: **per-view model selection** between rectilinear (rotation homography, f′ = f), stereographic face-warp correction (local virtual camera, f′ = f·sec²(θ/2)) and k₁ ~ N(0, 0.02²); fall back to σ ×3 when ambiguous. | sec²(θ/2) is exact only for stereographic warps (J2: 1.099 isotropic at 35° vs 1.49/1.22 for rectilinear 🔢). | [Art 3.2]; [Rob 3.1]; J2 conflict |
| D-13 | Contours: `ContourObs` kinds {hard, outer_bound, inner_bound}, normal-only residuals, sub-vertex zero crossing, truncated backward term, distance transform, gates at 0.15·IOD_px and 40° normal mismatch, Viterbi edge snap as the zero-download contour source. | Fixes tangential drift; vertex contours carry half-edge bias. | [Acc 3.8]; [Rob 3.8]; [Art 3.5] |
| D-14 | Expression handled as **covariance inflation** PΣ_exprPᵀ sized by robustness's class multipliers; tags are relative to the subject's own minimum, with no-score fallbacks; jaw hinge 10–13 mm anterior to tragion, N(1.5°, 1°²) on neutral views, σ 3° expressive, bounded [0°, 30°]. A smile moving neutral identity ≥ 0.3 mm fails CI. | First-order marginalisation only down-weights; the 0.3 mm gate stays hard. | [Acc 3.6]; [Rob 3.6]; J1 |
| D-15 | Symmetry is **evidence-gated**: full per-pair σ only where the region is prior-driven or unobserved, weight ×0.25 elsewhere; plane re-fitted by reflection Procrustes; output never symmetrised; `Asym` exported as its own key. | anat R4.2 assist mode; R3.3. | [Art 3.7]; J1/J2 |
| D-16 | **Claims ledger** with four states (measured / constrained / prior-driven / unobserved), computed at prior weight 1 with hard coverage rules and an absolute σ ≤ region-target condition. σ_rep² = σ_post²·max(1, γ², χ²_red) + σ_def². *Deviation recorded at M6 (WP-23, FU-02 option (i)): the pipeline ships the factor max(γ², min(1, χ²_red/κ), χ²_red, 0.5) instead; see §4.13.* | The rigidity slider and likeness mode must not change labels. | [Rob 3.10]; [Acc 3.11]; J1/J2 |
| D-17 | Tiers S/A/B/C (*metric / iris-scaled / proportions only / blockout*) are computed from evidence; T0–T3 are capture coaching only. Every report says "not validated against a scan" until M7 runs. | [Rob 1]; [Art 5.2] | J1/J2 |
| D-18 | **Shrinkage gate fixed**: test T = x̂ᵀS⁻¹x̂ against its *predictive* distribution (mean k_eff = Σλ_i, λ_i = eig(I − S^-½Σ_postS^-½)), not χ²_K. | The old gate fired on 85 % of faces drawn from the prior itself 🔢; the new gate fires at 0.8 % and detects 10× over-shrinkage 93 % 🔢. | J1 fatal flaw [all] |
| D-19 | Next-best photo: candidate pose Schur-marginalised, H′ = H + J_cᵀWJ_c − J_cᵀWJ_p(J_pᵀWJ_p + Λ_p)⁻¹J_pᵀWJ_c, perceptual region weights, user's own lens and distance. | Accuracy's gain treats the new pose as known. | [Art 3.10]; J1/J2 |
| D-20 | Solve in the **template gauge**; Frankfort levelling is a presentation transform. | Tragion and orbitale are poorly observed. | [Acc 2.5]; J1 |
| D-21 | When the delivery is Multires, fit the cage through **Catmull–Clark limit stencils**. | Avoids 0.1–0.4 mm shrink (bl W4). | [Acc 3.4, 4.5] |
| D-22 | Key stack: Basis = template, `ID_fit`, `Asym` and `artist` relative to `ID_fit`; exact rebase new artist = old artist + (new ID_fit − old ID_fit); immutable solves with Revert. | bl K2/K3 | [Art 4.6] |
| D-23 | **Pixels reach the engine only as decoded arrays**: the bridge decodes with `bpy.data.images` and writes float32 `.npy` working copies; outside Blender, the helper or a stdlib PNG reader supplies them; engine tests use synthetic arrays. | numpy cannot decode JPEG/HEIC. | J1/J2 fatal flaw [all] |
| D-24 | Jobs launch as `[sys.executable, "-I", launcher.py, job_dir]`; the launcher inserts its own directory into `sys.path`. | `-I` implies `-P` since 3.11, so `-m pkg` fails (checked here on 3.13 🔢). | [Rob 4]; J1 fatal flaw [Acc 4.4] |
| D-25 | Raw detector landmarks are a session cache (`cache_ttl_days = 0`); pins persist as the artist's work under RECONSTRUCT; a logged, consent-scoped opt-in may keep the cache. | eth §2.2; BIPA/GDPR. | [Art 2.4]; J2 conflict |
| D-26 | Tests never commit third-party biometric geometry: fixtures are synthetic, CC0, or consented, and real-person results are aggregate only. | eth A8, §2.2. | J1/J2 fatal flaw [Rob 5.4] |
| D-27 | Texture is never mirrored by default; low-band mirror fill is an explicit, provenance-marked option. Dense NCC and shading detail are off; sculpt guides are the default detail output. | anat R5.11; J1 conflict | [Rob 3.11]; [Art 3.8] |
| D-28 | Store build: no wheels, no network permission, CC0 assets only, GPL-3.0-or-later package. Detection comes from the user's-Python helper, JSON import or pins. The `.task` model is always a user-supplied, SHA-256-pinned path. | bl L1, L6; eth A3, A4, A6. | J1/J2 |
| D-29 | Extension id **`face3d_likeness`**, name "Face3D Likeness", tagline "Fit a sculpt-ready head to consented photos" (43 characters). Ids are permanent. | Two proposals agree. | J2 conflict |
| D-30 | Measure first: M1 = test bed + gauge-projected metrics + committed baseline + the cheap camera fixes + the five defect fixes. Test subjects are generated **independently of the fitted prior** (no inverse crime). | [Acc M1]; [Rob M1]; [Acc 5.1]; J1 | J1/J2 |
| D-31 | Ears are silhouette-only and labelled prior-driven; the cranium vault model, hinged ears, live solver, FLAME adapter and dense NCC are deferred (§10). | No CC0 ear keys; feasibility. | J2 conflict "Ears" |

---

## 2. Architecture

### 2.1 Invariants

1. **Engine (`face3d/`)** imports only `numpy` and the standard library (`math`, `json`, `struct`, `zlib`, `hashlib`, `tomllib`, `dataclasses`, `pathlib`). It never imports `bpy`, `scipy`, `cv2` or `torch` (bl A1, A6). It uses relative imports and is NumPy 1/2-neutral: no `np.float_` or `np.in1d`, explicit dtypes, `default_rng(seed)` (bl A4). A CI script enforces this by AST.
2. **Units**: float64 millimetres in the engine; float32 metres only at the bpy boundary (bl A3, rec INV-2).
3. **Determinism**: fixed seeds, ordered hypotheses, stable sorts; golden tests at rtol 1e-5 (bl Q2).
4. **Pure stages**: each pipeline stage is a function of (inputs, config, seed) cached by the SHA-256 of all three [Rob 2.2].
5. **Licence and consent are data**: every component carries a `LicenceTag`; `result.commercial_ok` is the AND over components (eth §5); gates are pure engine functions (eth A2).
6. **No fabrication**: no template, index map, annotation or prior value is invented to look measured. Procedural assets are labelled `generated`, and unverified scheme indices are `verified:false`.

### 2.2 Layers

```
L0 core/        schema, badged config, consent & licence policy, stage cache, audit
L1 io/, schemes/, data/      EXIF/HEIF/PNG, image ops, LandmarkSet, scheme files, packaged prior
L2 model/       registry, landmark priors, procedural template, template kit
L3 solve/       noise, robust, focal, pnp, bundle, terms, shape models, scale, mirror,
                expression, observability, next-best view
L4 fit/         symmetry, template warp, contours, edge snap, uncertainty, ledger
L5 handoff/, texture/, qa/   key maths, limit stencils, projection; checks, overlay geometry
L6 eval/, testbed/           metrics, coverage, subjects, rigs, detector simulator, faults, scorecard
L7 pipeline/    project file, stages, jobs, CLI          (all of the above: numpy-only)
L8 blender_ext/face3d_likeness/   GPL extension; only bridge.py converts bpy <-> numpy
L9 tools/       maintainer scripts (never imported by the engine)
```

### 2.3 Module map

St: **E** exists, unchanged · **X** exists, extended · **N** new.

| Path | St | Purpose | WP |
|---|---|---|---|
| `geometry/rotations.py`, `mesh/core.py`, `mesh/sparse.py`, `solve/triangulate.py`, `synthetic.py` | E | Kept; `synthetic.py` remains the legacy test fixture | — |
| `geometry/camera.py` | X | Inverse-depth ↔ `Camera` conversion; local virtual camera (rectilinear and stereographic); `to_blender_camera` unchanged | 06 |
| `geometry/procrustes.py` | X | Reflection mode; weighted reflection-plane fit | 12 |
| `geometry/rbf.py` | X | Per-landmark smoothing Λ = diag(α·σᵢ²); explicit linear map | 19 |
| `mesh/laplacian.py` | X | Per-vertex stiffness weights | 19 |
| `mesh/reduced.py` | X | Explicit linear map rows; similarity null-space projector Π | 17 |
| `mesh/distance.py`, `mesh/raster.py` | N | Exact point-to-triangle distance with a grid broad phase; numpy z-buffer rasteriser | 02 |
| `mesh/subdiv.py` | N | Catmull–Clark subdivision, limit stencils, cage fit | 13 |
| `core/{schema,config,policy,cache,audit}.py`, `core/defaults.toml` | N | Formats; badged defaults; consent scopes, data classes, licence taint; stage cache; JSONL audit | 04 |
| `io/exif.py` | X | Adds DateTimeOriginal, Software, DigitalZoomRatio, LensMake/Model/Specification, SubjectDistance, CustomRendered, GPS presence; reads all APP1 segments | 05 |
| `io/{heif,png,image_ops,landmarks}.py` | N | HEIF box parsing (irot/imir/clap/ispe/Exif); stdlib PNG; orientation, flip and resize with coordinate maps; `LandmarkSet` JSON | 05 |
| `schemes/*.json`, `data/landmark_prior_v1.json` | N | Scheme semantics; packaged factor prior (CC0, project-owned) | 03, 14 |
| `model/{registry,landmark_prior}.py` | N | Landmark registry and scheme loader; `LandmarkPrior` protocol, `FactorPrior`, `CompositePrior` | 03 |
| `model/{procedural_head,template_kit,conditional_prior}.py` | N | Procedural CC0 head; kit format with hash checks; conditional template prior | 08 |
| `solve/lm.py` | X | Pluggable linear-step solver; box projection in retract | 07 |
| `solve/noise.py` | N | Noise model in mm by kind; pins; occluder and expression multipliers | 07 |
| `solve/bundle.py`, `solve/reconstruct.py` | X | Main solver (§4.8) | 07, 10 |
| `solve/{robust,terms}.py` | N | IRLS schedule, ν_v, χ² bounds; `Term` and `ShapeModel` protocols | 10 |
| `solve/pnp.py`, `solve/focal.py` | X, N | Multi-start PnP; focal, distance and pose-prior ladders | 06 |
| `solve/{scale,mirror,expression,camera_model}.py` | N | Scale fusion and limbus fit; mirror test; expression tags; per-view camera-model selection and retouch residual test | 15 |
| `solve/{observability,nbv}.py`, `fit/ledger.py` | N | Marginals, LOVO, evidence, tiers, gates; next-best photo; claims ledger | 16 |
| `solve/shape_models.py` | N | `LinearBasis` shape model, extremal soft-argmax landmarks | 17 |
| `fit/silhouette.py` | X | Normal-only correction (M1); delegates to `fit/contour.py` later | 06, 17 |
| `fit/{contour,edge_snap,distance_transform}.py` | N | ContourObs, residual kinds, sub-vertex rim; Viterbi snap; Felzenszwalb EDT | 17 |
| `fit/symmetry.py` | N | Evidence-gated per-pair σ; S/Asym split; symmetry checks | 12 |
| `fit/template.py`, `fit/uncertainty.py` | X, N | Staged warp A–D with gates; per-vertex covariance | 19 |
| `handoff/keys.py` | N | Key stack, exact rebase, Basis Δ propagation, protect mask | 13 |
| `texture/{project,blend}.py` | N | z-buffer projection, weights, gains, two-band blend, fill | 18 |
| `qa/{checks,image_stats,overlay_geom,palette}.py` | N | Findings; blur, clipping, EAR; overlay polylines; Okabe–Ito with CVD checks | 09 |
| `eval/{align,coverage,metrics}.py` | N | Alignment and gauge projection; NEES and coverage; surface error statistics | 01, 02 |
| `testbed/*` | N | Subjects, rigs, detector simulator, faults, renders, scenarios, scorecard | 01, 11 |
| `pipeline/{project,stages,jobs,cli}.py`, `__main__.py` | N | Project file, cached stages, job protocol, CLI `python -m face3d …` | 20 |
| `blender_ext/face3d_likeness/*` | N | Extension (§6) | 21, 22 |
| `tools/*` | N | `build_prior_tables`, `build_template_kit`, `build_scheme_mediapipe`, `detect_mediapipe`, `calibrate_scheme`, `recalibrate_prior`, `build_extension`, `ci_checks` | 03, 08, 14, 21, 23 |

### 2.4 Data flow

```
photos ─ ingest (sha256, EXIF/HEIF, orientation baked, consent) ─ working copies (.npy/.png)
landmarks: helper JSON | imported JSON | pins | edge-snapped contours ─ LandmarkSet (session cache)
triage (QA findings, tags, σ multipliers, focal & distance ladder)
─ multi-start PnP ─ robust BA (inverse depth, ζ, factor prior, jaw, noise, robust schedule)
─ mirror / expression / camera-model / scale nuisances ─ BA re-solve
─ observability, LOVO, ledger, tier, next-best photo
─ warp A→B→C (frozen cameras) ─ D: contours with free cameras (LinearBasis) ─ per-vertex σ
─ result.json + arrays.npz ─ Blender apply (cameras, keys, attributes) ─ artist ─ hand-off ─ texture ─ export
```

### 2.5 How pixels reach the engine

Pixel-based steps (orientation baking, blur and clipping gates, edge snap, limbus fit, texture) take arrays. Three sources are supported:
1. **In Blender**, `bridge.image_to_array` loads the file with `bpy.data.images.load`, reads `pixels.foreach_get` into float32, flips rows to top-down, applies the HEIF/EXIF orientation with `io.image_ops`, and writes `photos/<sha>.npy` into the job folder.
2. **Outside Blender**, the user's-Python helper (Pillow, optional pillow-heif) writes PNG working copies with orientation baked; `io.png` reads 8/16-bit PNG with stdlib `zlib`.
3. **Tests** use synthetic arrays from `testbed.render`.

If Blender cannot decode a HEIC file (unconfirmed, bl Q12.3), the operator asks for a PNG or JPEG export or the helper. Working-copy metadata records `orientation_applied` and the transform applied, so coordinates are never rotated twice.

---

## 3. Data formats and coordinate conventions

### 3.1 Conventions

- **Image.** Continuous pixels with the origin at the top-left *corner*; the pixel (i, j) centre is at (i + ½, j + ½). MediaPipe normalised coordinates map as u = x·W, v = y·H. A resize maps u′ = u·W′/W (not D3's +0.5 form). A horizontal flip maps u′ = W − u and permutes labels with the scheme's L/R permutation π. The eight EXIF orientations are applied as exact coordinate maps. For HEIF, apply `irot`/`imir`/`clap` and then ignore EXIF Orientation (*smartphone-camera-pipeline* 🧠).
- **Camera.** OpenCV convention: X_c = RX + t, +y down, +z forward. Inside the solver each view uses inverse depth (D-02); the conversion is exact and unit-tested.
- **Head frame and gauge.** mm; +x subject's left, +y up, +z out of the face. The template is built in the Frankfort-horizontal frame of the prior mean, with its origin at mid-tragion (*metric-3d-landmark-reference* `head_frame_definition`). The solve fixes the gauge to the template via six rigid constraints on well-observed anchors (§4.6). **FH levelling of the fitted subject is a presentation transform** applied only on export, recomputed from the fitted tragia and orbitale and labelled with their σ.
- **Blender.** 1 BU = 1 m. One parent empty with R_x(+90°) and scale 0.001 holds head and cameras, so engine (x, y, z) mm → Blender (x, −z, y)·0.001 m (bl A8, anat R1.1). Cameras use `to_blender_camera` unchanged: `sensor_fit = HORIZONTAL`, `lens = f·36/W`, and both shifts in units of the **image width** (shift_x = (W/2 − c_x)/W, shift_y = (c_y − H/2)/W). That is correct because Blender measures shift in the sensor-fit dimension (W for HORIZONTAL; max(W, H) only for AUTO) ✅ (known fact 1; bl C4).
- **L/R** is always the subject's side (anat R1.2). Scheme indices never decide side when the scheme marks a group `lr: geometric` (MediaPipe iris 468–472/473–477 ↔️): the side is assigned from geometry (§4.3).

### 3.2 Files

All JSON files carry `format`, `version` and `licence`; arrays above ~1,000 values go to `.npy`/`.npz`, referenced by relative path and SHA-256.

**Project** (`<name>.face3d/project.json`, sits beside the `.blend`):
```json
{"format":"face3d.project","version":1,"seed":1234,"consent_id":"…","template":{"id":"procedural-head-v1","topology_sha256":"…"},
 "settings":{"sex_prior":"unspecified","population":"unknown","scale_population_source":"global_size"},
 "photos":[{"id":"p03","path":"photos/IMG_0412.HEIC","sha256":"…","rights_basis":"self_shot",
   "working_copy":"work/p03.npy","exif":{"f35":26,"lens_model":"…","software":null,"digital_zoom":1.0,"orientation":6,"wh":[3024,4032]},
   "tags":{"view":"front","expression":"auto","occluders":["glasses"],"mirrored":"auto","neutral_reference":false},
   "include":"auto","focal_group":"Apple|iPhone 15|…|26|3024|4032|still"}],
 "pins":[{"photo":"p03","target":{"landmark":"prn"},"xy_px":[1510.2,2011.7],"cls":"nose_tip","expertise":"novice","zoom":4.0}],
 "scale_refs":[{"kind":"caliper","a":"en_L","b":"en_R","mm":32.1,"sigma_mm":0.5}],
 "decisions":[{"kind":"mirror_flip","photo":"p07","by":"user","time":"…"}],
 "active_solve":"solves/0007","landmark_cache":{"keep":false}}
```

**LandmarkSet** (`face3d.landmarks`; session cache by default): `{scheme, detector:{backend, version, model_sha256, licence, commercial_ok, is_ml}, image:{sha256, wh, orientation_applied, input_flipped, coords:"px_corner"}, faces:[{score, uv (N,2) with NaN for missing, visible, cov (N,2,2)?, tta_spread_px?, blendshapes?}]}`. Branch on `scheme`, never on N (rec FMT-1).

**Scheme** (`face3d/schemes/<id>.json`): `{scheme, n, points:[{index, name, anatomical_id|null, kind ∈ {sharp_junction, extremal, curve, contour, brow, iris, hair, generic}, side ∈ {L, R, mid, geometric}, verified: bool, badge}], polylines:{…}, mirror_pairs:[[r, l]…] | "computed", lr_groups:[{indices, rule:"geometric"}], z_policy:"ignore"}`. Points with `verified:false` act only as curve or contour samples or carry an inflated σ_def until calibrated (*landmark-index-correspondence* 🧠).

**Template kit** (`<id>.kit.json` + `<id>.npz`): `{id, licence:"CC0-1.0", generated|measured, source_sha256, units:"mm", topology_sha256, order_checksum, n_verts, landmarks:{scheme:{name:{tri, bary, sigma_annot_mm, provenance}}}, mirror_map, midline, regions:{name:[vertex ids]}, region_weights, contour_rings, jaw_weights, stiffness, normals, uv}`. The loader refuses a topology-hash mismatch (rec INV-4, bl K1).

**Packaged prior** (`face3d/data/landmark_prior_v1.json`, CC0, generated by `tools/build_prior_tables.py` from the research JSON): the 44 ids, means per sex, factor names, sigmas and loadings (132 × 18) per sex, residual total/asymmetric SDs, κ defaults, the extra depth factor, the tragion floor, source SHA-256 and status "expert prior, not published coordinates" 🧠.

**Result** (`solves/NNNN/result.json` + `arrays.npz`, immutable): run `{config_sha256, seed, input hashes, engine version, licence {commercial_ok, components}}`; per camera `{K, R, t, f35, z, P = 100 mm/z, σ_logf, focal_status, model ∈ {pinhole, k1, virtual_stereo}, mirror {decision, Δ, g, margin}}`; per view `{rms_in, rms_lovo (% IOD and mm), ν_v, weight_share, rejected_frac, findings}`; `scale {mode, ζ, σ_ζ}`; landmarks with full covariance; `regions [{name, status, k, σ_rep_mm, coverage, why}]`; `tier`; `flags`; per-vertex arrays (stage vertices, σ_n, support, region ids).

**Job folder** (`<project>/jobs/<uuid>/`): `job.json {stage, config, seed, inputs}`, input arrays, `progress.jsonl` (one JSON object per line: `{t, stage, frac, msg_key}`), `result.json` + `arrays.npz`, `error.json` (no pixels, coordinates or paths, eth A7/F19), and a `cancel` sentinel file.

### 3.3 Data classes and persistence

| Artifact | Class (eth §2.2) | Default persistence |
|---|---|---|
| Photos, working copies | PERSONAL_IMAGE | external; working copies EXIF-stripped (GPS, serials, MakerNote, thumbnail) except Artist/Copyright |
| Detector landmarks, crops | BIOMETRIC_GEOMETRY | session cache, TTL 0; opt-in keep, logged |
| Pins, decisions | BIOMETRIC_GEOMETRY (artist work) | project, RECONSTRUCT scope |
| Solves, meshes, keys | BIOMETRIC_GEOMETRY | project, consent-scoped |
| Texture | LIKENESS_ASSET | needs TEXTURE + rights_basis ≠ unknown |
| Prior, template | AGGREGATE_PRIOR | bundled only if CC0 |

---

## 4. Algorithms

### 4.1 Ingest and photo QA gates

`qa.checks` returns `Finding{code, severity ∈ {info, warn, block}, value, threshold, action, msg_key, fix_key, source, badge}`; actions are one of *down-weight, drop class, exclude from geometry, exclude from texture, ask*. No gate pulls a value toward a norm (anat §6).

| Code | Detection | Action | Source |
|---|---|---|---|
| Q-ORIENT | `orientation_applied` false; view RMS > 3σ with roll ≈ ±90° | bake and re-detect | bl §10 🧠 |
| Q-EXIF-NONE | no Make/Model/f35 | ladder "nothing" prior | com R2.2 🧠 |
| Q-CROP | aspect not native; DigitalZoomRatio > 1; f35/FocalLength > 1.02× group mode | σ_logf 0.06 (zoom) / 0.09 (aspect) | *smartphone-camera-pipeline* 🧠 |
| Q-FRONTCAM | LensModel contains "front" | mirror test priority; selfie distance prior | 🧠 |
| Q-NEAR | solved z < 1.0 m warn, < 0.8 m strong, < 0.6 m texture/2D only | down-weight depth landmarks | com §9 🧠 |
| Q-WIDE | f35 ≤ 16 mm, face beyond 60 % of the half-diagonal or > 25° off-axis | camera-model selection (§4.3) | com R1.7 ✅ effect / 🧠 thresholds |
| Q-PROCESS | CustomRendered (portrait), Software names an editor, digital zoom beyond optical | robust weight + warning, no texture | 🧠/🆕 |
| Q-SMALL | face < 250 px warn, < 120 px reject (face *width*, measured pose-independently: scaled-orthographic scale of the landmarks × the prior's frontal landmark-box width, FU-03); iris < 20 px → no iris scale | σ floor, no detail | com R1.4 🧠 |
| Q-BLUR/BLINK/CLIP | Laplacian variance < 0.6× set median; EAR < 0.2; > 2 % skin clipped | down-weight; drop lids; no photometry | com R1.4, bl §10 🧠 |
| Q-DATES | DateTimeOriginal span > 18 months | split into date clusters | com §9 🧠 |
| Q-FACES / Q-CONSENT | > 1 face at score ≥ 0.6; sha256 not in the ConsentRecord | user picks the subject / block | eth F1–F2 |
| Q-RETOUCH | Software editor; skin smoothness index < 0.5× set median; eye/jaw residual pattern t > 3 (after BA, §4.9) | σ ×2–3, no texture | *smartphone-camera-pipeline* 🧠, 🆕 |

Occluder tags (one click each): glasses → eye σ ×2, no iris scale, lid points under the frame dropped; beard → pg/gn/me and jaw points dropped, outline becomes `outer_bound`, jaw stays prior-driven without a shaven photo; hair → ear and temple weight 0, no silhouette above trichion (the hairline-defined points, kind `hair`, are dropped with them); makeup → lip and brow borders σ ×2 [Rob 3.6] 🧠.

### 4.2 Focal, distance and pose priors

First matching rule wins (rec CAM-6, com R2.2) 🧠:

| Evidence | log f prior |
|---|---|
| SfM import or calibration | σ 0.005–0.02; poses frozen (BA-12) |
| EXIF f35, uncropped original | σ 0.04 |
| EXIF f35, zoom or aspect crop suspected | σ 0.06 / 0.09 |
| FocalLength + focal-plane resolution | σ 0.10 |
| Phone, no focal data | 26 mm, σ 0.25 |
| Nothing | 50 mm, σ 0.6 |

f_px = f35·√(W² + H²)/43.27 (diagonal convention ↔️, ≈4 % from width-based). Focal groups are keyed on (Make, Model, LensModel, f35, W, H, still/video) and tied softly in log space with σ_tie 0.02 (CAM-5 🧠), replacing today's hard shared focal. Distance prior on log z (face distance + 100 mm to the head origin): front camera 0.35 m (σ 0.3), rear 0.8 m (0.4), tele 2 m (0.4), unknown 1.0 m (0.7), taped ±5 cm; ρ bounded to 0.25–10 m (bl C6). The distance prior is never derived from IOD pixels: that would double-count the scale prior (J2 flaw on [Art 3.2]); IOD-based distance is used only to initialise. Optional pose tags: yaw σ 10° (5° with floor marks), pitch 5°, roll 3° (com R2.7 🧠).

### 4.3 Cameras

**Parameters.** Per view: rotation ω_v (multiplicative update R ← exp([δ]×)R), τ_v ∈ ℝ² (mm), a_v = log s_v (px/mm), ρ_v (mm⁻¹, box-projected to [1e-4, 4e-3]). Per focal group: φ_G = log f_G. Tie residual (a_v − log ρ_v − φ_G)/σ_tie; an ungrouped view puts its focal prior directly on a_v − log ρ_v. A view with known focal uses the reduced block (ω, τ, ρ) with s = fρ. Conversion: f = e^a/ρ, t = (τ_x, τ_y, 1/ρ).

**Initialisation.** `solve_pnp` tries f35 ∈ {13, 24, 26, 35, 50, 77, 85, 120, 135, 200} mm (when focal is unknown) × starts {affine, pitch-flipped (R ← R·R_x(π)), yaw-mirrored (reflect the pose about the camera's y–z plane)}, with LM and Huber δ = 2 in σ units (σ from the noise model), and keeps solutions with all z_c > 0. If two cheiral poses > 10° apart score within 20 %, it returns both and raises `C-TWIN` 🆕. The most frontal, most complete view initialises first; later views are initialised against the BA consensus.

**Per-view camera model** (D-12). For a view with flag Q-WIDE, fit three hypotheses on the view alone against the consensus shape: (a) rectilinear: rotate the face ray onto the optical axis with the homography H = KR_virtK⁻¹ (exact, f′ = f); (b) stereographic face-warp correction: local virtual camera along the ray with f′ = f·sec²(θ/2), isotropic 🔢; (c) k₁ ~ N(0, 0.02²). Choose the lowest robust cost + ½·(extra parameters)·ln(2n_v); if the two best are within 2 cost units, mark `ambiguous` and inflate σ ×3. A diagnostic k₁ with |k₁/σ| > 3 on a phone JPEG, or a radial-residual slope implying > 5 % magnification error, flags "non-pinhole processing or wrong z/f" (com R2.8 🧠).

**Geometric L/R.** For each `lr: geometric` group, project the template's left and right eye centres with the current camera and assign each cluster to the nearer one. Before any camera exists, use image-x order relative to the face midline, corrected by the view's `mirrored` flag. If both clusters are nearest the same eye, or the distance ratio is < 1.5, raise `Q-LR-AMBIG`.

### 4.4 Observation noise

For landmark i in view v, with p_iv = f_v/z_iv (px per mm at the point's depth) and t̂ the image tangent from neighbouring curve points:

Σ_iv = ν_v²·[p_iv²·m_iv²·η_i·R(t̂) diag(σ_n,i², σ_t,i²) R(t̂)ᵀ + (σ_tta,iv² + σ_floor,iv²) I₂] + P_iv Σ_expr,iv P_ivᵀ

| Kind | σ_n / σ_t (mm) | σ_def (mm) | Source |
|---|---|---|---|
| sharp_junction (en, ex, ch, sn, sto) | 1.25 / 1.25 | 0.5 | anat R4.1; *landmark-index-correspondence* 🧠 |
| extremal (prn, pg′, me′, g′, zy′, go′) | 2.0 / 3.0 | 1.5 | 🧠 |
| curve (lids, lips, dorsum) | 1.5 / 7.5 | 1.0 | 🧠 |
| contour (oval, jaw) | 2.5 / free (normal-only) | 2.0 | 🧠 |
| brow | 4.0 / free | 2.0 | 🧠 |
| iris centre (gaze; never a shape landmark) | 0.6 / 0.6 | — | [Art 3.1] |
| generic dense point | 2.0 / 2.0 | 1.5 | 🆕 |

- m_iv: occluder and makeup multipliers (§4.1).
- η_i = N/N_eff (N_eff 80, range 60–100) for dense points outside the curated ~100-point subset, else 1 (rec BA-2 🧠).
- σ_tta: test-time-augmentation spread when supplied.
- σ_floor = max(0.5 px, k·face_px/256) with k = 0.6 inner, 0.4 iris, 1.0 brows, 1.5 contour (bl ML 🧠).
- ν_v: §4.5.
- Expression: §4.9.
- **User pins**: Σ = (p_iv²σ_class² + zoom⁻²) I₂, where σ_class is crisp 0.8 (expert) / **1.2 (novice, default)**, contour 1.0, alar base 1.8, nose tip 2.0 ↔️, ears 2.5, palpation 4–5 ↔️, hair-defined 5 mm; zoom = screen px per image px at placement (bl §4 GW 🧠). The optional onboarding sets σ_crisp = max(RMS(Δ)/√2 + 0.3, 0.5) mm.
- **Definition bias** σ_def is not in Σ_iv (D-06).
- **View weight** w_v = 1/n_bin (15° yaw bins × pitch bands); then, if a view's share of the shape-block information trace exceeds 40 %, scale its weight down to 40 % (two passes).

This replaces `ViewObs.sigma_px = 1.0` (≈13× too tight, rec C5) and the 0.006·diagonal heuristic. An explicit float `sigma_px` still overrides, for backward compatibility.

**Image tangents (FU-04, implemented, opt-in: `pipeline.image_tangents` is false by default; the table above is unchanged).** t̂ is derived from the *detections*, never from ground truth: a scheme may name, per landmark, two neighbours on the same anatomical curve (`tangents.neighbours` in the scheme file, optional and backwards compatible), and t̂ in a view is the direction of the chord between the detected neighbours. `anatomical44` carries this for 16 landmarks: lids between the canthi, lips between the cheilions, nasion on the dorsum, the extremal points whose slide direction *landmark-index-correspondence* documents (me′/gn along the chin curve, zy′ along orbitale–tragion, go′ along the mandibular border) and the three points that note types "extremal (profile)" (g′, sl, pg′: along the midline profile between their midline neighbours) 🆕 provisional. For prn, al, or and the ear and cranial points the note documents no slide direction; none was invented (the WBS item "every extremal landmark" is narrowed to the documented ones: owner decision open). The tangent is carried as (t_x, t_y, ρ): the direction confidence ρ = exp(−2(σ_a² + σ_b²)/‖chord‖²) (σ_a, σ_b the neighbours' declared noise) is a separate column, so a plain (N, 2) tangent array keeps its old meaning (an exact direction of any length). ρ enters the covariance exactly: in the (n̂, t̂) frame Σ = diag(σ_n² + s·D, σ_t² − s·D) with D = σ_t² − σ_n², s = (1 − ρ)/2, so the normal direction is never declared tighter than the tangent is known. For the kinds whose tangent σ only *encodes* "free" (contour 1000 mm, brow 40 mm) the leak into the normal uses a finite slide spread instead (`noise.free_tangent_leak_mm` = 7.5 mm, the curve tangent σ 🆕) and the tangent stays free. A landmark without neighbours, with a hidden or dropped neighbour, with ρ < 0.5 (`noise.tangent_min_rho` 🆕) or carrying a user pin has no tangent and keeps the isotropic fallback: max(σ_n, σ_t) for kinds with a finite tangent σ (FU-01), the orientation average for the free-tangent kinds. No σ of the table was changed to match the simulator.

*Why it is off by default (FU-04 review).* The neighbour metadata is an expert reading of the research note, not a measurement. Where a detector's anisotropy follows it, the tangents help a little (fewer good observations rejected, χ²_red +0.01…0.03); where it does not (the WP-01 simulator draws one random direction per landmark), the tangent-derived noise rejects about 4 % of good observations, above the 2 % bound of §7.4, and the shape is 4 % worse; the reported uncertainty stays inside its bands either way (`docs/RESULTS.md` §3.1). A test bed whose noise axes are built from the same neighbour pairs cannot tell the two cases apart, so the release gates are measured on the WP-01 simulator as is, with the shipped default. The switch is to be turned on by the M7 per-index calibration of the error ellipse (§8). **Owner sign-off on this default is pending** (the WBS item asked for the tangents in the pipeline solve; they are implemented and tested there, but not enabled).

### 4.5 Robust schedule

With e_i = ‖Σ_iv^-½ r_iv‖ (whitened radial residual):
1. Two IRLS rounds, Huber weight min(1, 2/e).
2. One Tukey round, w = (1 − (e/4.685)²)² for e < 4.685, else 0.
3. Reject e > 3.035 (P = 1 % in 2D 🔢) and solve by least squares.
4. Before each round, ν_v² = clip(median_i e_i²/1.386, 1, 9).
5. View test: χ²_v = Σ e_i² over the view's inliers, dof_v = 2n_v − 7. Reject the view (finding F-VIEW-REJECT, action *ask*) when χ²_v > q₀.₉₉(dof_v), using the Wilson–Hilferty quantile q(z) = h(1 − 2/(9h) + z√(2/(9h)))³. Flag a view with ν_v > 2 or more than 15 % of its points rejected.

These defaults are tuned on the fault matrix (§7.4).

### 4.6 Shape prior and gauge

The solver's point set is the **anatomical backbone** (all 44 metric landmarks, latent when not observed) plus the scheme's other points. With X̃ = e^-ζ X:

E_shape = ½‖W_A(X̃_A − μ_A)‖² + ½‖W_C(X̃_C − T_C − B(X̃_A − T_A))‖²

- **FactorPrior** (A, WP-03): S_eff = K·S′·K + L_dL_dᵀ + GΛ_gGᵀ + R_floor, where S′ is the sex-mixture covariance with the `size` factor column removed.
  - **Sex mixture** when sex is unspecified (the default; never inferred, anat R2.7): μ = ½(μ_M + μ_F), S = ½(S_M + S_F) + ¼δδᵀ with δ = μ_M − μ_F (anat R5.5). A declared, consented sex selects that sex's prior.
  - **κ**: K = diag(κ) per coordinate, 1.5 by default (unknown population) and 2.5 on the x-coordinates of al, ac and en. κ = 1 only if the user declares a matched population; this is never stored as an ancestry label (anat R4.4, R7.4).
  - **Size factor** removed (ζ carries size; D-03).
  - **L_d**: the extra face-depth factor, σ 6 mm, loading dz = 1 on every landmark except t, sa, sba, eu, op and v. This is the unverified tragion-to-face offset (±8 mm in the source; known fact 4).
  - **R_floor**: tragion residual (1.0, 1.5, 2.0) mm, which makes R positive definite and reflects tragion definition noise. The source has zero variance there by frame construction.
  - **GΛ_gGᵀ**: rigid invariance (translation σ 100 mm, rotation σ 0.5 rad), so the prior constrains shape, not pose.
  - Whitening uses the Cholesky factor of the 3n×3n S_eff (n ≤ 44); `solve` uses Woodbury, S⁻¹ = R⁻¹ − R⁻¹L(I + LᵀR⁻¹L)⁻¹LᵀR⁻¹. Both are tested for equality.
- **ConditionalTemplatePrior** (C, WP-08): B is the biharmonic RBF transfer matrix from template anatomical positions T_A to the other template points T_C. It reproduces affine maps, so the prior is affine-invariant. W_C whitens region σ (lids 1.25, lips 2.0, nose 2.5, brow 2.5, cheek 3.0, jaw 3.0, ears 4.0, scalp 4.5 mm; *open-template-head-kit* 🧠), scaled by κ.
- **Gauge.** Six residuals G_aᵀ(X̃_a − μ_a)/0.01 mm on anchors {en, ex, p, n, prn, sn, ch, ls, li, sto} fix rotation and translation to the template without biasing shape. ζ fixes size.
- **Prior share.** p_i = σ²_post/σ²_prior per landmark is reported. *Likeness mode* (opt-in) widens κ until p_i ≤ 0.2 wherever ≥ 2 views see the point (anat R1.4), but labels are always computed at prior weight 1 (§4.12).
- hm08/MPFB bases and FLAME 2023 Open are **not** default (D-04); an adapter is promoted only when it beats this prior on held-out error and coverage.

### 4.7 Scale

ζ ~ N(0, 0.045²) is the single population source by default; the IPD prior (63 ± 3.8 mm, vergence-corrected ≈2 mm at 0.35 m) may replace it, never join it (rec BA-10; [Acc 3.7]). Metric terms:
- **Caliper or tape chord**: (‖X_a − X_b‖ − L − o)/σ_L, σ 0.5 mm, o = pressed-landmark offset (default 0, ↔️ +2–5 mm for bony points).
- **ID-1 card**: corners as extra points with chord 85.60 ± 0.5 mm and a "held against landmark k" depth prior, σ 10 mm.
- **Iris**: per eye and view, (f_v·D/z_eye,v − d_px)/σ_d with a shared D ~ N(11.8, 0.6²) mm (✅ mean, ↔️ σ). Used only when d_px ≥ 20, the limbus is sharp and there are no glasses. The limbus fit samples radial gradient profiles around the iris centre and fits a circle by IRLS; σ_d comes from the fit residual, floored at 0.5 px.

Iris alone gives ≈5.1 %; fused with the 0.045 population prior, ≈3.4 % 🔢; with a caliper, < 1 %. Scale mode is `measured` (caliper or card), `iris` or `prior`, always printed with ±%. References that disagree by more than 1 % and more than 2σ raise `S-CONFLICT`.

### 4.8 The bundle objective and solver

E = Σ_v w_v Σ_i ρ(r_iv) + Σ_v E_jaw,v + E_shape + E_sym + E_gauge + ½(ζ/σ_ζ)² + E_focal + E_tie + E_dist + E_pose + Σ_terms E_term

- r_iv = Σ_iv^-½(π_v(X_iv) − u_iv), with X_iv = jaw(X_i, θ_v) (§4.9); visibility weight ramps from 0 at n·(−v) = cos 80° to 1 at cos 60°, using template normals rotated by the current pose; far-side oval points drop out at |yaw| > 25°; MediaPipe z is ignored (rec BA-3, bl D2 🧠).
- **Terms** (`solve/terms.py`): extra residual blocks with their own parameters (scale references, iris D, contours, pins on surfaces). Each implements `params()`, `residuals(state)` and `jacobian(state)`.
- **ShapeModel**: `FreePoints` (default) or `LinearBasis` (X = e^ζ(X̄ + ΦΠc) for the surface stage). The LM, robust schedule and covariance code are shared.
- **Solver**: LM with Nielsen damping (exists); dense Cholesky steps when the parameter count ≤ 2,500. Above that, the step eliminates the non-anatomical points by Schur complement: under the conditional prior their Hessian blocks are 3×3 block-diagonal, leaving a reduced system over cameras, the anatomical backbone and ζ. Retract applies the box projection for ρ and θ.
- **Covariance**: H = JᵀJ at convergence (weights frozen). Σ_XX = (H_XX − H_XcH_cc⁻¹H_cX)⁻¹ eliminates cameras and globals; camera marginals use the complementary Schur complement. The result carries:
  - `cov` (3N×3N, template gauge, unconditional);
  - `cov_shape` (conditional on ζ̂);
  - `point_sigma_mm` = √diag(cov_shape) (legacy meaning, so existing tests stay valid);
  - `zeta`, `zeta_sigma`;
  - `sigma_rep_mm` (§4.13).
- **SfM cameras** are frozen: triangulate, Umeyama, then a shape solve; landmarks never move SfM cameras (rec BA-12).

### 4.9 Expression and jaw

**Tags.** Blendshape scores Δb are measured from the subject's own minimum (or the photo marked neutral).
- *Neutral*: jawOpen < 0.08, mouthSmile < 0.15, eyeBlink < 0.35, browInnerUp < 0.2.
- *Expressive*: smile > 0.25, squint/eyeWide/brow > 0.3, blink > 0.4.
- *Mild*: anything between (anat §6 🧠).
- *No scores*: an inner-lip gap/ch–ch > 0.04 drops sto and li; mouth width > 1.08× the set median marks mild 🆕.
- *Re-tag* at most 3 rounds: mobile-class reduced χ² > 4 → at least mild, > 9 → expressive 🆕.
  **Amended by FU-04** (the rule above is kept in `expression.retag_from_residuals`; the pipeline uses `retag_from_evidence`). Measured on the fault matrix, 4 and 9 are the 3·10⁻⁶ and 10⁻¹⁷ quantiles of the statistic's null on 12 dof, and a jaw opening never reaches the mobile class because the per-view hinge absorbs it. The pipeline now tests, against the view's *neutral* declared noise: (a) T = Σ min(e_i², 3.035²) over the mobile and jaw-dependent landmarks (full Mahalanobis residuals; a rejected landmark counts as a rejected one, no more) against χ²(2n) quantiles at false-alarm rates 0.01 (mild) and 0.001 (expressive); (b) the fitted jaw angle against the neutral population N(1.5°, 1°²), z = (θ̂ − 1.5°)/SD₀ with SD₀ the standard deviation of the fitted angle under "neutral" (SD₀² = σ_n² − σ_post² on a neutral-tagged view), at one-sided rates 0.05 (mild) and 0.005 (expressive) 🆕. Worst-case false tags per neutral view: 6 % mild, 0.6 % expressive.

**Covariance inflation.** Σ_expr,iv = (μ_c(tag)² − 1)·σ_kind,i²·I₃ in 3D, projected by P_iv = ∂u/∂X. Class multipliers μ_c (neutral/mild/expressive) are rigid 1/1/1.25, semi-mobile 1/1.75/2.5, mobile 1/3/drop, jaw-dependent 1 while θ is fitted ([Rob 3.6] 🧠). Lids are dropped on blink (EAR < 0.2) or gaze pitch > 12°. With no neutral view, lip and lid measurements finer than 1 mm are suppressed (BA-9).

**Jaw hinge.** X_iv = X_i + ω_i(R(θ_v e_x)(X_i − c) − (X_i − c)), with c = mid-tragion + (0, −5, +11.5) mm (10–13 mm anterior, 0–10 mm inferior; bl K8 ↔️) and per-landmark weights ω_i (me, gn, pg, sl, li 1.0; sto 0.5; ch 0.4; go 1.0; others 0). θ_v ∈ [0°, 30°] has prior N(1.5°, 1°²) on neutral views and N(1.5°, 3°²) otherwise.

**Hard gate**: one smiling view among five moves neutral-region identity < 0.3 mm. An expression basis is opt-in only, through a licence-clean adapter with the neutral anchor (BA-9) (deferred).

### 4.10 Mirror test

For each view: fit it against X̂, the BA consensus without that view (the template if alone), as given (C₀) and flipped (u′ = W − u, labels π; C₁). Δ = (C₀ − C₁)/C₀. Predicted detectability g = Σ_i‖Σ_i^-½ J_i A_i‖², with A = ½(X̂ − M·X̂_π) the consensus's asymmetric part.
- g < 4 → `undetermined` 🆕.
- All views selfies/front camera → project-level `mirror: unverifiable`; asymmetry claims flagged.
- Else `suggest_flip` iff Δ > 0.10 (front camera) or 0.20 (others) **and** C₀ − C₁ > 2√(2n_v) ([Art 3.6], derived) — otherwise `keep`.
- The UI pre-selects [Flip] only when Δ > 0.2 and the front-camera EXIF or ≥ 2 other views agree. The engine never mutates inputs; applying a flip is a user (or explicit CLI flag) decision stored in `project.decisions`.

Target: TPR ≥ 0.95 at ≥ 0.8 mm true asymmetry, FPR ≤ 0.02 (§7.4).

**Amended by FU-04 (thresholds derived from the test's null; the rule above is the original).** The flipped hypothesis mispredicts the view by 2w with ‖w‖² = g (after removing what a pose refit absorbs), so C₀ − C₁ ~ N(−4g, 16g) for a correctly labelled view and N(+4g, 16g) for a mirrored one.
- `suggest_flip` iff Δ > 0.10 / 0.20 (unchanged) **and** C₀ − C₁ > τ, with τ = z²₁₋α: the false-flip rate of a view is at most α for every g (its maximum over g is Φ(−√τ)). α = 10⁻⁴ (`mirror.flip_alpha` 🆕) gives τ = 13.83; this replaces 2√(2n_v), which grows with the number of landmarks although the null does not.
- A significant gap (C₀ − C₁ > τ) that the relative rule does not confirm (Δ ≤ 0.10 / 0.20) is `undetermined` (flag `M-GAP-SIGNIFICANT`), never `keep`: the evidence favours the flip at the α level.
- Otherwise `keep` iff g ≥ g_min, else `undetermined`. g_min is the detectability at which the *complete* rule above, on costs capped at 3.035σ per landmark, suggests the flip of a mirrored view with probability p = 0.95 (`mirror.keep_power` 🆕). Per landmark the gap gains x_i = min(|ε_i + d_i|², c²) − min(|ε_i|², c²) with d_i = 2w_i, and C₁ gains min(|ε_i|², c²); their moments depend on |d_i| only (tabulated), (gap, C₁) is treated as bivariate normal, and power = P(gap > τ, gap > Δ_rel/(1 − Δ_rel)·C₁). g_min is computed per view, for its own distribution of the asymmetry over its landmarks, its n_v and its camera class: 11.6 for 44 evenly loaded landmarks on a non-front camera (WP-15 note "g ≈ 12"), about 13 for a random pattern, larger with more landmarks (14.4 at 60, 17.9 at 80), 8.7 on a front camera. The gap condition alone gives ((z_p + √(z_p² + τ))/2)² = 8.16, a lower bound only: at g = 8.3 the complete rule finds 77 % of the flips on 44 landmarks, not 95 % (FU-04 review; the first FU-04 version used 8.16, and the g < 4 rule before it answered `keep` where the test found 44 % of the flips). The predicted power agrees with a Monte Carlo through the engine (0.77 / 0.93 / 0.97 predicted, 0.78 / 0.93 / 0.97 found at g = 8.3 / 12 / 14.2).
- Evidence is pooled across views in the noise, not in the decision: a flip is a property of one photo, so the test of a view uses the consensus of the *other* views and adds its projected covariance to Σ_i; the project status reports the summed detectability (`g_pooled`) without a set-level threshold (deviation from the FU-04 wording "pool mirror evidence across views"; owner decision open).
- Σ_i is the noise the view is declared with plus the projected covariance of the consensus without that view.
The engine still never mutates inputs. Status of the target: §7.4.

### 4.11 Symmetry

Per-pair, per-axis σ on d = X_l − M_P(X_r), where M_P reflects about the current plane P (anat R4.2 🧠): canthi/lids 0.85, brows 1.5 (vertical 2.0), alare/orbitale/zygion 1.25, cheilion 1.75, gonion 2.75, ears 3.5 mm. Midline-x σ: n/g 0.9, prn/sn 1.75, pg/me 2.5 mm. **Evidence gating**: where the pair's region is measured or constrained, the weight is ×0.25 (σ ×2). The plane is re-fitted each outer iteration by weighted reflection Procrustes (weights: upper face 1.0, midface 0.5, lower 0.25, ears 0.1; anat R3.3).

Output split: S = ½(V + mirror(V)), Asym = V − S. Checks: mirror RMSD < 0.3 mm on photos with visible asymmetry → "too symmetric"; > 1.5 mm → "unusually asymmetric – check pose"; with fewer than 2 views ≥ 30° apart, reported asymmetry σ is multiplied by 4 (anat §6).

### 4.12 Observability, evidence and tiers

- **Focal**: `measured` if σ_post(log f) < 0.10 (bl C2), `prior used` if > 0.8·σ_prior (CAM-7). P = 100 mm/z is reported.
  - **Amendment (FU-03, closes the M6 release blocker; 🆕).** The 0.10 threshold is applied to what the photos carry, not to a σ inherited from the prior. `measured` needs all of: σ_post < 0.10; the CAM-7 test (σ_post ≤ 0.8·σ_prior, so the solved value is the photos', not the prior's); σ_photos(log f) < 0.10, where σ_photos is the posterior σ of log f with the focal prior rows *and* the distance prior rows removed from the Gauss–Newton information (f and z trade off along the image-scale valley, so a distance prior is a focal prior in disguise; `solve.observability.focal_prior_evidence`, no re-solve); and no overruled prior on that view (§4.13: a focal with contradicting evidence reads `partial`). An unknown prior is never `measured`. A focal that is the EXIF value therefore reads `prior used`; tier S still accepts "EXIF-confirmed" (σ_EXIF ≤ 0.04) separately. Every view that is not `measured` carries the finding `C-FOCAL-PRIOR` (info for an EXIF or calibrated prior, warn for a guessed one and for an EXIF prior the photos contradict but that was kept, §4.13).
- **Evidence** per region r, always at prior weight 1: k_r = 1 − tr(Π_rΣ_postΠ_rᵀ)/tr(Π_rΣ_priorΠ_rᵀ), where Π_r selects the region's coordinates after gauge projection.
- **Coverage rules** (hard): depth needs 2 views ≥ 30° apart in yaw (bl C7); nose and chin projection need a front view plus |yaw| ≥ 60° (com R5.9); jaw underside needs a view with pitch ≤ −15°; ears need |yaw| ≥ 30° and pitch fixed by ≥ 2 views (com R3.3).
- **Status**:
  - *measured*: k ≥ 0.8, coverage met and σ_rep ≤ the region target;
  - *constrained*: 0.5 ≤ k < 0.8;
  - *prior-driven*: k < 0.5;
  - *unobserved*: no view sees the region.
- **Region targets** (EV-3 🧠): eyes, lips 1.0; brows, nose 1.2; nose projection, forehead, cheeks 1.5; jaw 2.0; ears, cranium 3.0 mm.
- **Tier**:
  - **S** *metric*: scale measured, nose and chin projection measured, ≥ 5 views, focal measured or EXIF-confirmed.
  - **A** *iris-scaled*: scale ∈ {measured, iris}, ≥ 3 views with one at |yaw| ≥ 45°; depth is claimed only where the coverage rules hold.
  - **C** *blockout*: one photo, all views within |yaw| < 20°, or all-selfie.
  - **B** *proportions only*: everything else.

### 4.13 Reported uncertainty and gates

σ_rep,i² = σ_post,i²·max(1, γ², χ²_red) + σ_def,i², where:
- χ²_red = Σe²/(m − p_eff), with p_eff = tr(H_dataΣ_post);
- γ² = mean of held-out whitened residuals² from leave-one-view-out re-solves (≥ 3 views; warm-started, ≤ 10 iterations). The predictive covariance is Σ_obs + PΣ_X(−v)Pᵀ.

Flags: LOVO error > 2× in-sample; focal versus EXIF > 15 %; group spread > 5 %.

**Focal versus EXIF (FU-03; 🆕 uncalibrated).** After pass 1 each focal group whose prior comes from EXIF is tested against the photos: t = (log f_photos − log f_EXIF)/√(σ_photos² + σ_EXIF²), with f_photos and σ_photos the photos-only estimate of §4.12 (one Gauss–Newton step from the solve). The EXIF value is *contradicted* when |t| > 2.576 (nominal false-alarm rate `focal.exif_reject_alpha` = 0.01 per group), σ_photos ≤ 0.25 (`focal.exif_reject_max_data_sigma`: the photos must know the focal at least as well as the ladder's "phone, no focal data" rule) and the group has ≥ 3 views. Pass 1 is then re-solved with the ladder prior *without* the EXIF focal (phone 26 mm σ 0.25, or 50 mm σ 0.6); that solve is adopted only if its focal differs from the EXIF value by more than 15 %, and the finding `C-FOCAL-EXIF` (warn, a card that asks, H6) and the flag `C-EXIF-OVERRULED` are raised. Otherwise the EXIF prior stands; when the EXIF value was contradicted but kept this way (the re-solve stayed within 15 % of it), the view's `C-FOCAL-PRIOR` is raised at *warn* instead of info and states the disagreement (`detail.exif_contradicted`, with t and the re-solve's relative difference), so a significant contradiction is never reported as a trusted EXIF (H6; FU-03 review). Measured behaviour, including the ranges where the photos do not carry the information and the test cannot fire, is in `docs/RESULTS.md` §3.1–3.2.

**Deviation recorded at M6 (WP-23; WBS FU-02 option (i); 🆕 test-bed calibrated, provisional).** The pipeline's observe stage reports σ_rep with the factor f = max(γ², min(1, χ²_red/κ), χ²_red, 0.5) in place of max(1, γ², χ²_red) (`pipeline.sigma_rep_deflate`, default on; `solve.observability.inflation(deflate=True)`; κ = 0.9535 corrects χ²_red for the robust trimming; floor `observability.deflation_min`). f equals the rule above whenever γ ≥ 1 or χ²_red ≥ 1, so inflation is untouched; it falls below 1 only when the in-sample χ²_red *and* the held-out γ² both say the declared noise is over-stated, and then takes the larger of the two. With fewer than 3 views γ = 1 and nothing is deflated. Both χ²_red and γ are evaluated against the noise **before** the QA σ multipliers (Q-SMALL, Q-BLUR, Q-NEAR × `pipeline.downweight_sigma_mult`), so the caution a down-weighted view adds is never deflated away; the result reports these calibration values (`chi2_red`, `gamma`), the solve's own χ²_red (`chi2_red_solve`) and f (`inflation`). Justification: with the rule above the gain-form σ_rep is over-conservative on the test bed (1σ coverage 0.771 against the §7.5 band 0.60–0.76 on the definition-bias row; NEES/dof 0.79 on two scorecard scenarios, FU-02); with f, 30 seeds give NEES/dof 1.04 and coverage 0.719 on that row, and no gated set is over-confident (`docs/RESULTS.md` §4.1). Evidence is tier 1 (synthetic) only; the rule reverts to the one above by setting the default to false.

**Shrinkage and plausibility** (D-18), per region r with x̂_r = X̃_r − μ_r: T_r = x̂_rᵀS_rr⁻¹x̂_r and λ = eig(I − S_rr^-½Σ_rrS_rr^-½). Then m = Σλ (= k_eff,r), v = 2Σλ², g = v/2m, h = 2m²/v. The finding is `pulled toward average` if T_r < g·q_h(−2.326) and `implausible` if T_r > g·q_h(3.090), with q_h the Wilson–Hilferty quantile. k_eff,r is reported.

### 4.14 Next-best photo

Candidates: yaw −90…90° in 15° steps × pitch {−20°, 0°, +20°}, using the dominant group's focal and median distance. For each, the predicted Jacobian on the visible anatomical subset gives H′ = H + J_cᵀWJ_c − J_cᵀWJ_p(J_pᵀWJ_p + Λ_p)⁻¹J_pᵀWJ_c, with p the candidate's own (ω, τ, ρ, focal-tie) block and Λ_p its priors. The score is Δ = Σ_r w_r(tr_rΣ − tr_rΣ′) via a Woodbury rank update. Weights: lids 1.0, brows 0.9, lips 0.8, nose 0.7, nose projection 0.7, jaw 0.5, cheeks 0.4, forehead 0.3, ears 0.15 (*face-perception-likeness* 🧠). The output is one sentence, e.g. "Next: left profile, eye height, 1.5–2 m". Acceptance: frontal-only sets pick |yaw| ≥ 60° in ≥ 90 % of seeds.

### 4.15 Template warp and per-vertex uncertainty

| Stage | Operation | Advance / gate |
|---|---|---|
| A | Umeyama, proper and reflected, on anatomical landmarks. Reflected RMS < 0.5× proper → "mirrored source" (never auto-flip); 7-landmark RMS > 10 mm → wrong axes (bl W2) | always |
| B | RBF φ = r: (K − Λ)w + Pa = y with Λ = diag(α·σᵢ²), α = 10⁻² (MM-8) | landmark RMS < 2.2 mm (2.5 % of 88 mm) |
| C | Bilaplacian with per-vertex stiffness (lid margins 3.0, lips 0.3, forehead 0.5, ligament strips 3–5; edge-flow ×5 on lids, lips, nostrils, ears; anat R5.9 🧠); offsets capped at 4 mm unless ≥ 2 views agree (MM-10) | RMS gain < 1 %/iteration |
| D | Contours with free cameras via `LinearBasis` (§4.16); no landmark moves > 0.5 mm (com R5.2) | contour ≤ 1 % of face height (bl S3) |

Gates at every stage: det J_warp > 0.2 and no flipped triangles (MM-11), else roll back the stage and flag. Targets are never symmetrised.

**Uncertainty.** Stage B is linear in the targets, V_B = V_A + A(X − X_A), with A = Φ_eval[K − Λ, P; Pᵀ, 0]⁻¹ restricted to the target columns. The explicit map is verified by finite differences. Cov(V_j) = A_jΣ_XA_jᵀ + σ²_res,r(j)·I₃, computed as ‖A_jL_X‖² with Σ_X = L_XL_Xᵀ, in chunks; no unit solves (J1/J2 flaw). σ_res by region (lids 1–1.5, nose 2–3, cheeks 2.5–4, ears 3–5, scalp 3–6, neck 5–10 mm; 🧠) applies until stage D's joint Laplace posterior covers the vertex (k > 0.5). Reported per vertex: σ_n = √(n_jᵀCov(V_j)n_j) and the σ_rep inflation of §4.13. *Recalibration recorded at M6 (WP-23; 🆕 test-bed calibrated, provisional):* Σ_X is the shape covariance `cov_shape` (conditional on scale) times the §4.13 factor f, and σ_res enters as `pipeline.sigma_res_scale` (0.25) × the regional values above. The regional values themselves (🧠, warp residuals against real faces) are unchanged; the multiplier is calibrated on the synthetic test bed only, where the warp reproduces the procedural subjects far better than the literature residuals, and must be re-derived (most likely raised towards 1) when scans are available (H8). Evidence: `docs/RESULTS.md` §4.2.

### 4.16 Contours, profiles and edge snap

- **Observations.** `ContourObs{view, xy (M,2), normal_out (M,2), sigma_n (M,), kind, source, commercial_ok}` from pins, a lasso, the MediaPipe oval, an edge-snapped polyline or an optional helper mask (SAM/MediaPipe segmenter, Apache-2.0).
- **Model rim.** On each mesh edge where q = n·(x − C_v) changes sign (vertex normals), the rim point is p = x_a + q_a/(q_a − q_b)·(x_b − x_a); it is kept if an adjacent face is front-facing and the rasterised depth confirms visibility.
- **Residuals.** r = n_obsᵀ(π(p) − x)/σ_n. `hard` uses Huber; `outer_bound` max(0, r − margin), margin 0–3 mm in px, weight ×10 (hair, beard, hat); `inner_bound` max(0, −r). A backward (model→photo) term uses the observed contour's Euclidean distance transform (Felzenszwalb–Huttenlocher, exact squared distances), truncated at 3σ, weight 0.5.
- **Matching.** Re-associated each outer iteration by uniform-grid nearest neighbour (not the O(M·P) matrix). The gate starts at 0.15·IOD_px and shrinks to 5σ_n; pairs with normals > 40° apart are rejected.
- **Noise.** σ_n² = σ_edge² + (0.5·s_model)² + σ_blur², floored at 0.005·IOD_px; at most 40 effective samples per view.
- **Edge snap** (zero-download contour source): a coarse polyline (≥ 5 clicks or the oval points) is resampled to M stations, each with offset k ∈ [−L, L], L = ⌈0.03·IOD_px⌉ along its normal. Minimise Σ −g_j(k_j) + λΣ|k_j − k_j−1| (g = gradient magnitude after a 1 px Gaussian, λ = 0.2·median g) by Viterbi in O(M·L²); deterministic. σ_snap,j = √(σ_g²/max(−∂²g_j/∂k², ε)) with σ_g = 1.4826·MAD of g in the band (px, dimensionally consistent), and σ_n = max(1 px, σ_snap).
- **Profiles**: detector points are dropped when |yaw| > 65°; profile pins on g, n, prn, sn, ls, li, pg use contour σ.
- **Extremal landmarks** (g′, zy′, go′, pg′) on a surface are evaluated as a soft-argmax over their candidate region, temperature 1.5 mm, recomputed after each pose update (anat R3.2).
- **Gauge projector** Π removes the 7-DoF similarity from the RBF coefficients at the anchors, so c cannot trade with the free cameras: with constraint C = Gᵀ(I₃ ⊗ Φ_a), Π = I − Cᵀ(CCᵀ)⁻¹C.
- **Diagnosis** (SIL-3): if interior landmark RMS < 3 % IOD but the contour residual exceeds 3σ_n on ≥ 2 views (or the ears fail), report "focal or distance wrong, not the face".

### 4.17 Hand-off maths

**Keys.** Basis = template; `ID_fit` (slider max 1.5; above 1 is a caricature preview); `Asym` and `artist` relative to `ID_fit`; muted `stage_*` diagnostics. Keys store absolute positions, so a refit rebases exactly: artist′ = artist + (ID′ − ID). A Basis write adds Δ to every dependent key (bl K3). "Protect measured regions" writes support (clipped to [0, 1]) into `.sculpt_mask`, where 1 = fully masked: measured vertices are locked and guessed ones stay sculptable (corrected after the WP-13 review; the original "1 − support" protected the guessed regions instead). A painted mask m becomes data weight 1 − m plus a pin at σ 0.2 mm (bl W5).

**Limit stencils.** On an all-quad cage, the Catmull–Clark limit position of a vertex of valence n is v∞ = (n²v + 4Σe_j + Σf_j)/(n(n + 5)), with e_j its edge neighbours and f_j its face-diagonal neighbours. Fit C to minimise ‖S_lim C − T‖² + μ‖L(C − T)‖², with L the unit-weight graph Laplacian and μ = 10⁻⁵, so Multires L2/L3 interpolate the fitted surface without the ≈e²/(6R) shrink (bl W4). 🔢 On a 1,538-vertex cube-sphere head (mean edge 8.7 mm): cond(S_lim) ≈ 9; the naive cage shrinks by RMS 0.38 mm (max 0.93); the fitted cage leaves RMS 0.0002 mm (max 0.0012).

### 4.18 Texture

Gates: TEXTURE scope, rights_basis ≠ unknown, reprojection median ≤ 1.5 px and max ≤ 3 px (bl T2). Views flagged filtered, retouched, warped or clipped, or from another date cluster, never feed albedo.
- z-buffer visibility with ε = max(1 mm, 2σ_geom);
- weight w = vis·cos²θ·fade(60°→75°)·edge;
- per-view gains solved in log space with Σ log g_v = 0;
- two-band blend split at σ 3 mm, high band from the best view;
- holes filled harmonically, then with model colour, and marked `filled` in the confidence map;
- mirror fill only on explicit opt-in, recorded in provenance (D-27).

Outputs: linear albedo, confidence, view index; "absolute colour unknown" without a colour chart.

---

## 5. Honesty and uncertainty contract

H1. Every number shown or exported carries σ_rep (§4.13) and a basis (*measured / constrained / prior-driven / unobserved*), worded plainly ("likely within ±1.4 mm, measured").
H2. Labels and σ are computed at prior weight 1. The rigidity slider, likeness mode and caricature preview never change them (J1 flaw on [Art 3.4, 3.11]).
H3. Definition bias is a floor that does not shrink with more views (D-06).
H4. Scale is always printed with its mode and ±% ("scale: iris+population ±3.4 %"). Iris alone is never described as better than ≈5 %. With no metric source the tier cannot exceed B.
H5. Focal is "measured" only when σ_post(log f) < 0.10, the photos alone reach that σ and the solved value is theirs rather than the prior's (§4.12 amendment, FU-03); otherwise "from prior".
H6. Mirror, expression, retouch and lens findings are cards that ask; the engine never silently flips, symmetrises, beautifies or pulls toward a norm (anat §6).
H7. `undetermined` and `unverifiable` are first-class answers (mirror, filters on a single photo).
H8. Every report states the tier, the count of active 🧠/🆕 defaults, and "not validated against a scan" until M7 passes. No claim is finer than the reference modality (0.2–1 mm, bl Q4).
H9. Prior-driven regions are hatched in the viewport and listed in the report with the next-best photo that would measure them.
H10. Ancestry is never asked, inferred or stored. Sex, age and BMI are optional consented inputs; the default is the sex mixture with unknown-population κ.
H11. Generated, ML-derived and filled data are labelled (`generated`, `is_ml`, `filled`) and never enter identity terms unless declared measurements.
H12. Honesty is tested: coverage, NEES, false-confidence and alarm-rate gates (§7.5) block a release.

---

## 6. Blender extension

### 6.1 Manifest and packaging

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
files = "Read reference photos and write project files"
[build]
paths_exclude_pattern = ["__pycache__/", "*.pyc", "/tests/", "*.blend1"]
```

`tools/build_extension.py` vendors `face3d/` into `face3d_likeness/engine/face3d/` and refuses to build if:
- any file lacks an SPDX header;
- any bundled asset is not CC0;
- a wheel or `network` permission is present;
- the tagline exceeds 64 characters;
- the engine imports anything outside numpy and the standard library.

The engine files keep MIT SPDX headers inside the GPL-3.0-or-later package (eth A1; compatible). The store build has no wheels, no network and CC0 assets only (known fact 3). The procedural template is generated at first run by our own code, so no asset is needed until the M3b template is verified. `blender_version_min` is the oldest line the external Blender CI tests.

### 6.2 Layout and module rules

`__init__.py` (register/unregister over a module list, skipping absent modules) · `compat.py` (feature probe < 100 ms: blender, python tag, numpy, online_access, platform; bl A9) · `props.py` (PropertyGroups: project path, pins, photo items, job status) · **`bridge.py`, the only module that touches bpy mesh or image data** · `jobs.py` · `launcher.py` · `ops_*.py` · `ui_panels.py` · `overlays.py` · `keymap.py`.

Bridge rules (bl A3):
- `foreach_get` into contiguous float32 (coordinates) or int32 (indices), converted to float64 for the engine;
- write back with `astype(float32)`, `foreach_set`, `mesh.update()`, in OBJECT mode, restoring the previous mode;
- copy mathutils values with `np.array(x, dtype=float64)`;
- image rows flipped bottom-up ↔ top-down.

### 6.3 Jobs and threading

`JobRunner.start(stage, inputs)` writes the job folder and launches `subprocess.Popen([sys.executable, "-I", launcher.py, job_dir])`. `launcher.py` inserts its own `engine/` directory (vendored) or the repository root (development) into `sys.path` and calls `face3d.pipeline.jobs.run_job(job_dir)`. A `bpy.app.timers` callback polls every 0.1 s, reads new `progress.jsonl` lines and does ≤ 20 ms of work per tick (bl A5). Cancel writes `cancel` and kills the process after 1 s, so a crash never costs sculpt work. Under `bpy.app.background`, jobs run synchronously in-process. Results are applied by a separate undoable operator.

### 6.4 Operators and guided rail

The sidebar tab **Face3D** has a guided rail: Consent → Photos → Check → Landmarks → Cameras → Shape → Confidence → Sculpt → Texture → Share. Each stage shows an icon *and* a word (Done / Needs attention / Not started), a "done when" line, and one primary button; `poll_message_set` explains why a button is disabled. Expert options sit in `DEFAULT_CLOSED` sub-panels; they display badges and never change labels (H2).

| Operator (`face3d.`) | Behaviour | Runs |
|---|---|---|
| `project_new`, `consent_edit` | project folder; ConsentRecord; default-deny gates | main |
| `photos_add` | hash, EXIF/HEIF, working copies, GPS strip, QA cards, one locked camera per photo with a background image | main + bridge |
| `landmarks_import`, `landmarks_detect` | JSON import; or the user's-Python helper path | main / job |
| `pin_tool` (WorkSpaceTool, P) | place/drag/nudge pins in camera view; σ from zoom; blind first pins | modal |
| `trace_contour` | ≥ 5 clicks → edge snap job | modal + job |
| `solve`, `fit`, `job_cancel` | background jobs | job |
| `card_accept`, `card_dismiss` | apply or dismiss a finding (e.g. mirror flip); logged | main, UNDO |
| `apply_result` | cameras, keys, attributes; refuses on topology mismatch or in Edit/Sculpt mode | main, UNDO |
| `handoff_sculpt`, `rebase_sculpt` | duplicate, bake mix, clear keys, Multires L2/L3 from the limit-fitted cage; rebase | main, UNDO |
| `review_next`/`_prev`, `view_next`/`_prev`, `compare_flip` (hold) | worst-first review queue; camera stepping; hold-to-flip | main |
| `texture_project`, `report_export`, `prepare_for_sharing`, `purge` | gated; lists and purges biometric leftovers (eth F9) | job / main |

All operators report through `self.report`; tracebacks never reach the user. Keys live in `keyconfigs.addon` (remappable); everything is F3-searchable.

### 6.5 Overlays and accessibility

`gpu` POST_PIXEL handlers draw polylines computed by `qa/overlay_geom.py`: σ ellipses, residual arrows ×5, pins, model contour versus traced outline, hatching for prior-driven regions, and a flipped thumbnail for mirror cards. The Okabe–Ito palette (auto pin #56B4E9 circle, user pin #E69F00 square, conflict #D55E00 cross, selected #F0E442 ring, contour #009E73 line, guessed #CC79A7 hatch) is always combined with shape, a dark outline and a light halo (≥ 3:1).
- **Contrast check.** Simulated protan, deutan and tritan vision leaves some colour pairs at ΔE₇₆ 16–17 🔢, so CI asserts ΔE ≥ 15 for every pair and ΔE ≥ 20 for any pair that shares a glyph shape.
- **Motion.** Comparison is hold-to-flip (no 3 Hz blink, WCAG 2.3.1), plus blur at 3 % of face width and a 64 px thumbnail.
- **Text.** Findings also go to the Info log and the text/HTML report (Blender has no screen reader).

### 6.6 Shape keys, undo and Multires

Per D-22 and §4.17. Engine state lives in project sidecars outside the undo stack. Objects are re-fetched by a `face3d_uuid` custom property after undo. A pin drag is one `undo_push` on release. Writing to the Multires copy only goes through `multires_reshape` from a subdivided copy, guarded by a test scene, with "new copy" as the fallback (bl K5, Q4 unverified). Attributes written: `f3d_sigma_mm`, `f3d_support`, `f3d_status` and region face sets.

### 6.7 Landmark acquisition

Every build supports: (1) manual pins and imported `LandmarkSet` JSON (zero-download path, eth A4); (2) `tools/detect_mediapipe.py`, run in the user's own Python with a user-installed `mediapipe`. The helper uses the Tasks FaceLandmarker in IMAGE mode with `num_faces=2`, blendshapes and transform enabled, a user-supplied SHA-256-pinned `.task`, and 6–10 TTA passes (jitter and a flip with π), and writes `LandmarkSet` JSON. MediaPipe semantics come from the scheme file (`verified:false` until calibrated). Wheel builds stay off-store, never bundle `.task` weights, and re-verify the weight licence each release (↔️).

### 6.8 Testing without Blender

- `tests/blender_stub/` provides minimal `bpy`, `mathutils`, `gpu`, `gpu_extras` and `blf` stubs.
- Tests: register/unregister; operator id prefixes and flags; `poll_message_set` text; bridge dtype and contiguity; frame mapping; the launcher runs under `-I` from a vendored layout; the manifest lint via `tomllib`; an AST check that only `bridge.py` touches mesh/image data and that `face3d/` never imports bpy.
- A headless Blender script (`blender -b --factory-startup --python-exit-code 1`) is delivered for an external CI on 4.5 LTS / 5.2 LTS (bl Q3), including the 0.01 px camera round-trip test (bl C4).

---

## 7. Validation plan

### 7.1 Test pyramid

1. **Unit and oracle tests**: analytic Jacobians against numeric ones; noiseless reprojection < 1e-6 px; inverse-depth ↔ pinhole equality; point-to-triangle against brute force to 1e-9; EDT against brute force; Woodbury against dense; rebase exact to 1e-9; schemas; policy gates.
2. **Test bed tier 1** (`face3d/testbed`, seeded, runs here): landmark-level (WP-01) and surface-level (WP-11).
3. **Bridge tests**: bpy stub, AST, manifest lint, subprocess launcher.
4. **Release gates** (WP-23): fault matrix, honesty metrics, scorecard against the committed baseline.

### 7.2 Test bed and the inverse crime

- **Subjects** come from generators **independent of the fitted prior** (D-30):
  - legacy `synthetic.random_subject` (polynomial fields);
  - smooth Gaussian-RBF displacement fields on the anatomical mean, with symmetric and asymmetric parts and anisotropic size;
  - on the procedural surface: feature variations outside the factor model (dorsal hump, chin cleft, lip curvature, cheek fullness).

  Prior-drawn subjects exist only as a labelled diagnostic and never set an acceptance threshold.
- **Detector simulator**: class σ in mm by kind (anisotropic); a **per-index definition bias shared across views** (σ_def); 5 % outliers at 5–20σ; visibility from template normals; TTA spread.
- **Rigs**: studio ring (5–9 views, 85 mm, 1.5–3 m), rear phone (26 mm, 0.6–1.5 m), selfie (22–30 mm, 0.25–0.45 m), camera roll (mixed, missing EXIF).
- **Images**: a numpy rasteriser draws depth, masks, Lambert-shaded textured images and blurred edges for the pixel steps.

### 7.3 Metrics

- Exact point-to-triangle distance (grid broad phase, signed by angle-weighted pseudonormals) under NoW-style 7-landmark rigid alignment, landmark similarity alignment and region alignment (rec EV-1).
- Median, RMS, p95, F@0.5/1/2 mm, per-region signed bias, scale error, and configuration RMS (EV-2).
- **Gauge-projected** landmark coverage and NEES: errors and covariances projected onto the complement of the 7-DoF similarity tangent at the truth; NEES = eᵀ(PΣPᵀ)⁺e/(3N − 7); scale evaluated separately as z = (ζ̂ − ζ)/σ_ζ.
- E_like = Σw_r RMS_r/Σw_r with the §4.14 weights.

### 7.4 Fault-injection matrix (targets 🆕; M1 records today's engine as the baseline)

| Fault | Must raise | Required | Degradation bound |
|---|---|---|---|
| 1 mirrored view among ≥ 3 | suggest flip | TPR ≥ 0.95 at ≥ 0.8 mm asymmetry; FPR ≤ 0.02; `undetermined` ≥ 0.9 when symmetric | shape ≤ 1.1× clean after user confirms |
| Orientation not baked | Q-ORIENT | TPR ≥ 0.99 | — |
| EXIF ±30 % crop or missing | C-FOCAL-PRIOR when unobservable | focal < 5 % when views span ≥ 60° (com R8.4) | ≤ 1.2× clean |
| Selfies at 0.35 m | Q-NEAR, tier ≤ B | z within 15 % | — |
| Jaw 5–15°, smile in 1 of 5 | expressive tag | TPR ≥ 0.9 | neutral identity moved < 0.3 mm (hard) |
| Beauty warp (eyes +6 %, jaw −4 %) | Q-RETOUCH | TPR ≥ 0.8 with ≥ 3 clean views | identity bias ≤ 0.5 mm |
| Off-axis wide-angle (stereographic and rectilinear) | Q-WIDE + correct model | model chosen correctly ≥ 0.8 | shape < 1 mm extra |
| Beard / glasses / hair tags | tag actions | beard → jaw prior-driven | scalp inside hull |
| Face 150 px | Q-SMALL | coverage holds | — |
| 5 % gross outliers | rejection | ≥ 95 % caught, ≤ 2 % inliers lost | ≤ 1.1× clean |
| Definition bias 1 mm | — | NEES/dof with σ_rep in [0.8, 1.25] | — |

Alarm budget: ≤ 1 spurious warn/block finding per 10 clean photos.

**Status at M6 (WP-23, updated by FU-03 and FU-04; targets unchanged).** The release run (`tests/test_fault_matrix.py`, 30 seeds through the pipeline, every rate on its point estimate) meets the rows for orientation, selfies, beard, glasses and hair tag actions (point drops included), Q-SMALL on every 150 px face, C-FOCAL-PRIOR on the unobservable set, rectilinear off-axis, gross outliers, definition bias, the alarm budget and, since FU-04, the expressive tag on a 5–15° jaw opening (28/30; the re-tag of §4.9 as amended). These targets are *calibration-pending*: mirror TPR; focal < 5 % with a cropped or missing EXIF (the robust EXIF prior of §4.13 fires on 0 of 30 sets: at 0.6–1.5 m the photos alone do not constrain the focal under the declared noise); expressive-tag TPR on a 2–4 mm smile and the 0.3 mm identity bound on both expression rows; Q-RETOUCH TPR; stereographic model selection (22/30 = 0.73, inside the binomial bound, below the target as a point estimate; the selected model is still not applied to the solve); scalp-inside-hull (not evaluated); coverage on 150 px faces (conservative). None is relaxed: each is listed with its measured value, cause and proposed fix in `docs/RESULTS.md` §3.1.

**Unreachable at the §4.4 nominal noise (FU-04 measurement; an owner decision on the rows is open).** With the tests calibrated against their own null distributions (§4.9, §4.10 as amended), three single-view targets cannot be met through the pipeline: (i) *mirror*: the detectability of a 0.8 mm asymmetry is g ≈ 1.4 against g_min ≥ 11.6 (1/30 flagged; also at 2.5 mm asymmetry, g ≈ 1.7, 4/30, because the consensus asymmetry is shrunk by the symmetric shape prior); the engine test itself meets the row where the detector is more precise (among the views that reach their g_min: 14 of 15 at 0.5× noise, 39 of 40 at 0.2×); (ii) *smile*: 2–4 mm of mouth-corner motion stays inside the null of the mobile-class χ² (0/30); (iii) *beauty warp*: eyes +6 % / jaw −4 % move the ratio statistics by 0.7–2.2 declared σ against the threshold 3 (0/30; 6/30 at three times the warp). The honesty conditions hold on the same run: no flip on 390 unmirrored views, no `keep` on a mirrored view, no neutral view tagged expressive (0/150), Q-RETOUCH on 1 of 1110 unretouched views (stated rate 0.7 %). The 0.3 mm identity bound, measured on all 44 landmarks against the untagged clean twin, is below the 0.35 mm that the expressive tag's own down-weighting moves at nominal noise (`docs/RESULTS.md` §3.2).

**Gate scenes and the image-tangent default (FU-04 review; owner sign-off pending).** Every row above is measured on the WP-01 detector simulator as is and with the pipeline as shipped, i.e. `pipeline.image_tangents` = false (§4.4). The first FU-04 version shipped the tangents on and measured the gates on scenes whose noise axes were rebuilt from the scheme's own neighbour pairs; on the unmodified simulator that default lost 4.1–4.5 % of good observations against the 2 % bound of the gross-outlier row and raised `F-VIEW-OUTLIERS` on the golden scene. Neither the modified scenes nor the simulator's random axes say how a real detector slides, so the conservative state ships and the question is left to the M7 per-index calibration. Three decisions are **open for the owner, not taken here**: (a) tangents off by default although the FU-04 item asked for them in the pipeline solve; (b) "every extremal landmark" narrowed to the 16 landmarks with a documented direction; (c) no set-level pooling of mirror evidence (§4.10).

**Release blocker `exif_crop.focal_label` (honesty, H5 / H12): closed by FU-03.** At M6 every view of a set whose EXIF focal was wrong by ±30 % was labelled focal "measured" while the solved focal was 28 % off, because σ_post(ln f) < 0.10 was inherited from the trusted wrong prior. The label is now derived from the photos' own information (§4.12 amendment): on the 30-seed release run no view of those sets is labelled "measured" (0/150; they read "prior used" and carry `C-FOCAL-PRIOR`), and the same holds without EXIF and on the unobservable set. No honesty gate fails; `OPEN_HONESTY_VIOLATIONS` in `tests/test_fault_matrix.py` is empty, and a new honesty gate (`exif_crop.no_false_overrule`) bounds the false alarms of the robust EXIF prior on clean sets.

### 7.5 Honesty metrics and promotion

- **Coverage.** In *measured* regions, 0.90–0.99 of vertices have |error| ≤ 1.96σ_rep. Landmarks: aligned 1σ coverage 0.60–0.76 and NEES/dof 0.8–1.25 over ≥ 30 seeds (*validation-test-bed*).
- **False confidence.** ≤ 5 % of *measured* regions exceed 2× their target.
- **Promotion rule.** A default or model changes only if held-out error drops and coverage holds, and E_like does not worsen by more than 2 % against the committed scorecard.

**Status at M6 (WP-23, re-measured after the FU-04 review; bands unchanged).** All bands are met on 30 seeds through the pipeline as shipped (FU-02 factor of §4.13, per-vertex recalibration of §4.15; image tangents of §4.4 off) on the WP-01 simulator: vertex coverage 0.986 (z RMS 0.60: still conservative, at the upper edge of the band), landmark 1σ coverage 0.722 and NEES/dof 1.02 with a 1 mm definition bias, false confidence 0/104, likeness-mode invariance 30/30, scale z RMS 1.07 (as at FU-03: 0.723 / 1.02 / 0/105 / 1.07). Clean-set χ²_red is 0.72 and the FU-02 factor 0.76. With the opt-in tangents the landmark bands also hold (NEES/dof 1.05, coverage 0.71, on the simulator's random axes and on scheme-aligned axes alike; χ²_red 0.79 / 0.75), so the opt-in is not over-confident; what it costs when misaligned is rejected observations (§7.4). With the §4.13 rule as originally written the shipped run gives landmark coverage 0.772 (outside the band), NEES/dof 0.80 and vertex coverage 1.000. Evidence, the calibration curves and the remaining conservative cases (sets with QA down-weights) are in `docs/RESULTS.md` §4.

Waves (dependency-ordered, for parallel execution): 1 = {01, 02, 03, 04, 05}; 2 = {06, 07, 08, 09}; 3 = {10, 11, 12, 13, 14}; 4 = {15, 16, 17, 18}; 5 = {19}; 6 = {20}; 7 = {21}; 8 = {22}; 9 = {23}; offline = {24}. WP-01 must merge before WP-06 and WP-07 touch the engine, so the baseline scorecard records today's behaviour.

**Implementation conventions for parallel WPs.**
- A new subpackage `__init__.py` contains only a one-line docstring, `"""face3d.<pkg>: <purpose> (exports added by WP-23)."""`. Two WPs that both need the package create byte-identical files.
- Public re-exports are added only by WP-23. Until then, tests import from module paths (e.g. `face3d.eval.metrics`).
- Every 🧠/↔️/🆕 constant is registered through `face3d.core.config.register_defaults` with its badge and source (WPs from wave 2 on).
- No WP edits a file owned by another WP in the same wave.

---

## 9. Risks

1. **Most defaults are 🧠 or 🆕** (≈70 % in the research). Mitigation: named badged defaults, honesty gates, M7 calibration, and "not validated against a scan" in every report.
2. **The prior is an expert synthesis**, weakest in profile depth (prn 108–130 mm ahead of tragion). Mitigation: κ widening, the 6 mm depth factor, coverage rules and next-best photo pushing users to profiles, recalibration tools.
3. **Synthetic detector errors are not MediaPipe's**, and the index semantics are unverified (even iris L/R ↔️). Mitigation: scheme data files, geometric L/R, `verified:false` downgrades, render-and-detect calibration on the maintainer's machine (M3b).
4. **The procedural head is not anatomical.** Mitigation: it is labelled `generated`; accuracy claims are made relative to the test bed only; M3b swaps in the real CC0 template behind the same kit format.
5. **Performance in numpy**: dense LM is fine to ~2,500 parameters; MediaPipe-478 uses the curated subset plus the conditional prior; LOVO and next-best photo use warm starts and rank updates. Budgets are asserted in tests.
6. **Blender behaviours unverified here** (HEIC decode, 5.x attribute names, multires_reshape detail-follow, shift round trip): delivered with headless scripts for external CI and guarded fallbacks.
7. **Store rules may shift** (C7/C8 on derived index tables and downloads) and **law may shift** (BIPA, AI Act Art. 50): policy as data, offline by default, `is_ml` provenance.
8. **Alarm fatigue**: measured by the alarm budget.
9. **Undetectable cases** (symmetric or all-selfie mirroring, a filter on the only photo) are reported as `undetermined`/`unverifiable`.

---

## 10. Deferred, explicitly

- **Live reduced solver** (P ≈ 110, warm-started, 2–5 iterations per drag, accepted when within 1e-3 of batch) and the 2-minute pin onboarding: after M6. The MVP solves on release in a background job.
- **Cranium vault parameters** (L, B, H log-normal priors, tape arc-length term, hair `outer_bound` at ×10) beyond what contours provide: after M6.
- **Hinged ears** with CC0 ear keys: after M7. Ears are silhouette-only and prior-driven.
- **Expression basis** (ψ_v with neutral anchor) via a licence-clean adapter; ARKit expression keys (need RIG_ANIMATE).
- **FLAME 2023 Open adapter** (user path, SHA-pinned, CC-BY attribution) and the hm08/MPFB TargetSpace: experimental, promoted only by the §7.5 rule; hm08 stays `commercial_ok: null` until its licence is verified.
- **Dense photo-consistency (NCC) sweep**: opt-in only after photometric pose refinement (TEX-7), gated to neutral, unfiltered views at ≤ 0.08 mm/px with ≥ 2 agreeing views, written only to `detail_measured`, rolled back if any landmark moves > 0.5 mm. **SH9 shading detail** goes to `detail_inferred` only.
- **Phone video / TrueDepth / LiDAR, monocular depth, generative fill, Gaussian avatars, learned regressors, identity-embedding losses**: not measurements; opt-in later, if ever.
- **Detector wheel builds** (off-store), the onnxruntime path, and SAM or segmenter helpers beyond the optional mask import.
- **Never built**: symmetrising, anonymising, 1:N matching, URL or social importers, telemetry (eth F16–F18, A5, A7).
