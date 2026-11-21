# Maintainer tools

These scripts in `tools/` build, calibrate and recalibrate the data files the engine relies on: the MediaPipe scheme, template-kit landmark embeddings and the landmark prior. They implement WP-14 (DESIGN 2.2 layer L9, 2.3, 3.2, 8 M3b/M7). WP-24 runs them offline with real inputs.

Ground rules:

- **The engine never imports these tools.** They use the standard library, numpy and `face3d`. Run them from a repository checkout: each script puts the repository root on `sys.path`.
- **Nothing here downloads anything.** Models, CSV files and samples are always supplied by the user or maintainer, by path (DESIGN D-28, eth A3/A4, C8).
- **No real-person data enters the repository.** See [What must never be committed](#what-must-never-be-committed).
- **Determinism.** Every random draw is seeded (`--seed`), and JSON output is written with sorted keys, so a rebuild gives the same bytes.
- **Testing.** `tests/test_tools.py` exercises every tool on synthetic inputs, with a fake `mediapipe` module and the procedural CC0 head. The sandbox has no MediaPipe, Blender or network.

| Tool | Runs where | Reads | Writes |
|---|---|---|---|
| `build_scheme_mediapipe.py` | repository checkout, any Python ≥ 3.11 with numpy | `research/data/landmark-index-correspondence.json` | `face3d/schemes/mediapipe_478.json` |
| `detect_mediapipe.py` | the **user's own Python**, with user-installed `mediapipe`, `Pillow` and optionally `pillow-heif` | photos or renders; a user-supplied `.task` model with its SHA-256 | `<stem>.landmarks.json`, `<stem>.mediapipe_extras.json` and, with `--png-out`, `<stem>.png` |
| `calibrate_scheme.py` | maintainer machine, after Blender renders of the template | template kit, render records, detections of the renders | updated kit, report JSON, optionally the updated scheme |
| `recalibrate_prior.py` | maintainer machine | ANSUR II CSV, or a landmark-sample NPZ | a `face3d.landmark_prior` JSON, e.g. `face3d/data/landmark_prior_v2.json` |

## Licence rules

- **Bundling: CC0 only.** The extension zip carries only CC0 assets (DESIGN D-28; ethics C7). Template kits report this as `bundle_ok`, which is true only for `licence == "CC0-1.0"`.
- **The MediaPipe `.task` model is never bundled.** The user supplies it with its SHA-256. `detect_mediapipe.py` refuses a model whose hash does not match, then passes the verified bytes to MediaPipe, so the checked file is the file that runs (eth F15). The MediaPipe code is Apache-2.0. The weights licence is marked "verify per release (contested)", and `commercial_ok` stays `null` until someone verifies it.
- **`mediapipe_478.json` is released as CC0-1.0, but store acceptance is contested.** The file holds index semantics derived from the Apache-2.0 connection sets plus expert candidates. Whether an extension store accepts derived index tables is contested (ethics C7). If the store refuses them, ship the two build tools and build the map on the user's machine on first run (WP-24).
- **ANSUR II CSV files are user-supplied and never bundled.** Only derived aggregates are written: pooled per-sex SDs and correlations, and refitted factor sigmas. Before choosing `--licence CC0-1.0`, the maintainer confirms that the source terms allow that.
- **FLAME 2023 Open is CC BY 4.0, which is not CC0.** A prior derived from FLAME samples needs `--attribution` and a matching `--licence` such as `CC-BY-4.0`. Such a prior cannot be bundled. Users download and point to it. Other FLAME versions are non-commercial: never use them.

## What must never be committed

- Photos of real people, their PNG working copies, and the `*.landmarks.json` / `*.mediapipe_extras.json` produced from them. These files are biometric geometry (DESIGN 3.3, D-25, D-26; eth A8). Detector output on real photos belongs in the project's session cache only.
- Meshes, fitted heads, embeddings or any other geometry of a real person.
- The raw inputs of recalibration: ANSUR II CSV files, FLAME files and landmark samples. Their SHA-256 values in the provenance block record them instead.
- Model files (`*.task`).

Only these may be committed:

- synthetic fixtures;
- CC0 assets, such as the procedural head and a CC0 template;
- aggregate statistics computed from consented or public data (pooled SDs, factor sigmas, calibration reports of template renders).

`calibrate_scheme.py` accepts only render records that declare `"source": "template_render"`, and its report never contains detections.

## 1. `build_scheme_mediapipe.py`: the MediaPipe scheme file

```sh
python3 tools/build_scheme_mediapipe.py [--research research/data/landmark-index-correspondence.json] \
    [--out face3d/schemes/mediapipe_478.json]
```

The tool builds the WP-03 scheme document from the research tables:

- `mediapipe_semantic_points` gives the anatomical candidates and the kinds taken from the `type` column.
- `mediapipe_region_polylines` gives the curve, contour and brow kinds, and the polylines.
- `mediapipe_mirror_pairs` gives 70 `[right, left]` pairs, with `mirror_complete: false`.
- `default_sigma_by_kind` and `detector_vs_definition_offsets` are copied as reference blocks (mm, 🧠).

Before writing, the tool checks the polylines against `set_sizes`: oval 36, lips 40, eyes 16 each, brows 10 each, contour union 128, midline 28, 478 points in total. It then loads the result through `face3d.model.registry.Scheme` and validates the mirror involution.

Expected output: 478 points, all `verified: false`. Badges come from the research status of each row: 🧠 knowledge, ↔️ contested, 📄 sourced. Generic points get 🆕.

Anatomical ids are given only for g, n, prn, sn, ls, li, sl, pg, me and the L/R pairs of al, ch, en, ex, ps and pi. Index 10 never maps to trichion. `sto` is not mapped, because it is the mean of indices 13 and 14.

The iris points 468–477 are named `iris_a_*` and `iris_b_*`. They have side `geometric` and no anatomical id, and they reach `p` only through `lr_groups` with `rule: "geometric"`. Each group also stores the contested research side as `provisional_side`. Nothing uses that value to assign a side; calibration compares against it. The two iris polylines follow the same rule: they are renamed `iris_a_centre_then_ring` and `iris_b_centre_then_ring`, have side `geometric`, and keep the research side only as `provisional_side`. In `mirror_pairs` (`[right_index, left_index]`), the iris-centre pair `[468, 473]` carries no side meaning; it only says the two centres mirror each other. The file also has `z_policy: "ignore"`.

Rerunning the tool on an unchanged research file gives byte-identical output, which the acceptance test checks. Whenever the research table changes, rebuild and commit.

## 2. `detect_mediapipe.py`: detection in the user's own Python

```sh
python3 tools/detect_mediapipe.py --model face_landmarker.task --model-sha256 <hex> \
    --images IMG_0412.HEIC IMG_0413.JPG --out work/landmarks [--tta 8] [--num-faces 2] [--png-out] [--seed 0]
```

Run it in a Python where `pip install mediapipe pillow` (and optionally `pillow-heif`) has been done by the user. Never run it inside Blender's Python. `mediapipe` and `Pillow` are imported only inside `main()`, so the module imports without them.

**Model check.** The tool reads the `.task` file once and compares its SHA-256 with `--model-sha256`. On a mismatch it exits with status 2 and writes nothing.

**Loading and orientation.** Pillow opens the image and `ImageOps.exif_transpose` bakes the EXIF orientation, so `image.orientation_applied` is true. HEIC needs `pillow-heif`; without it the photo is skipped with "convert the photo to PNG". `image.sha256` hashes the original file, and `image.wh` is the size after orientation.

**Detection.** The detector is `FaceLandmarker` from the Tasks API, in IMAGE mode, with blendshapes and transformation matrices. It runs on a copy whose long side is at most 2048 px. Landmarks map back with the corner convention `u = x·W`, `v = y·H` (DESIGN 3.1). MediaPipe z is dropped.

**TTA.** `--tta N` runs N passes: the plain image, then N−2 seeded similarity jitters (scale ±2 %, shift ±1 %), then one horizontal flip.

- Labels in the flip pass are permuted with the scheme's mirror permutation.
- Points without a known mirror are excluded from the flip pass: those neither in a pair nor on the midline.
- Output `uv` is the per-point median over passes.
- `tta_spread_px` = 1.4826 × the median radial deviation from that median. For isotropic noise this is about 1.75 σ, so it errs on the conservative side.
- `--tta 0` writes the plain pass unchanged.

**Output.** One `face3d.landmarks` file per photo, with scheme `mediapipe_478`. The detector block is `{backend: "mediapipe-tasks", version, model_sha256, licence, commercial_ok: null, is_ml: true, ...}`.

- All faces are written in MediaPipe's order, with blendshapes. The user or engine picks the subject (eth F1).
- The Tasks API reports no face confidence, so `score` is the fraction of TTA passes in which that face was found.
- MediaPipe returns all 478 points even when they are occluded; the engine's visibility weighting handles them (DESIGN 4.8).
- Transformation matrices go to `<stem>.mediapipe_extras.json`, which the engine does not use.
- `--png-out` writes the oriented image as a PNG working copy with no EXIF.

The exit status is 1 when any image was skipped.

## 3. `calibrate_scheme.py`: render-and-detect calibration

This step runs offline on the maintainer's machine (WP-24 M3b, step 5).

1. **Render the template kit in Blender.** Use 20–50 calibrated views: yaw −60…+60° in 10° steps, pitch −15/0/+15°, key light at 0/45/90°, an 85 mm-equivalent lens at 1.5 m (*landmark-index-correspondence*, "Calibrate detector semantics"). Use at least three different heads before you trust a detector bias.
2. **Run `detect_mediapipe.py` on the renders.** Use `--tta 0` or the default TTA.
3. **Write the render records file.**

   ```json
   {"format": "face3d.render_records", "version": 1, "source": "template_render",
    "renders": [{"K": [[f,0,cx],[0,f,cy],[0,0,1]], "R": [[...]], "t": [..], "W": 1920, "H": 1080,
                 "detections": "r00.landmarks.json", "face_index": 0}]}
   ```

   `K`, `R` and `t` use the engine's OpenCV convention: `X_c = R·X + t` in mm, square pixels, corner-origin pixels. Compute them from a Blender camera with `sensor_fit = HORIZONTAL` as follows:

   - **Intrinsics.** `f = lens·W/sensor_width`, `cx = W/2 − shift_x·W`, `cy = H/2 + shift_y·W` (DESIGN 3.1).
   - **Coordinate maps.** Engine mm map to Blender metres as `X_bl = 0.001·P·X` with `P = [[1,0,0],[0,0,−1],[0,1,0]]`. For `[R_bc | t_bc] = camera.matrix_world.normalized().inverted()` and `F = diag(1, −1, −1)`, the engine values are `R = F·R_bc·P` and `t = 1000·F·t_bc`. Use the normalized matrix because object scale does not affect the projection, and a camera parented to the 0.001-scaled empty of DESIGN 3.1 inherits that scale.
   - **Check.** Before a full run, project one known template vertex and compare it with the render.

4. **Run the tool.**

   ```sh
   python3 tools/calibrate_scheme.py --kit assets/template/realhead-v1.kit.json --renders renders/records.json \
       --scheme mediapipe_478 --out-kit out/realhead-v1.kit.json --report out/mediapipe_478.calibration.json \
       [--scheme-out out/mediapipe_478.json]
   ```

For each index, the tool works through these steps:

- **Start point.** It starts from the kit's embedding of that point. Without one, it uses the surface point hit by the ray of the first detection, found through a z-buffer `tri_id` lookup.
- **Visible renders.** It keeps renders where the point is camera-facing (cos ≥ cos 80°) and not occluded in the z-buffer.
- **Refinement.** It refines `(tri, bary)` by damped Gauss–Newton on the pixel reprojection error, walking across triangle edges, and trims renders above max(3 px, 3.035 σ̂).
- **Shrink.** It shrinks toward the prior embedding with `w = n/(n+2)`.
- **Uncertainty.** It reports `sigma_cal`: the RMS reprojection error converted to mm at each render's depth. `sqrt(sigma_def_kind² + sigma_cal²)` becomes the embedding's `sigma_annot_mm`.
- **Verification.** A point is `verified` when n ≥ 20 and `sigma_cal` ≤ 1.0 mm (sharp junctions and curves) or ≤ 2.5 mm (other kinds).

**Checks.** These use the unshrunk optimum `p_hat` of each calibrated point, that is, what the detections say. The shrink would pull a point seen in few renders back toward its prior embedding, for example an iris group from an earlier run back to its old side.

- **Mirror pairs.** Each listed pair must map to mirrored surface points within 2 mm; otherwise both points are flagged `pair_mismatch`. An uncalibrated member enters with its prior embedding.
- **Geometric L/R groups.** Each group is resolved by the 3D distance from its calibrated members to the template eye centres. The result is recorded as `lr_resolved {group: "L"|"R"}`, with flags:
  - `lr_unexpected`: the side disagrees with `provisional_side`;
  - `lr_ambiguous`: the distance ratio is below 1.5;
  - `lr_low_n`: a member was used in fewer than 20 renders;
  - `lr_poor_fit`: a member's `sigma_cal` exceeds its verification limit;
  - `lr_conflict`: two groups resolved to the same side.

  A group with no calibrated member is flagged `unresolved` and is not recorded.

  Sides stay `geometric` in the scheme.

**Outputs:**

- the kit, with updated embeddings for the scheme;
- the report: per index n, `sigma_cal`, `verified`, `w`, flags and template `tri`/`bary`, plus the pair results and `lr_resolved`;
- with `--scheme-out`, a copy of the scheme with the `verified` flags and a `calibration` record.

What to commit: the scheme semantics, the CC0 kit and the aggregate report. Never commit detections; for template renders they are disposable.

## 4. `recalibrate_prior.py`: refit the landmark prior

### (a) ANSUR II

```sh
python3 tools/recalibrate_prior.py --ansur ANSUR_II_MALE_Public.csv ANSUR_II_FEMALE_Public.csv \
    --licence CC0-1.0 --out face3d/data/landmark_prior_v2.json [--date 2026-12-01] [--min-group-n 30]
```

**Columns.** These follow the research table `ansur2_head_columns`, matched case-insensitively. Seven columns are required, each mapped to a prior chord: `headlength`→g–op, `headbreadth`→eu–eu, `bizygomaticbreadth`→zy–zy, `mentonsellionlength`→n–me (sellion ≈ n), `interpupillarybreadth`→p–p, `earlength`→sa–sba, and `tragiontopofhead`→v.y.

**Unit check.** The median of each column must be plausible: `headlength` 150–250 mm, other columns 0.75×–1.25× the research mean ranges. A column that fails is tried ÷10 and refused if it still fails. The script exits with status 2.

**Statistics.** Statistics are by `Gender` only. They are pooled over the file's DODRace groups with **equal weight per group** (balanced pooling, anat R5.5), and groups with fewer than 30 rows are left out. The output never contains group-conditioned statistics or priors (anat R7.4).

**Refit.** The factor sigmas are refitted with the calibration ported from `research/_raw/scripts/build_lm.py`: weighted NNLS on squared chord SDs, a ridge of 0.15 toward the initial guesses, and a floor at 0.5× the guess. The ANSUR SDs replace the mapped targets, and v.y is added. Means, loadings and residuals are kept. With the original targets, the port reproduces the packaged v1 sigmas within 0.006, which a test checks.

**Scale prior.** `scale_sigma_log` is proposed as the mean over sexes of the mean balanced log-SD of head length, head breadth and face height.

**Output.** A `face3d.landmark_prior` file (format version 1, `data_version` 2) that `FactorPrior.from_package(path=...)` loads. It carries `provenance {source, files [name, sha256], sha256, n per sex, date, badge 📄, base_prior}` and a `recalibration` block: pooled means, SDs and correlations, per-target ANSUR versus model SDs before and after, and the scale proposal.

### (b) Landmark samples

```sh
python3 tools/recalibrate_prior.py --landmark-samples flame_samples.npz --licence CC-BY-4.0 \
    --attribution "Contains geometry derived from FLAME 2023 Open (CC BY 4.0), https://flame.is.tue.mpg.de" \
    --out out/landmark_prior_flame.json [--factors 18]
```

**Input.** The NPZ holds `samples` (S, 44, 3) in the FH frame: mm, origin mid-tragion, +x the subject's left, ids in prior order. It may also hold `ids` and `sex` (S,) with values `M`/`F`. Without `sex`, one model is shared by both sexes. The tool refuses metres (with a hint to multiply by 1000), a wrong side convention, a tragion midpoint more than 10 mm from the origin, and too few samples.

**Fit.** The fit computes the empirical mean and covariance, then a low-rank plus diagonal model with K = 18 by iterated principal-axis factoring of the correlation matrix. Residual SDs are floored at 0.3 mm on the mm scale, so a coordinate whose total SD is below 0.3 mm still gets the full floor. Coordinates fixed by the frame (SD ≤ 1e-6 mm) are accepted: in the FH frame these are t_L.y, t_L.z, t_R.y and t_R.z. They stay out of the correlation step, get zero loadings and the 0.3 mm floor as residual, and are listed in `recalibration.frame_fixed_coordinates`.

**Output.** Factors `pf01…pf18`, the attribution text and provenance.

**Caveat.** These factors include isometric size, with no `size` column. The global log-scale ζ would therefore count size twice (D-03). Decide how to handle this before promoting such a prior (WP-24).

## Relation to WP-24

WP-24 runs the tools as follows:

- **M3b:** `detect_mediapipe.py` and `calibrate_scheme.py` on renders of the real CC0 template, then commits the scheme semantics and an aggregate report.
- **M7:** `recalibrate_prior.py` with ANSUR II, and optionally FLAME 2023 Open with attribution, to produce `landmark_prior_v2.json`. Provisional badges are replaced only by measured values.
