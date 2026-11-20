# Community & artist knowledge

*Area README for the research library on turning photos of a consenting person into a likeness-accurate, anatomically correct, sculpt-ready 3D head in Blender. Compiled 2026-11-20 from the 14 topic notes in this folder, their data tables in `../data/<topic>.json`, the per-topic digest and each note's verification log. Engine-facing digest: [`../_raw/requirements_community.md`](../_raw/requirements_community.md).*

## What this area covers

This area collects practitioner knowledge rather than lab results. It covers:

- how forum users (BlenderArtists, Polycount, Reddit), social and video teachers (Instagram, YouTube), portfolio breakdowns (ArtStation), ZBrush-era likeness teachers, traditional clay portraitists and the classic art-anatomy books get a likeness of a real person;
- how they shoot reference photos, clean and wrap scans, and judge AI-generated heads;
- which shared resources they rely on: awesome lists, datasets, anatomy atlases, scan stores and their licences.

Every note has an "Applying this to photo→3D face sculpting in Blender" section for artists and an "Algorithmic implications" section for the numpy fitting engine, so one body of knowledge serves both.

### Read this first: evidence quality

Across the 14 notes the badges count **19 ✅ verified · 63 📄 single-sourced · 824 🧠 expert knowledge · 250 ↔️ contested**: 1,156 claims, about 7% of them sourced. Most topics had no web harvest, so the notes are expert synthesis plus pinhole arithmetic.

- **Pinhole numbers** (magnification against distance, field of view, pitch from camera height) are reliable as geometry.
- **Anatomical ranges, thresholds and σ values** are provisional engineering defaults until they are checked against the anatomy notes or calibrated on synthetic and held-out data.
- **No source in this area ties "the likeness clicked" to a millimetre tolerance.**

Badge legend: ✅ verified (two sources, or confirmed by the fact-checker) · 📄 single source · 🧠 expert knowledge, not yet source-checked · ↔️ contested, population-dependent or time-sensitive.

**Verification corrections applied throughout this README.** The verification logs override the note bodies:

- **Ward et al. 2018, the "selfie effect":** the ≈30% figure is for the **nasal base** at 12 in against 5 ft; the nasal tip is ≈7%. The effect is modelled, not measured. The baseline is stated inconsistently (5 ft or orthographic), and a published letter argues part of it is perceptual.
- **KeenTools FaceBuilder:** the trial is **15 days per add-on**, not 30. The 2024 Freelancer price was 18 USD/month or 179 USD/year. Blender 5.0 has been supported since KeenTools 2025.3.
- **FLAME 2023 Open is CC BY 4.0,** so commercial use is allowed with attribution, but its texture model is BY-NC-SA 4.0. FLAME 2017/2019/2020 and the FLAME Blender add-on remain non-commercial.
- **MRD1:** sources give 3.5–4.5 mm (mean 3.5 mm in an older sample; 4.0–4.5 mm normal in a trial protocol), not 4–5 mm. Palpebral fissure height: mean 8.7 mm, range 7–12 mm.
- **Iris diameter (HVID) depends on the measuring device:** means run from 11.77 ± 0.40 mm (Orbscan) to 12.40 ± 0.43 mm (IOLMaster 700).
- **Hertel value (cornea ahead of the lateral orbital rim) depends on population:** published adult ranges are ≈8–23 mm; Caucasian means are 15.4–16.5 mm.
- **Ear axis tilt:** 15.6 ± 3.9° in one adult male cohort; other cohorts report >25° in ≈12–14% of people.
- **IPD:** the mean is ≈63 mm (63.36 mm, attributed to Dodgson 2004 by secondary sources). The SD is unconfirmed, and secondary sources give a range of 50–75 mm.
- **ICAO/ISO portrait pose:** ±5° yaw and pitch is confirmed, with roll relaxed to ±8° in the ISO/IEC 19794-5 corrigendum. The recalled 1.2–2.5 m distance was not found.
- **Cross-polarisation** costs ≈1.3 to 3+ stops; sources vary.
- **AI generators:** the Hunyuan3D licence excludes the EU, UK and South Korea and has a 1M MAU cap. TRELLIS and TRELLIS.2 are MIT, but some NVIDIA dependencies are non-commercial. Meshy free-plan outputs are CC BY 4.0.
- **Verified elsewhere in the area:** Blender Studio Human Base Meshes are CC0 ✅. MetaHuman may be used outside Unreal, Blender included, since the June 2025 (UE 5.6) licence update ✅. Smartphone wide-angle "face distortion correction" warps faces near the frame edge away from a pinhole projection ✅.

### How to use this area

- **Artists:** read the principles, then work through the [Blender checklist](#practical-checklist-for-an-artist-working-in-blender). The quick-reference tables give working numbers with their badges.
- **Engineers:** start with the [requirements digest](../_raw/requirements_community.md), then read the [contradictions](#cross-topic-contradictions-and-how-to-resolve-them) before choosing any default. Machine-readable tables are in `../data/<topic>.json`.
- **Everyone:** treat 🧠 numbers as starting values. For sourced values, follow the cross-links to `../anatomy/`, `../blender/` and `../reconstruction/` (for example `anatomy/facial-asymmetry.md`, `blender/reference-camera-setup.md`, `reconstruction/multi-view-fitting.md`).

Note abbreviations used in the tables: [LM](./likeness-mistakes.md), [RPP](./reference-photography-protocol.md), [RD](./reddit-face-from-photos.md), [IG](./instagram-social-sculptors.md), [PC](./polycount-likeness.md), [ZB](./zbrush-to-blender-likeness.md), [YT](./youtube-likeness-blender.md), [AS](./artstation-likeness.md), [TR](./traditional-portrait-sculpture.md), [AAB](./art-anatomy-books.md), [SCW](./scan-cleanup-wrapping.md), [AWL](./awesome-lists-resources.md), [AI](./ai-assisted-sculpting.md), [BA](./blenderartists-forum.md).

## Core principles

### A. Camera and reference

1. **Camera distance sets perspective; focal length only crops.** The nose tip is magnified against the ear plane by ≈(d + 0.10 m)/d: 1.33 at 0.3 m, 1.10 at 1 m and 1.05 at 2 m. Shoot from 1.5–2.5 m with an 85–135 mm-equivalent lens and crop afterwards. 🧠 (geometry); the selfie effect is ✅. Notes: [reference-photography-protocol](./reference-photography-protocol.md), [reddit-face-from-photos](./reddit-face-from-photos.md), [blenderartists-forum](./blenderartists-forum.md), [zbrush-to-blender-likeness](./zbrush-to-blender-likeness.md), [artstation-likeness](./artstation-likeness.md).
2. **Never judge likeness through an unmatched camera.** Give each photo its own solved perspective camera (focal length, distance, principal point, render resolution equal to the photo's pixels), with the photo as that camera's background image. Orthographic front and side planes are valid only for distant telephoto photos (about ≥3 m). 🧠. Notes: [youtube-likeness-blender](./youtube-likeness-blender.md), [zbrush-to-blender-likeness](./zbrush-to-blender-likeness.md), [blenderartists-forum](./blenderartists-forum.md), [polycount-likeness](./polycount-likeness.md).
3. **Most likeness errors start in the reference, not the sculpting.** Each of these misleads in a known direction: arm's-length selfies, mirrored front-camera images, beauty filters, phone lens correction (✅), liquified magazine covers (↔️), un-desqueezed anamorphic film stills, and photos taken years apart. 🧠 ✅. Notes: [artstation-likeness](./artstation-likeness.md), [reddit-face-from-photos](./reddit-face-from-photos.md), [likeness-mistakes](./likeness-mistakes.md).
4. **Solve head pose before placing features.** Unsolved pitch is the main cause of ears placed too high or too low: 5° moves the ears ≈5.7–7.0 mm against the eye line. 3° of roll or 5° of yaw fakes more asymmetry than a normal face has. A camera 0.3 m off eye level at 1.5 m gives ≈11° of pitch. 🧠. Notes: [likeness-mistakes](./likeness-mistakes.md), [reference-photography-protocol](./reference-photography-protocol.md).
5. **Depth needs angle, not more frontal photos.** Nose and chin projection count as measured only with a front view plus a view at |yaw| ≥ 60°. Twenty near-frontal shots constrain depth no better than one. Single-photo tools (AI generators, AutoFace, MetahumanModeler) take depth from their prior. 🧠 📄. Notes: [reference-photography-protocol](./reference-photography-protocol.md), [artstation-likeness](./artstation-likeness.md), [blenderartists-forum](./blenderartists-forum.md).
6. **Photos carry no absolute scale.** A measurement beats the population IPD prior (mean ≈63 mm; SD unconfirmed). Use a glasses-prescription PD, a caliper reading, or an ID-1 card in at least 2 views. 🧠 ↔️. Notes: [blenderartists-forum](./blenderartists-forum.md), [zbrush-to-blender-likeness](./zbrush-to-blender-likeness.md), [reference-photography-protocol](./reference-photography-protocol.md).
7. **Capture one consistent identity set.** Take 7–9 core stills (front, ±45°, ±90°, about 25–30° below and above) in one session of 15 minutes or less. Use one locked lens, with the camera at the sitter's eye–nose level, at f/8 full frame, in even diffuse light. The sitter keeps a neutral face with the same teeth position in every shot, the gaze on a fixed mark, hair off the ears and hairline, and glasses off. 🧠. Notes: [reference-photography-protocol](./reference-photography-protocol.md), [instagram-social-sculptors](./instagram-social-sculptors.md).

### B. Process

8. **Big to small, all views at once, with gates.** Work masses → feature placement → feature shape → surface, and add no detail until silhouettes and landmarks agree in every view. 🧠. Notes: [polycount-likeness](./polycount-likeness.md), [traditional-portrait-sculpture](./traditional-portrait-sculpture.md), [instagram-social-sculptors](./instagram-social-sculptors.md).
9. **Fit all views together; no hero photo.** A fix that helps one view and hurts two is wrong (ZBrush "whack-a-mole"), and a sculpt matched to one photo fails against the others. 🧠 ↔️. Notes: [zbrush-to-blender-likeness](./zbrush-to-blender-likeness.md), [artstation-likeness](./artstation-likeness.md), [likeness-mistakes](./likeness-mistakes.md).
10. **The profile silhouette is the most diagnostic view, and silhouettes slide.** Jaw, cheek and cranial outlines are occluding contours that move across the surface as the view turns. In a true profile only the forehead–nose–lips–chin line lies near the midline. 🧠. Notes: [zbrush-to-blender-likeness](./zbrush-to-blender-likeness.md), [traditional-portrait-sculpture](./traditional-portrait-sculpture.md).
11. **Measure between bony, expression-independent landmarks; the ear hole is the hub.** Distances from tragion to nasion, subnasale and gnathion fix face depth and asymmetry that frontal photos cannot. Mouth corners, lip line and hairline are trusted least. 🧠. Notes: [traditional-portrait-sculpture](./traditional-portrait-sculpture.md), [instagram-social-sculptors](./instagram-social-sculptors.md).
12. **Symmetry is a prior, not a constraint.** Block in with symmetry on, then release it. Real faces differ from their mirror image by ≈0.80 ± 0.24 mm RMS (📄). When to release it is contested ↔️. Notes: [likeness-mistakes](./likeness-mistakes.md), [polycount-likeness](./polycount-likeness.md), [scan-cleanup-wrapping](./scan-cleanup-wrapping.md).
13. **Keep identity and expression apart.** Fit identity from neutral photos and give each view its own zero-mean expression, so a smile or open jaw never becomes identity. The FaceBuilder vendor itself says neutral photos fit better. 📄. Notes: [blenderartists-forum](./blenderartists-forum.md), [artstation-likeness](./artstation-likeness.md), [zbrush-to-blender-likeness](./zbrush-to-blender-likeness.md).
14. **Build the eyes first, as globes.** Place ≈24 mm eyeballs before the lids, give the lids real margin thickness, and check cornea depth from above. Eyes too big, too open or too far forward is the most common critique. 🧠 ↔️. Notes: [likeness-mistakes](./likeness-mistakes.md), [polycount-likeness](./polycount-likeness.md).
15. **Hair and beards bound the skull from outside.** Treat hair silhouettes as outer bounds and take the cranium under them from a prior. "Cranium too short" and "neck too thin" are among the most frequent verdicts. 🧠. Notes: [polycount-likeness](./polycount-likeness.md), [traditional-portrait-sculpture](./traditional-portrait-sculpture.md), [scan-cleanup-wrapping](./scan-cleanup-wrapping.md).

### C. Perception and checks

16. **Brows and hair carry identity.** Add proxy brows and a hairline before any likeness verdict. Judge likeness with them on and shape with them off. Never distort correct geometry because grey clay does not read as the person. 🧠. Notes: [artstation-likeness](./artstation-likeness.md), [polycount-likeness](./polycount-likeness.md), [traditional-portrait-sculpture](./traditional-portrait-sculpture.md).
17. **Projected textures fake likeness.** A photo texture looks right from its own camera, so review shape untextured, from cameras at least 20–30° away, against at least 2 held-out photos. 🧠. Notes: [likeness-mistakes](./likeness-mistakes.md), [artstation-likeness](./artstation-likeness.md), [ai-assisted-sculpting](./ai-assisted-sculpting.md).
18. **Each studio check defeats one perceptual mechanism and has a computational twin.** Flip resets adaptation; blur or squint removes detail; a thumbnail tests configuration; the silhouette shows depth independently of lighting; overlay, difference and blink expose offsets; grayscale removes hue. Inversion helps judge spacing but hides feature errors (the Thatcher illusion). 🧠 ↔️. Notes: [likeness-mistakes](./likeness-mistakes.md), [traditional-portrait-sculpture](./traditional-portrait-sculpture.md).
19. **Canons are scaffolds and vocabulary, never targets.** The neoclassical canons fail in most measured subjects ✅. The orbital canon performs best, yet only 30.6% of African American women met it ✅. There is no support for the golden ratio or the phi mask ✅. Notes: [art-anatomy-books](./art-anatomy-books.md).
20. **Likeness lives in deviation from the average.** Priors and idealisation pull a fit toward an attractive mean, "a good-looking cousin", so preserve large deviations. Exaggeration (caricature) aids recognition in 2D but is unmeasured for realistic 3D ↔️. Notes: [likeness-mistakes](./likeness-mistakes.md), [polycount-likeness](./polycount-likeness.md), [instagram-social-sculptors](./instagram-social-sculptors.md).
21. **Likeness is a low-frequency property.** Forms of ≈2 mm wavelength and up carry it, and they are complete by Multires L2–L3 on a ≈10k-quad base. Pores add realism, not likeness. 🧠. Notes: [scan-cleanup-wrapping](./scan-cleanup-wrapping.md), [ai-assisted-sculpting](./ai-assisted-sculpting.md), [zbrush-to-blender-likeness](./zbrush-to-blender-likeness.md).
22. **Match the light.** Judge form under one key light matched to the photo, not under flat matcaps. Shading from one light cannot fix depth scale (the bas-relief ambiguity). 🧠. Notes: [polycount-likeness](./polycount-likeness.md), [art-anatomy-books](./art-anatomy-books.md), [likeness-mistakes](./likeness-mistakes.md).

### D. Tools, scans and licences

23. **No automatic route gives a finished likeness.** FaceBuilder, Headshot, Mesh to MetaHuman and photogrammetry each give a base, and auto-pins are a draft by the vendor's own account (📄). The likeness is still sculpted against solved cameras. 🧠 📄. Notes: [reddit-face-from-photos](./reddit-face-from-photos.md), [youtube-likeness-blender](./youtube-likeness-blender.md), [blenderartists-forum](./blenderartists-forum.md).
24. **Treat AI image-to-3D output as a weak shape prior.** It gives a plausible bust in minutes but almost never a likeness: the texture carries the identity, profile depth is invented, eyes and lips fuse, and hair inflates the cranium. 🧠 ↔️. Notes: [ai-assisted-sculpting](./ai-assisted-sculpting.md), [reddit-face-from-photos](./reddit-face-from-photos.md).
25. **A wrap is landmarks, then a thin-plate spline, then annealed non-rigid ICP.** Stiffness and landmark weight relax stage by stage ✅, and Shrinkwrap is only a final snap. Keep the raw scan as the only bake source, never fill holes you fit to, and never symmetrise. ✅ 🧠. Notes: [scan-cleanup-wrapping](./scan-cleanup-wrapping.md).
26. **Likeness can die downstream.** Retopology, baking, shading and hair cards can each lose it, so measure the deviation from sculpt to final mesh before approval. 🧠. Notes: [polycount-likeness](./polycount-likeness.md).
27. **Upstream licences decide what ships.** Most 3DMM data and landmark-model weights are non-commercial even when the code is permissive. FLAME 2023 Open is CC BY 4.0 (📄), MetaHuman may be used outside Unreal (✅), and Blender Studio Human Base Meshes are CC0 (✅). Keep provenance for every asset. Notes: [awesome-lists-resources](./awesome-lists-resources.md), [blenderartists-forum](./blenderartists-forum.md), [ai-assisted-sculpting](./ai-assisted-sculpting.md), [youtube-likeness-blender](./youtube-likeness-blender.md).
28. **Consent and approval are part of the pipeline.** Capture with written consent, since face data is biometric in many jurisdictions (GDPR special category ↔️). Show the sitter both the mirror and the true orientation, and keep approval edits reversible. 🧠 ↔️. Notes: [reference-photography-protocol](./reference-photography-protocol.md), [polycount-likeness](./polycount-likeness.md), [ai-assisted-sculpting](./ai-assisted-sculpting.md).

## Quick-reference tables

All values come from the notes; the badge is the note's own, after verification corrections.

### Q1. Perspective against camera distance

Pinhole geometry: nose-tip magnification over the ear (tragion) plane is (d + Δ)/d, with Δ ≈ 10 cm (9–12 cm assumed; the depth itself is unconfirmed). The framing column gives the f₃₅ that fills a 0.40 m vertical field in portrait orientation.

| Camera → nose tip | Nose : ear magnification | f₃₅ to frame 0.40 m | Typical source | Use as a shape cue | Badge | Notes |
|---|---|---|---|---|---|---|
| 0.3 m | 1.33 (1.30–1.40) | 27 mm | close selfie | never | 🧠 | [RD](./reddit-face-from-photos.md), [BA](./blenderartists-forum.md), [IG](./instagram-social-sculptors.md) |
| 0.5 m | 1.20 (1.18–1.24) | 45 mm | arm's-length selfie | only through a solved camera | 🧠 | [YT](./youtube-likeness-blender.md), [ZB](./zbrush-to-blender-likeness.md) |
| 1.0 m | 1.10 (1.09–1.12) | 90 mm | phone held by someone else; 85 mm headshot | yes, solved camera; never eyeballed | 🧠 | [RPP](./reference-photography-protocol.md) |
| 1.5 m | 1.067 | 135 mm | good likeness reference | recommended | 🧠 | [RPP](./reference-photography-protocol.md), [IG](./instagram-social-sculptors.md) |
| 2.0 m | 1.05 | 180 mm (or 85 mm cropped) | tele portrait | recommended | 🧠 | [IG](./instagram-social-sculptors.md) |
| 2.5 m | 1.04 | — | — | recommended | 🧠 | [RPP](./reference-photography-protocol.md) |
| 3.0 m | 1.033 | 270 mm (or 85–135 mm cropped) | long tele | near-orthographic; ortho planes acceptable | 🧠 | [YT](./youtube-likeness-blender.md), [TR](./traditional-portrait-sculpture.md) |
| 5.0 m | 1.02 | — | press, long lens | ortho tracing (needs ≥200 mm) | 🧠 | [RPP](./reference-photography-protocol.md) |

Measured counterpart: in Ward et al. 2018 the nasal base appears ≈30% wider at 12 in (≈30 cm) than at 5 ft, and the nasal tip ≈7% wider. ✅ in [AS](./artstation-likeness.md) (press and university summaries); 📄 in [LM](./likeness-mistakes.md), [RD](./reddit-face-from-photos.md), [YT](./youtube-likeness-blender.md).

**Phone lenses** (35 mm equivalent; time-sensitive; [RPP](./reference-photography-protocol.md), [ZB](./zbrush-to-blender-likeness.md)):

| Module | f₃₅ | Use for heads | Badge |
|---|---|---|---|
| Front (selfie) | ≈22–30 mm | never for identity | 🧠 |
| Ultra-wide | ≈13–16 mm | never | 🧠 |
| Main 1× | ≈23–28 mm | solver anchor at 0.5–0.8 m, or ≥1.5 m and cropped | 🧠 |
| 2× (often a main-sensor crop) | ≈46–52 mm | acceptable at 1.2–2 m | ↔️ |
| 3× tele | ≈65–77 mm | good at 1.5–2 m | ↔️ |
| 4–5× tele | ≈100–125 mm (iPhone 17 Pro 4× = 100 mm 📄) | best at 2–3 m in good light | ↔️ |

### Q2. Apparent error from unsolved pose

| Unsolved error | What moves | 3° | 5° | 10° | Badge | Note |
|---|---|---|---|---|---|---|
| Roll | eye-height difference across a 63 mm IPD | 3.3 mm | 5.5 mm | 10.9 mm | 🧠 | [LM](./likeness-mistakes.md) |
| Yaw | nose tip sideways against the canthal midpoint | 1.8–2.6 mm | 3.1–4.4 mm | 6.1–8.7 mm | 🧠 | [LM](./likeness-mistakes.md) |
| Pitch | nose tip vertically against the eye line | 1.8–2.6 mm | 3.1–4.4 mm | 6.1–8.7 mm | 🧠 | [LM](./likeness-mistakes.md) |
| Pitch | ears vertically against the eye line | 3.4–4.2 mm | 5.7–7.0 mm | 11.3–13.9 mm | 🧠 | [LM](./likeness-mistakes.md) |

Pitch caused by a camera-height mismatch Δh, shown as angle / vertical shift of the nose tip against the tragion ([RPP](./reference-photography-protocol.md), 🧠):

| Δh | d = 1.0 m | 1.5 m | 2.0 m | 3.0 m |
|---|---|---|---|---|
| 0.1 m | 5.7° / 10 mm | 3.8° / 7 mm | 2.9° / 5 mm | 1.9° / 3 mm |
| 0.3 m | 16.7° / 29 mm | 11.3° / 20 mm | 8.5° / 15 mm | 5.7° / 10 mm |
| 0.5 m (standing photographer, seated sitter) | 26.6° / 45 mm | 18.4° / 32 mm | 14.0° / 24 mm | 9.5° / 16 mm |

A 2° yaw fakes 2–3 mm of asymmetry 🧠 ([RPP](./reference-photography-protocol.md)).

### Q3. Capture defaults

| Item | Value | Badge | Note |
|---|---|---|---|
| Distance | 1.5–2.5 m; beyond ≈3 m the gains are tiny | 🧠 | [RPP](./reference-photography-protocol.md) |
| Lens | 85–135 mm equivalent; on a phone, a physical 2–5× lens from 1.5–3 m | 🧠 | [RPP](./reference-photography-protocol.md) |
| Camera height | lens at the sitter's eye–nose level, axis level; raise or lower the camera, never tilt the head | 🧠 | [RPP](./reference-photography-protocol.md) |
| Aperture | f/8 full frame (≈f/5.6 APS-C, f/4 Micro Four Thirds), focus on the near eye; at f/2.8 only ≈6 cm is sharp | 🧠 | [RPP](./reference-photography-protocol.md) |
| Shutter, ISO | ≥1/125 s on a tripod, ≥1/250 s handheld; ISO 100–400 | 🧠 | [RPP](./reference-photography-protocol.md) |
| Core identity set | 7–9 views: front, ±45°, ±90°, −25 to −30°, +25 to +30° | 🧠 | [RPP](./reference-photography-protocol.md) |
| Extended set | 15–20 views: add ±20–30°, ±135°, back, top, ear close-ups, hair-down front and 3/4 | 🧠 | [RPP](./reference-photography-protocol.md) |
| Practitioner yaw ring | 8 views (every 45°) at minimum, 12–16 preferred | 🧠 | [IG](./instagram-social-sculptors.md) |
| Session | one session of ≤15 min, one day; bursts of 3 per view | 🧠 ↔️ | [RPP](./reference-photography-protocol.md) |
| Expression | neutral; teeth lightly touching or ≈2–4 mm apart, the same in every shot | ↔️ | [RPP](./reference-photography-protocol.md) |
| Gaze | fixed on a mark straight ahead while the camera moves | ↔️ | [RPP](./reference-photography-protocol.md) |
| Prep | glasses off 10–15 min early; hair off ears and hairline (a cap adds ≈1–3 mm, so log it) | 🧠 | [RPP](./reference-photography-protocol.md) |
| Scale | ID-1 card (85.60 × 53.98 mm) or a ruler at cheek depth in ≥2 views; calipers σ ≈1–2 mm | 🧠 | [RPP](./reference-photography-protocol.md) |
| Light for fitting and texture | two softboxes at ±45°, key:fill ≤1.5:1 | 🧠 | [RPP](./reference-photography-protocol.md) |
| "Form" light set | one key at 45°, then 90°, 4:1–8:1 | ↔️ | [RPP](./reference-photography-protocol.md) |
| Cross-polarisation | for albedo and photogrammetry only; costs ≈1.3 to 3+ stops | ↔️ | [RPP](./reference-photography-protocol.md) |
| Face size | warn below 250 px wide, reject below 120 px; hero photos ≥400–600 px | 🧠 | [RPP](./reference-photography-protocol.md), [AS](./artstation-likeness.md) |
| Biometric pose standard | ±5° yaw and pitch; roll ±8° (a floor, not a target) | 📄 | [RPP](./reference-photography-protocol.md) |
| Photogrammetry pass | 40–150 photos in 3–4 rings, 10–20° steps, 60–80% overlap, ≤20–30 s per ring, 0.6–1.5 m, f/5.6–f/11 | 🧠 | [RPP](./reference-photography-protocol.md), [RD](./reddit-face-from-photos.md), [YT](./youtube-likeness-blender.md) |
| Video supplement | 4K at top bitrate, ≥1/250 s, ≥25–35 s per orbit, extract 2–5 fps | 🧠 | [RPP](./reference-photography-protocol.md) |

### Q4. Anatomical scale anchors and likeness checks (adults, neutral face)

| Quantity | Value | Use | Badge | Notes |
|---|---|---|---|---|
| Interpupillary distance | 63 mm; prior σ 3.5 mm (3.7 in ZB, 4 in IG); mean 63.36 mm per secondary source; SD unconfirmed | absolute scale when nothing is measured | 🧠 ↔️ | [BA](./blenderartists-forum.md), [ZB](./zbrush-to-blender-likeness.md), [IG](./instagram-social-sculptors.md) |
| Measured PD or caliper pair | measured value ± 1 mm (calipers 1–2 mm) | overrides any prior | 🧠 | [ZB](./zbrush-to-blender-likeness.md), [RPP](./reference-photography-protocol.md) |
| Iris diameter (HVID) | prior 11.7 ± 0.5 mm; device means 11.77 ± 0.40 to 12.40 ± 0.43 mm | per-photo scale when the iris is ≥20 px | ↔️ | [IG](./instagram-social-sculptors.md), [LM](./likeness-mistakes.md) |
| Eyeball | 24 mm sphere (radius 12 ± 0.5 mm) | eye proxy | 🧠 | [LM](./likeness-mistakes.md), [YT](./youtube-likeness-blender.md) |
| Cornea ahead of lateral orbital rim (Hertel) | prior 16 ± 2.5 mm; published 8–23 mm by population; Caucasian means 15.4–16.5 mm | eye depth | ↔️ | [LM](./likeness-mistakes.md), [PC](./polycount-likeness.md) |
| MRD1 | prior 4.5 ± 1 mm; sources 3.5–4.5 mm; falls with age | lid level; sclera above the iris reads as a stare | ↔️ | [LM](./likeness-mistakes.md), [PC](./polycount-likeness.md) |
| Palpebral fissure height | 8–11 mm; verified mean 8.7 mm, range 7–12 mm | eye opening | ↔️ | [LM](./likeness-mistakes.md) |
| Fissure length en–ex | 27–33 mm | "five eyes" check | 🧠 | [LM](./likeness-mistakes.md), [BA](./blenderartists-forum.md) |
| Intercanthal en–en | 28–35 mm; Kosovo-Albanian 32.5 ± 2.6 (M) / 31.8 ± 2.3 (F) mm | eye spacing | 🧠 / 📄 | [LM](./likeness-mistakes.md), [AAB](./art-anatomy-books.md) |
| Alar width al–al | 31–40 mm; often >40 mm in African-descent samples | nose width | ↔️ | [LM](./likeness-mistakes.md) |
| Mouth width ch–ch | 46–58 mm; ch–ch/IPD 0.78–0.90 | corners usually inside the pupil lines | 🧠 | [LM](./likeness-mistakes.md), [PC](./polycount-likeness.md) |
| Upper-lid margin thickness | ≈1.5–2.5 mm (flag <1 mm, "paper lids") | lids | 🧠 | [PC](./polycount-likeness.md) |
| Ear length / width | means ≈57–63 / 29–33 mm; prior 60 ± 4 mm | ear scale | 🧠 | [LM](./likeness-mistakes.md) |
| Ear axis tilt from vertical | prior 20 ± 7°; 15.6 ± 3.9° in one cohort; >25° in ≈12–14% elsewhere | "ears too upright" | ↔️ | [LM](./likeness-mistakes.md), [PC](./polycount-likeness.md) |
| Ear protrusion (helix to mastoid) | 17 ± 4 mm | top and front check | ↔️ | [LM](./likeness-mistakes.md) |
| Tragion height | level with orbitale (Frankfort); prior 0 ± 4 mm, only after pitch is solved | ear placement | 🧠 | [LM](./likeness-mistakes.md) |
| Head length g–op / breadth eu–eu | 175–205 / 140–160 mm; cranial σ ≈7 mm within one sex | cranium under hair | ↔️ | [LM](./likeness-mistakes.md), [PC](./polycount-likeness.md) |
| Face height n–gn | 125.8 ± 6.4 (M) / 115.5 ± 5.0 (F) mm, Kosovo-Albanian; SD 5–7 mm across three sources | σ basis (CV ≈4–8%) | ✅ | [AAB](./art-anatomy-books.md) |
| Scalp soft tissue | ≈4–8 mm over bone (unconfirmed) | cranium from hair outline | 🧠 | [PC](./polycount-likeness.md) |
| Whole-face mirror RMSD | 0.80 ± 0.24 mm; flag <0.3 mm as over-symmetrised | keep asymmetry | 📄 | [SCW](./scan-cleanup-wrapping.md), [LM](./likeness-mistakes.md) |
| Freeway space (rest against occlusion) | 2–4 mm | why the teeth position matters | 🧠 | [IG](./instagram-social-sculptors.md) |

The tragion depth chords (t–n ≈115–125 / 108–117 mm, t–sn ≈120–130 / 112–121 mm, t–gn ≈135–150 / 125–138 mm, M / F) are reconstructed from head geometry, not read from Farkas: ↔️ in [TR](./traditional-portrait-sculpture.md).

### Q5. Camera priors and photo-source types

Focal priors are log-normal on the 35 mm-equivalent focal length f₃₅, with σ_log = SD of ln f. All are 🧠 design values.

| Situation | Median f₃₅ | σ_log | Notes |
|---|---|---|---|
| Controlled capture, EXIF, one lens group | EXIF | 0.02 (tie within a lens group) | [AS](./artstation-likeness.md), [RPP](./reference-photography-protocol.md), [BA](./blenderartists-forum.md) |
| EXIF present, uncropped | EXIF | 0.03 | [ZB](./zbrush-to-blender-likeness.md), [YT](./youtube-likeness-blender.md) |
| EXIF present, possible crop or digital zoom | EXIF | 0.05–0.10 | [RD](./reddit-face-from-photos.md), [BA](./blenderartists-forum.md) |
| Physical focal length, guessed sensor | computed | 0.10 | [ZB](./zbrush-to-blender-likeness.md) |
| Phone, no EXIF | 26 mm | 0.25 | [RD](./reddit-face-from-photos.md) |
| Unknown camera | 50 mm | 0.6 (0.5 in YT) | [RD](./reddit-face-from-photos.md), [ZB](./zbrush-to-blender-likeness.md) |
| Current engine default (no EXIF) | — | 0.35 | [BA](./blenderartists-forum.md), [IG](./instagram-social-sculptors.md) |
| Camera distance, no measurement | 1.0 m | 0.7 | [ZB](./zbrush-to-blender-likeness.md) |
| Tape-measured distance | measured | σ ≈5 cm | [RPP](./reference-photography-protocol.md) |
| Principal point | image centre | 1% of max(W, H); 10% if cropped | [ZB](./zbrush-to-blender-likeness.md) |
| Radial k1 | 0 | σ 0.02 (reject ultra-wide images) | [ZB](./zbrush-to-blender-likeness.md) |
| Pixel aspect | 1.0 | σ 0.01 unless the frame is anamorphic | [AS](./artstation-likeness.md) |
| Freeing focal length | — | only when the views span ≥60° of yaw | [RD](./reddit-face-from-photos.md) |

Photo-source types for curated, existing photos ([AS](./artstation-likeness.md); the multipliers are design choices):

| Source | Typical d | f₃₅ prior | Nose:ear | Landmark σ multiplier | Use for | Badge |
|---|---|---|---|---|---|---|
| Event or press telephoto | 3–10 m | 135 mm, σ_log 0.5 | 1.01–1.03 | 1.0 | proportions, profile, yaw sweeps | 🧠 |
| Own controlled capture | 1.5–3 m | EXIF, 0.02 | 1.03–1.07 | 0.7–1.0 | everything | 🧠 |
| Studio portrait or magazine | 1.5–4 m | 100 mm, 0.4 | 1.03–1.07 | 2–3 or exclude (liquify risk) | hairline, colour | ↔️ |
| Film or TV still | 0.6–3 m | 50 mm, 0.7 | 1.03–1.17 | 1.5–2 | 3/4 form, expression | 🧠 |
| Interview video frame | 1–3 m | 50 mm, 0.7 | 1.03–1.10 | 1.5–2.5 | yaw coverage | 🧠 |
| Phone rear camera | 0.8–2 m | 26 mm, 0.6 | 1.05–1.13 | 1.2 | general | 🧠 |
| Phone selfie | 0.3–0.6 m | 26 mm, 0.1 | 1.17–1.33 | 3 or exclude | colour, hairline only | ↔️ |

### Q6. Landmark noise

| Landmark kind | σ | Badge | Notes |
|---|---|---|---|
| Automatic interior points (canthi, mouth corners, alae) | 0.02–0.03 × IOD | 🧠 | [RD](./reddit-face-from-photos.md), [BA](./blenderartists-forum.md), [ZB](./zbrush-to-blender-likeness.md) (↔️ there) |
| Automatic jaw and cheek contour | 0.05–0.08 × IOD, along the silhouette normal only | 🧠 | [RD](./reddit-face-from-photos.md), [BA](./blenderartists-forum.md), [AS](./artstation-likeness.md) |
| Brows | 0.04–0.06 × IOD, or ≈2 mm; never used for camera solving | 🧠 | [ZB](./zbrush-to-blender-likeness.md), [PC](./polycount-likeness.md) |
| Hairline (trichion) | 3–5 mm; never used for camera solving | 🧠 | [PC](./polycount-likeness.md) |
| Ears | 0.06–0.10 × IOD; weight 0 when \|yaw\| < 30° | 🧠 | [RD](./reddit-face-from-photos.md), [LM](./likeness-mistakes.md) |
| User-moved pins | 0.01 × IOD (RD); 0.75% IOD (YT); 1–2 screen px at the current zoom (BA) | 🧠 | [RD](./reddit-face-from-photos.md), [YT](./youtube-likeness-blender.md), [BA](./blenderartists-forum.md) |
| Reviewed auto-pins (vendor style) | 1.5% IOD corners, 2.5% lid and lip contours, 4% face oval | 🧠 | [YT](./youtube-likeness-blender.md) |
| Tier A bony landmarks (n, t, ex, en, prn, sn, pg, gn, zy, go) | caliper σ 1–2 mm | 🧠 | [TR](./traditional-portrait-sculpture.md) |
| Tier B soft landmarks (ch, sto, ls, li, al) | 2–4 mm | 🧠 | [TR](./traditional-portrait-sculpture.md) |
| Tier C hair-dependent landmarks (v, eu, op, tr) | one-sided bounds only; never for scale | 🧠 | [TR](./traditional-portrait-sculpture.md) |
| Scan wrap: point / sliding contour / ears and detector points on renders | 1 / 1.5–2 / 2–3 mm | 🧠 | [SCW](./scan-cleanup-wrapping.md) |
| Robust loss | Huber δ = 2σ; down-weight a view with RMS > 3σ or > 2× the median | 🧠 | [RD](./reddit-face-from-photos.md), [ZB](./zbrush-to-blender-likeness.md) |

### Q7. Symmetry schedules (σ of the mirror penalty)

| Note | Blockout / masses | Features | Surface / final | Badge |
|---|---|---|---|---|
| [PC](./polycount-likeness.md) | 1.0 mm | 2.0 mm (engine default `Priors.sigma_sym`) | 4.0 mm; `sigma_mid` 1.5 mm throughout | ↔️ |
| [ZB](./zbrush-to-blender-likeness.md) | 0.5 mm | 0.5 mm | 2–3 mm | 🧠 |
| [IG](./instagram-social-sculptors.md), [YT](./youtube-likeness-blender.md) | ≈1 mm | 2 mm or looser | 2–3 mm per vertex | 🧠 |
| [RD](./reddit-face-from-photos.md) | 1–2 mm per mirrored pair, which multi-view evidence can override | | | 🧠 |
| [SCW](./scan-cleanup-wrapping.md) (scan wrap) | ≥3–5 mm, only to fill unseen regions | | | 🧠 |

### Q8. Stage gates and acceptance thresholds

| Gate | Threshold | Badge | Notes |
|---|---|---|---|
| Masses → features | silhouette chamfer < 2% of n–gn and landmark RMS < 4% IOD; or chamfer < 2–3 mm in every view | 🧠 | [PC](./polycount-likeness.md), [TR](./traditional-portrait-sculpture.md) |
| Features → surface | detector-landmark RMS < 3% IOD (user-checked pins < 1.5%) in every view, including one held-out photo | 🧠 | [PC](./polycount-likeness.md) |
| Surface passes | no landmark moves > 0.5 mm | 🧠 | [PC](./polycount-likeness.md) |
| Primary-likeness target | interior reprojection < 2–3% IOD; silhouette < 1–2 mm | 🧠 | [AS](./artstation-likeness.md) |
| Caliper sheet | flag Δ > 2 mm (Tier A), > 3 mm (Tier B) | 🧠 | [TR](./traditional-portrait-sculpture.md) |
| Camera QA | front yaw and roll < 2°; profiles 85–95°; solved distance within 10% of the tape | 🧠 | [RPP](./reference-photography-protocol.md) |
| Focal consistency | flag > 10–15% disagreement with EXIF or same-lens photos | 🧠 | [BA](./blenderartists-forum.md) |
| Conflicting pin | > 3σ after convergence | 🧠 | [YT](./youtube-likeness-blender.md) |
| Paintover edit | reject if another view's RMS rises > 0.5% IOD | 🧠 | [PC](./polycount-likeness.md) |
| Likeness lint | flag only \|model − photo\| > 2σ_photo, or population \|z\| > 2.5 where no photo sees the feature | 🧠 | [LM](./likeness-mistakes.md), [PC](./polycount-likeness.md) |
| Over-symmetry | mirror RMSD < 0.3 mm when the photos show asymmetry | 🧠 | [LM](./likeness-mistakes.md) |
| Scan wrap | face distance median < 0.3, RMS < 0.5, p95 < 1.5 mm; area ratio 0.2–5, no flipped faces; minimum angle > 10–15° | 🧠 | [SCW](./scan-cleanup-wrapping.md) |
| Automatic template registration (reference) | 53.1% of landmarks < 2 mm, 84.4% < 4 mm | 📄 | [SCW](./scan-cleanup-wrapping.md) |
| Scan modality accuracy | stereophotogrammetry ≈0.2 mm mean against calipers, most < 2 mm ✅; a mobile scanner ≈1 mm 📄 | ✅ 📄 | [SCW](./scan-cleanup-wrapping.md) |
| Retopology and bake tolerance | lid margins, vermilion, alar rim 0.2–0.3 mm; nose tip, ear rims, chin 0.5 mm; cheeks, forehead 1.0 mm; back of head, neck 1.5–2 mm | 🧠 | [PC](./polycount-likeness.md) |
| Synthetic solver harness | focal error < 5%, rotation error < 2° when the views span ≥60° of yaw | 🧠 | [AWL](./awesome-lists-resources.md) |

### Q9. Diagnostic checks

| Check | Default | Badge | Notes |
|---|---|---|---|
| Flip | background image "Flip Horizontally" plus a flipped render; head Scale X = −1 is valid only near frontal | 🧠 | [LM](./likeness-mistakes.md), [ZB](./zbrush-to-blender-likeness.md) |
| Squint / blur | Gaussian σ ≈ 3–5% of face width, applied to photo and render | 🧠 | [LM](./likeness-mistakes.md), [TR](./traditional-portrait-sculpture.md) |
| Thumbnail | face 48–64 px wide (LM); 64–128 px (TR); 100–150 px face height (YT) | 🧠 | [LM](./likeness-mistakes.md), [TR](./traditional-portrait-sculpture.md), [YT](./youtube-likeness-blender.md) |
| Overlay | camera background image, Depth Front, opacity 0.3–0.5 (0.4 in ZB) | 🧠 | [LM](./likeness-mistakes.md), [ZB](./zbrush-to-blender-likeness.md) |
| Blink | toggle photo and render at 2–3 Hz (≈1–2 Hz in IG) with `bpy.app.timers` | 🧠 | [LM](./likeness-mistakes.md), [IG](./instagram-social-sculptors.md) |
| Silhouette | Workbench: Flat lighting, Single colour black, white background, through the solved camera | 🧠 | [LM](./likeness-mistakes.md), [TR](./traditional-portrait-sculpture.md) |
| Single key light | one area light at the photo's key direction, ≈30–45° up and to the side | 🧠 | [TR](./traditional-portrait-sculpture.md), [PC](./polycount-likeness.md) |
| Grayscale | desaturated photo copy; AgX "Greyscale" look if present | 🧠 (time-sensitive) | [LM](./likeness-mistakes.md) |
| Held-out photos | ≥2 photos the solver and sculptor never use | 🧠 | [LM](./likeness-mistakes.md), [TR](./traditional-portrait-sculpture.md) |
| Texture review | judge shape ≥20–30° away from the projecting camera | 🧠 | [LM](./likeness-mistakes.md), [AS](./artstation-likeness.md) |
| Upside-down | judges spacing only; always pair with an upright check | ↔️ | [LM](./likeness-mistakes.md) |
| Familiar viewer | show the sitter both orientations (sitters prefer the mirror image, friends the true one) | ↔️ | [LM](./likeness-mistakes.md), [PC](./polycount-likeness.md) |

### Q10. Scan cleanup and wrap ([SCW](./scan-cleanup-wrapping.md), all 🧠 design defaults)

| Stage | Regulariser radius / stiffness α | Landmark weight β | Max correspondence | Normal gate |
|---|---|---|---|---|
| Rigid (Umeyama) | — | point pairs only | — | — |
| Thin-plate spline | λ chosen so the landmark residual ≈ σ_lm | — | — | — |
| NICP 1 | 15–20 mm / 100 | 1.0 | 10 mm | 60° |
| NICP 2 | 8–10 mm / 20–50 | 0.5 | 8 mm | 60° |
| NICP 3 | 4–5 mm / 5–10 | 0.2 | 5 mm | 45° |
| NICP 4 | per vertex / 1–2 | 0.05 | 3 mm | 45° |
| Snap and relax | tangential only | frozen | ray 1–2 mm | 45° |

Region weights: face 1.0; lid margins 0.5; vermilion 1.0 (after a stomion cut); ears 0.3–0.5 (backs 0); eyeballs, mouth and nostril interiors 0; scalp 0.1 and beard 0.2–0.5, both one-sided, with an inward prior of 5–15 mm (1–3 mm if the hair is capped); a 2–3 mm scan-boundary band 0. Scan noise is ≈0.05–0.3 mm against likeness forms ≥2 mm, so denoise at radius ≤1 mm only, with lids, lips, alae and nasolabial fold masked. Eyeballs are replaced by ≈12 mm-radius spheres before wrapping. For AI meshes, non-rigid ICP stiffness anneals from about 50 to 1 over 5–8 steps, rejecting pairs >10 mm apart or with normals >45° apart ([AI](./ai-assisted-sculpting.md), 🧠).

### Q11. Blender settings for likeness work

| Setting | For likeness work | Badge | Notes |
|---|---|---|---|
| Units | Metric, scale 1.0, display in mm | 🧠 | [ZB](./zbrush-to-blender-likeness.md) |
| View clip start | 1–10 mm (0.001 m) | 🧠 | [ZB](./zbrush-to-blender-likeness.md), [YT](./youtube-likeness-blender.md) |
| Render resolution | exactly the photo's pixels, from the original uncropped file (default 1920×1080 is wrong) | 🧠 | [YT](./youtube-likeness-blender.md), [BA](./blenderartists-forum.md) |
| Camera | one per photo; lens from EXIF or the solver; Shift X/Y for an off-centre principal point; transforms locked; Lock Camera to View off | 🧠 | [YT](./youtube-likeness-blender.md), [AS](./artstation-likeness.md) |
| Background image | Depth Front, opacity 0.3–0.5, Frame Method Stretch | 🧠 | [YT](./youtube-likeness-blender.md), [ZB](./zbrush-to-blender-likeness.md) |
| Stepping through views | Timeline › Marker › Bind Camera to Markers (Ctrl+B) | 🧠 | [ZB](./zbrush-to-blender-likeness.md), [PC](./polycount-likeness.md) |
| Viewport focal length | 85–100 mm for free sculpting (default 50 mm); judge only through solved cameras | 🧠 (150–200 mm advice ↔️) | [LM](./likeness-mistakes.md), [YT](./youtube-likeness-blender.md), [ZB](./zbrush-to-blender-likeness.md) |
| Brush Radius Unit | Scene, so strokes are in mm | 🧠 | [IG](./instagram-social-sculptors.md), [YT](./youtube-likeness-blender.md) |
| Voxel remesh | blockout 2–5 mm, primaries 1–2 mm, refine 0.5–1 mm | 🧠 ↔️ | [ZB](./zbrush-to-blender-likeness.md), [YT](./youtube-likeness-blender.md), [IG](./instagram-social-sculptors.md) |
| Multires base | 2–10k (ZB) or 5–20k quads (RD, AS); likeness at L0–L2 | 🧠 | [ZB](./zbrush-to-blender-likeness.md), [RD](./reddit-face-from-photos.md), [AS](./artstation-likeness.md) |
| Eyes | separate 24 mm spheres | 🧠 | [YT](./youtube-likeness-blender.md) |
| Fitted base | never Dyntopo or remesh it (both destroy UVs and blendshapes); sculpt on Multires | 🧠 | [YT](./youtube-likeness-blender.md) |
| A/B experiments | shape keys; slider max above 1 to exaggerate; native sculpt layers had not shipped | ↔️ (time-sensitive) | [ZB](./zbrush-to-blender-likeness.md) |
| Detail from a scan | Multires Reshape level by level, or Bake from Multires (both in the 5.3 manual) | 📄 | [SCW](./scan-cleanup-wrapping.md) |
| Bakes | Emit trick for colour, Save as Render off; normal maps OpenGL +Y (flip green for Unreal); displacement in 32-bit EXR, mid-level 0; 16 px margin at 4K | 🧠 | [SCW](./scan-cleanup-wrapping.md) |
| Scale traps | MetaHuman and CC export in cm, Blender works in m (×100) | 🧠 | [YT](./youtube-likeness-blender.md) |
| Version drift | 5.3 current, 5.2 LTS; brushes are assets since 4.3; extensions since 4.2 | 🧠 | [YT](./youtube-likeness-blender.md) |

### Q12. Mesh density and detail scale

| Level on a ≈10k-quad base | Faces | Mean edge | Enough for | Badge |
|---|---|---|---|---|
| L0 | 10k | ≈3.5–3.6 mm | primary forms; likeness shape key | 🧠 |
| L1 | 40k | 1.8 mm | placement; AI-mesh detail at 256³ | 🧠 |
| L2 | 160k | ≈0.87–0.9 mm | lid creases, alar groove | 🧠 |
| L3 | 640k | ≈0.43–0.45 mm | fine wrinkles; likeness complete | 🧠 |
| L4–L5 | 2.6–10.5M | ≈0.22–0.11 mm | pores (or use maps) | 🧠 |

Sources: [SCW](./scan-cleanup-wrapping.md), [AI](./ai-assisted-sculpting.md). Polycount's ladder from a 2k-quad base ([PC](./polycount-likeness.md)): L0 cranium, face height, jaw, neck; L1 orbits, nose mass, mouth barrel, ear position; L2 lids, alae, vermilion border, helix; L3 soft tissue and age; L4 wrinkles; L5–6 pores. Texel spacing at 70% UV packing: 2K 0.20, 4K 0.10, 8K 0.05 mm, so 4K already matches a scan's 0.05–0.1 mm resolution ([SCW](./scan-cleanup-wrapping.md)). An AI generator's 256³ grid on a 0.25 m head box gives ≈0.98 mm voxels (smallest feature ≈2 mm), against likeness relief of ≈0.5–5 mm; a full-body input image leaves the face ≈37 px wide ([AI](./ai-assisted-sculpting.md)). All 🧠 arithmetic.

### Q13. Landmark schemes and base meshes

| Scheme or mesh | Size | Notes | Badge |
|---|---|---|---|
| iBUG 300-W / dlib | 68 2D points | 17 jaw points slide along the contour | 🧠 |
| WFLW | 98 2D points | ≈10,000 images | 🧠 |
| AFLW2000-3D | 68 3D points | 2,000 images; fitted, not scanned, ground truth | 🧠 |
| MediaPipe Face Mesh | 468 points; 478 with irises | Apache-2.0, CPU | 🧠 |
| ARKit face | 1,220 vertices; 52 blendshapes | Apple devices only | 🧠 |
| FLAME | 5,023 vertices (9,976 tris); 300 shape + 100 expression components; landmark embedding 51 static + 17 dynamic | barycentric embedding | 🧠 (counts) |
| Basel Face Model 2009 | 53,490 vertices; 199 components; 200 adults | mostly European | 🧠 |
| MakeHuman hm08 (MPFB2) | ≈13,380 body vertices (≈19,158 with helpers) | targets and sliders | 🧠 |
| Dense landmarks (Wood et al. 2022) | ≈700 | weights believed not public | ↔️ |
| FaceBuilder output | ≈51 ARKit-style keys | fixed KeenTools topology | ↔️ |
| Raw photogrammetry head | 1–20M triangles | bake source only | 🧠 |
| Sculpt-ready base | 5–20k quads | Multires | 🧠 |

Sources: [AWL](./awesome-lists-resources.md), [BA](./blenderartists-forum.md), [RD](./reddit-face-from-photos.md), [YT](./youtube-likeness-blender.md), [SCW](./scan-cleanup-wrapping.md).

### Q14. Licence quick reference (re-verify every release)

| Asset or tool | Terms | Ship in an add-on? | Badge | Notes |
|---|---|---|---|---|
| FLAME 2023 Open | CC BY 4.0 (texture model BY-NC-SA 4.0) | shape model with attribution | 📄 | [AWL](./awesome-lists-resources.md), [BA](./blenderartists-forum.md) |
| FLAME 2017/2019/2020, FLAME Blender add-on | non-commercial research, education or art | no; load from a user-supplied path | 📄 | [BA](./blenderartists-forum.md) |
| BFM 2009/2017, LSFM, FaceScape, NeRSemble, Ava-256 | non-commercial or on request | no | 🧠 ↔️ | [AWL](./awesome-lists-resources.md) |
| ICT-FaceKit | MIT unverified; the lab says to contact it for commercial use | not until verified | ↔️ | [AWL](./awesome-lists-resources.md) |
| MPFB2 / MakeHuman | GPL code; assets CC0 (AWL) or CC0/CC-BY disputed (BA) | verify first | ↔️ | [AWL](./awesome-lists-resources.md), [BA](./blenderartists-forum.md) |
| Blender Studio Human Base Meshes | CC0 | yes | ✅ | [YT](./youtube-likeness-blender.md) |
| dlib 68-point model; InsightFace weights | permissive code, non-commercial training data or weights | no | 🧠 | [AWL](./awesome-lists-resources.md) |
| MediaPipe (Apache-2.0), 3DDFA_V2 (MIT), face-alignment (BSD-3), eos (Apache-2.0) | permissive | yes, after checking | 🧠 | [AWL](./awesome-lists-resources.md) |
| MetaHuman | free; Unreal Engine EULA; use outside Unreal, including Blender, since June 2025 | no | ✅ | [AWL](./awesome-lists-resources.md), [RD](./reddit-face-from-photos.md) |
| Z-Anatomy | CC BY-SA 4.0; some bundled models CC BY-NC(-SA) | with attribution, minus NC parts | 📄 | [AWL](./awesome-lists-resources.md) |
| BodyParts3D | CC BY-SA 2.1 Japan or CC BY 4.0 | check | ↔️ | [AWL](./awesome-lists-resources.md) |
| Smithsonian Open Access 3D (Lincoln life masks) | CC0 | yes (test surfaces) | 🧠 | [AWL](./awesome-lists-resources.md) |
| Lee Perry-Smith head | believed CC BY 3.0 | probably, with attribution | ↔️ | [AWL](./awesome-lists-resources.md) |
| 3D Scan Store, Triplegangers, Texturing.XYZ, 3d.sk, Anatomy 360 | paid, per asset | no | 🧠 | [AWL](./awesome-lists-resources.md) |
| Complete Anatomy | EULA forbids extracting meshes | no | 🧠 | [AWL](./awesome-lists-resources.md) |
| Asaro head; Peck, Goldfinger, Spencer, Zarins, Faigin | in copyright | cite only; author your own plane regions | 🧠 | [AAB](./art-anatomy-books.md) |
| Bridgman 1920 and 1924; Loomis, Bridgman 1932 | US public domain; renewal-dependent | yes; check | 🧠; ↔️ | [AAB](./art-anatomy-books.md) |
| Hunyuan3D 2.x | Tencent community licence; excludes EU, UK, South Korea; 1M MAU cap | no | 📄 | [AI](./ai-assisted-sculpting.md) |
| TRELLIS, TRELLIS.2 | MIT code and weights; some NVIDIA dependencies non-commercial | check dependencies | 📄 | [AI](./ai-assisted-sculpting.md) |
| Meshy; Tripo | Meshy free-plan outputs CC BY 4.0, paid private; Tripo unverified | user's choice | 📄; ↔️ | [AI](./ai-assisted-sculpting.md) |
| KeenTools FaceBuilder | subscription, 15-day trial per add-on; EULA on exported heads not read | — | 📄 | [YT](./youtube-likeness-blender.md), [BA](./blenderartists-forum.md) |
| Faceform (R3DS) Wrap / ZWrap | perpetual + maintenance (2024.11: Indie ≈$570, Pro ≈$1,070 node-locked); ZWrap annual subscription | — | ✅ / 📄 | [SCW](./scan-cleanup-wrapping.md) |
| Sketchfab downloads | a Download button is not a commercial licence | read the licence field | 🧠 | [AWL](./awesome-lists-resources.md) |

### Q15. Routes from photos to a head (practitioner estimates, [YT](./youtube-likeness-blender.md))

| Route | Photos | Hands-on time | Likeness ceiling | Main failure | Badge |
|---|---|---|---|---|---|
| FaceBuilder pin fit, then sculpt | 3–9 | 0.5–2 h fit; 5–20 h sculpt | good front and 3/4; profile only as good as profile pins | over-pinning, wrong focal, expression absorbed | ↔️ |
| Ortho image planes and box modelling | 2 | 4–15 h | poor unless shot from ≥2 m with a tele lens | perspective mismatch | 🧠 |
| Sculpt by eye from a sphere or base mesh | 10–50 references | 10–60 h | high for experts, low for beginners | proportion drift, symmetry, eye depth | ↔️ |
| Photogrammetry, then cleanup and wrap | 50–150 | 1–3 h capture; 3–10 h cleanup | best metric shape (mid-face 0.5–2 mm) | motion, hair, eyes, shine | ↔️ |
| AI image-to-3D | 1–4 | minutes | blockout only | hallucinated profile, averaged features | ↔️ |
| MetaHuman or Headshot bridge | 1–9, or a mesh | 1–3 h | the input mesh, minus conform drift | drift at nose, lips, lids | ↔️ |

## Practical checklist for an artist working in Blender

**Before the shoot**
- [ ] Written consent for capture, storage, processing and deletion ([RPP](./reference-photography-protocol.md)).
- [ ] Space: a stool without backrest or swivel; a matte mid-grey backdrop ≥1 m behind; a 1.75 m floor circle marked every 45°; tripod at eye–nose height; a gaze mark on the wall ([RPP](./reference-photography-protocol.md)).
- [ ] Camera: 85–135 mm equivalent, or one locked physical 2–5× phone lens (never the front or ultra-wide camera). Portrait, beauty, mirror and night modes off. Manual exposure, white balance and focus; f/8 full frame; ≥1/250 s handheld; originals with EXIF kept ([RPP](./reference-photography-protocol.md)).
- [ ] Sitter: hair off ears and hairline (log any cap), glasses off 10–15 min early, matte powder, neutral face with a consistent teeth position, eyes on the gaze mark ([RPP](./reference-photography-protocol.md)).
- [ ] Measurements, with consent: PD and calipers (t–t; t–n, t–sn, t–gn on both sides; n–gn, ex–ex, sn–prn); an ID-1 card in ≥2 views ([TR](./traditional-portrait-sculpture.md), [RPP](./reference-photography-protocol.md)).
- [ ] Shoot the 7–9 core views in bursts of 3, check each at 100%, then a form-light set and hair-down front and 3/4 ([RPP](./reference-photography-protocol.md)).

**Ingest**
- [ ] Leave the originals untouched. Make working copies with EXIF orientation baked in and HEIC converted to PNG; record any crop ([RPP](./reference-photography-protocol.md)).
- [ ] Quarantine filtered or re-uploaded images, mirrored selfies (check a hair parting or mole), smiles (keep for expression only), photos from other years, and anything shot from under ≈0.6–1 m ([RD](./reddit-face-from-photos.md), [YT](./youtube-likeness-blender.md)).
- [ ] Hold back at least 2 photos that you will never sculpt against ([LM](./likeness-mistakes.md)).

**Scene and cameras**
- [ ] Metric units, scale 1.0, display in mm; head at the origin in a Frankfort-horizontal, midline-centred frame; clip start 1 mm ([ZB](./zbrush-to-blender-likeness.md), [TR](./traditional-portrait-sculpture.md)).
- [ ] One camera per photo: render resolution equal to the photo's pixels; lens from EXIF (35 mm-equivalent converted on the diagonal) or from the solver; Shift X/Y for a cropped principal point; the photo as Background Image (Depth Front, opacity 0.3–0.5, Stretch); transforms locked; cameras bound to markers ([BA](./blenderartists-forum.md), [YT](./youtube-likeness-blender.md)).
- [ ] Sanity-check the solve: front yaw and roll < 2°, profiles at 85–95°, solved distance within 10% of the tape, same-lens focals within 10–15% ([RPP](./reference-photography-protocol.md), [BA](./blenderartists-forum.md)).
- [ ] FaceBuilder users: 6–12 confident pins per view, no jaw-contour pins in the front view; delete pins rather than add them when they fight ([YT](./youtube-likeness-blender.md)).

**Blockout (Multires L0–L1, or voxel 2–5 mm)**
- [ ] Proxies first: 24 mm eye spheres, a dental-arch proxy, and hair and beard volumes as separate objects ([PC](./polycount-likeness.md)).
- [ ] Profile silhouette first, then front widths, then the 3/4 jaw and cheek contour, using large Grab or Elastic strokes with symmetry X on. Move cameras, never the mesh ([ZB](./zbrush-to-blender-likeness.md), [YT](./youtube-likeness-blender.md)).
- [ ] Cycle every camera every few strokes and compare flat black silhouettes per camera ([TR](./traditional-portrait-sculpture.md)).
- [ ] Leave lids and lips alone until the outer contours agree in every camera ([TR](./traditional-portrait-sculpture.md)).

**Features**
- [ ] Eyes: check the cornea against the lateral orbital rim from above; match MRD1 and the lower-lid level to the front photo; give the lid margins thickness ([LM](./likeness-mistakes.md)).
- [ ] Nose: set projection and nasolabial angle in the profile camera before width; take al–al only from photos shot at ≥1 m ([LM](./likeness-mistakes.md)).
- [ ] Mouth: take the width from the neutral front photo; the barrel must wrap the dental arch, so in 3/4 the far half foreshortens strongly ([LM](./likeness-mistakes.md)).
- [ ] Ears: only after pitch is solved. Put the tragion on the Frankfort plane, tilt the axis back, and check protrusion from the front and from above ([LM](./likeness-mistakes.md)).
- [ ] Symmetry off once the primaries match; re-add asymmetry only where ≥2 solved views agree, never from one tilted photo ([LM](./likeness-mistakes.md), [PC](./polycount-likeness.md)).

**Checks on every pass, big to small** ([LM](./likeness-mistakes.md))
- [ ] Profile and 3/4 silhouettes → 64 px thumbnail → overlay at 50% or Difference in every camera → blink → ratio panel (en–ex, en–en, al–al, ch–ch, n–sn …) → flip → grayscale under one area light at the photo's key direction → held-out photos → a familiar viewer, shown both orientations.
- [ ] Texture projection off for shape review; judge from ≥20–30° away from the projecting camera ([LM](./likeness-mistakes.md), [AS](./artstation-likeness.md)).
- [ ] Proxy brows and hairline (hair curves or cards) in place before any likeness verdict ([AS](./artstation-likeness.md), [PC](./polycount-likeness.md)).

**Finishing and export**
- [ ] Record experiments and sitter feedback as shape keys, so approval edits stay reversible ([ZB](./zbrush-to-blender-likeness.md), [PC](./polycount-likeness.md)).
- [ ] Never Dyntopo or remesh the fitted base ([YT](./youtube-likeness-blender.md)).
- [ ] If you retopologise or bake, colour sculpt-to-low distance (Geometry Nodes, Geometry Proximity) against the Q8 tolerances ([PC](./polycount-likeness.md)).
- [ ] Colour bakes with Save as Render off; normal maps OpenGL, with green flipped for Unreal ([SCW](./scan-cleanup-wrapping.md)).
- [ ] Physical output: scale for material shrink (fired clay ≈8–15%, lost-wax bronze ≈1–3%) and record it in the metadata ([TR](./traditional-portrait-sculpture.md)).
- [ ] Record a licence and provenance entry for every asset, and the sitter's sign-off ([AWL](./awesome-lists-resources.md), [PC](./polycount-likeness.md)).

## Cross-topic contradictions and how to resolve them

| # | Topic | Positions | Resolution |
|---|---|---|---|
| 1 | IPD prior σ | 3.5 mm (LM, RD, BA, YT, AI); 3.7 mm (ZB); 4 mm (IG). Range 54–74 mm (IG) against 50–75 mm (secondary sources, BA log) | Mean 63 mm. Use σ 3.5 mm, widening to 4 mm when sex is unknown, and keep it provisional (SD unconfirmed). Any measurement (PD, caliper, card) overrides it at σ ≈1 mm. |
| 2 | Iris as a scale cue | 11.7 ± 0.5 mm (LM, YT, IG) against device means 11.77–12.40 mm (IG log; IG suggests N(12.0, 0.5)) | Use the iris only as a secondary scale cue, only when it is ≥20 px, at 11.7–12.0 ± 0.5 mm. Prefer IPD or a measurement. Keep 11.7 mm for the inserted eye model. |
| 3 | MRD1 prior | 4.5 ± 1 mm (LM data table) against sources giving 3.5–4.5 mm (LM and PC logs) | Centre near 4.0 mm with σ 1 mm; it falls with age. Photo evidence always wins. |
| 4 | Hertel prior | 16 ± 2.5 (LM), N(16, 2) (IG), 15–17 mm (IG table), "higher in African-descent samples" (LM) | A weak prior of 16 ± 2.5 mm, widened when ancestry is outside the reference population. Profile and top views override it. The "higher in African-descent" claim depends on the sample (LM log). |
| 5 | Focal σ when EXIF exists | 0.02 (AS), 0.03 (ZB, YT), 0.05 (RD), 0.05–0.10 (BA) | Decide by provenance: an uncropped original with consistent LensModel gets 0.03 plus a lens-group tie of 0.02; a possible crop or digital zoom gets 0.05–0.10. |
| 6 | Focal prior without EXIF | 50 mm σ_log 0.6 (RD, ZB) or 0.5 (YT); engine default 0.35 (BA, IG); phone 26 mm σ 0.25 (RD) against 0.6 (AS) | Use the source-typed priors (Q5) when the source is known. Otherwise 50 mm at σ_log 0.6: at 0.35, a 26 mm phone lens sits ≈1.9σ from a 50 mm median. |
| 7 | Close photos | Warn below 0.8 m but keep, because it is informative (RD, BA, PC); warn below 1.0 m and refuse as a shape cue below 0.6 m (IG, YT); AI depth ×0.25 when f₃₅ < 35 mm (AI) | Tiered: warn below 1.0 m; below 0.8 m down-weight depth-sensitive landmarks unless focal is pinned by EXIF and multi-view; below 0.6 m use for texture and 2D cues by default, with a user override. |
| 8 | Symmetry schedule | engine 2.0 mm; 1 → 2 → 4 mm (PC); 0.5 → 2–3 mm (ZB); 1 → ≥2 mm (IG, YT); ≥3–5 mm for scan wraps (SCW); timing contested everywhere | A stage-dependent schedule: about 1 mm for masses, 2 mm for features, 3–4 mm for surface. Keep a strong pull only in unobserved regions; never symmetrise the output shape. |
| 9 | User-pin σ | 0.01 × IOD (RD); 0.75% IOD (YT); 1–2 screen px at the current zoom (BA) | Use BA's zoom-aware screen-pixel rule, floored at about 0.75% IOD, so a pin placed at low zoom is not treated as near-hard. |
| 10 | Auto-pin σ | 1.5 / 2.5 / 4% IOD (YT) against 2–3% interior and 5–8% contour (RD, BA, AS) | The YT values describe reviewed, vendor-style pins. Raw detector output uses the RD and BA values. |
| 11 | Caricature or distinctiveness | α 0.8–1.4 with 1.1–1.3 to try (LM); k 0–0.15, i.e. α 1.0–1.15 (IG); 0.9–1.2 (ZB); ×2 weight on tagged regions (PC); unmeasured in 3D | Default 1.0. Offer it as an opt-in preview shape key and record it in metadata; never apply it automatically. PC's "caricature handles" protect features from shrinkage without exaggerating them, the safer default. |
| 12 | Viewport lens | 85–100 mm (LM, YT) against 150–200 mm because the viewport may use a doubled sensor (ZB ↔️; tracker reports disagree) | Judge likeness only through solved cameras. 85–100 mm is safe for free sculpting either way. |
| 13 | Blender camera export | sensor fit HORIZONTAL with lens and shift normalised by width (BA, engine `to_blender_camera`); AUTO with max(W, H) (YT); a HORIZONTAL lens with max(W, H) shift (ZB) | Each pure convention is self-consistent, but mixing them breaks portrait photos. Follow the engine (HORIZONTAL, width) and unit-test by reprojecting a known landmark. The max(W, H) normalisation found no source in verification (ZB log). |
| 14 | 35 mm-equivalent conversion | diagonal 43.27 mm (CIPA; BA; engine `focal_px_from_35mm`) against width-based formulas | Use the diagonal. A width-based conversion is ≈4% short on 4:3 images. Per-maker practice is unverified, so flag > 10–15% disagreement. |
| 15 | Selfie-effect baseline | 5 ft (Rutgers) against orthographic (HealthDay); 30% "nasal width" in early drafts | Quote it as ≈30% wider nasal base and ≈7% wider tip at 12 in against 5 ft; use the pinhole table for computation. |
| 16 | Teeth and gaze | teeth lightly together (IG, ZB, AS) against no consensus (RPP); eyes on the lens (BA) against a fixed mark (RPP, RD) | Either teeth position, as long as it is identical in every shot and logged. Gaze on a fixed mark while the camera moves; some put the eyes on the lens for the front view only. |
| 17 | How many photos | 3–9 (YT), 5–9 (BA), 7–9 core and 15–20 extended (RPP), 8 minimum and 12–16 preferred (IG), 8–20 (ZB), 20–50+ (PC), 30–300 collected with 5–15 heroes (AS) | Different situations. A controlled shoot of a consenting sitter uses the RPP set. Existing photos need curating many and solving 5–15 heroes. Weight by 1/(views per 15° bin) either way. |
| 18 | Orthographic threshold | wrong closer than ≈2 m (BA); ≥3 m (TR, YT); ≥5 m with ≥200 mm (RPP) | Orthographic only from ≥3 m (≤3.3% excess). 2 m (5%) is tolerable for blocking only. |
| 19 | Voxel remesh size | 2–3 / 0.5–1 mm (ZB); 3–5 / 1.5–2 mm (YT); 1–2 mm (IG); 0.5–1 mm proxy (AI) | Blockout 2–5 mm, primaries 1–2 mm, refinement and proxies 0.5–1 mm, always at real scale. |
| 20 | Is Shrinkwrap or Surface Deform a wrap? | listed as wrap tools (RD, AI) against "a final snap only; Surface Deform does not fit" (SCW) | Follow SCW, which is backed by the NICP literature (✅ on annealing): landmarks, then TPS, then annealed NICP, then a Shrinkwrap snap. Surface Deform only passes on later deformation. |
| 21 | Starting point | a licensed scan wrapped to clean topology (AS, PC) against "never use a scan as the base; it pulls the likeness toward the scanned person" (AWL); sphere against base mesh (YT, PC) | In this project the base is the photo-fitted template. Scans of other people are side-by-side references or a weak prior (σ 3–5 mm), never the base. |
| 22 | FLAME licence | "mostly non-commercial" (RD) against corrected per-release terms (AWL, BA) | Per release: only FLAME 2023 Open (CC BY 4.0, texture model excluded) may enter a commercial path. |
| 23 | MPFB2/MakeHuman asset licence | CC0 (AWL) against CC0 or CC-BY disputed (BA) | Unresolved: verify before making it the default template. Blender Studio Human Base Meshes are the verified CC0 alternative (YT ✅). |
| 24 | FaceBuilder and Blender 5.x | "5.x support unconfirmed" (YT) against 5.0 supported since KeenTools 2025.3 (BA, sourced) | Follow BA's sourced claim. Price and EULA on exported heads remain unconfirmed. |
| 25 | TRELLIS licence | MIT (RD, 🧠) against MIT with non-commercial NVIDIA dependencies (AI, 📄) | Follow AI. |
| 26 | Date window | warn when dates span > 18 months (RD); age window ≤2–3 years (AS); one session (RPP) | Controlled capture: one session. Curated photos: warn above 18 months. |
| 27 | Thumbnail and blink settings | 48–64 / 64–128 px / 100–150 px face height; 2–3 Hz against 1–2 Hz | Cosmetic. Render 64 px and 128 px thumbnails; make the blink rate adjustable, defaulting to 2–3 Hz. |
| 28 | When to drop symmetry; neutral or characteristic expression | contested in LM, IG, PC, ZB, YT, AS, TR | Engine: fit neutral identity with a symmetry schedule; offer an optional "characteristic expression" key (0–1, default 0). The artist decides the timing. |

## Index of topic notes

| Note | Covers | ✅ / 📄 / 🧠 / ↔️ |
|---|---|---|
| [likeness-mistakes](./likeness-mistakes.md) (LM) | The predictable likeness errors (eyes, nose, mouth, ears, cranium, symmetry), their perceptual causes, proportion checks, pose-error arithmetic, and each studio check with its engine counterpart. | 0 / 1 / 46 / 17 |
| [reference-photography-protocol](./reference-photography-protocol.md) (RPP) | How to shoot a consenting sitter: distance, lens, height, aperture, shot list, sitter prep, light, phones, video, capture manifest and quality gates. | 0 / 1 / 78 / 18 |
| [reddit-face-from-photos](./reddit-face-from-photos.md) (RD) | Reddit's four routes (template fit, photogrammetry, sculpt by eye, AI), the recurring input defects, perspective tables and suggested fitting priors. | 1 / 1 / 57 / 8 |
| [instagram-social-sculptors](./instagram-social-sculptors.md) (IG) | Social-media sculptors' recurring process rules (big to small, profiles, fresh-eye checks, calipers), scale anchors, canons against measurement. Sourced part is only five profile bios. | 0 / 5 / 49 / 16 |
| [polycount-likeness](./polycount-likeness.md) (PC) | Game-art critique culture: verdict → measurable check, subdivision ladder, stage gates, paintover ingestion, export likeness tolerances. | 0 / 0 / 60 / 25 |
| [zbrush-to-blender-likeness](./zbrush-to-blender-likeness.md) (ZB) | The ZBrush likeness loop (Spotlight, Layers, whack-a-mole) translated to Blender cameras, shape keys and Multires; FOV tables and fitting priors. | 0 / 1 / 59 / 21 |
| [youtube-likeness-blender](./youtube-likeness-blender.md) (YT) | The five YouTube routes, FaceBuilder practice and pin plan, what tutorials omit, Blender defaults against likeness settings, camera export contract. | 1 / 2 / 61 / 19 |
| [artstation-likeness](./artstation-likeness.md) (AS) | Portfolio likeness breakdowns: reference curation by source type, focal priors per source, brows and hair as identity, timelines, breakdown-sheet generator. | 2 / 0 / 57 / 26 |
| [traditional-portrait-sculpture](./traditional-portrait-sculpture.md) (TR) | Clay portraiture: caliper sets from the ear hole, contour "profiles", pointing machine and photosculpture as algorithms, landmark tiers, material shrink. | 0 / 0 / 86 / 24 |
| [art-anatomy-books](./art-anatomy-books.md) (AAB) | Loomis, Reilly, Asaro, Bridgman, Peck, Spencer and Zarins; canons tested against anthropometry; weak canon priors; plane regions; copyright status. | 5 / 21 / 54 / 17 |
| [scan-cleanup-wrapping](./scan-cleanup-wrapping.md) (SCW) | Raw scan → fitting target → wrapped template: cleaning order, the Wrap recipe, NICP schedule, region weights, Blender natives ranked, baking, acceptance checks. | 5 / 13 / 51 / 8 |
| [awesome-lists-resources](./awesome-lists-resources.md) (AWL) | What awesome lists omit, the upstream face models and datasets and their licences, landmark schemes, anatomy atlases, scan stores, asset registry and test harness. | 2 / 3 / 75 / 22 |
| [ai-assisted-sculpting](./ai-assisted-sculpting.md) (AI) | Practitioner verdicts on Hunyuan3D, TRELLIS, Rodin, Meshy, Tripo and face fitters; licences; extraction-grid arithmetic; AI output as a region-weighted weak prior. | 0 / 6 / 47 / 20 |
| [blenderartists-forum](./blenderartists-forum.md) (BA) | FaceBuilder release threads (auto-pins are a draft, per-photo focal, neutral fits better), BA critique habits, 35 mm-equivalent conventions, solver defaults. | 3 / 9 / 44 / 9 |

## Gaps across the area

- **Few sources were harvested.** Twelve of the 14 notes started without a harvest. No Reddit, Polycount, YouTube or ArtStation thread or video was harvested, and Instagram yielded only five profile bios. Attributions to named artists are unverified throughout.
- **No quantitative likeness tolerance.** Nothing ties millimetre or reprojection error to recognition by people who know the sitter; the 1–2 mm working target is a heuristic ([ZB](./zbrush-to-blender-likeness.md)).
- **No benchmark of consumer tools against ground-truth scans**, whether FaceBuilder, Headshot, AI generators or manual workflows ([RD](./reddit-face-from-photos.md), [AI](./ai-assisted-sculpting.md)).
- **No calibration of the σ values.** Landmark, symmetry, AI and canon σ values, the 25% AI-information cap and the stage gates are all unvalidated engineering guesses.
- **Anthropometric ranges are mostly European-derived and partly unconfirmed:** IPD SD, tragion depths, head length, neck circumference, scalp thickness, vermilion heights, E-line distances.
- **Facts that go stale within months:** tool prices and versions, licences, Blender UI details and platform status (Fab against ArtStation Marketplace, Papers with Code, CGSociety).
