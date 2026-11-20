# Running MediaPipe / OpenCV / ONNX inside Blender

> Blender runs its own bundled CPython (3.11 in 4.1–4.5; unconfirmed for 5.x) with its own NumPy. Every compiled wheel must therefore match Blender's CPython tag, OS/architecture and NumPy ABI, and must never replace that NumPy. There are three ways to deliver MediaPipe, OpenCV or ONNX Runtime: pip into a private folder at runtime (an "Install dependencies" button), per-platform wheels bundled in a 4.2+ extension, or an out-of-process worker that exchanges files or socket messages with Blender. Existing face tools lean toward the third: mediapipe-facecap splits a MediaPipe "transmitter" from a Blender "receiver" [1], and the FaceFit prototype solves in an external server [2]. For a photo→head tool, run the fitter as pure NumPy inside Blender, run ONNX Runtime (or MediaPipe) on the CPU in an isolated worker as the default detector, and keep a dependency-free JSON landmark import as the fallback. The CPU has more than enough headroom for still photos (tens of ms per image). The real constraints are import time, install size, and whether wheels exist for each new Blender Python.
>
> Evidence status: 1 ✅ / 19 📄 / 63 🧠 / 13 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Blender's Python**
- Official builds bundle CPython and NumPy in `<X.Y>/python/`. `sys.executable` points to that interpreter, which has been the case since about 2.91; before that it was `bpy.app.binary_path_python` 🧠. Bundled versions: 3.9 (2.93–3.0), 3.10 (3.1–4.0), 3.11 (4.1–4.5) 🧠.
- 5.x: the 5.0.1 release fixed "the Python 3.14 build" and a test for Python newer than 3.11 [18] 📄. Those fixes concern builds against newer system Pythons and do not show that the bundle changed. 5.1–5.3 may bundle 3.11 or 3.13 ↔️. 5.3 is the current release [21] 📄, and 5.2 LTS is supported until Jul 2028 [19] 📄.
- Since 5.0, `mathutils` exposes a float32, non-contiguous buffer to NumPy [17] 📄. This matters at the bridge, not for detector output.
- By default Blender ignores `PYTHONPATH` and the user site-packages; `--python-use-system-env` turns them back on 🧠. That explains the classic case where pip reports success but Blender cannot import the package: `pip install --user` run via `sys.executable` writes to a user site that the subprocess sees and Blender does not 🧠 (moderate confidence).
- `bpy.utils.user_resource('SCRIPTS', path="modules")` is on `sys.path` at startup and is separate for each Blender version 🧠.
- Distro-packaged Blender (Arch, Debian, Fedora) uses the system Python, so the cp tag differs and pip stops with PEP 668 "externally-managed-environment". Snap and Microsoft Store installs are read-only 🧠.

**Delivery mechanisms**
- **Runtime pip.** Run `[sys.executable, "-m", "ensurepip"]`, then `pip install --target DIR --only-binary=:all: --no-deps …`. Official bundles include ensurepip, and recent ones already include pip 🧠 (moderate confidence).
- **Extension wheels (4.2+).** List the files in `blender_manifest.toml` as `wheels = ["./wheels/…whl"]` together with `platforms` (`windows-x64`, `windows-arm64`, `macos-arm64`, `macos-x64`, `linux-x64`). Blender extracts them on install into a site-packages directory that all extensions share (`extensions/.local/lib/pythonX.Y/site-packages`) 🧠. `blender --command extension build --split-platforms` builds one zip per platform 🧠. Because the directory is shared, two extensions that bundle different versions of the same package collide ↔️ (resolution rule unverified).
- **extensions.blender.org policy:** add-ons may not pip-install or download executable code at runtime, so dependencies ship as bundled wheels; code must be GPL-compatible; network access must be declared as a `network` permission and gated on `bpy.app.online_access` 🧠 (time-sensitive; verify).
- **Out of process.** Two variants: Blender's own interpreter in isolated mode (`[sys.executable, "-I", "worker.py"]`) with a private deps folder that can hold its own NumPy, or a separate Python/venv of any version 🧠. Either way a native crash in the worker cannot take unsaved sculpt work with it 🧠. Precedents: the transmitter/receiver split [1] 📄, and FaceFit, which fits MPFB2 heads using 57 of MediaPipe's 478 points with an external MCP solver and was tested on 4.2.3 LTS [2] 📄. MPFB2 itself has no ML dependencies and targets "4.2 LTS and newer" [22] 📄.
- **Native core download.** KeenTools FaceBuilder fetches a per-platform core library, online or from a file, instead of using pip 🧠. Its 2021.1 auto-alignment uses "a couple of neural networks" to place pins, and manual correction is still sometimes needed [3] 📄.
- **Other precedents:** BlendArMocap (MediaPipe → Rigify) had a preferences button that pip-installed mediapipe, often needed admin rights on Windows, and its maintenance has stalled 🧠. Dream Textures used pip or per-platform release zips holding multi-GB PyTorch 🧠.

**The packages**
- **MediaPipe** (Apache-2.0 code 🧠). The Tasks `FaceLandmarker` returns 478 landmarks: 468 mesh points plus iris points at 468–477 [8][9][10][11] ✅. It optionally adds 52 blendshape scores in [0, 1], off by default (`output_face_blendshapes`) [4][5][6] 📄. Labels are relative to the subject, so a mirrored input swaps L/R [4] 📄. Doc pages disagree on the detector input (192² vs 128²); both give the landmarker as 256² [4][7] ↔️. The model ships separately as `face_landmarker.task` 🧠. Desktop Python runs on the CPU via TFLite/XNNPACK, and the GPU delegate is effectively Linux-only 🧠. Wheels are built per CPython version and appear late for new Pythons. pip metadata pulls `opencv-contrib-python`, `matplotlib`, `protobuf` (pinned `<5` in many 0.10.x releases), and in some releases `jax`/`jaxlib` 🧠. The legacy `mp.solutions` API is deprecated and may be missing in recent wheels ↔️.
- **MediaPipe without mediapipe.** Community ONNX conversions of the Face Mesh weights exist [10] 📄, so onnxruntime plus NumPy can replace the whole mediapipe dependency tree. Check the conversion's licence 🧠.
- **ONNX Runtime** (MIT 🧠). The CPU wheel is built per cp tag. macOS wheels include the CoreML execution provider 🧠. `onnxruntime-gpu` and `onnxruntime-directml` provide the same import name, so they conflict with the CPU package 🧠. NumPy-2-built releases begin around 1.19 ↔️.
- **OpenCV** (Apache-2.0 since 4.5 🧠). The PyPI wheels are `abi3`: one wheel per OS/arch covers CPython ≥ 3.7, so it survives a Blender Python bump 🧠. The four variants (`opencv-python`, `-headless`, `-contrib-python`, `-contrib-python-headless`) all install `cv2`, so never install two of them 🧠. Inside Blender, use headless. In `solvePnP`, EPnP needs n ≥ 4 points, DLS silently falls back to EPnP, and points must be undistorted first [16] 📄.
- **NumPy ABI:** a wheel compiled against NumPy 1.x will not import under NumPy 2. A wheel built against NumPy 2 also runs on 1.x 🧠. 5.x's NumPy is unconfirmed, so ship NumPy-2-built wheels ↔️.
- **Heavier models:** InsightFace buffalo_l is ≈ 326 MB, and its w600k_r50.onnx (≈ 166 MB) outputs 512-D embeddings [13][14] 📄. Its weights are reportedly for non-commercial research only, a secondary claim [13] ↔️. Keep it out of any default that ships.

## Numbers & reference tables

**Table 1 – Bundled interpreter and required wheel tag**

| Blender | CPython | Wheel tag | NumPy | Badge |
|---|---|---|---|---|
| 2.93–3.0 | 3.9 | cp39 | 1.2x | 🧠 |
| 3.1–4.0 | 3.10 | cp310 | 1.2x | 🧠 |
| 4.1–4.5 LTS (until Jul 2027 [20]) | 3.11 | cp311 | ≈1.24–1.26 | 🧠 (📄 support date) |
| 5.0 | 3.11 likely | cp311 | unknown | ↔️ [18] |
| 5.1–5.3; 5.2 LTS until Jul 2028 | 3.11 or 3.13 | cp311 / cp313 | 1.26 or 2.x | ↔️ [19][21] |

**Table 2 – Packages (one platform, CPU builds)**

| Package | Licence | ABI | Wheel MB | Installed incl. deps, MB | Cold `import`, s | Badge |
|---|---|---|---|---|---|---|
| mediapipe 0.10.x | Apache-2.0 | per cp | 30–60 | 150–400 | 0.5–3 | 🧠 |
| onnxruntime | MIT | per cp | 5–20 | 20–60 | 0.2–1 | 🧠 |
| opencv-python-headless | Apache-2.0 | abi3 | 30–50 | 80–130 | 0.1–0.5 | 🧠 |
| opencv-contrib-python | Apache-2.0 | abi3 | 40–70 | 100–160 | 0.2–0.6 | 🧠 |

**Table 3 – Model files**

| Model | Size | Input | Output | Badge |
|---|---|---|---|---|
| face_landmarker.task | ≈3–4 MB | detector 128² or 192²; mesh 256² | 478 pts (+52 blendshapes) | ↔️ input [4][7]; 🧠 size |
| Face Mesh ONNX conversion | 1–5 MB | 192–256² | 468/478 pts | 📄 exists [10]; 🧠 size |
| OpenCV Zoo YuNet detector | < 0.5 MB | e.g. 320² | box + 5 pts | 🧠 |
| buffalo_l (SCRFD-10G + R50) | 326 MB; R50 166 MB | 640² / 112² | box+5 pts / 512-D | 📄 [13][14] |
| Depth Anything V2 Small | 25 M params; 60 ms (hardware not captured) | 518² | relative depth | 📄 [15] |

**Table 4 – Per-still-image CPU cost** (4–8 performance cores, AVX2 x86-64 or Apple M-series; model already loaded)

| Stage | Time | Badge |
|---|---|---|
| Decode a 24 MP JPEG (cv2) | 80–250 ms | 🧠 |
| Same via `bpy.data.images.load` + `pixels.foreach_get` | 0.4–2 s; 384 MB float32 RGBA | 🧠 |
| Face detection (BlazeFace/YuNet) | 2–10 ms | 🧠 |
| Face mesh 256² | 3–15 ms | 🧠 |
| Full FaceLandmarker incl. blendshapes | 10–40 ms | 🧠 |
| 3DDFA_V2 detection, 720p, ONNX | ≈15 ms (dominant stage); ">50 fps" claimed | 📄 [12] |
| SCRFD-10G 640² / ArcFace R50 112² | 30–100 / 15–50 ms | 🧠 |
| Depth Anything V2 Small 518² | 0.15–0.8 s | 🧠 |
| Session/model creation | 50–500 ms | 🧠 |
| Worker spawn + imports | 1–4 s (first run on Windows with antivirus: 10–20 s) | 🧠 |

A TFLite reimplementation of 3DDFA_V2 also claims real-time CPU performance [23] 📄 (a community claim).

**Table 5 – OS specifics (official builds)**

| OS | Interpreter | Typical failures | Badge |
|---|---|---|---|
| Windows | `…\Blender X.Y\X.Y\python\bin\python.exe` | Program Files is not writable (pip "defaults to user installation"); 260-char MAX_PATH; a loaded `.pyd` stays locked until restart; antivirus slows the first import; Store installs are read-only; CUDA DLLs need `os.add_dll_directory`; spawn workers with `CREATE_NO_WINDOW` | 🧠 |
| macOS | `Blender.app/Contents/Resources/X.Y/python/bin/python3.x` | writing inside the signed `.app` is blocked or breaks the signature; arm64 vs x86_64 wheels (Intel builds dropped in 5.0 ↔️); manually downloaded files carry the quarantine xattr | 🧠 |
| Linux tarball | `…/X.Y/python/bin/python3.x` | non-headless OpenCV pulls in Qt/xcb; snap is read-only; Flatpak keeps config under `~/.var/app/org.blender.Blender/`; distro builds use the system Python | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Keep the fitter dependency-free.** The landmark/shape solver needs only the NumPy that Blender bundles, so it runs on every OS and version. Detection is a plug-in with three tiers: (a) worker process (default), (b) in-process ONNX Runtime from bundled or pip-installed wheels, (c) importing a landmark JSON produced anywhere. Tier (c) is also your test harness.
2. **If you install in-process, use one command shape** 🧠:
   ```python
   target = bpy.utils.extension_path_user(__package__, path="deps", create=True)
   subprocess.run([sys.executable, "-m", "pip", "install", "--no-input",
       "--disable-pip-version-check", "--only-binary=:all:", "--no-deps",
       "--target", target, "onnxruntime==<pin>", "opencv-python-headless==<pin>"],
       check=True, env={**os.environ, "PYTHONNOUSERSITE": "1"})
   sys.path.append(target)   # append, never insert(0): Blender's NumPy must win
   ```
   `--no-deps` stops pip from pulling in a second NumPy. Add only the pure-Python dependencies that a clean `import` actually asks for. Gate the call on `bpy.app.online_access` and an explicit user click.
3. **Verify after install.** Check that `numpy.__file__` is still inside Blender's bundle, that `cv2.__file__` and `onnxruntime.__file__` are in `target`, and run a one-image smoke test. Log `sys.version`, `numpy.__version__`, the package versions, and the model's SHA-256.
4. **Feed the detector correctly.** Bake EXIF orientation into the pixels. Un-mirror selfie-camera shots, because a mirrored image swaps L/R [4]. Pass RGB (`cv2.imread` returns BGR; MediaPipe wants `ImageFormat.SRGB`) as 8-bit sRGB, not linear. If you read pixels through bpy, note that rows run bottom-up and must be flipped. Downscale to a long side of ≤ 2048 px for detection, then map back with the half-pixel rule x = (x′+0.5)·s − 0.5 🧠.
5. **Know the precision ceiling.** The landmarker resamples the face to 256², so one model pixel ≈ face width / 256 image pixels. For a face 1500 px wide that is about 6 px. More megapixels do not buy sub-pixel landmarks, but more views and a good solver do 🧠.
6. **Keep the UI alive.** Run inference in a worker thread or process. ONNX Runtime and MediaPipe release the GIL. Poll with `bpy.app.timers` and never touch `bpy` off the main thread. Cap ORT at (physical cores − 2) threads, so it doesn't fight Blender's TBB pool during sculpting 🧠.
7. **What goes wrong:** a pip-installed NumPy shadows Blender's ("compiled using NumPy 1.x cannot be run in NumPy 2.x", or Blender's own scripts break). `opencv-python` and `opencv-contrib-python` both get installed, leaving a corrupt `cv2`. cp311 wheels stop working after a Blender Python bump. An admin-run install leaves root-owned files. Windows refuses to update a locked `.pyd`. A detector finds two faces in a mirror or on a poster. A selfie flips L/R. EXIF rotation is ignored, so landmarks land on a sideways image. MediaPipe/absl `CHECK` failures abort the whole process, which is why the worker is the default 🧠.

## Algorithmic implications

- **Backend interface:** `detect(image_rgb_uint8, meta) → {points[N,2] px (origin at top-left, y down), visibility[N], scheme:"mp478"|"yunet5"|…, image_wh, exif_applied, mirrored, backend, backend_version, model_sha256}`. The fitter consumes only this contract. MediaPipe's normalised x,y are multiplied by W,H. Its z is relative and scaled roughly like x, so it gets weight 0 for multi-view solves 🧠.
- **Landmark noise priors** (starting values, 🧠; tune on held-out photos), with u = face width in px / 256:
  - inner features (eye and mouth corners, alar base, pupils): σ = 0.6u, iris centre 0.4u;
  - brows: 1.0u;
  - jawline and cheek contour: treat as point-to-curve with σ_normal = 1.5u and σ_tangent ≥ 5u, since contour points slide along the silhouette;
  - YuNet/SCRFD 5-point: σ ≈ 2–3 % of inter-ocular distance.
- **Gates:** require exactly one face with detection confidence ≥ 0.6. MediaPipe's defaults are 0.5 for detection, presence and tracking 🧠. After the multi-view solve, flag a view whose inner-point RMS reprojection exceeds 3σ, because the usual causes are mirroring, EXIF rotation or a wrong focal length. If two backends are available, flag points where they disagree by more than 3σ.
- **Defaults:**
  - ORT: `intra_op_num_threads = max(1, physical_cores − 2)`, `inter_op_num_threads = 1`, `ORT_ENABLE_ALL`, `providers=["CPUExecutionProvider"]`;
  - MediaPipe: `running_mode=IMAGE`, `num_faces=2` (to detect the ambiguity), `output_face_blendshapes=True` only when you are neutralising expressions;
  - worker timeout: 60 s on the first run, 10 s per image afterwards 🧠.
- **Determinism:** XNNPACK and MLAS kernels differ by instruction set (AVX2, AVX-512, NEON), so golden tests should allow about 0.05 px of drift across machines and stay exact only on the same machine 🧠.
- **Probes rather than version checks:** `importlib.util.find_spec("onnxruntime")`, `numpy.__version__ >= "2"`, the wheel tag from `sys.version_info`, and `bpy.app.online_access`. Disable a backend with a clear message instead of failing at registration.
- **Packaging matrix:** the per-platform wheel set is {win-x64, macos-arm64, linux-x64} × {cp311, plus cp313 if confirmed}, with OpenCV abi3 covering every cp tag. Leave out mediapipe on platforms without wheels (such as windows-arm64 🧠) and fall back to the ONNX conversion [10].

## Disagreements, myths & open questions

- **Schools of thought** ↔️: never modify Blender's Python and always use a worker (isolation, any Python, crash safety); bundled extension wheels as the only store-compliant option; runtime pip as the most convenient route for GitHub-distributed tools. This note backs the worker as the default and wheels as the store build.
- **Myth: "run Blender as administrator to install dependencies."** It leaves root-owned files in the install tree that the next update overwrites. Install per user instead 🧠.
- **Myth: "MediaPipe needs a GPU."** The desktop Python package runs on the CPU, and still photos take tens of ms 🧠.
- **Myth: "extension wheels are private to each add-on."** The site-packages directory is shared, so versions collide ↔️.
- **Myth: "MediaPipe z is metric depth."** It is relative and biased toward the mean face 🧠.
- **Open questions:**
  1. Which Python and NumPy do 5.1, 5.2 LTS and 5.3 bundle?
  2. Does mediapipe publish cp313 and NumPy-2-built wheels, and does `mp.solutions` survive?
  3. What size cap does extensions.blender.org apply, and how is its no-runtime-download rule worded?
  4. Do onnxruntime and mediapipe ship windows-arm64 wheels?
  5. What licence terms cover the face_landmarker model card and the ONNX conversion [10]?
  6. Did 5.0 really drop Intel Macs?

## Sources

[1] mozi1924/mediapipe-facecap-for-blender — https://github.com/mozi1924/mediapipe-facecap-for-blender — repo — n.d. (blender-face-addons harvest)
[2] VGCLUB/facefit-mpfb (FaceFit MPFB2 Blender add-on prototype) — https://github.com/VGCLUB/facefit-mpfb — repo — n.d. (craniometric-landmarks harvest)
[3] FaceBuilder for Blender 2021.1 is out: now with AI (Blender Artists) — https://blenderartists.org/t/facebuilder-for-blender-2021-1-is-out-now-with-ai/1294243 — forum — 2021
[4] MediaPipe Face Landmarker (Google AI Edge) — https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker — official docs — n.d.
[5] MediaPipe Face landmark detection guide for Python — https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python — official docs — n.d.
[6] mp.tasks.vision.FaceLandmarkerResult API — https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/FaceLandmarkerResult — official docs — n.d.
[7] Face Landmarker (ai.google.dev page) — https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker — official docs — n.d.
[8] MediaPipe Face Mesh (legacy docs mirror) — https://mediapipe.readthedocs.io/en/latest/solutions/face_mesh.html — official docs — n.d.
[9] MediaPipe Face Mesh: All 478 Landmark Points (DEV Community) — https://dev.to/metsander/mediapipe-face-mesh-all-478-landmark-points-5ec8 — blog — n.d.
[10] yakhyo/mediapipe-face-mesh-onnx README — https://github.com/yakhyo/mediapipe-face-mesh-onnx/blob/main/README.md — repo — n.d.
[11] cornpip/mediapipe_face_mesh — https://github.com/cornpip/mediapipe_face_mesh — repo — n.d.
[12] cleardusk/3DDFA_V2 — https://github.com/cleardusk/3DDFA_V2 — repo — 2020
[13] InsightFace python-package model_zoo.md — https://github.com/deepinsight/insightface/blob/master/python-package/docs/model_zoo.md — repo doc — 2024
[14] wangyifan349/insightface-face-similarity (third-party README) — https://github.com/wangyifan349/insightface-face-similarity — repo — n.d.
[15] Depth Anything V2 (alphaXiv mirror of arXiv 2406.09414) — https://www.alphaxiv.org/abs/2406.09414 — paper — 2024
[16] OpenCV calib3d solvePnP (4.x docs) — https://docs.opencv.org/4.x/d5/d1f/calib3d_solvePnP.html — official docs — 2026
[17] Blender 5.0: Python API — https://developer.blender.org/docs/release_notes/5.0/python_api/ — official docs — 2025
[18] Blender 5.0: Corrective Releases — https://developer.blender.org/docs/release_notes/5.0/corrective_releases/ — official docs — 2025
[19] 5.2 LTS — Blender — https://www.blender.org/download/releases/5-2/ — official docs — 2026
[20] Release Notes — Blender (index) — https://www.blender.org/download/releases/ — official docs — n.d.
[21] Blender Release Notes — Developer Documentation (index) — https://developer.blender.org/docs/release_notes/ — official docs — n.d.
[22] MPFB version history, Blender Extensions — https://extensions.blender.org/add-ons/mpfb/versions/ — official listing — 2026
[23] 1996scarlet/Dense-Head-Pose-Estimation (3DDFAv2 TFLite reimplementation) — https://github.com/1996scarlet/Dense-Head-Pose-Estimation — repo — 2020

No harvest or earlier draft existed for this topic, so every URL above comes from a sibling harvest in this library. Related notes: `blender-version-status-2026.md`, `bpy-mesh-api.md`, `blender-face-addons.md`.

**Further reading (by name, not yet linked)**
- Blender Extensions handbook (`blender_manifest.toml`, "Python Wheels") and the extensions.blender.org moderation guidelines
- Blender Manual, command-line arguments (`--python-use-system-env`, `--offline-mode`)
- PEP 425, 427, 384 (abi3), 600 (manylinux) and 668 (externally managed environments)
- Python documentation: `ensurepip`, `site`, the `-I` isolated mode
- NumPy 2.0 migration guide (ABI notes for downstream packages)
- ONNX Runtime documentation: threading and execution providers; opencv-python wheel README (variants)
- Kartynnik et al., "Real-time Facial Surface Geometry from Monocular Video on Mobile GPUs", 2019; Bazarevsky et al., "BlazeFace", 2019
- Wu, Peng, Yu, "YuNet: A Tiny Millisecond-level Face Detector", 2023; Guo et al., SCRFD, 2021
- BlendArMocap (cgtinker) and Dream Textures (carson-katri), as dependency-installer precedents; uv / python-build-standalone (Astral) for provisioning a worker Python
