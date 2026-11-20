# KeenTools FaceBuilder for Blender in practice

> FaceBuilder is a pin-driven template fitter. Each photo becomes a view with its own camera, and dragging points of a fixed KeenTools head onto the photo makes a closed-source core re-solve head shape, per-view pose, optional per-view expression and, if allowed, focal length. Since 2021.1 neural auto-alignment drafts the pins, which the vendor says can need manual correction [1]; since the ~2020 revamp focal length and sensor size are set per photo [2]. In practice it is the fastest route in Blender to matched cameras plus a plausible, textured, ARKit-ready base head, but likeness stops at its shape space: lids, alae, vermilion, ears and the hair-covered cranium must be sculpted, and pinhole-only cameras, cropped photos and mirrored selfies quietly corrupt the fit. No vendor or independent millimetre benchmark exists, and version, Blender support, price and trial terms are perishable (verified 2026-11-20 only against vendor pages: 2026.1.0 supports Blender 5.1; 15-day trial; Freelancer Annual 191.88 USD/yr) [5][7]; for this project FaceBuilder sets the UX bar (surface pins, live re-solve, rigidity sliders, per-view cameras) and supplies an external observation, not ground truth.
> Evidence status: 1 ✅ / 15 📄 / 47 🧠 / 23 ↔️ — verification pass 2026-11-20 (see log); remaining 🧠 items are unconfirmed.

## Key facts

**Sourced (BlenderArtists release threads; see Sources for provenance)**
- KeenTools announced each Blender milestone in its own BlenderArtists thread: the 2.8 beta, the first stable release, the "Revamped" FaceBuilder and 2021.1 [1][2][3][4] ✅ (the threads exist; dates are inferred from topic IDs).
- 2021.1 added auto-alignment: "a couple of neural networks" find the face and set up the pins; the developers say results are not always 100% accurate and manual adjustment is sometimes needed [1] 📄.
- The revamp sets focal length and sensor size automatically for each photo, using EXIF when present [2][9] 📄. Pixels constrain only the ratio focal/sensor, so the two are not separately observable 🧠.
- Expressions are supported, so neutral photos are not strictly required, but neutral photos give better quality [1][2] 📄 (both vendor statements, so not independent).
- Users call it paid, and one mentioned a 30-day trial [1][4]; the vendor now states a 15-day per-add-on trial [7] 📄 (corrected in verification; time-sensitive).
- Topic IDs put the revamp (1245723) before 2021.1 (1294243), contradicting the harvester's phrase "later revamp" ↔️.

**How it works (expert knowledge)**
- **Packaging:** one "KeenTools" add-on (FaceBuilder, GeoTracker, later FaceTracker) whose GPL Python front end installs a separate proprietary core library, downloaded or from a file; licence activation is online, offline or floating 🧠. Fitting and auto-alignment run locally; I know of no photo upload 🧠.
- **Model:** one fixed head topology (cranium cap, face, ears, neck, eye sockets) with toggleable parts and density options inside a low-dimensional learned shape space; you cannot load your own topology ↔️ (part and density names vary by version).
- **Views:** each image becomes a view with a Blender camera; the head stays put and the cameras move 🧠. Opening a view enters pin mode, looking through that camera at the photo.
- **Pins:** drag any surface point, not only predefined landmarks, onto the photo; the solver re-runs live while dragging; right-click deletes 🧠. Shape is shared, so a pin in one view moves every other view's fit 🧠.
- **Rigidity:** shape and expression rigidity sliders (later also blinking and neck-movement rigidity) set how far pins may pull away from the prior ↔️ (names and defaults vary).
- **Focal length:** per-view focal from EXIF, typed manually, or estimated from pins, per view or shared across views ↔️ (UI differs by release). Estimation is ill-conditioned for frontal, long-lens, distant shots (Table D) 🧠.
- **Expressions:** when on, each view gets its own expression coefficients over one shared identity; when off, every view is fitted as neutral 🧠.
- **Camera model:** pinhole with the principal point at the image centre; I know of no radial-distortion term in FaceBuilder ↔️.
- **Texture:** projects selected views into the head's UVs with angle-weighted blending (an "angle strictness"-type control), optional brightness and colour equalisation and gap filling; several UV layouts (recalled: Butterfly, Legacy, Spherical, Maxface) ↔️. Lighting, specular and shadows are baked in 🧠.
- **Blendshapes:** 51 built-in ARKit-compatible FACS blendshapes and Live Link Face CSV import, both introduced in 2021.1 [8] 📄; whether `tongueOut` is among the 51 is unconfirmed.
- **Siblings:** GeoTracker (object and camera tracking) and FaceTracker (facial performance on a FaceBuilder head) ship in the same add-on; FaceTracker for Blender arrived around 2024 ↔️.
- **Mesh ownership:** the head mesh is regenerated from the model, so Edit-mode or sculpt edits on the FaceBuilder object are overwritten or break it. Sculpt on a duplicate 🧠.

**Accuracy and reception**
- No published mm benchmark; vendor evidence is demos ↔️. The library's estimate for a 5–9-view pin fit with profiles is 0.8–2 mm on the face and 1–3 mm on the profile and nasal tip (`reconstruction/commercial-head-tools.md`) ↔️.
- Forum, Reddit and YouTube reception (synthesis) praises speed, camera matching and textures. It criticises the subscription, the closed core, the fixed topology, pin effort on profiles and ears, "generic" lids, noses and lips, and dependence on neutral, evenly lit photos with the hair off the face 🧠.

## Numbers & reference tables

**Table A — Release timeline** (verify every row after 2021)

| Milestone | Approx. date | Change | Badge | Src |
|---|---|---|---|---|
| KeenTools for Blender 2.8 (beta) | ~2019 | Nuke tool ported to Blender | 📄 | [4] |
| First stable FaceBuilder | ~2020 | stable release | 📄 | [3] |
| Revamped FaceBuilder | ~2020 | per-photo focal and sensor; expressions | 📄 | [2] |
| 2021.1 | 2021 | neural auto-alignment | 📄 | [1] |
| 2021.1 (22 Dec 2020) | Dec 2020 | 51 ARKit-compatible blendshapes, Live Link Face CSV (corrected in verification: 2021.1, not 2021–2022) | 📄 | [8] |
| 2022–2023 | — | GeoTracker for Blender | ↔️ | — |
| ~2024 | — | FaceTracker for Blender | ↔️ | — |
| 2025.3 (4 Dec 2025); 2026.1.0 (9 Apr 2026) | 2025–2026 | 2025.3 first added Blender 5.0; 2026.1.0 adds Blender 5.1 (latest found); installable from the Blender extensions menu; Blender 5.2 LTS / 5.3 support not confirmed | 📄 | [5][6][7] |

**Table B — View set that FaceBuilder fits well** (adults; yaw 0° = frontal)

| View | Yaw / pitch | Pin first | Focal estimation? | Badge |
|---|---|---|---|---|
| Front | 0° / 0° | canthi, mouth corners, pronasale, subnasale, menton | no: fix from EXIF | 🧠 |
| ¾ left and right | ±30–45° / 0° | the same, plus far cheek contour and ear attachment | best-conditioned view | 🧠 |
| Profiles | ±90° / 0° | silhouette: glabella, nasion, pronasale, subnasale, lips, pogonion; tragus | rarely | 🧠 |
| Low and high | 0–30° / ±15–20° | chin underside, brow ridge, nostrils | optional | 🧠 |
| Total | 5–9 views (1 works; depth then comes from the prior) | 4–8 confident pins per view | — | 🧠 |

**Table C — Pin reliability and engine σ** (IOD = inter-ocular distance in the image; matches `blender/blender-face-addons.md`)

| Feature class | Auto-pin quality | Engine σ | Badge |
|---|---|---|---|
| Canthi, mouth corners, subnasale | good in front and ¾ | user 0.75% IOD; auto 1.5% | 🧠 |
| Lid and lip contours | fair; slide along the contour | auto 2.5%, point-to-curve | 🧠 |
| Jaw and cheek outline | slides with yaw | 4%, silhouette residual | 🧠 |
| Profile silhouette | poor auto, so pin by hand | user 1%, silhouette | 🧠 |
| Ears | poor; often hidden by hair | 3–5%, drop when occluded | 🧠 |
| Hair outline (cranium) | wrong by 5–20+ mm | never pin; prior only | 🧠 |

**Table D — How well one view constrains focal length** (derived, order of magnitude). Assumptions: nose-tip-to-ear depth d = 0.10 m, face 800 px wide, pin noise 2 px, ~4 independent pins. The "ideal" column is the pin-noise floor; "realistic" adds about 4% for unknown facial depth when no profile view constrains it. The last column is the nose-width error a 20% focal error causes, ≈ 0.2·(d/Z)·35 mm.

| Camera → nose (m) | d/Z | σ(log f) ideal | σ(log f) realistic | Shape error from 20% focal error | Badge |
|---|---|---|---|---|---|
| 0.5 (selfie) | 0.20 | ~1% | ~4% | ~1.4 mm | 🧠 |
| 1.0 | 0.10 | ~2.5% | ~5% | ~0.7 mm | 🧠 |
| 2.0 | 0.05 | ~5% | ~6–7% | ~0.35 mm | 🧠 |
| 3.0 | 0.033 | ~7.5% | ~8–9% | ~0.23 mm | 🧠 |
| 5.0 | 0.02 | ~12% | ~13% | ~0.14 mm | 🧠 |

The rule that falls out: focal error is self-limiting. It matters at selfie range, where estimation works; it is unobservable at ≥2 m, where it barely matters 🧠.

**Table E — Commercial and output contract** (perishable)

| Item | Value | Badge |
|---|---|---|
| Pricing | Freelancer Monthly 19.99 USD/mo; Freelancer Annual 191.88 USD/yr; Studio Annual 699 USD/yr; bundles 29.99–39.99 USD/mo; per-platform licence (corrected in verification; vendor page may be dated) [7] | 📄 |
| Trial | 15 days per add-on, starting at first Blender launch [7] (corrected in verification; one forum user said 30 days [1][4]) | 📄 |
| Licence | GPL front end plus closed core; outputs belong to the user under the EULA | ↔️ |
| Platforms | Windows, macOS (Apple Silicon support recalled), Linux; CPU only | ↔️ |
| Blendshapes | 51 ARKit-compatible FACS shapes [8]; tongue absence unconfirmed | 📄 |
| Texture | user-set size, 2048² typical, up to 8K | ↔️ |
| Expected accuracy | 0.8–2 mm face, 1–3 mm profile (estimate, multi-view) | ↔️ |

## Applying this to photo→3D face sculpting in Blender

1. **Prepare files** 🧠
   - Keep the originals so EXIF survives. Blender does not read HEIC, so convert iPhone photos to JPEG or PNG with EXIF kept.
   - Do not crop, or crop symmetrically: an off-centre crop moves the principal point that FaceBuilder assumes is centred.
   - Un-mirror front-camera selfies, and apply EXIF rotation, or use the add-on's rotate control.
   - Avoid digital-zoom and portrait-mode shots: synthetic bokeh erodes the ears and hair edges, and some phones report the native lens focal on a cropped image. Trust `FocalLengthIn35mmFormat` over `FocalLength`.
2. **Lens distortion** 🧠
   - Phone main cameras already correct distortion in their JPEGs. Undistort ultra-wides, action cameras and wide zooms first, using lens profiles in a raw converter.
   - Disable "constrain crop" there: it rescales the frame, and the EXIF focal is then wrong. Otherwise let FaceBuilder estimate focal.
   - Keep the face near the centre of the frame.
3. **Cameras** 🧠
   - Same body and zoom → one focal. Fix focal from EXIF for views shot at ≥1.5 m.
   - Estimate only for unknown sources (web images, video frames), preferably on ¾ views, then copy the value to that camera's other views.
   - Distrust solved focals that differ by >10% within one lens, or from EXIF by >10–15%: suspect a bad pin, a crop or a resize.
4. **Pin** 🧠
   - Front first: Align face, then inspect every pin at 100% zoom.
   - Then the ¾ views, then pin the profiles by hand along the skin silhouette.
   - Return to the front view after each new view, because the shape is shared.
   - Use few, confident pins. When two pins fight and raise lumps, delete one rather than adding more.
   - Pin the eye corners, never the iris, which moves with gaze.
5. **Settings** 🧠
   - Turn Expressions off when every photo is neutral. When it is on, a squint or faint smile can be explained either as identity or as expression; set neutral views to zero expression if the release allows it.
   - Raise shape rigidity when the mesh dents between pins.
   - Lock or stiffen neck movement unless the neck is pinned in several views.
6. **Hair and occlusion** 🧠
   - Never pin the hair outline. The cranium, back of skull and ear tops then come from the prior.
   - Gate the result against head length g–op ≈ 182–200 mm (`anatomy/anthropometric-norms.md`), or shoot one photo with the hair wet and slicked back or under a thin cap.
   - Beards hide the jaw (pin the chin only), and glasses hide the canthi, so remove them.
7. **Validate** 🧠
   - Wireframe off, toggle the photo through each camera, then compare silhouettes, especially the profile.
   - Check scale: model IPD against the measured PD, with 55–72 mm plausible.
   - Look for mirrored asymmetries (moles, hair parting).
8. **Texture** 🧠
   - Build from the front and both ¾ views at 4K. Profiles smear the cheeks and ears, and photos with mixed white balance cause seams.
   - Equalise brightness and colour, then de-light or treat the result as reference only.
9. **Hand-off to sculpt** 🧠
   - Duplicate the head and apply its transforms. Add Multires and sculpt on the copy.
   - Keep the original hidden as a "fit snapshot".
   - Look through the FaceBuilder cameras with the photos as background to check likeness after every pass.
   - Create the 51 shapes only on the final topology, or regenerate them; shapes made before sculpting go stale.
10. **What goes wrong** 🧠: lumpy cheeks from over-pinning; unchecked ¾ and profile auto-pins [1]; mixed expressions with Expressions off; hair pinned as skull; selfie perspective solved with a wrong focal (wide nose, narrow face; Table D); web images with stripped EXIF; edits on the live FaceBuilder mesh; wrong scale after export.

## Algorithmic implications

- **Pins as first-class, surface-anchored constraints** 🧠: `Pin{view, xy_px, tri, bary, sigma, source∈{user,auto}}`. Re-solve on drag with a warm-started Levenberg–Marquardt, 2–5 iterations per mouse event, using only Jacobian rows for pinned points. A user pin replaces auto pins within ~3% IOD; Huber δ = 2σ.
- **Rigidity sliders → log-scale priors** 🧠: shape coefficients ~N(0,1) with λ_shape = 10^(2r−1), r ∈ [0,1], default 0.5. Expression off by default; when on, per-view expression ~N(0, 0.6²), and neutral-flagged views fixed at 0. Neck yaw, pitch and roll σ ≈ 10–15°; blink as its own coefficient with σ ≈ 0.2 unless the eyes are closed.
- **Focal handling with an observability gate** 🧠:
  - log-σ 0.03 for uncropped EXIF with a 35 mm-equivalent value;
  - 0.08 when a crop, zoom or resize is suspected;
  - 0.35–0.5 with no EXIF, starting from 50 mm-eq;
  - a camera-group tie of 0.02.
  - Estimate focal only when the posterior σ(log f) from JᵀJ is below 0.10; otherwise hold the prior and show "focal not observable from this view". Never solve sensor size [2].
- **Camera model** 🧠: principal point fixed at the centre unless crop metadata exist. Distortion k1 = 0 by default; enable k1 with σ 0.05 only when f35 < 28 mm or for action cameras, and prefer undistorting first.
- **Hair-aware contours** 🧠: segment hair; disable silhouette terms above the trichion and on ears when they are occluded. Regularise cranium vertices to the prior with σ 5–8 mm and log-normal priors on g–op and eu–eu. Write per-vertex "from prior" confidence to a colour attribute.
- **Interop** 🧠:
  - Import any Blender camera with a background image as a view, including FaceBuilder's cameras (naming unverified), so users can bring existing solves.
  - Treat a FaceBuilder head as a point-to-plane observation with σ 1–1.5 mm, or 3–4 mm on the cranium and ears, down-weighted once photo pins exist.
  - Never ship KeenTools topology or correspondences.
- **QA thresholds** 🧠: per-pin residual ≤1% IOD; per-view RMS ≤0.5% IOD; within-group focal spread ≤5%; IPD 55–72 mm. Warn when the camera-to-nose distance is <0.8 m.
- **Texture** 🧠: per-texel weight cos(θ)^k, with k = 2–4 mapped from an "angle strictness" slider. Reject θ > 70–75°, feather seams over 8–16 texels, and keep a per-texel view-index map.

## Disagreements, myths & open questions

- **Myth: the FaceBuilder head is the likeness.** It is a pinned, low-dimensional fit; fine forms are sculpted ↔️.
- **Myth: more pins, better fit.** Conflicting pins over-fit noise; vendor tutorials and users favour few, confident pins 🧠.
- **Myth: auto-alignment is one click.** The vendor says it is not always accurate [1] 📄.
- **Myth: Expressions mode is free.** It adds degrees of freedom that can absorb identity; neutral photos fit better [1][2] ↔️.
- **Focal priors disagree inside this library:** EXIF log-σ 0.03 and no-EXIF 0.5 (`reconstruction/commercial-head-tools.md`) against 0.05–0.10 and 0.35 (`community/blenderartists-forum.md`). The tiered values above reconcile them ↔️.
- **Lens distortion:** I believe FaceBuilder has no distortion model, and newer releases or GeoTracker may differ ↔️.
- **Licence legitimacy:** a GPL front end that loads a closed core is contested under the Blender Foundation and FSF reading (`blender/blender-extensions-packaging.md`) ↔️. Whether the add-on is on extensions.blender.org is unknown to me ↔️.
- **Thread order:** topic IDs say the revamp came before 2021.1 ↔️.
- **Open questions:** Blender 5.2 LTS / 5.3 support (latest confirmed: 5.1 in 2026.1.0); EULA terms and GPL/closed-core split; blendshape count; EULA terms for commercial reuse of exported heads; whether neutral views can be expression-locked individually; any mm-level benchmark against scans ↔️.

## Sources

No topic harvest or earlier draft existed. The four URLs below are reused from the library's BlenderArtists harvest (`_raw/harvests/blenderartists-forum.json`), where web search captured them; only search-result summaries were seen, and the same list is cited in `community/blenderartists-forum.md`.

1. FaceBuilder for Blender 2021.1 is out: now with AI — https://blenderartists.org/t/facebuilder-for-blender-2021-1-is-out-now-with-ai/1294243 — forum (vendor announcement) — 2021
2. Revamped FaceBuilder for Blender — https://blenderartists.org/t/revamped-facebuilder-for-blender/1245723 — forum (vendor announcement) — n.d. (~2020 by topic ID)
3. The first-stable FaceBuilder release for Blender — https://blenderartists.org/t/the-first-stable-facebuilder-release-for-blender/1210803 — forum — n.d. (~2020)
4. KeenTools For Blender 2.8 — https://blenderartists.org/t/keentools-for-blender-2-8/1173005 — forum (Blender Development Discussion) — n.d. (~2019)

5. KeenTools 2026.1.0 (9 April, 2026) release notes — https://keentools.io/news/2026-1 — vendor — 2026
6. KeenTools 2025.3.0 (4 December, 2025) release notes — https://keentools.io/news/2025-3 — vendor — 2025
7. FaceBuilder for Blender product page (pricing, trial, extensions-menu install) — https://keentools.io/products/facebuilder-for-blender — vendor — undated, possibly stale
8. KeenTools version 2021.1 (22 Dec 2020) release notes — https://keentools.io/news/2021-1 — vendor — 2020
9. Revamped FaceBuilder and other improvements in KeenTools 2.1.0 — https://link.keentools.io/210-post — vendor — n.d.

Related notes: `reconstruction/commercial-head-tools.md`, `community/blenderartists-forum.md`, `blender/blender-face-addons.md`, `blender/reference-camera-setup.md`, `community/reference-photography-protocol.md`, `anatomy/anthropometric-norms.md`, `blender/blender-version-status-2026.md`.

**Further reading (by name, not yet linked)**
- KeenTools FaceBuilder for Blender user documentation, and KeenTools' public GitHub repository for the Blender add-on's GPL code
- Apple ARKit documentation, `ARFaceAnchor.BlendShapeLocation`; Epic Games Live Link Face app documentation (CSV export)
- Hartley & Zisserman, *Multiple View Geometry in Computer Vision* (2nd ed., 2004)
- Zhang, "A Flexible New Technique for Camera Calibration", IEEE TPAMI (2000)
- Brown, "Decentering Distortion of Lenses", *Photogrammetric Engineering* (1966)
- Blanz & Vetter, "A Morphable Model for the Synthesis of 3D Faces", SIGGRAPH 1999
- Ward et al., "Nasal distortion in short-distance photographs: the selfie effect", *JAMA Facial Plastic Surgery* (2018)
- Farkas, *Anthropometry of the Head and Face* (2nd ed., 1994)

## Verification log (2026-11-20)

- **Current version / Blender support / extension packaging** — corrected/partly confirmed. Latest found: 2026.1.0 (9 Apr 2026) supports Blender 5.1; 2025.3 first added 5.0; Blender 5.2 LTS / 5.3 support not found (unconfirmed); installable via the Blender extensions menu per the product page. https://keentools.io/news/2026-1 , https://keentools.io/news/2025-3 , https://keentools.io/products/facebuilder-for-blender
- **Pricing / trial / licence** — corrected. Trial is 15 days per add-on (not 30); Freelancer Annual 191.88 USD/yr, Monthly 19.99, Studio Annual 699 (a bundle exists); subscription confirmed; EULA exists but its terms and the GPL-front-end-plus-closed-core claim were not found (unconfirmed). Product page may be stale. https://keentools.io/products/facebuilder-for-blender
- **Pinhole camera, centred principal point, no distortion model; focal from EXIF/manual/estimate** — partly confirmed: v2.1.0 sets focal and sensor per photo from EXIF [https://link.keentools.io/210-post]; typed or estimated focal confirmed for FaceTracker only. Pinhole/no-distortion unconfirmed (stays 🧠/↔️).
- **51 ARKit blendshapes, Live Link Face CSV** — confirmed (one vendor source): both in 2021.1 (22 Dec 2020). tongueOut absence unconfirmed. https://keentools.io/news/2021-1
