# Guided workflow and accessibility for non-expert users

> Non-expert artists rarely fail in the solver; they fail at capture (wide-angle selfies, smiles, hair over the ears, mirrored photos) and in correction (pinning ambiguous points, over-pinning one view). Tools that work for novices coach capture with immediate feedback (RealityScan, Scaniverse, Apple's Face ID ring), keep edits inside a plausible shape space (MetaHuman, FaceBuilder rigidity) and make every step cheap to undo. A Blender add-on should be a staged sidebar workflow built on Blender's conventions, with NumPy photo checks that explain problems in plain words. Overlays should mark pin type and error by shape as well as colour, the head should carry a "measured vs guessed" map, and user-pin σ should depend on landmark class, expertise and zoom. No harvest or earlier draft existed, so every claim here is expert knowledge awaiting verification.
>
> Evidence status: 0 ✅ / 0 📄 / 92 🧠 / 17 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Where novices fail**
- Roughly in order of damage:
  - Selfies at 30–50 cm (bigger nose, hidden ears).
  - A different expression per photo, usually a slight smile.
  - Hair over ears, hairline or jaw.
  - Mirrored front-camera images.
  - Pins on light instead of form (nose-tip highlight, nasolabial shadow edge).
  - Many pins in one view and none elsewhere, so 2D fits but depth stays wrong.

  🧠 See [likeness mistakes](../community/likeness-mistakes.md) and [camera distortion](../reconstruction/camera-perspective-distortion.md).
- **Anchoring:** with the model overlay visible, people place pins where the model already is. 🧠

**UX patterns in existing tools** (time-sensitive)
- **FaceBuilder:**
  - One camera per photo; auto-align drafts the pins.
  - Any surface point can be pinned, and the head re-solves live while you drag.
  - Rigidity sliders.
  - No capture coaching, quality score or uncertainty display.

  🧠 See [FaceBuilder](./facebuilder-blender.md).
- **Headshot:** a one-photo auto mode, and a pro mode with named alignment points shown on a reference illustration, plus region morphs. Headshot 2 adds mesh input. ↔️
- **MetaHuman Identity:** on a promoted neutral frame the tracker draws editable *contour curves* for lids, lips and brows, not loose points. Creator edits stay inside a learned space (preset blending, region handles), so novices cannot make an implausible face. ↔️ (moved into the editor around UE 5.6; licence terms change)
- **Polycam, RealityScan and Scaniverse:**
  - Auto-shutter, a photo count, and AR or painted coverage of what is captured.
  - RealityScan's coverage map is red-to-green, which colour-blind users cannot read.
  - Scaniverse processes on the device, which suits biometric data.

  🧠 (time-sensitive)
- **Apple Face ID / Persona enrolment:** a segmented ring fills as the head turns, with text cues and a separate ear step. This is the canonical pose-coverage widget. 🧠
- **FaceGen PhotoFit:** points are placed one at a time, each with a thumbnail showing where it goes. Slow, but novices rarely misidentify a point. 🧠

**Blender conventions**
- **Principles:** Blender 2.5's UI principles are non-blocking, non-modal and non-overlapping (Reynish), and the developer docs hold Human Interface Guidelines. A fit must never freeze the UI. 🧠
- **Panels:** sidebar tab (`bl_category`), `bl_parent_id` sub-panels, `use_property_split`, and `DEFAULT_CLOSED` for expert options. Grey out with `layout.enabled/active` instead of hiding. 🧠
- **Operators:**
  - Use `{'REGISTER','UNDO'}`.
  - `poll_message_set()` (≥3.0) explains in the tooltip why a button is disabled.
  - `self.report({'ERROR'|'WARNING'|'INFO'}, msg)` writes to the status bar and Info log.
  - Never let a traceback reach the user.

  🧠
- **Modal tools:** LMB/Enter confirms and RMB/Esc cancels. `workspace.status_text_set()` takes a draw function, so it can show mouse-icon hints. 🧠
- **Progress:** `wm.progress_*` shows only a number at the cursor. Use a modal timer with a per-tick budget and `UILayout.progress()` (≥4.0 ↔️). `bpy` is not thread-safe, so compute on copied arrays and write on the main thread only. 🧠
- **Undo:** Python globals are not undone, so keep pins and fit state in ID data (PropertyGroups, attributes, shape keys). Re-resolve references after `undo_post`, and push one undo step per drag release. 🧠
- **Overlays:** draw with `POST_PIXEL` handlers using `gpu` and `blf`. `bgl` and the `2D_`/`3D_` shader names went in 4.0. Use `POLYLINE_*` shaders for lines wider than 1 px (Metal and Vulkan ignore line width), and scale sizes by `ui_scale`. ↔️
- **Accessibility reach:** Blender exposes nothing to screen readers, so target low vision (UI scale, themes), colour-vision deficiency (CVD), motor limits (remappable `keyconfigs.addon` keymaps, F3-searchable operators, tablet) and cognitive load. 🧠

**Photo checks and feedback**
- ISO/IEC 29794-5 and BSI's open-source OFIQ define per-component face-image quality scores: sharpness, exposure, illumination uniformity, pose, expression neutrality, eyes open, mouth closed, occlusion and inter-eye distance. They assume one frontal photo; here pose is a coverage target across the set. Reimplement the cheap measures in NumPy. 🧠 (licence and status time-sensitive)
- **Sharpness:** variance of the Laplacian on a face crop resampled to a fixed IOD, judged against the set median. 🧠
- **Expression:** MediaPipe blendshape scores catch smiles, open jaws, blinks and raised brows. They are not calibrated probabilities, so compare against the photo the user marks as most neutral. 🧠
- **Ears, hairline and beard:** these need segmentation. MediaPipe's hair segmenter is Apache-2.0; CelebAMask-HQ face-parsing models are non-commercial. ↔️ See [licences](../ethics/licences-tos.md).
- **Messages:** each gives the problem, why it matters and the fix, as icon plus words, never colour alone. For example: "Photo 3 was taken from about 40 cm, so the nose will come out too large. Retake from 1.5 m or more and zoom in." Offer "use anyway" and log the override. 🧠

**Pins, colour and uncertainty**
- Red–green CVD affects about 8 % of men and 0.5 % of women of Northern European ancestry. Okabe–Ito, viridis and cividis survive the common types; encode by shape too. 🧠
- WCAG 2.2 sets 3:1 contrast for graphics, 4.5:1 for text and a 24×24 px minimum target. Pins over any skin tone need a dark outline *and* a light halo. 🧠
- **Precision aids:** an offset magnifier (Shift, Vogel & Baudisch 2007), Shift-drag and arrow-key nudges. Draw the landmark's **epipolar line** from other views: a pin far off the line means a different point was picked. 🧠
- Animated posterior draws (hypothetical outcome plots, Hullman et al. 2015) are read more accurately than error bars (Newman & Scholl 2012). 🧠
- **Usually prior-driven regions:** cranium under hair, forehead under a fringe, jaw under a beard, submental without a low view, nasal depth without ¾ views, ear detail, eye globes and teeth. 🧠

**Human landmark placement error**
- Trained operators on 3D stereophotogrammetry:
  - Crisp points (canthi, cheilia, subnasale): about 0.5–1 mm.
  - Alare, pronasale and nasion (vertical): 1–2 mm.
  - Palpation-defined points (gonion, zygion, orbitale, menton): 2–4 mm or more.

  🧠 (Toma 2009; Plooij 2009; Aynechi 2011; Fagertun 2014). This agrees with the library's CBCT finding that gonion is worst ([craniometric landmarks](../anatomy/craniometric-landmarks.md)).
- On 2D web photos, human labellers disagree by about 3–6 % IOD across 68-point sets, comparable to good detectors and dominated by contours. COFW's human figure is about 5.6 %. ↔️
- Error runs mostly *along* contours. 🧠
- Novices are about 1.3–2× worse than trained annotators on ambiguous points and similar on crisp corners. Illustrated definitions with feedback close much of the gap within one session. 🧠
- At full zoom, pointing error is under 1 screen px, so the definition dominates. 🧠

**Learning and testing**
- **Learning:** minimalist instruction (Carroll 1990) means real tasks, error recovery and little reading. ToolClips and stencil-style step highlighting aid discovery. 🧠
- **Testing:** think-aloud, heuristic evaluation, cognitive walkthrough, SUS, NASA-TLX and the Creativity Support Index. Cognitive Dimensions (Green & Petre 1996) names the pin-tool traps: *hidden dependencies* and *premature commitment*. 🧠

## Numbers & reference tables

**Table 1 — Photo checks: suggested defaults** (heuristics to calibrate, not standards; IOD = outer inter-canthal distance ≈ 88 mm; blendshape scores 0–1)

| Check | Measure | Warn | Exclude / block | Badge |
|---|---|---|---|---|
| Face present | detector | >1 face: ask | 0 faces | 🧠 |
| Resolution | outer IOD px | <250 | <100 (ICAO/ISO frontal min ≈90–120 px eye distance) | ↔️ |
| Sharpness | var(Laplacian), crop at IOD = 256 px | <0.6× set median | <0.3× median | 🧠 |
| Clipped highlights | % face px, any channel ≥250 | >1 % | >5 % | 🧠 |
| Crushed shadows | % face px ≤5 | >2 % | >10 % | 🧠 |
| Lighting asymmetry | L/R cheek luminance | >1.5 : 1 | >2.5 : 1 for texture | 🧠 |
| Camera distance | Z ≈ f_px·88 mm / IOD_px | <1.2 m | <0.7 m | 🧠 |
| EXIF focal, 35 mm eq. | face fills frame | <35 mm | <28 mm | 🧠 |
| Eyes closed | eyeBlink | >0.4 | >0.6: ignore lids in view | 🧠 |
| Mouth open | jawOpen | >0.10 | >0.25: drop from identity | 🧠 |
| Smile | mouthSmile | >0.25 | >0.5: drop from identity | 🧠 |
| Expression drift | L2 of 52-vector vs neutral photo | >0.4 | >0.8 | 🧠 |
| Hairline hidden | hair share of forehead band | >50 % | – (forehead guessed) | 🧠 |
| Ear hidden | ear visibility, \|yaw\| ≥60° | <50 % | – | 🧠 |
| Mirrored | flip test | flip lowers RMSE >30 % | – | 🧠 |

**Table 2 — Landmark placement error and user-pin σ** (normal direction, full resolution; % of 88 mm outer IOD)

| Class | Examples | Trained (mm) | Novice (mm) | User σ (mm) | % IOD | Tangent | Badge |
|---|---|---|---|---|---|---|---|
| Crisp corners | en, ex, ch, sn, iris centre | 0.5–1.0 | 0.8–1.5 | 0.8 exp / 1.2 nov | 0.9 / 1.4 | same | 🧠 |
| Vermilion midline | ls, li | 0.5–1.0 | 1.0–1.5 | 1.0 | 1.1 | 2.0 mm | 🧠 |
| Contours | lid margins, vermilion, alar rim | 0.5–1.0 | 1.0–1.5 | 1.0 | 1.1 | free | 🧠 |
| Profile silhouettes | nose, brow, chin edge | 0.5–1.0 | 1.0–1.5 | 1.0 | 1.1 | free | 🧠 |
| Nose tip | prn | 1–2 | 2–3 | 2.0 | 2.3 | 2.0 | ↔️ |
| Soft-tissue nasion | n′, se | x 0.5–1 / y 2–4 | y 3–5 | x 1.0 / y 3.5 | 1.1 / 4 | – | 🧠 |
| Alar base | ac, al, sbal | 1–1.5 | 1.5–2.5 | 1.8 | 2.0 | – | 🧠 |
| Ear points | sa, sba, obs, obi, t | 1–2 | 2–3 | 2.5 | 2.8 | – | 🧠 |
| Palpation-defined | go, zy, or, me, g | 2–4+ | 3–6 | 4–5 or curve only | 4.5–5.7 | – | ↔️ |
| Hair-defined | trichion, brows | 2–5 | 3–8 | 5; never skull | 5.7 | – | 🧠 |
| Motor term | any | 0.5–1 screen px | 0.7–1.5 screen px | × image px per screen px | – | – | 🧠 |

σ = √(σ_class² + σ_motor²). On a 12 MP photo at fit-to-window zoom (≈4 image px per screen px, ≈10 px/mm), a 1 px slip is ≈0.4 mm. 🧠

**Table 3 — Pose coverage** (minimum: frontal + both ¾; good: 5–7 photos at ≥1.5 m, one expression)

| View | Yaw | Pitch | Priority | Constrains | Badge |
|---|---|---|---|---|---|
| Frontal | 0 ± 5° | 0 ± 5° | required | widths, eye and mouth shape, asymmetry, texture | 🧠 |
| ¾ L and R | ±30–45° | 0 ± 10° | required | nose projection, cheek and jaw depth | 🧠 |
| Profiles | ±80–90° | 0 | strongly advised | nose, brow and chin profile; ear position | 🧠 |
| Low | 0–30° | −15 to −25° | advised | submental, jaw underside, nostrils | 🧠 |
| High | 0 | +15 to +20° | optional | brow ridge, top of head | 🧠 |
| Ear close-ups | ±90° | 0 | optional | helix, concha, lobule | 🧠 |

**Table 4 — Overlay encoding** (Okabe–Ito hex; sizes × `ui_scale`)

| Role | Colour | Shape | Badge |
|---|---|---|---|
| Auto pin | #56B4E9 sky blue | circle, dark outline | 🧠 |
| User pin | #E69F00 orange | square, dark outline | 🧠 |
| Conflict >3σ | #D55E00 vermillion | ✕ plus residual line | 🧠 |
| Selected | #F0E442 yellow | 2 px ring | 🧠 |
| Model contours | #009E73 bluish green | 1.5–2 px polyline | 🧠 |
| Guessed region | #CC79A7 reddish purple | hatching | 🧠 |
| Residual size | cividis bins <1, 1–2, 2–3, >3σ | true length (×3 optional, labelled) | 🧠 |
| Pin / hit size | 9 px / 12 px radius (≥24 px target) | – | 🧠 |

**Table 5 — Testing** 

| Item | Value | Badge |
|---|---|---|
| Formative think-aloud | ~5 users/round, ≥3 rounds | ↔️ ("5 users find 85 %" varies widely) |
| Summative metrics | ≥15–20 users | 🧠 |
| SUS | mean ≈68; ≥80 ≈ top 10–15 % | 🧠 |
| Pin accuracy | synthetic renders with known landmarks; RMS mm per class | 🧠 |
| Likeness | ≥5 people who know the subject, blind A/B | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **One tab, eight stages:** Consent → Photos → Check → Cameras → Landmarks → Fit → Confidence → Hand-off.
   - Each stage has a "done when" line.
   - "Next" is gated by `poll()`, with `poll_message_set` saying why ("2 photos still have blocking issues").
   - Experts can expand everything. 🧠
2. **Normalise, then check.**
   - Bake EXIF orientation into the pixels, convert HEIC, keep the originals.
   - Show one card per photo: thumbnail, icon, problem, fix, "use anyway".
   - A pose ring fills Table 3's bins and names the missing view ("add a photo from your left side"). 🧠
3. **Cameras.**
   - Show photos as camera background images, lock the solved transforms and turn off Lock Camera to View.
   - Report error in mm ("this photo disagrees by about 1.5 mm"), never as pixel RMSE.

   🧠 See [reference cameras](./reference-camera-setup.md).
4. **Review landmarks as a queue, like a spell checker.**
   - Sort by normalised residual; Tab and Shift+Tab move to the next or previous problem.
   - Each pin shows a plain name plus code, an illustration, and its epipolar line.
   - Place the first pins in each view *blind*, with the overlay hidden. 🧠
5. **Make the pin tool a `WorkSpaceTool`.**
   - Click places a pin; drag moves it, with an offset loupe.
   - Shift-drag moves at ¼ speed; arrows nudge 1 px, Shift+arrows 0.25 px.
   - X deletes; H and Alt+H hide and reveal.
   - The status bar shows hints. 🧠
6. **Re-solve live** with 2–5 warm-started LM iterations per mouse event at ≥20 fps. If an iteration exceeds ~50 ms, solve on release instead. Highlight regions that move. 🧠
7. **Rigidity in words:** "Stay close to an average head" ↔ "Follow my pins exactly", mapped internally to λ_shape = 10^(2r−1). 🧠
8. **Confidence stage:**
   - Hatch three levels (measured / partly / guessed), with ±mm on hover.
   - A "wobble" button plays 8–12 posterior samples.
   - List guessed regions with the next best photo to take. 🧠
9. **Hand-off:**
   - Write a `likeness` shape key.
   - Add `f3d_support` (0–1) and `f3d_sigma_mm` point attributes.
   - An operator copies (1 − support) into the sculpt mask, so measured regions stay protected while the artist sculpts the guessed ones.

   🧠 (that 4.x stores the mask as attribute `.sculpt_mask` is ↔️)

**What goes wrong:**
- **Over-pinning.** Warn above ~3–5 user pins per feature per view, or when one view holds more than 60 % of them.
- **Hair pinned as skull.**
- **Highlights pinned as form.**
- **Orbiting in camera view**, which breaks the camera match.
- **Pins kept in Python globals**, which desync on Ctrl+Z.
- **A blocking solve** that looks like a crash.
- **Status shown only in red and green.** 🧠

## Algorithmic implications

- **Pin record:** `Pin{view, xy_px, target: surface(tri,bary)|curve_id, cls, sigma_n_mm, sigma_t_mm, source, expertise, zoom_at_place, blind}` in a PropertyGroup, so it is undo-safe. A user pin replaces auto pins on the same feature within ~3 % IOD. 🧠
- **Engine mapping:** `face3d/solve/bundle.py` has one scalar `ViewObs.sigma_px` plus per-landmark `weights`.
  - Now: encode w_i = (sigma_px/σ_i,px)², with σ_i,px = √(σ_class²+σ_motor²)·px_per_mm from Table 2 and a Huber threshold of 2σ.
  - Later: accept `(N,)` or `(N,2,2)` covariances, for point-to-curve contours and anisotropic nasion. 🧠
- **Self-calibration:**
  - Default to the novice column.
  - An optional 2-minute onboarding places 6 crisp landmarks twice. σ_rep = RMS(Δ)/√2, and σ_crisp = max(σ_rep + 0.3 mm convention allowance, 0.5 mm).
  - Inflate a class's σ when the MAD scale of its whitened user residuals stays above 1.5. 🧠
- **Library default:** the current user σ of 0.75 % IOD (≈0.66 mm) fits experts on crisp corners only. For novices or soft points it over-weights the user about 3–30× in information. ↔️
- **Conflicts:** a normalised residual or epipolar distance above 3σ flags the pin, explained in mm. 🧠
- **Mirror test:** fit each view with and without an x-flip. If flipping lowers its RMSE by more than 30 % while the other views are unchanged, flag it. Never auto-flip. 🧠
- **Distance:** Z = f_px·88 mm/IOD_px (±6 % from population spread); warn below 1.2 m. 🧠
- **Expression gating:** views over Table 1 limits get identity weight ×0.25 or are dropped. Per-view expression coefficients get a strong zero-mean prior. 🧠
- **Support map:**
  - Use Σ_v = B Σ_θ Bᵀ for linear bases, or interpolate `point_sigma_mm` with the warp weights.
  - s = 1 − σ_post²/σ_prior², binned at 0.3 and 0.7. 🧠
- **Next-best photo:** for each Table 3 pose, score the expected drop in trace(Σ) over visible guessed vertices, and suggest the best one. 🧠
- **Check API:** pure NumPy, returning `{code, severity, value, threshold, msg_key, fix_key}`.
  - Messages are translatable via `bpy.app.translations`.
  - Thresholds are relative to the set median where content-dependent.
  - No network use, and no logs unless the user opts in. 🧠
- **Scheduling:** a modal timer with a 30–50 ms budget per tick. Esc keeps the last good state, and each committed solve is one undo step. 🧠

## Disagreements, myths & open questions

- **"More pins = better likeness"** is a myth. Past a few per feature, extra pins add noise and conflicts between views. 🧠
- **"Detectors beat humans"** ↔️: comparable on crisp benchmark points. But detectors pull toward the mean face, while a zoomed-in human catches identity-specific shape.
- **The "5 users" rule** ↔️: fine for iterative rounds, wrong for estimating rates.
- **Uncertainty displays for novices** ↔️: hypothetical outcome plots help, but overlays add load. Show hatching by default only at the Confidence stage.
- **Live re-solve while dragging** ↔️: fast for experts, but it may confuse novices when distant regions move. A/B test it against solve-on-release.
- **The library mixes IOD definitions** ↔️: outer (≈88 mm) and interpupillary (≈63 mm) differ 1.4× in every %-IOD σ. Store σ in mm.
- **Open questions:** there is no published study of novice pin accuracy in photo-to-head tools, so run one on synthetic renders before freezing Table 2. It is also unknown how well blendshape thresholds transfer across age, ethnicity and facial hair.
- **Time-sensitive:** vendor features, MetaHuman licence terms, and RealityScan and Scaniverse naming and ownership.

## Sources

No web harvest or earlier draft existed for this topic, so no URLs are cited. Related library notes: [FaceBuilder](./facebuilder-blender.md), [face add-ons](./blender-face-addons.md), [reference cameras](./reference-camera-setup.md), [extension packaging](./blender-extensions-packaging.md), [landmark detection](../reconstruction/landmark-detection.md), [commercial head tools](../reconstruction/commercial-head-tools.md), [craniometric landmarks](../anatomy/craniometric-landmarks.md), [photo protocol](../community/reference-photography-protocol.md), [biometric privacy](../ethics/biometric-privacy.md).

**Further reading (by name, not yet linked)**
- Reynish — The Evolution of Blender's User Interface (2008); Blender Developer Docs — Human Interface Guidelines; Blender Python API (Operator, UILayout, gpu, WorkSpace)
- ISO/IEC 29794-5 (face image quality) and BSI OFIQ; ISO/IEC 19794-5 and ICAO Doc 9303 portrait requirements
- Okabe & Ito — Color Universal Design (2008); Nuñez et al. — cividis, PLoS ONE (2018); W3C — WCAG 2.2 (2023)
- Vogel & Baudisch — Shift, CHI 2007; Hullman, Resnick & Adar — Hypothetical Outcome Plots, PLoS ONE (2015); Newman & Scholl — bar graphs of averages misinterpreted, Psychon Bull Rev (2012)
- Burgos-Artizzu, Perona & Dollár — Robust face landmark estimation under occlusion (COFW), ICCV 2013; Liu et al. — Semantic alignment, CVPR 2019
- Toma et al. (2009) Orthod Craniofac Res; Plooij et al. (2009) Int J Oral Maxillofac Surg; Aynechi et al. (2011) Angle Orthod; Fagertun et al. — 3D facial landmarks: inter-operator variability, BMC Med Imaging (2014)
- Carroll — The Nurnberg Funnel (1990); Grossman, Fitzmaurice & Attar — software learnability survey, CHI 2009; Grossman & Fitzmaurice — ToolClips, CHI 2010; Kelleher & Pausch — Stencils-based tutorials, CHI 2005
- Green & Petre — Cognitive Dimensions (1996); Brooke — SUS (1996); Hart & Staveland — NASA-TLX (1988); Cherry & Latulipe — Creativity Support Index, TOCHI (2014); Nielsen & Landauer (1993); Faulkner — Beyond the five-user assumption (2003); Tversky & Kahneman (1974)
