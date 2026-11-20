# BlenderArtists forum knowledge on faces

> BlenderArtists (BA) is where KeenTools announced each FaceBuilder for Blender release, from the 2.8 beta to 2021.1 "now with AI". It also hosts single-photo generator add-ons and a beginner question that keeps coming back: how do I model my own face from photos? The harvested threads say three things. Neural auto-pins are only a first draft. Focal length and sensor size are estimated for each photo. Expressive photos work, but neutral photos fit better. No thread gives an accuracy figure. The rest of this note sets out expert knowledge of how BA models and critiques faces, turned into numbers a solver can use.
> Evidence status: 3 ✅ / 9 📄 / 44 🧠 / 9 ↔️ — 🧠 items remain unverified; 2026-11-20 verification pass corrected FLAME and KeenTools terms (see log).

## Key facts

**From harvested threads**
- KeenTools announced FaceBuilder for Blender on BA in separate threads for each milestone: the 2.8 beta, the first stable release, the "Revamped" version and 2021.1. That makes BA the primary record of what the vendor said at each release [1][2][3][4] ✅
- In 2021.1, "a couple of neural networks" find the face and set up all the pins (paraphrased from the search summary) [1] 📄
- The developers say these automatic pins are not always 100% accurate and sometimes need adjusting by hand. This is the vendor's own caveat [1] 📄
- In the "Revamped" thread, focal length and sensor size are set automatically for each photo [2] 📄
- Expressions are supported, so neutral photos are not required, but they are said to give better quality. Both statements come from the vendor, so the sources are not independent [1][2] 📄
- Users describe FaceBuilder as paid. Forum users mention a 30-day trial, but KeenTools states each Blender add-on has a 15-day free trial that starts when you first create a head [10][11] (corrected in verification). KeenTools 2025.3 (Dec 2025) added official Blender 5.0 support [12]. Current price not confirmed [1][4] 📄
- MetahumanModeler ("Released Add-ons and Extensions") builds a mesh with MetaHuman topology from one image. Its author says it was built from their understanding of FaceBuilder [5] 📄
- Single-photo character generators come up repeatedly (AutoFace, MetahumanModeler). Both threads exist, but no accuracy evidence was found [5][6] ✅
- Beginners keep asking how to model a face from photos, in threads whose IDs suggest roughly 2020 to 2025. The answers in those threads were not harvested [7][8][9] ✅
- **Thread order:** Discourse numbers topics in the order they are created, so "Revamped" (1245723) came before 2021.1 (1294243). I also recall the revamp coming out in 2020. That contradicts the harvester's phrase "later revamp" [1][2] ↔️

**BA community knowledge (expert synthesis, not harvested)**
- **Image planes.** The method taught most often on BA is to model over front and side photos placed on orthographic image planes. It is also the most common cause of "my front and side don't line up" threads. The photos are perspective projections, and the head tilts and turns slightly between shots, so the eye, nose and chin heights disagree 🧠
- **The usual fix:** shoot from farther away with a longer lens, keep the camera level at nose height, and align the views on stable landmarks (inner canthi, nose base, ear tops). Treat the photos as guides, not as ground truth 🧠
- **Critique etiquette.** Critics ask for the reference photo placed next to a render taken through a *matched* camera, with the same focal length, angle and distance. Comparing a 50 mm render with a phone selfie tells you nothing 🧠
- **Frequent likeness critiques**, roughly in order (a synthesis, not a count):
  - the back of the skull is too short, because hair hid the cranium in the photos
  - the eyes are set too far apart or too close, or the eyeballs are the wrong size
  - the eyelids have no thickness, or the upper lid covers too little of the iris
  - the lips are flat instead of wrapping around the dental arch
  - the alae are too narrow, or the nose tip projects too much or too little
  - the ears sit too low or too far forward
  - the neck is too thin
  - the face is perfectly symmetric, which makes it look like a mannequin 🧠
- **Tools discussed on BA:**
  - MPFB2/MakeHuman: targets and sliders, with no photo fitting
  - MB-Lab and CharMorph, descended from ManuelbastioniLAB
  - Human Generator, which is paid
  - the FLAME Blender add-on, which raises licence questions
  - photogrammetry tools (Meshroom, RealityCapture)
  - fSpy, which needs straight lines in the scene and so is a poor fit for faces 🧠
- **Selfie traps:** front cameras are about 22–30 mm-equivalent and are held at 0.3–0.6 m. A mirrored selfie flips the person's real asymmetry. Beauty or face-correction processing warps the geometry 🧠

## Numbers & reference tables

**A. How much larger the nose-tip plane looks than the ear (tragion) plane.** Pinhole geometry gives 1 + d/Z, where Z is the distance from camera to nose tip and d is the depth from nose tip to tragion. The table uses d = 10 cm, with the bracketed range for d = 9–12 cm.

| Camera → nose tip (m) | Typical setup | Relative magnification | Badge |
|---|---|---|---|
| 0.3 | close selfie | 1.33 (1.30–1.40) | 🧠 |
| 0.5 | arm's-length selfie | 1.20 (1.18–1.24) | 🧠 |
| 1.0 | phone 1× | 1.10 (1.09–1.12) | 🧠 |
| 1.5 | 85 mm-eq head-and-shoulders | 1.067 (1.06–1.08) | 🧠 |
| 2.0 | 2–3× phone tele | 1.05 (1.045–1.06) | 🧠 |
| 3.0 | 135–200 mm-eq | 1.033 (1.03–1.04) | 🧠 |
| 5.0 | long tele | 1.02 | 🧠 |

**B. Distance for a tight head-only frame, and the magnification that results.** The frame is 0.35 m tall, shot in portrait orientation with the 36 mm sensor side vertical. **Perspective depends on distance; focal length only sets the crop.**

| Focal (35 mm-eq) | Distance (m) | Nose/ear magnification | Badge |
|---|---|---|---|
| 24 mm | 0.23 | 1.43 | 🧠 |
| 50 mm | 0.49 | 1.21 | 🧠 |
| 85 mm | 0.83 | 1.12 | 🧠 |
| 135 mm | 1.31 | 1.08 | 🧠 |
| 200 mm | 1.94 | 1.05 | 🧠 |

**C. 35 mm-equivalent conventions.** Converting by width, f_px = f35·W/36, compared with converting by diagonal, f_px = f35·diag/43.27. The engine's `focal_px_from_35mm` uses the diagonal.

| Native aspect | Width-based ÷ diagonal f_px | Effect if wrong | Badge |
|---|---|---|---|
| 3:2 | 1.000 | none | 🧠 |
| 4:3 (most phones) | 0.962 | focal about 4% short, so the camera is solved too close and the face too deep | ↔️ manufacturers may differ; the CIPA definition is diagonal-based [15], per-maker practice unverified |
| 16:9 | 1.048 | focal about 5% long | ↔️ |

**D. Base meshes discussed in BA add-on threads.** These figures are from memory; verify them before hard-coding.

| Model | Vertices | Parameters | Licence note | Badge |
|---|---|---|---|---|
| FLAME (2017/2020) | 5,023 (9,976 tris) | 300 shape, 100 expression; jaw, neck and eye joints | FLAME 2017/2019/2020 and the Blender add-on: non-commercial research, education or art only; the FLAME 2023 Open release is CC-BY-4.0 and allows commercial use, but the texture model is BY-NC-SA 4.0 [13][14] (corrected in verification) | 📄 licence / 🧠 counts |
| MakeHuman hm08 (MPFB2) | ≈13,380 body (≈19,158 including helper geometry) | macro and micro targets | code is GPL-3+; whether the assets are CC0 or CC-BY is disputed (see `blender/blender-face-addons.md`) | 🧠 |
| Basel Face Model 2009 | 53,490 | 199 shape PCs | non-commercial, registration required | 🧠 |
| ARKit blendshapes (Faceit target) | n/a | 52 | Apple spec | 🧠 |
| MediaPipe Face Mesh | 468 (478 with refinement) | landmarks | Apache-2.0 | 🧠 |

**E. Proportions critics use as sanity checks.** Adults of both sexes; the ranges are wide on purpose because sex, ancestry and age all shift them.

| Measure | Typical adult range | Badge |
|---|---|---|
| Interpupillary distance | mean ≈ 63 mm (Dodgson 2004 is cited at 63.36 mm by a secondary source [16]); range: secondary sources attribute 50–75 mm to Dodgson, versus 54–74 mm here; men wider, 2–3 mm gap unconfirmed [16] | ↔️ |
| Eyeball diameter | 23–25 mm | 🧠 |
| Visible iris diameter (HVID) | 11.0–12.5 mm | 🧠 |
| Intercanthal width (en–en) | 28–35 mm | 🧠 |
| Palpebral fissure length (ex–en) | 27–33 mm | 🧠 |
| Nasal width (al–al) | 30–40 mm, strongly ancestry-dependent | 🧠 |
| Mouth width (ch–ch) | 45–55 mm | 🧠 |
| Ear length | 55–70 mm, increases with age | 🧠 |
| Canon "ear axis parallel to nose bridge" | holds in only a minority of faces; the ear is usually more upright | ↔️ |

**F. Thread register.** Threads are listed in topic-ID order. The years are estimated from the IDs, except for [1], which carries its year in the title.

| ID | Thread | Est. year | Src |
|---|---|---|---|
| 1154237 | AutoFace: character from a single photograph | ~2019 | [6] |
| 1173005 | KeenTools for Blender 2.8 | ~2019 | [4] |
| 1210803 | First stable FaceBuilder release | ~2020 | [3] |
| 1211277 | Model human face from random photos | ~2020 | [7] |
| 1245723 | Revamped FaceBuilder | ~2020 | [2] |
| 1294243 | FaceBuilder 2021.1, now with AI | 2021 | [1] |
| 1313606 | Photo to 3D | ~2021 | [8] |
| 1531052 | MetahumanModeler (from a single image) | ~2024 | [5] |
| 1606840 | Want to Create a 3D Model Face of Myself? | ~2025 | [9] |

## Applying this to photo→3D face sculpting in Blender

1. **Capture**
   - Distance: shoot from 1.5 m or more, ideally 2–3 m, with a 2–3× phone lens or an 85–135 mm-equivalent lens. At that distance the nose/ear magnification stays at or below about 7% (Table A).
   - Camera height: put the lens at the level of the nose.
   - Views: take 5–9 of them. You need a front view, three-quarter views at about ±30–45°, both profiles, and one shot each from slightly below and slightly above.
   - Expression: neutral, with the lips closed and the eyes looking at the lens.
   - Setup: pull the hair back, light the face softly, and turn off filters and selfie mirroring.
   - Files: keep the originals, so the EXIF data survives.
   - Expressive photos: keep them for expression work only [1][2].
2. **Match the camera in Blender**
   - Set the render resolution to the photo's exact pixel size.
   - Set `sensor_fit = 'HORIZONTAL'` and `sensor_width = 36`, and convert the EXIF 35 mm-eq focal length using the diagonal (Table C). With `AUTO`, the sensor width applies to the *larger* dimension, which silently breaks portrait-orientation photos.
   - A cropped photo moves the principal point. Correct for it with Shift X/Y, or solve on the uncropped originals.
   - Put each photo in its camera's Background Images, not on an orthographic plane.
3. **Pins**
   - Treat the auto-pins as a draft and check every view [1].
   - Trust these most, in order: eye corners, mouth corners, alae and subnasale, ear top and tragus, chin. Check jaw-contour pins last, because they slide along the silhouette.
   - Re-solve, then review all the views together before you sculpt.
4. **Focal consistency.** Photos taken with the same lens at the same zoom should share one focal length. If the solved focals differ by more than about 10–15%, or disagree with the EXIF, suspect a bad pin or a cropped or rescaled file [2].
5. **Likeness check**
   - Render through each solved camera and overlay the render on the photo at 50% opacity, or with Difference blending.
   - Compare the profile silhouettes.
   - Flip the image horizontally, and blur it to judge the big shapes.
   - Check the scale against interpupillary distance (Table E), or better, against the PD on a glasses prescription.
6. **Sculpting order.** BA's consensus is to get the proportions right before adding any detail, and to keep the topology fixed in a Multires stack. 🧠
   - Use a lattice or a large Grab brush at Multires level 0–1 for cranium length and jaw.
   - Then place the eyeballs (Table E) and build the lid thickness over them.
   - Then the nose, then the lips over a curved dental arch, then the ears.
   - Break symmetry last, and keep the person's real asymmetry.
7. **Single photo.** With one photo, nose projection, forehead and chin slope, and cheek depth all come from the statistical prior [5][6]. Use the result for blocking only, and take depth from a profile photo.
8. **Topology and licences.** Choose the output topology (MPFB2, MetaHuman, FLAME or custom) *before* fitting, because retopologizing afterwards loses some of the fit [5]. Check the licences for FaceBuilder [1][4], FLAME and the MakeHuman assets before you distribute anything.
9. **Common failures**
   - mixing different expressions in one identity solve
   - accepting unchecked three-quarter and profile auto-pins
   - solving a selfie as if it were taken from far away, which gives a big nose and a narrow face
   - using a mirrored selfie
   - using orthographic planes for anything beyond blocking

## Algorithmic implications

- **Two levels of pin trust** 🧠
  - Detector pins go into `ViewObs.weights`, with σ measured in IOD: about 0.03×IOD for interior points and 0.06–0.08×IOD for contour points.
  - Contour residuals should be point-to-curve, measured along the normal only.
  - User-placed pins get σ ≈ 1–2 screen pixels, converted to image pixels at the current zoom, with a Huber loss.
  - Re-solve after every edit. This is the "auto, then fix" loop the vendor describes [1].
- **Cameras** 🧠
  - Solve one f_px per photo, and never optimize the sensor size: the pixels constrain only the ratio of focal length to sensor size, so auto-setting both [2] is redundant.
  - Initialize f_px from EXIF via `focal_px_from_35mm`. Set `f_prior_log_sigma` to 0.05–0.10 when EXIF is present, and keep the engine default of 0.35 when it is not.
  - Tie photos tagged "same lens" together with a log-difference prior of σ ≈ 0.02.
  - Export with `to_blender_camera`, which already writes HORIZONTAL sensor fit and the shift.
- **Perspective guard:** if the solved distance from camera to nose is under about 0.8 m, warn that the mid-face is inflated by 12% or more (Table A). Then down-weight that view's depth-sensitive landmarks, or ask the user for a far shot or a profile 🧠
- **Scale:** photos alone do not fix absolute size. Default to an IPD prior of 63 ± 3.5 mm (1σ), and let a user-entered PD or ruler measurement override it 🧠
- **Mirroring:** when the EXIF LensModel names a front camera, ask the user whether the image is mirrored, and offer a flip. Never symmetrize the head. Keep `sigma_sym` at about 2 mm (useful range 1.5–3) 🧠
- **Identity vs expression:** solve one identity vector for the whole set, plus one expression vector per view with a prior centered on zero. Fix the expression at zero for views flagged neutral. Drop lip landmarks from views with the mouth open, and lid landmarks from views where the person squints [1][2] 🧠
- **Depth confidence:** compute the posterior covariance from the LM solver's JᵀJ. Write each vertex's depth σ to a Blender color attribute so the artist can see which parts came from the prior, especially in single-view mode [5][6] 🧠
- **Template transfer:** move the template with `RBFWarp` followed by `laplacian_deform` onto the chosen topology. Version a landmark→vertex correspondence table for each base mesh (Table D). Attach `{licence, commercial_ok}` to every prior, and block FLAME-derived exports until the licence has been verified 🧠
- **Automated critique:** report per-landmark reprojection error as a percentage of IOD, plus per-view RMSE, alongside the overlay render from step 5. This automates the forum's own likeness check 🧠

## Disagreements, myths & open questions

- **Myth: AI pins are one-click.** The vendor itself says they are not [1].
- **Myth: support for expressions means any photo will do.** The same vendor material says neutral photos fit better [1][2].
- **Myth: "a telephoto lens flattens the face".** Distance does that; the lens only crops (Table B). The forum advice works only because a longer lens makes the photographer stand farther back ↔️
- **Orthographic planes vs matched cameras.** Orthographic planes are still the default in tutorials. They are wrong for photos taken closer than about 2 m, but fine for blocking 🧠
- **Proportion canons vs anthropometry.** Artists teach thirds, fifths and "ear parallel to nose". Farkas's revision of the neoclassical canons found that most of these rules are only approximate, or hold only in a minority of faces ↔️
- **Box modeling vs sculpt-and-retopo vs fitting tools.** There is no consensus. Fitting tools get to a first likeness faster; hand methods give more control 🧠
- **Single-photo likeness.** Threads [5][6] claim it, but nobody has measured it. On geometric grounds, the depth comes from the prior.
- **FaceBuilder terms** 📄. Users report it is paid [1][4]. KeenTools states a 15-day trial per add-on (not 30) [10][11] and Blender 5.0 support since 2025.3 [12] (corrected in verification). The current price is unconfirmed.
- **FLAME licence** 📄. Versions up to 2020 are non-commercial; FLAME 2023 Open is released under CC-BY-4.0 and allows commercial use [13][14] (corrected in verification).
- **Thread order** ↔️. Topic IDs and recollection both say the revamp came before 2021.1, contradicting the harvester's "later revamp".
- **Open questions:**
  - Has any BA thread measured accuracy, in millimetres or reprojection pixels?
  - What do the MPFB2 likeness threads advise?
  - A tally of errors flagged in "Focused Critique" threads.
  - Which bpy scripts have been shared for camera matching, landmark import or shape-key fitting?
  - What do threads [7][8][9] advise?

## Sources

1. FaceBuilder for Blender 2021.1 is out: now with AI — https://blenderartists.org/t/facebuilder-for-blender-2021-1-is-out-now-with-ai/1294243 — forum (vendor announcement) — 2021
2. Revamped FaceBuilder for Blender — https://blenderartists.org/t/revamped-facebuilder-for-blender/1245723 — forum (vendor announcement) — n.d. (~2020 by topic ID)
3. The first-stable FaceBuilder release for Blender — https://blenderartists.org/t/the-first-stable-facebuilder-release-for-blender/1210803 — forum — n.d.
4. KeenTools For Blender 2.8 — https://blenderartists.org/t/keentools-for-blender-2-8/1173005 — forum (Blender Development Discussion) — n.d.
5. Generating metahuman based on a single image blender ue5 tutorial — https://blenderartists.org/t/generating-metahuman-based-on-a-single-image-blender-ue5-tutorial/1531052 — forum (Released Add-ons and Extensions) — n.d.
6. AutoFace - Create Rigged and Textured Character from a Single Photograph — https://blenderartists.org/t/autoface-create-rigged-and-textured-character-from-a-single-photograph/1154237 — forum — n.d.
7. Model human face from random photos — https://blenderartists.org/t/model-human-face-from-random-photos/1211277 — forum (Modeling) — n.d.
8. Photo to 3D — https://blenderartists.org/t/photo-to-3d/1313606 — forum (Basics & Interface) — n.d.
9. Want to Create a 3D Model Face of Myself? — https://blenderartists.org/t/want-to-create-a-3d-model-face-of-myself/1606840 — forum (Modeling) — n.d.
10. FaceBuilder for Blender (product page, trial terms) — https://keentools.io/products/facebuilder-for-blender — vendor — current
11. KeenTools Blender Pack download page (per-add-on 15-day trial, per search summary) — https://keentools.io/download-blender — vendor — current
12. KeenTools 2025.3 (Dec 4, 2025) — https://keentools.io/news/2025-3 — vendor release notes — 2025
13. FLAME model license — https://flame.is.tue.mpg.de/modellicense.html — official (MPI) — current
14. FLAME project page — https://flame.is.tue.mpg.de/ — official (MPI) — current
15. 35 mm equivalent focal length (cites CIPA DCG-001, diagonal 43.27 mm) — https://en.wikipedia.org/wiki/35mm_equivalent — secondary — current
16. Pupillary distance (cites Dodgson 2004) — https://en.wikipedia.org/wiki/Pupillary_distance — secondary — current

**Further reading (by name, not yet linked)**
- Farkas, *Anthropometry of the Head and Face* (2nd ed., 1994)
- Farkas, Hreczko, Kolar & Munro, "Vertical and horizontal proportions of the face in young adult North American Caucasians: revision of neoclassical canons", *Plastic and Reconstructive Surgery* (1985)
- Dodgson, "Variation and extrema of human interpupillary distance", SPIE Stereoscopic Displays and Virtual Reality Systems XI (2004)
- Ward et al., "Nasal distortion in short-distance photographs: the selfie effect", *JAMA Facial Plastic Surgery* (2018)
- Li, Bolkart, Black, Li & Romero, "Learning a model of facial shape and expression from 4D scans" (FLAME), *ACM Transactions on Graphics* (2017)
- Paysan et al., "A 3D Face Model for Pose and Illumination Invariant Face Recognition" (Basel Face Model, 2009)
- Blanz & Vetter, "A Morphable Model for the Synthesis of 3D Faces" (SIGGRAPH 1999)
- Hartley & Zisserman, *Multiple View Geometry in Computer Vision*
- Zarins, *Anatomy of Facial Expression* (2017)
- Blender Manual: Camera properties (sensor fit, shift, background images)
- KeenTools FaceBuilder documentation; MPFB2 documentation; fSpy documentation

## Verification log (2026-11-20)

- **FLAME licence** — corrected. FLAME 2023 Open exists and is CC-BY-4.0 (commercial use allowed); earlier versions and the Blender add-on are non-commercial; texture model is BY-NC-SA 4.0. https://flame.is.tue.mpg.de/modellicense.html , https://flame.is.tue.mpg.de/
- **EXIF FocalLengthIn35mmFilm on the diagonal** — confirmed only in part (one secondary source). CIPA DCG-001 defines the conversion by diagonal (43.27 mm); the DC-008 wording itself was not seen, and per-manufacturer practice is unconfirmed, so the Table C badge stays ↔️. https://en.wikipedia.org/wiki/35mm_equivalent
- **KeenTools FaceBuilder terms** — corrected. Trial is 15 days per add-on, not 30; Blender 5.0 supported since KeenTools 2025.3; current price not found. https://keentools.io/products/facebuilder-for-blender , https://keentools.io/download-blender , https://keentools.io/news/2025-3
- **Adult IPD (Dodgson 2004)** — contested. Mean about 63 mm (63.36 cited) is consistent; secondary sources give 50–75 mm, not 54–74 mm; the male–female 2–3 mm gap was not confirmed. The 63 ± 3.5 mm prior stays 🧠. https://en.wikipedia.org/wiki/Pupillary_distance
