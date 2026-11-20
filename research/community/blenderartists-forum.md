# BlenderArtists forum knowledge on faces

> BlenderArtists (BA) is where KeenTools announced FaceBuilder for Blender, from the 2.8 beta thread through the 2021.1 "now with AI" release. It also hosts single-photo generator add-ons (AutoFace, MetahumanModeler) and a "model my own face from photos" question that keeps coming back year after year. The harvested threads say three things: neural auto-pinning is only a first draft, FaceBuilder estimates focal length and sensor size for each photo, and expressive photos are accepted but neutral ones fit better. None of the threads gives an accuracy figure. The rest of this note is expert knowledge (🧠) of BA modeling and critique culture, and it turns that into numbers an artist or a solver can use: how perspective changes with camera distance, the 35 mm-equivalent conventions, base-mesh sizes and sanity-check proportions.
> Evidence status: 3 ✅ / 7 📄 / 33 🧠 / 7 ↔️ — 🧠 items are queued for web verification.

## Key facts

**From harvested threads**
- KeenTools announced FaceBuilder for Blender on BA over several versions, in separate threads: the 2.8 beta, the first stable release, the "Revamped" release and 2021.1. BA is therefore the place to find the vendor's own statements and the users' early bug reports [1][2][3][4] ✅
- In 2021.1, "a couple of neural networks" find the face and place all the pins automatically (paraphrased from the search summary) [1] 📄
- The developers say the automatic pins are "not always 100% accurate" and sometimes need fixing by hand. This is the vendor's own warning [1] 📄
- The "Revamped FaceBuilder" thread says focal length and sensor size are set automatically for each photo [2] 📄
- Expressions are supported, so neutral photos are not strictly required, but neutral photos are still said to give better quality [1][2] 📄. Both threads come from the same vendor, so they are not independent sources.
- Forum users call FaceBuilder a paid add-on, and one mentions a 30-day trial. These terms may change over time and have not been checked against keentools.io [1][4] 📄
- MetahumanModeler ("Released Add-ons and Extensions") reportedly builds a mesh with MetaHuman topology from a single image. Its author says it was built from their understanding of FaceBuilder [5] 📄
- Single-photo character generators come up again and again (AutoFace, MetahumanModeler). Both threads exist, but neither has accuracy evidence [5][6] ✅
- Beginners keep asking how to model a face from photos ("random photos", "Photo to 3D", "a 3D model face of myself"). Judging by topic IDs, the threads span about 2020 to 2025. Their answers were not harvested [7][8][9] ✅
- **Thread order.** Discourse assigns topic IDs in the order topics are created. By ID, "Revamped" (1245723) came before 2021.1 (1294243), and I also recall the revamp landing in 2020. That contradicts the harvester's wording of a "later revamp" [1][2] ↔️

**BA community knowledge (expert synthesis, not harvested)**
- The method taught most often on BA is to put front and side photos on orthographic image planes and model over them. It is also the most common cause of "my front and side don't line up" threads. Photos are perspective projections, and head pitch and yaw differ between shots, so the eye, nose and chin heights disagree between views 🧠
- The standard forum fix is to shoot from farther away with a longer lens, keep the camera level at nose height, align the views on stable landmarks (inner eye corners, nose base, ear tops), and treat the photos as guides, not ground truth 🧠
- **The rule for likeness critiques.** Critics ask for the reference photo next to a render made through a *matched* camera, with the same focal length, angle and distance. A 50 mm orthographic-ish render compared with a phone selfie cannot be judged 🧠
- **Recurring critique targets**, roughly by how often they come up (synthesis, not counted):
  - back of the skull too short or flat, because hair hides the cranium;
  - eye spacing or eyeball size wrong;
  - eyelids with no thickness, and not enough of the iris covered by the upper lid;
  - flat lips that do not wrap around the dental arch;
  - nostril wings (alae) too narrow, or the nose tip projecting by the wrong amount;
  - ears placed too low or too far forward;
  - neck too thin;
  - perfect symmetry, which reads as a mannequin 🧠
- **Process consensus.** Get the proportions right first at low resolution (base mesh plus proportional editing, or the Grab brush at a large radius on Multires level 0–1). Keep a Multiresolution stack so the topology stays fixed. Break symmetry late. Add detail last 🧠
- **Tools that come up on BA:**
  - MPFB2/MakeHuman: slider and target based, with no photo fitting built in;
  - MB-Lab and CharMorph, from the ManuelbastioniLAB lineage;
  - Human Generator (paid);
  - FLAME's Blender add-on, whose research licence raises concerns;
  - photogrammetry (Meshroom, RealityCapture) for real scans;
  - fSpy, which needs straight lines in the scene and so is a poor fit for close face shots 🧠
- **Phone-selfie traps.** A front camera is about 22–30 mm-equivalent and is held at arm's length (0.3–0.6 m). Mirrored selfies flip the person's real asymmetry. "Beauty" and face-correction processing warps the geometry 🧠

## Numbers & reference tables

**A. Perspective: how much larger the nose-tip plane appears than the ear (tragion) plane.** This is pinhole geometry: magnification = 1 + d/Z, where Z is the distance from the camera to the nose tip and d is the depth from nose tip to tragion. The table takes d = 10 cm, and the range covers d = 9–12 cm.

| Camera → nose tip (m) | Typical setup | Relative magnification | Badge |
|---|---|---|---|
| 0.3 | close selfie | 1.33 (1.30–1.40) | 🧠 |
| 0.5 | arm's-length selfie | 1.20 (1.18–1.24) | 🧠 |
| 1.0 | phone 1× at a polite distance | 1.10 (1.09–1.12) | 🧠 |
| 1.5 | 85 mm-eq head-and-shoulders | 1.067 (1.06–1.08) | 🧠 |
| 2.0 | 2–3× phone tele | 1.05 (1.045–1.06) | 🧠 |
| 3.0 | 135–200 mm-eq | 1.033 (1.03–1.04) | 🧠 |
| 5.0 | long tele | 1.02 | 🧠 |

**B. Distance needed for a tight head-only framing** (0.35 m vertical field, portrait orientation, 36 mm long side), and the magnification that results. **Perspective depends on distance. Focal length only sets the crop.**

| Focal (35 mm-eq) | Distance (m) | Nose/ear magnification | Badge |
|---|---|---|---|
| 24 mm | 0.23 | 1.43 | 🧠 |
| 50 mm | 0.49 | 1.21 | 🧠 |
| 85 mm | 0.83 | 1.12 | 🧠 |
| 135 mm | 1.31 | 1.08 | 🧠 |
| 200 mm | 1.94 | 1.05 | 🧠 |

**C. The 35 mm-equivalent convention.** This compares a width-based conversion (f_px = f35·W/36) with the diagonal-based one (f_px = f35·diag/43.27). The engine's `focal_px_from_35mm` uses the diagonal.

| Native aspect | Width-based f_px ÷ diagonal f_px | Effect if the wrong one is used | Badge |
|---|---|---|---|
| 3:2 | 1.000 | none | 🧠 |
| 4:3 (most phones) | 0.962 | focal about 4% too short, so a slightly too-close camera and a deeper face | ↔️ manufacturers may differ |
| 16:9 | 1.048 | focal about 5% too long | ↔️ |

**D. Base meshes and model sizes discussed in BA add-on threads** (from my knowledge; check before hard-coding)

| Model | Vertices | Parameters | Licence note | Badge |
|---|---|---|---|---|
| FLAME (2017/2020) | 5,023 (9,976 tris) | 300 shape, 100 expression; jaw, neck and eye joints | non-commercial research; commercial via Meshcapade; a more open 2023 release is possible but unconfirmed | ↔️ licence / 🧠 counts |
| MakeHuman hm08 base (MPFB2) | ≈13,380 body (≈19,158 with helpers) | macro and micro targets | code GPL-3+, asset licence CC0 vs CC-BY disputed (see `blender/blender-face-addons.md`) | 🧠 |
| Basel Face Model 2009 | 53,490 | 199 PCA shape components | non-commercial, registration required | 🧠 |
| ARKit blendshape set (Faceit target) | n/a | 52 shapes | Apple spec | 🧠 |
| MediaPipe Face Mesh | 468 (478 with refine) | landmarks | Apache-2.0 | 🧠 |
| FaceBuilder head, MetaHuman head | not known here | n/a | proprietary | 🧠 |

**E. Sanity-check proportions critics reach for** (adults, mixed sexes; ranges are wide on purpose because of sex, ancestry and age)

| Measure | Typical adult range | Badge |
|---|---|---|
| Interpupillary distance | mean ≈ 63 mm; most adults 54–74 mm; men about 2–3 mm wider (Dodgson 2004) | 🧠 |
| Eyeball diameter | 23–25 mm | 🧠 |
| Visible iris diameter (HVID) | 11.0–12.5 mm | 🧠 |
| Intercanthal width (en–en) | 28–35 mm | 🧠 |
| Palpebral fissure length (ex–en) | 27–33 mm | 🧠 |
| Nasal width (al–al) | 30–40 mm, strongly ancestry-dependent | 🧠 |
| Mouth width (ch–ch) | 45–55 mm | 🧠 |
| Ear length | 55–70 mm, grows with age | 🧠 |
| "Ear axis parallel to the nose bridge" canon | holds only in a minority of people; ear tilt is usually less steep | ↔️ |

**F. Thread register** (topic-ID order; dates are estimates from IDs, except [1])

| ID | Thread | Est. year | Src |
|---|---|---|---|
| 1154237 | AutoFace: single photograph → character | ~2019 | [6] |
| 1173005 | KeenTools for Blender 2.8 | ~2019 | [4] |
| 1210803 | First stable FaceBuilder release | ~2020 | [3] |
| 1211277 | Model human face from random photos | ~2020 | [7] |
| 1245723 | Revamped FaceBuilder | ~2020 | [2] |
| 1294243 | FaceBuilder 2021.1, now with AI | 2021 | [1] |
| 1313606 | Photo to 3D | ~2021 | [8] |
| 1531052 | MetahumanModeler (single image) | ~2024 | [5] |
| 1606840 | Want to Create a 3D Model Face of Myself? | ~2025 | [9] |

## Applying this to photo→3D face sculpting in Blender

1. **Capture**
   - Stand at least 1.5 m from the subject, ideally 2–3 m. Use a 2–3× phone telephoto or an 85–135 mm-eq lens, which keeps the nose/ear magnification under about 7% (Table A).
   - Put the lens at nose height.
   - Take 5–9 views: front, ±30–45° three-quarters, both profiles, one slightly from below (jaw underside and nostrils) and one slightly from above (top of the cranium).
   - Use a neutral expression with the lips closed, the teeth lightly together and the eyes on the lens.
   - Pull the hair back so the ears and hairline show. Use soft, even light.
   - Turn off beauty filters and selfie mirroring, and keep the original files with their EXIF.
   - Keep expressive shots for later expression work only [1][2].
2. **Blender camera matching**
   - Set the render resolution to the photo's exact pixel size.
   - Set `sensor_fit = 'HORIZONTAL'` and `sensor_width = 36`, and convert the EXIF 35 mm-equivalent focal length using the diagonal (Table C). With `AUTO`, the sensor width applies to the *larger* image dimension, which silently breaks portrait-orientation photos.
   - A cropped photo moves the principal point. Use Shift X/Y, or solve on the uncropped originals.
   - Put each photo on its camera's Background Images, not on an orthographic plane.
3. **Pins and landmarks**
   - Accept auto-pins as a draft, then check every view [1]. Trust these in order: inner and outer eye corners, mouth corners, nostril wings and subnasale, ear top and tragus, chin.
   - Jaw-contour points slide along the silhouette and should be checked last.
   - After fixing pins, re-solve and look at all views together before you sculpt.
4. **Check focal length**
   - Photos from one phone lens at one zoom should share a focal length. If the solved focal lengths differ by more than about 10–15%, or disagree with EXIF, suspect a bad pin or a cropped or rescaled file [2].
5. **Check the likeness**
   - Render through each solved camera and overlay the render on the photo at 50% opacity, or with a Difference blend.
   - Compare profile silhouettes.
   - Flip both images horizontally to see them fresh, and blur both to judge the big shapes.
   - Check absolute scale against interpupillary distance (Table E), or better, against a real measurement such as the PD on the person's glasses prescription.
6. **Sculpting order**
   - Lattice or large-radius Grab on Multires level 0–1 for the cranium length and the jaw.
   - Then the eyes: set the eyeball first (Table E) and build lid thickness over it.
   - Then the nose, then the lips over a curved dental arch, then the ears.
   - Break symmetry only after the proportions match, and keep the person's real asymmetry instead of averaging it away.
7. **Single photo:** nose projection, forehead and chin slope, and cheek depth come from the tool's statistical prior, not from the person [5][6]. Use the output for blocking. Get the depth from a profile photo.
8. **Topology and licence**
   - Decide on the output topology (MPFB2, MetaHuman, FLAME, your own) *before* fitting, because retopologizing afterwards loses some of the fit [5].
   - Check the licence of FaceBuilder [1][4], FLAME and the MakeHuman assets before you distribute anything.
9. **Common failures**
   - mixing expressions in one identity solve;
   - unchecked three-quarter and profile auto-pins;
   - a selfie solved as if it were a far shot (nose too big, face too narrow);
   - mirrored selfies;
   - orthographic planes used for anything beyond blocking.

## Algorithmic implications

- **Two levels of pin trust**
  - Detector pins go into `ViewObs.weights` with σ in units of interocular distance (IOD): about 0.03×IOD for interior points and 0.06–0.08×IOD for contour points. Contour residuals should be point-to-curve (normal direction only), so contour points can slide along the silhouette.
  - User-placed pins get σ_px ≈ 1–2 screen pixels, converted to image pixels at the current zoom, with a Huber loss.
  - Re-solve after every edit. This is the "auto, then fix" workflow the vendor itself describes [1] 🧠
- **Cameras**
  - Solve one f_px per photo. Never optimize sensor size: pixels only constrain the ratio of focal length to sensor size, so FaceBuilder's two-value auto-set [2] is redundant.
  - Initialize from EXIF via `focal_px_from_35mm`. Use `f_prior_log_sigma` of 0.05–0.10 when EXIF is present, and keep the engine's 0.35 when it is not.
  - Tie photos tagged "same lens" with a log-difference prior σ ≈ 0.02.
  - Export with `to_blender_camera`. It already uses `HORIZONTAL` sensor fit and shift for an off-centre principal point 🧠
- **Perspective guard:** if the solved camera-to-nose distance is under about 0.8 m, warn that the photo inflates the mid-face by 12% or more (Table A). Lower that view's weight for depth-sensitive landmarks, or require a far shot or a profile 🧠
- **Scale:** images alone cannot give absolute scale. Default to an IPD prior of 63 ± 3.5 mm (1σ), and override it with a user-entered PD or ruler measurement when available 🧠
- **Mirroring:** if EXIF names a front camera (for example, a LensModel string that contains "front"), ask whether the image is mirrored and offer a flip. Never symmetrize the result; keep the engine's `sigma_sym` ≈ 2 mm (useful range 1.5–3 mm) 🧠
- **Identity vs expression:** use one identity vector and one expression vector per view, with the expression prior centred on zero. Views flagged neutral have their expression fixed at zero. Drop the lip landmarks from mouth-open views and the lid landmarks from squinting views [1][2] 🧠
- **Depth confidence:** compute the posterior covariance from the LM solver's JᵀJ. Write the per-vertex depth σ to a Blender color attribute, so the artist can see which parts come from the prior. This matters most in single-view mode [5][6] 🧠
- **Template transfer:** warp the template with `RBFWarp`, then run `laplacian_deform` onto the chosen topology. Keep versioned landmark→vertex correspondence tables per base mesh (Table D). Store `{licence, commercial_ok}` with every prior and default to refusing to export FLAME-derived data until its licence is checked 🧠
- **Built-in critique:** report per-landmark reprojection error as a percentage of IOD and per-view RMSE, and provide the overlay render from item 5. These are the forum's own likeness checks, automated 🧠

## Disagreements, myths & open questions

- **Myth: AI pins are one-click.** The vendor itself says they are not [1].
- **Myth: expressions make any photo usable.** The same material says neutral photos are better [1][2].
- **Myth: "a telephoto lens flattens the face."** Camera distance does that. Focal length only crops (Table B). The forum advice works only because a longer lens makes people stand farther away ↔️
- **Orthographic image planes vs matched cameras.** The planes are still the default in tutorials. They are geometrically wrong below about 2 m, but fine for blocking 🧠
- **Canons vs anthropometry.** Facial thirds, fifths and "ear parallel to nose" are taught as rules. Farkas's revision of the neoclassical canons found that most hold only approximately, or only in a minority of faces ↔️
- **Box modeling vs sculpt-and-retopo vs fitting tools.** BA has no consensus. Fitting tools win on time to a first likeness, while hand methods win on control 🧠
- **Single-photo likeness:** claimed by [5][6] and unmeasured. On geometric grounds, depth comes from the prior.
- **FaceBuilder terms:** paid, with a 30-day trial according to users [1][4]. The current price, licence and Blender 5.x support are unknown ↔️
- **FLAME licence:** research-only vs a possibly more open newer release ↔️
- **Thread order:** topic IDs and my recollection put "Revamped" before 2021.1, against the harvester's "later" ↔️
- **Open questions**
  - Has any BA thread measured accuracy (mm error, reprojection error) for FaceBuilder, AutoFace or MetahumanModeler?
  - What do MPFB2 likeness threads recommend for matching the targets to photos?
  - Which likeness errors do critiques actually flag most often? A count from the "Focused Critique" and "Works in Progress" categories would be useful.
  - Which bpy scripts have users shared for camera matching, MediaPipe/dlib landmark import, or shape-key fitting?
  - What do threads [7][8][9] actually advise?

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

**Further reading (by name, not yet linked)**
- Farkas, *Anthropometry of the Head and Face* (2nd ed., 1994)
- Farkas, Hreczko, Kolar & Munro, "Vertical and horizontal proportions of the face in young adult North American Caucasians: revision of neoclassical canons", *Plastic and Reconstructive Surgery* (1985)
- Dodgson, "Variation and extrema of human interpupillary distance", SPIE Stereoscopic Displays and Virtual Reality Systems XI (2004)
- Ward et al., "Nasal distortion in short-distance photographs: the selfie effect", *JAMA Facial Plastic Surgery* (2018)
- Li, Bolkart, Black, Li & Romero, "Learning a model of facial shape and expression from 4D scans" (FLAME), *ACM Transactions on Graphics* / SIGGRAPH Asia (2017)
- Paysan et al., "A 3D Face Model for Pose and Illumination Invariant Face Recognition" (Basel Face Model, 2009)
- Blanz & Vetter, "A Morphable Model for the Synthesis of 3D Faces" (SIGGRAPH 1999)
- Hartley & Zisserman, *Multiple View Geometry in Computer Vision*
- Zarins, *Anatomy of Facial Expression* (2017)
- Blender Manual: Camera properties (sensor fit, shift, background images)
- KeenTools FaceBuilder documentation; MPFB2 documentation; fSpy documentation
