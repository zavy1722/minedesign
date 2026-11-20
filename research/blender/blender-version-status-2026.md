# Blender release status and roadmap as of late 2026

> In late November 2026 Blender ships on two tracks: **5.3**, the feature release of 10 Nov 2026 that the developer docs and the "latest" manual both label current, and **5.2 LTS**, released 14 Jul 2026, supported until Jul 2028, with 5.2.4 out between 10 and 17 Nov [6][7][10][12][14][15]. **4.5 LTS** is supported until Jul 2027 [13], while 4.2 LTS ran out of support in Jul 2026, though face add-ons still target it [18][19]. Python 3.13 is the bundled interpreter from 5.1 on (5.1 dependency PR: Python 3.13.9; 5.2 LTS library tracker: Python 3.13.13) and NumPy moved to 2.3.x in the 5.1 cycle [20][21][22]; these are development-tracker sources, not the shipped release notes, so check `sys.version` and `numpy.__version__` at runtime (corrected in verification). The 5.0.1 fixes [4] fit with 5.0 still bundling Python 3.11. The breaks that matter most for a photo→head add-on are 5.0's `mathutils` buffer protocol, through which NumPy now gets float32, non-contiguous views [3], plus (from expert knowledge) the 4.2 extension platform, the 4.3 brush assets and several 5.0 removals. So the add-on should read versions at runtime, probe for features instead of version numbers, and keep the solver in float64 pure NumPy.
>
> Evidence status: 6 ✅ / 26 📄 / 61 🧠 / 3 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Release status**
- **5.3 is the current feature release.** The developer-docs index lists it as current stable, dated 10 Nov 2026 [12]. Two separately harvested manual pages under `/manual/en/latest/` are titled "Blender 5.3 Manual" [14][15]. ✅ that it shipped and is current (all first-party pages); the exact date is 📄.
- **5.2 LTS was released on 14 Jul 2026 and is supported until Jul 2028** [6][7] 📄 (two pages, one publisher). Third-party add-ons already target it: Face Shape Key Rig requires 5.2 or newer [16], and Faceit lists compatibility with 3.0–5.2 [17]. ✅ that 5.2 exists and ships.
- **5.2.4** is dated 10 Nov 2026 on the download page [6], and the releases page says the LTS entry was "last updated to 5.2.4 on November 10, 2026" [23] 📄 (corrected in verification). The 16 and 17 Nov dates on the 5.2 LTS milestone views [10] were stale plans.
- **4.5 LTS is supported until Jul 2027** [13][26][27] ✅. It is the last 4.x release 🧠.
- **4.2 LTS** (Jul 2024) ran out of support in Jul 2026 under the same two-year rule [26][28] 📄. Even so, MPFB2 2.0.18 lists "4.2 LTS and newer" [18], and the FaceFit prototype was tested on 4.2.3 LTS [19] 📄.
- **5.0 was released on 18 Nov 2025** [1][2] 📄 (one publisher, seen only at snippet level).
- **Cadence:** the 2026 plan named 5.1 (Mar), 5.2 LTS (Jul) and 5.3 (Nov) [9]. Both 5.2 and 5.3 arrived on plan [6][12] ✅. The pattern is three releases a year, an LTS every July, and two years of LTS support [6][9][13] 📄. The version number of the July 2027 LTS is not sourced 🧠.

**Python and NumPy inside Blender**
- 4.1–4.5 bundle **Python 3.11**; 3.1–4.0 bundled 3.10 🧠.
- In 5.0.1, one fix "unbreaks" the Python 3.14 build and another fixes a driver test for Python newer than 3.11 [4] 📄. Both concern builds against a system Python. They fit with 5.0 still *bundling* 3.11 ↔️.
- For 5.1–5.3: Blender has historically changed Python in a spring release, following the VFX Reference Platform (3.10 in 3.1, 3.11 in 4.1) 🧠. The 5.1 dependency PR lists Python 3.13.9 [21] and the 5.2 LTS library tracker lists a Python 3.13.13 security update [22], so 3.13 is bundled from 5.1 on 📄 (corrected in verification; development-tracker evidence, the 5.3 interpreter is not stated but expected to stay 3.13).
- NumPy: 4.x ships NumPy 1.2x (≈1.24–1.26) 🧠. The 5.1 library-changes tracker requests NumPy 2.3.x and the 5.1 dependency PR names NumPy 2.3.4 [20][21], so 5.1 moved to NumPy 2.x 📄 (corrected in verification; development-stage, the shipped version is not confirmed). Keep code NumPy 1/2-neutral because 4.x add-ons still run on 1.x.
- **5.0 `mathutils` buffer protocol:** `np.asarray(Vector/Matrix)` now returns a float32, non-contiguous view [3] 📄. mathutils has always stored single-precision floats. What changed is that NumPy no longer goes through the float64 sequence path 🧠 (see myths).
- Blender bundles NumPy and `requests`. It does not bundle Pillow, OpenCV, SciPy or MediaPipe 🧠.

**API changes that affect a face-fitting add-on** (each 🧠 unless cited; confirm against [3][5])
- **4.0:** passing a context-override dict to an operator was removed; use `with context.temp_override(...)` 🧠. The `gpu` built-in shaders lost their `2D_`/`3D_` prefixes (`UNIFORM_COLOR`, `POLYLINE_UNIFORM_COLOR`) 🧠.
- **4.1:** Auto Smooth was removed (`use_auto_smooth`, `calc_normals_split`). The replacements are the "Smooth by Angle" modifier and `Mesh.corner_normals` 🧠.
- **4.2 LTS: Extensions platform.** It introduced `blender_manifest.toml` with id, version, `blender_version_min` ≥ "4.2.0", an SPDX licence, `permissions`, `wheels` and `platforms`. It also added `bpy.app.online_access` and `bpy.utils.extension_path_user()`. Legacy `bl_info` add-ons can still be installed from disk 🧠.
- **4.3: Brush assets.** Brushes now live in asset libraries, so a script can no longer simply assign `tool_settings.sculpt.brush`. Activation goes through `bpy.ops.brush.asset_activate` [24][25] 📄 (the 4.3 notes say `paint.brush_set` was removed in favour of it; the "can no longer assign `tool_settings.sculpt.brush`" wording is not stated in the sources 🧠). `Brush.sculpt_tool` became `sculpt_brush_type` in **5.0**, not 4.3: 4.3 still used `sculpt_tool` [3][25] 📄 (corrected in verification).
- **4.4:** slotted Actions arrived 🧠.
- **5.0 removals** (moderate confidence, ≈60–70 % each):
  - `bgl` removed [3] 📄;
  - `bpy.props` values can no longer be read as `id["name"]` (system and user properties were split) [3] 📄;
  - the engine id `BLENDER_EEVEE_NEXT` went back to `BLENDER_EEVEE` 🧠;
  - the compositor tree moved to `scene.compositing_node_group` 🧠;
  - COLLADA import/export was removed 🧠;
  - the legacy Action API (`Action.fcurves`) was removed 🧠;
  - Intel-Mac builds were dropped, leaving 4.5 as the last 🧠.
- Official migration notes live in the compatibility index [5] and the per-release Python API pages [3] 📄.

**Sculpt and modeling roadmap**
- **Already landed:**
  - a C++ refactor of sculpt mode across 4.2–4.4, with multithreaded brushes and much faster entry into sculpt mode on dense meshes 🧠;
  - brush assets with an "Essentials" library in 4.3 🧠;
  - AgX as the default view transform since 4.0 🧠.
- **Long-standing limits a likeness pipeline has to design around:**
  - Dyntopo, voxel remesh and QuadriFlow all rebuild topology, which loses vertex indices, UVs and shape keys 🧠;
  - multires displacement cannot be written from Python 🧠;
  - multires and shape keys do not combine 🧠.
- **Still open:** the 2026 projects post [9] was harvested, but its sculpt items were not extracted, so any sculpt features in 5.3 or later are unknown 🧠.

## Numbers & reference tables

**Table 1 – Release lines (as of 2026-11-20)**

| Version | Track | Released | Support ends | Bundled Python | Badge | Src |
|---|---|---|---|---|---|---|
| 4.2 | LTS | Jul 2024 | Jul 2026 (ended) | 3.11 | 📄 support end; 🧠 rest | [26][28]; [18][19] (still targeted) |
| 4.5 | LTS | Jul 2025 | Jul 2027 | 3.11 | ✅ support end; 🧠 rest | [13][26][27] |
| 5.0 | feature | 2025-11-18 | — | 3.11 likely | 📄 date; ↔️ Python | [1][2][4] |
| 5.1 | feature | Mar 2026 (plan) | — | 3.13 (3.13.9 in dev PR) | 📄 plan; 📄 Python (corrected in verification) | [9][21] |
| 5.2 | LTS | 2026-07-14 | Jul 2028 | 3.13 (3.13.13 per tracker) | 📄 | [6][7][22] |
| 5.2.4 | LTS corrective | 2026-11-10 | (5.2) | — | 📄 (corrected in verification) | [6][23] |
| 5.3 | feature | 2026-11-10 | — | unconfirmed | ✅ current; 📄 date | [12][14][15][23] |

**Table 2 – LTS windows (derived from Table 1)**

| Window | LTS lines in support | Suggested CI matrix | Badge |
|---|---|---|---|
| Jul 2026 – Jul 2027 | 4.5, 5.2 | 4.5, 5.2, latest feature release (5.3), daily alpha during each beta | 📄 [6][13] |
| Jul 2027 – Jul 2028 | 5.2 + the Jul 2027 LTS | 5.2, new LTS, latest | 🧠 next LTS not sourced |

**Table 3 – Precision and size numbers for the engine**

| Quantity | Value | Badge |
|---|---|---|
| float32 machine epsilon | 2⁻²³ ≈ 1.19 × 10⁻⁷ (relative) | 🧠 (IEEE 754) |
| float32 spacing at 0.1 m / 1 m | ≈ 7.5 × 10⁻⁹ m / ≈ 1.2 × 10⁻⁷ m | 🧠 |
| float64 machine epsilon | 2⁻⁵² ≈ 2.2 × 10⁻¹⁶ | 🧠 |
| Multires face count | base faces × 4^L; a 20k-face base gives 1.28 M at L3, 5.1 M at L4 and 20.5 M at L5 | 🧠 (arithmetic) |
| `foreach_get/set` versus a per-vertex Python loop | ≈ 10–100× faster | 🧠 |
| Template vertex counts | FLAME 5,023; MakeHuman/MPFB whole-body base ≈ 13k | 🧠 |
| Voxel remesh output | ≈ surface area / voxel²; 1 mm voxels on a whole head ≈ 10⁵ faces | 🧠 |

**Table 4 – Mapping a Blender camera to a pinhole model (API stable since 2.8x)**

| Quantity | Mapping | Badge |
|---|---|---|
| Sensor fit | AUTO applies the sensor size to the larger resolution dimension [14] | 📄 |
| Focal length in pixels | f = lens_mm · S / sensor_mm, where S = max(W,H) for AUTO, W for HORIZONTAL, H for VERTICAL | 🧠 |
| Principal point (origin at the pixel corner, y down) | cx = W/2 − shift_x·S; cy = H/2 + shift_y·S | 🧠 |
| Axes | the camera looks down −Z with +Y up; an OpenCV camera = the Blender camera · diag(1, −1, −1) | 🧠 |
| Resolution | one render resolution per scene, not per camera | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Choose one build per job and keep it.** For a likeness job that runs for months, use 5.2 LTS, which gets fixes only, until Jul 2028 [6]. Use 5.3 only when you need one of its features. Brush assets, sculpt behaviour, colour management and add-on compatibility shift between feature releases 🧠, so do not switch mid-job. Record `bpy.app.version_string`, `sys.version` and `numpy.__version__` from the Python console.
2. **Normalise the photos before anything reads them.** Bake the EXIF orientation into the pixels and strip the tag. Blender's image loader has historically ignored EXIF orientation, while detectors that read through PIL or OpenCV may apply it, so the landmarks end up on a rotated image 🧠. In the same pass, read the focal length and 35 mm equivalent: Blender has no EXIF API and ships without Pillow 🧠.
3. **Use one camera per photo, and handle resolution yourself.** Render resolution applies to the whole scene. Photos with different sizes or orientations therefore need the resolution switched whenever the active camera changes, or a separate scene per view. Otherwise the background image is cropped or letterboxed (Fit vs Crop [14]) and every landmark shifts 🧠.
4. **Colour:** load photos as sRGB. For side-by-side checks of render against photo, set the view transform to *Standard*. AgX compresses skin highlights and desaturates them 🧠.
5. **Scale:** work at real scale with 1 unit = 1 m (head length ≈ 0.18–0.20 m 🧠). Set the camera's sensor and lens from EXIF. Voxel size and Dyntopo detail are measured in scene units, so a model at the wrong scale gives absurd face counts.
6. **Freeze the topology while anything still depends on vertex indices.** Write the fit as a shape key on the template ("likeness", value 0–1) so the artist can dial it in and compare. Do every landmark-driven step first. Then use Multires for detail. Leave Dyntopo and remeshing for last, if you use them at all 🧠.
7. **Interchange:** store landmarks, camera intrinsics and extrinsics, and shape coefficients in a JSON sidecar, not only inside the .blend. A .blend file is not guaranteed to open in an older major version 🧠. Exchange meshes as glTF, FBX, OBJ or USD; COLLADA is gone in 5.0 🧠.
8. **What usually goes wrong:** a 4.x add-on fails on 5.x at `import bgl` or `obj["prop"]`; brush scripts from tutorials older than 4.3 do nothing; bit-exact tests break because mathutils→NumPy has gone through float32 since 5.0 [3]; cp311 wheels stop importing after a Python bump; the artist runs 5.3 while the studio runs 5.2 LTS.

## Algorithmic implications

- **Support policy:**
  - set the manifest's `blender_version_min = "4.2.0"`, the platform floor, and warn at runtime below 4.5;
  - run CI on 4.5 LTS, 5.2 LTS, the current feature release, and the daily alpha during each beta window (roughly a month before release 🧠);
  - drop 4.5 after Jul 2027 [13].
- **Probe for features, never branch on version** (everything lives in `compat.py`):
  - check `np.asarray(mathutils.Vector((0, 0, 0))).dtype` to pick the copy path (a float32 view since 5.0 [3]);
  - never import `bgl`; draw only with `gpu`;
  - set the engine inside `try`, using `'BLENDER_EEVEE'` first and falling back to `'BLENDER_EEVEE_NEXT'` on `TypeError`;
  - check `hasattr(bpy.types.Scene, "compositing_node_group")`;
  - check `hasattr(bpy.ops.brush, "asset_activate")`;
  - check `"sculpt_brush_type" in bpy.types.Brush.bl_rna.properties`;
  - keep add-on state in a `PointerProperty` group and read it as attributes, never as `id["x"]` 🧠.
- **Precision boundary:** bulk reads go into a preallocated `np.empty(3*n, np.float32)` via `foreach_get("co", buf)` (the dtype must match for the fast memcpy path 🧠); convert to float64 once and solve in float64; write back with `astype(np.float32)`, `foreach_set`, `mesh.update()`. Read mathutils objects with `np.array(m, dtype=np.float64)`, and never pass `copy=False`, which raises in NumPy 2 when a copy is needed 🧠.
- **Suggested tolerance defaults**, scale-relative, with s = head scale (for example bizygomatic width ≈ 0.13–0.15 m 🧠):
  - Blender round-trip check: atol = 1e-6·s, which is ≈ 10–20 float32 steps at head scale.
  - Convergence: relative cost change < 1e-10, or step < 1e-8·s, in float64.
  - Finite differences: only in float64 and only on data that never went through float32, because the float32 noise floor (~1e-7 relative) ruins Jacobians. Prefer analytic Jacobians.
  - Golden-file tests: rtol = 1e-5.
- **NumPy 1/2-neutral subset** 🧠: avoid `np.float_`, `np.NaN`, `np.Inf`, `np.product`, `np.cumproduct`, `np.alltrue`, `np.row_stack`, `np.in1d` (use `np.isin`); give explicit dtypes (under NEP 50 a float32 array × a Python float stays float32); use `lstsq(..., rcond=None)` and `default_rng(seed)`. Test the pure-NumPy core outside Blender on CPython 3.11 + NumPy 1.26 and 3.13 + NumPy 2.x, covering both possible 5.x stacks.
- **Threads:** bpy is not thread-safe. Run the solve in a worker thread on copied arrays, poll it with `bpy.app.timers.register`, and apply the results on the main thread. Alternatively, chunk the iterations inside a modal operator 🧠.
- **Dependencies:** no compiled wheels in the core; landmark detection (MediaPipe/ONNX) runs out of process in its own Python, exchanging JSON. Any bundled wheels are built per platform and per CPython tag (cp311 for 4.x, cp313 for 5.1 and later), and never include `numpy` 🧠. Declare `permissions` (`network`, `files`), gate downloads on `bpy.app.online_access`, cache models under `extension_path_user(__package__, create=True)` 🧠.
- **Camera exchange:** solve in OpenCV convention and convert with Table 4. When writing cameras, set `sensor_fit='HORIZONTAL'` explicitly, so that portrait-orientation photos don't fall into the AUTO max(W,H) ambiguity [14].
- **Reproducibility record** for every fit: `{blender, python, numpy, addon_version, seed, solver_config}`; budget three compatibility passes a year [9].

## Disagreements, myths & open questions

- **"Latest stable is 5.3" vs "latest is 5.2.4 LTS"** [12] vs [6]: these are two tracks and both statements are true. The manual pages [14][15] corroborate that 5.3 is current ✅.
- **5.2.4 date:** 10 Nov [6][23]; the 16 and 17 Nov milestone dates [10] were stale plans 📄 (corrected in verification).
- **Myth: "Blender 5.x bundles Python 3.14."** The 3.14 item in [4] is a build fix ↔️.
- **Misreading: "mathutils switched from float64 to float32 in 5.0."** The storage was always float32 🧠. What is new is the buffer path to NumPy [3]. Either way, the advice is to pass `dtype=np.float64` explicitly.
- **Myth: "Extensions killed legacy add-ons."** Legacy installs still work; only a listing on extensions.blender.org needs a manifest 🧠.
- **Myth: "the LTS gets the sculpt improvements."** LTS lines get fixes only; sculpt features land in feature releases 🧠.
- **Verification record:** the earlier pass neither verified nor refuted anything (all harvest facts were snippet-level). This pass upgrades only "5.3 is current" and "5.2 ships", via other harvests. Nothing refuted.
- **Open questions:**
  1. Which Python does 5.0 bundle (5.1 and 5.2 are 3.13 per trackers [21][22]), and which does 5.3 bundle?
  2. Which exact NumPy 2.x does each shipped 5.x bundle (2.3.x per the 5.1 tracker [20][21])?
  3. What is the full list of breaking changes from 5.0 to 5.3? Each of the 🧠 5.0 removals above needs confirming against [3][5].
  4. What sculpt items are in [9] and in the 5.3 release notes?
  5. What will the version number of the Jul 2027 LTS be?
  6. Did 5.0 drop Intel Macs, which would remove the macos-x64 wheels?
  7. What size limits does extensions.blender.org place on bundled wheels?

## Sources

[1] Blender 5.0 — https://www.blender.org/releases/5-0/ — official-docs — 2025
[2] Blender 5.0 Release Notes — https://developer.blender.org/docs/release_notes/5.0/ — official-docs — 2025
[3] Blender 5.0: Python API — https://developer.blender.org/docs/release_notes/5.0/python_api/ — official-docs — 2025
[4] Blender 5.0: Corrective Releases — https://developer.blender.org/docs/release_notes/5.0/corrective_releases/ — official-docs — 2025
[5] Index – Blender Developer Documentation (compatibility) — https://developer.blender.org/docs/release_notes/compatibility/ — official-docs — n.d.
[6] 5.2 LTS — Blender (download/releases) — https://www.blender.org/download/releases/5-2/ — official-docs — 2026
[7] Blender 5.2 LTS — Blender — https://www.blender.org/releases/5-2/ — official-docs — 2026
[8] Blender 5.2 LTS Release — Blender (press) — https://www.blender.org/press/blender-5-2-lts-release/ — official-docs — 2026
[9] Projects to Look Forward to in 2026 — Blender — https://www.blender.org/development/projects-to-look-forward-to-in-2026/ — official-docs — 2026
[10] 5.2 LTS milestone — Blender Projects — https://projects.blender.org/blender/blender/milestone/33 — repo — 2026
[11] 5.0 milestone — Blender Projects — https://projects.blender.org/blender/blender/milestone/20 — repo — 2025
[12] Blender Release Notes — Blender Developer Documentation (index) — https://developer.blender.org/docs/release_notes/ — official-docs — n.d.
[13] Release Notes — Blender (index) — https://www.blender.org/download/releases/ — official-docs — n.d.
[14] Cameras — Blender 5.3 Manual — https://docs.blender.org/manual/en/latest/render/cameras.html — official-docs — 2026 (from the reference-camera-setup harvest)
[15] Principled BSDF — Blender 5.3 Manual — https://docs.blender.org/manual/en/latest/render/shader_nodes/shader/principled.html — official-docs — 2026 (from the skin-shading harvest)
[16] Fragid/face-shapekey-rig (GitHub) — https://github.com/Fragid/face-shapekey-rig — repo — n.d. (from the blender-face-addons harvest)
[17] Faceit: Facial Expressions and Performance Capture (Superhive) — https://superhivemarket.com/products/faceit — commercial listing — n.d. (from the blender-face-addons harvest)
[18] MPFB version history, Blender Extensions — https://extensions.blender.org/add-ons/mpfb/versions/ — official listing — 2026 (from the blender-face-addons harvest)
[19] VGCLUB/facefit-mpfb (FaceFit MPFB2 Blender add-on prototype) — https://github.com/VGCLUB/facefit-mpfb — repo — n.d. (from the craniometric-landmarks harvest)
[20] Library changes for Blender 5.1 (#147201) — https://projects.blender.org/blender/blender/issues/147201 — repo — 2025
[21] Deps: Library changes for Blender 5.1 (PR #149852) — https://projects.blender.org/blender/blender/pulls/149852 — repo — 2025
[22] Library changes for Blender 5.2 LTS (#153974) — https://projects.blender.org/blender/blender/issues/153974 — repo — 2026
[23] Blender 5.3 — https://www.blender.org/releases/5-3/ (and https://www.blender.org/download/releases/) — official-docs — 2026
[24] Blender 4.3: Sculpt, Paint, Texture — https://developer.blender.org/docs/release_notes/4.3/sculpt/ — official-docs — 2024
[25] Brush Operators — Blender Python API — https://docs.blender.org/api/current/bpy.ops.brush.html — official-docs — 2026
[26] LTS — Blender — https://www.blender.org/download/lts/ — official-docs — 2026
[27] Blender 4.5 LTS — Blender — https://www.blender.org/download/lts/4-5/ — official-docs — 2026
[28] Blender 4.2 LTS — Blender — https://www.blender.org/download/lts/4-2/ — official-docs — 2026

**Further reading (by name, not yet linked)**
- Blender Python API reference, including its "Gotchas" pages (bpy, mathutils, gpu, `foreach_get`)
- Blender Extensions developer handbook: the `blender_manifest.toml` schema and the "Python Wheels" guidance
- VFX Reference Platform, yearly specifications CY2024–CY2026
- NumPy 2.0 migration guide; NEP 50, "Promotion rules for Python scalars"
- IEEE 754-2008, Standard for Floating-Point Arithmetic
- Hartley & Zisserman, *Multiple View Geometry in Computer Vision*, 2nd ed., 2004 (camera conventions)
- BlenderProc (DLR), camera-intrinsics utilities (Blender ↔ K-matrix conversion)
- Farkas, *Anthropometry of the Head and Face*, 1994 (head-scale values used for the tolerances)

## Verification log (2026-11-20)

| Claim | Outcome | Source |
|---|---|---|
| Bundled Python in 5.0 / 5.1 / 5.2 LTS / 5.3 | Corrected: 5.1 deps PR lists Python 3.13.9; 5.2 LTS library tracker lists Python 3.13.13. 5.0 (3.11) and 5.3 not directly stated: unconfirmed. Development-tracker evidence only; the 5.2 release notes name no bundled Python | https://projects.blender.org/blender/blender/pulls/149852 ; https://projects.blender.org/blender/blender/issues/153974 |
| Bundled NumPy / move to 2.x | Corrected: 5.1 tracker requests NumPy 2.3.x (matching VFX 2026); deps PR names NumPy 2.3.4. Shipped version unconfirmed | https://projects.blender.org/blender/blender/issues/147201 ; https://projects.blender.org/blender/blender/pulls/149852 |
| 5.0 Python API breaks | Confirmed: BGL removed; bpy.props no longer stored with custom properties (no dict-style access). Unconfirmed: EEVEE id rename, compositing_node_group, COLLADA removal, Action.fcurves removal (not surfaced in results). mathutils float32 buffer: already sourced [3], not re-surfaced | https://developer.blender.org/docs/release_notes/5.0/python_api/ |
| 5.3 current, released 10 Nov 2026; 5.2.4 date | Confirmed 5.3 released 10 Nov 2026 and current. 5.2.4 corrected to 10 Nov 2026 (milestone dates 16/17 Nov were plans) | https://www.blender.org/releases/5-3/ ; https://www.blender.org/download/releases/ ; https://developer.blender.org/docs/release_notes/ |

## Verification log, pass 2 (2026-11-20)

| Claim | Outcome | Source |
|---|---|---|
| 4.2 LTS support ended Jul 2026 | Confirmed (4.2 LTS page says end-of-life) | https://www.blender.org/download/lts/4-2/ ; https://www.blender.org/download/lts/ |
| 4.5 LTS supported until Jul 2027 (two-year window) | Confirmed (4.5 LTS page; developer docs: LTS maintained two years) | https://www.blender.org/download/lts/4-5/ ; https://developer.blender.org/docs/release_notes/ |
| Next LTS due Jul 2027 / its version number | Unconfirmed; not stated in results (5.2 LTS is the current newer LTS) | none |
| 4.3 brush activation via `bpy.ops.brush.asset_activate` | Confirmed (`paint.brush_set` removed in favour of it); the "cannot assign `tool_settings.sculpt.brush`" wording not stated: unconfirmed | https://developer.blender.org/docs/release_notes/4.3/sculpt/ ; https://docs.blender.org/api/current/bpy.ops.brush.html |
| `Brush.sculpt_tool` renamed `sculpt_brush_type` in 4.3 | Corrected: the rename is in 5.0; 4.3 still used `sculpt_tool` | https://developer.blender.org/docs/release_notes/5.0/python_api/ |
