# Guided workflow and accessibility for non-expert users

> Artists who are not reconstruction experts rarely fail in the solver. They fail upstream, with wide-angle selfies, smiles, hair over the ears or mirrored photos, and in correction, by pinning ambiguous points, over-pinning or trusting one view. The tools that work for novices share three patterns. They coach capture with immediate, specific feedback (RealityScan, Scaniverse, Apple's Face ID ring); they keep edits inside a plausible shape space (MetaHuman, FaceBuilder rigidity); and they make every step cheap to undo. For a Blender add-on that means a stepwise sidebar workflow built on Blender's own conventions (poll messages, operator reports, non-blocking modal solves, undo-aware data), NumPy photo checks that explain problems in plain words, and pin overlays that show pin type and error by shape as well as colour. It also means a per-vertex "measured vs guessed" map, and a user-pin σ that depends on landmark class, expertise and zoom instead of one constant. No web harvest or earlier draft existed for this topic, so every claim below is expert knowledge awaiting verification.
>
> Evidence status: 0 ✅ / 0 📄 / 76 🧠 / 9 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Where novices actually fail**
- About in order of damage: (1) close or wide-angle capture (phone selfie at 30–50 cm), which enlarges the nose and hides the ears; (2) a different expression in each photo, usually a slight smile; (3) hair hiding ears, hairline and jaw; (4) mirrored front-camera images; (5) pins on shadows and highlights instead of forms, such as the nasolabial shadow edge or the specular dot on the nose tip; (6) over-pinning one view while the others stay unpinned, which fits 2D but leaves depth wrong. 🧠 See [likeness mistakes](../community/likeness-mistakes.md) and [camera distortion](../reconstruction/camera-perspective-distortion.md).
- **Anchoring:** people place a pin where the overlaid model already is. With the overlay visible, user pins and model agree more than the photo justifies. 🧠 (anchoring after Tversky & Kahneman 1974; not measured for this task)

**UX patterns in existing tools** (all time-sensitive; check current versions)
- **KeenTools FaceBuilder:** one camera per photo; auto-align drafts pins; any surface point can be pinned and the head re-solves live while you drag; shape and expression rigidity sliders; texture baked from views. It gives no capture coaching, no photo-quality score and no uncertainty display. 🧠 See [FaceBuilder](./facebuilder-blender.md).
- **Reallusion Headshot (Character Creator):** a quick auto mode from one photo, then a pro mode with a few named alignment points shown against a reference illustration, and region morph or sculpt refinement. Headshot 2 added mesh-to-head with alignment points. ↔️ (feature names vary by version)
- **MetaHuman (Mesh to MetaHuman / Identity):** you frame a neutral view ("promote frame") and the auto-tracker draws editable contour curves for lids, lips and brows, not loose points. An identity solve then conforms the template. Creator edits blend between presets and drag region handles inside a learned space, so even novices cannot make an implausible face. Since UE 5.6 (2025) Creator runs inside the editor rather than streamed from the cloud. ↔️ (version and licence terms change)
- **Polycam / RealityScan / Scaniverse (capture apps):** auto-shutter while you move, a running photo count, and AR or painted coverage that shows which parts of the subject are captured. RealityScan's coverage map uses a red-to-green scale, which colour-blind users cannot read. Scaniverse processes on the device, which suits biometric data. RealityScan was also Epic's 2025 new name for the RealityCapture desktop app. 🧠 (UI details and ownership are time-sensitive)
- **Apple Face ID / Persona / spatial-audio head scan:** a segmented ring fills as the head turns, plus spoken or text cues ("move your head slowly", "turn to the side") and a separate ear step. This is the best-known pose-coverage pattern. 🧠
- **FaceGen PhotoFit (older):** places a fixed point list one at a time, each with a thumbnail showing where it goes. Slow, but novices rarely misidentify points. 🧠

**Blender conventions an add-on should follow**
- The 2.5-era paradigms are non-blocking, non-modal and non-overlapping (William Reynish's UI paper). So long fits must not freeze the UI, and modes should be few and visible. 🧠 Blender also publishes Human Interface Guidelines in its developer documentation (wording, tooltips, layout). 🧠
- **Panels:** sidebar (`VIEW_3D`/`UI`, own `bl_category` tab), sub-panels via `bl_parent_id`, `use_property_split = True`, `DEFAULT_CLOSED` for expert options. `poll()` controls availability. Prefer greying out (`layout.active/enabled`) to hiding, so features stay discoverable. 🧠
- **Operators:** `bl_options={'REGISTER','UNDO'}`. `cls.poll_message_set("…")` (Blender ≥3.0) explains in the tooltip why a button is disabled, which is plain-language feedback for free. `self.report({'ERROR'|'WARNING'|'INFO'}, msg)` writes to the status bar and Info log. Return `{'CANCELLED'}`; never let a traceback reach the user. 🧠
- **Modal tools:** confirm with LMB/Enter and cancel with RMB/Esc. Show key hints in the status bar with `workspace.status_text_set()` (it accepts a draw function, so mouse icons can be shown) and in the header with `area.header_text_set()`. Clear both on exit. 🧠
- **Progress:** `wm.progress_begin/update/end` shows only a number at the cursor. For a cancellable fit, use a modal operator with `event_timer_add`, a time budget per tick and a `UILayout.progress()` bar (Blender ≥4.0 ↔️). `bpy` is not thread-safe: compute in a worker thread on copied NumPy arrays and write to Blender data only from the main thread. 🧠
- **Undo:** state in Python globals is not undone, so pins and fit state must live in ID data (PropertyGroups, attributes, shape keys). Undo invalidates Python references to Blender data, so re-resolve objects by name or pointer after `undo_post`. Push one undo step per pin drag, on release. 🧠
- **Overlays:** `SpaceView3D.draw_handler_add(..., 'WINDOW', 'POST_PIXEL')` with `gpu` and `blf`. `bgl` was removed in 4.0, along with the `2D_`/`3D_` shader prefixes. Use `POLYLINE_*` shaders for lines wider than 1 px, because line width is not honoured on Metal or Vulkan. Scale every size by `preferences.system.ui_scale`. ↔️ (API churn; re-check on 5.x)
- **Accessibility reach:** Blender exposes no UI to screen readers, so the practical audience is people with low vision (UI scale, themes), colour-vision deficiency (CVD), motor limits (keyboard, tablet, large targets) and cognitive load (plain language, checkpoints). Register add-on keymaps in `keyconfigs.addon` so every key is remappable, and make each action an operator so it can be found with F3 search. 🧠

**Photo checks and plain-language feedback**
- ISO/IEC 29794-5 (face image quality) and BSI's open-source OFIQ reference implementation define per-component scores: sharpness, under- and over-exposure, dynamic range, illumination uniformity, head pose, expression neutrality, eyes open, mouth closed, occlusion, inter-eye distance and more. Re-implement the cheap measures in NumPy rather than bundling OFIQ. 🧠 (licence and status time-sensitive)
- Those standards assume one frontal passport photo. Here pose is a coverage target across the set, not a pass/fail per photo. 🧠
- Express sharpness as variance of the Laplacian on a face crop resampled to a fixed IOD. Judge it relative to the set's median, because absolute thresholds depend on camera and content. 🧠
- MediaPipe blendshape scores catch expression problems (smile, open jaw, blink, raised brows). They are not calibrated probabilities, so compare each photo with the one the user marks as most neutral. 🧠
- Ears, hairline and beard need hair or face segmentation. MediaPipe's hair segmenter is Apache-2.0. Face-parsing models trained on CelebAMask-HQ have ear classes but non-commercial terms. ↔️ See [licences](../ethics/licences-tos.md).
- Each message should say what is wrong, why it matters and how to fix it, with an icon and words rather than colour alone, and never with jargon. For example: "Photo 3 was taken from about 40 cm, so the nose will come out larger than it is. Retake from 1.5 m or more and zoom in." Let the user override ("use anyway"), and record the override in the report. 🧠

**Pin interaction and colour**
- Red–green CVD affects about 8 % of men and 0.5 % of women of Northern European ancestry, roughly one male artist in twelve. 🧠
- Okabe–Ito ("Color Universal Design", 2008) and the viridis and cividis colormaps stay distinguishable under the common CVD types. Still encode by shape as well (circle = detector pin, square = user pin, ✕ = conflict, hollow = hidden or occluded). 🧠
- WCAG 2.2 sets non-text contrast at 3:1, text at 4.5:1 and a minimum target of 24×24 CSS px. Pins drawn over skin of any tone need a dark outline plus a light halo to reach 3:1 against both. 🧠
- Precise placement under the cursor needs an offset magnifier, as in Shift (Vogel & Baudisch 2007). Shift-drag for fine motion and arrow-key nudges also give keyboard-only access. 🧠
- Epipolar guidance: once a landmark exists in one view, draw its epipolar line in the other views. Placing the pin far from the line is the clearest sign that the user identified a different point. 🧠

**Showing what is guessed**
- Novices read animated draws from a posterior ("hypothetical outcome plots", Hullman et al. 2015) more accurately than error bars. Error bars invite misreading, such as treating values inside the bar as more likely (Newman & Scholl 2012). 🧠
- Areas that stay prior-driven in a standard capture: the hair-covered cranium, the back of the head, the forehead under a fringe, the jaw under a beard, the submental area without a low view, nasal depth without ¾ or profile views, inner ear detail, eye globes, and teeth. 🧠 See [hair](./hair-blender.md) and [forehead and hairline](../anatomy/forehead-brow-temple-hairline.md).

**How accurately people place landmarks**
- Trained operators on 3D stereophotogrammetry: about 0.5–1 mm for crisp points (canthi, cheilia, subnasale), 1–2 mm for moderate ones (alare, pronasale, soft-tissue nasion vertically), and 2–4 mm or more for palpation-defined points (gonion, zygion, orbitale, menton). 🧠 (Toma et al. 2009; Plooij et al. 2009; Aynechi et al. 2011; Fagertun et al. 2014). This matches the library's CBCT result that gonion has the largest observer error ([craniometric landmarks](../anatomy/craniometric-landmarks.md)).
- On 2D web photos, human labellers disagree by roughly 3–6 % of IOD across full 68-point sets, comparable to good detectors, with contours dominating. The commonly cited COFW human figure is about 5.6 % (pupil normalisation). ↔️
- Contour error is anisotropic: mostly along the curve, which is why ADNet and STAR model it. 🧠
- Novices are typically 1.3–2× worse than trained annotators on ambiguous points and similar on crisp corners. Illustrated definitions and feedback close much of the gap within one session. Most error comes from the definition, not from hand motion: at full zoom, mouse pointing error is under 1 screen px. 🧠

**Tutorials and testing**
- Effective in-tool learning follows minimalist instruction (Carroll, *The Nurnberg Funnel*, 1990): real tasks, error recovery, and little reading. Short demonstration clips in tooltips (ToolClips, Grossman & Fitzmaurice 2010) and stencil-style step highlighting (Kelleher & Pausch 2005) beat manuals for discovery. 🧠
- Methods: think-aloud, heuristic evaluation (Nielsen), cognitive walkthrough, Cognitive Dimensions (Green & Petre 1996), SUS (Brooke 1996), NASA-TLX and the Creativity Support Index (Cherry & Latulipe 2014). Cognitive Dimensions fits pin tools well: "hidden dependencies" (a pin moves a distant region), "viscosity" and "premature commitment". 🧠

## Numbers & reference tables

**Table 1 — Photo checks: suggested defaults** (design heuristics to calibrate on real capture sets, not standards; IOD = outer inter-canthal distance, about 88 mm adult; MediaPipe blendshape scores 0–1)

| Check | Measure | Warn | Exclude / block | Badge |
|---|---|---|---|---|
| Face present | detector | – | 0 faces: block; >1 face: ask which | 🧠 |
| Face resolution | outer IOD in px | <250 px (texture suffers) | <100 px (ICAO/ISO frontal minimum is ~90–120 px between eyes) | ↔️ |
| Sharpness | var(Laplacian), face crop at IOD = 256 px | <0.6× set median | <0.3× set median | 🧠 |
| Clipped highlights | % face pixels with any channel ≥250 (8-bit) | >1 % | >5 % | 🧠 |
| Crushed shadows | % face pixels ≤5 | >2 % | >10 % | 🧠 |
| Lighting asymmetry | L/R cheek luminance ratio | >1.5 : 1 | >2.5 : 1 (texture use) | 🧠 |
| Camera distance | Z ≈ f_px · 88 mm / IOD_px | <1.2 m | <0.7 m (strong warn) | 🧠 |
| EXIF focal (35 mm eq.) | with face filling frame | <35 mm | <28 mm | 🧠 |
| Eyes closed | eyeBlink_L/R | >0.4 | >0.6: lids ignored in this view | 🧠 |
| Mouth open | jawOpen | >0.10 | >0.25: excluded from identity | 🧠 |
| Smile | mouthSmile_L/R | >0.25 | >0.5: excluded from identity | 🧠 |
| Brows raised / frown | browInnerUp, browDown | >0.35 | – | 🧠 |
| Expression consistency | L2 of 52-vector vs marked-neutral photo | >0.4 | >0.8 | 🧠 |
| Glasses | detector or user tick | any | – (lenses shift apparent eye size and position) | 🧠 |
| Hairline hidden | hair fraction of forehead band | >50 %: "forehead will be guessed" | – | 🧠 |
| Ear hidden | ear-region visibility in views with \|yaw\| ≥60° | <50 % | – | 🧠 |
| Mirrored photo | flip test (see Algorithmic) | flip lowers RMSE >30 % | – | 🧠 |

**Table 2 — Landmark placement error and suggested user-pin σ** (σ for the normal direction at full image resolution, before the motor term; % of outer IOD at 88 mm)

| Class | Examples | Trained error (mm) | Novice error (mm) | User σ (mm) | ≈ % IOD | Tangent σ | Badge |
|---|---|---|---|---|---|---|---|
| Crisp corners | en, ex, ch, sn, iris centre, closed stomion | 0.5–1.0 | 0.8–1.5 | 0.8 expert / 1.2 novice | 0.9 / 1.4 | same | 🧠 |
| Vermilion midline | ls, li | 0.5–1.0 | 1.0–1.5 | 1.0 | 1.1 | 2.0 mm | 🧠 |
| Feature contours | lid margins, vermilion, alar rim | 0.5–1.0 normal | 1.0–1.5 | 1.0 | 1.1 | free (point-to-curve) | 🧠 |
| Profile silhouettes | nose, forehead, chin edge | 0.5–1.0 if sharp | 1.0–1.5 | 1.0 | 1.1 | free | 🧠 |
| Nose tip | prn | 1–2 | 2–3 | 2.0 | 2.3 | 2.0 | ↔️ |
| Soft-tissue nasion | n′ / se | x 0.5–1, y 2–4 | y 3–5 | x 1.0, y 3.5 | 1.1 / 4 | – | 🧠 |
| Alar base | ac, al, sbal | 1–1.5 | 1.5–2.5 | 1.8 | 2.0 | – | 🧠 |
| Ear points (side views) | sa, sba, obs, obi, t | 1–2 | 2–3 | 2.5 | 2.8 | – | 🧠 |
| Palpation-defined | go, zy, or, me, g | 2–4+ | 3–6 | 4–5, or offer as curve only | 4.5–5.7 | – | ↔️ |
| Hair-defined | trichion, brows | 2–5 | 3–8 | 5; never for the skull fit | 5.7 | – | 🧠 |
| Motor term | any | 0.5–1 screen px | 0.7–1.5 screen px | × (image px / screen px) at placement zoom | – | – | 🧠 |

Combine as σ = √(σ_class² + σ_motor²). At fit-to-window zoom on a 12 MP photo (≈4 image px per screen px, ≈10 px/mm) a 1-px slip is about 0.4 mm. At 100 % zoom it can be ignored. 🧠

**Table 3 — Pose coverage targets** (yaw: + = subject's left side towards the camera)

| View | Yaw | Pitch | Priority | Constrains | Badge |
|---|---|---|---|---|---|
| Frontal | 0 ± 5° | 0 ± 5° | required | widths, eye and mouth shape, asymmetry, texture | 🧠 |
| ¾ left and right | ±30–45° | 0 ± 10° | required | nose projection, cheek and jaw depth, triangulation baseline | 🧠 |
| Profiles | ±80–90° | 0 | strongly advised | nose, brow and chin profile; ear position (detectors fail, so use silhouette and pins) | 🧠 |
| Low (camera below) | 0–30° | −15 to −25° | advised | submental, jaw underside, nostrils | 🧠 |
| High (camera above) | 0 | +15 to +20° | optional | brow ridge, top of head | 🧠 |
| Ear close-ups | ±90° | 0 | optional | helix, concha, lobule | 🧠 |

Minimum viable set: frontal plus both ¾ (3 photos). Good: 5–7 photos at ≥1.5 m with the same expression throughout. 🧠 See [reference photography protocol](../community/reference-photography-protocol.md).

**Table 4 — Colour and target-size defaults** (Okabe–Ito hex values)

| Role | Colour | Shape | Badge |
|---|---|---|---|
| Detector/auto pin | sky blue #56B4E9 | filled circle, dark outline | 🧠 |
| User pin | orange #E69F00 | filled square, dark outline | 🧠 |
| Conflict (>3σ) | vermillion #D55E00 | ✕ plus residual line | 🧠 |
| Selected | yellow #F0E442 | ring, 2 px | 🧠 |
| Model silhouette and contours | bluish green #009E73 | 1.5–2 px polyline | 🧠 |
| Prior-driven region | reddish purple #CC79A7 | hatching, not fill | 🧠 |
| Residual magnitude | cividis bins: <1σ, 1–2σ, 2–3σ, >3σ | line length ×1 (×3 optional, labelled) | 🧠 |
| Pin size / hit radius | 9 px / 12 px × `ui_scale` (hit area ≥24 px wide) | – | 🧠 |
| Contrast | graphics ≥3:1, text ≥4.5:1 (WCAG 2.2) | dark outline + light halo | 🧠 |

**Table 5 — User-testing parameters**

| Item | Value | Badge |
|---|---|---|
| Formative think-aloud | ~5 users per round, ≥3 rounds | ↔️ (the "5 users find 85 %" claim varies widely by task) |
| Summative task metrics | ≥15–20 users for usable confidence intervals | 🧠 |
| SUS | 0–100; cross-study mean ≈68; ≥80 is roughly the top 10–15 % | 🧠 |
| Pin-accuracy test | synthetic renders with known landmarks; report RMS mm per class | 🧠 |
| Likeness judgement | ≥5 people familiar with the subject, blind A/B against the photo | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **One sidebar tab with numbered stages:** Consent → Photos → Check → Cameras → Landmarks → Fit → Confidence → Hand-off.
   - Each stage shows a "done when" line and has its own sub-panel.
   - "Next" is enabled by `poll()`; when it is disabled, `poll_message_set` says why ("2 photos still have blocking issues").
   - Experts can expand all panels. Nothing is hidden, only greyed out. 🧠
2. **Normalise, then check.** Bake EXIF orientation, convert HEIC and keep the originals. Run Table 1 and show one card per photo: thumbnail, icon, one-line problem, one-line fix, and "use anyway". Above the cards, draw a pose ring (Table 3 bins) that fills as views are added, and name the missing view in words ("add a photo from your left side"). 🧠
3. **Cameras:** load each photo as the camera background image. Lock the solved transforms and turn off Lock Camera to View. Report per-view error in millimetres ("this photo disagrees by about 1.5 mm"), never as "RMSE px". 🧠 See [reference cameras](./reference-camera-setup.md).
4. **Landmark review as a queue, like a spell checker.** Sort auto pins by normalised residual and use Tab/Shift+Tab for next/previous problem. Each pin shows its name in words plus its anthropometric code, a small illustration, and the epipolar line from other views. For the first pins of each view, hide the model overlay while placing them ("blind" placement) to avoid anchoring. 🧠
5. **Pin tool as a `WorkSpaceTool`**, so it has a toolbar icon and shortcut.
   - Click places a pin; drag moves it, with an offset loupe.
   - Shift-drag moves at ¼ speed; arrows nudge 1 image px and Shift+arrows 0.25 px.
   - X/Delete removes; H/Alt+H hides and reveals (Blender conventions).
   - The status bar shows the keys while the tool is active. 🧠
6. **Live re-solve on drag** at ≥20 fps, with 2–5 warm-started LM iterations per mouse event. If an iteration is slower than ~50 ms, show a ghost target and solve on release. Highlight the regions that move during the drag, so far-away changes are not a surprise. 🧠
7. **Rigidity in words:** a slider from "Stay close to an average head" to "Follow my pins exactly", which maps internally to λ_shape = 10^(2r−1). 🧠
8. **Confidence stage:** the overlay shows three hatched levels (measured / partly / guessed) with ±mm on hover. A "wobble" button plays 8–12 posterior samples. A list names the guessed regions together with the next best photo to take. 🧠
9. **Hand-off:** write the result to a `likeness` shape key. Store `f3d_support` (0–1) and `f3d_sigma_mm` as point attributes, and offer an operator that copies (1 − support) into the sculpt mask. Measured regions are then protected while the artist sculpts the guessed ones. 🧠 (that the mask is stored as attribute `.sculpt_mask` in 4.x is ↔️; verify).

**What goes wrong:**
- **Over-pinning.** Suggest at most ~3–5 user pins per feature per view, and warn when one view holds more than 60 % of all user pins.
- **Pinning in one view only:** depth stays a guess.
- **Hair pinned as skull.**
- **Light pinned instead of form:** the nose tip placed on the highlight, the nasolabial pin on the shadow edge.
- **Orbiting in camera view** breaks the camera match.
- **Pins kept in Python globals** desync after Ctrl+Z.
- **A blocking solve** makes Blender look frozen and gets force-quit.
- **Red/green-only status.** 🧠

## Algorithmic implications

- **Pin record:** `Pin{view, xy_px, target: surface(tri,bary) | curve_id, cls, sigma_n_mm, sigma_t_mm, source ∈ {user, auto}, expertise, zoom_at_place, blind}`. Store it in a PropertyGroup on the head object so it is undo-safe. A user pin replaces auto pins of the same feature within ~3 % IOD. 🧠
- **Engine mapping:** `face3d/solve/bundle.py` has one scalar `ViewObs.sigma_px` plus per-landmark `weights`. Encode per-pin σ as `w_i = (sigma_px / σ_i,px)²` now. Later, accept `(N,)` or `(N,2,2)` covariances, so that contours are point-to-curve (tangent σ → ∞) and nasion is anisotropic. Use σ_i,px = √(σ_class² + σ_motor²) · px_per_mm (Table 2), and a Huber threshold of 2σ. 🧠
- **Expertise and self-calibration:**
  - Default to the novice column.
  - An optional 2-minute onboarding asks the user to place 6 crisp landmarks twice on a sample face at different zooms. Take σ_rep = RMS(difference)/√2 and σ_class,crisp = max(σ_rep + 0.3 mm convention allowance, 0.5 mm).
  - During use, if the MAD-based scale of a class's whitened user-pin residuals stays above 1.5 across views, inflate that class's σ. 🧠
- **Library default disagreement:** the current user-pin default of 0.75 % IOD (about 0.66 mm with outer IOD) suits experts on crisp corners only. For novices or soft points it over-weights the user by a factor of about 3–30 in information terms. Treat as ↔️ until a pin study is run.
- **Conflict detection:** a normalised residual >3σ after the solve, or an epipolar distance >3σ, flags the pin, and the UI explains it in mm. 🧠
- **Mirror test:** solve each view with and without an x-flip. If the flipped photo lowers that view's RMSE by more than 30 % while the others are unchanged, flag it as probably mirrored. Never auto-flip. 🧠
- **Distance check:** Z = f_px · 88 mm / IOD_px (SD ≈ 5 mm means about ±6 % error). Warn below 1.2 m. 🧠
- **Expression gating:** views over the Table 1 limits get identity weight × 0.25 or are excluded. Per-view expression coefficients get a strong zero-mean prior. 🧠
- **Support map:**
  - Propagate the posterior to vertices: Σ_v = B Σ_θ Bᵀ for a linear basis, or use `point_sigma_mm` from the bundle for landmarks interpolated with the warp weights.
  - Support s = 1 − σ_post²/σ_prior², with bins at ≥0.7 "measured", 0.3–0.7 "partly" and <0.3 "guessed". 🧠
- **Next-best photo:** for each candidate pose in Table 3, score the expected drop in the trace of the posterior covariance over guessed vertices (visible vertices only), and suggest the top one. 🧠
- **Check API:** pure NumPy functions return `{code, severity, value, threshold, msg_key, fix_key}`. Messages are translatable via `bpy.app.translations`. Thresholds are relative to the photo-set median where content-dependent. Nothing is sent over the network, and nothing is logged unless the user opts in. 🧠
- **Solve scheduling:** a modal timer with a 30–50 ms budget per tick, Esc to cancel (the last good state is kept), and one undo step per committed solve. 🧠

## Disagreements, myths & open questions

- **"More pins make a better likeness."** Myth. Beyond a few per feature, extra pins mostly add the user's noise and conflicts between views. 🧠
- **"Detectors are more accurate than people."** ↔️ On crisp points they are comparable on benchmarks. But detectors pull towards the mean face, while a zoomed-in human catches identity-specific shape. Disagreement between human labellers sets a floor on benchmark error.
- **The "5 users" rule** ↔️: fine for iterative formative rounds, wrong for estimating rates.
- **Showing uncertainty to novices:** ↔️ HOPs help, but extra overlays add load. Make the hatching optional, and on by default only at the Confidence stage.
- **Live re-solve while dragging:** ↔️ experts find it fast; novices may be confused when distant regions move. Test both against "solve on release".
- **IOD definition in the library is inconsistent** ↔️: notes mix outer inter-canthal (~88 mm) and interpupillary (~63 mm) distance, a 1.4× difference in every %-IOD σ. Standardise on outer IOD, and store σ in mm with % as a derived value.
- **Open:** there is no published study of novice pin accuracy in photo-to-head tools. Run one with synthetic renders (known ground truth) before freezing Table 2.
- **Open:** how well MediaPipe blendshape thresholds transfer across age, ethnicity and facial hair. Calibrating against the user's own neutral photo is the safe default.
- **Time-sensitive:** vendor UX features, MetaHuman licence terms, RealityScan naming and Scaniverse ownership all change yearly.

## Sources

No web harvest or earlier draft existed for this topic, so no URLs are cited here. Related library notes (internal): [FaceBuilder](./facebuilder-blender.md), [face add-ons](./blender-face-addons.md), [reference cameras](./reference-camera-setup.md), [extension packaging](./blender-extensions-packaging.md), [landmark detection](../reconstruction/landmark-detection.md), [commercial head tools](../reconstruction/commercial-head-tools.md), [craniometric landmarks](../anatomy/craniometric-landmarks.md), [reference photography protocol](../community/reference-photography-protocol.md), [biometric privacy](../ethics/biometric-privacy.md).

**Further reading (by name, not yet linked)**
- Reynish, W. — The Evolution of Blender's User Interface (2008)
- Blender Developer Documentation — Human Interface Guidelines; Blender Python API reference (Operator, UILayout, gpu, WorkSpace)
- ISO/IEC 29794-5 — Face image quality; BSI — OFIQ (Open Source Face Image Quality)
- ISO/IEC 19794-5 and ICAO Doc 9303 — portrait image requirements
- Okabe, M. & Ito, K. — Color Universal Design (2008)
- Nuñez, Anderton & Renslow — cividis colormap, PLoS ONE (2018)
- W3C — Web Content Accessibility Guidelines (WCAG) 2.2 (2023)
- Vogel, D. & Baudisch, P. — Shift: a technique for operating pen-based interfaces using touch, CHI 2007
- Hullman, Resnick & Adar — Hypothetical Outcome Plots, PLoS ONE (2015)
- Newman, G. & Scholl, B. — Bar graphs depicting averages are perceptually misinterpreted, Psychonomic Bulletin & Review (2012)
- Burgos-Artizzu, Perona & Dollár — Robust face landmark estimation under occlusion (COFW), ICCV 2013
- Toma et al. — Reproducibility of facial soft tissue landmarks on 3D laser-scanned facial images, Orthod Craniofac Res (2009)
- Plooij et al. — Reproducibility and reliability of 3D soft tissue analysis using stereophotogrammetry, Int J Oral Maxillofac Surg (2009)
- Aynechi et al. — Accuracy and precision of a 3D anthropometric facial analysis with and without landmark labeling, Angle Orthodontist (2011)
- Fagertun et al. — 3D facial landmarks: inter-operator variability of manual annotation, BMC Medical Imaging (2014)
- Liu et al. — Semantic alignment: finding semantically consistent ground-truth for facial landmark detection, CVPR 2019
- Carroll, J. M. — The Nurnberg Funnel (1990)
- Grossman, Fitzmaurice & Attar — A survey of software learnability, CHI 2009; Grossman & Fitzmaurice — ToolClips, CHI 2010
- Kelleher & Pausch — Stencils-based tutorials, CHI 2005
- Green & Petre — Cognitive Dimensions of Notations, J Visual Languages & Computing (1996)
- Brooke — SUS: a "quick and dirty" usability scale (1996); Hart & Staveland — NASA-TLX (1988)
- Cherry & Latulipe — Creativity Support Index, ACM TOCHI (2014)
- Nielsen & Landauer — A mathematical model of the finding of usability problems, INTERCHI 1993; Faulkner — Beyond the five-user assumption (2003)
- Tversky & Kahneman — Judgment under uncertainty: heuristics and biases, Science (1974)
