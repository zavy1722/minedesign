# Packaging as a Blender extension

> Since Blender 4.2 LTS, add-ons are distributed as **extensions**: a zip with a `blender_manifest.toml` (schema `1.0.0`) that declares the id, a semantic version, SPDX licences, the supported Blender range, platforms, bundled Python wheels and permissions. The zip is built, validated and installed with `blender --command extension …` 🧠. Face and camera tools in this library already ship as extensions: MPFB2, Face Shape Key Rig, CaptureForge, Simple Camera Match and perspective-match [1][5][7][8][9] ✅. Every one whose licence was captured is GPL [1][3][5][7] ✅. The photo→head add-on should be a GPL-3.0-or-later extension with **no compiled wheels in its core**: the NumPy engine uses Blender's bundled NumPy. Landmark detectors and model weights stay optional and separately licensed, are fetched only with the `network` permission and `bpy.app.online_access`, and are never bundled when they carry non-commercial terms [17][18][19]. The main defence against Python, NumPy and API drift between releases is headless CI (`blender -b --factory-startup --python-exit-code 1 -P …`) on 4.5 LTS, 5.2 LTS and the current feature release [12][14][15]. This topic's own web harvest was not available, so the manifest schema, platform rules and CLI flags below are expert knowledge awaiting verification. The cited URLs come from sibling harvests in this library.
>
> Evidence status: 5 ✅ / 39 📄 / 67 🧠 / 8 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Manifest (`blender_manifest.toml`)**
- **Required keys:** `schema_version = "1.0.0"`, `id`, `version` (semver `MAJOR.MINOR.PATCH`), `name`, `tagline`, `maintainer` (`"Name <email>"`), `type` (`"add-on"` or `"theme"`), `blender_version_min` (no lower than `"4.2.0"`), and `license`, a list of `"SPDX:<id>"` strings [24][25] ✅.
- **Optional keys:**
  - `website` and `copyright` (a list of `"YEAR Holder"` strings; some licences require it) 🧠;
  - `tags`, from a fixed vocabulary (for add-ons this includes "Sculpt", "Modeling", "Mesh", "Camera", "Import-Export", "Rigging", "Pipeline", "Development" and "User Interface") 🧠;
  - `blender_version_max`, which is **exclusive**: the first version that is *not* supported [24] 📄;
  - `platforms`, `wheels`, `[permissions]`, and `[build]` with `paths` or `paths_exclude_pattern` 🧠.
- **`tagline`:** at most 64 characters, with no trailing punctuation [24] 📄. Permission reasons follow the same short-text style: one sentence, no final period [24] 📄.
- **`id` becomes the Python package.** An installed extension imports as `bl_ext.<repo>.<id>`: `blender_org` for platform installs, `user_default` for install-from-disk. `__package__` therefore differs per install. Never hard-code it, never use absolute self-imports, and never rename `id` after release, because users' preferences and updates key on it 🧠.
- **`bl_info` is unnecessary** in an extension. Legacy `bl_info` add-ons still install from disk; only the extension format and the online platform require the manifest 🧠. MPFB2 names the extension platform as its preferred install route [4] 📄.

**Permissions and online access**
- There are five permission keys for add-ons: `files`, `network`, `clipboard`, `camera` and `microphone`. Each takes a reason string [24] 📄 that is shown to the user before install 🧠.
- Permissions are **disclosure, not a sandbox**: Python inside Blender keeps full OS access 🧠.
- `bpy.app.online_access` mirrors the user's "Allow Online Access" preference, and the `--offline-mode`/`--online-mode` CLI flags can override it (`bpy.app.online_access_override`) 🧠. Extensions must check it before network use [24] 📄.
- **Persistent user data** belongs in `bpy.utils.extension_path_user(__package__, path="", create=True)`, which lives under `extensions/.user/<repo>/<id>` and survives updates. The extension's own directory is replaced on every update 🧠.

**Wheels**
- `wheels = ["./wheels/<file>.whl", …]` takes paths relative to the manifest. On install, Blender extracts them into **the extension's own** site-packages directory, not a shared one [27] 📄 (corrected in verification; the earlier claim of a per-repository shared `extensions/.local/lib/pythonX.Y/site-packages` was not supported). Collision behaviour between extensions bundling the same package is unverified 🧠.
- A wheel must match Blender's CPython ABI tag unless it is `abi3` or pure (`py3-none-any`). That tag is **cp311 for 4.1–4.5** 🧠. **Blender 5.1 bundles Python 3.13** (VFX Platform 2026) [28] 📄, so cp311 wheels do not load there. Which Python 5.2 LTS and 5.3 bundle is not stated in the sources found (presumably 3.13) 🧠; the 5.0.1 fixes for builds against Python >3.11 and 3.14 show build targets, not the bundled version [11].
- **Never bundle `numpy`.** Blender ships it, and a second copy breaks ABI for every add-on. The platform also forbids installing modules at runtime (`pip install`) 🧠.
- `blender --command extension build --split-platforms` writes one zip per platform that holds only the matching wheels, and records `platforms` in each zip's manifest [27] 📄.
- **Getting wheels:** `pip download <pkg>==<ver> --dest wheels --only-binary=:all: --python-version 3.11 --platform <tag>`, repeated per platform tag 🧠.
- Compiled modules cannot be hot-reloaded. Updating a wheel-bearing extension needs a Blender restart, and on Windows a loaded `.pyd` can block the update until then 🧠.

**extensions.blender.org rules (as I understand them)**
- **Licensing:** per the Terms of Service, add-ons must be fully GPL v3-or-later compliant (themes need only GPL-compatible); bundled non-code assets (images, fonts) must be CC0 [26] 📄 (corrected in verification). `SPDX:GPL-3.0-or-later` is the reference choice.
  - Listings follow this: MPFB code is GPL-3.0-or-later [1][3] ✅, its asset packs are CC0 or CC-BY [1] 📄, and Face Shape Key Rig is a free GPL listing [5] 📄.
- **Not allowed:** loading remote code or requiring externally downloaded components; depending on pre-compiled external packages (pure-Python wheels via the manifest are still allowed) [26] 📄. Obfuscated code, installing other add-ons and runtime `pip install` are also believed forbidden 🧠. Note: this tension with a platform-split onnxruntime build (Path B) needs checking before upload.
- **Moderation:** the first submission goes through manual review, and every upload needs a higher `version` 🧠.
- **Paid add-ons** are sold elsewhere. Faceit, for example, is sold on Superhive [22] 📄. The code is still GPL-licensed; vendors charge for convenience, support and assets 🧠.

**GPL obligations**
- **The Blender Foundation's position:** scripts that use `bpy` are derivative works of Blender (GPL-2.0-or-later), so distributed add-ons must be GPL-compatible. The position matches the FSF's plugin analysis but has never been tested in court ↔️.
- **When distributing, include:**
  - the full licence text;
  - preserved copyright notices;
  - the corresponding source (the `.py` files *are* the source; any binary you build needs its source offered);
  - each bundled wheel's own licence and notices 🧠.
- **Apache-2.0 dependencies** (MediaPipe, OpenCV ≥4.5) are compatible with GPLv3 but not with GPLv2-only, which is one more reason to choose GPL-3.0-or-later 🧠.
- **Non-commercial terms are GPL-incompatible**, so such files cannot be bundled:
  - InsightFace pretrained models are reported to be non-commercial (a secondary claim) [17] 📄;
  - philgras's video-head-tracker is CC BY-NC 3.0 [19] 📄;
  - FLAME model files have to be downloaded separately because of their licence [18] 📄.
- **Ported code brings its licence with it.** perspective-match ports fSpy's GPL-3.0 solver [9] 📄, so an engine that ports it becomes GPL 🧠.
- **Process boundaries:** under the FSF FAQ's reading, separate programs that exchange files or pipes at arm's length are aggregation, not one combined work 🧠. The FaceFit prototype already runs its solver in an external MCP server [20] 📄.

**Headless testing**
- The canonical call is `blender -b --factory-startup --python-exit-code 1 -P tests/run.py -- <args>`. Arguments are processed in order, and anything after `--` is left for `sys.argv` 🧠. `--python-exit-code` sets the exit code (0–255) used when a script run from the command line raises, and 0 disables it [29] 📄.
- **Without `--python-exit-code`, Blender exits 0 even when the script raised** (0 = disabled, the default). CI then shows false greens [29] 📄.
- **Background mode has:**
  - no event loop, so `bpy.app.timers` and modal operators never run;
  - no window, area or region;
  - no viewport `gpu` drawing;
  - no `view3d`/sculpt-stroke operators, which fail their poll 🧠.
- **CLI subcommands:** `blender --command extension validate | build | install-file -r user_default -e <zip> | server-generate --repo-dir <dir> [--html] | list` 🧠; `install-file` takes `-r REPO` and `-e/--enable` to enable after install [30] 📄. `server-generate` writes the `index.json` for a self-hosted repository 🧠.
- **Isolate CI** from the developer's own prefs with `BLENDER_USER_RESOURCES` (or `BLENDER_USER_CONFIG`/`_SCRIPTS`/`_EXTENSIONS`) pointed at a temporary directory [29] 📄 (`BLENDER_USER_RESOURCES` replaces the default directory of all user files; more specific `BLENDER_USER_*` variables override it).
- **Outside Blender:** PyPI `bpy` wheels pin one CPython minor version, and `fake-bpy-module` provides stubs for linting and type-checking 🧠.
- **The 5.0 `mathutils` change:** `np.asarray(Vector/Matrix)` now returns float32, non-contiguous views [10] 📄, so bit-exact golden files break across versions.

## Numbers & reference tables

**Table 1 – Manifest keys** (population: Blender 4.2–5.3 extension format)

| Key | Req. | Example / allowed | Constraint | Badge |
|---|---|---|---|---|
| `schema_version` | yes | `"1.0.0"` | only version so far | 📄 [24][25] |
| `id` | yes | `"face_likeness_fit"` | Python-identifier-like; immutable | 🧠 |
| `version` | yes | `"0.3.0"` | semver; must increase per upload | 🧠 |
| `tagline` | yes | short phrase | ≤ 64 chars, no trailing period | 📄 [24] |
| `type` | yes | `"add-on"` / `"theme"` | — | 🧠 |
| `blender_version_min` | yes | `"4.2.0"` | ≥ 4.2.0 | 🧠 (MPFB lists 4.2 LTS+ [2] 📄) |
| `blender_version_max` | no | `"6.0.0"` | exclusive bound | 📄 [24] |
| `license` | yes | `["SPDX:GPL-3.0-or-later"]` | add-ons: GPL v3-or-later [26] | 📄 |
| `platforms` | no | `windows-x64`, `windows-arm64`, `macos-x64`, `macos-arm64`, `linux-x64` | omit = all | 📄 [24] (`windows-arm64` is listed; `linux-arm64` is not) |
| `wheels` | no | `["./wheels/x.whl"]` | relative paths | 🧠 |
| `[permissions]` | no | `files`, `network`, `clipboard`, `camera`, `microphone` | reason string each | 📄 [24] |
| `[build] paths_exclude_pattern` | no | `["__pycache__/", "/.git/", "/tests/"]` | gitignore-style | 🧠 |

**Table 2 – Manifest platform ↔ wheel tag** (population: official Blender builds)

| Manifest platform | Wheel platform tag | Note | Badge |
|---|---|---|---|
| `linux-x64` | `manylinux_2_17`/`2_28_x86_64` | Blender's Linux builds need glibc ≥ 2.28, so the tag must be ≤ 2_28 | 🧠 |
| `windows-x64` | `win_amd64` | MAX_PATH (260 chars) breaks deep packages under `%APPDATA%` | 🧠 |
| `windows-arm64` | `win_arm64` | newer builds only | ↔️ |
| `macos-arm64` | `macosx_11_0_arm64` (or `universal2`) | Apple Silicon | 🧠 |
| `macos-x64` | `macosx_10_x/11_0_x86_64` | Intel Mac builds reportedly end with 4.5 | ↔️ |

**Table 3 – Support windows for the CI matrix** (as of 2026-11-20)

| Line | Status | Support ends | Python ABI | Badge |
|---|---|---|---|---|
| 4.5 LTS | supported | Jul 2027 [14] | cp311 | 📄 date; 🧠 ABI |
| 5.2 LTS | released 14 Jul 2026 | Jul 2028 [12][13] | unconfirmed | ✅ exists (also required by FSKR [6]); 📄 dates |
| 5.3 | current feature release, 10 Nov 2026 [15] | until the next release | unconfirmed | 📄 |

**Table 4 – Candidate dependencies** (wheel sizes per platform, order of magnitude)

| Package | Licence | Wheel size | Verdict for this project | Badge |
|---|---|---|---|---|
| numpy | BSD-3 | 15–20 MB | never bundle; use Blender's | 🧠 |
| scipy | BSD-3 | 30–40 MB | avoid; write LM/sparse solves in NumPy; its minimum NumPy must be ≤ Blender's | 🧠 |
| opencv-python-headless | Apache-2.0 | 30–50 MB | not in the core | 🧠 |
| onnxruntime (CPU) | MIT | ≈ 5–15 MB | optional wheel for an in-process detector | 🧠 |
| mediapipe | Apache-2.0 | 30–50 MB + heavy dependencies | out of process only | 🧠 |
| Pillow | HPND / MIT-CMU | 2–5 MB | unnecessary; parse EXIF in pure Python | 🧠 |
| InsightFace buffalo_l recogniser | models non-commercial (reported) | ≈ 166 MB (`w600k_r50.onnx`) | never bundle | 📄 [17][23] |

**Table 5 – Headless flags**

| Flag / variable | Effect | Badge |
|---|---|---|
| `-b`, `--background` | no UI | 🧠 |
| `--factory-startup` | ignore user prefs and startup.blend | 🧠 |
| `--python-exit-code N` | exit N on an uncaught Python exception (0 = off, the default) | 📄 [29] |
| `-P file`, `--python-expr` | run a script or an expression | 🧠 |
| `--offline-mode` / `--online-mode` | force `online_access` | 🧠 |
| `-noaudio` | skip audio initialisation in containers | 🧠 |
| `BLENDER_USER_RESOURCES` | relocate all user directories | 📄 [29] |

## Applying this to photo→3D face sculpting in Blender

1. **Repository layout.**
   - `addon/` is the extension source: the manifest, `__init__.py`, `ops/`, `ui/`, `data/` and `engine/`.
   - `engine/` is a pure-NumPy subpackage that imports **nothing** from `bpy` or its parent package and uses only relative imports. It therefore runs both as `bl_ext.<repo>.face_likeness_fit.engine` and in plain CPython for pytest.
   - `tests/unit/` and `tests/blender/` sit outside `addon/` and are excluded from the build.
2. **The manifest for the core build:**
   ```toml
   schema_version = "1.0.0"
   id = "face_likeness_fit"
   version = "0.3.0"
   name = "Face Likeness Fit"
   tagline = "Fit a sculpt-ready head to photos of a consenting person"
   maintainer = "Project maintainers <maintainers@example.org>"
   type = "add-on"
   tags = ["Sculpt", "Modeling", "Camera"]
   blender_version_min = "4.5.0"
   license = ["SPDX:GPL-3.0-or-later"]
   copyright = ["2026 Project contributors"]

   [permissions]
   files = "Read reference photos and write landmark sidecar files"

   [build]
   paths_exclude_pattern = ["__pycache__/", "/.git/", "/*.zip", "/dev/"]
   ```
   - Omit `platforms`: the build is pure Python with no wheels, so one zip serves every OS 🧠.
   - Add `network = "Download optional landmark model weights"` only once a downloader exists.
   - Add `camera` only for webcam capture.
3. **Photos are biometric data.**
   - The core must work fully offline, with manual landmark clicking always available as the fallback.
   - Nothing uploads photos or sends telemetry.
   - Record consent (who, when, scope) in the JSON sidecar next to the landmarks.
   - State all of this in the listing text. A `network` permission on a face tool will, rightly, draw scrutiny 🧠.
4. **Detectors:**
   - **Path A (default):** an out-of-process helper in its own Python environment (MediaPipe) that exchanges JSON or `.npz` through files. This mirrors FaceFit's external solver [20] and keeps MediaPipe's dependency stack out of Blender 🧠.
   - **Path B:** an optional platform-split build carrying onnxruntime wheels plus a permissively licensed ONNX landmark model. The model is downloaded into `extension_path_user`, never zipped, and SHA-256-pinned 🧠.
5. **Data you may bundle:**
   - correspondence tables (landmark → vertex or barycentric point), versioned per template;
   - a CC0 or CC-BY base mesh from MPFB/MakeHuman, with attribution in `NOTICE` [1] 📄.
   - Load FLAME and similar non-commercial models from a user-supplied path [18] 📄.
6. **Licence hygiene:**
   - `LICENSE` (GPL-3.0 full text) at the zip root;
   - `# SPDX-License-Identifier: GPL-3.0-or-later` plus `SPDX-FileCopyrightText` in every file;
   - a `NOTICE` that lists each asset and wheel with its licence;
   - no ported code under NC or unknown licences 🧠.
7. **CI pipeline:**
   - pytest on the engine with CPython 3.11 + NumPy 1.26 and with 3.13 + NumPy 2.x;
   - `extension validate`, then `extension build`;
   - for each of 4.5, 5.2 and 5.3: `install-file -r user_default` into a temporary `BLENDER_USER_RESOURCES`, then `blender -b --factory-startup --python-exit-code 1 -P tests/blender/run.py`.
   - Inside the script, enable `bl_ext.user_default.face_likeness_fit` and run stdlib `unittest`, because Blender's Python has no pytest.
   - End with `sys.exit(0 if ok else 1)` 🧠.
8. **What goes wrong:**
   - absolute imports or `bl_info`-era `__name__` used as the preferences `bl_idname`; use `__package__`;
   - writing caches into the extension folder, where updates wipe them;
   - cp311 wheels on a Blender that bundles another Python;
   - a bundled numpy;
   - green CI without `--python-exit-code`;
   - tests that need timers or a 3D View under `-b`;
   - bit-exact goldens across 5.0's float32 buffer path [10];
   - slim Linux containers missing X11/GL shared libraries, even in background mode 🧠.

## Algorithmic implications

- **Dependency contract:**
  - the engine may import only `numpy`, `math`, `json` and `tomllib` (in the standard library since Python 3.11) 🧠;
  - it solves in float64 and converts to float32 only at the `foreach_set` boundary;
  - it avoids APIs that were removed in NumPy 2.
- **Capability probe** (`compat.py`, run once at `register()`): it returns `{blender, python_tag, numpy, online_access, platform, has_onnxruntime}`. Any optional backend that fails the probe is disabled with a UI message, never with a traceback 🧠.
- **Model registry as data:** each entry is `{name, url, sha256, bytes, licence, commercial_ok, needs_network}`. The rules are:
  - download only if `online_access` is on and the user has confirmed;
  - verify the hash before loading;
  - refuse `commercial_ok=false` by default, and keep such entries out of the package;
  - store files under `extension_path_user` 🧠.
- **Budgets (suggested defaults 🧠):**
  - core zip ≤ 5 MB (code + tables) and ≤ 25 MB with a template mesh;
  - optional platform zips ≤ 50 MB;
  - `register()` < 100 ms, with no NumPy work and no file I/O at import, and heavy modules imported lazily inside operators.
- **Version stamping:** read `version` from the installed `blender_manifest.toml` with `tomllib`. Write `{addon_version, blender, python, numpy, seed, solver_config}` into every fit sidecar 🧠.
- **Synthetic regression suite** (deterministic; `np.random.default_rng(seed)`):
  - **Setup:** template head scale s ≈ 0.14 m (bizygomatic width); 3–5 cameras at 0.5–1.5 m with a 50–85 mm full-frame-equivalent lens; 68–100 landmarks.
  - **Noiseless case:** reprojection RMS < 1e-6 px and vertex RMS < 1e-6·s.
  - **Gaussian noise case:** σ = 1 px. Expected RMS ≈ σ·√(1 − p/n) (p parameters, n residuals); fail above 1.2 σ.
  - **Goldens:** compare with `rtol = 1e-5` and never bit-exact, because BLAS builds and the 5.0 float32 path differ across platforms [10] 🧠.
- **Headless-safe architecture:**
  - the solve path uses `bpy.data`, `bmesh` and `foreach_get/set` only;
  - operators are thin wrappers that hold no logic;
  - timer and modal progress UI is optional, and the synchronous path must work under `-b` 🧠.
- **Licence as a solver constraint:** a prior, template or correspondence table with `commercial_ok=false` cannot be the default. Fitting must work with the CC0 template alone 🧠.

## Disagreements, myths & open questions

- **"Every add-on must be GPL"** ↔️: this is the Blender Foundation's and the FSF's reading, and it is untested in court. Commercial vendors comply by keeping their code GPL and selling assets, support and binaries; KeenTools loads a closed core, which is contested 🧠.
- **Myth: "permissions sandbox the add-on."** They only disclose 🧠.
- **Myth: "extensions killed legacy add-ons."** Install-from-disk still accepts `bl_info` zips 🧠.
- **Does Blender skip wheels whose tags do not match** (so one zip could carry cp311 and cp313 wheels), and which version wins when two extensions bundle the same package? ↔️, verify.
- **`blender_version_min` floor:** 4.2.0 (MPFB precedent [2], the sibling library notes) or 4.5.0 (only supported LTS lines) ↔️. Rule: declare only what CI actually tests.
- **Platform values:** whether `windows-arm64` is accepted and whether `linux-arm64` exists ↔️. Whether 5.0 dropped Intel Macs ↔️.
- **Open questions:**
  1. Which NumPy does 5.1–5.3 bundle, and which Python do 5.2 and 5.3 bundle (5.1 bundles 3.13 [28])?
  2. What upload size limit does extensions.blender.org set? (Unconfirmed: a site-tracker issue reports a 10 MB check raised to 200 MB, not official documentation [31].)
  3. Which non-GPL licences (MIT, BSD, GPL-2.0-or-later, multiple SPDX entries) does the platform accept for add-on code?
  4. May a listed extension download model weights under non-free terms at runtime, given user consent?
  5. What listing media are required (icon, featured image sizes)?

## Sources

[1] MPFB, Blender Extensions listing — https://extensions.blender.org/add-ons/mpfb/ — official listing — n.d. (via blender-face-addons harvest)
[2] MPFB version history, Blender Extensions — https://extensions.blender.org/add-ons/mpfb/versions/ — official listing — 2026 (via blender-face-addons harvest)
[3] mpfb2 LICENSE.CODE.md — https://github.com/makehumancommunity/mpfb2/blob/master/LICENSE.CODE.md — repo — n.d. (via blender-face-addons harvest)
[4] makehumancommunity/mpfb2 — https://github.com/makehumancommunity/mpfb2 — repo — n.d. (via blender-face-addons harvest)
[5] Face Shape Key Rig (Blender Extensions) — https://extensions.blender.org/add-ons/face-shapekey-rig/ — official listing — n.d. (via blender-face-addons harvest)
[6] Fragid/face-shapekey-rig — https://github.com/Fragid/face-shapekey-rig — repo — n.d. (via blender-face-addons harvest)
[7] H0wZy/captureforge (GPL-3.0 Blender extension suite) — https://github.com/H0wZy/captureforge — repo — n.d. (via blender-face-addons harvest)
[8] Simple Camera Match (Blender Extensions listing) — https://extensions.blender.org/add-ons/simple-camera-match/ — official listing — n.d. (via portrait-lighting-compare harvest)
[9] voki6/perspective-match (Blender extension, fSpy solver port) — https://github.com/voki6/perspective-match — repo — n.d. (via reference-camera-setup harvest)
[10] Blender 5.0: Python API — https://developer.blender.org/docs/release_notes/5.0/python_api/ — official-docs — 2025 (via blender-version-status-2026 harvest)
[11] Blender 5.0: Corrective Releases — https://developer.blender.org/docs/release_notes/5.0/corrective_releases/ — official-docs — 2025 (via blender-version-status-2026 harvest)
[12] 5.2 LTS — Blender (download/releases) — https://www.blender.org/download/releases/5-2/ — official-docs — 2026 (via blender-version-status-2026 harvest)
[13] Blender 5.2 LTS — https://www.blender.org/releases/5-2/ — official-docs — 2026 (via blender-version-status-2026 harvest)
[14] Release Notes — Blender (index) — https://www.blender.org/download/releases/ — official-docs — n.d. (via blender-version-status-2026 harvest)
[15] Blender Release Notes — Developer Documentation (index) — https://developer.blender.org/docs/release_notes/ — official-docs — n.d. (via blender-version-status-2026 harvest)
[16] Compatibility index — Blender Developer Documentation — https://developer.blender.org/docs/release_notes/compatibility/ — official-docs — n.d. (via blender-version-status-2026 harvest)
[17] InsightFace model zoo docs — https://github.com/deepinsight/insightface/blob/master/python-package/docs/model_zoo.md — repo — n.d. (via identity-embeddings harvest)
[18] peizhiyan/flame-head-tracker — https://github.com/peizhiyan/flame-head-tracker — repo — n.d. (via multi-view-fitting harvest)
[19] philgras/video-head-tracker — https://github.com/philgras/video-head-tracker — repo — n.d. (via multi-view-fitting harvest)
[20] VGCLUB/facefit-mpfb — https://github.com/VGCLUB/facefit-mpfb — repo — n.d. (via craniometric-landmarks harvest)
[21] Projects to Look Forward to in 2026 — https://www.blender.org/development/projects-to-look-forward-to-in-2026/ — official-docs — 2026 (release cadence; via blender-version-status-2026 harvest)
[22] Faceit (Superhive) — https://superhivemarket.com/products/faceit — commercial listing — n.d. (via blender-face-addons harvest)
[23] wangyifan349/insightface-face-similarity — https://github.com/wangyifan349/insightface-face-similarity — repo (third-party) — n.d. (via identity-embeddings harvest)
[24] How to Create Extensions, Blender 5.2 LTS Manual — https://docs.blender.org/manual/en/latest/advanced/extensions/getting_started.html — official-docs — 2026 (added in verification)
[25] Extension manifest schema 1.0.0, Blender Developer Documentation — https://developer.blender.org/docs/features/extensions/schema/1.0.0/ — official-docs — 2026 (added in verification)
[26] Terms of Service, Blender Extensions — https://extensions.blender.org/terms-of-service/ — official — 2026 (added in verification)
[27] Python Wheels, Blender 5.2 LTS Manual — https://docs.blender.org/manual/en/latest/advanced/extensions/python_wheels.html — official-docs — 2026 (added in verification)
[28] Blender 5.1: Python API — https://developer.blender.org/docs/release_notes/5.1/python_api/ — official-docs — 2026 (added in verification)
[29] Command Line Arguments, Blender 5.3 Manual — https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html — official-docs — 2026 (added in verification pass 2)
[30] Extensions Command Line Arguments, Blender 5.2 LTS Manual — https://docs.blender.org/manual/en/latest/advanced/command_line/extension_arguments.html — official-docs — 2026 (added in verification pass 2)
[31] Support for uploading larger file sizes #130, extensions-website tracker — https://projects.blender.org/infrastructure/extensions-website/issues/130 — issue tracker — n.d. (added in verification pass 2)

**Further reading (by name, not yet linked)**
- Blender Extensions developer handbook: "Getting started", "Manifest", "Python Wheels", "Command-line arguments", "Creating an extensions repository"
- extensions.blender.org: Terms of Service and the extension guidelines and policies
- Blender Manual: Command Line Arguments; Add-ons and Extensions preferences
- Blender Python API reference: `bpy.utils.extension_path_user`, `bpy.app.online_access`
- GNU GPL v3 text; FSF "Frequently Asked Questions about the GNU Licenses" (plugins, aggregation, compatible licences)
- SPDX License List; REUSE specification (FSFE)
- Python Packaging User Guide: platform compatibility tags (PEP 425, PEP 600 manylinux, PEP 384 stable ABI)
- `fake-bpy-module` (PyPI); `bpy` module on PyPI
- NumPy 2.0 migration guide and the ABI notes for downstream packages
- GDPR Article 9 (biometric data as a special category)

## Verification log (2026-11-20)

- **Manifest schema 1.0.0** (required keys, tagline ≤64, `blender_version_max` exclusive, five permission keys, platform values): confirmed. https://docs.blender.org/manual/en/latest/advanced/extensions/getting_started.html ; https://developer.blender.org/docs/features/extensions/schema/1.0.0/ . `windows-arm64` is listed; `linux-arm64` is not.
- **extensions.blender.org licensing and rules**: corrected. Add-ons must be GPL v3-or-later (themes GPL-compatible), non-code assets CC0, no remote code or externally downloaded components, no pre-compiled external packages; `bpy.app.online_access` check confirmed in the manual. Runtime `pip install` ban not explicitly found (unconfirmed). https://extensions.blender.org/terms-of-service/ ; https://docs.blender.org/manual/en/latest/advanced/extensions/getting_started.html
- **Bundled Python**: Blender 5.1 bundles Python 3.13, confirmed. https://developer.blender.org/docs/release_notes/5.1/python_api/ . 4.1–4.5 = cp311 and 5.2/5.3 versions remain unconfirmed.
- **Wheels**: corrected. Wheels extract into the extension's own site-packages, not a shared per-repository one; `--split-platforms` per-platform zips confirmed. Skipping of non-matching wheel tags: unconfirmed. https://docs.blender.org/manual/en/latest/advanced/extensions/python_wheels.html

## Verification log, pass 2 (2026-11-20)

- **Headless CI flags** (`--python-exit-code` default 0 = disabled; `extension install-file -r REPO -e`; `BLENDER_USER_RESOURCES`): confirmed. https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html ; https://docs.blender.org/manual/en/latest/advanced/command_line/extension_arguments.html . Not explicitly seen in the results: `-b`, `--factory-startup`, `-P`, and how `BLENDER_USER_RESOURCES` interacts with `install-file` (left 🧠).
- **extensions.blender.org upload size limit**: unconfirmed. Only a tracker issue reports a 10 MB check raised to 200 MB (not official, undated). https://projects.blender.org/infrastructure/extensions-website/issues/130
- **Blender 5.0 dropping Intel macOS (macos-x64)**: unconfirmed; no usable evidence in the results. Left as is.
