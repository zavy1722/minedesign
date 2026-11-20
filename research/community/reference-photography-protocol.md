# How to shoot reference photos for 3D faces

> Distance, not focal length, sets facial perspective. The 85–135 mm (full-frame-equivalent) advice exists because those lenses let you stand 1.5–2.5 m away and still fill the frame, where the nose tip is only 4–7% over-magnified against the ears. A fitting and sculpting **identity set** is 7–9 core stills (front, ±45°, ±90°, below, above), extendable to 15–20. Shoot it in one ≤15-minute session with one locked lens, a neutral face, fixed gaze, hair off the ears and hairline, even diffuse light and a scale reference. Photogrammetry is a separate pass (40–150 photos in rings); video supplements stills. No harvest or draft existed for this topic, so every item is expert knowledge or camera arithmetic, cross-referenced to sibling notes.
>
> Evidence status: 0 ✅ / 1 📄 / 78 🧠 / 18 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Optics, distance, camera height**
- Perspective depends only on distance; at the same framing, a longer lens just lets you stand farther back. The nose tip's magnification over the ear plane is ≈ 100 mm / distance: 20% at 0.5 m, 6.7% at 1.5 m, 4% at 2.5 m (Table 2; `blender/reference-camera-setup.md`) 🧠
- At 1.5–2.5 m, an 85–135 mm lens frames a 0.4–1.0 m field and puts a face 1000–1700 px wide on 24 MP full frame. Crop later rather than walk closer 🧠
- Clinical facial-photography standards use a 90–105 mm macro-class lens on full frame at a fixed, recorded distance, with the Frankfurt horizontal level. Recommendations span 85–135 mm (Ettorre et al. 2006; Yavuzer et al. 2001; Galdino et al. 2001) ↔️
- Biometric portrait standards (ICAO; ISO/IEC 19794-5, 39794-5) require near-frontal pose (±5° in yaw and pitch; roll relaxed to ±8° in the ISO/IEC 19794-5 corrigendum) and even light 📄 [1]. ICAO is recalled as suggesting ~1.2–2.5 m, but that distance was not found in verification 🧠 (verify). They target 2D recognition: a floor, not a target
- At fixed framing, depth of field barely depends on focal length. Focus on the near eye at f/8 full frame (≈f/5.6 APS-C, f/4 Micro Four Thirds) to keep nose tip to ears sharp. At f/1.8–2.8 the ears and far cheek blur (Table 3) 🧠
- **Camera height:** lens at the sitter's eye–nose level, axis level. A 30 cm mismatch at 1.5 m gives 11° of pitch, which shifts the nose tip ~20 mm vertically against the ears (Table 4). This is the usual cause of "ears too high/low" 🧠
- **Head orientation:** natural head position (eyes on a mark at eye height ≥2 m away) or Frankfurt horizontal (tragus top level with the lower orbital rim); they differ by a few degrees, SD ~3–5° (`anatomy/craniometric-landmarks.md`) ↔️

**Shot list** (Table 1)
- **Core set (7–9 views):** front, ±45°, ±90°, plus ~25–30° below (jaw underside, nostrils) and ~25–30° above (brow ridge, lids, crown) 🧠
- **Extended set (15–20 views):** add ±20–30° half-turns, ±135° and the back, a top view, ear close-ups, and a hair-down front and 3/4. Hair is a major recognition cue (Sinha & Poggio 1996) 🧠
- **Raise or lower the camera; don't tilt the head,** which stretches or bunches submental and neck tissue 🧠
- **In-camera checks:** in the front view both ears are equally visible and the pupils level; in a true profile the far eye and brow are just hidden. A 2° yaw fakes 2–3 mm of asymmetry 🧠
- **Clinical "oblique" has two definitions:** 45° yaw, or the nose tip on the far cheek contour. Log which one you used ↔️

**The sitter**
- **Neutral expression:** lips lightly together, jaw and brow relaxed, eyes naturally open. Teeth either lightly touching (repeatable) or just apart (rest, ~2–4 mm gap), the same in every shot; bursts of 3 per view beat blinks ↔️
- **Gaze:** fixed on a mark straight ahead while the camera moves; following the camera changes lids, brow and inter-pupil distance. Some put the eyes on the lens for the front only ↔️
- **Hair off the ears, hairline and temples:** band, clips, gel, or a swim or wig cap. A cap adds ~1–3 mm, so log it 🧠
- **Remove and prepare:** glasses off 10–15 min early (pad dents fade), jewellery out, matte powder only, a neutral dark top with a low neckline 🧠
- **Beards hide the mandible:** shave if the person agrees, otherwise treat the jawline as unknown 🧠
- **Optional, with consent:** washable dots on palpated landmarks hidden under skin (gonion, zygion, orbitale), as in clinical anthropometry. They give the fitter true bony points 🧠
- **Measurements:** head breadth and length (spreading calipers); bizygomatic, bigonial, n–gn, al–al, ch–ch (sliding calipers); IPD; head circumference. Soft tissue limits σ to ≈ 1–2 mm (Farkas 1994) 🧠
- **Scale in frame:** an ID-1 card (85.60 × 53.98 mm, ISO/IEC 7810) or a ruler held at cheek depth in ≥2 views. Alternatively, a rigid headband with ArUco/AprilTag fiducials, which also tracks head pose 🧠

**Light & colour**
- **Even, diffuse light for fitting and texture:** overcast or open shade outdoors. Indoors, two large softboxes at ±45° slightly above eye level plus a reflector below, key-to-fill ≤1.5:1. Avoid overhead light, direct sun and mixed colour temperatures 🧠
- **Cross-polarisation** (film on the lights, lens polariser at 90°, until the corneal catchlight vanishes) removes specular reflections for albedo and photogrammetry. It costs roughly 1.3–3+ stops (sources vary: a single polarizer alone is 1–3 stops; cross-polarised setups need "several" stops) [2][3], and works best with lights near the lens axis, such as a ring flash (`blender/skin-shading.md`) ↔️
- Landmark fitting does not need cross-polarisation, which flattens apparent form; also shoot unpolarised 🧠
- **"Form" set:** one key light at 45° and then at 90°, 4:1–8:1. It shows the planes, cheekbones and brow ridge that flat light hides ↔️
- **Colour and exposure:** a grey card or colour chart for each lighting set; manual white balance and exposure; RAW; no clipped forehead or nose 🧠

**Camera & smartphone**
- **Lock settings:** exposure; focus at a tape-measured distance (focus breathing changes f); zoom. Use ISO 100–400, and a shutter of ≥1/125 s on a tripod or ≥1/250 s handheld 🧠
- **Phones:** never the front camera (~23–30 mm, arm's length, possibly mirrored or retouched) or the ultra-wide; use 2–5× from 1.5–3 m (Table 5). Disable portrait, beauty, mirror-front, night and auto-framing modes 🧠
- **Lock one physical lens with a manual app.** Phones silently substitute a cropped main camera in low light or inside the telephoto's minimum focus distance, so check EXIF `LensModel` on every image. On many phones "2×" is a crop of the main sensor ↔️
- **Files:** keep distortion correction on and EXIF intact, and convert HEIC to PNG. ProRAW and DNG are still processed 🧠

**Video**
- **A supplement, not a replacement:** 4K is only ≈8 MP, compression smears pores, rolling shutter skews motion, and stabilisation and video crops change the intrinsics relative to stills 🧠
- **Recipe:** 4K at top bitrate, ≥1/250 s, standard or no stabilisation, everything locked; ≥25–35 s per orbit (or a slowly rotated stool against a plain background); extract 2–5 fps and keep sharp, open-eye frames; expressions as a separate clip 🧠

**How many photos**
- **Fitting:** 7–9 well-spread neutral views give most of the gain. Twenty near-frontal shots constrain depth no better than one (`reconstruction/multi-view-fitting.md`) 🧠
- **Photogrammetry:** 40–150 photos in 3–4 rings, 10–20° steps, separate pass at 0.8–1.5 m (`reconstruction/photogrammetry-heads.md`) 🧠
- **One session, one day:** weight, hair, beard and morning puffiness vary between days 🧠

## Numbers & reference tables

**Table 1 — Shot list** (camera at 1.5–2 m; elevation = camera angle above the sitter's eye-level plane; at 1.75 m, ±25° means raising or lowering the camera ~0.8 m)

| # | View | Yaw | Elevation | Constrains | Tier | Badge |
|---|---|---|---|---|---|---|
| 1 | Front | 0° | 0° | widths, symmetry, eye and mouth shape | core | 🧠 |
| 2–3 | 3/4 L, R | ±45° | 0° | nose projection vs cheek, zygoma, gonial angle | core | 🧠 |
| 4–5 | Profile L, R | ±90° | 0° | nose, lip and chin projection; forehead slope; ear position | core | 🧠 |
| 6 | Low | 0° | −25 to −30° | jaw underside, nostrils, alar base | core | 🧠 |
| 7 | High | 0° | +25 to +30° | brow ridge, upper lids, crown | core | 🧠 |
| 8–9 | Low 3/4, high 3/4 | ±45° | ±25° | jaw–neck junction, cheek fullness | optional | 🧠 |
| 10–11 | Half-turn | ±20–30° | 0° | nasal dorsum against cheek, cheek contour | extended | 🧠 |
| 12–14 | Rear 3/4, back | ±135°, 180° | 0° | occiput, ear protrusion, nape | extended | 🧠 |
| 15 | Top | — | ~+80–90° | cranial vault, breadth vs length | extended | 🧠 |
| 16–17 | Ear close-ups | ±90° | 0° | helix, antihelix, concha, lobule | extended | 🧠 |
| 18–19 | Hair-down front, 3/4 | 0°, 45° | 0° | recognisability check | extended | 🧠 |

**Table 2 — Distance, perspective and framing** (arithmetic; Δ = 100 mm nose tip to tragion; field = long side in portrait orientation on a 36 mm sensor side; face width 140 mm)

| Distance (m) | Nose-over-ear excess | Field at 85 / 105 / 135 mm (m) | Face width, 105 mm on 24 MP (px) | Use | Badge |
|---|---|---|---|---|---|
| 0.35 | 29% | — (phone selfie) | — | never for identity | 🧠 |
| 1.0 | 10% | 0.42 / 0.34 / 0.27 | 2450 | solved camera only; never eyeball | 🧠 |
| 1.5 | 6.7% | 0.64 / 0.51 / 0.40 | 1633 | recommended | 🧠 |
| 2.0 | 5.0% | 0.85 / 0.69 / 0.53 | 1225 | recommended | 🧠 |
| 2.5 | 4.0% | 1.06 / 0.86 / 0.67 | 980 | recommended | 🧠 |
| 3.0 | 3.3% | 1.27 / 1.03 / 0.80 | 817 | near-orthographic | 🧠 |
| 5.0 | 2.0% | 2.12 / 1.71 / 1.33 | 490 | ortho tracing; needs ≥200 mm | 🧠 |

Phone face widths (12 MP, diagonal 35 mm equivalent): 1× at 1.5 m ≈280 px; 2× at 1.5 m ≈565 px; 3× (77 mm) at 1.75 m ≈720 px; 5× (120 mm) at 2.5 m ≈780 px 🧠

**Table 3 — Total depth of field (mm) at matched framing.** DoF ≈ 2Nc·u²/f², with c = 0.03 mm (halve it for pixel-level sharpness at 24 MP). The front view needs ~100–120 mm (nose tip to tragion), about 2/3 of it behind the eyes.

| Set-up | f/2.8 | f/4 | f/5.6 | f/8 | f/11 | Badge |
|---|---|---|---|---|---|---|
| 85 mm, 1.5 m | 52 | 75 | 105 | 149 | 206 | 🧠 |
| 105 mm, 2.0 m | 61 | 87 | 122 | 174 | 239 | 🧠 |
| 135 mm, 2.5 m | 58 | 82 | 115 | 165 | 226 | 🧠 |

**Table 4 — Pitch from a camera-height mismatch Δh**, atan(Δh/d), with the resulting nose-vs-tragion vertical shift, 100 mm·sin θ

| Δh | d = 1.0 m | 1.5 m | 2.0 m | 3.0 m | Badge |
|---|---|---|---|---|---|
| 0.1 m | 5.7° / 10 mm | 3.8° / 7 mm | 2.9° / 5 mm | 1.9° / 3 mm | 🧠 |
| 0.3 m | 16.7° / 29 mm | 11.3° / 20 mm | 8.5° / 15 mm | 5.7° / 10 mm | 🧠 |
| 0.5 m (standing photographer, seated sitter) | 26.6° / 45 mm | 18.4° / 32 mm | 14.0° / 24 mm | 9.5° / 16 mm | 🧠 |

**Table 5 — Smartphone lenses** (time-sensitive; 35 mm-equivalent)

| Camera | Equivalent | Use for heads | Badge |
|---|---|---|---|
| Front (selfie) | ~23–30 mm | never for identity | 🧠 |
| Ultra-wide | ~13–16 mm | never | 🧠 |
| Main 1× | ~24–26 mm | solver anchor at 0.5–0.8 m, or ≥1.5 m and cropped | 🧠 |
| 2× (often a main-sensor crop) | ~48–52 mm | acceptable at 1.2–2 m | ↔️ |
| 3× telephoto | ~65–77 mm | good at 1.5–2 m | ↔️ |
| 4–5× telephoto | ~100–125 mm (iPhone 17 Pro 4× = 100 mm equiv. [4]) | best at 2–3 m in good light | ↔️ |

**Table 6 — Photo counts by method**

| Method | Photos or frames | Spread | Time budget | Badge |
|---|---|---|---|---|
| Single-image regression | 1 front (a profile helps a lot) | — | — | 🧠 |
| Pin or template fitting (FaceBuilder-class) | 3–7 | front, 3/4, profiles | ~5 min | 🧠 |
| Multi-view landmark/3DMM identity fit | 7–9 core; 15–20 extended | yaw ±90°, elevation ±25° | ≤15 min | 🧠 |
| Monocular video tracker | 100–300 frames (10–30 s) | slow head turn to ±60–90° | ~1 min | ↔️ |
| Single-camera photogrammetry | 30–50 face, 60–120 head, +10–20 detail | 3–4 rings, 10–20° steps | ≤20–30 s per ring | 🧠 |
| Synchronised rig | 8–16 cameras face, 24–60 head | simultaneous | one strobe | ↔️ |

## Applying this to photo→3D face sculpting in Blender

1. **Set up the space:** a stool without backrest or swivel; a matte mid-grey backdrop ≥1 m behind; floor tape on a 1.75 m circle marked every 45° (22.5° for the extended set); tripod at eye height; a gaze mark on the wall ahead 🧠
2. **Consent and preparation:** written consent for capture, storage, processing and deletion (face data is biometric in many jurisdictions); then hair back, glasses off, powder, dots, measurements, scale card 🧠
3. **Shoot:** slate and chart frames; lock exposure, white balance, focus and lens; the identity set (Table 1) in bursts of 3, card in two views, each frame checked at 100% (eyes open, lashes sharp, ears visible, front without yaw); then optional passes (form light, hair-down, photogrammetry, expression video) 🧠
4. **Ingest:** keep originals untouched; make working copies with EXIF orientation baked in and HEIC converted to PNG; write the manifest (below); never crop or resize without recording it 🧠
5. **In Blender:** one solved camera per photo (`blender/reference-camera-setup.md`). The front should solve to yaw and roll <2°, profiles to 85–95°; distrust views whose solved distance misses the tape by >10% 🧠
6. **Sculpt:** block masses from profile and front; check nose projection and jaw in the 3/4 and low views; read planes from the form set; judge final likeness against the hair-down photos 🧠

**What goes wrong** 🧠

| Symptom | Capture cause | Fix |
|---|---|---|
| Ears too high or low | camera height ≠ eye level (Table 4) | re-shoot level, or free pitch in the solver |
| Nose too big, face too narrow | shot from <1 m | ≥1.5 m with a telephoto |
| Jaw and neck disagree between views | head tilted instead of camera moved; slumping | move the camera; reset posture |
| Eyelids differ between views | gaze followed the camera | fixed gaze mark |
| Focal length differs between "identical" shots | phone lens swap | lock the lens; group by `LensModel` |
| Texture seams, colour shifts | auto white balance or exposure | manual settings, chart, RAW |

## Algorithmic implications

- **Capture manifest** (JSON per session; shown in the add-on as a live shot checklist): per photo `view_tag`, nominal yaw and elevation, `lens_id`, measured distance, expression, hair, glasses, lighting tag (even / cross-pol / parallel / directional); per session caliper measurements with σ, scale objects, consent record 🧠
- **Pose priors from view tags** (initialisation plus weak prior): yaw σ 10° freehand, 5° with floor marks; pitch σ 5° on the main ring, 8–10° on high and low rings; roll σ 3°. Treat |solved − nominal| > 3σ as mislabelled or mirrored (flip test in `community/reddit-face-from-photos.md`) 🧠
- **Distance prior:** a tape-measured z with σ ≈ 5 cm (~3% at 1.75 m) breaks the focal–distance degeneracy when EXIF is missing or the crop unknown 🧠
- **Intrinsics grouping key:** (Make, Model, LensModel, FocalLength, width, height, still/video). Share log f within a group (σ ≈ 0.02), never across groups; video always gets its own group 🧠
- **Gates** 🧠:
  - reject eye aspect ratio <0.2 (blink; Soukupová & Čech 2016);
  - down-weight the bottom 20% by variance of the Laplacian on the face crop;
  - warn when the face is <250 px wide and reject below 120 px;
  - drop photometric terms when >2% of skin pixels are clipped;
  - exclude from the identity fit any view with mouth aperture >3% of inter-ocular distance (IOD) or a smile;
  - when hair covers the ears, drop the ear and temple landmarks.
- **Coverage score:** bin views by yaw (0, ±25, ±45, ±90, ±135, 180) and elevation (−25, 0, +25, top). Mark nose and chin projection "measured" only with a front view plus a |yaw| ≥ 60° view, and the jaw underside only with a low view. Otherwise show them as prior-driven in the heat-map 🧠
- **Anti-duplication:** weight each view by 1/(views in its 15° bin), so near-frontal bursts cannot dominate 🧠
- **Measurements as constraints:** caliper distances become landmark-pair residuals (σ 1–2 mm); the ID-1 card becomes a `ScaleRef` (σ ≈ 0.5 mm over 85.6 mm, ~0.6%) 🧠
- **Lighting tags route data:** albedo and photometric terms use only even or cross-polarised views; directional views feed landmarks, silhouettes and shading reference, with per-image gain 🧠
- **Video frame picker:** maximise bin coverage with ≤3 frames per bin, and drop frames where the relative angular speed exceeds ~10–15°/s. At a 15–30 ms phone readout that keeps rolling-shutter skew to a few pixels ↔️

## Disagreements, myths & open questions

- **Myth: "an 85 mm lens removes distortion."** Distance does that; the lens only frames the face from there 🧠
- **Myth: "shoot wide open."** At f/2.8 only ~6 cm is sharp (Table 3) 🧠
- **Myth: "farther is always better."** Beyond ~3 m gains are tiny while space, resolution and shake costs rise, and solvers use some perspective to identify focal length; 1.5–2.5 m is the practical optimum unless tracing orthographically 🧠
- **Myth: "more photos are better."** Duplicated angles add nothing, and mismatched expressions or lenses hurt (`reconstruction/multi-view-fitting.md`) ↔️
- **Rotate the sitter, or move the camera?** Rotating is fine for landmark fitting. It hurts photogrammetry and texture unless the light is fully even and the background masked ↔️
- **Flat light or form light?** Texture and photogrammetry need flat light, while sculptors want raking light to read planes. Shoot both ↔️
- **No consensus:** teeth together or apart; eyes on the lens or a fixed mark; 45° or "nose to cheek" obliques; 90–105 or 85–135 mm clinical lenses ↔️
- **Open questions** 🧠: how much phone pipelines (multi-frame fusion, face-aware processing) alter geometry; the gain per extra view in mm; 30° vs 45° obliques for fitting; current phone telephoto focal lengths and lens-switch rules (time-sensitive)

## Sources

1. ICAO TAG-MRTD/17 WP.009, pose tolerance ±5° (roll/pitch/yaw) in the standard — https://www2023.icao.int/Meetings/TAG-MRTD/Documents/Tag-Mrtd-17/TagMrtd17_WP009.pdf
2. Wikipedia, Polarizing filter (1–3 stops loss) — https://Www.wikipedia.org/wiki/Polarising_filter
3. Paul Bourke, Cross polarisation in photography (≥1.3 stops) — https://paulbourke.net/miscellaneous/crosspolarisation/index.html
4. Apple, iPhone 17 Pro technical specifications (4× Fusion Telephoto, 100 mm) — https://www.apple.com/am/iphone-17-pro/specs/

Related sourced material is in the sibling notes named above.

**Further reading (by name, not yet linked)**
- Ettorre et al., "Standards for digital photography in cranio-maxillo-facial surgery – Part I: Basic views and guidelines", J Craniomaxillofac Surg, 2006
- Yavuzer, Smirnov & Jackson, "Guidelines for standard photography in plastic surgery", Annals of Plastic Surgery, 2001
- Galdino, Vogel & Vander Kolk, "Standardizing digital photography: it's not all in the eye of the beholder", Plastic and Reconstructive Surgery, 2001
- Farkas, *Anthropometry of the Head and Face*, 2nd ed., 1994
- Moorrees & Kean, "Natural head position, a basic consideration in the interpretation of cephalometric radiographs", Am J Phys Anthropol, 1958
- Ward, Ward, Fried & Paskhover, "Nasal distortion in short-distance photographs: the selfie effect", JAMA Facial Plastic Surgery, 2018
- Sinha & Poggio, "I think I know that face...", Nature, 1996
- ICAO Doc 9303 and ICAO portrait-quality guidance; ISO/IEC 19794-5 and ISO/IEC 39794-5 (face image data)
- ISO/IEC 7810 (ID-1 card dimensions)
- Debevec et al., "Acquiring the Reflectance Field of a Human Face", SIGGRAPH 2000
- Ma et al., "Rapid Acquisition of Specular and Diffuse Normal Maps from Polarized Spherical Gradient Illumination", EGSR 2007
- Soukupová & Čech, "Real-Time Eye Blink Detection using Facial Landmarks", CVWW 2016

## Verification log (2026-11-20)

- Clinical photography lens 90–105 mm (85–135 mm range), Frankfurt horizontal, fixed distance (Ettorre/Yavuzer/Galdino): **unconfirmed**. Search summaries quoted Ettorre's "90–105 mm macro" but could not be tied to a specific URL; no distance or Frankfurt wording found. Stays ↔️.
- ICAO pose ±5° and 1.2–2.5 m: **pose confirmed, distance unconfirmed.** Yaw/pitch ±5° confirmed (roll relaxed to ±8° in the 19794-5 corrigendum) — https://www2023.icao.int/Meetings/TAG-MRTD/Documents/Tag-Mrtd-17/TagMrtd17_WP009.pdf. The 1.2–2.5 m distance was not found (ICAO Portrait Quality TR v1.0, https://icao.int/Security/FAL/TRIP/Documents/TR - Portrait Quality v1.0.pdf, is the likely place; contents not retrieved).
- Phone focal lengths and silent lens substitution: **unconfirmed** overall. Partial: iPhone 17 Pro 4× telephoto is 100 mm equiv. — https://www.apple.com/am/iphone-17-pro/specs/. No source found for low-light/minimum-focus switch to a cropped main camera (Moment mentions 12MP crop inside minimum focus: https://www.shopmoment.com/au/articles/iphone-17-camera-lenses-explained, text truncated).
- Cross-polarisation light cost ~2–3+ stops, best with on-axis lights: **contested** — range ~1.3 to 3+ stops: https://Www.wikipedia.org/wiki/Polarising_filter (1–3 stops), https://paulbourke.net/miscellaneous/crosspolarisation/index.html (≥1.3 stops), https://www.taylorfrancis.com/books/9781315722160/chapters/10.4324/9781315722160-9 (several stops). On-axis claim not verified.
