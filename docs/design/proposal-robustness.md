# Proposal: a robustness-first photo-to-head engine

*Design angle: robustness first, built for the photos people actually take. Written 2026-11-20 against `face3d/` at commit 887c5e5 (42 tests passing) and the five digests in `research/_raw/requirements_*.md`.*

**Citations** give the topic note and its badge: ✅ verified, 📄 single-sourced, 🧠 unverified expert knowledge, ↔️ contested. **🆕** marks a value this proposal introduces. It has no source and must be calibrated on the test bed (§5) before it becomes a default. Gap-topic notes were not yet in the repo, so citations to `open-template-head-kit` and `cranium-under-hair` refer to their draft data tables in `research/data/`. Every 🧠 or 🆕 number is a named config value with its badge, never a constant (anatomy digest).

---

## 0. Thesis

Accuracy on good photos is the easy part. The tool succeeds or fails on mirrored front-camera selfies, WhatsApp copies with no EXIF, a beard covering the jaw, and a smile in the only three-quarter view. This proposal makes four commitments:

1. **Detect each known failure mode** with a simple test that can be checked on its own.
2. **Degrade gracefully.** Down-weight or exclude bad evidence rather than fit through it.
3. **Say exactly what the result can still claim**, region by region.
4. **Measure all of the above** on a fault-injection test bed before any number becomes a default.

When a simple, verifiable algorithm and a clever, fragile one compete, the simple one wins.

---

## 1. Vision and user journey

### 1.1 The journey

1. **Start a project and record consent.** The add-on creates a `ConsentRecord` (ethics §2.1) and a project folder. Nothing runs without the `RECONSTRUCT` scope.
2. **Add photos.** The user can follow a guided capture protocol or drop in a camera roll. Each photo is hashed and its EXIF parsed (orientation, focal length, lens, date, editing software). Orientation is baked into the working pixels, and the originals stay untouched.
3. **Get landmarks.** Landmarks come from MediaPipe, either through an external helper that writes JSON or through an optional bundled wheel, or from manual pins. Manual pins and JSON import always work, so there is a path that needs no downloads at all (ethics A4).
4. **Triage the photos.** Every photo gets a QA card covering:
   - estimated distance, focal evidence and lens risk;
   - mirror status, expression tag and occluder tags;
   - blur and resolution;
   - a suspected-retouch flag.

   Each flag comes with the action it triggers and the reason, for example: *"selfie at ≈0.35 m: used for colour and frontal outline, not for nose projection"*.
5. **Solve cameras and landmarks.** A robust multi-view bundle adjustment (BA) runs, followed by a mirror check and an observability report ("focal length came from the prior, not from these photos").
6. **Fit the head.** The CC0 template is warped in stages, then fitted to contours and silhouettes. Profiles are traced with edge snapping.
7. **Review.** The user sees:
   - a claims ledger marking each region as measured, constrained, prior-driven or unobserved;
   - a held-out-view check;
   - an overlay sheet per camera;
   - the worst landmarks, listed first.

   The tool also asks for the photo that would most reduce uncertainty: "add a left profile".
8. **Hand off.** The likeness is written as shape keys on a stable topology. An empty `artist` layer is created, a Multires copy is prepared for sculpting, an optional texture is projected, and the export carries its provenance.

### 1.2 What we promise for each input tier

| Tier | Typical input | Promise | Default label |
|---|---|---|---|
| **S** | Protocol capture: 5 or more views spanning ±60–90° yaw plus a profile, 1.5–3 m, tele lens, EXIF, a scale reference | Metric size; depth measured; target ≤1.5 mm RMS face (benchmarks-metrics Table 6 🧠) | `metric`, depth measured |
| **A** | Rear phone camera, 3 or more views, at least one at |yaw| ≥ 45°, EXIF intact | Proportions plus measured depth where coverage rules hold (§3.10); scale from the iris, ≈2–4 % (multi-view-fitting 🧠) | `iris-scaled` |
| **B** | Camera roll: mixed devices and dates, missing EXIF, some expressions | Frontal proportions through the solved cameras; depth prior-driven unless a view exceeds 60° yaw | `proportions only`, depth prior |
| **C** | One photo, or selfies only | A blockout that matches through its own camera; no claim on nose projection, ears or cranium | `blockout`, single-view |

The tier is computed from the evidence, not chosen by the user. The UI always shows it.

---

## 2. Architecture

### 2.1 Layers and modules

The engine stays numpy-only. It imports only `numpy`, `math`, `json`, `struct`, `zlib`, `hashlib` and `tomllib`, always through relative imports. It never imports `bpy` (blender digest A1). In the Status column, **E** means the module exists, **X** means extend it, and **N** means new.

| Layer | Path | Status | Purpose |
|---|---|---|---|
| Policy and schemas | `face3d/core/schema.py` | N | Load and validate the project, landmark, scheme, template and result formats (§2.3), with explicit versions |
| | `face3d/core/policy.py` | N | Consent scopes, `LicenceTag`, taint as an AND over components, data classes; pure Python (ethics A2) |
| | `face3d/core/config.py` | N | Named defaults, each with badge and source; config SHA-256; seeds |
| I/O | `face3d/io/exif.py` | X | Add DateTimeOriginal 0x9003, Software 0x0131, DigitalZoomRatio 0xA404, LensMake 0xA433, SubjectDistance 0x9206, and read every APP1 segment |
| | `face3d/io/heif_exif.py` | N | Walk ISOBMFF boxes (`meta/iinf/iloc`) to pull the EXIF block out of HEIC; pixels are never decoded in the engine |
| | `face3d/io/png.py` | N | Decoder for 8/16-bit non-interlaced PNG (stdlib `zlib`), for tests and QA outside Blender |
| | `face3d/io/image_ops.py` | N | Bake EXIF orientation on arrays, flip with label permutation, resize maps |
| | `face3d/io/landmarks.py` | N | Adapters from detector JSON or manual pins to `LandmarkSet` |
| | `face3d/mesh/core.py` | E | OBJ I/O and topology |
| QA | `face3d/qa/image.py` | N | Face size, blur (variance of the Laplacian), clipping, skin-smoothness index |
| | `face3d/qa/photo.py` | N | Lens and distance triage, focal evidence ladder, intrinsics groups, date span |
| | `face3d/qa/expression.py` | N | Blendshape and geometric tagging with a subject baseline |
| | `face3d/qa/mirror.py` | N | Flip test with a discriminability check |
| | `face3d/qa/retouch.py` | N | EXIF Software check, residual-signature regression, wide-angle warp risk |
| | `face3d/qa/flags.py` | N | Flag registry: code, severity, evidence, action, source |
| Solve | `face3d/solve/pnp.py` | X | Multi-start (pitch-flip, yaw-mirror), cheirality check, twin flag, f35 set from CAM-3, Huber in σ units |
| | `face3d/solve/noise.py` | N | Landmark class σ in IOD fractions, anisotropic covariance, floors, dense inflation, per-view scale |
| | `face3d/solve/bundle.py` | X | Covariance blocks, visibility, jaw hinge, distance priors, soft focal tie, view cap, 4σ rejection, Schur marginals |
| | `face3d/solve/observability.py` | N | σ(log f), σ(log z), P = 100 mm/z, radial-signature regression, leave-one-view-out (LOVO) |
| | `face3d/solve/reconstruct.py`, `lm.py`, `triangulate.py` | X / E / E | Orchestration with the new noise and prior inputs |
| Model | `face3d/model/registry.py` | N | Anatomical landmark registry with kinds: vertex, barycentric, extremal, contour (anatomy R2.1) |
| | `face3d/model/template_kit.py` | N | Load the template sidecar and verify hashes, mirror map and regions |
| | `face3d/model/prior.py` | N | Per-landmark σ prior (baseline), linear basis adapters (CC0 targets, user-supplied FLAME 2023 Open), χ² and shrinkage gates |
| | `face3d/model/nuisance.py` | N | Jaw hinge, expression multipliers, occluder actions |
| Fit | `face3d/fit/template.py` | X | Staged A to D with gates; reflected Umeyama check; per-landmark RBF λ; region stiffness |
| | `face3d/fit/silhouette.py` | X | Point-to-line sliding residuals, one-sided mask hinges, trimming |
| | `face3d/fit/contour_trace.py` | N | Edge snapping by dynamic programming (DP) from a coarse polyline |
| | `face3d/fit/uncertainty.py` | N | Linear propagation of landmark covariance to vertex σ; claims ledger |
| | `face3d/geometry/*` | E / X | `RBFWarp` takes a diagonal Λ; camera export is unchanged |
| | `face3d/mesh/laplacian.py`, `reduced.py` | X / E | Per-vertex stiffness weights |
| Texture | `face3d/texture/{raster,project,blend}.py` | N | numpy z-buffer, view weights, gains, two-band blend, confidence |
| Evaluation | `face3d/eval/{surface,align,report}.py` | N | Exact point-to-triangle distance, NoW-style and landmark-only alignment (EV-1/2) |
| | `face3d/testbed/{subjects,capture,detector_model,faults,scorecard}.py` | N | Synthetic scenarios and fault injection (§5) |
| Pipeline | `face3d/pipeline.py`, `face3d/__main__.py` | N | Deterministic stage runner; CLI `python -m face3d {triage,solve,fit,report,testbed}` |
| Tools (outside the extension) | `tools/detect_mediapipe.py` | N | External detector helper (Tasks API, `IMAGE` mode, `num_faces=2`, test-time augmentation (TTA)) that writes landmark JSON |
| | `tools/build_template_kit.py`, `tools/build_extension.py` | N | Reproducible kit and zip builds with SHA-256 checks |
| Blender | `blender_ext/face3d_head/` | N | Manifest, bridge, operators, panels, overlays, jobs, key planner; engine vendored by the build |

### 2.2 Data flow

```
photos ─▶ ingest (sha256, EXIF/HEIF-EXIF, orientation, PhotoRecord, consent gate)
       ─▶ landmarks (helper JSON | wheel | manual pins) ─▶ LandmarkSet + TTA spread
       ─▶ triage (per-photo flags, tags, σ multipliers, include/exclude, focal ladder, groups)
       ─▶ camera init (multi-start PnP vs template, mirror test, distance prior)
       ─▶ robust BA (+jaw hinge, priors, rejection, per-view scale, view cap)
       ─▶ observability + LOVO ─▶ tier, scale mode, focal status
       ─▶ template warp A→B→C (gated) ─▶ contours/silhouettes D (one-sided masks)
       ─▶ uncertainty propagation ─▶ claims ledger
       ─▶ result.json + fit.obj + sigma.npy ─▶ Blender bridge (cameras, keys, attributes, overlays)
       ─▶ artist sculpt (artist key, Multires copy) ─▶ texture projection (gated) ─▶ export + provenance
```

Each arrow is a pure function from typed inputs to typed outputs. Each stage result is cached under the hash of its inputs and config, so a re-run after editing one pin recomputes only the stages below it.

### 2.3 Key data formats

All formats are JSON with a `format` name and an integer `version`. Arrays larger than about 1,000 numbers go to sidecar `.npy` files, referenced by path and SHA-256.

**Project** (`<name>.face3d.json`):

```json
{"format":"face3d.project","version":1,"seed":1234,
 "consent_id":"…","subject":{"pseudonym":"S01","declared":{"age_band":"adult"}},
 "photos":[{"id":"p03","path":"photos/IMG_0412.HEIC","sha256":"…","rights_basis":"self_shot",
   "exif":{"f35":26,"make":"…","lens_model":"… front camera …","datetime":"2025-06-02T10:11:12",
           "software":null,"orientation":6,"pixel_wh":[3024,4032]},
   "working":{"orientation_applied":true,"crop":null,"wh":[3024,4032]},
   "tags":{"view":"front","expression":"auto","occluders":["glasses"],"mirrored":"auto"},
   "landmarks":"lm/p03.json","contours":["ct/p03_profile.json"],"include":"auto"}],
 "scale_refs":[{"a":"ex_R","b":"ex_L","mm":null},{"kind":"card_id1","photo":"p01","mm":85.60,"sigma_mm":0.5}],
 "pins":[{"photo":"p03","landmark":"prn","uv":[1510.2,2011.7],"sigma_px":4}],
 "config_overrides":{},"template":"mpfb2-hm08-head@1"}
```

**Landmark set** (written by the helper or the pin editor). It holds coordinates only, never pixels (ethics: biometric geometry, session cache):

```json
{"format":"face3d.landmarks","version":1,"scheme":"mediapipe478",
 "detector":{"backend":"mediapipe-tasks","version":"0.10.x","model_sha256":"…","licence":"Apache-2.0",
             "commercial_ok":true,"is_ml":true},
 "image":{"sha256":"…","wh":[3024,4032],"orientation_applied":true,"input_flipped":false,"coords":"px_corner"},
 "faces":[{"score":0.97,"uv":"lm/p03_uv.npy","visible":null,"blendshapes":{"jawOpen":0.02},
           "tta_spread_px":"lm/p03_spread.npy","n_tta":8}]}
```

**Landmark scheme** (bundled, our own work, CC0). It records the convention per index and never guesses from the point count (reconstruction FMT-1):

```json
{"format":"face3d.scheme","scheme":"mediapipe478","n":478,"lr_permutation":"…478 ints…",
 "midline":[0,1,2,4,6,13,14,17,152,168],
 "classes":{"iris":[468,473],"anchor":[33,133,263,362,61,291],"lid":[159,145,386,374],
            "oval":"…36 ints…"},
 "convention":{"oval":"semi_contour","default":"surface_3d"},
 "sigma_iod":{"iris":[1.0,1.0],"anchor":[1.5,1.5],"lid":[2,5],"prn":[2.5,2.5],"brow":[4,6],"oval":[2.5,12]},
 "anatomical":{"ex_R":33,"en_R":133,"prn":1,"sn":2,"ch_R":61,"ls":0,"li":17},
 "verification":{"ex_R":{"status":"visual-2x","date":null}}}
```

**Template sidecar** (`template.json` plus `template.obj` and `basis.npz`):

```json
{"format":"face3d.template","template_id":"mpfb2-hm08-head","version":1,
 "source":{"upstream":"MPFB2 base mesh","upstream_sha256":"…","licence":"CC0-1.0","commercial_ok":true},
 "units":"mm","frame":"engine","n_vertices":0,"topology_sha256":"…","order_checksum":"…",
 "landmarks":{"en_R":{"kind":"barycentric","tri":0,"bary":[0,0,0],"sigma_mm":[1.5,1.5,2],"provenance":"annotated-2x"}},
 "scheme_maps":{"mediapipe478@0.10.x":{"file":"maps/mp478.npz","renders":40,"spread_mm_p95":0}},
 "regions":"regions.npz","mirror_map":"mirror.npy","midline":"midline.npy",
 "contours":{"jaw":"…","profile":"…","hairline":"…"},
 "stiffness":{"lid_margin":3.0,"lips":0.3,"forehead":0.5},
 "basis":{"kind":"cc0_targets_svd","file":"basis.npz","K":0,"sha256":"…","status":"experimental"}}
```

The zeros above are placeholders that the kit builder fills in. Nothing is hand-typed (§3.7).

**Result** (`results/run-<n>.json`):

```json
{"format":"face3d.result","version":1,"engine":"0.2.0","config_sha256":"…","seed":1234,
 "inputs":["sha256…"],"tier":"A",
 "cameras":[{"photo":"p03","K":[[…]],"R":[[…]],"t":[…],"convention":"opencv_px_corner",
   "f35":25.7,"z_mm":382,"P":0.26,"sigma_logf":0.21,"focal_status":"prior","group":"g2",
   "mirror":{"decision":"flipped","delta":0.41,"status":"decided"}}],
 "views":[{"photo":"p03","rmse_iod":0.018,"lovo_rmse_iod":0.024,"noise_scale":1.3,"weight_share":0.22,
   "rejected_frac":0.03,"tags":{"expression":"mild"},"flags":["Q-SELFIE","Q-MIRROR-FIXED"]}],
 "scale":{"mode":"iris","s":1.012,"sigma_rel":0.03},
 "landmarks3d":{"names":"…","X":"X.npy","cov":"covX.npy"},
 "regions":[{"name":"nose_projection","status":"prior_driven","k":0.31,"sigma_mm":3.8,
   "why":"no view with |yaw|≥60°"}],
 "flags":[{"code":"C-FOCAL-PRIOR","severity":"info","evidence":{"sigma_logf":0.21,"prior":0.25}}],
 "licence":{"commercial_ok":true,"components":["template:CC0-1.0","detector:Apache-2.0"]},
 "mesh":"fit.obj","vertex_sigma":"sigma.npy"}
```

### 2.4 Coordinate conventions

These are fixed in one place, `face3d/core/schema.py`, and have round-trip tests.

- **Image.** Continuous pixel coordinates with the origin at the top-left corner of the top-left pixel, so pixel (i, j) has its centre at (i + 0.5, j + 0.5), as in `camera.py`.
  - MediaPipe's normalised output maps as u = x·W.
  - Resizing maps as u_orig = u_small·W/W_small. The "+0.5" form in blender digest D3 belongs to the centre-at-integer convention and is not used.
  - A horizontal flip is u′ = W − u, plus the label permutation π.
- **Camera.** OpenCV: +x right, +y down, +z forward; X_c = R·X_w + t.
- **Head frame.** Millimetres, float64. +x is the subject's left, +y up, +z out of the face; the origin is on the midsagittal plane (anatomy R1.1; `synthetic.py`). It is levelled to Frankfort horizontal only once porion and orbitale are estimable.
- **Blender.** One `R_x(+90°)` parent empty maps (x, y, z) → (x, −z, y), and the bridge scales by 0.001 to get 1 BU = 1 m (blender digest A8). `.L` = +X.
- **Camera export.** `to_blender_camera`: lens = f·36/W, `sensor_fit` HORIZONTAL, both shifts divided by W. This is already tested on a 3000×4000 image (blender digest C4).
- **IOD** means outer-canthal ex–ex, the normaliser in landmark-detection Table 2. Values given in interpupillary units are multiplied by 0.70 (63/90 mm; landmark-detection Table 3 🧠). For each view, IOD_px = f·IOD_mm/z_v once a camera exists. Before that it is 0.2 × the landmark-box diagonal (`reconstruct.py`). This matters because the 2D ex–ex distance halves at 60° yaw.

### 2.5 Determinism

- Every random draw (TTA, multi-start order, synthetic data) uses `default_rng(project.seed)`.
- Hypotheses are tried in a fixed order and ties are broken by index.
- Sorts are stable, dicts are ordered, and all solves run in float64.
- Every result records `config_sha256` and the seed.
- Golden tests use rtol 1e-5 and are never bit-exact (blender digest Q2).
- The code is NumPy 1/2-neutral and CI covers 3.11 + NumPy 1.26 and 3.13 + NumPy 2.x (blender digest A4).

---

## 3. Algorithms

### 3.1 Input QA gates

Each gate produces a flag and a fixed action: down-weight, drop a landmark class, exclude the photo from geometry, exclude it from texture, or ask the user. Gates never correct anything toward a population norm (anatomy §6).

| Failure mode | Detection | Threshold | Action | Source |
|---|---|---|---|---|
| EXIF orientation not applied | `exif_applied` false; view RMS > 3σ; PnP roll ≈ ±90° | — | bake and re-detect | blender digest §10 🧠 |
| Missing or stripped EXIF (messengers, screenshots) | no Make, Model or f35; pixel size unlike any native aspect | — | prior from the source type (§3.3); `focal_status=prior` | community R2.2 🧠 |
| Crop or digital zoom | PixelXDimension ≠ working size; aspect ratio ∉ {4:3, 3:2, 16:9}; DigitalZoomRatio > 1 | — | σ_logf 0.08–0.10; free the principal point (σ 10 %) | community R2.5, reconstruction CAM-6 🧠 |
| Front camera (selfie) | LensModel contains "front" | — | run the mirror test; selfie distance prior; perspective evidence only | camera-perspective-distortion 🧠 |
| Near camera | z from the solve, cross-checked by f_px·63/IPD_px | warn < 1.0 m, strong < 0.8 m, < 0.6 m 2D/texture only | down-weight depth-bearing landmarks | community §9 🧠 |
| Ultrawide, face-aware warp correction | f35 ≤ 16 mm, face beyond 60 % of the half-diagonal, or off-axis > 25° | — | σ × 2 or exclude from geometry; keep for colour | community R1.7 (warp ✅, thresholds 🧠); Shih et al. 2019 |
| Small face or low resolution | face width px | warn < 250, reject < 120; iris scale needs an iris ≥ 20 px | σ floor; no iris scale; no detail layer | community R1.4 🧠, R4 ↔️ |
| Blur | variance of the Laplacian on the face crop, normalised by face width | bottom 20 % of the set | down-weight | community R1.4 🧠 |
| Blink | eye aspect ratio | < 0.2 | drop lid points | community R1.4 🧠 |
| Clipped skin | fraction of clipped skin pixels | > 2 % | no photometric or albedo use | community R1.4 🧠 |
| Expression | §3.6 | — | multipliers or drop | expression-neutralization 🧠 |
| Glasses, beard, hair, hat | user tags plus a consistency test (§3.6) | — | §3.6 table | anatomy §6, cranium-under-hair 🧠 |
| Retouch or beauty filter | §3.6 | — | σ × 2–3; never used for texture | artstation-likeness ↔️ |
| Mixed dates | DateTimeOriginal span | > 18 months warn; child tables in CHI | split into date clusters | community §9 🧠 |
| Zero or two faces | detector count with `num_faces=2` | exactly one face at score ≥ 0.6 | user picks; bystanders are never fitted | blender digest ML 🧠, ethics F1 |
| Photo not covered by consent | sha256 ∉ `photo_sha256[]` | — | block | ethics F2 |

### 3.2 Noise model

For landmark i in view v, with tangent direction t̂ taken from the neighbouring contour points:

  Σ_iv = s_v² · m(c_i, tag_v)² · R(t̂)·diag(σ_n², σ_t²)·R(t̂)ᵀ,

with each per-direction σ given by

  σ_• = max(σ̂_•(c_i)·IOD_v·√(N/N_eff), σ_tta,iv, σ_floor).

The terms are:

- **σ̂** per class in % IOD: iris 1.0; canthi, cheilia, labrale and subnasale 1.5; lid and lip contours 2 (normal) / 5 (tangent); pronasale 2.5; brows 3–5 / 6; jaw and oval 2.5 / 10–15 (landmark-detection Table 5 🧠).
- **√(N/N_eff)**, with N_eff ≈ 60–100, applies only to dense MediaPipe points that are not in the curated subset of about 100 points (landmark-detection 🧠).
- **σ_tta** is the spread over 6–10 TTA passes (reconstruction BA-2 🧠).
- **σ_floor** = max(0.5 px, k_c·u), where u = face width px/256 and k_c is 0.6 for inner points, 0.4 for the iris, 1.0 for brows and 1.5 for contour normals (blender digest ML 🧠).
- **m** is the expression multiplier (§3.6).
- **s_v** is a per-view noise scale estimated after the first BA pass:

  s_v² = clip(median_i ‖Σ_iv^{−½} r_iv‖² / 1.386, 1, 9),

  where 1.386 = 2 ln 2 is the median of χ²₂. This is a MAD-style robust scale (deformation-fitting-math 🧠), so retouched, warped or wrongly oriented views lose weight automatically. A view with s_v > 2 is flagged (🆕).

**View cap.** Each view is weighted 1/(number of views in its 15° yaw bin). No view may hold more than 40 % of the total data information, Σ tr(Jᵀ Σ⁻¹ J) (community R1.8 🧠).

This model replaces `ViewObs.sigma_px = 1.0` (≈13× too tight; landmark-detection 🧠) and the isotropic 0.006 × diagonal default.

### 3.3 Camera initialisation

**Focal evidence ladder.** The first matching rule sets the log-normal prior on f:

| Evidence | Median | σ_log | Source |
|---|---|---|---|
| Imported SfM or checkerboard calibration | value | 0.005–0.02 | reconstruction CAM-6 🧠 |
| EXIF f35 with an uncropped native size | EXIF | 0.04 | reconstruction CAM-6 🧠 |
| EXIF f35 with a crop or zoom suspected | EXIF | 0.08–0.10 | community R2.2 🧠 |
| FocalLength plus FocalPlaneResolution | computed | 0.10 | community R2.2 🧠 |
| Phone Make or Model, no focal | 26 mm | 0.25 | community R2.2 🧠 |
| Nothing | 50 mm | 0.6 | community R2.2 🧠 |

- f35 is converted on the diagonal (`focal_px_from_35mm`), noting the ≈4 % width-convention dispute (↔️).
- Intrinsics groups are keyed on (Make, Model, LensModel, f35, W, H, still/video). They get a soft tie of σ 0.02 in place of today's hard sharing (reconstruction CAM-5 🧠).
- **Distance prior** on log z: front camera 0.35 m, rear handheld 0.8 m, tele 2 m (reconstruction CAM-6 🧠, with σ read as log-σ 0.3/0.4/0.4); unknown 1.0 m with σ_log 0.7; tape-measured ±5 cm (community R2.4 🧠). Hard bounds are 0.25–10 m (blender digest C6).
- **Multi-start PnP** against the template landmarks:
  - f35 ∈ {13, 24, 26, 35, 50, 77, 85, 120, 135, 200} (reconstruction CAM-3 🧠; today's list lacks 26, 77 and 120);
  - for each focal value, start from the affine pose, a pitch-flipped pose and a yaw-mirrored pose;
  - reject solutions that fail the cheirality check (points must lie in front of the camera);
  - score with the robust cost.

  If the best two distinct poses (differing by more than 10° in rotation) score within 20 % of each other, raise `C-TWIN` and keep both for BA (🆕).
- **Off-axis faces.** Virtually rotate the ray through the face centre onto the optical axis, initialise, then rotate back (camera-perspective-distortion 🧠).
- **View order.** Start with the most frontal view that has the most visible points. Each later view is initialised by PnP against the BA consensus so far, not against the template, which reduces mean-face pull.

### 3.4 Mirrored images

For view v, let X̂ be the consensus from the other views, or the template if V = 1:

  C₀ = min_cam Σ ρ(r(cam; X̂, u)),  C₁ = the same for the flipped observation u′ = (W − u_x, u_y)_π,

where π swaps left and right labels. The test statistic is Δ_v = (C₀ − C₁)/C₀.

- **Discriminability.** The test is only possible if the face is measurably asymmetric. Let A = ½(X̂ − M·X̂_π), where M mirrors the head frame. Compute the expected cost gap g = Σ_i ‖Σ_iv^{−½} J_i A_i‖². If g < 4, return `undetermined` (🆕). A near-symmetric face seen by a noisy detector cannot be told apart from its mirror image, and the tool says so instead of guessing.
- **Decision.** Δ_v > 0.2 marks the view as mirrored (community R1.6 🧠).
  - If it is a front-camera photo, or the other views agree, flip it automatically and log the flip.
  - Otherwise, ask the user, showing both orientations side by side and prompting them to "check the parting or a mole" (likeness-mistakes 🧠).
- **All photos mirrored.** If every view is mirrored, for example a selfie-only set, geometry cannot detect it. The set is labelled `mirror: unverifiable`, the metadata and the user prompt decide, and the asymmetry-dependent claims in the ledger are marked unverified.
- Templates and scans also get a reflected Umeyama check (§3.9).

### 3.5 Robust bundle adjustment

The objective (X are the 3D landmarks; the camera, focal group, distance and jaw angle are per view):

  E = Σ_v w_v Σ_i ρ_H(‖Σ_iv^{−½}(π_v(X_i + J_i(θ_v)) − u_iv)‖; δ = 2)
    + Σ_v E_contour,v (§3.8)
    + Σ_g ((log f_g − μ_g)/σ_g)² + Σ_{v∈g} ((log f_v − log f_g)/0.02)²
    + Σ_v ((log z_v − μ_z,v)/σ_z,v)²
    + E_shape(X) (§3.7)
    + Σ_(l,r) ‖Σ_sym,lr^{−½}(X_l − M·X_r)‖² + Σ_mid (x_i/σ_mid,i)²
    + E_scale + E_pins.

- **Huber at δ = 2σ, in σ units** (reconstruction BA-5 🧠). This replaces the 3 px value in PnP and the 3σ value in BA. After convergence, drop residuals above 4σ and re-solve once. A view with more than 15 % of its points rejected is flagged.
- **Visibility.** Template normals give weight 0 at n·(−v) < cos 80°, ramping to full weight at cos 60°. Far-side oval points are dropped at |yaw| > 25° (reconstruction BA-3 🧠).
- **Symmetry.** Each pair gets its own σ: canthi 0.7–1.0, brows 1.5, alare 1.0–1.5, cheilia 1.5–2.0, gonia 2.5–3.0, ears 3–4 mm; the midline gets nasion 0.75–1.0, prn and sn 1.5–2.0, pg and me 2–3 mm (anatomy R4.2 🧠). Today's single 2.0 mm value becomes per-pair arrays.
- **Jacobians and covariance.** Rotation updates use left increments, as now. Posterior covariances come from the Schur complement over the camera blocks rather than the dense inverse once there are 100 or more landmarks.
- **Prior share.** Each landmark reports p_i = σ²_post/σ²_prior. Where ≥ 2 pose-solved views see the landmark and the prior still dominates, the cap of 10–20 % of the objective (anatomy R1.4 🧠) is enforced only in *likeness mode*: the prior σ is widened until p_i ≤ 0.2. In the default mode it is only reported.
- **Fixed cameras** (an SfM import) use triangulation, then Umeyama, then a 3D shape solve. Landmarks never move SfM cameras (reconstruction BA-12 🧠).

### 3.6 Expressions, occluders and retouching

**Expression tagging.**
- Blendshape scores are compared against the subject's own baseline b₀ = the per-channel minimum over views (landmark-detection 🧠), not against zero.
- A view is neutral if every Δb is below the landmark-detection thresholds: jawOpen 0.08, mouthSmile 0.15, eyeBlink 0.35, browInnerUp 0.2.
- It is expressive if any Δb exceeds the FACS thresholds: mouthSmile 0.25; cheekSquint, eyeWide or brow raise 0.3; eyeBlink 0.4 (anatomy §6 🧠).
- Anything in between is mild.
- Without blendshape scores (manual pins), geometric proxies are used: inner-lip gap / ch–ch > 0.04 means parted lips, so sto and li are dropped (anatomy §6 🧠); a mouth width more than 1.08× the median across views means a smile (🆕).
- After the first fit, views are re-tagged by their residual norm in an expectation-maximisation (EM) loop of at most three rounds (reconstruction BA-9 🧠).

**Multipliers m** (expression-neutralization table 🧠):

| Class | Neutral | Mild | Expressive |
|---|---|---|---|
| rigid | 1 | 1 | 1–1.5 |
| semi-mobile | 1 | 1.5–2 | 2–3 |
| mobile | 1 | 3 | drop |
| jaw-dependent | 1 | 1 if θ is fitted | 1 if θ is fitted |

**Jaw hinge.** This is the only expression parameter in the default path. It needs no external data:

  X_i(θ) = c + R_axis(θ)(X_i − c) for jaw-dependent i.

The axis runs through condyle points c_L and c_R on the template, ≈10–13 mm anterior to tragion (reconstruction BA-1 🧠). The angle θ gets prior N(1.5°, 1°) on neutral views with bounds [0°, 30°] (anatomy §4 🧠).

A low-rank ψ basis is opt-in, only through a licence-clean adapter (FLAME 2023 Open or verified MPFB expressions). In that case the neutral anchor applies: mean ψ over neutral views ≈ 0, σ 0.1 (reconstruction BA-9 🧠). If no view is neutral, mouth and lid measurements below 1 mm are suppressed and the ledger says why.

**Occluders.** Tags are set by the user with one click per photo. Defaults can be suggested, but the default path has no licence-clean detector for beards or glasses, and the tool does not pretend otherwise.

| Tag | Action | Source |
|---|---|---|
| glasses | eye-region σ × 2; no iris scale from this view; lid points under the frame are dropped. Consistency test: iris diameter / (en–ex) differs by > 3 % from the median of glasses-free views (lenses magnify ≈1–1.5 % per dioptre) | anatomy R3.4 🧠; test 🆕 |
| beard | pg, gn, me and jaw-oval points dropped; the beard outline is a one-sided outer bound; jaw region `prior-driven` unless a shaven photo exists | reference-photography-protocol 🧠, community R5.4 🧠 |
| hair over ears or forehead | ear and temple landmarks weight 0; no silhouette above the trichion; hair outline one-sided | community R1.4, blender digest S3 🧠 |
| hat | no cranium silhouette | 🆕 |
| makeup | lip and brow borders σ × 2 | artstation-likeness 🧠 |

**Retouching and beauty filters.** Three independent tests:

1. **EXIF `Software`** matches a list of known editors (🆕).
2. **Skin-smoothness index.** SSI_v = E_hf(cheek patch)/E_hf(brow and iris patch), the ratio of band-pass energy at matched mm/px. SSI_v < 0.5 × the set median raises `Q-FILTER` (🆕).
3. **Geometric signature.** Regress the whitened residuals on two fixed patterns: radial-outward about the eye centres (eye enlargement) and inward along the jaw normal (jaw slimming). A t-statistic > 3 raises `Q-RETOUCH`, sets σ × 2–3 and excludes the view from texture (artstation-likeness ↔️; test 🆕).

All three are relative to other views. A filter applied to the only photo cannot be detected geometrically, and the ledger says so.

**Wide-angle warp diagnostic.** Fit a per-view k₁ (prior σ 0.02, used only for testing). On a phone JPEG, where k₁ should be 0 (reconstruction CAM-1 🧠), |k₁/σ_k₁| > 3 raises "non-pinhole processing suspected". The radial residual is also regressed on ρ_i·δ_i; a slope implying more than 5 % magnification error raises "distance or focal wrong" (community R2.8 🧠).

### 3.7 Licence-clean shape prior

No permissive statistical head model with a large population is confirmed to exist (reconstruction §12). The default is therefore layered and honest about what it is:

1. **Baseline (M5).** An independent per-landmark Gaussian about the template landmarks. σ uses the anisotropic (N, 3) arrays at 1.0–1.5 × the population SD, falling back to 8 mm (anatomy R4.1 🧠). Ratio priors (anatomy R4.3) are diagnostics only.
2. **Experimental basis.** X = μ + B·c with c ~ N(0, I). B comes from a mass-weighted SVD of the CC0 MPFB2 local face targets, K 40–80 (open-template-head-kit data 🧠). Its variances come from an "anthropometric morphable model": 2,000–5,000 sampled heads whose measurements match published norms, keeping 95–99 % of the variance (same table 🧠). The method is unproven, so B stays `experimental` until the test bed shows that it lowers held-out error *and* keeps interval coverage (§5.3).
3. **Opt-in.** FLAME 2023 Open loaded from a user-supplied path with a SHA-256 pin and attribution (CC-BY-4.0; contents unverified 📄). Other FLAME versions and BFM are research-only; enabling one marks the result `commercial_ok=false` (reconstruction LIC-1).

**Gates.** ‖c‖² above the χ²_K 99.9 % quantile, or any |c_i| > 3, means an implausible shape (reconstruction MM-5 🧠). ‖c‖² < K − 2√(2K) means "pulled toward average" (community R5.8 🧠).

**Not fabricated.** Template landmark tables come from two independent annotators clicking in Blender, accepted when they agree within 1 mm (🆕). MediaPipe index maps come from detector-semantics calibration: render the template from 20–50 cameras, run the detector and store each index's mean landing point as barycentric coordinates (landmark-detection 🧠). Both are produced offline by maintainers and committed with provenance. CI checks only hashes, schemas, whether the L/R permutation is an involution, and that midline indices map to themselves.

### 3.8 Contours, silhouettes, profiles and hair

**Edge-snap tracer** (`contour_trace.py`). It takes a coarse polyline of at least 5 clicks, or detector oval points.

- Sample M stations along the line, each with an offset k ∈ [−L, L] along the normal, where L = 3 % IOD.
- The cost is C = Σ_j −g_j(k_j) + λ Σ_j |k_j − k_{j−1}|, where g is the Gaussian-smoothed gradient magnitude (σ 1 px) and λ = 0.2·median(g) (🆕).
- The minimum is found by dynamic programming (Viterbi) in O(M·L²). The result is deterministic and has no learned weights.
- Each sample gets σ_n = max(1 px, 1/√(curvature of the DP cost)).

The optional Segment Anything (SAM, Apache-2.0) backend runs in the external helper (ethics §5).

**Sliding residuals.** For each mesh occluding-contour vertex projection p_j, find the nearest outline segment and use r_j = n̂_seg·(p_j − q)/σ_n. Associations are recomputed every iteration (reconstruction BA-4, blender digest S1 🧠). This is combined with the existing outline-to-vertex direction in both directions, with 10 % trimming, so the contour cannot collapse onto a few vertices. The trim distance becomes 5 % IOD instead of the fixed `max_dist_px = 60` (🆕).

**One-sided masks** for hair, beard and hat. r_j = max(0, d_mask(p_j) + m)/σ, where d is the signed distance to the mask outline (positive outside) and m = 0–3 mm (community R5.4 🧠). The hinge weight is 10 × skin (cranium-under-hair data 🧠). The scalp must stay at least 2 mm inside the hair hull (blender digest W7 🧠). Cranium σ comes from the visual-hull overshoot: 7.8 mm with 4 views around, 1.9 mm with 8 (cranium-under-hair data, arithmetic). Vault priors come from the same table.

**Profile routing.** In views with |yaw| > 60–70°, detector points are discarded (landmark-detection 🧠) except user pins at σ 1 % IOD for g, n, prn, sn, ls, li and pg (blender digest S4 🧠). The traced profile is the main depth signal (reconstruction SIL-1 🧠).

**Acceptance.** Profile error ≤ 1–1.5 mm at the nose tip and chin (reconstruction SIL-3 🧠). Mean contour distance ≤ 1 % of face height on the unoccluded jaw (blender digest S5 🧠). If interior points fit but contours and ears do not, the message is "f and z wrong", not "shape wrong".

### 3.9 Template warp and detail

| Stage | Operation | Advance when | Source |
|---|---|---|---|
| A | Umeyama, proper *and* reflected; reflected RMS < 0.5 × proper means "mirrored source", never auto-flipped; 7-landmark RMS > 10 mm means wrong axes | always | blender digest W2 🧠 |
| B | RBF with φ = r: (Φ − Λ)w + Pa = y, Λ = diag(α·σ_i²), α = 10⁻² in normalised units (sign already fixed in `rbf.py`) | landmarks < 2–3 % IOD | reconstruction MM-8 🧠, community R5.2 🧠 |
| C | Bilaplacian on the displacement with per-vertex stiffness: lid margins 3.0, lips 0.3, forehead 0.5, ligament strips 3–5; constraint weight 10³; offsets capped at 3–5 mm unless ≥ 2 views agree | RMS gain < 1 %/iteration | anatomy R5.9, reconstruction MM-9/10 🧠 |
| D | Silhouettes via `ReducedDeformer`; no landmark may move > 0.5 mm | contour ≤ 1 % face height | community R5.2 🧠 |

**Gates after every stage.**
- Triangle det J > 0.2 and no normal flips (reconstruction MM-11 🧠).
- Lid–globe gap within [0, 0.3] mm (blender digest §4 🧠).
- Mirror RMSD between 0.3 and 1.5 mm (anatomy §6 🧠).
- Targets are never symmetrised (anatomy R5.9).

**Detail refinement** is off by default. It is allowed only from neutral, unfiltered views above the mm/px gates (fine lines ≤ 0.08 mm/px) and only where at least 2 views agree (anatomy R5.11 🧠). Otherwise the detail is labelled `synthetic`.

### 3.10 Uncertainty, observability and the claims ledger

- **Linear propagation.** For a fixed template, stages B and C are linear in the targets: V = V₀ + A·(X − X₀). Solving once per unit target gives A, and each vertex gets
  Cov(V_j) = Σ_ab A_ja A_jb Cov(X_a, X_b) + σ²_res,region·I.
  The region residual σ is lids 1–1.5, nose 2–3, cheeks 2.5–4, ears 3–5, scalp 3–6, neck 5–10 mm (open-template-head-kit data 🧠). A finite-difference test checks this exactly.
- **Reported σ.** σ_rep² = σ²_post·max(1, κ²) + σ²_bias.
  - κ is the leave-one-view-out calibration ratio: observed held-out error divided by predicted error.
  - σ_bias is 1–3 mm per landmark class until a detector-semantics map exists. This is bias that does not average out across views (reconstruction principle 5 🧠).
  - The Hessian alone is optimistic, so it is never shown without these two terms.
- **Status** comes from k = 1 − σ²_post/σ²_prior:
  - *measured* when k ≥ 0.8 (anatomy §6 🧠) *and* the coverage rule holds;
  - *constrained* when 0.5 ≤ k < 0.8;
  - *prior-driven* when k < 0.5 (🆕);
  - *unobserved* when no view sees the region.
- **Coverage rules.**
  - Depth claims need ≥ 2 views at least 30° apart (blender digest C7 🧠).
  - Nose and chin projection count as measured only with a front view plus one at |yaw| ≥ 60°; the jaw underside needs a low view (community R5.9 🧠).
  - Ears need |yaw| ≥ 30° and pitch fixed by ≥ 2 views (community R3.3 🧠).
- **Camera status.** Focal length is estimated only if σ(log f) < 0.10, otherwise held at the prior and reported (blender digest C2 🧠). A σ above 0.8 × the prior σ means "focal from prior" (reconstruction CAM-7). P = 100 mm/z is reported per view.
- **Scale status.** *measured* (ruler or caliper, overriding everything else; anatomy R3.4), *iris* (sharp limbus, no glasses), *IPD prior*, or *proportions only*. References that disagree by more than 1 % are flagged (reconstruction BA-10 🧠).
- **Next-best photo.** For each candidate yaw and pitch in a 15° grid, a simulated view (landmarks visible from that pose, σ from §3.2) is added to the Hessian. The tool recommends the pose that most reduces the summed σ over prior-driven regions weighted by perceptual importance (benchmarks-metrics Table 6 weights 🧠).

### 3.11 Texture projection

Texture projection runs only when geometry passes: reprojection median ≤ 1.5 px and max ≤ 3 px (blender digest T2 🧠), with `TEXTURE` consent and `rights_basis ≠ unknown` (ethics §3).

- A numpy z-buffer runs at 1,000–2,000 px with depth tolerance max(1 mm, 2σ_geom).
- View weights: w = vis·cos²θ·footprint·edge, faded from 60° to 75°, with 5 px edge erosion (reconstruction TEX-1/2 🧠).
- Per-view gains in linear RGB, with log-gain σ 0.3 when exposure was automatic (TEX-3 🧠).
- Two-band blending by default, split at 3 mm (TEX-4 🧠).
- **Excluded from albedo:** views flagged for filtering, retouching, warping or > 2 % clipping, and views from a different date cluster.
- Specular highlights are rejected through a median over ≥ 3 views.
- Texture is never mirrored (anatomy R5.11).
- Maps are 2048 px for phones (TEX-7 🧠). Outputs are a linear EXR plus confidence and source-view maps.
- Without a colour chart, the output is labelled "absolute albedo unknown".

---

## 4. Blender add-on design

**Package.** The extension lives in `blender_ext/face3d_head/` and contains:

- `blender_manifest.toml`
- `__init__.py` (registration and `compat.py` probes, < 100 ms)
- `bridge.py` (the only module that converts between bpy and numpy)
- `ops_project.py`, `ops_photos.py`, `ops_solve.py`, `ops_fit.py`, `ops_texture.py`, `ops_export.py`
- `ui_panels.py`, `overlays.py`, `jobs.py`, `keys.py`
- `face3d/` (the engine, vendored by `tools/build_extension.py`)
- `assets/template/` (CC0 kit only)
- `LICENSE`, `NOTICE`

**Operators** (all `REGISTER|UNDO` unless they only read):

| Operator | Purpose | Runs |
|---|---|---|
| `face3d.project_new` | ConsentRecord form; project folder under the user's chosen path | main |
| `face3d.photos_add` | Hash files, read EXIF/HEIF-EXIF, bake orientation into working copies, strip GPS (ethics F12) | main |
| `face3d.landmarks_import` / `face3d.detect` | Import JSON, or run the configured helper or wheel | job |
| `face3d.pin_edit` | Modal pin placement in a photo's camera view; σ from zoom | modal |
| `face3d.trace_contour` | Modal coarse polyline, then edge snap (§3.8) | modal + main |
| `face3d.triage` | QA cards and tags | job |
| `face3d.solve` / `face3d.fit` | §3.3–3.10 | job |
| `face3d.apply_result` | Cameras, keys, attributes; refuses if the topology hash differs or the object is in Edit or Sculpt Mode (blender digest K1/K4) | main |
| `face3d.bake_for_sculpt` | Duplicate the object, bake the key mix, clear keys, add Multires level 2–3 (blender digest K5, reconstruction SK-3 🧠) | main |
| `face3d.project_texture`, `face3d.review_sheet` | §3.11, §5.5 | job |
| `face3d.prepare_sharing`, `face3d.export` | Purge biometric leftovers (ethics F9); licence and consent gates; provenance | main |

**Panels** live in View3D › Sidebar › *Face3D*:

- Project & Consent
- Photos: a UIList with QA badges, tag toggles, include/exclude and mirror state
- Solve: tier, focal status per group, z and P per view
- Fit: stage progress and gates
- Review: claims ledger, LOVO, worst landmarks, next-best photo
- Export: licence and consent status, blocking reasons

**Overlays** are drawn with `gpu` draw handlers through the active photo camera:

- landmarks with σ ellipses;
- residual arrows exaggerated ×5;
- rejected points in red;
- traced outline against the projected silhouette;
- a flipped thumbnail for the mirror prompt.

In 3D, the attributes `face3d_sigma_mm` and `face3d_status` drive viewport colour, and region face sets drive masks.

**Undo and state.** Engine state lives in hashed sidecars in the project folder, not in the undo stack. Objects carry a `face3d_uuid` custom property and are fetched again by it after an undo. Jobs record the target's topology hash, and `apply_result` refuses to write if it has changed.

**Background jobs.**
- `jobs.py` writes inputs (JSON plus `.npy`) under `extension_path_user` and spawns `[sys.executable, "-I", launcher.py, job_dir]`. The launcher puts the vendored engine on `sys.path`.
- Results are polled with `bpy.app.timers` at 0.1 s and applied with ≤ 20 ms of work per tick (blender digest A5 🧠).
- Cancelling kills the process. A worker crash cannot lose sculpt work.
- When `bpy.app.background` is true, the same pipeline runs synchronously for headless CI.

**Shape keys** (blender digest K2/K3 🧠):

| Key | Content |
|---|---|
| `Basis` | Template mean |
| `F3D_stageB`, `F3D_stageD` | Diagnostic fitting stages, default 0 |
| `F3D_ID_v<n>` | The likeness, written with `from_mix=False` |
| `artist` | Sculpt layer, kept as Δ against the current ID across refits |

The `slider_max` of `F3D_ID` is 1.5. Per-view expression diagnostics are stored as data and become shape keys only with `RIG_ANIMATE` consent (ethics F4). Shape keys are never applied in place, and the delivery mesh is never remeshed.

**Manifest** (store build):

```toml
schema_version = "1.0.0"
id = "face3d_head"
version = "0.1.0"
name = "Face3D Head Fitter"
tagline = "Fit a sculpt-ready head to photos of a consenting person"
maintainer = "Face3D contributors <maintainers@example.invalid>"
type = "add-on"
blender_version_min = "4.5.0"
license = ["SPDX:GPL-3.0-or-later"]
tags = ["Sculpt", "Mesh", "Camera"]

[permissions]
files = "Read reference photos and write project sidecars and textures"

[build]
paths_exclude_pattern = ["__pycache__/", "*.pyc", "tests/", "*.blend1"]
```

- **Store build.** No wheels, no `network` permission, CC0 assets only (blender digest L1). Engine files carry MIT SPDX headers inside a GPL-3.0-or-later distribution (ethics A1).
- **Full build** (GitHub releases). It adds per-platform MediaPipe wheels and `platforms`, plus a NOTICE entry for the Apache-2.0 model. Whether this complies with the extensions platform rules is unconfirmed (↔️), so it is never the store build.
- **Minimum version.** `blender_version_min` is the oldest line CI tests (blender digest Q3); 4.2 LTS left support in July 2026.
- **Detector helper.** `tools/detect_mediapipe.py` runs in any user Python, so the cp311/cp313 wheel lag stops mattering (blender-python-ml-deps 🧠).

---

## 5. Validation and QA

### 5.1 Test pyramid

1. **Unit and oracle tests** (pytest, CPython only).
   - Jacobians match numeric ones.
   - Noiseless problems converge to an RMS below 10⁻⁶.
   - Camera ↔ Blender round trips hold to 10⁻⁶·s; OBJ round trips to < 2 µm (blender digest Q1/Q2 🧠).
   - Schema round trips and policy-gate tables.
   - Each QA gate is tested on synthetic arrays: a blurred checker, a clipped ramp, a smoothed noise patch.
2. **Scenario test bed** (`face3d/testbed`, seeded). A scenario is a subject × a capture protocol × a detector model × a fault set.
   - **Subjects:** template plus a smooth identity field plus 0.8 mm RMS asymmetry (facial-asymmetry 📄), using the existing `random_subject`.
   - **Capture protocols:** studio ring, rear phone handheld, selfie set, camera-roll mix.
   - **Detector model:** class σ from §3.2, a *fixed per-index bias field* of 1–3 mm that is the same in every view (reconstruction principle 5 🧠), 5 % gross outliers and a TTA spread.
   - A small numpy rasteriser renders masks and procedural-texture images for the contour and image-QA tests.
3. **Bridge tests.** Pure functions: axis and unit mapping, the key-layout planner, a manifest lint through `tomllib` (licence, tagline ≤ 64 characters, no numpy wheel, no `network` in the store build) and the zip builder. A headless Blender script (`blender -b --factory-startup --python-exit-code 1`) is provided for CI elsewhere.
4. **Real-data bed.** See §5.4.

### 5.2 Fault-injection matrix

These targets are 🆕 starting gates. The first M1 run records the current engine as the baseline.

| Fault injected | Injector | Must raise | Required | Degradation check |
|---|---|---|---|---|
| One mirrored view of N ≥ 3 | flip u, permute labels | `Q-MIRROR` | TPR ≥ 0.95 at asymmetry ≥ 0.8 mm; FPR ≤ 0.02 on clean sets; `undetermined` on symmetric subjects | shape error ≤ 1.1× clean |
| Orientation not baked | rotate by 90° | `Q-ORIENT` | TPR ≥ 0.99 | — |
| Wrong EXIF (±30 % crop), missing EXIF | perturb or drop f35 | `C-FOCAL-PRIOR` when unobservable | focal error < 5 % when views span ≥ 60° (community R8.4 🧠) | shape ≤ 1.2× clean |
| Selfie set at 0.35 m | protocol | `Q-SELFIE`, tier ≤ B | z within 15 % | perspective model beats ρ = 0 by ≥ 30 % on nose width |
| Jaw open 5–15°; smile pattern | displace mobile points | expressive tag | TPR ≥ 0.9 | rigid-region error ≤ 1.1× clean |
| Beauty warp: eyes +6 %, jaw −4 % | local radial warps | `Q-RETOUCH` | TPR ≥ 0.8 with ≥ 3 clean views | identity bias ≤ 0.5 mm |
| Face-aware wide-angle warp | stereographic remap off-axis | risk gate or k₁ test | TPR ≥ 0.8 | — |
| Glasses, beard, hair | σ and bias on tagged classes; masks | per-tag actions | jaw `prior-driven` under a beard | no hair-as-cranium: scalp inside the hull |
| Low resolution (face 150 px) | rescale | `Q-SMALL` | — | σ_rep coverage holds |
| Mixed dates | cheek and jaw drift of 2 mm | `Q-DATES` | — | — |

### 5.3 Honesty metrics

Uncertainty is part of the product, so it is tested like any other output.

- **Interval coverage.** For regions labelled *measured*, the fraction of vertices with |error| ≤ 1.96·σ_rep must be between 0.90 and 0.99 (🆕).
- **False confidence.** Regions labelled *measured* whose RMS exceeds 2× the target (benchmarks-metrics Table 6 🧠) must stay at or below 5 % (🆕).
- **Flag precision.** On clean scenarios, at most 1 spurious warning per 10 photos (🆕), because alarm fatigue is a failure mode too.
- **Promotion rule.** A new prior, term or default becomes the default only if the scorecard shows lower held-out error *and* no loss of coverage.

Shape is scored with `face3d/eval`: exact point-to-triangle distance, both NoW-style and landmark-only alignment, median, p95, F@1/2 mm, per-region bias, scale error and configuration RMS (reconstruction EV-1/2 🧠). The chamfer formula is always printed.

### 5.4 Real-data bed

The real-data bed is not in CI. It starts with 1–3 consenting sitters (benchmarks-metrics 🧠), growing to about 10, with spread across age, skin tone, beards, glasses and hair types. Each sitter provides:

- a reference scan, repeated 10 minutes later to measure the floor;
- the protocol ring;
- a rear-phone set;
- a selfie set;
- a dated camera-roll set.

Data is held under consent and retention rules (ethics §4). Only aggregate metrics are committed, and a leakage guard keeps tuning sitters out of reporting. This bed calibrates every 🧠 and 🆕 σ and gate, the per-class bias terms, the detector-semantics map and the six-face lineup (target ≥ 80 %; benchmarks-metrics 🧠).

### 5.5 Likeness checks shown to the artist

- **Per-camera sheet** (community R8.1 🧠): photo, clay render, 50 % overlay, difference, silhouette with chamfer, flipped, blurred and 64 px thumbnail versions.
- **Error lists:** worst landmarks first in % IOD; LOVO per view (flag held-out > 2× in-sample; reconstruction principle 15 🧠).
- **Sheets and lints:** a caliper sheet (Δ > 2 mm for tier A landmarks); canon z-scores in art vocabulary; a likeness lint that flags only |model − photo| > 2σ_photo and never pulls a supported feature toward the mean (community R8.2 🧠); a mirror-RMSD check that warns "over-symmetric" below 0.3 mm.
- **Approval renders** from about 1 m and from the sitter's favourite photo camera, because people know their face from mirrors and front cameras (camera-perspective-distortion ↔️).

---

## 6. Milestones

Each milestone ships on its own and is tested here with synthetic data.

- **M1 – Test bed and evaluation first.** Adds `face3d/eval` and `face3d/testbed`, the scorecard JSON and `python -m face3d testbed --suite smoke`.
  - Point-to-triangle distance matches brute force to 1e-9.
  - Alignment recovers a known similarity.
  - The baseline scorecard of the current engine is committed.
  - The smoke suite runs in ≤ 90 s.
- **M2 – Ingest, schemas and QA.** Adds the EXIF extensions, HEIF-EXIF, PNG, orientation operations, schemas, policy gates, image and photo QA, the focal ladder, intrinsics groups and a `triage` CLI.
  - Golden EXIF and HEIF byte fixtures parse correctly.
  - Every §3.1 gate fires on its synthetic fixture and stays silent on clean ones.
  - Running without consent is refused (ethics F3).
  - Results are deterministic across runs.
- **M3 – Robust cameras and BA.** Adds the noise model, multi-start PnP with the twin flag, distance priors, soft focal ties, visibility, Huber 2σ with 4σ rejection, per-view scale, the view cap, observability, LOVO, the mirror test and the radial signature.
  - The z sweep (0.25–5 m) and f35 sweep (13–200 mm) meet the §5.2 rows for cameras, mirroring and orientation.
  - Unobservable focal length is reported.
  - The existing tests still pass, with updated defaults.
- **M4 – Nuisances.** Adds expression tagging and multipliers, the jaw hinge, an optional basis adapter interface, occluder actions, retouch and warp diagnostics, and date clusters.
  - The expression, retouch, warp and occluder rows of §5.2 pass.
- **M5 – Template kit, warp and uncertainty.** Adds the template sidecar and kit builder (CI uses a procedural stand-in head; the real CC0 kit is built offline with recorded hashes), the registry, staged warp with gates, region stiffness, the fold gate, vertex σ propagation and the claims ledger.
  - The finite-difference check of σ propagation passes.
  - The coverage metric lies in [0.90, 0.99] on the smoke suite.
  - The experimental basis stays off unless it wins on the scorecard.
- **M6 – Contours and silhouettes.** Adds the edge-snap tracer, sliding residuals, one-sided masks and profile routing.
  - The tracer lands within 1 px of rendered mask edges.
  - Profile error at the nose tip and chin is ≤ 1.5 mm on synthetic profiles.
  - No scalp vertex lies outside the hair hull.
- **M7 – Blender extension MVP.** Adds the manifest, bridge, jobs, operators, panels, overlays, key planner and build script.
  - Bridge pure-function tests pass.
  - The manifest lint passes.
  - The zip contains no wheels or non-CC0 assets.
  - A headless script is supplied for the 4.5 and 5.2 LTS lines.
- **M8 – Detector helper, texture and review.** Adds `detect_mediapipe.py` with its JSON contract (tested with a fake backend), the numpy z-buffer, projection and blending, review sheets and export provenance.
  - Synthetic gain recovery within 2 % (reconstruction TEX-8 🧠).
  - No colour from occluded texels.
  - Filtered views are excluded.
- **M9 – Calibration release.** Builds the real-data bed (§5.4) and publishes a calibration report that moves σ values and gates from 🧠/🆕 to measured. It is not testable in CI; the tooling is.

---

## 7. Risks and deliberate omissions

**Risks**

- **No proven licence-clean statistical shape model.** The per-landmark baseline is weak in depth, and the CC0-target basis is an untested idea. Mitigation: the coverage rules and next-best-photo prompts push users toward profiles instead of relying on the prior.
- **Uncalibrated values.** About 70 % of the values cited here are 🧠, and the 🆕 gates are ours. Until M9 they are starting points, and the UI says so.
- **Synthetic detector models are not real detectors.** Bias fields and failure shapes may not match MediaPipe's real errors. The M9 detector-semantics calibration is the remedy.
- **Mirroring and filters cannot be fully detected.** A near-symmetric face, an all-selfie set or a filtered single photo cannot be verified geometrically. We report `undetermined` rather than guess.
- **Packaging.** MediaPipe wheels for cp313, the store's stance on bundled models (C7/C8), HEIC decoding inside Blender, and the 5.x shift and attribute names are all open. The external helper and the manual-pin path keep every stage working regardless.
- **Performance.** The dense Hessian is fine up to about 150 landmarks × 12 views. Larger problems need the Schur complement (M3).
- **Over-flagging.** Alarm fatigue would make users ignore real flags. Flag precision is measured (§5.3).

**Deliberately left out of the default path**

- **Monocular depth, generative fill, Gaussian avatars and photometric shape terms.** Their outputs are not measurements (reconstruction principles 12–14). They may come later only as opt-in terms behind the test bed.
- **Automatic beard, glasses and hair segmentation.** No licence-clean default model exists. User tags plus an optional SAM helper replace it.
- **Identity embeddings.** These are evaluation only and opt-in. Most weights are NC, and embeddings are never persisted (ethics).
- **Automatic correction of retouched photos.** We down-weight them and never "un-filter".
- **Phone video depth, ears beyond silhouette plus prior, hair grooming, teeth and eyelid detail.** These are later topics. The gap-topic notes for phone video, ears and guided workflow were not available when this was written.
- **Symmetrising, anonymising, 1:N matching and URL import.** These are never built (ethics F17, F18, A5).
